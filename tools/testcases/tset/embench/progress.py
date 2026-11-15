#!/usr/bin/env python3
"""progress.py -- 跑批进度看板（只读；m16-testcases-001）。

回答的是「**为什么看不见中间状态**」：长跑批（chipyard 单例数小时）期间，
主控机只能看到节点日志里**每完成一例就 flush** 的逐例行，以及 `ps` 里
正在跑的 `+loadmem=`。本工具把两者合成一张表，不写节点、不 kill、不改仓库。

数据源（全部只读）
------------------
1. 节点日志的逐例完成行（两种驱动格式都解析）：
   * `run_embench_e2e.py`::

         run_embench_e2e: 19 benchmark(s) x 1 opt level(s) ['O0'] ..., engine=chipyard, work dir ...
           benchmarks: aha-mont64, crc32, ...
           PASS  crc32 (-O0)  expected=0 actual=0 exit=0 cycles=37548594 20544.75s  (match)

   * `picolibc_tests.py`::

         [3/19] test-sin                 pass     cyc=123456    rc=0   ...

2. `ps -eo pid,etime,args` 中带 `+loadmem=<elf>` / `+semiout=` 的进程 ⇒ 在跑用例
   （embench 由 `<work>/<opt>/<bench>/<bench>.elf` 反推；picolibc 由 `<name>.elf`
   反推）；驱动命令行（`--only`）用于日志还是 0 字节时补齐 total。

输出：每批一段表 —— `done`（cycles / 墙钟）、`run`（已跑时长 + ETA）、
`pending`（未开始计数），批尾 `done/total` 与吞吐 `cycles/s`（现场统计，
不写死）。ETA = 该例历史 cycles（无则本批 done 的 cycles 中位数）/ 本批吞吐；
无数据时打 `n/a`，不猜。

只读与失败处理
--------------
* SSH 带 `BatchMode=yes` + `ConnectTimeout`，整条命令受 `--timeout`（默认 15 s）
  约束；某节点失败只标 `UNREACHABLE`，其余节点照常出表；
* 不写节点、不 kill、不 sync/reset、不改仓库；
* `--expect-done N` 把「解析出的 done 总数」与外部计数交叉校验（解析少算一例
  ⇒ rc=1）；批内 `done+run > total` 同样判错（防解析重复计数）。

退出码：0 = 全部节点取到且交叉校验通过；1 = 交叉校验失败 / 有节点失败；
2 = 用法错误 / 全部节点失败。
"""
from __future__ import annotations

import argparse
import re
import shlex
import statistics
import subprocess
import sys
import time

DEFAULT_PATTERNS = "*embench*.log,*picolibc*.log"
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=5",
            "-o", "ServerAliveInterval=5"]
LOG_SCAN_ROOT = ".work/log"
LOG_TAIL_BYTES = 524288

RE_EMB_HDR = re.compile(
    r"^run_embench_e2e: (\d+) benchmark\(s\) x (\d+) opt level\(s\) "
    r"\[(.*?)\].*?engine=(\w+)", re.M)
RE_EMB_BENCHES = re.compile(r"^  benchmarks: (.*)$", re.M)
RE_EMB_CASE = re.compile(
    r"^\s+(PASS|FAIL|TIMEOUT|BLOCKED|GUARD|ERROR)\s+(\S+)\s+\(-(\w+)\)\s+"
    r"expected=(\S+)\s+actual=(\S+)\s+exit=(\S+)"
    r"(?:\s+cycles=(\S+)\s+([\d.]+)s)?\s+\((.*)\)\s*$", re.M)
RE_EMB_DONE = re.compile(r"^run_embench_e2e: (PASS|FAIL)\s*$", re.M)

RE_PICO_CASE = re.compile(
    r"^\s+\[(\d+)/(\d+)\]\s+(\S+)\s+(pass|fail|excluded|blocked|skipped)\s+"
    r"cyc=(\S+)\s+rc=(\S+)\s*(.*)$", re.M)
RE_PICO_SUM = re.compile(
    r"^picolibc-tests: stage=\S+ engine=(\S+) total=(\d+) pass=\d+ fail=\d+ "
    r"excluded=\d+ blocked=\d+ skipped=\d+\s*$", re.M)
RE_ONLY = re.compile(r"--only[ =]([^ ]+)")
RE_REDIRECT = re.compile(r">\s*(\S+\.log)")

