"""特征码（AOB）生成、精简与扫描辅助。"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Callable

_HEX_TOKEN = re.compile(r"^(?:[0-9A-Fa-f]{2}|\?\?|\?)$")


@dataclass
class SignatureSample:
    address: int
    data: bytes
    before: int
    after: int
    note: str = ""

    @property
    def window_size(self) -> int:
        return self.before + self.after

    def to_dict(self) -> dict:
        return {
            "address": self.address,
            "address_hex": f"0x{self.address:X}",
            "before": self.before,
            "after": self.after,
            "note": self.note,
            "data_hex": self.data.hex(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> SignatureSample:
        raw = data.get("data_hex") or data.get("data") or ""
        if isinstance(raw, bytes):
            blob = raw
        else:
            blob = bytes.fromhex(str(raw))
        return cls(
            address=int(data.get("address", 0)),
            data=blob,
            before=int(data["before"]),
            after=int(data["after"]),
            note=str(data.get("note", "")),
        )


@dataclass
class GeneratedSignature:
    pattern: str
    offset_to_target: int
    fixed_bytes: int
    wildcard_bytes: int
    sample_count: int
    window_before: int
    window_after: int
    warnings: list[str] = field(default_factory=list)
    minimized: bool = False

    def pattern_bytes_and_mask(self) -> tuple[bytes, bytes]:
        return parse_pattern(self.pattern)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> GeneratedSignature:
        return cls(
            pattern=str(data["pattern"]),
            offset_to_target=int(data["offset_to_target"]),
            fixed_bytes=int(data.get("fixed_bytes", 0)),
            wildcard_bytes=int(data.get("wildcard_bytes", 0)),
            sample_count=int(data.get("sample_count", 0)),
            window_before=int(data.get("window_before", 0)),
            window_after=int(data.get("window_after", 0)),
            warnings=list(data.get("warnings") or []),
            minimized=bool(data.get("minimized", False)),
        )


@dataclass
class SavedSignature:
    """写入 Profile / 导出用的命名特征码。"""

    field_name: str
    pattern: str
    offset_to_target: int
    value_type: str = "int32"
    module_hint: str = ""
    verified: bool = False
    sample_count: int = 0
    fixed_bytes: int = 0
    notes: str = ""
    pattern_hash: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        if not d.get("pattern_hash") and self.pattern:
            from hashlib import sha1

            d["pattern_hash"] = sha1(self.pattern.strip().encode("utf-8")).hexdigest()[:12]
        return d

    @classmethod
    def from_dict(cls, data: dict) -> SavedSignature:
        return cls(
            field_name=str(data.get("field_name") or data.get("name") or "field"),
            pattern=str(data["pattern"]),
            offset_to_target=int(data["offset_to_target"]),
            value_type=str(data.get("value_type") or data.get("type") or "int32"),
            module_hint=str(data.get("module_hint") or data.get("module") or ""),
            verified=bool(data.get("verified", False)),
            sample_count=int(data.get("sample_count", 0)),
            fixed_bytes=int(data.get("fixed_bytes", 0)),
            notes=str(data.get("notes", "")),
            pattern_hash=str(data.get("pattern_hash", "")),
        )


def parse_address(text: str) -> int:
    raw = text.strip().replace("_", "")
    if not raw:
        raise ValueError("地址为空")
    return int(raw, 0)


def parse_pattern(pattern: str) -> tuple[bytes, bytes]:
    tokens = pattern.replace(",", " ").split()
    if not tokens:
        raise ValueError("特征码为空")
    values = bytearray()
    mask = bytearray()
    for tok in tokens:
        if not _HEX_TOKEN.match(tok):
            raise ValueError(f"非法特征码片段: {tok}")
        if tok in ("?", "??"):
            values.append(0)
            mask.append(0)
        else:
            values.append(int(tok, 16))
            mask.append(0xFF)
    return bytes(values), bytes(mask)


def format_pattern(values: bytes, mask: bytes) -> str:
    if len(values) != len(mask):
        raise ValueError("values/mask 长度不一致")
    return " ".join("??" if m == 0 else f"{v:02X}" for v, m in zip(values, mask, strict=True))


def generate_from_samples(
    samples: list[SignatureSample],
    *,
    min_samples: int = 3,
    min_fixed_bytes: int = 4,
) -> GeneratedSignature:
    """多样本对比生成特征码。样本可来自多次重启，或同进程多个同类地址。"""
    if len(samples) < min_samples:
        raise ValueError(f"至少需要 {min_samples} 个样本，当前 {len(samples)}")

    before = samples[0].before
    after = samples[0].after
    size = before + after
    if size <= 0:
        raise ValueError("窗口大小无效")

    for i, s in enumerate(samples):
        if s.before != before or s.after != after:
            raise ValueError(f"样本 {i + 1} 窗口与首样本不一致")
        if len(s.data) != size:
            raise ValueError(f"样本 {i + 1} 数据长度应为 {size}，实际 {len(s.data)}")

    values = bytearray(size)
    mask = bytearray(size)
    for i in range(size):
        col = {s.data[i] for s in samples}
        if len(col) == 1:
            values[i] = next(iter(col))
            mask[i] = 0xFF
        else:
            values[i] = 0
            mask[i] = 0

    start = 0
    while start < size and mask[start] == 0:
        start += 1
    end = size
    while end > start and mask[end - 1] == 0:
        end -= 1
    if start >= end:
        raise ValueError("对比后无可固定字节，请加大窗口或核对地址是否同类")

    trimmed_v = bytes(values[start:end])
    trimmed_m = bytes(mask[start:end])
    fixed = sum(1 for m in trimmed_m if m)
    wild = len(trimmed_m) - fixed
    offset_to_target = before - start

    warnings: list[str] = []
    if fixed < min_fixed_bytes:
        warnings.append(f"固定字节仅 {fixed} 个，特征可能不够稳，建议再采样本或加大窗口")
    if wild > fixed * 2:
        warnings.append("通配字节偏多，建议增加样本数（重启或同局多地址）")

    return GeneratedSignature(
        pattern=format_pattern(trimmed_v, trimmed_m),
        offset_to_target=offset_to_target,
        fixed_bytes=fixed,
        wildcard_bytes=wild,
        sample_count=len(samples),
        window_before=before,
        window_after=after,
        warnings=warnings,
    )


def find_pattern_in_buffer(
    buffer: bytes,
    pattern: bytes,
    mask: bytes,
    *,
    base_address: int = 0,
    max_hits: int = 64,
) -> list[int]:
    if not pattern or len(pattern) != len(mask):
        raise ValueError("pattern/mask 无效")
    plen = len(pattern)
    if plen > len(buffer):
        return []
    hits: list[int] = []
    limit = len(buffer) - plen + 1
    for i in range(limit):
        ok = True
        for j in range(plen):
            if mask[j] and buffer[i + j] != pattern[j]:
                ok = False
                break
        if ok:
            hits.append(base_address + i)
            if len(hits) >= max_hits:
                break
    return hits


def count_hits(
    count_fn: Callable[[str], int],
    pattern: str,
    *,
    max_acceptable: int = 1,
) -> int:
    return count_fn(pattern)


def minimize_unique_pattern(
    gen: GeneratedSignature,
    count_fn: Callable[[str], int],
    *,
    min_fixed: int = 4,
    max_hits: int = 1,
) -> GeneratedSignature:
    """在保证命中数 ≤ max_hits 的前提下，裁成更短特征码。"""
    values, mask = parse_pattern(gen.pattern)
    n = len(values)
    if n == 0:
        return gen

    best_pattern = gen.pattern
    best_len = n
    best_offset = gen.offset_to_target
    best_fixed = gen.fixed_bytes

    # 从两端向内收缩，再尝试滑动窗口子串
    candidates: list[tuple[int, int]] = []
    for left in range(n):
        for right in range(n, left, -1):
            fixed = sum(1 for m in mask[left:right] if m)
            if fixed < min_fixed:
                continue
            candidates.append((left, right))

    # 优先尝试更短的
    candidates.sort(key=lambda lr: (lr[1] - lr[0], lr[0]))

    for left, right in candidates:
        sub_v = values[left:right]
        sub_m = mask[left:right]
        # 裁首尾通配
        s = 0
        while s < len(sub_m) and sub_m[s] == 0:
            s += 1
        e = len(sub_m)
        while e > s and sub_m[e - 1] == 0:
            e -= 1
        if s >= e:
            continue
        sub_v = sub_v[s:e]
        sub_m = sub_m[s:e]
        fixed = sum(1 for m in sub_m if m)
        if fixed < min_fixed:
            continue
        pat = format_pattern(sub_v, sub_m)
        try:
            hits = count_fn(pat)
        except Exception:
            continue
        if 0 < hits <= max_hits and len(sub_v) < best_len:
            best_pattern = pat
            best_len = len(sub_v)
            # 原 offset：命中点 + offset = 目标
            # 子串相对原 pattern 起点多了 left+s
            best_offset = gen.offset_to_target - (left + s)
            best_fixed = fixed

    if best_pattern == gen.pattern:
        return gen

    wild = best_len - best_fixed
    warnings = list(gen.warnings)
    warnings.append(f"已精简为最短唯一特征码（长度 {best_len}）")
    return GeneratedSignature(
        pattern=best_pattern,
        offset_to_target=best_offset,
        fixed_bytes=best_fixed,
        wildcard_bytes=wild,
        sample_count=gen.sample_count,
        window_before=gen.window_before,
        window_after=gen.window_after,
        warnings=warnings,
        minimized=True,
    )


def samples_to_json(samples: list[SignatureSample]) -> str:
    return json.dumps(
        {"format": "ce-base-extractor/sig-samples-v1", "samples": [s.to_dict() for s in samples]},
        ensure_ascii=False,
        indent=2,
    )


def samples_from_json(text: str) -> list[SignatureSample]:
    data = json.loads(text)
    items = data.get("samples") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("样本 JSON 格式无效")
    return [SignatureSample.from_dict(x) for x in items]


def save_samples(samples: list[SignatureSample], path: str | Path) -> Path:
    p = Path(path)
    p.write_text(samples_to_json(samples), encoding="utf-8")
    return p


def load_samples(path: str | Path) -> list[SignatureSample]:
    return samples_from_json(Path(path).read_text(encoding="utf-8"))
