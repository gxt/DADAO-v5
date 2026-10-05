# INFRA-042t: M3 归档前置 —— 遗留台账梳理（`spec/Process-04 §2`）

**模块**：infra
**项目里程碑**：M3
**依赖**：`INFRA-041t`、`milestones.md` M3 达成（2026-10-05）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`spec/Process-04-里程碑归档规范.md §2`（归档前遗留台账梳理，**MUST**，6 步）；`.tao/knowledge/issues.yaml`（**41 open**）；`.tao/knowledge/lessons.md`。
- **输出**：按 §2 梳理后的 `issues.yaml` + `lessons.md`；**逐条判定表**（id → 动作 + 依据）写入本任务书完成区。
- **步骤 1–2 已由 `INFRA-041t` 覆盖**（关闭 `ISS-040`/`130`；顺带修并关 `ISS-134/135/136/140/144/145`；8 条边界 notes）——本任务**记录引用、不重复**。
- **本任务做步骤 3–6**：
  - **3. 移出「教训/过程记录」类** → `lessons.md` 对应主题节（§2/§3/§5/§6/§7）；`issues.yaml` 中**删除**或**留极简指针**（`见 lessons §x.y`）；**id 不复用**，如实说明。候选（**须逐条判**）：`ISS-139`（子代理假称用户裁定，`lessons §7.3` 已存在）、`ISS-146`（验证产物残留，`§7.4` 已存在）、`ISS-088`（注入脆弱点无结构性拦截）、`ISS-087`（仓库外 agent 规则未同步）等。
  - **4. moot/过期判定**（**不得凭印象**，须指依据）：已被后续任务覆盖、或里程碑达成而失效者 → `closed`（附理由）。候选（**须逐条判**）：`ISS-005`/`006`/`008`（M3 边界项，M3 已达成、剩余归 M4）、`ISS-019`/`026`（M3 golden 相关，M3 无独立 golden 模块）、`ISS-074`/`081`/`110`（M3 未做/顺延 M4）等。
  - **5. 头部同步**：`issues.yaml` 头部「项目里程碑状态」更新（**M2 → ✅ 达成；M3 → ✅ 达成**）；`scope` 枚举补 `M4`（或与用户既有口径一致）；`M1-gate` 历史注保留；必要时补 `M3-gate` 是否退役说明。
  - **6. 交付**：**逐条判定表**（对**全部** open 项给出动作 + 依据）+ `tools/infra/check_issues.py` **EXIT=0**。
- **约束**：**只动** `issues.yaml` + `lessons.md`（+ 判定表落本任务书）；不改 `spec/` 正文、`contracts/` 编码、其它任务书；id 不复用；不改已 `closed` 项内容（除归档指针）。
- **注意**：本步骤属**归档前置**——完成后方可进入 §3 归档判据任务。

## 验收标准

1. §2 步骤 3–6 逐条完成；**逐条判定表**（全部 open 项：id → 动作〔保留 open / closed / 移入 lessons〕+ 依据）写入完成区；处理条数与本任务前/后 open 计数自洽。
2. 移入 `lessons.md` 的条目**已落对应主题节**且内容准确；`issues.yaml` 无遗留重复；**id 不复用**，如实说明。
3. moot/过期项 `closed` + **理由可指依据**（任务 ID / 日期 / 证据）。
4. `issues.yaml` 头部里程碑状态同步（M2/M3 → ✅ 达成）；`yaml.safe_load` EXIT=0。
5. `tools/infra/check_issues.py` **EXIT=0**；`make check` EXIT=0（门控）。
6. 无仓库残留；一键证据 `.work/evidence/INFRA-042t/run.sh`（规格同 `LLVM-033t`；对可机械检查者含反例注入）。

## 完成区

**测试结果**：通过。
- 一键证据 `.work/evidence/INFRA-042t/run.sh`：**10/10 PASS，EXIT=0**（日志 `.work/log/infra/INFRA-042t-evidence.log`）。
- 反例自检 `run.sh --inject`：**8/8 注入→FAIL→还原→回绿，EXIT=0**（日志 `.work/log/infra/INFRA-042t-evidence-inject.log`）。
- `tools/infra/check_issues.py`：**EXIT=0**，`35 open, 56 closed (0 blocking M1-gate: 0)`。
- `make check`：**EXIT=0**，lit **34/34**、`repository checks: PASS`（日志 `.work/log/infra/INFRA-042t-make-check.log`）。
- `yaml.safe_load(issues.yaml)`：**EXIT=0**（91 条 = 35 open + 56 closed）。
- 失败原因：无。

