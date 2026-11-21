# m14-linux-028: 用户态 64 KiB ABI（AT_PAGESZ / mmap 对齐 / ELF 段对齐 / brk+mmap syscall 面）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-023`（syscall 闭环）
**可并行分片**：否（`components/linux` 单写者；共享 `mm/mmap.c`/`include/asm/elf.h`/`kernel/syscalls.c`）
**并行组**：与 K5 其余任务**串行**（同组件同写者）
**预估**：2–3 h（对齐/auxv 口径为主，代码量小）
**档位**：中改（用户可见 ABI 对齐 + syscall 面；复核 ≥3 路注入）
**状态**：已验证

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

## 完成区

**测试结果**：`k5_pagesz_probe.py` **66/66**（51 条基线 + 3 路注入各 5 项）；`k5_syscall_probe.py --no-inject` 62/62；`make check-linux-k0/-k1/-k2/-k3` 全 rc=0；`check-config-pins` PASS（22 脚本 / 24 符号 / 52 镜像）；`check-contracts-dir`、`check-knowledge-refs`、`apply_series`（幂等）rc=0；`check-patch-tree` **linux 段 0 问题**。
**修改文件**：`components/linux/patches/arch/dadao/` 下 `Kconfig`、`Kconfig.debug`、`configs/defconfig`、`include/asm/{processor,setup,vmalloc}.h`、`kernel/{Makefile,process,setup}.c`、`mm/init.c`、新增 `kernel/k5_pagesz_selftest.c.patch`；`components/linux/{series,changelog.md}`；新增 `tools/linux/k5_pagesz_probe.py`；21 份 `tools/linux/*.py` 的 `CONFIG_PINS` 补钉；`tools/linux/config_pins.py`（切片统一带 `PAGE_BLOCK_MAX_ORDER=10`）。
**未改**：`include/asm/elf.h`——`ELF_EXEC_PAGESIZE`/`ELF_MIN_ALIGN` 已由 `PAGE_SIZE` 唯一决定、`AT_PAGESZ` 实测即 `PAGE_SIZE`，无需改（由探针断言）；`spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile` 未动。
**验收结果**：`run.sh` → `RESULT: PASS`（21 项检查：派生值 + 自检 + 探针 66 条 + 3 路注入 + K0–K3 + K5 syscall + 配置/契约门控 + 补丁树 + 系列解析；日志在运行期证据目录的 `log/`）。注入实红：`auxv-pagesz-4k` ⇒ `a1_pagesz`（退码 `0x71`）、`mmap-unaligned` ⇒ `a2_*`（`0x72`）、`brk-not-page-rounded` ⇒ `a4_heap_vma`（`0x74`），每路 `cp`+md5 还原后重建回绿（宿主 rc=0）。A5 实测 `order=13 pages=8192 bytes=0x20000000 pa=0x40000000`；`buddyinfo` 14 列（末列 = 释放后整块空闲数）；trap 序列由 vmlinux 反汇编派生（10 条，末条 `0x2c01`）并与内核对账。
**新发现/坑**：
- `TASK_UNMAPPED_BASE`/`mmap_min_addr` 未按页对齐 ⇒ **每次**非 `MAP_FIXED` 的 `mmap` 静默 `-EINVAL`（其余 ABI 面"看起来都对"，只有逐项断言能逼出来）。
- `VMALLOC_START`（原 2 TiB+96 MiB）与直映射重叠 ⇒ `is_vmalloc_addr()` 把 PA>96 MiB 的 kmalloc 地址当 vmalloc；`kvfree()` 在软中断里把对象挂上延迟释放链并写入 `next` ⇒ `delayed_vfree_work` 永久告警/挂死。判据：控制台不得出现 `Trying to vfree() nonexistent vm area`。
- `pageblock_order` 不得等于 `MAX_PAGE_ORDER`：13/13 时 2 GiB 只有 4 个页块，migratetype 回退/直接压缩按 512 MiB 整块走，023 镜像在首个用户 trap 处不再前进（13/10 正常）⇒ `config_pins` 统一带 `PAGE_BLOCK_MAX_ORDER=10`。
- Vast 2 GiB 上启动期 slab 回退在 512 MiB/1 GiB/1.5 GiB 各取一页，任何 512 MiB 对齐区间都不是整块 ⇒ A5 用探针专用预留+释放实测（`buddyinfo` 列数是不依赖预留的证据）。
- `zone->managed_pages` 是 `atomic_long_t`；seq 读 `/proc/buddyinfo` 自身会再分配一页 ⇒「最大阶有空闲块」用 `free_area[MAX_PAGE_ORDER].nr_free` 判，`buddyinfo` 只判列数。
**遗留问题**：① 全仓 `check-patch-tree` 仍有 18 条 **musl** 问题：`.work/source/musl` 停在 2026-11-19 的补丁集，HEAD 已于 2026-11-21 合入 `m14-infra-005`；属环境遗留、需主会话决定是否 `apply_series --component musl`（越界未做）。② A5 的 512 MiB 实测依赖探针镜像的预留；里程碑镜像不预留、也不承诺启动后仍有整块。③ 本内核版本的通用 `binfmt_elf.c` 没有 `AT_MINSIGSTKSZ` 条目，探针已核对 auxv 全集。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：可交付（`待验收`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 探针函数栈帧 66 KiB（`char text[PAGE_SIZE]` 被内联）⇒ 16 KiB 内核栈被击穿 | ✅已修 | 文本缓冲改 `static` | 内核告警 `-Wframe-larger-than` 消失；探针跑通 |
| F2 A2 的 `munmap` 断言与第二次 `mmap` 复用同一地址 ⇒ 假红 | ✅已修 | 程序改为「先 B（保留）后 A（释放）」+ `a2_mmap_distinct` | A2 10 条全绿 |
| F3 在 trap 钩子里 `find_vma`（无 mmap 锁）⇒ `rwsem.h:81` 告警 | ✅已修 | 钩子只记录帧，判定移到子任务退出后、`mmap_read_lock` 下 | 告警消失 |
| F4 预留块落在 RAM 顶部，含启动期 memblock 保留（2 GiB−5 MiB）⇒ 释放活内存 | ✅已修 | 预留搜索从「RAM 顶部去掉 1/8」起 | 预留 `0x40000000+0x20000000`，无 vfree 告警 |
| F5 `mmap` 恒 `-EINVAL` | ✅已修 | `TASK_UNMAPPED_BASE` 取 `PAGE_ALIGN`；`paging_init()` 把 `mmap_min_addr`/`dac_mmap_min_addr` 对齐到页 | A2 全绿；新增强制 `a2_mmap_min_addr_aligned` |
| F6 `delayed_vfree_work` 死循环（`is_vmalloc_addr` 与直映射重叠） | ✅已修 | `VMALLOC_START` 移到直映射之上（2 TiB+2 GiB，仍在契约窗口内） | 跑批零 vfree 告警；判据写进 `judge` |
| F7 13/13 时 023 镜像首个用户 trap 后停住 | ✅已修 | `config_pins` 统一带 `PAGE_BLOCK_MAX_ORDER=10`（+defconfig） | `k5_syscall_probe` 62/62；K0–K3 rc=0 |
| F8 注入①是否会顺带改 ELF 装载 | ✅核实 | `ELF_EXEC_PAGESIZE=4096` 时 `ELF_MIN_ALIGN` 仍为 `PAGE_SIZE` | 只有 `a1_pagesz` 红，A3 全绿 |
| F9 探针未覆盖 `munmap` 真释放/`mprotect` 真生效 | ✅已修 | A2 加 `a2_munmap_released`、`a2_mprotect_ro`/`_rc`、`a2_mmap_b_len` | 10 条断言全绿且注入②能把它们打红 |

