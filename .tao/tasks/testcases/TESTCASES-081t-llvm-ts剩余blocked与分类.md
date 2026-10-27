# TESTCASES-081t: llvm-ts 剩余 blocked 与分类收口

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-077t、TESTCASES-078t、TESTCASES-079t、TESTCASES-080t
**状态**：待验收

## 背景（自包含，2026-10-27 `TESTCASES-077t` 全量实测）
077t 后 llvm-ts 全量 rc 仍为 1；剩余非 078/079/080 项：

1. `gawk` / `make` / `p2c`：原拟用 078 胶水 patch 修复。**用户 2026-10-27 裁定「选 1」**：按上游 CMake 证据记 `excluded` —— `MultiSource/Benchmarks/MallocBench/CMakeLists.txt:1-4` 只 `add_subdirectory(espresso)`（:1）/`gs`（:2）/`cfrac`（:4，:3-5 守卫），三个目录从不进入上游构建；不再尝试胶水修复。
2. `archie-client` / `plot2fig`：缺 BSD `re_comp`/`re_exec`；上游 CMake 用 `check_function_exists(re_comp)` 守卫 ⇒ 上游本就不为该 libc 构建该 target。建议按「架构/libc 不适用」记 `excluded`（带 CMake 源码指针），但这推翻了 `TESTCASES-050t` 的「保留 blocked」书面口径，须在本册明确改口径。
3. `ClamAV`：077t 全量中无明确归属（既非 077 三例，也非 078/079/080）；先诊断其 blocked 原因，再决定 patch/排除。
4. 驱动判据缺口：`gawk` 补方言后 guest NULL 解引用 → 自处理 SIGSEGV → `tkill(SIGIOT)` → 宿主 SIGABRT；`SIG_DELIVERY_RE` 不识别 `si_addr=NULL` 形态，误记 `blocked`。须补判据（真实 guest 转发 ⇒ fail；QEMU internal/timeout ⇒ blocked），并加可达 FAIL 自检。

## 目标
1. `gawk`/`make`/`p2c` 按上游 `MallocBench/CMakeLists.txt:1-4`（只构建 espresso/gs/cfrac）逐例记 `excluded`，理由引用实际行；不记 known-fail/blocked，不造 stub。
2. `archie-client`/`plot2fig` 按上游 `check_function_exists` 证据记 `excluded`，并更新 `TESTCASES-050t`/Process 相关口径（不再保留 blocked）。
3. 诊断 `ClamAV`：能修则最小修复，确属上游不适用则按证据 `excluded`；不得无依据 known-fail。
4. 修 `SIG_DELIVERY_RE`/分类判据缺口，覆盖 `si_addr=NULL` + `tkill(SIGIOT)` 形态；加反例。
5. 目标：llvm-ts static+dynamic **rc=0，fail=0、blocked=0、known-fail=0**（与 078/079/080 合并）；excluded 仅限有源码/CMake 证据的上游不构建项。

