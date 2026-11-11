# nodes — 构建 / 测试节点台账

> **维护规则**：只记**可复用的口径与事实**（机型、角色、组网、软件包、就绪判据、已知坑），不写节点地址与登录凭据（用户 2026-11-07 裁定：只写主机名 + 角色，地址现场 `tailscale status` 查）。
> **新增节点**：先用 `tools/infra/bootstrap_node.sh` 引导，验收通过后在「清单」与「新增流程」补一行；不手工散跑命令（见「已知坑」）。

## 1. 当前清单

| 主机名 | 角色 | 状态 |
| --- | --- | --- |
| `tao-clab` | **主控机**：唯一装 OpenCode 的机器，会话 / 派单 / 合并都在这里 | 在用 |
| `server207` | 构建 / 测试节点（纯执行，不装 OpenCode） | 就绪 |
| `server208` | 构建 / 测试节点（纯执行，不装 OpenCode） | 就绪 |
| `ics150` | 构建 / 测试节点（纯执行；经端口转发访问） | **待引导** |
| `ics160` | 构建 / 测试节点（纯执行；经端口转发访问） | **待引导** |
| `ics170` | 构建 / 测试节点（纯执行；经端口转发访问） | **待引导** |
| `ics180` | 构建 / 测试节点（纯执行；经端口转发访问） | **待引导** |

- 节点**不跑 AI 会话**，只跑 `make` 目标与测试驱动；派单与结果汇总回主控机。
- 节点数量会继续增加；判据是「同一 commit 的 `make check` + `make check-inst` 结果与主控机一致」，不是「机器装好了」。

## 1.1 `ics150`–`ics180`（2026-11-12 新增，待引导）

- 登录：SSH 别名 `ics150` / `ics160` / `ics170` / `ics180`（**地址与端口只在本地 `~/.ssh/config`**，按本文件维护规则不入库）；账号 `ubuntu`，`sudo` 免密。
- 与 207/208 的差异（实测，决定能不能照搬既有口径）：
  - CPU **40 vCPU**（207/208 是 64）⇒ `JOBS` 取 **16–20**，不要沿用 32。
  - 内存 **125 GiB**（同量级，够）。
  - 磁盘 **98 GiB、可用 83 GiB**（207/208 是 823 GiB）⇒ 就绪态 `.work` 约 53 GiB，**余量仅约 30 GiB**，跑大构建前须 `make check-disk`；不建议在同机并行两套组件构建。
  - **未装构建包**：`gcc`/`make`/`cc`/`ld` 均缺（207/208 的 `build-essential` 等见 §4.2）⇒ 引导前必须先装 §4.2 那批包。
  - 仓库不存在（`~/DADAO-v5` 缺失）⇒ 需 `bootstrap_node.sh --bundle` 从主控机同步。
- 就绪判据同 §5；未过判据前不得派构建/长跑任务。

## 2. 硬件与系统（207/208 两台同构）

- **CPU**：4 路 Intel Xeon E7-4820，8 核 / 16 线程 × 4 = **64 vCPU**（2.0 GHz；NUMA 4 节点，每节点 16 个逻辑 CPU）
- **内存**：**128 GiB**（`free` 可见 125 GiB），日常可用 > 120 GiB
- **磁盘**：根分区 823 GiB，构建前可用约 **700 GiB**；两台都是单盘 `/dev/sda2`，无独立数据盘
- **OS**：Ubuntu **24.04.5 LTS**；内核 6.8.0-149 / 6.8.0-139（两台小版本不同，未影响构建）
- **权限**：`gxt` 账号，`sudo` 免密
- **时区**：**`Asia/Shanghai`（CST, UTC+8）**，与主控机一致（2026-11-09 统一；两台原为 `Etc/UTC`，跨机比对日志时间曾因此误判）
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
- **`--repo` 必须是仓库根**：节点进入后比对 `git rev-parse --show-toplevel` 与 `--repo` 的物理路径；指向子目录 / 非仓库 / 裸仓库 ⇒ 该节点 rc=2（`--repo is not a repository root`），不再拿父仓库的 commit 冒充目标仓库。

