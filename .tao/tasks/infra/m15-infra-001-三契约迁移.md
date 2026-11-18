# m15-infra-001: 机型/执行环境/测试矩阵三契约迁移（消费点切换）

**模块**：infra
**项目里程碑**：M15
**依赖**：`m15-testcases-013`（ee-vast 资产集中；同改 tests 路径，须串行）
**可并行分片**：否（真源切换唯一）
**预估**：4–6 h
**档位**：大改（真源迁移 + 多驱动/门控）
**状态**：待验收

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

### 第 1 轮 engineer 自审

**范围**：`tools/testcases/lib/machine_profile.py`（真源重写）+ 7 个消费点 + 2 个新运行布局 YAML + 注释/文档同步 + 门控 `check_interface_alignment` 的几何期望源。

**逐项审查与处置**

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `dict(prof)` 走整数序列协议（`__getitem__` 无 `keys()`）⇒ `KeyError: 0` | ✅已修 | 新增 `Profile.to_dict()`；`tools/gem5/compare_chipyard.py` 改用 | `machine_profile('tiny')['sp']=0xffffff7eff00` |
| F2 `Profile.__init__` 误用契约级必填字段（`bootrom`/`ram`）校验扁平数据 | ✅已修 | 拆 `REQUIRED_CONTRACT_FIELDS`（构建期）与 `REQUIRED_PROFILE_FIELDS`（扁平） | `python3 tools/testcases/lib/machine_profile.py` rc=0 |
| F3 改 gem5 `fs.py.patch` 注释导致新增行数 +1，hunk 头与 `index` 行失效 | ✅已修 | 行数 298→299；`check_index_blobs --fix` 重写新 blob 哈希 | `git apply --check` OK；`check-index-blobs` 327 OK |
| F4 未用 API（`capability()`、`machine_key`） | ✅已修 | 删除 | 全仓 grep 0 引用 |
| F5 `_build_profile` 内 `load` 局部变量遮蔽模块 `load()` | ✅已修 | 改名 `load_block` | py_compile + 116 项证据全绿 |
| F6 自检 `--help` 触发 `generate_atomics_vectors.py` 重写已退役 YAML 载体（`tests/inst/atomics/*.yaml`）⇒ `check-tests-index` 红 | ✅已修 | 删除两个未跟踪残留；把该坑记入完成区 | `check-tests-index` 472 PASS |
| F7 注入 4 的注入对象是新文件，`git diff --name-only` 为空不构成"空注入"证据 | ✅已修 | `run.sh` 对未跟踪文件改用 md5 变化作证（tracked 仍要求 git diff 非空） | inj4：md5 `23b4077b→ac3d2300`，注入后 rc=1、还原后 rc=0 |
| F8 `check-knowledge-refs` 基线即 FAIL（2 条他任务书的证据脚本路径引用） | ⏸延后 | 不动他任务书（越界）；基线/本次同 2 条 | 基线日志与本次日志 `具体路径: 2` 逐条同名 |
| F9 `components/gem5/README.md`、`docs/TestReports/*`、`components/qemu/changelog.md` 仍提旧名 | ⏸延后 | 历史快照/组件变更记录，越出本任务文件清单 | `verify.py --only old-path` 列出 8 条并判为 allowed |

**判决**：F1–F7 已修并复验；F8/F9 延后（越界，需另立任务）。无未修 finding ⇒ 可标 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-18，大改档；判决 **Accepted**）

**自证/范围**：worktree `m14-infra-005/wt`（分支 `m15-infra-001`，HEAD `f7e68f5b`，基线 `661ae969`）；`git status -uall` 首尾均 0 行、六个目标文件 md5 首尾逐字节相同；`git diff 661ae969..HEAD` 72 文件（.tao 1 / components 1 / docs 1 / tests 17 / tools 52），`spec/`、`.tao/contracts/` **0 改动**，diff 内无版本号。

