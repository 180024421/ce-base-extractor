"""GUI 主题与布局辅助（简约大气风格）。"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

THEME = {
    "bg": "#f0f2f5",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "border": "#e2e8f0",
    "border_focus": "#93c5fd",
    "text": "#0f172a",
    "text_secondary": "#64748b",
    "text_muted": "#94a3b8",
    "accent": "#2563eb",
    "accent_light": "#dbeafe",
    "accent_hover": "#1d4ed8",
    "success": "#059669",
    "warning": "#d97706",
    "danger": "#dc2626",
    "header_bg": "#ffffff",
    "status_bg": "#1e293b",
    "status_fg": "#cbd5e1",
    "tab_active": "#2563eb",
}

FONTS = {
    "title": ("Microsoft YaHei UI", 15, "bold"),
    "subtitle": ("Microsoft YaHei UI", 9),
    "body": ("Microsoft YaHei UI", 9),
    "body_bold": ("Microsoft YaHei UI", 9, "bold"),
    "small": ("Microsoft YaHei UI", 8),
    "mono": ("Cascadia Mono", 10),
    "mono_sm": ("Cascadia Mono", 9),
}


def apply_theme(root: tk.Misc) -> ttk.Style:
    """应用全局 ttk 样式，返回 Style 实例供后续扩展。"""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    bg = THEME["bg"]
    surface = THEME["surface"]
    text = THEME["text"]
    accent = THEME["accent"]

    root.configure(bg=bg)

    style.configure(".", background=bg, foreground=text, font=FONTS["body"])
    style.configure("TFrame", background=bg)
    style.configure("Surface.TFrame", background=surface)
    style.configure("Card.TFrame", background=surface)
    style.configure("Header.TFrame", background=THEME["header_bg"])

    style.configure("Title.TLabel", font=FONTS["title"], foreground=text, background=THEME["header_bg"])
    style.configure(
        "Subtitle.TLabel",
        font=FONTS["subtitle"],
        foreground=THEME["text_secondary"],
        background=THEME["header_bg"],
    )
    style.configure("Muted.TLabel", font=FONTS["small"], foreground=THEME["text_muted"], background=bg)
    style.configure("Section.TLabel", font=FONTS["body_bold"], foreground=text, background=surface)
    style.configure("Hint.TLabel", font=FONTS["subtitle"], foreground=THEME["text_secondary"], background=bg)

    style.configure("TButton", padding=(10, 5), font=FONTS["body"])
    style.configure(
        "Primary.TButton",
        background=accent,
        foreground="#ffffff",
        padding=(14, 7),
        font=FONTS["body_bold"],
        borderwidth=0,
    )
    style.map(
        "Primary.TButton",
        background=[("active", THEME["accent_hover"]), ("pressed", THEME["accent_hover"])],
        foreground=[("disabled", "#94a3b8")],
    )
    style.configure(
        "Accent.TButton",
        background=THEME["success"],
        foreground="#ffffff",
        padding=(12, 6),
        font=FONTS["body_bold"],
    )
    style.map("Accent.TButton", background=[("active", "#047857")])

    style.configure("TNotebook", background=bg, borderwidth=0, tabmargins=[4, 4, 4, 0])
    style.configure(
        "TNotebook.Tab",
        padding=(18, 8),
        font=FONTS["body"],
        background=THEME["surface_alt"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", surface), ("active", surface)],
        foreground=[("selected", accent)],
    )

    style.configure(
        "TLabelframe",
        background=surface,
        bordercolor=THEME["border"],
        relief="solid",
        borderwidth=1,
    )
    style.configure("TLabelframe.Label", font=FONTS["body_bold"], foreground=text, background=surface)

    style.configure(
        "Treeview",
        background=surface,
        fieldbackground=surface,
        foreground=text,
        rowheight=28,
        font=FONTS["body"],
        borderwidth=0,
    )
    style.configure(
        "Treeview.Heading",
        font=FONTS["body_bold"],
        background=THEME["surface_alt"],
        foreground=text,
        relief="flat",
    )
    style.map("Treeview", background=[("selected", THEME["accent_light"])], foreground=[("selected", text)])

    style.configure("TEntry", padding=4, fieldbackground=surface)
    style.configure("TCombobox", padding=4)
    style.configure("Horizontal.TProgressbar", troughcolor=THEME["surface_alt"], background=accent)

    style.configure("Status.TFrame", background=THEME["status_bg"])
    return style


def make_h_separator(parent: tk.Misc, *, pady: int = 8) -> ttk.Separator:
    sep = ttk.Separator(parent, orient=tk.HORIZONTAL)
    sep.pack(fill=tk.X, pady=pady)
    return sep


def make_tool_group(parent: tk.Misc, title: str) -> ttk.LabelFrame:
    return ttk.LabelFrame(parent, text=title, padding=(10, 8))


class FileDropCard(tk.Frame):
    """文件选择卡片（拖放提示 + 路径展示）。"""

    def __init__(
        self,
        parent: tk.Misc,
        textvariable: tk.StringVar,
        *,
        allow_drop: bool = True,
        **kwargs,
    ) -> None:
        super().__init__(
            parent,
            bg=THEME["surface"],
            highlightbackground=THEME["border"],
            highlightthickness=1,
            **kwargs,
        )
        self._textvariable = textvariable
        self._active = False

        inner = tk.Frame(self, bg=THEME["surface"], padx=16, pady=12)
        inner.pack(fill=tk.BOTH, expand=True)

        hint = (
            "拖放 CE 导出文件到窗口，或点击「选择文件」"
            if allow_drop
            else "点击「选择文件」选择 CE 导出的 SQLite / PTR"
        )
        self._hint = tk.Label(
            inner,
            text=hint,
            font=FONTS["subtitle"],
            fg=THEME["text_muted"],
            bg=THEME["surface"],
        )
        self._hint.pack(anchor=tk.W)

        self._path = tk.Label(
            inner,
            textvariable=textvariable,
            font=FONTS["mono_sm"],
            fg=THEME["text"],
            bg=THEME["surface"],
            anchor=tk.W,
            justify=tk.LEFT,
            wraplength=900,
        )
        self._path.pack(anchor=tk.W, pady=(6, 0), fill=tk.X)

    def set_active(self, active: bool) -> None:
        self._active = active
        color = THEME["border_focus"] if active else THEME["border"]
        self.configure(highlightbackground=color)
        self._hint.configure(
            fg=THEME["accent"] if active else THEME["text_muted"],
        )
