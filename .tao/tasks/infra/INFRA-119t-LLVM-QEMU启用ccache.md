# INFRA-119t: LLVM / QEMU 构建入口接入 ccache

**模块**：infra
**项目里程碑**：M11
**依赖**：无（gem5 侧的既有接入 `tools/gem5/build_gem5.py` 只作**同构参照**，非执行依赖）
**状态**：已验证

## 执行环境

**执行环境**：本地（仓库根；从含本册的 `master` 建独立 `git worktree` + 分支 `INFRA-119t`）。证据落 `运行期证据（已清理，未归档）`、日志 `运行期日志（已清理，未归档）`、临时物 `运行期临时目录`。开工前确认：① `运行期 LLVM 构建树中的 build.ninja`、`运行期 QEMU 构建树中的 build.ninja` 存在（首轮 reconfig 的基线构建树）；② `ccache` 在 PATH（本机 `4.9.1`）；③ `manifest-check` 通过（两组件均已 enabled）。任一不成立 ⇒ **rc=2 BLOCKED**，不得用旧日志冒充。

## 用户口径（2026-11-04，主会话转达；与 `discussing.md` 同日 ccache 条目一致）

1. 只接 **LLVM + QEMU 两个构建入口**；gem5 已接；musl / picolibc / Linux 各自后续任务，本任务不碰。
2. 缓存用**全局默认** `ccache 缓存`；**不**软链到 PATH、**不**做编译器影子、**不**强制 `CCACHE_DIR` / `MAXSIZE`。
3. LLVM 走 CMake launcher（`-DCMAKE_C_COMPILER_LAUNCHER=… -DCMAKE_CXX_COMPILER_LAUNCHER=…`）或 `LLVM_CCACHE_BUILD=ON`；QEMU 在 configure 前用 `CC="ccache gcc"` / `CXX="ccache g++"`。
4. 配置变更必须**重跑 configure**（stamp 机制），既有 `build.ninja` 不得让旧编译器被静默复用。
5. 不改源码 / 补丁 / `spec/` / `tests/` / `contracts/`；不改变 QEMU 产物语义。
6. 验收 = 增量 + 一次 reconfig 均 rc=0、ccache 命中增长、产物/版本/md5 与未接 ccache 一致、L1/关键门控不退化、反例注入可达 FAIL。

## 现场事实（2026-11-04 只读核对，实施时须以现场复核）

