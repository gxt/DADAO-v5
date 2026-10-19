@@ Definition for the weak hook exercised by tests/e2e/weak_undef_e2e.c
@@ (LLVM-085t).  Linking this object turns `weak_hook` from an *undefined* weak
@@ function into a *defined* one, so the R_DADAO_REL26 call must take the normal
@@ path (a real `call`, in range) and the hook's value (9) must reach the caller
@@ -- i.e. the undefined-weak special case must not apply.
@@
@@ `ret rdha, imms18` returns the immediate in rdha, so this is a one-instruction
@@ function returning 9 (contract-isa.md §8.5).
	.text
	.globl	weak_hook
weak_hook:
	ret	rd8, 9
