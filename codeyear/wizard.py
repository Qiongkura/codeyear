"""Interactive terminal wizard for CodeYear.

The regular ``codeyear scan`` command stays non-interactive. Running
``codeyear`` (or ``codeyear tui``) walks through directory selection,
shows how many repos were found, scans with a progress bar, and lets the
user choose where the outputs go.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
from datetime import date
from pathlib import Path

from .card import render as render_card
from .html_report import render as render_html, render_en as render_html_en
from .poster import render as render_poster, render_long
from .scanner import find_repos, scan_repo
from .stats import build_stats, fmt_human, fmt_int


def _ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    value = input(f"{prompt}{hint}: ").strip()
    return value or default


def _yes(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    value = input(f"{prompt} [{hint}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "是"}


def _detect_identity() -> tuple[str, str] | None:
    def config(key: str) -> str:
        try:
            proc = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return (proc.stdout or "").strip()

    email, name = config("user.email"), config("user.name")
    if email or name:
        return email, name
    return None


def _choose_roots() -> list[Path]:
    roots = [Path.cwd().resolve()]
    print("选择要扫描的目录。默认是当前目录，可以继续添加。")
    while True:
        print("\n已选择：")
        if roots:
            for i, root in enumerate(roots, 1):
                print(f"  {i}. {root}")
        else:
            print("  （空）")
        print("\n  [Enter] 开始   [a] 添加目录   [r] 删除   [c] 清空")
        command = input("> ").strip().lower()

        if command == "":
            if roots:
                return roots
            print("至少选择一个目录。")
            continue
        if command == "a":
            path = Path(_ask("目录路径", str(Path.cwd()))).expanduser()
            if not path.is_dir():
                print("这不是一个文件夹。")
                continue
            path = path.resolve()
            if path in roots:
                print("这个目录已经在列表里。")
                continue
            roots.append(path)
            continue
        if command == "r":
            if not roots:
                continue
            raw = _ask("删除第几个", "1")
            try:
                roots.pop(int(raw) - 1)
            except (ValueError, IndexError):
                print("编号不对。")
            continue
        if command == "c":
            roots = []
            continue
        print("未知选项。")


def _discover(roots: list[Path], depth: int) -> list[tuple[Path, Path]]:
    seen: set[Path] = set()
    found: list[tuple[Path, Path]] = []
    for root in roots:
        for repo in find_repos(root, max_depth=depth):
            resolved = repo.resolve()
            if resolved not in seen:
                seen.add(resolved)
                found.append((resolved, root))
    return found


def _progress(done: int, total: int, path: Path) -> None:
    if not sys.stderr.isatty():
        if done:
            print(f"[{done}/{total}] {path.name}", file=sys.stderr)
        return
    width = 28
    filled = int(width * done / max(total, 1))
    bar = "[" + "#" * filled + "-" * (width - filled) + f"] {done}/{total}"
    name = path.name[:36]
    sys.stderr.write("\r" + bar + "  " + name.ljust(38))
    sys.stderr.flush()
    if done == total:
        sys.stderr.write("\n")


def _open(path: Path) -> None:
    try:
        if hasattr(os, "startfile"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            webbrowser.open(path.resolve().as_uri())
    except Exception as exc:  # pragma: no cover - platform dependent
        print(f"无法自动打开报告: {exc}", file=sys.stderr)


def _root_labels(roots: list[Path]) -> dict[Path, str]:
    labels: dict[Path, str] = {}
    used: set[str] = set()
    for root in roots:
        base = root.name or str(root)
        label = base
        n = 2
        while label in used:
            label = f"{base}-{n}"
            n += 1
        used.add(label)
        labels[root] = label
    return labels


def run() -> int:
    try:
        roots = _choose_roots()
        depth_raw = _ask("向下扫描深度", "6")
        try:
            depth = max(1, int(depth_raw))
        except ValueError:
            depth = 6

        print("\n正在查找 git 仓库…")
        repos = _discover(roots, depth)
        print(f"找到 {len(repos)} 个 git 仓库。")
        if not repos:
            print("没有找到仓库，换个目录试试。")
            return 2

        year_raw = _ask("统计年份", str(date.today().year))
        try:
            year = int(year_raw)
        except ValueError:
            year = date.today().year

        identity = _detect_identity()
        if identity:
            email, name = identity
            label = f"{name} <{email}>" if name and email else (email or name)
            if not _yes(f"只统计你本人（{label}）?", True):
                identity = None
        else:
            print("未检测到 git 身份，将统计所有作者。")

        out_raw = _ask("输出目录", "codeyear-output")
        out_dir = Path(out_raw).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        open_after = _yes("完成后打开报告?", True)

        labels = _root_labels(roots)
        results = []
        warnings: list[str] = []
        total = len(repos)
        for i, (repo, root) in enumerate(repos):
            _progress(i, total, repo)
            result = scan_repo(repo, root, year)
            if len(roots) > 1:
                label = labels[root]
                old = result.name
                new = label if old == label or old in {"", "."} else f"{label}/{old}"
                result.name = new
                for commit in result.commits:
                    commit.repo = new
            if result.warning:
                warnings.append(f"{result.name}: {result.warning}")
            results.append(result)
            _progress(i + 1, total, repo)

        root_label = " + ".join(str(root) for root in roots)
        stats = build_stats(
            year=year, root=root_label, repos=results,
            warnings=warnings, identity=identity,
        )
        if stats.commit_count == 0:
            print(f"\n{year} 年没有找到提交。")
            return 3

        base = out_dir / f"codeyear-{year}"
        written: list[tuple[str, Path]] = []
        json_path = base.with_suffix(".json")
        json_path.write_text(
            json.dumps(stats.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(("JSON", json_path))
        written.append(("HTML", render_html(stats, base.with_suffix(".html"))))
        written.append(("HTML-EN", render_html_en(
            stats, out_dir / f"codeyear-{year}-en.html")))
        written.append(("PNG", render_poster(stats, base.with_suffix(".png"))))
        written.append(("LONG", render_long(
            stats, out_dir / f"codeyear-{year}-long.png")))
        cards = render_card(stats, out_dir / f"codeyear-{year}-card.svg")
        written.append(("CARD", cards[0]))
        written.append(("CARD-DARK", cards[1]))

        print()
        print(f"CodeYear {year}  ·  {stats.persona.title}")
        print("-" * 46)
        print(f"仓库      {stats.repo_count}")
        print(f"提交      {fmt_int(stats.commit_count)}")
        print(f"代码行    {fmt_human(stats.lines_changed)}")
        print(f"活跃      {stats.active_days} 天 · 涉及 {stats.file_count} 个文件")
        print(f"输出      {out_dir}")
        print("-" * 46)
        for label, path in written:
            print(f"{label:<9}  {path.name}")

        if warnings:
            print()
            print("警告:")
            for warning in warnings:
                print(f"  - {warning}")

        if open_after:
            _open(written[0][1])
        return 0
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
