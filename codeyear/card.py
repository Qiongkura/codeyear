"""Render a compact SVG card for a GitHub profile README."""

from __future__ import annotations

import html
from datetime import date, timedelta
from pathlib import Path

from .stats import ReportStats, fmt_human, fmt_int, fmt_signed_pair, parse_daily

W, H = 900, 400
PAPER = "#f4f1e8"
PAPER2 = "#eceadf"
INK = "#171512"
INK2 = "#403c33"
MUTED = "#6f6a5e"
LINE = "#d9d3c2"
ACCENT = "#d4491f"
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
    x0, y0 = 500, 246
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


def build_svg(stats: ReportStats) -> str:
    monthly = stats.monthly
    peak = max(monthly) or 1
    bars = []
    bar_w, gap = 26, 8
    baseline = 330
    for i, value in enumerate(monthly):
        x = 32 + i * (bar_w + gap)
        height = max(int(value / peak * 60), 2)
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
            f'<text x="{x}" y="146" font-family="Consolas, monospace" '
            f'font-size="8" letter-spacing="1" fill="{MUTED}">{_e(label)}</text>'
        )
        stats_svg.append(
            f'<text x="{x}" y="174" font-family="Consolas, monospace" '
            f'font-size="24" fill="{INK}">{_e(value)}</text>'
        )
        stats_svg.append(
            f'<text x="{x}" y="192" font-family="Consolas, monospace" '
            f'font-size="8" fill="{MUTED}">{_e(sub)}</text>'
        )

    title = _truncate(stats.persona.title, 24)
    subtitle = _truncate(stats.persona.subtitle, 78)
    footer = "generated locally · no data uploaded"
    right_footer = f"深夜 {stats.night_share:.0%} · 周末 {stats.weekend_share:.0%}"

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="CodeYear {stats.year} · {_e(title)}">
  <title>CodeYear {stats.year} · {_e(title)}</title>
  <rect width="{W}" height="{H}" fill="{PAPER}"/>
  <line x1="0" y1="0" x2="{W}" y2="0" stroke="{ACCENT}" stroke-width="2"/>
  <text x="32" y="38" font-family="Consolas, monospace" font-size="11" letter-spacing="3" fill="{ACCENT}">CODEYEAR</text>
  <text x="868" y="38" text-anchor="end" font-family="Consolas, monospace" font-size="9" fill="{MUTED}">{stats.year} · LOCAL-FIRST</text>
  <text x="32" y="80" font-family="Georgia, Songti SC, SimSun, serif" font-size="30" fill="{INK}">{_e(title)}</text>
  <text x="32" y="104" font-family="-apple-system, Segoe UI, Microsoft YaHei, sans-serif" font-size="11" fill="{INK2}">{_e(subtitle)}</text>
  <line x1="32" y1="120" x2="868" y2="120" stroke="{LINE}"/>
  {''.join(stats_svg)}
  <line x1="32" y1="210" x2="868" y2="210" stroke="{LINE}"/>
  <text x="32" y="232" font-family="Consolas, monospace" font-size="8" letter-spacing="1" fill="{MUTED}">MONTHLY RHYTHM</text>
  <text x="448" y="232" text-anchor="end" font-family="Consolas, monospace" font-size="8" fill="{ACCENT}">峰值 {peak} 次</text>
  {''.join(bars)}
  <text x="500" y="232" font-family="Consolas, monospace" font-size="8" letter-spacing="1" fill="{MUTED}">CONTRIBUTION</text>
  {_heatmap(stats)}
  <text x="500" y="318" font-family="Consolas, monospace" font-size="8" fill="{MUTED}">{stats.active_days} 个活跃日 · 2026</text>
  <line x1="32" y1="360" x2="868" y2="360" stroke="{LINE}"/>
  <text x="32" y="380" font-family="Consolas, monospace" font-size="8" fill="{MUTED}">CODEYEAR · {stats.year} · {_e(footer)}</text>
  <text x="868" y="380" text-anchor="end" font-family="Consolas, monospace" font-size="8" fill="{MUTED}">{_e(right_footer)}</text>
</svg>
"""


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def render(stats: ReportStats, out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_svg(stats), encoding="utf-8")
    return path
