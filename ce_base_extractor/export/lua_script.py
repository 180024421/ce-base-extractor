"""导出 Auto Script Studio 兼容的 Lua 读内存片段。"""

from __future__ import annotations

from pathlib import Path

from ce_base_extractor.models import ExtractResult


def _hex(value: int) -> str:
    return f"0x{value:X}"


def result_to_lua_snippet(
    result: ExtractResult,
    *,
    game_name: str = "game",
    scc_json_name: str | None = None,
) -> str:
    scc_name = scc_json_name or f"{game_name}_scc.json"
    lines = [
        "-- Auto Script Studio / ce-base-extractor 生成",
        "-- 将同目录下的 SCC JSON 一并复制到设备脚本目录",
        f"-- 推荐: bot.load_bases('{scc_name}') 或 bot.read_chain(...)",
        "",
        "if bot and bot.set_pointer_size then",
        "  bot.set_pointer_size(8)",
        "end",
        "",
        "local function read_chain(module, base_off, offsets, vtype)",
        "  if bot and bot.read_chain then",
        "    return bot.read_chain(module, base_off, offsets, vtype)",
        "  end",
        "  if mem and mem.read_chain then",
        "    return mem.read_chain(module, base_off, offsets, vtype)",
        "  end",
        "  error('请使用 ASS android-runtime（root）或实现 read_chain')",
        "end",
        "",
        f"local _bases = (bot and bot.load_bases) and bot.load_bases('{scc_name}') or nil",
        "",
    ]
    for i, chain in enumerate(result.chains, 1):
        name = chain.export_name(i)
        off_list = ", ".join(_hex(o) for o in chain.offsets)
        vtype = chain.value_type or "int32"
        lines.append(f"-- {name} score={chain.score:.1f} verified={chain.verified}")
        lines.append(
            f"local {name} = (_bases and _bases.{name}) and _bases.{name}() or "
            f"read_chain('{chain.module_name}', {_hex(chain.module_offset)}, {{{off_list}}}, '{vtype}')"
        )
        lines.append("")
    lines.append("return {")
    for i, chain in enumerate(result.chains, 1):
        lines.append(f"  {chain.export_name(i)} = {chain.export_name(i)},")
    lines.append("}")
    lines.append("")
    return "\n".join(lines)


def save_lua_script(
    result: ExtractResult,
    output: str | Path,
    *,
    game_name: str = "game",
    preset_id: str = "ldplayer",
    write_scc_sidecar: bool = True,
) -> Path:
    path = Path(output)
    path.parent.mkdir(parents=True, exist_ok=True)
    scc_name = f"{game_name}_scc.json"
    path.write_text(
        result_to_lua_snippet(result, game_name=game_name, scc_json_name=scc_name),
        encoding="utf-8",
    )
    if write_scc_sidecar:
        from ce_base_extractor.export.scc_export import save_scc_json

        save_scc_json(result, path.with_name(scc_name), preset_id=preset_id)
    return path
