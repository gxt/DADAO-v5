# TESTCASES-033t: SEE/HEE + semihosting 向量（L1 MC + L3 执行；独立 oracle）

**模块**：testcases
**项目里程碑**：M5
**依赖**：`SPEC-114t`、`SPEC-115t`、`LLVM-060t`、`INFRA-048t`、`QEMU-047t`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `SPEC-114t`（SEE/semihosting 正文）+ `SPEC-115t`（`trap`/`escape`/`cfx2rc`/`cfx2rd` re-scope + `contracts/opcodes.yaml`）+ `.tao/adr/adr-0020-see-semihosting.md`（`Accepted`）。
  - `LLVM-060t`（MC 编码支持；**L1 MC 向量依赖它**）+ `INFRA-048t`（落点 `.dadao/tests/`）+ `QEMU-047t`（**新 bootrom**：生成物 `.dadao/tests/bootrom/bootrom.bin` + `-bios` 加载路径；**L3 执行向量的启动器/模式·向量配置来源**）。
  - `spec/Process-05-里程碑TDD规范.md`（§2 L1/L2/L3；§3「一能力一向量」；§4 期望值**独立派生**；§5 反例门控；§6 落点）；`contracts/opcodes.yaml`（L1 期望编码来源）。
  - `spec/SimRISC-11-其它.md`（4 条形式）、`spec/DADAO-12 §5`（异常进入/退出）、`spec/DADAO-22 §1/§3`（调用约定/初始化）、`.tao/knowledge/contract-abi.md §4.1/§4.4`（传参/返回）。
  - 既有 `tests/llvm/lit/MC/DADAO/`（`validate_mc_vectors.py` oracle）与 `tests/llvm/codegen/`（L3 驱动模式）；既有驱动 `tools/integ/run_codegen_e2e.py`/`run_elf_e2e.py`（**`run_m5_e2e.py` 复用其结构**：清单 → 自有工具链编 bin → `-bios`+`qemu` 跑 → 逐例比对 → `--inject` 反例自检）。
