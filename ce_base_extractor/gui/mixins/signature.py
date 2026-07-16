from __future__ import annotations

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from ce_base_extractor.export.scc_export import save_scc_json
from ce_base_extractor.export.signature_export import (
    save_ass_fields,
    save_lua_signatures,
    save_python_with_signatures,
)
from ce_base_extractor.gui.app_imports import *
from ce_base_extractor.gui.theme import FONTS, THEME, make_tool_group
from ce_base_extractor.models import ExtractResult
from ce_base_extractor.profiles.store import GameProfile
from ce_base_extractor.runtime.win_memory import read_chain_value
from ce_base_extractor.signature import (
    GeneratedSignature,
    SavedSignature,
    SignatureSample,
    generate_from_samples,
    load_samples,
    minimize_unique_pattern,
    parse_address,
    save_samples,
)
from ce_base_extractor.signature.history import (
    append_history,
    list_history,
    load_history_entry,
    pattern_hash,
)
from ce_base_extractor.signature.scanner import (
    count_pattern_hits,
    list_modules_detailed,
    scan_process,
)


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


class SignatureMixin:
    def _build_signature_tab(self) -> None:
        self._sig_samples: list[SignatureSample] = []
        self._sig_last: GeneratedSignature | None = None
        self._sig_last_pattern = ""
        self._sig_last_offset: int | None = None
        self._sig_hits: list[int] = []
        self._sig_scan_cancel = False
        self._sig_busy = False

        ttk.Label(
            self._tab_signature,
            text="① 采 ≥3 样本（重启同址 或 同局多址） ② 生成/精简 ③ 扫描验证 ④ 写入配置/导出。可粘贴多行地址一次采集。",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, pady=(0, 4))
        self._sig_show_guide_once()

        top = ttk.Frame(self._tab_signature)
        top.pack(fill=tk.X, pady=(0, 6))

        ttk.Button(top, text="选进程", command=self._pick_process).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Label(top, text="地址").pack(side=tk.LEFT)
        self.sig_addr_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.sig_addr_var, width=18).pack(side=tk.LEFT, padx=(4, 8))

        ttk.Label(top, text="备注").pack(side=tk.LEFT)
        self.sig_note_var = tk.StringVar()
        ttk.Entry(top, textvariable=self.sig_note_var, width=12).pack(side=tk.LEFT, padx=(4, 8))

        ttk.Label(top, text="前").pack(side=tk.LEFT)
        self.sig_before_var = tk.IntVar(value=32)
        ttk.Spinbox(top, from_=4, to=128, textvariable=self.sig_before_var, width=4).pack(
            side=tk.LEFT, padx=(2, 6)
        )
        ttk.Label(top, text="后").pack(side=tk.LEFT)
        self.sig_after_var = tk.IntVar(value=32)
        ttk.Spinbox(top, from_=4, to=128, textvariable=self.sig_after_var, width=4).pack(
            side=tk.LEFT, padx=(2, 8)
        )

        ttk.Button(top, text="采集样本", style="Primary.TButton", command=self._sig_capture).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(top, text="粘贴多址", command=self._sig_paste_addrs).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="删除", command=self._sig_remove).pack(side=tk.LEFT, padx=2)
        ttk.Button(top, text="清空", command=self._sig_clear).pack(side=tk.LEFT, padx=2)

        row2 = ttk.Frame(self._tab_signature)
        row2.pack(fill=tk.X, pady=(0, 6))
        ttk.Label(row2, text="字段名").pack(side=tk.LEFT)
        self.sig_field_var = tk.StringVar(value="field")
        ttk.Entry(row2, textvariable=self.sig_field_var, width=12).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(row2, text="类型").pack(side=tk.LEFT)
        self.sig_type_var = tk.StringVar(value="int32")
        ttk.Combobox(
            row2,
            textvariable=self.sig_type_var,
            values=("int32", "uint32", "int64", "uint64", "float", "double"),
            width=8,
            state="readonly",
        ).pack(side=tk.LEFT, padx=(4, 8))
        ttk.Label(row2, text="扫模块").pack(side=tk.LEFT)
        self.sig_module_var = tk.StringVar()
        self.sig_module_combo = ttk.Combobox(row2, textvariable=self.sig_module_var, width=18)
        self.sig_module_combo.pack(side=tk.LEFT, padx=(4, 4))
        ttk.Button(row2, text="刷新模块", command=self._sig_refresh_modules).pack(side=tk.LEFT, padx=2)
        ttk.Label(row2, text="范围").pack(side=tk.LEFT, padx=(8, 0))
        self.sig_region_mode_var = tk.StringVar(value="modules")
        ttk.Combobox(
            row2,
            textvariable=self.sig_region_mode_var,
            values=("modules", "heap", "all"),
            width=9,
            state="readonly",
        ).pack(side=tk.LEFT, padx=4)
        self.sig_stop_unique_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row2, text="唯一即停", variable=self.sig_stop_unique_var).pack(side=tk.LEFT, padx=4)

        row3 = ttk.Frame(self._tab_signature)
        row3.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(row3, text="导入样本", command=self._sig_import_samples).pack(side=tk.LEFT, padx=(0, 2))
        ttk.Button(row3, text="导出样本", command=self._sig_export_samples).pack(side=tk.LEFT, padx=2)
        ttk.Button(row3, text="历史", command=self._sig_show_history).pack(side=tk.LEFT, padx=2)
        ttk.Button(row3, text="对照链读数", command=self._sig_compare_chain).pack(side=tk.LEFT, padx=(12, 2))

        list_grp = make_tool_group(self._tab_signature, "样本列表（同局多地址 或 重启多样本均可）")
        list_grp.pack(fill=tk.X, pady=(0, 6))
        cols = ("idx", "note", "address", "window", "preview")
        self.sig_tree = ttk.Treeview(list_grp, columns=cols, show="headings", height=5)
        for col, title, w in (
            ("idx", "#", 36),
            ("note", "备注", 100),
            ("address", "地址", 120),
            ("window", "窗口", 80),
            ("preview", "预览", 360),
        ):
            self.sig_tree.heading(col, text=title)
            self.sig_tree.column(col, width=w, anchor=tk.W)
        self.sig_tree.pack(fill=tk.X, padx=4, pady=4)

        act = ttk.Frame(self._tab_signature)
        act.pack(fill=tk.X, pady=(0, 4))
        ttk.Button(act, text="生成特征码", style="Primary.TButton", command=self._sig_generate).pack(
            side=tk.LEFT, padx=(0, 4)
        )
        ttk.Button(act, text="精简唯一", command=self._sig_minimize).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="扫描验证", command=self._sig_scan).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="读值验证", command=self._sig_read_value).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="复制", command=self._sig_copy).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="写入配置", command=self._sig_save_profile).pack(side=tk.LEFT, padx=(12, 2))
        ttk.Button(act, text="导出向导", command=self._sig_export_wizard).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="导出脚本", command=self._sig_export_all).pack(side=tk.LEFT, padx=2)

        prog = ttk.Frame(self._tab_signature)
        prog.pack(fill=tk.X, pady=(0, 4))
        self.sig_progress = ttk.Progressbar(prog, mode="determinate", maximum=100)
        self.sig_progress.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.sig_progress_label = tk.StringVar(value="")
        ttk.Label(prog, textvariable=self.sig_progress_label, width=18).pack(side=tk.LEFT, padx=6)

        out_grp = make_tool_group(self._tab_signature, "结果")
        out_grp.pack(fill=tk.BOTH, expand=True)
        self.sig_out = _styled_text(out_grp, height=12, wrap=tk.WORD)
        self.sig_out.pack(fill=tk.BOTH, expand=True, padx=4, pady=4)

    def _sig_process_names(self) -> list[str]:
        preset = get_preset(self.preset_var.get())
        return list(preset.process_names) if preset else ["dnplayer.exe"]

    def _sig_attach(self):
        names = self._sig_process_names()
        mem = ProcessMemory.auto_attach(names, pid=self._target_pid)
        self._target_pid = mem.pid
        return mem

    def _sig_refresh_tree(self) -> None:
        self.sig_tree.delete(*self.sig_tree.get_children())
        for i, s in enumerate(self._sig_samples, start=1):
            preview = " ".join(f"{b:02X}" for b in s.data[:12])
            if len(s.data) > 12:
                preview += " …"
            self.sig_tree.insert(
                "",
                tk.END,
                values=(i, s.note or "-", f"0x{s.address:X}", f"-{s.before}/+{s.after}", preview),
            )

    def _sig_refresh_modules(self) -> None:
        try:
            mem = self._sig_attach()
            mods = list_modules_detailed(mem)
            mem.close()
        except Exception as exc:
            messagebox.showerror("模块列表失败", str(exc))
            return
        names = [""] + sorted({m.name for m in mods}, key=str.lower)
        self.sig_module_combo["values"] = names
        self.status_var.set(f"模块 {len(names) - 1} 个")

    def _sig_capture(self, *, silent: bool = False) -> None:
        try:
            addr = parse_address(self.sig_addr_var.get())
            before = int(self.sig_before_var.get())
            after = int(self.sig_after_var.get())
        except Exception as exc:
            if not silent:
                messagebox.showerror("地址无效", str(exc))
            return
        if before < 1 or after < 1:
            if not silent:
                messagebox.showerror("窗口无效", "前后窗口至少各为 1")
            return
        if self._sig_samples:
            first = self._sig_samples[0]
            if first.before != before or first.after != after:
                if silent:
                    return
                if not messagebox.askyesno("窗口不一致", "清空旧样本并按新窗口采集？"):
                    return
                self._sig_samples.clear()
        try:
            mem = self._sig_attach()
            data = mem.read_bytes(addr - before, before + after)
            mem.close()
        except Exception as exc:
            if not silent:
                messagebox.showerror("采集失败", str(exc))
            return
        note = self.sig_note_var.get().strip() or f"sample{len(self._sig_samples) + 1}"
        self._sig_samples.append(
            SignatureSample(address=addr, data=data, before=before, after=after, note=note)
        )
        self._sig_refresh_tree()
        n = len(self._sig_samples)
        self.status_var.set(f"样本 {n} 条（需 ≥3）")
        if n < 3 and not silent:
            messagebox.showinfo(
                "继续采集",
                f"已采集 {n} 条。\n可：① 重启后采同址 ② 同局再找 1～2 个同类地址一并采集。",
            )

    def _sig_remove(self) -> None:
        sel = self.sig_tree.selection()
        if not sel:
            return
        for idx in sorted((self.sig_tree.index(i) for i in sel), reverse=True):
            if 0 <= idx < len(self._sig_samples):
                del self._sig_samples[idx]
        self._sig_refresh_tree()

    def _sig_clear(self) -> None:
        self._sig_samples.clear()
        self._sig_last = None
        self._sig_last_pattern = ""
        self._sig_last_offset = None
        self._sig_hits = []
        self._sig_refresh_tree()
        self.sig_out.delete("1.0", tk.END)

    def _sig_show_gen(self, gen: GeneratedSignature) -> None:
        self._sig_last = gen
        self._sig_last_pattern = gen.pattern
        self._sig_last_offset = gen.offset_to_target
        lines = [
            f"字段: {self.sig_field_var.get().strip() or 'field'}",
            f"特征码: {gen.pattern}",
            f"样本数: {gen.sample_count}  固定: {gen.fixed_bytes}  通配: {gen.wildcard_bytes}",
            f"窗口: -{gen.window_before}/+{gen.window_after}  精简: {gen.minimized}",
            f"目标偏移: 命中地址 + ({gen.offset_to_target}) = 目标",
        ]
        if gen.warnings:
            lines.append("警告:")
            lines.extend(f"  - {w}" for w in gen.warnings)
        self.sig_out.delete("1.0", tk.END)
        self.sig_out.insert(tk.END, "\n".join(lines))

    def _sig_generate(self) -> None:
        try:
            gen = generate_from_samples(self._sig_samples, min_samples=3)
        except Exception as exc:
            messagebox.showerror("生成失败", str(exc))
            return
        self._sig_show_gen(gen)
        try:
            append_history(
                game=self.game_name_var.get().strip() or "game",
                field_name=self.sig_field_var.get().strip() or "field",
                gen=gen,
                value_type=self.sig_type_var.get(),
                module_hint=self.sig_module_var.get().strip(),
            )
        except Exception:
            pass
        self.status_var.set(f"已生成特征码（固定 {gen.fixed_bytes}）")

    def _sig_minimize(self) -> None:
        if not self._sig_last:
            messagebox.showwarning("提示", "请先生成特征码")
            return
        module = self.sig_module_var.get().strip() or None

        def work():
            try:
                mem = self._sig_attach()

                def count_fn(pat: str) -> int:
                    return count_pattern_hits(
                        mem,
                        pat,
                        max_hits=8,
                        module_filter=module,
                        region_mode=getattr(self, "sig_region_mode_var", tk.StringVar(value="all")).get(),
                    )

                gen = minimize_unique_pattern(self._sig_last, count_fn, max_hits=1)
                mem.close()
                self.after(0, lambda: self._sig_show_gen(gen))
                self.after(0, lambda: self.status_var.set("精简完成" if gen.minimized else "无法再精简"))
            except Exception as exc:
                self.after(0, lambda e=exc: messagebox.showerror("精简失败", str(e)))

        threading.Thread(target=work, daemon=True).start()
        self.status_var.set("正在精简（后台扫描）…")

    def _sig_scan(self) -> None:
        pattern = self._sig_last_pattern.strip()
        if not pattern:
            messagebox.showwarning("无特征码", "请先生成特征码")
            return
        if self._sig_busy:
            self._sig_scan_cancel = True
            return
        self._sig_busy = True
        self._sig_scan_cancel = False
        module = self.sig_module_var.get().strip() or None
        region_mode = self.sig_region_mode_var.get() if hasattr(self, "sig_region_mode_var") else "all"
        stop_unique = bool(self.sig_stop_unique_var.get()) if hasattr(self, "sig_stop_unique_var") else False
        self.sig_progress["value"] = 0
        self.sig_progress_label.set("扫描中…")

        def progress(p: float, label: str) -> None:
            self.after(0, lambda: self._sig_set_progress(p, label))

        def work():
            try:
                mem = self._sig_attach()
                hits = scan_process(
                    mem,
                    pattern,
                    max_hits=32,
                    module_filter=module,
                    region_mode=region_mode,
                    stop_when_unique=stop_unique,
                    progress=progress,
                    cancel=lambda: self._sig_scan_cancel,
                )
                mem.close()
                self.after(0, lambda: self._sig_on_scan_done(hits))
            except Exception as exc:
                self.after(0, lambda e=exc: self._sig_on_scan_fail(str(e)))

        threading.Thread(target=work, daemon=True).start()

    def _sig_set_progress(self, p: float, label: str) -> None:
        self.sig_progress["value"] = int(p * 100)
        self.sig_progress_label.set(label[:18])

    def _sig_on_scan_fail(self, msg: str) -> None:
        self._sig_busy = False
        self.sig_progress_label.set("失败")
        messagebox.showerror("扫描失败", msg)

    def _sig_on_scan_done(self, hits: list[int]) -> None:
        self._sig_busy = False
        self._sig_hits = hits
        self.sig_progress["value"] = 100
        self.sig_progress_label.set(f"命中 {len(hits)}")
        extra = ["", f"扫描命中: {len(hits)}"]
        off = self._sig_last_offset
        for h in hits[:20]:
            hint = f"  → 目标 0x{h + off:X}" if off is not None else ""
            extra.append(f"  0x{h:X}{hint}")
        if len(hits) > 20:
            extra.append(f"  … 另有 {len(hits) - 20} 条")
        if len(hits) == 1:
            extra.append("唯一命中，可用。")
        elif len(hits) == 0:
            extra.append("未命中：检查模块/范围，或游戏已更新需重采特征码（版本漂移）。")
            # Profile 漂移提醒
            try:
                game = self.game_name_var.get().strip() or "game"
                profile = self._profiles.load(game)
                name = self.sig_field_var.get().strip()
                for d in profile.signatures:
                    if d.get("field_name") == name and d.get("pattern_hash"):
                        ph = pattern_hash(pattern)
                        if d.get("pattern_hash") != ph:
                            extra.append(
                                f"警告: Profile 中 {name} 的 pattern_hash={d.get('pattern_hash')} "
                                f"与当前 {ph} 不一致。"
                            )
                        else:
                            extra.append(
                                f"警告: Profile 中已保存的特征码（hash={d.get('pattern_hash')}）"
                                "当前 0 命中，疑似热更/版本漂移，请重新采集。"
                            )
                        break
            except Exception:
                pass
        else:
            extra.append("命中偏多：可「精简唯一」或限制扫模块/改范围。")
        cur = self.sig_out.get("1.0", tk.END).rstrip()
        self.sig_out.delete("1.0", tk.END)
        self.sig_out.insert(tk.END, cur + "\n" + "\n".join(extra))
        self.status_var.set(f"特征码命中 {len(hits)}")

    def _sig_read_value(self) -> None:
        if not self._sig_hits:
            messagebox.showwarning("提示", "请先扫描验证并至少命中 1 处")
            return
        if self._sig_last_offset is None:
            return
        vtype = self.sig_type_var.get()
        hit = self._sig_hits[0]
        addr = hit + self._sig_last_offset
        try:
            mem = self._sig_attach()
            readers = {
                "int32": mem.read_i32,
                "uint32": mem.read_u32,
                "int64": mem.read_i64,
                "uint64": mem.read_u64,
                "float": mem.read_f32,
                "double": mem.read_f64,
            }
            fn = readers.get(vtype, mem.read_i32)
            val = fn(addr)
            mem.close()
        except Exception as exc:
            messagebox.showerror("读值失败", str(exc))
            return
        line = f"\n读值验证 @ 0x{addr:X} ({vtype}) = {val}"
        self.sig_out.insert(tk.END, line)
        self.status_var.set(f"读值 {val}")

    def _sig_copy(self) -> None:
        text = self._sig_last_pattern.strip()
        if not text:
            messagebox.showwarning("无特征码", "请先生成")
            return
        self.clipboard_clear()
        self.clipboard_append(text)
        self.status_var.set("已复制特征码")

    def _sig_as_saved(self) -> SavedSignature:
        if not self._sig_last:
            raise ValueError("请先生成特征码")
        name = self.sig_field_var.get().strip() or "field"
        return SavedSignature(
            field_name=name,
            pattern=self._sig_last.pattern,
            offset_to_target=self._sig_last.offset_to_target,
            value_type=self.sig_type_var.get(),
            module_hint=self.sig_module_var.get().strip(),
            verified=len(self._sig_hits) == 1,
            sample_count=self._sig_last.sample_count,
            fixed_bytes=self._sig_last.fixed_bytes,
        )

    def _sig_save_profile(self) -> None:
        try:
            saved = self._sig_as_saved()
        except Exception as exc:
            messagebox.showerror("无法保存", str(exc))
            return
        game = self.game_name_var.get().strip() or "game"
        try:
            profile = self._profiles.load(game)
        except FileNotFoundError:
            result = self._result or ExtractResult(
                chains=[], total_raw=0, total_after_filter=0, modules_seen=[], source_file="signature"
            )
            profile = GameProfile.from_result(
                result,
                game_name=game,
                preset=self.preset_var.get(),
                pointer_size=int(self.pointer_size_var.get()),
                target_pid=self._target_pid,
                android_package=getattr(self, "android_pkg_var", tk.StringVar()).get()
                if hasattr(self, "android_pkg_var")
                else "",
            )
        # upsert by field name
        sigs = [s for s in profile.signatures if s.get("field_name") != saved.field_name]
        sigs.append(saved.to_dict())
        profile.signatures = sigs
        profile.target_pid = self._target_pid
        path = self._profiles.save(profile)
        messagebox.showinfo("已写入配置", f"{saved.field_name} → {path}")
        self.status_var.set(f"特征码已写入 Profile: {game}")

    def _sig_export_all(self) -> None:
        try:
            saved = self._sig_as_saved()
        except Exception as exc:
            messagebox.showerror("无法导出", str(exc))
            return
        game = self.game_name_var.get().strip() or "game"
        out_dir = filedialog.askdirectory(title="选择导出目录")
        if not out_dir:
            return
        out = Path(out_dir)
        result = self._result or ExtractResult(
            chains=[], total_raw=0, total_after_filter=0, modules_seen=[], source_file="signature"
        )
        # merge profile signatures if any
        sigs = [saved]
        try:
            profile = self._profiles.load(game)
            for d in profile.signatures:
                s = SavedSignature.from_dict(d)
                if s.field_name != saved.field_name:
                    sigs.append(s)
        except FileNotFoundError:
            pass
        pkg = ""
        if hasattr(self, "android_pkg_var"):
            pkg = self.android_pkg_var.get().strip()
        py = save_python_with_signatures(
            result,
            sigs,
            out / f"{game}_reader.py",
            preset_id=self.preset_var.get(),
            game_name=game,
            pointer_size=int(self.pointer_size_var.get()),
            target_pid=self._target_pid,
        )
        lua = save_lua_signatures(sigs, out / f"{game}_aob.lua", game_name=game)
        ass = save_ass_fields(
            result,
            sigs,
            out / f"{game}_ass_fields.json",
            android_package=pkg,
            game_name=game,
            pointer_size=int(self.pointer_size_var.get()),
        )
        messagebox.showinfo("导出完成", f"{py.name}\n{lua.name}\n{ass.name}")
        self.status_var.set(f"已导出到 {out}")

    def _sig_export_samples(self) -> None:
        if not self._sig_samples:
            messagebox.showwarning("提示", "无样本可导出")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="sig_samples.json",
        )
        if not path:
            return
        save_samples(self._sig_samples, path)
        self.status_var.set(f"样本已导出: {path}")

    def _sig_import_samples(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("JSON", "*.json"), ("所有", "*.*")])
        if not path:
            return
        try:
            samples = load_samples(path)
        except Exception as exc:
            messagebox.showerror("导入失败", str(exc))
            return
        self._sig_samples = samples
        self._sig_refresh_tree()
        self.status_var.set(f"已导入样本 {len(samples)} 条")

    def _sig_show_guide_once(self) -> None:
        flag = Path.home() / "Documents" / "ce-exports" / ".sig_guide_done"
        if flag.is_file():
            return
        self.after(
            400,
            lambda: messagebox.showinfo(
                "特征码三步",
                "1. 选进程，填地址点「采集样本」（≥3：可重启重采，或同局多个同类地址）\n"
                "2. 「生成特征码」→ 可选「精简唯一」→「扫描验证」\n"
                "3. 「写入配置」或「导出向导」给 Python / ASS 使用\n\n"
                "也可从「监控」页把读成功的链地址送到本页采样。",
            ),
        )
        try:
            flag.parent.mkdir(parents=True, exist_ok=True)
            flag.write_text("1", encoding="utf-8")
        except OSError:
            pass

    def _sig_paste_addrs(self) -> None:
        win = tk.Toplevel(self)
        win.title("粘贴多行地址")
        win.geometry("420x280")
        ttk.Label(win, text="每行一个地址（0x... 或十进制），将按当前窗口逐个采集：").pack(
            anchor=tk.W, padx=12, pady=8
        )
        text = tk.Text(win, height=10, font=FONTS["mono"])
        text.pack(fill=tk.BOTH, expand=True, padx=12)
        try:
            clip = self.clipboard_get()
            if clip:
                text.insert("1.0", clip)
        except tk.TclError:
            pass

        def do_ok() -> None:
            lines = [ln.strip() for ln in text.get("1.0", tk.END).splitlines() if ln.strip()]
            win.destroy()
            if not lines:
                return
            ok_n = 0
            for i, line in enumerate(lines, 1):
                try:
                    self.sig_addr_var.set(line.split()[0])
                    self.sig_note_var.set(f"paste{i}")
                    self._sig_capture(silent=True)
                    ok_n += 1
                except Exception:
                    continue
            n = len(self._sig_samples)
            self.status_var.set(f"粘贴采集完成 {ok_n}/{len(lines)}（样本共 {n}）")
            if n >= 3:
                messagebox.showinfo("粘贴完成", f"已采集 {ok_n} 个地址，样本共 {n} 条，可生成特征码。")
            elif ok_n:
                messagebox.showinfo("粘贴完成", f"已采集 {ok_n} 个，样本共 {n} 条（还需 ≥3）。")

        ttk.Button(win, text="采集", style="Primary.TButton", command=do_ok).pack(pady=8)

    def _sig_capture_at(self, addr: int, note: str = "") -> None:
        """供监控页调用：按当前窗口采集指定地址。"""
        self.sig_addr_var.set(f"0x{addr:X}")
        if note:
            self.sig_note_var.set(note)
        self._sig_capture(silent=True)

    def _sig_compare_chain(self) -> None:
        if not self._sig_hits or self._sig_last_offset is None:
            messagebox.showwarning("提示", "请先扫描验证并命中")
            return
        if not self._result or not self._result.chains:
            messagebox.showwarning("提示", "当前无指针链结果可对照")
            return
        name = self.sig_field_var.get().strip()
        chain = next((c for i, c in enumerate(self._result.chains, 1) if c.export_name(i) == name), None)
        if chain is None:
            messagebox.showwarning("提示", f"未找到同名字段链: {name}")
            return
        try:
            mem = self._sig_attach()
            chain_val = read_chain_value(mem, chain, int(self.pointer_size_var.get()))
            aob_addr = self._sig_hits[0] + self._sig_last_offset
            readers = {
                "int32": mem.read_i32,
                "uint32": mem.read_u32,
                "int64": mem.read_i64,
                "uint64": mem.read_u64,
                "float": mem.read_f32,
                "double": mem.read_f64,
            }
            aob_val = readers.get(self.sig_type_var.get(), mem.read_i32)(aob_addr)
            mem.close()
        except Exception as exc:
            messagebox.showerror("对照失败", str(exc))
            return
        same = chain_val == aob_val
        line = (
            f"\n对照 {name}: chain={chain_val}  aob@0x{aob_addr:X}={aob_val}  "
            f"{'一致' if same else '不一致（可能显示拷贝/类型不同）'}"
        )
        self.sig_out.insert(tk.END, line)
        self.status_var.set("对照完成")

    def _sig_show_history(self) -> None:
        items = list_history(40)
        if not items:
            messagebox.showinfo("历史", "暂无特征码历史")
            return
        win = tk.Toplevel(self)
        win.title("特征码历史")
        win.geometry("640x360")
        tree = ttk.Treeview(win, columns=("time", "game", "field", "pattern"), show="headings", height=12)
        for col, title, w in (
            ("time", "时间", 140),
            ("game", "游戏", 80),
            ("field", "字段", 80),
            ("pattern", "特征码", 300),
        ):
            tree.heading(col, text=title)
            tree.column(col, width=w)
        tree.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        paths: list[str] = []
        for it in items:
            paths.append(it.get("_path", ""))
            tree.insert(
                "",
                tk.END,
                values=(
                    str(it.get("saved_at", ""))[:19],
                    it.get("game", ""),
                    it.get("field_name", ""),
                    str(it.get("pattern", ""))[:60],
                ),
            )

        def load_sel() -> None:
            sel = tree.selection()
            if not sel:
                return
            idx = tree.index(sel[0])
            path = paths[idx]
            try:
                saved = load_history_entry(path)
            except Exception as exc:
                messagebox.showerror("加载失败", str(exc))
                return
            self.sig_field_var.set(saved.field_name)
            self.sig_type_var.set(saved.value_type)
            self.sig_module_var.set(saved.module_hint)
            self._sig_last_pattern = saved.pattern
            self._sig_last_offset = saved.offset_to_target
            self._sig_last = GeneratedSignature(
                pattern=saved.pattern,
                offset_to_target=saved.offset_to_target,
                fixed_bytes=saved.fixed_bytes,
                wildcard_bytes=0,
                sample_count=saved.sample_count,
                window_before=0,
                window_after=0,
            )
            self.sig_out.delete("1.0", tk.END)
            self.sig_out.insert(tk.END, f"已从历史加载 {saved.field_name}\n{saved.pattern}")
            win.destroy()

        ttk.Button(win, text="加载选中", style="Primary.TButton", command=load_sel).pack(pady=6)

    def _sig_export_wizard(self) -> None:
        try:
            saved = self._sig_as_saved()
        except Exception as exc:
            messagebox.showerror("无法导出", str(exc))
            return
        default_dir = Path.home() / "Documents" / "ce-exports"
        default_dir.mkdir(parents=True, exist_ok=True)
        win = tk.Toplevel(self)
        win.title("导出向导")
        win.geometry("420x260")
        ttk.Label(win, text=f"默认目录: {default_dir}").pack(anchor=tk.W, padx=12, pady=8)
        v_py = tk.BooleanVar(value=True)
        v_lua = tk.BooleanVar(value=True)
        v_ass = tk.BooleanVar(value=True)
        v_scc = tk.BooleanVar(value=False)
        for text, var in (
            ("Python reader（含 AOB）", v_py),
            ("Lua AOB（ASS mem.aob_scan）", v_lua),
            ("ASS 字段表 JSON", v_ass),
            ("SCC JSON", v_scc),
        ):
            ttk.Checkbutton(win, text=text, variable=var).pack(anchor=tk.W, padx=16)

        def do_export() -> None:
            game = self.game_name_var.get().strip() or "game"
            out = default_dir
            result = self._result or ExtractResult(
                chains=[], total_raw=0, total_after_filter=0, modules_seen=[], source_file="signature"
            )
            sigs = [saved]
            try:
                profile = self._profiles.load(game)
                for d in profile.signatures:
                    s = SavedSignature.from_dict(d)
                    if s.field_name != saved.field_name:
                        sigs.append(s)
            except FileNotFoundError:
                pass
            pkg = self.android_pkg_var.get().strip() if hasattr(self, "android_pkg_var") else ""
            names = []
            if v_py.get():
                p = save_python_with_signatures(
                    result,
                    sigs,
                    out / f"{game}_reader.py",
                    preset_id=self.preset_var.get(),
                    game_name=game,
                    pointer_size=int(self.pointer_size_var.get()),
                    target_pid=self._target_pid,
                )
                names.append(p.name)
            if v_lua.get():
                p = save_lua_signatures(sigs, out / f"{game}_aob.lua", game_name=game)
                names.append(p.name)
            if v_ass.get():
                p = save_ass_fields(
                    result,
                    sigs,
                    out / f"{game}_ass_fields.json",
                    android_package=pkg,
                    game_name=game,
                    pointer_size=int(self.pointer_size_var.get()),
                )
                names.append(p.name)
            if v_scc.get():
                p = save_scc_json(
                    result,
                    out / f"{game}_scc.json",
                    preset_id=self.preset_var.get(),
                    android_package=pkg,
                    signatures=[s.to_dict() for s in sigs],
                )
                names.append(p.name)
            win.destroy()
            messagebox.showinfo("导出完成", "\n".join(names) or "未选择格式")
            self.status_var.set(f"已导出到 {out}")

        ttk.Button(win, text="导出", style="Primary.TButton", command=do_export).pack(pady=12)
