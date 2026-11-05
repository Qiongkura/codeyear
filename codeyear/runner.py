"""Shared scan and render pipeline for the wizard and the desktop GUI."""

from __future__ import annotations

import contextlib
import fnmatch
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

from .card import render as render_card
from .html_report import render as render_html
from .html_report import render_en as render_html_en
from .poster import render as render_poster
from .poster import render_long
from .scanner import RepoResult, find_repos, scan_repo
from .stats import ReportStats, build_stats, compare_summary

Progress = Callable[[int, int, str], None]
ALL_FORMATS = {"json", "html", "png", "long", "card"}
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def report_path(written: list[tuple[str, Path]], *, lang: str = "zh") -> Path | None:
    """Pick the report to open: English first when the UI is English."""
    labels = ("HTML-EN", "HTML") if lang == "en" else ("HTML",)
    by_label = dict(written)
    for label in labels:
        if label in by_label:
            return by_label[label]
    return None


def detect_identity() -> tuple[str, str] | None:
    def config(key: str) -> str:
        try:
            proc = subprocess.run(
                ["git", "config", "--global", key],
                capture_output=True, text=True, encoding="utf-8",
                errors="replace", timeout=10, creationflags=_NO_WINDOW,
            )
        except (OSError, subprocess.TimeoutExpired):
            return ""
        return (proc.stdout or "").strip()

    email, name = config("user.email"), config("user.name")
    if email or name:
        return email, name
    return None


def is_excluded(
    repo_path: Path, root: Path, patterns: list[str] | None
) -> bool:
    """Return True if *repo_path* matches any exclude pattern."""
    if not patterns:
        return False
    rel = repo_path.name
    with contextlib.suppress(ValueError):
        rel_str = repo_path.relative_to(root).as_posix()
        if rel_str != ".":
            rel = rel_str
    candidates = {
        repo_path.name.lower(),
        rel.lower(),
        repo_path.as_posix().lower(),
    }
    for raw in patterns:
        for part in str(raw).split(","):
            pat = part.strip().lower()
            if not pat:
                continue
            if any(
                c == pat or fnmatch.fnmatch(c, pat) or pat in c.split("/")
                for c in candidates
            ):
                return True
    return False


def discover(
    roots: list[Path],
    depth: int = 6,
    *,
    exclude: list[str] | None = None,
) -> list[tuple[Path, Path]]:
    seen: set[Path] = set()
    found: list[tuple[Path, Path]] = []
    for root in roots:
        for repo in find_repos(root, max_depth=depth):
            resolved = repo.resolve()
            if is_excluded(resolved, root, exclude):
                continue
            if resolved not in seen:
                seen.add(resolved)
                found.append((resolved, root))
    return found


def _root_labels(roots: list[Path]) -> dict[Path, str]:
    labels: dict[Path, str] = {}
    used: set[str] = set()
    for root in roots:
        base = root.name or str(root)
        label = base
        n = 2
        while label in used:
            label = f"{base}-{n}"
            n += 1
        used.add(label)
        labels[root] = label
    return labels


