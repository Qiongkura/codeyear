"""Render a 1200x1600 shareable poster in the same paper/ink style as the HTML report."""

from __future__ import annotations

import os
import re
from datetime import date, timedelta
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from .stats import ReportStats, fmt_int, fmt_signed_pair, language_breakdown, parse_daily

W, H = 1200, 1600
M = 64
SCALE = 2

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

# Rendering is synchronous, so a module-level language keeps the drawing
# helpers readable without threading ``lang`` through every call.
_LANG = "zh"
_MONTHS = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
]


def _t(zh: str, en: str) -> str:
    return en if _LANG == "en" else zh



def _font(size: int, kind: str = "sans") -> ImageFont.FreeTypeFont:
    key = (size, kind)
    if key in _FONT_CACHE:
        return _FONT_CACHE[key]
    for path in _FONT_PATHS.get(kind, []):
        if os.path.exists(path):
            try:
                font = ImageFont.truetype(path, size * SCALE, index=0)
                _FONT_CACHE[key] = font
                return font
            except OSError:
                continue
    font = ImageFont.load_default()
    _FONT_CACHE[key] = font
    return font


class _ScaledDraw:
    """Draw in 1200x1600 design coordinates while rendering at 2x."""

    def __init__(self, draw: ImageDraw.ImageDraw, scale: int):
        self._d = draw
        self.s = scale

    def text(self, xy, text, *args, **kwargs):
        self._d.text((xy[0] * self.s, xy[1] * self.s), text, *args, **kwargs)

    def line(self, xy, *args, **kwargs):
        if len(xy) == 4 and all(isinstance(v, (int, float)) for v in xy):
            coords = tuple(v * self.s for v in xy)
        else:
            coords = [(x * self.s, y * self.s) for x, y in xy]
        kwargs["width"] = max(1, int(kwargs.get("width", 1) * self.s))
        self._d.line(coords, *args, **kwargs)

    def rectangle(self, xy, *args, **kwargs):
        if len(xy) == 4 and all(isinstance(v, (int, float)) for v in xy):
            coords = tuple(v * self.s for v in xy)
        else:
            coords = [(x * self.s, y * self.s) for x, y in xy]
        kwargs["width"] = max(1, int(kwargs.get("width", 1) * self.s))
        self._d.rectangle(coords, *args, **kwargs)

    def textlength(self, text, *args, **kwargs):
        return self._d.textlength(text, *args, **kwargs) / self.s


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
    if _LANG == "en":
        if n >= 1_000_000:
            return f"{n / 1_000_000:.1f}m"
        if n >= 10_000:
            return f"{n / 1000:.0f}k"
        return f"{n:,}"
    if n >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if n >= 10_000:
        return f"{n / 10_000:.1f}万"
    return f"{n:,}"


def _signed(insertions: int, deletions: int) -> str:
    if _LANG == "en":
        if max(insertions, deletions) >= 10_000:
            return f"+{insertions / 1000:.0f}k / -{deletions / 1000:.0f}k"
        return f"+{insertions:,} / -{deletions:,}"
    return fmt_signed_pair(insertions, deletions)


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
    """Draw mixed mono + CJK text on one shared baseline (no tofu, no bobbing)."""
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

    ascent, descent = font.getmetrics()
    ascent /= SCALE
    descent /= SCALE
    vertical = anchor[1:2]
    if vertical == "m":
        baseline = y + (ascent - descent) / 2
    elif vertical == "s":
        baseline = y
    elif vertical == "b":
        baseline = y - descent
    else:
        baseline = y + ascent

    for ch, width in zip(text, widths):
        glyph_font = cjk_font if _is_cjk(ch) else font
        draw.text((x, baseline), ch, font=glyph_font, fill=fill, anchor="ls")
        x += width


def _rule(draw: ImageDraw.ImageDraw, y: int, color=LINE) -> None:
    draw.line((M, y, W - M, y), fill=color, width=1)


def _label(draw: ImageDraw.ImageDraw, xy: tuple[int, int], text: str) -> None:
    _draw_text(draw, xy, text.upper(), _font(10, "mono"), MUTED,
               cjk_font=_font(10, "sans"))


