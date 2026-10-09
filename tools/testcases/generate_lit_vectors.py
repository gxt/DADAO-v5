#!/usr/bin/env python3
"""generate_lit_vectors.py — 机械生成 lit MC 编码用例（TESTCASES-037t）。

**Spec-first / 禁反填（硬约束）**：本脚本的期望编码**只**从
``contracts/opcodes.yaml``（``op``/``value``/``mask``/``fields`` + 下述
确定性操作数赋值规则）机械派生，**从不**调用任何外部工具（本脚本
仅用标准库 + PyYAML，不启动子进程）——因此**任何期望值都不可能
从实现反填**。生成物由 ``llvm-mc``（被测实现）执行校验，方向为
「契约 → 期望」，而非「实现 → 期望」。

真源遍历（机械、无人工挑拣）：
  遍历 ``contracts/opcodes.yaml`` **全部**记录（按 ``(format, id)`` 排序），逐条
  生成一个用例；覆盖无法以「隐藏记录」方式被裁掉（生成器对**记录总数**与
  **可汇编记录数**现场统计并打印）。

输出（随产物入库，可重跑、幂等）：
  1. ``tests/llvm/lit/MC/DADAO/gen-fast.s``：**受控子集**（每个「操作数形态」
     取排序后首条记录），随既有 ``check-lit`` 进 ``make check``。
  2. ``tests/llvm/lit/MC/DADAO-gen/{lit.cfg.py,gen-*.s}``：**全量档**，由
     opt-in 目标 ``make check-lit-full`` 承载，**不进** ``make check``。

计数不写死：脚本只**现场统计**并打印，不把具体数字写入源码/文档。
"""

import os
import sys

try:
    import yaml as _yaml
except ImportError:  # pragma: no cover
    sys.exit("ERROR: PyYAML 未安装。运行: pip install pyyaml")

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OPCODES = os.path.join(REPO, "contracts", "opcodes.yaml")

GENERATOR_PATH = "tools/testcases/generate_lit_vectors.py"
FAST_FILE = os.path.join(REPO, "tests", "llvm", "lit", "MC", "DADAO", "gen-fast.s")
FULL_DIR = os.path.join(REPO, "tests", "llvm", "lit", "MC", "DADAO-gen")

# ── 操作数形态分类（用于「受控子集」机械选取；不手工挑拣）──────────────
# orri 的「多寄存器块赋值/格式转换」形态：目的/源均为 {start:end} 组，
# immu6 = 连续寄存器个数。其余 orri 为「立即数」形态。
ORRI_BLOCK = {
    "rd2rd", "rd2ra", "ra2rd", "rb2rb", "rd2rb", "rb2rd", "rd2rf", "rf2rd",
    "ft2fo", "ft2ft", "fo2ft", "fo2fo", "ftcls", "focls",
    "it2ft", "io2ft", "ut2ft", "uo2ft", "it2fo", "io2fo", "ut2fo", "uo2fo",
    "ft2it", "ft2io", "ft2ut", "ft2uo", "fo2it", "fo2io", "fo2ut", "fo2uo",
}
# ftroot/foroot：spec §7 用「标量 3 操作数」形态，immu6 = n（仅 n=2）。
ORRI_ROOTN = {"ftroot", "foroot"}

# 名字 → 位域（helper）
def _lo_hi(bits):
    inner = bits.strip().strip("[]")
    hi, lo = inner.split(":")
    return int(lo), int(hi)


def _field(rec, name):
    for f in rec["fields"]:
        if f["name"] == name:
            return f
    raise KeyError("record %s has no field %s" % (rec["id"], name))


def _reg(bank, num):
    return "%s%d" % (bank, num)


def _encode(rec, assigns):
    """word = value | Σ(field_value << lo)；assigns: {field_name: value}。"""
    value = rec["value"]
    word = int(value, 16) if isinstance(value, str) else int(value)
    for name, val in assigns.items():
        f = _field(rec, name)
        lo, hi = _lo_hi(f["bits"])
        width = hi - lo + 1
        word |= (int(val) & ((1 << width) - 1)) << lo
    return word & 0xFFFFFFFF


