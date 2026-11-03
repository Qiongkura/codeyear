# CodeYear · 代码手账

> 扫描你本地的 git 仓库，生成一份**只属于你**的年度代码手账：纸面档案风格的
> HTML 报告、一张 2400×3200 高清海报，以及一张 2400×5300 的完整长图。
> 只读本地 git，不登录、不上传。

![CodeYear 报告预览](docs/report-preview.png)

**示例报告**：[docs/sample-report.html](docs/sample-report.html)（用本机仓库生成，可直接浏览器打开）

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

**设计**
- 纸面档案：暖纸底、墨色、朱红强调，衬线大标题 + 等宽数据，方角、hairline
- 动效：滚动进度条、逐段浮现、数字滚动、真实 commit 跑马灯、纸面风格 tooltip
- 纯 vanilla JS，不依赖任何第三方前端库；尊重 `prefers-reduced-motion`
- 字体：系统衬线（Georgia / Songti / SimSun）+ 等宽（Consolas），不加载任何外部字体

## 快速开始

需要 Python 3.9+、Git，以及 Pillow：

```bash
pip install -r requirements.txt

# 在项目根目录（和 codeyear/ 同级）运行
python -m codeyear scan I:\projects --year 2026 --open
```

或安装成命令：

```bash
pip install -e .
codeyear scan I:\projects --year 2026 --open
```

输出默认在 `./codeyear-output/`：

```text
codeyear-2026.html       纸面档案风格报告，浏览器直接打开
codeyear-2026.png        2400×3200 海报（2× 渲染），直接发图
codeyear-2026-long.png   2400×5300 完整长图，适合发长图/存档
codeyear-2026-card.svg   900×540 GitHub 主页卡片（浅色/深色主题都能放）
codeyear-2026.json       原始统计数据，方便二次开发
```

海报示例（同一份数据）：

<img src="docs/sample.png" width="420" alt="CodeYear PNG 海报示例">

完整长图示例：[docs/sample-long.png](docs/sample-long.png)

## 挂到 GitHub 主页

扫描时会额外生成 `codeyear-2026-card.svg`。把它提交到你的 Profile 仓库
（仓库名与用户名相同，例如 `Qiongkura/Qiongkura`），在 README 里加一行：

```md
[![CodeYear 2026](./codeyear-2026-card.svg)](https://github.com/Qiongkura/codeyear)
```

GitHub 会直接渲染这张 900×540 的 SVG 卡片，浅色/深色主题都能放。卡片是静态文件，
重新运行扫描并提交即可更新。

<img src="docs/sample-card.svg" width="720" alt="CodeYear GitHub 主页卡片示例">

## 只统计你自己的提交

- 自动读取全局 `git config user.name` / `user.email`，只保留你作为作者的提交。
- 想统计所有人：加 `--all-authors`。
- 想指定作者：加 `--author "you@example.com"`。
- 同一项目的副本（相同 `remote` 或相同首个 commit）只保留提交最多的一份。
- 提交用了别的邮箱/名字时可能被过滤，可用 `--author` 或 `--all-authors` 覆盖。

## 常用参数

| 参数 | 说明 |
| --- | --- |
| `--year 2026` | 统计年份，默认今年 |
| `--out ./out` | 输出目录 |
| `--author "you@example.com"` | 只统计匹配的 git author |
| `--all-authors` | 统计所有作者的提交（默认只统计你本人） |
| `--max-depth 6` | 向下扫描仓库的最大深度 |
| `--timeout 300` | 单个仓库的扫描超时（秒） |
| `--no-png` / `--no-html` | 只生成其中一种 |
| `--no-long` | 不生成完整版长图（默认生成） |
| `--no-card` | 不生成 GitHub 主页卡片 |
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
- 只读 `git log`、仓库根目录 README 的第一行和 `git remote`；不读取其它工作区文件。
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
- [ ] English README
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