**重跑（rc 取被检命令自身，无 `| tee`；`timeout` 未触发 124）**：
- `./run.sh` rc=0（`checks=116 pass=116`）；`./run.sh --inject` rc=0（4 路各「注入 rc=1 → `cp`+md5 还原 → rc=0」，md5 回原值）
- `make check-tests-index` rc=0（`PASS（472 条）`，inst=272/arch=11/unit=186/tset=3 现场统计）；`make check-interface` rc=0（`总计: 89 项 | PASS: 89 | FAIL: 0`）
- `make check-dirs` / `make check-no-residue` rc=0（收尾复跑同）；`gen_machine_inc.py --check` rc=0；`make build-bootrom` rc=0（`self-test: PASS`）
- `make check-inst-asm` rc=0（`272/272 镜像通过（链例+故障链 633 例）`）；arch smoke 等价复跑（recipe 两条原样）`run_m5_e2e --profile vast` rc=0（`10/10`）、`min_rom_probe_046t.py` rc=0（`all 25 service ids exercised`）
- 附加：`make check-index-blobs` rc=0（327 OK）、`make check-patch-tree` rc=0（421 patches OK）

**对账（reviewer 独立算，不采信 verify.py）**：`git show 661ae969:tests/shared/machine-profiles.yaml` md5 `67ef6509…` == 证据基线副本；**36/36 字段逐项 EQ、mismatch=0**（bootrom/ram/ram_end/entry/sp/image_window/kernel_*/exit_block/dump_base/fault_record/ptw/hmon/smon/cfx）；套件开关 arch/embench/picolibc 六项一致；`suites` = tiny `[inst,tset/embench,unit/picolibc]` / user `[tset/embench,tset/libc-test,tset/llvm-ts]` / vast `[arch,tset/embench]`；`machine_name` = kaiwu-tiny/kaiwu-vast；`resolve("@RAM_BASE+0x20")=0xffffff000020`、`resolve("1:@SP")=0x100007fff0000`。

**驱动现场**：`run_m5_e2e --profile vast --build-only` rc=0（10/10）；`--profile tiny` rc=2 `does not run the arch suite (contracts/tests-matrix.yaml)`；`DADAO_TEST_PROFILE=vast`（省略 --profile）rc=0、`=tiny` rc=2；`picolibc_tests --profile vast` rc=2、`--profile bogus` rc=2、`--profile user` 被 argparse 拒（choices `tiny|vast`）；`machine_profile.py` 入口 rc=0。

**独立注入 5 路**（`cp` 备份 + md5 对账，**未用** checkout/restore/stash/show）：① machine.yaml tiny RAM `0x80_0000→0x100_0000` ⇒ `make check-tests-index` **rc=2**（`LDS … LENGTH 0x800000 != profile ram_size 0x1000000` + `ASM HEADER DRIFT`）→ 还原 rc=0、md5 `634a0f7b…`；② tests-matrix tiny 去 `tset/embench` ⇒ verify **rc=1**（`matrix[tiny]` 等 3 FAIL）→ rc=0；③ `tests/ee-vast/runtime.yaml` `sp` 越界（**任务书未列**）⇒ rc=1（`invariants raised`）→ rc=0；④ exec-envs tiny→`kaiwu-vast` ⇒ rc=1（`token-parity raised`）→ rc=0；⑤ machine.yaml vast `umon: true→1` ⇒ rc=1（`invariants raised`）→ rc=0。还原后 `md5sum` 六文件与注入前一致、`git status -uall` 0 行。

**外因判定（确为他任务/环境，非本改动）**：`check-knowledge-refs` **rc=2**，2 条 `.work/**` 分别在 `.tao/tasks/testcases/m15-testcases-013-…md:81`、`m15-testcases-015-…md:111`（本任务 `.tao/` 改动仅本任务书 ⇒ 基线同红；**派单称「已回绿」与实测不符**，按实测记）；`check-milestones-fresh` **rc=2** = `R1: m14-linux-030 有 worktree 但台账在「待开始」`（他任务台账）；`check-temp-dirs` **rc=2** = 5 个陈旧目录全属 `m14-testcases-006(-review)`/`m14-linux-009/005/015`（本任务目录是活动 worktree，已豁免）。

