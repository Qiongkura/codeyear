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

from . import i18n
from .runner import detect_identity, discover, render, scan
from .stats import fmt_human, fmt_int


def _ask(prompt: str, default: str = "") -> str:
    hint = f" [{default}]" if default else ""
    value = input(f"{i18n.tr(prompt)}{hint}: ").strip()
    return value or default


def _yes(prompt: str, default: bool = True) -> bool:
    hint = "Y/n" if default else "y/N"
    value = input(f"{i18n.tr(prompt)} [{hint}]: ").strip().lower()
    if not value:
        return default
    return value in {"y", "yes", "是"}


def _choose_roots() -> list[Path]:
    roots = [Path.cwd().resolve()]
    print(i18n.tr("选择要扫描的目录。默认是当前目录，可以继续添加。"))
    while True:
        print("\n" + i18n.tr("已选择："))
        if roots:
            for i, root in enumerate(roots, 1):
                print(f"  {i}. {root}")
        else:
            print("  " + i18n.tr("（空）"))
        print("\n  " + i18n.tr(
            "[Enter] 开始   [a] 添加目录   [r] 删除   [c] 清空"
        ))
        command = input("> ").strip().lower()

        if command == "":
            if roots:
                return roots
            print(i18n.tr("至少选择一个目录。"))
            continue
        if command == "a":
            path = Path(_ask("目录路径", str(Path.cwd()))).expanduser()
            if not path.is_dir():
                print(i18n.tr("这不是一个文件夹。"))
                continue
            path = path.resolve()
            if path in roots:
                print(i18n.tr("这个目录已经在列表里。"))
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
                print(i18n.tr("编号不对。"))
            continue
        if command == "c":
            roots = []
            continue
        print(i18n.tr("未知选项。"))


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
        print(i18n.tr("无法自动打开报告: {exc}", exc=exc), file=sys.stderr)


def run() -> int:
    try:
        roots = _choose_roots()
        depth_raw = _ask("向下扫描层级（文件夹层数）", "6")
        try:
            depth = max(1, int(depth_raw))
        except ValueError:
            depth = 6

        print("\n" + i18n.tr("正在查找 git 仓库…"))
        repos = discover(roots, depth)
        print(i18n.tr("找到 {count} 个 git 仓库。", count=len(repos)))
        if not repos:
            print(i18n.tr("没有找到仓库，换个目录试试。"))
            return 2

        year_raw = _ask("统计年份", str(date.today().year))
        try:
            year = int(year_raw)
        except ValueError:
            year = date.today().year

        identity = detect_identity()
        aliases: list[str] = []
        if identity:
            email, name = identity
            label = f"{name} <{email}>" if name and email else (email or name)
            if not _yes(
                i18n.tr("只统计你本人（{label}）?", label=label), True
            ):
                identity = None
            else:
                extra = _ask("旧邮箱/名字（逗号分隔，可空）", "")
                aliases = [item.strip() for item in extra.split(",") if item.strip()]
        else:
            print(i18n.tr("未检测到 git 身份，将统计所有作者。"))

        out_raw = _ask("输出目录", "codeyear-output")
        out_dir = Path(out_raw).expanduser().resolve()
        out_dir.mkdir(parents=True, exist_ok=True)
        compare = _yes("同时统计去年，生成同比?", False)
        all_branches = _yes("统计所有分支/tag?", False)
        jobs_raw = _ask("并行扫描数", "1")
        try:
            jobs = max(1, int(jobs_raw))
        except ValueError:
            jobs = 1
        open_after = _yes("完成后打开报告?", True)

        stats, warnings = scan(
            repos, roots, year, identity, aliases=aliases,
            progress=_progress, jobs=jobs, compare=compare,
            all_branches=all_branches,
        )
        if stats.commit_count == 0:
            print("\n" + i18n.tr("{year} 年没有找到提交。", year=year))
            return 3

        written = render(stats, out_dir)

        print()
        print(i18n.tr(
            "CodeYear {year}  ·  {title}",
            year=year, title=stats.persona.title,
        ))
        print("-" * 46)
        print(f"{i18n.tr('仓库'):<10}{stats.repo_count}")
        print(f"{i18n.tr('提交'):<10}{fmt_int(stats.commit_count)}")
        print(f"{i18n.tr('代码行'):<10}{fmt_human(stats.lines_changed)}")
        print(i18n.tr(
            "活跃      {days} 天 · 涉及 {count} 个文件",
            days=stats.active_days, count=stats.file_count,
        ))
        print(f"{i18n.tr('输出'):<10}{out_dir}")
        print("-" * 46)
        for label, path in written:
            print(f"{label:<9}  {path.name}")

        if warnings:
            print()
            print(i18n.tr("警告:"))
            for warning in warnings:
                print(f"  - {warning}")

        if open_after:
            _open(next(path for label, path in written if label == "HTML"))
        return 0
    except KeyboardInterrupt:
        print("\n" + i18n.tr("已取消。"))
        return 130
