@@ RUN: %not %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o /dev/null 2>&1 | %FileCheck %s --check-prefix=ERR

@@ `ISS-430` (m20-llvm-003) negative half: only a *resolved* Absolute symbol
@@ may be encoded as a value.  An equate that never resolves keeps its two
@@ symbols, so it is a genuine symbol difference and must still be rejected,
@@ and the operand is named with the diagnostic (not silently encoded as 0).
@@
@@ UVD = U1 - U0 with both operands undefined: nothing to fold.
@@ ERR: error: cannot use 'UVD' (its value is a symbol difference ('A - B')) as an instruction immediate
@@ ERR-NEXT: {{.*}}set.zw{{.*}}rb1, wp0, UVD
@@ XD = L1 - other spans two sections: the difference cannot be folded.
@@ ERR: error: cannot use 'XD' (its value is a symbol difference ('A - B')) as a branch/jump target
@@ ERR-NEXT: {{.*}}jump{{.*}}[rb0, XD]
@@ A resolved equate still has to fit the field: BIG = (L1-L0) * 0x80000
@@ (= 0x200000 bytes) is out of range for the 18-bit PC-relative immediate,
@@ so the diagnostic is about the value, not about a symbol difference.
@@ ERR: error: branch/jump target out of range for a 18-bit PC-relative immediate
@@ ERR-NEXT: {{.*}}br.z{{.*}}rb1{{.*}}[rb0, BIG]
@@ The written form `A - B` is not an equate and stays rejected as before.
@@ ERR: error: cannot use a symbol difference ('A - B') as a branch/jump target
@@ ERR-NEXT: {{.*}}jump{{.*}}[rb0, L1 - L0]

	.text
L0:
	swym	0
L1:
	.set	UVD, U1 - U0
	set.zw	rb1, wp0, UVD
	.set	XD, L1 - other
	jump	[rb0, XD]
	.set	BIG, (L1 - L0) * 0x80000
	br.z	rb1, [rb0, BIG]
	jump	[rb0, L1 - L0]
	.section	.data
other:
	.dd.b08	0