**越界披露**：任务书「预计改动文件」之外还改了 `include/asm/{setup,vmalloc}.h`、`mm/init.c`、`kernel/Makefile.patch`、`kernel/setup.c.patch`（预留/边界）、`tools/linux/config_pins.py` 与 21 份探针脚本的 `CONFIG_PINS`——均由 F4/F5/F6/F7 的必要修复或新 Kconfig 符号的补钉引起。

### 第 1 轮 reviewer 验收（2026-11-21）

**重跑记录（命令自身退出码，全部本机现场执行）**
1. `python3 tools/linux/k5_pagesz_probe.py`（完整，含探针自带 3 路注入）⇒ `k5_pagesz_probe: 66/66 passed`，rc=0（66 PASS / 0 FAIL）；console：`K5P auxv: pagesz=0x10000 (x1)`、`K5P alloc: order=13 pages=8192 bytes=536870912 pa=0x40000000`、`K5P buddyinfo:` 行 14 个数（0–13 阶）；`trap 条数 want=10 got=10`、末条 `0x2c01`；自带三路注入实红：`auxv-pagesz-4k rc=113 red=['a1_pagesz']`、`mmap-unaligned rc=114 red=['a2_*']`、`brk-not-page-rounded rc=116 red=['a4_heap_vma']`，各路还原 md5 相等后回绿。
2. **独立注入 ≥2 路**（`cp`+md5 还原 + 重建回绿，不用探针 `--inject`）：
   - ① 内核通用 `fs/binfmt_elf.c` 的 `NEW_AUX_ENT(AT_PAGESZ, ELF_EXEC_PAGESIZE)` 改 `4096UL` ⇒ 探针 rc=1、`A1: AT_PAGESZ want=0x10000 got=0x1000`、宿主退出码 113；还原 md5 `158c05ec…` 前后相等，重建后 `48/48 passed` rc=0。
   - ② `mm/mmap.c::sys_brk` 的 `do_brk_flags(…, newbrk - oldbrk, …)` 改为少映射一页 ⇒ rc=1、仅 `a4_heap_vma` 红、退出码 116；还原 md5 `0d7c68e1…` 相等，重建后 `48/48` rc=0。
   - ③ `include/asm/processor.h` 把 `TASK_UNMAPPED_BASE` 回退成 `TASK_SIZE / 3` ⇒ **探针仍 `48/48` 绿 rc=0**（已核注入期真重编译：470/553 个 `.o` 更新）⇒ 见 R1。
