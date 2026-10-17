# TESTCASES-048t: llvm-test-suite 两档用户态跑（静态档 → 动态档）

**模块**：testcases
**项目里程碑**：M8
**依赖**：`QEMU-062t`（`qemu-user` 的 DADAO 后端，**`已验证`**）；`INFRA-082t`（`P1` musl 静态，**`已验证`**）、`INFRA-085t`（`P2` 动态，**`已验证`**）；`LLVM-093t`（`llvm-test-suite` **取源与锁定**，**`已验证`**；锁 `commit 2919e551…`〔tag `llvmorg-23.1.3` peel〕，`patchless = true` ⇒ 源只读；**其「基线跑触发条件 = musl 静态/动态链跑通」现已满足**）；`TESTCASES-045t`（首份分类统计，`已验证`；其 `run_suite.py` 在 `dadao-m1` 路径上已硬失败 ⇒ **本册只借方法论，不复用运行路径**）；`ISS-247`（**链接基址**）、`ISS-246`（known-fail 依据）、`ISS-229`（串行）、`ISS-210`（安装根新鲜度）、`ADR-0025`（`D2`/`D6`/`D7`）；**同批三册**：`TESTCASES-046t` / `TESTCASES-047t` / `TESTCASES-048t`（本册）⇒ **同改共享文件 ⇒ 串行**。
**状态**：待验收

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
**测试结果**：**第 1 步**（全量见下「第 2 步」）。小样本 5 单元 × 两档 = **10/10 PASS**（static/dynamic 各 `total=5 pass=5 fail=0 blocked=0`、rc=0）；证据脚本 14 项全 PASS、rc=0（含注入→rc=1 恰 hello FAIL→回绿）。门控 `make check`(L1) 与 `check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py` 均 rc=0。
**修改文件**：新增 `tools/testcases/run_llvm_ts_user.py`；新增 `.work/evidence/TESTCASES-048t/run.sh`、`.work/evidence/TESTCASES-048t-step2/run.sh`（均 gitignored）；`.work/log/testcases/llvm-ts-user-{pilot,static,dynamic}-*.{json,log}`、`llvm-ts-user-both-{first-fixed,rerun}.log`、`llvm-ts-user-evidence-step2.log` 与 `llvm-ts-user-ft-host-glibc.log`（gitignored）；`.tao/knowledge/issues.yaml`（新增 `ISS-264`/`ISS-265`/`ISS-266`/`ISS-267`）；本任务书完成区/自审。**`Makefile` 未改**（可选 target 省略，避免与 046t/047t 同改共享文件）。
**验收结果**：A = **222**（`SingleSource/Benchmarks` 101/103 个含 main 的 `.c`；`MultiSource/{Benchmarks,Applications}` 104+17 程序目录）；B = **1890**（1241/645/2/2，**未跑**）；C：`External` `.c`=9（main 0）、非 C 后缀 719+226+28+22+11+4、`MicroBenchmarks` `.c`=10（main **0**）；证据脚本独立重算与 `--list` 一致、`census_ok=True`。oracle 形态：stdout+exit 161 / md5 52 / raw 3 / exit-only（非等价）6。小样本逐例两档均 PASS：`Shootout/hello`、`Polybench/blas/gemm/gemm`（md5+CMake flags）、`McCat/12-IOtest`（4 TU）、`Olden/bh`（4 TU，RUN_OPTIONS+`.small`）、`McCat/01-qbsort`（md5+stdin，3 TU）；两档 `min PT_LOAD=0x10000`，static 无 `PT_INTERP`、dynamic 有且路径 `/lib/ld-musl-dadao.so.1`（`readelf -lW` 现场）。
**新发现/坑**：① 参考 = **RunSafely 整份输出**（stdout+stderr 同一 fd + 裸 `exit N\n` 尾；hash 形式对整份取 md5）——只看 stdout 会把 gemm/qbsort 判假 fail。② 参考文件名 = **`llvm_multisource` target**，29 例与目录名不同（`jpeg-6a`→`cjpeg`、`ClamAV`→`clamscan`），按目录名会静默丢 29 个 oracle。③ dynamic 档必须 **`-fPIC`**（`stdout`/`stderr` 数据符号的 `R_DADAO_COPY` 被 lld 拒，ADR-0026 D7②）；与册子「同编译段」的**唯一偏差**，两档 compile cmd 均入 JSON。④ MultiSource 的 TU 集取上游 **curated `llvm_multisource(...)` 列表**（lua/jpeg/cfrac 另有第二个 `main`）。⑤ 54 例用上游 **fpcmp 容差**（已用 `tools/fpcmp.c` 自建 host 工具；byte-exact 会假 fail）。⑥ 上游 CMake 现场求值，引号语义须按 CMake（SMG2000 假 fail 根因）。⑦ `sqlite3` 需 `tclsh smalltest.tcl` 生成 `test*.sql`、`JM/ldecod` 需 `Output/`（在副本内建）。⑧ `ClamAV` 参考对**输出交错**敏感 → 仍按规则 `fail` + 逐例注记，不改标。⑨ 标定（40 例样本、jobs=8、timeout 300）：29 pass/1 fail/10 blocked，Σ=2089.9s、均值 52.2s/例。
**遗留问题**：① **全量两档已跑**（第 2 步：`193/2/0/27/0/222`，两档同）；② `known-fail` 表仅收 `ISS-246`（逐例依据表已实现，依据不成立即 FAIL；本册为 0）；③ B 类 1890、C 类结构排除按册**未跑**；④ Burg 等老 C 被现代 clang `-Wimplicit-int` 挡下 → `blocked`（未全局强压 `-Wno-`，如需另行裁定）；⑤ 全量实测坑：300s 超时 6、clang 前端崩溃 2（rc=-6）、qemu host SIGSEGV 4、`flog` libcall 缺口 2——均归 `blocked`；⑥ `ft`/`ClamAV` 两例 `fail` 为参考输出可移植性（`ISS-265`，**待裁定**是否扩展 known-fail 类别）。
**第 2 步（全量）确切命令行（已执行）**：`python3 tools/testcases/run_llvm_ts_user.py --link-mode both --jobs 8 --timeout 300 --work-dir .dadao/tests/llvm-ts-user`（两档顺序 static→dynamic、同一枚举快照；默认落 `.work/log/testcases/llvm-ts-user-<mode>-<mode>.{json,log}`）；`setsid nohup` 落 `LLVM_TS_EXIT=1`（仅因 `blocked>0`，`ISS-248` 口径），最终驱动复跑 04:11:08→04:36:23 = **25m15s**（static 12m37s + dynamic 12m38s；与前一版仅 md5 文案/`expected_exit` 字段差异的复跑逐例类别/退出码零变化）。

