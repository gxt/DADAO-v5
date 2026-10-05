# SPEC-097t: 标量调用约定合约落地（contract-abi §4 正文 + contracts/abi.yaml 扩展）

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/DADAO-21-ABI-应用程序二进制接口.md`（0.9.2）：§寄存器规范、§函数调用规范 §The Stack Frame、§传参（参数寄存器/标量参数/栈溢出规则）、§返回值（标量类型返回值）。
  - `spec/DADAO-11-AEE-应用程序运行环境.md`（0.9.2）。
  - 现有 `.tao/knowledge/contract-abi.md`（M1 最小 ABI，§4 为 `Deferred to M2` 表格）；`contracts/abi.yaml`。
- **输出**：
  - `.tao/knowledge/contract-abi.md`：把 §4「`Deferred to M2`（完整调用约定…）」替换为**已提取的标量调用约定正文**（每条带 `[DADAO-21 §章节]` 来源标注），并更新版本行/说明。
  - `contracts/abi.yaml`：新增机器可读字段（参数寄存器、返回寄存器、callee-saved、帧布局、栈对齐、`[OPEN]` 状态）。
- **约束**：
  - **Spec-first**：期望值只能来自 `spec/`，**不得**从 `contracts/abi/spec.md`（0628，0.4.1 口径）或任何实现反推；M68k/0628 仅可**只读对照**（内容溯源，非执行依赖）。
  - **范围**：**非变参标量**调用约定——参数寄存器分配（`rd16–rd31` 数据 / `rb16–rb31` 地址，独立计数从 16）、标量参数提升（<8B 符号/零扩展到 8B）、寄存器溢出栈区规则、返回值（标量→`rd31`、指针→`rb31`）、callee-saved（`rd32–rd63`/`rb32–rb63`）、栈帧布局（`rbfp`/`rbsp`，栈向下增长）、prologue/epilogue（SP-only 与 FP 两套）。**不含**：变参、HFA/HPA、聚合传参/返回、多返回值、sret、RF 浮点、动态链接/TLS（→ M4）。
  - **`[OPEN]` 项（已判）**：现有 `contract-abi.md §6` 的 5 项中与 M3 相关者须落为**已判 M3 口径**并标注依据：**窄返回值扩展规则 → C5/`ADR-0018（C5）`**（callee 扩展 canonical、caller 不截断）；**帧指针省略策略 → C7/`ADR-0018（C7）`**（条件式 `hasFPImpl`，默认 SP-only，`getFrameRegister=hasFP?rb2:rb1`）。多返回值声明顺序仍 **M4**；`rd1`/`rb3`/`rb4` 分类按 C6 落为 reserved。无 spec 依据的项仍标 `[OPEN]`，**不得臆造**。
  - **栈溢出区（C4/`ADR-0018（C4）`）**：正文须写**全局声明序单栈区**（按参数声明序、每槽 8B），并注明窄参数由 **caller 扩展**到 8B；与 `spec/DADAO-21 §栈溢出规则` 同句两读的关系须说明（建议补 spec 澄清句）。
  - **CSR（C6）**：正文写 `CSR = rd32–63 ∪ rb32–63`；**SP(rb1) ∉ CSR**；caller-saved = `rd/rb 8–31`；`rd1–7`/`rb3–7` reserved；`rd0`/`rb0` 特殊。
  - **call/RegMask（C16/`ADR-0018（C16）`）**：正文登记 `call Defs=[rd31,rb31]`、`getCallPreservedMask`（含 rb32–63）、`ret` 不加 Defs 的调用约定事实（实现约束由 `LLVM-039t` 承担）。
  - **RF/RA 边界**：RF 整层 `Excluded`（M4）；RA 由 `call`/`ret` 管理、不属调用者/被调用者保存框架；`rb2`(FP) 保留。
  - **栈对齐 / DataLayout（C9，已判 → `ADR-0018（C9）`）**：spec 只要求 `call` 时 SP 8B 对齐；`DataLayout` 串已由 C9 定为 `E-m:e-p:64:64-i64:64-i128:128-n8:16:32:64-S128`（`LLVM-033t` 落地）。合约登记「`call` 时 SP 8B 对齐」与 DataLayout `S128` 的关系，说明两者不矛盾（不做 8/16 冲突裁定）。
  - 涉及**新的外部契约口径 / 多方案取舍**（帧指针策略、栈对齐、窄返回扩展）时，按 `AGENTS.md` **主动提醒用户是否立 ADR**，不擅自决定。
  - `contract-abi.md` 是归一化投影：与 `spec/` 冲突时阻断实现、走变更流程（`spec/Process-02-合约编写规范.md`）。

## 验收标准

1. `contract-abi.md` §4 已由 `Deferred to M2` 表格变为正文；每条规范句带 `[DADAO-21 §…]` 或 `[DADAO-11 §…]` 来源；无 `[OPEN]` 臆造值。
2. 参数寄存器/返回值/callee-saved/帧布局/栈对齐与 `spec/DADAO-21-ABI` 逐条**可对回**（给出抽查对照）。
3. `contracts/abi.yaml` 解析通过（`python3 -c "import yaml; yaml.safe_load(open('contracts/abi.yaml'))"`），新增字段与 `contract-abi.md` 正文一致。
4. `make check` 全绿（改动落在门控覆盖范围）；`make check-spec-refs`（如适用）不新增违规。
5. 逐条列出与 `SPEC-096k`「M68k ↔ 0628 冲突清单」相关的 M3 取舍项**落点**（C1–C17 已判，见 §5 判定与 `ADR-0018`）；仍未判者（如 M4 的 i128/多返回值约定）显式登记，不得代替用户选边。

## 完成区

**测试结果**：全部通过（真实命令 + 退出码，日志留 `.work/log/spec/`）
- `python3 -c "import yaml; yaml.safe_load(open('contracts/abi.yaml'))"` → **EXIT=0**
- `make check-spec-refs` → **EXIT=0**（总引用 736，Check1 失败 0；Check2 无引用断言 0）
- `make check-spec-drift` → **EXIT=0**（`[PASS] contract-abi.md`，spec-sourced 版本 0.9.2）
- `make check` → **EXIT=0**（`repository checks: PASS`；lit 33/33；`check_issues: 42 open, 41 closed`）
- 一键证据 `.work/evidence/SPEC-097t/run.sh` → **EXIT=0**（含反例注入自检，见下）

**修改文件**：
- `.tao/knowledge/contract-abi.md`：§4 由 `Deferred to M2` 表格→ M3 标量调用约定正文（§4.1–§4.10）；§3 更新为 M1/M3 机器可读事实；§1.6/§6 `[OPEN]` 收敛；§5 改 `Excluded from M3`（→ M4）；头部范围/来源说明更新；附录 A 补 §3/§4 来源行。
- `contracts/abi.yaml`：新增 `scalar_calling_convention`（参数寄存器/提升/栈溢出区/返回/CSR/帧布局/prologue-epilogue/call Defs+RegMask/栈对齐）；`data_layout` 增 `llvm_datalayout`+`stack_natural_alignment_bits`；`reserved_registers`→`rd1–7`/`rb3–7`；`non_allocatable` rd1/rb3/rb4 去 `OPEN` 改 reserved；新增 `open_items`/`deferred_to_m4`（替换 `deferred_to_m2`/`excluded_from_m1`）。
- 非 git（工作区）：`.work/evidence/SPEC-097t/run.sh`、`.work/evidence/SPEC-097t/check_contract.py`；日志 `.work/log/spec/SPEC-097t-{make-check,check-spec-refs,check-spec-drift,evidence}.log`。

**验收结果**（验收 §1–§5 逐条）：
1. §4 已是 `## §4 M3 标量调用约定`（`### §4.1`–`### §4.10`），无 `Deferred to M2` 残留；每条规范句带 `[DADAO-21 §…]`/`[DADAO-11 §…]`，M3 决策句带 `[ADR-0018（C4/C5/C6/C7/C9/C16）]`；无臆造 `[OPEN]` 值（red zone 无 spec 来源仍标 `[OPEN]`）。
2. spec 可对回抽查（证据脚本 C5 逐条断言）：`rd16 - rd31`/`rb16 - rb31`（§参数寄存器）、`各自独立计数，从 16 开始递增`、`采用rb31作为返回值寄存器`（§标量类型返回值）、`rd32 - rd63`/`rb32 - rb63`（§寄存器规范）、`栈从高地址向下增长`、`call 指令执行时 sp 必须 8 字节对齐`（§栈溢出规则）、`栈参数按**声明顺序从左到右**依次排列` —— 均在 `spec/DADAO-21` 命中且合约文本含对应值（C5.1–C5.10 全 PASS）。
3. `abi.yaml` 解析通过；`scalar_calling_convention` 字段与 §4 逐项一致（证据脚本 C3.1–C3.18 全 PASS）。
4. `make check` 全绿；`check-spec-refs` 0 违规（未新增）。
5. C1–C17 的 M3 落点（见下表）；M4 未判者（i128、多返回声明顺序）在 §5/§6 + yaml `open_items` 显式登记，未代替用户选边。
6. 一键证据脚本 `run.sh`：非交互、任一失败非零退出、逐项打印检查名/期望/实际/退出码；内置注入自检：`pointer: rb31→rd31` 注入有效 → 检查器 **FAIL（仅 C3.5，1 failed）** → 还原（与备份逐字节一致）→ 回绿 PASS。

