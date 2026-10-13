# INFRA-074t: Chipyard 1.14.0 落地准备与 (1) 参考平台跑通

**模块**：infra
**项目里程碑**：M8
**依赖**：`INFRA-073t`（预研，`已验证`；结论/测速/清单**只引用不复制**）+ `ADR-0024`（Chipyard 基线，**提案 Candidate、待用户逐条确认**）+ **用户授权开始下载**（源已裁定）
**状态**：待验收

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

## P1/P2 执行记录（2026-10-13，本地）

> **申报（估算，开工前）**：P1 ≈25–45 min / 磁盘 ≈3–5 GB；P2 ≈30–60 min / 磁盘 ≈6–10 GB。**实测**（非估算）：P1 conda env ≈6 min、1.9 GB；P2 主仓 clone **160 s**、子模块 init **2963 s**、修复 ≈3 min，落盘 **≈304 MB**（`.git` 250 MB + 工作树 54 MB）。**一次只跑一个长任务**；均 `setsid nohup` 脱离 + `*_EXIT` 标记。

### P1 环境
- **conda/mamba**：`$HOME/miniforge3` **预先已存在**（2026‑01 预装）⇒ **未重装**；实测 `conda 25.11.1`、`mamba 2.4.0`、solver = libmamba。日志 `<日志>`。
- **sbt**：`2.0.9`（conda‑forge 经 **TUNA**；独立 env `cy`）。
- **Verilator**：`5.022`（conda‑forge 经 **TUNA**）⇒ **≥5.022 ✓**；与 chipyard `conda-reqs/chipyard-base.yaml` 的 **`verilator==5.022` 逐字一致**。原始输出 `<日志>`。
- **工具链隔离（D4）** ✓：conda 工具链**不在**默认 `PATH`（`command -v verilator` 仍 = `/usr/bin/verilator 5.020`）；**未**改 `~/.bashrc`；v5 `components/`（llvm‑project/qemu/picolibc/embench‑iot）**未动** ⇒ 未覆盖 v5 工具链。证据 `<日志>`。

### P2 拉取
- **FireMarshal ref 交叉确认（前置 3，✅ 已解决）**：仓库实为 **`firesim/FireMarshal`**（`ucb-bar/firemarshal` 直连 `Repository not found`；`INFRA-073t` 的「0 refs」= 查错仓名）⇒ 主 `gitclone.com` / 备 `ghfast.top` / **直连** 三路 **均 rc=0、392 refs** ✓。日志 `<日志>`。
- **主仓**：主源 `gitclone.com`、`--depth 1 --branch 1.14.0` ⇒ **HEAD = `0acc1e1de2d3284bcd4d876956932a013ffe1949`（与预期逐位一致 ✓）**、`describe=1.14.0`、160 s、16 MB。日志 `<日志>`。
- **lite 子模块**：按上游 `scripts/init-submodules-no-riscv-tools.sh`（**minimal set**）初始化；**未** `--recursive` 全量 ✗。`gitclone.com` 对部分 pinned commit 报 *unadvertised object* / 空仓 ⇒ 改备源 **`ghfast.top`**（可服任意 commit）修复。**终态 `git submodule status`：55 顶层，`+`（错 commit）0 处、lite 子集 29 个全部命中 pinned commit** ✓。
- **实际 lite 子集（29，现场导出）**：`fpga/fpga-shells`；`generators/`{bar‑fetchers, boom, constellation, diplomacy, hardfloat, icenet, rerocc, rocc‑acc‑utils, rocket‑chip, rocket‑chip‑blocks, rocket‑chip‑inclusive‑cache, shuttle, testchipip}；`sims/firesim`；`software/`{baremetal‑ide, embench/embench‑iot, firemarshal, firesim‑paper‑workloads, tacit_decoder}；`tools/`{DRAMSim2, axe, cde, dsptools, firrtl2, fixedpoint, install‑circt, rocket‑dsp‑utils, torture}。**排除 26**（riscv‑tools 工具链 / 可选核 cva6·ibex·sodor·vexiiriscv·ara·gemmini·nvdla·mempress·saturn·tacit·fft·radiance·caliptra·compress‑acc / coremark·spec2017·zephyr·nvdla‑workload / libgloss / tools/circt）——见锁册 `lite=false`。

### P1/P2 门控扩展 + `INFRA-073t` 订正（追加，2026-10-13，分支 `INFRA-074t-gate`）

> **背景**：P2 使 `chipyard`（ADR-0024 D1「不入 v5 组件补丁集」）以 `enabled=true` 缺补丁集入锁 ⇒ `make check` 红（遗留①）。经主会话裁定走 **(a) 门控支持「参考型组件」**（**不选** (b) `enabled=false`——与其「ADR 后 flip enabled」政策冲突）。**注**：完成区「测试结果」所述 `make check rc=2` 系本小节之前的现场，已被本节取代。

