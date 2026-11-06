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
    ok, _ = updater.perform_update({"has_update": True, "latest": "1.0",
                                    "exe_url": "exe", "sums_url": "sums"})
    assert not ok
    assert exe.read_bytes() == b"original"
    assert not (tmp_path / "CodeYear.exe.tmp").exists()
