# CodeYear · 代码手账

**简体中文** | [English](README.en.md) · [中文简介](docs/intro.zh.md)

> 扫描你本地的 git 仓库，生成一份**只属于你**的年度代码手账：中英双语 HTML 报告、
> 2400×3200 海报、完整长图，以及 GitHub 主页卡片。只读本地 git，不登录、不上传。

![CodeYear 报告预览](docs/report-preview.png)

**示例报告**：[中文](docs/sample-report.html) · [English](docs/sample-report-en.html)
（脱敏演示数据，可直接浏览器打开）

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

喜欢终端就用：

```bash
codeyear tui
```

终端向导同样支持多目录、仓库数量、进度条和输出目录。

## 它是什么

CodeYear 是给开发者做的「年度报告」。官方的 Wrapped 通常只覆盖公开数据、还要授权；
而大多数人的代码在私有仓库、公司内网或 Gitee。CodeYear 直接读本机的 `.git`，
所以私有项目、离线环境、公司电脑都能用。

它默认**只统计你本人作者的提交**（按 git `user.name` / `user.email` 识别），
并且会把同一个项目的多个副本（`work/`、`backup/`、fork）合并成一个，不会重复计数。

## 报告里有什么

**年度之最**
- 最忙的一天 / 一周、最长连续、最长空窗、最大单次提交、最长的 commit
- 第一次与最后一次提交的时间、仓库

**仓库档案**（提交最多的 3 个仓库）
- 提交数、行变更、主要语言、首次→最近提交
- 最常改的文件、最近 3 条真实 commit
- 简介直接引用该仓库 README 的第一行

**全部仓库索引**
- 每个仓库的 README 一句话、技术栈、自有代码、最近提交、活跃状态
- 可按主要语言筛选；没写 README 的会如实标注

**数字**
- 月度节奏、7×24 提交时钟、全年热力图
- 代码构成（按行数排序）、语言构成、**语言栈季度变化**
- 提交规模分布、提交类型、高频词、**消息长度分布**
- 增删比（含删除最多的仓库）、**编码会话**（间隔 ≤ 2 小时的提交算一次）
- 仓库生命周期甘特图、**仓库墓园**（30 天没动）
- 最常改的文件（完整路径）
- 本地仓库考古：全历史提交总数、最早一次提交（码龄）、今年新开的仓库、版本 tag
  （仓库口径，与只统计你本人的年度数字分开展示）

**设计**
- 纸面档案：暖纸底、墨色、朱红强调，衬线大标题 + 等宽数据，方角、hairline
- 版式：书脊式目录、超大年份封面、浅色四格统计条；每节末尾「下一节」，
  滚动时目录高亮，右下角一键回到顶部
- 中英双语：同时生成中文和英文报告，页内可切换
- 纯 vanilla JS，不依赖任何第三方前端库；尊重 `prefers-reduced-motion`
- 字体：系统衬线（Georgia / Songti / SimSun）+ 等宽（Consolas），不加载任何外部字体
- GitHub 卡片：640×1254 海报式布局，透明底、无整块底色，浅色/深色两版，靠大字号、细线和一个陶土色强调区分层级
- 卡片内含 8 条大白话分析：主攻项目、写码时段、改动大小、一次写多久、写删比例、最忙月份、精力集中度、提交说明

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

> 注意：GitHub 会通过图片代理缓存 README 里的图片，更新同名 SVG 后主页可能仍显示旧图。
> 需要刷新时，把文件重命名为带版本号的名字（如 `codeyear-2026-card-v2.svg`）并同步改 README，
> 或在图片地址后加查询参数（如 `?v=2`）。

### 自动更新到 Profile 仓库

如果本地已经有 Profile 仓库的 clone：

```bash
# 只写入本地，不联网
codeyear scan ~/code --year 2026 --profile-repo ~/Qiongkura

# 确认后再提交并推送（联网）
codeyear scan ~/code --year 2026 --profile-repo ~/Qiongkura --push-profile
```

`--profile-repo` 要是本地 clone。默认只改本地文件；加 `--push-profile` 才会 commit/push，
且只包含卡片 SVG 和 Profile README，报告和 JSON 不会上传。

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

## 常用参数

| 参数 | 说明 |
| --- | --- |
| `--year 2026` | 统计年份，默认今年 |
| `--out ./out` | 输出目录 |
| `--author "you@example.com"` | 只统计匹配的 git author |
| `--all-authors` | 统计所有作者的提交（默认只统计你本人） |
| `--max-depth 6` | 向下查找仓库的最大文件夹层数 |
| `--timeout 300` | 单个仓库的扫描超时（秒） |
| `--no-png` / `--no-html` | 只生成其中一种 |
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
```

## 隐私

- 所有统计都在本地完成，**没有任何网络请求**。
- 只读 `git log`、`git tag`、仓库根目录 README 的第一行和 `git remote`；不读取其它工作区文件。
- 输出文件默认忽略在 `.gitignore` 里。
- 报告顶部与页脚标注 `LOCAL ONLY · 数据未上传`。
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
  --pretty=format:%H%x1f%ad%x1f%ae%x1f%an%x1f%s \
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
- [ ] 同比去年（2025 vs 2026）
- [ ] 文件级删除量（被删最多的文件）
- [ ] PyInstaller 打包 exe / 桌面壳
- [x] English README
- [x] 英文 HTML 报告
- [x] 可选同步 GitHub Profile（仅本地 / 提交推送）
- [x] 交互式向导（多目录 / 仓库数量 / 进度条 / 输出位置）
- [x] 桌面 GUI（Tkinter，可双击）
- [ ] GitHub / Gitee 公开数据模式（输入用户名即可生成）

## 开发

```bash
# 本地生成一份报告
python -m codeyear scan I:\projects --year 2026 --out ./out

# 语法检查
python -m compileall -q codeyear
```

代码结构：

```text
codeyear/
  scanner.py      找仓库 + 解析 git log + README 首行
  stats.py        聚合统计 / 身份过滤 / 副本合并 / 指标
  keywords.py     提交关键词提取
  languages.py    扩展名 → 语言映射与过滤
  html_report.py  纸面档案 HTML 报告（内联 CSS/JS）
  poster.py       PNG 海报（Pillow）
  personas.py     代码人格
  cli.py          命令行
```

## License

MIT
