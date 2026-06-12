from __future__ import annotations

import json
from pathlib import Path

from ce_base_extractor.models import ExtractResult, PointerChain


def chains_to_python_module(
    chains: list[PointerChain],
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> str:
    payload = {
        "game": game_name,
        "pointer_size": pointer_size,
        "target_pid": target_pid,
        "chains": [
            {
                "name": c.export_name(i + 1),
                "module": c.module_name,
                "module_offset": c.module_offset,
                "offsets": list(c.offsets),
                "type": c.value_type,
                "verified": c.verified,
                "il2cpp_symbol": c.il2cpp_symbol,
            }
            for i, c in enumerate(chains)
        ],
    }
    data_repr = json.dumps(payload, ensure_ascii=False, indent=4)
    return f'''# -*- coding: utf-8 -*-
"""可 import 的游戏内存配置模块 · {game_name}

用法:
    from {game_name}_memory import GAME_CONFIG, CHAINS
    # 配合 ce_base_extractor.runtime.win_memory 或自建 reader 使用
"""
from __future__ import annotations

GAME_CONFIG = {data_repr}

CHAINS = GAME_CONFIG["chains"]
POINTER_SIZE = GAME_CONFIG["pointer_size"]
TARGET_PID = GAME_CONFIG["target_pid"]
'''

    # Fix: use valid module name - game_name might have invalid chars
    # The docstring uses game_name but file will be named properly


def save_python_module(
    result: ExtractResult,
    output: str | Path,
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> Path:
    path = Path(output)
    safe_name = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in game_name)
    content = chains_to_python_module(
        result.chains, game_name=safe_name, pointer_size=pointer_size, target_pid=target_pid
    )
    path.write_text(content, encoding="utf-8")
    return path
