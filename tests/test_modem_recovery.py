#!/usr/bin/env python3
"""Offline policy tests; serial, netifd, UCI and network writes are mocked."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / "network/utils/ml352d/ml352d"


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        text = SOURCE.read_text()
        self.policy = text.split('recover_registration() {', 1)[1].split('\nsim_state=unknown', 1)[0]
        self.dir = Path(self.tmp.name)

    def run_policy(self, *, registration=0, sim='ready', serial=True, enabled=True,
                   network=True, delay=0, cooldown=0, repeat=1, recheck='0'):
        script = '''#!/bin/sh
RUN_DIR="$TEST_DIR"
recovery_state="$RUN_DIR/recovery.state"
recovery_delay="$TEST_DELAY"
recovery_cooldown="$TEST_COOLDOWN"
recovery_window=86400
recovery_max_attempts=3
registered="$TEST_REG"
sim_state="$TEST_SIM"
interface=lte
netdev=eth1
last_sim_ok=0
offline_since=''
[ "$TEST_SERIAL" = 1 ] || last_sim_ok=''
read -r now rest < /proc/uptime
last_sim_ok="${now%%.*}"
[ "$TEST_SERIAL" = 1 ] || last_sim_ok=''
uci() { case "$*" in *disabled) [ "$TEST_ENABLED" = 1 ] && echo 0 || echo 1;; *proto) echo dhcp;; *device) echo eth1;; esac; }
ubus() { [ "$TEST_NETWORK" = 1 ] && printf '{"autostart":true,"available":true}'; }
jsonfilter() { case "$*" in *autostart) echo true;; *available) echo true;; esac; }
at() { printf '%s\\n' "$*" >> "$RUN_DIR/at-calls"; case "$*" in AT) echo OK;; AT+CEREG\\?) printf '+CEREG: 0,%s\\nOK\\n' "$TEST_RECHECK";; esac; }
value() { printf '%s\\n' "$2" | sed -n "s/^${1}:[[:space:]]*//p" | head -n 1; }
network_down() { echo down >> "$RUN_DIR/network-calls"; }
write_status() { :; }
log() { :; }
recover_registration() {'''+self.policy+'''
i=0
while [ "$i" -lt "$TEST_REPEAT" ]; do
    recover_registration
    i=$((i + 1))
done
'''
        env = dict(os.environ, TEST_DIR=str(self.dir), TEST_DELAY=str(delay),
                   TEST_COOLDOWN=str(cooldown), TEST_REG=str(registration),
                   TEST_SIM=sim, TEST_SERIAL='1' if serial else '0',
                   TEST_NETWORK='1' if network else '0', TEST_REPEAT=str(repeat),
                   TEST_ENABLED='1' if enabled else '0', TEST_RECHECK=recheck)
        result = subprocess.run(['sh'], input=script, text=True, capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        return (self.dir / 'at-calls').read_text().splitlines() if (self.dir / 'at-calls').exists() else []

    def test_sustained_failure_restarts_once(self):
        calls = self.run_policy(repeat=3, cooldown=1800)
        self.assertEqual(calls.count('AT+CFUN=1,1'), 1, calls)
        self.assertEqual((self.dir / 'recovery.state').stat().st_mode & 0o777, 0o600)

    def test_registered_or_missing_sim_does_not_restart(self):
        for reg, sim in ((1, 'ready'), (5, 'ready'), (0, 'absent'), (0, 'unavailable')):
            with self.subTest(reg=reg, sim=sim):
                self.assertEqual(self.run_policy(registration=reg, sim=sim), [])

    def test_missing_serial_or_network_does_not_restart(self):
        self.assertEqual(self.run_policy(serial=False), [])
        self.assertEqual(self.run_policy(network=False), [])

    def test_below_threshold_does_not_restart(self):
        self.assertEqual(self.run_policy(delay=600), [])

    def test_disabled_interface_and_registration_recheck(self):
        self.assertEqual(self.run_policy(enabled=False, repeat=2), [])
        calls = self.run_policy(recheck='5', repeat=2)
        self.assertIn('AT+CEREG?', calls)
        self.assertNotIn('AT+CFUN=1,1', calls)

    def test_attempt_budget_survives_process_restart(self):
        for _ in range(4):
            self.run_policy(repeat=2)
        self.assertEqual((self.dir / 'recovery.state').read_text().split()[1], '3')
        self.assertEqual((self.dir / 'at-calls').read_text().count('AT+CFUN=1,1'), 3)


if __name__ == '__main__':
    unittest.main()
