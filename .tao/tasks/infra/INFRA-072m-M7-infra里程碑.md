# INFRA-072m: M7 infra 模块里程碑核验

**模块**：infra
**项目里程碑**：M7
**依赖**：`INFRA-055t`/`056t`/`057t`/`058t`/`060t`/`061t`/`062t`/`063t`/`064t`/`065t`/`066t`/`067t`/`068t`/`069t`/`070t`（均 `已验证`）；`INFRA-071t`（`待开始`，依赖用户授权）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 目的
核验 **infra 模块 M7 目标**是否达成。**本模块 M7 口径（逐条；来源 = `milestones.md`「当前进度」M7 段落 + `INTEG-033k §任务分解`，逐条引用）**：

1. **picolibc 组件接入 + clang++ 接入**（`INFRA-055t`/`056t`）与 **picolibc 移植/构建集成**（`INFRA-057t`）——`components/picolibc/**` 补丁集 + `Makefile` 编库/落安装点；printf E2E 通过（`INTEG-033k §任务分解` `INFRA-056t`/`057t` 行）。
2. **门控分层 L1/L2/L3 + `check-spec-refs` 收口**（`INFRA-058t`）——`make check` 收缩为 L1（`check-qemu-semantics`/`check-lit`/`check-interface` 移出）、新增 `check-modules`（L2）/`check-full`（L3）/`check-qemu-smoke`；`.work/log/` 四分类判据入 `AGENTS.md` + 门控 `check-knowledge-refs`；**分层明细落 `docs/Process-07`**（`milestones.md §规划中`「门控分层」+ `INTEG-033k §收口核对 #1/#2`）。
3. **目录三分界 + 规范版本号**（`INFRA-060t`；`milestones.md §规划中`「目录三分界与规范版本号（用户 2026-10-11 裁定）」）。
4. **台账/文档减重**（`INFRA-061t`/`062t`/`063t`/`064t`）——changelog 并入 milestones、MEMORY 纯指针页、规则/台账分工、入口文档分工（`milestones.md` 流水行）。
5. **子代理 workdir 作用域 + 权限 fail-fast**（`INFRA-065t`）——规则层已落地；权限层（agent frontmatter `external_directory` deny）**待服务重启复验**（`ISS-199`；`milestones.md §规划中`「`INFRA-065t` 待复验」）。
6. **picolibc 运行时补齐（支撑 test 解锁）**——`libm` 恢复（`INFRA-066t`）、`__muldc3`/`__mulsc3`（`INFRA-067t`）、`setjmp`/`longjmp` 真实现（`INFRA-068t`）（`milestones.md` 流水行）。
7. **LLVM 组件 changelog 补齐 + 三检查并入 L1**（`INFRA-069t`：`check-isa-coverage`/`check-spec-numbering`/`check-spec-changelog`；`milestones.md §规划中` 两条已收口）。
8. **`.tao/knowledge/` 顶层收拢 + `docs/Process-07`**（`INFRA-070t`）。

## 核验内容（可执行步骤）
1. **L2 + 按需全量**：跑 `make check-modules`（L2 模块代表集）；按需跑 infra 相关全量（`check-components`/`check-patch-tree`/`check-knowledge-*`/`check-dirs` 等）——均留真实退出码。
2. **逐条核 M7 口径**（以**真实命令输出 + 退出码**为证，**禁**抽样推断 / 转述）：
   - 口径 1：`make test-picolibc-smoke`（printf E2E）真实通过；
   - 口径 2：`make check` = L1 且 `check-modules`/`check-full` 存在（`Makefile` 目标行）+ `docs/Process-07` 文件存在 + `check-knowledge-refs` 在 L1；
   - 口径 6：`nm` 复核 sysroot `libc.a` 符号（`floor`…`fmax`、`__muldc3`/`__mulsc3`、`setjmp`/`longjmp`）**全命中**（现场统计）；
   - 其余口径：核对对应任务产出文件存在 + 门控承载。
3. **跨模块影响**：本模块交付物（`Makefile`/`manifests/`/`components/**` 构建与门控）被 `llvm`/`qemu`/`spec`/`testcases` 补丁与向量变更牵动——**逐个核对是否未处置**；点名 `ISS-199`（权限 fail-fast 待用户复验）、`ISS-202`（`contract-*.md`→`contracts/` 待授权，跨 `spec` 只读锁册）、`ISS-200`（pre-M6 changelog 缺条目，`infra`+`llvm`）。**若存在未处置项 ⇒ 本 `m` 不得置里程碑**（`AGENTS.md`「模块里程碑与跨模块交互」）。
4. **M7 范围内 issue 处置**：对 `scope` 含 `infra` 的 M7 期 issue 逐条给动作（关闭 / 转遗留 / 指明编号）——至少含 `ISS-191`、`ISS-193`（infra 侧运行时/`sbrk` 面）、`ISS-196`（复核已 closed）、`ISS-199`/`ISS-200`/`ISS-202`；**`open` 者不得擅自 close**（须依据或用户裁定，`Process-04 §3`）。
5. **门控**：`make check`（L1）rc=0 + `make check-no-residue` rc=0 + issue 台账校验（`check_issues`，经 `make check` 承载）rc=0。

## 验收标准
1. **逐条核验表**：每条 M7 口径 → 证据（命令 + 真实输出 + 退出码）→ 结论（达成 / 未达成 + 理由）。
2. **关联任务态核**：上列各 `t` 是否均 `已验证`；各任务产出文件是否存在（现场核）。
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
- 立本 `m` 核验任务书（M7 infra 模块里程碑）；M7 口径 8 条逐条引用 `milestones.md` M7 段落 + `INTEG-033k §任务分解`；含跨模块影响（点 `ISS-199`/`202`/`200`）与「有未处置 ⇒ 不得置里程碑」纪律；执行方式 = reviewer 独立核验 + architect 记录/提交。
- **编号依据**：`infra` 现场最大 `INFRA-071t` ⇒ 本 `m` = `INFRA-072m`（模块内跨后缀递增）。
