include $(TOPDIR)/rules.mk

PKG_NAME:=lt22m-wwand
PKG_VERSION:=1
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define Package/lt22m-wwand
  SECTION:=net
  CATEGORY:=Network
  SUBMENU:=WWAN
  TITLE:=LT22M ML352 wwand profile and first-boot network defaults
  DEPENDS:=@TARGET_ramips_mt76x8 +wwand-ncm +luci-app-wwand +luci-proto-wwand +kmod-usb-serial-option
  PKGARCH:=all
endef

define Build/Compile
endef

define Package/lt22m-wwand/install
	$(INSTALL_DIR) $(1)/etc/uci-defaults $(1)/usr/share/wwand/boards.d
	$(INSTALL_BIN) ./files/95-lt22m-wwand $(1)/etc/uci-defaults/
	$(INSTALL_DATA) ./files/tuoshi,lt22m.json $(1)/usr/share/wwand/boards.d/
	$(INSTALL_DATA) ./files/tuoshi,lt22m-fullflash.json $(1)/usr/share/wwand/boards.d/
endef

$(eval $(call BuildPackage,lt22m-wwand))
