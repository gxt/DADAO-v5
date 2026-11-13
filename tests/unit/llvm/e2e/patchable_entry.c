/*
 * Fixture for `-fpatchable-function-entry` (m14-llvm-003).
 *
 * Nothing here depends on the option: both functions are plain external
 * definitions, so the file is also a valid "no option" baseline.  The
 * object-level lit test compiles it with -fpatchable-function-entry=N[,M] and
 * inspects the emitted slots / __patchable_function_entries section; the E2E
 * test links it against the hand-written assembly `main` in
 * patchable_entry_e2e.s, which calls `patched` so the slot really executes.
 *
 * `patched(41) == 0`, which is what the E2E `main` returns: an illegal or
 * mis-sized slot (or a broken link of the section) traps or returns non-zero.
 */

int patched(int x) { return x - 41; }

int patched2(int x) { return x * 3; }
