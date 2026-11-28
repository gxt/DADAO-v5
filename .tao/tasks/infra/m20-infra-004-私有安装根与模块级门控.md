# m20-infra-004: 私有安装根 + 模块级门控（`check-module COMPONENT=<c>`）

**模块**：infra
**项目里程碑**：M20
**依赖**：`m20-infra-003`（`DADAO_SOURCE_ROOT`/`private_source.sh` 私有源树已落地；本任务在其上叠加**私有安装根**与**模块级门控**）
**可并行分片**：否（动 `Makefile`/`tools/infra/paths.py`/新增门控脚本，全局串行；与 `m20-infra-005` 都动 `Makefile` ⇒ **串行，本任务 004 先**）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：待开始

## 背景（用户 2026-11-28 裁定三件：接受私有安装根 / 模块级门控按组件分 / 私有目录清理只报警）

现状（落地前可复验，事实非推测）：

- `tools/infra/paths.py` 把 `sdk_dir/host_toolchain_dir/host_tools_dir/target_sysroot_dir/test_artifacts_dir` 全部从 `manifests/install-dirs.lock.toml` 解析为 `<repo>/<相对路径>`，**无任何环境变量覆盖入口**（`_resolve(_load_manifest()[key])`，无 `os.environ`）。
- `Makefile` 顶部 `HOST_TOOLCHAIN_DIR := $(shell python paths.py host_toolchain_dir)` 等 7 个变量（含 `HOST_TOOLCHAIN_BIN/HOST_TOOLS_BIN/TARGET_SYSROOT_DIR/TEST_ARTIFACTS_DIR`）**不可覆盖**；`LLVM_BUILD/QEMU_BUILD/GEM5_BUILD` 是 `?=`（可覆盖），`DADAO_SOURCE_ROOT ?= .work/source`（可覆盖，m20-infra-003）。
- `install-host` 在 `GATE_LOCKED_TARGETS` 里（`_locked-install-host: install-cfx-aliases build-mc build-lld build-qemu build-builtins`），**只装共享根** `.dadao/{cross-toolchain,host-tools,dadao-unknown-elf,tests}`。
- 工具路径是**单绝对路径**：`$(LLVM_MC_BIN)=$(HOST_TOOLCHAIN_BIN)/llvm-mc`、`$(QEMU_BIN)=$(HOST_TOOLCHAIN_BIN)/qemu-system-dadao`、`$(HOST_TOOLS_BIN)/lli`、`$(HOST_LIT_DIR)=$(HOST_TOOLCHAIN_DIR)/share/lit` 等，全部从安装根派生。
- 后果：任务只覆盖 `LLVM_BUILD/QEMU_BUILD/DADAO_SOURCE_ROOT` 时，`check-inst-asm`/`check-idl`/`check-lit`/`test-codegen` 仍读**共享安装根里的旧二进制**（`check-inst-asm` 用 `llvm-mc`+`qemu-system-dadao`；`check-idl` 用 `$(QEMU_BIN)`；`test-codegen` 用 llc→llvm-mc→objcopy→qemu）。

用户口径：**模块级测试用该模块的私有构建树 + 私有安装根**；全局测试（`check-modules`/`check-full`/`night-run`）仍用共享安装根，且只在合并后的 master 上跑。

## 目标（分条，可验收）

1. **安装根 env 覆盖**：`paths.py` 支持单一 env `DADAO_INSTALL_ROOT` 覆盖整个安装根（`sdk_dir` 基）；默认值不变、默认命令行/输出**逐字节不变**（`make -n` 与 `paths.py --make` 各键 diff 空）；`DADAO_INSTALL_ROOT` 为**非法（空/纯空白/非绝对/不存在且不可建）值显式报错**（rc≠0 + 指名原因，不静默回落共享根）。
2. **私有安装目标** `install-host-private COMPONENT=<c> TASK_ID=<id>`（名自定，此为目标名）：把指定组件产物装进 `.work/private/<id>/install`；**不拿共享 gate lock**（不写共享构建树/安装根）；对共享根有写守卫（照 m20-infra-003 token 风格：目标解析到共享根且 token 空 ⇒ 拒绝 rc=2，非空 token 放行）；其余组件产物从共享根**继承**。
   - **继承方案（定死一种）= symlink 镜像**：私有安装根构造为**完整镜像**——共享根里本任务**未拥有**的组件产物路径用 `ln -s` 指回共享根，**拥有**的组件产物真实写入覆盖同名 symlink。选 symlink 而非「PATH 顺序」的理由：既有消费者全是 `$(HOST_TOOLCHAIN_BIN)/llvm-mc` 这类**单绝对路径**（非 PATH 查找），symlink 镜像无需改动任何消费者；PATH 顺序需把所有 `*_BIN` 解析改成「私有优先、共享回退」的查找包装，侵入面大得多。
   - 组件产物覆盖口径（写清依据）：`llvm` → clang/llc/llvm-mc/llvm-objcopy/llvm-nm/lld/lli + lit + clang builtin headers + compiler-rt builtins + cfx-aliases（= 现 `install-host` 里来自 `LLVM_BUILD` 的全部）；`qemu` → qemu-system-dadao/qemu-dadao。`tests/`（测试产物）与 `writers/`（写者状态）**不继承、在私有根下为私有新目录**——门控跑出来的产物不得写共享根。
