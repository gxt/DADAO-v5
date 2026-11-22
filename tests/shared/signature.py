#!/usr/bin/env python3
"""signature.py — 签名流（signature）机制 host 侧：解析 / 比对 / 三平台取流。

判据来源（真源，不写魔数）：
  * 槽宽 8 字节、大端、64 位：`contract-see §2` / `ADR-0003 D1`（与
    `tests/shared/asm/signature.inc` 的 `SIG_SLOT` 同一口径）；
  * 未写哨兵 `0xdeadbeef`：`tests/shared/asm/signature.inc` 的 `SIG_UNWRITTEN`
    （漏跑可见：报「槽 N 未写」，不静默当 0）；
  * 收尾输出通道 = semihosting `SYS_WRITE`（handle 1 块写）/ `SYS_WRITEC`
    逐字节回退（`contract-semihosting §3`）。

两类使用者（**机制只此一份**）：
  * `tests/ee-tiny/run_inst_tiny.py`：三平台取流 + 跨平台比对（`capture`/`parse`）；
  * `tests/arch/`：word-builder 探针用 `Emitter` 产 `SIG_BEGIN`/`SIGUPD`/`SIG_DUMP`
    等价指令序列，host 侧用同一 `parse`/`compare` 判定。

对外 API：
  parse(blob, count)      -> list[int | None]（None = 未写哨兵）
  compare(got, want)      -> list[str]（每条 = 「槽 N 期望 0x… 实际 0x…」）
  unwritten(slots)        -> list[str]（只用「漏跑可见」的 scope 用）
  capture(platform, ...)  -> (rc, blob, log_path)
  run(cmd, ...)           -> (rc, blob, log_path)
  Emitter(asm)            -> begin/upd/dump（word-builder 形态）

`capture` 的 platform：`qemu`（Tiny `-bios`/`-kernel`）、`gem5`（FS
`--console-out`）、`chipyard`（Verilator harness `+semiout`）、`qemu-bootrom`
（Vast 探针，`-machine ...,bootrom-image=`）。
退出码：`rc = -2` 表示超时（不是任何 guest 退出码）。
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

# 与 tests/shared/asm/signature.inc 同一口径
SLOT = 8
UNWRITTEN = 0xDEADBEEF
ARG_TAIL = 0x7F8          # SIG_DUMP 参数块在签名区尾部（容量 0x800）
MAX_SLOTS = 127           # inst 检查点上限（tests/inst/README.md）

SEMIHOST_TAG = 0x3FF00
SYS_WRITEC = 0x03
SYS_WRITE = 0x05


class SignatureError(Exception):
    """签名流不可解析：长度不是 `count × 8`，或槽数超出上限。"""


# ---------------------------------------------------------------------------
# 解析 / 比对
# ---------------------------------------------------------------------------
def parse(blob: bytes, count: int, sentinel: bool = True) -> list:
    """把字节流切成 `count` 个 8 字节大端槽。

    `sentinel=True`（默认，签名区由 `SIG_BEGIN` 预填的 scope 用）：`0xdeadbeef`
    ⇒ `None`（未写）；`sentinel=False`：原样返回值 —— 用于**不带预填**的既有
    inst 镜像（`tests/inst` 的槽全部由 `__REC` 写出，且合法结果本身就可能等于
    `0x00000000deadbeef`，不能把它当「未写」）。

    长度**必须**恰为 `count × 8`（fail-closed：短流/长流都抛 `SignatureError`，
    不按「能读多少读多少」静默放过）。
    """
    if count < 0 or count > MAX_SLOTS:
        raise SignatureError("槽数 %d 不在 0..%d" % (count, MAX_SLOTS))
    want = count * SLOT
    if len(blob) != want:
        raise SignatureError(
            "签名字节数 %d ≠ %d（%d 槽 × %d 字节）" % (len(blob), want, count, SLOT))
    slots = []
    for i in range(count):
        value = int.from_bytes(blob[i * SLOT:(i + 1) * SLOT], "big")
        slots.append(None if (sentinel and value == UNWRITTEN) else value)
    return slots


def compare(got, want) -> list:
    """逐槽比对，返回问题列表（空 = 全等）。

    每条写明槽号与两侧值（16 进制）；`None` = 0xdeadbeef 未写哨兵 ⇒
    「槽 N 未写」，不是「值为 0」。
    """
    problems = []
    if len(got) != len(want):
        problems.append("槽数 %d ≠ 期望 %d" % (len(got), len(want)))
    for i, (g, w) in enumerate(zip(got, want)):
        if g is None:
            problems.append("槽 %d 未写（期望 0x%016x）" % (i, w))
        elif g != w:
            problems.append("槽 %d 期望 0x%016x 实际 0x%016x" % (i, w, g))
    return problems


def unwritten(slots) -> list:
    """只检查「每个槽都被写过」（跨平台流的判定用它；`None` ⇒ 槽 N 未写）。"""
    return ["槽 %d 未写" % i for i, v in enumerate(slots) if v is None]


# ---------------------------------------------------------------------------
# 取流
# ---------------------------------------------------------------------------
def run(cmd, *, out=None, log=None, timeout=120, env=None):
    """执行一条命令并取签名流，返回 `(rc, blob, log_path)`。

    `out` 给定 ⇒ 流走**文件通道**（QEMU/semihosting chardev、gem5
    `--console-out`、chipyard `+semiout`），从该文件读字节；
    否则读进程 stdout。`log` 收 stdout+stderr（交互式调试不截断）。
    超时 ⇒ `rc = -2`、blob 为空（区别于任何 guest 退出码）。
    """
    if out is not None:
        Path(out).unlink(missing_ok=True)
    full_env = dict(os.environ)
    if env:
        full_env.update(env)
    stdout = subprocess.PIPE if log is None else open(log, "wb")
    try:
        try:
            proc = subprocess.run(cmd, stdout=stdout, stderr=subprocess.STDOUT,
                                  timeout=timeout, env=full_env,
                                  stdin=subprocess.DEVNULL)
            rc = proc.returncode
            blob = proc.stdout if proc.stdout is not None else b""
        except subprocess.TimeoutExpired:
            rc, blob = -2, b""
    finally:
        if log is not None:
            stdout.close()
    if out is not None:
        path = Path(out)
        blob = path.read_bytes() if path.is_file() else b""
    return rc, blob, log


def capture(platform, **kw):
    """按平台构造命令并取流；返回 `(rc, blob, log_path)`。

    platform 与必需参数：
      * `qemu`        : image, bootrom, out, log, timeout
      * `gem5`        : image, config, bootrom, out, log, outdir, timeout, extra
      * `chipyard`    : image, out, log, timeout, env, max_cycles
      * `qemu-bootrom`: rom, machine, out, log, timeout
    """
    if platform == "qemu":
        return _capture_qemu(**kw)
    if platform == "gem5":
        return _capture_gem5(**kw)
    if platform == "chipyard":
        return _capture_chipyard(**kw)
    if platform == "qemu-bootrom":
        return _capture_qemu_bootrom(**kw)
    raise ValueError("unknown signature platform %r" % (platform,))


def _capture_qemu(image, bootrom, out, log, timeout, qemu="qemu-system-dadao"):
    cmd = [str(qemu), "-M", "kaiwu-tiny", "-bios", str(bootrom),
           "-kernel", str(image),
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=%s" % out,
           "-nographic"]
    return run(cmd, out=out, log=log, timeout=timeout)


def _capture_gem5(image, config, bootrom, out, log, outdir, timeout, extra=(),
                  gem5="gem5.opt"):
    cmd = [str(gem5), "--outdir=%s" % outdir, str(config),
           "--profile", "tiny", "--bootrom", str(bootrom),
           "--kernel", str(image), "--semihost", "on",
           "--console-out", str(out)]
    cmd += list(extra)
    return run(cmd, out=out, log=log, timeout=timeout)


def _capture_chipyard(image, out, log, timeout, env, max_cycles,
                      sim="simulator-chipyard.harness-WumingTinyConfig"):
    cmd = [str(sim), "+permissive",
           "+loadmem=%s" % image, "+semiout=%s" % out,
           "+max-cycles=%s" % max_cycles, "+permissive-off", "none"]
    return run(cmd, out=out, log=log, timeout=timeout, env=env)


def _capture_qemu_bootrom(rom, machine, out, log, timeout,
                          qemu="qemu-system-dadao"):
    cmd = [str(qemu), "-machine",
           "%s,bootrom-image=%s" % (machine, rom), "-nographic",
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=%s" % out]
    return run(cmd, out=out, log=log, timeout=timeout)


# ---------------------------------------------------------------------------
# word-builder 形态（`tests/arch` 探针：与 signature.inc 同一语义）
# ---------------------------------------------------------------------------
class Emitter:
    """把签名机制落到 word 列表 builder 上。

    `asm` 提供编码器：`load_rd`/`load_rb`（返回 word 列表）、`st_o`/`add_si`/
    `add_si_rb`/`trap`（返回单 word）；`seq` 提供 `.e(*words)`/`.mark(label)`/
    `.b(kind, rd, label, rdb=0)`（自相对分支，见 `arch/node_probe_prelude.Seq`）。
    寄存器约定与 `signature.inc` 相同：`rb30` = 写指针。
    """

    def __init__(self, asm, ptr=30, tmp_rd=20, tmp_rb=20):
        self.asm = asm
        self.ptr = ptr
        self.tmp_rd = tmp_rd
        self.tmp_rb = tmp_rb
        self._tag = 0

    def begin(self, seq, buf, count):
        """预填 `count` 个 `0xdeadbeef` 槽，`rb30` 指区首（= `SIG_BEGIN`）。"""
        if count > MAX_SLOTS:
            raise SignatureError("槽数 %d > %d" % (count, MAX_SLOTS))
        seq.e(*self.asm.load_rb(self.ptr, buf))
        seq.e(*self.asm.load_rd(self.tmp_rd, UNWRITTEN))
        for i in range(count):
            seq.e(self.asm.st_o(self.tmp_rd, self.ptr, i * SLOT))

    def upd(self, seq, reg):
        """追加一个观测点（= `SIGUPD`）。"""
        seq.e(self.asm.st_o(reg, self.ptr, 0))
        seq.e(self.asm.add_si_rb(self.ptr, SLOT))

    def dump(self, seq, buf, count):
        """整段输出（= `SIG_DUMP`：块写失败则逐字节回退）。"""
        if count <= 0:
            return
        self._tag += 1
        fb, dn, lp = ("sig_fb_%d" % self._tag, "sig_dn_%d" % self._tag,
                      "sig_lp_%d" % self._tag)
        nbytes = SLOT * count
        argb = buf + ARG_TAIL
        seq.e(*self.asm.load_rb(self.tmp_rb, argb))
        seq.e(*self.asm.load_rd(self.tmp_rd, 1))            # 句柄 1
        seq.e(self.asm.st_o(self.tmp_rd, self.tmp_rb, 0))
        seq.e(*self.asm.load_rd(self.tmp_rd, buf))
        seq.e(self.asm.st_o(self.tmp_rd, self.tmp_rb, 8))
        seq.e(*self.asm.load_rd(self.tmp_rd, nbytes))
        seq.e(self.asm.st_o(self.tmp_rd, self.tmp_rb, 16))
        seq.e(*self.asm.load_rd(16, SYS_WRITE))
        seq.e(*self.asm.load_rb(16, argb))
        seq.e(self.asm.trap(0, SEMIHOST_TAG + SYS_WRITE))
        seq.e(*self.asm.load_rd(self.tmp_rd, nbytes))
        seq.b("z", 8, dn)                    # rd8 == 0：全部写完
        seq.b("eq", 8, fb, self.tmp_rd)      # rd8 == 长度：整段未写
        seq.b("nn", 8, fb)                   # rd8 < 0：句柄无效
        # 部分写（0 < rd8 < 长度）：不重复写，交给 host 长度断言
        seq.b("z", 0, dn)                    # rd0 恒零 ⇒ 无条件跳过回退块
        seq.mark(fb)
        seq.e(*self.asm.load_rb(16, buf))
        seq.e(*self.asm.load_rd(16, SYS_WRITEC))
        seq.e(*self.asm.load_rd(17, nbytes))
        seq.mark(lp)
        seq.e(self.asm.trap(0, SEMIHOST_TAG + SYS_WRITEC))
        seq.e(self.asm.add_si_rb(16, 1))
        seq.e(self.asm.add_si(17, -1))
        seq.b("nz", 17, lp)
        seq.mark(dn)
