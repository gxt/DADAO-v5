# INFRA-130t: 节点引导脚本与远程派单脚本

**模块**：infra
**项目里程碑**：M11
**依赖**：无（与 `GEM5-030t` 文件域不重叠）
**状态**：已验证

## 背景与事实

本轮新增两台 64C/128G 构建节点，用途是与主控机分担 LLVM/QEMU/gem5 构建与 tset 全量测试。首次初始化是**手工逐条 ssh 命令**完成的，过程中连踩四个坑，全部无脚本可复用：

1. 节点缺 `git config --global user.name/user.email` ⇒ `apply-series` 末尾 `git commit` 退出 128。
2. `install-host` **不会**自动 `apply-series`；跳过时 CMake 报 `The target 'DADAO' is not a core tier target`（LLVM 源树是未打补丁的上游 commit）。
3. `compiler-rt` builtins 构建树需**一次性手工配置**，且必须显式给 `-DCMAKE_C_COMPILER_TARGET=dadao-unknown-elf` / `-DCMAKE_CXX_COMPILER_TARGET=dadao-unknown-elf`，否则 `COMPILER_RT_DEFAULT_TARGET_ONLY=ON` 时报 `CMAKE_C_COMPILER_TARGET must also be set`。
4. 节点访问 GitHub 不稳定（`curl 28` / `GnuTLS recv error`）⇒ 仓库用 bundle 同步、组件用本地裸仓库 `.cache/*.git`，不能依赖 `git clone` 直连。

此外目前**没有任何跨机派单手段**：要在两台节点上跑同一批构建/测试，只能人工开两个 ssh 会话、手工汇总结果，无法做「同 commit、同门控、双机结果对比」。

节点主机名/IP、账号等属**运行期信息，不入库**：脚本只接受命令行参数或环境变量提供的节点清单。

## 目标

新增两个脚本，把「新节点从零到 `make check` 绿」和「向多节点派单/取回结果」固化为可复用命令。

### 1. `tools/infra/bootstrap_node.sh`

幂等引导一台新节点，步骤固定为：

1. 预检并报告：`git` / `cmake` / `ninja` / `scons` / `ccache` / `bison` / `flex` / `python3` / 必要 `-dev` 包；缺失时打印**待安装清单**并退出非零（是否安装由调用者决定，脚本不擅自 `apt install`）。
2. 配置 git 身份（已配置则跳过；值由参数或环境变量提供，不写死）。
3. 仓库同步：接受「本地 bundle 路径」或「已有仓库路径」作为输入；不接受直连 GitHub 作为唯一路径。
4. `make fetch`（走本地 `.cache/*.git`）。
5. **`make apply-series` 必须早于 `make install-host`**（坑 2），失败即停。
6. **compiler-rt 构建树**：若未配置，用与仓库主构建树一致的参数一次性 configure（含坑 3 的两个 `*_COMPILER_TARGET`），参数集中在脚本内一处常量。
7. `make install-host`，然后 `make check`，输出末尾各步 rc。

要求：每步打印 `[step N] ...` + `rc=`；任一步失败立即停并打印失败现场（最近 40 行日志）；`--dry-run` 只打印将执行的命令。

### 2. `tools/infra/remote.py`

子命令（`argparse`，风格与 `tools/infra/` 现有脚本一致，纯标准库）：

- `status`：对每个节点报告仓库 commit、工作树是否干净、`clang`/`qemu-dadao` 版本、磁盘/内存余量。
- `preflight`：检查各节点是否满足跑门控的前置（工具链三件套存在、`.cache` 非空、`apply-series` 后的源树 clean+base+1），输出逐节点 PASS/FAIL 与失败原因。
- `run`：在指定节点上跑一条**只读或幂等**命令（如 `make check` / 单个 check target），并发执行、每节点落一份日志、末尾汇总 `host -> rc`；任一非零则整体非零。
- `collect`：把各节点指定目录下的产物取回本地一个目录（按 host 分子目录），用于双机结果对比。