- **门控假定点（定位）**：`tools/infra/manifest_check.py::check_components`（对每个 enabled 组件逐查 `patch_dir` 为目录 + `patch_series` 为文件）；`tools/infra/check_patch_tree.py`（改动前 `main` 第 354 行、`check_component` 第 163/164 行、`run_source_state`）**直取** `component["patch_series"]`/`["patch_dir"]` ⇒ 假定「每个 enabled 组件都有补丁集」。`check-index-blobs` 已用 `if patch_dir:` 容缺（**本次未改**）。
- **体例依据（字段命名）**：新增**布尔**字段 **`patchless = true`**——对齐本文件既有布尔字段 `enabled`/`shallow` 体例。**未**选 `role = "reference"`：`role` 现为**自由文本描述**（如 gem5 的 `"functional second reference"`），复用作控制标志构成**语义重载**（且 gem5 该值 `reference` 与「有补丁集」并存 ⇒ 不能用它判别）。
- **门控改动（最小面）**：① `manifests/components.lock.toml` 的 `chipyard` 条目加 `patchless = true`；② `manifest_check.py`：enabled 且 `patchless` ⇒ **允许**缺 `patch_dir`/`patch_series`，**但若同时声明二者则报错**；**非** `patchless` 组件**仍照旧必查**（**未放宽**）；③ `check_patch_tree.py`：`main`/`run_source_state` **跳过** `patchless` 组件，打印计数改为按「实际检查的补丁组件数」**现场统计**（不写死）。
- **可达 FAIL（两条，均 `cp`+md5 还原）**：① 去掉 `patchless = true` ⇒ `manifest-check` `ERROR: component chipyard: missing patch series …`（rc=2）、`check-patch-tree` `KeyError: 'patch_series'`（rc=2）——回到当前行为 ✓；② `patchless=true` **夹带** `patch_dir`/`patch_series` ⇒ `manifest-check` `ERROR: component chipyard: patchless component must not declare patch_dir/patch_series`（rc=2）✓。两条还原后锁册 **md5 逐位复原**、门控**回绿**。
- **门控结果**：`make check` **rc=0** ✓（**本任务达成判据**）；`check-modules`(L2)、`check-no-residue`、`check_issues.py`、`check-knowledge-refs` 各 **rc=0**。
- **`INFRA-073t` 订正（只追加）**：§4.4 表后**追加**「订正」行——FireMarshal 实仓 = **`firesim/FireMarshal`**（`gitclone`/`ghfast`/直连三路均 rc=0、**392 refs**）⇒ 遗留⑤「0 refs」系**查错仓名**，**原 ⚠ 不成立**（§4 原文与审阅记录**未改写**）。
- **证据**：`.work/evidence/<任务ID>/run.sh`（green **7/7**、`--inject` **14/14**，均 rc=0）；日志 `.work/log/<模块>/`。
- **遗留① 处置**：**(a) 已落地 ⇒ 关闭**（`chipyard` 保持 `enabled=true`，门控显式识别「参考型/无补丁集」）。

## 完成区

**测试结果**：一键证据脚本 `run.sh` 基线 **8/8 PASS（rc=0）**；`--inject` 注反例 → **可达 FAIL**（`lite_pinned` rc=1）→ `cp`+md5 还原 → **回绿（rc=0）**。**门控（门控扩展后，见「P1/P2 门控扩展」小节）**：`make check` **rc=0**、`check-modules`(L2) **rc=0**、`check-no-residue` **rc=0**、`check-knowledge-refs` **rc=0**、`check_issues.py` **rc=0**（24 open/2 closed）、`check-patch-tree` **rc=0**、`check-index-blobs` **rc=0**。
**修改文件**：`manifests/components.lock.toml`（+ `chipyard` 条目 + `patchless=true`）；`manifests/chipyard-submodules.lock.toml`（**新增**，79 条）；`tools/infra/manifest_check.py`、`tools/infra/check_patch_tree.py`（`patchless` 参考型组件支持）；`.tao/tasks/infra/INFRA-073t-*.md`（**仅追加**订正）；本任务书；`.tao/knowledge/milestones.md`（`INFRA-074t` 进度）；`.work/evidence/<任务ID>/run.sh`（新）；`.work/log/<模块>/*`（日志）。**未提交 git**（提交权归 architect）；`.cache/chipyard/**` 已 gitignore ✓。
**验收结果**：见 §P1/P2 执行记录 + 审阅记录·engineer 自审。P1 四项工具原始输出、P2 主仓 commit 逐位一致、锁册 schema/计数/pinned 命中**均由 `run.sh` 现场断言**（非抄录）。
**新发现/坑**：① **FireMarshal 仓名 = `firesim/FireMarshal`**（`ucb-bar/firemarshal` 不存在）——`INFRA-073t` 遗留⑤「0 refs」系查错仓名；**ref 三路可用**。② **`gitclone.com` 是缓存代理，服不了任意 pinned commit**（`unadvertised object`／空仓；`DRAMSim2` 首次得空仓）⇒ 子模块 pinned commit **须走 `ghfast.top`/直连**；主仓 tag clone 用 `gitclone.com` 仍可。③ **chipyard 1.14.0 pin `verilator==5.022`**（已对齐 P1）。④ 上游 `init-submodules-no-riscv-tools.sh`：递归更新**任一子模块失败即 `|| exit 1` 中止**，且 `set -u` 下 ERR 陷阱引用未绑定 `$submodule_name` ⇒ 需自建续跑/修复。⑤ **`enabled=true` 的「无补丁」组件使 `manifest-check`+`check-patch-tree` 红**（见遗留①）。
**遗留问题**：① **[需裁定]** `chipyard` 置 `enabled=true`（遵 `components.lock.toml` 头「ADR 后 flip」政策），但 ADR-0024 明确 chipyard**不入 v5 组件补丁集** ⇒ 触发 `manifest-check`（缺 `patch_series`）与 `check-patch-tree`（`KeyError: 'patch_series'`）**红**；**未为过闸改门控/改判定**。**候选解**：(a) 门控支持「无补丁/参考型组件」（后续任务）；(b) 置 `enabled=false`（不改门控，本任务**未**采纳，因疑与「不得为过闸改判定」冲突）。**请 architect/用户裁定 (a)/(b)**。② **P3（RocketConfig Verilator 构建）/ P4（pk 冒烟）未做**——本任务仅授权 P1+P2。③ lite 子集 = 上游 **minimal set**（非「首次成功构建现场」，P3 未跑）⇒ P3 起可据需收紧。④ 拉取期间换源/重试见日志（`gitclone.com` TLS/early‑EOF/504 瞬时失败多次 + `DRAMSim2` 空仓 1 次 ⇒ 换 `ghfast.top`）。⑤ **`patchless` 未全覆盖**：`tools/infra/apply_series.py`（`component["patch_dir"]`/`["patch_series"]` 直取）与 `tools/infra/make_patch.py` 对 `patchless` 组件**仍会直取** `patch_dir`/`patch_series`（**非 L1/L2 门控、当前不触发**，因 `.work/<source>/<chipyard>` 工作树不存在）⇒ **建议后续任务对齐**（本任务未改，登记待排期）。

