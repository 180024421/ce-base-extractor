import struct
from pathlib import Path

from ce_base_extractor.models import PointerChain
from ce_base_extractor.parsers.ptr_parser import iter_ptr_chains, load_ptr


def _make_ptr(tmp_path: Path, compressed: bool, count: int = 3) -> Path:
    """构造最小可读 PTR 文件（plain 格式）。"""
    path = tmp_path / ("test-compressed.ptr" if compressed else "test-plain.ptr")
    modules = ["libil2cpp.so"]
    maxlevel = 4
    ends_with: list[int] = []
    max_bits = (8, 32, 4, 16)
    header = bytearray()
    header.append(1)  # version
    header += struct.pack("<I", 0)  # external
    header += struct.pack("<I", 0)  # worker
    header.append(1 if compressed else 0)
    header.append(0)  # aligned
    header += struct.pack("<4I", *max_bits)
    header += struct.pack("<I", len(ends_with))
    for e in ends_with:
        header += struct.pack("<I", e)
    header += struct.pack("<I", len(modules))
    for name in modules:
        nb = name.encode("utf-8")
        header += struct.pack("<I", len(nb))
        header += nb
        header += struct.pack("<q", 0)
        while len(header) % 4:
            header.append(0)
    header += struct.pack("<I", maxlevel)

    body = bytearray()
    if compressed:
        entry_size = (sum(max_bits) + 7) // 8
        for i in range(count):
            chunk = bytearray(entry_size)
            body += chunk
    else:
        entry_size = 4 + 8 + 4 + maxlevel * 4
        for i in range(count):
            modulenr = 0
            moduleoffset = 0x1000 + i * 0x100
            offsetcount = 2
            offsets = (0x18, 0x20) + (0,) * (maxlevel - 2)
            body += struct.pack("<i", modulenr)
            body += struct.pack("<q", moduleoffset)
            body += struct.pack("<I", offsetcount)
            body += struct.pack(f"<{maxlevel}i", *offsets)

    path.write_bytes(bytes(header) + bytes(body))
    return path


def test_iter_ptr_plain(tmp_path):
    p = _make_ptr(tmp_path, compressed=False, count=2)
    chains = list(iter_ptr_chains(p))
    assert len(chains) == 2
    assert chains[0].module_name == "libil2cpp.so"
    _, meta = load_ptr(p)
    assert meta["mmap"] is True


def test_chain_key_counter_spill():
    from ce_base_extractor.filters.key_store import ChainKeyCounter

    counter = ChainKeyCounter(sqlite_threshold=2, force_sqlite=False)
    shared_key = ("libil2cpp.so", 0x1000, (0x10, 0x20))
    chain = PointerChain("libil2cpp.so", 0x1000, (0x10, 0x20))
    try:
        for _ in range(3):
            counter.add_file_keys({shared_key: chain})
        assert counter.unique_count() == 1
        assert counter.file_count == 3
        assert counter.backend == "memory"
        stable = counter.items_at_least(2)
        assert len(stable) == 1
        assert stable[0][1] == 3

        counter2 = ChainKeyCounter(sqlite_threshold=1, force_sqlite=False)
        try:
            for i in range(4):
                counter2.add_file_keys(
                    {(f"m{i}", 0x1000 + i, (0x10,)): PointerChain("m", 0x1000 + i, (0x10,))}
                )
            assert counter2.backend == "sqlite"
            assert counter2.unique_count() == 4
        finally:
            counter2.close()
    finally:
        counter.close()


def test_cross_validate_sqlite_backend(tmp_path):
    from ce_base_extractor.filters.cross_validate import cross_validate_files

    def _db(name, off):
        import sqlite3

        db = tmp_path / name
        conn = sqlite3.connect(db)
        conn.execute(
            "CREATE TABLE pointerfiles (ptrid INTEGER PRIMARY KEY, name TEXT, maxlevel INTEGER)"
        )
        conn.execute("INSERT INTO pointerfiles VALUES (1, 'scan', 4)")
        conn.execute(
            "CREATE TABLE modules (ptrid INTEGER, moduleid INTEGER, name TEXT, PRIMARY KEY (ptrid, moduleid))"
        )
        conn.execute("INSERT INTO modules VALUES (1, 0, 'libil2cpp.so')")
        conn.execute(
            "CREATE TABLE results (ptrid INTEGER, resultid INTEGER, offsetcount INTEGER, "
            "moduleid INTEGER, moduleoffset BIGINT, offset1 INTEGER, offset2 INTEGER, "
            "PRIMARY KEY (ptrid, resultid))"
        )
        conn.execute(
            "INSERT INTO results VALUES (1, 1, 2, 0, ?, 0x18, 0x20)",
            (off,),
        )
        conn.commit()
        conn.close()
        return db

    db1 = _db("a.sqlite", 0x1000)
    db2 = _db("b.sqlite", 0x1000)
    stable, meta = cross_validate_files([db1, db2], force_sqlite_backend=True)
    assert len(stable) == 1
    assert meta["key_backend"] == "sqlite"
