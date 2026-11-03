# TESTCASES-093t: L3 探针装载模型与 check-arch 收口（F4 + identity-PTW prelude + 逐例判定）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-092t`（P0–P5 已验证；本册承接其 P6）、`QEMU-080t`（Node 几何/hmon/PTW）、`SPEC-183t`（`spec/Machine-v5` 真源）、`QEMU-079t`（Tiny，仅作不回归对照）
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根；任务分支 `TESTCASES-093t`；`.dadao/`、`.work/` 已就绪，不重建 QEMU/LLVM，不 merge、不 push）

## 用户已定口径（继承 092t，自包含）

- 只修**测试资产/harness/门控**：允许改 `tools/testcases/**`、`Makefile`；必要时 `tests/shared/asm/**`（仅新增共享宏时）；**禁改** `components/**`（QEMU/gem5）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`。
- **不得伪造**：期望值只从 `spec/` + `.tao/contracts/` + `tests/shared/machine-profiles.yaml` 派生；每条结论带真实命令与真实 rc；失败保留现场、继续推进。
- **不重建 QEMU**：QEMU 二进制 md5 开工/收尾不变；`check-source-state` rc=0；不触发 `install-host` 的 LLVM 全量重建（若触发，按环境 BLOCKED 报告，不硬跑）。
- 092t §5/§6 与「验收标准 6」原文仍是本册接口规范；092t 完成区引用的 `.work/log/testcases/TESTCASES-092t-P6-assessment.md` **在 master 不存在**（已核 `git log --all` / `git ls-files`），本册以 092t §5/§6 + 现场基线重建，不凭该文档的转述。

## 现状证据（2026-11-03 规划期，本机真跑；QEMU = `.dadao/cross-toolchain/bin/qemu-system-dadao`，profile=node）

### E1 `check-arch` 的 F4（pre-existing）

- `Makefile:1535` 探针循环**不传 `--qemu`**；13 个探针的 `DEFAULT_QEMU` 是 `.work/build/qemu/qemu-system-dadao`（`Makefile:1385` 的安装根是 `.dadao/cross-toolchain/bin`）。任务 worktree 无 `.work/build/qemu` ⇒ 13 探针一律 rc≠0（092t F4）。
- 现场：`.work/build/qemu/qemu-system-dadao` 存在但早于安装根（02:52 vs 09:52），默认可解析到**旧二进制**；因此只改 Makefile 传参还不够，驱动默认值也要按安装根解析。

### E2 13 探针基线（显式 `--qemu` 实跑；例数按 `--list` 现场派生，不写死）

合计 **227 例**（现场 `--list` 求和：13+14+9+37+34+25+6+16+7+23+12+17+14）。

- `044t` 13 例 **0 PASS**：全 `got=0x81`（CFXMEM），首条 RAM 写即退出。
- `045t` 14 例 **0 PASS**：同上。
- `049t` 9 例 **4 PASS**：`ram_rw`/`ram_top`/`ram_exec` + `oob_data_unmapped`/`oob_fetch_unmapped` 失败（0x81）。
- `integ039t` 37 例 **1 PASS**：页表建在 PA 0（`PT_L1_PA = RAM_BASE`），PTW off 写表即 CFXMEM。
- `integ040t` 34 例 **1 PASS**：同 039t（TLB/A-D 面）。
- `integ042t` 25 例 **3 PASS**：PMEM/DMA 面；CPU 侧 RAM 访问失败。
- `integ044t` 6 例 **0 PASS**：权限掩码面，仍先死在 RAM 访问。
- `integ046t` 16 例 **7 PASS / 8 FAIL / 1 崩溃**：`chain_basic`…`no_resume_poison` 全 rc=137(0x89)；`hmon_magic_mismatch` 在 `patch_trap_magic` 抛 `power trap instruction not found`（boot 布局常量已陈旧）。
- `integ047t` 7 例 **0/6 runtime PASS**（17 项 checks）：SBI DMA + `-icount`。
- `integ048t` 23 例 **22 PASS / 1 FAIL**：权限/deleg 面；`open_power_bootrom` 读 ROM 内容随装载模型变化。
- `integ049t` 12 例 **0 PASS**：cg7 空间描述，仍先死在 RAM。
- `integ050t` 17 例 **0/16 runtime PASS**（25 项 checks）：cfx_time/hart + `-icount`。
- `integ051t` 14 例 **2/14 checks PASS**：异步仲裁 + `-icount`。
- 关联项 `min_rom_probe_046t`（16 例，**在 `check-arch-smoke` [2/2]**，不在 13 清单）**当前红**：25 服务多数 `got=0x81`；其 `K_SVC/K_BUF/K_PATH` 参数块靠 `-kernel` 预置（即「kernel 预置表」）。

### E3 装载模型的四条硬约束（实测，决定方案）

1. **QEMU 拒绝 `-bios` 不带 `-kernel`**：`dadao-m1: -kernel test.bin is required`（rc=1，`dadao-machine.c` 路径 B）。⇒「去 `-kernel`」只能走 **路径 C**：`-machine dadao-m1,bootrom-image=<4 MiB>`（`-kernel` 可省；文件必须恰好 `rom_size`=4 MiB）。
2. **路径 C 可用**：4 MiB 镜像、探针码放 `reset_pc - bootrom_base = 0x3F_0000` 处，无 `-kernel` 跑同一条探针得同样 rc=0x81（= 原装载下的同一故障点），semihosting/`-d cpu` 正常。
3. **原 raw `-kernel` 的 16 B 是另一条独立缺陷**：Tiny `kernel_reserved=0x100`，16 B 镜像撞保留前缀；Node 虽 `kernel_reserved=0`，但「去 `-kernel`」后 raw 前缀/入口问题整体消失（路径 C 无 raw 装载）。本册不引入 raw 镜像。
4. **power 不能驱动 PMEM/PTW**（ADR-0045 D4 默认 mask）：同一指令序列
   - power（cfx63/hypv）：`cfx2rd cfx_pmem` / `st.o PMEM_BASE` / `cfx2rd cfx0` ⇒ **rc=0x81**（被拒）；
   - hmon（cfx3/hypv）：同序列 ⇒ **rc=0x00**。
   ⇒ prelude 的 PMEM/PTW 段**只能在 hmon 执行**；本体也必须在 hmon（多例需以 hmon 身份读写 cfx0/1/2/63 的寄存器/向量）。

### E4 规划期 spike（已在本机跑通，供实现复用）

在 `-machine bootrom-image` 的 4 MiB 镜像上，按「power 复位段（装 cfx3 hypv 向量 + `trap cfx3`）→ hmon 段（4 个超页 PTE 写 PMEM → `cfx_pmem` DMA 到 PA → poll BUSY → 清 PMEM staging → TLB invalidate → PTBR → `ptw_enable=1`）→ `jump` 到 `RESET_PC+0x1000` 本体」实跑：`PTBR=0x7FF0_0000`、`PTW_ENABLE=1`，本体 RAM store/load 成功，semihosting 退出码 = 期望值。
同时确认两条编码语义（易踩）：`br.nz` 的 `imms18` 与 `jump` 的 `imms24` 均以**指令字**为单位（`Addr = PC + (imm << 2)`），`br.nz` 基址 `rb0` = 该分支指令自身 PC；PTE 模板与 `hmon.S` 逐位一致：`0xF000_0000_0000_FFEF | (i << 29)`（i=0..3）。

## 目标

1. **F4 收口**：`check-arch` 的探针循环显式传 `--qemu $(QEMU_BIN)`；探针/驱动默认 QEMU 按安装根解析，直接运行也命中 `.dadao/cross-toolchain/bin`。
2. **统一装载模型**：一份共享 prelude（power 复位 + hmon identity-PTW + 4 MiB `bootrom-image` + 无 `-kernel`）；13 探针 + `min_rom_probe_046t` 共用，禁各写一份。
3. **逐例判定**：227 + 16 例逐条落 `verdict.tsv`（case/spec 节号/类别/改法/前后 rc）；不可成立者显式 `BLOCKED`（case + spec 引用 + 现场日志 + 需裁定项）。
4. **`check-arch` 13 探针真实跑绿**（或按用户裁定后的清单）；`check-arch-smoke`（含 046t 25 服务）与 `run_m5_e2e` 10/10、`check-inst`（Node 968 + Tiny 44）不退化。
5. 证据脚本 + ≥3 类互不相同的反例注入；L1/L2；台账/体例；状态 `待验收`。

## 接口规范

### 0. 上下文与装载（本册定义，含 E3 实测依据）

- 探针 ROM 即 bootrom：复位在 **power（cfx63/hypv）**；偏移 0 的 prelude 先装 `cfx_hmon.hypv.excp_vector = RESET_PC + H_OFF` 并 `trap cfx_hmon, 0`，进入 **hmon（cfx3/hypv）** 执行 PMEM/PTW 段；本体从 `RESET_PC + 0x1000` 起、在 **hmon** 执行。
- 「power 上下文」= **复位起于 power、prelude 的 power 段只在 power 做上面一件事件**；本体在 power **不可行**（E3：cfx_pmem/cfx_ptw/cfx0 访问被默认 mask 拒）。此解释与 092t §未决 5 的字面措辞不同，见 §未决 D1。
- 该模型与现有探针的 `bootstrap_prefix()/bootstrap_stage()` 语义一致（后者保留其清 power mask 的步骤，并入 prelude；**不保留**各自的 `-bios`/`-kernel` 装载代码）。

### 1. F4：QEMU 路径（先做，否则后续全红）

- `Makefile` `_locked-check-arch` 循环：`DADAO_TEST_PROFILE=node $(PYTHON) …/min_rom_probe_$$p.py --qemu $(QEMU_BIN) …`；`$(QEMU_BIN)` = 安装根。
- 驱动默认值：所有本册触及探针的 `DEFAULT_QEMU` 改为 `tools/infra/paths.py::host_toolchain_bin()/qemu-system-dadao`（`--qemu` 仍可覆盖）；共享 prelude 暴露 `default_qemu()` 一份实现。
- 断言：`make -n check-arch | grep -- '--qemu'` 每册一行；在无 `.work/build/qemu` 的目录运行 `--list`/单例不报 QEMU 缺失；证据落 `.work/evidence/TESTCASES-093t/f4/`。

### 2. 共享 prelude 契约（新 `tools/testcases/arch/node_probe_prelude.py`，一份实现）

输入：`profile`（node）、`prog_words`、`handlers`（相对本体基址的偏移）、`body_off=0x1000`、`pt_pa=0x7FF0_0000`、`pmem_stage=PMEM_BASE+0x1000`。

- **power 段**（ROM 偏移 0）：`cfx2rc cfx_hmon cg3 rc10 = RESET_PC+H_OFF`；`trap cfx_hmon, 0`。
- **hmon 段**（H_OFF，建议 `0x200`）：
  1. 清 `cfx_power` 的 cg0–cg3 `cfxmem/cfxexe`（= 旧 `bootstrap_stage`，逐字保留写入值 0）；
  2. 4 个 PTE 写 PMEM staging，`PTE_i = 0xF000_0000_0000_FFEF | (i<<29)`（`HSJU=0xF/SPF=0xFF/flags=0xEF`，与 `hmon.S` 逐位一致）；
  3. `cfx_pmem cg15 rc0..rc3`（src=PMEM staging、dst=pt_pa、size=32、START/DIR=0）；轮询 rc4 bit0 BUSY；**ERROR 或未 DONE ⇒ 退出码 0xE0**（现场日志 + 明确失败，不静默续跑）；
  4. 清 PMEM staging 32 B（恢复全零，避免污染 `integ042t` 的 SRAM/DMA 断言）；`cfx_pmem cg15 rc4` 写 `0x2`（DONE W1C）；
  5. `cfx_ptw cg12 rc0 = 2`（TLB invalidate）、`cg9 rc0 = pt_pa`（PTBR）、`cg8 rc8 = 1`（ptw_enable）；
  6. `jump` 到 `RESET_PC + body_off`（`imms24` 以字为单位）。
- **本体**：`ROM_BASE = RESET_PC + 0x1000`；原有 `H = ROM_BASE+0x100` 等标签随之平移；`build_rom` 上限从 `0x400` 放宽到「0x1000 + 本体大小」。
- **装载**：4 MiB `bytearray`，`image[reset_pc-rom_base : …] = prelude+body`（Node 偏移 `0x3F_0000`）；`-machine dadao-m1,bootrom-image=<img>` + `-semihosting-config enable=on,target=native` + `-d cpu -D <log>`；**无 `-kernel`**；仍每例独立进程。
- **exit_seq**：用 profile 的 `EXIT_BLOCK`（`EXIT_W0/W1/W2`）组参数块，不再写死 `0x00FF_F000`（Tiny 窗口修正；Node 也回到配置的 `0x7FFD_0000`）。
- **PT 区选择**：`pt_pa = 0x7FF0_0000`（64 KiB 对齐、RAM 内、低于 `fault_record=0x7FFC_0000`/`exit_block`/`dump_base`）。**不取 0**：`integ039t` 的 L1 表就在 `RAM_BASE+0`，PTBR=0 会在建表过程中覆盖 prelude 的表。

### 3. 逐例判定（强制）

- 证据文件 `.work/evidence/TESTCASES-093t/verdict.tsv`，列：`probe, case, spec_ref, category, action, rc_before, rc_after, blocker`。任务书只放按探针汇总 + BLOCKED 清单（≤30 行完成区）。
- 类别（每例必须归类）：
  - **A 纯装载**：只依赖 RAM 读写/取指；prelude 后原期望不变（多数）。
  - **B cfx 寄存器/向量（本体 hmon）**：prelude 后原期望不变；复核 `MODE/CFXCODE/PREVM` 是否仍为 hmon。
  - **C PTW/PTBR/TLB 自管**：切 PTBR 前必须 `TLB invalidate`（spec 只说 PTBR 写不刷新 TLB，见 `integ040t tlb_ptbr_write_no_flush`）；PT 区不得与 `pt_pa` 冲突；`ptw_enable=0` 例要显式关并恢复。
  - **D ROM 内容/绝对标签**：`ROM_BASE+0x1000` 平移后重导 `cip`/ROM 读值；依赖 ROM 字节内容的 case 逐条核对（`integ048t`）。
  - **E 上下文/掩码**：以本体 hmon 复核 `init_masks`/`deleg`/`prevm` 期望；不得把 power 的默认值当 hmon 的。
  - **F 时间/icount**：prelude DMA 引入 1 ms 虚拟时间；以本体开始计时为基线，核实 `-icount` 例的阈值/超时。
  - **G kernel 预置数据**（`min_rom_probe_046t`）：参数块/路径串改为**运行期物化**（PTW 后用 `st.o` 写 RAM，或 ROM 内嵌 + 拷贝）；删 `-kernel` 后不得有隐藏依赖。
  - **H boot chain**（`integ046t`）：不套 prelude；独立按 `power.S`/`build_step5_bootrom.py` 的 4 MiB 布局修常量与 `patch_trap_magic`。
- `BLOCKED` 必含：case 名、spec 节号、现场日志路径、原因、需用户裁定的选项（改期望/退役/移交）。**禁**静默跳过、禁从 `ARCH_CFX_PROBES` 删探针、禁改期望使 0x81 假绿。

### 4. `integ046t`（boot chain，独立处理）

- 保持 `-machine bootrom-image=<真实 bootrom_step5.bin>`（已无 `-kernel`）；仅修：
  - `POWER_OFF/H_ENTRY/S_ENTRY/WIN` 与 `build_step5_bootrom.py` 同源（power 在 image 偏移 `bootrom_size-0x10000`，即 `0x3F0000`；表在 image 偏移 0）；
  - `patch_trap_magic` 在 power 窗口按新布局找 `trap cfx_hmon, <magic>`；
  - `chain_basic` 等的 rc=137 逐例定位（先查 `-d cpu` 最后 PC 与 stage 标记），**不得**改期望掩盖。
- 若根因落在 bootrom/规范（非测试资产）⇒ 该例 `BLOCKED` + 用户裁定，不移交 QEMU 改动。

### 5. ISS-341 / ISS-342 处置（显式，不扩范围）

- **ISS-341**（`0x80|bit` vs CFXREG=0x84）：13 探针的通过判据用 semihosting 退出码与 `-d cpu` cause，不依赖该公式 ⇒ **不纳入**，保持 open，移交 SPEC/QEMU。
- **ISS-342**（cfx 组合 CFXREG 打到被访问 cfx ⇒ 自环）：探针侧已用本地向量规避（`044t cfxreg_badcombo` 设 cfx0 向量、`045t cfxreg_*` 设 cfx0 向量）；本册只需在逐例判定中复核这些向量仍在 hmon 下可写。boot chain 的 `cfx_umon.vector=ENTRY` 自环属 `integ046t` 的 boot 模型，若命中则 BLOCKED 移交，**不改 QEMU**。

## 实施清单（按序）

- **P0 基线冻结**：`git rev-parse HEAD`、QEMU md5、`check-source-state`；13+1 探针逐册 rc/失败清单落 `.work/evidence/TESTCASES-093t/baseline/`（自查，不是验收）。
- **P1 F4 + 共享 prelude**：§1/§2；先用 `044t run_mode_0` 单例跑通（RAM 把 `0xCAFE` 写读回 + 退出码正确），再跑 `044t` 全量。
- **P2 机械迁移**：13+1 驱动的 `ROM_BASE/ROM 上限/run()/exit_seq/bootstrap` 换成共享实现；逐册跑一遍生成 `verdict.tsv` 骨架（每例先归类，未通过不写 PASS）。
- **P3 批次 1（非 PTW 重）**：`044t 045t 049t integ042t integ044t integ048t integ049t` + `min_rom_probe_046t`（G 类物化）。
- **P4 批次 2（PTW/TLB）**：`integ039t integ040t`（C 类：PTBR/TLB/PT 区冲突）。
- **P5 批次 3（时间/中断/boot）**：`integ047t integ050t integ051t integ046t`（F/H 类）。
- **P6 门控与收尾**：`check-arch`、`check-arch-smoke`、`run_m5_e2e`、`check-inst`、L1/L2；证据脚本 + 注入；台账/体例；状态 `待验收`。

**拆分手册（预算不足时，须主会话执行）**：先收口 **13 个 `ARCH_CFX_PROBES`**（P1–P4 + P5 的 integ046t/047/050/051 视预算），把 `min_rom_probe_046t`（smoke [2/2]）与未完成的逐例判定原样拆 `TESTCASES-094t`；`check-arch` 保持红并如实披露，`check-arch-smoke` 的 [2/2] 红作为 094t 阻断前置。**任一路径**：探针清单/verdict 行逐项移交、不得删探针、不得把未跑绿写成 PASS。

## 验收标准

1. **F4**：`make -n check-arch` 每册含 `--qemu $(QEMU_BIN)`；无 `.work/build/qemu` 时直接跑单例仍解析到 `.dadao/…`；证据含 `DEFAULT_QEMU` 打印与 md5。
2. **`make check-arch` rc=0**：13 册逐个 rc=0，日志 `.work/log/arch/check-arch-probe-<id>.log`；每册通过例数 == `--list` 现场派生（`skipped` 不适用本门控）；BLOCKED 例必须附用户裁定原文 + spec 节号 + 现场日志，否则本项不成立。
3. **`make check-arch-smoke` rc=0**：[1/2] 10/10 + [2/2] `min_rom_probe_046t` 25 服务；若 046t 拆 094t，则 [1/2] 必绿且完成区如实披露 [2/2] 红与 094t 阻断前置。
4. **`run_m5_e2e` rc=0**（10/10，resume bootrom；`--qemu`=安装根）。
5. **`make check-inst` rc=0 且不退化**：Node `968 = 963 passed / 5 deferred / skipped_profile=44`；Tiny `44 = 44 passed / skipped_profile=968`（口径以现场为准）。
6. **逐例判定**：`verdict.tsv` 行数 == 13+1 册 `--list` 现场总数；每例有类别与 spec 引用；无「未归类/未跑先写 PASS」。
7. **证据/注入**：`.work/evidence/TESTCASES-093t/run.sh` 一条命令重跑全部断言、逐项取命令自身 rc（禁 `tee` 吞码）；`inject.sh` ≥3 类互不相同，均「注入→FAIL→`cp`+`md5sum -c` 还原→回绿」，禁 `git checkout/restore/stash/show`：
   (a) prelude 的 `ptw_enable=1` 改 0（或删一个 PTE）⇒ 对应 RAM 例 FAIL；
   (b) 把 `ROM_BASE` 回退到 `RESET_PC`（不偏移 0x1000）⇒ 至少一册 FAIL；
   (c) 046t 删掉一个运行期参数块物化 ⇒ 对应服务例 FAIL；
   (d) F4 回退（去掉 `--qemu`）⇒ 在无 `.work/build/qemu` 的目录 check-arch/单例 FAIL。
8. **L1/L2**：`make -k check` 中本册触及项全 PASS；外部基线红（如 `check-knowledge-refs` 历史悬空、`check-lit` 的 mcmodel）逐条给主树证据并声明非本任务；`make check-modules` rc=0（若 `install-host` 触发 LLVM 全量重建 ⇒ 环境 BLOCKED + 现场，不强跑）。
9. **范围**：`git status --porcelain -uall` 仅允许文件；`components/** spec/** contracts/** .tao/contracts/** .tao/adr/** manifests/**` 零 diff；QEMU md5 不变；`check-source-state` rc=0。
10. **体例/台账**：`make check-tasks`、`make check-milestones-fresh` rc=0；完成区 ≤30 行、审阅记录每轮 ≤40 行；状态 `待验收`；无仓库内临时文件（`check-no-residue`）。

## 未决（下发前请用户确认；否决则按下述处置）

1. **D1「power 上下文」的解释**：本册采用「power 复位 + hmon prelude/本体」（E3 实测 power 不能驱动 cfx_pmem/cfx_ptw/cfx0，rc=0x81 vs hmon rc=0x00）。若用户要求**本体在 power**：本册 **BLOCKED**（需改 QEMU mask 或 spec，超出范围）。
2. **D2 `min_rom_probe_046t` 是否纳入 093t**：默认纳入（它在 `check-arch-smoke` [2/2]，且根因同源：PTW off + kernel 预置表）；替代：拆 094t，`check-arch-smoke` [2/2] 保持红并作为 094t 阻断前置。
3. **D3 PT 区不取 PA 0**：092t §5 写 `PTBR=0`；本册改 `pt_pa=0x7FF0_0000`（`integ039t` 的 L1 表在 PA 0，PTBR=0 会在建表时覆盖 prelude 表）。若坚持 `PTBR=0`，需先给出 039t 的建表/失效方案，否则可能永久红。
4. **D4 预算拆分**：若 P0–P3 后仍超预算，按 §拆分手册执行（先 13 探针）；拆分须主会话授权并逐行移交 verdict。

## 文件范围

- **允许**：
  - `tools/testcases/arch/**`（13+1 探针、`node_probe_prelude.py`（新）、必要时 `run_m5_e2e.py` 的 qemu 默认解析）；
  - `tools/testcases/lib/**`（仅共享 helper：qemu 默认解析/exit_seq；不改 inst 语义）；
  - `Makefile`（仅 `check-arch` 循环传参、`check-arch-smoke` 如需）；
  - `tests/shared/asm/**`（仅新增共享宏，且先经主会话确认；默认不改）；
  - 本任务书、`.tao/knowledge/milestones.md`（流水行）、`.work/evidence/TESTCASES-093t/**`、`.work/log/{arch,testcases}/**`、`/tmp/opencode/TESTCASES-093t/**`。
- **禁止**：`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`、`.work/source/**` 源码改写；**不提交 git**（提交权归 architect）。

## 风险

- **R1 体量**：13+1 册 ≈243 例；按 P3/P4/P5 分批，超预算按 §拆分手册（禁跳过即绿）。
- **R2 PTBR/TLB**：prelude 先建立 identity 映射会填 TLB；自管页表的册（039t/040t）切换前必须 invalidate，且 PT 区不能冲突（D3）。
- **R3 ROM 内容**：`-bios`→`bootrom-image` 且本体偏移 0x1000，读取 ROM 字节/复位 PC 的 case 必须重导（`integ048t`）。
- **R4 046t 数据**：`K_*` 参数块从 `-kernel` 改运行期物化，必须逐字节核对（含 64-bit BE 字段、路径串、argv）。
- **R5 时间**：prelude DMA = 1 ms 虚拟时间；`-icount shift=0` 下 ~1e6 指令，注意 timeout 与计时基线。
- **R6 上下文**：本体必须在 hmon；若某例确需 power 语义 ⇒ BLOCKED + 裁定，不偷偷改上下文。
- **R7 日志/磁盘**：4 MiB 镜像 × 243 例 + `-d cpu` 可占数百 MB～GB；一律落 `/tmp/opencode/TESTCASES-093t/`，跑完汇总大小并清理，结论日志留 `.work/log/arch/`。
- **R8 环境**：`check-arch` 依赖 `check-arch-smoke → install-host`；若触发 LLVM 全量重建，停并报 BLOCKED（不在本任务重建）。

## 参考对照（0628 溯源，非执行必需）

- 「内容溯源，非执行必需」：`DADAO-0628` 的 QEMU/gem5 是单几何 + host 代劳启动，无 Node 4 MiB BootROM/hmon identity-PTW；v5 以 `QEMU-080t` + `spec/Machine-v5` 为准，不复用其装载代码/常量/测试。落点 = 本册 §0–§3 的 harness，不是 0628 结构。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：
