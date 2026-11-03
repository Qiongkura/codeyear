"""Render a compact SVG card for a GitHub profile README."""

from __future__ import annotations

import html
from datetime import date, timedelta
from pathlib import Path

from .stats import (
    ReportStats,
    fmt_human,
    fmt_int,
    fmt_signed_pair,
    language_breakdown,
    parse_daily,
)

W, H = 900, 540
PAPER = "#f4f1e8"
PAPER2 = "#eceadf"
INK = "#171512"
INK2 = "#403c33"
MUTED = "#6f6a5e"
LINE = "#d9d3c2"
ACCENT = "#d4491f"
PALETTE = ["#171512", "#d4491f", "#8f8672", "#b3ab97", "#c8c1ac"]
LEVELS = ["#e6e1d2", "#ddd6c4", "#a89f88", "#5c554a", "#171512"]


def _e(value: str) -> str:
    return html.escape(str(value), quote=True)


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _heatmap(stats: ReportStats) -> str:
    daily = parse_daily(stats.daily)
    start = date(stats.year, 1, 1)
    end = date(stats.year, 12, 31)
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=6 - end.weekday())
    cols = (grid_end - grid_start).days // 7 + 1

    cell, gap = 6, 1
    x0, y0 = 500, 212
    rects = []
    cursor = grid_start
    while cursor <= grid_end:
        if start <= cursor <= end:
            col = (cursor - grid_start).days // 7
            row = cursor.weekday()
            count = daily.get(cursor, 0)
            if count == 0:
                level = 0
            elif count == 1:
                level = 1
            elif count <= 3:
                level = 2
            elif count <= 6:
                level = 3
            else:
                level = 4
            x = x0 + col * (cell + gap)
            y = y0 + row * (cell + gap)
            rects.append(
                f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                f'fill="{LEVELS[level]}"/>'
            )
        cursor += timedelta(days=1)
    return (
        f'<rect x="{x0}" y="{y0}" width="{cols * (cell + gap) - gap}" '
        f'height="{7 * (cell + gap) - gap}" fill="#efece1"/>'
        + "".join(rects)
    )


def _lang_rows(stats: ReportStats) -> tuple[list[tuple[str, int]], int]:
    return language_breakdown(stats.languages, limit=4, min_share=0.01)


