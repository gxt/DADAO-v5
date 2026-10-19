# LLVM-120t: 静态 PIE 的 `_DYNAMIC` 改为运行期求（`ISS-245`）

**模块**：llvm
**项目里程碑**：M9
**依赖**：`LLVM-117t`（动态 TLS + T5 收口，`待验收`；同一 musl 自举面）、`INFRA-085t`（C1 动态自举 + `dlstart.c` 补丁来源，已归档）、`INFRA-096t`（安装根新鲜度，`待验收`）、`LLVM-118t`/`LLVM-119t`（同改工具链须串行；本册只改 `components/musl/**`，与二者在**构建树/安装根**上仍是串行关系）
**状态**：待开始

> **编号（现场取号，2026-10-20）**：`llvm` 现存最大 = `LLVM-117t`（本批另占 `118`/`119`）⇒ 取 **`120`**（编写前 `grep -rn 'LLVM-120' .tao/` 零命中）。
> **归口说明**：`ISS-245` 的 `scope` 记为 `infra`，但其修法面 = **LLVM 工具链产出的 `rcrt1.o` + musl 端口自举汇编**（`components/musl/patches/arch/dadao/crt_arch.h.patch`）。本批按**执行面**归 `llvm`（与 `LLVM-117t` 同族）；若验收时认定应归 `infra`，在完成区披露即可，不重开册。

## 执行环境
**执行环境**：本地

## 立项来源 / 现场事实（`ISS-245` 原始记录 + 现场源码）

- **现象**：静态 PIE 的 `crt/rcrt1.o` 在 `.text` 里留 **3 条 `R_DADAO_ABS48 _DYNAMIC`**（偏移 `0x4/0x8/0xC`），即 `_DYNAMIC` 是**链接期绝对地址**；装载基址 ≠ 链接地址时自举取错（静默错面）。复现命令：`llvm-readobj --relocations .work/source/musl/obj/crt/rcrt1.o`（现场 Section `.rela.text` = 3 条；同对象 `.rela.got` 的 `ABS48` 落在可写节、装载期转 `RELATIVE`，属允许）。
- **根因（源码现场）**：
  - `components/musl/patches/arch/dadao/crt_arch.h.patch:79-86`：`#ifdef SHARED` 下分两态——有 `DL_DYNAMIC_FROM_LOAD_BASE` ⇒ `rd2rb {rb17}, {rd0}`（运行期，C1 落地）；否则 ⇒ `set.rb rb17, _DYNAMIC`（**链接期绝对**）。
  - `components/musl/patches/ldso/dlstart.c.patch:21`：`#define DL_DYNAMIC_FROM_LOAD_BASE 1` **只在 `ldso/dlstart.c` 自身编译单元**（`#ifndef START` 分支）成立。
  - `.work/source/musl/crt/rcrt1.c:1-3`：`#define START "_start"` / `#define _dlstart_c _start_c` / `#include "../ldso/dlstart.c"` ⇒ `START` 已定义 ⇒ **不走** `DL_DYNAMIC_FROM_LOAD_BASE` ⇒ 绝对分支。
  - ldso 侧的运行期求法已在 `_dlstart_c` 内实现（`AT_BASE + PT_DYNAMIC.p_vaddr`，见 `dlstart.c.patch` 的 `#ifdef DL_DYNAMIC_FROM_LOAD_BASE` 块）；**静态 PIE 无 `AT_BASE`** ⇒ 需另一个运行期来源（`AT_PHDR`/自身 phdr 同法），这正是 `ISS-245` 给的启发式方向。
- **范围依据**：`-static-pie` **不在** `ADR-0025 D6` 的 P1/P2/P3 交付范围（当前不阻断在役判据）；但 `rcrt1.o` **随 crt 安装集发布** ⇒ 要么正确、要么**显式可判失败**，不得静默错。**派单方向 = 改为运行期求**（即 `ISS-245` 建议的 (a)）；若现场证明不可行，按验收第 5 条停下报告，**不得**自行改成「声明不支持」。
- **契约**：`.tao/contracts/contract-dynlink.md §6.2/§6.3`（`AT_BASE` 语义与自举）；`contract-elf.md §2.2`（重定位类型表，`ABS48`=6 / `PCREL_HI`=14 / `PCREL_LO`=15）；`ADR-0026 D3`（仅 GNU hash）/`D5`（GOT/TP 访问）；`ADR-0019 D12`（**类型号冻结**）；`ADR-0029 D2/D4`（PC 相对配对与 PIC 惯用法）。

## 接口规范

