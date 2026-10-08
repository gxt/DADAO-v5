# INTEG-020t: SEE/semihosting E2E + harness stdio 捕获 + 门控收口（`make test-semihost`）

**模块**：integ
**项目里程碑**：M5
**依赖**：`QEMU-046t`、`QEMU-047t`、`TESTCASES-033t`、`TESTCASES-034t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `QEMU-046t`（semihosting 共享层 + `SYS_EXIT`）、`QEMU-047t`（新 bootrom + `-bios`）、`TESTCASES-033t`（SEE/semihosting 向量）、`TESTCASES-034t`（exit-port→`SYS_EXIT` 迁移后）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`，**D7** host 侧安全：`-semihosting-config` 的 `target=`/`chardev=`/`arg=`；建议默认 `gdb`/沙箱）+ `adr-0004` 修订。
  - `spec/Process-05-里程碑TDD规范.md §6`（落点 + `INFRA-048t` 的 `.dadao/tests/`）；`tools/infra/paths.py`（`test_artifacts_dir`）。
  - 既有 `tools/integ/run_elf_e2e.py`/`Makefile::test-elf`/`check-lit`（E2E 驱动范式）。
  - **门槛（`INTEG-019k` §第 2 轮用户裁定 9；**正向口径已由 `INTEG-019k` §第 8 轮修订**）**：门控名 = **`make test-semihost`**（**不是** `test-see`）；组成 = ① **正向**（**bootrom（`-bios`）+ bin 应用**经 `-semihosting`、console 捕获、`SYS_EXIT` 码）；② **权限反例**（**M5 可观测 = cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕；**`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 权限层、不在 M5**〔`ADR-0020 D9`〕）；③ **服务表各条至少 1 例**；④ **不回归**（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`）；⑤ **`INTEG` 开闭**。
  - **RAM@0 双映射（C1 step1，`ADR-0004 R3`/`ADR-0020 D15`）**：M5 **正向**（bootrom/SEE + `-semihosting`）经 **RAM@0**（`QEMU-049t` 双映射提供）；**旧 RAM 段过渡保留** ⇒ 既有测试不回归；**step2**（旧向量/harness 迁到 RAM@0 + 删旧段 + 收紧断言）**另立、随 M6**（用户 2026-10-08 裁定；`ISS-165`），**不阻塞本门槛**。
- **输出**：
  1. **`tools/integ/` 驱动**（**复用 `tools/integ/run_m5_e2e.py`**〔`TESTCASES-033t` 产出〕，**只追加/最小改**，**不另建 `run_semihost_e2e.py`**）：fail-closed——bootrom（`-bios`，`QEMU-047t`）+ **bin 应用**（`objcopy -O binary`）经 `-semihosting`，跑通 semihosting 服务，**捕获 console 输出**，比对 `SYS_EXIT` 码；逐例打印「名字/期望/实际/退出码」。**（原「单/多 TU ELF」正向用例移 M6——用户 2026-10-08 裁定。）**
  2. **harness stdio 捕获（细节展开，本任务明确落定）**：
     - **`-semihosting-config` 的 `target=`/`chardev=`/`arg=` 由谁传**：**明确**是 **Makefile 传参** 还是 **harness 脚本包装**（二选一，落定并记录理由）；建议 **驱动脚本经 `-semihosting-config target=gdb|native,chardev=...` 传参**（与 `ADR-0020 D7` 一致，默认沙箱）。
     - **console 输出捕获落点**：捕获到 **stdout** 还是 **stderr**（或 chardev 文件），**落点** = `.dadao/tests/semihost-e2e/`（`INFRA-048t` 口径）；**比对方式**（逐字节/去尾空白/期望串包含）。
  3. **`Makefile` 新目标 `test-semihost`**：见门槛五组成；**任何一类不符即非零退出**；与既有 `test-elf`/`test-codegen` **并存**。
  4. **`tests/e2e/lit/`**（如适用）：semihosting E2E lit 用例（`Process-05 §6`；`check-lit` 路径 `tests/e2e/lit`）。
  5. **`make check` 收口**：新目标接入/不破坏既有门控；`INTEG` 开闭登记（`INTEG-021m` 前置）。
