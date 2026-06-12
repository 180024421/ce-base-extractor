from __future__ import annotations

from dataclasses import dataclass, field, fields


@dataclass(frozen=True)
class PointerChain:
    """一条指针链：模块基址 + 偏移链。"""

    module_name: str
    module_offset: int
    offsets: tuple[int, ...]
    score: float = 0.0
    source: str = ""

    @property
    def depth(self) -> int:
        return len(self.offsets)

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
    cross_validate_min: int = 0
    game_name: str = "game"

    @classmethod
    def from_dict(cls, data: dict) -> ExtractConfig:
        known = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in known})


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
