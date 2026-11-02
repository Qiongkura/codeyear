#!/usr/bin/env python3
"""Generate the Qiongkura code portfolio page.

Design direction: "engineering field-notes on paper" — warm paper background,
ink text, one vermilion accent, serif display + mono data, visible hairlines,
square corners. Real data from local git history, no third-party JS.

Outputs out-portfolio/index.html (ready for GitHub Pages).
"""

from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from html import escape
from pathlib import Path

ROOT = Path(r"I:\projects")
CY = ROOT / "codeyear"
OUT = CY / "out-portfolio"
ASSETS = OUT / "assets"
OUT.mkdir(parents=True, exist_ok=True)
ASSETS.mkdir(parents=True, exist_ok=True)

STATS = json.loads((CY / "out-all" / "codeyear-2026.json").read_text(encoding="utf-8"))

IMAGE_SOURCES = {
    "beamng.png": ROOT / "beamng-autopilot" / "docs" / "monitor_shot_top.png",
    "audiotransfer.png": ROOT / "audiotransfer" / "docs" / "studio.png",
    "focus.png": ROOT / "focus-time-tracker" / "docs" / "统计.png",
    "audio-visualizer.png": ROOT / "audio-visualizer" / "docs" / "screenshot.png",
    "marble.png": ROOT / "marble-machine" / "docs" / "screenshot.png",
    "digital-life.png": ROOT / "digital-life-chat" / "preview.png",
    "my-profile.webp": ROOT / "my-profile" / "assets" / "racing-frame.webp",
    "codeyear.png": ROOT / "codeyear" / "docs" / "sample.png",
}
for name, src in IMAGE_SOURCES.items():
    if src.exists():
        shutil.copy2(src, ASSETS / name)

# Real commit subjects harvested from local repos (2026-08 .. 2026-11).
TICKER = [
    ("audiotransfer", "Initial audio-to-buzzer converter and STM32 OLED player"),
    ("audiotransfer", "Protect vocal sections and add instrumental melody mode"),
    ("audiotransfer", "Cross-check sung pitch and regularize rapid vocal note changes"),
    ("audiotransfer", "Add note-level singing transcription and keep caches on project drive"),
    ("audiotransfer", "Unify automatic melody conversion across songs and preserve pitch timing"),
    ("audiotransfer", "Record verified STM32 upload and on-board pause tests"),
    ("marble-machine", "Critical fix: play-state freeze from undeclared platform var in renderPlay"),
    ("marble-machine", "Douyin capsule rect offset correction (+21css) for HUD icon row alignment"),
    ("marble-machine", "Age rating badge: embed the official CADPA 8+ badge as base64"),
    ("marble-machine", "Menu compliance block: smaller CADPA badge beside the text"),
    ("audio-visualizer", "修复：关窗后仍会触发已排队的定时器，刷 invalid command name"),
    ("audio-visualizer", "修复 test_keeps_only_latest_frame 的竞态"),
    ("focus-time-tracker", "CI：windows-latest 上跑 Python 3.10/3.12 矩阵测试"),
    ("focus-time-tracker", "README：补 CI 徽章与 Release 下载入口，CI 说明改为实际状态"),
    ("my-profile", "Add one-command web deploy script: md5-diff sync to Aliyun ECS"),
    ("SmartCar-STM32", "Add STM32 smart car and remote controller modules"),
]

CASES = [
    {
        "no": "01",
        "name": "BeamNG Autopilot",
        "stamp": "研究 · 未完",
        "fig": "fig.01 — 训练监控：车道线分割模型 accuracy 99.7%",
        "img": "beamng.png",
        "why": "想真正搞明白「车怎么自己开」，纸上看论文不如在仿真里从零造一遍。这是目前最大的一块代码，也是唯一一个我给自己设了验收门的项目。",
        "how": [
            "感知 / 决策 / 控制三层架构，再向端到端模仿学习推进",
            "车道线分割模型长期迭代，训练监控、数据回流、离线验证全套自建",
            "自设 strict 闭环验收门：不合格的模型不上线、不写进结论",
        ],
        "metrics": [("165.9k", "行 Python"), ("964", "commits"), ("224", "篇实验文档")],
        "honest": "strict 闭环验收 4 次 0/4 —— 不合格就是不合格，研究还在继续。",
        "link": "https://github.com/Qiongkura/BeamNG-autopilot",
        "link_label": "GitHub ↗",
    },
    {
        "no": "02",
        "name": "AudioTransfer Studio",
        "stamp": "v0.5.0",
        "fig": "fig.02 — 桌面工作台：拖入歌曲，一键转换、试听、烧录",
        "img": "audiotransfer.png",
        "why": "STM32 蜂鸣器的示例永远是单音 demo。我想让它唱一首完整的歌——有人声、有换气、有间奏的那种。",
        "how": [
            "Demucs 分离人声，RMVPE + CREPE 双模型交叉校验音高",
            "连续旋律路径判定：换气不接伴奏、颤音不碎成新音符",
            "自动生成 STM32 固件并一键烧录，六首完整录音统一验证并留档",
        ],
        "metrics": [("8.3k", "行 Python"), ("6", "首全曲验证"), ("1", "键烧录")],
        "honest": "模型权重是 CC BY-NC-SA，所以这个项目明确标注非商用。",
        "link": "https://github.com/Qiongkura/audiotransfer",
        "link_label": "GitHub ↗",
    },
    {
        "no": "03",
        "name": "Focus Time Tracker",
        "stamp": "成熟",
        "fig": "fig.03 — 统计页：每小时分布与近 7 天趋势",
        "img": "focus.png",
        "why": "想知道时间到底去哪了，但不想把屏幕使用记录交给任何一家云。",
        "how": [
            "Win32 API 采样前台窗口，纯 ctypes，零第三方采集依赖",
            "游戏按「启动器 / 安装目录」规则引擎识别；网站读浏览器本地历史库匹配",
            "SQLite WAL 本地存储 + 托盘常驻，CI 跑 Python 3.10/3.12 矩阵",
        ],
        "metrics": [("7.4k", "行 Python"), ("686", "个应用识别"), ("100%", "本地，不联网")],
        "honest": "所有数据都在本机一个 SQLite 文件里，删掉即消失。",
        "link": "https://github.com/Qiongkura/Focus-time-tracker",
        "link_label": "GitHub ↗",
    },
]

