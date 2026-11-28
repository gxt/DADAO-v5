# gem5/tiny_hmon — Kaiwu-Tiny `cfx_power` + `cfx3 hmon`


> 2026-11-22（`m16-testcases-006`）：本目录由 `tests/arch/hmon/` 迁入
> `tests/unit/gem5/tiny_hmon/`（arch 只测 Kaiwu-Vast；Tiny 用例归 unit），
> 驱动同步迁到 `tests/unit/gem5/check_tiny_hmon.py`；判据未改。
`TESTCASES`-style execution case for the Tiny machine's cfx set
(`m13-gem5-001`): `cfx_power` (cfx63, boot handover) and `cfx3 hmon` (the hypv
monitor).  Source: `spec/Kaiwu §1.1/§2/§3/§4.4/§5`, `spec/DADAO-12 §5`,
`spec/DADAO-13 §1`.

## Files

| File | Purpose |
|------|---------|
| `tiny_hmon.S` | SRAM-only application (fixed entry `0xffff_ff00_2000`): before each fault it writes its landing address to the return slot (data page +0x18); at the landing it records the four hmon data slots |
| `tiny_hmon.lds` | Application layout: `.text` at `ENTRY`, `.rcheck` `ENTRY+0x2000`, `.data` `ENTRY+0x3100`, `.results` `ENTRY+0x4000` |
| `tiny_hmon_layout.inc` | Application data-area offsets (slot pointer, fail counter, semihosting block) |
| `tiny_hmon_min.S` | QEMU probe application (`tools/testcases/arch/min_rom_probe_integ007t.py`): same minimal-handler contract, 6 observation records |
| `expected.yaml` | Independent oracle (spec-derived cause ids, ELF-symbol IPs and return slots, profile-derived cg7 values) |

The BootROM firmware (power stub + hmon handler) is **not** in this directory:
it is the *shared* `tests/ee-tiny/{power,hmon}.S` built by
`build_tiny_bootrom.py` — the same 8 KiB image QEMU and chipyard boot.  The
old gem5-only dispatch handler (`tiny_hmon_handler.{S,lds}`, 18 instructions /
248 B, frame recording + IALIGN rewrite + `+4`) was removed by
`m13-gem5-010`.

## What the case proves

1. `power → hmon` handover: power writes the default return address to slot
   +0x18 (= its trap + 4), traps into hmon; the shared minimal handler saves
   `CFXTRAP` to +0x00/+0x08/+0x10 of the 0xC00 page and escapes through +0x18.  Record 0 is those
   four slots read by the application.
2. `cfx2rd`/`cfx2rc` register file: hmon/power ids, vector, `switch_run_mode`,
   `excp_prev_run_mode`, counters, scratch, `cfx_intr_mask`, both cg7 space
   descriptors (records 1–16, plus 41 for the cg3 `rc15` low-bit masking).
3. Five synchronous fault classes × 3 cases each (records 17–31): `CFXMEM`,
   `ILLI`, `UNDI`, `MALIGN`, `IALIGN`.  The handler only saves the cause
   registers; the application-supplied return slot picks the landing, so a
   `+4` policy would land inside the record sequence and be visible.  For
   IALIGN the recorded IP is the illegal address itself (no next-IP
   write-back) and `info == ip`.
4. `CFXTRAP` (general trap), `CFXPERM` (cfxtrap mask denial) and `CFXREG`
   (unimplemented cfx5 register) enter the current run-mode monitor hmon.
   `CFXESC` (escape frame error) is the exception (`m18-gem5-003`):
   `DADAO-12 §5.1/§5.2(一)` delivers it to the **current cfx** — cfx63 in
   this body — so the case installs cfx63's hypv vector (`cg3 rc15`) at
   `esc_land`, records cfx63's own `cg5` frame there (cause_id / cause_ip /
   cause_info / prev_cfx_code), and asserts the monitor was **not** written:
   a `monitor_unchanged` record reads the hmon SRAM data slots (they still
   hold the previous monitor entry) and check 43 reads `excp_sync_num`
   (stays `15` = 5 classes × 3 cases).
5. Semihosting is cfxha-agnostic: the case calls `SYS_WRITE0` through
   `trap cfx_power, 0x3FF00` and the rest through `trap cfx_hmon, 0x3FF00`.
6. The run mode stays `hypv` on Tiny (`Kaiwu §2`): the body writes
   `switch_run_mode = user(0)`, takes a `CFXMEM`, and after the fault reads a
   cg3 (hypv-only, `DADAO-13 §1`) register successfully while
   `excp_prev_run_mode` records `3` (records 36, 42, 38–40).  The old
   in-handler cg3 probe (check 37) belonged to the dispatch fixture and is
   gone with it.

## m13-gem5-010 note

The dispatch fixture is retired: the case boots the shared firmware and
derives every cause record from the hmon SRAM data slots — code at `0x00`
(11 instructions, 44 B; table entry 48 B after 8-byte alignment), data at
+0x20 saved rd63 / +0x00 cause_id / +0x08 cause_ip / +0x10 cause_info /
+0x18 framework return address (page at hmon SRAM + 0xC00).  The data page lies outside the image
segment (power copies only the table `size` bytes).  The QEMU oracle for the
same contract is `tools/testcases/arch/min_rom_probe_integ007t.py` on
`tiny_hmon_min.S`.

## Run

```sh
# prerequisites: make build-gem5 + make install-host
make check-tiny-hmon
# equivalent direct invocation:
python3 tests/unit/gem5/check_tiny_hmon.py \
    --work-dir .dadao/tests/tiny-hmon
```

The runner assembles/links the shared firmware and the case, runs gem5 Tiny
FS, and compares the guest-exported result table against `expected.yaml`; any
mismatch, a wrong guest exit code, a missing `hmon-ok` console line, or an
hmon SRAM layout/SRAM-slot deviation is a failure.  The guest writes the table
through semihosting `SYS_OPEN` + `SYS_WRITE` and stops with `SYS_EXIT`
(`0x21` pass, `0x71` fail).
