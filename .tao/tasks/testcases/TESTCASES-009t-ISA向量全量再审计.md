# TESTCASES-009t: ISA 向量全量再审计（残留错误兜底）

**模块**：testcases
**项目里程碑**：M1
**依赖**：`TESTCASES-003t`、`004t`、`005t`、`006t`、`007t`、`008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/` 下**目标文件集**（`reg-arith`/`reg-logic`/`reg-shift-extend`/`reg-compare`/`reg-cond-assign`/`reg-imm-block`/`mem-rd`/`mem-rb`/`mem-ra`/`ctrl-br`/`ctrl-jump`/`ctrl-call`/`ctrl-ret`/`misc`，以及 `008t` 的保留编码文件）
  - `tests/vectors/schema.md`（`002t` 返工后：含 `expected_pc`、encoding 豁免）
  - `tests/vectors/inventory.md`（`002t` 返工后）
  - `contracts/opcodes.yaml`（mask/value 与字段位域）、`contracts/legality_rules.yaml`
  - `.tao/knowledge/contract-isa.md`（§2 编码、§3 数据类、§4 访存、§5 控制流、§7 系统、§9 异常）、`.tao/knowledge/adr-0004-test-machine.md`
- 输出：
  - 修复后的全部 `tests/vectors/isa/*.yaml`（残留错误）
  - `tests/vectors/inventory.md`（同步最终 `file` 列与覆盖状态）
  - 审计记录：逐族「重推导公式 + 依据章节 + 与现有数据比对结论」
- 约束：
  - 只做**根因明确**的数据纠正；无法确定的标 `[OPEN]`，不猜测
  - 每条修正给出依据（合约章节 + 手算）
  - **不重复修** F1（`003t`）、F10（各数据任务）、F7（`005t`/`006t`）已覆盖项
  - **不改** `contracts/`、`tools/`、`Makefile`
  - 完成后不自行 commit

## 任务范围

### 1. 独立重推导审计（核心）

对**全部** `tests/vectors/isa/*.yaml` 做一次系统性重推导审计，逐族重算 semantic/boundary/overlap 期望值并与现有数据比对，修复**残留**错误：

