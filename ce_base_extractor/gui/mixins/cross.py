from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *
from ce_base_extractor.gui.theme import FONTS, THEME, make_tool_group


class CrossMixin:
    def _build_cross_tab(self) -> None:
        ttk.Label(
            self._tab_cross,
            text="添加 2～3 个 Rescan 后的扫描文件，取交集得到最稳定基址",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(0, 10))

        btns = ttk.Frame(self._tab_cross)
        btns.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(btns, text="添加文件", style="Primary.TButton", command=self._add_cross_file).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btns, text="交叉验证", style="Accent.TButton", command=self._run_cross_extract).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(btns, text="对比文件", command=self._diff_sqlite).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(btns, text="清空列表", command=self._clear_cross_files).pack(side=tk.LEFT)

        stat_card = tk.Frame(
            self._tab_cross,
            bg=THEME["accent_light"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
        )
        stat_card.pack(fill=tk.X, pady=(0, 10))
        self.cross_stability_var = tk.StringVar(value="稳定率: —")
        tk.Label(
            stat_card,
            textvariable=self.cross_stability_var,
            font=FONTS["body_bold"],
            fg=THEME["accent"],
            bg=THEME["accent_light"],
            padx=14,
            pady=10,
        ).pack(anchor=tk.W)

        list_grp = make_tool_group(self._tab_cross, "已添加文件")
        list_grp.pack(fill=tk.BOTH, expand=True)

        list_wrap = ttk.Frame(list_grp)
        list_wrap.pack(fill=tk.BOTH, expand=True)
        self.cross_list = tk.Listbox(
            list_wrap,
            height=12,
            font=("Cascadia Mono", 9),
            bg=THEME["surface_alt"],
            fg=THEME["text"],
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=THEME["border"],
            selectbackground=THEME["accent_light"],
            selectforeground=THEME["text"],
        )
        self.cross_list.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb = ttk.Scrollbar(list_wrap, command=self.cross_list.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.cross_list.configure(yscrollcommand=sb.set)

    def _add_cross_file(self) -> None:
        paths = filedialog.askopenfilenames(
            filetypes=[
                ("CE SQLite/PTR", "*.sqlite *.db *.sqlite3 *.PTR *.ptr"),
                ("CE SQLite", "*.sqlite *.db"),
                ("CE Pointer", "*.PTR *.ptr"),
            ]
        )
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
            messagebox.showwarning("提示", "交叉验证至少需要 2 个文件")
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
        win.geometry("360x100")
        win.transient(self)
        win.configure(bg=THEME["bg"])
        ttk.Label(win, text="正在交叉验证，大文件可能较慢…").pack(pady=(16, 6))
        bar = ttk.Progressbar(win, mode="indeterminate")
        bar.pack(fill=tk.X, padx=20, pady=4)
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
                    title="选择扫描文件（可多选）",
                    filetypes=[("CE SQLite/PTR", "*.sqlite *.db *.PTR *.ptr")],
                )
                if len(picked) < 2:
                    return
                files = [Path(p) for p in picked]

            diff = diff_sqlite_many(files, ptrid=ptrid) if len(files) > 2 else diff_sqlite_files(
                files[0], files[1], ptrid=ptrid
            )
            ratio = diff.get("stability_ratio", 0)
            self.cross_stability_var.set(f"稳定率: {float(ratio) * 100:.1f}%")

            if len(files) == 2:
                counts = diff.get("counts_per_file", [0, 0])
                msg = (
                    f"文件数: 2\n"
                    f"各文件: {counts}\n"
                    f"并集: {diff.get('union', 0)} 条\n"
                    f"全部出现: {diff.get('in_all', 0)} 条\n"
                    f"稳定率: {float(ratio) * 100:.1f}%"
                )
            else:
                msg = (
                    f"文件数: {diff['file_count']}\n"
                    f"各文件: {diff['counts_per_file']}\n"
                    f"并集: {diff['union']} 条\n"
                    f"全部出现: {diff['in_all']} 条\n"
                    f"稳定率: {float(ratio) * 100:.1f}%\n"
                    f"出现次数分布: {diff['occurrence_histogram']}"
                )
            messagebox.showinfo("文件对比", msg)
        except Exception as exc:
            messagebox.showerror("对比失败", str(exc))
