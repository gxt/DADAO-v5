# LLVM-103t: `flog` libcall 最小补齐（`initLibcallLoweringInfo` 未注册 `LOG_*`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`TESTCASES-048t`（现场来源 = A 类 222 单元 × 两档全量，`blocked 27` 中的 2 例；两档一致）、`ISS-267`（登记源，本册承接 ④）；同族先例 = `LLVM-080t`/`LLVM-087t`（f64/f32 取整与极值 libcall）、`ISS-193(b)`；契约依据：`contract-isa`（无 FP `log` 指令 ⇒ 必走库调用）、`ADR-0027`（compiler-rt 接入，与本册无关但同构建面）、`ADR-0025`（M8 范围）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

- **现场（逐字）**：`error: no libcall available for flog`（clang 后端 fatal），两档一致、driver 记 `blocked`：
  - `MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD`（`random.c`）
  - `MultiSource/Benchmarks/MiBench/consumer-lame`（`psymodel.c`）
- **报错路径（本笔实读）**：`llvm/lib/CodeGen/SelectionDAG/LegalizeDAG.cpp` 的 libcall 展开分支 —— `DAG.getLibcalls().getLibcallImpl(LC) == RTLIB::Unsupported` 时 `emitError("no libcall available for " + Node->getOperationName())`。**该消息只打印 DAG 节点名（`flog` = `ISD::FLOG`），不打印类型/`LC`** ⇒ 具体是 `LOG_F32` 还是 `LOG_F64` **必须在诊断里报出**（见验收 1）。
- **根因方向（本笔实读，待诊断确认）**：`DADAOSubtarget::initLibcallLoweringInfo()` 目前注册了 `MEM*`、f64/f32 的 `FLOOR/CEIL/TRUNC/ROUND/RINT/NEARBYINT/FMIN/FMAX`（`LLVM-080t`/`LLVM-087t`）、i128 除法/取余等，**没有任何 `RTLIB::LOG_*`**；而 `impl_log` / `impl_logf` 在 `RuntimeLibcalls.inc` 中**存在**（现场 `impl_log = 2694`）⇒ 属「已注册机制、漏注册条目」的**接线缺口**，不是新语义。
- **⚠ 口径纠正（本笔）**：`ISS-267` 原文把该例写成「**f80** `long double log`」。现场事实 = `clang/lib/Basic/Targets/DADAO.h:55` `LongDoubleWidth = LongDoubleAlign = 64`（`long double` ≡ `double`；`ADR-0030` 的 binary128 排 `M9`）⇒ 本 target 当前**不产生 f80**；诊断须**证伪/改正**该表述，并按实际 `LC` 落最小补齐。不得以「f80 不支持」为由放过。

## 接口规范

- **输入**：
  - `.work/source/llvm-project/`（组件源码检出）+ `components/llvm-project/patches/**` + `series` + `changelog.md`
  - 语料：`.work/source/llvm-test-suite/MultiSource/Benchmarks/DOE-ProxyApps-C/CoMD/`、`.../MiBench/consumer-lame/`（`patchless`，**只读**）
  - 安装根 `.dadao/cross-toolchain/`（改 `components/**` ⇒ 必须 `install-host` 后才新鲜）
- **输出**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOSubtarget.cpp.patch`（`initLibcallLoweringInfo` 增补）+ `series`（不增删文件则计数不变）+ `changelog.md` 一条
  - lit 向量：`llvm/test/CodeGen/DADAO/` 最小 `.ll`（`llvm.log.f64` / 需要时 `llvm.log.f32`）⇒ FileCheck 断言生成到 `log`/`logf` 的调用
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）、修前/修后编译日志、反汇编或 `.s` 片段
  - 本任务书完成区
- **约束**：只改 `components/llvm-project/**` + 本任务书（+ 台账）；**不动** `spec/`、`.tao/contracts/`、`contracts/`、语料；**只补实际被需要的**条目（见验收 2），不得顺手扩成「全部数学 libcall 大表」。

## 最小复现（自包含）

```c
/* /tmp/opencode/LLVM-103t/repro_flog.c */
#include <math.h>
#include <stdio.h>
volatile double x = 2.718281828459045;
int main(void) {
    double y = log(x);              /* ⇒ ISD::FLOG ⇒ libcall */
    printf("y=%.6f\n", y);          /* 期望 1.000000 */
    return (y > 0.999999 && y < 1.000001) ? 0 : 1;
}
```

- 编链口径同 `TESTCASES-048t` 静态档（`clang -target dadao-unknown-elf -nostdinc -I <MUSL>/…` + `ld.lld` + compiler-rt builtins `--start-group`）。
- 修前须复现 `no libcall available for flog`；修后 `qemu-dadao` 打印 `y=1.000000` rc=0。
- 若 f32 面亦被需要：同法加 `float`/`logf` 变体，**不得**只凭猜测添加。

## 验收标准

1. **诊断先落盘**：完成区写「命中的 `LC`（`RTLIB::LOG_F32` / `LOG_F64`，逐例）+ 该 `LC` 在 `initLibcallLoweringInfo` 中的现状 + `ISS-267` 的 f80 表述为何不成立（或成立的反证）」+ 修前报错原文。
2. **最小补齐清单**：逐条列出**实际新增**的 `Info.setLibcallImpl(RTLIB::<X>, RTLIB::impl_<y>)`（含行号与理由——「哪个用例需要」）；**未新增**的同类项也须一句说明（例如「`EXP_*` 未被任何现场例需要 ⇒ 不加」）。禁止无现场依据的批量铺开。
3. **两例转绿（两档）**：`CoMD`、`consumer-lame` 修前 `blocked`（报错原文）⇒ 修后 `pass`（参考 oracle 或 exit-only 判定沿用 `048t` 规则），两档一致。
4. **`TESTCASES-048t` 复跑**：`--only 'CoMD$' --only 'consumer-lame$'` 两档；`blocked 27 → 25`、`pass 193 → 195`、`fail 2`/`known-fail 0`/`excluded 0` **不变**；**无回归**（逐例 JSON diff，类别变化仅这 2 例）。
5. **向量**：新增 lit 用例 PASS，且对**修前**后端 FAIL（可达 FAIL 证据：归档修前 `.s`/报错 或注入）。
6. **可达 FAIL（≥2）**：例如删掉新增的 `setLibcallImpl` 行、把 `impl_log` 改成错误 impl ⇒ 断言/编译失败 ⇒ `cp`+md5 还原 ⇒ 回绿（**禁** `git checkout`/`restore`/`stash`）。
7. **门控（各留自身 rc）**：`check-patch-tree`、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`check-lit_gen`、`make check`(L1)。
8. **`install-host` 前置申报**：改 `components/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；启动前申报预计耗时），完成后核安装根新鲜并复跑第 3/4 条。

## 不做

- **不做** 全量数学 libcall 家族补齐（`exp`/`pow`/`sin`/`cos`/`log10`… 无现场需求者不加）。
- **不做** `long double` / binary128（`ADR-0030` → `M9`）、f80 支持。
- **不做** `clang` 前端崩溃 2 例（`ISS-267` ①，未派册）、`brind`/varargs（`LLVM-102t`）、`ISS-265`（参考可移植性，待裁）。
- **不改** `spec/`、`.tao/contracts/`、`contracts/`、语料/期望值。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-103t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕被检命令自身退出码；长输出落 `.work/log/llvm/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（如「某例需要的是 `EXP_*` 而不只是 `LOG_*`」导致范围变化）时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、非空 blob、`check-patch-tree` 全绿。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
