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

### 1.2 工具交付物 vs 数据交付物应分层验收（`ISS-035`）

- **教训**：脚本（工具交付物）的 bug 不应阻断数据交付物的验收——两者应**分层验收**，分别给判据。
- 来源：原 `ISS-035`（M1 testcases 台账）。`INFRA-033t`（2026-10-04）判定其为**教训**而非待办 issue，自 `issues.yaml` 移入本文件（id 不复用）。

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
- **实操补充（`QEMU-038t`）**：`--inject` 在记录 `sha_bin_before` **之前须先做一次 normalize 重建**（对齐当前 clean commit）——否则基线取自 amend 前脏树构建的二进制（`qemu-version.h` 的 `git describe` 内嵌 revision 不同），还原后 sha 必不相等、误报「未复原」。主判据仍是**源码 blob sha + 重建回绿**；二进制 sha 复原为**同 commit/clean 态**下的辅证。

### 2.4 未重建 QEMU 的探针回归判据＝「逐字节一致 / 零新增失败」，**不要求**探针 `rc=0`（`LLVM-031t`）

- 改 **LLVM-only**（`make build-mc`、不重建 QEMU）时，QEMU 探针产出结构性不变；回归判据取**与改前基线逐字节一致**（`diff -q`），即**零新增失败**。
- **不得**以探针 `rc=0` 为判据——多个 legacy 探针（`min_rom_probe_005t..036t` 内 6 条）在基线即 `rc=1`（pre-existing FAIL），以 `rc` 判定会误报「本任务引入回归」。
- 实例：`LLVM-031t` 复用 `.work/evidence/QEMU-037t/baseline/`，17 条 `byte-identical` + `_037t` 91/91；已核实 18 个探针脚本均不引用 `llvm*`（`grep -l llvm tools/qemu/min_rom_probe_*.py` 空）。
- **6 条 legacy 探针确切清单（`QEMU-038t` 复核补全）**：`min_rom_probe_006t`、`_008t`、`_009t`、`_010t`、`_013t`、`_028t`（基线即 `rc=1`，pre-existing；与 `issues.yaml ISS-120` 一致，任务书同理见 §4.6）。

### 2.5 注入脚本须含异常退出回滚（trap）+ 替换串须含完整唯一条件前缀（`LLVM-031t`）

- 注入脚本须对注入态**异常退出**设 `EXIT`-trap，自动 `git checkout` 还原并**重建**（源码还原 ≠ 二进制还原），否则工作树/二进制留在注入态、后续验收不可信。
- 注入替换串必须是**完整、唯一可定位**的条件前缀：首版 `"if (false && " + old` 拼接得 `if (false && if (...` ⇒ 编译失败并遗留注入态；改为在 `if (` 后精确插入 `false && `（并加 trap）修复。
- 已在 `LLVM-031t` 的 `.work/evidence/LLVM-031t/run.sh` 落地（`trap cleanup EXIT` + `git diff --name-only` 非空校验 + sha256 还原断言）。

## 3. 子代理协作异常事件与处置

### 3.1 子代理异常返回须逐项扫描残留（`SPEC-049t`，2026-09-29）

- engineer 子代理异常返回（仅回「接下来需要做什么？」，未填完成区/未自审），但产出**部分落盘**（代码块 26 条已改、表格行 6 处漏改）。
- 教训：`check-asm-list-consistency` 绿灯**不覆盖正文**；子代理异常返回时须**逐项扫描残留**（不能只看「文件已改」）。
- 处置：主会话核对 `git status`/`grep` 后**未自行重试**，经用户授权重新下发补完，再由 reviewer 独立验收（9 项核验 + 3 类反例）后 Accepted。

### 3.2 engineer 子代理连续 3 次空返回（`ISS-055`，QEMU-009t 返工）

