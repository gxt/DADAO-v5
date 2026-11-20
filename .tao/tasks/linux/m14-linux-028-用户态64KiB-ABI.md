# m14-linux-028: 用户态 64 KiB ABI（AT_PAGESZ / mmap 对齐 / ELF 段对齐 / brk+mmap syscall 面）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-023`（syscall 闭环）
**可并行分片**：否（`components/linux` 单写者；共享 `mm/mmap.c`/`include/asm/elf.h`/`kernel/syscalls.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：2–3 h（对齐/auxv 口径为主，代码量小）
**档位**：中改（用户可见 ABI 对齐 + syscall 面；复核 ≥3 路注入）
**状态**：待开始

## 背景

`m14-linux-011` 已登记「用户态 API 影响（`AT_PAGESZ=65536`、`mmap` 64 KiB 对齐、ELF 段对齐）**K5 处理**」。本任务补齐这些用户态 64 KiB 页 ABI 口径 + `brk`/`mmap` syscall 面，使 musl 静态 `init` 的堆/映射/段装载在 64 KiB 页下正确。

DADAO 特有事实（**不得偏离**）：
- **页 64 KiB**（`PAGE_SIZE = 65536`、`PAGE_SHIFT = 16`，`spec/DADAO-12 §2.2.2`）；`AT_PAGESZ` 必须 = 65536。
- `mmap` 返回地址**须 64 KiB 对齐**（`MAP_FIXED` 除外的内核默认对齐 = 页大小）。
- ELF `LOAD` 段按页对齐（`ELF_EXEC_PAGESIZE = PAGE_SIZE` 已在 `asm/elf.h`，K0 即有）；`AT_PHDR`/`AT_ENTRY` 等 auxv 条目随之。
- `brk`/`mmap`/`munmap`/`mprotect` 是用户堆/映射的 syscall 面；`mmap` 走 asm-generic 的 byte-offset 形式（`016` 的 `syscalls.c` 已 shift，`mmap2` 无 legacy 分裂）。

## `ARCH_FORCE_MAX_ORDER` = 13（用户 2026-11-20 裁定，并入本任务）

**理由（用户原话）**：「改成 13，这样最大可分配的页恰好是一个超页，512 MiB」——`2^13 × 64 KiB = 512 MiB`，与超页（`SPF=0xFF`）**同尺寸**，buddy 的最大阶与超页对齐。

- 现状：我们取 **10**（`2^10 × 64 KiB = 64 MiB`），arm64 取 **13**（`036` 盘点发现）；
- 要做：把 `ARCH_FORCE_MAX_ORDER` 改 **13**，并核连带影响：
  1. **Tiny（8 MiB SRAM）**：buddy 会按 `MAX_ORDER` 初始化 14 个阶，实际最大块受 zone 大小限制 ⇒ **必须实测不回归**（K0–K4 全绿）；
  2. `pageblock_order`/compaction/CMA 的连带（`pageblock_order = min(MAX_ORDER-1, …)`）；
  3. `min_order`/`free_area_init` 的内存开销（14 个 list head，可忽略但要给数）；
- 验收：Tiny/Vast 都不回归；`/proc/buddyinfo` 显示最大阶 **13**；**Vast 上 512 MiB 超页粒度分配成功**（给实测）；`check-config-pins` 不因新增符号而红。

## 目标

1. **`AT_PAGESZ = 65536`**：auxv 的 `AT_PAGESZ` 条目 = `PAGE_SIZE`（现场派生，不写死 65536）；`AT_MINSIGSTKSZ` 等页相关条目同步核对。
2. **`mmap` 64 KiB 对齐**：`mmap`（非 `MAP_FIXED`）返回地址 `% 65536 == 0`；`mmap` 的 len 向上取整到页。
3. **ELF 段对齐**：`LOAD` 段按 64 KiB 对齐装载；`AT_ENTRY`/`AT_PHDR` 正确（`ELF_EXEC_PAGESIZE` 已定）。
4. **`brk`/`mmap` syscall 面**：用户态 `brk`（堆增长）、`mmap`/`munmap`/`mprotect` 可用；`brk` 按页对齐。
5. **探针** `tools/linux/k5_pagesz_probe.py` + `CONFIG_DADAO_K5_PAGESZ_SELFTEST`。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. `python3 tools/linux/k5_pagesz_probe.py` rc=0，逐 case 打印；期望值现场派生（页大小 ← 镜像 `.config` + `spec/DADAO-12 §2.2.2`、`AT_PAGESZ` ← auxv 现场读）。
2. **探针 case（各一条可达 FAIL 断言）**：
   - `A1 AT_PAGESZ`：auxv 里 `AT_PAGESZ == 65536`（现场读，非写死）；`AT_ENTRY` 非 0、`AT_PHDR` 有效。
   - `A2 mmap 对齐`：`mmap(NULL, len, PROT_READ|WRITE, MAP_PRIVATE|ANONYMOUS, ...)` 返回地址 `% 65536 == 0`；`munmap` 后释放。
   - `A3 ELF 段对齐`：装载的 `LOAD` 段起始 `% 65536 == 0`、`p_align` ≥ 65536 的段正确处理。
   - `A4 brk`：`brk(0)` 读当前堆尾（64 KiB 对齐）、`brk(+n)` 增长（按页取整）、越界访问堆外 ⇒ 触发缺页（`019`/`012` 通道）。
3. **≥3 路注入**（`cp`+md5 还原 + 重建回绿）：① `AT_PAGESZ` 写 4096 ⇒ `A1` 红；② `mmap` 不按页对齐返回 ⇒ `A2` 红；③ `brk` 不按页取整 ⇒ `A4` 红。
4. **不回归**：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_syscall_probe.py`（023）rc=0；`make check-patch-tree` rc=0。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树；临时文件放 `/tmp/opencode/m14-linux-028/`。
2. **预计改动文件**：`components/linux/patches/arch/dadao/include/asm/{elf.h,processor.h}.patch`、`components/linux/patches/arch/dadao/kernel/{syscalls.c,process.c}.patch`（`brk`/`mmap` 面）、`components/linux/patches/arch/dadao/kernel/{Kconfig.debug,k5_pagesz_selftest.c}.patch`（新）、`components/linux/changelog.md`、`tools/linux/k5_pagesz_probe.py`（新）。**不改** `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`。
3. 不提交 git；注入还原 `cp`+md5；注入后重建；禁 `checkout/restore/stash/reset --hard`。
4. 语义以 `spec/DADAO-12 §2.2.2`（页 64 KiB）+ `contract-elf`（`EM_DADAO`/端序）+ `contract-abi` 为准；页大小/对齐**现场派生**，不写死 65536；**不得**套 4 KiB 页经验。
5. `AT_PAGESZ` 等 auxv 值由内核现场生成，不硬编码；`mmap` 走 asm-generic 号表（`contract-syscall §1.2` 锁定源）。

## 待裁定（本任务不得自决；主会话转达用户后回填）

1. 无新裁定项；`AT_PAGESZ`/`mmap` 对齐/`ELF_EXEC_PAGESIZE` 口径已由页大小（64 KiB）唯一确定，本任务只做落地与断言。

## 审阅记录

（待填）
