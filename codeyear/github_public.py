"""Generate a CodeYear report from public GitHub data.

This is an optional online mode. The regular ``scan`` command still reads
local git and never uploads anything. This module only reads public
repositories through the GitHub REST API.
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from . import i18n
from .languages import language_for
from .runner import render, report_path
from .scanner import Commit, FileChange, RepoResult
from .stats import ReportStats, build_stats, fmt_human, fmt_int

API = "https://api.github.com"
DETAIL_WORKERS = 8
CACHE_VERSION = 1
CACHE_MAX = 5000


class _IncompleteList(list):
    """List result carrying an API pagination-cap marker."""

    truncated: bool = False


def default_cache_dir() -> Path:
    return Path.home() / ".cache" / "codeyear"

_OFFSET_RE = re.compile(
    r"^(?:UTC|GMT)?\s*([+-])\s*(\d{1,2})(?::?(\d{2}))?$", re.I
)
_FALLBACK_ZONES: dict[str, int] = {
    "utc": 0,
    "gmt": 0,
    "etc/utc": 0,
    "europe/london": 0,
    "europe/berlin": 60,
    "europe/paris": 60,
    "asia/shanghai": 480,
    "asia/chongqing": 480,
    "asia/hong_kong": 480,
    "asia/taipei": 480,
    "asia/singapore": 480,
    "asia/tokyo": 540,
    "asia/seoul": 540,
    "Asia/Kolkata".lower(): 330,
    "america/new_york": -300,
    "america/chicago": -360,
    "america/denver": -420,
    "america/los_angeles": -480,
}


def _parse_tz(tz: str | tzinfo | None = None) -> tzinfo | None:
    if isinstance(tz, tzinfo):
        return tz
    spec = (
        tz
        or os.environ.get("CODEYEAR_TZ")
        or os.environ.get("TZ")
        or ""
    ).strip()
    if not spec:
        return None
    if spec.upper() in {"Z", "UTC", "GMT"}:
        return timezone.utc
    m = _OFFSET_RE.match(spec)
    if m:
        sign = -1 if m.group(1) == "-" else 1
        hours = int(m.group(2))
        minutes = int(m.group(3) or 0)
        if hours <= 14 and minutes < 60:
            return timezone(sign * timedelta(hours=hours, minutes=minutes))
    try:
        return ZoneInfo(spec)
    except (ZoneInfoNotFoundError, KeyError, ValueError):
        mins = _FALLBACK_ZONES.get(spec.lower())
        if mins is not None:
            return timezone(timedelta(minutes=mins))
    return None


def _load_cache(path: Path | None) -> dict:
    if path is None or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict) or data.get("version") != CACHE_VERSION:
        return {}
    details = data.get("details")
    return details if isinstance(details, dict) else {}


def _slim_detail(detail: dict) -> dict:
    """Keep only fields needed by CodeYear, dropping multi-KB diff patches."""
    commit = detail.get("commit") or {}
    author = commit.get("author") or {}
    msg_lines = (commit.get("message") or "").splitlines()
    return {
        "parents": [{} for _ in (detail.get("parents") or [])],
        "commit": {
            "author": {"date": author.get("date")},
            "message": msg_lines[0][:200] if msg_lines else "",
        },
        "stats": {
            "additions": int((detail.get("stats") or {}).get("additions", 0)),
            "deletions": int((detail.get("stats") or {}).get("deletions", 0)),
        },
        "files": [
            {
                "filename": f.get("filename") or "",
                "additions": int(f.get("additions", 0)),
                "deletions": int(f.get("deletions", 0)),
            }
            for f in (detail.get("files") or [])
        ],
    }


def _save_cache(path: Path | None, details: dict) -> None:
    if path is None:
        return
    tmp: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if len(details) > CACHE_MAX:
            details = dict(list(details.items())[-CACHE_MAX:])
        payload = json.dumps(
            {"version": CACHE_VERSION, "details": details},
            ensure_ascii=False,
        )
        # Write-then-rename: an interrupted run must never leave a truncated
        # JSON file that breaks the next scan.
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(payload, encoding="utf-8")
        os.replace(tmp, path)
    except OSError:
        if tmp is not None:
            with contextlib.suppress(OSError):
                tmp.unlink()


def _dt(
    value: str | None, tz: str | tzinfo | None = None
) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        # GitHub timestamps are UTC. Convert to the requested timezone (or the
        # machine's local timezone) so hour-of-day and late-night statistics
        # match the local report.
        if parsed.tzinfo is not None:
            target_tz = _parse_tz(tz)
            parsed = parsed.astimezone(target_tz).replace(tzinfo=None)
        return parsed
    except ValueError:
        return None


class NoPublicCommitsError(RuntimeError):
    """The requested year contains no public commits."""


class GitHubAPI:
    def __init__(self, token: str | None = None) -> None:
        self.token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        self.remaining: int | None = None

    def get(self, path: str, params: dict | None = None):
        url = API + path
        if params:
            url += "?" + urllib.parse.urlencode(params)
        request = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "CodeYear",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        if self.token:
            request.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                remaining = response.headers.get("X-RateLimit-Remaining")
                if remaining is not None:
                    self.remaining = int(remaining)
                if response.status == 202:
                    return None
                body = response.read().decode("utf-8")
                return json.loads(body) if body else None
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code == 403 and (exc.headers.get("X-RateLimit-Remaining") == "0"):
                raise RuntimeError(
                    "GitHub API 已限流。请稍后重试，或设置 GITHUB_TOKEN / --token。"
                ) from exc
            raise

    def paginate(self, path: str, params: dict | None = None, pages: int = 10) -> list:
        items: list = []
        for page in range(1, pages + 1):
            query = dict(params or {})
            query.update({"per_page": 100, "page": page})
            data = self.get(path, query)
            if not data:
                break
            items.extend(data)
            if len(data) < 100:
                break
        return items


def _repos(
    api: GitHubAPI,
    username: str,
    since: datetime,
    include_forks: bool,
    *,
    tz: str | tzinfo | None = None,
) -> list[dict]:
    target_tz = _parse_tz(tz)
    repos = _IncompleteList()
    for page in range(1, 11):
        data = api.get(f"/users/{username}/repos", {
            "type": "owner", "sort": "pushed", "direction": "desc",
            "per_page": 100, "page": page,
        })
        if not data:
            break
        for repo in data:
            if repo.get("private"):
                continue
            if repo.get("fork") and not include_forks:
                continue
            pushed = _dt(repo.get("pushed_at"), tz=target_tz)
            if pushed and pushed < since:
                return repos
            repos.append(repo)
        if len(data) < 100:
            break
    else:
        repos.truncated = True
    return repos


def _commits(
    api: GitHubAPI,
    repo: dict,
    username: str,
    year: int,
    limit: int,
    quiet: bool,
    cache: dict | None = None,
    *,
    tz: str | tzinfo | None = None,
) -> list[Commit]:
    target_tz = _parse_tz(tz)
    full = repo["full_name"]
    # Pad the UTC window by a day on each side; actual filtering below uses
    # the local year, so commits near midnight in non-UTC zones are kept.
    since = f"{year - 1}-12-31T00:00:00Z"
    until = f"{year + 1}-01-02T00:00:00Z"
    listed = _IncompleteList()
    def _eligible_list_item(item: dict) -> bool:
        if len(item.get("parents") or []) > 1:
            return False
        raw_date = ((item.get("commit") or {}).get("author") or {}).get("date")
        if raw_date:
            d = _dt(raw_date, tz=target_tz)
            if d is not None and d.year != year:
                return False
        return True

    # A busy repository can exceed 1,000 commits in one year; keep paging
    # until the caller's budget is reached or GitHub runs out of pages.
    for page in range(1, 101):
        data = api.get(f"/repos/{full}/commits", {
            "author": username, "since": since, "until": until,
            "per_page": 100, "page": page,
        })
        if not data:
            break
        eligible = [item for item in data if _eligible_list_item(item)]
        if len(listed) + len(eligible) > limit:
            listed.extend(eligible[: limit - len(listed)])
            listed.truncated = True
            break
        listed.extend(eligible)
        if len(data) < 100:
            break
        if len(listed) >= limit:
            # At an exact page boundary, completeness cannot be inferred from
            # a full page alone. Probe for another entry rather than warn on a
            # repository whose history ends exactly at the limit.
            if len(listed) == limit and page < 100:
                extra = api.get(f"/repos/{full}/commits", {
                    "author": username, "since": since, "until": until,
                    "per_page": 100, "page": page + 1,
                }) or []
                extra_eligible = [it for it in extra if _eligible_list_item(it)]
                listed.truncated = bool(extra_eligible or len(extra) == 100)
            else:
                listed.truncated = True
            break
    else:
        listed.truncated = True

    items = listed[:limit]
    keys = [f"{full}@{item['sha']}" for item in items]
    details: list[dict | None] = []
    missing: list[tuple[int, dict]] = []
    for index, (item, key) in enumerate(zip(items, keys)):
        if cache is not None and key in cache:
            details.append(cache[key])
        else:
            details.append(None)
            missing.append((index, item))

    if missing:
        if api.remaining is not None and api.remaining < len(missing) + 5:
            raise RuntimeError(i18n.tr(
                "GitHub API 额度不足，请使用更高额度的 token（如 CODEYEAR_TOKEN）后重试。"
            ))

        def fetch_detail(entry: tuple[int, dict]):
            idx, item = entry
            detail = api.get(f"/repos/{full}/commits/{item['sha']}")
            if cache is not None and detail:
                cache[keys[idx]] = _slim_detail(detail)
            return detail

        # Commit details are independent; a small pool cuts wall time without
        # changing the request count or adding dependencies.
        with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
            fetched = list(pool.map(fetch_detail, missing))
        for (index, _item), detail in zip(missing, fetched):
            details[index] = detail

    commits = _IncompleteList()
    # The list endpoint may have more entries than the detail budget, or may
    # hit our page cap. Preserve that fact even when filtering removes merges.
    commits.truncated = listed.truncated or len(listed) > limit
    for item, detail in zip(items, details):
        if not detail:
            commits.truncated = True
            continue
        # Match the local scanner's --no-merges behavior.
        if len(detail.get("parents") or []) > 1:
            continue
        author_date = ((detail.get("commit") or {}).get("author") or {}).get("date")
        dt = _dt(author_date, tz=target_tz)
        if dt is None:
            dt = _dt((item.get("commit") or {}).get("author", {}).get("date"), tz=target_tz)
        if dt is None:
            commits.truncated = True
            continue
        if dt.year != year:
            continue
        message = ((detail.get("commit") or {}).get("message") or "").splitlines()
        subject = message[0].strip() if message else ""
        stats = detail.get("stats") or {}
        changes: list[FileChange] = []
        for file in detail.get("files") or []:
            path = file.get("filename") or ""
            lang = language_for(path)
            if lang is None:
                continue
            f_add = int(file.get("additions", 0))
            f_del = int(file.get("deletions", 0))
            changes.append(FileChange(
                path=path, lang=lang,
                lines=f_add + f_del,
                added=f_add,
                deleted=f_del,
            ))
        commits.append(Commit(
            repo=full,
            hash=item["sha"],
            dt=dt,
            subject=subject[:200],
            added=int(stats.get("additions", 0)),
            deleted=int(stats.get("deletions", 0)),
            files=len(detail.get("files") or []),
            author_email=username,
            author_name=username,
            changes=changes,
        ))
    if not quiet and commits:
        print(i18n.tr(
            "    {repo} · {count} 次提交", repo=full, count=len(commits),
        ), file=sys.stderr)
    return commits


def _total_commits(api: GitHubAPI, full: str, username: str) -> int:
    for attempt in range(2):
        data = api.get(f"/repos/{full}/stats/contributors")
        if isinstance(data, list):
            for contributor in data:
                author = contributor.get("author") or {}
                if (author.get("login") or "").lower() == username.lower():
                    return sum(int(week.get("c", 0)) for week in contributor.get("weeks", []))
            return 0
        if attempt == 0:
            time.sleep(0.35)
    return 0


def _contributed_repos(
    api: GitHubAPI,
    login: str,
    year: int,
    include_forks: bool,
) -> list[dict]:
    """Public repos the user committed to but does not own.

    One search request (plus pagination) finds commits authored by *login* in
    a year; the returned ``repository`` objects are merged into the scan set,
    so PRs merged into an org or another project count too.
    """
    found: dict[str, dict] = {}
    query = f"author:{login} author-date:{year}-01-01..{year}-12-31"
    for page in range(1, 4):
        try:
            data = api.get("/search/commits", {
                "q": query, "per_page": 100, "page": page,
            })
        except Exception:
            break
        items = (data or {}).get("items") or []
        if not items:
            break
        for item in items:
            repo = item.get("repository") or {}
            full = repo.get("full_name")
            if not full or full in found or repo.get("private"):
                continue
            if repo.get("fork") and not include_forks:
                continue
            if (repo.get("owner") or {}).get("login", "").lower() == login.lower():
                # Already covered by /users/{login}/repos.
                continue
            repo["_contributed_only"] = True
            found[full] = repo
        if len(items) < 100:
            break
    return list(found.values())


def fetch_stats(
    username: str,
    year: int,
    *,
    token: str | None = None,
    max_commits: int = 200,
    include_forks: bool = False,
    quiet: bool = False,
    cache_path: Path | None = None,
    tz: str | tzinfo | None = None,
    include_contributed: bool = False,
) -> tuple[ReportStats, list[str], str]:
    api = GitHubAPI(token)
    target_tz = _parse_tz(tz)
    cache = _load_cache(cache_path)
    if not api.token and max_commits > 30:
        max_commits = 30
        if not quiet:
            print("  ! " + i18n.tr(
                "未设置 GITHUB_TOKEN，最多拉取 30 条提交。"
            ), file=sys.stderr)

    try:
        user = api.get(f"/users/{urllib.parse.quote(username)}")
        if not user:
            raise RuntimeError(i18n.tr(
                "找不到 GitHub 用户: {username}", username=username,
            ))
        login = user.get("login") or username
        display_name = user.get("name") or login
        # Pad the repo cutoff by 1 day so repos pushed near Jan 1 UTC are not
        # skipped when converted to negative-offset timezones.
        since = datetime(year - 1, 12, 31)

        if not quiet:
            print(f"CodeYear · github.com/{login} · {year}", file=sys.stderr)
        repos = _repos(api, login, since, include_forks, tz=target_tz)
        if include_contributed:
            known = {r.get("full_name") for r in repos}
            extra = [
                r for r in _contributed_repos(api, login, year, include_forks)
                if r.get("full_name") not in known
            ]
            repos.extend(extra)
        if getattr(repos, "truncated", False):
            warnings = [i18n.tr(
                "公开仓库超过分页上限，统计可能不完整。"
            )]
        else:
            warnings = []
    except RuntimeError as exc:
        raise RuntimeError(i18n.tr(
            "GitHub API 错误: {exc}", exc=exc,
        )) from exc

    results: list[RepoResult] = []
    total = 0
    for index, repo in enumerate(repos, 1):
        if total >= max_commits:
            break
        full = repo["full_name"]
        if not quiet:
            print(f"[{index}/{len(repos)}] {full}", file=sys.stderr)
        try:
            commits = _commits(
                api, repo, login, year, max_commits - total, quiet,
                cache=cache, tz=target_tz,
            )
        except RuntimeError as exc:
            warnings.append(str(exc))
            break
        if getattr(commits, "truncated", False):
            warnings.append(i18n.tr(
                "{repo} 的提交数据可能不完整（分页、数量上限或详情缺失）。", repo=full,
            ))
        if not commits:
            continue
        total += len(commits)
        if total >= max_commits and (
            getattr(commits, "truncated", False) or index < len(repos)
        ):
            warnings.append(i18n.tr(
                "已达到 --max-commits 上限（{limit}）", limit=max_commits,
            ))
        results.append(RepoResult(
            path=Path(full),
            name=full,
            commits=commits,
            remote=repo.get("html_url"),
            readme_line=repo.get("description") or "",
            root=full,
            root_dt=_dt(repo.get("created_at"), tz=target_tz),
            total_commits=len(commits),
            tags_in_year=0,
        ))

    if results:
        def _fetch_repo_total(res: RepoResult) -> tuple[int, str | None]:
            try:
                return _total_commits(api, res.name, login), None
            except RuntimeError as exc:
                return 0, str(exc)

        with ThreadPoolExecutor(
            max_workers=min(len(results), DETAIL_WORKERS)
        ) as pool:
            totals = list(pool.map(_fetch_repo_total, results))
        for res, (repo_total, err) in zip(results, totals):
            if err:
                warnings.append(err)
            res.total_commits = repo_total or len(res.commits)

    if not results:
        _save_cache(cache_path, cache)
        if warnings:
            raise RuntimeError(warnings[-1])
        raise NoPublicCommitsError(i18n.tr(
            "{login} 在 {year} 年没有找到公开提交。", login=login, year=year,
        ))

    _save_cache(cache_path, cache)

    stats = build_stats(
        year=year,
        root=f"https://github.com/{login}",
        repos=results,
        warnings=warnings,
        identity=(login, display_name),
    )
    if stats.commit_count == 0:
        if warnings:
            raise RuntimeError(warnings[-1])
        raise NoPublicCommitsError(i18n.tr(
            "{login} 在 {year} 年没有找到公开提交。", login=login, year=year,
        ))
    return stats, warnings, login


def run(
    username: str,
    year: int,
    out_dir: str | Path,
    *,
    token: str | None = None,
    max_commits: int = 200,
    include_forks: bool = False,
    open_report: bool = False,
    quiet: bool = False,
    theme: str = "paper",
    card_only: bool = False,
    profile_repo: str | Path | None = None,
    push_profile: bool = False,
    fallback_previous: bool = False,
    cache_dir: str | Path | None = None,
    no_cache: bool = False,
    lang: str = "zh",
    tz: str | None = None,
    require_complete: bool = False,
    include_contributed: bool = False,
) -> int:
    cache_path = None
    if not no_cache:
        effective_dir = Path(cache_dir) if cache_dir else default_cache_dir()
        safe_name = re.sub(r"[^a-z0-9_.-]", "_", username.lower())
        cache_path = effective_dir / f"github-{safe_name}.json"
    try:
        try:
            stats, warnings, login = fetch_stats(
                username, year, token=token, max_commits=max_commits,
                include_forks=include_forks, quiet=quiet,
                cache_path=cache_path, tz=tz,
                include_contributed=include_contributed,
            )
        except NoPublicCommitsError:
            if not fallback_previous or year != datetime.now().year:
                raise
            stats, warnings, login = fetch_stats(
                username, year - 1, token=token, max_commits=max_commits,
                include_forks=include_forks, quiet=quiet,
                cache_path=cache_path, tz=tz,
                include_contributed=include_contributed,
            )
        else:
            if (fallback_previous and not stats.commit_count
                    and year == datetime.now().year):
                previous, prev_warnings, login = fetch_stats(
                    username, year - 1, token=token, max_commits=max_commits,
                    include_forks=include_forks, quiet=quiet,
                    cache_path=cache_path, tz=tz,
                    include_contributed=include_contributed,
                )
                if previous.commit_count:
                    stats, warnings = previous, prev_warnings
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    if warnings and (profile_repo or require_complete):
        print(i18n.tr("公开统计可能不完整："), file=sys.stderr)
        for warning in warnings:
            print(f"  - {warning}", file=sys.stderr)
        if push_profile or require_complete:
            print(i18n.tr("已取消自动更新；请先处理上述警告。"), file=sys.stderr)
            return 1

    year = stats.year
    out = Path(out_dir)
    formats = {"card"} if card_only else None
    written = render(stats, out, formats=formats, card_theme=theme)
    embed = chr(10).join([
        "<picture>",
        f'  <source media="(prefers-color-scheme: dark)" '
        f'srcset="./codeyear-{year}-card-dark.svg">',
        f'  <img src="./codeyear-{year}-card.svg" width="640" '
        f'alt="CodeYear {year}">',
        "</picture>",
        "",
    ])
    embed_path = out / f"codeyear-{year}-embed.md"
    embed_path.write_text(embed, encoding="utf-8")
    written.append(("EMBED", embed_path))
    embed_en = chr(10).join([
        "<picture>",
        f'  <source media="(prefers-color-scheme: dark)" '
        f'srcset="./codeyear-{year}-card-en-dark.svg">',
        f'  <img src="./codeyear-{year}-card-en.svg" width="640" '
        f'alt="CodeYear {year}">',
        "</picture>",
        "",
    ])
    embed_en_path = out / f"codeyear-{year}-embed-en.md"
    embed_en_path.write_text(embed_en, encoding="utf-8")
    written.append(("EMBED-EN", embed_en_path))

    if profile_repo:
        cards = {label: path for label, path in written}
        if lang == "en":
            light, dark = cards.get("CARD-EN"), cards.get("CARD-DARK-EN")
        else:
            light, dark = cards.get("CARD"), cards.get("CARD-DARK")
        if light and dark:
            from .profile import update_profile

            try:
                repo, changed, pushed = update_profile(
                    profile_repo, year, light, dark, push=push_profile,
                )
                written.append(("PROFILE", repo))
                if changed:
                    state = "已提交并推送" if pushed else "仅写入本地"
                    print("\n" + i18n.tr(
                        "Profile  {state} · {repo}",
                        state=i18n.tr(state), repo=repo,
                    ))
                else:
                    print("\n" + i18n.tr(
                        "Profile  卡片已是最新 · {repo}", repo=repo,
                    ))
            except Exception as exc:  # pragma: no cover - user environment
                print(i18n.tr(
                    "  ! 更新 Profile 失败: {exc}", exc=exc
                ), file=sys.stderr)
                return 1

    print()
    print(i18n.tr(
        "CodeYear {year}  ·  {title}",
        year=year, title=stats.persona.title,
    ))
    print("-" * 46)
    print(f"{i18n.tr('账号'):<10}github.com/{login}")
    print(f"{i18n.tr('仓库'):<10}{stats.repo_count}")
    print(f"{i18n.tr('提交'):<10}{fmt_int(stats.commit_count)}")
    print(f"{i18n.tr('代码行'):<10}{fmt_human(stats.lines_changed)}")
    print(i18n.tr(
        "活跃      {days} 天 · 涉及 {count} 个文件",
        days=stats.active_days, count=stats.file_count,
    ))
    print(f"{i18n.tr('输出'):<10}{out.resolve()}")
    print("-" * 46)
    for label, path in written:
        print(f"{label:<9}  {path.name}")
    if warnings:
        print()
        print(i18n.tr("提示:"))
        for warning in warnings:
            print(f"  - {warning}")
    if open_report:
        html = report_path(written, lang=lang)
        if html:
            try:
                if hasattr(os, "startfile"):
                    os.startfile(str(html))  # type: ignore[attr-defined]
                else:
                    import webbrowser
                    webbrowser.open(html.resolve().as_uri())
            except Exception:
                pass
    return 0
