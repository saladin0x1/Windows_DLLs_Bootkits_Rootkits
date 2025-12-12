# Process Hider - NtQuerySystemInformation Hook

## Overview
IAT hook that hides processes from Task Manager, Process Explorer, and any application using `NtQuerySystemInformation` to enumerate processes.

## How It Works
1. DLL is injected into target process (e.g., `taskmgr.exe`)
2. Hooks `NtQuerySystemInformation` via Import Address Table
3. Filters `SystemProcessInformation` queries to remove specified process from results

## Configuration
Edit `HIDDEN_PROCESS` in `dllmain.cpp`:
```cpp
static const std::string HIDDEN_PROCESS = "malware.exe";
```

## Building
```bash
# Visual Studio Developer Command Prompt
cl /LD /EHsc dllmain.cpp /link /OUT:process_hider.dll psapi.lib

# Or use CMake
mkdir build && cd build
cmake ..
cmake --build .
```

## Usage
Inject the compiled DLL into Task Manager or other monitoring tools:
```cpp
// Example using CreateRemoteThread
HANDLE hProcess = OpenProcess(PROCESS_ALL_ACCESS, FALSE, targetPid);
// ... standard DLL injection code
```

## Detection Vectors
- IAT modifications visible to memory scanners
- Hook detection via function pointer comparison
- Inline hook detection on original function

## Limitations
- Only hides from processes where DLL is injected
- Doesn't hide from kernel-mode tools
- Process still visible via direct syscalls
