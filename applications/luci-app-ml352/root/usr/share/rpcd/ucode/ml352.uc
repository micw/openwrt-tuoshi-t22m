#!/usr/bin/env ucode
'use strict';

import { readfile } from 'fs';

/* The daemon is the sole owner of the AT port. RPC exposes only safe status. */
const status_path = '/var/run/ml352/status.json';

function get_status() {
	let data;

	try {
		data = json(readfile(status_path));
	}
	catch (e) {
		return { available: false };
	}

	if (type(data) != 'object' || data == null)
		return { available: false };

	/* Read-only ACL: ICCID is shown to authenticated LuCI users, never logged.
	 * PIN, IMSI and IMEI remain unexposed.
	 */
	return {
		available: true,
		sim_state: data.sim_state,
		iccid: data.iccid,
		registered: data.registered,
		registration: data.registration,
		rat: data.rat,
		operator: data.operator,
		csq: data.csq,
		rssi_dbm: data.rssi_dbm,
		band: data.band,
		pdp_ip: data.pdp_ip,
		dhcp_ip: data.dhcp_ip,
		last_error: data.last_error,
		updated: data.updated
	};
}

return {
	'luci.ml352': {
		status: { call: get_status }
	}
};
