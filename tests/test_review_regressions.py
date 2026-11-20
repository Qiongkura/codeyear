from datetime import datetime
from pathlib import Path

from codeyear.scanner import Commit, RepoResult, _readme_line
from codeyear.stats import build_stats


def test_readme_skips_badges_and_code_preserves_csharp(tmp_path):
    (tmp_path / "README.md").write_text(
        '# [![Build](https://example.com/badge)](https://example.com)\n'
        '```bash\nnpm install example\n```\n'
        '# A tool for C# and F# developers\n', encoding="utf-8",
    )
    assert _readme_line(tmp_path) == "A tool for C# and F# developers"


def test_five_am_is_not_night():
    commit = Commit(repo="demo", hash="a", dt=datetime(2026, 1, 2, 5, 30),
                    subject="morning", added=1, deleted=0, files=1)
    stats = build_stats(year=2026, root="demo", repos=[
        RepoResult(path=Path("demo"), name="demo", commits=[commit])
    ])
    assert stats.night_share == 0
    assert stats.latest_night_commit is None


def test_exe_update_requires_checksum(tmp_path, monkeypatch):
    from codeyear import updater

    exe = tmp_path / "CodeYear.exe"
    exe.write_bytes(b"original")
    monkeypatch.setattr(updater, "is_frozen", lambda: True)
    monkeypatch.setattr(updater.sys, "executable", str(exe))

    def download(url, timeout):
        if url == "sums":
            raise OSError("unavailable")
        return b"new executable"

    monkeypatch.setattr(updater, "_download_bytes", download)
    ok, msg = updater.perform_update({"has_update": True, "latest": "1.0",
                                      "exe_url": "exe", "sums_url": "sums"})
    assert not ok
    assert "SHA256" not in msg
    assert exe.read_bytes() == b"original"
    assert not (tmp_path / "CodeYear.exe.tmp").exists()


def test_deleted_files_uses_styled_bar_and_protects_raw_data():
    from codeyear.html_report import build_html
    from codeyear.report_theme import decorate, to_english
    from codeyear.scanner import FileChange

    repo = RepoResult(
        path=Path("仓库A"),
        name="仓库A",
        commits=[
            Commit(
                repo="仓库A",
                hash="9" * 40,
                dt=datetime(2026, 5, 1, 2, 30),
                subject="refactor: 清理 1.5万 行历史代码与其他模块",
                added=5,
                deleted=240,
                files=1,
                author_email="me@example.com",
                author_name="Me",
                changes=[
                    FileChange(
                        "src/其他_1.5万.py", "Python", 245, added=5, deleted=240
                    )
                ],
            )
        ],
        total_commits=1,
    )
    stats = build_stats(
        year=2026, root="/tmp", repos=[repo], identity=("me@example.com", "Me")
    )
    html = decorate(build_html(stats), stats)
    assert "file-row" not in html
    assert "f-bar" not in html
    assert 'class="file-line"' in html
    assert 'class="bar-track"' in html

    en = to_english(html, stats)
    assert "src/其他_1.5万.py" in en
    assert "清理 1.5万 行历史代码" in en


def test_rolling_window_months_and_english_report():
    import re

    from codeyear.card import build_svg
    from codeyear.html_report import build_html
    from codeyear.report_theme import decorate, to_english
    from codeyear.scanner import FileChange
    from codeyear.stats import date_window, window_days, window_months

    repo = RepoResult(
        path=Path("demo"),
        name="demo",
        root_dt=datetime(2025, 12, 10, 9, 0),
        commits=[
            Commit(
                repo="demo",
                hash="c" * 40,
                dt=datetime(2026, 3, 10, 14, 0),
                subject="feat: rolling commit",
                added=20,
                deleted=4,
                files=1,
                author_email="me@example.com",
                author_name="Me",
                changes=[FileChange("app.py", "Python", 24, added=20, deleted=4)],
            )
        ],
        total_commits=1,
    )
    stats = build_stats(
        year=2026,
        root="/tmp/demo",
        repos=[repo],
        identity=("me@example.com", "Me"),
        rolling=True,
        since_dt=datetime(2025, 11, 19, 0, 0, 0),
        until_dt=datetime(2026, 11, 18, 23, 59, 59),
    )
    start, end = date_window(stats)
    assert (start.isoformat(), end.isoformat()) == ("2025-11-19", "2026-11-18")
    assert window_days(stats) == 365
    assert stats.new_repos == 1
    months = window_months(stats)
    assert len(months) == 12
    # The window touches 13 calendar months; the two oldest share the first
    # bar so the remaining bars stay chronological.
    assert [lbl for _, lbl in months] == [
        "11·12", "01", "02", "03", "04", "05", "06", "07", "08", "09", "10",
        "11"
    ]
    assert [lbl for _, lbl in months] == stats.monthly_labels
    assert all(start <= d <= end for d, _ in months)

    svg = build_svg(stats, lang="en")
    assert not re.findall(r"[\u4e00-\u9fff]+", svg)

    html = decorate(build_html(stats), stats)
    assert "近 365 天活跃热力图" in html
    en = to_english(html, stats)
    en_no_script = re.sub(r"<(style|script)\b.*?</\1>", "", en, flags=re.S | re.I)
    chinese = set(re.findall(r"[\u4e00-\u9fff]+", en_no_script))
    assert chinese <= {"中文"}


