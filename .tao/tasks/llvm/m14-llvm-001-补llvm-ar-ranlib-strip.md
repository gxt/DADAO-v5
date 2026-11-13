# m14-llvm-001: 补 LLVM 工具族（`llvm-ar`/`llvm-ranlib`/`llvm-strip` + `llvm-link`/`llvm-config`/`llvm-profdata`/`llvm-size`/`llvm-cov`）

**模块**：llvm
**项目里程碑**：M14
**依赖**：`m14-infra-001`（缺口登记与本任务同一对象：它只登记、本任务修缺口）；与**同改 `Makefile`** 的其它任务串行（`m14-infra-001`/`m14-infra-003` 均声明不改 `Makefile`，本任务占写锁）
**可并行分片**：否（单一 `Makefile` 安装集 + 单一脚本断言；构建/安装为整树串行操作）
**预估**：4–6 h（含增量构建 + 一次 `install-host` 重拷 + 证据）
**状态**：已验证

## 执行环境
**执行环境**：本地（需本机 LLVM 构建树与安装根；`build-mc`/`install-host` 属长任务，启动前申报预计耗时）

## 背景

- **实测缺口（`m14-infra-001` 登记，2026-11-13）**：构建树 `bin/` 只有 25 个条目，**没有** `llvm-ar`/`llvm-ranlib`/`llvm-strip`；安装根同样没有。现有规避：`AR=<GNU ar>`、`RANLIB=<GNU ranlib>`、`STRIP=<安装根 llvm-objcopy> --strip-all`（GNU `strip` 不认 `e_machine=0xDA0` 大端 ELF）。
- **用户 2026-11-13 裁定（经主会话转达）**：**先补工具链**，不长期用规避法。
- **架构师只读核对结论（engineer 须现场复核，完成区贴命令 + rc）**：
  1. `LLVM_BUILD_TOOLS:BOOL=ON`（cmake cache 现场值），`llvm/tools/CMakeLists.txt` 无条件 `add_llvm_tool_subdirectory(llvm-ar)` ⇒ **cmake 侧已包含**，缺的是**显式 ninja 目标选择**：`Makefile` 的 `LLVM_MC_FULL_TARGETS` 未列这三项，而本仓库只构建列出的目标（不跑 `all`）；`LLVM_INSTALL_UTILS` 不适用（本仓库不跑 `ninja install`，由 `install-host` 手工装）。
  2. 上游形态（源码只读）：`llvm/tools/llvm-ar/CMakeLists.txt` 为 `add_llvm_tool(llvm-ar …)` + `add_llvm_tool_symlink(llvm-ranlib llvm-ar)`；`llvm/tools/llvm-objcopy/CMakeLists.txt` 为 `add_llvm_tool_symlink(llvm-strip llvm-objcopy)` ⇒ **只有 `llvm-ar` 是独立可执行文件**，另两个是相对符号链接，行为由 `argv[0]` 分派。
  3. `ninja -C $(LLVM_BUILD) -n llvm-ar llvm-ranlib llvm-strip` 现场返回 8 步、**无 cmake 重配步骤** ⇒ 补目标不需要 `build-mc-reconfig`，也不改构建配置戳记。
- **同仓先例**：`INFRA-098t`（`llvm-nm`/`llvm-readelf` 入构建目标 + 安装集，相对符号链接走 `HOST_LLVM_TOOL_SYMLINKS`）——本任务按同一形态补三项即可，不新造机制。

## 目标

1. 构建目标 + 安装集补齐**用户 2026-11-13 裁定的全套**：
   - **必需**（内核构建直接用）：`llvm-ar`（实副本）、`llvm-ranlib`（`argv[0]` 符号链接）、`llvm-strip`（符号链接到 `llvm-objcopy`）；
   - **同批补齐**（用户裁定 A）：`llvm-link`、`llvm-config`、`llvm-profdata`、`llvm-size`、`llvm-cov`——同样走 `LLVM_MC_FULL_TARGETS` + `HOST_LLVM_TOOLS`（符号链接按上游 `add_llvm_tool_symlink` 形态），`check_install_tools.py` 一并断言；
