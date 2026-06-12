from ce_base_extractor.models import PointerChain
from ce_base_extractor.profiles.store import GameProfile, ProfileStore


def test_profile_roundtrip(tmp_path):
    chains = [PointerChain("libil2cpp.so", 0x1000, (0x18,), field_name="gold", value_type="int32")]
    from ce_base_extractor.models import ExtractResult

    result = ExtractResult(
        chains=chains,
        total_raw=1,
        total_after_filter=1,
        modules_seen=["libil2cpp.so"],
        source_file="test",
    )
    store = ProfileStore(tmp_path)
    profile = GameProfile.from_result(result, "demo")
    store.save(profile)
    loaded = store.load("demo")
    back = loaded.to_result()
    assert back.chains[0].field_name == "gold"
