# 里程碑 TDD 规范

> **状态**：生效（2026-10-06）｜**上位依据**：无——属**工程过程规范**（可逆、单模块、无外部契约，不命中 ADR 判据，见 `spec/Process-03`）。
> **首个实例**：**M4**（ELF 文件支持 + LLD 链接 + 汇编器遗留收口）。
> **关键词**：本规范用「**必须**（MUST）／**应当**（SHOULD）／**可以**（MAY）」表达规范性等级。无专用机器 checker；验收依赖各任务的一键证据与 `make check`。

---

## 1. 原则（MUST）

自 **M4 起，每个里程碑采用测试驱动开发（TDD）**：**先立测试向量与门控，再实现**。任务书的「验收标准」**必须**引用这些向量/门控（而非事后补测）。

## 2. 三层测试向量

| 层 | 测什么 | 期望值来源 | 定位 |
|---|---|---|---|
| **L1 编码/汇编器（MC）** | 汇编 ↔ 字节：伪指令展开、指导符、汇编器选项、诊断、编码往返 | ISA 编码表（`contracts/opcodes.yaml`） | 独立 oracle |
| **L2 CodeGen（结构）** | IR → 指令选择/寄存器/帧/段布局的**结构断言**（MIR/`.s`） | 手写 CHECK | **仅锁回归、不证语义** |
| **L3 执行（语义）** | IR → 代码 → **运行** → 结果比对 | **独立 oracle**（host 侧按 IR/spec 语义派生） | **新 ISA codegen 正确性的唯一判据** |

> **关键**：新 ISA 的 codegen「完成」只能由 **L3 + 独立 oracle** 证成；L2 的「IR + 汇编快照」只防回归（上游 `update_llc_test_checks.py` 的 autogen 断言即属 L2，**不得**当作语义真值）。

## 3. 规模原则（MUST）

**「一能力一向量」**：向量规模**必须**与能力规模**成正比**；**不得**超前建设大套件（测尚不存在的能力）。**应当**由每个任务自带其对应的少数向量/门控。

## 4. 移植原则（MUST/SHOULD）

- **可以**借鉴上游同类 target 的**测试结构**（用例形态、RUN/CHECK 组织）；
- 期望值**必须独立派生自 `spec/`**；**不得**从实现（`llc`/`qemu`）反推（呼应 `AGENTS.md`「Independent oracle」）；
- **应当**手写少量、可审计的用例；**不得**批量迁移上游 IR/向量而不逐条复核。

## 5. 反例门控（MUST）

每条向量/门控**必须能对注入的反例失败**（呼应 `AGENTS.md`「验证脚本反例门控」）；只会报 PASS 的向量不是证据。

## 6. 落点（SHOULD）

- **L1**：`tests/llvm/lit/MC/DADAO/`（必要时进 patch 的 `llvm/test/MC/DADAO/`）；
- **L2**：`tests/llvm/lit/CodeGen/DADAO/` 或 patch 的 `llvm/test/CodeGen/DADAO/`；MIR 用例；
- **L3**：`tests/llvm/codegen/`（M3）+ `tests/llvm/codegen/m4/`（M4 独立清单）+ `tools/integ/` + `tools/testcases/`；独立 oracle 脚本**随产物入库**；
- **其它落点**：QEMU 组件测试 `tests/qemu/`；E2E 驱动 `tests/e2e/lit/`；共享 harness `tests/scripts/`；契约向量 `tests/vectors/isa/`。

**测试运行产物落点与留存（用户 2026-10-06 裁定；自 M5 起生效）**：

> **适用范围**：本段只约束**测试运行产物**（跑测试产生的中间物/输出）；上列 L1/L2/L3 与「其它落点」是**测试源文件/向量**的落点，二者不同，源文件**仍随产物入库**。
> **规范等级**：本段为**用户裁定口径**——默认落点、退让判据、定位机制为 **MUST**；「不强制留存」为 **可以**（MAY）。（本节标题标 SHOULD 指上列 L1/L2/L3 示例落点。）

- **默认落 `.dadao/tests/`**：测试**运行产物默认**统一落 **`.dadao/tests/`**（`ADR-0016 D6`）——如 `.dadao/tests/codegen-e2e`、`.dadao/tests/elf-e2e`、`.dadao/tests/lit-output/<name>`。
- **退让判据 = 「能否用配置选项解决」**：仅当**用配置选项**（如 lit 的 `test_exec_root`、脚本的 `--work-dir`）**仍**「**难以放进 `.dadao/`**」时，才退到**该模块目录下**；**能配置解决的一律必须放 `.dadao/`**（「能配置解决」**不算**「难」）。**不得**以「历史上落在模块目录」为由保留旧落点。
- **落点须经定位机制解析、禁硬编码**：落点路径**必须**经 `manifests/install-dirs.lock.toml`（`test_artifacts_dir`）与 `tools/infra/paths.py` 解析（`ADR-0016 D7/D8`）；Makefile 与 Python 脚本**禁止硬编码** `.dadao/tests/` 字面路径。
- **`.work/log`/`.work/evidence` 不受本规则约束**：二者是**日志/证据留存区，不算「生成物」**，落点**不动**（仍为 `.work/log`、`.work/evidence`）。
- **生效时点：自 M5 起**：**M4 及以前**已完成/在做的测试落点**一律不动**；**自 M5 起**按本规则执行（能配置解决 ⇒ 必进 `.dadao/`）。
- **不强制留存**：测试运行产物**可以自清/不保留**；需要检视时保留、不需要时清理，均合规。

## 7. 与其它规范的关系

- `Process-02`（合约）：**期望值的来源**（spec-first）；
- `Process-03`（ADR）：涉及架构决策时先行；
- `Process-04`（归档）：里程碑收尾；
- `AGENTS.md`：Independent oracle、验证脚本反例门控、数据/期望值类任务附加要求。
