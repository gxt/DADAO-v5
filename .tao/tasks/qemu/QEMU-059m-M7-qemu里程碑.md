# QEMU-059m: M7 qemu 模块里程碑核验

**模块**：qemu
**项目里程碑**：M7
**依赖**：`QEMU-056t`/`058t`（均 `已验证`）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目的
核验 **qemu 模块 M7 目标**是否达成。**本模块 M7 口径（逐条；来源 = `milestones.md`「当前进度」M7 段落 + `INTEG-033k §任务分解`，逐条引用）**：

1. **RAM 基址改 `0xFC00_0000_0000`**（`QEMU-056t`）——`[47:42]≡63` 的 cfx63 段；16 MiB 不变；QEMU 机器映射 + `tests/scripts/dadao.lds`/`codegen_crt0.s`/异常向量 + harness + `check-interface` 断言 + `spec/Machine-01` 与锁同步（`INTEG-033k §裁定汇总 #10`）。
2. **NaN 传播规则参照宿主机**（`QEMU-058t`）——`float_2nan_prop_ab`（宿主机 SSE 实测）；`ISS-195` 收口，picolibc 全量 test blocked 归零（`milestones.md` 流水行 + `components/qemu/changelog.md`）。

## 核验内容（可执行步骤）
1. **L2 + 按需全量**：跑 `make check-modules`（L2，含 `check-qemu-smoke` 语义代表集）；按需跑 qemu 全量（`check-qemu-semantics`）——均留真实退出码。
2. **逐条核 M7 口径**（以**真实命令输出 + 退出码**为证，**禁**抽样推断 / 转述）：
   - 口径 1：`grep` 复核 RAM 基址为 `0xFC00_0000_0000`（QEMU 机器映射 + `dadao.lds` + `spec/Machine-01` + 锁一致）；`make check-interface` rc=0（断言派生自单一真源、非写死）；
   - 口径 2：`float_2nan_prop_rule` 现场复核为 `float_2nan_prop_ab`；`make check-picolibc-tests-full` 全量 rc=0 且 `fail 0 / blocked 0`（现场统计；四分类见 `TESTCASES-043m`）。
3. **跨模块影响**：本模块交付物（`components/qemu/patches/**` + 地址段口径）受 `spec`（`Machine-01` RAM 口径 + 只读锁）、`infra`（构建）、`testcases`（blocked 溯源）牵动——逐个核对是否未处置；点名 `ISS-198`（2-NaN payload 选择无任何测试覆盖，`qemu`+`testcases`）、`ISS-054`/`058`/`064`/`090`/`098`/`120`（挂账）。**若存在未处置项 ⇒ 本 `m` 不得置里程碑**（`AGENTS.md`「模块里程碑与跨模块交互」）。
4. **M7 范围内 issue 处置**：对 `scope` 含 `qemu` 的 M7 期 issue 逐条给动作（关闭 / 转遗留 / 指明编号）——至少含 `ISS-195`（M7 收口，复核后关闭）、`ISS-198`（转遗留，缺独立 oracle）；**`open` 者不得擅自 close**（须依据或用户裁定，`Process-04 §3`）。
5. **门控**：`make check`（L1）rc=0 + `make check-no-residue` rc=0 + issue 台账校验（`check_issues`）rc=0。

## 验收标准
1. **逐条核验表**：每条 M7 口径 → 证据（命令 + 真实输出 + 退出码）→ 结论（达成 / 未达成 + 理由）。
2. **关联任务态核**：`QEMU-056t`/`058t` 是否均 `已验证`；各任务产出文件（`components/qemu/patches/**`、`tests/scripts/*`、`spec/Machine-01`）是否存在（现场核）。
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
- 立本 `m` 核验任务书（M7 qemu 模块里程碑）；M7 口径 2 条逐条引用 `milestones.md` M7 段落 + `INTEG-033k §裁定汇总 #10`；含跨模块影响（点 `ISS-198` + 挂账）与「有未处置 ⇒ 不得置里程碑」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`qemu` 现场最大 `QEMU-058t` ⇒ 本 `m` = `QEMU-059m`（模块内跨后缀递增）。
