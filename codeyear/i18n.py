"""Tiny two-language message table for the CLI (no gettext dependency).

Chinese is the default; ``--lang en``, ``CODEYEAR_LANG=en`` or an English
system locale switches the CLI help and selected runtime messages to English.
"""

from __future__ import annotations

import argparse
import locale
import os

_LANG = "zh"

EN = {
    # top-level parser
    "界面与 Profile 卡片语言 / UI and profile-card language":
        "UI and profile-card language",
    # GUI language-switch label stays in Chinese
    "中文": "中文",
    "扫描本地 git 仓库，生成一份年度代码报告（HTML + PNG 海报）。":
        "Scan local git repositories and generate an annual code report "
        "(HTML + poster).",
    # command help
    "图形界面：点选目录、看进度、选输出位置":
        "Desktop GUI: pick folders, watch progress, choose output",
    "终端交互向导：选目录、看进度、选输出位置":
        "Terminal wizard: pick folders, watch progress, choose output",
    "检查或安装最新版本": "Check for or install the latest release",
    "只检查是否有新版本，不安装":
        "Only check whether an update is available",
    "从公开 GitHub 账号生成（联网，仅公开仓库）":
        "Generate from a public GitHub account (network, public repos only)",
    "启动公开 GitHub 卡片 HTTP 服务":
        "Run the public GitHub card HTTP service",
    "扫描一个文件夹下的所有 git 仓库":
        "Scan all git repositories under a folder",
    # github
    "GitHub 用户名": "GitHub username",
    "统计年份": "Year to report",
    "输出目录": "Output directory",
    "GitHub token；也可用 GITHUB_TOKEN":
        "GitHub token; GITHUB_TOKEN also works",
    "最多拉取多少条提交（无 token 时自动限制为 30）":
        "Maximum commits to fetch (capped at 30 without a token)",
    "包含 fork 仓库": "Include fork repositories",
    "生成后打开报告": "Open the report when done",
    "不打印扫描进度": "Suppress scan progress",
    "卡片主题：paper / mono / forest / ocean":
        "Card theme: paper / mono / forest / ocean",
    "只生成主页卡片和 embed 片段，不生成完整报告":
        "Only generate the profile card and embed snippet",
    "本地 GitHub Profile 仓库路径；自动更新 README 里的卡片":
        "Local GitHub profile repository; updates the card in its README",
    "更新后提交并推送 Profile 仓库（联网）；需同时指定 --profile-repo":
        "Commit and push the profile repo after updating (network); "
        "requires --profile-repo",
    "缓存公开 commit 详情到该目录，重复运行更快":
        "Cache public commit details in this directory for faster reruns",
    "禁用公开 commit 详情本地缓存":
        "Disable local caching of public commit details",
    "当年没有提交时回退到上一年，适合跨年自动更新":
        "Fall back to the previous year when the requested year has no commits",
    "时区（如 UTC+8 或 Asia/Shanghai；默认本机时区）":
        "Timezone (e.g. UTC+8 or Asia/Shanghai; default local timezone)",
    # serve
    "监听地址，默认 127.0.0.1": "Listen address, default 127.0.0.1",
    "监听端口，默认 8000": "Listen port, default 8000",
    "每张卡片最多拉取多少条提交": "Maximum commits fetched per card",
    # scan
    "要扫描的文件夹（可以多个，默认当前目录）":
        "Folders to scan (multiple allowed; default current directory)",
    "统计年份，默认今年": "Year to report, default current year",
    "统计过去 365 天（滚动年度），而非自然年":
        "Count the past 365 days (rolling year) instead of a calendar year",
    "排除指定仓库名或通配符（可重复或逗号分隔）":
        "Exclude repositories by name or glob (repeatable or comma-separated)",
    "输出目录，默认 ./codeyear-output":
        "Output directory, default ./codeyear-output",
    "只统计匹配的 git author（--author 参数）":
        "Only count the matching git author (--author)",
    "同时扫描去年，在报告里生成同比数据":
        "Also scan last year and add year-over-year data",
    "额外作者邮箱或名字，可重复；用于旧提交":
        "Extra author email/name, repeatable; for old commits",
    "忽略仓库里的 .mailmap（默认自动使用）":
        "Ignore the repository's .mailmap (used automatically by default)",
    "统计所有本地分支/tag 的提交（默认只看当前分支）":
        "Include every local branch/tag (default: current branch only)",
    "统计所有作者的提交（默认只统计你本人，按 git user.name / user.email 识别）":
        "Count every author (default: only you, by git user.name / user.email)",
    "向下查找仓库的最大文件夹层数，默认 6":
        "Maximum folder depth to search for repositories, default 6",
    "单个仓库的扫描超时秒数": "Per-repository timeout in seconds",
    "并行扫描的仓库数，默认 1": "Repositories to scan in parallel, default 1",
    "不生成 PNG 海报": "Skip the PNG poster",
    "不生成完整版长图": "Skip the full-length image",
    "不生成 GitHub 主页卡片": "Skip the GitHub profile card",
    "不生成 HTML 报告": "Skip the HTML report",
    "本地 GitHub Profile 仓库路径；只写入本地，不联网":
        "Local GitHub profile repository; writes locally only",
    "生成后自动打开报告": "Open the report when done",
    # runtime: scan
    "请改用 codeyear tui 或 codeyear scan。":
        "Use `codeyear tui` or `codeyear scan` instead.",
    "无法自动打开文件: {exc}": "Could not open the file: {exc}",
    "无法加载图形界面（Tkinter）: {exc}":
        "Could not load the GUI (Tkinter): {exc}",
    "错误: {exc}": "Error: {exc}",
    "--push-profile 需要同时指定 --profile-repo":
        "--push-profile requires --profile-repo",
    "在 {where} 下没有找到 git 仓库。":
        "No git repositories found under {where}.",
    "CodeYear {year} · 在 {where} 下找到 {count} 个仓库":
        "CodeYear {year} · found {count} repositories under {where}",
    "! 未检测到 git user.name / user.email，将统计所有作者的提交":
        "! No git user.name / user.email detected; counting all authors",
    "{year} 年没有找到提交。可以换 --year，或检查 --author 过滤条件。":
        "No commits found in {year}. Try another --year or check --author.",
    "! 指定了 --profile-repo，但 --no-card 关闭了卡片生成":
        "! --profile-repo was set, but --no-card disabled card generation",
    "Profile  已提交并推送": "Profile  committed and pushed",
    "Profile  仅写入本地": "Profile  written locally",
    "Profile  卡片已是最新": "Profile  card is up to date",
    "已提交并推送": "committed and pushed",
    "仅写入本地": "written locally",
    "Profile  {state} · {repo}": "Profile  {state} · {repo}",
    "Profile  卡片已是最新 · {repo}": "Profile  card is up to date · {repo}",
    "! 更新 Profile 失败: {exc}": "! Profile update failed: {exc}",
    "活跃      {days} 天（{pct}）· 最长连续 {streak} 天":
        "Active      {days} days ({pct}) · longest streak {streak} days",
    "语言      {count} 种": "Languages   {count}",
    "最忙一天  {day} · {count} 次提交":
        "Busiest day  {day} · {count} commits",
    "活跃      {days} 天 · 涉及 {count} 个文件":
        "Active      {days} days · across {count} files",
    "警告:": "Warnings:",
    "提示:": "Notes:",
    "仓库": "Repos",
    "身份": "Identity",
    "已过滤": "Filtered",
    "次他人提交": "commits by others",
    "提交": "Commits",
    "代码行": "Lines",
    "活跃": "Active",
    "最长连续": "Longest streak",
    "语言": "Languages",
    "最忙一天": "Busiest day",
    "警告": "Warnings",
    "身份 --author={author}": "Identity --author={author}",
    "身份 全部作者": "Identity  all authors",
    "全部作者": "all authors",
    "CodeYear {year}  ·  {title}": "CodeYear {year}",
    # runtime: public github
    "未设置 GITHUB_TOKEN，最多拉取 30 条提交。":
        "GITHUB_TOKEN not set; limiting to 30 commits.",
    "    {repo} · {count} 次提交": "    {repo} · {count} commits",
    "账号": "Account",
    "输出": "Output",
    "提示": "Notes",
    "找不到 GitHub 用户: {username}": "GitHub user not found: {username}",
    "GitHub API 错误: {exc}": "GitHub API error: {exc}",
    "{login} 在 {year} 年没有找到公开提交。":
        "No public commits found for {login} in {year}.",
    "已达到 --max-commits 上限（{limit}）":
        "Reached the --max-commits limit ({limit})",
    "GitHub API 额度不足，请使用更高额度的 token（如 CODEYEAR_TOKEN）后重试。":
        "GitHub API quota exhausted; use a higher-limit token "
        "(e.g. CODEYEAR_TOKEN) and retry.",
    # wizard
    "选择要扫描的目录。默认是当前目录，可以继续添加。":
        "Choose folders to scan. The current directory is selected by default.",
    "已选择：": "Selected:",
    "（空）": "(empty)",
    "[Enter] 开始   [a] 添加目录   [r] 删除   [c] 清空":
        "[Enter] start   [a] add folder   [r] remove   [c] clear",
    "至少选择一个目录。": "Choose at least one folder.",
    "目录路径": "Folder path",
    "这不是一个文件夹。": "That is not a folder.",
    "这个目录已经在列表里。": "That folder is already in the list.",
    "删除第几个": "Remove number",
    "编号不对。": "Invalid number.",
    "未知选项。": "Unknown option.",
    "无法自动打开报告: {exc}": "Could not open the report: {exc}",
    "向下扫描层级（文件夹层数）": "Folder depth to scan",
    "正在查找 git 仓库…": "Looking for git repositories…",
    "找到 {count} 个 git 仓库。": "Found {count} git repositories.",
    "没有找到仓库，换个目录试试。": "No repositories found; try another folder.",
    "只统计你本人（{label}）?": "Count only you ({label})?",
    "旧邮箱/名字（逗号分隔，可空）":
        "Old email/name (comma-separated, optional)",
    "未检测到 git 身份，将统计所有作者。":
        "No git identity detected; counting all authors.",
    "同时统计去年，生成同比?": "Also scan last year and add year-over-year data?",
    "统计所有分支/tag?": "Include all branches/tags?",
    "并行扫描数": "Parallel scans",
    "完成后打开报告?": "Open the report when done?",
    "{year} 年没有找到提交。": "No commits found in {year}.",
    "已取消。": "Cancelled.",
    # GUI
    "CodeYear · 代码手账": "CodeYear",
    "代码手账": "CodeYear",
    "选择目录，生成一份本地年度代码报告。":
        "Choose folders and generate a local annual code report.",
    "扫描目录": "Scan folders",
    "添加目录": "Add folder",
    "删除选中": "Remove selected",
    "清空": "Clear",
    "检查仓库": "Check repos",
    "可添加多个目录": "Multiple folders allowed",
    "年份": "Year",
    "扫描层级": "Depth",
    "卡片主题": "Card theme",
    "保存默认": "Save defaults",
    "已保存默认设置。": "Default settings saved.",
    "只统计我本人（{who}）": "Count only me ({who})",
    "未检测到 git 身份，将统计所有作者":
        "No git identity detected; counting all authors",
    "扫描层级 = 向下查找仓库的文件夹层数，默认 6。":
        "Depth = folder levels to search for repositories, default 6.",
    "并行数": "Jobs",
    "同比去年": "Compare last year",
    "所有分支": "All branches",
    "旧邮箱/名字": "Old emails/names",
    "选择…": "Choose…",
    "开始生成": "Generate",
    "打开报告": "Open report",
    "打开输出目录": "Open output folder",
    "选择目录后点击「开始生成」。":
        "Choose folders, then click Generate.",
    "结果": "Result",
    "选择要扫描的目录": "Choose folders to scan",
    "已添加，开始生成时会统计仓库数量":
        "Added; repository count is checked when generating",
    "没有目录": "No folders",
    "请先添加至少一个目录。": "Add at least one folder first.",
    "正在检查…": "Checking…",
    "选择输出目录": "Choose output folder",
    "请先添加至少一个要扫描的目录。":
        "Add at least one folder to scan first.",
    "参数不对": "Invalid values",
    "年份、扫描层级和并行数必须是数字。":
        "Year, depth and jobs must be numbers.",
    "没有找到 git 仓库。": "No git repositories found.",
    "找到 {count} 个 git 仓库": "Found {count} git repositories",
    "找到 {count} 个仓库，开始扫描…":
        "Found {count} repositories; scanning…",
    "仓库 {repos} · 提交 {commits} · 活跃 {days} 天 · 涉及 {files} 个文件":
        "Repos {repos} · Commits {commits} · Active {days} days · "
        "{files} files",
    "输出目录：{path}": "Output folder: {path}",
    "警告：": "Warnings:",
    "完成。": "Done.",
    "失败：{message}": "Failed: {message}",
    "生成失败": "Generation failed",
    "无法打开": "Cannot open",
    "无法保存": "Could not save",
    "无法启动图形界面: {exc}": "Could not start the GUI: {exc}",
    "检查更新": "Check update",
    "发现新版 v{version}": "Update v{version}",
    "正在检查更新…": "Checking for updates…",
    "正在下载并更新…": "Downloading and installing update…",
    "发现新版本": "Update available",
    "发现新版本 v{latest}（当前 v{current}）。\n是否立即在软件内自动更新？":
        "Version v{latest} is available (current v{current}).\n"
        "Update in-app now?",
    "更新完成": "Update complete",
    "近 365 天": "Last 365d",
    "排除仓库": "Exclude",
    "GitHub 账号（留空扫本地）": "GitHub user (optional)",
    "Profile 仓库": "Profile repo",
    "推送": "Push",
    "选择 Profile 仓库目录": "Choose profile repository folder",
    "正在拉取公开 GitHub 数据…": "Fetching public GitHub data…",
    "无法连接更新服务器，请检查网络。":
        "Could not reach the update server; check your connection.",
    "当前已是最新版本（v{version}）。":
        "Already on the latest version (v{version}).",
    "发现新版本 v{latest}（当前 v{current}）: {url}":
        "New version v{latest} available (current v{current}): {url}",
    "安装包 SHA256 校验未通过，已取消更新。":
        "Update package failed SHA256 verification; cancelled.",
    "已更新到 v{version}，重新打开软件即可生效。":
        "Updated to v{version}. Restart CodeYear to use the new version.",
    "已更新到 v{version}。": "Updated to v{version}.",
    "更新失败: {exc}": "Update failed: {exc}",
}


