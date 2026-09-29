#!/usr/bin/env python3
"""dadao_interp_v5.py —— DADAO SimRISC 0.5.3（v5 M1）Python golden 参考模型。

独立性合约（对应 0628 tools/dadao_interp.py 的 ADR-0009 M2a）
------------------------------------------------------------------------
本解释器是对 DADAO SimRISC 0.5.3 语义的独立重新实现，其唯一来源是：
  * 译码 ← contracts/opcodes.yaml（掩码/值 + 字段布局）
  * 语义 ← .tao/knowledge/contract-isa.md（每个处理函数都注明出处章节）
           + spec/SimRISC-0*.md（合约背后的规范正文）
           + ADR-0004（ISA 未明确、留给测试机绑定的部分：
             D6.5 rb0=当前PC、D5.1 排除指令→ILLI、D5.3 SBZ→ILLI）
它刻意不读 QEMU 的 target/dadao/*、LLVM 的 Dadao/*、测试向量生成器。
tests/vectors/isa/*.yaml 的一致性与未来 `golden vs QEMU` 差分之所以有意义，
正因为三者是同一规范的独立投影；照抄任何一方都会使差分成循环论证。

覆盖范围（完整的 178 条 M1 指令；contract-isa 附录 A.1-A.6）
  * RD rrrr 双目标：add.uo/so、sub.uo/so、mul.uo/so（合约 §3.1.1/§3.1.4）
  * RD riii 原地：add.si（合约 §3.1.3）
  * RD rrii 比较：cmp.si、cmp.ui（合约 §3.2.1）
  * RD rrrr 条件赋值：cs.n、cs.z、cs.p、cs.eq、cs.ne（合约 §3.5）
  * RD/RB rwii wyde 立即数：set.ow、set.zw、or.w、andnw（合约 §3.6/§4.4）
  * orri 块拷贝：rd2rd、rb2rd、rd2rb、rb2rb、ra2rd、rd2ra
    （合约 §3.7/§4.3/§4.9.3）
  * RD load/store：ld.sb/ub/sw/uw/st/ut/o、st.b/w/t/o、ldm.*/stm.*（多个）
    （合约 §4.1）
  * RB load/store：ld.o、st.o、ldm.o、stm.o（合约 §4.2）
  * RA load/store：ld.o、st.o、ldm.o、stm.o（合约 §4.9.1/§4.9.2）
  * RB 算术：add.so/sub.so（orrr）、add.si（riii）（合约 §4.5）
  * RB 比较：cmp.uo-rb（orrr）（合约 §4.6）
  * RB PC 相对：rela.si（riii）（合约 §4.7）
  * MISC 定宽：add/sub/cmp/mul/div/rem（orrr）、and/or/xor/xnor（orrr）、
    shl/shr/ext（orrr/orri），覆盖 byte/wyde/tetra/octa
    （合约 §3.1.2/§3.1.5/§3.2.2/§3.3/§3.4）
  * 控制流：br.n/nn/z/nz/p/np、br.eq/ne、br.z/nz-rb、jump、call、ret +
    RegRAS/MemRAS（§5.6）
  * 系统指令（M1）：swym、illi、fence（合约 §7.1-§7.3）
  * 排除指令（RF/cfx/LR-SC）：译码命中 excluded_m1 记录 → ILLI
    （ADR-0004 D5.1；合约 §6/§7.4/§7.5，opcodes.yaml 记 decode:ILLI）
  * 保留编码（QFC/MISC 空白单元）：UNDI（合约 §2.9/§8.2）

关键的 0.5.3 vs 0.4.1（0628）语义差异（本模型均已实现）
  * rb0 == 当前指令地址（ADR-0004 D6.5），不是 PC+4。
    顺序 pc_next = X+4；call 压栈 X+4；rela 基址 = X & ~0xFFF。
  * add.uo/sub.uo 零扩展到 128 位（进位/借位在 rdha）；add.so/sub.so
    符号扩展到 128 位。rrrr 已无除法：div/rem 是单目标 orrr，按位宽独立
    语义（向零截断，INT_MIN/-1 → ILLI 按各宽度判定）。
  * 定宽逻辑/移位/扩展对目标寄存器读-改-写：位宽之外的位保留目标寄存器的旧值。
  * RB 加减/add.si 取完整 64 位（高 16 位 = 结果位，可用于溢出检测）；
    块拷贝双向完整 64 位。
  * add.si 是 riii 原地形式（rdha += sext18）；rela 为 rela.si（riii）。
  * RA 有单个 ld.o/st.o（rrii）；ra0 作 ld/st 目标合法。
  * swym 是 iiii 格式（op 0x77，任何 N 都按 NOP 计时）；unimp 已删除，
    由 illi 取代（oiii，op 0x00/ha 0x00，恒报 ILLI，全零指令字）。
  * 新增：br.z/br.nz-rb、fence（SBZ 检查后 NOP）、rem.*、带位移量/扩展位
    越界检查的 ext/shl/shr（shamt/hd > N → ILLI）。
详见 DESIGN.md：完整的 0.4.1-vs-0.5.3 对比，以及规范有歧义之处本模型所取
的每一种解释（D-v5-*）。

异常（精确异常，无架构副作用——合约 §9.2）
  ILLI   操作数合法性（合约 §9.1）+ 整数除零 / INT_MIN/-1（§3.1.5）
         + 位移量/扩展位越界（§3.4）+ illi（§7.2）+ 排除指令（§6/§7.4/§7.5）
  UNDI   保留编码（合约 §2.9/§8.2）
  MALIGN 非对齐 load/store（合约 §4.1.1/§4.1.2/§4.2/§4.9）
  IALIGN PC 非 4 字节对齐（合约 §2.1）
  RASOF/RASUF RegRAS/MemRAS 上溢 / 下溢（合约 §5.6）
不建模（测试机层，ADR-0004，非 ISA）：UNMAPPED（D5.6）、exit 端口、
ROM/MMU。期望 UNMAPPED 的向量是纯测试机结果；验证器对其弃权
（SKIP-machine），与 0628 的 SKIP-harness 完全一致。
"""

import os
import re
import yaml

MASK64 = (1 << 64) - 1
MASK48 = (1 << 48) - 1
MASK16 = (1 << 16) - 1
HI16 = MASK64 ^ MASK48          # bits[63:48]
MASK128 = (1 << 128) - 1

