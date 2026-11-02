#!/usr/bin/env python3
"""Scalar and floating-point ISA reference model, derived from v5 contracts.

Encoding comes from contracts/opcodes.yaml; execution never reads LLVM/QEMU.
The supported scope is explicit (is_supported), independent of evolving scope
labels. Reserved encodings raise UNDI; privileged, atomic and fence operations
outside this model raise Unsupported.

State.pc is the low-48-bit fetch address. State.rb[0] retains the full 64-bit
control-flow value. A successful run advances both; a fault changes neither.
Memory is sparse, big endian, zero-filled, with 48-bit wrapping; it does not
model MMU, permissions, machine exceptions, ROM or exit-port devices.
See README.md and DESIGN.md for scope, normative sources and limitations.
"""

import os

import yaml
try:
    from . import fp_ref
except ImportError:
    import fp_ref

MASK64 = (1 << 64) - 1
MASK48 = (1 << 48) - 1
MASK16 = (1 << 16) - 1
HI16 = MASK64 ^ MASK48          # bits[63:48]
MASK128 = (1 << 128) - 1

# RAM entry = the address test vectors assume for the instruction under test
# (contract-isa §8 vectors cite ADR-0004 D2.2/D6.5; schema.md §expected_pc).
DEFAULT_PC = 0xFC0000000000

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_OPCODES_PATH = os.path.join(_REPO, 'contracts', 'opcodes.yaml')


class Fault(Exception):
    """Precise architectural exception (contract §15.2)."""
    def __init__(self, kind, detail=''):
        self.kind = kind
        super().__init__(f'{kind}: {detail}' if detail else kind)


class Unsupported(Exception):
    """Instruction is decodable but outside this model's scope."""
    def __init__(self, mnemonic, fmt):
        self.mnemonic = mnemonic
        self.fmt = fmt
        super().__init__(f'unsupported: {mnemonic}({fmt})')


class SpecificationGap(Exception):
    """A contradictory specification prevents a trustworthy expected result.

    This is a model diagnostic, not an architectural exception or a scope skip.
    """
    def __init__(self, iid, detail):
        self.iid = iid
        super().__init__(f'{iid}: {detail}')


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
_KNOWN_IDS = {r['id'] for _, _, r in _RECORDS if 'id' in r}


def _parse_bits(spec):
    hi, lo = spec.strip('[]').split(':')
    return int(hi), int(lo)


def _sext(val, bits):
    if val & (1 << (bits - 1)):
        return val - (1 << bits)
    return val


def decode(word):
    """Return (record, fields) for a 32-bit instruction word.

    Driven entirely by contracts/opcodes.yaml mask/value + field bit-ranges.
    Single-field immediates (imms12/immu12/imms18/immu18/imms24/immu16/immu6)
    are sign-extended iff the field record says signed (SimRISC-00 §指令域说明).
    Raises Fault(UNDI) for reserved encodings (contract §2.9/§13.4).
    Defined out-of-scope records are returned; execution raises Unsupported.
    """
    word = _uint(word, 32, 'instruction word')
    match = None
    for mask, value, rec in _RECORDS:
        if (word & mask) == value:
            match = rec
            break
    if match is None:
        raise Fault('UNDI', f'reserved encoding 0x{word:08X}')
    fields = {}
    for fld in match['fields']:
        hi, lo = _parse_bits(fld['bits'])
        raw = (word >> lo) & ((1 << (hi - lo + 1)) - 1)
        if fld.get('role') == 'imm' and fld.get('signed'):
            fields[fld['name']] = _sext(raw, hi - lo + 1)
        else:
            fields[fld['name']] = raw
    return match, fields


# ─── instruction ids (contracts/opcodes.yaml `id`, mnemonic_format_feature) ──
# Verified against the table at import (typo-proof): every id below must exist.

# Individual instruction ids (used in _exec comparisons; a misspelled NAME
# fails loudly with NameError, a misspelled VALUE fails the assert below).
_ID_ADD_UO = 'add.uo_rrrr_rd'
_ID_ADD_SO = 'add.so_rrrr_rd'
_ID_SUB_UO = 'sub.uo_rrrr_rd'
_ID_SUB_SO = 'sub.so_rrrr_rd'
_ID_MUL_UO = 'mul.uo_rrrr_rd'
_ID_MUL_SO = 'mul.so_rrrr_rd'
_ID_CS_N = 'cs.n_rrrr_rd'
_ID_CS_Z = 'cs.z_rrrr_rd'
_ID_CS_P = 'cs.p_rrrr_rd'
_ID_CS_EQ = 'cs.eq_rrrr_rd'
_ID_CS_NE = 'cs.ne_rrrr_rd'
_ID_BR_Z_RB = 'br.z_riii_rb'
_ID_BR_NZ_RB = 'br.nz_riii_rb'
_ID_BR_EQ = 'br.eq_rrii_rd'
_ID_BR_NE = 'br.ne_rrii_rd'

_DUAL_DEST = {_ID_ADD_UO, _ID_ADD_SO, _ID_SUB_UO,
              _ID_SUB_SO, _ID_MUL_UO, _ID_MUL_SO}
_COND_DST_HB = {_ID_CS_N, _ID_CS_Z, _ID_CS_P}
_COND_DST_HC = {_ID_CS_EQ, _ID_CS_NE}
_BR_RD = {'br.n_riii_rd', 'br.nn_riii_rd', 'br.z_riii_rd', 'br.nz_riii_rd',
          'br.p_riii_rd', 'br.np_riii_rd'}
_BR_RB = {_ID_BR_Z_RB, _ID_BR_NZ_RB}
_BR_DUAL = {_ID_BR_EQ, _ID_BR_NE}
_ID_ADD_SI_RD = 'add.si_riii_rd'
_ID_ADD_SI_RB = 'add.si_riii_rb'
_ID_AIP_SI_RB = 'aip.si_riii_rb'
_ID_CMP_SI = 'cmp.si_rrii_rd'
_ID_CMP_UI = 'cmp.ui_rrii_rd'
_ID_CMP_UO_RB = 'cmp.uo_orrr_dbb'
_ID_ADD_SO_RB = 'add.o_orrr_bbd'
_ID_SUB_SO_RB = 'sub.o_orrr_bbd'
_ID_SUB_RB_RD = 'sub.o_orrr_dbb'
_ID_JUMP_I = 'jump_iiii_rb'
_ID_JUMP_R = 'jump_rrii_rb'
_ID_CALL_I = 'call_iiii_ra'
_ID_CALL_R = 'call_rrii_ra'
_ID_RET = 'ret_riii_ra'
_ID_SWYM = 'swym_oiii_imm'
_ID_FENCE = 'fence_ciii_cfx'

