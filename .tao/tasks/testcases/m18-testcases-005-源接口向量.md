# m18-testcases-005: 每源 pending/mask/ack 向量（cg15/cg16）

**模块**：testcases
**项目里程碑**：M18
**依赖**：`m18-spec-008`、`m18-qemu-009`（执行侧）、`m18-testcases-004`（R3 载体基线）
**可并行分片**：否
**预估**：3–4 h（标定：同档 testcases-004 3–4 h；本任务为布局迁移 + 新语义向量，取 1–1.2×）
**档位**：中改（独立向量）
**状态**：已验证

## 背景

`m18-spec-008` 把异步捕获移到 `cg15`、monitor mask 移到 `cg15 rc3`、两个源各有 `cg16 rc16/17/18`，并把 pending 改为 ack 才清。现有向量（`m18-testcases-004` 的 escape/pmem/hart 载体）仍按 `cg9`/`cg8 rc1` 写。

## 目标

1. 迁移现有载体/探针：`tests/inst/11-cfx/**`、`tests/arch/**`、`tests/ee-vast|tiny/**`、`tests/shared/asm/**`、legacy 探针、`tools/testcases/generate_lit_vectors.py` 到 `cg15`/`cg15 rc3`/`cg16`。
2. 新向量（独立派生自 spec）：
   - timer：ENABLE/cmp/pending/mask/ack 五组（含使能即检、ack 幂等、写 cmp 不清 pending）；
   - DMA：bit0 合并 DONE|ERROR、ack 只清 pending、status 另行 W1C、`IRQ_EN` 已删；
   - 进入判定：源 mask 与 monitor mask 各自生效、多源合并、`cg15 rc4/rc5` 聚合；
   - `escape rc11` 写 `cg15 rc3` 整字。
3. 执行侧：QEMU（qemu-009 构建）+ RTL/gem5/IDL 可跑项；不可跑项登记 KNOWN-RED。
4. **补 qemu-009 reviewer F3 的两处覆盖**：① 直接断言 monitor `cg15 rc3` **复位全 1**（不能先写 ALL1 再读）；② `cg15 rc6`–`rc13`、`cg8 rc5` 等 reserved 槽访问 ⇒ `CFXREG`。
4. 旧槽位/旧措辞 grep 0；生成物重算。

## 验收

1. `check-inst-asm`、`check-tests-index`、`check-case-ledger`、`check-qemu-forms`、`check-spec-refs` rc=0；向量在 QEMU 上逐条 PASS。
2. 可达 FAIL ≥2（改期望/把 pending 改回进入即清），`cp`+md5 还原。
3. 完成区 ≤30 行；状态 → `待验收`。

## 硬约束

1. 独立 worktree；不提交 git；证据脚本 = 运行期证据目录内 `run.sh`。
2. 只动 `tests/**`、`tools/testcases/**`、`tools/llvm/*matrix*`（生成物）、本任务书；不改实现/spec/契约/Makefile；期望独立派生。
3. 等 `m18-spec-008` 与 `m18-qemu-009` 落地后派。

## 完成区