- **约束（硬）**：
  - **门控名 = `make test-semihost`**（**不得**用 `test-see`——用户指出"没有 SEE"）。
  - **`SYS_EXIT` 为退出机制**（`TESTCASES-034t` 后）；**不回归** M1–M4 链。
  - **期望值独立派生**（`Process-05 §4`）；console 比对**不得**只凭 QEMU 输出反填。
  - **不回归**：`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit` 全绿。
  - `Makefile`/`tests/`/`tools/` 为共享文件，与其它改这些文件的任务**串行**。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/INTEG-020t/`；**不提交 git**；复杂命令输出留存 `.work/log/integ/`（**禁 `tee`**）。
  - **重建成本申报**：依赖 `build-mc`/`build-lld`/`build-qemu`（增量；`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **正向**：`make test-semihost` EXIT=0；bootrom（`-bios`）+ **bin 应用**经 `-semihosting`，console 捕获内容与 `SYS_EXIT` 码逐例比对正确；给真实输出（console ≥1）。**（原「单/多 TU ELF」正向用例移 M6——用户 2026-10-08 裁定。）**
2. **权限反例**（cfx 级）：**M5 可观测 = cfx 级**——`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕（≥1 类）——机器可判（真实输出）。**（`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 层、不在 M5；`ADR-0020 D9`。）**
3. **服务表覆盖**：**25 服务各 ≥1 例**（脚本计数=25；给真实输出）。
4. **不回归**：`make test-elf` 5/5、`make test-codegen` 15/15、`make check`、`make check-lit` 全 EXIT=0（给真实输出）。
5. **harness stdio 落定**：完成区明确「`-semihosting-config` 传参方」与「console 捕获落点/比对方式」，且与实现一致（`grep`/真实输出）。
6. **反例门控**：注入反例（改一条期望退出码 / 改一条 console 期望串 ⇒ `test-semihost` **非零退出** ⇒ 还原 ⇒ 回绿）；给真实输出。
7. **一键证据脚本**：`.work/evidence/INTEG-020t/run.sh`——非交互、失败非零、逐项打印、含注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅 `tools/integ/**` + `Makefile` + `tests/e2e/lit/**` + 本任务书；`.dadao/` 生成物不入库。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 核 25 服务/反向例/不回归 + 判决）

#### architect 前置风险评估（QEMU-047t 遗留；2026-10-08，**只追加**，**待用户裁定**）

**背景**：`QEMU-047t` 选 **`ADR-0004 D2.3` 路径 B（raw-bin 双镜像）**——bootrom 经 `-bios` 载入 ROM 基址、应用 flat bin 经 `-kernel` 载入**旧 RAM 段**；**未实现「`-bios` bootrom + ELF 应用」组合**。实测（`.work/source/qemu/hw/dadao/dadao-machine.c`）：kernel 为 ELF 时走**路径 A 并整体忽略 `machine->firmware`**（无 `-bios`、PC=`e_entry`）；`dadao_load_regions[]` 仍仅 `{旧 RAM 0xffff_0000_0000, ROM 0xffff_ffff_0000}`，**未含 RAM@0**。

**（1）是否确为门槛前置缺口（实测核实）**

- 门槛正向组成原文（`milestones.md` M5 段 / `INTEG-019k` §第 2 轮裁定 9）= **「bootrom + 单/多 TU ELF 经 `-semihosting`、console 捕获、`SYS_EXIT` 码」**；本任务书「输出 1」「验收 1」同义复述。
- `ADR-0004`（`R1`）：`-bios` bootrom 路径与既有 M4 ELF 路径（`D2.2/D2.3` **路径 A，不用 `-bios`**）**并存、非替代**；`D2.3 路径 A` 正文明确「本路径**不使用**外部 `-bios` ROM blob」。⇒ **「`-bios`+ELF」组合语义未被任何 ADR 定义。**
- 现网三条可用路径：**(a) 路径 B** = bootrom + raw-bin（`QEMU-047t` 已实现）——**非 ELF**（手工 `.S` → `objcopy` flat，未过 `llc`/`ld.lld`、无多 TU）；**(b) 路径 A** = ELF 单独（**无 bootrom**；段须落 `dadao_load_regions[]` 已列区域 = 旧 RAM/ROM）；**(c) 「`-bios`+ELF」组合 = 不存在**。
- **结论**：**按字面耦合读**（bootrom 与单/多 TU ELF 同为一例）⇒ **确为门槛前置缺口**：(a) 缺「ELF」、(b) 缺「bootrom」、(c) 未实现，无任一现成路径可同时满足两者。**按拆分读**（正向含两个独立子例）⇒ ELF 子例可由路径 A 满足（semihosting 在译码层短路、与 cfx 无关，**不依赖 bootrom 初始化**）、bootrom 子例仅 raw-bin；但此时 ELF 子例**未经 SEE 初始化**，与 M5「SEE/HEE 运行环境」目的不符。**判据取舍待用户裁定。**

