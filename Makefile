# Master Makefile
# Builds all components

.PHONY: all bootkits rootkits clean

all: bootkits

# Build bootkit payloads
bootkits:
	@echo "Building bootkits..."
	@$(MAKE) -C bootkits/sector0 payloads

# Clean all build artifacts
clean:
	@echo "Cleaning all..."
	@$(MAKE) -C bootkits/sector0 clean

# Test Python syntax
test:
	@echo "Testing Python modules..."
	@$(MAKE) -C bootkits/sector0 test

# Show structure
tree:
	@find . -type f -name "*.py" -o -name "*.cpp" -o -name "*.asm" -o -name "*.c" | \
		grep -v __pycache__ | sort
