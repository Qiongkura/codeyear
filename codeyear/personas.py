"""Turn raw numbers into a small, human-readable coding persona."""

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

    # 1) When do they write code?
    if night_share >= 0.35:
        time_adj, time_en = "深夜", "Late-night"
        time_desc = f"{_pct(night_share)} 的提交发生在 22:00–05:00"
        time_desc_en = f"{_pct(night_share)} of commits happened between 22:00–05:00"
    elif early_share >= 0.28:
        time_adj, time_en = "清晨", "Early-morning"
        time_desc = f"{_pct(early_share)} 的提交发生在 05:00–09:00"
        time_desc_en = f"{_pct(early_share)} of commits happened between 05:00–09:00"
    elif weekend_share >= 0.35:
        time_adj, time_en = "周末", "Weekend"
        time_desc = f"{_pct(weekend_share)} 的提交发生在周末"
        time_desc_en = f"{_pct(weekend_share)} of commits happened on weekends"
    elif 9 <= peak_hour <= 18:
        time_adj, time_en = "白天", "Daytime"
        time_desc = f"提交高峰在 {peak_hour:02d}:00"
        time_desc_en = f"peak hour was {peak_hour:02d}:00"
    else:
        time_adj, time_en = "全天候", "All-hours"
        time_desc = f"提交高峰在 {peak_hour:02d}:00"
        time_desc_en = f"peak hour was {peak_hour:02d}:00"

    # 2) How do they write code?
    delete_ratio = deletions / max(insertions + deletions, 1)

    if delete_ratio >= 0.5:
        noun, noun_en = "考古学家", "archaeologist"
        style_desc = "删掉的代码比写下的还多"
        style_desc_en = "you deleted more code than you wrote"
    elif fix_share >= 0.35:
        noun, noun_en = "修补匠", "tinkerer"
        style_desc = f"修复类提交占 {_pct(fix_share)}"
        style_desc_en = f"{_pct(fix_share)} of typed commits were fixes"
    elif feat_share >= 0.35:
        noun, noun_en = "建筑师", "builder"
        style_desc = f"功能类提交占 {_pct(feat_share)}"
        style_desc_en = f"{_pct(feat_share)} of typed commits were features"
    elif lang_count >= 5:
        noun, noun_en = "多语言者", "polyglot"
        style_desc = f"一年里碰了 {lang_count} 种语言"
        style_desc_en = f"you touched {lang_count} languages"
    elif longest_streak >= 21:
        noun, noun_en = "长跑选手", "long-distance runner"
        style_desc = f"最长连续 {longest_streak} 天没有断更"
        style_desc_en = f"your longest streak was {longest_streak} days"
    elif avg_per_active >= 5:
        noun, noun_en = "高产机器", "high-output machine"
        style_desc = f"每个活跃日平均 {avg_per_active:.1f} 次提交"
        style_desc_en = f"you averaged {avg_per_active:.1f} commits per active day"
    else:
        noun, noun_en = "稳健开发者", "steady developer"
        style_desc = f"每个活跃日平均 {avg_per_active:.1f} 次提交"
        style_desc_en = f"you averaged {avg_per_active:.1f} commits per active day"

    title = f"{time_adj}{noun}"
    title_en = f"{time_en} {noun_en}"

    subtitle = (
        f"{year} 年，你在 {repos} 个仓库里提交了 {commits:,} 次，"
        f"改了 {lines:,} 行代码。{time_desc}；{style_desc}。"
    )
    subtitle_en = (
        f"In {year} you made {commits:,} commits across {repos} repositories, "
        f"changing {lines:,} lines. {time_desc_en}; {style_desc_en}."
    )

    badges: list[str] = []
    badges_en: list[str] = []

    def add(label: str, label_en: str) -> None:
        if label not in badges:
            badges.append(label)
            badges_en.append(label_en)

    if night_share >= 0.5:
        add("夜猫子", "Night owl")
    elif night_share >= 0.35:
        add("深夜型", "Late-night")
    if early_share >= 0.4:
        add("早起鸟", "Early bird")
    if weekend_share >= 0.4:
        add("周末战士", "Weekend warrior")
    if delete_ratio >= 0.6:
        add("删繁就简", "Simplifier")
    if fix_share >= 0.5:
        add("修 bug 主力", "Bug fixer")
    if feat_share >= 0.5:
        add("功能输出", "Feature shipper")
    if lang_count >= 8:
        add("语言收藏家", "Language collector")
    if longest_streak >= 50:
        add("连续记录者", "Streak keeper")
    if avg_per_active >= 8:
        add("高频提交", "High frequency")
    if commits >= 1000:
        add("千次提交", "1k commits")
    if active_days >= 100:
        add("长期主义", "Consistent")
    if busiest_count >= 20:
        add("爆发日", "Burst day")
    if repos >= 10:
        add("多线并行", "Multi-project")
    elif repos >= 5:
        add("多项目", "Multi-project")
    if current_streak >= 7:
        add("正在连续", "On a streak")
    if not badges:
        add(f"{time_adj}型", time_en)

    badges = badges[:6]
    badges_en = badges_en[:6]

    summary = subtitle + (
        f"最长连续 {longest_streak} 天，"
        f"每个活跃日平均 {avg_per_active:.1f} 次提交。"
    )
    summary_en = subtitle_en + (
        f" Longest streak {longest_streak} days, "
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