## 8. 新增节点流程

1. 装 `tailscale` 并加入同一 tailnet；确认 `tailscaled` 常驻、`gxt` 免密 `sudo` 可用。
   - **时区必须设为 `Asia/Shanghai`**：`bootstrap_node.sh` 的 **step 0** 会自动 `sudo timedatectl set-timezone Asia/Shanghai` 并校验（幂等：已是 CST 则跳过）；手工引导时同样执行该命令，并 `date` 与主控机比对（差异 ≤ 1 s）。节点原厂多为 `Etc/UTC`；不统一会让跨机日志时间戳差 8 h，导致「任务到底在哪台做」判断错误（2026-11-09 实际发生过）。
2. 装 4.2 的包（或让 `bootstrap_node.sh` step 1 报清单后照单安装）。
3. 同步仓库（bundle 或内网 rsync）+ 本地 `.cache/*.git`。
4. `tools/infra/bootstrap_node.sh`：`fetch → apply-series → compiler-rt configure → install-host → make check`。
   - **补丁集变更后必须先 reset**：`apply-series` 只接受「base」或「base+1 且内容等于补丁集」；上游 v5 的补丁集更新后，节点源树仍是旧的 base+1 ⇒ 它会拒绝并退出非零。做法：`git -C .work/source/<组件> reset --hard <manifests 里的 commit>`，再 `make apply-series`。
5. 验收：`make check` rc=0、`make check-inst` 与本机同 commit 结果一致；用 `tools/infra/remote.py status/preflight` 确认。
6. 在本文件「1. 当前清单」与「5. 就绪判据」补一行实测值。

## 9. 缓存维护（主控机 → 节点 `.cache`）

- **同步 + 校验一条命令**：`python3 tools/infra/sync_cache.py --hosts 'gxt@<node>,gxt@<node2>' --repo '~/DADAO-v5'`（节点清单也可从 `DADAO_NODES` 取；**无内置清单**）。`--dry-run` 只打印计划、不写远端；`--jobs` 控制并发。
- **增量**：`rsync -a` 推送 `.cache/`（裸仓库对象 append-only，第二次运行应近似 0 字节）。**不用 `--delete`**：节点可能持有主控机没有的对象，静默删除比留残留更危险。
- **校验判据**：对 `manifests/components.lock.toml` 每个 enabled 组件，在节点执行 `git -C <repo>/.cache/<name>.git cat-file -e <commit>^{commit}`；缺任一 commit（或整个裸仓库缺失）即该节点 FAIL，提示「缓存过期，请重新同步」。组件的 `submodule_lock` 所列必需子模块（`lite or dadao_extra`，与 `fetch.py` 同一并集）镜像同样逐个校验（§11.5）。逐节点汇总 `host -> rc`，任一非零整体非零。
- **前提**：同步期间主控机与节点都不要跑 `make fetch`（rsync 读的是活仓库，正在写的 pack 可能被复制半截；partial transfer rc 23/24 会保留为非零，不做兜底）。
- **不做 NFS/sshfs 挂载**（用户 2026-11-07 裁定）：跨 Tailscale（含 DERP 中继）挂载在断链时**挂起**而非报错；只读挂载与 `fetch.py` 写 `.cache` 的路径冲突；运行期还会引入主控机单点依赖。
- **主控机缓存须先齐全**：新节点上线前先 `make fetch`；主控机缺某个 bare repo 时校验会明确报 `missing bare repository`（与「缺 commit」同为 FAIL），不得跳过校验掩盖。

## 10. 任务分配规则（哪类活上哪台）

**分工主轴：实现留主控机，执行上节点。**

