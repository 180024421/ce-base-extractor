"""游戏 Profile 版本对比与迁移建议。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ce_base_extractor.filters.fuzzy_dedupe import fuzzy_dedupe_key
from ce_base_extractor.models import PointerChain
from ce_base_extractor.profiles.store import GameProfile


def _chain_key(c: dict) -> tuple:
    return (
        str(c.get("module", "")).lower(),
        int(c.get("module_offset", 0)),
        tuple(int(o) for o in c.get("offsets", [])),
    )


def _fuzzy_key(c: dict, step: int = 0x8) -> tuple:
    chain = PointerChain(
        module_name=str(c.get("module", "")),
        module_offset=int(c.get("module_offset", 0)),
        offsets=tuple(int(o) for o in c.get("offsets", [])),
    )
    return fuzzy_dedupe_key(chain, last_offset_tolerance=step, ignore_last_offset=True)


@dataclass
class ProfileMigrationReport:
    unchanged: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    added: list[str] = field(default_factory=list)
    fuzzy_matched: list[tuple[str, str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "unchanged": self.unchanged,
            "removed": self.removed,
            "added": self.added,
            "fuzzy_matched": [{"old": a, "new": b} for a, b in self.fuzzy_matched],
        }


def compare_profiles(
    old: GameProfile,
    new: GameProfile,
    *,
    fuzzy_step: int = 0x8,
) -> ProfileMigrationReport:
    old_exact = {_chain_key(c): c.get("field_name", "") for c in old.chains}
    new_exact = {_chain_key(c): c.get("field_name", "") for c in new.chains}
    report = ProfileMigrationReport()

    matched_old_keys: set[tuple] = set()
    matched_new_keys: set[tuple] = set()

    for key, name in old_exact.items():
        if key in new_exact:
            report.unchanged.append(name or str(key))
            matched_old_keys.add(key)
            matched_new_keys.add(key)

    old_fuzzy: dict[tuple, tuple[tuple, str]] = {}
    for c in old.chains:
        fk = _fuzzy_key(c, fuzzy_step)
        if _chain_key(c) not in matched_old_keys:
            old_fuzzy[fk] = (_chain_key(c), c.get("field_name", ""))

    new_fuzzy: dict[tuple, tuple[tuple, str]] = {}
    for c in new.chains:
        fk = _fuzzy_key(c, fuzzy_step)
        if _chain_key(c) not in matched_new_keys:
            new_fuzzy[fk] = (_chain_key(c), c.get("field_name", ""))

    for fk, (old_key, old_name) in old_fuzzy.items():
        if fk in new_fuzzy:
            new_key, new_name = new_fuzzy[fk]
            report.fuzzy_matched.append((old_name or str(old_key), new_name or str(new_key)))
            matched_old_keys.add(old_key)
            matched_new_keys.add(new_key)

    for key, name in old_exact.items():
        if key not in matched_old_keys:
            report.removed.append(name or str(key))

    for key, name in new_exact.items():
        if key not in matched_new_keys:
            report.added.append(name or str(key))

    return report
