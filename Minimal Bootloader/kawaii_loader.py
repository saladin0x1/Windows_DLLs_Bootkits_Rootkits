import ctypes
import sys
import os
import subprocess
import time
import re
import platform
import struct
import hashlib
from tkinter import messagebox, Tk

from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.backends import default_backend
import cryptography.hazmat.primitives.serialization.pkcs12

DIR = os.path.dirname(os.path.abspath(__file__))

BOOT = "bootloader.efi" 
SECURE_IMAGE_NAME = "bootloader_secure.efi" 

EFI_PATH = r"\EFI\BOOT"
BOOT_NAME = "Kawaii Bootloader"
DRV = "S" 
CERT_NAME = "kawaii_uwu"
CERT_FILE = os.path.join(DIR, "kawaii_cert.cer")
TEMP_PS1 = os.path.join(DIR, "temp_cert.ps1")
TEMP_PFX = os.path.join(DIR, "temp_export.pfx")
PFX_PASSWORD = "<your_passkey>" 

HEADER_MAGIC = 0xDEADBEEF
BOOTLOADER_VERSION = 0x0100
PUBLIC_KEY_INDEX = 0x01
DEVICE_ID = 0x12345678
RSA_KEY_SIZE = 2048 
SIGNATURE_SIZE = RSA_KEY_SIZE // 8 

def admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

if platform.system() == "Windows" and not admin():
    root = Tk()
    root.withdraw()
    messagebox.showinfo(
        "Admin Rights Required",
        "This script needs administrator privileges. It will restart as administrator."
    )
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1
    )
    sys.exit()

def run_cmd(cmd, shell=False):
    try:
        if isinstance(cmd, str) and not shell:
            cmd = cmd.split()
            
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            shell=shell,
            encoding='utf-8',
            errors='ignore'
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {' '.join(e.cmd) if isinstance(e.cmd, list) else e.cmd}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")
        raise

def find_signtool():
    return None

def load_private_key_from_pfx(pfx_path, password):
    print(f"Loading private key from PFX: {pfx_path}...")
    with open(pfx_path, "rb") as f:
        pfx_data = f.read()

    private_key, _, _ = serialization.pkcs12.load_key_and_certificates(
        pfx_data,
        password.encode('utf-8'),
        default_backend()
    )
    return private_key

def cert():
    print(f"Generating, installing, and exporting certificate '{CERT_NAME}'...")
    
    script = f"""
$ErrorActionPreference='Stop'

Get-ChildItem -Path Cert:\\CurrentUser\\My | Where-Object {{$_.Subject -like "CN={CERT_NAME}"}} | Remove-Item -Force
if (Test-Path "{TEMP_PFX}") {{ Remove-Item "{TEMP_PFX}" -Force }}

$cert = New-SelfSignedCertificate -DnsName "{CERT_NAME}" -CertStoreLocation "Cert:\\CurrentUser\\My" -KeyExportPolicy Exportable -NotAfter (Get-Date).AddYears(5) -Type CodeSigning -HashAlgorithm SHA256

$p = "{CERT_FILE}"
Export-Certificate -Cert $cert -FilePath $p -Force -Type CERT

if (Test-Path $p) {{
    Import-Certificate -FilePath $p -CertStoreLocation "Cert:\\LocalMachine\\Root"
    Write-Host "Certificate imported successfully to Root store."
}} else {{
    throw "Certificate file not found after export."
}}

$cert | Export-PfxCertificate -FilePath "{TEMP_PFX}" -Password (ConvertTo-SecureString -String "{PFX_PASSWORD}" -Force -AsPlainText)
Write-Host "Private key exported to PFX successfully."
"""
    try:
        with open(TEMP_PS1, "w", encoding="utf-8") as f:
            f.write(script)
            
        run_cmd(f"powershell -ExecutionPolicy Bypass -File \"{TEMP_PS1}\"", shell=True)
        print("Certificate successfully generated, imported, and PFX exported.")
        
    except Exception as e:
        print(f"Certificate management failed: {e}")
        raise
    finally:
        if os.path.exists(TEMP_PS1):
            os.remove(TEMP_PS1)