## 审阅记录

#### 第 1 轮 engineer 自审（2026-10-13）
- **范围**：仅 P1+P2。逐行审 ① `gen-submodules-lock.py`、② `manifests/*` 两文件、③ `run.sh`。
- **逻辑正确性**：锁册 `commit` 一律取 **pinned**（`git submodule status --recursive` 首列 = 索引记录值，非工作树检出态）→ 与 `git ls-tree HEAD` 抽核**一致**；`url` 按 **path**（非 submodule name）取自属主 `.gitmodules`；lite 标记 = 顶层已初始化集（`^[ +]`），与 `git submodule status` **现场计数对账一致（29）**。
- **防造假**：`run.sh` 每条断言有**可达 FAIL**（`--inject` 实测 `lite_pinned` rc=1）；计数**现场统计**（`lite_count_live`，不写死）；`make check` 红为**现场 rc**，未改门控。
- **finding 处置**：

  | finding | 处置 | 改了什么 | 复验证据 |
  |---|---|---|---|
  | 子模块 url 按 `name` 解析漏 firemarshal `opensbi`/`linux`（name≠path） | ✅已修 | 改为**按 path** 解析属主 `.gitmodules` | 79 条 **0 空 url** |
  | `DRAMSim2` 空克隆致 `.git/modules` 损坏 | ✅已修 | `rm` 空 gitdir 后 re‑init（ghfast） | 命中 pinned `44322e2f` |
  | 首次 clone 与残留进程竞争 → `invalid index-pack` | ✅已修 | 杀残进程 + 清目录 + 单进程重跑 | `CLONE_EXIT=0` |
  | 子模块 init 因单个失败中止、未跑 phase‑2 | ✅已修 | 自建续跑脚本（ghfast） | 16 路径中 15 rc=0 + 1 单修 |
  | chipyard `enabled=true` → 2 门控红 | ⏸延后 | **未改**（遵「不得为过闸改判定」） | 登记遗留①，**待裁定** |

- **判决**：15/16 目标子模块经 ghfast 修复、`DRAMSim2` 单独修复 ⇒ **lite 29 个全命中 pinned**；主仓 commit 逐位一致。**P1/P2 达成**；遗留①（门控冲突，**需裁定**）、②（P3/P4 未授权）**如实登记**。状态 → `待验收`（**注**：遗留①虽为未决 finding，但属**任务设计冲突、需用户/架构师裁定**，非可实现侧修复项；按下发指令置 `待验收` 并显式上报）。

#### architect 提交留痕（2026-10-13）
- **档位**：规划产出提交（新任务书 `待开始`，无 `WIP:` 前缀）。
- **任务内容提交**：**`3055be6`**（信息 `M8 规划：Chipyard 基线 ADR（提案，待逐条确认）+ 立 INFRA-074t（下载/环境/参考平台）`）；**本留痕为其 follow-up 提交**（**未 `--amend`**，避免 `INFRA-073t` F2 类留痕 hash 不一致）。
- **文件集对账**：`git diff --cached --name-status` = `A .tao/adr/adr-0024-chipyard-baseline.md` + `A .tao/tasks/infra/INFRA-074t-chipyard-落地准备与参考平台.md` + `M .tao/knowledge/milestones.md`（**显式 staging**，未用 `git add -A`/`.`）——与本任务「规划产出 = ADR + 任务书 + `milestones.md`」**逐条一致**（无漏提 / 多提 / 越界）。
- **未 push**（`origin/master..HEAD` = 1 条；分支 `M8-规划`）。

#### 第 2 轮 engineer 自审（门控扩展，2026-10-13，分支 `INFRA-074t-gate`）
- **范围**：仅门控扩展 + `INFRA-073t` 订正。逐行审 ① `tools/infra/manifest_check.py`、② `tools/infra/check_patch_tree.py`（`main`/`check_component`/`run_source_state`）、③ `manifests/components.lock.toml`、④ `.work/evidence/<任务ID>/run.sh`。
- **逻辑正确性**：`patchless` 为**显式声明**才放行；**非** `patchless` 分支与改动前**逐行一致**（未放宽）；`patchless` 路径**主动拒绝** `patch_dir`/`patch_series`（防夹带）；`check_patch_tree` 打印计数已改**现场统计**（`checked` 变量）。边界：`patchless` 且 `patch_dir=""`（空串）**不触发**报错——属退化写法，可接受。
- **防造假**：`run.sh` green **7/7**、`--inject` **14/14** 均 rc=0；两条注入均有**可达 FAIL**（真实 `rc=2` + 错误文本匹配）；注入后 `git diff --name-only` 非空；还原用 `cp`+md5（**禁** `git checkout/restore/stash`）；计数 `printed==live`（现场，不写死）。
- **finding 处置**：

  | finding | 处置 | 改了什么 | 复验证据 |
  |---|---|---|---|
  | 计数断言误用被覆盖的 `LAST_OUT`（首轮 harness bug，误报 FAIL） | ✅已修 | 显式捕获 `check-patch-tree` 输出到 `patch_tree_out` | green 7/7（含计数 PASS） |
  | `run_source_state` 对 `patchless` 组件仍套「base+1」不变量 | ✅已修 | 显式跳过 + 打印 `patchless; skipped` | `--source-state` rc=0 |

- **判决**：门控**只加一条明确例外**（显式 `patchless` 参考型），**未放宽**其余组件；`make check` **rc=0**；两条 FAIL 路径可达且还原回绿；遗留① **(a) 落地 ⇒ 关闭**。状态保持 `待验收`（本追加小节 + 订正随 `INFRA-074t` 一并受验）。

