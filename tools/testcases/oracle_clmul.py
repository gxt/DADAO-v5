#!/usr/bin/env python3
"""Independent oracle for the ``clmul.o`` integration probes (TESTCASES-057t).

Everything in this module is derived from **polynomial arithmetic over GF(2)**
on plain Python integers, plus the published standards' test vectors.  Nothing
is read back from QEMU or LLVM: the probes only print raw observations, and the
expected value of every observation is computed here.

What is modelled, and from where
--------------------------------
``clmul.o`` (carry-less 64x64 -> 128 multiply)
    Semantics: ``rdHA``/``rdHB`` = high/low 64 bits of the GF(2)[x] product
    (``contract-isa.md`` ``clmul.o_rrrr_rd``; ADR-0035 D2/D4; the same source
    LLVM-122t/QEMU-068t were implemented against).  ``clmul()`` below is a
    shift-and-xor product, i.e. the definition itself -- not a copy of any
    implementation.

GHASH (GF(2^128) multiply inside AES-GCM)
    NIST SP 800-38D §6.3 (Algorithm 1: right-shift bit-serial multiply with
    ``R = 0xe1 || 0^120``) and the GCM specification (McGrew & Viega, Appendix
    B test cases, which publish *every intermediate* ``X_i`` as well as
    ``GHASH(H,A,C)``).  The GCM block <-> polynomial bit order ("reflected",
    i.e. the leftmost bit of the block is the highest field element) is the
    single most error-prone point here, so it is modelled twice:

    * ``gf_mul_gcm()``  -- bit-serial right-shift (the standard's own form);
    * ``gf_mul_gcm_via_clmul()`` -- bit-reverse both operands, do one
      ``clmul.o`` product, reduce by ``x^128 + x^7 + x^2 + x + 1``, reverse
      back.  ``selftest_checks()`` proves the two agree (and both reproduce the
      published ``X_1``), which is exactly the bridge the C probe uses.

    The C probe is then judged against ``gf_mul_gcm()`` -- the reference whose
    correctness is pinned by the published ``X_i``/``GHASH`` values, never the
    other way round.

CRC-32C (Castagnoli)
    Parameters are *fixed by the standard* and asserted in ``selftest_checks``:
    poly ``0x1EDC6F41`` (reflected ``0x82F63B78``), init ``0xFFFFFFFF``,
    refin = refout = true, xorout ``0xFFFFFFFF``, check value
    ``crc32c("123456789") == 0xE3069283``.  ``crc32c()`` is bit-serial (no
    table, no clmul) so it cannot share a bug with the C folding kernel; the
    four classic published vectors (32 zero bytes, 32 0xff bytes, the ramp
    00..1f and its reverse) are asserted as the anchors.

Probe protocol (what the C probes print; see ``parse()``)
---------------------------------------------------------
    REV    <label> <in> <out>                          rev64 (bit reversal)
    EDGE   <label> <a> <b> <lo> <hi> <wide_hi> <wide_lo>
    PAIR   <label> <lo> <hi>                           llvm.dadao.clmul {lo,hi}
    GIN    <label> <h> <aad-hex|-> <ct-hex|->          GHASH inputs as used
    CHAIN  <label> <index> <x>                         intermediate Y_i
    GOUT   <label> <s>                                 GHASH(H,A,C)
    CRC    <label> <len> <crc> <fnv1a64-of-data>

Every record is judged here; a probe that prints fewer records than the tables
require is red (missing records are never a pass).

``judge_*(..., mutation=...)`` exists only so the driver can model a *wrong*
expectation (flipped bit / wrong CRC polynomial / swapped clmul halves /
ordinary multiply) and prove the comparison really fails -- the reachable-FAIL
self test.  A mutation never changes what the shipped run asserts.
"""
MASK64 = (1 << 64) - 1
MASK128 = (1 << 128) - 1

# ══════════════════════════════════════════════════════════════════════════
# GF(2)[x] primitives (all on Python integers; no component product imported)
# ══════════════════════════════════════════════════════════════════════════


def clmul(a, b):
    """Full GF(2)[x] product of two non-negative integers (bit i = x^i)."""
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        b >>= 1
    return r


def polymod(value, poly, degree):
    """``value mod poly`` where ``poly`` has degree ``degree`` (implicit bit)."""
    for i in range(value.bit_length() - 1, degree - 1, -1):
        if (value >> i) & 1:
            value ^= poly << (i - degree)
    return value


def rev(value, bits):
    """Reverse the low ``bits`` bits of ``value``."""
    r = 0
    for i in range(bits):
        r = (r << 1) | ((value >> i) & 1)
    return r


def clmul_lo(a, b):
    return clmul(a, b) & MASK64


def clmul_hi(a, b):
    return clmul(a, b) >> 64


