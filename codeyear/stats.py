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
    new_repos: int
    total_commits: int
    tags_in_year: int
    earliest_dt: datetime | None
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
    monthly: list[int]
    hour_weekday: list[list[int]]
    size_buckets: list[tuple[str, int]]
    busiest_week: tuple[str, int] | None
    busiest_week_start: str | None
    longest_gap: tuple[int, str, str] | None
    largest_commit: dict | None
    largest_deletion: dict | None
    avg_subject_len: int
    conventional_share: float
    weekend_share: float
    night_share: float
    first_commit: dict | None
    last_commit: dict | None
    sessions: dict
    message_buckets: list[tuple[str, int]]
    language_quarters: list[dict]
    dormant: list[dict]
    avg_files_per_commit: float
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
    identity_label: str
    filtered_commits: int
    persona: Persona
    warnings: list[str]
    previous: dict | None = None

    def as_dict(self) -> dict:
        data = asdict(self)
        data["first_dt"] = self.first_dt.isoformat() if self.first_dt else None
        data["last_dt"] = self.last_dt.isoformat() if self.last_dt else None
        data["earliest_dt"] = self.earliest_dt.isoformat() if self.earliest_dt else None
        return data

    @property
    def public_source(self) -> bool:
        """True when stats came from the optional public GitHub mode."""
        return self.root.startswith(("https://github.com/", "http://github.com/"))


def compare_summary(current: "ReportStats", previous: "ReportStats") -> dict:
    def pct(now: int | float, before: int | float) -> float | None:
        return (now - before) / before if before else None

    return {
        "year": previous.year,
        # 去年原始值：0 提交时无法做同比，报告据此降级展示
        "previous_commits": previous.commit_count,
        "previous_lines": previous.lines_changed,
        "previous_insertions": previous.insertions,
        "previous_deletions": previous.deletions,
        "previous_active_days": previous.active_days,
        "previous_repos": previous.repo_count,
        "previous_streak": previous.longest_streak,
        "previous_avg_subject_len": previous.avg_subject_len,
        "previous_weekend_share": previous.weekend_share,
        "previous_night_share": previous.night_share,
        "previous_monthly": list(previous.monthly),
        # 今年 - 去年
        "commits": current.commit_count - previous.commit_count,
        "commits_pct": pct(current.commit_count, previous.commit_count),
        "lines": current.lines_changed - previous.lines_changed,
        "lines_pct": pct(current.lines_changed, previous.lines_changed),
        "insertions": current.insertions - previous.insertions,
        "deletions": current.deletions - previous.deletions,
        "active_days": current.active_days - previous.active_days,
        "active_days_pct": pct(current.active_days, previous.active_days),
        "repos": current.repo_count - previous.repo_count,
        "streak": current.longest_streak - previous.longest_streak,
        "avg_subject_len": current.avg_subject_len - previous.avg_subject_len,
        "weekend_share": current.weekend_share - previous.weekend_share,
        "night_share": current.night_share - previous.night_share,
    }


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


def _is_mine(
    commit: Commit,
    identity: tuple[str, str],
    aliases: list[str] | None = None,
) -> bool:
    email, name = identity
    email_l = commit.author_email.strip().lower()
    name_l = commit.author_name.strip().lower()
    for value in [email, name, *(aliases or [])]:
        value = (value or "").strip().lower()
        if value and (email_l == value or name_l == value):
            return True
    return False