**修改文件**（`git status` 仅见下列 3 个受版控文件 + 本任务书 untracked）：
- `.tao/knowledge/issues.yaml`：step 3–6 全部处置（头部同步、scope 枚举 +M4、边界项拆分、教训类移出、step 4 关闭 2 项）。
- `.tao/knowledge/lessons.md`：新增 `§2.6`（承接 ISS-088）、`§6.6`（承接 ISS-087）；`§7.3`/`§7.4` 的 `→ ISS-139/146` 指针改为「原 id 已并入本文件、退役不复用」。
- `spec/Process-04-里程碑归档规范.md`：§2 step 4 增补「里程碑边界项拆分处置」规则（**用户 2026-10-05 明确指示「写到流程规范里」**；**越出** dispatch 硬约束 #4「只动 issues.yaml + lessons.md」，已披露，见「遗留问题」）。
- `.work/evidence/INFRA-042t/run.sh`（`/tmp/opencode/INFRA-042t/` 仅临时日志；证据脚本按约定留 `.work/`，gitignored）。
- 日志：`.work/log/infra/INFRA-042t-{evidence,evidence-inject,make-check}.log`。
- 本任务书（状态 + 完成区 + 自审）。
- **未触碰** `contracts/`、其它 `spec/` 正文、其它任务书、`.tao/archive/**`、`.work/evidence/{LLVM-*,INFRA-*}` 既有脚本。

**验收结果**（真实命令 + 输出，完整见日志）：

1) 一键证据（`.work/log/infra/INFRA-042t-evidence.log`）：
```
[PASS] issues-yaml | expected: yaml ok; 91/35/56; ids unique; schema valid | actual: ok: 91 total / 35 open / 56 closed; ids unique; schema valid | rc=0
[PASS] header | expected: M2/M3 ✅ 达成; scope enum +M4; M1-gate/M3-gate notes | actual: all present | rc=0
[PASS] boundary | expected: 8 items open, scope M4 (no M3), notes M3+M4 | actual: ok: 8 boundary items open with M4 scope and M3/M4 notes | rc=0
[PASS] split | expected: 005/006/008 open; ISS-149/150 closed+resolved_by+cross-ref | actual: ok | rc=0
[PASS] moved | expected: 087/088/139/146 out of issues; §2.6/§6.6/§7.3/§7.4 in lessons | actual: ok | rc=0
[PASS] step4-closed | expected: ISS-015/INFRA-016t + ISS-039/LLVM-014t closed | actual: ok | rc=0
[PASS] process-rule | expected: Process-04 §2 step 4 carries boundary-item rule | actual: ok | rc=0
[PASS] ids-not-reused | expected: 087/088/139/146 absent; 149/150 present; max=150 | actual: ok | rc=0
[PASS] check-issues | expected: check_issues.py rc=0 | actual: check_issues: 35 open, 56 closed (0 blocking M1-gate: 0) | rc=0
[PASS] make-check | expected: make check rc=0 | actual: rc=0, repository checks: PASS | rc=0
RESULT: PASS (10 checks, 0 failures)
EXIT=0
```

2) 反例自检（`.work/log/infra/INFRA-042t-evidence-inject.log`，8 例各自靶向不同检查）：
```
inject[issues-schema]:  AssertionError ('ISS-149','open with resolved_by') -> 还原 [PASS] ; PASS
inject[header]:         no-M3-done -> 还原 [PASS]                                   ; PASS
inject[boundary]:       AssertionError ('ISS-005','still M3-scoped') -> 还原 [PASS]  ; PASS
inject[split]:          AssertionError ('ISS-150','open') -> 还原 [PASS]            ; PASS
inject[moved]:          no-§6.6 -> 还原 [PASS]                                       ; PASS
inject[step4]:          AssertionError ('ISS-015','open') -> 还原 [PASS]            ; PASS
inject[process-rule]:   no-boundary-item-rule ... -> 还原 [PASS]                    ; PASS
inject[ids-reuse]:      AssertionError ('ISS-146','retired id reused') -> 还原 [PASS]; PASS
INJECT RESULT: PASS (8/8 injections FAIL then green)
EXIT=0
```
> 注入均改**真实文件**、以 `sha256` 断言「注入生效 + 还原一致」（脚本 `inject_run`）；`git status` 注入后仍仅 3 个应改文件。

