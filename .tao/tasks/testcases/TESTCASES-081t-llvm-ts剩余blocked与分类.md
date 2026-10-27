# TESTCASES-081t: llvm-ts 剩余 blocked 与分类收口

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-077t、TESTCASES-078t、TESTCASES-079t、TESTCASES-080t
**状态**：待开始

## 背景（自包含，2026-10-27 `TESTCASES-077t` 全量实测）
077t 后 llvm-ts 全量 rc 仍为 1；剩余非 078/079/080 项：

1. `gawk` / `make` / `p2c`：C89 语料 + glibc-only（`sys_nerr`）/ `logf` 与 musl `math.h` 冲突，**编译参数无解**，需语料胶水 patch（同 078 的 A 方案：`tests/tset/llvm-ts/patches/`，应用到 `.work/` 副本，`llvm-test-suite` 保持 patchless）。
2. `archie-client` / `plot2fig`：缺 BSD `re_comp`/`re_exec`；上游 CMake 用 `check_function_exists(re_comp)` 守卫 ⇒ 上游本就不为该 libc 构建该 target。建议按「架构/libc 不适用」记 `excluded`（带 CMake 源码指针），但这推翻了 `TESTCASES-050t` 的「保留 blocked」书面口径，须在本册明确改口径。
3. `ClamAV`：077t 全量中无明确归属（既非 077 三例，也非 078/079/080）；先诊断其 blocked 原因，再决定 patch/排除。
4. 驱动判据缺口：`gawk` 补方言后 guest NULL 解引用 → 自处理 SIGSEGV → `tkill(SIGIOT)` → 宿主 SIGABRT；`SIG_DELIVERY_RE` 不识别 `si_addr=NULL` 形态，误记 `blocked`。须补判据（真实 guest 转发 ⇒ fail；QEMU internal/timeout ⇒ blocked），并加可达 FAIL 自检。

## 目标
1. 用 078 的测试胶水 patch 机制修 `gawk`/`make`/`p2c`（逐例、最小、可审计），不改上游源码树本体。
2. `archie-client`/`plot2fig` 按上游 `check_function_exists` 证据记 `excluded`，并更新 `TESTCASES-050t`/Process 相关口径（不再保留 blocked）。
3. 诊断 `ClamAV`：能修则最小修复，确属上游不适用则按证据 `excluded`；不得无依据 known-fail。
4. 修 `SIG_DELIVERY_RE`/分类判据缺口，覆盖 `si_addr=NULL` + `tkill(SIGIOT)` 形态；加反例。
5. 目标：llvm-ts static+dynamic **rc=0，fail=0、blocked=0、known-fail=0**（与 078/079/080 合并）；excluded 仅限有源码/CMake 证据的架构/libc 不适用项。

## 验收
- 定向：`gawk`/`make`/`p2c` pass；`archie-client`/`plot2fig` 为 excluded（理由含 CMake 行）；`ClamAV` 有结论（pass/excluded + 证据）。
- 判据反例：构造/引用 `si_addr=NULL` + `tkill(SIGIOT)` 形态 ⇒ 分类从 blocked 变 fail（可达 FAIL）；还原回绿。
- `make check-tset-llvm-full`（static+dynamic）rc=0，零 fail/blocked/known-fail；`make check` rc=0；证据 `.work/evidence/<任务号>/run.sh`。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-081t/`。

## 约束
- 只改 `tests/tset/llvm-ts/`、`tools/testcases/tset/llvm-ts/`、胶水/参考、相关文档/任务书；不改 spec/qemu/LLVM 语义。
- `llvm-test-suite` 保持 `patchless=true`，不改 components.lock；不建组件 patch set。
- 不放宽比较、不静默跳过；每个 excluded 必须有源码/构建系统证据。
- **不提交、不 push**；长跑申报耗时；不跑无关全量。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
