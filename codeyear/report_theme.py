"""New editorial theme and English edition for the CodeYear report."""

from __future__ import annotations

import html as htmlmod
import re

from .stats import ReportStats


def _human(n: int) -> str:
    if n >= 10000:
        return f"{n / 10000:.1f} 万"
    return f"{n:,}"


def _en_human(n: int) -> str:
    if n >= 10000:
        return f"{n / 1000:.0f}k"
    return f"{n:,}"


def _comma(n: int) -> str:
    return f"{n:,}"


CSS = r"""
<style id="v2">
:root{
  --paper:#f5f2e9; --paper2:#ece8dc; --ink:#141413; --ink2:#3d3d3a;
  --muted:#6f6a5e; --line:#d8d2c2; --line2:#c8c2b2;
  --acc:#c8552f; --acc2:#a8431f;
  --serif:Georgia,"Songti SC","SimSun","Noto Serif CJK SC",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;
  --mono:"Cascadia Mono",Consolas,"SFMono-Regular",Menlo,monospace;
}
body{background:var(--paper);font-size:15.5px;line-height:1.8}
body::before,body::after{display:none!important}
#progress,.ticker,.nav-meta,.scroll-hint,.sec-index,.sec-sub,.sec-line,.kicker{display:none!important}
::selection{background:var(--acc);color:var(--paper)}

body{padding-left:220px}
.rail{position:fixed;left:0;top:0;bottom:0;width:220px;padding:38px 26px 26px;
  display:flex;flex-direction:column;justify-content:space-between;
  border-right:1px solid var(--line);background:var(--paper);z-index:20}
.rail-brand{display:flex;align-items:center;gap:8px;font-family:var(--serif);
  font-size:22px;letter-spacing:-.01em}
.rail-brand i{width:7px;height:7px;background:var(--acc);display:block}
.rail-year{font-size:12px;color:var(--muted);margin-top:8px}
.rail-nav{display:flex;flex-direction:column;gap:14px;margin-top:52px;
  border-top:1px solid var(--line);padding-top:22px}
.rail-nav a{font-size:13px;color:var(--muted);text-decoration:none;position:relative}
.rail-nav a:hover{color:var(--ink)}
.rail-nav a.active{color:var(--ink)}
.rail-nav a.active::before{content:"";position:absolute;left:-14px;top:50%;
  width:4px;height:4px;background:var(--acc);transform:translateY(-50%)}

.next-link{display:flex;align-items:baseline;justify-content:flex-end;gap:10px;
  margin-top:52px;font-size:12px;color:var(--muted);text-decoration:none}
.next-link .next-kicker{letter-spacing:.04em}
.next-link .name{font-family:var(--serif);font-size:18px;color:var(--ink)}
.next-link .name i{font-style:normal}
.next-link:hover .name{color:var(--acc)}
.rail-foot .lang{display:block;font-size:12px;color:var(--muted);
  text-decoration:none;margin-bottom:12px}
.rail-foot .top{display:flex;justify-content:space-between;border-top:1px solid var(--line);
  padding-top:14px;font-size:12px;color:var(--ink);text-decoration:none}

.wrap{max-width:1040px;padding:0 56px}
.hero{display:block;padding:100px 0 0}
.cover-kicker{font-size:12px;letter-spacing:.16em;color:var(--acc);margin-bottom:18px}
.cover-year{font-family:var(--serif);font-size:clamp(120px,15vw,180px);line-height:.82;
  letter-spacing:-.05em;color:var(--ink);margin-left:-6px}
.scan-roots{margin:14px 0 0;font-family:var(--sans);font-size:13px;
  color:var(--muted);line-height:1.6;word-break:break-all}
.compare-line{margin:16px 0 0;font-family:var(--sans);font-size:13px;
  color:var(--muted);line-height:1.6}
h1{font-family:var(--serif);font-weight:400;font-size:46px;line-height:1.15;
  letter-spacing:-.02em;color:var(--ink);margin:24px 0 0}
h1 em{font-style:normal;color:var(--acc)}
.lede{margin:22px 0 0;max-width:640px;font-size:18px;line-height:1.8;color:var(--ink2)}

.to-top{position:fixed;right:26px;bottom:26px;z-index:30;display:inline-flex;
  align-items:center;gap:6px;background:var(--paper);border:1px solid var(--ink);
  padding:10px 14px;font-family:var(--sans);font-size:12px;color:var(--ink);
  text-decoration:none;opacity:0;pointer-events:none;transition:opacity .2s}
.to-top.show{opacity:1;pointer-events:auto}
.to-top:hover{background:var(--ink);color:var(--paper)}

.hero-stats{display:grid;grid-template-columns:repeat(4,1fr);background:transparent;
  border:1px solid var(--ink);margin-top:48px;padding:0}
.hero-stats .hs{padding:22px 24px;border:0;border-left:1px solid var(--line);
  text-align:left}
.hero-stats .hs:first-child{border-left:0}
.hs b{display:block;font-family:var(--serif);font-size:40px;line-height:1.1;
  font-weight:400;letter-spacing:-.02em;color:var(--ink)}
.hs span{font-family:var(--sans);font-size:12px;color:var(--muted);letter-spacing:0}

section{padding:88px 0 0;scroll-margin-top:24px}
.sec-head{border-bottom:2px solid var(--ink);padding-bottom:16px;margin-bottom:0}
.sec-head h2{font-family:var(--serif);font-size:36px;font-weight:400;letter-spacing:-.01em}

/* records: no boxes, just a quiet table */
.records{grid-template-columns:repeat(3,1fr);border:0;margin-top:0;column-gap:56px}
.record{border:0;padding:24px 0;min-height:auto}
.record:nth-child(n+4){border-top:1px solid var(--line)}
.record .k{font-family:var(--sans);font-size:12px;letter-spacing:0;color:var(--muted)}
.record .v{font-family:var(--serif);font-size:33px;font-weight:400;letter-spacing:-.01em;
  margin:8px 0 4px}
.record .v small{font-family:var(--sans);font-size:13px}
.record .s{font-family:var(--sans);font-size:12px;color:var(--muted)}

/* repo archive: data plates, not cards */
.archive{border-top:1px solid var(--ink);border-bottom:1px solid var(--line);padding:28px 0 38px;gap:56px}
.plate{border:0;background:transparent;padding:0}
.plate .big b{font-family:var(--serif);font-size:32px;font-weight:400;letter-spacing:-.01em}
.plate .big span{font-family:var(--sans);font-size:12px;color:var(--muted)}
.plate .langs{gap:0;margin:14px 0 6px}
.plate .langs span{border:0;background:transparent;padding:0 12px 0 0;
  font-family:var(--sans);font-size:12.5px;color:var(--muted)}
.plate .rec{font-family:var(--sans);font-size:12.5px;line-height:1.8;color:var(--ink2)}
.plate .rec b{font-family:var(--sans);font-size:11px;color:var(--acc)}
.plate .rec div{border-top:1px solid var(--line);padding:7px 0}
.case-no{display:none}
.stamp{border:0;padding:0;font-family:var(--sans);font-size:12px;letter-spacing:0;
  color:var(--muted)}
.archive h3{font-family:var(--serif);font-size:32px;font-weight:400}
.readme-quote{font-family:var(--serif);font-size:16px;color:var(--ink2);
  border-left:2px solid var(--acc);padding-left:14px}
.how{font-family:var(--sans);font-size:13.5px;line-height:1.8}
.how li{border-top:1px solid var(--line);padding:9px 0 9px 18px}
.how li::before{content:"·";color:var(--acc);left:2px}
.case-link{font-family:var(--sans);font-size:12px;letter-spacing:0;color:var(--ink2)}

/* index */
.filters{margin:26px 0 8px;gap:24px}
.filter{border:0;padding:4px 0;font-family:var(--sans);font-size:13px;color:var(--muted);
  border-bottom:1px solid transparent}
.filter.on{background:transparent;color:var(--ink);border-bottom-color:var(--ink)}
.filter.on span{color:var(--muted)}
.filter:hover:not(.on){background:transparent;color:var(--ink)}
.index-table th{font-family:var(--sans);font-size:12px;letter-spacing:0;color:var(--muted);
  border-bottom:1px solid var(--ink);padding:10px 8px;white-space:nowrap}
.index-table td{border-bottom:1px solid var(--line);padding:12px 8px;font-size:14px}
.index-table tbody tr:hover{background:transparent}
.t-name{font-weight:500}
.t-stack,.t-loc,.t-status,.t-no{font-family:var(--mono);font-size:11.5px}
.index-note{font-family:var(--sans);font-size:12px}

/* numbers: captions above charts, no cards */
.num-grid{gap:56px 64px;margin-top:52px}
.num-panel{border:0;background:transparent;padding:0;
  border-top:1px solid var(--ink);padding-top:18px}
.num-grid > .num-panel:first-child{border-top:0;padding-top:0}
.num-panel h3{font-family:var(--sans);font-size:13px;letter-spacing:0;color:var(--ink);
  font-weight:600;margin-bottom:20px}
.num-panel h3 b{font-weight:400;color:var(--muted)}
.stack{border:0;height:12px}
.lang-bar{border:0;height:22px}
.lang-bar i+i{border-left:2px solid var(--paper)}
.bar-track{border:0;height:7px;background:var(--paper2)}
.bar-track i{background:var(--ink)}
.bar-name{font-family:var(--sans);font-size:13px;width:170px}
.bar-val{font-family:var(--mono)}
.lang-legend div{font-family:var(--sans);font-size:12.5px}
.hour-chart{height:132px}
.hour-bar{background:var(--ink)}
.hour-bar.peak{background:var(--acc)}
.heat-panel{margin-top:32px}
.heat-wrap{border:0;background:transparent;padding:0}
.cell{background:var(--paper2)}
.clock .c{background:var(--paper2)}
.month-col i{background:var(--ink)}
.month-col.peak i{background:var(--acc)}
.clock .c.l1,.cell.l1{background:#ddd6c4}
.clock .c.l2,.cell.l2{background:#a89f88}
.clock .c.l3,.cell.l3{background:#5c554a}
.clock .c.l4,.cell.l4{background:var(--ink)}
.lc-track{border:0;background:var(--paper2)}
.chips-cloud span{border:0;background:transparent;padding:0 14px 0 0;
  font-family:var(--sans);font-size:13px;color:var(--ink2)}
.chips-cloud b{font-weight:400;color:var(--muted)}
.pair{border:0;height:12px}
.q-stack{border:0}
.mini-stats b{font-family:var(--serif);font-size:28px;font-weight:400}
.mini-stats span{font-family:var(--sans);font-size:12px}
.file-line{border-top:1px solid var(--line)}
.file-path{font-size:12px}
.sub-head{font-family:var(--sans);font-size:12px;letter-spacing:0}
.year-span{font-family:var(--sans);font-size:12px}

/* about + footer */
.about{border:0;background:transparent;padding:0}
.about ul{font-family:var(--sans);font-size:14px}
.about li{border-top:1px solid var(--line);padding:10px 0 10px 18px}
.about li::before{content:"·";color:var(--acc);left:2px}
.quote{font-family:var(--serif);font-size:28px;border-left:2px solid var(--acc)}
footer{border-top:1px solid var(--line);margin-top:88px;padding:24px 0 44px}
.foot-in{max-width:1040px;padding:0 56px;font-family:var(--sans);font-size:12px}

/* one quiet load fade; everything else stays still like print */
@keyframes cy-fade{from{opacity:0}to{opacity:1}}
main{animation:cy-fade .24s ease both}
.rail-nav a,.next-link .name{transition:color .18s ease}
.repo-search{margin-left:auto;background:transparent;border:0;
  border-bottom:1px solid var(--line);font-family:var(--sans);font-size:13px;
  padding:4px 2px;color:var(--ink);outline:none;min-width:200px}
.repo-search::placeholder{color:var(--muted)}
.rv,.rv-line{opacity:1!important;transform:none!important;transition:none!important}
.sec-line,.bar-track i,.hour-bar,.month-col i{transform:none!important;opacity:1!important}
@media (prefers-reduced-motion: reduce){
  main{animation:none}
}
@media print{
  .rail,.to-top,.next-link,.filters,.repo-search{display:none!important}
  body{padding-left:0;background:#fff;color:#000;
    -webkit-print-color-adjust:exact;print-color-adjust:exact}
  main{animation:none!important}
  .wrap{max-width:none;padding:0}
  .hero{padding-top:0}
  #records,#archives,#index,#numbers,#about{break-before:page}
  .sec-head{border-color:#000}
  a{color:inherit;text-decoration:none}
}
@page{margin:16mm}
#tip{border:1px solid var(--line);box-shadow:none;background:var(--paper);
  font-family:var(--sans);font-size:12px}

@media(max-width:900px){
  body{padding-left:0}
  .rail{position:sticky;width:auto;height:auto;flex-direction:row;align-items:center;
    justify-content:space-between;padding:16px 22px;border-right:0;
    border-bottom:1px solid var(--line)}
  .rail-nav,.rail-foot,.rail-year{display:none}
  .wrap{max-width:100%;padding:0 22px}
  .hero{padding:56px 0 0}
  .cover-year{font-size:clamp(96px,22vw,140px)}
  h1{font-size:38px}
  .hero-stats{grid-template-columns:1fr 1fr}
  .foot-in{max-width:100%;padding:0 22px}
  .records{grid-template-columns:repeat(2,1fr);column-gap:32px}
}
@media(max-width:640px){
  .wrap,.nav,.foot-in{padding-left:22px;padding-right:22px}
  .nav-links{display:none}
  h1{font-size:44px}
  .hero-stats{grid-template-columns:1fr 1fr;padding:0 20px}
  .records{grid-template-columns:1fr}
}
</style>
"""