节点清单来源优先级：`--hosts a,b` > 环境变量 `DADAO_NODES` > 仓库内**不存在**的默认（即必须有输入，否则报错说明）。ssh 一律 `-o BatchMode=yes`，失败即报该 host 失败，不静默跳过。

## 范围 / 非范围

**在范围内**：`tools/infra/bootstrap_node.sh`、`tools/infra/remote.py`、本任务书、`milestones.md`。

**不在范围**：`Makefile` 目标、门控脚本、`AGENTS.md`、节点上的实际部署与安装、任何 `components/`、`spec/`、`contracts/`。

## 验收标准

1. **`bash -n tools/infra/bootstrap_node.sh` rc=0**；`--dry-run` 输出含 `apply-series` 且其行号早于 `install-host`，并含两个 `CMAKE_*_COMPILER_TARGET`。
2. **`python3 tools/infra/remote.py --help`、四个子命令各 `--help`** rc=0。
3. **无节点可用时不假绿**：`remote.py status` 不给节点清单 ⇒ rc≠0 且提示如何提供；给一个不可达 host ⇒ 该 host 报 FAIL、汇总 rc≠0。
4. **本机自测**（把本机当单节点，`--hosts` 指向 localhost 或直接跑脚本的本地路径分支）：`status` 报出真实 commit、`qemu-dadao --version`；`run -- make check` 或 `run -- ./tools/infra/check_issues.py` 能拿到真实 rc 并落日志；`collect` 能取回一个已存在的小文件。
5. **失败路径可达**：对 `run` 注入一个 `exit 3` 的命令 ⇒ 该 host rc=3、整体 rc≠0（留存真实输出）；对 `collect` 指向不存在目录 ⇒ 该 host 报错、整体 rc≠0。
6. `make check`（L1）rc=0（本任务不改门控与文档引用，应无新增红）。
7. 完成区 ≤30 行、无运行期路径（节点 IP/主机名/日志绝对路径一律不写）。

## 说明

- 本任务只交付**脚本**；用它在两台节点上再跑一遍完整引导属后续运维动作，不在验收范围。
- 脚本不写死任何主机名/IP/账号；密钥与 known_hosts 由调用环境负责。
- 若实现中发现某步无法幂等（例如 `apply-series` 在已打过补丁的源树上行为），如实记录并给出调用前提，不要用 `git reset --hard` 静默兜底。

## 完成区

