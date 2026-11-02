"""Render the CodeYear annual report as an "engineering field-notes" page.

Design: warm paper background, ink text, one vermilion accent, serif display
+ mono data, visible hairlines, square corners. Every number on the page comes
from the runner's own git history; nothing is uploaded anywhere.

Pure vanilla JS (no dependencies): scroll progress, live clock, reveal-on-scroll,
count-up numbers, a real commit ticker, and an index-table filter. Honors
``prefers-reduced-motion``.
"""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta
from html import escape
from pathlib import Path

from .stats import (
    ReportStats,
    fmt_human,
    fmt_int,
    fmt_signed_pair,
    language_breakdown,
    parse_daily,
)

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
}
@media(max-width:640px){
  .wrap,.nav,.foot-in{padding-left:20px;padding-right:20px}
  .hero-stats{grid-template-columns:1fr 1fr}
  .nav-links{display:none}
  h1{font-size:42px}
  .index-table .t-stack,.index-table .t-desc{display:none}
  .next-row{grid-template-columns:1fr}
}
@media (prefers-reduced-motion: reduce){
  *,*::before,*::after{animation:none!important;transition:none!important}
  .rv,.rv-line{opacity:1!important;transform:none!important}
  .sec-line,.bar-track i,.hour-bar{transform:none!important;opacity:1!important}
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
  filters.forEach(btn=>btn.addEventListener('click',()=>{
    filters.forEach(b=>b.classList.toggle('on', b===btn));
    const f = btn.dataset.filter;
    let n=0;
    rows.forEach(r=>{
      const show = f==='all' || r.dataset.cat===f;
      r.style.display = show ? '' : 'none';
      if(show) n++;
    });
    if(countEl) countEl.textContent = n+' / '+rows.length;
  }));
})();
"""


def _stamp_for(last_iso: str, generated: str) -> tuple[str, bool]:
    """(label, is_active) based on how recently the repo was touched."""
    try:
        last = datetime.strptime(last_iso, "%Y.%m.%d").date()
        gen = datetime.strptime(generated, "%Y-%m-%d %H:%M").date()
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


def build_archives(stats: ReportStats) -> str:
    blocks = []
    for i, repo in enumerate(stats.repo_details[:3]):
        stamp, active = _stamp_for(repo["last"], stats.generated_at)
        langs = "".join(
            f'<span>{escape(str(lang))} {(n / max(repo["lines"], 1) * 100):.0f}%</span>'
            for lang, n in repo["langs"]
        )
        recents = "".join(
            f'<div><b>{escape(r["date"])}</b>{escape(r["subject"])}</div>'
            for r in repo.get("recent", [])
        )
        readme = escape(repo["readme"]) if repo.get("readme") else "（这个仓库的 README 还没写简介）"
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
        if repo.get("remote") and "github.com" in repo["remote"]:
            url = repo["remote"].replace(".git", "")
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
            <h3>{name_html}</h3>
            <p class="readme-quote">{readme}</p>
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
        stamp, active = _stamp_for(repo["last"], stats.generated_at)
        name = escape(repo["name"])
        if repo.get("remote") and "github.com" in repo["remote"]:
            url = repo["remote"].replace(".git", "")
            name = f'<a href="{escape(url)}" target="_blank" rel="noopener">{name} ↗</a>'
        readme = escape(repo["readme"]) if repo.get("readme") else "（README 没写简介）"
        none_cls = "" if repo.get("readme") else ' class="t-desc none"'
        hot = ' class="t-status hot"' if active else ""
        stack = " · ".join(escape(str(lang)) for lang, _ in repo["langs"])
        rows.append(
            f'<tr data-cat="{cat_of(repo)}">'
            f'<td class="t-no">{i:02d}</td>'
            f'<td class="t-name">{name}</td>'
            f'<td class="t-desc"{none_cls}>{readme}</td>'
            f'<td class="t-stack">{stack}</td>'
            f'<td class="t-loc">{fmt_human(repo["lines"])}</td>'
            f'<td class="t-stack">{repo["last"]}</td>'
            f'<td class="t-status"{hot}>{stamp}</td>'
            f"</tr>"
        )
    return f"""
    <div class="filters">{filters}</div>
    <table class="index-table">
      <thead><tr>
        <th>NO</th><th>仓库</th><th>一句话（README 原文）</th><th>栈</th>
        <th>自有代码</th><th>最近提交</th><th>状态</th>
      </tr></thead>
      <tbody>{''.join(rows)}</tbody>
    </table>
    <p class="index-note"><span id="row-count">{len(stats.repo_details)} / {len(stats.repo_details)}</span>
      · 「一句话」直接取自每个仓库 README 的第一行——没写的就是没写。</p>
    """


def build_heatmap(stats: ReportStats) -> str:
    daily = parse_daily(stats.daily)
    start = date(stats.year, 1, 1)
    end = date(stats.year, 12, 31)
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
      <h3>{stats.year} 活跃热力图 <b>· {stats.active_days} 个活跃日</b></h3>
      <div class="heat-wrap">
        <div class="months">{months}</div>
        <div class="heat">{''.join(cells)}</div>
      </div>
      <div class="heat-legend">{legend}<span style="margin-left:6px">少 → 多 · 框出今天</span></div>
    </div>
    """


