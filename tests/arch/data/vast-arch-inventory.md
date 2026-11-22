# Vast arch 三平台 cfx 盘点矩阵

> 任务：`m16-testcases-004`（只读盘点；不改组件）。
> 盘点基线：分支 `m16-testcases-004` 的 `0eb640c5`。组件证据按 `docs/Process-01` 口径
> 指向**补丁树**（`components/<c>/patches/**`，行号 = 该补丁文件内行号）；仓库内脚本/用例
> 直接指文件行号。所有引用均现场核对，未凭记忆补写。
>
> 范围：**只 Kaiwu-Vast**、cfx **0/2/3/4/5/15/32/34/63**、不含 Tiny / linux-user。
> 统计口径：9 cfx × 3 平台 = **27 格**；本文按 `### cfx<N> <name> — <平台>` 一格一节，
> 每节固定五面（寄存器面 / 命令与副作用 / 异常与子原因 / 现有测试载体 / 现有门控）。
> 「缺」的判定依据写在格内（全树 grep 0 命中、cfx 不在实现集合、或契约存在但无对应行）。
>
> **迁移后注（`m16-testcases-006`，2026-11-22）**：Tiny 的 `tests/arch/hmon/` 与
> `tools/gem5/check_tiny_hmon.py` 已迁到 `tests/unit/gem5/`；本文是盘点基线快照，
> 下方「现有测试载体/门控」中的旧路径**保持原样**（不改写历史证据）。Vast 侧无变化。

## 结论摘要

- **QEMU**：cfx0/2/3/4/15/32/34/63 有实现；**cfx5 cache 整体缺**（无 cache 模型，
  cfx5 不在实现掩码 ⇒ 访问按未实现 cfx 报 CFXREG）。待 `m16-qemu-001`。
- **gem5**：与 QEMU 同一实现集合（0/1/2/3/4/15/32/34/63）；**cfx5 缺**，
  且无 `--caches`/访存类型标志。待 `m16-gem5-020`。
- **RTL（chipyard）**：实现集合只有 **cfx3 hmon / cfx4 ptw / cfx63 power**
  （`WumingCfxHa` 仅三个常量）。cfx0/2/15/32/34 缺；cfx5 的 cache 阵列已有，
  但 **cfx5 寄存器/命令面缺**（源码明写「later task」）。待 `m16-chipyard-016`。

---

## cfx0 umon（user monitor）

### cfx0 umon — QEMU