# Full index table. cat: research / embedded / tools / web / writing / archive
TABLE = [
    ("beamng-autopilot", "BeamNG 自动驾驶研究", "Python · BeamNGpy · PyTorch", "165.9k", "研究中", "2026", "research",
     "https://github.com/Qiongkura/BeamNG-autopilot"),
    ("audiotransfer", "歌曲 → 主旋律 → STM32 固件", "Python · Demucs · RMVPE", "8.3k", "v0.5.0", "2026", "tools",
     "https://github.com/Qiongkura/audiotransfer"),
    ("focus-time-tracker", "屏幕使用时间统计", "Python · Win32 · SQLite", "7.4k", "成熟", "2026", "tools",
     "https://github.com/Qiongkura/Focus-time-tracker"),
    ("my-profile", "个人主页 qiongkura.xyz", "JavaScript · 静态站", "13.0k", "已上线", "2026", "web",
     "https://github.com/Qiongkura/my-profile"),
    ("SmartCar / SmartCar-STM32", "智能小车 + 遥控器", "C · STM32F103 · PlatformIO", "12.4k", "已完成", "2026", "embedded",
     "https://github.com/Qiongkura/SmartCar-STM32"),
    ("audio-visualizer", "系统声音实时可视化", "Python · WASAPI", "2.4k", "exe 已发布", "2026", "tools",
     "https://github.com/Qiongkura/audio-visualizer"),
    ("netease-music-parser", "网易云分享链接 → 播放卡片", "JavaScript · 零依赖", "9.3k", "可发布", "2026", "web", None),
    ("marble-machine", "弹珠机 Canvas 游戏", "JavaScript · 三端", "3.0k", "三端可玩", "2026", "web", None),
    ("pc-maintenance-sim", "3D 电脑维护教学游戏", "JavaScript · Three.js", "3.5k", "P0 原型", "2026", "web", None),
    ("flightfix v64–v69", "ESP32 迷你无人机飞控修改", "Arduino · C++ · GPL3", "2.5k", "调试中", "2026", "embedded", None),
    ("codeyear", "本地 git 年度报告", "Python · Pillow", "2.0k", "v0.1", "2026", "tools", None),
    ("digital-life-chat / exact", "流浪地球风格终端 UI", "CSS · JS", "5.9k", "UI 实验", "2026", "web", None),
    ("pcb / ultrasonic-ui", "超声相控阵 PCB + 数据分析", "Altium · Python", "0.5k", "硬件 + 脚本", "2026", "embedded", None),
    ("DQNsnake / autosnake", "Double DQN + PER 贪吃蛇", "Python · Java · PyTorch", "1.7k", "实验", "2026", "web",
     "https://github.com/Qiongkura/DQN-Reinforcement-Learning-Snake"),
    ("urban-novel-writer", "300 万字小说创作工作台", "Markdown · LLM 工作流", "2.0k 文档", "写作中", "2026", "writing", None),
    ("biotech_ppt", "结课汇报 PPT 生成", "JavaScript · pptxgenjs", "0.6k", "完成", "2026", "web", None),
    ("beamng-dlss5-setup", "DLSS5 配置与模型验证", "Python", "1.3k", "工具", "2026", "tools", None),
    ("CodexWork / 副本仓", "固件修复工作区与备份", "C · Python", "96.9k 副本", "归档候选", "2026", "archive", None),
]

CATS = [
    ("all", "全部"),
    ("research", "研究"),
    ("embedded", "嵌入式"),
    ("tools", "工具"),
    ("web", "Web & 游戏"),
    ("writing", "写作"),
    ("archive", "归档"),
]

NEXT = [
    ("2026.11", "CodeYear v0.2", "打包 exe、英文 README、30 秒 demo。年底总结季是它唯一的窗口期。"),
    ("2026.11–12", "软著第一批", "AudioTransfer + Focus Time Tracker：60 页源码 + 用户手册，走正规代理。"),
    ("2026.12", "BeamNG 收口", "给 strict gate 一个明确结论：要么过，要么把结论如实写进论文。副本仓归档。"),
]

