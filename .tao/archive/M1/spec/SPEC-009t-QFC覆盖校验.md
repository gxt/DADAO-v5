# SPEC-009t: QFC 覆盖校验

**模块**：spec
**项目里程碑**：M1
**依赖**：`SPEC-003t`
**状态**：已验证

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
3. **编码表路径**：v5 为 `contracts/opcodes.yaml`（模块重划前为 `verif/opcodes.yaml`）。
4. **脚本目录**：`verif/` → `tools/spec/`。
5. **M1 scope 外差异**：须按 0.5.3 的 M1 范围重新分类，不得把 M1 内差异当正常。

## 已知坑 / 结论

1. **QFC 双向比对零误报**：结果须可解释（差异项全为 M1 排除项或明确分类）。
2. **`check_qfc_coverage.py` 只读不阻断**（informational，exit 0）。
3. **QFC 单元格区分 reserved 与 MISC 指针**：空白 = UNDI 保留；`MISC-*` = 子表指针，不能当具体指令。
4. **`opcodes.yaml` 自检前提**：其 mask/value 唯一性由 `SPEC-003t`/`validate_encoding.py` 保证。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-022a-qfc-lit-oracle.md`
- DADAO-0628：`.dadao/DADAO-0628/scripts/check_qfc_coverage.py`
- 本项目：`spec/SimRISC-00-指令系统设计.md`、`contracts/opcodes.yaml`、`tools/spec/validate_encoding.py`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 tools/spec/check_qfc_coverage.py` 可运行，输出双向差异与数量汇总，exit 0；差异项逐条分类（M1 内/外）
2. 脚本不修改任何 yaml 文件（只读）
3. QFC 解析覆盖 v5 主表 + 全部 MISC 子表（含 octa/tetra/wyde/byte/RF/AMO）
4. 完成区粘贴真实 stdout，不转述

## 完成区

**测试结果**：通过 4/4 验收标准（脚本可运行且 exit 0；只读不改数据文件；QFC 解析覆盖主表 + 全部 6 个 MISC 子表；完成区粘贴真实 stdout）。无失败。

**修改文件**：
- 新增 `tools/spec/check_qfc_coverage.py`（404 行；本轮重写核对，`classify_m1` 改为由主表子表指针派生，去掉硬编码 op）
- `.tao/tasks/spec/SPEC-009t-QFC覆盖校验.md`（本任务书：状态 + 完成区 + 自审记录）
- 未改动任何数据文件：`spec/SimRISC-00-指令系统设计.md`、`contracts/opcodes.yaml` 的 md5 运行前后不变（见下）

**验收结果**：

命令：`python3 tools/spec/check_qfc_coverage.py`（exit 0）；完整日志：`.tao/logs/SPEC-009t-check_qfc_coverage.log`

真实 stdout（逐字粘贴）：

```text
check_qfc_coverage: QFC 表 ↔ contracts/opcodes.yaml 双向覆盖校验
  spec: spec/SimRISC-00-指令系统设计.md
  yaml: contracts/opcodes.yaml

[QFC 解析]
  主表具体指令单元格: 91
  MISC-AMO   (op=0x00): 10
  MISC-octa  (op=0x40): 31
  MISC-tetra (op=0x41): 26
  MISC-wyde  (op=0x42): 26
  MISC-byte  (op=0x43): 26
  MISC-RF    (op=0x44): 46
  子表指针: MISC-AMO@0x00, MISC-octa@0x40, MISC-tetra@0x41, MISC-wyde@0x42, MISC-byte@0x43, MISC-RF@0x44
  reserved（空白）单元格: 250
  QFC (op,ha) 指令总数: 256

[YAML 解析]
  记录数: 256，distinct (op,ha): 256

[双向差异]
  QFC-only（QFC 有、yaml 缺）: 0
  YAML-only（yaml 有、QFC 不含）: 0

[差异分类]（M1 内差异 = 真实缺口/错误；M1 外差异 = 已知范围排除）
  （无差异）

[M1 范围]
  QFC 中 M1 外条目: 78（LR-SC 原子=8, 浮点（MISC-RF）=46, 浮点（RF）=18, 特权 cfx=6）
  yaml 中 excluded_m1 条目: 78
  → QFC 与 yaml 的 M1 外条目集合一致

[汇总]
  QFC 指令数: 256
  YAML 指令数: 256
  差异总数: 0（M1 内: 0，M1 外: 0）
  OK: QFC 表与 opcodes.yaml 双向完全一致

check_qfc_coverage: done (informational, exit 0)
```

