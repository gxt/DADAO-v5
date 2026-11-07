# INFRA-130t: 节点引导脚本与远程派单脚本

**模块**：infra
**项目里程碑**：M11
**依赖**：无（与 `GEM5-030t` 文件域不重叠）
**状态**：待开始

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
