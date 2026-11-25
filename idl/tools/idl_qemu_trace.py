#!/usr/bin/env python3
"""idl_qemu_trace.py — 从 QEMU 观测面派生逐指令 trace（`m17-idl-004`）。

口径（与 `idl/tools/idl_qemu_state.py` 同一组 QEMU 参数）：

  * `-accel tcg,one-insn-per-tb=on -d cpu -D <log>`：每个 TB 一条 `cpu_dump_state`
    记录，记录的是**该指令执行前**的架构状态；
  * 入口 = 第一条 `PC == ELF e_entry` 的记录；入口之前的 BootROM/hmon 固件记录
    不属于被测应用，丢弃；
  * **连续重复记录**（同 PC 且状态逐字段相同）是 QEMU TB 日志伪影，折叠；
  * 第 i 条指令的执行效果 = `records[i+1] - records[i]`（四寄存器组、运行模式、
    cfx code、cfx5/cfx4）；异常 = 记录间 `cfx3`/`cfx63` 的 `TRAPN/SYNCN/ASYNCN`
    计数增量，异常码/地址/信息取该 cfx 的 `CG5`（`cause_id`/`cause_ip`/`cause_info`）；
  * 取指异常 QEMU **不出记录**，其效果落在下一条记录（handler）上 ⇒ 归属到前一条
    指令的区间（与执行器的归并规则一致）。

指令字/助记符从**同一份镜像**读取（ELF PT_LOAD 段 + BootROM 的 hmon 段），用
`contracts/opcodes.yaml` 的编码表译码；不使用 QEMU 反汇编、不解释语义。

`-d cpu` 不提供内存观测，因此 trace 不含内存写回（`m20-gem5-001` 的两个模型各自
可观测内存时再扩展；字段口径见 `idl/docs/trace-format.md`）。
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.dont_write_bytecode = True       # `idl/`/`tools/` 不留字节码残渣
import idl_trace_common as tc  # noqa: E402

DEFAULT_QEMU = REPO_ROOT / ".dadao" / "cross-toolchain" / "bin" / "qemu-system-dadao"

_BANK_RE = re.compile(r"(RD|RB|RF|RA)\[(\d\d)\]: ([0-9a-f]{16})")
_CFX5_RE = re.compile(r"CFX(\d\d) PREVM:([0-9a-f]+) CID:([0-9a-f]+) "
                      r"CIP:([0-9a-f]+) CINFO:([0-9a-f]+) PEND:([0-9a-f]+)")
_CFX4_RE = re.compile(r"CFX(\d\d) ID:[0-9a-f]+ VER:[0-9a-f]+ "
                      r"TRAPN:([0-9a-f]+) SYNCN:([0-9a-f]+) "
                      r"ASYNCN:([0-9a-f]+) ESCN:([0-9a-f]+)")
_BITS_RE = re.compile(r"^\[(\d+):(\d+)\]$")

# contract-semihosting §3 的「无返回 / 宿主时钟」服务号。
_SEMIHOST_IMPL_DEFINED = (0x03, 0x10, 0x18, 0x20)


# ---------------------------------------------------------------------------
# QEMU 观测面
# ---------------------------------------------------------------------------
def elf_entry(path):
    data = Path(path).read_bytes()
    if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 2:
        raise SystemExit("not a big-endian ELF64: %s" % path)
    (entry,) = struct.unpack_from(">Q", data, 24)
    return entry


def parse_dump(path):
    """流式解析 `-d cpu` 记录（只保留四寄存器组、mode、cfx code、cfx3/63）。"""
    records = []
    cur = None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if line.startswith("PC: "):
                if cur is not None:
                    records.append(cur)
                cur = {"pc": int(line.split()[1], 16), "mode": None,
                       "cfx": None,
                       "banks": {b: [0] * 64 for b in tc.BANKS},
                       "cfx5": {}, "cfx4": {}}
                continue
            if cur is None:
                continue
            if line.startswith("MODE: "):
                cur["mode"] = int(line.split()[1], 0)
            elif line.startswith("CFXCODE: "):
                cur["cfx"] = int(line.split()[1], 0)
            elif line[:2] in ("RD", "RB", "RF", "RA"):
                for bank, idx, val in _BANK_RE.findall(line):
                    cur["banks"][bank.lower()][int(idx)] = int(val, 16)
            else:
                m = _CFX5_RE.match(line)
                if m:
                    cfx = int(m.group(1))
                    if cfx in (3, 63):
                        cur["cfx5"][cfx] = [int(x, 16) for x in m.groups()[1:]]
                    continue
                m = _CFX4_RE.match(line)
                if m:
                    cfx = int(m.group(1))
                    if cfx in (3, 63):
                        cur["cfx4"][cfx] = [int(x, 16) for x in m.groups()[1:5]]
    if cur is not None:
        records.append(cur)
    return records


def _same_state(a, b):
    return (a["pc"] == b["pc"] and a["mode"] == b["mode"]
            and a["cfx"] == b["cfx"] and a["banks"] == b["banks"]
            and a["cfx5"] == b["cfx5"] and a["cfx4"] == b["cfx4"])


def entry_index(records, entry):
    for i, rec in enumerate(records):
        if rec["pc"] == entry:
            return i
    raise SystemExit("idl_qemu_trace: entry %#x not in cpu dump" % entry)


def collapse(records):
    """折叠连续重复记录（同 PC 且状态逐字段相同）；返回 (records, n_dropped)。"""
    if not records:
        return [], 0
    out = [records[0]]
    dropped = 0
    for rec in records[1:]:
        if out and _same_state(out[-1], rec):
            dropped += 1
            continue
        out.append(rec)
    return out, dropped


def entry_state(rec):
    return {"ip": rec["pc"], "mode": rec["mode"], "cfx": rec["cfx"],
            "rd": list(rec["banks"]["rd"]), "rb": list(rec["banks"]["rb"]),
            "rf": list(rec["banks"]["rf"]), "ra": list(rec["banks"]["ra"])}


def run_qemu(elf, bootrom, qemu=None, log_path=None, guest_out=None,
             timeout=600):
    """跑一次 QEMU（`one-insn-per-tb` + `-d cpu`）；返回 dump 路径（调用方删除）。"""
    qemu = str(qemu or DEFAULT_QEMU)
    if log_path is None:
        fd, log_path = tempfile.mkstemp(prefix="qemu-cpu-", suffix=".log")
        os.close(fd)
    if guest_out is None:
        fd, guest_out = tempfile.mkstemp(prefix="qemu-semi-", suffix=".out")
        os.close(fd)
    cmd = [qemu, "-M", "kaiwu-tiny", "-bios", str(bootrom),
           "-kernel", str(elf),
           "-semihosting-config", "enable=on,target=native,chardev=semi",
           "-chardev", "file,id=semi,path=%s" % guest_out,
           "-nographic", "-accel", "tcg,one-insn-per-tb=on",
           "-d", "cpu", "-D", str(log_path)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=timeout)
    if proc.returncode != 0:
        sys.stderr.write("idl_qemu_trace: qemu rc=%d stderr=%s\n"
                         % (proc.returncode,
                            proc.stderr.decode("utf-8", "replace")[:400]))
    return {"log": str(log_path), "guest_out": str(guest_out),
            "rc": proc.returncode}


# ---------------------------------------------------------------------------
# 指令字来源（ELF + BootROM hmon 段）
# ---------------------------------------------------------------------------
def _machine_profile():
    path = REPO_ROOT / "tools" / "testcases" / "lib" / "machine_profile.py"
    spec = importlib.util.spec_from_file_location("machine_profile", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class ImageMap:
    """PC → 指令字：ELF PT_LOAD 段 + BootROM 的 hmon 段（同一份镜像）。"""

    def __init__(self, elf_path, bootrom_path, hmon_base):
        data = Path(elf_path).read_bytes()
        if data[:4] != b"\x7fELF" or data[4] != 2 or data[5] != 2:
            raise SystemExit("not a big-endian ELF64: %s" % elf_path)
        phoff, = struct.unpack_from(">Q", data, 32)
        phentsize, phnum = struct.unpack_from(">HH", data, 54)
        self.segments = []
        for i in range(phnum):
            off = phoff + i * phentsize
            p_type, = struct.unpack_from(">I", data, off)
            p_offset, p_vaddr, p_paddr, p_filesz = struct.unpack_from(
                ">QQQQ", data, off + 8)
            if p_type == 1 and p_filesz:               # PT_LOAD
                self.segments.append((p_paddr, data[p_offset:p_offset + p_filesz]))
        self.hmon_base = hmon_base
        self.hmon = b""
        if bootrom_path:
            image = Path(bootrom_path).read_bytes()
            table_off = 0xE000
            magic, version, count = struct.unpack_from(">IHH", image, table_off)
            if magic != 0x44424F54 or version != 1:
                raise SystemExit("bootrom index table: bad magic/version")
            for i in range(count):
                ent = table_off + 16 + i * 32
                etype, _flags, offset, size, _res = struct.unpack_from(
                    ">IIQQQ", image, ent)
                if etype == 1:
                    self.hmon = image[offset:offset + size]
                    break

    def read(self, addr, count):
        for base, blob in self.segments:
            if base <= addr and addr + count <= base + len(blob):
                off = addr - base
                return bytes(blob[off:off + count])
        if (self.hmon and self.hmon_base <= addr
                and addr + count <= self.hmon_base + len(self.hmon)):
            off = addr - self.hmon_base
            return bytes(self.hmon[off:off + count])
        return None

    def word(self, addr):
        raw = self.read(addr, 4)
        if raw is None:
            return None
        return int.from_bytes(raw, "big")


class Decoder:
    """`contracts/opcodes.yaml` 编码表（只译码，不解释语义）。"""

    def __init__(self, path=None):
        import yaml
        records = yaml.safe_load(
            Path(path or (REPO_ROOT / "contracts" / "opcodes.yaml"))
            .read_text(encoding="utf-8"))
        self.entries = [(int(str(r["mask"]), 0), int(str(r["value"]), 0), r)
                        for r in records]

    def decode(self, word):
        if word is None:
            return None
        for mask, value, rec in self.entries:
            if (word & mask) == value:
                return rec, self._fields(rec, word)
        return None

    @staticmethod
    def _fields(rec, word):
        out = {}
        for fld in rec["fields"]:
            m = _BITS_RE.match(fld["bits"])
            hi, lo = int(m.group(1)), int(m.group(2))
            width = hi - lo + 1
            raw = (word >> lo) & ((1 << width) - 1)
            if fld.get("signed") and (raw >> (width - 1)):
                raw -= 1 << width
            out[fld["name"]] = raw
        return out


def semihost_service(rec, fields, banks_before):
    if rec is None or rec.get("mnemonic") != "trap":
        return None
    immu18 = fields.get("immu18", 0)
    if (immu18 >> 8) & 0x3FF != 0x3FF:
        return None
    return banks_before["rd"][16] & 0xFF


# ---------------------------------------------------------------------------
# QEMU 侧 trace 派生
# ---------------------------------------------------------------------------
def derive_trace(records, image, decoder):
    """`records` = 入口起的记录（折叠后）；返回 trace 与统计。"""
    out = []
    states = []
    ra_ok = tc.init_ra_ok(records[0]["banks"])
    rd8_taint = False
    ra_skips = 0
    rd8_skips = 0
    unresolved = 0
    for i in range(len(records) - 1):
        a, b = records[i], records[i + 1]
        word = image.word(a["pc"])
        hit = decoder.decode(word)
        if hit is None:
            unresolved += 1
            op_id = mnemonic = None
            fields = {}
        else:
            rec, fields = hit
            op_id, mnemonic = rec["id"], rec["mnemonic"]
        service = semihost_service(
            None if hit is None else hit[0], fields, a["banks"])
        if service in _SEMIHOST_IMPL_DEFINED:
            rd8_taint = True
        elif a["banks"]["rd"][8] != b["banks"]["rd"][8]:
            rd8_taint = False
        if rd8_taint:
            rd8_skips += 1
        dst, val, skipped, skips = tc.reg_delta(a["banks"], b["banks"], ra_ok,
                                                rd8_ok=not rd8_taint)
        ra_skips += skipped
        exc = None
        for cfx in (3, 63):
            prev4 = a["cfx4"].get(cfx, [0, 0, 0, 0])
            next4 = b["cfx4"].get(cfx, [0, 0, 0, 0])
            if prev4[:3] != next4[:3]:
                frame = b["cfx5"].get(cfx, [0] * 5)
                exc = tc.exc_object(cfx, frame[1], frame[2], frame[3])
                break
        rec = tc.make_record(i + 1, a["pc"], word, op_id, mnemonic,
                             dst, val, exc)
        rec["skip"] = skips                  # 比较用：E4 跳过的 RA 条目名
        out.append(rec)
        states.append({"mode": b["mode"], "cfx": b["cfx"]})
    return {"records": out, "states": states, "ra_ok": ra_ok,
            "rd8_taint": rd8_taint, "unresolved": unresolved,
            "ra_skips": ra_skips, "rd8_skips": rd8_skips}


def observe(elf, bootrom, qemu=None, keep_log=None):
    """跑 QEMU 并返回 (records_from_entry, entry_state, meta)。"""
    elf = Path(elf)
    entry = elf_entry(elf)
    run = run_qemu(elf, bootrom, qemu=qemu, log_path=keep_log)
    try:
        records = parse_dump(run["log"])
        idx = entry_index(records, entry)
        collapsed, dropped = collapse(records[idx:])
        with open(run["guest_out"], "rb") as fh:
            guest = fh.read()
        return {"records": collapsed, "entry": entry_state(collapsed[0]),
                "qemu_rc": run["rc"], "guest_out": guest,
                "duplicates": dropped, "raw_from_entry": len(records) - idx}
    finally:
        if keep_log is None:
            for path in (run["log"], run["guest_out"]):
                try:
                    os.unlink(path)
                except OSError:
                    pass


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--elf", required=True)
    ap.add_argument("--bootrom", required=True)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--entry-out", required=True,
                    help="入口架构状态 JSON（供 idl_exec --init）")
    ap.add_argument("--trace-out", required=True)
    ap.add_argument("--max-bytes", type=int, default=tc.DEFAULT_MAX_BYTES)
    ap.add_argument("--summary-out", default=None)
    args = ap.parse_args(argv)

    obs = observe(args.elf, args.bootrom, qemu=args.qemu)
    prof = _machine_profile()
    image = ImageMap(args.elf, args.bootrom, prof.HMON_BASE)
    trace = derive_trace(obs["records"], image, Decoder())
    writer = tc.TraceWriter(args.trace_out, max_bytes=args.max_bytes)
    for rec in trace["records"]:
        writer.write(rec)
    parts = writer.close()
    summary = {"elf": str(args.elf), "instructions": len(trace["records"]),
               "duplicates": obs["duplicates"],
               "raw_from_entry": obs["raw_from_entry"],
               "ra_skips": trace["ra_skips"], "rd8_skips": trace["rd8_skips"],
               "unresolved": trace["unresolved"], "parts": parts,
               "bytes": writer.bytes}
    Path(args.entry_out).write_text(json.dumps(obs["entry"]),
                                    encoding="utf-8")
    if args.summary_out:
        Path(args.summary_out).write_text(json.dumps(summary) + "\n",
                                          encoding="utf-8")
    print("idl_qemu_trace: %s instructions=%d duplicates=%d unresolved=%d "
          "bytes=%d parts=%d" % (Path(args.elf).name, len(trace["records"]),
                                 obs["duplicates"], trace["unresolved"],
                                 writer.bytes, len(parts)))
    return 0 if trace["unresolved"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
