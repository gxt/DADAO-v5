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