def build_numbers(stats: ReportStats) -> str:
    total_lines = max(stats.lines_changed, 1)
    details = stats.repo_details
    top = details[0] if details else None
    top_share = top["lines"] / total_lines * 100 if top else 0
    others = [d for d in details[1:6] if d["lines"] > 0]
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
    palette = ["#171512", "#d4491f", "#8f8672", "#b3ab97", "#6f6a5e", "#c8c1ac"]
    lang_bar = "".join(
        f'<i style="width:{n / (sum(v for _, v in rows_lang) or 1) * 100:.2f}%;background:{palette[i % len(palette)]}"></i>'
        for i, (_name, n) in enumerate(rows_lang)
    )
    lang_legend = "".join(
        f'<div><span class="sq" style="background:{palette[i % len(palette)]}"></span>'
        f'{escape(name)}<b>{n / (sum(v for _, v in rows_lang) or 1) * 100:.0f}%</b></div>'
        for i, (name, n) in enumerate(rows_lang)
    )

    max_hour = max(stats.by_hour) or 1
    peak = stats.by_hour.index(max_hour)
    hour_bars = "".join(
        f'<div class="hour-bar{" peak" if v == max_hour and v > 0 else ""}" '
        f'style="height:{max(v / max_hour * 100, 2):.1f}%" title="{h:02d}:00 · {v} 次提交"></div>'
        for h, v in enumerate(stats.by_hour)
    )
    hour_labels = "".join(
        f"<span>{h:02d}</span>" if h in (0, 6, 12, 18, 23) else "<span></span>"
        for h in range(24)
    )

    max_file = max((n for _, n in stats.top_files), default=1)
    file_rows = "".join(
        f'<div class="bar-row"><span class="bar-name">{escape(path)}</span>'
        f'<div class="bar-track"><i style="width:{n / max_file * 100:.1f}%"></i></div>'
        f'<span class="bar-val">{fmt_human(n)}</span></div>'
        for path, n in stats.top_files[:6]
    ) or '<p class="num-note">没有可统计的代码文件。</p>'

    night_share = (stats.by_hour[22] + sum(stats.by_hour[:5])) / max(stats.commit_count, 1)
    return f"""
    <div class="num-grid">
      <div class="num-panel rv">
        <h3>代码构成 <b>· 头部集中度</b></h3>
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
      <div class="num-panel rv">
        <h3>一天里的你 <b>· {stats.persona.title}</b></h3>
        <div class="hour-chart">{hour_bars}</div>
        <div class="hour-labels">{hour_labels}</div>
        <p class="num-note">峰值 {peak:02d}:00 · {max_hour} 次提交；深夜（22:00–05:00）占 {night_share:.0%}。</p>
      </div>
      <div class="num-panel rv" style="--d:90ms">
        <h3>最常改的文件 <b>· 改动热区</b></h3>
        {file_rows}
      </div>
    </div>
    {build_heatmap(stats)}
    """


