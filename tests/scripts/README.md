# QEMU Semantic Test Harness

## Overview

This directory contains the QEMU-based ISA semantic test harness for `dadao-m1`. The harness builds test binaries from vector YAML files, runs them in QEMU, and reports PASS/FAIL based on exit codes.

**Key design principle (D1)**: No dependency on `llvm-mc`. All instruction words are generated directly via `struct.pack('>I', encoding_word)` from the vector YAML.

## Files

| File | Purpose |
|------|---------|
| `gen_trampoline.py` | Generates ROM trampoline blob (`trampoline.bin`) |
| `trampoline.bin` | ROM trampoline (16 bytes, 4 instructions) |
| `build_test_binary.py` | Builds test binary from vector YAML |
| `run_qemu_test.py` | Main test runner |
| `verify_harness_dump.py` | Harness dump channel verification (QMP protocol, byte layout, 10a `-device loader` channel) |
| `README.md` | This file |

## Quick Start

### Generate trampoline

```bash
python3 tests/scripts/gen_trampoline.py
```

This generates `tests/scripts/trampoline.bin` (16 bytes).

### Run a single test

```bash
python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --case 1
```

### Run all tests in a file

```bash
python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml
```

### Run all vector files (batch mode)

```bash
python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ --batch
```

### Run with diagnostics (dump mode)

```bash
python3 tests/scripts/run_qemu_test.py tests/vectors/isa/reg-arith.yaml --dump
```

## QEMU Binary

The harness expects `qemu-system-dadao` at `.work/build/qemu/qemu-system-dadao` (out-of-tree build). Override with:

```bash
# Environment variable
export QEMU_SYSTEM_DADAO=/path/to/qemu-system-dadao

# Or command-line flag
python3 tests/scripts/run_qemu_test.py --qemu /path/to/qemu-system-dadao ...
```

## Binary Layout

The test binary is loaded at RAM base `0xffff_0000_0000` (ADR-0004 D2.2):

```
[section 1] loader   - Set rd/rb/ra registers from input_state, write memory
[section 2] test     - Raw encoding word (struct.pack('>I', word))
[section 3] dumper   - Dump state to state-dump region (diagnostics only)
[section 4] exit     - Compare expected_state with actual, write exit code
```

### Loader (section 1)

Loads input registers using `set.zw` (clear + set wyde) + `or.w` (merge wyde):

- RD registers: `set.zw rdX, wp0, chunk0` + `or.w rdX, wp1/2/3, chunk`
- RB registers: `set.zw rbX, wp0, chunk0` + `or.w rbX, wp1/2/3, chunk` (rb variant)
- RA registers: load via RD temp → `rd2ra raX, rdY, 1`
- Memory: load address to RB temp, load value to RD temp, `st.o rd, rb, 0`

### Test (section 2)

Raw 4-byte encoding word from `encoding.word` field in the vector YAML.

### Dumper (section 3)

Dumps `rd[1..63]`, `rb[1..63]`, and `rb0` (PC) to state-dump region for diagnostics.

**PC dump mechanism**: `st.o-rb` requires `rbha != rb0` (legality constraint), so `rb0` (PC) cannot be stored directly. The harness uses `rb2rd rd63, rb0, 1` to copy PC into scratch register `rd63`, then `st.o rd63, rb62, 0x400` to store it at the dump region. Encoding from `contracts/opcodes.yaml` (`rb2rd`, format `orri`, op=0x40, ha=0x36).

**State-dump region** (at `0xffff_00fe_0000`, total 1032 bytes):

| Offset | Content | Size | Notes |
|--------|---------|------|-------|
| `0x0000` | `rd[0]` slot | 8 bytes | **Reserved, not written** (rd0 is hardwired zero) |
| `0x0008` | `rd[1..63]` | 504 bytes (rd[i] @ i*8, i=1..63) | big-endian |
| `0x0200` | `rb[0]` slot | 8 bytes | **Reserved, not written** (rb0=PC stored at +0x400) |
| `0x0208` | `rb[1..63]` | 504 bytes (rb[i] @ 0x200+i*8, i=1..63) | big-endian |
| `0x0400` | `pc` (rb0 via `rb2rd`→`st.o-rd`) | 8 bytes | big-endian |

### Exit (section 4)

