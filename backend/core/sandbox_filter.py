"""Compile a process-local seccomp filter; does not change system policy."""
import ctypes
import errno

class Comparison(ctypes.Structure):
    _fields_=[('arg',ctypes.c_uint),('op',ctypes.c_uint),('datum_a',ctypes.c_uint64),('datum_b',ctypes.c_uint64)]

def export(fd):
    lib=ctypes.CDLL('libseccomp.so.2')
    lib.seccomp_init.argtypes=[ctypes.c_uint32];lib.seccomp_init.restype=ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes=[ctypes.c_char_p];lib.seccomp_syscall_resolve_name.restype=ctypes.c_int
    lib.seccomp_rule_add.argtypes=[ctypes.c_void_p,ctypes.c_uint32,ctypes.c_int,ctypes.c_uint]
    lib.seccomp_export_bpf.argtypes=[ctypes.c_void_p,ctypes.c_int]
    lib.seccomp_release.argtypes=[ctypes.c_void_p]
    ctx=lib.seccomp_init(0x7fff0000)
    if not ctx:raise OSError('Cannot initialize seccomp')
    try:
        for name in ['fork','vfork','unshare','setns','ptrace','process_vm_readv','process_vm_writev','mount','umount2','pivot_root','bpf','perf_event_open','userfaultfd','open_by_handle_at']:
            num=lib.seccomp_syscall_resolve_name(name.encode())
            if num>=0 and lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,num,0)!=0:raise OSError('Cannot compile sandbox filter')
        clone3=lib.seccomp_syscall_resolve_name(b'clone3')
        if clone3>=0 and lib.seccomp_rule_add(ctx,0x00050000|errno.ENOSYS,clone3,0)!=0:raise OSError('Cannot filter clone3')
        # Permit native library threads; forbid creating another process.
        clone=lib.seccomp_syscall_resolve_name(b'clone')
        if clone>=0 and lib.seccomp_rule_add(ctx,0x00050000|errno.EPERM,clone,1,Comparison(0,7,0x10000,0))!=0:raise OSError('Cannot filter clone')
        if lib.seccomp_export_bpf(ctx,fd)!=0:raise OSError('Cannot export sandbox filter')
    finally:lib.seccomp_release(ctx)