# RAM entry = the address test vectors assume for the instruction under test
# (contract-isa §5 vectors cite ADR-0004 D2.2/D6.5; schema.md §expected_pc).
DEFAULT_PC = 0xFFFF00000000

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_OPCODES_PATH = os.path.join(_REPO, 'contracts', 'opcodes.yaml')


class Fault(Exception):
    """Precise architectural exception (contract §9.2)."""
    def __init__(self, kind, detail=''):
        self.kind = kind
        super().__init__(f'{kind}: {detail}' if detail else kind)


class Unsupported(Exception):
    """Instruction is decodable but outside this model's scope."""
    def __init__(self, mnemonic, fmt):
        self.mnemonic = mnemonic
        self.fmt = fmt
        super().__init__(f'unsupported: {mnemonic}({fmt})')


# ─── decode table (driven by contracts/opcodes.yaml, NOT hand-coded) ─────────

def _load_records(path=_OPCODES_PATH):
    with open(path) as f:
        recs = yaml.safe_load(f)
    out = []
    for r in recs:
        mask = int(r['mask'], 16) if isinstance(r['mask'], str) else r['mask']
        value = int(r['value'], 16) if isinstance(r['value'], str) else r['value']
        out.append((mask, value, r))
    return out


_RECORDS = _load_records()


def _parse_bits(spec):
    hi, lo = spec.strip('[]').split(':')
    return int(hi), int(lo)


def _sext(val, bits):
    if val & (1 << (bits - 1)):
        return val - (1 << bits)
    return val


# Split-immediate groups in v5 opcodes.yaml: e.g. imms18_hi/mid/lo,
# imms24_b23_18/..., immu16_hi/mid/lo. Reassembled high-to-low per
# SimRISC-00 §指令域说明 ("hb→hc→hd 高位到低位").
_IMM_SPLIT_RE = re.compile(r'^(imms\d+|immu\d+?)_(hi|mid|lo|b23_18|b17_12|b11_6|b5_0)$')


def _reassemble_immediates(raw):
    """Merge split immediate parts into canonical imms12/immu12/imms18/immu18/
    imms24/immu24/immu16 entries. `raw` maps field name -> (value, hi, signed).
    Returns dict of canonical name -> (possibly sign-extended) int."""
    groups = {}
    for name, (val, hi, signed) in raw.items():
        m = _IMM_SPLIT_RE.match(name)
        if not m:
            continue
        groups.setdefault(m.group(1), []).append((hi, val, signed))
    out = {}
    for canon, parts in groups.items():
        parts.sort(reverse=True)          # high bits first
        width = sum(hi - lo + 1 for hi, lo, _ in
                    [(h, h - (v.bit_length() - 1) if False else h) for h, v, _ in parts]) \
            if False else None            # (placeholder, replaced below)
        # Recompute widths from the recorded bit-ranges instead:
        total, wsum, signed = 0, 0, False
        # parts currently lack `lo`; re-derive: each part's width is known from
        # its position in the canonical immediate; simpler: concatenate using
        # the stored (hi, val) plus widths looked up from the field order.
        # We stored only (val, hi, signed) — width = 6/4/6/6 by slot order.
        # hi desc order gives: [23:18]/[17:12]/[15:12]/[11:6]/[5:0].
        widths = []
        for hi, val, s in parts:
            signed = signed or s
            if hi == 23:
                w = 6
            elif hi == 17:
                w = 6
            elif hi == 15:
                w = 4
            elif hi == 11:
                w = 6
            elif hi == 5:
                w = 6
            else:  # pragma: no cover — defensive
                raise AssertionError(f'unexpected imm part hi={hi}')
            widths.append(w)
        for (hi, val, _), w in zip(parts, widths):
            total = (total << w) | (val & ((1 << w) - 1))
            wsum += w
        out[canon] = _sext(total, wsum) if signed else total
    return out


def decode(word):
    """Return (record, fields) for a 32-bit instruction word.

    Driven entirely by contracts/opcodes.yaml mask/value + field bit-ranges.
    Split immediates are reassembled to canonical imms12/immu12/imms18/immu18/
    imms24/immu24/immu16 (signed parts sign-extended per SimRISC-00).
    Raises Fault(UNDI) for reserved encodings (contract §2.9/§8.2).
    Records with excluded_m1 are RETURNED (encoding is defined); execution
    raises ILLI for them (ADR-0004 D5.1).
    """
    word &= 0xFFFFFFFF
    match = None
    for mask, value, rec in _RECORDS:
        if (word & mask) == value:
            match = rec
            break
    if match is None:
        raise Fault('UNDI', f'reserved encoding 0x{word:08X}')
    fields = {}
    raw_imm = {}
    for fld in match['fields']:
        hi, lo = _parse_bits(fld['bits'])
        raw = (word >> lo) & ((1 << (hi - lo + 1)) - 1)
        if _IMM_SPLIT_RE.match(fld['name']):
            raw_imm[fld['name']] = (raw, hi, bool(fld.get('signed')))
        elif fld.get('role') == 'imm' and fld.get('signed'):
            fields[fld['name']] = _sext(raw, hi - lo + 1)
        else:
            fields[fld['name']] = raw
    fields.update(_reassemble_immediates(raw_imm))
    return match, fields


# ─── architectural state ─────────────────────────────────────────────────────

class State:
    def __init__(self):
        self.rd = [0] * 64
        self.rb = [0] * 64
        self.rf = [0] * 64
        self.ra = [0] * 64
        self.mem = {}          # addr[47:0] -> byte
        self.pc = DEFAULT_PC
        self.pc_next = None

    # RD: rd0 hardwired zero (contract §1.3.1)
    def rd_read(self, n):
        return 0 if n == 0 else (self.rd[n] & MASK64)

    def rd_write(self, n, v):
        if n == 0:                       # rd0 write = no-op (dual-dest discard)
            return
        self.rd[n] = v & MASK64

    # RB: rb0 = current instruction address, hardware-maintained
    # (contract §1.3.2 + ADR-0004 D6.5). Writes to rb0 are gated by legality
    # (ILLI) before execution, so rb_write(0) is unreachable; ignore defensively.
    def rb_read(self, n):
        return self.rb[n] & MASK64

    def rb_write(self, n, v):
        if n == 0:
            return
        self.rb[n] = v & MASK64

    def ra_read(self, n):
        return self.ra[n] & MASK64

    def ra_write(self, n, v):
        self.ra[n] = v & MASK64

    def load_mem(self, ea, n):
        ea &= MASK48
        v = 0
        for i in range(n):
            v = (v << 8) | self.mem.get((ea + i) & MASK48, 0)   # big-endian §1.6
        return v

    def store_mem(self, ea, n, val):
        ea &= MASK48
        for i in range(n):
            self.mem[(ea + i) & MASK48] = (val >> (8 * (n - 1 - i))) & 0xFF


