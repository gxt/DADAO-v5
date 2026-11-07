# nodes — 构建 / 测试节点台账

> **维护规则**：只记**可复用的口径与事实**（机型、角色、组网、软件包、就绪判据、已知坑），不写节点地址与登录凭据（用户 2026-11-07 裁定：只写主机名 + 角色，地址现场 `tailscale status` 查）。
> **新增节点**：先用 `tools/infra/bootstrap_node.sh` 引导，验收通过后在「清单」与「新增流程」补一行；不手工散跑命令（见「已知坑」）。

## 1. 当前清单

| 主机名 | 角色 | 状态 |
| --- | --- | --- |
| `tao-clab` | **主控机**：唯一装 OpenCode 的机器，会话 / 派单 / 合并都在这里 | 在用 |
| `server207` | 构建 / 测试节点（纯执行，不装 OpenCode） | 就绪 |
| `server208` | 构建 / 测试节点（纯执行，不装 OpenCode） | 就绪 |

- 节点**不跑 AI 会话**，只跑 `make` 目标与测试驱动；派单与结果汇总回主控机。
- 节点数量会继续增加；判据是「同一 commit 的 `make check` + `make check-inst` 结果与主控机一致」，不是「机器装好了」。

## 2. 硬件与系统（两台同构）

- **CPU**：4 路 Intel Xeon E7-4820，8 核 / 16 线程 × 4 = **64 vCPU**（2.0 GHz；NUMA 4 节点，每节点 16 个逻辑 CPU）
- **内存**：**128 GiB**（`free` 可见 125 GiB），日常可用 > 120 GiB
- **磁盘**：根分区 823 GiB，构建前可用约 **700 GiB**；两台都是单盘 `/dev/sda2`，无独立数据盘
- **OS**：Ubuntu **24.04.5 LTS**；内核 6.8.0-149 / 6.8.0-139（两台小版本不同，未影响构建）
- **权限**：`gxt` 账号，`sudo` 免密
- **没有 GPU**：本仓库当前构建/测试链路不依赖 GPU

判据含义：64 vCPU 支持 `JOBS=32`（单机一半核）稳定跑；128 GiB 内存使 LLVM/gem5 并行链接不触发 swap。

## 3. 组网（Tailscale）

- 三台（`tao-clab` + 两节点）**同属一个 tailnet**，`tailscale` 版本 **1.104.5**，服务 `tailscaled` 常驻。
- 节点的可达性由 tailnet 保证；**主控机与节点之间不要求直连**：`server207` 曾观测到 direct，`server208` 走 DERP 中继（当前中继点在 `nue`，即德国纽伦堡）。
- 含义：**DERP 走公网中继，延迟高、带宽有限** ⇒
  - 适合：小文件、日志、结果回传；
  - 不适合：大仓库 clone、组件 tarball 传输。故仓库用 **bundle + 内网 rsync**，组件用**本地裸仓库 cache**，不依赖公网直连。
- 免密登录只对 `gxt` 账号配置；所有跨机脚本一律 `ssh -o BatchMode=yes`（缺 key 时就地失败，不静默降级）。

## 4. 软件包安装情况

### 4.1 基础镜像已带（未动）

`apt-mark showmanual` 显示 **69** 个手动包，构建相关的主要有：`build-essential`、`clang`（系统版，备用）、`gcc-riscv64-*`、`bison`、`flex`、`cmake`、`bc`、`gdb`、`git`、`gh`、`catch2`、`cloc`、`docker.io`（**已装但未启用**，`systemctl is-active docker` = inactive）、`openjdk-17-jdk`、`r-base`、`texlive-*`、`gtkwave`、`srecord`、`ninja-build`、`scons`、`python3-*` 等。

即：**基础系统镜像已具备大部分依赖**，本轮只补了缺的几项。

### 4.2 本轮补装（一次性，两台相同）

`build-essential cmake ninja-build scons ccache git rsync curl wget ca-certificates bison flex gperf bc m4 pkg-config python3 python3-dev python3-pip python3-venv python3-yaml python-is-python3 zlib1g-dev libssl-dev libelf-dev libglib2.0-dev libpixman-1-dev libncurses-dev libfdt-dev libprotobuf-dev protobuf-compiler libfmt-dev liblz4-dev libmpc-dev device-tree-compiler unzip zip file jq tmux htop iotop sysstat ripgrep tree meson`

