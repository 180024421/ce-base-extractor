from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ce_base_extractor.pipeline import mark_wizard_done

WATCH_DIR = Path.home() / "Documents" / "ce-exports"


def show_first_run_wizard(parent: tk.Tk, on_done=None) -> None:
    win = tk.Toplevel(parent)
    win.title("欢迎使用 CE 基址提取器")
    win.geometry("520x380")
    win.transient(parent)
    win.grab_set()

    ttk.Label(win, text="雷电模拟器 · 快速向导", font=("Segoe UI", 14, "bold")).pack(
        anchor=tk.W, padx=16, pady=(16, 8)
    )
    text = (
        "1. CE 附加 dnplayer.exe，完成指针扫描并 Rescan 2～3 次\n"
        "2. 每次导出 SQLite 到:\n"
        f"   {WATCH_DIR}\n"
        "3. 在本工具「交叉验证」页添加多个 SQLite\n"
        "4. 为每条结果设置字段名（如 gold、hp）和类型\n"
        "5. 导出 Python 脚本，运行:\n"
        "   python game_reader.py --list-processes  # 多开时选 PID\n"
        "6. 重启模拟器后点「重启验证」确认基址稳定"
    )
    ttk.Label(win, text=text, justify=tk.LEFT, wraplength=480).pack(anchor=tk.W, padx=16, pady=8)

    WATCH_DIR.mkdir(parents=True, exist_ok=True)

    def finish():
        mark_wizard_done()
        win.destroy()
        if on_done:
            on_done()

    ttk.Button(win, text="开始使用", command=finish).pack(pady=16)
