include $(TOPDIR)/rules.mk

PKG_NAME:=lt22m-modem-ui
PKG_VERSION:=1
PKG_RELEASE:=1
PKG_LICENSE:=GPL-2.0-only

include $(INCLUDE_DIR)/package.mk

define Package/lt22m-modem-ui
  SECTION:=luci
  CATEGORY:=LuCI
  TITLE:=LT22M modem service and LuCI with German app translation
  DEPENDS:=@TARGET_ramips_mt76x8 +ml352d +luci-app-ml352 +luci-i18n-ml352-de
  PKGARCH:=all
endef

define Build/Compile
endef

define Package/lt22m-modem-ui/install
	:
endef

$(eval $(call BuildPackage,lt22m-modem-ui))
