from __future__ import annotations

from dataclasses import dataclass, field, fields


@dataclass
class PointerChain:
    """一条指针链：模块基址 + 偏移链。"""

    module_name: str
    module_offset: int
    offsets: tuple[int, ...]
    score: float = 0.0
    source: str = ""
    field_name: str = ""
    value_type: str = "int32"
    verified: bool = False
    il2cpp_symbol: str = ""

    @property
    def depth(self) -> int:
        return len(self.offsets)

    def export_name(self, fallback_index: int) -> str:
        return self.field_name.strip() or f"chain_{fallback_index}"

    def dedupe_key(self) -> tuple:
        return (
            self.module_name.lower(),
            self.module_offset,
            self.offsets,
        )


@dataclass
class ExtractConfig:
    max_depth: int = 5
    max_single_offset: int = 0x1000
    top_n: int = 20
    min_score: float = 0.0
    dedupe: bool = True
    emulator_mode: bool = True
    ptrid: int | None = None
    preset: str = "ldplayer"
    module_whitelist: list[str] | None = None
    module_blacklist: list[str] | None = None
    required_end_offset: int | None = None
    cross_validate_min: int = 2
    game_name: str = "game"
    pointer_size: int = 8
    target_pid: int | None = None
    il2cpp_map_path: str | None = None
    android_package: str = ""
    live_probe: bool = True
    probe_top_n: int = 10
    probe_drop_unreadable: bool = True
    fuzzy_dedupe: bool = True
    fuzzy_last_offset_step: int = 0x8
    cross_validate_require_all: bool = False
    cross_validate_fuzzy: bool = True
    sqlite_module_prefilter: bool = True
    stream_single_file: bool = True

    def validate(self) -> ExtractConfig:
        if self.top_n < 1:
            raise ValueError("top_n 必须 >= 1")
        if self.max_depth < 1:
            raise ValueError("max_depth 必须 >= 1")
        if self.pointer_size not in (4, 8):
            raise ValueError("pointer_size 必须为 4 或 8")
        if self.probe_top_n < 0:
            raise ValueError("probe_top_n 不能为负")
        if self.fuzzy_last_offset_step < 0:
            raise ValueError("fuzzy_last_offset_step 不能为负")
        return self

    @classmethod
    def from_dict(cls, data: dict) -> ExtractConfig:
        known = {f.name for f in fields(cls)}
        cfg = cls(**{k: v for k, v in data.items() if k in known})
        return cfg.validate()


@dataclass
class ExtractResult:
    chains: list[PointerChain]
    total_raw: int
    total_after_filter: int
    modules_seen: list[str]
    source_file: str
    ptrid: int | None = None
    cross_validate_meta: dict | None = None
    module_stats: list[dict] = field(default_factory=list)
    live_probe_meta: list[dict] | None = None