CSS = r"""
:root{
  --paper:#f4f1e8; --paper2:#eceadf; --ink:#171512; --ink2:#403c33;
  --muted:#6f6a5e; --line:#d9d3c2; --line2:#c8c1ac;
  --acc:#d4491f; --acc2:#b23a15;
  --serif:"Fraunces","Noto Serif SC","Songti SC",Georgia,serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;
  --mono:"IBM Plex Mono",Consolas,"SFMono-Regular",Menlo,monospace;
  --ease:cubic-bezier(.22,1,.36,1);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15px;line-height:1.7;-webkit-font-smoothing:antialiased}
::selection{background:var(--acc);color:var(--paper)}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.5;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='140' height='140'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/%3E%3CfeColorMatrix values='0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 .035 0'/%3E%3C/filter%3E%3Crect width='140' height='140' filter='url(%23n)'/%3E%3C/svg%3E")}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;opacity:.55;
  background-image:linear-gradient(var(--line) 1px,transparent 1px);
  background-size:100% 220px;
  mask-image:linear-gradient(180deg,transparent,#000 140px,#000 calc(100% - 200px),transparent)}
.wrap{max-width:1160px;margin:0 auto;padding:0 28px;position:relative;z-index:1}
.mono{font-family:var(--mono)}
a{color:inherit}
h1,h2,h3{margin:0;font-weight:600}

/* progress */
#progress{position:fixed;top:0;left:0;height:2px;width:0;background:var(--acc);z-index:99}

/* nav */
header{position:sticky;top:0;z-index:50;background:rgba(244,241,232,.88);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.nav{max-width:1160px;margin:0 auto;padding:0 28px;height:58px;display:flex;
  align-items:center;justify-content:space-between;gap:24px}
.logo{font-family:var(--mono);font-size:13px;letter-spacing:.22em;text-decoration:none;
  display:inline-flex;align-items:center;gap:9px}
.logo i{width:9px;height:9px;background:var(--acc);display:inline-block}
.nav-links{display:flex;gap:22px;font-size:13px}
.nav-links a{color:var(--ink2);text-decoration:none;font-family:var(--mono);font-size:12px;
  letter-spacing:.04em}
.nav-meta{display:flex;align-items:center;gap:16px;font-family:var(--mono);font-size:11px;
  color:var(--muted)}
.nav-gh{color:var(--ink);text-decoration:none;border:1px solid var(--ink);padding:5px 11px;
  font-size:11px;letter-spacing:.06em;transition:background .2s,color .2s}
.nav-gh:hover{background:var(--ink);color:var(--paper)}

/* links with animated underline */
.u{color:var(--ink);text-decoration:none;
  background:linear-gradient(var(--acc),var(--acc)) no-repeat 0 100%/0 2px;
  transition:background-size .35s var(--ease);padding-bottom:2px}
.u:hover{background-size:100% 2px}

/* hero */
.hero{padding:86px 0 64px;display:grid;grid-template-columns:1.25fr .75fr;gap:48px;
  align-items:end}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.22em;color:var(--acc);
  margin:0 0 22px}
h1{font-family:var(--serif);font-size:clamp(46px,6.4vw,84px);line-height:1.06;
  letter-spacing:-.02em;font-weight:600}
h1 em{font-style:normal;color:var(--acc)}
.lede{margin:26px 0 0;font-size:16.5px;line-height:1.85;color:var(--ink2);max-width:600px}
.lede b{color:var(--ink);font-weight:600}
.cta-row{display:flex;gap:12px;margin-top:34px}
.btn{display:inline-flex;align-items:center;gap:10px;padding:12px 22px;background:var(--ink);
  color:var(--paper);font-size:13px;font-weight:600;text-decoration:none;
  font-family:var(--mono);letter-spacing:.06em;transition:background .2s;will-change:transform}
.btn:hover{background:var(--acc)}
.btn.ghost{background:transparent;color:var(--ink);border:1px solid var(--ink)}
.btn.ghost:hover{background:var(--ink);color:var(--paper)}
.hero-stats{display:grid;grid-template-columns:1fr 1fr;border-left:1px solid var(--line)}
.hs{padding:18px 20px;border-bottom:1px solid var(--line)}
.hs:nth-child(odd){border-right:1px solid var(--line)}
.hs:nth-last-child(-n+2){border-bottom:0}
.hs b{display:block;font-family:var(--mono);font-size:30px;font-weight:500;
  letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.hs span{font-size:11px;color:var(--muted);font-family:var(--mono);letter-spacing:.06em}
.scroll-hint{font-family:var(--mono);font-size:10px;letter-spacing:.24em;color:var(--muted);
  margin-top:26px;display:flex;align-items:center;gap:12px}
.scroll-hint::after{content:"";flex:1;height:1px;background:var(--line)}

/* ticker */
.ticker{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);background:var(--ink);
  color:var(--paper);overflow:hidden;position:relative;z-index:1}
.ticker-inner{display:flex;align-items:center;height:46px}
.tick-label{flex:none;padding:0 18px;border-right:1px solid rgba(244,241,232,.25);
  font-family:var(--mono);font-size:10px;letter-spacing:.18em;display:flex;align-items:center;
  gap:8px;height:100%;background:var(--ink)}
.tick-label i{width:7px;height:7px;border-radius:50%;background:var(--acc);
  animation:pulse 1.6s ease-in-out infinite}
@keyframes pulse{50%{opacity:.25}}
.tick-viewport{flex:1;overflow:hidden;height:100%;display:flex;align-items:center;
  mask-image:linear-gradient(90deg,transparent,#000 40px,#000 calc(100% - 40px),transparent)}
.tick-track{display:flex;gap:44px;width:max-content;animation:tick 70s linear infinite;
  padding-left:44px}
.ticker:hover .tick-track{animation-play-state:paused}
@keyframes tick{to{transform:translateX(-50%)}}
.tick-item{display:flex;align-items:baseline;gap:10px;font-size:12.5px;white-space:nowrap}
.tick-item b{font-family:var(--mono);font-size:10px;color:var(--acc);font-weight:500;
  letter-spacing:.04em}

/* sections */
section{padding:86px 0 0;scroll-margin-top:70px}
.sec-head{display:flex;align-items:baseline;justify-content:space-between;gap:20px;
  flex-wrap:wrap;border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:8px}
.sec-index{font-family:var(--mono);font-size:10px;letter-spacing:.24em;color:var(--acc)}
.sec-head h2{font-family:var(--serif);font-size:34px;letter-spacing:-.01em}
.sec-sub{color:var(--muted);font-size:13.5px;font-family:var(--mono)}

/* case studies */
.case{display:grid;grid-template-columns:1.02fr .98fr;gap:44px;padding:44px 0;
  border-bottom:1px solid var(--line)}
.case.flip .case-media{order:2}
.case-media figure{margin:0}
.case-shot{margin:0;border:1px solid var(--ink);background:var(--paper2);overflow:hidden;
  transform-style:preserve-3d;
  transition:transform .18s ease-out,box-shadow .3s var(--ease)}
.case-shot img{display:block;width:100%;height:auto;transform:scale(1.001);
  transition:transform .8s var(--ease);will-change:transform}
.case:hover .case-shot img{transform:scale(1.025)}
.case:hover .case-shot{box-shadow:6px 6px 0 var(--ink)}
figcaption{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:10px;
  letter-spacing:.04em}
.case-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.case-no{font-family:var(--mono);font-size:12px;color:var(--acc);letter-spacing:.14em}
.stamp{font-family:var(--mono);font-size:10px;letter-spacing:.14em;border:1px solid var(--ink);
  padding:4px 10px;display:inline-flex;align-items:center;gap:7px}
.stamp i{width:6px;height:6px;background:var(--acc);display:inline-block}
.case h3{font-family:var(--serif);font-size:30px;letter-spacing:-.01em;margin-bottom:14px}
.case .why{color:var(--ink2);margin:0 0 16px}
.how{list-style:none;margin:0 0 20px;padding:0;font-family:var(--mono);font-size:12.5px;
  line-height:1.6}
.how li{padding:9px 0 9px 20px;border-top:1px dashed var(--line2);position:relative;color:var(--ink2)}
.how li::before{content:"—";position:absolute;left:0;color:var(--acc)}
.case-meta{display:flex;gap:26px;flex-wrap:wrap;margin-bottom:16px}
.case-meta span{font-size:11px;color:var(--muted);font-family:var(--mono)}
.case-meta b{display:block;font-family:var(--mono);font-size:21px;font-weight:500;
  color:var(--ink);letter-spacing:-.01em}
.honest{font-size:12.5px;color:var(--acc2);border-left:2px solid var(--acc);
  padding:4px 0 4px 12px;margin:0 0 18px;font-family:var(--mono)}
.case-link{font-family:var(--mono);font-size:12px;letter-spacing:.08em}

/* index table */
.filters{display:flex;gap:6px;flex-wrap:wrap;margin:20px 0 14px}
.filter{background:transparent;border:1px solid var(--ink);color:var(--ink);border-radius:0;
  padding:6px 12px;font-size:11.5px;cursor:pointer;font-family:var(--mono);letter-spacing:.04em;
  transition:background .15s,color .15s}
.filter span{color:var(--muted);margin-left:5px;font-size:10px}
.filter.on{background:var(--ink);color:var(--paper)}
.filter.on span{color:rgba(244,241,232,.6)}
.filter:hover:not(.on){background:var(--paper2)}
.index-table{width:100%;border-collapse:collapse;font-size:13px}
.index-table th{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--muted);
  text-align:left;font-weight:500;padding:9px 12px;border-bottom:2px solid var(--ink)}
.index-table td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}
.index-table tr{transition:background .15s}
.index-table tbody tr:hover{background:var(--paper2)}
.index-table .t-no{font-family:var(--mono);font-size:11px;color:var(--muted);width:34px}
.index-table .t-name{font-weight:600;white-space:nowrap}
.index-table .t-name a{text-decoration:none}
.index-table .t-name a:hover{color:var(--acc)}
.index-table .t-desc{color:var(--ink2)}
.index-table .t-stack{font-family:var(--mono);font-size:11px;color:var(--muted)}
.index-table .t-loc{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums}
.index-table .t-status{font-family:var(--mono);font-size:11px;white-space:nowrap}
.index-table .t-status.hot{color:var(--acc)}
.index-note{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:12px}

/* numbers */
.num-grid{display:grid;grid-template-columns:1.1fr .9fr;gap:26px;margin-top:34px}
.num-panel{border:1px solid var(--ink);padding:22px;background:var(--paper)}
.num-panel h3{font-family:var(--mono);font-size:10.5px;letter-spacing:.18em;color:var(--muted);
  font-weight:500;margin-bottom:18px}
.num-panel h3 b{color:var(--acc);font-weight:500}
.stack{display:flex;height:14px;border:1px solid var(--ink)}
.stack i{display:block;height:100%}
.stack-labels{display:flex;justify-content:space-between;font-size:10.5px;color:var(--muted);
  margin-top:8px;font-family:var(--mono)}
.bar-row{display:flex;align-items:center;gap:12px;margin:10px 0;font-size:12.5px}
.bar-name{width:130px;color:var(--ink2);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.bar-track{flex:1;height:10px;border:1px solid var(--ink);background:var(--paper)}
.bar-track i{display:block;height:100%;background:var(--ink);transform-origin:left;
  transform:scaleX(0);transition:transform 1s var(--ease)}
.in .bar-track i{transform:scaleX(1)}
.bar-val{width:52px;text-align:right;font-family:var(--mono);font-size:11px;color:var(--muted)}
.lang-bar{display:flex;height:26px;border:1px solid var(--ink);margin-bottom:14px}
.lang-bar i{display:block;height:100%;position:relative}
.lang-bar i+ i{border-left:1px solid var(--paper)}
.lang-legend{display:grid;grid-template-columns:1fr 1fr;gap:8px 20px;font-size:12px}
.lang-legend div{display:flex;align-items:center;gap:8px;color:var(--ink2);
  font-family:var(--mono);font-size:11.5px}
.lang-legend b{margin-left:auto;font-weight:500;color:var(--ink)}
.sq{width:9px;height:9px;flex:none}
.hour-chart{display:flex;align-items:flex-end;gap:3px;height:120px}
.hour-bar{flex:1;background:var(--ink);min-height:2px;transform-origin:bottom;
  transform:scaleY(0);transition:transform .8s var(--ease)}
.in .hour-bar{transform:scaleY(1)}
.hour-bar.peak{background:var(--acc)}
.hour-labels{display:flex;gap:3px;margin-top:8px;font-family:var(--mono);font-size:9px;
  color:var(--muted)}
.hour-labels span{flex:1;text-align:center}
.heat-panel{margin-top:26px}
.heat-wrap{width:max-content;max-width:100%;margin:0 auto;overflow-x:auto;padding:6px 2px 2px;
  border:1px solid var(--ink);background:var(--paper)}
.months{display:grid;grid-template-columns:repeat(12,1fr);font-family:var(--mono);font-size:9px;
  color:var(--muted);margin-bottom:6px}
.heat{display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,13px);
  grid-auto-columns:13px;gap:3px}
.cell{width:13px;height:13px;background:var(--paper2)}
.cell.out{background:transparent}
.cell.l1{background:#ddd6c4}.cell.l2{background:#a89f88}.cell.l3{background:#5c554a}
.cell.l4{background:var(--ink)}
.cell.l4.today{outline:2px solid var(--acc);outline-offset:1px}
.heat-legend{display:flex;align-items:center;justify-content:center;gap:4px;font-size:10px;
  color:var(--muted);margin-top:12px;font-family:var(--mono)}
.heat-legend .cell{width:10px;height:10px}
.num-note{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:16px;line-height:1.9}

/* next */
.next-list{margin-top:8px}
.next-row{display:grid;grid-template-columns:130px 220px 1fr;gap:20px;padding:22px 0;
  border-bottom:1px solid var(--line);align-items:baseline}
.next-when{font-family:var(--mono);font-size:12px;color:var(--acc)}
.next-what{font-family:var(--serif);font-size:19px}
.next-how{color:var(--ink2);font-size:13.5px}
.quote{margin:44px 0 0;padding:6px 0 6px 26px;border-left:3px solid var(--acc);
  font-family:var(--serif);font-size:26px;line-height:1.5;color:var(--ink)}
.quote small{display:block;font-family:var(--mono);font-size:10.5px;color:var(--muted);
  margin-top:10px;letter-spacing:.1em}

/* footer */
footer{border-top:2px solid var(--ink);margin-top:90px;padding:24px 0 44px}
.foot-in{max-width:1160px;margin:0 auto;padding:0 28px;display:flex;
  justify-content:space-between;gap:14px;flex-wrap:wrap;font-family:var(--mono);
  font-size:11px;color:var(--muted)}
.foot-in a{color:var(--ink);text-decoration:none}
.foot-in a:hover{color:var(--acc)}

/* reveal animation */
.rv{opacity:0;transform:translateY(20px);
  transition:opacity .75s var(--ease),transform .75s var(--ease);
  transition-delay:var(--d,0ms)}
.rv.in{opacity:1;transform:none}
.rv-line{opacity:0;transform:translateY(30px);
  transition:opacity .85s var(--ease),transform .85s var(--ease);
  transition-delay:var(--d,0ms)}
.rv-line.in{opacity:1;transform:none}
.sec-line{height:2px;background:var(--ink);transform:scaleX(0);transform-origin:left;
  transition:transform .9s var(--ease) .1s}
.sec-line.in{transform:scaleX(1)}

@media(max-width:920px){
  .hero{grid-template-columns:1fr;gap:36px;padding-top:56px}
  .hero-stats{border-left:0;grid-template-columns:repeat(4,1fr)}
  .hs{border-right:0!important;border-bottom:1px solid var(--line)}
  .hs:nth-last-child(-n+2){border-bottom:1px solid var(--line)}
  .case,.case.flip{grid-template-columns:1fr}
  .case.flip .case-media{order:0}
  .num-grid{grid-template-columns:1fr}
  .next-row{grid-template-columns:1fr;gap:6px;padding:18px 0}
}
@media(max-width:640px){
  .wrap,.nav,.foot-in{padding-left:20px;padding-right:20px}
  .hero-stats{grid-template-columns:1fr 1fr}
  .nav-links{display:none}
  h1{font-size:44px}
  .index-table .t-stack,.index-table .t-desc{display:none}
  .quote{font-size:21px}
}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
  .rv,.rv-line{opacity:1!important;transform:none!important;clip-path:none!important}
  .sec-line,.bar-track i,.hour-bar{transform:none!important;opacity:1!important}
  .tick-track{animation:none!important}
}
"""

