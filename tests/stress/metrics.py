"""Resource metrics monitoring for stress tests — memory, FD, subprocess leaks."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field


@dataclass
class Snapshot:
    timestamp: float
    rss_mb: float
    fd_count: int
    child_count: int


def rss_mb() -> float:
    """Return current process RSS in MB."""
    try:
        with open("/proc/self/status") as fh:
            for line in fh:
                if line.startswith("VmRSS:"):
                    parts = line.split()
                    return float(parts[1]) / 1024.0
    except (FileNotFoundError, PermissionError):
        pass
    return 0.0


def fd_count() -> int:
    """Count open file descriptors for the current process."""
    try:
        return len(os.listdir("/proc/self/fd"))
    except (FileNotFoundError, PermissionError):
        return 0


def child_count() -> int:
    """Count child processes (zombie detection)."""
    try:
        pid = os.getpid()
        count = 0
        for entry in os.listdir("/proc"):
            if not entry.isdigit():
                continue
            try:
                with open(f"/proc/{entry}/stat") as fh:
                    stat = fh.read()
                ppid = stat.split(") ", 1)[1].split()[1] if ") " in stat else "0"
                if int(ppid) == pid:
                    count += 1
            except (FileNotFoundError, PermissionError, ValueError):
                pass
        return count
    except (FileNotFoundError, PermissionError):
        return 0


def take_snapshot() -> Snapshot:
    return Snapshot(
        timestamp=time.monotonic(),
        rss_mb=rss_mb(),
        fd_count=fd_count(),
        child_count=child_count(),
    )


@dataclass
class LeakDetector:
    baseline: Snapshot | None = None
    snapshots: list[Snapshot] = field(default_factory=list)
    max_rss_mb: float = 0.0
    max_fd: int = 0

    def set_baseline(self) -> None:
        self.baseline = take_snapshot()
        self.max_rss_mb = self.baseline.rss_mb
        self.max_fd = self.baseline.fd_count

    def check(self) -> Snapshot:
        snap = take_snapshot()
        self.snapshots.append(snap)
        self.max_rss_mb = max(self.max_rss_mb, snap.rss_mb)
        self.max_fd = max(self.max_fd, snap.fd_count)
        return snap

    def summary(self) -> dict:
        if not self.baseline:
            return {"error": "No baseline set"}
        return {
            "baseline_rss_mb": round(self.baseline.rss_mb, 2),
            "peak_rss_mb": round(self.max_rss_mb, 2),
            "rss_growth_mb": round(self.max_rss_mb - self.baseline.rss_mb, 2),
            "baseline_fd": self.baseline.fd_count,
            "peak_fd": self.max_fd,
            "fd_growth": self.max_fd - self.baseline.fd_count,
            "snapshot_count": len(self.snapshots),
        }
