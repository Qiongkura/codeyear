"""Small HTTP card service for public GitHub accounts.

Run ``codeyear serve`` locally or deploy the container to a Python host.
Only public GitHub data is read; private repositories still require the
local ``codeyear scan`` mode.
"""

from __future__ import annotations

import re
import sys
import threading
import time
from datetime import date
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from .card import build_svg
from .github_public import fetch_stats

USERNAME_RE = re.compile(r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?$")
CACHE: dict[tuple[str, int, int], tuple[float, object]] = {}
CACHE_LOCK = threading.Lock()
CACHE_TTL = 3600


def _cached_stats(username: str, year: int, token: str | None, max_commits: int):
    key = (username.lower(), year, max_commits)
    now = time.time()
    with CACHE_LOCK:
        item = CACHE.get(key)
        if item and now - item[0] < CACHE_TTL:
            return item[1]
    stats, _warnings, _login = fetch_stats(
        username, year, token=token, max_commits=max_commits, quiet=True,
    )
    with CACHE_LOCK:
        CACHE[key] = (time.time(), stats)
    return stats


def _error_svg(message: str) -> str:
    safe = (
        message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="640" height="200">
  <rect width="640" height="200" fill="#f5f2e9"/>
  <text x="24" y="72" font-family="Georgia, serif" font-size="22" fill="#141413">CodeYear</text>
  <text x="24" y="112" font-family="monospace" font-size="12" fill="#6f6a5e">{safe}</text>
  <text x="24" y="140" font-family="monospace" font-size="11" fill="#73726c">public data only · try again or use local mode</text>
</svg>
"""


class Handler(BaseHTTPRequestHandler):
    token: str | None = None
    max_commits: int = 200

    def log_message(self, fmt: str, *args) -> None:  # pragma: no cover
        print(f"{self.address_string()} - {fmt % args}", file=sys.stderr)

    def _send(self, status: int, body: str, content_type: str) -> None:
        data = body.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "public, max-age=3600")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(200, "ok", "text/plain; charset=utf-8")
            return
        if parsed.path == "/":
            self._send(200, LANDING, "text/html; charset=utf-8")
            return
        if parsed.path not in {"/card.svg", "/card-dark.svg"}:
            self._send(404, "not found", "text/plain; charset=utf-8")
            return

        query = parse_qs(parsed.query)
        username = (query.get("username") or [""])[0].strip()
        if not USERNAME_RE.match(username):
            self._send(400, _error_svg("invalid GitHub username"), "image/svg+xml")
            return
        try:
            year = int((query.get("year") or [""])[0])
        except ValueError:
            year = date.today().year
        if not 2008 <= year <= date.today().year + 1:
            self._send(400, _error_svg("invalid year"), "image/svg+xml")
            return

        try:
            stats = _cached_stats(username, year, self.token, self.max_commits)
            svg = build_svg(stats, dark=parsed.path.endswith("-dark.svg"))
        except Exception as exc:
            self._send(502, _error_svg(str(exc)), "image/svg+xml")
            return
        self._send(200, svg, "image/svg+xml; charset=utf-8")


LANDING = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CodeYear · 在线卡片</title>
<style>
:root{--paper:#f5f2e9;--ink:#141413;--muted:#6f6a5e;--line:#d8d2c2;--acc:#c8552f}
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);
  font-family:-apple-system,"Segoe UI","Microsoft YaHei",sans-serif}
.wrap{max-width:980px;margin:0 auto;padding:48px 28px 70px}
h1{font-family:Georgia,"Songti SC",serif;font-size:48px;font-weight:400;margin:0}
p{color:var(--muted);line-height:1.7}
.row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:28px 0 18px}
input,select{background:white;border:1px solid var(--line);padding:9px 10px;
  font:inherit;color:var(--ink);outline:none}
input{width:220px}
button{background:var(--acc);color:white;border:0;padding:10px 18px;
  font:inherit;font-weight:600;cursor:pointer}
button.secondary{background:#ece8dc;color:var(--ink)}
.preview{border:1px solid var(--line);padding:12px;background:transparent;
  min-height:120px;display:flex;align-items:center;justify-content:center}
img{max-width:100%;height:auto}
pre{white-space:pre-wrap;word-break:break-all;background:#ece8dc;padding:14px;
  font-family:Consolas,monospace;font-size:12px;line-height:1.6}
.hint{font-size:12px}
</style>
</head>
<body>
<div class="wrap">
  <h1>CodeYear</h1>
  <p>输入一个公开 GitHub 用户名，生成一张可嵌入 Profile README 的年度卡片。
     只读公开仓库；私有仓库请运行本地版 <code>codeyear scan</code>。</p>

  <div class="row">
    <input id="user" placeholder="GitHub username" value="octocat">
    <input id="year" type="number" value="__YEAR__" min="2008" max="__YEAR__" style="width:100px">
    <select id="theme"><option value="light">浅色</option><option value="dark">深色</option></select>
    <button onclick="loadCard()">生成</button>
  </div>

  <div class="preview"><img id="card" alt="CodeYear card"></div>

  <p class="hint">卡片会缓存 1 小时。公开数据受 GitHub API 限流影响；完整本地报告请安装 CodeYear。</p>

  <h3>嵌入到 Profile README</h3>
  <pre id="snippet"></pre>
  <button class="secondary" onclick="copySnippet()">复制嵌入代码</button>
</div>
<script>
let current = "";
function loadCard() {
  const user = document.getElementById("user").value.trim();
  const year = document.getElementById("year").value || "__YEAR__";
  const theme = document.getElementById("theme").value;
  const base = location.origin;
  const name = theme === "dark" ? "card-dark.svg" : "card.svg";
  const url = `${base}/${name}?username=${encodeURIComponent(user)}&year=${year}`;
  document.getElementById("card").src = url + "&t=" + Date.now();
  current = `<picture>
  <source media="(prefers-color-scheme: dark)" srcset="${base}/card-dark.svg?username=${encodeURIComponent(user)}&year=${year}">
  <img src="${base}/card.svg?username=${encodeURIComponent(user)}&year=${year}" width="640" alt="CodeYear ${year}">
</picture>`;
  document.getElementById("snippet").textContent = current;
}
function copySnippet() {
  navigator.clipboard.writeText(current).catch(() => {});
}
loadCard();
</script>
</body>
</html>
"""


def serve(
    host: str = "127.0.0.1",
    port: int = 8000,
    *,
    token: str | None = None,
    max_commits: int = 200,
) -> int:
    Handler.token = token
    Handler.max_commits = max_commits
    global LANDING
    LANDING = LANDING.replace("__YEAR__", str(date.today().year))
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"CodeYear card service: http://{host}:{port}", file=sys.stderr)
    print(f"Endpoint: /card.svg?username=octocat&year={date.today().year}", file=sys.stderr)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n停止。", file=sys.stderr)
    finally:
        httpd.server_close()
    return 0
