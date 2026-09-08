from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import re
import shutil
import tempfile
import tomllib
from typing import Iterator


CODEX_SYSTEM_DIR = Path("/etc/codex")
CODEX_ETC_DIR = Path("/etc")
CODEX_ETC_MIRROR = Path("/tmp/.dreadnought-host-etc")
_FEATURE_SECTION = re.compile(r"^\s*\[features\]\s*(?:#.*)?$")
_TABLE_HEADER = re.compile(r"^\s*\[")
_UNIFIED_EXEC = re.compile(r"^(?P<indent>\s*)unified_exec\s*=.*$")


class CodexCompatibilityError(RuntimeError):
    pass


def pin_unified_exec_requirement(contents: str) -> str:
    """Pin Codex unified_exec=false without discarding existing managed policy.

    Codex normalizes ordinary user/CLI feature opt-outs back to enabled. A system
    requirements layer is the supported authority that may disable UnifiedExec.
    Keep the existing requirements document byte-for-byte except for the one
    feature key we own. Exotic inline/dotted feature layouts fail closed instead
    of risking an invalid or policy-dropping rewrite.
    """

    if contents.strip():
        try:
            parsed = tomllib.loads(contents)
        except tomllib.TOMLDecodeError as exc:
            raise CodexCompatibilityError(f"invalid existing Codex requirements.toml: {exc}") from exc
    else:
        parsed = {}

    features = parsed.get("features")
    if features is not None and not isinstance(features, dict):
        raise CodexCompatibilityError("Codex requirements [features] must be a table")

    lines = contents.splitlines()
    section_start: int | None = None
    section_end = len(lines)
    for index, line in enumerate(lines):
        if _FEATURE_SECTION.match(line):
            section_start = index
            for candidate in range(index + 1, len(lines)):
                if _TABLE_HEADER.match(lines[candidate]):
                    section_end = candidate
                    break
            break

    if features is not None and section_start is None:
        raise CodexCompatibilityError(
            "existing Codex requirements use an unsupported inline/dotted features layout; "
            "refusing to replace managed policy"
        )

    if section_start is None:
        rendered = contents.rstrip()
        if rendered:
            rendered += "\n\n"
        rendered += "[features]\nunified_exec = false\n"
    else:
        replaced = False
        for index in range(section_start + 1, section_end):
            match = _UNIFIED_EXEC.match(lines[index])
            if match:
                lines[index] = f"{match.group('indent')}unified_exec = false"
                replaced = True
                break
        if not replaced:
            lines.insert(section_end, "unified_exec = false")
        rendered = "\n".join(lines).rstrip() + "\n"

    try:
        check = tomllib.loads(rendered)
    except tomllib.TOMLDecodeError as exc:
        raise CodexCompatibilityError(f"generated Codex requirements.toml is invalid: {exc}") from exc
    if (check.get("features") or {}).get("unified_exec") is not False:
        raise CodexCompatibilityError("failed to pin Codex unified_exec=false")
    return rendered


@contextmanager
def codex_system_requirements_overlay() -> Iterator[Path]:
    """Yield a private /etc view with managed Codex requirements injected.

    Bubblewrap cannot create /etc/codex after the host root has been mounted
    read-only when that directory does not already exist. Build a complete /etc
    facade instead: every host /etc entry except codex points at a read-only
    mirror mounted by the caller, while /etc/codex is a private copy containing
    the managed UnifiedExec requirement.
    """

    with tempfile.TemporaryDirectory(prefix="dreadnought-codex-etc-") as raw:
        overlay = Path(raw) / "etc"
        overlay.mkdir(parents=True)

        for entry in CODEX_ETC_DIR.iterdir():
            if entry.name == "codex":
                continue
            (overlay / entry.name).symlink_to(CODEX_ETC_MIRROR / entry.name)

        codex = overlay / "codex"
        if CODEX_SYSTEM_DIR.is_dir():
            shutil.copytree(CODEX_SYSTEM_DIR, codex, symlinks=True)
        else:
            codex.mkdir(parents=True)

        requirements = codex / "requirements.toml"
        existing = requirements.read_text(encoding="utf-8") if requirements.is_file() else ""
        requirements.write_text(pin_unified_exec_requirement(existing), encoding="utf-8")
        yield overlay
