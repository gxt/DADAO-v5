# INFRA-134t: 工具清理与 `remote.py` 仓库根校验

**模块**：infra
**项目里程碑**：M11
**依赖**：`INFRA-130t` / `INFRA-131t`（已合入）
**状态**：已验证

## 背景与事实

两处已登记但未修的工具缺陷（验收时被 reviewer 判为「不阻断、可后修」）：

- `ISS-347`：`tools/infra/bootstrap_node.sh` 的 `DEV_OK` 实为「问题标志」（0=正常），名实相反，曾被改出反逻辑（依赖齐全反而退出 2）；另缺「仅 dev 缺失、工具齐全」的隔离用例，全缺时待安装清单 `- binutils` 重复 3 次。
- `ISS-348`：`tools/infra/remote.py` 的 `--repo` 指向某仓库的**子目录**时 `cd` 成功、`git rev-parse` 读到父仓库 commit，会报出「不是目标仓库」的状态而不报错。

两者都只改 `tools/infra/`，不触碰 `components/`、`Makefile`、门控判据与 SPEC，可独立于 gem5 线推进。

## 目标

1. **`bootstrap_node.sh` 语义改名**：`DEV_OK` → `DEV_BAD`（或等价：变量名与「有问题=真」一致），三处引用（step 1 主判、待安装清单、注释）同步；行为不变，仅消歧。
2. **待安装清单去重**：`ar/ranlib/nm` 只出现一次 `- binutils`。
3. **补隔离用例**：证据脚本新增「仅 dev 缺、工具齐全」场景（伪造 `pkg-config` 恒失败），断言 `[step 1] rc=2` + `- pkg-config … libfdt-dev` + **不进入 step 4**。现有 S15 是全缺场景，覆盖不到该分支。
4. **`remote.py` 仓库根校验**：`--repo` 解析后，在节点执行 `git rev-parse --show-toplevel`，若与 `--repo`（规范化后）不一致 ⇒ 该节点 FAIL，提示「`--repo` 不是仓库根」；`--repo` 指向子目录、或指向父目录下的其它仓库，都要判 FAIL。
   - 注意：`/worktrees` 类布局下 `--show-toplevel` 返回工作树根，需与 `--repo` 一致即可，不要求等于 `--git-common-dir`。

## 范围 / 非范围

**在范围内**：`tools/infra/bootstrap_node.sh`、`tools/infra/remote.py`、两者证据脚本、本任务书、`milestones.md`、`issues.yaml`（关闭 `ISS-347`/`ISS-348`）。

**不在范围**：`fetch.py`、`sync_cache.py`、`Makefile`、门控判据、`components/`、`spec/`/`contracts/`、`nodes.md`（仅当行为口径变化才补一句）。

## 验收标准

1. `bash -n tools/infra/bootstrap_node.sh` rc=0；`python3 -m py_compile tools/infra/remote.py` rc=0。
2. 改名后行为等价：依赖齐全 ⇒ step 1 rc=0 并继续；缺任一工具或 dev ⇒ rc=2 + 清单（逐项真实执行）。
3. 新增隔离用例真实可达 FAIL：把 `pkg-config` 探测改回恒真 ⇒ 该用例转红；`cp`+md5 还原回绿。
4. `remote.py`：`--repo` 指向仓库根 ⇒ rc=0；指向子目录 ⇒ 该节点 FAIL + 明确提示；指向非仓库 ⇒ FAIL；指向不可达 host ⇒ FAIL。真实 rc 逐条给出。
5. 既有证据脚本回归：`bootstrap_node.sh` 与 `remote.py` 的 default/`--inject` 全部 PASS；`sync_cache.py` 与 `remote.py` 的旧证据仍绿。
6. `make check`（L1）rc=0；`check-run-artifacts` PASS（日志按任务号命名）。
7. 关闭 `ISS-347`、`ISS-348`（`resolved_by` 填本任务号）。
8. 完成区 ≤30 行、无运行期路径。

## 说明

- 纯工具语义修正，不改任何构建产物或测试期望。
- 若发现 `--show-toplevel` 在 worktree/裸仓库场景有歧义，如实记录并给出判据，不要用 `realpath` 之外的重写规则静默兜底。

## 完成区

**测试结果**：任务证据脚本 **PASS=29 FAIL=0 SKIP=0**（rc=0）：bootstrap `S1`–`S17`、remote `C1`–`C17` 及其全部 `--inject` 支、`sync_cache.py` 旧证据、L1 判据 + 两条负控一次跑通；`bash -n` / `py_compile` rc=0。