def custom_sign(private_key):
    bl_src = os.path.join(DIR, BOOT)
    secure_img_path = os.path.join(DIR, SECURE_IMAGE_NAME)
    
    print(f"--- Starting Custom Secure Signing Process for '{BOOT}' ---")

    if not os.path.exists(bl_src):
        raise FileNotFoundError(f"Binary file '{bl_src}' missing in script directory.")

    try:
        with open(bl_src, 'rb') as f:
            raw_binary_data = f.read()
            
        binary_size = len(raw_binary_data)
        print(f"Raw binary size: {binary_size} bytes")

        signature = private_key.sign(
            raw_binary_data,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        print(f"Digital Signature Size: {len(signature)} bytes")

        header_fixed_data = struct.pack(
            '<IIIIII',
            HEADER_MAGIC,
            BOOTLOADER_VERSION,
            PUBLIC_KEY_INDEX,
            DEVICE_ID,
            binary_size,
            0
        )

        secure_header = header_fixed_data + signature
        print(f"Secure Header Size: {len(secure_header)} bytes")
        
        with open(secure_img_path, 'wb') as f:
            f.write(secure_header)
            f.write(raw_binary_data)
        
        print(f"✅ Successfully created secure image: {SECURE_IMAGE_NAME}")
        
    except Exception as e:
        print(f"Binary signing failed: {e}")
        raise

def mount():
    print(f"Searching for EFI System Partition...")
    tmp = 'tmp_list.txt'
    vol = None
    
    try:
        with open(tmp, 'w') as f:
            f.write("list volume\n")
        out = run_cmd(["diskpart", "/s", tmp])
    finally:
        if os.path.exists(tmp): os.remove(tmp)

    for line in out.splitlines():
        if "FAT32" in line and ("System" in line or "Hidden" in line) and "Volume" in line:
            m = re.search(r'Volume\s+(\d+)', line)
            if m:
                vol = m.group(1)
                break
    
    if not vol:
        raise Exception("EFI System Partition (ESP) volume not found (FAT32 and System/Hidden attributes).")
    
    print(f"Found EFI volume: {vol}. Mounting as letter {DRV}:")
    
    tmp_mount = 'tmp_mount.txt'
    content = f"select volume {vol}\nassign letter={DRV}\nexit\n"
    
    try:
        with open(tmp_mount, 'w') as f: f.write(content)
        run_cmd(["diskpart", "/s", tmp_mount])
    finally:
        if os.path.exists(tmp_mount): os.remove(tmp_mount)
        
    time.sleep(2)  
    
    drive_path = f"{DRV}:"
    if not os.path.isdir(drive_path):
           raise Exception(f"Failed to mount EFI partition as {drive_path}. Check if the letter {DRV} is already in use.")

    return drive_path

def umount(d):
    print(f"Unmounting volume {d}...")
    tmp = 'tmp_umount.txt'
    content = f"select volume {d.strip(':')}\nremove\nexit\n"  
    try:
        out = run_cmd(f"diskpart /s list_vol.txt")
        vol = None
        for line in out.splitlines():
            if d.strip(':') in line:
                m = re.search(r'Volume\s+(\d+)', line)
                if m:
                    vol = m.group(1)
                    break
            
        if vol:
            content = f"select volume {vol}\nremove letter={d.strip(':')}\nexit\n"
            with open(tmp, 'w') as f: f.write(content)
            run_cmd(["diskpart", "/s", tmp])
            print(f"Volume {d} unmounted successfully.")
        else:
            print(f"Could not find volume number for drive {d} to unmount.")
            
    except Exception as e:
        print(f"Warning: Failed to unmount drive {d}. Manual removal might be necessary. Error: {e}")
    finally:
        if os.path.exists(tmp): os.remove(tmp)

def boot(private_key):
    print("\n--- Starting Bootloader Installation ---")
    
    custom_sign(private_key)
    
    bl_src = os.path.join(DIR, SECURE_IMAGE_NAME)
    
    d = None
    try:
        d = mount()
        
        base_dir = os.path.join(d, EFI_PATH.strip('\\'))
        dest_path = os.path.join(base_dir, BOOT) 
        
        print(f"Copying '{SECURE_IMAGE_NAME}' to '{dest_path}'...")
        os.makedirs(base_dir, exist_ok=True)
        run_cmd(f"copy /Y \"{bl_src}\" \"{dest_path}\"", shell=True)
        
        if not os.path.exists(dest_path) or os.path.getsize(dest_path) == 0:
            raise Exception(f"Copy failed. Destination file '{dest_path}' not found or is empty.")
        print("Bootloader copied successfully.")
        
        bcd_path = os.path.join(EFI_PATH, BOOT).replace("/", "\\")
        
        print(f"Creating new BCD entry: '{BOOT_NAME}'...")
        out = run_cmd(["bcdedit", "/create", "/d", BOOT_NAME, "/application", "bootmgr"])
        
        m = re.search(r'\{[0-9a-fA-F-]{36}\}', out)
        if not m: raise Exception("Failed to extract GUID from 'bcdedit /create' output.")
        g = m.group(0)
        print(f"New BCD Entry GUID: {g}")
        
        run_cmd(["bcdedit", "/set", g, "device", f"partition={d}"])
        run_cmd(["bcdedit", "/set", g, "path", bcd_path])
        run_cmd(["bcdedit", "/displayorder", g, "/addfirst"])
        
        print("BCD entry created and set as first in display order.")
        messagebox.showinfo("Success", f"Bootloader '{BOOT_NAME}' installed successfully! REMEMBER TO ENROLL '{CERT_FILE}'!")

    except Exception as e:
        print(f"\n--- Installation Failed ---")
        messagebox.showerror("Error", f"Installation failed: {e}")
        raise
    finally:
        if d: umount(d)

def main():
    if platform.system() != "Windows":
        raise OSError(f"This script is designed for Windows, not {platform.system()}.")

    binary_path = os.path.join(DIR, BOOT)
    if not os.path.exists(binary_path):
        print(f"Creating dummy input binary: {binary_path} (10 KB)")
        with open(binary_path, 'wb') as f:
            f.write(os.urandom(10240))
    
    private_key = None
    
    try:
        cert()
        
        private_key = load_private_key_from_pfx(TEMP_PFX, PFX_PASSWORD)
        
        boot(private_key)
        
        print("\n--- Self-Destruct Sequence Initiated ---")
        exe = sys.executable
        bat = os.path.join(DIR, "delete_me.bat")
        
        target = os.path.abspath(__file__) 
        
        with open(bat, 'w') as f:
            f.write('@echo off\n')
            f.write(f'ping 127.0.0.1 -n 5 >nul\n')
            f.write(f'del "{target}" /f /q\n')
            f.write(f'del "{os.path.join(DIR, SECURE_IMAGE_NAME)}" /f /q\n') 
            f.write(f'if exist "{os.path.join(DIR, BOOT)}" del "{os.path.join(DIR, BOOT)}" /f /q\n')
            f.write(f'del "%~f0" /f /q\n')
            
        subprocess.Popen([bat], shell=True, creationflags=subprocess.DETACHED_PROCESS)
        print(f"Script finished. **IMPORTANT:** Retained '{CERT_FILE}' for manual UEFI key enrollment.")
        sys.exit(0)

    except Exception as e:
        print(f"FATAL ERROR: {e}")
        if 'root' not in locals() and 'root' not in globals():
            try:
                root = Tk()
                root.withdraw()
                messagebox.showerror("Fatal Error", f"A critical error occurred: {e}")
            except:
                pass
        sys.exit(1)
        
    finally:
        if os.path.exists(TEMP_PFX):
            os.remove(TEMP_PFX)
            print(f"Cleaned up sensitive temporary PFX file: {TEMP_PFX}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL ERROR in main execution: {e}")
        sys.exit(1)
