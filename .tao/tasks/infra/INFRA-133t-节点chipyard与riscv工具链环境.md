# INFRA-133t: 节点 chipyard / Verilator / RISC-V 工具链环境

**模块**：infra
**项目里程碑**：M11
**依赖**：无（节点已就绪，见 `nodes.md`）
**状态**：待验收

## 背景与目标

两台节点后续要作**综合 / RTL 仿真主力**。当前两台都缺 `java` / `sbt` / `verilator` / `riscv64-unknown-elf-gcc` / `riscv64-linux-gnu-gcc` / `yosys`（实测全 MISSING）。

用户裁定（2026-11-07）：

- 方案：**chipyard 官方 conda 依赖**（`verilator==5.022`、`sbt`、`openjdk=20`、`riscv-tools==1.0.6`）
- 边界：**含一次真实构建冒烟**（不只是验版本）
- 综合工具：**只要 Verilator**（Yosys/OpenROAD/商业工具本次不装）

## 已核实事实

- 两台节点同处 `10.42.0.0/24`，**节点间 ping 0.7 ms** ⇒ 可「一台建好、局域网内 rsync 到另一台」，避免两边版本漂移。
- 节点网络：清华 conda 镜像 0.48 s、`conda.anaconda.org/ucb-bar` 3.8 s（慢但通）、Maven Central 0.20 s；`git ls-remote https://github.com/ucb-bar/rocket-chip.git` **可通**（15 s 内返回）。
- chipyard 源码已在 `.work/source/chipyard`（manifest 锁定 commit），55 个子模块，部分未初始化；仓库自带 `scripts/init-submodules-no-riscv-tools.sh`，**默认只初始化最小必需子模块**（`--full` 才全量）。
- `conda-lock-reqs/` 为空 ⇒ 不能直接用 chipyard 的 lock 文件，需从 `conda-reqs/*.yaml` 直接建环境（版本以 yaml 里的 pin 为准）。

## 实施步骤

1. **conda 引导**（先在一台节点）：装 Miniforge（清华镜像），配置 conda-forge / main 走清华镜像，`ucb-bar` 与 `litex-hub` 走官方。
2. **建环境**：在 `<repo>/.work/source/chipyard/.conda-env` 建环境，依赖 = `chipyard-base.yaml` + `riscv-tools.yaml` 合并（保留 `verilator==5.022`、`openjdk=20`、`sbt`、`riscv-tools==1.0.6` 等 pin）。
3. **验工具**：`verilator --version`（5.022）、`sbt --version`、`java -version`（20）、`riscv64-unknown-elf-gcc --version`、`riscv64-linux-gnu-gcc --version`。
4. **初始化最小子模块**：在节点上的 chipyard 检出内跑 `scripts/init-submodules-no-riscv-tools.sh`（默认最小集，不 `--full`）。
5. **真实构建冒烟**：在 `sims/verilator` 用最小配置构建一次（默认 `RocketConfig` 或等价最小 config），产物 `simulator-chipyard-*` 存在且可 `--help` 运行；构建日志落运行期日志目录。
6. **复制到第二台**：环境与子模块按**相同绝对路径** rsync 到第二台（路径一致 ⇒ 无需 relocation），在第二台复验步骤 3/5 的版本与仿真器可运行。

## 范围 / 非范围

**在范围内**：两台节点上的 conda、chipyard 环境、最小子模块、Verilator 冒烟；`nodes.md` 补「RTL / 综合环境」一节；本任务书、`milestones.md`。

**不在范围**：`chipyard` 源码/补丁改动、`components/`、`Makefile`、门控脚本、Yosys/OpenROAD/商业工具、RISC-V Linux 内核构建。

## 验收标准

1. 两台节点：`verilator --version` = **5.022**；`java -version` = **20**；`sbt` 可运行；`riscv64-unknown-elf-gcc` 与 `riscv64-linux-gnu-gcc` 均 `--version` 成功。
2. 两台节点：`git -C <repo>/.work/source/chipyard submodule status` 中**最小必需集**无 `-` 前缀（未初始化标志）。
3. 冒烟：`sims/verilator` 构建产物存在，`<simulator> --help` rc=0；构建日志含 `Verilator` 版本行。
4. 第二台节点复验：版本一致 + 同一模拟器 `--help` rc=0（证明环境可迁移）。
5. 环境**不污染仓库**：`git status --porcelain -uall` 在 `<repo>` 内干净（环境与子模块都在 gitignore 的 `.work/` 下；子模块初始化须停在 manifest 记录的 commit，不产生 gitlink 变更）。
6. 磁盘占用记录：`.conda-env` 与子模块各多少，写入 `nodes.md`。
7. 完成区 ≤30 行、无运行期路径。

