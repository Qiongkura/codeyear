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

from . import __version__, i18n
from .card import THEMES
from .card import render as render_card
from .config import load as load_config
from .html_report import render as render_html
from .html_report import render_en as render_html_en
from .poster import render as render_poster
from .poster import render_long
from .runner import discover, scan
from .stats import fmt_int

_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _build_parser() -> argparse.ArgumentParser:
    cfg = load_config()
    parser = argparse.ArgumentParser(
        prog="codeyear",
        description="扫描本地 git 仓库，生成一份年度代码报告（HTML + PNG 海报）。",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--lang", choices=["zh", "en"], default=None,
                        help="界面与 Profile 卡片语言 / UI and profile-card language")

    sub = parser.add_subparsers(dest="command", required=False)
    sub.add_parser("gui", help="图形界面：点选目录、看进度、选输出位置")
    sub.add_parser("tui", help="终端交互向导：选目录、看进度、选输出位置")
    github = sub.add_parser("github", help="从公开 GitHub 账号生成（联网，仅公开仓库）")
    github.add_argument("username", help="GitHub 用户名")
    github.add_argument("--year", type=int, default=cfg.get("year", date.today().year),
                        help="统计年份")
    github.add_argument("--out", default=cfg.get("out", "codeyear-output"),
                        help="输出目录")
    github.add_argument("--token", default=None, help="GitHub token；也可用 GITHUB_TOKEN")
    github.add_argument("--max-commits", type=int, default=cfg.get("max_commits", 200),
                        help="最多拉取多少条提交（无 token 时自动限制为 30）")
    github.add_argument("--include-forks", action="store_true", help="包含 fork 仓库")
    github.add_argument("--open", action="store_true", default=cfg.get("open", False),
                        help="生成后打开报告")
    github.add_argument("--quiet", action="store_true", help="不打印扫描进度")
    github.add_argument("--theme", choices=sorted(THEMES),
                        default=cfg.get("theme", "paper"),
                        help="卡片主题：paper / mono / forest / ocean")
    github.add_argument("--card-only", action="store_true",
                        help="只生成主页卡片和 embed 片段，不生成完整报告")
    github.add_argument("--profile-repo", default=None,
                        help="本地 GitHub Profile 仓库路径；自动更新 README 里的卡片")
    github.add_argument("--push-profile", action="store_true",
                        help="更新后提交并推送 Profile 仓库（联网）；需同时指定 --profile-repo")
    github.add_argument("--cache-dir", default=None,
                        help="缓存公开 commit 详情到该目录，重复运行更快")
    github.add_argument("--fallback-previous", action="store_true",
                        help="当年没有提交时回退到上一年，适合跨年自动更新")
    server = sub.add_parser("serve", help="启动公开 GitHub 卡片 HTTP 服务")
    server.add_argument("--host", default="127.0.0.1", help="监听地址，默认 127.0.0.1")
    server.add_argument("--port", type=int, default=8000, help="监听端口，默认 8000")
    server.add_argument("--token", default=None, help="GitHub token；也可用 GITHUB_TOKEN")
    server.add_argument("--max-commits", type=int, default=200,
                        help="每张卡片最多拉取多少条提交")
    scan = sub.add_parser("scan", help="扫描一个文件夹下的所有 git 仓库")
    scan.add_argument("path", nargs="*", default=(cfg.get("roots") or ["."]),
                      help="要扫描的文件夹（可以多个，默认当前目录）")
    scan.add_argument("--year", type=int, default=cfg.get("year", date.today().year),
                      help="统计年份，默认今年")
    scan.add_argument("--out", default=cfg.get("out", "codeyear-output"),
                      help="输出目录，默认 ./codeyear-output")
    scan.add_argument("--author", default=cfg.get("author"),
                      help="只统计匹配的 git author（--author 参数）")
    scan.add_argument("--compare", action="store_true",
                      default=cfg.get("compare", False),
                      help="同时扫描去年，在报告里生成同比数据")
    scan.add_argument("--fallback-previous", action="store_true",
                      default=cfg.get("fallback_previous", False),
                      help="当年没有提交时回退到上一年，适合跨年自动更新")
    scan.add_argument("--alias", action="append", default=cfg.get("aliases", []),
                      help="额外作者邮箱或名字，可重复；用于旧提交")
    scan.add_argument("--no-mailmap", action="store_true",
                      default=cfg.get("no_mailmap", False),
                      help="忽略仓库里的 .mailmap（默认自动使用）")
    scan.add_argument("--all-branches", action="store_true",
                      default=cfg.get("all_branches", False),
                      help="统计所有本地分支/tag 的提交（默认只看当前分支）")
    scan.add_argument("--all-authors", action="store_true",
                      default=cfg.get("all_authors", False),
                      help="统计所有作者的提交（默认只统计你本人，按 git user.name / user.email 识别）")
    scan.add_argument("--max-depth", type=int, default=cfg.get("max_depth", 6),
                      help="向下查找仓库的最大文件夹层数，默认 6")
    scan.add_argument("--timeout", type=int, default=cfg.get("timeout", 300),
                      help="单个仓库的扫描超时秒数")
    scan.add_argument("--jobs", type=int, default=cfg.get("jobs", 1),
                      help="并行扫描的仓库数，默认 1")
    scan.add_argument("--no-png", action="store_true", help="不生成 PNG 海报")
    scan.add_argument("--no-long", action="store_true", help="不生成完整版长图")
    scan.add_argument("--no-card", action="store_true", help="不生成 GitHub 主页卡片")
    scan.add_argument("--no-html", action="store_true", help="不生成 HTML 报告")
    scan.add_argument("--profile-repo", default=None,
                      help="本地 GitHub Profile 仓库路径；只写入本地，不联网")
    scan.add_argument("--push-profile", action="store_true",
                      help="更新后提交并推送 Profile 仓库（联网）；需同时指定 --profile-repo")
    scan.add_argument("--open", action="store_true", default=cfg.get("open", False),
                      help="生成后自动打开报告")
    scan.add_argument("--quiet", action="store_true", help="不打印扫描进度")
    i18n.localize_parser(parser)
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
        print(i18n.tr("无法自动打开文件: {exc}", exc=exc), file=sys.stderr)


