# SPEC-010t: Spec 冻结（status/impact-matrix/CI 检查）

**模块**：spec
**依赖**：`SPEC-006t`、`SPEC-007t`、`SPEC-008t`、`SPEC-009t`（间接依赖 `SPEC-002t`/`SPEC-003t` 均须 Accepted）

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `manifests/spec.lock.toml`（当前 status/commit/versions/foundation_included）
  - 已 Accepted 的 `.tao/knowledge/contract-*.md`、`adr-*.md`
  - `.tao/knowledge/contract-isa.md`（版本头格式示例）
- 输出：
  - `docs/impact-matrix.md`（规格来源 → 合约/文件 → 下游实现目标）
  - `scripts/check_spec_drift.py`（fail-closed 的规格漂移检查）
  - `manifests/spec.lock.toml`（`status = "frozen"`；`foundation_included` 补入本轮合约）
- 约束：
  - 冻结前所有 authority artifact（SPEC-002t/003t/006t/007t/008t/009t）必须 Accepted
  - `check_spec_drift.py` 不联网，只读本地文件
  - 脚本须通过 `python3 -m compileall -q scripts`
  - impact matrix 覆盖「每个 spec 章节」，实现目标须区分 LLVM MC / LLVM CodeGen / QEMU CPU /
    QEMU machine / gem5 / Sail / vectors / harness
  - 完成后不自行 commit

## 背景（完整）

### 目标

执行规格冻结动作：
1. 确认 `manifests/spec.lock.toml` 的 `status = "frozen"`（v5 该文件已为 frozen，须核对并补齐
   `foundation_included`/versions）
2. 新建 `docs/impact-matrix.md`，记录 spec/ADR/合约章节与下游实现的依赖映射
3. 新建 `scripts/check_spec_drift.py`，fail-closed 校验所有合约的来源与 `spec.lock.toml` 一致；
   并在可用的构建入口中调用（v5 尚无 Makefile，见差异）

### 设计理由

- 冻结是「所有 authority artifact 均已 Accepted」后的最后动作，不能与 contract review 并行自我批准。
- impact matrix 用于 spec/ADR 变更时快速评估影响范围；必须逐节覆盖，否则无实用价值。
- drift checker 必须 fail-closed：缺失/格式错误的来源不能静默 PASS，否则只能证明「匹配到的来源
  一致」，不能证明「所有合约 provenance 均已冻结」。

### 关键概念 / 数据

**impact-matrix 格式**：三列表格 `规格来源 | 依赖此节的合约/文件 | 下游实现目标`。
至少覆盖：

- ISA（SimRISC-00..04）：寄存器模型/编码/标量/地址内存/控制流/浮点/系统，对应 `contract-isa.md` 各节
- ABI（DADAO-11 AEE、DADAO-21 ABI）：寄存器角色/数据表示/传参/返回值/栈帧，对应 `contract-abi.md`
- ELF：`contract-elf.md` §1–§6 对应 ADR-0003 §D1–§D5
- Test machine：ADR-0004 §D1–§D6 对应 QEMU machine / harness
- 实现目标区分：LLVM MC、LLVM CodeGen、QEMU CPU、QEMU machine、gem5、Sail、vectors、harness

**check_spec_drift.py 行为规则（fail-closed）**：

- 枚举 `.tao/knowledge/contract-*.md`，每个文件必须被分类为以下之一，否则 ERROR：
  - **spec-sourced**：含 `> **版本：X.Y.Z**` 头 → 版本须与 `spec.lock.toml [versions]` 对应项一致；
    且引用的 `spec/` 文件须真实存在
  - **ADR-sourced**：来源标注引用 `adr-000N-*.md` → 该 ADR 文件须存在且 `Status: Accepted`
- 缺来源、来源格式损坏、未知 ADR 来源 → ERROR 并非零退出
- 全部通过 → 输出 `spec drift check: PASS` 并返回 0
- 风格参考 DADAO-0628 的 `scripts/check_wiki_drift.py`（v5 无 wiki commit，改用版本号/文件存在性）
- 至少包含 4 个负测试：版本不匹配、来源缺失、来源格式错误、未知 ADR

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-004b-spec-freeze.md`（完整转述；含 3 轮 Architecture Review）
- DADAO-0628：`scripts/check_wiki_drift.py`（drift checker 模板）
- DADAO-0628：`manifests/spec.lock.toml`（status 字段冻结示例）
- DADAO-0628：`code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）

## 交付物

