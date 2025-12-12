"""
Sector0 Core Module
======================
Core functionality for the bootkit installer.
"""

import os as _os
import sys as _sys

# Ensure parent directory is in path for imports
_this_dir = _os.path.dirname(_os.path.abspath(__file__))
_parent_dir = _os.path.dirname(_this_dir)
if _parent_dir not in _sys.path:
    _sys.path.insert(0, _parent_dir)

try:
    from .utils import (
        log, 
        init_logging,
        is_admin, 
        request_admin, 
        run_cmd,
        run_cmd_safe,
        run_cmd_silent,
        is_windows,
        allocate_console
    )
    from .disk import DiskManager
    from .legacy import LegacyBootInstaller
    from .uefi import UEFIBootInstaller
except ImportError:
    from core.utils import (
        log, 
        init_logging,
        is_admin, 
        request_admin, 
        run_cmd,
        run_cmd_safe,
        run_cmd_silent,
        is_windows,
        allocate_console
    )
    from core.disk import DiskManager
    from core.legacy import LegacyBootInstaller
    from core.uefi import UEFIBootInstaller

__all__ = [
    'log',
    'init_logging',
    'is_admin', 
    'request_admin',
    'run_cmd',
    'run_cmd_safe',
    'run_cmd_silent',
    'is_windows',
    'allocate_console',
    'DiskManager',
    'LegacyBootInstaller',
    'UEFIBootInstaller',
]
