"""Custodia local: DPAPI CurrentUser, DACL privada y bloqueo de mantenimiento."""
import base64
from contextlib import contextmanager
import ctypes
from ctypes import wintypes as w
import os
from pathlib import Path
import threading
import time

PREFIX=b'ST-DPAPI-1\n'
_lock=threading.RLock()
_path_locks={}

class Blob(ctypes.Structure):
    _fields_=[('cbData',w.DWORD),('pbData',ctypes.POINTER(ctypes.c_ubyte))]

def _dpapi(data,decrypt=False):
    if os.name!='nt': raise RuntimeError('La custodia de claves requiere Windows.')
    crypt=ctypes.WinDLL('crypt32',use_last_error=True)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.LocalFree.argtypes=[w.HLOCAL];kernel.LocalFree.restype=w.HLOCAL
    raw=(ctypes.c_ubyte*len(data)).from_buffer_copy(data)
    source=Blob(len(data),raw);output=Blob()
    fn=crypt.CryptUnprotectData if decrypt else crypt.CryptProtectData
    fn.argtypes=[ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.POINTER(Blob),ctypes.c_void_p,ctypes.c_void_p,w.DWORD,ctypes.POINTER(Blob)]
    fn.restype=w.BOOL
    # No LOCAL_MACHINE: la protección se asocia al usuario actual.
    if not fn(ctypes.byref(source),None,None,None,None,1,ctypes.byref(output)):
        raise OSError(ctypes.get_last_error(),'Windows no pudo proteger o abrir la clave. Usa el mismo usuario de Windows.')
    try:return ctypes.string_at(output.pbData,output.cbData)
    finally:kernel.LocalFree(output.pbData)

def protect(data): return PREFIX+base64.b64encode(_dpapi(data))
def unprotect(data):
    if not data.startswith(PREFIX):raise ValueError('Formato de clave protegida inválido.')
    return _dpapi(base64.b64decode(data[len(PREFIX):],validate=True),True)