#### architect 交叉复核 + 提交留痕（2026-10-13，分支 `INFRA-074t-land`）
- **档位**：**architect 交叉复核**（**reviewer 未跑本轮**）⇒ 任务**保持 `待验收`**、**待 reviewer 独立验收**（本留痕**不构成**独立验收，不置 `已验证`）。
- **交叉复核（architect 自跑，均现场 rc）**：`make check` **rc=0**；`make check-modules`(L2) **rc=0**；`check-no-residue` / `check-knowledge-refs` / `check-patch-tree` / `check-index-blobs` / `check_issues.py` 各 **rc=0**。日志 `/tmp/opencode/arch-INFRA-074t-land/*.log`（临时）。
- **提交**：**`105cb31`**（信息 `INFRA-074t(P1/P2): Chipyard 1.14.0 拉取（lite 29）+ 锁册 + 门控支持 patchless 参考型组件`）；**本留痕为其 follow-up 提交**（**未 `--amend`**，避免 hash 不一致）。
- **文件集对账**：`git diff --cached --name-status` = `A manifests/chipyard-submodules.lock.toml` + `M manifests/components.lock.toml` + `M tools/infra/check_patch_tree.py` + `M tools/infra/manifest_check.py` + `M .tao/tasks/infra/INFRA-073t-*.md` + `M .tao/tasks/infra/INFRA-074t-*.md` + `M .tao/knowledge/milestones.md`（**显式 staging**，未用 `git add -A`/`.`）——与本任务范围**逐条一致**（**无漏提 / 多提 / 越界**）。
- **遗留追加**：见「完成区·遗留问题」**⑤**（`patchless` **未覆盖** `apply_series.py`/`make_patch.py`，**非门控、当前不触发**，建议后续对齐）。
- **未 push**（`push` 只由主会话在 `/complete` 后执行）。

#### 第 1 轮 reviewer 验收（2026-10-13，独立重跑）
- **范围**：P1/P2 + 门控扩展 + 双锁册，对照验收标准逐条**自己重跑**（workdir=仓库根；注入还原全程 `cp`+md5，**禁** checkout/restore/stash；前后 `git status --porcelain -uall` 均 0 行、4 目标文件 md5 全复原 ✓）。
- **门控（真实 rc，无 `| tee` 吞码）**：`make check`=**0**、`make check-modules`(L2)=**0**、`check-no-residue`/`check-knowledge-refs`/`check_issues.py`(24 open/2 closed)/`check-patch-tree`(`4 component(s), 127 patches OK`)/`check-index-blobs` 各=**0**。
- **独立注入 I1**（自去 `patchless`，sed 删行）：`make manifest-check` **rc=2** `ERROR: component chipyard: missing patch series …`；`make check-patch-tree` **rc=2** `KeyError: 'patch_series'`（位于 `series_path = ROOT / component["patch_series"]`）⇒ 可达 FAIL ✓；`cp` 还原 md5 `95248c825e14ecf02bf94cd53dba8007` **逐位复原**、双门控回绿（rc=0/0）。
- **独立注入 I2**（`patchless=true` 夹带 `patch_dir`/`patch_series`）：`make manifest-check` **rc=2** `ERROR: component chipyard: patchless component must not declare patch_dir/patch_series` ✓；还原复原回绿。
- **未放宽核 I3**（**非** `patchless` 的 picolibc 去掉 `patch_dir`/`patch_series`）：`make manifest-check` **rc=2** `missing patch series` + `make check-patch-tree` **rc=2** `KeyError: 'patch_series'` ⇒ 例外**仅限显式 `patchless`**，非普遍放宽 ✓。
- **证据脚本重跑**：gate `run.sh` green **7 PASS rc=0**；`--inject` **14 PASS / 0 FAIL rc=0**（I1 rc=2、I2 rc=2、两次 md5 复原、还原后回绿）。P1/P2 `run.sh` 8 项全 rc=0；`--inject` `lite_pinned` FAIL(rc=1)→md5 `430152a6…` 复原→回绿 rc=0。计数现场统计（`checked`/live 对账）非写死 ✓。
- **锁册 vs 现场（全量）**：`git submodule status --recursive` **79** 条 = 锁册 79 条（path 集合相等、commit **0** 处不符、`+` 错配 **0**）；`lite=true` **29** 与实初始化 **29** 精确一致（lite↔init 0 处不符）；抽样 **10** 条（fpga-shells/boom/rocket-chip/firemarshal/embench-iot/DRAMSim2/torture/firesim/hardfloat/cde）commit 逐位 **MATCH**；顶层 **55** ✓（排除 26 ✓）；`components.lock.toml` chipyard commit == 检出 HEAD `0acc1e1de2d3…` ✓、体例与 llvm/qemu 一致（repository/commit/shallow/shallow_ref/role + `[[component.source]]`×2，补丁字段换显式 `patchless`）✓、`format=1`/79 条/0 空 url ✓。
- **文档核**：`INFRA-073t` 订正 = **只追加 +2 行**（原文/审阅记录未改写）✓，且「392 refs」经我 `git ls-remote https://github.com/firesim/FireMarshal.git` **rc=0、392 行**独立复核 ✓；074t「P1/P2 完成、P3/P4 未做、遗留⑤在」如实 ✓；未伪称 reviewer 已验收（明标「reviewer 未跑本轮、待 reviewer 独立验收」）✓。
- **阻断（文档如实 / 硬约束 3「完成区与真实输出逐条对齐」）**：① 门控扩展记录 + 第 2 轮自审写「`--inject` **13/13**」，我实测 **14 PASS**（I1 8 + I2 6）——数字与真实输出不符；② 完成区「测试结果」仍写 `make check rc=2`（现场 **rc=0**，仅有「已被本节取代」注）、「修改文件」漏 `tools/infra/manifest_check.py`/`check_patch_tree.py`/`INFRA-073t`/`milestones.md`（追加小节与 architect 留痕有披露，但完成区清单未对齐）。
- **返工要求（不改代码/门控/锁册）**：就地订正 ①② 记录数字与完成区清单（13→14、测试结果改注或更新、修改文件补 4 项），复验即绿。
- **非阻断建议**：③ `milestones.md` INFRA-074t 行状态列仍「待开始」（应「待验收」，收尾可修）；④ 子模块锁册头注释「firesim … excluded」与 `sims/firesim`（lite=true）不符，宜改「firesim 嵌套子模块/VLSI excluded」；⑤ 遗留⑤陈述属实（实测 `apply_series.py:108/109`、`make_patch.py:162/163` 直取补丁字段），维持登记待排期。
- **判决**：**Needs Revision**——仅 ①② 记录对齐项未过（说 N 跑出 M / 完成区与真实输出不逐条一致）；技术面（门控可达 FAIL、未放宽、锁册一致性、全部门控 rc）**均独立验证通过**，无代码缺陷。

