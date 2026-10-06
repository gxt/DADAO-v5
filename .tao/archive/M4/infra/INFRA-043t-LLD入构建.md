# INFRA-043t: LLD 入构建目标

**模块**：infra
**项目里程碑**：M4
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：`Makefile` 现有 LLVM 构建设施；`.work/source/llvm-project`（已 `make prepare`，含 `lld/` 源码树，`lld/ELF/Arch/` 已有 RISCV/PPC64/SystemZ 等 target）。
- **输出**：`Makefile` 新增构建入口，产出 **`ld.lld`**（`.work/build/llvm/bin/ld.lld`）+ 构建证据。
- **约束**：
  - **现状事实（实测）**：`Makefile` 的 `build-mc`/`build-mc-reconfig` 用 `cmake -DLLVM_ENABLE_PROJECTS=""`（**不含 `lld`**）配置 `.work/build/llvm`；`build-mc` 在 `build.ninja` 已存在时**跳过 cmake**（增量快路径）。因此启用 `lld` **必须**改 `LLVM_ENABLE_PROJECTS`（含 `lld`）并重跑 cmake。
  - **改动最小**：优先新增独立目标 `build-lld`（与 `build-mc` 同风格：`manifest-check` + `component-enabled,llvm-project` 前置；`-DLLVM_TARGETS_TO_BUILD=DADAO -DLLVM_ENABLE_PROJECTS=lld`；`ninja ld.lld`）；**不得**擅自改变 `build-mc` 的既有语义/产物，以免 M3 `test-codegen` 回归。若实现选择扩展 `build-mc`，须说明并保证不回归。
  - 由于 `build.ninja` 的 `LLVM_ENABLE_PROJECTS` 不同，**须评估**是否需要独立构建目录或强制 reconfig；若复用同一 `.work/build/llvm`，须在任务书/完成区说明对 `build-mc` 增量路径的影响并验证不回归。
  - 并行度受 `JOBS`（默认 8）限制，**禁止** `-j$(nproc)`；LLD 构建预计 **5–20 分钟**（`lld` + 其 `LLVM` 依赖；具体以实测为准）——**开始前在回复写明预计耗时**。
  - **不伪造成功**：目标须真实构建 `ld.lld`；失败即停、不自动重试。
  - 不改组件源码、不改 `components/**` 补丁集（LLD target 代码由 `LLVM-056t` 负责）。
  - 临时目录 `/tmp/opencode/INFRA-043t/`；**不提交 git**。

## 验收标准

1. 新目标（如 `make build-lld`）EXIT=0；`.work/build/llvm/bin/ld.lld` 存在、可执行，且 `ld.lld --version` EXIT=0（输出含 `LLD`）。
2. `make build-mc` 原行为**不回归**（`llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj`/`FileCheck`/`not`/`llc` 仍产出或报告 `no work to do`）。
3. `make check-no-residue` EXIT=0；`git status --untracked-files=all` 仅 `Makefile` + 本任务书。
4. 一键证据脚本 `.work/evidence/INFRA-043t/run.sh`：非交互；任一失败非零退出；逐项打印「检查名/期望/实际/rc」；内置注入自检（临时隐藏/改名 `ld.lld` → 检查 FAIL → 还原 → 回绿；结尾**不得**用 `tee` 吞退出码）；完成区贴真实输出。

## 完成区

**测试结果**：通过 4/4 验收项。
- 验收1（`make build-lld`）：EXIT=0，耗时 272s（cmake 重配置 + 增量构建 `lld` 及其 LLVM 依赖，未全量重建）；`.work/build/llvm/bin/ld.lld` 存在且可执行（`ld.lld -> lld` 符号链接）；`ld.lld --version` EXIT=0，输出含 `LLD`。
- 验收2（`make build-mc` 不回归）：EXIT=0；7 个工具（`llvm-mc`/`llvm-objdump`/`llvm-objcopy`/`llvm-readobj`/`FileCheck`/`not`/`llc`）均存在可执行。**附加**：`make check-lit` EXIT=0（MC+E2E 50/50）；`make test-codegen` EXIT=0（15/15，M3 CodeGen 门控）。
- 验收3（残留/git）：`make check-no-residue` EXIT=0；`git status --untracked-files=all` 仅 `M Makefile`（填完成区后另加本任务书）。
- 验收4（一键证据）：`.work/evidence/INFRA-043t/run.sh` EXIT=0，17 项检查全 PASS，含内置注入（隐藏 `ld.lld` → 检查 FAIL → 还原 → 回绿）。

