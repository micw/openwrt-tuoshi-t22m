include $(TOPDIR)/rules.mk

PKG_NAME:=ml352d
PKG_VERSION:=0.1.0
PKG_RELEASE:=5
PKG_LICENSE:=GPL-2.0-only
PKG_BUILD_DIR:=$(BUILD_DIR)/$(PKG_NAME)

include $(INCLUDE_DIR)/package.mk

define Build/Compile
endef

define Package/ml352d
  SECTION:=net
  CATEGORY:=Network
  SUBMENU:=WWAN
  TITLE:=Lightweight ASR ML352 LTE modem supervisor
  DEPENDS:=+socat +ucode +ucode-mod-fs +kmod-usb-net-rndis +kmod-usb-serial-option
  PKGARCH:=all
endef

define Package/ml352d/conffiles
/etc/config/ml352
endef

define Package/ml352d/install
	$(INSTALL_DIR) $(1)/usr/sbin $(1)/usr/libexec $(1)/etc/init.d $(1)/etc/config $(1)/etc/uci-defaults
	$(INSTALL_BIN) ./ml352d $(1)/usr/sbin/ml352d
	$(INSTALL_BIN) ./ml352-led-chase.uc $(1)/usr/libexec/ml352-led-chase.uc
	$(INSTALL_BIN) ./ml352.init $(1)/etc/init.d/ml352
	$(INSTALL_CONF) ./ml352.config $(1)/etc/config/ml352
	$(INSTALL_BIN) ./95-ml352-defaults $(1)/etc/uci-defaults/95-ml352-defaults
endef

$(eval $(call BuildPackage,ml352d))