补充验收证据：
- `python3 -m py_compile tools/spec/check_qfc_coverage.py` → `py_compile OK`
- 只读验证：运行前后 `md5sum spec/SimRISC-00-指令系统设计.md contracts/opcodes.yaml` 不变（`0847be38…` / `79039ab8…`）
- 非 no-op 验证（篡改副本，非仓库文件）：删 `jump-iiii`、把 `swym` op 由 0x77 改为 0x78，脚本报 `QFC-only 2` + `YAML-only 1`，分类 `M1 内: 3`，仍 exit 0 → 双向比对真实有效

**新发现/坑**：
1. QFC 主表 16×8=128 格，含 6 个 `MISC-*` 指针（AMO/octa/tetra/wyde/byte/RF）+ 91 条具体指令，故主表空白 31 格；6 个子表各 8×8=64 格、共 165 条指令、空白 219 格；全表 reserved=250 = 512 − 256 具体 − 6 指针。手工核算时易把指针格误计入具体指令。
2. `tools/spec/generate_opcodes.py` 是**硬编码记录**（不解析 markdown），因此 `check_qfc_coverage.py` 直接解析 QFC 表是**真正独立 oracle**；两者 256/256 完全一致，说明 `contracts/opcodes.yaml` 未相对规范漂移。
3. 主表指令在 yaml 中**无 `ha` 字段**（记 None），子表指令有 `ha`；比对时统一转 int。
4. `MISC-RF` 46 条名称均以 `ft`/`fo` 开头，按名称也能识别；但按主表指针判定子表更稳（不依赖命名约定）。
5. 建议沉淀知识：QFC 覆盖检查命令与"零差异"基线（QFC/YAML 均 256；M1 外 78 = LR-SC 8 + MISC-RF 46 + RF 18 + 特权 cfx 6）。

**遗留问题**：无。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：Accepted（无未修 finding）

审查范围：`tools/spec/check_qfc_coverage.py`（新增，404 行）——自主逐行审查。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1：docstring 声明子表 op「由主表指针决定（不硬编码）」，但 `classify_m1` 硬编码 `op==0x44`/`op==0x00` | ✅已修 | `classify_m1` 增加 `misc_name` 参数，由 `spec["pointers"]` 派生；调用点（3 处）同步传入 | 重跑输出与修改前逐字节一致：256/256、0 差异、M1 外分类计数不变 |
| F2：docstring 写 yaml 键为 `(op, str(ha))`，实现用 int `ha` | ✅已修 | docstring 改为 `(op, ha_or_None)` 并注明统一整数比较 | `py_compile OK`；重跑一致 |
| F3：`LRSC_HA` 常量与名称正则 `^(lr_\|sc_)` 判定重复 | ✅已修 | 随 F1 删除 `LRSC_HA`，LR-SC 统一由子表名 + 名称判定 | 重跑 `LR-SC 原子=8` 不变 |

逐项审查结论：
- **逻辑正确性**：主表 `op=(row_val<<3)|col_val`、子表 `ha=(row_val<<3)|col_val`；手工抽查 14 条编码（swym 0x77 / ret 0x76 / jump 0x70 / cfx2rd 0x7A / trap 0x7F / rd2rd (0x40,0x2C) / and.b (0x43,0x08) / ftadd (0x44,0x10) / lr_nn.o (0x00,0x10) / illi (0x00,0x00) / fence (0x00,0x01) / add.uo 0x50 / ld.ub 0x10 / or.w 0x48）与 yaml 全部一致。
- **边界情况**：输入缺失 → WARN + exit 0；指针与子表区段对不上 → 打印 `[QFC 结构告警]`；指针格与 reserved 空白格均不计入具体指令集合。
- **覆盖完整性**：6 个 MISC 子表全部解析，无 `MISC-Norm`（v5 已无），主表 91 + 子表 165 = 256，与 yaml 记录数吻合。
- **防造假**：所有命令输出重定向至 `.tao/logs/SPEC-009t-check_qfc_coverage.log`；篡改副本实验独立证明比对非 no-op。
- **只读约束**：运行前后数据文件 md5 不变，`git diff -- spec/ contracts/` 为空。
- **exit 语义**：任何差异下均 `sys.exit(0)`（informational，不阻断）。

**自审判决**：Accepted，无遗留未修 finding。

### 第 1 轮 reviewer 验收

**判决**：Accepted

**审查者**：reviewer agent（独立重跑，未修改任何代码/数据文件）

