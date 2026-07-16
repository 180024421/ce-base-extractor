from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *
from ce_base_extractor.gui.theme import FONTS, THEME, make_tool_group


def _styled_text(parent, **kwargs) -> tk.Text:
    return tk.Text(
        parent,
        font=FONTS["mono"],
        bg=THEME["surface_alt"],
        fg=THEME["text"],
        relief=tk.FLAT,
        padx=8,
        pady=8,
        highlightthickness=1,
        highlightbackground=THEME["border"],
        **kwargs,
    )


class AuxMixin:
    def _build_modules_tab(self) -> None:
        ttk.Label(
            self._tab_modules,
            text="勾选模块作为白名单（不勾选 = 不过滤）。提取后自动刷新统计。",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(0, 8))

        paned = ttk.Panedwindow(self._tab_modules, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        mod_grp = make_tool_group(paned, "模块白名单")
        stat_grp = make_tool_group(paned, "模块统计")
        paned.add(mod_grp, weight=1)
        paned.add(stat_grp, weight=1)

        mf = ttk.Frame(mod_grp)
        mf.pack(fill=tk.BOTH, expand=True)

        self.module_canvas = tk.Canvas(
            mf, highlightthickness=0, bg=THEME["surface"], bd=0
        )
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

        self.stats_tree = ttk.Treeview(
            stat_grp,
            columns=("module", "count", "tier", "avg_depth"),
            show="headings",
            height=14,
        )
        for col, title, w in (
            ("module", "模块", 200),
            ("count", "数量", 72),
            ("tier", "优先级", 72),
            ("avg_depth", "均层级", 72),
        ):
            self.stats_tree.heading(col, text=title)
            self.stats_tree.column(col, width=w, anchor=tk.W)
        self.stats_tree.pack(fill=tk.BOTH, expand=True)

    def _build_monitor_tab(self) -> None:
        row = ttk.Frame(self._tab_monitor)
        row.pack(fill=tk.X, pady=(0, 10))
        ttk.Label(row, text="刷新间隔 (秒)").pack(side=tk.LEFT)
        self.monitor_interval_var = tk.IntVar(value=2)
        ttk.Spinbox(row, from_=1, to=60, textvariable=self.monitor_interval_var, width=6).pack(
            side=tk.LEFT, padx=8
        )
        self.monitor_btn = ttk.Button(
            row, text="开始监控", style="Accent.TButton", command=self._toggle_monitor
        )
        self.monitor_btn.pack(side=tk.LEFT)
        ttk.Button(row, text="送特征码采样", command=self._monitor_send_to_sig).pack(
            side=tk.LEFT, padx=(12, 0)
        )

        mon_grp = make_tool_group(self._tab_monitor, "实时读数")
        mon_grp.pack(fill=tk.BOTH, expand=True)

        self.monitor_tree = ttk.Treeview(
            mon_grp,
            columns=("name", "value", "type", "updated"),
            show="headings",
            height=16,
        )
        for col, title, w in (
            ("name", "字段", 130),
            ("value", "当前值", 180),
            ("type", "类型", 72),
            ("updated", "时间", 90),
        ):
            self.monitor_tree.heading(col, text=title)
            self.monitor_tree.column(col, width=w, anchor=tk.W)
        self.monitor_tree.tag_configure("changed", foreground=THEME["danger"])
        self.monitor_tree.tag_configure("same", foreground=THEME["success"])
        self.monitor_tree.pack(fill=tk.BOTH, expand=True)

    def _build_profile_tab(self) -> None:
        row = ttk.Frame(self._tab_profile)
        row.pack(fill=tk.X, pady=(0, 10))
        for text, cmd in (
            ("保存配置", self._save_profile),
            ("加载", self._load_profile),
            ("复检", self._profile_recheck),
            ("版本对比", self._profile_migrate),
            ("删除", self._delete_profile),
            ("刷新", self._refresh_profiles),
        ):
            ttk.Button(row, text=text, command=cmd).pack(side=tk.LEFT, padx=(0, 6))

        self.profile_var = tk.StringVar()
        pick_row = ttk.Frame(self._tab_profile)
        pick_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(pick_row, text="游戏配置").pack(side=tk.LEFT)
        self.profile_combo = ttk.Combobox(
            pick_row, textvariable=self.profile_var, state="readonly", width=32
        )
        self.profile_combo.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)

        info_grp = make_tool_group(self._tab_profile, "配置详情")
        info_grp.pack(fill=tk.BOTH, expand=True)
        self.profile_info = _styled_text(info_grp, height=14)
        self.profile_info.pack(fill=tk.BOTH, expand=True)
        self._refresh_profiles()

    def _build_history_tab(self) -> None:
        row = ttk.Frame(self._tab_history)
        row.pack(fill=tk.X, pady=(0, 10))
        ttk.Button(row, text="保存到收藏", style="Primary.TButton", command=self._save_favorites).pack(
            side=tk.LEFT, padx=(0, 6)
        )
        ttk.Button(row, text="刷新", command=self._refresh_history).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(row, text="导出 Python", command=self._export_history_python).pack(side=tk.LEFT)

        self.history_game_var = tk.StringVar()
        pick_row = ttk.Frame(self._tab_history)
        pick_row.pack(fill=tk.X, pady=(0, 8))
        ttk.Label(pick_row, text="游戏").pack(side=tk.LEFT)
        self.history_combo = ttk.Combobox(
            pick_row, textvariable=self.history_game_var, state="readonly", width=32
        )
        self.history_combo.pack(side=tk.LEFT, padx=8, fill=tk.X, expand=True)
        self.history_combo.bind("<<ComboboxSelected>>", lambda _e: self._show_history_game())

        hist_grp = make_tool_group(self._tab_history, "收藏链")
        hist_grp.pack(fill=tk.BOTH, expand=True)
        self.history_text = _styled_text(hist_grp, height=16)
        self.history_text.pack(fill=tk.BOTH, expand=True)
        self._refresh_history()

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
        self._monitor_errors = 0
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
            elif self._target_pid and self._monitor_mem.pid != self._target_pid:
                self._monitor_mem.close()
                self._monitor_mem = ProcessMemory.auto_attach(names, pid=self._target_pid)
            mem = self._monitor_mem
            ps = int(self.pointer_size_var.get())
            now = datetime.now().strftime("%H:%M:%S")
            tick_errors = 0
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
                    tick_errors += 1
                    self.monitor_tree.insert(
                        "", tk.END, values=(name, f"ERR: {exc}", chain.value_type, now)
                    )
            if tick_errors:
                self._monitor_errors += 1
                mem.invalidate_module_cache()
                if self._monitor_errors >= 2:
                    mem.close()
                    self._monitor_mem = None
                    self._monitor_errors = 0
            else:
                self._monitor_errors = 0
        except Exception as exc:
            self.status_var.set(f"监控错误: {exc}")
            if self._monitor_mem:
                self._monitor_mem.invalidate_module_cache()
                self._monitor_mem.close()
                self._monitor_mem = None
            self._monitor_errors = 0

        interval = max(1, int(self.monitor_interval_var.get())) * 1000
        self._monitor_job = self.after(interval, self._monitor_tick)

    def _monitor_send_to_sig(self) -> None:
        """将监控选中字段解析为地址，送到特征码页采集样本。"""
        if not self._result or not self._result.chains:
            messagebox.showwarning("提示", "请先提取结果")
            return
        sel = self.monitor_tree.selection()
        if not sel:
            messagebox.showwarning("提示", "请在监控列表中选中一个字段")
            return
        name = self.monitor_tree.item(sel[0], "values")[0]
        chain = next(
            (c for i, c in enumerate(self._result.chains, 1) if c.export_name(i) == name),
            None,
        )
        if chain is None:
            messagebox.showerror("错误", f"找不到链: {name}")
            return
        try:
            names = list(get_preset(self.preset_var.get()).process_names) if get_preset(self.preset_var.get()) else ["dnplayer.exe"]
            mem = ProcessMemory.auto_attach(names, pid=self._target_pid)
            addr = mem.resolve_chain(
                chain.module_name,
                chain.module_offset,
                chain.offsets,
                int(self.pointer_size_var.get()),
            )
            mem.close()
        except Exception as exc:
            messagebox.showerror("解析地址失败", str(exc))
            return
        if hasattr(self, "_sig_capture_at"):
            self.notebook.select(self._tab_signature)
            self.sig_field_var.set(name)
            self.sig_type_var.set(chain.value_type or "int32")
            self._sig_capture_at(addr, note=f"from:{name}")
        else:
            messagebox.showinfo("地址", f"{name} @ 0x{addr:X}")

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
