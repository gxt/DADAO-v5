# INFRA-047t: install 落地（`.dadao/` 安装根 + 门控/执行器改从 install 根取可执行）

**模块**：infra
**项目里程碑**：M5
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 范围修正说明（2026-10-07，architect）

本任务原「门控/执行器」界定（`Makefile` 路径变量 + `tools/integ/run_{codegen,elf}_e2e.py` + `tests/**/lit.cfg.py`）**漏掉了 `ADR-0016 D9` 原文点名**的 `run_qemu_test.py`；主会话下发前预检（F1）把验收 2 的 grep 范围收窄至 `Makefile`+`tools/infra`+`tools/integ`，使该漏项在验收中**不可见**（reviewer「第 1 轮验收 B 节」已发现，但因超范围未阻塞判决）。

- **依据（决定性）**：`ADR-0016 D9` 原文——「**门控/执行器**（**`run_qemu_test.py`**、lit、各 `check_*`）改从 **install 根**取可执行；`.work/` 仅作 **build 区**」。故 `tests/scripts/run_qemu_test.py`（`make check` 子门控 `check-qemu-semantics` 的执行器）**本就在 D9 范围内**，原界定与 grep 范围漏项属**范围收窄错误**。
- **处置**：**本任务内闭合，不另立任务兜底**——将 `tests/scripts/run_qemu_test.py` 及 `Makefile:check-qemu-semantics` 调用处纳入「输出 3」，扩「验收 2」grep 范围至 `tests/scripts/`，并新增「验收 8」（`check-qemu-semantics` 改根 + 假绿守卫）。
- **纪律**：本修正由 architect **只追加**（新增本节 + 新增验收 8 + 扩写输出 3/约束/验收 2），**未改写**既有「完成区」「审阅记录」；「完成区」的旧范围结论（7/7）须由 engineer 就新增验收 8 补跑后更新。

## 接口规范

- **背景（现状实测，务必以 `grep`/`ls` 为准）**：
  - **定位机制（`ADR-0016 D7/D8`）已由 `INFRA-019t`（M2）建立**：`manifests/install-dirs.lock.toml`（单一真源，含 `sdk_dir=".dadao"`、`host_toolchain_dir=".dadao/cross-toolchain"`、`target_sysroot_dir=".dadao/dadao-unknown-elf"`、`test_artifacts_dir=".dadao/tests"`）+ `tools/infra/paths.py`（解析模块；`--make` 供 Makefile 消费）。
  - **未落地部分（本任务）**：**没有 install 动作**——`Makefile` 的 `build-mc`/`build-lld`/`build-qemu` 只产 `.work/build/{llvm,qemu}` 内可执行；门控/执行器（`check-lit` 的 `LIT_BIN`、`test-codegen`/`test-elf` 的 `LLC_BIN`/`LLVM_MC_BIN`/`LLVM_OBJCOPY_BIN`/`LLD_BIN`/`QEMU_BIN`）**就地**从 `.work/build` 取；`.dadao/` 下**只有** `tests/`（见 `ls -la .dadao/`），**无** `cross-toolchain/`、`dadao-unknown-elf/`。
- **输入**：
  - `.tao/adr/adr-0016-dadao-install-layout.md`（**Accepted**，D1–D11；用户 2026-10-02 逐条确认）。
  - `manifests/install-dirs.lock.toml`、`tools/infra/paths.py`（现状，勿重复造）；`Makefile`（`build-*` 目标、路径变量段）。
  - `.tao/knowledge/milestones.md`「M5 起步待办」（用户 2026-10-06）：落地 `D1–D11`——host 工具链 → `.dadao/cross-toolchain`（D3/D4/D11）、target sysroot → `.dadao/dadao-unknown-elf`（D5）、`manifests/` 单一真源定位（D7，禁硬编码）、**门控/执行器改从 install 根取可执行**、`.work/` **仅**作 build 区（D9）；保留「从源码可重建」。
- **输出**：
  1. `Makefile` 新增 **install 目标**（命名建议 `install-host`，可被 `make check` 之外的流程调用）：把所需 host 工具集从构建树汇入 `$(HOST_TOOLCHAIN_DIR)`（`bin/`）。**按 `D11`「只装所需工具集」**——至少 `llvm-mc`/`llvm-objdump`/`llvm-readobj`/`FileCheck`/`not`/`llc`/`ld.lld`/`llvm-lit` + `qemu-system-dadao`（以 `build-mc`/`build-lld`/`build-qemu` 现存目标集为准）；**不得**全量 `cmake --install`。
     - **`llvm-lit` 的安装口径**：`llvm-lit` 是**构建树生成的脚本**（`$(LLVM_BUILD)/bin/llvm-lit`，非单纯二进制，`Makefile:347` `LIT_BIN` 依赖它）；本任务禁全量 `cmake --install`，故须择一方式将其引入 install 根（由 engineer 实测确定并留证）：
       - ① `cp` 脚本 + **就地适配**（确保其能找到被测工具——必要时经 `--param`/环境变量或生成最小配置）；
       - ② 以最小 `cmake --install --component` 或等价方式**仅装 lit**（须说明为何不构成「全量 install」）。
     - **验收须真跑 `make check-lit`，全 `tests/*/lit` 用例通过**（以实测为准，不以「文件存在」代替）。
  2. `$(TARGET_SYSROOT_DIR)`（`.dadao/dadao-unknown-elf/{include,lib}`）按 `D5` 建立（当前无 header/lib 消费者，建空骨架 + README 指针即可，**不得**臆造内容）。
  3. **门控/执行器改从 install 根取可执行**（`D9`）：`Makefile`（`LIT_BIN`/`LLC_BIN`/`LLVM_MC_BIN`/`LLVM_OBJCOPY_BIN`/`LLD_BIN`/`QEMU_BIN` 等）**改为经 `$(HOST_TOOLCHAIN_BIN)` 解析**（或经 `tools/infra/paths.py`）；lit 的 `lit.cfg.py` 工具替换、`tools/integ/run_{codegen,elf}_e2e.py` 默认工具路径如硬编码 `.work/build` 亦一并对齐（**逐个 grep 核实，不臆测**）。
     - **「门控/执行器」的界定**（`D9` 对齐范围，本修正已扩）：指 `Makefile` 的路径变量段（`LIT_BIN`/`LLC_BIN`/`LLVM_MC_BIN`/`LLVM_OBJCOPY_BIN`/`LLD_BIN`/`QEMU_BIN` 等）+ `tools/integ/run_{codegen,elf}_e2e.py` 的 `DEFAULT_*` 工具路径 + lit 相关配置（`tests/**/lit.cfg.py`）+ **`tests/scripts/run_qemu_test.py`**（`D9` 原文点名）。
     - **`tests/scripts/run_qemu_test.py`（本修正新增，`D9` 原文点名）**：`DEFAULT_QEMU`（现 `L32 = ".work/build/qemu/qemu-system-dadao"`）**改为经 `tools/infra/paths.py` 解析到 install 根**——即 `str(paths.host_toolchain_bin() / "qemu-system-dadao")`（**禁硬编码** install 路径，`D7`）。该脚本**已** import `paths.py`（`L62-64`，现用于 artifacts 目录），只需让 `DEFAULT_QEMU` 也走 `paths.py`。**保留** `find_qemu()` 既有优先级（`L74-93`）：env `QEMU_SYSTEM_DADAO` → 新 `DEFAULT_QEMU`（install 根）→ `shutil.which` PATH 兜底；`--qemu` argparse（`L627`）不动。
     - **`Makefile` 的 `check-qemu-semantics`**（`L507`，属 `make check`）：其调用 `tests/scripts/run_qemu_test.py` 处（`L517`）**增传 `--qemu $(QEMU_BIN)`**，使该门控显式从 install 根取 QEMU（`QEMU_BIN = $(HOST_TOOLCHAIN_BIN)/qemu-system-dadao`，`L397`）。
     - **`tests/scripts/verify_harness_dump.py`（核实后定去留）**：`L43` 同款硬编码 `QEMU = ".work/build/qemu/qemu-system-dadao"`。**实测 `grep` 确认其不被任何 `Makefile` 门控经代码/子进程调用**（仅自身 docstring 引用）⇒ **非**门控/执行器，**保留**（对齐可留后续任务；本任务内如顺手对齐，须确保不引入门控副作用与行为变化）。
     - **不在本任务范围**：`tools/qemu/*`（23 文件，历史任务探针/冒烟脚本）与 `tools/llvm/test_*.py`（2 文件，独立脚本、非 `Makefile` 门控目标）中的 `.work/build` 引用**不属**门控/执行器，**保留**（如需对齐**另立任务**，不在本任务顺手改）。**唯一允许保留的文档命中**：`tests/scripts/README.md:68`（描述 harness 期望的 QEMU 路径）——**允许保留**，但须**同步更新其描述**（改指 install 根）或在完成区**说明**其为何保留（二者择一，须留证）。
  4. 构建目标保持**可从源码重建**：`install-host` 依赖 `build-mc`/`build-lld`/`build-qemu`；`.work/` 仍为唯一构建真源（install 只是缓存，`D9`）。
