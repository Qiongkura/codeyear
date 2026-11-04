"""Generate a CodeYear report from public GitHub data.

This is an optional online mode. The regular ``scan`` command still reads
local git and never uploads anything. This module only reads public
repositories through the GitHub REST API.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from .languages import language_for
from .runner import render
from .scanner import Commit, FileChange, RepoResult
from .stats import ReportStats, build_stats, fmt_human, fmt_int

API = "https://api.github.com"
DETAIL_WORKERS = 4


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


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


def _repos(api: GitHubAPI, username: str, since: datetime,
           include_forks: bool) -> list[dict]:
    repos: list[dict] = []
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
            pushed = _dt(repo.get("pushed_at"))
            if pushed and pushed < since:
                return repos
            repos.append(repo)
        if len(data) < 100:
            break
    return repos


def _commits(
    api: GitHubAPI,
    repo: dict,
    username: str,
    year: int,
    limit: int,
    quiet: bool,
) -> list[Commit]:
    full = repo["full_name"]
    since = f"{year}-01-01T00:00:00Z"
    until = f"{year + 1}-01-01T00:00:00Z"
    listed: list[dict] = []
    for page in range(1, 11):
        data = api.get(f"/repos/{full}/commits", {
            "author": username, "since": since, "until": until,
            "per_page": 100, "page": page,
        })
        if not data:
            break
        listed.extend(data)
        if len(data) < 100 or len(listed) >= limit:
            break

    items = listed[:limit]
    if api.remaining is not None and api.remaining < len(items) + 5:
        raise RuntimeError("GitHub API 额度不足，请设置 GITHUB_TOKEN 后重试。")

    def fetch_detail(item: dict):
        return api.get(f"/repos/{full}/commits/{item['sha']}")

    # Commit details are independent; a small pool cuts wall time without
    # changing the request count or adding dependencies.
    with ThreadPoolExecutor(max_workers=DETAIL_WORKERS) as pool:
        details = list(pool.map(fetch_detail, items))

    commits: list[Commit] = []
    for item, detail in zip(items, details):
        if not detail:
            continue
        # Match the local scanner's --no-merges behavior.
        if len(detail.get("parents") or []) > 1:
            continue
        author_date = ((detail.get("commit") or {}).get("author") or {}).get("date")
        dt = _dt(author_date)
        if dt is None:
            dt = _dt((item.get("commit") or {}).get("author", {}).get("date"))
        if dt is None or dt.year != year:
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
            changes.append(FileChange(
                path=path, lang=lang,
                lines=int(file.get("additions", 0)) + int(file.get("deletions", 0)),
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
        print(f"    {full} · {len(commits)} 次提交", file=sys.stderr)
    return commits


def _total_commits(api: GitHubAPI, full: str, username: str) -> int:
    for _ in range(3):
        data = api.get(f"/repos/{full}/stats/contributors")
        if isinstance(data, list):
            for contributor in data:
                author = contributor.get("author") or {}
                if (author.get("login") or "").lower() == username.lower():
                    return sum(int(week.get("c", 0)) for week in contributor.get("weeks", []))
            return 0
        time.sleep(1)
    return 0


def fetch_stats(
    username: str,
    year: int,
    *,
    token: str | None = None,
    max_commits: int = 200,
    include_forks: bool = False,
    quiet: bool = False,
) -> tuple[ReportStats, list[str], str]:
    api = GitHubAPI(token)
    if not api.token and max_commits > 30:
        max_commits = 30
        if not quiet:
            print("  ! 未设置 GITHUB_TOKEN，最多拉取 30 条提交。", file=sys.stderr)

    try:
        user = api.get(f"/users/{urllib.parse.quote(username)}")
        if not user:
            raise RuntimeError(f"找不到 GitHub 用户: {username}")
        login = user.get("login") or username
        display_name = user.get("name") or login
        since = datetime(year, 1, 1)

        if not quiet:
            print(f"CodeYear · github.com/{login} · {year}", file=sys.stderr)
        repos = _repos(api, login, since, include_forks)
    except RuntimeError as exc:
        raise RuntimeError(f"GitHub API 错误: {exc}") from exc

    results: list[RepoResult] = []
    warnings: list[str] = []
    total = 0
    for index, repo in enumerate(repos, 1):
        if total >= max_commits:
            warnings.append(f"已达到 --max-commits 上限（{max_commits}）")
            break
        full = repo["full_name"]
        if not quiet:
            print(f"[{index}/{len(repos)}] {full}", file=sys.stderr)
        try:
            commits = _commits(api, repo, login, year, max_commits - total, quiet)
        except RuntimeError as exc:
            warnings.append(str(exc))
            break
        if not commits:
            continue
        total += len(commits)
        try:
            repo_total = _total_commits(api, full, login)
        except RuntimeError as exc:
            warnings.append(str(exc))
            repo_total = 0
        results.append(RepoResult(
            path=Path(full),
            name=full,
            commits=commits,
            remote=repo.get("html_url"),
            readme_line=repo.get("description") or "",
            root=full,
            root_dt=_dt(repo.get("created_at")),
            total_commits=repo_total or len(commits),
            tags_in_year=0,
        ))

    if not results:
        raise RuntimeError(f"{login} 在 {year} 年没有找到公开提交。")

    stats = build_stats(
        year=year,
        root=f"https://github.com/{login}",
        repos=results,
        warnings=warnings,
        identity=(login, display_name),
    )
    if stats.commit_count == 0:
        raise RuntimeError(f"{login} 在 {year} 年没有找到公开提交。")
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
) -> int:
    try:
        stats, warnings, login = fetch_stats(
            username, year, token=token, max_commits=max_commits,
            include_forks=include_forks, quiet=quiet,
        )
        if (
            fallback_previous
            and not stats.commit_count
            and year == datetime.now().year
        ):
            previous, prev_warnings, login = fetch_stats(
                username, year - 1, token=token, max_commits=max_commits,
                include_forks=include_forks, quiet=quiet,
            )
            if previous.commit_count:
                stats, warnings = previous, prev_warnings
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
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

    if profile_repo:
        cards = {label: path for label, path in written}
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
                    print(f"\nProfile  {state} · {repo}")
                else:
                    print(f"\nProfile  卡片已是最新 · {repo}")
            except Exception as exc:  # pragma: no cover - user environment
                print(f"  ! 更新 Profile 失败: {exc}", file=sys.stderr)
                return 1

    print()
    print(f"CodeYear {year}  ·  {stats.persona.title}")
    print("-" * 46)
    print(f"账号      github.com/{login}")
    print(f"仓库      {stats.repo_count}")
    print(f"提交      {fmt_int(stats.commit_count)}")
    print(f"代码行    {fmt_human(stats.lines_changed)}")
    print(f"活跃      {stats.active_days} 天 · 涉及 {stats.file_count} 个文件")
    print(f"输出      {out.resolve()}")
    print("-" * 46)
    for label, path in written:
        print(f"{label:<9}  {path.name}")
    if warnings:
        print()
        print("提示:")
        for warning in warnings:
            print(f"  - {warning}")
    if open_report:
        html = next((path for label, path in written if label == "HTML"), None)
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