def user_sid():
    adv=ctypes.WinDLL('advapi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=w.HANDLE
    kernel.CloseHandle.argtypes=[w.HANDLE]
    kernel.LocalFree.argtypes=[w.HLOCAL];kernel.LocalFree.restype=w.HLOCAL
    adv.OpenProcessToken.argtypes=[w.HANDLE,w.DWORD,ctypes.POINTER(w.HANDLE)]
    adv.GetTokenInformation.argtypes=[w.HANDLE,ctypes.c_int,ctypes.c_void_p,w.DWORD,ctypes.POINTER(w.DWORD)]
    adv.ConvertSidToStringSidW.argtypes=[ctypes.c_void_p,ctypes.POINTER(w.LPWSTR)]
    token=w.HANDLE()
    if not adv.OpenProcessToken(kernel.GetCurrentProcess(),8,ctypes.byref(token)):raise ctypes.WinError(ctypes.get_last_error())
    try:
        size=w.DWORD();adv.GetTokenInformation(token,1,None,0,ctypes.byref(size))
        data=ctypes.create_string_buffer(size.value)
        if not adv.GetTokenInformation(token,1,data,size,ctypes.byref(size)):raise ctypes.WinError(ctypes.get_last_error())
        sid=ctypes.cast(data,ctypes.POINTER(ctypes.c_void_p))[0];text=w.LPWSTR()
        if not adv.ConvertSidToStringSidW(sid,ctypes.byref(text)):raise ctypes.WinError(ctypes.get_last_error())
        try:return text.value
        finally:kernel.LocalFree(ctypes.cast(text,w.HLOCAL))
    finally:kernel.CloseHandle(token)

def private_directory(directory):
    """Solo usuario actual y SYSTEM. Rechaza enlaces antes de cambiar permisos."""
    root=Path(directory)
    root.mkdir(parents=True,exist_ok=True)
    paths=[root,*root.rglob('*')]
    if any(p.is_symlink() or (hasattr(p,'is_junction') and p.is_junction()) for p in paths):
        raise RuntimeError('No se permiten enlaces dentro del almacén privado.')
    if os.name!='nt':
        if os.environ.get('ST_TEST_MODE')!='1':raise RuntimeError('Se requiere Windows.')
        for p in paths:p.chmod(0o700 if p.is_dir() else 0o600)
        return
    adv=ctypes.WinDLL('advapi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    adv.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes=[w.LPCWSTR,w.DWORD,ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(w.DWORD)]
    adv.GetSecurityDescriptorDacl.argtypes=[ctypes.c_void_p,ctypes.POINTER(w.BOOL),ctypes.POINTER(ctypes.c_void_p),ctypes.POINTER(w.BOOL)]
    adv.SetNamedSecurityInfoW.argtypes=[w.LPWSTR,ctypes.c_int,w.DWORD,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p]
    adv.SetNamedSecurityInfoW.restype=w.DWORD
    kernel.LocalFree.argtypes=[w.HLOCAL];kernel.LocalFree.restype=w.HLOCAL
    sd=ctypes.c_void_p();sddl=f'D:P(A;OICI;FA;;;SY)(A;OICI;FA;;;{user_sid()})'
    if not adv.ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl,1,ctypes.byref(sd),None):raise ctypes.WinError(ctypes.get_last_error())
    try:
        present=w.BOOL();defaulted=w.BOOL();acl=ctypes.c_void_p()
        if not adv.GetSecurityDescriptorDacl(sd,ctypes.byref(present),ctypes.byref(acl),ctypes.byref(defaulted)):raise ctypes.WinError(ctypes.get_last_error())
        for p in paths:
            status=adv.SetNamedSecurityInfoW(str(p.resolve()),1,0x80000004,None,None,acl,None)
            if status:raise OSError(status,'No fue posible restringir el almacén privado.')
    finally:kernel.LocalFree(sd)

def directory_acl(directory):
    """Lectura de la DACL real para diagnósticos, sin depender de PowerShell."""
    adv=ctypes.WinDLL('advapi32',use_last_error=True);kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    adv.GetNamedSecurityInfoW.argtypes=[w.LPWSTR,ctypes.c_int,w.DWORD,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_void_p)]
    adv.GetNamedSecurityInfoW.restype=w.DWORD
    adv.GetSecurityDescriptorControl.argtypes=[ctypes.c_void_p,ctypes.POINTER(w.WORD),ctypes.POINTER(w.DWORD)]
    adv.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes=[ctypes.c_void_p,w.DWORD,w.DWORD,ctypes.POINTER(w.LPWSTR),ctypes.c_void_p]
    kernel.LocalFree.argtypes=[w.HLOCAL];kernel.LocalFree.restype=w.HLOCAL
    sd=ctypes.c_void_p();status=adv.GetNamedSecurityInfoW(str(Path(directory).resolve()),1,4,None,None,None,None,ctypes.byref(sd))
    if status:raise OSError(status,'No fue posible leer la DACL.')
    try:
        control=w.WORD();revision=w.DWORD();text=w.LPWSTR()
        if not adv.GetSecurityDescriptorControl(sd,ctypes.byref(control),ctypes.byref(revision)):raise ctypes.WinError(ctypes.get_last_error())
        if not adv.ConvertSecurityDescriptorToStringSecurityDescriptorW(sd,1,4,ctypes.byref(text),None):raise ctypes.WinError(ctypes.get_last_error())
        try:return {'protected':bool(control.value&0x1000),'sddl':text.value}
        finally:kernel.LocalFree(ctypes.cast(text,w.HLOCAL))
    finally:kernel.LocalFree(sd)

@contextmanager
def file_lock(path,wait=False):
    """Bloqueo liberado por Windows incluso si termina el proceso."""
    import msvcrt
    with _lock:
        mutex=_path_locks.setdefault(str(Path(path).resolve()),threading.RLock())
    with mutex:
        with Path(path).open('a+b') as stream:
            if stream.seek(0,2)==0:stream.write(b'0');stream.flush()
            deadline=time.monotonic()+(10 if wait else 0)
            while True:
                stream.seek(0)
                try:msvcrt.locking(stream.fileno(),msvcrt.LK_NBLCK,1);break
                except OSError:
                    if time.monotonic()>=deadline:raise RuntimeError('La aplicación está en uso. Detén el servidor antes del mantenimiento.') from None
                    time.sleep(.05)
            try:yield
            finally:stream.seek(0);msvcrt.locking(stream.fileno(),msvcrt.LK_UNLCK,1)

def atomic_write(path,data):
    import secrets
    path=Path(path);temporary=path.with_name(path.name+'.'+secrets.token_hex(6)+'.tmp')
    try:
        with temporary.open('xb') as stream:stream.write(data);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
    finally:temporary.unlink(missing_ok=True)
