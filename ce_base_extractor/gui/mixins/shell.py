from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ce_base_extractor.gui.app_imports import *


class ShellMixin:
    def _build_ui(self) -> None:
        header = ttk.Frame(self, padding=(12, 8))
        header.pack(fill=tk.X)
        ttk.Label(
            header,
            text="CE 指针扫描 → 稳定基址 → Python 内存读取脚本",
            font=("Segoe UI", 12, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            header,
            text="默认雷电模拟器 · 支持多轮 Rescan 交叉验证 · 一键生成 Python 读取脚本",
            foreground="#555",
        ).pack(anchor=tk.W)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=12, pady=4)

        self._tab_extract = ttk.Frame(self.notebook, padding=8)
        self._tab_cross = ttk.Frame(self.notebook, padding=8)
        self._tab_modules = ttk.Frame(self.notebook, padding=8)
        self._tab_history = ttk.Frame(self.notebook, padding=8)
        self._tab_monitor = ttk.Frame(self.notebook, padding=8)
        self._tab_profile = ttk.Frame(self.notebook, padding=8)
        self.notebook.add(self._tab_extract, text="单文件提取")
        self.notebook.add(self._tab_cross, text="交叉验证")
        self.notebook.add(self._tab_modules, text="模块过滤")
        self.notebook.add(self._tab_monitor, text="实时监控")
        self.notebook.add(self._tab_profile, text="游戏配置")
        self.notebook.add(self._tab_history, text="收藏历史")

        self._build_extract_tab()
        self._build_cross_tab()
        self._build_modules_tab()
        self._build_monitor_tab()
        self._build_profile_tab()
        self._build_history_tab()
        self._build_footer()

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, padding=(12, 6))
        footer.pack(fill=tk.X)
        ttk.Button(footer, text="复制全部", command=self._copy_all).pack(side=tk.LEFT)
        ttk.Button(footer, text="导出 TXT", command=lambda: self._export("txt")).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(footer, text="导出 JSON", command=lambda: self._export("json")).pack(
            side=tk.LEFT
        )
        ttk.Button(footer, text="保存配置", command=self._save_user_config).pack(
            side=tk.LEFT, padx=12
        )

        self.watch_var = tk.BooleanVar(value=False)
        self.watch_incremental_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            footer,
            text=f"监视导出目录 ({WATCH_DIR.name})",
            variable=self.watch_var,
            command=self._toggle_watch,
        ).pack(side=tk.LEFT, padx=8)
        ttk.Checkbutton(
            footer,
            text="增量交叉",
            variable=self.watch_incremental_var,
        ).pack(side=tk.LEFT)

        self.status_var = tk.StringVar(value="就绪 · 默认雷电模拟器")
        ttk.Label(footer, textvariable=self.status_var).pack(side=tk.RIGHT)

    def _save_user_config(self) -> None:
        cfg = self._current_config()
        path = save_config(cfg)
        self.status_var.set(f"配置已保存: {path}")

    def _toggle_watch(self) -> None:
        if self.watch_var.get():
            WATCH_DIR.mkdir(parents=True, exist_ok=True)
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
                self.after(0, lambda: self.status_var.set(f"监视失败 {path.name}: {exc}"))

            self._watcher = FolderWatcher(WATCH_DIR, on_new, on_error=on_error)
            self._watcher.start()
            self.status_var.set(f"正在监视: {WATCH_DIR}")
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
            self.status_var.set(f"自动提取失败: {exc}")

    def destroy(self) -> None:
        self._stop_monitor()
        if self._watcher:
            self._watcher.stop()
        super().destroy()