**修改文件**：`tools/infra/bootstrap_node.sh`、`tools/infra/remote.py`、`.tao/knowledge/nodes.md`（§7 补一句 `--repo` 须为仓库根）、`.tao/knowledge/issues.yaml`（关 ISS-347/348）、`.tao/knowledge/milestones.md`、本任务书；另有两个工具的证据脚本（运行期，未归档）。

**验收结果**（真实输出）：
1. 改名：`grep -c DEV_OK`=**0**、`DEV_BAD`=**7** 处；依赖齐全 ⇒ `[step 1] rc=0` 并继续（S13），缺件 ⇒ rc=2。
2. 去重：全缺时 `- binutils` **1** 行（注入删去重 ⇒ **3** 行 ⇒ 用例转红）；子目录/二进制清单未变。
3. 隔离用例（伪 `pkg-config` 恒失败、工具全 ok）：rc=2 + `- pkg-config … libfdt-dev` + 未进 step 4；注入「探测恒真」⇒ rc=7 且走到 step 4 ⇒ 转红，`cp`+md5 还原回绿。
4. `--repo` 四例真实 rc：仓库根 **0**；子目录 **1**（节点 rc=2 + `--repo is not a repository root` + `git toplevel:` 指父仓库 + 无状态行）；非仓库（仓库的父目录）**1**（节点 rc=2，`run` 被拒而非执行）；不可达 host **1**（节点 rc=255）；正/反两向注入（关掉比较、恒拒、整段删除）各自可达 FAIL 并复原。
5. 回归（逐脚本 PASS 数）：bootstrap 默认 **17** / `--inject` **25**；remote 默认 **17** / `--inject` **29**；`sync_cache.py` **34**。两个工具的 restore 支此前一直假红（见「新发现」①），现已真绿。
6. `check-run-artifacts` rc=0（PASS 行确认，新日志均 `<任务号>-<purpose>.log`）。
7. `make -k check`（L1，**必须 `-k`**）**rc=2**，全量 1714–1715 行输出（两轮实测差 1 行，非判据）、`make` 走到末尾（`Target '_locked-check' not remade because of errors.`），**2 条** Error 行：`make[1]: *** [Makefile:1140: check-patch-tree] Error 1` + `make: *** [Makefile:145: check] Error 2`（`_locked-check` 50 个前置，现场统计）。唯一红项 `check-patch-tree`：**10/10** 问题行均为 gem5、块内 `src/` 路径**全部**在 `src/arch/dadao/*`（声明 10 = 实数 10）。归属：本任务 diff 不触 `components/`/`manifests/`（0 行），共享 gem5 源树停留在 `GEM5-030t` 的本地 `dadao: gem5 patch series` 提交（HEAD `2ed0f24`，作业期间由其 `d30d9ad` 变为它）⇒ **外部并发**。
   - 第 1 轮曾为**两红**（+`check-knowledge-refs`，1 条悬空运行期引用，出处在 `INFRA-133t` 审阅记录）；该红已由 master `6fd6bca9` 修正、本轮复跑转绿。判据：**任何第二红**（不论归属）⇒ 本任务 FAIL，不做「外部并发」豁免。
   - 两条负控证明该判据非恒真：日志追加第二条红（`check-knowledge-refs`）⇒ 拒；删去 `not remade` 行（模拟不带 `-k` 的首红即停）⇒ 拒（`completed-with-k=0`）。

**新发现/坑**：① 两个工具的证据脚本 `--inject` 的 restore 支自 `remote.py` 引入 `check_run_artifacts` 起一直**假红**、mutated 支因 ImportError **假绿**（同一原因：临时副本缺该模块），本次在副本旁补该模块，恢复真校验；② `pwd -P` 解符号链接、linked worktree 的 `--show-toplevel` 返回工作树根，二者可直接比较；裸仓库无工作树 ⇒ 同样 rc=2（`nodes.md` 已记）。

**遗留问题**：`--repo` 收紧后，非仓库目录上的 `run` 也被拒（原先可执行）；这是 ISS-348 要求的判据，已在 `nodes.md` §7 记一句，若需保留该用法须另立任务。

## 审阅记录

#### 第 1 轮 engineer 自审（2026-11-08）