**测试结果**：运行期证据脚本 default **16 PASS / 0 FAIL（rc=0）**、`--inject` **20 PASS / 0 FAIL**（缺 target、去 BatchMode 均真实转红后还原回绿）；L1 `make -k check` rc=2，仅 `check-patch-tree` 红（外部并发 `GEM5-030t`），`check-run-artifacts` 本轮 **PASS**，其余 target 全绿。
**修改文件**：① 新 `tools/infra/bootstrap_node.sh`；② 新 `tools/infra/remote.py`；③ `.tao/knowledge/milestones.md`（INFRA-130t 行）；④ 本任务书（状态、完成区、自审）。
**验收结果**：
1. `bash -n` rc=0；`--dry-run` rc=0，`make apply-series` 行号 **13** < `make install-host` 行号 **21**，含 `-DCMAKE_C_COMPILER_TARGET=dadao-unknown-elf` 与 `-DCMAKE_CXX_COMPILER_TARGET=dadao-unknown-elf` 各 1 处。
2. `remote.py --help` 与四子命令 `--help` 均 rc=0。
3. 无节点清单：rc=2 且提示 `--hosts`/`DADAO_NODES`；不可达占位主机：该 host rc=255、汇总 rc=1。
4. 本机自测走 **`--local` 本地路径分支**（ssh 到 localhost 因 known_hosts 校验失败，属调用环境职责）：`status` rc=0，commit=`c8f772aa…`、`qemu-dadao version 11.1.1`；`run -- python3 tools/infra/check_issues.py` rc=0 且落每节点日志；`collect` 取回小文件 rc=0。
5. 失败路径真实可达：`run -- sh -c 'exit 3'` 该 host rc=3、整体 rc=1；`collect` 指向不存在目录该 host rc=2、整体 rc=1（日志含 `remote directory not found`）。
6. 引导失败即停：依赖齐全时 `[step 1] rc=0` 并进入后续步骤；PATH 置空伪造缺依赖 ⇒ `[step 1] rc=2` + 待安装清单且不进入 step 4；注入 rc=7 的 make ⇒ `[step 4] rc=7` + 最近 40 行；缺 git 身份 ⇒ rc=2 且给出参数/环境变量提示。
7. 本区 ≤30 行；两脚本无 IP/主机名/账号/绝对路径字面量（证据脚本 S12 现场 grep）。
**新发现/坑**：① 新节点上 `install-host` 无法自举 compiler-rt：`build-builtins` 需已配置的构建树，故 step 6 在缺 build-tree clang 时先 `make build-mc build-lld`（仍严格早于 install-host）。② 运行期日志名必须带任务号（`INFRA-130t-…`），否则 L1 `check-run-artifacts` A3 判非法；`.EXIT` 后缀亦非法。③ `remote.py` 并发时不可把 host 写进共享 args（已改为显式传参，4 节点并发实测日志互不串）。④ 证据临时树不得落在仓库内（本 worktree 位于仓库外的任务目录，改用同级独立临时目录）。⑤ 预检汇总标志须用「问题标志」（0=正常、1=有问题）；libfdt 探针须 `<libfdt.h>`（`<fdt.h>` 缺 `fdt32_t` 定义恒失败）。
**遗留问题**：① 按任务书「说明」，未在两台真实节点上跑完整引导，仅交付脚本与失败路径证据；② L1 仅 `check-patch-tree` 红，归外部并发 `GEM5-030t`：共享 gem5 源树 HEAD 内容不等于本工作树 `components/gem5/patches`（`GEM5-030t` 工作树内 5 个 `.patch` 未提交），本任务未改 gem5/门控。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 并发 fan-out 把 host 写在共享 `args.host`，线程间可串号 | ✅已修 | `build_shell/run_node` 显式接收 host | 4 节点 `--local` 并发，4 份日志各 1 条 `done`，汇总 4×rc=0 |
| F2 默认日志名不含任务号，L1 `check-run-artifacts` A3 判非法 | ✅已修 | bootstrap/remote 日志统一 `INFRA-130t-` 前缀 | `check_run_artifacts.py` 复跑仅剩外部 `GEM5-030t-baseline.EXIT` 1 条 |
| F3 证据临时树落在本 worktree 内，污染 `git status` | ✅已修 | 证据脚本 `TMP` 移到同级 `-tmp` 目录 | `git status --porcelain -uall` 仅两新脚本 |
| F4 `--help` 在首个空行截断，不显示 Options | ✅已修 | usage 改为 awk 至 `set -uo pipefail` | `-h` 输出含 Usage/Options 全部条目 |
| F5 新节点无 build-tree clang 时 compiler-rt configure 必失败 | ✅已修 | step 6 先 `make build-mc build-lld`，仍早于 install-host | dry-run 行号 13 < 21；S13 注入在 step 4 正确停 |
| F6 首版 `collect` 失败日志误显 rc=0 | ❌不修（非缺陷） | 复核为读取到上一轮同秒旧文件；新日志写入 rc=2 正确 | 删旧日志复跑，S11 日志 `# rc: 2` 且含错误原文 |

判决：F1–F5 已修并复验，F6 复核为非缺陷；无未修缺陷 ⇒ 状态置「待验收」。

### 第 1 轮 reviewer 验收（2026-11-07，全部自跑）

