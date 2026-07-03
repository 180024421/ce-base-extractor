"""导出 Auto Script Studio 兼容的 Lua 读内存片段。"""

from __future__ import annotations

from pathlib import Path

from ce_base_extractor.models import ExtractResult


def _hex(value: int) -> str:
    return f"0x{value:X}"


def result_to_lua_snippet(result: ExtractResult) -> str:
    lines = [
        "-- Auto Script Studio / ce-base-extractor 生成",
        "-- 需配合 mem 模块或 bot 扩展；以下为指针链读数模板",
        "local mem = require('mem')  -- 或项目内内存读取封装",
        "",
    ]
    for i, chain in enumerate(result.chains, 1):
        name = chain.export_name(i)
        off_list = ", ".join(_hex(o) for o in chain.offsets)
        vtype = chain.value_type or "int32"
        lines.append(f"-- {name} score={chain.score:.1f}")
        lines.append(
            f"local {name} = mem.read_chain('{chain.module_name}', "
            f"{_hex(chain.module_offset)}, {{{off_list}}}, '{vtype}')"
        )
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def save_lua_script(result: ExtractResult, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result_to_lua_snippet(result), encoding="utf-8")
    return path