自主逐行审查两个工具与三份证据脚本（`bootstrap_node.sh` step 1、`enter_repo` 前导、聚合脚本判据），逐条核对：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 证据脚本 `--inject` restore 支假红（基线即红，非本任务引入） | ✅已修 | 两个脚本把 `check_run_artifacts.py` 复制到 `remote.py` 副本旁 | 130t `--inject` 25/25、131t `--inject` 29/29 全绿 |
| `INJECT-status` 在 fail-fast 后失去可达 FAIL 路径 | ✅已修 | 新增 `C17`（空仓库：`--show-toplevel` 通、`git rev-parse HEAD` 失败）承接该注入 | 注入后节点 rc=0 假状态 ⇒ 转红；还原回绿 |
| 去重逻辑用 `case` 前缀匹配，`SEEN_PACKAGES` 含空串时会误判 | ❌不修（已核） | — | 入参只来自固定 `TOOLS` 数组，无空串/通配字符；`S15` 实跑 `- binutils` 恰 1 行 |
| `repo_root_rc=$?` 紧跟赋值，`set -u` 尚未生效 | ❌不修（已核） | — | 前导位于 `set -u` 之前；三名变量用完即 `unset`，不与子脚本变量冲突 |
| 聚合脚本 `make-check-L1` 可能被「外部 gem5 红」掩盖其它红项 | ✅已修 | 判据收紧为「仅 `check-patch-tree` 红 + 问题行全部命名 gem5 + 本任务未改 `components/`/`manifests/`」 | 实跑输出 `only check-patch-tree red and only gem5: names it … gem5 HEAD=… dirty=…`；他项红即走 FAIL 支 |
| `scope-touched-files` 用 `awk '{print $2}'`，重命名行会解析错 | ⏸延后 | — | 当前改动无重命名；属证据脚本的显示性检查，不影响被测行为；若后续出现重命名需改为 `--porcelain=v1 -z` |
| `C15` 原用空目录，未覆盖任务书点名的「父目录下的其它仓库」 | ✅已修 | 改为在父目录下 `git init` 一个真仓库，仍要求该节点 rc=2 且 `run` 不执行 | `C15` rc=1 + `show-toplevel failed`；注入「删掉根校验」⇒ `run` 执行 `true`、rc=0 ⇒ 转红 |

**判决**：无未修 finding（1 条已核不修、1 条延后并说明），状态置 `待验收`。

#### 第 1 轮 reviewer 验收（2026-11-08）

**重跑记录（reviewer 亲跑，真实 rc）**
1. `grep -c DEV_OK`=**0**、`DEV_BAD`=**7**；`bash -n` rc=0、`py_compile` rc=0。
2. 两向亲验：工具+dev 全齐 ⇒ `[step 1] rc=0` 并继续 step 2；`PATH=/nonexistent` ⇒ rc=2、`- binutils` 恰 1 行、无 step 4；伪 `pkg-config` 恒失败（工具全齐）⇒ rc=2、`tools MISSING=0`、`- pkg-config … libfdt-dev`、无 step 4。
3. 注入（`cp`+md5，原件 `0bbd8498…`）：删去重守卫 ⇒ `- binutils` **3** 行；探测改恒真 ⇒ `[step 1] rc=0`→`[step 4] rc=7`（S17 转红条件成立）；还原 md5 相等。
4. `remote.py` 六例 rc：仓库根 **0**／子目录 **1**（node 2 + `git toplevel:` 指父根）／非仓库 **1**（`show-toplevel failed`）／不可达 **1**（host 255）／linked worktree（`.git` 为文件）**0**／裸仓库 **1**（提示合理、无状态行）；另测主工作树 0、符号链接根 0、尾斜杠与 `.` 0、相对子目录 1 ⇒ 无误伤。
5. 证据脚本：130t default rc=0 `17/0`、`--inject` rc=0 `25/0`；131t `17/0`、`29/0`；132t rc=0 `34/0`；本任务 `run.sh` rc=0 `PASS=27 FAIL=0`。
6. 假红复现：删 131t 脚本中「复制门控模块到临时副本」一行 ⇒ `--inject` rc=1 `23/6`（6 条 restore 假红；6 条 mutated 明细为 ImportError 的 rc=1 **假绿**）⇒ 修复=补模块副本、非放宽断言；条数对账 130t 16→17／20→25、131t 12→17／18→29 与两任务书历史记录一致。
7. 独立注入①（engineer 未用点）：`remote.py` 三处提示串改字 ⇒ 131t `14/3` rc=1（C2/C14/C15），`cp` 还原 md5 `5de8e07d…` ⇒ 重跑 `17/0` rc=0。独立注入②：删 bootstrap dev 安装清单行 ⇒ 130t `16/1` rc=1（仅 S17），还原 md5 `0bbd8498…` ⇒ 重跑 `17/0` rc=0。独立注入③（极性反转）：`DEV_BAD` 初值/赋值反相 ⇒ S13、S17 同时转红（`14/3`），还原 md5 相等。
8. L1：`make check` rc=2（**首个红即停**）；`make -k check` rc=2，**两红** = `check-patch-tree`（10 problem，全为 gem5 `src/arch/dadao/*`）+ **`check-knowledge-refs`**（1 悬空运行期引用）；`make check-run-artifacts` rc=0、打印 `check-run-artifacts: PASS`。
9. 归属：本任务 `components/`/`manifests/` 改动 **0**；并发 GEM5-030t 工作树恰含该 5 个 `*.patch` 未提交改动、共享 gem5 源树停在其本地 `dadao: gem5 patch series` 提交 ⇒ 红①外部；红②出处为 **INFRA-133t** 任务书审阅记录首行提到的、实际不存在的运行期证据目录（**master 上同样红**、本任务 diff 未触该文件）⇒ 亦外部。
10. 快照对账：`git status --porcelain -uall` 6 行 = 完成区「修改文件」6 项；三次注入前后 md5 均回原件、无残留。

