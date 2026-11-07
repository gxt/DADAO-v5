#!/usr/bin/env python3
"""Fan out read-only orchestration commands to a list of build nodes.

Subcommands
-----------
``status``     git commit / worktree dirtiness, toolchain versions, free disk
               and memory, one block per node.
``preflight``  per-node gate readiness: clang/llc/ld.lld present, ``.cache``
               non-empty, every enabled component at ``base + expected patch
               commits`` with a clean worktree.  Prints PASS/FAIL per item.
``run``        run one read-only or idempotent command on every node (for
               example ``run -- make check``); one log per node.
``collect``    copy a directory from every node into a local per-host subtree.

Node inventory
--------------
There is deliberately no built-in node list: ``--hosts a,b`` wins, then the
``DADAO_NODES`` environment variable; with neither the command fails and says
how to supply it.  Every transport uses ``ssh -o BatchMode=yes`` so a missing
key fails loudly instead of prompting.  ``--local`` skips ssh and runs the
same scripts on this host (self-test only); node labels still come from
``--hosts``.

``--repo`` may start with ``~/``: it is expanded against the *remote* ``$HOME``
(quoting a path would stop the shell from expanding it).  If the directory can
not be entered the node fails with rc=2 and no status lines are printed - a
node whose repository is missing must never look like a clean node.

Exit status is 0 only when every node succeeded; the final summary always
prints ``host -> rc``.

Log file names are ``<task-id>-<subcommand>-<host>.log`` under
``.work/log/infra/<task-id>/remote/`` (host sanitised).  ``--log-prefix`` names
the *dispatching task* (default ``INFRA-130t``, the task that introduced this
tool); it must be a task id, because ``check-run-artifacts`` rejects any other
shape -- a tool-name prefix such as ``remote-`` would turn L1 red.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SSH_BASE = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10"]

# Log-file names must satisfy `check-run-artifacts` (`<TASK-ID>-<purpose>.log`),
# so the prefix is a *task id*, not a tool name: name the logs after the task
# dispatching the run.  The pattern is imported from the gate so the two cannot
# drift; `DEFAULT_LOG_PREFIX` is only the fallback for ad-hoc runs.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_run_artifacts import TASK_ID as _TASK_ID_RE  # noqa: E402  (gate is the single source)

DEFAULT_LOG_PREFIX = "INFRA-130t"

STATUS_SCRIPT = r"""set -u
if ! commit="$(git rev-parse HEAD 2>&1)"; then
  printf 'commit=MISSING\n'
  printf 'commit_error=%s\n' "$commit"
  exit 2
fi
printf 'commit=%s\n' "$commit"
if ! dirty="$(git status --porcelain 2>/dev/null)"; then
  printf 'worktree=UNKNOWN\n'
  printf 'dirty_files=UNKNOWN\n'
  printf 'status_error=git status failed\n'
  exit 2
fi
if [ -n "$dirty" ]; then printf 'worktree=dirty\n'; else printf 'worktree=clean\n'; fi
files=0
if [ -n "$dirty" ]; then files=$(printf '%s\n' "$dirty" | wc -l | tr -d ' '); fi
printf 'dirty_files=%s\n' "$files"
bin="$(python3 tools/infra/paths.py host_toolchain_bin 2>/dev/null || true)"
if [ -n "$bin" ] && [ -x "$bin/clang" ]; then
  printf 'clang=%s\n' "$("$bin/clang" --version 2>&1 | head -n1)"
else
  printf 'clang=MISSING\n'
fi
if [ -n "$bin" ] && [ -x "$bin/qemu-dadao" ]; then
  printf 'qemu=%s\n' "$("$bin/qemu-dadao" --version 2>&1 | head -n1)"
else
  printf 'qemu=MISSING\n'