- **ccache**：`/usr/bin/ccache` 4.9.1；`ccache -s` 显示 `Cache size 0.0 / 5.0 GiB`（**冷缓存**）；`hash_dir = true`（默认）⇒ ccache 不重写调试路径，产物可与直编**逐字节相同**。
- **等价性预检（已实测）**：`gcc -g -O2 -c` 直编、经 ccache 的 miss、经 ccache 的 hit 三者 md5 相同（`acd52ff7…`）；`ccache --print-stats` 的 `direct_cache_hit` 在命中时 +1，是「命中增长」的可靠读数。
- **LLVM**（`Makefile` L294-300）：`LLVM_BUILD_CONFIG = targets=… projects=… build_type=… assertions=ON`；`LLVM_CONFIGURE` 用该串 `cmp` 比对 `运行期 LLVM 构建树中的 .dadao-llvm-config`，不同才 cmake 并回写 stamp。`CMakeCache.txt`：`CMAKE_C_COMPILER=/usr/bin/cc`、`CMAKE_CXX_COMPILER=/usr/bin/c++`、`LLVM_CCACHE_BUILD:BOOL=OFF`（36 行注入点在 cmake 命令行，不在 CMakeCache 手改）。
- **QEMU**（`Makefile` L364-393）：`_locked-build-qemu` 见 `build.ninja` 即跳过 configure ⇒ **必须新增 stamp 判据**，否则新编译器不生效。`运行期 QEMU 构建树中的 config-meson.cross` 现为 `c = ['cc','-m64']`、`cpp = ['c++','-m64']`，`config-host.mak` 不记录 CC。
- **QEMU configure 契约**（`QEMU 组件源树中的 configure` L286-298、L1826-1829）：`cc="${CC-…gcc}"`、`cxx="${CXX-…g++}"` 直接吃环境变量；`meson_quote` 按空格拆成列表 ⇒ `CC="ccache gcc"` 写成 `c = ['ccache','gcc']`，无引号陷阱。
- **`cc` ≡ `gcc`**：`/usr/bin/cc` 与 `/usr/bin/gcc` 同文件（md5 `af50fbdcef87…`）；`c++` 与 `g++` 同文件（md5 `71ae60bd230d…`）⇒ 把 QEMU 从 `cc` 改 `gcc` 不引入编译器差异。
- **既有基线**：LLVM `bin/{llc,llvm-mc,clang-23,lli,lld,ld.lld}` 存在（clang 4.3 GB、llc 1.9 GB）；QEMU `qemu-system-dadao`、`qemu-dadao` 存在。**既有红**（与本任务无关，不得归因、也不得声称本任务引入）：`check-tasks --strict` 的 `TESTCASES-090t`（`待验收`）、`check-knowledge-refs` 的 66 条悬空（均为既往任务册对 `运行期证据（已清理，未归档）` 的引用；本册引用已用通配形，现场核验新增悬空 = 0）。

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
  - `QEMU_CONFIGURE`（单行 shell，与 `LLVM_CONFIGURE` 同构）：stamp `运行期 QEMU 构建树中的 .dadao-qemu-config` 与配置串 `cmp` 不同 ⇒ `mkdir -p` + `cd` + `CC="…" CXX="…" $(CURDIR)/$(QEMU_SRC)/configure $(QEMU_CONFIGURE_ARGS)`，成功后才回写 stamp。
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

- 不改 `组件源树`、`components/**`、`spec/**`、`contracts/**`、`.tao/contracts/**`、`tests/**`、`manifests/**`、`tools/**`、`docs/**`；不跑 `install-host`（`install-host` 会连带 `build-builtins`，本任务无工具内容变化）。
- 不改 ccache 自身配置（`CCACHE_DIR`/`max_size`/`sloppiness`/`compression`）；不软链 PATH。
- 构建树 `运行期构建树` 是 disposable，不入库；stamp 只写在构建树内。

## 验收标准

