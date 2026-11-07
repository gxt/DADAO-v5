# INFRA-131t: remote.py 假绿与仓库路径展开

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-130t`（已合入）
**状态**：待开始

## 背景与事实

`INFRA-130t` 交付的 `remote.py` 首次用到真实节点上即暴露缺陷。实测命令：

```
python3 tools/infra/remote.py status --hosts 'gxt@<node>,gxt@<node2>' --repo '~/DADAO-v5'
```

两台节点均返回 **rc=0 (PASS)**，但日志里：

```
# rc: 0
commit=fatal: not a git repository (or any of the parent directories): .git
worktree=clean
dirty_files=0
clang=MISSING
qemu=MISSING
--- stderr ---
bash: line 1: cd: ~/DADAO-v5: No such file or directory
```

即：**仓库根本没进去，节点状态完全没读到，却报 PASS**。

### 根因（已定位，两处）

1. **`&&` 只护住脚本第一行**：`build_shell` 拼成 `cd <repo> && <script>`，而 `<script>` 是多行、以 `set -u` 开头 ⇒ 远端实际展开为
   `cd <repo> && set -u` + 换行 + 其余各行；换行等价 `;`，所以 **`cd` 失败后其余命令照跑**，退出码取最后一条命令（`free`/`df`）⇒ 恒 0。
2. **`~` 被引号吃掉**：`shlex.quote("~/DADAO-v5")` 产出 `'~/DADAO-v5'`，引号内的 `~` 不展开 ⇒ `cd` 必失败。因此第 1 条必然被触发。

附带：`status` 即使 `git rev-parse` 失败也不判 FAIL（`git ... 2>&1 | head -n1` 的 rc 被管道吞掉）；`preflight` 等脚本是否有同类「最后一条命令决定 rc」问题未核。

## 目标

1. **仓库进不去必须判该节点失败**（非零 + 汇总 FAIL），不得输出「干净/无脏文件」这类假状态。
2. `--repo` 支持以 `~/` 开头，按远端 `$HOME` 展开。
3. `status` 里 `git` 读不到 commit（非仓库 / 命令失败）⇒ 该节点 FAIL。
4. 顺查另外三个子命令（`preflight`/`run`/`collect`）是否存在同类「cd 失败仍继续」「rc 被管道/最后一条命令吞掉」的问题，一并修。

## 范围 / 非范围

**在范围内**：`tools/infra/remote.py`、其证据脚本、本任务书、`milestones.md`、`issues.yaml`（如需登记）。

**不在范围**：`bootstrap_node.sh`（`ISS-347` 另记）、`Makefile`、其它门控。

## 验收标准

1. **复现→修复**：修复前能用一条命令复现「仓库不存在 ⇒ rc=0 + `commit=fatal`」；修复后同一命令 ⇒ 该节点 FAIL、整体非零，且日志明确「repository not found / not a git repository」，**不再打印 `worktree=clean`/`dirty_files=0`**。
2. **`~/` 展开**：`--repo '~/<repo>'` 在远端能进到正确目录（用真实节点或本机 `--local` 验证路径展开，不得靠手工改成绝对路径绕过）。
3. **正常路径**：`--repo` 有效时 `status` 报出真实 commit、clang/qemu 版本、磁盘/内存；rc=0。
4. **失败路径逐子命令**：`preflight`/`run`/`collect` 在「仓库不存在」时同样 FAIL（给出真实 rc）；`run` 注入 `exit 3` 仍应得 host rc=3。
5. **证据脚本**：新增断言能覆盖 1/2/4；**必须给出注入→FAIL→还原→回绿**（`cp`+md5，禁 git 还原）；断言总数与真实 rc 逐条对齐。
6. `make check`（L1）rc=0（或唯一红为外部占用并有归属证据）。
7. 完成区 ≤30 行、无运行期路径（节点地址、日志绝对路径不写）。

## 说明

- 这是 `INFRA-130t` 遗留的使用侧缺陷，**不是**要重做设计；保持现有子命令与参数风格，只修「cd 语义 / 路径展开 / rc 传播」。
- 修复后请在真实节点上跑一次 `status`，把结果（不含地址）写进完成区作为使用侧证据。
