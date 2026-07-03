"""游戏 Profile 版本对比与迁移建议。"""

from __future__ import annotations

from dataclasses import dataclass, field

from ce_base_extractor.profiles.store import GameProfile


def _chain_key(c: dict) -> tuple:
    return (
        str(c.get("module", "")).lower(),
        int(c.get("module_offset", 0)),
        tuple(int(o) for o in c.get("offsets", [])),
    )


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


def compare_profiles(old: GameProfile, new: GameProfile) -> ProfileMigrationReport:
    old_map = {_chain_key(c): c.get("field_name", "") for c in old.chains}
    new_map = {_chain_key(c): c.get("field_name", "") for c in new.chains}
    report = ProfileMigrationReport()

    for key, name in old_map.items():
        if key in new_map:
            report.unchanged.append(name or str(key))
        else:
            report.removed.append(name or str(key))

    for key, name in new_map.items():
        if key not in old_map:
            report.added.append(name or str(key))

    return report