**重跑记录（真实输出/退出码）**
1. `bash -n` rc=0；`--dry-run` rc=0，`make … apply-series` 行 **13** < `make … install-host` 行 **21**，`-DCMAKE_C_COMPILER_TARGET`/`-DCMAKE_CXX_COMPILER_TARGET=dadao-unknown-elf` 各 1 处。
2. `remote.py --help` + status/preflight/run/collect 四个 `--help` 全 rc=0；无子命令 rc=2。
3. 无节点清单（`env -u DADAO_NODES … status --repo .`）→ rc=2，`no nodes given; pass --hosts a,b (or set DADAO_NODES)`；`DADAO_NODES=x` 路径可走通（rc=1，因 host 不可达）。
4. 不可达 host → `badhost.invalid -> 255 (FAIL)`、`overall rc=1`、整体 rc=1（不静默跳过）。
5. `run --local -- sh -c 'exit 3'` → host rc=3、整体 rc=1；`collect` 指不存在目录 → host rc=2、整体 rc=1，日志含 `remote directory not found`。
6. 成功路径：`status --local` rc=0，`commit=c8f772aae588…`、`qemu-dadao version 11.1.1`；`run -- python3 tools/infra/check_issues.py` rc=0，日志真值 `check_issues: 2 open, 5 closed`；`collect` 取回小文件 rc=0 内容一致。
7. engineer 证据脚本：default **14 PASS/0 FAIL rc=0**；`--inject` **18 PASS/0 FAIL rc=0**（与完成区逐条对齐）。
8. **reviewer 独立注入**（未用 engineer 注入点）：把 `remote.py::summarize` 的 `return worst` 改为 `return 0` ⇒ 脚本 `11 PASS / 3 FAIL` rc=1（S5/S9/S11 转红）；`cp` 备份 + md5 还原 `c15340b814a1dbca996c7788a6fdcf1c` 相等 ⇒ 重跑 `14 PASS/0 FAIL` rc=0。
9. bootstrap 失败即停（自建无 Makefile 仓库）→ rc=2、`[step 4] rc=2` + 最近 40 行；证据 S13 fake-make → rc=7 + tail。
10. L1 `make -k check` → **rc=2**，唯一红 `check-patch-tree`（10 problem）；`check-run-artifacts` 本轮 PASS。
11. 归属：不含本任务改动的干净 master 树跑 `check_patch_tree.py` → rc=1，输出与本任务树**逐字节相同**；三树 `.work/source/gem5` 指同一路径、GEM5-030t 5 个 `.patch` 未提交 ⇒ 外部并发，不判本任务失败。
12. 快照对账：审前/审后 `git status --porcelain -uall` 同为 2 改 2 增，四文件 md5 不变。

**阻断发现（Needs Revision 根因）**
- **F-REV1 `bootstrap_node.sh` step 1 判据反了**（两处 `[ "$DEV_OK" -ne 0 ]`，行 211/222）：本机实测 `dev libfdt: MISSING` 却打 `[step 1] rc=0` 继续往下（违任务书「缺失→退出非零」）；用恒成功 `cc` 让探测全通过反而 `[step 1] rc=2` + 虚假「待安装清单」⇒ 全就绪节点被直接拒绝，引导不可用。证据脚本 S1–S14 **无一覆盖 step 1**，故 14/18 全绿未暴露（覆盖缺口）。
- **F-REV2 探针错**：`#include <fdt.h>` 单独 include 恒编译失败（本机已装 libfdt-dev 仍 rc=1），应为 `#include <libfdt.h>`（本机 rc=0）；只修 F-REV1 不修探针会让每台就绪节点 exit 2。
- **建议最小修正**：两处 `-ne 0`→`-eq 0`、探针改 `libfdt.h`，证据脚本补两条可达 FAIL（全就绪 ⇒ step1 rc=0；缺 dev ⇒ step1 rc=2 且列包）。已在**临时副本**验证：全就绪 step1 rc=0、伪造 dev 缺失 step1 rc=2 并列 `- pkg-config … libfdt-dev`；被测产物 md5 未变。
- 非阻断 finding：① `status` 的 `dirty_files` 少计 1（`printf | wc -l` 丢尾行，实测 4 变更报 3）；② 完成区称 L1 两红，本轮 `check-run-artifacts` 已绿（在飞 embench 产物补齐，时序差异）；③ 证据 `INJECT-batchmode` 只验变异已应用、未走 FAIL 判定，建议改对变异副本跑 S12。

