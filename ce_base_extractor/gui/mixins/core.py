from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.gui.app_imports import *


class CoreMixin:
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
            watch_dir=str(self._watch_dir()),
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
        if hasattr(self, "_file_card"):
            self._file_card.set_active(True)
        try:
            ids = list_ptrids(path) if path.suffix.lower() in (".sqlite", ".db", ".sqlite3") else []
            if ids:
                self.ptrid_var.set(str(ids[-1]))
        except Exception as exc:
            self.status_var.set(f"已选择: {path.name}（读取 ptrid 失败: {exc}）")
            return
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
        if hasattr(self, "_update_next_steps"):
            self._update_next_steps(result)
        if not result.chains:
            from ce_base_extractor.gui.errors import empty_result_tip

            messagebox.showwarning(
                "无输出结果",
                empty_result_tip(had_raw=result.total_raw > 0),
            )

    def _extract_async(self, fn, title: str, *, use_progress: bool = False) -> None:
        self._extract_busy = True
        self.status_var.set(title)
        win = tk.Toplevel(self)
        win.title(title)
        win.geometry("360x110")
        win.transient(self)
        ttk.Label(win, text=title).pack(pady=(12, 4))
        prog_label = ttk.Label(win, text="准备中…")
        prog_label.pack()
        # 行数未知时用 indeterminate；有回调时仍用脉冲条 + 行数文案，避免假进度卡住
        bar = ttk.Progressbar(win, mode="indeterminate")
        bar.pack(fill=tk.X, padx=16, pady=4)
        bar.start(12)

        def work() -> None:
            try:
                if use_progress:

                    def on_progress(n: int) -> None:
                        self.after(
                            0,
                            lambda n=n: prog_label.config(text=f"已扫描 {n:,} 行（处理中…）"),
                        )

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
        from ce_base_extractor.gui.errors import format_user_error

        win.destroy()
        self._extract_busy = False
        messagebox.showerror("提取失败", format_user_error("", exc))

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
