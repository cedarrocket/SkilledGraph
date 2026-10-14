"""Approved Bash only; bounded process-group lifetime and output, not an OS sandbox."""
import os
import selectors
import shutil
import signal
import subprocess
import time


def bash(command, *, cwd, timeout=10, output_limit=16000):
    if not isinstance(command,str) or not command.strip() or len(command)>20000:
        raise ValueError('Command must contain 1..20000 characters')
    if not 0 < timeout <= 30: raise ValueError('Timeout must be in (0,30]')
    executable=shutil.which('bash')
    if not executable: raise RuntimeError('Bash executable unavailable')
    env={'PATH':os.defpath, 'LANG':'C.UTF-8', 'TERM':'dumb'}
    process=subprocess.Popen([executable,'--noprofile','--norc','-c',command],cwd=cwd,
        env=env,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True)
    data=bytearray(); reason=None
    def kill():
        try: os.killpg(process.pid,signal.SIGKILL)
        except ProcessLookupError: pass
    try:
        with selectors.DefaultSelector() as selector:
            selector.register(process.stdout,selectors.EVENT_READ)
            deadline=time.monotonic()+timeout
            while selector.get_map():
                if time.monotonic()>=deadline:
                    reason='timeout'; break
                for key,_ in selector.select(min(0.1,max(0,deadline-time.monotonic()))):
                    chunk=os.read(key.fileobj.fileno(),4096)
                    if not chunk:
                        selector.unregister(key.fileobj); continue
                    remaining=output_limit-len(data)
                    data.extend(chunk[:remaining])
                    if len(chunk)>remaining:
                        reason='output_limit'; break
                if reason: break
        if reason is None:
            try: process.wait(timeout=max(0.001,deadline-time.monotonic()))
            except subprocess.TimeoutExpired: reason='timeout'
        # Reap the main process normally; terminate remaining descendants or limits.
        kill()
        if process.poll() is None: process.wait(timeout=3)
        return {'returncode':process.returncode,'output':data.decode('utf-8',errors='replace'),
                'stopped':reason}
    finally:
        kill()
        process.stdout.close()
        if process.poll() is None: process.wait(timeout=3)