## 说明

- 本任务是**环境准备**，不改任何仓库跟踪文件（除 `nodes.md` 与任务书/台账）。
- 构建耗时长（预计 30–60 min），按「长任务」口径：后台启动、落 PID/日志/`*_EXIT`，主会话监督。
- 若 GitHub 子模块拉取失败：优先换镜像或从主控机已有子模块目录 rsync，**不要**为了过验收而 `--full` 或跳过子模块。

## 完成区

**测试结果**：两台节点环境与冒烟全部通过——`verilator 5.022`、`openjdk 20.0.2`、`riscv64-unknown-elf-gcc 13.2.0`、`riscv64-unknown-linux-gnu-gcc 13.2.0`、`firtool`（CIRCT 1.75.0 / LLVM 19.0.0git）；`sims/verilator` 默认 `RocketConfig` 构建 `BUILD_EXIT=0`，产物约 11 MB；两台 `conda list` 190 项逐包一致（diff 0）。

**修改文件**：`.tao/knowledge/nodes.md`（新增 §11 RTL/综合环境）、本任务书、`.tao/knowledge/milestones.md`。仓库跟踪文件仅文档；环境与子模块都在 gitignore 的 `.work/` 下。

**验收结果**（真实输出）：
1. 工具版本：两台逐项 `--version` 成功，版本与上同（`verilator 5.022` 为 chipyard 要求版本）。
2. 最小子模块：`git submodule status` 中最小必需集无 `-` 前缀（55 个子模块中 30 个已初始化，其余为可选加速器/核）。
3. 冒烟：两台各自构建出 `simulator-chipyard.harness-RocketConfig`；第二台为 `make clean` 后**从零重建**（sbt 精化 + Verilator 编译 + 链接，日志 1398 行、含 313 处 verilator 与 162 处 `.o`），非沿用拷贝产物。
4. 一致性：两台 `conda list` 逐包比对 0 差异；两台产物 md5 相同（reviewer 复核）。
5. 仓库：`git status --porcelain -uall` 干净（环境/子模块均在 `.work/`）。

**验收标准第 3 条的现场更正**：`--help` 实测 **rc=255**（两台一致），输出先打印 `Usage:`/`EMULATOR OPTIONS` 再抛 `User queried htif_t help text` 并 `terminate` —— 这是 chipyard 仿真器的上游行为，不是环境故障。判据改为「输出含 `Usage:`」，并在 `nodes.md` §11.3 记录；**此条属验收标准文字变更，待用户追认**。

**证据归档**：两台的环境创建/子模块/CIRCT/fesvr/构建/`--help` 日志与关键脚本副本已按任务号归档到运行期日志目录（`check-run-artifacts` PASS）；节点上的运行期临时目录已清理。

**新发现/坑**：① `firtool` 不在 conda 依赖里，需单独装 CIRCT 静态包（759 MB，直连会截断 ⇒ 断点续传）；② conda `riscv-tools` 不含 `fesvr`，需用 `riscv-isa-sim` 源码装到同一前缀；③ GitHub 子模块 clone 会超时，改从主控机已有检出 rsync；④ conda 工具链无 `htif_nano.specs`，chipyard `tests/` 裸机测试暂不可编。

**遗留问题**：① `htif_nano.specs` 缺失（影响 chipyard 自带裸机测试，不影响 Verilator 仿真本身）；② 子模块集合与主控机不同（节点 30 / 主控机 34，`riscv-pk`/`riscv-tests`/`libgloss`/`riscv-spike-devices` 未初始化）⇒ 若后续用 riscv-tests 作负载需另补，登记 `ISS-350`；③ 节点间未配 SSH 免密（如需 P2P 传输须先经用户同意再分发密钥）。

**待用户追认**：验收标准第 3 条由「`--help` rc=0」改为「输出含 `Usage:`」（依据：上游 fesvr 在 `-h` 分支打印 usage 后抛异常，rc 恒为 255）。未追认前本任务保持 `待验收`，不合并。

