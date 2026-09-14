# SPEC-010t: Spec 冻结（impact-matrix + 冻结状态）

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-004t`、`SPEC-005t`、`SPEC-006t`、`SPEC-007t`、`SPEC-008t`、`SPEC-009t`（间接依赖 `SPEC-002t`/`SPEC-003t` 均须 Accepted）
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `README.md`（当前版本号表：规范版本 + 冻结状态）
  - 已 Accepted 的 `.tao/knowledge/contract-*.md`、`adr-*.md`
  - `.tao/knowledge/contract-isa.md`（版本头格式示例）
- 输出：
  - `docs/impact-matrix.md`（规格来源 → 合约/文件 → 下游实现目标）
  - `README.md`（冻结状态标注为 `已冻结`）
- 约束：
  - 冻结前所有 authority artifact（`SPEC-002t`~`SPEC-009t`）必须 Accepted
  - impact matrix 逐节覆盖 spec 章节；**实现目标只区分 M1 目标**：LLVM MC / QEMU CPU / QEMU machine / vectors / harness。M1 外（LLVM CodeGen、gem5、Sail）**不列为目标**（可汇总为「M1 外」或标 `Deferred`）
  - 完成后不自行 commit

> **注**：spec drift 检查（`check_spec_drift.py`）属**通用 CI 检查**，已拆至 `INFRA-012t`，不在本任务。

## 背景（完整）

### 目标

执行规格冻结动作：
1. 核对 `README.md` 的规范版本表与已 Accepted 合约一致，并把冻结状态标注为 `已冻结`
2. 新建 `docs/impact-matrix.md`，记录 spec/ADR/合约章节与下游实现的依赖映射

### 设计理由

- 冻结是「所有 authority artifact 均已 Accepted」后的最后动作，不能与 contract review 并行自我批准。
- impact matrix 用于 spec/ADR 变更时快速评估影响范围；必须逐节覆盖，否则无实用价值。

### 关键概念 / 数据

**impact-matrix 格式**：三列表格 `规格来源 | 依赖此节的合约/文件 | 下游实现目标`。
至少覆盖：

- ISA（SimRISC-00..04）：寄存器模型/编码/标量/地址内存/控制流/系统，对应 `contract-isa.md` 各节
- ABI（DADAO-11 AEE、DADAO-21 ABI）：寄存器角色/数据表示/传参/返回值/栈帧，对应 `contract-abi.md`
- ELF：`contract-elf.md` §1–§6 对应 ADR-0003 §D1–§D5
- Test machine：ADR-0004 §D1–§D6 对应 QEMU machine / harness
- 实现目标区分（**M1**）：LLVM MC、QEMU CPU、QEMU machine、vectors、harness；M1 外（LLVM CodeGen、gem5、Sail）不列为目标（可汇总为「M1 外」或标 `Deferred`）

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-004b-spec-freeze.md`（impact matrix / 冻结部分）
- DADAO-0628：`manifests/spec.lock.toml`（status 字段冻结示例）
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `docs/impact-matrix.md` | 规格来源 → 合约/文件 → 下游实现目标的三列矩阵，逐节覆盖 |
| `README.md` | 规范版本表核对无误，冻结状态标注为 `已冻结` |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **冻结状态**：v5 不使用 `manifests/spec.lock.toml`（其 commit 锁随仓库更新而失效）；本任务的冻结动作是**核对** `README.md` 版本表与已 Accepted 合约一致，并在合约全部 Accepted 后把冻结状态标注为 `已冻结`。
2. **构建入口**：v5 接入 `make check`（Makefile 由 `INFRA-006t` 提供）；drift 检查归 `INFRA-012t`。
3. **impact matrix 行集**：须按 v5 的 `contract-isa.md`/`contract-abi.md`/`contract-elf.md` 与 ADR-0003/0004 的真实章节重建，不能照抄 0.4.1 的章节号。

## 已知坑 / 结论

摘自 DL-004b 三轮 Architecture Review：

1. **P0 在 Candidate ADR/contract 上提前设置 frozen**：必须等所有 prerequisite review 通过后最后执行 freeze commit，不能与 contract review 并行自我批准。
2. **P0 impact matrix 章节映射错误且不完整**：0.4.1 首版 8 行多处事实错误（章节号错、遗漏大量节）；必须逐节覆盖 ISA/ABI/ELF/ADR，且实现目标区分组件（M1 范围）。
3. **P1 manifest 与冻结范围元数据不自洽**：`name`/`foundation_included` 须与 status/冻结范围一致，使用者能据此判断冻结边界。
4. **最终结论**：第三轮 Accepted（freeze gate 待所有 authority artifacts 均 Accepted 后把 `README.md` 冻结状态标注为 `已冻结`）。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-004b-spec-freeze.md`
- DADAO-0628：`.work/DADAO-0628/manifests/spec.lock.toml`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）
- 本项目：`README.md`（规范版本表）、`.tao/knowledge/contract-isa.md`（版本头示例）
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `docs/impact-matrix.md` 存在，逐节覆盖 ISA（SimRISC-00..04）、ABI（DADAO-11/21）、ELF、ADR-0003/0004；**实现目标只区分 M1 目标**（LLVM MC / QEMU CPU / QEMU machine / vectors / harness），M1 外（LLVM CodeGen / gem5 / Sail）不列为目标
2. `README.md` 规范版本表与已 Accepted 合约一致，冻结状态标注为 `已冻结`
3. 冻结前所有 authority artifact 均 Accepted（`SPEC-002t`~`SPEC-009t`）
4. 不照抄 0.4.1 的章节号/矩阵行；无行号引用
5. 未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

（待填写）

#### 第 1 轮 reviewer 验收

（待填写）
