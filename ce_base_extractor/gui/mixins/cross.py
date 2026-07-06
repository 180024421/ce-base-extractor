from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *


class CrossMixin:
    def _build_cross_tab(self) -> None:
        ttk.Label(
            self._tab_cross,
            text="添加 2～3 个 Rescan 后的 SQLite，取交集得到最稳定基址",
        ).pack(anchor=tk.W)
        btns = ttk.Frame(self._tab_cross)
        btns.pack(fill=tk.X, pady=6)
        ttk.Button(btns, text="添加文件", command=self._add_cross_file).pack(side=tk.LEFT)
        ttk.Button(btns, text="清空", command=self._clear_cross_files).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="交叉验证提取", command=self._run_cross_extract).pack(side=tk.LEFT)
        ttk.Button(btns, text="对比 SQLite", command=self._diff_sqlite).pack(side=tk.LEFT, padx=6)

        self.cross_stability_var = tk.StringVar(value="稳定率: —")
        ttk.Label(
            self._tab_cross, textvariable=self.cross_stability_var, foreground="#0066cc"
        ).pack(anchor=tk.W, pady=(0, 4))

        self.cross_list = tk.Listbox(self._tab_cross, height=8)
        self.cross_list.pack(fill=tk.BOTH, expand=True, pady=4)

    def _add_cross_file(self) -> None:
        paths = filedialog.askopenfilenames(filetypes=[("CE SQLite", "*.sqlite *.db")])
        for p in paths:
            path = Path(p)
            self._extra_files.append(path)
            self.cross_list.insert(tk.END, str(path))
        if paths and not self._current_file:
            self._set_file(Path(paths[0]))

    def _clear_cross_files(self) -> None:
        self._extra_files.clear()
        self.cross_list.delete(0, tk.END)

    def _run_cross_extract(self) -> None:
        if len(self._extra_files) < 2:
            messagebox.showwarning("提示", "交叉验证至少需要 2 个 SQLite 文件")
            return

        primary = self._extra_files[0]
        extras = self._extra_files[1:]

        def fn():
            return extract(primary, config=self._current_config(), extra_files=extras)

        def done(result: ExtractResult) -> None:
            self._populate_result(result)
            self.notebook.select(self._tab_extract)

        self._extract_busy = True
        self.status_var.set("正在交叉验证…")
        win = tk.Toplevel(self)
        win.title("交叉验证")
        win.geometry("320x80")
        win.transient(self)
        ttk.Label(win, text="正在交叉验证，大文件可能较慢…").pack(pady=(12, 4))
        bar = ttk.Progressbar(win, mode="indeterminate")
        bar.pack(fill=tk.X, padx=16, pady=4)
        bar.start(10)

        def work() -> None:
            try:
                result = fn()
                self.after(
                    0, lambda: (win.destroy(), setattr(self, "_extract_busy", False), done(result))
                )
            except Exception as exc:
                self.after(
                    0,
                    lambda e=exc: (
                        win.destroy(),
                        setattr(self, "_extract_busy", False),
                        messagebox.showerror("交叉验证失败", str(e)),
                    ),
                )

        threading.Thread(target=work, daemon=True).start()

    def _diff_sqlite(self) -> None:
        ptrid = self._parse_ptrid()
        try:
            if len(self._extra_files) >= 2:
                files = self._extra_files
            else:
                picked = filedialog.askopenfilenames(
                    title="选择 SQLite（可多选）",
                    filetypes=[("SQLite", "*.sqlite *.db")],
                )
                if len(picked) < 2:
                    return
                files = [Path(p) for p in picked]

            if len(files) == 2:
                diff = diff_sqlite_files(files[0], files[1], ptrid=ptrid)
                msg = (
                    f"A: {diff['count_a']} 条\nB: {diff['count_b']} 条\n"
                    f"共同: {diff['common']} 条\n仅A: {diff['only_a']} 仅B: {diff['only_b']}\n"
                    f"稳定率: {diff['stability_ratio'] * 100:.1f}%"
                )
            else:
                diff = diff_sqlite_many(files, ptrid=ptrid)
                msg = (
                    f"文件数: {diff['file_count']}\n"
                    f"各文件: {diff['counts_per_file']}\n"
                    f"并集: {diff['union']} 条\n"
                    f"全部出现: {diff['in_all']} 条\n"
                    f"稳定率: {diff['stability_ratio'] * 100:.1f}%\n"
                    f"出现次数分布: {diff['occurrence_histogram']}"
                )
                self.cross_stability_var.set(f"稳定率: {diff['stability_ratio'] * 100:.1f}%")
            messagebox.showinfo("SQLite 对比", msg)
        except Exception as exc:
            messagebox.showerror("对比失败", str(exc))
