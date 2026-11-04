from datetime import datetime
from pathlib import Path

from codeyear.card import THEMES, build_svg
from codeyear.html_report import build_html
from codeyear.languages import language_for
from codeyear.scanner import Commit, FileChange, RepoResult
from codeyear.stats import build_stats, compare_summary


def _stats():
    commits = [
        Commit(
            repo="demo", hash="a" * 40, dt=datetime(2026, 1, 2, 10, 0),
            subject="feat: add parser", added=120, deleted=12, files=2,
            author_email="me@example.com", author_name="Me",
            changes=[FileChange("src/parser.py", "Python", 120),
                     FileChange("README.md", "Markdown", 12)],
        ),
        Commit(
            repo="demo", hash="b" * 40, dt=datetime(2026, 1, 5, 23, 0),
            subject="fix: handle empty input", added=8, deleted=3, files=1,
            author_email="me@example.com", author_name="Me",
            changes=[FileChange("src/parser.py", "Python", 11)],
        ),
    ]
    repo = RepoResult(
        path=Path("demo"), name="demo", commits=commits,
        remote="https://example.com/demo", readme_line="Demo project",
        root="root-demo", root_dt=datetime(2025, 6, 1),
        total_commits=len(commits), tags_in_year=1,
    )
    return build_stats(
        year=2026, root="/tmp/demo", repos=[repo],
        identity=("me@example.com", "Me"),
    )


def test_stats_aggregate():
    stats = _stats()
    assert stats.commit_count == 2
    assert stats.repo_count == 1
    assert stats.insertions == 128
    assert stats.deletions == 15
    assert stats.active_days == 2
    assert stats.languages[0][0] == "Python"


def test_card_themes():
    stats = _stats()
    for theme in THEMES:
        svg = build_svg(stats, theme=theme)
        assert svg.startswith("<svg")
    assert build_svg(stats).startswith("<svg")


def test_report_contains_search_and_data_analysis():
    html = build_html(_stats())
    assert "数据分析" in html
    assert 'id="repo-search"' in html
    assert "repo-search" in html
    assert "month-col" in html
    assert "bottom:calc(" in html


def test_compare_summary():
    from dataclasses import replace

    current = _stats()
    previous = replace(
        current, year=2025, commit_count=1, lines_changed=50,
        active_days=1, repo_count=1, longest_streak=1,
    )
    summary = compare_summary(current, previous)
    assert summary["year"] == 2025
    assert summary["commits"] == 1
    assert summary["lines"] > 0
    assert summary["previous_commits"] == 1
    assert summary["previous_lines"] == 50
    assert summary["previous_monthly"] == previous.monthly
    assert summary["active_days_pct"] == 1.0


def test_compare_panel_renders():
    from dataclasses import replace

    stats = _stats()
    previous = replace(
        stats, year=2025, commit_count=1, lines_changed=50,
        active_days=1, repo_count=1, longest_streak=1,
        weekend_share=1.0,
    )
    stats.previous = compare_summary(stats, previous)
    html = build_html(stats)
    assert "同比去年" in html
    assert "2025 vs 2026" in html
    assert "cmp-row" in html
    assert "cmp-cols" in html
    assert "cmp-bar prev" in html
    assert "个百分点" in html
    assert "今年峰值" in html


def test_compare_panel_without_previous_commits():
    from dataclasses import replace

    stats = _stats()
    previous = replace(
        stats, year=2025, commit_count=0, lines_changed=0,
        active_days=0, repo_count=0, longest_streak=0,
    )
    stats.previous = compare_summary(stats, previous)
    html = build_html(stats)
    assert "以下按 0 计算" in html
    assert "--alias" in html
    assert "cmp-row" in html
    assert "cmp-cols" in html


def test_compare_line_without_previous_commits():
    from dataclasses import replace
    from codeyear.report_theme import decorate

    stats = _stats()
    previous = replace(
        stats, year=2025, commit_count=0, lines_changed=0,
        active_days=0, repo_count=0, longest_streak=0,
    )
    stats.previous = compare_summary(stats, previous)
    html = decorate(build_html(stats), stats)
    assert "同比 2025（去年 0 次提交）" in html
    assert "提交 +2" in html


