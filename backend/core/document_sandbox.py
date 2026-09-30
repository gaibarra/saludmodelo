"""Fail-closed Linux sandbox for document tools; never bind the project or secrets."""
import json
import os
import signal
import subprocess
import tempfile
from pathlib import Path

class SandboxError(Exception):
    pass

def execute(command,*,files=None,signatures=None,certificates=None,ocr_runtime=None,timeout=20,memory=512*1024*1024):
    files=files or {}
    with tempfile.TemporaryDirectory(prefix='salud-sandbox-') as folder:
        root=Path(folder)
        args=['/usr/bin/bwrap','--unshare-user','--unshare-net','--unshare-pid','--unshare-ipc','--unshare-uts','--unshare-cgroup-try','--die-with-parent','--new-session','--cap-drop','ALL','--clearenv','--setenv','LANG','C.UTF-8','--ro-bind','/usr','/usr','--ro-bind','/lib','/lib','--ro-bind','/lib64','/lib64','--proc','/proc','--dev','/dev','--tmpfs','/tmp','--dir','/input','--dir','/app','--chdir','/tmp']
        for index,(target,source) in enumerate(files.items()):
            if not target.startswith(('/input/','/app/')):raise ValueError('Invalid sandbox mount')
            if isinstance(source,bytes):
                path=root/str(index);path.write_bytes(source);path.chmod(0o600)
            else:path=Path(source).resolve(strict=True)
            args+=['--ro-bind',str(path),target]
        if signatures:
            path=Path(signatures).resolve(strict=True)
            args+=['--ro-bind',str(path),'/signatures']
        if certificates:
            args+=['--ro-bind',str(Path(certificates).resolve(strict=True)),'/certificates']
        if ocr_runtime:
            args+=['--ro-bind',str(Path(ocr_runtime).resolve(strict=True)),'/ocr','--setenv','LD_LIBRARY_PATH','/ocr/usr/lib/x86_64-linux-gnu','--setenv','OMP_THREAD_LIMIT','1']
        # Limits apply to the complete process tree, including the sandbox PID 1.
        args=['/usr/bin/nice','-n','10','/usr/bin/prlimit',f'--as={memory}',f'--cpu={max(1,int(timeout))}', '--fsize=16777216','--nofile=64','--core=0','--']+args+['--']+command
        output=root/'output'
        from .sandbox_filter import export
        with (root/'filter').open('w+b') as policy,(root/'status').open('w+b') as status,output.open('wb') as out:
            export(policy.fileno());policy.seek(0)
            split=args.index('--',args.index('/usr/bin/bwrap'))
            args[split:split]=['--seccomp',str(policy.fileno()),'--json-status-fd',str(status.fileno())]
            try:
                child=subprocess.Popen(args,stdout=out,stderr=subprocess.DEVNULL,stdin=subprocess.DEVNULL,env={'LANG':'C.UTF-8'},cwd=folder,start_new_session=True,pass_fds=(policy.fileno(),status.fileno()))
            except OSError as error:raise SandboxError('sandbox_unavailable') from error
            try:child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid,signal.SIGKILL);child.wait();raise SandboxError('sandbox_timeout')
        try:states=[json.loads(line) for line in (root/'status').read_text().splitlines()]
        except ValueError:raise SandboxError('sandbox_unavailable')
        if not any('exit-code' in state for state in states):raise SandboxError('sandbox_unavailable')
        if output.stat().st_size>=16_777_216:raise SandboxError('output_limit')
        return child.returncode,output.read_bytes()

def probe():
    try:
        code,output=execute(['/usr/bin/python3','-I','-c','import os,socket; assert not os.path.exists("/home"); assert not os.path.exists("/run"); assert not os.path.exists("/var"); s=socket.socket(); s.settimeout(0.2); assert s.connect_ex(("192.0.2.1",443))!=0; print("isolated")'])
        return code==0 and output.strip()==b'isolated'
    except (OSError,SandboxError):return False