**修改文件**：
- `Makefile`（唯一改动；+34/-1）：
  - `.PHONY` 增加 `build-lld`；
  - `help` 增加一行；
  - 新增 `LLD_TARGETS = lld` 与 `build-lld: manifest-check` 目标（`component-enabled,llvm-project` 前置 → `cmake -DLLVM_TARGETS_TO_BUILD=DADAO -DLLVM_ENABLE_PROJECTS=lld …` → `ninja -j$(JOBS) … lld`）。
  - **未改动** `build-mc`/`build-mc-lite`/`build-mc-reconfig` 的语义与产物。
- 非提交物（`.work/` gitignored）：`.work/evidence/INFRA-043t/run.sh`（一键证据脚本，随产物保留在 `.work/`）；日志 `.work/log/infra/INFRA-043t-*.log`。

**验收结果**（真实输出，命令均 `cmd > log 2>&1; rc=$?; echo EXIT=$rc`，无 `tee`）：

1) `make build-lld`（`.work/log/infra/INFRA-043t-build-lld.log` 末）：
```
[151/152] Linking CXX static library lib/liblldWasm.a
[152/152] Linking CXX executable bin/lld
build-lld: PASS
EXIT=0 ELAPSED=272s
```
2) `ld.lld --version`（`.work/log/infra/INFRA-043t-ldlld-version.log`）：
```
LLD 23.1.1 (/mnt/tao/DADAO-v5/.cache/llvm-project.git c9b87ba1ad110d70db9560e57b6a7f375b168f9f) (compatible with GNU linkers)
EXIT=0
```
3) `make build-mc`（`.work/log/infra/INFRA-043t-build-mc-after-lld.log`）：
```
ninja: Entering directory `.work/build/llvm'
[1/2] Linking CXX executable bin/llvm-mc
[2/2] Linking CXX executable bin/llvm-objdump
build-mc: PASS
EXIT=0 ELAPSED=12s
```
工具存在性：`OK llvm-mc/llvm-objdump/llvm-objcopy/llvm-readobj/FileCheck/not/llc/ld.lld`。
4) 一键证据 `.work/evidence/INFRA-043t/run.sh`（`.work/log/infra/INFRA-043t-evidence.log`）：
```
make build-lld                             | expected=rc=0 | actual=... | rc=0 | PASS
ld.lld artifact (.../bin/ld.lld)           | expected=executable | actual=executable | rc=0 | PASS
ld.lld --version                           | expected=rc=0 & contains LLD | actual=rc=0 has_LLD=yes :: LLD 23.1.1 ... | rc=0 | PASS
make build-mc (no regression)              | expected=rc=0 | rc=0 | PASS
build-mc tool llvm-mc/objdump/objcopy/readobj/FileCheck/not/llc | present+executable | present | rc=0 | PASS (×7)
make check-no-residue                      | expected=rc=0 | rc=0 | PASS
inject: ld.lld hidden                      | expected=absent & backup exists | absent=yes backup=yes | rc=0 | PASS
inject: artifact check FAILs               | expected=not executable | missing/not-executable | rc=0 | PASS
inject: restored (backup gone)             | expected=no leftover backup | backup=gone | rc=0 | PASS
inject: artifact check green again         | expected=executable | executable | rc=0 | PASS
=== result: 0 failure(s) ===
EVIDENCE: PASS
SCRIPT_EXIT=0
```
5) 独立产品级注入（验证证据脚本主检查的 FAIL 路径真实可达）：
```
$ sed -i 's/^LLD_TARGETS = lld$/LLD_TARGETS = lld-nonexistent-target/' Makefile   # 注入
$ git diff --name-only → Makefile                       # 注入非空
$ make build-lld   → ninja: error: unknown target 'lld-nonexistent-target'; make: *** Error 1
INJECTED_EXIT=2
$ cp .../Makefile.orig Makefile                          # 还原
$ make build-lld   → ninja: no work to do. / build-lld: PASS
RESTORED_EXIT=0
```
6) 残留：`make check-no-residue` → `EXIT=0` / `check-no-residue: PASS`；`git status --untracked-files=all --short` → ` M Makefile`。

**设计说明（独立构建目录 vs 复用）**：选择**复用** `.work/build/llvm` + **每次强制 cmake**（不做 `build.ninja` 快路径）。理由：
- 独立构建目录需从零编译 LLVM 核心库（远超任务预算 5–20 min，实测复用增量仅 272s），故否决。
- 复用同一目录时，启用 `lld` 必须切换 `LLVM_ENABLE_PROJECTS=lld`，而 `build.ninja` 快路径会保留旧的 `LLVM_ENABLE_PROJECTS=""` 配置、导致 `lld` 目标不可用，故 `build-lld` **不得**用 `build.ninja` 存在性做跳过判据（已在 Makefile 注释说明）。
- 对 `build-mc` 增量路径的影响：reconfigure 后 `build.ninja` 已含 `lld`，`build-mc` 仍走快路径（跳过 cmake）且其目标照常构建（实测 EXIT=0；lit 50/50、test-codegen 15/15 无回归）；`build-mc-reconfig` 可用 `LLVM_ENABLE_PROJECTS=""` 还原 lld-less 配置（还原后再跑 `build-lld` 会重新启用 lld）。
- **与任务书 `ninja ld.lld` 的偏差**：实测 `ninja -t targets` 中**无** `bin/ld.lld:` 目标（`ld.lld` 由 `add_lld_symlink → ALWAYS_GENERATE` 作为 `lld` 的 POST_BUILD 拷贝生成），有效目标为 `lld`（`lld: phony`）；故用 `ninja … lld`，产物仍为 `bin/ld.lld`。

**新发现/坑**：
1. `lld` 的 `ninja` 目标名是 `lld`，**不是** `ld.lld`：`lld/CMakeLists.txt` 用 `add_lld_symlink`（`ALWAYS_GENERATE`）把 `ld.lld` 等名字做成 `lld` 可执行体的 POST_BUILD 拷贝，ninja 无独立 `ld.lld` 目标。
2. LLVM `build.ninja` 的 `LLVM_ENABLE_PROJECTS` 是**构建目录级**配置：同一 `.work/build/llvm` 无法同时以空 projects 与 `lld` 配置；启用子项目必须重跑 cmake；`build-mc` 的「build.ninja 存在即跳过 cmake」快路径对该场景不适用。
3. 复用构建目录 reconfigure 后，`build-mc` 会重新链接 `llvm-mc`/`llvm-objdump`（2 步），属正常增量、非回归。

**遗留问题**：无。（`test-codegen`/`check-lit` 为附加非回归证据，非任务书验收项；均通过。）

## 审阅记录

#### 第 1 轮 engineer 自审

改动仅 `Makefile`（+34/-1，新增 `build-lld` 目标与 `LLD_TARGETS`，加 `.PHONY`/help），未触碰组件源码、补丁集或既有目标语义。交付物：`.work/evidence/INFRA-043t/run.sh`（非提交物）。逐行审查：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 任务书建议 `ninja ld.lld`，但该 ninja 目标不存在（`ld.lld` 为 `lld` 的 POST_BUILD 拷贝） | ✅已修 | 目标改用 `ninja … lld`（`LLD_TARGETS = lld`），注释说明原因 | `ninja -C .work/build/llvm -t targets all`：有 `bin/lld:` 与 `lld: phony`，`bin/ld.lld:` 计数 0；构建产出 `bin/ld.lld -> lld`，`ld.lld --version` EXIT=0 |
| F2 复用共享构建目录是否回归 `build-mc`/M3 | ✅已验 | 无（未改 build-mc） | `make build-mc` EXIT=0；`make check-lit` EXIT=0（50/50）；`make test-codegen` EXIT=0（15/15） |
| F3 `build-lld` 不能沿用 `build.ninja` 快路径，否则切不回 lld 配置 | ✅设计确认 | 采用每次 `cmake` 强制重配置；Makefile 注释写明 | `make build-lld` 两次均 EXIT=0；`CMakeCache.txt` 显示 `LLVM_ENABLE_PROJECTS=lld` |
| F4 证据脚本 `report … "$(artifact_actual)" "$?"` 中 `$?` 可能被命令替换覆盖 | ✅已修 | 改为先 `artifact_rc; a_rc=$?` 再传 `$a_rc`（2 处） | 重跑脚本：`ld.lld artifact` / `inject: green again` 两行 rc 判定正确、全 PASS |
| F5 证据脚本「能失败」未独立验证 | ✅已验 | 新增产品级注入步骤（临时改 Makefile 目标名） | 注入后 `git diff --name-only=Makefile`；`make build-lld` → `unknown target 'lld-nonexistent-target'`，`INJECTED_EXIT=2`；还原后 `RESTORED_EXIT=0`、`git status` 仅 `M Makefile` |
| F6 边界：component 未启用时是否伪造成功 | ✅保持 | 沿用 `component-enabled,llvm-project` 前置，未启用则 `exit 1` | 与 `build-mc` 同款守卫（`make -n` 显示守卫命令） |

**判决**：全部 finding 已处置（✅），无未修项；验收 1–4 均有真实输出。
**注**：本任务无用户裁定需落盘（未向用户提问）。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查时间**：2026-10-06

##### 一、证据脚本审核（`.work/evidence/INFRA-043t/run.sh`）

逐行审查结果：

| 检查项 | 结果 | 说明 |
|--------|------|------|
| FAIL 路径 | ✅ | `report()` 函数：`rc != 0` → `verdict=FAIL` + `FAILS++`；结尾 `FAILS != 0` → `exit 1`。每条检查有独立 rc 判定 |
| 恒真断言 | ✅无 | 每条 `report` 的 expected/actual 不同；注入自检 4 条各有独立判定逻辑（隐藏/FAIL/还原/回绿） |
| 注入非空可还原 | ✅ | `mv "$LLD" "$inj_bak"` 确保非空（检查 `[ ! -e "$LLD" ] && [ -e "$inj_bak" ]`）；`restore_injection()` 还原 + `trap restore_injection EXIT` 安全网 |
| 结尾无 `tee` | ✅ | 最后 5 行：`echo` + `if` + `exit`，无管道 |
| `$?` 捕获 | ✅ | `artifact_rc; a_rc=$?` 模式（2 处），先取码再传参 |

脚本合格，无需修改。

##### 二、独立重跑证据脚本

```
$ bash .work/evidence/INFRA-043t/run.sh > /tmp/opencode/INFRA-043t-review/evidence-run.log 2>&1; rc=$?; echo "SCRIPT_EXIT=$rc"
SCRIPT_EXIT=0
```

完整输出（17/17 PASS）：

```
=== INFRA-043t evidence (repo: /mnt/tao/DADAO-v5) ===
make build-lld                             | expected=rc=0                     | actual=see ...evidence-build-lld.log     | rc=0 | PASS
ld.lld artifact (.../bin/ld.lld)           | expected=executable               | actual=executable                        | rc=0 | PASS
ld.lld --version                           | expected=rc=0 & contains LLD      | actual=rc=0 has_LLD=yes :: LLD 23.1.1 … | rc=0 | PASS
make build-mc (no regression)              | expected=rc=0                     | actual=see ...evidence-build-mc.log      | rc=0 | PASS
build-mc tool llvm-mc                      | expected=present+executable       | actual=present                           | rc=0 | PASS
build-mc tool llvm-objdump                 | expected=present+executable       | actual=present                           | rc=0 | PASS
build-mc tool llvm-objcopy                 | expected=present+executable       | actual=present                           | rc=0 | PASS
build-mc tool llvm-readobj                 | expected=present+executable       | actual=present                           | rc=0 | PASS
build-mc tool FileCheck                    | expected=present+executable       | actual=present                           | rc=0 | PASS
build-mc tool not                          | expected=present+executable       | actual=present                           | rc=0 | PASS
build-mc tool llc                          | expected=present+executable       | actual=present                           | rc=0 | PASS
make check-no-residue                      | expected=rc=0                     | actual=see ...check-no-residue.log       | rc=0 | PASS
--- injection self-check (hide ld.lld -> expected FAIL -> restore) ---
inject: ld.lld hidden                      | expected=absent & backup exists   | actual=absent=yes backup=yes             | rc=0 | PASS
inject: artifact check FAILs               | expected=not executable           | actual=missing/not-executable            | rc=0 | PASS
inject: restored (backup gone)             | expected=no leftover backup       | actual=backup=gone                       | rc=0 | PASS
inject: artifact check green again         | expected=executable               | actual=executable                        | rc=0 | PASS
=== result: 0 failure(s) ===
EVIDENCE: PASS
```

##### 三、独立注入验证

**注入方式**：修改 `Makefile` 的 `build-lld` 目标中 `-DLLVM_ENABLE_PROJECTS=lld` → `-DLLVM_ENABLE_PROJECTS=NONEXISTENT_REVIEWER_INJECT`（与 engineer 的 `LLD_TARGETS=lld-nonexistent` 不同——我改的是 cmake 选项而非 ninja 目标变量）。

**注入**：
```
$ sed -i 's/-DLLVM_ENABLE_PROJECTS=lld/-DLLVM_ENABLE_PROJECTS=NONEXISTENT_REVIEWER_INJECT/' Makefile
$ git diff --name-only
Makefile                         ← 注入非空 ✓
```

**注入后 `make build-lld`**：
```
$ make build-lld > /tmp/opencode/INFRA-043t-review/injected-build.log 2>&1; rc=$?; echo "INJECTED_EXIT=$rc"
INJECTED_EXIT=2
```
错误信息：`CMake Error at CMakeLists.txt:165 (MESSAGE): NONEXISTENT_REVIEWER_INJECT isn't a known project` ✓

