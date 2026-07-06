from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *


class AuxMixin:
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
