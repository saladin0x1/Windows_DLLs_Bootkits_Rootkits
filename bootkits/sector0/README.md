# Sector0 Bootkit

A modular bootkit for Windows supporting Legacy BIOS and UEFI.

## Quick Start

```bash
# 1. Build payloads (on dev machine)
make payloads

# 2. Copy to target Windows machine
# 3. Run installer as Administrator
python installer.py
```

## Architecture

```
sector0/
├── installer.py    # Entry point
├── config.py       # All configuration
├── Makefile        # Build commands
├── core/
│   ├── utils.py    # Logging, admin checks, command execution
│   ├── disk.py     # DiskManager class - partitions, raw disk access
│   ├── legacy.py   # LegacyBootInstaller - MBR/VBR manipulation
│   └── uefi.py     # UEFIBootInstaller - ESP, BCD configuration
└── payloads/
    ├── build.sh       # Payload build script
    ├── bootloader.asm # Legacy BIOS payload (512 bytes)
    ├── bootloader.bin # Compiled legacy payload
    ├── BOOTX64.c      # UEFI payload source
    └── BOOTX64.efi    # Compiled UEFI payload
```

## Configuration

Edit `config.py`:

```python
UEFI = {
    "binary": "BOOTX64.efi",
    "efi_path": r"\EFI\BOOT",
    "boot_name": "Sector0",
}

BIOS = {
    "binary": "bootloader.bin",
    "dest_name": "bootmgr",
}

INSTALLER = {
    "auto_reboot": True,
    "reboot_delay": 0,
    "create_backup": True,
    "verbose": True,
}
```

## What It Does

### Legacy BIOS Mode
1. Mounts System Reserved partition
2. Backs up original `bootmgr`
3. Writes payload to:
   - `bootmgr` file
   - VBR (Volume Boot Record)
   - MBR (Master Boot Record)

### UEFI Mode
1. Mounts EFI System Partition
2. Copies EFI binary to `\EFI\BOOT\BOOTX64.efi`
3. Creates BCD boot entry
4. Overrides Windows Boot Manager

## Extending

### Add New Payload
1. Create payload source in `payloads/`
2. Update `build.sh`
3. Update config if needed

### Add New Feature
1. Add to appropriate module in `core/`
2. Update installer.py if new flow needed

## Command Line Options

```
--no-reboot     Don't reboot after installation
--verbose       Detailed logging
--uefi-only     Force UEFI mode
--bios-only     Force Legacy BIOS mode
```
