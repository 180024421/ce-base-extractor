from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *


class ExtractMixin:
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
            failed: list[str] = []
            with mem:
                for i, chain in enumerate(self._result.chains, 1):
                    name = chain.export_name(i)
                    try:
                        self._before_verify[name] = read_chain_value(
                            mem, chain, int(self.pointer_size_var.get())
                        )
                    except Exception:
                        failed.append(name)
            msg = f"已记录 {len(self._before_verify)} 个字段\n请重启雷电后点「重启验证」"
            if failed:
                msg += f"\n\n读取失败 {len(failed)} 个: {', '.join(failed[:8])}"
                if len(failed) > 8:
                    msg += " …"
            messagebox.showinfo("记录读数", msg)
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