1. **接入点存在**：`grep -c ccache 运行期 LLVM 构建树中的 build.ninja` > 0（launcher 出现在编译命令行）；`grep -E "c = \['ccache'" 运行期 QEMU 构建树中的 config-meson.cross` 命中；两份 stamp 内容含 `ccache=` 且值 = `command -v ccache`。
2. **LLVM 构建**：`make build-mc` 首轮 rc=0（日志出现一次 `llvm: configuring`，申报并记录耗时）；紧接着再跑 `make build-mc` rc=0 且 `ninja: no work to do`（`grep -q "no work to do"`）。`make build-mc-reconfig` rc=0 且**不触发**全量重编（第二轮仍 no work）。
3. **QEMU 构建**：`make build-qemu` 首轮 rc=0（出现一次 `qemu: configuring`）；再跑 rc=0 且无编译动作；`make build-qemu-reconfig` rc=0 且无全量重编。
4. **产物一致**：§接口规范 3 列出的全部二进制 md5+size 与开工前基线**逐项相等**、`--version` 首行 `cmp` 相等；`make check-install-tools` rc=0（安装根与 build 树尺寸一致 ⇒ 无需重装）。
5. **命中增长**：删除 1 个 LLVM 对象（如 `tools/llvm-mc/CMakeFiles/llvm-mc.dir/llvm-mc.cpp.o`）与 1 个 QEMU 对象后重建，`ccache --print-stats` 的 `direct_cache_hit`（+`preprocessed_cache_hit`）**严格增长**，且重建对象/最终二进制 md5 不变；证据脚本给出前后计数。
6. **语义不退化**：`make check-inst-smoke QEMU_BIN=运行期 QEMU 构建树中的 qemu-system-dadao` rc=0（缺 bootrom 先 `make build-bootrom`）；`运行期 LLVM 构建树中的 bin/llvm-mc --version`、`llc --version` 的 `dadao` 目标存在（`--version` 输出中 grep `dadao`）。
7. **L1/关键门控**：`make check` 的 rc 与基线相同且**无新增失败目标**（既有 `check-knowledge-refs` 72 悬空为基线红，不归本任务）；`check-milestones-fresh`、`check-archive`、`check-components`、`check-patch-tree`、`check-no-residue`、`check-dirs`、`check-install-tools` rc=0；`check-tasks` 附表出现本任务；交付树中状态仍为 `待验收`，故 `check-tasks --strict` 出现**唯一** `① INFRA-119t` 属预期，其它 `①` 为 0。
8. **范围**：`git diff --name-only <base>` 只含 `Makefile` + 本册 + `.tao/knowledge/milestones.md`；无 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej` 残留。
9. **证据/注入**：`运行期证据（已清理，未归档）` 的 `run.sh` 一键分 phase 重跑（baseline → precheck → build → 一致性 → 命中 → 语义 → 门控 → 注入），每 phase 落 `*_EXIT=<rc>`；`REPORT.md` 数字全部脚本现场生成（含基线/重建 md5、`ccache --print-stats` 前后值、耗时）。
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

- `运行期证据（已清理，未归档）`：`run.sh`（`--inject` 跑反例）+ `REPORT.md` + `baseline/`（开工前 md5/size/`--version`/`ccache --print-stats` 快照）+ `precheck/`（直编 vs 经 ccache 的 md5 等价性探针，含源码与产物）。
- 日志：`运行期日志（已清理，未归档）`（`…-build-mc`/`…-build-qemu`）、`运行期日志（已清理，未归档）`（smoke）。长构建一律 background + `*_EXIT`，禁 `setsid nohup` 后失联。
- 构建身份：`组件源树 {llvm-project,qemu}` 的 `git rev-parse HEAD`、`manifests/components.lock.toml` 的锁定 commit、`ccache --version`、gcc/g++ `--version`。

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

**测试结果**：全部可执行判据 PASS：`consistency` **rc=0（24/24，含 `check-install-tools`）**、`determinism` rc=0、`hit` rc=0（`hits_before=5865` 严格增长、对象/二进制 md5 不变）、`inject` **rc=0（40 条断言 I1–I7）**、`static` 20/20。主路径重建（`make build-mc-reconfig` @ `仓库根`，rc=0，3573 步 ccache 全命中）后 `llc/llvm-mc/clang-23/lli` 与基线 md5+size 逐项相等（`0ab44948…`/`3693b3fe…`/`ba2d2a6c…`/`288196de…`）；注入后 I7 复核产物未变。
**修改文件**：`Makefile`（ccache 接入 + `QEMU_STAMP` 绝对化）；`运行期证据（已清理，未归档）`（`运行期临时目录` 软链主工作树，不入库）。
**验收结果**：真 rc：`consistency`=0、`determinism`=0、`hit`=0、`inject`=0、`static`=0、`check-install-tools`=0、`check-no-residue`=0。错误路径试跑 `--inject`（cwd=运行期临时目录 worktree）⇒ **rc=2 BLOCKED**（路径守卫），不再破坏共享构建树。
**新发现/坑**：① **产物 md5 只在同一构建路径下可比**：cmake 把 cwd 烘进 `build.ninja`，跨 worktree 跑 build/inject 会静默重配共享树并把产物换成另一套路径（早前 5 个 LLVM 二进制 md5 不等 + `check-install-tools` rc=2 即此）；已加 `require_same_build_root()` 守卫。② QEMU `CCACHE=/bin/false` 在 configure 编译器探测阶段即失败 ⇒ 按设计**不写** stamp（I2 断言改为「stamp/`config-meson.cross`/`build.ninja` 原封不动」）。③ 全局 ccache 计数会被并发任务污染 ⇒ I4 改**私有 `CCACHE_DIR`**（seed miss=1/hit=0 → disabled hits=0、miss 冻结 → 恢复 hits>0）。④ 失败的 `/bin/false` 运行会 unlink 已启动命令的输出 ⇒ restore 需重编少量对象，fast path 由「紧接的再一次 build」证 `no work to do`。⑤ ccache 4.9 的 `disabled` 计数器不随 env 禁用递增（用 hits/miss 判）。⑥ ccache 现场 `cache_dir=ccache 缓存目录`、`max_size=20G`（任务书旧写 `ccache 缓存`/5 GiB）。
**遗留问题**：① `build-qemu-reconfig` 真实开销未单独实测（configure 无条件重写 `config-host.h`，可能大范围重编），需主会话按需测量；② `semantics`/`gates` 本轮未重跑（上轮已 PASS，本轮产物经 I7 验证未变）；③ 任务书「现场事实」ccache 路径/容量按上⑥更正。**状态保持 `待开始`（由主会话决定是否推进）。**

## 审阅记录

#### 第 1 轮 engineer 自审

审查对象：`git diff -- Makefile` + `运行期证据（已清理，未归档）`。要点：off 分支 `$(if)` 展开为空（cmake 仅多一个空格；QEMU 不设空 `CC`，探针断言 `CC=<unset>`）；`QEMU_CONFIGURE` 的 `… configure || exit 1; echo stamp` 保证 configure 失败不写 stamp；`CCACHE ?=` 的命令行值经 `$(MAKE)` 重入传递（`make -n build-mc CCACHE=/bin/false` 实测 launcher 变 `/bin/false`）；`build-mc-lite`/`build-lld` 复用同一 `LLVM_CONFIGURE` 自动继承；未新增 target/门控，`.PHONY` 未动；QEMU 三参数逐字搬入。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| QEMU stamp 只记 `cc=` 时验收①「两份 stamp 含 `ccache=`」不成立 | ✅已修 | `QEMU_BUILD_CONFIG` 前置 `ccache=<path|off>` | `static/make-n-build-qemu.txt` 含 `ccache=/usr/bin/ccache` |
| 静态断言计数写错（launcher 对 2、probe 期望 0）⇒ 假红 | ✅已修 | 2→1；0→1 | 重跑 static 19/19 PASS |
| `grep -cF '-DCMAKE…'` 被当选项（`unknown devices method`） | ✅已修 | 加 `--` | 重跑 static PASS |
| 证据脚本临时目录落在 worktree 内（未跟踪残留） | ✅已修 | 统一 `$AUX=运行期临时目录`，清理 `probe/`、`ccache-precheck/` | `git status --porcelain -uall` 仅 ` M Makefile` |
| `gates` 原按 `make check` rc=0 判，与既有红冲突 | ✅已修 | baseline 记 FAIL target 集，gates 判「无新增」 | `baseline/check-baseline-failing.txt` |
| 静态 phase 可能恒真 | ✅已修 | 注入删除 launcher ⇒ 4 FAIL/rc=1；cp+md5 还原 ⇒ 回绿 | `static/inject-launcher-removed.log`、`static/restored-after-inject.log` |

判决：实现与证据脚本无未修 finding；构建类 phase 未执行，状态保持 `待开始`。

#### 第 2 轮 engineer 自审（构建后轮）

审查对象：本轮 `Makefile` 增补（`QEMU_STAMP`）+ 证据脚本修复 + 一致性结论。要点：`QEMU_STAMP` 只在 stamp 的
读写处生效，`QEMU_CONFIGURE`/reconfig 行为语义不变；脚本改动均不改判据（cross 断言改为按 `$(command -v ccache)`
实值匹配，属修正错误期望，非放宽）；`consistency` 的 md5 判据原样保留、真红。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `$AUX` 在 tmpfs 重启后不存在 ⇒ `--version` 比对假 FAIL | ✅已修 | preflight/consistency `mkdir -p "$AUX"` | 重跑 `consistency`：9/9 `--version` 首行 PASS |
| QEMU cross 断言把 launcher 当裸 `ccache`（实为绝对路径） | ✅已修 | 按 `$CCACHE_BIN` 精确匹配 `c = ['…/ccache','gcc'` | `consistency` 两条 PASS |
| `QEMU_STAMP` 未绝对化 ⇒ `cd` 后回写落到 `<build>/<build>/…`（stamp 丢失、每次重配） | ✅已修 | `QEMU_STAMP = $(abspath …)` + 相对 build 回归用例 | 注入旧写法 ⇒ 4 FAIL/rc=1；还原 ⇒ probe 0 failure（`static/inject-stamp-relative-build*.log`） |
| 静态断言随 `QEMU_STAMP` 变化而假红（stamp 路径计数） | ✅已修 | 改为「绝对 stamp 定义 1 处 + `$(QEMU_STAMP)` 2 处」+ dry-run 绝对路径 | `static` 20/20 PASS |
| 有把 LLVM md5 差异误判为 ccache/非确定的可能 | ✅已修（证据化） | 新增 `determinism` phase + `path-normalize-proof.py` | `determinism` PASS：同路径 A/B 对象 md5 全等、`.debug_str` 相同、根路径归一化后 `.debug_line_str` 相同 |
| `check-install-tools` rc=2 想用 `install-host` 消掉 | ❌不修（任务书禁止） | 记录同源根因 | 该门控保持 FAIL，结论 BLOCKED（§完成区遗留①） |

判决：无未修 finding；LLVM 5 项 md5+size 与 `check-install-tools` 属**路径一致性 BLOCKED**，不由实现缺陷引起，
状态保持 `待开始`。

#### 第 3 轮 engineer 自审（inject 收口轮）

审查对象：`run.sh` 的 inject 重写（路径守卫、I2/I4/I5 断言、I7 收尾）与 `Makefile` 的 `QEMU_STAMP` 修复；判据未改动、
未用 `install-host`、未改期望值。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| inject 从非构建 worktree 跑会静默重配共享树、换掉已验收产物 | ✅已修 | `require_same_build_root()`；注入前「产物==基线」守卫 | 错误路径 `--inject` ⇒ rc=2；正确路径 I1–I7 全 PASS |
| I2 断言「stamp 写成 /bin/false」与行为矩阵「configure 失败不写 stamp」矛盾 | ✅已修 | 改断言：rc≠0 且 stamp/`config-meson.cross`/`build.ninja` 原封不动 | `inject-final.log` I2 6 条 PASS（configure 报 `C compiler "/bin/false gcc" … does not work`） |
| I4 依赖全局 ccache 计数，被并发任务污染 ⇒ 假红 | ✅已修 | 私有 `CCACHE_DIR`：seed(0/1) → disabled(hits=0, miss 冻结) → 恢复(hits>0) | I4 5 条 PASS |
| I1「restore 后 ninja: no work to do」假设不成立（失败运行会 unlink 输出） | ✅已修 | restore 断言「产物==基线」；fast path 由紧接的再一次 `make build-mc` 证 | I1 9 条 PASS（`no work to do`=1） |
| I5 与基线比较，但产物已被 I1 的 restore 换掉 ⇒ 归因错误 | ✅已修 | 起始守卫 + 同时对照「篡改前 md5」与「基线」+ I7 复核整轮产物未变 | I5 4 条、I7 2 条 PASS |
| `determinism` 字节相同时分支写成 `chk … 1 1`（恒真） | ✅已修 | 改为 `cmp -s` 实测 rc | 重跑 determinism PASS（`cmp rc=0`） |
| BLOCKED（rc=2）被驱动记成普通 FAIL（rc=1） | ✅已修 | 驱动遇 rc=2 直接 `exit 2` 并打印 BLOCKED | 错误路径实测 rc=2 |

判决：无未修 finding；可执行判据全绿，状态交主会话决定（保持 `待开始`）。

#### 第 1 轮 reviewer 验收（2026-11-04）

**快照对账**：主工作树起始 `git status --porcelain -uall` 空、HEAD=`aa690763`、`Makefile md5=7dc70938…`；备份 `cp -p Makefile 运行期临时目录`（md5 同）→ `cp` 任务版 `22dc83ac…` → 跑完 `cp` 还原，收尾 md5 回 `7dc70938…`、`git status` 空、HEAD 与 `.tao/knowledge/milestones.md`（`304ba457…`）、本册（`9ec47ef3…`）md5 全等；全程只用 `cp`+md5，未用 `checkout/restore/stash`。

**我自己的重跑**（`REPO=仓库根`；JOBS 按 AGENTS 取 8，派单写的 32 未采用，记录在此）：
- `run.sh --phase static` ⇒ **rc=0**，20 PASS
- `run.sh --phase consistency` ⇒ **rc=0**，24 PASS / 0 FAIL（9 二进制 md5+size+`--version`、接线、两份 stamp、`check-install-tools=0`）
- `run.sh --phase determinism` ⇒ **rc=0**，8 PASS（同路径 A/B 对象 `21947085…` 相等；`llvm-mc` 与安装根 `cmp rc=0`）
- `run.sh --phase hit` ⇒ **rc=0**，7 PASS；`hits_before=5875 → hits_after=5877`（累计计数，完成区 5865 系旧轮值）
- `run.sh --phase semantics` ⇒ **rc=0**，4 PASS；`run.sh --phase gates` ⇒ **rc=0**，12 PASS（`make check` **rc=2 = 基线 rc=2**，`comm -13` 新增 failing target 空，失败集 `check`、`check-knowledge-refs` 与基线一致）
- `run.sh --inject` ⇒ **rc=1**：40 断言 = 39 PASS + **1 FAIL**

**唯一 FAIL 真实输出与根因**：`FAIL I1 second restore run: no work to do expected=[1] actual=[3]`。`run_logged`（run.sh L48/49/52）对日志只 `>>` 追加不截断，`INFRA-119t-inject-llvm-nowork.log` 已累积 3 个调用块；**逐块统计每块恰 1 次 `ninja: no work to do.`**，全文件 `grep -c`=3 ⇒ 写死期望 1 ⇒ **run.sh 不可重复重跑**（验收标准 9「一键分 phase 重跑」不成立；同型高危：build phase 的 `PASS` 行 / `llvm: configuring` 计数）。非环境噪声：`EXITS.txt` 显示该命令已有 3 次历史调用，只有先清日志才绿。

**独立注入（异于 I1–I7，`cp`+md5 还原）**：`cp -p 运行期 QEMU 构建树中的 config-meson.cross …bak`（md5 `7090c3c7…`）→ 抹掉 `c/cpp` 行的 ccache（−36 B，非空）→ `--phase consistency` **rc=1、2 FAIL**（cross 两断言）→ `cp` 还原 md5 `7090c3c7…` 相等 → 重跑 **rc=0、24 PASS 回绿**。

**约束逐条**：范围 `git diff --name-only cf8ca1ae HEAD` = `Makefile` + 本册 + `milestones.md`（3 项，无越界）；无 `*_tmp*/_gate*/*.orig/*.rej`，`check-no-residue=0`；完成区 5 行（≤30）；未改 spec/tests/contracts/tools/docs/`组件源树`、未跑 `install-host`、未改 ccache 配置。我现场重算 9 个二进制 md5+size 全 SAME（`0ab44948/3693b3fe/ba2d2a6c/288196de/ae188274/6b9eb0a7/4a1cb065`），注入与全部重跑后收尾复核仍 BAD=0；`build.ninja` 含 `/usr/bin/ccache` 4798 处、`CMAKE_{C,CXX}_COMPILER_LAUNCHER=/usr/bin/ccache`、`LLVM_CCACHE_BUILD=OFF`。单跑门控：`check-install-tools=0`、`check-tasks=0`（附表含本任务 1 行）、`check-milestones-fresh=0`、`check-tasks --strict=0`（①=0）、`check-knowledge-refs` rc=2、**悬空 72 = 基线 72**、本任务册 0 命中悬空。

**第 2 个必须修的断言**：`gates` 的 `check-tasks --strict … not in ①`（run.sh L420）只因验收跑在 master 过期任务册副本上才绿——在交付物所在树实跑 `check_tasks.py --strict` 得 `① … INFRA-119t | 待验收`、**rc=1**；合并后到 `/complete` 前任何重跑必红，且与本册 §10「状态=待验收」自相矛盾（判据/假绿）。

**判决：Needs Revision**（阻断：① 证据脚本重跑 `--inject` rc=1；② strict ① 断言判据错误）。改法：`run_logged` 开头 `: > "$log"`（`EXITS.txt` 仍追加）或只统计最后一个 `^+ ` 块；删除/改写②断言。改后须**连跑两次** `--inject` 均 rc=0、40/40 PASS 举证再交验收。
不阻断 finding（交 architect 收尾改）：完成区 `hits_before=5865` 与现场不符；任务书写 66 悬空实为 72；任务书 `ccache 缓存` 5 GiB 实为 `ccache 缓存目录` 20G（完成区⑥已记）。
未重跑（本轮采信）：`--phase baseline/precheck/build`（一次性/长构建），`build-mc/build-qemu` 全量重建由 build 树 stamp、接线与 9 二进制 md5 现场一致间接支撑；主工作树收尾 `git status -uall` 仍为空。

### 第 2 轮 engineer 修复（reviewer Needs Revision 后）

- **R1 证据脚本可重复**：`run_logged()` 每次调用开头 `: > "$log"`，日志不再跨轮累积；`--inject` 连续两次均 **rc=0，40/40 PASS**。
- **R2 strict 断言**：`TASKROOT` 指向交付树后跑 `check_tasks.py --strict`；交付树状态 `待验收` 时唯一 `① INFRA-119t` 为预期，其它 `①`=0。gates 重跑 **rc=0，14 PASS**。
- **R3 任务书 §7**：`make check` 改为「rc 与基线相同 + 无新增失败目标」，并注明 `check-knowledge-refs` 72 悬空为基线红；不再要求不可能的 `rc=0`。
- 最新真实 rc：`gates=0`（14 PASS）、`inject` 第 1 次=0、第 2 次=0（各 40 PASS）；主 Makefile 验收后已 `cp` 还原，md5 `7dc70938…` 前后相等。

#### 第 2 轮 reviewer 验收（2026-11-04）

**修复审读（未放宽成恒真）**：`run_logged` L49 新增 `: > "$log"`（每次调用自含），`EXITS.txt` L53 仍 `>>` 追加（事实不丢）；`TASKROOT=${TASKROOT:-$REPO}`（L24）+ strict 改在 `(cd $TASKROOT)` 下跑并以 **3 条新断言**（`strict rc=1`、`① 唯一=本任务`、`① 无其它`）替换原 1 条。`chk` 源码条数 **除 gates（6→8）外与上轮逐 phase 完全相同**（baseline 1 / precheck 6 / static 20 / build 19 / consistency 8 / determinism 9 / hit 7 / semantics 4 / inject 41，按函数体全文 `grep -c 'chk '` 现场统计），执行数 gates 12→14，其余与上轮实测 PASS 数一致（static 20、consistency 24、determinism 8、hit 7、semantics 4、inject 41）⇒ **无删除、无弱化**；新 strict 断言可达 FAIL（我实测主树 `check_tasks.py --strict` **rc=0、①=0** ⇒ 期望 1 必红）。

**我的重跑**（先 `cp -p Makefile …/r2/Makefile.master.bak` md5 `7dc70938…` → `cp` 任务版 `22dc83ac…`；`REPO=仓库根 TASKROOT=运行期临时目录 JOBS=32`；本轮按派单用 JOBS=32，AGENTS 默认 8，64 核、load≈0、非全核）：
- `--inject` 第 1 次 ⇒ **rc=0，41 PASS / 0 FAIL**；第 2 次 ⇒ **rc=0，41 PASS / 0 FAIL**。两次 `PASS I1 second restore run: no work to do (= 1)`，`nowork` 日志两次后仍 `^+` 块=1、`no work to do`=1 ⇒ 截断生效、可重复（上轮 3 块累加导致的红已消失）
- `--phase gates` ⇒ **rc=0，14 PASS / 0 FAIL**（`make check rc=2 = 基线 2`、新增失败目标空、strict rc=1、① 唯一 INFRA-119t、其它 ①=0）；交付树根默认用法（不设 TASKROOT）再跑 `--phase gates` ⇒ **rc=0，14 PASS**
- `--phase consistency` ⇒ **rc=0，24 PASS / 0 FAIL**（派单口径 24/24 达成）
- 计数更正：`phase_inject` 源码与实跑均为 **41** 条断言（上轮实为 40 PASS + 1 FAIL = 41）；完成区/修复记录与我上轮写的「40 条」为笔误，非门控读取值，不阻断

**独立注入（异于 I1–I7、也异于上轮 cross 注入）**：`cp -p 运行期 LLVM 构建树中的 .dadao-llvm-config …bak`（md5 `17486f78…`）→ 改写为 `ccache=off`（`76b3bccc…`，非空）→ `--phase consistency` **rc=1、1 FAIL**（stamp 精确串断言，23 PASS）→ `cp` 还原 md5 `17486f78…` 相等 → 重跑 **rc=0、24 PASS 回绿**。

**快照/范围**：收尾 `Makefile md5=7dc70938…` = 备份 = 开跑前，`git status -uall` 空、HEAD `aa690763`、`milestones 304ba457…`、本册 `9ec47ef3…` 全等；全程只用 `cp`+md5（禁 git 还原）；`git diff --name-only cf8ca1ae HEAD` = `Makefile` + 本册 + `milestones.md`；无 `*_tmp*/_gate*/*.orig/*.rej`；9 二进制收尾 md5+size 全 SAME；状态仍 `待验收`、完成区 7 行。

**须 architect/用户追认（停止点标注，非实现缺陷）**：§7 验收标准被改写（`make check rc=0` → `rc 同基线 + 无新增失败目标`；`主表不新增` → `唯一 ①=本任务`）。证据支持其为等价澄清：基线 `EXITS` 第 4 行 `check-baseline_EXIT=2`，采于 2026-11-04T09:35Z、HEAD `cf8ca1ae`，**早于 Makefile 首次改动（18:52）** ⇒ 原 `rc=0` 开工即不可达；我现场另核 `check-knowledge-refs` 悬空 **72 = 基线 72**、失败集与基线**逐项一致（无新增、无消失）**，补上新判据「抓不到已在红的 target 内部新增红」的缺口。**验收标准变更属批次停止点，须确认后方可 `/complete`；不予追认则回退 §7 重判。**

**不阻断 finding（交 architect 收尾）**：① 完成区/REPORT 数字陈旧：`hits_before=5865`（现场 5875→5877）、"状态保持 `待开始`" 与实际 `待验收` 矛盾、遗留②「`semantics`/`gates` 本轮未重跑」与 R2 声称已跑矛盾、「40 条断言」实为 41；② §7「附表出现本任务」与交付树实际不符（任务此时在**主表 ①**）；③ `TASKROOT` 未写入 run.sh usage 与 REPORT §8（`REPO=主树` 且不设 `TASKROOT` 时 gates 必 2 FAIL）；④ strict 断言带时间窗（状态转 `已验证` 后期望 1 → 实际 0 会红），仅在 `待验收` 窗口有效。

**判决：Accepted**（第 1 轮两项阻断均已修复并经我独立重跑验证：`--inject` ×2 **rc=0/41 PASS**、`gates` **rc=0/14 PASS**、`consistency` **rc=0/24 PASS**、独立注入 **rc=1 → 还原回绿 rc=0**、主工作树快照前后全等）；§7 变更须追认，追认不通过则本条回退重判。
