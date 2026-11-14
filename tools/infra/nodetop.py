#!/usr/bin/env python3
"""nodetop — one-terminal, top-like view of the build/test nodes.

Per node it shows: cores, 1-minute load (as a bar and percent), memory
available, disk use, how many test processes are running, which task owns
them, and the hottest process.  Refreshes in place; ``q`` / Ctrl-C quits.

Usage
-----
    python3 tools/infra/nodetop.py                 # live, 2 s refresh
    python3 tools/infra/nodetop.py --interval 5
    python3 tools/infra/nodetop.py --once          # one snapshot (pipe-friendly)
    python3 tools/infra/nodetop.py --hosts ics150,server207
    python3 tools/infra/nodetop.py --repo /home/ubuntu/DADAO-v5

Transport is plain ``ssh -o BatchMode=yes <host>`` (hosts come from
``~/.ssh/config``; same assumption as ``tools/infra/remote.py``).  The remote
side is a short POSIX shell script fed on stdin, so there are no quoting
games.  A node that is unreachable or slow is reported as ``ERR`` and keeps
showing its last good numbers plus the error, so one dead node never blanks
the view.

Exit status: 0 on clean quit (and on ``--once`` when at least one node
answered), 1 when ``--once`` found no reachable node.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import shutil
import subprocess
import sys
import time

DEFAULT_HOSTS = ["ics150", "ics160", "ics170", "ics180", "server207", "server208"]
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
       "-o", "ServerAliveInterval=2", "-o", "ServerAliveCountMax=1"]

# Remote probe: one key=value line each, so values may contain spaces.
PROBE = r"""
repo="$1"
echo "cores=$(nproc 2>/dev/null || echo 0)"
awk '{print "load1=" $1; print "load5=" $2}' /proc/loadavg 2>/dev/null
awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{print "mem_total_kb=" t+0; print "mem_avail_kb=" a+0}' /proc/meminfo
if [ -d "$repo" ]; then
  df -Pk "$repo" 2>/dev/null | awk 'NR==2{print "disk_used_kb=" $3; print "disk_total_kb=" $2}'
