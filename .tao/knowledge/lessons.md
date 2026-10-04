# 经验与教训（Lessons / Methodology）

> 本文件承载各模块台账中沉淀的**非 issue 内容**：教训（经验）、方法论、过程记录（子代理异常事件、任务书模板改进、反例注入教训、工具陷阱等），按主题组织。
>
> issue / 待决 / 缺口 / 后续候选类内容见 `.tao/knowledge/issues.yaml`。本文件由 `INFRA-032t`（2026-10-04）从原 backlog 散文台账拆分而来；原台账已删除。

## 1. 验收与验证方法论

### 1.1 期望值须「独立派生」（禁以被测实现校准）

- FP 独立 oracle（`GOLDEN-001t` 起）期望值须**独立派生自 `spec/`**，**禁**由 LLVM/QEMU 生成或校准（Independent oracle 原则，见 `AGENTS.md`）。
- `QEMU-036t` 的可复用做法（探针 113 例）：
  1. **RNE**（f32↔f64、int→f32/f64）用宿主 `struct`/`float` 锚点；
  2. **非 RNE**（RTZ/RDN/RUP）用 `fractions.Fraction` **精确有理数舍入器**逐位推导（输入取精确二元分数 `1±2^-24`、`1±2^-24±2^-30`）；
  3. **f→i** 用 `int()` 向零截断 + `INT32/INT64/UINT32/UINT64` 独立常量饱和界；
  4. **NaN** 用 IEEE754 规则（`尾数<<29` 加宽 / 保留高尾数位收窄）。
- **教训**：期望值写死时必须交付**可复算的派生器**（内联进探针/自检，如 `verify_derivations()`），使「常量 = 派生结果」可独立验证；否则硬编码值与实现形成自证循环。

## 2. 证据脚本与反例注入规范

### 2.1 管道退出码陷阱（`INTEG-005t` N1）

- `cmd | tee log; echo $?` 取到的是**管道末端 `tee`** 的退出码（恒 0），而非被检命令的退出码；曾致改前基线日志末行记 `EXIT=0`（真实 `EXIT=1`），证据与结论自相矛盾。
- 正解：`cmd > log 2>&1; rc=$?; … ; echo "EXIT=$rc"`，或 `${PIPESTATUS[0]}`，或 `set -o pipefail`。
- 已固化入 `AGENTS.md`「验证脚本反例门控」。

### 2.2 合并反例注入互相抵消（`QEMU-035t`）

- 一键证据脚本的 `MUST_FAIL` 清单须**逐例标注其对应的唯一注入**；凡一例受 ≥2 注入影响，须核查是否存在「多注入抵消 → 假绿」路径。
- 实例：初版 `MUST_FAIL` 含 `CL04`（ft negZero），同时受注入 (b2)（classify signpos 位偏移）与 (c)（negZero/posZero 互换）影响 → 恒 PASS（假绿）。
- 处置：改用单一归因用例（`CL05`/`CL14`），或**分轮注入**（每轮只注入一处）。

### 2.3 二进制 sha 随源码 commit 变化（`QEMU-035t`）

- QEMU 二进制内嵌源码 revision，故**跨 commit/amend** 时不得以二进制 sha 相等作还原判据——应断言**源码 blob sha**，二进制等价以「**重建后探针回绿**」为证。
- **同一 commit 工作树内**注入→还原并**重建**后，二进制 sha 应复原。

## 3. 子代理协作异常事件与处置

### 3.1 子代理异常返回须逐项扫描残留（`SPEC-049t`，2026-09-29）

- engineer 子代理异常返回（仅回「接下来需要做什么？」，未填完成区/未自审），但产出**部分落盘**（代码块 26 条已改、表格行 6 处漏改）。
- 教训：`check-asm-list-consistency` 绿灯**不覆盖正文**；子代理异常返回时须**逐项扫描残留**（不能只看「文件已改」）。
- 处置：主会话核对 `git status`/`grep` 后**未自行重试**，经用户授权重新下发补完，再由 reviewer 独立验收（9 项核验 + 3 类反例）后 Accepted。

