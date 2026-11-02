"""Lightweight keyword extraction for commit subjects (no third-party deps).

English words are extracted with a regex. Chinese has no whitespace, so we
count 2-character n-grams and drop a stopword list of high-frequency commit
vocabulary. It is deliberately simple: the goal is a fun word cloud, not NLP.
"""

from __future__ import annotations

import re
from collections import Counter

EN_STOP: set[str] = {
    # conventional commit noise
    "fix", "fixes", "fixed", "feat", "feature", "features", "chore", "docs",
    "doc", "refactor", "style", "test", "tests", "build", "ci", "release",
    "version", "bump", "merge", "branch", "revert", "update", "updates",
    "updated", "add", "adds", "added", "remove", "removes", "removed",
    "delete", "deleted", "change", "changes", "changed", "improve",
    "improves", "improved", "support", "supports", "initial", "init",
    "commit", "commit", "wip", "minor", "major", "patch", "new", "use",
    "using", "used", "make", "makes", "made", "move", "moves", "moved",
    "rename", "renamed", "cleanup", "clean", "cleanup", "misc", "small",
    "readme", "license", "gitignore",
    # generic English
    "the", "and", "for", "with", "from", "this", "that", "these", "those",
    "into", "onto", "over", "under", "when", "where", "which", "while",
    "then", "than", "also", "only", "just", "more", "less", "some", "any",
    "all", "not", "but", "can", "could", "should", "would", "will", "may",
    "have", "has", "had", "was", "were", "are", "is", "be", "been", "being",
    "you", "your", "our", "their", "its", "it", "we", "they", "them",
    "via", "per", "after", "before", "during", "without", "within",
    "file", "files", "code", "project", "work", "stuff", "thing", "things",
    "todo", "note", "notes", "error", "errors", "issue", "issues",
    "test", "tests", "type", "types", "line", "lines", "page", "pages",
}

# High-frequency Chinese 2-grams that carry little meaning in a word cloud.
ZH_STOP_2: set[str] = {
    "修复", "更新", "新增", "添加", "删除", "修改", "优化", "重构", "调整",
    "支持", "实现", "使用", "增加", "解决", "完善", "测试", "文档", "版本",
    "功能", "问题", "代码", "项目", "文件", "部分", "相关", "进行", "一个",
    "可以", "已经", "没有", "这个", "那个", "以及", "但是", "因为", "所以",
    "如果", "或者", "并且", "同时", "目前", "现在", "还是", "就是", "不是",
    "不能", "需要", "可能", "我们", "你们", "他们", "自己", "一下", "一些",
    "这些", "那些", "所有", "主要", "默认", "临时", "合并", "分支", "提交",
    "首次", "初始", "补充", "改进", "处理", "逻辑", "页面", "接口", "数据",
    "用户", "系统", "模块", "配置", "参数", "样式", "组件", "服务", "环境",
    "本地", "线上", "生产", "开发", "调试", "编译", "部署", "发布", "回滚",
    "兼容", "性能", "安全", "错误", "异常", "警告", "日志", "缓存", "网络",
    "请求", "响应", "数据库", "字段", "表格", "列表", "详情", "编辑", "创建",
    "初始化", "加载", "显示", "隐藏", "点击", "输入", "输出", "上传", "下载",
    "导入", "导出", "已经", "重新", "再次", "直接", "通过", "根据", "对于",
    "关于", "用于", "位于", "包括", "包含", "提供", "获取", "设置", "打开",
    "关闭", "开始", "结束", "完成", "失败", "成功", "正常", "默认", "手动",
    "自动", "简单", "复杂", "小型", "大型", "新的", "旧的", "当前", "之前",
    "之后", "现在", "今年", "今天", "昨天", "明天", "最后", "第一", "第二",
    "一下", "一直", "一起", "一样", "一定", "非常", "比较", "更加", "最好",
}

_CJK_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
_EN_RE = re.compile(r"[A-Za-z][A-Za-z0-9_+#.\-]{2,}")
_PREFIX_RE = re.compile(r"^\s*(?:[A-Za-z]+(?:\([^)]*\))?!?:|[^\s:：]{1,8}[:：])\s*")

# Chinese 2-grams containing these characters are usually grammatical glue,
# not meaningful keywords ("个原", "的功", ...).
_ZH_SKIP_CHARS = set(
    "个的了在是和与及把被对为以于之其此该每各等即并或而则因所由从到向给让使"
    "得地着过这那有没就都也很还再又最更太我你他她它们一二三四五六七八九十"
)


def _strip_prefix(text: str) -> str:
    return _PREFIX_RE.sub("", text, count=1)


def extract_keywords(subjects: list[str], top: int = 14) -> list[tuple[str, int]]:
    counts: Counter[str] = Counter()

    for raw in subjects:
        text = _strip_prefix(raw)
        for word in _EN_RE.findall(text):
            word = word.lower().strip(".-_")
            if len(word) >= 3 and word not in EN_STOP:
                counts[word] += 1
        for seq in _CJK_RE.findall(text):
            for i in range(len(seq) - 1):
                gram = seq[i:i + 2]
                if gram[0] in _ZH_SKIP_CHARS or gram[1] in _ZH_SKIP_CHARS:
                    continue
                if gram not in ZH_STOP_2:
                    counts[gram] += 1

    # Single occurrences are usually noise; keep them only when we have little data.
    min_count = 2 if sum(counts.values()) >= 40 else 1
    items = [(k, v) for k, v in counts.items() if v >= min_count]
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    return items[:top]