**测试结果**：证据脚本 26/26（4 门控 + arch-self-test + check-inst-asm 274/274 + 2 探针 + 2 探针自检 + 6 载体模式 + 2 oracle 自检 + 2 旧槽 grep + 3 注入红→cp+md5 回绿）。`m18qemu009` 17 例/134 断言、`m18qemu008` 21 例/150 断言、`cfx15.S` hmon/smon/umon 124/38/38 槽、`pmem_dma.S` 48/10/10 槽逐条 PASS；两个 `--self-test` 全断言可达 FAIL。
**修改文件**：`tests/arch/hart/{cfx15.S,check_cfx15.py,check_hart.py,expected.yaml,README.md}`、`tests/arch/pmem/{pmem_dma.S,pmem_oracle.py,expected.yaml,README.md}`、`tests/arch/{modes.yaml,vast-arch-inventory.md}`、`tests/inst/11-cfx/{escape_ciii_cfx.S,cfx2rc_crrr_cfx.S,cfx2rd_crrr_cfx.S}`、`tests/unit/gem5/tiny_hmon/{tiny_hmon.S,expected.yaml}`、`tools/testcases/arch/min_rom_probe_{m18qemu009,m18qemu008,integ050t,integ051t,async_094t,integ042t}.py`、`tools/testcases/arch/README.md`、本任务书。
**验收结果**：工作树 QEMU（qemu-009 合入后源码，md5 `f0767113…`）构建 PASS；共享安装根仍为 0.8.0（qemu md5 `8b49d6d9…`、step5 bootrom 旧），未覆盖，证据脚本记录两侧 md5 并用本地 `.dadao` 树（工具链软链 + 本地 bootrom/gate.lock）跑门控。F3①：`hart_layout` 在未写 monitor 掩码前直读 umon/jmon/smon/hmon `cg15 rc3` = 全 1；F3②：新增 `reserved_cg15_a..d`（rc6–rc13）与 `reserved_cg8_5`（cg8 rc5/rc1）⇒ `CFXREG`；另新增 `source_mask_gate`（源 mask 独立门控）与 `dma_merge_two_completions`（bit0 合并/ack 只清 pending）。注入：cfx15 oracle 把 entry-pending 改回 0、F3 复位改 0、F3 reserved 期望改 0 均 rc=1，`cp`+md5 还原后回绿。
**新发现/坑**：启动链 PMEM DMA 在新模型留下 `cg16` pending bit0，会污染 `cg15 rc5` 汇总 ⇒ 载体入口须先 ack；`set.ow wp0,0xffff` 是 64 位全 1（其余 48 位补 1），不是低 16 位；`cfx_hart cg16 rc0` 只留 bit0，写 2/3 读回 0/1；S 模式旧 `cg3 rc12=0x…FCF7` 不含 cg15 ⇒ 自访问 CFXREG→PC 0，须加 bit15/16；共享安装根 + 共享 bootrom/gate.lock 会让 check-inst-asm 交叉污染（rc=-2），改用本地 `.dadao` 树后 274/274。
**遗留问题**：`integ042t/integ050t/integ051t/async_094t` 的**异步返回路径**仍按 R2（smon 直接 `escape` 到 hypv，0.8.1 判升权 ⇒ CFXESC），其 async 用例 KNOWN-RED；入口/ack 语义已由 `m18qemu009` 覆盖，待 gem5/RTL/内核任务统一改写。`tests/arch/pmem/pmem.S` + `check_pmem.py`（RTL/gem5 寄存器面，含 IRQ_EN）与 `tests/unit/linux/k2_*`（内核仍 0.8.0）归 `m18-chipyard`/`m18-gem5`/`m18-linux-027`，未在本任务改。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| cfx15 timer_ctrl 期望仍按旧 IMASK/ISTATUS 写 2/3 原值 | ✅已修 | oracle 改为 bit0-only：写 2⇒0、写 3⇒1 | hmon/smon/umon 三模式 PASS |
| 启动链 PMEM DMA pending bit32 污染 `cg15 rc5` 汇总 | ✅已修 | `cfx15.S`/`pmem_dma.S` 入口先写 `cfx_pmem cg16 rc18` ack | 槽 26/63 等回绿 |
| S 模式 `cfx_smon cg3 rc12` 未放 cg15 ⇒ 自访问 CFXREG 落 PC 0 | ✅已修 | setup_s 改 `0xFFFFFFFFFFFE7CF7` | smon 38 槽 PASS |
| pmem multi-source 只捕获 PMEM（timer 源 mask 仍全 1） | ✅已修 | 入口补 `cfx_hart cg16 rc16=0` | multi src_frame = 1<<15\|1<<32 |
| m18qemu008 未 ack 预置 DMA、async handler 进入即清假设 | ✅已修 | body_setup ack；两处 handler escape 前 `cg16 rc18` | 21 例/150 断言 PASS |
| 旧槽扫描把 reserved 负例/`cfx_ptw cg9` 当违规 | ✅已修 | 证据脚本排除 `reserved`/`CFXREG`/`cfx_ptw`；注释同步 cg15 | grep 两路 PASS (0) |
| 证据脚本 `ck` 的 `$?` 取到 if 状态、inject 多传参数 | ✅已修 | 先存 rc；修正调用 | 证据 26/26 |
| 共享 `.dadao` 软链导致旧 QEMU/bootrom/gate.lock 交叉污染 | ✅已修 | 工作树本地 `.dadao` 树：工具链软链、qemu 指工作树构建、本地 bootrom/gate.lock | check-inst-asm 274/274 |
| 旧 R2 探针的 smon→hypv 异步返回与“不得升权”冲突 | ⏸延后 | 槽位/ack 已迁移；返回路径待各实现任务重写 | 登记 KNOWN-RED，未静默跳过 |

### 第 1 轮 reviewer 验收

