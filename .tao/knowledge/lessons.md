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
- **组件（QEMU）场景再审（`QEMU-044t`，2026-10-08）**：「源码还原 ≠ 二进制还原」在组件场景**再次成立**——engineer 的 `.work/evidence/QEMU-044t/run.sh`（合并注入自检）与 reviewer 的**独立注入**（`if (0 && …)` 短路 trap mask）均走「`cp` 备份 → 注入 → **重建** → FAIL → `cp` 还原 + `md5` 对账 → **重建** → 回绿」；**若只 `cp` 还原源码不重建，探针会跑在注入过的二进制上**，回绿判据不成立。还原**禁用** `git checkout`/`git restore`/`git stash`（会连带清掉未提交改动），一律 `cp` + `md5` 对账。相关：§2.3（二进制 sha 随 commit 变化）、§8.4（独立注入用临时树 + `cp`/md5）。

### 2.6 注入/验证的脆弱点无结构性拦截（原 `ISS-088`）

- 记录的脆弱点：**行号定位**（源码/文件变动后失配）、**空注入**（模式未命中却静默继续）、**手改污染**（注入态残留）、**注入无鉴别力**（断言恒真）。
- 候选方案（用户 2026-10-03 裁定**暂不修，仅登记**）：新增 `tools/infra/inject_check.py`——唯一定位（锚点命中计数须为 1）+ sha 断言（改前/改后/还原一致）+ 要求被检命令非零退出 + `trap` 复原，退出码即判决。
- 来源：原 `ISS-088`；`INFRA-042t`（2026-10-05，`Process-04 §3` 归档前置梳理；原 §2，2026-10-06 因新增 §1「里程碑生命周期」顺延）判定其为**方法论/工具陷阱记录**而非待办 issue，自 `issues.yaml` 移入本文件（id 不复用）。

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

- `docs/m1-retrospective.md`、`docs/m2-spec-planning.md`、`changelog.md`、全部已验收任务书、`.tao/archive/SimRISC-0.5.3/` 中的旧路径保留（历史快照）；如需全仓一致再另行裁定。

### 5.4 `validate_vectors.py` 变更历史（审计追溯，`ISS-024`）

- 记录：`002t`→`003t`→`004t` 两次**纯新增**，**未弱化**既有断言（审计追溯基线）。
- 来源：原 `ISS-024`；`INFRA-033t`（2026-10-04）判定其为**审计记录**而非待办 issue，移入本文件（id 不复用）。

### 5.5 F7 守卫基线（参照基准，`ISS-032`）

- 记录：`005t`→`006t`→`007t` 形成单一 `if/elif` 守卫块，F7 守卫基线已完整，作为**参照基准**。
- 来源：原 `ISS-032`；`INFRA-033t`（2026-10-04）判定其为**基线记录**而非待办 issue，移入本文件（id 不复用）。

### 5.6 只读清单门控范式：TOML 锁 + `--root` 临时树注入 + `if errors` fail-closed（`SPEC-119t`，2026-10-07）

- **范式（可复用）**：对「不许改的只读清单」（此处 = 上游 20 册 `spec/`）做**机械门控**，三要素：
  1. **TOML `[[…]]` 锁 + 复用既有 checker 体例**：逐项 `sha256` 锁于 `manifests/*.lock.toml`，checker 复用既有 `check_index_blobs.py`/`check_dirs.py` 范式（manifest 驱动、`--verbose`、`--root` 覆盖、只读、非零退出），**不另造轮子**。
  2. **`--root DIR` 让「临时树注入」成为默认自测手段**：checker 从 `<root>/manifests/*.lock.toml` 读锁、逐 `path` 相对 `<root>` 解析 ⇒ 注入/还原全在 `/tmp/opencode/<任务ID>/` 的**临时树**内进行，**不触碰真实仓库**；还原一律 `cp` 备份 + md5 对账（**禁** `git checkout/restore/stash`，见全局「注入/改动的还原纪律」）。
  3. **fail-closed 判据用 `if errors:` 而非 `if mismatches:`**：锁**残缺**（某条缺 `sha256` / 缺 `format` / 条目为空）时，若只判「被锁文件失配数」会 `mismatches==0` ⇒ 误返回 0（**fail-open**）。必须让**任何**锁解析错误 / 文件不符 / 缺失都计入 `errors`，并据 `errors` 非零退出——「锁本身坏掉」也必须 FAIL。
- **反例门控须覆盖「锁残缺」类**（改册 / 删册 / 改锁值 / 缺 `format` / 空条目 / 缺 `sha256`），**不能只测「被锁文件被改」**——否则 fail-open 路径不被证伪。
- **门控类任务的「变更集」定义 = tracked `git diff` ∪ untracked `git status`**：新建文件（untracked）不出现在 `git diff`，判断「改了哪些文件/是否越界」须用 `git status --porcelain -uall`（或并集），并加 `git -c core.quotePath=false`（否则非 ASCII 路径被转义致集合比较假失败）。
- 落地见 `manifests/spec-readonly.lock.toml` + `tools/infra/check_spec_readonly.py` + `make check-spec-readonly` + `spec/Process-06-spec目录保护规范.md`（`SPEC-119t`）。

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

### 6.6 仓库外全局 agent 规则未同步新验收规程（原 `ISS-087`）

- 缺口：`~/t.a.o/opencode/agent/{reviewer,engineer}.md`（仓库外全局 agent 规则）未同步仓库内的新验收规程——reviewer 缺「一键证据脚本」「不另写等价验证脚本」「强制独立注入一次反例」；engineer 完成区规范未含「交付一键证据脚本」。
- 处置约束：`~/t.a.o/**` **不得擅动，须用户批准**（仓库外、非本仓版本控制）。
- 来源：原 `ISS-087`；`INFRA-042t`（2026-10-05）判定其为**过程记录（仓库外同步缺口）**而非本仓待办 issue，自 `issues.yaml` 移入本文件（id 不复用）。

## 7. 教训条目

### 7.1 softfloat 目标必须显式设 `default_nan_pattern`（`QEMU-037t`）

- `fp_status_init` 用 `memset(st,0,...)` 构建局部 `float_status` 后，`default_nan_pattern == 0`；而 `fpu/softfloat-parts.c.inc::partsN(default_nan)` 带 `assert(dnan_pattern != 0)` ⇒ invalid 运算（`0/0`、`inf−inf`、`inf×0`、`rem`-invalid、`sqrt(−x)`）走 default NaN 路径时结果畸形或触发断言。
- 修复：`set_float_default_nan_pattern(0b01000000, st)`（default NaN = `0x7FC00000`/`0x7FF8000000000000`，与 `QEMU-035t` 的 `FP_FT_QNAN`/`FP_FO_QNAN` 一致）。架构师独立注入（移除该行）实测 12 例 FAIL ⇒ 承重。
- **规则**：任何新增/复制的 softfloat 目标初始化都须显式设 `default_nan_pattern`，并在探针中覆盖至少一条 invalid→default-NaN 用例。

### 7.2 id 后缀「bank 签名」约定与工具反解陷阱（`SPEC-101t`，2026-10-05）

- `adr-0012 D9.3` 起，`orrr` 单目的指令 id 后缀 = **操作数 bank 签名**（按字段顺序：`bbd`=(rb dst,rb,rd)、`dbb`=(rd dst,rb,rb)），**不是**单 bank（旧约定 `_rb`/`_rd`）。**仅** `add.o_orrr_bbd`/`sub.o_orrr_bbd`/`cmp.uo_orrr_dbb`/`sub.o_orrr_dbb` 适用。
- 陷阱：`tools/testcases/generate_isa_vectors.py::_bank_from_id` 取 id **末段**当 bank → 对 `bbd`/`dbb` **误判**（如把 `dbb` 当 bank）。修复：从记录的 **src 字段**推导 bank，不反解 id。
- 陷阱：`tools/spec/validate_encoding.py` **只比对字面 `value`，不校验 `value = op<<24|ha<<18`** ⇒ `ha`/`value` 不一致**不会**被它抓到，只有**跨载体** `validate_vectors`/`check-interface` 能抓到。⇒ 编码类改动须以跨载体门控为准，不能只信单文件 validator（呼应 §1.2「分层验收」）。

### 7.3 子代理的用户裁定须**原样落盘**（子会话问答对父会话不可见）（2026-10-05 机制订正）

- **机制**：`engineer`/`reviewer` 等子代理在**其自身子会话**里用 `question` 工具**直接征询用户**，用户当场作答；但**父会话（主会话）只能看到子代理的最终报告**，看不到那次问答。于是报告里一句「用户裁定 X」在父会话**无法核对**。
- **订正（原结论作废）**：曾把 `LLVM-034t`「i64→GPRD 已获用户裁定」、`SPEC-097t`「内联 `Fence` 经用户确认忽略」判为「**假称**」（原 `ISS-139`）。经用户 2026-10-05 澄清：**这些裁定确为真实用户裁定**，症结在**父会话不可见**，非子代理造假。**删去「假称 / 零容忍」定性。**
- **规则**：
  1. 子代理**取得用户裁定后，须把用户原话（或问答摘要）原样写入任务书**（完成区 / 审阅记录），使父会话与事后审计可追溯。
  2. 主会话**不得**仅因「父会话无记录」就否定子代理报告的用户裁定、反复回问同一问题（除非有**相反证据**）。
  3. 涉及用户裁定的结论（范围删减、口径变更、ADR decision 通过）仍应可追溯到**具体原话**——通过规则 1 落盘保证。
- **原 `ISS-139` 已并入本条**（id 退役、不复用）。

### 7.4 验证命令产物不得落入仓库测试目录（`LLVM-048t`，2026-10-05）

- 现象：`llc` 验证命令在 `tests/codegen/` 就地生成 `ptr_add_offset.s`，随 `git add -A` 误入提交（reviewer 审计未捕获，主会话在提交输出中发现）。
- 规则：证据/验证命令一律在 `.work/<任务ID>/` 或 `/tmp/opencode/<任务ID>/` 下运行，产物勿落仓库源/测试目录；收尾（`/complete`）必须核对 `git status --untracked-files=all` 干净。
- 已处置：`dca57b8` 移除该文件 + `.gitignore` 加 `tests/codegen/*.s|.o|.bin`。（原 `ISS-146` 已随本条并入 `lessons.md`；该 id 退役、不复用。）

### 7.5 擅自修改上游 spec 册（`SPEC-114t` round1，2026-10-07）

