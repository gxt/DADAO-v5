# INFRA-119t: LLVM / QEMU 构建入口接入 ccache

**模块**：infra
**项目里程碑**：M11
**依赖**：无（gem5 侧的既有接入 `tools/gem5/build_gem5.py` 只作**同构参照**，非执行依赖）
**状态**：待开始

## 执行环境

**执行环境**：本地（仓库根；从含本册的 `master` 建独立 `git worktree` + 分支 `INFRA-119t`）。证据落 `.work/evidence/INFRA-119t/**`、日志 `.work/log/infra/INFRA-119t-*.log`、临时物 `/tmp/opencode/INFRA-119t/**`。开工前确认：① `.work/build/llvm/build.ninja`、`.work/build/qemu/build.ninja` 存在（首轮 reconfig 的基线构建树）；② `ccache` 在 PATH（本机 `4.9.1`）；③ `manifest-check` 通过（两组件均已 enabled）。任一不成立 ⇒ **rc=2 BLOCKED**，不得用旧日志冒充。

## 用户口径（2026-11-04，主会话转达；与 `discussing.md` 同日 ccache 条目一致）

1. 只接 **LLVM + QEMU 两个构建入口**；gem5 已接；musl / picolibc / Linux 各自后续任务，本任务不碰。
2. 缓存用**全局默认** `~/.cache/ccache`；**不**软链到 PATH、**不**做编译器影子、**不**强制 `CCACHE_DIR` / `MAXSIZE`。
3. LLVM 走 CMake launcher（`-DCMAKE_C_COMPILER_LAUNCHER=… -DCMAKE_CXX_COMPILER_LAUNCHER=…`）或 `LLVM_CCACHE_BUILD=ON`；QEMU 在 configure 前用 `CC="ccache gcc"` / `CXX="ccache g++"`。
4. 配置变更必须**重跑 configure**（stamp 机制），既有 `build.ninja` 不得让旧编译器被静默复用。
5. 不改源码 / 补丁 / `spec/` / `tests/` / `contracts/`；不改变 QEMU 产物语义。
6. 验收 = 增量 + 一次 reconfig 均 rc=0、ccache 命中增长、产物/版本/md5 与未接 ccache 一致、L1/关键门控不退化、反例注入可达 FAIL。

## 现场事实（2026-11-04 只读核对，实施时须以现场复核）

- **ccache**：`/usr/bin/ccache` 4.9.1；`ccache -s` 显示 `Cache size 0.0 / 5.0 GiB`（**冷缓存**）；`hash_dir = true`（默认）⇒ ccache 不重写调试路径，产物可与直编**逐字节相同**。
- **等价性预检（已实测）**：`gcc -g -O2 -c` 直编、经 ccache 的 miss、经 ccache 的 hit 三者 md5 相同（`acd52ff7…`）；`ccache --print-stats` 的 `direct_cache_hit` 在命中时 +1，是「命中增长」的可靠读数。
- **LLVM**（`Makefile` L294-300）：`LLVM_BUILD_CONFIG = targets=… projects=… build_type=… assertions=ON`；`LLVM_CONFIGURE` 用该串 `cmp` 比对 `.work/build/llvm/.dadao-llvm-config`，不同才 cmake 并回写 stamp。`CMakeCache.txt`：`CMAKE_C_COMPILER=/usr/bin/cc`、`CMAKE_CXX_COMPILER=/usr/bin/c++`、`LLVM_CCACHE_BUILD:BOOL=OFF`（36 行注入点在 cmake 命令行，不在 CMakeCache 手改）。
- **QEMU**（`Makefile` L364-393）：`_locked-build-qemu` 见 `build.ninja` 即跳过 configure ⇒ **必须新增 stamp 判据**，否则新编译器不生效。`.work/build/qemu/config-meson.cross` 现为 `c = ['cc','-m64']`、`cpp = ['c++','-m64']`，`config-host.mak` 不记录 CC。
- **QEMU configure 契约**（`.work/source/qemu/configure` L286-298、L1826-1829）：`cc="${CC-…gcc}"`、`cxx="${CXX-…g++}"` 直接吃环境变量；`meson_quote` 按空格拆成列表 ⇒ `CC="ccache gcc"` 写成 `c = ['ccache','gcc']`，无引号陷阱。
- **`cc` ≡ `gcc`**：`/usr/bin/cc` 与 `/usr/bin/gcc` 同文件（md5 `af50fbdcef87…`）；`c++` 与 `g++` 同文件（md5 `71ae60bd230d…`）⇒ 把 QEMU 从 `cc` 改 `gcc` 不引入编译器差异。
- **既有基线**：LLVM `bin/{llc,llvm-mc,clang-23,lli,lld,ld.lld}` 存在（clang 4.3 GB、llc 1.9 GB）；QEMU `qemu-system-dadao`、`qemu-dadao` 存在。**既有红**（与本任务无关，不得归因、也不得声称本任务引入）：`check-tasks --strict` 的 `TESTCASES-090t`（`待验收`）、`check-knowledge-refs` 的 66 条悬空（均为既往任务册对 `.work/evidence/*` 的引用；本册引用已用通配形，现场核验新增悬空 = 0）。