#### architect 记录订正 + 落地（2026-10-13，分支 `INFRA-074t-fix`）
- **依据**：第 1 轮 reviewer 判 `Needs Revision`——仅 ①②③ 记录对齐项未过（技术面无缺陷）。本次**只订正记录/注释，不改代码/门控/锁数据**。
- **① 计数订正**：`P1/P2 门控扩展`·「证据」+ 第 2 轮自审的 `--inject` **13/13 → 14/14**（与 reviewer 独立重跑一致）。
- **② 完成区「测试结果」**：`make check` 由旧注 `rc=2`（门控扩展前现场）订正为 **`rc=0`**，并补 `check-modules`(L2)/`check-knowledge-refs`/`check-patch-tree`。
- **③ 完成区「修改文件」**：补 `tools/infra/manifest_check.py`、`tools/infra/check_patch_tree.py`、`.tao/tasks/infra/INFRA-073t-*.md`、`.tao/knowledge/milestones.md`（对齐实际文件集）。
- **措辞订正（非阻断④）**：`manifests/chipyard-submodules.lock.toml` 头注「`firesim … excluded`」→「`firesim` 自身 **included**、其 nested 子模块（`sim/*`,`platforms/*`）excluded」（**只改注释文字**，锁数据未动；同步订正临时生成器注释）。
- **`milestones.md` 核**：`INFRA-074t` 行**保持 `待开始`**（P3/P4 未做），「进度：P1/P2 + 门控扩展 已完成；P3/P4 未做」注明仍在 ⇒ **不改**。
- **交叉复核（architect 自跑，均现场 rc）**：`make check` / `check-modules`(L2) / `check-no-residue` / `check-knowledge-refs` / `check_issues.py` / `check-patch-tree` / `check-index-blobs` 各 **rc=0**（日志 `/tmp/opencode/arch-INFRA-074t-fix/*.log`）。
- **任务状态**：**保持 `待验收`**（本留痕为 review 收口订正，**不构成**独立验收）。**未 push**。

## P3/P4 执行记录 + 落点修正（2026-10-13；**主会话代行**；追加）

> **主会话代行声明**：P3（RocketConfig Verilator 构建）/ P4（参考平台冒烟）**及本次落点修正**均由**主会话代行**完成（**非**本任务 engineer 子代理原生执行）⇒ **须 reviewer 独立验收**；本小节**只追加**，**不改写**既有完成区 / 审阅记录结论。

### P3 最小构建（实测，`setsid nohup` + `*_EXIT`）
- **env**：`conda-lock install`（lean lockfile）⇒ **`ENV_EXIT=0`**。
- **CIRCT**：`firtool-1.75.0`（`circt-full-static-linux-x64.tar.gz`，sha256 逐位一致）⇒ **`CIRCT_EXIT=0`**（首次因 `.sha256` 文件行格式判 `rc=1`，**按需重试 1 次**；日志 `<CIRCT 日志 1/2>`）。
- **toolchain-extra**：riscv-isa-sim（`spike`/`spike-dasm`/`libriscv.so`/`libfesvr.a`）+ riscv-pk + riscv-tests + libgloss + DRAMSim2 + uart_tsi ⇒ **`EXTRA_EXIT=0`**（日志 `<EXTRA 日志>`）。
- **Verilator sim**：首次 **`SIM_BUILD_EXIT=2`**（sbt assembly，Scala 100 errors）⇒ **重试 `SIM_BUILD_EXIT=0`**；simulator ≈ 11.2 MB（`<P3 sim 日志>`）。

### P4 参考平台冒烟（实测）
- **必达（裸机 hello）**：`run-binary BINARY=tests/build/hello.riscv` ⇒ **`P4_HELLO_EXIT=0`**（P3 期初跑，日志 `<P4 hello 日志>`）；真实输出含 **`Hello world from core 0, a rocket`**（另有 `[UART] UART0 is here (stdin/stdout).`、`Verilog $finish`）⇒ 证据 `<P4 STDOUT 证据>`。
- **`pk`（本任务验收标准 ④ 之「必达」）**：**未跑通** ⇒ **`PK_EXIT=2`**（`TestDriver.v:147` 断言 `%Fatal`，`max-cycles` 内未完成；`<pk 日志>`）⇒ **如实登记为未达成**；**pk↔QEMU 对照亦未做**。
- **Linux（可选）**：未做（依赖 FireMarshal）。

### 落点修正（用户 2026-10-13 约定原话为据）
> 用户原话：「**`.cache` 下面应该是裸仓库，然后在 `.work` 下面有 `source` 和 `build`**」

