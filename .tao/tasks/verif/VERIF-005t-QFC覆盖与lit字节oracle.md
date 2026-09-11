# VERIF-005t: QFC 覆盖校验 + lit 字节 oracle

**模块**：verif
**项目里程碑**：M1
**依赖**：`SPEC-003t`、`LLVM-009t`

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `spec/SimRISC-00-指令系统设计.md` 的 SimRISC QFC 表（主表 + MISC 子表）——opcode 布局权威来源
  - `verif/opcodes.yaml`（256 条记录，mask/value/op/format）
  - `tests/lit/MC/Dadao/*.s` 的 `# OBJ:` 行（字节级期望）
- 输出：
  - `verif/check_qfc_coverage.py`：QFC 表 ↔ `opcodes.yaml` 双向比对（lint，informational，exit 0）
  - `verif/check_lit_bytes.py`：lit `# OBJ:` 字节 ↔ `opcodes.yaml` 独立校验（真错误时 exit 1）
- 约束：
  - 两个脚本都**只读** yaml/规范，不改任何数据文件
  - `check_lit_bytes.py` 不运行 LLVM 工具（纯 Python + yaml），oracle 独立于实现
  - QFC 解析以 v5 `spec/SimRISC-00` 的实际表结构为准
  - 检查类脚本放 `verif/`（与 `validate_encoding.py` 一致）

## 背景（完整）

### 目标

补齐两条未覆盖的 lint 缺口：

- **QFC 覆盖**：规范 QFC 表是 opcode 布局的权威来源，但从未与 `opcodes.yaml` 做双向比对；若 `opcodes.yaml` 漏填/错填某 op/ha，当前检查无法发现。
- **lit 字节 oracle**：lit 文件中 `# OBJ:` 行手写了期望字节，但这些字节是否与 `opcodes.yaml` 的 mask/value 公式一致，从未有独立、常态化的验证。

### 设计理由

翻译链 `spec → opcodes.yaml → (LLVM/QEMU) → 测试` 中，最弱环是「规范表 ↔ 机器可读编码表」和「手写期望字节 ↔ 编码表」。两者都要用独立 oracle 机械校验，避免人工手算遗漏。

### 关键概念 / 数据

**QFC 表结构（0.4.1 形态，供对照）**：`SimRISC-00` 有四个 markdown 表——主表（16 行 × 8 列，行头 `RRRR-Rxxx`、列头 `xxxx-xCCC`）+ 三个 MISC 子表（`MISC-Norm` op=0x10、`MISC-RF` op=0x50、`MISC-AMO` op=0x70，子表行头 `RRR-xxx`、列头 `xxx-CCC`）。

- 主表解码：`bits[7:3]=int("RRRR-R",2)`、`bits[2:0]=int("CCC",2)`、`op=(bits[7:3]<<3)|bits[2:0]`
- 子表解码：`ha[5:3]=int("RRR",2)`、`ha[2:0]=int("CCC",2)`、`ha=(ha[5:3]<<3)|ha[2:0]`，`op` 由所属子表固定
- 单元格：空白 → reserved（UNDI）；`MISC-*` → 子表指针；`{name}-{format}` → 一条具体指令

**比对逻辑**：

1. 解析 QFC → `(op, ha_or_None)` 集合 `qfc_opids`
2. 读 `opcodes.yaml` → `(op, str(ha))` 集合 `yaml_opids`
3. 报告 `qfc_opids - yaml_opids`（QFC 有但 yaml 缺）与 `yaml_opids - qfc_opids`（yaml 有但 QFC 不含，需排除 M1 scope 外项）
4. 数量汇总；exit 0（lint 警告不阻断）

