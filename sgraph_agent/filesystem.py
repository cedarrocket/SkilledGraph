"""POSIX workspace file operations, using dir-fds and no-follow opens."""
from contextlib import contextmanager
import hashlib
import os
from pathlib import Path, PurePosixPath
import stat
import weakref
from uuid import uuid4

BLOCKED = {'.git', '.aws', '.ssh', '.codex', '.agents', 'credentials', 'auth.json', 'deepseek_api.txt'}
MAX_FILE_BYTES = 1024 * 1024


class Workspace:
    def __init__(self, root):
        if os.name != 'posix':
            raise RuntimeError('Workspace safety currently requires POSIX dir-fd APIs')
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir(): raise ValueError('Workspace must be a directory')
        self._root_fd = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        self._cleanup = weakref.finalize(self, os.close, self._root_fd)

    def parts(self, name, *, directory=False):
        if not isinstance(name, str) or not name or '\x00' in name or '\\' in name:
            raise ValueError('Use a nonempty relative POSIX path')
        path = PurePosixPath(name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Path must stay inside the workspace')
        parts = path.parts
        if not parts and not directory: raise ValueError('File path required')
        for part in parts:
            lower = part.lower()
            if lower in BLOCKED or lower.startswith('.env') or lower.endswith(('.pem', '.key')):
                raise ValueError('Credential/private path is blocked')
        return parts

    @contextmanager
    def directory(self, name='.'):
        parts = self.parts(name, directory=True)
        fd = os.dup(self._root_fd)
        try:
            for part in parts:
                new = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=fd)
                os.close(fd)
                fd = new
            yield fd
        finally: os.close(fd)

    @contextmanager
    def parent(self, name):
        parts = self.parts(name)
        with self.directory('/'.join(parts[:-1]) or '.') as fd:
            yield fd, parts[-1]

    def check(self, name, *, write=False, directory=False):
        if directory:
            with self.directory(name): pass
        else:
            with self.parent(name) as (fd, leaf):
                try: info = os.stat(leaf, dir_fd=fd, follow_symlinks=False)
                except FileNotFoundError:
                    if write: return
                    raise
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError('Only regular files with one link are permitted')

    def read(self, name):
        with self.parent(name) as (parent, leaf):
            fd = os.open(leaf, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=parent)
            try:
                info = os.fstat(fd)
                if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
                    raise ValueError('Only regular files with one link are permitted')
                if info.st_size > MAX_FILE_BYTES: raise ValueError('File exceeds 1 MiB')
                with os.fdopen(fd, 'rb', closefd=False) as source:
                    data = source.read(MAX_FILE_BYTES + 1)
                if len(data) > MAX_FILE_BYTES: raise ValueError('File exceeds 1 MiB')
                if b'\x00' in data: raise ValueError('Binary file unsupported')
                return data.decode('utf-8')
            finally: os.close(fd)

    def write(self, name, content):
        data = content.encode('utf-8')
        if len(data) > MAX_FILE_BYTES: raise ValueError('Write exceeds 1 MiB')
        self.check(name, write=True)
        with self.parent(name) as (fd, leaf):
            try: mode = stat.S_IMODE(os.stat(leaf,dir_fd=fd,follow_symlinks=False).st_mode) & 0o777
            except FileNotFoundError: mode = 0o600
            temporary = '.sgraph-write-' + str(uuid4())
            handle = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=fd)
            try:
                os.fchmod(handle,mode)
                with os.fdopen(handle, 'wb') as target:
                    target.write(data)
                    target.flush()
                    os.fsync(target.fileno())
                # Replacement never follows a symlink installed after check().
                os.replace(temporary, leaf, src_dir_fd=fd, dst_dir_fd=fd)
            finally:
                try: os.unlink(temporary, dir_fd=fd)
                except FileNotFoundError: pass
        return {'path':name, 'bytes':len(data), 'sha256':hashlib.sha256(data).hexdigest()}

    def entries(self, name='.'):
        result=[]
        with self.directory(name) as fd, os.scandir(fd) as entries:
            for index, entry in enumerate(entries):
                if index >= 2000: break
                leaf=entry.name
                path=(PurePosixPath(name) / leaf).as_posix()
                try:
                    self.parts(path)
                    info=os.stat(leaf,dir_fd=fd,follow_symlinks=False)
                    if stat.S_ISDIR(info.st_mode): result.append({'path':path,'kind':'directory'})
                    elif stat.S_ISREG(info.st_mode) and info.st_nlink == 1:
                        result.append({'path':path,'kind':'file'})
                except (OSError,ValueError): continue
        return sorted(result,key=lambda entry:entry['path'])[:500]
