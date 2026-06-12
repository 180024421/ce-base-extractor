from __future__ import annotations

import json
from pathlib import Path

from ce_base_extractor.models import ExtractResult, PointerChain


def _hex_offset(value: int) -> str:
    return f"0x{value:X}"


def format_chain(chain: PointerChain, index: int | None = None) -> str:
    prefix = f"[{index}] " if index is not None else ""
    head = f"{chain.module_name}+{_hex_offset(chain.module_offset)}"
    if not chain.offsets:
        return f"{prefix}{head}  (score={chain.score:.1f})"
    tail = " → ".join(f"+{_hex_offset(o)}" for o in chain.offsets)
    return f"{prefix}{head} → {tail}  (score={chain.score:.1f})"


def format_ce_table(chain: PointerChain) -> str:
    """CE 地址表可用的指针表达式。"""
    head = f'"{chain.module_name}"+{_hex_offset(chain.module_offset)}'
    if not chain.offsets:
        return head
    parts = [head]
    for off in chain.offsets:
        parts.append(_hex_offset(off))
    return ",".join(parts)


def to_text(result: ExtractResult, include_ce_format: bool = True) -> str:
    lines: list[str] = []
    lines.append(f"源文件: {result.source_file}")
    if result.ptrid is not None:
        lines.append(f"ptrid: {result.ptrid}")
    lines.append(
        f"原始 {result.total_raw} 条 → 过滤后 {result.total_after_filter} 条 → 输出 {len(result.chains)} 条"
    )
    lines.append("")
    for i, chain in enumerate(result.chains, 1):
        lines.append(format_chain(chain, i))
        if include_ce_format:
            lines.append(f"    CE: {format_ce_table(chain)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def to_json(result: ExtractResult) -> str:
    payload = {
        "source_file": result.source_file,
        "ptrid": result.ptrid,
        "total_raw": result.total_raw,
        "total_after_filter": result.total_after_filter,
        "modules_seen": result.modules_seen,
        "chains": [
            {
                "module": c.module_name,
                "module_offset": c.module_offset,
                "module_offset_hex": _hex_offset(c.module_offset),
                "offsets": list(c.offsets),
                "offsets_hex": [_hex_offset(o) for o in c.offsets],
                "depth": c.depth,
                "score": round(c.score, 2),
                "ce_expression": format_ce_table(c),
            }
            for c in result.chains
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def save_result(result: ExtractResult, output: str | Path, fmt: str = "txt") -> Path:
    out = Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    if fmt == "json":
        out.write_text(to_json(result), encoding="utf-8")
    else:
        out.write_text(to_text(result), encoding="utf-8")
    return out
