from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ce_base_extractor.gui.theme import FONTS, THEME
from ce_base_extractor.runtime.win_memory import ProcessInfo


class ProcessPickerDialog(tk.Toplevel):
    def __init__(self, parent, processes: list[ProcessInfo]) -> None:
        super().__init__(parent)
        self.title("选择模拟器进程")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.configure(bg=THEME["bg"])
        self.selected: ProcessInfo | None = None

        ttk.Label(
            self,
            text="检测到多个进程，请选择要附加的实例：",
            style="Hint.TLabel",
        ).pack(anchor=tk.W, padx=16, pady=(16, 8))

        wrap = tk.Frame(self, bg=THEME["surface"], highlightbackground=THEME["border"], highlightthickness=1)
        wrap.pack(padx=16, pady=4)

        self.listbox = tk.Listbox(
            wrap,
            width=76,
            height=min(10, len(processes)),
            font=FONTS["mono_sm"],
            bg=THEME["surface_alt"],
            fg=THEME["text"],
            relief=tk.FLAT,
            selectbackground=THEME["accent_light"],
        )
        for p in processes:
            self.listbox.insert(tk.END, p.label)
        self.listbox.pack(padx=8, pady=8)
        self.listbox.selection_set(0)

        btns = ttk.Frame(self)
        btns.pack(pady=16)
        ttk.Button(btns, text="确定", style="Primary.TButton", command=self._ok).pack(
            side=tk.LEFT, padx=6
        )
        ttk.Button(btns, text="取消", command=self.destroy).pack(side=tk.LEFT)

        self._processes = processes

    def _ok(self) -> None:
        sel = self.listbox.curselection()
        if sel:
            self.selected = self._processes[int(sel[0])]
        self.destroy()


def pick_process(parent, processes: list[ProcessInfo]) -> ProcessInfo | None:
    if not processes:
        return None
    if len(processes) == 1:
        return processes[0]
    dlg = ProcessPickerDialog(parent, processes)
    parent.wait_window(dlg)
    return dlg.selected
