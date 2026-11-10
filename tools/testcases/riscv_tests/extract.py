#!/usr/bin/env python3
"""Extract the RV64 riscv-tests inventory and the portable case corpus.

Provenance: the port targets the riscv-tests checkout locked by the chipyard
toolchain manifest (upstream commit 0494f954a3d8d2ca9e4972da7a01e94b6a909bce).
This script is the *refresh* tool: it reads that checkout, classifies every
RV64 ISA test file, extracts the architectural value cases we can express with
DADAO instructions, and writes the repo-tracked data:

  tests/riscv-tests/upstream-index.yaml   file list + sha256 (traceability)
  tests/riscv-tests/inventory.yaml        per-file 移植/需改/不适用 + reason
  tests/riscv-tests/cases/<suite>/<name>.yaml   portable case vectors

The committed files are self-contained: the gate and the generator never need
the upstream checkout (fresh clone reproducible).  `--check` re-derives and
compares, so a drifted re-extraction cannot pass silently.

Classification policy (task m13-integ-004):
  port    DADAO has an instruction whose value semantics match the RISC-V
          instruction, and the *architectural* value cases are mechanically
          portable.  Pipeline hazard / register-aliasing macros (BYPASS,
          SRC*_EQ_DEST, ZERODEST) are omitted: they test a RISC-V
          microarchitecture, not ISA-visible results.
  rewrite DADAO has the capability but the test body/observation has to be
          re-expressed (register banks, link/RAS model, load/store address
          bank, 32-bit extension, FP model, atomics via LR/SC).
  na      No DADAO counterpart (CSR/S-mode, AMO, I-cache alias, ...).
"""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys

try:
    import yaml
except ImportError:  # pragma: no cover - PyYAML is a repo dependency
    sys.stderr.write("ERROR: PyYAML is required\n")
    sys.exit(2)

REPO_ROOT = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
OUT = os.path.join(REPO_ROOT, "tests", "riscv-tests")
SUITES = ("rv64ui", "rv64um", "rv64ua", "rv64uf", "rv64ud", "rv64si")
UPSTREAM_COMMIT = "0494f954a3d8d2ca9e4972da7a01e94b6a909bce"

MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1

# ---------------------------------------------------------------------------
# Classification (per upstream file, name without .S)
# ---------------------------------------------------------------------------

PORT = {
    # rv64ui: 64-bit RR / immediate / 32-bit word forms
    "rv64ui": {
        "add", "addi", "addiw", "addw", "and", "andi", "or", "ori",
        "sll", "slli", "slliw", "sllw", "slt", "slti", "sltiu", "sltu",
        "sra", "srai", "sraiw", "sraw", "srl", "srli", "srliw", "srlw",
        "sub", "subw", "xor", "xori",
    },
    # rv64um: 64-bit product/quotient families whose 128-bit / fixed-value
    # semantics line up as well
    "rv64um": {"div", "divu", "mul", "mulh", "mulhu", "rem", "remu"},
}

NA = {
    # No AMO instruction in DADAO; AMO -> LR/SC is a different test.
    "rv64ua": {
        "amoadd_d", "amoadd_w", "amoand_d", "amoand_w", "amomax_d",
        "amomax_w", "amomaxu_d", "amomaxu_w", "amomin_d", "amomin_w",
        "amominu_d", "amominu_w", "amoor_d", "amoor_w", "amoswap_d",
        "amoswap_w", "amoxor_d", "amoxor_w",
    },
    # Supervisor CSR / S-mode / I-cache alias / misaligned fetch model.
    "rv64si": {"csr", "dirty", "icache-alias", "ma_fetch"},
}

