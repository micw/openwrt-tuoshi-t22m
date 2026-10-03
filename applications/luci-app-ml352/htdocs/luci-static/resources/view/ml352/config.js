'use strict';
'require view';
'require form';

function validateDeviceName(section_id, value) {
	return /^[A-Za-z0-9_./:-]+$/.test(value) ||
		_('Use only letters, digits, underscores, dots, slashes, colons and hyphens.');
}

return view.extend({
	render: function() {
		var m, s, o;

		m = new form.Map('ml352', _('ML352 Configuration'),
			_('Configure the ML352 cellular modem. Save & Apply reloads the modem service.'));
		m.readonly = !L.hasViewPermission();

		s = m.section(form.NamedSection, 'modem', 'modem', _('Modem settings'));

		o = s.option(form.Flag, 'enabled', _('Enable modem service'));
		o.default = '1';
		o.rmempty = false;

		o = s.option(form.Value, 'apn', _('APN'),
			_('Leave empty to request the mobile network default APN. The APN is not read from the SIM.'));
		o.placeholder = _('Network default');
		o.validate = function(section_id, value) {
			return !value || /^[A-Za-z0-9._-]+$/.test(value) ||
				_('Use only letters, digits, dots, underscores and hyphens.');
		};

		o = s.option(form.Flag, 'roaming', _('Allow roaming'));
		o.default = '1';
		o.rmempty = false;


		o = s.option(form.Value, 'at_port', _('AT serial port'));
		o.default = '/dev/ttyUSB1';
		o.rmempty = false;
		o.validate = validateDeviceName;

		o = s.option(form.Value, 'netdev', _('Modem network device'));
		o.default = 'eth1';
		o.rmempty = false;
		o.validate = validateDeviceName;

		o = s.option(form.Value, 'interface', _('OpenWrt network interface'));
		o.default = 'lte';
		o.rmempty = false;
		o.validate = validateDeviceName;

		return m.render();
	}
});