# id -> (width_bytes, signed_or_None)
_LD_INFO = {
    'ld.sb_rrii_rd': (1, True), 'ld.ub_rrii_rd': (1, False),
    'ld.sw_rrii_rd': (2, True), 'ld.uw_rrii_rd': (2, False),
    'ld.st_rrii_rd': (4, True), 'ld.ut_rrii_rd': (4, False),
    'ld.o_rrii_rd': (8, None), 'ld.o_rrii_rb': (8, None), 'ld.o_rrii_ra': (8, None),
    'ldm.sb_rrri_rd': (1, True), 'ldm.ub_rrri_rd': (1, False),
    'ldm.sw_rrri_rd': (2, True), 'ldm.uw_rrri_rd': (2, False),
    'ldm.st_rrri_rd': (4, True), 'ldm.ut_rrri_rd': (4, False),
    'ldm.o_rrri_rd': (8, None), 'ldm.o_rrri_rb': (8, None), 'ldm.o_rrri_ra': (8, None),
}
# id -> width_bytes
_ST_INFO = {
    'st.b_rrii_rd': 1, 'st.w_rrii_rd': 2, 'st.t_rrii_rd': 4, 'st.o_rrii_rd': 8,
    'st.o_rrii_rb': 8, 'st.o_rrii_ra': 8,
    'stm.b_rrri_rd': 1, 'stm.w_rrri_rd': 2, 'stm.t_rrri_rd': 4, 'stm.o_rrri_rd': 8,
    'stm.o_rrri_rb': 8, 'stm.o_rrri_ra': 8,
}

_REFERENCED_IDS = (
    set(_DUAL_DEST) | set(_COND_DST_HB) | set(_COND_DST_HC) |
    set(_BR_RD) | set(_BR_RB) | set(_BR_DUAL) | set(_LD_INFO) | set(_ST_INFO) |
    {_ID_ADD_SI_RD, _ID_ADD_SI_RB, _ID_AIP_SI_RB, _ID_CMP_SI, _ID_CMP_UI,
     _ID_CMP_UO_RB, _ID_ADD_SO_RB, _ID_SUB_SO_RB, _ID_SUB_RB_RD, _ID_JUMP_I, _ID_JUMP_R,
     _ID_CALL_I, _ID_CALL_R, _ID_RET, _ID_SWYM, _ID_FENCE})
_UNKNOWN = _REFERENCED_IDS - _KNOWN_IDS
assert not _UNKNOWN, f'golden references unknown opcodes.yaml ids: {_UNKNOWN}'


# Explicit families: newly tagged m1 instructions never silently gain support.
_SUPPORTED_IDS = frozenset(
    (_REFERENCED_IDS - {_ID_FENCE}) |
    {r['id'] for _, _, r in _RECORDS
     if r['scope'] == 'm1' and (
         (r['format'] == 'rwii' and r['id'].rsplit('_', 1)[-1] in ('rd', 'rb')) or
         r['mnemonic'] in ('rd2rd', 'rb2rd', 'rd2rb', 'rb2rb', 'rd2ra', 'ra2rd') or
         (r['format'] in ('orrr', 'orri') and r['id'].rsplit('_', 1)[-1] == 'rd' and
          r['mnemonic'].split('.')[0] in
          ('add', 'sub', 'mul', 'div', 'rem', 'cmp', 'and', 'or', 'xor',
           'xnor', 'shl', 'shr', 'ext')))} |
    {_ID_AIP_SI_RB} |
    {r['id'] for _, _, r in _RECORDS if r['scope'] == 'fp'}
)


def is_supported(rec):
    """Whether this model implements the decoded instruction family."""
    return rec['id'] in _SUPPORTED_IDS


def _uint(value, bits, name):
    """Accept integers and 0x-prefixed strings, never silently truncate input."""
    if isinstance(value, str):
        value = int(value, 0)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f'{name} must be an integer or numeric string')
    if not 0 <= value < 1 << bits:
        raise ValueError(f'{name} must fit unsigned {bits} bits')
    return value


# ─── architectural state ─────────────────────────────────────────────────────

class State:
    def __init__(self):
        self.rd = [0] * 64
        self.rb = [0] * 64
        self.rf = [0x7FF800007FC00000] + [0] * 63
        self.ra = [0] * 64
        self.mem = {}          # addr[47:0] -> byte
        self.pc = DEFAULT_PC
        self.rb[0] = DEFAULT_PC
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
        self.ra[n] = v & ((1 << 54) - 1 if n == 0 else MASK64)

    def rf_write(self, n, v):
        if n == 0:
            # FCSR exposes only rounding mode and accrued exception flags.
            mask = (3 << 32) | 0x1F
            self.rf[0] = (self.rf[0] & ~mask) | (v & mask)
        else:
            self.rf[n] = v & MASK64

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


# Access width (bytes) per memory mnemonic. Sources: contract §3.1/§3.2/§3.3;
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
    if input_state is not None and not isinstance(input_state, dict):
        raise ValueError('input_state must be a mapping')
    st = State()
    full_pc = _uint(pc, 64, 'pc')
    st.pc = full_pc & MASK48
    st.rb[0] = full_pc
    input_state = input_state or {}
    unknown = set(input_state) - {'rd', 'rb', 'ra', 'rf', 'memory'}
    if unknown:
        raise ValueError(f'unknown state fields: {sorted(unknown)}')
    for bank in ('rd', 'rb', 'ra', 'rf'):
        entries = input_state.get(bank)
        if entries is None:
            entries = {}
        if not isinstance(entries, dict):
            raise ValueError(f'{bank} must be a mapping')
        for name, val in entries.items():
            if not isinstance(name, str) or not name.startswith(bank) or not name[2:].isdigit():
                raise ValueError(f'invalid register name: {name!r}')
            idx = int(name[2:])
            if not 0 <= idx < 64 or name != f'{bank}{idx}':
                raise ValueError(f'invalid register name: {name!r}')
            val = _uint(val, 64, name)
            if bank == 'rd' and idx == 0 and val != 0:
                raise ValueError('rd0 must be zero')
            if bank == 'rb' and idx == 0 and val != full_pc:
                raise ValueError('rb0 must agree with pc')
            if bank == 'ra' and idx == 0 and val >> 54:
                raise ValueError('ra0 SBZ bits must be zero in input state')
            getattr(st, bank)[idx] = val
    memory = input_state.get('memory')
    if memory is None:
        memory = []
    if not isinstance(memory, list):
        raise ValueError('memory must be a list')
    for entry in memory:
        if not isinstance(entry, dict) or set(entry) - {'address', 'value', 'width'} or not {'address', 'value'} <= set(entry):
            raise ValueError('memory entries require address/value and optional width')
        addr = _uint(entry['address'], 48, 'memory address')
        width = entry.get('width', mem_width)
        if isinstance(width, bool) or not isinstance(width, int) or width not in (1, 2, 4, 8):
            raise ValueError('memory width must be 1, 2, 4 or 8 bytes')
        st.store_mem(addr, width, _uint(entry['value'], 64, 'memory value'))
    return st