- **搬树**：`.cache/chipyard`（8.9 GB，含 `.conda-env` + 构建产物）→ **`.work/source/chipyard`**（同 fs `mv`，**<1 s**，**`MOVE_EXIT=0`**）；**`.cache/chipyard` 已不存在**；`.cache/` 其余（`refs`/`embench-iot`/`qemu.git`/`llvm-project.git`/`picolibc.git`）**未动**（日志 `<move 日志>`）。
- **重建（env 内含绝对路径前缀 ⇒ 必须重建；源码/锁文件在树内，**无下载**）**：
  - **conda env**：`conda-lock install -p <新落点>/.conda-env <lean lockfile>`（**211 包全命中本地缓存**）⇒ **`ENV_REBUILD_EXIT=0`**、**≈1 min**、新 env 内 **0 处**残留旧前缀（日志 `<env 重建日志>`）。
  - **riscv-isa-sim 补建**（P3 `EXTRA` 曾装入 env，重建 env 时被清除）：全量 `configure`+`make -j8`+`install` ⇒ **各步 rc=0**、**≈2 min 50 s**；产出 `libriscv.so`/`libfesvr.a`/`spike`/`spike-dasm`（另 `cp libdramsim.so` 入 env `lib/`）。末位 `*_EXIT` 标记因进程回收未落盘，**事后按日志各步 rc=0 与产物在位补记 `ISA_SIM_EXIT=0`**（日志 `<isa-sim 日志>`）。
  - **CIRCT `firtool`**：P3 曾手动解入 env，重建 env 后**缺失**；本次**未重新下载**（遵硬约束 3）⇒ 走「**复用既有 RTL**」路线：改写 sim 生成 `.f` 列表的绝对前缀（`.cache/chipyard`→`.work/source/chipyard`），**不触发** Chisel/firtool（verilator 直接消费既有 `gen-collateral` RTL）。
  - **Verilator sim 重编**：`make -C <新落点>/sims/verilator`（`-j8`；verilator 重跑 + C++ 重编 + 重链）⇒ **`SIM_BUILD2_EXIT=0`**、**≈1.5 min**；新二进制 rpath 指向**新 env**、`ldd` 解析 `libriscv.so`/`libdramsim.so` 均出自新 env（日志 `<sim 重建日志>`）。
    - **中途失败现场（有据，非掩盖根因）**：首次于 23:10 因改写 `.anno.json`（firtool 入参）mtime 变新触发 Chisel `Generator` 重生成 `.fir` ⇒ 连带触发 `firtool` ⇒ `make rc=2`（`firtool not found`）；**处置**＝将相关生成物 mtime 归位到「jar 之后、`gen-collateral` 之前」后重跑成功。
- **P4 复跑**（新落点）：**`P4_HELLO_EXIT=0`**，真实输出含 **`Hello world from core 0, a rocket`** ⇒ 证据 `<P4 复跑 STDOUT 证据>`、`<P4 复跑日志>`。

### 落点约定固化（治根）
- 仓库根 `AGENTS.md`「目录结构」**+1 行**；`.tao/knowledge/lessons.md` **追加 §3.19**（判据层，≤2 行）。
- `manifests/chipyard-submodules.lock.toml` 头注生成路径改指 `.work/source/chipyard`（**仅注释文字**，锁数据未动）。

### 遗留（**追加**，不改写④⑤）
- **⑥** P3/P4 **由主会话代行 ⇒ 待 reviewer 独立验收**；**`pk` 未跑通**（`PK_EXIT=2`）、pk↔QEMU 对照未做、Linux 未做。
- **⑦** 落点修正路线：因「不得重新下载」+ `firtool` 已随重建 env 清除，sim 重编走「复用既有 RTL + 改写 `.f` 路径前缀」而非全链 firtool 重生成；**如需完整链重建，须先恢复 `firtool`**（重下载或另立任务）。
- **⑧**（**architect 追加，2026-10-14；源 = 第 2 轮 reviewer 非阻断建议①**）**P1/P2 历史证据脚本 `.work/evidence/<任务ID>/run.sh` 内 `CK=".cache/chipyard"` 路径已随落点修正失效**（该脚本为历史版本，**保留不改写**，此处**仅注明**；P3/P4 落点修正后的当前证据脚本另在 `.work/evidence/<任务ID>-fix2/`）。
- **⑨**（**architect 追加，2026-10-14；承 ⑦**）**CIRCT `firtool` 未在重建 env 中恢复**（`firtool` 不在重建 env、不在默认 `PATH`）⇒ **建议**：仅在需要「**重新生成 RTL**」（触发 Chisel `Generator`/`firtool`）时**单立任务**恢复（重下载或按锁装入）；**无需时维持现状**（复用既有 RTL 路线仍可跑通 P4）。
- **⑩**（**architect 追加，2026-10-14；源 = 第 2 轮 reviewer 非阻断建议②**）`.cache/embench-iot` 为 **checkout（非裸仓库）**，与「`.cache/` 只放裸仓库」约定不符 ⇒ 已登记新 issue **`ISS-204`（open）**（本任务**未动**该目录）。

## 完成区（落点修正，**追加**；不改写上文完成区）

