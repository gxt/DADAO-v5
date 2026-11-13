# arch/hmon — Machine-v5-Tiny `cfx_power` + `cfx3 hmon`

`TESTCASES`-style execution case for the Tiny machine's cfx set
(`m13-gem5-001`): `cfx_power` (cfx63, boot handover) and `cfx3 hmon` (the hypv
monitor).  Source: `spec/Machine-v5 §1.1/§2/§3/§4.4/§5`, `spec/DADAO-12 §5`,
`spec/DADAO-13 §1`.

## Files

| File | Purpose |
|------|---------|
| `tiny_hmon.S` | SRAM-only application (fixed entry `0xffff_ff01_0100`): before each fault it writes its landing address to hmon slot `0xF8`; at the landing it records the four hmon data slots |
| `tiny_hmon.lds` | Application layout: `.text` at `ENTRY`, `.rcheck` `ENTRY+0x2000`, `.data` `ENTRY+0x3100`, `.results` `ENTRY+0x4000` |
| `tiny_hmon_layout.inc` | Application data-area offsets (slot pointer, fail counter, semihosting block) |
| `tiny_hmon_min.S` | QEMU probe application (`tools/testcases/arch/min_rom_probe_integ007t.py`): same minimal-handler contract, 6 observation records |
| `expected.yaml` | Independent oracle (spec-derived cause ids, ELF-symbol IPs and return slots, profile-derived cg7 values) |

The BootROM firmware (power stub + hmon handler) is **not** in this directory:
it is the *shared* `tests/shared/bootrom/tiny/{power,hmon}.S` built by
`build_tiny_bootrom.py` — the same 64 KiB image QEMU and chipyard boot.  The
old gem5-only dispatch handler (`tiny_hmon_handler.{S,lds}`, 18 instructions /
248 B, frame recording + IALIGN rewrite + `+4`) was removed by
`m13-gem5-010`.

## What the case proves

1. `power → hmon` handover: power writes the default return address to slot
   `0xF8` (= its trap + 4), traps into hmon; the shared minimal handler saves
   `CFXTRAP` to `0xE0/0xE8/0xF0` and escapes through `0xF8`.  Record 0 is those
   four slots read by the application.
2. `cfx2rd`/`cfx2rc` register file: hmon/power ids, vector, `switch_run_mode`,
   `excp_prev_run_mode`, counters, scratch, `cfx_intr_mask`, both cg7 space
   descriptors (records 1–16, plus 41 for the cg3 `rc10` low-bit masking).
3. Five synchronous fault classes × 3 cases each (records 17–31): `CFXMEM`,
   `ILLI`, `UNDI`, `MALIGN`, `IALIGN`.  The handler only saves the cause
   registers; the application-supplied return slot picks the landing, so a
   `+4` policy would land inside the record sequence and be visible.  For
   IALIGN the recorded IP is the illegal address itself (no next-IP
   write-back) and `info == ip`.
4. `CFXTRAP` (general trap), `CFXESC` (escape target error), `CFXPERM`
   (cfxtrap mask denial) and `CFXREG` (unimplemented cfx5 register) also enter
   hmon (records 32–35).
5. Semihosting is cfxha-agnostic: the case calls `SYS_WRITE0` through
   `trap cfx_power, 0x3FF00` and the rest through `trap cfx_hmon, 0x3FF00`.
6. The run mode stays `hypv` on Tiny (`Machine-v5 §2`): the body writes
   `switch_run_mode = user(0)`, takes a `CFXMEM`, and after the fault reads a
   cg3 (hypv-only, `DADAO-13 §1`) register successfully while
   `excp_prev_run_mode` records `3` (records 36, 42, 38–40).  The old
   in-handler cg3 probe (check 37) belonged to the dispatch fixture and is
   gone with it.

## m13-gem5-010 note

The dispatch fixture is retired: the case boots the shared firmware and
derives every cause record from the hmon SRAM data slots — code at `0x00`
(11 instructions, 44 B; table entry 48 B after 8-byte alignment), data at
`0xD8` saved rd63 / `0xE0` cause_id / `0xE8` cause_ip / `0xF0` cause_info /
`0xF8` framework return address.  The data area lies outside the image
segment (power copies only the table `size` bytes).  The QEMU oracle for the
same contract is `tools/testcases/arch/min_rom_probe_integ007t.py` on
`tiny_hmon_min.S`.

## Run

```sh
# prerequisites: make build-gem5
python3 tools/gem5/check_tiny_hmon.py
```

The runner assembles/links the shared firmware and the case, runs gem5 Tiny
FS, and compares the guest-exported result table against `expected.yaml`; any
mismatch, a wrong guest exit code, a missing `hmon-ok` console line, or an
hmon SRAM layout/SRAM-slot deviation is a failure.  The guest writes the table
through semihosting `SYS_OPEN` + `SYS_WRITE` and stops with `SYS_EXIT`
(`0x21` pass, `0x71` fail).