# Access width (bytes) per memory mnemonic. Sources: contract §4.1/§4.2/§4.9;
# schema.md §input_state.memory[].value 契约 (b->1, w->2, t->4, o->8).
def mem_width_for(rec):
    mn = rec.get('mnemonic', '')
    if rec.get('format') not in ('rrii', 'rrri'):
        return 8
    base = mn.split('.')[0]
    if base in ('ld', 'ldm', 'st', 'stm'):
        suf = mn.split('.')[1] if '.' in mn else 'o'
        return {'b': 1, 'sb': 1, 'ub': 1, 'w': 2, 'sw': 2, 'uw': 2,
                't': 4, 'st': 4, 'ut': 4, 'o': 8}[suf]
    return 8


def build_state(input_state, pc=DEFAULT_PC, mem_width=8):
    """Construct a State from a vector `input_state` mapping.

    mem_width: byte width used to plant input memory entries (schema.md
    §input_state.memory[].value 契约: value is the N-byte value at address,
    N = the vector's access width).
    """
    st = State()
    st.pc = pc
    st.rb[0] = pc & MASK48               # rb0 = current instruction address
    input_state = input_state or {}      # (contract §1.3.2 + ADR-0004 D6.5)
    for name, val in (input_state.get('rd') or {}).items():
        st.rd[int(name[2:])] = int(val, 16) & MASK64
    for name, val in (input_state.get('rb') or {}).items():
        st.rb[int(name[2:])] = int(val, 16) & MASK64
    for name, val in (input_state.get('ra') or {}).items():
        st.ra[int(name[2:])] = int(val, 16) & MASK64
    for name, val in (input_state.get('rf') or {}).items():
        st.rf[int(name[2:])] = int(val, 16) & MASK64
    for entry in (input_state.get('memory') or []):
        addr = int(entry['address'], 16)
        width = entry.get('width', mem_width)
        v = entry['value']
        v = int(v, 16) if isinstance(v, str) else v
        st.store_mem(addr, width, v)
    return st


# ─── legality (contract §9.1 + §3/§4/§7 — static, word-only) ─────────────────

# Dual-destination rrrr (contract §3.1.1/§3.1.4)
_DUAL_DEST = {'add.uo-rd', 'add.so-rd', 'sub.uo-rd', 'sub.so-rd',
              'mul.uo-rd', 'mul.so-rd'}
# rrrr cond-assign with dst=rdhb (cs.n/z/p) / dst=rdhc (cs.eq/ne) (§3.5)
_COND_DST_HB = {'cs.n-rd', 'cs.z-rd', 'cs.p-rd'}
_COND_DST_HC = {'cs.eq-rd', 'cs.ne-rd'}
# Fixed-width N (max shamt / ext start bit) by insn suffix (contract §3.4.1/§3.4.2)
_N_BY_SUFFIX = {'b': 7, 'ub': 7, 'sb': 7,
                'w': 15, 'uw': 15, 'sw': 15,
                't': 31, 'ut': 31, 'st': 31,
                'o': 63, 'uo': 63, 'so': 63}
_BITS_BY_SUFFIX = {'b': 8, 'ub': 8, 'sb': 8,
                   'w': 16, 'uw': 16, 'sw': 16,
                   't': 32, 'ut': 32, 'st': 32,
                   'o': 64, 'uo': 64, 'so': 64}


def _check_multi_range(first, count, bank):
    # contract §9.1: immu6=0 -> ILLI; first+count > 64 -> ILLI (no wrap)
    if count == 0:
        raise Fault('ILLI', 'immu6 == 0 (contract §9.1)')
    if first + count > 64:
        raise Fault('ILLI', f'{bank}{first}+{count} > 64 (contract §9.1)')


def _check_blockcopy(dst_first, src_first, count, dst_bank):
    # contract §3.7/§4.3/§4.9.3: immu6 in [1,63]; dst != reg0 (rd/rb only);
    # dst+count <= 64; src+count <= 64
    if count == 0:
        raise Fault('ILLI', 'immu6 == 0 (contract §9.1)')
    if dst_bank in ('rd', 'rb') and dst_first == 0:
        raise Fault('ILLI', f'block-copy dst {dst_bank}0 (contract §9.1)')
    if dst_first + count > 64 or src_first + count > 64:
        raise Fault('ILLI', 'block-copy start+immu6 > 64 (contract §9.1)')


