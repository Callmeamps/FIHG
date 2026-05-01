"""PTY-based terminal runtime for Unix systems.

Manages real shell subprocesses with pseudo-terminal (PTY) support.
Sessions are tracked in-memory; each session emits stdout/stderr via an
asyncio.Queue and can be consumed through stream().

Usage:
    runtime = TerminalRuntime()
    sess = await runtime.spawn("/bin/bash")
    await runtime.write(sess.id, "ls -la\\n")
    async for chunk in runtime.stream(sess.id):
        print(chunk, end="")
"""

import asyncio
import fcntl
import os
import pty
import signal
import struct
import termios
import time
import uuid
from dataclasses import dataclass, field
from typing import AsyncIterator, Optional


@dataclass
class TermSession:
    """A live terminal session backed by a PTY."""
    id: str
    command: str
    pid: int
    fd: int
    status: str = "running"  # running, closed, errored
    exit_code: Optional[int] = None
    buffer: str = ""
    created_at: float = field(default_factory=time.time)
    queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)


class TerminalRuntime:
    """Manages PTY sessions. One runtime per process."""

    def __init__(self):
        self._sessions: dict[str, TermSession] = {}
        self._readers: dict[str, asyncio.Task] = {}

    async def spawn(self, command: str = "/bin/bash", cols: int = 80, rows: int = 24) -> TermSession:
        """Spawn a new PTY session.

        Args:
            command: The command to run (e.g., "/bin/bash").
            cols, rows: Initial terminal dimensions.

        Returns:
            A TermSession object with the allocated PTY.
        """
        session_id = str(uuid.uuid4())
        pid, fd = pty.fork()

        if pid == 0:
            # Child process
            try:
                signal.signal(signal.SIGTERM, signal.SIG_DFL)
                os.environ["TERM"] = "xterm-256color"
                os.execvp(command.split()[0], command.split())
            except Exception:
                os._exit(1)
        else:
            # Parent
            fcntl.fcntl(fd, fcntl.F_SETFL, os.O_NONBLOCK)
            self._set_winsize(fd, rows, cols)

            session = TermSession(
                id=session_id,
                command=command,
                pid=pid,
                fd=fd,
            )
            self._sessions[session_id] = session
            self._readers[session_id] = asyncio.create_task(
                self._read_loop(session)
            )
            return session

    async def write(self, session_id: str, data: str) -> None:
        """Write data to the PTY."""
        session = self._sessions.get(session_id)
        if not session or session.status != "running":
            raise RuntimeError(f"Session {session_id} not running")
        os.write(session.fd, data.encode())

    async def resize(self, session_id: str, cols: int, rows: int) -> None:
        """Resize the PTY dimensions."""
        session = self._sessions.get(session_id)
        if not session:
            raise RuntimeError(f"Session {session_id} not found")
        self._set_winsize(session.fd, rows, cols)

    async def close(self, session_id: str) -> None:
        """Close a session by killing the child process."""
        session = self._sessions.get(session_id)
        if not session:
            return
        if session_id in self._readers:
            self._readers[session_id].cancel()
        try:
            os.kill(session.pid, signal.SIGTERM)
            await asyncio.sleep(0.1)
            try:
                os.waitpid(session.pid, os.WNOHANG)
            except ChildProcessError:
                pass
        except ProcessLookupError:
            pass
        finally:
            session.status = "closed"
            await session.queue.put(None)  # signal end of stream
            try:
                os.close(session.fd)
            except OSError:
                pass

    async def stream(
        self, session_id: str, full_output: bool = False
    ) -> AsyncIterator[str]:
        """Yield output chunks as they arrive from the PTY.

        Args:
            session_id: ID of the session to stream.
            full_output: If True, yield the existing buffer first before
                         streaming live data. Use to capture full session
                         history (e.g., after a cell has finished running).
                         If False, only stream new data from the queue.

        Yields:
            Raw output chunks (bytes decoded as strings).
        """
        session = self._sessions.get(session_id)
        if not session:
            return

        if full_output:
            yield session.buffer

        while session.status == "running":
            try:
                chunk = await session.queue.get()
            except asyncio.CancelledError:
                break
            if chunk is None:
                break
            yield chunk

        # Drain any remaining queued output after session closes
        if session.status == "closed":
            while not session.queue.empty():
                try:
                    chunk = session.queue.get_nowait()
                    if chunk is None:
                        break
                    yield chunk
                except asyncio.QueueEmpty:
                    break

    async def _read_loop(self, session: TermSession) -> None:
        """Background task: read PTY output and push to session queue."""
        loop = asyncio.get_running_loop()
        try:
            while session.status == "running":
                data = await loop.run_in_executor(None, os.read, session.fd, 4096)
                if not data:
                    break
                decoded = data.decode(errors="replace")
                session.buffer += decoded
                await session.queue.put(decoded)
        except (OSError, BlockingIOError):
            pass
        finally:
            session.status = "closed"
            await session.queue.put(None)  # mark end of stream
            try:
                _, status = os.waitpid(session.pid, os.WNOHANG)
                session.exit_code = os.WEXITSTATUS(status) if os.WIFEXITED(status) else -1
            except ProcessLookupError:
                session.exit_code = -1

    def _set_winsize(self, fd: int, rows: int, cols: int) -> None:
        """Set PTY window size via TIOCSWINSZ ioctl."""
        if os.isatty(fd):
            size = struct.pack("HHHH", rows, cols, 0, 0)
            fcntl.ioctl(fd, termios.TIOCSWINSZ, size)

    @property
    def sessions(self) -> dict[str, TermSession]:
        return dict(self._sessions)