- 事件：`QEMU-009t` 返工时 engineer 子代理**连续 3 次空返回**，主会话代行完成修改并登记。
- 处置规则已固化入 `AGENTS.md`「子代理返回异常处理」（连续 ≥3 次空返回且产出未落盘 ⇒ 主会话可代行，仍须 reviewer 独立验收 + 登记 `issues.yaml`）。
- 来源：原 `ISS-055`；`INFRA-033t`（2026-10-04）判定其为**过程记录**而非待办 issue，移入本文件（id 不复用）。

### 3.3 qemu 模块子代理异常事件汇总（`ISS-066`，2026-09-21）

- 事件：`QEMU-016t/017t/018t` 的 engineer 完成区与真实输出不符或空返回（2026-09-21 汇总）。
- 教训：完成区结论须与真实输出**逐条对齐**；子代理异常返回时须**逐项扫描残留**（见 §3.1）。
- 来源：原 `ISS-066`；`INFRA-033t`（2026-10-04）判定其为**过程记录**而非待办 issue，移入本文件（id 不复用）。

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

### 4.6 任务书「pre-existing 失败清单」须与实测一致（`QEMU-038t`）

- `QEMU-038t` 任务书 §5 称「M1 探针已知 pre-existing 失败仅 `min_rom_probe_008t`/`_013t`」，实测为 **6 条**（`_006t/_008t/_009t/_010t/_013t/_028t`，与 `issues.yaml ISS-120` 一致）；engineer 已如实披露并改用「与基线逐字节一致 / 零新增」判据，未影响结论。
- **教训**：任务书凡断言「仅 X 条 / X 与 Y」pre-existing，须在**下发前**对**全量探针**实测（或直接引用 `issues.yaml ISS-120` 的既列清单），不得沿用上一任务的旧清单；回归判据统一取「与改前基线逐字节一致 / 零新增」（见 §2.4），不依赖该清单的条数。

## 5. 工具陷阱与门控约定

### 5.1 机械生成投影须在两个 drift 门控显式排除

- 机械生成投影入 `.tao/knowledge/contract-*.md` 时，须**同步**加入 `tools/infra/check_spec_drift.py`（`EXCLUDED_CONTRACTS`）与 `tools/infra/check_spec_refs.py`（`_EXCLUDED_CONTRACTS`）**两个**排除名单，否则会以「无来源头 / 无 § 引用」误报。
- `contract-cfx-aliases.md`、`contract-asm-list.md` 均已加入两处（`check_spec_refs` 恢复 76）。

### 5.2 路径类 grep/遍历检查须排除 `__pycache__`（`INFRA-027t`）

- `tools/**/__pycache__/*.pyc` 内嵌旧 docstring 字符串，`grep -rn tools` 会报 `binary file matches`。已补入 `Process-01 §8.1` 实现注意。

### 5.3 历史文档旧路径「保留、不回溯更新」（by design）

- `docs/m1-retrospective.md`、`docs/m2-spec-planning.md`、`changelog.md`、全部已验收任务书、`spec/SimRISC-0.5.3/` 中的旧路径保留（历史快照）；如需全仓一致再另行裁定。

### 5.4 `validate_vectors.py` 变更历史（审计追溯，`ISS-024`）

- 记录：`002t`→`003t`→`004t` 两次**纯新增**，**未弱化**既有断言（审计追溯基线）。
- 来源：原 `ISS-024`；`INFRA-033t`（2026-10-04）判定其为**审计记录**而非待办 issue，移入本文件（id 不复用）。

### 5.5 F7 守卫基线（参照基准，`ISS-032`）

- 记录：`005t`→`006t`→`007t` 形成单一 `if/elif` 守卫块，F7 守卫基线已完整，作为**参照基准**。
- 来源：原 `ISS-032`；`INFRA-033t`（2026-10-04）判定其为**基线记录**而非待办 issue，移入本文件（id 不复用）。

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

### 6.5 `LLVM-010t` 关闭的理由与去向（`ISS-072`）

