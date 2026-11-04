# TESTCASES-092t: Tiny/Node 执行资产收口（profile 过滤 + Node 移交模型 + arch/L3 探针）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-091t`（profile 真源/资产迁移基线）、`QEMU-079t`（Tiny 机器与 `profile=tiny`）、`QEMU-080t`（Node 机器、hmon/PTW/hypv、缺省 tiny）、`SPEC-183t`（`spec/Machine-v5` 几何/装载/cfx 真源）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库根；任务分支内实现，不 merge、不 push）

## 用户已定口径（自包含，2026-11-02/03 批次）

- 本任务只修**测试资产/harness/门控**：允许改 `tests/**`、`tools/testcases/**`、`tools/qemu/semantics_gate.py`、`Makefile` 的测试选择；**禁改** QEMU/gem5 实现、`spec/**`、`contracts/**`。
- **不得伪造**：期望值只从 `spec/` + `.tao/contracts/` + profile 表派生；每条结论带真实命令与真实 rc；失败保留现场、继续推进。
- 「不跑 QEMU 实现改造」= **不重建 QEMU**：本任务不触碰 `components/**`，`build-qemu` 只做增量 no-op；改的是 hmon/bootrom 汇编与测试驱动。
- Tiny/Node 真源：`spec/Machine-v5-测试机运行环境.md` §1/§1.1/§1.2/§2/§3/§6；测试侧几何真源 `tests/shared/machine-profiles.yaml`。
- Node 现行实现（QEMU-080t，用户裁定）：identity `[0, 2 GiB)`、`entry=0x10_0000`、`SP=0x7fff_0000`、hmon 4×512 MiB 超页 `SPF=0xFF`；`spec §6` 的 `0x0200…` 口径冲突已登记 `ISS-340`，本任务**不**改 spec、不按 spec §6 改资产。

## 现状证据（2026-11-03 规划期实测，均由本册记录者在本仓库真跑）

失败分类以 `QEMU-079t`/`QEMU-080t` 完成区为基线，本册现场复核：

1) **Node 全量 inst**（等价 `check-inst` 的 Node 段）——4 册 33 例探针：
   ```
   DADAO_TEST_PROFILE=node python3 tools/testcases/lib/run_qemu_test.py <4册> --batch \
     --qemu <安装根二进制> \
     --trampoline <trampoline 镜像> --jobs 8
   → 33 total / 12 passed / 21 failed / 0 errors
   ```
   - **19 条非 profile 失败**（= QEMU-080t 遗留①的「19 条 Node 移交模型」）：
     - `6×FAIL code 0x01`：`ctrl-call[1,2,3,7,8,9]`（期望/输入 RA 值写死 Tiny 绝对地址 `0xFFFF_FF01_0104` 等，Node 下状态比较失败）。
     - `12×UNKNOWN(0xB7)`：`ctrl-call[5]`、`ctrl-ret[0,1,2,3,4,8,9]`、`misc[2,3,4,5]`。`0xB7` = `tests/shared/bootrom/step5/hmon.S` 的 `hmon_exit_b7`（收到非 boot-magic 的 trap/cause）：Node 下测试体的同步 fault 进入 current-mode monitor `hmon`，被 hmon 的 magic 检查拒掉。
     - `1×Expected UNMAPPED, got UNDI`：`ctrl-jump[2]`（目标在 profile RAM 内，零字取指 ⇒ UNDI）。
   - 另 `2 条 profile 不适用`（`ctrl-call[10]`、`ctrl-jump[5]`）被 `build_test_binary` 抛错计 FAIL（门控无 profile 过滤）。

2) **Tiny 全量 inst 子集**（8 册 242 例，Tiny trampoline）：
   ```
   DADAO_TEST_PROFILE=tiny python3 tools/testcases/lib/run_qemu_test.py <8册> --batch \
     --qemu <安装根二进制> \
     --trampoline tools/testcases/lib/trampoline.bin --jobs 8
   → 242 total / 227 passed / 15 failed
   ```
   - **11 条真失败**：`ctrl-br[3,7,11,15,19,23,27,31,35,39]`、`ctrl-jump[2]`，全为 `Expected UNMAPPED, got UNDI`（目标 `@ENTRY-0x4000` / `@ENTRY-0x1000` 落在 Tiny 8 MiB SRAM 内，取指到全零字 ⇒ UNDI，不是 UNMAPPED）。
   - 另 **4 条** `misc[2..5]` 为 `profiles:[node]` 在 tiny 下抛错计 FAIL（同 profile 过滤缺失）。
   - `profiles:[tiny]` 共 **43 条**（1 aip-si + 10 ctrl-br + 1 ctrl-call + 1 ctrl-jump + 4 mem-ra + 4 mem-rb + 22 mem-rd），其中 32 条在 Tiny 下**已通过**（CFXMEM 类、aip-si 边界），不要改它们的期望。

3) **arch-smoke 5 红**（Node，`run_m5_e2e.py` 实跑）：
   ```
   → 5/10 passed, 5 failed
   FAIL m5_perm_reserved_illi    rc=183(0xB7) cause=ILLI
   FAIL m5_perm_mask_cfxperm     rc=183(0xB7) cause=CFXPERM
   FAIL m5_perm_unimpl_cfxreg    rc=183(0xB7) cause=CFXREG
   FAIL m5_perm_badcombo_cfxreg  qemu timeout 30s
   FAIL m5_trap_escape           qemu timeout 30s
   ```
   边界：这 5 个 `.s` 按「user 模式 + `cfx_umon` 的 user 异常向量」写；Node 测试体在 **hypv / cfx_umon**，fault 进 **hmon**（H 模式），`m5_trap_escape` 因 hmon 把 `cfx_umon.hypv.excp_vector` 设成 `ENTRY` 而**自环**。