## 接口规范

### 1. Makefile 变量（唯一实现改动）

```make
# 仅当 ccache 在 PATH 才启用；`make ... CCACHE=` 可显式关闭（空值）。
CCACHE ?= $(shell command -v ccache 2>/dev/null)
```

- **LLVM**：`LLVM_BUILD_CONFIG` 追加 `ccache=$(if $(CCACHE),$(CCACHE),off)`；`LLVM_CONFIGURE` 的 cmake 调用追加 `$(if $(CCACHE),-DCMAKE_C_COMPILER_LAUNCHER=$(CCACHE) -DCMAKE_CXX_COMPILER_LAUNCHER=$(CCACHE))`。**不启用** `LLVM_CCACHE_BUILD=ON`（它会关 PCH，且 ccache 缺失时 FATAL，行为不够温和）。
- **QEMU**：新增
  - `QEMU_CONFIGURE_ARGS = --target-list=dadao-softmmu,dadao-linux-user --enable-tcg --disable-werror`（原参数原样搬入，不改语义）；
  - `QEMU_BUILD_CONFIG = args=$(QEMU_CONFIGURE_ARGS) cc=$(…|default) cxx=$(…|default)`；
  - `QEMU_CONFIGURE`（单行 shell，与 `LLVM_CONFIGURE` 同构）：stamp `.work/build/qemu/.dadao-qemu-config` 与配置串 `cmp` 不同 ⇒ `mkdir -p` + `cd` + `CC="…" CXX="…" $(CURDIR)/$(QEMU_SRC)/configure $(QEMU_CONFIGURE_ARGS)`，成功后才回写 stamp。
  - `_locked-build-qemu` 与 `_locked-build-qemu-reconfig` 都调 `QEMU_CONFIGURE`；reconfig 先 `rm -f` stamp。删除原「`build.ninja` 存在即跳过」分支（由 stamp 取代）。
- 帮助文本（L157-162）补一句 ccache 状态来源，不新增 target、不新增门控。

### 2. 行为矩阵（必须逐条成立）

- stamp 缺失（首次接入）⇒ 重跑 configure，stamp 写入带 ccache 的配置串。
- stamp 相同且 `build.ninja` 存在 ⇒ 跳过 configure（增量 fast path）。
- `CCACHE=`（空）或 ccache 不在 PATH ⇒ 不接 ccache，stamp 记 `off`，重跑一次 configure（命令变化所致），日志打印 `ccache: off`。
- configure 失败 ⇒ **不写** stamp（下次仍重跑），rc≠0。
- `build-mc-reconfig` / `build-qemu-reconfig` ⇒ 无条件重跑 configure，仍带同一 launcher，**不产生**第二次全量重编。

### 3. 产物一致性判据（硬条件）

- 接 ccache 前后，下列文件 **md5 与 size 完全相同**，且 `--version` 首行**逐字节相同**（`cmp`）：LLVM `llc`/`llvm-mc`/`clang`/`clang-23`/`lli`/`lld`/`ld.lld`；QEMU `qemu-system-dadao`/`qemu-dadao`。
- 依据：launcher 只改调用前缀，ccache `hash_dir=true` 不改调试路径，命中回放的是同一次编译产物（已实测 md5 相同）。**若复现出不一致**：逐项查 `-fdebug-prefix-map`/`-ffile-prefix-map`、`-frandom-seed`、`__DATE__/__TIME__`、link `build-id`，给出证据与根因；不得把「不一致」当可接受。

