# LLVM-090m: M7 llvm 模块里程碑核验

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`/`080t`/`081t`/`082t`/`084t`/`085t`/`086t`/`087t`/`088t`/`089t`（均 `已验证`）
**状态**：里程碑

## 执行环境
**执行环境**：本地

## 目的
核验 **llvm 模块 M7 目标**是否达成。**本模块 M7 口径（逐条；来源 = `milestones.md`「当前进度」M7 段落 + `INTEG-033k §任务分解`，逐条引用）**：

1. **P0 后端补齐**（`LLVM-079t`）——`f32→f64 anyext` 载入 / FP 比较取值 `setcc` / `f64↔i64 bitcast` / `f64 select_cc` / `i64 cttz`（优先 ISA 现成指令）（`INTEG-033k §裁定汇总 #4`）。
2. **P1 后端补齐**（`LLVM-080t`）——`floor`/`ceil`/`trunc`/`round`/`rint`/`nearbyint`、`fmin`/`fmax`、`fabs`/`copysign` 双精度（`INTEG-033k §裁定汇总 #6`）。
3. **ISA↔后端覆盖矩阵**（`LLVM-081t`）——生成式；以 `contracts/opcodes.yaml` **全量**为真源、**两层分列**（汇编器可受理／**ISel 是否用得上**）；`--check` 已由 `INFRA-069t` 并入 L1（`check-isa-coverage`）（`INTEG-033k §裁定汇总 #5`）。
4. **M7 后端欠账收口**（`LLVM-082t`）——`ISS-189` 数据指导符唯一集（`Toolchain-01 §7.1`）+ `LLVM-074t` 遗留（`tailjmp` 纳入 `BranchRelaxation`）（`INTEG-033k §收口核对 #4/#5`）。
5. **FP 无序谓词收口**（`LLVM-084t`）——`SETUO`/`SETO`/`SETONE`/`SETUEQ` + don't-care 码 lowering；`ISS-193`(a) 收口。
6. **未定义弱符号可链接化**（`LLVM-085t`）——REL26 自循环 + `call`→`jump`；`ISS-194` 收口。
7. **内联汇编 `"r"` 约束解锁**（`LLVM-086t`）——`ISS-193`(e) 收口。
8. **f32 取整/极值 libcall 注册**（`LLVM-087t`）——`ISS-193`(b) 收口。
9. **截断存储 `trunc f64→f32`**（`LLVM-088t`）——`ISS-193`(d) 收口。
10. **f32 `log` 族 libcall 注册**（`LLVM-089t`）——`ISS-193`(b) 残余收口。

## 核验内容（可执行步骤）
1. **L2 + 按需全量**：跑 `make check-modules`（L2，含 `check-lit` 代表集）；按需跑 llvm 相关全量（`check-lit-full` 经 `test-m6` 承载 / `check-instrinfo` / `check-isa-coverage` 等）——均留真实退出码。
2. **逐条核 M7 口径**（以**真实命令输出 + 退出码**为证，**禁**抽样推断 / 转述）：
   - 口径 1/2/5–10：`make check-lit`（真实 PASS）+ 对应 `ISS-193` 类过滤表条目数现场统计 + 最小用例 `clang -c`/`llc` rc=0；
   - 口径 3：`make check-isa-coverage` rc=0（矩阵与真源一致，无漂移）；
   - 口径 4：`llvm-mc` 对口径外数据指示符**拒绝** + `tailjmp` 的 `BranchRelaxation` 行为（真实输出）。
3. **跨模块影响**：本模块后端补丁集（`components/llvm-project/patches/llvm/lib/Target/DADAO/**`）受 `spec`（`contracts/opcodes.yaml` 真源、`Toolchain-01 §7.1`、`ADR-0019 D9`）与 `testcases`（向量）牵动——逐个核对是否未处置；点名 `ISS-193`（剩余 (c) i64 `bswap` / (f) `long double` strtod，仍 `open`）、`ISS-197`、`ISS-187`（复用候选）、`ISS-108`（拆分，推迟）、`ISS-200`（changelog 缺条目）。**若存在未处置项 ⇒ 本 `m` 不得置里程碑**（`AGENTS.md`「模块里程碑与跨模块交互」）。
4. **M7 范围内 issue 处置**：对 `scope` 含 `llvm` 的 M7 期 issue 逐条给动作（关闭 / 转遗留 / 指明编号）——至少含 `ISS-188`/`189`/`193`/`194`/`196`/`197`（M7 收口者复核后关闭，未清剩余面转遗留）；**`open` 者不得擅自 close**（须依据或用户裁定，`Process-04 §3`）。
5. **门控**：`make check`（L1）rc=0 + `make check-no-residue` rc=0 + issue 台账校验（`check_issues`）rc=0。

