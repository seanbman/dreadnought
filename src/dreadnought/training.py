from __future__ import annotations

from copy import deepcopy
import hashlib
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
from typing import Any, Iterable
from uuid import uuid4

from . import __version__
from .evaluation import EvaluationSummary
from .order import Order
from .protocol import ProtocolRecord, RecordKind
from .usage import TokenUsage


TRAINING_EPISODE_SCHEMA_VERSION = 1
TRAINING_FEEDBACK_SCHEMA_VERSION = 1
PROMPT_PROFILE = "project-arm-v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=False) + "\n")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid JSONL at {path}:{line_number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"invalid JSONL object at {path}:{line_number}")
        rows.append(payload)
    return rows


def _git_output(path: Path | str, *args: str) -> str | None:
    root = Path(path).resolve()
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    value = completed.stdout.strip()
    return value or None


def git_revision(path: Path | str) -> str | None:
    return _git_output(path, "rev-parse", "HEAD")


def git_branch(path: Path | str) -> str | None:
    value = _git_output(path, "rev-parse", "--abbrev-ref", "HEAD")
    return None if value in {None, "HEAD"} else value


def git_repository(path: Path | str) -> str | None:
    remote = _git_output(path, "config", "--get", "remote.origin.url")
    if not remote:
        return None
    normalized = remote.strip()
    slug: str | None = None
    if normalized.startswith("git@github.com:"):
        slug = normalized.split(":", 1)[1]
    elif "github.com/" in normalized:
        slug = normalized.split("github.com/", 1)[1]
    if slug is None:
        return None
    slug = slug.split("?", 1)[0].split("#", 1)[0].strip("/")
    if slug.endswith(".git"):
        slug = slug[:-4]
    parts = [part for part in slug.split("/") if part]
    if len(parts) != 2:
        return None
    return "/".join(parts)


def _runtime_revision() -> str | None:
    declared = os.environ.get("DREADNOUGHT_COMMIT_SHA")
    if declared:
        return declared.strip() or None
    source_root = Path(__file__).resolve().parents[2]
    return git_revision(source_root)


def _safe_relative_ref(ref: object) -> str | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    path = Path(ref.strip())
    if path.is_absolute() or any(part == ".." for part in path.parts):
        return None
    return str(path)


def _artifact_location(
    ref: object,
    *,
    project_root: Path,
    scratch_root: Path | None,
) -> tuple[str, str, Path | None] | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    raw = ref.strip()
    path = Path(raw)
    roots: list[tuple[str, Path]] = [("project", project_root.resolve())]
    if scratch_root is not None:
        roots.insert(0, ("scratch", scratch_root.resolve()))

    if path.is_absolute():
        resolved = path.resolve()
        for scope, root in roots:
            try:
                relative = resolved.relative_to(root)
            except ValueError:
                continue
            return scope, str(relative), resolved
        return None

    relative = _safe_relative_ref(raw)
    if relative is None:
        return None
    for scope, root in roots:
        candidate = (root / relative).resolve()
        try:
            candidate.relative_to(root)
        except ValueError:
            continue
        if candidate.exists():
            return scope, relative, candidate
    # Agent work is scratch-first when a scratch root exists. Preserve the
    # reported relative identity without pretending the file was observed.
    if scratch_root is not None:
        return "scratch", relative, (scratch_root.resolve() / relative)
    return "project", relative, (project_root.resolve() / relative)