- **约束（硬）**：
  - **不改组件源码**（`components/**`、`.work/source/**` 不碰）；本任务**不涉补丁导出**。
  - **路径一律真实路径**（`D8`，`paths.py` 已实现）；`Makefile`/脚本**禁硬编码** install 路径（`D7`）。
  - **只动任务范围**：**不得为满足验收 2 而修改 `tools/qemu/*`、`tools/llvm/test_*.py`**（越界）；其 `.work/build` 引用按「输出 3」界定**保留**。（本范围修正后 `tests/scripts/run_qemu_test.py` **属**本任务范围、`tests/scripts/README.md` 描述须同步；`tools/qemu/*`、`tools/llvm/test_*.py` 仍**不得**动。）
  - **不得弱化任何门控**；改路径后须以**注入反例**证明门控仍承重（把 install 根某可执行临时改名 ⇒ 依赖它的门控**非零退出** ⇒ 还原回绿）——防「门控改路径后假绿」。
  - `Makefile` 为共享文件，与其它改 `Makefile` 的任务（`INFRA-048t` 等）**串行**。
  - 失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/INFRA-047t/`；**不提交 git**（architect 统一提交）；复杂命令输出留存 `.work/log/infra/`（`cmd > log 2>&1; rc=$?`，**禁 `tee`**）。
  - **重建成本申报（实测口径）**：`build-mc` ninja 增量（秒级）；**`build-lld` 每次必跑 cmake 重配 + 链接（数分钟，源码注释明说跳过 guard 不可用）**；`build-qemu` 有增量 fast path（秒级）⇒ `make install-host` 约 **3–8 分钟**，整套验收约 **10–20 分钟**，`JOBS=8`；开工前在回复中写明预计耗时。

## 验收标准

1. **install 落地**：`make install-host` EXIT=0；`ls -l $(HOST_TOOLCHAIN_BIN)/` 含 `llvm-mc`/`llvm-objdump`/`llvm-readobj`/`FileCheck`/`not`/`llc`/`ld.lld`/`llvm-lit`/`qemu-system-dadao`（逐个 `--version`/`-h` EXIT=0，给真实输出）；`$(TARGET_SYSROOT_DIR)` 存在（`include/`、`lib/`）；**`make check-lit` 真实全绿**（`tests/llvm/lit/MC/DADAO`、`tests/llvm/lit/CodeGen/DADAO`、`tests/e2e/lit`；当前共约 60 个用例，以 `make check-lit` 实测输出为准，**必须 0 失败**；不以「文件存在」代替）。
2. **门控改根**：`grep -rn "\.work/build" Makefile tools/infra tools/integ tests/scripts | grep -v __pycache__` 显示门控/执行器可执行**不再**取自 `.work/build`（改经 install 根/`paths.py`）；给真实 `grep` 输出。**范围声明**：`tools/qemu/*`（历史任务探针/冒烟脚本）与 `tools/llvm/test_*.py`（独立脚本、非 `Makefile` 门控目标）**不在本任务范围**，其 `.work/build` 引用**保留**（如需对齐**另立任务**）；`tests/scripts/` 下**门控执行器**（`run_qemu_test.py`）的 `.work/build` 须**清零**；`tests/scripts/README.md` 的文档命中**允许保留**但须**同步更新描述或说明**（见「输出 3」末条）。
3. **不回归**：`make test-codegen` 15/15 EXIT=0；`make test-elf` 5/5 EXIT=0；`make check` EXIT=0（含 `check-lit`）；给真实输出。
4. **可重建**：删 `.dadao/cross-toolchain` 后 `make install-host` 仍 EXIT=0（从 `.work/` 构建树重建），给真实输出。
5. **假绿守卫（反例门控）**：临时重命名 install 根某可执行（如 `llvm-mc`）⇒ 依赖它的门控（`test-elf` 或 `check-lit`）**非零退出**；还原后回绿。给真实「改名→FAIL→还原→回绿」输出；**还原用 `cp`+`md5` 对账，禁用 `git checkout`/`git restore`/`git stash`**。
6. **一键证据脚本**：`.work/evidence/INFRA-047t/run.sh`——非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + rc」；内置「注入→FAIL→还原→回绿」自检；结尾**禁 `tee`**（用 `rc=$?`）。
7. **无残留**：`make check-no-residue` EXIT=0；`git status --untracked-files=all` 仅本任务应有改动（`Makefile` + 相关脚本 + 本任务书）；`.dadao/` 为 gitignored（不入库）。
8. **`check-qemu-semantics` 改根 + 假绿守卫**（本修正新增）：`make check-qemu-semantics` EXIT=0（给真实输出，含 `PASS` 行）；**注入反例**——临时改名 install 根 `qemu-system-dadao` ⇒ `make check-qemu-semantics`（及/或 `make test-elf`，二者均依赖该可执行）**非零退出** ⇒ 还原后回绿；给真实「改名→FAIL→还原→回绿」输出。此注入同时证明该门控**确从 install 根取 QEMU**（若仍回退 `.work/build`，rename install 根不会致 FAIL）。**还原用 `cp`+`md5` 对账，禁用 `git checkout`/`git restore`/`git stash`**。

## 完成区

**测试结果**：通过 **7/7 验收项**（一键证据脚本 `.work/evidence/INFRA-047t/run.sh` 汇总 **24 passed, 0 failed**, EXIT=0）。逐项真实输出见下「验收结果」。失败原因：无。

**修改文件**（本任务**完整清单** = 前一轮 6 份源文件 + 第 2 轮补修新增/修改；对账见各条目后标注）：

前半（已 WIP 提交 `88baab4`；`abf131d`）：
- `Makefile`（新增 `install-host` 目标；`LIT_BIN`/`LLC_BIN`/`LLVM_MC_BIN`/`LLVM_OBJCOPY_BIN`/`QEMU_BIN`/`LLD_BIN` 改经 `$(HOST_TOOLCHAIN_BIN)`；`test-codegen`/`test-elf` 依赖改 `install-host`；help）——**第 2 轮再次修改**（`check-qemu-semantics` 增传 `--qemu`，见下）
- `tools/integ/run_codegen_e2e.py`（`DEFAULT_*` 改经 `tools/infra/paths.py::host_toolchain_bin()`）
- `tools/integ/run_elf_e2e.py`（同上）
- `tests/llvm/lit/MC/DADAO/lit.cfg.py`（工具目录改 install 根 + 注释）
- `tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`（同上）
- `tests/e2e/lit/lit.cfg.py`（工具/qemu 改 install 根 + 注释）

第 2 轮补修新增/修改（D9 原文点名 `run_qemu_test.py`）：
- `tests/scripts/run_qemu_test.py`（`DEFAULT_QEMU` 改经 `paths.py::host_toolchain_bin()`；`find_qemu()` 优先级 env → install 根 → PATH 保留；`--qemu` 不动）
- `tests/scripts/README.md`（「QEMU Binary」节改指 install 根/`paths.py` 口径）
- `Makefile`（`check-qemu-semantics` 调用处增传 `--qemu $(QEMU_BIN)`；注释同步）

- `.tao/tasks/infra/INFRA-047t-install落地.md`（本任务书：完成区/自审/状态）
- 证据脚本/日志落在 gitignored 的 `.work/evidence/INFRA-047t/run.sh`、`.work/log/infra/INFRA-047t-*.log`（不入库）

**与 `git status --porcelain -uall` 对账**：现显示第 2 轮**未提交** 3 份源文件——`Makefile`、`tests/scripts/README.md`、`tests/scripts/run_qemu_test.py`——加本任务书；前一轮 6 份源文件已入 `88baab4`/`abf131d`，故不再出现在 `git status`（逐条吻合，无遗漏/无越界）。

**验收结果**（真实命令输出 / rc，均取自 `.work/log/infra/INFRA-047t-*.log`）：

- **验收1 install 落地**：`make install-host` → `EXIT=0`（`install-host: PASS`）。`ls .dadao/cross-toolchain/bin/` = `FileCheck ld.lld->lld llc lld llvm-lit llvm-mc llvm-objcopy llvm-objdump llvm-readobj not qemu-system-dadao`；逐个 smoke：
  ```
  rc=0 llvm-mc --version / llvm-objdump --version / llvm-readobj --version / FileCheck --version
  rc=0 llc --version / ld.lld --version ("LLD 23.1.1") / llvm-lit --version ("lit 23.1.1dev") / qemu-system-dadao --version ("QEMU emulator version 11.1.1")
  rc=0 `not /bin/false`（取反，期望 0）；rc=1 `not /bin/true`（期望 1）
  ```
  （`not` 无 `--version`/`-h`：它把首个位置参数当被测程序，故以功能调用核验，见「新发现/坑」。）
  `$(TARGET_SYSROOT_DIR)`：`.dadao/dadao-unknown-elf/{include,lib}` + `README.md` 存在。`make check-lit` → `EXIT=0`，`Total Discovered Tests: 60 / Passed: 60 (100.00%) / Failed: 0`（MC+CodeGen+E2E 全绿，真跑非「文件存在」）。
- **验收2 门控改根**：`grep -rn "\.work/build" Makefile tools/infra tools/integ | grep -v __pycache__` 剩余命中**仅** build 区变量/注释，**无**门控/执行器可执行路径：
  ```
  Makefile:28/30/32  QEMU_BUILD/LLVM_BUILD/GEM5_BUILD ?= .work/build/...   ← D9「.work/ 仅作 build 区」的构建树定义
  Makefile:178/184/379  注释；tools/integ/run_*.py:53/61  注释
  ```
  门控路径实测（证据脚本 A2，`no-match`）：
  ```
  380:LIT_BIN = $(HOST_TOOLCHAIN_BIN)/llvm-lit
  394:LLC_BIN = $(HOST_TOOLCHAIN_BIN)/llc   395:LLVM_MC_BIN=.../llvm-mc
  396:LLVM_OBJCOPY_BIN = .../llvm-objcopy  397:QEMU_BIN = .../qemu-system-dadao  428:LLD_BIN = .../ld.lld
  run_codegen_e2e.py:70-73 / run_elf_e2e.py:78-81  DEFAULT_* = os.path.join(_TOOLCHAIN_BIN, ...)
  ```
- **验收3 不回归**：`make test-codegen` → `EXIT=0`，`Results: 15/15 passed, 0 failed`；`make test-elf` → `EXIT=0`，`Results: 5/5 passed, 0 failed`；`make check` → `EXIT=0`，`repository checks: PASS`（含 check-lit 60/60）。
- **验收4 可重建**：`rm -rf .dadao/cross-toolchain`（`ls` → `No such file or directory`, rc=2）后 `make install-host` → `EXIT=0`，11 个 bin 条目齐全（从 `.work/` 构建树重建）。
- **验收5 假绿守卫**：改名 install 根 `llvm-mc` → `make check-lit` `EXIT=2`（`Passed: 2 / Failed: 58`）；`cp`+`md5` 还原（`.inject-bak` mv 回，`md5sum` 前后一致 `9501910d88d3f4337ced6fe1f7de3a71`）→ `make check-lit` `EXIT=0`（`Passed: 60 (100.00%)`）。**未**用 `git checkout/restore/stash`；无 `.inject-bak` 残留。
- **验收6 一键证据脚本**：`.work/evidence/INFRA-047t/run.sh`（非交互；逐项打印 name/expected/actual/rc；含内置注入自检；结尾 `rc=$?` 无 `tee`）→ `EVIDENCE EXIT=0`，`=== summary: 24 passed, 0 failed ===`。
- **验收7 无残留**：`make check-no-residue` → `EXIT=0`（`check-no-residue: PASS`）；`git status --porcelain -uall` 仅上列 6 个源文件 + 本任务书；`.dadao/` 为 gitignored（不入库）。

**新发现/坑**：
- **`llvm-lit` 不能裸 `cp`**：它是**构建树生成的脚本**（`Makefile` 旧 `LIT_BIN`），依赖 `path()` 把 `<build>/bin` 上溯到 `.work/source/llvm-project/llvm/utils/lit` 找到 `lit` 包，并内联 `map_config`。拷到 `.dadao/cross-toolchain/bin` 后上溯目标不存在 ⇒ `import lit` 失败。本任务采「option ①：装 `lit` 包 + 生成最小 launcher」——`install-host` 把 `$(LLVM_SRC)/utils/lit/lit` 包拷到 `<prefix>/share/lit/lit`，并 `printf` 生成自定位 wrapper（`_prefix=dirname(dirname(__file__))` → `sys.path.insert(<prefix>/share/lit)`）。install 根自包含（删 `.work` 不影响 `llvm-lit --version`/门控）。**未**用 `cmake --install`（不存在 lit component；见 `utils/lit/CMakeLists.txt` 无 install 规则）。
- **`not` 无 `--version`/`-h`**：`not` 把第一个参数当作 PATH 中要执行的程序，故用 `not /bin/false`（rc=0）证明可用；验收1的「逐个 `--version`/`-h`」对 `not` 以功能调用替代。
- **lit scratch 落点**：`test_exec_root = dirname(tools_dir)/test-output/<suite>`；tools_dir 改指 install 根后，scratch 落 `.dadao/cross-toolchain/test-output/`（gitignored，可随 install 重建），不再落 `.work/build/llvm/test-output`。
- **D9 未覆盖（本任务范围外，勿在本任务顺手改）**：`Makefile:check-qemu-semantics` 经 `tests/scripts/run_qemu_test.py` 仍默认 `.work/build/qemu/qemu-system-dadao`；`tests/scripts/verify_harness_dump.py` 同。二者**不在**本任务「门控/执行器」界定（Makefile 路径变量 + `tools/integ/run_{codegen,elf}_e2e.py` + `tests/**/lit.cfg.py`）与验收2 的 grep 范围（`Makefile tools/infra tools/integ`）内。`tools/qemu/*`（23 文件）与 `tools/llvm/test_*.py`（2 文件）中的 `.work/build` 按任务书**保留**。

**遗留问题**：
- **建议另立任务**：把 `check-qemu-semantics` 依赖的 `tests/scripts/run_qemu_test.py`（及其 `DEFAULT_QEMU`）也对齐到 install 根（D9），并补 `tests/scripts/verify_harness_dump.py`。本任务未做（越界）。
- `check-lit` **未**声明 `install-host` 前置依赖（保持 INFRA-021t 既有「不构建、缺失即显式报错」设计，fail-closed：`test -x $(LIT_BIN) || exit 1`）；`test-codegen`/`test-elf` 已改依赖 `install-host`。
- install-host 每次 `cp -a` ~4.7 GB（llc 1.7G + lld 1.9G 占大头）；`make check` 不触发（仅 `test-codegen`/`test-elf`/显式 `install-host` 触发）。未做增量拷贝优化（KISS；如需可后续）。

### 第 2 轮（补修 D9 缺口）

**发起依据**：architect「范围修正说明」（2026-10-07）——`ADR-0016 D9` **原文点名** `run_qemu_test.py`；原「门控/执行器」界定与验收 2 的 grep 范围漏项，本任务内闭合（新增「验收 8」）。本轮**仅做增量补修**（前一轮产出已 WIP 提交 `88baab4`/`abf131d`），**未改写**既有完成区/审阅记录。

**测试结果**（本轮）：通过 **8/8 验收项**；一键证据脚本 `.work/evidence/INFRA-047t/run.sh` 汇总 **31 passed, 0 failed**（`EVIDENCE EXIT=0`）。失败原因：无。

**验收结果**（真实命令输出 / rc；均 `cmd > log 2>&1; rc=$?`，**禁 `tee`**；日志 `.work/log/infra/INFRA-047t-*.log`）：

- **验收1 install 落地**（复跑）：`make install-host` → `EXIT=0`（增量 25s；`install-host: PASS`）。`ls .dadao/cross-toolchain/bin/` = `FileCheck ld.lld->lld llc lld llvm-lit llvm-mc llvm-objcopy llvm-objdump llvm-readobj not qemu-system-dadao`（11 项）；逐个 smoke 全 `rc=0`（`llvm-mc/llvm-objdump/llvm-readobj/FileCheck/llc/ld.lld/llvm-lit/qemu-system-dadao --version`；`not /bin/false`=0、`not /bin/true`=1）。sysroot `.dadao/dadao-unknown-elf/{include,lib,README.md}` 存在。
- **验收2 门控改根（扩范围 grep）**：`grep -rn "\.work/build" Makefile tools/infra tools/integ tests/scripts | grep -v __pycache__` → 剩余命中**仅**：
  ```
  Makefile:28/30/32   QEMU/LLVM/GEM5_BUILD ?= .work/build/...   ← D9「.work/ 仅作 build 区」
  Makefile:178/184/379 注释；tools/integ/run_*.py:53/61 注释
  tests/scripts/verify_harness_dump.py:43  QEMU = ".work/build/qemu/qemu-system-dadao"  ← 非门控（见下）
  ```
  `tests/scripts/run_qemu_test.py` 与 `tests/scripts/README.md` 的 `.work/build` **已清零**。证据脚本 A2b 实测：`DEFAULT_QEMU = /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin/qemu-system-dadao`（`under install root`），`Makefile check-qemu-semantics passes --qemu` match。
- **验收3 不回归**：`make test-codegen` → `EXIT=0`（`Results: 15/15 passed, 0 failed`）；`make test-elf` → `EXIT=0`（`Results: 5/5 passed, 0 failed`）；`make check` → `EXIT=0`（`check-qemu-semantics: PASS`；`Total Discovered Tests: 60 / Passed: 60 (100.00%)`；`repository checks: PASS`）。
- **验收4 可重建**：`rm -rf .dadao/cross-toolchain`（`ls` → `No such file or directory`, rc=2）→ `make install-host` → `EXIT=0`，11 项 bin 齐全（从 `.work/` 构建树重建）。
- **验收5 假绿守卫（llvm-mc）**：证据脚本 A5 复跑仍绿——注入 `llvm-mc` → `check-lit` `Passed: 2 (3.33%) / Failed: 58`（非零）→ `cp`+md5 还原（`9501910d88d3f4337ced6fe1f7de3a71`）→ `Passed: 60 (100.00%)`。
- **验收6 一键证据脚本**：`.work/evidence/INFRA-047t/run.sh`（非交互；逐项打印 name/expected/actual/rc；含 A5+A8b 双注入自检；结尾 `rc=$?` 无 `tee`）→ `=== summary: 31 passed, 0 failed ===`，`EVIDENCE EXIT=0`。**脚本可失败（自证）**：临时改名 install 根 `llvm-readobj` 后跑 `run.sh` → `=== summary: 29 passed, 2 failed ===`，`INJECT_SCRIPT_RC=1`（`FAIL tool:llvm-readobj --version actual=127`、`FAIL make check-lit actual=2`）；`cp`+md5 还原后 → `31 passed, 0 failed`，`RESTORE_SCRIPT_RC=0`，无 `.inject-bak` 残留。
- **验收7 无残留**：`make check-no-residue` → `EXIT=0`；`git status --porcelain -uall` = ` M Makefile` / ` M tests/scripts/README.md` / ` M tests/scripts/run_qemu_test.py`（+ 本任务书）；`.dadao/` gitignored（不入库）。
- **验收8 `check-qemu-semantics` 改根 + 假绿守卫**（新增）：`make check-qemu-semantics` → `EXIT=0`，`Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors`，`check-qemu-semantics: PASS`；**注入反例**——`mv .dadao/cross-toolchain/bin/qemu-system-dadao{,.inject-bak}`（`ls` rc=2）→ `make check-qemu-semantics` → `INJECT_RC=2`（`check-qemu-semantics: FAIL (rc=1)`，`tail` 显示 `FileNotFoundError: .../bin/qemu-system-dadao`）→ `mv` 还原，`md5sum` 前后一致（`38e16e3daf60fc50efe4692d0fbcc177`）→ `make check-qemu-semantics` → `RESTORE_RC=0`（149/149），无 `.inject-bak` 残留。**未**用 `git checkout/restore/stash`。**门控承重判定**：`--qemu $(QEMU_BIN)` 使改名 install 根 QEMU 即致 FAIL ⇒ 证明该门控**确从 install 根取 QEMU**（不再回退 `.work/build`）。证据脚本 A8b 复跑此注入，纳入 `31 passed`。

**新发现/坑**：
- `tests/scripts/verify_harness_dump.py:43` 仍硬编码 `.work/build/qemu/qemu-system-dadao`：**实测 `grep -rn "verify_harness_dump"`（`Makefile`/`*.py`/`*.sh`）全仓仅命中其自身 docstring（`verify_harness_dump.py:17`），无任何门控/子进程调用** ⇒ 非门控/执行器，按任务书「输出 3」**保留**（out-of-scope）。
- `install-host` 会把 install 根缺失的受管工具从 `.work/build` **重新拷回**：故 `test-codegen`/`test-elf`（`install-host` 依赖）**不是** install 根注入靶——注入会被 `install-host` 静默修复；`check-lit`/`check-qemu-semantics`（无 `install-host` 依赖）才是有效注入靶。
- `check-qemu-semantics` 现显式传 `--qemu $(QEMU_BIN)` ⇒ 该门控**依赖 install 根存在**：`.dadao/cross-toolchain` 缺失时 `make check` 会 FAIL（fail-closed），不再回退 `.work/build`（对齐 D9）。
- `run_qemu_test.py` 把 `paths.py` 导入上移到常量段后，`DEFAULT_QEMU` 在**模块导入时**即解析（读 `manifests/install-dirs.lock.toml`，缺失则显式 `sys.exit(1)`）；`--qemu` 显式路径仍优先（`args.qemu or find_qemu()` 短路），不改行为。

**遗留问题**：
- ✅**已修**（上轮遗留）：`run_qemu_test.py` 的 `DEFAULT_QEMU` 已对齐 install 根——上轮「建议另立任务」项**本任务内闭合**。
- `tests/scripts/verify_harness_dump.py` 保留 `.work/build` 硬编码（非门控；如需对齐**另立任务**，不在本任务顺手改）。
- `check-lit` 仍未声明 `install-host` 前置依赖（保持 INFRA-021t fail-closed 设计），与上轮一致。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：逐行审 `git diff` 的 6 个源文件（Makefile / 2×integ runner / 3×lit.cfg.py）。
**逻辑正确性**：
- F1（已修）：`llvm-lit` wrapper 首发漏 `import sys` → `NameError`（实测 `llvm-lit --version` traceback）。已补 `'import sys'` 并重跑 `make install-host`；复验 `lit 23.1.1dev` rc=0。✅
- F2（已修）：证据脚本 A5 注入断言用 `record <name> "non-zero" "$rc_inj"` 做**字符串相等**，`"non-zero"≠"2"` 恒 FAIL（首轮 `EVIDENCE EXIT=1`，23/24）。已改为先判 `[ "$rc_inj" -ne 0 ]` 再写定值；复验 24/24 EXIT=0。✅
- 门控路径：`check-lit`/`test-codegen`/`test-elf` 经 install 根解析，且注入证明**承重**（改名前非零）。✅
- 边界：install 缺失时 `check-lit` 显式报错非零（fail-closed）；lit.cfg 找不到 manifest 时 import 失败非静默。✅
**设计与惯用法**：install 根自包含（无 `cmake --install`，D11）；`paths.py` 单一真源（D7）；`.work` 仍为构建真源（D9）。`ld.lld` 以 `ln -sf` 保持 symlink（省 1.9G）。✅
**防造假**：所有 rc/输出取自真实日志；证据脚本对被测 install 根可执行做**独立注入→FAIL→md5 还原→回绿**。✅

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 wrapper 缺 `import sys` | ✅已修 | Makefile `install-host` printf 加 `'import sys'` | 重跑 `make install-host` EXIT=0；`llvm-lit --version` → `lit 23.1.1dev` rc=0 |
| F2 证据脚本注入断言恒 FAIL | ✅已修 | `.work/evidence/INFRA-047t/run.sh` A5 改先判 `-ne 0` | `run.sh` → `24 passed, 0 failed`，`EVIDENCE EXIT=0` |
| `not` 无 `--version/-h` | ✅已处置（非缺陷） | 验收以 `not /bin/false`(=0)/`not /bin/true`(=1) 功能核验 | 证据脚本 A1 rc=0/rc=1 两行 PASS |
| `tests/scripts/run_qemu_test.py` 未对齐 install 根 | ⏸延后 | 无（超本任务界定，见「遗留问题」） | 建议另立任务 |


#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**〔改 install 根 `llvm-mc` 名〕+ 约束核验 + B 节门控来源表 + 判决）

**审查者**：mimo-v2.5-pro（reviewer subagent）
**审查时间**：2026-10-07

---

##### A. 证据脚本审核（`.work/evidence/INFRA-047t/run.sh`）

逐条核对每个断言的 FAIL 路径：

| 行 | 断言 | FAIL 路径 | 恒真？ |
|---|---|---|---|
| 54–56 | `tool:$tool --version` rc=0 | rc≠0 → FAIL | 否 ✅ |
| 58–59 | `not /bin/false` rc=0 | rc≠0 → FAIL | 否 ✅ |
| 60–61 | `not /bin/true` rc=1 | rc≠1 → FAIL | 否 ✅ |
| 67 | sysroot include 存在 | 目录不存在 → FAIL | 否 ✅ |
| 68 | sysroot lib 存在 | 目录不存在 → FAIL | 否 ✅ |
| 69 | sysroot README.md 存在 | 文件不存在 → FAIL | 否 ✅ |
| 76–80 | Makefile gate vars 无 `.work/build` | grep 有匹配 → FAIL | 否 ✅ |
| 82–87 | integ DEFAULT_* 无 `.work/build` | grep 有匹配 → FAIL | 否 ✅ |
| 88–92 | integ DEFAULT_* 用 paths.py | grep 无匹配 → FAIL | 否 ✅ |
| 99–100 | `make check-lit` rc=0 | rc≠0 → FAIL | 否 ✅ |
| 103–104 | `make test-codegen` rc=0 | rc≠0 → FAIL | 否 ✅ |
| 107–108 | `make test-elf` rc=0 | rc≠0 → FAIL | 否 ✅ |
| 111–112 | `make check` rc=0 | rc≠0 → FAIL | 否 ✅ |
| 119–120 | `make check-no-residue` rc=0 | rc≠0 → FAIL | 否 ✅ |
| 136–140 | 注入后 check-lit 非零 | rc=0 → `unexpected-pass(0)` → FAIL | 否 ✅ |
| 141 | md5 还原一致 | md5 不等 → FAIL | 否 ✅ |
| 142 | 还原后 check-lit rc=0 | rc≠0 → FAIL | 否 ✅ |

**注入自检**：行 126–144，rename `llvm-mc` → run `check-lit` → expect FAIL → mv back → md5 比对 → run `check-lit` expect PASS。**非空且可还原** ✅
**结尾**：行 149 `exit 1`（fail 非零）/ 行 152 `exit 0`，无 `tee`，用 `$fail` 变量判。✅
**脚本质量**：合格，无需打回。

---

##### A. 重跑证据脚本（真实输出）

```
$ bash .work/evidence/INFRA-047t/run.sh > /tmp/opencode/INFRA-047t-review/evidence-run.log 2>&1; echo "EVIDENCE_EXIT=$?"
EVIDENCE_EXIT=0
```

完整输出（`/tmp/opencode/INFRA-047t-review/evidence-run.log`）：

```
=== INFRA-047t evidence ===
REPO_ROOT = /mnt/tao/DADAO-v5
HOST_TOOLCHAIN_BIN = /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin
TARGET_SYSROOT_DIR = /mnt/tao/DADAO-v5/.dadao/dadao-unknown-elf

--- A1: installed host tool set ---
PASS  tool:llvm-mc --version                         expected=0 actual=0
PASS  tool:llvm-objdump --version                    expected=0 actual=0
PASS  tool:llvm-readobj --version                    expected=0 actual=0
PASS  tool:FileCheck --version                       expected=0 actual=0
PASS  tool:llc --version                             expected=0 actual=0
PASS  tool:ld.lld --version                          expected=0 actual=0
PASS  tool:llvm-lit --version                        expected=0 actual=0
PASS  tool:qemu-system-dadao --version               expected=0 actual=0
PASS  tool:not /bin/false (inverts)                  expected=0 actual=0
PASS  tool:not /bin/true (inverts)                   expected=1 actual=1
--- A1b: target sysroot skeleton ---
PASS  sysroot ./include exists                       expected=0 actual=0
PASS  sysroot ./lib exists                           expected=0 actual=0
PASS  sysroot ./README.md exists                     expected=0 actual=0
--- A2: gate paths resolve to the install root ---
PASS  Makefile gate vars free of .work/build         expected=no-match actual=no-match
PASS  integ DEFAULT_* free of .work/build            expected=no-match actual=no-match
PASS  integ DEFAULT_* use paths.py toolchain bin     expected=match actual=match
--- A3: gates ---
PASS  make check-lit                                 expected=0 actual=0  (Passed: 60, 100.00%)
PASS  make test-codegen                              expected=0 actual=0  (Results: 15/15 passed, 0 failed)
PASS  make test-elf                                  expected=0 actual=0  (Results: 5/5 passed, 0 failed)
PASS  make check                                     expected=0 actual=0  (repository checks: PASS)
--- A7: residue gate ---
PASS  make check-no-residue                          expected=0 actual=0
--- A5: injection self-test (rename install-root llvm-mc) ---
PASS  injected check-lit is non-zero                 expected=non-zero actual=non-zero
PASS  llvm-mc restored (md5 match)                   expected=0 actual=0
PASS  restored check-lit is green                    expected=0 actual=0
inject log:   Passed:  2 (3.33%)   Failed: 58 (96.67%)
restore log:   Passed: 60 (100.00%)

=== summary: 24 passed, 0 failed ===
```

**EVIDENCE_EXIT=0**，**24/24 PASS**。与 engineer 完成区声称一致。

---

##### A. 独立注入反例（reviewer 自行执行，不由 engineer 自检替代）

**注入目标**：rename install 根 `llvm-mc`（`check-lit` 依赖，不触发 `install-host` 重建）。

**注入前快照**：
```
$ md5sum .dadao/cross-toolchain/bin/llvm-mc
9501910d88d3f4337ced6fe1f7de3a71  .dadao/cross-toolchain/bin/llvm-mc

$ cp -a .dadao/cross-toolchain/bin/llvm-mc /tmp/opencode/INFRA-047t-review/llvm-mc.preinject
$ md5sum /tmp/opencode/INFRA-047t-review/llvm-mc.preinject
9501910d88d3f4337ced6fe1f7de3a71  /tmp/opencode/INFRA-047t-review/llvm-mc.preinject
```

**注入（改名）**：
```
$ mv .dadao/cross-toolchain/bin/llvm-mc .dadao/cross-toolchain/bin/llvm-mc.inject-bak
$ ls .dadao/cross-toolchain/bin/llvm-mc
ls: cannot access '.dadao/cross-toolchain/bin/llvm-mc': No such file or directory
```

**注入后门控**：
```
$ make check-lit > inject-check-lit.log 2>&1; echo "INJECT_RC=$?"
INJECT_RC=2

$ grep -E 'Passed:|Failed:' inject-check-lit.log
  Passed:  2 (3.33%)
  Failed: 58 (96.67%)
```

**→ 门控承重确认：2/58，rc=2（非零）。**

**还原**：
```
$ mv .dadao/cross-toolchain/bin/llvm-mc.inject-bak .dadao/cross-toolchain/bin/llvm-mc
$ md5sum .dadao/cross-toolchain/bin/llvm-mc
9501910d88d3f4337ced6fe1f7de3a71  .dadao/cross-toolchain/bin/llvm-mc
$ md5sum /tmp/opencode/INFRA-047t-review/llvm-mc.preinject
9501910d88d3f4337ced6fe1f7de3a71  /tmp/opencode/INFRA-047t-review/llvm-mc.preinject
→ md5 一致 ✅
```

**还原后门控**：
```
$ make check-lit > restore-check-lit.log 2>&1; echo "RESTORE_RC=$?"
RESTORE_RC=0

$ grep -E 'Passed:|Failed:' restore-check-lit.log
  Passed: 60 (100.00%)
```

**→ 回绿确认：60/60，rc=0。**

**还原纪律**：未使用 `git checkout`/`git restore`/`git stash`；用 `cp` 备份 + `md5sum` 对账。注入前后 `git status --porcelain -uall` 均为空（`.dadao/` 为 gitignored）。

---

##### A. 验收标准逐条核验

| # | 验收标准 | reviewer 判定 | 证据 |
|---|---------|-------------|------|
| 1 | `make install-host` EXIT=0；11 个 bin 工具可运行；sysroot 骨架存在；`make check-lit` 60/60 | ✅ PASS | 证据脚本 A1/A1b/A3 + reviewer 重跑 EXIT=0 |
| 2 | `grep -rn "\.work/build" Makefile tools/infra tools/integ` 门控/执行器无 `.work/build` | ✅ PASS | 证据脚本 A2（Makefile gate vars + integ DEFAULT_*） |
| 3 | `make test-codegen` 15/15；`make test-elf` 5/5；`make check` EXIT=0 | ✅ PASS | 证据脚本 A3 + reviewer 重跑 |
| 4 | 删 `.dadao/cross-toolchain` 后 `make install-host` 仍 EXIT=0 | ✅ PASS | engineer 完成区记录（证据脚本未含此项，但 `install-host` 依赖 `build-mc`/`build-lld`/`build-qemu` 且从 `.work/` cp，逻辑可重建） |
| 5 | 改名 install 根可执行 → 门控非零；还原回绿 | ✅ PASS | 证据脚本 A5 + reviewer 独立注入（rename `llvm-mc` → rc=2 → 还原 → rc=0） |
| 6 | 一键证据脚本非交互、逐项打印、含注入自检、结尾无 `tee` | ✅ PASS | 脚本审核通过 + 重跑 EXIT=0 |
| 7 | `make check-no-residue` EXIT=0；`git status` 仅本任务改动 | ✅ PASS | reviewer 重跑 residue EXIT=0；`git status` 空 |

---

##### B. 门控来源表（D9 落地完整性）

`make check`（Makefile:297）的全部子门控及其可执行来源：

| 门控名 | 可执行依赖 | 来源 | D9 对齐？ |
|--------|-----------|------|----------|
| manifest-check | `tools/infra/manifest_check.py` | 脚本，无外部可执行 | N/A ✅ |
| validate-vectors | `tools/spec/validate_vectors.py` | 脚本 | N/A ✅ |
| check-spec-drift | `tools/spec/check_spec_drift.py` | 脚本 | N/A ✅ |
| check-patch-tree | `tools/infra/check_patch_tree.sh` | 脚本 | N/A ✅ |
| check-index-blobs | `tools/infra/check_index_blobs.py` | 脚本 | N/A ✅ |
| check-asm-list | `tools/spec/check_asm_list.py` | 脚本 | N/A ✅ |
| check-asm-list-drift | `tools/spec/check_asm_list_drift.py` | 脚本 | N/A ✅ |
| check-asm-prose | `tools/spec/check_asm_prose.py` | 脚本 | N/A ✅ |
| check-spec-codeblocks | `tools/spec/check_spec_codeblocks.py` | 脚本 | N/A ✅ |
| check-legality-drift | `tools/spec/check_legality_drift.py` | 脚本 | N/A ✅ |
| check-legality-invariants | `tools/spec/check_legality_invariants.py` | 脚本 | N/A ✅ |
| check-interface | `tools/integ/check_interface_alignment.py` | 脚本（读 `run_qemu_test.py` 源码做静态分析，不执行 QEMU） | N/A ✅ |
| validate-encoding | `tools/spec/validate_encoding.py` | 脚本 | N/A ✅ |
| check-scope | `tools/spec/check_scope.py` | 脚本 | N/A ✅ |
| check-rule-refs | `tools/spec/check_rule_refs.py` | 脚本 | N/A ✅ |
| check-fp-contract | `tools/spec/check_fp_contract.py` | 脚本 | N/A ✅ |
| check-instrinfo | `tools/spec/check_instrinfo.py` | 脚本 | N/A ✅ |
| **check-qemu-semantics** | **`tests/scripts/run_qemu_test.py` → `DEFAULT_QEMU = ".work/build/qemu/qemu-system-dadao"`** | **`.work/build`（硬编码）** | **❌ 未对齐** |
| check-cfx-aliases | `tools/spec/check_cfx_aliases.py` | 脚本 | N/A ✅ |
| check-dirs | `tools/infra/check_dirs.sh` | 脚本 | N/A ✅ |
| check-no-residue | `tools/infra/check_no_residue.sh` | 脚本 | N/A ✅ |
| check-lit | `$(HOST_TOOLCHAIN_BIN)/llvm-lit` | install 根 | ✅ |
| test-codegen | `$(HOST_TOOLCHAIN_BIN)/{llc,llvm-mc,llvm-objcopy,qemu-system-dadao}` | install 根 | ✅ |
| test-elf | `$(HOST_TOOLCHAIN_BIN)/{llc,llvm-mc,ld.lld,qemu-system-dadao}` | install 根 | ✅ |

**其它被门控引用的脚本**：
- `tests/scripts/verify_harness_dump.py`：**不被任何 Makefile 门控调用**（独立验证脚本，不属 D9 范围）。✅
- `tools/integ/check_interface_alignment.py`：读 `run_qemu_test.py` 源码做静态分析（不执行 QEMU），不属门控可执行路径。✅

**B 节结论**：
- `check-qemu-semantics`（`make check` 子门控）通过 `tests/scripts/run_qemu_test.py` 仍从 `.work/build/qemu/qemu-system-dadao` 取 QEMU 可执行——**未对齐 D9**。
- **但**该脚本不在任务书「门控/执行器」界定范围（Makefile 路径变量 + `tools/integ/run_{codegen,elf}_e2e.py` + `tests/**/lit.cfg.py`）内，且任务书约束明确禁止修改 `tests/scripts/` 下的脚本（"只动任务范围"）。
- engineer 在完成区「遗留问题」中已明确标注并建议另立任务。
- **此为 D9 的已知残余缺口，不在本任务验收范围内，不阻塞本任务判决**；建议架构师另立任务对齐 `check-qemu-semantics`。

---

##### 约束核验

| 约束 | 判定 | 证据 |
|------|------|------|
| 不改组件源码（`components/**`、`.work/source/**`） | ✅ | `git diff --name-only` 仅 6 个文件，无 `components/` |
| 路径一律真实路径（D8），禁硬编码 install 路径（D7） | ✅ | Makefile 用 `$(HOST_TOOLCHAIN_BIN)`，integ 用 `paths.py` |
| 只动任务范围，不改 `tools/qemu/*`、`tools/llvm/test_*.py` | ✅ | `git diff --name-only` 无越界 |
| 不弱化门控 | ✅ | 注入反例证明门控承重（rename `llvm-mc` → rc=2） |
| `Makefile` 为共享文件，与其它任务串行 | ✅ | 仅本任务修改，无并发冲突 |
| 临时目录 `/tmp/opencode/INFRA-047t/` | ✅ | 证据脚本/logs 在 `.work/`，reviewer 用 `/tmp/opencode/INFRA-047t-review/` |
| 不提交 git | ✅ | reviewer 未提交 |
| 还原纪律：禁 `git checkout/restore/stash`，用 `cp`+md5 | ✅ | reviewer 注入用 `cp` 备份 + `md5sum` 对账 |

---

##### 判决：**Accepted**

全部 7 项验收标准通过（reviewer 独立重跑 + 独立注入反例验证）。证据脚本合格（每个断言有可达 FAIL 路径、注入自检非空可还原、结尾无 `tee`）。未弱化门控、未越界。B 节发现 `check-qemu-semantics` 仍从 `.work/build` 取 QEMU（D9 残余缺口），但不在本任务界定范围内，不阻塞判决。

#### 第 1 轮 architect 提交（WIP）
**档位**：`WIP:`（reviewer 尚未验收，任务状态 `待验收`）
**提交号**：`4ab0fd1c5fef735cfae70b261c85311b1ff81222`
**文件集对账**（`git diff --cached --name-only` vs 完成区「修改文件」声明）：
- staged 7 文件 = 声明 7 文件，**逐条一致**（`Makefile`、`tools/integ/run_codegen_e2e.py`、`tools/integ/run_elf_e2e.py`、`tests/llvm/lit/MC/DADAO/lit.cfg.py`、`tests/llvm/lit/CodeGen/DADAO/lit.cfg.py`、`tests/e2e/lit/lit.cfg.py`、`.tao/tasks/infra/INFRA-047t-install落地.md`）
- **漏提**：无；**多提**：无；**越界**：无（`git status --porcelain -uall` 无未跟踪文件，`.work/` 为 gitignored 未入库）
- 显式 staging（逐个路径，未用 `git add -A`）；只 `commit`，未 `push`

#### 第 1 轮 reviewer 验收后范围修正（architect，2026-10-07）

**依据**：`ADR-0016 D9` **原文点名** `run_qemu_test.py`——「**门控/执行器**（**`run_qemu_test.py`**、lit、各 `check_*`）改从 **install 根**取可执行」。原「门控/执行器」界定（`Makefile` 路径变量 + `tools/integ/run_{codegen,elf}_e2e.py` + `tests/**/lit.cfg.py`）与验收 2 的 grep 范围（`Makefile`+`tools/infra`+`tools/integ`，主会话下发前预检 F1 收窄）**均漏掉该脚本**，致 `make check` 子门控 `check-qemu-semantics` 的 QEMU 来源未纳入（reviewer「第 1 轮验收 B 节」已发现，因超范围未阻塞判决）。**本任务内闭合，不另立任务兜底。**

**改动**（仅本任务书；未改 ADR/spec/代码）：
1. 「输出 3」增补：`tests/scripts/run_qemu_test.py` 的 `DEFAULT_QEMU` 改经 `tools/infra/paths.py::host_toolchain_bin()` 解析到 install 根（禁硬编码，保留 env/PATH 兜底、`--qemu` 不动）；`Makefile` 的 `check-qemu-semantics`（L517）调用处传 `--qemu $(QEMU_BIN)`；核实 `tests/scripts/verify_harness_dump.py`（**实测 `grep`：不被任何门控经代码/子进程调用**，保留）。
2. 「验收 2」grep 范围增补 `tests/scripts`；out-of-scope 收窄为 `tools/qemu/*`、`tools/llvm/test_*.py`；`tests/scripts/README.md:68` 文档命中允许保留但须同步描述/说明。
3. 新增「验收 8」：`make check-qemu-semantics` EXIT=0 + 注入反例（改名 install 根 `qemu-system-dadao` ⇒ 非零 ⇒ `cp`+`md5` 还原回绿）。
4. 新增「范围修正说明」节（文件顶部），记录依据与处置。

**状态**：保持 `待验收`（范围修正后须重新验收）。**完成区**「7/7」为**旧范围**结论，须由 engineer 就新增验收 8 补跑并更新本任务书完成区（本次修正**不改写**完成区与既有审阅记录，仅追加本段）。
**提交**：`WIP:`（任务重新打开）——提交号与 `git show --stat` 见 architect 回报（本段不写死自身提交号，避免 amend 造成的悬空引用）。

#### 第 2 轮 engineer 自审

**范围**：逐行审本轮 3 份改动（`tests/scripts/run_qemu_test.py`、`Makefile`、`tests/scripts/README.md`）及其与既有 `find_qemu()`/`--qemu` 的交互；复跑验收 1–8 与证据脚本。

**逻辑正确性**：
- `DEFAULT_QEMU` 由 `.work/build/...` 字符串改为 `str(_paths.host_toolchain_bin() / "qemu-system-dadao")`（绝对、realpath，经 `paths.py` 单一真源，D7 无硬编码）；`paths.py` 导入上移至常量段（`_REPO_ROOT` + `sys.path.insert`），删除原 L61–64 重复导入。实测 `DEFAULT_QEMU = /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin/qemu-system-dadao`。✅
- `find_qemu()` 优先级保持 env `QEMU_SYSTEM_DADAO` → **install 根默认**（直接 `os.path.isfile(DEFAULT_QEMU)`）→ `shutil.which` PATH 兜底；去掉原先 `os.path.join(repo_root, DEFAULT_QEMU)`（对绝对路径虽结果相同但语义误导）。✅
- `--qemu`（L627）与 `args.qemu or find_qemu()` 短路（L655）**未改**：显式 `--qemu` 时不进入 `find_qemu()`。✅
- 边界：install 根 QEMU 缺失且 env/PATH 均无 ⇒ `find_qemu()` 返回 None ⇒ `main` 报错 `sys.exit(1)`（fail-closed，实测注入 rc=2 抛出 `FileNotFoundError`）。✅
- `Makefile`：`check-qemu-semantics`（L518）增传 `--qemu $(QEMU_BIN)`（`QEMU_BIN = $(HOST_TOOLCHAIN_BIN)/qemu-system-dadao`，L397）；注释同步 install 根口径；`.work/build` 变量定义与 build 目标**未动**（D9 build 区）。✅
- `README.md`「QEMU Binary」节改述 install 根/`paths.py`，不再写 `.work/build`。✅

**设计与惯用法**：复用 `paths.py`（不另造路径解析）；不新增依赖、不改签名；与既有 lit.cfg/integ runner 的 install 根口径一致。✅
**防造假**：全部 rc/输出取自真实日志（`cmd > log 2>&1; rc=$?`，无 `tee`）；注入用 `cp`+md5 对账（禁 `git checkout/restore/stash`），还原后无 `.inject-bak` 残留；证据脚本经「注入→FAIL(1)→还原→回绿(0)」自证可失败。✅

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 上轮延后项：`run_qemu_test.py` 未对齐 install 根 | ✅已修 | `DEFAULT_QEMU` 改经 `paths.py::host_toolchain_bin()`；`Makefile` 增 `--qemu`；README 同步 | 证据脚本 A2b `under install root` match；验收8 注入承重（INJECT_RC=2→RESTORE_RC=0） |
| `verify_harness_dump.py:43` 仍含 `.work/build` | ❌不修 | 无（实测非门控/执行器，任务书明确 out-of-scope） | `grep -rn "verify_harness_dump"` 全仓仅命中其自身 docstring |
| `tests/scripts/README.md:68` 文档命中 `.work/build` | ✅已修 | 「QEMU Binary」节改指 install 根/`paths.py` | 验收2 grep：`tests/scripts` 下 README 命中清零 |

**判决**：本轮 finding 全部处置（1 ✅已修 / 1 ❌不修〔非缺陷〕/ 1 ✅已修）⇒ 状态 `待验收` 成立。

#### 第 2 轮 architect 提交（WIP）

**档位**：**`WIP:`**——reviewer 尚未复验（engineer 第 2 轮补修后状态 `待验收`），非验收完成，故按 WIP 档提交。
**文件集审核**（显式 staging，禁 `git add -A`）：`git diff --cached --name-only` = `Makefile`、`tests/scripts/README.md`、`tests/scripts/run_qemu_test.py`、`.tao/tasks/infra/INFRA-047t-install落地.md`，共 4 份；与「修改文件」第 2 轮声明**逐条一致**，**无漏提、无多提、无越界**（`.work/**` gitignored，不入库）。提交前 `git status --porcelain -uall` 无本任务别的未暂存残留。
**提交**：仅 `commit`，**未 `push`**（push 由主会话在 `/complete` 收尾后执行）。提交号与 `git show --stat` 见 architect 回报（本段不写死自身提交号，避免悬空引用）。

#### 第 2 轮 reviewer 验收

（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**〔改 install 根 `qemu-system-dadao` 名〕+ 验收 1–8 逐条核验 + 判决）

**审查者**：mimo-v2.5-pro（reviewer subagent）
**审查时间**：2026-10-07

---

##### A. 证据脚本审核（第 2 轮新增断言：A2b / A8 / A8b）

逐条核对新断言的 FAIL 路径：

| 行 | 断言 | FAIL 路径 | 恒真？ |
|---|---|---|---|
| 98–110 | A2b: `DEFAULT_QEMU` 落在 install 根 | `$dq` 不以 `$BIN/` 开头 → case `*` 分支 → `"no-match"≠"match"` → FAIL | 否 ✅ |
| 111–115 | A2b: `DEFAULT_QEMU` 无 `.work/build` | grep 有匹配 → `"match"≠"no-match"` → FAIL | 否 ✅ |
| 116–122 | A2b: Makefile 传 `--qemu` | grep 无匹配 → `$sem_gate` 空 → `"match"≠"no-match"` → FAIL | 否 ✅ |
| 148–151 | A8: `make check-qemu-semantics` rc=0 | rc≠0 → `"$rc"≠"0"` → FAIL | 否 ✅ |
| 192 | A8b: 注入后 `check-qemu-semantics` 非零 | rc=0 → `"non-zero"≠"unexpected-pass(0)"` → FAIL | 否 ✅ |
| 203 | A8b: qemu md5 还原一致 | md5 不等 → `$?≠0` → FAIL | 否 ✅ |
| 204 | A8b: 还原后 `check-qemu-semantics` rc=0 | rc≠0 → FAIL | 否 ✅ |

**A2b 实现细节**：用 `exec()` 在子进程中执行 `run_qemu_test.py` 模块体，提取 `DEFAULT_QEMU` 常量值。若 `paths.py` 或 manifest 缺失，子进程会抛异常/exit 非零，`$dq` 为空 → case `*` → FAIL。**非恒真** ✅

**A8b 注入自检**：行 187–206，rename `qemu-system-dadao` → run `check-qemu-semantics` → expect FAIL → mv back → md5 比对 → run `check-qemu-semantics` expect PASS。**非空且可还原** ✅

**结尾**：行 211–214，`"$fail" -ne 0` → `exit 1` / `exit 0`，无 `tee`。✅

**脚本质量**：合格，无需打回。

---

##### B. 重跑证据脚本（真实输出）

```
$ bash .work/evidence/INFRA-047t/run.sh > /tmp/opencode/INFRA-047t-review2/evidence-run.log 2>&1; echo "EVIDENCE_EXIT=$?"
EVIDENCE_EXIT=0
```

完整输出（`/tmp/opencode/INFRA-047t-review2/evidence-run.log`）：

```
=== INFRA-047t evidence ===
REPO_ROOT = /mnt/tao/DADAO-v5
HOST_TOOLCHAIN_BIN = /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin
TARGET_SYSROOT_DIR = /mnt/tao/DADAO-v5/.dadao/dadao-unknown-elf

--- A1: installed host tool set ---
PASS  tool:llvm-mc --version                         expected=0 actual=0
PASS  tool:llvm-objdump --version                    expected=0 actual=0
PASS  tool:llvm-readobj --version                    expected=0 actual=0
PASS  tool:FileCheck --version                       expected=0 actual=0
PASS  tool:llc --version                             expected=0 actual=0
PASS  tool:ld.lld --version                          expected=0 actual=0
PASS  tool:llvm-lit --version                        expected=0 actual=0
PASS  tool:qemu-system-dadao --version               expected=0 actual=0
PASS  tool:not /bin/false (inverts)                  expected=0 actual=0
PASS  tool:not /bin/true (inverts)                   expected=1 actual=1
--- A1b: target sysroot skeleton ---
PASS  sysroot ./include exists                       expected=0 actual=0
PASS  sysroot ./lib exists                           expected=0 actual=0
PASS  sysroot ./README.md exists                     expected=0 actual=0
--- A2: gate paths resolve to the install root ---
PASS  Makefile gate vars free of .work/build         expected=no-match actual=no-match
PASS  integ DEFAULT_* free of .work/build            expected=no-match actual=no-match
PASS  integ DEFAULT_* use paths.py toolchain bin     expected=match actual=match
run_qemu_test.py DEFAULT_QEMU = /mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin/qemu-system-dadao
PASS  run_qemu_test DEFAULT_QEMU under install root  expected=match actual=match
PASS  run_qemu_test DEFAULT_QEMU free of .work/build expected=no-match actual=no-match
PASS  Makefile check-qemu-semantics passes --qemu    expected=match actual=match
--- A3: gates ---
PASS  make check-lit                                 expected=0 actual=0  (Passed: 60, 100.00%)
PASS  make test-codegen                              expected=0 actual=0  (Results: 15/15 passed, 0 failed)
PASS  make test-elf                                  expected=0 actual=0  (Results: 5/5 passed, 0 failed)
PASS  make check                                     expected=0 actual=0  (repository checks: PASS)
--- A8: check-qemu-semantics gate ---
PASS  make check-qemu-semantics                      expected=0 actual=0  (check-qemu-semantics: PASS, 149/149)
--- A7: residue gate ---
PASS  make check-no-residue                          expected=0 actual=0
--- A5: injection self-test (rename install-root llvm-mc) ---
PASS  injected check-lit is non-zero                 expected=non-zero actual=non-zero
PASS  llvm-mc restored (md5 match)                   expected=0 actual=0
PASS  restored check-lit is green                    expected=0 actual=0
--- A8b: injection self-test (rename install-root qemu-system-dadao) ---
PASS  injected check-qemu-semantics is non-zero      expected=non-zero actual=non-zero
PASS  qemu-system-dadao restored (md5 match)         expected=0 actual=0
PASS  restored check-qemu-semantics is green         expected=0 actual=0

=== summary: 31 passed, 0 failed ===
```

**EVIDENCE_EXIT=0**，**31/31 PASS**。与 engineer 完成区声称一致。

---

##### C. 独立注入反例（reviewer 自行执行，不由 engineer 自检替代）

**注入目标**：rename install 根 `qemu-system-dadao`（`check-qemu-semantics` 依赖）。

**鉴别力前提**：build 树 `.work/build/qemu/qemu-system-dadao` **仍然存在**（`34813120` 字节）。若门控仍从 build 树取 QEMU，改名 install 根**不会**致 FAIL——这是区分"门控已改根"与"假改根"的关键。

**注入前快照**：
```
$ md5sum .dadao/cross-toolchain/bin/qemu-system-dadao
38e16e3daf60fc50efe4692d0fbcc177  .dadao/cross-toolchain/bin/qemu-system-dadao

$ cp -a .dadao/cross-toolchain/bin/qemu-system-dadao /tmp/opencode/INFRA-047t-review2/qemu-system-dadao.preinject
$ md5sum /tmp/opencode/INFRA-047t-review2/qemu-system-dadao.preinject
38e16e3daf60fc50efe4692d0fbcc177  /tmp/opencode/INFRA-047t-review2/qemu-system-dadao.preinject
```

**注入（改名）**：
```
$ mv .dadao/cross-toolchain/bin/qemu-system-dadao .dadao/cross-toolchain/bin/qemu-system-dadao.inject-bak
$ ls .dadao/cross-toolchain/bin/qemu-system-dadao
ls: cannot access '.dadao/cross-toolchain/bin/qemu-system-dadao': No such file or directory
```

**确认 build 树 QEMU 仍在**：
```
$ ls -la .work/build/qemu/qemu-system-dadao
-rwxrwxr-x 1 ubuntu ubuntu 34813120 Oct  6 20:04 .work/build/qemu/qemu-system-dadao
```

**注入后门控**：
```
$ make check-qemu-semantics > inject-check-qemu.log 2>&1; echo "INJECT_RC=$?"
INJECT_RC=2

$ tail -5 inject-check-qemu.log
FileNotFoundError: [Errno 2] No such file or directory: '/mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin/qemu-system-dadao'
check-qemu-semantics: FAIL (rc=1)
make: *** [Makefile:509: check-qemu-semantics] Error 1
```

**→ 门控承重确认：rc=2，报错指向 install 根路径（非 `.work/build`）——证明门控确从 install 根取 QEMU。**

**还原**：
```
$ mv .dadao/cross-toolchain/bin/qemu-system-dadao.inject-bak .dadao/cross-toolchain/bin/qemu-system-dadao
$ md5sum .dadao/cross-toolchain/bin/qemu-system-dadao
38e16e3daf60fc50efe4692d0fbcc177  .dadao/cross-toolchain/bin/qemu-system-dadao
$ md5sum /tmp/opencode/INFRA-047t-review2/qemu-system-dadao.preinject
38e16e3daf60fc50efe4692d0fbcc177  /tmp/opencode/INFRA-047t-review2/qemu-system-dadao.preinject
→ md5 一致 ✅
```

**还原后门控**：
```
$ make check-qemu-semantics > restore-check-qemu.log 2>&1; echo "RESTORE_RC=$?"
RESTORE_RC=0

$ grep -E 'Results:|check-qemu-semantics:' restore-check-qemu.log
Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors
check-qemu-semantics: PASS
```

**→ 回绿确认：149/149，rc=0。**

**还原纪律**：未使用 `git checkout`/`git restore`/`git stash`；用 `cp` 备份 + `md5sum` 对账。注入前后 `git status --porcelain -uall` 均为空（`.dadao/` 为 gitignored）。无 `.inject-bak` 残留。

---

##### D. 验收标准逐条核验

| # | 验收标准 | reviewer 判定 | 证据 |
|---|---------|-------------|------|
| 1 | `make install-host` EXIT=0；11 个 bin 工具可运行；sysroot 骨架存在；`make check-lit` 60/60 | ✅ PASS | 证据脚本 A1/A1b/A3 + reviewer 重跑 EXIT=0 |
| 2 | `grep -rn "\.work/build" Makefile tools/infra tools/integ tests/scripts` 门控/执行器无 `.work/build` | ✅ PASS | 证据脚本 A2/A2b（gate vars + integ DEFAULT_* + run_qemu_test DEFAULT_QEMU）；reviewer 独立 grep 确认剩余命中仅 build 区变量/注释/非门控文件 |
| 3 | `make test-codegen` 15/15；`make test-elf` 5/5；`make check` EXIT=0（含 `check-qemu-semantics`） | ✅ PASS | 证据脚本 A3 + A8 + reviewer 重跑；`make check` 包含 `check-qemu-semantics`（Makefile L297） |
| 4 | 删 `.dadao/cross-toolchain` 后 `make install-host` 仍 EXIT=0 | ✅ PASS | engineer 完成区记录（`install-host` 从 `.work/` 构建树 cp，逻辑可重建） |
| 5 | 改名 install 根可执行 → 门控非零；还原回绿 | ✅ PASS | 证据脚本 A5 + reviewer 第 1 轮独立注入（rename `llvm-mc` → rc=2 → 还原 → rc=0） |
| 6 | 一键证据脚本非交互、逐项打印、含注入自检、结尾无 `tee` | ✅ PASS | 脚本审核通过 + 重跑 EXIT=0（31/31） |
| 7 | `make check-no-residue` EXIT=0；`git status` 仅本任务改动 | ✅ PASS | reviewer 重跑 residue EXIT=0；`git status` 空（WIP 已提交） |
| **8** | **`check-qemu-semantics` 改根 + 假绿守卫**：`make check-qemu-semantics` EXIT=0；注入改名 install 根 `qemu-system-dadao` ⇒ 非零（鉴别力：build 树 QEMU 仍在，若门控用 build 树则仍绿）；还原回绿 | ✅ PASS | 证据脚本 A8/A8b + **reviewer 独立注入**（INJECT_RC=2，报错指向 install 根路径，非 `.work/build`；RESTORE_RC=0，149/149） |

---

##### E. `run_qemu_test.py` 改动复核

- `DEFAULT_QEMU`（L39）：由 `.work/build/...` 字符串改为 `str(_paths.host_toolchain_bin() / "qemu-system-dadao")`，经 `paths.py` 单一真源解析，D7 无硬编码。✅
- `find_qemu()`（L76–93）：优先级 env `QEMU_SYSTEM_DADAO` → install 根默认（`os.path.isfile(DEFAULT_QEMU)`）→ `shutil.which` PATH 兜底。未改动。✅
- `--qemu`（L627）：`default=None`；L655 `args.qemu or find_qemu()` 短路——显式 `--qemu` 时不进入 `find_qemu()`。未改动。✅
- Makefile L518：`--qemu $(QEMU_BIN)`（`QEMU_BIN = $(HOST_TOOLCHAIN_BIN)/qemu-system-dadao` L397）。✅
- 路径一致性：`Makefile` 传 `--qemu` 指向 install 根，`run_qemu_test.py` 的 `DEFAULT_QEMU` 也指向 install 根，两者一致。✅

---

##### F. 约束核验

| 约束 | 判定 | 证据 |
|------|------|------|
| 不改组件源码（`components/**`、`.work/source/**`） | ✅ | `git show --stat c9d0aee` 仅 4 文件，无 `components/` |
| 路径一律真实路径（D8），禁硬编码 install 路径（D7） | ✅ | `run_qemu_test.py` 用 `paths.py::host_toolchain_bin()`；Makefile 用 `$(HOST_TOOLCHAIN_BIN)` |
| 只动任务范围：`tests/scripts/run_qemu_test.py`、`tests/scripts/README.md`、`Makefile`、任务书 | ✅ | `git show --stat c9d0aee` 精确 4 文件；`tools/qemu/*`、`tools/llvm/test_*.py`、`tests/scripts/verify_harness_dump.py` 未动 |
| 不弱化门控 | ✅ | 独立注入反例证明 `check-qemu-semantics` 承重（rename install 根 QEMU → rc=2，报错指向 install 根，非 build 树） |
| `Makefile` 为共享文件，与其它任务串行 | ✅ | 仅本任务修改 |
| 临时目录 `/tmp/opencode/INFRA-047t-review2/` | ✅ | reviewer 注入/日志均在该目录 |
| 不提交 git | ✅ | reviewer 未提交 |
| 还原纪律：禁 `git checkout/restore/stash`，用 `cp`+md5 | ✅ | reviewer 注入用 `cp` 备份 + `md5sum` 对账；无 `.inject-bak` 残留 |

---

##### 判决：**Accepted**

全部 8 项验收标准通过（reviewer 独立重跑 31/31 PASS + 独立注入反例验证 `check-qemu-semantics` 确从 install 根取 QEMU）。证据脚本合格（每个断言有可达 FAIL 路径、A5+A8b 双注入自检非空可还原、结尾无 `tee`）。未弱化门控、未越界。本轮闭合了第 1 轮遗留的 D9 缺口（`check-qemu-semantics` 改根），上轮 B 节 `check-qemu-semantics` 未对齐问题已消除。

#### 第 2 轮 architect 提交（正常）

**档位**：**正常提交**（非 `WIP:`）——reviewer 第 2 轮判决 **Accepted**（第 2 轮 reviewer 复审记录见上），验收完成。
**文件集审核**（显式 staging，禁 `git add -A`）：`git diff --cached --name-only` = `.tao/tasks/infra/INFRA-047t-install落地.md`，共 1 份（本轮工作树仅 reviewer 复审记录追加；实现类文件 `Makefile`、`tests/scripts/README.md`、`tests/scripts/run_qemu_test.py` 已在前序 WIP 提交 `c9d0aee` 入库）；与本次提交范围**一致**，**无漏提、无多提、无越界**。提交前 `git status --porcelain -uall` 无本任务别的未暂存/未跟踪残留。
**提交**：仅 `commit`，**未 `push`**（push 由主会话在 `/complete` 收尾、将本任务本地提交 squash/amend 为单一「已验证」提交后执行）。提交号与 `git show --stat` 见 architect 回报（本段不写死自身提交号，避免悬空引用）。

#### 主会话统一验收报告（`/complete`，2026-10-07）

- **reviewer**：第 1 轮 `Accepted` →（主会话下发前预检发现「D9 范围收窄漏项」⇒ 任务重开）→ 第 2 轮 `Accepted`。独立注入（改名 install 根 `qemu-system-dadao`）⇒ `make check-qemu-semantics` **INJECT_RC=2**（报错路径指向 `…/cross-toolchain/bin/qemu-system-dadao`，非 `.work/build`）⇒ `md5` 还原（`38e16e3daf60fc50efe4692d0fbcc177`）⇒ 回绿 **149/149**。
- **architect 交叉复核**：**确认 `Accepted`**（无阻塞性补充发现）。独立列出 `make check` **全部 22 个门控**的可执行来源，**无第二个门控取 `.work/build`**；`run_qemu_test.py` 的 `env → install 根 → PATH` 优先级与 `--qemu` 短路未被破坏；`Makefile` 的 `check-qemu-semantics` 已传 `--qemu $(QEMU_BIN)`。
- **共识**：`ADR-0016 D9` 点名项（**`run_qemu_test.py`**、lit、**各 `check_*`**）已改从 **install 根**取可执行；门控未弱化（**两轮注入均证承重**）；未越界（提交文件集无 `components/**`、无 `tools/qemu/*`、无 `tools/llvm/test_*.py`）。
- **分歧/补充（低严重度、非阻塞，不改变判决）**：① `tests/scripts/verify_harness_dump.py` 仍硬编码 `.work/build`——经调用链反证为**非门控** ⇒ out-of-scope，但违反 `ADR-0016` 后果条「新增脚本禁硬编码路径」⇒ **建议另立任务**对齐；② reviewer 门控来源表 2 处命名笔误（`check_patch_tree.py`、`check_asm_list_consistency.py`）；③ `check-interface` **确会** subprocess 调两个静态 lint 子脚本（二者不取 `.work/build`，对 D9 无影响）。
- **收尾检查**：门控全绿（reviewer 第 2 轮重跑：`make check` **EXIT=0**、`check-qemu-semantics` **149/149**、`check-lit` **60/60**、`test-codegen` **15/15**、`test-elf` **5/5**、`check-no-residue` **EXIT=0**）；证据留非易失位置 `.work/evidence/INFRA-047t/`、`.work/log/infra/`；`git status --untracked-files=all` 无临时残留。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
