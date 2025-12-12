# Windows Bootkits & Rootkits

A collection of low-level Windows security research tools.

## Structure

```
├── bootkits/
│   └── sector0/          # MBR/VBR bootkit with UEFI support
│       ├── installer.py      # Main installer
│       ├── config.py         # Configuration
│       ├── core/             # Modular components
│       │   ├── utils.py      # Logging, admin, commands
│       │   ├── disk.py       # Disk operations, raw access
│       │   ├── legacy.py     # Legacy BIOS installer
│       │   └── uefi.py       # UEFI installer
│       └── payloads/         # Boot payloads
│           ├── bootloader.asm  # Legacy 16-bit bootloader
│           └── BOOTX64.c       # UEFI application
│
├── rootkits/
│   ├── process_hider/       # NtQuerySystemInformation IAT hook
│   └── watchdog/            # Process termination watchdog
│
└── firmware/
    └── seabios/             # Custom BIOS builds
```

## Bootkits

### Sector0
MBR/VBR bootkit supporting both Legacy BIOS and UEFI systems.

**Features:**
- Automatic boot mode detection
- Direct MBR/VBR sector writes
- BCD manipulation for UEFI
- Modular, maintainable codebase

**Usage:**
```bash
cd bootkits/sector0

# Build payloads
make payloads

# Run installer (on target Windows machine)
python installer.py

# Options
python installer.py --no-reboot
python installer.py --bios-only
python installer.py --uefi-only
```

## Rootkits

### Process Hider
IAT hook that hides processes from Task Manager.

### Watchdog
Auto-terminates specified processes.

**Building:**
```bash
# Visual Studio
cl /LD /EHsc dllmain.cpp /link /OUT:output.dll

# MinGW
x86_64-w64-mingw32-g++ -shared -o output.dll dllmain.cpp
```

## Requirements

**Development (macOS/Linux):**
- NASM (bootloader assembly)
- mingw-w64 (UEFI cross-compile)
- Python 3.8+

**Target (Windows):**
- Windows 10/11
- Administrator privileges
- Secure Boot disabled (for UEFI)

## Disclaimer

For educational and authorized security research only.
These tools can cause permanent system damage.
Only use on systems you own or have explicit permission to test.

## License

MIT