# ══════════════════════════════════════════════════════════════════════════
# clmul.o case tables
# ══════════════════════════════════════════════════════════════════════════
# Boundary cells (design §A of the task): 0, 1, the top bit, the top bit of
# both operands (the only way the product reaches bit 126), all-ones, and
# single-bit pairs (1<<k)*(1<<m) == 1<<(k+m) exercised through the instruction.
CLMUL_EDGE_CASES = [
    ("zero_zero", 0, 0),
    ("zero_top", 0, 1 << 63),
    ("one_zero", 1, 0),
    ("one_one", 1, 1),
    ("one_top", 1, 1 << 63),
    ("top_top", 1 << 63, 1 << 63),
    ("top_one", 1 << 63, 1),
    ("zero_bit", 1 << 0, 1 << 63),
    ("all_all", MASK64, MASK64),
    ("all_one", MASK64, 1),
    ("all_top", MASK64, 1 << 63),
    ("msb_pair", 0x8000000000000001, 0x8000000000000001),
    ("alt_alt", 0xAAAAAAAAAAAAAAAA, 0x5555555555555555),
    ("low_high", 0x0123456789ABCDEF, 0xFEDCBA9876543210),
]
# Single-bit pairs: (1<<k)*(1<<m) == 1<<(k+m) -- k+m must stay <= 126 so the
# result is one bit and the high/low half split is unambiguous.
for _k, _m in ((0, 0), (1, 62), (31, 32), (62, 63), (63, 63), (63, 0)):
    CLMUL_EDGE_CASES.append(("bit_%d_%d" % (_k, _m), 1 << _k, 1 << _m))

# Randomised cells: the C probe draws them from a splitmix64 stream with a
# fixed seed (printed with the operands, so the oracle derives the expectation
# from the operands themselves -- no second PRNG to keep in sync).
MIN_RANDOM_EDGES = 64
RANDOM_SEED = 0xC1A50577

# Two 128-bit values for the bit-reversal bridge (REV records).
REV_CASES = [
    ("zero", 0),
    ("all", MASK64),
    ("pattern", 0x0123456789ABCDEF),
    ("top", 1 << 63),
    ("low", 1),
    ("rev_self", 0xF7B3D591E6A2C480),
]


# ══════════════════════════════════════════════════════════════════════════
# GCM / GHASH
# ══════════════════════════════════════════════════════════════════════════
GCM_R = 0xE1 << 120
GCM_POLY = (1 << 128) | 0x87          # x^128 + x^7 + x^2 + x + 1


def gf_mul_gcm(x, y):
    """NIST SP 800-38D Algorithm 1 (bit-serial, right shift)."""
    z = 0
    v = x & MASK128
    for i in range(128):
        if (y >> (127 - i)) & 1:
            z ^= v
        if v & 1:
            v = (v >> 1) ^ GCM_R
        else:
            v >>= 1
    return z & MASK128


def gf_mul_gcm_via_clmul(x, y):
    """The clmul.o bridge: reverse, carry-less multiply, reduce, reverse back.

    ``rev128`` maps the GCM block (leftmost bit = highest field element) onto
    the plain polynomial order that ``clmul.o`` uses.  This function is *not*
    used to judge the C probe; it exists to prove that the bridge the probe
    implements is the same operation as the standard's own definition (see
    ``selftest_checks``).
    """
    a = rev(x & MASK128, 128)
    b = rev(y & MASK128, 128)
    return rev(polymod(clmul(a, b), GCM_POLY, 128), 128)


def _blocks(data):
    """Split bytes into 16-byte big-endian blocks, zero padded."""
    out = []
    for i in range(0, len(data), 16):
        blk = data[i:i + 16]
        out.append(int.from_bytes(blk + b"\x00" * (16 - len(blk)), "big"))
    return out


def ghash_chain(h, aad, ct):
    """Intermediate GHASH values Y_1..Y_m AND the final S (SP 800-38D §6.4).

    The published GCM vectors list ``X_1..X_m`` = ``Y_1..Y_m`` for the A||C part
    and a final step that feeds ``len(A)||len(C)``; both are returned so the
    probe's intermediate values can be judged, not just the tag.
    """
    chain = []
    y = 0
    for b in _blocks(aad) + _blocks(ct):
        y = gf_mul_gcm(y ^ b, h)
        chain.append(y)
    lenblk = ((len(aad) * 8) << 64) | (len(ct) * 8)
    y = gf_mul_gcm(y ^ lenblk, h)
    return chain, y


def ghash(h, aad=b"", ct=b""):
    return ghash_chain(h, aad, ct)[1]