- 期望值仍须**手工派生**自 `contract-isa.md`/`spec/`/ADR-0004；不得从 LLVM/QEMU 反推；若依赖实现/布局而不可独立确定，标 `[OPEN]` 或 deferred 并说明。
- 重点覆盖「易误读的位域/语义族」：
  - `orrr`/`orri` 字段语义（`orri` 立即数位域，F1 已修 `orrr`）；
  - RB 全 64 位算术（无 48-bit 截断）；
  - 块赋值写入宽度（`rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/`ra2rd`/`rd2ra`）；
  - wyde-position（rwii）；
  - `cmp`/`cs`（含 C-27 overlap 保持 deferred）；
  - RA 存取；
  - multi load/store 的 count/对齐；
  - 控制流 `expected_pc`（taken/not-taken、`call` 压栈、`ret` 弹栈）与 `expected_state.ra`。

### 2. 文件布局一致性

- 确认 `tests/vectors/isa/` 只含**目标文件集**（数据从零生成，无任何旧文件/历史文件混入）。
- 同步 `inventory.md` 的 `file` 列与最终文件布局一致（F2/F3 的 inventory 同步校验须通过）。

### 3. 问题类别核对（0628 清单，v5 按 0.5.3 重查）

1. **encoding 位域错误**（`hb`/`hc` 混淆）：复核全部 `orrr`/`orri` 的 `fields` 与 word 位组装是否一致（含 `orri` 立即数位域）。
2. **`input_state` 出现 rd0**：`set.zw rd0` → `ha=0` → ILLI；validator 已机械禁止，本任务复核零违例。
3. **期望值错误**：与修正后的 encoding/语义不一致（立即数 wyde 位置、块赋值写入宽度等）——**本任务核心**（F1 族除外）。
4. **store encoding `ha=0` → ILLI**：归 `004t`，本任务复核不复发。
5. **load encoding `addr=0` → 未映射**：归 `004t`，本任务复核不复发。
6. **deferred 状态**：实现侧 bug 未解决时标 `status: deferred` 并写明 reason；v5 不照搬 0628 的 `divs`/`divu` TCG bug。

## 验收标准

1. 对全部目标文件给出**逐族重推导审计记录**（公式 + 依据 + 比对结论），非抽样
2. 全部 `encoding.word` 与 `contracts/opcodes.yaml` 的 `(word & mask) == value` 一致
3. `input_state` 中无 `rd0`/`rb0` 条目
4. 期望值按 0.5.3 语义（含 RB 全 64 位、`expected_pc`）逐条手算且自洽；**F1/F10/F7 覆盖项不重复改**
5. `tests/vectors/isa/` 只含目标文件集（数据从零生成，无旧/历史文件）；`inventory.md` `file` 列与之一致
6. deferred 向量有明确 `deferred_reason`；无法确定处标 `[OPEN]` 并在完成区列出
7. **数据级覆盖率（本任务兜底门控）**：对全部 `isa/*.yaml` 机械核验——M1 scope 内**每个 `(insn, format)` 至少有 1 条 `status: active` 的对应 class case**；缺失须报错/记录。**不得仅以 `validate_vectors.py` 输出的 `178/178` 作为数据覆盖判据**（该数字为 inventory 声明级：inventory 行集 == `opcodes.yaml` M1 身份集，实测零数据/仅 1 条 case 亦输出 `178/178`）。
8. `python3 tools/testcases/validate_vectors.py` 零错误；`make check` PASS
9. 每处修正可回溯到合约章节
10. 未自行 commit

## 背景（完整）

### 目标

在 `003t`~`008t` 完成后，对整个向量集做一次**系统性重推导**，修复未被前序任务覆盖的残留错误，使向量真正可作为实现（LLVM/QEMU/integ）的独立 oracle。

### 设计理由

- 0628 DL-027a 表明：review 通过后仍存在成批数据错误；v5 的 F1（`orrr` 移位/扩展 40 条期望值全错）正是同类问题的再现，且 reviewer 因**抽样偏差**未发现。
- 因此仅修 F1/F10 不够，须对整个向量集做一次系统性重推导；本任务作为**兜底**，覆盖各数据任务的范围边界之外与跨族交互。
- **数据级覆盖率兜底（交叉复核补充）**：`002t` 的 `validate_vectors.py` 覆盖率为**声明级**（inventory 行集 == `opcodes.yaml` M1 身份集），**不校验数据**；本任务须补上数据级覆盖的机械核验（见验收标准 7），否则存在「声明完整但数据从未被机械校验」的空档。

### 上游引用

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-027a-architect-direct-vector-fixes.md`（内容溯源，非执行依赖）

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符与文件组织**：v5 目标文件集为 14 个 `reg-*`/`mem-*`/`ctrl-*`/`misc`（方案 A）。
2. **ORRI/ORRR 位域**：以 v5 `contract-isa.md` §2.2 与 `contracts/opcodes.yaml` 的 `fields` 为准，不照抄 0628。
3. **RB 语义**：0.5.3 RB 全 64 位，无 48-bit 截断。
4. **`divs`/`divu` → `div.so`/`div.uo`**：0628 的 TCG label bug 属 0.4.1 实现问题，v5 不照搬。
5. **`expected_pc`**：v5 新增；控制流审计须覆盖。

## 已知坑 / 结论

1. **rd0 禁止出现在 `input_state`**：预置 rd0 会经 `set.zw rd0` → ILLI。
2. **ORRI 位域**：`bits[17:12]=dst, bits[11:6]=src, bits[5:0]=count`（hb/hc 易混淆）；v5 用 opcodes.yaml `fields` 核对。
3. **load encoding `addr=0`**：ADR-0004 D5.6 → `0x87`；基址须指向 RAM（`004t`）。
4. **store encoding `ha=0`**：`st.*`/`stm.*` 的 `rdha` 为源，`rd0` → ILLI（`004t`）。
5. **deferred 必须有 reason**：不静默。
6. **不自行 commit**：完成后等待审查。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-027a-architect-direct-vector-fixes.md`（内容溯源）
- 本项目：`contracts/opcodes.yaml`、`.tao/knowledge/contract-isa.md`、`contracts/legality_rules.yaml`、`tests/vectors/schema.md`、`tests/vectors/inventory.md`
- 知识库：`.tao/knowledge/MEMORY.md`、`.tao/knowledge/deferred.md`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审
（待填写）

### 第 1 轮 reviewer 验收
（待填写）
