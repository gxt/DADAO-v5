# INFRA-131t: remote.py 假绿与仓库路径展开

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-130t`（已合入）
**状态**：已验证

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

## 完成区

**测试结果**：证据脚本 12/12 通过；`--inject` 18/18（3 组注入→FAIL→`cp`+md5 还原→回绿）；`INFRA-130t` 旧证据 16/16 仍绿。
**修改文件**：`tools/infra/remote.py`、`.work/evidence/INFRA-131t/run.sh`（新增）、本任务书、`.tao/knowledge/milestones.md`。
**验收结果**（真实 rc，均现场自跑）：
- 修复前复现：`--local` 指向不存在目录 ⇒ `overall rc=0`、节点 `rc=0 (PASS)`，日志有 `commit=fatal: not a git repository`、`worktree=clean`、`dirty_files=0`，stderr 有 `cd: ... No such file or directory`；两台真实节点用 `--repo '~/<repo>'` 同样假绿（rc=0）。
- 修复后同一命令 ⇒ 节点 `rc=2 (FAIL)`、`overall rc=1`，日志含 `repository not found`，且**不打印** `worktree=clean`/`dirty_files=0`；真实节点同路径亦 `rc=2`。
- 目录存在但非 git 仓库 ⇒ `commit=MISSING` + `commit_error=fatal: not a git repository`，rc=2。
- `--repo '~/<repo>'`：`--local` 覆盖 `$HOME` 后报出该 HOME 下仓库的真实 commit（与调用者仓库 HEAD 不同），rc=0；`~/` 不存在 ⇒ rc=2 且打印展开后路径；`~user/x` ⇒ rc=2 显式拒绝。
- 正常路径 `--local status` ⇒ 真实 commit、`qemu-dadao version 11.1.1`、磁盘/内存，rc=0。
- `preflight`/`run`/`collect` 仓库不存在 ⇒ 节点 rc=2、整体非零；`run -- sh -c 'exit 3'` ⇒ host rc=3。
- 真实节点 `status`（2 台，gxt 账号）⇒ rc=0，两机 commit `afff2886…`、`worktree=clean`/`dirty_files=0`、`qemu-dadao version 11.1.1`（真实值，非 MISSING）。
- `make -k check`（L1）rc=2，唯一 Error 是 `check-patch-tree`（gem5 5 个 patch 与共享 gem5 源树 HEAD 不一致）；归属 `GEM5-030t`（待验收；其 worktree 未提交改的正是这 5 个 patch，且共享 gem5 HEAD 的 diff 与其 patch 正文逐字一致）⇒ 外部并发，非本任务回归。
**新发现/坑**：① `cd X && <多行脚本>` 只护首行——换行等价 `;`，rc 取末条命令 ⇒ cd 失败变假绿，须 `|| exit`。② `shlex.quote('~/x')` 会吃掉 `~`，远端路径须显式拼 `"$HOME"`。③ `git … 2>&1 | head` 吞 rc，须 `if ! var="$(…)"` 取真实状态。④ `--local` 下若调用者 cwd 本身是仓库，cd 失败会读出调用者仓库数据（比“无数据”更隐蔽）。⑤ 日志前缀仍为 `INFRA-130t`（沿用既有断言，改名会破坏旧证据）。
**遗留问题**：无未完成项。外部并发：`GEM5-030t` 占用共享 gem5 源树，其合并前 L1 需由主会话复跑。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `cd` 用变量后 body `set -u` 是否受影响 | ✅已修 | 前置段 `repo_dir=…`→`cd`→`unset repo_dir`，body 的 `set -u` 在其后 | C1/C6 正常；仓库不存在 rc=2 |
| F2 `cd` 受 `CDPATH` 影响可能进错目录且污染 stdout | ✅已修 | 改为 `if ! CDPATH= cd "$repo_dir"` | 证据重跑 12/12、`--inject` 18/18 |
| F3 `git status` 失败仍可能报 `worktree=clean` | ✅已修 | 失败时打印 `worktree=UNKNOWN`/`dirty_files=UNKNOWN` 并 `exit 2` | C2 对非 git 目录：rc=2、无 `worktree=clean` |
| F4 `--remote-dir` 同样被 `shlex.quote` 吃掉 `~` | ✅已修 | `collect` 改用 `quote_remote_path` + `[ -d ]` 判定 | C12 `~/repo` 取值 `fixture`、rc=0 |
| F5 `~user/x` 会被静默当字面路径 | ✅已修 | `quote_remote_path` 显式 `fail(...)` | C5 rc=2 且输出“supported for remote paths” |
| F6 证据 C5 grep 模式含括号写错导致假 FAIL | ✅已修 | 改 `grep -qF "supported for remote paths"` | C5 转 PASS |
| F7 `INJECT-status` 只回退 commit 守卫，`dirty` 守卫仍兜住，未真复现假绿 | ✅已修 | 整段回退为旧的 `head -n1` + 无条件 clean 写法 | INJECT-status 变异后 rc=0（假绿复现）→ 断言 FAIL |
| F8 证据注入是否为“空注入” | ✅已修 | 记录变异前后 md5 并断言不等 | 18/18，三组变异 md5 均与原件不同 |
| F9 证据断言硬编码 `INFRA-130t-*.log` 文件名，日志前缀一变即误红 | ✅已修 | 新增 `log_of`：从工具自身输出取 `log=` 路径，不再写死文件名 | 重跑 12/12 + `--inject` 18/18 |

判决：无未修 finding ⇒ 置「待验收」。

### 第 1 轮 reviewer 验收

**重跑记录**（命令均自跑于任务 worktree；临时产物落运行期临时目录，未归档；下述 rc 全部为 reviewer 终端真实退出码）：
1. 读码：`build_shell` = `enter_repo()` 前置段（`if ! CDPATH= cd "$repo_dir"; then printf … >&2; exit 2; fi` + `unset`）+ 脚本体，**不再用 `&&` 护多行**；`status`/`preflight`（`command_status`）、`run`、`collect` 四条路径全部经 `run_node → build_shell`，无旁路；`quote_remote_path`：`~`→`"$HOME"`、`~/x`→`"$HOME"/x`、`~user`→`fail()` 拒绝，其余走 `shlex.quote`；`STATUS_SCRIPT` 的 `git rev-parse` 或 `git status` 失败 ⇒ 打 `commit=MISSING`/`worktree=UNKNOWN` 后 `exit 2`，走不到 clean 行。
2. 修复前复现（`git show HEAD:tools/infra/remote.py` 只读取旧版，非 git 还原）：cwd 非仓库 ⇒ **rc=0 PASS** + `commit=fatal: not a git repository` + `worktree=clean` + `dirty_files=0`；cwd 为仓库 ⇒ rc=0 且误读调用者仓库数据；**真节点 + `--repo '~/DADAO-v5'` ⇒ 两节点 rc=0、`commit=fatal`、`worktree=clean`、`qemu=MISSING`、overall rc=0**（与任务书背景逐字一致，复现成立）。
3. 场景 a（repo 不存在，`--local`）：overall rc=**1**、节点 rc=**2**、stderr `repository not found`；日志中 `worktree=clean`/`dirty_files=0` 命中 **0 次**。场景 b（存在非 git 目录）：overall rc=**1**、节点 rc=**2**、`commit=MISSING` + `commit_error=… not a git repository`，无 clean/0。场景 c：覆盖 `$HOME` 后 `~/<fixture>` ⇒ rc=**0** 且 commit 与 fixture HEAD 逐字相同；`~/<不存在>` ⇒ rc=**1**、节点 rc=**2** 并打印展开后的 `$HOME/<name>`；`~user/x` ⇒ rc=**2** `only '~/' (or '~') is supported`。
4. rc 传播：`run -- sh -c 'exit 3'` ⇒ 节点 rc=**3**、overall rc=**1**（原被吞那类）；`preflight`/`run`/`collect` 在 repo 不存在时均节点 rc=**2**、overall **1**；collect 在 repo 存在但 remote-dir 缺失 ⇒ 节点 rc=**2**；collect `~/` 展开 rc=**0** 且取回 fixture 文件。
5. 真节点（两台，gxt 账号，地址不落盘）：`status --repo '~/DADAO-v5'` ⇒ overall rc=**0**，两机 `commit=afff2886…`、`worktree=clean`/`dirty_files=0`、`qemu=…11.1.1`；另用独立 `ssh … git rev-parse HEAD` 交叉核对，两机 HEAD 与日志逐字一致、porcelain 计数 0，`qemu`/`clang` 版本与独立取值逐字一致。`--repo '~/<不存在>'` ⇒ 两节点 rc=**2**、overall rc=**1**。
6. 证据脚本：default ⇒ rc=**0** `PASS=12 FAIL=0`；`--inject` ⇒ rc=**0** `PASS=18 FAIL=0`（3 组变异 md5 均 ≠ 原件，还原后 md5 回到原件）。**reviewer 自选注入点**（非其已有三组：令 `command_run` 脚体吞 rc `shlex.join(command) + ' || true'`）：变异 md5 `b8c93abf…` ≠ 原件 `9f68b262…` ⇒ 转红 `FAIL C10-run-exit3-propagates`、`PASS=11 FAIL=1`、rc=**1**；`cp` 还原 + md5 相等 ⇒ 回绿 `PASS=12 FAIL=0`、rc=**0**（全程未用 git 还原）。
7. 回归：INFRA-130t 证据脚本 ⇒ rc=**0** `PASS=16 FAIL=0 SKIP=0`（与主仓副本 md5 相同，未被改动）；`bash -n` 两个 run.sh 均 rc=**0**；`python3 -m py_compile tools/infra/remote.py` rc=**0**（本轮无 shell 产物改动）。
8. L1：`make -k check` ⇒ **EXIT=2**，`[PASS]=1212`、`[FAIL]=0`，唯一 Error = `check-patch-tree`（10 problem = 5 文件 × 断言⑥⑨），`check-knowledge-refs` 悬空 0、`check-no-residue` PASS。归属核验：共享 gem5 源树 HEAD 的该 5 文件 diff 与并发任务工作树**未提交**的 5 个 `.patch` **5/5 字节一致**，且该任务工作树改动清单正是这 5 个文件 ⇒ 外部占用，非本任务回归。
9. 完成区 15 行 ≤30、无运行期绝对路径/节点地址（扫描仅命中背景节占位符与 `.work/evidence/` 仓库相对路径）；`milestones.md` 与任务书状态均为 `待验收`，一致；改动面 = `tools/infra/remote.py` + 本任务书 + `milestones.md` + 证据脚本，未越界；本轮 reviewer 未 commit/push、注入用 `cp`+md5。

**核验范围**：以上 1–9 全部由 reviewer 自跑验证，**未采信 engineer 转述**；其完成区数字（12/18/16、rc=2/1/3/0、L1 rc=2 唯一红）与我实测逐条一致。
**文档级 finding（不阻断，交 architect 收尾改）**：完成区称 `GEM5-030t`「待验收」，其任务书实为「待开始」（该任务工作树已有大量未提交改动）——措辞笔误，归属结论不受影响。
**约束核验**：验收 1–7 逐条满足；验收 6 的唯一红已核实为外部占用并附归属证据。
**判决：Accepted**。

**「假绿是否已根除」：是。** 依据（均为 reviewer 自跑真实 rc）：① repo 不存在 ⇒ overall **1**/节点 **2**，日志 0 处 `worktree=clean`、`dirty_files=0`；② 非 git 目录 ⇒ **1**/**2**、`commit=MISSING`；③ `~/` 不存在 ⇒ **1**/**2** 并打印展开路径；④ `run -- sh -c 'exit 3'` ⇒ 节点 **3**；⑤ `preflight`/`run`/`collect` 缺仓库 ⇒ 节点 **2**；⑥ 两台真节点 `~/` 缺路径双 FAIL、overall **1**，而正确路径 **0** 且与节点独立 `git rev-parse` 逐字一致；⑦ 同一命令用旧版脚本 ⇒ 节点 **0**（复现成立，断言确能区分新旧）。

#### 收尾（architect，2026-11-07 21:35）

- 判决 Accepted：reviewer 以 7 条独立 rc 证「假绿已根除」（旧版同命令节点 rc=0 / 新版 rc=2，含两真节点两向验证）。
- F1（record 更正）：审阅记录称 `GEM5-030t` 任务书为「待开始」——那是**本任务分支上 master 的旧副本**；`030t` 的 `待验收` 只在其自身未提交工作树内，非笔误，归属结论不受影响。
- F2（不阻断）：`--repo` 指向某 git 仓库的**子目录**时 cd 成功、会报父仓库状态；不属「cd 失败仍 PASS」，登记 `ISS-348`（要求校验仓库根）后另议。
