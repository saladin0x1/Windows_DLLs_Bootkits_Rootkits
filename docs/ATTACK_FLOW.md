# Sector0 Bootkit - Complete Legacy BIOS Attack Flow

A step-by-step breakdown of the entire bootkit attack chain from infection to destruction.

---

## Table of Contents

1. [Stage 1: Infection](#stage-1-infection-windows-running)
2. [Stage 2: BIOS Boot Sequence](#stage-2-bios-boot-sequence)
3. [Stage 3: Bootloader Execution](#stage-3-bootloader-execution)
4. [Stage 4: Disk State After Attack](#stage-4-disk-state-after-attack)
5. [Stage 5: Result on Next Boot](#stage-5-result-on-next-boot)
6. [Code Flow Summary](#code-flow-summary)
7. [Key Points](#key-points)

---

## Stage 1: Infection (Windows Running)

```
┌─────────────────────────────────────────────────────────────────┐
│                     WINDOWS IS RUNNING                          │
│                   (64-bit Protected Mode)                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  User runs: python installer.py                                 │
│                                                                 │
│  1. Check admin privileges (required for raw disk access)      │
│  2. Read bootloader.bin (512 bytes)                            │
│  3. Open \\.\PhysicalDrive0 via kernel32.CreateFileW()         │
│  4. Write bootloader.bin to Sector 0 (MBR)                     │
│  5. Reboot system                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     ┌───────────────┐
                     │    REBOOT     │
                     └───────────────┘
```

### What `installer.py` does:

```python
# Opens raw disk for writing
handle = kernel32.CreateFileW(
    "\\\\.\\PhysicalDrive0",    # Raw disk access
    GENERIC_WRITE,
    FILE_SHARE_READ | FILE_SHARE_WRITE,
    None,
    OPEN_EXISTING,
    0, None
)

# Writes bootloader to sector 0
kernel32.WriteFile(handle, bootloader_bin, 512, ...)
```

---

## Stage 2: BIOS Boot Sequence

```
┌─────────────────────────────────────────────────────────────────┐
│                      POWER ON / REBOOT                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BIOS                                    │
│                                                                 │
│  1. POST (Power-On Self Test)                                  │
│  2. Initialize hardware                                         │
│  3. Read Sector 0 from first HDD (512 bytes)                   │
│  4. Check bytes 510-511 for 0xAA55 signature                   │
│  5. Load sector to memory address 0x7C00                       │
│  6. Jump to 0x7C00 (start executing our code!)                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │  CPU now in 16-bit Real Mode  │
              │  Executing our bootloader.asm │
              │  at address 0x7C00            │
              └───────────────────────────────┘
```

### Key Points:

- BIOS runs in **16-bit Real Mode**
- No memory protection
- No OS running yet
- Full hardware access via BIOS interrupts

---

## Stage 3: Bootloader Execution

```
┌─────────────────────────────────────────────────────────────────┐
│                   BOOTLOADER RUNNING                            │
│                  (16-bit Real Mode)                             │
│                  (Full hardware access)                         │
│                  (No OS protection!)                            │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   PHASE 1     │   │   PHASE 2     │   │   PHASE 3     │
│               │   │               │   │               │
│ Setup CPU     │   │ Print Message │   │ Wipe Payload  │
│ registers     │   │ via BIOS      │   │               │
│ DS=ES=0       │   │ INT 0x10      │   │               │
│ SP=0x7C00     │   │               │   │               │
└───────────────┘   └───────────────┘   └───────┬───────┘
                                                │
                    ┌───────────────────────────┼───────────────────────────┐
                    ▼                           ▼                           ▼
          ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
          │  WIPE STEP A    │         │  WIPE STEP B    │         │  WIPE STEP C    │
          │                 │         │                 │         │                 │
          │ Corrupt MBR     │         │ Overwrite       │         │ Corrupt VBR     │
          │ Partition Table │         │ Sectors 1-255   │         │ OEM Name        │
          │                 │         │                 │         │                 │
          │ Zero out bytes  │         │ Fill with       │         │ Zero out NTFS   │
          │ 0x1BE-0x1FD     │         │ "SECTOR0!!"     │         │ identifier      │
          └─────────────────┘         └─────────────────┘         └─────────────────┘
```

### Phase Details:

#### Phase 1: CPU Setup
```asm
_start:
    cli                 ; Disable interrupts
    xor ax, ax
    mov ds, ax          ; DS = 0
    mov es, ax          ; ES = 0
    mov ss, ax          ; SS = 0
    mov sp, 0x7C00      ; Stack below our code
    sti                 ; Re-enable interrupts
```

#### Phase 2: Print Message
```asm
    mov si, msg_goodbye
    call print_string   ; Uses INT 0x10, AH=0x0E
```

Output: `SECTOR0: Disk wipe complete.`

#### Phase 3: Wipe Payload

| Step | Action | BIOS Call | Effect |
|------|--------|-----------|--------|
| A | Zero partition table | INT 0x13, AH=03 | Windows can't find partitions |
| B | Overwrite sectors 1-255 | INT 0x13, AH=03 | Boot files destroyed |
| C | Corrupt VBR OEM name | INT 0x13, AH=03 | NTFS unrecognizable |

---

## Stage 4: Disk State After Attack

### Before (Normal Windows MBR disk):

```
┌────────────────────────────────────────────────────────────────────────┐
│ Sector 0 (MBR)                                                         │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Boot Code (Windows)           │ Partition Table │ 0xAA55           │ │
│ │ 446 bytes                     │ 64 bytes        │ 2 bytes          │ │
│ └────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────┤
│ Sector 1-62: Reserved / Bootloader continuation                       │
├────────────────────────────────────────────────────────────────────────┤
│ Sector 63+: NTFS Partition (Windows C:)                               │
│   - VBR (Volume Boot Record)                                           │
│   - $MFT (Master File Table)                                           │
│   - Windows files...                                                   │
└────────────────────────────────────────────────────────────────────────┘
```

### After (Destroyed):

```
┌────────────────────────────────────────────────────────────────────────┐
│ Sector 0 (MBR) - CORRUPTED                                            │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │ Our Bootloader               │ 0x00000000...   │ 0xAA55            │ │
│ │ (still here)                 │ ZEROED!         │                   │ │
│ └────────────────────────────────────────────────────────────────────┘ │
├────────────────────────────────────────────────────────────────────────┤
│ Sectors 1-255: SECTOR0!!SECTOR0!!SECTOR0!!SECTOR0!!SECTOR0!!...       │
│                DESTROYED - All bootloader data gone                    │
├────────────────────────────────────────────────────────────────────────┤
│ Sector 256+: May still have some data but UNREACHABLE                 │
│   - No partition table pointing to it                                  │
│   - VBR corrupted                                                      │
│   - $MFT likely damaged                                                │
└────────────────────────────────────────────────────────────────────────┘
```

### Partition Table Layout:

| Offset | Size | Content | After Attack |
|--------|------|---------|--------------|
| 0x000 | 446 bytes | Boot code | Our bootloader |
| 0x1BE | 16 bytes | Partition 1 | `0x00...` (zeroed) |
| 0x1CE | 16 bytes | Partition 2 | `0x00...` (zeroed) |
| 0x1DE | 16 bytes | Partition 3 | `0x00...` (zeroed) |
| 0x1EE | 16 bytes | Partition 4 | `0x00...` (zeroed) |
| 0x1FE | 2 bytes | Signature | `0xAA55` (preserved) |

---

## Stage 5: Result on Next Boot

```
┌─────────────────────────────────────────────────────────────────┐
│                      NEXT REBOOT                                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         BIOS                                    │
│                                                                 │
│  1. Load Sector 0 (our bootloader again)                       │
│  2. Execute → wipes again (no-op, already destroyed)           │
│  3. Halts in infinite loop                                     │
│                                                                 │
│  OR if bootloader was also overwritten:                        │
│                                                                 │
│  1. Load Sector 0                                              │
│  2. No valid boot code                                         │
│  3. "Operating System Not Found" / "No bootable device"        │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │         💀 DEAD 💀            │
              │                               │
              │  - Windows won't boot         │
              │  - Recovery won't work        │
              │  - Data unrecoverable         │
              │  - Reinstall required         │
              └───────────────────────────────┘
```

---

## Code Flow Summary

```
installer.py (Python, Windows userland)
    │
    ├── Opens \\.\PhysicalDrive0
    ├── Writes bootloader.bin to sector 0
    └── Reboots
            │
            ▼
bootloader.asm (Assembly, 16-bit Real Mode)
    │
    ├── _start:           Setup DS=0, ES=0, SP=0x7C00
    ├── print_string:     "SECTOR0: Disk wipe complete."
    ├── wipe_payload:
    │   ├── read_mbr      INT 0x13, AH=02 (read sector 1)
    │   ├── Zero partition table (offset 0x1BE, 64 bytes)
    │   ├── write_mbr     INT 0x13, AH=03 (write sector 1)
    │   ├── Loop 255x:
    │   │   ├── fill_wipe_pattern ("SECTOR0!!")
    │   │   └── Write sector N
    │   ├── read_vbr      (sector 2)
    │   ├── corrupt_vbr   (zero OEM name)
    │   └── write_vbr
    └── jmp $             Infinite loop (halt)
```

---

## Key Points

| Stage | Mode | Privilege | What Happens |
|-------|------|-----------|--------------|
| Infection | 64-bit Protected | Admin (Ring 3) | Python writes 512 bytes to disk |
| Boot | 16-bit Real | Ring 0 equivalent | BIOS loads and jumps to 0x7C00 |
| Wipe | 16-bit Real | Full hardware | Direct disk I/O via BIOS INT 0x13 |
| After | N/A | N/A | System bricked |

---

## BIOS Interrupts Used

| Interrupt | Function | Purpose |
|-----------|----------|---------|
| `INT 0x10, AH=0x0E` | Teletype Output | Print characters to screen |
| `INT 0x13, AH=0x02` | Read Sectors | Read disk sectors to memory |
| `INT 0x13, AH=0x03` | Write Sectors | Write memory to disk sectors |

---

## Why This Works

1. **No Secure Boot** - Legacy BIOS doesn't verify code signatures
2. **No TPM checks** - No measured boot in Legacy mode
3. **Raw disk access** - Windows allows admin to write to PhysicalDrive0
4. **Real Mode freedom** - 16-bit code has full hardware access
5. **BIOS trust** - BIOS executes any code with valid 0xAA55 signature

---

## Defense Mechanisms (Not Present in Legacy BIOS)

| Protection | Legacy BIOS | UEFI + Secure Boot |
|------------|-------------|-------------------|
| Code signing | ❌ None | ✅ Required |
| TPM measurement | ❌ None | ✅ PCR values |
| Write protection | ❌ None | ✅ Possible |
| Boot verification | ❌ 0xAA55 only | ✅ Certificate chain |

---

*Author: saladin0x1*  
*Based on: https://github.com/liuzhaicutey/Windows_DLLs_Bootkits_Rootkits*