**约束核验**：两脚本无 IP/主机名/账号/家目录/绝对路径字面量（多组 grep 全空）；节点清单只来自 `--hosts`/`DADAO_NODES`，缺失 rc=2 并给提示；完成区 16 行 ≤30 且无运行期路径；milestones 与任务书状态一致（待验收）；改动仅 4 文件未越界；本轮未 commit/push、注入用 cp+md5 还原。

**判决：Needs Revision** —— 指名失败项 F-REV1/F-REV2（代码行为 vs 任务书 step 1）+ 证据脚本 step 1 覆盖缺口；其余 1–7 条验收与 L1 归属均通过。修后请重跑证据脚本与 L1。

### 第 2 轮 engineer 返工（reviewer Needs Revision）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F-REV1 step 1 判据反向：依赖全齐 rc=2、缺依赖 rc=0 | ✅已修 | `DEV_OK` 改为问题标志（初值 0、有问题置 1），遗漏清单与待安装清单三处引用同步 | S13 依赖齐全 `[step 1] rc=0` 并进入 step 4；S15 `PATH` 置空 ⇒ `[step 1] rc=2` + 待安装清单且无 step 4 |
| F-REV1 证据未覆盖 step 1 两支 | ✅已修 | 新增 S15（缺依赖→rc=2）并把 S13 增加「依赖齐全→step 1 rc=0 继续」断言 | default 16 PASS / 0 FAIL |
| F-REV2 libfdt 探针 `#include <fdt.h>` 恒失败 | ✅已修 | 改为 `#include <libfdt.h>` | 本机 `dev libfdt: ok`；S13 rc=0 |
| N1 `dirty_files` 用 `printf '%s'`→`wc -l` 丢尾行 | ✅已修 | 非空时 `printf '%s\n'` 计数，空值显式 0 | S16 四个变更报 `dirty_files=4` |
| N2 `INJECT-batchmode` 只验变异已应用 | ✅已修 | 增加 fake ssh 捕获真实 argv 的 `batchmode_case`，变异后断言 argv 缺 `BatchMode=yes` | inject 20 PASS：变异 FAIL、`cp` 还原后 PASS |
| N3 完成区 L1 两红措辞过期 | ✅已修 | 按本轮实况改为仅 `check-patch-tree` 红 | `make -k check` 日志：check-run-artifacts PASS |

判决：F-REV1/F-REV2 与三条非阻断项全部已修并复验，无未修 finding ⇒ 保持「待验收」。

### 第 2 轮 reviewer 验收（2026-11-07，全部自跑）

