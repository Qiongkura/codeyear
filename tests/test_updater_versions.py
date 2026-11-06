import pytest

from codeyear.updater import _build_release_info, _version_is_newer


@pytest.mark.parametrize("latest,current,expected", [
    ("0.2.14rc1", "0.2.14", False),
    ("0.2.14", "0.2.14rc1", True),
    ("0.2.15.dev1", "0.2.14", True),
    ("0.2.14.post1", "0.2.14", True),
    ("v0.2.15", "0.2.14", True),
    ("invalid999", "0.2.14", False),
])
def test_pep440_update_comparison(latest, current, expected):
    assert _version_is_newer(latest, current) is expected
    assert _build_release_info(current, latest)["has_update"] is expected