def build_svg(stats: ReportStats) -> str:
    monthly = stats.monthly
    peak = max(monthly) or 1
    bars = []
    bar_w, gap = 26, 8
    baseline = 300
    for i, value in enumerate(monthly):
        x = 32 + i * (bar_w + gap)
        height = max(int(value / peak * 64), 2)
        fill = ACCENT if value == peak and value > 0 else INK
        bars.append(
            f'<rect x="{x}" y="{baseline - height}" width="{bar_w}" '
            f'height="{height}" fill="{fill}"/>'
        )
        bars.append(
            f'<text x="{x + bar_w / 2}" y="{baseline + 12}" text-anchor="middle" '
            f'font-family="Consolas, monospace" font-size="7" fill="{MUTED}">'
            f"{i + 1:02d}</text>"
        )

    stat_items = [
        ("COMMITS / 提交", fmt_int(stats.commit_count), f"{stats.repo_count} 个仓库"),
        ("LINES / 行变更", fmt_human(stats.lines_changed),
         fmt_signed_pair(stats.insertions, stats.deletions)),
        ("ACTIVE / 活跃天", str(stats.active_days),
         f"占全年 {stats.active_days / (366 if _is_leap(stats.year) else 365):.0%}"),
        ("STREAK / 最长连续", str(stats.longest_streak),
         f"当前 {stats.current_streak} 天"),
    ]
    stats_svg = []
    for i, (label, value, sub) in enumerate(stat_items):
        x = 32 + i * 212
        stats_svg.append(
            f'<text x="{x}" y="124" font-family="Consolas, monospace" '
            f'font-size="8" letter-spacing="1" fill="{MUTED}">{_e(label)}</text>'
        )
        stats_svg.append(
            f'<text x="{x}" y="152" font-family="Consolas, monospace" '
            f'font-size="22" fill="{INK}">{_e(value)}</text>'
        )
        stats_svg.append(
            f'<text x="{x}" y="169" font-family="Consolas, monospace" '
            f'font-size="8" fill="{MUTED}">{_e(sub)}</text>'
        )

    lang_rows, lang_total = _lang_rows(stats)
    lang_total = lang_total or 1
    lang_bar = []
    x = 32
    for i, (_name, value) in enumerate(lang_rows):
        width = int(440 * value / lang_total)
        lang_bar.append(
            f'<rect x="{x}" y="352" width="{width}" height="12" '
            f'fill="{PALETTE[i % len(PALETTE)]}"/>'
        )
        x += width
    lang_legend = []
    for i, (name, value) in enumerate(lang_rows):
        col, row = i // 3, i % 3
        lx = 32 + col * 222
        ly = 378 + row * 18
        lang_legend.append(
            f'<rect x="{lx}" y="{ly - 7}" width="7" height="7" '
            f'fill="{PALETTE[i % len(PALETTE)]}"/>'
        )
        lang_legend.append(
            f'<text x="{lx + 14}" y="{ly}" font-family="Consolas, monospace" '
            f'font-size="8" fill="{INK2}">{_e(_truncate(name, 14))}</text>'
        )
        lang_legend.append(
            f'<text x="{lx + 200}" y="{ly}" text-anchor="end" '
            f'font-family="Consolas, monospace" font-size="8" fill="{MUTED}">'
            f"{value / lang_total * 100:.0f}%</text>"
        )

    repo_rows = []
    repos = stats.repo_details[:3]
    max_commits = max((r["commits"] for r in repos), default=1)
    for i, repo in enumerate(repos):
        ry = 356 + i * 22
        repo_rows.append(
            f'<text x="500" y="{ry}" font-family="Consolas, monospace" '
            f'font-size="7" fill="{ACCENT}">{i + 1:02d}</text>'
        )
        repo_rows.append(
            f'<text x="522" y="{ry}" font-family="Consolas, monospace" '
            f'font-size="8" fill="{INK2}">{_e(_truncate(repo["name"], 34))}</text>'
        )
        repo_rows.append(
            f'<text x="868" y="{ry}" text-anchor="end" font-family="Consolas, monospace" '
            f'font-size="8" fill="{MUTED}">{fmt_int(repo["commits"])}</text>'
        )
        width = int(150 * repo["commits"] / max_commits)
        repo_rows.append(
            f'<rect x="700" y="{ry - 5}" width="{width}" height="3" fill="#b3ab97"/>'
        )

    record_items = []
    if stats.busiest_day:
        day, count = stats.busiest_day
        record_items.append(("最忙一天", f"{count} 次", day.replace("-", ".")))
    if stats.longest_gap:
        days, start, end = stats.longest_gap
        record_items.append(("最长空窗", f"{days} 天", f"{start[5:]} – {end[5:]}"))
    if stats.largest_commit:
        lc = stats.largest_commit
        record_items.append(("最大提交", f"{fmt_int(lc['lines'])} 行", lc["repo"]))
    record_items.append(("最长 commit", f"{len(stats.longest_subject)} 字符",
                         _truncate(stats.longest_subject, 22)))
    records = []
    for i, (label, value, sub) in enumerate(record_items):
        rx = 32 + i * 212
        records.append(
            f'<text x="{rx}" y="458" font-family="Consolas, monospace" '
            f'font-size="8" letter-spacing="1" fill="{MUTED}">{_e(label)}</text>'
        )
        records.append(
            f'<text x="{rx}" y="478" font-family="Georgia, Songti SC, SimSun, serif" '
            f'font-size="15" fill="{INK}">{_e(value)}</text>'
        )
        records.append(
            f'<text x="{rx}" y="496" font-family="Consolas, monospace" '
            f'font-size="7" fill="{MUTED}">{_e(sub)}</text>'
        )

    title = _truncate(stats.persona.title, 24)
    subtitle = _truncate(stats.persona.subtitle, 84)
    footer = "generated locally · no data uploaded"
    right_footer = f"深夜 {stats.night_share:.0%} · 周末 {stats.weekend_share:.0%}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="CodeYear {stats.year} · {_e(title)}">
  <title>CodeYear {stats.year} · {_e(title)}</title>
  <rect width="{W}" height="{H}" fill="{PAPER}"/>
  <line x1="0" y1="0" x2="{W}" y2="0" stroke="{ACCENT}" stroke-width="2"/>
  <text x="32" y="30" font-family="Consolas, monospace" font-size="11" letter-spacing="3" fill="{ACCENT}">CODEYEAR</text>
  <text x="868" y="30" text-anchor="end" font-family="Consolas, monospace" font-size="9" fill="{MUTED}">{stats.year} · LOCAL-FIRST</text>
  <text x="32" y="72" font-family="Georgia, Songti SC, SimSun, serif" font-size="28" fill="{INK}">{_e(title)}</text>
  <text x="32" y="94" font-family="-apple-system, Segoe UI, Microsoft YaHei, sans-serif" font-size="10" fill="{INK2}">{_e(subtitle)}</text>
  <line x1="32" y1="108" x2="868" y2="108" stroke="{LINE}"/>
  {''.join(stats_svg)}
  <line x1="32" y1="184" x2="868" y2="184" stroke="{LINE}"/>
  <text x="32" y="200" font-family="Consolas, monospace" font-size="8" letter-spacing="1" fill="{MUTED}">MONTHLY RHYTHM</text>
  <text x="448" y="200" text-anchor="end" font-family="Consolas, monospace" font-size="8" fill="{ACCENT}">峰值 {peak} 次</text>
  {''.join(bars)}
  <text x="500" y="200" font-family="Consolas, monospace" font-size="8" letter-spacing="1" fill="{MUTED}">CONTRIBUTION</text>
  <text x="868" y="200" text-anchor="end" font-family="Consolas, monospace" font-size="8" fill="{MUTED}">{stats.active_days} 个活跃日</text>
  {_heatmap(stats)}
  <line x1="32" y1="320" x2="868" y2="320" stroke="{LINE}"/>
  <text x="32" y="336" font-family="Consolas, monospace" font-size="8" letter-spacing="1" fill="{MUTED}">LANGUAGES</text>
  {''.join(lang_bar)}
  {''.join(lang_legend)}
  <text x="500" y="336" font-family="Consolas, monospace" font-size="8" letter-spacing="1" fill="{MUTED}">TOP REPOS</text>
  {''.join(repo_rows)}
  <line x1="32" y1="440" x2="868" y2="440" stroke="{LINE}"/>
  {''.join(records)}
  <line x1="32" y1="510" x2="868" y2="510" stroke="{LINE}"/>
  <text x="32" y="528" font-family="Consolas, monospace" font-size="7" fill="{MUTED}">CODEYEAR · {stats.year} · {_e(footer)}</text>
  <text x="868" y="528" text-anchor="end" font-family="Consolas, monospace" font-size="7" fill="{MUTED}">{_e(right_footer)}</text>
</svg>
"""


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def render(stats: ReportStats, out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_svg(stats), encoding="utf-8")
    return path