def test_card_preview_slot_map_preserves_distinct_dark_colors():
    import re

    from codeyear.card import THEMES
    from codeyear.html_report import _SLOT_PALETTE, _slot_map, build_card_preview_widget

    stats = build_stats(
        year=2026,
        root="/tmp",
        repos=[
            RepoResult(
                path=Path("demo"),
                name="demo",
                commits=[
                    Commit(
                        repo="demo",
                        hash=f"{i:040x}",
                        dt=datetime(2026, 2, 1, 10 + i, 0),
                        subject="feat: x",
                        added=10,
                        deleted=1,
                        files=1,
                    )
                    for i in range(5)
                ],
                total_commits=5,
            )
        ],
    )
    widget = build_card_preview_widget(stats, lang="en")
    assert "themePart" not in widget
    forest_dark = THEMES["forest"][1]
    smap = _slot_map(forest_dark)
    assert smap[_SLOT_PALETTE["muted"]] == forest_dark["muted"]
    assert smap[_SLOT_PALETTE["levels"][3]] == forest_dark["levels"][3]
    assert forest_dark["muted"] != forest_dark["levels"][3]
    assert re.search(r"#01000f", widget)


def test_server_tz_validation_normalization_and_error_sanitization(monkeypatch):
    import threading
    import urllib.error
    import urllib.request
    from http.server import ThreadingHTTPServer

    from codeyear import server

    calls = []
    stats = build_stats(
        year=2026,
        root="https://github.com/me",
        repos=[
            RepoResult(
                path=Path("me/demo"),
                name="me/demo",
                commits=[
                    Commit(
                        repo="me/demo",
                        hash="1" * 40,
                        dt=datetime(2026, 1, 2, 10, 0),
                        subject="feat: ok",
                        added=1,
                        deleted=0,
                        files=1,
                    )
                ],
                total_commits=1,
            )
        ],
    )

    def fake_fetch(username, year, **kwargs):
        if username == "explode":
            raise KeyError("secret_internal_token_123")
        calls.append(kwargs.get("tz"))
        return stats, [], username

    monkeypatch.setattr(server, "fetch_stats", fake_fetch)
    monkeypatch.setattr(server.Handler, "log_message", lambda *a, **k: None)
    server.CACHE.clear()
    server.RATE.clear()

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"
    try:
        try:
            urllib.request.urlopen(
                f"{base}/card.svg?username=me&year=2026&tz=not_a_real_tz",
                timeout=5,
            )
        except urllib.error.HTTPError as exc:
            assert exc.code == 400
            assert b"invalid timezone" in exc.read()
        else:
            raise AssertionError("expected 400 for invalid tz")
        assert calls == []

        with urllib.request.urlopen(
            f"{base}/card.svg?username=me&year=2026&tz=UTC%2B8", timeout=5
        ) as r1:
            assert r1.status == 200
        with urllib.request.urlopen(
            f"{base}/card.svg?username=me&year=2026&tz=%2B08:00", timeout=5
        ) as r2:
            assert r2.status == 200
        assert len(calls) == 1

        try:
            urllib.request.urlopen(
                f"{base}/card.svg?username=explode&year=2026", timeout=5
            )
        except urllib.error.HTTPError as exc:
            assert exc.code == 502
            body = exc.read().decode("utf-8")
            assert "secret_internal_token_123" not in body
            assert "upstream service error" in body
        else:
            raise AssertionError("expected 502")
    finally:
        httpd.shutdown()
        httpd.server_close()
        t.join(timeout=5)


