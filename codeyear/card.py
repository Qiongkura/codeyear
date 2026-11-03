"""Render a large, transparent SVG card for a GitHub profile README."""

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

W, H = 640, 1070
M = 28
RIGHT = W - M
COL4 = 146
MONO = "Consolas, 'SFMono-Regular', Menlo, monospace"
SANS = "-apple-system, 'Segoe UI', 'Microsoft YaHei', sans-serif"
SERIF = "Georgia, 'Songti SC', SimSun, serif"

LIGHT = {
    "ink": "#141413",
    "ink2": "#3d3d3a",
    "muted": "#73726c",
    "line": "#d9d7cd",
    "accent": "#d97757",
    "bar": "#cfcbbe",
    "palette": ["#141413", "#d97757", "#8f8d84", "#b8b5aa", "#ddd9cc"],
    "levels": ["#e7e4da", "#ddd8ca", "#b8b2a0", "#6f6a5e", "#d97757"],
}

DARK = {
    "ink": "#f0eee6",
    "ink2": "#d5d2c8",
    "muted": "#9a978e",
    "line": "#3a3936",
    "accent": "#e08a68",
    "bar": "#4a4843",
    "palette": ["#f0eee6", "#e08a68", "#9a978e", "#7a7770", "#55534d"],
    "levels": ["#262623", "#3a3936", "#5c5952", "#9a978e", "#e08a68"],
}


def _e(value: str) -> str:
    return html.escape(str(value), quote=True)


def _truncate(text: str, limit: int) -> str:
    text = (text or "").strip()
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _text(
    x: float,
    y: float,
    text: str,
    size: float,
    fill: str,
    *,
    family: str = MONO,
    anchor: str | None = None,
    spacing: float | None = None,
) -> str:
    attrs = [
        f'x="{x}"',
        f'y="{y}"',
        f'font-family="{family}"',
        f'font-size="{size}"',
        f'fill="{fill}"',
    ]
    if anchor:
        attrs.append(f'text-anchor="{anchor}"')
    if spacing is not None:
        attrs.append(f'letter-spacing="{spacing}"')
    return f'<text {" ".join(attrs)}>{_e(text)}</text>'


def _rule(y: float, color: str) -> str:
    return f'<line x1="{M}" y1="{y}" x2="{RIGHT}" y2="{y}" stroke="{color}"/>'


def _metric(x: float, y: float, number: str, unit: str, c: dict,
            size: float = 28) -> str:
    """One hero number per insight, with a small muted unit."""
    if not unit:
        return _text(x - 1, y, number, size, c["ink"], family=SERIF)
    dx = 1 if unit in {"%", ":1"} else 4
    return (
        f'<text x="{x - 1}" y="{y}" font-family="{SERIF}" font-size="{size}" '
        f'fill="{c["ink"]}">{_e(number)}'
        f'<tspan font-size="12.5" fill="{c["muted"]}" dx="{dx}">{_e(unit)}</tspan></text>'
    )


def _heatmap(stats: ReportStats, c: dict, x0: float, y0: float,
             cell: float = 8, gap: float = 2) -> str:
    daily = parse_daily(stats.daily)
    start = date(stats.year, 1, 1)
    end = date(stats.year, 12, 31)
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=6 - end.weekday())

    rects = []
    cursor = grid_start
    while cursor <= grid_end:
        if start <= cursor <= end:
            col = (cursor - grid_start).days // 7
            row = cursor.weekday()
            count = daily.get(cursor, 0)
            if count:
                if count == 1:
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
                    f'fill="{c["levels"][level]}"/>'
                )
        cursor += timedelta(days=1)
    return "".join(rects)


