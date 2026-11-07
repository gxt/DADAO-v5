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