# Published AES-GCM test vectors: "The Galois/Counter Mode of Operation (GCM)",
# McGrew & Viega, Appendix B (identical values in NIST SP 800-38D test cases).
# Each entry publishes H, every intermediate X_i and GHASH(H,A,C) -- the KAT is
# used only to prove this oracle right, never to replace it.
GHASH_KATS = [
    {
        "label": "spec_tc1",
        "h": "66e94bd4ef8a2c3b884cfa59ca342b2e",
        "aad": "",
        "ct": "",
        "chain": [],
        "ghash": "00000000000000000000000000000000",
    },
    {
        "label": "spec_tc2",
        "h": "66e94bd4ef8a2c3b884cfa59ca342b2e",
        "aad": "",
        "ct": "0388dace60b6a392f328c2b971b2fe78",
        "chain": ["5e2ec746917062882c85b0685353deb7"],
        "ghash": "f38cbb1ad69223dcc3457ae5b6b0f885",
    },
    {
        "label": "spec_tc3",
        "h": "b83b533708bf535d0aa6e52980d53b78",
        "aad": "",
        "ct": ("42831ec2217774244b7221b784d0d49c"
               "e3aa212f2c02a4e035c17e2329aca12e"
               "21d514b25466931c7d8f6a5aac84aa05"
               "1ba30b396a0aac973d58e091473f5985"),
        "chain": ["59ed3f2bb1a0aaa07c9f56c6a504647b",
                  "b714c9048389afd9f9bc5c1d4378e052",
                  "47400c6577b1ee8d8f40b2721e86ff10",
                  "4796cf49464704b5dd91f159bb1b7f95"],
        "ghash": "7f1b32b81b820d02614f8895ac1d4eac",
    },
    {
        "label": "spec_tc4",
        "h": "b83b533708bf535d0aa6e52980d53b78",
        "aad": "feedfacedeadbeeffeedfacedeadbeefabaddad2",
        "ct": ("42831ec2217774244b7221b784d0d49c"
               "e3aa212f2c02a4e035c17e2329aca12e"
               "21d514b25466931c7d8f6a5aac84aa05"
               "1ba30b396a0aac973d58e091"),
        "chain": ["ed56aaf8a72d67049fdb9228edba1322",
                  "cd47221ccef0554ee4bb044c88150352",
                  "54f5e1b2b5a8f9525c23924751a3ca51",
                  "324f585c6ffc1359ab371565d6c45f93",
                  "ca7dd446af4aa70cc3c0cd5abba6aa1c",
                  "1590df9b2eb6768289e57d56274c8570"],
        "ghash": "698e57f70e6ecc7fd9463b7260a9ae5f",
    },
]

# Degenerate field elements: the multiply must vanish / stay consistent.
#   * H = 0            -> every product is 0
#   * H = all ones     -> a non-trivial element (oracle-computed reference)
#   * single block     -> the shortest chained path
#   * two blocks       -> chained accumulation (X_2 depends on X_1)
GHASH_EXTRA_CASES = [
    {"label": "zero_h",
     "h": "00000000000000000000000000000000",
     "aad": "",
     "ct": "000102030405060708090a0b0c0d0e0f"
           "101112131415161718191a1b1c1d1e1f"},
    {"label": "ones_h",
     "h": "ffffffffffffffffffffffffffffffff",
     "aad": "00112233445566778899aabbccddeeff",
     "ct": "ffeeddccbbaa99887766554433221100"
           "0f1e2d3c4b5a69788796a5b4c3d2e1f0"},
    {"label": "one_block",
     "h": "c0a1d4b6e8f20a3c5d7e9b1f3a5c7e90",
     "aad": "",
     "ct": "deadbeefcafebabe0123456789abcdef"},
    {"label": "two_blocks",
     "h": "0123456789abcdeffedcba9876543210",
     "aad": "",
     "ct": "00000000000000000000000000000001"
           "80000000000000000000000000000000"},
    {"label": "block_and_half",
     "h": "66e94bd4ef8a2c3b884cfa59ca342b2e",
     "aad": "aabbccddeeff00112233445566778899"
            "001122334455",                       # 22 bytes -> padded block
     "ct": "11111111111111111111111111111111"
           "2222222222222222222222"},             # 11 bytes -> padded block
]


# ══════════════════════════════════════════════════════════════════════════
# CRC-32C (Castagnoli)
# ══════════════════════════════════════════════════════════════════════════
CRC32C_POLY = 0x1EDC6F41              # x^32 + x^28+x^27+x^26+x^25+... (natural)
CRC32C_POLY_REFLECTED = 0x82F63B78    # refin/refout = true representation
CRC32C_INIT = 0xFFFFFFFF
CRC32C_XOROUT = 0xFFFFFFFF
CRC32C_CHECK = (b"123456789", 0xE3069283)


def crc32c(data, poly_reflected=CRC32C_POLY_REFLECTED):
    """Bit-serial CRC-32C (reflected), the standard's definition.

    ``poly_reflected`` exists only for the injection self test (a wrong
    polynomial must be caught); the shipped runs always use CRC-32C's
    ``0x82F63B78``.
    """
    s = CRC32C_INIT
    for byte in data:
        s ^= byte
        for _ in range(8):
            s = (s >> 1) ^ (poly_reflected if s & 1 else 0)
    return s ^ CRC32C_XOROUT


