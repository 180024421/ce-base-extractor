"""监视目录时增量交叉验证，避免每次全量重读 SQLite。"""

from __future__ import annotations

from pathlib import Path

from ce_base_extractor.filters.cross_validate import cross_validate_files
from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key
from ce_base_extractor.filters.key_store import DEFAULT_SQLITE_THRESHOLD, ChainKeyCounter
from ce_base_extractor.models import PointerChain
from ce_base_extractor.parsers.chain_io import iter_file_chains


class IncrementalCrossValidator:
    def __init__(
        self,
        min_occurrences: int = 2,
        ptrid: int | None = None,
        *,
        fuzzy: bool = True,
        fuzzy_last_offset_step: int = 0x8,
        module_ids: set[int] | None = None,
        sqlite_threshold: int = DEFAULT_SQLITE_THRESHOLD,
        force_sqlite_backend: bool = False,
    ) -> None:
        self.min_occurrences = min_occurrences
        self.ptrid = ptrid
        self.fuzzy = fuzzy
        self.fuzzy_last_offset_step = fuzzy_last_offset_step
        self.module_ids = module_ids
        self._counter = ChainKeyCounter(
            sqlite_threshold=sqlite_threshold,
            force_sqlite=force_sqlite_backend,
        )
        self._files: list[str] = []

    def _key(self, chain: PointerChain) -> tuple:
        if self.fuzzy:
            return fuzzy_dedupe_key(
                chain,
                last_offset_tolerance=self.fuzzy_last_offset_step,
                ignore_last_offset=True,
            )
        return chain.dedupe_key()

    def add_file(self, path: str | Path) -> dict:
        path = Path(path)
        seen: dict[tuple, PointerChain] = {}
        before_unique = self._counter.unique_count()
        for chain in iter_file_chains(path, self.ptrid, module_ids=self.module_ids):
            key = self._key(chain)
            if key not in seen:
                seen[key] = chain
        self._counter.add_file_keys(seen)
        self._files.append(str(path.resolve()))
        return {
            "file": str(path),
            "new_unique_keys": self._counter.unique_count() - before_unique,
            "file_count": len(self._files),
            "stable_keys": len(self.stable_chains()),
        }

    def stable_chains(self) -> list[PointerChain]:
        total = len(self._files)
        out: list[PointerChain] = []
        for chain, count in self._counter.items_at_least(self.min_occurrences):
            out.append(
                PointerChain(
                    module_name=chain.module_name,
                    module_offset=chain.module_offset,
                    offsets=chain.offsets,
                    score=float(count),
                    source=f"cross_validate:{count}/{total}",
                )
            )
        return out

    def meta(self) -> dict:
        total = len(self._files)
        in_all = self._counter.count_in_all() if total else 0
        return {
            "files": list(self._files),
            "min_occurrences": self.min_occurrences,
            "unique_keys": self._counter.unique_count(),
            "stable_keys": len(self.stable_chains()),
            "in_all": in_all,
            "stability_ratio": round(in_all / max(self._counter.unique_count(), 1), 4),
            "streaming": True,
            "incremental": True,
            "fuzzy": self.fuzzy,
            "key_backend": self._counter.backend,
        }

    def close(self) -> None:
        self._counter.close()

    def cross_validate_via_batch(self) -> tuple[list[PointerChain], dict]:
        """将已累积文件作为批量交叉验证（复用 cross_validate_files）。"""
        return cross_validate_files(
            self._files,
            min_occurrences=self.min_occurrences,
            ptrid=self.ptrid,
            module_ids=self.module_ids,
            fuzzy=self.fuzzy,
            fuzzy_last_offset_step=self.fuzzy_last_offset_step,
            force_sqlite_backend=self._counter.backend == "sqlite",
        )
