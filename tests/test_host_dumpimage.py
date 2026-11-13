#!/usr/bin/env python3
"""Resolve the dumpimage built by the pinned OpenWrt uboot-tools package."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.verify_images import host_dumpimage


class HostDumpimageTests(unittest.TestCase):
    def test_uboot_release_and_previous_host_dir_format(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            makefile = tree / 'package/boot/uboot-tools/Makefile'
            makefile.parent.mkdir(parents=True)
            old = tree / 'build_dir/host/u-boot-2026.07/tools/dumpimage'
            old.parent.mkdir(parents=True)
            old.touch()
            new = tree / 'build_dir/host/u-boot-v2026.10/tools/dumpimage'
            new.parent.mkdir(parents=True)
            new.touch()
            makefile.write_text('PKG_VERSION:=2026.10\n')
            self.assertEqual(host_dumpimage(tree), new)
            makefile.write_text('PKG_VERSION:=2026.07\n')
            self.assertEqual(host_dumpimage(tree), old)
            old.unlink()
            with self.assertRaisesRegex(AssertionError, 'Missing or ambiguous'):
                host_dumpimage(tree)

    def test_ambiguous_current_version_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            tree = Path(directory)
            makefile = tree / 'package/boot/uboot-tools/Makefile'
            makefile.parent.mkdir(parents=True)
            makefile.write_text('PKG_VERSION:=2026.10\n')
            for name in ('u-boot-v2026.10', 'u-boot-2026.10'):
                candidate = tree / 'build_dir/host' / name / 'tools/dumpimage'
                candidate.parent.mkdir(parents=True)
                candidate.touch()
            with self.assertRaisesRegex(AssertionError, 'Missing or ambiguous'):
                host_dumpimage(tree)


if __name__ == '__main__':
    unittest.main()