For **semantic/boundary** cases with `expected_state`:
1. Load expected values into temp registers
2. For RD: XOR actual register with expected
3. For RB: `rb2rd` copies actual RB into scratch RD, then XOR with expected
4. For RA: `ra2rd` copies actual RA into scratch RD, then XOR with expected
5. OR all differences into accumulator
6. If accumulator == 0 → write `0x00` (PASS) to exit port
7. If accumulator != 0 → write `0x01` (FAIL) to exit port

For **encoding** cases (no expected_state, no expected_fault):
- Write `0x00` (PASS) to exit port after test instruction

For **legality** cases with `expected_fault`:
- Write safety-net FAIL code (if fault doesn't happen)
- QEMU handles the fault and writes fault code to exit port

## Exit Code Protocol (ADR-0004 D3/D5)

| Range | Source | Meaning |
|-------|--------|---------|
| `0x00` | Exit port | PASS |
| `0x01`-`0x7F` | Exit port | FAIL (test-defined) |
| `0x80`-`0xFF` | Machine fault | See below |

Machine fault codes (ADR-0004 D5.8):

| Code | Fault | Description |
|------|-------|-------------|
| `0x87` | UNMAPPED | Access to unmapped memory |
| `0x88` | ILLI | Illegal instruction |
| `0x89` | UNDI | Undefined instruction |
| `0x8A` | RASOF | RAS overflow |
| `0x8B` | RASUF | RAS underflow |
| `0x8C` | MALIGN | Memory alignment error |
| `0x8D` | IALIGN | Instruction alignment error |

## Register Conventions (D4)

| Register | Purpose |
|----------|---------|
| `rd60` | Temp for loading expected values |
| `rd61` | XOR+ORR accumulator |
| `rd62` | Exit code |
| `rd63` | Temp for dump |
| `rb60` | Exit port address |
| `rb61` | Temp for memory address |
| `rb62` | Dump pointer |

**Note**: `rd60`-`rd63` and `rb60`-`rb63` are scratch registers. Test vectors must not use these registers for input/expected values.

## State-Dump Mechanism (D7)

**Normal mode**: Dumper section dumps state to memory, then continues to exit section. Host reads exit code from `$?`.

**Dump mode** (`--dump` flag): After dumper section, guest spins (`jump rb0, rd0, 0`) instead of writing to exit port. Host uses QMP to dump memory. The harness starts QEMU with `-S` (frozen CPU), connects to QMP Unix socket, sends `cont` to resume guest, waits for guest to reach spin, then issues `pmemsave` and `quit`:

```bash
# The harness does this automatically. For manual testing:
# Start QEMU with QMP Unix socket and frozen CPU
qemu-system-dadao -machine dadao-m1 -nographic -bios trampoline.bin -kernel test.bin \
  -qmp unix:/tmp/qemu-qmp.sock,server=on,wait=off -S

# Connect to QMP, resume guest, dump memory
# (requires a QMP client; the harness implements this internally via QMPClient)
```

The dump file contains:
- `dump.bin[8:512]`: rd[1..63] (63 × 8 bytes, big-endian, rd[i] @ i*8)
- `dump.bin[520:1024]`: rb[1..63] (63 × 8 bytes, big-endian, rb[i] @ 0x200+i*8)
- `dump.bin[1024:1032]`: pc (rb0, 8 bytes, big-endian)

## Timeout

Default timeout is 9 seconds (ADR-0004 D3). Override with:

```bash
python3 tests/scripts/run_qemu_test.py --timeout 30 ...
```

Timeout is a harness safety net only; it does not affect guest pass/fail determination.

## Schema Field Consumption (D6)

The harness consumes the following fields from vector YAML:

- `encoding.word`: Raw instruction word (hex string)
- `input_state.rd/rb/ra`: Register values to load (hex strings)
- `input_state.memory`: Memory values to write (`address` + `value`)
- `expected_state.rd/rb/ra`: Expected register values for comparison
- `expected_fault`: Expected fault code (ILLI/UNDI/MALIGN/etc.)
- `expected_pc`: Branch target PC (consumed by poison patterns in QEMU-017t/018t)
- `encoding.reserved: true`: Reserved encoding case (skip identity validation)
- `status`: `active`/`deferred` (deferred cases skipped in batch mode)