**（2）选项（代价 / 影响面）**

- **A（另立任务，串于 `QEMU-047t` 与 `INTEG-020t` 之间）**：扩 `dadao_load_regions[]`（+RAM@0）+ 定义「`-bios`+ELF」组合加载/入口约定（复位 PC=`0xffff_ffff_0000`、bootrom 先跑、初始化后跳 ELF `e_entry`；须定 `e_entry` 传递方式）+ 验证（含反例）。
  - 代价：新任务书 + `components/qemu/**` 补丁 + 重 `build-qemu`（5–20 min）；**新增组合语义属加载模型 / 外部契约变更 ⇒ 须 ADR 修订且逐条经用户确认**（`AGENTS.md`「ADR 逐条确认」）。
  - 影响面：`INTEG-020t` 依赖 += 新任务；`QEMU-048m` 关联任务 += 新任务；M5 任务数 +1；可能需 `check-interface` 断言更新。
- **B（调整 M5 门槛正向为 raw-bin 组合，保持现状）**：正向 = 「bootrom（`-bios`）+ raw-bin 应用经 `-semihosting`」。
  - 与 `R1`「并存」的关系：`R1` 并存**本就不含「组合」**语义 ⇒ 门槛不应要求组合 ⇒ **与 `R1` 自洽、无需改 ADR/组件**。
  - 代价：改门槛口径（`milestones.md` M5 段 + `INTEG-019k` 裁定 9 + 本任务书「输出 1」/「验收 1」）——**属规范/门槛变更 ⇒ 须用户裁定**。
  - 损失：「多 TU ELF」在 M5 门槛正向**不再被 E2E 覆盖**（多 TU ELF 仅由 M4 `test-elf` 覆盖，**不带** semihosting/bootrom）。
- **C（其它）**：**C1（并入本任务）**——把扩表 + 组合语义并入 `INTEG-020t`；本任务已重（E2E+harness+门控+lit+`make check` 收口），再叠组件补丁/组合语义/重构建 ⇒ 违反 Do-One-Thing、增大阻塞面 ⇒ **不推荐**。**C2（仅扩 `dadao_load_regions[]`+RAM@0，不定义组合）**——使路径 A 的 ELF 段可链进 RAM@0，但**仍无 bootrom** ⇒ 门槛正向「bootrom」仍缺，组合缺口**只解一半** ⇒ **不推荐作最终方案**。

**（3）建议（**待用户裁定**，架构师不擅自定）**

- **倾向 A**（若用户确认门槛正向按字面耦合读）：唯一能同时满足「bootrom」+「单/多 TU ELF」且**保留 `R1` 并存**（新增第三条组合路径，不删路径 A/B）的方案；与门控收口（`INTEG-020t`）解耦，合 Do-One-Thing。**但须先由用户裁定「是否承认『`-bios`+ELF』为门槛前置」，并逐条确认组合加载语义的 ADR 决策**，据此才可建任务 / 改 ADR。
- **次选 B**（若用户接受 M5 门槛正向不含组合、且「多 TU ELF」不在 M5 门槛 E2E 覆盖）：最小改动、零组件补丁、零回归风险，但降低门槛正向覆盖度。
- **本评估**：只写评估与选项；**未改任务范围、未动 `spec/`、未建新任务、未立 ADR**——均**待用户裁定后再行**。

#### architect M5 范围简化落纸（2026-10-08，用户裁定；只追加）

**背景**：上「architect 前置风险评估」（`QEMU-047t` 遗留）判「`-bios`+ELF 组合缺口」为**可能 M5 门槛前置**、倾向选项 A，**待用户裁定**。用户本轮就此裁定 → **M5 范围简化**（口径与上评估**选项 B** 一致：M5 门槛正向改为 bootrom + bin，与 `ADR-0004 R1`「并存」自洽；组合移 M6）。

**用户原话（逐字落盘；`AGENTS.md`「用户裁定落盘」/`lessons §7.3`）**：

> 「确实，这是两个分开的事情，用bios的时候，直接接bin，也就是objdump后的测试程序；而用elf的时候，则不需要bootrom，只需要semihosting即可。我们简化一下M5本身的任务目标，只做bootrom+bin的情况；elf加载放在M6，与完整LLVM的任务一起进行；你觉得呢」