**第 2 步结果（2026-10-18，全量两档）**
- **两档六数（逐数相同）**：`total=222 pass=193 fail=2 known-fail=0 blocked=27 excluded=0`；pass 拆分 = 参考 oracle **192** / exit-only（非等价）**1**；oracle 形态 stdout 161 / md5 52 / raw 3 / none 6；`closure_ok=True`、`classification_ok=True`。
- **与首轮逐例 diff（两档均恰 6 例）**：`Misc/mandel`、`Misc/mandel-2`、`DOE-ProxyApps-C/RSBench` `blocked→pass`；`mediabench/jpeg/jpeg-6a`、`mediabench/mpeg2/mpeg2dec`、`Prolangs-C/gnugo` `fail→pass`；其余 216 例类别零变化（46 例 md5-pass 仅 reason 文案变）。
- **驱动修正（依据）**：① `llvm_test_data()` 复制进 per-case run dir（`cmake/modules/TestSuite.cmake:22-45` + `SingleMultiSource.cmake:101` 的 `WORKDIR %S`；mediabench 输入在 `../data`）⇒ `testimg.ppm`/`mei16v2.m2v` 就位；② 链接加 `clang -print-libgcc-file-name` 指向的 compiler-rt archive，与 libc 同 `--start-group` ⇒ `__muldc3`/`__divdc3` 解析；③ md5 oracle 不再额外要求 `exit==0`（`HashProgramOutput.sh` 对 RunSafely 整份文档〔含 `exit N` 尾〕取 md5；`gnugo` 基线即 exit 1）；④ 补 `include_directories`/`target_include_directories` 跟踪（`archie-client` 的 `<copyright.h>` 被上游 `check_function_exists(re_comp)` 守卫、musl 无 `re_comp` ⇒ 仍 `blocked` + 逐例 note）。
- **`fail` 逐条**（两档同）：① `Ptrdist/ft` — 运行 `qemu-dadao …/ft.elf 1500 100000`；`md5(output+exit)=3dd953c9…` vs 参考 `63acb35e…`，exit 0/0；宿主 glibc 同源同参数**复现参考值** ⇒ musl `srandom` 播种差异（`ISS-265`，`llvm-ts-user-ft-host-glibc.log`）。② `Applications/ClamAV` — `clamscan` 两文均 38072 B，仅 `Initializing the engine (devel-20071218)` 与库龄告警的交错位置不同（`ISS-265`；不改标）。
- **`blocked` 27 分类（两档同；逐条 `reason`/`compile`/`run` 见 `.work/log/testcases/llvm-ts-user-{static,dynamic}-{static,dynamic}.log`）**：编译/C 方言 7（Burg、siod、gawk、make、p2c、OptimizerEval、cdecl）；300s timeout 6（lemon、lua、SimpleMOC、unix-smail、mafft、nbench）；qemu 宿主信号 11 4（SPASS、consumer-typeset、8b10b、dbms）；缺头 3（office-ispell `sgtty.h`、archie-client `copyright.h`、Polybench template `polybench.h`）；clang 前端崩溃 rc=-6 2（lencod、obsequi）；后端 libcall 缺 2（CoMD、consumer-lame `flog`）；varargs 未支持 1（plot2fig）；`Cannot select: t29: ch = brind` 1（evalloop）；`undefined symbol: RUNTIME_INIT` 1（aarch64-init-cpu-features）。
- **覆盖边界**：A=222 全执行（== 枚举集，`closure_ok`）；B=**1890 未跑**（1241/645/2/2，另立）；C：`External` `.c`=9（main 0）、非 C 后缀 719/226/28/22/11/4、`MicroBenchmarks` `.c`=10（main 0）；205 个成功链接例 `min PT_LOAD=0x10000`，static **无** `PT_INTERP`、dynamic 全 `/lib/ld-musl-dadao.so.1`；未做 `RISC-V+musl` golden 对照（`P4`）。
- **新 issue**：`ISS-264`（本子任务首次下发 `Task cancelled`、盘上零改动、已重试一次）、`ISS-265`（ft/ClamAV 参考可移植性，**待裁定**）、`ISS-266`（qemu 宿主 SIGSEGV ×4：SPASS/consumer-typeset/8b10b/dbms）、`ISS-267`（后端缺口 ×6：clang 崩溃 2、`brind`、varargs、f80 `flog` ×2）。
- **证据/门控**：`.work/evidence/TESTCASES-048t-step2/run.sh` 17 项全 PASS、rc=0（注入 A `--inject-wrong-oracle`→rc=1 恰 hello FAIL→回绿；注入 B 改参考文件→rc=1→`cp` 还原 md5 相等→回绿）；`check-tasks`/`check-knowledge-refs`/`check-no-residue`/`check_issues.py`/`make check`(L1) 均 rc=0。
- **新发现/坑（第 2 步）**：① md5 参考 = RunSafely 整份文档哈希 ⇒ **基线 exit 非 0 也合法**（gnugo），不得额外要求 exit 0；② musl `srandom` 播种 ≠ glibc/BSD（`src/prng/random.c` 头注释）⇒ `ft` 参考不可移植；**宿主 glibc 同源复现**是区分「驱动/参考错」与「libc 语义差」的独立判据；③ MultiSource 输入按 `llvm_test_data()`+`WORKDIR %S` 摆（`../data`），不是 `cwd=源目录`；④ 上游 `check_function_exists` 守卫的 target（archie）在 musl 上本就不构建，blocked 根因须注记。
- **阶段进度**：第 1 步 ✅（驱动/枚举/小样本）；第 2 步 ✅（驱动修正 + 两档全量 + 分类 + 证据 + 门控）；**按本笔指令未改 `**状态**`**（仍 `待开始`）。

