"""Regression tests for the v0.2.17 optimisation pass.

Covers: cheap scanning of cloned/foreign repos, lifetime-metric scoping,
generated-code filtering, rolling-window month ordering, atomic cache writes,
external-contribution discovery, and scan cancellation.
"""

import subprocess
import threading
from datetime import datetime
from pathlib import Path

from codeyear.scanner import Commit, FileChange, RepoResult, matches_identity
from codeyear.stats import build_stats, month_labels, month_slots, window_months


# --------------------------------------------------------------------------
# helpers (local copies so this module stands alone)
# --------------------------------------------------------------------------
def _git(repo, *args, env=None):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True,
        text=True, env=env,
    )


def _init_repo(repo: Path, email="me@example.com", name="Me"):
    import os

    repo.mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    _git(repo, "config", "user.email", email)
    _git(repo, "config", "user.name", name)
    return os.environ.copy()


def _commit(repo, filename, message, date, env, author=None):
    (repo / filename).write_text(message, encoding="utf-8")
    _git(repo, "add", "-A")
    stamp = dict(env, GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    if author:
        stamp.update(GIT_AUTHOR_NAME=author[0], GIT_AUTHOR_EMAIL=author[1])
    _git(repo, "commit", "-qm", message, env=stamp)


def _commit_obj(hash_, dt, repo="demo", email="me@example.com", name="Me",
                path="a.py", lang="Python", added=10, deleted=2):
    return Commit(
        repo=repo, hash=hash_, dt=dt, subject="feat: work",
        added=added, deleted=deleted, files=1,
        author_email=email, author_name=name,
        changes=[FileChange(path, lang, added + deleted, added, deleted)],
    )


# --------------------------------------------------------------------------
# 1. scanner: zero-commit early exit + foreign-repo metadata skip
# --------------------------------------------------------------------------
def test_scan_repo_skips_metadata_for_repo_without_commits(tmp_path, monkeypatch):
    from codeyear import scanner

    repo = tmp_path / "empty"
    _init_repo(repo)
    # A repo with no commits in the requested year at all.
    calls = []
    for name in ("_git_remote", "_git_root_info", "_git_total_commits",
                 "_git_tags_in_year"):
        monkeypatch.setattr(
            scanner, name,
            lambda *a, _n=name, **k: calls.append(_n) or (None, None),
        )

    result = scanner.scan_repo(repo, tmp_path, 2026)
    assert result.commits == []
    assert calls == [], "no metadata subprocess work for an empty window"


def test_scan_repo_skips_metadata_when_only_others_committed(tmp_path, monkeypatch):
    from codeyear import scanner

    repo = tmp_path / "upstream"
    env = _init_repo(repo, email="upstream@example.com", name="Upstream")
    _commit(repo, "a.py", "feat: upstream work", "2026-02-01T10:00:00", env)

    calls = []
    for name in ("_git_remote", "_git_root_info", "_git_total_commits",
                 "_git_tags_in_year"):
        monkeypatch.setattr(
            scanner, name,
            lambda *a, _n=name, **k: calls.append(_n) or (None, None),
        )

    result = scanner.scan_repo(
        repo, tmp_path, 2026, identity=("me@example.com", "Me"),
    )
    assert len(result.commits) == 1
    assert calls == [], "a clone with none of my commits costs no extra git calls"


def test_scan_repo_counts_only_my_lifetime_commits(tmp_path):
    from codeyear.scanner import scan_repo

    repo = tmp_path / "mixed"
    env = _init_repo(repo)
    _commit(repo, "a.py", "feat: mine", "2026-02-01T10:00:00", env)
    _commit(repo, "b.py", "feat: theirs", "2026-02-02T10:00:00", env,
            author=("Other Dev", "other@example.com"))
    _commit(repo, "c.py", "feat: mine again", "2026-02-03T10:00:00", env)

    everyone = scan_repo(repo, tmp_path, 2026)
    assert everyone.total_commits == 3

    mine = scan_repo(
        repo, tmp_path, 2026, identity=("me@example.com", "Me"),
    )
    assert mine.total_commits == 2, "lifetime total must not import others' work"


def test_matches_identity_is_case_insensitive_and_alias_aware():
    assert matches_identity("ME@example.com", "", ("me@example.com", "Me"))
    assert matches_identity("", "me", ("me@example.com", "Me"))
    assert matches_identity("old@x.com", "", ("me@example.com", "Me"),
                            ["old@x.com"])
    assert not matches_identity("notme@example.com", "Not Me",
                                ("me@example.com", "Me"))
    assert matches_identity("anyone@x.com", "Anyone", None)


# --------------------------------------------------------------------------
# 2. stats: lifetime metrics stay on repos that actually contributed
# --------------------------------------------------------------------------
def test_lifetime_metrics_ignore_repos_without_my_commits():
    mine = RepoResult(
        path=Path("mine"), name="mine", root="root-mine",
        root_dt=datetime(2024, 5, 1), total_commits=40, tags_in_year=2,
        commits=[_commit_obj("a" * 40, datetime(2026, 3, 1, 10, 0))],
    )
    # A vendored upstream clone: huge history, 2005 root, no commits of mine.
    upstream = RepoResult(
        path=Path("linux"), name="linux", root="root-linux",
        root_dt=datetime(2005, 4, 7), total_commits=1_000_000,
        tags_in_year=80, commits=[],
    )
    stats = build_stats(
        year=2026, root="/tmp", repos=[mine, upstream],
        identity=("me@example.com", "Me"),
    )
    assert stats.repo_count == 1
    assert stats.total_commits == 40
    assert stats.tags_in_year == 2
    assert stats.earliest_dt == datetime(2024, 5, 1)


def test_lifetime_metrics_fall_back_when_nothing_is_mine():
    """With no matching commits, lifetime numbers use the deduped repo set."""
    repo = RepoResult(
        path=Path("d"), name="d", root="r", root_dt=datetime(2020, 1, 1),
        total_commits=7, tags_in_year=1, commits=[],
    )
    stats = build_stats(
        year=2026, root="/tmp", repos=[repo],
        identity=("me@example.com", "Me"),
    )
    assert stats.total_commits == 7
    assert stats.earliest_dt == datetime(2020, 1, 1)


# --------------------------------------------------------------------------
# 3. languages: modern lockfiles and generated code are ignored
# --------------------------------------------------------------------------
def test_modern_lockfiles_and_generated_code_are_skipped():
    from codeyear.languages import language_for

    for path in (
        "uv.lock", "pdm.lock", "pixi.lock", "bun.lock", "deno.lock",
        "paket.lock", "mix.lock", "pubspec.lock", "Podfile.lock",
        "api/service.pb.go", "api/service_pb2.py", "api/service_pb2_grpc.py",
        "lib/model.g.dart", "lib/model.freezed.dart",
        "src/components/App.generated.ts", "dist/app.min.js",
        "__generated__/types.ts",
    ):
        assert language_for(path) is None, path


def test_modern_languages_are_recognised():
    from codeyear.languages import language_for

    assert language_for("schema.prisma") == "Prisma"
    assert language_for("paper.typ") == "Typst"
    assert language_for("main.gleam") == "Gleam"
    assert language_for("model.mojo") == "Mojo"
    assert language_for("infra/main.tf") == "Terraform"
    assert language_for("default.nix") == "Nix"
    assert language_for("ui/Main.qml") == "QML"
    assert language_for("player.gd") == "GDScript"
    assert language_for("CMakeLists.txt") == "CMake"
    assert language_for("src/shader.wgsl") == "Shader"


def test_handwritten_files_still_count():
    from codeyear.languages import language_for

    assert language_for("src/app.py") == "Python"
    assert language_for("src/util.ts") == "TypeScript"
    assert language_for("docs/guide.md") == "Markdown"


# --------------------------------------------------------------------------
# 4. rolling window: chronological month labels shared by every renderer
# --------------------------------------------------------------------------
def test_month_slots_always_return_twelve_bins():
    from datetime import date

    for start, end in (
        (date(2026, 1, 1), date(2026, 12, 31)),
        (date(2025, 11, 21), date(2026, 11, 20)),
        (date(2025, 6, 15), date(2026, 11, 20)),
        (date(2024, 1, 1), date(2026, 11, 20)),
    ):
        slots = month_slots(start, end)
        assert len(slots) == 12
        flat = [m for group in slots for m in group]
        assert flat == sorted(flat), "bins stay chronological"
        assert len(flat) >= 12


def test_rolling_month_labels_are_chronological_and_shared():
    from codeyear.card import build_svg
    from codeyear.html_report import build_html

    repo = RepoResult(
        path=Path("demo"), name="demo", root="r",
        root_dt=datetime(2025, 11, 1),
        commits=[
            _commit_obj("c1" * 20, datetime(2025, 12, 15, 10, 0)),
            _commit_obj("c2" * 20, datetime(2026, 1, 15, 10, 0)),
            _commit_obj("c3" * 20, datetime(2026, 3, 15, 10, 0)),
        ],
        total_commits=3,
    )
    stats = build_stats(
        year=2026, root="/tmp", repos=[repo],
        identity=("me@example.com", "Me"),
        rolling=True,
        since_dt=datetime(2025, 11, 21, 0, 0, 0),
        until_dt=datetime(2026, 11, 20, 23, 59, 59),
    )
    labels = month_labels(stats)
    # The window touches 13 calendar months; the two oldest share one bar so
    # the rest stay chronological, oldest on the left.
    assert labels == ["11·12", "01", "02", "03", "04", "05", "06", "07",
                      "08", "09", "10", "11"]
    assert len(labels) == 12
    # Commits land in the right bin instead of a "month number" bucket.
    assert stats.monthly[0] == 1, "Nov+Dec share the first bar"
    assert stats.monthly[labels.index("01")] == 1
    assert stats.monthly[labels.index("03")] == 1
    assert sum(stats.monthly) == 3

    ticks = [lbl for _, lbl in window_months(stats)]
    assert ticks == labels

    html = build_html(stats)
    assert html.count('class="month-col') == 12
    for lbl in labels:
        assert f"<span>{lbl}</span>" in html

    svg = build_svg(stats)
    assert svg.startswith("<svg")


def test_natural_year_keeps_january_to_december_labels():
    repo = RepoResult(
        path=Path("demo"), name="demo", commits=[
            _commit_obj("d" * 40, datetime(2026, 7, 4, 12, 0))
        ], total_commits=1,
    )
    stats = build_stats(
        year=2026, root="/tmp", repos=[repo],
        identity=("me@example.com", "Me"),
    )
    assert month_labels(stats) == [f"{m:02d}" for m in range(1, 13)]
    assert stats.monthly[6] == 1
    assert [q["q"] for q in stats.language_quarters] == ["Q1", "Q2", "Q3", "Q4"]


# --------------------------------------------------------------------------
# 5. GitHub public mode: atomic cache + contributed repos
# --------------------------------------------------------------------------
def test_public_cache_write_is_atomic(tmp_path, monkeypatch):
    from codeyear import github_public

    path = tmp_path / "cache" / "github-me.json"
    github_public._save_cache(path, {"repo@sha": {"commit": {}}})
    assert path.is_file()
    assert not path.with_name(path.name + ".tmp").exists()

    original = Path.write_text

    def boom(self, *args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", boom)
    # Must swallow the error and leave no temp file behind.
    github_public._save_cache(path, {"repo@sha2": {"commit": {}}})
    monkeypatch.setattr(Path, "write_text", original)

    from codeyear.github_public import _load_cache

    assert list(_load_cache(path)) == ["repo@sha"]
    assert sorted(p.name for p in path.parent.iterdir()) == [path.name]


def test_contributed_repos_excludes_owned_and_private(monkeypatch):
    from codeyear import github_public

    api = github_public.GitHubAPI(token=None)

    def fake_get(self, path, params=None):
        assert path == "/search/commits"
        return {
            "items": [
                {"repository": {
                    "full_name": "org/lib", "private": False, "fork": False,
                    "owner": {"login": "org"},
                }},
                {"repository": {
                    "full_name": "me/mine", "private": False, "fork": False,
                    "owner": {"login": "me"},
                }},
                {"repository": {
                    "full_name": "someone/secret", "private": True,
                    "fork": False, "owner": {"login": "someone"},
                }},
                {"repository": {
                    "full_name": "org/lib", "private": False, "fork": False,
                    "owner": {"login": "org"},
                }},
            ]
        }

    monkeypatch.setattr(github_public.GitHubAPI, "get", fake_get)
    found = github_public._contributed_repos(api, "me", 2026, False)
    assert [r["full_name"] for r in found] == ["org/lib"]
    assert found[0]["_contributed_only"] is True


# --------------------------------------------------------------------------
# 6. runner: default jobs and cancellation
# --------------------------------------------------------------------------
def test_default_jobs_is_bounded_and_parallel():
    from codeyear.runner import DEFAULT_JOBS

    assert 2 <= DEFAULT_JOBS <= 8


def test_runner_scan_can_be_cancelled(tmp_path):
    from codeyear.runner import discover, scan

    repos_dir = []
    for i in range(4):
        repo = tmp_path / f"repo-{i}"
        env = _init_repo(repo)
        _commit(repo, "a.py", "feat: x", "2026-02-01T10:00:00", env)
        repos_dir.append(repo)

    repos = discover([tmp_path])
    assert len(repos) == 4

    cancel = threading.Event()
    cancel.set()
    try:
        scan(repos, [tmp_path], 2026, None, cancel_event=cancel)
    except RuntimeError as exc:
        assert "取消" in str(exc)
    else:  # pragma: no cover - cancellation must be honoured
        raise AssertionError("a pre-set cancel event must abort the scan")


def test_runner_scan_without_cancel_event_completes(tmp_path):
    from codeyear.runner import discover, scan

    repo = tmp_path / "demo"
    env = _init_repo(repo)
    _commit(repo, "a.py", "feat: one", "2026-02-01T10:00:00", env)

    stats, warnings = scan(
        discover([tmp_path]), [tmp_path], 2026, None,
        cancel_event=threading.Event(),
    )
    assert stats.commit_count == 1
    assert not warnings
