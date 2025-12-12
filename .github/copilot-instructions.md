# Sector0 - AI Coding Agent Instructions

Sector0 is an MBR/VBR bootkit targeting Windows Legacy BIOS systems. This is low-level security research code—exercise caution.

## Architecture Overview

```
installer.py          → Entry point (CLI, admin elevation, mode detection)
    ↓
core/disk.py          → DiskManager: raw disk I/O via Windows kernel32 API
    ↓
core/legacy.py        → LegacyBootInstaller: MBR/VBR hijacking
core/uefi.py          → UEFIBootInstaller: ESP manipulation, BCD config (experimental)
    ↓
payloads/bootloader.asm  → 16-bit Real Mode x86 assembly (512-byte MBR payload)
payloads/BOOTX64.c       → UEFI C payload (not fully tested)
```

**Data flow**: Python installer → Windows raw disk API (`\\.\PhysicalDrive0`) → writes payload binary to sector 0 (MBR) → reboot triggers BIOS to load payload at `0x7C00`.

## Build Commands

```bash
# Build all payloads (NASM for .asm, mingw for .c)
make payloads

# Build Legacy BIOS payload only
nasm -f bin payloads/bootloader.asm -o payloads/bootloader.bin

# Build UEFI payload (requires mingw-w64)
cd payloads && ./build.sh

# Validate Python syntax
make test

# Package for distribution
make package
```

## Testing with QEMU

```bash
dd if=/dev/zero of=disk.img bs=512 count=2048
dd if=payloads/bootloader.bin of=disk.img conv=notrunc
qemu-system-i386 -hda disk.img
```

## Code Conventions

- **Python**: ctypes for Windows API calls—see `core/disk.py` for kernel32 patterns
- **Assembly**: NASM syntax with `[org 0x7C00]` and `DS=0` segment setup (bug fix documented in `bootloader.asm` lines 23-35)
- **Logging**: Use `log(msg, level)` from `core/utils.py`—writes to console and `installer.log`
- **Config**: All tunables in `config.py`—prefer config dicts (`UEFI`, `BIOS`, `INSTALLER`) over raw constants

## Key Patterns

### Windows Raw Disk Access (`core/disk.py`)
```python
handle = kernel32.CreateFileW(
    "\\\\.\\PhysicalDrive0",
    GENERIC_WRITE,
    FILE_SHARE_READ | FILE_SHARE_WRITE,
    None, OPEN_EXISTING, 0, None
)
kernel32.WriteFile(handle, bootloader_bin, 512, ...)
```

### Real Mode Segment Setup (`payloads/bootloader.asm`)
```asm
xor ax, ax      ; DS=ES=0 for org 0x7C00
mov ds, ax      ; Critical: wrong segment = wrong memory access
mov es, ax
```

## Important Constraints

- **Windows-only**: Installer uses Windows APIs exclusively (`ctypes.windll`)
- **Admin required**: Raw disk access needs elevation—`is_admin()` / `request_admin()` handle this
- **Legacy BIOS only**: MBR payloads don't work with UEFI Secure Boot
- **Payload size**: MBR must be exactly 512 bytes with `0xAA55` signature at offset 510

## UEFI Support Status

UEFI code in `core/uefi.py` and `payloads/BOOTX64.c` exists but is **not fully tested**. The README explicitly notes this.

## Documentation

- `docs/ATTACK_FLOW.md` — Full infection chain with diagrams
- `docs/BOOTLOADER_EXPLAINED.md` — Assembly walkthrough with memory layout

## firmware_sources/

Contains EDK2 and SeaBIOS source trees for reference. These are **not built** as part of the main project—they exist for research context.
