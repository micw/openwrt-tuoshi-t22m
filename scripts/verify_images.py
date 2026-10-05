#!/usr/bin/env python3
"""Fail closed on unexpected LT22M release images and missing embedded packages."""
import json
from pathlib import Path
import subprocess
import sys

EXPECTED_PACKAGES = {
    "ml352d", "luci-app-ml352", "lt22m-modem-ui", "kmod-wireguard",
    "wireguard-tools", "luci-proto-wireguard", "kmod-crypto-lib-curve25519",
    "kmod-crypto-lib-chacha20poly1305", "kmod-udptunnel4",
}
PREFIX = "openwrt-ramips-mt76x8-"


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("stock", "fullflash"):
        raise SystemExit("usage: verify_images.py stock|fullflash OPENWRT_TREE")
    flavor, tree = sys.argv[1], Path(sys.argv[2])
    target = tree / "bin/targets/ramips/mt76x8"
    device = "tuoshi_lt22m" + ("_fullflash" if flavor == "fullflash" else "")
    stem = PREFIX + device + "-squashfs-"
    names = [stem + "sysupgrade.bin"]
    if flavor == "stock":
        names.insert(0, stem + "factory.bin")
    manifest = target / (PREFIX + device + ".manifest")
    assert manifest.is_file(), f"Missing manifest: {manifest}"
    installed = {line.split(" - ", 1)[0] for line in manifest.read_text().splitlines()}
    missing = EXPECTED_PACKAGES - installed
    assert not missing, f"Missing image packages: {sorted(missing)}"
    magic = bytes.fromhex("27051956" if flavor == "fullflash" else "27151967")
    dumpimage = tree / "build_dir/host/u-boot-2026.07/tools/dumpimage"
    fwtool = tree / "staging_dir/host/bin/fwtool"
    assert dumpimage.is_file() and fwtool.is_file(), "Missing host image verification tools"
    for name in names:
        image = target / name
        assert image.is_file(), f"Missing image: {image}"
        size = image.stat().st_size
        assert 262144 < size <= 7104 * 1024, f"Image size out of bounds: {name} {size}"
        with image.open("rb") as stream:
            assert stream.read(4) == magic, f"Wrong uImage magic: {name}"
        cmd = [str(dumpimage), "-l", str(image)]
        if flavor == "stock":
            cmd[1:1] = ["-M", "0x27151967"]
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL)
        if "sysupgrade" in name:
            metadata = json.loads(subprocess.check_output(
                [str(fwtool), "-q", "-i", "-", str(image)], text=True))
            devices = metadata["supported_devices"]
            board = metadata["version"]["board"]
            expected_board = device
            assert board == expected_board, (board, expected_board)
            assert devices[0] == "tuoshi,lt22m", devices
            if flavor == "fullflash":
                assert devices[1] == "tuoshi,lt22m-fullflash", devices
            else:
                assert len(devices) == 1, devices
        print(f"VALID {flavor}: {name} ({size} bytes)")
    print("VALID packages:", ", ".join(sorted(EXPECTED_PACKAGES)))


if __name__ == "__main__":
    main()
