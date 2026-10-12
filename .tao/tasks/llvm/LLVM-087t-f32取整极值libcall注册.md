# LLVM-087t: f32 取整/极值 libcall 注册（`ISS-193`(b)）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-086t`（同改 `components/llvm-project/patches` ⇒ **串行**）
**状态**：待开始

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 2 项**）；依据 `ISS-193`(b)（blocked **10**）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：f32 libcall 注册范围（全族 vs 只取整六项）。
- 选项：A「**f32 全族（含 `fminf`/`fmaxf`）（推荐）**」／B「只做取整六项」／C「先补充」。
- **用户选择 = A「f32 全族（含 `fminf`/`fmaxf`）（推荐）」**。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（事实）

- `LLVM-080t`（P1）**只给 f64** 注册了 libcall（`RTLIB::{FLOOR,CEIL,TRUNC,ROUND,RINT,NEARBYINT,FMIN,FMAX}_F64`）；**f32 变体未注册** ⇒ 报 **`NOLIBCALL`** ⇒ `ISS-193`(b) 共 **10 条**源不可编（`frintf`/`flogf`/`ftruncf` 等）；`fmin_f` 现状亦为 `NOLIBCALL`（`LLVM-084t` 报告）。
- ISA **无**取整方向族与 `fmin`/`fmax` 指令（`contracts/opcodes.yaml` 现场为准）⇒ 走 **libcall** 是既定路径（与 f64 一致）。

## 接口规范

- **输出**：
  1. **注册 f32 全族 libcall**（范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`）：
     `RTLIB::{FLOOR,CEIL,TRUNC,ROUND,RINT,NEARBYINT,FMIN,FMAX}_F32` → 符号 `floorf`/`ceilf`/`truncf`/`roundf`/`rintf`/`nearbyintf`/`fminf`/`fmaxf`。
     - **前置校验（必做）**：**先**用 `nm`（目标端对象/静态库）证明这些符号在 **picolibc sysroot** 中存在；**缺任一 ⇒ 停下报告**（不擅自改 picolibc，`lessons §3.17`）。
  2. **重建**（`build-mc`+`install-host`；申报耗时；>10 min ⇒ `setsid nohup` + `XXX_EXIT`；`JOBS=8`、禁全核、一次一个；`124` 判 FAIL）。
  3. **探针 + 全量 test**：`tools/testcases/picolibc-probe-fp.sh` 复跑（f32 类 `NOLIBCALL` 应清零）+ `make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ **解锁用例清单**。
  4. `.tao/knowledge/milestones.md` 流水更新 `LLVM-087t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**最小改动**（只注册 f32 族，与 f64 对称）；**不改** `spec/`、`contracts/`、`tests/vectors/`、picolibc 源；**计数不写死**。

## 验收标准

1. **f32 族可用**：探针中 f32 取整/极值类 **`NOLIBCALL` 清零**（现场统计，非抽样）；抽样 ≥3 源 **`clang -c` rc=0**。
2. **真跑**：≥3 条相关 picolibc test **真跑 rc=0**（真实输出/退出码）；**`fail` 仍须 0**。
3. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
4. **门控**：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
5. **反例可失败**：注入（回退某条注册 / 改错期望）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
6. **未扩范围**：未改 picolibc 源、未动 `spec/`（`git diff` 证据）。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-087t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/llvm-project` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/llvm-project/patches/**`、`tests/llvm/**`、任务书、`milestones.md` 行）；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、**计数不写死**、捕获退出码）。
8. 反例注入还原**禁** `git checkout`/`restore`/`stash`；一律 `cp` + md5 对账。
9. **计数不写死**。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
