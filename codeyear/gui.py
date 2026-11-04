"""Desktop GUI for CodeYear, built with Tkinter (no extra dependency)."""

from __future__ import annotations

import contextlib
import ctypes
import os
import queue
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import date
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from . import i18n
from .runner import detect_identity, discover, render, scan
from .stats import fmt_int

PAPER = "#f5f2e9"
PAPER2 = "#ece8dc"
INK = "#141413"
MUTED = "#6f6a5e"
ACCENT = "#c8552f"
LINE = "#d8d2c2"


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.roots: list[Path] = []
        self.queue: queue.Queue = queue.Queue()
        self.identity = detect_identity()
        self.written: list[tuple[str, Path]] = []
        self.html_path: Path | None = None
        self.busy = False

        root.title(i18n.tr("CodeYear · 代码手账"))
        root.geometry("860x960")
        root.minsize(760, 720)
        root.configure(bg=PAPER)
        self._style()
        self._build()
        self._poll()

    def _style(self) -> None:
        style = ttk.Style()
        with contextlib.suppress(tk.TclError):
            style.theme_use("clam")
        style.configure(
            "CY.Horizontal.TProgressbar",
            troughcolor=PAPER2, background=ACCENT, bordercolor=LINE,
            lightcolor=ACCENT, darkcolor=ACCENT, thickness=8,
        )
        style.configure(
            "CY.Vertical.TScrollbar",
            background=PAPER2, troughcolor=PAPER, bordercolor=LINE,
            arrowcolor=MUTED, relief="flat",
        )
        style.configure(
            "CY.TEntry",
            fieldbackground="white", foreground=INK, bordercolor=LINE,
            lightcolor=LINE, darkcolor=LINE, padding=(6, 4),
            font=("Consolas", 10),
        )
        style.map("CY.TEntry", fieldbackground=[("disabled", PAPER2)],
                  foreground=[("disabled", MUTED)])
        style.configure(
            "CY.TSpinbox",
            fieldbackground="white", foreground=INK, background=PAPER2,
            arrowcolor=MUTED, bordercolor=LINE, lightcolor=LINE,
            darkcolor=LINE, padding=(6, 4), font=("Consolas", 10),
        )
        style.map("CY.TSpinbox", fieldbackground=[("disabled", PAPER2)],
                  foreground=[("disabled", MUTED)])
        style.configure(
            "CY.TButton",
            background=PAPER2, foreground=INK, bordercolor=LINE,
            lightcolor=PAPER2, darkcolor=PAPER2, padding=(12, 6),
            font=("Microsoft YaHei", 9),
        )
        style.map(
            "CY.TButton",
            background=[("active", "#ddd7c8"), ("disabled", PAPER2)],
            foreground=[("disabled", MUTED)],
        )
        style.configure(
            "Accent.TButton",
            background=ACCENT, foreground="white", bordercolor=ACCENT,
            lightcolor=ACCENT, darkcolor=ACCENT, padding=(18, 8),
            font=("Microsoft YaHei", 10, "bold"),
        )
        style.map(
            "Accent.TButton",
            background=[("active", "#a8431f"), ("disabled", "#d8a08c")],
            foreground=[("disabled", "#f5e6df")],
        )
        style.configure(
            "CY.TCheckbutton",
            background=PAPER, foreground=INK, indicatorbackground="white",
            indicatorforeground=INK, indicatorrelief="flat",
            padding=(0, 2), font=("Microsoft YaHei", 9),
        )
        style.map(
            "CY.TCheckbutton",
            background=[("active", PAPER)],
            foreground=[("disabled", MUTED)],
        )
        style.configure(
            "CY.TLabelframe",
            background=PAPER, bordercolor=LINE, lightcolor=LINE,
            darkcolor=LINE, relief="solid", borderwidth=1,
        )
        style.configure(
            "CY.TLabelframe.Label",
            background=PAPER, foreground=INK,
            font=("Microsoft YaHei", 10, "bold"),
        )

    def _build(self) -> None:
        pad = {"padx": 22}

        header = tk.Frame(self.root, bg=PAPER)
        header.pack(fill="x", **pad, pady=(22, 10))
        tk.Label(
            header, text=i18n.tr("代码手账"), bg=PAPER, fg=INK,
            font=("Georgia", 26), anchor="w",
        ).pack(anchor="w")
        tk.Label(
            header, text=i18n.tr("选择目录，生成一份本地年度代码报告。"),
            bg=PAPER, fg=MUTED, font=("Microsoft YaHei", 10), anchor="w",
        ).pack(anchor="w", pady=(4, 0))

        body = tk.Frame(self.root, bg=PAPER)
        body.pack(fill="both", expand=True, **pad)

        # ---- folders -------------------------------------------------
        folder_box = ttk.LabelFrame(
            body, text=i18n.tr("扫描目录"), style="CY.TLabelframe", padding=0,
        )
        folder_box.pack(fill="x", pady=(6, 12))

        list_wrap = tk.Frame(folder_box, bg=PAPER)
        list_wrap.pack(fill="x", padx=12, pady=(8, 6))
        self.folder_list = tk.Listbox(
            list_wrap, height=5, selectmode=tk.EXTENDED, exportselection=False,
            bg="white", fg=INK, relief="flat", highlightthickness=1,
            highlightbackground=LINE, highlightcolor=LINE,
            selectbackground=ACCENT, selectforeground="white",
            font=("Consolas", 10),
        )
        self.folder_list.pack(side="left", fill="x", expand=True)
        scroll = ttk.Scrollbar(
            list_wrap, orient="vertical", style="CY.Vertical.TScrollbar",
            command=self.folder_list.yview)
        scroll.pack(side="right", fill="y")
        self.folder_list.configure(yscrollcommand=scroll.set)

        buttons = tk.Frame(folder_box, bg=PAPER)
        buttons.pack(fill="x", padx=12, pady=(0, 10))
        self._button(buttons, i18n.tr("添加目录"), self._add_folder).pack(side="left")
        self._button(buttons, i18n.tr("删除选中"), self._remove_folder).pack(
            side="left", padx=(8, 0))
        self._button(buttons, i18n.tr("清空"), self._clear_folders).pack(
            side="left", padx=(8, 0))
        self._button(buttons, i18n.tr("检查仓库"), self._check_repos).pack(
            side="left", padx=(8, 0))
        self.count_label = tk.Label(
            buttons, text=i18n.tr("可添加多个目录"), bg=PAPER, fg=MUTED,
            font=("Microsoft YaHei", 9),
        )
        self.count_label.pack(side="right")

        # ---- options -------------------------------------------------
        options = tk.Frame(body, bg=PAPER)
        options.pack(fill="x", pady=(0, 12))

        tk.Label(options, text=i18n.tr("年份"), bg=PAPER, fg=MUTED,
                 font=("Microsoft YaHei", 9)).grid(row=0, column=0, sticky="w")
        self.year_var = tk.StringVar(value=str(date.today().year))
        ttk.Entry(
            options, width=8, textvariable=self.year_var, style="CY.TEntry",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        tk.Label(options, text=i18n.tr("扫描层级"), bg=PAPER, fg=MUTED,
                 font=("Microsoft YaHei", 9)).grid(
            row=0, column=1, sticky="w", padx=(22, 0))
        self.depth_var = tk.StringVar(value="6")
        ttk.Entry(
            options, width=6, textvariable=self.depth_var, style="CY.TEntry",
        ).grid(row=1, column=1, sticky="w", padx=(22, 0), pady=(2, 0))

        if self.identity:
            email, name = self.identity
            who = f"{name} <{email}>" if name and email else (email or name)
            identity_text = i18n.tr("只统计我本人（{who}）", who=who)
        else:
            identity_text = i18n.tr("未检测到 git 身份，将统计所有作者")
        self.identity_var = tk.BooleanVar(value=bool(self.identity))
        self.identity_box, self._identity_draw = self._check(
            options, identity_text, self.identity_var,
            enabled=bool(self.identity),
        )
        self.identity_box.grid(
            row=0, column=2, rowspan=2, sticky="w", padx=(26, 0))

        tk.Label(
            body, text=i18n.tr(
                "扫描层级 = 向下查找仓库的文件夹层数，默认 6。"
            ),
            bg=PAPER, fg=MUTED, font=("Microsoft YaHei", 8), anchor="w",
        ).pack(fill="x", pady=(0, 10))

        advanced = tk.Frame(body, bg=PAPER)
        advanced.pack(fill="x", pady=(0, 10))
        tk.Label(advanced, text=i18n.tr("并行数"), bg=PAPER, fg=MUTED,
                 font=("Microsoft YaHei", 9)).pack(side="left")
        self.jobs_var = tk.StringVar(value="1")
        ttk.Entry(
            advanced, width=4, textvariable=self.jobs_var, style="CY.TEntry",
        ).pack(side="left", padx=(6, 20))
        self.compare_var = tk.BooleanVar(value=False)
        compare_box, self._compare_draw = self._check(
            advanced, i18n.tr("同比去年"), self.compare_var,
        )
        compare_box.pack(side="left")
        self.all_branches_var = tk.BooleanVar(value=False)
        branches_box, self._branches_draw = self._check(
            advanced, i18n.tr("所有分支"), self.all_branches_var,
        )
        branches_box.pack(side="left", padx=(16, 0))
        tk.Label(advanced, text=i18n.tr("旧邮箱/名字"), bg=PAPER, fg=MUTED,
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(22, 6))
        self.alias_var = tk.StringVar(value="")
        ttk.Entry(
            advanced, width=22, textvariable=self.alias_var, style="CY.TEntry",
        ).pack(side="left")

        out_row = tk.Frame(body, bg=PAPER)
        out_row.pack(fill="x", pady=(0, 14))
        tk.Label(out_row, text=i18n.tr("输出目录"), bg=PAPER, fg=MUTED,
                 font=("Microsoft YaHei", 9)).pack(side="left", padx=(0, 8))
        self.out_var = tk.StringVar(value="codeyear-output")
        ttk.Entry(
            out_row, textvariable=self.out_var, style="CY.TEntry",
        ).pack(side="left", fill="x", expand=True)
        self._button(out_row, i18n.tr("选择…"), self._choose_output).pack(
            side="left", padx=(8, 0))

        # ---- actions -------------------------------------------------
        actions = tk.Frame(body, bg=PAPER)
        actions.pack(fill="x", pady=(0, 10))
        self.start_btn = ttk.Button(
            actions, text=i18n.tr("开始生成"), command=self._start,
            style="Accent.TButton", cursor="hand2",
        )
        self.start_btn.pack(side="left")
        self.open_btn = self._button(
            actions, i18n.tr("打开报告"), self._open_report,
        )
        self.open_btn.configure(state="disabled")
        self.open_btn.pack(side="left", padx=(10, 0))
        self.folder_btn = self._button(
            actions, i18n.tr("打开输出目录"), self._open_output,
        )
        self.folder_btn.configure(state="disabled")
        self.folder_btn.pack(side="left", padx=(10, 0))

        self.progress = ttk.Progressbar(
            body, style="CY.Horizontal.TProgressbar", mode="determinate",
        )
        self.progress.pack(fill="x", pady=(4, 6))
        self.status = tk.Label(
            body, text=i18n.tr("选择目录后点击「开始生成」。"),
            bg=PAPER, fg=MUTED, font=("Microsoft YaHei", 9), anchor="w",
        )
        self.status.pack(fill="x")

        # ---- result --------------------------------------------------
        result_box = ttk.LabelFrame(
            body, text=i18n.tr("结果"), style="CY.TLabelframe", padding=0,
        )
        result_box.pack(fill="both", expand=True, pady=(12, 0))
        text_wrap = tk.Frame(result_box, bg=PAPER)
        text_wrap.pack(fill="both", expand=True, padx=12, pady=10)
        self.result = tk.Text(
            text_wrap, height=8, wrap="word", bg="white", fg=INK,
            relief="flat", highlightthickness=1, highlightbackground=LINE,
            selectbackground=ACCENT, selectforeground="white",
            font=("Consolas", 9),
        )
        self.result.pack(side="left", fill="both", expand=True)
        rscroll = ttk.Scrollbar(
            text_wrap, orient="vertical", style="CY.Vertical.TScrollbar",
            command=self.result.yview)
        rscroll.pack(side="right", fill="y")
        self.result.configure(yscrollcommand=rscroll.set, state="disabled")

    def _button(self, parent, text, command):
        return ttk.Button(
            parent, text=text, command=command, style="CY.TButton",
            cursor="hand2",
        )

    # ---- folder actions ----------------------------------------------
    def _add_folder(self) -> None:
        path = filedialog.askdirectory(
            parent=self.root, title=i18n.tr("选择要扫描的目录"), mustexist=True,
        )
        if not path:
            return
        resolved = Path(path).resolve()
        if resolved in self.roots:
            return
        self.roots.append(resolved)
        self.folder_list.insert("end", str(resolved))
        self.count_label.configure(
            text=i18n.tr("已添加，开始生成时会统计仓库数量")
        )

    def _remove_folder(self) -> None:
        selected = list(self.folder_list.curselection())
        for index in reversed(selected):
            self.folder_list.delete(index)
            del self.roots[index]

    def _clear_folders(self) -> None:
        self.folder_list.delete(0, "end")
        self.roots.clear()

    def _check_repos(self) -> None:
        if not self.roots:
            messagebox.showwarning(
                i18n.tr("没有目录"), i18n.tr("请先添加至少一个目录。"),
            )
            return
        try:
            depth = int(self.depth_var.get())
        except ValueError:
            depth = 6
        self.count_label.configure(text=i18n.tr("正在检查…"))
        threading.Thread(
            target=self._count_work, args=(list(self.roots), depth),
            daemon=True,
        ).start()

    def _count_work(self, roots, depth) -> None:
        try:
            self.queue.put(("checked", len(discover(roots, depth))))
        except Exception as exc:  # pragma: no cover - UI path
            self.queue.put(("error", str(exc)))

    def _choose_output(self) -> None:
        path = filedialog.askdirectory(
            parent=self.root, title=i18n.tr("选择输出目录"), mustexist=False,
        )
        if path:
            self.out_var.set(path)

    # ---- worker ------------------------------------------------------
    def _start(self) -> None:
        if self.busy:
            return
        if not self.roots:
            messagebox.showwarning(
                i18n.tr("没有目录"),
                i18n.tr("请先添加至少一个要扫描的目录。"),
            )
            return
        try:
            year = int(self.year_var.get())
            depth = int(self.depth_var.get())
            jobs = max(1, int(self.jobs_var.get()))
        except ValueError:
            messagebox.showwarning(
                i18n.tr("参数不对"),
                i18n.tr("年份、扫描层级和并行数必须是数字。"),
            )
            return
        out_dir = Path(self.out_var.get()).expanduser().resolve()
        identity = self.identity if self.identity_var.get() else None
        compare = self.compare_var.get()
        all_branches = self.all_branches_var.get()
        aliases = [item.strip() for item in self.alias_var.get().split(",")
                   if item.strip()]

        self._set_busy(True)
        self.written = []
        self.html_path = None
        self.progress.configure(value=0, maximum=1)
        self.status.configure(text=i18n.tr("正在查找 git 仓库…"))
        self._set_result("")
        threading.Thread(
            target=self._work,
            args=(list(self.roots), depth, year, out_dir, identity,
                  jobs, compare, aliases, all_branches),
            daemon=True,
        ).start()

    def _work(self, roots, depth, year, out_dir, identity, jobs, compare,
              aliases, all_branches) -> None:
        try:
            repos = discover(roots, depth)
            if not repos:
                raise RuntimeError(i18n.tr("没有找到 git 仓库。"))
            self.queue.put(("count", len(repos)))

            def progress(done, total, name):
                self.queue.put(("progress", done, total, name))

            stats, warnings = scan(
                repos, roots, year, identity, aliases=aliases,
                progress=progress, jobs=jobs, compare=compare,
                all_branches=all_branches,
            )
            if stats.commit_count == 0:
                raise RuntimeError(i18n.tr(
                    "{year} 年没有找到提交。", year=year,
                ))
            written = render(stats, out_dir)
            self.queue.put(("done", stats, written, warnings, out_dir))
        except Exception as exc:  # pragma: no cover - UI path
            self.queue.put(("error", str(exc)))

    def _poll(self) -> None:
        try:
            while True:
                event = self.queue.get_nowait()
                kind = event[0]
                if kind == "count":
                    count = event[1]
                    self.status.configure(text=i18n.tr(
                        "找到 {count} 个仓库，开始扫描…", count=count,
                    ))
                elif kind == "checked":
                    self.count_label.configure(text=i18n.tr(
                        "找到 {count} 个 git 仓库", count=event[1],
                    ))
                elif kind == "progress":
                    _, done, total, name = event
                    self.progress.configure(maximum=max(total, 1), value=done)
                    self.status.configure(text=f"{done}/{total} · {name}")
                elif kind == "done":
                    _, stats, written, warnings, out_dir = event
                    self._finish(stats, written, warnings, out_dir)
                elif kind == "error":
                    self._fail(event[1])
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _finish(self, stats, written, warnings, out_dir) -> None:
        self.written = written
        self.html_path = next(
            (path for label, path in written if label == "HTML"), None)
        lines = [
            i18n.tr(
                "仓库 {repos} · 提交 {commits} · 活跃 {days} 天 · 涉及 {files} 个文件",
                repos=stats.repo_count, commits=fmt_int(stats.commit_count),
                days=stats.active_days, files=stats.file_count,
            ),
            i18n.tr("输出目录：{path}", path=out_dir),
            "",
        ]
        lines += [f"{label:<9} {path.name}" for label, path in written]
        if warnings:
            lines += ["", i18n.tr("警告：")] + [f"- {item}" for item in warnings]
        self._set_result("\n".join(lines))
        self.status.configure(text=i18n.tr("完成。"))
        self.progress.configure(value=self.progress["maximum"])
        self._set_busy(False)
        self.open_btn.configure(
            state="normal" if self.html_path else "disabled")
        self.folder_btn.configure(state="normal")

    def _fail(self, message: str) -> None:
        self._set_busy(False)
        self.status.configure(text=i18n.tr(
            "失败：{message}", message=message,
        ))
        messagebox.showerror(i18n.tr("生成失败"), message)

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.start_btn.configure(state=state)

    def _check(self, parent, text, variable, enabled=True):
        frame = tk.Frame(parent, bg=PAPER,
                         cursor="hand2" if enabled else "")
        canvas = tk.Canvas(
            frame, width=16, height=16, bg=PAPER,
            highlightthickness=0, bd=0,
            cursor="hand2" if enabled else "",
        )
        canvas.pack(side="left", padx=(0, 8))
        label = tk.Label(
            frame, text=text, bg=PAPER,
            fg=INK if enabled else MUTED,
            font=("Microsoft YaHei", 9),
            cursor="hand2" if enabled else "",
        )
        label.pack(side="left")

        def draw() -> None:
            canvas.delete("all")
            if not enabled:
                canvas.create_rectangle(1, 1, 15, 15, outline=LINE, fill=PAPER2)
                return
            if variable.get():
                canvas.create_rectangle(1, 1, 15, 15, outline=ACCENT, fill=ACCENT)
                canvas.create_line(
                    4, 8, 7, 11, 12, 4, fill="white", width=2,
                    capstyle="round", joinstyle="round",
                )
            else:
                canvas.create_rectangle(1, 1, 15, 15, outline=LINE, fill="white")

        def toggle(_event=None) -> None:
            if not enabled or self.busy:
                return
            variable.set(not variable.get())
            draw()

        if enabled:
            canvas.bind("<Button-1>", toggle)
            label.bind("<Button-1>", toggle)
        draw()
        return frame, draw

    def _set_result(self, text: str) -> None:
        self.result.configure(state="normal")
        self.result.delete("1.0", "end")
        self.result.insert("1.0", text)
        self.result.configure(state="disabled")

    def _open_report(self) -> None:
        if self.html_path:
            self._open_path(self.html_path)

    def _open_output(self) -> None:
        if not self.written:
            return
        out_dir = self.written[0][1].parent
        self._open_path(out_dir)

    def _open_path(self, path: Path) -> None:
        try:
            if hasattr(os, "startfile"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            else:
                webbrowser.open(path.as_uri())
        except Exception as exc:  # pragma: no cover - platform dependent
            messagebox.showerror(i18n.tr("无法打开"), str(exc))


def _enable_dpi() -> None:
    with contextlib.suppress(Exception):
        ctypes.windll.shcore.SetProcessDpiAwareness(1)


def run() -> int:
    i18n.set_lang(i18n.detect(sys.argv[1:]))
    _enable_dpi()
    try:
        root = tk.Tk()
    except tk.TclError as exc:
        print(i18n.tr("无法启动图形界面: {exc}", exc=exc), file=sys.stderr)
        print(i18n.tr("请改用 codeyear tui 或 codeyear scan。"),
              file=sys.stderr)
        return 1
    App(root)
    root.mainloop()
    return 0


def main() -> None:
    raise SystemExit(run())
