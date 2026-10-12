# INFRA-065t: 子代理工作目录作用域（workdir）规则 + 权限 fail-fast

**模块**：infra
**项目里程碑**：M7
**依赖**：无（**改 `AGENTS.md` + `.opencode/agents/*.md` ⇒ 与在办任务串行**）
**状态**：待开始

> 本任务书由**主会话**依用户 2026-10-11 裁定撰写（非常规 architect 起草，已披露）。**缘起**：子代理常在命令首位写 `cd /mnt/tao`（仓库**父目录**）⇒ 触发权限询问 ⇒ **夜跑无人应答 = 挂死**。

## 用户裁定（2026-10-11，**原话**）

> 「子代理在组合命令的时候，经常会使用 `cd /mnt/tao` 来作为命令的起始第一条，于是，就卡住在访问权限这里；这个事情如何避免；尤其是在夜跑的时候」
> 「**`cd` 命令本身是不能禁止的，应该是限制子代理都在 `workdir` 中**」
> 「**可以**；不过现在就要夜跑了，**等明早吧**」

## 目的

把"子代理作用域"钉在 **workdir = 仓库根**：仓内相对路径 `cd` 允许；**越出仓库**（绝对路径 / `~` / 上跳）**当场失败**（fail-fast），而不是"无人应答地挂 ask"。

## 诊断（已取证，写入本任务书供复核）

| 检查 | 结果 | 推断 |
|---|---|---|
| OS 层 `cd /mnt/tao` | rc=0 正常 | 非文件系统问题 |
| `.opencode/agents/{architect,engineer,reviewer}.md` frontmatter | `permissions: [shell * → allow, sudo * → deny]` | **shell 已全允许却仍 ask/卡** ⇒ **该 `permissions` 形态很可能未生效**（待 canary 判定） |
| 仓内 `cd /mnt` 示例 | `git grep` **0 命中** | 非文档所示范，属模型习惯 |

## 输出

1. **canary 验证**（**先做**）：后台起一子代理，只跑 `cd /mnt/tao && pwd; echo rc=$?`，据结果判定 `permissions` 是否生效与**该写哪种形态**（agent frontmatter vs 项目 `.opencode/opencode.jsonc`）：
   - 返回 `deny/error` ⇒ 权限层生效 ✓；
   - 返回 `rc=0` 且无 ask ⇒ 仅"越界默认 ask"作怪 ⇒ deny 规则同样有效 ✓；
   - **长时间不返回** ⇒ 权限层不可靠 ⇒ 只靠规则层 + 夜跑冒烟（**须登记**）。
2. **规则层（作用域 = workdir，不禁 `cd`）**：
   - `AGENTS.md`「**子代理硬约束（下发提示必带）**」**新增一条**：命令一律在 **workdir（= 仓库根）** 内、用**相对路径**；**禁出界** `cd /*`、`cd ~*`、`cd ..*`；换目录用工具的 **`workdir` 参数**。
   - `.opencode/agents/{architect,engineer,reviewer}.md` 各自的硬约束节各一句（同一口径）。
3. **权限层（fail-fast，替掉"无人应答的 ask"）**：按 canary 结论在**生效的位置**加 deny：
   ```
   - action: shell
     resource: "cd /*"     # 绝对路径 ⇒ 出界
     effect: deny
   - action: shell
     resource: "cd ~*"     # home ⇒ 出界
     effect: deny
   - action: shell
     resource: "cd ..*"    # 上跳 ⇒ 出界（仓内 `cd .work/...` 不受影响）
     effect: deny
   ```
4. **夜跑纪律**：夜跑前做**权限冒烟**（1 条代表性命令，不含绝对 `cd`）+ 下发提示内联该条；夜跑任务避免绝对路径。
5. **知识沉淀**：`lessons` 追加一条（≤3 行 + 指针）：**"待办/计划"必须落任务书或 `milestones.md`，不得落 `.work/`（可丢弃、无人提醒）**；并在 `milestones.md`「规划中」登记本任务。

## 约束

- **不加门控**（用户口径：能靠规则 + 权限解决的，不新增门控）。
- 只动 `AGENTS.md`、`.opencode/agents/*.md`、`lessons.md`、`milestones.md`、本任务书；越界须披露。
- 临时目录 `/tmp/opencode/INFRA-065t/`；**不提交 git**；禁 `git add -A`/`.`。
- 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
- 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位），否则 `check-knowledge-refs` 判悬空、`make check` 自伤。

## 验收标准

1. **canary 结论**：给出三种结果中**实测**那一种 + 依据（真实输出/超时现象），并据此确定 deny 落点（agent frontmatter vs `opencode.jsonc`）。
2. **规则落地**：`AGENTS.md`「子代理硬约束」含该条（`grep` 真实输出）；三个 agent 定义各含一句（`grep` 真实输出）。
3. **权限 deny 生效**：注入/实跑一条**出界命令**（如 `cd /mnt/tao`，**用临时子代理或受控方式**，避免主会话被卡）⇒ **当场失败**（deny/error，**非挂起**）；仓内 `cd .work/...` 仍**正常**（对照）。
4. **夜跑冒烟**：给出「夜跑前冒烟」的可执行步骤（1 条命令 + 期望结果）。
5. **知识沉淀**：`lessons` 新条目（≤3 行 + 指针）+ `milestones.md`「规划中」登记。
6. **门控**：`make check`、`check-knowledge-refs`、`check-no-residue` 各 EXIT=0（捕获**命令自身**退出码）。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