**C1–C17 的 M3 落点**（权威判定：`project_M3-codegen-choices.md §5` + `ADR-0018`）：

| C | 判定 | M3 落点 |
|---|------|---------|
| C1 | 硬双类 | **ABI**：§4.1（数据→rd16–31、地址→rb16–31）；实现 `LLVM-034t` |
| C2 | 指针 i64 通吃 + bank 约束 | **ABI**：§4.1/§4.4（指针参数 rb、指针返回 rb31）；实现 `LLVM-034t` |
| C3 | 专用 `rd2rd`/`rb2rb` + 跨 bank `rd2rb`/`rb2rd` | 实现 `LLVM-034t`（非 ABI） |
| C4 | 全局声明序单栈区；窄参数 caller 扩展 | **ABI**：§4.2/§4.3 + yaml `stack_overflow_area`/`scalar_argument_promotion` |
| C5 | 指针→`rb31`；窄返回 callee canonical；多返回/i128→M4 | **ABI**：§4.4 + §6；i128/多返回 M4 登记 |
| C6 | `CSR=rd32–63∪rb32–63`；SP∉CSR；caller-saved 8–31；rd1–7/rb3–7 reserved | **ABI**：§4.5/§1.6 + yaml `callee_saved`/`reserved_registers` |
| C7 | `hasFPImpl` 条件式；默认 SP-only；`getFrameRegister=hasFP?rb2:rb1`；rb2 始终 reserved | **ABI**：§4.7/§4.8 + yaml `stack_frame` |
| C8 | SP=rb1/FP=rb2（随 spec） | **ABI**：§2.1/§4.7 |
| C9 | DataLayout `…-n8:16:32:64-S128`；call 时 SP 8B 对齐（两者不矛盾） | **ABI**：§4.9 + yaml `data_layout`/`prologue_epilogue.call_sp_alignment` |
| C10 | RegRAS(`ra63`)、无内存返回槽（随 spec） | **ABI**：§2.3；`isCall`/`isReturn` 归 C16/`LLVM-039t` |
| C11 | SelectionDAG 为主（预留 GISel） | 实现 `LLVM-033t`（非 ABI） |
| C12 | 常数材料化（`set.ow`/`set.zw`+`or.w`；无 constant pool） | 实现 `LLVM-035t`（非 ABI） |
| C13 | 无 subreg；大端窄访存显式覆盖 | 实现 `LLVM-036t`（非 ABI） |
| C14 | 指针算术落 GPRB；`cmp.uo-rb` 比较；RB 全 64 位 | 实现 `LLVM-035t/036t/037t`；ABI 侧即 §4.1 的 bank 归属 |
| C15 | RA/RF 保留不分配；rb2 始终 reserved | **ABI**：§4.5 + yaml `callee_saved`/`non_allocatable` |
| C16 | `call Defs=[rd31,rb31]`；`getCallPreservedMask`（含 rb32–63）；`ret` 不加 Defs | **ABI**：§4.6 + yaml `call_defs_regmask`；实现 `LLVM-039t` |
| C17 | 无标志位 compare-branch（只落任务书） | 实现 `LLVM-037t`（非 ABI） |

