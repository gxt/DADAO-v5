# TESTCASES-077t: llvm-ts 架构专用用例与超时/编译门控

**模块**：testcases
**项目里程碑**：M10
**依赖**：TESTCASES-076t
**状态**：待开始

## 背景（2026-10-27 全量实测，自包含）
`check-tset-llvm-full`（static）在 `TESTCASES-076t` 全量中失败，除语料 UB 外还有三类**非 DADAO 语义问题**：

1. `SingleSource/Benchmarks/Misc/aarch64-init-cpu-features`：
   - 源码 `.work/source/llvm-test-suite/SingleSource/Benchmarks/Misc/aarch64-init-cpu-features.c:5` 引用 `__aarch64_cpu_features`，`:8/:10/:13` 用 `RUNTIME_INIT`（AArch64 的 `__init_cpu_features*`）；
   - DADAO 无此符号 ⇒ `ld.lld: undefined symbol: RUNTIME_INIT`，被记 `BLOCKED`。
2. `MultiSource/Applications/Burg`：
   - `be.c:335` `parameter 'to' was not declared, defaults to 'int'`（ISO C99 起为 error）⇒ `BLOCKED`（compile error）。
3. `MultiSource/Benchmarks/mafft`：
   - 超时 `1620s`（27 min）⇒ `BLOCKED`（timeout）。

这三项**不是** DADAO 编译器/后端缺陷；但当前驱动按「有 main 就收」把它们收进全量，导致全量/夜跑无法全绿。

## 目标
1. **架构专用排除**：在 `tools/testcases/tset/llvm-ts/run_llvm_ts_user.py` 增加**逐例、带源码依据**的「架构专用/不适用」排除表，至少含 `aarch64-init-cpu-features`；扫描同目录/同套件其它 aarch64/riscv/x86 专用用例，按同口径处理。排除必须是 `excluded`（不是 pass/fail/known-fail），理由含源码文件:行与符号证据；不得用宽泛通配。
2. **Burg 编译口径**：用**最小 per-case 编译参数**修复（如 `-Wno-error=implicit-int` 或该例 `-std=gnu89`，二选一以实测为准），不得全局放宽所有套件；确认不改变其它用例命令。
3. **mafft 超时**：先实测单例真实耗时；按需提高**该例** timeout（如 3600s）或给出可复现的加速方案；不得把全局 `DEFAULT_TIMEOUT` 无据放大；夜跑总时长须记录。
4. 不改测试期望/断言，不把「适用用例」降级为 known-fail/blocked。

## 验收
- 定向（static+dynamic）：`aarch64-init-cpu-features` 为 `excluded`（理由指向源码）；`Burg` 编译并运行到自身判定；`mafft` 在设定 timeout 内完成并 pass。
- `make check-tset-llvm-full`（static+dynamic）**rc=0**，且无未知 `fail`/`blocked`；`known-fail` 仅限既有已裁定项（ISS-265/ISS-266）。
- `make check` rc=0；`check-case-ledger` rc=0；证据 `.work/evidence/<任务号>/run.sh`（含注入→FAIL→`cp`+md5 还原→PASS）。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/TESTCASES-077t/`。

## 约束
- 只改本任务范围内的 `tools/testcases/tset/llvm-ts/`、`tests/tset/llvm-ts/`、`Makefile`、索引/ledger、任务书/milestones；不改 spec/qemu/LLVM 语义。
- **不提交、不 push**；不跑无关全量；长跑（mafft）申报预计耗时。
- 排除项必须可审计：`excluded` 行含 `id + reason + 源码指针`，不得静默跳过。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