# ---- English edition -------------------------------------------------
EN_MAP = {
    "代码手账": "CodeYear",
    "年度代码报告": "Annual Code Report",
    "2026 年度代码报告": "2026 Annual Code Report",
    "回到顶部": "Back to top",
    "下一节": "Next",
    "顶部": "Top",
    "「git 不会说谎——": '"Git never lies —',
    "尤其是加了 --no-merges 的时候。": " especially with --no-merges.",
    "」": '"',
    "包括休眠的和没写 README 的": "Including dormant repos and those without a README",
    "git 里能查到的，不靠形容词": "What git can prove, without adjectives",
    "CodeYear · 代码手账": "CodeYear · Code Yearbook",
    "2026 年度代码报告 ·": "2026 Annual Code Report ·",
    "年度之最": "Yearly records",
    "仓库档案": "Repository profiles",
    "仓库索引": "Repository index",
    "全部仓库索引": "Full repository index",
    "数字": "Numbers",
    "数据分析": "Data analysis",
    "关于": "About",
    "2026 年，": "In 2026,",
    "次提交。": "commits.",
    "38.2 万": "382k",
    "次提交": "commits",
    "行代码变更": "lines changed",
    "个活跃日": "active days",
    "个仓库": "repositories",
    "先看几个最极端的数字": "",
    "最忙的一天": "Busiest day",
    "最忙的一周": "Busiest week",
    "最长连续": "Longest streak",
    "最长空窗": "Longest gap",
    "最大单次提交": "Largest commit",
    "最长的 commit": "Longest message",
    "天": "days",
    "行": "lines",
    "字符": "chars",
    "第一次提交": "First commit",
    "最后一次提交": "Last commit",
    "提交最多的三个仓库 · 时间线与热区": "",
    "种主要语言": "main languages",
    "活跃": "Active",
    "休眠": "Dormant",
    "进行中": "In progress",
    "全部": "All",
    "序号": "#",
    "仓库": "Repository",
    "一句话（README 原文）": "README first line",
    "栈": "Stack",
    "自有代码": "Own code",
    "最近提交": "Latest commit",
    "状态": "Status",
    "（README 没写简介）": "(No README description)",
    "月度节奏": "Monthly rhythm",
    "7×24 提交时钟": "7×24 commit clock",
    "周一": "Mon", "周二": "Tue", "周三": "Wed", "周四": "Thu",
    "周五": "Fri", "周六": "Sat", "周日": "Sun",
    "周末占 40%，深夜（22:00–05:00）占 44%。":
        "Weekend 40%; late night (22:00–05:00) 44%.",
    "代码构成": "Code composition",
    "语言构成": "Languages",
    "其他": "Other",
    "语言栈变化": "Language mix",
    "无提交": "No commits",
    "提交规模": "Commit size",
    "提交类型": "Commit types",
    "高频词": "Keywords",
    "消息长度": "Message length",
    "增删比": "Add/delete ratio",
    "删除最多的仓库": "Most deletions",
    "编码会话": "Coding sessions",
    "次会话": "sessions",
    "最长一次": "Longest",
    "最长一次里的提交": "Commits in longest",
    "平均一次": "Average",
    "仓库生命周期": "Repository lifecycle",
    "首次–最近": "First–latest",
    "仓库墓园": "Repo graveyard",
    "最常改的文件": "Most edited files",
    "2026 活跃热力图": "2026 activity",
    "少 → 多 · 框出今天": "Less → more · today outlined",
    "关于本报告": "About this report",
    "口径与方法": "Method",
    "这份报告由 CodeYear 在你的电脑上生成，代码从未离开这台机器。":
        "Generated by CodeYear on your computer. Your code never leaves it.",
    "只统计 2026 年的提交；合并提交（--no-merges）不计入。":
        "Only commits from 2026 are counted; merge commits (--no-merges) are excluded.",
    "同一项目出现在多个目录时只保留提交最多的一个；同一 commit 只计一次。":
        "Copies of the same project collapse into one; each commit is counted once.",
    "时间取 author date；跨时区协作时以提交者本地时间为准。":
        "Dates use author date, i.e. the author's local time.",
    "「自有代码」= 非空行；已剔除第三方库、生成工程与二进制。":
        "“Own code” means non-empty lines, excluding third-party libraries, generated projects, and binaries.",
    "CODEYEAR · 代码手账 2026": "CODEYEAR · 2026",
    "0–10 行": "0–10 lines",
    "10–100 行": "10–100 lines",
    "100–500 行": "100–500 lines",
    "500–2k 行": "500–2k lines",
    "2k+ 行": "2k+ lines",
    "0–20 字符": "0–20 chars",
    "20–40 字符": "20–40 chars",
    "40–80 字符": "40–80 chars",
    "80–160 字符": "80–160 chars",
    "160+ 字符": "160+ chars",
    "· 每个月的提交次数": "· commits per month",
    "· 星期几、几点提交最多": "· busiest weekday and hour",
    "· 哪些仓库写的代码最多": "· repos with the most code",
    "· 各种语言占了多少行": "· lines by language",
    "· 每个季度的语言占比": "· share by quarter",
    "· 每次提交改了多少行": "· lines changed per commit",
    "· 哪种类型的提交最多": "· which type appears most",
    "· 提交说明里最常出现的词": "· words in commit messages",
    "· 提交说明一般写多长": "· how long commit messages are",
    "· 写了多少、删了多少": "· lines added vs deleted",
    "· 每个仓库今年活跃的时间段": "· active span per repo",
    "· 超过 30 天没动的仓库": "· repos untouched for 30+ days",
    "· 每个文件改了多少行": "· changed lines per file",
    "· 哪天有提交": "· days with commits",
    "· 一次连续写多久": "· how long one sitting lasts",
    "· 峰值 23:00": "· peak 23:00",
    "· 头部集中度（按行数）": "· concentration by lines",
    "· 按行变更估算": "· estimated by lines changed",
    "· 按季度占比": "· share by quarter",
    "· 小步快跑还是大爆炸": "· small steps or big bangs",
    "· commit message 里的口头禅": "· phrases in commit messages",
    "· 建设 vs 重构": "· building vs refactoring",
    "· 2026 活跃区间": "· 2026 active span",
    "· 改动热区（完整路径）": "· full paths",
}