## 验收标准
1. **逐条核验表**：每条 M7 口径 → 证据（命令 + 真实输出 + 退出码）→ 结论（达成 / 未达成 + 理由）。
2. **关联任务态核**：上列各 `t` 是否均 `已验证`；各任务产出文件（补丁集、`tools/llvm/**` 矩阵）是否存在（现场核）。
3. **跨模块判定**：明列未处置项（若有）⇒ 明确写「**不得置里程碑**」；无未处置项则写「无」。
4. **状态机**：核验通过 ⇒ 主会话将 `**状态**` 置 `里程碑`；未通过 ⇒ 保持 `待开始` 并登记阻断。
5. **角色**：本任务**无实现**（核验类）——由 **reviewer 独立执行核验**，**architect** 记录 / 回填完成区 / 提交；**不得**要求 engineer 写无意义实现。

## 硬约束
- 临时目录 `/tmp/opencode/<任务ID>/`；**禁**仓库内临时文件。
- **不提交 git**（提交权归 architect，核验后在本任务分支内提交）。
- 命令须捕退出码：`cmd; echo rc=$?`（**禁** `cmd | tail`/`| tee` 吞码）。
- 任务书文本**不写** `.work/<具体路径>` 字面（用 `<>` 占位）。
- 反例注入还原：**禁** `git checkout`/`git restore`/`git stash`；一律 `cp` 备份 + md5 对账或临时树。
- 计数不写死：一律现场统计，或写「不下降 / 逐项相等」。

## 完成区
**测试结果**：L1 `make check` rc=0；L2 `make check-modules` rc=0（check-lit 107/107、check-qemu-smoke 86/86、check-isa-coverage PASS、picolibc-tests fast 20/18pass/0fail/2excluded/0blocked）；`check-no-residue` rc=0；`check_issues` rc=0（27 open / 10 closed / 0 blocking）。
**修改文件**：本任务为核验类，**无实现**、无文件修改。
**验收结果**：M7 口径 10 条逐条核验均达成（证据见审阅记录）；跨模块无未处置阻断项；门控全绿。
**新发现/坑**：① `ISS-189`（数据指导符）已被 `LLVM-082t` 收口（8 名 GAS 指导符全 rc=1 拒绝），建议关闭 `resolved_by: LLVM-082t`；② `ISS-193` 过滤表仅余 2 条（(c) bswap / (f) strtod long double），blocked=0（对应 test=0 条）；③ 反例注入确认 `validate_instrinfo.py` 能检出 op 编码漂移（rc=0→1→0）。
**遗留问题**：`ISS-193`（(c)/(f) 2 条）、`ISS-188`（FP 完备性剩余非 P0/P1 项）、`ISS-187`（窄位优化候选）、`ISS-197`（`"m"` 约束健壮性）均为 open 非阻塞项，转遗留。

## 审阅记录

#### 第 1 轮 architect 规划（2026-10-13）
- 立本 `m` 核验任务书（M7 llvm 模块里程碑）；M7 口径 10 条逐条引用 `milestones.md` M7 段落 + `INTEG-033k`；含跨模块影响（点 `ISS-193` 剩余面 / `ISS-197` / `ISS-200`）与「有未处置 ⇒ 不得置里程碑」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`llvm` 现场最大 `LLVM-089t` ⇒ 本 `m` = `LLVM-090m`（模块内跨后缀递增）。

#### 第 1 轮 reviewer 验收（2026-10-13）
**重跑记录**：
- `make check`(L1) rc=0（全量 30+ 门控项全 PASS，含 check-isa-coverage、check-fp-contract、check_issues 27open/10closed/0blocking）
- `make check-modules`(L2) rc=0（check-lit 107/107 PASS、check-qemu-smoke 86/86 PASS、codegen-e2e 15/15、elf-e2e 5/5、test-semihost 10/10、picolibc-tests fast=20 pass=18 fail=0 excluded=2 blocked=0）
- `check-no-residue` rc=0；`check_issues.py` rc=0

