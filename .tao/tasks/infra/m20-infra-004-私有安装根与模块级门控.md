# m20-infra-004: 私有安装根 + 模块级门控（`check-module COMPONENT=<c>`）

**模块**：infra
**项目里程碑**：M20
**依赖**：`m20-infra-003`（`DADAO_SOURCE_ROOT`/`private_source.sh` 私有源树已落地；本任务在其上叠加**私有安装根**与**模块级门控**）
**可并行分片**：否（动 `Makefile`/`tools/infra/paths.py`/新增门控脚本，全局串行；与 `m20-infra-005` 都动 `Makefile` ⇒ **串行，本任务 004 先**）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

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

## 完成区

**测试结果**：运行期证据目录内 `run.sh` **42/42 PASS**（含 4 类可达 FAIL 注入：非法规格、映射错 target、共享根写入、共享安装根注入）。私有 qemu 模块跑 `check-inst-asm` 266/274、`check-idl` 265/274，两门控失败集与共享根基线 **逐行 diff 为空**（8 个 `stm.*` SIGINT + `cfx2rd_crrr_cfx`，均为基线红）；私有 llvm 跑 3/4 绿（test-codegen/check-instrinfo/check-cfx-alias-table rc=0），`check-lit` 183/187，与基线同 4 个 smoke E2E 超时。
**修改文件**：`tools/infra/paths.py`（`DADAO_INSTALL_ROOT`）；`tools/infra/private_install.py`（新）；`tools/infra/check_module.py`（新）；`tools/infra/module_gates.toml`（新）；`Makefile`（`install-host-private`/`check-module`/`check-module-gates` + 私有模式 `install-host` 短路 + 帮助文本）；本任务书。
**验收结果**：
- 默认 `paths.py --make` 与 master 基线执行结果 `diff` 为空；override 后 7 个键全部重定位到私有根；空/空白/相对/不可建 4 种值均 rc=2。
- 私有根打印：`llvm-mc`（镜像 symlink，md5 `227e2f8c…`）与 `qemu-system-dadao`（owned 真实文件，md5 `8442c39e…`，realpath 在私有根）；共享根 4 个二进制聚合 md5 `df155244…` 前后相同（4/4 PASS）。
- 注入：`DADAO_INSTALL_ROOT` 指回共享根 ⇒ rc=2；映射注入不存在 target ⇒ rc=2，`cp`+md5 还原后回绿（md5 `9e2009ba…` 复原）。
- 守卫：真共享根无 token rc=2 且 md5 不变；sandbox 有 token 放行（兄弟文件保留）、无 token rc=2；`DADAO_MODULE_INSTALL_ROOT` 与解析根不符 ⇒ rc=2。
- L1 受影响子集：`check-dirs`/`check-manifests-guard`/`check-tests-index`/`check-writer-guards` 绿；`check-knowledge-refs` 无本任务新增红；`check-temp-dirs` 本任务目录在用；`check-patch-tree` llvm/qemu 段 0 problem（全仓 2 problem = linux `trap.S`，基线红）。
**新发现/坑**：① `build/bin/clang` 是 symlink，`os.link` 不解引用 ⇒ 私有根内 dangling（lit 报 `command not found`/127），须 `resolve()` 后 hardlink（`cp -L` 语义）；② lit 包必须落 `share/lit/lit`，少一层即 `ModuleNotFoundError`；③ `QEMU_CONFIGURE` 用 `$(CURDIR)/$(QEMU_SRC)`，`DADAO_SOURCE_ROOT` 为绝对路径时拼错，私有 qemu 构建须用相对值（未改，登记）；④ 私有模式下 writer guard 只登记共享 `llvm-mc`（私有安装路径不在其组件映射），语义可接受；⑤ 基线红：`stm.*` 8 例、`cfx2rd_crrr_cfx`、4 个 smoke E2E 超时（本任务失败集与基线逐行相同）；⑥ 证据脚本不可在运行中编辑（bash 按字节偏移续读，必然语法错）。
**遗留问题**：gem5/chipyard 私有构建未实测（无私有 gem5.opt；映射与校验已就绪）；chipyard 空映射按任务书口径由 `check-module` rc=2 指路按需 `idl_four_way.py --platforms chipyard`；上述基线红待 M20 qemu 修复任务。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| H1 `os.link` 硬链 build 树 `bin/clang` symlink 本身 ⇒ 私有根 dangling | ✅已修 | `_place_file` 先 `src.resolve()` 再 link（同 `cp -L`） | 私有 `clang --version` 正常；lit 由 23 红降至 4 红（同基线） |
| H2 lit 包复制到 `share/lit`（少一层）⇒ `llvm-lit` `ModuleNotFoundError` | ✅已修 | 落 `share/lit/lit`，并按 `install-host` 先清 `share/lit` | `llvm-lit --version` = 23.1.3dev |
| H3 `--print-root` 仍要求 `--component` ⇒ 证据脚本取私有根失败 | ✅已修 | 组件改为仅安装分支必填 | `--print-root --task-id selftest` rc=0 |
| H4 私有根嵌套在共享根内会自我镜像 | ✅已修 | 嵌套一律 rc=2（token 不放行） | 守卫分支 4 项注入通过 |
| H5 共享根缺文件时 md5 对账恒真 | ✅已修 | `check_module` 对 `MISSING` fail-closed | 证据 run 4/4 共享 md5 检查 |
| H6 断言口径：继承工具 realpath 在共享根 | ❌不修（有意） | 断言改为「消费路径在私有根 + 本组件 owned 工具必须是真实文件（非 symlink）」；qemu 跑中 qemu realpath 在私有根，llvm 跑中 llvm-mc realpath 在私有根 | 私有跑输出 + `(owned)` 计数 |