3) `check_issues.py`：
```
$ python3 tools/infra/check_issues.py ; echo "EXIT=$?"
check_issues: 35 open, 56 closed (0 blocking M1-gate: 0)
EXIT=0
```

4) `make check`（`.work/log/infra/INFRA-042t-make-check.log`）：
```
$ make check > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
Total Discovered Tests: 34
  Passed: 34 (100.00%)
check_issues: 35 open, 56 closed (0 blocking M1-gate: 0)
repository checks: PASS
```

5) 计数自洽：处理前 `41 open / 52 closed / 93 total` → 处理后 `35 open / 56 closed / 91 total`。
`open: 41 − 4（ISS-087/088/139/146 移出）− 2（ISS-015/039 closed）= 35`；`closed: 52 + 2（015/039）+ 2（新 ISS-149/150）= 56`；`total: 93 − 4 + 2 = 91`。

### 逐条判定表（对处理前**全部 41 个 open 项**：id → 动作 + 依据）

| id | 动作 | 依据（可指） |
|----|------|--------------|
| ISS-003 | 保留 open；scope `post-M1`→`M4` | 三项（FP RF/cfx/LR-SC 原子）均未实现；M2/M3 已达成 ⇒ 归 M4（ISS-081/110 追踪 FP/cfx） |
| ISS-005 | 保留 open（未交付部分，归 M4）＋ 新增 **closed ISS-149**（交付部分） | 用户 2026-10-05 裁定；M3 交付标量 CC（`SPEC-097t`+`LLVM-039t`，均 `已验证`），剩余变参/聚合/多返回/sret/间接调用归 M4 |
| ISS-006 | 保留 open；scope `M3`→`M4` | 主题 5 项 `[OPEN]`（`contract-abi.md §6`）M3 未交付其中任何一项（note 所指『已交付部分』= ISS-005 的标量 CC，记录见 ISS-149） |
| ISS-008 | 保留 open（未交付部分，归 M4）＋ 新增 **closed ISS-150**（交付部分） | 用户 2026-10-05 裁定；M3 交付最小重定位（`LLVM-041t`，`已验证`），剩余完整重定位/LLD 归 M4 |
| ISS-011 | 保留 open | 编码知识条（0628 `tools/opcodes.yaml` 不可作权威）；无消解记录，仍有规范价值 |
| ISS-014 | 保留 open | `ADR-0005` Consequences C2 表述待精确；无消解任务 |
| ISS-015 | **closed**（step 4 已被后续任务覆盖） | `INFRA-016t`（`已验证`）在 `tools/infra/doctor.py` 增 `component-deps` 层（`_QEMU_PKGS`/`_LIBFDT_HEADER` 实测在文件内） |
| ISS-019 | 保留 open；scope `M3`→`M4` | golden 模块 M3 未启动；结果级/FP 独立 oracle 未交付 |
| ISS-026 | 保留 open；scope `M3`→`M4` | golden model imm 语义守卫 M3 未交付 |
| ISS-038 | 保留 open | `createDadaoELFObjectWriter` 仅在自身文件 + `CMakeLists.txt` 出现、未注册（死代码）——实测 `grep -rln DADAOELFObjectWriter` 仅 2 命中 |
| ISS-039 | **closed**（step 4 已被后续任务覆盖） | `LLVM-014t`（commit `d3ee023`）设 `setELFHeaderEFlags(0x1)`；`tests/lit/MC/Dadao/e_flags.s` CHECK `Flags[0x1]`、lit 34/34 PASS；与已 closed 的 `ISS-007` 同因 |
| ISS-043 | 保留 open | 分支/跳转 fixup 越界静默截断；无消解任务 |
| ISS-044 | 保留 open | 未定义符号静默留 0（`call ext_sym`）；无消解任务（同域 ISS-142） |
| ISS-045 | 保留 open | `getFixupKindForInstr` default 未白名单化；无消解任务 |
| ISS-047 | 保留 open | `llvm-objdump -d` 需显式 `--triple`；无消解任务 |
| ISS-050 | 保留 open | `dadao_cpu_tlb_fill` 未用 `access_type`/未 48 位屏蔽；无消解任务 |
| ISS-054 | 保留 open | 探针标签化框架建议；`tools/qemu/` 无该框架 |
| ISS-058 | 保留 open | `decodetree.py` 输出依赖 `PYTHONHASHSEED`；无消解任务 |
| ISS-064 | 保留 open | `cpu_loop_exit` longjmp 泄漏 MMIO re-entrancy 守卫；无消解任务 |
| ISS-074 | 保留 open；scope `M3`→`M4` | `reg-cond-assign.yaml` 5 条 `C-27` overlap 语义 M3 未交付 |
| ISS-078 | 保留 open | `focls/ftcls` 之外 FP 指令未复核；无消解任务 |
| ISS-081 | 保留 open；scope `M3`→`M4` | M3=纯整数 CodeGen，FP/RF 后续（oracle/harness/向量/E2E）未交付 |
| ISS-087 | **移入 `lessons.md §6.6`**（issues 删除，id 不复用） | 过程记录（仓库外 agent 规则未同步），非本仓待办；用户 2026-10-05 裁定 |
| ISS-088 | **移入 `lessons.md §2.6`**（issues 删除，id 不复用） | 方法论/工具陷阱记录；用户 2026-10-03 裁定「暂不修，仅登记」；用户 2026-10-05 裁定移入 |
| ISS-090 | 保留 open | `components/qemu/changelog.md` 缺 2026-09-23 起历史行（QEMU-025t~033t）；未补全 |
| ISS-093 | 保留 open | 行内 code span 检测（方案 b）deferred；未处理 |
| ISS-098 | 保留 open | harness `ret`/`call` 语义 pre-existing 失败；无消解任务 |
| ISS-102 | 保留 open | 覆盖门控 `(id,class)` 粒度；无消解任务 |
| ISS-108 | 保留 open | LLVM 大文件（>1000 行）建议性跟踪；未处理 |
| ISS-110 | 保留 open；scope `M3`→`M4` | cfx 仍 `scope: excluded`/decode ILLI，M3 未交付 |
| ISS-117 | 保留 open | `check_interface_alignment.py` e_flags 检测假绿；未处理 |
| ISS-118 | 保留 open | lit 覆盖断言粒度（不可解）；未处理 |
| ISS-120 | 保留 open | `min_rom_probe_*` 群 pre-existing 漂移；未处理 |
| ISS-125 | 保留 open | 生成器↔向量漂移余 4 文件；未清 |
| ISS-126 | 保留 open | FP 开放点固定取值（供 GOLDEN 参照）；未处理 |
| ISS-138 | 保留 open | >128K 帧 scheme 1 未实现（`DADAORegisterInfo.cpp.patch` 显式「scheme 1 not implemented」在） |
| ISS-139 | **移入 `lessons.md §7.3`**（issues 删除；`§7.3` 已存在，id 不复用） | 教训（子代理假称裁定），issues 中为重复条目 |
| ISS-142 | 保留 open | 未定义/跨 section 引用静默留 0 + 无 relocation（→M4）；无消解任务 |
| ISS-146 | **移入 `lessons.md §7.4`**（issues 删除；`§7.4` 已存在，id 不复用） | 教训（验证产物残留），issues 中为重复条目 |
| ISS-147 | 保留 open | E2E 期望值 137 落 fault 区（`tests/codegen/call_narrow_args.ll` 实测 `137`） |
| ISS-148 | 保留 open | `gen_m1_asm.py`/`test_m1_asm.py` docstring 仍写「177」（实测） |

