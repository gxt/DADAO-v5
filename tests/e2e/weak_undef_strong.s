@@ Strictness probe for the undefined-weak exception (LLVM-085t / ISS-194): a
@@ *strong* reference must keep failing.  This object references `strong_fn`
@@ without defining it, so
@@   * linked as-is                          -> `undefined symbol: strong_fn`;
@@   * linked with a defined-but-far symbol  (`--defsym strong_fn=<far>`) ->
@@     `relocation R_DADAO_REL26 out of range`.
@@ Both are link-time errors (contract-elf.md §3.2, ADR-0019 §D6); the
@@ undefined-weak exception must not leak into either.
	.text
	.globl	_start
_start:
	call	[rb0, strong_fn]
	ret	rd0, 0
