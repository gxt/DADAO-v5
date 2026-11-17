# k0 BootROM firmware — Kaiwu-Vast K1 boot chain (m14-qemu-001)

The 4 MiB Vast BootROM for the **kernel boot path**: the reused step5 `power`
stage hands over to this directory's `hmon`, which loads and enters `smon`, and
`smon` builds the first page table, turns the PTW on and hands the kernel over
in `supv` at the kernel's **VA** entry.

Normative sources (nothing here restates them):

- `spec/Kaiwu §6.3.1`–`§6.3.4` — the kernel VA window, the two load paths,
  the fixed boot info, the entry state and the failure semantics;
- `.tao/contracts/contract-linux-boot.md` + `contracts/linux-boot.yaml` — the
  same facts as a review contract and a machine-readable projection (the probe
  derives every expectation from the YAML at run time);
- `spec/DADAO-12 §2.2.1`/`§2.2.3` — the L1 index (`VA[41:29]`) and PTE bits;
- `spec/DADAO-23 §3` — the `trap cfx_smon` → `escape cfx_smon` handover;
- `ADR-0051` (`D2`/`D4`/`D5`/`D6`) — the decisions behind them.

## Files

- `power.S`/`power.lds` — **not here**: the step5 power stage is reused
  verbatim (`tests/shared/bootrom/step5/`); it also carries the two shared ROM
  routines (`rom_validate_table` at ROM+`0x2000`, `elf_loader` at ROM+`0x2400`).