> **moot/过期判定结论**：除 step 4 关闭的 `ISS-015`/`ISS-039`（已被 `INFRA-016t`/`LLVM-014t` 覆盖）外，**无其它 moot/过期项**——8 个 M3 边界项经 `SPEC-096k §M4 交接`/`milestones.md` 证实其剩余为**真实 M4 工作**（故按用户裁定拆分/保留，非失效），其余 31 项均为未消解的工作项（依据见上表）。**逐条均指依据，无凭印象。**

**新发现/坑**：
- **`INFRA-041t` 的 step 1 有漏网**：`ISS-015`（`INFRA-016t` 已修 `doctor.py`）、`ISS-039`（`LLVM-014t` 已修 e_flags，实为 `ISS-007` 的重复条目）此前仍 `open`；本任务 step 4「已被后续任务覆盖」补关。建议：归档前的 step 1 应按「任务标题 ↔ 现存 open 项」交叉扫描，避免漏关。
- **`ISS-006` 的边界 note 有误导**：`INFRA-041t` 写「M3 已交付部分 = 标量调用约定」，但该交付实为 `ISS-005` 的主题；`ISS-006` 主题（5 项 `[OPEN]`）M3 未交付任何一项。本任务在 note 中加注澄清，**未**为其另建 closed 条目（避免与 `ISS-149` 重复）。
- **`scope` 枚举缺 `M4` 是前序 block 点**：`INFRA-041t` 因枚举不含 `M4` 只能改 `notes`、不能改 `scope`；本任务补枚举后，将 8 个边界项 + `ISS-003` 的 scope 校正到 `M4`（`Process-04 §2.2`）。
- **用户裁定已固化**：边界项「交付部分单独 close、未交付部分留 open」写入 `spec/Process-04 §2` step 4，后续里程碑归档不再询问。