- **事故经过**：`SPEC-114t`（SEE/semihosting 规范正文）**round1**，engineer 在**无用户授权**下修改了**上游只读册** `spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/DADAO-22-SBI-主管系统二进制接口.md`（各插入 2 行，把「实现范围」「semihosting 承接/返回」写进上游册）。
- **用户裁定（原话，2026-10-07，经主会话转达——子会话问答对父会话不可见，见 §7.3）**：「**DADAO-21 和 DADAO-22 都不应该做修改**」；「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」。**上游只读册清单（用户全选，共 20 册）** = `DADAO-1x`(11/12/13) + `DADAO-2x`(21/22/23) + `SimRISC-00..12` + `Toolchain-01`。
- **根因（三处，须一并堵住）**：
  1. **架构阶段**把上游只读册写成任务书的**可改对象**（`SPEC-114t` round1 任务书「输出」item 2 原文把 `DADAO-12` 本体列为待改），下游 engineer 据此执行——**职责边界失守**（改 `spec/` 从未获用户授权）。
  2. **下发前预检**只有 4 项（内部一致性 / 依赖链 / 验收可执行性 / 与 spec/vectors 一致），**没有**「拟改文件清单 × `spec/` 清单」这一关 ⇒ 命中 `spec/` 而缺用户授权时不阻断。
  3. **无机械门控**：`spec/` 上游只读册没有哈希锁，改动在 `make check` 中**零告警**（round1 的 `make check` 全绿，未被任何门控拦下）。
- **防复发（机制化，`SPEC-119t` =「spec 目录保护：只读哈希锁 + 门控 + 流程约束」）**：
  - **哈希锁**：`manifests/spec-readonly.lock.toml`（上游 20 册逐册 `sha256`）+ `tools/infra/check_spec_readonly.py` + `make check-spec-readonly`（**纳入 `make check`**）⇒ 未更新锁而改册 ⇒ **门控 FAIL**；确需修改（先经用户授权）时同一变更内更新锁。
  - **下发前预检第 5 项**：`/dispatch` 前把**拟改文件清单 × `spec/` 清单**逐一对照——命中 `spec/` 而无**用户授权原话** ⇒ **BLOCKED**（`AGENTS.md`「下发前预检」由 4 项扩为 **5 项**）。
  - **reviewer / architect 固定检查**：验收/提交前固定执行 `git diff --name-only`（提交前 `git diff --cached --name-only`）与 `spec/` 清单交叉；有交集而缺用户授权证据 ⇒ reviewer 判 `Needs Revision` / architect 拒绝提交。
  - **规则正文**入 `spec/Process-06-spec目录保护规范.md`：**`spec/` 下任何新增/修改/删除（含 v5 自定册 `Machine-*`/`Process-*`/`spec/README.md`）均须用户"事先"明确允许，授权原话落盘**；上游只读册只作**只读引用**（引 `§` 章节号，不改一字）。
- **已处置**：`DADAO-12`/`DADAO-22` 以 **`cp`+`md5` 还原**到 base `96f09f1`（md5 `83dec5ea…`/`a3070bd4…`，逐字一致；**未用** `git checkout/restore/stash`，见全局「注入/改动的还原纪律」）；`SPEC-114t` round2 返工后上游册**零改动**（20/20 md5 SAME），相关正文一律落新建 `spec/Machine-01-测试机运行环境.md`。
- **✅ 已落地（`SPEC-119t`，2026-10-07）**：上「防复发」三处机制**全部实现并通过验收**——`manifests/spec-readonly.lock.toml`（上游 20 册 `sha256` 锁）+ `tools/infra/check_spec_readonly.py`（`if errors` **fail-closed**）+ `make check-spec-readonly`（**纳入 `make check`**）+ 规则正文 `spec/Process-06-spec目录保护规范.md`（①–⑤ 均 MUST）。reviewer **`Accepted`**、architect 交叉复核通过（20 册 `sha256` 独立重算全等、路径清单无多无漏、`spec/` 变更仅 `Process-06`+`README.md`〔无上游册〕、6 类反例注入均 FAIL 且 `cp`+md5 还原回绿）。范式见 §5.6。

### 7.6 下发前预检第 2 项须核「本任务**验证手段**所需的全部前置」，非仅「任务书声明的依赖」（`SPEC-115t` BLOCKED，2026-10-07）

