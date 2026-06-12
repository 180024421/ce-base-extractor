from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ce_base_extractor.runtime.win_memory import ProcessInfo


class ProcessPickerDialog(tk.Toplevel):
    def __init__(self, parent, processes: list[ProcessInfo]) -> None:
        super().__init__(parent)
        self.title("选择雷电实例")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.selected: ProcessInfo | None = None

        ttk.Label(self, text="检测到多个模拟器进程，请选择:").pack(
            anchor=tk.W, padx=12, pady=(12, 6)
        )

        self.listbox = tk.Listbox(self, width=72, height=min(8, len(processes)))
        for p in processes:
            self.listbox.insert(tk.END, p.label)
        self.listbox.pack(padx=12, pady=4)
        self.listbox.selection_set(0)

        btns = ttk.Frame(self)
        btns.pack(pady=12)
        ttk.Button(btns, text="确定", command=self._ok).pack(side=tk.LEFT, padx=6)
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
