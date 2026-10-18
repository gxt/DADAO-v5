# INFRA-090t: musl `arch/dadao/bits/float.h` 常量块换 binary128

**模块**：infra
**项目里程碑**：M8
**依赖**：`ADR-0030`（`Accepted`：`D1` 常量、`D5` 只改 `bits/float.h`、`_l` 不改）、`ADR-0031`（`Accepted`：16 B 值半字顺序，供 `_l` 路径的 128 位值传递）、`LLVM-106t`（前端 `__SIZEOF_LONG_DOUBLE__=16` / `__LDBL_MANT_DIG__=113` + 后端 `f128`；**联动**，本册可先行、`_l` 转正验收须其就绪）、`INFRA-079t`（builtins TF 符号）、`ISS-250`
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

musl `arch/dadao/bits/float.h` 现状按 **binary64** 写死（`LDBL_MANT_DIG 53` / `LDBL_MAX_EXP 1024` / `DECIMAL_DIG 17`，文件头注释明确「`long double` is identically `double`」）。`ADR-0030 D1` 定案 `long double` = IEEE binary128（`LDBL_MANT_DIG` 113 / `LDBL_MAX_EXP` 16384 / `DECIMAL_DIG` 36），`D5` 要求**只换常量块、不改 `_l` 源码**（上游 113 位分支已在场：`.work/source/musl/src/` 下 `LDBL_MANT_DIG == 113` 命中 53 个文件）。不改则 `libc-test` 的 `math/{acoshl,asinhl,erfcl,lgammal,tgammal}`（`ISS-250`）继续偏移 1.5–10 ulp。

**现成同值模板**：`.work/source/musl/arch/aarch64/bits/float.h`（完整 113 常量块）⇒ 逐字对齐、**不自造数值**。

## 接口规范

- **输入**：
  - `.work/source/musl/`（组件源码检出，`git` 干净基线，musl 1.2.6）
  - `components/musl/patches/**` + `series` + `changelog.md`（补丁集化，`docs/Process-01` 树形补丁 + 一文件一补丁）
  - 决策：`ADR-0030`（`D1`/`D5`）、`ADR-0031`（`D6`/`D7`）
- **输出**：
  - `components/musl/patches/arch/dadao/bits/float.h.patch`：常量块换 binary128（`FLT_EVAL_METHOD 0` 保留；`LDBL_TRUE_MIN`/`MIN`/`MAX`/`EPSILON`、`LDBL_MANT_DIG 113`、`LDBL_MIN_EXP -16381`、`LDBL_MAX_EXP 16384`、`LDBL_DIG 33`、`LDBL_MIN_10_EXP -4931`、`LDBL_MAX_10_EXP 4932`、`DECIMAL_DIG 36`），文件头注释同步改写（删除「identically double」表述），数值逐字取 `arch/aarch64/bits/float.h`
  - `series` 计数不变（同文件已有一条补丁）；`changelog.md` 一条
  - 证据：`.work/evidence/<任务号>/run.sh`（default + `--inject`）
  - 本任务书完成区
- **约束**：只改 `components/musl/**` + 本任务书（+ 台账按裁决）；**不改** `spec/`、`.tao/contracts/`、`contracts/`、`components/llvm-project/**`（归 `LLVM-106t`）；**不改** musl `src/math/**` 任何 `_l` 源码（`ADR-0030 D5`）。

## 验收标准

1. **常量块逐字对齐**：`arch/dadao/bits/float.h` 的 12 个宏与 `arch/aarch64/bits/float.h` **逐字相同**（含 `L` 后缀与有效数字位数）；差异仅限文件头注释。
2. **头文件自洽（独立判据）**：`clang -target dadao-unknown-elf -E -dM` 的 `__LDBL_MANT_DIG__`/`__SIZEOF_LONG_DOUBLE__` 与头内 `LDBL_*` 一致（`LLVM-106t` 就绪时）；未就绪时以「头内数值 = binary128 手算值」独立核对（`DECIMAL_DIG = ceil(1 + 113·log10 2) = 36` 等）。
3. **`_l` 分支在场**：构建后 `nm`/预处理器核 `LDBL_MANT_DIG == 113` 分支被选中（现场统计命中数，不写死）；`_l` 源码零改动（`git diff --name-only` 对账）。
4. **`libc-test` 5 例（`LLVM-106t` 就绪后）**：`math/{acoshl,asinhl,erfcl,lgammal,tgammal}` 静态档 `known-fail/blocked → pass`，且 `TESTCASES-047t` 静态档整体 `fail=0` 不回归（逐例记账）；未就绪时完成区标 `BLOCKED` + 替代证据。
5. **可达 FAIL**：≥2 处注入（例如：把 `LDBL_MANT_DIG` 改回 53、`DECIMAL_DIG` 改回 17）⇒ 对应断言 `[FAIL]`、脚本 rc=1 ⇒ `cp` + md5 还原 ⇒ 回绿、rc=0（**禁** `git checkout`/`restore`/`stash`）。
6. **门控（各留自身 rc）**：`check-patch-tree`、`check-component-changelog`、`check-musl-freshness`、`make check`(L1)；`make build-musl` / `build-musl-shared` rc=0（不并发）。

## 不做

- **不改** `_l` 源码、`libm`、`math` 面实现（`ADR-0030 D5`）。
- **不改** `spec/`、`.tao/contracts/`、`contracts/`、`components/llvm-project/**`。
- **不做** `ISS-250` 之外的 binary128 精度调优；不做 `f80`。
- **不做** 动态档/两档全量复跑（`TESTCASES-*` 归其各自任务）。

## 硬约束

1. 临时目录 `/tmp/opencode/INFRA-090t/`；workdir = 仓库根、相对路径；禁出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；显式 staging（**禁** `git add -A`/`.`）。
3. 完成区与真实输出逐条对齐；留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）；复杂输出落 `.work/log/infra/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 用户裁定须把**原话**写入本任务书。
7. 补丁导出纪律：`/tmp` 写入、行数下限、非空 blob、`check-patch-tree` 断言全绿。

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
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）