# ─── legality (contract §15.1 + §3/§4/§14 — static, word-only) ───────────────

# Fixed-width N (max shamt / ext start bit) by insn suffix (contract §6.4.1/§6.4.2
# + §10.4/§11.4/§12.4)
_N_BY_SUFFIX = {'b': 7, 'ub': 7, 'sb': 7,
                'w': 15, 'uw': 15, 'sw': 15,
                't': 31, 'ut': 31, 'st': 31,
                'o': 63, 'uo': 63, 'so': 63}
_BITS_BY_SUFFIX = {'b': 8, 'ub': 8, 'sb': 8,
                   'w': 16, 'uw': 16, 'sw': 16,
                   't': 32, 'ut': 32, 'st': 32,
                   'o': 64, 'uo': 64, 'so': 64}


def _check_multi_range(first, count, bank):
    # contract §15.1: immu6=0 -> ILLI; first+count > 64 -> ILLI (no wrap)
    if count == 0:
        raise Fault('ILLI', 'immu6 == 0 (contract §15.1)')
    if first + count > 64:
        raise Fault('ILLI', f'{bank}{first}+{count} > 64 (contract §15.1)')


def _check_blockcopy(dst_first, src_first, count, dst_bank):
    # Same-bank overlap is forbidden (SimRISC-02 §3.1).
    if count == 0:
        raise Fault('ILLI', 'immu6 == 0 (contract §15.1)')
    if dst_bank in ('rd', 'rb') and dst_first == 0:
        raise Fault('ILLI', f'block-copy dst {dst_bank}0 (contract §15.1)')
    if dst_first + count > 64 or src_first + count > 64:
        raise Fault('ILLI', 'block-copy start+immu6 > 64 (contract §15.1)')


def check_legality(rec, f):
    """Raise Fault(ILLI) on static operand-legality violation (contract §15.1).

    Static = derivable from the instruction word alone (register numbers,
    immu6). Dynamic checks (orrr shamt/hd, MALIGN, RASOF/RASUF)
    live in _exec.
    """
    iid, fmt = rec['id'], rec['format']
    if not is_supported(rec):
        raise Unsupported(rec['mnemonic'], fmt)

    if rec.get('scope') == 'fp':
        _check_fp_legality(rec, f)
        return

    if iid == _ID_SWYM:
        return
    return _check_scalar_legality(rec, f)


def _check_fp_legality(rec, f):
    """Static FP legality from contract-fp and legality_rules.yaml."""
    mn, fmt = rec['mnemonic'], rec['format']
    if mn in ('ftfma', 'fofma'):
        if f['rfha'] == 0:
            raise Fault('ILLI', 'floating destination rf0 (contract-fp §1)')
        return
    if 'rfhb' in f and f['rfhb'] == 0 and rec['id'] != 'rd2rf_orri_rf':
        raise Fault('ILLI', 'floating destination rf0 (contract-fp §1)')
    if rec['id'] in ('cs.eq_rrrr_rf', 'cs.ne_rrrr_rf') and f['rfhc'] == 0:
        raise Fault('ILLI', 'floating destination rf0 (contract-fp §1)')
    if 'rdhb' in f and f['rdhb'] == 0:
        raise Fault('ILLI', 'destination rd0 (contract-fp §15)')
    if fmt in ('orri', 'rrri') and 'immu6' in f:
        count = f['immu6']
        if mn in ('ftrnd', 'fornd'):
            if count not in (0x01, 0x02, 0x04, 0x08, 0x10, 0x20):
                raise Fault('ILLI', 'roundToIntegral selector is not one-hot (contract-fp §18)')
            return
        if mn in ('ftroot', 'foroot'):
            if count != 2:
                raise Fault('ILLI', f'{mn} requires n=2')
        elif count == 0:
            raise Fault('ILLI', 'immu6 == 0 (contract-fp §15)')
        if mn in ('ftroot', 'foroot'):
            return
        for name in ('rfha', 'rfhb', 'rfhc', 'rdhb', 'rdhc'):
            if name in f and f[name] + count > 64:
                raise Fault('ILLI', f'{name} + immu6 > 64 (contract-fp §15)')
        if mn in ('ft2ft', 'ft2fo', 'fo2ft', 'fo2fo'):
            if max(f['rfhb'], f['rfhc']) < min(f['rfhb'] + count, f['rfhc'] + count):
                raise Fault('ILLI', 'convert_ff source and destination ranges overlap')


def _fp_bits(st, n, fmt):
    value = st.rf[n] & MASK64
    return value & fmt.mask


def _fp_write(st, n, bits, fmt):
    if fmt is fp_ref.F32:
        old = st.rf[n]
        st.rf_write(n, (old & ~fmt.mask) | (bits & fmt.mask))
    else:
        st.rf_write(n, bits & MASK64)


def _fp_flags(st, flags):
    st.rf_write(0, st.rf[0] | (flags & 0x1F))