def _be_bytes(word):
    return " ".join("%02x" % ((word >> (8 * (3 - i))) & 0xFF) for i in range(4))


def _align_of(rec):
    """从 legality 中提取对齐（`aligned(N)`）；无则 1。"""
    for leg in rec.get("legality") or []:
        if leg.startswith("aligned("):
            return int(leg[len("aligned("):-1])
    return 1


# --------------------------------------------------------------------------
# 逐 format 生成「规范操作数文本 + 字段赋值」
# --------------------------------------------------------------------------
def _build_positive(rec):
    """返回 (asm_text, assigns, shape_key)；无法以确定形态表达则抛 ValueError。"""
    fmt = rec["format"]
    mn = rec["mnemonic"]
    fields = rec["fields"]

    if fmt == "iiii":
        imm = 12 >> 2                      # 字节偏移 12
        return "%s [rb0, 12]" % mn, {"imms24": imm}, "iiii"

    if fmt == "oiii":
        if mn == "fence":
            # §5 fence 的 SBZ 约束：immu18[17:12]=[11:6]=[5:4]=0
            return "fence 0", {"immu18": 0}, "oiii-fence"
        return "swym 8", {"immu18": 8}, "oiii-swym"

    if fmt == "ciii":
        if mn == "escape":
            return ("escape cfx63, [excp_cause_ip, 8]",
                    {"cfxha": 63, "imms18": 8 >> 2}, "ciii-escape")
        return "trap cfx63, 1", {"cfxha": 63, "immu18": 1}, "ciii-trap"

    if fmt == "crrr":
        return ("%s cfx63, cg8, rc1, rd8" % mn,
                {"cfxha": 63, "cghb": 8, "rchc": 1, "rdhd": 8}, "crrr")

    if fmt == "rwii":
        dst = fields[0]
        return ("%s %s, wp1, 0x1234" % (mn, _reg(dst["bank"], 8)),
                {dst["name"]: 8, "wpN": 1, "immu16": 0x1234}, "rwii")

    if fmt == "riii":
        f0 = fields[0]
        if mn == "add.si":
            return ("add.si %s, 8" % _reg(f0["bank"], 8),
                    {f0["name"]: 8, "imms18": 8}, "riii-alu")
        if mn == "ret":
            return "ret rd8, 8", {"rdha": 8, "imms18": 8}, "riii-ret"
        # br.*（条件组 + [rb0, 字节偏移]）
        return ("%s {%s}?, [rb0, 12]" % (mn, _reg(f0["bank"], 8)),
                {f0["name"]: 8, "imms18": 12 >> 2}, "riii-branch")

    if fmt == "rrrr":
        if mn in ("add.uo", "add.so", "sub.uo", "sub.so", "mul.uo", "mul.so"):
            a, b, c, d = fields
            return ("%s {%s, %s}, %s, %s" % (mn, _reg(a["bank"], 8),
                                             _reg(b["bank"], 9),
                                             _reg(c["bank"], 10),
                                             _reg(d["bank"], 11)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 10, d["name"]: 11},
                    "rrrr-dst2")
        if mn in ("cs.eq", "cs.ne"):
            a, b, c, d = fields
            return ("%s {%s, %s}?, %s, %s" % (mn, _reg(a["bank"], 8),
                                              _reg(b["bank"], 9),
                                              _reg(c["bank"], 10),
                                              _reg(d["bank"], 11)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 10, d["name"]: 11},
                    "rrrr-cs2")
        if mn in ("cs.n", "cs.z", "cs.p"):
            a, b, c, d = fields
            return ("%s {%s}?, %s, %s, %s" % (mn, _reg(a["bank"], 8),
                                              _reg(b["bank"], 9),
                                              _reg(c["bank"], 10),
                                              _reg(d["bank"], 11)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 10, d["name"]: 11},
                    "rrrr-cs1")
        raise ValueError("unhandled rrrr mnemonic %s" % mn)

    if fmt == "rrii":
        if mn in ("jump", "call"):
            a, b, c = fields
            return ("%s [%s, %s, 96]" % (mn, _reg(a["bank"], 8),
                                         _reg(b["bank"], 9)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 96 >> 2}, "rrii-jump")
        if mn.startswith("cmp."):
            a, b, c = fields
            return ("%s %s, %s, 1" % (mn, _reg(a["bank"], 8), _reg(b["bank"], 9)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 1}, "rrii-cmp")
        if mn.startswith("br."):
            a, b, c = fields
            return ("%s {%s, %s}?, [rb0, 16]" % (mn, _reg(a["bank"], 8),
                                                 _reg(b["bank"], 9)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 16 >> 2}, "rrii-branch")
        # ld./st.*（访存：dst/src, [rb, 字节偏移]）
        if mn.startswith(("ld.", "st.")):
            a, b, c = fields
            imm = _align_of(rec)
            return ("%s %s, [rb9, %d]" % (mn, _reg(a["bank"], 8), imm),
                    {a["name"]: 8, b["name"]: 9, c["name"]: imm}, "rrii-mem")
        raise ValueError("unhandled rrii mnemonic %s" % mn)

    if fmt == "rrri":
        a, b, c, d = fields       # 组起始, rb 基址, rd 偏移, immu6=count
        return ("%s {%s}, [rb0, rd9]" % (mn, _reg(a["bank"], 8)),
                {a["name"]: 8, b["name"]: 0, c["name"]: 9, d["name"]: 1},
                "rrri")

    if fmt == "orrr":
        a, b, c = fields
        return ("%s %s, %s, %s" % (mn, _reg(a["bank"], 8), _reg(b["bank"], 9),
                                   _reg(c["bank"], 10)),
                {a["name"]: 8, b["name"]: 9, c["name"]: 10}, "orrr")

    if fmt == "orri":
        a, b, c = fields
        if mn in ORRI_ROOTN:
            # ftroot/foroot rfHB, rfHC, n（仅 n=2）
            return ("%s %s, %s, 2" % (mn, _reg(a["bank"], 8), _reg(b["bank"], 9)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 2}, "orri-rootn")
        if mn in ORRI_BLOCK:
            # {dst:…}, {src:…}，count=1
            return ("%s {%s}, {%s}" % (mn, _reg(a["bank"], 8), _reg(b["bank"], 9)),
                    {a["name"]: 8, b["name"]: 9, c["name"]: 1}, "orri-block")
        # 立即数形态：ext./shr./shl. dst, src, imm
        return ("%s %s, %s, 1" % (mn, _reg(a["bank"], 8), _reg(b["bank"], 9)),
                {a["name"]: 8, b["name"]: 9, c["name"]: 1}, "orri-imm")

    raise ValueError("unsupported format %s (id=%s)" % (fmt, rec["id"]))