**还原**：
```
$ cp /tmp/opencode/INFRA-043t-review/Makefile.bak Makefile
$ git diff Makefile | head -5     ← 与 engineer 版本一致
```

**还原后重建**（cmake 缓存被污染，需重跑 `make build-lld` 恢复，~3 分钟）：
```
$ make build-lld > .../restored-build.log 2>&1; rc=$?; echo "RESTORED_EXIT=$rc"
RESTORED_EXIT=0
```

**还原后验证**：
```
$ grep 'LLVM_ENABLE_PROJECTS:STRING' .work/build/llvm/CMakeCache.txt
LLVM_ENABLE_PROJECTS:STRING=lld                    ← 正确恢复 ✓
$ .work/build/llvm/bin/ld.lld --version
LLD 23.1.1 (...) (compatible with GNU linkers)     ← 仍可用 ✓
```

##### 四、独立复核逐项

| 验收项 | 命令 | 真实输出/退出码 | 结果 |
|--------|------|----------------|------|
| `make build-lld` EXIT=0 | `make build-lld`（重跑） | `build-lld: PASS` / EXIT=0 | ✅ |
| `ld.lld` 存在可执行 | `file .work/build/llvm/bin/ld.lld` | `symbolic link to lld` | ✅ |
| `ld.lld --version` 含 LLD | 独立执行 | `LLD 23.1.1 …` / EXIT=0 | ✅ |
| `make build-mc` 不回归 | `make build-mc` | `ninja: no work to do.` / EXIT=0 | ✅ |
| 7 工具存在 | `for t in …; [ -x … ]; done` | 全部 OK | ✅ |
| `check-no-residue` EXIT=0 | `make check-no-residue` | EXIT=0 | ✅ |
| `git status` 仅 Makefile + 任务书 | `git status --untracked-files=all --short` | ` M Makefile` + ` M .tao/tasks/infra/INFRA-043t-…` | ✅ |
| `git diff` 只新增 build-lld | `git diff Makefile` | `.PHONY` 加 `build-lld` + help 行 + 新增目标块；**未动** `build-mc`/`build-mc-lite`/`build-mc-reconfig` | ✅ |

