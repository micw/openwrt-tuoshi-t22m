#!/usr/bin/env python3
"""Offline stock sysupgrade tests. Every MTD and sysfs path is a temporary fixture."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

TREE = Path(__file__).resolve().parents[2] / "openwrt-lt22m-stock"
SCRIPT = TREE / "target/linux/ramips/mt76x8/base-files/lib/upgrade/platform.sh"
IMAGE = TREE / "bin/targets/ramips/mt76x8/openwrt-ramips-mt76x8-tuoshi_lt22m-squashfs-sysupgrade.bin"
HOST_FWTOOL = TREE / "staging_dir/host/bin/fwtool"
HOST_DUMPIMAGE = TREE / "build_dir/host/u-boot-2026.07/tools/dumpimage"
LABELS = ("u-boot", "u-boot-env", "factory", "fwconcat0", "stock-storage",
          "fwconcat1", "stock-firmware2", "fwconcat2", "firmware")
SIZES = (0x30000, 0x10000, 0x10000, 0x770000, 0x40000,
         0x50000, 0x770000, 0x40000, 0x800000)
OFFSETS = (0, 0x30000, 0x40000, 0x50000, 0x7c0000,
           0x800000, 0x850000, 0xfc0000)


class StockGuard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        for prerequisite in (SCRIPT, IMAGE, HOST_FWTOOL, HOST_DUMPIMAGE):
            if not prerequisite.is_file():
                raise unittest.SkipTest(f"build prerequisite missing: {prerequisite}")
        cls.original_image = IMAGE.read_bytes()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="lt22m-stock-guard-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        (self.bin / "dumpimage").symlink_to(HOST_DUMPIMAGE)
        (self.bin / "fwtool").symlink_to(HOST_FWTOOL)
        self.put("bin/jsonfilter", "#!/usr/bin/env python3\nimport json,sys\n"
                 "d=json.load(sys.stdin)\n"
                 "e=sys.argv[sys.argv.index('-e')+1]\n"
                 "print(d['supported_devices'][0] if e=='@.supported_devices[0]' "
                 "else d['version']['board'] if e=='@.version.board' else '')\n").chmod(0o755)
        self.put("bin/fw_printenv", "#!/bin/sh\n"
                 "[ \"$1\" = -n ] || exit 1\n"
                 "case \"$2\" in Image1Stable) echo \"${TEST_STABLE:-1}\" ;; "
                 "Image1Try) echo \"${TEST_TRY:-0}\" ;; *) exit 1 ;; esac\n").chmod(0o755)
        self.image = self.put("image.bin", self.original_image)
        self.proc = self.put("proc/mtd", "dev: size erasesize name\n" + "".join(
            f'mtd{i}: {size:08x} 00010000 "{LABELS[i]}"\n'
            for i, size in enumerate(SIZES)))
        for i, (offset, size) in enumerate(zip(OFFSETS, SIZES)):
            for key, value in (("offset", offset), ("size", size),
                               ("erasesize", 65536),
                               ("flags", "0xc00" if i in (0, 1, 3, 4, 5, 6, 7) else "0x800")):
                self.put(f"sys/class/mtd/mtd{i}/{key}", f"{value}\n")
        self.boot = self.put("dev/mtd0", b"x" * SIZES[0])
        self.slot_a = self.put("dev/mtd3", self.original_image)
        self.backup = self.root / "backup.tar.gz"
        subprocess.run(["tar", "-czf", str(self.backup), "-C", str(self.root),
                        "proc/mtd"], check=True)
        for i in (1, 2, 4, 6):
            self.put(f"dev/mtd{i}", b"x" * SIZES[i])
        import hashlib
        loader_hash = hashlib.sha256(self.boot.read_bytes()).hexdigest()
        script = SCRIPT.read_text().replace(
            "45eb1fbce7dbd5ede73054e5d1870c5e131f1cd8f0b641844889afae2421542b",
            loader_hash)
        script = script.replace("/proc/mtd", str(self.proc))
        script = script.replace("/sys/class/mtd", str(self.root / "sys/class/mtd"))
        for i in (0, 1, 2, 3, 4, 6):
            script = script.replace(f"/dev/mtd{i}", str(self.root / f"dev/mtd{i}"))
        self.script = self.put("platform.sh", script)
        self.sentinel = self.root / "would-write"
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ['PATH']}")

    def put(self, relative, data):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_text(data)
        return path

    def run_check(self, stage2=False, mutate_partition=None,
                  mutate_slot_offset=None, short_slot=False, backup=False):
        command = ("board_name() { echo tuoshi,lt22m; }\n"
                   ". \"$SCRIPT\"\n"
                   "get_magic_long() { hexdump -v -n 4 -e '4/1 \"%02x\"' \"$1\"; }\n"
                   "default_do_upgrade() { printf flashed > \"$SENTINEL\"; "
                   "cp \"$IMAGE\" \"$SLOT_A\"; "
                   "if [ \"$MUTATE_SLOT_OFFSET\" -ge 0 ]; then "
                   "printf X | dd of=\"$SLOT_A\" bs=1 seek=\"$MUTATE_SLOT_OFFSET\" "
                   "conv=notrunc 2>/dev/null; fi; "
                   "if [ \"$SHORT_SLOT\" = 1 ]; then truncate -s 1024 \"$SLOT_A\"; fi; "
                   "if [ -n \"$MUTATE_PARTITION\" ]; then "
                   "printf X > \"$MUTATE_PARTITION\"; fi; }\n"
                   "UPGRADE_BACKUP=${UPGRADE_BACKUP:-}\n"
                   + ('platform_do_upgrade "$IMAGE"\n' if stage2 else
                      'platform_check_image "$IMAGE"\n'))
        return subprocess.run(["sh", "-c", command], env=dict(
            self.env, SCRIPT=str(self.script), IMAGE=str(self.image),
            SENTINEL=str(self.sentinel), SLOT_A=str(self.slot_a),
            MUTATE_SLOT_OFFSET=str(-1 if mutate_slot_offset is None else mutate_slot_offset),
            SHORT_SLOT="1" if short_slot else "0",
            UPGRADE_BACKUP=str(self.backup) if backup else "",
            MUTATE_PARTITION=(str(self.root / f"dev/mtd{mutate_partition}")
                              if mutate_partition is not None else "")),
            capture_output=True, text=True)

    def assert_rejected(self):
        self.sentinel.unlink(missing_ok=True)
        for stage2 in (False, True):
            with self.subTest(stage2=stage2):
                run = self.run_check(stage2)
                self.assertNotEqual(run.returncode, 0, run.stdout + run.stderr)
                self.assertFalse(self.sentinel.exists(), "unsafe image reached writer")

    def test_built_image_is_accepted_in_both_stages(self):
        for stage2 in (False, True):
            result = self.run_check(stage2)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.sentinel.read_text(), "flashed")

    def test_slot_a_readback_covers_rootfs_with_or_without_backup(self):
        rootfs_byte = 64 + int.from_bytes(self.original_image[12:16], "big") + 1024
        for backup in (False, True):
            with self.subTest(backup=backup):
                result = self.run_check(stage2=True, backup=backup)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.sentinel.unlink()
                result = self.run_check(stage2=True, backup=backup,
                                        mutate_slot_offset=rootfs_byte)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn("slot A readback mismatch", result.stderr)
                self.assertTrue(self.sentinel.exists())
                self.sentinel.unlink()

    def test_slot_a_short_read_rejected_but_marker_replacement_allowed(self):
        result = self.run_check(stage2=True, short_slot=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("slot A readback mismatch", result.stderr)
        self.sentinel.unlink()
        marker = len(self.original_image) // 65536 * 65536
        result = self.run_check(stage2=True, mutate_slot_offset=marker,
                                backup=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_sysupgrade_over_7104_kib_is_rejected_in_both_stages(self):
        maximum = 7104 * 1024
        self.assertLess(len(self.original_image), maximum)
        self.image.write_bytes(self.original_image.ljust(maximum + 1, b"\xff"))
        self.assert_rejected()

    def test_protected_partition_mutation_aborts_ramfs_stage(self):
        for partition in (2, 4, 6):
            with self.subTest(partition=partition):
                result = self.run_check(stage2=True, mutate_partition=partition)
                self.assertNotEqual(result.returncode, 0)
                self.assertTrue(self.sentinel.exists())
                self.sentinel.unlink()

    def test_kernel_and_rootfs_corruption(self):
        for offset in (4, 80, 40):
            with self.subTest(offset=offset):
                data = bytearray(self.original_image)
                data[offset] ^= 1
                self.image.write_bytes(data)
                self.assert_rejected()
        self.image.write_bytes(self.original_image)
        kernel_size = 64 + int.from_bytes(self.original_image[12:16], "big")
        data = bytearray(self.original_image)
        data[kernel_size + 40:kernel_size + 44] = b"\0" * 4
        self.image.write_bytes(data)
        self.assert_rejected()

    def test_factory_file_and_wrong_metadata(self):
        marker = len(self.original_image) // 65536 * 65536
        self.image.write_bytes(self.original_image[:marker + 4])
        self.assert_rejected()
        self.image.write_bytes(self.original_image)
        result = subprocess.run([str(HOST_FWTOOL), "-q", "-i", "-", str(self.image)],
                                check=True, capture_output=True, text=True)
        doc = json.loads(result.stdout)
        doc["supported_devices"] = ["tuoshi,other"]
        metadata = self.put("new-metadata.json", json.dumps(doc))
        subprocess.run([str(HOST_FWTOOL), "-q", "-i", str(self.root / "old.json"),
                        "-t", str(self.image)], check=True)
        subprocess.run([str(HOST_FWTOOL), "-q", "-I", str(metadata), str(self.image)], check=True)
        self.assert_rejected()

    def test_wrong_geometry_flags_and_stock_loader(self):
        self.put("sys/class/mtd/mtd4/offset", "8192000\n")
        self.assert_rejected()
        self.put("sys/class/mtd/mtd4/offset", f"{OFFSETS[4]}\n")
        self.put("sys/class/mtd/mtd2/flags", "0xc00\n")
        self.assert_rejected()
        self.put("sys/class/mtd/mtd2/flags", "0x800\n")
        for partition in (4, 6):
            with self.subTest(partition=partition):
                self.put(f"sys/class/mtd/mtd{partition}/flags", "0x800\n")
                self.assert_rejected()
                self.put(f"sys/class/mtd/mtd{partition}/flags", "0xc00\n")
        self.boot.write_bytes(b"y" * SIZES[0])
        self.assert_rejected()

    def test_boot_flags(self):
        self.env["TEST_STABLE"] = "0"
        self.assert_rejected()
        self.env.pop("TEST_STABLE")
        self.env["TEST_TRY"] = "3"
        self.assert_rejected()


if __name__ == "__main__":
    unittest.main()