- **事由**：`SPEC-115t`（re-scope：`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `scope: excluded` → `m1`）**依赖字段**列 `SPEC-114t`/`SPEC-113t`/`SPEC-119t`；但工程师在改动前核对**验收手段** `make check`，实测发现 `scope: excluded → m1` 会撞 **3 个跨模块门控**（均在 `make check` 内）：
  1. `tools/testcases/validate_vectors.py` —— `tests/vectors/inventory.md` 的 M1 行集必须 == `contracts/opcodes.yaml` 的 `scope==m1` 集（探针实测 4×`INVENTORY MISSING`）；
  2. `tools/integ/check_interface_alignment.py` —— `inventory.md` M1 计数 == `opcodes` M1 计数，且**每个 M1 `format` 族须有 lit `; OBJ:` 覆盖**（探针实测缺 `['ciii','crrr']`）；
  3. `tools/llvm/validate_instrinfo.py` —— **每条 `scope==m1` 记录须有唯一 `.td` def**（探针实测 `151/155`）⇒ **必须** `LLVM-060t` 的 `.td`。
  而 `LLVM-060t`/`TESTCASES-033t` 在原 Wave 顺序中**在 `SPEC-115t` 之后** ⇒ **本任务单发必红**，工程师 **BLOCKED（未实施、工作树零改动）**。
- **根因**：`AGENTS.md`「下发前预检」第 2 项（**依赖链实际可用性**）被**窄化**为「核任务书 `依赖` 字段所指向的任务是否已验证/存在」，**未核**「**本任务验证手段**所需的**全部**前置（含跨任务的门控载体/工具产出）」。`SPEC-115t` 的 `依赖` 字段本身**没有漏**——漏的是「**门控载体（`inventory.md`/lit `; OBJ:`/`.td` def）由谁产出、是否在依赖链上游**」这一层。
- **教训 / 判据（可复用）**：下发前预检第 2 项须把验收命令（如 `make check`）**逐个子门控拆开**，对**每个子门控**问三问：
  1. 它**读哪些文件**（门控载体）；
  2. 这些文件**由谁产出**（本任务？同仓库前置？跨模块前置？）；
  3. 产者是否已在**本任务之前**（依赖链上游）且**已验证**？
  凡「产物须在**同一原子变更**内出现的门控载体」（如 `inventory.md` 行集 == `scope==m1` 集）⇒ 必须**并入本任务文件集**或**前置**，不得留在下游任务（否则成环或红）。
- **处置（本轮）**：用户裁定「**先 `LLVM-060t` 再 `SPEC-115t`**」⇒ `SPEC-115t` 重排（`LLVM-060t` 前置）+ 文件集扩至门控载体（`tools/spec/generate_opcodes.py`/`tests/vectors/inventory.md`/`tools/llvm/validate_instrinfo.py`）；`encode_cfx` 另立 `SPEC-120t`。详见 `SPEC-115t`/`INTEG-019k` 审阅记录「第 2 轮/第 7 轮 architect 重排落纸」。
- **配套**：与 §7.2（跨载体门控：`validate_encoding` 只比字面值、跨载体门控才抓得到）同类——**编码/范围类改动的验收，须以跨载体门控为准，并识别其载体产者**。

### 7.7 生成器随产物入库：产物入 git ⇒ 生成器不得只留 `.work/`（`LLVM-060t`，2026-10-07）

- **事由**：`LLVM-060t` round1 把 `DADAOCfxAlias.inc`（**已入 git** 的产物，落 `components/llvm-project/patches/**/AsmParser/DADAOCfxAlias.inc.patch`）的**生成器**留在 `.work/LLVM-060t/gen_cfx_cpp_table.py`；因**原任务书允许文件集**把 `tools/**` 限为 `validate_instrinfo.py`，engineer 未越界、生成器**未入库**（`.work/` 被 `.gitignore` 整体忽略）。
- **根因**：任务书「允许文件集（验收 10 无残留清单）」按「**任务范围**」而非「**产物可否复现**」定，漏了「产物入库 ⇒ 生成器随之入库」这一条。
- **判据（可复用）**：**凡产出被提交（入 git）的生成器/脚本，必须随产物保留在非易失位置**（优先 `tools/<module>/`，否则 `.work/<任务ID>/`）——`AGENTS.md`「临时目录」条已定；判据是**产物是否入库**，而非「脚本是否只服务一个任务」；**「一次性」只描述用途，不等于可丢弃**。任务书的「允许文件集」须**显式含**「随产物入库的生成器」这一项（`LLVM-060t` 由 architect 追加输出 6b + 约束 + 验收 10 修复）。
- **落地**：`tools/llvm/gen_cfx_alias_table.py`（**复用** `tools/spec/gen_cfx_aliases.py` 投影函数、不另造轮子；`--out` 便于对临时路径校验）随产物入库；生成物内 provenance 行（`// Generator:`）指向生成器当前路径（经用户裁定授权改该 1 行注释）。**可复现性须以 `cmp` 逐字节证**（重跑生成器 → worktree `.inc` 不变 ⇒ `git diff <lock-commit> -- .inc` 与已入库 patch `cmp` EXIT=0）；architect 交叉复核时**须自己跑一遍生成器 + `cmp`**，不得采信他人输出。

### 7.8 re-scope 的双层（生成器 + yaml）与跨任务契约（`MC_ONLY_EXCLUDED_IDS` 加/减）（`SPEC-115t`/`LLVM-060t`，2026-10-08）

- **事由**：`SPEC-115t`（re-scope）有两处易漏的「双层」结构：
  1. **生成物双层**：`contracts/opcodes.yaml` 由 `tools/spec/generate_opcodes.py` 生成（git 历史中二者恒同改）⇒ 只改 yaml 会使生成器失同步（下次重跑即回退）。
  2. **跨任务门控载体**：`tools/llvm/validate_instrinfo.py` 的 `MC_ONLY_EXCLUDED_IDS` 是**跨任务共享集合**，其内容随 `scope` 状态改变——`LLVM-060t` 阶段 4 条仍 `scope: excluded` 但 MC 层需 `.td` def ⇒ **加入**；`SPEC-115t` re-scope 为 `m1` 后 ⇒ **移除**（否则 `missing_mc_only` / `bad_non_m1` FAIL）。
- **判据（可复用）**：
  1. **生成物改动须「改生成器 + 重跑」**，禁只手改生成物；重跑须 **byte-identical / 幂等**（两跑 md5 相等），并作为验收项（`SPEC-115t` 验收 9）。
  2. **跨任务共享的集合型门控载体**（其内容随某任务的状态改变）⇒ 须在**两个任务的接口**写明「**谁加、谁减**」，并把「本任务应移除/加入」列为**接收变更方**的验收项 + 机械核验（`SPEC-115t` 验收 10：`MC_ONLY_EXCLUDED_IDS` 不再含 4 条、`fence_oiii_imm` 保留）。
- **配套**：与 §7.6（下发前预检第 2 项须识别门控载体产者）同类——**范围类改动的门控载体可能横跨多个任务**，须在规划阶段显式定「加/减」归属，否则单发必红或留下失同步的隐藏回退。

### 7.9 证据脚本对「已提交变更」的断言须带提交范围（`BASE..HEAD`），否则提交后假 FAIL（`SPEC-115t` round1→round2，2026-10-08）

- **事由**：`SPEC-115t` round1 的证据脚本 `.work/evidence/SPEC-115t/run.sh` 用**裸 `git diff`** 检测「锁文件变更」「生成器改动」（`git diff -- manifests/…` / `git diff --name-only`）；但 architect 已把交付物 **WIP 提交**，而裸 `git diff` 比较的是**工作树 vs HEAD** ⇒ 变更已入 HEAD、工作树干净 ⇒ 输出为空 ⇒ 两项断言**假 FAIL**（`expected=2 actual=0` / `[FAIL] 9 generator modified`），证据脚本 EXIT=1。
- **判据（可复用）**：证据脚本中凡断言「某变更存在 / 某文件被改」的 git 调用，若被测产物**可能已被提交**，**必须带提交范围**（`git diff "$BASE_COMMIT"..HEAD -- …`，`BASE_COMMIT` = 本任务基线提交，可经环境变量覆盖以验证 FAIL 路径）；**禁裸 `git diff`**。仅「检测工作树残留」用 `git status --porcelain`（不依赖是否已提交，合理保留）。
- **配套**：与 §2.1（管道退出码陷阱）同为「**证据脚本自身缺陷导致假 FAIL/假 PASS**」类——**证据脚本本身也是交付物**，其 git 调用须经受「提交后仍应回绿」的自检；reviewer 审核脚本时须**逐条核 git 调用的 range**（`SPEC-115t` reviewer round2 即如此）。
- **指向**：`SPEC-115t` 落地 = round2 新增 `BASE_COMMIT`（默认基线）+ 检查 7 追加 `$BASE_COMMIT..HEAD` 越界检查；规则见 §8.7。

### 7.10 `ADR-0016 D9` 点名项被改述收窄、门控来源未沿调用链核（`INFRA-047t`，2026-10-07）

- **事由**：`INFRA-047t` 的目标之一是「**门控/执行器改从 install 根取可执行**」（`ADR-0016 D9`）。第 1 轮实现与验收（判 `Accepted`）时，`make check` 的子门控 `check-qemu-semantics` 仍经 `tests/scripts/run_qemu_test.py` 从 `.work/build` 取 QEMU——**未被发现**：任务书把 `D9` 点名清单**改述**为「`Makefile` 路径变量 + `tools/integ/run_{codegen,elf}_e2e.py` + `tests/**/lit.cfg.py`」，漏掉 `D9` **原文点名**的 `run_qemu_test.py`；下发前预检又把验收 grep 范围收窄到 `Makefile`+`tools/infra`+`tools/integ`，使该缺口在验收中**不可见**。reviewer 在 B 节已瞄到，但因「超出任务界定」未阻塞判决。
- **根因**：① **点名清单被概括改述**，未逐字列举、逐项核到底；② 核对门控可执行来源只 `grep` 工具目录，未从 `make check` 依赖表**沿调用链**追到 `tests/scripts/`（门控常经脚本**间接**取可执行）。
- **处置/闭合**：architect 范围修正后**重开一轮**（第 2 轮 reviewer `Accepted`），补修 `run_qemu_test.py` 改根；`tests/scripts/verify_harness_dump.py` 经**调用链反证**为非门控 ⇒ out-of-scope（登记遗留）。
- **规范**：见 §8.1。

### 7.11 生成物落点迁移未同删旧产物目录、脚本比对 git 路径受 `core.quotePath` 干扰（`INFRA-048t`，2026-10-07）

- **事由**：`INFRA-048t` 把 `test-codegen`/`test-elf`/lit 的运行产物落点从源码树/构建树迁到 `.dadao/tests/`，并要求清理 `.gitignore` 旧忽略规则 `tests/llvm/codegen-e2e/`。**下发前预检**发现：该旧目录**实际存在**（内含 `arith_*.bin/.o/.s/.prog.s` 等运行产物），若只清忽略规则而不删目录，运行产物会暴露为未跟踪残留，与任务自身「无残留」验收**自相矛盾**（实测清规则后 `git status --porcelain -uall` 多出 60 个 `??`）。另：lit scratch 的**实际**旧落点（`.dadao/cross-toolchain/test-output/`，因 `INFRA-047t` 改了 `tools_dir` 默认）与任务书描述的 `.work/build/llvm/test-output/` **不一致**。证据脚本用默认 `git status` 匹配中文任务书路径，自审实测 `bad-count=1`（**假阳性**：非 ASCII 路径被加引号 + 八进制转义）。
- **根因**：① 迁移只「改落点 + 清规则」，漏「删残留旧产物目录」；② 旧落点路径以**任务书描述为准、未实测**（已被上游任务改变）；③ 脚本比对 git 路径**未关 `core.quotePath`**。
- **处置/闭合**：同删旧产物目录（`tests/llvm/codegen-e2e/`、`.work/codegen-e2e-elf`）；证据脚本改 `git -c core.quotePath=false`；reviewer `Accepted` + architect 交叉复核。
- **规范**：见 §8.2。

### 7.12 误把 `.PHONY` 续行当 `make check` 依赖（`SPEC-117t`，2026-10-07）

- **事由**：`SPEC-117t` 的约束原写「`make check`（`check-spec-refs` 等）EXIT=0」，下发前预检据此**断言**「`check-spec-refs` 确在 `make check` 依赖链内」，并引 `Makefile:41` 为据。**实测**：`Makefile:41` 是 `.PHONY` 清单的**续行**（`... check-spec-refs check-spec-drift ...`），**不是**依赖；`check:`（`Makefile:297`）的依赖行**不含** `check-spec-refs`；其目标处（`Makefile:336`）注释明示 `# Standalone target, not part of \`make check\`.`。
- **根因**：把 `.PHONY` 伪目标声明**误读**为依赖关系；且行号引用未逐行核对（reviewer 记录中曾把注释行 `336` 误记为 `337`，仅偏一、不影响结论）。
- **处置/闭合**：主会话更正 + 工程师实测该两门控单独跑均 `EXIT=0`；规范正文与验收分别写明「standalone，不在 `make check` 依赖链内」。
- **规范**：见 §8.3。

### 7.13 核「已 `Accepted` 决策未被静默改写」不能只凭 `git diff` hunk（`SPEC-113t`，2026-10-07）

- **事由**：`SPEC-113t` 按 `Process-03`「不直接改写已 `Accepted` 的决策」就地修订 `ADR-0004`：新增 `## 修订` 条目（`R1`/`R2`/`R3`）表达取代/覆盖关系，**不得**改动受保护决策 `D1`/`D2.1`/`D3`/`D4`/`D5`/`D6` 正文。工程师原拟用 `git diff` 的 hunk（删除行）判定「未静默改写」，但 hunk 边界**脆弱**：修订条目里**引用** D 项正文措辞（如「覆盖 `D1` 内存映射表…」）会与正文改动**混淆**。另 `ADR-0004 R2` 括注称「（`D3` 标 `Superseded`）」，实测 `D3` 节标题与节内**均无** `Superseded`——该「已标」实为**文件级取代声明**，非节内标记（措辞不精确；决策成立：`Process-03`「新增 ADR 或标注 `Superseded`」已由新增 `ADR-0020` 满足）。
- **根因**：① 判「正文未改」依赖脆弱的 `git diff` hunk 边界；② 节提取**未做非空校验**（空提取 ⇒ 两侧都空 ⇒ 假 PASS）；③ 「已标 `Superseded`」未核到**节内**标记。
- **处置/闭合**：改用「`git show HEAD:<file>` × 工作树**按节 diff + 非空校验**」；reviewer 独立注入（临时树 `cp`+md5）；architect 交叉复核；`ADR-0004 D3` 标题下补 in-place 标记 `> **Superseded by ADR-0020 D8**`。
- **规范**：见 §8.4；机械核验范式另见 §5.6。

### 7.14 任务书「事实源」段的「唯一 / 仅」类断言须下发前全量实测（`SPEC-116t`，2026-10-08）

- **事由**：`SPEC-116t`（`Toolchain-01 §1` 格式类口径同步）任务书「事实源」段写 `crii` 为 **「唯一」** `scope: excluded` 的 M1 格式。实测（`python3` 逐 `format` 统计 `contracts/opcodes.yaml`）：`scope==excluded` 的格式共 **3** 个——`crii`×2 / `oiii`×1（`fence`）/ `orrr`×8（`lr_*`+`sc_*`）。
- **处置**：engineer **以实测为准**——`§1` 的 cfx 子句**只写 cfx 组**（`crrr`/`crii`/`ciii`），`crii` 据实 = `excluded`，**未**把 cfx 组外的同值项（`oiii`/`orrr`）混入该子句（避免臆断、避免扩义）；完成区记明更正，reviewer `Accepted`。
- **教训**：任务书「事实源 / 事实核实」段凡出现「**唯一 / 仅 / 全部 / 共 N 个**」类**计数或集合**断言，须在**下发前**对生成物**全量实测**并落纸（与 §4.6 同类），不得沿用旧任务/历史台账的表述；子句若限定某**子集**（如「cfx 组」），只在该子集内据实书写，不把子集外的同值项混入。

### 7.15 证据脚本断言依赖「未提交工作树」⇒ 提交后假 FAIL；reviewer 误以「pre-commit 设计」放行（`SPEC-120t`，2026-10-08）

