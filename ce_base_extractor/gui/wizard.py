from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ce_base_extractor.pipeline import mark_wizard_done

WATCH_DIR = Path.home() / "Documents" / "ce-exports"


def show_first_run_wizard(parent: tk.Tk, on_done=None) -> None:
    win = tk.Toplevel(parent)
    win.title("欢迎使用 CE 基址提取器")
    win.geometry("560x460")
    win.transient(parent)
    win.grab_set()

    ttk.Label(win, text="雷电模拟器 · CE 标准流程（SOP）", font=("Segoe UI", 14, "bold")).pack(
        anchor=tk.W, padx=16, pady=(16, 8)
    )
    text = (
        "【准备】\n"
        "1. CE 附加 dnplayer.exe（多开时用 --list-processes 选 PID）\n"
        "2. 对目标数值做指针扫描，Rescan 2～3 次（值变化 / 未变化各一次）\n"
        "3. 每次 File → Export to sqlite，保存到:\n"
        f"   {WATCH_DIR}\n\n"
        "【交叉验证】\n"
        "4. 本工具「交叉验证」页添加 2～3 个 SQLite\n"
        "5. 关注稳定率（3/3 优于 2/3）；可勾选「仅全命中」\n\n"
        "【命名与导出】\n"
        "6. 为每条链设置字段名（gold、hp）与类型\n"
        "7. 导出 Python / Lua（Auto Script Studio）/ SCC JSON\n\n"
        "【验证】\n"
        "8. 重启模拟器后点「重启验证」\n"
        "9. 游戏更新后用 profile-migrate 对比旧版配置"
    )
    ttk.Label(win, text=text, justify=tk.LEFT, wraplength=520).pack(anchor=tk.W, padx=16, pady=8)

    WATCH_DIR.mkdir(parents=True, exist_ok=True)

    def finish():
        mark_wizard_done()
        win.destroy()
        if on_done:
            on_done()

    ttk.Button(win, text="开始使用", command=finish).pack(pady=16)