def build_stats(
    *,
    year: int,
    root: str,
    repos: list[RepoResult],
    warnings: list[str] | None = None,
    identity: tuple[str, str] | None = None,
    aliases: list[str] | None = None,
) -> ReportStats:
    warnings = list(warnings or [])
    aliases = [alias.strip() for alias in (aliases or []) if alias.strip()]
    filtered_commits = 0
    identity_label = ""
    if identity:
        email, name = identity
        identity_label = f"{name} <{email}>" if name and email else (email or name)
    commits: list[Commit] = []
    lang_counter: Counter[str] = Counter()
    file_counter: Counter[str] = Counter()
    repo_counter: Counter[str] = Counter()
    file_set: set[tuple[str, str]] = set()

    # Backups and copies of the same repo share commit hashes. Keep the
    # largest copy first and count every hash once, so a "projects" folder
    # full of snapshots does not inflate the report.
    # Copies of the same project (same first commit or same remote) should read
    # as one project. A work/backup folder full of clones then collapses into
    # the biggest copy instead of showing up as several repos.
    parent = list(range(len(repos)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a: int, b: int) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    buckets: dict[str, int] = {}
    for i, repo in enumerate(repos):
        keys: list[str] = []
        if repo.root:
            keys.append("root:" + repo.root)
        remote = (repo.remote or "").strip().lower().removesuffix(".git")
        if remote:
            keys.append("remote:" + remote)
        for key in keys:
            if key in buckets:
                union(i, buckets[key])
            else:
                buckets[key] = i

    grouped: dict[int, list[RepoResult]] = {}
    for i, repo in enumerate(repos):
        grouped.setdefault(find(i), []).append(repo)
    chosen = [
        max(group, key=lambda r: (len(r.commits), -len(r.name)))
        for group in grouped.values()
    ]

    ordered = sorted(chosen, key=lambda repo: len(repo.commits), reverse=True)
    selected: list[tuple[RepoResult, list[Commit]]] = []
    seen_hashes: set[str] = set()
    for repo in ordered:
        if repo.warning:
            warnings.append(f"{repo.name}: {repo.warning}")
        unique: list[Commit] = []
        for commit in repo.commits:
            if commit.hash in seen_hashes:
                continue
            if identity is not None and not _is_mine(commit, identity, aliases):
                filtered_commits += 1
                continue
            seen_hashes.add(commit.hash)
            unique.append(commit)
        if unique:
            selected.append((repo, unique))

    # Year-scoped counts stay on the active repos; lifetime numbers use every
    # local repo after copy/backup dedupe, so an old project that was quiet
    # this year still contributes its history.
    new_repos = sum(
        1 for repo, _ in selected
        if repo.root_dt is not None and repo.root_dt.year == year
    )
    total_commits = sum(repo.total_commits for repo in chosen)
    tags_in_year = sum(repo.tags_in_year for repo in chosen)
    root_dates = [repo.root_dt for repo in chosen if repo.root_dt is not None]
    earliest_dt = min(root_dates) if root_dates else None

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
            "added": sum(c.added for c in unique),
            "deleted": sum(c.deleted for c in unique),
            "active_days": len({c.dt.date() for c in unique}),
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
    monthly = [0] * 12
    hour_weekday = [[0] * 24 for _ in range(7)]
    size_counter: Counter[str] = Counter()
    week_counter: Counter[tuple[int, int]] = Counter()
    subject_lens: list[int] = []
    daily: Counter[str] = Counter()
    type_counter: Counter[str] = Counter()
    night_commits = 0
    early_commits = 0
    weekend_commits = 0

    for c in commits:
        by_hour[c.dt.hour] += 1
        by_weekday[c.dt.weekday()] += 1
        monthly[c.dt.month - 1] += 1
        hour_weekday[c.dt.weekday()][c.dt.hour] += 1
        daily[c.dt.date().isoformat()] += 1
        if c.subject:
            subject_lens.append(len(c.subject))
        size = c.added + c.deleted
        if size < 10:
            size_counter["0–10"] += 1
        elif size < 100:
            size_counter["10–100"] += 1
        elif size < 500:
            size_counter["100–500"] += 1
        elif size < 2000:
            size_counter["500–2k"] += 1
        else:
            size_counter["2k+"] += 1
        iso = c.dt.isocalendar()
        week_counter[(iso[0], iso[1])] += 1
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

    size_order = ["0–10", "10–100", "100–500", "500–2k", "2k+"]
    size_buckets = [(label, size_counter.get(label, 0)) for label in size_order]

    busiest_week: tuple[str, int] | None = None
    busiest_week_start: str | None = None
    if week_counter:
        (wy, wn), wc = max(week_counter.items(), key=lambda kv: kv[1])
        busiest_week = (f"{wy}-W{wn:02d}", wc)
        try:
            busiest_week_start = date.fromisocalendar(wy, wn, 1).strftime("%Y.%m.%d")
        except ValueError:
            busiest_week_start = None

    longest_gap: tuple[int, str, str] | None = None
    if len(active_dates) >= 2:
        best_gap = 0
        best_i = 0
        for i in range(1, len(active_dates)):
            gap = (active_dates[i] - active_dates[i - 1]).days
            if gap > best_gap:
                best_gap, best_i = gap, i
        if best_gap > 0:
            longest_gap = (
                best_gap,
                active_dates[best_i - 1].strftime("%Y.%m.%d"),
                active_dates[best_i].strftime("%Y.%m.%d"),
            )

    largest_commit: dict | None = None
    largest_deletion: dict | None = None
    if commits:
        lc = max(commits, key=lambda c: c.added + c.deleted)
        largest_commit = {
            "lines": lc.added + lc.deleted,
            "repo": lc.repo,
            "date": lc.dt.strftime("%Y.%m.%d"),
            "subject": lc.subject[:80],
        }
        ld = max(commits, key=lambda c: c.deleted)
        if ld.deleted > 0:
            largest_deletion = {
                "lines": ld.deleted,
                "repo": ld.repo,
                "date": ld.dt.strftime("%Y.%m.%d"),
                "subject": ld.subject[:80],
            }

    avg_subject_len = round(sum(subject_lens) / len(subject_lens)) if subject_lens else 0
    conventional_share = sum(type_counter.values()) / max(commit_count, 1)
    weekend_share = weekend_commits / max(commit_count, 1)
    night_share = night_commits / max(commit_count, 1)

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

    sorted_commits = sorted(commits, key=lambda c: c.dt)
    first_commit = None
    last_commit = None
    if sorted_commits:
        fc, lc2 = sorted_commits[0], sorted_commits[-1]
        first_commit = {"date": fc.dt.strftime("%Y.%m.%d %H:%M"), "repo": fc.repo,
                        "subject": fc.subject[:80]}
        last_commit = {"date": lc2.dt.strftime("%Y.%m.%d %H:%M"), "repo": lc2.repo,
                       "subject": lc2.subject[:80]}

    # A session is a run of commits with no gap longer than 2 hours.
    sessions = {"count": 0, "longest_minutes": 0, "longest_commits": 0,
                "longest_start": "", "longest_end": "", "avg_minutes": 0}
    if sorted_commits:
        groups: list[list[Commit]] = []
        current = [sorted_commits[0]]
        for c in sorted_commits[1:]:
            if (c.dt - current[-1].dt).total_seconds() <= 2 * 3600:
                current.append(c)
            else:
                groups.append(current)
                current = [c]
        groups.append(current)
        durations = [(g[-1].dt - g[0].dt).total_seconds() / 60 for g in groups]
        longest_i = max(range(len(groups)), key=lambda i: durations[i])
        sessions = {
            "count": len(groups),
            "longest_minutes": round(durations[longest_i]),
            "longest_commits": len(groups[longest_i]),
            "longest_start": groups[longest_i][0].dt.strftime("%Y.%m.%d %H:%M"),
            "longest_end": groups[longest_i][-1].dt.strftime("%Y.%m.%d %H:%M"),
            "avg_minutes": round(sum(durations) / len(durations)),
        }

    message_counter: Counter[str] = Counter()
    for c in commits:
        length = len(c.subject)
        if length < 20:
            message_counter["0–20"] += 1
        elif length < 40:
            message_counter["20–40"] += 1
        elif length < 80:
            message_counter["40–80"] += 1
        elif length < 160:
            message_counter["80–160"] += 1
        else:
            message_counter["160+"] += 1
    message_buckets = [
        (label, message_counter.get(label, 0))
        for label in ["0–20", "20–40", "40–80", "80–160", "160+"]
    ]

    top_langs = [name for name, _ in languages[:4]]
    quarters: list[Counter[str]] = [Counter() for _ in range(4)]
    for c in commits:
        q = min((c.dt.month - 1) // 3, 3)
        for change in c.changes:
            quarters[q][change.lang] += change.lines
    language_quarters = []
    for i, qc in enumerate(quarters):
        rows = [(name, qc.get(name, 0)) for name in top_langs]
        rest = sum(v for k, v in qc.items() if k not in top_langs)
        rows.append(("其他", rest))
        language_quarters.append({"q": f"Q{i + 1}", "rows": rows})

    today_date = datetime.now().date()
    dormant: list[dict] = []
    for repo in repo_details:
        try:
            last_d = datetime.strptime(repo["last"], "%Y.%m.%d").date()
        except ValueError:
            continue
        days = (today_date - last_d).days
        if days > 30:
            dormant.append({
                "name": repo["name"], "last": repo["last"], "days": days,
                "commits": repo["commits"],
            })
    dormant.sort(key=lambda d: -d["days"])

    avg_files_per_commit = (
        round(sum(c.files for c in commits) / max(commit_count, 1), 1)
        if commits else 0.0
    )
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
        new_repos=new_repos,
        total_commits=total_commits,
        tags_in_year=tags_in_year,
        earliest_dt=earliest_dt,
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
        monthly=monthly,
        hour_weekday=hour_weekday,
        size_buckets=size_buckets,
        busiest_week=busiest_week,
        busiest_week_start=busiest_week_start,
        longest_gap=longest_gap,
        largest_commit=largest_commit,
        largest_deletion=largest_deletion,
        avg_subject_len=avg_subject_len,
        conventional_share=conventional_share,
        weekend_share=weekend_share,
        night_share=night_share,
        first_commit=first_commit,
        last_commit=last_commit,
        sessions=sessions,
        message_buckets=message_buckets,
        language_quarters=language_quarters,
        dormant=dormant,
        avg_files_per_commit=avg_files_per_commit,
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
        identity_label=identity_label,
        filtered_commits=filtered_commits,
        persona=persona,
        warnings=warnings,
    )