**测试结果**：一键证据脚本 `.work/evidence/<任务ID>/run.sh` 绿色 **22/22 PASS（rc=0）**；`--inject`（伪造 `.cache/chipyard`）⇒ `cache_chipyard_absent` **FAIL（rc=1）** ⇒ 还原 ⇒ **回绿 22/22（rc=0）**。门控：`make check`(L1) **rc=0**、`make check-modules`(L2) **rc=0**、`check-no-residue` **rc=0**、`check-knowledge-refs` **rc=0**（0 悬空）、`check_issues.py` **rc=0**（24 open/2 closed）、`check-patch-tree` **rc=0**、`check-index-blobs` **rc=0**。
**修改文件**：`.work/source/chipyard/**`（搬树 + env/仿真器重建，未入 git）；`manifests/chipyard-submodules.lock.toml`（头注生成路径，**仅注释**）；`AGENTS.md`（+1 行落点约定）；`.tao/knowledge/lessons.md`（+§3.19）；本任务书（**仅追加**）；`.work/log/<模块>/*`、`.work/evidence/<任务ID>/run.sh`（新）。**未提交 git**。
**验收结果**：见「P3/P4 执行记录 + 落点修正」小节；关键现场值：`MOVE_EXIT=0`、`ENV_REBUILD_EXIT=0`（≈1 min）、`ISA_SIM_EXIT=0`（≈2 min 50 s，事后按各步 rc=0 与产物补记）、`SIM_BUILD2_EXIT=0`（≈1.5 min）、`P4_HELLO_EXIT=0`（含 `Hello world from core 0, a rocket`）。
**新发现/坑**：① **chipyard `make` 在缺 `firtool` 时无法重建**——改写 `.anno.json`（firtool 入参）mtime 会触发 Chisel `Generator` 重生成 `.fir` ⇒ 连带触发 `firtool`；`make -n` 因**不执行** Generator 而**漏报**该依赖（**dry-run 绿 ≠ 真跑绿**）。② **重建 conda env 会清除 P3 手动装入 env 的 `firtool`/`spike-dasm`/`libriscv.so` 等**（非 lockfile 内容）⇒ 须分别补建（riscv-isa-sim 可由树内源码**无下载**重建；`firtool` 需下载或另立任务）。③ 长脚本 `{ ... } > log` 块后的 `rc=$?` 取的是**块退出码（恒 0）** ⇒ 会覆盖被检命令 rc（本轮已修）；`setsid nohup` 脚本末位标记偶有被回收未落盘 ⇒ 以日志逐步 rc + 产物为据。
**遗留问题**：**⑥ P3/P4 由主会话代行 ⇒ 待 reviewer 独立验收**；`pk` 未跑通（`PK_EXIT=2`）、pk↔QEMU 对照未做、Linux 未做；⑦ 完整链重建须先恢复 `firtool`。**未 push**（提交权归 architect）。

#### 第 3 轮 engineer 自审（落点修正，2026-10-13；**主会话代行**）

- **范围**：逐行审 ① 搬树/重建驱动脚本（`/tmp/opencode/<任务ID>/*.sh`，一次性）、② `.work/evidence/<任务ID>/run.sh`、③ `AGENTS.md`/`lessons.md`/锁册头注、④ 任务书追加小节。
- **逻辑正确性**：搬家用 `mv`（同 fs）保留 inode/mtime；重建只从**树内 lockfile + 本地包缓存**（211 包 0 miss）与树内源码，**无下载**；新 env `bin/` 旧前缀 **0 处**、新前缀 208 文件；sim `.f`/`VTestDriver.mk` 旧前缀 **0 处**、新前缀在位；`ldd` 解析 `libriscv.so`/`libdramsim.so` 出自新 env。**边界**：`make -n` 干跑**不执行** Chisel `Generator`，故其"无 firtool"绿灯**不构成**真跑保证（见 finding F2）。
- **防造假**：`run.sh` green **22/22 rc=0**、`--inject`（伪造 `.cache/chipyard`）**可达 FAIL（rc=1）**→ 还原 → 回绿（rc=0）；计数**现场统计**（`PASS/FAIL`、`grep -c` 实时）；`P4` 断言为**行为级**（真跑 `hello.riscv` 捕获输出含 `Hello world from core 0, a rocket`）；脚本结尾**不用 tee 吞码**。
- **finding 处置**：

  | finding | 处置 | 改了什么 | 复验证据 |
  |---|---|---|---|
  | F1 重建 env 连带清除 P3 手动装入 env 的 `firtool`/`spike-dasm`/`libriscv.so` 等 | ✅已修/⏸延后 | riscv-isa-sim **由树内源码无下载补建**；`firtool` **未重下载**（登记遗留⑦） | env 内 `libriscv.so`/`libfesvr.a`/`spike-dasm`/`libdramsim.so` 在位 |
  | F2 `make -n` 漏报 Chisel→firtool 依赖（dry-run 绿≠真跑绿） | ✅已修 | 归位生成物 mtime（jar 之后 / `gen-collateral` 之前）避免触发 Generator | 真跑 `Generator=0`、`firtool=0`，`SIM_BUILD2_EXIT=0` |
  | F3 驱动脚本 `{…} > log` 后 `rc=$?` 取块退出码（恒 0），掩盖 `make rc=2` | ✅已修 | 改用块内 `rc=$?`（块非子 shell） | 修后 `SIM_BUILD2_EXIT` 与 `make rc` 一致 |
  | F4 证据脚本用**相对** `PATH`/`RISCV`，`make -C` 换目录后 `spike-dasm` 丢失致 check9 假 FAIL | ✅已修 | 改**绝对**路径 | green 由 20/22 → **22/22** |
  | F5 `setsid nohup` 脚本末位 `*_EXIT` 偶未落盘（进程被回收） | ✅已修 | 以日志**逐步 rc + 产物**为据补记，并如实披露 | `ISA_SIM_EXIT=0`（configure/make/install rc=0 + 产物在位） |

- **判决**：5 条 finding 全部处置（F1 之 `firtool` 部分按约束**不重下载**、登记遗留⑦）；安全面（搬家保留成果、无越界、无下载、无 `git checkout` 还原、临时物在 `/tmp/opencode/<任务ID>/`）齐备；门控全绿。**待 reviewer 独立验收**（P3/P4 系主会话代行）。状态保持 `待验收`。

#### 第 2 轮 reviewer 验收（2026-10-13，独立重跑；落点修正 + P3/P4 实测）

