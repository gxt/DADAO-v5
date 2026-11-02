@@ RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t.o
@@ RUN: %llvm_readobj -r --expand-relocs %t.o | %FileCheck %s
@@ RUN: echo 'aip.si rb4, %%pcrel_hi(extg)'      | %llvm_mc --triple=dadao-unknown-elf -show-encoding 2>&1 | %FileCheck %s --check-prefix=ENC
@@ RUN: echo 'aip.si rb4, %%pcrel_hi(extg'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-NORPAREN
@@ RUN: echo 'aip.si rb4, %%pcrel_hi extg'      | %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR-NOLPAREN

@@ Relocation specifiers `%pcrel_hi(expr)` / `%pcrel_lo(expr)` (ADR-0029 D2;
@@ contract-elf.md §3.1/§3.2): the assembler must PARSE the '(' ')' pair that
@@ wraps the inner expression and keep it as the fixup's value -- the low half of
@@ the IP-relative pair has no other spelling, so the printer's
@@ `... [rbX, %pcrel_lo(<site>)]` form (what `clang -S` emits) has to read back.
@@
@@ Regression lock (LLVM-095t 遗留①): the parser used to *check* for '(' but not
@@ consume it, so MCAsmParser::parseParenExpression -- documented as "assuming
@@ that an initial '(' has already been consumed" -- swallowed the whole
@@ `(...)` and the trailing parseRParen() then failed on the next token
@@ (`error: expected ')'`).  RUN line 1 fails outright under that defect.
@@
@@ Note: the low half is pinned here through the object file (RUN 1/2); its
@@ `--show-encoding` display is pinned separately in
@@ show-encoding-fixup-bigendian.s.  The streamer used to trip its own
@@ `assert(Bit == 0 && "Encoder wrote into fixed up bit!")` for a partially
@@ covered byte on this big-endian target, because the 12-bit fixup's
@@ TargetOffset was given in little-endian bit order; LLVM-132t (ISS-232) moved
@@ it to the MSB-first offset (20).  Object emission was never affected -- that
@@ is what RUN 1/2 pin.
@@
@@ The expectation values are the contract's, not the implementation's: the high
@@ record lands on the `aip.si` imms18 (type 14) and the low record on the paired
@@ `ld.o` imms12 (type 15) with the *site* as pairing information (section
@@ symbol `.text` + addend = site address, contract-elf.md §3.1).

@@ CHECK:      Relocation {
@@ CHECK-NEXT:   Offset: 0x0
@@ CHECK-NEXT:   Type: R_DADAO_PCREL_HI (14)
@@ CHECK-NEXT:   Symbol: extg
@@ CHECK-NEXT:   Addend: 0x0
@@ CHECK-NEXT: }
@@ CHECK-NEXT: Relocation {
@@ CHECK-NEXT:   Offset: 0x4
@@ CHECK-NEXT:   Type: R_DADAO_PCREL_LO (15)
@@ CHECK-NEXT:   Symbol: .text
@@ CHECK-NEXT:   Addend: 0x0
@@ CHECK-NEXT: }

@@ ENC: aip.si rb4, %pcrel_hi(extg)
@@ ENC: fixup A - offset: 0, value: %pcrel_hi(extg), kind: DADAO_FK_PCREL_HI

@@ ERR-NORPAREN: error: expected ')'
@@ ERR-NOLPAREN: error: expected '(' after '%pcrel_hi'

	.text
	.globl	f
f:
.Lpcrel_hi0:
	aip.si	rb4, %pcrel_hi(extg)
	ld.o	rb4, [rb4, %pcrel_lo(.Lpcrel_hi0)]
