PYTHON      := python3
PKG_NAME    := baxters-power-goo
PKG_VERSION := 1.0.0

# All paths are RELATIVE — never derive absolute paths from Makefile location.
# Spaces in directory names break $(shell dirname ...) expansions in make,
# which was the root cause of a previous catastrophic rm -rf incident.

INSTALL_LIB   := debian/usr/lib/$(PKG_NAME)
INSTALL_BIN   := debian/usr/bin
INSTALL_APPS  := debian/usr/share/applications
ICON_DIR      := debian/usr/share/icons/hicolor

ICON_STAGING_16  := debian/icons/hicolor/16x16/apps
ICON_STAGING_32  := debian/icons/hicolor/32x32/apps
ICON_STAGING_48  := debian/icons/hicolor/48x48/apps
ICON_STAGING_256 := debian/icons/hicolor/256x256/apps

.PHONY: all clean icons test build-deb clean-deb _stage _build

all: icons

# ── Icons ──────────────────────────────────────────────────────────────────
icons:
	$(PYTHON) generate_icon.py

# ── Tests ──────────────────────────────────────────────────────────────────
test:
	PYTHONPATH=src $(PYTHON) -m pytest tests/ -v

# ── .deb packaging ─────────────────────────────────────────────────────────
build-deb: clean-deb icons _stage _build

clean-deb:
	rm -rf debian/usr dist/

_stage:
	# --- application files ---
	mkdir -p $(INSTALL_LIB)/assets
	mkdir -p $(INSTALL_LIB)/src
	mkdir -p $(INSTALL_BIN)
	mkdir -p $(INSTALL_APPS)
	mkdir -p $(ICON_DIR)/16x16/apps
	mkdir -p $(ICON_DIR)/32x32/apps
	mkdir -p $(ICON_DIR)/48x48/apps
	mkdir -p $(ICON_DIR)/256x256/apps

	cp main.py             $(INSTALL_LIB)/
	cp -r src/             $(INSTALL_LIB)/
	cp assets/icon_16.png  $(INSTALL_LIB)/assets/
	cp assets/icon_32.png  $(INSTALL_LIB)/assets/
	cp assets/icon_48.png  $(INSTALL_LIB)/assets/
	cp assets/icon_256.png $(INSTALL_LIB)/assets/

	# --- launcher ---
	cp scripts/$(PKG_NAME) $(INSTALL_BIN)/$(PKG_NAME)
	chmod 0755             $(INSTALL_BIN)/$(PKG_NAME)

	# --- desktop / icons ---
	cp debian/$(PKG_NAME).desktop               $(INSTALL_APPS)/
	cp $(ICON_STAGING_16)/$(PKG_NAME).png       $(ICON_DIR)/16x16/apps/
	cp $(ICON_STAGING_32)/$(PKG_NAME).png       $(ICON_DIR)/32x32/apps/
	cp $(ICON_STAGING_48)/$(PKG_NAME).png       $(ICON_DIR)/48x48/apps/
	cp $(ICON_STAGING_256)/$(PKG_NAME).png      $(ICON_DIR)/256x256/apps/

_build:
	mkdir -p dist
	dpkg-deb --build --root-owner-group debian \
	    dist/$(PKG_NAME)_$(PKG_VERSION)_all.deb
	@echo "Built: dist/$(PKG_NAME)_$(PKG_VERSION)_all.deb"

# ── Clean ──────────────────────────────────────────────────────────────────
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	rm -rf dist/ assets/*.png
