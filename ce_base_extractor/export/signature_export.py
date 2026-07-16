"""特征码导出：Python / Lua / ASS 字段表。"""

from __future__ import annotations

import json
from pathlib import Path

from ce_base_extractor.filters.presets import get_preset
from ce_base_extractor.models import ExtractResult, PointerChain
from ce_base_extractor.signature import SavedSignature


def signatures_to_python_snippet(signatures: list[SavedSignature]) -> str:
    if not signatures:
        return "SIGNATURES = []\n"
    blocks = []
    for s in signatures:
        blocks.append(
            "    {\n"
            f'        "name": {s.field_name!r},\n'
            f'        "pattern": {s.pattern!r},\n'
            f'        "offset_to_target": {s.offset_to_target},\n'
            f'        "type": {s.value_type!r},\n'
            f'        "module_hint": {s.module_hint!r},\n'
            f'        "verified": {str(s.verified)},\n'
            "    }"
        )
    return "SIGNATURES = [\n" + ",\n".join(blocks) + "\n]\n"


def _aob_helpers_python() -> str:
    return '''
def _parse_aob(pattern: str):
    values = bytearray()
    mask = bytearray()
    for tok in pattern.replace(",", " ").split():
        if tok in ("?", "??"):
            values.append(0)
            mask.append(0)
        else:
            values.append(int(tok, 16))
            mask.append(0xFF)
    return bytes(values), bytes(mask)


def _find_aob(buf: bytes, pattern: bytes, mask: bytes, base: int = 0, max_hits: int = 8):
    plen = len(pattern)
    hits = []
    for i in range(0, len(buf) - plen + 1):
        ok = True
        for j in range(plen):
            if mask[j] and buf[i + j] != pattern[j]:
                ok = False
                break
        if ok:
            hits.append(base + i)
            if len(hits) >= max_hits:
                break
    return hits


def resolve_signature(mem: "ProcessMemory", sig: dict, module_hint: str | None = None) -> int:
    """扫描特征码并返回目标地址（命中 + offset_to_target）。"""
    pattern, mask = _parse_aob(sig["pattern"])
    hint = (module_hint or sig.get("module_hint") or "").strip().lower()
    modules = mem.list_modules(refresh=True)
    regions = []
    if hint:
        for name, base in modules.items():
            if hint in name.lower():
                # 无精确 size 时读最多 32MB
                regions.append((base, 32 * 1024 * 1024))
    if not regions:
        # 回退：扫所有模块基址起 8MB
        for name, base in modules.items():
            regions.append((base, 8 * 1024 * 1024))
    hits = []
    for base, size in regions:
        chunk = 1024 * 1024
        off = 0
        plen = len(pattern)
        while off + plen <= size and len(hits) < 8:
            try:
                buf = mem.read_bytes(base + off, min(chunk, size - off))
            except OSError:
                break
            hits.extend(_find_aob(buf, pattern, mask, base + off, max_hits=8 - len(hits)))
            if len(hits) >= 8:
                break
            off += max(len(buf) - plen + 1, 1)
        if hits:
            break
    if not hits:
        raise LookupError(f"特征码未命中: {sig.get('name')}")
    if len(hits) > 1:
        # 取第一个；调用方可再验证
        pass
    return hits[0] + int(sig.get("offset_to_target", 0))


def read_signature(mem: "ProcessMemory", sig: dict):
    addr = resolve_signature(mem, sig)
    reader = READERS.get(sig.get("type", "int32"))
    if reader is None:
        raise ValueError(f"不支持的类型: {sig.get('type')}")
    return reader(mem, addr)
'''


