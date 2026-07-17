from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *
from ce_base_extractor.gui.theme import THEME, FileDropCard, make_tool_group


class ExtractMixin:
    def _build_extract_tab(self) -> None:
        # ── 主操作 ──
        top = ttk.Frame(self._tab_extract)
        top.pack(fill=tk.X, pady=(0, 10))

        primary = ttk.Frame(top)
        primary.pack(side=tk.LEFT)
        ttk.Button(primary, text="选择文件", style="Primary.TButton", command=self._browse).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(primary, text="提取基址", style="Accent.TButton", command=self._run_extract).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(primary, text="选进程", command=self._pick_process).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(primary, text="导入 SCC", command=self._import_scc).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(primary, text="ASS 交接包", command=self._export_ass_handoff).pack(side=tk.LEFT)

        # ── 文件卡片 ──
        self.file_var = tk.StringVar(value="尚未选择文件")
        self._file_card = FileDropCard(
            self._tab_extract, self.file_var, allow_drop=HAS_WINDND
        )
        self._file_card.pack(fill=tk.X, pady=(0, 10))

        # ── 下一步引导 ──
        self._next_steps = make_tool_group(self._tab_extract, "下一步（有结果后）")
        self._next_steps.pack(fill=tk.X, pady=(0, 8))
        ns = ttk.Frame(self._next_steps)
        ns.pack(fill=tk.X)
        self.next_step_var = tk.StringVar(value="先交叉验证或提取，得到结果后这里会出现快捷操作")
        ttk.Label(ns, textvariable=self.next_step_var, style="Hint.TLabel").pack(anchor=tk.W, pady=(0, 4))
        for text, cmd in (
            ("智能命名", self._auto_name),
            ("测试读取", self._test_read),
            ("导出全部", self._export_all),
            ("ASS 交接包", self._export_ass_handoff),
            ("打开导出目录", self._open_export_dir),
        ):
            ttk.Button(ns, text=text, command=cmd).pack(side=tk.LEFT, padx=(0, 6))

        # ── 参数区（日常只显示模拟器+游戏名）──
        opts = make_tool_group(self._tab_extract, "提取参数")
        opts.pack(fill=tk.X, pady=(0, 8))

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

        basic = ttk.Frame(opts)
        basic.pack(fill=tk.X)
        ttk.Label(basic, text="模拟器").pack(side=tk.LEFT)
        ttk.Combobox(
            basic,
            textvariable=self.preset_var,
            values=[p.id for p in PRESETS.values()],
            state="readonly",
            width=11,
        ).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(basic, text="游戏名").pack(side=tk.LEFT)
        ttk.Entry(basic, textvariable=self.game_name_var, width=16).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Label(basic, textvariable=self.pid_label_var, foreground=THEME["text_secondary"]).pack(
            side=tk.LEFT
        )

        self._extract_extra = ttk.Frame(opts)
        grid = self._extract_extra

        ttk.Label(grid, text="ptrid").grid(row=0, column=0, sticky=tk.W, padx=(0, 4), pady=3)
        ttk.Entry(grid, textvariable=self.ptrid_var, width=8).grid(row=0, column=1, sticky=tk.W, pady=3)
        ttk.Label(grid, text="输出条数").grid(row=0, column=2, sticky=tk.W, padx=(16, 4), pady=3)
        ttk.Spinbox(grid, from_=1, to=200, textvariable=self.top_n_var, width=8).grid(
            row=0, column=3, sticky=tk.W, padx=(0, 16), pady=3
        )
        ttk.Label(grid, text="最大层级").grid(row=0, column=4, sticky=tk.W, padx=(0, 4), pady=3)
        ttk.Spinbox(grid, from_=1, to=10, textvariable=self.max_depth_var, width=8).grid(
            row=0, column=5, sticky=tk.W, pady=3
        )

        ttk.Label(grid, text="最大偏移").grid(row=1, column=0, sticky=tk.W, padx=(0, 4), pady=3)
        ttk.Spinbox(
            grid,
            from_=16,
            to=65536,
            increment=16,
            textvariable=self.max_offset_var,
            width=8,
        ).grid(row=1, column=1, sticky=tk.W, pady=3)
        ttk.Label(grid, text="末级偏移(hex)").grid(row=1, column=2, sticky=tk.W, padx=(16, 4), pady=3)
        ttk.Entry(grid, textvariable=self.end_offset_var, width=10).grid(
            row=1, column=3, sticky=tk.W, padx=(0, 16), pady=3
        )

        row2 = ttk.Frame(grid)
        row2.grid(row=2, column=0, columnspan=6, sticky=tk.W, pady=(4, 0))
        ttk.Label(row2, text="指针宽度").pack(side=tk.LEFT)
        ttk.Combobox(
            row2, textvariable=self.pointer_size_var, values=("4", "8"), width=5, state="readonly"
        ).pack(side=tk.LEFT, padx=(4, 16))
        ttk.Checkbutton(row2, text="模拟器模式", variable=self.emulator_var).pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(row2, text="Il2Cpp").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.il2cpp_var, width=32).pack(side=tk.LEFT, padx=4)
        ttk.Button(row2, text="浏览", command=self._browse_il2cpp).pack(side=tk.LEFT, padx=(0, 12))

        # 默认隐藏额外参数（高级模式再显示）
        # _extract_extra 不 pack，直到 _show_extract_extra_params(True)

        # ── 导出 / 验证（双列工具组）──
        tools_row = ttk.Frame(self._tab_extract)
        tools_row.pack(fill=tk.X, pady=(0, 8))
        tools_row.columnconfigure(0, weight=1)
        tools_row.columnconfigure(1, weight=1)

        export_grp = make_tool_group(tools_row, "导出")
        export_grp.grid(row=0, column=0, sticky=tk.NSEW, padx=(0, 6))
        exp_inner = ttk.Frame(export_grp)
        exp_inner.pack(fill=tk.X)
        for i, (text, cmd) in enumerate(
            [
                ("Python", self._export_python),
                ("Lua", self._export_lua),
                ("SCC JSON", self._export_scc),
                (".CT", self._export_ct),
                ("全部", self._export_all),
            ]
        ):
            ttk.Button(exp_inner, text=text, command=cmd).grid(row=0, column=i, padx=3, pady=2)

        verify_grp = make_tool_group(tools_row, "验证与工具")
        verify_grp.grid(row=0, column=1, sticky=tk.NSEW, padx=(6, 0))
        ver_inner = ttk.Frame(verify_grp)
        ver_inner.pack(fill=tk.X)
        self.verify_step_var = tk.StringVar(value="步骤: ① 记录读数 → ② 重启模拟器 → ③ 重启验证")
        ttk.Label(ver_inner, textvariable=self.verify_step_var, style="Hint.TLabel").grid(
            row=0, column=0, columnspan=4, sticky=tk.W, pady=(0, 4)
        )
        for i, (text, cmd) in enumerate(
            [
                ("记录读数", self._snapshot_values),
                ("重启验证", self._restart_verify),
                ("测试读取", self._test_read),
                ("智能命名", self._auto_name),
            ]
        ):
            ttk.Button(ver_inner, text=text, command=cmd).grid(row=1, column=i, padx=3, pady=2)

        # ── 高级选项（可折叠）──
        self._adv_visible = tk.BooleanVar(value=False)
        adv_toggle = ttk.Checkbutton(
            self._tab_extract,
            text="显示高级选项",
            variable=self._adv_visible,
            command=self._toggle_advanced,
        )
        adv_toggle.pack(anchor=tk.W, pady=(0, 4))

        self._adv_frame = ttk.Frame(self._tab_extract)
        adv_inner = make_tool_group(self._adv_frame, "高级")
        adv_inner.pack(fill=tk.X)
        self.live_probe_var = tk.BooleanVar(value=self._config.live_probe)
        self.probe_drop_var = tk.BooleanVar(value=self._config.probe_drop_unreadable)
        self.fuzzy_var = tk.BooleanVar(value=self._config.fuzzy_dedupe)
        self.cross_all_var = tk.BooleanVar(value=self._config.cross_validate_require_all)
        self.stream_var = tk.BooleanVar(value=self._config.stream_single_file)
        self.android_pkg_var = tk.StringVar(value=getattr(self._config, "android_package", ""))

        adv_grid = ttk.Frame(adv_inner)
        adv_grid.pack(fill=tk.X)
        for i, (text, var) in enumerate(
            [
                ("在线探针", self.live_probe_var),
                ("剔除不可读", self.probe_drop_var),
                ("模糊去重", self.fuzzy_var),
                ("交叉需全命中", self.cross_all_var),
                ("流式读取", self.stream_var),
            ]
        ):
            ttk.Checkbutton(adv_grid, text=text, variable=var).grid(row=0, column=i, padx=(0, 12), sticky=tk.W)
        pkg_row = ttk.Frame(adv_inner)
        pkg_row.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(pkg_row, text="Android 包名").pack(side=tk.LEFT)
        ttk.Entry(pkg_row, textvariable=self.android_pkg_var, width=36).pack(side=tk.LEFT, padx=8)

        # ── 结果区 ──
        self._results_paned = ttk.Panedwindow(self._tab_extract, orient=tk.VERTICAL)
        self._results_paned.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        list_frame = make_tool_group(self._results_paned, "结果列表 · 双击复制 CE 表达式")
        detail_frame = make_tool_group(self._results_paned, "详情")
        self._results_paned.add(list_frame, weight=2)
        self._results_paned.add(detail_frame, weight=3)

        tree_wrap = ttk.Frame(list_frame)
        tree_wrap.pack(fill=tk.BOTH, expand=True)
        self.tree = ttk.Treeview(
            tree_wrap,
            columns=("score", "name", "type", "module", "base", "depth", "verified"),
            show="headings",
        )
        for col, title, w in (
            ("score", "评分", 52),
            ("name", "字段", 100),
            ("type", "类型", 56),
            ("module", "模块", 200),
            ("base", "基址", 100),
            ("depth", "层级", 44),
            ("verified", "✓", 36),
        ):
            self.tree.heading(col, text=title)
            self.tree.column(col, width=w, anchor=tk.W)
        self.tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        sb = ttk.Scrollbar(tree_wrap, command=self.tree.yview)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=sb.set)
        self.tree.bind("<Double-1>", self._on_tree_double_click)
        ttk.Button(list_frame, text="编辑选中字段", command=self._edit_selected_chain).pack(
            anchor=tk.E, pady=(6, 0)
        )

        self.detail = tk.Text(
            detail_frame,
            wrap=tk.WORD,
            font=("Cascadia Mono", 10),
            bg=THEME["surface_alt"],
            fg=THEME["text"],
            relief=tk.FLAT,
            padx=8,
            pady=8,
            highlightthickness=1,
            highlightbackground=THEME["border"],
        )
        self.detail.pack(fill=tk.BOTH, expand=True)

    def _toggle_advanced(self) -> None:
        if self._adv_visible.get():
            self._adv_frame.pack(fill=tk.X, pady=(0, 8), before=self._results_paned)
        else:
            self._adv_frame.pack_forget()

    def _show_extract_extra_params(self, show: bool) -> None:
        if not hasattr(self, "_extract_extra"):
            return
        if show:
            self._extract_extra.pack(fill=tk.X, pady=(6, 0))
        else:
            self._extract_extra.pack_forget()

    def _update_next_steps(self, result: ExtractResult) -> None:
        n = len(result.chains)
        if n == 0:
            self.next_step_var.set(
                f"输出 0 条（原始 {result.total_raw}）。可放宽最大偏移/层级，或换交叉验证。"
            )
            return
        self.next_step_var.set(
            f"已得到 {n} 条 → 建议：① 智能命名 ② 测试读取 ③ 导出全部 / ASS 交接包"
        )

    def _open_export_dir(self) -> None:
        folder = self._watch_dir() if hasattr(self, "_watch_dir") else WATCH_DIR
        if hasattr(self, "_open_dir"):
            self._open_dir(Path(folder))
        else:
            import os

            Path(folder).mkdir(parents=True, exist_ok=True)
            os.startfile(folder)  # type: ignore[attr-defined]

    def _try_sample_flow(self) -> None:
        """无 CE：生成示例 SQLite → 交叉验证 → 展示结果。"""
        import importlib.util

        root = Path(__file__).resolve().parents[3]
        script = root / "examples" / "make_sample_sqlite.py"
        if not script.is_file():
            messagebox.showerror("试跑失败", f"未找到示例脚本: {script}")
            return
        spec = importlib.util.spec_from_file_location("ce_make_sample_sqlite", script)
        if spec is None or spec.loader is None:
            messagebox.showerror("试跑失败", "无法加载示例脚本")
            return
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        ex = root / "examples"
        ex.mkdir(parents=True, exist_ok=True)
        r1, r2 = ex / "sample_r1.sqlite", ex / "sample_r2.sqlite"
        mod._write(r1, 0x12345678)
        mod._write(r2, 0x12345678)
        self.game_name_var.set("demo_sample")
        self._extra_files = [r1, r2]
        if hasattr(self, "cross_list"):
            self.cross_list.delete(0, tk.END)
            self.cross_list.insert(tk.END, str(r1))
            self.cross_list.insert(tk.END, str(r2))
        self._set_file(r1)
        self.notebook.select(self._tab_cross)
        try:
            result = extract(r1, config=self._current_config(), extra_files=[r2])
            self._populate_result(result)
            self.notebook.select(self._tab_extract)
            messagebox.showinfo(
                "试跑完成",
                f"已用 examples 示例交叉验证，得到 {len(result.chains)} 条。\n"
                "可点「智能命名 / 导出全部 / ASS 交接包」体验后续步骤。\n"
                "真实流程请用 CE 导出的 SQLite 替换示例文件。",
            )
        except Exception as exc:
            from ce_base_extractor.gui.errors import format_user_error

            messagebox.showerror("试跑失败", format_user_error("", exc, context="cross"))

    def _export_ass_handoff(self) -> None:
        if not self._result or not self._result.chains:
            messagebox.showwarning("提示", "请先提取或交叉验证得到结果")
            return
        game = self.game_name_var.get().strip() or "game"
        folder = filedialog.askdirectory(
            title="选择 ASS 交接包输出目录",
            initialdir=str(self._watch_dir() if hasattr(self, "_watch_dir") else WATCH_DIR),
        )
        if not folder:
            return
        out = Path(folder) / f"{game}_ass_handoff"
        out.mkdir(parents=True, exist_ok=True)
        snapshots, android_pkg = self._export_snapshots_context()
        files = export_all(
            self._result,
            out,
            game_name=game,
            preset_id=self.preset_var.get(),
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
            android_package=android_pkg,
            snapshots=snapshots,
        )
        readme = out / "README_ASS交接.txt"
        readme.write_text(
            "\n".join(
                [
                    f"# {game} → Auto Script Studio 交接说明",
                    "",
                    "本目录由 CE 基址提取器「ASS 交接包」生成。",
                    "",
                    "【放入 Studio 工程】",
                    "1. 打开 Auto Script Studio，打开或新建你的脚本工程",
                    "2. 将本目录中的 Lua / SCC JSON 复制到工程（如 lib/ 或根目录）",
                    "3. 在 main.lua 中按导出脚本注释调用 bot.load_bases / mem.read_chain",
                    "",
                    "【重要限制】",
                    "• 读内存需要 APK + root（PC 联调会明确报 not supported）",
                    "• 先用 Studio「打包并安装」debug 包，再热替换脚本",
                    "• 游戏更新后请重新交叉验证并导出",
                    "",
                    f"已导出文件数: {len(files)}",
                    f"游戏名: {game}",
                    f"模拟器预设: {self.preset_var.get()}",
                ]
            ),
            encoding="utf-8",
        )
        if hasattr(self, "_open_dir"):
            self._open_dir(out)
        messagebox.showinfo("ASS 交接包", f"已生成到:\n{out}\n\n请阅读 README_ASS交接.txt")
        self.status_var.set(f"ASS 交接包: {out}")

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
        label = preset.label if preset else "模拟器"
        try:
            processes = ProcessMemory.list_matching(names)
        except OSError as exc:
            messagebox.showerror("错误", str(exc))
            return
        if not processes:
            messagebox.showwarning(
                "提示",
                f"未找到「{label}」进程，请先启动模拟器，或在提取参数中切换「模拟器」预设。",
            )
            return
        picked = pick_process(self, processes)
        if picked:
            self._target_pid = picked.pid
            self.pid_label_var.set(f"进程: {picked.label}")

    def _ensure_profile_for_snapshots(self, game: str) -> bool:
        """记录读数写入 Profile；不存在时引导创建。"""
        try:
            self._profiles.load(game)
            return True
        except FileNotFoundError:
            pass
        if not self._result:
            return False
        if not messagebox.askyesno(
            "保存游戏 Profile",
            f"尚未保存游戏 Profile「{game}」。\n"
            "记录读数需要写入 Profile 才能持久化，是否现在创建并保存？",
        ):
            return False
        profile = GameProfile.from_result(
            self._result,
            game_name=game,
            preset=self.preset_var.get(),
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
            android_package=self.android_pkg_var.get().strip(),
        )
        self._profiles.save(profile)
        if hasattr(self, "_refresh_profiles"):
            self._refresh_profiles()
            self.profile_var.set(game)
        return True

    def _snapshot_values(self) -> None:
        if not self._result:
            return
        try:
            preset = get_preset(self.preset_var.get())
            names = list(preset.process_names) if preset else ["dnplayer.exe"]
            emu_label = preset.label if preset else "模拟器"
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
            self.verify_step_var.set("步骤: ① 已记录 → ② 请重启模拟器 → ③ 点「重启验证」")
            msg = (
                f"已记录 {len(self._before_verify)} 个字段\n"
                f"请重启「{emu_label}」后点「重启验证」"
            )
            if failed:
                msg += f"\n\n读取失败 {len(failed)} 个: {', '.join(failed[:8])}"
                if len(failed) > 8:
                    msg += " …"
            messagebox.showinfo("记录读数", msg)
            game = self.game_name_var.get().strip()
            if game and self._ensure_profile_for_snapshots(game):
                try:
                    profile = self._profiles.load(game)
                    profile.record_snapshots(self._before_verify)
                    self._profiles.save(profile)
                except Exception as exc:
                    messagebox.showwarning("Profile 写入", f"读数已记录到本次会话，但写入 Profile 失败: {exc}")
        except Exception as exc:
            messagebox.showerror("失败", str(exc))

    def _restart_verify(self) -> None:
        if not self._result or not self._before_verify:
            messagebox.showwarning("提示", "请先点「记录读数」，重启模拟器后再点「重启验证」")
            return
        if not messagebox.askyesno(
            "重启验证",
            "请确认已重启模拟器且游戏已重新进入目标界面。\n现在开始对比读数？",
        ):
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
        self.verify_step_var.set(
            f"步骤: 完成 — 稳定 {len(verified_names)}/{len(results)}；可再「记录读数」开始下一轮"
        )
        messagebox.showinfo("重启验证", "\n".join(lines[:15]))

    def _export_snapshots_context(self) -> tuple[dict[str, dict] | None, str]:
        game = self.game_name_var.get().strip() or "game"
        return load_export_context(
            game,
            session_values=self._before_verify or None,
            android_fallback=self.android_pkg_var.get().strip(),
        )

    def _export_scc(self) -> None:
        if not self._result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=f"{self.game_name_var.get()}_bases_scc.json",
        )
        if path:
            snapshots, android_pkg = self._export_snapshots_context()
            save_scc_json(
                self._result,
                path,
                preset_id=self.preset_var.get(),
                snapshots=snapshots,
                android_package=android_pkg,
            )
            self.status_var.set(f"已导出 SCC: {path}")

    def _export_lua(self) -> None:
        if not self._result:
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".lua",
            initialfile=f"{self.game_name_var.get()}_reader.lua",
        )
        if path:
            save_lua_script(
                self._result,
                path,
                game_name=self.game_name_var.get().strip() or "game",
            )
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
        folder = filedialog.askdirectory(initialdir=str(self._watch_dir() if hasattr(self, "_watch_dir") else WATCH_DIR))
        if not folder:
            return
        game = self.game_name_var.get().strip() or "game"
        snapshots, android_pkg = self._export_snapshots_context()
        files = export_all(
            self._result,
            folder,
            game_name=game,
            preset_id=self.preset_var.get(),
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
            android_package=android_pkg,
            snapshots=snapshots,
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
