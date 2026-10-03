# INFRA-026t: 文档分层改造 — 组件补丁流程（E1–E8）与 ADR 规则修订（T3）

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：`SPEC-084t`（`spec/Process-01-组件补丁组织与构建编排.md`、`spec/Process-03-ADR编写规范.md` 就位）；按用户裁定串行于 `SPEC-085t` 之后（非能力依赖，仅为避免并发改共享文件）。
**状态**：待开始

> 本任务是「文档分层改造」的 **T3**。T1 = `SPEC-084t`（已完成），T2 = `SPEC-085t`。
> **本任务书为 T1/T2 完成前的完整草案**；T1 落盘后须复核 `spec/Process-01-*.md`/`spec/Process-03-*.md` 是否就位；若实际路径/内容与草案不符，**先报告再调整**，不得自行改契约。

## 执行环境
**执行环境**：本地

## 一、已定决策（真源，逐条已经用户确认；不得增删、不得重新决策）

### 决策 6：ADR 规则修订（落 `spec/Process-03-ADR编写规范.md`）
- **判据删除「不可逆」**（现有判据 1「不可逆 / 高代价」→ 去掉「不可逆」，保留「高代价」等其余判据；须同步 `AGENTS.md` 中提及判据处，见下）。
- **明确 ADR 不承载规范正文**：规范正文归 `spec/` 与 `contract-*`；ADR 只记**决策、理由、被否方案、指向规范章节**。
- 判据与格式的其余部分不变（落点/命名/模板/流程/提醒义务）。

### E1–E8：`spec/Process-01` 的组件补丁流程正文（用户逐条确认，原样落入）
- **E1 不变量**：`.work/source/<component>` 任何时刻须满足 **worktree 干净**（`git status --porcelain` 空）且 **HEAD = 上游 base + 恰好 1 个 commit**。
- **E2 任务起点**：动组件**前**须先把既有改动提交/收敛成"base+1 且干净"；**不干净不得开始新改动**。
- **E3 导出**：起点干净 ⇒ `git diff <base>` 精确定位并导出修改/新增文件；**导出前必须校验 E1**，不满足**拒绝导出**；**§6.3 的 `git add -N` 技巧作废**。
- **E4 收敛**：需要时 `git reset --soft HEAD~` → `git add -A` → `git commit`，把多次改动**收敛为 1 个** commit（维持 base+1）。
- **E5 应用侧**：`make prepare`/`apply-series` 应用完补丁集后**自动 `git add -A` + `git commit`**（**不固定 author/committer 日期**——用户明确「不要引入不必要的流程；生成 working tree 与重生成 patch 都不需要这些元数据」；**不设 local `user.name/email`**，用环境既有；commit message 固定简短 **`dadao: <component> patch series`**）；**重复应用幂等**（不产生第 2 个 commit）；**现行"HEAD 必须 == base 否则拒绝"须放宽为「HEAD ∈ {base, base+1 且该 commit 内容 == patches}」**。
- **E6 机械断言**（`check-patch-tree` **追加 ⑦⑧⑨**，不重排现有 ①–⑥）：⑦ worktree 干净；⑧ HEAD = base + **恰好 1** commit；⑨ 该 commit 的 `git diff <base>` 与 `patches/` 内容一致。
- **E7 模块自检**：修改该组件的模块，**改动前/改动后各查一次** E1；不干净 ⇒ **先排查自身**，不得带脏树继续；查法**并入 `check_patch_tree.py`**，暴露 **`--source-state`**（复用断言 ⑦⑧ 逻辑）。
- **E8 与旧文关系**：§6.1「不必 commit／不保留作者与提交信息」**改写**为提交式流程；**澄清**：补丁**仍**是裸 `git diff`（不含作者/提交信息），**本地 commit 只用于维持干净工作树、永不推送上游**。

## 二、接口规范

### 输入
- `spec/Process-01-组件补丁组织与构建编排.md`（T1 产出，含 §6/§7/§8）
- `spec/Process-03-ADR编写规范.md`（T1 产出）
- `tools/infra/make_patch.py`、`tools/infra/apply_series.py`、`tools/infra/check_patch_tree.py`
- `manifests/components.lock.toml`、`.work/source/{llvm-project,qemu}`（已有工作树）
- `AGENTS.md`（ADR 判据提及处 L33：`不可逆、跨模块、多方案、外部契约、结论固化、定位`）
- `Makefile`（`check-patch-tree`、`prepare`/`apply-series` 目标）
- 已验收参考：`INFRA-023t`（补丁生成/应用幂等与内容断言）、`INTEG-005t`（同类修复）任务书（只读借鉴，不改）