**重跑记录（本人在任务 worktree 仓库根执行；证据一律指运行期证据目录内的 `run.sh`）**
1. `run.sh` 连跑 3 次：均 `summary: pass=26 fail=0`、`EXIT=0`（4 门控 + arch-self-test + check-inst-asm + 2 探针 + 2 自检 + 6 载体 + 2 oracle 自检 + 2 旧槽 grep + 3 注入红→回绿）。
2. `check-inst-asm`：`274/274 镜像通过（274 个 id；链例 + 故障链 634 例）`、`check-inst-asm: PASS`。
3. `min_rom_probe_m18qemu009.py --qemu <工作树 qemu>`：`17 case(s), 0 failure(s)`，逐例 check 数现场求和 = **134**；`--self-test` 17/17 全「有可达 FAIL」PASS。
4. `min_rom_probe_m18qemu008.py`：`21 case(s), 0 failure(s)`，现场求和 = **150**；`--self-test` PASS。
5. 载体：`arch-hart-001/hmon（124 槽）`、`arch-hart-002/smon（38）`、`arch-hart-002/umon（38）`、`arch-pmem-001/hmon（48）`、`arch-pmem-002/smon（10）`、`arch-pmem-002/umon（10）` 全 PASS；`check_cfx15 --self-test`、`pmem_oracle --self-test` PASS。
6. `make check`：`EXIT=2`，唯一红 = `check-syscall-abi`（缺 linux 源树，环境），日志 `[PASS] 110` 行、零 `[FAIL]`。
7. `git show --name-only 2fbb118f` = 24 文件，与完成区「修改文件」逐行 `diff` 无差；禁区 `components/ spec/ .tao/contracts/ Makefile idl/` 零命中；`git branch -r --contains` 为空（未 push）；状态「待验收」；任务书无运行期路径。

**注入**
- 工程师 3 路我方重跑均红（`slot 70 … expected 0x0 actual 0x8000`、`rd20 expected 0x0 actual 0x4`、`rd38 expected 0x0 actual 0xffff…`），`cp`+md5 回绿（`feded80e…`/`de524035…`）。
- 我方自设 1 路：删 `cfx15.S` 入口 `cfx_pmem cg16 rc18` ack（md5 变更）⇒ 同一 `run.sh` `EXIT=1`、`pass=22 fail=4`（hmon/smon/umon 的 slot 26/63 等 FAIL）；`cp` 还原 md5 相等后重跑 `26/26 EXIT=0`。
- 附两路：删 `pmem_dma.S` 同一 ack ⇒ 全绿不红（该 ack 在本环境冗余，已还原）；向 `cfx15.S` 注入 `cg8 rc1` 违规行使 `run.sh` 第 5 步 grep `FAIL` 可达（已还原，md5 `5a9538a8…`）。

**约束核验**：独立 worktree、WIP 提交仅在任务分支且未 push；证据脚本位于运行期证据目录；期望现场由 `spec_facts()`/`facts()` 解析 `spec/DADAO-12` + 契约 + ADR 派生（非读实现）；仅动声明的 24 文件，无越界。

**遗留判定**：`async_094t` 实跑 `8/8 FAIL`，代码核验 smon handler 写 `cg5 rc0/rc1/rc3`（现 HW/RO ⇒ `CFXREG`）+ `escape` 回 hypv（升权 ⇒ `CFXESC`）⇒「双重非法」登记成立；但 `integ050t` 全量 `3/17 runtime passed`（`hart_id_zero` 等 4 例 TIMEOUT、`timer_ctrl_rw` rd7 3→1、SBI 两例 0x7e），迁移前基线在同 QEMU 同例亦红 ⇒ 无回归、登记口径偏窄。依赖只写「待 gem5/RTL/内核任务」，未点名任务号。负例改造：spec 侧「异步进入模式上限」裁定时间（16:32）晚于本提交（16:20）且本分支未含、实现侧同名任务仍「待开始」⇒ **建议等其落地后再把返回路径改成「默认 rc14=supv 下 hypv 不进入」负例**，由 architect 定夺。

**finding（4 条，均文档/口径级，不阻断）**：F1 KNOWN-RED 只写「async 用例」，050t 实测 3/17；F2 遗留未点名依赖任务号（`m18-chipyard-003`/`m18-gem5-005`/`m18-idl-004`/`m18-linux-027`）；F3 目标 4「旧槽位 grep 0」未在任务书写明文件集已排除 `tests/arch/pmem/pmem.S`（现场 `tests/arch/**` 仍 30+ 旧槽、4 处 `IRQ_EN`，归属已披露给 chipyard/gem5）；F4 `pmem_dma.S` 槽 23 注释 `@@ 23 = 0` 与本任务新头注「进入后仍置位」及 oracle 期望相反（改前既有）。

**判决：Accepted**