RE_LOADMEM = re.compile(r"\+loadmem=(\S+)")
RE_SEMIOUT = re.compile(r"\+semiout=(\S+)")
RE_EMB_ELF = re.compile(r"/(m6-embench|embench)/([^/]+)/([^/]+)/[^/]*\.elf$")
RE_EMB_SEMI = re.compile(r"/(m6-embench|embench)/([^/]+)/([^/]+)/semi\.out$")
RE_PICO_SEMI = re.compile(r"/run/([^/]+)/semi\.out$")


def _hms(value: str) -> int:
    parts = [int(p) for p in value.split(":")]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    raise ValueError(value)


def parse_etime(value: str) -> int:
    """``ps etime`` -> seconds: ``[[DD-]HH:]MM:SS``."""
    if "-" in value:
        days, rest = value.split("-", 1)
        return int(days) * 86400 + _hms(rest)
    return _hms(value)


def fmt_dur(seconds) -> str:
    if seconds is None:
        return "n/a"
    total = int(round(seconds))
    hours, rem = divmod(total, 3600)
    minutes, secs = divmod(rem, 60)
    if hours:
        return "%dh%02dm" % (hours, minutes)
    if minutes:
        return "%dm%02ds" % (minutes, secs)
    return "%ds" % secs


def _num(text):
    if text is None or text in ("-", "?", "None"):
        return None
    try:
        return int(text)
    except ValueError:
        return None


def _batch(host, path, mtime, kind):
    return {"host": host, "path": path, "mtime": mtime, "kind": kind,
            "engine": None, "total": None, "expected": set(), "cases": {},
            "complete": False, "running": [], "bytes": 0}


def parse_embench(host, path, mtime, text):
    batch = _batch(host, path, mtime, "embench")
    batch["bytes"] = len(text)
    m = RE_EMB_HDR.search(text)
    args = None
    if m:
        n_bench, n_opt, opts_text, engine = m.groups()
        batch["engine"] = engine
        args = [o.strip().strip("'\"") for o in opts_text.split(",") if o.strip()]
        mb = RE_EMB_BENCHES.search(text)
        benches = ([b.strip() for b in mb.group(1).split(",") if b.strip()]
                   if mb else [])
        batch["expected"] = {(b, o) for b in benches for o in args}
        if benches and args:
            batch["total"] = len(benches) * len(args)
    for m in RE_EMB_CASE.finditer(text):
        status, bench, opt, _exp, _act, _exit, cycles, secs, reason = m.groups()
        batch["cases"][(bench, opt)] = {
            "name": bench, "opt": opt, "status": status,
            "cycles": _num(cycles),
            "seconds": float(secs) if secs else None,
            "reason": reason,
        }
    batch["complete"] = bool(RE_EMB_DONE.search(text))
    return batch


def parse_picolibc(host, path, mtime, text):
    batch = _batch(host, path, mtime, "picolibc")
    batch["bytes"] = len(text)
    total = None
    for m in RE_PICO_CASE.finditer(text):
        _done, denom, name, status, cyc, _rc, reason = m.groups()
        total = max(total or 0, int(denom))
        batch["cases"][name] = {
            "name": name, "opt": None, "status": status,
            "cycles": _num(cyc), "seconds": None, "reason": reason.strip(),
        }
    ms = RE_PICO_SUM.search(text)
    if ms:
        batch["engine"] = ms.group(1)
        total = int(ms.group(2))
        batch["complete"] = True
    batch["total"] = total
    return batch


def classify_log(host, path, mtime, text):
    base = path.rsplit("/", 1)[-1]
    if RE_EMB_HDR.search(text) or "run_embench_e2e:" in text:
        return parse_embench(host, path, mtime, text)
    if "picolibc-tests:" in text:
        return parse_picolibc(host, path, mtime, text)
    if "picolibc" in base:
        return parse_picolibc(host, path, mtime, text)
    return parse_embench(host, path, mtime, text)


def parse_ps(text):
    """Return (running, drivers) from ``ps -eo pid,etime,args`` output."""
    running, drivers = [], []
    for line in text.splitlines():
        parts = line.split(None, 2)
        if len(parts) < 3 or not parts[0].isdigit():
            continue
        pid, etime, cmd = parts
        if "+loadmem=" in cmd:
            m = RE_LOADMEM.search(cmd)
            if not m:
                continue
            elf = m.group(1)
            semi = RE_SEMIOUT.search(cmd)
            running.append({
                "pid": pid, "etime": etime, "elapsed": parse_etime(etime),
                "elf": elf, "semiout": semi.group(1) if semi else None,
                "kind": None, "name": None, "opt": None,
            })
        elif "run_embench_e2e.py" in cmd or "picolibc_tests.py" in cmd:
            mo = RE_ONLY.search(cmd)
            mr = RE_REDIRECT.search(cmd)
            drivers.append({
                "pid": pid, "etime": etime, "cmd": cmd,
                "only": ([n for n in mo.group(1).split(",") if n] if mo else None),
                "log": mr.group(1) if mr else None,
            })
    for run in running:
        semi = run["semiout"]
        m = RE_EMB_ELF.search(run["elf"]) or (RE_EMB_SEMI.search(semi)
                                             if semi else None)
        if m:
            run["kind"], run["opt"], run["name"] = "embench", m.group(2), m.group(3)
        elif "picolibc" in run["elf"]:
            run["kind"] = "picolibc"
            run["name"] = run["elf"].rsplit("/", 1)[-1][:-4]
        elif semi and "picolibc" in semi:
            ms = RE_PICO_SEMI.search(semi)
            if ms:
                run["kind"], run["name"] = "picolibc", ms.group(1)
    return [r for r in running if r["kind"]], drivers