3. **模块级门控** `check-module COMPONENT=<c> TASK_ID=<id>`：解析私有源（`.work/private/<id>/source/<c>`）、私有构建（`LLVM_BUILD/QEMU_BUILD/GEM5_BUILD` 覆盖到私有）、私有安装根（`DADAO_INSTALL_ROOT=.work/private/<id>/install`），按「组件 → 门控」映射跑该组件的模块级门控。映射必须是**数据**（`tools/infra/module_gates.toml`），并加校验：映射里每个 target 必须真实存在于 Makefile（解析 `.PHONY`/目标定义，防写错名；缺失 ⇒ rc=2 fail-closed）。
4. **映射最小集**（按组件，写清依据）：
   - `llvm` → `check-lit`（L2，MC+CodeGen+E2E，读安装根 llvm-mc/llc/objcopy）、`test-codegen`（M3 CodeGen E2E，llc→llvm-mc→objcopy→qemu）、`check-instrinfo`（L1，`DADAOInstrInfo*.td`↔`opcodes.yaml`）、`check-cfx-alias-table`（L1，`contracts/cfx-aliases.txt`==spec 投影）——四者均真实存在；
   - `qemu` → `check-inst-asm`（L2，inst `.S` 全量、单平台 QEMU，用 llvm-mc+qemu）、`check-idl`（L2，IDL+QEMU 两方，用 `$(QEMU_BIN)`）；
   - `gem5` → `check-gem5-decode`（GEM5-004t，264 行 decode 断言）、`check-wuming-cycles`（m16-gem5-002，周期表重解析）、`check-tiny-hmon`（m19-gem5-003，FS profile 单例）。**check-idl-full 的 gem5 腿**不进映射数据：`check-idl-full` 是四方整体目标（`--platforms qemu,gem5,chipyard`），无独立 per-platform 目标、且为 nightly 小时级 ⇒ 定为**按需单独调**（`idl_four_way.py --platforms gem5`），在任务书此段说明即可，不进 `module_gates.toml`；
   - `chipyard` → 同 gem5 口径（单例缺 ⇒ 按需 `idl_four_way.py --platforms chipyard`；映射里可空，说明见上）。
   - 全局 `check-modules`/`check-full` **成员不动**。
5. **防呆**：`check-module` 必须打印实际解析到的 `llvm-mc`/`qemu-system-dadao` 路径与 md5，并**断言二者位于私有根**（`realpath` 前缀 == `DADAO_INSTALL_ROOT`）；共享安装根在任务前后 md5 不变（脚本化对账，不能只看 `git status`）。
6. **范围红线**：不改 `spec/`/契约/测试向量语义；不改 `check-modules`/`check-full` 的成员；不改变默认 `make check` 行为。

## 验收（逐条贴真实 rc）

1. **闭环**：`TASK_ID=selftest` 建私有树（llvm 或 qemu 选一）→ `install-host-private` 装私有根 → `check-module COMPONENT=<c>` 跑通并打印私有 `llvm-mc`/`qemu-system-dadao` 路径 + md5；断言二者在私有根内；共享根 md5 前后相同（脚本化 diff）。
2. **默认不回归**：再跑一次默认 `make check` 证明默认行为不变（`make -n`/`paths.py --make` 与改前逐字节相同，给 `diff`）。
3. **注入→FAIL→还原→回绿**（证据脚本「运行期证据目录 `run.sh`」）：如把 `DADAO_INSTALL_ROOT` 指回共享根 ⇒ 断言「私有路径」FAIL；`cp`+md5 还原后回绿。每条断言有可达 FAIL。
4. **映射校验可失败**：在 `module_gates.toml` 注入一个不存在的 target ⇒ 校验 rc=2；还原后回绿。
5. **守卫可失败**：`install-host-private` 在解析到共享根且无 token 时 rc=2；设 token 放行（配对测试在一次性 sandbox 跑放行分支，真共享根只跑拒绝分支，同 m20-infra-003 F1）。
6. `check-knowledge-refs`/`check-manifests-guard`/`check-tests-index`/`check-writer-guards`/`check-temp-dirs`/`check-dirs` 不因本任务新增红（基线同红除外，逐行 diff 判据）。

## 约束

独立 `git worktree`；不提交 git；只改 `tools/infra/paths.py`、`Makefile`（最小接线：`DADAO_INSTALL_ROOT` 接线 + `install-host-private`/`check-module`/`check-module-gates` 目标 + 帮助文本）、新增 `tools/infra/module_gates.toml` 与（如需）`tools/infra/install_host_private.py`/`check_module.py` 与本任务书；**不改门控判据语义**（各门控红绿结论不变）；不改 `spec/`/契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
