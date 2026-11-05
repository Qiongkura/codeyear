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
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


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
    root_dt: datetime | None = None
    total_commits: int = 0
    tags_in_year: int = 0


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
    since_year: int | None = None,
    trust_repo: bool,
    use_mailmap: bool = True,
    all_branches: bool = False,
) -> list[str]:
    start_year = since_year if since_year is not None else year
    cmd = ["git", "-c", "core.quotepath=false"]
    if trust_repo:
        # Some repos are copies/backups owned by another Windows account.
        # Git refuses to read them unless the exact path is trusted. Scope the
        # trust to this one repo instead of changing the user's global config.
        cmd += ["-c", f"safe.directory={repo_path}"]
    mailmap = use_mailmap and (repo_path / ".mailmap").exists()
    name_fmt = "%aN" if mailmap else "%an"
    email_fmt = "%aE" if mailmap else "%ae"
    cmd += [
        "-C", str(repo_path),
        "log",
        f"--since={start_year}-01-01T00:00:00",
        f"--until={year + 1}-01-01T00:00:00",
        "--date=format:%Y-%m-%dT%H:%M:%S",
        f"--pretty=format:%x1e%H%x1f%ad%x1f{email_fmt}%x1f{name_fmt}%x1f%s",
        "--numstat",
        "--no-renames",
        "--no-merges",
        f"--max-count={MAX_COMMITS_PER_REPO}",
    ]
    if all_branches:
        cmd.append("--all")
    if author:
        cmd.append(f"--author={author}")
    if mailmap:
        # Git's canonical identity mapping: old emails/names collapse into the
        # current one without requiring --alias on every run.
        cmd.append("--use-mailmap")
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


_ORIGIN_SECTION_RE = re.compile(
    r'^\[remote\s+"origin"\]\s*$([\s\S]*?)(?=^\[|\Z)', re.M
)
_ORIGIN_URL_RE = re.compile(r"^\s*url\s*=\s*(.+)$", re.M)


def _git_remote(repo_path: Path) -> str | None:
    git_cfg = repo_path / ".git" / "config"
    if git_cfg.is_file():
        try:
            cfg_text = git_cfg.read_text(encoding="utf-8", errors="replace")
            sec = _ORIGIN_SECTION_RE.search(cfg_text)
            if sec:
                m = _ORIGIN_URL_RE.search(sec.group(1))
                if m:
                    url = m.group(1).strip()
                    if url:
                        return url
            else:
                return None
        except OSError:
            pass
    try:
        proc = subprocess.run(
            ["git", "-c", f"safe.directory={repo_path.as_posix()}",
             "-C", str(repo_path), "remote", "get-url", "origin"],
            capture_output=True, creationflags=_NO_WINDOW,
            text=True, encoding="utf-8",
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
            capture_output=True, creationflags=_NO_WINDOW,
            text=True, encoding="utf-8",
            errors="replace", timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    roots = proc.stdout.strip().splitlines()
    return roots[0].strip() if roots else None


def _git_text(repo_path: Path, args: list[str], timeout: int = 30) -> str:
    """Run a small read-only git command; failures degrade to empty output."""
    try:
        proc = subprocess.run(
            ["git", "-c", f"safe.directory={repo_path.as_posix()}",
             "-C", str(repo_path), *args],
            capture_output=True, creationflags=_NO_WINDOW,
            text=True, encoding="utf-8",
            errors="replace", timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return (proc.stdout or "").strip() if proc.returncode == 0 else ""


def _git_root_date(repo_path: Path, root_hash: str) -> datetime | None:
    value = _git_text(
        repo_path,
        ["show", "-s", "--format=%ad", "--date=format:%Y-%m-%dT%H:%M:%S", root_hash],
    )
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%S")
    except ValueError:
        return None


def _git_total_commits(repo_path: Path) -> int:
    """All commits on HEAD — repository scope, not the filtered year scope."""
    value = _git_text(repo_path, ["rev-list", "--count", "HEAD"])
    try:
        return int(value)
    except ValueError:
        return 0


def _git_root_info(repo_path: Path) -> tuple[str | None, datetime | None]:
    """Fetch both root commit hash and its author date in one git call."""
    value = _git_text(
        repo_path,
        [
            "rev-list", "--max-parents=0",
            "--format=%ad", "--date=format:%Y-%m-%dT%H:%M:%S", "HEAD",
        ],
    )
    if not value:
        return None, None
    lines = [line.strip() for line in value.splitlines() if line.strip()]
    root_hash: str | None = None
    root_dt: datetime | None = None
    for idx, line in enumerate(lines):
        if line.startswith("commit "):
            candidate = line[7:].strip()
            if candidate:
                root_hash = candidate
                if idx + 1 < len(lines):
                    try:
                        root_dt = datetime.strptime(
                            lines[idx + 1], "%Y-%m-%dT%H:%M:%S"
                        )
                    except ValueError:
                        root_dt = None
                break
    return root_hash, root_dt


def _has_any_tags(repo_path: Path) -> bool:
    git_dir = repo_path / ".git"
    if not git_dir.is_dir():
        return True
    tags_dir = git_dir / "refs" / "tags"
    try:
        if tags_dir.is_dir() and any(tags_dir.iterdir()):
            return True
    except OSError:
        return True
    packed = git_dir / "packed-refs"
    if packed.is_file():
        try:
            return "refs/tags/" in packed.read_text(
                encoding="utf-8", errors="replace"
            )
        except OSError:
            return True
    return False


def _git_tags_in_year(repo_path: Path, year: int) -> int:
    if not _has_any_tags(repo_path):
        return 0
    value = _git_text(repo_path, ["for-each-ref", "--format=%(creatordate:short)", "refs/tags"])
    prefix = f"{year}-"
    return sum(1 for line in value.splitlines() if line.strip().startswith(prefix))


def scan_repo(
    repo_path: Path,
    root: Path,
    year: int,
    *,
    since_year: int | None = None,
    author: str | None = None,
    timeout: int = 300,
    use_mailmap: bool = True,
    all_branches: bool = False,
) -> RepoResult:
    start_year = since_year if since_year is not None else year
    name = _repo_name(repo_path, root)
    result = RepoResult(path=repo_path, name=name)

    trust_repo = False
    while True:
        cmd = _build_log_cmd(
            repo_path, year, author,
            since_year=since_year,
            trust_repo=trust_repo, use_mailmap=use_mailmap,
            all_branches=all_branches,
        )
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                creationflags=_NO_WINDOW,
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
    result.readme_line = _readme_line(repo_path) if proc.stdout.strip() else None
    result.root, result.root_dt = _git_root_info(repo_path)
    result.total_commits = _git_total_commits(repo_path)
    result.tags_in_year = _git_tags_in_year(repo_path, year)

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
        if not (start_year <= dt.year <= year):
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