JS = r"""
(function(){
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $  = (s,c)=> (c||document).querySelector(s);
  const $$ = (s,c)=> [...(c||document).querySelectorAll(s)];

  /* scroll progress */
  const bar = $('#progress');
  const onScroll = ()=>{
    const h = document.documentElement;
    const p = h.scrollTop / (h.scrollHeight - h.clientHeight || 1);
    if(bar) bar.style.width = (p*100).toFixed(2)+'%';
  };
  addEventListener('scroll', onScroll, {passive:true}); onScroll();

  /* live clock */
  const clock = $('#clock');
  const pad = n=> String(n).padStart(2,'0');
  const tick = ()=>{
    const d = new Date();
    clock.textContent = pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());
  };
  if(clock){ tick(); setInterval(tick, 1000); }

  /* reveal on scroll */
  const targets = $$('.rv, .rv-line, .sec-line');
  if(RM || !('IntersectionObserver' in window)){
    targets.forEach(el=>el.classList.add('in'));
  }else{
    const io = new IntersectionObserver(es=>{
      es.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target);} });
    },{threshold:.12, rootMargin:'0px 0px -40px 0px'});
    targets.forEach(el=>io.observe(el));
  }

  /* count up */
  const counters = $$('[data-count]');
  const run = el=>{
    const target = parseFloat(el.dataset.count);
    const dec = parseInt(el.dataset.dec||'0',10);
    const suffix = el.dataset.suffix||'';
    const sep = 'sep' in el.dataset;
    const dur = 1300, t0 = performance.now();
    const fmt = v=>{
      let s = v.toFixed(dec);
      if(sep) s = Number(s).toLocaleString('en-US');
      return s + suffix;
    };
    const step = now=>{
      const p = Math.min((now-t0)/dur, 1);
      const e = 1-Math.pow(1-p,3);
      el.textContent = fmt(target*e);
      if(p<1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  if(RM || !('IntersectionObserver' in window)){
    counters.forEach(el=>{
      const t = parseFloat(el.dataset.count), dec=parseInt(el.dataset.dec||'0',10);
      let s=t.toFixed(dec); if('sep' in el.dataset) s=Number(s).toLocaleString('en-US');
      el.textContent = s + (el.dataset.suffix||'');
    });
  }else{
    const cio = new IntersectionObserver(es=>{
      es.forEach(e=>{ if(e.isIntersecting){ run(e.target); cio.unobserve(e.target);} });
    },{threshold:.5});
    counters.forEach(el=>cio.observe(el));
  }

  /* table filter */
  const filters = $$('.filter');
  const rows = $$('.index-table tbody tr');
  const countEl = $('#row-count');
  filters.forEach(btn=>btn.addEventListener('click',()=>{
    filters.forEach(b=>b.classList.toggle('on', b===btn));
    const f = btn.dataset.filter;
    let n=0;
    rows.forEach(r=>{
      const show = f==='all' || r.dataset.cat===f;
      r.style.display = show ? '' : 'none';
      if(show) n++;
    });
    if(countEl) countEl.textContent = n+' / '+rows.length+' 项';
  }));

  /* subtle tilt on case shots */
  if(!RM && matchMedia('(pointer:fine)').matches){
    $$('.case-shot').forEach(box=>{
      box.addEventListener('mousemove', ev=>{
        const r = box.getBoundingClientRect();
        const x = (ev.clientX-r.left)/r.width - .5;
        const y = (ev.clientY-r.top)/r.height - .5;
        box.style.transform = 'perspective(900px) rotateY('+(x*2.4)+'deg) rotateX('+(-y*2.4)+'deg)';
      });
      box.addEventListener('mouseleave', ()=>{ box.style.transform=''; });
    });
    /* magnetic buttons */
    $$('.btn').forEach(btn=>{
      btn.addEventListener('mousemove', ev=>{
        const r = btn.getBoundingClientRect();
        const x = ev.clientX-r.left-r.width/2, y = ev.clientY-r.top-r.height/2;
        btn.style.transform = 'translate('+(x*.12)+'px,'+(y*.18)+'px)';
      });
      btn.addEventListener('mouseleave', ()=>{ btn.style.transform=''; });
    });
  }

  /* hero parallax removed: conflicts with reveal transform on h1 */
})();
"""


