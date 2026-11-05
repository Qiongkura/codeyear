"""Render the CodeYear annual report as an "engineering field-notes" page.

Design: warm paper background, ink text, one vermilion accent, serif display
+ mono data, visible hairlines, square corners. Every number on the page comes
from the runner's own git history; nothing is uploaded anywhere.

Pure vanilla JS (no dependencies): scroll progress, live clock, reveal-on-scroll,
count-up numbers, a real commit ticker, and an index-table filter. Honors
``prefers-reduced-motion``.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

from .card import THEMES as CARD_THEMES
from .card import build_svg as build_card_svg
from .stats import (
    ReportStats,
    date_window,
    fmt_human,
    fmt_int,
    language_breakdown,
    parse_daily,
)

CSS = r"""
:root{
  --paper:#f4f1e8; --paper2:#eceadf; --ink:#171512; --ink2:#403c33;
  --muted:#6f6a5e; --line:#d9d3c2; --line2:#c8c1ac;
  --acc:#d4491f; --acc2:#b23a15;
  --serif:Georgia,"Times New Roman","Songti SC","SimSun","Noto Serif CJK SC",serif;
  --sans:-apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei","PingFang SC",sans-serif;
  --mono:"Cascadia Mono",Consolas,"SFMono-Regular",Menlo,monospace;
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
a{color:inherit}
h1,h2,h3{margin:0;font-weight:600}

#progress{position:fixed;top:0;left:0;height:2px;width:0;background:var(--acc);z-index:99}
header{position:sticky;top:0;z-index:50;background:rgba(244,241,232,.88);
  backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.nav{max-width:1160px;margin:0 auto;padding:0 28px;height:58px;display:flex;
  align-items:center;justify-content:space-between;gap:24px}
.logo{font-family:var(--mono);font-size:13px;letter-spacing:.22em;text-decoration:none;
  display:inline-flex;align-items:center;gap:9px}
.logo i{width:9px;height:9px;background:var(--acc);display:inline-block}
.nav-links{display:flex;gap:22px}
.nav-links a{color:var(--ink2);text-decoration:none;font-family:var(--mono);font-size:12px}
.nav-meta{display:flex;align-items:center;gap:16px;font-family:var(--mono);font-size:11px;
  color:var(--muted)}
.badge{border:1px solid var(--ink);padding:5px 11px;font-size:10px;letter-spacing:.1em;
  color:var(--ink)}

.u{color:var(--ink);text-decoration:none;
  background:linear-gradient(var(--acc),var(--acc)) no-repeat 0 100%/0 2px;
  transition:background-size .35s var(--ease);padding-bottom:2px}
.u:hover{background-size:100% 2px}

.hero{padding:84px 0 60px;display:grid;grid-template-columns:1.25fr .75fr;gap:48px;align-items:end}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.2em;color:var(--acc);margin:0 0 22px;
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
h1{font-family:var(--serif);font-size:clamp(44px,6vw,78px);line-height:1.08;
  letter-spacing:-.02em}
h1 em{font-style:normal;color:var(--acc)}
.lede{margin:26px 0 0;font-size:16px;line-height:1.85;color:var(--ink2);max-width:600px}
.lede b{color:var(--ink);font-weight:600}
.hero-stats{display:grid;grid-template-columns:1fr 1fr;border-left:1px solid var(--line)}
.hs{padding:18px 20px;border-bottom:1px solid var(--line)}
.hs:nth-child(odd){border-right:1px solid var(--line)}
.hs:nth-last-child(-n+2){border-bottom:0}
.hs b{display:block;font-family:var(--mono);font-size:29px;font-weight:500;
  letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.hs span{font-size:11px;color:var(--muted);font-family:var(--mono);letter-spacing:.06em}
.scroll-hint{font-family:var(--mono);font-size:10px;letter-spacing:.24em;color:var(--muted);
  margin-top:26px;display:flex;align-items:center;gap:12px}
.scroll-hint::after{content:"";flex:1;height:1px;background:var(--line)}

.ticker{border-top:1px solid var(--ink);border-bottom:1px solid var(--ink);background:var(--ink);
  color:var(--paper);overflow:hidden;position:relative;z-index:1}
.ticker-inner{display:flex;align-items:center;height:46px}
.tick-label{flex:none;padding:0 18px;border-right:1px solid rgba(244,241,232,.25);
  font-family:var(--mono);font-size:10px;letter-spacing:.18em;display:flex;align-items:center;
  gap:8px;height:100%}
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
.tick-item b{font-family:var(--mono);font-size:10px;color:var(--acc);font-weight:500}

section{padding:86px 0 0;scroll-margin-top:70px}
.sec-head{display:flex;align-items:baseline;justify-content:space-between;gap:20px;
  flex-wrap:wrap;border-bottom:2px solid var(--ink);padding-bottom:14px;margin-bottom:8px}
.sec-index{font-family:var(--mono);font-size:10px;letter-spacing:.24em;color:var(--acc)}
.sec-head h2{font-family:var(--serif);font-size:34px;letter-spacing:-.01em}
.sec-sub{color:var(--muted);font-size:13.5px;font-family:var(--mono)}
.sec-line{height:2px;background:var(--ink);transform:scaleX(0);transform-origin:left;
  transition:transform .9s var(--ease) .1s}
.sec-line.in{transform:scaleX(1)}

.archive{display:grid;grid-template-columns:.92fr 1.08fr;gap:40px;padding:42px 0;
  border-bottom:1px solid var(--line)}
.archive.flip .plate-wrap{order:2}
.plate-wrap{display:flex;flex-direction:column;gap:12px}
.plate{border:1px solid var(--ink);background:var(--paper2);padding:22px;flex:1}
.plate .big{display:flex;gap:26px;flex-wrap:wrap}
.plate .big b{display:block;font-family:var(--mono);font-size:26px;font-weight:500;
  letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.plate .big span{font-size:10.5px;color:var(--muted);font-family:var(--mono)}
.plate .langs{display:flex;gap:6px;flex-wrap:wrap;margin:16px 0 4px}
.plate .langs span{font-size:10.5px;font-family:var(--mono);border:1px solid var(--line2);
  padding:3px 8px;color:var(--ink2);background:var(--paper)}
.plate .rec{margin-top:14px;font-family:var(--mono);font-size:11px;line-height:1.9;color:var(--ink2)}
.plate .rec b{color:var(--acc);font-weight:500;font-size:10px;margin-right:8px}
.plate .rec div{border-top:1px dashed var(--line2);padding:6px 0}
.case-top{display:flex;align-items:center;justify-content:space-between;margin-bottom:14px}
.case-no{font-family:var(--mono);font-size:12px;color:var(--acc);letter-spacing:.14em}
.stamp{font-family:var(--mono);font-size:10px;letter-spacing:.14em;border:1px solid var(--ink);
  padding:4px 10px;display:inline-flex;align-items:center;gap:7px}
.stamp i{width:6px;height:6px;background:var(--acc);display:inline-block}
.stamp.sleep i{background:var(--muted)}
.archive h3{font-family:var(--serif);font-size:29px;letter-spacing:-.01em;margin-bottom:12px}
.readme-quote{border-left:2px solid var(--acc);padding:4px 0 4px 14px;color:var(--ink2);
  font-size:14px;margin:0 0 18px;font-style:italic}
.how{list-style:none;margin:0 0 20px;padding:0;font-family:var(--mono);font-size:12.5px;line-height:1.6}
.how li{padding:9px 0 9px 20px;border-top:1px dashed var(--line2);position:relative;color:var(--ink2)}
.how li::before{content:"—";position:absolute;left:0;color:var(--acc)}
.case-link{font-family:var(--mono);font-size:12px;letter-spacing:.08em;display:inline-block;
  margin-top:4px}

.filters{display:flex;gap:6px;flex-wrap:wrap;margin:20px 0 14px}
.filter{background:transparent;border:1px solid var(--ink);color:var(--ink);border-radius:0;
  padding:6px 12px;font-size:11.5px;cursor:pointer;font-family:var(--mono);
  transition:background .15s,color .15s}
.filter span{color:var(--muted);margin-left:5px;font-size:10px}
.filter.on{background:var(--ink);color:var(--paper)}
.filter.on span{color:rgba(244,241,232,.6)}
.filter:hover:not(.on){background:var(--paper2)}
.index-table{width:100%;border-collapse:collapse;font-size:13px}
.index-table th{font-family:var(--mono);font-size:10px;letter-spacing:.14em;color:var(--muted);
  text-align:left;font-weight:500;padding:9px 12px;border-bottom:2px solid var(--ink)}
.index-table td{padding:12px;border-bottom:1px solid var(--line);vertical-align:top}
.index-table tbody tr{transition:background .15s}
.index-table tbody tr:hover{background:var(--paper2)}
.t-no{font-family:var(--mono);font-size:11px;color:var(--muted);width:34px}
.t-name{font-weight:600;white-space:nowrap}
.t-name a{text-decoration:none}
.t-name a:hover{color:var(--acc)}
.t-desc{color:var(--ink2)}
.t-desc.none{color:var(--muted);font-style:italic}
.t-stack{font-family:var(--mono);font-size:11px;color:var(--muted)}
.t-loc{font-family:var(--mono);font-size:12px;font-variant-numeric:tabular-nums}
.t-status{font-family:var(--mono);font-size:11px;white-space:nowrap}
.t-status.hot{color:var(--acc)}
.index-note{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:12px}

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
.bar-name{width:150px;color:var(--ink2);overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap;font-family:var(--mono);font-size:11.5px}
.bar-track{flex:1;height:10px;border:1px solid var(--ink);background:var(--paper)}
.bar-track i{display:block;height:100%;background:var(--ink);transform-origin:left;
  transform:scaleX(0);transition:transform 1s var(--ease)}
.in .bar-track i{transform:scaleX(1)}
.bar-val{width:56px;text-align:right;font-family:var(--mono);font-size:11px;color:var(--muted)}
.lang-bar{display:flex;height:26px;border:1px solid var(--ink);margin-bottom:14px}
.lang-bar i{display:block;height:100%}
.lang-bar i+i{border-left:1px solid var(--paper)}
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
.cell.today{outline:2px solid var(--acc);outline-offset:1px}
.heat-legend{display:flex;align-items:center;justify-content:center;gap:4px;font-size:10px;
  color:var(--muted);margin-top:12px;font-family:var(--mono)}
.heat-legend .cell{width:10px;height:10px}
.num-note{font-family:var(--mono);font-size:10.5px;color:var(--muted);margin-top:16px;line-height:1.9}

/* ---- year records ---- */
.records{display:grid;grid-template-columns:repeat(3,1fr);border-top:1px solid var(--ink);
  border-left:1px solid var(--ink);margin-top:26px}
.record{border-right:1px solid var(--ink);border-bottom:1px solid var(--ink);padding:20px 22px;
  min-height:150px;display:flex;flex-direction:column;justify-content:space-between}
.record .k{font-family:var(--mono);font-size:10px;letter-spacing:.16em;color:var(--muted)}
.record .v{font-family:var(--serif);font-size:31px;line-height:1.15;margin:10px 0 6px;
  letter-spacing:-.01em}
.record .v small{font-family:var(--sans);font-size:13px;color:var(--muted);letter-spacing:0}
.record .s{font-family:var(--mono);font-size:10.5px;color:var(--muted);line-height:1.65;
  overflow:hidden;text-overflow:ellipsis}

/* ---- monthly rhythm ---- */
.month-chart{display:flex;align-items:flex-end;gap:6px;height:150px;margin-top:8px;
  padding-top:16px}
.month-col{position:relative;flex:1;height:100%;display:flex;
  flex-direction:column;justify-content:flex-end}
.month-col i{display:block;background:var(--ink);min-height:2px;transform-origin:bottom;
  transform:scaleY(0);transition:transform .85s var(--ease)}
.in .month-col i{transform:scaleY(1)}
.month-col.peak i{background:var(--acc)}
.month-col b{position:absolute;left:-3px;right:-3px;text-align:center;
  font-family:var(--mono);font-size:9px;font-weight:400;line-height:1;
  color:var(--muted);pointer-events:none}
.month-labels{display:flex;gap:6px;margin-top:7px;font-family:var(--mono);font-size:9px;
  color:var(--muted)}
.month-labels span{flex:1;text-align:center}

/* ---- 7x24 clock ---- */
.clock-wrap{overflow-x:auto}
.clock{display:grid;grid-template-columns:34px repeat(24,28px);gap:3px;
  justify-content:center;min-width:748px;padding:2px 0}
.clock .wd{font-family:var(--mono);font-size:9.5px;color:var(--muted);text-align:right;
  padding-right:6px;align-self:center}
.clock .hh{font-family:var(--mono);font-size:8px;color:var(--muted);text-align:center;height:14px}
.clock .c{width:28px;height:16px;background:var(--paper2)}
.clock .c.l1{background:#ddd6c4}.clock .c.l2{background:#a89f88}
.clock .c.l3{background:#5c554a}.clock .c.l4{background:var(--ink)}

/* ---- lifecycle bars ---- */
.lc-months{display:grid;grid-template-columns:190px 1fr 96px;gap:10px;
  font-family:var(--mono);font-size:9px;color:var(--muted);margin-bottom:6px}
.lc-month-ticks{display:grid;grid-template-columns:repeat(12,1fr)}
.lc-month-ticks span{text-align:left}
.lc-end{text-align:right}
.lc-row{display:grid;grid-template-columns:190px 1fr 96px;gap:10px;
  align-items:center;margin:7px 0}
.lc-name{font-family:var(--mono);font-size:10.5px;color:var(--ink2);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.lc-track{height:10px;background-color:var(--paper2);
  background-image:linear-gradient(90deg,var(--line) 1px,transparent 1px);
  background-size:calc(100% / 12) 100%;border:1px solid var(--line2);position:relative}
.lc-track i{position:absolute;top:0;bottom:0;background:var(--ink);z-index:1;min-width:1px}
.lc-track i.hot{background:var(--acc)}
.lc-track i.dot{width:7px;height:7px;top:50%;bottom:auto;transform:translateY(-50%)}
.lc-date{font-family:var(--mono);font-size:9.5px;color:var(--muted);text-align:right}

/* ---- keyword chips / churn ---- */
.chips-cloud{display:flex;gap:6px;flex-wrap:wrap}
.chips-cloud span{font-family:var(--mono);font-size:10.5px;border:1px solid var(--line2);
  padding:4px 9px;color:var(--ink2);background:var(--paper)}
.chips-cloud b{color:var(--acc);font-weight:500;margin-left:5px}
.pair{display:flex;height:18px;border:1px solid var(--ink);margin:10px 0}
.pair i{display:block;height:100%}

.year-span{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;
  margin-top:14px;padding-bottom:10px;border-bottom:1px solid var(--line);
  font-family:var(--mono);font-size:10.5px;color:var(--muted)}
.year-span b{color:var(--ink);font-weight:500}

.sub-head{font-family:var(--mono);font-size:9.5px;letter-spacing:.12em;color:var(--muted);
  margin:16px 0 2px}

.mini-stats{display:grid;grid-template-columns:1fr 1fr;gap:14px 18px}
.mini-stats b{display:block;font-family:var(--mono);font-size:24px;font-weight:500;
  letter-spacing:-.01em}
.mini-stats span{font-size:10px;color:var(--muted);font-family:var(--mono)}

.file-line{padding:10px 0;border-top:1px dashed var(--line2)}
.file-line:first-child{border-top:0;padding-top:0}
.file-path{font-family:var(--mono);font-size:11px;color:var(--ink2);line-height:1.55;
  word-break:break-all;margin-bottom:6px}
.file-meta{display:flex;align-items:center;gap:10px}
.file-meta .bar-track{flex:1}

.q-chart{display:flex;align-items:flex-end;gap:26px;height:190px;margin-top:8px}
.q-col{flex:1;display:flex;flex-direction:column;height:100%}
.q-stack{flex:1;display:flex;flex-direction:column-reverse;border:1px solid var(--ink);
  background:var(--paper2)}
.q-stack i{display:block;width:100%}
.q-none{flex:1;display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-size:9.5px;color:var(--muted)}
.q-label{font-family:var(--mono);font-size:10px;color:var(--muted);text-align:center;
  margin-top:6px}
.q-legend{display:flex;gap:18px;flex-wrap:wrap;font-family:var(--mono);font-size:10.5px;
  color:var(--muted);margin-top:14px}
.q-legend span{display:flex;align-items:center;gap:6px}
.q-legend i{display:inline-block;width:9px;height:9px}

.dormant-row{display:grid;grid-template-columns:1fr 170px 70px;gap:12px;
  padding:9px 0;border-top:1px dashed var(--line2);font-family:var(--mono);font-size:11px}
.dormant-row:first-child{border-top:0}
.d-name{color:var(--ink2)}
.d-last{color:var(--muted)}
.d-days{text-align:right;color:var(--acc)}

#tip{position:fixed;left:0;top:0;z-index:90;pointer-events:none;opacity:0;
  background:var(--paper);border:1px solid var(--ink);box-shadow:4px 4px 0 var(--acc);
  font-family:var(--mono);font-size:11px;line-height:1.5;color:var(--ink);
  padding:6px 9px;max-width:300px;transition:opacity .12s var(--ease)}
#tip.show{opacity:1}

@media(min-width:921px){.num-grid .span2{grid-column:span 2}}


.about{border:1px solid var(--ink);padding:26px;background:var(--paper)}
.about ul{margin:0;padding:0;list-style:none;font-family:var(--mono);font-size:12px;color:var(--ink2)}
.about li{padding:9px 0 9px 20px;border-top:1px dashed var(--line2);position:relative}
.about li:first-child{border-top:0}
.about li::before{content:"—";position:absolute;left:0;color:var(--acc)}
.quote{margin:44px 0 0;padding:6px 0 6px 26px;border-left:3px solid var(--acc);
  font-family:var(--serif);font-size:25px;line-height:1.5;color:var(--ink)}
.quote small{display:block;font-family:var(--mono);font-size:10.5px;color:var(--muted);
  margin-top:10px;letter-spacing:.1em}

footer{border-top:2px solid var(--ink);margin-top:90px;padding:24px 0 44px}
.foot-in{max-width:1160px;margin:0 auto;padding:0 28px;display:flex;
  justify-content:space-between;gap:14px;flex-wrap:wrap;font-family:var(--mono);
  font-size:11px;color:var(--muted)}

.rv{opacity:0;transform:translateY(20px);transition:opacity .75s var(--ease),
  transform .75s var(--ease);transition-delay:var(--d,0ms)}
.rv.in{opacity:1;transform:none}
.rv-line{opacity:0;transform:translateY(30px);transition:opacity .85s var(--ease),
  transform .85s var(--ease);transition-delay:var(--d,0ms)}
.rv-line.in{opacity:1;transform:none}

@media(max-width:920px){
  .hero{grid-template-columns:1fr;gap:36px;padding-top:56px}
  .hero-stats{border-left:0;grid-template-columns:repeat(4,1fr)}
  .hs{border-right:0!important;border-bottom:1px solid var(--line)}
  .hs:nth-last-child(-n+2){border-bottom:1px solid var(--line)}
  .archive,.archive.flip{grid-template-columns:1fr}
  .archive.flip .plate-wrap{order:0}
  .num-grid{grid-template-columns:1fr}
  .records{grid-template-columns:repeat(2,1fr)}
}
@media(max-width:640px){
  .wrap,.nav,.foot-in{padding-left:20px;padding-right:20px}
  .hero-stats{grid-template-columns:1fr 1fr}
  .nav-links{display:none}
  h1{font-size:42px}
  .index-table .t-stack,.index-table .t-desc{display:none}
  .records{grid-template-columns:1fr}
  .lc-row{grid-template-columns:120px 1fr 76px}
  .lc-months{grid-template-columns:120px 1fr 76px}
  .dormant-row{grid-template-columns:1fr 120px 52px}
  .q-chart{gap:10px}
}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
  .rv,.rv-line{opacity:1!important;transform:none!important}
  .sec-line,.bar-track i,.hour-bar{transform:none!important;opacity:1!important}
  .tick-track{animation:none!important}
}
@media print{
  .rv,.rv-line{opacity:1!important;transform:none!important}
  .sec-line,.bar-track i,.hour-bar{transform:none!important}
  .tick-track{animation:none!important}
}
"""

JS = r"""
(function(){
  const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const $$ = (s,c)=> [...(c||document).querySelectorAll(s)];

  const bar = document.getElementById('progress');
  const onScroll = ()=>{
    const h = document.documentElement;
    const p = h.scrollTop / (h.scrollHeight - h.clientHeight || 1);
    if(bar) bar.style.width = (p*100).toFixed(2)+'%';
  };
  addEventListener('scroll', onScroll, {passive:true}); onScroll();

  const clock = document.getElementById('clock');
  const pad = n=> String(n).padStart(2,'0');
  const tickClock = ()=>{
    const d = new Date();
    clock.textContent = pad(d.getHours())+':'+pad(d.getMinutes())+':'+pad(d.getSeconds());
  };
  if(clock){ tickClock(); setInterval(tickClock, 1000); }

  const targets = $$('.rv, .rv-line, .sec-line');
  if(RM || !('IntersectionObserver' in window)){
    targets.forEach(el=>el.classList.add('in'));
  }else{
    const io = new IntersectionObserver(es=>{
      es.forEach(e=>{ if(e.isIntersecting){ e.target.classList.add('in'); io.unobserve(e.target);} });
    },{threshold:.1, rootMargin:'0px 0px -30px 0px'});
    targets.forEach(el=>io.observe(el));
  }

  const counters = $$('[data-count]');
  const finalText = el=>{
    const t = parseFloat(el.dataset.count), dec = parseInt(el.dataset.dec||'0',10);
    let s = t.toFixed(dec);
    if('sep' in el.dataset) s = Number(s).toLocaleString('en-US');
    return s + (el.dataset.suffix||'');
  };
  const run = el=>{
    const target = parseFloat(el.dataset.count);
    const dec = parseInt(el.dataset.dec||'0',10);
    const suffix = el.dataset.suffix||'';
    const sep = 'sep' in el.dataset;
    const dur = 1300, t0 = performance.now();
    const step = now=>{
      const p = Math.min((now-t0)/dur, 1);
      const e = 1-Math.pow(1-p,3);
      let s = (target*e).toFixed(dec);
      if(sep) s = Number(s).toLocaleString('en-US');
      el.textContent = s + suffix;
      if(p<1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  };
  if(RM || !('IntersectionObserver' in window)){
    counters.forEach(el=>el.textContent = finalText(el));
  }else{
    const cio = new IntersectionObserver(es=>{
      es.forEach(e=>{ if(e.isIntersecting){ run(e.target); cio.unobserve(e.target);} });
    },{threshold:.5});
    counters.forEach(el=>cio.observe(el));
  }

  const filters = $$('.filter');
  const rows = $$('.index-table tbody tr');
  const countEl = document.getElementById('row-count');
  const searchEl = document.getElementById('repo-search');
  const applyFilter = ()=>{
    const active = document.querySelector('.filter.on');
    const f = active ? active.dataset.filter : 'all';
    const q = searchEl ? searchEl.value.trim().toLowerCase() : '';
    let n=0;
    rows.forEach(r=>{
      const show = (f==='all' || r.dataset.cat===f) &&
                   (!q || r.textContent.toLowerCase().includes(q));
      r.style.display = show ? '' : 'none';
      if(show) n++;
    });
    if(countEl) countEl.textContent = n+' / '+rows.length;
  };
  filters.forEach(btn=>btn.addEventListener('click',()=>{
    filters.forEach(b=>b.classList.toggle('on', b===btn));
    applyFilter();
  }));
  if(searchEl) searchEl.addEventListener('input', applyFilter);

  /* paper-style tooltip (replaces native title bubbles) */
  const tip = document.getElementById('tip');
  if(tip){
    let target = null;
    const place = ev=>{
      const gap = 14;
      let x = ev.clientX + gap, y = ev.clientY + gap;
      const r = tip.getBoundingClientRect();
      if(x + r.width > innerWidth - 8) x = ev.clientX - r.width - gap;
      if(y + r.height > innerHeight - 8) y = ev.clientY - r.height - gap;
      tip.style.transform = 'translate('+x+'px,'+y+'px)';
    };
    document.addEventListener('mouseover', ev=>{
      const el = ev.target.closest ? ev.target.closest('[data-tip]') : null;
      if(!el) return;
      target = el;
      tip.textContent = el.dataset.tip;
      tip.classList.add('show');
      place(ev);
    });
    document.addEventListener('mouseout', ev=>{
      if(!target) return;
      if(ev.relatedTarget && target.contains(ev.relatedTarget)) return;
      target = null;
      tip.classList.remove('show');
    });
    document.addEventListener('mousemove', ev=>{ if(target) place(ev); });
    addEventListener('scroll', ()=>{ target=null; tip.classList.remove('show'); }, {passive:true});
    addEventListener('blur', ()=>{ target=null; tip.classList.remove('show'); });
  }
})();
"""


def _stamp_for(
    last_iso: str, generated: str, year: int | None = None
) -> tuple[str, bool]:
    """(label, is_active) based on how recently the repo was touched."""
    try:
        last = datetime.strptime(last_iso, "%Y.%m.%d").date()
        gen = datetime.strptime(generated, "%Y-%m-%d %H:%M").date()
        if year is not None and year < gen.year:
            gen = date(year, 12, 31)
        days = (gen - last).days
    except ValueError:
        return "未知", False
    if days <= 7:
        return "活跃", True
    if days <= 30:
        return "进行中", True
    return "休眠", False


def build_ticker(stats: ReportStats) -> str:
    if not stats.ticker:
        return ""
    items = "".join(
        f'<span class="tick-item"><b>{escape(t["repo"])}</b>{escape(t["subject"])}</span>'
        for t in stats.ticker
    )
    return f"""
    <div class="ticker" aria-label="最近的真实提交记录">
      <div class="ticker-inner">
        <div class="tick-label"><i></i>LIVE · GIT</div>
        <div class="tick-viewport"><div class="tick-track">{items}{items}</div></div>
      </div>
    </div>
    """


def _web_url(remote: str) -> str | None:
    """Normalize a git remote (https or ssh) to a clickable web URL."""
    remote = (remote or "").strip()
    if not remote:
        return None
    if remote.startswith("git@") and ":" in remote:
        host, path = remote[4:].split(":", 1)
        return f"https://{host}/{path.removesuffix('.git')}"
    if remote.startswith(("http://", "https://")):
        return remote.removesuffix(".git")
    return None


def build_archives(stats: ReportStats) -> str:
    blocks = []
    for i, repo in enumerate(stats.repo_details[:3]):
        stamp, active = _stamp_for(repo["last"], stats.generated_at, stats.year)
        langs = "".join(
            f'<span>{escape(str(lang))} {(n / max(repo["lines"], 1) * 100):.0f}%</span>'
            for lang, n in repo["langs"]
        )
        recents = "".join(
            f'<div><b>{escape(r["date"])}</b><span data-raw>{escape(r["subject"])}</span></div>'
            for r in repo.get("recent", [])
        )
        has_readme = bool(repo.get("readme"))
        readme = escape(repo["readme"]) if has_readme else "（这个仓库的 README 还没写简介）"
        readme_raw = " data-raw" if has_readme else ""
        top_file = repo.get("top_file")
        facts = [
            f'首次提交 {repo["first"]} → 最近提交 {repo["last"]}',
            "语言：" + " · ".join(f"{lang} {n}" for lang, n in repo["langs"]),
        ]
        if top_file:
            facts.append(f'最常改的文件：{top_file[0]}（{fmt_human(top_file[1])} 行变更）')
        facts.append("提交 " + fmt_int(repo["commits"]) + " 次（已按 hash 去重）")
        how = "".join(f"<li>{escape(f)}</li>" for f in facts)
        link = ""
        url = _web_url(repo.get("remote") or "")
        if url:
            link = f'<a class="u case-link" href="{escape(url)}" target="_blank" rel="noopener">GITHUB ↗</a>'
        name_html = escape(repo["name"])
        blocks.append(f"""
        <article class="archive{' flip' if i % 2 else ''}">
          <div class="plate-wrap">
            <div class="plate">
              <div class="big">
                <div><b>{fmt_int(repo["commits"])}</b><span>次提交</span></div>
                <div><b>{fmt_human(repo["lines"])}</b><span>行代码变更</span></div>
                <div><b>{len(repo["langs"])}</b><span>种主要语言</span></div>
              </div>
              <div class="langs">{langs}</div>
              <div class="rec">{recents if recents else '<div>（最近没有提交）</div>'}</div>
            </div>
          </div>
          <div class="case-body">
            <div class="case-top">
              <span class="case-no">№ {i + 1:02d}</span>
              <span class="stamp{' sleep' if not active else ''}"><i></i>{stamp}</span>
            </div>
            <h3 data-raw>{name_html}</h3>
            <p class="readme-quote"{readme_raw}>{readme}</p>
            <ul class="how">{how}</ul>
            {link}
          </div>
        </article>
        """)
    return "".join(blocks)


def build_table(stats: ReportStats) -> str:
    lang_counts: dict[str, int] = {}
    for repo in stats.repo_details:
        if repo["langs"]:
            lang_counts[repo["langs"][0][0]] = lang_counts.get(repo["langs"][0][0], 0) + 1
    top_langs = sorted(lang_counts.items(), key=lambda kv: -kv[1])[:5]
    known = {lang for lang, _ in top_langs}

    cats = [("all", "全部")] + [(lang, lang) for lang, _ in top_langs]
    if any(repo["langs"] and repo["langs"][0][0] not in known for repo in stats.repo_details):
        cats.append(("__other", "其他"))

    def cat_of(repo: dict) -> str:
        if not repo["langs"]:
            return "__other"
        lang = repo["langs"][0][0]
        return lang if lang in known else "__other"

    filters = "".join(
        f'<button class="filter{" on" if key == "all" else ""}" data-filter="{escape(key)}">'
        f'{escape(label)}<span>{sum(1 for r in stats.repo_details if key == "all" or cat_of(r) == key)}</span></button>'
        for key, label in cats
    )

    rows = []
    for i, repo in enumerate(stats.repo_details, 1):
        stamp, active = _stamp_for(repo["last"], stats.generated_at, stats.year)
        name = escape(repo["name"])
        url = _web_url(repo.get("remote") or "")
        if url:
            name = f'<a href="{escape(url)}" target="_blank" rel="noopener">{name} ↗</a>'
        has_readme = bool(repo.get("readme"))
        readme = escape(repo["readme"]) if has_readme else "（README 没写简介）"
        none_cls = ' data-raw' if has_readme else ' class="t-desc none"'
        hot = ' class="t-status hot"' if active else ""
        stack = " · ".join(escape(str(lang)) for lang, _ in repo["langs"])
        rows.append(
            f'<tr data-cat="{cat_of(repo)}">'
            f'<td class="t-no">{i:02d}</td>'
            f'<td class="t-name" data-raw>{name}</td>'
            f'<td class="t-desc"{none_cls}>{readme}</td>'
            f'<td class="t-stack">{stack}</td>'
            f'<td class="t-loc">{fmt_human(repo["lines"])}</td>'
            f'<td class="t-stack">{repo["last"]}</td>'
            f'<td class="t-status"{hot}>{stamp}</td>'
            f"</tr>"
        )
    return f"""
    <div class="filters">{filters}
      <input class="repo-search" id="repo-search" type="search"
             placeholder="搜索仓库 / 语言 / 简介" aria-label="搜索仓库">
    </div>
    <table class="index-table">
      <thead><tr>
        <th>NO</th><th>仓库</th><th>一句话（README 原文）</th><th>栈</th>
        <th>自有代码</th><th>最近提交</th><th>状态</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <p class="index-note"><span id="row-count">{len(stats.repo_details)} / {len(stats.repo_details)}</span></p>
    """


def build_heatmap(stats: ReportStats) -> str:
    daily = parse_daily(stats.daily)
    start, end = date_window(stats)
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
        if tip:
            cells.append(
                f'<span class="cell {cls}" data-tip="{escape(tip)}" '
                f'aria-label="{escape(tip)}"></span>'
            )
        else:
            cells.append(f'<span class="cell {cls}"></span>')
        cursor += timedelta(days=1)

    months = "".join(f"<span>{m:02d}</span>" for m in range(1, 13))
    legend = "".join(f'<span class="cell l{i}"></span>' for i in range(5))
    return f"""
    <div class="num-panel heat-panel rv span2">
      <h3>{stats.year} 活跃热力图 <b>· {stats.active_days} 个活跃日</b></h3>
      <div class="heat-wrap">
        <div class="months">{months}</div>
        <div class="heat" role="img" aria-label="全年提交热力图">{''.join(cells)}</div>
      </div>
      <div class="heat-legend">{legend}<span style="margin-left:6px">少 → 多 · 框出今天</span></div>
    </div>
    """


def _panel(title: str, body: str, *, span: bool = False) -> str:
    cls = "num-panel rv span2" if span else "num-panel rv"
    return f'<div class="{cls}"><h3>{title}</h3>{body}</div>'


def build_records(stats: ReportStats) -> str:
    cards: list[str] = []

    def add(label: str, value: str, sub: str) -> None:
        cards.append(
            f'<div class="record rv"><div class="k">{label}</div>'
            f'<div class="v">{value}</div><div class="s">{sub}</div></div>'
        )

    if stats.busiest_day:
        day, count = stats.busiest_day
        add("最忙的一天", f"{count} <small>次提交</small>", day.replace("-", "."))
    if stats.busiest_week:
        week, count = stats.busiest_week
        add("最忙的一周", f"{count} <small>次提交</small>",
            f"{week} · 起于 {stats.busiest_week_start or '—'}")
    add("最长连续", f"{stats.longest_streak} <small>天</small>",
        f"当前连续 {stats.current_streak} 天")
    if stats.longest_gap:
        days, start, end = stats.longest_gap
        add("最长空窗", f"{days} <small>天</small>", f"{start} → {end}")
    if stats.largest_commit:
        lc = stats.largest_commit
        add("最大单次提交", f"{fmt_int(lc['lines'])} <small>行</small>",
            f"{escape(lc['repo'])} · {lc['date']}")
    add("最长的 commit", f"{len(stats.longest_subject)} <small>字符</small>",
        f'<span data-raw>{escape(stats.longest_subject[:90])}</span>')
    if getattr(stats, "latest_night_commit", None):
        nc = stats.latest_night_commit
        add("最晚的一次熬夜", f"{escape(nc['time'])}",
            f"{escape(nc['repo'])} · {escape(nc['date'])} · {escape(nc['subject'][:42])}")

    span = ""
    if stats.first_commit and stats.last_commit:
        fc, lc = stats.first_commit, stats.last_commit
        fc_sub = f" · {escape(fc['subject'][:40])}" if fc.get("subject") else ""
        lc_sub = f" · {escape(lc['subject'][:40])}" if lc.get("subject") else ""
        span = (
            f'<div class="year-span rv">'
            f'<span>第一次提交 <b>{escape(fc["date"])}</b> · {escape(fc["repo"])}{fc_sub}</span>'
            f'<span>最后一次提交 <b>{escape(lc["date"])}</b> · {escape(lc["repo"])}{lc_sub}</span>'
            f'</div>'
        )
    return f'<div class="records">{"".join(cards)}</div>{span}'


def build_monthly(stats: ReportStats) -> str:
    max_v = max(stats.monthly) or 1
    peak = stats.monthly.index(max_v) + 1

    def column(month: int, value: int) -> str:
        pct = max(value / max_v * 100, 1.5)
        label = (
            f'<b style="bottom:calc({pct:.1f}% + 3px)">{value:,}</b>'
            if value else ""
        )
        return (
            f'<div class="month-col{" peak" if value == max_v and value > 0 else ""}" '
            f'data-tip="{month} 月 · {value} 次提交" '
            f'aria-label="{month} 月 · {value} 次提交">'
            f'<i style="height:{pct:.1f}%"></i>{label}</div>'
        )

    cols = "".join(column(m + 1, v) for m, v in enumerate(stats.monthly))
    labels = "".join(f"<span>{m:02d}</span>" for m in range(1, 13))
    return _panel(
        f"月度节奏 <b>· 峰值 {peak:02d} 月 · {max_v} 次</b>",
        f'<div class="month-chart" role="img" aria-label="月度提交次数">{cols}</div>'
        f'<div class="month-labels">{labels}</div>',
        span=True,
    )


def build_clock(stats: ReportStats) -> str:
    flat = [v for row in stats.hour_weekday for v in row]
    max_v = max(flat) or 1

    def level(v: int) -> str:
        if v == 0:
            return "l0"
        if v <= max_v * 0.15:
            return "l1"
        if v <= max_v * 0.35:
            return "l2"
        if v <= max_v * 0.6:
            return "l3"
        return "l4"

    days = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    head = '<span class="wd"></span>' + "".join(
        f'<span class="hh">{h if h % 3 == 0 else ""}</span>' for h in range(24)
    )
    rows = []
    for wd, row in enumerate(stats.hour_weekday):
        cells = "".join(
            f'<span class="c {level(v)}" data-tip="{days[wd]} {h:02d}:00 · {v} 次提交" '
            f'aria-label="{days[wd]} {h:02d}:00 · {v} 次提交"></span>'
            for h, v in enumerate(row)
        )
        rows.append(f'<span class="wd">{days[wd]}</span>{cells}')

    totals = [sum(stats.hour_weekday[wd][h] for wd in range(7)) for h in range(24)]
    peak = totals.index(max(totals))
    return _panel(
        f"7×24 提交时钟 <b>· 峰值 {peak:02d}:00</b>",
        f'<div class="clock-wrap"><div class="clock" role="img" '
        f'aria-label="7×24 提交时钟">{head}{"".join(rows)}</div></div>'
        f'<p class="num-note">周末占 {stats.weekend_share:.0%}，'
        f'深夜（22:00–05:00）占 {stats.night_share:.0%}。</p>',
        span=True,
    )


def build_sizes(stats: ReportStats) -> str:
    max_v = max((v for _, v in stats.size_buckets), default=1) or 1
    rows = "".join(
        f'<div class="bar-row"><span class="bar-name">{label} 行</span>'
        f'<div class="bar-track"><i style="width:{v / max_v * 100:.1f}%"></i></div>'
        f'<span class="bar-val">{v}</span></div>'
        for label, v in stats.size_buckets
    )
    return _panel("提交规模 <b>· 小步快跑还是大爆炸</b>", rows)


def build_types(stats: ReportStats) -> str:
    if not stats.commit_types:
        return _panel("提交类型 <b>· 约定式提交</b>",
                      '<p class="num-note">没有识别到 Conventional Commits 类型。</p>')
    max_v = max(v for _, v in stats.commit_types) or 1
    rows = "".join(
        f'<div class="bar-row"><span class="bar-name">{escape(name)}</span>'
        f'<div class="bar-track"><i style="width:{v / max_v * 100:.1f}%"></i></div>'
        f'<span class="bar-val">{v}</span></div>'
        for name, v in stats.commit_types
    )
    return _panel(f"提交类型 <b>· 约定式占 {stats.conventional_share:.0%}</b>", rows)


def build_keywords(stats: ReportStats) -> str:
    if not stats.keywords:
        return _panel("高频词 <b>· 口头禅</b>",
                      '<p class="num-note">提交信息太短，没有提取到关键词。</p>')
    chips = "".join(
        f"<span>{escape(word)}<b>{count}</b></span>" for word, count in stats.keywords[:16]
    )
    return _panel(
        "高频词 <b>· commit message 里的口头禅</b>",
        f'<div class="chips-cloud">{chips}</div>'
        f'<p class="num-note">平均每条 {stats.avg_subject_len} 字符。</p>',
    )


def build_messages(stats: ReportStats) -> str:
    max_v = max((v for _, v in stats.message_buckets), default=1) or 1
    rows = "".join(
        f'<div class="bar-row"><span class="bar-name">{label} 字符</span>'
        f'<div class="bar-track"><i style="width:{v / max_v * 100:.1f}%"></i></div>'
        f'<span class="bar-val">{v}</span></div>'
        for label, v in stats.message_buckets
    )
    return _panel(
        f"消息长度 <b>· 平均 {stats.avg_subject_len} 字符</b>",
        rows + '<p class="num-note">最长的一条见「年度之最」。</p>',
    )


def build_adddel(stats: ReportStats) -> str:
    ins, deleted = stats.insertions, stats.deletions
    total = max(ins + deleted, 1)
    ratio = deleted / max(ins, 1)
    body = (
        f'<div class="pair">'
        f'<i style="width:{ins / total * 100:.1f}%;background:var(--ink)"></i>'
        f'<i style="width:{deleted / total * 100:.1f}%;background:var(--acc)"></i></div>'
        f'<div class="stack-labels"><span>新增 {fmt_human(ins)} 行</span>'
        f'<span>删除 {fmt_human(deleted)} 行</span></div>'
        f'<p class="num-note">删除 / 新增 = {ratio:.0%}。'
    )
    if stats.largest_deletion:
        ld = stats.largest_deletion
        body += (f'最大的一次删除 {fmt_int(ld["lines"])} 行'
                 f'（{escape(ld["repo"])}，{ld["date"]}）。')
    body += "</p>"

    top_del = sorted(stats.repo_details, key=lambda d: -d["deleted"])[:3]
    if top_del:
        max_del = max(d["deleted"] for d in top_del) or 1
        body += '<div class="sub-head">删除最多的仓库</div>'
        body += "".join(
            f'<div class="bar-row"><span class="bar-name">{escape(d["name"])}</span>'
            f'<div class="bar-track"><i style="width:{d["deleted"] / max_del * 100:.1f}%;'
            f'background:var(--acc)"></i></div>'
            f'<span class="bar-val">{fmt_human(d["deleted"])}</span></div>'
            for d in top_del
        )
    return _panel("增删比 <b>· 建设 vs 重构</b>", body)


def build_sessions(stats: ReportStats) -> str:
    s = stats.sessions
    if not s.get("count"):
        body = '<p class="num-note">没有足够的提交时间数据。</p>'
    else:
        hours = s["longest_minutes"] // 60
        mins = s["longest_minutes"] % 60
        body = (
            f'<div class="mini-stats">'
            f'<div><b>{s["count"]}</b><span>次编码会话</span></div>'
            f'<div><b>{hours}h {mins:02d}m</b><span>最长一次连续编码</span></div>'
            f'<div><b>{s["longest_commits"]}</b><span>最长会话里的提交</span></div>'
            f'<div><b>{s["avg_minutes"]}m</b><span>平均会话时长</span></div>'
            f'</div>'
            f'<p class="num-note">间隔 ≤ 2 小时算同一会话。最长一次：'
            f'{escape(s["longest_start"])} → {escape(s["longest_end"])}。</p>'
        )
    return _panel("工作节奏 <b>· 会话而不是次数</b>", body)


def build_language_quarters(stats: ReportStats) -> str:
    if not stats.language_quarters:
        return _panel("语言栈变化 <b>· 按季度占比</b>",
                      '<p class="num-note">没有足够数据。</p>', span=True)
    palette = ["#171512", "#d4491f", "#8f8672", "#b3ab97", "#c8c1ac"]
    names = [name for name, _ in stats.language_quarters[0]["rows"]]
    cols = []
    for q in stats.language_quarters:
        raw_total = sum(v for _, v in q["rows"])
        total = raw_total or 1
        segs = []
        if raw_total == 0:
            segs.append('<span class="q-none">无提交</span>')
        for i, (name, value) in enumerate(q["rows"]):
            if value <= 0:
                continue
            pct = value / total * 100
            segs.append(
                f'<i style="height:{pct:.2f}%;background:{palette[i % len(palette)]}" '
                f'data-tip="{escape(name)} · {pct:.0f}% · {fmt_human(value)} 行"></i>'
            )
        cols.append(
            f'<div class="q-col"><div class="q-stack">{"".join(segs)}</div>'
            f'<span class="q-label">{q["q"]}</span></div>'
        )
    legend = "".join(
        f'<span><i style="background:{palette[i % len(palette)]}"></i>{escape(name)}</span>'
        for i, name in enumerate(names)
    )
    return _panel(
        "语言栈变化 <b>· 按季度占比</b>",
        f'<div class="q-chart" role="img" aria-label="语言栈季度变化">'
        f'{"".join(cols)}</div>'
        f'<div class="q-legend">{legend}</div>',
        span=True,
    )


def build_lifecycle(stats: ReportStats) -> str:
    start, end = date_window(stats)
    span_days = max((end - start).days, 1)
    ordered = sorted(stats.repo_details, key=lambda r: (r["first"], -r["commits"]))[:10]

    months = "".join(f"<span>{m:02d}</span>" for m in range(1, 13))
    head = (
        f'<div class="lc-months"><span></span>'
        f'<div class="lc-month-ticks">{months}</div>'
        f'<span class="lc-end">首次–最近</span></div>'
    )

    rows = []
    for repo in ordered:
        try:
            first = datetime.strptime(repo["first"], "%Y.%m.%d").date()
            last = datetime.strptime(repo["last"], "%Y.%m.%d").date()
        except ValueError:
            continue
        left = max(0.0, min(100.0, (first - start).days / span_days * 100))
        width = max(0.0, min(100.0 - left, (last - first).days / span_days * 100))
        _stamp, active = _stamp_for(repo["last"], stats.generated_at, stats.year)
        hot = " hot" if active else ""
        if (last - first).days == 0:
            bar = f'<i class="dot{hot}" style="left:calc({left:.2f}% - 3px)"></i>'
            dates = repo["first"][5:]
        else:
            bar = f'<i class="{hot.strip()}" style="left:{left:.1f}%;width:{width:.2f}%"></i>'
            dates = f'{repo["first"][5:]}–{repo["last"][5:]}'
        rows.append(
            f'<div class="lc-row">'
            f'<span class="lc-name" data-tip="{escape(repo["name"])} · '
            f'{repo["commits"]} 次提交 · {repo["active_days"]} 个活跃日">'
            f'{escape(repo["name"])}</span>'
            f'<div class="lc-track" data-tip="{repo["commits"]} 次提交 · '
            f'{fmt_human(repo["lines"])} 行变更 · {repo["active_days"]} 个活跃日">'
            f'{bar}</div>'
            f'<span class="lc-date">{dates}</span></div>'
        )
    return _panel(
        f"仓库生命周期 <b>· {stats.year} 活跃区间</b>",
        f'<div class="lc-chart">{head}{"".join(rows)}</div>',
        span=True,
    )


def build_deleted_files(stats: ReportStats) -> str:
    rows_data = getattr(stats, "top_deleted_files", None) or []
    if not rows_data:
        return ""
    max_del = max((n for _, n in rows_data), default=1) or 1
    rows = "".join(
        f'<div class="file-row"><span class="idx">{i:02d}</span>'
        f'<span class="f-path">{escape(path)}</span>'
        f'<div class="f-bar"><i style="width:{n / max_del * 100:.1f}%;background:var(--acc)"></i></div>'
        f'<span class="f-num">-{fmt_int(n)}</span></div>'
        for i, (path, n) in enumerate(rows_data[:8], 1)
    )
    return (
        '<div class="num-panel rv span2">'
        '<h3>文件级重构榜 <b>· 删除行数最多的文件</b></h3>'
        f'{rows}'
        '</div>'
    )


def build_dormant(stats: ReportStats) -> str:
    if not stats.dormant:
        return _panel("仓库墓园 <b>· 30 天没动</b>",
                      '<p class="num-note">没有休眠超过 30 天的仓库。</p>', span=True)
    rows = "".join(
        f'<div class="dormant-row"><span class="d-name">{escape(d["name"])}</span>'
        f'<span class="d-last">最后提交 {d["last"]}</span>'
        f'<span class="d-days">{d["days"]} 天</span></div>'
        for d in stats.dormant
    )
    return _panel(
        f"仓库墓园 <b>· {len(stats.dormant)} 个仓库超过 30 天没动</b>",
        rows, span=True,
    )


def build_compare(stats: ReportStats) -> str:
    """Year-over-year panel: metric table plus a month-by-month chart."""
    previous = stats.previous
    if not previous:
        return ""

    prev_year = previous.get("year", stats.year - 1)
    prev_commits = previous.get("previous_commits")
    if prev_commits is None:  # reports generated before raw values were stored
        prev_commits = stats.commit_count - previous.get("commits", 0)

    head = (
        f'<div class="num-panel rv span2 cmp-panel">'
        f'<h3>同比去年 <b>· {prev_year} vs {stats.year}</b></h3>'
    )
    hint = ""
    if prev_commits == 0:
        hint = (
            f'<p class="cmp-hint">{prev_year} 年在扫描范围内没有提交，'
            "以下按 0 计算。</p>"
            '<p class="cmp-hint">如果当时用过其他邮箱或名字，可以用 '
            "<code>--alias</code> 把旧身份合并进来后重新生成。</p>"
        )

    def human(value: int) -> str:
        return fmt_human(value).replace(" ", "")

    def delta_int(value: int, pct: float | None) -> str:
        text = f"{value:+,}" if value else "0"
        if pct is not None:
            text += " (0%)" if not pct else f" ({pct:+.0%})"
        return text

    def delta_human(value: int, pct: float | None) -> str:
        text = (
            ("+" if value > 0 else "-") + human(abs(value))
            if value else "0"
        )
        if pct is not None:
            text += " (0%)" if not pct else f" ({pct:+.0%})"
        return text

    def pp_parts(before: float, now: float) -> tuple[str, str, str]:
        before_pct = round(before * 100)
        now_pct = round(now * 100)
        delta = now_pct - before_pct
        return (
            f"{before_pct}%",
            f"{now_pct}%",
            f"{delta:+d} 个百分点" if delta else "0",
        )

    prev_weekend = previous.get("previous_weekend_share", 0.0)
    prev_night = previous.get("previous_night_share", 0.0)
    weekend_before, weekend_now, weekend_delta = pp_parts(
        prev_weekend, stats.weekend_share
    )
    night_before, night_now, night_delta = pp_parts(
        prev_night, stats.night_share
    )
    rows = [
        ("提交", f"{prev_commits:,}", f"{stats.commit_count:,}",
         delta_int(previous["commits"], previous.get("commits_pct"))),
        ("代码行变更", human(previous.get("previous_lines", 0)),
         human(stats.lines_changed),
         delta_human(previous["lines"], previous.get("lines_pct"))),
        ("新增行", human(previous.get("previous_insertions", 0)),
         human(stats.insertions),
         delta_human(previous.get("insertions", 0),
                     previous.get("insertions_pct"))),
        ("删除行", human(previous.get("previous_deletions", 0)),
         human(stats.deletions),
         delta_human(previous.get("deletions", 0),
                     previous.get("deletions_pct"))),
        ("活跃日", f'{previous.get("previous_active_days", 0):,}',
         f"{stats.active_days:,}",
         delta_int(previous["active_days"], previous.get("active_days_pct"))),
        ("涉及仓库", f'{previous.get("previous_repos", 0):,}',
         f"{stats.repo_count:,}",
         delta_int(previous["repos"], previous.get("repos_pct"))),
        ("最长连续（天）", f'{previous.get("previous_streak", 0):,}',
         f"{stats.longest_streak:,}",
         delta_int(previous["streak"], previous.get("streak_pct"))),
        ("平均提交信息（字符）", f'{previous.get("previous_avg_subject_len", 0):,}',
         f"{stats.avg_subject_len:,}",
         delta_int(previous.get("avg_subject_len", 0),
                   previous.get("avg_subject_len_pct"))),
        ("周末占比", weekend_before, weekend_now, weekend_delta),
        ("深夜占比", night_before, night_now, night_delta),
    ]
    table = "".join(
        f'<div class="cmp-row"><span class="cmp-k">{label}</span>'
        f'<span class="cmp-v">{before}</span>'
        f'<span class="cmp-v cur">{now}</span>'
        f'<span class="cmp-d{" zero" if change in ("0", "0pp") else ""}">{change}</span>'
        "</div>"
        for label, before, now, change in rows
    )

    prev_monthly = list(previous.get("previous_monthly") or [])
    prev_monthly += [0] * (12 - len(prev_monthly))
    cur_monthly = list(stats.monthly) + [0] * (12 - len(stats.monthly))
    chart_max = max([1, *prev_monthly[:12], *cur_monthly[:12]])
    cols = []
    for i in range(12):
        pv, cv = prev_monthly[i], cur_monthly[i]
        pp = pv / chart_max * 100
        cp = cv / chart_max * 100
        prev_label = (
            f'<b style="bottom:calc({pp:.1f}% + 3px)">{pv:,}</b>' if pv else ""
        )
        cur_label = (
            f'<b style="bottom:calc({cp:.1f}% + 3px)">{cv:,}</b>' if cv else ""
        )
        cols.append(
            f'<div class="cmp-col"><div class="cmp-bars">'
            f'<div class="cmp-bar prev"><i style="height:{pp:.1f}%" '
            f'data-tip="{prev_year} · {i + 1} 月 · {pv} 次提交"></i>'
            f"{prev_label}</div>"
            f'<div class="cmp-bar cur"><i style="height:{cp:.1f}%" '
            f'data-tip="{stats.year} · {i + 1} 月 · {cv} 次提交"></i>'
            f"{cur_label}</div>"
            f'</div><span>{i + 1}</span></div>'
        )
    notes = []
    cur_peak = max(cur_monthly[:12])
    prev_peak = max(prev_monthly[:12])
    if cur_peak:
        notes.append(
            f"<span>今年峰值 {cur_monthly.index(cur_peak) + 1} 月 · "
            f"{cur_peak:,} 次</span>"
        )
    if prev_peak:
        notes.append(
            f"<span>去年峰值 {prev_monthly.index(prev_peak) + 1} 月 · "
            f"{prev_peak:,} 次</span>"
        )

    chart = (
        f'<div class="cmp-chart" role="img" aria-label="月度同比柱状图">'
        f'<div class="cmp-cols">{"".join(cols)}</div>'
        f'<div class="cmp-legend"><span><i class="prev"></i>{prev_year}</span>'
        f'<span><i class="cur"></i>{stats.year}</span></div></div>'
    )
    note_html = f'<div class="cmp-note">{"".join(notes)}</div>' if notes else ""
    return (
        head + hint
        + '<div class="cmp-row cmp-head"><span class="cmp-k">指标</span>'
        f'<span class="cmp-v">{prev_year}</span>'
        f'<span class="cmp-v cur">{stats.year}</span>'
        '<span class="cmp-d">变化</span></div>'
        + table + chart + note_html + "</div>"
    )


def build_numbers(stats: ReportStats) -> str:
    total_lines = max(stats.lines_changed, 1)
    details = stats.repo_details
    by_lines = sorted(details, key=lambda d: (-d["lines"], -d["commits"]))
    top = by_lines[0] if by_lines else None
    top_share = top["lines"] / total_lines * 100 if top else 0
    others = [d for d in by_lines[1:6] if d["lines"] > 0]
    max_other = max((d["lines"] for d in others), default=1)
    other_rows = "".join(
        f'<div class="bar-row"><span class="bar-name">{escape(d["name"])}</span>'
        f'<div class="bar-track"><i style="width:{d["lines"] / max_other * 100:.1f}%"></i></div>'
        f'<span class="bar-val">{fmt_human(d["lines"])}</span></div>'
        for d in others
    )
    other_note = (
        f'<div class="stack-labels"><span>{escape(top["name"])} · {fmt_human(top["lines"])}</span>'
        f'<span>其余 {len(details) - 1} 个仓库 · {fmt_human(total_lines - top["lines"])}</span></div>'
        if top and len(details) > 1 else
        f'<div class="stack-labels"><span>{escape(top["name"]) if top else "—"}</span></div>'
    )

    rows_lang, _total = language_breakdown(stats.languages, limit=6, min_share=0.01)
    lang_total = sum(v for _, v in rows_lang) or 1
    palette = ["#171512", "#d4491f", "#8f8672", "#b3ab97", "#6f6a5e", "#c8c1ac"]
    lang_bar = "".join(
        f'<i style="width:{n / lang_total * 100:.2f}%;background:{palette[i % len(palette)]}"></i>'
        for i, (_name, n) in enumerate(rows_lang)
    )
    lang_legend = "".join(
        f'<div><span class="sq" style="background:{palette[i % len(palette)]}"></span>'
        f'{escape(name)}<b>{n / lang_total * 100:.0f}%</b></div>'
        for i, (name, n) in enumerate(rows_lang)
    )

    max_file = max((n for _, n in stats.top_files), default=1)
    file_rows = "".join(
        f'<div class="file-line"><div class="file-path">{escape(path)}</div>'
        f'<div class="file-meta"><div class="bar-track">'
        f'<i style="width:{n / max_file * 100:.1f}%"></i></div>'
        f'<span class="bar-val">{fmt_human(n)}</span></div></div>'
        for path, n in stats.top_files[:8]
    ) or '<p class="num-note">没有可统计的代码文件。</p>'

    return f"""
    <div class="num-grid">
      {build_compare(stats)}
      {build_monthly(stats)}
      {build_clock(stats)}
      <div class="num-panel rv">
        <h3>代码构成 <b>· 头部集中度（按行数）</b></h3>
        <div class="stack">
          <i style="width:{top_share:.1f}%;background:var(--acc)"></i>
          <i style="width:{100 - top_share:.1f}%;background:var(--ink)"></i>
        </div>
        {other_note}
        {other_rows}
      </div>
      <div class="num-panel rv" style="--d:90ms">
        <h3>语言构成 <b>· 按行变更估算</b></h3>
        <div class="lang-bar">{lang_bar}</div>
        <div class="lang-legend">{lang_legend}</div>
      </div>
      {build_language_quarters(stats)}
      {build_sizes(stats)}
      {build_types(stats)}
      {build_keywords(stats)}
      {build_messages(stats)}
      {build_adddel(stats)}
      {build_sessions(stats)}
      {build_lifecycle(stats)}
      {build_dormant(stats)}
      <div class="num-panel rv span2">
        <h3>最常改的文件 <b>· 改动热区（完整路径）</b></h3>
        {file_rows}
      </div>
      {build_deleted_files(stats)}
      {build_heatmap(stats)}
    </div>
    """


def _theme_color_map(base_dict: dict, target_dict: dict) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for k in ("ink", "ink2", "muted", "line", "accent", "bar"):
        mapping[base_dict[k].lower()] = target_dict[k]
    for src, dst in zip(base_dict["palette"], target_dict["palette"]):
        mapping.setdefault(src.lower(), dst)
    for src, dst in zip(base_dict["levels"], target_dict["levels"]):
        mapping.setdefault(src.lower(), dst)
    return mapping


def build_card_preview_widget(stats: ReportStats, *, lang: str = "zh") -> str:
    en = lang == "en"
    base_light, base_dark = CARD_THEMES["paper"]
    maps: dict[str, dict[str, dict[str, str]]] = {}
    for t_name, (t_light, t_dark) in CARD_THEMES.items():
        maps[t_name] = {
            "light": _theme_color_map(base_light, t_light),
            "dark": _theme_color_map(base_dark, t_dark),
        }
    svg_light = build_card_svg(stats, dark=False, theme="paper", lang=lang)
    svg_dark = build_card_svg(stats, dark=True, theme="paper", lang=lang)
    suffix = "-en" if en else ""
    embed_snippet = escape(
        "<picture>\n"
        f'  <source media="(prefers-color-scheme: dark)" '
        f'srcset="./codeyear-{stats.year}-card{suffix}-dark.svg">\n'
        f'  <img src="./codeyear-{stats.year}-card{suffix}.svg" width="640" '
        f'alt="CodeYear {stats.year}">\n'
        "</picture>"
    )
    payload_json = json.dumps(
        {
            "year": stats.year,
            "suffix": suffix,
            "light": svg_light,
            "dark": svg_dark,
            "maps": maps,
        },
        ensure_ascii=False,
    ).replace("</", "<\\/")

    heading = "GitHub profile card" if en else "GitHub 主页卡片"
    note = (
        "Preview all 4 themes in light or dark mode, download the SVG directly, or paste the snippet into your profile README.md:"
        if en
        else "实时预览 4 套主题与浅色/深色效果，可直接下载当前 SVG，或粘贴下方代码到同名 Profile 仓库的 README.md："
    )
    theme_labels = (
        [("paper", "Paper"), ("mono", "Mono"), ("forest", "Forest"), ("ocean", "Ocean")]
        if en
        else [("paper", "纸色 Paper"), ("mono", "黑白 Mono"), ("forest", "森林 Forest"), ("ocean", "海洋 Ocean")]
    )
    mode_labels = (
        [("light", "Light"), ("dark", "Dark")]
        if en
        else [("light", "浅色"), ("dark", "深色")]
    )
    dl_label = "Download current SVG" if en else "下载当前卡片 SVG"
    copy_label = "Copy embed snippet" if en else "复制嵌入代码"

    t_btns = "".join(
        f'<button class="filter{" on" if k == "paper" else ""}" type="button" data-card-theme="{k}">{lbl}</button>'
        for k, lbl in theme_labels
    )
    m_btns = "".join(
        f'<button class="filter{" on" if k == "light" else ""}" type="button" data-card-mode="{k}">{lbl}</button>'
        for k, lbl in mode_labels
    )
    return f"""<!--CARD_WIDGET_START-->
      <div class="sub-head" style="margin-top:24px">{heading}</div>
      <p class="num-note" style="margin:6px 0 10px">{note}</p>
      <div class="filters" style="margin:8px 0 10px;display:flex;gap:6px;flex-wrap:wrap;align-items:center">
        {t_btns}
        <span style="margin:0 4px;color:var(--line2)">|</span>
        {m_btns}
        <button class="filter" type="button" id="download-card-svg" style="margin-left:auto">{dl_label}</button>
      </div>
      <div id="card-preview-stage" style="border:1px solid var(--line);padding:16px;margin:0 0 12px;display:flex;justify-content:center;background:var(--paper);transition:background .18s">
        <div id="card-preview-inner" style="width:100%;max-width:460px">{svg_light}</div>
      </div>
      <pre class="embed-code" id="embed-snippet" style="background:var(--paper2);border:1px solid var(--line);padding:12px;font-family:var(--mono);font-size:11.5px;overflow-x:auto;margin:0 0 8px">{embed_snippet}</pre>
      <button class="filter" type="button" id="copy-embed" onclick="navigator.clipboard&&navigator.clipboard.writeText(document.getElementById('embed-snippet').textContent)">{copy_label}</button>
      <script>
      (function(){{
        const data = {payload_json};
        let curTheme = "paper", curMode = "light";
        const stage = document.getElementById("card-preview-stage");
        const inner = document.getElementById("card-preview-inner");
        const dlBtn = document.getElementById("download-card-svg");
        function currentSvg() {{
          const raw = curMode === "dark" ? data.dark : data.light;
          const cmap = (data.maps[curTheme] || data.maps.paper)[curMode];
          return raw.replace(/#[0-9a-f]{{6}}/gi, m => cmap[m.toLowerCase()] || m);
        }}
        function updateView() {{
          if (!inner || !stage) return;
          const svg = currentSvg();
          inner.innerHTML = svg;
          const svgEl = inner.querySelector("svg");
          if (svgEl) {{ svgEl.style.width = "100%"; svgEl.style.height = "auto"; }}
          stage.style.background = curMode === "dark" ? "#141413" : "var(--paper)";
        }}
        document.querySelectorAll("[data-card-theme]").forEach(btn => {{
          btn.addEventListener("click", () => {{
            curTheme = btn.getAttribute("data-card-theme") || "paper";
            document.querySelectorAll("[data-card-theme]").forEach(b => b.classList.toggle("on", b === btn));
            updateView();
          }});
        }});
        document.querySelectorAll("[data-card-mode]").forEach(btn => {{
          btn.addEventListener("click", () => {{
            curMode = btn.getAttribute("data-card-mode") || "light";
            document.querySelectorAll("[data-card-mode]").forEach(b => b.classList.toggle("on", b === btn));
            updateView();
          }});
        }});
        if (dlBtn) {{
          dlBtn.addEventListener("click", () => {{
            const blob = new Blob([currentSvg()], {{type: "image/svg+xml;charset=utf-8"}});
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            const darkPart = curMode === "dark" ? "-dark" : "";
            const themePart = curTheme === "paper" ? "" : "-" + curTheme;
            a.href = url;
            a.download = "codeyear-" + data.year + "-card" + data.suffix + themePart + darkPart + ".svg";
            document.body.appendChild(a);
            a.click();
            a.remove();
            setTimeout(() => URL.revokeObjectURL(url), 1000);
          }});
        }}
        updateView();
      }})();
      </script>
      <!--CARD_WIDGET_END-->"""


def build_about(stats: ReportStats) -> str:
    public = stats.public_source
    if public:
        privacy_line = "这份报告根据公开 GitHub 数据生成；没有读取或上传本机代码。"
        identity_line = (
            "只统计该账号名下的公开仓库，以及 GitHub 能关联到该账号的提交；"
            "不读取私有仓库。"
        )
        merge_line = f"只统计 {stats.year} 年的提交；合并提交不计入。"
    else:
        privacy_line = "这份报告由 CodeYear 在你的电脑上生成，代码从未离开这台机器。"
        if stats.identity_label:
            identity_line = (
                f"只统计你本人作者的提交（{escape(stats.identity_label)}）；"
                f"已过滤 {stats.filtered_commits} 次他人提交。"
            )
        else:
            identity_line = "未检测到 git 身份，统计了所有作者的提交（可用 --all-authors 显式开启）。"
        merge_line = f"只统计 {stats.year} 年的提交；合并提交（--no-merges）不计入。"
    quote_tail = (
        "尤其是加了 --no-merges 的时候。" if not public
        else "尤其是只读公开数据的时候。"
    )
    card_widget = build_card_preview_widget(stats, lang="zh")
    return f"""
    <div class="about rv">
      <ul>
        <li>{privacy_line}</li>
        <li>{identity_line}</li>
        <li>{merge_line}</li>
        <li>同一项目出现在多个目录时只保留提交最多的一个；同一 commit 只计一次。</li>
        <li>时间取 author date；跨时区协作时以提交者本地时间为准。</li>
        <li>「自有代码」= 非空行；已剔除第三方库、生成工程与二进制。</li>
      </ul>
      {card_widget}
    </div>
    <div class="quote rv">「git 不会说谎——<em style="font-style:normal;color:var(--acc)">{quote_tail}</em>」
      <small>CODEYEAR · {stats.generated_at}</small>
    </div>
    """


def build_persona_block(stats: ReportStats) -> str:
    persona = stats.persona
    badges = "".join(
        f"<span>{escape(badge)}</span>" for badge in persona.badges
    )
    summary = getattr(persona, "summary", persona.subtitle)
    return f"""
    <div class="persona-block">
      <div>
        <div class="persona-kicker">YEAR AT A GLANCE · {stats.year}</div>
        <h2 class="persona-name" data-persona-name>{escape(persona.title)}</h2>
        <p class="persona-summary" data-persona-summary>{escape(summary)}</p>
      </div>
      <div class="persona-badges" data-persona-badges>{badges}</div>
    </div>
    """


def build_html(stats: ReportStats) -> str:
    public = stats.public_source
    total_k = stats.lines_changed / 10000
    if stats.lines_changed >= 10000:
        lines_value, lines_dec, lines_suffix = total_k, 1, "万"
    else:
        lines_value, lines_dec, lines_suffix = float(stats.lines_changed), 0, ""
    span = "—"
    if stats.first_dt and stats.last_dt:
        span = f"{stats.first_dt:%Y.%m.%d} — {stats.last_dt:%Y.%m.%d}"
    busiest = stats.busiest_day[0].replace("-", ".") if stats.busiest_day else "—"

    hero_stats = f"""
      <div class="hs rv" style="--d:120ms"><b data-count="{lines_value:.4g}" data-dec="{lines_dec}" data-suffix="{lines_suffix}">0</b><span>行代码变更</span></div>
      <div class="hs rv" style="--d:190ms"><b data-count="{stats.commit_count}" data-sep>0</b><span>次提交</span></div>
      <div class="hs rv" style="--d:260ms"><b data-count="{stats.active_days}">0</b><span>个活跃日</span></div>
      <div class="hs rv" style="--d:330ms"><b data-count="{stats.repo_count}">0</b><span>个有提交的仓库</span></div>
    """

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeYear {stats.year} · {escape(stats.persona.title)}</title>
<meta name="description" content="CodeYear 年度代码手账：{escape(stats.persona.subtitle)}">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E%3Crect width='32' height='32' fill='%23d4491f'/%3E%3Ctext x='16' y='23' font-family='monospace' font-size='19' fill='%23f4f1e8' text-anchor='middle'%3EC%3C/text%3E%3C/svg%3E">
<style>{CSS}</style>
<noscript><style>.rv,.rv-line{{opacity:1!important;transform:none!important}}
.sec-line{{transform:none!important}}</style></noscript>
</head>
<body>
<a class="skip" href="#records">跳到主要内容</a>
<div id="progress"></div>
<header>
  <div class="nav">
    <a class="logo" href="#top"><i></i>CODEYEAR</a>
    <div class="nav-links" aria-label="主导航">
      <a href="#records">之最</a><a href="#archives">档案</a><a href="#index">索引</a>
      <a href="#numbers">数据分析</a><a href="#about">关于</a>
    </div>
    <div class="nav-meta">
      <span id="clock">--:--:--</span>
      <span class="badge">{'PUBLIC DATA · 来自 GitHub' if public else 'LOCAL ONLY · 数据未上传'}</span>
    </div>
  </div>
</header>

<main id="top">
  <div class="wrap">
    <section class="hero">
      <div>
        <p class="kicker rv">SCAN · {escape(stats.root)} · {stats.year}</p>
        <h1 class="rv-line"><span>{stats.year} 年，</span><br><em>{fmt_int(stats.commit_count)} 次提交，<span style="white-space:nowrap">{fmt_human(stats.lines_changed)} 行。</span></em></h1>
        <p class="lede rv" style="--d:160ms">{escape(stats.persona.subtitle)}
        代码行变更是 <b>+{fmt_human(stats.insertions)} / -{fmt_human(stats.deletions)}</b>，最忙的一天是 <b>{busiest}</b>。
        下面每个数字都来自{'公开 GitHub 数据' if public else '本机 git'}——<b>{'没有读取或上传本地代码' if public else '这份报告没有上传任何东西'}</b>。</p>
      </div>
      <div>
        <div class="hero-stats">{hero_stats}</div>
        <p class="scroll-hint rv" style="--d:420ms">SCROLL — 全部来自你的仓库</p>
      </div>
    </section>
    {build_persona_block(stats)}
  </div>

  {build_ticker(stats)}

  <div class="wrap">
    <section id="records">
      <div class="sec-head rv">
        <div><div class="sec-index">01 / YEAR IN REVIEW</div><h2>年度之最</h2></div>
        <span class="sec-sub">先看几个最极端的数字</span>
      </div>
      <div class="sec-line"></div>
      {build_records(stats)}
    </section>

    <section id="archives">
      <div class="sec-head rv">
        <div><div class="sec-index">02 / REPO ARCHIVES</div><h2>仓库档案</h2></div>
        <span class="sec-sub">提交最多的三个仓库 · 时间线与热区</span>
      </div>
      <div class="sec-line"></div>
      {build_archives(stats)}
    </section>

    <section id="index">
      <div class="sec-head rv">
        <div><div class="sec-index">03 / FULL INDEX</div><h2>全部仓库索引</h2></div>
        <span class="sec-sub">包括休眠的和没写 README 的</span>
      </div>
      <div class="sec-line"></div>
      {build_table(stats)}
    </section>

    <section id="numbers">
      <div class="sec-head rv">
        <div><div class="sec-index">04 / BY THE NUMBERS</div><h2>数据分析</h2></div>
        <span class="sec-sub">git 里能查到的，不靠形容词</span>
      </div>
      <div class="sec-line"></div>
      {build_numbers(stats)}
    </section>

    <section id="about">
      <div class="sec-head rv">
        <div><div class="sec-index">05 / ABOUT THIS REPORT</div><h2>关于本报告</h2></div>
        <span class="sec-sub">口径与方法</span>
      </div>
      <div class="sec-line"></div>
      {build_about(stats)}
    </section>
  </div>
</main>

<footer>
  <div class="foot-in">
    <span>CODEYEAR · 代码手账 {stats.year}</span>
    <span>扫描范围 {escape(stats.root)} · {escape(span)}</span>
    <span>由 CodeYear {'根据公开 GitHub 数据生成' if public else '在本机生成'} · {escape(stats.generated_at)} · {'没有读取或上传本地代码' if public else '代码从未离开这台电脑'}</span>
  </div>
</footer>

<div id="tip" aria-hidden="true"></div>
<script>{JS}</script>
</body>
</html>
"""


def render(stats: ReportStats, out_path: str | Path) -> Path:
    from .report_theme import decorate

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(decorate(build_html(stats), stats), encoding="utf-8")
    return path


def render_en(stats: ReportStats, out_path: str | Path) -> Path:
    from .report_theme import decorate, to_english

    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    html = decorate(build_html(stats), stats)
    path.write_text(to_english(html, stats), encoding="utf-8")
    return path