def _is_negative(rec):
    """scope: excluded 且**汇编器不实现** ⇒ 反例（须显式拒绝）；fence 例外（可汇编）。"""
    return rec.get("scope") == "excluded" and rec["mnemonic"] != "fence"


def _negative_text(rec):
    fmt = rec["format"]
    mn = rec["mnemonic"]
    if fmt == "orrr":          # lr（rd, [rb, imm]）/ sc（rd, rd, [rb, imm]）——spec §5
        if mn.startswith("sc_"):
            return "%s rd8, rd9, [rb1, 0]" % mn
        return "%s rd9, [rb1, 0]" % mn
    if fmt == "crii":          # cfxld/cfxst：cfxHA, [rb, imm]
        return "%s cfx63, [rb2, 1]" % mn
    raise ValueError("no negative form for %s" % rec["id"])


def build_case(rec):
    """返回 dict(id, mnemonic, format, scope, spec_cite, kind, shape, asm|None, word|None)。"""
    base = {
        "id": rec["id"],
        "mnemonic": rec["mnemonic"],
        "format": rec["format"],
        "scope": rec.get("scope", ""),
        "spec_cite": rec.get("spec_cite", ""),
    }
    if _is_negative(rec):
        base.update(kind="negative", shape="excluded",
                    asm=_negative_text(rec), word=None)
        return base
    asm, assigns, shape = _build_positive(rec)
    base.update(kind="positive", shape=shape, asm=asm,
                word=_encode(rec, assigns))
    return base


