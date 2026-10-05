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