- **事由**：`SPEC-120t` round1 证据脚本的 C10 由**工作树** `git status --porcelain` 计算「非 `.tao` 改动集」并断言 = 2 文件。architect **WIP 提交前**运行 PASS（工作树 = 交付物）；**WIP 提交后**工作树干净 ⇒ C10 必然为空 ⇒ **假 FAIL**（reviewer round1 实测 `C10 FAIL`，却以「post-commit 已知限制、不阻塞验收」判 `Accepted`）；`:140` 诊断行裸 `git diff --name-only` 同类。
- **根因**：reviewer round1 **未按 §8.7 rule 4**「逐条核 git 调用是否带 range」判，反而接受「pre-commit 设计」的放行理由——把「提交后必红」当作可接受的脚本设计。
- **处置/闭合**：**主会话依 `lessons §8.7` 推翻 round1 `Accepted` ⇒ 改判 `Needs Revision`**（判例：此为**首次由主会话推翻 reviewer `Accepted`**）；engineer round2 **修一类**（全脚本枚举 6 处 git 调用：C10 改 `$BASE_COMMIT..HEAD`；C9/C11 工作树残留合理保留；诊断行 2 处非断言）⇒ round2 reviewer `Accepted`（`BASE_COMMIT=HEAD` 重放复现 C10 FAIL，证断言非恒真；`cp`+md5 注入/还原有鉴别力）。
- **规范**：见 §8.7 rule 5。

### 7.16 规范以「委派 / 占位」把决策留给实现任务 ⇒ 覆盖缺口须落台账 + 提请授权，不得静默改 `spec/`（`QEMU-049t`，2026-10-08）

- **事由**：`QEMU-049t` 按 `ADR-0020 D15` 在机器模型落地三条**实现口径**（**`umon` 段（`addr[47:42]==0`）越界访问/取指 ⇒ `CFXMEM`（`0x81`）**；**其余段（含旧 `power` 段 63）⇒ 测试机约定 `unmapped`（`0x87`）**；**RAM@0 = 16 MiB**）。核 `spec/Machine-01 §1` 现行措辞**未完全覆盖**：① `§1.1` 表 RAM@0「大小」列仍是占位 `【待 QEMU-049t 定】`；② `§1.2` 末条把「精确路由与 RAM@0 容量」**显式委派**给 `QEMU-049t`（未写口径）；③ `§1.2`「层次与适用」条的 `CFXMEM` 措辞（「cfxha 段内的非法子区间、越界访问/取指」）按字面**也覆盖 `power` 段 63**，与已落地路由（`power` 63 ⇒ `0x87`）**歧义**。
- **根因**：规范正文以「**委派给某任务落地**」或「**留占位**」的方式把决策权下放 ⇒ 该任务**必然**产生「**实现已定口径 vs 规范正文未覆盖/歧义**」的**覆盖缺口**；缺口本身是规范侧事项，不能由实现任务顺手改 `spec/` 收口。
- **处置/闭合**：engineer 与 architect **均未改 `spec/`**（守 `§8.5`/`Process-06`）——实现口径由门控 `check-interface` **新增 6 断言**（`RAM0_BASE`/`RAM0_SIZE`/`init_ram`/`add_subregion`/`EXIT_CFXMEM=0x81`/`CFXHA_UMON=0`）固化为**事实载体**；缺口 + **拟改文本**登记 **`ISS-166`**，交主会话提请用户授权收口（授权前 `spec/` 一字不改）。reviewer `Accepted`、architect 交叉复核通过。
- **教训 / 判据（可复用）**：任务若落地规范「委派给本任务 / 留占位」的决策，须（i）在**规范正文以外**（任务书完成区 + `issues.yaml`）记明「已落地口径 + 规范对应段落现状（占位/委派/歧义）+ 拟改文本」；（ii）实现口径由**门控断言**固化（缺口在授权前即可机械核验、实现不依赖未授权的 spec 改动）；（iii）缺口**一律不改 `spec/` 收口**，登记 issue 并请用户**事先**授权，授权后在**同一变更**内同步该册 `sha256` 锁（若涉上游册）。

### 7.17 保护范围扩面（上游册 → 含 v5 自定册）须四处一致；立案前提「更新某册锁」须先实测锁实际包含哪些册（`SPEC-121t`，2026-10-08）

- **事由**：`SPEC-121t` 承接 `ISS-166`（收口 `Machine-01 §1` 越界路由/RAM@0 容量口径）。立案时原拟「**更新**锁中该册（`Machine-01`）`sha256`（其余 **19** 册不得变）」——该表述隐含前提「**锁已含** `Machine-01`」（因 `§1` 改动会改变该册 `sha256`）。architect 立案**实测**发现 `manifests/spec-readonly.lock.toml` **仅 20 册上游册**（`SimRISC-00..12` / `DADAO-1x` / `DADAO-2x` / `Toolchain-01`），**不含** `spec/Machine-01`（`spec/Process-06 §6` 明文「**不在锁内**：`spec/Machine-01`…」）⇒ 原前提**错误**（应为「其余 **20** 册」，且操作为**新增**而非**更新**）。经用户裁定「把 `Machine-01` 新增进锁」改为**新增**条目（锁内 **20→21**）。
- **根因**：① 「更新某册锁」类表述**隐含**「该册已在锁内」的**前提**，立案未先实测即沿用（同 §7.14/§8.8 同类：计数/集合类断言须全量实测）；② 把 v5 自定册纳入原「只保护上游册」的锁 = **保护范围扩面**，牵动**不止**锁清单——`Process-06 §5` 标题/正文「只保护上游 20 册」的**语义**、§6 **清单/计数/「不在锁内」注记**、**门控输出/help 措辞**（`upstream read-only spec volume(s)`）**四处**均须同步，否则规范与机制自相矛盾（「只覆盖上游」表述不再准确）。
- **处置/闭合**：用户裁定 ②/④/⑤ 授权——**新增** `Machine-01` 锁条 + `spec/Process-06 §5/§6` 同步（**语义扩面**至「含 v5 自定册 `spec/Machine-01`」）+ 门控措辞去「upstream」（checker docstring/`--help`/成功行 + `Makefile` help/注释，**逻辑零改动**）；`ISS-166` 结案。reviewer `Accepted`（**独立注入**改真仓库 RAM@0 容量 ⇒ checker MISMATCH ⇒ `cp`+md5 还原回绿，有鉴别力）、architect 交叉复核通过（独立核 `§1.1`=16 MiB / `§1.2` 新条+末条 / 锁 **21** 条且 `Machine-01` `sha256` 相符 / 既有 20 册 `sha256` 集合**逐条未变** / `Process-06 §1` 未改 / checker 去 `upstream` / `check-spec-readonly` `21 … OK` **EXIT=0**）。
- **残留（授权边界外，未改）**：`Process-06 §1`「**上游只读册**（清单见 §6）」的括注在 §6 含 v5 自定册后**字面略不精确**——`§1` **不在**用户授权范围（授权明文仅 `§5`/`§6`），故**未改**，登记「遗留」待另授权一行措辞修正。

### 7.18 验证型任务（无实现改动）亦须交付**可失败的专证据**，且「基线无缺口」结论须有**覆盖依据**（`QEMU-045t`，2026-10-08）

- **事由**：`QEMU-045t` 为**验证型任务**（范围收缩为「`QEMU-044t` 基线之上深化/验证 + 专探针」），交付**无组件补丁改动**（`components/**` 零改动）+ 新专探针 `tools/qemu/min_rom_probe_045t.py`（**14 用例**）。reviewer `Accepted`；architect 交叉复核确认「未发现 044t 基线缺口」结论**有覆盖依据**。
- **根因**：验证型任务易被误当「低风险」放过——（i）**无实现改动** ⇒ 若跳过反例注入，「证据脚本能失败」这一门控（`AGENTS.md`「验证脚本反例门控」）可能落空，只余「跑通即 PASS」的恒真叙事；（ii）「**未发现基线缺口**」若不配**覆盖面**依据，则等同于想当然（同 §7.14/§8.8 同类：集合/覆盖类断言须全量实测）。
- **处置/闭合**：验证型任务**亦**须交付**可失败的专证据**——本案证据脚本内置 **6 反例（A–F）合并注入** ⇒ **8 用例 FAIL** ⇒ `cp`+md5 还原 ⇒ **重建** ⇒ 回绿；reviewer 另做**独立注入**（`<<2`→`<<4`，与 A–F 不同、**特异**：只命中 escape 偏移路径 ⇒ 2 用例 FAIL 而 `reserved_illi` 仍 PASS）；且「未发现基线缺口」须由**用例覆盖面**兜底（14 用例**逐条对应**任务输出范围：trap 一般/`trap_mask`/reserved、escape 正/负/跨 cfx 禁止/允许、`cfx2rd`/`cfx2rc` cg0–cg7 全寄存器面、CFXREG 4 类），**非以 validator 绿灯 / 覆盖脚本充数**（对齐 `AGENTS.md`「**覆盖 ≠ 语义**」）。
- **残留**：无。

### 7.19 「复用上游共享层」须同时落地**接入点清单**，缺一即 SIGSEGV 或 CLI 被拒；「只写钩子」式范围低估（`QEMU-046t`，2026-10-08）

- **事由**：`QEMU-046t` 落地 semihosting，任务书约束字面为「**只写** `target/dadao/common-semi-target.c`（+ 接入点/异常枚举）」。实现中发现，**复用**上游共享层 `semihosting/arm-compat-semi.c` 除钩子文件外，还**必须**补齐三处接入点，否则功能不可达或直接崩溃：① **debug 地址翻译钩子**——共享层经 `cpu_memory_rw_debug()` 读写 guest 内存，该路径在 `sysemu_ops` 未实现 `translate_for_debug` 时回退调用 **NULL** 的 `get_phys_addr_debug` ⇒ **SIGSEGV**（需在 `target/dadao/cpu.c` 新增 `dadao_cpu_translate_for_debug`）；② **`-semihosting-config` 的 arch mask**——`DEF(...)` 带 `QEMU_ARCH_*` 掩码，`system/vl.c` 的 `qemu_arch_available()` 按此门控，DADAO 原不在列 ⇒ CLI 被拒（需扩 `qemu-options.hx`）；③ **Kconfig `select` + meson 挂钩**——共享层 `.c` 需经 `select ARM_COMPATIBLE_SEMIHOSTING if TCG` + `when: 'CONFIG_...'` 条件编译才编入 `libsystem.a`。另加 `cpu.h` 的异常枚举。两项超字面范围者（① ②）已按「**越界披露**」报备。
- **根因**：任务书按「**文件**」划范围（只写钩子文件），未按「**复用共享层所需的全部接入点**」划范围——共享层的**服务逻辑**虽可零改动复用，但其**触及宿主/CLI/构建的接缝**（内存访问、CLI 门控、编译接线）分散在多个文件，「只写钩子」隐含**低估**。此类缺口在**首次**触达共享层时才暴露（本次为全首次）。
- **处置/闭合**：实现补 ③ 项接入点、暴露并当场修 ①（SIGSEGV）与 ②（CLI 拒绝）；两项越界如实披露，reviewer 判「最小必要接线」`Accepted`；architect 交叉复核确认两处补丁**均为必要**（`translate_for_debug` 接入 `SysemuCPUOps`、`qemu-options.hx` 两处 `DEF` arch mask 均增 `QEMU_ARCH_DADAO`）。
- **残留**：无（「须在任务书输出中列全接入点」已提升为 §8.13 规范）。