def _redact_value(
    value: Any,
    *,
    project_root: Path,
    workspace: Path,
    scratch_root: Path | None = None,
) -> Any:
    if isinstance(value, dict):
        return {
            key: _redact_value(
                item,
                project_root=project_root,
                workspace=workspace,
                scratch_root=scratch_root,
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [
            _redact_value(
                item,
                project_root=project_root,
                workspace=workspace,
                scratch_root=scratch_root,
            )
            for item in value
        ]
    if isinstance(value, tuple):
        return [
            _redact_value(
                item,
                project_root=project_root,
                workspace=workspace,
                scratch_root=scratch_root,
            )
            for item in value
        ]
    if not isinstance(value, str):
        return value
    text = value
    replacements: list[tuple[str, str]] = [
        (str(project_root.resolve()), "<PROJECT>"),
        (str(workspace.resolve()), "<WORKSPACE>"),
    ]
    if scratch_root is not None:
        replacements.insert(0, (str(scratch_root.resolve()), "<SCRATCH>"))
    for raw, replacement in replacements:
        if raw and raw in text:
            text = text.replace(raw, replacement)
    return text


def _sanitized_protocol_record(
    record: ProtocolRecord,
    *,
    project_root: Path,
    workspace: Path,
    scratch_root: Path | None,
) -> dict[str, Any]:
    payload = _redact_value(
        record.to_dict(),
        project_root=project_root,
        workspace=workspace,
        scratch_root=scratch_root,
    )
    if record.kind is RecordKind.ARTIFACT:
        location = _artifact_location(
            record.data.get("ref"),
            project_root=project_root,
            scratch_root=scratch_root,
        )
        if location is None:
            payload.setdefault("data", {})["ref"] = "<REDACTED_EXTERNAL_REF>"
        else:
            scope, relative, _ = location
            payload.setdefault("data", {})["ref"] = f"{scope}:{relative}"
    return payload


def _sanitized_verdict(
    record: ProtocolRecord,
    *,
    project_root: Path,
    workspace: Path,
    scratch_root: Path | None,
) -> dict[str, Any]:
    payload = _redact_value(
        record.to_dict(),
        project_root=project_root,
        workspace=workspace,
        scratch_root=scratch_root,
    )
    data = payload.get("data") or {}
    evidence = data.get("evidence")
    if isinstance(evidence, dict) and evidence.get("type") == "command":
        for key in ("stdout", "stderr"):
            raw = evidence.pop(key, None)
            if isinstance(raw, str):
                encoded = raw.encode("utf-8")
                evidence[f"{key}_sha256"] = hashlib.sha256(encoded).hexdigest()
                evidence[f"{key}_bytes"] = len(encoded)
    return payload


def _instructions_sha256(workspace: Path) -> str | None:
    path = workspace / ".dreadnought" / "INSTRUCTIONS.md"
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_fingerprint(path: Path | None, *, max_bytes: int = 16 * 1024 * 1024) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"exists": bool(path and path.exists()), "bytes": None, "sha256": None, "hash_status": "not_file"}
    size = path.stat().st_size
    if size > max_bytes:
        return {"exists": True, "bytes": size, "sha256": None, "hash_status": "skipped_size"}
    return {
        "exists": True,
        "bytes": size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "hash_status": "hashed",
    }


def _usage_dict(usage: TokenUsage | dict[str, Any] | None) -> dict[str, Any] | None:
    if usage is None:
        return None
    if isinstance(usage, TokenUsage):
        return usage.to_dict()
    return dict(usage)


def _acceptance_rollup(order: Order, evaluation: EvaluationSummary) -> list[dict[str, Any]]:
    prefix = f"acceptance:{order.id}:"
    by_index: dict[int, ProtocolRecord] = {}
    for verdict in evaluation.verdicts:
        subject = verdict.subject_ref or ""
        if not subject.startswith(prefix):
            continue
        try:
            index = int(subject[len(prefix):])
        except ValueError:
            continue
        by_index[index] = verdict

    rows: list[dict[str, Any]] = []
    for index, criterion in enumerate(order.acceptance):
        verdict = by_index.get(index)
        rows.append(
            {
                "index": index,
                "criterion": criterion,
                "status": verdict.data.get("status") if verdict else "not_yet_verified",
                "claim_refs": list(verdict.data.get("claim_refs") or []) if verdict else [],
            }
        )
    return rows


def _artifact_rows(
    records: Iterable[ProtocolRecord],
    *,
    project_root: Path,
    scratch_root: Path | None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for record in records:
        if record.kind is not RecordKind.ARTIFACT:
            continue
        location = _artifact_location(
            record.data.get("ref"),
            project_root=project_root,
            scratch_root=scratch_root,
        )
        if location is None:
            continue
        scope, relative, resolved = location
        rows.append(
            {
                "record_id": record.id,
                "artifact_type": record.data.get("artifact_type"),
                "scope": scope,
                "ref": relative,
                **_file_fingerprint(resolved),
            }
        )
    return rows


def _failure_category(*, exit_code: int, evaluation: EvaluationSummary) -> str | None:
    if exit_code != 0:
        return "process_exit_nonzero"
    if evaluation.accepted and evaluation.status.value == "supported":
        return None
    return f"verification_{evaluation.status.value}"


def _stable_split(episode_id: str, *, eval_percent: int, seed: str) -> str | None:
    if eval_percent <= 0:
        return None
    if eval_percent >= 100:
        return "eval"
    digest = hashlib.sha256(f"{seed}:{episode_id}".encode("utf-8")).digest()
    bucket = int.from_bytes(digest[:4], "big") % 10000
    return "eval" if bucket < eval_percent * 100 else "train"


class TrainingCorpus:
    """Append-only normalized execution corpus for later model-training exports.

    Grapher remains Dreadnought's durable project brain. This corpus is a derived
    research dataset: raw protocol/evaluation evidence is preserved separately,
    normalized here one execution per row, and exported later without coupling
    canonical evidence to a model-specific chat template.
    """

    def __init__(self, workspace: Path | str):
        self.workspace = Path(workspace).resolve()
        self.root = self.workspace / ".dreadnought" / "training"
        self.episodes_path = self.root / "episodes.jsonl"
        self.feedback_path = self.root / "feedback.jsonl"

    def ensure_local_storage(self) -> Path:
        self.root.mkdir(parents=True, exist_ok=True)
        ignore = self.root / ".gitignore"
        expected = "*\n!.gitignore\n"
        if not ignore.exists():
            ignore.write_text(expected, encoding="utf-8")
        return ignore

    def record_dispatch(
        self,
        *,
        order: Order,
        project_root: Path,
        scratch_root: Path | None = None,
        adapter_id: str,
        network_policy: str,
        exit_code: int,
        duration_ms: int,
        observation_id: str,
        agent_records: Iterable[ProtocolRecord],
        evaluation: EvaluationSummary,
        usage: TokenUsage | dict[str, Any] | None = None,
        project_commit_before: str | None = None,
        project_commit_after: str | None = None,
        parent_episode_id: str | None = None,
        retry_index: int = 0,
    ) -> dict[str, Any]:
        if retry_index < 0:
            raise ValueError("retry_index must be non-negative")
        self.ensure_local_storage()
        records = list(agent_records)
        eligible = bool(evaluation.accepted and evaluation.status.value == "supported")
        exclusion_reasons: list[str] = []
        if not evaluation.accepted:
            exclusion_reasons.append("order_not_accepted")
        if evaluation.status.value != "supported":
            exclusion_reasons.append(f"verification_{evaluation.status.value}")

        episode = {
            "schema_version": TRAINING_EPISODE_SCHEMA_VERSION,
            "episode_id": f"episode-{uuid4().hex}",
            "created_at": _utc_now(),
            "project": {
                "id": order.project_id or self.workspace.name,
                "root_name": project_root.name,
                "repository": git_repository(project_root),
                "branch": git_branch(project_root),
                "commit_before": project_commit_before,
                "commit_after": project_commit_after,
            },
            "dreadnought": {
                "version": __version__,
                "revision": _runtime_revision(),
                "protocol_schema_version": 1,
                "prompt_profile": PROMPT_PROFILE,
                "instructions_sha256": _instructions_sha256(self.workspace),
            },
            "agent": {
                "adapter_id": adapter_id,
                "provider": (_usage_dict(usage) or {}).get("provider"),
                "model": (_usage_dict(usage) or {}).get("model"),
            },
            "order": _redact_value(
                order.to_dict(),
                project_root=project_root,
                workspace=self.workspace,
                scratch_root=scratch_root,
            ),
            "execution": {
                "exit_code": exit_code,
                "duration_ms": max(0, int(duration_ms)),
                "network_policy": network_policy,
                "observation_id": observation_id,
                "failure_category": _failure_category(exit_code=exit_code, evaluation=evaluation),
            },
            "lineage": {
                "parent_episode_id": parent_episode_id,
                "retry_index": retry_index,
            },
            "agent_testimony": [
                _sanitized_protocol_record(
                    record,
                    project_root=project_root,
                    workspace=self.workspace,
                    scratch_root=scratch_root,
                )
                for record in records
            ],
            "evaluation": {
                "accepted": evaluation.accepted,
                "status": evaluation.status.value,
                "acceptance": _acceptance_rollup(order, evaluation),
                "verdicts": [
                    _sanitized_verdict(
                        record,
                        project_root=project_root,
                        workspace=self.workspace,
                        scratch_root=scratch_root,
                    )
                    for record in evaluation.verdicts
                ],
            },
            "artifacts": _artifact_rows(
                records,
                project_root=project_root,
                scratch_root=scratch_root,
            ),
            "usage": _usage_dict(usage),
            "feedback_refs": [],
            "dataset": {
                "eligible": eligible,
                "redacted": True,
                "redaction_policy": "structural-v1",
                "split": None,
                "exclusion_reasons": exclusion_reasons,
            },
        }
        _append_jsonl(self.episodes_path, episode)
        return episode

    def record_feedback(
        self,
        episode_id: str,
        *,
        rating: str,
        comment: str,
        actor_id: str = "human:user",
    ) -> dict[str, Any]:
        if rating not in {"accept", "reject", "revise"}:
            raise ValueError("feedback rating must be accept, reject, or revise")
        if not comment.strip():
            raise ValueError("feedback comment must not be empty")
        if self.find_episode(episode_id) is None:
            raise ValueError(f"training episode not found: {episode_id}")
        self.ensure_local_storage()
        payload = {
            "schema_version": TRAINING_FEEDBACK_SCHEMA_VERSION,
            "feedback_id": f"feedback-{uuid4().hex}",
            "created_at": _utc_now(),
            "episode_id": episode_id,
            "actor_id": actor_id,
            "rating": rating,
            "comment": comment.strip(),
        }
        _append_jsonl(self.feedback_path, payload)
        return payload

    def episodes(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.episodes_path)

    def feedback(self) -> list[dict[str, Any]]:
        return _read_jsonl(self.feedback_path)

    def find_episode(self, episode_id: str) -> dict[str, Any] | None:
        for episode in reversed(self.episodes()):
            if episode.get("episode_id") == episode_id:
                return episode
        return None

    def stats(self) -> dict[str, Any]:
        episodes = self.episodes()
        feedback = self.feedback()
        by_project: dict[str, int] = {}
        for row in episodes:
            project_id = str((row.get("project") or {}).get("id") or "unknown")
            by_project[project_id] = by_project.get(project_id, 0) + 1
        return {
            "episodes": len(episodes),
            "accepted": sum(1 for row in episodes if bool((row.get("evaluation") or {}).get("accepted"))),
            "eligible": sum(1 for row in episodes if bool((row.get("dataset") or {}).get("eligible"))),
            "feedback_records": len(feedback),
            "by_project": dict(sorted(by_project.items())),
            "episodes_path": str(self.episodes_path),
            "feedback_path": str(self.feedback_path),
        }

    def export(
        self,
        output: Path | str,
        *,
        mode: str = "eligible",
        eval_percent: int = 0,
        split_seed: str = "dreadnought-v1",
    ) -> dict[str, Any]:
        if mode not in {"eligible", "accepted", "all"}:
            raise ValueError("training export mode must be eligible, accepted, or all")
        if not 0 <= eval_percent <= 100:
            raise ValueError("eval_percent must be between 0 and 100")
        if not split_seed.strip():
            raise ValueError("split_seed must not be empty")
        feedback_by_episode: dict[str, list[dict[str, Any]]] = {}
        for item in self.feedback():
            feedback_by_episode.setdefault(str(item.get("episode_id")), []).append(item)

        selected: list[dict[str, Any]] = []
        for source in self.episodes():
            if mode == "eligible" and not bool((source.get("dataset") or {}).get("eligible")):
                continue
            if mode == "accepted" and not bool((source.get("evaluation") or {}).get("accepted")):
                continue
            row = deepcopy(source)
            joined_feedback = feedback_by_episode.get(str(row.get("episode_id")), [])
            row["feedback_refs"] = [str(item.get("feedback_id")) for item in joined_feedback]
            row["human_feedback"] = joined_feedback
            row.setdefault("dataset", {})["split"] = _stable_split(
                str(row.get("episode_id")),
                eval_percent=eval_percent,
                seed=split_seed,
            )
            selected.append(row)

        target = Path(output).expanduser().resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            for row in selected:
                handle.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
        return {
            "output": str(target),
            "mode": mode,
            "records": len(selected),
            "eval_percent": eval_percent,
            "split_seed": split_seed,
            "train_records": sum(1 for row in selected if (row.get("dataset") or {}).get("split") == "train"),
            "eval_records": sum(1 for row in selected if (row.get("dataset") or {}).get("split") == "eval"),
        }
