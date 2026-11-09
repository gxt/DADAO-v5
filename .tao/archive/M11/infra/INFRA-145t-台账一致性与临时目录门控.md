# INFRA-145t: 台账一致性与临时目录门控（靠规则，不靠记忆）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-143t`（派单时间列）
**状态**：已验证

## 用户授权（原话）

> 「/tmp目录满的问题，是临时目录没有清理，这种事情不要一再发生！同样，台账漏了的问题，也需要避免；不要靠记忆，而是靠规则！！！」

## 目标（两条机械规则）

### R1 台账一致性：有在跑任务就必须在「进行中」

`tools/infra/check_milestones_fresh.py` 新增断言：

- 读 `git worktree list --porcelain`（以及 `.git/worktrees/*/HEAD` 分支名），凡分支名匹配任务号（`<PREFIX>-\d{3}[a-z]?`）者：
  - 该任务号**不得**出现在「待开始」表；
  - 必须出现在「进行中」表且带合法派单时间；
  - 若其任务书 `**状态**` 已 `已验证`，必须出现在「已验证」表。
- 无 worktree 但有同名本地分支（未合并）同样按「进行中」要求。
- 输出逐条指名（`L?? <任务号>: 有 worktree/分支但台账在「待开始」`）。

### R2 临时目录与 `/tmp` 占用门控

新增 `tools/infra/check_temp_dirs.py`（L1）：

- 扫描 `/tmp/opencode/*` 与 `$TMPDIR/opencode/*`：
  - 排除 `git worktree list` 中的活动路径（这些由任务收尾清理）；
  - 任一非活动目录 **mtime 超过 2 小时** ⇒ FAIL 并列出（`du` 前 5）；
  - `/tmp` 使用率 **> 70%** ⇒ FAIL（`df` 实测值，不写死容量）。
- 允许 `--root` 指向临时树做自检；**不得**删除任何目录（只报告）。

### R3 文档与门控接入

- `AGENTS.md`：`/tmp` 规则处补「非在用任务临时目录超过 2 小时即红（`check-temp-dirs`）；任务收尾必须删除 worktree 与临时目录」。
- `docs/Process-07`：登记两个新断言/目标所属层（L1）。
- `Makefile`：`check-temp-dirs` 目标并入 `make check` 清单。

## 验收标准

1. `make check-milestones-fresh` rc=0；**可达 FAIL**：临时把某在跑任务的台账行移回「待开始」⇒ FAIL 并指名；`cp`+md5 还原回绿。
2. `make check-temp-dirs` rc=0（当前环境）；**可达 FAIL**：造一个 `/tmp/opencode/<假任务>/` 并 `touch -d '3 hours ago'` ⇒ FAIL；删除后回绿。再测试「`/tmp` 占用 >70%」分支（可用 `--root` + 伪造 df 输出或参数注入，需给出真实 rc）。
3. `make check`（L1）rc=0（并发任务的红需核实归属）。
4. `AGENTS.md`/`Process-07`/`Makefile` 与实现一致。
5. 完成区 ≤30 行、无运行期路径。

## 说明

- 两个门控都**只报告不删除**；清理动作仍由主会话在收尾时执行（避免门控误删现场）。
- `check-temp-dirs` 必须能在其他机器上跑（无 `/tmp/opencode` 时按「无残留」PASS，不 vacuous 失败）。

## 执行中用户裁定（2026-11-08）

- 问：R1 已检出 `INFRA-145t` 有 worktree/分支但台账仍在「待开始」（应为「进行中」+ 派单时间），派单说明写「台账行不要动（主会话维护）」，如何处置？
  答：**授权我移入「进行中」（推荐）**。
- 问：R2 实测 `/tmp/opencode` 有 116 个 >2h 非活动目录（5.3 GiB；`/tmp` 占用 38%，未超 70%），门控按规格必红，是否授权清理这些陈旧目录？
  答：**授权全删陈旧目录（推荐）**。

## 完成区

