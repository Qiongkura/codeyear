# CodeYear · A Local-First Coding Yearbook

**English** | [简体中文](README.md)

> Scan the git repositories on your own machine and turn them into a yearbook that belongs to you:
> a paper-archive HTML report, a 2400×3200 poster, a 2400×5330 long image, and a theme-aware
> GitHub profile card. Local git only — no sign-in, no upload.

![CodeYear report preview](docs/report-preview.png)

**Sample report**: [docs/sample-report.html](docs/sample-report.html) — generated from a real machine; open it directly in a browser.

## What it is

CodeYear is a year-in-review for developers. Official Wrapped-style reports usually cover only public data and require authorization, while most of our code lives in private repositories, company intranets, or Gitee. CodeYear reads `.git` on your machine, so private projects, offline environments, and work laptops all work.

By default it counts only commits authored by you (matching git `user.name` / `user.email`) and merges copies of the same project (`work/`, `backup/`, forks) so nothing is double-counted.

## What's in the report

**Yearly records**
- Busiest day/week, longest streak, longest gap, largest single commit, longest commit message
- Time and repository of the first and last commit

**Repository profiles** (top 3 by commits)
- Commits, line changes, main languages, first → latest commit
- Most-edited file, three recent real commits
- Description taken from the first line of the repository README

**Full repository index**
- One-line README summary, stack, own code, latest commit, activity status
- Filter by main language; repositories without a README are marked honestly

**Numbers**
- Monthly rhythm, 7×24 commit clock, full-year heatmap
- Code composition by lines, language breakdown, **quarterly language shifts**
- Commit-size distribution, commit types, keywords, **message-length distribution**
- Add/delete ratio (including the repo with the most deletions), **coding sessions** (commits within 2 hours count as one)
- Repository lifecycle Gantt chart, **repo graveyard** (untouched for 30 days)
- Most-edited files (full paths)
- Local repository archaeology: all-time commits, first commit (code age), repositories started this year, version tags (repository scope, shown separately from your personal yearly numbers)

**Design**
- Paper archive: warm paper, ink, vermilion accent, large serif headings + monospaced data, square corners, hairlines
- Motion: scroll progress, staggered reveals, count-up numbers, live commit ticker, paper-style tooltips
- Vanilla JS only; respects `prefers-reduced-motion`
- System fonts only (Georgia / Songti / SimSun + Consolas); no external font requests
- GitHub card: 640×1254 poster layout, transparent background, light/dark variants, hierarchy from type, hairlines, and one terracotta accent
- Eight plain-language insights: main project, coding hours, commit size, session length, add/delete ratio, busiest month, focus spread, commit-message style

## Quick start

Requires Python 3.9+, Git, and Pillow:

```bash
pip install -r requirements.txt

# Run from the project root (next to codeyear/)
python -m codeyear scan I:\projects --year 2026 --open
```

Or install it as a command:

```bash
pip install -e .
codeyear scan I:\projects --year 2026 --open
```

Outputs go to `./codeyear-output/` by default:

```text
codeyear-2026.html          paper-archive report; open in a browser
codeyear-2026.png           2400×3200 poster (2× render)
codeyear-2026-long.png      2400×5330 full-length image
codeyear-2026-card.svg      640×1254 GitHub profile card (transparent, light)
codeyear-2026-card-dark.svg 640×1254 dark variant (transparent)
codeyear-2026.json          raw statistics for further processing
```

Poster sample (same data):

<img src="docs/sample.png" width="420" alt="CodeYear poster sample">

Full-length sample: [docs/sample-long.png](docs/sample-long.png)

## Put it on your GitHub profile

The scan also produces a light and a dark card, both with transparent backgrounds. Commit both files to your profile repository (the repository named after your username, e.g. `Qiongkura/Qiongkura`) and use `<picture>` in its README to switch by theme:

```md
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./codeyear-2026-card-dark.svg">
  <img src="./codeyear-2026-card.svg" width="640" alt="CodeYear 2026">
</picture>
```

With `<picture>`, GitHub picks the right version for the viewer's theme. If you only use `<img>`, dark mode will show the light card. The card is a static file: re-run the scan and commit to update it.