### 输出
1. `spec/Process-01-组件补丁组织与构建编排.md`：§6/§7/§8 **改写**以容纳 E1–E8（含 E5 幂等与 HEAD 集合、E6 新断言、E8 澄清）；§6.3 `git add -N` 作废。
2. `tools/infra/apply_series.py`：E5（应用后自动 `git add -A` + `git commit`、不固定日期、幂等、HEAD 检查放宽）。
3. `tools/infra/check_patch_tree.py`：E6（新增三条断言：worktree 干净 / HEAD=base+恰好1 / HEAD 的 `git diff <base>` == `patches/` 内容）。
4. `tools/infra/make_patch.py`：E3（导出前校验 E1，不满足拒绝导出；移除 `git add -N` 依赖——**若** E1 成立则 `git diff <base>` 已含新增文件）。
5. **E7 复用自检**（**用户裁定：并入 `check_patch_tree.py`**）：在 `check_patch_tree.py` 暴露 **`--source-state`** 子模式（复用断言 ①「worktree 干净 + HEAD=base+恰好1」的判定逻辑），供模块改动前/后调用；不为 E7 新建独立脚本。
6. `spec/Process-03-ADR编写规范.md`：判据修订（去「不可逆」；ADR 不承载规范正文）。
7. `AGENTS.md`：同步 ADR 判据列表（L33）与相关表述（去「不可逆」；补「ADR 不承载规范正文」）。
8. `Makefile`（如新增 `check-source-state` 目标则同步；`prepare`/`apply-series` 注释）。

### 约束
- 全程中文；**不提交 git**；只动任务书范围，越界须披露。
- **不得改 `adr-*` 正文**；不得改已验收历史任务书；不得改 `spec/SimRISC-*`/`spec/SimRISC-0.5.3/`。
- **不得引入不必要的流程**（用户明确）：不固定 author/committer 日期；仅最小改动。
- 临时产物 `/tmp/opencode/INFRA-026t/`；日志留 `.work/log/infra/`。
- **不得在全核并行**下跑构建；本任务以 Python/文本为主，若需重建（预期**不需要**）须 `JOBS=8` 并申报。
- 遵循 `AGENTS.md`「子代理硬约束」「验证脚本反例门控」。

## 三、实施步骤

### 0. 预检与基线（记录，不修改）
- `git status --porcelain` 干净。
- 复核 T1 产出：`test -f spec/Process-01-组件补丁组织与构建编排.md && test -f spec/Process-03-ADR编写规范.md`。
- **记录当前 `.work/source` 状态**（`git -C .work/source/<c> rev-parse HEAD` 与 `status --porcelain`）作为**基线**：
  - 实测（2026-10-03）两工作树 HEAD = 上游 base、工作树脏（补丁未提交）——**不满足 E1**；这是**改造前**的正常基线，E5 落地后由 `make apply-series` 建立 E1。
- 基线门控：`make check-patch-tree`、`python3 -m compileall -q tools`（捕获 `rc`）。

### 1. `Process-01` 正文改写（§6/§7/§8 + E8）
- **§6 生成流程**：
  - §6.1 改写为「**提交式流程**」（E8）：改组件源码在 working tree 进行；**E1 不变量**（干净 + HEAD=base+1）；补丁仍是**裸 `git diff`**（不含作者/提交信息）；本地 commit 仅用于维持干净工作树、**永不推送上游**。
  - §6.2 幂等保留。
  - §6.3 改写（E3）：起点干净 ⇒ `git diff <base>` 精确定位导出；**导出前校验 E1，不满足拒绝导出**；**明确废止**原 `git add -N` 技巧（含 2026-10-03 `LLVM-026t` 补注段落——须改写/移除与新流程冲突的部分）。
  - 新增 **E2 任务起点** 与 **E4 收敛**（`reset --soft HEAD~` → `add -A` → `commit`）。
- **§7 应用流程**（E5）：应用后 `git add -A` + `git commit`（不固定日期）；重复应用幂等（不产生第 2 个 commit，可用「commit 内容 == patches」判定跳过）；HEAD 检查放宽为 `HEAD ∈ {base, base+1 且该 commit 内容 == patches}`。
- **§8 机器检查**：**追加 ⑦⑧⑨**（⑦ worktree 干净 / ⑧ HEAD=base+恰好1 / ⑨ HEAD 的 `git diff <base>` == patches 内容；**不重排现有 ①–⑥**），并同步表格与说明；新增 **E7 自检**入口 `--source-state`。
- **新增 E7 自检**小节：模块改动前/后各查一次 E1；不干净先排查自身；给出可复用命令/脚本。
- 版本/变更记录（§12）追加一条本任务（rev. 2026-10-03）。

