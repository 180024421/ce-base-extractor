"""监视目录时增量交叉验证，避免每次全量重读 SQLite。"""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key
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
    ) -> None:
        self.min_occurrences = min_occurrences
        self.ptrid = ptrid
        self.fuzzy = fuzzy
        self.fuzzy_last_offset_step = fuzzy_last_offset_step
        self.module_ids = module_ids
        self._counter: Counter[tuple] = Counter()
        self._exemplar: dict[tuple, PointerChain] = {}
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
        seen: set[tuple] = set()
        added_keys = 0
        for chain in iter_file_chains(path, self.ptrid, module_ids=self.module_ids):
            key = self._key(chain)
            if key in seen:
                continue
            seen.add(key)
            if self._counter[key] == 0:
                added_keys += 1
            self._counter[key] += 1
            if key not in self._exemplar:
                self._exemplar[key] = chain
        self._files.append(str(path.resolve()))
        return {
            "file": str(path),
            "new_unique_keys": added_keys,
            "file_count": len(self._files),
            "stable_keys": len(self.stable_chains()),
        }

    def stable_chains(self) -> list[PointerChain]:
        total = len(self._files)
        out: list[PointerChain] = []
        for key, count in self._counter.items():
            if count >= self.min_occurrences:
                chain = self._exemplar[key]
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
        in_all = sum(1 for c in self._counter.values() if c == total) if total else 0
        return {
            "files": list(self._files),
            "min_occurrences": self.min_occurrences,
            "unique_keys": len(self._counter),
            "stable_keys": len(self.stable_chains()),
            "in_all": in_all,
            "stability_ratio": round(in_all / max(len(self._counter), 1), 4),
            "streaming": True,
            "incremental": True,
            "fuzzy": self.fuzzy,
        }
