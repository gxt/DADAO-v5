# SPEC-136m: M7 spec 模块里程碑核验

**模块**：spec
**项目里程碑**：M7
**依赖**：`SPEC-131t`/`133t`/`134t`/`135t`（均 `已验证`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目的
核验 **spec 模块 M7 目标**是否达成。**本模块 M7 口径（逐条；来源 = `milestones.md`「当前进度」M7 段落 + `INTEG-033k §任务分解`，逐条引用）**：

1. **过渡 oracle 约定 + semihosting `cfxha` 口径 + 锁同步**（`SPEC-131t`）——宿主机结果作参照 + 明确边界（端序 / `long double`=f64 vs 宿主 80-bit / `fenv` / UB / 实现定义），登记为「**非判据真源**」；`trap` 的 `cfxha` 口径澄清（`contract-semihosting §1` / `Machine-01 §5.1`）与 `cfx3` vs `cfx_umon`(cfx0) 一致性处置（`INTEG-033k §裁定汇总 #7/#9`）。
2. **标题章节号统一与引用同步**（`SPEC-133t`）——21 册标题/章节号统一，引用随之同步（`milestones.md` 流水行）。
3. **附录版本与变更记录**（`SPEC-134t`）——21 册「附录：版本与变更记录」+ `-rc` 版本口径 + `spec/README.md` 册维护约定（`milestones.md §规划中`「目录三分界与规范版本号」）。
4. **未定义弱符号口径固化**（`SPEC-135t`）——`ADR-0019` 就地追加 `D9` + `contract-elf §3.3` 正文；口径 = PC 相对分支/call 解析为**本位自循环**（`call-iiii`→`jump-iiii` 改写，免 RegRAS 失衡）（`milestones.md §规划中`「`ADR-0019`/`contract-elf` 增补」）。

## 核验内容（可执行步骤）
1. **L2 + 按需全量**：跑 `make check-modules`（L2 模块代表集）；按需跑 spec 相关全量（`check-spec-drift`/`check-spec-refs`/`check-spec-numbering`/`check-spec-changelog`/`check-scope`/`validate-encoding`/`check-spec-readonly` 等）——均留真实退出码。
2. **逐条核 M7 口径**（以**真实命令输出 + 退出码**为证，**禁**抽样推断 / 转述）：
   - 口径 1：`contract-semihosting §1` + `spec/Machine-01 §5.1` 正文存在且口径一致；过渡 oracle 约定正文/合约存在（真实 `grep` 证据）；
   - 口径 2/3：`make check-spec-numbering`/`check-spec-changelog` rc=0（L1 承载）；21 册附录章节现场清点；
   - 口径 4：`ADR-0019` `D9` 与 `contract-elf §3.3` 正文存在（真实 `grep`）。
3. **跨模块影响**：本模块为**规范正文 + 合约**真源，被 `infra`/`llvm`/`qemu`/`testcases` 的实现/向量所依赖——逐个核对是否未处置；点名 `ISS-201`（未定义弱符号防御分支未入规范，**须用户逐条确认**才能改已确认的 `D9`）、`ISS-202`（`contract-*.md`→`contracts/` 迁移跨 `spec` 只读锁册 `Toolchain-01`，待授权）、`ISS-190`/`ISS-192`/`ISS-160`/`ISS-126`。**若存在未处置项 ⇒ 本 `m` 不得置里程碑**（`AGENTS.md`「模块里程碑与跨模块交互」）。
4. **M7 范围内 issue 处置**：对 `scope` 含 `spec` 的 M7 期 issue 逐条给动作（关闭 / 转遗留 / 指明编号）——至少含 `ISS-201`（待用户裁定）、`ISS-192`、`ISS-160`、`ISS-190`、`ISS-126`；**`open` 者不得擅自 close**（须依据或用户裁定，`Process-04 §3`）。
5. **门控**：`make check`（L1）rc=0 + `make check-no-residue` rc=0 + issue 台账校验（`check_issues`）rc=0。

## 验收标准
1. **逐条核验表**：每条 M7 口径 → 证据（命令 + 真实输出 + 退出码）→ 结论（达成 / 未达成 + 理由）。
2. **关联任务态核**：`SPEC-131t`/`133t`/`134t`/`135t` 是否均 `已验证`；各任务产出文件（`spec/` 正文、`contract-*.md`、`ADR-0019`）是否存在（现场核）。
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
- 立本 `m` 核验任务书（M7 spec 模块里程碑）；M7 口径 4 条逐条引用 `milestones.md` M7 段落 + `INTEG-033k`；含跨模块影响（点 `ISS-201`/`202` 等）与「有未处置 ⇒ 不得置里程碑」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`spec` 现场最大 `SPEC-135t` ⇒ 本 `m` = `SPEC-136m`（模块内跨后缀递增）。
