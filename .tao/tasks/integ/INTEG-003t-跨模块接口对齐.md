# INTEG-003t: 跨模块接口对齐核对

**模块**：integ
**项目里程碑**：M1
**依赖**：`LLVM-013m`、`QEMU-021m`、`SPEC-011m`、`TESTCASES-012m`（原写 `TESTCASES-010m`，该里程碑已更名为 `012m`）
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/adr-0003-object-abi.md`、`adr-0004-test-machine.md`（跨模块接口契约）
  - `.tao/knowledge/contract-elf.md`、`contract-abi.md`、`contract-isa.md`
  - `contracts/opcodes.yaml`、`tests/vectors/**`（schema）
  - `components/llvm-project/patches/*`、`components/qemu/patches/*`（两侧实现）
- 输出：接口对齐核对清单/脚本（落在 `tests/e2e/` 或 `tools/integ/`），逐条给出「一致 / 不一致 + 证据」
- 约束：
  - **只核对、不修改**两侧实现或合约（发现不一致则报告，走变更流程）
  - 核对项须**机械可判定**（字段/格式/取值比对），不靠人眼
  - 期望值来自 ADR/合约，**不从实现反推**
  - 完成后不自行 commit

## 背景（完整）

### 目标

机械核对本项目的**跨模块接口契约**是否两侧一致，防止「单测各自过、组合挂」：

1. **LLVM MC ELF emitter ↔ QEMU loader**：ELF 头字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`e_flags`/`EI_OSABI`）、`e_flags[7:0]=1`、`.o → objcopy .text → flat` 流水线。
2. **ADR-0003 ↔ ADR-0004**：flat binary 格式、RAM 入口、`e_entry` 不参与、双镜像（`-bios` + `-kernel`）。
3. **`testcases` 向量 schema ↔ QEMU harness**：harness 消费的 YAML 字段（`class`/`input_state`/`expected_state`/`expected_fault`）与向量 schema 一致。
4. **`contracts/opcodes.yaml` ↔ LLVM/QEMU 两侧实现**：编码/助记符两侧一致（可由各自模块的 lit/向量间接覆盖，此处做**交叉**核对）。

### 设计理由

跨模块接口若只靠「各自测试」无法覆盖：单侧字段/格式改了、另一侧没跟上，双方单测都绿、组合才暴露。集成层须有**静态**核对把接口契约变成机械检查。

### 关键概念 / 数据

- 核对项组织为清单（每项：接口、来源 ADR/合约、两侧取值、判定）。
- 机械可判定项（字段值、格式常量、schema 字段名）用脚本核对；无法机械判定的项须说明并给人工证据。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-033a-mc-qemu-e2e-smoke.md`（接口相关部分）
- 本项目：ADR-0003/0004、`contract-elf.md`/`contract-abi.md`/`contract-isa.md`、`contracts/opcodes.yaml`

## 交付物

- 跨模块接口对齐核对清单（含每项的「一致/不一致 + 证据」）
- 可复跑的核对脚本（对机械可判定项）
- 完成区附真实核对输出

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **接口契约来源**：v5 以 ADR-0003/0004 与 v5 合约为准，不照抄 0628。
2. **内存图/exit 协议**：以 v5 ADR-0004（核内地址空间模型、spec cause 派生 fault 码）为准。
3. **opcodes**：v5 `contracts/opcodes.yaml`（0.5.3 编码）。

## 已知坑 / 结论

1. **只核对不改**：发现不一致只报告，改动走对应模块的变更流程。
2. **期望值独立**：接口期望值来自 ADR/合约，不从实现反推。
3. **机械优先**：能脚本化的项不靠人眼；无法机械化的项须显式说明。
4. **与 `INTEG-002t` 分工**：本任务做**静态**核对；`INTEG-002t` 做**动态** E2E。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-033a-mc-qemu-e2e-smoke.md`
- 本项目：`.tao/knowledge/adr-0003-object-abi.md`、`adr-0004-test-machine.md`、`contract-elf.md`、`contracts/opcodes.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. 核对清单覆盖上述 4 类接口，逐项有「一致/不一致 + 证据」
2. 机械可判定项有可复跑脚本；运行输出真实
3. 未修改两侧实现/合约（diff 确认）
4. 完成区粘贴真实核对输出，数字来自实跑
5. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