4) **L3 探针 13 个**（Node，实跑代表）：
   ```
   DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_044t.py --qemu <qemu>
   → RESULT: FAIL（13/13 例 got=0x81 CFXMEM，含 run_mode_0..3/reset_values/cfx_rw_share/…）
   DADAO_TEST_PROFILE=node python3 tools/testcases/arch/min_rom_probe_046t.py --qemu <qemu>
   → RESULT: FAIL（25 服务例全 0x81）
   ```
   根因（两条，均已实测）：① 探针程序在 `-bios` 64 KiB 窗口（cfxha 63）执行、**PTW off**，却直接写 `RAM_BASE`（Node = PA 0）⇒ `addr[47:42]==0 && ptw_enable==0` ⇒ `CFXMEM`（`spec/Machine-v5 §1.2`）；② 探针仍用 `-kernel` 传 16 B（Node `kernel_reserved=0` 时无害，Tiny 下撞 0x100 保留前缀报错）。
   `check-arch` 的 13 探针清单（Makefile `ARCH_CFX_PROBES`）：`044t 045t 049t integ039t integ040t integ042t integ044t integ046t integ047t integ048t integ049t integ050t integ051t`。

5) **两条修法已在本机验证（只改 yaml 的临时试验，未落盘）**：
   - Tiny：`ctrl-br[3]` 编码改 `0x68060000`（`imms18=-0x8000`，目标 `@ENTRY-0x2_0000` < SRAM 基址）+ `expected_fault: CFXMEM` ⇒ 单例 **PASS（0x81）**。
   - Tiny：`ctrl-br[27]`（12 位 imm，`-0x400`）保持编码、`expected_fault: UNDI` ⇒ 单例 **PASS（0x89）**。
   - Node：把 `ctrl-call/ctrl-ret` 的 RA/MemRAS 绝对地址按 Node `entry=0x10_0000` 重写后，`ctrl-call[1,2,5]`、`ctrl-ret[0,2,4]` 全部 **PASS**；整批残差只剩 `misc[2..5]`（0xB7）与 `ctrl-jump[2]`（UNDI）。

## 目标

1. **profile 适用性单一语义**：`check-inst`/`check-inst-smoke` 在同一门控里**显式跳过**不适用于当前 profile 的 case，并报数；不适用 ≠ 失败。
2. **几何符号化**：inst 向量里所有「入口相对」的 RA/RAS 值改成 profile token（含递归计数），Tiny/Node 同一份 case 都能正确解析。
3. **Tiny 11 条 boundary 修正**：按 Tiny 8 MiB SRAM/入口/UNDI 的真实路由改期望（可出 SRAM 的改 `CFXMEM`，12 位 imm 不可达的改 `UNDI`），**不改 QEMU**。
4. **Node 移交模型**：用 hmon 的两个策略把「machine fault 退出码」与「cause 自检后恢复」分开，使 inst 的 fault 期望与 arch 的 cause 断言在 Node 上**真实可观察**；不再靠 0xB7 兜底。
5. **arch-smoke 5 条 Node 可执行**：4 个 `m5_perm_*` 读 hmon 记录的 fault cause；`m5_trap_escape` 由测试体自装 `cfx_umon.hypv` 向量。
6. **13 个 L3 探针 Node 可跑**：统一「identity PTW prelude + 无 `-kernel`」装载模型；逐例按 spec 校正期望；不可成立的 case 必须显式登记并经用户裁定，禁静默跳过/伪造。
7. 门控接线（`check-inst` 含 Tiny 子集段）、证据与反例注入齐备；状态 `待验收`。

## 接口规范

### 0. 总原则

- 期望值真源：`spec/`（尤其 `Machine-v5` §1.1/§1.2/§2/§3/§6）+ `.tao/contracts/` + `tests/shared/machine-profiles.yaml`；**不得**从 QEMU 行为反推期望值。允许用 QEMU 观察**路由**（是否 0xB7/超时/0x81）来定位资产错误，但期望值必须能引用 spec。
- 同一 case ID 只保留一份（`TESTCASES-091t §3`），profile 差异用 `profiles:`/token 表达，**禁止**拆成两册/两 ID。
- 每条改动都要能反例 FAIL（见验收 9）。

### 1. profile 适用性（门控）

- `tools/testcases/lib/run_qemu_test.py`：`run_batch`/单例路径遇到 `profiles` 不含当前 profile 的 case ⇒ **跳过并计数**（`skipped_profile`），不抛错、不计 FAIL；打印 `SKIP(profile) <file>[<i>] <id> profiles=[…]`；`total` 口径 = 实际运行数；结束时打印 `skipped_profile=N`。
- `tools/qemu/semantics_gate.py`：
  - 结构断言改为 `运行 total + skipped_profile == 现场派生用例总数`（仍 fail-closed：`total==0` ⇒ FAIL）；
  - 新增 `--only-profile-cases`：只运行「显式写了 `profiles:` 且包含当前 profile」的 case（供 Tiny 段）；
  - 不改 `KNOWN_DEFERRED` 精确名单语义。
- `tools/testcases/inst/run_qemu_smoke.py` 同步（代表集里被 profile 排除的组要有替代代表，不能出现某组 0 例却“通过”）。

### 2. `<count>:@TOKEN` 复合 token（RA/RAS 值）

- 语法：`"<count>:@TOKEN[+0x…|-0x…]"`，`count` 为十进制或 `0x…`，范围 `0..0xFFFF`；结果 = `(count << 48) | resolved_addr`，要求 `resolved_addr < 2^48`。
- 实现位置：`tools/testcases/lib/machine_profile.py::resolve()`（`validate_vectors`/`build_test_binary`/harness 共用同一函数，禁各写一份）。
- 用途（本任务）：`ra0` = `"<RACNT>:@ENTRY+0x700000"`（MRPTR）、`raN` = `"<recursive_count>:@ENTRY+0x4"`；**绝对数据地址**（如 `0xAAAA…`/`0xDDDD…`）保持普通十六进制，不做替换。
- `tests/inst/schema.md`「机器几何、token 与 `profiles`」补该语法与「仅用于带计数字段的 RA 值」的说明；validator 对非法 count/越 48 位地址报错。
- 生成器（`tools/testcases/generate_ctrl_br.py`、`generate_ctrl_jump_call_ret.py`；如涉及 `generate_mem_vectors.py` 的 tiny case 同规则）改为输出复合 token；`make check-generator-sync` 必须逐字节一致。

### 3. Node hmon 双策略（fault-exit / resume）

