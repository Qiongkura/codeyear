from types import SimpleNamespace

from codeyear import github_public


def test_incomplete_public_stats_do_not_push_or_modify_profile(tmp_path, monkeypatch, capsys):
    stats = SimpleNamespace(year=2026, commit_count=1)
    monkeypatch.setattr(github_public, "fetch_stats", lambda *a, **k: (stats, ["truncated"], "me"))
    called = []
    monkeypatch.setattr(github_public, "render", lambda *a, **k: called.append(True))
    result = github_public.run("me", 2026, tmp_path / "out", profile_repo=tmp_path,
                               push_profile=True, no_cache=True, quiet=True)
    assert result == 1
    assert not called
    assert "truncated" in capsys.readouterr().err


def test_strict_mode_blocks_separate_automation(tmp_path, monkeypatch):
    stats = SimpleNamespace(year=2026, commit_count=1)
    monkeypatch.setattr(github_public, "fetch_stats", lambda *a, **k: (stats, ["truncated"], "me"))
    assert github_public.run("me", 2026, tmp_path, require_complete=True, no_cache=True) == 1


def test_incomplete_public_stats_warn_when_updating_locally(tmp_path, monkeypatch, capsys):
    stats = SimpleNamespace(year=2026, commit_count=1, repo_count=1, lines_changed=1,
                            active_days=1, file_count=1, persona=SimpleNamespace(title="x"))
    monkeypatch.setattr(github_public, "fetch_stats", lambda *a, **k: (stats, ["truncated"], "me"))
    def render(stats, out, **kwargs):
        out.mkdir(parents=True, exist_ok=True)
        return []
    monkeypatch.setattr(github_public, "render", render)
    assert github_public.run("me", 2026, tmp_path / "out", profile_repo=tmp_path,
                             no_cache=True, quiet=True) == 0
    assert "truncated" in capsys.readouterr().err