def fnv1a64(data):
    h = 14695981039346656037
    for byte in data:
        h ^= byte
        h = (h * 1099511628211) & MASK64
    return h


def crc_pattern(kind, n):
    """Deterministic data patterns, mirrored by the C probe.

    ``ramp``  b[i] = (i*31 + 7) & 0xff
    ``lcg``   state = 0x123456789abcdef0; state = state*6364136223846793005 +
              1442695040888963407 (mod 2^64); b[i] = state >> 56
    ``zeros`` all zero bytes
    ``ff``    all 0xff bytes
    ``seq``   b[i] = i & 0xff
    ``seqr``  b[i] = (n - 1 - i) & 0xff
    ``string`` the ASCII bytes "123456789" (n must be 9)
    """
    if kind == "ramp":
        return bytes((i * 31 + 7) & 0xFF for i in range(n))
    if kind == "lcg":
        out = bytearray()
        state = 0x123456789ABCDEF0
        for _ in range(n):
            state = (state * 6364136223846793005 + 1442695040888963407) \
                & MASK64
            out.append(state >> 56)
        return bytes(out)
    if kind == "zeros":
        return b"\x00" * n
    if kind == "ff":
        return b"\xff" * n
    if kind == "seq":
        return bytes(i & 0xFF for i in range(n))
    if kind == "seqr":
        return bytes((n - 1 - i) & 0xFF for i in range(n))
    if kind == "string":
        return b"123456789"[:n]
    raise AssertionError("unknown CRC pattern %r" % kind)


# Lengths: 0/1/7/8/9 (sub-chunk, exactly one chunk, chunk+tail), 15/16/17,
# 63/64/65 (chunk boundaries in the folding kernel), 1000 (long) and the
# classic published vectors (32 zero / 0xff / ramp / reversed ramp bytes).
CRC_CASES = [
    ("crc_empty_ramp", "ramp", 0),
    ("crc_one_ramp", "ramp", 1),
    ("crc_seven_ramp", "ramp", 7),
    ("crc_eight_ramp", "ramp", 8),
    ("crc_nine_ramp", "ramp", 9),
    ("crc_fifteen_ramp", "ramp", 15),
    ("crc_sixteen_ramp", "ramp", 16),
    ("crc_seventeen_ramp", "ramp", 17),
    ("crc_sixtythree_lcg", "lcg", 63),
    ("crc_sixtyfour_lcg", "lcg", 64),
    ("crc_sixtyfive_lcg", "lcg", 65),
    ("crc_thousand_lcg", "lcg", 1000),
    ("crc_check123456789", "string", 9),
    ("crc_zeros32", "zeros", 32),
    ("crc_ff32", "ff", 32),
    ("crc_seq32", "seq", 32),
    ("crc_seqr32", "seqr", 32),
]

# Published CRC-32C anchors (the classic crc32c test vectors: 32 zero bytes,
# 32 0xff bytes, bytes 00..1f and their reverse), used to pin the reference.
CRC32C_PUBLISHED = [
    ("zeros32", "zeros", 32, 0x8A9136AA),
    ("ff32", "ff", 32, 0x62A8AB43),
    ("seq32", "seq", 32, 0x46DD794E),
    ("seqr32", "seqr", 32, 0x113FDB5C),
]


# ══════════════════════════════════════════════════════════════════════════
# parsing the probe output
# ══════════════════════════════════════════════════════════════════════════
def _hex(text):
    return int(text, 16)


def _hexbytes(text):
    """'-' = empty; otherwise an even-length lowercase hex string."""
    if text == "-":
        return b""
    return bytes.fromhex(text)


def parse(text):
    """Split probe output into typed records; unknown lines go to ``junk``."""
    out = {"rev": [], "edge": [], "pair": [], "gin": {}, "chain": [],
           "gout": {}, "crc": [], "junk": []}
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        tok = line.split()
        kind = tok[0]
        try:
            if kind == "REV" and len(tok) == 4:
                out["rev"].append({"label": tok[1], "in": _hex(tok[2]),
                                   "out": _hex(tok[3])})
            elif kind == "EDGE" and len(tok) == 8:
                out["edge"].append({"label": tok[1], "a": _hex(tok[2]),
                                    "b": _hex(tok[3]), "lo": _hex(tok[4]),
                                    "hi": _hex(tok[5]),
                                    "wide_hi": _hex(tok[6]),
                                    "wide_lo": _hex(tok[7])})
            elif kind == "PAIR" and len(tok) == 4:
                out["pair"].append({"label": tok[1], "lo": _hex(tok[2]),
                                    "hi": _hex(tok[3])})
            elif kind == "GIN" and len(tok) == 5:
                out["gin"][tok[1]] = {"h": _hex(tok[2]),
                                      "aad": _hexbytes(tok[3]),
                                      "ct": _hexbytes(tok[4])}
            elif kind == "CHAIN" and len(tok) == 4:
                out["chain"].append({"label": tok[1],
                                     "index": int(tok[2]),
                                     "x": _hex(tok[3])})
            elif kind == "GOUT" and len(tok) == 3:
                out["gout"][tok[1]] = _hex(tok[2])
            elif kind == "CRC" and len(tok) == 5:
                out["crc"].append({"label": tok[1], "len": int(tok[2]),
                                   "crc": _hex(tok[3]), "fnv": _hex(tok[4])})
            else:
                out["junk"].append(line)
        except ValueError:
            out["junk"].append(line)
    return out