**测试结果**：一键证据 `run.sh` **17/17 PASS**（rc=0）；R1/R2 各自的「注入→FAIL→还原→回绿」均为真实退出码。
**修改文件**：`tools/infra/check_temp_dirs.py`（新增，R2）；`tools/infra/check_milestones_fresh.py`（R1 + 自检六类真 git 用例）；`Makefile`（`check-temp-dirs` 目标 / PHONY / help / `_locked-check` 并入 L1）；`AGENTS.md`（`/tmp` 规则补门控一句）；`docs/Process-07-门控分层规范.md`（两个门控登记 L1）；`.tao/knowledge/milestones.md`（`INFRA-145t` 行移入「进行中」+ 派单时间，按上述用户裁定）。
**验收结果**：
- R1：基线 rc=0；注入（把在跑 `INTEG-060t` 移回「待开始」）rc=1 并指名 `INTEG-060t: 有 worktree 但台账在「待开始」`；`cp`+md5 还原（md5 一致）后 rc=0。
- R2：基线 rc=0；造 3 h 前非活动目录 rc=1 并指名、删除后 rc=0；`--usage-max 1`（真实 df 3.5%）rc=1、`--usage-max 100` rc=0；`--root` 指向不存在目录 rc=0（不 vacuous 失败）。
- `make check-milestones-fresh` / `make check-temp-dirs` rc=0；L1 其余 **50** 个目标 rc=0（`check_issues.py` + `compileall tools` 亦 rc=0）。
- `make check` 唯一红 = `check-patch-tree`（共享源树 gem5 `se_workload.cc` 未提交改动，属并发 `INTEG-060t`，其任务书已列该文件在范围内）——**非本任务**。
- R2 首跑在真实环境 FAIL（116 个陈旧目录 / 5.3 GiB，`/tmp` 38%），按用户裁定清理后回绿（`/tmp` 2%）。
**新发现/坑**：
- 「有 worktree / 未合并分支」是派单的机械证据；台账漏移会被 R1 立即指名（本次 `INFRA-145t` 自身即命中一次，靠规则而非记忆发现）。
- 已合并分支必须豁免，否则已验证任务会被残留分支拉回「进行中」（R1 自检已覆盖）。
- 体积只对**陈旧项**做 `du` 排序，避免每轮全量扫描；扫描根不可读时按 FAIL（fail-closed）而非 traceback。
**遗留问题**：无。R2 首跑暴露的 116 个陈旧目录已按用户裁定清理，清单留运行期证据。

## 审阅记录

### 第 1 轮 engineer 自审

**判决**：全部 finding 已处置 → 标「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R2 自检「活动 worktree 排除」原两支写同一结果（无法区分排除是否生效） | ✅已修 | 单列 `active_root`：带排除 ⇒ PASS、不带排除 ⇒ FAIL | `--self-test` 注入②/③ 均 PASS |
| 不可读扫描根会抛 traceback 而非 FAIL | ✅已修 | `audit` 捕获 `OSError` ⇒ VIOLATION（fail-closed） | `--self-test` + `py_compile` rc=0 |
| R1 自检「仅未合并分支」用 `git branch` 指向 master，实际已合并（恒 PASS） | ✅已修 | `commit-tree` 推进分支后才作为未合并分支 | 自检注入② rc=1 且 marker 命中 |
| `git init -b master` 依赖 git ≥ 2.28 | ✅已修 | 改 `git init` + `symbolic-ref HEAD` | 自检 rc=0 |
| 占用阈值自检用 `pct-1`，在空文件系统上可能退化为恒 PASS | ✅已修 | 阈值注入改 `-1`（必 FAIL）+ 100（必 PASS） | 自检注入④/基线③ 均 PASS |

### 第 1 轮 reviewer 验收（2026-11-08，独立重跑）

**判决：Accepted**。F1–F3 为设计/文档层 finding，交 architect 定夺，不改本判决。以下命令均由 reviewer 亲自执行（workdir=本任务工作树、相对路径；临时根按任务书路径规则记作 `<根>`）。

**重跑记录**
- `bash 运行期证据脚本 run.sh` ⇒ `SUMMARY: PASS (17/17)`、`RUN_EXIT=0`（23.7 s）；盘上 `r1-*.log`/`selftest-*.log`/`make-milestones.log` 与 engineer 留档逐字节相同，`r2-*.log` 仅差现场计数（直接子目录 7→8、占用 1.8%）⇒ 留档为真实输出、非转述。
- `python3 tools/infra/check_milestones_fresh.py --self-test` ⇒ **rc=0**、`self-test: PASS`（十四类 + **R1 六类真 git 用例**逐条 PASS）；`python3 tools/infra/check_temp_dirs.py --self-test` ⇒ **rc=0**、`self-test: PASS`（9 例，含「只报告不删除」）。
- `make check-milestones-fresh` **rc=0**（`R1 逐条核验 2 个在跑任务号`）；`make check-temp-dirs` **rc=0**；`make help` 含 `check-temp-dirs`。
- `make -k check` ⇒ **rc=2**，唯一红 `check-patch-tree`：`2 problem(s)` 全为 `src/arch/dadao/se_workload.cc`；并发 `INTEG-060t` 工作树 ` M components/gem5/patches/src/arch/dadao/se_workload.cc.patch`（其任务书第 24 行列该文件在范围内），本任务 `git status -- components/` 空 ⇒ 归属 060t，非本任务。

**独立注入（`cp`+md5 还原；还原后被改文件 md5 与注入前快照逐项相同，`git status` 仍为原 7 项）**