| 文件 | 说明 |
|------|------|
| `docs/impact-matrix.md` | 规格来源 → 合约/文件 → 下游实现目标的三列矩阵，逐节覆盖 |
| `scripts/check_spec_drift.py` | fail-closed 规格漂移检查（版本/ADR 分类、负测试） |
| `manifests/spec.lock.toml` | `status = "frozen"`；`foundation_included` 补入本轮冻结合约范围 |

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **来源标识**：DADAO-0628 用 Wiki commit SHA（`**Source**: Wiki commit <sha>`）；v5 的合约以
   `spec/` 文档版本号（SimRISC 0.5.3 / ABI 0.9.2 等）与文件存在性为 provenance，
   `spec.lock.toml` 记录 `commit = 9e69b55d…` 与 `[versions]`。drift checker 须据此改造，
   不能照抄 SHA 匹配逻辑。
2. **spec.lock 状态**：v5 的 `manifests/spec.lock.toml` 当前已为 `status = "frozen"`；
   本任务的冻结动作是**核对**其 status/versions/foundation_included 与已 Accepted 合约一致，
   并在合约全部 Accepted 后确认冻结边界，而非从 candidate 翻转。
3. **构建入口**：v5 尚无 `Makefile`/CI（构建编排由 infra 模块负责）。
   本任务交付独立可运行的 `scripts/check_spec_drift.py` 并给出 gate 命令；
   待 infra 模块引入构建编排时再接入 `make check`，不在本任务新建 Makefile。
4. **脚本命名**：`check_wiki_drift.py` → `check_spec_drift.py`（v5 无 wiki）。
5. **impact matrix 行集**：须按 v5 的 `contract-isa.md`/`contract-abi.md`/`contract-elf.md` 与
   ADR-0003/0004 的真实章节重建，不能照抄 0.4.1 的章节号（0.4.1 首版矩阵有多处章节号错误）。

## 已知坑 / 结论

摘自 DL-004b 三轮 Architecture Review：

1. **P0 在 Candidate ADR/contract 上提前设置 frozen**：必须等所有 prerequisite review 通过后
   最后执行 freeze commit，不能与 contract review 并行自我批准。
2. **P0 impact matrix 章节映射错误且不完整**：0.4.1 首版 8 行多处事实错误（章节号错、遗漏大量节）；
   必须逐节覆盖 ISA/ABI/ELF/ADR，且实现目标区分组件。
3. **P1 drift checker fail-open**：缺失/损坏/未知来源静默跳过 → 只证明「匹配到的一致」。
   必须枚举每个 `contracts/*/spec.md` 并强制分类，未知/缺失来源必须失败，且加负测试。
4. **P1 manifest 与冻结范围元数据不自洽**：`name`/`foundation_included` 须与 status/冻结范围一致，
   使用者能据此判断冻结边界。
5. **最终结论**：第三轮 Accepted（freeze gate 暂挂起，待 spec.lock.toml 最终 frozen 提交）；
   实质工作完成，所有 authority artifacts 均 Accepted 后再最终提交 frozen。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-004b-spec-freeze.md`（完整转述）
- DADAO-0628：`.work/DADAO-0628/scripts/check_wiki_drift.py`
- DADAO-0628：`.work/DADAO-0628/manifests/spec.lock.toml`
- DADAO-0628：`.work/DADAO-0628/code-agent/designs/0002-detailed-roadmap.md`（Spec Freeze 段）
- 本项目：`manifests/spec.lock.toml`、`.tao/knowledge/contract-isa.md`（版本头示例）
- 本项目：`manifests/spec.lock.toml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `docs/impact-matrix.md` 存在，逐节覆盖 ISA（SimRISC-00..04）、ABI（DADAO-11/21）、ELF、ADR-0003/0004；
   实现目标区分 LLVM MC / CodeGen / QEMU CPU / QEMU machine / gem5 / Sail / vectors / harness
2. `scripts/check_spec_drift.py` 存在，fail-closed：枚举所有 `.tao/knowledge/contract-*.md` 并强制分类
3. 脚本对「版本不匹配 / 来源缺失 / 来源格式错误 / 未知 ADR」四类均非零退出（负测试齐全）
4. 脚本正常运行输出 `spec drift check: PASS` 并返回 0；`python3 -m compileall -q scripts` 通过
5. `manifests/spec.lock.toml` `status = "frozen"`，`versions`/`foundation_included` 与已 Accepted
   合约范围一致（补入 contract-abi/contract-elf/adr-0003/adr-0004 等）
6. 冻结前所有 authority artifact 均 Accepted（SPEC-002t/003t/006t/007t/008t/009t）
7. 给出 gate 命令；若未接入 Makefile，须在完成区说明接入时机（infra 模块）
8. 不照抄 0.4.1 的章节号/矩阵行；无行号引用

## 完成区

**状态**：待开始
**Commit**：
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
