from __future__ import annotations

import os
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ce_base_extractor.pipeline import mark_wizard_done

DEFAULT_WATCH_DIR = Path.home() / "Documents" / "ce-exports"


def _open_path(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.startfile(path)  # type: ignore[attr-defined]
    except Exception:
        subprocess.run(["explorer", str(path)], check=False)


def show_first_run_wizard(parent: tk.Tk, on_done=None, *, watch_dir: Path | None = None) -> None:
    watch = Path(watch_dir) if watch_dir else DEFAULT_WATCH_DIR
    win = tk.Toplevel(parent)
    win.title("欢迎使用 CE 基址提取器")
    win.geometry("600x540")
    win.transient(parent)
    win.grab_set()

    ttk.Label(win, text="推荐流程（GUI）", font=("Segoe UI", 14, "bold")).pack(
        anchor=tk.W, padx=16, pady=(16, 8)
    )
    text = (
        "【CE 最短清单】\n"
        "□ 以管理员运行 CE 与本工具\n"
        "□ CE 附加模拟器进程（与本工具「选进程」同一 PID）\n"
        "□ 指针扫描后 Rescan ≥2 次，每次 Export to sqlite\n"
        f"□ 文件保存到监视目录：{watch}\n\n"
        "【本工具】\n"
        "1. 打开「交叉验证」添加 2～3 个 SQLite → 交叉验证\n"
        "2. 为字段命名 → 测试读取 → 导出 / ASS 交接包\n"
        "3. 记录读数 → 重启模拟器 → 重启验证\n\n"
        "无 CE？菜单「帮助 → 无 CE 试跑示例」可一键看完整闭环。\n"
        "菜单「帮助 → 流程说明」可随时再看本向导。"
    )
    ttk.Label(win, text=text, justify=tk.LEFT, wraplength=560).pack(anchor=tk.W, padx=16, pady=8)

    watch.mkdir(parents=True, exist_ok=True)

    btn_row = ttk.Frame(win)
    btn_row.pack(fill=tk.X, padx=16, pady=(4, 0))
    ttk.Button(btn_row, text="打开监视目录", command=lambda: _open_path(watch)).pack(side=tk.LEFT)

    def finish():
        mark_wizard_done()
        win.destroy()
        if on_done:
            on_done()

    ttk.Button(win, text="开始使用", command=finish).pack(pady=16)
