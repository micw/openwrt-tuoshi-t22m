#!/usr/bin/env python3
"""Offline UCI-mock coverage for LT22M first-boot and guarded migration."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / 'collections/lt22m-wwand/files/95-lt22m-wwand'
UCI_MOCK = '''#!/usr/bin/env python3
import json, os, sys
p = os.environ['MOCK_UCI_STATE']
s = json.load(open(p))
a = [v for v in sys.argv[1:] if v != '-q']
cmd = a[0]
def get(key):
    parts = key.split('.')
    if len(parts) == 2: return s.get(parts[0], {}).get(parts[1], {}).get('_type')
    return s.get(parts[0], {}).get(parts[1], {}).get(parts[2])
if cmd == 'get':
    value = get(a[1]);
    if value is None: sys.exit(1)
    print(value); sys.exit(0)
if cmd == 'show':
    for section, settings in s.get(a[1], {}).items():
        print('%s.%s=%s' % (a[1], section, settings['_type']))
        for key, value in settings.items():
            if key != '_type': print('%s.%s.%s=%s' % (a[1], section, key, value))
    sys.exit(0)
if cmd == 'set':
    key, value = a[1].split('=', 1)
    parts = key.split('.')
    if len(parts) == 2: s.setdefault(parts[0], {})[parts[1]] = {'_type': value}
    else: s.setdefault(parts[0], {}).setdefault(parts[1], {})[parts[2]] = value
elif cmd == 'delete':
    parts = a[1].split('.')
    s.get(parts[0], {}).get(parts[1], {}).pop(parts[2], None)
elif cmd == 'add_list':
    key, value = a[1].split('=', 1)
    parts = key.split('.')
    target = s[parts[0]][parts[1]]
    target[parts[2]] = (target.get(parts[2], '') + ' ' + value).strip()
elif cmd != 'commit': sys.exit(2)
with open(p, 'w') as out: json.dump(s, out)
'''


class DefaultsTest(unittest.TestCase):
    def run_defaults(self, network=None, legacy=None, board='tuoshi,lt22m'):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            state = {'network': network or {}, 'firewall': {
                'wan': {'_type': 'zone', 'name': 'wan', 'network': 'wan wan6'}}}
            if legacy is not None:
                state['ml352'] = {'modem': {'_type': 'modem', 'enabled': '1',
                                           'at_port': '/dev/ttyUSB1', 'netdev': 'eth1',
                                           'interface': 'lte', 'apn': '',
                                           'roaming': '1', **legacy}}
            statefile = root / 'uci.json'
            statefile.write_text(json.dumps(state))
            (root / 'uci').write_text(UCI_MOCK)
            (root / 'cat').write_text('#!/bin/sh\ncase "$1" in /tmp/sysinfo/board_name) printf "%s\\n" "$MOCK_BOARD" ;; *) exec /bin/cat "$@" ;; esac\n')
            (root / 'logger').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$MOCK_LOG"\n')
            for name in ('uci', 'cat', 'logger'):
                (root / name).chmod(0o755)
            env = dict(os.environ, PATH=f'{root}:{os.environ["PATH"]}',
                       MOCK_UCI_STATE=str(statefile), MOCK_BOARD=board,
                       MOCK_LOG=str(root / 'log'))
            subprocess.run(['/bin/sh', str(SCRIPT)], env=env, check=True)
            result = json.loads(statefile.read_text())
            log = (root / 'log').read_text() if (root / 'log').exists() else ''
            return result, log

    def test_fresh_board_config(self):
        state, _ = self.run_defaults()
        self.assertEqual(state['network']['lte']['proto'], 'wwand')
        self.assertNotIn('ipv4_dhcp', state['network']['lte'])
        self.assertNotIn('apn', state['network']['lte'])
        self.assertEqual(state['network']['ml352']['device'], 'eth1')
        self.assertEqual(state['network']['ml352']['path'], '1-1')
        self.assertEqual(state['network']['lt22m_wwand']['autosetup'], '0')
        self.assertIn('lte', state['firewall']['wan']['network'].split())

    def test_migrate_exact_legacy_preserves_metric_and_apn(self):
        lte = {'_type': 'interface', 'proto': 'dhcp', 'device': 'eth1',
               'metric': '23', 'defaultroute': '0'}
        state, _ = self.run_defaults({'lte': lte}, {'apn': 'private.example', 'roaming': '0'},
                                     board='tuoshi,lt22m-fullflash')
        iface = state['network']['lte']
        self.assertEqual(iface['proto'], 'wwand')
        self.assertEqual(iface['modem'], 'ml352')
        self.assertNotIn('ipv4_dhcp', iface)
        self.assertEqual(iface['metric'], '23')
        self.assertEqual(iface['defaultroute'], '0')
        self.assertEqual(iface['apn'], 'private.example')
        self.assertNotIn('device', iface)
        self.assertEqual(state['network']['ml352']['ml352_roaming'], '0')
        self.assertEqual(state['network']['ml352']['path'], '1-1')

    def test_custom_lte_is_not_migrated(self):
        for device, proto in [('usb0', 'dhcp'), ('eth1', 'static')]:
            with self.subTest(device=device, proto=proto):
                lte = {'_type': 'interface', 'proto': proto, 'device': device}
                state, log = self.run_defaults({'lte': lte})
                self.assertEqual(state['network']['lte'], lte)
                self.assertNotIn('ml352', state['network'])
                self.assertIn('non-default LTE preserved', log)

    def test_already_migrated_lte_is_not_rewritten(self):
        lte = {'_type': 'interface', 'proto': 'wwand', 'modem': 'other',
               'apn': 'operator.apn', 'ipv4_dhcp': '1'}
        state, _ = self.run_defaults({'lte': lte})
        self.assertEqual(state['network']['lte'], lte)
        self.assertNotIn('ml352', state['network'])

    def test_previous_local_dhcp_child_flag_removed_only_from_known_migration(self):
        lte = {'_type': 'interface', 'proto': 'wwand', 'modem': 'ml352',
               'ipv4_dhcp': '1', 'apn': 'private.example', 'metric': '23'}
        modem = {'_type': 'wwand_modem', 'protocol': 'ncm', 'device': 'eth1',
                 'tty': '/dev/ttyUSB1'}
        state, _ = self.run_defaults({'lte': lte, 'ml352': modem})
        self.assertNotIn('ipv4_dhcp', state['network']['lte'])
        self.assertEqual(state['network']['lte']['apn'], 'private.example')
        self.assertEqual(state['network']['lte']['metric'], '23')
        self.assertEqual(state['network']['ml352'], modem)

        custom = {**modem, 'tty': '/dev/ttyUSB2'}
        state, _ = self.run_defaults({'lte': lte, 'ml352': custom})
        self.assertEqual(state['network']['lte'], lte)
        self.assertEqual(state['network']['ml352'], custom)

    def test_custom_legacy_control_path_is_not_migrated(self):
        lte = {'_type': 'interface', 'proto': 'dhcp', 'device': 'eth1'}
        state, log = self.run_defaults({'lte': lte}, {'at_port': '/dev/ttyUSB2'})
        self.assertEqual(state['network']['lte'], lte)
        self.assertNotIn('ml352', state['network'])
        self.assertIn('Custom legacy modem settings preserved', log)

    def test_conflicting_existing_wwand_modem_is_not_retargeted(self):
        lte = {'_type': 'interface', 'proto': 'dhcp', 'device': 'eth1'}
        other = {'_type': 'wwand_modem', 'protocol': 'ncm', 'device': 'usb0',
                 'tty': '/dev/ttyUSB3'}
        state, log = self.run_defaults({'lte': lte, 'ml352': other})
        self.assertEqual(state['network']['lte'], lte)
        self.assertEqual(state['network']['ml352'], other)
        self.assertIn('Conflicting existing wwand modem preserved', log)

    def test_invalid_apn_not_copied(self):
        lte = {'_type': 'interface', 'proto': 'dhcp', 'device': 'eth1'}
        state, log = self.run_defaults({'lte': lte}, {'apn': 'bad";reboot'})
        self.assertNotIn('apn', state['network']['lte'])
        self.assertIn('Invalid legacy APN skipped', log)

    def test_other_board_is_unchanged(self):
        state, _ = self.run_defaults(board='unrelated,router')
        self.assertEqual(state['network'], {})
        self.assertEqual(state['firewall']['wan']['network'], 'wan wan6')


if __name__ == '__main__':
    unittest.main()
