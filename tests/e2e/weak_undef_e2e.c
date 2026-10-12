/* Undefined weak function hook, end to end (LLVM-085t / ISS-194).
 *
 * `weak_hook` is declared weak and (in this variant) never defined, so it stays
 * an *undefined weak* function at link time.  ELF weak semantics give such a
 * symbol the value 0, which is what the guard below observes; the call itself
 * is therefore dead.  picolibc uses exactly this idiom for its optional
 * platform hooks (`_user_strerror` in strerror.c, `gettimeofday` in
 * semihost/common/open.c and write.c, `arc4random_abort` /
 * `arc4random_fork_detect` in stdlib/arc4random.c) -- all of which used to fail
 * to link with `R_DADAO_REL26 out of range` because address 0 is 2^47 away from
 * the DADAO image.
 *
 * The program exits 0 on the correct behaviour so the lit gate can use the
 * guest exit code directly:
 *   * undefined weak  -> address 0, guard taken, dead call never entered, 0;
 *   * defined weak (linked with tests/e2e/weak_hook_def.s) -> the guard is not
 *     taken and the definition returns 9, so the exit code is non-zero.
 */
extern int weak_hook(int) __attribute__((weak));

int main(void) {
	if (&weak_hook == (void *)0)
		return 0;		/* undefined weak: address is 0 */
	if (weak_hook == (void *)0)
		return 0;		/* same test, function-pointer form */
	return weak_hook(7) & 0xff;	/* definition present: 9 */
}