**重跑记录（真实输出/退出码）**
1. step 1 代码直读：`DEV_OK` 初值 0、三处问题点置 1（glib/pixman/zlib、libfdt、cc 缺失）；行 211 主判与行 222 待装清单行同为 `-ne 0`，`MISSING` 分支独立 ⇒ **语义一致、无反逻辑**；探针已是 `#include <libfdt.h>`（本机 `dev libfdt: ok`）。
2. 方向 A（真实本机、依赖齐全）⇒ `[step 1] rc=0` 并进入 step 2/3/4（step4 rc=2 仅因测试仓无 Makefile，用以证明"继续"）。
3. 方向 B 三支均停在 step 1：B1 PATH 置空 ⇒ rc=2 + 完整清单（含 `- build-essential`）、step4 出现 **0** 次；B2 仅 dev 缺（伪 pkg-config 恒 1）⇒ rc=2 + `- pkg-config … libfdt-dev`、step4 **0** 次；B3 仅缺 bison/flex ⇒ rc=2 + `- bison` `- flex` 且**不**打印 dev 行。
4. `bash -n` rc=0；`--dry-run` rc=0，`apply-series` 行 **13** < `install-host` 行 **21**，两个 `CMAKE_*_COMPILER_TARGET=dadao-unknown-elf` 各 **1** 处。
5. 证据脚本自跑：default **16 PASS / 0 FAIL rc=0**；`--inject` **20 PASS / 0 FAIL rc=0**；主+四子命令 `--help` 全 rc=0（S3）。
6. `dirty_files` 亲验：合成仓 4 变更（porcelain 4 行）⇒ `dirty_files=4`；本任务真实 4 变更 ⇒ `dirty_files=4`。
7. `INJECT-batchmode` 确为行为断言：我另用 fake ssh 独立捕获真实 argv＝`-o / BatchMode=yes / -o / ConnectTimeout=10 / fakehost / cd . && …`（`BatchMode=yes` 独占行 1 条）；变异副本走 FAIL 支、`cp` 还原走 PASS 支。
8. **reviewer 第 2 轮独立注入**（换点，第 1 轮未用）：把 `remote.py` 的 `dirty_files` 回退为丢尾行写法 ⇒ **15 PASS / 1 FAIL**、S16 转红、rc=1；`cp`+md5 还原 `b0070890f41e1375d2f07c941db68eb4` 相等 ⇒ 重跑 **16 PASS / 0 FAIL** rc=0。
9. L1 `make -k check` → **rc=2**，45 个 check-* target，唯一 Error `check-patch-tree`（10 problem）；`check-run-artifacts: PASS`，无其它 Error 行。
10. 归属：不含本任务两脚本的干净 master 树跑 `check_patch_tree.py` → rc=1，输出与本任务树**逐字节相同**（11 行）；GEM5-030t 有 **5** 个未提交 `components/gem5/patches/*.patch`，本任务 `components/` 改动 **0** ⇒ 外部并发，不判本任务失败。
11. 快照对账：审前/审后 `git status --porcelain -uall` 同为 2 改 2 增；`bootstrap_node.sh`/`remote.py`/`run.sh`/`milestones.md` md5 与注入前一致（注入已清）。

**约束核验**：完成区 16 行 ≤30 且无运行期路径；milestones 与任务书状态同为「待验收」；两脚本复扫无 IP/主机名/账号/家目录/绝对路径字面量；改动仅 4 文件未越界；本轮未 commit/push，注入一律 `cp`+md5 还原（未用 git 还原）。

**非阻断 finding（建议，不重开一轮）**：① 变量名 `DEV_OK` 实为「问题标志」（0=正常），名实相反、易被后人改回反逻辑，建议改名 `DEV_BAD`；② 证据脚本缺「仅 dev 缺失、工具齐全」的隔离用例（S15 是全缺场景），该方向我已亲验正确，建议补一条；③ 全缺时清单 `- binutils` 重复 3 次（ar/ranlib/nm），建议去重（纯展示）。

**判决：Accepted** —— F-REV1/F-REV2 与三条非阻断项均经我自跑复验；step 1 两向判据、证据 16/20 真实 rc、独立注入转红→还原→回绿、L1 唯一红及其外部归属，全部由本人命令输出证实。

#### 收尾（architect，2026-11-07 21:11）

- 判决 Accepted（第 2 轮 reviewer 全自跑：step 1 两向判据、证据 16/20 真值、独立注入转红→还原→回绿、L1 唯一红归属外部）。
- F1（非阻断）：`DEV_OK` 实为「问题标志」，名实相反 ⇒ 登记 `ISS-347` 待改名，实施时须同步三处引用并复跑证据脚本。
- F2（非阻断）：证据缺「仅 dev 缺失、工具齐全」隔离用例；全缺清单 `- binutils` 重复 3 次 ⇒ 一并记入 `ISS-347`。
- 交付仅两个脚本（引导 8 步幂等 + 四子命令派单），脚本内无写死主机信息，节点清单只从 `--hosts`/`DADAO_NODES` 取。
