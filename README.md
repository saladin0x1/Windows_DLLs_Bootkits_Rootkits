# Sector0

MBR/VBR bootkit targeting Windows Legacy BIOS systems.

> **For educational and authorized security research only.**

## Overview

Sector0 is a modular bootkit that hijacks the Master Boot Record to execute arbitrary code before the operating system loads. Useful for understanding boot-level persistence, disk structures, and real-mode x86 assembly.

## Usage

```bash
# Windows VM (Administrator required)
python installer.py
```

The system reboots and the payload executes at the BIOS level.

## Project Structure

```
├── installer.py          # Entry point
├── config.py             # Settings
├── core/
│   ├── disk.py           # Raw disk I/O, sector read/write
│   ├── legacy.py         # MBR/VBR installation
│   ├── uefi.py           # UEFI support (not tested yet)
│   └── utils.py          # Helpers
├── payloads/
│   ├── bootloader.asm    # 16-bit real mode payload
│   └── bootloader.bin    # Compiled binary (512 bytes)
├── docs/
│   ├── ATTACK_FLOW.md    # Technical breakdown of attack chain
│   └── BOOTLOADER_EXPLAINED.md  # Assembly walkthrough
└── firmware_sources/     # Custom SeaBIOS builds
```

## Requirements

- Windows 10/11 VM
- Legacy BIOS mode (not UEFI Secure Boot)
- MBR partition table
- Python 3.x
- Administrator privileges

## Build

```bash
nasm -f bin payloads/bootloader.asm -o payloads/bootloader.bin
```

## Test (QEMU)

```bash
dd if=/dev/zero of=disk.img bs=512 count=2048
dd if=payloads/bootloader.bin of=disk.img conv=notrunc
qemu-system-i386 -hda disk.img
```

## Documentation

- [Attack Flow](docs/ATTACK_FLOW.md) - Full infection chain
- [Bootloader Internals](docs/BOOTLOADER_EXPLAINED.md) - Assembly breakdown

## Credits

Based on [liuzhaicutey/Windows_DLLs_Bootkits_Rootkits](https://github.com/liuzhaicutey/Windows_DLLs_Bootkits_Rootkits). Refactored for clarity and maintainability.

## License

MIT