## 审阅记录

#### 第 1 轮 engineer 自审
**范围**：`tools/testcases/run_llvm_ts_user.py` 全文逐行 + 小样本/证据脚本实跑；判决 = 发现项全部已修、复验见下（按本笔指令**不改状态**）。

| # | finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| 1 | 该 clang 不接受 `--target`（首跑 hello 直接 blocked） | ✅已修 | `-target` | hello PASS |
| 2 | oracle 只取 stdout：漏 stderr、漏 `exit N` 尾 | ✅已修 | `run_stream`（stdout+stderr 同 fd）+ 整份文档比较 | gemm/qbsort 由 FAIL→PASS |
| 3 | hash 形式按 stdout 取 md5（漏 exit 尾） | ✅已修 | md5(output+`exit N\n`) | qbsort/gemm md5 命中 |
| 4 | 参考基名取目录名：29 例 oracle 丢失 | ✅已修 | `multi_target_name()`（`llvm_multisource` target） | oracle 形态 161/52/3/6（现场） |
| 5 | CMake 引号语义：`"-n 30 15 30"` 成一个 argv | ✅已修 | 整体引号去引号、嵌入式保留（cmake 3.28 对照） | SMG2000 FAIL→PASS |
| 6 | 有 `FP_TOLERANCE` 的 54 例被 byte-exact 误判 | ✅已修 | 自建上游 fpcmp，`-r/-a/-i` | sqlite3 + McGill×4 PASS |
| 7 | `JM/ldecod` 缺 `Output/`（语料无此目录） | ✅已修 | 副本内建 RUN_OPTIONS 输出父目录 | ldecod PASS |
| 8 | `sqlite3` 缺 `test*.sql`（上游 tcl 生成） | ✅已修 | `CASE_PREPARE` 跑 `tclsh smalltest.tcl` | sqlite3 PASS（fpcmp） |
| 9 | `--only` 无匹配时静默少跑 | ✅已修 | 每个 pattern 必须命中，否则 rc=2 | `blas/gemm$` → rc=2 |
| 10 | 超时只杀直接子进程（qemu 可能残留） | ✅已修 | `start_new_session`+`killpg`；现场清理首跑孤儿 | 采样 300s 超时例无残留 |
| 11 | 死代码/未用常量（`A_TREES`/`EXIT_RE`/`expected_stdout`） | ✅已修 | 删除；`FAULT_NAMES` 接入 fail 原因 | `py_compile` rc=0 |
| 12 | `both` + 显式 `--json-out` 两档互相覆盖 | ✅已修 | `-static`/`-dynamic` 后缀 | both 实跑产出两文件 |