- `tests/shared/bootrom/step5/hmon.S` 入口分流（`cfx_hmon cg5 rc2` = cause id，`cg5 rc4 & 0x3FFFF` = magic）：
  - `cause == CFXTRAP(1<<0) && magic == 0x30001` ⇒ 现有 boot 初始化（power 移交），不变。
  - 否则（测试体同步 fault / 非法 trap）：
    - **resume 策略**：把 `cause`（以及 `excp_cause_ip`，若寄存器可取）写到 **fault-record 槽**，然后 `escape cfx_hmon, 1`（`imms18=1` ⇒ 回到 `excp_cause_ip+4`），让向量恢复执行并自检。
    - **exit 策略**：退出码 = `0x80 | bit_index(cause)`（`ADR-0004 D5.8`；ILLI=0x88、UNDI=0x89、RASOF=0x8A、RASUF=0x8B、CFXMEM=0x81、CFXPERM=0x80、CFXREG=0x84），沿用 `hmon_exit_b7` 的 semihosting 退出块；**不得**再统一写 0xB7。
  - `hmon_exit_b7` 仅保留给「boot 移交本身 magic/cause 不符」的真实固件错误。
- **fault-record 槽**：`tests/shared/machine-profiles.yaml` 新增 `fault_record` 字段（node = `0x7FFC_0000`，tiny = `null`；在 Node RAM 内、不与 `exit_block=0x7FFD_0000`/`dump_base=0x7FFE_0000` 冲突）；`machine_profile.py` 的 `REQUIRED_FIELDS`/`_INT_FIELDS`/校验同步；arch 向量用 `--defsym FAULT_RECORD=…` + `ld.o` 读（VA=PA identity），**不依赖 cfx0→cfx3 的跨 cfx 寄存器访问**。
- 两个 bootrom 变体（同一 `hmon.S`，`llvm-mc --defsym` 选策略）：
  - `bootrom_step5.bin`（resume；`check-arch-smoke`/`check-arch`/`run_m5_e2e` 用）；
  - `bootrom_step5_inst.bin`（exit；`check-inst`/`check-inst-smoke` 用）。
  - `tools/testcases/arch/build_step5_bootrom.py` 与 Makefile `build-bootrom` 产出两者，均须 4 MiB、`verify_image` PASS；`build/install` 的 QEMU 二进制不动。

### 4. arch 5 条向量（Node 可执行）

- `m5_perm_reserved_illi` / `m5_perm_mask_cfxperm` / `m5_perm_unimpl_cfxreg` / `m5_perm_badcombo_cfxreg`：
  - 删除「user 模式 + bootrom 装 user 向量」的假设；fault 由 hmon（current-mode monitor）承接并写 fault-record；
  - 失败路径改为：`ld.o` 读 `FAULT_RECORD`，与 `1<<n` 期望值比较；通过/失败 token 保持 `0x50..0x53`/`0xE1`（或按需统一，manifest 同步更新 derivation）。
  - `m5_perm_badcombo_cfxreg` 的首条 `cfx2rd cfx_umon, cg6, rc63` 仍由 hmon 承接，恢复后继续。
- `m5_trap_escape`：测试体在 `trap` 前用 `cfx2rc cfx_umon, cg3, rc10, <本地 stub>` 把 `cfx_umon` 的 **hypv** 异常向量指向本文件内的 `escape cfx_umon, 1` stub；随后 `trap cfx_umon, 0x0123`，回来后读 `cfx_umon cg5 rc2`（CFXTRAP）与 `cfx_umon cg4 rc5`（escape_num）。
- `tests/arch/umon/expected.yaml`：更新 5 条 derivation/coverage（current-mode monitor、fault-record 槽、hypv 向量安装），`expected_cause` 保持不变；`tools/testcases/validate_m5_vectors.py` 若解析 derivation 约定需同步（不降断言强度）。
- `tools/testcases/arch/run_m5_e2e.py`：`_defsym_args()` 增加 `FAULT_RECORD`（从 profile 取）；`--profile tiny` 仍显式拒绝。

### 5. L3 13 探针（Node 装载模型）

- 新增共享 prelude（建议 `tools/testcases/arch/node_probe_prelude.py`，或并入现有驱动；**一份实现，13 探针共用**），在 `-bios` 64 KiB 窗口的偏移 0 执行：
  1. 在 cfx_pmem SRAM（`0x47ff_0000_0000`）写 4 个超页 PTE 模板（`SPF=0xFF`、`PPN=i*0x2000`、flags `0xEF`，与 `hmon.S` 逐位一致）；
  2. `cfx2rc cfx_pmem cg15 rc0..rc3`（src/dst=PA 0/size=32/START），轮询 `dma_status.BUSY`；
  3. `cfx2rc cfx_ptw cg12 rc0`（TLB invalidate）、`cg9 rc0`（PTBR=0）、`cg8 rc8`（`ptw_enable=1`）；
  4. `jump` 到探针程序基址（`RESET_PC + 0x1000`）。
- 探针程序整体平移到 ROM 偏移 `0x1000`（各探针把 `ROM_BASE` 改为 `RESET_PC + 0x1000` 即可让 `H=ROM_BASE+0x100` 等标签地址自动跟随；若某探针用 `ROM_BASE` 断言复位 PC，需单独核对）。
- **去掉 `-kernel`**（探针不需要 RAM 预置镜像；Node 不再受任何 raw 前缀约束）；保留 `-bios` + `-semihosting-config` + `-d cpu -D <log>`；每例仍是独立 QEMU 进程。
- 逐例判定（必须写进证据表）：
  - 语义在新 profile 仍成立 ⇒ 仅换算地址/上下文（如 PTW 由 prelude 开启）。
  - 语义前提是「PTW off 直写 PA」/「legacy 16 MiB 窗口」/「jail 模式」等 **新 profile 下不存在** 的前提 ⇒ 用等价手段重写同一意图（例：先 `ptw_enable=0` 再访存以验证 `CFXMEM`，随后恢复），并在 `notes`/derivation 里给出 spec 节号。
  - 确实无法在新 profile 表达 ⇒ 记 `BLOCKED`（case 名 + spec 引用 + 现场日志 + 原因），**并请用户裁定**（改期望 or 退役）；裁定通过后才允许改该探针的 case 清单/覆盖台账。
- `check-arch` 仍跑 13 探针全量；任一探针 rc≠0 ⇒ 整体红（不改成「跳过」）。

### 6. 门控接线（Makefile）

