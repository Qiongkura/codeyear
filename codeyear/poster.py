"""Render a 1200x1600 shareable poster in the same paper/ink style as the HTML report."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .stats import ReportStats, fmt_signed_pair, language_breakdown, parse_daily

W, H = 1200, 1600
M = 64

PAPER = (244, 241, 232)
PAPER2 = (236, 234, 223)
INK = (23, 21, 18)
INK2 = (64, 60, 51)
MUTED = (111, 106, 94)
LINE = (217, 211, 194)
LINE2 = (200, 193, 172)
ACCENT = (212, 73, 31)
ACCENT2 = (178, 58, 21)

_FONT_PATHS: dict[str, list[str]] = {
    "serif": [
        "C:/Windows/Fonts/georgia.ttf",
        "C:/Windows/Fonts/times.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
        "/System/Library/Fonts/Supplemental/Georgia.ttf",
    ],
    "serifcn": [
        "C:/Windows/Fonts/simsun.ttc",
        "C:/Windows/Fonts/simsun.ttf",
        "C:/Windows/Fonts/STZHONGS.TTF",
        "/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ],
    "sans": [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyh.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
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


def _font(size: int, kind: str = "sans") -> ImageFont.FreeTypeFont:
    key = (size, kind)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for path in _FONT_PATHS.get(kind, []):
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size, index=0)
                _FONT_CACHE[key] = font
                return font
            except OSError:
                continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


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


def _spaced(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill,
            spacing: int) -> None:
    x, y = xy
    for ch in text:
        draw.text((x, y), ch, font=font, fill=fill)
        x += draw.textlength(ch, font=font) + spacing


def _is_cjk(ch: str) -> bool:
    return "\u4e00" <= ch <= "\u9fff" or ch in "，。：；！？、「」（）—·"


def _draw_text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str, font, fill,
               anchor: str = "la", cjk_font=None) -> None:
    """Draw mixed mono + CJK text without tofu glyphs."""
    if cjk_font is None or not any(_is_cjk(ch) for ch in text):
        draw.text(xy, text, font=font, fill=fill, anchor=anchor)
        return
    widths = [
        draw.textlength(ch, font=(cjk_font if _is_cjk(ch) else font))
        for ch in text
    ]
    total = sum(widths)
    x, y = xy
    if anchor.startswith("r"):
        x -= total
    elif anchor.startswith("m"):
        x -= total / 2
    for ch, width in zip(text, widths):
        glyph_font = cjk_font if _is_cjk(ch) else font
        draw.text((x, y), ch, font=glyph_font, fill=fill)
        x += width


def _rule(draw: ImageDraw.ImageDraw, y: int, color=LINE) -> None:
    draw.line((M, y, W - M, y), fill=color, width=1)


def _label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    _draw_text(draw, xy, text.upper(), _font(10, "mono"), MUTED,
               cjk_font=_font(10, "sans"))


def _header(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _spaced(draw, (M, 50), "CODEYEAR", _font(20, "mono"), ACCENT, 6)
    draw.text((W - M, 56), "代码手账", font=_font(15, "sans"), fill=MUTED, anchor="ra")

    draw.text((M - 5, 76), str(stats.year), font=_font(150, "serif"), fill=INK, anchor="lt")

    span = "—"
    if stats.first_dt and stats.last_dt:
        span = f"{stats.first_dt:%Y.%m.%d} — {stats.last_dt:%Y.%m.%d}"
    meta = f"{stats.root}   ·   {stats.repo_count} 个仓库   ·   {span}"
    _draw_text(draw, (M, 262),
               _ellipsize(draw, meta, _font(12, "mono"), W - 2 * M),
               _font(12, "mono"), MUTED, cjk_font=_font(12, "sans"))
    _rule(draw, 300)


def _persona(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _label(draw, (M, 322), "YOUR CODING YEAR")
    title = _ellipsize(draw, stats.persona.title, _font(42, "serifcn"), W - 2 * M)
    draw.text((M - 2, 338), title, font=_font(42, "serifcn"), fill=INK)

    body = _font(15, "sans")
    lines = _wrap(draw, stats.persona.subtitle, body, W - 2 * M, 2)
    for i, line in enumerate(lines):
        draw.text((M, 402 + i * 24), line, font=body, fill=INK2)


def _stats(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _rule(draw, 476)
    labels = ["COMMITS / 提交", "LINES / 行变更", "ACTIVE / 活跃天", "STREAK / 最长连续"]
    values = [
        f"{stats.commit_count:,}",
        _big(stats.lines_changed),
        str(stats.active_days),
        str(stats.longest_streak),
    ]
    subs = [
        f"{stats.repo_count} 个仓库",
        fmt_signed_pair(stats.insertions, stats.deletions),
        f"占全年 {stats.active_days / (366 if _is_leap(stats.year) else 365):.0%}",
        f"当前 {stats.current_streak} 天",
    ]
    col_w = (W - 2 * M) / 4
    for i, (label, value, sub) in enumerate(zip(labels, values, subs)):
        x = int(M + i * col_w)
        _draw_text(draw, (x, 494), label, _font(10, "mono"), MUTED,
                   cjk_font=_font(10, "sans"))
        _draw_text(draw, (x - 1, 510), value, _font(36, "mono"), INK,
                   cjk_font=_font(30, "sans"))
        _draw_text(draw, (x, 558),
                   _ellipsize(draw, sub, _font(10, "mono"), col_w - 18),
                   _font(10, "mono"), MUTED, cjk_font=_font(10, "sans"))
    _rule(draw, 590)


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


def _monthly(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _label(draw, (M, 612), "MONTHLY RHYTHM")
    max_v = max(stats.monthly) or 1
    peak = stats.monthly.index(max_v) + 1
    _draw_text(draw, (W - M, 612), f"峰值 {peak:02d} 月 · {max_v} 次",
               _font(11, "mono"), ACCENT, anchor="ra", cjk_font=_font(11, "sans"))

    baseline = 758
    max_h = 104
    gap = 10
    bar_w = int((W - 2 * M - gap * 11) / 12)
    for i, value in enumerate(stats.monthly):
        x = M + i * (bar_w + gap)
        h = max(int(value / max_v * max_h), 2 if value else 2)
        draw.rectangle((x, baseline - h, x + bar_w, baseline),
                       fill=ACCENT if value == max_v and value > 0 else INK)
    draw.line((M, baseline, W - M, baseline), fill=INK, width=1)
    for i in range(12):
        cx = M + i * (bar_w + gap) + bar_w / 2
        draw.text((cx, baseline + 7), f"{i + 1:02d}", font=_font(9, "mono"),
                  fill=MUTED, anchor="ma")


def _clock(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _label(draw, (M, 800), "7 × 24 CLOCK")
    flat = [v for row in stats.hour_weekday for v in row]
    max_v = max(flat) or 1

    def color(v: int) -> tuple[int, int, int]:
        if v == 0:
            return PAPER2
        if v <= max_v * 0.15:
            return (221, 214, 196)
        if v <= max_v * 0.35:
            return (168, 159, 136)
        if v <= max_v * 0.6:
            return (92, 85, 74)
        return INK

    days = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]
    label_w = 38
    gap = 3
    cell_w = 40
    cell_h = 14
    x0 = M + label_w
    y0 = 842

    for h in range(24):
        if h % 3 == 0:
            draw.text((x0 + h * (cell_w + gap) + cell_w / 2, 826), f"{h:02d}",
                      font=_font(8, "mono"), fill=MUTED, anchor="ma")

    for wd, row in enumerate(stats.hour_weekday):
        y = y0 + wd * (cell_h + 4)
        draw.text((M, y + 2), days[wd], font=_font(8, "mono"), fill=MUTED)
        for h, value in enumerate(row):
            x = x0 + h * (cell_w + gap)
            draw.rectangle((x, y, x + cell_w, y + cell_h), fill=color(value))

    _rule(draw, 972)


def _languages(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _label(draw, (M, 992), "LANGUAGES / 语言")
    rows, total = language_breakdown(stats.languages, limit=4, min_share=0.01)
    if not rows:
        draw.text((M, 1024), "没有可统计的代码文件", font=_font(12, "sans"), fill=MUTED)
        return

    palette = [INK, ACCENT, (143, 134, 114), (179, 171, 151), (200, 193, 172)]
    bar_x, bar_y, bar_w, bar_h = M, 1018, 500, 16
    x = bar_x
    for i, (_name, value) in enumerate(rows):
        w = int(bar_w * value / total)
        draw.rectangle((x, bar_y, x + w, bar_y + bar_h), fill=palette[i % len(palette)])
        x += w
    if x < bar_x + bar_w:
        draw.rectangle((x, bar_y, bar_x + bar_w, bar_y + bar_h),
                       fill=palette[len(rows) % len(palette)])

    for i, (name, value) in enumerate(rows):
        y = 1048 + i * 25
        draw.rectangle((M, y + 2, M + 8, y + 10), fill=palette[i % len(palette)])
        draw.text((M + 18, y), _ellipsize(draw, name, _font(11, "sans"), 300),
                  font=_font(11, "sans"), fill=INK2)
        draw.text((M + 500, y), f"{value / total * 100:.0f}%", font=_font(10, "mono"),
                  fill=MUTED, anchor="ra")


def _files(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    x = 620
    _label(draw, (x, 992), "MOST EDITED FILES")
    rows = stats.top_files[:4]
    if not rows:
        draw.text((x, 1024), "暂无数据", font=_font(12, "sans"), fill=MUTED)
        return
    max_v = max(v for _, v in rows) or 1
    for i, (path, lines) in enumerate(rows):
        y = 1020 + i * 38
        draw.text((x, y), f"{i + 1:02d}", font=_font(9, "mono"), fill=ACCENT)
        _draw_text(draw, (x + 24, y - 1),
                   _ellipsize(draw, path, _font(10, "mono"), 400),
                   _font(10, "mono"), INK2, cjk_font=_font(10, "sans"))
        draw.line((x + 24, y + 15, x + 24 + int(400 * lines / max_v), y + 15),
                  fill=INK, width=3)
        _draw_text(draw, (W - M, y), _big(lines), _font(9, "mono"), MUTED,
                   anchor="ra", cjk_font=_font(9, "sans"))


def _heatmap(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _rule(draw, 1200)
    _label(draw, (M, 1216), f"CONTRIBUTION / {stats.active_days} 个活跃日")

    daily = parse_daily(stats.daily)
    start = date(stats.year, 1, 1)
    end = date(stats.year, 12, 31)
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=6 - end.weekday())
    cols = (grid_end - grid_start).days // 7 + 1

    cell, gap = 14, 4
    x0 = (W - (cols * cell + (cols - 1) * gap)) // 2
    y0 = 1266

    for month in range(1, 13):
        col = (date(stats.year, month, 1) - grid_start).days // 7
        draw.text((x0 + col * (cell + gap), 1246), f"{month:02d}",
                  font=_font(8, "mono"), fill=MUTED)

    for col in range(cols):
        for row in range(7):
            day = grid_start + timedelta(days=col * 7 + row)
            if day < start or day > end:
                continue
            count = daily.get(day, 0)
            if count == 0:
                fill = PAPER2
            elif count == 1:
                fill = (221, 214, 196)
            elif count <= 3:
                fill = (168, 159, 136)
            elif count <= 6:
                fill = (92, 85, 74)
            else:
                fill = INK
            x = x0 + col * (cell + gap)
            y = y0 + row * (cell + gap)
            draw.rectangle((x, y, x + cell, y + cell), fill=fill)


def _closing(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    quote = "「代码不会说谎，git 尤其不会。」"
    draw.text((M, 1424), quote, font=_font(24, "serifcn"), fill=INK)
    sub = f"LOCAL ONLY · 生成于 {stats.generated_at} · 代码从未离开这台电脑"
    _draw_text(draw, (M, 1468), sub, _font(10, "mono"), MUTED,
               cjk_font=_font(10, "sans"))

    _rule(draw, 1520)
    draw.text((M, 1534), "LOCAL-FIRST · NO DATA UPLOADED",
              font=_font(9, "mono"), fill=MUTED)
    draw.text((W - M, 1534), f"CODEYEAR · {stats.year}",
              font=_font(9, "mono"), fill=MUTED, anchor="ra")


def render(stats: ReportStats, out_path: str | Path) -> Path:
    img = Image.new("RGB", (W, H), PAPER)
    draw = ImageDraw.Draw(img)

    # Very light ledger grid.
    for x in range(0, W, 48):
        draw.line((x, 0, x, H), fill=(239, 236, 226), width=1)
    for y in range(0, H, 48):
        draw.line((0, y, W, y), fill=(239, 236, 226), width=1)

    _header(draw, stats)
    _persona(draw, stats)
    _stats(draw, stats)
    _monthly(draw, stats)
    _clock(draw, stats)
    _languages(draw, stats)
    _files(draw, stats)
    _heatmap(draw, stats)
    _closing(draw, stats)

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return path