def build_svg(stats: ReportStats, *, dark: bool = False) -> str:
    c = DARK if dark else LIGHT
    monthly = stats.monthly
    peak = max(monthly) or 1
    peak_month = monthly.index(peak) + 1 if peak else 1
    peak_hour = stats.by_hour.index(max(stats.by_hour)) if any(stats.by_hour) else 0
    owner = (stats.identity_label or "").split(" <")[0].strip()

    # ---- header -------------------------------------------------------
    title = _truncate(stats.persona.title, 24)
    subtitle = stats.persona.subtitle
    subtitle_parts = subtitle.split("。", 1)
    sub_lines = [subtitle_parts[0] + ("。" if len(subtitle_parts) > 1 else "")]
    if len(subtitle_parts) > 1:
        sub_lines.append(subtitle_parts[1])

    header = [
        f'<rect x="0" y="0" width="{W}" height="3" fill="{c["accent"]}"/>',
        _text(M, 30, f"CODEYEAR · {stats.year}", 9, c["accent"], spacing=2.4),
        (
            _text(RIGHT, 32, _truncate(owner, 26), 17, c["ink"], family=SERIF,
                  anchor="end")
            if owner
            else _text(RIGHT, 30, "LOCAL-FIRST", 9, c["muted"], anchor="end")
        ),
        _text(M - 1, 82, title, 36, c["ink"], family=SERIF),
    ]
    for i, line in enumerate(sub_lines[:2]):
        header.append(_text(M, 108 + i * 20, line, 11.5, c["ink2"], family=SANS))
    header.append(_rule(142, c["line"]))

    # ---- six summary tiles -------------------------------------------
    tiles = [
        ("COMMITS / 提交", fmt_int(stats.commit_count), "年度提交"),
        ("LINES / 行变更", fmt_human(stats.lines_changed),
         fmt_signed_pair(stats.insertions, stats.deletions)),
        ("ACTIVE / 活跃天", str(stats.active_days),
         f"占全年 {stats.active_days / (366 if _is_leap(stats.year) else 365):.0%}"),
        ("STREAK / 最长连续", str(stats.longest_streak),
         f"当前 {stats.current_streak} 天"),
        ("REPOS / 仓库", str(stats.repo_count), f"今年新开 {stats.new_repos}"),
        ("TOTAL / 累计", fmt_int(stats.total_commits), "仓库全历史"),
    ]
    tile_svg = []
    for i, (label, value, sub) in enumerate(tiles):
        row, col = divmod(i, 3)
        x = M + col * 194.6
        y = row * 88
        tile_svg.append(_text(x, 164 + y, label, 10, c["muted"], spacing=0.6))
        tile_svg.append(_text(x - 1, 208 + y, value, 36, c["ink"], family=SERIF))
        tile_svg.append(_text(x, 226 + y, sub, 9.5, c["muted"]))
    tile_svg.append(_rule(332, c["line"]))

    # ---- monthly rhythm ----------------------------------------------
    bars = []
    bar_w, gap = 40, 8
    baseline = 430
    for i, value in enumerate(monthly):
        x = M + i * (bar_w + gap)
        height = max(int(value / peak * 66), 2)
        fill = c["accent"] if value == peak and value > 0 else c["ink"]
        bars.append(
            f'<rect x="{x}" y="{baseline - height}" width="{bar_w}" '
            f'height="{height}" fill="{fill}"/>'
        )
        bars.append(_text(x + bar_w / 2, baseline + 14, f"{i + 1:02d}", 9.5,
                          c["muted"], anchor="middle"))

    # ---- full-width contribution heatmap -----------------------------
    cell, gap_h = 8, 2
    grid_start = date(stats.year, 1, 1)
    grid_start -= timedelta(days=grid_start.weekday())
    grid_end = date(stats.year, 12, 31)
    grid_end += timedelta(days=6 - grid_end.weekday())
    grid_cols = (grid_end - grid_start).days // 7 + 1
    grid_w = grid_cols * (cell + gap_h) - gap_h
    grid_x = (W - grid_w) / 2

    charts = [
        _text(M, 350, "MONTHLY RHYTHM", 10, c["muted"], spacing=1),
        _text(RIGHT, 350, f"峰值 {peak_month:02d} 月 · {peak} 次", 10, c["accent"],
              anchor="end"),
        *bars,
        _rule(462, c["line"]),
        _text(M, 480, "CONTRIBUTION", 10, c["muted"], spacing=1),
        _text(RIGHT, 480, f"{stats.active_days} 个活跃日", 10, c["muted"], anchor="end"),
        _heatmap(stats, c, grid_x, 498, cell, gap_h),
        _rule(582, c["line"]),
    ]

    # ---- derived insights ---------------------------------------------
    cols2 = [M, M + 306]
    top_repo = stats.repo_details[0] if stats.repo_details else None
    if top_repo and stats.commit_count:
        share = top_repo["commits"] / stats.commit_count
        focus_num, focus_unit = f"{share * 100:.0f}", "%"
        focus_sub = f"{_truncate(top_repo['name'], 20)} · {fmt_int(top_repo['commits'])} 次"
    else:
        focus_num, focus_unit, focus_sub = "—", "", "暂无数据"

    night, weekend = stats.night_share, stats.weekend_share
    rhythm_num, rhythm_unit = f"{peak_hour:02d}:00", ""
    rhythm_sub = f"深夜 {night:.0%} · 周末 {weekend:.0%}"

    size_map = dict(stats.size_buckets)
    size_total = sum(size_map.values()) or 1
    small_share = (size_map.get("0–10", 0) + size_map.get("10–100", 0)) / size_total
    large_share = (size_map.get("500–2k", 0) + size_map.get("2k+", 0)) / size_total
    if small_share >= 0.6:
        style_kind = "小步迭代"
    elif large_share >= 0.35:
        style_kind = "大提交"
    else:
        style_kind = "中等粒度"
    style_num, style_unit = f"{small_share * 100:.0f}", "%"
    style_sub = f"{style_kind} · 大提交 {large_share:.0%}"

    sessions = stats.sessions or {}
    sess_count = int(sessions.get("count") or 0)
    avg_min = int(sessions.get("avg_minutes") or 0)
    if avg_min >= 90:
        pace_kind = "沉浸型"
    elif avg_min >= 45:
        pace_kind = "专注型"
    elif avg_min > 0:
        pace_kind = "碎片型"
    else:
        pace_kind = ""
    if avg_min:
        if avg_min >= 90:
            pace_num, pace_unit = f"{avg_min / 60:.1f}", "小时"
        else:
            pace_num, pace_unit = str(avg_min), "分钟"
        pace_sub = f"{pace_kind} · {sess_count} 次会话"
    else:
        pace_num, pace_unit, pace_sub = "—", "", "暂无会话"

    churn_total = stats.insertions + stats.deletions
    deletion_share = stats.deletions / churn_total if churn_total else 0
    ratio = stats.insertions / stats.deletions if stats.deletions else 0
    if deletion_share >= 0.5:
        churn_kind = "重构型"
    elif deletion_share >= 0.3:
        churn_kind = "平衡型"
    else:
        churn_kind = "扩张型"
    if ratio:
        churn_num, churn_unit = f"{ratio:.1f}", ":1"
        churn_sub = f"{churn_kind} · 删除占 {deletion_share:.0%}"
    else:
        churn_num, churn_unit = "只增", ""
        churn_sub = f"{churn_kind} · 没有删除"

    peak_share = peak / max(stats.commit_count, 1)
    burst_num, burst_unit = f"{peak_share * 100:.0f}", "%"
    burst_sub = f"{peak_month:02d} 月 · {peak} 次提交"

    top2 = sum(repo["commits"] for repo in stats.repo_details[:2])
    top2_share = top2 / max(stats.commit_count, 1)
    breadth_num, breadth_unit = f"{top2_share * 100:.0f}", "%"
    breadth_sub = f"前 2 个项目 · 共 {stats.repo_count} 个仓库"

    msg_map = dict(stats.message_buckets)
    msg_total = sum(msg_map.values()) or 1
    mid_share = msg_map.get("40–80", 0) / msg_total
    avg_subject = stats.avg_subject_len
    if avg_subject >= 50:
        msg_kind = "详细型"
    elif avg_subject <= 25:
        msg_kind = "简洁型"
    else:
        msg_kind = "适中"
    msg_num, msg_unit = str(avg_subject), "字"
    msg_sub = f"{msg_kind} · {mid_share:.0%} 在 40–80 字"

    insights = [
        ("主力项目 / FOCUS", focus_num, focus_unit, focus_sub),
        ("峰值时段 / RHYTHM", rhythm_num, rhythm_unit, rhythm_sub),
        ("提交粒度 / GRAIN", style_num, style_unit, style_sub),
        ("平均会话 / SESSIONS", pace_num, pace_unit, pace_sub),
        ("增删比 / CHURN", churn_num, churn_unit, churn_sub),
        ("峰值月份 / BURST", burst_num, burst_unit, burst_sub),
        ("项目集中度 / SCOPE", breadth_num, breadth_unit, breadth_sub),
        ("消息长度 / MESSAGES", msg_num, msg_unit, msg_sub),
    ]
    insight_svg = [
        _text(M, 600, "INSIGHTS / 观察", 10, c["muted"], spacing=1),
        f'<line x1="321" y1="600" x2="321" y2="862" stroke="{c["line"]}"/>',
    ]
    for i, (label, number, unit, sub) in enumerate(insights):
        row, col = divmod(i, 2)
        x = cols2[col]
        top = 628 + row * 58
        insight_svg.append(_text(x, top, label, 10, c["muted"], spacing=0.4))
        insight_svg.append(_metric(x, top + 26, number, unit, c))
        insight_svg.append(_text(x, top + 44, sub, 10, c["muted"]))
    insight_svg.append(_rule(862, c["line"]))

    # ---- four detail columns ------------------------------------------
    cols4 = [M + i * COL4 for i in range(4)]
    row_y = [904 + i * 24 for i in range(5)]
    sections = []

    # Four named languages + the "其他" bucket keeps the column at five rows.
    lang_rows, lang_total = language_breakdown(stats.languages, limit=4, min_share=0.01)
    lang_total = lang_total or 1
    sections.append(_text(cols4[0], 880, f"LANGUAGES · {stats.language_count} 种", 10,
                          c["muted"], spacing=0.6))
    for i, (name, value) in enumerate(lang_rows[:5]):
        y = row_y[i]
        sections.append(_text(cols4[0], y, _truncate(name, 18), 11, c["ink2"]))
        sections.append(_text(cols4[0] + COL4 - 12, y, f"{value / lang_total * 100:.0f}%",
                              10.5, c["muted"], anchor="end"))
        track_w = COL4 - 12
        width = int(track_w * value / lang_total)
        sections.append(
            f'<rect x="{cols4[0]}" y="{y + 9}" width="{track_w}" height="2" '
            f'fill="{c["line"]}"/>'
        )
        sections.append(
            f'<rect x="{cols4[0]}" y="{y + 9}" width="{width}" height="2" '
            f'fill="{c["palette"][i % len(c["palette"])]}"/>'
        )

    type_rows = stats.commit_types[:5]
    type_total = sum(value for _, value in stats.commit_types) or 1
    sections.append(_text(cols4[1], 880, "COMMIT TYPES", 10, c["muted"], spacing=0.6))
    for i, (name, value) in enumerate(type_rows[:5]):
        y = row_y[i]
        sections.append(_text(cols4[1], y, _truncate(name, 14), 11, c["ink2"]))
        sections.append(_text(cols4[1] + COL4 - 12, y, fmt_int(value), 10.5,
                              c["muted"], anchor="end"))
        track_w = COL4 - 12
        width = int(track_w * value / type_total)
        sections.append(
            f'<rect x="{cols4[1]}" y="{y + 9}" width="{track_w}" height="2" '
            f'fill="{c["line"]}"/>'
        )
        sections.append(
            f'<rect x="{cols4[1]}" y="{y + 9}" width="{width}" height="2" '
            f'fill="{c["ink2"]}"/>'
        )

    repos = stats.repo_details[:4]
    max_commits = max((r["commits"] for r in repos), default=1)
    sections.append(_text(cols4[2], 880, f"TOP REPOS · {stats.repo_count} 个", 10,
                          c["muted"], spacing=0.6))
    for i, repo in enumerate(repos):
        y = row_y[i]
        sections.append(_text(cols4[2], y, _truncate(repo["name"], 18), 11,
                              c["ink2"]))
        sections.append(_text(cols4[2] + COL4 - 12, y, fmt_int(repo["commits"]), 10.5,
                              c["muted"], anchor="end"))
        width = int((COL4 - 12) * repo["commits"] / max_commits)
        sections.append(
            f'<rect x="{cols4[2]}" y="{y + 8}" width="{width}" height="2" '
            f'fill="{c["ink2"]}"/>'
        )

    record_items: list[tuple[str, str]] = []
    if stats.busiest_day:
        day, count = stats.busiest_day
        record_items.append(("最忙一天", f"{count} 次 · {day[5:].replace('-', '.')}"))
    if stats.busiest_week:
        _week, count = stats.busiest_week
        when = (stats.busiest_week_start or "")[5:].replace("-", ".")
        record_items.append(("最忙一周", f"{count} 次 · {when}" if when else f"{count} 次"))
    if stats.longest_gap:
        days, start, end = stats.longest_gap
        span = start[5:].replace("-", ".")
        record_items.append(("最长空窗", f"{days} 天 · {span}"))
    if stats.largest_commit:
        record_items.append(("最大提交", f"{fmt_int(stats.largest_commit['lines'])} 行"))
    if stats.top_files:
        path, _lines = stats.top_files[0]
        record_items.append(("最常改文件", _truncate(path.split("/")[-1], 24)))
    sections.append(_text(cols4[3], 880, "RECORDS / 年度之最", 10, c["muted"],
                          spacing=0.6))
    for i, (label, value) in enumerate(record_items[:5]):
        y = row_y[i]
        sections.append(_text(cols4[3], y, label, 10.5, c["muted"]))
        sections.append(_text(cols4[3] + COL4 - 12, y, value, 10.5, c["ink2"],
                              anchor="end"))

    # ---- footer -------------------------------------------------------
    meta_parts = []
    if stats.earliest_dt:
        meta_parts.append(f"最早提交 {stats.earliest_dt:%Y.%m}")
    if stats.tags_in_year:
        meta_parts.append(f"今年 {stats.tags_in_year} 个版本 tag")
    meta_line = " · ".join(meta_parts)
    right_footer = f"生成于 {stats.generated_at.replace('-', '.')}"
    footer = [
        _rule(1018, c["line"]),
        _text(M, 1036, meta_line, 9, c["muted"]),
        _text(RIGHT, 1036, right_footer, 9, c["muted"], anchor="end"),
        _text(M, 1054, f"CODEYEAR · {stats.year} · generated locally · no data uploaded",
              8.5, c["muted"]),
        _text(RIGHT, 1054, "LOCAL ONLY", 8.5, c["accent"], anchor="end", spacing=1),
    ]

    label = f"{owner} · CodeYear {stats.year} · {title}" if owner else (
        f"CodeYear {stats.year} · {title}"
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{_e(label)}">
  <title>{_e(label)}</title>
  {''.join(header)}
  {''.join(tile_svg)}
  {''.join(charts)}
  {''.join(insight_svg)}
  {''.join(sections)}
  {''.join(footer)}
</svg>
"""


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def render(stats: ReportStats, out_path: str | Path) -> list[Path]:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    paths = [path]
    path.write_text(build_svg(stats), encoding="utf-8")

    dark_path = path.with_name(f"{path.stem}-dark{path.suffix}")
    dark_path.write_text(build_svg(stats, dark=True), encoding="utf-8")
    paths.append(dark_path)
    return paths