def _detect_identity() -> tuple[str, str] | None:
    """The runner's git identity, used to keep only their own commits."""

    def config(key: str) -> str:
        try:
            proc = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10, creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return (proc.stdout or "").strip()

    email, name = config("user.email"), config("user.name")
    if email or name:
        return (email, name)
    return None


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    i18n.set_lang(i18n.detect(argv))
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command in {None, "gui"}:
        try:
            from .gui import run as run_gui
        except ImportError as exc:
            print(i18n.tr("无法加载图形界面（Tkinter）: {exc}", exc=exc),
                  file=sys.stderr)
            print(i18n.tr("请改用 codeyear tui 或 codeyear scan。"),
                  file=sys.stderr)
            return 1
        return run_gui()
    if args.command == "tui":
        from .wizard import run as run_wizard

        return run_wizard()
    if args.command == "github":
        from .github_public import run as run_github

        if args.push_profile and not args.profile_repo:
            parser.error(i18n.tr("--push-profile 需要同时指定 --profile-repo"))
        return run_github(
            args.username, args.year, Path(args.out),
            token=args.token, max_commits=args.max_commits,
            include_forks=args.include_forks,
            open_report=args.open, quiet=args.quiet,
            theme=args.theme, card_only=args.card_only,
            profile_repo=args.profile_repo,
            push_profile=args.push_profile,
            fallback_previous=args.fallback_previous,
            cache_dir=args.cache_dir,
            lang=i18n.get_lang(),
        )
    if args.command == "serve":
        from .server import serve

        return serve(
            args.host, args.port,
            token=args.token, max_commits=args.max_commits,
        )
    if args.command != "scan":
        parser.print_help()
        return 0

    if args.push_profile and not args.profile_repo:
        parser.error(i18n.tr("--push-profile 需要同时指定 --profile-repo"))

    roots = [Path(path).expanduser() for path in (args.path or ["."])]
    try:
        repos = discover(roots, args.max_depth)
    except (FileNotFoundError, NotADirectoryError) as exc:
        print(i18n.tr("错误: {exc}", exc=exc), file=sys.stderr)
        return 2

    if not repos:
        where = " + ".join(str(root) for root in roots)
        print(i18n.tr("在 {where} 下没有找到 git 仓库。", where=where),
              file=sys.stderr)
        return 2

    if not args.quiet:
        where = " + ".join(str(root) for root in roots)
        print(i18n.tr(
            "CodeYear {year} · 在 {where} 下找到 {count} 个仓库",
            year=args.year, where=where, count=len(repos),
        ), file=sys.stderr)

    identity = None
    if not args.all_authors and not args.author:
        identity = _detect_identity()
        if identity is None and not args.quiet:
            print(i18n.tr(
                "  ! 未检测到 git user.name / user.email，将统计所有作者的提交"
            ), file=sys.stderr)

    def progress(done: int, total: int, name: str) -> None:
        if not args.quiet and done:
            print(f"  [{done}/{total}] {name}", file=sys.stderr)

    stats, warnings = scan(
        repos, roots, args.year, identity,
        aliases=args.alias, author=args.author, timeout=args.timeout,
        jobs=max(1, args.jobs), progress=progress,
        compare=args.compare, use_mailmap=not args.no_mailmap,
        all_branches=args.all_branches,
    )

    if (
        args.fallback_previous
        and stats.commit_count == 0
        and args.year == date.today().year
    ):
        previous, prev_warnings = scan(
            repos, roots, args.year - 1, identity,
            aliases=args.alias, author=args.author, timeout=args.timeout,
            jobs=max(1, args.jobs), progress=progress,
            compare=args.compare, use_mailmap=not args.no_mailmap,
            all_branches=args.all_branches,
        )
        if previous.commit_count:
            stats, warnings = previous, prev_warnings
            args.year = previous.year

    if stats.commit_count == 0:
        print(
            i18n.tr(
                "{year} 年没有找到提交。可以换 --year，或检查 --author 过滤条件。",
                year=args.year,
            ),
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
    en_cards = []
    if not args.no_card:
        card_paths = render_card(stats, out_dir / f"codeyear-{args.year}-card.svg")
        written.append(("CARD", card_paths[0]))
        written.append(("CARD-DARK", card_paths[1]))
        en_cards = render_card(
            stats, out_dir / f"codeyear-{args.year}-card-en.svg", lang="en",
        )
        written.append(("CARD-EN", en_cards[0]))
        written.append(("CARD-DARK-EN", en_cards[1]))

    exit_code = 0
    if args.profile_repo:
        if not card_paths:
            print(i18n.tr(
                "  ! 指定了 --profile-repo，但 --no-card 关闭了卡片生成"
            ), file=sys.stderr)
            exit_code = 1
        else:
            from .profile import update_profile

            profile_cards = en_cards if i18n.get_lang() == "en" else card_paths
            try:
                profile_repo, changed, pushed = update_profile(
                    args.profile_repo, args.year,
                    profile_cards[0], profile_cards[1],
                    push=args.push_profile,
                )
                written.append(("PROFILE", profile_repo))
                if changed:
                    state = "已提交并推送" if pushed else "仅写入本地"
                    print("\n" + i18n.tr(
                        "Profile  {state} · {repo}",
                        state=i18n.tr(state), repo=profile_repo,
                    ))
                else:
                    print("\n" + i18n.tr(
                        "Profile  卡片已是最新 · {repo}", repo=profile_repo,
                    ))
            except Exception as exc:  # pragma: no cover - user environment
                print(i18n.tr(
                    "  ! 更新 Profile 失败: {exc}", exc=exc
                ), file=sys.stderr)
                exit_code = 1

    # Console summary
    active_pct = stats.active_days / (366 if _is_leap(args.year) else 365)
    print()
    print(i18n.tr(
        "CodeYear {year}  ·  {title}",
        year=args.year, title=stats.persona.title,
    ))
    print("-" * 46)
    print(f"{i18n.tr('仓库'):<10}{stats.repo_count}")
    if stats.identity_label:
        print(f"{i18n.tr('身份'):<10}{stats.identity_label}")
        if stats.filtered_commits:
            print(f"{i18n.tr('已过滤'):<10}{stats.filtered_commits} "
                  f"{i18n.tr('次他人提交')}")
    elif args.author:
        print(f"{i18n.tr('身份'):<10}--author={args.author}")
    else:
        print(f"{i18n.tr('身份'):<10}{i18n.tr('全部作者')}")
    print(f"{i18n.tr('提交'):<10}{fmt_int(stats.commit_count)}")
    print(f"{i18n.tr('代码行'):<10}{fmt_int(stats.lines_changed)}  "
          f"(+{fmt_int(stats.insertions)} / -{fmt_int(stats.deletions)})")
    print(i18n.tr(
        "活跃      {days} 天（{pct}）· 最长连续 {streak} 天",
        days=stats.active_days, pct=f"{active_pct:.0%}",
        streak=stats.longest_streak,
    ))
    print(i18n.tr("语言      {count} 种", count=stats.language_count))
    if stats.busiest_day:
        print(i18n.tr(
            "最忙一天  {day} · {count} 次提交",
            day=stats.busiest_day[0], count=stats.busiest_count,
        ))
    print("-" * 46)
    for label, path in written:
        print(f"{label:<9}  {path.resolve()}")

    if warnings:
        print()
        print(i18n.tr("警告:"))
        for warning in warnings:
            print(f"  - {warning}")

    if args.open and written:
        target = next((p for label, p in written if label == "HTML"), written[0][1])
        _open_path(target)

    return exit_code


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
