# Tuoshi LT22M local OpenWrt feed and personal firmware builds

This repository carries the LT22M firmware profiles and the local wwand/ML352
integration for v1.0.0. The older `ml352d` daemon and LuCI sources remain here
for historic images but are excluded from the wwand profiles. The feed contains
no device-unique flash dumps, passwords, keys or modem credentials. **This
source feed is not a hosted APK repository.**

## Downloadable firmware

[Tagged releases](https://github.com/micw/openwrt-tuoshi-t22m/releases) contain
three distinct LT22M images, each with the modem service, LuCI modem UI,
`kmod-wireguard`, `wireguard-tools`, and `luci-proto-wireguard` built together:

| Image suffix | Purpose |
| --- | --- |
| `tuoshi_lt22m-squashfs-factory.bin` | Stock-layout factory image for the OEM updater (OEM uImage magic). |
| `tuoshi_lt22m-squashfs-sysupgrade.bin` | Stock-layout OpenWrt sysupgrade. |
| `tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin` | Fullflash-layout OpenWrt sysupgrade with the checked OpenWrt SPL-family loader (standard uImage magic). **Not** an OEM factory upload. |

Starting with RC5, both device images are built from the *same* pinned
fullflash-capable OpenWrt fork commit, with distinct stock and fullflash device
profiles. The stock-layout image bundles the `lt22m-bootloader` tool and its
matching SPL/U-Boot binary, but installing the image never writes mtd0. After
booting the OEM-uploaded stock-layout factory image, inspect the live layout
and bootloader with `lt22m-bootloader inspect`, save an off-device backup, then
explicitly run `lt22m-bootloader flash bundled`. This interactive operation
writes only mtd0 (SPI `0x000000–0x02ffff`), checks the full readback and does
not reboot. Without an intervening reboot, use `sysupgrade -T -n` followed by
`sysupgrade -n` with the matching fullflash sysupgrade image. The stock-layout
sysupgrade hook checks the OpenWrt SPL-family marker **and** a CRC-valid
second stage, physical MTD layout, firmware image and no-settings migration
before writing firmware in its RAM stage. This conversion destroys the old
stock B/recovery space at and beyond `0x7c0000`; it does not write mtd0,
Environment or Factory. Keep an external SPI recovery method for an interrupted
loader write. Never force an incompatible image through a failed board check.

The built factory image must also pass the original OEM web updater. Offline
inspection of stock `jhttpd` shows an upload-length check against the runtime
`Firmware` MTD size (`0x770000` bytes = 7616 KiB), **not** the historical
6150-KiB guess. Our 7104-KiB build cap is below that bound, but neither bound
proves acceptance: the updater also checks OEM image identity/CRC and requires
free `/tmp` RAM for staging. RC5's exact factory binary has not been uploaded
through the OEM UI on hardware; treat that first-install step as unverified.

These custom kernel modules match **only** the firmware built alongside them;
OpenWrt's public snapshot kmods use a different kernel ABI. The generated
`lt22m` URL in OpenWrt's default `distfeeds.list` is not a hosted binary feed.
Use the released firmware rather than forcing upstream kmods onto this image.

## Build provenance

The Actions workflow uses immutable OpenWrt and wwand source commits in
[`profiles/sources.env`](profiles/sources.env), pinned OpenWrt package/LuCI
revisions in [`profiles/feeds.conf`](profiles/feeds.conf), and this repository's
tagged commit for the vendored wwand/LuCI package recipes and LuCI resources. Each clean build selects just
one device using [`profiles/stock-v1.config`](profiles/stock-v1.config) or
[`profiles/fullflash-v1.config`](profiles/fullflash-v1.config). The workflow
checks image magic, CRC, metadata, size, required packages, offline guards,
and publishes only the three named binaries plus SHA-256 sums and source pins.
The visible OpenWrt release is the Git tag; its revision is the tag followed by
the short, pinned OpenWrt source commit (for example
`v1.0.0-8424280`). This is set explicitly instead of relying on OpenWrt's
Git-history counter in a shallow checkout. Manual `workflow_dispatch` runs
build artifacts without creating a release; a `v*` tag publishes only after
both images pass verification. `v1.0.0` is a stable GitHub release, whereas
`*-rc*` tags remain prereleases. Always verify the published `SHA256SUMS`.

A release image is not a bootloader installer or a backup of a physical device.
The source feed does not replace OpenWrt's standard package feeds.

## wwand/ML352 integration for v1.0.0

The stock and fullflash profiles select the modern wwand
NCM backend, its LuCI app/protocol and a board-gated `lt22m-wwand` package,
not `ml352d` or `luci-app-ml352`. Both board IDs get modular JSON `tech`
LEDs; GPIO1/38 are intentionally not modem power/reset controls. A fresh
LT22M uses wwand for modem control and its native IPv4 /32 plus NOARP device
route on the renamed RNDIS link `wwand0`. The ML352 adapter merges DNS from a
CGCONTRDP response matching the assigned CGPADDR address. The revised
upstream-dialect fullflash test image was installed on 2026-11-17: native `lte`
now owns IPv4 and both carrier DNS servers; bound LTE traffic and reconnect
passed, and the old dynamic DHCP child `lte_4` is absent.
A known old `lte proto dhcp device eth1` is migrated in place; custom LTE
configurations are preserved. The internal modem is anchored by USB port `1-1`
so `eth1`→`wwand0` renaming does not break daemon rediscovery. ML352 reads
`CGACT?` before repeating PDP activation, avoiding CME on an already active
bearer. Serving and neighbour cells are read-only raw indices. ML352 AT*CELL
has no safe readback and no extra selection API is included.

For a reproducible local release build, use the two pinned OpenWrt source
revisions and feed configuration from `profiles/`, select the appropriate
`*-v1.config` profile, install this feed's `wwand`, `luci-app-wwand` and
`luci-proto-wwand` packages, then build and run `scripts/verify_images.py`.
A separate, older stock-only **development** tree without the
`lt22m-bootloader` package cannot produce a loader-migration-capable stock
release image; do not publish its locally checked binaries.
The release workflow refuses to publish without a pinned ML352 source commit
and a verified SDK mirror hash. The first fullflash tests on 2026-11-16/17
proved wwand's native IPv4/DNS but preceded a second-router edge case. On
2026-11-22 the Segelverein fullflash LT22M was upgraded with preserved LAN,
WireGuard and SIM configuration; after the stable-USB-path and idempotent-PDP
fixes, the SIM reached LTE with **no explicit APN**. Native IPv4, two DNS
servers, bound traffic, interface reconnect and protected-MTD checks passed.
The SIM PIN was configured only on that router, not embedded in an image.
Forced modem-failure recovery remains untested. Details, hardware observations and limits are in the local
wwand worktree's `docs/lt22m-ml352.md`.

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

## ML352 runtime APN display

The status view reads CID 1 from the modem's `AT+CGDCONT?` response through
`ml352d` rather than displaying the UCI setting. An empty but valid modem APN
is shown as "No APN configured in modem"; missing or malformed replies are
unknown (`—`). A network-selected default APN cannot be inferred from an
empty modem context. The configured UCI APN remains available in the settings
page and controls modem configuration, but is not substituted for telemetry.

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
