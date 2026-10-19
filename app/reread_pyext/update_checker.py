"""Check the latest stable release published for re/read Desktop."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse


LATEST_RELEASE_API = "https://api.github.com/repos/nvtruongops/reread-pyext/releases/latest"
RELEASE_PAGE = "https://github.com/nvtruongops/reread-pyext/releases/tag/{}"
_VERSION_PATTERN = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


@dataclass(frozen=True)
class UpdateCheckResult:
    latest_version: str
    release_url: str
    update_available: bool
    installer_url: str | None = None
    installer_sha256: str | None = None
    installer_size: int | None = None


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
    installer_url = None
    installer_sha256 = None
    installer_size = None
    if is_newer:
        assets = release.get("assets")
        installer = (
            next(
                (asset for asset in assets if isinstance(asset, dict) and asset.get("name") == "reread_pyext_setup.exe"),
                None,
            )
            if isinstance(assets, list)
            else None
        )
        if installer is None:
            raise ValueError("The latest release does not include reread_pyext_setup.exe.")
        installer_url = str(installer.get("browser_download_url") or "")
        parsed_url = urlparse(installer_url)
        if (
            parsed_url.scheme != "https"
            or parsed_url.hostname != "github.com"
            or Path(parsed_url.path).name != "reread_pyext_setup.exe"
        ):
            raise ValueError("The latest release installer URL is not a valid GitHub download URL.")
        digest = str(installer.get("digest") or "")
        digest_match = re.fullmatch(r"sha256:([0-9a-fA-F]{64})", digest)
        if digest_match is None:
            raise ValueError("The latest release installer has no valid SHA-256 digest.")
        try:
            installer_size = int(installer.get("size"))
        except (TypeError, ValueError):
            installer_size = 0
        if installer_size <= 0:
            raise ValueError("The latest release installer has an invalid file size.")
        installer_sha256 = digest_match.group(1).lower()
    return UpdateCheckResult(
        latest_version=latest_version,
        release_url=RELEASE_PAGE.format(tag),
        update_available=is_newer,
        installer_url=installer_url,
        installer_sha256=installer_sha256,
        installer_size=installer_size,
    )


def download_installer(
    result: UpdateCheckResult,
    destination_dir: str | Path | None = None,
    progress: Callable[[int, int], None] | None = None,
    timeout: float = 30.0,
) -> Path:
    """Download the published setup file and return it only after SHA-256 verification."""
    if not result.update_available or not result.installer_url or not result.installer_sha256 or not result.installer_size:
        raise ValueError("This update result does not contain verified installer metadata.")
    parsed_url = urlparse(result.installer_url)
    if (
        parsed_url.scheme != "https"
        or parsed_url.hostname != "github.com"
        or Path(parsed_url.path).name != "reread_pyext_setup.exe"
    ):
        raise ValueError("The latest release installer URL is not a valid GitHub download URL.")
    if not re.fullmatch(r"[0-9a-f]{64}", result.installer_sha256):
        raise ValueError("The latest release installer has no valid SHA-256 digest.")
    if result.installer_size <= 0:
        raise ValueError("The latest release installer has an invalid file size.")

    output_dir = Path(destination_dir) if destination_dir is not None else Path(tempfile.gettempdir())
    output_dir.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_path = tempfile.mkstemp(prefix="reread-update-", suffix=".exe", dir=output_dir)
    digest = hashlib.sha256()
    received = 0
    try:
        request = urllib.request.Request(
            result.installer_url,
            headers={"User-Agent": "re-read-desktop"},
        )
        with os.fdopen(descriptor, "wb") as output, urllib.request.urlopen(request, timeout=timeout) as response:
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > result.installer_size:
                    raise ValueError("The downloaded installer size does not match the release metadata.")
                digest.update(chunk)
                output.write(chunk)
                if progress:
                    progress(received, result.installer_size)
        if received != result.installer_size:
            raise ValueError("The downloaded installer size does not match the release metadata.")
        if digest.hexdigest() != result.installer_sha256:
            raise ValueError("The downloaded installer SHA-256 does not match the release metadata.")
        return Path(temporary_path)
    except Exception:
        Path(temporary_path).unlink(missing_ok=True)
        raise