##### 五、偏差/决策判定

| 偏差/决策 | 判定 | 说明 |
|-----------|------|------|
| `ninja ld.lld` 无效 → 用 `ninja … lld` | ✅合理且已充分披露 | `lld/CMakeLists.txt` 用 `add_lld_symlink(ALWAYS_GENERATE)` 做 POST_BUILD 拷贝，ninja 无独立 `ld.lld` 目标。完成区有 `ninja -t targets` 证据。Makefile 注释也写明。 |
| 复用 `.work/build/llvm` + 每次强制 cmake | ✅合理 | 独立构建目录需全量编译 LLVM（远超 5-20 min 预算）；强制 cmake 确保 `LLVM_ENABLE_PROJECTS` 切换正确。`build-mc` 增量路径不受影响（实测 `no work to do`）。 |
| `build-mc-reconfig` 可还原 lld-less 配置 | ✅已披露 | 完成区说明了双向切换路径。 |
| 遗留 | 无 | 无遗留问题。 |

##### 六、判决

**Accepted**。

全部 4 项验收标准通过（独立重跑 + 独立注入均确认）。证据脚本合格（FAIL 路径可达、注入非空可还原、无恒真断言、结尾无 `tee`）。Makefile 改动最小（仅新增 `build-lld`，未动既有目标）。`ninja ld.lld → lld` 偏差合理且已充分披露。无遗留。
