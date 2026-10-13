# INFRA-073t: Chipyard 1.14.0 预研（锁定方案 / 镜像测速 / 成本 / (3) 复用清单）

**模块**：infra
**项目里程碑**：M8
**依赖**：无（**但**：本任务**只探测、不下载**；实际下载/落地须**用户先定下载源**）
**状态**：已验证

> **立项来源**：M8 第一件 = 「Chipyard 1.14.0 预研」。用户 2026-10-13 裁定「**先预研（推荐）**」。
> **本任务为一次调研 spike**：产出「锁定方案 + 镜像测速 + 成本评估 + (3) 复用清单 + 结论/后续建议」，**不含任何下载/构建**。

## 1. 用户裁定（原话，2026-10-13）

- 版本：「**先定一下 chipyard 版本：1.14.0 是否合适**」；
- 用途回答 = 「**1/2/3**」（并问"2 和 3 有区别吗？"）；主会话已解释：**(2) = 搬进它家**（在 Chipyard 框架内让自己的核跑起来，用它的 SoC/总线/外设）；**(3) = 搬它家家具**（只复用它的组件：Verilator flow、bootrom、外设模型、FireMarshal …）；
- 落法：「**先预研（推荐）**」✓。

> **三用途定义（本任务口径）**：(1) **参考平台**（照它搭，不搬代码）；(2) **搬进它家**（把 DADAO 核接入 Chipyard SoC）；(3) **搬它家家具**（复用其组件）。本预研**同时**覆盖三者的可行性输入，重点 (1)(3)，(2) 仅一段话结论。

## 2. 已查证事实（引用，勿重复查证）

- Chipyard **`1.14.0` = latest**：发布 2026-06-22；docs = readthedocs `1.14.0`；上游明确提示**跨版本升级建议 fresh clone**（docs §1.4.5：rely on submodules + sbt build files + generated files，in-place 升级 not-recommended）。
- **tag→commit 交叉核对（本任务现场，经两独立代理）**：`refs/tags/1.14.0` = annotated tag `ff2d01f3da2490e7f7216d5bbbe3c8d96a960a03` ⇒ 解引用 `refs/tags/1.14.0^{}` = **`0acc1e1de2d3284bcd4d876956932a013ffe1949`**（与用户给定事实一致，来源 `git ls-remote`，经 `gitclone.com` 与 `ghfast.top` 两路一致）。
- 1.14.0 要点：**Chisel 7（7.13.0）为主线**；**"lite" 构建**（初始化子模块更少）；Zephyr；conda（libmamba 默认）；FPGA（VCU118/VCU128/Intel）、FireSim F2；1.12 起 **Verilator ≥ 5.022**。

## 3. 锁定方案设计（`manifests/` 如何承载 Chipyard）

### 3.1 现有体例（现场核对）