**未做/边界**：全量未跑（第 2 步）；B/C 未跑；未新增外部依赖（fpcmp 由语料 `tools/fpcmp.c` + host cc 构建）；未改 `spec/`/`contracts/`/`.work/source/**`；未 commit/push。

#### 第 1 轮 reviewer 验收
（独立重跑、约束核验、判决）

#### 第 2 轮 engineer 自审
**范围**：第 2 步新增/改动代码逐行（`llvm_test_data`/`include_directories` 解析、run-dir 输入复制、`--start-group` 链接、md5 oracle、builtins 解析）+ 两档全量产物复核 + 证据脚本实跑（17/17 PASS）；判决 = finding 全部已修（按下笔指令**不改 `**状态**`**）。

| # | finding（自审发现） | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|---|
| 1 | md5 oracle 把 `expected_exit` 硬设为 0，属**无依据期望值**（哈希已含 exit 尾；gnugo 基线 exit 1） | ✅已修 | md5 分支置 `expected_exit=None`、失败文案去掉 `expected 0`；仅比哈希 | 两档 `gnugo` pass/exit 1/`expected_exit=null`；52 例 md5 全为 null |
| 2 | 上述修正发生在首轮修正后全量之后（产物与最终驱动有文案/字段差） | ✅已修 | 用最终驱动**重跑两档** | `04:11:08→04:36:23`（25m15s），与前一版**逐例类别/退出码零 diff** |
| 3 | `llvm_test_data()` 若源文件缺失会静默继续？ | ✅已修（实现即显式失败） | 缺文件 `raise FileNotFoundError` ⇒ `blocked`（`reason` 含路径） | 67 例 test_data 源**全部存在**（独立脚本核）；jpeg/mpeg2 就位 |
| 4 | `include_directories` 解析可能把 `target_include_directories` 的目标名当路径 | ✅已修 | `target_include_directories` 去掉首参；关键字白名单过滤 | `Burg` compile cmd 含 `-I …/Burg`；`archie-client` 仍 `blocked`（上游 `check_function_exists` 守卫）+ 逐例 note |
| 5 | 注入 B 改真实参考文件，若还原失败会污染只读语料 | ✅已修 | `cp` 备份 → 注入（md5 变化确认）→ `cp` 还原 → md5 相等 → 回绿 | 还原后 md5 `6f61e492…` 与注入前相等；`.work/source/llvm-test-suite` `git status` 干净 |
| 6 | `fail` 是否给出命令 + 首错行 | ✅不修（已满足） | 报告每例写 `compile`/`link`/`run` + `first_error` | `ft` 报告行含 3 条 compile/link/run 与 `first_error`（现场 grep） |
| 7 | `libc.a` 与 builtins 互相引用需确定性顺序 | ✅已修 | `--start-group … --end-group` | 205 个**链接成功**例 0 个 `undefined symbol`（`aarch64` 的 `RUNTIME_INIT` 在链接阶段失败、未计入 205） |

**未做/边界**：B/C 未跑；`ft`/`ClamAV` 维持 `fail`（`ISS-265` 待裁定）；未改 `spec/`/`contracts/`/`.work/source/**`/`Makefile`；未 commit/push。
