#!/usr/bin/env python3
"""Offline reconnect-policy tests; serial, netifd, UCI and time are mocked."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'network/utils/ml352d/ml352d'


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        self.policy = (SOURCE.read_text().split('recover_connection() {', 1)[1]
                       .split('\nsim_state=unknown', 1)[0]
                       .replace('/proc/uptime', '"$TEST_UPTIME_FILE"'))

    def run_policy(self, *, times=(1000, 1599, 1600), registration=0,
                   sim='ready', serial=True, enabled=True, network=True,
                   autostart=True, owned=False, pdp='', dhcp='', up=False,
                   recheck='0', fresh_pdp='', fresh_dhcp='', stale_budget=False,
                   restored_at=None, lost_at=None):
        for name in ('at-calls', 'network-calls', 'log'):
            (self.dir / name).unlink(missing_ok=True)
        marker = self.dir / 'network-down-owned'
        if owned:
            marker.touch()
        else:
            marker.unlink(missing_ok=True)
        if stale_budget:
            (self.dir / 'recovery.state').write_text('91915 3 95527\n')
        script = '''#!/bin/sh
RUN_DIR="$TEST_DIR"
network_down_owned="$RUN_DIR/network-down-owned"
recovery_delay=600
registered="$TEST_REG"
sim_state="$TEST_SIM"
interface=lte
netdev=eth1
pdp_ip="$TEST_PDP"
dhcp_ip="$TEST_DHCP"
offline_since=''
last_sim_ok=''
uci() { case "$*" in *disabled) [ "$TEST_ENABLED" = 1 ] && echo 0 || echo 1;; *proto) echo dhcp;; *device) echo eth1;; esac; }
ubus() { [ "$TEST_NETWORK" = 1 ] || return 1; printf '{"autostart":%s,"available":true,"up":%s}\\n' "$TEST_AUTOSTART" "$TEST_UP"; }
jsonfilter() { case "$*" in *autostart) echo "$TEST_AUTOSTART";; *available) echo true;; *up) echo "$TEST_UP";; esac; }
ip() { [ -z "$TEST_FRESH_DHCP" ] || printf '2: eth1 inet %s/24 scope global eth1\\n' "$TEST_FRESH_DHCP"; }
valid_ip() { case "$1" in ''|0.0.0.0) return 1;; *.*.*.*) return 0;; *) return 1;; esac; }
at() { printf '%s\\n' "$*" >> "$RUN_DIR/at-calls"; case "$*" in
    AT) echo OK;;
    'AT+CEREG? AT+CGACT? AT+CGPADDR') printf '+CEREG: 3,%s\\n+CGACT: 1,1\\n+CGPADDR: 1,"%s"\\nOK\\n' "$TEST_RECHECK" "$TEST_FRESH_PDP";;
    'AT+CFUN=1,1') echo OK;; esac; }
value() { printf '%s\\n' "$2" | sed -n "s/^${1}:[[:space:]]*//p" | head -n 1; }
value_cid1() { printf '%s\\n' "$2" | sed -n "s/^${1}:[[:space:]]*1,[[:space:]]*//p" | head -n 1; }
network_down() { echo down >> "$RUN_DIR/network-calls"; }
write_status() { :; }
log() { printf '%s\\n' "$*" >> "$RUN_DIR/log"; }
recover_connection() {'''+self.policy+'''
for now in $TEST_TIMES; do
    printf '%s 0\\n' "$now" > "$TEST_UPTIME_FILE"
    [ "$TEST_SERIAL" = 1 ] && last_sim_ok="$now" || last_sim_ok=''
    if [ "$now" = "$TEST_RESTORED_AT" ]; then
        registered=1 pdp_ip=10.0.0.2 dhcp_ip=10.0.0.2 TEST_UP=true
    fi
    if [ "$now" = "$TEST_LOST_AT" ]; then
        registered=0 pdp_ip='' dhcp_ip='' TEST_UP=false
    fi
    recover_connection
done
'''
        env = dict(os.environ, TEST_DIR=str(self.dir),
                   TEST_UPTIME_FILE=str(self.dir / 'uptime'),
                   TEST_TIMES=' '.join(map(str, times)), TEST_REG=str(registration),
                   TEST_SIM=sim, TEST_SERIAL='1' if serial else '0',
                   TEST_ENABLED='1' if enabled else '0',
                   TEST_NETWORK='1' if network else '0',
                   TEST_AUTOSTART='true' if autostart else 'false',
                   TEST_PDP=pdp, TEST_DHCP=dhcp,
                   TEST_UP='true' if up else 'false',
                   TEST_RECHECK=recheck, TEST_FRESH_PDP=fresh_pdp,
                   TEST_FRESH_DHCP=fresh_dhcp,
                   TEST_RESTORED_AT='' if restored_at is None else str(restored_at),
                   TEST_LOST_AT='' if lost_at is None else str(lost_at))
        result = subprocess.run(['sh'], input=script, text=True,
                                capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        calls = self.dir / 'at-calls'
        return calls.read_text().splitlines() if calls.exists() else []

    def test_no_budget_or_cooldown_every_ten_minutes(self):
        calls = self.run_policy(times=(1000, 1599, 1600, 2199, 2200,
                                       2800, 3400, 4000), stale_budget=True)
        self.assertEqual(calls.count('AT+CFUN=1,1'), 5, calls)
        self.assertEqual((self.dir / 'recovery.state').read_text(),
                         '91915 3 95527\n')  # Stale budget is never consulted.

    def test_sustained_failure_required(self):
        self.assertNotIn('AT+CFUN=1,1',
                         self.run_policy(times=(1000, 1300, 1599)))
        calls = self.run_policy(times=(1000, 1500, 1600, 2199, 2200),
                                restored_at=1500, lost_at=1600)
        self.assertEqual(calls.count('AT+CFUN=1,1'), 1, calls)

    def test_uptime_rollback_restarts_ten_minute_timer(self):
        calls = self.run_policy(times=(1000, 1300, 900, 1499, 1500))
        self.assertEqual(calls.count('AT+CFUN=1,1'), 1, calls)

    def test_missing_sim_serial_or_network_does_not_restart(self):
        for settings in ({'sim': 'absent'}, {'sim': 'unavailable'},
                         {'serial': False}, {'network': False},
                         {'enabled': False}, {'autostart': False}):
            with self.subTest(settings=settings):
                self.assertEqual(self.run_policy(**settings), [])

    def test_daemon_owned_down_is_not_manual_ifdown(self):
        calls = self.run_policy(autostart=False, owned=True)
        self.assertEqual(calls.count('AT+CFUN=1,1'), 1, calls)

    def test_connected_interface_is_not_restarted(self):
        calls = self.run_policy(registration=1, pdp='10.0.0.2',
                                dhcp='10.0.0.2', up=True)
        self.assertEqual(calls, [])

    def test_registered_without_pdp_or_dhcp_restarts(self):
        for pdp, dhcp, up in (('', '', False), ('10.0.0.2', '', False),
                              ('10.0.0.2', '10.0.0.3', True)):
            with self.subTest(pdp=pdp, dhcp=dhcp, up=up):
                calls = self.run_policy(registration=1, pdp=pdp,
                                        dhcp=dhcp, up=up, recheck='1',
                                        fresh_pdp=pdp, fresh_dhcp=dhcp)
                self.assertEqual(calls.count('AT+CFUN=1,1'), 1, calls)

    def test_recheck_prevents_reset_if_link_just_recovered(self):
        calls = self.run_policy(registration=0, recheck='1',
                                fresh_pdp='10.0.0.2',
                                fresh_dhcp='10.0.0.2', up=True)
        self.assertIn('AT+CEREG? AT+CGACT? AT+CGPADDR', calls)
        self.assertNotIn('AT+CFUN=1,1', calls)

    def test_interface_ownership_follows_daemon_down_and_up(self):
        source = SOURCE.read_text()
        functions = source.split('network_down_owned=', 1)[1].split('network_restart() {', 1)[0]
        script = '''RUN_DIR="$TEST_DIR"
interface=lte
ubus() { :; }
network_down_owned=''' + functions + '''
network_down
[ -f "$network_down_owned" ] || exit 1
network_up
[ ! -e "$network_down_owned" ] || exit 2
'''
        result = subprocess.run(['sh'], input=script, text=True, capture_output=True,
                                env=dict(os.environ, TEST_DIR=str(self.dir)))
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main()