**四条理解（主会话转达；architect 核对：与原话一致，无出入）**：

1. **M5 门槛正向**改为：`-bios <bootrom>` + **bin 应用**经 `-semihosting`（console 捕获 + `SYS_EXIT` 码）；原「单/多 TU ELF」用例**移 M6**。
2. **M4 既有 `test-elf`（path A：ELF、不用 bootrom）保留**为**不回归项**（不撤、不改）。
3. **`-bios`+ELF 组合 / ELF 加载器扩展（`dadao_load_regions[]`+RAM@0）/ 组合入口语义 ⇒ 移 M6**；**M5 不做**；**本阶段不立 ADR**（**推迟至 M6**，现只登记待办 + 理由）。
4. **连带**：`TESTCASES-033t` 改以 **bin 形态**承载；`TESTCASES-034t` 口径不变；`QEMU-049t` 挂到 `QEMU-047t` 的「ELF loader 未含 RAM@0」前置风险**改挂 M6**；`RAM@0` **step2（旧向量迁移）随 M6**。

**本任务受影响落点（已改）**：接口规范「门槛」/输出 1、验收 1——正向由「bootrom + 单/多 TU ELF」→「bootrom（`-bios`）+ **bin**」；**M4 `test-elf`（path A）仍为不回归项**（验收 4/6 不变）。

**ADR 推迟至 M6**：**本任务不涉组合 ADR**——「`-bios`+ELF 组合」加载/入口语义属加载模型/外部契约，**ADR 决策推迟至 M6**（`ISS-168`）；**M5 阶段不立 ADR**。

**未改范围**：本轮**未动 `spec/`**（本文件亦无 `spec/` 改动）；上「architect 前置风险评估」为**历史记录，保留不改**（只追加本节）。

#### 主会话判定落纸（architect，2026-10-08，只追加）

**背景**：`TESTCASES-033t` 审阅记录「下发前预检修订」末「**供裁定**」第 3 项登记——本任务输出 1 曾举 `run_semihost_e2e.py` 为例，与 `TESTCASES-033t` 产出的 `tools/integ/run_m5_e2e.py` 重复。主会话本轮**判定**：**去重、复用 `run_m5_e2e.py`**（属去重、非新增范围）。

**判定 3（`tools/integ/` 驱动复用）— 已落纸**

- **判定原话（主会话）**：「`INTEG-020t` 的输出 1 若举 `run_semihost_e2e.py` ⇒ 改为**复用 `tools/integ/run_m5_e2e.py`**（**只追加/最小改**，并在其审阅记录说明依据）。」
- **依据**：`run_m5_e2e.py` 由 `TESTCASES-033t` 产出（读 m5 清单 → 自有工具链编 bin → `qemu -bios <bootrom> -kernel <bin> -semihosting-config …` → 逐例比对 → `--inject` 反例自检）；本任务职责 = `make test-semihost` 接线 + harness stdio 捕获 + 门控收口 ⇒ **在其上追加/最小改**即可（DRY），**不另建 `run_semihost_e2e.py`**。
- **改法**：输出 1 的「（如 `run_semihost_e2e.py`）」→「（**复用 `tools/integ/run_m5_e2e.py`**〔`TESTCASES-033t` 产出〕，**只追加/最小改**，**不另建 `run_semihost_e2e.py`**）」。

**边界**：本轮仅改**本任务书**（输出 1 + 本审阅记录）；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。

#### 口径全局对齐（architect，2026-10-08）

**依据**：已确认的 **`ADR-0020 D9`**——M5 权限范围只做 `cfx0/1/2/3/63`；`NUPERM/NJPERM/NSPERM/NHPERM` 属 `DADAO-12 §2.2` **PTBR 权限层、不在 M5**；**M5 可观测的权限反例 = cfx 级**：`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕。**性质 = 与既定决策的一致性修正，非新增范围**。

**逐处改动（本文件）**：

1. 接口规范「门槛」组成 ②（:18）：`未授权模式 ⇒ NUPERM/NJPERM/NSPERM/NHPERM` → **cfx 级 `ILLI`/`CFXREG`**（保留 `NUPERM…` 出处说明）。
2. 验收标准 2「权限反例」（:40）：同口径改（cfx 级 `ILLI`/`CFXREG` + 保留 `NUPERM…` 出处说明）。

**边界**：本轮仅改本任务书上述 2 处 + 本审阅记录；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。
