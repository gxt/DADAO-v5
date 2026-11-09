# INFRA-143t: 台账「进行中」表增派单时间；派单即移入该表

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-141t`（三分表）、`INFRA-142t`（文件头）
**状态**：已验证

## 用户授权（原话）

> 「这个问题的关键不是引入新状态，而是派单后，应该把对应任务移动到第二类表格中，第二类表格应该增加：派单时间」

## 背景与事实

- 现状三分表：`待开始`（预估时间）/ `进行中`（预估时间）/ `已验证`（完成时间）。
- 问题：任务书状态在**任务分支内**改，合并前主树看不到 ⇒ 在跑的任务在主树仍显示 `待开始`，`进行中` 表恒空。
- 用户裁决：**不引入新状态**；改为「**派单即移入进行中**」，并给该表加 **派单时间** 列。

## 目标

### 1. 版式

```markdown
## 待开始（未开工）
| 编号 | 预估时间 | 一句改动 |

## 进行中（已派单：待开始 / 待验收 / 待返工）
| 编号 | 派单时间 | 预估时间 | 一句改动 |

## 已验证
| 编号 | 完成时间 | 一句改动 |
```

- **派单时间** 格式 `YYYY-MM-DD HH:MM`（派单动作发生时由主会话填写）。
- 「进行中」表收录：**已派单但未合并**的任务，即任务书状态可为 `待开始`（已派单、实现中）、`待验收`、`待返工`。
- 「待开始」表 = **尚未派单**的任务（无派单时间）。

### 2. 门控（`check_milestones_fresh.py`）

- **分类映射**：
  - 待开始表：任务书状态**必须** `待开始`；
  - 进行中表：任务书状态 ∈ {`待开始`,`待验收`,`待返工`}，且**必须有**派单时间；
  - 已验证表：任务书状态**必须** `已验证`。
- **可判定性（关键）**：`待开始` 状态的任务可出现在**任一**前两表——出现在「待开始」表表示未派单、出现在「进行中」表表示已派单；门控用**表位置**区分，不要求额外状态。
- 其余断言保持：并集覆盖、一句改动 ≤120、仅第三表倒序、无状态列、跨表不重复、fail-closed。
- `--self-test` 注入增补：① 进行中行**缺**派单时间 ⇒ FAIL；② 待开始表行**带**派单时间 ⇒ FAIL（表位置与列不符）；③ 派单时间格式非法 ⇒ FAIL。

### 3. 迁移现有三条在跑任务

按现场首个任务专属日志时间填派单时间（实测）：

| 任务 | 派单时间 | 预估 |
|---|---|---|
| `GEM5-028t` | 2026-11-08 09:53 | 1–2 h |
| `QEMU-085t` | 2026-11-08 11:17 | 2–3 h |
| `INFRA-140t` | 2026-11-08 12:24 | 1 h |

（`INFRA-143t` 自己也按派单时填入。）

### 4. 文档

- `AGENTS.md`「批次授权」「任务成立判据」两处：补「**派单即把该行移入「进行中」并填派单时间**」。
- `docs/Process-07`（门控描述行）与 `.opencode/commands/complete.md`（E 节）同步三表 + 派单时间。
- `milestones.md` 文件头说明段同步（表结构与列含义）。

## 范围 / 非范围

**在范围内**：`tools/infra/check_milestones_fresh.py`、`.tao/knowledge/milestones.md`、`AGENTS.md`、`docs/Process-07`、`.opencode/commands/complete.md`、本任务书。

**不在范围**：任务书状态机（仍四态）、`docs/Process-04`、其它门控。

## 验收标准

1. `make check-milestones-fresh` rc=0；三条在跑任务已在「进行中」表且带派单时间；`待开始` 表只剩真正未派单的。
2. 五类注入逐条真实 rc：① 进行中缺派单时间；② 待开始行带派单时间；③ 派单时间格式非法；④ 状态映射不符（如 `已验证` 行留在进行中）；⑤ 第三表乱序；均 `cp`+md5 还原回绿。
3. `--self-test` rc=0（含新增三类）。
4. `make check`（L1）rc=0（并发任务导致的 `check-patch-tree` 红需核实归属）。
5. 文档三处与新格式一致。
6. 完成区 ≤30 行、无运行期路径。

## 说明

- 「派单时间」由**主会话**在派单时填写；engineer/reviewer 不改台账行（只改任务书 `**状态**`），以减少合并冲突。
- 预估值仍是人工估值，门控只校验格式与存在性。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：可交付（无未修 finding）；实现与自审均完成。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 证据脚本临时目录与工作树根下同名目录冲突 ⇒ 未跟踪残留 | ✅已修 | 临时目录改到脚本同目录 `tmp/`（不落跟踪区） | `git status --porcelain -uall` 仅 6 个改动文件（均本任务范围）；证据脚本 36/36 |
| F2 注入④按行前缀替换 ⇒ 注入行 5 格、未命中目标断言 | ✅已修 | 改为整行替换 | 注入④ 各断言全 PASS、命中 MISMATCH |
| F3 门控注释残留旧口径「类别即状态」 | ✅已修 | 改为「表位置即状态」 | 全文件 grep 0 命中 |
| F4 `docs/Process-04` 两处仍写旧表名 | ⏸延后 | 任务「不在范围」明确排除 Process-04 | 已在完成区记录 |
| F5 自产日志退出码文件命名不合法 ⇒ L1 的 `check-run-artifacts` 假红 | ✅已修 | 退出码并入 `.log` / 改用 `-exit.txt` 合法名 | L1 复跑 `check-run-artifacts` PASS |

**逐行要点**：`check_rows` 按表种类定列宽（待开始/已验证 3 格、进行中 4 格）；「缺派单时间」「不得含派单时间」各有独立可达 FAIL；派单时间用独立 `DISPATCH_RE` 严格校验（不接受 `（登记）`）；A1 允许 `待开始` 出现在前两表（表位置区分未派单/已派单）；A4 仅第三表倒序；覆盖/fail-closed/长度/状态列断言未改。`--self-test` 由十一类扩为十四类，逐条断言「rc=1 且命中目标断言」。

### 第 1 轮 reviewer 验收

**判决**：**Accepted**（无阻断项；2 条文档级 finding 见末尾）。以下均 reviewer 亲自重跑，非采信 engineer 转述。

**重跑记录（命令 / 真实输出 / 退出码）**
- `make check-milestones-fresh` → `rc=0`；`结果: PASS（待开始 4 行 / 进行中 4 行 / 已验证 97 行；分类一致 / 覆盖 / ≤120 字符 / 已验证倒序 / 格式 / 无状态列）`
- `python3 tools/infra/check_milestones_fresh.py --self-test` → `rc=0`；干净基线 + 注入①–⑭ 共 15 行 `PASS`、`FAIL` 行数 0
- 任务证据脚本（运行期、未归档）在任务 worktree 内以 `SKIP_L1=1` 运行 → `EVID_RC=0`，`结果: PASS=36 FAIL=0`；注入前 md5 `0e101594…`、终态同值（S5 校验）
- **独立注入（reviewer 自造，非脚本用例）**：删 `INFRA-140t` 派单时间后**重跑同一脚本** → `RUN_RC=1`、`结果: PASS=29 FAIL=7`（S1/S3 均 FAIL）；`cp` 备份还原 → md5 回 `0e101594…` → 重跑 `EVID_RC=0`、`36/36`。另有 5 类真树注入逐条 `python3 …` `rc=1`（make 包装为 rc=2）、命中「缺派单时间」「不得含派单时间」「须为 `YYYY-MM-DD HH:MM`」「A1 MISMATCH」「A4 逆序」，及 2 类附加注入（待验收行入待开始表 → A1 MISMATCH；未派单行入进行中无派单时间 → 宽度错），每次 `cp`+md5 还原、回绿 `rc=0`
- `make -k check`（L1）→ `rc=2`，唯一红：`check-patch-tree: 4 problem(s)` = qemu `linux-user/mmap.c` ⑥⑨ + gem5 `src/arch/dadao/se_workload.cc` ⑥⑨；其余全 PASS（含 `check-run-artifacts: PASS`、`check-milestones-fresh` PASS）。**归属核实**：在主树 master 上 `make check-patch-tree` 同样 `rc=2` 同 4 条；本分支 `git diff --name-only` 仅 6 个任务范围文件、`components/` 零改动；`components/qemu/patches/linux-user/mmap.c.patch` 与 `components/gem5/.../se_workload.cc.patch` 中 `mremap`/`mmapCeiling` 均 0 处 ⇒ 红来自并发 QEMU-085t/GEM5-028t
- **快照对账**：验收前后 `git status --porcelain -uall` 均为同一 6 文件，md5 逐文件相等（`8c276b19…/0e101594…/cf96b83b…/131950f7…/8aa54289…/82772476…`），与完成区「修改文件」声明一致；主树 `git status` 干净、主树台账 md5 `4ae56b90…` 未被我误跑的脚本污染（trap 已还原，主树门控仍 `rc=0`）

**约束核验**
- 分类规则（读码 + 注入证实）：待开始表仅 `待开始` 且禁派单时间（3 格）；进行中表 ∈ {`待开始`,`待验收`,`待返工`} 且派单时间必填（4 格、`DISPATCH_RE` 严格）；已验证表仅 `已验证`；`STATUS_VALUES` 仍为四值、状态列仍禁止 ⇒ **未引入新状态**
- 迁移：四条均在进行中表，派单时间/预估 = 028t `09:53/1–2 h`、085t `11:17/2–3 h`、140t `12:24/1 h`、143t `13:51/2 h`，与任务书给定值一致；实测佐证：各任务**首个专属日志** mtime = 09:53 / 11:17 / 12:24，143t worktree 建立 `13:50:51`（reflog）；四者均有任务分支 + worktree。待开始表剩 `INTEG-060t/TESTCASES-104t/INTEG-059t/TESTCASES-103t`，`git worktree list`/`git branch` 中均无对应项 ⇒ 真正未派单
- 文档：`AGENTS.md` 批次授权 + 任务成立判据两处、`docs/Process-07` 判据行、`.opencode/commands/complete.md` E 节、`milestones.md` 文件头三表说明均与新格式一致；全仓 `分类即状态` 0 命中；旧表名 `已提交待验收` 仅余 `docs/Process-04` 与历史任务书（任务书明列不在范围，已在完成区记录）⇒ 不判失败
- 完成区 18 行（≤30），无临时目录、家目录、宿主绝对路径、`.work/…` 等运行期路径

**Finding（均文档级，不阻断，交 architect 收尾改）**
- F1：完成区「现树 `mmap.c` 有 `mremap` 8 处」——现文件实为 **16** 处；8 = `git show HEAD -- linux-user/mmap.c` 的新增处数，措辞宜写明口径。
- F2：证据脚本按自身路径推 `repo`，`.work` 是指向主树的符号链接 ⇒ 在**主树**执行会审主树（我首跑 22/14 FAIL，属用法陷阱；脚本 fail-closed 不出假绿）。建议在脚本内加「所审树须含派单时间格式」自检或改用 `git rev-parse --show-toplevel`。

## 完成区

**测试结果**：任务域检查 36/36 PASS（证据脚本 `SKIP_L1=1` 档）；`--self-test` 15 条（干净基线 + 14 注入）rc=0；L1 见下。
**修改文件**：
- `tools/infra/check_milestones_fresh.py`：进行中表 4 列 + 派单时间必填；待开始表禁派单时间；进行中允许 `待开始`（已派单）；self-test 十四类
- `.tao/knowledge/milestones.md`：文件头三表说明/列含义 + 派单即移入；GEM5-028t/QEMU-085t/INFRA-140t/INFRA-143t 迁入「进行中」并填派单时间
- `AGENTS.md`：批次授权、任务成立判据两处补「派单即移入进行中并填派单时间」
- `docs/Process-07-门控分层规范.md`：`check-milestones-fresh` 判据行同步
- `.opencode/commands/complete.md`：E 节三表 + 派单时间
**验收结果**：
- 真树门控 rc=0：待开始 4 行 / 进行中 4 行 / 已验证 97 行（现场统计）
- 五类注入：均 rc=1 且命中对应断言；`cp`+md5 还原后逐条回绿（逐条输出见证据脚本）
- 迁移核验：四条任务在「进行中」且派单时间/预估符合（GEM5-028t 09:53 / QEMU-085t 11:17 / INFRA-140t 12:24 / INFRA-143t 13:51；本任务按建树时刻 13:50:51 填 13:51）
- L1 复跑 `make -k check`：仅 `check-patch-tree` 红（qemu `linux-user/mmap.c` / gem5 `se_workload.cc`——共享构建树 HEAD 已含在跑任务 QEMU-085t/GEM5-028t 的补丁：现树 `mmap.c` 中 `mremap` 命中 16 处（其中 8 处为 `HEAD` 版新增）、`se_workload.cc` 中 `mmapCeiling` 命中 6 处，本分支补丁文件均为 0 处；本任务 diff 不触及 `components/` 与构建树）。本任务门控 `check-milestones-fresh` 与 `check-run-artifacts` 均 PASS（后者首轮红系本任务自产退出码文件命名不合法，改名后消失）。
**新发现/坑**：
- 「进行中」标题改名后 `docs/Process-04` 两处引用仍是旧名（本任务范围排除），建议后续随档案规范同步。
- 证据脚本的临时目录若放在任务工作区根下会与同名目录冲突产生残留，须放脚本内 `tmp/`（不落跟踪区）。
**遗留问题**：无（Process-04 文案待后续任务同步，非本任务范围）

#### 收尾（architect，2026-11-08 14:18）

- 判决 Accepted：reviewer 独立跑门控（4/4/97）、`--self-test` 15 条、证据 36/36，并自造 7 类注入逐条 rc=1 + `cp`+md5 还原；主树复现同 4 条 `check-patch-tree` 证明属并发任务。
- F1：完成区「`mmap.c` 有 `mremap` 8 处」口径已改为「命中 16 处，其中 8 处为 HEAD 版新增」。
- F2：证据脚本按自身路径推 `repo`，在任务 worktree 里 `.work` 指向主树 ⇒ 主树执行会审主树（fail-closed，不出假绿）。记录为证据脚本使用注意；后续复用该脚本时须从任务 worktree 调用。
- 结论：不引入新状态；`待开始`/`进行中` 仅由表位置 + 派单时间区分。