**约束核验**：独立 worktree、未提交 git ✓；`spec/`、`.tao/contracts/` 0 改动、版本号未动 ✓；`tests/shared/machine-profiles.yaml` 已 `git rm`，全仓旧路径残留仅 8 条历史文档（TestReports 4 / qemu changelog 2 / gem5 README 2）+ `.tao/` 归档台账，逐条判为文档级 ✓；`qemu_*` 全仓 grep 0 ✓；证据脚本无 `tee` 吞码 ✓；主工作树 `git status -uall` 0 行 ✓。
**越界 1 项（判可接受）**：`components/gem5/patches/configs/dadao/fs.py.patch` 不在硬约束 2 清单内——复核为**纯注释 + `index`/hunk 行数**同步（零语义），且目标 §3 明列 gem5 `fs.py` 为消费点、该文件只能经补丁触达，完成区 F3 已披露。
**文档级 finding（不阻断，交 architect 收尾改）**：`tools/testcases/parity/run_parity.py:1525` 报错文案仍写旧字段 `vast.picolibc=false`（行为已改读 `suite_enabled`）。

**判决：Accepted** —— 验收命令块在 reviewer 重跑下全部通过、5 路独立注入均「注入→红→`cp`+md5 还原→回绿」、3 项红经逐条核证为外因；请 architect 终审。

## 完成区

**测试结果**：一键证据 `run.sh --inject` rc=0：正向 116/116 PASS；4 路注入（RAM 尺寸 / 矩阵去 arch / 删 capability / 运行布局 kernel_reserved）均「注入→rc=1→`cp`+md5 还原→rc=0」。
**修改文件**：`tools/testcases/lib/machine_profile.py`（真源重写：machine.yaml+exec-envs.yaml+tests-matrix.yaml+`tests/ee-<env>/runtime.yaml`；`--profile`/`DADAO_TEST_PROFILE` 语义不变；`qemu_*` 移除；新增 `suites()/suite_enabled()/to_dict()`）；新增 `tests/ee-tiny/runtime.yaml`、`tests/ee-vast/runtime.yaml`；`git rm tests/shared/machine-profiles.yaml`；消费点 `check_interface_alignment.py`（QEMU 宏 vs machine.yaml）、`run_m5_e2e.py`、`picolibc_tests.py`、`run_embench_e2e.py`、`test_picolibc_smoke.py`、`run_parity.py`、`compare_chipyard.py`、`gen_machine_inc.py`（+重生成两份 `.inc`，值不变）、`tests/shared/README.md`、`tests/inst/schema.md`、`docs/Process-09`、gem5 `fs.py.patch`（注释+blob 哈希）及 40 余份注释同步。
**验收结果**：`check-tests-index` 472 PASS；`check-interface` 89/89；`check-dirs`/`check-no-residue`/`gen_machine_inc --check` PASS；`build-bootrom` PASS；`check-inst-asm` 272/272（633 例）；arch smoke 等价复跑（run_m5_e2e 10/10 + 25-service）PASS；L1 `make check` 至 `check-knowledge-refs` 前全绿。
**新发现/坑**：① `machine_profile.Profile` 只实现 `__getitem__` 时 `dict(prof)` 会按整数索引炸——对外统一用 `to_dict()`；② `components/gem5` new-file 补丁改注释须同步 hunk 行数 + `index` 哈希（`check-index-blobs --fix`）；③ `tools/qemu/generate_atomics_vectors.py` 无 argparse，任何非 `--check` 调用都会写入已退役的 `tests/inst/atomics/*.yaml` 并使 `check-tests-index` 红（勿以 `--help` 探活）；④ `check-arch-smoke` 依赖 `install-host`，本 worktree 未重建工具链 ⇒ 用与其 recipe 等价的两条命令复跑。
**遗留问题**：`check-knowledge-refs` 基线即 FAIL（2 条属 `m15-testcases-013/015` 任务书的证据脚本路径引用，非本任务、未越界修）；`check-milestones-fresh`/`check-temp-dirs` 红属他任务台账与 `/tmp` 陈旧目录（环境态，与本改动无关）；`components/gem5/README.md`、`docs/TestReports/*`、`components/qemu/changelog.md` 仍提旧文件名（历史快照，建议后续文档任务统一）。
