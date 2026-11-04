"""Turn raw numbers into a short, factual year-at-a-glance summary."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Persona:
    title: str
    subtitle: str
    traits: list[str]
    badges: list[str]
    badges_en: list[str]
    title_en: str
    subtitle_en: str
    summary: str
    summary_en: str


def _pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def build_persona(
    *,
    year: int,
    commits: int,
    repos: int,
    lines: int,
    insertions: int,
    deletions: int,
    active_days: int,
    longest_streak: int,
    current_streak: int,
    night_commits: int,
    early_commits: int,
    weekend_commits: int,
    peak_hour: int,
    fix_commits: int,
    feat_commits: int,
    typed_commits: int,
    lang_count: int,
    busiest_count: int,
) -> Persona:
    total = max(commits, 1)
    night_share = night_commits / total
    early_share = early_commits / total
    weekend_share = weekend_commits / total
    fix_share = fix_commits / max(typed_commits, 1)
    feat_share = feat_commits / max(typed_commits, 1)
    avg_per_active = commits / max(active_days, 1)
    delete_ratio = deletions / max(insertions + deletions, 1)

    if night_share >= 0.35:
        time_window = "22:00–05:00"
        time_share = night_share
        time_label_en = "late-night"
    elif early_share >= 0.28:
        time_window = "05:00–09:00"
        time_share = early_share
        time_label_en = "early-morning"
    elif weekend_share >= 0.35:
        time_window = "周末"
        time_share = weekend_share
        time_label_en = "weekend"
    elif 9 <= peak_hour <= 18:
        time_window = f"{peak_hour:02d}:00 前后"
        time_share = 0.0
        time_label_en = "daytime"
    else:
        time_window = f"{peak_hour:02d}:00 前后"
        time_share = 0.0
        time_label_en = "night"

    if delete_ratio >= 0.5:
        title, title_en = "删代码比写代码还多的人", "Deletes more than writes"
    elif fix_share >= 0.35:
        title, title_en = "主要在和 bug 打交道的人", "Mostly fixing bugs"
    elif feat_share >= 0.35:
        title, title_en = "一直在加功能的人", "Always adding features"
    elif night_share >= 0.5:
        title, title_en = "夜里出活的人", "Works late at night"
    elif night_share >= 0.35:
        title, title_en = "偶尔熬到深夜的人", "Sometimes up late"
    elif early_share >= 0.28:
        title, title_en = "早起写代码的人", "Early-morning coder"
    elif weekend_share >= 0.35:
        title, title_en = "周末才有点空写代码的人", "Weekend coder"
    elif lang_count >= 8:
        title, title_en = "什么语言都碰一点的人", "Touches everything"
    elif longest_streak >= 21:
        title, title_en = "很少断更的人", "Rarely breaks the streak"
    elif avg_per_active >= 5:
        title, title_en = "一天能提交很多次的人", "Commits a lot"
    else:
        title, title_en = "稳稳当当写代码的人", "Steady coder"

    if time_share:
        time_sentence = f"{_pct(time_share)} 的提交发生在 {time_window}"
        time_sentence_en = (
            f"{_pct(time_share)} of commits happened in the {time_label_en} "
            f"window"
        )
    else:
        time_sentence = f"提交高峰在 {time_window}"
        time_sentence_en = f"peak hour was {time_window}"

    style_parts = []
    style_parts_en = []
    if typed_commits:
        style_parts.append(f"修复类占 {_pct(fix_share)}")
        style_parts_en.append(f"fixes {_pct(fix_share)}")
        style_parts.append(f"功能类占 {_pct(feat_share)}")
        style_parts_en.append(f"features {_pct(feat_share)}")
    style_parts.append(f"{lang_count} 种语言")
    style_parts_en.append(f"{lang_count} languages")

    subtitle = (
        f"{year} 年，你在 {repos} 个仓库里提交了 {commits:,} 次，"
        f"改了 {lines:,} 行代码。{time_sentence}。"
    )
    subtitle_en = (
        f"In {year} you made {commits:,} commits across {repos} repositories, "
        f"changing {lines:,} lines. {time_sentence_en}."
    )

    badges = [
        f"{commits:,} 次提交",
        f"{lang_count} 种语言",
        f"{repos} 个仓库",
        f"{active_days} 个活跃日",
    ]
    badges_en = [
        f"{commits:,} commits",
        f"{lang_count} languages",
        f"{repos} repositories",
        f"{active_days} active days",
    ]

    style_text_en = ", ".join(style_parts_en)
    style_text_en = style_text_en[:1].upper() + style_text_en[1:]

    summary = subtitle + (
        "，".join(style_parts)
        + f"；最长连续 {longest_streak} 天，"
        f"每个活跃日平均 {avg_per_active:.1f} 次提交。"
    )
    summary_en = subtitle_en + (
        " " + style_text_en
        + f"; longest streak {longest_streak} days, "
        f"{avg_per_active:.1f} commits per active day."
    )

    traits = [
        f"{active_days} 个活跃日",
        f"最长连续 {longest_streak} 天",
        f"单日最高 {busiest_count} 次",
        f"{lang_count} 种语言",
    ]
    return Persona(
        title=title,
        subtitle=subtitle,
        traits=traits,
        badges=badges,
        badges_en=badges_en,
        title_en=title_en,
        subtitle_en=subtitle_en,
        summary=summary,
        summary_en=summary_en,
    )