2. 安装集断言由「Makefile 变量」自动扩展（脚本**不得**另立第二份清单），并对三项增加**在 DADAO 大端 ELF 上可用**的功能断言；
3. 给 `m14-linux-002` / `m14-infra-001` 可消费的结论（`AR`/`RANLIB`/`STRIP` 改为 `llvm-*`；矩阵三行 `present`）。

## 接口规范

**输入**：`Makefile`（`LLVM_MC_FULL_TARGETS`/`HOST_LLVM_TOOLS`/`HOST_LLVM_TOOL_SYMLINKS`/`install-host`/`build-mc`）、`tools/infra/check_install_tools.py`、本机构建树与安装根。

**输出（`Makefile` 只增不改，既有项顺序不动）**：

1. `LLVM_MC_FULL_TARGETS` 追加 `llvm-ar llvm-ranlib llvm-strip`（三个都要列：两个符号链接也各有自己的 ninja 目标）；**`LLVM_MC_LITE_TARGETS` 不变**（lite = 最小 MC 集，不因本任务变宽）。
2. `HOST_LLVM_TOOLS` 追加 `llvm-ar`（真实副本，`atomic-install`）。
3. `HOST_LLVM_TOOL_SYMLINKS` 追加 `llvm-ranlib:llvm-ar llvm-strip:llvm-objcopy`（**相对符号链接**、零拷贝；`llvm-objcopy` 已在安装集内）。
4. 相邻注释更新（`Makefile` 现有 503–516 与 640–650 段）：写明三者上游形态（`add_llvm_tool_symlink`）、**`argv[0]` 分派**、以及为何 `llvm-ranlib`/`llvm-strip` **不得**走 `atomic-install`（`cp -aL` 解引用 ⇒ 数百 MB 重复副本 + 破坏“别名同源”断言）。

**输出（`tools/infra/check_install_tools.py`）**：

5. 三项“存在 + 可执行 + `--version` rc=0 + 尺寸==构建树”断言**沿用变量驱动**，不复制清单；两个别名另得“相对符号链接 + 目标可执行 + 同源”断言（已有逻辑自动覆盖）。
6. 新增**功能断言组**（每条一行 `[PASS]/[FAIL]`，仿既有 `check_elf_probe` 的 `llvm-readelf -h` 探针风格；探针沿用 `ELF_PROBE_REL`，**缺失 ⇒ SKIP**，不阻断无 musl 的新克隆；所有中间产物在 `/tmp/opencode/check-install-tools/` 下 `mkdtemp`，`finally` 删除）：
   - `llvm-ar` 往返：探针对象复制成 2 个成员 → `llvm-ar rcs` 建归档 → `llvm-ar t` 成员集合相等 → `llvm-ar x` 解出成员与原件逐字节一致（md5/sha256 相等）；任一不符 ⇒ FAIL。
   - `llvm-ranlib` 索引：`llvm-ar rc`（**不带 `s`**）建档 → `llvm-nm -s` 无索引段 → `llvm-ranlib` rc=0 → `llvm-nm -s` 出现索引段且成员仍可列出；前后无差异或 rc≠0 ⇒ FAIL（具体文本以现场输出为准，证据须贴前后两段原文）。
   - `llvm-strip`：探针对象副本 → `llvm-strip --strip-all` rc=0 → `llvm-readelf -h` 仍为 `Data: … big endian` + `Machine: da0`（`e_machine` 不变）→ `llvm-objdump -d` rc=0 且反汇编非空；输入不是大端 DADAO 或任一失败 ⇒ FAIL。
7. `--self-test` 增 **≥2 路**针对上述功能断言的可达 FAIL（假工具按 `basename` 分派：`llvm-ar`/`llvm-ranlib`/`llvm-strip` 各自的绿基线 + 各自注入；例如归档丢成员、`llvm-strip` rc≠0、ranlib 不写索引），基线仍绿、注入必红、`cp`+md5 还原。既有 5 类注入语义不得削弱。