**lit 字节校验**：从每个 `.s` 提取 `# OBJ: AA BB CC DD{{.*}}mnemonic`，`word=int("AABBCCDD",16)`；遍历 `opcodes.yaml` 找 `(word & mask) == value` 的记录；无匹配 → `WARN`（真错误，exit 1）；全匹配 → `check_lit_bytes: N patterns OK`（exit 0）。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-022a-qfc-lit-oracle.md`（完整转述：背景 O-4/O-5、QFC 表结构与解码、双向比对逻辑、lit OBJ 行解析与校验、DL-011c spacer、Makefile 集成、约束、验收、完成区、代码级 Architecture Review）
- DADAO-0628：`scripts/check_qfc_coverage.py`、`scripts/check_lit_bytes.py`（形态参考，禁止复制正文）

## 交付物

- `verif/check_qfc_coverage.py`：QFC 表 ↔ `verif/opcodes.yaml` 双向覆盖校验
- `verif/check_lit_bytes.py`：lit `# OBJ:` 字节 ↔ `verif/opcodes.yaml` 独立 oracle
- 完成区附两脚本真实 stdout（含 M1 scope 外差异的分类说明）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **QFC 表结构重构**：0.5.3 主表列头/行头与子表体系改变——主表行 `0000-0xxx`/`0100-0xxx` 指向 `MISC-AMO`/`MISC-octa`/`MISC-tetra`/`MISC-wyde`/`MISC-byte`/`MISC-RF` 六类子表；**没有 0.4.1 的 `MISC-Norm` 子表**（0.5.3 的固定位宽操作改用 octa/tetra/wyde/byte 四张子表 + 主表 `0100-0xxx` 行）。解析器必须按 v5 实际表结构重写，`op`/`ha` 推导规则与 0.4.1 不同。
2. **规范来源改为 `spec/`**：0.4.1 读 DADAO-0628 的 wiki 参考（外部）；v5 **无 wiki**，读 `spec/SimRISC-00-指令系统设计.md`。
3. **编码表路径**：`tools/opcodes.yaml` → `verif/opcodes.yaml`。
4. **脚本目录**：0.4.1 放 `scripts/`；v5 放 `verif/`（与 `validate_encoding.py` 一致）。
5. **lit spacer 不重复**：0.4.1 的 `DL-011c` 给 13 个 lit 文件补 `{{.*}}`；v5 由 `LLVM-009t` 从源头内建 `{{.*}}`，故本任务**只做 oracle 校验，不改 lit 文件**（避免跨模块改动 `tests/lit/`）。
6. **lit 文件形态**：`tests/lit/MC/Dadao/*.s` 由 `LLVM-009t` 按 0.5.3 助记符重写，字节期望手推；本任务校验其与 `opcodes.yaml` 一致。
7. **M1 scope 外差异**：0.4.1 报告 29 项「QFC 有 yaml 无」（RF/CFX/system/RA）属正常；v5 需按 0.5.3 的 M1 范围重新分类，**不得把 M1 内差异当正常**。

## 已知坑 / 结论

摘自 DADAO-0628 DL-022a 完成区与代码级 Architecture Review：

1. **QFC 双向比对零误报**：0.4.1 结果为 `0 only in yaml`、`29 only in wiki`（全为 M1 排除项）；v5 结果须同样可解释。
2. **`check_qfc_coverage.py` 只读不阻断**（informational，exit 0），`check_lit_bytes.py` 无匹配即真错误（exit 1），两者语义不同，不可混淆。
3. **lit 字节 oracle 不运行 LLVM**：纯 Python + yaml，才能独立于实现发现工具/手推错误。
4. **正则兼容 spacer**：`# OBJ:` 提取 4 个 hex 字节，不关心其后 `{{.*}}`；v5 lit 已内建 spacer，正则须兼容。
5. **QFC 单元格区分 reserved 与 MISC 指针**：空白 = UNDI 保留；`MISC-*` = 子表指针，不能当具体指令。
6. **`opcodes.yaml` 自检前提**：其 mask/value 唯一性由 `SPEC-003t`/`validate_encoding.py` 保证；本任务在其基础上做交叉比对。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-022a-qfc-lit-oracle.md`
- DADAO-0628：`.work/DADAO-0628/scripts/check_qfc_coverage.py`
- DADAO-0628：`.work/DADAO-0628/scripts/check_lit_bytes.py`
- DADAO-0628：`.work/DADAO-0628/tests/lit/MC/Dadao/`
- 本项目：`spec/SimRISC-00-指令系统设计.md`、`verif/opcodes.yaml`、`verif/validate_encoding.py`、`tests/lit/MC/Dadao/`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 verif/check_qfc_coverage.py` 可运行，输出双向差异与数量汇总，exit 0；差异项逐条分类（M1 内/外）
2. `python3 verif/check_lit_bytes.py` 输出 `N patterns OK`、exit 0；若存在无匹配字节则 exit 1
3. 两脚本均不修改任何 yaml/lit 文件（只读）
4. `check_lit_bytes.py` 不含对 LLVM 工具的调用（grep 确认）
5. QFC 解析覆盖 v5 主表 + 全部 MISC 子表（含 octa/tetra/wyde/byte/RF/AMO）
6. 完成区粘贴两脚本真实 stdout，不转述

## 完成区

**状态**：待开始
**Commit**：
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
