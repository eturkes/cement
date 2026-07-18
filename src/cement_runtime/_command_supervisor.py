"""Linux one-shot adapter supervisor; private subprocess entry point."""

from __future__ import annotations

import base64
import ctypes
import json
import os
import signal
import subprocess
import sys
import threading
import time
from typing import BinaryIO

_TIMEOUT = 124
_OUTPUT_LIMIT = 125
_START_FAILURE = 126
_CLEANUP_FAILURE = 127


def _become_subreaper() -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), "prctl(PR_SET_CHILD_SUBREAPER) failed")


def _descendants(root: int) -> set[int]:
    parents: dict[int, int] = {}
    try:
        entries = os.scandir("/proc")
    except OSError:
        return set()
    with entries:
        for entry in entries:
            if not entry.name.isdecimal():
                continue
            try:
                with open(f"/proc/{entry.name}/status", "rb") as status:
                    for line in status:
                        if line.startswith(b"PPid:"):
                            parents[int(entry.name)] = int(line.split()[1])
                            break
            except (OSError, ValueError, IndexError):
                continue
    found: set[int] = set()
    frontier = {root}
    while frontier:
        children = {pid for pid, parent in parents.items() if parent in frontier}
        children -= found
        if not children:
            break
        found.update(children)
        frontier = children
    return found


def _children_alive() -> bool:
    """Reap zombies and report whether any adopted child is still running."""

    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except InterruptedError:
            continue
        except ChildProcessError:
            return False
        if pid == 0:
            return True


def _terminate_all(deadline: float) -> bool:
    while time.monotonic() < deadline:
        if not _children_alive():
            return True
        descendants = _descendants(os.getpid())
        for pid in descendants:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        time.sleep(0.01)
    return not _children_alive()


def _read_bounded(
    stream: BinaryIO,
    *,
    limit: int,
    capture: bytearray | None,
    exceeded: threading.Event,
) -> None:
    total = 0
    try:
        while chunk := stream.read(65_536):
            total += len(chunk)
            if total > limit:
                exceeded.set()
                return
            if capture is not None:
                capture.extend(chunk)
    except (OSError, ValueError):
        pass
    finally:
        stream.close()


def _write(stream: BinaryIO, request: bytes) -> None:
    try:
        stream.write(request)
        stream.flush()
    except (BrokenPipeError, OSError):
        pass
    finally:
        stream.close()


def _decode_command(encoded: str) -> tuple[str, ...]:
    value = json.loads(base64.urlsafe_b64decode(encoded.encode("ascii")).decode("utf-8"))
    if type(value) is not list or not value or any(type(item) is not str for item in value):
        raise ValueError("invalid command envelope")
    return tuple(value)


def main() -> int:
    if len(sys.argv) != 4 or not sys.platform.startswith("linux"):
        return _START_FAILURE
    try:
        command = _decode_command(sys.argv[1])
        timeout = float(sys.argv[2])
        limit = int(sys.argv[3])
        request = sys.stdin.buffer.read(2_097_153)
        if len(request) > 2_097_152:
            return _START_FAILURE
        _become_subreaper()
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            close_fds=True,
        )
    except Exception:
        return _START_FAILURE

    raw = bytearray()
    exceeded = threading.Event()
    threads: tuple[threading.Thread, ...] = ()
    started: list[threading.Thread] = []
    timed_out = False
    setup_failed = False
    cleaned = False
    try:
        assert process.stdin is not None and process.stdout is not None
        assert process.stderr is not None
        threads = (
            threading.Thread(target=_write, args=(process.stdin, request), daemon=True),
            threading.Thread(
                target=_read_bounded,
                args=(process.stdout,),
                kwargs={"limit": limit, "capture": raw, "exceeded": exceeded},
                daemon=True,
            ),
            threading.Thread(
                target=_read_bounded,
                args=(process.stderr,),
                kwargs={"limit": limit, "capture": None, "exceeded": exceeded},
                daemon=True,
            ),
        )
        for thread in threads:
            thread.start()
            started.append(thread)
        deadline = time.monotonic() + timeout
        while process.poll() is None:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                timed_out = True
                break
            if exceeded.wait(timeout=min(0.05, remaining)):
                break
    except Exception:
        setup_failed = True
    finally:
        cleanup_deadline = time.monotonic() + 5.0
        # If the adapter created its own process group/session, kill that too.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except OSError:
            pass
        if process.poll() is None:
            try:
                process.kill()
            except OSError:
                pass
        remaining = cleanup_deadline - time.monotonic()
        if remaining > 0:
            try:
                process.wait(timeout=remaining)
            except subprocess.TimeoutExpired:
                pass
        try:
            cleaned = _terminate_all(cleanup_deadline)
        except Exception:
            cleaned = False
        for thread in started:
            thread.join(timeout=max(0.0, cleanup_deadline - time.monotonic()))

    if (
        setup_failed
        or len(started) != len(threads)
        or not cleaned
        or any(thread.is_alive() for thread in started)
    ):
        return _CLEANUP_FAILURE
    if timed_out:
        return _TIMEOUT
    if exceeded.is_set():
        return _OUTPUT_LIMIT
    returncode = process.returncode
    if type(returncode) is not int:
        return _CLEANUP_FAILURE
    if returncode != 0:
        return returncode if 1 <= returncode < _TIMEOUT else 1
    try:
        sys.stdout.buffer.write(raw)
        sys.stdout.buffer.flush()
    except OSError:
        return _CLEANUP_FAILURE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
