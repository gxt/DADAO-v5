/* mcmodel_far.c -- >32 MiB code-layout link test (LLVM-131t; ADR-0036 D1/D5).
 *
 * `far_fn` is emitted into `.far`, which tests/e2e/mcmodel_far.lds places
 * 64 MiB above `.text`, i.e. beyond the +/-32 MiB reach of a direct
 * `call`/`jump` (R_DADAO_REL26).
 *
 *   * `-mcmodel=default`: the call is PC-relative and the link must fail with
 *     "relocation R_DADAO_REL26 out of range" (the existing hard error -- the
 *     control case);
 *   * `-mcmodel=large`: the call target is materialized as a 48-bit absolute
 *     address (ABS48) and called indirectly, so the same layout links.
 *
 * The image is link-only: `.far` sits outside the 16 MiB RAM window of the
 * `dadao-m1` machine, so it is never executed.
 */

__attribute__((noinline, section(".far"))) long far_fn(long x) { return x + 1; }

__attribute__((noinline)) long call_far(long x) { return far_fn(x) + 1; }

int main(void) { return call_far(1) == 3 ? 0 : 1; }
