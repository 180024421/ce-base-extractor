from __future__ import annotations

from pathlib import Path

from ce_base_extractor.filters.presets import EmulatorPreset, get_preset
from ce_base_extractor.models import ExtractResult, PointerChain

_STANDALONE_READER = Path(__file__).resolve().parent.parent / "runtime" / "standalone_reader.py"


def _embedded_reader_source() -> str:
    return _STANDALONE_READER.read_text(encoding="utf-8")


def _format_chain_dict(chain: PointerChain, index: int) -> str:
    name = chain.export_name(index)
    parts = [
        f'        "name": {name!r},',
        f'        "module": {chain.module_name!r},',
        f'        "module_offset": 0x{chain.module_offset:X},',
        f'        "offsets": {list(chain.offsets)!r},',
        f'        "type": {chain.value_type!r},',
        f'        "verified": {str(chain.verified)},',
    ]
    if chain.il2cpp_symbol:
        parts.append(f'        "il2cpp_symbol": {chain.il2cpp_symbol!r},')
    parts.append(f'        "score": {chain.score:.1f},')
    return "    {\n" + "\n".join(parts) + "\n    }"


def chains_to_python_script(
    chains: list[PointerChain],
    preset: EmulatorPreset | None = None,
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
    embed_reader: bool = True,
) -> str:
    preset = preset or get_preset("ldplayer")
    assert preset is not None
    process_names = repr(list(preset.process_names))
    chain_blocks = ",\n".join(_format_chain_dict(c, i) for i, c in enumerate(chains, 1))
    pid_line = f"TARGET_PID = {target_pid}" if target_pid else "TARGET_PID = None"
    reader_block = (
        _embedded_reader_source()
        if embed_reader
        else ("from ce_base_extractor.runtime.win_memory import ProcessMemory\n")
    )
    attach_line = "ProcessMemory.auto_attach(PROCESS_NAMES, pid=TARGET_PID)"

    return f'''# -*- coding: utf-8 -*-
"""
自动生成内存读取脚本
游戏: {game_name}
模拟器: {preset.label}
"""
from __future__ import annotations

import argparse
import sys

{reader_block}

PROCESS_NAMES = {process_names}
POINTER_SIZE = {pointer_size}
{pid_line}

CHAINS = [
{chain_blocks}
]

READERS = {{
    "int32": lambda mem, addr: mem.read_i32(addr),
    "uint32": lambda mem, addr: mem.read_u32(addr),
    "int64": lambda mem, addr: mem.read_i64(addr),
    "uint64": lambda mem, addr: mem.read_u64(addr),
    "float": lambda mem, addr: mem.read_f32(addr),
    "double": lambda mem, addr: mem.read_f64(addr),
    "bytes16": lambda mem, addr: mem.read_bytes(addr, 16),
}}


def read_chain(mem: "ProcessMemory", chain: dict):
    addr = mem.resolve_chain(
        chain["module"], chain["module_offset"], chain["offsets"], pointer_size=POINTER_SIZE
    )
    reader = READERS.get(chain.get("type", "int32"))
    if reader is None:
        raise ValueError(f"不支持的类型: {{chain.get('type')}}")
    return reader(mem, addr)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="读取 CE 基址数据")
    parser.add_argument("--chain", help="只读取指定字段名")
    parser.add_argument("--pid", type=int, help="指定模拟器进程 PID（多开时用）")
    parser.add_argument("--list-processes", action="store_true", help="列出匹配的模拟器进程")
    parser.add_argument("--list-modules", action="store_true", help="列出模块")
    args = parser.parse_args(argv)

    if args.list_processes:
        for pid, name in ProcessMemory.list_matching(PROCESS_NAMES):
            print(f"PID={{pid}}  {{name}}")
        return 0

    pid = args.pid if args.pid is not None else TARGET_PID
    try:
        mem = {attach_line}
    except (ProcessLookupError, OSError) as exc:
        print(f"附加失败: {{exc}}", file=sys.stderr)
        print("提示: python {game_name}_reader.py --list-processes", file=sys.stderr)
        return 1

    with mem:
        if args.list_modules:
            for name, base in sorted(mem.list_modules().items()):
                print(f"{{name}} @ 0x{{base:X}}")
            return 0

        targets = CHAINS
        if args.chain:
            targets = [c for c in CHAINS if c["name"] == args.chain]
            if not targets:
                print(f"未找到: {{args.chain}}", file=sys.stderr)
                return 1

        for chain in targets:
            try:
                value = read_chain(mem, chain)
                sym = chain.get("il2cpp_symbol", "")
                extra = f"  [{{sym}}]" if sym else ""
                print(f"{{chain['name']}}: {{value}}{{extra}}")
            except Exception as exc:
                print(f"{{chain['name']}}: 失败 - {{exc}}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


def result_to_python_script(
    result: ExtractResult,
    preset_id: str = "ldplayer",
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> str:
    preset = get_preset(preset_id)
    return chains_to_python_script(
        result.chains,
        preset=preset,
        game_name=game_name,
        pointer_size=pointer_size,
        target_pid=target_pid,
    )


def save_python_script(
    result: ExtractResult,
    output: str | Path,
    preset_id: str = "ldplayer",
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> Path:
    path = Path(output)
    path.write_text(
        result_to_python_script(
            result,
            preset_id=preset_id,
            game_name=game_name,
            pointer_size=pointer_size,
            target_pid=target_pid,
        ),
        encoding="utf-8",
    )
    return path