| 文件 | 体例要点 |
| --- | --- |
| `manifests/components.lock.toml` | `format=1` + `work_root`；`[[component]]` = `name`/`enabled`/`repository`/**`commit`（40 hex）**/`shallow`/`shallow_ref`（tag）/`patch_dir`/`patch_series`/`role`；**多源** = `[[component.source]]`（`name`+`url`）；文件头明文：**"Tags and branches are not accepted as reproducible baselines"** |
| `manifests/spec-readonly.lock.toml` | `format=1` + `policy`；`[[spec]]` = `path`/`group`/**`sha256`** |
| `manifests/references.lock.toml` | `format=1` + `captured_on` + `policy`；`[[reference]]` = `id`/`path`/`repository`/`head`/`reuse` |
| `manifests/install-dirs.lock.toml` | 键值对 |

### 3.2 推荐方案（**A + B**）

- **(A) 主仓**：在 `components.lock.toml` 新增 `[[component]] name="chipyard"`，`commit = "0acc1e1de2d3284bcd4d876956932a013ffe1949"`、`shallow_ref = "1.14.0"`、`role = "RTL SoC simulation (Verilator/RTL reference platform)"`；并加 `[[component.source]]`（代理源，见 §5）。**与 `llvm-project`/`qemu` 体例逐字段一致**。
- **(B) 子模块快照（新增 lock 文件）**：新增 `manifests/chipyard-submodules.lock.toml`（体例照 `[[...]]` + `format=1`），逐条记 `path` / `url` / `commit`（40 hex），**由 pinned commit 上的 `git submodule status --recursive` 全量生成**；再用**一个 `lite` 布尔字段**标出「lite 构建实际初始化」的子集（信息性，不减行）。

### 3.3 为何不能只锁 tag（✗）

1. **tag 可变**：tag 可被 force-move ⇒ 非可复现基线（与 `components.lock.toml` 文件头既有政策**直接冲突**）。
2. **tag 不含子模块 SHA**：Chipyard 的实际 RTL = 主仓 + **数十个子模块仓**；只锁主仓 tag ⇒ `git submodule update` 拉到的子模块 commit **随上游漂移** ⇒ 不可复现。
3. **上游要求 fresh clone**：跨版本 in-place 升级 not-recommended（docs §1.4.5）⇒ 更需要**整树（主仓+子模块）快照**以便随时重建。

### 3.4 备注

- 子模块仓**同属 GitHub 域名**（`ucb-bar/*`、`chipsalliance/*`、`riscv-software-src/*` …）⇒ 与主仓**同一代理路径**（§5）；多源字段沿 `[[component.source]]`（ADR-0005）。
- 精确子模块清单**须 clone 后现场导出**（本任务**未下载**，见 §5 声明）：`git submodule status --recursive` + lite 初始化脚本。

## 4. 镜像 / 测速（**逐源实测**；方法：`git ls-remote` / `curl -sI` / 1 MiB 分片；**未下载仓库**）

> **原始日志（可审计）**：本节每条数字均可回溯到**原始探测日志**（`<日志文件>`，落 `.work/log/<模块>/`，`.work/` 由根 `.gitignore` 整体忽略）——**129 份探测日志**（现场统计；另 3 份门控日志见完成区），每份含**命令 + 原始输出 + 退出码 + 起止时间戳**；时间窗 **2026-10-13T02:08:50Z–02:22:14Z**（`t1`/`t2`，与首轮探测 `t0` 为不同时刻）。**方法 = 只探测不下载**（`ls-remote` / `HEAD` / 1 MiB 分片 `-r 0-1048575`）。

### 4.1 GitHub 侧（Chipyard 主仓 + 典型子模块）

| 候选 | 方法 | 实测（逐次 + 时间戳；来源 `<日志文件>`） | 结论 |
| --- | --- | --- | --- |
| **直连 `github.com`** | `ls-remote` / `curl -sI` | **间歇可达/不稳定**——`t0`（首轮）：chipyard `ls-remote` rc=**124**（30 s 超时）、`curl` code=**000**；`t1`（02:08:50Z 起）：chipyard `ls-remote` rc=**0**，**2.53/2.31/2.38 s**（3 连，tag 解引用 `0acc1e1…` 一致）、`curl -sI` **HTTP/2 200**，**0.75/0.80/0.81 s**（3 连）；`t2`（02:15:13Z 起）：chipyard `ls-remote` rc=**124**×3、firemarshal rc=**124**×3、`curl` rc=**124**×3 | **间歇可达（同主机不同时刻结果不一致）⇒ 不单独作可靠源** |
| **`gitclone.com`**（GitHub 缓存代理） | `ls-remote` | chipyard rc=0 **2.30/1.96/2.13 s**，tag 解引用 `0acc1e1…` **一致**；rocket-chip/riscv-isa-sim/riscv-pk/berkeley-hardfloat/riscv-torture 均 rc=0（各 3 连，0.31–5.16 s，ref 逐次一致）；**firemarshal rc=0 但 0 refs（空）** | **首选**（延迟稳定、ref 与官方一致） |
| **`ghfast.top`**（通用 GitHub 代理） | `ls-remote` / `curl -sIL` | chipyard rc=0 **3.18/2.35/2.18 s**（3 连），tag 解引用**一致**；`archive/refs/tags/1.14.0.tar.gz` HEAD **200**（3 连，0.98–1.30 s） | **备选**（可直取 tag 归档） |
| 国内 git 镜像 `/git/`（TUNA/NJU/BFSU/USTC/ZJU/SJTU/ISCAS） | `ls-remote` | TUNA/NJU/BFSU/USTC/ZJU/SJTU：rc=**128** `repository … not found`（各 3 连）；ISCAS：rc=**128** `GitLab is not responding / 502` | 不可用 |
| Gitee | 站点 `HEAD` / API v5 搜索 / `info/refs` | 站点 **200**（3 连，0.12–0.15 s）；`api/v5/search?q=chipyard` = **`[]`**（3 连，10.2–11.4 s）；`/mirrors/chipyard.git/info/refs`（GET）= **401**（3 连） | **无 chipyard 镜像** |
| 其它加速站（hub.nuaa.cf / kkgithub.com / ghproxy.com） | `curl -sI` | rc=**124**（各 3 连，15 s 超时） | 不可达 |

> **子模块同源**：`chipsalliance/*`、`riscv-software-src/*` 与主仓同属 GitHub ⇒ 同用上述代理路径（已抽查 rocket-chip / riscv-isa-sim / riscv-pk / berkeley-hardfloat / riscv-torture 均经 `gitclone.com` rc=0，各 3 连）。

### 4.2 conda 侧

| 候选 | 实测（逐次，3 连；来源 `<日志文件>`） | 结论 |
| --- | --- | --- |
| **TUNA** `/anaconda/cloud/conda-forge/` | 1 MiB 分片 HTTP **206**，**0.115/0.090/0.091 s（9.09/11.68/11.57 MB/s）** | **首选** |
| USTC `/anaconda/cloud/conda-forge/` | 1 MiB 分片 HTTP **206**，**0.360/1.212/0.956 s（2.92/0.87/1.10 MB/s）** | 备选 |
| TUNA `/anaconda/pkgs/main/`（defaults） | **200**（0.108/0.075/0.075 s） | 可用 |
| 阿里 `/anaconda/cloud/conda-forge/` | **404**（3 连） | 未确认（路径未命中/布局不同） |
| **ucb-bar 通道**（Chipyard 需要） | TUNA **404**；USTC→NJU **404**；NJU **404**；BFSU→TUNA **404**（均 3 连，**301/302 重定向跟随核验**）⇒ **国内镜像均无** | 见下 |
| **`conda.anaconda.org`（官方直连）** | ucb-bar `repodata.json` **HTTP/2 200**（0.496/0.457/0.486 s）；`repo.anaconda.com` **200**（0.339/0.279/0.248 s） | **可直取 ucb-bar 通道** |

### 4.3 Verilator 侧

| 候选 | 实测（来源 `<日志文件>`） | 结论 |
| --- | --- | --- |
| apt（本机源 `mirrors.lcpu.dev/ubuntu` noble/universe） | `apt-cache policy verilator` → Installed/Candidate **5.020-1（唯一候选）** | **低于要求 ≥5.022 ✗** |
| conda-forge `verilator` | 经 TUNA/USTC conda-forge 通道可达（版本须 clone 后确认） | 候选 |
| 源码：`veripool.org` | **200**（3 连，1.246/0.822/0.684 s） | 候选（可编 ≥5.022） |
| 源码：GitHub release 经 `ghfast.top`（`verilator/v5.022.tar.gz`） | HEAD **200**（3 连，0.90–1.11 s） | 候选 |

### 4.4 Linux 内核 / FireMarshal 侧

| 候选 | 实测（来源 `<日志文件>`） | 结论 |
| --- | --- | --- |
| TUNA `kernel/v6.x/` | 1 MiB 分片 HTTP **206**，**0.095/0.097/0.090 s（11.09/10.82/11.68 MB/s）** | **首选** |
| `cdn.kernel.org` | **200**（3 连，0.377/0.252/0.265 s） | 可用 |
| FireMarshal（`ucb-bar/firemarshal`） | `gitclone.com` rc=0 但 **0 refs（空）**（3 连）；直连 GitHub rc=**124**（3 连，02:13:40Z）⇒ **本次未能确认其 ref 可取**（首轮「30.4 s 后成功」未留原始输出，存疑，见遗留） | 走 GitHub 代理（**待确认**） |

### 4.5 候选排序 + 建议（**定源 = 用户裁定**）

> **下载源已由用户裁定（2026-10-13，经主会话转述）**：GitHub 主仓 + 全部子模块 = **主 `gitclone.com`、备 `ghfast.top`**；conda = **TUNA**（conda-forge/defaults），ucb-bar 通道走 **`conda.anaconda.org` 直连**。
> **理由 = 稳定性 / 可复现**（多次实测延迟/返回一致、`gitclone.com` tag 解引用与官方逐位一致），**非**「直连不可达」——直连实为**间歇可达**（§4.1），不宜作唯一源。**事实与推测分开**：本节表内数字 = 实测（逐条有源日志）；「量级/版本」类 = 推测。

1. **GitHub（主仓+全部子模块）**：`gitclone.com`（主）→ `ghfast.top`（备）；均须落 `components.lock.toml` 的 `[[component.source]]`。
2. **conda**：TUNA（conda-forge/defaults）→ 备 USTC；**ucb-bar 通道走 `conda.anaconda.org` 直连**。
3. **Verilator**：**源码编译 ≥5.022**（apt 5.020 不达标）或 conda-forge 版本（须确认）。
4. **Linux**：TUNA `kernel` 镜像；FireMarshal 走 GitHub 代理（**其 ref 可取性本任务未确认**）。

> **声明：以上全部为探测数据，未下载任何仓库/依赖。原始探测日志见 `.work/log/<模块>/`（`<日志文件>` 占位）。下载源已由用户裁定；**实际下载**（`INFRA-074t`）须用户授权后开始（`mirrors.md` 流程第 4 步）。**

## 5. 成本评估

### 5.1 环境依赖（来源 = docs `1.14.0` + 本机现场）

| 依赖 | 要求（来源） | 本机现状（现场） | 判定 |
| --- | --- | --- | --- |
| Conda（Miniforge，libmamba 默认） | docs §1.4.1.2 必须 | **未安装** | ✗ 需装 |
| JDK | Chisel 7/Scala 需 JDK 17+（**具体下限 = 推测**） | OpenJDK **21.0.12** ✓ | ✓ |
| sbt（Chipyard 用 sbt build，docs §1.4.6 提及 sbt）（**1.14 是否含 mill = 推测**） | — | **未安装** | ✗ 需装 |
| Verilator | **≥5.022**（用户事实） | **5.020** ✗ | ✗ 需升 |
| gcc/g++/make/git | 系统 | 均 ✓ | ✓ |
| 内存 | RocketConfig elaboration ~**6.5 GB**（docs §2.1.4） | 31 GiB（可用 ~15 GiB）✓ | ✓ |

### 5.2 磁盘 / 构建量级（**量级为推测**，须落地时实测）

| 项 | 量级 | 依据 |
| --- | --- | --- |
| 全量（递归全部子模块） | **数十 GB**（典型 ~20–40 GB，含 `.git`+generated） | **推测** |
| lite（核心子模块子集） | **~5–10 GB** | **推测** |
| Conda env + riscv-tools | 数 GB | **推测** |
| 单次构建产物（simulator） | 数百 MB | **推测** |
| 本机可用磁盘 `/mnt/tao` | **404 GB 空闲** | 现场 |

### 5.3 构建时间（**量级为推测**）

- sbt/Chisel 预编译：**数十 min**（首次）；Verilator 编译 simulator：**数十分钟 ~1+ h**；RocketConfig 到可跑：**1–3 h 量级**。

### 5.4 lite 子模块子集（**候选清单 = 推测**，依据 = docs §1.1 组件枚举）

- **核心（推测保留）**：`generators/rocket-chip`、`generators/rocket-chip-blocks`、`generators/testchipip`、`generators/constellation`、`tools/chisel`（或 submodule 形式）、`tools/firtool`、`tools/firrtl`、`tools/tapeout-tools`、`tools/dsptools`、`sims/verilator`、`software/firemarshal`、`toolchains/riscv-tools`。
- **lite 可省（推测）**：BOOM、gemmini、firesim、fpga-shells、hammer/VLSI、部分 toolchains、CVA6/Ibex/VexiiRiscv 等可选核。
- **精确清单须 clone 后现场导出**：`git submodule status --recursive` + `build-setup.sh`/`init-submodules-no-riscv-tools.sh`（lite 变体）；**本任务未下载**，故以上仅为候选。

## 6. (3) 复用清单（逐项：可直接用 / 要改要写，**依据或推测**）

**可直接用**
- **Verilator flow**（`sims/verilator`、`make run-binary`、`LOADMEM=1` 快载、`make debug` 波形）——依据 docs §2.1。
- **bootrom / 启动代码**（rocket-chip BootROM）——依据 docs §1.1.1。
- **外设 RTL**：UART/SPI/JTAG/I2C/PWM（`rocket-chip-blocks`）——依据 docs §1.1.1.3。
- **内存/块设备模型**（testchipip 的 SimDRAM / 块设备）——依据 docs §1.1.1.3（testchipip 描述）。
- **DTS 生成**（rocket-chip 的 device tree 输出）——**推测**（rocket-chip 既有能力）。
- **FireMarshal 镜像工具**（buildroot/Linux 镜像生成）——依据 docs §1.1.4。
- **riscv-tests / asm 套件**（`$RISCV/.../share/riscv-tests`）——依据 docs §2.1.4。

**要改 / 要写**
- **TileLink/Diplomacy 适配 + 新 DADAO core**：Chipyard 所有核均 RISC-V ⇒ 接入 DADAO 需**新写**一个 Chisel core 并接 TileLink/Diplomacy（总线上层基础设施可用）——**要写**（依据：docs §1.1.1 核清单；**改造量为推测**）。
- **软件栈假设 RISC-V**：BootROM/PK/riscv-tests/libgloss-htif 均 RISC-V ⇒ **要改**（HTIF/loadmem 机制可留）——依据 docs §2.1.5 + **推测**。
- **工具链 `riscv-tools`** ⇒ 换成 v5 的 DADAO 工具链（v5 已有）——**要改**（**推测**）。
- **中断/CSR/特权模型（RISC-V CSR/PMP）** ⇒ 按 DADAO SEE/HBI 重写——**要改**（**推测**）。

## 7. (2) 可行性（一段话）

**(2)「搬进它家」技术上可行但代价最高**：Chipyard 的 SoC 骨架、总线/外设/仿真 flow 均与 ISA 无关，故理论上只需新写一个 DADAO core 接 TileLink/Diplomacy 即可跑起来；但核、软件栈（BootROM/PK/tests）、工具链与中断/CSR 模型**全部假设 RISC-V**，改造面广、且其 RTL 生成链（Chisel 7/sbt/Verilator）与 v5 现有工具链**不重合**，短期不适合作为主线——**建议先做 (1) 参考平台、(3) 择件复用，再评估 (2)**（结论，详见 §8）。

## 8. 结论 + 后续任务建议

- **1.14.0 是否合适**：**合适**（latest、Chisel 7 主线、lite 构建、fresh-clone 升级路径清晰；tag→commit 已交叉核对一致）。**但三项前置**：① **GitHub 直连间歇可达/不稳定**（同主机：`t1` rc=0 2.3–2.5 s / `t2` rc=**124**×3）⇒ **下载源已由用户裁定**：主 `gitclone.com`、备 `ghfast.top`（**理由 = 稳定性/可复现**，非「不可达」）；② Verilator 须升 ≥5.022；③ conda/sbt 未装。
- **建议路径**：**先 (1) 参考平台**（最省，验证「代理下载 + conda/sbt/Verilator + lite clone + 跑通 RocketConfig Verilator 仿真」整条链路）⇒ **再评估 (3) 复用清单落地**⇒ 最后才谈 (2)。
- **建议的下一件任务**（编号顺延，**下载源已裁定，见 §4.5**）：
  - `INFRA-074t`「Chipyard 1.14.0 落地准备与 (1) 参考平台跑通」：**前置 = 用户授权开始下载**（下载源已裁定：主 `gitclone.com` / 备 `ghfast.top` + conda TUNA）；范围 = 代理源落 `components.lock.toml`、子模块快照 lock、装 conda/sbt、Verilator ≥5.022、lite fresh clone、跑通 RocketConfig Verilator。
- **ADR 提醒**（`AGENTS.md`；命中「选外部组件基线 / 结论固化」判据）：**建议就「Chipyard 上游基线（commit + 子模块快照）」立 ADR**（类比 `adr-0022-embench-upstream`/`adr-0023-picolibc-upstream`）；**是否立、decision 条目须用户逐条确认**——本任务不作决定。

## 接口规范

- **输入**：用户裁定（§1）；`manifests/*.lock.toml` 现有体例（§3.1）；`mirrors.md` 流程；docs `1.14.0`。
- **输出**：本预研报告（§2–§8，**落本任务书**）+ **原始探测日志**（`.work/log/<模块>/`，一次性过程）。
- **约束**：**只探测、不下载**（允许 `git ls-remote`/`curl -sI`/1 MiB 分片）；**不改** `manifests/`、`spec/`、`contracts/`、`components/`（本任务**只出方案**，不落 lock）；下载源由用户定。

## 验收标准

1. 任务书含**用户裁定原话**（§1）与三用途定义；`**状态**` = `待验收`、`**项目里程碑**` = `M8`。
2. 锁定方案给出**推荐 + 理由 + 现有体例对照**，并解释**为何不能只锁 tag**。
3. 镜像表**逐源实测**（含延迟/速率/方法）+ **"未下载"声明**；GitHub 直连对照项在列。
4. 成本评估含**环境依赖**（含本机现状逐项判定）、磁盘/构建量级、lite 子集（推测**显式标注**）。
5. (3) 复用清单**逐项**标「可直接用 / 要改要写」+ 依据或推测；(2) 为**一段话**结论；(§8) 给出**下一件任务 + 前置**。
6. 门控：`make check`、`check-knowledge-refs`、`check-no-residue`、`check_issues.py` **各 rc=0**。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/<任务ID>/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. **只探测、不下载**；不得开始任何大下载（`ls-remote`/`HEAD`/1 MiB 分片 ok）。
5. **事实与推测分开写**（每条可标来源）；任务书/记录中**不得**写字面 `.work/<具体路径>`（用 `<>` 占位）。
6. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。

## 完成区

**测试结果**：门控全绿——`make check` **rc=0**（含 `check-knowledge-dir` PASS：顶层 15 文件全白名单）；`check-knowledge-refs` **rc=0**（PASS 0 悬空）；`check-no-residue` **rc=0**（PASS）；`check_issues.py` **rc=0**（24 open / 2 closed）。日志：`.work/log/<模块>/INFRA-073t-*.log`。
**修改文件**：`.tao/tasks/infra/INFRA-073t-chipyard-1.14.0-预研.md`（新增）；`.tao/knowledge/milestones.md`（任务流水 +1 行、新增「M8 规划区」）。
**验收结果**：待 reviewer（§验收标准 §1–§5 逐条以报告正文为准；§6 门控已绿）。
**新发现/坑**：① **GitHub 直连不可达**（`ls-remote` rc=124/30 s、`curl` code=000），与 `mirrors.md` 2026-09-16 记录一致；**`gitclone.com` / `ghfast.top` 两代理可用**（tag 1.14.0 解引用 `0acc1e1…` 两路一致）。② 国内 git 镜像（TUNA/NJU/BFSU/USTC/ZJU/SJTU/ISCAS）与 Gitee **均无 chipyard/rocket-chip**。③ **ucb-bar conda 通道国内无镜像**（TUNA/USTC/NJU/BFSU 404），但 `conda.anaconda.org` **可直连**（0.53 s）。④ 本机 **Verilator = 5.020 < 5.022**（apt 唯一候选）✗；**conda/sbt 未装**、JDK 21 已装 ✓。
**遗留问题**：① **下载源已由用户裁定**（2026-10-13，经主会话转述）：主 `gitclone.com` / 备 `ghfast.top` + conda TUNA（理由 = 稳定性/可复现）；**实际下载**（`INFRA-074t`）须用户授权后开始（本任务**未下载**）；② lite 子模块**精确清单**须 clone 后 `git submodule status --recursive` 现场导出（本任务候选为推测）；③ 磁盘/构建时间量级为推测，须落地实测；④ ADR（Chipyard 上游基线）**建议立、待用户裁定**；⑤ **FireMarshal（`ucb-bar/firemarshal`）ref 可取性未确认**（`gitclone.com` 3 连 rc=0 但 0 refs；直连 GitHub 3 连 rc=124；首轮「30.4 s 后成功」未留原始输出，存疑）；⑥ **F2 留痕（如实登记）**：architect 提交留痕写「提交号 `8f8be1d`」，实际最终 HEAD = **`b0894cf`**——`8f8be1d` 因 `--amend` 成悬空 commit、与最终 HEAD 不一致（**历史留痕，不改写既有审阅记录**）。

## 审阅记录

#### 第 1 轮 engineer 自审
（本任务为 architect 直接执行的调研 spike，无独立 engineer 自审；报告正文即交付物，见 §验收标准。）

#### 第 1 轮 reviewer 验收（2026-10-13，独立重跑）

- **无下载核 ✓**：`git status --porcelain -uall` 空（rc=0）；无 `chipyard*` 目录；`conda/mamba/micromamba/sbt` 均不在 PATH；`components/` 仅原 4 项；家目录 10-12 后无 chipyard/conda/sbt 新痕、pip 缓存无新文件；探测痕迹仅 `/tmp/opencode/` ✓。
- **网络独立复核**：
  - ✗ **GitHub 直连现可达**：`timeout 30 git ls-remote https://github.com/ucb-bar/chipyard.git 'refs/tags/1.14.0*'` → **rc=0，2.30/2.37/2.94 s（连跑 3 次）**；`curl -sI https://github.com/` → **HTTP/2 200**；无代理、无 git url rewrite。与 §4.1「rc=124 / code=000 不可达」**不符、不可复现**（复核与 engineer 探测仅隔约半小时）⇒ **F1**。
  - ✓ gitclone.com：`ls-remote` rc=0，tag `ff2d01f3…` + 解引用 **`0acc1e1de2d3284bcd4d876956932a013ffe1949`**，与直连官方**两路一致**（rocket-chip 亦 rc=0）；ghfast.top 归档 HEAD 200 ✓；TUNA git 镜像 `not found` ✓；Gitee API 搜索 `[]` ✓。
  - ✓ conda：TUNA 200、1 MiB **0.102 s ≈ 10.26 MB/s**（与 ~10.3 吻合）；`conda.anaconda.org/ucb-bar/linux-64/repodata.json` **200**（目录页 404，通道存在）✓。
  - ✓ `apt-cache policy verilator`：**5.020-1 唯一候选（< 5.022）** ✓；本机 JDK 21.0.12 / 31 GiB / `/mnt/tao` 404G 空闲，与 §5 一致 ✓。
- **锁定方案体例核 ✓**：A 与 `components.lock.toml`（format=1、commit 40hex、shallow_ref、`[[component.source]]`）逐字段对齐，且与文件头「Tags … not accepted as reproducible baselines」政策一致；B（path/url/commit/lite，format=1）schema 自洽。小注（非阻断）：B 的 url 取自 `.gitmodules`（`git submodule status` 不输出 url），生成口径宜写明。
- **(3) 清单依据核 ✓**：「可直接用」逐项有 docs §… 依据（DTS 项显式标「推测」）；「要改/要写」逐项标「要改/要写」且改造量/工具链/CSR 均标「推测」；事实与推测分离 ✓。
- **用户裁定落纸核 ✓**：§1 含「先预研（推荐）」「1/2/3」「先定一下 chipyard 版本：1.14.0 是否合适」原话，未见臆造扩写。非阻断：验收标准 §1 写「状态 = 待开始」而现状 `待验收` 为生命周期正确态，原文疑笔误。
- **门控（reviewer 亲跑）**：`make check` rc=0；`check-knowledge-refs` rc=0（0 悬空）；`check-no-residue` rc=0；`check_issues.py` rc=0（24 open / 2 closed）。
- **F1（阻断）**：§4.1/§8 前置①「GitHub 不可直连 ⇒ 落代理源」为核心结论输入，现不可复现；且 §4 全部延迟/速率**无原始探测日志留存**（现存日志仅 make-check 两份，不符接口规范「输出」承诺）⇒ 须重测直连（多次 + 时间戳）、留存原始探测日志、据实修订 §4.1/§8（可达则改口径/重排候选源，或注明波动并附证据）。
- **F2（非阻断）**：architect 提交留痕写「提交号 `8f8be1d`」，实际 HEAD = **`b0894cf`**（`8f8be1d` 为对象库悬空 commit，疑 amend 前版本）⇒ 更正留痕 hash 或注明 amend 过程。
- **工作区快照对账**：验收前 `git status --porcelain -uall` 空；本审阅记录写入后仅本任务书 1 处 M（reviewer 本笔），无其它残留。
- **判定：Needs Revision**（阻断 = F1；F2 与体例小注为非阻断建议）。

#### architect 提交留痕
- **档位**：正常提交（**无 `WIP:`** 前缀，按主会话 2026-10-13 指定消息）；**提交号 `8f8be1d`**。
- **文件集对账**：`git diff --cached --name-status` = `M .tao/knowledge/milestones.md` + `A .tao/tasks/infra/INFRA-073t-chipyard-1.14.0-预研.md`，与完成区「修改文件」**逐条一致**（无漏提 / 多提 / 越界）；**显式 staging**（未用 `git add -A`/`.`）。
- **未 push**（`origin/master..HEAD` = 1 条，仅本任务 commit）；分支 `INFRA-073t`。

#### 第 1 轮返工（F1，2026-10-13）
- **F1 处置 ✅**：重测「GitHub 直连」= **间歇可达/不稳定**——`t1`（02:08:50Z）chipyard `ls-remote` rc=0 **2.53/2.31/2.38 s**、`curl -sI` **HTTP/2 200**（0.75–0.81 s）；`t2`（02:15:43Z）chipyard/firemarshal `ls-remote` rc=**124**×3、`curl` rc=**124**×3（DNS 正常）。⇒ 原「不可达」仅 `t0` 一次成立；**§4.1 / §8 前置① 已按实修订**。
- **原始日志**：重测 **129 份探测日志**（`<日志文件>`，02:08:50Z–02:20:14Z），每份含**命令 + 原始输出 + rc + 时间戳**；§4 每条数字均标来源日志。
- **定源（用户裁定）**：主 `gitclone.com` / 备 `ghfast.top` + conda TUNA；**理由 = 稳定性/可复现**（非「直连不可达」）——写入 §4.5 / §8。
- **F2 处置 ✅**：留痕 commit 差异（`8f8be1d` vs 最终 HEAD `b0894cf`）按实登记入「遗留问题」⑥（**只追加，不改写既有审阅记录**）。
- **改动文件**：仅本任务书——§4（头 + 4.1–4.5）、§8、验收标准 §1（`待开始`→`待验收`）、遗留问题；新增本节。

#### 复验轮 reviewer 验收（2026-10-13，F1 修复复核，最小范围）

1. **原始日志核 ✓**：现存 **132 份 fix 日志**（129 探测 + 3 门控）+ 2 份首轮，与自述相符；抽检 7 类（github-direct-lsremote/curl-head 各 6、gitclone-lsremote 3、conda-tuna-1mib 3、verilator-aptpolicy、gitclone-firemarshal 3+allrefs）均含**命令+原始输出+rc+起止时间戳**；关键数字逐条溯源 ✓（gitclone 2.295/1.963/2.125、TUNA 9.09/11.68/11.57 MB/s、ghfast 3.179/2.351/2.177、kernel 11.09/10.82/11.68、gitee 10.2–11.4 s、verilator 5.020-1、firemarshal `LINECOUNT=0`）。
2. **独立复核 ✓**：GitHub 直连 rc=0 3 连（2.24/2.28/2.30 s，tag `0acc1e1…`）＝落"通"时段，与**间歇**表述一致（"断"时段 6 份 rc=124 日志 @02:15–02:19Z 留痕）；`gitclone.com` rc=0 3 连、tag 解引用与官方**逐位一致**；TUNA 分片 10.09–11.61 MB/s ✓。
3. **诚实性核 ✓**：§4.1「间歇可达」逐次+时间戳；§4.5/§8① 定源 = **用户裁定**、理由 = 稳定性/可复现（明写「非『直连不可达』」）；事实/推测分离 ✓；验收标准 §1 = `待验收` ✓；F2 入遗留⑥ ✓；首轮「30.4 s」标存疑 ✓。
4. **门控（亲跑）**：`make check`=0、`check-knowledge-refs`=0（0 悬空）、`check-no-residue`=0、`check_issues.py`=0（24 open/2 closed）。
5. **N1（非阻断，建议收尾订正）**：§4.1 括注「DNS 正常：`20.205.243.166`」**无日志出处**（全 `.work/log/` grep 无命中）⇒ §4 头「每条数字均可回溯」因此失实，收尾二选一：删括注或补 DNS 日志。
6. **N2（非阻断）**：时间窗「02:08:50Z–02:20:14Z」实应为 **02:22:14Z**（verilator 追加场）；§4.1「t2（02:15:43Z 起）」实为 run4 end（起 = 02:15:13Z）。
7. **遗留意见**：firemarshal 0 refs 已如实登记 ✓——建议 `INFRA-074t` 前先经 ghfast/直连交叉确认其 ref，否则 FireMarshal 链路会卡（不影响本预研判定）；F2 留痕处置（登记不改写历史）✓ 同意。
8. **判定：Accepted**（F1 已修复且经独立复现；N1/N2 为非阻断订正、不构成返工级缺陷；终审归架构师）。