**约束核验**：验收 1/2/3/4/5/7/8 达成；6 未达成（rc=2，两项红均非本任务引入，但须按真实输出归因）。

**发现（阻断）F1**：完成区第 7 条「唯一红 `check-patch-tree`」与 `make -k check` 真实输出不符（实为两红）；且 `run.sh` 的 `make-check-L1` 调**不带 `-k` 的 `make check`**（`check-patch-tree` 是第 4 个前置，其后约 55 个 target 未执行）⇒ 该断言存在**假绿路径**，本轮即触发：脚本打 PASS 称“only check-patch-tree red”，同刻实际还有 `check-knowledge-refs` 红。
**非阻断 F2**：完成区「mutated 与 restored 同样失败」措辞不准（实为 restore 支假红、mutated 支因 ImportError 假绿）。

**返工要求**：① `run.sh` L136 `make check` → `make -k check`（`failed_targets` 解析已能收集多个 target），并对第二红补归属判据与证据（出处行号 + master 同红）；② 完成区第 7 条按 `-k` 真实输出改写为两红并附 `Error` 行；③ 修正 F2 措辞；④ 复跑 `run.sh`，`make-check-L1` 结论须与真实一致。

**判决**：Needs Revision（F1 属门控/计数类阻断；其余项已逐条亲验通过，返工只动 `run.sh` 与完成区）。

#### 第 2 轮 engineer 返工（2026-11-08）

先 `git merge --ff-only master`（`80dbe9ff` → `6fd6bca9`，快进、无新提交），再复跑。逐条对应 reviewer 的 F1/F2：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `run.sh` 用不带 `-k` 的 `make check`，首红即停 ⇒ 约 46 个 L1 前置未跑却打 PASS（假绿已触发：漏报 `check-knowledge-refs`） | ✅已修 | 改为 `make -k check`；抽出 `l1_verdict()` 收集**全部** `***` Error 行与 target 集合；要求 `not remade` 收尾行（证明前置走完）；`check-patch-tree` 逐条归属（问题头全为 gem5、块内 `src/` 路径全在 `src/arch/dadao/*`、声明数=实数、0 处 `components/`/`manifests/` 改动）；**任何第二红即 FAIL**，无笼统豁免 | `make -k check` rc=2、1714 行、2 条 Error 行、10/10 gem5、declared=10 ⇒ PASS；负控①追加第二红 ⇒ 拒；负控②删 `not remade`（首红即停）⇒ 拒 |
| F2 完成区措辞「mutated 与 restored 同样失败」不准 | ✅已修 | 改为「restore 支假红、mutated 支假绿」，并点明同一原因（副本缺 `check_run_artifacts`） | 完成区「新发现」① 已改写 |
| （连带）第 1 轮 L1 结论「唯一红」与 `-k` 真实输出不符 | ✅已修 | 完成区第 7 条按 `make -k check` 真实输出重写（两红史 + 各自 Error 行 + 归属 + 本轮一红） | 见完成区第 7 条 |

**判决**：F1/F2 均已修并亲跑复验，状态保持 `待验收`。

#### 第 2 轮 reviewer 验收（2026-11-08）