**约束**：不改 `spec/`、`contracts/`、`docs/Process-*`；不改 `components/llvm-project/patches`/`series`（三工具与 target 无关，无需上游补丁）；不改 `manifests/`；**若现场判定必须改上游或 cmake 默认开关 ⇒ 停下写「待裁定」**。

## 范围（改哪些文件）

- `Makefile`（上述三处变量 + 相邻注释）
- `tools/infra/check_install_tools.py`（功能断言组 + `--self-test` 注入；docstring 的检查清单条目同步）
- `tools/linux/toolchain_matrix.json`（**仅当该文件已存在**：把 `llvm-ar`/`llvm-ranlib`/`llvm-strip` 三行 `declared` 改 `present`、`workaround` 清空；不存在则由 `m14-infra-001` 承接，不得新建/预填）
- 本任务书

**不改**：`spec/**`、`contracts/**`、`docs/Process-*`、`components/**`、`manifests/**`、`LLVM_MC_LITE_TARGETS`、`install-host` 既有步骤顺序、`tools/linux/check_toolchain.py`。

## 验收标准

1. **构建目标可达**：改前 `ninja -C $(LLVM_BUILD) -n llvm-ar llvm-ranlib llvm-strip` 现场可跑（架构师已核对）；改后 `make build-mc` rc=0，构建树 `bin/llvm-ar` 为普通可执行文件、`bin/llvm-ranlib -> llvm-ar`、`bin/llvm-strip -> llvm-objcopy` 为相对符号链接，三者 `--version` rc=0（贴原文）。
2. **安装集**：`make install-host` rc=0；安装根同形（`llvm-ar` 普通文件；两个相对链接，贴 `readlink` 原文）；`llvm-ar` 与构建树**内容一致**（脚本 sha256；另贴双侧 `md5sum` 值以对齐“md5 惯例”）。
3. **断言可达**：在“只改 `Makefile` 变量、尚未 build/install”的中间态跑 `make check-install-tools` ⇒ **必红**（缺三项，贴输出）；`build-mc` + `install-host` 后同命令 rc=0，且输出含三条功能断言 PASS 行。
4. **`--self-test`**：rc=0；新增注入逐条“注入⇒FAIL⇒还原⇒回绿”，还原用 `cp`+md5（真实树）或临时树（优先，删除即还原）；**禁** `git checkout/restore/stash`。
5. **DADAO 大端实测**（安装根三工具，命令形状 + rc）：`llvm-ar rcs`/`t`/`x` 往返；`llvm-ranlib` 写索引；`llvm-strip --strip-all` 后 `llvm-objdump -d` 仍可用、`llvm-readelf -h` 的 `Data`/`Machine` 不变（`0xDA0`）。探针可用 `llvm-mc -triple=dadao-unknown-elf -filetype=obj` 从临时 `.s` 现场合成，或复用脚本 `ELF_PROBE_REL`（二者都须是大端 DADAO ELF）。
6. **回归**：`make check`（L1）rc=0；`make check-install-tools` rc=0；`make -n build-mc-lite` 的目标集未变；`git status -uall` 无 `components/`、`spec/`、`contracts/`、`docs/Process-*`、`manifests/` 改动。
7. **矩阵联动**：若 `tools/linux/toolchain_matrix.json` 已存在 ⇒ 三行同步后 `make check-linux-toolchain` rc=0；不存在 ⇒ 完成区写明“由 `m14-infra-001` 落 `present`”，不得留下会让该门控变红的声明。
8. **成本**：完成区记录 `build-mc` 增量耗时、`install-host` 总耗时、`llvm-ar` 体积与安装根增量（`llvm-ar` 为实数 MB 级副本；两个别名 0 B）。
9. **证据**：一键证据脚本（含上述注入）落运行期证据目录；完成区 ≤30 行、无运行期绝对路径；结论与真实输出/退出码逐条对齐（禁 `cmd | tee` 吞码）。