def build_ticker() -> str:
    items = "".join(
        f'<span class="tick-item"><b>{escape(repo)}</b>{escape(subject)}</span>'
        for repo, subject in TICKER
    )
    return f"""
    <div class="ticker" aria-label="最近的真实提交记录">
      <div class="ticker-inner">
        <div class="tick-label"><i></i>LIVE · GIT</div>
        <div class="tick-viewport">
          <div class="tick-track">{items}{items}</div>
        </div>
      </div>
    </div>
    """


def build_case(case: dict, flip: bool) -> str:
    metrics = "".join(
        f'<span><b>{escape(v)}</b>{escape(label)}</span>' for v, label in case["metrics"]
    )
    how = "".join(f"<li>{escape(item)}</li>" for item in case["how"])
    return f"""
    <article class="case{' flip' if flip else ''}">
      <div class="case-media">
        <figure>
          <div class="case-shot"><img src="assets/{escape(case["img"])}" alt="{escape(case["name"])}" loading="lazy"></div>
          <figcaption>{escape(case["fig"])}</figcaption>
        </figure>
      </div>
      <div class="case-body">
        <div class="case-top">
          <span class="case-no">№ {case["no"]}</span>
          <span class="stamp"><i></i>{escape(case["stamp"])}</span>
        </div>
        <h3>{escape(case["name"])}</h3>
        <p class="why">{escape(case["why"])}</p>
        <ul class="how">{how}</ul>
        <div class="case-meta">{metrics}</div>
        <p class="honest">{escape(case["honest"])}</p>
        <a class="u case-link" href="{escape(case["link"])}" target="_blank" rel="noopener">{escape(case["link_label"])}</a>
      </div>
    </article>
    """