def scan(
    repos: list[tuple[Path, Path]],
    roots: list[Path],
    year: int,
    identity: tuple[str, str] | None,
    *,
    aliases: list[str] | None = None,
    author: str | None = None,
    timeout: int = 300,
    jobs: int = 1,
    progress: Progress | None = None,
    compare: bool = False,
    use_mailmap: bool = True,
    all_branches: bool = False,
    rolling: bool = False,
) -> tuple[ReportStats, list[str]]:
    labels = _root_labels(roots)
    results: list[RepoResult] = []
    warnings: list[str] = []
    total = len(repos)

    until_dt: datetime | None = None
    since_dt: datetime | None = None
    scan_since_dt: datetime | None = None
    if rolling:
        until_dt = datetime.now().replace(
            hour=23, minute=59, second=59, microsecond=0
        )
        since_dt = (until_dt - timedelta(days=364)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        scan_since_dt = (
            (since_dt - timedelta(days=365)) if compare else since_dt
        )

    def prepare(repo: Path, root: Path) -> RepoResult:
        kwargs: dict = {
            "author": author,
            "timeout": timeout,
            "use_mailmap": use_mailmap,
            "all_branches": all_branches,
        }
        if rolling and scan_since_dt is not None and until_dt is not None:
            kwargs["since_dt"] = scan_since_dt
            kwargs["until_dt"] = until_dt
        elif compare:
            kwargs["since_year"] = year - 1
        result = scan_repo(repo, root, year, **kwargs)
        if len(roots) > 1:
            label = labels[root]
            old = result.name
            new = label if old == label or old in {"", "."} else f"{label}/{old}"
            result.name = new
            for commit in result.commits:
                commit.repo = new
        return result

    if jobs <= 1:
        for i, (repo, root) in enumerate(repos):
            if progress:
                progress(i, total, repo.name)
            result = prepare(repo, root)
            if result.warning:
                warnings.append(f"{result.name}: {result.warning}")
            results.append(result)
            if progress:
                progress(i + 1, total, repo.name)
    else:
        with ThreadPoolExecutor(max_workers=jobs) as pool:
            futures = {
                pool.submit(prepare, repo, root): repo
                for repo, root in repos
            }
            for done, future in enumerate(as_completed(futures), 1):
                repo = futures[future]
                try:
                    result = future.result()
                except Exception as exc:  # pragma: no cover - worker failure
                    warnings.append(f"{repo}: {exc}")
                    continue
                if result.warning:
                    warnings.append(f"{result.name}: {result.warning}")
                results.append(result)
                if progress:
                    progress(done, total, result.name)

    root_label = " + ".join(str(root) for root in roots)
    if compare:
        if rolling and since_dt is not None:
            current_results = [
                replace(r, commits=[c for c in r.commits if c.dt >= since_dt])
                for r in results
            ]
            prev_results = [
                replace(r, commits=[c for c in r.commits if c.dt < since_dt])
                for r in results
            ]
        else:
            current_results = [
                replace(r, commits=[c for c in r.commits if c.dt.year == year])
                for r in results
            ]
            prev_results = [
                replace(
                    r, commits=[c for c in r.commits if c.dt.year == year - 1]
                )
                for r in results
            ]
        stats = build_stats(
            year=year,
            root=root_label,
            repos=current_results,
            warnings=warnings,
            identity=identity,
            aliases=aliases,
        )
        previous = build_stats(
            year=year - 1,
            root=root_label,
            repos=prev_results,
            warnings=[],
            identity=identity,
            aliases=aliases,
        )
        stats.previous = compare_summary(stats, previous)
    else:
        stats = build_stats(
            year=year,
            root=root_label,
            repos=results,
            warnings=warnings,
            identity=identity,
            aliases=aliases,
        )
    return stats, warnings


def render(
    stats: ReportStats,
    out_dir: Path,
    formats: set[str] | None = None,
    *,
    card_theme: str = "paper",
    lang: str = "zh",
) -> list[tuple[str, Path]]:
    formats = formats or ALL_FORMATS
    out_dir.mkdir(parents=True, exist_ok=True)
    base = out_dir / f"codeyear-{stats.year}"
    written: list[tuple[str, Path]] = []

    if "json" in formats:
        path = base.with_suffix(".json")
        path.write_text(
            json.dumps(stats.as_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(("JSON", path))
    if "html" in formats:
        written.append(("HTML", render_html(stats, base.with_suffix(".html"))))
        written.append(("HTML-EN", render_html_en(
            stats, out_dir / f"codeyear-{stats.year}-en.html")))
    if "png" in formats:
        written.append(("PNG", render_poster(stats, base.with_suffix(".png"))))
        if lang == "en":
            written.append(("PNG-EN", render_poster(
                stats, out_dir / f"codeyear-{stats.year}-en.png", lang="en")))
    if "long" in formats:
        written.append(("LONG", render_long(
            stats, out_dir / f"codeyear-{stats.year}-long.png")))
        if lang == "en":
            written.append(("LONG-EN", render_long(
                stats, out_dir / f"codeyear-{stats.year}-en-long.png",
                lang="en")))
    if "card" in formats:
        cards = render_card(stats, out_dir / f"codeyear-{stats.year}-card.svg",
                            theme=card_theme)
        written.append(("CARD", cards[0]))
        written.append(("CARD-DARK", cards[1]))
        en_cards = render_card(
            stats, out_dir / f"codeyear-{stats.year}-card-en.svg",
            theme=card_theme, lang="en",
        )
        written.append(("CARD-EN", en_cards[0]))
        written.append(("CARD-DARK-EN", en_cards[1]))
    return written