def test_english_report_translates_session_panel():
    from codeyear.report_theme import decorate, to_english

    stats = _stats()
    en = to_english(decorate(build_html(stats), stats), stats)
    assert "Coding rhythm" in en
    assert "工作节奏" not in en
    assert "coding sessions" in en
    assert "Search repos / languages / descriptions" in en


def test_profile_update_versions_and_rewrites_readme(tmp_path):
    import subprocess

    from codeyear.profile import update_profile

    repo = tmp_path / "profile"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    readme = repo / "README.md"
    readme.write_text(
        '# Me\n\n<picture>\n'
        '  <source media="(prefers-color-scheme: dark)" '
        'srcset="./codeyear-2025-card-dark.svg">\n'
        '  <img src="./codeyear-2025-card.svg" width="640" '
        'alt="CodeYear 2025">\n'
        "</picture>\n",
        encoding="utf-8",
    )
    (repo / "codeyear-2025-card.svg").write_text("<svg id='old'/>", encoding="utf-8")
    (repo / "codeyear-2025-card-dark.svg").write_text(
        "<svg id='old-dark'/>", encoding="utf-8"
    )
    light = tmp_path / "light.svg"
    dark = tmp_path / "dark.svg"
    light.write_text("<svg id='l1'/>", encoding="utf-8")
    dark.write_text("<svg id='d1'/>", encoding="utf-8")

    _, changed, pushed = update_profile(repo, 2026, light, dark)
    assert changed and not pushed
    text = readme.read_text(encoding="utf-8")
    assert "codeyear-2026-card-v1.svg" in text
    assert "codeyear-2026-card-v1-dark.svg" in text
    assert "codeyear-2025-card.svg" not in text
    assert 'alt="CodeYear 2026"' in text
    assert not (repo / "codeyear-2025-card.svg").exists()
    assert not (repo / "codeyear-2025-card-dark.svg").exists()

    _, changed_again, _ = update_profile(repo, 2026, light, dark)
    assert not changed_again
    assert not (repo / "codeyear-2026-card-v2.svg").exists()

    light.write_text("<svg id='l2'/>", encoding="utf-8")
    dark.write_text("<svg id='d2'/>", encoding="utf-8")
    _, changed_third, _ = update_profile(repo, 2026, light, dark)
    assert changed_third
    text = readme.read_text(encoding="utf-8")
    assert "codeyear-2026-card-v2.svg" in text
    assert "codeyear-2026-card-v2-dark.svg" in text
    assert "codeyear-2026-card-v1.svg" not in text
    assert not (repo / "codeyear-2026-card-v1.svg").exists()
    assert (repo / "codeyear-2026-card-v2.svg").exists()


def test_profile_update_inserts_missing_readme_block(tmp_path):
    import subprocess

    from codeyear.profile import update_profile

    repo = tmp_path / "profile"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    light = tmp_path / "light.svg"
    dark = tmp_path / "dark.svg"
    light.write_text("<svg/>", encoding="utf-8")
    dark.write_text("<svg/>", encoding="utf-8")

    update_profile(repo, 2026, light, dark)
    text = (repo / "README.md").read_text(encoding="utf-8")
    assert "<picture>" in text
    assert "codeyear-2026-card-v1.svg" in text
    assert "codeyear-2026-card-v1-dark.svg" in text


def test_identity_alias():
    old = Commit(
        repo="demo", hash="c" * 40, dt=datetime(2026, 2, 1, 12, 0),
        subject="feat: old email", added=3, deleted=1, files=1,
        author_email="old@example.com", author_name="Old Name",
        changes=[FileChange("src/old.py", "Python", 4)],
    )
    repo = RepoResult(
        path=Path("demo"), name="demo", commits=[old], root="root-old",
        root_dt=datetime(2025, 1, 1), total_commits=1,
    )
    without = build_stats(
        year=2026, root="/tmp", repos=[repo],
        identity=("me@example.com", "Me"),
    )
    assert without.commit_count == 0
    with_alias = build_stats(
        year=2026, root="/tmp", repos=[repo],
        identity=("me@example.com", "Me"),
        aliases=["old@example.com"],
    )
    assert with_alias.commit_count == 1


