# arch/hmon — Machine-v5-Tiny `cfx_power` + `cfx3 hmon`

`TESTCASES`-style execution case for the Tiny machine's cfx set
(`m13-gem5-001`): `cfx_power` (cfx63, boot handover) and `cfx3 hmon` (the hypv
monitor).  Source: `spec/Machine-v5 §1.1/§2/§3/§4.4/§5`, `spec/DADAO-12 §5`,
`spec/DADAO-13 §1`.

## Files

| File | Purpose |
|------|---------|
| `tiny_hmon.S` | Three-segment ELF: power stub in BootROM, hmon handler in hmon SRAM, body in SRAM |
| `tiny_hmon.lds` | Fixed layout: BootROM `0xffff_ffff_0000`, hmon `0x0fff_0000_0000`, SRAM `0xffff_ff01_0100` |
| `expected.yaml` | Independent oracle (spec-derived cause ids, ELF-symbol IPs, profile-derived cg7 values) |

## What the case proves

1. `power → hmon` handover: the BootROM writes `cfx_hmon_hypv_excp_vector`,
   then `trap cfx_hmon, 0` enters the hmon vector (record 0: `CFXTRAP`,
   handler PC = hmon base).
2. `cfx2rd`/`cfx2rc` register file: hmon/power ids, vector, `switch_run_mode`,
   `excp_prev_run_mode`, counters, scratch, `cfx_intr_mask`, and both cg7
   space descriptors (records 1–16).
3. Five synchronous fault classes × 3 cases each enter hmon with the spec
   `excp_cause_id`/`excp_cause_ip`/`excp_cause_info` (records 17–31):
   `CFXMEM`, `ILLI`, `UNDI`, `MALIGN`, `IALIGN`.  The IALIGN cases assert that
   the recorded IP is the illegal address itself (no next-IP write-back).
4. `CFXTRAP` (general trap), `CFXESC` (escape target error), `CFXPERM`
   (cfxtrap mask denial) and `CFXREG` (unimplemented cfx5 register) also enter
   hmon (records 32–35).
5. Semihosting is cfxha-agnostic: the case calls `SYS_WRITE0` through
   `trap cfx_power, 0x3FF00` and the rest through `trap cfx_hmon, 0x3FF00`.
6. The run mode stays `hypv` on Tiny (`Machine-v5 §2`): the body writes
   `switch_run_mode = user(0)`, takes a `CFXMEM`, the handler reads a cg3
   (hypv-only, `DADAO-13 §1`) register successfully, and
   `excp_prev_run_mode` records `3` (records 36–40).

## Run

```sh
# prerequisites: make build-gem5
python3 tools/gem5/check_tiny_hmon.py
```

The runner assembles/links the case, runs gem5 Tiny FS, and compares the
guest-exported result table against `expected.yaml`; any mismatch, a wrong
guest exit code or a missing `hmon-ok` console line is a failure.  The guest
writes the table through semihosting `SYS_OPEN` + `SYS_WRITE` and stops with
`SYS_EXIT` (`0x21` pass, `0x71` fail).