def _fp_execute(rec, f, st):
    mn, fmtname = rec['mnemonic'], rec['mnemonic'].split('.')[0]
    iid = rec['id']
    mode = (st.rf[0] >> 32) & 3
    if fmtname.startswith('ft') or mn.startswith(('ft', 'it2ft', 'io2ft', 'ut2ft', 'uo2ft')):
        fmt = fp_ref.F32
    else:
        fmt = fp_ref.F64

    if mn in ('ld.t', 'ld.o', 'ldm.t', 'ldm.o', 'st.t', 'st.o', 'stm.t', 'stm.o'):
        width = 4 if mn.endswith('.t') else 8
        load = mn.startswith('ld')
        multi = mn.startswith(('ldm', 'stm'))
        base = st.rb_read(f['rbhb']) & MASK48
        index = st.rd_read(f['rdhc']) & MASK48 if multi else 0
        count = f['immu6'] if multi else 1
        offset = f['imms12'] if not multi else 0
        eas = [((base + index + i * width) if multi else (base + offset)) & MASK48
               for i in range(count)]
        for ea in eas:
            _check_align(ea, width)
        regs = [f['rfha'] + i for i in range(count)]
        if load:
            values = [st.load_mem(ea, width) for ea in eas]
            for reg, value in zip(regs, values):
                if width == 4:
                    _fp_write(st, reg, value, fp_ref.F32)
                else:
                    st.rf_write(reg, value)
        else:
            values = [st.rf[reg] & ((1 << (8 * width)) - 1) for reg in regs]
            for ea, value in zip(eas, values):
                st.store_mem(ea, width, value)
        return

    if rec['format'] == 'rwii' and 'rfha' in f:
        shift = f['wpN'] * 16
        mask = MASK16 << shift
        value = (st.rf[f['rfha']] & ~mask) | ((f['immu16'] & MASK16) << shift)
        st.rf_write(f['rfha'], value)
        return
    if iid == 'rd2rf_orri_rf':
        values = [st.rd_read(f['rdhc'] + i) for i in range(f['immu6'])]
        for i, value in enumerate(values): st.rf_write(f['rfhb'] + i, value)
        return
    if iid == 'rf2rd_orri_rf':
        values = [st.rf[f['rfhc'] + i] for i in range(f['immu6'])]
        for i, value in enumerate(values): st.rd_write(f['rdhb'] + i, value)
        return
    if mn.startswith('cs.'):
        if mn in ('cs.n', 'cs.z', 'cs.p'):
            v = st.rd_read(f['rdha'])
            condition = ((v >> 63) != 0 if mn == 'cs.n' else
                         v == 0 if mn == 'cs.z' else (v != 0 and (v >> 63) == 0))
            source = f['rfhc'] if condition else f['rfhd']
            st.rf_write(f['rfhb'], st.rf[source])
        else:
            eq = st.rd_read(f['rdha']) == st.rd_read(f['rdhb'])
            if eq == (mn == 'cs.eq'):
                st.rf_write(f['rfhc'], st.rf[f['rfhd']])
        return
    if mn in ('ftcls', 'focls'):
        for i in range(f['immu6']):
            st.rd_write(f['rdhb'] + i, fp_ref.classify(_fp_bits(st, f['rfhc'] + i, fmt), fmt))
        return
    if mn in ('ft2ft', 'ft2fo', 'fo2ft', 'fo2fo'):
        src = fp_ref.F32 if mn.startswith('ft') else fp_ref.F64
        dst = fp_ref.F32 if mn.endswith('ft') else fp_ref.F64
        values = [st.rf[f['rfhc'] + i] & src.mask for i in range(f['immu6'])]
        results = [fp_ref.convert_float(v, src, dst, mode) for v in values]
        for i, (value, flags) in enumerate(results):
            _fp_write(st, f['rfhb'] + i, value, dst)
            _fp_flags(st, flags)
        return
    if mn.endswith(('2it', '2io', '2ut', '2uo')):
        src = fp_ref.F32 if mn.startswith('ft') else fp_ref.F64
        width = 32 if mn.endswith(('2it', '2ut')) else 64
        signed = mn.endswith(('2it', '2io'))
        values = [_fp_bits(st, f['rfhc'] + i, src) for i in range(f['immu6'])]
        results = [fp_ref.convert_to_int(v, src, width, signed, mode) for v in values]
        for i, (value, flags) in enumerate(results):
            st.rd_write(f['rdhb'] + i, _sext(value, width) & MASK64 if signed else value)
            _fp_flags(st, flags)
        return
    if mn.endswith(('2ft', '2fo')) and mn[:2] in ('it', 'io', 'ut', 'uo'):
        dst = fp_ref.F32 if mn.endswith('2ft') else fp_ref.F64
        width = 32 if mn.startswith(('it', 'ut')) else 64
        signed = mn.startswith(('it', 'io'))
        values = [st.rd_read(f['rdhc'] + i) for i in range(f['immu6'])]
        if signed: values = [_sext(v, width) for v in values]
        else: values = [v & ((1 << width) - 1) for v in values]
        results = [fp_ref.convert_int(v, dst, mode) for v in values]
        for i, (value, flags) in enumerate(results):
            _fp_write(st, f['rfhb'] + i, value, dst)
            _fp_flags(st, flags)
        return
    if mn in ('ftroot', 'foroot'):
        value = _fp_bits(st, f['rfhc'], fmt)
        result, flags = fp_ref.sqrt(value, fmt, mode)
        _fp_write(st, f['rfhb'], result, fmt); _fp_flags(st, flags)
        return
    if mn in ('ftsgnj', 'ftsgnn', 'fosgnj', 'fosgnn'):
        a, b = st.rf[f['rfhc']], st.rf[f['rfhd']]
        mask = fmt.mask
        signmask = 1 << fmt.sign_shift
        result = (a & mask & ~signmask) | (((b >> fmt.sign_shift) ^ int(mn.endswith('sgnn'))) << fmt.sign_shift)
        _fp_write(st, f['rfhb'], result, fmt)
        return
    if mn in ('ftqcmp', 'ftscmp', 'foqcmp', 'foscmp'):
        a_bits, b_bits = _fp_bits(st, f['rfhc'], fmt), _fp_bits(st, f['rfhd'], fmt)
        a, b = fp_ref.decode(a_bits, fmt), fp_ref.decode(b_bits, fmt)
        if a[1] == 'nan' or b[1] == 'nan':
            signaling = mn.endswith('scmp')
            rdval = fmt.canonical_snan if signaling else fmt.canonical_qnan
            flags = fp_ref.NV if signaling or (a[1] == 'nan' and not a[3] & fmt.qbit) or (b[1] == 'nan' and not b[3] & fmt.qbit) else 0
        else:
            if a[1] == 'inf' or b[1] == 'inf':
                av = -1 if a[1] == 'inf' and a[0] else 1 if a[1] == 'inf' else 0
                bv = -1 if b[1] == 'inf' and b[0] else 1 if b[1] == 'inf' else 0
                rdval = (av > bv) - (av < bv) if a[1] == 'inf' or b[1] == 'inf' else 0
                if a[1] != 'inf' and b[1] == 'inf': rdval = -bv
                if a[1] == 'inf' and b[1] != 'inf': rdval = av
            else:
                av, bv = a[2] or 0, b[2] or 0
                rdval = (av > bv) - (av < bv)
            flags = 0
        st.rd_write(f['rdhb'], rdval & MASK64); _fp_flags(st, flags)
        return
    if mn in ('ftfma', 'fofma'):
        result, flags = fp_ref.fma(_fp_bits(st, f['rfhb'], fmt),
                                   _fp_bits(st, f['rfhc'], fmt),
                                   _fp_bits(st, f['rfhd'], fmt), fmt, mode)
        _fp_write(st, f['rfha'], result, fmt)
        _fp_flags(st, flags)
        return
    if mn in ('ftrnd', 'fornd'):
        result, flags = fp_ref.round_to_integral(_fp_bits(st, f['rfhc'], fmt),
                                                 fmt, f['immu6'], mode)
        _fp_write(st, f['rfhb'], result, fmt)
        _fp_flags(st, flags)
        return
    if mn in ('ftmin', 'ftmax', 'fomin', 'fomax'):
        result, flags = fp_ref.minmax('min' if mn.endswith('min') else 'max',
                                      _fp_bits(st, f['rfhc'], fmt),
                                      _fp_bits(st, f['rfhd'], fmt), fmt)
        _fp_write(st, f['rfhb'], result, fmt)
        _fp_flags(st, flags)
        return
    if mn in ('ftsclb', 'fosclb'):
        exponent = _sext(st.rd_read(f['rdhd']), 64)
        result, flags = fp_ref.scaleb(_fp_bits(st, f['rfhc'], fmt), exponent, fmt, mode)
        _fp_write(st, f['rfhb'], result, fmt); _fp_flags(st, flags)
        return
    if rec['format'] == 'orrr' and mn[:2] in ('ft', 'fo'):
        op = {'add':'add', 'sub':'sub', 'mul':'mul', 'div':'div', 'rem':'rem'}.get(mn[2:])
        if op:
            result, flags = fp_ref.arithmetic(op, _fp_bits(st, f['rfhc'], fmt),
                                              _fp_bits(st, f['rfhd'], fmt), fmt, mode)
            _fp_write(st, f['rfhb'], result, fmt); _fp_flags(st, flags)
            return
    raise Unsupported(mn, rec['format'])


