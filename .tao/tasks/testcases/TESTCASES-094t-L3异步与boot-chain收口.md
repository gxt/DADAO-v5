# TESTCASES-094t: L3 异步投递与 boot-chain 收口（integ049/050/051 + integ046 + 046t）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-093t`（开工前置：共享 prelude / F4 / 已绿 9 册）、`QEMU-080t`（Node 4 MiB BootROM、hmon/PTW/hypv）、`SPEC-183t`（`spec/Machine-v5` 真源）、`INTEG-046t`/`INTEG-049t`/`INTEG-050t`/`INTEG-051t`（已归档，仅口径溯源）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；任务分支 `TESTCASES-094t`；`运行期安装根`、`运行期临时目录` 已就绪；不重建 QEMU/LLVM，不 merge、不 push）

## 用户已定口径（2026-11-03，自包含）

- 只修**测试资产/harness/门控**：允许改 `tools/testcases/**`、`Makefile`；**禁改** `components/**`（QEMU/gem5）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`。
- **不得伪造**：期望值只从 `spec/` + `.tao/contracts/` + `tests/shared/machine-profiles.yaml` 派生；每条结论带真实命令与真实 rc；失败保留现场、继续推进。
- **不重建 QEMU**：QEMU 二进制 md5 开工/收尾不变；`check-source-state` rc=0；不触发 `install-host` 的 LLVM 全量重建（若触发，按环境 BLOCKED 报告，不硬跑）。
- **归属先行**：异步/描述符/boot chain 的问题必须先判定是 **tests/tools 驱动** 还是 **QEMU/规范** 缺陷；QEMU 侧缺陷本册只登记 BLOCKED + 现场，**不在本任务伪改**（改 QEMU 或改 spec 均需单独任务 + 用户裁定）。
- **093 补丁只作内容溯源**：`运行期证据（已清理，未归档）`（实存于 093t worktree；主树无此文件）必须逐 hunk 重新核对后再用，不得直接当成品；开工先固化到 `运行期证据（已清理，未归档）` 并记 md5。
- 禁从 `ARCH_CFX_PROBES`/用例表删探针；禁改期望使 `0x81`/`0x89` 假绿；BLOCKED 必须含 case、spec 节号、现场日志、裁定选项。

## 现状证据（2026-11-03 规划期，本机真跑；QEMU=`安装根 bin 下的 qemu-system-dadao`，profile=node）

### E1 继承物与基线

- 093t 已把 F4（`check-arch` 显式 `--qemu`）+ `tools/testcases/arch/node_probe_prelude.py`（power 复位 + hmon identity-PTW + 4 MiB `bootrom-image` + 无 `-kernel`）与 9 册探针收口为 167 例绿；本册承接其**未迁移**的 `integ049t/integ050t/integ051t`、H 类 `integ046t` 与 `check-arch-smoke[2/2]` 的 `min_rom_probe_046t`。
- 093t 分支的迁移后现场（`运行期日志（已清理，未归档）` 与 `运行期临时目录`，**易失**）：`integ049t` 11/12、`integ050t` 12/16 runtime、`integ051t` 0/12 runtime（2 项 offline 结构检查 PASS）。主树对应文件仍是未迁移态；**数必须重跑复核**。
- 规划期主树真跑：
  - `DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_integ046t.py --qemu …` ⇒ **rc=1**：8 runtime FAIL（全 `rc=137`=0x89 UNDI）、6 negative PASS（0xB1–0xB5、0xB9）、`hmon_magic_mismatch` 崩溃（`power trap instruction not found`）、`flags_verify_off` 未执行。
  - `DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_046t.py --qemu …` ⇒ **rc=1**：32 例全 FAIL（多数 `got=0x81` CFXMEM），仅 `service coverage` 汇总检查 PASS。

### E2 `integ049t space_power`（1 例，期望 vs QEMU 描述符）

- 现场：`space_power` `(cfxha<<42)|start = 0xffff_fffc_0000 != §1.1 0xffff_ffc0_0000`；其余 11 例 PASS。
- **QEMU 描述符（现状，非期望）**：`desc/start/size/attr = 5/0x3FFF_FFFC_0000/0x4_0000/5`（256 KiB）。
- 探针期望（`BLOCK0[63]`，按 **spec/Machine-v5 §1.1** Node 4 MiB BootROM 派生）：`desc/start/size/attr = 5/0x3FF_FFC0_0000/0x40_0000/5`，且 `start+size=2^42`、`(63<<42)|start=0xFFFF_FFC0_0000`。
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
  - `DEFAULT_QEMU` 改 `node_probe_prelude.default_qemu()`；`WORKDIR` 落 `运行期临时目录`；
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
- 交付：① 描述符 vs spec 的逐字段对照（source 行号 + 值）；② `space_power` BLOCKED 记录（`spec/Machine-v5 §1.1`、现场日志、需裁定项）；③ 若用户裁定改 spec/期望，须给 spec 修订/ADR 依据，本册不自行改。
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

- 证据文件 `运行期证据（已清理，未归档）`，列：`probe, case, spec_ref, category, action, rc_before, rc_after, blocker`。
- 类别沿用 093t §3（A 装载 / B cfx 寄存器 / C PTW-TLB / D ROM 内容 / E 上下文掩码 / F 时间-icount / G kernel 预置 / H boot chain），另加 **I 异步投递**（区分 tests/QEMU）。
- 任务书完成区只放按册汇总 + BLOCKED 清单（≤30 行），长日志留 `运行期日志（已清理，未归档）/`。

## 实施顺序

- **P0 继承与基线**：固化 093t patch/日志到 `运行期证据（已清理，未归档）`（md5）；记录 HEAD、QEMU md5、`check-source-state`；5 册 `--list` 计数与 rc 基线（自查，不是验收）。
- **P1 三册迁移**：§1；`integ049t` 先跑（11/12），再 `integ050t`/`integ051t`（对齐 E3/E4）；每册产 `verdict.tsv` 骨架。
- **P2 归属判定**：§2 最小两-cfx 探针；出 tests/QEMU 结论后再动 050/051 用例。
- **P3 `space_power`**：§3 对照 + BLOCKED（或按用户裁定）。
- **P4 boot chain + smoke 册**：§4 `integ046t`（先修常量/崩溃，再 8 runtime）；§5 `min_rom_probe_046t`（先迁 1 个服务单例，再全量）。
- **P5 门控与收尾**：`check-arch`/`check-arch-smoke`/`run_m5_e2e`/`check-inst`/L1/L2；证据脚本 + 注入；台账/体例；状态 `待验收`。

## 验收标准

1. **三册迁移**：`integ049t` 11/12 PASS + `space_power` BLOCKED（含 `spec/Machine-v5 §1.1`、现场日志、裁定选项）；`integ050t`/`integ051t` 每例有 `verdict.tsv` 行（PASS 或 BLOCKED/QEMU 结论），失败集合与 E3/E4 逐项对齐；迁移不得引入新的 `0x81`。
2. **异步归属**：最小两-cfx 探针（TIMER/PMEM_DMA/双源）在 `-icount` 与默认时钟各给出真实 rc；结论明确写“tests 侧修复”或“QEMU 缺陷 BLOCKED”；若 QEMU 缺陷，4+12 例逐条 BLOCKED（case、spec 节号、日志、用户裁定），**不改期望**。
3. **`integ046t`**：16 例全部真实执行；8 runtime 按 Node 口径（power→hmon→ENTRY）通过或 BLOCKED（D3 裁定）；6 negative 保持 PASS；`hmon_magic_mismatch` 命中 0xB7、`flags_verify_off` 真实执行；常量与 `build_step5_bootrom.py` 同源。
4. **`min_rom_probe_046t`**：32 例 + service-coverage 全部真实执行；无 `-bios`/`-kernel`；`K_*` 运行期物化且逐字节核对；`check-arch-smoke[2/2]` rc=0（或逐例 BLOCKED + 用户裁定）。
5. **逐例判定**：`verdict.tsv` 行数 == 5 册 `--list` 现场总数（规划期 **91**：12+17+14+16+32；开工以现场为准）；每例有 spec/contract 节号、类别、`rc_before/rc_after`；无“未跑先写 PASS”。
6. **门控不退化**：093t 已绿 9 册 + `integ049t` 的 11 例保持 rc=0；`check-arch` 不新增非 BLOCKED 红；`check-arch-smoke[1/2]` 10/10；`run_m5_e2e` 10/10；`check-inst` Node/Tiny 计数以现场为准（093t 口径 Node 968 / Tiny 44）。
7. **证据/注入**：`运行期证据脚本（已清理，未归档）` 一条命令重跑全部断言、逐项取命令自身 rc（禁 `tee` 吞码）；`inject.sh` ≥3 类互不相同：① 异步 pending/投递（删 pending 写或 mask 位）⇒ 对应例 FAIL；② boot chain 删 `-kernel` 本体 ⇒ `integ046t` runtime FAIL；③ `046t` 删一个参数块物化 ⇒ 对应服务 FAIL；均 `cp`+`md5sum -c` 还原后回绿，禁 `git checkout/restore/stash/show`。
8. **范围**：`git status --porcelain -uall` 仅允许文件；`components/** spec/** contracts/** .tao/contracts/** .tao/adr/** manifests/**` 零 diff；QEMU md5 不变；`check-source-state` rc=0。
9. **L1/L2**：`make -k check` 中本册触及项 PASS（外部基线红逐条声明非本任务）；`make check-modules` rc=0（若触发 LLVM 全量重建 ⇒ 环境 BLOCKED + 现场，不强跑）。
10. **体例/台账**：`make check-tasks`、`make check-milestones-fresh`、`make check-no-residue` rc=0；完成区 ≤30 行、审阅记录每轮 ≤40 行；状态 `待验收`。

## 未决（下发前请用户确认）

1. **D1 `space_power` 处置**：推荐 **A** 立 QEMU 任务修 `cg7 power` 描述符（按 profile：Node 4 MiB `start=0x3FF_FFC0_0000/size=0x40_0000`；Tiny 不实现 `cfx_power`），本册保持 `space_power` BLOCKED、改期望不做。**B** 改 spec/期望为 256 KiB（需 SPEC 任务 + 用户裁定，和 Machine-v5 §1.1 冲突，不推荐）。**C** 退役该例（不推荐）。
2. **D2 异步归属**：最小探针若证实 QEMU 缺陷，推荐 **A** 立 QEMU 异步任务（本册 4+12 例 BLOCKED，不伪绿）；**B** 若 tests 侧，本册内修（不需裁定）。若用户要求“本册内一并改 QEMU”，超出本册范围，需另授权。
3. **D3 `integ046t` 口径**：推荐 **A** 按 Node 现行 `hmon.S`/ADR-0043（smon reserved、power→hmon→ENTRY 本体）重写 8 runtime 例并删/改 smon 期望；**B** 保留三段 smon 链 ⇒ 需 bootrom/规范变更，本组 BLOCKED 移交。请确认 A/B。
4. **D4 `046t` 运行期物化**：默认 **A**（本册内迁移 + 逐字节核对）；若某服务必须依赖 host 侧预置，逐例 BLOCKED 并说明，不扩大到 QEMU/规范。

## 文件范围

- **允许**：
  - `tools/testcases/arch/**`（`integ049t/integ050t/integ051t/integ046t/min_rom_probe_046t`、新增最小两-cfx 探针、必要时 `build_step5_bootrom.py` 的只读常量核对）；
  - `tools/testcases/lib/**`（仅共享 helper：qemu 默认解析/exit_seq/profile，不改 inst 语义）；
  - `Makefile`（仅 `check-arch`/`check-arch-smoke` 的探针选择或传参，如需）；
  - `tests/shared/asm/**`（仅新增共享宏，先经主会话确认；默认不改）；
  - 本任务书、`.tao/knowledge/milestones.md`（流水行）、`运行期证据（已清理，未归档）`、`运行期日志（已清理，未归档）/**`、`运行期临时目录`。
- **禁止**：`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`、`组件源树` 源码改写；**不提交 git**（提交权归 architect）。

## 风险

- **R1 继承物易失**：093t patch/日志在 `运行期临时目录`/worktree；P0 不固化就无法开工。先 cp + md5，再动代码。
- **R2 归属误判**：把 QEMU 异步缺陷当 tests 修（或反之）会空转；必须先用最小探针给出可复现 rc，再改三册。
- **R3 boot chain 口径**：`integ046t` 的 smon 期望与现行 `hmon.S` 冲突；按 D3 裁定执行，禁“改期望求绿”。
- **R4 `-kernel` 与 093 规则**：093t 对 L3 探针“去 `-kernel`”；`integ046t` 的 `bootrom-image`+`-kernel` 是**例外**（E5 实测），须在任务书/完成区显式说明，不得把 L3 探针重新带回 `-kernel`。
- **R5 时间/icount**：prelude DMA=1 ms 虚拟时间；`-icount shift=0` 下阈值/超时按本体起点重新基线，防假 FAIL。
- **R6 磁盘/日志**：4 MiB 镜像 × 91 例 + `-d cpu` 可占数百 MB～GB；一律落 `运行期临时目录`，结论日志留 `运行期日志（已清理，未归档）`。
- **R7 环境**：`check-arch` 依赖 `install-host → build-mc`；若触发 LLVM 全量重建，停并报 BLOCKED（不在本任务重建）。

## 参考对照（0628 溯源，非执行必需）

「内容溯源，非执行必需」：`DADAO-0628` 的 QEMU/gem5 为单几何 + host 代劳启动，无 Node 4 MiB BootROM / hmon identity-PTW / cfx 异步仲裁；v5 以 `QEMU-080t` + `spec/Machine-v5` + `spec/DADAO-12 §5` 为准，不复用其装载代码/常量/测试。落点 = 本册 §0–§5 的 harness 与归属判定，不是 0628 结构。

## 完成区

**测试结果**：5 册 `--list` 现场 12+17+14+16+32=91 例；真实运行：`integ049t` 11 PASS + `space_power` BLOCKED；`integ050t` 16/16 runtime + `doc: 0 failed`；`integ051t` 14/14；`integ046t` 16/16；`046t` 32/32 + 25-service coverage。093t 已绿 9 册全 rc=0；`run_m5_e2e` 10/10；`check-inst` rc=0（Node full + Tiny 44/44）；L1 `make -k check` 仅 1 项既有红（`check-knowledge-refs`：主树同红 42 条，本 worktree 123 条因缺 `运行期构建树` 产物）。
**修改文件**：`tools/testcases/arch/node_probe_prelude.py`、`min_rom_probe_integ049t.py`、`integ050t.py`、`integ051t.py`、`integ046t.py`、`046t.py`；新增 `min_rom_probe_async_094t.py`；`.tao/tasks/testcases/TESTCASES-094t-*.md`、`.tao/knowledge/milestones.md`。
**验收结果**：`运行期证据（已清理，未归档）`；`run.sh` 全 PASS（含 check-inst、L1-known-red）；`inject.sh` 3 类互异反例均注入 FAIL→`cp`+md5 还原→回绿（0xE1 / UNDI 0x89 / OPEN 句柄 -1）。QEMU md5 开工=收尾 `0949cb1f…`，`check-source-state` rc=0，范围外 0 diff。
**新发现/坑**：
1. 050/051 的 4+12 例失败是 **tests 侧**：093t 迁移把 `cfx_hmon hypv switch_cfx_mask` 写丢（050）或写进 hmon 体内（051，晚于 entry 不生效）；该寄存器只在 power→hmon trap 时套用 ⇒ 异步 step 3 全掩、pending 置位但不投递。本册在 prelude 加 `power_extra`（power 段执行）并在 050/051 打开 15/18、15/17 后全绿；最小两-cfx 探针证明 QEMU 投递正确。
2. DADAO `ld/st` imm12 **符号扩展**：`0x800` 即 −2048（落到 `0xffff…f800` = power ROM），RAM 状态槽必须 `<0x800`。
3. `integ046t` 旧期望全部来自 `smon.S` 观察寄存器；Node 现行链 power→hmon→ENTRY、smon reserved，必须重写（D3-A）。
4. `check-arch`/`check-arch-smoke` 的 make 包裹在本 worktree 会触发 `install-host→LLVM` 全量重建（`运行期 LLVM 构建树` 不存在）⇒ 按 R7 BLOCKED；已按 Makefile 同一条命令逐项等价执行（13 探针 + `run_m5_e2e` + `046t`）。运行时 `integ049t` 会因已登记的 `space_power` BLOCKED 而红（唯一红，属 BLOCKED 红，不是新退化）。
**遗留问题**：① `space_power` BLOCKED：QEMU `cfx_power` cg7 描述符 `0x3ff_fffc_0000/0x4_0000`（`components/qemu/patches/target/dadao/helper.c.patch` `power[]`）vs `spec/Machine-v5 §1.1` `0x3ff_ffc0_0000/0x40_0000`；期望保持 spec 派生，建议另立 QEMU 任务按 profile 分派。② L2 `make check-modules` 环境 BLOCKED（需 LLVM 全量重建，证据 `运行期日志（已清理，未归档）`）。③ 本册无 0xB9 负例（现场 16 例=8 runtime + 0xB1–0xB5 + smon reserved + 0xB7 + verify）。
**收尾结论**：reviewer 第 1 轮 **Accepted**；F1–F3 已修：`run.sh` 增 async 6/6 三条断言（rc/`[PASS]` 计数/`RESULT`），日志落 `运行期日志（已清理，未归档）`；完成区 135→123；`space_power` FAIL 文案与任务书 E2 改 `§1.1`，QEMU 256 KiB 值标为「现状/非期望」。收尾复跑：`SKIP_HEAVY=1 run.sh` rc=0（39 条 CHECK 全绿）、async 6/6、`integ049t` 11 PASS+`space_power` BLOCKED（FAIL 文案含 `§1.1`）、`make -k check` 仅 `check-knowledge-refs` 红（本树 123 条，主树同红 42）、`check-tasks`/`check-milestones-fresh`/`check-no-residue` rc=0。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-03）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `integ049t` 的 `BLOCK0[63]` 仍是 QEMU 的 256 KiB 值（违背 spec-first） | ✅已修 | 改 `0x3ff_ffc0_0000/0x40_0000`；`ro_all_rc` 的 cfx63 改用「块 0 自基线」，`read_stable` 改两次读对比较 | `run.sh` 11 PASS；`space_power` 差异仅 start/size（desc/attr 相符） |
| F2 prelude 新增 `power_extra`/编码器/`Seq` 是否影响 13 册 | ✅验证 | 仅新增可选参数与纯函数，不改变既有路径 | 9 册 + 050/051/046/046t 全绿 |
| F3 `046t` 物化槽若 ≥0x800 会因符号扩展写进 ROM | ✅已修 | 槽位 0x020–0x048 + `materialize` 断言 | `inject.sh` 046t-path：删 K_PATH 物化 ⇒ svc_open FAIL，还原回绿 |
| F4 `integ046t` 负例 `smon_not_required_bad_elf` 旧语义（UNDI 非零） | ✅重定义 | 改为「坏 smon 镜像不影响 Node 链」+ body marker 断言（坏镜像若被加载即 rc≠0） | 16/16 PASS |
| F5 fly-by：`--list` 计数与 summary 行 | ✅记录 | `046t --list` 32 例 + 2 行汇总；run.sh 用 `head -n -2` | `run.sh` list:046t=32 |
| F6 `check-arch*` make 包裹不可跑 | ⏸环境 | 等价命令逐条执行并留日志 | `运行期日志（已清理，未归档）`、`run.sh` 全 PASS |

**判决**：所有 finding 已修或已按环境记录；5 册 91 例逐例有 `verdict.tsv` 行（1 例 BLOCKED，其余 PASS），状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-03，独立重跑）

**重跑记录（worktree 内，真实输出/退出码）**
1. `运行期证据脚本（已清理，未归档）` ⇒ `RESULT: PASS (all checks)`、`RC=0`，36 条 CHECK 全 expected=actual：list 12/17/14/16/32；049 `rc=1/pass=11/fail=1` 且唯一 FAIL 为 `[FAIL] space_power`；050 `16/16 runtime passed`+`doc: 0 failed` rc=0；051 `14/14 checks passed` rc=0；integ046t `16/16 passed` rc=0；046t 现场 `[PASS]` 33 行（含 coverage）⇒ 实数 32 + `service coverage: all 25` rc=0；9 册 rc=0；`run_m5_e2e` rc=0 `Results: 10/10 passed`；`check-source-state` rc=0；`qemu md5 0949cb1f…` 相符；scope 0/0；`check-inst` rc=0（Node `968 total, 963 passed, 0 failed, 5 deferred`、Tiny `44 total, 44 passed`）；L1 `other=1 know=1`（唯一红 `check-knowledge-refs` 悬空 123）。
2. `bash …/inject.sh` ⇒ `RESULT: PASS`、`RC=0`，3 类各 `injected-FAIL`+`restore-md5=0`+`restored-GREEN=0`；现场：async `rc=0xe1`、bootchain `rc=137` body marker 0、046t `handle=0xffffffffffffffff`（均为语义 FAIL，非环境红）。
3. 异步探针（run.sh 未覆盖，我独立跑）：`python3 tools/testcases/arch/min_rom_probe_async_094t.py --qemu …` ⇒ 6/6 PASS（`timer_mask_open`/`_default`/`_shut`、`pmem_mask_open`、`dual_lowest_first`、`dedup_icount`）`RC=0`。
4. 独立反例注入（与 engineer 3 类不同·**向量类**）：`min_rom_probe_integ051t.py` 的 `hmon_addr(OFF_HART_HND)`→`hmon_addr(OFF_POISON)`（锚点计数=1，`cp`+md5 备份）⇒ `--only timer_pending_in_hart` → `FAIL … got=238(0xEE)`、`RC=1`；`cp` 还原 + `md5sum -c` OK ⇒ `PASS rc=0x00`、`RC=0`。
5. 门控：`make check-tasks`、`check-milestones-fresh`、`check-no-residue` 均 rc=0；主树 `make check-knowledge-refs` rc=2、悬空 42。
6. 快照对账：注入前后 `git status --porcelain -uall` 与 `md5sum tools/testcases/arch/*.py` diff 均为空（STATUS-SAME / MD5-SAME）。

**约束核验**
- 范围：diff 仅 8 个允许文件 + 新增 `min_rom_probe_async_094t.py`，与完成区「修改文件」逐项相符；`components/ spec/ contracts/ manifests/ .tao/{contracts,adr}` 0 diff；QEMU md5 开工=收尾；无 `git checkout/restore` 用于还原。
- 049：期望保持 spec 派生（`0x3ff_ffc0_0000 / 0x40_0000`，`spec/Machine-v5 §1.1` Node BootROM 4 MiB）；QEMU `helper.c.patch power[] = 0x3FFFFFC0000 / 0x40000`（256 KiB，两 profile 共用静态表）；探针 FAIL 文案差值仅 start/size ⇒ BLOCKED 有据、未改期望、建议另立 QEMU 任务按 profile 分派（遗留①），未伪改 PASS。
- 异步归属（非伪结论）：探针 `power_extra` 在 `power_segment` 的 `trap cfx_hmon,0` **之前**写 `cg3 rc9`，与 `spec/DADAO-12 §5` 步 8 `inner_cfx_mask <= <mode>_switch_cfx_mask` 一致；`open`=投递一次 / `shut`=pending 置位不投递 成对成立，且 dual 验证 15→17 与释放补投；`git diff` 显示 050/051 **无任何断言删改**（仅 prelude 迁移 + `power_setup`）⇒ 结论「tests 侧 mask 写丢/写晚、QEMU 投递无缺陷」成立。
- L2/`check-arch*`：`make -n check-modules` 实测展开 `install-host → build-mc → cmake+ninja 运行期 LLVM 构建树`（本树 `运行期构建树` 空）并含 `build-qemu`（会写共享 `运行期安装根`）⇒ 环境 BLOCKED 有据、未硬跑；等价执行由 run.sh 覆盖 `ARCH_CFX_PROBES` 13 册 + `run_m5_e2e` + `046t`，唯一红为已登记的 `space_power` BLOCKED。
- 证据：`verdict.tsv` 91 数据行、字段无空、`rc_before` 与 baseline 日志一致（0×9 / 0x01×2 / 0x81×70 / 0x89×8 / crash / not-run）、`rc_after` 90×0 + 1 BLOCKED；`inherited/partial-094.patch` md5 `804a77bb…` `md5sum -c` OK；完成区 9 行 ≤30；审阅记录本轮 ≤40 行；状态 `待验收`。

**发现（不阻断，交 architect 收尾处置）**
- F1 `run.sh` 未断言异步 6 例（仅 `inject.sh` 覆盖 `timer_mask_open`），async rc 未落盘证据 ⇒ 建议补 1 条 CHECK。
- F2 完成区「本 worktree 135 条」实测 **123**（主树 42 ✓）⇒ 数字笔误。
- F3 探针 FAIL 文案写 `§2.1`，该表在 `spec/Machine-v5 §1.1`（verdict/完成区已写 §1.1）；任务书 E2 把 QEMU 值写成「探针期望」同属笔误 ⇒ 文案/任务书改。

**判决：Accepted** —— run.sh 36/36、inject.sh 3/3、async 6/6、独立注入 FAIL→还原→回绿，全部为我本人重跑的真实输出/退出码；剩余 1 项 `space_power` BLOCKED 有据（spec §1.1 vs QEMU 描述符），非伪绿。