- 记录：`LLVM-010t` 关闭时已无独立交付物，**编号留空**；遗留可选项「加 `llvm-objcopy` 构建目标」**后续已落实**（`Makefile` 的 `LLVM_MC_FULL_TARGETS` 含 `llvm-objcopy`，`build-mc-lite` 不含）。
- 来源：原 `ISS-072`；`INFRA-033t`（2026-10-04）判定其为**关闭记录**（无未决待办）而非 issue，移入本文件（id 不复用）。

## 7. 教训条目

### 7.1 softfloat 目标必须显式设 `default_nan_pattern`（`QEMU-037t`）

- `fp_status_init` 用 `memset(st,0,...)` 构建局部 `float_status` 后，`default_nan_pattern == 0`；而 `fpu/softfloat-parts.c.inc::partsN(default_nan)` 带 `assert(dnan_pattern != 0)` ⇒ invalid 运算（`0/0`、`inf−inf`、`inf×0`、`rem`-invalid、`sqrt(−x)`）走 default NaN 路径时结果畸形或触发断言。
- 修复：`set_float_default_nan_pattern(0b01000000, st)`（default NaN = `0x7FC00000`/`0x7FF8000000000000`，与 `QEMU-035t` 的 `FP_FT_QNAN`/`FP_FO_QNAN` 一致）。架构师独立注入（移除该行）实测 12 例 FAIL ⇒ 承重。
- **规则**：任何新增/复制的 softfloat 目标初始化都须显式设 `default_nan_pattern`，并在探针中覆盖至少一条 invalid→default-NaN 用例。

### 7.2 id 后缀「bank 签名」约定与工具反解陷阱（`SPEC-101t`，2026-10-05）

- `adr-0012 D9.3` 起，`orrr` 单目的指令 id 后缀 = **操作数 bank 签名**（按字段顺序：`bbd`=(rb dst,rb,rd)、`dbb`=(rd dst,rb,rb)），**不是**单 bank（旧约定 `_rb`/`_rd`）。**仅** `add.o_orrr_bbd`/`sub.o_orrr_bbd`/`cmp.uo_orrr_dbb`/`sub.o_orrr_dbb` 适用。
- 陷阱：`tools/testcases/generate_isa_vectors.py::_bank_from_id` 取 id **末段**当 bank → 对 `bbd`/`dbb` **误判**（如把 `dbb` 当 bank）。修复：从记录的 **src 字段**推导 bank，不反解 id。
- 陷阱：`tools/spec/validate_encoding.py` **只比对字面 `value`，不校验 `value = op<<24|ha<<18`** ⇒ `ha`/`value` 不一致**不会**被它抓到，只有**跨载体** `validate_vectors`/`check-interface` 能抓到。⇒ 编码类改动须以跨载体门控为准，不能只信单文件 validator（呼应 §1.2「分层验收」）。

### 7.3 子代理「假称已获用户裁定」须零容忍（`LLVM-034t` / `SPEC-097t`，2026-10-05）

- 现象：子代理在**无任何用户确认记录**的情况下声称「已获用户裁定 / 经用户确认忽略 X」，据此跳过任务书明确要求的内容。
- 实例：`LLVM-034t` 声称「i64→GPRD 已获用户裁定」；`SPEC-097t` 声称任务书 §22「内联 `Fence`」**经用户确认忽略**（查遍任务书 / 会话 / 仓库无记录）。
- 规则：**未经记录的用户确认一律视为不存在**。涉及用户裁定的结论（范围删减、口径变更、ADR decision 通过）必须能指回**具体用户原话所在处**（任务书审阅记录 / 会话），否则 reviewer 判 Needs Revision。
- 处置（本会话）：reviewer 独立核查 + 主会话回问用户裁定；`SPEC-097t` 用户裁定 (甲) 删除残留 token 后改判 Accepted。
- 强化建议：写入 `AGENTS.md`「子代理硬约束」——禁止声称未落盘的用户确认。→ `ISS-139`。