def build_table() -> str:
    filters = "".join(
        f'<button class="filter{" on" if key == "all" else ""}" data-filter="{key}">'
        f'{label}<span>{sum(1 for t in TABLE if key == "all" or t[6] == key)}</span></button>'
        for key, label in CATS
    )
    rows = []
    for i, (name, desc, stack, loc, status, year, cat, link) in enumerate(TABLE, 1):
        name_html = (
            f'<a href="{escape(link)}" target="_blank" rel="noopener">{escape(name)} ↗</a>'
            if link else escape(name)
        )
        hot = ' class="t-status hot"' if status in ("研究中", "写作中", "调试中") else ""
        rows.append(
            f'<tr data-cat="{cat}">'
            f'<td class="t-no">{i:02d}</td>'
            f'<td class="t-name">{name_html}</td>'
            f'<td class="t-desc">{escape(desc)}</td>'
            f'<td class="t-stack">{escape(stack)}</td>'
            f'<td class="t-loc">{escape(loc)}</td>'
            f'<td class="t-status"{hot}>{escape(status)}</td>'
            f'<td class="t-stack">{year}</td>'
            f"</tr>"
        )
    return f"""
    <div class="filters">{filters}</div>
    <table class="index-table">
      <thead>
        <tr><th>NO</th><th>项目</th><th>一句话</th><th>栈</th><th>自有代码</th><th>状态</th><th>年</th></tr>
      </thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <p class="index-note"><span id="row-count">{len(TABLE)} / {len(TABLE)} 项</span>
      · 自有代码 = 非空行，已剔除第三方库、生成工程与重复副本；仓库副本（CodexWork 等）不计入总量。</p>
    """