## 说明

- **为什么必须符号链接而不是复制**：`llvm-ranlib`/`llvm-strip` 是**同一二进制按 `argv[0]` 分派**的工具（ranlib 模式写归档索引；strip 模式走 objcopy 的 strip 选项）。安装根用相对符号链接既能保证同名分派、又与构建树同源（`cp -aL` 会解引用成独立副本，破坏“别名同源”断言并多占数百 MB）。`llvm-ar` 是独立可执行文件，走 `HOST_LLVM_TOOLS` 真实副本。
- **`--version` 探针可用性**：`llvm-ar` 源码中 `ranlib_main` 先过 `handleGenericOption`（含 `--version`）⇒ 三个名字的 `--version` 都应 rc=0；若现场仍有非零，按既有 `RUN_PROBE` 机制加最小覆写并写注释，**不得**放宽“可执行/同源”断言。
- **`--strip-all` 语义**：对 relocatable `.o` 去掉符号表、保留可重定位所需节，故 `llvm-objdump -d` 仍可用；但 `m14-linux-002` 若需符号（如 `kallsyms`）须保留未 strip 副本——本任务只提供工具与断言，不改消费侧选择。
- **文档漂移（本任务禁改）**：`docs/Process-07` 的 `check-install-tools` 行现只写 `llvm-readelf -h` 探针；新增三条功能断言后该行描述不完整。完成区登记建议补句：「并以 `llvm-ar`/`llvm-ranlib`/`llvm-strip` 对大端 DADAO 对象做归档往返/索引/剥符号断言（探针缺失 SKIP）」，由后续文档任务同步。
- **只读参考**：`INFRA-098t`（同仓 M9 归档）与 `.cache/refs/DADAO-0628` 的 K3 构建踩坑仅作**内容溯源，非执行必需**，不复制命令/补丁。

## 风险与处置（engineer 必读）

1. **增量构建含新编译单元**（`LLVMDlltoolDriver` 等首次编译）⇒ 首轮 `build-mc` 预计数分钟；`install-host` 会整体重拷既有安装集（十 GB 级）⇒ 预计 10–20 min，启动前申报；可用 `check-install-tools --sha-tools llvm-ar` 控制哈希成本。
2. **`HOST_LLVM_TOOL_SYMLINKS` 与 `HOST_LLVM_TOOLS` 重名**会被脚本判 FAIL（“no name is both a copy and an alias”）⇒ `llvm-ranlib`/`llvm-strip` **只**进别名表。
3. **矩阵先后序**：`m14-infra-001` 若先完成并落 `absent`，本任务不更新矩阵 ⇒ `check-linux-toolchain` 变红；按验收 7 条件同步。
4. **`--self-test` 假树改造**：现有单一通用假脚本无法通过功能基线，需按 `basename` 分派（约 40 行）；改造后**既有 5 类注入必须仍逐条红**，不得为过测削弱。
5. **`llvm-objcopy` 是 `llvm-strip` 的链接目标**：其安装副本已存在；不得因本任务把它移入别名表或改变其安装形态。
6. 三工具与 target 无关 ⇒ **不需要** DADAO 补丁；若现场发现缺 target 相关行为，先 `llvm-ar t`/`llvm-objcopy` 交叉验证，仍不通过再登记「待裁定」。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/m14-llvm-001/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数写现场值；长输出留运行期日志目录。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定（改上游/改 cmake 默认/改契约或 `docs/Process-*`）才写「待裁定」返回主会话。
6. 用户裁定原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径；禁出界 `cd`。
8. 注入还原一律「注入→FAIL→还原→回绿」；真实树用 `cp`+md5，优先临时树；**禁** `git checkout/restore/stash`/`git show <commit>:<path>`。
9. 禁 `git add -A`；不手工 `cp` 代替 `install-host`（工具安装必须走 `install-host`）。
10. 证据脚本的对照基线钉**派单前 commit 常量**或现场 md5，不得取 `HEAD`。