#### 一、重跑记录

**命令**：`python3 tools/spec/check_qfc_coverage.py`（exit 0）

**真实 stdout**：

```text
check_qfc_coverage: QFC 表 ↔ contracts/opcodes.yaml 双向覆盖校验
  spec: spec/SimRISC-00-指令系统设计.md
  yaml: contracts/opcodes.yaml

[QFC 解析]
  主表具体指令单元格: 91
  MISC-AMO   (op=0x00): 10
  MISC-octa  (op=0x40): 31
  MISC-tetra (op=0x41): 26
  MISC-wyde  (op=0x42): 26
  MISC-byte  (op=0x43): 26
  MISC-RF    (op=0x44): 46
  子表指针: MISC-AMO@0x00, MISC-octa@0x40, MISC-tetra@0x41, MISC-wyde@0x42, MISC-byte@0x43, MISC-RF@0x44
  reserved（空白）单元格: 250
  QFC (op,ha) 指令总数: 256

[YAML 解析]
  记录数: 256，distinct (op,ha): 256

[双向差异]
  QFC-only（QFC 有、yaml 缺）: 0
  YAML-only（yaml 有、QFC 不含）: 0

[差异分类]（M1 内差异 = 真实缺口/错误；M1 外差异 = 已知范围排除）
  （无差异）

[M1 范围]
  QFC 中 M1 外条目: 78（LR-SC 原子=8, 浮点（MISC-RF）=46, 浮点（RF）=18, 特权 cfx=6）
  yaml 中 excluded_m1 条目: 78
  → QFC 与 yaml 的 M1 外条目集合一致

[汇总]
  QFC 指令数: 256
  YAML 指令数: 256
  差异总数: 0（M1 内: 0，M1 外: 0）
  OK: QFC 表与 opcodes.yaml 双向完全一致

check_qfc_coverage: done (informational, exit 0)
```

**日志路径**：`.tao/logs/SPEC-009t-review-run.log`

#### 二、独立核验（防 no-op）

| 核验项 | 方法 | 结果 |
|--------|------|------|
| **真正解析 spec QFC 表** | 复制 spec 到临时目录，删除 `swym-iiii` 单元格 → QFC 指令数从 256 降为 255，脚本报 `YAML-only 1` | ✅ 脚本动态解析，非硬编码 |
| **篡改副本比对有效** | 篡改 yaml 中 swym 的 op 从 0x77→0x78 → 脚本报 `QFC-only 1`（0x77）+ `YAML-only 1`（0x78），均分类 M1 内 | ✅ 双向比对真实有效 |
| **篡改删除 yaml 条目** | 从 yaml 删除 jump-iiii + jump-rrii → 脚本报 `QFC-only 2`，分类 M1 内 | ✅ 差异检测正确 |
| **只读约束** | 运行前后 `md5sum spec/SimRISC-00-指令系统设计.md contracts/opcodes.yaml` 不变（`0847be38…` / `79039ab8…`）；`git diff -- spec/ contracts/` 为空 | ✅ 只读，零修改 |
| **MISC 指针 vs reserved 区分** | 调用 `parse_spec()` 检查：6 个 MISC 指针均不在 `qfc_opids` 中；子表 op 与指针 op 一致 | ✅ 指针不计入指令集合 |
| **手工核算总数** | 主表 16×8=128 格（91 指令 + 6 指针 + 31 空白）；6 子表各 8×8=64 格（165 指令 + 219 空白）；总计 256+6+250=512 | ✅ 与脚本输出一致 |
| **py_compile** | `python3 -m py_compile tools/spec/check_qfc_coverage.py` → OK | ✅ 无语法错误 |

#### 三、约束逐条核验

| 验收标准 | 判定 | 证据 |
|----------|------|------|
| 1. `python3 tools/spec/check_qfc_coverage.py` 可运行，输出双向差异与数量汇总，exit 0；差异项逐条分类（M1 内/外） | ✅ 通过 | 重跑 exit 0；输出含 QFC/YAML 解析汇总 + 双向差异 + M1 分类 + 数量汇总 |
| 2. 脚本不修改任何 yaml 文件（只读） | ✅ 通过 | 运行前后 md5 不变，git diff 为空 |
| 3. QFC 解析覆盖 v5 主表 + 全部 MISC 子表（含 octa/tetra/wyde/byte/RF/AMO） | ✅ 通过 | 6 个子表全部解析（AMO/octa/tetra/wyde/byte/RF）；主表 91 + 子表 165 = 256；篡改 spec 测试确认动态解析 |
| 4. 完成区粘贴真实 stdout，不转述 | ✅ 通过 | 完成区 stdout 与 reviewer 重跑输出逐字节一致 |

