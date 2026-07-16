"""特征码本地历史（Documents/ce-exports/sig-history）。"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path

from ce_base_extractor.signature import GeneratedSignature, SavedSignature


def _history_dir() -> Path:
    p = Path.home() / "Documents" / "ce-exports" / "sig-history"
    p.mkdir(parents=True, exist_ok=True)
    return p


def pattern_hash(pattern: str) -> str:
    return sha1(pattern.strip().encode("utf-8")).hexdigest()[:12]


def append_history(
    *,
    game: str,
    field_name: str,
    gen: GeneratedSignature,
    value_type: str = "int32",
    module_hint: str = "",
) -> Path:
    entry = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "game": game,
        "field_name": field_name,
        "value_type": value_type,
        "module_hint": module_hint,
        "pattern_hash": pattern_hash(gen.pattern),
        **gen.to_dict(),
    }
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = _history_dir() / f"{stamp}_{field_name}.json"
    path.write_text(json.dumps(entry, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def list_history(limit: int = 30) -> list[dict]:
    files = sorted(_history_dir().glob("*.json"), reverse=True)
    out: list[dict] = []
    for f in files[:limit]:
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            data["_path"] = str(f)
            out.append(data)
        except (json.JSONDecodeError, OSError):
            continue
    return out


def load_history_entry(path: str | Path) -> SavedSignature:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return SavedSignature(
        field_name=str(data.get("field_name") or "field"),
        pattern=str(data["pattern"]),
        offset_to_target=int(data["offset_to_target"]),
        value_type=str(data.get("value_type") or "int32"),
        module_hint=str(data.get("module_hint") or ""),
        verified=bool(data.get("verified", False)),
        sample_count=int(data.get("sample_count", 0)),
        fixed_bytes=int(data.get("fixed_bytes", 0)),
        notes=str(data.get("pattern_hash") or ""),
    )