> GitHub caches README images through its image proxy, so an updated SVG with the same name may still show the old version. To force a refresh, rename the file with a version suffix (e.g. `codeyear-2026-card-v2.svg`) and update the README, or append a query string (e.g. `?v=2`).

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/sample-card-dark.svg">
  <img src="docs/sample-card.svg" width="640" alt="CodeYear GitHub profile card sample">
</picture>

## Only your own commits

- Reads your global `git config user.name` / `user.email` and keeps only commits authored by you.
- To count everyone: add `--all-authors`.
- To pick an author explicitly: add `--author "you@example.com"`.
- Copies of the same project (same `remote` or same first commit) keep only the copy with the most commits.
- "All-time commits" and "first commit" use repository scope: every local repository after deduplication, without author filtering. Yearly commit counts still include only your own commits.
- Commits made with another email/name may be filtered out; use `--author` or `--all-authors` to override.

## Common options

| Option | Description |
| --- | --- |
| `--year 2026` | Year to report; defaults to the current year |
| `--out ./out` | Output directory |
| `--author "you@example.com"` | Only count the matching git author |
| `--all-authors` | Count every author (default: only you) |
| `--max-depth 6` | Maximum directory depth to scan |
| `--timeout 300` | Per-repository timeout in seconds |
| `--no-png` / `--no-html` | Skip one of the outputs |
| `--no-long` | Skip the full-length image (generated by default) |
| `--no-card` | Skip the GitHub profile card |
| `--open` | Open the report when done |
| `--quiet` | Suppress scan progress |

Examples:

```bash
# One repository only
codeyear scan . --year 2026

# Multiple repositories with an explicit author
codeyear scan D:\code --year 2026 --author "you@example.com"

# Include teammates' commits
codeyear scan D:\code --year 2026 --all-authors
```

## Privacy

- Everything runs locally. **There are no network requests.**
- Reads only `git log`, `git tag`, the first line of each repository README, and `git remote`; no other workspace files.
- Output files are ignored by `.gitignore` by default.
- The report header and footer say `LOCAL ONLY · no data uploaded`.
- On git's `dubious ownership` error (common with copied repositories), it retries with `safe.directory` for that repository only; your global git config is never changed.

## Known limitations

- Merge commits are excluded (`--no-merges`).
- Uses author date (`%ad`); in cross-timezone teams, the committer's local time wins.
- Binaries, images, lockfiles, and build artifacts are excluded from language/file statistics.
- A commit that appears in multiple repositories is counted once.
- "Own code" counts non-empty lines and excludes third-party libraries, generated projects, and model directories; the report's "About this report" section states the exact scope for each project.

## How it works

For each repository:

```text
git log --since=2026-01-01 --until=2027-01-01 \
  --pretty=format:%H%x1f%ad%x1f%ae%x1f%an%x1f%s \
  --numstat --no-renames --no-merges
```

Then:

1. Filter by author identity and keep only your commits.
2. Deduplicate by commit hash and merge copies by project lineage.
3. Aggregate by day, hour, weekday, quarter, language, and file.
4. Render the paper report, poster, long image, and profile card.

Languages are mapped from file extensions. Lockfiles, build artifacts, images, and binaries are filtered out so `package-lock.json` does not win "most-edited file".

## Roadmap

- [x] Paper-archive HTML report with motion
- [x] Only your commits (`--all-authors` to opt out)
- [x] Merge project copies by lineage
- [x] Yearly records / 7×24 clock / coding sessions / quarterly languages / repo graveyard
- [x] Paper-themed PNG poster
- [x] Theme-aware GitHub profile card (light/dark, transparent)
- [ ] Year-over-year comparison (2025 vs 2026)
- [ ] File-level deletions (most-deleted files)
- [ ] PyInstaller exe / desktop shell
- [x] English README
- [ ] Public GitHub / Gitee mode (username in, report out)

## Development

```bash
# Generate a report locally
python -m codeyear scan I:\projects --year 2026 --out ./out

# Syntax check
python -m compileall -q codeyear
```

Code layout:

```text
codeyear/
  scanner.py      find repositories + parse git log + README first line
  stats.py        aggregation / identity filtering / copy merging / metrics
  keywords.py     commit keyword extraction
  languages.py    extension → language mapping and filters
  html_report.py  paper-archive HTML report (inline CSS/JS)
  poster.py       PNG poster (Pillow)
  personas.py     coding persona
  cli.py          command line
```

## License

MIT