## 4. 任务书模板改进教训

### 4.1 「改动清单」与「范围边界/事实核实」须交叉自检（`SPEC-086t`）

3 处内部矛盾：

1. 「改动清单」要求改 `tools/testcases/generate_misc.py`，而「范围边界」写其产物 `tests/vectors/isa/*.yaml`「不动」（改生成器后重跑必致产物 1 行注释变更）——同一文件既在改动清单又标「不动」即矛盾；
2. 标签 `R8/scope-excluded` 与括注「`ld.t-rf` 现属 `scope: fp`」不符（实测 `ld.t_rrii_rf` 确为 `fp`）；
3. 引用 file:line 事实失实：称 `spec/SimRISC-00` L255 有 `MISC-RF … Excluded from M1`，实测该文件全文无此字样。

**教训**：改动清单与范围边界/事实核实两节须交叉自检；标签类括注须与实际字段值一致；引用的 file:line 事实须在**下发前实测**。

### 4.2 反例注入判据须与门控脚本实际行为对齐（`SPEC-089t`）

- 任务书称「`dst_rf0` 改回 `deferred` 但保留 FP 引用 ⇒ `check-rule-refs` Gate2 FAIL」，实测 `tools/spec/check_rule_refs.py` 的 Gate2 对 `status==deferred` **直接 `continue`**（L82-83「deferred 允许 0 引用」）⇒ EXIT=0；正确回归判据是**摘要口径**（`active 被引用 11 / deferred 1`）。
- 「不变量计数」须下发前实测：任务书写「lit 26 / patches 67」，实测 29/69（非本任务引入）。

### 4.3 正例/反例清单须交叉自检、操作数角色须与格式定义一致（`LLVM-030t`）

- `LLVM-030t` §6.2 把 `ftadd rf0, rf2, rf3` 列为「正例（rf0 源合法）」，实为 `dst_rf0` 反例（`ftadd` 格式 `orrr`、**目的为首操作数**）。
- **教训**：同一串不得同时出现在正例与反例清单；`orrr`/`orri` 目的为首操作数，`cs.*`-rf 目的位置不同。

### 4.4 编码类反例示例须选用未占用 opx/op（`LLVM-029t`）

- §6.8-A 示例 `ftadd ha 0x10→0x11` 与 `ftsub`（同 `op=0x44`、`ha=0x11`）冲突 ⇒ `llvm-tblgen -gen-disassembler` 报 `Decoding conflict`、**构建直接失败**（非 oracle/lit FAIL），不满足「重建后 oracle/lit FAIL」的验收语义。
- **教训**：反例须写明「注入后构建成功、目标检查 FAIL」；不得给出会触发 TableGen 解码冲突或构建失败的值。

### 4.5 反例注入条目须写清「注入什么 → 哪些用例应 FAIL」（`QEMU-033t` §6.1(b)）

- 原文「只查部分重叠、不查完全重合 … ⇒ T3 仍 PASS 但 T2/T4 应 FAIL」与括注「证明含完全重合承重」**互为矛盾**；engineer 按意图取 `hb != hc` 注入（实测 T3/T7→0x89、T2/T4/T6 仍 0x88）。
- **教训**：反例条目须与括注的证明目的交叉自检，不得出现「T3 仍 PASS」与「证明含完全重合承重」并存。

## 5. 工具陷阱与门控约定

### 5.1 机械生成投影须在两个 drift 门控显式排除

- 机械生成投影入 `.tao/knowledge/contract-*.md` 时，须**同步**加入 `tools/infra/check_spec_drift.py`（`EXCLUDED_CONTRACTS`）与 `tools/infra/check_spec_refs.py`（`_EXCLUDED_CONTRACTS`）**两个**排除名单，否则会以「无来源头 / 无 § 引用」误报。
- `contract-cfx-aliases.md`、`contract-asm-list.md` 均已加入两处（`check_spec_refs` 恢复 76）。

