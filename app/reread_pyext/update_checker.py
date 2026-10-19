"""Check the latest stable release published for re/read Desktop."""

from __future__ import annotations

import json
import re
import urllib.request
from dataclasses import dataclass


LATEST_RELEASE_API = "https://api.github.com/repos/nvtruongops/reread-pyext/releases/latest"
RELEASE_PAGE = "https://github.com/nvtruongops/reread-pyext/releases/tag/{}"
_VERSION_PATTERN = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True)
class UpdateCheckResult:
    latest_version: str
    release_url: str
    update_available: bool


def _version_key(value: str) -> tuple[int, int, int]:
    match = _VERSION_PATTERN.fullmatch(value.strip())
    if match is None:
        raise ValueError(f"Unsupported release version: {value}")
    return tuple(map(int, match.groups()))


def check_for_update(current_version: str, timeout: float = 8.0) -> UpdateCheckResult:
    request = urllib.request.Request(
        LATEST_RELEASE_API,
        headers={"Accept": "application/vnd.github+json", "User-Agent": "re-read-desktop"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        release = json.loads(response.read().decode("utf-8"))

    if not isinstance(release, dict):
        raise ValueError("GitHub returned an invalid release response.")
    tag = str(release.get("tag_name") or "").strip()
    latest_version = tag.removeprefix("v")
    is_newer = _version_key(latest_version) > _version_key(current_version)
    return UpdateCheckResult(
        latest_version=latest_version,
        release_url=RELEASE_PAGE.format(tag),
        update_available=is_newer,
    )