- 安装方式：`apt-get update` + `apt-get install -y`（两机并行），两台均 rc=0；`dpkg -s` 抽查关键包（`build-essential`/`cmake`/`ninja-build`/`scons`/`ccache`/`bison`/`flex`/`libglib2.0-dev`/`libpixman-1-dev`）全部 `install ok installed`。
- **未装**：OpenCode、任何 AI 会话运行时（节点纯执行）。
- 这些包名与版本判据已固化进 `tools/infra/bootstrap_node.sh` 的 step 1 预检；缺包时脚本只**报告待安装清单**并退出非零，不擅自 `apt install`。

### 4.2.1 ccache

- 节点装了 `ccache 4.9.1`，且构建**确实在用**（`Makefile` 把 `ccache` 接到 LLVM 的 CMake launcher 与 QEMU 的 `CC/CXX` 前缀）。
- **不要整份复制主控机的 `~/.config/ccache/ccache.conf`**：其中的 `cache_dir = /mnt/tao/ccache` 是主控机大磁盘路径，节点不存在。
- 节点口径：`cache_dir` 保持默认本地路径；`max_size = 50G`（默认 5G 在首次 LLVM 构建后就到 4.0G，会开始淘汰）；其余项保持默认（不设 `sloppiness`、不设 `base_dir`）。
- **不做跨机共享缓存**：主控机构建路径 `/mnt/tao/...` 与节点 `/home/gxt/...` 不同，ccache 命中键含路径，要共享就得改 `base_dir`/哈希语义，正确性风险大于收益。


### 4.3 工具链（仓库内自建，不是系统包）

- 节点上的 `clang` / `qemu-dadao` 来自**仓库内构建并安装**的 `.dadao/cross-toolchain/`，不是 apt 包。
- 就绪时版本：`clang 23.1.3`（指向各自 `.cache/llvm-project.git` 的补丁后 commit）、`qemu-dadao 11.1.1`。
- 安装入口只有 `make install-host`；手工 `cp` 属例外手法（须记理由 + md5 核对）。
- 磁盘占用（就绪态）：`.work` 约 **53 GiB** / 台，`.cache` 约 **1.3 GiB** / 台。

## 5. 就绪判据（两台实测）

| 项目 | 结果 |
| --- | --- |
| `make check`（L1） | 两机 rc=0，约 **64 s**（63.9 / 64.6） |
| `make check-inst` | 两机 rc=0，`44 total / 44 passed`、`skipped_profile=985`，**结果行逐字相同** |
| `make install-host` | 两机 PASS（含 `check-cfx-alias-install` 6 项） |
| 工作树 | 干净（`dirty=0`），同一 commit |

判据口径：**「同 commit + 同门控 + 结果一致」才算就绪**；只跑通构建不算。

## 6. 已知坑（四类，均已固化进脚本）

1. **缺 git 身份**：新机没有 `user.name/user.email` ⇒ `apply-series` 末尾 `git commit` 退出 128。
   - **口径（2026-11-07 起）**：直接**复制主控机的 `~/.gitconfig`** 到节点（身份 + 别名全量一致），而不是逐项 `git config`；该文件只含身份与别名（无签名、无凭据、无机器相关路径），可整份复制。`bootstrap_node.sh` 的「缺身份则设置」仅作兜底。
2. **`install-host` 不会自动 `apply-series`**：跳过时 CMake 报 `The target 'DADAO' is not a core tier target`（源树是未打补丁的上游 commit）。顺序必须 `fetch → apply-series → install-host`。
3. **compiler-rt builtins 需一次性手工 configure**：`COMPILER_RT_DEFAULT_TARGET_ONLY=ON` 时缺 `CMAKE_C_COMPILER_TARGET` / `CMAKE_CXX_COMPILER_TARGET` 会直接报错；两值都须为 `dadao-unknown-elf`。
4. **公网不可达**：GitHub 大传输会 `curl 28` / `GnuTLS recv error` ⇒ 仓库走 bundle、组件走本地 `.cache/*.git`，不把「直连公网」当唯一路径。

## 7. 用途与并发约定

- 单机构建 `JOBS=32`（≥ 一半核），**禁** `-j$(nproc)`；一次只跑一个重任务。
- **gem5 补丁类任务必须串行**：任务 worktree 与主工作树共享 `.work/source/gem5`，多个未提交补丁集并发会互相污染（`check-patch-tree` 会红，且红得「有理」）。
- tset 全量（static / dynamic 分档）可拆到多节点并行，但需保证 **同 commit、同工具链**；结果汇总后逐字比对。
- 主控机负责会话与合并；节点只回报 rc 与日志，不改共享台账。
- **派单日志命名**：`<任务号>-<子命令>-<主机>.log`，落在主控机的运行期日志目录（按任务号分子目录），由 `remote.py --log-prefix <任务号>` 指定（默认沿用引入工具的 `INFRA-130t`）。前缀**必须是任务号**：`check-run-artifacts` 只接受 `check-<name>.log` 或 `<TASK-ID>-<purpose>.log`，用工具名作前缀会让 L1 直接红。