fi
printf 'disk_avail_kb=%s\n' "$(df -Pk . 2>/dev/null | awk 'NR==2{print $4}')"
printf 'mem_avail_mb=%s\n' "$(free -m 2>/dev/null | awk '/^Mem:/{print $7}')"
printf 'mem_total_mb=%s\n' "$(free -m 2>/dev/null | awk '/^Mem:/{print $2}')"
exit 0
"""

PREFLIGHT_SCRIPT = r"""set -u
fail=0
bin="$(python3 tools/infra/paths.py host_toolchain_bin 2>/dev/null || true)"
for tool in clang llc ld.lld; do
  if [ -n "$bin" ] && [ -x "$bin/$tool" ]; then
    printf 'PASS tool:%s\n' "$tool"
  else
    printf 'FAIL tool:%s missing\n' "$tool"
    fail=1
  fi
done
entries="$(ls -A .cache 2>/dev/null | wc -l | tr -d ' ')"
if [ "${entries:-0}" -gt 0 ]; then
  printf 'PASS cache:entries=%s\n' "$entries"
else
  printf 'FAIL cache:empty or missing\n'
  fail=1
fi
python3 - <<'PY'
import subprocess
import sys
import tomllib
from pathlib import Path

bad = 0
try:
    manifest = tomllib.loads(Path("manifests/components.lock.toml").read_text())
except Exception as exc:  # noqa: BLE001 - report and fail, never fake a PASS
    print(f"FAIL manifest:{exc}")
    sys.exit(1)

for comp in manifest.get("component", []):
    if not comp.get("enabled"):
        continue
    name = comp["name"]
    base = comp.get("commit", "")
    src = Path(".work/source") / name
    if not (src / ".git").exists():
        print(f"FAIL source:{name} missing")
        bad += 1
        continue
    head = subprocess.run(
        ["git", "-C", str(src), "rev-parse", "HEAD"],
        capture_output=True, text=True,
    ).stdout.strip()
    dirty = subprocess.run(
        ["git", "-C", str(src), "status", "--porcelain"],
        capture_output=True, text=True,
    ).stdout.strip()
    count = subprocess.run(
        ["git", "-C", str(src), "rev-list", "--count", f"{base}..HEAD"],
        capture_output=True, text=True,
    )
    commits = int(count.stdout.strip()) if count.returncode == 0 and count.stdout.strip() else -1
    series = comp.get("patch_series")
    expected = 0
    if series:
        path = Path(series)
        if path.exists():
            lines = [line for line in path.read_text().splitlines() if line.strip() and not line.lstrip().startswith("#")]
            expected = 1 if lines else 0
    ok = commits == expected and not dirty
    print(
        f"{'PASS' if ok else 'FAIL'} source:{name} head={head[:12]} "
        f"commits_since_base={commits} expected={expected} dirty={len(dirty.splitlines())}"
    )
    if not ok:
        bad += 1

