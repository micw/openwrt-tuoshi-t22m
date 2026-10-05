Three firmware images for Tuoshi LT22M, built from pinned OpenWrt fork commits with the ML352 modem service/UI and WireGuard kernel module, tools and LuCI protocol included in every image. `SHA256SUMS` and `BUILD_INFO.txt` accompany the images.

- `*tuoshi_lt22m-squashfs-factory.bin`: OEM stock-layout factory uploader (custom OEM uImage magic).
- `*tuoshi_lt22m-squashfs-sysupgrade.bin`: stock-layout OpenWrt sysupgrade.
- `*tuoshi_lt22m_fullflash-squashfs-sysupgrade.bin`: fullflash OpenWrt sysupgrade, **not** an OEM upload. It requires the checked OpenWrt SPL-family loader. Migrating from stock to fullflash additionally needs `sysupgrade -n` and erases the original B/recovery area; it does not flash the loader.

The firmware reports this RC1 tag as its OpenWrt release and the tag plus pinned OpenWrt source commit as its revision, rather than the misleading `r0-1eaea67` from shallow Git history. The packages are compiled for the release image's own kernel ABI. Do not force public OpenWrt snapshot kernel modules onto this firmware. No device-specific Factory contents, bootloader/environment backups, personal credentials or WireGuard private keys are included.
