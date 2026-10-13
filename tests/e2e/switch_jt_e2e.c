/* switch_jt_e2e.c — LLVM-072t (M6, ISS-177 / G3) jump-table switch E2E vector.
 *
 * Freestanding (no libc): crt0 reports the `main` return value as the guest
 * exit code (tests/scripts/codegen_crt0.s, contract-semihosting.md §3).
 *
 * A dense `switch` is lowered to a jump table (ISD::BR_JT): the table lives in
 * a read-only data section as one 8-byte absolute case address per entry
 * (EK_BlockAddress -> R_DADAO_ABS48) and the dispatch materializes the table
 * base, scales the index, loads the entry and jumps through it (contract-isa.md
 * §8.3 `jump rb, rd, imm12`).  Before LLVM-072t the backend could not select
 * `br_jt` at all, so this file did not even compile.
 *
 * Expected guest exit code is derived by hand from the C semantics (independent
 * of the backend): `main` returns a bitmask whose bit n is set iff check n
 * holds, so the exit code is 255 exactly when every case / default / fallthrough
 * behaves correctly.
 *
 *   bit 0  pick(100) == 3     first table entry
 *   bit 1  pick(107) == 23    middle table entry
 *   bit 2  pick(115) == 59    last table entry
 *   bit 3  pick(200) == 0     above the range  -> default
 *   bit 4  pick(99)  == 0     below the range  -> default
 *   bit 5  fall(0)   == 7     0 -> 1 -> 2 fallthrough chain (1+2+4)
 *   bit 6  fall(3)   == 24    3 -> 4 fallthrough (8+16)
 *   bit 7  fall(4)   == 16    stops at case 4, no fallthrough into case 5
 *   ---------------------------------------------------------------
 *   all bits set  ->  0xFF = 255
 */

/* Dense 16-case jump table (case values 100..115; table index = x - 100). */
long pick(long x) {
  switch (x) {
  case 100: return 3;
  case 101: return 5;
  case 102: return 7;
  case 103: return 11;
  case 104: return 13;
  case 105: return 17;
  case 106: return 19;
  case 107: return 23;
  case 108: return 29;
  case 109: return 31;
  case 110: return 37;
  case 111: return 41;
  case 112: return 43;
  case 113: return 47;
  case 114: return 53;
  case 115: return 59;
  default:  return 0;
  }
}

/* A switch whose cases fall through into one another; the table entries for
 * index 0 and 3 must land on the shared blocks (contract C semantics). */
long fall(long x) {
  long r = 0;
  switch (x) {
  case 0: r += 1;         /* fallthrough */
  case 1: r += 2;         /* fallthrough */
  case 2: r += 4;  break;
  case 3: r += 8;         /* fallthrough */
  case 4: r += 16; break;
  case 5: r += 32; break;
  case 6: r += 64; break;
  case 7: r += 128; break;
  case 8: r += 256; break;
  case 9: r += 512; break;
  default: r += 1000; break;
  }
  return r;
}

long main(void) {
  long ok = 0;
  ok |= (pick(100) == 3)  << 0;
  ok |= (pick(107) == 23) << 1;
  ok |= (pick(115) == 59) << 2;
  ok |= (pick(200) == 0)  << 3;
  ok |= (pick(99)  == 0)  << 4;
  ok |= (fall(0) == 7)    << 5;
  ok |= (fall(3) == 24)   << 6;
  ok |= (fall(4) == 16)   << 7;
  return ok;
}
