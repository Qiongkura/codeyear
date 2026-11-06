"""Config-backed CLI booleans can be overridden in either direction."""

import json

import pytest

from codeyear.cli import _build_parser

OPTIONS = [
    ("scan", "rolling", "--rolling", "--no-rolling"),
    ("scan", "compare", "--compare", "--no-compare"),
    ("scan", "fallback_previous", "--fallback-previous", "--no-fallback-previous"),
    ("scan", "all_branches", "--all-branches", "--no-all-branches"),
    ("scan", "all_authors", "--all-authors", "--no-all-authors"),
    ("scan", "no_mailmap", "--no-mailmap", "--mailmap"),
    ("scan", "open", "--open", "--no-open"),
    ("github", "open", "--open", "--no-open"),
]


@pytest.mark.parametrize("command,key,enable,disable", OPTIONS)
@pytest.mark.parametrize("configured", [False, True])
def test_boolean_config_and_cli_precedence(tmp_path, monkeypatch, command, key, enable, disable, configured):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({key: configured}), encoding="utf-8")
    monkeypatch.setenv("CODEYEAR_CONFIG", str(config))
    parser = _build_parser()
    base = [command] + (["someone"] if command == "github" else [])
    assert getattr(parser.parse_args(base), key) is configured
    assert getattr(parser.parse_args([*base, enable]), key) is True
    assert getattr(parser.parse_args([*base, disable]), key) is False
    assert getattr(parser.parse_args([*base, enable, disable]), key) is False
    assert getattr(parser.parse_args([*base, disable, enable]), key) is True


@pytest.mark.parametrize("command,key,enable,disable", OPTIONS)
def test_default_is_false_without_config(tmp_path, monkeypatch, command, key, enable, disable):
    monkeypatch.setenv("CODEYEAR_CONFIG", str(tmp_path / "missing.json"))
    base = [command] + (["someone"] if command == "github" else [])
    assert getattr(_build_parser().parse_args(base), key) is False


def test_help_shows_inverse_options(monkeypatch, tmp_path):
    monkeypatch.setenv("CODEYEAR_CONFIG", str(tmp_path / "missing.json"))
    parser = _build_parser()
    subparsers = next(action for action in parser._actions if action.dest == "command")
    scan_help = subparsers.choices["scan"].format_help()
    github_help = subparsers.choices["github"].format_help()
    for flag in ("--no-rolling", "--no-compare", "--no-fallback-previous",
                 "--no-all-branches", "--no-all-authors", "--mailmap", "--no-open"):
        assert flag in scan_help
    assert "--no-open" in github_help
