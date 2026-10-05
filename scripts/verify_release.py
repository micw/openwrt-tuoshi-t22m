#!/usr/bin/env python3
"""Accept only the three requested firmware binaries from two isolated builds."""
from pathlib import Path
import sys

EXPECTED = {
    "openwrt-ramips-mt76x8-tuoshi_lt22m-squashfs-factory.bin",
    "openwrt-ramips-mt76x8-tuoshi_lt22m-squashfs-sysupgrade.bin",
    "openwrt-ramips-mt76x8-tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin",
}

if len(sys.argv) != 2:
    raise SystemExit("usage: verify_release.py DIST_DIRECTORY")
directory = Path(sys.argv[1])
actual = {path.name for path in directory.glob("*.bin")}
assert actual == EXPECTED, f"Unexpected firmware set: {sorted(actual)}"
for name in sorted(EXPECTED):
    path = directory / name
    assert path.is_file() and 262144 < path.stat().st_size <= 7104 * 1024, name
for flavor in ("stock", "fullflash"):
    source = directory / f"source-{flavor}.txt"
    assert source.is_file() and "Feed source: " in source.read_text(), source
print("Validated three LT22M images:", ", ".join(sorted(actual)))
