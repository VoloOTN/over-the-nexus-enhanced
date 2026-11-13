"""Minimal GDB Remote Serial Protocol (RSP) client for the melonDS GDB stub.

melonDS implements a small RSP server (src/debug/GdbStub.cpp). This client speaks
just enough of it to: halt/continue the ARM9, set hardware breakpoints, read the
register file and read memory — which is all we need to trace the WC2011 effect
engine at runtime.

Verified protocol details (from melonDS master, src/debug/):
  * Register order for `g`/`G` (GdbArch.h `Register` enum, 39 regs):
        r0..r12 = indices 0..12, sp=13, lr=14, pc=15 (PIPELINE-CORRECTED),
        cpsr=16, then banked/spsr regs 17..38.  `g` returns 39*4*2 = 312 hex chars.
  * Breakpoints: `Z0,<addr>,<kind>` / `z0,...`; kind 2=thumb, 4=arm. melonDS
        always installs a HARDWARE breakpoint regardless of type. Reply "OK".
  * Memory: `m<addr>,<len>` (both hex) -> hex byte string; `M<addr>,<len>:<hex>`.
  * Continue: `c` (optionally `c<addr>`); Step: `s`. Reply only arrives when the
        target next stops (breakpoint/watchpoint/break).
  * Halt: send a raw 0x03 byte (no framing).
  * Handshake: on a new connection melonDS expects the client to send a single
        '+' first, then it acks.
  * Ack mode is ON (we never negotiate QStartNoAckMode): every packet we send is
        followed by '+'; every packet we receive we must '+' ack.

This is read/observe tooling only; it never writes registers or memory.
"""

from __future__ import annotations

import socket
import time
from dataclasses import dataclass

# Register indices within the `g` packet (see module docstring).
REG_NAMES = [f"r{i}" for i in range(13)] + ["sp", "lr", "pc", "cpsr"]
REG_PC = 15
REG_LR = 14
REG_SP = 13


@dataclass
class StopReply:
    raw: str
    signal: int | None
    pc: int | None


class RspError(RuntimeError):
    pass


