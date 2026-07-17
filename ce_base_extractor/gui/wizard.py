from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import ttk

from ce_base_extractor.pipeline import mark_wizard_done

DEFAULT_WATCH_DIR = Path.home() / "Documents" / "ce-exports"


def show_first_run_wizard(parent: tk.Tk, on_done=None, *, watch_dir: Path | None = None) -> None:
    watch = Path(watch_dir) if watch_dir else DEFAULT_WATCH_DIR
    win = tk.Toplevel(parent)
    win.title("欢迎使用 CE 基址提取器")
    win.geometry("580x500")
    win.transient(parent)
    win.grab_set()

    ttk.Label(win, text="推荐流程（GUI）", font=("Segoe UI", 14, "bold")).pack(
        anchor=tk.W, padx=16, pady=(16, 8)
    )
    text = (
        "【准备】\n"
        "1. 用 Cheat Engine 附加模拟器进程（本工具「提取」页可点「选进程」查看 PID）\n"
        "2. 对目标数值做指针扫描，Rescan 2～3 次（值变化 / 未变化各至少一次）\n"
        "3. 每次 File → Export to sqlite，保存到：\n"
        f"   {watch}\n\n"
        "【交叉验证】\n"
        "4. 打开「交叉验证」页，添加 2～3 个 SQLite，点「交叉验证」\n"
        "5. 关注稳定率（3/3 优于 2/3）；需要时可勾选高级选项「交叉需全命中」\n\n"
        "【命名与导出】\n"
        "6. 在结果列表为每条链设置字段名（如 gold、hp）与类型\n"
        "7. 导出 Python / Lua（Auto Script Studio）/ SCC JSON\n\n"
        "【验证】\n"
        "8. 点「记录读数」→ 重启模拟器 → 再点「重启验证」\n"
        "9. 游戏更新后：在「游戏 Profile」页用「版本对比」对照旧配置\n\n"
        "提示：菜单「帮助 → 流程说明」可随时再看本向导。"
    )
    ttk.Label(win, text=text, justify=tk.LEFT, wraplength=540).pack(anchor=tk.W, padx=16, pady=8)

    watch.mkdir(parents=True, exist_ok=True)

    def finish():
        mark_wizard_done()
        win.destroy()
        if on_done:
            on_done()

    ttk.Button(win, text="开始使用", command=finish).pack(pady=16)
