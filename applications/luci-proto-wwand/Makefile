#
# LuCI network-manager protocol handler for the wwand modem daemon.
# Registers only the 'wwand' protocol UI (protocol/wwand.js). It deliberately
# does NOT ship a 'qmi' alias: `proto qmi` stays with luci-proto-qmi/uqmi (no
# file collision, good-citizen coexistence), and interfaces are moved to
# `proto wwand` via the migration list in the LuCI modem page.
#
# Source htdocs/root is committed below src/ in the tagged LT22M feed.
# Install explicitly from PKG_BUILD_DIR; luci.mk would not build this layout.
# Update PKG_VERSION/RELEASE for the release's package identity.
# No remote LuCI checkout, mirror hash, or fork is needed at build time.

include $(TOPDIR)/rules.mk

PKG_NAME:=luci-proto-wwand
PKG_VERSION:=1.7.0_pre1
PKG_RELEASE:=1


PKG_LICENSE:=GPL-2.0-only
PKG_MAINTAINER:=

include $(INCLUDE_DIR)/package.mk

define Package/luci-proto-wwand
  SECTION:=luci
  CATEGORY:=LuCI
  SUBMENU:=4. Protocols
  TITLE:=Support for QMI/5G cellular modems (wwand)
  # This handler uses five resource modules that luci-app-wwand ships —
  # wwand.bands, .format, .modemopts, .modemsid and .rpc — so it depends on
  # the app rather than carrying a second copy of them.
  DEPENDS:=+luci-base +wwand +luci-app-wwand
  PKGARCH:=all
endef

define Package/luci-proto-wwand/description
  LuCI protocol handler for the wwand cellular modem daemon: the network-native
  'wwand' proto only; the legacy 'qmi' proto remains with uqmi.
endef

# Immutable source is vendored in this tagged feed; never build in src itself.
define Build/Prepare
	mkdir -p $(PKG_BUILD_DIR)
	$(CP) ./src/. $(PKG_BUILD_DIR)/
endef

define Build/Compile
endef

define Package/luci-proto-wwand/install
	$(INSTALL_DIR) $(1)/www/luci-static/resources/protocol
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/htdocs/luci-static/resources/protocol/*.js \
		$(1)/www/luci-static/resources/protocol/
	$(INSTALL_DIR) $(1)/usr/share/rpcd/acl.d
	$(INSTALL_DATA) $(PKG_BUILD_DIR)/root/usr/share/rpcd/acl.d/*.json \
		$(1)/usr/share/rpcd/acl.d/
endef

$(eval $(call BuildPackage,luci-proto-wwand))