# --------------------------------------------------------------------------
# 渲染
# --------------------------------------------------------------------------
_RUN_OBJ = (
    "; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t\n"
    "; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | "
    "%FileCheck %s --check-prefix=OBJ\n"
    "; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | "
    "%FileCheck %s --check-prefix=ASM\n"
)


def _header(kind, source, extra=""):
    bar = "; " + "=" * 70 + "\n"
    return (
        bar
        + "; GENERATED by %s — DO NOT EDIT\n" % GENERATOR_PATH
        + "; %s\n" % kind
        + "; 期望编码机械派生自 contracts/opcodes.yaml（op/value/mask/fields）；\n"
        + "; 无 llvm-mc/llc/QEMU 反填。重跑: python3 %s\n" % GENERATOR_PATH
        + "; source: %s\n" % source
        + extra
        + bar
    )


def _render_positive(cases):
    """返回单个 .s 文件内容（正例：llvm_mc→obj→objdump→FileCheck OBJ + ASM 往返）。"""
    out = [_header("lit MC 编码正例", "contracts/opcodes.yaml", _RUN_OBJ), "\n.text\n"]
    for c in cases:
        mnem = c["mnemonic"]
        word = c["word"]
        out.append("\n; @src %s %08x | %s\n"
                   % (c["id"], word, c["spec_cite"]))
        out.append("; OBJ: {{[0-9a-f]+:}} %s{{.*}}%s\n" % (_be_bytes(word), mnem))
        out.append("; ASM: %s\n" % c["asm"])
        out.append("%s\n" % c["asm"])
    return "".join(out)


def _render_negative(cases):
    out = [_header("lit MC 编码反例（scope: excluded 且汇编器不实现 ⇒ 须显式拒绝）",
                   "contracts/opcodes.yaml")]
    # 每个反例一条独立 RUN（echomac 单条 → 必须报 unrecognized）
    for c in cases:
        out.append("; RUN: echo '%s' | %%not %%llvm_mc --triple=dadao-unknown-elf "
                   "-filetype=obj -o /dev/null 2>&1 | "
                   "%%FileCheck %%s --check-prefix=UNREC\n" % c["asm"])
    out.append("\n.text\n")
    out.append("; UNREC: error: unrecognized instruction mnemonic\n")
    for c in cases:
        out.append("\n; @src %s | %s\n" % (c["id"], c["spec_cite"]))
        out.append("; %s（scope: excluded，汇编器 MUST 拒绝）\n" % c["asm"])
    return "".join(out)


# --------------------------------------------------------------------------
# 校验（生成器自检：捕获重复词/歧义，避免生成不可判定的 OBJ 行）
# --------------------------------------------------------------------------
def _load_records():
    with open(OPCODES, "r", encoding="utf-8") as fh:
        recs = _yaml.safe_load(fh)
    if not isinstance(recs, list):
        raise SystemExit("opcodes.yaml 顶层必须是列表")
    return recs


def _selfcheck(cases):
    """(word&mask)==value 且全表唯一匹配；否则该 OBJ 行不可判定 ⇒ 生成器 MUST 失败。"""
    recs = _load_records()
    table = [(r["id"], r["mnemonic"], int(r["mask"], 16), int(r["value"], 16))
             for r in recs]
    for c in cases:
        if c["kind"] != "positive":
            continue
        m = [t for t in table if (c["word"] & t[2]) == t[3]]
        if len(m) != 1:
            raise SystemExit(
                "generator self-check FAIL: %s word=0x%08X matched %d records %s"
                % (c["id"], c["word"], len(m), [x[0] for x in m]))
        if m[0][1] != c["mnemonic"]:
            raise SystemExit(
                "generator self-check FAIL: %s word=0x%08X matched mnemonic %s"
                % (c["id"], c["word"], m[0][1]))