| 注入 | rc | 关键输出 |
|---|---|---|
| 145t 行（有 worktree）移回「待开始」 | 1 | `R1: … INFRA-145t: 有 worktree 但台账在「待开始」` |
| 145t 行整行删除（未列入任何表） | 1 | `R1: INFRA-145t: 有 worktree 但未列入「进行中」/「已验证」表` |
| 145t 任务书改 `已验证`、行留进行中 | 1 | `R1: INFRA-145t: 任务书 **状态** 已已验证，但台账在 … L34（须在「已验证」表）` |
| 造 3 h 前非活动目录 | 1 | `VIOLATION: <根>/ZZ-REVIEW-145t: 非活动临时目录 mtime 3.0 h > 2 h`；**检查后目录仍在**，删除后 rc=0 |
| `--usage-max 1` ／ `--usage-max 100` | 1 ／ 0 | `占用 1.8% > 1%` ／ `结果: PASS` |
| `TMPDIR=<根>/tmprun` 造第二扫描根 3 h 目录 | 1 ／ 删后 0 | 第二扫描根被扫并指名 |
| `--root` 指向非 git 树（复制完整 `.tao`） | 0 | `非 git 仓库（--root 自检树）⇒ R1 跳过`，无误报 |

**约束核验**：只报告不删除——两脚本无 `rmtree`/`unlink`/`os.remove`/`os.rmdir`（`shutil` 仅 `disk_usage`，grep 命中仅文档字符串）、无 `walk`/`glob`（只扫直接子目录）；活动 worktree 排除、已合并分支豁免（自检基线② rc=0）；完成区 15 行 ≤30 且无运行期路径；台账 145t 行在「进行中」、派单时间 `2026-11-08 16:43` 合法（A5 rc=0）；主工作树 `git status` 空。

**清理副作用（未误删）**：`cleaned-dirs.txt` 116 条带时龄路径全在 `<根>` 下，无 `INFRA-145t`/`INTEG-060t`/`INTEG-060t-work`；两工作树 `git status` 无删除项、本任务未碰 `components/`；活动 worktree 与 `INTEG-060t-work` 均在，现场 8 目录全为活动/新鲜，占用 1.8%。

**Finding（交 architect 定夺）**
- **F1（设计层）**：L2 `check-arch`/`check-arch-smoke` 探针根 `TESTCASES-093t`（42.1 MiB）/`TESTCASES-094t`（30.8 MiB）不会被 L1 刷新（`_locked-check` deps 无 `check-arch`；L1 自建根位次 `check-scope`13/`check-width-sizes`46/`check-code-range`49/`check-runner-reap`50 均 < `check-temp-dirs`51 ⇒ L1 自建根会刷新、L2 根不会）⇒ **L2 跑过 2 小时后 `make check` 必红**（`--max-age-hours 0` 实测命中 `TESTCASES-093t`/`TESTCASES-094t`/`INTEG-060t-work`）。残留是真实残留、非误报，但会自触发循环；且并发任务的非 worktree 工作目录被标「非活动」，有被误删风险 ⇒ 豁免口径与清理归属需裁定。
- **F2**：门控只扫目录，`<根>` 下 465 个陈旧**文件**不报（规格即如此，与「满了」诉求存在缺口）。
- **F3（文档）**：`cleaned-dirs.txt` 共 119 行（116 行带时龄路径 + 3 行裸名）vs 完成区「116」；「5.3 GiB / 38%→2%」目录已删不可复算 ⇒ 采信，数字口径由 architect 收尾统一。

#### 收尾（architect，2026-11-08 17:28）

- 判决 Accepted：reviewer 独立 7 类注入（移回待开始/整行删除/册已验证留进行中/3h 目录/占用阈值/TMPDIR 第二根/非 git 树）逐条 rc=1 且还原；代码无任何删除调用（`grep rmtree|unlink|remove` 仅命中文档串）；清理 116 目录无活动 worktree 误删。
- **F1（设计缺陷，另立 `INFRA-146t`）**：L2 `check-arch` 的探针根（`TESTCASES-093t`/`094t`）长期驻留 `/tmp/opencode`，L1 不刷新 ⇒ 2 小时后 `make check` 自触发红。处置：把**共享探针根迁到 `.work/`**（持久目录），`/tmp/opencode` 只留每任务 scratch；并调整 R2 豁免口径。
- **F2**：R2 只扫目录、不报陈旧大文件 ⇒ 在 `INFRA-146t` 一并加「陈旧文件」报告（>100 MiB 且 >2h）。
- **F3**：清单 119 行（116+3 裸名）与完成区「116」口径已在 146t 文档订正。
- 附：本任务清理 116 个陈旧目录，`/tmp` 38%→2%；两门控已并入 L1（`_locked-check` 51 项）。
