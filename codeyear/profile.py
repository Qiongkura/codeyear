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


def _push_target(repo: Path) -> tuple[str, str, str]:
    """Verify the remote branch exactly matches HEAD before modifying anything."""
    branch = _git(repo, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch.returncode != 0 or not branch.stdout.strip():
        raise RuntimeError("Cannot push profile: HEAD must be on a branch with an upstream")
    name = branch.stdout.strip()
    remote = _git(repo, "config", "--get", f"branch.{name}.remote")
    merge = _git(repo, "config", "--get-all", f"branch.{name}.merge")
    remote_name = remote.stdout.strip()
    refs = merge.stdout.splitlines()
    if (remote.returncode != 0 or not remote_name or remote_name == "."
            or merge.returncode != 0 or len(refs) != 1
            or not refs[0].startswith("refs/heads/")):
        raise RuntimeError("Cannot push profile: configure a single remote upstream branch")
    head = _git(repo, "rev-parse", "--verify", "HEAD")
    if head.returncode != 0:
        raise RuntimeError("Cannot push profile: no existing HEAD commit")
    # Use this exact push URL and branch explicitly, regardless of push.default
    # or remote.pushDefault. Multiple push URLs cannot be checked atomically.
    urls = _git(repo, "remote", "get-url", "--push", "--all", remote_name)
    if urls.returncode != 0 or len(urls.stdout.splitlines()) != 1:
        raise RuntimeError("Cannot push profile: configure exactly one push URL")
    url = urls.stdout.strip()
    remote_ref = _git(repo, "ls-remote", "--exit-code", "--refs", url, refs[0])
    lines = remote_ref.stdout.splitlines()
    if remote_ref.returncode != 0 or len(lines) != 1:
        raise RuntimeError("Cannot push profile: cannot verify the remote upstream branch")
    fields = lines[0].split()
    if len(fields) != 2 or fields[1] != refs[0] or fields[0] != head.stdout.strip():
        raise RuntimeError("Cannot push profile: local HEAD differs from remote upstream; "
                           "resolve existing unpushed or incoming commits first")
    return url, refs[0], fields[0]


def _push(repo: Path, url: str, ref: str, old_head: str) -> None:
    """Push only our commit, if the verified remote ref has not changed."""
    commit = _git(repo, "rev-parse", "--verify", "HEAD")
    parents = _git(repo, "rev-list", "--parents", "-n", "1", "HEAD")
    parts = parents.stdout.split()
    if (commit.returncode != 0 or parents.returncode != 0 or len(parts) != 2
            or parts[0] != commit.stdout.strip() or parts[1] != old_head):
        raise RuntimeError("Cannot push profile: HEAD changed since verification")
    result = _git(repo, "push", url, f"{parts[0]}:{ref}")
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "git push failed").strip())


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

    if push:
        # A normal git commit includes the entire index, not just paths we add.
        # Refuse before modifying files so existing staged work cannot be pushed.
        staged = _git(repo, "diff", "--cached", "--quiet")
        if staged.returncode == 1:
            raise RuntimeError("Cannot push profile with existing staged changes")
        if staged.returncode != 0:
            raise RuntimeError((staged.stderr or "git diff failed").strip())
        dirty = _git(
            repo, "status", "--porcelain", "--untracked-files=all", "--",
            "README.md", ":(glob)**/codeyear-*.svg",
        )
        if dirty.returncode != 0:
            raise RuntimeError((dirty.stderr or "git status failed").strip())
        if dirty.stdout.strip():
            raise RuntimeError("Cannot push profile with existing README or card changes")
        push_target = _push_target(repo)

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
                        "codeyear-*-card-dark.svg",
                        "codeyear-*-card-en-v*.svg",
                        "codeyear-*-card-en.svg",
                        "codeyear-*-card-en-dark.svg"):
            for old in directory.glob(pattern):
                if old not in keep:
                    old.unlink(missing_ok=True)

    # Replace any year's card reference so a new year also takes over the
    # README instead of appending a second card block. The path prefix (e.g.
    # "./assets/") is left intact, so subdirectory layouts keep working.
    # English filenames are handled too, so switching --lang does not append
    # a second card block next to the old one.
    text = re.sub(r"codeyear-\d{4}-card-en-v\d+-dark\.svg", dark_name, text)
    text = re.sub(r"codeyear-\d{4}-card-en-v\d+\.svg", light_name, text)
    text = re.sub(r"codeyear-\d{4}-card-en-dark\.svg", dark_name, text)
    text = re.sub(r"codeyear-\d{4}-card-en\.svg", light_name, text)
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
        added = _git(repo, "add", "-A", "README.md", ":(glob)**/codeyear-*.svg")
        if added.returncode != 0:
            raise RuntimeError((added.stderr or "git add failed").strip())
        staged = _git(repo, "diff", "--cached", "--name-only")
        if staged.returncode != 0:
            raise RuntimeError((staged.stderr or "git diff failed").strip())
        if staged.stdout.strip():
            commit = _git(
                repo, "commit", "-m", f"Update CodeYear {year} card to v{version}"
            )
            if commit.returncode != 0:
                raise RuntimeError((commit.stderr or "git commit failed").strip())
            _push(repo, *push_target)
            pushed = True
    return repo, True, pushed