# ══════════════════════════════════════════════════════════════════════════
# judging
# ══════════════════════════════════════════════════════════════════════════
def _ck(name, expected, actual, detail="", ok=None):
    """One judged check; ``ok`` overrides the expected/actual comparison."""
    return {"name": name, "expected": expected, "actual": actual,
            "ok": bool(expected == actual) if ok is None else bool(ok),
            "detail": detail}


def _apply_mul_mutation(hi, lo, mutation):
    """Model a wrong expectation for one clmul.o cell (injection only)."""
    if mutation == "clmul_half_swap":
        return lo, hi
    return hi, lo


def judge_rev(parsed, mutation=None):
    checks = []
    for rec in parsed["rev"]:
        want = rev(rec["in"], 64)
        got = rec["out"]
        if mutation == "rev_identity":
            want = rec["in"]
        checks.append(_ck("edges/%s: rev64" % rec["label"], "%016x" % want,
                          "%016x" % got,
                          "bit reversal (GCM block order <-> clmul order)"))
    have = {r["label"] for r in parsed["rev"]}
    want = {label for label, _ in REV_CASES}
    checks.append(_ck("edges: rev64 cases present", "0 missing",
                      "missing=%d" % len(want - have),
                      ok=not (want - have),
                      detail="missing=%s" % sorted(want - have)[:4]))
    return checks


def _clmul_expect(a, b, mutation):
    hi, lo = clmul_hi(a, b), clmul_lo(a, b)
    if mutation == "clmul_ordinary_mul":
        prod = a * b
        hi, lo = (prod >> 64) & MASK64, prod & MASK64
    return _apply_mul_mutation(hi, lo, mutation)


def judge_edges(parsed, mutation=None):
    checks = []
    for rec in parsed["edge"]:
        a, b = rec["a"], rec["b"]
        hi, lo = _clmul_expect(a, b, mutation)
        wide_hi, wide_lo = _apply_mul_mutation(hi, lo, mutation)
        checks.append(_ck("edges/%s: low half (llvm.clmul)" % rec["label"],
                          "%016x" % lo, "%016x" % rec["lo"]))
        checks.append(_ck("edges/%s: high half (dadao.clmul.hi)"
                          % rec["label"], "%016x" % hi, "%016x" % rec["hi"]))
        checks.append(_ck("edges/%s: __int128 builtin" % rec["label"],
                          "%016x%016x" % (wide_hi, wide_lo),
                          "%016x%016x" % (rec["wide_hi"], rec["wide_lo"])))
    for rec in parsed["pair"]:
        ab = _pair_ab(parsed, rec)
        if ab is None:
            checks.append(_ck("edges/%s: pair operands" % rec["label"],
                              "EDGE record present", "missing", ok=False))
            continue
        hi, lo = _clmul_expect(ab[0], ab[1], mutation)
        checks.append(_ck("edges/%s: pair lo (llvm.dadao.clmul)" % rec["label"],
                          "%016x" % lo, "%016x" % rec["lo"]))
        checks.append(_ck("edges/%s: pair hi (llvm.dadao.clmul)" % rec["label"],
                          "%016x" % hi, "%016x" % rec["hi"]))
    checks.extend(_coverage_edges(parsed))
    return checks


def _pair_ab(parsed, rec):
    """Operands of a PAIR record (the EDGE record with the same label)."""
    for e in parsed["edge"]:
        if e["label"] == rec["label"]:
            return e["a"], e["b"]
    return None