LIT_CFG = '''# -*- Python -*-
# GENERATED suite config for tests/llvm/lit/MC/DADAO-gen (TESTCASES-037t).
# Resolves llvm-mc/llvm-objdump/FileCheck from the install-root host toolchain.
import os
import sys
import lit.formats

config.name = "DADAO-MC-gen"
config.test_source_root = os.path.dirname(__file__)
config.suffixes = [".s"]
config.test_format = lit.formats.ShTest(False)

here = os.path.dirname(os.path.abspath(__file__))
root = here
while (root != os.path.dirname(root)
       and not os.path.isfile(os.path.join(root, "manifests",
                                           "install-dirs.lock.toml"))):
    root = os.path.dirname(root)
sys.path.insert(0, os.path.join(root, "tools", "infra"))
import paths as dadao_paths

tools_dir = getattr(config, "llvm_tools_dir", None) or os.environ.get(
    "LLVM_TOOLS_DIR", "") or str(dadao_paths.host_toolchain_bin())
if not os.path.isdir(tools_dir):
    sys.exit("lit.cfg.py: could not locate LLVM tools directory; run 'make install-host' first")
tools_dir = os.path.abspath(tools_dir)
for tool in ("llvm-mc", "llvm-objdump", "llvm-readobj", "FileCheck", "not"):
    config.substitutions.append(("%" + tool.replace("-", "_"), os.path.join(tools_dir, tool)))

config.test_exec_root = str(dadao_paths.test_artifacts_dir() / "lit-output" / config.name)
os.makedirs(config.test_exec_root, exist_ok=True)
'''


def generate():
    recs = _load_records()
    recs_sorted = sorted(recs, key=lambda r: (r["format"], r["id"]))
    cases = [build_case(r) for r in recs_sorted]
    _selfcheck(cases)

    positives = [c for c in cases if c["kind"] == "positive"]
    negatives = [c for c in cases if c["kind"] == "negative"]

    # ── 全量档：按 format 分文件 ──
    os.makedirs(FULL_DIR, exist_ok=True)
    with open(os.path.join(FULL_DIR, "lit.cfg.py"), "w", encoding="utf-8") as fh:
        fh.write(LIT_CFG)

    by_fmt = {}
    for c in positives:
        by_fmt.setdefault(c["format"], []).append(c)
    written = []
    for fmt in sorted(by_fmt):
        path = os.path.join(FULL_DIR, "gen-%s.s" % fmt)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_render_positive(by_fmt[fmt]))
        written.append(path)
    if negatives:
        path = os.path.join(FULL_DIR, "gen-excluded.s")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(_render_negative(negatives))
        written.append(path)

    # ── 快档：每个 shape 取排序后首条（受控子集，机械选取）──
    seen = set()
    fast = []
    for c in positives:
        if c["shape"] not in seen:
            seen.add(c["shape"])
            fast.append(c)
    os.makedirs(os.path.dirname(FAST_FILE), exist_ok=True)
    with open(FAST_FILE, "w", encoding="utf-8") as fh:
        fh.write(_render_positive(fast))

    return cases, positives, negatives, fast, written


def main():
    cases, positives, negatives, fast, written = generate()
    print("generate_lit_vectors: opcodes.yaml 记录 %d 条（现场统计）" % len(cases))
    print("  正例（可汇编）：%d 条" % len(positives))
    print("  反例（scope: excluded，不实现）：%d 条" % len(negatives))
    print("  shape 类：%d 个（快档取每类首条 → %d 条）" % (len(set(c["shape"] for c in positives)), len(fast)))
    print("  全量档文件：")
    for p in written:
        print("    %s" % os.path.relpath(p, REPO))
    print("  快档文件：%s" % os.path.relpath(FAST_FILE, REPO))
    per_fmt = {}
    for c in positives:
        per_fmt[c["format"]] = per_fmt.get(c["format"], 0) + 1
    print("  按 format：%s" % ", ".join("%s=%d" % (k, per_fmt[k]) for k in sorted(per_fmt)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
