# LLVM-140t: McCat 18-imp `L_canny.c` -O2 SIGABRT（SelectionDAG RUW 类型不匹配）

**模块**：llvm
**项目里程碑**：M10
**依赖**：LLVM-139t（当前后端基线）
**状态**：待开始

## 背景

夜跑 `2026-10-29-12` 的 `tset:llvm-ts` static/dynamic 两档都在同一用例失败：

- 用例：`MultiSource/Benchmarks/McCat/18-imp`
- 文件：`L_canny.c`
- 编译：`-O2`
- 现象：clang 在函数 `dfilter` 的指令选择阶段 SIGABRT（rc=134）
- 断言：`SelectionDAG::ReplaceAllUsesWith` 的
  `Cannot use this version of ReplaceAllUsesWith!`
- 结果：`213 pass / 0 fail / 1 blocked / 8 excluded`；夜跑整体 rc=2，报告 `2026-10-29-12` 不能作为 M10 证据。

已确认可复现，不是超时/OOM/flaky。复现命令见下；崩溃输出已留 `.work/log/llvm/LLVM-140t/LLVM-140t-clang-crash.log`。

## 目标

1. **最小化并定位**
   - 用 `dfilter`/`L_canny.c` 生成可重复的 reduced case（优先 `llvm-reduce` 或裁剪 IR）；
   - 确定是 DADAO `DAGToDAGISel`/pattern/自定义 lowering 的哪一步触发，记录调用栈或 MIR/DAG 证据；
   - 检查是否与 LLVM-137/138/139 的后端改动相关；如相关，指出具体文件/条件。
2. **最小修复**
   - 只改 DADAO 后端必要代码/补丁；不关闭断言、不吞异常、不把用例标 known-fail/blocked 了事；
   - 不改变全局 ABI、寄存器类、code model、i64 语义；不碰 QEMU/spec。
3. **回归测试**
   - 新增 lit/CodeGen 回归（优先 reduced `.ll`，覆盖 `ReplaceAllUsesWith` 类型不匹配路径）；
   - 精确复现命令编译 rc=0；
   - `run_llvm_ts_user.py --only 'McCat/18-imp' --link-mode static|dynamic` 两档 rc=0；
   - 相关 LLVM-137/138/139 向量与 `check-lit` 不回归。
4. **重跑最终夜跑（主会话）**
   - engineer 只交定向验证；修复合入后由主会话重跑 `make check-night`（长任务，主会话 `setsid nohup`，报告目录用新的本地 `YYYY-MM-DD-HH`）。

## 精确复现

```bash
.dadao/cross-toolchain/bin/clang -target dadao-unknown-elf -nostdinc \
  -I .work/source/musl/arch/dadao -I .work/source/musl/arch/generic \
  -I .work/source/musl/obj/include -I .work/source/musl/include \
  -I .work/source/llvm-test-suite/MultiSource/Benchmarks/McCat/18-imp \
  -O2 -DNDEBUG -w -DSMALL_PROBLEM_SIZE -Wno-implicit-int \
  -c .work/source/llvm-test-suite/MultiSource/Benchmarks/McCat/18-imp/L_canny.c \
  -o /tmp/opencode/LLVM-140t/L_canny.o
```

期望修复后 rc=0；当前 rc=134。崩溃 reproducer 可由上述命令重生成；原始副本在 `/tmp/opencode/LLVM-140t/`（临时目录，不作持久证据）。

## 验收

- 上述精确命令 rc=0；生成对象非空。
- `run_llvm_ts_user.py --only 'McCat/18-imp'` static/dynamic rc=0。
- 新增回归测试全绿；`make check-lit`、`make check`、`check-patch-tree`、`check-source-state` rc=0。
- 证据 `.work/evidence/<任务号>/run.sh`：注入→FAIL→`cp`+md5 还原→PASS。
- 完成区 ≤30 行；状态 `待验收`；`milestones.md` 行同步；临时目录 `/tmp/opencode/LLVM-140t/`。
- 不跑完整夜跑（主会话负责）；不跑 `check-full`（未授权）。

## 约束

- 只改 LLVM 后端/补丁/测试/文档；不改 spec/QEMU/contracts。
- 不提交、不 push；`make build-llvm`/`make install-host` 等重建先申报耗时。
- 失败保留完整现场（命令、输出、退出码、日志）；不得以排除用例或放宽断言代替修复。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
