from __future__ import annotations

import struct
from pathlib import Path

from ce_base_extractor.models import PointerChain


def _align4(offset: int) -> int:

    return (offset + 3) & ~3


def _read_bitfield(data: bytes, bit_offset: int, bit_count: int) -> int:

    if bit_count <= 0:
        return 0

    byte_index = bit_offset >> 3

    shift = bit_offset & 7

    value = 0

    bits_read = 0

    while bits_read < bit_count:
        if byte_index >= len(data):
            break

        chunk = data[byte_index]

        take = min(8 - shift, bit_count - bits_read)

        value |= ((chunk >> shift) & ((1 << take) - 1)) << bits_read

        bits_read += take

        byte_index += 1

        shift = 0

    return value


def _parse_header(data: bytes) -> tuple[dict, int]:

    offset = 0

    version = data[offset]

    offset += 1

    if version not in range(1, 9):
        raise ValueError(f"不支持的 PTR 版本: {version}")

    _external = struct.unpack_from("<I", data, offset)[0]

    offset += 4

    _worker = struct.unpack_from("<I", data, offset)[0]

    offset += 4

    compressed = data[offset]

    offset += 1

    aligned = data[offset]

    offset += 1

    max_bits = struct.unpack_from("<4I", data, offset)

    offset += 16

    ends_count = struct.unpack_from("<I", data, offset)[0]

    offset += 4

    ends_with = list(struct.unpack_from(f"<{ends_count}I", data, offset)) if ends_count else []

    offset += ends_count * 4

    module_count = struct.unpack_from("<I", data, offset)[0]

    offset += 4

    modules: list[str] = []

    for _ in range(module_count):
        name_len = struct.unpack_from("<I", data, offset)[0]

        offset += 4

        name = data[offset : offset + name_len].decode("utf-8", errors="replace")

        offset += name_len

        offset += 8

        modules.append(name)

        offset = _align4(offset)

    maxlevel = struct.unpack_from("<I", data, offset)[0]

    offset += 4

    masks = [((1 << b) - 1) if b else 0 for b in max_bits]

    return {
        "version": version,
        "compressed": bool(compressed),
        "aligned": bool(aligned),
        "modules": modules,
        "maxlevel": maxlevel,
        "max_bits": max_bits,
        "masks": masks,
        "ends_with": ends_with,
        "header_end": offset,
    }, offset


def _parse_compressed_entry(
    data: bytes,
    offset: int,
    header: dict,
) -> tuple[PointerChain | None, int]:

    max_bits = header["max_bits"]

    _masks = header["masks"]

    _maxlevel = header["maxlevel"]

    ends_with: list[int] = header["ends_with"]

    aligned = header["aligned"]

    entry_size = (sum(max_bits) + 7) // 8

    if offset + entry_size > len(data):
        return None, offset

    chunk = data[offset : offset + entry_size]

    bit = 0

    if max_bits[1] == 32:
        module_offset = _read_bitfield(chunk, bit, 32)

        if module_offset & 0x80000000:
            module_offset = module_offset - (1 << 32)

    else:
        module_offset = _read_bitfield(chunk, bit, max_bits[1])

    bit += max_bits[1]

    modulenr = _read_bitfield(chunk, bit, max_bits[0])

    if modulenr and (modulenr >> (max_bits[0] - 1)) == 1:
        modulenr = modulenr - (1 << max_bits[0])

    bit += max_bits[0]

    offsetcount = _read_bitfield(chunk, bit, max_bits[2]) + len(ends_with)

    bit += max_bits[2]

    offsets: list[int] = list(ends_with)

    for _ in range(len(ends_with), offsetcount):
        val = _read_bitfield(chunk, bit, max_bits[3])

        if aligned:
            val <<= 2

        offsets.append(val)

        bit += max_bits[3]

    if modulenr == -1:
        module_name = "<absolute>"

    elif 0 <= modulenr < len(header["modules"]):
        module_name = header["modules"][modulenr]

    else:
        module_name = f"<module#{modulenr}>"

    chain = PointerChain(
        module_name=module_name,
        module_offset=int(module_offset),
        offsets=tuple(offsets[:offsetcount]),
        source="ptr-compressed",
    )

    return chain, offset + entry_size


def _parse_plain_entry(data: bytes, offset: int, header: dict) -> tuple[PointerChain | None, int]:

    maxlevel = header["maxlevel"]

    entry_size = 4 + 8 + 4 + maxlevel * 4

    if offset + entry_size > len(data):
        return None, offset

    modulenr = struct.unpack_from("<i", data, offset)[0]

    moduleoffset = struct.unpack_from("<q", data, offset + 4)[0]

    offsetcount = struct.unpack_from("<I", data, offset + 12)[0]

    raw = struct.unpack_from(f"<{maxlevel}i", data, offset + 16)

    offsets = tuple(int(x) for x in raw[:offsetcount])

    if modulenr == -1:
        module_name = "<absolute>"

    elif 0 <= modulenr < len(header["modules"]):
        module_name = header["modules"][modulenr]

    else:
        module_name = f"<module#{modulenr}>"

    return (
        PointerChain(
            module_name=module_name,
            module_offset=int(moduleoffset),
            offsets=offsets,
            source="ptr",
        ),
        offset + entry_size,
    )


def load_ptr(path: str | Path) -> tuple[list[PointerChain], dict]:

    ptr_path = Path(path)

    if not ptr_path.is_file():
        raise FileNotFoundError(f"文件不存在: {ptr_path}")

    data = ptr_path.read_bytes()

    header, offset = _parse_header(data)

    chains: list[PointerChain] = []

    parse_fn = _parse_compressed_entry if header["compressed"] else _parse_plain_entry

    entry_size_hint = (
        (sum(header["max_bits"]) + 7) // 8
        if header["compressed"]
        else (4 + 8 + 4 + header["maxlevel"] * 4)
    )

    while offset + entry_size_hint <= len(data):
        chain, new_offset = parse_fn(data, offset, header)

        if chain is None or new_offset <= offset:
            break

        chains.append(chain)

        offset = new_offset

    meta = {
        "module_count": len(header["modules"]),
        "modules": header["modules"],
        "result_count": len(chains),
        "version": header["version"],
        "compressed": header["compressed"],
    }

    return chains, meta