def _check_scalar_legality(rec, f):
    iid, fmt = rec['id'], rec['format']
    if iid == _ID_RET and f['rdha'] == 0 and f['imms18'] != 0:
        raise Fault('ILLI', 'ret rd0 requires immediate zero')
    # Branches/jumps/calls/ret: sources only; ret rd0 is legal (§8.2/§8.5)
    if iid in _BR_RD or iid in _BR_RB or iid in _BR_DUAL or iid in (
            _ID_JUMP_I, _ID_JUMP_R, _ID_CALL_I, _ID_CALL_R, _ID_RET):
        return

    if iid in _DUAL_DEST:                           # §6.1.1/§6.1.4
        a, b = f['rdha'], f['rdhb']
        if a == 0 and b == 0:
            raise Fault('ILLI', 'both dst == rd0 (contract §6.1.1)')
        if a == b and a != 0:
            raise Fault('ILLI', 'rdha == rdhb non-rd0 (contract §6.1.1)')
        return
    if iid in _COND_DST_HB:                         # §6.5 dst=rdhb
        if f['rdhb'] == 0:
            raise Fault('ILLI', 'cond-assign dst rdhb == rd0 (contract §6.5)')
        return
    if iid in _COND_DST_HC:                         # §6.5 dst=rdhc
        if f['rdhc'] == 0:
            raise Fault('ILLI', 'cond-assign dst rdhc == rd0 (contract §6.5)')
        return

    if fmt == 'rrii':
        if iid in _ST_INFO:
            return
        if 'rdha' in f and f['rdha'] == 0:
            raise Fault('ILLI', 'rdha == rd0 (contract §15.1)')
        if 'rbha' in f and f['rbha'] == 0:
            raise Fault('ILLI', 'rbha == rb0 (contract §15.1)')
        return
    if fmt == 'rrri':
        # multi: zero-dst + immu6 range + bank boundary (§3.1.2/§3.2/§3.3.2)
        if 'rdha' in f:
            if f['rdha'] == 0 and iid not in _ST_INFO:
                raise Fault('ILLI', 'rdha == rd0 (contract §15.1)')
            _check_multi_range(f['rdha'], f['immu6'], 'rd')
        elif 'rbha' in f:
            if f['rbha'] == 0 and iid not in _ST_INFO:
                raise Fault('ILLI', 'rbha == rb0 (contract §15.1)')
            _check_multi_range(f['rbha'], f['immu6'], 'rb')
        elif 'raha' in f:                           # ra0 legal, no zero check
            _check_multi_range(f['raha'], f['immu6'], 'ra')
        return
    if fmt == 'riii':
        # add.si-rd (§6.1.3): rdha != rd0; add.si-rb: rbha != rb0
        if 'rdha' in f and f['rdha'] == 0:
            raise Fault('ILLI', 'rdha == rd0 (contract §15.1)')
        if 'rbha' in f and f['rbha'] == 0:
            raise Fault('ILLI', 'rbha == rb0 (contract §15.1)')
        return
    if fmt == 'rwii':
        if 'rdha' in f and f['rdha'] == 0:
            raise Fault('ILLI', 'wyde dst rdha == rd0 (contract §15.1)')
        if 'rbha' in f and f['rbha'] == 0:
            raise Fault('ILLI', 'wyde dst rbha == rb0 (contract §15.1)')
        return
    if fmt == 'orri':
        mn = rec['mnemonic']
        if mn in ('rd2rd', 'rb2rd', 'rd2rb', 'rb2rb', 'ra2rd', 'rd2ra'):
            dst_nm = [k for k in f if k in ('rdhb', 'rbhb', 'rahb')][0]
            src_nm = [k for k in f if k in ('rdhc', 'rbhc', 'rahc')][0]
            _check_blockcopy(f[dst_nm], f[src_nm], f['immu6'], dst_nm[:2])
            if dst_nm[:2] == src_nm[:2] and abs(f[dst_nm] - f[src_nm]) < f['immu6']:
                raise Fault('ILLI', 'same-bank block-copy ranges overlap')
            if mn == 'ra2rd' and f['rdhb'] == 0:    # §3.3.3 explicit
                raise Fault('ILLI', 'ra2rd dst rdhb == rd0 (contract §3.3.3)')
            return
        # orri shift/ext: dst != rd0 + immu6 <= N (§6.4.1/§6.4.2 static part)
        if f['rdhb'] == 0:
            raise Fault('ILLI', 'dst rdhb == rd0 (contract §15.1)')
        suf = mn.split('.')[1]
        if f['immu6'] > _N_BY_SUFFIX[suf]:
            raise Fault('ILLI', f'immu6 {f["immu6"]} > N={_N_BY_SUFFIX[suf]} '
                                f'(contract §6.4)')
        return
    if fmt == 'orrr':
        # orrr dst: rdhb != rd0 (§6.x) or rbhb != rb0 (RB arith §7.1)
        if 'rdhb' in f and f['rdhb'] == 0:
            raise Fault('ILLI', 'dst rdhb == rd0 (contract §15.1)')
        if 'rbhb' in f and f['rbhb'] == 0:
            raise Fault('ILLI', 'dst rbhb == rb0 (contract §15.1)')
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


# ─── compare result helper (contract §6.2/§7.3) ──────────────────────────────