sys.exit(1 if bad else 0)
PY
rc=$?
[ "$rc" -eq 0 ] || fail=1
exit "$fail"
"""


def safe_name(host: str) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]", "_", host)


def fail(message: str, rc: int = 2) -> None:
    print(f"remote.py: ERROR: {message}", file=sys.stderr)
    raise SystemExit(rc)


def resolve_hosts(args: argparse.Namespace) -> list[str]:
    raw = args.hosts if args.hosts else os.environ.get("DADAO_NODES", "")
    hosts: list[str] = []
    for token in re.split(r"[,\s]+", raw or ""):
        if token and token not in hosts:
            hosts.append(token)
    if not hosts:
        fail(
            "no nodes given; pass --hosts a,b (or set DADAO_NODES). "
            "There is no built-in node list."
        )
    for host in hosts:
        if host.startswith("-"):
            fail(f"refusing host that looks like an option: {host}")
    return hosts


def require_repo(args: argparse.Namespace) -> str:
    if not args.repo:
        fail("--repo PATH is required (the remote checkout to run in)")
    return args.repo


def log_prefix(args: argparse.Namespace) -> str:
    prefix = args.log_prefix or DEFAULT_LOG_PREFIX
    if not re.fullmatch(_TASK_ID_RE, prefix):
        fail(
            f"--log-prefix must be a task id matching {_TASK_ID_RE} "
            f"(got {prefix!r}); check-run-artifacts rejects any other log name"
        )
    return prefix


def log_root(args: argparse.Namespace) -> Path:
    root = Path(args.log_dir) if args.log_dir else Path(".work/log/infra") / log_prefix(args) / "remote"
    return root if root.is_absolute() else REPO_ROOT / root


def quote_remote_path(path: str) -> str:
    """Quote *path* for a remote shell, expanding a leading ``~/`` correctly.

    ``shlex.quote`` protects the path but also neutralises a leading ``~``, so
    the shell would look for a literal directory named ``~``.  A path starting
    with ``~/`` is therefore rebuilt as ``"$HOME"/rest``; other ``~user`` forms
    are rejected instead of silently mis-expanding.
    """
    if path == "~":
        return '"$HOME"'
    if path.startswith("~/"):
        rest = path[2:]
        return '"$HOME"/' + (shlex.quote(rest) if rest else '""')
    if path.startswith("~"):
        fail(f"only '~/' (or '~') is supported for remote paths, got {path!r}")
    return shlex.quote(path)


def enter_repo(repo: str) -> str:
    """Return a preamble that enters *repo* or aborts the whole script.

    A plain ``cd PATH && <multi-line script>`` only guards the first line: the
    remaining lines still run and the final command decides the exit status,
    which turns a missing repository into a fake PASS.
    """
    return (
        f"repo_dir={quote_remote_path(repo)}\n"
        'if ! CDPATH= cd "$repo_dir"; then\n'
        "  printf 'remote.py: repository not found: %s\\n' \"$repo_dir\" >&2\n"
        "  exit 2\n"
        "fi\n"
        "unset repo_dir\n"
    )


def build_shell(args: argparse.Namespace, host: str, script: str) -> list[str]:
    """Return the argv that runs *script* on one node."""
    payload = enter_repo(args.repo) + script
    if args.local:
        return ["bash", "-c", payload]
    return [*SSH_BASE, *args.ssh_arg, host, payload]


def run_node(args: argparse.Namespace, host: str, script: str, *, binary: bool = False) -> subprocess.CompletedProcess:
    argv = build_shell(args, host, script)
    if binary:
        return subprocess.run(argv, capture_output=True)
    return subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", errors="replace")


def write_log(path: Path, host: str, rc: int, stdout, stderr) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    body = f"# host: {host}\n# rc: {rc}\n--- stdout ---\n{stdout}\n--- stderr ---\n{stderr}\n"
    path.write_text(body, errors="replace")
    return path


def parallel(args: argparse.Namespace, fn):
    hosts = args.resolved_hosts
    workers = max(1, min(args.jobs, len(hosts)))
    results: dict[str, tuple[int, object]] = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(fn, host): host for host in hosts}
        for future in concurrent.futures.as_completed(futures):
            host = futures[future]
            results[host] = future.result()
    return [(host, *results[host]) for host in hosts]


def summarize(rows) -> int:
    print("host -> rc")
    worst = 0
    for host, rc, extra in rows:
        verdict = "PASS" if rc == 0 else "FAIL"
        print(f"  {host} -> {rc} ({verdict})")
        if rc != 0:
            worst = 1
    print(f"overall rc={worst}")
    return worst


def node_script(args: argparse.Namespace) -> str:
    return {
        "status": STATUS_SCRIPT,
        "preflight": PREFLIGHT_SCRIPT,
    }[args.subcommand]


def command_status(args: argparse.Namespace) -> int:
    script = node_script(args)

    def one(host: str):
        try:
            proc = run_node(args, host, script)
        except OSError as exc:
            path = log_root(args) / f"{log_prefix(args)}-{args.subcommand}-{safe_name(host)}.log"
            write_log(path, host, 127, "", f"{type(exc).__name__}: {exc}")
            return 127, path
        path = write_log(log_root(args) / f"{log_prefix(args)}-{args.subcommand}-{safe_name(host)}.log", host, proc.returncode, proc.stdout, proc.stderr)
        return proc.returncode, path

    rows = parallel(args, one)
    for host, rc, path in rows:
        print(f"=== {host} (rc={rc}, log={path}) ===")
        print(path.read_text(errors="replace"), end="")
    return summarize(rows)


def command_run(args: argparse.Namespace) -> int:
    command = list(args.cmd)
    if command and command[0] == "--":
        command = command[1:]
    if not command:
        fail("run needs a command, e.g. remote.py run --hosts a,b --repo PATH -- make check")
    script = shlex.join(command)

    def one(host: str):
        try:
            proc = run_node(args, host, script)
        except OSError as exc:
            path = log_root(args) / f"{log_prefix(args)}-run-{safe_name(host)}.log"
            write_log(path, host, 127, "", f"{type(exc).__name__}: {exc}")
            return 127, path
        path = write_log(log_root(args) / f"{log_prefix(args)}-run-{safe_name(host)}.log", host, proc.returncode, proc.stdout, proc.stderr)
        return proc.returncode, path

    rows = parallel(args, one)
    for host, rc, path in rows:
        print(f"=== {host} rc={rc} log={path} ===")
    return summarize(rows)


def command_collect(args: argparse.Namespace) -> int:
    dest_root = Path(args.dest_dir)
    if not dest_root.is_absolute():
        dest_root = REPO_ROOT / dest_root
    script = (
        f"remote_dir={quote_remote_path(args.remote_dir)}\n"
        'if [ ! -d "$remote_dir" ]; then\n'
        "  printf 'collect: remote directory not found: %s\\n' \"$remote_dir\" >&2\n"
        "  exit 2\n"
        "fi\n"
        'tar -C "$remote_dir" -czf - .'
    )

    def one(host: str):
        log = log_root(args) / f"{log_prefix(args)}-collect-{safe_name(host)}.log"
        try:
            proc = run_node(args, host, script, binary=True)
        except OSError as exc:
            write_log(log, host, 127, "", f"{type(exc).__name__}: {exc}")
            return 127, log
        if proc.returncode != 0:
            write_log(log, host, proc.returncode, "", proc.stderr.decode(errors="replace"))
            return proc.returncode, log
        target = dest_root / safe_name(host)
        target.mkdir(parents=True, exist_ok=True)
        extract = subprocess.run(["tar", "-C", str(target), "-xzf", "-"], input=proc.stdout, capture_output=True)
        write_log(log, host, extract.returncode, "", extract.stderr.decode(errors="replace"))
        return extract.returncode, log

    rows = parallel(args, one)
    for host, rc, path in rows:
        print(f"=== {host} rc={rc} log={path} ===")
    return summarize(rows)


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--hosts", help="comma/space separated node list (default: $DADAO_NODES)")
    common.add_argument("--repo", default="", help="remote repository path (required; a leading ~/ is expanded on the node)")
    common.add_argument("--log-dir", default="", help="local log directory (default: .work/log/infra/<log-prefix>/remote)")
    common.add_argument("--log-prefix", default=DEFAULT_LOG_PREFIX, help=f"task id used in log file names (default: {DEFAULT_LOG_PREFIX}; must match {_TASK_ID_RE})")
    common.add_argument("--jobs", type=int, default=8, help="parallel nodes (default: 8)")
    common.add_argument("--local", action="store_true", help="run on this host instead of ssh (self-test only)")
    common.add_argument("--ssh-arg", action="append", default=[], metavar="ARG", help="extra ssh option (repeatable)")

    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="subcommand", required=True)

    status = sub.add_parser("status", parents=[common], help="report node state")
    status.set_defaults(func=command_status)

    preflight = sub.add_parser("preflight", parents=[common], help="check gate prerequisites")
    preflight.set_defaults(func=command_status)

    run = sub.add_parser("run", parents=[common], help="run one command on every node")
    run.add_argument("cmd", nargs=argparse.REMAINDER, help="command after --, e.g. -- make check")
    run.set_defaults(func=command_run)

    collect = sub.add_parser("collect", parents=[common], help="fetch a remote directory")
    collect.add_argument("--remote-dir", required=True, help="remote directory to copy (a leading ~/ is expanded on the node)")
    collect.add_argument("--dest-dir", required=True, help="local destination root (one subdirectory per host)")
    collect.set_defaults(func=command_collect)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.resolved_hosts = resolve_hosts(args)
    require_repo(args)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