def test_language_mapping():
    assert language_for("src/main.py") == "Python"
    assert language_for("package-lock.json") is None


def test_github_card_only_updates_profile(tmp_path, monkeypatch):
    import subprocess

    from codeyear import github_public

    stats = _stats()
    monkeypatch.setattr(
        github_public, "fetch_stats",
        lambda *args, **kwargs: (stats, [], "Me"),
    )

    def fake_render(stats, out_dir, formats=None, card_theme="paper"):
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        assert formats == {"card"}
        light = out / f"codeyear-{stats.year}-card.svg"
        dark = out / f"codeyear-{stats.year}-card-dark.svg"
        light.write_text("<svg id='light'/>", encoding="utf-8")
        dark.write_text("<svg id='dark'/>", encoding="utf-8")
        return [("CARD", light), ("CARD-DARK", dark)]

    monkeypatch.setattr(github_public, "render", fake_render)

    repo = tmp_path / "profile"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)

    out = tmp_path / "out"
    code = github_public.run(
        "me", 2026, out, card_only=True, profile_repo=repo, quiet=True,
    )
    assert code == 0
    text = (repo / "README.md").read_text(encoding="utf-8")
    assert "codeyear-2026-card-v1.svg" in text
    assert "codeyear-2026-card-v1-dark.svg" in text
    assert (out / "codeyear-2026-embed.md").exists()


def test_github_fallback_to_previous_year(tmp_path, monkeypatch):
    import subprocess
    from dataclasses import replace
    from datetime import datetime

    from codeyear import github_public

    current = datetime.now().year
    base = _stats()
    empty = replace(
        base, year=current, commit_count=0, lines_changed=0,
        active_days=0, repo_count=1,
    )
    older = replace(
        base, year=current - 1, commit_count=3, lines_changed=100,
        active_days=2, repo_count=1,
    )
    calls = []

    def fake_fetch(username, year, **kwargs):
        calls.append(year)
        return (empty if year == current else older), [], "Me"

    monkeypatch.setattr(github_public, "fetch_stats", fake_fetch)

    def fake_render(stats, out_dir, formats=None, card_theme="paper"):
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        light = out / f"codeyear-{stats.year}-card.svg"
        dark = out / f"codeyear-{stats.year}-card-dark.svg"
        light.write_text("<svg id='light'/>", encoding="utf-8")
        dark.write_text("<svg id='dark'/>", encoding="utf-8")
        return [("CARD", light), ("CARD-DARK", dark)]

    monkeypatch.setattr(github_public, "render", fake_render)

    repo = tmp_path / "profile"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)

    code = github_public.run(
        "me", current, tmp_path / "out", card_only=True,
        profile_repo=repo, fallback_previous=True, quiet=True,
    )
    assert code == 0
    assert calls == [current, current - 1]
    text = (repo / "README.md").read_text(encoding="utf-8")
    assert f"codeyear-{current - 1}-card-v1.svg" in text