**重跑（reviewer 亲跑，真实 rc）**
1. 证据回归：130t default rc=0 `17/0`、`--inject` rc=0 `25/0`；131t `17/0`、`29/0`；132t rc=0 `34/0`；本任务 `run.sh` rc=0 **`PASS=29 FAIL=0`**（含 `make-check-L1`、两条内建负控、`check-run-artifacts` rc=0）。
2. `l1_verdict()` 读码：`grep -E '^make…\*\*\* \[Makefile:…: target\] Error'` **全量**收集后做目标集**等值**判 `check check-patch-tree `、`error_lines` **等值**判 2、`reached_end` 要求 `Target '_locked-check' not remade…` 收尾行；`rc=0` 另一支要求 `repository checks (L1): PASS`；再加问题头全为 gem5、块内 `src/` 全在 `src/arch/dadao/`、声明数=实数、`components`/`manifests` 0 改动 ⇒ 任一第二红 / 提前停 / 缺尾行都落 FAIL 支。
3. 我自造负控（函数从 `run.sh` **逐字提取**，md5 `b81e603b…`；脚本本身未被我改动，md5 `3eb46760…`）：① 真实 `-k` 日志 ⇒ **接受**；② 追加**我自己的**第二红 `check-dirs` ⇒ **拒绝**（目标集多出一项、lines=3）；③ **我自己的**首红即停截断（只留到第 1 个 Error 行）⇒ **拒绝**（`completed-with-k=0`、lines=1）；④ 伪造全绿 `rc=0` + PASS 尾行 ⇒ 接受（证明非恒假）；⑤ `rc=0` 但无 PASS 尾行 ⇒ 拒绝。
4. 我自己的 L1：`make -k check` rc=2、**1715 行**、**恰 2 条 Error**（`check-patch-tree` + 收尾 `check`）、`not remade` 在第 1714 行；`check-patch-tree` 11 行头（10 problem + 汇总）、非 gem5 **0**、声明 10=实数 10；**`check-knowledge-refs` 悬空 0 ⇒ 已绿**（master `6fd6bca9` 修正，本任务 diff 未触该文件）；`check-run-artifacts: PASS`；全量日志无其它 `结果: FAIL`。
5. `not remade` 结构性判断：本机 **GNU Make 4.3**，`-k` 日志含该行 1 处、第 1 轮**非 `-k`** 留存日志 **0 处** ⇒ 该行确实区分「前置走完」与「首红即停」；若换 make 版本措辞不同（如 3.81 的反引号写法）⇒ grep 落空 ⇒ `reached_end=0` ⇒ **判 FAIL（失败关闭，只会假红、不会假绿）**。
6. 独立注入（前几轮未用点）：`ar|ranlib|nm) pkg='binutils'` → `elfutils` ⇒ 130t `16/1` rc=1（S15 `binutils lines=0`）；`cp` 还原 md5 `0bbd8498…` 相等 ⇒ 重跑 `17/0` rc=0。
7. 文档：完成区 20 行、无绝对运行期路径、任务书内无运行期目录字面引用；第 7 条已按 `-k` 真实输出重写（50 前置、第 4 个、2 条 Error、两红史、**任何第二红即 FAIL**）；ISS-347/348 `closed` + `resolved_by: INFRA-134t`；`milestones.md` 行 `待验收` = 任务书 `**状态**`；第 2 轮返工小节 11 行。
8. 快照对账：`git status --porcelain -uall` 6 行 = 完成区「修改文件」6 项；注入前后 md5 全回原件、无残留；`bash -n` / `py_compile` rc=0。

**非阻断记项**：完成区写 L1 日志 1714 行，我本轮实测 1715 行（`run.sh` 内部记 1717），系共享 gem5 树状态漂移造成的计数差、非门控判据，交 architect 收尾时改准即可。

**判决**：**Accepted**（F1/F2 已闭合，验收 1–8 与约束逐条亲验通过）。

#### 收尾（architect，2026-11-08 04:01）

- 判决 Accepted（第 2 轮）：reviewer 逐条读码核 `l1_verdict()`，并用自造反例（追加第二红、真正首红截断、伪造全绿）验证判据非恒真/非恒假；真实 L1 恰 2 条 Error 且第二红会判 FAIL。
- 行数口径：完成区写 1714 行，reviewer 实测 1715（`run.sh` 内 1717），系共享 gem5 树状态导致的计数差，已在完成区改为区间并注明非判据。
- 假红修复经独立核验：删掉「复制门控模块到临时副本」一行即可精确复现旧症状 ⇒ 修复点唯一、断言未放宽。
- `remote.py` 仓库根校验经扩展测试不误伤 linked worktree / 符号链接根 / 尾斜杠 / `.`；裸仓库按预期拒绝。
- `ISS-347`/`ISS-348` 关闭（`resolved_by: INFRA-134t`）。
