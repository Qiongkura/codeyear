# 用 Cloudflare 上线卡片服务

如果你只有 Cloudflare，没有 VPS，最快的方式是用 **Cloudflare Tunnel** 把本机的
`codeyear serve` 暴露成一个 HTTPS 地址。不需要改代码，也不需要把服务迁到云端。

> 这是“本机常开 + Cloudflare 隧道”的方案，不是无服务器托管。
> 电脑关机或休眠时，卡片地址会不可用。

## 1. 安装 cloudflared

Windows：

```powershell
winget install --id Cloudflare.cloudflared
```

或者从 Cloudflare 的 GitHub Releases 下载 `cloudflared-windows-amd64.exe`，
改名为 `cloudflared.exe` 并放进 PATH。

确认：

```powershell
cloudflared --version
```

## 2. 启动卡片服务

先设置 GitHub token（公开模式用，提升 API 额度）：

```powershell
$env:GITHUB_TOKEN = "ghp_xxx"
codeyear serve --host 127.0.0.1 --port 8000 --max-commits 500
```

本机验证：

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/
http://127.0.0.1:8000/card.svg?username=octocat&year=2012&theme=paper
```

## 3. 快速隧道（先看效果）

另开一个 PowerShell：

```powershell
cloudflared tunnel --url http://127.0.0.1:8000
```

它会输出一个 `https://xxx.trycloudflare.com` 地址。打开这个地址就是卡片页；
卡片接口是：

```text
https://xxx.trycloudflare.com/card.svg?username=Qiongkura&year=2026
https://xxx.trycloudflare.com/card-dark.svg?username=Qiongkura&year=2026&theme=forest
```

这个地址每次重启 cloudflared 都会变，适合测试，不适合长期放主页。

## 4. 固定域名（推荐）

前提：域名已经托管在 Cloudflare。

```powershell
cloudflared tunnel login
cloudflared tunnel create codeyear-card
cloudflared tunnel route dns codeyear-card card.example.com
```

记下 `create` 输出的 UUID。新建
`C:\Users\<你>\.cloudflared\config.yml`：

```yaml
tunnel: <UUID>
credentials-file: C:\Users\<你>\.cloudflared\<UUID>.json
ingress:
  - hostname: card.example.com
    service: http://127.0.0.1:8000
  - service: http_status:404
```

启动：

```powershell
cloudflared tunnel run codeyear-card
```

然后把 `card.example.com` 当成正式地址：

```text
https://card.example.com/
https://card.example.com/card.svg?username=Qiongkura&year=2026&theme=paper
```

## 5. 让服务常驻

两个进程都要保持运行：

1. `codeyear serve`
2. `cloudflared tunnel run codeyear-card`

推荐用 Windows 任务计划程序，登录时启动 `codeyear serve`；
cloudflared 可以用：

```powershell
cloudflared service install
```

或者同样放进任务计划程序。先启动卡片服务，再启动隧道。

## 6. 注意

- 只读公开 GitHub 数据；私有仓库请用本地 `codeyear scan`。
- 必须设置 `GITHUB_TOKEN`，否则 API 限流很严重，且最多只拉 30 条提交。
- 卡片服务自带 1 小时内存缓存；Cloudflare 也会缓存 SVG。
- 电脑必须常开；这是 Tunnel 方案的限制。
- 如果被人刷接口，在 Cloudflare 控制台加 Rate Limiting 规则。
- 想完全脱离本机，需要：
  - **Cloudflare Containers**（Workers Paid）运行仓库里的 Docker 镜像；或
  - 把卡片渲染改写成 Cloudflare Worker（TypeScript），目前还没做。