- `_locked-check-inst`（L3）分两段、逐段取 rc、汇总 fail：
  - `[1/2] Node 全量`：`DADAO_TEST_PROFILE=node` + `--trampoline $(STEP5_BOOTROM_DIR)/bootrom_step5_inst.bin`，日志 `运行期日志（已清理，未归档）`；
  - `[2/2] Tiny 子集`：`DADAO_TEST_PROFILE=tiny` + `--trampoline tools/testcases/lib/trampoline.bin` + `--only-profile-cases`，日志 `运行期日志（已清理，未归档）`；
  - 两段都打印 `total/passed/failed/deferred/skipped_profile`；任一段 rc≠0 ⇒ `check-inst` 红。
- `_locked-check-inst-smoke` 换用 `bootrom_step5_inst.bin`；`check-arch-smoke`/`check-arch` 保持 `bootrom_step5.bin`（resume）。
- `l3_run.py` 的 `check-inst` 行不变（仍是一条 L3 记录）；`check-full` 语义不变（不新增 L3 scope 行）。

## 实施清单（按序，可分段交付）

- **P0 基线冻结**：记录开工前 `git rev-parse HEAD`、QEMU 二进制 md5（`安装根 bin 下的 qemu-system-dadao`）、`check-inst`/`check-arch-smoke`/`check-arch` 真实 rc 与失败清单（自查，不是验收）。证据落 `运行期证据（已清理，未归档）`。
- **P1 token + 生成器**：实现 `<count>:@TOKEN`；改 `generate_ctrl_br.py`/`generate_ctrl_jump_call_ret.py` 的 RA/RA0/MemRAS 值；重生成 `tests/inst/base/{ctrl-br,ctrl-jump,ctrl-call,ctrl-ret}.yaml`；`schema.md` 同步；`validate_vectors` 双 profile、`check-generator-sync`、`check-case-ledger`、`check-tests-index` 全绿。
- **P2 profile 过滤**：`run_qemu_test`/`semantics_gate`/`run_qemu_smoke` 跳过与计数；门控结构断言改 `total+skipped==派生`；新增 `--only-profile-cases`。
- **P3 Tiny 11 条**：`ctrl-br` 8 条 riii 改 imm/CFXMEM、2 条 rrii 改 UNDI；`ctrl-jump[2]` 改 imm/CFXMEM + `profiles:[tiny]`；notes 写清目标算式与 spec 依据；真实 Tiny 跑 44 条 tiny-only 全绿（含原 32 条不回退）。
- **P4 Node hmon 双策略 + inst**：`hmon.S` 分流、两个 bootrom 变体、Makefile 接线、`machine-profiles.yaml` 的 `fault_record`；Node 19 条残差按 token（14 条）+ exit 策略（misc 4；`ctrl-ret[9]` 由 token 修好）清零；`ctrl-jump[2]` 归 tiny 后 Node 段无残差。
- **P5 arch 5 条**：按 §4 改 4 个 `m5_perm_*` + `m5_trap_escape` + `expected.yaml`；`check-arch-smoke` 10/10。
- **P6 L3 13 探针**：prelude + 13 探针装载模型 + 逐例判定；`check-arch` rc=0（或按用户裁定后的清单 rc=0）。
- **P7 收尾**：`check-inst` 两段接线、证据脚本与 3 类注入、L1/L2、体例/台账、状态 `待验收`。

> 阶段 P0–P5 与 P6 之间可独立验收；P6 体量最大（13 探针 ≈219 例、≈9.9k 行驱动），若下发后确认超预算，由主会话按本册 §5/§6 原样拆出后续任务（本册保留 P6 全部约束），不得把未跑绿写成 PASS。

## 验收标准

1. **构建/接口**：`make build-bootrom` rc=0；`bootrom_step5.bin` 与 `bootrom_step5_inst.bin` 均 4 MiB 且 builder `verify_image` PASS；两者差异仅限 hmon 镜像区（`cmp`/偏移报告）；`make check-interface` rc=0（90/90，几何未变）。
2. **静态**：`python3 tools/testcases/validate_vectors.py --profile tiny` 与 `--profile node` rc=0；`python3 tools/testcases/validate_m5_vectors.py` rc=0（现场统计 checks，不写死）；`make check-tests-index`、`make check-generator-sync`、`make check-no-residue` rc=0；`make check-case-ledger` rc=0 且 `git diff --exit-code tests/case-ledger.tsv` rc=0（若 P6 退役 case，须先有用户裁定并说明 ledger 变更）。
3. **`make check-inst` rc=0**：Node 段 = `1012 − 44 = 968` 例，`0 failed`、`5 deferred`、`skipped_profile=44`；Tiny 段 = `44` 例，`0 failed`、`skipped_profile=968`；两段真实日志在 `运行期日志（已清理，未归档）`，逐例 SKIP 行含 id 与 profiles。
4. **`make check-inst-smoke` rc=0**（代表集每组 ≥1 例实际执行；无「全组被跳过」）。
5. **`make check-arch-smoke` rc=0、10/10**：5 个 semihosting 不回退；4 个 `m5_perm_*` 与 `m5_trap_escape` 实测 PASS（其中 fault-record 读值与 `expected_cause` 一致）。
6. **`make check-arch` rc=0**：13 探针逐个 rc=0，日志 `运行期日志（已清理，未归档）`；任何 BLOCKED 例必须有用户裁定原文 + spec 引用 + 现场日志，且计入完成区。
7. **L1/L2**：`make -k check` 中本任务触及的检查全 PASS；若有外部基线红（如 `check-patch-tree` 的 gem5 未重导出、`check-knowledge-refs` 的历史 `运行期临时目录` 悬空），须逐条给主树/基线证据并声明非本任务；`make check-modules`（L2）rc=0。
8. **证据/注入**：`运行期证据脚本（已清理，未归档）` 一条命令重跑全部断言、逐项取命令自身 rc（禁 `tee` 吞码）、复杂输出落 `运行期日志（已清理，未归档）`；`inject.sh` 至少 3 类**互不相同**的反例，均要求「注入→FAIL→`cp`+`md5sum -c` 还原→回绿」：
   - (a) 破坏一个 `<count>:@TOKEN` 值（如把 `1:@ENTRY+0x4` 的 count 改 2）⇒ 对应 inst case FAIL；
   - (b) 把 hmon 策略切回统一 0xB7（或翻转 `HMON_FAULT_POLICY`）⇒ Node fault 类 case FAIL；
   - (c) 把探针 prelude 的 `ptw_enable=1` 改为 0（或清一个 PTE）⇒ 对应 L3 探针 FAIL。
   禁 `git checkout/restore/stash/show` 还原（`lessons §3.2`）。