### 7.20 还原方式再扩面：`git show <commit>:<path> > <path>` 亦属「从提交读回」，工作树有未提交改动时会丢改动（`QEMU-047t`，2026-10-08）

- **事由**：`QEMU-047t` reviewer 做**独立注入**（移除 `tests/scripts/bootrom.S` 的 SP 初始化 `set.zw rb1, wp1, 0x00f0` ⇒ `stack_in_ram0`/`handler_reached`/`app_exit_0` FAIL）后，**还原**用了 `git show HEAD:tests/scripts/bootrom.S > tests/scripts/bootrom.S`（理由：证据脚本注入 A 流程已删除其 `.preinject` 备份文件），而非另行 `cp`。
- **本次结果**：目标文件**已提交（在 HEAD 中）且工作树对该文件无未提交改动** ⇒ `git show HEAD:<path>` 读回的内容 == 原始内容（`md5` 相符、还原+重建后探针回绿），**未造成损失**。
- **根因 / 判据（可复用）**：`git show <commit>:<path> > <path>` **等同 `git checkout <commit> -- <path>` / `git restore`**——它把文件**覆盖为「提交中的版本」**，在**工作树对该文件有未提交改动**时会**静默丢弃**这些改动（且无 `cp` 备份可对账）。因此它与 `git checkout`/`git restore`/`git stash` **同类，属须避免的还原方式**（§2.5 / §8.4 rule 4 的禁用清单据此**扩充**）。
- **正解**：还原一律以**注入前 `cp` 备份 + `md5` 对账**为准，或**优先在临时树**（`/tmp/opencode/<任务ID>/`）注入（不触碰真实仓库）；二者均**不以 `git status`/`git diff` 干净作为「已还原」证据**（脏文件被清后也显示干净）。
- **提示**：本条**不否定该 reviewer 独立注入的有效性**（注入→FAIL→还原+重建→回绿流程成立、有鉴别力），仅**记录还原方式的偏差**并要求后续严格用 `cp` 备份。

### 7.21 门槛前置：门槛正向依赖的「路径 / 组合」若 ADR/规范未定义，须在门槛任务立案前裁定，不得默认可用（`QEMU-047t`/`INTEG-020t`，2026-10-08）

- **事由**：M5 门控 `make test-semihost` 正向 = 「**bootrom + 单/多 TU ELF 经 `-semihosting`**、console 捕获、`SYS_EXIT` 码」。`QEMU-047t`（新 bootrom）按 `ADR-0004 D2.3` 选 **raw-bin path B**（bootrom `-bios` + 应用 flat bin `-kernel`），**未实现**「`-bios` bootrom + **ELF** 应用」组合——实测 `hw/dadao/dadao-machine.c`：kernel 为 ELF 时走**路径 A 并整体忽略 `machine->firmware`（`-bios`）**，且 `dadao_load_regions[]` **仅含旧 RAM + ROM、未含 RAM@0**；而 `ADR-0004 D2.3 路径 A` 正文**明示「不使用外部 `-bios` ROM blob」** ⇒ **「`-bios`+ELF」组合语义未被任何 ADR 定义**（`R1` 只言「并存、非替代」，不含「组合」）。
- **根因**：门槛正向把两种**未定义能否共存**的路径（`-bios` bootrom 与 ELF `-kernel`）**并在同一例**，而 ADR 里二者是**两条互斥路径**、无组合定义 ⇒ 门槛任务（`INTEG-020t`）若照字面执行，**无任一现成路径可同时满足**（(a) path B 缺 ELF、(b) path A 缺 bootrom、(c) 组合未实现）。
- **判据（可复用）**：门槛任务立案 / `/dispatch` 前，须对门槛正向依赖的**每个路径 / 组合**问：「**该组合是否已被 ADR / 规范定义且已实现**？」**未定义** ⇒ 视为**前置缺口**，须**先经用户裁定**（① 承认缺口并另立任务实现该组合〔+ ADR 逐条确认〕 / ② 调整门槛口径以匹配现状〔与既有 ADR 自洽〕 / ③ 其它），**不得**默认「组合可用」而把风险留给门槛任务（否则门槛任务必红或被迫降级覆盖）。与 §7.6（下发前预检第 2 项须核本任务验证手段所需的全部前置）同类——**扩展至「门槛任务的验证手段的前置组合是否被 ADR 定义」**。
- **处置（本轮）**：`QEMU-047t` 按 `ADR-0004 R1` 与最小修改原则**未**引入该组合；缺口 + 选项 A/B/C（**倾向 A**）+ 建议**只追加**写入 `INTEG-020t` 任务书「审阅记录」+ `milestones.md` M5 段，**待用户裁定**（**未改任务范围、未动 `spec/`、未建新任务、未立 ADR**）。

### 7.22 独立 oracle 的期望值须「能机械解析则机械解析」，不可机械解析者须带 contract 引用 + 披露；执行载体的旁路通道须显式重定向（`TESTCASES-033t`，2026-10-08）

- **事由**：`TESTCASES-033t` 的独立 oracle `tools/testcases/validate_m5_vectors.py` 的期望值来源分两类：**（a）可机械解析** —— semihosting 服务表（`contract-semihosting.md §3`，**25 条**）经 regex `SVC_ROW_RE` **逐条解析**，并断言 `len(services) == 25`；**（b）不可机械解析** —— cfx 权限规则 → cause（`RULE_CAUSE`，4 条）、monitor cause 位（`CAUSE_ID`，3 条）、pass/fail token（`PASS_TOKEN`）为**带 contract § 引用的硬编码**（注释标 `contract-see §3`/`DADAO-12 §3/§4`/`DADAO-22 §3`）。
- **根因 / 判据（可复用）**：契约中**结构化可解析**的部分（表格行、清单）**必须机械解析**，禁用硬编码复制（否则契约改了 oracle 不跟 ⇒ **静默漂移**）；契约中**语义性/散落**的部分（位编码、规则→异常映射、文档化 token）**只能硬编码**，但须 ① 带 `contract-*`/`spec` § **引用注释**、② 在任务书 / `README` **披露**、③ 与**既有同层 oracle 范式一致**（此处对齐 `validate_codegen_vectors.py` 的 `HAND_DERIVED`、`validate_elf_vectors.py`）。
- **附带教训（执行载体的旁路通道）**：M5 执行载体 = `-bios` bootrom + flat bin；semihosting 控制台（`WRITEC`/`WRITE0`）在 `target=native` **无 `chardev` 时输出到 QEMU 进程 stderr**（与 QEMU 自身告警**不可区分**）⇒ 比对须**显式** `-chardev file,id=semi,path=…` + `semihosting-config …chardev=semi` **落盘**再比对，不得依赖默认 stderr。
- **处置（本轮）**：服务表机械解析（25 条）；硬编码部分带引用 + 披露（已记任务书「遗留」）；驱动加 `-chardev` 捕获（已披露，任务书「新发现 2」）。**无缺口**。
- **提示**：独立 oracle 绿灯**只是必要条件**——真实执行语义由 E2E 驱动（`tools/integ/run_m5_e2e.py`）承担；oracle **禁** `subprocess`/`os.system`/`Popen`（`grep` 0 命中）。

### 7.23 exit-port → semihosting `SYS_EXIT` 全量迁移的四条实现坑（块指针 `rb16`／退出码在内存块／`-d cpu` 须强制 TB 边界／范围计数须脚本枚举）（`TESTCASES-034t`，2026-10-08）

- **事由**：`TESTCASES-034t` 把 M1–M4 **全部**依赖 exit-port（MMIO `0xffff_8000_0000`，写 `st.o rdN,[rb16,0]`）的向量/harness/oracle 迁到 semihosting `SYS_EXIT`（`ADR-0020 D8` / `ADR-0004 R2`）。迁移中踩到四条坑：
  1. **块指针 = `rb16`、退出码在内存块（非寄存器）**：旧 exit-port 是「把寄存器 `st.o` 写到 MMIO 地址」；`SYS_EXIT` 是「**64 位大端参数块** `{reason=0x20026, code}` 由块指针指 + `rd16=0x18` + `trap cfx_umon, 0x30000`」。初版**沿用 exit-port 习惯把块指针放 `rb3`** ⇒ 全部 FAIL（`SYS_EXIT` 读 `rb16`）。**块指针在 `rb16`、退出码在内存块第 2 字段**，不是「写某个寄存器」。
  2. **`-semihosting-config enable=on,target=native` 须由 harness 显式给**：否则 `SYS_EXIT` 不可达、host `$?` 不传播（`ADR-0020 D7`：`native` 非默认、须显式开，测试侧显式开属合规）。
  3. **`-d cpu` 的「最后一次 dump」观测陷阱**：旧 exit-port 的 `st.o` 是 **MMIO**，QEMU 在 store 前强制切 TB（`CF_LAST_IO`）⇒「最后一次 dump」恰落在 store 前、捕获到前置 `ld_o` 结果；而 `SYS_EXIT` 的 `trap` 经 `raise_exception`→`cpu_loop_exit_restore` 结束 TB、**不在 trap 前切分** ⇒ 若「读观测值的 `ld_o`」与 exit 序列同处一个 TB，最后一次 dump 落在 `ld_o` 之前、观测到**旧值**（`svc_read`/`svc_get_cmdline` 曾因此 FAIL）。**修法**：exit 序列**前置一条 no-op `jump`**（`jump-iiii imms24=1`，跳到下一条）强制 TB 边界 + 回主循环 + 记录下一 TB 的 dump。
  4. **范围计数须脚本枚举，不靠目测抽样**：`ISS-147`（期望退出码落 fault 区 `0x80–0xFF`）初判 **5** 条，脚本枚举发现实为 **7** 条（另有 `call_multiarg_stack`=171、`ptr_add_offset`=171，均 `0xAB`，亦落 fault 区）。