REWRITE_REASON = {
    "rv64ui": {
        "auipc": "IP 相对立即数模型不同（DADAO `aip.si` 以 4 KiB 为单位，不提供 `lui/auipc` 组合）",
        "beq": "分支用 `br.eq`/`br.ne` 比较寄存器；测试体需重排寄存器并去掉 RISC-V x0/延迟槽假设",
        "bne": "同上（`br.eq`/`br.ne`）",
        "blt": "有序比较需 `cmp.so` + `br.n`，测试体需改写",
        "bge": "有序比较需 `cmp.so` + `br.np`/`br.p` 组合，测试体需改写",
        "bltu": "无符号比较需 `cmp.uo` + `br.n`，测试体需改写",
        "bgeu": "无符号比较需 `cmp.uo` + `br.np`/`br.p` 组合，测试体需改写",
        "fence_i": "DADAO `fence cfxHA, immu18` 是 cfx 资源域屏障，无指令取指屏障语义",
        "jal": "DADAO 链接寄存器是 RegRAS（`call`/`ret`），不是 x1/x5 通用寄存器模型",
        "jalr": "同上；间接跳转目标在 RB，且返回地址走 RAS",
        "lb": "地址操作数在 RB、结果在 RD，需重排寄存器；符号扩展规则相同",
        "lbu": "地址在 RB、结果在 RD；零扩展规则相同",
        "ld": "地址在 RB、结果在 RD；8 字节对齐约束需在测试体中显式满足",
        "lh": "地址在 RB、结果在 RD；半字符号扩展",
        "lhu": "地址在 RB、结果在 RD；半字零扩展",
        "lw": "地址在 RB、结果在 RD；32 位符号扩展用 `ld.t`",
        "lwu": "地址在 RB、结果在 RD；32 位零扩展用 `ld.ut`",
        "lui": "无 `lui`；常量用 `set.zw`/`or.w` 的 wyde-position 序列构造",
        "ma_data": "测试依赖 RISC-V 地址对齐/异常模型；DADAO 对齐异常走 cfx，需重写",
        "sb": "地址在 RB、数据在 RD；偏移 12 位有符号",
        "sd": "地址在 RB、数据在 RD；8 字节对齐",
        "sh": "地址在 RB、数据在 RD；半字存储",
        "simple": "RISC-V 冒烟程序依赖 `lui/addi` 立即数组合，需按 DADAO 重写",
        "sw": "地址在 RB、数据在 RD；32 位存储",
    },
    "rv64um": {
        "mulhsu": "无混合符号 128 位乘；需用 `mul.so`/`mul.uo` 分解合成",
        "mulw": "32 位乘积的高位扩展未在 DADAO `mul.st` 契约中规定，需显式 `ext.so 31` 验证",
        "divw": "32 位有符号除需显式符号扩展/边界派生，未纳入本轮移植",
        "divuw": "32 位无符号除需显式零扩展/边界派生，未纳入本轮移植",
        "remw": "32 位有符号余需显式符号扩展/边界派生，未纳入本轮移植",
        "remuw": "32 位无符号余需显式零扩展/边界派生，未纳入本轮移植",
    },
    "rv64ua": {
        "lrsc": "LR/SC 存在（`lr.o`/`sc.o`），但保留集/失败码语义与 RISC-V 不同，测试体需重写",
    },
    "rv64uf": {
        "fadd": "DADAO 浮点用 ft/fo 两组寄存器与 rf0 标志，测试体需按 contract-fp 重写",
        "fclass": "同上；`fclass` 映射 `ftcls`/`focls`，分类位定义需重排",
        "fcmp": "同上；比较结果编码与 RISC-V 不同",
        "fcvt": "同上；转换指令与舍入模式取自 rf0",
        "fcvt_w": "同上；整型转换边界与 NaN 语义按 contract-fp",
        "fdiv": "同上；除法/余数/开方指令族不同",
        "fmadd": "同上；FMA 指令族（ftfma/fofma）与 RISC-V 命名/寄存器不同",
        "fmin": "同上；min/max NaN 规则按 DADAO",
        "ldst": "浮点 load/store 走 RF 存取指令，地址仍在 RB",
        "move": "浮点寄存器移动/符号注入指令族不同",
        "recoding": "NaN recoding 规则按 DADAO，需重写期望值",
    },
    "rv64ud": {
        "fadd": "DADAO 64 位浮点用 fo 系列，测试体需按 contract-fp 重写",
        "fclass": "同上；`focls` 分类位定义不同",
        "fcmp": "同上；`foqcmp`/`foscmp` 结果编码不同",
        "fcvt": "同上；`fo2it`/`it2fo` 等转换族不同",
        "fcvt_w": "同上；整型转换边界与 NaN 语义不同",
        "fdiv": "同上；除法/余数/开方族不同",
        "fmadd": "同上；`fofma` 与 RISC-V 命名/寄存器不同",
        "fmin": "同上；`fomin`/`fomax` NaN 规则",
        "ldst": "浮点 load/store 走 RF 存取指令",
        "move": "浮点寄存器移动/符号注入指令族不同",
        "recoding": "NaN recoding 规则按 DADAO",
        "structural": "结构测试依赖 RISC-V FP 寄存器堆/流水模型，DADAO 无对应结构",
    },
    "rv64si": {
        "sbreak": "DADAO 用 `trap cfxHA, immu18` 产生异常，无 `sbreak` 的 S-mode 观察通道",
        "scall": "DADAO 无 S-mode ecall；系统调用走 semihosting/trap",
        "wfi": "DADAO `swym` 为空转，不是 WFI 低功耗语义",
    },
}