def _remote_script(repo: str, patterns) -> str:
    if repo.startswith("~/"):
        repo_expr = '"$HOME"/' + shlex.quote(repo[2:])
    else:
        repo_expr = shlex.quote(repo)
    terms = " -o ".join("-name %s" % shlex.quote(p) for p in patterns)
    return (
        "repo=%s\n"
        'cd "$repo" 2>/dev/null || { echo "###REPO_MISSING"; exit 2; }\n'
        'echo "###PS"\n'
        "ps -eo pid,etime,args\n"
        'echo "###LOGS"\n'
        "find %s -maxdepth 4 -type f \\( %s \\) -print 2>/dev/null | sort | "
        'while IFS= read -r f; do\n'
        '  echo "###LOG $f $(stat -c %%Y "$f" 2>/dev/null || echo 0)"\n'
        '  tail -c %d "$f" 2>/dev/null\n'
        "  echo\n"
        "done\n"
    ) % (repo_expr, LOG_SCAN_ROOT, terms, LOG_TAIL_BYTES)


def fetch(host: str, repo: str, patterns, timeout: int):
    """Run the read-only probe on one host; return (rc, ps_text, logs, err)."""
    script = _remote_script(repo, patterns)
    cmd = (["bash", "-c", script] if host == "local"
           else ["ssh"] + SSH_OPTS + [host, "bash -c " + shlex.quote(script)])
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, "", [], "timeout after %ds" % timeout
    out = proc.stdout.decode("utf-8", "replace")
    err = proc.stderr.decode("utf-8", "replace").strip()
    if proc.returncode != 0:
        return proc.returncode, "", [], err or "ssh rc=%d" % proc.returncode
    ps_lines, logs, cur, section = [], [], None, None
    for line in out.splitlines():
        if line == "###PS":
            section = "ps"
        elif line == "###LOGS":
            section = None
        elif line.startswith("###LOG "):
            parts = line.split()
            cur = {"path": parts[1] if len(parts) > 1 else "?",
                   "mtime": int(parts[2]) if len(parts) > 2 else 0,
                   "lines": []}
            logs.append(cur)
            section = "log"
        elif line == "###REPO_MISSING":
            return 2, "", [], "repo not found on host"
        elif section == "ps":
            ps_lines.append(line)
        elif section == "log" and cur is not None:
            cur["lines"].append(line)
    return 0, "\n".join(ps_lines), logs, None


def _attach_running(batches, running, drivers, host):
    unlogged = {}
    for run in running:
        target = None
        for batch in sorted(batches, key=lambda b: b["mtime"], reverse=True):
            if batch["kind"] != run["kind"] or batch["complete"]:
                continue
            if run["kind"] == "embench":
                key = (run["name"], run["opt"])
                if key in batch["cases"]:
                    continue
                if batch["expected"] and key not in batch["expected"]:
                    continue
            else:
                if run["name"] in batch["cases"]:
                    continue
                only = _pico_only_for(drivers, batch)
                # picolibc 的归属必须有证据：驱动 --only 点名，或该批已有
                # 逐例完成行（同一批的后续用例）。一个早先被停掉、0 用例的
                # 旧日志不得把无关的孤儿 sim 算到自己头上。
                if only:
                    if run["name"] not in only:
                        continue
                elif not batch["cases"]:
                    continue
            if batch["total"] is not None and (
                    len(batch["cases"]) + len(batch["running"]) >= batch["total"]):
                continue
            target = batch
            break
        if target is None:
            key = (host, run["kind"])
            target = unlogged.setdefault(key, _batch(
                host, "(unlogged)", 0, run["kind"]))
            target["total"] = None
        target["running"].append(run)
    return list(unlogged.values())