def test_profile_push_stages_old_version_deletions(tmp_path):
    import subprocess

    from codeyear.profile import update_profile

    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)

    repo = tmp_path / "profile"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "t@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "T"], cwd=repo, check=True)
    subprocess.run(
        ["git", "remote", "add", "origin", str(remote)], cwd=repo, check=True
    )

    (repo / "README.md").write_text(
        '<img src="./codeyear-2026-card-v1.svg" alt="CodeYear 2026">\n',
        encoding="utf-8",
    )
    (repo / "codeyear-2026-card-v1.svg").write_text(
        "<svg id='old'/>", encoding="utf-8"
    )
    (repo / "codeyear-2026-card-v1-dark.svg").write_text(
        "<svg id='old-dark'/>", encoding="utf-8"
    )
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-qm", "init"], cwd=repo, check=True)
    subprocess.run(
        ["git", "push", "-q", "-u", "origin", "HEAD"], cwd=repo, check=True
    )

    light = tmp_path / "light.svg"
    dark = tmp_path / "dark.svg"
    light.write_text("<svg id='new'/>", encoding="utf-8")
    dark.write_text("<svg id='new-dark'/>", encoding="utf-8")

    _, changed, pushed = update_profile(repo, 2026, light, dark, push=True)
    assert changed and pushed

    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo,
        capture_output=True, text=True, check=True,
    )
    assert status.stdout.strip() == ""

    tree = subprocess.run(
        ["git", "--git-dir", str(remote), "ls-tree", "-r", "--name-only", "HEAD"],
        capture_output=True, text=True, check=True,
    )
    names = tree.stdout.split()
    assert "codeyear-2026-card-v2.svg" in names
    assert "codeyear-2026-card-v1.svg" not in names


def test_profile_update_keeps_card_subdirectory(tmp_path):
    import subprocess

    from codeyear.profile import update_profile

    repo = tmp_path / "profile"
    (repo / "assets").mkdir(parents=True)
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    readme = repo / "README.md"
    readme.write_text(
        '<picture>\n'
        '  <source media="(prefers-color-scheme: dark)" '
        'srcset="./assets/codeyear-2025-card-dark.svg">\n'
        '  <img src="./assets/codeyear-2025-card.svg" width="640" '
        'alt="CodeYear 2025">\n'
        "</picture>\n",
        encoding="utf-8",
    )
    light = tmp_path / "light.svg"
    dark = tmp_path / "dark.svg"
    light.write_text("<svg id='new'/>", encoding="utf-8")
    dark.write_text("<svg id='new-dark'/>", encoding="utf-8")

    update_profile(repo, 2026, light, dark)
    text = readme.read_text(encoding="utf-8")
    assert "./assets/codeyear-2026-card-v1.svg" in text
    assert "./assets/codeyear-2026-card-v1-dark.svg" in text
    assert (repo / "assets" / "codeyear-2026-card-v1.svg").exists()
    assert (repo / "assets" / "codeyear-2026-card-v1-dark.svg").exists()
    assert not (repo / "codeyear-2026-card-v1.svg").exists()


def test_public_mode_skips_merge_commits():
    from codeyear.github_public import _commits

    class FakeAPI:
        remaining = 100

        def get(self, path, params=None):
            if path.endswith("/commits"):
                return [{"sha": "a"}, {"sha": "b"}]
            if path.endswith("/commits/a"):
                return {
                    "commit": {
                        "author": {"date": "2026-01-02T10:00:00Z"},
                        "message": "feat: keep",
                    },
                    "stats": {"additions": 1, "deletions": 0},
                    "files": [],
                    "parents": [{}],
                }
            return {
                "commit": {
                    "author": {"date": "2026-01-03T10:00:00Z"},
                    "message": "Merge branch 'main'",
                },
                "stats": {"additions": 0, "deletions": 0},
                "files": [],
                "parents": [{}, {}],
            }

    commits = _commits(
        FakeAPI(), {"full_name": "me/demo"}, "me", 2026, 10, True,
    )
    assert [commit.hash for commit in commits] == ["a"]


def test_server_cache_is_bounded(monkeypatch):
    from codeyear import server

    monkeypatch.setattr(
        server, "fetch_stats", lambda *args, **kwargs: (object(), [], "me")
    )
    server.CACHE.clear()
    for index in range(server.CACHE_MAX + 20):
        server._cached_stats(f"user{index}", 2026, None, 10)
    assert len(server.CACHE) <= server.CACHE_MAX


def test_server_rate_limit():
    from codeyear import server

    server.RATE.clear()
    assert all(server._allow("1.2.3.4") for _ in range(server.RATE_LIMIT))
    assert not server._allow("1.2.3.4")
    assert server._allow("5.6.7.8")