- **输入**：`components/musl/patches/arch/dadao/crt_arch.h.patch`、`components/musl/patches/ldso/dlstart.c.patch`、`components/musl/patches/series`、`.work/source/musl`（组件源）、安装根 clang/ld.lld、`tools/infra/build_musl.py`、`tools/infra/apply_series.py`。
- **输出**：
  1. **诊断先行**：静态 PIE（无解释器、无 `AT_BASE`）在**装载基址 ≠ 链接地址**时，从哪些运行期信息可定位自身 `PT_DYNAMIC`（候选：`AT_PHDR` + `PT_PHDR.p_vaddr` / 入口 PC 页对齐 / auxv 其它项）；给出成立条件与失败条件（页对齐、`p_vaddr` 关系），并说明为何对 `crt1.o`（非 PIE）无影响；
  2. **实现**：`crt_arch.h.patch` 的 `START` 分支改为运行期求值（`.got` 相对取址 / `AT_PHDR` 派生二选一，按诊断结论）；`crt1.o`（非 PIE）**逐字节不变**；
  3. 独立 oracle：Python/`llvm-readobj` 解析 ELF（`PT_PHDR`/`PT_DYNAMIC`/`p_vaddr`/auxv）独立算出期望 `_DYNAMIC`，与运行期探针实际值比较；**不从实现输出反推**；
  4. 证据 `.work/evidence/<任务ID>/run.sh`（default + inject）+ 日志 `.work/log/llvm/LLVM-120t-*.log`（或 `musl/`，按所在模块）。
- **约束**：**不改** `spec/` / `contracts/`（机器数据）/ `.tao/contracts/**` / `tests/vectors/**`；**不改** `ADR` 决策；musl 改动必须落**补丁文件**（一文件一补丁 + `series` 同步，`check-patch-tree` rc=0）；改 `components/musl/**` 后须 `apply-series` + `build-musl`/`build-musl-shared`；**`install-host` 前置**（musl 编译消费安装根工具链）；不 commit/push。

## 验收标准

1. **对象级（可达、非语义）**：重建后 `rcrt1.o` 的 `.rela.text` 中 `R_DADAO_ABS48 _DYNAMIC` **计数 = 0**；`.rela.text` 其余重定位逐条列出并解释（不得只是「消失」，若改用 `PCREL_HI/LO` 或 GOT 槽，须证明配对完整、无悬空）；`crt1.o` 与改前 **md5 相同**（`cmp` 逐字节）。
2. **运行期正确（核心判据）**：`-static-pie` 链接的探针程序在**装载基址 ≠ 链接地址**下运行成功；须证明基址确实不同（用 `-B <base>` / 随机化 / 显式 `guest_base` 之一，写明所选方式与实测两个地址），退出码 = 手算值（如 7），stdout 逐字节等于手写期望。
3. **独立 oracle**：脚本从 ELF + auxv 独立算 `_DYNAMIC`（`AT_PHDR − PT_PHDR.p_vaddr + PT_DYNAMIC.p_vaddr`）并与探针读到的 `_DYNAMIC`/`rb17` 比较；两值相等且与「链接期值」**不同**（证明不是蒙对）。
4. **回归**：`build-musl` + `build-musl-shared` rc=0；`check-musl-freshness` rc=0（重链戳记）；`ldso` 自身（`_dlstart`）动态自举不回归（最小动态 ELF 跑通 exit 0）；静态档 047t 抽样（含 `functional/setjmp` 等）不回归；`check-patch-tree`（补丁数变化须如实）+ `check-lit`/`check-instrinfo` 不受影响。
5. **不可行时的出口**：若证实静态 PIE 无法在无 `AT_BASE` 下安全定位 `PT_DYNAMIC`，**停下报告**（给证据 + 两个候选边界：(a) 保持错误 → 不可接受；(b) 显式声明 `-static-pie` 不支持并给出**可判失败**（链接期或运行期显式报错），取 (b) 需用户语义裁定）。**不得**静默保留绝对地址。
6. **可达 FAIL ≥ 2**（真实输出 + 还原回绿；`cp`+md5）：
   - (a) **修前现场**：`llvm-readobj --relocations rcrt1.o` 3 条 `ABS48 _DYNAMIC`（改前复现、改后 0）；若 lld 直接拒绝 `-static-pie`，记录**真实**拒绝签名；
   - (b) **注入回退**：临时树把 `START` 分支改回绝对形态 ⇒ 对象级断言红 / 运行探针错值；
   - (c) **错误基址注入**：把运行期基址偏移改错（如漏减 `PT_PHDR.p_vaddr`）⇒ oracle 比较红。
7. **门控**：`make check`(L1) rc=0；`check-patch-tree` / `check-musl-freshness` / `check-builtins-freshness` 各留 rc；`make check-modules`（L2）rc=0 或逐项给真值 + 原因。
8. 完成区（≤30 行）与真实输出逐条对齐；`milestones.md` 一行；`issues.yaml` 的 `ISS-245` 按实况回填（`closed` + `resolved_by`，或「保留 open + 依据」）。
9. **不跑** `git commit`/`push`；`-static-pie` 是否纳入 P2/P3 口径**不改**（只修 `rcrt1.o` 的正确性，范围裁定仍归用户）。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-120t/`；命令一律在 workdir 内、**相对路径**；禁出界 `cd`。
2. 不提交 git；禁 `git checkout/restore/stash` 还原注入（`cp` + md5 对账）。
3. 完成区与真实输出逐条对齐；禁 `cmd | tee` 吞码（用 `; rc=$?`）。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定（接受不支持边界 / 改 `spec/` / 改契约）时留问。
6. 复杂命令输出留 `.work/log/`；重建按 `AGENTS.md` 申报耗时、`JOBS=8`。
7. **`install-host` 前置**：musl 构建消费安装根工具链；未装就验 = 假绿（`ISS-210`）。

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
