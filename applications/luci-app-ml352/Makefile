include $(TOPDIR)/rules.mk

LUCI_TITLE:=LuCI support for ML352 cellular modems
LUCI_DEPENDS:=+luci-base +ml352d +rpcd-mod-ucode
LUCI_PKGARCH:=all
PKG_VERSION:=0.1.0
PKG_RELEASE:=1
PKG_PO_VERSION:=0.1.0-r1
PKG_LICENSE:=GPL-2.0-only

# Reuse the official LuCI build rules; this package lives in a local feed.
include $(TOPDIR)/feeds/luci/luci.mk

# call BuildPackage - OpenWrt buildroot package scanner signature