def build_about(stats: ReportStats) -> str:
    return f"""
    <div class="about rv">
      <ul>
        <li>这份报告由 CodeYear 在你的电脑上生成，代码从未离开这台机器。</li>
        <li>只统计 {stats.year} 年的提交；合并提交（--no-merges）不计入。</li>
        <li>同一 commit 出现在多个仓库时只计一次，归属提交数最多的仓库。</li>
        <li>时间取 author date；跨时区协作时以提交者本地时间为准。</li>
        <li>「自有代码」= 非空行；已剔除第三方库、生成工程与二进制。</li>
      </ul>
    </div>
    <div class="quote rv">「git 不会说谎——<em style="font-style:normal;color:var(--acc)">尤其是加了 --no-merges 的时候。</em>」
      <small>CODEYEAR · {stats.generated_at}</small>
    </div>
    """


def build_html(stats: ReportStats) -> str:
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
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600&family=IBM+Plex+Mono:wght@400;500&family=Noto+Serif+SC:wght@600&display=swap" rel="stylesheet">
<style>{CSS}</style>
</head>
<body>
<div id="progress"></div>
<header>
  <div class="nav">
    <a class="logo" href="#top"><i></i>CODEYEAR</a>
    <div class="nav-links">
      <a href="#archives">档案</a><a href="#index">索引</a><a href="#numbers">数字</a><a href="#about">关于</a>
    </div>
    <div class="nav-meta">
      <span id="clock">--:--:--</span>
      <span class="badge">LOCAL ONLY · 数据未上传</span>
    </div>
  </div>
</header>

<main id="top">
  <div class="wrap">
    <section class="hero">
      <div>
        <p class="kicker rv">SCAN · {escape(stats.root)} · {stats.year}</p>
        <h1 class="rv-line"><span>{stats.year} 年，</span><br><em>{fmt_int(stats.commit_count)} 次提交，{fmt_human(stats.lines_changed)} 行。</em></h1>
        <p class="lede rv" style="--d:160ms">{escape(stats.persona.subtitle)}
        代码行变更是 <b>+{fmt_human(stats.insertions)} / -{fmt_human(stats.deletions)}</b>，最忙的一天是 <b>{busiest}</b>。
        下面每个数字都来自本机 git——<b>这份报告没有上传任何东西</b>。</p>
      </div>
      <div>
        <div class="hero-stats">{hero_stats}</div>
        <p class="scroll-hint rv" style="--d:420ms">SCROLL — 全部来自你的仓库</p>
      </div>
    </section>
  </div>

  {build_ticker(stats)}

  <div class="wrap">
    <section id="archives">
      <div class="sec-head rv">
        <div><div class="sec-index">01 / REPO ARCHIVES</div><h2>仓库档案</h2></div>
        <span class="sec-sub">提交最多的三个仓库 · 时间线与热区</span>
      </div>
      <div class="sec-line"></div>
      {build_archives(stats)}
    </section>

    <section id="index">
      <div class="sec-head rv">
        <div><div class="sec-index">02 / FULL INDEX</div><h2>全部仓库索引</h2></div>
        <span class="sec-sub">包括休眠的和没写 README 的</span>
      </div>
      <div class="sec-line"></div>
      {build_table(stats)}
    </section>

    <section id="numbers">
      <div class="sec-head rv">
        <div><div class="sec-index">03 / BY THE NUMBERS</div><h2>数字</h2></div>
        <span class="sec-sub">git 里能查到的，不靠形容词</span>
      </div>
      <div class="sec-line"></div>
      {build_numbers(stats)}
    </section>

    <section id="about">
      <div class="sec-head rv">
        <div><div class="sec-index">04 / ABOUT THIS REPORT</div><h2>关于本报告</h2></div>
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
    <span>由 CodeYear 在本机生成 · {escape(stats.generated_at)} · 代码从未离开这台电脑</span>
  </div>
</footer>

<script>{JS}</script>
</body>
</html>
"""


def render(stats: ReportStats, out_path: str | Path) -> Path:
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(build_html(stats), encoding="utf-8")
    return path