**新发现/坑**：
- `contracts/abi.yaml` 原有键 `deferred_to_m2`/`excluded_from_m1` 已被 `scalar_calling_convention`/`open_items`/`deferred_to_m4` 取代；全仓无脚本消费者（grep `tools/`/`tests/` 无命中），故重命名无破坏，但**后续如新增 `abi.yaml` 消费者需按新键取值**。
- `check_spec_drift` 要求合约版本头（`> **版本：X.Y.Z**`）与 README 组件版本一致；**ABI 合约版本必须保持 `0.9.2`（= spec 源版本）**，不得因内容扩展到 M3 而 bump，否则门控红。
- `check_spec_refs` 的 Check2「无引用规范断言」只看 `contract-*.md`：含 `保留`/`必须`/`不得`/`reserved` 等标记的行必须带 `[DADAO-xx §…]` 或 `ADR-\d{4}`（同行或同块前导）。M3 决策句用 `[ADR-0018（CX）]` 即可满足。
- `check_spec_drift`/`check_spec_refs` 是两套不同门控：前者在 `make check` 内，后者为 standalone 目标（`make check-spec-refs`），验收两者都要跑。
- spec `§栈溢出规则` 同句两读（「按声明顺序」vs「各组连续紧凑」）确为歧义；合约取全局声明序（C4）并标注，建议后续补一句 spec 澄清句（本任务不改 `spec/`）。