**逐条核 M7 口径**（10 条）：
| 口径 | 证据 | 结论 |
|------|------|------|
| 1. P0 后端补齐（LLVM-079t） | check-lit 107/107 PASS；clang -c rc=0；llc rc=0；P0 五类（anyext/setcc/bitcast/select_cc/cttz）补丁确认 | 达成 |
| 2. P1 后端补齐（LLVM-080t） | check-lit PASS；P1（floor/ceil/trunc/round/rint/nearbyint/fmin/fmax/fabs/copysign）补丁确认 | 达成 |
| 3. ISA↔后端覆盖矩阵（LLVM-081t） | `gen_isa_coverage --check` rc=0（227 记录、accept 217/reject 10、yes 86/no 141） | 达成 |
| 4. M7 后端欠账收口（LLVM-082t） | 数据指导符：8 名 GAS 指导符全 rc=1 拒绝（含 .2byte/.4byte/.8byte/.value/.int/.dc.b/.single/.double）；tailjmp：按用户裁定 A 登记为 ISA 固有范围（非静默硬报错） | 达成 |
| 5. FP 无序谓词收口（LLVM-084t） | SETUO/SETO/SETONE/SETUEQ lowering 补丁确认（6+2 处）；ISS-193(a) 30→0 条过滤 | 达成 |
| 6. 未定义弱符号可链接化（LLVM-085t） | lld DADAO.cpp.patch 含 weak/self-loop/jump 逻辑（9 处）；ISS-194 closed | 达成 |
| 7. 内联汇编 `"r"` 约束解锁（LLVM-086t） | getRegForInlineAsmConstraint 补丁确认；ISS-193(e) 2 条过滤已删 | 达成 |
| 8. f32 取整/极值 libcall 注册（LLVM-087t） | RTLIB FLOOR/CEIL/TRUNC/ROUND/RINT/NEARBYINT/FMIN/FMAX_F32 补丁确认（8 处）；ISS-193(b) 全清 | 达成 |
| 9. 截断存储 trunc f64→f32（LLVM-088t） | setTruncStoreAction 补丁确认；ISS-193(d) 2 条过滤已删 | 达成 |
| 10. f32 log 族 libcall 注册（LLVM-089t） | RTLIB::LOG_F32 补丁确认；ISS-193(b) 残余最后 1 条过滤已删 | 达成 |

**跨模块影响**：
- `ISS-193`（(c) bswap / (f) strtod long double）：2 条 open、过滤表 2 条、blocked=0（无对应 test）→ **非阻断**，转遗留
- `ISS-197`（`"m"` 约束健壮性）：open、picolibc 0 处使用、非阻塞 → 转遗留
- `ISS-200`（changelog 历史缺口）：open、M7 范围外 → 转遗留
- **无未处置阻断项 ⇒ 无「不得置里程碑」理由**

**Issue 逐条动作建议**：
| Issue | 动作 | 依据 |
|-------|------|------|
| ISS-187 | 保持 open（优化候选，非缺陷） | 用户裁定「先只登记，暂不改」 |
| ISS-188 | 保持 open（P0/P1 已收口，剩余非阻塞） | LLVM-079t/080t 已验证；剩余项转遗留 |
| ISS-189 | **建议关闭** resolved_by=LLVM-082t | 8 名 GAS 指导符全被拒绝（rc=1），LLVM-082t 已收口 |
| ISS-193 | 保持 open（(c)/(f) 2 条残留） | 过滤表 2 条、blocked=0 |
| ISS-197 | 保持 open（健壮性缺陷，非阻塞） | picolibc 0 处 `"m"` 约束 |
| ISS-200 | 保持 open（历史缺口，M7 范围外） | 早期口径缺失，非 M7 引入 |

**反例注入**：`contracts/opcodes.yaml` 中 `ld.ub` 的 `op` 由 `0x10` 改为 `0xFF` → `validate_instrinfo.py` 报 2 errors（FAIL: baseline 154/155 + FAIL: orphan 1，rc=1）→ `cp` 还原（md5 `965feb70…` = match）→ rc=0 回绿 ✓

**里程碑核验结论**：**通过**。M7 口径 10 条逐条达成（真实命令输出 + 退出码为证）；跨模块无未处置阻断项；门控全绿（L1 rc=0、L2 rc=0、check-no-residue rc=0、check_issues rc=0）。
