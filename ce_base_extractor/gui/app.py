from __future__ import annotations

import json
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.compare.sqlite_diff import diff_sqlite_files, diff_sqlite_many
from ce_base_extractor.export.batch_export import export_all
from ce_base_extractor.export.ct_export import result_to_ct
from ce_base_extractor.export.formatter import format_ce_table, to_json, to_text
from ce_base_extractor.export.lua_script import save_lua_script
from ce_base_extractor.export.python_script import save_python_script
from ce_base_extractor.export.scc_export import save_scc_json
from ce_base_extractor.filters.presets import PRESETS, get_preset
from ce_base_extractor.gui.chain_dialog import open_chain_editor
from ce_base_extractor.gui.process_picker import pick_process
from ce_base_extractor.gui.wizard import show_first_run_wizard
from ce_base_extractor.history.store import HistoryStore
from ce_base_extractor.integrations.scc import scheduled_recheck_profile
from ce_base_extractor.io.scc_import import import_scc_to_result
from ce_base_extractor.models import ExtractConfig, ExtractResult, PointerChain
from ce_base_extractor.parsers.sqlite_parser import list_ptrids
from ce_base_extractor.pipeline import extract, load_config, save_config, wizard_completed
from ce_base_extractor.profiles.migrate import compare_profiles
from ce_base_extractor.profiles.store import GameProfile, ProfileStore
from ce_base_extractor.runtime.win_memory import ProcessMemory, read_chain_value
from ce_base_extractor.suggest.field_names import suggest_field_names
from ce_base_extractor.verify.restart_verify import verify_restart_stability
from ce_base_extractor.watch.folder_watcher import FolderWatcher
from ce_base_extractor.watch.incremental_cross import IncrementalCrossValidator

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
        self._before_verify: dict[str, int | float | bytes] = {}
        self._target_pid: int | None = self._config.target_pid
        self._profiles = ProfileStore()
        self._monitor_running = False
        self._monitor_job: str | None = None
        self._monitor_prev: dict[str, object] = {}
        self._extract_busy = False
        self._incremental_cross: IncrementalCrossValidator | None = None
        self._monitor_mem: ProcessMemory | None = None

        self._build_ui()
        if _HAS_WINDND:
            windnd.hook_dropfiles(self, func=self._on_drop)
        if not wizard_completed():
            self.after(300, lambda: show_first_run_wizard(self))

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

    def _build_extract_tab(self) -> None:
        row = ttk.Frame(self._tab_extract)
        row.pack(fill=tk.X)
        ttk.Button(row, text="选择 SQLite/PTR", command=self._browse).pack(side=tk.LEFT)
        ttk.Button(row, text="提取基址", command=self._run_extract).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="导出 Python", command=self._export_python).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="导出 Lua", command=self._export_lua).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="导出 SCC JSON", command=self._export_scc).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="导出 .CT", command=self._export_ct).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="选进程", command=self._pick_process).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="记录读数", command=self._snapshot_values).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="重启验证", command=self._restart_verify).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="测试读取", command=self._test_read).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="智能命名", command=self._auto_name).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="一键导出全部", command=self._export_all).pack(side=tk.LEFT, padx=4)
        ttk.Button(row, text="导入SCC", command=self._import_scc).pack(side=tk.LEFT, padx=4)

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
        self.pointer_size_var = tk.IntVar(value=getattr(self._config, "pointer_size", 8))
        self.il2cpp_var = tk.StringVar(value=self._config.il2cpp_map_path or "")
        self.pid_label_var = tk.StringVar(value="进程: 自动")

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
        ttk.Label(opts, text="最大层级").grid(
            row=1, column=2, sticky=tk.W, padx=(12, 0), pady=(6, 0)
        )
        ttk.Spinbox(opts, from_=1, to=10, textvariable=self.max_depth_var, width=8).grid(
            row=1, column=3, padx=4, pady=(6, 0)
        )
        ttk.Label(opts, text="末级偏移(hex)").grid(
            row=1, column=4, sticky=tk.W, padx=(12, 0), pady=(6, 0)
        )
        ttk.Entry(opts, textvariable=self.end_offset_var, width=10).grid(
            row=1, column=5, padx=4, pady=(6, 0)
        )
        ttk.Checkbutton(opts, text="模拟器模式", variable=self.emulator_var).grid(
            row=1, column=6, padx=(12, 0), pady=(6, 0)
        )
        ttk.Label(opts, text="指针宽度").grid(row=2, column=0, sticky=tk.W, pady=(6, 0))
        ttk.Combobox(
            opts, textvariable=self.pointer_size_var, values=("4", "8"), width=6, state="readonly"
        ).grid(row=2, column=1, padx=4, pady=(6, 0), sticky=tk.W)
        ttk.Label(opts, text="Il2Cpp 映射").grid(
            row=2, column=2, sticky=tk.W, padx=(12, 0), pady=(6, 0)
        )
        ttk.Entry(opts, textvariable=self.il2cpp_var, width=36).grid(
            row=2, column=3, columnspan=2, padx=4, pady=(6, 0)
        )
        ttk.Button(opts, text="浏览", command=self._browse_il2cpp).grid(
            row=2, column=5, pady=(6, 0)
        )
        ttk.Label(opts, textvariable=self.pid_label_var).grid(
            row=2, column=6, padx=(12, 0), pady=(6, 0), sticky=tk.W
        )

        adv = ttk.LabelFrame(self._tab_extract, text="高级选项", padding=8)
        adv.pack(fill=tk.X, pady=4)
        self.live_probe_var = tk.BooleanVar(value=self._config.live_probe)
        self.probe_drop_var = tk.BooleanVar(value=self._config.probe_drop_unreadable)
        self.fuzzy_var = tk.BooleanVar(value=self._config.fuzzy_dedupe)
        self.cross_all_var = tk.BooleanVar(value=self._config.cross_validate_require_all)
        self.stream_var = tk.BooleanVar(value=self._config.stream_single_file)
        self.android_pkg_var = tk.StringVar(value=getattr(self._config, "android_package", ""))
        ttk.Checkbutton(adv, text="在线探针", variable=self.live_probe_var).pack(side=tk.LEFT)
        ttk.Checkbutton(adv, text="剔除不可读", variable=self.probe_drop_var).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Checkbutton(adv, text="模糊去重", variable=self.fuzzy_var).pack(side=tk.LEFT)
        ttk.Checkbutton(adv, text="交叉需全命中", variable=self.cross_all_var).pack(
            side=tk.LEFT, padx=8
        )
        ttk.Checkbutton(adv, text="流式读取", variable=self.stream_var).pack(side=tk.LEFT)
        ttk.Label(adv, text="Android包名").pack(side=tk.LEFT, padx=(12, 4))
        ttk.Entry(adv, textvariable=self.android_pkg_var, width=28).pack(side=tk.LEFT)

        paned = ttk.Panedwindow(self._tab_extract, orient=tk.VERTICAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=6)

        list_frame = ttk.LabelFrame(paned, text="结果（双击复制 CE 表达式）", padding=4)
        detail_frame = ttk.LabelFrame(paned, text="详情", padding=4)
        paned.add(list_frame, weight=2)
        paned.add(detail_frame, weight=3)

        self.tree = ttk.Treeview(
            list_frame,
            columns=("score", "name", "type", "module", "base", "depth", "verified"),
            show="headings",
        )
        for col, title, w in (
            ("score", "评分", 50),
            ("name", "字段名", 90),
            ("type", "类型", 60),
            ("module", "模块", 180),
            ("base", "基址", 100),
            ("depth", "层级", 40),
            ("verified", "验证", 40),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb = ttk.Scrollbar(list_frame, command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        ttk.Button(list_frame, text="编辑字段", command=self._edit_selected_chain).pack(
            side=tk.BOTTOM, pady=4
        )

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
        ttk.Button(btns, text="对比 SQLite", command=self._diff_sqlite).pack(side=tk.LEFT, padx=6)

        self.cross_stability_var = tk.StringVar(value="稳定率: —")
        ttk.Label(
            self._tab_cross, textvariable=self.cross_stability_var, foreground="#0066cc"
        ).pack(anchor=tk.W, pady=(0, 4))

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
        self._module_window = self.module_canvas.create_window(
            (0, 0), window=self.module_inner, anchor=tk.NW
        )
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

    def _build_monitor_tab(self) -> None:
        row = ttk.Frame(self._tab_monitor)
        row.pack(fill=tk.X)
        self.monitor_interval_var = tk.IntVar(value=2)
        ttk.Label(row, text="刷新间隔(秒)").pack(side=tk.LEFT)
        ttk.Spinbox(row, from_=1, to=60, textvariable=self.monitor_interval_var, width=6).pack(
            side=tk.LEFT, padx=6
        )
        self.monitor_btn = ttk.Button(row, text="开始监控", command=self._toggle_monitor)
        self.monitor_btn.pack(side=tk.LEFT, padx=6)

        self.monitor_tree = ttk.Treeview(
            self._tab_monitor,
            columns=("name", "value", "type", "updated"),
            show="headings",
            height=14,
        )
        for col, title, w in (
            ("name", "字段", 120),
            ("value", "当前值", 160),
            ("type", "类型", 70),
            ("updated", "时间", 90),
        ):
            self.monitor_tree.heading(col, text=title)
            self.monitor_tree.column(col, width=w, anchor=tk.W)
        self.monitor_tree.tag_configure("changed", foreground="#c0392b")
        self.monitor_tree.tag_configure("same", foreground="#27ae60")
        self.monitor_tree.pack(fill=tk.BOTH, expand=True, pady=8)

    def _build_profile_tab(self) -> None:
        row = ttk.Frame(self._tab_profile)
        row.pack(fill=tk.X, pady=4)
        ttk.Button(row, text="保存当前为游戏配置", command=self._save_profile).pack(side=tk.LEFT)
        ttk.Button(row, text="加载配置", command=self._load_profile).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="立即复检", command=self._profile_recheck).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="版本对比", command=self._profile_migrate).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="删除配置", command=self._delete_profile).pack(side=tk.LEFT)
        ttk.Button(row, text="刷新列表", command=self._refresh_profiles).pack(side=tk.LEFT, padx=6)

        self.profile_var = tk.StringVar()
        ttk.Label(self._tab_profile, text="已保存的游戏配置").pack(anchor=tk.W, pady=(8, 0))
        self.profile_combo = ttk.Combobox(
            self._tab_profile, textvariable=self.profile_var, state="readonly"
        )
        self.profile_combo.pack(fill=tk.X)
        self.profile_info = tk.Text(self._tab_profile, height=12, font=("Consolas", 10))
        self.profile_info.pack(fill=tk.BOTH, expand=True, pady=8)
        self._refresh_profiles()

    def _build_history_tab(self) -> None:
        row = ttk.Frame(self._tab_history)
        row.pack(fill=tk.X)
        ttk.Button(row, text="保存当前结果到收藏", command=self._save_favorites).pack(side=tk.LEFT)
        ttk.Button(row, text="刷新", command=self._refresh_history).pack(side=tk.LEFT, padx=6)
        ttk.Button(row, text="导出收藏为 Python", command=self._export_history_python).pack(
            side=tk.LEFT
        )

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
            cross_validate_require_all=bool(self.cross_all_var.get()),
            cross_validate_fuzzy=bool(self.fuzzy_var.get()),
            game_name=self.game_name_var.get().strip() or "game",
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
            il2cpp_map_path=self.il2cpp_var.get().strip() or None,
            android_package=self.android_pkg_var.get().strip(),
            live_probe=bool(self.live_probe_var.get()),
            probe_drop_unreadable=bool(self.probe_drop_var.get()),
            fuzzy_dedupe=bool(self.fuzzy_var.get()),
            stream_single_file=bool(self.stream_var.get()),
            sqlite_module_prefilter=self._config.sqlite_module_prefilter,
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
        for i, chain in enumerate(result.chains, 1):
            self.tree.insert(
                "",
                tk.END,
                iid=str(i - 1),
                values=(
                    f"{chain.score:.1f}",
                    chain.export_name(i),
                    chain.value_type,
                    chain.module_name,
                    f"0x{chain.module_offset:X}",
                    chain.depth,
                    "✓" if chain.verified else "",
                ),
                tags=(format_ce_table(chain),),
            )

        self._refresh_module_panel(result)
        self._refresh_stats(result)

        msg = f"原始 {result.total_raw} 条 → 输出 {len(result.chains)} 条"
        if result.cross_validate_meta:
            meta = result.cross_validate_meta
            ratio = meta.get("stability_ratio")
            if ratio is not None:
                msg += f"（稳定率 {float(ratio) * 100:.1f}%）"
            else:
                msg += f"（交叉验证 {meta.get('stable_keys', '?')} 条稳定）"
            self.cross_stability_var.set(
                f"稳定率: {float(meta.get('stability_ratio', 0)) * 100:.1f}%"
                if meta.get("stability_ratio") is not None
                else f"交集: {meta.get('stable_keys', '?')} 条"
            )
        self.status_var.set(msg)

    def _run_extract(self) -> None:
        if not self._current_file:
            messagebox.showwarning("提示", "请先选择文件")
            return
        if self._extract_busy:
            return
        self._extract_async(
            lambda on_progress=None: extract(
                self._current_file,
                config=self._current_config(),
                on_progress=on_progress,
            ),
            "正在提取基址…",
            use_progress=True,
        )

    def _extract_async(self, fn, title: str, *, use_progress: bool = False) -> None:
        self._extract_busy = True
        self.status_var.set(title)
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("320x90")
        win.transient(self)
        ttk.Label(win, text=title).pack(pady=(12, 4))
        prog_label = ttk.Label(win, text="")
        prog_label.pack()
        bar = ttk.Progressbar(win, mode="indeterminate" if not use_progress else "determinate")
        bar.pack(fill=tk.X, padx=16, pady=4)
        if use_progress:
            bar.configure(maximum=100, value=0)
        else:
            bar.start(10)

        def work() -> None:
            try:
                if use_progress:
                    last = [0]

                    def on_progress(n: int) -> None:
                        last[0] = n
                        self.after(0, lambda: prog_label.config(text=f"已扫描 {n} 行"))

                    result = fn(on_progress)
                else:
                    result = fn()
                self.after(0, lambda: self._on_extract_done(result, win))
            except Exception as exc:
                self.after(0, lambda e=exc: self._on_extract_error(e, win))

        threading.Thread(target=work, daemon=True).start()

    def _on_extract_done(self, result: ExtractResult, win: tk.Toplevel) -> None:
        win.destroy()
        self._extract_busy = False
        self._populate_result(result)

    def _on_extract_error(self, exc: Exception, win: tk.Toplevel) -> None:
        win.destroy()
        self._extract_busy = False
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

    def _on_tree_double_click(self, event) -> None:
        region = self.tree.identify("region", event.x, event.y)
        if region == "cell":
            col = self.tree.identify_column(event.x)
            if col in ("#2", "#3"):
                self._edit_selected_chain()
                return
        self._copy_selected_ce()

    def _copy_selected_ce(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        tags = self.tree.item(sel[0], "tags")
        if tags:
            self.clipboard_clear()
            self.clipboard_append(tags[0])
            self.status_var.set("已复制 CE 表达式")

    def _edit_selected_chain(self) -> None:
        if not self._result:
            return
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("提示", "请先选择一条结果")
            return
        idx = int(sel[0])
        if idx < 0 or idx >= len(self._result.chains):
            return
        updated = open_chain_editor(self, self._result.chains[idx], idx + 1)
        if updated:
            chains = list(self._result.chains)
            chains[idx] = updated
            self._result = ExtractResult(
                chains=chains,
                total_raw=self._result.total_raw,
                total_after_filter=self._result.total_after_filter,
                modules_seen=self._result.modules_seen,
                source_file=self._result.source_file,
                ptrid=self._result.ptrid,
                cross_validate_meta=self._result.cross_validate_meta,
                module_stats=self._result.module_stats,
            )
            self._populate_result(self._result)

    def _browse_il2cpp(self) -> None:
        path = filedialog.askopenfilename(
            filetypes=[("Il2Cpp", "*.json *.cs *.txt"), ("所有", "*.*")]
        )
        if path:
            self.il2cpp_var.set(path)

    def _pick_process(self) -> None:
        preset = get_preset(self.preset_var.get())
        names = list(preset.process_names) if preset else ["dnplayer.exe"]
        try:
            processes = ProcessMemory.list_matching(names)
        except OSError as exc:
            messagebox.showerror("错误", str(exc))
            return
        if not processes:
            messagebox.showwarning("提示", "未找到雷电进程，请先启动模拟器")
            return
        picked = pick_process(self, processes)
        if picked:
            self._target_pid = picked.pid
            self.pid_label_var.set(f"进程: {picked.label}")

    def _snapshot_values(self) -> None:
        if not self._result:
            return
        try:
            preset = get_preset(self.preset_var.get())
            names = list(preset.process_names) if preset else ["dnplayer.exe"]
            mem = ProcessMemory.auto_attach(names, pid=self._target_pid)
            self._before_verify.clear()
            with mem:
                for i, chain in enumerate(self._result.chains, 1):
                    name = chain.export_name(i)
                    try:
                        self._before_verify[name] = read_chain_value(
                            mem, chain, int(self.pointer_size_var.get())
                        )
                    except Exception:
                        pass
            messagebox.showinfo(
                "记录读数", f"已记录 {len(self._before_verify)} 个字段\n请重启雷电后点「重启验证」"
            )
            game = self.game_name_var.get().strip()
            if game:
                try:
                    profile = self._profiles.load(game)
                    profile.record_snapshots(self._before_verify)
                    self._profiles.save(profile)
                except FileNotFoundError:
                    pass
        except Exception as exc:
            messagebox.showerror("失败", str(exc))

    def _restart_verify(self) -> None:
        if not self._result or not self._before_verify:
            messagebox.showwarning("提示", "请先点「记录读数」再重启模拟器")
            return
        results = verify_restart_stability(
            self._result.chains,
            self._before_verify,
            preset_id=self.preset_var.get(),
            pointer_size=int(self.pointer_size_var.get()),
            pid=self._target_pid,
        )
        lines = []
        verified_names: list[str] = []
        chains = list(self._result.chains)
        for i, r in enumerate(results):
            name = chains[i].export_name(i + 1)
            if r.error:
                status = f"失败: {r.error}"
            elif r.stable:
                if r.value_unchanged is False:
                    status = f"可读 ✓（数值变化 {r.before} → {r.after}）"
                else:
                    status = "稳定 ✓"
            else:
                status = "不稳定"
            lines.append(f"{name}: {status}")
            if r.stable:
                verified_names.append(name)
                chains[i] = PointerChain(
                    module_name=chains[i].module_name,
                    module_offset=chains[i].module_offset,
                    offsets=chains[i].offsets,
                    score=chains[i].score,
                    source=chains[i].source,
                    field_name=chains[i].field_name,
                    value_type=chains[i].value_type,
                    verified=True,
                    il2cpp_symbol=chains[i].il2cpp_symbol,
                )
        self._result = ExtractResult(
            chains=chains,
            total_raw=self._result.total_raw,
            total_after_filter=self._result.total_after_filter,
            modules_seen=self._result.modules_seen,
            source_file=self._result.source_file,
            ptrid=self._result.ptrid,
            cross_validate_meta=self._result.cross_validate_meta,
            module_stats=self._result.module_stats,
        )
        self._populate_result(self._result)
        game = self.game_name_var.get().strip() or "未命名游戏"
        self._history.mark_verified(game, verified_names)
        messagebox.showinfo("重启验证", "\n".join(lines[:15]))

    def _export_scc(self) -> None:
        if not self._result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"{self.game_name_var.get()}_bases_scc.json",
        )
        if path:
            save_scc_json(self._result, path, preset_id=self.preset_var.get())
            self.status_var.set(f"已导出 SCC: {path}")

    def _export_lua(self) -> None:
        if not self._result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".lua",
            initialfile=f"{self.game_name_var.get()}_reader.lua",
        )
        if path:
            save_lua_script(self._result, path)
            self.status_var.set(f"已导出 Lua: {path}")

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
        path = filedialog.asksaveasfilename(
            defaultextension=f".{ext}", filetypes=[(ext, f"*.{ext}")]
        )
        if not path:
            return
        content = to_json(self._result) if fmt == "json" else to_text(self._result)
        Path(path).write_text(content, encoding="utf-8")
        self.status_var.set(f"已导出: {path}")

    def _export_ct(self) -> None:
        if not self._result:
            messagebox.showwarning("提示", "请先提取结果")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".CT", filetypes=[("CE Table", "*.CT")]
        )
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
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
        )
        self.status_var.set(f"已生成 Python 脚本: {path}")

    def _test_read(self) -> None:
        if not self._result or not self._result.chains:
            messagebox.showwarning("提示", "请先提取结果")
            return
        try:
            from ce_base_extractor.filters.presets import get_preset
            from ce_base_extractor.runtime.win_memory import ProcessMemory

            preset = get_preset(self.preset_var.get())
            names = list(preset.process_names) if preset else ["dnplayer.exe"]
            mem = ProcessMemory.auto_attach(names, pid=self._target_pid)
            ps = int(self.pointer_size_var.get())
            lines: list[str] = []
            with mem:
                for i, chain in enumerate(self._result.chains[:5], 1):
                    try:
                        val = read_chain_value(mem, chain, ps)
                        lines.append(f"{chain.export_name(i)} ({chain.value_type}) = {val}")
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

    def _auto_name(self) -> None:
        if not self._result:
            return
        chains = suggest_field_names(self._result.chains)
        self._result = ExtractResult(
            chains=chains,
            total_raw=self._result.total_raw,
            total_after_filter=self._result.total_after_filter,
            modules_seen=self._result.modules_seen,
            source_file=self._result.source_file,
            ptrid=self._result.ptrid,
            cross_validate_meta=self._result.cross_validate_meta,
            module_stats=self._result.module_stats,
        )
        self._populate_result(self._result)
        self.status_var.set("已应用智能字段命名")

    def _export_all(self) -> None:
        if not self._result:
            messagebox.showwarning("提示", "请先提取结果")
            return
        folder = filedialog.askdirectory(initialdir=str(WATCH_DIR))
        if not folder:
            return
        game = self.game_name_var.get().strip() or "game"
        files = export_all(
            self._result,
            folder,
            game_name=game,
            preset_id=self.preset_var.get(),
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
        )
        messagebox.showinfo("导出完成", f"已导出 {len(files)} 个文件到:\n{folder}")

    def _import_scc(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("SCC JSON", "*.json")])
        if not path:
            return
        try:
            result = import_scc_to_result(path)
            self._populate_result(result)
            self.status_var.set(f"已导入: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))

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

    def _toggle_monitor(self) -> None:
        if self._monitor_running:
            self._stop_monitor()
        else:
            self._start_monitor()

    def _start_monitor(self) -> None:
        if not self._result or not self._result.chains:
            messagebox.showwarning("提示", "请先提取结果")
            return
        self._monitor_running = True
        self.monitor_btn.configure(text="停止监控")
        self._monitor_tick()

    def _stop_monitor(self) -> None:
        self._monitor_running = False
        self.monitor_btn.configure(text="开始监控")
        if self._monitor_job:
            self.after_cancel(self._monitor_job)
            self._monitor_job = None
        if self._monitor_mem:
            self._monitor_mem.close()
            self._monitor_mem = None

    def _monitor_tick(self) -> None:
        if not self._monitor_running or not self._result:
            return
        from datetime import datetime

        try:
            preset = get_preset(self.preset_var.get())
            names = list(preset.process_names) if preset else ["dnplayer.exe"]
            if self._monitor_mem is None:
                self._monitor_mem = ProcessMemory.auto_attach(names, pid=self._target_pid)
            mem = self._monitor_mem
            ps = int(self.pointer_size_var.get())
            now = datetime.now().strftime("%H:%M:%S")
            for item in self.monitor_tree.get_children():
                self.monitor_tree.delete(item)
            for i, chain in enumerate(self._result.chains, 1):
                name = chain.export_name(i)
                try:
                    val = read_chain_value(mem, chain, ps)
                    prev = self._monitor_prev.get(name)
                    tag = "same" if prev == val else "changed"
                    if prev is None:
                        tag = ""
                    self._monitor_prev[name] = val
                    self.monitor_tree.insert(
                        "", tk.END, values=(name, val, chain.value_type, now), tags=(tag,)
                    )
                except Exception as exc:
                    self.monitor_tree.insert(
                        "", tk.END, values=(name, f"ERR: {exc}", chain.value_type, now)
                    )
        except Exception as exc:
            self.status_var.set(f"监控错误: {exc}")
            if self._monitor_mem:
                self._monitor_mem.close()
                self._monitor_mem = None

        interval = max(1, int(self.monitor_interval_var.get())) * 1000
        self._monitor_job = self.after(interval, self._monitor_tick)

    def _refresh_profiles(self) -> None:
        games = self._profiles.list_games()
        self.profile_combo["values"] = games
        if games and not self.profile_var.get():
            self.profile_var.set(games[0])

    def _save_profile(self) -> None:
        if not self._result:
            return
        game = self.game_name_var.get().strip() or "未命名游戏"
        profile = GameProfile.from_result(
            self._result,
            game_name=game,
            preset=self.preset_var.get(),
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
            android_package=self.android_pkg_var.get().strip(),
        )
        if self._before_verify:
            profile.record_snapshots(self._before_verify)
        path = self._profiles.save(profile)
        self._refresh_profiles()
        self.profile_var.set(game)
        messagebox.showinfo("游戏配置", f"已保存: {path}")

    def _load_profile(self) -> None:
        game = self.profile_var.get()
        if not game:
            return
        try:
            profile = self._profiles.load(game)
            self.game_name_var.set(profile.game_name)
            self.preset_var.set(profile.preset)
            self.pointer_size_var.set(str(profile.pointer_size))
            self._target_pid = profile.target_pid
            result = profile.to_result()
            self._before_verify = profile.snapshot_values()
            self._populate_result(result)
            self.profile_info.delete("1.0", tk.END)
            self.profile_info.insert(tk.END, f"已加载 {game}\n链数: {len(result.chains)}\n")
            self.status_var.set(f"已加载游戏配置: {game}")
        except Exception as exc:
            messagebox.showerror("加载失败", str(exc))

    def _profile_recheck(self) -> None:
        game = self.profile_var.get() or self.game_name_var.get().strip()
        if not game:
            messagebox.showwarning("提示", "请选择或填写游戏名")
            return
        try:
            result = scheduled_recheck_profile(game, pid=self._target_pid)
            lines = [
                f"{d['name']}: {'稳定' if d['stable'] else d.get('error', '不稳定')}"
                for d in result.details
            ]
            messagebox.showinfo(
                "复检结果", "\n".join(lines[:15]) + f"\n\n稳定 {result.stable}/{result.total}"
            )
        except Exception as exc:
            messagebox.showerror("复检失败", str(exc))

    def _profile_migrate(self) -> None:
        game = self.profile_var.get()
        if not game:
            messagebox.showwarning("提示", "请选择游戏配置")
            return
        path = filedialog.askopenfilename(filetypes=[("SQLite", "*.sqlite *.db")])
        if not path:
            return
        try:
            old = self._profiles.load(game)
            cfg = self._current_config()
            cfg.game_name = game
            cfg.live_probe = False
            new_result = extract(path, config=cfg)
            new = GameProfile.from_result(new_result, game, preset=old.preset)
            report = compare_profiles(old, new)
            msg = json.dumps(report.to_dict(), ensure_ascii=False, indent=2)
            self.profile_info.delete("1.0", tk.END)
            self.profile_info.insert(tk.END, msg)
        except Exception as exc:
            messagebox.showerror("对比失败", str(exc))

    def _delete_profile(self) -> None:
        game = self.profile_var.get()
        if not game:
            return
        if messagebox.askyesno("确认", f"删除配置「{game}」?"):
            self._profiles.delete(game)
            self.profile_var.set("")
            self._refresh_profiles()

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


def run_gui() -> None:
    app = App()
    app.mainloop()
