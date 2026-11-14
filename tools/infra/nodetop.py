#!/usr/bin/env python3
"""nodetop — tmux-like 2×3 pane view of the six build/test nodes.

Each pane is one node: a header line (cores, 1-min load, memory, disk, how many
test processes are running, ssh latency) followed by the **hottest processes**
(default 10).  A node that times out shows ``ERR`` and keeps its last good
numbers, so one dead node never blanks the grid.

Usage
-----
    python3 tools/infra/nodetop.py                  # live grid, 2 s refresh, q 退出
    python3 tools/infra/nodetop.py --procs 12 --interval 3
    python3 tools/infra/nodetop.py --once           # one plain table (pipe-friendly)
    python3 tools/infra/nodetop.py --hosts ics150,server207
    python3 tools/infra/nodetop.py --layout list    # live, one block per node

Keys: ``q`` / ``Q`` / Esc quit, ``p`` pause/resume, ``+``/``-`` change refresh.
Transport is plain ``ssh -o BatchMode=yes <host>`` (hosts from
``~/.ssh/config``, same assumption as ``tools/infra/remote.py``); the remote
side is a short POSIX shell script fed on stdin, so there is no quoting.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import select
import shutil
import subprocess
import sys
import time

DEFAULT_HOSTS = ["ics150", "ics160", "server207", "ics170", "ics180", "server208"]
SSH = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=4",
       "-o", "ServerAliveInterval=2", "-o", "ServerAliveCountMax=1"]

# Remote probe: one key=value per line; process lines are "p=<cpu>\t<name>\t<detail>".
PROBE = r"""
repo="$1"; n="$2"
echo "cores=$(nproc 2>/dev/null || echo 0)"
awk '{print "load1=" $1; print "load5=" $2}' /proc/loadavg 2>/dev/null
awk '/^MemTotal:/{t=$2} /^MemAvailable:/{a=$2} END{print "mem_total_kb=" t+0; print "mem_avail_kb=" a+0}' /proc/meminfo
if [ -d "$repo" ]; then
  df -Pk "$repo" 2>/dev/null | awk 'NR==2{print "disk_used_kb=" $3; print "disk_total_kb=" $2}'
fi
echo "tests=$(pgrep -c -f 'harness-WumingTinyConfig|qemu-system-dadao|gem5\.opt' 2>/dev/null || echo 0)"
ps -eo pcpu=,etime=,args= --sort=-pcpu 2>/dev/null | grep -vE '[p]s -eo|[p]grep -c|[d]f -Pk|[s]h -s --|[a]wk /|grep -oE' | head -"$n" | while read -r cpu etime args; do
  name=$(printf '%s' "$args" | awk '{print $1}' | sed 's#.*/##')
  detail=$(printf '%s' "$args" | grep -oE '\+loadmem=[^ ]+' | sed 's#.*/##' | head -1)
  [ -z "$detail" ] && detail=$(printf '%s' "$args" | grep -oE '/tmp/opencode/[a-z0-9-]+|\.dadao/tests/[a-z0-9-]+' | head -1 | sed 's#.*/##')
  printf 'p=%s\t%s\t%s\t%s\n' "$cpu" "$etime" "$name" "$detail"