EN_PATTERNS = [
    (r"扫描目录：(.*) · (\d+) 个仓库", r"Scan roots: \1 · \2 repositories"),
    (r"38\.2\s*万\s*行代码，53 个活跃日，10 个仓库。",
     r"382k lines of code, 53 active days, 10 repositories."),
    (r"(\d[\d,]*) 次提交", r"\1 commits"),
    (r"当前连续 (\d+) 天", r"Current streak: \1 days"),
    (r"(\d{4}-W\d+) · 起于 (\d{4}\.\d{2}\.\d{2})", r"\1 · from \2"),
    (r"首次提交 (.*) → 最近提交 (.*)", r"First \1 → latest \2"),
    (r"语言：(.*)", r"Languages: \1"),
    (r"最常改的文件：(.*)（(.*) 行变更）", r"Most edited: \1 (\2 lines changed)"),
    (r"提交 (\d+) 次（已按 hash 去重）", r"\1 commits (deduplicated by hash)"),
    (r"· 峰值 (\d+) 月 · (\d+) 次", r"· peak month \1 · \2 commits"),
    (r"· 约定式占 (\d+)%", r"· \1% conventional"),
    (r"· 平均 (\d+) 字符", r"· average \1 chars"),
    (r"· (\d+) 个仓库超过 30 天没动", r"· \1 repos untouched for 30+ days"),
    (r"· (\d+) 个活跃日", r"· \1 active days"),
    (r"其余 (\d+) 个仓库 · (.*)", r"Other \1 repos · \2"),
    (r"新增 (.*) 行", r"Added \1 lines"),
    (r"删除 (.*) 行", r"Deleted \1 lines"),
    (r"删除 / 新增 = (\d+)%。最大的一次删除 (.*) 行（(.*)，(.*)）。",
     r"Deletions / additions = \1%. Largest deletion: \2 lines (\3, \4)."),
    (r"平均每条 (\d+) 字符。", r"Average \1 characters."),
    (r"最长的一条见「年度之最」。", 'Longest message in "Yearly records".'),
    (r"16 小时 01 分", r"16h 01m"),
    (r"(\d+) 分钟", r"\1 min"),
    (r"最后提交 (.*)", r"Last commit \1"),
    (r"(\d+) 天", r"\1 days"),
    (r"扫描范围 (.*) · (.*)", r"Scanned \1 · \2"),
    (r"由 CodeYear 在本机生成 · (.*) · 代码从未离开这台电脑",
     r"Generated locally by CodeYear · \1 · your code never left this machine"),
    (r"只统计你本人作者的提交（(.*)）；已过滤 (\d+) 次他人提交。",
     r"Only your commits (\1); \2 commits by others filtered out."),
    (r"间隔 ≤ 2 小时的提交算一次会话。最长一次：(.*) → (.*)。",
     r"Commits within 2 hours count as one session. Longest: \1 → \2."),
]