def _pico_only_for(drivers, batch):
    stem = batch["path"].rsplit("/", 1)[-1][:-4]
    for drv in drivers:
        only = drv.get("only")
        if not only:
            continue
        hint = drv.get("log")
        if hint and hint.rsplit("/", 1)[-1][:-4] != stem:
            continue
        if any(stem.endswith(n) or (n.startswith("test-") and stem.endswith(n[5:]))
               for n in only):
            return set(only)
    return None


def _fill_totals_from_drivers(batch, drivers):
    if batch["total"] is not None or batch["cases"]:
        return
    only = _pico_only_for(drivers, batch)
    if only:
        batch["total"] = len(only)


def _driver_alive(batch, drivers):
    """True when a driver for this batch is still alive (between cases)."""
    stem = batch["path"].rsplit("/", 1)[-1][:-4]
    for drv in drivers:
        kind = ("embench" if "run_embench_e2e.py" in drv["cmd"]
                else "picolibc" if "picolibc_tests.py" in drv["cmd"] else None)
        if kind != batch["kind"]:
            continue
        hint = drv.get("log")
        if hint is None:
            return True
        if hint.rsplit("/", 1)[-1][:-4] == stem:
            return True
    return False


def _median(values):
    vals = [v for v in values if v is not None]
    return statistics.median(vals) if vals else None


def _history(all_batches):
    hist = {}
    for batch in sorted(all_batches, key=lambda b: b["mtime"]):
        for key, case in batch["cases"].items():
            hkey = (batch["kind"],) + (key if isinstance(key, tuple) else (key,))
            hist[hkey] = case
    return hist


def _eta(batch, run, history):
    if run["kind"] == "embench":
        hkey = ("embench", run["name"], run["opt"])
    else:
        hkey = ("picolibc", run["name"])
    hist = history.get(hkey)
    done = list(batch["cases"].values())
    tgt = hist.get("cycles") if hist else None
    if tgt is None:
        tgt = _median([c["cycles"] for c in done])
    cyc = [c["cycles"] for c in done if c["cycles"] is not None]
    secs = [c["seconds"] for c in done if c["seconds"] is not None]
    rate = (sum(cyc) / sum(secs)) if cyc and secs and sum(secs) > 0 else None
    if tgt and rate:
        return tgt / rate - run["elapsed"]
    if hist and hist["status"] == "PASS" and hist.get("seconds"):
        return hist["seconds"] - run["elapsed"]
    return None


def _fmt_eta(seconds) -> str:
    if seconds is None:
        return "n/a"
    if seconds <= 0:
        return "overdue"
    return fmt_dur(seconds)


def _throughput(batch):
    cyc = [c["cycles"] for c in batch["cases"].values()
           if c["cycles"] is not None]
    secs = [c["seconds"] for c in batch["cases"].values()
            if c["seconds"] is not None]
    if not cyc or not secs or sum(secs) <= 0:
        return None
    return sum(cyc) / sum(secs)


