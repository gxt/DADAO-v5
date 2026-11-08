# INFRA-145t: 台账一致性与临时目录门控（靠规则，不靠记忆）

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-143t`（派单时间列）
**状态**：待开始

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