def _coverage_edges(parsed):
    checks = []
    labels = {r["label"] for r in parsed["edge"]}
    want_edges = {label for label, _a, _b in CLMUL_EDGE_CASES}
    checks.append(_ck("edges: boundary cells present", "0 missing",
                      "missing=%d" % len(want_edges - labels),
                      ok=not (want_edges - labels),
                      detail="missing=%s" % sorted(want_edges - labels)[:4]))
    table = {label: (a, b) for label, a, b in CLMUL_EDGE_CASES}
    drift = [rec["label"] for rec in parsed["edge"]
             if rec["label"] in table
             and (rec["a"], rec["b"]) != table[rec["label"]]]
    checks.append(_ck("edges: boundary operands match the oracle table",
                      "0 drifted", "%d drifted" % len(drift),
                      ok=not drift, detail="drifted=%s" % drift[:4]))
    random = sorted(l for l in labels if l.startswith("rand_"))
    checks.append(_ck("edges: randomised cells", ">= %d" % MIN_RANDOM_EDGES,
                      len(random), ok=len(random) >= MIN_RANDOM_EDGES,
                      detail="seed 0x%08x (splitmix64, printed operands)"
                      % RANDOM_SEED))
    # The product must actually reach the top half on the boundary cell, i.e.
    # this is not a case set where hi is always zero.
    top = [r for r in parsed["edge"] if r["label"] == "top_top"]
    checks.append(_ck("edges: top_top high half non-zero", "!= 0",
                      "%016x" % top[0]["hi"] if top else "missing",
                      ok=bool(top) and top[0]["hi"] != 0,
                      detail="(1<<63)*(1<<63) = 1<<126"))
    return checks


def _ghash_case_table():
    """Every GHASH case: published KATs plus the synthetic ones."""
    table = []
    for kat in GHASH_KATS:
        table.append({
            "label": kat["label"],
            "h": int(kat["h"], 16),
            "aad": bytes.fromhex(kat["aad"]),
            "ct": bytes.fromhex(kat["ct"]),
            "kat": kat,
        })
    for case in GHASH_EXTRA_CASES:
        table.append({
            "label": case["label"],
            "h": int(case["h"], 16),
            "aad": bytes.fromhex(case["aad"]),
            "ct": bytes.fromhex(case["ct"]),
            "kat": None,
        })
    return table


def judge_ghash(parsed, mutation=None):
    checks = []
    table = _ghash_case_table()
    have = set(parsed["gin"]) & set(parsed["gout"])
    want = {c["label"] for c in table}
    checks.append(_ck("ghash: all cases observed", "0 missing",
                      "missing=%d" % len(want - have),
                      ok=not (want - have),
                      detail="missing=%s" % sorted(want - have)[:4]))
    for case in table:
        label = case["label"]
        if label not in have:
            checks.append(_ck("ghash/%s: record present" % label, "present",
                              "missing", False))
            continue
        gin, s = parsed["gin"][label], parsed["gout"][label]
        checks.append(_ck("ghash/%s: input H" % label,
                          "%032x" % case["h"], "%032x" % gin["h"],
                          detail="probe input must equal the case data"))
        checks.append(_ck("ghash/%s: input AAD" % label,
                          case["aad"].hex() or "-", gin["aad"].hex() or "-"))
        checks.append(_ck("ghash/%s: input C" % label,
                          case["ct"].hex() or "-", gin["ct"].hex() or "-"))
        chain, ref = ghash_chain(case["h"], case["aad"], case["ct"])
        if case["kat"]:
            # Anchor: the *published* intermediates and GHASH(H,A,C).
            for i, published in enumerate(case["kat"]["chain"]):
                checks.append(_ck("ghash/%s: X%d (published)" % (label, i + 1),
                                  published, "%032x" % chain[i]))
            want_s = case["kat"]["ghash"]
        else:
            want_s = "%032x" % ref
        got = parsed["gout"][label]
        if mutation == "ghash_bitflip":
            # Model a wrong *expectation*: flip the lowest bit of the value the
            # oracle says is right.  The comparison must be bit-exact.
            want_s = "%032x" % (int(want_s, 16) ^ 1)
        checks.append(_ck("ghash/%s: GHASH(H,A,C)" % label, want_s,
                          "%032x" % got,
                          detail="published KAT" if case["kat"]
                          else "oracle bit-serial reference"))
        printed = {r["index"] - 1: r["x"] for r in parsed["chain"]
                   if r["label"] == label}
        if len(printed) != len(chain):
            checks.append(_ck("ghash/%s: chain length" % label, len(chain),
                              len(printed)))
        else:
            bad = [i for i in range(len(chain)) if printed[i] != chain[i]]
            checks.append(_ck("ghash/%s: chain values" % label, "0 mismatched",
                              "%d mismatched" % len(bad),
                              detail="" if not bad else "indices %s"
                              % bad[:4]))
    checks.extend(_coverage_ghash(parsed, table))
    return checks