def _scope_line(stats: ReportStats) -> str:
    parts = []
    if stats.earliest_dt:
        parts.append(_t(
            f"最早提交 {stats.earliest_dt:%Y.%m}",
            f"first commit {stats.earliest_dt:%Y.%m}",
        ))
    if stats.new_repos:
        parts.append(_t(
            f"今年新开 {stats.new_repos} 个仓库",
            f"{stats.new_repos} new repositories",
        ))
    if stats.tags_in_year:
        parts.append(_t(
            f"{stats.tags_in_year} 个版本 tag",
            f"{stats.tags_in_year} release tags",
        ))
    return "   ·   ".join(parts)


def _header(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _spaced(draw, (M, 50), "CODEYEAR", _font(20, "mono"), ACCENT, 6)
    draw.text((W - M, 56), _t("代码手账", "YEARBOOK"),
              font=_font(15, "sans"), fill=MUTED, anchor="ra")

    draw.text((M - 5, 76), str(stats.year), font=_font(150, "serif"), fill=INK, anchor="lt")

    span = "—"
    if stats.first_dt and stats.last_dt:
        span = f"{stats.first_dt:%Y.%m.%d} — {stats.last_dt:%Y.%m.%d}"
    meta = f"{stats.root}   ·   {stats.repo_count} " + _t("个仓库", "repositories") + f"   ·   {span}"
    _draw_text(draw, (M, 262),
               _ellipsize(draw, meta, _font(12, "mono"), W - 2 * M),
               _font(12, "mono"), MUTED, cjk_font=_font(12, "sans"))
    scope = _scope_line(stats)
    if scope:
        _draw_text(draw, (M, 282),
                   _ellipsize(draw, scope, _font(10, "mono"), W - 2 * M),
                   _font(10, "mono"), MUTED, cjk_font=_font(10, "sans"))
    _rule(draw, 300)


def _persona(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _label(draw, (M, 322), "YOUR CODING YEAR")
    title = _ellipsize(
        draw, stats.persona.title_en if _LANG == "en" else stats.persona.title,
        _font(42, "serif" if _LANG == "en" else "serifcn"), W - 2 * M,
    )
    draw.text((M - 2, 338), title,
              font=_font(42, "serif" if _LANG == "en" else "serifcn"), fill=INK)

    body = _font(15, "sans")
    text = stats.persona.subtitle_en if _LANG == "en" else stats.persona.subtitle
    lines = _wrap(draw, text, body, W - 2 * M, 2)
    for i, line in enumerate(lines):
        draw.text((M, 402 + i * 24), line, font=body, fill=INK2)


def _stats(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _rule(draw, 476)
    if _LANG == "en":
        labels = ["COMMITS", "LINES", "ACTIVE", "STREAK", "TOTAL"]
        subs = [
            f"{stats.repo_count} repos with commits",
            _signed(stats.insertions, stats.deletions),
            f"{stats.active_days / (366 if _is_leap(stats.year) else 365):.0%} of the year",
            f"{stats.current_streak}-day current streak",
            "all-time",
        ]
    else:
        labels = ["COMMITS / 提交", "LINES / 行变更", "ACTIVE / 活跃天",
                  "STREAK / 最长连续", "TOTAL / 累计"]
        subs = [
            f"{stats.repo_count} 个有提交的仓库",
            _signed(stats.insertions, stats.deletions),
            f"占全年 {stats.active_days / (366 if _is_leap(stats.year) else 365):.0%}",
            f"当前 {stats.current_streak} 天",
            "仓库全历史",
        ]
    values = [
        f"{stats.commit_count:,}",
        _big(stats.lines_changed),
        str(stats.active_days),
        str(stats.longest_streak),
        f"{stats.total_commits:,}",
    ]
    col_w = (W - 2 * M) / 5
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
    _draw_text(draw, (W - M, 612), _t(
        f"峰值 {peak:02d} 月 · {max_v} 次",
        f"Peak {_MONTHS[peak - 1]} · {max_v}",
    ), _font(11, "mono"), ACCENT, anchor="ra", cjk_font=_font(11, "sans"))

    baseline = 758
    max_h = 104
    gap = 10
    bar_w = int((W - 2 * M - gap * 11) / 12)
    for i, value in enumerate(stats.monthly):
        x = M + i * (bar_w + gap)
        h = max(int(value / max_v * max_h), 2)
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
    _label(draw, (M, 992), _t(
        f"LANGUAGES / 语言 · {stats.language_count} 种",
        f"LANGUAGES · {stats.language_count}",
    ))
    rows, total = language_breakdown(stats.languages, limit=4, min_share=0.01)
    if not rows:
        draw.text((M, 1024), _t("没有可统计的代码文件", "No code files to count"),
                  font=_font(12, "sans"), fill=MUTED)
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
        label = "Other" if _LANG == "en" and name == "其他" else name
        _draw_text(draw, (M + 18, y + 6), _ellipsize(draw, label, _font(11, "sans"), 300),
                   _font(11, "sans"), INK2, anchor="lm", cjk_font=_font(11, "sans"))
        draw.text((M + 500, y + 6), f"{value / total * 100:.0f}%", font=_font(10, "mono"),
                  fill=MUTED, anchor="rm")


def _files(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    x = 620
    _label(draw, (x, 992), "MOST EDITED FILES")
    rows = stats.top_files[:4]
    if not rows:
        draw.text((x, 1024), _t("暂无数据", "No data"),
                  font=_font(12, "sans"), fill=MUTED)
        return
    max_v = max(v for _, v in rows) or 1
    for i, (path, lines) in enumerate(rows):
        y = 1020 + i * 38
        _draw_text(draw, (x, y + 5), f"{i + 1:02d}", _font(9, "mono"), ACCENT,
                   anchor="lm")
        _draw_text(draw, (x + 24, y + 5),
                   _ellipsize(draw, path, _font(10, "mono"), 400),
                   _font(10, "mono"), INK2, anchor="lm", cjk_font=_font(10, "sans"))
        draw.line((x + 24, y + 15, x + 24 + int(400 * lines / max_v), y + 15),
                  fill=INK, width=3)
        _draw_text(draw, (W - M, y + 5), _big(lines), _font(9, "mono"), MUTED,
                   anchor="rm", cjk_font=_font(9, "sans"))


def _heatmap(draw: ImageDraw.ImageDraw, stats: ReportStats) -> None:
    _rule(draw, 1200)
    _label(draw, (M, 1216), _t(
        f"CONTRIBUTION / {stats.active_days} 个活跃日",
        f"CONTRIBUTION / {stats.active_days} active days",
    ))

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
    quote = _t("「代码不会说谎，git 尤其不会。」",
               "“Code doesn’t lie. Git especially doesn’t.”")
    draw.text((M, 1424), quote,
              font=_font(24, "serif" if _LANG == "en" else "serifcn"), fill=INK)
    sub = _t(
        f"LOCAL ONLY · 生成于 {stats.generated_at} · 代码从未离开这台电脑",
        f"LOCAL ONLY · generated {stats.generated_at} · code never left this machine",
    )
    footer_label = "LOCAL-FIRST · NO DATA UPLOADED"
    if stats.public_source:
        sub = _t(
            f"PUBLIC DATA · 生成于 {stats.generated_at} · 仅使用公开 GitHub 数据",
            f"PUBLIC DATA · generated {stats.generated_at} · public GitHub data only",
        )
        footer_label = "PUBLIC DATA · GITHUB"
    _draw_text(draw, (M, 1468), sub, _font(10, "mono"), MUTED,
               cjk_font=_font(10, "sans"))

    _rule(draw, 1520)
    draw.text((M, 1534), footer_label,
              font=_font(9, "mono"), fill=MUTED)
    draw.text((W - M, 1534), f"CODEYEAR · {stats.year}",
              font=_font(9, "mono"), fill=MUTED, anchor="ra")


def render(stats: ReportStats, out_path: str | Path, *, lang: str = "zh") -> Path:
    global _LANG
    _LANG = "en" if lang == "en" else "zh"
    img = Image.new("RGB", (W * SCALE, H * SCALE), PAPER)
    draw = _ScaledDraw(ImageDraw.Draw(img), SCALE)

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


# --------------------------------------------------------------------------
# Full-length "long image" version
# --------------------------------------------------------------------------

LONG_W = 1200
LONG_H = 4000


def _long_title(draw: ImageDraw.ImageDraw, y: int, no: str, cn: str, en: str) -> int:
    _rule(draw, y - 18)
    draw.text((M, y), f"{no} / {en}", font=_font(9, "mono"), fill=ACCENT)
    heading = en if _LANG == "en" else cn
    heading_font = "serif" if _LANG == "en" else "serifcn"
    _draw_text(draw, (M, y + 16), heading, _font(26, heading_font), INK,
               cjk_font=_font(26, "serifcn"))
    return y + 54


def _long_header(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    _spaced(draw, (M, y), "CODEYEAR", _font(18, "mono"), ACCENT, 5)
    _draw_text(draw, (W - M, y + 3), _t(f"代码手账 · {stats.year}", f"Yearbook · {stats.year}"),
               _font(13, "sans"), MUTED, anchor="ra", cjk_font=_font(13, "sans"))

    draw.text((M - 4, y + 20), str(stats.year), font=_font(110, "serif"), fill=INK)
    span = "—"
    if stats.first_dt and stats.last_dt:
        span = f"{stats.first_dt:%Y.%m.%d} — {stats.last_dt:%Y.%m.%d}"
    meta = f"{stats.root}   ·   {stats.repo_count} " + _t("个仓库", "repositories") + f"   ·   {span}"
    _draw_text(draw, (M, y + 158), _ellipsize(draw, meta, _font(11, "mono"), W - 2 * M),
               _font(11, "mono"), MUTED, cjk_font=_font(11, "sans"))
    scope = _scope_line(stats)
    if scope:
        _draw_text(draw, (M, y + 176), _ellipsize(draw, scope, _font(10, "mono"), W - 2 * M),
                   _font(10, "mono"), MUTED, cjk_font=_font(10, "sans"))

    title = stats.persona.title_en if _LANG == "en" else stats.persona.title
    title_font = "serif" if _LANG == "en" else "serifcn"
    _draw_text(draw, (M, y + 196), title, _font(34, title_font), INK,
               cjk_font=_font(34, "serifcn"))
    subtitle = stats.persona.subtitle_en if _LANG == "en" else stats.persona.subtitle
    lines = _wrap(draw, subtitle, _font(14, "sans"), W - 2 * M, 2)
    for i, line in enumerate(lines):
        draw.text((M, y + 242 + i * 22), line, font=_font(14, "sans"), fill=INK2)

    _rule(draw, y + 300)
    if _LANG == "en":
        labels = ["COMMITS", "LINES", "ACTIVE", "STREAK", "TOTAL"]
        subs = [f"{stats.repo_count} repos with commits",
                _signed(stats.insertions, stats.deletions),
                f"{stats.active_days / (366 if _is_leap(stats.year) else 365):.0%} of the year",
                f"{stats.current_streak}-day current streak",
                "all-time"]
    else:
        labels = ["COMMITS / 提交", "LINES / 行变更", "ACTIVE / 活跃天",
                  "STREAK / 最长连续", "TOTAL / 累计"]
        subs = [f"{stats.repo_count} 个有提交的仓库",
                _signed(stats.insertions, stats.deletions),
                f"占全年 {stats.active_days / (366 if _is_leap(stats.year) else 365):.0%}",
                f"当前 {stats.current_streak} 天",
                "仓库全历史"]
    values = [f"{stats.commit_count:,}", _big(stats.lines_changed),
              str(stats.active_days), str(stats.longest_streak),
              f"{stats.total_commits:,}"]
    col_w = (W - 2 * M) / 5
    for i, (label, value, sub) in enumerate(zip(labels, values, subs)):
        x = int(M + i * col_w)
        _draw_text(draw, (x, y + 318), label, _font(9, "mono"), MUTED,
                   cjk_font=_font(9, "sans"))
        _draw_text(draw, (x, y + 332), value, _font(30, "mono"), INK,
                   cjk_font=_font(25, "sans"))
        _draw_text(draw, (x, y + 370), _ellipsize(draw, sub, _font(9, "mono"), col_w - 18),
                   _font(9, "mono"), MUTED, cjk_font=_font(9, "sans"))
    _rule(draw, y + 392)
    return y + 416


def _long_records(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "01", "年度之最", "YEAR IN REVIEW")
    records: list[tuple[str, str, str]] = []
    if stats.busiest_day:
        day, count = stats.busiest_day
        records.append((_t("最忙的一天", "Busiest day"),
                        _t(f"{count} 次提交", f"{count} commits"),
                        day.replace("-", ".")))
    if stats.busiest_week:
        week, count = stats.busiest_week
        records.append((_t("最忙的一周", "Busiest week"),
                        _t(f"{count} 次提交", f"{count} commits"),
                        _t(f"{week} · 起于 {stats.busiest_week_start or '—'}",
                           f"{week} · from {stats.busiest_week_start or '—'}")))
    records.append((_t("最长连续", "Longest streak"),
                    _t(f"{stats.longest_streak} 天", f"{stats.longest_streak} days"),
                    _t(f"当前连续 {stats.current_streak} 天",
                       f"{stats.current_streak}-day current streak")))
    if stats.longest_gap:
        days, start, end = stats.longest_gap
        records.append((_t("最长空窗", "Longest gap"),
                        _t(f"{days} 天", f"{days} days"),
                        f"{start} – {end}"))
    if stats.largest_commit:
        lc = stats.largest_commit
        records.append((_t("最大单次提交", "Largest commit"),
                        _t(f"{fmt_int(lc['lines'])} 行", f"{fmt_int(lc['lines'])} lines"),
                        f"{lc['repo']} · {lc['date']}"))
    records.append((_t("最长的 commit", "Longest message"),
                    _t(f"{len(stats.longest_subject)} 字符",
                       f"{len(stats.longest_subject)} chars"),
                    stats.longest_subject[:46]))

    card_w, card_h = 344, 100
    for i, (label, value, sub) in enumerate(records[:6]):
        col, row = i % 3, i // 3
        bx = M + col * (card_w + 20)
        by = y0 + row * (card_h + 12)
        draw.rectangle((bx, by, bx + card_w, by + card_h), outline=LINE)
        _draw_text(draw, (bx + 14, by + 12), label, _font(9, "mono"), MUTED,
                   cjk_font=_font(9, "sans"))
        _draw_text(draw, (bx + 14, by + 30), value, _font(21, "serifcn"), INK,
                   cjk_font=_font(21, "serifcn"))
        _draw_text(draw, (bx + 14, by + 68), _ellipsize(draw, sub, _font(9, "mono"), card_w - 28),
                   _font(9, "mono"), MUTED, cjk_font=_font(9, "sans"))
    return y0 + 2 * card_h + 12 + 8


def _long_monthly(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "02", "月度节奏", "MONTHLY RHYTHM")
    max_v = max(stats.monthly) or 1
    peak = stats.monthly.index(max_v) + 1
    _draw_text(draw, (W - M, y0), _t(
        f"峰值 {peak:02d} 月 · {max_v} 次",
        f"Peak {_MONTHS[peak - 1]} · {max_v}",
    ), _font(10, "mono"), ACCENT, anchor="ra", cjk_font=_font(10, "sans"))
    baseline = y0 + 128
    max_h = 92
    gap = 8
    bar_w = int((W - 2 * M - gap * 11) / 12)
    for i, value in enumerate(stats.monthly):
        x = M + i * (bar_w + gap)
        h = max(int(value / max_v * max_h), 2)
        draw.rectangle((x, baseline - h, x + bar_w, baseline),
                       fill=ACCENT if value == max_v and value > 0 else INK)
    draw.line((M, baseline, W - M, baseline), fill=INK, width=1)
    for i in range(12):
        cx = M + i * (bar_w + gap) + bar_w / 2
        draw.text((cx, baseline + 7), f"{i + 1:02d}", font=_font(9, "mono"),
                  fill=MUTED, anchor="ma")
    return baseline + 30


def _long_clock(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "03", "7×24 提交时钟", "7 × 24 CLOCK")
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
    cell_h = 12
    x0 = M + label_w
    for h in range(24):
        if h % 3 == 0:
            draw.text((x0 + h * (cell_w + gap) + cell_w / 2, y0 - 2),
                      f"{h:02d}", font=_font(8, "mono"), fill=MUTED, anchor="ma")
    for wd, row in enumerate(stats.hour_weekday):
        yy = y0 + 12 + wd * (cell_h + 3)
        draw.text((M, yy + 1), days[wd], font=_font(8, "mono"), fill=MUTED)
        for h, value in enumerate(row):
            x = x0 + h * (cell_w + gap)
            draw.rectangle((x, yy, x + cell_w, yy + cell_h), fill=color(value))
    _draw_text(draw, (W - M, y0 + 8), _t(
        f"周末占 {stats.weekend_share:.0%} · 深夜占 {stats.night_share:.0%}",
        f"weekend {stats.weekend_share:.0%} · late-night {stats.night_share:.0%}",
    ), _font(9, "mono"), MUTED, anchor="ra", cjk_font=_font(9, "sans"))
    return y0 + 12 + 7 * (cell_h + 3) + 14


def _long_bars(draw: ImageDraw.ImageDraw, x: int, y: int, w: int,
               rows: list[tuple[str, int]], max_v: int, color=INK) -> int:
    for i, (label, value) in enumerate(rows):
        yy = y + i * 24
        _draw_text(draw, (x, yy), _ellipsize(draw, label, _font(9, "mono"), 130),
                   _font(9, "mono"), INK2, cjk_font=_font(9, "sans"))
        bx = x + 138
        bw = w - 138 - 54
        draw.rectangle((bx, yy - 7, bx + bw, yy - 1), outline=LINE)
        if value > 0:
            draw.rectangle((bx, yy - 7, bx + max(int(bw * value / max_v), 2), yy - 1),
                           fill=color)
        draw.text((x + w, yy), f"{value:,}", font=_font(8, "mono"), fill=MUTED,
                  anchor="rm")
    return y + len(rows) * 24


def _long_lang_files(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "04", "语言与文件", "LANGUAGES & FILES")
    draw.text((M, y0), "LANGUAGES", font=_font(9, "mono"), fill=MUTED)
    rows, total = language_breakdown(stats.languages, limit=4, min_share=0.01)
    palette = [INK, ACCENT, (143, 134, 114), (179, 171, 151), (200, 193, 172)]
    bar_w = 500
    x = M
    for i, (_name, value) in enumerate(rows):
        w = int(bar_w * value / total)
        draw.rectangle((x, y0 + 20, x + w, y0 + 34), fill=palette[i % len(palette)])
        x += w
    if x < M + bar_w:
        draw.rectangle((x, y0 + 20, M + bar_w, y0 + 34),
                       fill=palette[len(rows) % len(palette)])
    for i, (name, value) in enumerate(rows):
        yy = y0 + 46 + i * 21
        draw.rectangle((M, yy + 2, M + 8, yy + 10), fill=palette[i % len(palette)])
        label = "Other" if _LANG == "en" and name == "其他" else name
        _draw_text(draw, (M + 16, yy + 6), label, _font(10, "sans"), INK2,
                   anchor="lm", cjk_font=_font(10, "sans"))
        draw.text((M + 500, yy + 6), f"{value / total * 100:.0f}%",
                  font=_font(9, "mono"), fill=MUTED, anchor="rm")

    xr = 620
    draw.text((xr, y0), "MOST EDITED FILES", font=_font(9, "mono"), fill=MUTED)
    files = stats.top_files[:5]
    max_v = max((v for _, v in files), default=1)
    for i, (path, lines) in enumerate(files):
        yy = y0 + 22 + i * 28
        _draw_text(draw, (xr, yy), f"{i + 1:02d}", _font(8, "mono"), ACCENT)
        _draw_text(draw, (xr + 22, yy),
                   _ellipsize(draw, path, _font(9, "mono"), 420),
                   _font(9, "mono"), INK2, cjk_font=_font(9, "sans"))
        draw.line((xr + 22, yy + 14, xr + 22 + int(420 * lines / max_v), yy + 14),
                  fill=INK, width=3)
        _draw_text(draw, (W - M, yy), _big(lines), _font(8, "mono"), MUTED,
                   anchor="ra", cjk_font=_font(8, "sans"))
    return y0 + 172


def _long_sizes_types(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "05", "规模与类型", "SIZE & TYPES")
    draw.text((M, y0), "COMMIT SIZE", font=_font(9, "mono"), fill=MUTED)
    max_s = max((v for _, v in stats.size_buckets), default=1)
    _long_bars(draw, M, y0 + 24, 500,
               [(_t(f"{label} 行", f"{label} lines"), v)
                for label, v in stats.size_buckets], max_s)

    xr = 620
    draw.text((xr, y0), "COMMIT TYPES", font=_font(9, "mono"), fill=MUTED)
    types = stats.commit_types[:6]
    max_t = max((v for _, v in types), default=1)
    _long_bars(draw, xr, y0 + 24, 516, types, max_t)
    _draw_text(draw, (W - M, y0 + 8),
               _t(f"约定式 {stats.conventional_share:.0%}",
                  f"Conventional {stats.conventional_share:.0%}"),
               _font(9, "mono"), ACCENT, anchor="ra", cjk_font=_font(9, "sans"))
    return y0 + 176


def _long_msgs_sessions(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "06", "消息与节奏", "MESSAGES & SESSIONS")
    draw.text((M, y0), "MESSAGE LENGTH", font=_font(9, "mono"), fill=MUTED)
    max_m = max((v for _, v in stats.message_buckets), default=1)
    _long_bars(draw, M, y0 + 24, 500,
               [(_t(f"{label} 字符", f"{label} chars"), v)
                for label, v in stats.message_buckets], max_m)

    xr = 620
    draw.text((xr, y0), "CODING SESSIONS", font=_font(9, "mono"), fill=MUTED)
    s = stats.sessions
    hours, mins = divmod(int(s.get("longest_minutes", 0)), 60)
    items = [
        (_t("会话次数", "Sessions"), f"{s.get('count', 0)}"),
        (_t("最长会话", "Longest session"), f"{hours}h {mins:02d}m"),
        (_t("最长会话提交", "Longest session commits"), f"{s.get('longest_commits', 0)}"),
        (_t("平均会话", "Average session"), f"{s.get('avg_minutes', 0)}m"),
    ]
    for i, (label, value) in enumerate(items):
        col, row = i % 2, i // 2
        bx = xr + col * 258
        by = y0 + 26 + row * 46
        _draw_text(draw, (bx, by), label, _font(9, "mono"), MUTED,
                   cjk_font=_font(9, "sans"))
        _draw_text(draw, (bx, by + 14), value, _font(20, "mono"), INK,
                   cjk_font=_font(16, "sans"))
    _draw_text(draw, (xr, y0 + 140), _t(
        f"间隔 ≤ 2 小时算同一会话 · 平均每条 {stats.avg_subject_len} 字符",
        f"Sessions split at 2h gaps · avg {stats.avg_subject_len} chars per subject",
    ), _font(9, "mono"), MUTED, cjk_font=_font(9, "sans"))
    return y0 + 176


def _long_churn_dormant(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "07", "增删与墓园", "CHURN & DORMANT")
    draw.text((M, y0), "ADD / DELETE", font=_font(9, "mono"), fill=MUTED)
    total = max(stats.insertions + stats.deletions, 1)
    draw.rectangle((M, y0 + 24, M + 500, y0 + 38), outline=INK)
    draw.rectangle((M, y0 + 24, M + int(500 * stats.insertions / total), y0 + 38),
                   fill=INK)
    draw.rectangle((M + int(500 * stats.insertions / total), y0 + 24,
                    M + 500, y0 + 38), fill=ACCENT)
    _draw_text(draw, (M, y0 + 48),
               _t(f"新增 {_signed(stats.insertions, stats.deletions)}",
                  f"Added {_signed(stats.insertions, stats.deletions)}"),
               _font(9, "mono"), MUTED, cjk_font=_font(9, "sans"))
    top_del = sorted(stats.repo_details, key=lambda d: -d["deleted"])[:3]
    max_del = max((d["deleted"] for d in top_del), default=1)
    _long_bars(draw, M, y0 + 80, 500,
               [(d["name"], d["deleted"]) for d in top_del], max_del, color=ACCENT)

    xr = 620
    draw.text((xr, y0), "DORMANT REPOS", font=_font(9, "mono"), fill=MUTED)
    if not stats.dormant:
        draw.text((xr, y0 + 26),
                  _t("没有休眠超过 30 天的仓库",
                     "No repositories dormant for more than 30 days"),
                  font=_font(11, "sans"), fill=MUTED)
    for i, repo in enumerate(stats.dormant[:5]):
        yy = y0 + 24 + i * 26
        _draw_text(draw, (xr, yy + 6), repo["name"], _font(9, "mono"), INK2,
                   anchor="lm", cjk_font=_font(9, "sans"))
        draw.text((W - M, yy + 6), _t(f"{repo['days']} 天", f"{repo['days']} days"),
                  font=_font(9, "mono"), fill=ACCENT, anchor="rm")
    return y0 + 186


def _long_heatmap(draw: ImageDraw.ImageDraw, stats: ReportStats, y: int) -> int:
    y0 = _long_title(draw, y, "08", "全年热力图", "CONTRIBUTION")
    daily = parse_daily(stats.daily)
    start = date(stats.year, 1, 1)
    end = date(stats.year, 12, 31)
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=6 - end.weekday())
    cols = (grid_end - grid_start).days // 7 + 1
    cell, gap = 14, 4
    x0 = (W - (cols * cell + (cols - 1) * gap)) // 2
    y0 += 18
    for month in range(1, 13):
        col = (date(stats.year, month, 1) - grid_start).days // 7
        draw.text((x0 + col * (cell + gap), y0 - 16), f"{month:02d}",
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
            yy = y0 + row * (cell + gap)
            draw.rectangle((x, yy, x + cell, yy + cell), fill=fill)
    _draw_text(draw, (W - M, y0 - 18), _t(
        f"{stats.active_days} 个活跃日",
        f"{stats.active_days} active days",
    ), _font(9, "mono"), MUTED, anchor="ra", cjk_font=_font(9, "sans"))
    return y0 + 7 * (cell + gap) + 18


def render_long(stats: ReportStats, out_path: str | Path, *, lang: str = "zh") -> Path:
    global _LANG
    _LANG = "en" if lang == "en" else "zh"
    img = Image.new("RGB", (LONG_W * SCALE, LONG_H * SCALE), PAPER)
    draw = _ScaledDraw(ImageDraw.Draw(img), SCALE)
    for x in range(0, LONG_W, 48):
        draw.line((x, 0, x, LONG_H), fill=(239, 236, 226), width=1)
    for yy in range(0, LONG_H, 48):
        draw.line((0, yy, LONG_W, yy), fill=(239, 236, 226), width=1)

    y = _long_header(draw, stats, 56)
    y = _long_records(draw, stats, y + 20)
    y = _long_monthly(draw, stats, y + 30)
    y = _long_clock(draw, stats, y + 30)
    y = _long_lang_files(draw, stats, y + 30)
    y = _long_sizes_types(draw, stats, y + 30)
    y = _long_msgs_sessions(draw, stats, y + 30)
    y = _long_churn_dormant(draw, stats, y + 30)
    y = _long_heatmap(draw, stats, y + 30)

    draw.text((M, y + 24), _t("「代码不会说谎，git 尤其不会。」",
                              "“Code doesn’t lie. Git especially doesn’t.”"),
              font=_font(22, "serif" if _LANG == "en" else "serifcn"), fill=INK)
    sub = _t(
        f"LOCAL ONLY · 生成于 {stats.generated_at} · 代码从未离开这台电脑",
        f"LOCAL ONLY · generated {stats.generated_at} · code never left this machine",
    )
    footer_label = "LOCAL-FIRST · NO DATA UPLOADED"
    if stats.public_source:
        sub = _t(
            f"PUBLIC DATA · 生成于 {stats.generated_at} · 仅使用公开 GitHub 数据",
            f"PUBLIC DATA · generated {stats.generated_at} · public GitHub data only",
        )
        footer_label = "PUBLIC DATA · GITHUB"
    _draw_text(draw, (M, y + 62), sub,
               _font(9, "mono"), MUTED, cjk_font=_font(9, "sans"))
    _rule(draw, y + 100)
    draw.text((M, y + 112), footer_label,
              font=_font(9, "mono"), fill=MUTED)
    draw.text((W - M, y + 112), f"CODEYEAR · {stats.year}",
              font=_font(9, "mono"), fill=MUTED, anchor="ra")

    final_h = min(y + 150, LONG_H)
    img = img.crop((0, 0, LONG_W * SCALE, final_h * SCALE))
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return path
