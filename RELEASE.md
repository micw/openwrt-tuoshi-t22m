# OpenWrt for the Tuoshi LT22M

Experimental firmware for the Tuoshi LT22M 4G router. These images include the
ML352 modem service and LuCI interface, German LuCI translations, and WireGuard.
They are built together from pinned OpenWrt and package-feed sources; see
`BUILD_INFO.txt` for the exact commits and `SHA256SUMS` for the downloaded files.
No device-specific Factory data, credentials or private keys are included.

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

The **exact RC5 factory binary has not yet been tested through the OEM web UI**.
Its size is within the stock Firmware MTD and its OEM image magic, name and CRC
have been checked offline, but web-upload acceptance and staging RAM remain
hardware-dependent. Likewise, the complete RC5 three-step migration has not
been exercised as a single sequence on a factory-stock device. Treat this as
a prerelease and do not force an image past a failed device or upgrade check.

Packages and kernel modules in these images are built for this firmware's
kernel ABI. Public OpenWrt snapshot kernel modules are not interchangeable;
this source repository is not a hosted binary package feed.
