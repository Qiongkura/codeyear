"""Command line entry point."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import webbrowser
from datetime import date
from pathlib import Path

from . import __version__
from .card import render as render_card
from .html_report import render as render_html, render_en as render_html_en
from .poster import render as render_poster, render_long
from .scanner import find_repos, scan_repo
from .stats import build_stats, fmt_int


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeyear",
        description="扫描本地 git 仓库，生成一份年度代码报告（HTML + PNG 海报）。",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    sub = parser.add_subparsers(dest="command", required=False)
    sub.add_parser("gui", help="图形界面：点选目录、看进度、选输出位置")
    sub.add_parser("tui", help="终端交互向导：选目录、看进度、选输出位置")
    scan = sub.add_parser("scan", help="扫描一个文件夹下的所有 git 仓库")
    scan.add_argument("path", nargs="?", default=".", help="要扫描的文件夹（默认当前目录）")
    scan.add_argument("--year", type=int, default=date.today().year, help="统计年份，默认今年")
    scan.add_argument("--out", default="codeyear-output", help="输出目录，默认 ./codeyear-output")
    scan.add_argument("--author", default=None, help="只统计匹配的 git author（--author 参数）")
    scan.add_argument("--all-authors", action="store_true",
                      help="统计所有作者的提交（默认只统计你本人，按 git user.name / user.email 识别）")
    scan.add_argument("--max-depth", type=int, default=6, help="最大扫描深度，默认 6")
    scan.add_argument("--timeout", type=int, default=300, help="单个仓库的扫描超时秒数")
    scan.add_argument("--no-png", action="store_true", help="不生成 PNG 海报")
    scan.add_argument("--no-long", action="store_true", help="不生成完整版长图")
    scan.add_argument("--no-card", action="store_true", help="不生成 GitHub 主页卡片")
    scan.add_argument("--no-html", action="store_true", help="不生成 HTML 报告")
    scan.add_argument("--profile-repo", default=None,
                      help="本地 GitHub Profile 仓库路径；只写入本地，不联网")
    scan.add_argument("--push-profile", action="store_true",
                      help="更新后提交并推送 Profile 仓库（联网）；需同时指定 --profile-repo")
    scan.add_argument("--open", action="store_true", help="生成后自动打开报告")
    scan.add_argument("--quiet", action="store_true", help="不打印扫描进度")
    return parser


def _open_path(path: Path) -> None:
    try:
        if path.suffix.lower() in {".html", ".htm"}:
            webbrowser.open(path.resolve().as_uri())
        elif hasattr(os, "startfile"):
            os.startfile(str(path))  # type: ignore[attr-defined]
        else:
            webbrowser.open(path.resolve().as_uri())
    except Exception as exc:  # pragma: no cover - platform dependent
        print(f"无法自动打开文件: {exc}", file=sys.stderr)


def _detect_identity() -> tuple[str, str] | None:
    """The runner's git identity, used to keep only their own commits."""

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
        return (email, name)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in {None, "gui"}:
        try:
            from .gui import run as run_gui
        except ImportError as exc:
            print(f"无法加载图形界面（Tkinter）: {exc}", file=sys.stderr)
            print("请改用 codeyear tui 或 codeyear scan。", file=sys.stderr)
            return 1
        return run_gui()
    if args.command == "tui":
        from .wizard import run as run_wizard

        return run_wizard()
    if args.command != "scan":
        parser.print_help()
        return 0

    if args.push_profile and not args.profile_repo:
        parser.error("--push-profile 需要同时指定 --profile-repo")

    root = Path(args.path).expanduser()
    try:
        repos = find_repos(root, max_depth=args.max_depth)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(f"错误: {exc}", file=sys.stderr)
        return 2

    if not repos:
        print(f"在 {root} 下没有找到 git 仓库。", file=sys.stderr)
        return 2

    if not args.quiet:
        print(f"CodeYear {args.year} · 在 {root} 下找到 {len(repos)} 个仓库", file=sys.stderr)

    identity = None
    if not args.all_authors and not args.author:
        identity = _detect_identity()
        if identity is None and not args.quiet:
            print("  ! 未检测到 git user.name / user.email，将统计所有作者的提交",
                  file=sys.stderr)

    results = []
    warnings: list[str] = []
    for i, repo in enumerate(repos, 1):
        if not args.quiet:
            print(f"  [{i}/{len(repos)}] {repo}", file=sys.stderr)
        result = scan_repo(
            repo, root.resolve(), args.year,
            author=args.author, timeout=args.timeout,
        )
        if result.warning:
            warnings.append(f"{result.name}: {result.warning}")
            if not args.quiet:
                print(f"       ! {result.warning}", file=sys.stderr)
        results.append(result)

    stats = build_stats(
        year=args.year, root=str(root.resolve()), repos=results,
        warnings=warnings, identity=identity,
    )

    if stats.commit_count == 0:
        print(
            f"{args.year} 年没有找到提交。可以换 --year，或检查 --author 过滤条件。",
            file=sys.stderr,
        )
        return 3

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"codeyear-{args.year}"

    written: list[tuple[str, Path]] = []

    json_path = base.with_suffix(".json")
    json_path.write_text(
        json.dumps(stats.as_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    written.append(("JSON", json_path))

    if not args.no_html:
        html_path = render_html(stats, base.with_suffix(".html"))
        written.append(("HTML", html_path))
        en_path = render_html_en(stats, out_dir / f"codeyear-{args.year}-en.html")
        written.append(("HTML-EN", en_path))

    if not args.no_png:
        png_path = render_poster(stats, base.with_suffix(".png"))
        written.append(("PNG", png_path))
        if not args.no_long:
            long_path = render_long(stats, out_dir / f"codeyear-{args.year}-long.png")
            written.append(("LONG", long_path))

    card_paths = []
    if not args.no_card:
        card_paths = render_card(stats, out_dir / f"codeyear-{args.year}-card.svg")
        written.append(("CARD", card_paths[0]))
        written.append(("CARD-DARK", card_paths[1]))

    if args.profile_repo:
        if not card_paths:
            print("  ! 指定了 --profile-repo，但 --no-card 关闭了卡片生成",
                  file=sys.stderr)
        else:
            from .profile import update_profile

            try:
                profile_repo, changed, pushed = update_profile(
                    args.profile_repo, args.year, card_paths[0], card_paths[1],
                    push=args.push_profile,
                )
                written.append(("PROFILE", profile_repo))
                if changed:
                    state = "已提交并推送" if pushed else "仅写入本地"
                    print(f"\nProfile  {state} · {profile_repo}")
                else:
                    print(f"\nProfile  卡片已是最新 · {profile_repo}")
            except Exception as exc:  # pragma: no cover - user environment
                print(f"  ! 更新 Profile 失败: {exc}", file=sys.stderr)

    # Console summary
    active_pct = stats.active_days / (366 if _is_leap(args.year) else 365)
    print()
    print(f"CodeYear {args.year}  ·  {stats.persona.title}")
    print("-" * 46)
    print(f"仓库      {stats.repo_count}")
    if stats.identity_label:
        print(f"身份      {stats.identity_label}")
        if stats.filtered_commits:
            print(f"已过滤    {stats.filtered_commits} 次他人提交")
    elif args.author:
        print(f"身份      --author={args.author}")
    else:
        print("身份      全部作者")
    print(f"提交      {fmt_int(stats.commit_count)}")
    print(f"代码行    {fmt_int(stats.lines_changed)}  (+{fmt_int(stats.insertions)} / -{fmt_int(stats.deletions)})")
    print(f"活跃      {stats.active_days} 天（{active_pct:.0%}）· 最长连续 {stats.longest_streak} 天")
    print(f"语言      {stats.language_count} 种")
    if stats.busiest_day:
        print(f"最忙一天  {stats.busiest_day[0]} · {stats.busiest_count} 次提交")
    print("-" * 46)
    for label, path in written:
        print(f"{label:<9}  {path.resolve()}")

    if warnings:
        print()
        print("警告:")
        for warning in warnings:
            print(f"  - {warning}")

    if args.open and written:
        target = next((p for label, p in written if label == "HTML"), written[0][1])
        _open_path(target)

    return 0


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