3. 门控逐条重跑：`make check-linux-k0/-k1/-k2/-k3` rc=0；`k5_syscall_probe.py --no-inject` `62/62 passed` rc=0；`make check-config-pins` PASS 且现场统计 **切片脚本 22 / Kconfig 符号 24 / 镜像 52**（与完成区一致）；`check-contracts-dir`、`check-knowledge-refs` rc=0；`apply_series --component linux` 连跑两次均 rc=0（幂等）；`check-patch-tree` **linux 段 0 条**（`linux: 105 patch(es)`）。
4. 证据脚本：运行期证据目录内的 `run.sh` 全量重跑 ⇒ `checks: 21, failed: 0`、`RESULT: PASS`、rc=0；其 `selfcheck` rc=0（判据可红）。

**findings**
- **R1（覆盖缺口，不阻断）**：`TASK_UNMAPPED_BASE` 页对齐这半个修复**无任何断言覆盖**（注入③证明）。该值只经 `fs/exec.c::arch_pick_mmap_layout()` 进 `mm->mmap_base`，A2 用的是手工 `mm_alloc()` 的 mm（不走 exec、`mmap_base` 未置），故 A2 只覆盖 `mmap_min_addr` 那半；F5 行「复验证据 A2 全绿」对这半不成立。修法本身是根因（`mm/mmap.c` 以 `mm->mmap_base` 为 `low_limit`、`offset_in_page` 非页地址返 `-EINVAL`）。建议补一条「exec 后 `mm->mmap_base` 页对齐」断言。
- **R2（文档级）**：`make check-patch-tree` 整体 rc=1，19 条全在其他组件（chipyard 6、musl 8、gem5 2、picolibc 3），linux 段 0 条；本任务 diff 未触及这些组件（前后 `git status` 对账一致），属基线/环境既有。完成区遗留①「18 条 musl」计数与归属不准（实为 musl 8 + 其它 11）⇒ 请 architect 收尾改。
- **R3（脚本判据，不阻断）**：`run.sh` 补丁树判据只 grep `linux: assertion`、不读整体 rc——linux 段问题可达 FAIL（grep 会命中），但非 linux 问题不进判定；建议补一行现场打印问题总数。

**约束核验**：未改 `spec/**`、`.tao/contracts/**`、`tests/**`、`components/qemu/**`、`Makefile`（`git status` 前后逐行对账一致）；越界披露的 6 类改动逐条核为新 Kconfig 符号补钉与 F4–F7 必要修复，未放宽任何判据（`config_pins` 只增补钉与 `PAGE_BLOCK_MAX_ORDER` 常量）。四处修法判定：`TASK_UNMAPPED_BASE`/`mmap_min_addr` 页对齐 = 根因（覆盖见 R1）；`VMALLOC_START = 0x20080000000`（2 TiB+2 GiB）在 `contract-linux-boot` 内核窗口 `[2 TiB, 3 TiB)` 内、≥ Vast 2 GiB 直映射上界、与固定分区（≤+96 MiB）不重叠 = 根因；`PAGE_BLOCK_MAX_ORDER=10` 用的是内核自带 `mm/Kconfig` 上限符号（`range 1 ARCH_FORCE_MAX_ORDER`，10 合法），pageblock 只定 migratetype 位图粒度、与 512 MiB 超页叶映射无语义耦合，K0–K3 全绿 = 合理；A5 探针专用预留+释放是可达实测（`buddyinfo` 14 列不依赖预留），已入遗留②，非绕行。期望值全部现场派生（spec §2.2.2 + 镜像 `.config` + auxv 现场读），无写死 65536 的判据。

**判决**：**Accepted**（R1 由 architect 定夺是否补断言；R2/R3 文档级，收尾改）。
