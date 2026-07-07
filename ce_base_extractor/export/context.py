"""导出上下文：从 Profile 加载 snapshots / android_package。"""

from __future__ import annotations

from ce_base_extractor.profiles.store import ProfileStore, _snapshot_encode


def load_export_context(
    game_name: str,
    *,
    session_values: dict[str, object] | None = None,
    android_fallback: str = "",
) -> tuple[dict[str, dict] | None, str]:
    """返回 (snapshots, android_package)，无 profile 时可用 session_values 兜底。"""
    snapshots: dict[str, dict] | None = None
    android_package = android_fallback or ""
    if game_name and game_name != "game":
        try:
            profile = ProfileStore().load(game_name)
            snapshots = profile.snapshots or None
            android_package = profile.android_package or android_package
        except FileNotFoundError:
            pass
    if session_values and not snapshots:
        snapshots = {
            name: {"value": _snapshot_encode(val)} for name, val in session_values.items()
        }
    return snapshots, android_package