def _case_label(batch, case):
    if batch["kind"] == "embench":
        return "%s (-%s)" % (case["name"], case["opt"])
    return case["name"]


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Read-only Embench/picolibc batch progress board")
    ap.add_argument("--hosts", default=None,
                    help="comma-separated node list (e.g. server208,ics170); "
                         "omit with --local")
    ap.add_argument("--local", action="store_true",
                    help="probe this machine instead of ssh (self-test)")
    ap.add_argument("--repo", default="~/DADAO-v5",
                    help="repository root on each node (default ~/DADAO-v5)")
    ap.add_argument("--logs", default=DEFAULT_PATTERNS,
                    help="comma-separated glob patterns for log basenames "
                         "(default %s)" % DEFAULT_PATTERNS)
    ap.add_argument("--window", type=int, default=180,
                    help="a *finished* log is shown only if modified within N "
                         "minutes (unfinished logs always shown; default 180)")
    ap.add_argument("--timeout", type=int, default=15,
                    help="bound for one host probe, seconds (default 15)")
    ap.add_argument("--expect-done", type=int, default=None,
                    help="cross-check: parsed done total must equal N (rc=1 "
                         "otherwise); use in evidence to catch a parser that "
                         "silently drops a completed case")
    args = ap.parse_args(argv)

    if args.local:
        hosts = ["local"]
    elif args.hosts:
        hosts = [h.strip() for h in args.hosts.split(",") if h.strip()]
    else:
        ap.error("--hosts is required unless --local")
    patterns = [p.strip() for p in args.logs.split(",") if p.strip()]
    if not patterns:
        ap.error("--logs must name at least one glob")

    now = time.time()
    all_batches, host_errors, host_running = [], [], {}
    for host in hosts:
        rc, ps_text, logs, err = fetch(host, args.repo, patterns, args.timeout)
        if rc != 0:
            host_errors.append((host, rc, err))
            print("[%s] UNREACHABLE: %s" % (host, err or "rc=%s" % rc))
            continue
        running, drivers = parse_ps(ps_text)
        host_batches = []
        for entry in logs:
            text = "\n".join(entry["lines"])
            batch = classify_log(host, entry["path"], entry["mtime"], text)
            _fill_totals_from_drivers(batch, drivers)
            host_batches.append(batch)
        host_running[host] = (running, drivers)
        all_batches.extend(host_batches)

    history = _history(all_batches)
    done_total = 0
    known_total = 0
    unknown_total = 0
    running_known = 0
    inconsistent = []
    for host in hosts:
        if host not in host_running:
            continue
        running, drivers = host_running[host]
        host_batches = [b for b in all_batches if b["host"] == host]
        candidates = [b for b in host_batches
                      if not b["complete"]
                      or (now - b["mtime"]) <= args.window * 60]
        unlogged = _attach_running(candidates, running, drivers, host)
        shown = [b for b in candidates
                 if b["cases"] or b["running"]
                 or ((b["bytes"] or b["complete"])
                     and (now - b["mtime"]) <= args.window * 60)] + unlogged
        print("\n== %s (%d active batch, %d running case) =="
              % (host, len(shown), len(running)))
        if not shown:
            print("  (no matching log and no +loadmem process)")
            continue
        for batch in sorted(shown, key=lambda b: b["mtime"], reverse=True):
            done = list(batch["cases"].values())
            n_run = len(batch["running"])
            total = batch["total"]
            pending = (total - len(done) - n_run) if total is not None else None
            if total is not None and pending < 0:
                inconsistent.append((host, batch["path"], len(done), n_run, total))
            rate = _throughput(batch)
            state = ("complete" if batch["complete"]
                     else "running" if n_run
                     else "driver" if _driver_alive(batch, drivers)
                     else "stopped")
            print("  batch %s  [%s%s]  done=%d%s running=%d%s"
                  % (batch["path"].replace("./", "", 1),
                     batch["kind"],
                     ", engine=" + batch["engine"] if batch["engine"] else "",
                     len(done),
                     "/%d" % total if total is not None else "/n/a",
                     n_run,
                     "  pending=%d" % pending if pending is not None
                     else "  pending=n/a"))
            print("    throughput: %s  state=%s mtime=%s"
                  % ("%.0f cycles/s" % rate if rate else "n/a", state,
                     time.strftime("%Y-%m-%dT%H:%M:%S",
                                   time.localtime(batch["mtime"]))
                     if batch["mtime"] else "-"))
            print("    %-5s %-30s %12s %10s %9s %8s"
                  % ("state", "case", "cycles", "wall", "elapsed", "eta"))
            for case in done:
                print("    %-5s %-30s %12s %10s %9s %8s"
                      % (case["status"], _case_label(batch, case),
                         case["cycles"] if case["cycles"] is not None else "-",
                         ("%ss" % case["seconds"]) if case["seconds"] is not None
                         else "-", "-", "-"))
            for run in batch["running"]:
                eta = _eta(batch, run, history)
                print("    %-5s %-30s %12s %10s %9s %8s"
                      % ("run",
                         ("%s (-%s)" % (run["name"], run["opt"])
                          if run["kind"] == "embench" else run["name"]),
                         "-", "-", fmt_dur(run["elapsed"]), _fmt_eta(eta)))
            done_total += len(done)
            if total is not None:
                known_total += total
                running_known += n_run
            else:
                unknown_total += 1

    pending_known = max(0, known_total - done_total - running_known)
    print("\nprogress: done=%d total=%s pending=%d running=%d "
          "unknown-total-batch=%d"
          % (done_total, known_total if known_total else "n/a",
             pending_known,
             sum(len(r) for r, _d in host_running.values()), unknown_total))
    print("progress: throughput per batch above (cycles/s, live counts; "
          "no hard-coded totals)")

    failed = False
    if inconsistent:
        for host, path, nd, nr, total in inconsistent:
            print("ERROR: %s %s parsed done=%d run=%d > total=%d"
                  % (host, path, nd, nr, total))
        failed = True
    if args.expect_done is not None and done_total != args.expect_done:
        print("ERROR: --expect-done %d but parsed done=%d"
              % (args.expect_done, done_total))
        failed = True
    if host_errors:
        failed = True
    if host_errors and len(host_errors) == len(hosts):
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
