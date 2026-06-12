from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.export.formatter import format_ce_table, to_json, to_text
from ce_base_extractor.models import ExtractConfig
from ce_base_extractor.pipeline import extract, load_config

try:
    import windnd

    _HAS_WINDND = True
except ImportError:
    _HAS_WINDND = False


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CE 基址提取器（模拟器优化）")
        self.geometry("920x640")
        self.minsize(760, 520)

        self._config = load_config()
        self._current_file: Path | None = None
        self._result_text = ""

        self._build_ui()
        if _HAS_WINDND:
            windnd.hook_dropfiles(self, func=self._on_drop)

    def _build_ui(self) -> None:
        top = ttk.Frame(self, padding=12)
        top.pack(fill=tk.X)

        ttk.Label(top, text="CE 指针扫描 SQLite / PTR → 一键提取稳定基址", font=("Segoe UI", 11, "bold")).pack(
            anchor=tk.W
        )
        ttk.Label(
            top,
            text="模拟器场景优先 libil2cpp.so / libunity.so 等 Android 游戏模块",
            foreground="#555",
        ).pack(anchor=tk.W, pady=(4, 8))

        btn_row = ttk.Frame(top)
        btn_row.pack(fill=tk.X)
        ttk.Button(btn_row, text="选择文件", command=self._browse).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="提取基址", command=self._run_extract).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="复制全部", command=self._copy_all).pack(side=tk.LEFT)
        ttk.Button(btn_row, text="导出 TXT", command=lambda: self._export("txt")).pack(side=tk.LEFT, padx=8)
        ttk.Button(btn_row, text="导出 JSON", command=lambda: self._export("json")).pack(side=tk.LEFT)

        self.file_var = tk.StringVar(value="未选择文件（可拖放 .sqlite / .db / .PTR）")
        ttk.Label(top, textvariable=self.file_var, foreground="#333").pack(anchor=tk.W, pady=(8, 0))

        opt = ttk.LabelFrame(self, text="过滤参数", padding=10)
        opt.pack(fill=tk.X, padx=12, pady=8)

        self.top_n_var = tk.IntVar(value=self._config.top_n)
        self.max_depth_var = tk.IntVar(value=self._config.max_depth)
        self.max_offset_var = tk.IntVar(value=self._config.max_single_offset)
        self.emulator_var = tk.BooleanVar(value=self._config.emulator_mode)

        ttk.Label(opt, text="输出条数").grid(row=0, column=0, sticky=tk.W)
        ttk.Spinbox(opt, from_=1, to=200, textvariable=self.top_n_var, width=8).grid(row=0, column=1, padx=6)
        ttk.Label(opt, text="最大层级").grid(row=0, column=2, sticky=tk.W, padx=(16, 0))
        ttk.Spinbox(opt, from_=1, to=10, textvariable=self.max_depth_var, width=8).grid(row=0, column=3, padx=6)
        ttk.Label(opt, text="单级偏移上限(hex)").grid(row=0, column=4, sticky=tk.W, padx=(16, 0))
        ttk.Entry(opt, textvariable=self.max_offset_var, width=10).grid(row=0, column=5, padx=6)
        ttk.Checkbutton(opt, text="模拟器模式", variable=self.emulator_var).grid(row=0, column=6, padx=(16, 0))

        paned = ttk.Panedwindow(self, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        list_frame = ttk.LabelFrame(paned, text="结果列表（双击复制 CE 表达式）", padding=6)
        text_frame = ttk.LabelFrame(paned, text="详情", padding=6)
        paned.add(list_frame, weight=2)
        paned.add(text_frame, weight=3)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("score", "module", "base", "depth"),
            show="headings",
            height=8,
        )
        for col, title, width in (
            ("score", "评分", 70),
            ("module", "模块", 260),
            ("base", "基址偏移", 140),
            ("depth", "层级", 60),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.bind("<Double-1>", self._copy_selected_ce)

        self.detail = tk.Text(text_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.detail.pack(fill=tk.BOTH, expand=True)

        self.status_var = tk.StringVar(value="就绪")
        ttk.Label(self, textvariable=self.status_var, padding=(12, 0)).pack(anchor=tk.W)

    def _current_config(self) -> ExtractConfig:
        return ExtractConfig(
            top_n=int(self.top_n_var.get()),
            max_depth=int(self.max_depth_var.get()),
            max_single_offset=int(self.max_offset_var.get()),
            emulator_mode=bool(self.emulator_var.get()),
            dedupe=True,
        )

    def _on_drop(self, files: list[bytes]) -> None:
        if not files:
            return
        path = Path(files[0].decode("gbk", errors="ignore"))
        self._set_file(path)

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="选择 CE 导出文件",
            filetypes=[
                ("CE SQLite", "*.sqlite *.db *.sqlite3"),
                ("CE Pointer", "*.PTR *.ptr"),
                ("所有文件", "*.*"),
            ],
        )
        if path:
            self._set_file(Path(path))

    def _set_file(self, path: Path) -> None:
        self._current_file = path
        self.file_var.set(str(path))
        self.status_var.set(f"已选择: {path.name}")

    def _run_extract(self) -> None:
        if not self._current_file:
            messagebox.showwarning("提示", "请先选择或拖入 CE 导出文件")
            return
        try:
            result = extract(self._current_file, config=self._current_config())
        except Exception as exc:
            messagebox.showerror("提取失败", str(exc))
            self.status_var.set(f"失败: {exc}")
            return

        self._result_text = to_text(result)
        self.detail.delete("1.0", tk.END)
        self.detail.insert(tk.END, self._result_text)

        for item in self.tree.get_children():
            self.tree.delete(item)
        for chain in result.chains:
            self.tree.insert(
                "",
                tk.END,
                values=(
                    f"{chain.score:.1f}",
                    chain.module_name,
                    f"0x{chain.module_offset:X}",
                    chain.depth,
                ),
                tags=(format_ce_table(chain),),
            )

        self.status_var.set(
            f"完成：原始 {result.total_raw} 条，输出 {len(result.chains)} 条"
        )

    def _copy_selected_ce(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0], "tags")
        if tags:
            self.clipboard_clear()
            self.clipboard_append(tags[0])
            self.status_var.set("已复制 CE 表达式到剪贴板")

    def _copy_all(self) -> None:
        if not self._result_text:
            messagebox.showinfo("提示", "暂无结果可复制")
            return
        self.clipboard_clear()
        self.clipboard_append(self._result_text)
        self.status_var.set("已复制全部结果")

    def _export(self, fmt: str) -> None:
        if not self._current_file:
            messagebox.showwarning("提示", "请先提取结果")
            return
        ext = "json" if fmt == "json" else "txt"
        default_name = self._current_file.with_suffix(f".bases.{ext}").name
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}",
            initialfile=default_name,
            filetypes=[(ext.upper(), f"*.{ext}")],
        )
        if not path:
            return
        try:
            result = extract(self._current_file, config=self._current_config())
            content = to_json(result) if fmt == "json" else to_text(result)
            Path(path).write_text(content, encoding="utf-8")
            self.status_var.set(f"已导出: {path}")
        except Exception as exc:
            messagebox.showerror("导出失败", str(exc))


def run_gui() -> None:
    app = App()
    app.mainloop()
