# step5 BootROM firmware (INTEG-046t)

256 KiB BootROM (`0xffff_fffc_0000`–`0xffff_ffff_ffff`) implementing the
ADR-0043 chain **power → hmon → smon**.  The interface truth for the image
index table, ELF checks and failure codes is the task file
`.tao/tasks/integ/INTEG-046t-Step5启动链落地.md` §接口规范 1/2/5.

## Files

- `power.S` — power stage (cfx63/hypv) plus the two shared ROM routines:
  - `rom_validate_table` at ROM base + `0x2000`: validates the header
    (`magic 0x44424F54`, version 1, count 2, reserved 0) and every entry
    (`type ∈ {1,2}`, flags bits `[31:3] = 0`); looks up one entry by type.
    Returns `rd8` (0 / `0xB1` / `0xB2` / `0xB6`), `rd2` offset, `rd3` size,
    `rd4` flags.
  - `elf_loader` at ROM base + `0x2400`: validates/loads an ELF image.
    Inputs `rd2` file offset, `rd3` size, `rb2` target SRAM base, `rd4` flags;
    returns `rd8` (0 / `0xB3` / `0xB4` / `0xB5`) and `rd5 = e_entry`.
- `hmon.S` — hmon stage at `0x0fff_0000_0000` (cfx3/hypv).
- `smon.S` — smon stage at `0x0bff_0000_0000` (cfx2/supv).
- `power.lds` / `hmon.lds` / `smon.lds` — 64 KiB link windows with size
  `ASSERT`s; `power.lds` also pins the two shared routine offsets.
- `../build_step5_bootrom.py` (in `tools/testcases/arch/`) packs the table and
  the three images; it patches the `boot_magic_trap` immediate to the table's
  `boot_magic` (default `0x30001`).

## Image layout (big-endian)

```text
0x00000  16-byte header + 2 × 32-byte entries
         hmon.elf (16-byte aligned)
         smon.elf (16-byte aligned)
0x30000  power flat segment, linked at 0xffff_ffff_0000 (64 KiB window)
0x40000  end (exactly 256 KiB)
```

Flags used: `REQUIRED=1`, `LOAD=2`, `VERIFY=4` (default `0x7`).

## Loading semantics used by the firmware

- power validates the table, loads hmon into hmon SRAM, writes
  `cfx_hmon.hypv.excp_vector = e_entry` and `switch_run_mode = 3`, then
  `trap cfx_hmon, <boot_magic>`.
- hmon checks `CFXTRAP` + the magic, loads smon, writes
  `cfx_smon.hypv.excp_vector = e_entry` and `switch_run_mode = 2`, opens
  `cfx_ptw`/`cfx_pmem`/`cfx_smon` for source smon by writing
  `cg3 rc12 = 0x8` (all cg allowed except the hardware-fixed bit3; whole
  group, not per cg), writes `cfx_power cg2 rc1 = 0xffff_ffff_ffff_fff3`
  (only bit2 = 0) so smon can read the power BootROM, keeps
  `cfx_hmon`/`cfx_power` `hypv_cg_reg_deleg` at the reset `~0` (never writes
  their `cg3 rc12`), clears `cfx_hmon.supv.cfxtrap` bit 2, then **last**
  revokes its own `cfx_pmem` access (cg3 rc0/rc1/rc3/rc2 = all ones) before
  `trap cfx_smon`.
- smon checks the magic, clears cfx_pmem SRAM, writes the L1 PTE
  `0x4000_0000_0000_FFE3` at SRAM offset `0x8000`, DMAs the 64 KiB page table
  to PA 0, sets `PTBR=0` then `PTW_ENABLE=1`, and self-checks
  `VA 0x0200_0000_xxxx ↔ PA` in both directions with DMA.

## Observation registers (`-d cpu`)

`rd5` VA round-trip, `rd6` DMA readback of the same word, `rd7` reverse
direction word, `rd8` PTBR, `rd9` PTW enable, `rd10/11/12` power/hmon/smon
stage markers, `rd13` park-poison OR (must be 0), `rd14` PTE read back from PA
`0x8000`, `rd15` DMA status of the page-table copy (`DONE = 2`),
`rd17/rd18/rd19` the `cg_reg_deleg` readback of `cfx_ptw`/`cfx_pmem`/`cfx_smon`
(all `0x8`), `rd20` the power BootROM header at `0xffff_fffc_0000`
(`0x4442_4f54_0001_0002`), `rd21` `cfx_power` supv cfxmem
(`0xffff_ffff_ffff_fff3`), `rd22` `cfx_power` `cg_reg_deleg` (all ones).

## Build

```sh
make build-bootrom   # install-root toolchain required
```

Outputs under `.dadao/tests/bootrom/step5/`:
`power.{o,elf,bin}`, `hmon.{o,elf}`, `smon.{o,elf}`, `bootrom_step5.bin`
(exactly 262144 bytes).  The builder is invoked twice: once for the real
image, once for `--self-test` (layout/table/trap checks plus an injected
`--max-image-size=4096` rejection).