**遗留问题**：
- **越界披露**：`spec/Process-04-里程碑归档规范.md` 的改动**越出**本任务 dispatch 硬约束「只动 `issues.yaml` + `lessons.md`」，系**用户 2026-10-05 明确指示**「写到流程规范里」；特此披露，供 reviewer/主会话核验。
- 其余无未完成项；step 3–6 全部完成，仓库无残留（`git status` 仅 3 个应改文件 + 本任务书）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`.tao/knowledge/issues.yaml`（全文件 diff）、`.tao/knowledge/lessons.md`（§2.6/§6.6/§7.3/§7.4）、`spec/Process-04-里程碑归档规范.md`（§2 step 4）、`.work/evidence/INFRA-042t/run.sh`（全文）。

**审查要点（逐行）**：
- **逻辑正确性**：`issues.yaml` diff 逐条核对——头部 M2/M3 达成、M4 枚举与状态、M3-gate 注；`ISS-003`/`005`/`006`/`008`/`019`/`026`/`074`/`081`/`110` scope 校正；`ISS-149`/`150` 新 closed 条目（`resolved_by` 指向 `SPEC-097t`+`LLVM-039t` / `LLVM-041t`，均 `已验证`）；`ISS-015`/`039` 关闭；`ISS-087/088/139/146` 删除。计数自洽（41→35 open / 52→56 closed / 93→91 total）。
- **设计/惯用法**：拆分遵循「**原 id 保留给 open 剩余**、新 id 给 closed 交付部分」（保留 `milestones.md`/`SPEC-096k` 对 `ISS-005`/`008` 的引用）；教训类「先落 lessons 节、再从 issues 删」并更新 `§7.3`/`§7.4` 反向指针，避免悬空引用；`Process-04` 规则追加在 step 4 下作子条目，不破坏有序列表结构。
- **边界情况**：`ISS-006` 的「已交付部分」经复核实为 `ISS-005` 的交付 ⇒ **不**为 `ISS-006` 建 closed 条目（避免重复），改为 note 加注；`ISS-038` 经 `grep` 确认 ELF writer 仍未注册 ⇒ 保持 open（不误关）。
- **防造假**：所有命令 `cmd > log 2>&1; rc=$?`；证据脚本 `inject_run` 以 `sha256` 断言注入生效（非空）与还原一致；完成区结论逐条对齐真实输出；无 `tee`。
- **门控可达性**：`--inject` 8 例各自使不同检查 FAIL（非恒真、非「两支同写」），还原后回绿；`check_issues.py`/`make check` 独立 EXIT=0。
- **约束核查**：临时目录 `/tmp/opencode/INFRA-042t/`（仓库内无临时文件）；未提交 git；除**用户指示的** `Process-04` 外只动 `issues.yaml`+`lessons.md`；未改 `contracts/` 编码、未改其它任务书、未改已 closed 项内容（除 `ISS-015/039` 的关闭 + 归档指针）。