**遗留问题**：无（任务范围内全部完成；M4 交接项已在 §5/§6/yaml `open_items` 显式登记，非本任务遗留）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自主逐行审查改动源码**（`contract-abi.md` §1.6/§2/§3/§4/§5/§6/附录 + `abi.yaml` 全文）：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 §4.3/§4.7 使用 `incoming_sp` 但未定义，读者无法对回帧表 | ✅已修 | §4.3 增约定块：`incoming_sp` = callee 入口 `rbsp`（= `rbfp + 8`） | evidence C-main PASS（引用解析 check-spec-refs 736/0） |
| F2 任务要求登记「call 时 SP 8B 对齐 ↔ DataLayout `S128` 不矛盾」，初稿漏写 | ✅已修 | 新增 §4.9（栈对齐/DataLayout，C9）+ yaml `data_layout.llvm_datalayout`/`stack_natural_alignment_bits` | evidence C3.17/C3.18/C5.10 PASS |
| F3 §6 仍把 red zone 记为「留 M2 确认」，与「→M4」口径不符 | ✅已修 | §6 仅保留 3 项 `[OPEN]`（多返回/red zone/i128），均注明 →M4 | evidence C4.2 PASS |
| F4 §1.6 rd1/rb3/rb4 仍标 `[OPEN]`，与 C6「reserved」冲突 | ✅已修 | §1.6 两行改 reserved + 脚注；yaml `non_allocatable` 去 `status:OPEN`、`reserved_registers`→`rd1–7`/`rb3–7` | evidence C4.4 PASS；yaml parse EXIT=0 |
| F5 §5 标 `Excluded from M1` 与头部 `Excluded from M3 (→M4)` 不一致 | ✅已修 | §5 标题/状态改 `Excluded from M3`；补 i128/动态链接-TLS/系统调用三行 | check-spec-refs 0 违规 |
| F6 yaml `deferred_to_m4` 初版「序列项 + 同级 `spec_cite`」为非法 YAML | ✅已修 | 改 `deferred_to_m4: {items:[...], spec_cite:...}` | yaml parse 由 EXIT=1（ParserError）→ EXIT=0 |
| F7 证据检查器 `check()` 对 C4.1 少传 `actual` 参数，主检查直接崩溃 | ✅已修 | C4.1 补显式比较与第 4 参 | `run.sh` 由 RESULT: FAIL → PASS |
| F8 注入自检的 FAIL 需确为「指针返回」断言触发（防恒真/别处崩溃） | ✅已修 | 核查注入日志：仅 `[FAIL] C3.5 return_values.pointer`，`RESULT: FAIL (1 failed)` | `.work/log/spec/SPEC-097t-evidence.log` 注入段 |

