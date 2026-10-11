# LLVM-080t: P1 后端补齐（取整 / fmin-fmax / fabs-copysign 双精度）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-079t`（P0；同改 `components/llvm-project/patches` ⇒ 串行）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - 用户裁定（2026-10-11；`INTEG-033k §裁定汇总 #6`）：**P1 后端纳入 M7** = `floor`/`ceil`/`trunc`/`round`/`rint`/`nearbyint`、`fmin`/`fmax`、`fabs`/`copysign`（**双精度**）。
  - 缺口证据（实测）：`.work/log/testcases/picolibc-probe-fp.log`——`floor_d/ceil_d/trunc_d/round_d/rint_d/nearbyint_d` = `NOLIBCALL`；`fmin_d/fmax_d` = `NOLIBCALL`；`fabs_d/copysign_d` = `CANNOT_SELECT`（`bitcast`）。`ISS-188`。
  - `contract-fp.md`、`contracts/opcodes.yaml`（scope `fp`）——ISA FP 指令集（取整类如 `ftroot`/`ftcls` 等**以合约/编码表为准**）。
- **输出**：
  1. 补齐 P1 类 ISel/lowering：范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`；**优先 ISA 现成指令**，无现成指令者按 `spec`/`contracts` 口径（libcall 或软件序列，须显式登记依据）。
  2. lit / CodeGen 用例（期望值独立派生，禁反填）。
  3. 重建工具链（`setsid` 脱离、`JOBS=8`、申报耗时）。
- **约束**：
  - **依赖 `LLVM-079t` 已落地**（P0 的 `bitcast`/`setcc` 是 P1 部分项的前置）；同改补丁集 ⇒ **串行**。
  - **计数不写死**：以探针现场统计为准。
  - 只动任务范围，越界须披露。

## 验收标准

1. **P1 类清零**：重跑同一 FP 探针脚本——`NOLIBCALL`/`CANNOT_SELECT` 中 **P1 类（取整六项 / fmin-fmax / fabs-copysign 双精度）清零**（现场统计真实输出）。
2. **语义 E2E**：至少 1 个 FP 相关 picolibc test（如 `test/test-math/test-floor.c`/`test-ceil.c`）编/链/跑出正确退出码（QEMU semihosting）。
3. **ISA/口径证据**：逐类给出 `llc -S` 真实片段或登记所用 libcall/软件序列依据。
4. **门控**：`make check` + lit 全量档 **EXIT=0**；`check-patch-tree` EXIT=0。
5. **反例门控**：新增用例**能失败**（注入错误期望值 ⇒ FAIL ⇒ `cp`+md5 还原 ⇒ 回绿）。
6. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