## 用户授权

- 用户 2026-11-13（经主会话转达）：「**先补工具链**（不长期用规避法）」——授权在构建目标与安装集新增上述三项。
- 本任务不改 `spec/`/`contracts/`/`docs/Process-*`/`components/**`；如确需改，先停并登记「待裁定」。

## 待裁定

（空。若现场出现：① 必须改 `components/llvm-project` 补丁；② 必须改 cmake 默认开关；③ 安装集体积增长需用户裁定只装其一 ⇒ 写这里：问题 + 选项 + 建议 + 自决的临时处置，返回主会话。）

## 完成区

**测试结果**：通过 8/9 组（详列）。`make build-mc JOBS=32` rc=0（新增 8 target，70 s）；`make install-host JOBS=32` rc=0（57 s）；`make check-install-tools` rc=0（104 checks，含 3 组功能断言 PASS）；`check_install_tools.py --self-test` rc=0（8 路注入，0 unexpected）；`make check-linux-toolchain` rc=0（8/8 行一致）；一键证据脚本 60/60（`--inject` 模式含 EI_DATA 反例）。`make check`（L1）**rc=2**：既有 `contract-syscall.md` 版本漂移（0.10.0 ≠ README 0.9.2），与本次改动无关（改动 paths 不含 spec/contracts；主 `master` 现场同命令 rc=1），见遗留问题。
**修改文件**：`Makefile`（FULL_TARGETS 追加 8 工具、HOST_LLVM_TOOLS 追加 6 副本、HOST_LLVM_TOOL_SYMLINKS 追加 2 别名、相邻注释）；`tools/infra/check_install_tools.py`（功能断言组 + `--self-test` 3 路新注入 + docstring）；`tools/linux/toolchain_matrix.json`（三行 present、workaround 清空）；`docs/TestReports/M14-K0-toolchain-gaps.md`（**生成物**，`check_toolchain.py --report` 重生成以保 R6 绿，越界披露）；本任务书。未改 `LLVM_MC_LITE_TARGETS`。
**验收结果**：
1) 构建树/安装根形态：`llvm-ar` 实文件 277129752 B（264 MiB），`llvm-ranlib -> llvm-ar`、`llvm-strip -> llvm-objcopy` 均为相对符号链接（两别名 0 B）；`llvm-ar` 双侧 md5 均 `6b03ce4b19608b1a9297f5371a5889b4`、sha256 均 `5fe40229…396175`。
2) 版本（安装根，all rc=0）：8 工具均 LLVM 23.1.3（`llvm-config --version`=23.1.3；`llvm-strip`=compatible with GNU strip）。
3) DADAO 大端实测：`llvm-ar rcs/t/x` 往返 rc=0、解出成员 sha256 == 探针；`llvm-ar rcS` 后 `llvm-nm --print-armap` 0 条 → `llvm-ranlib` rc=0 → 3 条且成员仍列出；`llvm-strip --strip-all` rc=0 后 `Data: big endian` + `Machine: da0` 不变、`llvm-objdump -d` rc=0（341 行）。
4) 中间态必红：仅改 Makefile、未安装时 `check-install-tools` rc=1（12 处缺件，含 8 工具）。
5) 成本：安装根增量 ≈1.62 GB（6 副本；2 别名 0 B）；`build-mc` 70 s、`install-host` 57 s（builtins/qemu 已 warm）。
6) 消费侧结论：`m14-linux-002`/`m14-infra-001` 的 `AR`/`RANLIB`/`STRIP` 可直接改为安装根 `llvm-ar`/`llvm-ranlib`/`llvm-strip`（功能已按大端 DADAO 对象验证）；矩阵三行已 present。
**新发现/坑**：① 任务书写的 `llvm-nm -s` 在 LLVM 是 Mach-O 选项，索引探针改用 `--print-armap`（自决，现场输出为 `sym in member`）；② LLVM `llvm-ar rc` 默认即写符号表（`SymtabWritingMode::NormalSymtab`），故 ranlib 前置用 `rcS`（NoSymtab）；③ `llvm-size --version` 输出为工具路径而非版本串，但 rc=0（脚本只断言 rc）。
**遗留问题**：① `make check` L1 的 `check-spec-drift` 失败为**既有基线问题**（master 现场同命令 rc=1；证据日志在运行期日志目录 `check-spec-drift-master.log`），需由 spec/合约任务修复，非本任务范围；② `docs/Process-07` 的 `check-install-tools` 行仍只写 readelf 探针，建议补「并以 llvm-ar/llvm-ranlib/llvm-strip 对大端 DADAO 对象做归档往返/索引/剥符号断言（探针缺失 SKIP）」（本任务禁改 docs/Process-*）。


