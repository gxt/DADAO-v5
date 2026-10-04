; smoke_fp: minimal FP end-to-end smoke (M2 gate ④).
;
; Pipeline under test:
;   RD immediates -> rd2rf -> RF
;   ftadd  (f32 add, contract-fp.md §5)
;   ft2it  (f32 -> signed int32, contract-fp.md §3)
;   cmp.so (integer equality, contract-isa.md §6.2.2) -> br.nz -> exit port
;
; Program: rf1 = 1.5, rf2 = 2.25; rf3 = ftadd(rf1, rf2); rd3 = ft2it(rf3);
;          PASS iff rd3 == 3.
;
; Exit protocol (ADR-0004 D3): write 8 B to exit port 0xffff_8000_0000;
;   0x00 = PASS, non-zero = FAIL. First write wins.
;
; ── Expected values: INDEPENDENTLY HAND-DERIVED (IEEE-754 binary32) ──────────
; NOT produced, calibrated, or back-filled from llvm-mc / llvm-objdump / QEMU
; output. Every step below is derived from spec/ + contract-fp.md only.
;
;   1.5  = 1.1b  x 2^0 -> sign=0, exp=127=0x7F, mant=0x400000
;                        -> 0_01111111_10000000000000000000000 = 0x3FC00000
;   2.25 = 1.001b x 2^1 -> sign=0, exp=128=0x80, mant=0x200000
;                        -> 0_10000000_00100000000000000000000 = 0x40100000
;
;   ftadd: 1.5 + 2.25 = 3.75 (exact in binary32, no rounding)
;   3.75 = 1.111b x 2^1 -> sign=0, exp=128=0x80, mant=0x700000
;                        -> 0_10000000_11100000000000000000000 = 0x40700000
;
;   ft2it (float->int): 3.75 -> 3.  Round-toward-zero truncation is the
;   project-established f->i semantics (contract-fp.md §3; SimRISC-07
;   §格式转换指令; the task's own candidate scenario states
;   "ft2it 向零截断 -> 3"). Result is 3 = 0x00000003.
;
; ── Bit-pattern construction ────────────────────────────────────────────────
;   set.zw rdN, wp1, immu16 sets wyde #1 = register bits[31:16]; bits[15:0]
;   stay 0 (all other rd/rb/ra = 0 at entry per ADR-0004 D6.5). Thus:
;     rd1 = 0x0000_0000_3FC0_0000  (f32 1.5 in the low 32 bits)
;     rd2 = 0x0000_0000_4010_0000  (f32 2.25)
;   rd2rf copies the full 64-bit word unchanged into RF (contract-fp.md §12);
;   the ft format uses only the low 32 bits (contract-fp.md §1).
;
; NOTE (see smoke_add.s): the wyde position must be written as a named token
;   wp0/wp1/wp2/wp3. Bare numeric 0/1/2/3 is rejected by the assembler (Error);
;   wpN is encoded verbatim (LLVM-045t / ISS-128).
;
; Entry state (ADR-0004 D6.5):
;   rb0=0xffff_0000_0000 (PC), rb1=0xffff_00ff_0000 (SP), rb2=0xffff_0000_0000
;   rd0=0 (hardwired), all other rd/rb/ra = 0; rf0 = FCSR = 0

_start:
    ; 1. Construct exit-port address rb3 = 0xffff_8000_0000
    set.zw  rb3, wp2, 0xffff        ; rb3[47:32] = 0xffff, rest = 0
    or.w    rb3, wp1, 0x8000        ; rb3[31:16] |= 0x8000

    ; 2. f32 bit patterns into RD low 32 bits
    set.zw  rd1, wp1, 0x3fc0        ; rd1 = 0x0000_0000_3FC0_0000
    set.zw  rd2, wp1, 0x4010        ; rd2 = 0x0000_0000_4010_0000

    ; 3. RD -> RF (64-bit block copy, no datatype conversion)
    rd2rf   {rf1}, {rd1}
    rd2rf   {rf2}, {rd2}

    ; 4. FP add: rf3 = 1.5 + 2.25 = 3.75 (0x40700000)
    ftadd   rf3, rf1, rf2

    ; 5. f32 -> int32: rd3 = trunc(3.75) = 3
    ft2it   {rd3}, {rf3}

    ; 6. Compare against hand-derived expectation 3 (cmp.so -> 0 iff equal)
    set.zw  rd4, wp0, 3
    cmp.so  rd5, rd3, rd4
    br.nz   {rd5}?, [rb0, Lfail]

    ; 7. PASS: write 0x00 -> exit port
    st.o    rd5, [rb3, 0]

Lfail:
    ; 8. FAIL: write 0x01 -> exit port
    set.zw  rd7, wp0, 1
    st.o    rd7, [rb3, 0]
    swym    0