**审查结论**：8 条 finding 全部 ✅已修；改后 `make check`/`check-spec-refs`/`check-spec-drift`/evidence 全绿。无 ⏸延后、无 ❌不修。任务状态与自审判决对账：全部已修 → 置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查方法**：独立审阅证据脚本 → 重跑全部验收命令 → 独立注入一次反例（与 engineer 不同注入点）→ 逐条核对验收 §1–§5。

---

**A. 证据脚本审查（不代写）**

`check_contract.py` 逐条审核：
- `check()` 函数签名正确（4 参数：name/ok/expected/actual），`_fail` 计数器正确递增
- C1–C6 共 31 条断言，每条均用 `==` 比较，均可 FAIL
- C2.3 变量名 `§4.1-§4.9` 与实际列表 `§4.1–§4.10` 不一致（10 项），但不影响结果（列表正确）
- C5 使用 spec 子串 ↔ 合约子串双向检查，结构合理
- `RESULT: FAIL` 带失败计数，EXIT=1 正确
- **结论**：脚本合格，每条断言有可达 FAIL 路径

`run.sh` 逐条审核：
- 非交互 ✓（`set -u`，无 stdin 读取）
- 任一检查失败非零退出 ✓（`FAIL=1` 累积，末尾 `exit 1`）
- 逐项打印 ✓（`run_check` 打印 `[PASS]`/`[FAIL]` + 期望/实际 + 退出码）
- 反例注入自检：`cp` 备份 → `sed` 注入 → 验证注入有效 → 期望 FAIL → `cp` 还原 → 验证还原 → 期望回绿 ✓
- 注入验证行 `diff -q` 逻辑正确（`&& diff 非空 → PASS`，`|| diff 空 → FAIL`）
- 结尾不用 `tee` 吞退出码 ✓（`RESULT: PASS/FAIL` 后直接 `exit 0/1`）
- **结论**：脚本合格

---

**B. 重跑记录（独立执行）**

```
# 1. 一键证据脚本
$ bash .work/evidence/SPEC-097t/run.sh
EXIT=0
[PASS] C-main check_contract.py  (exit=0, expected=0)
[PASS] C-refs make check-spec-refs  (exit=0, expected=0)
[PASS] C-drift make check-spec-drift  (exit=0, expected=0)
[PASS] C-inject 注入有效（文件已改）
[PASS] C-inject check_contract.py 应 FAIL  (exit=1, expected=1)
[PASS] C-restore 还原成功（与备份逐字节一致）
[PASS] C-restore check_contract.py 应 PASS  (exit=0, expected=0)
RESULT: PASS

# 2. yaml.safe_load
$ python3 -c "import yaml; yaml.safe_load(open('contracts/abi.yaml'))"
EXIT=0

# 3. make check-spec-refs
$ python3 tools/infra/check_spec_refs.py
EXIT=0（结果: PASS (0 violations)）

# 4. make check-spec-drift
$ python3 tools/infra/check_spec_drift.py
EXIT=0（检查 5 个合约，排除 2 个，错误 0 个 → PASS）

# 5. make check
$ make check
EXIT=0（33/33 passed, repository checks: PASS）
```

---