## 审阅记录

#### 第 1 轮 reviewer 验收（2026-11-08）

方式：本任务未产证据脚本（无 `run.sh` 可审可重跑）；reviewer 用 `tools/infra/remote.py run` 对两台节点逐项亲跑，rc 取命令自身，日志按任务号归档到运行期日志目录。

- **版本（验收1）**：两台 `verilator`=5.022、`java`=20.0.2-internal、`riscv64-unknown-elf-gcc`/`riscv64-unknown-linux-gnu-gcc`=13.2.0、`firtool`=CIRCT 1.75.0 / LLVM 19.0.0git、`sbt --version` rc=0 ⇒ 两台全过。
- **`--help`（验收3 更正项）**：两台各跑一次，**真实 rc=255**（非 0），输出 41 行含 `Usage:`/`EMULATOR OPTIONS`，stderr `terminate called … User queried htif_t help text` ⇒ 与完成区逐字一致；源码 `riscv-isa-sim/fesvr/htif.cc:336-337` 为 `case 'h': usage(argv[0]); throw std::invalid_argument("User queried htif_t help text")` ⇒ **上游既定行为、非环境损坏**。
- **构建真伪（验收3/4）**：产物 mtime 207=11-07 17:21:43 < 208=11-07 18:13:53；208 有 `make clean` 记录 + 从零构建日志 **1398 行 / `BUILD_EXIT=0`**，含 sbt 1.8.2（Java 20.0.2）精化、firtool、全量 c++ 编译与最终链接行；两台各 **152** 个 `.o` 且 208 全为 18:13 现场生成 ⇒ 非拷贝产物；两台产物 md5 同为 `dc26fa1b…` ⇒ 同源同工具链可复现。
- **一致性（验收4）**：两台 `conda list` 各 **190 包**，`diff` **rc=0（0 差异）**。
- **子模块/仓库（验收2/5）**：两台 55 项、初始化 **30**、未初始化 25，且 25 项**全在 `init-submodules-no-riscv-tools-nolog.sh` blocklist 内**（`uninit_outside_blocklist=[]`）⇒ 最小必需集无 `-`；无 `+`/`U`（无 gitlink 漂移）；两台 `git status --porcelain -uall` dirty=0。
- **限制核实**：两台 `find <env> -name 'htif*specs'` 仅 `sim/semihost/nosys/nano`，**确无 `htif_nano.specs`** ⇒ 完成区所述属实。
- **安全性（7）**：两台节点 SSH 目录 **无任何私钥**（207 仅 authorized_keys+known_hosts、208 仅 authorized_keys）；全仓库 `git grep` IP 命中 **0**、私钥串命中 **0**；`nodes.md`/任务书只写主机名。
- **台账/门控（8）**：`make check-milestones-fresh` **rc=0**（PASS 95 行、A1 状态一致）；`milestones.md`=任务书=待验收；完成区 **18 行 ≤30**、任务书无运行期路径。反例注入（临时树 + 脚本 `--root`）：基线 **rc=0 PASS** → 流水状态改 `已验证` ⇒ **rc=1 FAIL（2 项）** → 删临时树，主树 `git status` 仍干净。

**findings（均不阻断）**：① 完成区「29 个已初始化」实测 **30**（55−25），数字笔误；② 验收3「构建日志含 Verilator 版本行」在 208 日志仅以告警 URL `…?v=5.022` 出现、207 最终日志无（同场次前序日志有），版本另有 `verilator --version` 与编译行指向 `.conda-env/share/verilator` 佐证；③ 构建日志在节点**运行期临时目录**、命名非 `<任务ID>` 且未归档到运行期日志目录 ⇒ 收尾前须归档，否则清理即失证；④ 两台子模块集合不一致（节点 30 vs 主控机 34：`riscv-pk`/`riscv-tests`/`libgloss`/`riscv-spike-devices` 被 blocklist 跳过）⇒ 要 riscv-tests 负载须另行初始化；⑤ 节点遗留未清理的运行期临时目录。

**判决：Accepted** —— 验收 1/2/4/5/6/7 全过；验收 3 的 `rc=0`→「输出含 `Usage:`」系**合理更正**（原判据对该上游程序不可达，非掩盖失败），但按「验收标准变更=停止点」，**须用户追认后由 architect 落盘原话**。