fi
echo "tests=$(pgrep -c -f 'harness-WumingTinyConfig|qemu-system-dadao|gem5\.opt' 2>/dev/null || echo 0)"
echo "top=$(ps -eo pcpu=,args= --sort=-pcpu 2>/dev/null | grep -v '[p]s -eo' | head -1 | cut -c1-100)"
echo "task=$(ps -eo args= 2>/dev/null | grep -v 'grep -' | grep -oE '/(tmp/opencode|eval)/[a-z0-9-]+|\.dadao/tests/[a-z0-9-]+' | sed 's#^\.dadao/tests/##' | sort | uniq -c | sort -rn | head -1 | awk '{print $1 "x " $2}')"
"""

INT_FIELDS = {"cores": "cores", "tests": "tests", "mem_total_kb": "mem_total",
              "mem_avail_kb": "mem_avail", "disk_used_kb": "du", "disk_total_kb": "dt"}
FLOAT_FIELDS = {"load1": "load1", "load5": "load5"}


class Sample:
    __slots__ = ("cores", "load1", "load5", "mem_total", "mem_avail", "du", "dt",
                 "tests", "top", "task", "stamp", "latency", "err")

    def __init__(self) -> None:
        self.cores = 0
        self.load1 = 0.0
        self.load5 = 0.0
        self.mem_total = 0
        self.mem_avail = 0
        self.du = 0
        self.dt = 0
        self.tests = 0
        self.top = ""
        self.task = ""
        self.stamp = 0.0     # wall clock when the sample arrived
        self.latency = 0.0   # ssh round trip
        self.err = ""


def probe(host: str, repo: str, timeout: float) -> Sample:
    s = Sample()
    t0 = time.time()
    try:
        cp = subprocess.run(SSH + [host, "sh -s -- " + repo], input=PROBE,
                            text=True, capture_output=True, timeout=timeout)
        if cp.returncode != 0:
            msg = (cp.stderr or "").strip().splitlines()
            s.err = msg[-1][:48] if msg else f"ssh rc={cp.returncode}"
        for line in cp.stdout.splitlines():
            if "=" not in line:
                continue
            k, v = line.split("=", 1)
            v = v.strip()
            if k in INT_FIELDS:
                try:
                    setattr(s, INT_FIELDS[k], int(float(v)))
                except ValueError:
                    pass
            elif k in FLOAT_FIELDS:
                try:
                    setattr(s, FLOAT_FIELDS[k], float(v))
                except ValueError:
                    pass
            elif k == "top":
                s.top = v
            elif k == "task":
                s.task = v
    except subprocess.TimeoutExpired:
        s.err = "timeout"
    except Exception as exc:  # noqa: BLE001 - one host must never kill the view
        s.err = type(exc).__name__
    s.latency = time.time() - t0
    s.stamp = time.time()
    return s


def fmt_kb(kb: float) -> str:
    if kb <= 0:
        return "-"
    for unit in ("K", "M", "G", "T"):
        if kb < 1024 or unit == "T":
            return f"{kb:.0f}{unit}" if unit == "K" else f"{kb:.1f}{unit}"
        kb /= 1024
    return f"{kb:.0f}T"


def bar(frac: float, width: int) -> str:
    frac = max(0.0, min(1.0, frac))
    n = int(round(frac * width))
    return "#" * n + "." * (width - n)


def render(hosts, state, width, color, tick, interval) -> str:
    now = time.time()
    out = [f"nodetop  {time.strftime('%H:%M:%S')}  tick={tick}  refresh={interval:g}s  (q 退出)",
           "-" * width,
           f"{'HOST':<10} {'CORE':>4} {'LOAD1':>6} {'LOAD%':>5} {'LOAD':<9} "
           f"{'MEM-AVAIL':>10} {'DISK%':>5} {'TEST':>4}  TOP / TASK"]
    for h in hosts:
        s = state.get(h)
        if s is None:
            out.append(f"{h:<10}  (等待首个采样…)")
            continue
        loadpct = (s.load1 / s.cores) if s.cores else 0.0
        diskpct = (s.du / s.dt) if s.dt else 0.0
        tag = ""
        if s.err:
            age = max(0.0, now - s.stamp)
            tag = f"  [ERR {s.err}｜上次成功 {age:.0f}s 前]"
        elif loadpct >= 1.0:
            tag = "  [满载]"
        elif diskpct >= 0.9:
            tag = "  [磁盘告警]"
        out.append(f"{h:<10} {s.cores:>4} {s.load1:>6.2f} {loadpct * 100:>4.0f}% "
                   f"{bar(loadpct, 9)} {fmt_kb(s.mem_avail):>10} {diskpct * 100:>4.0f}% "
                   f"{s.tests:>4}  {(s.top or '-')[:74]}{tag}")
        out.append(f"{'':<10} {'':>4} {'':>6} {'':>5} {'':<9} {'':>10} {'':>5} {'':>4}  "
                   f"task: {s.task or '-'}｜latency {s.latency * 1000:.0f}ms")
    out.append("-" * width)
    out.append("阈值：LOAD% ≥100% 红（满载）｜节点可多任务共占，合计并行度 ≤ 核数-2｜DISK% ≥90% 先清")
    text = "\n".join(out)
    if not color:
        return text
    RED, YEL, DIM, OFF = "\033[31m", "\033[33m", "\033[2m", "\033[0m"
    painted = []
    for ln in text.splitlines():
        if ln.startswith("nodetop"):
            painted.append(DIM + ln + OFF)
        elif "[满载]" in ln or "[磁盘告警]" in ln:
            painted.append(RED + ln + OFF)
        elif "[ERR" in ln:
            painted.append(YEL + ln + OFF)
        elif ln.startswith("-") or ln.startswith("阈值") or ln.startswith("HOST"):
            painted.append(DIM + ln + OFF)
        else:
            painted.append(ln)
    return "\n".join(painted)


def main() -> int:
    ap = argparse.ArgumentParser(description="top-like view of the build nodes")
    ap.add_argument("--hosts", default=os.environ.get("DADAO_NODES", ""),
                    help="comma/space separated; default $DADAO_NODES or the six known nodes")
    ap.add_argument("--repo", default=os.environ.get("DADAO_NODE_REPO", "/home/ubuntu/DADAO-v5"),
                    help="remote repository root, used for disk usage")
    ap.add_argument("--interval", type=float, default=2.0)
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--once", action="store_true", help="print one snapshot and exit")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    hosts = args.hosts.replace(",", " ").split() or DEFAULT_HOSTS
    width = min(shutil.get_terminal_size((140, 30)).columns, 150)
    color = sys.stdout.isatty() and not args.no_color
    state: dict[str, Sample] = {}

    def snapshot() -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as ex:
            futures = {ex.submit(probe, h, args.repo, args.timeout): h for h in hosts}
            for fut in concurrent.futures.as_completed(futures):
                h = futures[fut]
                new = fut.result()
                if new.err and h in state:
                    state[h].err = new.err       # keep last good numbers
                else:
                    state[h] = new

    if args.once:
        snapshot()
        print(render(hosts, state, width, color, 0, args.interval))
        return 0 if any(not s.err for s in state.values()) else 1

    tick = 0
    try:
        if color:
            sys.stdout.write("\033[?25l")        # hide cursor
        while True:
            tick += 1
            snapshot()
            sys.stdout.write("\033[H\033[J" + render(hosts, state, width, color,
                                                     tick, args.interval) + "\n")
            sys.stdout.flush()
            time.sleep(max(0.2, args.interval))
    except KeyboardInterrupt:
        pass
    finally:
        if color:
            sys.stdout.write("\033[?25h\n")      # restore cursor
    return 0


if __name__ == "__main__":
    sys.exit(main())
