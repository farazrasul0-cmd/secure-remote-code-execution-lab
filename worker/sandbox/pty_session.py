"""Interactive Pseudo-Terminal (PTY) session manager for low-level terminal emulation.

Handles master/slave PTY allocation, non-blocking asynchronous streaming,
terminal resize ioctls (SIGWINCH), and cross-platform Windows compatibility fallbacks.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import struct
import sys
from typing import Any

logger = logging.getLogger("rce_worker.pty")

# Detect platform capability for POSIX PTY and termios
IS_POSIX = sys.platform != "win32"

if IS_POSIX:
    import fcntl
    import pty
    import termios
else:
    fcntl = None  # type: ignore[assignment]
    pty = None  # type: ignore[assignment]
    termios = None  # type: ignore[assignment]


class PTYSession:
    """Manages an interactive Pseudo-Terminal session for untrusted container/process execution."""

    def __init__(self, cols: int = 80, rows: int = 24):
        self.cols = cols
        self.rows = rows
        self.master_fd: int | None = None
        self.slave_fd: int | None = None
        self.child_pid: int | None = None
        self.is_open: bool = False
        self._reader_task: asyncio.Task | None = None
        self._input_queue: asyncio.Queue[bytes] = asyncio.Queue()

    def open(self) -> tuple[int | None, int | None]:
        """Allocate a new pseudo-terminal master/slave pair on POSIX systems."""
        if not IS_POSIX:
            logger.info(
                "Non-POSIX platform detected. Using standard pipe fallback for PTY emulation."
            )
            self.is_open = True
            return None, None

        try:
            self.master_fd, self.slave_fd = pty.openpty()
            self.set_window_size(self.cols, self.rows)

            # Set non-blocking mode on master_fd
            flags = fcntl.fcntl(self.master_fd, fcntl.F_GETFL)
            o_nonblock = getattr(os, "O_NONBLOCK", 0o4000)
            fcntl.fcntl(self.master_fd, fcntl.F_SETFL, flags | o_nonblock)

            # Ensure newline translation (ONLCR) on slave termios
            attrs = termios.tcgetattr(self.slave_fd)
            attrs[1] = attrs[1] | termios.ONLCR  # c_oflag: translate \n to \r\n
            termios.tcsetattr(self.slave_fd, termios.TCSANOW, attrs)

            self.is_open = True
            logger.info(
                "Allocated Linux PTY pair: master_fd=%d, slave_fd=%d (size: %dx%d)",
                self.master_fd,
                self.slave_fd,
                self.cols,
                self.rows,
            )
            return self.master_fd, self.slave_fd
        except Exception as exc:
            logger.error("Failed to allocate Linux PTY pair: %s", exc)
            self.close()
            raise

    def set_window_size(self, cols: int, rows: int) -> bool:
        """Issue TIOCSWINSZ ioctl to update terminal viewport and trigger SIGWINCH in child."""
        self.cols = max(10, cols)
        self.rows = max(4, rows)

        if not IS_POSIX or self.master_fd is None:
            return True

        try:
            # struct winsize { unsigned short ws_row, ws_col, ws_xpixel, ws_ypixel; };
            winsize = struct.pack("HHHH", self.rows, self.cols, 0, 0)
            fcntl.ioctl(self.master_fd, termios.TIOCSWINSZ, winsize)
            logger.debug(
                "Updated PTY window geometry to %dx%d on master_fd %d",
                self.cols,
                self.rows,
                self.master_fd,
            )
            return True
        except Exception as exc:
            logger.warning("Failed to set window size via TIOCSWINSZ: %s", exc)
            return False

    def write_input(self, data: str | bytes) -> None:
        """Write user keystrokes into the PTY master to be consumed by the child process."""
        data_bytes = data.encode("utf-8") if isinstance(data, str) else data

        if not self.is_open:
            logger.warning("Attempted to write to closed PTY session")
            return

        if IS_POSIX and self.master_fd is not None:
            try:
                os.write(self.master_fd, data_bytes)
            except (BlockingIOError, OSError) as exc:
                logger.warning("PTY master write buffer saturated: %s", exc)
        else:
            # Enqueue for pipe-based fallback
            self._input_queue.put_nowait(data_bytes)

    async def read_output(self, max_bytes: int = 4096) -> bytes:
        """Asynchronously read available terminal output bytes from PTY master."""
        if not self.is_open:
            return b""

        if IS_POSIX and self.master_fd is not None:
            loop = asyncio.get_running_loop()
            try:
                # Wait until master_fd has data available to read
                future = loop.create_future()

                def on_readable():
                    loop.remove_reader(self.master_fd)
                    if not future.done():
                        future.set_result(None)

                loop.add_reader(self.master_fd, on_readable)
                try:
                    await future
                    return os.read(self.master_fd, max_bytes)
                finally:
                    loop.remove_reader(self.master_fd)
            except (OSError, asyncio.CancelledError):
                return b""
        else:
            # Emulated async read
            await asyncio.sleep(0.01)
            return b""

    def send_signal(self, sig: int) -> bool:
        """Forward an operating system signal (e.g. SIGINT, SIGTERM) to child process group."""
        if self.child_pid is None:
            return False

        try:
            os.kill(self.child_pid, sig)
            logger.info("Delivered signal %d to child PID %d", sig, self.child_pid)
            return True
        except ProcessLookupError:
            logger.debug("Child PID %d already terminated", self.child_pid)
            return False
        except Exception as exc:
            logger.error(
                "Failed to forward signal %d to PID %d: %s", sig, self.child_pid, exc
            )
            return False

    def close(self) -> None:
        """Safely release master and slave file descriptors."""
        self.is_open = False
        if IS_POSIX:
            if self.slave_fd is not None:
                with contextlib.suppress(OSError):
                    os.close(self.slave_fd)
                self.slave_fd = None

            if self.master_fd is not None:
                with contextlib.suppress(OSError):
                    os.close(self.master_fd)
                self.master_fd = None
        logger.info("Closed PTYSession cleanly")

    def __enter__(self) -> PTYSession:
        self.open()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self.close()
