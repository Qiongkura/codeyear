"""Aggregate per-repo commit data into one report."""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta

from .keywords import extract_keywords
from .languages import is_code_language
from .personas import Persona, build_persona
from .scanner import Commit, RepoResult

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

KNOWN_TYPES: set[str] = {
    "feat", "fix", "docs", "style", "refactor", "perf", "test", "tests",
    "build", "ci", "chore", "revert", "release", "hotfix", "wip", "merge",
    "remove", "add", "update", "improve", "init",
}

ZH_TYPES: dict[str, str] = {
    "修复": "fix", "修正": "fix", "解决": "fix",
    "新增": "feat", "添加": "feat", "增加": "feat", "支持": "feat",
    "更新": "chore", "优化": "perf", "重构": "refactor",
    "文档": "docs", "测试": "test", "构建": "build", "发布": "release",
    "删除": "remove", "移除": "remove", "合并": "merge", "回滚": "revert",
}

_CONV_RE = re.compile(r"^\s*([A-Za-z]+)(?:\([^)]*\))?!?:\s*")
_ZH_RE = re.compile(r"^\s*([\u4e00-\u9fff]{2})[:：]\s*")


@dataclass
class ReportStats:
    year: int
    root: str
    generated_at: str
    repo_count: int
    repo_names: list[str]
    commit_count: int
    insertions: int
    deletions: int
    lines_changed: int
    file_count: int
    active_days: int
    longest_streak: int
    current_streak: int
    first_dt: datetime | None
    last_dt: datetime | None
    by_hour: list[int]
    by_weekday: list[int]
    daily: dict[str, int]
    languages: list[tuple[str, int]]
    top_files: list[tuple[str, int]]
    keywords: list[tuple[str, int]]
    commit_types: list[tuple[str, int]]
    repo_commits: list[tuple[str, int]]
    busiest_day: tuple[str, int] | None
    busiest_count: int
    longest_subject: str
    language_count: int
    repo_details: list[dict]
    ticker: list[dict]
    persona: Persona
    warnings: list[str]

    def as_dict(self) -> dict:
        data = asdict(self)
        data["first_dt"] = self.first_dt.isoformat() if self.first_dt else None
        data["last_dt"] = self.last_dt.isoformat() if self.last_dt else None
        return data


def fmt_int(n: int) -> str:
    return f"{int(n):,}"


def fmt_human(n: int) -> str:
    n = int(n)
    if abs(n) >= 100_000_000:
        return f"{n / 100_000_000:.1f}亿"
    if abs(n) >= 10_000:
        return f"{n / 10_000:.1f}万"
    return f"{n:,}"


def fmt_pct(value: float) -> str:
    return f"{value * 100:.0f}%"


def fmt_signed_pair(insertions: int, deletions: int) -> str:
    """Keep +additions / -deletions on the same unit scale."""
    if max(insertions, deletions) >= 10_000:
        return f"+{insertions / 10_000:.1f}万 / -{deletions / 10_000:.1f}万"
    return f"+{insertions:,} / -{deletions:,}"


def parse_daily(daily: dict[str, int]) -> dict[date, int]:
    return {date.fromisoformat(k): v for k, v in daily.items()}


def _commit_type(subject: str) -> str | None:
    m = _CONV_RE.match(subject)
    if m:
        t = m.group(1).lower()
        # Only real Conventional Commit types. A subject such as
        # "traffic: ..." must not turn into a fake type.
        return t if t in KNOWN_TYPES else None
    m = _ZH_RE.match(subject)
    if m:
        return ZH_TYPES.get(m.group(1))
    return None


def language_breakdown(
    languages: list[tuple[str, int]],
    *,
    limit: int = 8,
    min_share: float = 0.01,
) -> tuple[list[tuple[str, int]], int]:
    """Top languages plus an "其他" bucket, dropping invisible slivers."""
    total = sum(v for _, v in languages) or 1
    rows = [(name, n) for name, n in languages if n / total >= min_share][:limit]
    rest = total - sum(n for _, n in rows)
    if rest > 0 and rest / total >= min_share:
        rows.append(("其他", rest))
    return rows, total