### 2. `apply_series.py`（E5）
- 应用完成后：`git add -A` + `git commit -m "dadao: <component> patch series"`（`<component>` 为组件名，如 `dadao: qemu patch series`）。
- **不设** local `user.name`/`user.email`（用环境/仓库既有身份）；**不设** `GIT_AUTHOR_DATE`/`GIT_COMMITTER_DATE`（用户明确「不要引入不必要的流程」）。
- **幂等**：若 HEAD 已是 base+1 且其内容 == patches（无工作树改动、`git diff --stat <base>` 与当前一致），则**不再产生 commit**（跳过）。
- **HEAD 前置检查放宽**：接受 `HEAD == base`（未应用）或 `HEAD == base+1 且该 commit 内容 == patches`（已应用）；其余拒绝。
- 保留逐补丁 `git apply --check --reverse` 幂等逻辑（先判已应用则跳过）。
- 边界：空 series、组件未启用等既有分支不变。

### 3. `check_patch_tree.py`（E6 + E7）
- **E6：追加三条断言 ⑦⑧⑨（用户裁定：追加编号，不重排现有 ①–⑥）**：
  1. **⑦ worktree 干净**：`.work/source/<name>` 的 `git status --porcelain` 为空；
  2. **⑧ HEAD = base + 恰好 1 commit**：`git rev-list --count <base>..HEAD == 1`；
  3. **⑨ 该 commit 的 `git diff <base>` 与 `patches/` 内容一致**：commit 的 net diff（按路径归一化 `index` 行后）与补丁集逐路径一致。
- **E7：暴露 `--source-state`**（复用断言 ⑦⑧ 的判定逻辑），作为模块改动前/后可调用的自检入口；输出清晰的 PASS/FAIL 与真实状态（HEAD、count、porcelain 摘要）。复用断言逻辑，**不重复实现**。
- 若 `.work/source/<name>` 缺失：沿用既有「跳过 apply 检查」的通知语义；断言 ⑦–⑨ 亦随之**明确打印跳过**（不得静默）。
- 同步 `Process-01 §8` 表格与 docstring（现 docstring 写「6 条断言」→ 更新为 9 条；说明 ⑨ 与既有断言 ⑥ 的分工：⑥＝补丁应用产物 vs 工作树，⑨＝HEAD commit vs 补丁集）。

### 4. `make_patch.py`（E3）
- 导出前**校验 E1**（worktree 干净 + `git rev-list --count <base>..HEAD == 1`）；不满足**拒绝导出**（非零退出，打印原因）。
- 因 E1 成立时改动已 commit，`git diff <base>` 天然包含新增文件，**移除/停用** `changed_paths()` 的 `git add -A -N` 依赖（或保留但不作为新增文件可见性的唯一手段——须与 E3「技巧作废」一致）。
- 既有 `merge-base --is-ancestor` 检查与幂等导出（§6.2）保留。

### 5. `Process-03` 与 `AGENTS.md`（决策 6）
- `spec/Process-03-ADR编写规范.md`：
  - 「何时写 ADR」判据 1 去「不可逆」（保留「高代价」等）；判据列表其余不变；
  - 新增明确表述：**ADR 不承载规范正文**——规范正文归 `spec/` 与 `contract-*`；ADR 只记**决策/理由/被否方案/指向规范章节**；
  - 「典型场景」「不写 ADR」段落据实微调以自洽。
- `AGENTS.md` L33 判据列表同步去「不可逆」；如必要，在同段补「ADR 不承载规范正文」。**不得**改动 AGENTS.md 其它无关段落。

## 四、验收标准

1. **正文落位**：`grep -nE "worktree 干净|恰好 1 个 commit|拒绝导出|reset --soft|幂等|永不推送|⑦|⑧|⑨|source-state" spec/Process-01-组件补丁组织与构建编排.md` 命中 E1–E8 要点；`grep -n "git add -N" spec/Process-01-*` **零命中**（或明确标注「作废」）。
2. **ADR 判据**：`grep -n "不可逆" spec/Process-03-ADR编写规范.md AGENTS.md` **零命中**；`grep -nE "不承载规范正文|规范正文" spec/Process-03-ADR编写规范.md` 命中。
3. **工具改造**：`python3 -m compileall -q tools` exit 0。
4. **E5 幂等（真实执行）**：
   - `make apply-series`（或 `python3 tools/infra/apply_series.py`）首次运行后 `.work/source/<c>` 满足 E1（干净 + HEAD=base+1）；给出 `git rev-parse HEAD`、`rev-list --count <base>..HEAD`、`status --porcelain` 的真实输出。
   - **commit 元数据**：`git log -1 --format='%s|%an|%ae'` 的 subject == **`dadao: <component> patch series`**；确认**未**设置 local `user.name/user.email`（`git config --local --get user.name` 为空/未设置）。
   - **再跑一次**同一命令：**不新增 commit**（count 仍为 1、HEAD 不变）；给出两次运行前后 HEAD/count 对比。
