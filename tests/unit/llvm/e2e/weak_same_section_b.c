/* Strong definition of the weak hook from weak_same_section_a.c (ISS-482).
 *
 * After `ld.lld -r a.o b.o` this definition must win, and the caller's
 * R_DADAO_REL26 must resolve to it instead of the (empty) weak body.
 */

volatile int marker;

void hook(int x) { marker = x; }
