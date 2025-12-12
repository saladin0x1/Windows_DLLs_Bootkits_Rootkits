#!/bin/bash
# Sector0 Payload Build Script
# Compiles bootloader.asm and UEFI payload

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PAYLOADS_DIR="$SCRIPT_DIR"

echo "==================================="
echo "Sector0 Payload Builder"
echo "==================================="

# Build Legacy BIOS bootloader
if command -v nasm &> /dev/null; then
    echo "[+] Building bootloader.bin..."
    nasm -f bin "$PAYLOADS_DIR/bootloader.asm" -o "$PAYLOADS_DIR/bootloader.bin"
    echo "    Output: bootloader.bin ($(wc -c < "$PAYLOADS_DIR/bootloader.bin") bytes)"
else
    echo "[!] NASM not found - skipping Legacy BIOS payload"
    echo "    Install: brew install nasm (macOS) or apt install nasm (Linux)"
fi

# Build UEFI payload (requires cross-compiler)
if [ -f "$PAYLOADS_DIR/BOOTX64.c" ]; then
    if command -v x86_64-w64-mingw32-gcc &> /dev/null; then
        echo "[+] Building BOOTX64.efi..."
        x86_64-w64-mingw32-gcc \
            -ffreestanding \
            -fno-stack-protector \
            -fno-stack-check \
            -fshort-wchar \
            -mno-red-zone \
            -c "$PAYLOADS_DIR/BOOTX64.c" \
            -o "$PAYLOADS_DIR/BOOTX64.o"
        
        x86_64-w64-mingw32-ld \
            -nostdlib \
            -Wl,-dll \
            -shared \
            -Wl,--subsystem,10 \
            -e efi_main \
            "$PAYLOADS_DIR/BOOTX64.o" \
            -o "$PAYLOADS_DIR/BOOTX64.efi"
        
        rm -f "$PAYLOADS_DIR/BOOTX64.o"
        echo "    Output: BOOTX64.efi ($(wc -c < "$PAYLOADS_DIR/BOOTX64.efi") bytes)"
    else
        echo "[!] x86_64-w64-mingw32-gcc not found - skipping UEFI payload"
        echo "    Install: brew install mingw-w64 (macOS) or apt install mingw-w64 (Linux)"
    fi
fi

echo ""
echo "Build complete!"
echo ""
ls -la "$PAYLOADS_DIR"/*.bin "$PAYLOADS_DIR"/*.efi 2>/dev/null || echo "No compiled payloads found"
