#!/usr/bin/env python3
"""Generate the complete DADAO assembly-instruction list.

See ``docs/spec/assembly-list.md`` (generated) and
``docs/spec/component-patching.md`` (spec-writing conventions).

Sources
-------
* ``contracts/opcodes.yaml`` -- the authoritative 256-entry encoding table
  (178 M1 + 78 ``excluded_m1``), with per-field ``role``/``bank``.

Derivation rules (validated against ``tests/lit/MC/Dadao/*.s``)
---------------------------------------------------------------
* operands are the fields whose ``role`` is one of dst/src/imm/wyde_pos/
  cfxcode/cfx_cg/cfx_rc; ``minor_op`` fields are already encoded in the
  mnemonic and are **not** operands;
* split immediate fields (``imms18_hi/_mid/_lo``, ``immu24_b*``, ...) merge
  into one immediate operand;
* a concrete example line is built per instruction and then **verified** by
  assembling it with ``llvm-mc``.
"""
from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
OPCODES = ROOT / "contracts/opcodes.yaml"
LIT_DIR = ROOT / "tests/lit/MC/Dadao"
DEFAULT_MC = ROOT / ".work/build/llvm/bin/llvm-mc"
TRIPLE = "dadao-unknown-elf"

OPERAND_ROLES = {"dst", "src", "imm", "wyde_pos", "cfxcode", "cfx_cg", "cfx_rc"}
SPLIT_SUFFIX = re.compile(r"^(imms?\d+|immu?\d+)_(?:hi|mid|lo|b\d+_\d+)$")

# Immediate width/signedness from the field base name (e.g. imms18 -> s18).
IMM_RE = re.compile(r"^imm([us]?)(\d+)$")

# Concrete example operands per role, tried in order until one assembles.
EXAMPLES = {
    "rd": ["rd8", "rd9", "rd10", "rd11", "rd1", "rd2"],
    "rb": ["rb2", "rb3", "rb1", "rb0"],
    "ra": ["ra1", "ra2"],
    "rf": ["rf2", "rf3"],
}
IMM_EXAMPLE = {"immu6": "1", "immu12": "1", "immu16": "0x1234", "immu18": "1",
               "immu24": "1", "imms12": "1", "imms18": "1", "imms24": "1",
               "wpN": "0"}


def base_imm(name: str) -> str:
    m = SPLIT_SUFFIX.match(name)
    return m.group(1) if m else name


def imm_range(name: str) -> str:
    m = IMM_RE.match(name)
    if not m:
        return "0..3 (wyde position)" if name == "wpN" else "—"
    signed, bits = m.group(1) == "s", int(m.group(2))
    if signed:
        return f"s{bits}: {-(1 << (bits - 1))}..{(1 << (bits - 1)) - 1}"
    return f"u{bits}: 0..{(1 << bits) - 1}"


def operands(entry: dict) -> list[dict]:
    out = []
    for field in entry.get("fields", []):
        role = field.get("role")
        if role not in OPERAND_ROLES:
            continue
        name = base_imm(field["name"])
        if role == "wyde_pos":
            kind, bank = "wpN", None
        elif role == "cfxcode":
            kind, bank = "cfx", None
        elif role in ("cfx_cg", "cfx_rc"):
            kind, bank = "cfx", None
        else:
            bank = field.get("bank")
            kind = "imm" if (bank == "imm" or name.startswith("imm")) else "reg"
        if out and out[-1]["kind"] == kind == "imm":
            continue
        out.append({"kind": kind, "bank": bank, "name": name})
    return out


def template(entry: dict, ops: list[dict]) -> str:
    parts = []
    for op in ops:
        if op["kind"] == "imm":
            parts.append(op["name"])
        elif op["kind"] == "wpN":
            parts.append("wpN")
        elif op["kind"] == "cfx":
            parts.append("cfx_<name>")
        else:
            parts.append(f"{op['bank']}N")
    if not parts:
        return entry["mnemonic"]
    return f"{entry['mnemonic']} " + ", ".join(parts)


def example_line(entry: dict, ops: list[dict], attempt: int) -> str:
    parts = []
    for op in ops:
        if op["kind"] == "imm":
            parts.append(IMM_EXAMPLE.get(op["name"], "1"))
        elif op["kind"] == "wpN":
            parts.append("0")
        elif op["kind"] == "cfx":
            parts.append("cfx_power")
        else:
            pool = EXAMPLES.get(op["bank"], ["rd8"])
            parts.append(pool[attempt % len(pool)])
    if not parts:
        return entry["mnemonic"]
    return f"{entry['mnemonic']} " + ", ".join(parts)