- `hmon.S` / `hmon.lds` — K1 boot hmon at `0x0fff_0000_0000` (cfx3/hypv):
  trap-cause/magic check → image index table lookup of type 2 (smon) →
  `elf_loader` into smon SRAM → `cfx_smon.hypv_excp_vector = e_entry`,
  `hypv_switch_run_mode = supv` → open the supv permissions →
  `trap cfx_smon, 0x30001`. It **never** builds a page table, never writes PA
  `0` and never touches the boot info page. **Every cfx this machine implements
  except `cfx_hmon` is handed to smon** (user ruling 2026-11-17): for each
  target the four supv synchronous source masks (`cg2` rc0–rc3: cfxtrap/
  cfxmem/cfxreg/cfxexe) get source bits {2, 15} cleared (`cfx_smon` and, after
  the kernel's first `cfx_hart` interrupt delivery, `cfx_hart` —
  `spec/DADAO-12 §5.3`) and `hypv_cg_reg_deleg` = `0x8`. `cfx_hmon` stays at
  its reset masks, so supv access to the hypervisor monitor is still
  `CFXPERM`. `cfx5`/`cfx33`/`cfx62` are allocated but not implemented by
  `Kaiwu-Vast` (`spec/Kaiwu §「测试机 cfx 实现范围（按 profile）」`), so they
  have no rows to open. `cfx_pmem`/`cfx_ptw`/`cfx_smon` always stay open (the
  boot chain needs them before the kernel exists); `--defsym
  OPEN_SUPV_ALL=0` builds the permission-negative variant with the remaining
  targets left closed, and `--defsym K2_TIME_PERM=0` closes `cfx_hart`/
  `cfx_time` only (the K2 gate's negative case).
- `smon.S` / `smon.lds` — K1 smon at `0x0bff_0000_0000` (cfx2/supv):
  boot info read-only validation → 64 KiB page table with **one** 512 MiB
  superpage PTE → DMA to PA `0` → TLB invalidate, `PTBR = 0`,
  `ptw_enable = 1` (with read-back) → `rb16`/`rb17`/`rb3` → `escape` into the
  kernel's VA entry. The page table page has exactly one writer: smon.
- `probe_kernel.S` / `probe_kernel.lds` — the minimal kernel-shaped probe
  (not Linux): reads the boot info and the page table through the prebuilt
  mapping, self-checks the handover and records everything in `rd5`–`rd30`.
- `tools/qemu/k0_boot_probe.py` — builds these images, runs them on
  `qemu-system-dadao -machine kaiwu-vast,bootrom-image=...,-kernel ...` and
  checks the ABI plus the rejection paths.

## Boot chain

```text
reset (RESET_PC, cfx_power/hypv)
  └─ power (step5, unchanged): validate table, load hmon, trap cfx_hmon
       └─ hmon (this dir): load smon, open supv perms, trap cfx_smon
            └─ smon (this dir): validate boot info, build page table, PTW on,
                 escape cfx_smon -> kernel VA entry (supv, cfxcode smon)
                 └─ kernel (host `-kernel` payload at VA 0x0200_0010_0000)
```

The host loader (`hw/dadao/dadao-machine.c`, K1 path) loads the kernel at
`p_vaddr - 2 TiB` and writes the boot info; `power`/`hmon`/`smon` only read it.

## Failure codes (guest side, semihosting `SYS_EXIT`)

`hmon` (unchanged step5 values; `spec/Kaiwu §6.3.2` + task §7):

- `0xB1`/`0xB2`/`0xB6` — image index table (header, entry, type missing)
- `0xB3`/`0xB4`/`0xB5` — smon ELF (size, header/structure, segment)
- `0xB8` — trap cause or boot magic mismatch

`smon` (task §7; identical in `smon.S`, this file and the probe script):

- `0xC1` boot info `magic` or `version` mismatch
- `0xC2` boot info `size < 0x60`
- `0xC3` `kernel_base` not `0x0200_0010_0000` or not 64 KiB aligned
- `0xC4` initramfs fields out of range (K1 requires `size == 0`, base fixed)
- `0xC5` page-table DMA failed or the PTE read-back differs
- `0xC6` `PTBR` / `ptw_enable` read-back differs
- `0xC7` RAM geometry / page size / hart id mismatch

No failure escapes into the kernel: the probe asserts that the kernel window
never executes for every negative case.

## Probe kernel register map (`-d cpu`, last dump block)

- `rd5`–`rd15` — boot info fields `0x00`…`0x40` in §6.3.3 order
  (`magic`, `version`, `size`, `ram_base`, `ram_size`, `kernel_base`,
  `kernel_size`, `initramfs_base`, `initramfs_size`, `cmdline_base`,
  `cmdline_size`)
- `rd17`–`rd20` — `ptbr`, `page_size_log2`, `hart_id`, `flags`
- `rd21`–`rd24` — `PTE[4096..4099]` read through the kernel window
  (index `PTE_INDEX = VA[41:29]` of `0x0200_0000_0000` = 4096)
- `rd25`–`rd27` — `rb16` (entry VA), `rb17` (boot info VA), `rb3` as saved at
  entry
- `rd28` — non-zero 8-byte words in the 64 KiB page table page (expect **1**:
  one superpage PTE; everything else zero)
- `rd29` — non-zero 8-byte words in the boot info page after `0x60` (expect 0)
- `rd30` — self-check failure mask (bit `n-1` = check `n`; 0 = all passed)

Self-check list (exit code `0xD0 | n` for the first failure; for `n >= 16` the
low nibble aliases — `rd30` identifies the exact check):

1–15 the 15 boot info fields, 16–19 the four PTE words, 20 the page-table
non-zero count, 21 the boot info page tail count, 22–24 `rb16`/`rb17`/`rb3`.

## Test-only negative variants (`--defsym SMON_NEG_CASE=<n>`)

`hmon` can DMA-patch one boot info field right before the smon trap so the
probe can prove smon's read-only validation rejects a bad boot info. The
production image is assembled with `SMON_NEG_CASE=0` (the block is empty):

- `1` — `size = 0x20` (2 bytes at `0x06`) → smon `0xC2`
- `2` — `kernel_base = base | 1` (8 bytes at `0x18`) → smon `0xC3`
- `3` — `hart_id = 5` (4 bytes at `0x54`) → smon `0xC7`; the valid value is 0,
  so this case also proves the injected bytes really reach the boot info page
  (a zero-filling or mis-addressed DMA would leave smon green)

The staging word lives in the **cfx_pmem SRAM**: the DMA's 42-bit cfx view only
reaches that window, so staging in hmon SRAM would copy unrelated bytes.

## Not done here (later K1 tasks)

No console, timer, interrupt controller, SMP, initramfs loading (host side,
`m14-infra-002`) or TLB/cache policy; the probe kernel builds no stack and no
`.bss`. `smon` also does not open the `supv_*_cfx_mask` rows of the SBI surface
(`DADAO-23 §3`) because the K0 kernel does not issue SBI calls yet.