- **寄存器面**：有。cfx0 在 Vast 实现掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`），通用寄存器行由 `cfx_reg_ptr` 解析：cg0–cg2 模式行、cg4 id/version/计数、cg5 异常帧、cg6 scratch、cg8 rc1 全局中断掩码（`components/qemu/patches/target/dadao/helper.c.patch:1996`、`components/qemu/patches/target/dadao/helper.c.patch:2018`、`components/qemu/patches/target/dadao/helper.c.patch:2028`、`components/qemu/patches/target/dadao/helper.c.patch:2042`）。
- **命令与副作用**：有。`trap`/`escape`/`cfx2rd`/`cfx2rc` 的通用路径（`components/qemu/patches/target/dadao/helper.c.patch:2814`、`components/qemu/patches/target/dadao/helper.c.patch:2872`、`components/qemu/patches/target/dadao/helper.c.patch:2936`、`components/qemu/patches/target/dadao/helper.c.patch:3035`）；U-mode 同步异常目标 = cfx0（`components/qemu/patches/target/dadao/helper.c.patch:343`，`U->0`）。
- **异常与子原因**：有。大类编码 `components/qemu/patches/target/dadao/cpu.h.patch:299`；两轴权限拒绝 `CFXPERM`（`components/qemu/patches/target/dadao/helper.c.patch:63`）；未实现/保留寄存器 ⇒ `CFXREG`（`components/qemu/patches/target/dadao/helper.c.patch:2955`）。
- **现有测试载体**：QEMU bootrom 探针。`tests/arch.yaml:14` 起 10 条 `arch-umon-*`，载体 `tests/arch/umon/*.s`，由 `tools/testcases/arch/run_m5_e2e.py` 配 step5 BootROM 执行（`Makefile:1717`）。
- **现有门控**：`check-arch-smoke`（L2，`Makefile:1708` 的目标，`Makefile:1717` 调 `tools/testcases/arch/run_m5_e2e.py`）。

### cfx0 umon — gem5

- **寄存器面**：有。cfx0 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`），行结构 `NodeCfxRegs`（`components/gem5/patches/src/arch/dadao/node_cfx.hh.patch:124`），通用解析 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:483`。
- **命令与副作用**：有。`nodeTrap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:929`）、`nodeEscape`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:968`）、`nodeCfxRead/Write`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:1009`/`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:1077`）、异常进入 `nodeCfxEnter`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:308`）。
- **异常与子原因**：有。cause 常量（`components/gem5/patches/src/arch/dadao/node_cfx.hh.patch:55`），结构校验 `checkCauseId`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:319`）。
- **现有测试载体**：无。`tools/gem5/` 只有 Tiny 的 `tools/gem5/check_tiny_hmon.py`，无 Vast 的 umon 用例；`components/gem5/patches/configs/dadao/fs.py.patch` 只提供 `--profile vast` 装载（`components/gem5/patches/configs/dadao/fs.py.patch:118`）。
- **现有门控**：无。

### cfx0 umon — RTL

- **寄存器面**：缺。`WumingCfxHa` 只有 hmon/power/ptw（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:89`），cfx0 无寄存器行；现场 `grep -rl cfx_umon components/chipyard/patches` = 0 命中 ⇒ 未实现 cfxha 在 `GewuFile` 读/写均报 CFXREG。
- **命令与副作用**：缺。`trap`/`escape`/`cfx2rd`/`cfx2rc` 指令译码存在（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:1421`、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:1565`），但目标 cfx0 无寄存器行/无向量，只能落 CFXREG；无 umon 专属副作用。
- **异常与子原因**：缺。同步异常固定进 hmon（`monitor = 0`，`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:154`），没有 U-mode → cfx0 的路由。
- **现有测试载体**：无。
- **现有门控**：无。

---

## cfx2 smon（supervisor monitor）

### cfx2 smon — QEMU

- **寄存器面**：有。cfx2 在 Vast 掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`）；通用行同 cfx0（`components/qemu/patches/target/dadao/helper.c.patch:1996`）；cg7 的 smon 空间块（`components/qemu/patches/target/dadao/helper.c.patch:1971`）；smon SRAM 64 KiB（`components/qemu/patches/hw/dadao/dadao-machine.c.patch:1155`）。
- **命令与副作用**：有。S-mode 中断源轴读 cfx_smon `cg2 rc4`（`components/qemu/patches/target/dadao/helper.c.patch:2139`）；S-mode 同步异常目标 = cfx2（`components/qemu/patches/target/dadao/helper.c.patch:343`，`S->2`）。
- **异常与子原因**：有。与 cfx0 同一通用 cause 表（`components/qemu/patches/target/dadao/cpu.h.patch:299`）与两轴权限（`components/qemu/patches/target/dadao/helper.c.patch:63`）。
- **现有测试载体**：QEMU bootrom 探针。step5 BootROM 编入 smon 固件（`Makefile:828`），`tools/testcases/arch/min_rom_probe_integ046t.py:391` 经 `cfx2rd` 校验 smon 的向量/切换值（明示「smon is reserved, never entered」）。
- **现有门控**：`check-arch`（L3，`integ046t` 在 `ARCH_CFX_PROBES`，`Makefile:1706`、`Makefile:1733`）。

### cfx2 smon — gem5

- **寄存器面**：有。cfx2 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`），通用解析 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:483`，cg7 smon 块 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:457`；smon 64 KiB 区间（`components/gem5/patches/configs/dadao/fs.py.patch:103`）。
- **命令与副作用**：有。异常进入/寄存器读写同 cfx0（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:308`、`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:1009`、`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:1077`）；无 smon 专属命令。
- **异常与子原因**：有。`components/gem5/patches/src/arch/dadao/node_cfx.hh.patch:55` 的 cause 常量；`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:319` 结构校验。
- **现有测试载体**：无（Vast cfx2 无用例；Tiny `check_tiny_hmon` 不覆盖 smon）。
- **现有门控**：无。

### cfx2 smon — RTL

- **寄存器面**：缺。`WumingCfxHa` 无 smon（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:89`）；现场 `grep -rl cfx_smon components/chipyard/patches` = 0 命中。
- **命令与副作用**：缺。无 cfx2 行，寄存器访问报 CFXREG；异常只进 hmon。
- **异常与子原因**：缺。无 S-mode → cfx2 路由（`monitor = 0`，`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:154`）。
- **现有测试载体**：无。
- **现有门控**：无。

---

## cfx3 hmon（hypervisor monitor）

### cfx3 hmon — QEMU

- **寄存器面**：有。cfx3 在 Vast 掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`）；通用行 + cg7 hmon 空间块（`components/qemu/patches/target/dadao/helper.c.patch:1972`）；hmon SRAM 64 KiB（`components/qemu/patches/hw/dadao/dadao-machine.c.patch:1135`）；H-mode 目标 = cfx3（`components/qemu/patches/target/dadao/helper.c.patch:343`）。
- **命令与副作用**：有。`trap` 移交/`escape` 返回与帧块异步（`components/qemu/patches/target/dadao/helper.c.patch:2814`、`components/qemu/patches/target/dadao/helper.c.patch:2872`、`components/qemu/patches/target/dadao/helper.c.patch:2254`）；异常进入 `cfx_enter` 保存 prev-mode/prev-cfx（`components/qemu/patches/target/dadao/helper.c.patch:2123`）。
- **异常与子原因**：有。全部同步大类（`components/qemu/patches/target/dadao/cpu.h.patch:299`）+ `CFXMEM`/`CFXPERM` 子原因（`components/qemu/patches/target/dadao/helper.c.patch:570`、`components/qemu/patches/target/dadao/helper.c.patch:792`）。
- **现有测试载体**：QEMU bootrom 探针。`tools/testcases/arch/min_rom_probe_integ046t.py:7` 覆盖 power→hmon→测试体链与 hmon 帧；`tests/arch/hmon/tiny_hmon_min.S` 走 Tiny 的 `integ007t`（不在 Vast 范围）。
- **现有门控**：`check-arch`（L3，`integ046t`/`integ007t` 均在 `ARCH_CFX_PROBES`，`Makefile:1706`）。

### cfx3 hmon — gem5

- **寄存器面**：有。cfx3 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`），cg7 hmon 块 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:457`，hmon 区间 `components/gem5/patches/configs/dadao/fs.py.patch:102`。
- **命令与副作用**：有。`nodeCfxEnter`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:308`）、`nodeTrap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:929`）、`nodeEscape`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:968`）、帧屏蔽异步（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:283`）。
- **异常与子原因**：有。`components/gem5/patches/src/arch/dadao/node_cfx.hh.patch:55` cause 常量；`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:319` 结构校验；`CFXMEM` 子原因在 TLB 侧（`components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:151`）。
- **现有测试载体**：gem5 FS，但**仅 Tiny**：`tools/gem5/check_tiny_hmon.py:1`（Tiny 两件装载 + hmon）；Vast 无 hmon 用例。
- **现有门控**：手工脚本（`python3 tools/gem5/check_tiny_hmon.py`；`Makefile` 无该目标）。Vast 侧无。

### cfx3 hmon — RTL

- **寄存器面**：有。hmon 是 `WumingGewuParams` 的第一项（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:134`），通用行解析 `components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:467`；hmon 帧归属 `monitor = 0`（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:154`）。
- **命令与副作用**：有。`trap`/`escape`（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:1421`、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:1565`），异常进入/返回 `GewuFile`（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:721`）。
- **异常与子原因**：有。`GewuCauseId` 子原因表与 wyde 规则（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:100`），帧写入点结构断言（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:742`）。
- **现有测试载体**：RTL ELF+loadmem。`tools/chipyard/excp/causeid.S:1`（全宽 cause_id/cause_info）与 `tools/chipyard/excp/prevcfx.S:1`（power→hmon 移交与 `cg5 rc1`）。
- **现有门控**：手工脚本（`tools/chipyard/excp/check_causeid.py:1`、`tools/chipyard/excp/check_prevcfx.py`；`Makefile` 无 chipyard 目标）。

---

## cfx4 ptw（page table walker / TLB）

### cfx4 ptw — QEMU

- **寄存器面**：有。cfx4 在 Vast 掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`）；`cg8 rc8` ptw_enable、`cg9 rc0` PTBR、`cg12 rc0..3` TLB 控制/ASID/始/长（`components/qemu/patches/target/dadao/helper.c.patch:2048`）。
- **命令与副作用**：有。`tlb_control` 写即执行（`components/qemu/patches/target/dadao/helper.c.patch:707`、`components/qemu/patches/target/dadao/helper.c.patch:3125`）；两级步查 `dadao_ptw_walk`（`components/qemu/patches/target/dadao/helper.c.patch:771`）；TLB 命中/填充（`components/qemu/patches/target/dadao/helper.c.patch:536`、`components/qemu/patches/target/dadao/helper.c.patch:633`）。
- **异常与子原因**：有。`CFXMEM` 的 `ISPFTRAP/IGPTRAP/DGPTRAP/NONPTW/ADWBFAIL` 与 `CFXPERM` 的 `NW/NR/NX/NH PERM`（`components/qemu/patches/target/dadao/helper.c.patch:570`、`components/qemu/patches/target/dadao/helper.c.patch:792`、`components/qemu/patches/target/dadao/helper.c.patch:818`）。
- **现有测试载体**：QEMU bootrom 探针。`tools/testcases/arch/min_rom_probe_tlb.py:1`（15 条 `arch-ptw-001..015`，期望清单 `tests/arch/ptw/expected.yaml:1`）；另有 `tools/testcases/arch/min_rom_probe_integ039t.py`、`tools/testcases/arch/min_rom_probe_integ040t.py`。
- **现有门控**：`check-arch`（L3，`tlb`/`integ039t`/`integ040t` 在 `ARCH_CFX_PROBES`，`Makefile:1706`）。

### cfx4 ptw — gem5

- **寄存器面**：有。cfx4 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`）；ptw 行解析 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:526`（enable/PTBR/TLB 控制）。
- **命令与副作用**：有。TLB 维护与步查在 `components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:127`（PTE 回写）与 `components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:146`（缺页子原因）+ `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:1080` 一带的 `tlbControl` 执行。
- **异常与子原因**：有。`components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:151`（IGPTRAP/DGPTRAP/ISPFTRAP/DSPFTRAP）、`components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:167`（NU/NH PERM）、`components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:262`（NX/NW/NR）、`components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:308`（ADWBFAIL）、`components/gem5/patches/src/arch/dadao/node_tlb.cc.patch:378`（NONPTW）。
- **现有测试载体**：无（Vast cfx4 无 gem5 用例）。
- **现有门控**：无。

### cfx4 ptw — RTL

- **寄存器面**：有。`GewuPtwParams`（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:225`）与六个行译码（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:479`）；ptw 仅 `useVM = true` 的 Vast 注入（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:147`）。
- **命令与副作用**：有。`tlb_control` 写脉冲与 scope/size 校验（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:1582`）；步查 `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingPtw.scala.patch:415`；I/D TLB `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingTlb.scala.patch:65`。
- **异常与子原因**：有。`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingPtw.scala.patch:303`（HSJU→NU/NH PERM）、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingPtw.scala.patch:306`（NX/NW/NR）、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingPtw.scala.patch:491`（ADWBFAIL）、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingPtw.scala.patch:417`（NONPTW）；`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingTlb.scala.patch:171`（IGPTRAP/DGPTRAP）。
- **现有测试载体**：RTL ELF+loadmem。`tools/chipyard/ptw/vastptw.S:1`（寄存器面 19 记录）、`tools/chipyard/ptw/vastwalk.S:1`（两级步查/A-D）、`tools/chipyard/tlb/vasttlb.S:1`（I/D TLB）。
- **现有门控**：手工脚本（`tools/chipyard/ptw/check_vastptw.py:1`、`tools/chipyard/ptw/check_vastwalk.py`、`tools/chipyard/tlb/check_vasttlb.py`；`Makefile` 无对应目标）。

---

## cfx5 cache（cache organization）

### cfx5 cache — QEMU

- **寄存器面**：缺。cfx5 不在 Vast 实现掩码（`components/qemu/patches/target/dadao/cpu.c.patch:55` 只有 0/1/2/3/4/15/32/34/63），访问按未实现 cfx 报 `CFXREG`（`components/qemu/patches/target/dadao/helper.c.patch:2955`）；现场 `grep -rn "cfx_cache\|cache-model" components/qemu/patches` = 0 命中。
- **命令与副作用**：缺。无 cache 模型、无 cfx5 clean/invalidate 命令；同样 0 命中（arch 规定 `-machine kaiwu-vast,cache-model=on` 属 `m16-qemu-001`）。
- **异常与子原因**：缺。除「cfx5 寄存器访问 ⇒ CFXREG」外，无 cfx5 自身 cause/子原因。
- **现有测试载体**：无。
- **现有门控**：无。

### cfx5 cache — gem5

- **寄存器面**：缺。`kCfxhaMap` 无 5（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`）；现场 `grep -rn "cfx_cache\|CfxhaCache\|cache-model" components/gem5/patches` = 0 命中。
- **命令与副作用**：缺。FS 配置明写 `no caches`（`components/gem5/patches/configs/dadao/fs.py.patch:23`），未接 `--caches`，也无 `IsLoad/IsStore/IsAtomic`（现场 grep 0 命中）。
- **异常与子原因**：缺。无 cfx5 专属 cause；cache 相关访存异常仍走 cfx4/cfx3。
- **现有测试载体**：无。
- **现有门控**：无。

### cfx5 cache — RTL

- **寄存器面**：缺。`GewuParams` 的 cfx 序列只有 hmon/power/ptw（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:132`），无 cache 行 ⇒ CFXREG。
- **命令与副作用**：缺。cache 阵列已实现（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCache.scala.patch:135`），但 clean/invalidate 端口仅供内部，源码明写「`cfx5` wiring is a later task」（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCache.scala.patch:49`、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCache.scala.patch:158`；`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:747`、`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch:1060`）。
- **异常与子原因**：缺。无 cfx5 命令面，故无 cfx5 自身异常；cache 访存异常仍走 cfx4/cfx3。
- **现有测试载体**：无 cfx5 寄存器用例。`tools/chipyard/dcache/vastdcache.S:1` 与 `tools/chipyard/icache/vasticache.S:1` 只测 cache 阵列（命中/缺失/替换），不测 cfx5 寄存器/命令。
- **现有门控**：手工脚本（`tools/chipyard/dcache/check_vastdcache.py:1`、`tools/chipyard/icache/check_vasticache.py:1`；不覆盖 cfx5）。

---

## cfx15 hart（hart 标识 / 定时器）

### cfx15 hart — QEMU

- **寄存器面**：有。cfx15 在 Vast 掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`）；`cg8 rc0/2/3/4/5` = hart_id/cycle/insn/timer_cmp/ctrl|ISTATUS（`components/qemu/patches/target/dadao/helper.c.patch:2552`）。
- **命令与副作用**：有。单 hart 一次性定时器：`cg8 rc4/rc5` 写（`components/qemu/patches/target/dadao/helper.c.patch:2759`）、arming（`components/qemu/patches/target/dadao/helper.c.patch:2712`）；TIMER pending 落目标 cfx `cg5 rc5`（`components/qemu/patches/target/dadao/helper.c.patch:2705`）。
- **异常与子原因**：有。`TIMER = 1<<10`（`components/qemu/patches/target/dadao/cpu.h.patch:358`），异步源映射 `components/qemu/patches/target/dadao/helper.c.patch:2611`；`cause_info = 0`（`components/qemu/patches/target/dadao/helper.c.patch:2672` 一带）。
- **现有测试载体**：QEMU bootrom 探针。`tools/testcases/arch/min_rom_probe_integ050t.py:1`（cfx_time/cfx_hart 寄存器与计数器）、`tools/testcases/arch/min_rom_probe_integ051t.py:1`（统一异步仲裁/TIMER）。
- **现有门控**：`check-arch`（L3，`integ050t`/`integ051t` 在 `ARCH_CFX_PROBES`，`Makefile:1706`）。

### cfx15 hart — gem5

- **寄存器面**：有。cfx15 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`）；`hartRegRead`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:670`）、`hartRegWrite`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:703`）。
- **命令与副作用**：有。定时器事件 `NodeTimerEvent`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:108`）、到期处理 `nodeTimerExpire`（同文件 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:880` 一带）。
- **异常与子原因**：有。`CauseTimer = 1<<10`（`components/gem5/patches/src/arch/dadao/node_cfx.hh.patch:69`）。
- **现有测试载体**：无（Vast cfx15 无 gem5 用例）。
- **现有门控**：无。

### cfx15 hart — RTL

- **寄存器面**：缺。`WumingCfxHa` 无 hart（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:89`）；现场 `grep -rl cfx_hart components/chipyard/patches` = 0 命中。
- **命令与副作用**：缺。无 hart 行、无定时器实现。
- **异常与子原因**：缺。无 TIMER 源。
- **现有测试载体**：无。
- **现有门控**：无。

---

## cfx32 pmem（64 KiB SRAM + DMA）

### cfx32 pmem — QEMU

- **寄存器面**：有。cfx32 在 Vast 掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`）；64 KiB SRAM 窗口（`components/qemu/patches/target/dadao/helper.c.patch:1058`；宿主侧映射 `components/qemu/patches/hw/dadao/dadao-machine.c.patch:1119`）；`cg15 rc0..4` DMA 寄存器（`components/qemu/patches/target/dadao/helper.c.patch:2386`、`components/qemu/patches/target/dadao/helper.c.patch:2404`）；cg7 pmem 块（`components/qemu/patches/target/dadao/helper.c.patch:1975`）。
- **命令与副作用**：有。`cg15 rc3` 写 START 触发 DMA，1 ms 虚拟时间完成（`components/qemu/patches/target/dadao/helper.c.patch:2338`、`components/qemu/patches/target/dadao/helper.c.patch:2380`）；BUSY 期间写 rc0..3 被忽略（`components/qemu/patches/target/dadao/helper.c.patch:2404`）。
- **异常与子原因**：有。`PMEM_DMA = 1<<8`（`components/qemu/patches/target/dadao/cpu.h.patch:405`）；PA/尺寸/CFX 越界错误码（`components/qemu/patches/target/dadao/helper.c.patch:2349`～`components/qemu/patches/target/dadao/helper.c.patch:2364`）。
- **现有测试载体**：QEMU bootrom 探针。`tools/testcases/arch/min_rom_probe_integ042t.py:1`（SRAM+DMA）、`tools/testcases/arch/min_rom_probe_integ047t.py:1`（DMA 的 SBI 契约）。
- **现有门控**：`check-arch`（L3，`integ042t`/`integ047t` 在 `ARCH_CFX_PROBES`，`Makefile:1706`）。

### cfx32 pmem — gem5

- **寄存器面**：有。cfx32 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`）；`dmaRegRead`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:556`）、`dmaRegWrite`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:624`）；pmem 64 KiB 区间（`components/gem5/patches/configs/dadao/fs.py.patch:104`）。
- **命令与副作用**：有。DMA 事件 `NodeDmaEvent`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:93`）与完成处理（同文件 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:600` 一带）。
- **异常与子原因**：有。`CausePmemDma = 1<<8`（`components/gem5/patches/src/arch/dadao/node_cfx.hh.patch:70`）。
- **现有测试载体**：无（Vast cfx32 无 gem5 用例）。
- **现有门控**：无。

### cfx32 pmem — RTL

- **寄存器面**：缺。`WumingCfxHa` 无 pmem（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:89`）；现场 `grep -rl cfx_pmem components/chipyard/patches` = 0 命中。
- **命令与副作用**：缺。无 64 KiB SRAM / DMA 命令。
- **异常与子原因**：缺。无 `PMEM_DMA` 源。
- **现有测试载体**：无。
- **现有门控**：无。

---

## cfx34 time（全局时间）

### cfx34 time — QEMU

- **寄存器面**：有。cfx34 在 Vast 掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`）；`cg10 rc0` = 频率、`rc1` = 64 位时间值（`components/qemu/patches/target/dadao/helper.c.patch:2531`）。
- **命令与副作用**：有。时间值取自 `QEMU_CLOCK_VIRTUAL`，epoch = 复位时刻（`components/qemu/patches/target/dadao/helper.c.patch:2524`）；`cg10` 只读，写报 `CFXREG`（`components/qemu/patches/target/dadao/helper.c.patch:3079`）。
- **异常与子原因**：有（仅 CFXREG）。无 cfx34 自身 cause/子原因；非法写走通用 CFXREG（`components/qemu/patches/target/dadao/helper.c.patch:3079`）。
- **现有测试载体**：QEMU bootrom 探针。`tools/testcases/arch/min_rom_probe_integ050t.py:1`（cfx_time 1 GHz/64 位）。
- **现有门控**：`check-arch`（L3，`integ050t` 在 `ARCH_CFX_PROBES`，`Makefile:1706`）。

### cfx34 time — gem5

- **寄存器面**：有。cfx34 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`）；`timeRegRead`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:729`，rc0=freq、rc2=time value）。
- **命令与副作用**：有。`nodeTimeValue` 取 `curTick()` 并换算纳秒（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:177`）；cfx34 只读。
- **异常与子原因**：有（仅 CFXREG）。非法写走通用寄存器判定（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:1077` 起的 `nodeCfxWrite`）。
- **现有测试载体**：无（Vast cfx34 无 gem5 用例）。
- **现有门控**：无。

### cfx34 time — RTL

- **寄存器面**：缺。`WumingCfxHa` 无 time（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:89`）；现场 `grep -rl cfx_time components/chipyard/patches` = 0 命中。
- **命令与副作用**：缺。无时间寄存器。
- **异常与子原因**：缺。无 cfx34 行，访问报 CFXREG。
- **现有测试载体**：无。
- **现有门控**：无。

---

## cfx63 power（BootROM / 复位）

### cfx63 power — QEMU

- **寄存器面**：有。cfx63 在 Vast 掩码内（`components/qemu/patches/target/dadao/cpu.c.patch:55`）；通用行 + cg7 BootROM 块（`components/qemu/patches/target/dadao/helper.c.patch:1978`）；复位 `inner_cfx_code = 63`（`components/qemu/patches/target/dadao/cpu.c.patch:286`）。
- **命令与副作用**：有。复位向量/BootROM 装载（`components/qemu/patches/target/dadao/cpu.h.patch:227` 的 Vast 几何），`trap cfx_hmon` 移交属固件（`tests/ee-vast/power_vast.S:1`）。
- **异常与子原因**：有。cfx63 作为普通 cfx 参与通用 cause/两轴权限（`components/qemu/patches/target/dadao/cpu.h.patch:299`、`components/qemu/patches/target/dadao/helper.c.patch:63`）。
- **现有测试载体**：QEMU bootrom 探针。`tools/testcases/arch/min_rom_probe_integ046t.py:1`（step5 启动链 power→hmon）；镜像源 `tests/ee-vast/power_vast.S:1`。
- **现有门控**：`check-arch`（L3，`integ046t`/`integ049t` 在 `ARCH_CFX_PROBES`，`Makefile:1706`；`check-arch-smoke` 也用同一 BootROM，`Makefile:1717`）。

### cfx63 power — gem5

- **寄存器面**：有。cfx63 在 `kCfxhaMap`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:33`）；复位 `s.cfxCode = CfxhaPower`（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:197`）；cg7 BootROM 块（`components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:457`）。
- **命令与副作用**：有。Vast BootROM 区间 4 MiB（`components/gem5/patches/configs/dadao/fs.py.patch:92`），复位/装载由 FS 配置驱动。
- **异常与子原因**：有。`components/gem5/patches/src/arch/dadao/node_cfx.hh.patch:55` cause 常量与 `components/gem5/patches/src/arch/dadao/node_cfx.cc.patch:319` 结构校验。
- **现有测试载体**：无（Vast cfx63 无 gem5 用例；Tiny `check_tiny_hmon` 覆盖 power→hmon，但不在 Vast 范围）。
- **现有门控**：无（Vast）。

### cfx63 power — RTL

- **寄存器面**：有。power 是 `WumingGewuParams` 第二项（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:142`），BootROM 描述 `exists|ROM`（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:143`）、`R|X`（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingParams.scala.patch:145`）；通用行解析 `components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:467`。
- **命令与副作用**：有。复位从 BootROM 取指、`trap cfx_hmon` 移交由固件完成（`tests/ee-vast/power_vast.S:1`）；Tiny 的 bootrom hex 资源在同名补丁树（`components/chipyard/patches/generators/dadao-wuming/src/main/resources/dadao/bootrom/bootrom.tiny.hex.patch:1`）。
- **异常与子原因**：有。通用 cause 表/两轴权限（`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:100`、`components/chipyard/patches/generators/dadao-gewu/src/main/scala/gewu/GewuFile.scala.patch:735`）。
- **现有测试载体**：RTL ELF+loadmem。`tools/chipyard/excp/prevcfx.S:1` 校验 power→hmon 移交的 `cg5 rc1`；`tools/chipyard/excp/causeid.S:1` 走同一固件链。
- **现有门控**：手工脚本（`tools/chipyard/excp/check_prevcfx.py`、`tools/chipyard/excp/check_causeid.py`；`Makefile` 无 chipyard 目标）。
