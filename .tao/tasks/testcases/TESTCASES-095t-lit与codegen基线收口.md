# TESTCASES-095t: lit mcmodel 与 codegen 19 例基线收口

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-094t`（L3 基线已收口）、`LLVM-131t`（mcmodel 实现，已归档）、`INTEG-012t`（`test-codegen` 门控，已归档）、`QEMU-079t`/`QEMU-080t`（Machine-v5 Tiny/Node 系统机）
**状态**：待开始

## 执行环境
**执行环境**：本地（仓库根；`.dadao/cross-toolchain` 安装根已就绪；不重建 LLVM/QEMU；不 merge、不 push）

## 用户已定口径（2026-11-03，自包含）

- **范围**：只改 `tests/**`、`tools/testcases/**`、`Makefile`（按需）；**禁改** `components/**`（QEMU/gem5）、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`。
- **先判归属**：每个失败先定位到 **tests / 工具（runner·cfg·Makefile）/ QEMU** 三者之一，留依据（命令 + rc + 日志）再动手；QEMU 侧缺陷只登记现场与 spec 节号，**不在本册伪改**。
- **不改期望求绿**：期望值来自 `spec/` + `contracts/` 与既有独立导出（`tests/unit/llvm/codegen/expected.yaml`、lit `FileCheck` 断言），不得为绿灯放宽/删除断言。
- **不得以 BLOCKED 收尾**：本任务须给出全绿结论；若前置确实不可用，须当场在允许范围内修复或给出等价分步执行证据，**不得**以“环境不可用”作为收尾状态。
- **不重建组件**：QEMU/LLVM 二进制 md5 开工/收尾不变；`check-source-state` rc=0；不触发 `install-host` 的 LLVM 全量重建（若触发 ⇒ 用等价分步命令留证据，不硬跑）。

## 现状证据（2026-11-03 规划期真读/真跑）

### E1 lit 12 项环境透传（`DADAO-E2E::mcmodel.test`）

- `Makefile:1356-1358` 的 `check-lit` 直接调用 `$(LIT_BIN) tests/unit/llvm/lit/MC/DADAO tests/unit/llvm/lit/CodeGen/DADAO tests/unit/llvm/e2e/lit -v`，未显式导出工具根环境；`lit.cfg.py` 先取 `config.llvm_tools_dir`，再取 `LLVM_TOOLS_DIR`，最后回落 `paths.host_toolchain_bin()`。
- `tests/unit/llvm/e2e/lit/lit.cfg.py` 共定义 **12 个 `%` 替换**（`llvm_mc`/`llvm_objcopy`/`clang`/`FileCheck`/`not`/`llvm_objdump`/`qemu`/`ld`/`trampoline`/`crt0`/`linker_script`/`e2e_dir`）；这些即“12 项环境透传”的清单，`mcmodel.test` 用其中 10 项（`%clang %llvm_mc %ld %crt0 %linker_script %qemu %llvm_objdump %not %FileCheck %e2e_dir`）。
- `%qemu` 解析有两条候选路径（`tools_dir/qemu-system-dadao`，否则 `dirname(tools_dir)/qemu/qemu-system-dadao`）；`%ld` 追加 `-L tests/shared/linker`。二者在 `make check-lit`（GateLock、不同 cwd、环境变量未导出）下是否可解析，是本册第一条硬断言。
- 历史绿灯仅作线索、**不作验收证据**：`.work/log/check-lit.log:161` 有 `PASS: DADAO-E2E :: mcmodel.test (159 of 159)`（旧安装根/旧树）。

### E2 codegen 19 例 raw 通道与 RASOF

- `tests/unit/llvm/codegen/*.ll` 实数 **19** 例；`Makefile:1390-1408` 的 `test-codegen` 走 `tools/testcases/unit/run_codegen_e2e.py`：`llc → llvm-mc → llvm-objcopy -O binary --only-section=.text.start --only-section=.text` 得 **raw `.bin`**（预置 `profile.kernel_reserved` 零字节），再 `qemu -bios trampoline.bin -kernel <bin>`，**不装载 ELF**。
- 判据是 **guest 进程退出码** vs `expected.yaml`；`run_codegen_e2e.py:77-85` 把 `0x80|idx` 机器故障单列（`0x88 ILLI`/`0x89 UNDI`/`0x8A RASOF`/`0x8B RASUF`/`0x8C MALIGN`/`0x8D IALIGN`），且 `0x80..0xFF` 不得与正常期望码混同。
- 历史日志仅作线索：`.work/log/integ/test-codegen.log` 记 `19 programs ... 19/19 passed, 0 failed`（旧构建，需本册重跑）。

### E3 前置判据（先判 tests/工具/QEMU）

- 工具：`llc`、`llvm-mc`、`llvm-objcopy`、`ld.lld`、`clang`、`FileCheck`、`llvm-lit`、`qemu-system-dadao` 均由 `tools/infra/paths.py` 的 `host_toolchain_bin()` 定位；缺任一 ⇒ 先判“安装根/路径解析”问题（工具类），不得直接归因 QEMU。
- QEMU：`-M dadao-m1`、`-bios trampoline.bin`、`-semihosting-config enable=on,target=native`、`SYS_EXIT` 回传 `$?` 是 E2 判据成立的前提；`DADAO_TEST_PROFILE=tiny` 下 `kernel_reserved` 与 raw 入口偏移须一致。
- tests：lit 用例的 `FileCheck` 断言（LARGE/DEFAULT/PIC/REJECT-*/FAR-*/REL26）与 `expected.yaml` 期望值均为独立导出，**不得**用本机输出反推后回写。

