/**
 * Process Watchdog - Auto-Terminator
 * ===================================
 * Monitors for and terminates specified processes.
 * 
 * How it works:
 *   Runs a background thread that polls for target process.
 *   When found, terminates it immediately.
 * 
 * Usage:
 *   1. Compile as DLL
 *   2. Inject into long-running process or use as persistence
 *   3. Target process will be killed whenever it starts
 * 
 * Configuration:
 *   Change TARGET_PROCESS to kill different process
 */

#include <windows.h>
#include <tlhelp32.h>
#include <string>

// ============================================================
// CONFIGURATION
// ============================================================
static const wchar_t* TARGET_PROCESS = L"Notepad.exe";
static const DWORD POLL_INTERVAL_MS = 1000;
static const bool SHOW_ERRORS = false;  // Set to true for debugging


// ============================================================
// Process Utilities
// ============================================================

void ShowError(const wchar_t* message) {
    if (SHOW_ERRORS) {
        MessageBoxW(NULL, message, L"Watchdog Error", MB_OK | MB_ICONERROR);
    }
}

BOOL IsProcessRunning(const wchar_t* processName) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) {
        return FALSE;
    }

    PROCESSENTRY32W entry = { sizeof(PROCESSENTRY32W) };
    BOOL found = FALSE;

    if (Process32FirstW(snapshot, &entry)) {
        do {
            if (_wcsicmp(entry.szExeFile, processName) == 0) {
                found = TRUE;
                break;
            }
        } while (Process32NextW(snapshot, &entry));
    }

    CloseHandle(snapshot);
    return found;
}

DWORD GetProcessId(const wchar_t* processName) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) {
        return 0;
    }

    PROCESSENTRY32W entry = { sizeof(PROCESSENTRY32W) };
    DWORD pid = 0;

    if (Process32FirstW(snapshot, &entry)) {
        do {
            if (_wcsicmp(entry.szExeFile, processName) == 0) {
                pid = entry.th32ProcessID;
                break;
            }
        } while (Process32NextW(snapshot, &entry));
    }

    CloseHandle(snapshot);
    return pid;
}

BOOL TerminateProcessByName(const wchar_t* processName) {
    HANDLE snapshot = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snapshot == INVALID_HANDLE_VALUE) {
        return FALSE;
    }

    PROCESSENTRY32W entry = { sizeof(PROCESSENTRY32W) };
    BOOL terminated = FALSE;

    if (Process32FirstW(snapshot, &entry)) {
        do {
            if (_wcsicmp(entry.szExeFile, processName) == 0) {
                HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, entry.th32ProcessID);
                if (hProcess != NULL) {
                    if (TerminateProcess(hProcess, 0)) {
                        terminated = TRUE;
                    } else {
                        ShowError(L"Failed to terminate process - access denied");
                    }
                    CloseHandle(hProcess);
                } else {
                    ShowError(L"Failed to open process - access denied");
                }
            }
        } while (Process32NextW(snapshot, &entry));
    }

    CloseHandle(snapshot);
    return terminated;
}


// ============================================================
// Watchdog Thread
// ============================================================

DWORD WINAPI WatchdogThread(LPVOID lpParam) {
    while (TRUE) {
        if (IsProcessRunning(TARGET_PROCESS)) {
            TerminateProcessByName(TARGET_PROCESS);
        }
        Sleep(POLL_INTERVAL_MS);
    }
    return 0;
}


// ============================================================
// DLL Entry Point
// ============================================================

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    switch (reason) {
        case DLL_PROCESS_ATTACH:
            DisableThreadLibraryCalls(hModule);
            // Use thread pool for efficiency
            QueueUserWorkItem(WatchdogThread, NULL, WT_EXECUTEDEFAULT);
            break;
        case DLL_PROCESS_DETACH:
            break;
    }
    return TRUE;
}
