"""Lightweight, zero-dependency version checker and in-app updater.

Design principles:
- Never block startup or fail noisy when offline.
- Prefer static CDN endpoints (GitHub Pages ``version.json`` / PyPI JSON) over
  rate-limited GitHub REST API calls.
- On Windows ``CodeYear.exe`` builds, update atomically in-place via
  ``os.replace`` (renaming the running executable to ``.old`` and moving the
  verified download into place) without spawning ``.cmd`` / PowerShell scripts.
"""

from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

from packaging.version import InvalidVersion, Version

from . import __version__, i18n

VERSION_JSON_URL = "https://qiongkura.github.io/codeyear/version.json"
PYPI_JSON_URL = "https://pypi.org/pypi/codeyear/json"
GITHUB_LATEST_URL = (
    "https://api.github.com/repos/Qiongkura/codeyear/releases/latest"
)
RELEASE_BASE = "https://github.com/Qiongkura/codeyear/releases"
MAX_DOWNLOAD_BYTES = 150 * 1024 * 1024
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def parse_version(version: str) -> tuple[int, ...]:
    """Return the historical numeric fallback representation of a version.

    This helper remains tuple-shaped for callers that used the old public
    behavior.  Update decisions use :mod:`packaging` below so prereleases and
    post/dev releases follow PEP 440 rather than losing their ordering.
    """
    cleaned = (version or "").strip().lstrip("vV")
    parts = re.findall(r"\d+", cleaned)
    return tuple(int(p) for p in parts) if parts else (0,)


def _version_is_newer(latest: str, current: str) -> bool:
    """Compare PEP 440 versions; reject invalid version metadata."""
    try:
        return Version(latest.strip()) > Version(current.strip())
    except (InvalidVersion, AttributeError):
        return False


def is_frozen() -> bool:
    """True when running inside a PyInstaller single-file executable."""
    return bool(getattr(sys, "frozen", False))


def cleanup_old_executable(exe_path: Path | None = None) -> bool:
    """Remove ``CodeYear.exe.old`` left over from a previous in-app update."""
    target = exe_path or (Path(sys.executable) if is_frozen() else None)
    if target is None:
        return False
    old_path = target.with_suffix(target.suffix + ".old")
    if not old_path.exists():
        return False
    with contextlib.suppress(OSError):
        old_path.unlink()
        return True
    return False


def _fetch_json(url: str, timeout: float) -> dict | None:
    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": f"CodeYear/{__version__}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            data = json.loads(body)
            return data if isinstance(data, dict) else None
    except (OSError, ValueError, urllib.error.URLError):
        return None


def _build_release_info(
    current: str, latest: str, notes: str = ""
) -> dict:
    clean_latest = latest.strip().lstrip("vV")
    tag = f"v{clean_latest}"
    dl_base = f"{RELEASE_BASE}/download/{tag}"
    return {
        "current": current.strip().lstrip("vV"),
        "latest": clean_latest,
        "has_update": _version_is_newer(clean_latest, current),
        "url": f"{RELEASE_BASE}/tag/{tag}",
        "exe_url": f"{dl_base}/CodeYear.exe",
        "wheel_url": f"{dl_base}/codeyear-{clean_latest}-py3-none-any.whl",
        "sums_url": f"{dl_base}/SHA256SUMS.txt",
        "notes": (notes or "").strip(),
    }


def check_update(
    current_version: str = __version__,
    *,
    timeout: float = 3.0,
) -> dict | None:
    """Return release metadata dict or ``None`` if all endpoints fail."""
    # 1. Static Pages JSON (Fastly CDN, no API rate limit).
    data = _fetch_json(VERSION_JSON_URL, timeout)
    if data and isinstance(data.get("version"), str) and data["version"].strip():
        return _build_release_info(
            current_version,
            data["version"],
            str(data.get("notes") or ""),
        )

    # 2. PyPI JSON endpoint (Fastly CDN, no rate limit).
    data = _fetch_json(PYPI_JSON_URL, timeout)
    info = data.get("info") if isinstance(data, dict) else None
    if isinstance(info, dict) and isinstance(info.get("version"), str):
        return _build_release_info(current_version, info["version"])

    # 3. GitHub Releases API fallback.
    data = _fetch_json(GITHUB_LATEST_URL, timeout)
    if data and isinstance(data.get("tag_name"), str):
        return _build_release_info(
            current_version,
            data["tag_name"],
            str(data.get("body") or ""),
        )
    return None


