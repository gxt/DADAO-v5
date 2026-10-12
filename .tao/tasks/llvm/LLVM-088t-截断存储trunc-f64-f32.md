# LLVM-088t: 截断存储 `trunc f64→f32` 收口（`ISS-193`(d)）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-087t`（同改 `components/llvm-project/patches` ⇒ **串行**）
**状态**：待开始

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 3 项**）；依据 `ISS-193`(d)（**2 源 ⇒ blocked 14**）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：`ISS-193`(d) 截断存储的落法。
- 选项：A「**按此落任务书（推荐）**」／B「先补充」。
- **用户选择 = A「按此落任务书（推荐）」**（= 照 P0 `EXTLOAD` 的**镜像手法**加 `TruncStoreAction`，**不动** (c) `bswap`）。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（事实）

- `vfscanf.c`/`vfwscanf.c` 族（**2 源**）需把 **f64 截断后存为 f32** ⇒ 后端**缺 `TruncStore` pattern** ⇒ `Cannot select` ⇒ 依赖它们的 **14 条** test blocked。
- 与 `LLVM-079t` 修过的「f32→f64 `anyext` **载入**」（`setLoadExtAction(EXTLOAD,f64,f32,Expand)`）**互为镜像**。
- ISA 有现成 FP 转换指令 **`ft2fo`**（f64→f32）✓。

## 接口规范

- **输出**：
  1. **`setTruncStoreAction(MVT::f32, MVT::f64, …)`**（`Expand`/`Custom` 由 engineer 按现场选定并**给依据**）+ 必要时补 **ISel pattern**（**优先复用 ISA `ft2fo`**）；范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`。
  2. **重建**（`build-mc`+`install-host`；申报耗时；>10 min ⇒ `setsid nohup` + `XXX_EXIT`；`JOBS=8`、禁全核、一次一个；`124` 判 FAIL）。
  3. **探针 + 全量 test**：`tools/testcases/picolibc-probe-compile.sh` + `make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ **解锁用例清单**。
  4. `.tao/knowledge/milestones.md` 流水更新 `LLVM-088t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**最小改动**（只 TruncStore f32←f64）；**不动 `ISS-193`(c) `bswap`**（现 0 条 test 依赖，无收益）；**不改** `spec/`、`contracts/`、`tests/vectors/`、picolibc 源；**计数不写死**。

## 验收标准

1. **可编**：`vfscanf.c`/`vfwscanf.c` 两源 `clang -c` **rc=0**（真实输出）。
2. **真跑**：≥3 条 `vfscanf`/`vfprintf` 族相关 picolibc test **真跑 rc=0**（真实输出/退出码）；**`fail` 仍须 0**。
3. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
4. **门控**：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
5. **反例可失败**：注入（回退该 action / 改错期望）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
6. **未扩范围**：未动 `bswap`、未改 picolibc 源、未动 `spec/`（`git diff` 证据）。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-088t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/llvm-project` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围；越界须披露。
5. 失败保留现场并继续推进；**只在需用户语义裁定**时**停止并报告**（禁自拟自答）。
6. 任务书/记录中**不得写字面 `.work/<具体路径>`**（用 `<>` 占位）。
7. 一键证据脚本落 `.work/evidence/<任务ID>/`（能失败、可达 FAIL、结构断言、计数不写死、捕获退出码）。
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