def _normalize(value: str | None) -> str:
    return "en" if (value or "").lower().startswith("en") else "zh"


def set_lang(value: str | None) -> None:
    global _LANG
    _LANG = _normalize(value)


def get_lang() -> str:
    return _LANG


def detect(argv: list[str] | None = None) -> str:
    args = list(argv or [])
    for index, arg in enumerate(args):
        if arg == "--lang" and index + 1 < len(args):
            return _normalize(args[index + 1])
        if arg.startswith("--lang="):
            return _normalize(arg.split("=", 1)[1])
    env = os.environ.get("CODEYEAR_LANG")
    if env:
        return _normalize(env)
    loc = os.environ.get("LC_ALL") or os.environ.get("LANG") or ""
    if not loc:
        try:
            loc = locale.getlocale()[0] or ""
        except (ValueError, OSError):
            loc = ""
    loc = loc.lower()
    if "zh" in loc or "chinese" in loc:
        return "zh"
    return "en" if loc else "zh"


def tr(text: str, **kwargs) -> str:
    if _LANG == "en":
        text = EN.get(text, text)
    return text.format(**kwargs) if kwargs else text


def localize_parser(parser: argparse.ArgumentParser) -> None:
    """Translate argparse help strings in place (recursing into subparsers)."""
    if _LANG != "en":
        return
    if parser.description:
        parser.description = tr(parser.description)
    for action in parser._actions:
        if action.help:
            action.help = tr(action.help)
        if isinstance(action, argparse._SubParsersAction):
            for choice in action._choices_actions:
                if choice.help:
                    choice.help = tr(choice.help)
            for subparser in action.choices.values():
                localize_parser(subparser)
