# TESTCASES-048t: llvm-test-suite 两档用户态跑（静态档 → 动态档）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-user` 的 DADAO 后端，**`已验证`**）；`INFRA-082t`（`P1` musl 静态，**`已验证`**）、`INFRA-085t`（`P2` 动态，**`已验证`**）；`LLVM-093t`（`llvm-test-suite` **取源与锁定**，**`已验证`**；锁 `commit 2919e551…`〔tag `llvmorg-23.1.3` peel〕，`patchless = true` ⇒ 源只读；**其「基线跑触发条件 = musl 静态/动态链跑通」现已满足**）；`TESTCASES-045t`（首份分类统计，`已验证`；其 `run_suite.py` 在 `dadao-m1` 路径上已硬失败 ⇒ **本册只借方法论，不复用运行路径**）；`ISS-247`（**链接基址**）、`ISS-246`（known-fail 依据）、`ISS-229`（串行）、`ISS-210`（安装根新鲜度）、`ADR-0025`（`D2`/`D6`/`D7`）；**同批三册**：`TESTCASES-046t` / `TESTCASES-047t` / `TESTCASES-048t`（本册）⇒ **同改共享文件 ⇒ 串行**。
**状态**：待开始

> **编号（现场取号，2026-10-17）**：现存最大 = `TESTCASES-045t` ⇒ 三册顺取 `046`/`047`/`048`；全历史 `grep -E 'TESTCASES-04[678]'` **0 命中**。

## 立项来源 / 用户裁定（原话逐字引录，渠道 = 经主会话问答）

- **2026-10-15**：「**不用改D6，就按原来的顺序进行，然后增加embench和两个新的test suite的测试；测试的时候区分静态链接和动态链接，先测静态链接，再测动态链接**」⇒ 三套 × 两档、**先静态后动态**。
- **2026-10-14**：「**暂缓，等 musl 跑通**」（`LLVM-093t`「基线跑暂缓」原话）⇒ 触发条件 = **musl 静态 / 动态链跑通**；`P1`（`INFRA-082t`）/`P2`（`INFRA-085t`）/`P3`（`QEMU-062t`）**均已 `已验证`** ⇒ **条件成立**。
- **2026-10-15**（`External/` 口径）：「上游 `External/**`（含 SPEC CFP2006/CFP2017）**已排除**」（`TESTCASES-045t` 记录的用户口径）⇒ 本册**不碰** `External/**`。
- **判据边界**：与 `RISC-V + musl` golden 的对照归 **`P4`**（`ADR-0025 D7`）⇒ **本册不做对照** ✗。

## 范围（**本批 = 有界子集，须用户确认后才可 `/dispatch`**）

`AGENTS.md`「任务分解与执行确认」：执行任何具体任务前须与用户确认任务书内容 ⇒ 下表范围 = **提案**。

| 分档 | 目录 | 本批动作 | 现场计数（本笔派生，**执行期再派生、不写死**） |
|---|---|---|---|
| **A 本批两档都跑** | `SingleSource/Benchmarks/`（单 TU 程序） | 编链 + 跑 | **101** 例 |
| | `MultiSource/Benchmarks/` | 按**程序目录**（目录内全部 `.c` 一起编链）+ 跑 | **104** 个程序单元 |
| | `MultiSource/Applications/` | 同上 | **17** 个程序单元 |
| **B 本批只计数、声明范围外** | `SingleSource/Regression/` | **不跑**（只给现场计数与理由，**另立任务**） | **1241** 例 |
| | `SingleSource/UnitTests/` | 同上 | **645** 例 |
| | `MultiSource/{UnitTests,Examples}/` | 同上 | **4** 例 |
| **C 结构性排除**（逐条 reason + 现场计数） | `External/**` | 用户口径已排除 | 现场计数 |
| | 非 `.c` 后缀（`.cc/.cpp/.cxx/.C/.m/.mm/.f*`） | sysroot **无 C++ 标准库** / 无 Fortran 前端 | 现场按后缀计数 |
| | `MicroBenchmarks/**` | 现场 **0** 个 `.c`（含 `main`）⇒ 本批无对象（须如实记录） | 0 |

- **B 的理由**：本批两档 = A 类 × 2 轮 ≈ **444** 次编链 + 运行；B 类另有 ≈1890 例，单轮 wall-clock 远超单册范围。**B 不是「通过」**，报告中必须写「**未跑，计数 N，另立任务**」。
- **若用户要求本批纳入 B** ⇒ 停下报告，改为分册（按目录树拆 2–3 册、各自两档），**不得**在一册里静默裁剪。

## 目标（两轮，顺序固定：静态档 → 动态档）

