import subprocess

import pytest

from codeyear.profile import update_profile


def git(repo, *args):
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True,
        capture_output=True, text=True,
    ).stdout


def setup_repo(tmp_path):
    repo = tmp_path / "profile"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.name", "Test")
    git(repo, "config", "user.email", "test@example.com")
    (repo / "README.md").write_text("# Profile\n", encoding="utf-8")
    (repo / "private.txt").write_text("original\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "initial")
    light = tmp_path / "light.svg"
    dark = tmp_path / "dark.svg"
    light.write_text("light", encoding="utf-8")
    dark.write_text("dark", encoding="utf-8")
    return repo, light, dark


def test_push_rejects_staged_changes_before_modifying_files(tmp_path):
    repo, light, dark = setup_repo(tmp_path)
    (repo / "private.txt").write_text("staged secret\n", encoding="utf-8")
    git(repo, "add", "private.txt")
    (repo / "private.txt").write_text("unstaged secret\n", encoding="utf-8")
    before = git(repo, "diff", "--cached", "--binary")
    head = git(repo, "rev-parse", "HEAD")
    with pytest.raises(RuntimeError, match="staged changes"):
        update_profile(repo, 2026, light, dark, push=True)
    assert git(repo, "diff", "--cached", "--binary") == before
    assert git(repo, "rev-parse", "HEAD") == head
    assert (repo / "private.txt").read_text(encoding="utf-8") == "unstaged secret\n"
    assert (repo / "README.md").read_text(encoding="utf-8") == "# Profile\n"
    assert not (repo / "codeyear-2026-card-v1.svg").exists()


@pytest.mark.parametrize("name", ["README.md", "assets/codeyear-other.svg"])
def test_push_rejects_preexisting_profile_path_changes(tmp_path, name):
    repo, light, dark = setup_repo(tmp_path)
    path = repo / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("user content\n", encoding="utf-8")
    before = git(repo, "status", "--porcelain", "--untracked-files=all")
    with pytest.raises(RuntimeError, match="README or card changes"):
        update_profile(repo, 2026, light, dark, push=True)
    assert git(repo, "status", "--porcelain", "--untracked-files=all") == before
    assert path.read_text(encoding="utf-8") == "user content\n"


def configure_remote(tmp_path, repo):
    remote = tmp_path / "remote.git"
    subprocess.run(["git", "init", "--bare", "-q", str(remote)], check=True)
    branch = git(repo, "symbolic-ref", "--short", "HEAD").strip()
    head = git(repo, "rev-parse", "HEAD").strip()
    # Populate the local bare repository without invoking git push.
    subprocess.run(["git", "--git-dir", str(remote), "fetch", "-q", str(repo),
                    f"{head}:refs/heads/{branch}"], check=True)
    git(repo, "remote", "add", "origin", str(remote))
    git(repo, "config", f"branch.{branch}.remote", "origin")
    git(repo, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")
    git(repo, "update-ref", f"refs/remotes/origin/{branch}", head)
    return remote, branch


def test_push_rejects_preexisting_unpushed_commit(tmp_path, monkeypatch):
    repo, light, dark = setup_repo(tmp_path)
    remote, branch = configure_remote(tmp_path, repo)
    (repo / "private.txt").write_text("private committed data\n", encoding="utf-8")
    git(repo, "add", "private.txt")
    git(repo, "commit", "-qm", "private commit")
    head = git(repo, "rev-parse", "HEAD")
    before = git(repo, "status", "--porcelain")
    from codeyear import profile
    monkeypatch.setattr(profile, "_push", lambda *args: pytest.fail("unexpected push"))
    with pytest.raises(RuntimeError, match="unpushed or incoming"):
        update_profile(repo, 2026, light, dark, push=True)
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == before
    assert (repo / "README.md").read_text(encoding="utf-8") == "# Profile\n"
    assert not (repo / "codeyear-2026-card-v1.svg").exists()
    assert subprocess.run(["git", "--git-dir", str(remote), "rev-parse",
                           f"refs/heads/{branch}"], capture_output=True,
                          text=True, check=True).stdout != head


def test_push_target_rejects_unpushed_history_without_modifying_files(tmp_path, monkeypatch):
    from codeyear import profile

    repo, light, dark = setup_repo(tmp_path)
    real_git = profile._git
    remote_head = git(repo, "rev-parse", "HEAD").strip()
    (repo / "private.txt").write_text("private\n", encoding="utf-8")
    git(repo, "add", "private.txt")
    git(repo, "commit", "-qm", "private")
    branch = git(repo, "symbolic-ref", "--short", "HEAD").strip()
    git(repo, "config", f"branch.{branch}.remote", "origin")
    git(repo, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")

    def fake_git(repo, *args):
        if args[:4] == ("remote", "get-url", "--push", "--all"):
            return subprocess.CompletedProcess(args, 0, "example-remote\n", "")
        if args[0] == "ls-remote":
            return subprocess.CompletedProcess(args, 0, f"{remote_head}\trefs/heads/{branch}\n", "")
        if args[0] == "push":
            pytest.fail("unexpected push")
        return real_git(repo, *args)

    monkeypatch.setattr(profile, "_git", fake_git)
    with pytest.raises(RuntimeError, match="unpushed or incoming"):
        update_profile(repo, 2026, light, dark, push=True)
    assert (repo / "README.md").read_text(encoding="utf-8") == "# Profile\n"
    assert not (repo / "codeyear-2026-card-v1.svg").exists()


def test_push_targets_only_verified_branch(tmp_path, monkeypatch):
    from codeyear import profile

    repo, light, dark = setup_repo(tmp_path)
    head = git(repo, "rev-parse", "HEAD").strip()
    branch = git(repo, "symbolic-ref", "--short", "HEAD").strip()
    git(repo, "config", f"branch.{branch}.remote", "origin")
    git(repo, "config", f"branch.{branch}.merge", f"refs/heads/{branch}")
    real_git = profile._git
    calls = []

    def fake_git(repo, *args):
        if args[:4] == ("remote", "get-url", "--push", "--all"):
            return subprocess.CompletedProcess(args, 0, "example-remote\n", "")
        if args[0] == "ls-remote":
            return subprocess.CompletedProcess(args, 0, f"{head}\trefs/heads/{branch}\n", "")
        if args[0] == "push":
            calls.append(args)
            return subprocess.CompletedProcess(args, 0, "", "")
        return real_git(repo, *args)

    monkeypatch.setattr(profile, "_git", fake_git)
    assert update_profile(repo, 2026, light, dark, push=True)[1:] == (True, True)
    new_head = git(repo, "rev-parse", "HEAD").strip()
    assert calls == [("push", "example-remote", f"{new_head}:refs/heads/{branch}")]
    assert git(repo, "rev-parse", "HEAD^").strip() == head


def test_push_requires_verifiable_upstream(tmp_path):
    repo, light, dark = setup_repo(tmp_path)
    with pytest.raises(RuntimeError, match="upstream"):
        update_profile(repo, 2026, light, dark, push=True)
    assert not (repo / "codeyear-2026-card-v1.svg").exists()


def test_clean_remote_creates_only_card_commit(tmp_path, monkeypatch):
    repo, light, dark = setup_repo(tmp_path)
    remote, branch = configure_remote(tmp_path, repo)
    old_head = git(repo, "rev-parse", "HEAD").strip()
    from codeyear import profile
    calls = []
    monkeypatch.setattr(profile, "_push", lambda *args: calls.append(args))
    _, changed, pushed = update_profile(repo, 2026, light, dark, push=True)
    assert changed and pushed
    assert calls == [(repo.resolve(), str(remote), f"refs/heads/{branch}", old_head)]
    assert git(repo, "rev-parse", "HEAD^").strip() == old_head
    assert set(git(repo, "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD").splitlines()) == {
        "README.md", "codeyear-2026-card-v1.svg", "codeyear-2026-card-v1-dark.svg"
    }
