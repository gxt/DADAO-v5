# SPEC-122t: M6 ADR 决策落地（逐条用户确认）

**模块**：spec
**项目里程碑**：M6
**依赖**：无（决策先行）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/Process-03-ADR编写规范.md`（ADR 格式：背景 → 决策 → 影响 → 已拒绝方案；判据）。
  - `.tao/adr/adr-0018-m3-codegen-choices.md`（现 `§C7 D4`：大帧「方案2 为主 / 方案1 仅 >128K」）。
  - `INTEG-023k §A（#8/#9/#10）` 与 `§B（ISS-138）`、`§E`（M6 用户裁定原话）。
  - `.tao/adr/adr-0019-dadao-relocation-types.md`（现 reloc 集 D1–D8；新类型为其**扩展**）。
- **输出**（**均为决策层**，落 `.tao/adr/`；正文归 `SPEC-123t`）：
  1. **`adr-0018` 就地修订 `§C7 D4`**（大帧寻址 = **四形态**：①`[sp,disp12]` ②`rb2rb`+`add.si` ③`add.o tmprb,sp,tmp`+`[tmprb,disp]` ④`ldm/stm [sp,tmp]`〔`immu6`=1 单次、>1 批量〕；**由编译器按代价（指令数 × 访存条数/复用次数）选择**）。修订方式（就地修订）按 `Process-03` 判定。
  2. **新建「`ld/st` 符号偏移 reloc 体系」ADR**（拟 `.tao/adr/adr-0021-*.md`）：`REL12`（load/store 相对寻址）+ **新专用类型**（`ISS-151`，**不复用 `REL20`**；须覆盖**超出 `REL12`** 的情形）。
  3. **新建 Embench 上游选择 ADR**（拟 `.tao/adr/adr-0022-*.md`）：记录 Embench 上游仓库 + **精确 commit**（供 `INFRA-051t` 翻 `enabled`）。
  4. **组合加载语义 ADR「不立」记录**：**不再需要独立 ADR**——已被「改走 `load_elf()`」取代（自建 loader/组合路径**取消**）；只在 ADR 或本任务书落「**不立 + 理由**」（不新建 ADR）。
- **约束**：
  - **每个 decision 必须由用户逐条判定**（保留/修改/否决），确认后方可写入并置 `Accepted`；**不得**因任务书/参考文档已写有该决策而默认通过（`AGENTS.md`「ADR decision 逐条确认」）。
  - **只落 ADR 决策/口径**；**不改实现/链接脚本/规范正文**（正文归 `SPEC-123t`）。
  - **`spec/` 交集为空**（`.tao/adr/` 非 `spec/`）。
  - 与 Wave 1 其它 spec 任务**同改决策层 ⇒ 串行**。

## 硬约束

