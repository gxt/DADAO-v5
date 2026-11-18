#!/usr/bin/env python3
"""check_prevcfx — `tools/chipyard/excp/prevcfx.S` 的判据（`m16-chipyard-005`）。

探针把 6 个 8 字节架构值写进结果缓冲后 `SYS_WRITEC` 打印（打印顺序 = 程序顺序）：

  ① `cg5 rc1` 的 boot 保存值           期望 `cfx_power` 编号（Tiny = 63）
  ② `cg5 rc1` 写 0x25 后读回            期望 0x25（RW）
  ③ 写回 `cfx_power` 编号后读回         期望 63
  ④ hmon 入口记录的 `cause_id`         期望 `1 << CFXTRAP`
  ⑤ 落点到达次数                       期望 2
  ⑥ cfx_power 入口记录的 `cause_id`     期望 `1 << CFXESC`

期望值**现场从仓库可跟踪文件派生**（不写死位号）：
  * `CFXTRAP`/`CFXESC` 位号 ← `spec/DADAO-12-SEE-主管系统运行环境.md` §5.2「monitor 异常编号」表；
  * `cfx_power`/`cfx_hmon` 的 cfxha ← `.tao/contracts/contract-see.md`（Tiny 实现范围与复位 cfx）。

退出码：0 = 全部通过；1 = 任一失败（逐项打印 检查名 / expected / actual）。
"""
from __future__ import annotations

import argparse
import re
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
RECORD = 8
N_RECORDS = 6
RW_SENTINEL = 0x25  # `prevcfx.S` 里写入 `cg5 rc1` 的哨兵值（源码同值）


def fail(msg: str) -> None:
    print("FAIL  " + msg)
    global FAILED
    FAILED = True


FAILED = False


def eq(name: str, want, got) -> None:
    if want == got:
        print("PASS  %-46s expected=%-10s actual=%s" % (name, want, got))
    else:
        fail("%-46s expected=%s actual=%s" % (name, want, got))


def parse_cause_bits(spec: Path) -> dict[str, int]:
    text = spec.read_text()
    sec = None
    for line in text.split("\n"):
        if "（二）monitor 异常编号" in line:
            sec = []
            continue
        if sec is not None:
            if line.startswith("**（三）"):
                break
            sec.append(line)
    if not sec:
        raise SystemExit("check_prevcfx: spec §5.2「monitor 异常编号」表 not found")
    bits = {}
    for line in sec:
        m = re.match(r"^\|\s*`?([A-Z0-9_]+)`?\s*\|\s*(\d+)\s*\|", line.strip())
        if m:
            bits[m.group(1)] = int(m.group(2))
    for need in ("CFXTRAP", "CFXESC"):
        if need not in bits:
            raise SystemExit("check_prevcfx: %s not in the cause table" % need)
    return bits


def parse_cfx_codes(contract: Path) -> dict[str, int]:
    text = contract.read_text()
    power = re.search(r"`cfx_power`（cfx(\d+)", text)
    hmon = re.search(r"`cfx(\d+) hmon`", text)
    if not power or not hmon:
        raise SystemExit("check_prevcfx: contract-see lacks the Tiny cfx ids")
    return {"power": int(power.group(1)), "hmon": int(hmon.group(1))}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stream", required=True, help="SYS_WRITEC 字节流")
    ap.add_argument("--spec", default=str(
        REPO / "spec/DADAO-12-SEE-主管系统运行环境.md"))
    ap.add_argument("--contract", default=str(
        REPO / ".tao/contracts/contract-see.md"))
    args = ap.parse_args()

    bits = parse_cause_bits(Path(args.spec))
    codes = parse_cfx_codes(Path(args.contract))
    print("oracle: CFXTRAP=1<<%d  CFXESC=1<<%d  cfx_power=%d  cfx_hmon=%d"
          % (bits["CFXTRAP"], bits["CFXESC"], codes["power"], codes["hmon"]))

    raw = Path(args.stream).read_bytes()
    eq("stream bytes (%d records x %d)" % (N_RECORDS, RECORD),
       N_RECORDS * RECORD, len(raw))
    if len(raw) != N_RECORDS * RECORD:
        print("check_prevcfx: stream is short/long — the guest did not reach the "
              "print (a fail-fast `__EXIT` fired)", file=sys.stderr)
        return 1

    rec = list(struct.unpack(">" + "Q" * N_RECORDS, raw))
    eq("cg5 rc1 boot value == cfx_power", codes["power"], rec[0])
    eq("cg5 rc1 RW sentinel readback", RW_SENTINEL, rec[1])
    eq("cg5 rc1 write-back readback", codes["power"], rec[2])
    eq("hmon frame cause_id == CFXTRAP", 1 << bits["CFXTRAP"], rec[3])
    eq("landing arrivals", 2, rec[4])
    eq("current-cfx frame cause_id == CFXESC", 1 << bits["CFXESC"], rec[5])
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