## 目标

1. **lit 收口**：`make check-lit` rc=0，`DADAO-E2E::mcmodel.test` 绿灯；12 项 `%` 替换在门控环境下逐项可解析（含 `%qemu` 双候选与 `%ld -L`），不依赖调用者手工 `export`。
2. **codegen 收口**：`make test-codegen` rc=0 且日志 `19/19 passed, 0 failed`；raw（非 ELF）通道真实成立；`0x80|idx` 故障码（RASOF=0x8A）映射保持且可被反例证伪。
3. **unit 收口**：`make check-unit` 全绿（= `check-lit` + `test-codegen` + `test-elf` + `ir-lli` + `picolibc` fast）。
4. **归属可核**：逐项给出 tests / 工具 / QEMU 归类与依据；QEMU 侧只登记现场（含 spec/contract 节号），不改组件。
5. **门控与体例**：L1/L2 不退化；`check-tasks`/`check-milestones-fresh`/`check-no-residue` rc=0；证据脚本 + 反例注入；状态 `待验收`。

## 接口规范

- **输入**：`tests/unit/llvm/lit/**`（MC/CodeGen 快档）、`tests/unit/llvm/e2e/lit/**`（含 `lit.cfg.py` 与 `mcmodel.test`）、`tests/unit/llvm/codegen/**`（19 `.ll` + `expected.yaml`）、`tools/testcases/unit/run_codegen_e2e.py`、`Makefile` 的 `check-lit`/`test-codegen`/`check-unit` 目标、安装根工具与 `qemu-system-dadao`。
- **输出**：
  - 失败根因表 `case | 类别(tests/工具/QEMU) | 依据(命令+rc+日志) | 处置`（落本任务日志目录）；
  - 必要时对 tests/工具/Makefile 的最小改动（不得触碰期望值语义）；
  - 本任务证据目录下的 `run.sh`/`inject.sh` 与验收日志。
- **约束**：
  - 只改 `tests/**`、`tools/testcases/**`、`Makefile`；
  - **禁改** `components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`；
  - 单次跑 ≤5 min（超时即判 FAIL 并留现场），日志落本任务日志目录，不用 `tee` 吞退出码；
  - 证据必须来自本树真实运行，禁引用历史日志当验收。

## 实施顺序

- **P0 基线（判前置）**：记录 HEAD、QEMU/LLVM 安装根 md5、`check-source-state` rc；`llvm-lit -v tests/unit/llvm/e2e/lit/mcmodel.test` 与 `make test-codegen` 各跑一次留 rc；把每个失败归入 tests/工具/QEMU。
- **P1 lit 12 项透传**：在 `tests/unit/llvm/e2e/lit/lit.cfg.py` 内做路径解析加固（必要时 `Makefile` 的 `check-lit` 显式传 `LLVM_TOOLS_DIR`），逐个替换项打印/断言解析结果；再跑 `make check-lit` 全绿。
- **P2 codegen 19 raw/RASOF**：按 E2 复核 raw 通道（`.bin` 尺寸/入口偏移/`kernel_reserved`）；19 例逐例对账 `expected.yaml`；`0x8A` 等的映射与 FAIL 路径保留；`--inject` 自测跑通。
- **P3 汇总门控**：`make check-unit`；L1 `make -k check`（本册触及项）+ L2 `make check-modules`（若触发重建 ⇒ 等价分步命令 + 现场，不硬跑）。
- **P4 证据与收尾**：`run.sh` 一键重跑、`inject.sh` 反例；体例门控；完成区（≤30 行）与状态 `待验收`。