1. **第 1 轮 = 静态档**：A 类全部程序按 **musl 静态**（`crt1.o` + `libc.a`）编链，`qemu-dadao` 上跑。
2. **第 2 轮 = 动态档**：同一批按 **musl 动态**（`-dynamic-linker /lib/ld-musl-dadao.so.1` + `libc.so`）编链，同法跑。
3. **产出**：逐例结果 + 五类分类 + `known-fail` 表（若有，**唯一依据 = `ISS-246`**）+ B/C 计数与理由 + 覆盖边界声明 + 一键证据（含**可达 FAIL**）。
4. **判据**：优先用**上游自带的参考输出**作独立 oracle（`reference_for` 顺序：`.reference_output.small` > `.reference_output.big-endian`（本机大端，`ADR-0003 D1`）> `.reference_output`）；无参考输出者，**唯一可达判据 = 「跑完且退出码 0」+ 记录 stdout sha256**，并在报告中**明写「这不是输出等价判定」**。

## 已核事实（本笔现场；执行时只作复核）

| 项 | 现场值（2026-10-17） |
|---|---|
| 源 | `.work/source/<llvm-test-suite>`（锁 `2919e551…`；`patchless` ⇒ **只读**；检出 ≈2.4 GB） |
| 顶层 | `ABI-Testsuite Bitcode CMakeLists.txt CTMark ClangAnalyzer External Fortran LNTBased MicroBenchmarks MultiSource SingleSource …` |
| 枚举口径 | 扫描面 = `SingleSource/**`、`MultiSource/**`、`MicroBenchmarks/**`；候选 = `.c` 且含 `main`；`MultiSource/**` 的判定单元 = **目录**（同目录多个 `.c` 一起编） |
| 参考输出 | 上游随用例提供 `.reference_output*`（大端变体 `.reference_output.big-endian` 存在时优先） |
| 编译参数 | 基准树（`SingleSource/Benchmarks`、`MultiSource/Benchmarks`、`MultiSource/Applications`）加 `-DSMALL_PROBLEM_SIZE`（上游「验证型」小规模开关，只改工作量、不改程序判定） |
| 历史耗时 | `dadao-m1` 时代 `Shootout` 的 `fib2/nestedloop/sieve` 曾达数十秒（`SMALL_PROBLEM_SIZE` 下）；user 模式显著更快，但仍须逐例 `timeout` |
| 静态/动态产物 | 同 `TESTCASES-047t`（musl `lib/{crt1.o,libc.a,libc.so}` + 目标 sysroot `ld-musl-dadao.so.1`） |

## 链接与运行口径（自包含；`<...>` 为占位）

- **基址**：**lld 默认**，**禁** `-T tests/scripts/dadao.lds`（`ISS-247`：`0xFC00_0000_0000` 超出 47 位宿主用户 VA ⇒ `Unable to find a guest_base…`）。
- **头文件**：musl 口径（与 `build_musl.py` 同集合、`-nostdinc`）。
- **静态档**：`clang --target=dadao-unknown-elf -nostdinc <musl 头> -O2 -DSMALL_PROBLEM_SIZE -c <每个 TU>` ⇒ `ld.lld -o <p>.elf <musl>/lib/crt1.o <objs> -L <musl>/lib -lc` ⇒ `qemu-dadao <p>.elf`。
- **动态档**：同编译段 ⇒ `ld.lld … -dynamic-linker /lib/ld-musl-dadao.so.1` ⇒ `qemu-dadao -L <target-sysroot> <p>.elf`。
- **超时**：默认 `--timeout 120`（基准可 `--timeout 300`，最终值写入报告）；`124` ⇒ `blocked`（**不得**默认为 pass/fail）。
- **驱动**：`--link-mode static|dynamic` 显式二选一；两档**顺序**执行；**两档用同一枚举快照**（同一批程序、同一编译参数），保证可比。

## 失败分类（计数运行期派生，禁写死）

| 类 | 定义 | 判定后果 |
|---|---|---|
| `pass` | 编链成功 + 跑完 + oracle 匹配（有参考输出）/ 退出码 `0`（无参考输出，另注「非等价判定」） | 计入 pass |
| `fail`（**真失败**） | 编链成功 + 跑完 + oracle **不匹配** / 退出码非 0，且不可归 `known-fail` | 计入 fail |
| `known-fail` | 失败可逐条归因到 `ISS-246`（`__thread`），逐条注症状原文 + 依据 | 单列，**不计 pass** |
| `blocked` | 编链失败 / 缺符号 / 后端缺口（如 `Cannot select`）/ `qemu` 崩 / `timeout` | 计入 blocked；**`blocked>0 ⇒ 本档 rc=1`**（`ISS-248` 口径） |
| `excluded` | **开工前**声明、结构性范围外（C++/Fortran/`External/**`/无 `main` 的 helper） | 唯一 skip 通道 |

- **禁止**把真失败归入 `known-fail`/`excluded`；**禁止**因「上游也失败」而静默改标（必须给出现场首错行）。
- `known-fail` 本册预期 **0**（llvm-test-suite C 用例不依赖 `__thread`）；若出现须按上表口径逐条登记（**不得**凑数）。

