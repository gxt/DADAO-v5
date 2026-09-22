# INFRA-012t: spec drift 检查

**模块**：infra
**项目里程碑**：M1
**依赖**：`SPEC-010t`（spec 冻结）
**状态**：待开始

## 预检订正（2026-09-21，下发前，含用户裁定）

> 本节优先级高于下文旧文本；冲突时以本节为准。

**P1 — 枚举 `contract-*.md` 时排除 `contract-authoring.md`**（用户裁定）：
- 实测 `contract-*.md` 有 **4 个**，其中 **`contract-authoring.md` 无任何来源头**（它是**合约编写规范/模板**，非合约）⇒ fail-closed 检查器必然对它 ERROR ✗
- **处置**：脚本内置**显式排除名单**（当前 = `contract-authoring.md`），并在报告中**注明被排除的文件与理由**；其余 **3 个**（`contract-isa.md`/`contract-abi.md`/`contract-elf.md`）**强制分类**，未知/缺失来源 → ERROR
- **不得**用宽泛模式（如「无 `> **版本**` 就跳过」）替代显式名单 ✗（那会退化为 fail-open）

**P2 — ADR 状态按中文形态解析**（用户裁定）：
- 实测 12 个 ADR 用 **`**状态**：Accepted`**（中文）✓；**仓库无** `Status: Accepted` 英文形态 ✗ ⇒ 任务书旧文「`Status: Accepted`」不适用
- **处置**：解析 `**状态**：Accepted`（建议兼容英文 `Status: Accepted` 作防御）；**非 Accepted** → ERROR（实测 12 个中 **11 个** Accepted，1 个非 Accepted ⇒ 若某合约引用该 ADR 则应报错）

**P3 — 版本表映射须显式定义**：
- README 版本表组件名 = `SimRISC` / `AEE / ABI` / `SEE / SBI` / `HEE / HBI` ✓；合约头引用的 spec 文件名 = `SimRISC-00` / `DADAO-21` / `DADAO-11` … ✗（命名不同）
- 实测：`contract-isa.md` `> **版本：0.5.3**` ↔ `SimRISC 0.5.3` ✓；`contract-abi.md` `> **版本：0.9.2**` ↔ `AEE / ABI 0.9.2` ✓
- ⇒ 脚本须**显式定义映射**（如 `SimRISC-0x`→`SimRISC`、`DADAO-11/21`→`AEE / ABI`、`DADAO-12/22`→`SEE / SBI`、`DADAO-13/23`→`HEE / HBI`），并在报告中给出每个合约的映射依据；**不得**靠模糊匹配

**P4 — `make check` 现红（须知悉）**：
- 当前 `make check` **因 `ISS-056`（`fence`）为红** ✓（见 `docs/issues.yaml`）⇒ 本任务把 `check-spec-drift` 接入 `make check` 后，红因可能**叠加** ⇒ 完成区须**分别说明**「drift check 自身是否 PASS」与「`make check` 整体状态及红因构成」，**不得**把既有红因误记为本任务引入 ✗

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `README.md`（当前版本号表）
  - `.tao/knowledge/contract-*.md`（被检查对象）
  - `.tao/knowledge/adr-*.md`（ADR-sourced 合约的来源）
- 输出：`tools/infra/check_spec_drift.py`（fail-closed 的规格漂移检查）
- 约束：
  - 脚本不联网，只读本地文件
  - 须通过 `python3 -m compileall tools`
  - 接入 `make check`
  - 至少 4 个负测试：版本不匹配、来源缺失、来源格式错误、未知 ADR

## 背景（完整）

### 目标

fail-closed 校验所有合约的来源与 `README.md` 版本表一致；并在可用的构建入口（`make check`）中调用。

### 设计理由

drift checker 必须 fail-closed：缺失/格式错误的来源不能静默 PASS，否则只能证明「匹配到的来源一致」，不能证明「所有合约 provenance 均已冻结」。

### 关键概念 / 数据

**`check_spec_drift.py` 行为规则（fail-closed）**：

- 枚举 `.tao/knowledge/contract-*.md`，每个文件必须被分类为以下之一，否则 ERROR：
  - **spec-sourced**：含 `> **版本：X.Y.Z**` 头 → 版本须与 `README.md` 版本表对应项一致；且引用的 `spec/` 文件须真实存在
  - **ADR-sourced**：来源标注引用 `adr-000N-*.md` → 该 ADR 文件须存在且 `Status: Accepted`
- 缺来源、来源格式损坏、未知 ADR 来源 → ERROR 并非零退出
- 全部通过 → 输出 `spec drift check: PASS` 并返回 0
- 至少包含 4 个负测试：版本不匹配、来源缺失、来源格式错误、未知 ADR

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-004b-spec-freeze.md`（drift checker 部分）
- DADAO-0628：`scripts/check_wiki_drift.py`（逻辑参考，v5 自实现；v5 无 wiki commit，改用版本号/文件存在性）

## 交付物

- `tools/infra/check_spec_drift.py`：fail-closed 规格漂移检查（版本/ADR 分类、负测试）
- 完成区附真实 stdout 与负测试证据

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **来源标识**：0628 用 Wiki commit SHA；v5 的合约以 `spec/` 文档版本号与文件存在性为 provenance，版本表在 `README.md`。不能照抄 SHA 匹配逻辑。
2. **脚本命名**：`check_wiki_drift.py` → `check_spec_drift.py`（v5 无 wiki）。
3. **脚本目录**：`scripts/` → `tools/infra/`。
4. **构建入口**：v5 接入 `make check`（Makefile 由 `INFRA-006t` 提供）。

## 已知坑 / 结论

1. **P1 drift checker fail-open**：缺失/损坏/未知来源静默跳过 → 只证明「匹配到的一致」。必须枚举每个 `contract-*.md` 并强制分类，未知/缺失来源必须失败，且加负测试。
2. **v5 无 `manifests/spec.lock.toml`**：版本表在 `README.md`。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-004b-spec-freeze.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_wiki_drift.py`
- 本项目：`README.md`（规范版本表）、`.tao/knowledge/contract-isa.md`（版本头示例）、`Makefile`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `tools/infra/check_spec_drift.py` 存在，fail-closed：枚举所有 `.tao/knowledge/contract-*.md` 并强制分类
2. 脚本对「版本不匹配 / 来源缺失 / 来源格式错误 / 未知 ADR」四类均非零退出（负测试齐全）
3. 脚本正常运行输出 `spec drift check: PASS` 并返回 0；`python3 -m compileall tools` 通过
4. 接入 `make check`
5. 完成区粘贴真实 stdout，数字来自实跑

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
