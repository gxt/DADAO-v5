# m15-infra-001: 机型/执行环境/测试矩阵三契约迁移（消费点切换）

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-testcases-013`（ee-vast 资产集中；同改 tests 路径，须串行）
**可并行分片**：否（真源切换唯一）
**预估**：4–6 h
**档位**：大改（真源迁移 + 多驱动/门控）
**状态**：待开始

## 背景（用户 2026-11-18 定稿）

三份契约已落盘（`193d2232`）：
- `contracts/machine.yaml`：纯硬件几何 + capabilities + run_modes（无 entry/sp/exit/测试集/semihosting）
- `contracts/exec-envs.yaml`：`tiny` / `vast` / `user`，每个有 `machine`、engine 带 `(kaiwu-*)`、`load` 只有 `kind`
- `contracts/tests-matrix.yaml`：`tiny: [inst, tset/embench, unit/picolibc]`、`user: [tset/embench, tset/libc-test, tset/llvm-ts]`、`vast: [arch, tset/embench]`

当前代码仍读旧真源 `tests/shared/machine-profiles.yaml`（`tools/testcases/lib/machine_profile.py`），且旧文件混杂了测试集开关与 QEMU 回填值。本任务把消费点切到新契约，并删除旧文件。

## 目标

1. **`machine_profile.py` 改真源**：读 `contracts/machine.yaml`（几何/能力/run_modes）与 `contracts/exec-envs.yaml`（entry/sp/load/exit 的**去向**——见下）；`resolve()` 的 token 语义不变。
2. **拆分职责**：
   - 测试集开关（`arch`/`embench`/`picolibc`）从 profile 移到 `tests-matrix.yaml`；驱动按「当前 env + 套件」查矩阵。
   - QEMU 回填常量（`qemu_ram_*`/`qemu_bootrom_*`/`qemu_reset_pc`）移到 QEMU 侧（`components/qemu` 或生成物），不再由 profile 提供。
   - `entry`/`sp`/`image_window`/`kernel_base`/`kernel_reserved`/`host_loader`/`bootrom_load`/`exit_block`/`dump_base`/`fault_record`：按用户裁定**不进 machine.yaml**；消费者改为从**测试资产/驱动参数**取（tiny 的 entry 由 `tests/ee-tiny/kaiwu-tiny-app.lds` 提供；sp/window 等由驱动常量或新 `tests/ee-*/` 配置承载）。
3. **消费点更新**：`tools/testcases/arch/node_probe_prelude.py`（`PROFILE.get("ptw"/"hmon")`）、`picolibc_tests.py`（`prof.get("picolibc")`）、`run_asm_suite.py`/`run_suite.py`、`check_tests_index.py`、`tools/infra/build_*`、gem5 `configs/dadao/fs.py`/`se_timing.py`（profile 引用）、`run_embench_*`、`run_libc_test_*` 等。
4. **删除旧文件**：`tests/shared/machine-profiles.yaml`（迁移完成后删除，`git rm`）。
5. **门控**：`check-tests-index`/`check-dirs`/`check-knowledge-refs`/`check-interface` 等全绿；新增/更新必要的路径断言。
6. **兼容**：`--profile tiny|vast` 与 `DADAO_TEST_PROFILE` 的 CLI 语义保留（映射到新契约的 machine/env）。

## 验收（逐条贴真实 rc）

1. `machine_profile.load("tiny")`/`load("vast")` 从新契约返回几何/能力；`resolve("@RAM_BASE")` 等 token 与旧值逐项相等（对账表）。
2. 测试集矩阵：`tiny` 跑 inst/embench/picolibc、`user` 跑 embench/libc-test/llvm-ts、`vast` 跑 arch/embench——由 `tests-matrix.yaml` 驱动（至少 1 个驱动现场验证）。
3. QEMU 常量不再由 profile 提供（`grep` 证明 `qemu_*` 已移出）。
4. `tests/shared/machine-profiles.yaml` 已删除；全仓 grep 旧路径 0（归档/文档除外，逐条判断）。
5. 门控全绿：`check-tests-index`(472)、`check-dirs`、`check-no-residue`、`check-interface`、`check-knowledge-refs`；`build-bootrom`/`check-arch-smoke`/`check-inst-asm` 272/272。
6. ≥3 路注入（含 1 路任务书未列）：改 machine.yaml 的 RAM 尺寸 ⇒ 门控/驱动红；改 tests-matrix 开关 ⇒ 套件选择红；删一个 capability ⇒ arch 驱动拒绝；`cp`+md5 还原。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树。
2. 只动：`contracts/{machine,exec-envs,tests-matrix}.yaml`（如需微调）、`tools/`、`tests/`、`Makefile`、`docs/Process-09`、本任务书；**不动** `spec/`、`.tao/contracts/`、组件补丁语义。
3. **不改版本号**；不提交 git；`cp`+md5 还原。
4. 迁移用 `git mv`/`git rm`。

## 待裁定

（无）

## 审阅记录

（待填）
