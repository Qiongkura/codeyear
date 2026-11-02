"""Find local git repositories and extract one year of commit data.

Everything runs against the local ``git`` binary; nothing is uploaded.
"""

from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .languages import language_for, normalize_path

SKIP_DIRS: set[str] = {
    ".git", ".svn", ".hg",
    "node_modules", "bower_components", "dist", "build", "out", "output",
    "target", "vendor", "third_party", "third-party", "coverage", "htmlcov",
    ".next", ".nuxt", ".svelte-kit", ".parcel-cache", ".turbo",
    "__pycache__", ".venv", "venv", "env", "site-packages",
    "pods", "deriveddata", ".gradle", ".m2", "obj", "bin",
    "$recycle.bin", "system volume information",
    "codeyear-output", ".testrepo",
}

# A single repo with an enormous history can make one ``git log`` very slow.
# This caps output per repo; it is far above a normal personal year.
MAX_COMMITS_PER_REPO = 50_000


@dataclass
class FileChange:
    path: str
    lang: str
    lines: int


@dataclass
class Commit:
    repo: str
    hash: str
    dt: datetime
    subject: str
    added: int
    deleted: int
    files: int
    author_email: str = ""
    author_name: str = ""
    changes: list[FileChange] = field(default_factory=list)


@dataclass
class RepoResult:
    path: Path
    name: str
    commits: list[Commit] = field(default_factory=list)
    warning: str | None = None
    remote: str | None = None
    readme_line: str | None = None
    root: str | None = None


def find_repos(root: Path, max_depth: int = 6) -> list[Path]:
    """Return git repositories under *root* (or *root* itself if it is one)."""
    root = root.resolve()
    if not root.exists():
        raise FileNotFoundError(f"路径不存在: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"不是文件夹: {root}")

    if (root / ".git").exists():
        return [root]

    repos: list[Path] = []
    base_parts = len(root.parts)

    def _on_error(_err: OSError) -> None:  # pragma: no cover - permission noise
        return None

    for current, dirs, _files in os.walk(root, onerror=_on_error):
        cur = Path(current)
        depth = len(cur.parts) - base_parts
        if depth > max_depth:
            dirs[:] = []
            continue

        dirs[:] = sorted(
            d for d in dirs
            if d.lower() not in SKIP_DIRS and not d.startswith(".")
        )

        if (cur / ".git").exists():
            repos.append(cur)
            # Do not descend into a repo: submodules would double count.
            dirs[:] = []

    return repos


def _repo_name(path: Path, root: Path) -> str:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return path.name
    return rel.as_posix() if str(rel) != "." else path.name


def _parse_int(value: str) -> int:
    if value == "-" or not value:
        return 0
    try:
        return int(value)
    except ValueError:
        return 0


def _build_log_cmd(
    repo_path: Path,
    year: int,
    author: str | None,
    *,
    trust_repo: bool,
) -> list[str]:
    cmd = ["git", "-c", "core.quotepath=false"]
    if trust_repo:
        # Some repos are copies/backups owned by another Windows account.
        # Git refuses to read them unless the exact path is trusted. Scope the
        # trust to this one repo instead of changing the user's global config.
        cmd += ["-c", f"safe.directory={repo_path}"]
    cmd += [
        "-C", str(repo_path),
        "log",
        f"--since={year}-01-01T00:00:00",
        f"--until={year + 1}-01-01T00:00:00",
        "--date=format:%Y-%m-%dT%H:%M:%S",
        "--pretty=format:%x1e%H%x1f%ad%x1f%ae%x1f%an%x1f%s",
        "--numstat",
        "--no-renames",
        "--no-merges",
        f"--max-count={MAX_COMMITS_PER_REPO}",
    ]
    if author:
        cmd.append(f"--author={author}")
    return cmd


def _readme_line(repo_path: Path) -> str | None:
    """First meaningful line of the repo's README — the author's own words."""
    for name in ("README.md", "readme.md", "Readme.md", "README", "README.txt", "README.rst"):
        path = repo_path / name
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for raw in text.splitlines():
            line = raw.strip()
            if not line or line.startswith("<") or line.startswith("!"):
                continue
            line = re.sub(r"[\\#>*`_\[\]()]","", line).strip()
            line = re.sub(r"\s+", " ", line)
            if len(line) >= 6:
                return line[:110]
    return None


def _git_remote(repo_path: Path) -> str | None:
    try:
        proc = subprocess.run(
            ["git", "-c", f"safe.directory={repo_path.as_posix()}",
             "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    url = (proc.stdout or "").strip()
    return url or None


def _git_root(repo_path: Path) -> str | None:
    """First root commit — the shared ancestor of copies of the same project."""
    try:
        proc = subprocess.run(
            ["git", "-c", f"safe.directory={repo_path.as_posix()}",
             "-C", str(repo_path), "rev-list", "--max-parents=0", "HEAD"],
            capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    roots = proc.stdout.strip().splitlines()
    return roots[0].strip() if roots else None


def scan_repo(
    repo_path: Path,
    root: Path,
    year: int,
    *,
    author: str | None = None,
    timeout: int = 300,
) -> RepoResult:
    name = _repo_name(repo_path, root)
    result = RepoResult(path=repo_path, name=name)

    trust_repo = False
    while True:
        cmd = _build_log_cmd(repo_path, year, author, trust_repo=trust_repo)
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except FileNotFoundError:
            result.warning = "找不到 git 命令"
            return result
        except subprocess.TimeoutExpired:
            result.warning = f"扫描超时（>{timeout}s）"
            return result
        except OSError as exc:  # pragma: no cover - rare shell issues
            result.warning = f"无法启动 git: {exc}"
            return result

        if proc.returncode == 0:
            break

        stderr = (proc.stderr or "").strip()
        lower = stderr.lower()
        if not trust_repo and (
            "dubious ownership" in lower
            or "safe.directory" in lower
            or "detected dubious ownership" in lower
        ):
            trust_repo = True
            continue
        if "not a git repository" in lower:
            # A stray .git file/dir inside a vendored dependency. Nothing to
            # report: it is not a broken user repository.
            return result

        lines = stderr.splitlines()
        result.warning = lines[-1] if lines else f"git exited {proc.returncode}"
        return result

    result.remote = _git_remote(repo_path)
    result.readme_line = _readme_line(repo_path)
    result.root = _git_root(repo_path)

    if not proc.stdout.strip():
        return result

    for chunk in proc.stdout.split("\x1e"):
        chunk = chunk.strip("\n")
        if not chunk.strip():
            continue

        lines = chunk.splitlines()
        header = lines[0].split("\x1f", 4)
        if len(header) < 5:
            continue

        commit_hash, date_s, author_email, author_name, subject = header
        try:
            dt = datetime.strptime(date_s, "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            continue
        if dt.year != year:
            continue

        added_total = 0
        deleted_total = 0
        files = 0
        changes: list[FileChange] = []

        for line in lines[1:]:
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            added = _parse_int(parts[0])
            deleted = _parse_int(parts[1])
            path = normalize_path("\t".join(parts[2:]))
            files += 1
            added_total += added
            deleted_total += deleted

            lang = language_for(path)
            if lang is None:
                continue
            changes.append(FileChange(path=path, lang=lang, lines=added + deleted))

        result.commits.append(
            Commit(
                repo=name,
                hash=commit_hash,
                dt=dt,
                subject=subject.strip(),
                added=added_total,
                deleted=deleted_total,
                files=files,
                author_email=author_email.strip(),
                author_name=author_name.strip(),
                changes=changes,
            )
        )

    return result
