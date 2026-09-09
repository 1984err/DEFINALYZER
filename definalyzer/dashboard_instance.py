"""One dashboard owns a workspace's job queue at a time."""
import os


class DashboardLease:
    def __init__(self, root):
        root.mkdir(parents=True, exist_ok=True)
        self.stream = (root / '.dashboard-instance.lock').open('a+b')
        try:
            self.stream.seek(0, 2)
            if not self.stream.tell():
                self.stream.write(b'0'); self.stream.flush()
            self.stream.seek(0)
            if os.name == 'nt':
                import msvcrt
                msvcrt.locking(self.stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(self.stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as error:
            self.stream.close(); self.stream = None
            raise RuntimeError('A dashboard is already running for this workspace. Use the existing dashboard window.') from error

    def close(self):
        if self.stream is not None:
            self.stream.close(); self.stream = None
