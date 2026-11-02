"""Render a shareable 1200x1600 PNG poster with Pillow."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .stats import ReportStats, fmt_signed_pair, language_breakdown, parse_daily

W, H = 1200, 1600
M = 72

BG_TOP = (7, 11, 20)
BG_BOTTOM = (12, 20, 38)
GRID = (10, 16, 30)
PANEL = (13, 20, 36)
LINE = (28, 39, 64)
TEXT = (232, 238, 249)
MUTED = (139, 152, 176)
DIM = (17, 26, 46)
ACCENT = (94, 234, 212)
AMBER = (251, 191, 36)
PALETTE = [
    (94, 234, 212), (56, 189, 248), (167, 139, 250),
    (251, 191, 36), (251, 113, 133), (52, 211, 153),
]

_FONT_PATHS: dict[str, list[str]] = {
    "regular": [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ],
    "bold": [
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/msyhbd.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ],
    "mono": [
        "C:/Windows/Fonts/consola.ttf",
        "C:/Windows/Fonts/consolab.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",
    ],
}
_FONT_CACHE: dict[tuple[int, str], ImageFont.FreeTypeFont] = {}


def _font(size: int, kind: str = "regular") -> ImageFont.FreeTypeFont:
    key = (size, kind)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for path in _FONT_PATHS.get(kind, []):
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size)
                _FONT_CACHE[key] = font
                return font
            except OSError:
                continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


def _gradient(width: int, height: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    strip = Image.new("RGB", (1, height))
    px = strip.load()
    for y in range(height):
        t = y / max(height - 1, 1)
        px[0, y] = tuple(round(top[i] + (bottom[i] - top[i]) * t) for i in range(3))
    return strip.resize((width, height), Image.Resampling.BILINEAR)


def _mix(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = max(0.0, min(1.0, t))
    return tuple(round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _ellipsize(draw: ImageDraw.ImageDraw, text: str, font, max_width: float) -> str:
    if not text:
        return text
    if draw.textlength(text, font=font) <= max_width:
        return text
    ell = "…"
    while text and draw.textlength(text + ell, font=font) > max_width:
        text = text[:-1]
    return text + ell


_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]|[^\u4e00-\u9fff\s]+|\s+")


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_width: float, max_lines: int) -> list[str]:
    tokens = _TOKEN_RE.findall(text)
    lines: list[str] = []
    cur = ""
    for tok in tokens:
        if tok.isspace():
            if cur:
                cur += " "
            continue
        candidate = cur + tok
        if draw.textlength(candidate, font=font) <= max_width:
            cur = candidate
        else:
            if cur.strip():
                lines.append(cur.strip())
            cur = tok
    if cur.strip():
        lines.append(cur.strip())

    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = _ellipsize(draw, lines[-1] + "…", font, max_width)
    return lines


def _big(n: int) -> str:
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return f"{n:,}"


def _spaced(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill, spacing: int) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def _header(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _spaced(draw, (M, 56), "CODEYEAR", _font(21, "mono"), ACCENT, 7)
    draw.text((W - M, 62), "代码年报", font=_font(17), fill=MUTED, anchor="ra")

    draw.text((M - 4, 88), str(stats.year), font=_font(132, "bold"), fill=TEXT, anchor="lt")

    span = "—"
    if stats.first_dt and stats.last_dt:
        span = f"{stats.first_dt:%Y.%m.%d} — {stats.last_dt:%Y.%m.%d}"
    meta = f"{stats.root}   ·   {stats.repo_count} 个仓库   ·   {span}"
    meta = _ellipsize(draw, meta, _font(16), W - 2 * M)
    draw.text((M, 276), meta, font=_font(16), fill=MUTED)

    draw.line((M, 316, W - M, 316), fill=LINE, width=1)


def _persona(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    eyebrow_font = _font(12, "mono")
    _spaced(draw, (M, 344), "YOUR CODING PERSONA", eyebrow_font, ACCENT, 4)

    title_font = _font(46, "bold")
    title = _ellipsize(draw, stats.persona.title, title_font, W - 2 * M)
    draw.text((M - 2, 366), title, font=title_font, fill=TEXT)

    body_font = _font(18)
    lines = _wrap(draw, stats.persona.subtitle, body_font, W - 2 * M, max_lines=2)
    for i, line in enumerate(lines):
        draw.text((M, 436 + i * 28), line, font=body_font, fill=MUTED)

    # Trait chips
    chip_font = _font(13)
    x, y = M, 508
    for trait in stats.persona.traits:
        width = draw.textlength(trait, font=chip_font) + 26
        draw.rounded_rectangle((x, y, x + width, y + 30), radius=15, fill=DIM, outline=LINE)
        draw.text((x + 13, y + 7), trait, font=chip_font, fill=(205, 217, 234))
        x += width + 9


def _stats(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    label_font = _font(12)
    value_font = _font(43, "bold")
    sub_font = _font(14)
    col_w = (W - 2 * M) // 4
    base_y = 570

    active_pct = stats.active_days / (366 if _is_leap(stats.year) else 365)
    items = [
        ("提交次数  COMMITS", f"{stats.commit_count:,}", f"跨 {stats.repo_count} 个仓库"),
        ("代码行变更  LINES", _big(stats.lines_changed),
         fmt_signed_pair(stats.insertions, stats.deletions)),
        ("活跃天数  ACTIVE", str(stats.active_days), f"占全年 {active_pct:.0%}"),
        ("最长连续  STREAK", str(stats.longest_streak), f"当前连续 {stats.current_streak} 天"),
    ]

    for i, (label, value, sub) in enumerate(items):
        x = M + i * col_w
        draw.text((x, base_y), label, font=label_font, fill=MUTED)
        draw.text((x - 1, base_y + 20), value, font=value_font, fill=TEXT)
        draw.text((x, base_y + 82), sub, font=sub_font, fill=MUTED)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _heatmap(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    draw.text((M, 684), "提交热力图", font=_font(15), fill=MUTED)
    draw.text((M + 82, 687), "CONTRIBUTION", font=_font(10, "mono"), fill=ACCENT)
    draw.text((W - M, 687), "少 → 多", font=_font(11), fill=(101, 114, 138), anchor="ra")

    daily = parse_daily(stats.daily)
    start = date(stats.year, 1, 1)
    end = date(stats.year, 12, 31)
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=6 - end.weekday())
    cols = (grid_end - grid_start).days // 7 + 1

    cell, gap = 14, 5
    x0 = (W - (cols * cell + (cols - 1) * gap)) // 2
    y0 = 730

    # Month markers
    for month in range(1, 13):
        col = (date(stats.year, month, 1) - grid_start).days // 7
        draw.text((x0 + col * (cell + gap), 710), f"{month:02d}",
                  font=_font(9, "mono"), fill=(101, 114, 138))

    for col in range(cols):
        for row in range(7):
            day = grid_start + timedelta(days=col * 7 + row)
            if day < start or day > end:
                continue
            count = daily.get(day, 0)
            if count == 0:
                color = DIM
            elif count == 1:
                color = (22, 78, 99)
            elif count <= 3:
                color = (14, 116, 144)
            elif count <= 6:
                color = (34, 211, 238)
            else:
                color = (165, 243, 252)
            x = x0 + col * (cell + gap)
            y = y0 + row * (cell + gap)
            draw.rounded_rectangle((x, y, x + cell, y + cell), radius=3, fill=color)


def _hours(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    draw.text((M, 894), "提交时段", font=_font(15), fill=MUTED)
    draw.text((M + 68, 897), "HOURS", font=_font(10, "mono"), fill=ACCENT)

    max_v = max(stats.by_hour) or 1
    peak = stats.by_hour.index(max_v)
    draw.text((W - M, 896), f"峰值 {peak:02d}:00 · {max_v} 次",
              font=_font(13), fill=AMBER, anchor="ra")

    baseline = 1060
    max_height = 130
    bar_w, gap = 36, 8
    x0 = M

    for hour, value in enumerate(stats.by_hour):
        x = x0 + hour * (bar_w + gap)
        height = int(value / max_v * max_height) if value else 2
        height = max(height, 2)
        t = value / max_v if max_v else 0
        color = AMBER if (value == max_v and value > 0) else _mix((22, 78, 99), ACCENT, t)
        draw.rounded_rectangle(
            (x, baseline - height, x + bar_w, baseline),
            radius=4,
            fill=color,
        )

    draw.line((M, baseline, W - M, baseline), fill=LINE, width=1)

    for hour in (0, 6, 12, 18, 23):
        cx = x0 + hour * (bar_w + gap) + bar_w / 2
        draw.text((cx, baseline + 10), f"{hour:02d}", font=_font(10, "mono"),
                  fill=(101, 114, 138), anchor="ma")


def _languages(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    draw.text((M, 1114), "语言分布", font=_font(15), fill=MUTED)
    draw.text((M + 68, 1117), "LANGUAGES", font=_font(10, "mono"), fill=ACCENT)

    rows, total = language_breakdown(stats.languages, limit=4, min_share=0.01)
    if not rows:
        draw.text((M, 1158), "没有可统计的代码文件", font=_font(14), fill=(101, 114, 138))
        return

    name_font = _font(16)
    pct_font = _font(13)
    for i, (name, lines) in enumerate(rows):
        y = 1156 + i * 38
        pct = lines / total
        color = PALETTE[i % len(PALETTE)]

        label = _ellipsize(draw, name, name_font, 108)
        draw.text((M, y), label, font=name_font, fill=TEXT)

        bar_x, bar_w, bar_h = 196, 700, 8
        draw.rounded_rectangle((bar_x, y + 10, bar_x + bar_w, y + 10 + bar_h),
                               radius=4, fill=DIM)
        fill_w = max(int(bar_w * pct), 6)
        draw.rounded_rectangle((bar_x, y + 10, bar_x + fill_w, y + 10 + bar_h),
                               radius=4, fill=color)

        draw.text((W - M, y - 1), f"{pct:.0%}", font=pct_font, fill=MUTED, anchor="ra")


def _files(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    draw.text((M, 1374), "最常改的文件", font=_font(15), fill=MUTED)
    draw.text((M + 96, 1377), "MOST EDITED FILES", font=_font(10, "mono"), fill=ACCENT)

    rows = stats.top_files[:4]
    if not rows:
        draw.text((M, 1412), "暂无数据", font=_font(14), fill=(101, 114, 138))
        return

    idx_font = _font(10, "mono")
    path_font = _font(14)
    val_font = _font(12)
    for i, (path, lines) in enumerate(rows):
        y = 1408 + i * 28
        draw.text((M, y + 2), f"{i + 1:02d}", font=idx_font, fill=AMBER)
        display = _ellipsize(draw, path, path_font, 880)
        draw.text((M + 34, y), display, font=path_font, fill=(205, 217, 234))
        draw.text((W - M, y + 1), f"{_big(lines)} 行", font=val_font,
                  fill=MUTED, anchor="ra")


def _footer(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    draw.line((M, 1540, W - M, 1540), fill=LINE, width=1)
    draw.text((M, 1556), "LOCAL-FIRST · NO DATA UPLOADED",
              font=_font(10, "mono"), fill=(101, 114, 138))
    draw.text((W - M, 1556), f"codeyear · {stats.year}",
              font=_font(10, "mono"), fill=(101, 114, 138), anchor="ra")


def render(stats: ReportStats, out_path: str | Path) -> Path:
    img = _gradient(W, H, BG_TOP, BG_BOTTOM)
    draw = ImageDraw.Draw(img)

    for x in range(0, W, 48):
        draw.line((x, 0, x, H), fill=GRID, width=1)
    for y in range(0, H, 48):
        draw.line((0, y, W, y), fill=GRID, width=1)

    _header(draw, stats)
    _persona(draw, stats)
    _stats(draw, stats)
    _heatmap(draw, stats)
    _hours(draw, stats)
    _languages(draw, stats)
    _files(draw, stats)
    _footer(draw, stats)

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return path