9. **范围**：`git status --porcelain -uall` 仅本任务允许文件；`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**` 零 diff；`QEMU 组件源树` 保持开工单提交（`make check-source-state` rc=0，仅增量 no-op）。
10. **体例/台账**：`make check-tasks`、`make check-milestones-fresh` rc=0；完成区 ≤30 行、审阅记录每轮 ≤40 行；状态 `待验收`；`components/testcases` 无 changelog 要求（testcases 模块无组件补丁）。

## 未决（本册默认采用，下发前请用户确认；否决则按括号内替代）

1. **`<count>:@TOKEN` 扩展**（默认采用；替代：把带绝对地址的 RA 用例全部 `profiles:[tiny]`，Node 放弃这些覆盖）。理由：同一 case 一份、Node/Tiny 都真实跑。
2. **hmon 双策略 + 新增 `bootrom_step5_inst.bin`**（默认采用；替代：Node fault 类 case 全部 `profiles:[tiny]`，但 Tiny 的 ILLI 由「无 cfx」触发，属**不同原因**，会把 case 测成伪绿）。理由：Node 的 machine fault 退出码必须能被 inst harness 真实观察。
3. **Tiny 段并入 `check-inst`**（默认采用：Node 全量 + Tiny tiny-only 44 条；替代：单立 `check-inst-tiny` 但必须挂进 L3，否则 44 条永不执行）。
4. **12 位分支（`br.eq`/`br.ne`）边界保留为 `UNDI`**（默认采用；替代：退役这 2 条 case，需改 `case-ledger.tsv` 并说明覆盖损失）。理由：12 位 imm 最大 ±8 KiB，距 Tiny SRAM 两边界（−0x10100 / +0x7EFEFF）都够不到，原「UNMAPPED」意图在两 profile 均不可表达。
5. **13 探针统一「power 上下文 + identity-PTW prelude」**（默认采用；替代：逐探针迁到 body/hmon 上下文，改上下文模型与更多期望）。若逐例判定出现「新 profile 下不可成立」，默认**登记 BLOCKED + 请示裁定**，不自行退役。

## 文件范围

- **允许**：
  - `tests/inst/base/{ctrl-br,ctrl-jump,ctrl-call,ctrl-ret,aip-si,mem-*,misc}.yaml`（仅 P1/P3 涉及者重生成）、`tests/inst/schema.md`；
  - `tests/arch/umon/{m5_perm_*.s,m5_trap_escape.s,expected.yaml}`；
  - `tests/shared/bootrom/step5/{hmon.S,hmon.lds}`、`tests/shared/machine-profiles.yaml`（仅新增 `fault_record` 字段及注释）；
  - `tools/testcases/lib/{machine_profile.py,run_qemu_test.py,build_test_binary.py,gen_trampoline.py 如需}`、`tools/testcases/inst/run_qemu_smoke.py`、`tools/qemu/semantics_gate.py`、`tools/testcases/generate_ctrl_br.py`、`generate_ctrl_jump_call_ret.py`、`generate_mem_vectors.py`（仅 tiny 用例）、`tools/testcases/validate_m5_vectors.py`、`tools/testcases/arch/{run_m5_e2e.py,build_step5_bootrom.py,min_rom_probe_*.py,node_probe_prelude.py(新)}`、`tools/testcases/check_tests_index.py`（仅地址/token 扫描适配）；
  - `Makefile`（仅测试选择/环境行与 `build-bootrom` 两个镜像产物）；
  - `tests/case-ledger.tsv`（仅未决 4 被否决而退役 case 时，且需用户裁定）；
  - `tests/shared/asm/machine*.inc`（仅 `FAULT_RECORD` defsym 接线必需时）；
  - `.tao/knowledge/issues.yaml`（新问题登记）、本任务书、`.tao/knowledge/milestones.md`、`运行期证据（已清理，未归档）`、`运行期日志（已清理，未归档）/`、`运行期临时目录`。
