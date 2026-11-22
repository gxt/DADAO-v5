#!/usr/bin/env python3
"""check_exec_parity.py — `tests/inst` 载体的「最终架构状态/退出码」差分判据。

判据（`m17-idl-003` 验收 1）：

  1. 用 `tools/idl/qemu_final_state.py` 取 QEMU 的**入口态**（ELF `e_entry`
     执行前）与**末态**（收尾 semihosting trap 执行前）；
  2. 把入口态装进 `idl/idl_exec.py`，跑同一 ELF 到停机；
  3. 比较末态：四寄存器组（`rd`/`rb`/`rf`/`ra`）、`ip`、`mode`、`cfx`、
     `SYS_WRITEC` 字节流、退出码。

文档化的等价（只两条，理由都在规范/实现约定里）：

  1. `contract-semihosting §3` 里「无返回」的服务（`SYS_WRITEC`/`SYS_EXIT`）不规定
     `rd8`；QEMU 用 `0xdeadbeef` 占位（`semihosting/arm-compat-semi.c` 的
     `common_semi_dead_cb`，是实现约定不是架构语义）。执行器把这种情形标记为
     `rd8_defined=false`，比对时两侧都跳过 `rd8`。
  2. `spec/SimRISC-00 §2.4`：「有效区之外的 `ra_i` 内容未定义」；`ra1..ra63` 只比
     `RACNT` 有效区（`64−RACNT .. 63`），`ra0`（RACNT + MRPTR）全比。

用法：

    python3 tools/idl/check_exec_parity.py --cases idl/idl_exec_cases.toml \
        --images <run_inst_tiny 的 --work-dir> --bootrom <bootrom_tiny.bin>

退出码：0 = 全部用例通过；1 = 有用例不一致；2 = 环境/输入问题。
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
EXEC = REPO_ROOT / "idl" / "idl_exec.py"
ORACLE = HERE / "qemu_final_state.py"

BANKS = ("rd", "rb", "rf", "ra")


def load_cases(path):
    try:
        import tomllib
    except ImportError:  # pragma: no cover
        raise SystemExit("check_exec_parity: Python 3.11+ (tomllib) required")
    with open(path, "rb") as fh:
        doc = tomllib.load(fh)
    cases = doc.get("case")
    if not isinstance(cases, list) or not cases:
        raise SystemExit("check_exec_parity: %s: no [[case]] entries" % path)
    for c in cases:
        # m17-idl-005 起清单是「镜像 → 类别」：`image` 是主键，`id` 由 stem 派生
        # （旧清单只有 `id`，保留兼容）。
        if "image" in c:
            c.setdefault("id", Path(c["image"]).stem)
        for key in ("id", "category"):
            if key not in c:
                raise SystemExit("check_exec_parity: case missing %r: %r"
                                 % (key, c))
    return cases


def run_case(case, images, bootrom, qemu, tmp, python):
    cid = case["id"]
    elf = Path(images) / cid / (cid + ".elf")
    if not elf.is_file():
        return {"id": cid, "ok": False,
                "detail": "missing image %s" % elf}
    harness_out = elf.parent / (cid + ".qemu.out")
    oracle_json = Path(tmp) / (cid + ".qemu.json")
    guest_out = Path(tmp) / (cid + ".qemu.out")
    proc = subprocess.run(
        [python, str(ORACLE), "--elf", str(elf), "--qemu", qemu,
         "--bootrom", str(bootrom), "--json-out", str(oracle_json),
         "--guest-out", str(guest_out)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return {"id": cid, "ok": False,
                "detail": "qemu_final_state rc=%d: %s"
                          % (proc.returncode, proc.stderr.strip()[:400])}
    oracle = json.loads(oracle_json.read_text(encoding="utf-8"))

    init_json = Path(tmp) / (cid + ".init.json")
    init_json.write_text(json.dumps(oracle["entry"]), encoding="utf-8")
    state_json = Path(tmp) / (cid + ".state.json")
    image_out = Path(tmp) / (cid + ".exec.out")
    proc = subprocess.run(
        [python, str(EXEC), "--elf", str(elf), "--init", str(init_json),
         "--bootrom", str(bootrom), "--state-out", str(state_json),
         "--image-out", str(image_out)],
        capture_output=True, text=True)
    if proc.returncode != 0:
        return {"id": cid, "ok": False,
                "detail": "idl_exec rc=%d: %s"
                          % (proc.returncode, (proc.stderr or proc.stdout)
                             .strip()[:600])}
    state = json.loads(state_json.read_text(encoding="utf-8"))

    diffs = []
    last = oracle["last"]
    expected_out = bytes.fromhex(oracle["guest_out_hex"])
    got_out = image_out.read_bytes() if image_out.exists() else b""
    if not expected_out:
        diffs.append("QEMU 侧 SYS_WRITEC 字节流为空（判据无效）")
    if got_out != expected_out:
        first = next((i for i, (a, b) in enumerate(zip(got_out, expected_out))
                      if a != b), min(len(got_out), len(expected_out)))
        diffs.append("SYS_WRITEC 字节流 len %d != %d，首差 @%d"
                     % (len(got_out), len(expected_out), first))
    if state["exit_code"] != oracle["qemu_rc"]:
        diffs.append("退出码 %r != QEMU %r"
                     % (state["exit_code"], oracle["qemu_rc"]))
    if state["ip"] != last["ip"]:
        diffs.append("ip %#x != QEMU %#x" % (state["ip"], last["ip"]))
    if state["mode"] != last["mode"]:
        diffs.append("mode %r != QEMU %r" % (state["mode"], last["mode"]))
    if state["cfx"] != last["cfx"]:
        diffs.append("cfx %r != QEMU %r" % (state["cfx"], last["cfx"]))
    for bank in BANKS:
        # spec/SimRISC-00 §2.4：「有效区之外的 ra_i 内容未定义」⇒ 只比有效区
        # （ra0 全比；ra1..63 的有效区 = 64−RACNT .. 63）。
        racnt = 0
        if bank == "ra":
            racnt = (state["ra"][0] >> 48) & 0x3F
            if racnt != (last["ra"][0] >> 48) & 0x3F:
                diffs.append("ra0[53:48] RACNT %d != QEMU %d"
                             % (racnt, (last["ra"][0] >> 48) & 0x3F))
        for idx in range(64):
            if bank == "rb" and idx == 0:
                continue                      # rb0 = IP，上面已比
            if bank == "rd" and idx == 8 and not state.get("rd8_defined", True):
                continue                      # 文档化等价：无返回服务不规定 rd8
            if bank == "ra" and idx >= 1 and idx < 64 - racnt:
                continue                      # 未定义区
            got = state[bank][idx]
            want = last[bank][idx]
            if got != want:
                diffs.append("%s[%d] %#x != QEMU %#x" % (bank, idx, got, want))
                if len(diffs) >= 8:
                    break
        if len(diffs) >= 8:
            break
    if harness_out.is_file():
        hb = harness_out.read_bytes()
        if hb != expected_out:
            diffs.append("QEMU 观测面与 harness 记录不一致（%d vs %d B）"
                         % (len(expected_out), len(hb)))
    return {"id": cid, "category": case["category"], "ok": not diffs,
            "detail": "; ".join(diffs) if diffs else "regs/out/exit 全等",
            "steps": state.get("steps"), "bytes": len(got_out)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", default=str(REPO_ROOT / "idl"
                                           / "idl_exec_cases.toml"))
    ap.add_argument("--images", required=True,
                    help="run_inst_tiny.py 的 --work-dir（内含 <id>/<id>.elf）")
    ap.add_argument("--bootrom", required=True)
    ap.add_argument("--qemu", default=None)
    ap.add_argument("--tmp", default=None)
    ap.add_argument("--only", action="append", default=None,
                    help="只跑这些 id（可重复；用于注入自检缩小范围）")
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args(argv)

    qemu = args.qemu or str(REPO_ROOT / ".dadao" / "cross-toolchain" / "bin"
                            / "qemu-system-dadao")
    for what, path in (("qemu", qemu), ("bootrom", args.bootrom),
                       ("idl_exec.py", EXEC), ("qemu_final_state.py", ORACLE)):
        if not Path(path).is_file():
            print("check_exec_parity: %s not found: %s" % (what, path),
                  file=sys.stderr)
            return 2
    cases = load_cases(args.cases)
    if args.only:
        wanted = set(args.only)
        cases = [c for c in cases if c["id"] in wanted]
        missing = wanted - {c["id"] for c in cases}
        if missing:
            print("check_exec_parity: unknown --only id: %s"
                  % ", ".join(sorted(missing)), file=sys.stderr)
            return 2
    tmpdir = args.tmp or tempfile.mkdtemp(prefix="exec-parity-")
    Path(tmpdir).mkdir(parents=True, exist_ok=True)
    records = []
    for case in cases:
        rec = run_case(case, args.images, args.bootrom, qemu, tmpdir,
                       sys.executable)
        records.append(rec)
        print("[%s] %-22s %-10s %s"
              % ("PASS" if rec["ok"] else "FAIL", rec.get("id"),
                 rec.get("category", ""), rec.get("detail", "")))
    npass = sum(1 for r in records if r["ok"])
    if not args.only and len(records) < 20:
        print("check_exec_parity: 用例数 %d < 20（验收下限）" % len(records),
              file=sys.stderr)
        return 2
    print("-" * 72)
    print("check_exec_parity: %d/%d 用例最终架构状态/退出码与 QEMU 一致"
          % (npass, len(records)))
    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps({"schema": "exec-parity/1", "records": records},
                       indent=1) + "\n", encoding="utf-8")
    return 0 if npass == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