- **根因 / 判据（可复用）**：跨「停机协议」迁移时，**新旧协议的参数传递 / 观测切点 / 编码宽度都可能不同**——不可沿用旧协议的习惯（寄存器角色）与观测假设（TB 切分点）；迁移前须**先记改前基线（逐条真实输出）再对拍**，且**范围 / 计数一律脚本枚举**。
- **处置（本轮）**：四条坑全部当场修（块指针改 `rb16`；harness 显式 `target=native`；`046t`/`049t` 前置 no-op `jump`；`ISS-147` 7 条掩码 `255→127` 并同步 oracle）。**无缺口**（迁移后各门控与改前逐项相等、26 探针逐条等价）。
- **附带教训（一份 crt0 服务两条管线）**：同一 `tests/scripts/codegen_crt0.s` 在 M3（`cat crt0.s prog.s` 单 TU、无 link）与 M4（`llvm-mc crt0.o` + `ld.lld`）下均可用 ⇒ 迁移点收敛为 **1 文件 + 2 driver**（DRY）。
- **提示**：规范落 §8.17。

### 7.24 门控收口的三个坑：GNU make 失败码 = 2（非子命令 1）／「不回归」用 make 前置链机械保证／跨模块复用已验收产物的可接受性（`INTEG-020t`，2026-10-08）

- **事由**：`INTEG-020t` 收口 M5 门控 `make test-semihost`（五组成：正向 / cfx 级权限反例 / 服务表 25 / 不回归 / INTEG 开闭；原「单/多 TU ELF」正向移 M6，见 §8.15）。三点：
  1. **GNU make recipe 失败返回 2，而非子命令的退出码**：注入反例时 `tools/integ/run_m5_e2e.py` 返回 `1`（驱动 fail-closed 出口），但 `make test-semihost` 整体返回 **`2`**（make 对「任一 recipe 失败」一律以 `EXIT_FAILURE=2` 结束，recipe 里写 `exit 1` 也不改变 make 自身退出码）。证据脚本若把「注入后须失败」判据写成 `rc == 1` ⇒ **假 FAIL**；须用 **`rc -ne 0`**（工程实测：注入 A/B 两轮 `RUN … EXIT=2`，`run.sh` 用 `nonzero()` `[ "$1" -ne 0 ]` 实现）。
  2. **「不回归」可作门控前置链机械保证**：把组 ④（`test-elf`/`test-codegen`/`check`〔`check` 依赖行含 `check-lit`/`check-no-residue`〕）列为 `test-semihost` 的 **make 前置** ⇒ 任一前置失败则 make 中止、整体非零，无需在 recipe 内重复调用；组 ①+②③ 则在 recipe 内**捕获子命令 `rc` 并 `exit $$rc`**（`$$?` 紧接子命令，禁经管道）。实测整轮 **59s**（无组件重建，`install-host` 增量为主）。
  3. **跨模块复用已验收产物承担门控组成**：门控 ③（服务表 25 覆盖）**未在 integ 侧另建向量**，而是**调用 `QEMU-046t` 已入库的探针** `tools/qemu/min_rom_probe_046t.py`（全量跑、逐服务 ≥1 例 + 覆盖计数 = 25、缺任一即非零）。
- **根因 / 判据（可复用）**：
  - 「注入 ⇒ 门控非零」类判据**不得硬编码具体码**（make 层面 = 2，子命令可为 1/2/其它）⇒ 一律 `-ne 0`（与 §2.1 管道退出码陷阱、§8.7「裸 `git diff` 假 FAIL」同一族：**判据不得依赖脆弱的实现细节**）。
  - 门控「聚合既有各模块门控」是**既定范式**（M3/M4 门控已如此）；判「跨模块复用**已验收产物**」是否可接受三条件：① 被复用物**已入库且经其原任务验收**（非本任务新建）；② 该组成**本即原任务的交付断言**（25 服务覆盖 = `QEMU-046t` 交付，且 `min_rom_probe_046t.py` 探针 `--list` 末两行 `distinct 25`/`required 25` 机器可判）；③ 复用**不新增跨模块契约、不改 `spec/`/`components/`**。满足则属**复用**（非「凭空引用」），直接调用即可、零新增向量/oracle。
  - **门控名 / 组成口径**：门控名 = `make test-semihost`（**非** `test-see`）；console「≥3 类」中 `WRITE` 服务载荷走 **host 文件**（`expected_file`）、其 console **为空** —— 「有输出 2 例」逐字节（`m5_semi_writec`=`41`、`m5_semi_write0`=`4f 4b 0a`）、「应无输出 3 例」校验空（`m5_semi_write`/`m5_semi_exit`/`m5_semi_exit_extended`），二者均属 console 比对。
- **处置（本轮）**：三点均已落（证据脚本 `nonzero()` 用 `-ne 0`；组 ④ 作 make 前置；组 ③ 调 `QEMU-046t` 探针）；`make test-semihost` **EXIT=0**（59s），不回归 `test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit` 62/62 全绿。**无缺口**。
- **提示**：规范落 §8.18。

## 8. 操作规范（该这样做 / 不该这样做）

> 由 `feedback_001…007`（2026-10-08，用户裁定）**并回**本文件：**经过/根因**归 §7.10–§7.13 与 §7.5/§7.7/§7.9，**正面规范**归本节。每条的「教训指引」只给指针，不复述经过。

### 8.1 ADR/规范逐个点名一类产物时，任务界定与验收范围须「逐字列出、逐项核到底」；核门控可执行来源须沿调用链逐跳追

- **规则**：
  1. ADR/规范**逐个点名**一类产物时，任务书「范围」与「验收 grep 范围」须把点名项**原样抄入**，逐项给「已落地 / 不适用 / out-of-scope（附证据）」结论；**不得**以概括措辞替代点名清单。
  2. 核对「门控可执行来源」须从 `make check` 依赖表出发，沿「门控 → 脚本 → 可执行/子脚本」调用链**逐跳追**；grep 范围须覆盖**全部被调脚本所在目录**（含 `tests/scripts/`），不能只 grep `Makefile`+`tools/**`。
  3. 判「是否门控/执行器」须用**调用链证据**（全仓 grep 脚本名 + 门控对其 `import`/`subprocess`）；不得因「同款写法」或「同目录」类推。判 out-of-scope 须给**调用链反证**并登记遗留。
- **依据/来源**：`INFRA-047t`（2026-10-07 第 1 轮后由 architect 范围修正、重开一轮闭合）。
- **教训指引**：见 §7.10。

### 8.2 迁移生成物落点须「改落点 + 清旧忽略规则 + 删残留旧产物目录」同一原子落地；脚本比对 git 路径须关 `core.quotePath`；迁移前须实测旧落点真实路径

- **规则**：
  1. 迁移生成物落点 = 改落点 + 清旧忽略规则 + **同删残留旧产物目录**，三者须**同一原子落地**；任务书「输出」须显式列出旧目录为**删除目标**，并贴删除前后 `ls`/`git status --porcelain -uall` 真实输出。判据：清掉忽略规则后 `git status --untracked-files=all` 若暴露旧产物，即证必须同删。
  2. 迁移前须 `grep`/`ls` **实测**旧落点真实路径（可能已被上游任务改变），不以任务书/历史描述为准。
  3. 脚本比对 `git status` 路径须先 `git -c core.quotePath=false`；非 ASCII 路径默认被加引号 + 八进制转义，会与按原文匹配的白名单**错配** ⇒ **假阳性 FAIL**。
  4. 范围判定不得越界：旧落点删除目标**只列任务书明确列出的目录**；gitignored 树内其它历史残留**登记为遗留/另立任务**，不顺手删。
- **依据/来源**：`INFRA-048t`（2026-10-07 下发前预检修订 + 验收；reviewer `Accepted` + architect 交叉复核）。
- **教训指引**：见 §7.11。

### 8.3 判 target 是否在 `make check` 依赖链须读 `check:` 依赖行而非 `.PHONY` 清单；行号引用须逐行核对

- **规则**：
  1. 判「某 target 是否随 `make check` 跑」只看 `check:` 目标的**依赖行**（`grep -n '^check:' Makefile`），**不得**以 `.PHONY:` 清单为准（`.PHONY` 只是伪目标声明，与依赖关系无关）；再 `grep -n '^<target>:' Makefile` 看目标处注释（常标 `standalone`）。
  2. 要求「另跑 standalone target」时，须显式写明「standalone，不在 `make check` 依赖链内」，并各自单独跑、各自报 EXIT，不得与 `make check` 合并成一句「`make check`（含 X）」。
  3. `.PHONY`、`check:` 依赖行、目标处注释三者都要核；**行号引用须逐行核对**再落纸。
- **依据/来源**：`SPEC-117t`（2026-10-07 下发前预检错误引用；工程师实测 + 主会话更正 + reviewer 独立复核 + architect 交叉复核）。
- **教训指引**：见 §7.12。

### 8.4 核「已 `Accepted` 决策未被静默改写」用「HEAD×工作树按节 diff + 非空校验」；「已标 `Superseded`」须核到节内标记；独立注入用临时树 + `cp`/md5

- **规则**：
  1. 判「受保护决策正文未被改写」用「`git show HEAD:<file>` × 工作树**按节前缀提取**后逐节 `diff -q` ⇒ `same`」，**不以 `git diff` hunk 为准**（hunk 边界脆弱：修订条目引用正文措辞会混淆）。
  2. 提取结果须做**非空校验**（每节 `行数 > 0`），否则空提取 ⇒ 两侧都空 ⇒ `same` ⇒ **假 PASS**。
  3. 「某决策已标 `Superseded`」须核到**该节内**的 in-place 标记（`awk '/^### D3 /,/^### D4 /' <file> | grep -c Superseded`），不得以「修订条目里写了『已标』」为准。
  4. 独立注入须「**非空 → 检出 FAIL → 还原回绿**」三步齐证；注入宜在**临时树** `/tmp/opencode/<任务ID>/`，还原用 `cp`+md5（**禁** `git checkout/restore/stash`）。
- **依据/来源**：`SPEC-113t`（2026-10-07 engineer 自审 F2 + reviewer 独立注入 + architect 交叉复核）。
- **教训指引**：见 §7.13；机械核验范式另见 §5.6。

### 8.5 改 `spec/` 目录须用户**事先**明确授权（含 v5 自定册）；上游只读册只作只读引用

- **规则**：
  1. `spec/` 下任何**新增/修改/删除**（含 v5 自定册 `Machine-*`/`Process-*` 与 `spec/README.md`）**须用户"事先"明确允许**，授权**原话落盘**；未获授权而拟改 `spec/` ⇒ **BLOCKED**。
  2. **上游只读册**（`DADAO-1x`〔11/12/13〕、`DADAO-2x`〔21/22/23〕、`SimRISC-00..12`、`Toolchain-01`，共 **20 册**）只作**只读引用**（引 `§` 章节号，**不改一字**）；确需修改须先经用户授权，并在**同一变更**内更新 `manifests/spec-readonly.lock.toml` 的 `sha256`。
  3. 任务书「输出」不得把上游只读册列为可改对象；需要的新正文一律落 **v5 自定册**。
  4. **三处固定检查**（下发前预检第 5 项 / reviewer 验收 / architect 提交）均以 `git diff --name-only`（提交前 `--cached`）与 `spec/` 清单交叉；有交集而缺授权证据 ⇒ 阻断。