def _coverage_ghash(parsed, table):
    checks = []
    labels = set(parsed["gout"])
    # Coverage classes are derived from the case table itself (never a
    # hard-coded count): single block, chained multi-block, AAD, zero H, all-1 H.
    single = [c["label"] for c in table
              if c["kat"] is None and len(c["ct"]) <= 16 and not c["aad"]]
    multi = [c["label"] for c in table if len(c["ct"]) > 16]
    aad = [c["label"] for c in table if c["aad"]]
    zero_h = [c["label"] for c in table if c["h"] == 0]
    ones_h = [c["label"] for c in table if c["h"] == MASK128]
    for what, group in (("single 16-byte block", single),
                        ("chained multi-block", multi),
                        ("AAD blocks", aad), ("zero H", zero_h),
                        ("H = all ones", ones_h)):
        missing = [l for l in group if l not in labels]
        checks.append(_ck("ghash: %s covered" % what, ">= 1 case",
                          "%d case(s)" % (len(group) - len(missing)),
                          ok=bool(group) and not missing,
                          detail="cases=%s" % group[:4]))
    # The bridge itself: GCM's order and the natural polynomial order differ by
    # a reversal, so a half/bit order mistake would keep this identity false.
    bridge = [c for c in table if c["label"] == "spec_tc2"]
    if bridge:
        c = bridge[0]
        chin = int.from_bytes(c["ct"][:16], "big")
        scal = gf_mul_gcm(c["h"], chin)
        via = gf_mul_gcm_via_clmul(c["h"], chin)
        checks.append(_ck("ghash: rev+clmul bridge == NIST multiply", "equal",
                          "equal" if scal == via else "different",
                          ok=scal == via,
                          detail="X1=%032x (published)" % scal))
    return checks


def judge_crc(parsed, mutation=None):
    checks = []
    poly = 0xEDB88320 if mutation == "crc_ieee_poly" else CRC32C_POLY_REFLECTED
    have = {r["label"]: r for r in parsed["crc"]}
    want = {label for label, _kind, _n in CRC_CASES}
    checks.append(_ck("crc: all cases observed", "0 missing",
                      "missing=%d" % len(want - set(have)),
                      ok=not (want - set(have)),
                      detail="missing=%s" % sorted(want - set(have))[:4]))
    for label, kind, n in CRC_CASES:
        rec = have.get(label)
        if rec is None:
            checks.append(_ck("crc/%s: record present" % label, "present",
                              "missing", False))
            continue
        data = crc_pattern(kind, n)
        checks.append(_ck("crc/%s: length" % label, n, rec["len"]))
        checks.append(_ck("crc/%s: data digest (fnv1a64)" % label,
                          "%016x" % fnv1a64(data), "%016x" % rec["fnv"],
                          detail="pattern=%s" % kind))
        checks.append(_ck("crc/%s: CRC-32C" % label,
                          "%08x" % crc32c(data, poly), "%08x" % rec["crc"]))
    for name, kind, n, published in CRC32C_PUBLISHED:
        data = crc_pattern(kind, n)
        checks.append(_ck("crc: published vector %s" % name,
                          "%08x" % published, "%08x" % crc32c(data, poly),
                          detail="reference pinned to the published value"))
    # The standard's parameter check value, on both sides.
    checks.append(_ck("crc: reference check value (\"123456789\")",
                      "%08x" % CRC32C_CHECK[1],
                      "%08x" % crc32c(CRC32C_CHECK[0], poly),
                      detail="poly 0x%08x init 0x%08x refin/refout true "
                      "xorout 0x%08x" % (poly, CRC32C_INIT, CRC32C_XOROUT)))
    # The clmul path must be reached: the lengths above include whole 8-byte
    # chunks, and the folding kernel is the only consumer of clmul.o.
    chunked = [label for label, _k, n in CRC_CASES if n >= 8]
    checks.append(_ck("crc: whole-chunk cases present", ">= 1",
                      len(chunked), ok=bool(chunked),
                      detail="cases=%s" % chunked[:4]))
    return checks


