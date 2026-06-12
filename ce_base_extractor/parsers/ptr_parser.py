from __future__ import annotations

import struct
from pathlib import Path

from ce_base_extractor.models import PointerChain


def _read_cstring(data: bytes, offset: int) -> tuple[str, int]:
    end = data.index(b"\x00", offset)
    return data[offset:end].decode("utf-8", errors="replace"), end + 1


def _align4(offset: int) -> int:
    return (offset + 3) & ~3


def load_ptr(path: str | Path) -> tuple[list[PointerChain], dict]:
    """解析 CE 指针扫描 .PTR 文件（非压缩格式）。"""
    ptr_path = Path(path)
    if not ptr_path.is_file():
        raise FileNotFoundError(f"文件不存在: {ptr_path}")

    data = ptr_path.read_bytes()
    if len(data) < 8:
        raise ValueError("PTR 文件过短或已损坏")

    offset = 0
    version = data[offset]
    offset += 1
    if version not in (1, 2, 3, 4, 5, 6, 7, 8):
        raise ValueError(f"不支持的 PTR 版本: {version}")

    # 跳过头部标志与 maxlevel 等字段，定位模块列表
    # 参考 CE PointerscanresultReader.create 的读取顺序（简化版，适用于常见导出）
    offset += 4  # external scanners
    offset += 4  # worker id
    compressed = data[offset]
    offset += 1
    if compressed:
        raise ValueError("当前仅支持非压缩 PTR，请在 CE 导出时关闭 compressedptr")

    offset += 1  # aligned
    offset += 4  # max bit counts (x4)
    offset += 4  # ends with offset list count
    ends_count = struct.unpack_from("<I", data, offset - 4)[0]
    offset += ends_count * 4

    module_count = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    modules: list[str] = []
    for _ in range(module_count):
        name_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        name = data[offset : offset + name_len].decode("utf-8", errors="replace")
        offset += name_len
        offset += 8  # module base (qword), 解析时不需要
        modules.append(name)
        offset = _align4(offset)

    maxlevel = struct.unpack_from("<I", data, offset)[0]
    offset += 4
    entry_size = 4 + 8 + 4 + maxlevel * 4  # modulenr + moduleoffset + offsetcount + offsets

    chains: list[PointerChain] = []
    while offset + entry_size <= len(data):
        modulenr = struct.unpack_from("<i", data, offset)[0]
        moduleoffset = struct.unpack_from("<q", data, offset + 4)[0]
        offsetcount = struct.unpack_from("<I", data, offset + 12)[0]
        raw = struct.unpack_from(f"<{maxlevel}i", data, offset + 16)
        offsets = tuple(int(x) for x in raw[:offsetcount])

        if modulenr == -1:
            module_name = "<absolute>"
        elif 0 <= modulenr < len(modules):
            module_name = modules[modulenr]
        else:
            module_name = f"<module#{modulenr}>"

        chains.append(
            PointerChain(
                module_name=module_name,
                module_offset=int(moduleoffset),
                offsets=offsets,
                source="ptr",
            )
        )
        offset += entry_size

    meta = {
        "module_count": len(modules),
        "modules": modules,
        "result_count": len(chains),
        "version": version,
    }
    return chains, meta
