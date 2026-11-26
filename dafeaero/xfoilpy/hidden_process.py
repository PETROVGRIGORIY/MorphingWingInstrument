"""Запуск программы на невидимом рабочем столе Windows: её окна не видны
пользователю и не перехватывают фокус ввода."""
import ctypes
import msvcrt
import os
import subprocess
import uuid
from ctypes import wintypes
from pathlib import Path

_k32 = ctypes.WinDLL("kernel32", use_last_error=True)
_u32 = ctypes.WinDLL("user32", use_last_error=True)

_GENERIC_ALL = 0x10000000
_STARTF_USESTDHANDLES = 0x00000100
_CREATE_NO_WINDOW = 0x08000000
_WAIT_TIMEOUT = 0x00000102


class _STARTUPINFOW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD), ("lpReserved", wintypes.LPWSTR),
        ("lpDesktop", wintypes.LPWSTR), ("lpTitle", wintypes.LPWSTR),
        ("dwX", wintypes.DWORD), ("dwY", wintypes.DWORD),
        ("dwXSize", wintypes.DWORD), ("dwYSize", wintypes.DWORD),
        ("dwXCountChars", wintypes.DWORD), ("dwYCountChars", wintypes.DWORD),
        ("dwFillAttribute", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
        ("wShowWindow", wintypes.WORD), ("cbReserved2", wintypes.WORD),
        ("lpReserved2", ctypes.POINTER(ctypes.c_byte)),
        ("hStdInput", wintypes.HANDLE), ("hStdOutput", wintypes.HANDLE),
        ("hStdError", wintypes.HANDLE),
    ]


class _PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("hProcess", wintypes.HANDLE), ("hThread", wintypes.HANDLE),
        ("dwProcessId", wintypes.DWORD), ("dwThreadId", wintypes.DWORD),
    ]


# Явные типы обязательны: без них дескрипторы обрезаются до 32 бит в 64-битном Python
_u32.CreateDesktopW.restype = wintypes.HANDLE
_u32.CreateDesktopW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPVOID,
                                wintypes.DWORD, wintypes.DWORD, wintypes.LPVOID]
_u32.CloseDesktop.argtypes = [wintypes.HANDLE]
_k32.CreateProcessW.argtypes = [
    wintypes.LPCWSTR, wintypes.LPWSTR, wintypes.LPVOID, wintypes.LPVOID, wintypes.BOOL,
    wintypes.DWORD, wintypes.LPVOID, wintypes.LPCWSTR,
    ctypes.POINTER(_STARTUPINFOW), ctypes.POINTER(_PROCESS_INFORMATION),
]
_k32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
_k32.GetExitCodeProcess.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
_k32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
_k32.CloseHandle.argtypes = [wintypes.HANDLE]


def run_hidden(exe: str | Path, stdin_path: str | Path, cwd: str | Path, timeout: float) -> int:
    """Запускает exe на скрытом рабочем столе, подавая stdin_path на вход.
    Возвращает код завершения; по таймауту убивает процесс и бросает TimeoutExpired."""
    desktop = f"dafeaero_{uuid.uuid4().hex}"
    hdesk = _u32.CreateDesktopW(desktop, None, None, 0, _GENERIC_ALL, None)
    if not hdesk:
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        with open(stdin_path, "rb") as f_in, open(os.devnull, "wb") as f_out:
            h_in = msvcrt.get_osfhandle(f_in.fileno())
            h_out = msvcrt.get_osfhandle(f_out.fileno())
            os.set_handle_inheritable(h_in, True)
            os.set_handle_inheritable(h_out, True)

            si = _STARTUPINFOW()
            si.cb = ctypes.sizeof(si)
            si.lpDesktop = desktop
            si.dwFlags = _STARTF_USESTDHANDLES
            si.hStdInput, si.hStdOutput, si.hStdError = h_in, h_out, h_out
            pi = _PROCESS_INFORMATION()

            ok = _k32.CreateProcessW(
                None, ctypes.create_unicode_buffer(f'"{exe}"'), None, None, True,
                _CREATE_NO_WINDOW, None, str(cwd), ctypes.byref(si), ctypes.byref(pi),
            )
            if not ok:
                raise ctypes.WinError(ctypes.get_last_error())
            try:
                if _k32.WaitForSingleObject(pi.hProcess, int(timeout * 1000)) == _WAIT_TIMEOUT:
                    _k32.TerminateProcess(pi.hProcess, 1)
                    _k32.WaitForSingleObject(pi.hProcess, 5000)
                    raise subprocess.TimeoutExpired(str(exe), timeout)
                code = wintypes.DWORD()
                _k32.GetExitCodeProcess(pi.hProcess, ctypes.byref(code))
                return code.value
            finally:
                _k32.CloseHandle(pi.hProcess)
                _k32.CloseHandle(pi.hThread)
    finally:
        _u32.CloseDesktop(hdesk)