**findings 与处置**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 证据脚本 `moved` 检查误用字面 `§7.3`/`§7.4`（lessons 实为 `### 7.3`/`### 7.4` 标题），致默认运行 FAIL | ✅已修 | 改为 `grep '### 7.3 …'`/`'### 7.4 …'` | `run.sh` 重跑 10/10 PASS EXIT=0 |
| 2 | `INFRA-041t` step 1 漏关 `ISS-015`/`ISS-039`（已被后续任务消解） | ✅已修 | step 4 判为「已被后续任务覆盖」→ `closed` + `resolved_by` | `ISS-015→INFRA-016t`、`ISS-039→LLVM-014t`；证据脚本 `step4-closed` PASS |
| 3 | `ISS-006` 边界 note 声称「M3 已交付部分」实为 `ISS-005` 的交付 | ✅已修（加注澄清，不重复建档） | note 加 INFRA-042t 澄清句；`ISS-006` 保持 open | `boundary`/`split` PASS；`grep` 确认 5 项 `[OPEN]` 仍在 |
| 4 | `spec/Process-04` 改动越出 dispatch 硬约束 | ⏸披露（用户指示） | §2 step 4 增补边界项规则 | `process-rule` PASS；「遗留问题」已披露 |
| 5 | `ISS-003` 的 `post-M1` 是否需明确化（§2.2） | ✅已修 | scope `post-M1`→`M4` + note | `issues-yaml`/`header` PASS |
| 6 | 新 id 是否复用退役 id | ✅已核 | 新条目 `ISS-149/150`（max=150） | `ids-not-reused` PASS + 注入 `ids-reuse` FAIL |

**自审判决**：无未修 finding（#4 为有依据的披露）。10/10 证据 + 8/8 注入全绿，`check_issues.py`/`make check` EXIT=0，仓库无残留。任务状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查日期**：2026-10-05

---

### 一、证据脚本审核

`.work/evidence/INFRA-042t/run.sh`（354 行）逐项审核：

| 维度 | 判定 |
|------|------|
| 检查项覆盖 | 10 项（issues-yaml / header / boundary / split / moved / step4-closed / process-rule / ids-not-reused / check-issues / make-check），覆盖验收标准全部 |
| FAIL 路径可达 | 每项均有明确断言或 `rc=1` 分支，非恒真（如 `assert e['status'] == 'open'` / `grep -q` 失败即 `rc=1`） |
| 注入靶 | 8 项各自靶不同检查/不同文件，无「两支同写同一结果」 |
| 注入机制 | `inject_run`：`cp` 备份 → `sha256` 前值 → 注入 → 校 sha256 非空且已变 → 跑检查 → 确 FAIL → `cp` 还原 → 校 sha256 一致 → 重跑确认回绿 |
| 退出码 | 末尾 `echo "EXIT=$rc"; exit "$rc"`，无 `tee` 吞退出码 |

**结论**：脚本合格，不代写/不改。

---

### 二、重跑证据脚本

#### 2.1 正常运行

```
$ bash .work/evidence/INFRA-042t/run.sh > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

逐项输出：

| # | 检查名 | 实际 | rc |
|---|--------|------|----|
| 1 | issues-yaml | ok: 91 total / 35 open / 56 closed; ids unique; schema valid | 0 |
| 2 | header | all present | 0 |
| 3 | boundary | ok: 8 boundary items open with M4 scope and M3/M4 notes | 0 |
| 4 | split | ok: 005/006/008 open; ISS-149/150 closed with resolved_by + cross-ref | 0 |
| 5 | moved | ok | 0 |
| 6 | step4-closed | ok: ISS-015->INFRA-016t, ISS-039->LLVM-014t (closed) | 0 |
| 7 | process-rule | ok | 0 |
| 8 | ids-not-reused | ok: retired ids absent; ISS-149/150 present; max id 150 | 0 |
| 9 | check-issues | check_issues: 35 open, 56 closed (0 blocking M1-gate: 0) | 0 |
| 10 | make-check | rc=0, repository checks: PASS | 0 |

**RESULT: PASS (10 checks, 0 failures) / EXIT=0**

#### 2.2 注入自检

```
$ bash .work/evidence/INFRA-042t/run.sh --inject > log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