### 第 1 轮 reviewer 验收 —— 判决：**Accepted**

**重跑记录（下列命令全部由 reviewer 本人执行，输出/退出码为本人终端实测，未采信完成区）**

1. **默认不回归**：`git archive master` 出的干净树与本树在同环境跑 `python3 tools/infra/paths.py --make`，`diff` 空（rc=0）；`DADAO_INSTALL_ROOT` 空/纯空白/相对/不存在且不可建/非目录 5 种值全部 rc=2 且指名原因（不静默回落）；`DADAO_MODULE_INSTALL_ROOT` 与解析根不符 ⇒ make rc=2。
2. **写探针**：私有安装根 33 个 symlink 目标全部落在共享根或私有根内（越界 0）；向私有根、`tests/`、`writers/` 写探针文件 ⇒ 共享根无对应文件；owned 工具 inode 与共享根不同（无硬链穿透回共享根）。
3. **守卫**：真共享根无 token ⇒ `private_install.py` rc=2；一次性 sandbox 有 token ⇒ rc=0 且兄弟文件保留；sandbox 无 token ⇒ rc=2。
4. **证据脚本**：运行期证据目录内 `run.sh` 重跑 **42/42 PASS、rc=0**（与完成区一致）；reviewer 另做 3 类独立注入：`DADAO_INSTALL_ROOT` 指回共享根 ⇒ `check-module` rc=2；映射注入不存在 target ⇒ `check-module-gates` rc=2，`cp`+md5 还原（`9e2009ba…`）后回 rc=0；`DADAO_MODULE_INSTALL_ROOT` 不符 ⇒ rc=2。
5. **映射校验**：reviewer 自行 grep `GATE_LOCKED_TARGETS`/`.PHONY`/字面目标行，`module_gates.toml` 的 9 个 gate target 全部真实存在；未知 COMPONENT、chipyard 空映射、缺 TASK_ID、TASK_ID 含路径分隔符均 rc=2。
6. **基线红判据**（master 干净树复跑同一命令，未用 `|| true`）：`check-inst-asm` **266/274**（8 条 FAIL）、`check-idl` **265/274**（9 条 FAIL）、`check-lit` **183/187**（4 个 smoke E2E）；与私有跑失败集 `diff` **三者均为空**（rc=0）。`check-knowledge-refs` 在 master 干净树与本树的违规行**逐行相同**（2 条，来自派单提交内容，非本任务引入）。
7. **私有二进制真实性**：qemu 跑打印 `qemu-system-dadao` realpath 落在私有安装根、md5 `8442c39e…`（共享为 `c5a46ef7…`），`llvm-mc` 显式标 `(inherited)`；llvm 跑 `llvm-mc` realpath 在私有根标 `(owned)`、`qemu-system-dadao` 标 `(inherited)`；`check-lit` 183/187，`test-codegen`/`check-instrinfo`/`check-cfx-alias-table` rc=0（3/4 绿，同完成区）。
8. **共享根不变**：私有跑前后共享安装根 6 个二进制（`llvm-mc`/`qemu-system-dadao`/`llvm-objdump`/`ld.lld`/`lli`/`cfx-aliases.txt`）**逐文件** md5 全部相同（不是聚合摘要）。
9. **默认门控成员**：`_locked-check-modules`/`_locked-check-full`/`_locked-check` 与 master 逐行相同；`install-host` 仍在 `GATE_LOCKED_TARGETS`（成员 52 个未增删），共享模式 recipe 与 master 仅差一个空行。
10. **范围与文档**：`git status -uall` 仅任务书 + `paths.py` + 3 个新工具 + `module_gates.toml` + `Makefile`；无运行期目录/证据入库；未动 `spec/`/契约/测试向量语义；完成区 14 行（≤30）且无运行期路径；交付物 md5 在审查前后一致（我的注入全部还原）。

**约束核验**：独立 worktree ✓；本轮零 git 写操作（不提交）✓；改动文件与任务书「约束」声明逐一对得上 ✓；新增文本无「银行」误用 ✓。`check-patch-tree` reviewer 重跑 rc=1，2 problem 全在 `linux`（trap.S），llvm/qemu 段 0 problem —— 本任务 diff 不触及组件补丁树，判为基线红（**逻辑核对，未在 master 树复跑**，如需可补）。

**发现（不阻断，留 architect 收尾处理）**：F1 `run.sh` 失败集对比未校验日志存在性（`cp` 失败 ⇒ 两侧空文件 ⇒ 恒等 PASS）；本轮日志实测 280/289 行非空且计数 266/274、265/274，结论不受影响，建议补 `test -s`。F2 `check-patch-tree` 断言只 grep `(llvm-project|qemu): (assertion|problem)` 行且不取 rc，非 assertion 型错误不会计入。F3 `check_module.py` 共享根快照只含 4 个文件（缺 llvm 拥有的 `ld.lld`/`llvm-objdump`），reviewer 已用 6 个逐文件快照补验。F4 完成区写「聚合 md5」，建议表述为逐文件（`check_module.py` 内部本就是逐文件 `[PASS]`）。

**判决：Accepted** —— 验收命令块在 reviewer 本人重跑下全部通过，10 条独立核验项与硬约束无违反；F1–F4 属证据脚本健壮性/文档表述问题，不改代码行为、门控退出码与断言语义。