- **P4 独立重跑**：`make -C sims/verilator run-binary BINARY=../../tests/build/hello.riscv`（PATH 含 `riscv-tools/bin`）⇒ 真实输出含 `Hello world from core 0, a rocket`、`[UART] UART0 is here`、`Verilog $finish`；rc=0 ⇒ **P4 可复现 ✓**。
- **门控（真实 rc，无 `| tee` 吞码）**：`make check`=**0**、`check-modules`(L2)=**0**、`check-no-residue`/`check-knowledge-refs`/`check_issues.py`(24 open/2 closed)/`check-patch-tree`(4 component(s), 127 patches OK)/`check-index-blobs` 各=**0**。
- **落点约定核**：`.cache/chipyard` 不存在 ✓；`.work/source/chipyard` 完整（simulator/conda-env/hello.riscv 在位）✓；`AGENTS.md`+1行/`lessons.md`+§3.19 与用户原话「`.cache/` 下面应该是裸仓库，`.work` 下面有 `source` 和 `build`」语义一致 ✓；跟踪区无大构建树（`git status` 仅 4 文件）✓。
- **锁册核**：`chipyard-submodules.lock.toml` vs `72d40b6` 仅头注 1 行（旧前缀→新前缀），锁数据 md5 逐位一致、79 条 ✓；`git grep 'cache/chipyard'` 命中仅任务文件（历史记录）✓。
- **记录诚实性核**：P3/P4 显式标注「主会话代行」✓；不伪称 reviewer 已验收（「待 reviewer 独立验收」）✓；`ISA_SIM` 末位标记缺失如实登记（`_EXIT` 文件含 post-hoc 说明）✓；落点修正含用户原话+实测耗时/退出码 ✓；遗留⑦（firtool 未恢复）在 ✓。
- **证据脚本审核**：`INFRA-074t-fix2/run.sh` 22 项、计数现场统计、不吞码；P4 为行为级（真跑 sim 捕获 banner）✓；重跑 **22/22 rc=0** ✓；`--inject`（`cache_chipyard_absent`）可达 FAIL (rc=1) ⇒ 还原 ⇒ 回绿 ✓。
- **独立反例**：手动 `mkdir .cache/chipyard` + marker ⇒ `cache_chipyard_absent` **FAIL** (rc=1) ⇒ `rm -rf` 还原 ⇒ **22/22 rc=0** ✓（注入物彻底清除、无残留）。
- **非阻断建议**：① `.work/evidence/INFRA-074t/run.sh`（P1/P2 历史）`CK=".cache/chipyard"` 路径已失效（reloc 后 red），建议注明历史版本或更新；② `.cache/embench-iot` 为 checkout（非裸仓库），属历史遗留，建议后续统一至 `.work/source`。
- **判决**：**Accepted**——P4 独立复现、门控全绿、锁册数据未变、记录诚实性通过、证据脚本可达 FAIL+还原回绿；无阻断项。

#### architect 交叉复核 + 非阻断登记 + 提交留痕（2026-10-14，分支 `INFRA-074t-land2`）

- **依据**：reviewer 第 2 轮判 **`Accepted`**（0 阻断）⇒ 档位 = **正常提交**（**无** `WIP:` 前缀）。
- **交叉复核（architect 自跑，均现场 rc）**：`make check`(L1) **rc=0**；`make check-modules`(L2) **rc=0**；`check-no-residue` **rc=0**；`check-knowledge-refs` **rc=0**；`check-patch-tree` **rc=0**；`check-index-blobs` **rc=0**；`check_issues.py` **rc=0**（**25 open / 2 closed**，含本次新增 `ISS-204`）。日志 `/tmp/opencode/arch-INFRA-074t-land2/*.log`（临时）。**改动前后各跑一轮，均 rc=0。**
- **3 条非阻断登记（如实、不掩盖）**：
  - ① **P1/P2 历史证据脚本 `run.sh` 内 `.cache/chipyard` 路径已随落点修正失效** ⇒ 本任务书「遗留」**⑧**（**仅注明**；历史版本**保留、未改写**）。
  - ② **`.cache/embench-iot` 为 checkout（非裸仓库）** ✗ 违反「`.cache/` 只放裸仓库」约定 ⇒ 新增 **`ISS-204`（open）**（编号取现场下一空位；`check_issues.py` rc=0）+ 本任务书「遗留」**⑩**（指针）；**未动**该目录本身 ✗。
  - ③ **CIRCT `firtool` 未在重建 env 中恢复**（= 遗留⑦）⇒ 本任务书「遗留」**⑨**：**建议**需「重新生成 RTL」时**单立任务**恢复（**无需时维持现状**）。
- **记录订正（同轮，**只追加/只改指定行**）**：`milestones.md` 的 `INFRA-074t` 行 **进度注明** → 「P1/P2 + P3/P4（参考平台跑通）+ 落点修正 已完成；待收尾」+ 状态列 `待开始`→`待验收`（reviewer 第 1 轮非阻断③）；M8 规划区**追加 1 行**「进度·续」⇒ **未改写既有行**。
- **文件集对账**：`git diff --cached --name-status` = **`M`×6**——`AGENTS.md`、`.tao/knowledge/lessons.md`、`.tao/tasks/infra/INFRA-074t-*.md`、`manifests/chipyard-submodules.lock.toml`、`.tao/knowledge/issues.yaml`、`.tao/knowledge/milestones.md`（**显式 staging 逐个路径**，**未**用 `git add -A`/`.`）；与完成区「修改文件」+ 本任务范围**逐条对齐**（**无漏提 / 多提 / 越界**）。
- **提交**：`INFRA-074t(落点修正): .cache/chipyard → .work/source/chipyard + 约定入 AGENTS/lessons + P3/P4 记录（已验证）`（本分支 1 条，squash 落地 `master`；**提交号/时间**由主会话 `/complete` 回填 `milestones.md` 本行「完成时间」）。
- **未 `push`**（`push` 只由主会话在 `/complete` 后执行）。