def test_scan_fallback_previous_year(tmp_path):
    import os
    import subprocess
    import sys
    from datetime import date

    current = date.today().year
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "me@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Me"], cwd=repo, check=True)
    (repo / "a.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    env = dict(
        os.environ,
        GIT_AUTHOR_DATE=f"{current - 1}-06-01T12:00:00",
        GIT_COMMITTER_DATE=f"{current - 1}-06-01T12:00:00",
    )
    subprocess.run(
        ["git", "commit", "-qm", "feat: old"], cwd=repo,
        check=True, env=env,
    )

    project = Path(__file__).resolve().parents[1]
    out = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable, "-m", "codeyear", "scan", str(repo),
            "--year", str(current), "--fallback-previous", "--all-authors",
            "--out", str(out), "--no-html", "--no-png", "--no-long",
            "--no-card", "--quiet",
        ],
        cwd=project, capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr
    assert (out / f"codeyear-{current - 1}.json").exists()


def test_scan_profile_failure_returns_nonzero(tmp_path):
    import os
    import subprocess
    import sys
    from datetime import date

    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "me@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Me"], cwd=repo, check=True)
    (repo / "a.txt").write_text("x", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    env = dict(
        os.environ,
        GIT_AUTHOR_DATE=f"{date.today().year}-06-01T12:00:00",
        GIT_COMMITTER_DATE=f"{date.today().year}-06-01T12:00:00",
    )
    subprocess.run(
        ["git", "commit", "-qm", "feat: current"], cwd=repo,
        check=True, env=env,
    )

    not_a_repo = tmp_path / "not-a-repo"
    not_a_repo.mkdir()
    project = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable, "-m", "codeyear", "scan", str(repo),
            "--year", str(date.today().year), "--all-authors",
            "--out", str(tmp_path / "out"), "--profile-repo", str(not_a_repo),
            "--no-html", "--no-png", "--no-long", "--quiet",
        ],
        cwd=project, capture_output=True, text=True,
    )
    assert result.returncode == 1


def test_public_mode_report_labels():
    from dataclasses import replace

    from codeyear.report_theme import decorate, to_english

    public = replace(_stats(), root="https://github.com/me")
    html = build_html(public)
    assert "PUBLIC DATA" in html
    assert "公开 GitHub 数据" in html
    assert "不读取私有仓库" in html
    assert "LOCAL ONLY" not in html

    local = build_html(_stats())
    assert "LOCAL ONLY" in local
    assert "代码从未离开这台电脑" in local

    decorated = decorate(html, public)
    assert "数据来源：https://github.com/me" in decorated
    en = to_english(decorated, public)
    assert "Source: https://github.com/me" in en
    assert "Generated from public GitHub data" in en
    assert "no local code was read or uploaded" in en


def test_english_report_has_no_untranslated_ui():
    import re

    from codeyear.report_theme import decorate, to_english

    stats = _stats()
    en = to_english(decorate(build_html(stats), stats), stats)
    en = re.sub(r"<(style|script)\b.*?</\1>", "", en, flags=re.S | re.I)
    chinese = set(re.findall(r"[\u4e00-\u9fff]+", en))
    # "中文" is the intentional link back to the Chinese edition.
    assert chinese <= {"中文"}


def test_compare_percentages_and_rounded_points():
    from dataclasses import replace

    stats = _stats()
    previous = replace(
        stats, year=2025, commit_count=1, lines_changed=50,
        active_days=1, repo_count=1, longest_streak=1,
        insertions=64, deletions=30, avg_subject_len=10,
        weekend_share=0.58, night_share=0.58,
    )
    stats = replace(stats, weekend_share=0.59, night_share=0.59)
    stats.previous = compare_summary(stats, previous)
    summary = stats.previous
    assert summary["insertions_pct"] == 1.0
    assert summary["deletions_pct"] == -0.5
    assert summary["repos_pct"] == 0.0

    html = build_html(stats)
    assert "+64 (+100%)" in html
    assert "-15 (-50%)" in html
    assert "0 (0%)" in html
    assert "+1 个百分点" in html
    assert "+0 个百分点" not in html