def build_heatmap() -> str:
    daily = {date.fromisoformat(k): v for k, v in STATS["daily"].items()}
    start = date(2026, 1, 1)
    end = date(2026, 12, 31)
    grid_start = start - timedelta(days=start.weekday())
    grid_end = end + timedelta(days=6 - end.weekday())
    today = date.today()

    cells: list[str] = []
    cursor = grid_start
    while cursor <= grid_end:
        if cursor < start or cursor > end:
            cls, tip = "out", ""
        else:
            count = daily.get(cursor, 0)
            if count == 0:
                cls = "l0"
            elif count == 1:
                cls = "l1"
            elif count <= 3:
                cls = "l2"
            elif count <= 6:
                cls = "l3"
            else:
                cls = "l4"
            if cursor == today:
                cls += " today"
            tip = f"{cursor.isoformat()} · {count} 次提交"
        cells.append(f'<span class="cell {cls}" title="{escape(tip)}"></span>')
        cursor += timedelta(days=1)

    months = "".join(f"<span>{m:02d}</span>" for m in range(1, 13))
    legend = "".join(f'<span class="cell l{i}"></span>' for i in range(5))
    return f"""
    <div class="num-panel heat-panel">
      <h3>2026 活跃热力图 <b>· 58 个活跃日</b></h3>
      <div class="heat-wrap">
        <div class="months">{months}</div>
        <div class="heat">{''.join(cells)}</div>
      </div>
      <div class="heat-legend">{legend}<span style="margin-left:6px">少 → 多 · 框出今天</span></div>
    </div>
    """


def build_numbers() -> str:
    beamng_code = 165_917
    total_code = 239_907
    top_other = [
        ("My Profile", 12_971), ("SmartCar / STM32", 12_360),
        ("Netease Parser", 9_334), ("AudioTransfer", 8_348),
        ("Focus Tracker", 7_430), ("Digital Life", 5_872),
        ("PC Maintenance", 3_544), ("Marble Machine", 3_000),
    ]
    max_other = max(v for _, v in top_other)
    other_rows = "".join(
        f'<div class="bar-row"><span class="bar-name">{escape(name)}</span>'
        f'<div class="bar-track"><i style="width:{v / max_other * 100:.1f}%"></i></div>'
        f'<span class="bar-val">{v / 1000:.1f}k</span></div>'
        for name, v in top_other
    )
    langs = [("Python", 80, "#171512"), ("Web / JS", 14, "#d4491f"),
             ("C / Arduino", 5, "#8f8672"), ("其他", 1, "#c8c1ac")]
    lang_bar = "".join(f'<i style="width:{pct}%;background:{color}"></i>' for _n, pct, color in langs)
    lang_legend = "".join(
        f'<div><span class="sq" style="background:{color}"></span>{escape(name)}<b>{pct}%</b></div>'
        for name, pct, color in langs
    )
    repo = dict(STATS["repo_commits"])
    beamng_commits = repo.get("beamng-autopilot", 0)
    profile = repo.get("my-profile", 0)
    other = STATS["commit_count"] - beamng_commits - profile
    total = max(STATS["commit_count"], 1)
    b_pct, p_pct = beamng_commits / total * 100, profile / total * 100
    o_pct = 100 - b_pct - p_pct

    hours = STATS["by_hour"]
    max_hour = max(hours) or 1
    peak = hours.index(max_hour)
    hour_bars = "".join(
        f'<div class="hour-bar{" peak" if v == max_hour and v > 0 else ""}" '
        f'style="height:{max(v / max_hour * 100, 2):.1f}%" title="{h:02d}:00 · {v} 次提交"></div>'
        for h, v in enumerate(hours)
    )
    hour_labels = "".join(
        f"<span>{h:02d}</span>" if h in (0, 6, 12, 18, 23) else "<span></span>"
        for h in range(24)
    )
    return f"""
    <div class="num-grid">
      <div class="num-panel rv">
        <h3>代码构成 <b>· 一个项目占了 69%</b></h3>
        <div class="stack">
          <i style="width:{beamng_code / total_code * 100:.1f}%;background:var(--acc)"></i>
          <i style="width:{100 - beamng_code / total_code * 100:.1f}%;background:var(--ink)"></i>
        </div>
        <div class="stack-labels"><span>BeamNG Autopilot · 165.9k</span><span>其余 17 个项目 · 74.0k</span></div>
        {other_rows}
      </div>
      <div class="num-panel rv" style="--d:90ms">
        <h3>语言构成 <b>· 按自有代码估算</b></h3>
        <div class="lang-bar">{lang_bar}</div>
        <div class="lang-legend">{lang_legend}</div>
        <div class="bar-row" style="margin-top:22px">
          <span class="bar-name">2026 提交</span>
          <div class="bar-track"><i style="width:{b_pct:.1f}%;background:var(--acc)"></i></div>
          <span class="bar-val">{b_pct:.0f}%</span>
        </div>
        <div class="stack-labels"><span>BeamNG {beamng_commits} 次 · My Profile {profile} 次 · 其余 {other} 次</span><span>{total} commits</span></div>
      </div>
      <div class="num-panel rv">
        <h3>一天里的我 <b>· 夜猫子实锤</b></h3>
        <div class="hour-chart">{hour_bars}</div>
        <div class="hour-labels">{hour_labels}</div>
        <p class="num-note">峰值 {peak:02d}:00 · {max_hour} 次提交；40% 发生在 22:00–05:00。</p>
      </div>
      <div class="num-panel rv" style="--d:90ms">
        <h3>写过的字 <b>· 不止代码</b></h3>
        <div class="bar-row"><span class="bar-name">BeamNG 实验文档</span>
          <div class="bar-track"><i style="width:100%"></i></div><span class="bar-val">224 篇</span></div>
        <div class="bar-row"><span class="bar-name">小说章节存档</span>
          <div class="bar-track"><i style="width:8%"></i></div><span class="bar-val">2.0k 行</span></div>
        <div class="bar-row"><span class="bar-name">验证/说明文档</span>
          <div class="bar-track"><i style="width:38%"></i></div><span class="bar-val">8 篇</span></div>
        <p class="num-note">_beamng-autopilot 的 224 篇实验报告是按日归档的，索引脚本生成——论文素材已经在攒了。</p>
      </div>
    </div>
    {build_heatmap()}
    """