_block_re = re.compile(r"<(style|script)\b.*?</\1>", re.S | re.I)


def _translate_core(core: str) -> str | None:
    if core in EN_MAP:
        return EN_MAP[core]
    for pattern, repl in EN_PATTERNS:
        m = re.fullmatch(pattern, core)
        if m:
            return m.expand(repl)
    return None


def _wan_convert(text: str) -> str:
    def repl(m):
        value = float(m.group(1)) * 10
        if value >= 100:
            return f"{value:.0f}k"
        return f"{value:g}k"
    return re.sub(r"(\d+(?:\.\d+)?)\s*万", repl, text)


def _translate_node(value: str) -> str:
    lead = value[: len(value) - len(value.lstrip())]
    trail = value[len(value.rstrip()):]
    core = value.strip()
    if not core:
        return value
    en = _translate_core(core)
    if en is None:
        en = _wan_convert(core)
    else:
        en = _wan_convert(en)
    return lead + en + trail


WEEK = {"周一": "Mon", "周二": "Tue", "周三": "Wed", "周四": "Thu",
        "周五": "Fri", "周六": "Sat", "周日": "Sun"}
MONTH = {i: m for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
     "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}


def _translate_tip(value: str) -> str:
    v = _wan_convert(htmlmod.unescape(value))
    v = re.sub(r"(周[一二三四五六日])\s*(\d{2}:\d{2}) · (\d+) 次提交",
               lambda m: f"{WEEK[m.group(1)]} {m.group(2)} · {m.group(3)} commits", v)
    v = re.sub(r"(\d+) 月 · (\d+) 次提交",
               lambda m: f"{MONTH[int(m.group(1))]} · {m.group(2)} commits", v)
    v = re.sub(r"(\d{4}-\d{2}-\d{2}) · (\d+) 次提交",
               lambda m: f"{m.group(1)} · {m.group(2)} commits", v)
    v = re.sub(r"(.*?) · (\d+)% · ([\d.,k]+) 行",
               lambda m: f"{m.group(1)} · {m.group(2)}% · {m.group(3)} lines", v)
    v = re.sub(r"(.*?) · ([\d.,k]+) 行变更",
               lambda m: f"{m.group(1)} · {m.group(2)} lines changed", v)
    v = re.sub(r"(.*?) · (\d+) 次提交",
               lambda m: f"{m.group(1)} · {m.group(2)} commits", v)
    v = re.sub(r"(\d+) 次提交", lambda m: f"{m.group(1)} commits", v)
    v = re.sub(r"([\d.,k]+) 行变更", lambda m: f"{m.group(1)} lines changed", v)
    v = re.sub(r"([\d.,k]+) 行", lambda m: f"{m.group(1)} lines", v)
    v = re.sub(r"(\d+) 个活跃日", lambda m: f"{m.group(1)} active days", v)
    v = re.sub(r"(\d+) 次", lambda m: f"{m.group(1)} times", v)
    v = v.replace("没有提交", "No commits").replace("无提交", "No commits")
    v = v.replace("最近的真实提交记录", "Recent real commits")
    v = v.replace("其他", "Other")
    return v


def translate_html(source: str) -> str:
    blocks = []

    def stash(m):
        blocks.append(m.group(0))
        return f"@@BLOCK{len(blocks) - 1}@@"

    text = _block_re.sub(stash, source)
    text = re.sub(r">([^<>]+)<",
                  lambda m: ">" + _translate_node(m.group(1)) + "<", text)
    text = re.sub(r"@@BLOCK(\d+)@@", lambda m: blocks[int(m.group(1))], text)
    text = re.sub(r'(data-tip|aria-label)="([^"]*)"',
                  lambda m: f'{m.group(1)}="{htmlmod.escape(_translate_tip(m.group(2)), quote=True)}"',
                  text)
    text = text.replace('<html lang="zh-CN">', '<html lang="en">')
    text = re.sub(r'<meta name="description" content="[^"]*">',
                  '<meta name="description" content="CodeYear annual code report - a local-first year in review.">',
                  text)
    text = text.replace('aria-label="回到顶部"', 'aria-label="Back to top"')
    return text

CAPTIONS = [
    (r"· 峰值 \d+ 月 · \d+ 次", "· 每个月的提交次数"),
    (r"· 峰值 \d{2}:\d{2}", "· 星期几、几点提交最多"),
    ("· 头部集中度（按行数）", "· 哪些仓库写的代码最多"),
    ("· 按行变更估算", "· 各种语言占了多少行"),
    ("· 按季度占比", "· 每个季度的语言占比"),
    ("· 小步快跑还是大爆炸", "· 每次提交改了多少行"),
    (r"· 约定式占 \d+%", "· 哪种类型的提交最多"),
    ("· commit message 里的口头禅", "· 提交说明里最常出现的词"),
    (r"· 平均 \d+ 字符", "· 提交说明一般写多长"),
    ("· 建设 vs 重构", "· 写了多少、删了多少"),
    (r"· \d{4} 活跃区间", "· 每个仓库今年活跃的时间段"),
    (r"· \d+ 个仓库超过 30 天没动", "· 超过 30 天没动的仓库"),
    ("· 改动热区（完整路径）", "· 每个文件改了多少行"),
    (r"· \d+ 个活跃日", "· 哪天有提交"),
]


def _fix_h3(m):
    inner = m.group(1)
    for pattern, repl in CAPTIONS:
        inner = re.sub(pattern, repl, inner)
    return f"<h3>{inner}</h3>"


def decorate(source: str, stats: ReportStats) -> str:
    year = stats.year
    commits = stats.commit_count
    lines = stats.lines_changed
    active = stats.active_days
    repos = stats.repo_count
    html = source

    cover = (
        f'<div class="cover-year">{year}</div>'
        f'<p class="scan-roots">扫描目录：{htmlmod.escape(stats.root)}'
        f' · {repos} 个仓库</p>'
        f'<h1><em>{_comma(commits)}</em> 次提交。</h1>'
    )
    html = re.sub(
        r'<h1 class="rv-line">.*?</h1>',
        lambda _match: cover,
        html, count=1, flags=re.S,
    )
    html = re.sub(
        r'<p class="lede rv"[^>]*>.*?</p>',
        f'<p class="lede">{_human(lines)} 行代码，{active} 个活跃日，'
        f'{repos} 个仓库。</p>',
        html, count=1, flags=re.S,
    )
    hero_stats = f"""
<div class="hero-stats">
  <div class="hs"><b>{_comma(commits)}</b><span>次提交</span></div>
  <div class="hs"><b>{_human(lines)}</b><span>行代码变更</span></div>
  <div class="hs"><b>{active}</b><span>个活跃日</span></div>
  <div class="hs"><b>{repos}</b><span>个仓库</span></div>
</div>"""
    compare_html = ""
    previous = stats.previous
    if previous:
        def _delta(value: int, pct: float | None) -> str:
            text = f"{value:+,}" if value else "0"
            if pct is not None:
                text += f"（{pct:+.0%}）"
            return text

        compare_html = (
            f'<p class="compare-line">同比 {previous["year"]}：'
            f'提交 {_delta(previous["commits"], previous["commits_pct"])} · '
            f'行数 {_delta(previous["lines"], previous["lines_pct"])} · '
            f'活跃 {_delta(previous["active_days"], None)} 天 · '
            f'仓库 {_delta(previous["repos"], None)}'
            "</p>"
        )
    html = re.sub(
        r'<div class="hero-stats">.*?<p class="scroll-hint[^>]*>.*?</p>',
        hero_stats + compare_html, html, count=1, flags=re.S,
    )
    rail = f"""<aside class="rail">
  <div>
    <div class="rail-brand"><i></i>代码手账</div>
    <div class="rail-year">{year} 年度代码报告</div>
    <nav class="rail-nav">
      <a href="#records">年度之最</a>
      <a href="#archives">仓库档案</a>
      <a href="#index">仓库索引</a>
      <a href="#numbers">数据分析</a>
      <a href="#about">关于</a>
    </nav>
  </div>
  <div class="rail-foot">
    <a class="lang" href="codeyear-{year}-en.html">English</a>
    <a class="top" href="#top">回到顶部 <span>&uarr;</span></a>
  </div>
</aside>"""
    html = re.sub(r'<header>.*?</header>', '', html, count=1, flags=re.S)
    html = html.replace('<body>', '<body>\n' + rail, 1)

    nexts = [
        ("records", "archives", "仓库档案", "下一节", "&rarr;"),
        ("archives", "index", "仓库索引", "下一节", "&rarr;"),
        ("index", "numbers", "数据分析", "下一节", "&rarr;"),
        ("numbers", "about", "关于本报告", "下一节", "&rarr;"),
        ("about", "top", "回到顶部", "", "&uarr;"),
    ]
    for sid, nid, label, kicker, arrow in nexts:
        kick = f'<span class="next-kicker">{kicker}</span>' if kicker else ""
        link = (f'<a class="next-link" href="#{nid}">{kick}'
                f'<span class="name">{label} <i>{arrow}</i></span></a>')
        html = re.sub(
            rf'(<section id="{sid}">)(.*?)(</section>)',
            lambda m: m.group(1) + m.group(2) + link + m.group(3),
            html, count=1, flags=re.S,
        )

    html = html.replace(
        '<script>',
        '<a class="to-top" href="#top" aria-label="回到顶部">&uarr; '
        '<span>顶部</span></a>\n<script>', 1,
    )
    html = html.replace('</body>', """<script>
(()=>{
  const t=document.querySelector('.to-top');
  const f=()=>t.classList.toggle('show',scrollY>700);
  addEventListener('scroll',f,{passive:true});f();
  const links=[...document.querySelectorAll('.rail-nav a')];
  const byId=new Map(links.map(a=>[a.getAttribute('href').slice(1),a]));
  const spy=new IntersectionObserver(es=>{
    es.forEach(e=>{
      if(!e.isIntersecting)return;
      links.forEach(a=>a.classList.remove('active'));
      const a=byId.get(e.target.id);
      if(a)a.classList.add('active');
    });
  },{rootMargin:'-25% 0px -65% 0px'});
  document.querySelectorAll('section[id]').forEach(s=>spy.observe(s));
})();
</script>
</body>""")
    html = re.sub(r"<h3>(.*?)</h3>", _fix_h3, html, flags=re.S)
    return html.replace('</head>', CSS + '</head>')


def to_english(source: str, stats: ReportStats) -> str:
    year = stats.year
    en_map = dict(EN_MAP)
    en_map[f"{year} 年度代码报告"] = f"{year} Annual Code Report"
    en_map[f"CODEYEAR · 代码手账 {year}"] = f"CODEYEAR · {year}"
    EN_MAP.update(en_map)

    html = re.sub(
        r'<p class="lede">.*?</p>',
        f'<p class="lede">{_en_human(stats.lines_changed)} lines of code, '
        f'{stats.active_days} active days, {stats.repo_count} repositories.</p>',
        source, count=1, flags=re.S,
    )
    html = html.replace(
        f'href="codeyear-{year}-en.html">English<',
        f'href="codeyear-{year}.html">中文<',
    )
    html = re.sub(r'<meta name="description" content="[^"]*">',
                  '<meta name="description" content="CodeYear annual code report '
                  '- a local-first year in review.">', html)
    html = translate_html(html)
    html = re.sub(r'<title>.*?</title>',
                  f'<title>CodeYear {year} · Annual Code Report</title>',
                  html, count=1, flags=re.S)
    return html
