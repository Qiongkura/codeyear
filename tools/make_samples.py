"""Generate the anonymized sample report and cards used by the docs.

Run from the repository root:

    python tools/make_samples.py

The data is entirely synthetic: no real repository, commit, or identity is used.
"""

from __future__ import annotations

import random
import shutil
import sys
import tempfile
from calendar import monthrange
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from codeyear.runner import render  # noqa: E402
from codeyear.scanner import Commit, FileChange, RepoResult  # noqa: E402
from codeyear.stats import build_stats, compare_summary  # noqa: E402

DOCS = ROOT / "docs"
YEAR = 2026
PREVIOUS = 2025

REPOS = [
    "project-alpha", "project-beta", "project-gamma", "project-delta",
    "project-epsilon", "project-zeta", "project-eta", "project-theta",
    "project-iota", "project-kappa",
]
COUNTS = [180, 150, 130, 120, 110, 100, 90, 80, 65, 52]
PREV_COUNTS = [150, 130, 110, 100, 95, 85, 75, 65, 45, 35]

LANG_FILES = [
    ("src/core.py", "Python"), ("src/parser.py", "Python"),
    ("web/app.ts", "TypeScript"), ("web/theme.css", "CSS"),
    ("src/main.rs", "Rust"), ("cmd/server.go", "Go"),
    ("src/engine.cpp", "C++"), ("README.md", "Markdown"),
    ("docs/notes.md", "Markdown"), ("scripts/build.py", "Python"),
]
SUBJECTS = [
    "feat: add parser for config files",
    "fix: handle empty input",
    "docs: update setup notes",
    "refactor: split report renderer",
    "perf: cache repository metadata",
    "test: cover alias matching",
    "feat: 支持多根目录扫描",
    "fix: 修正跨年统计",
    "docs: 补充部署说明",
    "style: tidy the editor layout",
    "build: add release workflow",
    "chore: bump dependencies",
    "feat: add theme gallery",
    "fix: avoid duplicate commits",
    "docs: translate the quick start",
]
README_LINES = [
    "A tiny tool for turning git history into a readable annual report.",
    "Notes, experiments, and small utilities collected over the year.",
    "A local-first dashboard for tracking side projects.",
    "A visual playground for audio and animation ideas.",
    "Firmware experiments for a small wheeled robot.",
    "A command-line helper for batch media transfers.",
    "A reinforcement-learning snake game.",
    "A desktop-first focus timer.",
    "A personal site and portfolio.",
    "A collection of interface sketches and prototypes.",
]
MONTH_WEIGHTS_2026 = [1, 1, 2, 3, 4, 5, 7, 9, 11, 9, 8]
MONTH_WEIGHTS_2025 = [4, 4, 5, 6, 7, 8, 9, 10, 11, 9, 8, 7]
HOUR_WEIGHTS = [6, 7, 5, 3, 3, 2, 3, 2, 2, 3, 4]
HOURS = [22, 23, 0, 1, 2, 9, 10, 14, 16, 20, 21]
TODAY = datetime(2026, 11, 3, 12, 0)


def _commits(
    rng: random.Random, repo: str, count: int, year: int,
) -> list[Commit]:
    weights = MONTH_WEIGHTS_2026 if year == YEAR else MONTH_WEIGHTS_2025
    months = list(range(1, len(weights) + 1))
    files = LANG_FILES
    commits: list[Commit] = []
    for _ in range(count):
        month = rng.choices(months, weights=weights, k=1)[0]
        day = rng.randint(1, monthrange(year, month)[1])
        if year == YEAR and (month, day) > (TODAY.month, TODAY.day):
            month, day = TODAY.month, TODAY.day
        hour = rng.choices(HOURS, weights=HOUR_WEIGHTS, k=1)[0]
        dt = datetime(year, month, day, hour, rng.randint(0, 59))
        added = rng.randint(1, 220)
        deleted = rng.randint(0, 80)
        if rng.random() < 0.012:
            added = rng.randint(4500, 9000)
            deleted = rng.randint(500, 2500)
        file_count = rng.randint(1, 6)
        changes = []
        for path, lang in rng.sample(files, k=min(file_count, len(files))):
            changes.append(FileChange(
                path=path, lang=lang,
                lines=max(1, added // file_count + rng.randint(-8, 8)),
            ))
        commits.append(Commit(
            repo=repo,
            hash=f"{rng.getrandbits(160):040x}",
            dt=dt,
            subject=rng.choice(SUBJECTS),
            added=added,
            deleted=deleted,
            files=file_count,
            author_email="demo@example.com",
            author_name="Demo User",
            changes=changes,
        ))
    return commits


def _repo(
    rng: random.Random, name: str, count: int, year: int, index: int,
) -> RepoResult:
    return RepoResult(
        path=Path(name),
        name=name,
        commits=_commits(rng, name, count, year),
        remote=f"https://github.com/demo-user/{name}",
        readme_line=README_LINES[index % len(README_LINES)],
        root=name,
        root_dt=datetime(2024, 1, 1),
        total_commits=count + rng.randint(40, 260),
        tags_in_year=rng.randint(1, 4),
    )


def _strip_trailing(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    path.write_text(
        "\n".join(line.rstrip() for line in text.splitlines()) + "\n",
        encoding="utf-8",
    )


def _fix_lang_link(path: Path, old: str, new: str) -> None:
    """Point the sample report's language switch at the renamed docs file."""
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace(old, new), encoding="utf-8")


def main() -> None:
    rng = random.Random(20261103)
    current_repos = [
        _repo(rng, name, count, YEAR, index)
        for index, (name, count) in enumerate(zip(REPOS, COUNTS))
    ]
    previous_repos = [
        _repo(rng, name, count, PREVIOUS, index)
        for index, (name, count) in enumerate(zip(REPOS, PREV_COUNTS))
    ]

    stats = build_stats(
        year=YEAR,
        root="/home/demo/code",
        repos=current_repos,
        identity=("demo@example.com", "Demo User"),
    )
    previous = build_stats(
        year=PREVIOUS,
        root="/home/demo/code",
        repos=previous_repos,
        identity=("demo@example.com", "Demo User"),
    )
    stats.previous = compare_summary(stats, previous)

    names = {
        "HTML": "sample-report.html",
        "HTML-EN": "sample-report-en.html",
        "CARD": "sample-card.svg",
        "CARD-DARK": "sample-card-dark.svg",
        "CARD-EN": "sample-card-en.svg",
        "CARD-DARK-EN": "sample-card-en-dark.svg",
        "PNG": "sample.png",
        "LONG": "sample-long.png",
    }
    with tempfile.TemporaryDirectory() as tmp:
        written = render(
            stats, Path(tmp), formats={"html", "card", "png", "long"},
        )
        for label, path in written:
            if label in names:
                target = DOCS / names[label]
                shutil.copy2(path, target)
                if label.startswith("HTML"):
                    _strip_trailing(target)
                    if target.name == "sample-report.html":
                        _fix_lang_link(
                            target, f"codeyear-{YEAR}-en.html",
                            "sample-report-en.html",
                        )
                    elif target.name == "sample-report-en.html":
                        _fix_lang_link(
                            target, f"codeyear-{YEAR}.html",
                            "sample-report.html",
                        )

    print(f"wrote {len(names)} files to {DOCS}")


if __name__ == "__main__":
    main()
