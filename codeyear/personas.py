"""Turn raw numbers into a small, human-readable coding persona."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Persona:
    title: str
    subtitle: str
    traits: list[str]


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
        time_adj = "深夜"
        time_desc = f"{_pct(night_share)} 的提交发生在 22:00–05:00"
    elif early_share >= 0.28:
        time_adj = "清晨"
        time_desc = f"{_pct(early_share)} 的提交发生在 05:00–09:00"
    elif weekend_share >= 0.35:
        time_adj = "周末"
        time_desc = f"{_pct(weekend_share)} 的提交发生在周末"
    elif 9 <= peak_hour <= 18:
        time_adj = "白天"
        time_desc = f"提交高峰在 {peak_hour:02d}:00"
    else:
        time_adj = "全天候"
        time_desc = f"提交高峰在 {peak_hour:02d}:00"

    # 2) How do they write code?
    delete_ratio = deletions / max(insertions + deletions, 1)

    if delete_ratio >= 0.5:
        noun = "考古学家"
        style_desc = "删掉的代码比写下的还多"
    elif fix_share >= 0.35:
        noun = "修补匠"
        style_desc = f"修复类提交占 {_pct(fix_share)}"
    elif feat_share >= 0.35:
        noun = "建筑师"
        style_desc = f"功能类提交占 {_pct(feat_share)}"
    elif lang_count >= 5:
        noun = "多语言者"
        style_desc = f"一年里碰了 {lang_count} 种语言"
    elif longest_streak >= 21:
        noun = "长跑选手"
        style_desc = f"最长连续 {longest_streak} 天没有断更"
    elif avg_per_active >= 5:
        noun = "高产机器"
        style_desc = f"每个活跃日平均 {avg_per_active:.1f} 次提交"
    else:
        noun = "稳健开发者"
        style_desc = f"每个活跃日平均 {avg_per_active:.1f} 次提交"

    title = f"{time_adj}{noun}"

    subtitle = (
        f"{year} 年，你在 {repos} 个仓库里提交了 {commits:,} 次，"
        f"改了 {lines:,} 行代码。{time_desc}；{style_desc}。"
    )

    traits = [
        f"{active_days} 个活跃日",
        f"最长连续 {longest_streak} 天",
        f"单日最高 {busiest_count} 次",
        f"{lang_count} 种语言",
    ]
    return Persona(title=title, subtitle=subtitle, traits=traits)