### 5.2 路径类 grep/遍历检查须排除 `__pycache__`（`INFRA-027t`）

- `tools/**/__pycache__/*.pyc` 内嵌旧 docstring 字符串，`grep -rn tools` 会报 `binary file matches`。已补入 `Process-01 §8.1` 实现注意。

### 5.3 历史文档旧路径「保留、不回溯更新」（by design）

- `docs/m1-retrospective.md`、`docs/m2-spec-planning.md`、`changelog.md`、全部已验收任务书、`spec/SimRISC-0.5.3/` 中的旧路径保留（历史快照）；如需全仓一致再另行裁定。

## 6. spec 开放点与过程记录

### 6.1 历史记录不改写正文（体例）

- 原 backlog 台账 L18（历史）含旧规则 id（`fp_root_invalid_n`、`fp_log_invalid_base`）与旧计数（`178 M1 + 78`），均为 `SPEC-067t` 前的历史状态；按体例**不改写历史正文**。
- 注：`fp_log_invalid_base` 已删除、`fp_root_invalid_n` 已改名 `encode_fp_root_n`、计数已更新。

### 6.2 `TESTCASES` 任务集最终裁决（2026-09-15，用户逐条确认）

- F1 数据修复归 `003t`；F10 分摊到 `003t`~`007t`（不单列 encoding 任务）；F7 采用方案 (i)（schema 扩 `expected_pc`）→ PC-only 全部改 active；F5 归 `008t`（原 `011t` 编号撤销）；文件布局方案 A。
- 旧 `004t`/`005t`/`006t` 属**已达成**（非暂缓），关闭理由与证据见 `TESTCASES-001k` 任务表重排说明。

### 6.3 合法性清单渲染格式的用户确认门 ② 未显式答复（`SPEC-073t`，2026-10-02）

- 12 章 `LEGALITY` 生成区已按现有格式提交（`fe190e2`）；用户选择「迁移环境」，未逐章确认。若迁移后需改格式，属 `gen_legality_list.py` + `check-legality-drift` 的同步改动（成本低）。

### 6.4 旧审查者文本与新规程无硬矛盾（`INFRA-031t`）

- `~/t.a.o/opencode/agent/reviewer.md` §2「重跑，不要读」字面似与「reviewer 先审脚本」张力，但「不要读」指**不看工程师完成区叙述**，非实质冲突；「绝不自行修改代码」针对「改代码凑绿」，与「注入→FAIL→还原」的证伪不冲突。
- 结论：新规程与仍生效的旧文本**无硬矛盾**，仅需在全局同步时澄清措辞。

## 7. 教训条目

### 7.1 softfloat 目标必须显式设 `default_nan_pattern`（`QEMU-037t`）

- `fp_status_init` 用 `memset(st,0,...)` 构建局部 `float_status` 后，`default_nan_pattern == 0`；而 `fpu/softfloat-parts.c.inc::partsN(default_nan)` 带 `assert(dnan_pattern != 0)` ⇒ invalid 运算（`0/0`、`inf−inf`、`inf×0`、`rem`-invalid、`sqrt(−x)`）走 default NaN 路径时结果畸形或触发断言。
- 修复：`set_float_default_nan_pattern(0b01000000, st)`（default NaN = `0x7FC00000`/`0x7FF8000000000000`，与 `QEMU-035t` 的 `FP_FT_QNAN`/`FP_FO_QNAN` 一致）。架构师独立注入（移除该行）实测 12 例 FAIL ⇒ 承重。
- **规则**：任何新增/复制的 softfloat 目标初始化都须显式设 `default_nan_pattern`，并在探针中覆盖至少一条 invalid→default-NaN 用例。
