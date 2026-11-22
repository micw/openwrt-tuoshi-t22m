# OpenWrt for the Tuoshi LT22M

OpenWrt firmware for the Tuoshi LT22M 4G router. Version 1.0.0 replaces the
legacy ML352 modem daemon with wwand's ML352 NCM adapter and LuCI status app;
it also includes WireGuard. The wwand source is pinned to a tested fork commit;
LuCI sources and package recipes are vendored in this tagged image feed. See
`BUILD_INFO.txt` for exact commits and `SHA256SUMS` for image checksums. No
SIM PIN, APN, device-specific Factory data, credentials or private keys are
included in generic images.

## Changes in v1.0.1

- wwand completes the ML352 RNDIS DHCP handshake before reporting the data
  session as connected, without applying lease addresses, DNS, or routes.
- netifd reinstalls routes when the L3 device is replaced under the same name
  with a different kernel interface index.
- The combined Fullflash release candidate recovered LTE and HTTPS automatically
  after an upgrade reboot and a separate ML352 USB re-enumeration on hardware.
  A physical power cycle and stock OEM installation were not tested.

## Choose the image for your bootloader and flash layout

| Release file | Use |
| --- | --- |
| `openwrt-ramips-mt76x8-tuoshi_lt22m-squashfs-factory.bin` | **First OpenWrt installation through the original stock web updater.** OEM-compatible uImage for the original bootloader and two-slot *stock layout*. It writes stock slot A; it does not install a bootloader. |
| `openwrt-ramips-mt76x8-tuoshi_lt22m-squashfs-sysupgrade.bin` | Subsequent **stock-layout OpenWrt** upgrades. Use with `sysupgrade`, **not** the OEM web updater. |
| `openwrt-ramips-mt76x8-tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin` | Migration to, or upgrade of, **fullflash OpenWrt**. Standard uImage; requires the compatible LT22M OpenWrt SPL/U-Boot already in mtd0. **Never upload this file to the stock web updater.** |

In the **stock layout**, the original bootloader remains installed. OpenWrt
uses the first firmware slot beginning at `0x50000`; stock Storage and firmware
slot B remain separate. This layout preserves the original bootloader's B→A
recovery behavior.

In the **fullflash layout**, the replacement bootloader uses a single firmware
partition from `0x50000` to the end of the 16-MiB SPI NOR. The former Storage,
second firmware slot and stock B→A fallback are removed. The bootloader
(`0x00000–0x2ffff`), Environment (`0x30000–0x3ffff`) and unique Factory data
(`0x40000–0x4ffff`) are separate from that firmware partition.

## From stock to fullflash

1. Install the **stock-layout factory image** through the original web UI and
   boot OpenWrt. Save verified off-device copies of the bootloader, Environment,
   Factory, stock Storage and firmware slot B before changing the layout.
2. In the running stock-layout OpenWrt, use `lt22m-bootloader inspect` to check
   the board, flash layout and installed bootloader. The bundled tool and
   matching U-Boot are included in this release's stock image. Run
   `lt22m-bootloader flash bundled` **explicitly** when ready; it writes only
   mtd0, verifies the entire 192-KiB readback and does **not** reboot. An
   interrupted or incompatible bootloader write requires external SPI recovery.
3. **Without rebooting between the bootloader and firmware writes**, copy the
   fullflash sysupgrade image to `/tmp` and run:

   ```sh
   sysupgrade -T -n /tmp/openwrt-ramips-mt76x8-tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin
   sysupgrade -n /tmp/openwrt-ramips-mt76x8-tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin
   ```

   The migration guard requires the LT22M OpenWrt SPL-family marker and a
   CRC-valid second stage, matching physical MTD layout and valid firmware. It
   refuses configuration-backup migration; `-n` is required for this one-time
   layout change. The firmware step does not rewrite mtd0, Environment or
   Factory. After a successful fullflash boot, ordinary fullflash sysupgrades
   can preserve configuration.

The LT22M fullflash image's ML352 wwand adapter was tested on two running
fullflash routers. On the second, an unset APN obtained native LTE IPv4 and two
DNS servers; bound IP/hostname traffic and an interface reconnect passed after
the CGACT read-before-activation fix. SIM PINs belong in the router's preserved
UCI configuration; this generic image carries none. A forced modem-failure
recovery sequence has not been tested.

The **v1.0.0 stock factory binary has not been installed through the OEM web UI**.
Its size and OEM image magic/name/CRC are checked offline, but exact web-upload
acceptance and staging RAM remain hardware-dependent. The complete
stock→fullflash three-step migration has not been exercised as one sequence on
a factory-stock device. Do not force an image past a failed device/upgrade check.

Packages and kernel modules in these images are built for this firmware's
kernel ABI. Public OpenWrt snapshot kernel modules are not interchangeable;
this source repository is not a hosted binary package feed.