- **禁止**：`components/**`（QEMU/gem5 及补丁）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`、`组件源树` 的源码改写（只读）。

## 风险

- **R1 体量**：P6 13 探针 ≈219 例；若超出单任务预算，按 P0–P5 已绿部分先验收，P6 原样拆出后续任务（禁止「跳过即绿」）。
- **R2 hmon 变体回归**：改动影响所有 Node inst/arch；每次改后必须跑 `check-inst` + `check-arch-smoke` 两向（exit/resume）验证，不许只看单侧。
- **R3 fault 语义**：`0xB7` 是「hmon 收到非 boot magic」的**固件**错误码，不是 ISA 码；改策略后若把非预期 fault 也当 PASS 即属伪造 —— inst harness 必须把 `0x80|bit` 与 `expected_fault` 精确比较。
- **R4 12 位分支**：`UNDI` 期望覆盖的是「取指全零字」，不是「越界」；notes/derivation 必须写清，避免后人误读成 UNMAPPED 覆盖。
- **R5 探针上下文**：power 上下文 + PTW on 会污染 `cfx_ptw`/`cfx_pmem` 的 reset 值；断言这些寄存器的 case 必须按 §5 逐例校正（spec 引用），必要时 BLOCKED。
- **R6 spec 解释**：jail 模式、cfx 权限掩码、PTW-off 路由若有歧义 ⇒ 停下请示，不用 QEMU 行为当规范。
- **R7 token 兼容**：`<count>:@TOKEN` 只对 RA 值有语义；若误用于普通寄存器会造成 16 位截断，validator 必须能拒绝（可达 FAIL）。
- **R8 磁盘/日志**：`-d cpu` 日志单例可达数十 MB（QEMU-080t 曾写满根盘）；一律落 `运行期临时目录`，每探针跑完即汇总大小并清理临时大文件（保留结论日志）。

## 参考对照（0628 溯源，非执行必需）

- 「内容溯源，非执行必需」：`DADAO-0628` 的 QEMU/gem5 是单几何 + host 代劳的启动模型，hmon 页表/模式移交为历史参考；v5 的 Tiny/Node 几何已被 `SPEC-183t` 取代，不复用其常量、不复制其测试或引导代码。落点 = 本册 §3/§5 的 harness 资产，不是 0628 结构。

## 完成区

**测试结果**：P0–P5 全绿（真实 rc，本机实跑）：`make check-inst` **rc=0**（Node `968 = 963 passed / 5 deferred / skipped_profile=44`；Tiny `44 = 44 passed / skipped_profile=968`）；`make check-inst-smoke` **rc=0**（90/90，skipped 0）；`run_m5_e2e`（resume bootrom）**rc=0**（10/10，5 semi 不回退 + 5 perm 实测 PASS）；`运行期证据脚本（已清理，未归档）` **rc=0（28/28）**。**P6（13 个 L3 探针）未实施** ⇒ `make check-arch` 仍红（`min_rom_probe_046t` 32 FAIL/1 PASS；根因与拆分建议见 `运行期日志（已清理，未归档）`）。

**修改文件**：`tests/shared/{machine-profiles.yaml,asm/machine-node.inc,bootrom/step5/hmon.S}`；`tests/inst/schema.md`、`tests/inst/base/{ctrl-br,ctrl-jump,ctrl-call,ctrl-ret,misc}.yaml`（生成器重生成）、`tests/case-ledger.tsv`（重生成，11 行期望变化，**无退役**）、`tests/arch/umon/{m5_perm_reserved_illi,m5_perm_mask_cfxperm,m5_perm_unimpl_cfxreg,m5_perm_badcombo_cfxreg,m5_trap_escape}.s` + `expected.yaml`；`tools/testcases/lib/{machine_profile,run_qemu_test}.py`、`tools/testcases/{validate_vectors,generate_ctrl_br,generate_ctrl_jump_call_ret,generate_misc}.py`、`tools/testcases/inst/run_qemu_smoke.py`、`tools/testcases/arch/{build_step5_bootrom,gen_machine_inc,run_m5_e2e}.py`、`tools/qemu/semantics_gate.py`、`Makefile`；`.tao/knowledge/issues.yaml`（ISS-341/342）、本任务书。**越界披露**：`tools/testcases/arch/gen_machine_inc.py` 不在 §文件范围清单，但它是 `machine-node.inc` 的唯一生成器，`FAULT_RECORD` 只能由它产出（改 3 行 + `--check` 回绿）。

**验收结果**：`validate_vectors --profile {tiny,node}` rc=0；`validate_m5_vectors` rc=0（140 checks）；`check-generator-sync`/`check-tests-index`(+`--self-test`)/`check-case-ledger`/`gen_machine_inc --check`/`check-interface`/`check-no-residue`/`check-milestones-fresh` rc=0；`build-bootrom` rc=0（两镜像均 4 MiB + `verify_image` + `--compare` 组件级差异报告：power/smon 逐字节一致、仅 hmon 载荷与表内 size 不同）；注入 (a) 破坏 `<count>:@TOKEN` → 单例 FAIL → `cp`+md5 还原 → 回绿；(b) 用 resume 镜像冒充 inst 镜像（临时树）→ misc[2] FAIL → 换回 → 回绿。L1 `make -k check`：仅 `check-knowledge-refs` 红（106 条悬空 `运行期临时目录` 全在其它模块 `.tao` 文档，与本任务改动无交集 = 外部基线）。L2：`check-inst-smoke`/`check-tset-{libc,llvm,embench}-smoke` PASS；`check-lit` 仅 `DADAO-E2E::mcmodel.test` 红（LLVM codegen，未触及）；`check-unit`/`check-modules` BLOCKED（前件 `install-host` 触发 3303 目标 LLVM 全量重建，与本任务无关；已中止，install 根未改写）。

**新发现/坑**：① Node 下 `cfx2rd/cfx2rc` 的**寄存器组合** CFXREG 以「被访问的 cfx」为异常目标（非当前模式 monitor）⇒ 打到 `cfx_umon.hypv` 向量 = ENTRY ⇒ 本体自环（`-d cpu` 恒 PC=ENTRY 且 fault-record 全 0）；资产侧改为 body 自装 `cfx_umon` hypv stub（`ISS-342`）。② ADR-0004 D5.8 的 `0x80|bit_index` 与 CFXREG=0x84 不自洽（`ISS-341`），hmon exit 策略因此逐码写死。③ llvm-mc 对 `add.si rd, (label-.)` / `LOAD_ADDR label` 均崩（no PC-relative fixup）⇒ 用 `rb0 - 4`（stub 紧邻 main）规避。④ 从 hypv 写 `cfx_hmon` 的 cg3 被 CFXPERM 拒绝（只能写自己 cfx）。⑤ 单例/批量都需先做 profile 过滤再判 deferred（否则 Tiny 段会算进 5 条 deferred，与 968 口径不符）。

**遗留问题**：**P6 未实施（13 探针）**：装载模型（prelude/PTW/去 `-kernel`/ROM 偏移 0x1000）+ 逐例重判（含 `exit_seq` 写死 Tiny 窗口、kernel 预置数据表失效、PTW 打开后 `addr[47:42]==0` 地址语义改变）远超单任务预算，建议按本册 §5 拆成 `<PREFIX>-093t`（装载模型）与 `<PREFIX>-094t`（逐例判定 + BLOCKED/用户裁定），证据与拆法见 `运行期日志（已清理，未归档）`；`make check-arch` 在拆分任务完成前维持红。另：`tests/case-ledger.tsv` 的 diff 需随本任务 commit 落地（重生成所致，非退役）。

**收尾（architect 2026-11-03）**：reviewer 判 **P0–P5 Accepted**、P6 拆独立任务 ⇒ 本册置 `已验证`；P6 未实施、`make check-arch` 仍红，如实留待拆分任务。findings 处置：**F1 已修**（以现场 `check-knowledge-refs` **101** 条为准，完成区「106」系笔误）；**F2 已解**（本提交落地后 `git diff --exit-code tests/case-ledger.tsv` rc=0，11 行系 P3 重生成、非退役；验收标准 2 原文不改，以现场 rc 为准）；**F3 已修**（`milestones.md` 属允许范围、已随本册登记并提交）；**F4 转 `TESTCASES-093t` 阻断前置**（见下）；**F5 已修**（`install-host` 现场触发 `[1/3147]`，完成区「3303 目标」为早期读数）；**F6 已解**（流水「一句改动」按实测改写，不再称 `check-arch` 绿）。

**TESTCASES-093t 拆分建议（P6 收口）**：092t 原议 093t（装载模型）+094t（逐例判定）合并为单册 `TESTCASES-093t`，092t §5/§6 与「验收标准 6」原文保留、作为其接口规范。**阻断前置（必须先行，否则 P6 做完仍红）**：① **F4** —— `check-arch` 的 13 探针循环不传 `--qemu`、默认 `运行期 QEMU 构建树中的 qemu-system-dadao` 在任务 worktree 不存在（pre-existing，092t 未改该循环）⇒ 探针一律 rc≠0；093t 须先修该循环（传 `--qemu` 或按安装根解析）。② 13 探针统一 prelude（identity PTW + 去 `-kernel` + ROM 偏移 `0x1000`）③ 逐例判定表，BLOCKED 须用户裁定原文 + spec 节号 ④ 体量 ≈219 例，超预算再由主会话按 092t §5 拆 `TESTCASES-094t`（逐例判定 + BLOCKED/裁定）。

## 审阅记录

#### 第 1 轮 engineer 自审
自主逐行审查（无嵌套子代理）。findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 misc[2..5] 装 `cfx3.hypv` 向量的前缀从 hypv 被 CFXPERM 拒 ⇒ 观察不到 ILLI | ✅已修 | 生成器删 `_illegal_escape_sequence`，用例只留被测 `escape`（靠 hmon exit 策略看 0x88） | 4 例 Node rc=0x88；`generate_misc --check` PASS |
| F2 `m5_perm_badcombo` 的 CFXREG 打到被访问 cfx(umon) 的 ENTRY 向量 ⇒ 自环(timeout) | ✅已修 | 用例自装 `cfx_umon.hypv` = 本地 `escape` stub（`rb0-4`） | `run_m5_e2e` PASS(0x53)；`-d cpu` 无自环 |
| F3 `add.si rd,(label-.)` → llvm-mc crash | ✅已修 | stub 紧邻 `main`，用 `add.si -4` + `jump [rb0, main]` 布局 | 汇编 rc=0，10/10 |
| F4 validator 的 boundary fault 白名单只收 ILLI/UNMAPPED | ✅已修 | 扩为 +CFXMEM/UNDI（Tiny 真实路由，附 spec 依据） | 两 profile `validate_vectors` rc=0 |
| F5 `case-ledger.tsv` 11 行漂移 | ✅已修 | `check_case_ledger --write` 重生成（1995 条不变 ⇒ 无退役） | `make check-case-ledger` rc=0 |
| F6 `generate_misc.py` 删序列后留下死函数/死 import | ✅已修 | 删 `_cfx2r{c,d}`/`_xor_o`/`_br_nz`/`encode_illi_poison` 等孤儿 | `--check` PASS |
| F7 `run_single_test` 默认选例未过滤 profile（可能选中不适用 case） | ✅已修 | `next(...)` 加 `case_applies` | Node `--case 11` → SKIP rc=0 |
| F8 D5.8 公式 vs CFXREG=0x84 不自洽 | ❌不修（禁改 spec/ADR） | hmon 逐码写死 + 登记 `ISS-341` | issues.yaml 解析 OK |
| F9 CFXREG 异常目标 cfx 与「current-mode monitor」不一致 | ❌不修（禁改 QEMU） | 资产侧规避 + 登记 `ISS-342` | 同上 + arch 10/10 |
| F10 P6 探针未实施 | ⏸延后 | 见「遗留问题」，附评估文档 | `check-arch` 仍红（未写 PASS） |

判决：F1–F7 已修并复验，F8/F9 属禁改范围改为登记，F10 按任务书 P6 附注/§R1 拆分；**P0–P5 判「待验收」**，P6 交主会话拆任务。

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 独立真跑；rc 均取命令自身，未用管道/tee 取码）**
- `运行期证据脚本（已清理，未归档）` → **rc=0，`== RESULT: 28/28 PASS, 0 FAIL ==`**（86 s）。
- `make check-inst` → **rc=0**；Node `Results: 968 total, 963 passed, 0 failed, 5 deferred, 0 errors, skipped_profile=44`；Tiny `Results: 44 total, 44 passed, 0 failed, 0 deferred, 0 errors, skipped_profile=968`；SKIP 行 44/968 条，逐条含 `file[i] <id> profiles=[…]`。
- `make check-inst-smoke` → **rc=0**；`代表集: 90 条`（现场派生）、`QEMU: total=90 passed=90 failed=0 deferred=0 errors=0 skipped_profile=0`，class/mnemonic 覆盖与「不得全组被跳过」断言在。
- `run_m5_e2e`（resume 镜像，run.sh 第 5 段）→ **rc=0，`Results: 10/10 passed, 0 failed`**；5 个 perm 实测 exit=80/81/82/83/96、cause=ILLI/CFXPERM/CFXREG/CFXREG/CFXTRAP 与 expected 一致；`expected_cause` 无 diff。
- 静态：`validate_vectors --profile {tiny,node}`、`validate_m5_vectors`（**现场 140 checks**）、`gen_machine_inc --check`、`check-generator-sync`、`check-tests-index`(+`--self-test`)、`check-case-ledger`、`check-no-residue`、`check-tasks`、`check-milestones-fresh`、`check-interface`（90 项全 PASS）、`check-source-state` → **均 rc=0**。
- L1 `make -k check` → **rc=2**，唯一失败 `check-knowledge-refs`（`悬空: 101`，条目全在 gem5/spec/qemu 等其它模块 `.tao` 文档，本任务关键字命中 **0**）= 外部基线，与完成区口径一致（数量见 F1）。
- L2 `make check-lit` → **rc=2**，`Failed Tests (1): DADAO-E2E :: mcmodel.test`（161/162 pass，LLVM codegen）= 外部。
- P6 现场（显式 `--qemu`）：`min_rom_probe_044t` → **rc=1，13 FAIL/0 PASS**；`min_rom_probe_046t` → **rc=1，32 FAIL/1 PASS**（失败面几乎全 `got=0x81` CFXMEM，与任务书 §现状证据 4 根因一致）；按 `check-arch` 的实际调用方式（**不传 `--qemu`**）跑 13 探针 → **全部 rc≠0** ⇒ `check-arch` 必红。
- `make check-arch-smoke` → 前置 `install-host` 触发 `ninja -j8 -C 运行期 LLVM 构建树 … [1/3147]` 全量重建，900 s 由 reviewer 中止；install 根 mtime 全部 ≤ `2026-11-03 10:09`（开工前）⇒ 未改写；`_locked-test-codegen/-test-elf` 依赖 `install-host`、`_locked-check-arch-smoke` 亦依赖 ⇒ **`check-unit`/`check-modules` BLOCKED 成立**。
- QEMU md5 `0949cb1f85df0cf04fbd7ec6b441129e` = P0 基线 ⇒ 未重建、未改动。

**独立注入（与 engineer 的 (a) count 破坏、(b) resume 镜像均不同）**：`cp tests/inst/base/ctrl-br.yaml → …bak`（md5 `80d03d04eb6a7e78198ca1e3b6816aee`）→ 将 `ctrl-br[3] br.n_riii_rd` boundary `expected_fault` `CFXMEM`→`UNMAPPED` → 重跑**同一** `run.sh` → **rc=1，`24/28`，4 FAIL**（`generate_ctrl_br --check: FAIL`、`check-case-ledger: 缺 1 行/多 1 行`、`check-inst [2/2] tiny subset rc=1`、`FAIL ctrl-br.yaml[3]: Expected UNMAPPED, got CFXMEM`）→ `cp` 还原 + `md5sum -c` **OK** → 重跑 **rc=0，28/28** 回绿。注入前后 `git status --porcelain -uall` 快照逐行一致（31 文件，无残留）。

**约束核验**：禁区 `components/ spec/ contracts/ .tao/contracts/ .tao/adr/ manifests/ .tao/knowledge/discussing.md .tao/archive/` **零 diff**；`git status` 31 文件 = 完成区声明 + `milestones.md`（在允许范围内，声明漏列 = F3）；完成区 5 段（≤30 行）、审阅记录 17 行（≤40）；状态 `待验收`；P6 明写「未实施 ⇒ `make check-arch` 仍红」并给 093t/094t 拆分，**无 PASS 伪称**；ISS-341/342 已登记且 `issues.yaml` 过 L1；`case-ledger` **11 行重生成、无退役**（10×ctrl-br boundary + 1×ctrl-jump[2]；`check-case-ledger` rc=0）；`<count>:@TOKEN` 真实实现（29 处实例；`resolve` 实测 node/tiny 正确，越界 count/越 48 位/非法 token 均 `ProfileError`，validator 有 RA/RAS placement 拒绝 = R7 可达）；profile 过滤真实实现（`case_applies` + `skipped_profile` + `--only-profile-cases` + `total+skipped==现场派生` fail-closed + `skipped==0` 即红）；Tiny 11 条 = 8×CFXMEM + 2×UNDI（ctrl-br）+ ctrl-jump[2] `profiles:[tiny] CFXMEM`，Node 段 0 failed ⇒ 19 条残差清零。

**Findings（文档级，按 §6.5 不阻断）**：F1 完成区「悬空 106 条」vs 现场 `悬空: 101`；F2 验收标准 2 的 `git diff --exit-code tests/case-ledger.tsv` 实测 **rc=1**（11 行系 P3 期望变更的必然重生成、已披露、非退役，原文只预留「P6 退役需裁定」例外 ⇒ 措辞与交付冲突，commit 后自然回 rc=0，建议收尾修订措辞）；F3 `milestones.md` 未列入「修改文件」；F4 `check-arch` 探针循环不传 `--qemu`、默认 `运行期 QEMU 构建树中的 qemu-system-dadao` 在本 worktree **不存在**（**pre-existing，本任务未改该循环**）⇒ 即便 P6 完成 `check-arch` 仍会红，须写进 093t 前置；F5 「3303 目标」vs 现场 `[1/3147]`；F6 milestones「一句改动」仍写「check-inst/check-arch 真跑绿」。

**判决：P0–P5 = Accepted，P6 按任务书 P6 附注/R1 拆为独立任务。** 依据：验收标准 1/3/4/8/9/10 全部由 reviewer 自己重跑证实；标准 5 的 `run_m5_e2e 10/10`（P5 本体）成立，标准 6（`check-arch` rc=0）、标准 5 的 `make check-arch-smoke` 整体、标准 7 的 `check-modules` 属 **P6 + install-host 环境**阻断，完成区已如实 BLOCKED 披露（无伪绿），符合任务书「P0–P5 与 P6 可独立验收、不得把未跑绿写成 PASS」；F1–F6 由 architect 收尾修订，其中 **F4 为 P6 收口的阻断前置**（供 architect 定夺）。

#### 收尾提交（architect 2026-11-03）
- **档位**：正常提交（reviewer `Accepted`，P0–P5）。
- **文件集对账**：显式 staging **31/31** 与完成区「修改文件」逐项一致；唯一额外项 `milestones.md`（允许范围、已在收尾结论披露）；禁区 `components/ spec/ contracts/ .tao/contracts/ .tao/adr/ manifests/` 零 diff。
- **提交**：`TESTCASES-092t: Tiny/Node 执行资产 P0–P5`（本分支 HEAD；`git rev-parse HEAD` 见主会话报告）。
- **提交后复跑**（本 worktree，真 rc）：`运行期证据脚本（已清理，未归档）` **rc=0（28/28）**（含 `check-inst` 两段 / `check-inst-smoke` / `run_m5_e2e` / 注入 a,b）；`check-case-ledger`/`check-no-residue`/`check-milestones-fresh`/`check-tests-index`/`check-generator-sync`/`check-interface`/`check-source-state` 均 **rc=0**；`git diff --exit-code tests/case-ledger.tsv` **rc=0**（F2 消解）。
- **同步**：`git merge master`（`master = ee2ef948`）**rc=0 / Already up to date**（master 未前进，无冲突）；**未 merge 到 master、未 push**。
