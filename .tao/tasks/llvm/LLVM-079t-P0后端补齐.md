# LLVM-079t: P0 后端补齐（FP 载入/取值/bitcast/select_cc/cttz）

**模块**：llvm
**项目里程碑**：M7
**依赖**：无（M6 已验证态；`INTEG-033k` 裁定 #4）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #4`）：**P0 后端纳入 M7** = ① `f32→f64 anyext` 载入 ② FP 比较取值 **`setcc`** ③ `f64↔i64 bitcast` ④ `f64 select_cc` ⑤ `i64 cttz`；**优先用 ISA 现成指令**（如 `ft2fo`）。
  - 缺口证据（**实测，非估算**）：`.work/log/testcases/picolibc-probe-summary.log`——341 个 picolibc test 编译探针中 **64 个 `BACKEND_CANNOT_SELECT`**，其 **distinct node 签名** = `f64,ch = load …`（40，= `f32→f64` anyext 载入）/ `i64 = setcc … ConstantFP:f64`（16+1+1）/ `i64 = cttz`（1）/ `i64 = bitcast`（1）/ `f64 = bitcast`（2）/ `f64 = select_cc … setlt`（1）。另见 `.work/log/testcases/picolibc-probe-fp.log`。
  - `ISS-188`（FP 完备性缺口）；`contract-fp.md`（FP/RF 指令）；`contracts/opcodes.yaml`（scope `fp`）——FP 指令已实现于 MC/QEMU。
- **输出**：
  1. DADAO 后端 ISel 补齐 5 类 P0 模式：范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（`DADAOISelLowering.cpp`/`DADAOInstrInfo.td` 等），**优先复用 ISA 现成指令**（FP↔RD 转换/位操作已有指令，如 `ft2fo`/`rf2rd`/`rd2rf` 等，**以 `contracts/opcodes.yaml`/`contract-fp.md` 为准**）。
  2. lit / CodeGen 用例：新增覆盖 5 类模式（**期望值独立派生自 `spec`/`contracts`，禁从 `llc` 反填**）。
  3. 重建工具链（改 `components/llvm-project/patches` ⇒ 须重建；`setsid` 脱离、`JOBS=8`、`lessons §8.21`；**启动前申报预计耗时**）。
- **约束**：
  - **最小改动**：只补 P0 五类；**P1（取整/min-max/fabs/copysign）归 `LLVM-080t`**。
  - **`ft2fo` 等 ISA 现成指令优先**，不自造 lowering；无 ISA 依据的形态须显式登记。
  - **计数不写死**：探针/门控计数**现场统计**；验收写「P0 类清零」而非固定条目数。
  - 只动任务范围，越界须披露。

## 验收标准

1. **P0 类清零**：以**同一 picolibc 编译探针脚本**重跑（`.work/log/testcases/picolibc-probe-compile.sh` 及其产物 `picolibc-probe-compile-table.tsv`）——**`BACKEND_CANNOT_SELECT` 中 P0 类签名（load-anyext / setcc / bitcast / select_cc / cttz）全部清零**（现场统计真实输出；**非抽样、非估算**）。
2. **语义 E2E**：至少 1 个真实 picolibc test（P0 相关，如 `test/test-math/*` 或 `test/test-stdio/test-fprintf-*`）编/链/跑出正确退出码（QEMU semihosting）。
3. **ISA 现成指令证据**：P0 类生成的汇编中出现预期 ISA 指令（`llc -march=dadao -S`，逐类给出真实片段）。
4. **门控**：`make check`、`make check-lit`（或等价的 lit 全量档）**EXIT=0**；`check-patch-tree` EXIT=0。
5. **反例门控**：新增 lit 用例**能失败**（注入错误期望值 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
