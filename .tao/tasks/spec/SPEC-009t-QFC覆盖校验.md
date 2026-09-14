# SPEC-009t: QFC 覆盖校验

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-003t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `spec/SimRISC-00-指令系统设计.md` 的 SimRISC QFC 表（主表 + MISC 子表）——opcode 布局权威来源
  - `contracts/opcodes.yaml`（256 条记录，mask/value/op/format）
- 输出：`tools/spec/check_qfc_coverage.py`：QFC 表 ↔ `contracts/opcodes.yaml` 双向比对（lint，informational，exit 0）
- 约束：
  - 只读 yaml/规范，不改任何数据文件
  - QFC 解析以 v5 `spec/SimRISC-00` 的实际表结构为准
  - 脚本放 `tools/spec/`（与 `validate_encoding.py` 一致）

## 背景（完整）

### 目标

补齐 lint 缺口：规范 QFC 表是 opcode 布局的权威来源，但从未与 `contracts/opcodes.yaml` 做双向比对；若 `opcodes.yaml` 漏填/错填某 op/ha，当前检查无法发现。

### 设计理由

翻译链 `spec → contracts/opcodes.yaml → (LLVM/QEMU) → 测试` 中最弱环是「规范表 ↔ 机器可读编码表」，须用独立 oracle 机械校验，避免人工遗漏。

### 关键概念 / 数据

**QFC 表结构（0.4.1 形态，供对照）**：`SimRISC-00` 有主表（行头 `RRRR-Rxxx`、列头 `xxxx-xCCC`）+ MISC 子表（行头 `RRR-xxx`、列头 `xxx-CCC`）。

- 主表解码：`bits[7:3]=int("RRRR-R",2)`、`bits[2:0]=int("CCC",2)`、`op=(bits[7:3]<<3)|bits[2:0]`
- 子表解码：`ha[5:3]=int("RRR",2)`、`ha[2:0]=int("CCC",2)`、`ha=(ha[5:3]<<3)|ha[2:0]`，`op` 由所属子表固定
- 单元格：空白 → reserved（UNDI）；`MISC-*` → 子表指针；`{name}-{format}` → 一条具体指令

**比对逻辑**：

1. 解析 QFC → `(op, ha_or_None)` 集合 `qfc_opids`
2. 读 `contracts/opcodes.yaml` → `(op, str(ha))` 集合 `yaml_opids`
3. 报告 `qfc_opids - yaml_opids`（QFC 有但 yaml 缺）与 `yaml_opids - qfc_opids`（yaml 有但 QFC 不含，需排除 M1 scope 外项）
4. 数量汇总；exit 0（lint 警告不阻断）

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-022a-qfc-lit-oracle.md`（QFC 部分）
- DADAO-0628：`scripts/check_qfc_coverage.py`（形态参考，禁止复制正文）

## 交付物

- `tools/spec/check_qfc_coverage.py`：QFC 表 ↔ `contracts/opcodes.yaml` 双向覆盖校验
- 完成区附脚本真实 stdout（含 M1 scope 外差异的分类说明）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **QFC 表结构重构**：0.5.3 主表行 `0000-0xxx`/`0100-0xxx` 指向 `MISC-AMO`/`MISC-octa`/`MISC-tetra`/`MISC-wyde`/`MISC-byte`/`MISC-RF` 六类子表；**没有 0.4.1 的 `MISC-Norm` 子表**。解析器必须按 v5 实际表结构重写。
2. **规范来源改为 `spec/`**：v5 读 `spec/SimRISC-00-指令系统设计.md`。
3. **编码表路径**：`contracts/opcodes.yaml` → `contracts/opcodes.yaml`。
4. **脚本目录**：`verif/` → `tools/spec/`。
5. **M1 scope 外差异**：须按 0.5.3 的 M1 范围重新分类，不得把 M1 内差异当正常。

## 已知坑 / 结论

1. **QFC 双向比对零误报**：结果须可解释（差异项全为 M1 排除项或明确分类）。
2. **`check_qfc_coverage.py` 只读不阻断**（informational，exit 0）。
3. **QFC 单元格区分 reserved 与 MISC 指针**：空白 = UNDI 保留；`MISC-*` = 子表指针，不能当具体指令。
4. **`opcodes.yaml` 自检前提**：其 mask/value 唯一性由 `SPEC-003t`/`validate_encoding.py` 保证。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-022a-qfc-lit-oracle.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_qfc_coverage.py`
- 本项目：`spec/SimRISC-00-指令系统设计.md`、`contracts/opcodes.yaml`、`tools/spec/validate_encoding.py`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 tools/spec/check_qfc_coverage.py` 可运行，输出双向差异与数量汇总，exit 0；差异项逐条分类（M1 内/外）
2. 脚本不修改任何 yaml 文件（只读）
3. QFC 解析覆盖 v5 主表 + 全部 MISC 子表（含 octa/tetra/wyde/byte/RF/AMO）
4. 完成区粘贴真实 stdout，不转述

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
