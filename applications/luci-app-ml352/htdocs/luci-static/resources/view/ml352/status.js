'use strict';
'require view';
'require rpc';
'require uci';
'require poll';
'require dom';

var callStatus = rpc.declare({
	object: 'luci.ml352',
	method: 'status',
	expect: {}
});

function loadStatus() {
	uci.unload('ml352');

	return Promise.all([
		L.resolveDefault(callStatus(), null),
		L.resolveDefault(uci.load('ml352'), null)
	]).then(function(results) {
		return {
			status: results[0],
			apn: results[1] == null ? null :
				(uci.get('ml352', 'modem', 'apn') || _('Network default'))
		};
	});
}

function display(value) {
	return value === null || value === undefined || value === '' ? '\u2014' : String(value);
}

function updatedTime(value) {
	var seconds = Number(value);
	return value && isFinite(seconds) && seconds > 0 ?
		new Date(seconds * 1000).toLocaleString() : value;
}

function registrationLabel(value) {
	switch (String(value)) {
	case '0': return _('Not registered');
	case '1': return _('Home network');
	case '2': return _('Searching');
	case '3': return _('Registration denied');
	case '5': return _('Roaming');
	default: return value;
	}
}

function simStateLabel(value) {
	switch (value) {
	case 'ready': return _('Ready');
	case 'absent': return _('SIM not inserted');
	case 'unavailable': return _('Modem unavailable');
	case 'unknown': return _('Unknown');
	default: return value;
	}
}

// Nominal standardized LTE band frequencies, not the exact carrier frequency
// or a list of this module's RF capabilities. Unknown/other-RAT values stay raw.
var lteBandMHz = {
	'1': 2100,
	'3': 1800,
	'5': 850,
	'7': 2600,
	'8': 900,
	'20': 800,
	'28': 700,
	'38': 2600,
	'40': 2300,
	'41': 2500
};

function bandLabel(status) {
	var band = status.band == null ? '' : String(status.band);

	if (status.rat === 'lte' && Object.prototype.hasOwnProperty.call(lteBandMHz, band))
		return band + ' (' + lteBandMHz[band] + ' MHz)';

	return status.band;
}

function row(label, value) {
	return E('tr', { 'class': 'tr' }, [
		E('td', { 'class': 'td', 'width': '33%' }, E('strong', {}, label)),
		E('td', { 'class': 'td' }, document.createTextNode(display(value)))
	]);
}

return view.extend({
	load: loadStatus,

	renderStatus: function(data) {
		var status = data.status;

		if (!status || status.available === false || status.available === 0)
			return E('div', {}, [
				E('div', { 'class': 'alert-message warning' },
					_('ML352 live status is unavailable. Check that the modem service is running.')),
				E('div', { 'class': 'cbi-section' },
					E('table', { 'class': 'table' }, row(_('APN'), data.apn)))
			]);

		var stale = Number(status.updated) > 0 &&
			(Date.now() / 1000 - Number(status.updated) > 90);

		var section = E('div', { 'class': 'cbi-section' }, [
			E('h3', {}, _('Modem and network')),
			E('table', { 'class': 'table' }, [
				row(_('SIM state'), simStateLabel(status.sim_state)),
				row(_('ICCID'), status.iccid),
				row(_('APN'), data.apn),
				row(_('Registered'), status.registered == null ? null :
					(status.registered === true || status.registered === 1 || status.registered === '1' ? _('Yes') : _('No'))),
				row(_('Registration'), registrationLabel(status.registration)),
				row(_('Radio access technology'), status.rat),
				row(_('Operator'), status.operator),
				row(_('Signal quality (CSQ)'), status.csq),
				row(_('RSSI (dBm)'), status.rssi_dbm),
				row(_('ML352 frequency band'), bandLabel(status)),
				row(_('PDP IP address'), status.pdp_ip),
				row(_('DHCP IP address'), status.dhcp_ip),
				row(_('Last error'), status.last_error),
				row(_('Last updated'), updatedTime(status.updated))
			])
		]);

		if (stale)
			section.insertBefore(E('div', { 'class': 'alert-message warning' },
				_('The modem status has not been updated recently.')), section.firstChild);

		return section;
	},

	render: function(data) {
		var container = E('div');
		var content = E('div', {}, [
			E('h2', {}, _('ML352 Status')),
			E('div', { 'class': 'cbi-map-descr' }, [
				_('Read-only modem status and configured APN. Refreshes every five seconds.'),
				' ',
				_('SIM state and ICCID are checked at most once per minute.')
			]),
			container
		]);

		dom.content(container, this.renderStatus(data));
		poll.add(L.bind(function() {
			return loadStatus().then(L.bind(function(updated) {
				dom.content(container, this.renderStatus(updated));
			}, this));
		}, this), 5);

		return content;
	},

	handleSaveApply: null,
	handleSave: null,
	handleReset: null
});
