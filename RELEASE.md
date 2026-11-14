Three firmware images for Tuoshi LT22M, built from pinned OpenWrt fork commits with the ML352 modem service/UI and WireGuard kernel module, tools and LuCI protocol included in every image. `SHA256SUMS` and `BUILD_INFO.txt` accompany the images.

- `*tuoshi_lt22m-squashfs-factory.bin`: OEM stock-layout factory uploader (custom OEM uImage magic).
- `*tuoshi_lt22m-squashfs-sysupgrade.bin`: stock-layout OpenWrt sysupgrade.
- `*tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin`: fullflash OpenWrt sysupgrade, **not** an OEM upload. It requires the checked OpenWrt SPL-family loader. Migrating from stock to fullflash additionally needs `sysupgrade -n` and erases the original B/recovery area; it does not flash the loader.

RC5 builds both stock-layout and fullflash images from the same pinned
fullflash-capable OpenWrt fork. Unlike RC4's stock image, the RC5 stock image
includes `lt22m-bootloader` and the guarded stock→fullflash sysupgrade hook.
The intended path is OEM-web stock factory → booted stock-layout OpenWrt
→ `lt22m-bootloader inspect` / explicit `flash bundled` with full mtd0
readback → `sysupgrade -n` to the fullflash image, without rebooting between
loader and firmware writes. Loader and migration mechanisms were exercised
in development; this exact RC5 image sequence has not yet been device-tested. The firmware image never automatically flashes
the loader. The exact RC5 factory image still needs OEM-web acceptance testing;
its OpenWrt size check is not a measured stock-updater limit. Inspect the
protected partitions and keep an off-device recovery copy before mtd0 writes.

RC4 corrects the ML352 LuCI band label: the German status page now shows "Frequenzband" instead of LuCI-Base's conflicting "Frequenztyp". For ten LTE band numbers offered by the archived stock ASR band selector it appends the nominal standardized band frequency, for example `20 (800 MHz)`; unknown bands and non-LTE modes retain the raw modem value. The frequency is a band name, not an exact measured carrier frequency or a claim that every listed band is supported by this particular modem. The German LuCI translation package is versioned separately so existing installations receive the new string. The modem service itself is unchanged from RC3.

RC3 updates the ML352 supervisor and LuCI status: after registration it sends `AT+CGACT=1,1` followed by `AT*NETACT=1,1,1` without depending on an APN username, and LuCI displays the configured APN. For an already wedged data path it retains the separate `NETACT=0 → CGACT=1 → NETACT=1` recovery. DNS `0.0.0.0` alone no longer triggers a disconnect. Automatic rebind requires an explicitly configured IPv4 ping target reachable through this APN (`ml352.modem.recovery_probe_ip`); it is off by default to avoid disconnects on private APNs. Three failed probes over at least a minute, fresh registration/PDP/network checks and a bounded retry are required; a failed ping alone never authorizes a radio reset. The previously introduced ten-minute modem restart for a genuinely missing mobile connection, manual-ifdown protection and stock/fullflash upgrade guards remain. Normal fullflash-to-fullflash sysupgrade can preserve the existing configuration; `-n` is only required for a stock-to-fullflash migration.

The firmware reports its release tag as its OpenWrt release and the tag plus pinned OpenWrt source commit as its revision, rather than the misleading `r0-1eaea67` from shallow Git history. The packages are compiled for the release image's own kernel ABI. Do not force public OpenWrt snapshot kernel modules onto this firmware. No device-specific Factory contents, bootloader/environment backups, personal credentials or WireGuard private keys are included.