def test_github_list_skips_merges_slims_cache_and_exact_limit_no_warn(monkeypatch):
    from codeyear import github_public as gh

    class RichAPI:
        token = "tok"
        remaining = 5000

        def __init__(self):
            self.detail_shas = []

        def get(self, path, params=None):
            if path == "/users/me":
                return {"login": "me", "name": "Me"}
            if path == "/users/me/repos":
                return [
                    {
                        "full_name": "me/repo",
                        "private": False,
                        "fork": False,
                        "pushed_at": "2026-06-01T00:00:00Z",
                        "html_url": "https://github.com/me/repo",
                        "created_at": "2025-01-01T00:00:00Z",
                    }
                ]
            if path == "/repos/me/repo/commits":
                if params["page"] > 1:
                    return []
                return [
                    {
                        "sha": "merge1",
                        "parents": [{"sha": "p1"}, {"sha": "p2"}],
                        "commit": {"author": {"date": "2026-05-02T10:00:00Z"}},
                    },
                    {
                        "sha": "prevyr",
                        "parents": [{"sha": "p0"}],
                        "commit": {"author": {"date": "2025-12-31T10:00:00Z"}},
                    },
                    {
                        "sha": "real1",
                        "parents": [{"sha": "p1"}],
                        "commit": {"author": {"date": "2026-05-01T10:00:00Z"}},
                    },
                    {
                        "sha": "real2",
                        "parents": [{"sha": "p2"}],
                        "commit": {"author": {"date": "2026-05-03T10:00:00Z"}},
                    },
                ]
            if path == "/repos/me/repo/stats/contributors":
                return [{"author": {"login": "me"}, "weeks": [{"c": 10}]}]
            sha = path.rsplit("/", 1)[-1]
            self.detail_shas.append(sha)
            return {
                "parents": [{}],
                "commit": {
                    "author": {"date": "2026-05-01T10:00:00Z"},
                    "message": f"feat: {sha}\n\nextra body",
                },
                "stats": {"additions": 5, "deletions": 1},
                "files": [
                    {
                        "filename": "a.py",
                        "additions": 5,
                        "deletions": 1,
                        "patch": "@@ -1 +1,5 @@ huge diff",
                    }
                ],
            }

    api = RichAPI()
    monkeypatch.setattr(gh, "GitHubAPI", lambda token=None: api)
    cache_file = Path("mem-cache")
    saved = {}
    monkeypatch.setattr(gh, "_load_cache", lambda p: saved)
    monkeypatch.setattr(gh, "_save_cache", lambda p, d: saved.update(d))

    stats, warnings, login = gh.fetch_stats(
        "me", 2026, token="tok", max_commits=2, quiet=True,
        cache_path=cache_file, tz="UTC",
    )
    assert login == "me"
    assert stats.commit_count == 2
    assert set(api.detail_shas) == {"real1", "real2"}
    assert not warnings
    assert "patch" not in saved["me/repo@real1"]["files"][0]


def test_updater_wheel_sha256_verification_and_pep668(monkeypatch):
    import hashlib
    from types import SimpleNamespace

    from codeyear import updater

    monkeypatch.setattr(updater, "is_frozen", lambda: False)
    wheel_payload = b"fake-wheel-bytes"
    good_hash = hashlib.sha256(wheel_payload).hexdigest()

    def bad_download(url, timeout):
        if url.endswith(".whl"):
            return wheel_payload
        return ("0" * 64 + "  codeyear-1.2.0-py3-none-any.whl\n").encode()

    monkeypatch.setattr(updater, "_download_bytes", bad_download)
    pip_called = []
    monkeypatch.setattr(
        updater.subprocess,
        "run",
        lambda *a, **k: pip_called.append(a) or SimpleNamespace(returncode=0),
    )
    ok, msg = updater.perform_update({
        "has_update": True,
        "current": "1.0.0",
        "latest": "1.2.0",
        "wheel_url": "https://example.com/codeyear-1.2.0-py3-none-any.whl",
        "sums_url": "https://example.com/SHA256SUMS.txt",
    })
    assert not ok
    assert "SHA256" in msg
    assert not pip_called

    def good_download(url, timeout):
        if url.endswith(".whl"):
            return wheel_payload
        return f"{good_hash}  codeyear-1.2.0-py3-none-any.whl\n".encode()

    monkeypatch.setattr(updater, "_download_bytes", good_download)
    monkeypatch.setattr(
        updater.subprocess,
        "run",
        lambda *a, **k: SimpleNamespace(
            returncode=1,
            stderr="error: externally-managed-environment\n",
            stdout="",
        ),
    )
    ok2, msg2 = updater.perform_update({
        "has_update": True,
        "current": "1.0.0",
        "latest": "1.2.0",
        "wheel_url": "https://example.com/codeyear-1.2.0-py3-none-any.whl",
        "sums_url": "https://example.com/SHA256SUMS.txt",
    })
    assert not ok2
    assert "PEP 668" in msg2


def test_cli_copy_append_does_not_mutate_config_defaults(tmp_path, monkeypatch):
    import json

    from codeyear.cli import _build_parser

    cfg = tmp_path / "cfg.json"
    cfg.write_text(
        json.dumps({"exclude": ["vendor-*"], "aliases": ["old@x.com"]}),
        encoding="utf-8",
    )
    monkeypatch.setenv("CODEYEAR_CONFIG", str(cfg))
    parser = _build_parser()

    first = parser.parse_args(["scan", "--exclude", "temp-*", "--alias", "new@x.com"])
    assert first.exclude == ["vendor-*", "temp-*"]
    assert first.alias == ["old@x.com", "new@x.com"]

    second = parser.parse_args(["scan"])
    assert second.exclude == ["vendor-*"]
    assert second.alias == ["old@x.com"]

    cleared = parser.parse_args(["scan", "--exclude", ""])
    assert cleared.exclude == []