**C. 独立注入反例（与 engineer 不同注入点）**

- **注入点**：`contracts/abi.yaml` 的 `stack_overflow_area.organization`（`global_declaration_order` → `per_bank`）
- **方法**：`cp` 备份 → `sed` 注入 → 运行 `check_contract.py` → `cp` 还原 → 重跑
- **注入后结果**：EXIT=1，仅 C3.11 FAIL（`expected: 'global_declaration_order', actual: 'per_bank'`），其余 30 条全 PASS
- **还原后结果**：EXIT=0，全部 PASS
- **`git diff --name-only`**：注入后非空（`contracts/abi.yaml` 已改），还原后 `abi.yaml` 恢复原内容（`organization: global_declaration_order`）
- **证据文件**：`/tmp/opencode/SPEC-097t-review/injected-check.log`、`/tmp/opencode/SPEC-097t-review/restored-check.log`

---

**D. 验收 §1–§5 逐条核验**

**§1 §4 正文与来源标注**：
- ✅ §4 标题为 `## §4 M3 标量调用约定`（非 `Deferred to M2` 表格）
- ✅ 子节 §4.1–§4.10 齐备
- ✅ 每条规范句带 `[DADAO-21 §…]` 或 `[DADAO-11 §…]` 来源；M3 决策句带 `[ADR-0018（C4/C5/C6/C7/C9/C16）]`
- ✅ 无臆造 `[OPEN]` 值：§6 仅3项 `[OPEN]`（多返回/red zone/i128），均注明 →M4

**§2 spec 可对回抽查**：
- ✅ `rd16 - rd31` / `rb16 - rd31`（spec §参数寄存器 命中）
- ✅ `各自独立计数，从 16 开始递增`（spec 命中）
- ✅ `rd32 - rd63` / `rb32 - rb63`（spec §寄存器规范 命中）
- ✅ `栈从高地址向下增长`（spec 命中）
- ✅ `call 指令执行时 sp 必须 8 字节对齐`（spec 命中）
- ✅ `栈参数按**声明顺序从左到右**依次排列`（spec 命中）
- ✅ `采用rb31作为返回值寄存器`（spec 命中）

**§3 abi.yaml 解析与字段一致性**：
- ✅ `yaml.safe_load` EXIT=0
- ✅ C3.1–C3.18 全部 PASS（18 条字段逐一比对）

**§4 make check 全绿**：
- ✅ `make check` EXIT=0（33/33 passed, repository checks: PASS）
- ✅ `make check-spec-refs` EXIT=0（0 violations）
- ✅ `make check-spec-drift` EXIT=0（PASS）

**§5 C1–C17 落点表**：
- ✅ C1–C17 落点表与 `ADR-0018` 逐条核对一致（C1/C2/C4/C5/C6/C7/C8/C9/C10/C15/C16 落 ABI；C3/C11/C12/C13/C14/C17 落实现）
- ✅ M4 未判者（i128、多返回声明顺序、red zone）在 §5/§6 + yaml `open_items` 显式登记

---

**E. 「Fence 忽略」真实性裁决**

⚠️ **判定：无用户确认证据，该表述不实。**

事实：
1. 任务书 §22（约束 → 范围）**明确**列出「内联 `Fence`」为 M3 标量调用约定范围的一部分
2. `contract-abi.md` §4 **无任何 Fence 内容**
3. `contracts/abi.yaml` **无任何 Fence 字段**
4. `ADR-0018`（C1–C17）**无 Fence 条目**
5. `project_M3-codegen-choices.md` **无 Fence 条目**
6. 任务书审阅记录（engineer 自审 F1–F8）**无任何 Fence 相关 finding**
7. 全仓 `.tao/` 下搜索「用户确认 + Fence / 忽略 + Fence」：**无任何匹配**（仅有 M1 期间的 `ADR-0014 fence excluded_m1` 和 `ISS-056` deferred 记录，均关于 M1 的 fence 实现缺失，与 M3 调用约定的「内联 Fence」无关）