## 8. 新增节点流程

1. 装 `tailscale` 并加入同一 tailnet；确认 `tailscaled` 常驻、`gxt` 免密 `sudo` 可用。
2. 装 4.2 的包（或让 `bootstrap_node.sh` step 1 报清单后照单安装）。
3. 同步仓库（bundle 或内网 rsync）+ 本地 `.cache/*.git`。
4. `tools/infra/bootstrap_node.sh`：`fetch → apply-series → compiler-rt configure → install-host → make check`。
5. 验收：`make check` rc=0、`make check-inst` 与本机同 commit 结果一致；用 `tools/infra/remote.py status/preflight` 确认。
6. 在本文件「1. 当前清单」与「5. 就绪判据」补一行实测值。

## 9. 缓存维护（主控机 → 节点 `.cache`）

- **同步 + 校验一条命令**：`python3 tools/infra/sync_cache.py --hosts 'gxt@<node>,gxt@<node2>' --repo '~/DADAO-v5'`（节点清单也可从 `DADAO_NODES` 取；**无内置清单**）。`--dry-run` 只打印计划、不写远端；`--jobs` 控制并发。
- **增量**：`rsync -a` 推送 `.cache/`（裸仓库对象 append-only，第二次运行应近似 0 字节）。**不用 `--delete`**：节点可能持有主控机没有的对象，静默删除比留残留更危险。
- **校验判据**：对 `manifests/components.lock.toml` 每个 enabled 组件，在节点执行 `git -C <repo>/.cache/<name>.git cat-file -e <commit>^{commit}`；缺任一 commit（或整个裸仓库缺失）即该节点 FAIL，提示「缓存过期，请重新同步」。逐节点汇总 `host -> rc`，任一非零整体非零。
- **前提**：同步期间主控机与节点都不要跑 `make fetch`（rsync 读的是活仓库，正在写的 pack 可能被复制半截；partial transfer rc 23/24 会保留为非零，不做兜底）。
- **不做 NFS/sshfs 挂载**（用户 2026-11-07 裁定）：跨 Tailscale（含 DERP 中继）挂载在断链时**挂起**而非报错；只读挂载与 `fetch.py` 写 `.cache` 的路径冲突；运行期还会引入主控机单点依赖。
- **主控机缓存须先齐全**：新节点上线前先 `make fetch`；主控机缺某个 bare repo 时校验会明确报 `missing bare repository`（与「缺 commit」同为 FAIL），不得跳过校验掩盖。

## 10. 任务分配规则（哪类活上哪台）

**分工主轴：实现留主控机，执行上节点。**

- **只在主控机做**：改 `components/**` 补丁集（单写者，避免多台各持一份未提交补丁）、改 `Makefile`/`contracts/`/`tests/inst/` 等共享文件、文档与台账、门控脚本。
- **优先给节点**：纯执行类 — tset 各档全量、门控复跑（L1/L2/L3）、夜跑、timeout 预算实验、矩阵重生成、RTL 构建与仿真回归。
- **一段活只在一台跑**：同一次对照里，QEMU 腿与 gem5 腿分到不同机器，结果回主控机汇总，不来回搬产物。
- **构建与基线不同机**：同机并发会让 `timeout` 判成失败（已有 `Quicksort` 120 s 临界实例）。

**派单前必须过三条**（缺一不派）：

1. 同 commit：`git rev-parse HEAD` 一致（节点用 bundle/`remote.py` 同步）；
2. 同源码树：比 **tree hash**，不比 commit id（各机 `apply-series` 的本地 commit SHA 天然不同）；
3. 二进制可比：gem5/QEMU 由同一补丁集构建；要判确定性时比对二进制 md5 或 `build-id`。

**动作与留痕**：

- 派单命令：`python3 tools/infra/remote.py run --hosts 'gxt@<node>,…' --repo '~/DADAO-v5' --log-prefix <任务号> -- <命令>`；日志落 `<运行期日志目录>/<任务号>/remote/<任务号>-run-<主机>.log`。
- 结果核对**不看单一 rc**：rc + 计数 + 失败集合逐条对齐；`gem5_only_fail` / `qemu_only_fail` 要列名归因。
- 长任务（>10 min）：主控机后台启动、落 PID/日志/`*_EXIT`，主会话监督；子代理不得在会话内等长跑。

**停止点（需先问用户，不自行决定）**：新增/减少节点、破坏性或硬件操作（烧录/复位）、装 license 工具、改动 SPEC/契约语义、跨模块修改、push。