def check_legality(rec, f):
    """Raise Fault(ILLI) on static operand-legality violation (contract §9.1).

    Static = derivable from the instruction word alone (register numbers,
    immu6). Dynamic checks (div-by-zero, orrr shamt/hd, MALIGN, RASOF/RASUF)
    live in _exec.
    """
    insn, fmt = rec['insn'], rec['format']

    # fence SBZ bits[17:4] must be zero (contract §7.3 + ADR-0004 D5.3)
    if insn == 'fence':
        if f['immu18'] & 0x3FFF0:
            raise Fault('ILLI', 'fence SBZ bits[17:4] != 0 (contract §7.3/D5.3)')
        return
    # illi/swym: no static legality (illi always faults at execution, §7.2)
    if insn in ('illi', 'swym-iiii'):
        return
    # Branches/jumps/calls/ret: sources only; ret rd0 is legal (§5.2/§5.5)
    if insn.startswith(('br.', 'jump-', 'call-')) or insn == 'ret-riii':
        return

    if insn in _DUAL_DEST:                          # §3.1.1/§3.1.4
        a, b = f['rdha'], f['rdhb']
        if a == 0 and b == 0:
            raise Fault('ILLI', 'both dst == rd0 (contract §3.1.1)')
        if a == b and a != 0:
            raise Fault('ILLI', 'rdha == rdhb non-rd0 (contract §3.1.1)')
        return
    if insn in _COND_DST_HB:                        # §3.5 dst=rdhb
        if f['rdhb'] == 0:
            raise Fault('ILLI', 'cond-assign dst rdhb == rd0 (contract §3.5)')
        return
    if insn in _COND_DST_HC:                        # §3.5 dst=rdhc
        if f['rdhc'] == 0:
            raise Fault('ILLI', 'cond-assign dst rdhc == rd0 (contract §3.5)')
        return

    if fmt == 'rrii':
        # ld/st single + cmp.si/ui: rdha (dst or store-src) != rd0 (§4.1.1);
        # RB ld/st: rbha != rb0 (§4.2); RA ld/st: ra0 LEGAL (§4.9.1).
        if 'rdha' in f and f['rdha'] == 0:
            raise Fault('ILLI', 'rdha == rd0 (contract §9.1)')
        if 'rbha' in f and f['rbha'] == 0:
            raise Fault('ILLI', 'rbha == rb0 (contract §9.1)')
        return
    if fmt == 'rrri':
        # multi: zero-dst + immu6 range + bank boundary (§4.1.2/§4.2/§4.9.2)
        if 'rdha' in f:
            if f['rdha'] == 0:
                raise Fault('ILLI', 'rdha == rd0 (contract §9.1)')
            _check_multi_range(f['rdha'], f['immu6'], 'rd')
        elif 'rbha' in f:
            if f['rbha'] == 0:
                raise Fault('ILLI', 'rbha == rb0 (contract §9.1)')
            _check_multi_range(f['rbha'], f['immu6'], 'rb')
        elif 'raha' in f:                           # ra0 legal, no zero check
            _check_multi_range(f['raha'], f['immu6'], 'ra')
        return
    if fmt == 'riii':
        # add.si-rd (§3.1.3): rdha != rd0; add.si-rb/rela.si-rb: rbha != rb0
        if 'rdha' in f and f['rdha'] == 0:
            raise Fault('ILLI', 'rdha == rd0 (contract §9.1)')
        if 'rbha' in f and f['rbha'] == 0:
            raise Fault('ILLI', 'rbha == rb0 (contract §9.1)')
        return
    if fmt == 'rwii':
        if 'rdha' in f and f['rdha'] == 0:
            raise Fault('ILLI', 'wyde dst rdha == rd0 (contract §9.1)')
        if 'rbha' in f and f['rbha'] == 0:
            raise Fault('ILLI', 'wyde dst rbha == rb0 (contract §9.1)')
        return
    if fmt == 'orri':
        mn = rec['mnemonic']
        if mn in ('rd2rd', 'rb2rd', 'rd2rb', 'rb2rb', 'ra2rd', 'rd2ra'):
            dst_nm = [k for k in f if k in ('rdhb', 'rbhb', 'rahb')][0]
            src_nm = [k for k in f if k in ('rdhc', 'rbhc', 'rahc')][0]
            _check_blockcopy(f[dst_nm], f[src_nm], f['immu6'], dst_nm[:2])
            if mn == 'ra2rd' and f['rdhb'] == 0:    # §4.9.3 explicit
                raise Fault('ILLI', 'ra2rd dst rdhb == rd0 (contract §4.9.3)')
            return
        # orri shift/ext: dst != rd0 + immu6 <= N (§3.4.1/§3.4.2 static part)
        if f['rdhb'] == 0:
            raise Fault('ILLI', 'dst rdhb == rd0 (contract §9.1)')
        suf = mn.split('.')[1]
        if f['immu6'] > _N_BY_SUFFIX[suf]:
            raise Fault('ILLI', f'immu6 {f["immu6"]} > N={_N_BY_SUFFIX[suf]} '
                                f'(contract §3.4)')
        return
    if fmt == 'orrr':
        # orrr dst: rdhb != rd0 (§3.x) or rbhb != rb0 (RB arith §4.5.1)
        if 'rdhb' in f and f['rdhb'] == 0:
            raise Fault('ILLI', 'dst rdhb == rd0 (contract §9.1)')
        if 'rbhb' in f and f['rbhb'] == 0:
            raise Fault('ILLI', 'dst rbhb == rb0 (contract §9.1)')
        # orrr shift/ext bound is DYNAMIC (shamt from rdhd) -> checked in _exec
        return


# ─── condition flags (contract Appendix B) ───────────────────────────────────

def _cond_br_rd(mnemonic, v):
    neg = (v >> 63) & 1
    if mnemonic == 'br.n':
        return neg == 1
    if mnemonic == 'br.nn':
        return neg == 0
    if mnemonic == 'br.z':
        return v == 0
    if mnemonic == 'br.nz':
        return v != 0
    if mnemonic == 'br.p':
        return neg == 0 and v != 0
    if mnemonic == 'br.np':
        return neg == 1 or v == 0
    raise AssertionError(mnemonic)


def _is_neg(v):
    return (v >> 63) & 1 == 1                          # N: bit[63]=1

def _is_zero(v):
    return (v & MASK64) == 0                           # Z: all 64 bits = 0

def _is_pos(v):
    return not _is_neg(v) and v != 0                   # P: bit[63]=0 AND rest!=0


# ─── compare result helper (contract §3.2/§4.6) ──────────────────────────────

def _cmp3(a, b):
    """Three-way compare -> -1/0/1 packed as 64-bit two's complement."""
    if a < b:
        return MASK64                                  # -1
    if a > b:
        return 1
    return 0


# ─── fixed-width helpers (contract §3.1.2/§3.1.5/§3.2.2/§3.3/§3.4) ───────────

def _suffix_of(mn):
    return mn.split('.')[1]


def _is_signed_suffix(suf):
    return suf in ('sb', 'sw', 'st', 'so')


def _arith_orrr(mn, a64, b64):
    """Fixed-width add/sub/mul (contract §3.1.2): truncate sources to width,
    operate, truncate to width, then sign/zero-extend to 64 (FULL overwrite)."""
    suf = _suffix_of(mn)
    bits = _BITS_BY_SUFFIX[suf]
    mask = (1 << bits) - 1
    a, b = a64 & mask, b64 & mask
    base = mn.split('.')[0]
    if base == 'add':
        r = (a + b) & mask
    elif base == 'sub':
        r = (a - b) & mask
    elif base == 'mul':
        r = (a * b) & mask
    else:  # pragma: no cover
        raise AssertionError(mn)
    return (_sext(r, bits) & MASK64) if _is_signed_suffix(suf) else r


