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


def _latest_version(directory: Path, year: int) -> tuple[int, Path | None]:
    pattern = re.compile(rf"^codeyear-{year}-card-v(\d+)\.svg$")
    found: list[tuple[int, Path]] = []
    for path in directory.iterdir():
        match = pattern.match(path.name)
        if match:
            found.append((int(match.group(1)), path))
    if not found:
        return 0, None
    return max(found, key=lambda item: item[0])


def _card_dir(text: str) -> str:
    """Directory used by the existing README card reference, if any."""
    match = re.search(
        r'(?:src|srcset)="(?:\./)?([^"]*/)?codeyear-\d{4}-card[^"]*\.svg[^"]*"',
        text,
    )
    if not match:
        return ""
    prefix = (match.group(1) or "").strip("/")
    if not prefix or prefix.startswith(("http:", "https:")):
        return ""
    return prefix


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

    readme = repo / "README.md"
    text = readme.read_text(encoding="utf-8") if readme.exists() else ""
    rel_dir = _card_dir(text)
    target = repo
    if rel_dir:
        candidate = (repo / rel_dir).resolve()
        try:
            candidate.relative_to(repo)
            target = candidate
        except ValueError:  # README path escapes the repo; stay at the root
            target = repo
    target.mkdir(parents=True, exist_ok=True)

    version, latest_light = _latest_version(target, year)
    if latest_light is not None:
        latest_dark = target / f"codeyear-{year}-card-v{version}-dark.svg"
        if (
            latest_dark.exists()
            and latest_light.read_bytes() == light.read_bytes()
            and latest_dark.read_bytes() == dark.read_bytes()
        ):
            return repo, False, False

    version += 1
    light_name = f"codeyear-{year}-card-v{version}.svg"
    dark_name = f"codeyear-{year}-card-v{version}-dark.svg"
    shutil.copy2(light, target / light_name)
    shutil.copy2(dark, target / dark_name)
    # Only the newest version stays referenced; drop older versioned files so
    # a daily/weekly Action does not accumulate one SVG pair per run. Also
    # remove unversioned cards left by the old fixed-filename workflow.
    keep = {target / light_name, target / dark_name}
    for directory in {repo, target}:
        for pattern in ("codeyear-*-card-v*.svg", "codeyear-*-card.svg",
                        "codeyear-*-card-dark.svg"):
            for old in directory.glob(pattern):
                if old not in keep:
                    old.unlink(missing_ok=True)

    # Replace any year's card reference so a new year also takes over the
    # README instead of appending a second card block. The path prefix (e.g.
    # "./assets/") is left intact, so subdirectory layouts keep working.
    text = re.sub(r"codeyear-\d{4}-card-v\d+-dark\.svg", dark_name, text)
    text = re.sub(r"codeyear-\d{4}-card-v\d+\.svg", light_name, text)
    text = re.sub(r"codeyear-\d{4}-card-dark\.svg", dark_name, text)
    text = re.sub(r"codeyear-\d{4}-card\.svg", light_name, text)
    text = re.sub(r'alt="CodeYear \d{4}"', f'alt="CodeYear {year}"', text)
    if light_name not in text:
        prefix = f"./{rel_dir}/" if rel_dir else "./"
        block = (
            '<p align="center">\n'
            "  <picture>\n"
            f'    <source media="(prefers-color-scheme: dark)" '
            f'srcset="{prefix}{dark_name}">\n'
            f'    <img src="{prefix}{light_name}" width="640" '
            f'alt="CodeYear {year}">\n'
            "  </picture>\n"
            "</p>\n"
        )
        text = text.rstrip() + "\n\n" + block
    readme.write_text(text, encoding="utf-8")

    pushed = False
    if push:
        # -A is required so the old versioned files removed above are staged
        # as deletions too; glob magic covers cards in nested asset folders.
        _git(repo, "add", "-A", "README.md", ":(glob)**/codeyear-*.svg")
        staged = _git(repo, "diff", "--cached", "--name-only")
        if staged.stdout.strip():
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