def _cmp3(a, b):
    """Three-way compare -> -1/0/1 packed as 64-bit two's complement."""
    if a < b:
        return MASK64                                  # -1
    if a > b:
        return 1
    return 0


# ─── fixed-width helpers (contract §6.1.2/§6.1.5/§6.2.2/§6.3/§6.4 + §10/§11/§12)

def _suffix_of(mn):
    return mn.split('.')[1]


def _is_signed_suffix(suf):
    return suf in ('sb', 'sw', 'st', 'so')


def _arith_orrr(mn, a64, b64):
    """Fixed-width add/sub/mul (contract §6.1.2 + §10.1.1/§11.1.1/§12.1.1):
    truncate sources to width, operate, truncate to width, then sign/zero-extend
    to 64 (FULL overwrite)."""
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
    """Fixed-width div/rem (contract §6.1.5 + §10.1.2/§11.1.2/§12.1.2). Sources
    truncated to width; defined zero/overflow results; trunc-toward-zero."""
    suf = _suffix_of(mn)
    bits = _BITS_BY_SUFFIX[suf]
    mask = (1 << bits) - 1
    a, b = a64 & mask, b64 & mask
    base = mn.split('.')[0]
    signed = _is_signed_suffix(suf)
    if b == 0:
        r = a if base == 'rem' else mask
        return (_sext(r, bits) & MASK64) if signed else r
    if signed:
        sa, sb = _sext(a, bits), _sext(b, bits)
        if sa == -(1 << (bits - 1)) and sb == -1:
            return 0 if base == 'rem' else sa & MASK64
        q = abs(sa) // abs(sb)                         # trunc toward zero (C99)
        if (sa < 0) != (sb < 0):
            q = -q
        r = sa - q * sb if base == 'rem' else q        # rem sign = dividend
        return _sext(r & mask, bits) & MASK64
    r = (a % b) if base == 'rem' else (a // b)
    return r & mask                                    # zero-extended


def _logic_orrr(mn, c64, d64, old_dst):
    """64-bit logic (SimRISC-04 §4.1); narrow logic encodings are reserved."""
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
    return r & mask


def _shift_orrr_orri(mn, src64, shamt, old_dst):
    """Fixed-width shift (contract §6.4.1 + §10.4.1/§11.4.1/§12.4.1). shamt
    already bound-checked; result sign/zero-extended to the full register."""
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
    return (_sext(r, N + 1) & MASK64) if suf[0] == 's' else r


def _ext_orrr_orri(mn, src64, hd, old_dst):
    """64-bit extension (SimRISC-04 §4.2); bit hd is the last retained bit."""
    suf = _suffix_of(mn)
    N = _N_BY_SUFFIX[suf]
    maskN = (1 << (N + 1)) - 1
    lowmask = (1 << (hd + 1)) - 1
    low = src64 & lowmask
    if suf[0] == 's' and ((src64 >> hd) & 1):
        fill = (~lowmask) & maskN                      # sign extend
    else:
        fill = 0                                       # zero extend
    return (low | fill) & maskN


# ─── wyde immediate helper (contract §5.1 RD / §5.2 RB) ──────────────────────

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


# ─── RegRAS/MemRAS (contract §8.6) ───────────────────────────────────────────

def _ras_push(st, new_addr):
    """SimRISC-00 §2.4.1 C1/C2/C3; RACNT determines validity."""
    new_addr &= MASK48
    used, ptr = (st.ra[0] >> 48) & 63, st.ra[0] & MASK48
    top = st.ra[63]
    if used and (top & MASK48) == new_addr and top >> 48 < 0xFFFF:
        st.ra[63] = top + (1 << 48)
        return
    if used == 63:
        if not ptr:
            raise Fault('RASOF', 'RegRAS full and MemRAS disabled')
        ptr = (ptr - 8) & MASK48
        _check_align(ptr, 8)
        st.store_mem(ptr, 8, st.ra[1])
    # Only valid entries move; inactive slots are unspecified by the ISA.
    for i in range(max(1, 63 - used), 63):
        st.ra[i] = st.ra[i + 1]
    st.ra[63] = (1 << 48) | new_addr
    st.ra[0] = (min(used + 1, 63) << 48) | ptr


def _ras_pop(st):
    """SimRISC-00 §2.4.2 D1–D4b; validate before changing state."""
    used, ptr = (st.ra[0] >> 48) & 63, st.ra[0] & MASK48
    if used:
        top = st.ra[63]
        count, addr = top >> 48, top & MASK48
        if not count:
            raise Fault('RASUF', 'valid RegRAS top has zero recursion count')
        if count > 1:
            st.ra[63] -= 1 << 48
        else:
            for i in range(63, 64 - used, -1):
                st.ra[i] = st.ra[i - 1]
            st.ra[64 - used] = 0
            st.ra[0] = ((used - 1) << 48) | ptr
        return addr
    if not ptr:
        raise Fault('RASUF', 'empty RegRAS and MemRAS disabled')
    _check_align(ptr, 8)
    content = st.load_mem(ptr, 8)
    count, addr = content >> 48, content & MASK48
    if not count:
        raise Fault('RASUF', 'MemRAS top has zero recursion count')
    st.ra[0] = (ptr + 8) & MASK48
    if count > 1:
        st.ra[63] = ((count - 1) << 48) | addr
        st.ra[0] |= 1 << 48
    return addr


# ─── memory access helpers (contract §3.1/§3.2/§3.3) ─────────────────────────

def _extend(val, width, signed):
    if signed:                                         # sign-extend to 64
        return _sext(val, width * 8) & MASK64
    return val & MASK64                                # zero-extend / octa


def _check_align(ea, width):
    # contract §3.1.1: byte no fault; wyde/tetra/octa naturally aligned.
    if width > 1 and (ea % width) != 0:
        raise Fault('MALIGN', f'ea=0x{ea:X} width={width} (contract §3.1.1)')


# ─── main execute ────────────────────────────────────────────────────────────

def _exec(word, st):
    rec, f = decode(word)
    iid, fmt, mn = rec['id'], rec['format'], rec['mnemonic']

    check_legality(rec, f)
    st.pc_next = (st.rb_read(0) + 4) & MASK64
    if iid == _ID_SWYM:
        return
    if rec.get('scope') == 'fp':
        _fp_execute(rec, f, st)
        return

    # ── RD rrrr dual-dest arith (contract §6.1.1/§6.1.4) ──────────────────────
    if iid in _DUAL_DEST:
        c, d = st.rd_read(f['rdhc']), st.rd_read(f['rdhd'])
        if iid == _ID_SUB_UO:                          # ADR-0049: rdha = borrow 0/1
            st.rd_write(f['rdhb'], (c - d) & MASK64)
            if f['rdha'] != 0:
                st.rd_write(f['rdha'], 1 if c < d else 0)
            return
        if iid == 'add.uo_rrrr_rd':                    # zero-extend; high = carry
            res = (c + d) & MASK128
        elif iid in ('add.so_rrrr_rd', 'sub.so_rrrr_rd'):  # sign-extend to 128
            res = (_sext(c, 64) + _sext(d, 64) if iid == 'add.so_rrrr_rd'
                   else _sext(c, 64) - _sext(d, 64)) & MASK128
        elif iid == 'mul.uo_rrrr_rd':
            res = (c * d) & MASK128
        else:                                          # mul.so_rrrr_rd
            res = (_sext(c, 64) * _sext(d, 64)) & MASK128
        st.rd_write(f['rdha'], (res >> 64) & MASK64)   # high half
        st.rd_write(f['rdhb'], res & MASK64)           # low half
        return

    # ── RD/RB riii in-place add (contract §6.1.3/§7.2) ────────────────────────
    if iid == _ID_ADD_SI_RD:                           # rdha += sext18, full 64
        st.rd_write(f['rdha'], (st.rd_read(f['rdha']) + f['imms18']) & MASK64)
        return
    if iid == _ID_ADD_SI_RB:                           # full 64-bit (SimRISC-05 §3.1/3.2)
        st.rb_write(f['rbha'], (st.rb_read(f['rbha']) + f['imms18']) & MASK64)
        return
    if iid == _ID_AIP_SI_RB:
        st.rb_write(f['rbha'], (st.rb_read(0) + (f['imms18'] << 12)) & MASK64)
        return

    # ── RD rrii compare (contract §6.2.1) ─────────────────────────────────────
    if iid == _ID_CMP_SI:                              # signed rdhb vs sext12
        st.rd_write(f['rdha'], _cmp3(_sext(st.rd_read(f['rdhb']), 64),
                                     f['imms12']))
        return
    if iid == _ID_CMP_UI:                              # unsigned rdhb vs zext12
        st.rd_write(f['rdha'], _cmp3(st.rd_read(f['rdhb']), f['immu12']))
        return

    # ── RD rrrr cond-assign (contract §6.5) ───────────────────────────────────
    if iid in _COND_DST_HB:                            # cs.n/z/p
        sel = st.rd_read(f['rdha'])
        cond = (_is_neg(sel) if iid == 'cs.n_rrrr_rd' else
                _is_zero(sel) if iid == 'cs.z_rrrr_rd' else _is_pos(sel))
        st.rd_write(f['rdhb'], st.rd_read(f['rdhc'] if cond else f['rdhd']))
        return
    if iid in _COND_DST_HC:                            # cs.eq/ne
        eq = st.rd_read(f['rdha']) == st.rd_read(f['rdhb'])
        if (eq and iid == 'cs.eq_rrrr_rd') or (not eq and iid == 'cs.ne_rrrr_rd'):
            st.rd_write(f['rdhc'], st.rd_read(f['rdhd']))
        return

    # ── rwii wyde immediate (contract §5.1 RD / §5.2 RB) ───────────────────────
    if fmt == 'rwii':
        imm16 = f['immu16']
        if 'rdha' in f:
            st.rd_write(f['rdha'], _apply_wyde(mn, st.rd_read(f['rdha']),
                                               f['wpN'], imm16))
        else:
            st.rb_write(f['rbha'], _apply_wyde(mn, st.rb_read(f['rbha']),
                                               f['wpN'], imm16))
        return

    # ── orri block copy (contract §4.1/§4.2/§3.3.3; full 64-bit) ───────
    # Legality rejects intersecting ranges within the same bank.
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

    # ── MISC fixed-width orrr/orri (contract §6.1.2/§6.1.5/§6.2.2/§6.3/§6.4 ────
    #     + §10/§11/§12 counterparts) ──────────────────────────────────────────
    if fmt in ('orrr', 'orri') and mn.split('.')[0] in (
            'add', 'sub', 'mul', 'div', 'rem', 'cmp', 'and', 'or', 'xor',
            'xnor', 'shl', 'shr', 'ext'):
        base = mn.split('.')[0]
        # RB arithmetic (contract §7.1): FULL 64-bit (SimRISC-05 §3.1/3.2)
        if iid in (_ID_ADD_SO_RB, _ID_SUB_SO_RB):
            a, b = st.rb_read(f['rbhc']), st.rd_read(f['rdhd'])
            st.rb_write(f['rbhb'], ((a + b) if iid == _ID_ADD_SO_RB
                                    else (a - b)) & MASK64)
            return
        if iid == _ID_SUB_RB_RD:
            st.rd_write(f['rdhb'], st.rb_read(f['rbhc']) - st.rb_read(f['rbhd']))
            return
        # RB compare (contract §7.3): full 64-bit unsigned.
        if iid == _ID_CMP_UO_RB:
            st.rd_write(f['rdhb'], _cmp3(st.rb_read(f['rbhc']), st.rb_read(f['rbhd'])))
            return
        suf = _suffix_of(mn)
        bits = _BITS_BY_SUFFIX[suf]
        if base in ('add', 'sub', 'mul'):              # §6.1.2 full overwrite
            st.rd_write(f['rdhb'], _arith_orrr(mn, st.rd_read(f['rdhc']),
                                               st.rd_read(f['rdhd'])))
            return
        if base in ('div', 'rem'):                     # §6.1.5 full overwrite
            st.rd_write(f['rdhb'], _divrem_orrr(mn, st.rd_read(f['rdhc']),
                                                st.rd_read(f['rdhd'])))
            return
        if base == 'cmp':                              # §6.2.2 full 64-bit -1/0/1
            mask = (1 << bits) - 1
            a, b = st.rd_read(f['rdhc']) & mask, st.rd_read(f['rdhd']) & mask
            if _is_signed_suffix(suf):
                a, b = _sext(a, bits), _sext(b, bits)
            result = _cmp3(a, b)
            st.rd_write(f['rdhb'], result)          # §6.2.2: -1/0/1 fills 64 bits
            return
        if base in ('and', 'or', 'xor', 'xnor'):       # §6.3 full 64-bit logic
            st.rd_write(f['rdhb'], _logic_orrr(mn, st.rd_read(f['rdhc']),
                                               st.rd_read(f['rdhd']),
                                               st.rd_read(f['rdhb'])))
            return
        if base in ('shl', 'shr', 'ext'):              # §6.4 value result + bound check
            N = _N_BY_SUFFIX[suf]
            if fmt == 'orri':
                amt = f['immu6']                       # static ≤N in legality
            else:                                      # orrr: rdhd[5:0] (SimRISC-04 §4.2)
                amt = st.rd_read(f['rdhd']) & 0x3F
                if amt > N:
                    raise Fault('ILLI', f'{mn} shamt/hd {amt} > N={N} '
                                        f'(contract §6.4)')
            if base == 'ext':
                st.rd_write(f['rdhb'], _ext_orrr_orri(mn, st.rd_read(f['rdhc']),
                                                      amt, st.rd_read(f['rdhb'])))
            else:
                st.rd_write(f['rdhb'], _shift_orrr_orri(mn, st.rd_read(f['rdhc']),
                                                        amt, st.rd_read(f['rdhb'])))
            return

    # ── loads ───────────────────────────────────────────────────────────────
    if iid in _LD_INFO and fmt == 'rrii':              # single (§3.1.1/§3.2/§3.3.1)
        width, signed = _LD_INFO[iid]
        ea = ((st.rb_read(f['rbhb']) & MASK48) + f['imms12']) & MASK48
        _check_align(ea, width)
        val = _extend(st.load_mem(ea, width), width, signed)
        if 'rbha' in f:
            st.rb_write(f['rbha'], val)                # full 64-bit (§3.2)
        elif 'raha' in f:
            st.ra_write(f['raha'], val)                # full 64-bit (§3.3.1)
        else:
            st.rd_write(f['rdha'], val)
        return
    if iid in _LD_INFO and fmt == 'rrri':              # multi (§3.1.2/§3.2/§3.3.2)
        width, signed = _LD_INFO[iid]
        base = st.rb_read(f['rbhb']) & MASK48
        idx = st.rd_read(f['rdhc']) & MASK48           # snapshot (§3.1.2)
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
    if iid in _ST_INFO and fmt == 'rrii':              # single (§3.1.1/§3.2/§3.3.1)
        width = _ST_INFO[iid]
        ea = ((st.rb_read(f['rbhb']) & MASK48) + f['imms12']) & MASK48
        _check_align(ea, width)
        src_nm = 'rbha' if 'rbha' in f else ('raha' if 'raha' in f else 'rdha')
        src = {'rdha': st.rd_read, 'rbha': st.rb_read,
               'raha': st.ra_read}[src_nm](f[src_nm])
        st.store_mem(ea, width, src & ((1 << (width * 8)) - 1))
        return
    if iid in _ST_INFO and fmt == 'rrri':              # multi (§3.1.2/§3.2/§3.3.2)
        width = _ST_INFO[iid]
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

    # ── control flow (contract §8; rb0 = current addr, ADR-0004 D6.5) ──────────
    rb0 = st.rb_read(0)
    if iid in _BR_RD:                                  # single-reg RD (§8.2.2)
        if _cond_br_rd(mn, st.rd_read(f['rdha'])):
            st.pc_next = (rb0 + (f['imms18'] << 2)) & MASK64
        return
    if iid in _BR_RB:                                  # RB zero test (§8.2.3)
        is_zero = (st.rb_read(f['rbha']) & MASK64) == 0
        if (is_zero and iid == _ID_BR_Z_RB) or (not is_zero and iid == _ID_BR_NZ_RB):
            st.pc_next = (rb0 + (f['imms18'] << 2)) & MASK64
        return
    if iid in _BR_DUAL:                                # dual-reg (§8.2.1)
        eq = st.rd_read(f['rdha']) == st.rd_read(f['rdhb'])
        if (eq and iid == 'br.eq_rrii_rd') or (not eq and iid == 'br.ne_rrii_rd'):
            st.pc_next = (rb0 + (f['imms12'] << 2)) & MASK64
        return
    if iid == _ID_JUMP_I:                              # §8.3 relative
        st.pc_next = (rb0 + (f['imms24'] << 2)) & MASK64
        return
    if iid == _ID_JUMP_R:                              # §8.3 absolute
        st.pc_next = ((st.rb_read(f['rbha']) & MASK64) +
                      (st.rd_read(f['rdhb']) & MASK64) +
                      (f['imms12'] << 2)) & MASK64
        return
    if iid == _ID_CALL_I:                              # §8.4 relative
        _ras_push(st, (rb0 + 4) & MASK48)            # return addr = PC+4
        st.pc_next = (rb0 + (f['imms24'] << 2)) & MASK64
        return
    if iid == _ID_CALL_R:                              # §8.4 absolute
        _ras_push(st, (rb0 + 4) & MASK48)
        st.pc_next = ((st.rb_read(f['rbha']) & MASK64) +
                      (st.rd_read(f['rdhb']) & MASK64) +
                      (f['imms12'] << 2)) & MASK64
        return
    if iid == _ID_RET:                                 # §8.5
        ret_addr = _ras_pop(st)                        # may raise RASUF
        st.pc_next = ret_addr & MASK48
        st.rd_write(f['rdha'], f['imms18'] & MASK64)   # rdha=rd0 discards (legal)
        return

    raise Unsupported(mn, fmt)


def run(word, input_state=None, pc=DEFAULT_PC, state=None):
    """Execute a single instruction word.

    Returns (State, fault_kind_or_None). On fault the returned state is the
    pre-execution snapshot (precise: no architectural side effect, §15.2).
    Raises Unsupported for out-of-scope instructions, SpecificationGap for
    contract-open inputs, and ValueError for malformed inputs.
    """
    word = _uint(word, 32, 'instruction word')
    decode_fault = None
    if state is None:
        # Decode only to interpret vector memory width; a pending decode fault
        # is reported after the fetch-alignment check, never before it.
        try:
            rec0, _ = decode(word)
            width = mem_width_for(rec0)
        except Fault as ex:
            width, decode_fault = 8, ex.kind
        state = build_state(input_state, pc, mem_width=width)
    if state.pc & 3:
        return state, 'IALIGN'
    if decode_fault:
        return state, decode_fault
    if state.pc != (state.rb_read(0) & MASK48):
        raise ValueError('State.pc must equal low48(State.rb[0])')
    import copy
    work = copy.deepcopy(state)
    try:
        _exec(word, work)
    except Fault as ex:
        return state, ex.kind
    except fp_ref.FPGap as ex:
        rec, _ = decode(word)
        raise SpecificationGap(rec['id'], str(ex)) from ex
    work.rb[0] = work.pc_next & MASK64
    work.pc = work.pc_next & MASK48
    work.pc_next = work.pc
    return work, None


if __name__ == '__main__':
    import sys
    w = int(sys.argv[1], 16)
    rec, f = decode(w)
    print(f"0x{w:08X} -> {rec['id']}({rec['format']}) fields={f}"
          + (" [unsupported]" if not is_supported(rec) else ""))