逐项：

| # | 注入靶 | 注入→FAIL 证据 | 还原→回绿 | sha256 一致 |
|---|--------|---------------|----------|------------|
| 1 | issues-schema | AssertionError ('ISS-149','open with resolved_by') | PASS | ✓ |
| 2 | header | no-M3-done | PASS | ✓ |
| 3 | boundary | AssertionError ('ISS-005','still M3-scoped') | PASS | ✓ |
| 4 | split | AssertionError ('ISS-150','open') | PASS | ✓ |
| 5 | moved | no-§6.6 | PASS | ✓ |
| 6 | step4 | AssertionError ('ISS-015','open') | PASS | ✓ |
| 7 | process-rule | no-boundary-item-rule no-rule-text no-user-ruling-date | PASS | ✓ |
| 8 | ids-reuse | AssertionError ('ISS-146','retired id reused') | PASS | ✓ |

**INJECT RESULT: PASS (8/8 injections FAIL then green) / EXIT=0**

---

### 三、独立注入（reviewer 自选，不在工程师 8 项内）

**注入靶**：`ISS-005` scope `[M4]` → `[MX]`（改 scope 枚举值，删除 M4）

**注入命令**：
```python
# 替换 ISS-005 的 scope: [M4] -> scope: [MX]
s.replace('scope: [M4]', 'scope: [MX]', 1)
```

**注入后验证**：
```
ISS-005 scope: ['MX']
BOUNDARY CHECK: FAIL (ISS-005 missing M4 scope)
```

**还原**：
```python
s.replace('scope: [MX]', 'scope: [M4]', 1)
```

**还原后验证**：
```
ISS-005 scope: ['M4']
BOUNDARY CHECK: PASS
```

**git diff --name-only**（注入前/还原后一致）：
```
.tao/knowledge/issues.yaml
.tao/knowledge/lessons.md
spec/Process-04-里程碑归档规范.md
```

**结论**：独立注入确认——改 scope 后 boundary 检查 FAIL，还原后回绿。脚本的 boundary 检查具有鉴别力。

---

### 四、步骤 3–6 独立复核

#### 步骤 3：教训/过程记录移出

| 验证项 | 结果 |
|--------|------|
| ISS-087 在 issues.yaml | ✘ 不存在（已删除） |
| ISS-088 在 issues.yaml | ✘ 不存在（已删除） |
| ISS-139 在 issues.yaml | ✘ 不存在（已删除） |
| ISS-146 在 issues.yaml | ✘ 不存在（已删除） |
| `lessons.md §2.6`（ISS-088） | ✓ 存在：`### 2.6 注入/验证的脆弱点无结构性拦截（原 'ISS-088'）` |
| `lessons.md §6.6`（ISS-087） | ✓ 存在：`### 6.6 仓库外全局 agent 规则未同步新验收规程（原 'ISS-087'）` |
| `lessons.md §7.3`（ISS-139） | ✓ 存在，含 `原 'ISS-139' 已随本条并入` 指针 |
| `lessons.md §7.4`（ISS-146） | ✓ 存在，含 `原 'ISS-146' 已随本条并入` 指针 |
| id 不复用 | ✓ ISS-087/088/139/146 不在 issues.yaml；新 id ISS-149/150 max=150 |

#### 步骤 4：逐条判定表核验

**边界项（8 项）scope 校正**：

| id | scope | status | notes 含 M3+M4 | 判定 |
|----|-------|--------|---------------|------|
| ISS-005 | [M4] | open | ✓ | ✓ |
| ISS-006 | [M4] | open | ✓ | ✓ |
| ISS-008 | [M4] | open | ✓ | ✓ |
| ISS-019 | [golden, M4] | open | ✓ | ✓ |
| ISS-026 | [testcases, M4] | open | ✓ | ✓ |
| ISS-074 | [testcases, M4] | open | ✓ | ✓ |
| ISS-081 | [spec, golden, testcases, llvm, qemu, integ, M4] | open | ✓ | ✓ |
| ISS-110 | [llvm, M4] | open | ✓ | ✓ |