- **输出**：
  - **L1 MC 向量**：落 `tests/llvm/lit/MC/DADAO/`（如 `m5-trap-escape-cfx2.s`）——`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码与往返；**分阶段**：`LLVM-060t` 就绪前以 lit **`UNSUPPORTED:`** 标记暂缓（`Process-05`；`LLVM-060t` 完成后**去除**标记）。期望编码**独立派生自 `contracts/opcodes.yaml`**（**禁**从 `llvm-mc` 反推）。
  - **L3 执行向量**：落 `tests/llvm/codegen/m5/`（独立 m5 清单 + `expected.yaml`）——**承载形态 = bin**（`llc`/`llvm-mc` → `objcopy -O binary` → `qemu`；**不经 `ld.lld` 多 TU ELF**——用户 2026-10-08 M5 范围简化裁定，见下「承载形态裁定」）跑通：① **semihosting 服务**（≥ console `WRITEC/WRITE0/WRITE` + `EXIT`/`EXIT_EXTENDED`；`READC` 可 host 输入桩）；② **权限反例**（未授权模式/未实现 cfx ⇒ `NUPERM/NJPERM/NSPERM/NHPERM` 或 `CFXREG`）；③ **一条一般 trap 进入向量 + escape 返回**。**期望值独立派生自 spec/契约**（**禁**从 QEMU 反填）。
  - **L3 运行方式（与 M5 门槛口径一致；用户 2026-10-08 裁定）**：`qemu-system-dadao -M dadao-m1 -bios <bootrom.bin> -kernel <vec.bin> -semihosting-config enable=on,target=<native|gdb>`；`<bootrom.bin>` = `QEMU-047t` 产物 `.dadao/tests/bootrom/bootrom.bin`（**经 `tools/infra/paths.py::test_artifacts_dir()`/`BOOTROM_DIR` 解析，禁硬编码**），`<vec.bin>` 由**自有工具链**（`llvm-mc`/`llc` → `llvm-objcopy -O binary`）产生。**L3 全部用例均经 `-bios` bootrom**（bootrom = 唯一应用入口/启动器：复位 PC=`0xffff_ffff_0000`，须由 bootrom 完成模式/向量/栈初始化后 hypv→user 跳应用——**无 `-bios` 则应用无入口、不执行**）；若认为某例无需 bootrom，**须写出依据**（该例如何获得入口/模式配置）**供裁定，不得静默采用**（依据见「审阅记录 · 下发前预检修订」）。
  - **m5 L3 驱动**：**新建 `tools/integ/run_m5_e2e.py`**（复用既有 runner 结构：读 m5 清单 → 自有工具链编 bin → `qemu -bios <bootrom> -kernel <bin> -semihosting-config …` → 逐例比对期望退出码/故障码 → `--inject` 反例自检；对 `run_codegen_e2e.py`/`run_elf_e2e.py` **只复用结构、不改其 M3/M4 门控**）；本任务内**直接 `python3` 调用**（`Makefile`/`make test-semihost` 接线归 `INTEG-020t`，本任务**不改 `Makefile`**）。
  - **独立 oracle**：扩展 `tools/testcases/validate_mc_vectors.py` / 新增 `validate_elf_vectors.py` 派生（复用 `029t`/`030t` 共享 validator，`Process-05 §6`）；**不调用** `llvm-mc`/`llc`/QEMU 作为期望来源。
  - `tests/llvm/lit/MC/DADAO/README-m5.md`（向量 ↔ 能力 ↔ 期望值来源对照）。
- **门控时序（`Process-05` TDD）**：向量**先立**；L1 暂缓用 `UNSUPPORTED:`（**不接门控**），由 `LLVM-060t` 完成后（或 `INTEG-020t` 收口时）去除标记接入 `check-lit`；L3 落 m5 独立清单（`make test-codegen`/`test-elf` 的 M3/M4 驱动**不读**，避免误接）。
- **约束（硬）**：
  - **期望值独立派生**（`AGENTS.md`「Independent oracle」；`Process-05 §4`）；**不得**从 LLVM/QEMU 反填。
  - **规模 ∝ 能力**（「一能力一向量」），手写少量、可审计；**禁**批量迁移。
  - **向量须能对反例失败**（`Process-05 §5`）：每条向量有可达 FAIL 路径（**逐条**核对，避免恒真/两支同值）。
  - **允许改动文件集（越界须披露）**：`tests/llvm/lit/MC/DADAO/**`、`tests/llvm/codegen/m5/**`、`tools/testcases/validate_*.py`、`tools/integ/run_m5_e2e.py`、**本任务书**；`.work/evidence/TESTCASES-033t/**`（gitignored、非入库）。
  - 不改 `contracts/**`/`components/**`/`Makefile`/`spec/**`；临时目录 `/tmp/opencode/TESTCASES-033t/`；**不提交 git**；复杂命令输出留存 `.work/log/testcases/`（**禁 `tee`**）。
  - **重建成本申报**：L3 需 `build-mc`/`build-lld`/`build-qemu`（增量，`build-qemu` 5–20 分钟）；开工前说明。

## 验收标准

1. **L1 向量**：`tests/llvm/lit/MC/DADAO/` 含 4 条指令编码/往返向量（`LLVM-060t` 就绪前带 `UNSUPPORTED:`）；`make check-lit` EXIT=0 且新向量被正确处理（unsupported 或 PASS）。
2. **L3 向量**：`tests/llvm/codegen/m5/` 含 semihosting 服务（≥3 类）/权限反例（≥3 类）/一般 trap+escape 各 ≥1；给出「向量 ↔ 能力 ↔ 期望值来源」表。
3. **独立 oracle**：`python3 tools/testcases/validate_*.py` EXIT=0；oracle **无** `subprocess`/`os.system`/`Popen`（`grep` 核实）；期望值可独立重算。
4. **L3 执行**：经 m5 驱动（`python3 tools/integ/run_m5_e2e.py …`）跑通，逐例「名字/期望/实际/退出码」；**逐例给出实际 qemu 命令行（含 `-bios`）**，并核**复位 PC/bootrom 生效**（`-d cpu` 首块 `PC=0xffff_ffff_0000` 或等价，含「模式/向量配置生效」观测）；给真实输出（`.work/log/testcases/`）。
5. **反例门控**：对注入反例（改一条期望字节 / 改一条服务号 / 改一条权限期望）⇒ oracle/驱动器**非零退出**；还原后回绿（真实输出）。
6. **门控**：`make check`/`make check-lit` EXIT=0；`make check-no-residue` EXIT=0。
7. **一键证据脚本**：`.work/evidence/TESTCASES-033t/run.sh`——非交互、失败非零、逐项打印、≥2 类注入自检、结尾**禁 `tee`**。
8. **无残留**：`git status --untracked-files=all` 仅新增向量 + oracle + `tools/integ/run_m5_e2e.py` + README + 本任务书。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 独立全量重算（逐条） + 门控 + 判决）

#### architect 重排落纸（2026-10-07，用户裁定 1）
**用户原话**：「**A 重排：先 LLVM-060t 再 SPEC-115t（推荐）**」（经主会话转达；见 `lessons §7.3`）。

**对本任务的影响（lit 归属裁定）**：本任务的 L1 MC 向量落点 `tests/llvm/lit/MC/DADAO/` 现由**前置的 `LLVM-060t` 先行自带**（含 `crrr`/`ciii` 的 `; OBJ:`），本任务**复用/扩展**（不再需要「`LLVM-060t` 就绪前以 `UNSUPPORTED:` 暂缓」，因其已就绪）。`tests/vectors/inventory.md` 的 4 行由 `SPEC-115t` 承接（`validate_vectors` 要求行集 == `scope==m1` 集，原子强制）。完整归属理由见 `SPEC-115t` 审阅记录「第 2 轮 architect 重排落纸」。

#### architect 承载形态裁定（2026-10-08，用户裁定）

**用户原话（逐字落盘；完整原话见 `INTEG-019k` §第 8 轮）**：

> 「……用bios的时候，直接接bin，也就是objdump后的测试程序；而用elf的时候，则不需要bootrom，只需要semihosting即可……只做bootrom+bin的情况；elf加载放在M6……」

**对本任务的影响**：

1. **L3 执行向量承载形态改 = bin**（`llc`/`llvm-mc` → `objcopy -O binary` → `qemu`）；**不经 `ld.lld` 多 TU ELF**（已同步接口规范「L3 执行向量」条）。
2. **原「单/多 TU ELF」正向用例移 M6**（ELF 加载/链接态随 M6，与「`-bios`+ELF 组合语义」一并；登记 `ISS-168`）。本任务保留的 L3 用例 = semihosting 服务 / 权限反例 / 一般 trap+escape（**bin 形态即可承载**，不依赖多 TU ELF）。
3. **L1 MC 向量不变**（`trap`/`escape`/`cfx2rd`/`cfx2rc` 编码/往返；`LLVM-060t` 已自带，本任务复用/扩展）。

**未改范围**：本轮**未动 `spec/`**。

#### 下发前预检修订（architect，2026-10-08，只追加）

**背景**：主会话对本任务书作「**下发前预检**」，发现 2 处缺口（F1 运行方式未写明致前置缺口；F2「m5 驱动」无落点）。本轮据**用户裁定口径**（M5 门槛正向 = **bootrom（`-bios`）+ bin 应用**经 `-semihosting`；`INTEG-019k` §第 8 轮）修订本任务书；**未触 `spec/`**、**未改任务范围**（L1/L3 与交付物不变）。

**F1（L3 运行方式未写明 ⇒ 前置缺口）**

- **事实**：门槛口径含 **bootrom（`-bios`）**，但原任务书未提 `bootrom`/`-bios`/`QEMU-047t`，依赖段亦无 `QEMU-047t`。而 L3 的权限反例（reserved cfxha / 未实现 cfx / scratch rc≥N / RO 写）与「一般 `trap` 进向量 + `escape`」需**模式/掩码/向量配置**，且 bin 应用**无独立入口** ⇒ 需 bootrom。
- **改法**：① **依赖段 += `QEMU-047t`**（**已验证**；bootrom 产物 `.dadao/tests/bootrom/bootrom.bin` + `-bios` 路径）；② 「输入」补 `QEMU-047t` 说明；③ 「输出」L3 新增**运行方式**条（`qemu-system-dadao -M dadao-m1 -bios <bootrom> -kernel <bin> -semihosting-config …`；bin 由**自有工具链** `llvm-mc`/`llc` → `llvm-objcopy -O binary` 产生；bootrom 路径经 `tools/infra/paths.py` 解析、禁硬编码）；④ **验收 4** 补「逐例给出**实际 qemu 命令行（含 `-bios`）** + 核**复位 PC/bootrom 生效**」。
- **「L3 是否某些用例无需 bootrom」——architect 依据（**供裁定**；本轮按「**全部经 bootrom**」写）**：
  1. **门槛口径**（用户 2026-10-08 裁定）明示 L3 载体 = bootrom（`-bios`）+ bin ⇒ 一律经 bootrom；
  2. **bootrom 是唯一应用入口/启动器**：`-kernel <bin>` 的 flat bin 落**旧 RAM 基址**，**复位 PC = ROM 基址 `0xffff_ffff_0000`**，须由 bootrom 完成模式/向量/栈初始化后 **hypv→user 跳应用**（`QEMU-047t`：栈置 RAM@0）——**无 `-bios` 则应用无入口、不执行**；
  3. semihosting 服务例虽在**译码层短路**（`QEMU-046t`，不进入向量），**仍需 bootrom 把应用启动/进入 user**；
  4. ⇒ **结论：L3 全部用例均经 bootrom，无例外**。若 engineer 认为某例可省，**须给依据供裁定**（该例如何获得入口/模式配置），**不得静默采用**。

**F2（「m5 驱动」无落点）**

- **事实**：`tests/llvm/codegen/m5/` 不存在；`tools/integ/` 仅 `run_codegen_e2e.py`/`run_elf_e2e.py` ⇒ 验收 4「经 m5 驱动跑通」**无实现落点**，且「新建驱动」未入输出/允许文件集。
- **改法（择 ①，理由见下）**：**新建 `tools/integ/run_m5_e2e.py`**，已写入「输出」并加入**允许改动文件集**（含验收 8「无残留」清单）。本任务内**直接 `python3` 调用**；`Makefile`/`make test-semihost` 接线归 `INTEG-020t`（本任务**不改 `Makefile`**）。
- **择 ①（新建）而非 ②（扩 `run_codegen_e2e.py` 加 `--list m5`）的理由**：① M5 管线与 M3 门控**实质不同**（`-bios` bootrom vs `trampoline.bin`、`-semihosting-config`、期望含**故障码**），且 m5 源码形态偏 `.s`（`trap`/`escape`/`cfx2*`/semihosting）；② 沿用本项目**每里程碑一个 runner** 的既有范式（M3 `run_codegen_e2e.py`、M4 `run_elf_e2e.py` ⇒ M5 `run_m5_e2e.py`）；③ **不触碰** M3 门控脚本，零回归风险。DRY 通过**复用 runner 结构**（清单加载 / 构建管线 / qemu 调用 / `--inject` 自检）达成。

**供裁定（本轮未改主文，仅登记）**

1. **L3 执行还直接依赖 `QEMU-044t`/`045t`/`046t`（+ `QEMU-049t`）**：semihosting 例需 `QEMU-046t`、一般 `trap`/`escape` 例需 `QEMU-045t`、cfx/权限反例需 `QEMU-044t`、RAM@0 需 `QEMU-049t`。本轮按指令**只 += `QEMU-047t`**（其自身依赖 `QEMU-044t`/`QEMU-049t`）；**是否将 `QEMU-045t`/`046t` 等一并列入依赖段，供裁定**（均**已验证**）。
2. **「未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`」的 M5 可观测性**：`NUPERM` 等属 `DADAO-12 §2.2` **PTBR 权限层**，**不在 M5**（`ADR-0020 D9`；`QEMU-044t` 遗留明示）。M5 机器可观测的**权限反例 = cfx 级**（reserved cfxha ⇒ `ILLI`；未实现 cfx ⇒ `CFXREG`；scratch rc≥N ⇒ `CFXREG`；RO 写 ⇒ `CFXREG`，见 `QEMU-044t` 完成区）。**建议 L3 权限反例按 cfx 级（`ILLI`/`CFXREG`）表述**；本轮**未改主文**（「输出 ②」「验收 2」沿用原文），**供裁定**。
3. **`INTEG-020t` 的 `tools/integ/` 驱动复用**：`INTEG-020t` 输出 1 举 `run_semihost_e2e.py` 为例；为避免与 `run_m5_e2e.py` 重复，**建议 `INTEG-020t` 复用 `run_m5_e2e.py`**（其负责 `make test-semihost` 接线 + console stdio 捕获）。**供主会话协调**（本轮未改 `INTEG-020t`）。

**台账同步（最小）**：`INTEG-019k` §任务分解表 `TESTCASES-033t` 行依赖 += `QEMU-047t`；Wave 4 依赖链同步。`milestones.md` 未列本任务依赖 ⇒ **无需改**。

**边界**：本轮仅改**本任务书** + `INTEG-019k` 台账（1 行 + Wave 4）；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。
