from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from ce_base_extractor.models import PointerChain

VALUE_TYPES = ("int32", "uint32", "int64", "uint64", "float", "double", "bytes16")


class ChainEditDialog(tk.Toplevel):
    def __init__(self, parent, chain: PointerChain, index: int) -> None:
        super().__init__(parent)
        self._chain = chain
        self.title(f"编辑导出字段 · {chain.module_name}")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result: PointerChain | None = None

        ttk.Label(self, text=f"模块: {chain.module_name}+0x{chain.module_offset:X}").grid(
            row=0, column=0, columnspan=2, padx=12, pady=(12, 4), sticky=tk.W
        )

        ttk.Label(self, text="字段名").grid(row=1, column=0, padx=12, sticky=tk.W)
        self.name_var = tk.StringVar(value=chain.field_name or f"chain_{index}")
        ttk.Entry(self, textvariable=self.name_var, width=28).grid(row=1, column=1, padx=8, pady=4)

        ttk.Label(self, text="数据类型").grid(row=2, column=0, padx=12, sticky=tk.W)
        self.type_var = tk.StringVar(value=chain.value_type or "int32")
        ttk.Combobox(self, textvariable=self.type_var, values=VALUE_TYPES, state="readonly").grid(
            row=2, column=1, padx=8, pady=4, sticky=tk.W
        )

        ttk.Label(self, text="Il2Cpp 符号").grid(row=3, column=0, padx=12, sticky=tk.W)
        self.sym_var = tk.StringVar(value=chain.il2cpp_symbol)
        ttk.Entry(self, textvariable=self.sym_var, width=28).grid(row=3, column=1, padx=8, pady=4)

        self.verified_var = tk.BooleanVar(value=chain.verified)
        ttk.Checkbutton(self, text="已验证稳定", variable=self.verified_var).grid(
            row=4, column=0, columnspan=2, padx=12, pady=4, sticky=tk.W
        )

        btns = ttk.Frame(self)
        btns.grid(row=5, column=0, columnspan=2, pady=12)
        ttk.Button(btns, text="确定", command=self._ok).pack(side=tk.LEFT, padx=6)
        ttk.Button(btns, text="取消", command=self.destroy).pack(side=tk.LEFT)

    def _ok(self) -> None:
        c = self._chain
        self.result = PointerChain(
            module_name=c.module_name,
            module_offset=c.module_offset,
            offsets=c.offsets,
            score=c.score,
            source=c.source,
            field_name=self.name_var.get().strip(),
            value_type=self.type_var.get(),
            verified=self.verified_var.get(),
            il2cpp_symbol=self.sym_var.get().strip(),
        )
        self.destroy()


def open_chain_editor(parent, chain: PointerChain, index: int) -> PointerChain | None:
    dlg = ChainEditDialog(parent, chain, index)
    parent.wait_window(dlg)
    return dlg.result
