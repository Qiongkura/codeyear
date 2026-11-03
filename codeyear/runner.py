"""Shared scan and render pipeline for the wizard and the desktop GUI."""

from __future__ import annotations

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .card import render as render_card
from .html_report import render as render_html, render_en as render_html_en
from .poster import render as render_poster, render_long
from .scanner import find_repos, scan_repo
from .stats import ReportStats, build_stats, compare_summary

Progress = Callable[[int, int, str], None]
ALL_FORMATS = {"json", "html", "png", "long", "card"}
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


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


def discover(roots: list[Path], depth: int = 6) -> list[tuple[Path, Path]]:
    seen: set[Path] = set()
    found: list[tuple[Path, Path]] = []
    for root in roots:
        for repo in find_repos(root, max_depth=depth):
            resolved = repo.resolve()
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
    author: str | None = None,
    timeout: int = 300,
    jobs: int = 1,
    progress: Progress | None = None,
    compare: bool = False,
) -> tuple[ReportStats, list[str]]:
    labels = _root_labels(roots)
    results: list[RepoResult] = []
    warnings: list[str] = []
    total = len(repos)

    def prepare(repo: Path, root: Path) -> RepoResult:
        result = scan_repo(repo, root, year, author=author, timeout=timeout)
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

    stats = build_stats(
        year=year,
        root=" + ".join(str(root) for root in roots),
        repos=results,
        warnings=warnings,
        identity=identity,
    )
    if compare:
        previous, _ = scan(
            repos, roots, year - 1, identity,
            author=author, timeout=timeout, jobs=jobs,
            progress=None, compare=False,
        )
        stats.previous = compare_summary(stats, previous)
    return stats, warnings


def render(
    stats: ReportStats,
    out_dir: Path,
    formats: set[str] | None = None,
    *,
    card_theme: str = "paper",
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
    if "long" in formats:
        written.append(("LONG", render_long(
            stats, out_dir / f"codeyear-{stats.year}-long.png")))
    if "card" in formats:
        cards = render_card(stats, out_dir / f"codeyear-{stats.year}-card.svg",
                            theme=card_theme)
        written.append(("CARD", cards[0]))
        written.append(("CARD-DARK", cards[1]))
    return written