def verify_sha256(
    file_path: Path, expected_name: str, sums_text: str
) -> bool:
    """Verify ``file_path`` against ``SHA256SUMS.txt`` content."""
    expected_hash: str | None = None
    for line in (sums_text or "").splitlines():
        parts = line.strip().split()
        if len(parts) >= 2:
             digest = parts[0].strip().lower()
             name = parts[-1].lstrip("*./").strip()
             if name == expected_name and re.fullmatch(r"[0-9a-f]{64}", digest):
                 expected_hash = digest
                 break
    if not expected_hash:
        return False
    h = hashlib.sha256()
    with file_path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest().lower() == expected_hash


def replace_running_executable(
    new_file: Path, target_exe: Path | None = None
) -> Path:
    """Atomically swap ``new_file`` into ``target_exe`` without batch scripts."""
    target = (target_exe or Path(sys.executable)).resolve()
    old_path = target.with_suffix(target.suffix + ".old")
    if old_path.exists():
        with contextlib.suppress(OSError):
            old_path.unlink()
    os.replace(target, old_path)
    try:
        os.replace(new_file, target)
    except Exception:
        with contextlib.suppress(OSError):
            os.replace(old_path, target)
        raise
    return target


def _download_bytes(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(
        url, headers={"User-Agent": f"CodeYear/{__version__}"}
    )
    chunks: list[bytes] = []
    total = 0
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        while True:
            chunk = resp.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > MAX_DOWNLOAD_BYTES:
                raise ValueError("download exceeds maximum allowed size")
            chunks.append(chunk)
    return b"".join(chunks)


def perform_update(
    info: dict | None = None,
    *,
    timeout: float = 60.0,
) -> tuple[bool, str]:
    """Download and apply the latest update for either frozen exe or pip."""
    if info is None:
        info = check_update(timeout=min(timeout, 10.0))
    if not info:
        return False, i18n.tr("无法连接更新服务器，请检查网络。")
    if not info.get("has_update"):
        return True, i18n.tr(
            "当前已是最新版本（v{version}）。", version=info["current"]
        )

    latest = info["latest"]
    if is_frozen():
        target = Path(sys.executable).resolve()
        tmp_path = target.with_suffix(target.suffix + ".tmp")
        try:
            payload = _download_bytes(info["exe_url"], timeout=timeout)
            tmp_path.write_bytes(payload)
            try:
                sums_text = _download_bytes(
                    info["sums_url"], timeout=15.0
                ).decode("utf-8", errors="replace")
            except Exception as exc:
                tmp_path.unlink(missing_ok=True)
                return False, i18n.tr(
                    "无法下载校验文件，已取消更新: {exc}", exc=exc
                )
            if not verify_sha256(
                tmp_path, "CodeYear.exe", sums_text
            ):
                tmp_path.unlink(missing_ok=True)
                return False, i18n.tr("安装包 SHA256 校验未通过，已取消更新。")
            replace_running_executable(tmp_path, target)
            return True, i18n.tr(
                "已更新到 v{version}，重新打开软件即可生效。", version=latest
            )
        except Exception as exc:
            tmp_path.unlink(missing_ok=True)
            return False, i18n.tr("更新失败: {exc}", exc=exc)

    # Python / pip environment: download and verify wheel SHA256 before install.
    wheel_name = f"codeyear-{latest}-py3-none-any.whl"
    with tempfile.TemporaryDirectory(prefix="codeyear-upd-") as tmp_dir:
        wheel_path = Path(tmp_dir) / wheel_name
        try:
            wheel_bytes = _download_bytes(info["wheel_url"], timeout=timeout)
            wheel_path.write_bytes(wheel_bytes)
            sums_url = info.get("sums_url")
            if sums_url:
                try:
                    sums_text = _download_bytes(sums_url, timeout=15.0).decode(
                        "utf-8", errors="replace"
                    )
                except Exception as exc:
                    return False, i18n.tr(
                        "无法下载校验文件，已取消更新: {exc}", exc=exc
                    )
                if not verify_sha256(wheel_path, wheel_name, sums_text):
                    return False, i18n.tr("安装包 SHA256 校验未通过，已取消更新。")
        except Exception as exc:
            return False, i18n.tr("更新失败: {exc}", exc=exc)

        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--upgrade",
                str(wheel_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            creationflags=_NO_WINDOW,
        )
    if proc.returncode == 0:
        return True, i18n.tr("已更新到 v{version}。", version=latest)
    err = (proc.stderr or proc.stdout or "pip install failed").strip()
    if "externally-managed-environment" in err:
        return False, i18n.tr(
            "当前为系统受管 Python 环境（PEP 668），请使用 pipx upgrade codeyear 或虚拟环境更新。"
        )
    if "No module named pip" in err:
        return False, i18n.tr(
            "当前 Python 环境未包含 pip，请使用包管理器（如 uv tool upgrade codeyear）更新。"
        )
    return False, i18n.tr("更新失败: {exc}", exc=err.splitlines()[-1])