def build_python_reader_with_signatures(
    *,
    chains: list[PointerChain],
    signatures: list[SavedSignature],
    preset_id: str = "ldplayer",
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> str:
    from ce_base_extractor.export.python_script import chains_to_python_script

    base = chains_to_python_script(
        chains,
        preset=get_preset(preset_id),
        game_name=game_name,
        pointer_size=pointer_size,
        target_pid=target_pid,
    )
    # 在 CHAINS 后插入 SIGNATURES 与辅助函数，并扩展 main
    insert = "\n" + signatures_to_python_snippet(signatures) + _aob_helpers_python()
    marker = "\nREADERS = {"
    if marker not in base:
        return base + insert
    out = base.replace(marker, insert + marker, 1)
    if "for chain in targets:" in out and "read_signature" not in out:
        if "\n    return 0\n\n\nif __name__" in out:
            extra = """
        for sig in SIGNATURES:
            if args.chain and sig["name"] != args.chain:
                continue
            try:
                value = read_signature(mem, sig)
                print(f"{sig['name']} [aob]: {value}")
            except Exception as exc:
                print(f"{sig['name']} [aob]: 失败 - {exc}", file=sys.stderr)
"""
            out = out.replace(
                "\n    return 0\n\n\nif __name__",
                extra + "\n    return 0\n\n\nif __name__",
                1,
            )
    return out


def save_python_with_signatures(
    result: ExtractResult,
    signatures: list[SavedSignature],
    output: str | Path,
    *,
    preset_id: str = "ldplayer",
    game_name: str = "game",
    pointer_size: int = 8,
    target_pid: int | None = None,
) -> Path:
    path = Path(output)
    path.write_text(
        build_python_reader_with_signatures(
            chains=result.chains,
            signatures=signatures,
            preset_id=preset_id,
            game_name=game_name,
            pointer_size=pointer_size,
            target_pid=target_pid,
        ),
        encoding="utf-8",
    )
    return path


def signatures_to_lua(signatures: list[SavedSignature], *, game_name: str = "game") -> str:
    lines = [
        "-- Auto Script Studio / ce-base-extractor AOB 字段",
        "-- 若运行时尚无 mem.aob_scan，请用同目录 Python reader，或自行实现扫描。",
        f"-- game: {game_name}",
        "",
        "local SIGS = {",
    ]
    for s in signatures:
        lines.append("  {")
        lines.append(f'    name = "{s.field_name}",')
        lines.append(f'    pattern = "{s.pattern}",')
        lines.append(f"    offset = {s.offset_to_target},")
        lines.append(f'    type = "{s.value_type}",')
        if s.module_hint:
            lines.append(f'    module = "{s.module_hint}",')
        lines.append("  },")
    lines.append("}")
    lines.append("")
    lines.append("local function read_sig(sig)")
    lines.append("  if not (mem and mem.aob_scan and mem.read) then")
    lines.append("    error('需要 ASS mem.aob_scan / mem.read（root）')")
    lines.append("  end")
    lines.append("  local hit = mem.aob_scan(sig.pattern, sig.module)")
    lines.append("  if not hit then error('aob miss: ' .. sig.name) end")
    lines.append("  local base = type(hit) == 'number' and hit or tonumber(hit)")
    lines.append("  return mem.read(base + sig.offset, sig.type)")
    lines.append("end")
    lines.append("")
    lines.append("local out = {}")
    lines.append("for _, sig in ipairs(SIGS) do")
    lines.append("  local ok, val = pcall(read_sig, sig)")
    lines.append("  if ok then out[sig.name] = val else bot.log(tostring(val)) end")
    lines.append("end")
    lines.append("return out")
    lines.append("")
    return "\n".join(lines)


def save_lua_signatures(signatures: list[SavedSignature], output: str | Path, *, game_name: str = "game") -> Path:
    path = Path(output)
    path.write_text(signatures_to_lua(signatures, game_name=game_name), encoding="utf-8")
    return path


def build_ass_fields_table(
    *,
    chains: list[PointerChain],
    signatures: list[SavedSignature],
    android_package: str = "",
    game_name: str = "game",
    pointer_size: int = 8,
) -> dict:
    fields: list[dict] = []
    for i, c in enumerate(chains, 1):
        fields.append(
            {
                "name": c.export_name(i),
                "type": c.value_type or "int32",
                "kind": "chain",
                "module": c.module_name,
                "module_offset": c.module_offset,
                "offsets": list(c.offsets),
                "verified": c.verified,
            }
        )
    for s in signatures:
        fields.append(
            {
                "name": s.field_name,
                "type": s.value_type,
                "kind": "aob",
                "pattern": s.pattern,
                "offset_to_target": s.offset_to_target,
                "module_hint": s.module_hint,
                "verified": s.verified,
            }
        )
    return {
        "format": "ce-base-extractor/ass-fields-v1",
        "game": game_name,
        "android_package": android_package,
        "pointer_size": pointer_size,
        "fields": fields,
        "notes": "ASS: chain 用 bot.read_chain；aob 用 mem.aob_scan + mem.read（需 root）。",
    }


def save_ass_fields(
    result: ExtractResult,
    signatures: list[SavedSignature],
    output: str | Path,
    *,
    android_package: str = "",
    game_name: str = "game",
    pointer_size: int = 8,
) -> Path:
    path = Path(output)
    payload = build_ass_fields_table(
        chains=result.chains,
        signatures=signatures,
        android_package=android_package,
        game_name=game_name,
        pointer_size=pointer_size,
    )
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