def assemble(line: str, mc: Path) -> tuple[bool, str]:
    with tempfile.NamedTemporaryFile("w", suffix=".s", delete=False) as handle:
        handle.write(line + "\n")
        path = Path(handle.name)
    try:
        result = subprocess.run(
            [str(mc), f"--triple={TRIPLE}", "-filetype=asm", str(path)],
            capture_output=True, text=True,
        )
        return result.returncode == 0, (result.stderr.strip().splitlines() or [""])[0]
    finally:
        path.unlink(missing_ok=True)


def lit_coverage() -> dict[str, str]:
    covered: dict[str, str] = {}
    for lit in sorted(LIT_DIR.glob("*.s")):
        for line in lit.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("."):
                continue
            mnemonic = line.split()[0]
            covered.setdefault(mnemonic, lit.name)
    return covered


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mc", default=str(DEFAULT_MC))
    parser.add_argument("-o", "--output", default=str(ROOT / "docs/spec/assembly-list.md"))
    args = parser.parse_args()

    mc = Path(args.mc)
    entries = yaml.safe_load(OPCODES.read_text())
    lit = lit_coverage()

    by_format: dict[str, list[dict]] = {}
    for entry in entries:
        by_format.setdefault(entry["format"], []).append(entry)

    rows = []
    ok = failed = 0
    for fmt in sorted(by_format):
        rows.append(f"\n### `{fmt}`（{len(by_format[fmt])} 条）\n")
        rows.append("| insn | 汇编形式（模板） | 汇编形式（示例） | 操作数（role/bank） | 立即数范围 | op/mask/value | 范围 | lit | llvm-mc |")
        rows.append("|---|---|---|---|---|---|---|---|---|")
        for entry in by_format[fmt]:
            ops = operands(entry)
            tmpl = template(entry, ops)
            detail = ", ".join(
                f"{o['bank'] or o['name']}:{o['kind']}" if o["kind"] == "reg" else f"{o['name']}:imm"
                for o in ops
            ) or "—"
            imm = "; ".join(
                f"{o['name']} {imm_range(o['name'])}"
                for o in ops
                if o["kind"] in ("imm", "wpN")
            ) or "—"
            ex, verified = "—", "—"
            if not entry.get("excluded_m1"):
                for attempt in range(4):
                    line = example_line(entry, ops, attempt)
                    good, err = assemble(line, mc)
                    if good:
                        ex, verified = line, "✅"
                        ok += 1
                        break
                    ex = line
                    verified = f"❌ {err[:60]}"
                else:
                    failed += 1
            else:
                ex, verified = example_line(entry, ops, 0), "— (excluded_m1)"
            scope = "excluded" if entry.get("excluded_m1") else "M1"
            rows.append(
                f"| `{entry['insn']}` | `{tmpl}` | `{ex}` | {detail} | {imm} | "
                f"`{entry['op']}` / `{entry['mask']}` / `{entry['value']}` | {scope} | "
                f"{lit.get(entry['mnemonic'], '—')} | {verified} |"
            )

    header = f"""# DADAO 汇编指令完整列表（自动生成）

> **生成器**：`tools/llvm/gen_asm_list.py`（本文件为生成物，请勿手工编辑；改生成器后重跑）
> **源**：`contracts/opcodes.yaml`（256 条 = M1 178 + `excluded_m1` 78）
> **推导规则**：操作数取 `role ∈ {{dst, src, imm, wyde_pos, cfxcode, cfx_cg, cfx_rc}}`；
> `minor_op`（165 处）已内嵌助记符，不作操作数；拆分的立即数字段合并为单一操作数。
> **验证**：M1 条目逐条送 `llvm-mc --triple={TRIPLE}` 汇编（示例列即被验证的真实行）；
> `excluded_m1` 条目 M1 未实现，仅列出规范推导形式。
> **统计**：M1 验证通过 **{ok}** 条，失败 **{failed}** 条。

## 立即数范围速查

| 字段 | 范围 |
|---|---|
| `imms12` | s12: -2048..2047 |
| `imms18` | s18: -131072..131071 |
| `imms24` | s24: -8388608..8388607 |
| `immu6` | u6: 0..63 |
| `immu12` | u12: 0..4095 |
| `immu16` | u16: 0..65535 |
| `immu18` | u18: 0..262143 |
| `immu24` | u24: 0..16777215 |
| `wpN` | wyde 位置 0..3（写作数字；`wpN` 记法不是合法汇编语法） |
"""

    out = Path(args.output)
    out.write_text(header + "\n".join(rows) + "\n", encoding="utf-8")
    print(f"gen-asm-list: {len(entries)} entries -> {out.relative_to(ROOT)}")
    print(f"gen-asm-list: M1 verified {ok}, failed {failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
