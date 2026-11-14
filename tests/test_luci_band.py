#!/usr/bin/env python3
"""Offline LuCI band rendering and unique German translation checks."""
import json
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
VIEW = ROOT / 'applications/luci-app-ml352/htdocs/luci-static/resources/view/ml352/status.js'
DE = ROOT / 'applications/luci-app-ml352/po/de/ml352.po'


class BandDisplayTests(unittest.TestCase):
    def test_nominal_lte_band_mapping_and_safe_fallback(self):
        view = VIEW.read_text()
        helper = ('var lteBandMHz = ' + view.split('var lteBandMHz = ', 1)[1]
                  .split('\nfunction row(', 1)[0])
        cases = [
            ({'rat': 'lte', 'band': str(band)}, f'{band} ({mhz} MHz)')
            for band, mhz in ((1, 2100), (3, 1800), (5, 850), (7, 2600),
                              (8, 900), (20, 800), (28, 700), (38, 2600),
                              (40, 2300), (41, 2500))
        ] + [
            ({'rat': 'umts', 'band': '1'}, '1'),
            ({'rat': 'unknown', 'band': '20'}, '20'),
            ({'rat': 'lte', 'band': '66'}, '66'),
            ({'rat': 'lte', 'band': ''}, ''),
            ({'rat': 'lte', 'band': None}, None),
        ]
        script = ("const vm = require('node:vm');\n"
                  f"vm.runInThisContext({json.dumps(helper)});\n"
                  f"let cases = {json.dumps([case for case, _ in cases])};\n"
                  "process.stdout.write(JSON.stringify(cases.map(bandLabel)));\n")
        proc = subprocess.run(['node', '-e', script], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout), [expected for _, expected in cases])

    def test_modem_specific_translation_avoids_global_band_collision(self):
        view = VIEW.read_text()
        self.assertIn("row(_('ML352 frequency band'), bandLabel(status))", view)
        self.assertNotIn("_('Band')", view)
        self.assertIn('msgid "ML352 frequency band"\nmsgstr "Frequenzband"',
                      DE.read_text())


if __name__ == '__main__':
    unittest.main()
