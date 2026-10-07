# INFRA-047t: install 落地（`.dadao/` 安装根 + 门控/执行器改从 install 根取可执行）

**模块**：infra
**项目里程碑**：M5
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **背景（现状实测，务必以 `grep`/`ls` 为准）**：
  - **定位机制（`ADR-0016 D7/D8`）已由 `INFRA-019t`（M2）建立**：`manifests/install-dirs.lock.toml`（单一真源，含 `sdk_dir=".dadao"`、`host_toolchain_dir=".dadao/cross-toolchain"`、`target_sysroot_dir=".dadao/dadao-unknown-elf"`、`test_artifacts_dir=".dadao/tests"`）+ `tools/infra/paths.py`（解析模块；`--make` 供 Makefile 消费）。
  - **未落地部分（本任务）**：**没有 install 动作**——`Makefile` 的 `build-mc`/`build-lld`/`build-qemu` 只产 `.work/build/{llvm,qemu}` 内可执行；门控/执行器（`check-lit` 的 `LIT_BIN`、`test-codegen`/`test-elf` 的 `LLC_BIN`/`LLVM_MC_BIN`/`LLVM_OBJCOPY_BIN`/`LLD_BIN`/`QEMU_BIN`）**就地**从 `.work/build` 取；`.dadao/` 下**只有** `tests/`（见 `ls -la .dadao/`），**无** `cross-toolchain/`、`dadao-unknown-elf/`。
- **输入**：
  - `.tao/adr/adr-0016-dadao-install-layout.md`（**Accepted**，D1–D11；用户 2026-10-02 逐条确认）。
  - `manifests/install-dirs.lock.toml`、`tools/infra/paths.py`（现状，勿重复造）；`Makefile`（`build-*` 目标、路径变量段）。
  - `.tao/knowledge/milestones.md`「M5 起步待办」（用户 2026-10-06）：落地 `D1–D11`——host 工具链 → `.dadao/cross-toolchain`（D3/D4/D11）、target sysroot → `.dadao/dadao-unknown-elf`（D5）、`manifests/` 单一真源定位（D7，禁硬编码）、**门控/执行器改从 install 根取可执行**、`.work/` **仅**作 build 区（D9）；保留「从源码可重建」。
- **输出**：
  1. `Makefile` 新增 **install 目标**（命名建议 `install-host`，可被 `make check` 之外的流程调用）：把所需 host 工具集从构建树汇入 `$(HOST_TOOLCHAIN_DIR)`（`bin/`）。**按 `D11`「只装所需工具集」**——至少 `llvm-mc`/`llvm-objdump`/`llvm-readobj`/`FileCheck`/`not`/`llc`/`ld.lld` + `qemu-system-dadao`（以 `build-mc`/`build-lld`/`build-qemu` 现存目标集为准）；**不得**全量 `cmake --install`。
  2. `$(TARGET_SYSROOT_DIR)`（`.dadao/dadao-unknown-elf/{include,lib}`）按 `D5` 建立（当前无 header/lib 消费者，建空骨架 + README 指针即可，**不得**臆造内容）。
  3. **门控/执行器改从 install 根取可执行**（`D9`）：`Makefile`（`LIT_BIN`/`LLC_BIN`/`LLVM_MC_BIN`/`LLVM_OBJCOPY_BIN`/`LLD_BIN`/`QEMU_BIN` 等）**改为经 `$(HOST_TOOLCHAIN_BIN)` 解析**（或经 `tools/infra/paths.py`）；lit 的 `lit.cfg.py` 工具替换、`tools/integ/run_{codegen,elf}_e2e.py` 默认工具路径如硬编码 `.work/build` 亦一并对齐（**逐个 grep 核实，不臆测**）。
  4. 构建目标保持**可从源码重建**：`install-host` 依赖 `build-mc`/`build-lld`/`build-qemu`；`.work/` 仍为唯一构建真源（install 只是缓存，`D9`）。
- **约束（硬）**：
  - **不改组件源码**（`components/**`、`.work/source/**` 不碰）；本任务**不涉补丁导出**。
  - **路径一律真实路径**（`D8`，`paths.py` 已实现）；`Makefile`/脚本**禁硬编码** install 路径（`D7`）。
  - **不得弱化任何门控**；改路径后须以**注入反例**证明门控仍承重（把 install 根某可执行临时改名 ⇒ 依赖它的门控**非零退出** ⇒ 还原回绿）——防「门控改路径后假绿」。
  - `Makefile` 为共享文件，与其它改 `Makefile` 的任务（`INFRA-048t` 等）**串行**。
  - 失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/INFRA-047t/`；**不提交 git**（architect 统一提交）；复杂命令输出留存 `.work/log/infra/`（`cmd > log 2>&1; rc=$?`，**禁 `tee`**）。
  - **重建成本申报**：`install-host` 首次需先 `build-mc`（增量，视现状）、`build-lld`（触发 cmake 重配，数分钟）、`build-qemu`（**5–20 分钟**）；开工前在回复中写明预计耗时。

## 验收标准

1. **install 落地**：`make install-host` EXIT=0；`ls -l $(HOST_TOOLCHAIN_BIN)/` 含 `llvm-mc`/`llvm-objdump`/`FileCheck`/`not`/`llc`/`ld.lld`/`qemu-system-dadao`（逐个 `--version`/`-h` EXIT=0，给真实输出）；`$(TARGET_SYSROOT_DIR)` 存在（`include/`、`lib/`）。
2. **门控改根**：`grep -rn "\.work/build" Makefile tools/ | grep -v __pycache__` 显示门控/执行器可执行**不再**取自 `.work/build`（改经 install 根/`paths.py`）；给真实 `grep` 输出。
3. **不回归**：`make test-codegen` 15/15 EXIT=0；`make test-elf` 5/5 EXIT=0；`make check` EXIT=0（含 `check-lit`）；给真实输出。
4. **可重建**：删 `.dadao/cross-toolchain` 后 `make install-host` 仍 EXIT=0（从 `.work/` 构建树重建），给真实输出。
5. **假绿守卫（反例门控）**：临时重命名 install 根某可执行（如 `llvm-mc`）⇒ 依赖它的门控（`test-elf` 或 `check-lit`）**非零退出**；还原后回绿。给真实「改名→FAIL→还原→回绿」输出；**还原用 `cp`+`md5` 对账，禁用 `git checkout`/`git restore`/`git stash`**。
6. **一键证据脚本**：`.work/evidence/INFRA-047t/run.sh`——非交互；任一检查失败即非零退出；逐项打印「检查名 + 期望/实际 + rc」；内置「注入→FAIL→还原→回绿」自检；结尾**禁 `tee`**（用 `rc=$?`）。
7. **无残留**：`make check-no-residue` EXIT=0；`git status --untracked-files=all` 仅本任务应有改动（`Makefile` + 相关脚本 + 本任务书）；`.dadao/` 为 gitignored（不入库）。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**〔改 install 根可执行名/删 install 根目录〕+ 约束核验 + 判决）