- **只在主控机做**：改 `components/**` 补丁集（单写者，避免多台各持一份未提交补丁）、改 `Makefile`/`contracts/`/`tests/inst/` 等共享文件、文档与台账、门控脚本。
- **优先给节点**：纯执行类 — tset 各档全量、门控复跑（L1/L2/L3）、夜跑、timeout 预算实验、矩阵重生成、RTL 构建与仿真回归。
- **一段活只在一台跑**：同一次对照里，QEMU 腿与 gem5 腿分到不同机器，结果回主控机汇总，不来回搬产物。
- **节点不空转**：节点任务结束（`*_EXIT` 落盘或任务书不再实现中）后，若「待开始任务书存在 + 依赖满足 + 目标节点无负载」三条成立，**立即派单**；「等主控机收口」不是延期理由（2026-11-09 曾因此让 `server207` 空转 1h36m）。
- **一致性判据（用户 2026-11-09 澄清，取代此前的「同一二进制」口径）**：
  - **功能结果**（pass/fail/exit/架构状态）：判据 = **源码 tree hash + 补丁集一致**；二进制可以不同（gem5 内嵌编译时间，md5 每次重建都变，不能作身份）。
  - **时间/性能**：只承诺**同一次运行内的比值**（gem5 ÷ QEMU）可比；跨机绝对值不承诺，同款硬件 + 同源码 + 同编译器下可作参考量，须标注机器指纹。
  - **二进制 md5** 只作诊断，不作可比性判据。
- **多节点分开评测**（用户 2026-11-09）：每台节点独立跑完整套件、产出「本机数据」；汇总按**机器指纹**（CPU 型号 / 源码 tree hash / 编译器版本）分组——同组内可直接比，跨组只比比值与相对量。
- **单任务单机、不迁移**（用户 2026-11-09）：一个 chipyard 构建/仿真任务固定在一台节点上做完，中途不换机器（当时选 207 只是就近，非技术限制；任务可整体派给 208）。
- **旧口径（保留作历史）**：基线分片必须用同一二进制（2026-11-09 修订）：`remote.py status` 现输出 `qemu_md5` 与 `musl_head`；分片前逐节点与主控机比对，**任一不同即不得直接对比**。原因实测：两台节点的 `qemu-system-dadao` md5 各异（`988304f2…` / `7b630d98…`），`musl` 源树 HEAD 也不同（`f4c2beb1…` / `0fbef28c…` vs 主控机 `24c1fd2…`）——「同源码 + 各自构建」不保证行为一致（ldso 捐赠堆布局差异足以让 `malloc-brk-fail` 在两台得出相反结果）。
  - 修法：基线分片时把**主控机构建的安装根**同步到节点（或节点重跑 `fetch`+`apply-series`+`build-musl` 并核 md5/HEAD）；核不上就不并数据。
- **基线运行窗口内同机不得有构建负载**：判据是「构建/编译/Verilator/sbt/大拷贝等 CPU 或 IO 密集进程的生命周期，不得与基线运行时段重叠」；构建进程已退出后再跑基线**不受限**。原因：用例 runtime 贴预算边界（`Quicksort` 128.9 s / `Queens` 135.4 s 对 120 s 预算），负载把「通过」推成 `timeout`，进而被误记为能力缺口。

**派单前必须过三条**（缺一不派）：

1. 同 commit：`git rev-parse HEAD` 一致（节点用 bundle/`remote.py` 同步）；
2. 同源码树：比 **tree hash**，不比 commit id（各机 `apply-series` 的本地 commit SHA 天然不同）；
3. 二进制可比：gem5/QEMU 由同一补丁集构建；要判确定性时比对二进制 md5 或 `build-id`。

**动作与留痕**：

- 派单命令：`python3 tools/infra/remote.py run --hosts 'gxt@<node>,…' --repo '~/DADAO-v5' --log-prefix <任务号> -- <命令>`；日志落 `<运行期日志目录>/<任务号>/remote/<任务号>-run-<主机>.log`。
- 结果核对**不看单一 rc**：rc + 计数 + 失败集合逐条对齐；`gem5_only_fail` / `qemu_only_fail` 要列名归因。
- 长任务（>10 min）：主控机后台启动、落 PID/日志/`*_EXIT`，主会话监督；子代理不得在会话内等长跑。

