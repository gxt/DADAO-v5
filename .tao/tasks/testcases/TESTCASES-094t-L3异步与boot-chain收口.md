# TESTCASES-094t: L3 异步投递与 boot-chain 收口（integ049/050/051 + integ046 + 046t）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-093t`（开工前置：共享 prelude / F4 / 已绿 9 册）、`QEMU-080t`（Node 4 MiB BootROM、hmon/PTW/hypv）、`SPEC-183t`（`spec/Machine-v5` 真源）、`INTEG-046t`/`INTEG-049t`/`INTEG-050t`/`INTEG-051t`（已归档，仅口径溯源）
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根；任务分支 `TESTCASES-094t`；`.dadao/`、`.work/` 已就绪；不重建 QEMU/LLVM，不 merge、不 push）

## 用户已定口径（2026-11-03，自包含）

- 只修**测试资产/harness/门控**：允许改 `tools/testcases/**`、`Makefile`；**禁改** `components/**`（QEMU/gem5）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`。
- **不得伪造**：期望值只从 `spec/` + `.tao/contracts/` + `tests/shared/machine-profiles.yaml` 派生；每条结论带真实命令与真实 rc；失败保留现场、继续推进。
- **不重建 QEMU**：QEMU 二进制 md5 开工/收尾不变；`check-source-state` rc=0；不触发 `install-host` 的 LLVM 全量重建（若触发，按环境 BLOCKED 报告，不硬跑）。
- **归属先行**：异步/描述符/boot chain 的问题必须先判定是 **tests/tools 驱动** 还是 **QEMU/规范** 缺陷；QEMU 侧缺陷本册只登记 BLOCKED + 现场，**不在本任务伪改**（改 QEMU 或改 spec 均需单独任务 + 用户裁定）。
- **093 补丁只作内容溯源**：`.work/evidence/TESTCASES-093t/partial-094.patch`（实存于 093t worktree；主树无此文件）必须逐 hunk 重新核对后再用，不得直接当成品；开工先固化到 `.work/evidence/TESTCASES-094t/inherited/` 并记 md5。
- 禁从 `ARCH_CFX_PROBES`/用例表删探针；禁改期望使 `0x81`/`0x89` 假绿；BLOCKED 必须含 case、spec 节号、现场日志、裁定选项。

## 现状证据（2026-11-03 规划期，本机真跑；QEMU=`.dadao/cross-toolchain/bin/qemu-system-dadao`，profile=node）

### E1 继承物与基线

- 093t 已把 F4（`check-arch` 显式 `--qemu`）+ `tools/testcases/arch/node_probe_prelude.py`（power 复位 + hmon identity-PTW + 4 MiB `bootrom-image` + 无 `-kernel`）与 9 册探针收口为 167 例绿；本册承接其**未迁移**的 `integ049t/integ050t/integ051t`、H 类 `integ046t` 与 `check-arch-smoke[2/2]` 的 `min_rom_probe_046t`。
- 093t 分支的迁移后现场（`.work/log/arch/` 与 `/tmp/opencode/TESTCASES-093t/runall/`，**易失**）：`integ049t` 11/12、`integ050t` 12/16 runtime、`integ051t` 0/12 runtime（2 项 offline 结构检查 PASS）。主树对应文件仍是未迁移态；**数必须重跑复核**。
- 规划期主树真跑：
  - `DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_integ046t.py --qemu …` ⇒ **rc=1**：8 runtime FAIL（全 `rc=137`=0x89 UNDI）、6 negative PASS（0xB1–0xB5、0xB9）、`hmon_magic_mismatch` 崩溃（`power trap instruction not found`）、`flags_verify_off` 未执行。
  - `DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_046t.py --qemu …` ⇒ **rc=1**：32 例全 FAIL（多数 `got=0x81` CFXMEM），仅 `service coverage` 汇总检查 PASS。

### E2 `integ049t space_power`（1 例，期望 vs QEMU 描述符）

- 现场：`space_power` `(cfxha<<42)|start = 0xffff_fffc_0000 != §2.1 0xffff_ffc0_0000`；其余 11 例 PASS。
- 探针期望（`BLOCK0[63]`，按 spec/Machine-v5 §2.1 派生）：`desc/start/size/attr = 5/0x3FF_FFFC_0000/0x4_0000/5`，且 `start+size=2^42`、`(63<<42)|start=0xFFFF_FFC0_0000`。
- QEMU 源（`components/qemu/patches/target/dadao/helper.c.patch:1576-1580`）：`power` 表 `start=0x3FFFFFC0000`、`size=0x40000`（**只剩末 256 KiB**），注释亦写 “power 256 KiB BootROM”；spec 的 Node 4 MiB `0xffff_ffc0_0000..0xffff_ffff_ffff` 对应 `start=0x3FF_FFC0_0000`、`size=0x40_0000`。
- 判定：**QEMU 描述符陈旧**（`cg7` 静态表按编译期常量、两 profile 共用；Tiny 无 `cfx_power`，修复须按 profile 分派）。不在本册伪改。

### E3 `integ050t`（17 例：16 runtime + `doc_shape`；4 例失败）

- 迁移后 12/16 runtime PASS；失败 4 例均与**实际投递**有关：`timer_cmp_clears`（0xE2）、`timer_interrupt`（0xE1）、`timer_imask_pending`（0xE4）、`timer_retrigger`（0xE1）。
- `timer_istatus`/`timer_ones_disable`/`sbi_hart_set_timer` PASS ⇒ 比较器/ISTATUS/一次性条件成立，**TIMER 到期→handler 的实际投递未发生**（`RAM_STATE+0x18` 计数恒 0）。

### E4 `integ051t`（14 例：12 runtime + 2 offline；12 runtime 全失败）

- offline `doc_shape`/`no_async_enable` PASS；12 runtime 全 FAIL，且失败点集中在第一处 pending/投递断言：
  `pmem_pending_in_pmem`（0xA4）、`timer_pending_in_hart`（0xB4）、`pending_no_cross_cfx`（0xC6）、`global_mask_block`（0xD1）、`per_cfx_mask_block`（0xE3）、`cause_mask_block`（0xF3）、`timer_imask_hold`/`low_cfxha_first`/`escape_kick`/`direct_target`/`dedup_same_source`/`pmem_error_info`（更早失败，日志码 3/18/33/49/67/81）。
- 与 E3 同源信号：**pending 位可能写入、但 `cfx_enter(async)`/re-kick 未实际投递**；`integ051t` 的 QEMU 静态断言（`structure: 0 failed`）仍 PASS，说明补丁树形状未变，问题在**运行期仲裁/驱动**。

### E5 `integ046t`（16 例：8 runtime + 6 negative PASS + 1 崩溃 + 1 未达）

- 8 runtime 例（`chain_basic`…`no_resume_poison`）全 `rc=137`（0x89 UNDI）；最后 dump PC = `0x0fff_0000_0118`（hmon 的 `trap cfx_umon, 0`）后跳到 `ENTRY=0x10_0000`；探针的 `-dfilter` 只覆盖 power/hmon/smon 三个窗口，**RAM 本体未装载**，`ENTRY` 处为零字 ⇒ UNDI。
- 最小验证（规划期，手工 256 B 本体 + `bootrom-image` + `-kernel`）：语义正确的最小 body 在 `0x10_0000` 执行并 `SYS_EXIT 0x42`，QEMU 回 **rc=66(0x42)** ⇒ `bootrom-image` 与 `-kernel` 可共存，链 `power→hmon→ENTRY` 正常；**8 例的 smon 期望/无本体装载属测试资产陈旧**（`hmon.S` 明写 Node “smon is reserved and not used by this stage”）。
- 崩溃 `hmon_magic_mismatch`：`POWER_OFF=0x30000`、`ROM_SIZE=0x40000` 是旧 256 KiB 布局；实际 power 在 4 MiB 镜像偏移 `0x3F0000`，`patch_trap_magic()` 扫错区间。负例 0xB1–0xB5 仍 PASS（它们按表偏移构造，不依赖该常量）。

### E6 `min_rom_probe_046t`（32 例 + service-coverage）

- 32 例全 FAIL（多数 `got=0x81`）；探针仍用 `-bios` + `-kernel`，参数块 `K_OPEN/K_SVC/K_BUF/K_PATH/K_STR` 由 `-kernel` 预置，本体在 power 执行且未过 PTW ⇒ RAM 访问/参数块读取即 CFXMEM。
- 需按 093t G 类：共享 prelude + 4 MiB `bootrom-image` + **无 `-kernel`**，参数块/路径串/argv 改为**运行期物化**（PTW 后用 `st.o` 写 RAM 或 ROM 内嵌拷贝），并逐字节核对 64-bit BE 字段。

## 目标

1. **三册迁移收口**：`integ049t` 11/12 绿 + `space_power` 按裁定 BLOCKED；`integ050t`/`integ051t` 先判定归属，再修驱动或 BLOCKED。
2. **异步归属判定**：用最小两-cfx 探针证明 TIMER/PMEM_DMA 的 pending 位、mask、仲裁、投递到 handler 的全链路，给出 tests vs QEMU 的书面结论。
3. **boot chain 收口**：`integ046t` 16 例按 Node 现行口径（power→hmon→ENTRY）重写/判定；负例 0xB1–0xB5 不退化。
4. **smoke 册收口**：`min_rom_probe_046t` 32 例迁移到共享 prelude + 运行期物化，`check-arch-smoke[2/2]` 真实跑绿或逐例 BLOCKED。
5. 逐例 `verdict.tsv` + 证据/注入 + L1/L2；`check-arch`/`check-arch-smoke`/`run_m5_e2e`/`check-inst` 不退化；状态 `待验收`。

## 接口规范

### 0. 继承契约（093t §0/§2，自包含要点）

- 本体 `ROM_BASE = RESET_PC + 0x1000`，在 **hmon（cfx3/hypv）** 执行；power 段只装 `cfx_hmon.hypv.excp_vector` 并 `trap cfx_hmon,0`；hmon 段建 identity 超页（`PTE=0xF000_0000_0000_FFEF|(i<<29)`）、PMEM DMA 到 `pt_pa=0x7FF0_0000`、TLB invalidate、PTBR、`ptw_enable=1`，再 `jump` 到本体。
- 装载：4 MiB `bootrom-image`（Node 偏移 `0x3F0000`）+ `-semihosting-config`；**无 `-kernel`**；每例独立进程；QEMU 默认值为 `tools/infra/paths.py::host_toolchain_bin()/qemu-system-dadao`。
- 退出：profile `exit_block`（Node `0x7FFD_0000`），不写死 `0x00FF_F000`。
- 本册新增的 boot-chain 例外见 §4：`bootrom-image` **可与 `-kernel` 共存**（E5 实测），仅 boot chain 用 `-kernel` 提供 ENTRY 本体；L3 探针本体仍在 ROM、不再用 `-kernel`。

### 1. 三册迁移（`integ049t`/`integ050t`/`integ051t`）

- 以 093t `partial-094.patch` 为线索，**逐 hunk 重写/复核**（不直接 `git apply` 成品）：
  - `DEFAULT_QEMU` 改 `node_probe_prelude.default_qemu()`；`WORKDIR` 落 `/tmp/opencode/TESTCASES-094t/<probe>/`；
  - `ROM_BASE=_prelude.ROM_BASE`；`build_rom/run/exit_seq` 走共享实现；`hmon_addr(off)` 改本体相对；
  - `bootstrap_prefix/stage` 中 **power→hmon 交接与 power mask 清理由 prelude 负责**；探针只保留自身 hmon 向量/mask/pending 清理（`hmon_setup`/`hmon_extra`），不得把 prelude 的段重复一份。
- 迁移后先跑全册：`--list` 计数与 E1 一致；`integ049t` 应为 11 PASS + `space_power` 唯一 FAIL；`integ050t`/`integ051t` 的失败集合须与 E3/E4 对齐（不一致 ⇒ 先查迁移，不准直接下 QEMU 结论）。

### 2. 异步投递归属判定（先判后修）

- 在 `tools/testcases/arch/` 新增**最小两-cfx 探针**（本册资产，可独立运行；不得复制三册的完整 harness）：
  1. 仅 TIMER：hmon 下装 cfx_hart 向量、清 `excp_cause_mask` bit10 与全局 mask bit15，arm 一次，等 handler 计数；
  2. 仅 PMEM_DMA：cfx_pmem 一次 8 B DMA，等 cfx_pmem handler 计数；
  3. 两源同时 pending：验证“最低目标 cfxha 先”（15 再 17）、mask 释放后的 re-kick、同一源去重；
  4. 分别在 `-icount shift=0` 与默认时钟各跑一次。
- 判据（必须写进 `verdict.tsv` 的 `category`）：
  - **最小探针能投递、三册不能** ⇒ tests 侧（prelude 的 mask 清位/向量/时序/观察通道）→ 本册内修；
  - **最小探针也不能投递** ⇒ QEMU 异步仲裁/投递缺陷 → 逐例 `BLOCKED` + 现场 + 用户裁定（立 QEMU 任务），**不改期望**；
  - **pending 位本身不置位** ⇒ 先查 CFX 寄存器写权限/`cg5 rc5` 语义（spec/DADAO-12 §3.6/§5、ADR-0045 D3），再定归属。
- 交叉核对：`spec/DADAO-12 §5`、`spec/Machine-v5 §1/§2`、`.tao/contracts/contract-see.md`、ADR-0045 D3；`integ051t` 的 offline 结构断言（单一 `cfx_enter`、mask 只在 `cfx_enter`）继续作为 QEMU 形状证据，但**不等于运行期正确**。

### 3. `integ049t space_power`（期望 vs 描述符）

- 期望**保持 spec 派生值**（`0xFFFF_FFC0_0000`/4 MiB），不得为求绿改成 QEMU 的 256 KiB。
- 交付：① 描述符 vs spec 的逐字段对照（source 行号 + 值）；② `space_power` BLOCKED 记录（spec §2.1、现场日志、需裁定项）；③ 若用户裁定改 spec/期望，须给 spec 修订/ADR 依据，本册不自行改。
- 推荐处置：立 QEMU 任务把 `power` 描述符按 profile 分派（Node 4 MiB；Tiny 不实现 `cfx_power`），本册不改 `components/`。

### 4. `integ046t`（H 类 boot chain，独立处理）

- **不改 bootrom/ELF 二进制**；只改探针：
  - `ROM_SIZE/POWER_OFF` 从 profile 派生（`bootrom_size`；`POWER_OFF=bootrom_size-0x10000=0x3F0000`），`patch_trap_magic()` 扫 `[POWER_OFF, bootrom_size)`；
  - `POWER_WIN/HMON_WIN/SMON_WIN` 与 `build_step5_bootrom.py`/`hmon.S` 同源；`-dfilter` 增加 `ENTRY+image_window` 窗口，观察本体；
  - **8 runtime 例**：按 Node 现行口径（power→hmon→**ENTRY 本体**，smon reserved）重写——用 `-kernel` 提供最小本体（`kernel_base=0x10_0000`、`kernel_reserved=0`；E5 已证 `bootrom-image`+`-kernel` 可共存），本体只做 stage 标记/观察后 `SYS_EXIT`；若用户坚持保留 smon 三段链，则本组 BLOCKED（需 bootrom/规范变更，见 D3）。
  - 负例 0xB1–0xB5 与 0xB9 必须继续 PASS；`hmon_magic_mismatch` 修常量后应命中 0xB7；`flags_verify_off` 必须真实执行。
- 若根因落在 bootrom/规范（非测试资产）⇒ 该例 `BLOCKED` + 用户裁定，不把 QEMU/bootrom 改动塞进本册。

### 5. `min_rom_probe_046t`（G 类：运行期物化）

- 迁移到共享 prelude（本体 hmon、4 MiB `bootrom-image`、无 `-kernel`）；删除 `-bios`/`-kernel` 与 `K_*` 预置依赖。
- 参数块/路径串/argv：在 PTW 后用 `st.o` 写 RAM（或 ROM 内嵌+拷贝），逐字节核对 64-bit BE 字段、路径串、`SYS_GET_CMDLINE` 的 host argv；`-chardev file` 的输入/输出路径不变。
- 25 服务逐个真实执行；`svc_exit`/`svc_exit_extended` 的 host `$?` 必须等于期望码；保留 `service coverage` 汇总检查。
- 若某服务依赖 host 侧预置（非 guest 内存），在 `verdict.tsv` 标 `BLOCKED`（case + spec/contract 节号 + 现场），不得用假数据绕过。

### 6. 逐例判定（强制）

- 证据文件 `.work/evidence/TESTCASES-094t/verdict.tsv`，列：`probe, case, spec_ref, category, action, rc_before, rc_after, blocker`。
- 类别沿用 093t §3（A 装载 / B cfx 寄存器 / C PTW-TLB / D ROM 内容 / E 上下文掩码 / F 时间-icount / G kernel 预置 / H boot chain），另加 **I 异步投递**（区分 tests/QEMU）。
- 任务书完成区只放按册汇总 + BLOCKED 清单（≤30 行），长日志留 `.work/log/{arch,testcases}/`。

## 实施顺序

- **P0 继承与基线**：固化 093t patch/日志到 `.work/evidence/TESTCASES-094t/inherited/`（md5）；记录 HEAD、QEMU md5、`check-source-state`；5 册 `--list` 计数与 rc 基线（自查，不是验收）。
- **P1 三册迁移**：§1；`integ049t` 先跑（11/12），再 `integ050t`/`integ051t`（对齐 E3/E4）；每册产 `verdict.tsv` 骨架。
- **P2 归属判定**：§2 最小两-cfx 探针；出 tests/QEMU 结论后再动 050/051 用例。
- **P3 `space_power`**：§3 对照 + BLOCKED（或按用户裁定）。
- **P4 boot chain + smoke 册**：§4 `integ046t`（先修常量/崩溃，再 8 runtime）；§5 `min_rom_probe_046t`（先迁 1 个服务单例，再全量）。
- **P5 门控与收尾**：`check-arch`/`check-arch-smoke`/`run_m5_e2e`/`check-inst`/L1/L2；证据脚本 + 注入；台账/体例；状态 `待验收`。

## 验收标准

1. **三册迁移**：`integ049t` 11/12 PASS + `space_power` BLOCKED（含 spec §2.1、现场日志、裁定选项）；`integ050t`/`integ051t` 每例有 `verdict.tsv` 行（PASS 或 BLOCKED/QEMU 结论），失败集合与 E3/E4 逐项对齐；迁移不得引入新的 `0x81`。
2. **异步归属**：最小两-cfx 探针（TIMER/PMEM_DMA/双源）在 `-icount` 与默认时钟各给出真实 rc；结论明确写“tests 侧修复”或“QEMU 缺陷 BLOCKED”；若 QEMU 缺陷，4+12 例逐条 BLOCKED（case、spec 节号、日志、用户裁定），**不改期望**。
3. **`integ046t`**：16 例全部真实执行；8 runtime 按 Node 口径（power→hmon→ENTRY）通过或 BLOCKED（D3 裁定）；6 negative 保持 PASS；`hmon_magic_mismatch` 命中 0xB7、`flags_verify_off` 真实执行；常量与 `build_step5_bootrom.py` 同源。
4. **`min_rom_probe_046t`**：32 例 + service-coverage 全部真实执行；无 `-bios`/`-kernel`；`K_*` 运行期物化且逐字节核对；`check-arch-smoke[2/2]` rc=0（或逐例 BLOCKED + 用户裁定）。
5. **逐例判定**：`verdict.tsv` 行数 == 5 册 `--list` 现场总数（规划期 **91**：12+17+14+16+32；开工以现场为准）；每例有 spec/contract 节号、类别、`rc_before/rc_after`；无“未跑先写 PASS”。
6. **门控不退化**：093t 已绿 9 册 + `integ049t` 的 11 例保持 rc=0；`check-arch` 不新增非 BLOCKED 红；`check-arch-smoke[1/2]` 10/10；`run_m5_e2e` 10/10；`check-inst` Node/Tiny 计数以现场为准（093t 口径 Node 968 / Tiny 44）。
7. **证据/注入**：`.work/evidence/TESTCASES-094t/run.sh` 一条命令重跑全部断言、逐项取命令自身 rc（禁 `tee` 吞码）；`inject.sh` ≥3 类互不相同：① 异步 pending/投递（删 pending 写或 mask 位）⇒ 对应例 FAIL；② boot chain 删 `-kernel` 本体 ⇒ `integ046t` runtime FAIL；③ `046t` 删一个参数块物化 ⇒ 对应服务 FAIL；均 `cp`+`md5sum -c` 还原后回绿，禁 `git checkout/restore/stash/show`。
8. **范围**：`git status --porcelain -uall` 仅允许文件；`components/** spec/** contracts/** .tao/contracts/** .tao/adr/** manifests/**` 零 diff；QEMU md5 不变；`check-source-state` rc=0。
9. **L1/L2**：`make -k check` 中本册触及项 PASS（外部基线红逐条声明非本任务）；`make check-modules` rc=0（若触发 LLVM 全量重建 ⇒ 环境 BLOCKED + 现场，不强跑）。
10. **体例/台账**：`make check-tasks`、`make check-milestones-fresh`、`make check-no-residue` rc=0；完成区 ≤30 行、审阅记录每轮 ≤40 行；状态 `待验收`。

## 未决（下发前请用户确认）

1. **D1 `space_power` 处置**：推荐 **A** 立 QEMU 任务修 `cg7 power` 描述符（按 profile：Node 4 MiB `start=0x3FF_FFC0_0000/size=0x40_0000`；Tiny 不实现 `cfx_power`），本册保持 `space_power` BLOCKED、改期望不做。**B** 改 spec/期望为 256 KiB（需 SPEC 任务 + 用户裁定，和 Machine-v5 §2.1 冲突，不推荐）。**C** 退役该例（不推荐）。
2. **D2 异步归属**：最小探针若证实 QEMU 缺陷，推荐 **A** 立 QEMU 异步任务（本册 4+12 例 BLOCKED，不伪绿）；**B** 若 tests 侧，本册内修（不需裁定）。若用户要求“本册内一并改 QEMU”，超出本册范围，需另授权。
3. **D3 `integ046t` 口径**：推荐 **A** 按 Node 现行 `hmon.S`/ADR-0043（smon reserved、power→hmon→ENTRY 本体）重写 8 runtime 例并删/改 smon 期望；**B** 保留三段 smon 链 ⇒ 需 bootrom/规范变更，本组 BLOCKED 移交。请确认 A/B。
4. **D4 `046t` 运行期物化**：默认 **A**（本册内迁移 + 逐字节核对）；若某服务必须依赖 host 侧预置，逐例 BLOCKED 并说明，不扩大到 QEMU/规范。

## 文件范围

- **允许**：
  - `tools/testcases/arch/**`（`integ049t/integ050t/integ051t/integ046t/min_rom_probe_046t`、新增最小两-cfx 探针、必要时 `build_step5_bootrom.py` 的只读常量核对）；
  - `tools/testcases/lib/**`（仅共享 helper：qemu 默认解析/exit_seq/profile，不改 inst 语义）；
  - `Makefile`（仅 `check-arch`/`check-arch-smoke` 的探针选择或传参，如需）；
  - `tests/shared/asm/**`（仅新增共享宏，先经主会话确认；默认不改）；
  - 本任务书、`.tao/knowledge/milestones.md`（流水行）、`.work/evidence/TESTCASES-094t/**`、`.work/log/{arch,testcases}/**`、`/tmp/opencode/TESTCASES-094t/**`。
- **禁止**：`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`、`.work/source/**` 源码改写；**不提交 git**（提交权归 architect）。

## 风险

- **R1 继承物易失**：093t patch/日志在 `/tmp`/worktree；P0 不固化就无法开工。先 cp + md5，再动代码。
- **R2 归属误判**：把 QEMU 异步缺陷当 tests 修（或反之）会空转；必须先用最小探针给出可复现 rc，再改三册。
- **R3 boot chain 口径**：`integ046t` 的 smon 期望与现行 `hmon.S` 冲突；按 D3 裁定执行，禁“改期望求绿”。
- **R4 `-kernel` 与 093 规则**：093t 对 L3 探针“去 `-kernel`”；`integ046t` 的 `bootrom-image`+`-kernel` 是**例外**（E5 实测），须在任务书/完成区显式说明，不得把 L3 探针重新带回 `-kernel`。
- **R5 时间/icount**：prelude DMA=1 ms 虚拟时间；`-icount shift=0` 下阈值/超时按本体起点重新基线，防假 FAIL。
- **R6 磁盘/日志**：4 MiB 镜像 × 91 例 + `-d cpu` 可占数百 MB～GB；一律落 `/tmp/opencode/TESTCASES-094t/`，结论日志留 `.work/log/arch/`。
- **R7 环境**：`check-arch` 依赖 `install-host → build-mc`；若触发 LLVM 全量重建，停并报 BLOCKED（不在本任务重建）。

## 参考对照（0628 溯源，非执行必需）

「内容溯源，非执行必需」：`DADAO-0628` 的 QEMU/gem5 为单几何 + host 代劳启动，无 Node 4 MiB BootROM / hmon identity-PTW / cfx 异步仲裁；v5 以 `QEMU-080t` + `spec/Machine-v5` + `spec/DADAO-12 §5` 为准，不复用其装载代码/常量/测试。落点 = 本册 §0–§5 的 harness 与归属判定，不是 0628 结构。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

（待 engineer 自审 / reviewer 验收后按轮次追加；每轮 ≤40 行）
