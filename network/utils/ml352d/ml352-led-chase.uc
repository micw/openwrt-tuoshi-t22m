#!/usr/bin/env ucode
'use strict';

import { stat, writefile } from 'fs';

/* This process is the only writer while LTE connection setup is animated.
 * Exit when the owning ml352d shell disappears, even after an unclean kill.
 */
const owner = +ARGV[0];
const led_dir = getenv('ML352_LED_ROOT') || '/sys/class/leds';
const leds = [ '2', '3', '4' ];

if (!owner || owner <= 1)
	exit(1);

function led_path(name, attr) {
	return `${led_dir}/blue:mobile-${name}/${attr}`;
}

function all_off() {
	for (let led in leds) {
		if (stat(led_path(led, 'brightness')) != null)
			writefile(led_path(led, 'brightness'), '0\n');
	}
}

for (let led in leds) {
	if (stat(led_path(led, 'trigger')) != null)
		writefile(led_path(led, 'trigger'), 'none\n');
}
all_off();

while (stat(`/proc/${owner}`) != null) {
	let stepped = false;
	for (let led in leds) {
		if (stat(`/proc/${owner}`) == null)
			break;
		if (stat(led_path(led, 'brightness')) == null)
			continue;
		writefile(led_path(led, 'brightness'), '1\n');
		sleep(500);
		stepped = true;
		writefile(led_path(led, 'brightness'), '0\n');
	}
	/* All LED paths may be missing during USB/board setup. Keep the
	 * worker bounded rather than spinning through the empty for loop.
	 */
	if (!stepped)
		sleep(500);
}

all_off();
