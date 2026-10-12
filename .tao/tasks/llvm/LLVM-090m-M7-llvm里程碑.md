# LLVM-090m: M7 llvm 模块里程碑核验

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`/`080t`/`081t`/`082t`/`084t`/`085t`/`086t`/`087t`/`088t`/`089t`（均 `已验证`）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 architect 规划（2026-10-13）
- 立本 `m` 核验任务书（M7 llvm 模块里程碑）；M7 口径 10 条逐条引用 `milestones.md` M7 段落 + `INTEG-033k`；含跨模块影响（点 `ISS-193` 剩余面 / `ISS-197` / `ISS-200`）与「有未处置 ⇒ 不得置里程碑」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`llvm` 现场最大 `LLVM-089t` ⇒ 本 `m` = `LLVM-090m`（模块内跨后缀递增）。
