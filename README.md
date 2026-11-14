# Tuoshi LT22M local OpenWrt feed and personal firmware builds

This repository contains the `ml352d` modem service, its LuCI application and the
`lt22m-modem-ui` metapackage. The LTE registration-recovery fix is in
`ml352d` 0.1.0-r3. It contains no device-unique flash dumps, passwords, keys,
or modem credentials. **This source feed is not a hosted APK repository.**

## Downloadable firmware

[Tagged releases](https://github.com/micw/openwrt-tuoshi-t22m/releases) contain
three distinct LT22M images, each with the modem service, LuCI modem UI,
`kmod-wireguard`, `wireguard-tools`, and `luci-proto-wireguard` built together:

| Image suffix | Purpose |
| --- | --- |
| `tuoshi_lt22m-squashfs-factory.bin` | Stock-layout factory image for the OEM updater (OEM uImage magic). |
| `tuoshi_lt22m-squashfs-sysupgrade.bin` | Stock-layout OpenWrt sysupgrade. |
| `tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin` | Fullflash-layout OpenWrt sysupgrade with the checked OpenWrt SPL-family loader (standard uImage magic). **Not** an OEM factory upload. |

The fullflash migration from a stock layout requires an already installed,
validated OpenWrt SPL-family loader and `sysupgrade -n`: the stock B/recovery
area at and beyond 0x7c0000 is erased. The loader itself occupies SPI
0x00000–0x2ffff and is never written by these release-image builds. Preserve
an off-device backup and external SPI recovery before any loader migration.
Do not force an image onto a different board or loader; the runtime upgrade
guards additionally validate the physical MTD layout and loader identity.

These custom kernel modules match **only** the firmware built alongside them;
OpenWrt's public snapshot kmods use a different kernel ABI. The generated
`lt22m` URL in OpenWrt's default `distfeeds.list` is not a hosted binary feed.
Use the released firmware rather than forcing upstream kmods onto this image.

## Build provenance

The Actions workflow uses the immutable fork commits in
[`profiles/sources.env`](profiles/sources.env), the pinned upstream package and
LuCI revisions in [`profiles/feeds.conf`](profiles/feeds.conf), and this
repository's tagged commit for the local feed. Each clean build selects just
one device using [`profiles/stock-v1.config`](profiles/stock-v1.config) or
[`profiles/fullflash-v1.config`](profiles/fullflash-v1.config). The workflow
checks image magic, CRC, metadata, size, required packages, offline guards,
and publishes only the three named binaries plus SHA-256 sums and source pins.
The visible OpenWrt release is the Git tag; its revision is the tag followed by
the short, pinned OpenWrt source commit (for example
`v0.1.0-rc1-81cc3e5`). This is set explicitly instead of relying on
OpenWrt's Git-history counter in a shallow checkout. Manual
`workflow_dispatch` runs build artifacts without creating a release; a `v*`
tag publishes a prerelease once both builds pass. RC1 test builds may replace
the RC1 tag and its assets: always verify the current `SHA256SUMS`.

A release image is not a bootloader installer or a backup of a physical device.
The source feed does not replace OpenWrt's standard package feeds.

## ML352 data connection (0.1.0-r7)

After registration, `ml352d` sends `AT+CGACT=1,1` followed by
`AT*NETACT=1,1,1` **regardless of whether an APN username exists**. The
non-disconnecting setup runs once when the service takes over a connection
and after a newly observed registration or PDP loss, not every status poll.

A wedged RNDIS data path has a separate, bounded recovery sequence:
`AT*NETACT=0,1,1` → `AT+CGACT=1,1` → `AT*NETACT=1,1,1`, followed by a fresh
DHCP request. DNS `0.0.0.0` alone no longer triggers it. Automatic rebind is
**off by default**, since private APNs may have no access to public hosts.
To opt in, configure an IPv4 address that reliably answers ICMP *via this
specific APN*, e.g. on a public Telekom APN:

```sh
uci set ml352.modem.recovery_probe_ip='1.1.1.1'
uci commit ml352
/etc/init.d/ml352 restart
```

The supervisor pings through the modem interface every 45 seconds only while
CID 1, DHCP and the network interface are up. Three consecutive failures over
at least 60 seconds, followed by fresh modem and network checks, permit at
most two rebinds until the probe succeeds. An unreachable probe alone does
not authorize a radio reset. Leave this option empty for private APNs unless
you have a reachable, operator-controlled endpoint; a blocked ping target
otherwise causes unnecessary rebinds. The rebind policy has offline tests;
a controlled hardware failure/recovery test remains outstanding.

## ML352 band display

LuCI shows the raw numeric `AT*BANDIND?` band value. When `AT^SYSINFO` also
identifies LTE and the number matches one of B1/B3/B5/B7/B8/B20/B28/B38/B40/B41,
it adds that standardized band's **nominal** MHz name, e.g. `20 (800 MHz)`.
This is not the measured carrier frequency or channel bandwidth. Unknown
numbers and non-LTE radio modes retain the raw modem value. The stock ASR
firmware permits those ten LTE band-lock switches for its JD3_AFL variant;
this does **not** establish that the actual LT22M modem has that variant or
that these switches exhaust its hardware RF capabilities. No ML352-specific
`AT*BANDIND?` manual or complete 3G band list has been verified. The ten
band-lock choices come from the separately archived Tuoshi ASR stock UI;
nominal LTE frequencies follow [ETSI TS 136 101, table 5.5-1](https://www.etsi.org/deliver/etsi_ts/136100_136199/136101/15.09.00_60/ts_136101v150900p.pdf).