## 验收标准

1. **lit**：`make check-lit` rc=0；`llvm-lit -v tests/unit/llvm/e2e/lit/mcmodel.test` rc=0；12 项 `%` 替换逐项有解析证据（含 `%qemu` 命中哪条候选、`%ld` 的 `-L` 路径），且在未手工 `export` 的干净 shell 下成立。
2. **codegen**：`make test-codegen` rc=0，日志含 `19 programs`、`19/19 passed, 0 failed`；抽查证明走 raw（`objcopy --only-section` 产 `.bin`、`-kernel` 装 raw、无 ELF）；`run_codegen_e2e.py --inject` 自测 rc=0。
3. **RASOF/故障码**：`0x80|idx` 映射（含 `0x8A RASOF`）在交付物中仍可查，且一条“故障码当正常值”反例可 FAIL；不得把机器故障码当 PASS。
4. **check-unit**：`make check-unit` rc=0（其成员逐项 rc 留证）。
5. **L1/L2**：`make -k check` 本册触及项 PASS，其它既有红逐条声明“非本任务/主树同红”；`make check-modules` rc=0，若因构建产物缺失触发重建 ⇒ 给出等价分步执行证据 + 现场，且**不得**以 BLOCKED 收尾。
6. **证据/注入**：本任务证据目录的 `run.sh` 一条命令重跑全部断言（逐项取命令自身 rc）；`inject.sh` ≥2 类互异反例（如 lit 工具路径/替换项、codegen 期望值）注入 ⇒ FAIL，`cp`+`md5sum -c` 还原 ⇒ 回绿，禁 `git checkout/restore/stash/show`。
7. **范围**：`git status --porcelain -uall` 仅允许文件；`components/** spec/** contracts/** .tao/contracts/** .tao/adr/** manifests/**` 零 diff；QEMU 二进制 md5 开工=收尾；`check-source-state` rc=0。
8. **不可 BLOCKED**：任务不得以 BLOCKED 状态收尾；所有前置失败须在允许范围内修复，或给出可复核的等价执行证据并继续推进；越界根因（QEMU/gem5/spec/contracts）须上报用户裁定并保留现场，不得伪绿。
9. **体例**：`make check-tasks`、`make check-milestones-fresh`、`make check-no-residue` rc=0；完成区 ≤30 行、审阅记录每轮 ≤40 行；状态 `待验收`。

## 文件范围

- **允许**：
  - `tests/unit/llvm/e2e/lit/**`（`lit.cfg.py` 路径/替换加固；用例仅在证明确为笔误时最小修，逐条记依据）；
  - `tests/unit/llvm/codegen/**`（仅 `expected.yaml` 笔误且经独立 oracle 复核时；默认不改）；
  - `tools/testcases/unit/run_codegen_e2e.py`（raw/故障码/自测相关的最小修）；
  - `Makefile`（仅 `check-lit`/`test-codegen`/`check-unit` 的环境透传与传参）；
  - 本任务书、`.tao/knowledge/milestones.md`（流水行）、`.work/{evidence,log}/TESTCASES-095t/**`、`/tmp/opencode/TESTCASES-095t/**`。
- **禁止**：`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`.tao/adr/**`、`manifests/**`、`.tao/knowledge/discussing.md`、`.tao/archive/**`、`.work/source/**` 源码改写；**不提交 git**（提交权归 architect）。

## 风险

- **R1 工具链缺项**：`clang`/`ld.lld`/`llvm-objdump`/`llvm-lit` 任一缺失会让 lit 假失败；先判工具（E3），再判 QEMU。
- **R2 `install-host` 触发重建**：`check-unit`/`check-modules` 依赖安装根；若目标展开出 LLVM 全量重建，改等价分步执行并留 `.work/log`，不硬跑、也不以 BLOCKED 收尾。
- **R3 QEMU 行为漂移**：raw 入口偏移/`kernel_reserved`/`SYS_EXIT` 回传随 profile 变；以 `tests/shared/machine-profiles.yaml` 为准，不写死。
- **R4 `%qemu` 双候选**：`tools_dir/…` 与 `dirname(tools_dir)/qemu/…` 在不同安装形态下命中不同可执行文件；证据须写明实际命中路径与 md5。
- **R5 历史日志陷阱**：E1/E2 的历史绿灯是旧构建，不得作为验收证据；以本树重跑为准。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