#### 四、发现的问题

无。脚本逻辑正确，比对有效，只读约束守住了。

**审查判决**：Accepted，全部 4 条验收标准通过，无遗留问题。

### architect 交叉复核

**判决**：Accepted（与 reviewer 判决一致，无返工项）

**复核者**：architect agent（独立重跑 + 自建独立解析器；未修改任何代码/数据文件）

#### 一、独立重跑

- `python3 tools/spec/check_qfc_coverage.py` → **exit 0**；输出与完成区/reviewer 日志**逐字节一致**（`diff` 为空）。
- 运行前后 md5 不变：spec `0847be3824a5e97110a247589574f101`、yaml `79039ab8bfff05429a1970961a49ec26`；`git diff -- spec/ contracts/` 为空。

#### 二、脚本「真解析 / 只读」独立核验

- **只读**：全脚本仅两处 `open(..., encoding="utf-8")`（读模式），无 `.write(`/`os.remove`/`subprocess`；运行前后数据文件 md5 不变。
- **真解析**（在 `/tmp/opencode/arch-009t/` 的独立副本上篡改，独立复现 reviewer 全部实验）：

  | 篡改 | 脚本反应 | 判定 |
  |------|---------|------|
  | 清空主表 `swym-iiii` 单元格 | `YAML-only 1`（0x77，M1 内） | ✅ 动态解析主表 |
  | 清空 MISC-RF 子表 `ftadd-orrr` | `YAML-only 1`（0x44/0x10） | ✅ 动态解析子表 |
  | yaml `swym` op `0x77`→`0x78` | `QFC-only 1` + `YAML-only 1` | ✅ 双向比对有效 |
  | yaml 删 `jump-iiii`+`jump-rrii` | `QFC-only 2`（0x70/0x71，M1 内） | ✅ 差异检测正确 |
  | 主表指针 `MISC-octa`→`MISC-Norm` | 触发 `[QFC 结构告警]`（指针无子表 + 子表无指针），octa 31 条不再计入 | ✅ 指针驱动子表解析 |

#### 三、独立 oracle 交叉核算（自建解析器，不复用被测脚本）

- 主表 128 格 = **91 具体 + 6 指针 + 31 空白**；6 子表 384 格 = **165 具体 + 219 空白**；总 **256 具体 + 250 reserved**；各子表计数（AMO 10 / octa 31 / tetra 26 / wyde 26 / byte 26 / RF 46）与脚本输出**逐项一致**。
- 自建 QFC 集合 ↔ `opcodes.yaml`：QFC=256、YAML=256、**双向差异均 0** → **「零差异」是真实结果，非漏解析导致的假绿**。
- yaml `excluded_m1`=78，独立分类组成（MISC-RF 46 + RF 18 + AMO/LR-SC 8 + cfx 6）与脚本 `[M1 范围]` 输出一致。
- 6 个指针均未误入指令集合；子表 op 均由主表指针派生；yaml 主表 91 条无 `ha` 字段（记 None），与脚本比较口径一致。

#### 四、验收标准 1–4 对照

1. ✅ exit 0；输出双向差异 + 数量汇总 + M1 内/外分类。
2. ✅ 只读：md5 前后不变、`git diff` 为空。
3. ✅ 主表 + 全部 6 个 MISC 子表（octa/tetra/wyde/byte/RF/AMO）均被解析。
4. ✅ 完成区 stdout 逐字真实（与本次重跑、两份日志 `diff` 一致）。

#### 五、发现的问题

**无阻塞项，无遗漏/过松。** 仅记录 2 处非阻塞观察（不影响本任务验收）：

1. `classify_m1` 对 YAML-only 差异优先采信 yaml 的 `excluded_m1` 标记；若 yaml 错标 excluded 且 QFC 缺该条，会被归为 M1 外。但 `[M1 范围]` 段对「QFC M1 外集合 == yaml excluded 集合」做集合相等校验，可兜住此类偏差（当前输出为「集合一致」）。
2. `_QFC_FORMATS` 为硬编码格式后缀集合，仅影响 M1 分类时的名称剥离，**不影响双向集合比对**；若规范新增格式后缀需同步维护。

**交叉复核判决**：Accepted，reviewer 的 Accepted 判决成立，证据可复现，无遗漏、无过松。