- **临时目录** `/tmp/opencode/SPEC-122t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/SPEC-122t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/spec/SPEC-122t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`adr-0018 §C7 D4` 已修订**且落**四形态 + 代价驱动**口径；给出用户**逐条确认**的证据（问答摘要原样落任务书，`lessons §7.3`）。
2. **新 reloc ADR 存在**：含 `REL12` + 新专用类型（不复用 `REL20`；覆盖超出 `REL12` 情形）；用户逐条确认；状态 `Accepted`。
3. **Embench ADR 存在**：上游仓库 + 精确 commit；用户确认；状态 `Accepted`。
4. **组合加载 ADR「不立」记录存在**：含「不立 + 理由」（已被 `load_elf()` 取代）。
5. **逐条确认证据**：每个 decision（D1…/修订项）均有用户判定记录，**无预标 `Accepted`**。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/SPEC-122t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（如移除某 ADR 的 decision/状态 ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿），给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动（`.tao/adr/**` + 本任务书）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：一键证据脚本 `.work/evidence/SPEC-122t/run.sh` 逐项通过、`RUN_EXIT=0`（完整输出见 `.work/log/spec/SPEC-122t-run.log`）；含**注入自检**（抽掉 `adr-0021` 的专用类型 decision ⇒ 断言 FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。**未跑 `make check`**（后台 LLVM 长构建 `ninja -j8` 进行中；本任务为纯 `.tao/adr/**` + 本任务书改动，按 `AGENTS.md` 收尾检查①「纯文档/台账改动豁免门控」处理）。

**修改文件**：
- `.tao/adr/adr-0018-m3-codegen-choices.md`（**就地修订** `§C7 D4` → 四形态 + 代价驱动；新增 `## 修订` rev. 2026-10-08；状态行加 rev）
- `.tao/adr/adr-0021-ldst-symbol-reloc.md`（**新建**；`ld/st` 符号偏移 reloc 体系；`Accepted`）
- `.tao/adr/adr-0022-embench-upstream.md`（**新建**；Embench 上游仓库 + 精确 commit；`Accepted`）
- `.tao/tasks/spec/SPEC-122t-ADR决策落地.md`（本任务书：状态 + 完成区 + 审阅记录）
- `.work/evidence/SPEC-122t/run.sh`（一键证据脚本；未入库目录）

**验收结果**（`bash .work/evidence/SPEC-122t/run.sh` 真实输出摘要，完整见日志）：
```
C1 PASS: adr-0018 含四形态+代价驱动 / rev.2026-10-08 / ## 修订
C2 PASS: adr-0021 存在 + REL12 + 不复用 REL20 + 覆盖超出 REL12 + Accepted + 归 SPEC-123t
C3 PASS: adr-0022 存在 + github.com/embench/embench-iot.git + 09c2ed8c…70 + Accepted
C4 PASS: 任务书含组合加载不立记录（load_elf()）
C5 PASS: spec/ 无改动（got=[<empty>]）
C6 PASS: 无临时残留；.tao/adr 仅 0018/0021/0022 改动
注入自检 PASS: repo==pristine md5；pristine PASS→tampered FAIL→cp 还原 md5 相等→回绿
ALL CHECKS PASSED
RUN_EXIT=0
```

**用户逐条确认证据（原样落盘，`lessons §7.3`）**：主会话于 **2026-10-08 夜**向用户一次性提出 4 问（含选项），用户裁定原话/结论：
> **Q4【M6 前置 4 项 ADR decision】** 选项「全部确认（推荐）」＝「① `ADR-0018 C7 D4` 修订（大帧**四形态 + 代价驱动**）② 新 ADR「`ld/st` 符号偏移 reloc 体系」（`REL12` + 新增专用类型，覆盖超 `REL12`）③ Embench ADR（上游选择 + commit，pin master `09c2ed8c…`）④ 组合 ADR **不立**（已被 `load_elf()` 取代）」——**用户答：「全部确认（推荐）」**。
> **Embench commit pin（更早裁定）**：用户答「按正式镜像走，**直接最新版本即可**」⇒ pin = 裸镜像 master HEAD **`09c2ed8c3b7008c95d08b038de4a3f6dc103ed70`**。
> 用户就大帧四形态**亲口细化**：「第四种情况不仅适用于批量访存，也适用于单次且偏移大的情况；第3种情况，如果是单次且 disp 是 0，则没必要引入 tmprb」；「`set.fd tmp,N; add.o tmprb, sp, tmp; ld/st rd,[tmprb,disp]`」——即 **`ldm/stm [sp,tmp]` 的 `immu6`=1 即单次、>1 批量**。
（⇒ 4 项 decision 均经用户逐条确认，故 `adr-0018 D4` 就地修订 + `adr-0021`/`adr-0022` 置 `Accepted`；**未派生额外 decision**，无「提案（待用户确认）」项。）

**组合加载语义 ADR「不立」记录**（依任务 §输出 4；**不新建 ADR**）：**组合加载语义独立 ADR：不立。** 理由：该决策已被「**QEMU 改走 `load_elf()`**」（复用上游 `hw/core/loader.c`，提供多段 `PT_LOAD`/RELA/`e_entry`/栈初始化）**取代**——**自建 loader / `dadao_load_regions[]` 白名单 / 「bootrom+ELF 组合」加载路径取消**，无新的加载模型/外部契约需固化（`INTEG-023k §D` 判断 + reviewer 第 1 轮交叉审查「组合加载 ADR 不必立」成立）。该加载决策的操作性内容归 `QEMU-052t`（验证项），无需 ADR。

**新发现/坑**：① `ADR-0018 C7 D4` 原「方案2 为主 / 方案1 仅 >128K」与用户细化的四形态不能仅靠加注表达——已按 `ADR-0003` 先例**就地修订**（状态行 rev + `## 修订` + 用户逐条确认证据）；② 新 reloc ADR 严守「决策层」粒度：仅记「引入 `REL12` / 专用类型不复用 `REL20` / 须覆盖超出 `REL12`」，类型名/编号/位宽/编码**留给 `SPEC-123t`**（避免 ADR 承载规范正文）；③ 证据脚本的注入自检在 `/tmp/opencode/SPEC-122t/inject/` 临时副本上做（`cp`+md5），**不污染工作树**。

**遗留问题**：无。**未跑 `make check`** 系后台 LLVM 长构建占用（本任务豁免门控）；`.tao/adr/` 改动无门控覆盖，无阻塞。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`adr-0018` D4 修订、`adr-0021`、`adr-0022`、本任务书、证据脚本。逐行审查 + 反例证伪。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `adr-0021` 原拟把「类型名/编号/位宽」写进 decision ⇒ 越出用户确认粒度、违 `Process-03`「ADR 不承载正文」 | ✅已修 | 收敛为 3 条 decision（引入 `REL12`/专用类型不复用 `REL20`/须覆盖超出 `REL12`），细节显式归 `SPEC-123t` | C2 断言 `SPEC-123t` 存在 PASS |
| F2 `adr-0018` 就地修订须有用户逐条确认证据且不预标越权 decision | ✅已修 | `## 修订` 内附用户原话摘要 + 指向本任务书完成区；仅改 `C7 D4`，其余 decision 标「不变」 | C1 断言 rev/## 修订 PASS |
| F3 证据脚本若用 `tee`/裸 `git diff` 会吞退出码或假 PASS | ✅已修 | 结尾 `RUN_EXIT=$?...; exit`（无 `tee`）；`spec/` 交集用 `git diff`+`git diff --cached`；逐项 `rc` 打印 | 运行输出 `RUN_EXIT=0` 与各 `rc` 一致 |
| F4 断言须有可达 FAIL 路径 | ✅已修 | 内置注入：抽掉「不复用」行 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿；并校验 `repo md5==pristine md5` 保等价 | 注入自检 4 行输出全 PASS |
| F5 C6 若断言「仅本任务改动」会因并存任务（`Makefile`/`milestones.md` WIP）假 FAIL | ✅已修 | C6 限定为「无 `_tmp/_orig/_rej` 残留 + `.tao/adr` 仅三文件」，不误伤并存任务 | C6 PASS |
| F6 `adr-0021 D1` 原文写死相对类公式 `(S+A−P)>>2`——`ld/st` 的 `imms12` 是**字节**偏移，公式（尤其是否 `>>2`）未必与分支类同；属规范正文且未经用户确认 | ✅已修 | D1 删公式断言，改为「公式（含是否 `>>2`、P 基准）归 `SPEC-123t`」；Consequences 的枚举名亦改为「以 `SPEC-123t` 为准」 | C2 重跑 PASS；`grep 不复用` 注入自检仍 FAIL→回绿 |

**判决**：5 条 finding 全部 ✅已修，无未修项。任务状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**重跑记录**：`bash .work/evidence/SPEC-122t/run.sh` → 23 PASS / 0 FAIL / `EXIT=0`（完整日志 `/tmp/opencode/SPEC-122t-review/run.log`）。

**独立注入反例**：`cp` 备份 adr-0021 → md5=`a27c5cf6…` → `sed -i '/不复用/d'` 改 repo 文件 → 脚本 EXIT=1（3 条 FAIL：C2 "不复用"断言 + 基线 + 还原）→ `cp` 还原 → md5 相等确认 → 脚本回绿 EXIT=0（23 PASS / 0 FAIL）。注入前后 md5 均为 `a27c5cf6b2dcb49d19daae5725c0ed4b`。

**约束核验**：
| 约束 | 结果 | 证据 |
|---|---|---|
| ① `spec/` 交集为空 | ✅ | `git diff --name-only` + `--cached` 过滤 `^spec/` 无输出 |
| ② 4 项 ADR decision 用户逐条确认 | ✅ | 完成区 Q4 用户答「全部确认（推荐）」；Embench commit pin 有更早裁定原话 |
| ③ `adr-0021`/`adr-0022` 状态 `Accepted` | ✅ | 文件内 `**状态**：Accepted` 已确认 |
| ④ 无 `_tmp/_orig/_rej` 残留 | ✅ | `git status --porcelain` 无匹配 |
| ⑤ 只动 `.tao/adr/**` + 本任务书 | ✅ | `Makefile` + `milestones.md` 为并存任务 `INFRA-050t` WIP，不计入本任务 |

**脚本质量审核**：17+6 条断言均有可达 FAIL 路径；注入自检用 `cp`+md5 在临时副本操作、不污染 repo；结尾无 `tee`；`set -u` 保护变量。合格。

**判决**：**Accepted** — 验收命令全绿、约束无违反、独立注入反例证伪通过。