## 接口规范

- **输入**：`.work/source/<llvm-test-suite>`（只读）、musl 静态/动态产物、`qemu-dadao`。
- **输出**：① 驱动（入 git，建议 `tools/testcases/run_llvm_ts_user.py`）；② 逐例 JSON/CSV + 报告（落 `.work/log/testcases/`）；③ `.work/evidence/<任务ID>/run.sh`（非交互、任一失败非零、含可达 FAIL）；④ 可选 `Makefile` target（**不入** L1/L2/L3）；⑤ 完成区 + 报告摘要（含 A/B/C 三分档计数）。
- **约束**：不改 `.work/source/**`（`patchless`）；不改 `spec/`、`.tao/contracts/`、`contracts/`、`components/**`；注入用 `cp` + md5 还原。

## 验收标准

1. **范围口径可核**：报告给出 A/B/C 三分档的**现场枚举计数**与命令，且 A 类执行集 == 枚举集（少一个即 FAIL）；B 类明写「未跑 + 计数 + 另立」，**不得**计入 pass。
2. **两档顺序正确且各自完整**：static 轮先跑完、dynamic 轮后开始；两档各自 rc + 六数（total/pass/fail/known-fail/blocked/excluded）。
3. **基址 = lld 默认**：每档 ≥1 例 `readelf -l` / `llvm-readobj` 输出，证明最低 `PT_LOAD` ≠ `0xFC00_0000_0000`；命令留证。
4. **两档形态可核**：静态档**无** `PT_INTERP`；动态档**有** `PT_INTERP = /lib/ld-musl-dadao.so.1` + `ldso` 真跑证据（≥1 例）。
5. **oracle 声明诚实**：有参考输出的用例 = 逐字比对参考文件（文件名见报告）；无参考输出者必须标注「exit-only，非等价」；`pass` 中两类分别计数。
6. **分类可信**：`fail` 逐条含命令 + 首错行；`blocked` 逐条含根因指针（`Cannot select` 文本 / 缺符号名 / timeout 秒数）；`excluded` 逐条 reason。
7. **可达 FAIL**：注入 ≥1 例期望值/参考输出错误 ⇒ 驱动 rc=1 且恰该例 FAIL；`cp` + md5 还原 ⇒ 回绿（三态留证）。
8. **门控**（串行，`ISS-229`）：`make check`(L1) rc=0；`make check-modules`(L2) rc=0；`check-patch-tree` **预期 177**（不改组件）；`check-no-residue`/`check-tasks`/`check-knowledge-refs`/`check_issues.py` rc=0。
9. **前置申报**：开工前申报预计耗时（两档 × A 类 ≈444 次编链）；如需 `install-host` ⇒ **≈5 min**、`JOBS=8`、**不并发**、改后必须跑（`ISS-210`）；本册预期不改组件。
10. **完成区 ≤30 行**，与真实输出逐条对齐；长输出落 `.work/log/testcases/`。

## 判据边界（本批**不做** ✗）

- **不做** `SingleSource/Regression` / `SingleSource/UnitTests`（B 类，仅计数；另立任务）。
- **不做**与 `RISC-V + musl` golden 对照 ⇒ **`P4`**（`ADR-0025 D7`）。
- **不做** C++/Fortran 支持（sysroot 无 C++ 标准库、无 Fortran 前端）。
- **不做** `ISS-246` 修复（归 `LLVM-100t`）、不改 `dadao.lds`、不改组件 / `spec/` / 契约。
- **不做** `embench-iot` / `libc-test`（各自独立成册）。

## 硬约束

1. 临时目录 `/tmp/opencode/TESTCASES-048t/`；命令在 workdir 内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件（2.4 GB 检出**只读**，编译产物落 `.work/build/` 或 `/tmp`）。
2. **不用** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. **只动**：`tools/testcases/**`、`Makefile`（可选）、`.work/**`（gitignored）、本任务书、`milestones.md`（如需）。**不动** `spec/` / `.tao/contracts/` / `contracts/` / `components/**` / `.work/source/**`。
4. 完成区与真实输出逐条对齐；**禁** `cmd | tail` 接进 `&&`、**禁** `cmd | tee` 吞码。
5. **不提交**（提交权归 architect）；用户裁定须把**原话**写入本任务书。
6. **失败保留现场并继续推进**（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
7. 长任务（单档预计 >10 min）⇒ `setsid nohup` + 落 `XXX_EXIT=$rc`，**不在会话内等待**；**一次只跑一档**。
8. 与 `TESTCASES-046t`/`047t` 同改 `Makefile`/`milestones.md` ⇒ **串行**。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（自审意见、finding 处置及判决）

#### 第 1 轮 reviewer 验收
（独立重跑、约束核验、判决）