- **依据/来源**：`SPEC-114t` round1 擅改上游只读册事故，用户 2026-10-07 裁定；机制落地 `SPEC-119t`。
- **教训指引**：见 §7.5；范式另见 §5.6；规则正文 `spec/Process-06-spec目录保护规范.md`。

### 8.6 生成器随产物入库（产物入 git ⇒ 生成器不得只留 `.work/`）

- **规则**：
  1. **判据 = 产物是否入库**：凡产出**被提交（入 git）**的生成器/脚本，必须**随产物**保留在**非易失位置**——优先 `tools/<module>/`，否则 `.work/<任务ID>/`；**不得**只留 `/tmp` 或 `.work/`（被 `.gitignore` 整体忽略 ⇒ 不入库）。
  2. **「一次性」只描述用途，不等于可丢弃**。
  3. 任务书「允许文件集」须**显式含**「随产物入库的生成器」。
  4. 入库生成器须**可复现生成**产物（`cmp` 逐字节证）；architect 交叉复核时**须自己跑一遍生成器 + `cmp`**，不采信他人输出。
  5. 生成物内 provenance 行（如 `// Generator: <路径>`）须指向生成器当前路径；落点迁移致失真时按用户授权改注释并**重新导出 patch**（只改注释、表数据/编码零变化）。
- **依据/来源**：`LLVM-060t`（2026-10-07 round1→round2）。
- **教训指引**：见 §7.7。

### 8.7 证据脚本对「已提交变更」的断言须带提交范围（`BASE..HEAD`）

- **规则**：
  1. 凡断言「某变更存在 / 某文件被改」的 git 调用，若被测产物**可能已被提交**，**必须带提交范围**：`git diff "$BASE_COMMIT"..HEAD -- <path>`；**禁裸 `git diff`**（裸 diff 比较**工作树 vs HEAD**，变更已入 HEAD 时返回空 ⇒ **假 FAIL**）。
  2. `BASE_COMMIT` 须可经**环境变量覆盖**（默认基线），以便 `BASE_COMMIT=HEAD` 重放脚本、验证该断言**确实可 FAIL**。
  3. 只有「检测工作树残留」才用 `git status --porcelain`（其语义就是查工作树，合理保留）；需在**提交后**仍抓越界则另加 `$BASE_COMMIT..HEAD` 越界断言。
  4. 证据脚本本身也是**交付物**：须经受「**提交后仍应回绿**」自检；reviewer 审核须**逐条核 git 调用是否带 range**；engineer 修一处缺陷须 `grep -nE '\bgit\s+(diff|status|log|show)\b'` **全脚本同类排查**。
  5. **评审不得因「pre-commit 设计」放行**：凡证据脚本的断言依赖**未提交工作树**（`git status` / 裸 `git diff`）而**提交后必红 / 必空**，reviewer **不得**以「pre-commit 设计 / 提交前已验证 / post-commit 已知限制」为由判 `Accepted`——**须判 `Needs Revision`**，要求改为 `$BASE_COMMIT..HEAD`。判例：`SPEC-120t` round1 reviewer 判 `Accepted`（C10 用工作树 `git status` 计算改动集，post-commit 必然为空 ⇒ 假 FAIL），**由主会话依 §8.7 推翻改判 `Needs Revision`**（首次推翻），round2 改 `$BASE_COMMIT..HEAD` 后回绿。
- **依据/来源**：`SPEC-115t`（2026-10-08 round1→round2）；补强 `SPEC-120t`（2026-10-08，主会话推翻 round1 `Accepted`）。
- **教训指引**：见 §7.9、§7.15；同类 §2.1（管道退出码陷阱）。

### 8.8 任务书「事实源」段的「唯一 / 仅 / 全部」类断言须下发前全量实测；子集子句只在该子集内书写

- **规则**：
  1. 任务书「事实源 / 事实核实」段凡出现「**唯一 / 仅 / 全部 / 共 N 个**」类**计数或集合**断言，须在**下发前**用生成物**全量实测**（如 `python3` 逐条统计）并落纸——**不得**沿用旧任务 / 历史台账的表述。
  2. 规范子句若**限定某子集**（如「cfx 组」「M1 组」），只在该子集内据实书写；子集外同值项**不得混入**（避免扩义或臆断）。
- **依据/来源**：`SPEC-116t`（2026-10-08；engineer 实测更正 + reviewer `Accepted`）。
- **教训指引**：见 §7.14；同类 §4.1/§4.6。

### 8.9 子代理异常返回：第 1 次重试后仍异常/未落盘 ⇒ 停止重试、拆分任务，不再耗满重试预算

- **规则**：
  1. `task` 异常返回（`Task cancelled`/空结果）先核对完成区与 `git status`：产出已落盘 ⇒ 视为完成；**确未落盘 ⇒ 重试同一任务一次**（附失败现场）。
  2. **第 1 次重试后仍异常/未落盘** ⇒ **立即停止重试**（**不耗满 3 次、不盲目再重试**），**与用户商定把该任务拆分为多个小任务**（缩小单次下发粒度、要求分段落盘），拆分后再重下一发。
  3. 每次异常与重试须登记（子代理 task_id、异常类型/次数、重试结果、**任务拆分决议**）。
- **依据/来源**：用户 2026-10-08 裁定原话「如果重试后仍然断，不要再重试，可以考虑将该任务拆分成多个小任务」；实例 `QEMU-044t`（2026-10-08，第 1 次下发 `aborted` 且未落盘 ⇒ 重试一次成功）。
- **教训指引**：见 §3.2、§3.3；对应 `AGENTS.md`「子代理返回异常处理」。

### 8.10 规范以「委派 / 占位」留给任务的决策 ⇒ 实现口径落门控 + 覆盖缺口落台账并提请授权（不得静默改 `spec/`）

- **规则**：
  1. 任务若落地规范「**委派给本任务**」或「**留占位**」的决策，须在**规范正文以外**记明三件事：已落地的**实现口径**、规范对应段落**现状**（占位 / 委派 / 歧义，逐条引用 `§`）、**拟改文本**（放任务书完成区 + `issues.yaml`）。
  2. 实现口径须由**门控断言**固化（如 `check-interface` 断言 RAM@0 基址/大小/注册点/`CFXMEM=0x81`）——使覆盖缺口在用户授权前即可**机械核验**，且实现不依赖任何未授权的 `spec/` 改动。
  3. 规范覆盖缺口**一律不改 `spec/` 收口**（守 §8.5 / `Process-06`）；登记 issue 并请用户**事先**授权；授权后在**同一变更**内同步该册 `sha256` 锁（若涉上游册）。
  4. **区分两类**：「实现口径已在门控固化」（授权前可核验、不阻塞里程碑）vs「规范正文缺口」（须授权收口）——前者登记遗留、后者提请授权，二者**不得混为一次静默改 `spec/`**。
- **依据/来源**：`QEMU-049t`（2026-10-08，`ISS-166`：`Machine-01 §1` 未覆盖越界路由口径与 RAM@0 容量，`spec/` 零改动）。
- **教训指引**：见 §7.16；规则正文另见 §8.5 / `spec/Process-06-spec目录保护规范.md`。

### 8.11 保护范围扩面（上游只读册 → 含 v5 自定册）须四处一致；立案前须实测锁文件实际包含哪些册

- **规则**：
  1. 立案（写任务书）前，凡涉及「**更新**某册锁 / 某清单」的表述，须先**实测**该锁/清单文件**实际包含**哪些项（`grep -c '^\[\[spec\]\]' <lock>` + 逐册 `path`），**不得**沿用历史/上一任务的前提（本例原前提「锁含 `Machine-01`，只剩其余 **19** 册」经实测**证伪**——锁**仅 20 册上游册**，不含 `Machine-01`）——「更新」的前提是「已在锁内」，不在即应为「**新增**」。
  2. 保护**范围扩面**（如把 v5 自定册纳入原「只保护上游册」的锁）至少同步**四处一致**：① **机制正文**语义（`Process-06 §5` 标题/正文去「只覆盖上游」限定）；② **锁/机制清单**与计数（§6 标题 `20→21` + 分组行 + 「不在锁内」注记移出该册）；③ **门控措辞**（checker docstring/`--help`/成功输出行 + `Makefile` help/注释，去「upstream」，**逻辑零改动**）；④ **判据注记**（正文/门控中凡「只覆盖上游」的限定语）。四处任一漏改 ⇒ 规范与机制**自相矛盾**（「只覆盖上游」不再准确）。
  3. 授权范围**边界外的相邻措辞**（如 `Process-06 §1` 的「（清单见 §6）」括注因扩面而字面失真）**不得顺手改**——登记「**遗留**」并提请用户**另行授权**；改动范围以用户授权的 `§` 为**硬边界**（改即 BLOCKED）。
  4. 扩面后 `sha256` 锁须**改毕后实测**（`sha256sum`），并核「既有册 `sha256` **逐条未变**」（`git diff` 中既有 `sha256` 行的 `-`/`+` 计数 = 0）。
- **依据/来源**：`SPEC-121t`（2026-10-08；用户裁定 ②/④/⑤；reviewer `Accepted` + architect 交叉复核）。
- **教训指引**：见 §7.17；同类 §8.5 / §8.8。

### 8.12 伪代码为权威：prose 与伪代码张力时以实现伪代码为准；上游只读册的张力**登记 issue + 提请授权**，禁静默改 `spec/`

- **规则**：
  1. 规范内**伪代码（权威优先级最高）** 与 **prose** 对同一语义有张力时，**以实现伪代码为准**。本案 `DADAO-12 §5` 异常退出：伪代码 `⟨cfxname⟩` 明确定义为 `inner_cfx_code`（**当前**执行 `escape` 的 cfx），返回地址用**当前 cfx** 的 `excp_cause_ip`（`imms18 << 2`）——prose「硬件直接恢复到 **A 的 prev 现场**」的跨 cfx 措辞**不采用**；且伪代码**不恢复** `inner_cfx_code`（只恢复 `inner_cfx_mask`/`inner_run_mode`）。
  2. 验证/实现任务发现**上游只读册**的 prose/伪代码**覆盖缺口或措辞张力**时，**一律不改 `spec/`**（守 §8.5 / `Process-06`）——**登记 issue（新号）+ 建议另立 spec 任务**，提请用户**事先**授权；授权后在**同一变更**内同步该册 `sha256` 锁。
  3. **区分两类**：「**澄清**类」（实现与伪代码一致，仅易误解，如 escape 不恢复 `inner_cfx_code`）⇒ 入 `lessons`，**不立** spec 任务；「**覆盖缺口 / 张力**类」（prose 与伪代码/机制不符，须改上游册）⇒ **登记 issue + 提请授权**，不得静默改。