NA_REASON = {
    "rv64ua": "DADAO 无 AMO 指令族；用 LR/SC 循环模拟会成为另一个测试（见 `lrsc` 的需改）",
    "rv64si": "DADAO 无 CSR / S-mode / I-cache 别名模型；该测试无对应观察通道",
}

PORT_MAP = {
    "add": "`add.uo {rdhi,rdlo}` 低 64 位", "addi": "`add.uo {rdhi,rdlo}` + 立即数寄存器",
    "addiw": "`add.st`（32 位符号扩展）", "addw": "`add.st`",
    "and": "`and.o`", "andi": "`and.o` + 立即数寄存器",
    "or": "`or.o`", "ori": "`or.o` + 立即数寄存器",
    "xor": "`xor.o`", "xori": "`xor.o` + 立即数寄存器",
    "sll": "`shl.o`", "slli": "`shl.o` + 立即数寄存器", "sllw": "`shl.t` + `ext.so 31`",
    "slliw": "`shl.t` + `ext.so 31`（立即数寄存器）",
    "srl": "`shr.uo`", "srli": "`shr.uo` + 立即数寄存器", "srlw": "`shr.ut` + `ext.so 31`",
    "srliw": "`shr.ut` + `ext.so 31`（立即数寄存器）",
    "sra": "`shr.so`", "srai": "`shr.so` + 立即数寄存器", "sraw": "`shr.st`",
    "sraiw": "`shr.st`（立即数寄存器）",
    "slt": "`cmp.so` + `shr.so 63` + `and.o 1`", "sltu": "`cmp.uo` + `shr.so 63` + `and.o 1`",
    "slti": "`cmp.so` + `shr.so 63` + `and.o 1`", "sltiu": "`cmp.uo` + `shr.so 63` + `and.o 1`",
    "sub": "`sub.uo {rdhi,rdlo}` 低 64 位", "subw": "`sub.st`",
    "mul": "`mul.so {rdhi,rdlo}` 低 64 位", "mulh": "`mul.so` 高 64 位",
    "mulhu": "`mul.uo` 高 64 位", "div": "`div.so`", "divu": "`div.uo`",
    "rem": "`rem.so`", "remu": "`rem.uo`",
}

# ---------------------------------------------------------------------------
# Integer semantics (independent of the emitted assembly)
# ---------------------------------------------------------------------------

def u64(x):
    return x & MASK64


def s64(x):
    x &= MASK64
    return x - (1 << 64) if x >> 63 else x


def s32(x):
    x &= MASK32
    return x - (1 << 32) if x >> 31 else x


def _div(a, b):
    """Truncate toward zero, C99 semantics."""
    q = abs(a) // abs(b)
    return -q if (a < 0) != (b < 0) else q


def _rem(a, b):
    return a - _div(a, b) * b


