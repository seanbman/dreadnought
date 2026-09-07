from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass

RELEASES_URL = "https://api.github.com/repos/seanbman/dreadnought/releases?per_page=20"
REPOSITORY = "https://github.com/seanbman/dreadnought.git"
DISABLE_ENV = "DREADNOUGHT_NO_UPDATE_CHECK"

_VERSION_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)(?:(a|b|rc)(\d+))?$")
_STAGE_RANK = {"a": 0, "b": 1, "rc": 2, None: 3}


@dataclass(frozen=True)
class ReleaseInfo:
    tag: str
    version: str
    html_url: str
    prerelease: bool


def _key(version: str) -> tuple[int, int, int, int, int]:
    match = _VERSION_RE.match(version.strip())
    if not match:
        raise ValueError(f"unsupported version: {version}")
    major, minor, patch = map(int, match.group(1, 2, 3))
    stage = match.group(4)
    serial = int(match.group(5) or 0)
    return major, minor, patch, _STAGE_RANK[stage], serial


def latest_release(*, timeout: float = 2.0) -> ReleaseInfo | None:
    request = urllib.request.Request(
        RELEASES_URL,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "dreadnought-update-check"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            releases = json.load(response)
    except (OSError, urllib.error.URLError, json.JSONDecodeError):
        return None
    candidates: list[ReleaseInfo] = []
    for release in releases:
        if release.get("draft"):
            continue
        tag = str(release.get("tag_name") or "")
        try:
            _key(tag)
        except ValueError:
            continue
        candidates.append(
            ReleaseInfo(
                tag=tag,
                version=tag.removeprefix("v"),
                html_url=str(release.get("html_url") or ""),
                prerelease=bool(release.get("prerelease")),
            )
        )
    return max(candidates, key=lambda item: _key(item.version), default=None)


def update_available(current_version: str, release: ReleaseInfo | None) -> bool:
    if release is None:
        return False
    try:
        return _key(release.version) > _key(current_version)
    except ValueError:
        return False


def install_release(tag: str | None = None, *, timeout: float = 8.0) -> str:
    release = None
    if tag is None:
        release = latest_release(timeout=timeout)
        if release is None:
            raise RuntimeError("could not resolve a published Dreadnought release")
        tag = release.tag
    else:
        _key(tag)
        if not tag.startswith("v"):
            tag = f"v{tag}"
    spec = f"git+{REPOSITORY}@{tag}"
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "install", "--upgrade", spec],
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"pip update failed with exit code {completed.returncode}")
    return tag


def maybe_notify(current_version: str) -> None:
    if os.environ.get(DISABLE_ENV) or not sys.stderr.isatty():
        return
    release = latest_release()
    if update_available(current_version, release):
        assert release is not None
        print(
            f"Dreadnought {release.tag} is available (installed {current_version}). "
            "Run `dreadnought update` or rerun install.sh.",
            file=sys.stderr,
        )