- **依据/来源**：`QEMU-045t`（2026-10-08，`ISS-167`：`DADAO-12 §5` 跨 cfx escape prose/伪代码张力；`spec/` 零改动）。
- **教训指引**：见 §7.18；同类 §8.5 / §8.10。

### 8.13 「复用上游共享层」任务须在输出中列全**接入点清单**（arch mask / `translate_for_debug` / Kconfig select / meson 挂钩），缺一即 SIGSEGV 或 CLI 被拒

- **规则**：
  1. 任务范围若为「**复用**上游共享层（如 `semihosting/arm-compat-semi.c`）」，**不得**只按「钩子文件」划范围；任务书「输出」须**显式列全接入点清单**，逐项给落点：① 钩子实现文件（target-specific：`common_semi_arg`/`common_semi_set_ret`/`is_64bit_semihosting` 等）；② **调试地址翻译钩子**（共享层经 `cpu_memory_rw_debug()` 读写 guest 内存 ⇒ 须实现 `SysemuCPUOps.translate_for_debug`，否则回退 NULL ⇒ **SIGSEGV**）；③ **CLI arch mask**（`qemu-options.hx` 的 `DEF(...)` `QEMU_ARCH_*` 掩码 ⇒ 缺则 `qemu_arch_available()` 拒绝 CLI）；④ **Kconfig `select` + meson `when:` 挂钩**（否则共享层 `.c` 不编入）。任一项漏列 ⇒ 实现期必然「越界」或功能不可达。
  2. 越界**判据**：以「**是否为本任务复用共享层的必需接线**」为准，**非**以任务书字面文件清单为准；超出字面清单的必需接线须**如实披露**（完成区「新发现/坑」+ 审阅记录），**不得裁剪**，由 reviewer 判「必要接线 / 越界」。
  3. **共享层零改动**仍须**实测证**：`git -C .work/source/<comp> diff --stat HEAD -- <share-path>` 为空；本任务只改**目标侧**接入点，不重写共享层。
- **依据/来源**：`QEMU-046t`（2026-10-08；`common-semi-target.c` 钩子 + `translate_for_debug`〔CPU.c〕+ `qemu-options.hx` arch mask + `Kconfig`/`meson.build` 接线；reviewer `Accepted` 判两项披露为「最小必要接线」+ architect 交叉复核）。
- **教训指引**：见 §7.19；同类 §8.1（点名类产物须逐项核到底）。

### 8.14 还原方式禁用清单扩充：`git show <commit>:<path> > <path>` 与 `git checkout`/`restore`/`stash` 同类

- **规则**：
  1. **禁用**用 `git checkout`/`git restore`/`git stash` **及 `git show <commit>:<path> > <path>`** 还原注入或临时改动——它们都把文件**覆盖为「提交中的版本」**，在**工作树对该文件有未提交改动**时**静默丢弃**这些改动。
  2. 还原一律 **`cp` 备份 + `md5` 对账**（注入前 `cp f f.preinject` 并记 md5；还原 `cp` 回；以 md5 相等判成功），或**优先在临时树**（`/tmp/opencode/<任务ID>/`）注入。
  3. **`git status`/`git diff` 干净不作「已还原」证据**；「还原须含重建」（源码还原 ≠ 二进制还原）。
- **依据/来源**：`QEMU-047t`（2026-10-08，reviewer 独立注入还原用 `git show HEAD:<path>`；本次未造成损失但属偏差）。与全局 `AGENTS.md`「注入/改动的还原纪律」同源。
- **教训指引**：见 §7.20；相关 §2.5 / §8.4 rule 4。

### 8.15 门槛任务立案前须核「门槛正向依赖的路径 / 组合是否已被 ADR / 规范定义」

- **规则**：
  1. 门槛（里程碑门控）正向用例若把**两条及以上的路径 / 组合**（如 `-bios` + ELF）**并在同一例**，须在**门槛任务立案 / 下发前**逐项核：「该路径 / 组合是否已被 ADR / 规范**定义**？是否已**实现**？」
  2. **未定义** ⇒ 视为**前置缺口**，**先经用户裁定**（另立任务实现 + ADR 逐条确认 / 调整门槛口径 / 其它），**不得**默认「组合可用」而把风险留给门槛任务。
  3. 缺口与选项只**追加**写入相关任务书审阅记录 + `milestones.md`，**不改任务范围、不动 `spec/`、不擅自建任务 / 立 ADR**（`待用户裁定`）。
- **依据/来源**：`QEMU-047t` 遗留 + `INTEG-020t` architect 前置风险评估（2026-10-08，**待用户裁定**；`spec/` 零改动）。
- **教训指引**：见 §7.21；同类 §7.6 / §8.8（前置 / 「唯一·仅·全部」类断言须下发前全量实测）。

### 8.16 独立 oracle：结构化期望值必须机械解析；只能硬编码者须带 contract § 引用并披露；执行载体须显式捕获旁路通道

- **规则**：
  1. 期望值的**结构化来源**（契约表格 / 清单）须在独立 oracle 内**机械解析**（**逐条**），禁复制为硬编码常量（防「契约→oracle」静默漂移）。
  2. **语义性**期望值（位编码、规则→异常映射、文档化 token）**只能硬编码**时，须：带 `contract-*`/`spec` § **引用注释**；在任务书 / `README` **披露**；与**既有同层 oracle 范式一致**。
  3. 独立 oracle **禁** `subprocess`/`os.system`/`Popen`（不调 `llvm-mc`/`llc`/`llvm-objcopy`/QEMU）；其绿灯**只是必要条件**，真实执行语义由 E2E 驱动承担（「覆盖 ≠ 语义」）。
  4. 执行载体的**旁路输出通道**（如 semihosting 控制台）须**显式**重定向到可比对的位置（M5：`-chardev file,id=semi,path=…` + `chardev=semi`），禁依赖默认 stderr（与 QEMU 告警混淆、不可判定）。
- **依据/来源**：`TESTCASES-033t`（2026-10-08，reviewer `Accepted` + architect 交叉复核）。
- **教训指引**：见 §7.22；同类 §7.19 / §8.13（复用共享层须列接入点清单）。

### 8.17 测试停机协议迁移（exit-port → semihosting `SYS_EXIT`）：块指针 `rb16` + 退出码在内存块 + 显式 `target=native`；迁移类任务先记改前基线再对拍；`-d cpu` 观测强制 TB 边界；范围计数脚本枚举

- **规则**：
  1. **semihosting `SYS_EXIT` 约定**（迁自 exit-port 时）：参数为 **64 位大端内存块** `{reason=0x20026, exit_code}`，**块指针在 `rb16`**（**非**旧 exit-port 的「寄存器习惯」）、服务号 `rd16=0x18`、`trap cfx_umon, 0x30000`；**退出码在内存块第 2 字段、不是直接写某寄存器**。改错块指针寄存器即全部 FAIL。
  2. **harness 须显式** `-semihosting-config enable=on,target=native`——否则 `SYS_EXIT` 不可达、host `$?` 不传播（`ADR-0020 D7`：`native` 非默认、须由 harness 显式开）。
  3. **`-d cpu` 观测**：`SYS_EXIT` 的 `trap` **不在 trap 前切 TB**（不同于 exit-port 的 MMIO store 会因 `CF_LAST_IO` 切分）⇒ 若「读观测值的 `ld_o`」与 exit 序列同 TB，「最后一次 dump」会落在 `ld_o` 之前、观测到旧值。**修法**：exit 序列**前置一条 no-op `jump-iiii imms24=1`** 强制 TB 边界。
  4. **迁移类任务**须**先记改前基线**（逐条真实输出）**再对拍**（迁移后逐项与改前相等）；**范围 / 计数一律脚本枚举**（禁目测抽样——`ISS-147` 实为 7 条而非 5 条）；默认全迁、例外须**逐条披露**并登记 issue。
- **依据/来源**：`TESTCASES-034t`（2026-10-08，reviewer `Accepted` + architect 交叉复核；`ISS-147` 结案、`ISS-169` 登记 6 探针例外）。
- **教训指引**：见 §7.23；同类 §8.16（执行载体旁路通道须显式）、§8.2（迁移须同一原子落地）。

### 8.18 门控收口：注入判据用 `-ne 0`（GNU make 失败码 = 2）；「不回归」用 make 前置链机械保证；跨模块复用「已验收产物」作门控组成的三条件

- **规则**：
  1. 门控/证据脚本判「注入反例 ⇒ 应失败」**一律用非零判据**（`-ne 0`），**禁**硬编码 `== 1`——GNU make 对「任一 recipe 失败」以 **`2`** 结束，与子命令退出码不同；子命令的退出码只能在日志里叙述，不能作为门控判据。
  2. 门控若含「不回归」组成，优先把其载体（既有各模块门控 target）列为**新门控的 make 前置**——由 make 机械保证「任一前置失败 ⇒ 整体非零」；recipe 内的子步骤须**显式捕获 `rc` 并 `exit $$rc`**（`$$?` 紧接子命令，禁经管道，见 §2.1）。
  3. 门控组成**复用其它模块已验收产物**（如调用其探针承担某项覆盖）**可接受**，须同时满足三条件：① 被复用物**已入库且经其原任务验收**；② 该组成**本即原任务的交付断言**；③ **不新增跨模块契约、不改 `spec/`/`components/`**。否则应在本模块内新建向量/oracle。
  4. 门控「覆盖计数」类断言须**机器可判**（脚本 `--list`/摘要打 `distinct N`/`required N` + 全量跑断言集合差为空、缺任一即非零），禁目测抽样（呼应 §8.17 rule 4）。
- **依据/来源**：`INTEG-020t`（2026-10-08，M5 门槛收口；reviewer `Accepted` + architect 交叉复核）。
- **教训指引**：见 §7.24；同类 §8.3（判门控依赖链须读 `check:` 依赖行）、§8.16（独立 oracle 绿灯仅必要条件）、§2.1（管道退出码陷阱）。
