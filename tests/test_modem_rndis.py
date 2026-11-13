#!/usr/bin/env python3
"""Offline ML352 setup/rebind tests; AT, ICMP, netifd, UCI and uptime are mocked."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'network/utils/ml352d/ml352d'


class RndisTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.dir = Path(temp.name)
        source = SOURCE.read_text()
        self.policy = (source.split('setup_attempts=0\n', 1)[1]
                       .split('\n# A sustained missing cellular data connection', 1)[0]
                       .replace('/proc/uptime', '"$TEST_UPTIME_FILE"'))
        self.session_change = ('if [ "$last_pdp" != "$pdp_ip" ]; then' +
                               source.split('if [ "$last_pdp" != "$pdp_ip" ]; then', 1)[1]
                               .split('\n        now="$(date +%s)"', 1)[0])

    def run_policy(self, *, probe='', dns='0.0.0.0', times=(1000,),
                   new_session=False,
                   sim='ready', registered=1, pdp='10.0.0.2', dhcp='10.0.0.2',
                   dhcp_after=None, pdp_after=None,
                   up=True, autostart=True, disabled=False, proto='dhcp',
                   device='eth1', fail='', transport_fail='', partial='',
                   stale_ok='', stale_error='',
                   ping_ok=False, ping_recovers_at=None, down_at=None,
                   fresh_reg='1', fresh_cgact='1', fresh_pdp=None):
        for name in ('at-calls', 'ping-calls', 'network-calls', 'log'):
            (self.dir / name).unlink(missing_ok=True)
        script = '''#!/bin/sh
RUN_DIR="$TEST_DIR"
interface=lte
netdev=eth1
sim_state="$TEST_SIM"
registered="$TEST_REG"
pdp_ip="$TEST_PDP"
dhcp_ip="$TEST_DHCP"
last_error=''
last_pdp="$TEST_PDP"
last_renew=0
offline_since=''
retry_interval=45
recovery_probe_ip="$TEST_PROBE"
setup_attempts="$TEST_SETUP_ATTEMPTS"
uci() { case "$*" in
    *disabled) [ "$TEST_DISABLED" = true ] && echo 1 || echo 0;;
    *proto) echo "$TEST_PROTO";;
    *device) echo "$TEST_DEVICE";; esac; }
ubus() { echo '{"autostart":true,"up":true,"dns-server":["0.0.0.0"]}'; }
jsonfilter() { case "$*" in
    *dns-server*) printf '%s\\n' $TEST_DNS;;
    *autostart) echo "$TEST_AUTOSTART";;
    *up) echo "$TEST_UP";; esac; }
ping() {
    printf '%s\\n' "$*" >> "$RUN_DIR/ping-calls"
    [ "$TEST_PING_OK" = true ] && return 0
    if [ "$now" = "$TEST_PING_RECOVERS_AT" ]; then return 0; fi
    if [ "$now" = "$TEST_DOWN_AT" ]; then TEST_AUTOSTART=false; fi
    return 1
}
ip() { printf '2: eth1 inet %s/24 scope global eth1\\n' "$dhcp_ip"; }
at() {
    printf '%s\\n' "$*" >> "$RUN_DIR/at-calls"
    [ "$*" = "$TEST_TRANSPORT_FAIL" ] && return 1
    [ "$*" = "$TEST_STALE_OK" ] && { printf 'OK\\n%s\\n' "$*"; return 0; }
    [ "$*" = "$TEST_STALE_ERROR" ] && { printf 'ERROR\\n%s\\n' "$*"; return 0; }
    [ "$*" = "$TEST_FAIL" ] && { printf '%s\\nERROR\\n' "$*"; return 0; }
    if [ "$*" = 'AT+CEREG? AT+CGACT? AT+CGPADDR' ]; then
        printf '+CEREG: 3,%s\\n+CGACT: 1,%s\\n+CGPADDR: 1,"%s"\\nOK\\n' \\
            "$TEST_FRESH_REG" "$TEST_FRESH_CGACT" "$TEST_FRESH_PDP"
        return
    fi
    printf '%s\\n' "$*"
    [ "$*" = "$TEST_PARTIAL" ] || echo OK
}
sleep() { :; }
value() { printf '%s\\n' "$2" | sed -n "s/^${1}:[[:space:]]*//p" | head -n 1; }
value_cid1() { printf '%s\\n' "$2" | sed -n "s/^${1}:[[:space:]]*1,[[:space:]]*//p" | head -n 1; }
network_restart() {
    [ "$TEST_AUTOSTART" = true ] && [ "$TEST_UP" = true ] &&
        echo restart >> "$RUN_DIR/network-calls"
    :
}
log() { printf '%s\\n' "$*" >> "$RUN_DIR/log"; }
''' + self.policy + '''
for now in $TEST_TIMES; do
    printf '%s 0\\n' "$now" > "$TEST_UPTIME_FILE"
    if [ "$now" = "$TEST_DHCP_AFTER" ]; then dhcp_ip="$pdp_ip"; fi
    if [ "$now" = "$TEST_PDP_AFTER" ]; then pdp_ip=10.0.0.3 dhcp_ip=10.0.0.3; fi
    last_error=''
''' + self.session_change + '''
    ensure_setup
    ensure_rndis
done
printf 'last_error=%s rndis_recovery_needed=%s setup_attempts=%s\\n' \\
    "$last_error" "$rndis_recovery_needed" "$setup_attempts"
'''
        env = {**os.environ, 'TEST_DIR': str(self.dir),
               'TEST_UPTIME_FILE': str(self.dir / 'uptime'),
               'TEST_TIMES': ' '.join(map(str, times)),
               'TEST_PROBE': probe, 'TEST_DNS': dns,
               'TEST_SETUP_ATTEMPTS': '0' if new_session else '2',
               'TEST_SIM': sim, 'TEST_REG': str(registered),
               'TEST_PDP': pdp, 'TEST_DHCP': dhcp,
               'TEST_DHCP_AFTER': str(dhcp_after or ''),
               'TEST_PDP_AFTER': str(pdp_after or ''),
               'TEST_UP': str(up).lower(),
               'TEST_AUTOSTART': str(autostart).lower(),
               'TEST_DISABLED': str(disabled).lower(),
               'TEST_PROTO': proto, 'TEST_DEVICE': device,
               'TEST_FAIL': fail, 'TEST_TRANSPORT_FAIL': transport_fail,
               'TEST_STALE_OK': stale_ok, 'TEST_STALE_ERROR': stale_error,
               'TEST_PARTIAL': partial, 'TEST_PING_OK': str(ping_ok).lower(),
               'TEST_PING_RECOVERS_AT': str(ping_recovers_at or ''),
               'TEST_DOWN_AT': str(down_at or ''),
               'TEST_FRESH_REG': fresh_reg,
               'TEST_FRESH_CGACT': fresh_cgact,
               'TEST_FRESH_PDP': pdp if fresh_pdp is None else fresh_pdp}
        result = subprocess.run(['sh'], input=script, text=True,
                                capture_output=True, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)

        def calls(name):
            path = self.dir / name
            return path.read_text().splitlines() if path.exists() else []
        return calls('at-calls'), calls('network-calls'), calls('ping-calls'), result.stdout

    def test_new_session_activates_and_binds_without_username_or_dns(self):
        at, restarts, probes, output = self.run_policy(
            new_session=True, pdp='', dhcp='', up=False, dns='', times=(1000, 1020, 1045))
        self.assertEqual(at, ['AT+CGACT=1,1', 'AT*NETACT=1,1,1',
                              'AT+CGACT=1,1', 'AT*NETACT=1,1,1'])
        self.assertEqual((restarts, probes), ([], []))
        self.assertIn('setup_attempts=2', output)

    def test_dhcp_converging_after_echo_only_bind_avoids_second_setup(self):
        at, _, _, output = self.run_policy(
            new_session=True, pdp='10.0.0.2', dhcp='', times=(1000, 1045, 1090),
            partial='AT*NETACT=1,1,1', dhcp_after=1045)
        self.assertEqual(at, ['AT+CGACT=1,1', 'AT*NETACT=1,1,1'])
        self.assertIn('setup_attempts=2', output)

    def test_service_start_setup_runs_once_even_with_cached_lease(self):
        at, restarts, probes, output = self.run_policy(
            new_session=True, times=(1000, 1045, 1090))
        self.assertEqual(at, ['AT+CGACT=1,1', 'AT*NETACT=1,1,1'])
        self.assertEqual((restarts, probes), (['restart'], []))
        self.assertIn('last_error= rndis_recovery_needed=0', output)
        for dns in ('', '1.1.1.1', '0.0.0.0 1.1.1.1'):
            with self.subTest(dns=dns):
                self.assertEqual(self.run_policy(dns=dns)[:3], ([], [], []))

    def test_explicit_ifdown_and_unready_sim_never_send_at(self):
        settings = ({'autostart': False}, {'disabled': True}, {'proto': 'none'},
                    {'device': 'eth2'}, {'sim': 'absent'}, {'registered': 0})
        for kwargs in settings:
            with self.subTest(**kwargs):
                self.assertEqual(self.run_policy(probe='1.1.1.1', **kwargs)[:3],
                                 ([], [], []))

    def test_normal_setup_binds_even_when_cgact_replies_error(self):
        at, _, _, output = self.run_policy(new_session=True, pdp='', dhcp='', up=False,
                                          fail='AT+CGACT=1,1')
        self.assertEqual(at, ['AT+CGACT=1,1', 'AT*NETACT=1,1,1'])
        self.assertIn('last_error=rndis_setup_unconfirmed', output)

    def test_optional_probe_requires_three_failures_spanning_one_minute(self):
        at, restarts, probes, _ = self.run_policy(
            probe='1.1.1.1', dns='1.1.1.1', times=(1000, 1045, 1090, 1135))
        self.assertEqual(len(probes), 4)
        self.assertEqual(at, ['AT+CEREG? AT+CGACT? AT+CGPADDR',
                              'AT*NETACT=0,1,1', 'AT+CGACT=1,1',
                              'AT*NETACT=1,1,1'])
        self.assertEqual(restarts, ['restart'])

    def test_new_pdp_ip_resets_probe_streak_before_disruptive_rebind(self):
        at, restarts, probes, _ = self.run_policy(
            probe='1.1.1.1', times=(1000, 1045, 1090, 1135, 1180),
            pdp_after=1090)
        self.assertEqual(len(probes), 5)
        self.assertEqual(at, ['AT+CEREG? AT+CGACT? AT+CGPADDR'])
        # The recheck at 1180 still sees the *old* mocked PDP and safely aborts.
        self.assertEqual(restarts, [])

    def test_probe_recovery_resets_failure_streak(self):
        at, restarts, probes, _ = self.run_policy(
            probe='1.1.1.1', times=(1000, 1045, 1090),
            ping_recovers_at=1045)
        self.assertEqual((at, restarts), ([], []))
        self.assertEqual(len(probes), 3)

    def test_manual_ifdown_during_probe_wins_before_disconnect(self):
        at, restarts, probes, _ = self.run_policy(
            probe='1.1.1.1', times=(1000, 1045, 1090), down_at=1090)
        self.assertEqual((at, restarts), ([], []))
        self.assertEqual(len(probes), 3)

    def test_fresh_at_recheck_rejects_stale_pdp_or_registration(self):
        for changed in ({'fresh_reg': '0'}, {'fresh_cgact': '0'},
                        {'fresh_pdp': '10.0.0.3'}):
            with self.subTest(**changed):
                at, restarts, _, _ = self.run_policy(
                    probe='1.1.1.1', times=(1000, 1045, 1090), **changed)
                self.assertEqual(at, ['AT+CEREG? AT+CGACT? AT+CGPADDR'])
                self.assertEqual(restarts, [])

    def test_disconnect_always_attempts_final_bind_even_after_cgact_error(self):
        at, restarts, _, output = self.run_policy(
            probe='1.1.1.1', times=(1000, 1045, 1090),
            fail='AT+CGACT=1,1')
        self.assertEqual(at[-3:], ['AT*NETACT=0,1,1', 'AT+CGACT=1,1',
                                   'AT*NETACT=1,1,1'])
        self.assertEqual(restarts, ['restart'])
        self.assertIn('last_error=rndis_bind_unconfirmed', output)

    def test_explicit_terminal_bind_error_escalates_only_after_two_attempts(self):
        at, restarts, _, output = self.run_policy(
            probe='1.1.1.1', times=(1000, 1045, 1090, 1135, 1180),
            fail='AT*NETACT=1,1,1')
        self.assertEqual(len(at), 8)  # two fresh checks and two 3-command rebinds
        self.assertEqual(restarts, [])
        self.assertIn('last_error=rndis_bind_failed', output)
        self.assertIn('rndis_recovery_needed=1', output)

    def test_late_previous_ok_or_error_is_not_current_bind_result(self):
        for stale in ('stale_ok', 'stale_error'):
            with self.subTest(stale=stale):
                at, restarts, _, output = self.run_policy(
                    probe='1.1.1.1', times=(1000, 1045, 1090, 1135),
                    **{stale: 'AT*NETACT=1,1,1'})
                self.assertEqual(len(at), 8)
                self.assertEqual(restarts, ['restart', 'restart'])
                self.assertIn('rndis_recovery_needed=0', output)

    def test_transport_error_does_not_escalate_radio_reset(self):
        at, restarts, _, output = self.run_policy(
            probe='1.1.1.1', times=(1000, 1045, 1090, 1135, 1180),
            transport_fail='AT*NETACT=1,1,1')
        self.assertEqual(len(at), 8)
        self.assertEqual(restarts, ['restart', 'restart'])
        self.assertIn('rndis_recovery_needed=0', output)

    def test_main_loop_calls_both_policies(self):
        source = SOURCE.read_text()
        self.assertIn('    ensure_setup\n    if [ "$registered" -eq 1 ]', source)
        self.assertIn('    ensure_rndis\n    led_update\n    write_status', source)


if __name__ == '__main__':
    unittest.main()
