"""Interactive terminal wizard for CodeYear.

The regular ``codeyear scan`` command stays non-interactive. Running
``codeyear tui`` walks through directory selection, shows how many repos
were found, scans with a progress bar, and lets the user choose where the
outputs go. The desktop GUI lives in ``gui.py`` and shares the same runner.
"""

from __future__ import annotations

import os
import sys
import webbrowser
from datetime import date
from pathlib import Path

from .runner import detect_identity, discover, render, scan
from .stats import fmt_human, fmt_int


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


def _progress(done: int, total: int, name: str) -> None:
    if not sys.stderr.isatty():
        if done:
            print(f"[{done}/{total}] {name}", file=sys.stderr)
        return
    width = 28
    filled = int(width * done / max(total, 1))
    bar = "[" + "#" * filled + "-" * (width - filled) + f"] {done}/{total}"
    name = name[:36]
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


def run() -> int:
    try:
        roots = _choose_roots()
        depth_raw = _ask("向下扫描层级（文件夹层数）", "6")
        try:
            depth = max(1, int(depth_raw))
        except ValueError:
            depth = 6

        print("\n正在查找 git 仓库…")
        repos = discover(roots, depth)
        print(f"找到 {len(repos)} 个 git 仓库。")
        if not repos:
            print("没有找到仓库，换个目录试试。")
            return 2

        year_raw = _ask("统计年份", str(date.today().year))
        try:
            year = int(year_raw)
        except ValueError:
            year = date.today().year

        identity = detect_identity()
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
        compare = _yes("同时统计去年，生成同比?", False)
        jobs_raw = _ask("并行扫描数", "1")
        try:
            jobs = max(1, int(jobs_raw))
        except ValueError:
            jobs = 1
        open_after = _yes("完成后打开报告?", True)

        stats, warnings = scan(
            repos, roots, year, identity, progress=_progress,
            jobs=jobs, compare=compare,
        )
        if stats.commit_count == 0:
            print(f"\n{year} 年没有找到提交。")
            return 3

        written = render(stats, out_dir)

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
            _open(next(path for label, path in written if label == "HTML"))
        return 0
    except KeyboardInterrupt:
        print("\n已取消。")
        return 130
