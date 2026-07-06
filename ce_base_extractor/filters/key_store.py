"""大规模交叉验证用的键计数存储（内存 Counter / SQLite  spill）。"""

from __future__ import annotations

import json
import sqlite3
import tempfile
from collections import Counter
from dataclasses import dataclass

from ce_base_extractor.models import PointerChain

DEFAULT_SQLITE_THRESHOLD = 200_000


def serialize_key(key: tuple) -> str:
    return json.dumps(key, separators=(",", ":"))


def deserialize_key(text: str) -> tuple:
    return tuple(json.loads(text))


@dataclass
class ChainKeyCounter:
    """统计指针链 dedupe 键在多份扫描中的出现次数。"""

    sqlite_threshold: int = DEFAULT_SQLITE_THRESHOLD
    force_sqlite: bool = False
    db_path: str | None = None

    def __post_init__(self) -> None:
        self._use_sqlite = self.force_sqlite
        self._memory_counter: Counter[str] = Counter()
        self._memory_exemplar: dict[str, PointerChain] = {}
        self._conn: sqlite3.Connection | None = None
        self._file_count = 0

    def _open_sqlite(self) -> sqlite3.Connection:
        if self._conn is None:
            path = self.db_path or ":memory:"
            self._conn = sqlite3.connect(path)
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS chain_keys ("
                "key TEXT PRIMARY KEY, cnt INTEGER NOT NULL, exemplar TEXT NOT NULL)"
            )
        return self._conn

    def _migrate_to_sqlite(self) -> None:
        if self._use_sqlite:
            return
        conn = self._open_sqlite()
        for key_str, count in self._memory_counter.items():
            exemplar = self._memory_exemplar[key_str]
            conn.execute(
                "INSERT INTO chain_keys(key, cnt, exemplar) VALUES (?, ?, ?)"
                " ON CONFLICT(key) DO UPDATE SET cnt=cnt+excluded.cnt",
                (key_str, count, _chain_to_json(exemplar)),
            )
        conn.commit()
        self._memory_counter.clear()
        self._memory_exemplar.clear()
        self._use_sqlite = True

    def add_file_keys(self, keys: dict[tuple, PointerChain]) -> None:
        """keys: 单文件内去重后的 key -> exemplar。"""
        self._file_count += 1
        if not self._use_sqlite and len(self._memory_counter) + len(keys) > self.sqlite_threshold:
            self._migrate_to_sqlite()

        if self._use_sqlite:
            conn = self._open_sqlite()
            for key, chain in keys.items():
                key_str = serialize_key(key)
                row = conn.execute("SELECT cnt FROM chain_keys WHERE key=?", (key_str,)).fetchone()
                if row:
                    conn.execute("UPDATE chain_keys SET cnt=cnt+1 WHERE key=?", (key_str,))
                else:
                    conn.execute(
                        "INSERT INTO chain_keys(key, cnt, exemplar) VALUES (?, 1, ?)",
                        (key_str, _chain_to_json(chain)),
                    )
            conn.commit()
            return

        for key, chain in keys.items():
            key_str = serialize_key(key)
            self._memory_counter[key_str] += 1
            if key_str not in self._memory_exemplar:
                self._memory_exemplar[key_str] = chain

    def items_at_least(self, min_count: int) -> list[tuple[PointerChain, int]]:
        out: list[tuple[PointerChain, int]] = []
        if self._use_sqlite:
            conn = self._open_sqlite()
            for key_str, cnt, exemplar_json in conn.execute(
                "SELECT key, cnt, exemplar FROM chain_keys WHERE cnt >= ?", (min_count,)
            ):
                out.append((_chain_from_json(exemplar_json), int(cnt)))
            return out

        for key_str, cnt in self._memory_counter.items():
            if cnt >= min_count:
                out.append((self._memory_exemplar[key_str], int(cnt)))
        return out

    def count_in_all(self) -> int:
        n = self._file_count
        if n == 0:
            return 0
        if self._use_sqlite:
            conn = self._open_sqlite()
            row = conn.execute("SELECT COUNT(*) FROM chain_keys WHERE cnt=?", (n,)).fetchone()
            return int(row[0]) if row else 0
        return sum(1 for c in self._memory_counter.values() if c == n)

    def unique_count(self) -> int:
        if self._use_sqlite:
            conn = self._open_sqlite()
            row = conn.execute("SELECT COUNT(*) FROM chain_keys").fetchone()
            return int(row[0]) if row else 0
        return len(self._memory_counter)

    @property
    def file_count(self) -> int:
        return self._file_count

    @property
    def backend(self) -> str:
        return "sqlite" if self._use_sqlite else "memory"

    def close(self) -> None:
        if self._conn is not None:
            self._conn.close()
            self._conn = None


def _chain_to_json(chain: PointerChain) -> str:
    return json.dumps(
        {
            "module_name": chain.module_name,
            "module_offset": chain.module_offset,
            "offsets": list(chain.offsets),
            "source": chain.source,
        }
    )


def _chain_from_json(text: str) -> PointerChain:
    data = json.loads(text)
    return PointerChain(
        module_name=data["module_name"],
        module_offset=int(data["module_offset"]),
        offsets=tuple(int(o) for o in data["offsets"]),
        source=data.get("source", ""),
    )


def temp_key_counter(**kwargs) -> ChainKeyCounter:
    """磁盘临时库，适合超大 union 键空间。"""
    tmp = tempfile.NamedTemporaryFile(suffix=".keys.sqlite", delete=False)
    tmp.close()
    return ChainKeyCounter(force_sqlite=True, db_path=tmp.name, **kwargs)
