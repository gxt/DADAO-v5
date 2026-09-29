#!/usr/bin/env python3
"""validate_interp_v5.py —— 在 tests/vectors/isa/*.yaml 上运行 dadao_interp_v5.py。

裁决桶（对应 0628 验证器的 PASS/FAIL/SKIP 合约）：
  PASS          golden 与向量一致（异常 + 状态 + pc）
  FAIL          真分歧（需分类：golden 缺陷 vs 向量缺陷）
  SKIP-deferred 向量 status == deferred（规范尚未提取）
  SKIP-machine  向量期望 UNMAPPED（测试机层，ADR-0004 D5.6，
                ISA golden 刻意不建模——与 0628 的 SKIP-harness 同理弃权）

按类别处理：
  encoding  只做译码：向量断言的是编码层性质
            （指令字匹配 opcodes.yaml 掩码/值、字段合法、无 ILLI），
            不执行。若向量钉住异常（ILLI/UNDI 类编码，如保留字），
            只比较 golden 的"译码 + 静态合法性"结果；刻意不做动态执行
            （避免在零状态寄存器上凭空制造向量本意的异常，如除零）。
  legality / overlap（含期望异常）+ reserved.yaml：走正常单步运行路径；
            经 decode + check_legality + _exec 核验 UNDI/ILLI，
            除异常外不比较状态。
  semantic / boundary / overlap（含期望状态）：完整单步运行；
            比较 expected_fault、expected_state.{rd,rb,ra,rf,memory}
            与 expected_pc（对退役时刻 rb0/下一PC，见 schema.md）。

内存比较遵循 schema.md §input_state.memory[].value 合约：
期望的内存 value 是地址处 N 字节大端值，N = 该向量的访问位宽
（由指令助记符解出）。
"""

import glob
import os
import sys

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dadao_interp_v5 import (MASK64, Fault, Unsupported, build_state,  # noqa: E402
                             check_legality, decode, mem_width_for, run)

VECTORS_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))), 'tests', 'vectors', 'isa')


def _hex(v):
    return v if isinstance(v, str) else f'0x{v:X}'


def _parse_int(v):
    return int(v, 16) if isinstance(v, str) else v


def compare_state(st, expected, width):
    """Return list of mismatch strings (empty == agree)."""
    bad = []
    expected = expected or {}
    for bank in ('rd', 'rb', 'ra', 'rf'):
        want = expected.get(bank) or {}
        have = getattr(st, bank)
        for name, val in want.items():
            idx = int(name[2:])
            hv, wv = have[idx] & MASK64, _parse_int(val) & MASK64
            if hv != wv:
                bad.append(f'{bank}{idx}: golden=0x{hv:016X} vector={_hex(val)}')
    for entry in (expected.get('memory') or []):
        addr = _parse_int(entry['address'])
        w = entry.get('width', width)
        hv = st.load_mem(addr, w)
        wv = _parse_int(entry['value']) & ((1 << (8 * w)) - 1)
        if hv != wv:
            bad.append(f'mem[0x{addr:X}]+{w}: golden=0x{hv:X} vector={_hex(entry["value"])}')
    return bad


def check_vector(t, fname, idx):
    """Return (bucket, detail)."""
    tag = f'{fname}#{idx} {t["insn"]} {t["encoding"]["word"]} [{t["class"]}]'
    if t.get('status') == 'deferred' or t.get('deferred_reason'):
        return 'SKIP-deferred', f'{tag} :: {t.get("deferred_reason")}'
    if (t.get('expected_fault') or '').upper() == 'UNMAPPED':
        return 'SKIP-machine', f'{tag} :: UNMAPPED is test-machine layer (D5.6)'
    word = _parse_int(t['encoding']['word'])
    want_fault = t.get('expected_fault')

    # — encoding class: decode + static legality only, no execution —
    if t.get('class') == 'encoding':
        try:
            rec, f = decode(word)
        except Fault as ex:
            if want_fault == ex.kind:
                return 'PASS', ''
            return 'FAIL', f'{tag} :: decode fault {ex.kind}, vector wants {want_fault}'
        if rec.get('excluded_m1'):
            got = 'ILLI'
        else:
            try:
                check_legality(rec, f)
                got = None
            except Fault as ex:
                got = ex.kind
        if got == want_fault:
            return 'PASS', ''
        return 'FAIL', (f'{tag} :: static legality={got}, '
                        f'vector wants {want_fault}')

    # — all other classes: full single-step run —
    try:
        st, got_fault = run(word, t.get('input_state') or {})
    except Unsupported as ex:
        return 'FAIL', f'{tag} :: golden Unsupported: {ex}'
    if got_fault != want_fault:
        return 'FAIL', (f'{tag} :: fault golden={got_fault} '
                        f'vector={want_fault}')
    if got_fault is not None:
        return 'PASS', ''                       # fault vectors: no state check
    try:
        rec, _ = decode(word)
        width = mem_width_for(rec)
    except Fault:                               # unreachable (run decoded OK)
        width = 8
    bad = compare_state(st, t.get('expected_state'), width)
    if t.get('expected_pc') is not None:
        want_pc = _parse_int(t['expected_pc'])
        if st.pc_next != want_pc:
            bad.append(f'pc: golden=0x{st.pc_next:X} vector={t["expected_pc"]}')
    if bad:
        return 'FAIL', f'{tag} :: ' + '; '.join(bad)
    return 'PASS', ''


def main(paths=None):
    paths = paths or sorted(glob.glob(os.path.join(VECTORS_DIR, '*.yaml')))
    buckets = {'PASS': 0, 'FAIL': 0, 'SKIP-deferred': 0, 'SKIP-machine': 0}
    failures, skips = [], []
    per_file = {}
    for path in paths:
        fname = os.path.basename(path)
        vecs = yaml.safe_load(open(path))
        fstat = {'PASS': 0, 'FAIL': 0, 'SKIP': 0}
        for i, t in enumerate(vecs):
            bucket, detail = check_vector(t, fname, i)
            buckets[bucket] += 1
            if bucket == 'PASS':
                fstat['PASS'] += 1
            elif bucket == 'FAIL':
                fstat['FAIL'] += 1
                failures.append(detail)
            else:
                fstat['SKIP'] += 1
                skips.append((bucket, detail))
        per_file[fname] = fstat
    print(f'{"file":28s} {"PASS":>5s} {"FAIL":>5s} {"SKIP":>5s}')
    for fname, s in per_file.items():
        print(f'{fname:28s} {s["PASS"]:5d} {s["FAIL"]:5d} {s["SKIP"]:5d}')
    print('-' * 48)
    tot = sum(buckets.values())
    print(f'TOTAL {tot}: PASS={buckets["PASS"]} FAIL={buckets["FAIL"]} '
          f'SKIP-deferred={buckets["SKIP-deferred"]} '
          f'SKIP-machine={buckets["SKIP-machine"]}')
    if failures:
        print(f'\nFAILURES ({len(failures)}):')
        for d in failures:
            print('  ' + d)
    if skips:
        print(f'\nSKIPS ({len(skips)}):')
        for b, d in skips:
            print(f'  [{b}] {d}')
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:] or None))
