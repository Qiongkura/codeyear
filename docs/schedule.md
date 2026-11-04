# 定时更新私有项目的卡片

GitHub Action 只读取公开仓库。私有仓库要每天自动更新主页卡片，需要在能访问这些
仓库的机器上运行 `scan`，或者用 self-hosted runner。

## Windows 任务计划程序

1. 先手动确认这条命令能跑通：

```powershell
codeyear scan D:\code --year 2026 --profile-repo C:\path\to\Qiongkura --push-profile --fallback-previous
```

2. 打开「任务计划程序」→「创建基本任务」：
   - 触发器：每天，例如 12:00
   - 操作：启动程序
     - 程序：`cmd.exe`
     - 参数：`/c codeyear scan D:\code --year 2026 --profile-repo C:\path\to\Qiongkura --push-profile --fallback-previous >> C:\path\to\codeyear.log 2>&1`
     - 起始于：你的用户目录（确保能找到 `codeyear`）

3. 确认 Profile 仓库的 git 凭证已经保存（Git Credential Manager 即可）。

## macOS / Linux cron

```bash
# 每天 12:00
0 12 * * * cd /home/me && /usr/local/bin/codeyear scan /home/me/code --year 2026 --profile-repo /home/me/Qiongkura --push-profile --fallback-previous >> /home/me/.codeyear.log 2>&1
```

## GitHub Actions + self-hosted runner

如果已经有 self-hosted runner，可以把
[codeyear-card-self-hosted.yml](codeyear-card-self-hosted.yml) 复制到
`<用户名>/<用户名>/.github/workflows/`，然后在仓库的 **Settings → Variables**
里设置 `CODEYEAR_CODE_DIR` 为 runner 上代码目录的绝对路径。

这样私有项目只在本机/内网 runner 上读取，只有卡片 SVG 和 Profile README 会被推送。