**停止点（需先问用户，不自行决定）**：新增/减少节点、破坏性或硬件操作（烧录/复位）、装 license 工具、改动 SPEC/契约语义、跨模块修改、push。

### 10.1 调试边界

- **节点只执行**：构建、测试、仿真、`gdb` 等都在节点跑；节点**不改被跟踪文件、不产生补丁**。
- **chipyard 分配（用户 2026-11-09 修订，取代 2026-11-08 的「全部放 207」）**：
  - **调试/快速迭代**（改 RTL、`sbt compile`、elab、小规模仿真）⇒ **主控机**。理由：sbt/elab 是单核敏感（JVM 单进程），EPYC 7773X 单核比节点的 E7-4820 快 4–6 倍；且 sbt/elab 只用 1–2 核，**可与门控并行**。
  - **Verilator 长仿真**（inst 全量、T0/T1 冒烟、多例并行）⇒ **节点**。理由：单次几十分钟到几小时，不占主控机的门控资源。
  - **Verilator 构建并行度**：主控机 `JOBS=32`（留一半给门控/系统），节点 `JOBS=48`。
  - **单任务单机、不迁移**：一个任务内的「构建+仿真」固定在一台；已开工的任务不中途换机（如已在节点构建完的，就地收口）。
  - 一致性：功能结果按**源码 tree hash + 补丁集**；**不跨机复制 `simulator-*`**（Verilator 产物与机器相关）。
  - **所有对仓库的修改一律在主控机**（worktree + 补丁 + 台账），节点只接收同步后的代码。
- **冲突必须串行**：任何会改同一份文件/同一组件源树的任务不得并行。
- **节点交互不走 `/tmp`**：bundle、rsync 暂存、回传产物等中转文件放 `.work/`（主控机）与仓库内/家目录（节点）；`/tmp` 是 tmpfs，耗光会断任务链。
- **改代码只在主控机**：源码改动、补丁导出、台账与判断都在主控机；「在节点手改再拷回来」禁止（补丁会无法复现）。
- **重建用主控机的补丁**：需要节点复现时，走「主控机改 → 导出补丁 → 同步节点 → `apply-series` → 重建」；调试时可以在节点上读 gdb/日志，但**结论带回主控机**再决定改什么。

## 11. RTL / 综合环境（chipyard + Verilator + RISC-V 工具链）

**用户裁定（2026-11-07）**：用 chipyard 官方 conda 依赖；含一次真实构建冒烟；综合工具**只要 Verilator**（Yosys/OpenROAD/商业工具不装）。

### 11.1 装了什么、在哪

- `conda`（Miniforge）在 `~/miniforge3`；conda-forge 走清华镜像，`ucb-bar`/`litex-hub` 走官方。
- 环境在 `<repo>/.work/source/chipyard/.conda-env`（**repo 相对路径**，与 chipyard 默认一致）：约 **6.1 GiB**（含 riscv-tools 626 MiB）。
- 版本：`verilator 5.022`、`openjdk 20.0.2`、`sbt`（conda 包）、`riscv64-unknown-elf-gcc 13.2.0`、`riscv64-unknown-linux-gnu-gcc 13.2.0`、`firtool`（CIRCT 1.75.0 / LLVM 19.0.0git）。
- riscv 工具在 `<env>/riscv-tools/bin`，由 `activate.d/activate-riscv-tools.sh` 注入 PATH；`sims/` 的构建还需要 `RISCV=<env>/riscv-tools`。
- chipyard 源码 + 最小子模块约 **2.9 GiB**。最小子模块集由 `scripts/init-submodules-no-riscv-tools.sh` 决定（两台实测 **30/55**，其余 25 个均在脚本 blocklist 内：可选加速器/核 + `riscv-pk`/`riscv-tests`/`libgloss`/`riscv-spike-devices`）。**现行口径**以 `manifests/chipyard-submodules.lock.toml` 的 `lite = true`（29 条）∪ `dadao_extra = true`（1 条）为准（共 30 条，见 §11.5）。