class RspClient:
    """A tiny blocking RSP client for the melonDS GDB stub."""

    def __init__(self, host: str = "127.0.0.1", port: int = 3333,
                 connect_timeout: float = 5.0):
        self.host = host
        self.port = port
        self._buf = bytearray()
        self.sock = socket.create_connection((host, port), timeout=connect_timeout)
        self.sock.settimeout(None)
        # Initial handshake: melonDS wants a leading '+' from the client.
        self.sock.sendall(b"+")

    # -- low level ---------------------------------------------------------
    def _recv_some(self, timeout: float | None) -> None:
        self.sock.settimeout(timeout)
        try:
            data = self.sock.recv(4096)
        except socket.timeout:
            raise TimeoutError("no data from GDB stub")
        finally:
            self.sock.settimeout(None)
        if not data:
            raise RspError("connection closed by stub")
        self._buf.extend(data)

    @staticmethod
    def _cksum(payload: bytes) -> int:
        return sum(payload) & 0xFF

    def _send_packet(self, data: str) -> None:
        payload = data.encode("ascii")
        pkt = b"$" + payload + b"#" + b"%02x" % self._cksum(payload)
        self.sock.sendall(pkt)
        self._wait_ack()

    def _wait_ack(self, timeout: float = 5.0) -> None:
        while True:
            # consume any buffered ack bytes first
            while self._buf:
                c = self._buf[0]
                self._buf.pop(0)
                if c == ord("+"):
                    return
                if c == ord("-"):
                    raise RspError("stub NAK'd our packet")
                # not an ack byte: push back and stop draining
                self._buf.insert(0, c)
                break
            self._recv_some(timeout)

    def _read_packet(self, timeout: float | None = 10.0) -> str:
        """Read one '$...#xx' packet, ack it, and return its inner payload."""
        while True:
            # try to parse a complete packet out of the buffer
            start = self._buf.find(b"$")
            if start != -1:
                hash_idx = self._buf.find(b"#", start)
                if hash_idx != -1 and len(self._buf) >= hash_idx + 3:
                    payload = bytes(self._buf[start + 1:hash_idx])
                    del self._buf[:hash_idx + 3]
                    self.sock.sendall(b"+")  # ack the packet
                    return payload.decode("ascii", "replace")
            self._recv_some(timeout)

    # -- high level --------------------------------------------------------
    def halt(self, timeout: float = 5.0) -> StopReply:
        self.sock.sendall(b"\x03")
        return self._parse_stop(self._read_packet(timeout))

    def add_breakpoint(self, addr: int, kind: int = 2) -> None:
        self._send_packet(f"Z0,{addr:x},{kind}")
        reply = self._read_packet(5.0)
        if reply != "OK":
            raise RspError(f"Z0 @ {addr:#x} failed: {reply!r}")

    def del_breakpoint(self, addr: int, kind: int = 2) -> None:
        self._send_packet(f"z0,{addr:x},{kind}")
        self._read_packet(5.0)

    def add_watchpoint(self, addr: int, length: int = 1, kind: str = "r") -> None:
        """Hardware watchpoint. kind: 'w'=write (Z2), 'r'=read (Z3), 'a'=access (Z4).
        length is the watched region size in bytes."""
        ztype = {"w": 2, "r": 3, "a": 4}[kind]
        self._send_packet(f"Z{ztype},{addr:x},{length:x}")
        reply = self._read_packet(5.0)
        if reply != "OK":
            raise RspError(f"Z{ztype} @ {addr:#x} failed: {reply!r}")

    def del_watchpoint(self, addr: int, length: int = 1, kind: str = "r") -> None:
        ztype = {"w": 2, "r": 3, "a": 4}[kind]
        self._send_packet(f"z{ztype},{addr:x},{length:x}")
        self._read_packet(5.0)

    def cont_and_wait(self, timeout: float | None = None) -> StopReply:
        """Continue; block until the target next stops. timeout=None waits forever."""
        self._send_packet("c")
        return self._parse_stop(self._read_packet(timeout))

    def step(self, timeout: float | None = 5.0) -> StopReply:
        """Single-step one instruction (RSP 's'); block until it stops."""
        self._send_packet("s")
        return self._parse_stop(self._read_packet(timeout))

    def read_registers(self) -> list[int]:
        self._send_packet("g")
        data = self._read_packet(5.0)
        n = len(data) // 8
        regs = [int.from_bytes(bytes.fromhex(data[i * 8:i * 8 + 8]), "little")
                for i in range(n)]
        return regs

    def read_mem(self, addr: int, length: int) -> bytes:
        self._send_packet(f"m{addr:x},{length:x}")
        data = self._read_packet(5.0)
        if data.startswith("E") and len(data) == 3:
            raise RspError(f"memory read @ {addr:#x} failed: {data}")
        return bytes.fromhex(data)

    def write_mem(self, addr: int, data: bytes) -> None:
        """Write bytes to target memory via the RSP 'M' packet (melonDS supports it).
        Used only by deliberate live experiments (e.g. poking a status flag to test a
        hypothesis); normal tracing stays read-only."""
        self._send_packet(f"M{addr:x},{len(data):x}:{data.hex()}")
        reply = self._read_packet(5.0)
        if reply != "OK":
            raise RspError(f"memory write @ {addr:#x} failed: {reply!r}")

    def _parse_stop(self, raw: str) -> StopReply:
        sig = None
        pc = None
        if raw and raw[0] in "ST" and len(raw) >= 3:
            try:
                sig = int(raw[1:3], 16)
            except ValueError:
                sig = None
            # T replies may carry "pc:....." fields; pull a swbreak pc if present
            for field in raw[3:].split(";"):
                if ":" in field:
                    k, _, v = field.partition(":")
                    if k in ("swbreak", "hwbreak", "pc"):
                        try:
                            pc = int.from_bytes(bytes.fromhex(v.zfill(8)), "big")
                        except ValueError:
                            pass
        return StopReply(raw=raw, signal=sig, pc=pc)

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def detach(self) -> None:
        """Clean RSP detach: send 'D' so the stub resumes the target AND keeps
        listening for the next client, then close the socket. melonDS wedges
        (accepts TCP but ignores RSP) if a client just closes mid-session
        without detaching; 'D' avoids that.
        """
        try:
            self._send_packet("D")
            try:
                self._read_packet(2.0)  # expect 'OK'
            except TimeoutError:
                pass
        except Exception:
            pass
        finally:
            self.close()


def connect(host: str = "127.0.0.1", port: int = 3333,
            retries: int = 1, delay: float = 0.5) -> RspClient:
    last: Exception | None = None
    for _ in range(retries):
        try:
            return RspClient(host, port)
        except OSError as exc:  # noqa: PERF203
            last = exc
            time.sleep(delay)
    raise RspError(f"could not connect to GDB stub at {host}:{port}: {last}")