done
"""

INT_FIELDS = {"cores": "cores", "tests": "tests", "mem_total_kb": "mem_total",
              "mem_avail_kb": "mem_avail", "disk_used_kb": "du", "disk_total_kb": "dt"}
FLOAT_FIELDS = {"load1": "load1", "load5": "load5"}


class Sample:
    __slots__ = ("cores", "load1", "load5", "mem_total", "mem_avail", "du", "dt",
                 "tests", "procs", "stamp", "latency", "err")

    def __init__(self) -> None:
        self.cores = 0
        self.load1 = 0.0
        self.load5 = 0.0
        self.mem_total = 0
        self.mem_avail = 0
        self.du = 0
        self.dt = 0
        self.tests = 0
        self.procs: list[tuple[float, str, str, str]] = []
        self.stamp = 0.0
        self.latency = 0.0
        self.err = ""


def probe(host: str, repo: str, nprocs: int, timeout: float) -> Sample:
    s = Sample()
    t0 = time.time()
    try:
        cp = subprocess.run(SSH + [host, f"sh -s -- {repo} {nprocs}"], input=PROBE,
                            text=True, capture_output=True, timeout=timeout)
        if cp.returncode != 0:
            msg = (cp.stderr or "").strip().splitlines()
            s.err = msg[-1][:40] if msg else f"ssh rc={cp.returncode}"
        for line in cp.stdout.splitlines():
            if line.startswith("p="):
                parts = line[2:].split("\t")
                if len(parts) >= 3:
                    try:
                        s.procs.append((float(parts[0]), parts[1], parts[2],
                                        parts[3] if len(parts) > 3 else ""))
                    except ValueError:
                        pass
                continue
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
            return f"{kb:.0f}{unit}"
        kb /= 1024
    return f"{kb:.0f}T"


def fit(text: str, width: int) -> str:
    return text if len(text) <= width else text[: max(0, width - 1)] + "…"


def compact_etime(raw: str) -> str:
    """ps etime (`[[dd-]hh:]mm:ss`) -> fixed 5 chars: mm:ss / hh:mm / Nd HH."""
    raw = raw.strip()
    days = 0
    if "-" in raw:
        d, raw = raw.split("-", 1)
        try:
            days = int(d)
        except ValueError:
            return raw[:5]
    parts = raw.split(":")
    try:
        nums = [int(x) for x in parts]
    except ValueError:
        return raw[:5]
    if days:
        return f"{days}d{nums[0] if nums else 0:02d}"
    if len(nums) == 3:
        return f"{nums[0]:02d}:{nums[1]:02d}"
    if len(nums) == 2:
        return f"{nums[0]:02d}:{nums[1]:02d}"
    return raw[:5]


def proc_line(cpu: float, etime: str, name: str, detail: str, width: int) -> str:
    """CPU% | elapsed | full binary name (no abbreviation); hint only if it fits.

    When the name is wider than the pane keeps the *tail* (that is what tells
    the binaries apart, e.g. ``...WumingTinyConfig``), never an invented alias.
    """
    prefix = f"{cpu:>4.0f}% {compact_etime(etime):>5} "
    room = width - len(prefix)
    shown = name if len(name) <= room else "…" + name[-(room - 1):] if room > 1 else name[:room]
    head = prefix + shown
    if detail:
        room = width - len(head) - 2
        if room >= len(detail) + 1:
            head += " " + detail
        elif room >= 8:                      # keep the hint's tail (the ELF name)
            head += " " + detail[-(room - 1):]
    return fit(head, width)


def pane(s: Sample | None, host: str, w: int, nlines: int, now: float) -> list[str]:
    """One header line (all gauges + ssh latency) then nlines process lines."""
    if s is None:
        lines = [fit(f"{host}  等待采样…", w)]
        return lines + [""] * nlines
    loadpct = (s.load1 / s.cores * 100) if s.cores else 0.0
    diskpct = (s.du / s.dt * 100) if s.dt else 0.0
    state = ""
    if s.err:
        state = f" ERR {s.err}({max(0, now - s.stamp):.0f}s前)"
    elif loadpct >= 100:
        state = " 满载"
    elif diskpct >= 90:
        state = " 磁盘!"
    head = (f"{host} {s.cores}c L{s.load1:.1f}({loadpct:.0f}%) "
            f"M{fmt_kb(s.mem_avail)} D{diskpct:.0f}% T{s.tests} "
            f"ssh{s.latency:.2f}s{state}")
    lines = [fit(head, w)]
    for cpu, etime, name, detail in s.procs[:nlines]:
        lines.append(proc_line(cpu, etime, name, detail, w))
    while len(lines) < 1 + nlines:
        lines.append("")
    return lines[: 1 + nlines]


def pane_lines(h: int, cap: int = 0, rows: int = 2) -> int:
    """How many process rows fit in one pane at this terminal height."""
    chrome = 4  # title + legend + 2 separator lines
    pane_h = max(4, (h - chrome) // rows)
    n = max(3, pane_h - 1)
    return min(n, cap) if cap > 0 else n


def render_grid(hosts, state, w, h, nlines, color, tick, interval) -> str:
    now = time.time()
    cols, rows = 3, 2
    gutter = 1
    pane_w = max(24, (w - (cols - 1) * gutter) // cols)
    panes = []
    for i, host in enumerate(hosts):
        panes.append(pane(state.get(host), host, pane_w, nlines, now))

    title = (f"nodetop {time.strftime('%H:%M:%S')}  tick={tick}  {interval:g}s  "
             f"procs={nlines}/pane   q=quit p=pause +/-=refresh")
    legend = ("字段：L=1 分钟负载(占核数%)  M=可用内存  D=磁盘使用率  T=测试进程数  "
              "ssh=采样往返延迟｜进程行：CPU% ｜ 已运行时间 ｜ 进程名")
    out = [fit(title, w), fit(legend, w), "-" * w]
    for r in range(rows):
        chunk = panes[r * cols:(r + 1) * cols]
        for line_i in range(1 + nlines):
            cells = [c[line_i] if line_i < len(c) else "" for c in chunk]
            row = ("│" * gutter).join(cell.ljust(pane_w) for cell in cells)
            out.append(fit(row, w))
        if r < rows - 1:
            out.append("┼" * w)
    out.append("-" * w)
    out.append(fit("阈值：LOAD% ≥100% 红｜节点可多任务共占（并行度之和 ≤ 核数−2）｜"
                   f"DISK% ≥90% 先清｜q 退出", w))
    text = "\n".join(out)
    if not color:
        return text
    RED, YEL, DIM, OFF = "\033[31m", "\033[33m", "\033[2m", "\033[0m"
    painted = []
    for ln in text.splitlines():
        if ln.startswith("nodetop") or ln.startswith("-") or ln.startswith("┼") \
                or ln.startswith("阈值"):
            painted.append(DIM + ln + OFF)
        elif "满载" in ln or "磁盘!" in ln:
            painted.append(RED + ln + OFF)
        elif "ERR" in ln:
            painted.append(YEL + ln + OFF)
        else:
            painted.append(ln)
    return "\n".join(painted)


def render_list(hosts, state, w, nprocs, now) -> str:
    out = [f"nodetop {time.strftime('%H:%M:%S')}  (list)", "-" * min(w, 150)]
    for h in hosts:
        s = state.get(h)
        if s is None:
            out.append(f"{h}: 等待采样…")
            continue
        loadpct = (s.load1 / s.cores * 100) if s.cores else 0.0
        diskpct = (s.du / s.dt * 100) if s.dt else 0.0
        flag = f"  ERR {s.err}" if s.err else ""
        out.append(f"{h:<10} {s.cores:>3}c  L{s.load1:5.1f} ({loadpct:3.0f}%)  "
                   f"M{fmt_kb(s.mem_avail):>8}  D{diskpct:3.0f}%  T{s.tests:>3}  "
                   f"ssh {s.latency * 1000:4.0f}ms{flag}")
        for cpu, etime, name, detail in s.procs[:nprocs]:
            out.append(f"           {proc_line(cpu, etime, name, detail, w - 11)}")
    return "\n".join(out)


def read_key(timeout: float) -> str:
    """Return one key press ('' when none) without blocking."""
    if not sys.stdin.isatty():
        time.sleep(timeout)
        return ""
    r, _, _ = select.select([sys.stdin], [], [], timeout)
    if not r:
        return ""
    return sys.stdin.read(1)


def main() -> int:
    ap = argparse.ArgumentParser(description="tmux-like 2x3 pane view of the build nodes")
    ap.add_argument("--hosts", default=os.environ.get("DADAO_NODES", ""),
                    help="comma/space separated; default $DADAO_NODES or the six known nodes")
    ap.add_argument("--repo", default=os.environ.get("DADAO_NODE_REPO", "/home/ubuntu/DADAO-v5"))
    ap.add_argument("--procs", type=int, default=0,
                    help="max processes per node; 0 (default) = fill the pane height")
    ap.add_argument("--interval", type=float, default=5.0)
    ap.add_argument("--timeout", type=float, default=6.0)
    ap.add_argument("--layout", choices=("grid", "list"), default="grid")
    ap.add_argument("--once", action="store_true", help="one plain list snapshot, then exit")
    ap.add_argument("--no-color", action="store_true")
    args = ap.parse_args()

    hosts = args.hosts.replace(",", " ").split() or DEFAULT_HOSTS
    color = sys.stdout.isatty() and not args.no_color
    state: dict[str, Sample] = {}

    def snapshot(nprocs: int) -> None:
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(hosts)) as ex:
            futures = {ex.submit(probe, h, args.repo, max(1, nprocs), args.timeout): h
                       for h in hosts}
            for fut in concurrent.futures.as_completed(futures):
                h = futures[fut]
                new = fut.result()
                if new.err and h in state:
                    state[h].err = new.err
                else:
                    state[h] = new

    if args.once:
        w, h = shutil.get_terminal_size((150, 40))
        nlines = args.procs or 20
        snapshot(nlines)
        print(render_list(hosts, state, w, nlines, time.time()))
        return 0 if any(not s.err for s in state.values()) else 1

    pause = False
    tick = 0
    old_term = None
    if sys.stdin.isatty():
        import termios
        import tty
        old_term = termios.tcgetattr(sys.stdin.fileno())
        tty.setcbreak(sys.stdin.fileno())
    try:
        if color:
            sys.stdout.write("\033[?25l")
        while True:
            w, h = shutil.get_terminal_size((150, 44))
            nlines = pane_lines(h, args.procs)
            if not pause:
                tick += 1
                snapshot(nlines)
            if args.layout == "grid":
                body = render_grid(hosts, state, w, h, nlines, color, tick, args.interval)
            else:
                body = render_list(hosts, state, w, nlines, time.time())
            sys.stdout.write("\033[H\033[J" + body + "\n")
            sys.stdout.flush()
            waited = 0.0
            while waited < max(0.2, args.interval):
                key = read_key(0.1)
                waited += 0.1
                if key in ("q", "Q", "\x1b"):
                    raise KeyboardInterrupt
                if key in ("p", "P"):
                    pause = not pause
                if key in ("+", "="):
                    args.interval = max(0.5, args.interval - 0.5)
                if key in ("-", "_"):
                    args.interval = min(60.0, args.interval + 0.5)
                if key:
                    break
    except KeyboardInterrupt:
        pass
    finally:
        if old_term is not None:
            import termios
            termios.tcsetattr(sys.stdin.fileno(), termios.TCSADRAIN, old_term)
        if color:
            sys.stdout.write("\033[?25h\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