5. **E6 断言可失败（⑦⑧⑨，反例门控，须真实注入并还原）**：
   - 在临时工作树（**优先** `/tmp/opencode/INFRA-026t/` 复制或独立 fixture git 仓库）或受控注入下，分别制造三种缺陷，确认 `check_patch_tree.py` **FAIL（非零）**：
     a) 工作树加一个未提交改动 → 断言 **⑦「worktree 干净」** FAIL；
     b) 再追加一个 commit（HEAD=base+2）→ 断言 **⑧「恰好 1」** FAIL；
     c) 篡改某补丁内容（与 HEAD diff 不一致）→ 断言 **⑨「diff == patches」** FAIL。
   - **还原**：注入必须可复原；对**真实** `.work/source` 的注入须确认还原且**包含重建**（本任务改的是 Python，不需重建二进制；但若注入了 commit，须 `git reset --hard <原 HEAD>` 并核对 `status` 干净、count 恢复）。给出 `git diff --name-only` 先非空后无残留的证据。
   - 若在独立 fixture 中完成，**须在完成区说明**并给出该 fixture 的创建命令与真实输出。
6. **`--source-state`（E7）**：`python3 tools/infra/check_patch_tree.py --source-state`（E1 成立时）exit 0 并打印 HEAD/count/干净状态；对 a)/b) 两种注入分别 exit 非零（复用 ⑦⑧ 逻辑，不得另写一套）。
7. **`make check-patch-tree` 通过**：在 E1 成立的工作树上 exit 0（若工作树缺失则明确打印跳过并说明）。
8. **修复须「修一类」**：如发现同类缺陷（如某断言恒真、退出码未传播），**全文件排查**，不得只改被点名的一条。
9. **留证**：所有复杂命令按 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"` 捕获退出码，日志留 `.work/log/infra/INFRA-026t-*.log`。
10. **自包含**：不依赖外部仓库。

## 五、下发前四项预检（主会话下发时须逐条给结论；T1/T2 完成后复核）

1. **任务书内部一致性**：✅ E1–E8、决策 6 与验收 1–10 一致（E6＝断言 ⑦⑧⑨；E7＝`--source-state`；E5 message 固定）；已澄清「改造前 `.work/source` 不满足 E1 属正常基线，E5 落地后建立」。无自相矛盾。
2. **依赖链实际可用性**：依赖 `SPEC-084t`（Process-01/03 就位）；`.work/source/{llvm-project,qemu}` **已存在**且可 `git` 操作（已核实）。**T1 完成后**复核 Process-01/03 at new path。当前（T1 前）Process-0x 为旧路径 → **该依赖就绪度 BLOCKED**。
3. **验收可执行性**：
   - 「现在可跑」：`compileall`、grep 门控、`apply_series`/`check_patch_tree` 的 Python 执行、fixture 反例注入（纯 git/Python，无需重建）。
   - 「T1 后跑」：Process-01/03 grep。
   - **BLOCKED 项**：`make check` 全量（需 `check-lit`/`check-qemu-semantics` 构建产物）。**替代证据**：`make check-patch-tree` + `compileall` + fixture 反例。
   - **重建预期**：**不需要**（不改组件源码补丁；仅改 Python 工具与文档）。
4. **与 spec/vectors 一致**：本任务不改编码/期望值；E5/E6 涉及 `.work/source` 的 git 状态，与 `contracts/`、`tests/vectors/` 无交集。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）

## 收尾与提交（用户裁定，2026-10-03）
- **执行期不提交**：engineer/reviewer 子代理**不得** `git commit`/`git add`（注：E5 的自动提交是**被测工具**对 `.work/source/<component>` 的行为，**不是**对 DADAO-v5 主仓库的提交，二者严格区分）。
- **收尾后各提交一次**：本任务经 `/complete`（reviewer 验收 + 架构师交叉复核 + 知识沉淀）通过、`**状态**` 置为 `已验证` 后，**主会话**为该任务（DADAO-v5 主仓库）做**一次独立提交**；**每任务完成、验收通过后各做一次提交**，不积压、不批量；**未收尾不得提交**。
- 提交前满足项目 `AGENTS.md`「任务收尾」的收尾检查。

## 决策裁定记录（用户 2026-10-03 裁定，已并入本任务书）
- **原开放问题 #3（E5 commit）**：裁定 **不设** local `user.name/email`（用环境既有）；message 固定 `dadao: <component> patch series`。
- **原开放问题 #4（E6 编号）**：裁定 **追加 ⑦⑧⑨**，不重排 ①–⑥。
- **原开放问题 #5（E7 落点）**：裁定 **并入 `check_patch_tree.py`**，暴露 `--source-state`（复用断言 ⑦⑧ 逻辑）。
- 本任务**无待确认事项**。
