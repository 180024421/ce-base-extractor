"""导出 Auto Script Studio 兼容的 Lua 读内存片段。"""

from __future__ import annotations

from pathlib import Path

from ce_base_extractor.models import ExtractResult


def _hex(value: int) -> str:
    return f"0x{value:X}"


def result_to_lua_snippet(result: ExtractResult) -> str:
    lines = [
        "-- Auto Script Studio / ce-base-extractor 生成",
        "-- 用法: 将片段粘贴到 main.lua，配合 android-runtime 内存读取",
        "-- 若项目有 bot.read_chain / mem.read_chain，按实际 API 替换下方调用",
        "",
        "local function read_chain(module, base_off, offsets, vtype)",
        "  -- TODO: 对接 ASS android-runtime 内存模块",
        "  if bot and bot.read_chain then",
        "    return bot.read_chain(module, base_off, offsets, vtype)",
        "  end",
        "  error('请实现 read_chain 或引入 mem 模块')",
        "end",
        "",
    ]
    for i, chain in enumerate(result.chains, 1):
        name = chain.export_name(i)
        off_list = ", ".join(_hex(o) for o in chain.offsets)
        vtype = chain.value_type or "int32"
        lines.append(f"-- {name} score={chain.score:.1f} verified={chain.verified}")
        lines.append(
            f"local {name} = read_chain('{chain.module_name}', "
            f"{_hex(chain.module_offset)}, {{{off_list}}}, '{vtype}')"
        )
        lines.append("")
    lines.append("return {")
    for i, chain in enumerate(result.chains, 1):
        lines.append(f"  {chain.export_name(i)} = {chain.export_name(i)},")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def save_lua_script(result: ExtractResult, output: str | Path) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result_to_lua_snippet(result), encoding="utf-8")
    return path
