from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *
from ce_base_extractor.gui.theme import FONTS, THEME
from ce_base_extractor.gui.wizard import show_first_run_wizard


class ShellMixin:
    def _watch_dir(self) -> Path:
        raw = ""
        if hasattr(self, "watch_dir_var"):
            raw = self.watch_dir_var.get().strip()
        elif getattr(self, "_config", None) and getattr(self._config, "watch_dir", ""):
            raw = str(self._config.watch_dir).strip()
        return Path(raw) if raw else WATCH_DIR

    def _build_ui(self) -> None:
        self._build_menubar()

        # ── 顶栏 ──
        header = ttk.Frame(self, style="Header.TFrame", padding=(20, 14))
        header.pack(fill=tk.X)
        header_inner = ttk.Frame(header, style="Header.TFrame")
        header_inner.pack(fill=tk.X)

        title_col = ttk.Frame(header_inner, style="Header.TFrame")
        title_col.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(title_col, text="CE 基址提取器", style="Title.TLabel").pack(anchor=tk.W)
        ttk.Label(
            title_col,
            text="指针扫描 → 稳定基址 → 脚本导出 · 雷电 / 逍遥 / 蓝叠",
            style="Subtitle.TLabel",
        ).pack(anchor=tk.W, pady=(2, 0))

        tk.Frame(header, bg=THEME["border"], height=1).pack(fill=tk.X, side=tk.BOTTOM)

        # ── 主内容 ──
        body = ttk.Frame(self, padding=(16, 12))
        body.pack(fill=tk.BOTH, expand=True)

        self.notebook = ttk.Notebook(body)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self._tab_extract = ttk.Frame(self.notebook, padding=(4, 8))
        self._tab_cross = ttk.Frame(self.notebook, padding=(4, 8))
        self._tab_signature = ttk.Frame(self.notebook, padding=(4, 8))
        self._tab_modules = ttk.Frame(self.notebook, padding=(4, 8))
        self._tab_monitor = ttk.Frame(self.notebook, padding=(4, 8))
        self._tab_profile = ttk.Frame(self.notebook, padding=(4, 8))
        self._tab_history = ttk.Frame(self.notebook, padding=(4, 8))

        self.notebook.add(self._tab_extract, text="  提取  ")
        self.notebook.add(self._tab_cross, text="  交叉验证  ")
        self.notebook.add(self._tab_signature, text="  特征码  ")
        self.notebook.add(self._tab_modules, text="  模块  ")
        self.notebook.add(self._tab_monitor, text="  监控  ")
        self.notebook.add(self._tab_profile, text="  游戏 Profile  ")
        self.notebook.add(self._tab_history, text="  收藏  ")

        self._build_extract_tab()
        self._build_cross_tab()
        self._build_signature_tab()
        self._build_modules_tab()
        self._build_monitor_tab()
        self._build_profile_tab()
        self._build_history_tab()

        self._build_footer()

    def _build_menubar(self) -> None:
        menubar = tk.Menu(self)
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="流程说明…", command=self._show_wizard_again)
        help_menu.add_command(label="各页签说明…", command=self._show_tab_map)
        menubar.add_cascade(label="帮助", menu=help_menu)
        self.config(menu=menubar)

    def _show_wizard_again(self) -> None:
        show_first_run_wizard(self, watch_dir=self._watch_dir())

    def _show_tab_map(self) -> None:
        messagebox.showinfo(
            "各页签说明",
            "提取 — 选文件、提取基址、导出与重启验证\n"
            "交叉验证 — 多份 Rescan 取交集（与底栏「监视+增量交叉」互补）\n"
            "特征码 — 多样本 AOB 生成 / 扫描 / 写入游戏 Profile\n"
            "模块 — 白名单与统计\n"
            "监控 — 实时读链\n"
            "游戏 Profile — 按游戏保存链与快照（不等于底栏默认参数）\n"
            "收藏 — 历史收藏导出\n\n"
            "底栏「保存默认参数」写入 user_config.json（全局提取默认值）。",
        )

    def _build_footer(self) -> None:
        toolbar = ttk.Frame(self, padding=(16, 8))
        toolbar.pack(fill=tk.X)

        left = ttk.Frame(toolbar)
        left.pack(side=tk.LEFT)
        ttk.Button(left, text="复制全部", command=self._copy_all).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(left, text="TXT", command=lambda: self._export("txt")).pack(side=tk.LEFT, padx=2)
        ttk.Button(left, text="JSON", command=lambda: self._export("json")).pack(side=tk.LEFT, padx=2)
        ttk.Button(left, text="保存默认参数", command=self._save_user_config).pack(
            side=tk.LEFT, padx=(12, 0)
        )

        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=12)

        initial_watch = getattr(self._config, "watch_dir", "") or str(WATCH_DIR)
        self.watch_dir_var = tk.StringVar(value=initial_watch)
        self.watch_var = tk.BooleanVar(value=False)
        self.watch_incremental_var = tk.BooleanVar(value=True)
        self.watch_check = ttk.Checkbutton(
            toolbar,
            text="监视目录",
            variable=self.watch_var,
            command=self._toggle_watch,
        )
        self.watch_check.pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(toolbar, text="增量交叉", variable=self.watch_incremental_var).pack(
            side=tk.LEFT
        )
        ttk.Entry(toolbar, textvariable=self.watch_dir_var, width=28).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Button(toolbar, text="…", width=3, command=self._browse_watch_dir).pack(side=tk.LEFT)

        status_bar = tk.Frame(self, bg=THEME["status_bg"], height=30)
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)
        status_bar.pack_propagate(False)

        self.status_var = tk.StringVar(value="就绪")
        tk.Label(
            status_bar,
            textvariable=self.status_var,
            bg=THEME["status_bg"],
            fg=THEME["status_fg"],
            font=FONTS["small"],
            anchor=tk.W,
            padx=16,
        ).pack(side=tk.LEFT, fill=tk.Y)

    def _browse_watch_dir(self) -> None:
        path = filedialog.askdirectory(initialdir=str(self._watch_dir()))
        if path:
            self.watch_dir_var.set(path)
            if self.watch_var.get():
                self.watch_var.set(False)
                self._toggle_watch()
                self.watch_var.set(True)
                self._toggle_watch()

    def _save_user_config(self) -> None:
        cfg = self._current_config()
        path = save_config(cfg)
        self.status_var.set(f"默认参数已保存: {path}")

    def _toggle_watch(self) -> None:
        if self.watch_var.get():
            watch = self._watch_dir()
            watch.mkdir(parents=True, exist_ok=True)
            cfg = self._current_config()
            if self.watch_incremental_var.get():
                self._incremental_cross = IncrementalCrossValidator(
                    min_occurrences=max(cfg.cross_validate_min, 2),
                    ptrid=cfg.ptrid,
                    fuzzy=cfg.cross_validate_fuzzy,
                )

            def on_new(path: Path) -> None:
                self.after(0, lambda: self._on_watch_file(path))

            def on_error(path: Path, exc: Exception) -> None:
                self.after(
                    0,
                    lambda: messagebox.showerror(
                        "监视失败", f"{path.name}\n{exc}"
                    ),
                )

            self._watcher = FolderWatcher(watch, on_new, on_error=on_error)
            self._watcher.start()
            self.status_var.set(f"正在监视: {watch}")
        else:
            if self._watcher:
                self._watcher.stop()
                self._watcher = None
            self._incremental_cross = None
            self.status_var.set("已停止监视")

    def _on_watch_file(self, path: Path) -> None:
        self._set_file(path)
        try:
            cfg = self._current_config()
            if self.watch_incremental_var.get() and self._incremental_cross:
                info = self._incremental_cross.add_file(path)
                stable = self._incremental_cross.stable_chains()
                if stable:
                    from ce_base_extractor.filters.scorer import filter_and_rank

                    ranked = filter_and_rank(stable, cfg)
                    result = ExtractResult(
                        chains=ranked,
                        total_raw=len(stable),
                        total_after_filter=len(ranked),
                        modules_seen=sorted({c.module_name for c in stable}),
                        source_file=str(path),
                        cross_validate_meta=self._incremental_cross.meta(),
                    )
                    self._populate_result(result)
                self.status_var.set(
                    f"增量交叉 +{info['new_unique_keys']} 键, 稳定 {info['stable_keys']} 条"
                )
            else:
                result = extract(path, config=cfg)
                self._populate_result(result)
                self.status_var.set(f"自动提取: {path.name}")
        except Exception as exc:
            messagebox.showerror("自动提取失败", f"{path.name}\n{exc}")
            self.status_var.set(f"自动提取失败: {exc}")

    def destroy(self) -> None:
        self._stop_monitor()
        if self._watcher:
            self._watcher.stop()
        super().destroy()