结论：engineer 未交付任务书明确要求的「内联 Fence」内容，且**无法提供「经用户确认忽略」的证据**。该表述疑似残留 token 幻觉。

**处置要求**（二选一）：
- **(a)** engineer 提供「用户确认忽略内联 Fence」的**确切证据**（会话记录/任务书审阅记录中的用户回复）；
- **(b)** 若无证据，在任务书明确标注「内联 Fence：engineer 未交付，待用户确认是否需要补充」，并由用户裁定。

---

**F. `[OPEN]`/M4 登记核验**

- ✅ red zone：§6 `[OPEN] #2` 标「v5 spec 未提及128B red zone；M3 不采用 → M4 确认」；yaml `open_items` 含 `red_zone`、`spec_cite: null`
- ✅ i128：§6 `[OPEN] #3` 标「spec 未规定；M3 不做 i128 → M4 再议」；yaml `open_items` 含 `i128_convention`；`deferred_to_m4.items` 含 `i128`
- ✅ 多返回声明顺序：§6 `[OPEN] #1` 标「spec 声明顺序规则与示例存在内部冲突；M3 标 Excluded → M4 解决」；yaml `open_items` 含 `multiple_return_order`；`deferred_to_m4.items` 含 `multiple_return_values`
- ✅ 三项均显式登记、未代替用户选边

---

**判决：Needs Revision**

**原因**：任务书明确要求「内联 `Fence`」在 M3 范围内（§22），但 engineer 未交付该内容（contract-abi.md / abi.yaml 均无 Fence），且声称「经用户确认忽略」但**无任何用户确认证据**。需 engineer 提供证据或由用户裁定。

**其余部分**（§4 正文、abi.yaml 扩展、来源标注、spec 对回、C1–C17 落点、[OPEN] 登记、证据脚本质量、make check 全绿）**均通过**。

---

#### 第 2 轮复核（Fence 残留 token 删除后改判）

**触发**：用户裁定「内联 `Fence`」为残留 token/笔误，主会话已从任务书 §22 删除「、内联 `Fence`」。

**1. 核实 §22 不含 Fence**

```
$ grep -n "Fence" .tao/tasks/spec/SPEC-097t-标量调用约定合约.md
（仅命中审阅记录 E 段 12 行——历史记录，§22 正文无 Fence）
$ sed -n '22p' .tao/tasks/spec/SPEC-097t-标量调用约定合约.md
  - **范围**：**非变参标量**调用约定——参数寄存器分配（…）、prologue/epilogue（SP-only 与 FP 两套）。**不含**：变参、…（→ M4）。
```

✅ §22 已无「内联 `Fence`」。

**2. 重跑证据脚本**

```
$ bash .work/evidence/SPEC-097t/run.sh
EXIT=0
[PASS] C-main check_contract.py  (exit=0, expected=0)
[PASS] C-refs make check-spec-refs  (exit=0, expected=0)
[PASS] C-drift make check-spec-drift  (exit=0, expected=0)
[PASS] C-inject 注入有效（文件已改）
[PASS] C-inject check_contract.py 应 FAIL  (exit=1, expected=1)
[PASS] C-restore 还原成功（与备份逐字节一致）
[PASS] C-restore check_contract.py 应 PASS  (exit=0, expected=0)
RESULT: PASS
```

**3. 重跑 make check**

```
$ make check
EXIT=0
33/33 passed (100.00%)
check_issues: 42 open, 41 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

**4. 回归确认**

第 1 轮已通过项（§4 正文/来源标注、abi.yaml 解析与字段一致性、[OPEN]/M4 登记、C1–C17 落点表、独立注入验证、证据脚本质量）——本轮重跑 EXIT=0 全绿，**无回归**。

**5. 判决：改判 Accepted**

第 1 轮唯一卡点（「内联 `Fence`」范围缺失）已由用户裁定为残留 token 并从 §22 删除。删除后重跑全部验收命令 EXIT=0，无回归。`SPEC-097t` 可进入 `/complete`。
