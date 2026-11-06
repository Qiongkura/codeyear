from codeyear import updater


def test_pep440_prerelease_ordering():
    assert updater._version_is_newer("1.0.0", "1.0.0rc1")
    assert not updater._version_is_newer("1.0.0rc1", "1.0.0")
    assert updater._version_is_newer("1.0.0rc2", "1.0.0rc1")
    assert updater._version_is_newer("1.0.0.post1", "1.0.0")
    assert updater._version_is_newer("1.0.0", "1.0.0.dev1")


def test_release_info_uses_pep440_prerelease_comparison():
    info = updater._build_release_info("1.0.0rc1", "v1.0.0rc2")
    assert info["has_update"] is True
    info = updater._build_release_info("1.0.0", "1.0.0rc2")
    assert info["has_update"] is False


def test_invalid_versions_are_not_treated_as_updates():
    assert not updater._version_is_newer("release-2", "release-1")
