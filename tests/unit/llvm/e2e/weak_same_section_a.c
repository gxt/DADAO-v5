/* weak_same_section (ISS-482): a weak definition and its caller in the *same*
 * section (no -ffunction-sections) must still reach the linker.
 *
 * The call to `hook` has to be recorded as an R_DADAO_REL26 relocation: the
 * weak definition is interposable, so the strong definition in
 * weak_same_section_b.c must be able to take over at link time.  Folding the
 * displacement in the assembler made the strong definition unreachable (the
 * kernel's arch_do_signal_or_restart / generic stub case, m14-linux-045).
 *
 * `local_helper` is file-local (STB_LOCAL): its call keeps the in-place fast
 * path and produces no relocation (ISS-482 fix must not bloat local loops).
 */

__attribute__((weak)) void hook(int x) { (void)x; }

static void local_helper(int x) { (void)x; }

void caller(int x) { if (x) hook(x); }

void local_caller(int x) { if (x) local_helper(x); }
