#!/usr/bin/env python3
"""check_k6.py — M18 K6 closure gate (`make check-linux-k6`; `m18-linux-003`).

K6 is where the machine runs a *program the user recognises*: the kernel hands
PID 1 to the initramfs `/init`, which execs busybox's `sh` on the semihosting
console, and that shell runs commands and returns their exit codes.  The stage
question this gate asks is "does the delivered K6 image still start the shell
and run its representative commands end to end?" — with **representative**
cases only (the full applet sweeps stay in the K6 evidence scripts).

Groups (the group letter is what ``--selfcheck``/``--inject`` flip):

  S  startup: the image builds with the K6 symbol on and every probe off, the
     initramfs ships the generator's `/init` (byte-derived marker + prompt),
     the shipped `bin/busybox` is the build product (manifest sha256), the
     shell banner appears once, and `/init` is what the kernel execs.
  C  commands: the shell runs the five representative commands (echo, mkdir,
     cat, ls, rm) with the correct output and exit status, including the
     failure arms (`mkdir` on an existing path, `rm` on a missing one) and the
     `mkdir -> write -> ls -> rm -> ls` filesystem effect.
  E  exit: the script's final `exit N` is the QEMU process status, and the
     shell's last prompt line is that command (PID 1's exit is the session end).
  R  reverse assertions and the §4a retirement: no named termination, no
     `unknown cause`, no panic/oops, no probe owned by the image, no `-d`; the
     `Makefile` wires the gate into PHONY / the lock / L2 / help, and the §4a.3
     record names every audited item (new wording in, retired wording out,
     replacement pointer present).

Every expectation is derived, never restated:

  * `/init` marker, prompt, `exec /bin/sh` -> ``tools/linux/make_initramfs.py``
                                              (the generator's own constants)
  * applet links / busybox sha256           -> the built ``manifest.json`` and
                                              the build product on disk
  * command names / output / rc             -> ``COMMANDS`` below (the script
                                              this gate feeds and judges)
  * final exit status                       -> the script's own ``exit N``
  * image symbol values                     -> the image's ``.config``
  * retirement anchors                      -> the files named in §4a.3

Exit status: 0 = every check passed; 1 = at least one FAIL; 2 = an input could
not be derived (generator / build tree / toolchain missing).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

_REPO = Path(__file__).resolve().parents[3]
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from tools.linux import config_pins as pins                   # noqa: E402
from tools.linux import make_defconfig as defconfig          # noqa: E402
from tools.linux import make_initramfs as initramfs          # noqa: E402
from tools.linux import paths as linux_paths                 # noqa: E402
from tools.qemu import k0_boot_probe as k0                   # noqa: E402

JOBS = os.environ.get("JOBS", "32")
TIMEOUT_QEMU = int(os.environ.get("K6G_QEMU_TIMEOUT", "300"))
TIMEOUT_BUILD = int(os.environ.get("K6G_BUILD_TIMEOUT", "1800"))

SCRATCH = (Path(os.environ.get("K6G_TMP")
                or os.environ.get("DADAO_TMP")
                or "/tmp/opencode/m18-linux-003") / "check-linux-k6")
LOG_DIR = SCRATCH / "log"

PROCESS_07 = _REPO / "docs" / "Process-07-门控分层规范.md"
MAKEFILE = _REPO / "Makefile"
SOURCE = linux_paths.linux_source_dir()
BUILD = linux_paths.linux_build_dir()
VMLINUX = BUILD / "vmlinux"

GROUPS = "SCER"

#: Every ``CONFIG_DADAO_*`` symbol of ``Kconfig.debug`` (``check-config-pins``
#: C3 requires the key set to equal the Kconfig set).  The K6 image is the
#: production boot: every milestone probe off, the K6 continuation on.
CONFIG_PINS = {
    "CONFIG_DADAO_K1_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_EARLY_STOP": "n",
    "CONFIG_DADAO_K2_TIME_STOP": "n",
    "CONFIG_DADAO_K2_TIME_CASE": "n",
    "CONFIG_DADAO_K2_IRQ_TEST": "n",
    "CONFIG_DADAO_K2_TRAP_SELFTEST": "n",
    "CONFIG_DADAO_K2_SELFTEST_REENTRY": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXTRAP": "n",
    "CONFIG_DADAO_K2_SELFTEST_CFXESC": "n",
    "CONFIG_DADAO_K2_SELFTEST_UNKNOWN": "n",
    "CONFIG_DADAO_K4_STACK_SELFTEST": "0",
    "CONFIG_DADAO_K4_COW_SELFTEST": "0",
    "CONFIG_DADAO_K4_SELFTEST": "n",
    "CONFIG_DADAO_K4_SWITCH_SELFTEST": "n",
    "CONFIG_DADAO_K4_KTHREAD_SELFTEST": "n",
    "CONFIG_DADAO_K5_SYSCALL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLONE_SELFTEST": "n",
    "CONFIG_DADAO_K5_FUTEX_SELFTEST": "n",
    "CONFIG_DADAO_M45_ENTRY_SELFTEST": "n",
    "CONFIG_DADAO_K5_SIGNAL_SELFTEST": "n",
    "CONFIG_DADAO_K5_CLOCK_SELFTEST": "n",
    "CONFIG_DADAO_K5_PAGESZ_SELFTEST": "n",
}

#: The K6 continuation symbol lives in ``Kconfig`` (not ``Kconfig.debug``), so
#: it is not part of the pin set above.  It is kept as a name (not an inline
#: ``CONFIG_DADAO_X=v`` list element) so ``check-config-pins`` C4 stays true.
K6_SHELL_LINE = "CONFIG_DADAO_K6_SHELL=y"

#: The representative commands, in script order.  Each row is
#: (case name, shell line, exact output lines, "marker=N" the shell prints).
#: ``mkdir`` / ``rm`` appear twice on purpose: the second call is the failure
#: arm (already exists / already gone).  The five *commands* the task names are
#: echo, mkdir, cat, ls, rm; ``false`` and the second calls judge exit codes.
COMMANDS = (
    ("echo", "echo hello; echo echo-rc=$?", ("hello",), "echo-rc=0"),
    ("ls-root", "ls /; echo ls-root-rc=$?", (), "ls-root-rc=0"),
    ("mkdir", "mkdir /k6; echo mkdir-rc=$?", (), "mkdir-rc=0"),
    ("mkdir-exists", "mkdir /k6; echo mkdir2-rc=$?", (), "mkdir2-rc=1"),
    ("cat", "echo payload > /k6/f; cat /k6/f; echo cat-rc=$?",
     ("payload",), "cat-rc=0"),
    ("ls-file", "ls /k6; echo ls-rc=$?", ("f",), "ls-rc=0"),
    ("cat-init", "cat /init; echo cat-init-rc=$?", (), "cat-init-rc=0"),
    ("rm", "rm /k6/f; echo rm-rc=$?", (), "rm-rc=0"),
    ("ls-empty", "ls /k6; echo ls2-rc=$?", (), "ls2-rc=0"),
    ("rm-missing", "rm /k6/f; echo rm2-rc=$?", (), "rm2-rc=1"),
    ("false", "false; echo false-rc=$?", (), "false-rc=1"),
)

#: The five commands the K6 exit criterion names (the rest are exit-code arms).
REPRESENTATIVE = ("echo", "mkdir", "cat", "ls", "rm")

#: The script fed to the shell on stdin; the final line is the process status.
SCRIPT = "".join(f"{line}\n" for _n, line, _o, _m in COMMANDS) + "exit 7\n"

#: §4a.3 retirement table: (file, retired wording, replacement, disposition,
#: alternative criterion).  The gate asserts both directions and that
#: ``docs/Process-07 §4a.3`` carries the row.
RETIREMENTS = (
    ("tests/unit/linux/k4_switch_probe.py",
     "trigger: busybox cannot start for want of K5's",
     "K6 (`check-linux-k6`) is the vehicle that starts",
     "改限定语",
     "check-linux-k6 S 组：/init -> busybox sh 真跑"),
    ("tests/unit/linux/k4_switch_probe.py",
     "Reaching it needs F16 (the boot stops inside `kernel_init_freeable()`,",
     "probe image keeps its own `/init.musl` target",
     "改限定语",
     "check-linux-k6 S/C 组 + 本镜像自己的 /init.musl 判据"),
)

#: The §4a.3 audit: every hit of the target class, including the kept rows
#: (a kept row must be recorded with its reason, not silently omitted).
AUDIT = (
    ("tests/unit/linux/k4_switch_probe.py",
     "K6 (`check-linux-k6`) is the vehicle that starts", "改限定语"),
    ("tests/unit/linux/k4_switch_probe.py",
     "keeps its own `/init.musl` target", "改限定语"),
    ("tests/unit/linux/k4_switch_probe.py",
     "per-task user-mode frame", "保留"),
    ("tests/unit/linux/k4_kthread_probe.py",
     "kernel_init 尚未 execve", "保留"),
    ("components/linux/patches/init/main.c.patch",
     "missing piece is the syscall surface", "保留"),
    ("components/linux/patches/arch/dadao/kernel/k4_switch_selftest.c.patch",
     "until then the honest target", "保留"),
)


class Report:
    """``[PASS]/[FAIL] <id> <name> | 期望=... 实际=...`` plus live ``[STAT]``."""

    def __init__(self, quiet: bool = False) -> None:
        self.total = 0
        self.fails: list[str] = []
        self.groups: dict[str, list[int]] = {}
        self.quiet = quiet

    def check(self, cid: str, name: str, expected, actual) -> bool:
        self.total += 1
        ok = expected == actual
        tally = self.groups.setdefault(cid[0], [0, 0])
        tally[0] += 1
        if not ok:
            tally[1] += 1
            self.fails.append(f"{cid} {name}: 期望={expected} 实际={actual}")
        if not self.quiet:
            print(f"  [{'PASS' if ok else 'FAIL'}] {cid} {name} | "
                  f"期望={expected} 实际={actual}", flush=True)
        return ok

    def stat(self, text: str) -> None:
        if not self.quiet:
            print(f"  [STAT] {text}", flush=True)

    def info(self, text: str) -> None:
        if not self.quiet:
            print(f"  [INFO] {text}", flush=True)

    def summary(self) -> str:
        parts = []
        for group in GROUPS:
            if group in self.groups:
                total, failed = self.groups[group]
                parts.append(f"{group} {total - failed}/{total}")
        return "  ".join(parts)


# ---------------------------------------------------------------------------
# small helpers and live-derived expectations
# ---------------------------------------------------------------------------

def md5(path: Path) -> str:
    return hashlib.md5(Path(path).read_bytes()).hexdigest()


def flat(text: str) -> str:
    return " ".join(text.split())


def config_value(config: str, symbol: str) -> str | None:
    for line in config.splitlines():
        if line.startswith(symbol + "="):
            return line.split("=", 1)[1].strip()
    return None


def config_enabled(config: str, symbol: str) -> bool:
    return config_value(config, symbol) in ("y", "1")


def init_script() -> str:
    return initramfs.INIT_SCRIPT.decode("utf-8")


def init_marker() -> str:
    match = re.search(r'^echo "([^"]+)"$', init_script(), re.MULTILINE)
    if not match:
        raise SystemExit("check_k6: INIT_SCRIPT has no echo marker line")
    return match.group(1)


def init_prompt() -> str:
    match = re.search(r"^PS1='([^']*)'$", init_script(), re.MULTILINE)
    if not match:
        raise SystemExit("check_k6: INIT_SCRIPT has no PS1 line")
    return match.group(1)


def init_exec() -> str:
    match = re.search(r"^(exec \S+)$", init_script(), re.MULTILINE)
    if not match:
        raise SystemExit("check_k6: INIT_SCRIPT has no exec line")
    return match.group(1)


def expected_exit() -> int:
    match = re.search(r"^exit\s+(\d+)\s*$", SCRIPT, re.MULTILINE)
    if not match:
        raise SystemExit("check_k6: the script has no final exit line")
    return int(match.group(1))


def manifest_path() -> Path:
    return linux_paths.linux_initramfs_manifest()


def load_manifest() -> dict:
    path = manifest_path()
    if not path.is_file():
        raise SystemExit(f"check_k6: {path} missing (run make linux-initramfs)")
    return json.loads(path.read_text(encoding="utf-8"))


def repo_text(rel: str) -> str:
    path = _REPO / rel
    if not path.is_file():
        raise SystemExit(f"check_k6: repository file missing: {rel}")
    return path.read_text(encoding="utf-8")


#: Console noise emitted by the kernel around the shell (kept out of the
#: command-output regions; never used to "explain away" a shell line).
_NOISE_RE = re.compile(
    r"^(K[0-9] |K3 pf:|K4 umon|Linux version |Memory:|Freeing unused|"
    r"Run /init as init process|DADAO initramfs:|BusyBox v)")


def region(text: str, start: str, end: str) -> list[str] | None:
    """Lines between the echoed command @start and its @end marker."""
    lines = text.splitlines()
    first = next((i for i, line in enumerate(lines) if start in line), None)
    if first is None:
        return None
    last = next((i for i in range(first + 1, len(lines)) if end in lines[i]),
                None)
    if last is None:
        return None
    return lines[first + 1:last]


def visible(lines: list[str]) -> list[str]:
    return [line for line in lines if line.strip() and not _NOISE_RE.match(line)]


# ---------------------------------------------------------------------------
# build + boot
# ---------------------------------------------------------------------------

def _log_tail(path: Path, count: int = 12) -> str:
    try:
        return "\n".join(path.read_text(encoding="utf-8",
                                        errors="replace").splitlines()[-count:])
    except OSError:
        return ""


def run_logged(label: str, cmd: list[str]) -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log = LOG_DIR / f"{label}.log"
    print(f"[INFO] {label}: {' '.join(cmd)}", flush=True)
    env = dict(os.environ, JOBS=JOBS)
    try:
        with log.open("wb") as stream:
            rc = subprocess.call(cmd, cwd=str(_REPO), stdout=stream,
                                 stderr=subprocess.STDOUT, env=env,
                                 timeout=TIMEOUT_BUILD)
    except subprocess.TimeoutExpired:
        rc = 124
    print(f"[INFO] {label}: rc={rc} (log {log})", flush=True)
    if rc != 0:
        print(_log_tail(log), flush=True)
    return rc


def build_kernel() -> tuple[int, str | None]:
    rc = defconfig.apply_config_lines(
        pins.config_lines(CONFIG_PINS) + [K6_SHELL_LINE])
    if rc != 0:
        return rc, None
    rc = run_logged("kernel", [sys.executable,
                               str(_REPO / "tools" / "linux" / "make_vmlinux.py"),
                               "--jobs", JOBS, "--skip-code-range"])
    config = None
    if (BUILD / ".config").is_file():
        config = (BUILD / ".config").read_text(encoding="utf-8")
    return rc, config


def build_image() -> tuple[int, str | None, dict | None]:
    rc = run_logged("busybox", [sys.executable,
                                str(_REPO / "tools" / "linux" / "build_busybox.py"),
                                "--jobs", JOBS])
    if rc != 0:
        return rc, None, None
    rc = run_logged("initramfs", [sys.executable,
                                  str(_REPO / "tools" / "linux" / "make_initramfs.py")])
    if rc != 0:
        return rc, None, None
    rc, config = build_kernel()
    if rc != 0 or config is None:
        return rc, None, None
    return 0, config, load_manifest()


_ROM: str | None = None


def firmware() -> str:
    global _ROM
    if _ROM is None:
        k0.load_contract()
        if not k0.ABI:
            raise SystemExit("check_k6: the boot contract is empty")
        SCRATCH.mkdir(parents=True, exist_ok=True)
        _ROM = k0.build_firmware(str(SCRATCH / "bootrom"),
                                 name="bootrom_k6g.bin")
    return _ROM


def boot(tag: str) -> tuple[int, str, list[str]]:
    if not VMLINUX.is_file():
        raise SystemExit(f"check_k6: {VMLINUX} missing (build the K6 image)")
    qemu = str(linux_paths.toolchain_bin() / "qemu-system-dadao")
    if not os.access(qemu, os.X_OK):
        raise SystemExit("check_k6: qemu-system-dadao missing (make install-host)")
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    cmd = [qemu, "-machine", f"kaiwu-vast,bootrom-image={firmware()}",
           "-display", "none", "-serial", "none",
           "-chardev", "stdio,id=semi",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-kernel", str(VMLINUX)]
    try:
        proc = subprocess.run(cmd, cwd=str(_REPO), input=SCRIPT, text=True,
                              capture_output=True, timeout=TIMEOUT_QEMU)
        rc = proc.returncode
        text = (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        rc = 124
        out = exc.stdout or ""
        err = exc.stderr or ""
        if isinstance(out, bytes):
            out = out.decode(errors="replace")
        if isinstance(err, bytes):
            err = err.decode(errors="replace")
        text = out + err
    (LOG_DIR / f"{tag}.log").write_text(text, encoding="utf-8")
    return rc, text, cmd


# ---------------------------------------------------------------------------
# S — startup
# ---------------------------------------------------------------------------

def judge_s(rep: Report, text: str, config: str | None,
            manifest: dict | None) -> None:
    g = "S"
    if config is not None:
        rep.check(g, "镜像配置：CONFIG_DADAO_K6_SHELL = y", "y",
                  config_value(config, "CONFIG_DADAO_K6_SHELL"))
        on = [symbol for symbol, value in CONFIG_PINS.items()
              if value == "n" and config_enabled(config, symbol)]
        rep.check(g, "镜像配置：所有探针/阶段边界符号关", [], on)
        rep.check(g, "镜像页大小 64 KiB（defconfig 的 K6 口径）", "y",
                  config_value(config, "CONFIG_PAGE_SIZE_64KB"))
    if manifest is not None:
        init_entry = next((entry for entry in manifest["entries"]
                           if entry["name"] == "init"), None)
        rep.check(g, "initramfs 含 /init", True, init_entry is not None)
        if init_entry:
            want = hashlib.sha256(initramfs.INIT_SCRIPT).hexdigest()
            rep.check(g, "/init 的 sha256 == 生成器的 INIT_SCRIPT", want,
                      init_entry.get("sha256"))
        links = manifest.get("applet_links", {})
        rep.check(g, "applet 链接集 == 生成器声明的 APPLETS",
                  sorted(initramfs.APPLETS), sorted(links))
        rep.check(g, "每个 applet 链接都指向 busybox", [],
                  sorted(name for name, target in links.items()
                         if target != initramfs.BUSYBOX_LINK))
        product = initramfs.busybox_product()
        sha = hashlib.sha256(product.read_bytes()).hexdigest()
        rep.check(g, "镜像里的 bin/busybox == 当前构建产物", sha,
                  manifest.get("busybox", {}).get("sha256"))

    marker = init_marker()
    prompt = init_prompt()
    rep.check(g, "内核把 /init 当作 init 进程执行", True,
              "Run /init as init process" in text)
    rep.check(g, "生成器的 /init 启动行出现且只出现一次", 1,
              len([line for line in text.splitlines() if line == marker]))
    rep.check(g, "busybox ash 的启动横幅出现且只出现一次", 1,
              len(re.findall(r"^BusyBox v\S+ .*built-in shell \(ash\)$",
                             text, re.MULTILINE)))
    rep.check(g, "shell 提示符 == INIT_SCRIPT 的 PS1", len(COMMANDS) + 1,
              len([line for line in text.splitlines()
                   if line.startswith(prompt)]))


# ---------------------------------------------------------------------------
# C — the five representative commands
# ---------------------------------------------------------------------------

def judge_c(rep: Report, text: str, manifest: dict | None = None) -> None:
    g = "C"
    names = {name.split("-")[0] for name, *_rest in COMMANDS}
    rep.check(g, "代表命令集 == 任务口径", sorted(REPRESENTATIVE),
              sorted(names & set(REPRESENTATIVE)))
    rep.stat(f"commands={len(REPRESENTATIVE)} cases={len(COMMANDS)}")

    for name, line, outputs, marker in COMMANDS:
        lines = region(text, line, marker)
        if lines is None:
            rep.check(g, f"{name}: 命令与 rc 行都出现", True, False)
            continue
        body = visible(lines)
        rep.check(g, f"{name}: rc 标记是脚本期望的 {marker}", True,
                  marker in text)
        if name == "ls-file":
            rep.check(g, "ls 列出刚写的文件 f", True, "f" in body)
        elif name == "ls-empty":
            rep.check(g, "rm 后 ls /k6 输出为空", [], body)
        else:
            rep.check(g, f"{name}: 输出行 {outputs}", [],
                      [want for want in outputs if want not in body])
        if name == "mkdir-exists":
            rep.check(g, "mkdir 的失败臂给出诊断", True,
                      any("File exists" in entry or "exist" in entry.lower()
                          for entry in body))
        if name == "rm-missing":
            rep.check(g, "rm 的失败臂给出诊断", True,
                      any("No such file" in entry or "can't remove" in entry
                          for entry in body))
        if name == "cat-init":
            rep.check(g, "cat /init 打印生成器的 exec 行", True,
                      init_exec() in body)

    entries = (manifest or {}).get("entries") or []
    rep.check(g, "initramfs 条目可派生（空表 ⇒ vacuous FAIL）", True,
              bool(entries))
    top = sorted({entry["name"].split("/")[0] for entry in entries} - {"."})
    ls_lines = region(text, "ls /; echo ls-root-rc=$?", "ls-root-rc=")
    tokens = set()
    if ls_lines is not None:
        for line in visible(ls_lines):
            tokens.update(line.split())
    rep.check(g, "ls / 列出 initramfs 顶层条目", [], [name for name in top
                                                     if name not in tokens])

    positions = []
    for _name, _line, _outputs, marker in COMMANDS:
        index = text.find(marker)
        positions.append(index)
    rep.check(g, "命令按脚本顺序执行（rc 行下标递增）", sorted(positions),
              positions)
    rep.check(g, "没有中途停摆（每条命令的 rc 行都在）", [],
              [marker for _n, _l, _o, marker in COMMANDS if marker not in text])


# ---------------------------------------------------------------------------
# E — process exit
# ---------------------------------------------------------------------------

def judge_e(rep: Report, text: str, rc: int) -> None:
    g = "E"
    want = expected_exit()
    rep.check(g, "QEMU 进程状态 == 脚本最后的 exit N", want, rc)
    rep.check(g, "不是超时（rc 124 是 FAIL，不是通过）", False, rc == 124)
    rep.check(g, "exit 码在 guest 可编码范围内（1..127）", True, 1 <= want <= 127)
    non_empty = [line for line in text.splitlines() if line.strip()]
    rep.check(g, "最后一条输入是 exit N（shell 收到并执行）", True,
              bool(non_empty) and f"exit {want}" in non_empty[-1])


# ---------------------------------------------------------------------------
# R — reverse assertions, wiring and §4a.3 retirement
# ---------------------------------------------------------------------------

def retirement_problems(files: dict[str, str | None]) -> list[str]:
    problems = []
    for rel, old, new, _disposition, _alternative in RETIREMENTS:
        text = files.get(rel)
        if text is None:
            problems.append(f"{rel}: 文件缺失")
            continue
        if new not in text:
            problems.append(f"{rel}: 新文案缺失（{new[:24]}…）")
        if old in text:
            problems.append(f"{rel}: 旧文案回潮（{old[:24]}…）")
    return problems


def judge_r(rep: Report, run: dict) -> None:
    g = "R"
    text = run["text"]
    lines = [line for line in text.splitlines() if line.strip()]
    rep.check(g, "无 monitor 具名终止痕迹（dadao: die）", [],
              [line for line in lines if line.startswith("dadao: die")])
    rep.check(g, "无 die-no-vma", [], [line for line in lines
                                       if "die-no-vma" in line])
    rep.check(g, "无 unknown cause", False, "unknown cause" in text)
    rep.check(g, "无 panic / oops / BUG / Call Trace", [],
              [line for line in lines
               if re.search(r"(Kernel panic|\bpanic\b|\bOops\b|^BUG:|"
                            r"Call Trace)", line)])
    rep.check(g, "无 recursive supv exception", False,
              "recursive supv exception" in text)
    rep.check(g, "无内核自报 FAIL 行", [],
              [line for line in lines if re.search(r"FAIL: ?\S+=", line)])
    starts = [name for name in
              ("K4 switch: begin", "K5 selftest: begin",
               "K5 clone selftest: begin", "K5 futex selftest: begin",
               "M46 selftest: begin", "K5P selftest: begin",
               "K5 clock: begin") if name in text]
    rep.check(g, "镜像不跑任何阶段探针", [], starts)
    rep.check(g, "命令行无 -d/-D（无逐指令日志）", True,
              "-d" not in run["cmd"] and "-D" not in run["cmd"])

    # §4a.3: new wording in, retired wording out.
    files = {rel: (repo_text(rel) if (_REPO / rel).is_file() else None)
             for rel, *_rest in RETIREMENTS}
    rep.check(g, "§4a 退役：新文案在 / 旧文案不在", [],
              retirement_problems(files))

    doc = PROCESS_07.read_text(encoding="utf-8")
    rep.check(g, "Process-07 §4a.3 有本任务的退役记录", True,
              "4a.3" in doc and "m18-linux-003" in doc)
    for rel, _old, _new, disposition, alternative in RETIREMENTS:
        row = [line for line in doc.splitlines()
               if rel in line and (disposition in line
                                   or flat(alternative)[:20] in flat(line))]
        rep.check(g, f"§4a 记录覆盖 {rel}:{_old[:16]}…", True, bool(row))
        rep.check(g, f"§4a 记录指向替代判据（{alternative[:12]}…）", True,
                  bool(row) and any(disposition in line
                                    or "check-linux-k6" in line
                                    for line in row))
    for rel, anchor, disposition in AUDIT:
        row = [line for line in doc.splitlines()
               if rel in line and flat(anchor)[:24] in flat(line)
               and disposition in line]
        rep.check(g, f"§4a.3 审计行：{rel.split('/')[-1]}:{anchor[:16]}…",
                  True, bool(row))

    make = MAKEFILE.read_text(encoding="utf-8")
    phony_lines, in_phony = [], False
    for line in make.splitlines():
        if line.startswith(".PHONY:"):
            in_phony = True
        elif in_phony and not line.rstrip().endswith("\\"):
            phony_lines.append(line)
            break
        if in_phony:
            phony_lines.append(line)
    phony = "\n".join(phony_lines)
    locked_lines, collecting = [], False
    for line in make.splitlines():
        if line.startswith("GATE_LOCKED_TARGETS"):
            collecting = True
        if collecting:
            locked_lines.append(line)
            if not line.rstrip().endswith("\\"):
                break
    locked_text = "\n".join(locked_lines)
    l2 = [line for line in make.splitlines()
          if line.startswith("_locked-check-modules:")]
    help_text = make.split("help:", 1)[1] if "help:" in make else ""
    rep.check(g, "Makefile：check-linux-k6 入 PHONY", True,
              "check-linux-k6" in phony)
    rep.check(g, "Makefile：check-linux-k6 入 GATE_LOCKED_TARGETS", True,
              "check-linux-k6" in locked_text)
    rep.check(g, "Makefile：check-linux-k6 入 L2 _locked-check-modules", True,
              bool(l2) and "check-linux-k6" in l2[0])
    rep.check(g, "Makefile：help 有 check-linux-k6 行", True,
              "make check-linux-k6" in help_text)
    doc_rows = [line for line in doc.splitlines()
                if line.startswith("| `make check-linux-k6`")]
    rep.check(g, "Process-07 目标-层表有 check-linux-k6（L2）", True,
              bool(doc_rows) and "**L2**" in doc_rows[0])


# ---------------------------------------------------------------------------
# injections (real rebuilds, `cp` + md5 restore, green again)
# ---------------------------------------------------------------------------

#: name -> injection spec.  ``root`` selects the repository tree or the
#: component source tree; ``kind`` selects what must be rebuilt afterwards.
INJECTIONS = {
    "init-no-shell": {
        "root": "repo", "kind": "initramfs",
        "path": "tools/linux/make_initramfs.py",
        "old": '    b"exec /bin/sh\\n"\n',
        "new": '    b"exit 0\\n"\n',
        "group": "S",
        "why": "/init 不再 exec sh（shell 启动行消失）⇒ S 红",
    },
    "prompt-changed": {
        "root": "repo", "kind": "initramfs",
        "path": "tools/linux/make_initramfs.py",
        "old": "    b\"PS1='dadao# '\\n\"\n",
        "new": "    b\"PS1='k6# '\\n\"\n",
        "group": "S",
        "why": "提示符与 INIT_SCRIPT 不一致 ⇒ S 红",
    },
    "applet-cat-missing": {
        "root": "repo", "kind": "initramfs",
        "path": "tools/linux/make_initramfs.py",
        "old": 'APPLETS = ("cat", "cp",',
        "new": 'APPLETS = ("cp",',
        "group": "C",
        "why": "镜像不装 cat 链接 ⇒ cat 命令 rc=127、输出缺失 ⇒ C 红",
    },
    "exit-code-zero": {
        "root": "source", "kind": "kernel",
        "path": "kernel/exit.c",
        "old": "dadao_init_exit(tsk->signal->group_exit_code ?: (int)code);",
        "new": "dadao_init_exit(0);",
        "group": "E",
        "why": "PID 1 的退出码被写 0 ⇒ QEMU rc 与 exit N 不符 ⇒ E 红",
    },
    "k6-shell-off": {
        "root": "source", "kind": "kernel",
        "path": "arch/dadao/kernel/setup.c",
        "old": "#ifdef CONFIG_DADAO_K6_SHELL",
        "new": "#if 0",
        "group": "S",
        "why": "boot 停在 K4 边界、不进 /init ⇒ S 红",
    },
}

#: Static injection: the §4a "retired wording comes back" path.
STATIC_INJECTIONS = {
    name: (rel, old) for name, rel, old in (
        ("retired-back", *RETIREMENTS[0][:2]),
    )
}


def group_red(group: str, run: dict, quiet: bool = True) -> list[str]:
    rep = Report(quiet=quiet)
    if group == "S":
        judge_s(rep, run["text"], None, None)
    elif group == "C":
        judge_c(rep, run["text"], run.get("manifest"))
    elif group == "E":
        judge_e(rep, run["text"], run["rc"])
    else:
        judge_r(rep, run)
    return rep.fails


def rebuild(kind: str) -> int:
    """Rebuild the artefact that carries @kind.

    The kernel embeds the initramfs at link time (``usr/initramfs_data.S``), so
    an initramfs injection needs the kernel rebuilt too — otherwise the old
    archive inside ``vmlinux`` would mask the mutation.
    """
    if kind == "initramfs":
        rc = run_logged("initramfs", [sys.executable,
                                      str(_REPO / "tools" / "linux" /
                                          "make_initramfs.py")])
        if rc != 0:
            return rc
    return build_kernel()[0]


def run_static_injection(rep: Report, name: str) -> None:
    rel, old = STATIC_INJECTIONS[name]
    path = _REPO / rel
    original = path.read_bytes()
    before = md5(path)
    tmp = SCRATCH / f"inject-{name}.orig"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(original)
    text = original.decode()
    if old in text:
        rep.check(f"INJECT {name}", "旧文案已不在源码中（还原态）", True, False)
        return
    path.write_text(text + "\n" + old + "\n", encoding="utf-8")
    try:
        rep.check(f"INJECT {name}", "注入改动了源码", True,
                  path.read_bytes() != original)
        files = {rel2: (path.read_text(encoding="utf-8")
                        if rel2 == rel else repo_text(rel2))
                 for rel2, *_rest in RETIREMENTS}
        rep.check(f"INJECT {name}", "旧文案回潮 ⇒ R 红", True,
                  any("旧文案回潮" in problem
                      for problem in retirement_problems(files)))
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        files = {rel2: (path.read_text(encoding="utf-8")
                        if rel2 == rel else repo_text(rel2))
                 for rel2, *_rest in RETIREMENTS}
        rep.check(f"INJECT {name}", "还原后 R 回绿", [],
                  retirement_problems(files))


def run_injection(rep: Report, name: str) -> None:
    spec = INJECTIONS[name]
    path = (_REPO / spec["path"] if spec["root"] == "repo"
            else SOURCE / spec["path"])
    original = path.read_bytes()
    before = md5(path)
    tmp = SCRATCH / f"inject-{name}.orig"
    tmp.parent.mkdir(parents=True, exist_ok=True)
    tmp.write_bytes(original)
    text = original.decode()
    if spec["old"] not in text:
        rep.check(f"INJECT {name}", "注入点存在于源码", True, False)
        return
    path.write_text(text.replace(spec["old"], spec["new"], 1), encoding="utf-8")
    try:
        rep.check(f"INJECT {name}", "注入改动了源码", True,
                  path.read_bytes() != original)
        rc = rebuild(spec["kind"])
        rep.check(f"INJECT {name}", f"注入后镜像可构建（{spec['why']}）", 0, rc)
        if rc != 0:
            return
        run_rc, out, cmd = boot(f"inject-{name}")
        fails = group_red(spec["group"], {"rc": run_rc, "text": out,
                                          "cmd": cmd,
                                          "manifest": load_manifest()})
        rep.info(f"inject {name}: rc={run_rc} group={spec['group']} "
                 f"red={fails[:3]}")
        rep.check(f"INJECT {name}", f"{spec['why']}", True, bool(fails))
    finally:
        path.write_bytes(tmp.read_bytes())
        rep.check(f"INJECT {name}", "还原（cp + md5 对账）", before, md5(path))
        rc = rebuild(spec["kind"])
        rep.check(f"INJECT {name}", "还原后可构建", 0, rc)
        if rc == 0:
            run_rc, out, cmd = boot(f"restored-{name}")
            fails = group_red(spec["group"], {"rc": run_rc, "text": out,
                                              "cmd": cmd,
                                              "manifest": load_manifest()})
            rep.check(f"INJECT {name}", "还原后本组回绿", [], fails[:5])


# ---------------------------------------------------------------------------
# --selfcheck: every group flips (no build, no boot)
# ---------------------------------------------------------------------------

SYNTH_MANIFEST = {"entries": [{"name": name} for name in
                              ("bin", "dev", "init",
                               initramfs.MUSL_INIT_NAME)]}


def synthetic_console() -> str:
    """A console where every watched fact is right (selfcheck scaffolding)."""
    marker = init_marker()
    prompt = init_prompt()
    out = [marker, "Run /init as init process",
           "BusyBox v1.38.0 (2026-05-13 02:20:15 UTC) built-in shell (ash)"]
    for name, line, outputs, rc_marker in COMMANDS:
        out.append(prompt + line)
        out.extend(outputs)
        if name == "mkdir-exists":
            out.append("mkdir: can't create directory '/k6': File exists")
        if name == "rm-missing":
            out.append("rm: can't remove '/k6/f': No such file or directory")
        if name == "cat-init":
            out.append(init_exec())
        if name == "ls-file":
            out.append("f")
        out.append(rc_marker)
    # `ls /` is judged from the manifest; put its names in its own region.
    names = "        ".join(sorted({"bin", "dev", "init",
                                     initramfs.MUSL_INIT_NAME}))
    index = out.index(prompt + "ls /; echo ls-root-rc=$?")
    out.insert(index + 1, names)
    out.append(prompt + f"exit {expected_exit()}")
    return "\n".join(out) + "\n"


def selfcheck() -> int:
    problems: list[str] = []
    base = synthetic_console()

    def flip(group: str, why: str, watched: str, broken: str,
             rc: int = 7) -> None:
        run = lambda text, code: {"rc": code, "text": text, "cmd": ["qemu"],
                                  "manifest": SYNTH_MANIFEST}  # noqa: E731
        clean = not any(watched in fail
                        for fail in group_red(group, run(base, 7)))
        red = any(watched in fail
                  for fail in group_red(group, run(broken, rc)))
        ok = clean and red
        print(f"  [{'PASS' if ok else 'FAIL'}] selfcheck {group} | "
              f"注入「{why}」⇒ 期望={group} 变红 实际="
              f"对照={'绿' if clean else '红'}"
              f"、翻转后={'红' if red else '未变红'}", flush=True)
        if not ok:
            problems.append(f"selfcheck {group}: 未翻转（{why}）")

    flip("S", "/init 启动行缺失", "生成器的 /init 启动行",
         base.replace(init_marker() + "\n", "", 1))
    flip("C", "cat 输出缺失", "cat: 输出行", base.replace("payload\n", "", 1))
    flip("E", "退出码改成 3", "QEMU 进程状态", base, rc=3)

    # R: a panic turns the reverse group red (the console checks run first).
    run = {"rc": expected_exit(), "text": base, "cmd": ["qemu"],
           "manifest": SYNTH_MANIFEST}
    base_fails = group_red("R", run)
    panic = base.replace("BusyBox v", "Kernel panic - not syncing\nBusyBox v", 1)
    red_fails = group_red("R", {"rc": expected_exit(), "text": panic,
                                "cmd": ["qemu"],
                                "manifest": SYNTH_MANIFEST})
    ok = (not any("panic" in fail for fail in base_fails)
          and any("panic" in fail for fail in red_fails))
    print(f"  [{'PASS' if ok else 'FAIL'}] selfcheck R | 注入「panic」⇒ "
          f"期望=R 变红 实际={'翻转' if ok else '未翻转'}", flush=True)
    if not ok:
        problems.append("selfcheck R: panic 未变红")

    # R: the retired wording coming back must be red.
    files = {rel: (repo_text(rel) if (_REPO / rel).is_file() else None)
             for rel, *_rest in RETIREMENTS}
    clean = retirement_problems(files)
    rel, old, _new, _d, _a = RETIREMENTS[0]
    dirty_files = dict(files)
    dirty_files[rel] = (files[rel] or "") + "\n" + old
    dirty = retirement_problems(dirty_files)
    ok = not clean and bool(dirty)
    print(f"  [{'PASS' if ok else 'FAIL'}] selfcheck R | 注入「旧文案回潮」⇒ "
          f"期望=R 变红 实际={'红：' + dirty[0] if dirty else '未变红'}",
          flush=True)
    if not ok:
        problems.append("selfcheck R: 旧文案回潮未变红")

    if problems:
        print(f"check_k6 --selfcheck: FAIL ({len(problems)} 问题)")
        for problem in problems:
            print("  - " + problem)
        return 1
    print(f"check_k6 --selfcheck: PASS ({len(GROUPS)} 组各一次可翻转 + 对照)")
    return 0


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="M18 K6 closure gate")
    parser.add_argument("--selfcheck", action="store_true",
                        help="prove every group can fail (no build, no boot)")
    parser.add_argument("--inject", action="append", default=[], metavar="NAME",
                        help=f"run this injection (repeatable); one of: "
                             f"{', '.join(sorted(set(INJECTIONS) | set(STATIC_INJECTIONS)))}")
    parser.add_argument("--all-inject", action="store_true",
                        help="run every injection (the evidence script does this)")
    parser.add_argument("--no-build", action="store_true",
                        help="assert on the existing build products only")
    parser.add_argument("--only", default="", metavar="GROUPS",
                        help="run only these group letters (e.g. SCR)")
    args = parser.parse_args()

    if args.selfcheck:
        return selfcheck()

    wanted = [g for g in GROUPS if not args.only or g in args.only]
    if not wanted:
        raise SystemExit(f"check_k6: no group in --only {args.only!r}")

    config = manifest = None
    if args.no_build:
        if (BUILD / ".config").is_file():
            config = (BUILD / ".config").read_text(encoding="utf-8")
        if manifest_path().is_file():
            manifest = load_manifest()
    else:
        rc, config, manifest = build_image()
        if rc != 0 or config is None or manifest is None:
            rep = Report()
            rep.check("S", "K6 镜像可构建（busybox + initramfs + kernel）",
                      0, rc)
            print(f"\ncheck_k6: 0/{rep.total} passed, "
                  f"{len(rep.fails)} FAILED")
            return 1

    rep = Report()
    run = None
    if any(group in wanted for group in ("S", "C", "E", "R")):
        run_rc, out, cmd = boot("gate")
        run = {"rc": run_rc, "text": out, "cmd": cmd}
        for group in ("S", "C", "E"):
            if group not in wanted:
                continue
            if group == "S":
                judge_s(rep, out, config, manifest)
            elif group == "C":
                judge_c(rep, out, manifest)
            else:
                judge_e(rep, out, run_rc)
        if "R" in wanted:
            judge_r(rep, run)

    names = list(args.inject)
    if args.all_inject:
        names += sorted(INJECTIONS) + sorted(STATIC_INJECTIONS)
    for name in names:
        if name in STATIC_INJECTIONS:
            run_static_injection(rep, name)
        elif name in INJECTIONS:
            run_injection(rep, name)
        else:
            raise SystemExit(f"check_k6: unknown injection {name!r}")

    print()
    print(f"check_k6: {rep.summary()}  items={rep.total} "
          f"commands={len(REPRESENTATIVE)}")
    if rep.fails:
        print(f"check_k6: {rep.total - len(rep.fails)}/{rep.total} passed, "
              f"{len(rep.fails)} FAILED")
        for name in rep.fails:
            print(f"  - {name}")
        return 1
    print(f"check_k6: {rep.total}/{rep.total} passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