# ══════════════════════════════════════════════════════════════════════════
# oracle self test (proves the reference before it judges anything)
# ══════════════════════════════════════════════════════════════════════════
def selftest_checks():
    """Identities that pin the reference implementations (no component used)."""
    checks = []

    def ck(name, expected, actual, detail=""):
        checks.append(_ck("oracle: " + name, expected, actual, detail))

    # --- clmul.o: algebraic identities on the definition ---------------------
    idents = [("one_left", 0x0123456789ABCDEF), ("one_right", 0xFEDCBA9876543210),
              ("all_ones", MASK64), ("top", 1 << 63)]
    for name, a in idents:
        ck("clmul(a,1) == a [%s]" % name, "%016x" % a,
           "%016x" % clmul(a, 1))
        ck("clmul(1,a) == a [%s]" % name, "%016x" % a,
           "%016x" % clmul(1, a))
    for k, m in ((0, 0), (3, 60), (31, 32), (62, 64), (63, 63)):
        ck("clmul(1<<%d,1<<%d) == 1<<%d" % (k, m, k + m), "%032x"
           % (1 << (k + m)), "%032x" % clmul(1 << k, 1 << m))
    pairs = [(0xDEADBEEFCAFEBABE, 0x0123456789ABCDEF),
             (MASK64, MASK64), (0x8000000000000000, 0x7FFFFFFFFFFFFFFF),
             (0xAAAAAAAAAAAAAAAA, 0x5555555555555555)]
    for a, b in pairs:
        ck("commutativity [%016x,%016x]" % (a, b), "%032x" % clmul(a, b),
           "%032x" % clmul(b, a))
    triples = [(3, 5, 7), (MASK64, 1 << 63, 0xFFFF),
               (0x0123456789ABCDEF, 0xFEDCBA9876543210, 0x0F0F0F0F0F0F0F0F)]
    for a, b, c in triples:
        ck("associativity [%x,%x,%x]" % (a, b, c),
           "%032x" % clmul(clmul(a, b), c),
           "%032x" % clmul(a, clmul(b, c)))
    for a, b, c in triples:
        ck("distributivity a*(b^c) [%x,%x,%x]" % (a, b, c),
           "%032x" % (clmul(a, b) ^ clmul(a, c)),
           "%032x" % clmul(a, b ^ c))
    # High/low split identity: (hi << 64) | lo == full product.
    for a, b in pairs:
        ck("hi/lo split [%016x,%016x]" % (a, b), "%032x" % clmul(a, b),
           "%032x" % ((clmul_hi(a, b) << 64) | clmul_lo(a, b)))

    # --- GHASH: the two independent formulations must agree, on the
    #     published operands and on random ones ------------------------------
    kat = [k for k in GHASH_KATS if k["label"] == "spec_tc2"][0]
    h = int(kat["h"], 16)
    x1 = int.from_bytes(bytes.fromhex(kat["ct"]), "big")
    ck("GHASH multiply: bit-serial == published X1 (GCM App.B tc2)",
       kat["chain"][0], "%032x" % gf_mul_gcm(h, x1))
    ck("GHASH multiply: rev+clmul == bit-serial", "%032x" % gf_mul_gcm(h, x1),
       "%032x" % gf_mul_gcm_via_clmul(h, x1))
    for i, (a, b) in enumerate((
            (0x0123456789ABCDEFFEDCBA9876543210,
             0xFEDCBA98765432100123456789ABCDEF),
            (MASK128, MASK128), (0, 0xDEADBEEF),
            (1 << 127, 1 << 127), (1, MASK128))):
        ck("GHASH multiply: rev+clmul == bit-serial [rand%d]" % i,
           "%032x" % gf_mul_gcm(a, b), "%032x" % gf_mul_gcm_via_clmul(a, b))
    # Field axioms on the GCM multiply.
    ck("GHASH multiply: x*1 == x", "%032x" % 0x0123456789ABCDEF,
       "%032x" % gf_mul_gcm(0x0123456789ABCDEF, 1 << 127))
    ck("GHASH multiply: commutativity", "%032x" % gf_mul_gcm(h, x1),
       "%032x" % gf_mul_gcm(x1, h))
    # Every published KAT, chain included.
    for kat in GHASH_KATS:
        chain, s = ghash_chain(int(kat["h"], 16), bytes.fromhex(kat["aad"]),
                               bytes.fromhex(kat["ct"]))
        ck("GHASH %s: published GHASH(H,A,C)" % kat["label"], kat["ghash"],
           "%032x" % s)
        ck("GHASH %s: published chain" % kat["label"],
           "|".join(kat["chain"]) or "empty",
           "|".join("%032x" % v for v in chain) or "empty")

    # --- CRC-32C: parameter check value + the classic published vectors -----
    ck("CRC-32C check value (\"123456789\")", "%08x" % CRC32C_CHECK[1],
       "%08x" % crc32c(CRC32C_CHECK[0]),
       detail="poly 0x%08x reflected 0x%08x, init/xorout 0x%08x, refin/refout"
       % (CRC32C_POLY, CRC32C_POLY_REFLECTED, CRC32C_INIT))
    ck("CRC-32C empty message == init^xorout", "00000000",
       "%08x" % crc32c(b""))
    for name, kind, n, published in CRC32C_PUBLISHED:
        ck("CRC-32C published vector %s" % name, "%08x" % published,
           "%08x" % crc32c(crc_pattern(kind, n)),
           detail="%s x%d" % (kind, n))
    # A wrong polynomial must not reproduce the check value (guards against a
    # silently mis-parameterised reference).
    ck("CRC-32C: IEEE polynomial is a different function", "different",
       "different" if crc32c(CRC32C_CHECK[0], 0xEDB88320) != CRC32C_CHECK[1]
       else "same")
    return checks


if __name__ == "__main__":  # pragma: no cover - manual probe of the oracle
    bad = [c for c in selftest_checks() if not c["ok"]]
    for c in selftest_checks():
        print("%s %s | expected=%s | actual=%s"
              % ("PASS" if c["ok"] else "FAIL", c["name"], c["expected"],
                 c["actual"]))
    raise SystemExit(1 if bad else 0)
