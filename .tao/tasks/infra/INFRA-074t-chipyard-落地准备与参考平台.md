# INFRA-074t: Chipyard 1.14.0 落地准备与 (1) 参考平台跑通

**模块**：infra
**项目里程碑**：M8
**依赖**：`INFRA-073t`（预研，`已验证`；结论/测速/清单**只引用不复制**）+ `ADR-0024`（Chipyard 基线，**提案 Candidate、待用户逐条确认**）+ **用户授权开始下载**（源已裁定）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 背景与立项来源

- **用途与落法（用户 2026-10-13 裁定）**：Chipyard 用途 = 「**1/2/3**」；落法 = 「**先预研（推荐）**」；**本任务 = 预研（`INFRA-073t`）通过后的落地 + (1) 参考平台**。
- **上游基线（引用 `ADR-0024 D1/D2`，**提案待确认**）**：Chipyard **`1.14.0`**，commit **`0acc1e1de2d3284bcd4d876956932a013ffe1949`**；锁定方式 = 主仓 `[[component]]` + 子模块快照锁册。
- **下载源（用户 2026-10-13 已裁定；细则指针 → `INFRA-073t §4.5`，**不复制**）**：GitHub 主仓 + 全部子模块 = 主 `gitclone.com` / 备 `ghfast.top`；conda = **TUNA**（conda-forge/defaults）、ucb-bar 通道走 `conda.anaconda.org` 直连。

## 前置（开工条件；任一未满足 ⇒ 不得开工 / 停下报告）

1. **用户授权开始下载**（`mirrors.md` 流程第 4 步；源已裁定但**下载本身须授权**）。
2. `ADR-0024` 的 `D1`–`D5` **逐条确认**（**未确认前不得改 `manifests/`**）。
3. **交叉确认 FireMarshal ref 可取**（⚠，见 P2）——`INFRA-073t` 遗留⑤：`gitclone.com` 对 `ucb-bar/firemarshal` **0 refs（空）**、直连 GitHub `rc=124`，**其 ref 可取性未确认**；须先经 `ghfast.top`/直连交叉确认，否则 FireMarshal/内核链路会卡（**不影响 P3/P4 最小冒烟**）。

> **依赖说明**：P1（环境）/ P2（拉取主仓 + lite 子模块）/ P3（最小构建）**不依赖** FireMarshal ref；仅 **P4 的「可选 Linux」**依赖之 ⇒ 该前置于 P4 前确认即可。

## 分相范围（每相完成即报进度；**可先交 P1/P2**）

### P1 — 环境准备
- 安装 **conda（Miniforge，libmamba 默认）+ mamba**（conda 源 = **TUNA**）；安装 **sbt**。
- 安装 **Verilator ≥ `5.022` 并 pin**（apt 仅 `5.020` ✗ ⇒ 源码编译（`veripool.org` / GitHub release 经 `ghfast.top`）或 conda-forge 版本）；**版本入记录**（若 `ADR-0024 D2` 确认，则入锁）。
- **工具链隔离**（`ADR-0024 D4` 草案）：**不得**用 Chipyard conda 工具链**覆盖** v5 既有 `gcc`/`llvm`/`picolibc`（`PATH` 处理须显式记录）。
- 产出：`conda --version` / `mamba --version` / `sbt --version` / `verilator --version`（**≥5.022**）原始输出；环境清单落 `.work/log/<模块>/`。

### P2 — 拉取（主仓 + lite 子模块）
- 落 `manifests/components.lock.toml` 的 `chipyard` 条目（commit + `shallow_ref = "1.14.0"` + `[[component.source]]` 主/备源；**逐字段对齐既有体例**）+ **新增** `manifests/chipyard-submodules.lock.toml`（`format = 1`；`path`/`url`/`commit` + `lite` 标记）。
- **先**交叉确认 FireMarshal ref（前置 3）；**再**拉取主仓（`gitclone.com` 主 / `ghfast.top` 备）与 **lite** 子模块（**禁** `--recursive` 全量 ✗，`ADR-0024 D3`）。
- **lite 子集以首次成功构建现场导出为准**（`git submodule status --recursive` 快照 + lite 初始化脚本），**不预先写死**（候选清单为推测，指针 → `INFRA-073t §5.4`，**不复制**）。
- 产出：`components.lock.toml` / `chipyard-submodules.lock.toml`（新）diff + 拉取日志（落 `.work/log/<模块>/`）。

### P3 — 最小构建（RocketConfig Verilator sim）
- 按上游 docs 流程（`build-setup.sh`/`init-submodules-no-riscv-tools.sh` 类，以 `1.14.0` 实际为准）完成 sbt/Chisel 预编译 + **RocketConfig Verilator** simulator 构建。
- 产出：simulator 可执行 + 构建日志（落 `.work/log/<模块>/`）。