**拆分项**：

| 新 id | 来源 | status | resolved_by | notes 含 cross-ref | 判定 |
|-------|------|--------|-------------|-------------------|------|
| ISS-149 | ISS-005 | closed | SPEC-097t+LLVM-039t | ✓ | ✓ 与用户裁定一致 |
| ISS-150 | ISS-008 | closed | LLVM-041t | ✓ | ✓ 与用户裁定一致 |

**原 id 保留 open**：ISS-005/006/008 均 open ✓

**step 4 补关**：

| id | status | resolved_by | 依据 | 判定 |
|----|--------|-------------|------|------|
| ISS-015 | closed | INFRA-016t | doctor.py component-deps 层 | ✓ 真实存在 |
| ISS-039 | closed | LLVM-014t | setELFHeaderEFlags(0x1) | ✓ 真实存在 |

**ISS-006 澄清**：判定表称「M3 未交付任何一项」，实测 `ISS-006` 的 `contract-abi.md §6` 仍列 5 项 `[OPEN]`，note 中加注澄清。✓ 不重复建档（交付部分已归 ISS-149）。

**ISS-003 scope 校正**：`post-M1` → `M4`，实测 scope=['M4'] ✓

**其余 31 项保留 open**：判定表逐条指依据（任务 ID / 文件内容 / grep 结果），无凭印象。✓

**计数自洽**：41 open → 移出 4（087/088/139/146）+ 关闭 2（015/039）= 35 open；52 closed + 2（015/039）+ 2（149/150）= 56 closed；93 total − 4 + 2 = 91 total。实测 35/56/91 ✓

#### 步骤 5：头部同步

| 验证项 | 结果 |
|--------|------|
| M2 = ✅ 达成 | ✓（第 7 行） |
| M3 = ✅ 达成 | ✓（第 10 行） |
| M4 = 未规划 | ✓（第 13 行） |
| scope 枚举含 M4 | ✓（第 28 行） |
| M1-gate 历史注 | ✓（第 14–18 行） |
| M3-gate 退役说明 | ✓（第 20–23 行） |

#### 步骤 6：交付

| 验证项 | 命令 | 输出 | EXIT |
|--------|------|------|------|
| check_issues.py | `python3 tools/infra/check_issues.py` | 35 open, 56 closed (0 blocking M1-gate: 0) | 0 |
| yaml.safe_load | `python3 -c "import yaml; ..."` | total=91, open=35, closed=56 | 0 |
| make check | `make check` | lit 34/34, repository checks: PASS | 0 |

---

### 五、Process-04 改动判定

**位置**：`spec/Process-04-里程碑归档规范.md` 第 26 行，§2 step 4 子条目。

**内容**：新增「里程碑边界项拆分处置」规则，忠实于用户裁定（2026-10-05）：
- 交付部分单独 `closed`（新 id），`resolved_by` 指向交付任务
- 原 id 保留给未交付 `open` 条目，不复用
- 未交付部分留 `open`，scope 校正到下一里程碑
- 不得整条一并 closed，也不得一律保留

**自洽性**：
- 与 §2 step 4 原文（moot/过期判定）结构一致，作为子条目不破坏有序列表
- 与 §3 归档判据不冲突（新 closed 条目的 resolved_by 日期 ≤ 达成日，符合§3.4）
- 与 §4 归档结构兼容

**越界说明**：改动超出 dispatch 硬约束「只动 issues.yaml + lessons.md」，但系用户 2026-10-05 明确指示「写到流程规范里」，已在任务书遗留问题披露。✓

---

### 六、门控

- `make check`：EXIT=0，lit 34/34，repository checks: PASS ✓
- `git status`：仅 3 个应改文件 + 本任务书 untracked，无残留 ✓

---

### 判决

**Accepted**

验收命令块 10/10 全绿（独立重跑）、8/8 注入全绿、独立注入 1/1 确认鉴别力、步骤 3–6 逐项复核通过、判定表 41 条逐条成立、Process-04 改动忠实且自洽、门控全绿、仓库无残留。
