"""
Sector0 Core Module
======================
Core functionality for the bootkit installer.
"""

from .utils import (
    log, 
    init_logging,
    is_admin, 
    request_admin, 
    run_cmd,
    run_cmd_safe,
    is_windows,
    allocate_console
)
from .disk import DiskManager
from .legacy import LegacyBootInstaller
from .uefi import UEFIBootInstaller

__all__ = [
    'log',
    'init_logging',
    'is_admin', 
    'request_admin',
    'run_cmd',
    'run_cmd_safe',
    'is_windows',
    'allocate_console',
    'DiskManager',
    'LegacyBootInstaller',
    'UEFIBootInstaller',
]