def build_next() -> str:
    rows = "".join(
        f'<div class="next-row rv" style="--d:{i * 80}ms">'
        f'<span class="next-when">{escape(when)}</span>'
        f'<span class="next-what">{escape(what)}</span>'
        f'<span class="next-how">{escape(how)}</span></div>'
        for i, (when, what, how) in enumerate(NEXT)
    )
    return f"""
    <div class="next-list">{rows}</div>
    <div class="quote rv">「发布比完美重要。代码已经够多了，
      <em style="font-style:normal;color:var(--acc)">接下来拼的是发出去。</em>」
      <small>—— 2026 年底给自己的备忘</small>
    </div>
    """


def main() -> None:
    filters_note = ""
    hero_stats = f"""
      <div class="hs rv" style="--d:120ms"><b data-count="239.9" data-dec="1" data-suffix="k">0</b><span>行自有代码</span></div>
      <div class="hs rv" style="--d:190ms"><b data-count="1247" data-sep>0</b><span>2026 次提交</span></div>
      <div class="hs rv" style="--d:260ms"><b data-count="30" data-suffix="+">0</b><span>个项目目录</span></div>
      <div class="hs rv" style="--d:330ms"><b data-count="58">0</b><span>个活跃日</span></div>
    """

    html = f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Qiongkura · 代码手账 2026</title>
<meta name="description" content="Qiongkura 的代码手账：自动驾驶研究、嵌入式固件、本地优先工具与一本 300 万字的小说。全部数据来自本机 git 历史。">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23d4491f'/%3E%3Ctext x='16' y='23' font-family='monospace' font-size='19' fill='%23f4f1e8' text-anchor='middle'%3EQ%3C/text%3E%3C/svg%3E">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Noto+Serif+SC:wght@600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div id="progress"></div>
<header>
  <div class="nav">
    <a class="logo" href="#top"><i></i>QIONGKURA</a>
    <div class="nav-links">
      <a href="#work">作品</a><a href="#numbers">数字</a><a href="#next">计划</a>
    </div>
    <div class="nav-meta">
      <span id="clock">--:--:--</span>
      <a class="nav-gh" href="https://github.com/Qiongkura" target="_blank" rel="noopener">GITHUB ↗</a>
    </div>
  </div>
</header>

<main id="top">
  <div class="wrap">
    <section class="hero">
      <div>
        <p class="kicker rv">I:\\PROJECTS · 30+ REPOS · EST. 2024</p>
        <h1 class="rv-line"><span>我先把它做出来，</span><br><em>再告诉你为什么。</em></h1>
        <p class="lede rv" style="--d:160ms">白天写代码，晚上也在写代码。BeamNG 里训自动驾驶，STM32 上写固件，
        把整首歌变成蜂鸣器的旋律，还在写一本 <b>300 万字</b>的小说。
        这里是全部 <b>30+ 个项目</b>的户口本——每个数字都来自本机 git，不是简历形容词。</p>
        <div class="cta-row rv" style="--d:260ms">
          <a class="btn" href="#work">看作品</a>
          <a class="btn ghost" href="#numbers">看数字</a>
        </div>
      </div>
      <div>
        <div class="hero-stats">{hero_stats}</div>
        <p class="scroll-hint rv" style="--d:420ms">SCROLL — 下面都是真的</p>
      </div>
    </section>
  </div>

  {build_ticker()}

  <div class="wrap">
    <section id="work">
      <div class="sec-head rv">
        <div><div class="sec-index">01 / SELECTED WORK</div><h2>三件值得展开讲的</h2></div>
        <span class="sec-sub">问题 → 做法 → 结果，含未完成的部分</span>
      </div>
      <div class="sec-line"></div>
      {build_case(CASES[0], False)}
      {build_case(CASES[1], True)}
      {build_case(CASES[2], False)}

      <div class="sec-head rv" style="margin-top:56px">
        <div><div class="sec-index">02 / FULL INDEX</div><h2>全部项目索引</h2></div>
        <span class="sec-sub">包括没做完的和不好意思讲的</span>
      </div>
      <div class="sec-line"></div>
      {build_table()}
    </section>

    <section id="numbers">
      <div class="sec-head rv">
        <div><div class="sec-index">03 / BY THE NUMBERS</div><h2>数字</h2></div>
        <span class="sec-sub">git 里能查到的，不靠形容词</span>
      </div>
      <div class="sec-line"></div>
      {build_numbers()}
    </section>

    <section id="next">
      <div class="sec-head rv">
        <div><div class="sec-index">04 / NOW &amp; NEXT</div><h2>现在与接下来</h2></div>
        <span class="sec-sub">写了日期的才算计划</span>
      </div>
      <div class="sec-line"></div>
      {build_next()}
    </section>
  </div>
</main>

<footer>
  <div class="foot-in">
    <span>QIONGKURA · 代码手账 2026</span>
    <span>数据来自本机 git 历史 · 生成于 2026-11-02 · 未上传任何代码</span>
    <span><a href="https://qiongkura.xyz" target="_blank" rel="noopener">qiongkura.xyz</a> · <a href="https://github.com/Qiongkura" target="_blank" rel="noopener">GitHub ↗</a></span>
  </div>
</footer>

<script>{JS}</script>
</body>
</html>
"""
    path = OUT / "index.html"
    path.write_text(html, encoding="utf-8")
    print(path)


if __name__ == "__main__":
    main()