### 11.2 建环境时必须补的三处（官方 `build-setup.sh` 之外）

1. **`firtool` 不在 conda 依赖里**：需装 CIRCT 静态包（`firtool-1.75.0`，**759 MB**）。直连 GitHub release 会截断（`Unexpected EOF`）⇒ 用 `wget -c` 断点续传循环，校验字节数后再解包到 `<env>`。
2. **conda `riscv-tools` 不含 fesvr**：`sims/` 的 C++ 测试驱动需要 `fesvr/*.h` 与 `libfesvr.a` ⇒ 用 chipyard 自带 `toolchains/riscv-tools/riscv-isa-sim` 源码 `configure --prefix=<env>/riscv-tools && make && make install`。
3. **GitHub 时通时不通**：子模块 clone 会 135 s 超时。**优先从主控机已有检出 rsync**（工作树 + `.git/modules` 元数据，按相同绝对路径），不要反复重试 clone。

### 11.3 冒烟判据（实测）

- `sims/verilator`（默认 `RocketConfig`，`-j32`）构建成功，产物 `simulator-chipyard.harness-RocketConfig` 约 **11 MB**；单次 clean 构建为 **20–30 分钟量级**。
- **`--help` 的退出码是 255（上游行为）**：chipyard 仿真器打印 help 后会 `terminate called ... User queried htif_t help text`。判据应看「输出含 `Usage:` / `EMULATOR OPTIONS`」，**不能**用 rc=0。
- 两台的 `conda list` 逐包比对 **190 项、0 差异**（环境可复现）。

### 11.4 已知限制

- conda 版 riscv 工具链**没有 `htif_nano.specs`**（只有 `nano.specs`）⇒ chipyard 自带 `tests/` 裸机测试暂时编不了；要用需补 riscv-pk / newlib 的 htif 支持，属后续任务。
- 两台目前**不共享** conda 环境：各自本地建（包清单一致）；chipyard 源码树走主控机中继。节点间尚未配置 SSH 免密（如需 P2P 传输要先经用户同意再分发密钥）。

### 11.5 子模块来源与镜像

- 必需子模块集 = `manifests/chipyard-submodules.lock.toml` 中 **`lite = true`（上游最小集，29 条）∪ `dadao_extra = true`（本仓库额外需要，1 条：`toolchains/riscv-tools/riscv-isa-sim`，因 conda `riscv-tools` 不含 fesvr）**，共 **30** 条（`tomllib` 现场统计；`grep -c 'lite = true'` 报 30 是文件头注释里也有该字样）。`lite` 语义保持上游原义，不再被本仓库的额外需求改写。
- 主控机把它镜像成 `.cache/submodules/<path 派生名>.git`（`generators/testchipip` → `generators__testchipip.git`）：主控机联网用 `fetch.py --populate-submodules` 建镜像；节点只从主控机 `sync_cache.py` 同步，缺镜像时 `make fetch` 明确失败并指向该脚本（节点不向 GitHub 拉子模块）。
- 约定正文（镜像布局 / 命名 / 失败语义）见 `docs/Process-01 §14「子模块（submodule）的获取与镜像」`。

## 12. 主控机 `/tmp`（待切回磁盘，用户自理）

- 现状：主控机 `/tmp` 由 `/etc/fstab` 配成 16G tmpfs；节点 `/tmp` 已在 ext4 磁盘上（无需改）。
- 用户 2026-11-08 决定改回磁盘，**推迟到用户自行选时间执行**（`sudo` 由用户操作）。
- **不再主动提醒重启**；切换前置 = `/tmp/opencode` 下无活动 worktree（由主会话在切换前清理/迁移）。
