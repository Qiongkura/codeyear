"""Optionally write the GitHub profile card into a local profile repo.

No network access happens unless ``push=True``. Even then, only the card
SVGs and the profile README are committed; the report and raw JSON stay
on this machine.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
        creationflags=_NO_WINDOW,
    )


def _latest_version(repo: Path, year: int) -> tuple[int, Path | None]:
    pattern = re.compile(rf"^codeyear-{year}-card-v(\d+)\.svg$")
    found: list[tuple[int, Path]] = []
    for path in repo.iterdir():
        match = pattern.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    if not found:
        return 0, None
    return max(found, key=lambda item: item[0])


def update_profile(
    repo_path: str | Path,
    year: int,
    light_card: str | Path,
    dark_card: str | Path,
    *,
    push: bool = False,
) -> tuple[Path, bool, bool]:
    """Update a local profile repo.

    Returns ``(repo, changed, pushed)``. Without ``push=True`` the working
    tree is updated but nothing is committed or sent anywhere.
    """

    repo = Path(repo_path).expanduser().resolve()
    if not (repo / ".git").exists():
        raise FileNotFoundError(f"不是 git 仓库: {repo}")

    light = Path(light_card)
    dark = Path(dark_card)
    if not light.exists() or not dark.exists():
        raise FileNotFoundError("找不到卡片文件，请先生成卡片")

    version, latest_light = _latest_version(repo, year)
    if latest_light is not None:
        latest_dark = repo / f"codeyear-{year}-card-v{version}-dark.svg"
        if (
            latest_dark.exists()
            and latest_light.read_bytes() == light.read_bytes()
            and latest_dark.read_bytes() == dark.read_bytes()
        ):
            return repo, False, False

    version += 1
    light_name = f"codeyear-{year}-card-v{version}.svg"
    dark_name = f"codeyear-{year}-card-v{version}-dark.svg"
    shutil.copy2(light, repo / light_name)
    shutil.copy2(dark, repo / dark_name)

    readme = repo / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    text = re.sub(rf"codeyear-{year}-card-v\d+-dark\.svg", dark_name, text)
    text = re.sub(rf"codeyear-{year}-card-v\d+\.svg", light_name, text)
    text = re.sub(rf"codeyear-{year}-card-dark\.svg", dark_name, text)
    text = re.sub(rf"codeyear-{year}-card\.svg", light_name, text)
    if light_name not in text:
        block = (
            '<p align="center">\n'
            "  <picture>\n"
            f'    <source media="(prefers-color-scheme: dark)" '
            f'srcset="./{dark_name}">\n'
            f'    <img src="./{light_name}" width="640" '
            f'alt="CodeYear {year}">\n'
            "  </picture>\n"
            "</p>\n"
        )
        text = text.rstrip() + "\n\n" + block
    readme.write_text(text, encoding="utf-8")

    pushed = False
    if push:
        _git(repo, "add", "README.md", light_name, dark_name)
        status = _git(repo, "status", "--porcelain")
        if status.stdout.strip():
            commit = _git(
                repo, "commit", "-m", f"Update CodeYear {year} card to v{version}"
            )
            if commit.returncode != 0:
                raise RuntimeError((commit.stderr or "git commit failed").strip())
            push_result = _git(repo, "push")
            if push_result.returncode != 0:
                raise RuntimeError((push_result.stderr or "git push failed").strip())
            pushed = True
    return repo, True, pushed
