"""
Sector0 - Utility Functions
==============================
Logging, admin checks, and command execution helpers.
"""

import ctypes
import sys
import os
import subprocess
import platform
from typing import Union, List, Optional

# Import config - handle both package and direct execution
import os as _os
import sys as _sys
_this_dir = _os.path.dirname(_os.path.abspath(__file__))
_parent_dir = _os.path.dirname(_this_dir)
if _parent_dir not in _sys.path:
    _sys.path.insert(0, _parent_dir)

try:
    from ..config import LOG_FILE, VERBOSE
except ImportError:
    from config import LOG_FILE, VERBOSE


def log(msg: str, level: str = "INFO") -> None:
    """
    Log message to console and file.
    
    Args:
        msg: Message to log
        level: Log level (INFO, WARNING, ERROR, DEBUG)
    """
    formatted = f"[{level}] {msg}"
    print(formatted)
    
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(formatted + '\n')
    except Exception:
        pass


def init_logging(log_file: str = None, verbose: bool = True) -> None:
    """Initialize logging - clear old log file."""
    target = log_file if log_file else LOG_FILE
    try:
        with open(target, 'w', encoding='utf-8') as f:
            f.write(f"=== Sector0 Installer Log ===\n")
    except Exception:
        pass


def is_windows() -> bool:
    """Check if running on Windows."""
    return platform.system() == "Windows"


def allocate_console() -> None:
    """Allocate a console window for frozen executables (PyInstaller)."""
    if not is_windows():
        return
    
    try:
        ctypes.windll.kernel32.AllocConsole()
    except Exception:
        pass


def is_admin() -> bool:
    """Check if running with administrator privileges."""
    if platform.system() != "Windows":
        return os.geteuid() == 0
    
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def request_admin() -> None:
    """
    Request admin privileges. Restarts the script with elevation if needed.
    Exits the current process if elevation is requested.
    """
    if platform.system() != "Windows":
        if not is_admin():
            log("This script requires root privileges. Run with sudo.", "ERROR")
            sys.exit(1)
        return
    
    if is_admin():
        return
    
    log("Requesting administrator privileges...", "INFO")
    
    try:
        # Re-run the script with elevation
        ctypes.windll.shell32.ShellExecuteW(
            None,
            "runas",
            sys.executable,
            " ".join([f'"{arg}"' for arg in sys.argv]),
            None,
            1  # SW_SHOWNORMAL
        )
    except Exception as e:
        log(f"Failed to request admin privileges: {e}", "ERROR")
    
    sys.exit(0)


def run_cmd(
    cmd: Union[str, List[str]],
    shell: bool = False,
    check: bool = True,
    capture: bool = True
) -> Optional[str]:
    """
    Execute a command and return output.
    
    Args:
        cmd: Command string or list of arguments
        shell: Whether to run through shell
        check: Raise exception on non-zero exit
        capture: Capture and return output
    
    Returns:
        Command stdout if capture=True, else None
    
    Raises:
        subprocess.CalledProcessError on failure if check=True
    """
    if isinstance(cmd, str) and not shell:
        cmd = cmd.split()
    
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture,
            text=True,
            shell=shell,
            encoding='utf-8',
            errors='ignore'
        )
        return result.stdout if capture else None
        
    except subprocess.CalledProcessError as e:
        cmd_str = ' '.join(e.cmd) if isinstance(e.cmd, list) else e.cmd
        log(f"Command failed: {cmd_str}", "ERROR")
        if e.stdout:
            log(f"  stdout: {e.stdout.strip()}", "DEBUG")
        if e.stderr:
            log(f"  stderr: {e.stderr.strip()}", "DEBUG")
        raise


def run_cmd_silent(
    cmd: Union[str, List[str]],
    shell: bool = False
) -> tuple:
    """
    Execute command without raising exceptions.
    
    Returns:
        Tuple of (success: bool, stdout: str, stderr: str)
    """
    if isinstance(cmd, str) and not shell:
        cmd = cmd.split()
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            shell=shell,
            encoding='utf-8',
            errors='ignore'
        )
        return (result.returncode == 0, result.stdout, result.stderr)
    except Exception as e:
        return (False, "", str(e))


# Alias for backwards compatibility
run_cmd_safe = run_cmd_silent
