from __future__ import annotations

import tkinter as tk
from dataclasses import asdict
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import format_ce_table, to_json, to_text
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.filters.presets import PRESETS
from ce_base_extractor.history.store import HistoryStore
from ce_base_extractor.models import ExtractConfig, ExtractResult
from ce_base_extractor.parsers.sqlite_parser import list_ptrids
from ce_base_extractor.pipeline import extract, load_config, save_config
from ce_base_extractor.watch.folder_watcher import FolderWatcher

try:
    import windnd

    _HAS_WINDND = True
except ImportError:
    _HAS_WINDND = False

WATCH_DIR = Path.home() / "Documents" / "ce-exports"


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("CE 基址提取器 · 雷电模拟器")
        self.geometry("1080x720")
        self.minsize(900, 600)

        self._config = load_config()
        self._current_file: Path | None = None
        self._extra_files: list[Path] = []
        self._result: ExtractResult | None = None
        self._result_text = ""
        self._history = HistoryStore()
        self._watcher: FolderWatcher | None = None
        self._module_vars: dict[str, tk.BooleanVar] = {}

        self._build_ui()
        if _HAS_WINDND:
            windnd.hook_dropfiles(self, func=self._on_drop)

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
        self.notebook.add(self._tab_extract, text="单文件提取")
        self.notebook.add(self._tab_cross, text="交叉验证")
        self.notebook.add(self._tab_modules, text="模块过滤")
        self.notebook.add(self._tab_history, text="收藏历史")

        self._build_extract_tab()
        self._build_cross_tab()
        self._build_modules_tab()
        self._build_history_tab()
        self._build_footer()

    def _build_extract_tab(self) -> None:
        row = ttk.Frame(self._tab_extract)
        row.pack(fill=tk.X)
        ttk.Button(row, text="选择 SQLite/PTR", command=self._browse).pack(side=tk.LEFT)
        ttk.Button(row, text="提取基址", command=self._run_extract).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="导出 Python 脚本", command=self._export_python).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="导出 .CT", command=self._export_ct).pack(side=tk.LEFT)
        ttk.Button(row, text="测试读取", command=self._test_read).pack(side=tk.LEFT, padx=6)

        self.file_var = tk.StringVar(value="拖放或选择 CE 导出文件")
        ttk.Label(self._tab_extract, textvariable=self.file_var).pack(anchor=tk.W, pady=6)

        opts = ttk.LabelFrame(self._tab_extract, text="参数", padding=8)
        opts.pack(fill=tk.X, pady=4)

        self.preset_var = tk.StringVar(value=self._config.preset)
        self.top_n_var = tk.IntVar(value=self._config.top_n)
        self.max_depth_var = tk.IntVar(value=self._config.max_depth)
        self.max_offset_var = tk.IntVar(value=self._config.max_single_offset)
        self.emulator_var = tk.BooleanVar(value=self._config.emulator_mode)
        self.game_name_var = tk.StringVar(value=self._config.game_name)
        self.ptrid_var = tk.StringVar(value="")
        self.end_offset_var = tk.StringVar(value="")

        ttk.Label(opts, text="模拟器").grid(row=0, column=0, sticky=tk.W)
        ttk.Combobox(
            opts,
            textvariable=self.preset_var,
            values=[p.id for p in PRESETS.values()],
            state="readonly",
            width=12,
        ).grid(row=0, column=1, padx=4)
        ttk.Label(opts, text="游戏名").grid(row=0, column=2, sticky=tk.W, padx=(12, 0))
        ttk.Entry(opts, textvariable=self.game_name_var, width=14).grid(row=0, column=3, padx=4)
        ttk.Label(opts, text="ptrid").grid(row=0, column=4, sticky=tk.W, padx=(12, 0))
        ttk.Entry(opts, textvariable=self.ptrid_var, width=8).grid(row=0, column=5, padx=4)

        ttk.Label(opts, text="输出条数").grid(row=1, column=0, sticky=tk.W, pady=(6, 0))
        ttk.Spinbox(opts, from_=1, to=200, textvariable=self.top_n_var, width=8).grid(
            row=1, column=1, padx=4, pady=(6, 0)
        )
        ttk.Label(opts, text="最大层级").grid(row=1, column=2, sticky=tk.W, padx=(12, 0), pady=(6, 0))
        ttk.Spinbox(opts, from_=1, to=10, textvariable=self.max_depth_var, width=8).grid(
            row=1, column=3, padx=4, pady=(6, 0)
        )
        ttk.Label(opts, text="末级偏移(hex)").grid(row=1, column=4, sticky=tk.W, padx=(12, 0), pady=(6, 0))
        ttk.Entry(opts, textvariable=self.end_offset_var, width=10).grid(
            row=1, column=5, padx=4, pady=(6, 0)
        )
        ttk.Checkbutton(opts, text="模拟器模式", variable=self.emulator_var).grid(
            row=1, column=6, padx=(12, 0), pady=(6, 0)
        )

        paned = ttk.Panedwindow(self._tab_extract, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=6)

        list_frame = ttk.LabelFrame(paned, text="结果（双击复制 CE 表达式）", padding=4)
        detail_frame = ttk.LabelFrame(paned, text="详情", padding=4)
        paned.add(list_frame, weight=2)
        paned.add(detail_frame, weight=3)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("score", "module", "base", "depth", "source"),
            show="headings",
        )
        for col, title, w in (
            ("score", "评分", 60),
            ("module", "模块", 220),
            ("base", "基址", 120),
            ("depth", "层级", 50),
            ("source", "来源", 100),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb = ttk.Scrollbar(list_frame, command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", self._copy_selected_ce)

        self.detail = tk.Text(detail_frame, wrap=tk.WORD, font=("Consolas", 10))
        self.detail.pack(fill=tk.BOTH, expand=True)

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

        self.cross_list = tk.Listbox(self._tab_cross, height=8)
        self.cross_list.pack(fill=tk.BOTH, expand=True, pady=4)

    def _build_modules_tab(self) -> None:
        ttk.Label(
            self._tab_modules,
            text="勾选模块作为白名单（不勾选=不过滤）。提取后自动刷新模块统计。",
        ).pack(anchor=tk.W)
        mf = ttk.Frame(self._tab_modules)
        mf.pack(fill=tk.BOTH, expand=True, pady=6)

        self.module_canvas = tk.Canvas(mf, highlightthickness=0)
        self.module_inner = ttk.Frame(self.module_canvas)
        mscroll = ttk.Scrollbar(mf, orient=tk.VERTICAL, command=self.module_canvas.yview)
        self.module_canvas.configure(yscrollcommand=mscroll.set)
        mscroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.module_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self._module_window = self.module_canvas.create_window((0, 0), window=self.module_inner, anchor=tk.NW)
        self.module_inner.bind("<Configure>", self._on_module_frame_configure)
        self.module_canvas.bind("<Configure>", self._on_module_canvas_configure)

        sf = ttk.LabelFrame(self._tab_modules, text="模块统计", padding=4)
        sf.pack(fill=tk.BOTH, expand=True)
        self.stats_tree = ttk.Treeview(
            sf,
            columns=("module", "count", "tier", "avg_depth"),
            show="headings",
            height=6,
        )
        for col, title, w in (
            ("module", "模块", 240),
            ("count", "数量", 80),
            ("tier", "优先级", 80),
            ("avg_depth", "均层级", 80),
        ):
            self.stats_tree.heading(col, text=title)
            self.stats_tree.column(col, width=w, anchor=tk.W)
        self.stats_tree.pack(fill=tk.BOTH, expand=True)

    def _build_history_tab(self) -> None:
        row = ttk.Frame(self._tab_history)
        row.pack(fill=tk.X)
        ttk.Button(row, text="保存当前结果到收藏", command=self._save_favorites).pack(side=tk.LEFT)
        ttk.Button(row, text="刷新", command=self._refresh_history).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="导出收藏为 Python", command=self._export_history_python).pack(side=tk.LEFT)

        self.history_game_var = tk.StringVar()
        ttk.Label(self._tab_history, text="游戏").pack(anchor=tk.W, pady=(8, 0))
        self.history_combo = ttk.Combobox(
            self._tab_history, textvariable=self.history_game_var, state="readonly"
        )
        self.history_combo.pack(fill=tk.X)
        self.history_combo.bind("<<ComboboxSelected>>", lambda _e: self._show_history_game())

        self.history_text = tk.Text(self._tab_history, height=16, font=("Consolas", 10))
        self.history_text.pack(fill=tk.BOTH, expand=True, pady=6)
        self._refresh_history()

    def _build_footer(self) -> None:
        footer = ttk.Frame(self, padding=(12, 6))
        footer.pack(fill=tk.X)
        ttk.Button(footer, text="复制全部", command=self._copy_all).pack(side=tk.LEFT)
        ttk.Button(footer, text="导出 TXT", command=lambda: self._export("txt")).pack(side=tk.LEFT, padx=4)
        ttk.Button(footer, text="导出 JSON", command=lambda: self._export("json")).pack(side=tk.LEFT)
        ttk.Button(footer, text="保存配置", command=self._save_user_config).pack(side=tk.LEFT, padx=12)

        self.watch_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            footer,
            text=f"监视导出目录 ({WATCH_DIR.name})",
            variable=self.watch_var,
            command=self._toggle_watch,
        ).pack(side=tk.LEFT, padx=8)

        self.status_var = tk.StringVar(value="就绪 · 默认雷电模拟器")
        ttk.Label(footer, textvariable=self.status_var).pack(side=tk.RIGHT)

    def _on_module_frame_configure(self, _event=None) -> None:
        self.module_canvas.configure(scrollregion=self.module_canvas.bbox("all"))

    def _on_module_canvas_configure(self, event) -> None:
        self.module_canvas.itemconfig(self._module_window, width=event.width)

    def _parse_ptrid(self) -> int | None:
        raw = self.ptrid_var.get().strip()
        if not raw:
            return None
        return int(raw, 0)

    def _parse_end_offset(self) -> int | None:
        raw = self.end_offset_var.get().strip()
        if not raw:
            return None
        return int(raw, 16) if raw.lower().startswith("0x") else int(raw)

    def _current_config(self) -> ExtractConfig:
        whitelist = None
        selected = [m for m, var in self._module_vars.items() if var.get()]
        if selected:
            whitelist = selected

        return ExtractConfig(
            top_n=int(self.top_n_var.get()),
            max_depth=int(self.max_depth_var.get()),
            max_single_offset=int(self.max_offset_var.get()),
            emulator_mode=bool(self.emulator_var.get()),
            dedupe=True,
            preset=self.preset_var.get(),
            ptrid=self._parse_ptrid(),
            module_whitelist=whitelist,
            module_blacklist=self._config.module_blacklist,
            required_end_offset=self._parse_end_offset(),
            cross_validate_min=self._config.cross_validate_min,
            game_name=self.game_name_var.get().strip() or "game",
        )

    def _on_drop(self, files: list[bytes]) -> None:
        if not files:
            return
        for raw in files:
            path = Path(raw.decode("gbk", errors="ignore"))
            if path.suffix.lower() in (".sqlite", ".db", ".sqlite3", ".ptr"):
                if self.notebook.index(self.notebook.select()) == 1:
                    self._extra_files.append(path)
                    self.cross_list.insert(tk.END, str(path))
                else:
                    self._set_file(path)
                return

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[
                ("CE SQLite", "*.sqlite *.db *.sqlite3"),
                ("CE Pointer", "*.PTR *.ptr"),
            ],
        )
        if path:
            self._set_file(Path(path))

    def _set_file(self, path: Path) -> None:
        self._current_file = path
        self.file_var.set(str(path))
        try:
            ids = list_ptrids(path) if path.suffix.lower() in (".sqlite", ".db", ".sqlite3") else []
            if ids:
                self.ptrid_var.set(str(ids[-1]))
        except Exception:
            pass
        self.status_var.set(f"已选择: {path.name}")

    def _populate_result(self, result: ExtractResult) -> None:
        self._result = result
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
                    chain.source,
                ),
                tags=(format_ce_table(chain),),
            )

        self._refresh_module_panel(result)
        self._refresh_stats(result)

        msg = f"原始 {result.total_raw} 条 → 输出 {len(result.chains)} 条"
        if result.cross_validate_meta:
            msg += f"（交叉验证 {result.cross_validate_meta.get('stable_keys', '?')} 条稳定）"
        self.status_var.set(msg)

    def _run_extract(self) -> None:
        if not self._current_file:
            messagebox.showwarning("提示", "请先选择文件")
            return
        try:
            result = extract(self._current_file, config=self._current_config())
            self._populate_result(result)
        except Exception as exc:
            messagebox.showerror("提取失败", str(exc))

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
        try:
            primary = self._extra_files[0]
            extras = self._extra_files[1:]
            result = extract(primary, config=self._current_config(), extra_files=extras)
            self._populate_result(result)
            self.notebook.select(self._tab_extract)
        except Exception as exc:
            messagebox.showerror("交叉验证失败", str(exc))

    def _refresh_module_panel(self, result: ExtractResult) -> None:
        for child in self.module_inner.winfo_children():
            child.destroy()
        self._module_vars.clear()

        modules = sorted(set(result.modules_seen))
        for i, name in enumerate(modules):
            var = tk.BooleanVar(value=False)
            self._module_vars[name] = var
            ttk.Checkbutton(self.module_inner, text=name, variable=var).grid(
                row=i // 2, column=i % 2, sticky=tk.W, padx=8, pady=2
            )

    def _refresh_stats(self, result: ExtractResult) -> None:
        for item in self.stats_tree.get_children():
            self.stats_tree.delete(item)
        for stat in result.module_stats[:50]:
            self.stats_tree.insert(
                "",
                tk.END,
                values=(stat["module"], stat["count"], stat["tier"], stat["avg_depth"]),
            )

    def _copy_selected_ce(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0], "tags")
        if tags:
            self.clipboard_clear()
            self.clipboard_append(tags[0])
            self.status_var.set("已复制 CE 表达式")

    def _copy_all(self) -> None:
        if not self._result_text:
            return
        self.clipboard_clear()
        self.clipboard_append(self._result_text)

    def _export(self, fmt: str) -> None:
        if not self._result:
            messagebox.showwarning("提示", "请先提取结果")
            return
        ext = fmt
        path = filedialog.asksaveasfilename(defaultextension=f".{ext}", filetypes=[(ext, f"*.{ext}")])
        if not path:
            return
        content = to_json(self._result) if fmt == "json" else to_text(self._result)
        Path(path).write_text(content, encoding="utf-8")
        self.status_var.set(f"已导出: {path}")

    def _export_ct(self) -> None:
        if not self._result:
            messagebox.showwarning("提示", "请先提取结果")
            return
        path = filedialog.asksaveasfilename(defaultextension=".CT", filetypes=[("CE Table", "*.CT")])
        if not path:
            return
        Path(path).write_text(
            result_to_ct(self._result, title=self.game_name_var.get()),
            encoding="utf-8",
        )
        self.status_var.set(f"已导出 CT: {path}")

    def _export_python(self) -> None:
        if not self._result:
            messagebox.showwarning("提示", "请先提取结果")
            return
        default = f"{self.game_name_var.get()}_reader.py"
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            initialfile=default,
            filetypes=[("Python", "*.py")],
        )
        if not path:
            return
        save_python_script(
            self._result,
            path,
            preset_id=self.preset_var.get(),
            game_name=self.game_name_var.get(),
        )
        self.status_var.set(f"已生成 Python 脚本: {path}")

    def _test_read(self) -> None:
        if not self._result or not self._result.chains:
            messagebox.showwarning("提示", "请先提取结果")
            return
        try:
            from ce_base_extractor.runtime.win_memory import ProcessMemory
            from ce_base_extractor.filters.presets import get_preset

            preset = get_preset(self.preset_var.get())
            names = list(preset.process_names) if preset else ["dnplayer.exe"]
            mem = ProcessMemory.auto_attach(names)
            lines: list[str] = []
            with mem:
                for chain in self._result.chains[:5]:
                    try:
                        addr = mem.resolve_chain(
                            chain.module_name,
                            chain.module_offset,
                            chain.offsets,
                        )
                        val = mem.read_i32(addr)
                        lines.append(
                            f"{chain.module_name}+0x{chain.module_offset:X} → 0x{addr:X} = {val}"
                        )
                    except Exception as exc:
                        lines.append(f"{chain.module_name}: 失败 - {exc}")
            messagebox.showinfo("读取测试（前5条）", "\n".join(lines) or "无结果")
        except Exception as exc:
            messagebox.showerror("读取失败", f"{exc}\n\n请确认雷电模拟器已运行且 CE 附加同一进程")

    def _save_favorites(self) -> None:
        if not self._result or not self._result.chains:
            messagebox.showwarning("提示", "暂无结果可保存")
            return
        game = self.game_name_var.get().strip() or "未命名游戏"
        n = self._history.add_chains(game, self._result.chains)
        self._refresh_history()
        messagebox.showinfo("收藏", f"已保存 {n} 条到「{game}」")

    def _refresh_history(self) -> None:
        games = self._history.list_games()
        self.history_combo["values"] = games
        if games and not self.history_game_var.get():
            self.history_game_var.set(games[0])
            self._show_history_game()

    def _show_history_game(self) -> None:
        game = self.history_game_var.get()
        entries = self._history.get_chains(game)
        self.history_text.delete("1.0", tk.END)
        for e in entries:
            offsets = " → ".join(f"+0x{o:X}" for o in e["offsets"])
            self.history_text.insert(
                tk.END,
                f"{e['module']}+0x{e['module_offset']:X} {offsets}  (score={e.get('score', 0)})\n",
            )

    def _export_history_python(self) -> None:
        game = self.history_game_var.get()
        if not game:
            return
        entries = self._history.get_chains(game)
        if not entries:
            messagebox.showwarning("提示", "该游戏暂无收藏")
            return
        from ce_base_extractor.export.python_script import chains_to_python_script
        from ce_base_extractor.filters.presets import get_preset
        from ce_base_extractor.models import PointerChain

        chains = [
            PointerChain(
                e["module"],
                e["module_offset"],
                tuple(e["offsets"]),
                score=float(e.get("score", 0)),
            )
            for e in entries
        ]
        preset = get_preset(self.preset_var.get())
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            initialfile=f"{game}_reader.py",
        )
        if not path:
            return
        Path(path).write_text(
            chains_to_python_script(chains, preset=preset, game_name=game),
            encoding="utf-8",
        )
        self.status_var.set(f"已从收藏导出: {path}")

    def _save_user_config(self) -> None:
        cfg = self._current_config()
        path = save_config(cfg)
        self.status_var.set(f"配置已保存: {path}")

    def _toggle_watch(self) -> None:
        if self.watch_var.get():
            WATCH_DIR.mkdir(parents=True, exist_ok=True)

            def on_new(path: Path) -> None:
                self.after(0, lambda: self._on_watch_file(path))

            self._watcher = FolderWatcher(WATCH_DIR, on_new)
            self._watcher.start()
            self.status_var.set(f"正在监视: {WATCH_DIR}")
        else:
            if self._watcher:
                self._watcher.stop()
                self._watcher = None
            self.status_var.set("已停止监视")

    def _on_watch_file(self, path: Path) -> None:
        self._set_file(path)
        try:
            result = extract(path, config=self._current_config())
            self._populate_result(result)
            self.status_var.set(f"自动提取: {path.name}")
        except Exception as exc:
            self.status_var.set(f"自动提取失败: {exc}")

    def destroy(self) -> None:
        if self._watcher:
            self._watcher.stop()
        super().destroy()


def run_gui() -> None:
    app = App()
    app.mainloop()