## 验收
- 定向：`gawk`/`make`/`p2c` 与 `archie-client`/`plot2fig` 为 excluded（理由含 CMake 实际行，不是 fail/blocked）；`ClamAV` 两档 pass（byte-exact）。
- 判据反例：构造/引用 `si_addr=NULL` + `tkill(SIGIOT)` 形态 ⇒ 分类从 blocked 变 fail（可达 FAIL）；还原回绿。
- 定向两档无回归；`make check` rc=0；证据 `.work/evidence/TESTCASES-081t/run.sh`（注入→FAIL→`cp`+md5 还原→PASS）。全量 `check-tset-llvm-full` 按限制留后续。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-081t/`。

## 约束
- 只改 `tests/tset/llvm-ts/`、`tools/testcases/tset/llvm-ts/`、胶水/参考、相关文档/任务书；不改 spec/qemu/LLVM 语义。
- `llvm-test-suite` 保持 `patchless=true`，不改 components.lock；不建组件 patch set。
- 不放宽比较、不静默跳过；每个 excluded 必须有源码/构建系统证据。
- **不提交、不 push**；长跑申报耗时；不跑无关全量。

## 完成区

**状态**：已完成（用户 2026-10-27 裁定「**选 1**」：gawk/make/p2c 按上游 CMake 证据排除）

**用户裁定原话（摘要）**：「用户裁定：**选 1——gawk/make/p2c 按上游 CMake 证据排除**（`MultiSource/Benchmarks/MallocBench/CMakeLists.txt` 只 `add_subdirectory(espresso/gs/cfrac)`）。」——因此不再尝试语料胶水修复，三例逐例记 `excluded`。

**测试结果**：
- `.work/evidence/TESTCASES-081t/run.sh` → **13/13 PASS rc=0**：C2 注入（删 `si_addr=NULL` 分支 ⇒ selfcheck 报 `si_addr=NULL delivery line is not recognised` ⇒ `cp`+md5 还原 ⇒ 回绿）。
- `--only 'MallocBench/gawk|make|p2c'`（static；dynamic 同路径同判据）→ rc=2 + `declared exclusion`，不执行、不记 fail/blocked；`--list` 现场：214 executed + **8 excluded** = 222 discovered。
- ClamAV `--link-mode both --only 'ClamAV$'`：static/dynamic 均 `pass=1 fail=0 known-fail=0 blocked=0`，`matched (byte-exact)`（`clamscan.reference_output.big-endian`）。
- `--only archie-client|plot2fig` → rc=2 + `declared exclusion`（回归不成立）；`make check` rc=0。

**修改文件**：
- `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py`：`STRUCTURAL_EXCLUSIONS` +gawk/make/p2c（引 `MallocBench/CMakeLists.txt:1-4` 只建 espresso/gs/cfrac）+ 原 archie/plot2fig；docstring 同步；保留 `CASE_STDIO_GLUE`（ClamAV）、`SIG_DELIVERY_RE` 的 `si_addr=NULL` 与 `signal_delivery_selfcheck`、`ISS265_ADMISSION` 清空。
- `tests/tset/llvm-ts/patches/glue/glibc_stdio_buffer.c`（新）、`patches/README.md`、`tests/tset/llvm-ts/README.md`、`.tao/archive/M8/testcases/TESTCASES-050t-驱动与口径收尾.md`（archie 旧口径作废注）。
- `.work/evidence/TESTCASES-081t/run.sh`、`.work/log/testcases/TESTCASES-081t-*.log`（证据，不入库）；`.tao/knowledge/milestones.md`、本任务书。

**新发现/坑**：
1. gawk/make/p2c 的目录自带 CMakeLists（`llvm_multisource()`），但父 `MallocBench/CMakeLists.txt:1-4` 从不 `add_subdirectory` 它们——「有 CMakeLists」≠「上游会构建」，排除判据应看父链。
2. ClamAV 参考首行位置 = glibc stdio 缓冲（`st_blksize`=4096）而非程序行为；musl `BUFSIZ`=1024 提前 flush，胶原语料改不了，用 `glibc_stdio_buffer.c` 复现参考 libc 语义（比较仍 byte-exact）。
3. musl `setvbuf(f, NULL, ..., size)` 不采用 size（必须给调用方 buffer）；`qemu -strace` 的 `si_addr=NULL` 是合法投递形态。

**遗留问题**：未跑 `check-tset-llvm-full`/`check-full`/`check-night`（按限制，全量留后续批次）；gawk/make/p2c 的语料缺陷（regex 64 位、缺 `glob/glob.h`/`p2crc`）已记录但不影响排除结论，若将来上游补全语料可另立任务复核。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-27）

**审查方式**：自主逐行审 diff（驱动 208 行 + 5 个文档/新胶水文件）并逐条跑证据脚本；独立验收由 `/complete` 的 reviewer 承担。

**判决**：全部 finding 已修；gawk/make/p2c 按用户裁定「选 1」转为有 CMake 证据的 `excluded`，无未修项 → `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `signal_delivery_selfcheck` 的 `QEMU internal` 分支恒真（vacuous） | ✅已修 | 抽出 `signal_delivery_hit()`（internal 优先）供 probe 与自检共用 | 证据 C1/C2 + 注入 NULL 分支真红 |
| F2 `CASE_STDIO_GLUE` 注释写 `malloc(4096)`，实现用静态数组 | ✅已修 | 注释与实现一致 | 驱动 import + ClamAV 两档 pass |
| F3 证据脚本 C2 探针退出码取反（problems 存在却 exit 0） | ✅已修 | `sys.exit(1 if problems else 0)` | 重跑 9/9 PASS，注入项真红 |
| F4 ClamAV 用固定 4096 而非宿主 `st_blksize`，是否可复现 | ❌不修（有据） | 无 | 参考由上游机器生成，胶水要复现的是**参考的**缓冲语义；4096 即参考文档可复现的隐含值（glibc 常规文件默认），且写入 `why` |
| F5 `ISS265_ADMISSION` 清空后自检期望表仍写 ClamAV | ✅已修 | `expected = {}` | 驱动自检 C1 绿；ClamAV 走 byte-exact pass 而非 known-fail |
| F6 gawk/make/p2c 未 pass | ✅已修（用户裁定） | `STRUCTURAL_EXCLUSIONS` +3（引 `MallocBench/CMakeLists.txt:1-4`） | 证据 C3/C4：`--only` rc=2 + declared exclusion；13/13 PASS |
| F7 C4 只校验理由文本子串（自指），未核上游 CMake 实体 | ✅已修 | 证据增 C4b：现场解析 `MallocBench/CMakeLists.txt` 的 `add_subdirectory` 集合 | C4b PASS：`['espresso', 'gs', 'cfrac']`，三例均不在集合 |