def rr_value(op, a, b):
    a = u64(a)
    b = u64(b)
    if op in ("add", "addi", "addiw", "addw"):
        if op in ("addiw", "addw"):
            return u64(s32(a + b))
        return u64(a + b)
    if op in ("sub", "subw"):
        return u64(s32(a - b)) if op == "subw" else u64(a - b)
    if op in ("and", "andi"):
        return a & b
    if op in ("or", "ori"):
        return a | b
    if op in ("xor", "xori"):
        return a ^ b
    if op in ("sll", "slli"):
        return u64(a << (b & 63))
    if op in ("srl", "srli"):
        return u64(a >> (b & 63))
    if op in ("sra", "srai"):
        return u64(s64(a) >> (b & 63))
    if op in ("sllw", "slliw"):
        return u64(s32(s32(a) << (b & 31)))
    if op in ("srlw", "srliw"):
        return u64(s32((a & MASK32) >> (b & 31)))
    if op in ("sraw", "sraiw"):
        return u64(s32(s32(a) >> (b & 31)))
    if op == "slt":
        return 1 if s64(a) < s64(b) else 0
    if op in ("sltu",):
        return 1 if a < b else 0
    if op == "slti":
        return 1 if s64(a) < s64(b) else 0
    if op == "sltiu":
        return 1 if a < b else 0
    if op == "mul":
        return u64(a * b)
    if op == "mulh":
        return u64((s64(a) * s64(b)) >> 64)
    if op == "mulhu":
        return u64((a * b) >> 64)
    if op in ("div", "divu"):
        sa, sb = s64(a), s64(b)
        if b == 0:
            return MASK64
        if op == "divu":
            return u64(a // b)
        if sa == -(1 << 63) and sb == -1:
            return u64(sa)
        return u64(_div(sa, sb))
    if op in ("rem", "remu"):
        sa, sb = s64(a), s64(b)
        if b == 0:
            return a
        if op == "remu":
            return u64(a % b)
        if sa == -(1 << 63) and sb == -1:
            return 0
        return u64(_rem(sa, sb))
    raise KeyError(f"no oracle for {op}")


SIGNED_IMM_OPS = {"addi", "andi", "ori", "xori", "slti", "sltiu", "addiw"}


def sext12(x):
    """RISC-V I-type immediate: 12-bit two's complement."""
    x &= 0xFFF
    return x - 0x1000 if x & 0x800 else x


def cval(text):
    expr = text.strip()
    expr = expr.replace("__riscv_xlen", "64")
    expr = expr.replace("MASK_XLEN", "")
    expr = expr.replace("/", "//")
    return int(eval(expr, {"__builtins__": {}}, {}))


# ---------------------------------------------------------------------------
# Macro parsing
# ---------------------------------------------------------------------------

RR_RE = re.compile(
    r"TEST_RR_OP\(\s*(\d+)\s*,\s*([A-Za-z0-9_.]+)\s*,\s*([^,]+?)\s*,"
    r"\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")
IMM_RE = re.compile(
    r"TEST_IMM_OP\(\s*(\d+)\s*,\s*([A-Za-z0-9_.]+)\s*,\s*([^,]+?)\s*,"
    r"\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")
SRL_RE = re.compile(r"TEST_SRL\(\s*(\d+)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")
SRLI_RE = re.compile(r"TEST_SRLI\(\s*(\d+)\s*,\s*([^,]+?)\s*,\s*([^)]+?)\s*\)")


def _strip_comment(line):
    return line.split("#", 1)[0]


def parse_cases(path, name):
    cases = []
    with open(path, "r", encoding="utf-8") as fh:
        for raw in fh:
            line = _strip_comment(raw)
            for m in RR_RE.finditer(line):
                tc, op, res, a, b = m.groups()
                cases.append({
                    "testnum": int(tc), "form": "rr", "op": op,
                    "expected": u64(cval(res)),
                    "src1": u64(cval(a)), "src2": u64(cval(b)),
                })
            for m in IMM_RE.finditer(line):
                tc, op, res, a, imm = m.groups()
                imm_val = cval(imm)
                if op in SIGNED_IMM_OPS:
                    imm_val = sext12(imm_val)
                cases.append({
                    "testnum": int(tc), "form": "imm", "op": op,
                    "expected": u64(cval(res)),
                    "src1": u64(cval(a)), "src2": u64(imm_val),
                })
            for m in SRL_RE.finditer(line):
                tc, v, a = m.groups()
                cases.append({
                    "testnum": int(tc), "form": "rr", "op": "srl",
                    "expected": u64(u64(cval(v)) >> (cval(a) & 63)),
                    "src1": u64(cval(v)), "src2": u64(cval(a)),
                })
            for m in SRLI_RE.finditer(line):
                tc, v, a = m.groups()
                cases.append({
                    "testnum": int(tc), "form": "imm", "op": "srli",
                    "expected": u64(u64(cval(v)) >> (cval(a) & 63)),
                    "src1": u64(cval(v)), "src2": u64(cval(a)),
                })
    # A test number is unique inside one upstream file; duplicates would make
    # the exit code ambiguous.
    seen = set()
    for c in cases:
        if c["testnum"] in seen:
            raise SystemExit(f"{name}: duplicate testnum {c['testnum']}")
        seen.add(c["testnum"])
    if not cases:
        raise SystemExit(f"{name}: no portable value cases found")
    # Independent oracle cross-check of every extracted expected value.
    for c in cases:
        want = rr_value(c["op"], c["src1"], c["src2"])
        if want != c["expected"]:
            raise SystemExit(
                f"{name} test {c['testnum']}: upstream expected "
                f"0x{c['expected']:016x} != oracle 0x{want:016x}")
    cases.sort(key=lambda c: c["testnum"])
    return cases


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def read_text(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def dump_yaml(obj):
    return yaml.safe_dump(obj, sort_keys=False, allow_unicode=True,
                          default_flow_style=False, width=100)


def hx(v):
    return f"0x{v:016x}"


def build(upstream):
    isa = os.path.join(upstream, "isa")
    index = []
    inventory = []
    cases_by_file = {}
    for suite in SUITES:
        ddir = os.path.join(isa, suite)
        names = sorted(n[:-2] for n in os.listdir(ddir) if n.endswith(".S"))
        for name in names:
            path = os.path.join(ddir, name + ".S")
            rel = f"isa/{suite}/{name}.S"
            index.append({"suite": suite, "name": name,
                          "path": rel, "sha256": sha256(path)})
            if name in PORT.get(suite, set()):
                cls = "port"
                cases = parse_cases(path, f"{suite}/{name}")
                cases_by_file[(suite, name)] = cases
                reason = f"可机械移植：{PORT_MAP[name]}"
            elif name in NA.get(suite, set()):
                cls = "na"
                reason = NA_REASON[suite]
            else:
                cls = "rewrite"
                reason = REWRITE_REASON.get(suite, {}).get(
                    name, "测试体需按 DADAO 寄存器/指令模型重写")
            inventory.append({
                "suite": suite,
                "name": name,
                "class": cls,
                "dadao": PORT_MAP.get(name, "—") if cls == "port" else "—",
                "reason": reason,
                "cases": (f"cases/{suite}/{name}.yaml" if cls == "port" else None),
            })
    return index, inventory, cases_by_file


def write_all(upstream, check=False):
    index, inventory, cases_by_file = build(upstream)
    files = {
        os.path.join(OUT, "upstream-index.yaml"): dump_yaml({
            "upstream": "riscv-software-src/riscv-tests",
            "commit": UPSTREAM_COMMIT,
            "suites": list(SUITES),
            "files": index,
        }),
        os.path.join(OUT, "inventory.yaml"): dump_yaml({
            "schema": "riscv-tests-port-inventory-v1",
            "upstream_commit": UPSTREAM_COMMIT,
            "classes": {"port": "可移植", "rewrite": "需改",
                        "na": "不适用"},
            "entries": inventory,
        }),
    }
    for (suite, name), cases in cases_by_file.items():
        files[os.path.join(OUT, "cases", suite, name + ".yaml")] = dump_yaml({
            "upstream": f"isa/{suite}/{name}.S",
            "upstream_sha256": next(
                f["sha256"] for f in index
                if f["suite"] == suite and f["name"] == name),
            "note": "只含架构可见的值用例；BYPASS/SRC*_EQ_DEST/ZERODEST "
                    "属 RISC-V 微架构/寄存器别名测试，未移植。",
            "cases": [{**c, "expected": hx(c["expected"]),
                       "src1": hx(c["src1"]), "src2": hx(c["src2"])}
                      for c in cases],
        })
    drift = []
    for path, text in files.items():
        if check:
            if not os.path.isfile(path) or read_text(path) != text:
                drift.append(os.path.relpath(path, REPO_ROOT))
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
    if check:
        if drift:
            print("extract: FAIL (stale files)")
            for p in drift:
                print("  " + p)
            return 1
        print(f"extract: PASS ({len(index)} upstream file(s), "
              f"{len(inventory)} inventory row(s), "
              f"{len(cases_by_file)} case file(s))")
        return 0
    print(f"extract: wrote {len(index)} upstream file(s), "
          f"{len(inventory)} inventory row(s), {len(cases_by_file)} case file(s)")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--upstream", default=os.environ.get("RISCV_TESTS_DIR"),
                    help="riscv-tests checkout (env RISCV_TESTS_DIR); "
                         "required for refresh and --check")
    ap.add_argument("--check", action="store_true",
                    help="re-derive and compare with committed data")
    args = ap.parse_args(argv)
    if not args.upstream or not os.path.isdir(os.path.join(args.upstream, "isa")):
        sys.stderr.write("extract: ERROR: --upstream / RISCV_TESTS_DIR must "
                         "point at a riscv-tests checkout\n")
        return 2
    return write_all(args.upstream, check=args.check)


if __name__ == "__main__":
    sys.exit(main())