def _streaks(active_dates: list[date], year: int) -> tuple[int, int]:
    longest = 0
    run = 0
    prev: date | None = None
    for d in active_dates:
        if prev is not None and (d - prev).days == 1:
            run += 1
        else:
            run = 1
        longest = max(longest, run)
        prev = d

    current = 0
    today = date.today()
    if year == today.year:
        cursor = today
        if cursor not in set(active_dates):
            cursor -= timedelta(days=1)
        active = set(active_dates)
        while cursor in active:
            current += 1
            cursor -= timedelta(days=1)
    return longest, current


def build_stats(
    *,
    year: int,
    root: str,
    repos: list[RepoResult],
    warnings: list[str] | None = None,
) -> ReportStats:
    warnings = list(warnings or [])
    commits: list[Commit] = []
    lang_counter: Counter[str] = Counter()
    file_counter: Counter[str] = Counter()
    repo_counter: Counter[str] = Counter()
    file_set: set[tuple[str, str]] = set()

    # Backups and copies of the same repo share commit hashes. Keep the
    # largest copy first and count every hash once, so a "projects" folder
    # full of snapshots does not inflate the report.
    ordered = sorted(repos, key=lambda repo: len(repo.commits), reverse=True)
    selected: list[tuple[RepoResult, list[Commit]]] = []
    seen_hashes: set[str] = set()
    for repo in ordered:
        if repo.warning:
            warnings.append(f"{repo.name}: {repo.warning}")
        unique: list[Commit] = []
        for commit in repo.commits:
            if commit.hash in seen_hashes:
                continue
            seen_hashes.add(commit.hash)
            unique.append(commit)
        if unique:
            selected.append((repo, unique))

    multi_repo = len(selected) > 1
    repo_line_counter: dict[str, int] = {}
    repo_langs: dict[str, Counter] = {}
    repo_files: dict[str, Counter] = {}
    for repo, unique in selected:
        repo_counter[repo.name] = len(unique)
        commits.extend(unique)
        repo_line_counter[repo.name] = 0
        repo_langs[repo.name] = Counter()
        repo_files[repo.name] = Counter()
        for commit in unique:
            for change in commit.changes:
                lang_counter[change.lang] += change.lines
                repo_langs[repo.name][change.lang] += change.lines
                repo_line_counter[repo.name] += change.lines
                if is_code_language(change.lang):
                    display = f"{repo.name}/{change.path}" if multi_repo else change.path
                    file_counter[display] += change.lines
                    repo_files[repo.name][change.path] += change.lines
                file_set.add((repo.name, change.path))

    repo_details: list[dict] = []
    for repo, unique in selected:
        if not unique:
            continue
        langs_r = repo_langs[repo.name].most_common(3)
        top_file = repo_files[repo.name].most_common(1)
        repo_details.append({
            "name": repo.name,
            "commits": len(unique),
            "lines": repo_line_counter.get(repo.name, 0),
            "langs": [[lang, n] for lang, n in langs_r],
            "first": min(c.dt for c in unique).strftime("%Y.%m.%d"),
            "last": max(c.dt for c in unique).strftime("%Y.%m.%d"),
            "readme": repo.readme_line,
            "top_file": [top_file[0][0], top_file[0][1]] if top_file else None,
            "remote": repo.remote,
            "recent": [
                {"date": c.dt.strftime("%m.%d"), "subject": c.subject.strip()[:90]}
                for c in sorted(unique, key=lambda c: c.dt, reverse=True)[:3]
                if len(c.subject.strip()) >= 10
            ],
        })
    repo_details.sort(key=lambda d: (-d["commits"], -d["lines"]))

    ticker: list[dict] = []
    seen_subject: set[str] = set()
    for commit in sorted(commits, key=lambda c: c.dt, reverse=True):
        subject = commit.subject.strip()
        if len(subject) < 10 or subject.lower().startswith("merge"):
            continue
        if subject in seen_subject:
            continue
        seen_subject.add(subject)
        ticker.append({
            "repo": commit.repo,
            "date": commit.dt.strftime("%m.%d"),
            "subject": subject[:100],
        })
        if len(ticker) >= 26:
            break

    commit_count = len(commits)
    insertions = sum(c.added for c in commits)
    deletions = sum(c.deleted for c in commits)
    lines_changed = insertions + deletions

    by_hour = [0] * 24
    by_weekday = [0] * 7
    daily: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    night_commits = 0
    early_commits = 0
    weekend_commits = 0

    for c in commits:
        by_hour[c.dt.hour] += 1
        by_weekday[c.dt.weekday()] += 1
        daily[c.dt.date().isoformat()] += 1
        if c.dt.hour >= 22 or c.dt.hour <= 4:
            night_commits += 1
        elif 5 <= c.dt.hour <= 8:
            early_commits += 1
        if c.dt.weekday() >= 5:
            weekend_commits += 1
        t = _commit_type(c.subject)
        if t:
            type_counter[t] += 1

    active_dates = sorted(date.fromisoformat(k) for k, v in daily.items() if v > 0)
    longest_streak, current_streak = _streaks(active_dates, year)

    busiest: tuple[str, int] | None = None
    busiest_count = 0
    if daily:
        busiest_count = max(daily.values())
        busiest_day = min(k for k, v in daily.items() if v == busiest_count)
        busiest = (busiest_day, busiest_count)

    first_dt = min((c.dt for c in commits), default=None)
    last_dt = max((c.dt for c in commits), default=None)
    longest_subject = max((c.subject for c in commits), key=len, default="")

    languages = lang_counter.most_common()
    top_files = [
        (path, n) for path, n in file_counter.most_common(12)
    ]
    keywords = extract_keywords([c.subject for c in commits], top=14)
    commit_types = type_counter.most_common(8)
    repo_commits = repo_counter.most_common()

    peak_hour = by_hour.index(max(by_hour)) if any(by_hour) else 0
    typed_commits = sum(type_counter.values())

    persona = build_persona(
        year=year,
        commits=commit_count,
        repos=len(repo_counter),
        lines=lines_changed,
        insertions=insertions,
        deletions=deletions,
        active_days=len(active_dates),
        longest_streak=longest_streak,
        current_streak=current_streak,
        night_commits=night_commits,
        early_commits=early_commits,
        weekend_commits=weekend_commits,
        peak_hour=peak_hour,
        fix_commits=type_counter.get("fix", 0),
        feat_commits=type_counter.get("feat", 0),
        typed_commits=typed_commits,
        lang_count=len(languages),
        busiest_count=busiest_count,
    )

    return ReportStats(
        year=year,
        root=root,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
        repo_count=len(repo_counter),
        repo_names=[name for name, _ in repo_commits],
        commit_count=commit_count,
        insertions=insertions,
        deletions=deletions,
        lines_changed=lines_changed,
        file_count=len(file_set),
        active_days=len(active_dates),
        longest_streak=longest_streak,
        current_streak=current_streak,
        first_dt=first_dt,
        last_dt=last_dt,
        by_hour=by_hour,
        by_weekday=by_weekday,
        daily=dict(sorted(daily.items())),
        languages=languages,
        top_files=top_files,
        keywords=keywords,
        commit_types=commit_types,
        repo_commits=repo_commits,
        busiest_day=busiest,
        busiest_count=busiest_count,
        longest_subject=longest_subject,
        language_count=len(languages),
        repo_details=repo_details,
        ticker=ticker,
        persona=persona,
        warnings=warnings,
    )