def _divrem_orrr(mn, a64, b64):
    """Fixed-width div/rem (contract §3.1.5). Sources truncated to width;
    div-by-zero and INT_MIN/-1 (per width) -> ILLI; trunc-toward-zero."""
    suf = _suffix_of(mn)
    bits = _BITS_BY_SUFFIX[suf]
    mask = (1 << bits) - 1
    a, b = a64 & mask, b64 & mask
    base = mn.split('.')[0]
    signed = _is_signed_suffix(suf)
    if b == 0:                                         # D-v5-3: truncated divisor
        raise Fault('ILLI', f'{mn} div by zero (contract §3.1.5)')
    if signed:
        sa, sb = _sext(a, bits), _sext(b, bits)
        if sa == -(1 << (bits - 1)) and sb == -1:
            raise Fault('ILLI', f'{mn} INT_MIN/-1 (contract §3.1.5)')
        q = abs(sa) // abs(sb)                         # trunc toward zero (C99)
        if (sa < 0) != (sb < 0):
            q = -q
        r = sa - q * sb if base == 'rem' else q        # rem sign = dividend
        return _sext(r & mask, bits) & MASK64
    r = (a % b) if base == 'rem' else (a // b)
    return r & mask                                    # zero-extended


def _logic_orrr(mn, c64, d64, old_dst):
    """Fixed-width logic (contract §3.3): low `bits` computed, high bits of
    the destination PRESERVED (read-modify-write)."""
    bits = _BITS_BY_SUFFIX[_suffix_of(mn)]
    mask = (1 << bits) - 1
    c, d = c64 & mask, d64 & mask
    base = mn.split('.')[0]
    if base == 'and':
        r = c & d
    elif base == 'or':
        r = c | d
    elif base == 'xor':
        r = c ^ d
    elif base == 'xnor':
        r = ~(c ^ d) & mask
    else:  # pragma: no cover
        raise AssertionError(mn)
    return ((old_dst & (MASK64 ^ mask)) | (r & mask)) & MASK64


def _shift_orrr_orri(mn, src64, shamt, old_dst):
    """Fixed-width shift (contract §3.4.1). shamt already bound-checked
    (static for orri, dynamic for orrr). High bits PRESERVED."""
    suf = _suffix_of(mn)
    N = _N_BY_SUFFIX[suf]
    maskN = (1 << (N + 1)) - 1
    src = src64 & maskN
    base = mn.split('.')[0]
    if base == 'shl':
        r = (src << shamt) & maskN                     # low bits filled 0
    elif base == 'shr':
        if suf[0] == 's' and (src >> N) & 1:           # arithmetic: fill src[N]
            r = (_sext(src, N + 1) >> shamt) & maskN
        else:                                          # logical: fill 0
            r = (src >> shamt) & maskN
    else:  # pragma: no cover
        raise AssertionError(mn)
    return ((old_dst & (MASK64 ^ maskN)) | r) & MASK64


def _ext_orrr_orri(mn, src64, hd, old_dst):
    """Fixed-width extend (contract §3.4.2). hd already bound-checked.
    rdhb[hd:0] = src[hd:0]; rdhb[N:hd+1] = ext(src[hd]); high PRESERVED."""
    suf = _suffix_of(mn)
    N = _N_BY_SUFFIX[suf]
    maskN = (1 << (N + 1)) - 1
    lowmask = (1 << (hd + 1)) - 1
    low = src64 & lowmask
    if suf[0] == 's' and ((src64 >> hd) & 1):
        fill = (~lowmask) & maskN                      # sign extend
    else:
        fill = 0                                       # zero extend
    return ((old_dst & (MASK64 ^ maskN)) | ((low | fill) & maskN)) & MASK64


# ─── wyde immediate helper (contract §3.6/§4.4) ──────────────────────────────

def _apply_wyde(mn, cur, ww, imm16):
    """Return new 64-bit value after a wyde-immediate op.
    ww selects wyde: 0->[15:0] 1->[31:16] 2->[47:32] 3->[63:48] (§2.4)."""
    shift = ww * 16
    target = (cur >> shift) & MASK16
    if mn == 'set.zw':                                 # target=imm; others 0
        return (imm16 << shift) & MASK64
    if mn == 'set.ow':                                 # target=imm; others 0xFFFF
        base = MASK64 & ~(MASK16 << shift)
        return (base | (imm16 << shift)) & MASK64
    if mn == 'or.w':                                   # target |= imm; rest kept
        newt = (target | imm16) & MASK16
    elif mn == 'andn.w':                               # target &= ~imm; rest kept
        newt = (target & (~imm16 & MASK16)) & MASK16
    else:  # pragma: no cover
        raise AssertionError(mn)
    return ((cur & ~(MASK16 << shift)) | (newt << shift)) & MASK64


# ─── RegRAS/MemRAS (contract §5.6) ───────────────────────────────────────────

def _ras_push(st, new_addr):
    """Push return address (contract §5.6.1). Precise: RASOF leaves RA untouched
    (run() discards the work copy, but checks are ordered before mutation)."""
    new_addr &= MASK48
    top = st.ra[63]
    cnt = (top >> 48) & 0xFFFF
    addr48 = top & MASK48
    if cnt == 0:                                       # case 1: empty top
        st.ra[63] = (1 << 48) | new_addr
        return
    if 1 <= cnt <= 0xFFFE and addr48 == new_addr:      # case 2: recursion
        st.ra[63] = ((cnt + 1) << 48) | addr48
        return
    # case 3: shift-push; evict old ra1 if valid
    if ((st.ra[1] >> 48) & 0xFFFF) == 0:               # ra1 invalid: pure shift
        for i in range(2, 64):                         # ra{i-1} <- ra{i}
            st.ra[i - 1] = st.ra[i]
        st.ra[63] = (1 << 48) | new_addr
        return
    if (st.ra[0] & MASK48) == 0:                       # RegRAS-only -> RASOF
        raise Fault('RASOF', 'RegRAS overflow (contract §5.6.1)')
    # MemRAS spill: count overflow check BEFORE any mutation (precise)
    mem_cnt = (st.ra[0] >> 48) & 0xFFFF
    if mem_cnt == 0xFFFF:
        raise Fault('RASOF', 'MemRAS count overflow (contract §5.6.1)')
    evicted = st.ra[1]
    for i in range(2, 64):
        st.ra[i - 1] = st.ra[i]
    st.ra[63] = (1 << 48) | new_addr
    new_ptr = ((st.ra[0] & MASK48) - 8) & MASK48       # ra0 -= 8, store ra1
    st.store_mem(new_ptr, 8, evicted)
    st.ra[0] = (((mem_cnt + 1) & 0xFFFF) << 48) | new_ptr


def _ras_pop(st):
    """Pop return address (contract §5.6.2). Precise: RASUF leaves RA untouched."""
    top = st.ra[63]
    cnt = (top >> 48) & 0xFFFF
    addr48 = top & MASK48
    if cnt > 1:                                        # case 1: recursion
        st.ra[63] = ((cnt - 1) << 48) | addr48
        return addr48
    if cnt == 1:                                       # case 2: shift-pop
        for i in range(62, 0, -1):                     # ra{i+1} <- ra{i}
            st.ra[i + 1] = st.ra[i]
        st.ra[1] = 0
        return addr48
    # case 3: RegRAS empty
    if (st.ra[0] & MASK48) == 0:
        raise Fault('RASUF', 'RegRAS underflow (contract §5.6.2)')
    # MemRAS fill: validate BEFORE mutation (precise)
    mem_cnt = (st.ra[0] >> 48) & 0xFFFF
    if mem_cnt == 0:
        raise Fault('RASUF', 'MemRAS count underflow (contract §5.6.2)')
    ptr = st.ra[0] & MASK48
    content = st.load_mem(ptr, 8)
    ccnt, caddr = (content >> 48) & 0xFFFF, content & MASK48
    if ccnt == 0:
        raise Fault('RASUF', 'MemRAS invalid entry (contract §5.6.2)')
    new_ptr = (ptr + 8) & MASK48                       # ra0 += 8, count -= 1
    st.ra[0] = (((mem_cnt - 1) & 0xFFFF) << 48) | new_ptr
    if ccnt > 1:                                       # remaining refs -> ra63
        st.ra[63] = ((ccnt - 1) << 48) | caddr
    return caddr


# ─── memory access helpers (contract §4.1/§4.2/§4.9) ─────────────────────────

# insn -> (width_bytes, signed_or_None)
_LD_INFO = {
    'ld.sb-rd': (1, True), 'ld.ub-rd': (1, False),
    'ld.sw-rd': (2, True), 'ld.uw-rd': (2, False),
    'ld.st-rd': (4, True), 'ld.ut-rd': (4, False),
    'ld.o-rd': (8, None), 'ld.o-rb': (8, None), 'ld.o-ra': (8, None),
    'ldm.sb-rd': (1, True), 'ldm.ub-rd': (1, False),
    'ldm.sw-rd': (2, True), 'ldm.uw-rd': (2, False),
    'ldm.st-rd': (4, True), 'ldm.ut-rd': (4, False),
    'ldm.o-rd': (8, None), 'ldm.o-rb': (8, None), 'ldm.o-ra': (8, None),
}
_ST_INFO = {
    'st.b-rd': 1, 'st.w-rd': 2, 'st.t-rd': 4, 'st.o-rd': 8,
    'st.o-rb': 8, 'st.o-ra': 8,
    'stm.b-rd': 1, 'stm.w-rd': 2, 'stm.t-rd': 4, 'stm.o-rd': 8,
    'stm.o-rb': 8, 'stm.o-ra': 8,
}


def _extend(val, width, signed):
    if signed:                                         # sign-extend to 64
        return _sext(val, width * 8) & MASK64
    return val & MASK64                                # zero-extend / octa


def _check_align(ea, width):
    # contract §4.1.1: byte no fault; wyde/tetra/octa naturally aligned.
    if width > 1 and (ea % width) != 0:
        raise Fault('MALIGN', f'ea=0x{ea:X} width={width} (contract §4.1.1)')


# ─── main execute ────────────────────────────────────────────────────────────

def _exec(word, st):
    rec, f = decode(word)
    insn, fmt, mn = rec['insn'], rec['format'], rec['mnemonic']

    # M1-excluded but defined encodings -> ILLI (ADR-0004 D5.1)
    if rec.get('excluded_m1'):
        raise Fault('ILLI', f'{insn} excluded from M1 (ADR-0004 D5.1)')

    # illi / swym / fence (contract §7)
    if insn == 'illi':
        raise Fault('ILLI', 'illi (contract §7.2)')
    if insn == 'swym-iiii':
        st.pc_next = st.pc + 4                         # NOP incl. timing N (§7.1)
        return

    check_legality(rec, f)
    st.pc_next = st.pc + 4                             # default sequential

    if insn == 'fence':                                # barrier; M1 NOP (§7.3)
        return

    # ── RD rrrr dual-dest arith (contract §3.1.1/§3.1.4) ─────────────────────
    if insn in _DUAL_DEST:
        c, d = st.rd_read(f['rdhc']), st.rd_read(f['rdhd'])
        if insn in ('add.uo-rd', 'sub.uo-rd'):         # zero-extend to 128
            res = (c + d if insn == 'add.uo-rd' else c - d) & MASK128
        elif insn in ('add.so-rd', 'sub.so-rd'):       # sign-extend to 128
            res = (_sext(c, 64) + _sext(d, 64) if insn == 'add.so-rd'
                   else _sext(c, 64) - _sext(d, 64)) & MASK128
        elif insn == 'mul.uo-rd':
            res = (c * d) & MASK128
        else:                                          # mul.so-rd
            res = (_sext(c, 64) * _sext(d, 64)) & MASK128
        st.rd_write(f['rdha'], (res >> 64) & MASK64)   # high half
        st.rd_write(f['rdhb'], res & MASK64)           # low half
        return

    # ── RD/RB riii in-place add (contract §3.1.3/§4.5.2) ─────────────────────
    if insn == 'add.si-rd':                            # rdha += sext18, full 64
        st.rd_write(f['rdha'], (st.rd_read(f['rdha']) + f['imms18']) & MASK64)
        return
    if insn == 'add.si-rb':                            # full 64-bit (D-v5-1)
        st.rb_write(f['rbha'], (st.rb_read(f['rbha']) + f['imms18']) & MASK64)
        return

    # ── rela.si (contract §4.7): base=(rb0)&~0xFFF; hi16 preserved ────────────
    if insn == 'rela.si-rb':
        base = (st.rb_read(0) & MASK48) & ~0xFFF       # rb0 = current addr
        res = (base + (f['imms18'] << 12)) & MASK48
        old = st.rb_read(f['rbha'])
        st.rb_write(f['rbha'], (old & HI16) | res)
        return

    # ── RD rrii compare (contract §3.2.1) ────────────────────────────────────
    if insn == 'cmp.si-rd':                            # signed rdhb vs sext12
        st.rd_write(f['rdha'], _cmp3(_sext(st.rd_read(f['rdhb']), 64),
                                     f['imms12']))
        return
    if insn == 'cmp.ui-rd':                            # unsigned rdhb vs zext12
        st.rd_write(f['rdha'], _cmp3(st.rd_read(f['rdhb']), f['immu12']))
        return

    # ── RD rrrr cond-assign (contract §3.5) ──────────────────────────────────
    if insn in _COND_DST_HB:                           # cs.n/z/p
        sel = st.rd_read(f['rdha'])
        cond = (_is_neg(sel) if insn == 'cs.n-rd' else
                _is_zero(sel) if insn == 'cs.z-rd' else _is_pos(sel))
        st.rd_write(f['rdhb'], st.rd_read(f['rdhc'] if cond else f['rdhd']))
        return
    if insn in _COND_DST_HC:                           # cs.eq/ne
        eq = st.rd_read(f['rdha']) == st.rd_read(f['rdhb'])
        if (eq and insn == 'cs.eq-rd') or (not eq and insn == 'cs.ne-rd'):
            st.rd_write(f['rdhc'], st.rd_read(f['rdhd']))
        return

    # ── rwii wyde immediate (contract §3.6 RD / §4.4 RB) ──────────────────────
    if fmt == 'rwii':
        imm16 = f['immu16']
        if 'rdha' in f:
            st.rd_write(f['rdha'], _apply_wyde(mn, st.rd_read(f['rdha']),
                                               f['wpN'], imm16))
        else:
            st.rb_write(f['rbha'], _apply_wyde(mn, st.rb_read(f['rbha']),
                                               f['wpN'], imm16))
        return

    # ── orri block copy (contract §3.7/§4.3/§4.9.3; full 64-bit, D-v5-2) ──────
    if fmt == 'orri' and mn in ('rd2rd', 'rb2rd', 'rd2rb', 'rb2rb',
                                'ra2rd', 'rd2ra'):
        count = f['immu6']
        dst_nm = [k for k in f if k in ('rdhb', 'rbhb', 'rahb')][0]
        src_nm = [k for k in f if k in ('rdhc', 'rbhc', 'rahc')][0]
        dst, src = f[dst_nm], f[src_nm]
        d_bank, s_bank = dst_nm[:2], src_nm[:2]
        read = {'rd': st.rd_read, 'rb': st.rb_read,
                'ra': st.ra_read}[s_bank]
        write = {'rd': st.rd_write, 'rb': st.rb_write,
                 'ra': st.ra_write}[d_bank]
        for i in range(count):                         # increasing i, read-then-write
            write(dst + i, read(src + i))              # full 64-bit, no conversion
        return

    # ── MISC fixed-width orrr/orri (contract §3.1.2/§3.1.5/§3.2.2/§3.3/§3.4) ──
    if fmt in ('orrr', 'orri') and mn.split('.')[0] in (
            'add', 'sub', 'mul', 'div', 'rem', 'cmp', 'and', 'or', 'xor',
            'xnor', 'shl', 'shr', 'ext'):
        base = mn.split('.')[0]
        # RB arithmetic (contract §4.5.1): FULL 64-bit (D-v5-1)
        if insn in ('add.so-rb', 'sub.so-rb'):
            a, b = st.rb_read(f['rbhc']), st.rd_read(f['rdhd'])
            st.rb_write(f['rbhb'], ((a + b) if insn == 'add.so-rb'
                                    else (a - b)) & MASK64)
            return
        # RB compare (contract §4.6): unsigned, hi16 ignored (D-v5-4)
        if insn == 'cmp.uo-rb':
            st.rd_write(f['rdhb'], _cmp3(st.rb_read(f['rbhc']) & MASK48,
                                         st.rb_read(f['rbhd']) & MASK48))
            return
        suf = _suffix_of(mn)
        bits = _BITS_BY_SUFFIX[suf]
        if base in ('add', 'sub', 'mul'):              # §3.1.2 full overwrite
            st.rd_write(f['rdhb'], _arith_orrr(mn, st.rd_read(f['rdhc']),
                                               st.rd_read(f['rdhd'])))
            return
        if base in ('div', 'rem'):                     # §3.1.5 full overwrite
            st.rd_write(f['rdhb'], _divrem_orrr(mn, st.rd_read(f['rdhc']),
                                                st.rd_read(f['rdhd'])))
            return
        if base == 'cmp':                              # §3.2.2 full 64-bit -1/0/1
            mask = (1 << bits) - 1
            a, b = st.rd_read(f['rdhc']) & mask, st.rd_read(f['rdhd']) & mask
            if _is_signed_suffix(suf):
                a, b = _sext(a, bits), _sext(b, bits)
            st.rd_write(f['rdhb'], _cmp3(a, b))
            return
        if base in ('and', 'or', 'xor', 'xnor'):       # §3.3 RMW
            st.rd_write(f['rdhb'], _logic_orrr(mn, st.rd_read(f['rdhc']),
                                               st.rd_read(f['rdhd']),
                                               st.rd_read(f['rdhb'])))
            return
        if base in ('shl', 'shr', 'ext'):              # §3.4 RMW + bound check
            N = _N_BY_SUFFIX[suf]
            if fmt == 'orri':
                amt = f['immu6']                       # static ≤N in legality
            else:                                      # orrr: rdhd[5:0] (D-v5-5)
                amt = st.rd_read(f['rdhd']) & 0x3F
                if amt > N:
                    raise Fault('ILLI', f'{mn} shamt/hd {amt} > N={N} '
                                        f'(contract §3.4)')
            if base == 'ext':
                st.rd_write(f['rdhb'], _ext_orrr_orri(mn, st.rd_read(f['rdhc']),
                                                      amt, st.rd_read(f['rdhb'])))
            else:
                st.rd_write(f['rdhb'], _shift_orrr_orri(mn, st.rd_read(f['rdhc']),
                                                        amt, st.rd_read(f['rdhb'])))
            return

    # ── loads ───────────────────────────────────────────────────────────────
    if insn in _LD_INFO and fmt == 'rrii':             # single (§4.1.1/§4.2/§4.9.1)
        width, signed = _LD_INFO[insn]
        ea = ((st.rb_read(f['rbhb']) & MASK48) + f['imms12']) & MASK48
        _check_align(ea, width)
        val = _extend(st.load_mem(ea, width), width, signed)
        if 'rbha' in f:
            st.rb_write(f['rbha'], val)                # full 64-bit (§4.2)
        elif 'raha' in f:
            st.ra_write(f['raha'], val)                # full 64-bit (§4.9.1)
        else:
            st.rd_write(f['rdha'], val)
        return
    if insn in _LD_INFO and fmt == 'rrri':             # multi (§4.1.2/§4.2/§4.9.2)
        width, signed = _LD_INFO[insn]
        base = st.rb_read(f['rbhb']) & MASK48
        idx = st.rd_read(f['rdhc']) & MASK48           # snapshot (§4.1.2)
        count = f['immu6']
        eas = [(base + idx + i * width) & MASK48 for i in range(count)]
        for ea in eas:                                 # precise: pre-check all
            _check_align(ea, width)
        dst_nm = 'rbha' if 'rbha' in f else ('raha' if 'raha' in f else 'rdha')
        write = {'rdha': st.rd_write, 'rbha': st.rb_write,
                 'raha': st.ra_write}[dst_nm]
        for i, ea in enumerate(eas):
            write(f[dst_nm] + i, _extend(st.load_mem(ea, width), width, signed))
        return

    # ── stores ──────────────────────────────────────────────────────────────
    if insn in _ST_INFO and fmt == 'rrii':             # single (§4.1.1/§4.2/§4.9.1)
        width = _ST_INFO[insn]
        ea = ((st.rb_read(f['rbhb']) & MASK48) + f['imms12']) & MASK48
        _check_align(ea, width)
        src_nm = 'rbha' if 'rbha' in f else ('raha' if 'raha' in f else 'rdha')
        src = {'rdha': st.rd_read, 'rbha': st.rb_read,
               'raha': st.ra_read}[src_nm](f[src_nm])
        st.store_mem(ea, width, src & ((1 << (width * 8)) - 1))
        return
    if insn in _ST_INFO and fmt == 'rrri':             # multi (§4.1.2/§4.2/§4.9.2)
        width = _ST_INFO[insn]
        base = st.rb_read(f['rbhb']) & MASK48
        idx = st.rd_read(f['rdhc']) & MASK48
        count = f['immu6']
        src_nm = 'rbha' if 'rbha' in f else ('raha' if 'raha' in f else 'rdha')
        read = {'rdha': st.rd_read, 'rbha': st.rb_read,
                'raha': st.ra_read}[src_nm]
        eas = [(base + idx + i * width) & MASK48 for i in range(count)]
        for ea in eas:
            _check_align(ea, width)
        for i, ea in enumerate(eas):
            st.store_mem(ea, width, read(f[src_nm] + i) & ((1 << (width * 8)) - 1))
        return

    # ── control flow (contract §5; rb0 = current addr, ADR-0004 D6.5) ─────────
    rb0 = st.rb_read(0) & MASK48
    if insn in ('br.n-rd', 'br.nn-rd', 'br.z-rd', 'br.nz-rd', 'br.p-rd',
                'br.np-rd'):                           # single-reg RD (§5.2.2)
        if _cond_br_rd(mn, st.rd_read(f['rdha'])):
            st.pc_next = (rb0 + (f['imms18'] << 2)) & MASK48
        return
    if insn in ('br.z-rb', 'br.nz-rb'):                # RB zero test (§5.2.3, D-v5-6)
        is_zero = (st.rb_read(f['rbha']) & MASK64) == 0
        if (is_zero and insn == 'br.z-rb') or (not is_zero and insn == 'br.nz-rb'):
            st.pc_next = (rb0 + (f['imms18'] << 2)) & MASK48
        return
    if insn in ('br.eq-rd', 'br.ne-rd'):               # dual-reg (§5.2.1)
        eq = st.rd_read(f['rdha']) == st.rd_read(f['rdhb'])
        if (eq and insn == 'br.eq-rd') or (not eq and insn == 'br.ne-rd'):
            st.pc_next = (rb0 + (f['imms12'] << 2)) & MASK48
        return
    if insn == 'jump-iiii':                            # §5.3 relative
        st.pc_next = (rb0 + (f['imms24'] << 2)) & MASK48
        return
    if insn == 'jump-rrii':                            # §5.3 absolute
        st.pc_next = ((st.rb_read(f['rbha']) & MASK48) +
                      (st.rd_read(f['rdhb']) & MASK48) +
                      (f['imms12'] << 2)) & MASK48
        return
    if insn == 'call-iiii':                            # §5.4 relative
        _ras_push(st, (st.pc + 4) & MASK48)            # return addr = PC+4
        st.pc_next = (rb0 + (f['imms24'] << 2)) & MASK48
        return
    if insn == 'call-rrii':                            # §5.4 absolute
        _ras_push(st, (st.pc + 4) & MASK48)
        st.pc_next = ((st.rb_read(f['rbha']) & MASK48) +
                      (st.rd_read(f['rdhb']) & MASK48) +
                      (f['imms12'] << 2)) & MASK48
        return
    if insn == 'ret-riii':                             # §5.5
        ret_addr = _ras_pop(st)                        # may raise RASUF
        st.pc_next = ret_addr & MASK48
        st.rd_write(f['rdha'], f['imms18'] & MASK64)   # rdha=rd0 discards (legal)
        return

    raise Unsupported(mn, fmt)


def run(word, input_state=None, pc=DEFAULT_PC, state=None):
    """Execute a single instruction word.

    Returns (State, fault_kind_or_None). On fault the returned state is the
    pre-execution snapshot (precise: no architectural side effect, §9.2).
    Raises Unsupported for out-of-scope instructions.
    """
    if state is None:
        # Decode first: unknown encodings -> UNDI; known ones reveal the
        # memory width needed to plant input memory (schema.md value contract).
        try:
            rec0, _ = decode(word)
            width = mem_width_for(rec0)
        except Fault as ex:
            return build_state(input_state, pc), ex.kind
        state = build_state(input_state, pc, mem_width=width)
    # IALIGN precheck (contract §2.1)
    if state.pc & 0x3:
        return state, 'IALIGN'
    import copy
    work = copy.deepcopy(state)
    try:
        _exec(word, work)
    except Fault as ex:
        return state, ex.kind          # discard partial work: precise (§9.2)
    return work, None


if __name__ == '__main__':
    import sys
    w = int(sys.argv[1], 16)
    rec, f = decode(w)
    print(f"0x{w:08X} -> {rec['insn']}({rec['format']}) fields={f}"
          + (" [excluded_m1]" if rec.get('excluded_m1') else ""))