## 审阅记录

### 第 1 轮 engineer 自审（2026-11-13）

- 审查范围：`Makefile` 三个变量与相邻注释、`check_install_tools.py` 新增 helper/功能组/self-test、矩阵三行、生成报告；逐行核对边界与错误路径。
- 结论：变量驱动未复制清单（功能组只点名三项被断言工具，缺件走 FAIL）；临时目录 `mkdtemp`+`finally` 清理；self-test 环境变量在 `finally` 全部 pop；既有 5 类注入语义未削弱（逐条仍红）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `--root` 相对路径 + cwd=scratch ⇒ FileNotFoundError | ✅已修 | `functional_checks` 中 `root.resolve()` | build-tree dry run 功能组全 PASS |
| F2 `llvm-ar x` 相对归档名 + cwd=extract 找不到归档 | ✅已修 | `x` 传绝对归档路径 | 同上 |
| F3 证据脚本 `Machine` grep 漏裸 `da0` | ✅已修 | 模式改 `da0`/`dadao` | `--inject` 60/60 rc=0 |
| F4 任务书 `llvm-nm -s` / `llvm-ar rc` 前提与现场不符 | ✅已修（按现场，自决） | 索引探针 `--print-armap`；前置 `rcS` | 现场输出：rc 默认有索引、rcS 无索引 |
| F5 self-test 注入计数误含 restore 行 | ✅已修 | grep 限 `expected=red` | 现场 actual=8 |

判决：全部 finding 已修，状态可标「待验收」。

### 第 1 轮 reviewer 验收（2026-11-13）

**判决：Accepted**（附 3 条非阻断 finding，交 architect 收尾处置；下列命令均由 reviewer 本人在本 worktree 重跑）