### P4 — (1) 参考平台冒烟
- **必达**：跑通 **`pk`**（proxy kernel）于 RocketConfig Verilator sim（如 `make run-binary` / `LOADMEM` 路径，以 `1.14.0` 实际为准）。
- **可选**：跑通 **Linux**（依赖 FireMarshal + 内核；见前置 3）。
- **对照**（`ADR-0024 D5` 草案）：将 `pk` 结果与**我们 QEMU** 的结果对照（对照口径/边界**记录在案**，不引入新 oracle）。
- 产出：运行日志 + 退出码；对照记录。

## 长任务规则（每相涉及长命令时必遵守）

1. **脱离生命周期**：长构建/长下载用 `setsid nohup <cmd> > <log> 2>&1 &`，**落完成标记** `XXX_EXIT=$rc`；**禁**会话内等待器。
2. **并发**：`JOBS=8`，**禁全核** `-j$(nproc)`；**一次只跑一个**长任务。
3. **超时判据**：完成为 `rc=0`；`timeout` 的 **`124` 判 FAIL**。
4. **启动前申报**：预计耗时 + 磁盘占用（量级为**推测**，指针 → `INFRA-073t §5.2/§5.3`）。
5. **诊断超时**：约 60 min 无根因 ⇒ **停下报告**，不试错。
6. **每相完成即报进度**（可先交 P1/P2），不积压。

## 接口规范

- **输入**：`INFRA-073t`（结论/测速/清单/(3) 复用清单，(已验证)）；`ADR-0024`（提案）；`manifests/*.lock.toml` 现有体例；`mirrors.md` 流程；用户授权（下载）。
- **输出**：`manifests/components.lock.toml`（`chipyard` 条目）+ `manifests/chipyard-submodules.lock.toml`（新增）；环境就绪证据 + lite clone + RocketConfig Verilator 构建 + `pk`（+ 可选 Linux）跑通；日志落 `.work/log/<模块>/`、一键证据脚本落 `.work/evidence/<任务ID>/`。
- **约束**：**不改** `spec/`、`contracts/`、组件补丁（`docs/Process-01`）；Chipyard **不进** v5 组件补丁集；**不覆盖** v5 工具链（`ADR-0024 D4`）；引用 `INFRA-073t` 只**指针、不复制**。

## 验收标准

1. P1：`conda`/`mamba`/`sbt` 就绪 + `verilator --version` **≥5.022**（原始输出）；**未覆盖** v5 工具链（证据）。
2. P2：`components.lock.toml` 条目逐字段对齐既有体例；`chipyard-submodules.lock.toml` 为新文件、`format=1`、含 `path`/`url`/`commit` + `lite` 标记；**lite 而非全量**（`git submodule status` 计数佐证）；FireMarshal ref 已交叉确认（或显式登记未确认）。
3. P3：RocketConfig Verilator simulator 构建成功（simulator 路径 + 构建退出码）。
4. P4：`pk` 跑通（运行日志 + 退出码）；Linux（可选）状态登记；与 QEMU 对照记录在案。
5. 长任务均有 `setsid nohup` + `XXX_EXIT=$rc` 落盘；无 `124` 未处置。
6. 门控：`make check`、`check-knowledge-refs`、`check-no-residue`、`check_issues.py` 各 `rc=0`。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-074t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；**禁** `cmd | tee`/`| tail` 吞码。
4. **只动本任务范围**（`manifests/` 两文件 + 环境 + `.work/` 日志）；越界须披露。
5. **事实与推测分开写**；任务书/记录中**不得**写字面 `.work/<具体路径>`（用 `<>` 占位）。
6. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、捕获退出码、计数不写死）。
8. **不改** `spec/`、`contracts/`、组件补丁。

## 引用（指针，**不重复复制**）

- **测速 / 镜像候选排序 / 定源理由** → `INFRA-073t §4`（**内容溯源，非执行必需**）。
- **(3) 复用清单** → `INFRA-073t §6`；**(2) 结论** → `INFRA-073t §7`；**lite 候选子集** → `INFRA-073t §5.4`（**推测**）；**成本量级** → `INFRA-073t §5.2/§5.3`（**推测**）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### architect 提交留痕（2026-10-13）
- **档位**：规划产出提交（新任务书 `待开始`，无 `WIP:` 前缀）。
- **任务内容提交**：**`3055be6`**（信息 `M8 规划：Chipyard 基线 ADR（提案，待逐条确认）+ 立 INFRA-074t（下载/环境/参考平台）`）；**本留痕为其 follow-up 提交**（**未 `--amend`**，避免 `INFRA-073t` F2 类留痕 hash 不一致）。
- **文件集对账**：`git diff --cached --name-status` = `A .tao/adr/adr-0024-chipyard-baseline.md` + `A .tao/tasks/infra/INFRA-074t-chipyard-落地准备与参考平台.md` + `M .tao/knowledge/milestones.md`（**显式 staging**，未用 `git add -A`/`.`）——与本任务「规划产出 = ADR + 任务书 + `milestones.md`」**逐条一致**（无漏提 / 多提 / 越界）。
- **未 push**（`origin/master..HEAD` = 1 条；分支 `M8-规划`）。