### 4. 不变量

- 不改 `.work/source/**`、`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`tests/**`、`manifests/**`、`tools/**`、`docs/**`；不跑 `install-host`（`install-host` 会连带 `build-builtins`，本任务无工具内容变化）。
- 不改 ccache 自身配置（`CCACHE_DIR`/`max_size`/`sloppiness`/`compression`）；不软链 PATH。
- 构建树 `.work/build/**` 是 disposable，不入库；stamp 只写在构建树内。

## 验收标准

1. **接入点存在**：`grep -c ccache .work/build/llvm/build.ninja` > 0（launcher 出现在编译命令行）；`grep -E "c = \['ccache'" .work/build/qemu/config-meson.cross` 命中；两份 stamp 内容含 `ccache=` 且值 = `command -v ccache`。
2. **LLVM 构建**：`make build-mc` 首轮 rc=0（日志出现一次 `llvm: configuring`，申报并记录耗时）；紧接着再跑 `make build-mc` rc=0 且 `ninja: no work to do`（`grep -q "no work to do"`）。`make build-mc-reconfig` rc=0 且**不触发**全量重编（第二轮仍 no work）。
3. **QEMU 构建**：`make build-qemu` 首轮 rc=0（出现一次 `qemu: configuring`）；再跑 rc=0 且无编译动作；`make build-qemu-reconfig` rc=0 且无全量重编。
4. **产物一致**：§接口规范 3 列出的全部二进制 md5+size 与开工前基线**逐项相等**、`--version` 首行 `cmp` 相等；`make check-install-tools` rc=0（安装根与 build 树尺寸一致 ⇒ 无需重装）。
5. **命中增长**：删除 1 个 LLVM 对象（如 `tools/llvm-mc/CMakeFiles/llvm-mc.dir/llvm-mc.cpp.o`）与 1 个 QEMU 对象后重建，`ccache --print-stats` 的 `direct_cache_hit`（+`preprocessed_cache_hit`）**严格增长**，且重建对象/最终二进制 md5 不变；证据脚本给出前后计数。
6. **语义不退化**：`make check-inst-smoke QEMU_BIN=.work/build/qemu/qemu-system-dadao` rc=0（缺 bootrom 先 `make build-bootrom`）；`.work/build/llvm/bin/llvm-mc --version`、`llc --version` 的 `dadao` 目标存在（`--version` 输出中 grep `dadao`）。
7. **L1/关键门控**：`make check` rc=0（本任务红=0，既有红逐条基线复现）；`check-milestones-fresh`、`check-archive`、`check-components`、`check-patch-tree`、`check-no-residue`、`check-dirs`、`check-install-tools` rc=0；`check-tasks` 附表出现本任务且主表不新增（`--strict` 既有红 `TESTCASES-090t` 保持原样）。
8. **范围**：`git diff --name-only <base>` 只含 `Makefile` + 本册 + `.tao/knowledge/milestones.md`；无 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej` 残留。
9. **证据/注入**：`.work/evidence/INFRA-119t/*` 的 `run.sh` 一键分 phase 重跑（baseline → precheck → build → 一致性 → 命中 → 语义 → 门控 → 注入），每 phase 落 `*_EXIT=<rc>`；`REPORT.md` 数字全部脚本现场生成（含基线/重建 md5、`ccache --print-stats` 前后值、耗时）。
10. **完成区/状态**：完成区 ≤30 行、与真实输出逐条对齐；状态 `待验收`。

## 必测反例（每条必须可达 FAIL；不是上限）

1. **launcher 未真正生效**：`make build-mc CCACHE=/bin/false` ⇒ 配置 stamp 与 build.ninja 的 launcher 变成 `/bin/false`，构建立即非零退出，`grep ccache build.ninja` 断言 FAIL；恢复 `make build-mc`（默认）⇒ reconfig 回 ccache、`ninja: no work to do` ⇒ 回绿。
2. **QEMU 同型**：`make build-qemu CCACHE=/bin/false` ⇒ configure/编译非零退出；恢复后回绿。
3. **stamp 失效（旧分支回归）**：临时改回「`build.ninja` 存在即跳过 configure」的逻辑（`cp` 备份 + md5 还原）⇒ 换 `CCACHE=/bin/false` 后**不重跑** configure，接入点断言 FAIL ⇒ 证 stamp 判据有实际约束力。
4. **命中不增长**：`CCACHE_DISABLE=1` 下删对象重建 ⇒ 计数不增长，命中断言 FAIL；去掉变量重建 ⇒ 回绿。
5. **md5 比较不能恒真**：把基线某二进制重命名/换一份（`cp` 备份 + md5 还原）⇒ 一致性断言 FAIL；还原后回绿。
6. **空跑/少跑**：`ccache --print-stats` 无输出或 build 日志缺 `PASS` 行 ⇒ 驱动 rc=2（fail-closed），不得绿灯。

> 还原纪律：一律 `cp` 备份 + `md5sum` 对账（禁 `git checkout`/`restore`/`stash`/`show`）；`git status`/`git diff` 干净**不作**还原证据。

## 证据

- `.work/evidence/INFRA-119t/*`：`run.sh`（`--inject` 跑反例）+ `REPORT.md` + `baseline/`（开工前 md5/size/`--version`/`ccache --print-stats` 快照）+ `precheck/`（直编 vs 经 ccache 的 md5 等价性探针，含源码与产物）。
- 日志：`.work/log/infra/INFRA-119t-*.log`（`…-build-mc`/`…-build-qemu`）、`.work/log/qemu/*`（smoke）。长构建一律 background + `*_EXIT`，禁 `setsid nohup` 后失联。
- 构建身份：`.work/source/{llvm-project,qemu}` 的 `git rev-parse HEAD`、`manifests/components.lock.toml` 的锁定 commit、`ccache --version`、gcc/g++ `--version`。

## 说明（风险 / 非目标 / 未决）

### 1. 风险

- **R1 全量重编成本（最重要）**：launcher 进入编译命令行 ⇒ ninja 认为命令变化，**首轮必全量重编**（不是缺陷）。ccache 冷缓存（0.0 GiB）首轮基本全 miss，且哈希/压缩带来额外开销。预估：**QEMU 15–30 min、LLVM 60–150 min（`-j8`，含 4.3 GB clang 链接）**；启动前申报耗时，分两个后台任务跑、各自落 `*_EXIT`。
- **R2 缓存容量**：默认 `max_size 5 GiB`，LLVM+QEMU 全量对象远超此值 ⇒ 长期高淘汰，命中率有限。本任务按用户口径**不调** `max_size`，只把 `ccache -s` 的 size/eviction 事实写进完成区，供后续单独立项。
- **R3 QEMU 编译器身份**：`cc`→`gcc` 依赖「同文件」实测（见现场事实）；换机器复核后若不同 ⇒ **停并报**，不得带差异继续。
- **R4 gate lock**：`build-mc`/`build-qemu` 在 `GATE_LOCKED_TARGETS`，同一工作树一次只跑一个，等待上限 3600 s；`make -j` 保持 `JOBS=8`，禁全核。
- **R5 一次性判定口径**：`check-install-tools` 用 size 比对 build 树；若重建后 size 变化，先查根因，**不得**用 `make install-host` 掩盖（其前置 `build-builtins` 成本高且无内容变化）。
- **R6 stamp 与并发**：stamp 写在构建树内，`clean-work` 会清掉 ⇒ 首次构建重跑 configure（预期）；不把 stamp 放仓库。

### 2. 非目标

gem5（已接）、musl、picolibc、Linux 的 ccache 接入；ccache 配置调优；`install-host` 重装；任何源码/补丁/spec/tests/contracts/docs 改动；`build-mc-lite`/`build-lld` 的额外行为（它们复用同一 `LLVM_CONFIGURE`，自动继承）。

### 3. 未决（执行时可登记，不阻塞）

- ① 是否把「ccache max_size / 淘汰率」单独立项（本任务只记事实）。
- ② 若首轮 LLVM 全量重编超过 2 h，是否拆成两次跨会话续跑（须登记检查点：日志路径 + `*_EXIT` 位置 + 预计完成时间）。

### 4. 参考对照（内容溯源，非执行必需）

- `tools/gem5/build_gem5.py`（既有 ccache 接入形态：探测 `shutil.which("ccache")`、`CC`/`CXX` 前缀、不强设 `CCACHE_DIR`）——只作同构参照。
- `discussing.md` 2026-11-04「ccache 接入口径」；`AGENTS.md`「构建与注入测试的成本控制」「长任务」。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