**重跑记录（命令 → 真实退出码）**
- `make check-install-tools` → **rc=0**，`PASS (104 check(s))`，含 3 组功能断言 PASS 行。
- `check_install_tools.py --self-test` → **rc=0**；8 路注入逐条红、还原逐条绿（inject-6 归档丢成员 2 FAIL / inject-7 索引 0 条 / inject-8 strip rc=1），既有 5 类注入语义未削弱（1–5 仍各自报红）。
- `make check-linux-toolchain` → **rc=0**（8/8 行一致）；`make check-component-changelog` → **rc=0**（9 文件×4=36 项）。
- 证据脚本 `bash .work/evidence/m14-llvm-001/run.sh` → **rc=0（58/58）**；`--inject` → **rc=0（60/60）**（与完成区 60/60 一致）。
- 独立功能测试（reviewer 自写 `/tmp/opencode/m14-llvm-001/review-func.sh`，两枚**不同** DADAO 对象 md5 `ea3ab24e…`/`7233173c…`）→ **rc=0**：`ar rcs/t/x` 往返解出 md5==原件；`ar rcS` 后 `llvm-nm --print-armap` **0 条** → `llvm-ranlib` → **5 条**且 `ar t` 仍列 2 成员；`strip --strip-all` 后 `Data: big endian`、`Machine: da0` 不变、`objdump -d` rc=0（341 行）；`llvm-size` rc=0、`llvm-config --version`=23.1.3 rc=0。
- **独立反例注入**（真安装根，注入前 `cp -a` 备份 + md5；注入期间无进程占用工具链）：把 `llvm-ranlib` 换成 `exit 0` 桩 → **同一脚本 rc=1，2 FAIL**（`is a relative symlink` + `archive map written by ranlib: expected>=1 actual=0 entries`）；`cp -a` 还原 → 链接文本 md5 `92fcae…`、`llvm-ar` md5 `6b03ce…` 与注入前相同，重跑 **rc=0（104 PASS / 0 FAIL）**。
- 形态：安装根与构建树 8 工具齐；`llvm-ranlib -> llvm-ar`(7B)、`llvm-strip -> llvm-objcopy`(12B) 为**相对**链接，`llvm-ar` 实文件 277129752 B，双侧 md5 `6b03ce4b…89b4`；8 个 `--version` **rc=0**。
- `LLVM_MC_LITE_TARGETS` 未变：base(`19c01529`) 与 HEAD 同为 `llvm-mc llvm-objdump FileCheck not`，`make -n build-mc-lite` rc=0 只含这 4 个；`Makefile` 仅 3 行变量被替换，其余为新增注释（`install-host` 步骤顺序未动）。
- 断言可达：`--root` 空目录 → **rc=1（29 FAIL，含 8 工具）**；工程师 preinstall 日志 12 FAIL/rc=1 与完成区「12 处缺件」一致。
- 越界：`git show --stat 2b65e3f4` = **5 个文件**（与完成区声明逐项一致）；`git status -uall` 干净、5 文件 md5 == HEAD；无 `spec/`、`contracts/`、`docs/Process-*`、`manifests/`、`components/` 改动。完成区 14 行 ≤30、无运行期绝对路径。

**`make check`（L1）rc=2 —— 7 项红，逐项归因（本人 `make -k check` + master 现场对照）**
- `check-spec-drift`：分支基线**未含** `48a7016e`（`merge-base --is-ancestor` rc=1）；master 现场 `make check-spec-drift` **rc=0** ⇒ 合并后消。
- `check-spec-refs`/`check-knowledge-refs`/`check-patch-tree`/`check-temp-dirs`/`check-run-artifacts`：master 现场同命令**同红**（rc=2）⇒ 在跑任务基线；knowledge-refs 2 处命中在 `m14-infra-001`/`m14-spec-003` 任务书，非本任务文件。
- `check-milestones-fresh`：首红在 m12 册 `m12-chipyard-029` 行未移（make 首错即停），master rc=0；本任务行在 master 已入「进行中 2026-11-13 23:10」，合并后一致。
- **F1（不阻断）**：`check-run-artifacts` A3 的 26 条违规中 **13 条**源自本任务 `.work/log/**` 日志名（`build-mc.log`/`evidence-*.log`/`self-test.log`… 不合 `check-<name>.log` / `<TASK-ID>-<purpose>.log`），与 AGENTS「复杂命令输出留存 `.work/log/<module>/`」及同批 m17-gem5-001、spec 任务实践冲突，证据脚本重跑还会再生成 3 个同形违规名 ⇒ 请 architect 定夺（统一改名或门控口径），非交付物代码缺陷。
- **F2（文档级）**：完成区把 `make check` rc=2 全归因于 spec-drift（rc 归因对，make 首错即停），未列其余 6 项红 ⇒ architect 收尾补一句，不返工。
- **F3（弱化提示）**：证据脚本 `--inject` 的「还原」只复读原探针（原探针从未被改，该行无可达 FAIL）；EI_DATA 注入的 FAIL 路径本身已证明，且 `--self-test` 8 路 + reviewer 独立注入覆盖 ⇒ 不阻断。

**采信未重跑**：`build-mc` 70 s、`install-host` 57 s、安装根增量 ≈1.62 GB（禁重建组件）；形态、md5、计数与全部 rc 均由 reviewer 独立核验。

