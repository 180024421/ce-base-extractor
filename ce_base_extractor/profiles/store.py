from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from ce_base_extractor.models import ExtractResult, PointerChain


def _profiles_dir() -> Path:
    p = Path.home() / "Documents" / "ce-exports" / "profiles"
    p.mkdir(parents=True, exist_ok=True)
    return p


@dataclass
class GameProfile:
    game_name: str
    preset: str = "ldplayer"
    pointer_size: int = 8
    target_pid: int | None = None
    chains: list[dict] = field(default_factory=list)
    updated_at: str = ""
    version: int = 1

    @classmethod
    def from_result(
        cls,
        result: ExtractResult,
        game_name: str,
        preset: str = "ldplayer",
        pointer_size: int = 8,
        target_pid: int | None = None,
    ) -> GameProfile:
        chains = []
        for i, c in enumerate(result.chains, 1):
            chains.append(
                {
                    "field_name": c.export_name(i),
                    "module": c.module_name,
                    "module_offset": c.module_offset,
                    "offsets": list(c.offsets),
                    "value_type": c.value_type,
                    "verified": c.verified,
                    "il2cpp_symbol": c.il2cpp_symbol,
                    "score": c.score,
                }
            )
        return cls(
            game_name=game_name,
            preset=preset,
            pointer_size=pointer_size,
            target_pid=target_pid,
            chains=chains,
            updated_at=datetime.now(timezone.utc).isoformat(),
        )

    def to_result(self, source: str = "profile") -> ExtractResult:
        chains = [
            PointerChain(
                module_name=c["module"],
                module_offset=int(c["module_offset"]),
                offsets=tuple(int(o) for o in c["offsets"]),
                score=float(c.get("score", 0)),
                source=source,
                field_name=c.get("field_name", ""),
                value_type=c.get("value_type", "int32"),
                verified=bool(c.get("verified", False)),
                il2cpp_symbol=c.get("il2cpp_symbol", ""),
            )
            for c in self.chains
        ]
        return ExtractResult(
            chains=chains,
            total_raw=len(chains),
            total_after_filter=len(chains),
            modules_seen=sorted({c.module_name for c in chains}),
            source_file=source,
        )


class ProfileStore:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or _profiles_dir()

    def _game_path(self, game_name: str) -> Path:
        return self.directory / f"{game_name}.json"

    def _versions_dir(self, game_name: str) -> Path:
        d = self.directory / game_name / "versions"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def list_games(self) -> list[str]:
        return sorted(p.stem for p in self.directory.glob("*.json"))

    def list_versions(self, game_name: str) -> list[str]:
        vdir = self.directory / game_name / "versions"
        if not vdir.is_dir():
            return []
        return sorted((p.stem for p in vdir.glob("*.json")), reverse=True)

    def save(self, profile: GameProfile) -> Path:
        existing = None
        path = self._game_path(profile.game_name)
        if path.is_file():
            try:
                existing = json.loads(path.read_text(encoding="utf-8"))
                profile.version = int(existing.get("version", 1)) + 1
            except (json.JSONDecodeError, TypeError):
                profile.version = 2
        else:
            profile.version = 1

        payload = asdict(profile)
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        version_path = self._versions_dir(profile.game_name) / f"{stamp}.json"
        version_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def load(self, game_name: str) -> GameProfile:
        data = json.loads(self._game_path(game_name).read_text(encoding="utf-8"))
        return GameProfile(**data)

    def load_version(self, game_name: str, version_id: str) -> GameProfile:
        path = self.directory / game_name / "versions" / f"{version_id}.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        return GameProfile(**data)

    def delete(self, game_name: str) -> None:
        self._game_path(game_name).unlink(missing_ok=True)
