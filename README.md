# CodeYear · 代码手账

[![CI](https://github.com/Qiongkura/codeyear/actions/workflows/ci.yml/badge.svg)](https://github.com/Qiongkura/codeyear/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/Qiongkura/codeyear)](https://github.com/Qiongkura/codeyear/releases/latest)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org/)
[![Demo](https://img.shields.io/badge/demo-online-brightgreen)](https://qiongkura.github.io/codeyear/)

**简体中文** | [English](README.en.md) · [中文简介](docs/intro.zh.md)

> 扫描你本地的 git 仓库，生成一份**只属于你**的年度代码手账：中英双语 HTML 报告、
> 2400×3200 海报、完整长图，以及 GitHub 主页卡片。默认只读本地 git，不登录、不上传；
> 公开 GitHub 模式是可选联网功能。

![CodeYear 报告预览](docs/report-preview.png)

**在线示例**：[https://qiongkura.github.io/codeyear/](https://qiongkura.github.io/codeyear/)

**示例报告**：[中文](docs/sample-report.html) · [English](docs/sample-report-en.html)
（脱敏演示数据，可直接浏览器打开）

## 下载 / 安装

**Windows（不需要 Python）**：从 [Releases](https://github.com/Qiongkura/codeyear/releases/latest)
下载 `CodeYear.exe`，双击打开，选择项目目录即可。

**开发者**：

```bash
pip install git+https://github.com/Qiongkura/codeyear.git
codeyear
```

也可以从 Release 下载 wheel：

```bash
pip install https://github.com/Qiongkura/codeyear/releases/download/v0.2.11/codeyear-0.2.11-py3-none-any.whl
```

> exe 未做代码签名，Windows SmartScreen 可能提示；点「更多信息 → 仍要运行」。
> macOS / Linux 用 wheel 或源码运行。

## 30 秒上手

需要 Python 3.9+ 和 Git。把 `~/code` 换成你存放项目的文件夹（不是 CodeYear 仓库本身）：

```bash
git clone https://github.com/Qiongkura/codeyear.git
cd codeyear
pip install -r requirements.txt
python -m codeyear scan ~/code --open
```

或者用 uv 一行运行（需要先装 [uv](https://docs.astral.sh/uv/)）：

```bash
uvx --from git+https://github.com/Qiongkura/codeyear.git codeyear scan ~/code --open
```

Windows 把 `~/code` 换成 `C:\code` 之类的路径。报告会生成到 `codeyear-output/`，
`--open` 会自动打开 HTML。

## 图形界面 / 交互式向导

想点选操作，直接运行：

```bash
codeyear
```

会打开桌面窗口：添加多个目录、检查仓库数量、看进度条、选输出位置，完成后直接打开报告。
Windows 也可以在仓库根目录双击 `CodeYear.cmd`。

需要 Tkinter；Windows/macOS 的 Python 自带，Linux 装 `python3-tk`。安装后也可以运行 `codeyear-gui`。

## 界面语言

CLI 和终端向导默认跟随系统语言，也可以强制英文：

```bash
codeyear --lang en scan ~/code --open
CODEYEAR_LANG=en codeyear scan ~/code --open
```

`--lang` 要放在子命令前面。GUI 也跟随同一语言设置；报告本身一直是中英双语。

喜欢终端就用：

```bash
codeyear tui
```

终端向导同样支持多目录、仓库数量、进度条和输出目录。

## 公开 GitHub 模式（可选联网）

不想扫描本地仓库，可以先看一个公开账号：

```bash
codeyear github Qiongkura --year 2026 --out ./codeyear-github
```

- 只读公开仓库，不会读取私有仓库。
- **口径**：只统计该账号名下的公开仓库（GitHub `type=owner`），以及 GitHub 能关联到该账号的提交；组织仓库、collaborator 仓库、未绑定 GitHub 账号的邮箱提交不计入，合并提交也不计入。需要完整历史请用本地 `scan`。
- 需要网络；默认最多拉 200 条提交详情，可用 `--max-commits` 调整。
- 没有 token 时最多 30 条，且容易触发 GitHub API 限流；建议设置 `GITHUB_TOKEN` 或传 `--token`。
- 输出包含完整报告、海报、长图、卡片，以及 `codeyear-2026-embed.md`，可以直接粘到 Profile README。
- 只想要卡片：加 `--card-only`，跳过报告、海报和长图。
- 想直接更新 Profile 仓库：加 `--profile-repo ~/Qiongkura`（只写本地）或再加 `--push-profile`（联网推送）。
- 跨年自动更新：加 `--fallback-previous`，当年还没有提交时继续用上一年的卡片。
- 重复运行更快：加 `--cache-dir ~/.cache/codeyear` 缓存 commit 详情（按 SHA，不会过期）。
- 卡片主题：`--theme paper|mono|forest|ocean`；[主题预览](docs/themes.md)。
- 本地 `scan` 仍是默认模式，代码不会上传。

### 在线卡片服务

```bash
codeyear serve --port 8000
```

打开 `http://127.0.0.1:8000`，输入用户名即可生成卡片；服务端带 1 小时 LRU 缓存和每 IP 限流。

部署到 Render / Railway / Fly / VPS：设置 `GITHUB_TOKEN`，启动命令：

```bash
codeyear serve --host 0.0.0.0 --port $PORT --max-commits 500
```

仓库里带 `Dockerfile` 和 `render.yaml`，Render 可以直接识别。镜像也会发布到 GHCR
（包默认私有，需要在 GitHub 的 Package settings 里设为 Public 后匿名拉取）：

```bash
docker run -p 8000:8000 -e GITHUB_TOKEN=your_token ghcr.io/qiongkura/codeyear:latest
```

```text
https://your-host/card.svg?username=Qiongkura&year=2026
https://your-host/card-dark.svg?username=Qiongkura&year=2026
```

`--max-commits` 是每次最多拉多少条提交详情，不是 GitHub 的总提交数；每条详情一次 API 请求。
默认 200，无 token 会自动降为 30。要更完整就设置 token 并调大；完整本地历史仍用 `scan`。

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/Qiongkura/codeyear)

如果只有 Cloudflare，可以用 Tunnel 把本机服务暴露出去：
[Cloudflare Tunnel 部署步骤](docs/cloudflare.md)。

> Action 和在线服务都只使用公开 GitHub 数据；要自动更新包含私有项目的本地卡片，
> 需要本机定时任务或自托管 runner。
>
> Action 会自动把卡片块写进 Profile README（首次运行也会插入），并使用带版本号的
> 文件名绕过 GitHub 的图片缓存；无需手动粘贴 embed 片段。模板默认每天 04:00 UTC
> 更新；改 workflow 里的 `cron` 可切成每周一 `0 4 * * 1` 或每月 1 日 `0 4 1 * *`。
> 跨年时如果新的一年还没有提交，`--fallback-previous` 会继续显示上一年的卡片。
> 模板直接安装 Release 里的 wheel；升级时改 `CODEYEAR_VERSION`（当前 `0.2.11`）。

GitHub Action 自动更新模板：[docs/codeyear-card.yml](docs/codeyear-card.yml)。

用法：

1. 在 `<用户名>/<用户名>` 仓库新建 `.github/workflows/codeyear-card.yml`
2. 粘贴模板内容
3. 在 Actions 页面手动运行一次 `Update CodeYear card`

之后按 cron 自动更新；README 里没有卡片块时会自动插入，有旧年份引用时会自动替换。

## 它是什么

CodeYear 是给开发者做的「年度报告」。官方的 Wrapped 通常只覆盖公开数据、还要授权；
而大多数人的代码在私有仓库、公司内网或 Gitee。CodeYear 直接读本机的 `.git`，
所以私有项目、离线环境、公司电脑都能用。

它默认**只统计你本人作者的提交**（按 git `user.name` / `user.email` 识别），
并且会把同一个项目的多个副本（`work/`、`backup/`、fork）合并成一个，不会重复计数。

## 报告里有什么

**年度概览**
- 一个总结称号，按数据选（夜里出活的人、主要在和 bug 打交道的人、删代码比写代码还多的人…）
- 4 个指标标签（提交 / 语言 / 仓库 / 活跃日）+ 一段数字总结

**年度之最**
- 最忙的一天 / 一周、最长连续、最长空窗、最大单次提交、最长的 commit
- 第一次与最后一次提交的时间、仓库

**仓库档案**（提交最多的 3 个仓库）
- 提交数、行变更、主要语言、首次→最近提交
- 最常改的文件、最近 3 条真实 commit
- 简介直接引用该仓库 README 的第一行

**全部仓库索引**
- 每个仓库的 README 一句话、技术栈、自有代码、最近提交、活跃状态
- 可按主要语言筛选、按关键词搜索；没写 README 的会如实标注

**数据分析**
- 月度节奏、7×24 提交时钟、全年热力图
- 代码构成（按行数排序）、语言构成、**语言栈季度变化**
- 提交规模分布、提交类型、高频词、**消息长度分布**
- 增删比（含删除最多的仓库）、**编码会话**（间隔 ≤ 2 小时的提交算一次）
- 仓库生命周期甘特图、**仓库墓园**（30 天没动）
- 最常改的文件（完整路径）
- 本地仓库考古：全历史提交总数、最早一次提交（码龄）、今年新开的仓库、版本 tag
  （仓库口径，与只统计你本人的年度数字分开展示）
- 同比去年：`--compare` 会多扫一年；封面显示摘要，数据分析区有 10 项指标对照和 12 个月双柱图

**设计**
- 纸面档案：暖纸底、墨色、朱红强调，衬线大标题 + 等宽数据，方角、hairline
- 版式：书脊式目录、超大年份封面（标注本次扫描目录）、浅色四格统计条；
  每节末尾「下一节」，滚动时目录高亮，右下角一键回到顶部
- 动效：整页轻微淡入，目录高亮和链接颜色有短过渡；不做滚动弹跳、数字滚动；尊重 `prefers-reduced-motion`
- 中英双语：同时生成中文和英文报告，页内可切换
- 纯 vanilla JS，不依赖任何第三方前端库；尊重 `prefers-reduced-motion`
- 字体：系统衬线（Georgia / Songti / SimSun）+ 等宽（Consolas），不加载任何外部字体
- GitHub 卡片：640×1254 海报式布局，透明底、无整块底色，浅色/深色两版，靠大字号、细线和一个陶土色强调区分层级
- 卡片内有 8 条大白话分析：主攻项目、写码时段、改动大小、一次写多久、写删比例、最忙月份、精力集中度、提交说明
- 卡片主题：paper / mono / forest / ocean；公开卡片服务支持 `theme` 参数
- 报告可直接通过浏览器打印/导出 PDF
- 可访问性：跳过导航链接、键盘焦点样式、图表 aria-label

## 安装与输出

上面的命令只会安装 Pillow。想把 CodeYear 安装成全局命令：

```bash
pip install -e .
codeyear scan ~/code --year 2026 --open
```

输出默认在 `./codeyear-output/`：

```text
codeyear-2026.html          中文报告，浏览器直接打开
codeyear-2026-en.html       英文报告，同一份数据
codeyear-2026.png           2400×3200 海报（2× 渲染），直接发图
codeyear-2026-long.png      2400×5330 完整长图，适合发长图/存档
codeyear-2026-card.svg      640×1254 海报式 GitHub 卡片（透明底 · 浅色）
codeyear-2026-card-dark.svg 640×1254 同一张卡片的深色版（透明底）
codeyear-2026.json          原始统计数据，方便二次开发
```

海报示例（同一份数据）：

<img src="docs/sample.png" width="420" alt="CodeYear PNG 海报示例">

完整长图示例：[docs/sample-long.png](docs/sample-long.png)

## 挂到 GitHub 主页

扫描时会额外生成浅色和深色两张卡片，都没有背景色。把两个文件一起提交到你的
Profile 仓库（仓库名与用户名相同，例如 `Qiongkura/Qiongkura`），在 README 里用
`<picture>` 按主题切换：

```md
<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./codeyear-2026-card-dark.svg">
  <img src="./codeyear-2026-card.svg" width="640" alt="CodeYear 2026">
</picture>
```

使用 `<picture>` 时，GitHub 在浅色/深色主题下会自动选对应版本；如果只写 `<img>`，
深色主题下会显示浅色版。卡片是静态文件，重新运行扫描并提交即可更新。

> 注意：GitHub 会通过图片代理缓存 README 里的图片。用 `--profile-repo` 或下面的
> Action 时，CodeYear 会自动使用带版本号的文件名并同步改 README，避免主页显示旧图；
> 手动提交时则需要自己重命名文件或加查询参数。

### 自动更新到 Profile 仓库

如果本地已经有 Profile 仓库的 clone：

```bash
# 私有项目：扫描本地代码，只写入 Profile 仓库（不联网）
codeyear scan ~/code --year 2026 --profile-repo ~/Qiongkura

# 确认后再提交并推送（联网）
codeyear scan ~/code --year 2026 --profile-repo ~/Qiongkura --push-profile

# 跨年定时任务：当年还没有提交时沿用上一年的卡片
codeyear scan ~/code --year 2026 --profile-repo ~/Qiongkura --push-profile --fallback-previous
```

只有公开数据也可以直接更新 Profile：

```bash
codeyear github Qiongkura --year 2026 --card-only \
  --profile-repo ~/Qiongkura --push-profile
```

`--profile-repo` 要是本地 clone。默认只改本地文件；加 `--push-profile` 才会 commit/push，
且只包含卡片 SVG 和 Profile README，报告和 JSON 不会上传。每次更新会写入
`codeyear-2026-card-vN.svg` 并重写 README，同时清掉旧版本文件；跨年时也会把 README
里上一年的引用替换成新一年的卡片。

私有仓库要定时更新，可以用 Windows 任务计划、cron 或 self-hosted runner：
[定时更新私有项目卡片](docs/schedule.md)。

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/sample-card-dark.svg">
  <img src="docs/sample-card.svg" width="640" alt="CodeYear GitHub 主页卡片示例">
</picture>

## 只统计你自己的提交

- 自动读取全局 `git config user.name` / `user.email`，只保留你作为作者的提交。
- 想统计所有人：加 `--all-authors`。
- 想指定作者：加 `--author "you@example.com"`。
- 同一项目的副本（相同 `remote` 或相同首个 commit）只保留提交最多的一份。
- 「累计提交」与「最早提交」是仓库口径：按去重后的全部本地仓库统计，不按作者过滤；
  年度提交数仍只统计你本人。
- 提交用了别的邮箱/名字时可能被过滤，可用 `--author` 或 `--all-authors` 覆盖。
- 保留旧邮箱/旧名字：`--alias "old@example.com"`，可重复；这些提交仍算你本人。
- 仓库里有 `.mailmap` 时会自动使用，把旧邮箱/名字映射到当前身份；不想用加 `--no-mailmap`。
- 默认只看当前分支；加 `--all-branches` 会统计所有本地分支/tag 的提交（合并提交仍不计入）。
  GUI 里对应「旧邮箱/名字」输入框，多个用逗号分隔。

## 常用参数

| 参数 | 说明 |
| --- | --- |
| `--year 2026` | 统计年份，默认今年 |
| `--out ./out` | 输出目录 |
| `--author "you@example.com"` | 只统计匹配的 git author |
| `--all-authors` | 统计所有作者的提交（默认只统计你本人） |
| `--compare` | 同时扫描去年，生成同比数据（扫描时间翻倍） |
| `--fallback-previous` | 当年没有提交时回退到上一年，适合跨年定时任务 |
| `--alias "old@example.com"` | 额外作者邮箱/名字，可重复 |
| `--no-mailmap` | 忽略仓库里的 `.mailmap`（默认自动使用） |
| `--all-branches` | 统计所有本地分支/tag 的提交（默认只看当前分支） |
| `--max-depth 6` | 每个根目录向下查找仓库的最大文件夹层数 |
| `--timeout 300` | 单个仓库的扫描超时（秒） |
| `--jobs 4` | 并行扫描的仓库数，项目多时明显加快 |
| `--no-png` / `--no-html` | 跳过 PNG / HTML（可同时使用） |
| `--no-long` | 不生成完整版长图（默认生成） |
| `--no-card` | 不生成 GitHub 主页卡片 |
| `--profile-repo PATH` | 写入本地 Profile 仓库的卡片与 README（不联网） |
| `--push-profile` | 更新后提交并推送 Profile 仓库（联网） |
| `--open` | 生成后自动打开报告 |
| `--quiet` | 不打印扫描进度 |

示例：

```bash
# 只统计某个仓库
codeyear scan . --year 2026

# 多仓库 + 指定作者
codeyear scan D:\code --year 2026 --author "you@example.com"

# 包含团队里其他人的提交
codeyear scan D:\code --year 2026 --all-authors

# 多个根目录
codeyear scan D:\work E:\oss --year 2026

# 和去年对比
codeyear scan D:\code --year 2026 --compare
```

## 配置文件（可选）

常用参数可以写进 `~/.codeyear.json`（或用 `CODEYEAR_CONFIG` 指定路径）：

```json
{
  "roots": ["D:/code"],
  "year": 2026,
  "aliases": ["old@example.com"],
  "compare": true,
  "all_branches": true,
  "jobs": 4,
  "out": "codeyear-output"
}
```

支持 `roots / year / out / author / all_authors / aliases / compare /
fallback_previous / all_branches / no_mailmap / jobs / max_depth / timeout /
theme / max_commits / open`。命令行显式参数优先于配置文件；文件不存在或字段
类型不对时会自动忽略。

## 隐私

- 默认 `scan` 模式所有统计都在本地完成，**没有任何网络请求**。
- `github` 公开模式、`serve` 在线服务和 `--push-profile` 是可选联网功能；它们只读取公开 GitHub 数据或推送卡片，不会上传本地代码。
- 本地模式只读 `git log`、`git tag`、仓库根目录 README 的第一行和 `git remote`；不读取其它工作区文件。
- 输出文件默认忽略在 `.gitignore` 里。
- 本地报告页脚标注 `LOCAL ONLY · 数据未上传`；公开模式报告会标注公开数据来源。
- 遇到 git 的 `dubious ownership`（常见于拷贝来的仓库），只对当前仓库做一次
  `safe.directory` 重试，不会改你的全局 git 配置。

## 已知限制

- 只统计 `--no-merges` 的提交；合并提交本身不计入。
- 使用 author date（`%ad`），跨时区协作时以提交者本地时间为准。
- 二进制、图片、锁文件和构建产物不参与语言/文件统计。
- 同一个 commit 出现在多个仓库时只计一次。
- “自有代码”按非空行统计，已排除第三方库、生成工程与模型目录；不同项目的口径
  在报告「关于本报告」里也会写明。

## 工作原理

对每个仓库执行一次：

```text
git log --since=2026-01-01 --until=2027-01-01 \
  --pretty=format:%H%x1f%ad%x1f%aE%x1f%aN%x1f%s \
  --numstat --no-renames --no-merges
```

然后：

1. 按作者身份过滤，只保留你本人的提交；
2. 按 commit hash 去重，按项目血统合并副本；
3. 按天、小时、星期、季度、语言、文件聚合；
4. 生成纸面报告与海报。

语言根据扩展名映射；锁文件、构建产物、图片和二进制会被过滤掉，
避免 `package-lock.json` 抢走「最常改的文件」。

## 路线图

- [x] 纸面档案风格 HTML 报告 + 动效
- [x] 只统计本人提交（`--all-authors` 可关闭）
- [x] 项目副本按血统合并
- [x] 年度之最 / 7×24 / 编码会话 / 季度语言 / 仓库墓园
- [x] PNG 海报重绘为纸面主题
- [x] 同比去年（封面摘要 + 数据分析面板）
- [ ] 文件级删除量（被删最多的文件）
- [x] PyInstaller 打包 exe / 桌面壳
- [x] English README
- [x] 英文 HTML 报告
- [x] 可选同步 GitHub Profile（仅本地 / 提交推送）
- [x] 每日自动更新 GitHub 主页卡片（GitHub Action）
- [x] 交互式向导（多目录 / 仓库数量 / 进度条 / 输出位置）
- [x] 桌面 GUI（Tkinter，可双击）
- [x] GitHub 公开数据模式（输入用户名即可生成）
- [x] 在线卡片服务（Render / Docker / Cloudflare Tunnel）
- [ ] Gitee 公开数据模式
- [x] 卡片主题（paper / mono / forest / ocean）
- [x] 仓库搜索与打印样式
- [x] 多目录 CLI
- [x] pytest 测试 + GitHub Actions CI

## 开发

```bash
# 本地生成一份报告
python -m codeyear scan I:\projects --year 2026 --out ./out

# 语法检查
python -m compileall -q codeyear

# 代码风格
ruff check codeyear tests tools

# 测试 + 覆盖率（CI 门槛 75%，UI/海报模块不计入）
pip install -e ".[dev]"
pytest -q --cov=codeyear --cov-report=term-missing
```

代码结构：

```text
codeyear/
  scanner.py      找仓库 + 解析 git log + README 首行
  stats.py        聚合统计 / 身份过滤 / 副本合并 / 指标
  keywords.py     提交关键词提取
  languages.py    扩展名 → 语言映射与过滤
  html_report.py  纸面档案 HTML 报告（内联 CSS/JS）
  report_theme.py 新版报告主题 / 英文版
  card.py         GitHub 主页卡片
  poster.py       PNG 海报（Pillow）
  personas.py     代码人格
  github_public.py 公开 GitHub 数据模式
  runner.py       扫描 + 渲染流水线（GUI/向导共用）
  gui.py          Tkinter 桌面界面
  wizard.py       终端交互向导
  server.py       公开卡片 HTTP 服务
  profile.py      本地 / 推送 Profile 卡片同步
  cli.py          命令行
```

## License

MIT
