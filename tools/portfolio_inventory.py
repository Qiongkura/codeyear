"""Inventory every project under I:\\projects for the portfolio summary.

This is a local analysis helper, not part of CodeYear's core CLI.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT = Path(r"I:\projects")
OUT = Path(r"I:\projects\codeyear\out-portfolio")

SKIP_DIRS = {
    ".git", ".svn", ".hg", "node_modules", "bower_components", "dist", "build",
    "out", "output", "target", "vendor", "third_party", "third-party",
    "coverage", "htmlcov", ".next", ".nuxt", ".svelte-kit", ".parcel-cache",
    ".turbo", "__pycache__", ".venv", "venv", "env", "site-packages",
    "pods", "deriveddata", ".gradle", ".m2", "obj", "bin", "logs", "backups",
    ".pio", "sdkconfig", "managed_components", "dependencies",
}

NON_CODE_LANGS = {
    "Markdown", "MDX", "reStructuredText", "TeX", "JSON", "YAML", "TOML",
    "INI", "Config", "Jupyter",
}

MAX_FILE_BYTES = 3_000_000

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from codeyear.languages import language_for, is_skipped  # noqa: E402


def read_headline(project: Path) -> str:
    for name in ("README.md", "readme.md", "README_CN.md", "README.en.md", "README.txt"):
        p = project / name
        if p.exists():
            try:
                lines = [
                    line.strip()
                    for line in p.read_text(encoding="utf-8", errors="replace").splitlines()
                    if line.strip()
                ]
            except OSError:
                return ""
            return " / ".join(lines[:3])[:240]
    return ""


def count_files(project: Path) -> dict:
    lang_files: Counter[str] = Counter()
    lang_lines: Counter[str] = Counter()
    files = 0
    total_lines = 0
    total_bytes = 0
    biggest: list[tuple[str, int]] = []
    latest = 0.0

    for current, dirs, filenames in os.walk(project):
        dirs[:] = [
            d for d in dirs
            if d.lower() not in SKIP_DIRS and not d.startswith(".")
        ]
        for filename in filenames:
            fp = Path(current) / filename
            try:
                rel = fp.relative_to(project).as_posix()
            except ValueError:
                continue
            if is_skipped(rel):
                continue
            lang = language_for(rel)
            if not lang:
                continue
            try:
                stat = fp.stat()
            except OSError:
                continue
            if stat.st_size > MAX_FILE_BYTES:
                continue
            try:
                text = fp.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            line_count = sum(1 for line in text.splitlines() if line.strip())
            files += 1
            total_lines += line_count
            total_bytes += stat.st_size
            latest = max(latest, stat.st_mtime)
            lang_files[lang] += 1
            lang_lines[lang] += line_count
            biggest.append((rel, line_count))
            biggest.sort(key=lambda item: -item[1])
            biggest = biggest[:8]

    code_lines = sum(n for lang, n in lang_lines.items() if lang not in NON_CODE_LANGS)
    doc_lines = sum(lang_lines.get(lang, 0) for lang in NON_CODE_LANGS)
    return {
        "files": files,
        "lines": total_lines,
        "code_lines": code_lines,
        "doc_lines": doc_lines,
        "bytes": total_bytes,
        "languages": lang_lines.most_common(8),
        "file_types": lang_files.most_common(8),
        "biggest_files": biggest,
        "latest_mtime": datetime.fromtimestamp(latest).isoformat(timespec="seconds") if latest else None,
    }


def git_run(project: Path, args: list[str]) -> str:
    cmd = [
        "git", "-c", f"safe.directory={project.as_posix()}",
        "-C", str(project), *args,
    ]
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True,
            encoding="utf-8", errors="replace", timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout.strip()


def git_info(project: Path) -> dict:
    if not (project / ".git").exists():
        return {}
    count = git_run(project, ["rev-list", "--count", "HEAD"])
    root = git_run(project, ["rev-list", "--max-parents=0", "HEAD"]).splitlines()
    last = git_run(project, ["log", "-1", "--format=%ad|%s", "--date=short"])
    first = git_run(project, ["log", "-1", "--reverse", "--format=%ad", "--date=short"])
    remote = git_run(project, ["remote", "get-url", "origin"])
    return {
        "commits": int(count) if count.isdigit() else 0,
        "root": root[0] if root else "",
        "last": last,
        "first": first,
        "remote": remote,
    }


def nested_repos(project: Path, max_depth: int = 2) -> list[str]:
    found: list[str] = []
    base_parts = len(project.parts)
    for current, dirs, _files in os.walk(project):
        cur = Path(current)
        depth = len(cur.parts) - base_parts
        if depth > max_depth:
            dirs[:] = []
            continue
        dirs[:] = [d for d in dirs if d != ".git" and not d.startswith(".")]
        if (cur / ".git").exists():
            found.append(cur.relative_to(ROOT).as_posix())
            dirs[:] = []
    return found


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for project in sorted(ROOT.iterdir()):
        if not project.is_dir() or project.name.startswith("."):
            continue
        if project.name in {"PlatformIO", "migration-20261011", "_tmp_inspect", "audiotransfer-work"}:
            # Tooling, transient migrations and duplicate work trees: recorded
            # separately, not as first-class projects.
            rows.append({
                "name": project.name,
                "kind": "tooling-or-backup",
                "git": git_info(project),
                "nested_repos": nested_repos(project, 1),
            })
            continue

        info = count_files(project)
        info.update({
            "name": project.name,
            "kind": "project",
            "headline": read_headline(project),
            "git": git_info(project),
        })
        rows.append(info)

    payload = {
        "root": str(ROOT),
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "projects": rows,
    }
    (OUT / "inventory.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"{'project':28} {'code':>8} {'total':>8} {'files':>6}  top languages")
    print("-" * 92)
    for row in sorted(rows, key=lambda r: r.get("code_lines", 0), reverse=True):
        if row["kind"] != "project":
            print(f"{row['name']:28} {'-':>8} {'-':>8} {'-':>6}  [{row['kind']}]")
            continue
        langs = ", ".join(f"{lang}:{n}" for lang, n in row["languages"][:3])
        print(
            f"{row['name']:28} {row['code_lines']:>8,} {row['lines']:>8,} "
            f"{row['files']:>6}  {langs}"
        )


if __name__ == "__main__":
    main()
