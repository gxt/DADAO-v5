# LLVM-086t: 内联汇编 `"r"` 约束解锁（`ISS-193`(e)）

**模块**：llvm
**项目里程碑**：M7
**依赖**：`LLVM-085t`（同改 `components/llvm-project/patches` ⇒ **串行**）
**状态**：待开始

> 立项来源：用户 2026-10-12 裁定「**先在 M7 内做解锁件再归档**」+ 本轮讨论（**从易到难第 1 项**）；依据 `ISS-193`(e)（blocked 2）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：`"r"` 语义（GPRD vs GPRB）与是否**立"内联汇编约束约定"**。
- 选项：A「`"r"`→GPRD + 新增 `"b"`→GPRB + `"f"`→GPRF + 立最小约定（于 `spec/Toolchain-01` + lit 钉住）」／B「`"r"`→GPRB 优先」／C「**只解锁，不立约定**」。
- **用户选择 = C「只解锁，不立约定」** ⇒ **只把 `"r"` 映射到通用数据寄存器类（GPRD）**；**不新增 `"b"`/`"f"`**、**不立约束约定**（后置）。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（实测）

- 根因：DADAO target **未实现** `getRegForInlineAsmConstraint` ⇒ 任何 `"r"` 约束报 **`could not allocate output register for constraint 'r'`**。
- 最小复现（实测 rc=141）：`long c(long*p){long v;__asm__ volatile("" : "=r"(v) : "r"(p)); return v;}`。
- 现场用例（`picolibc`）**均为空 asm 编译器屏障**：`__asm__ __volatile__("" ::"r"(dest) : "memory");`（`libc/string/memset_explicit.c:44`、`memset_s.c:68,75`）⇒ **asm 体内无指令**，寄存器类别不影响语义 ⇒ 映射到数据类即可解锁。
- 事实（`contract-abi`）：**指针类参数使用基址寄存器 `rb16–rb31`**；ISA 有 `rd2rb`/`rb2rd` ⇒ **GPRD 与 GPRB 不通用**（本任务**只解锁**，不做类型分派——分派在 LLVM 后端**不可行**：VT 只有 `i64`）。

## 接口规范

- **输出**：
  1. **实现 `DADAOTargetLowering::getRegForInlineAsmConstraint`**（范围 `components/llvm-project/patches/llvm/lib/Target/DADAO/**`）：`"r"` → **GPRD 类**（`GPRD` vs `GPRD_Allocatable` 由 engineer 按**寄存器分配器口径**选定并**给依据**）；**其余约束回落** `TargetLowering::getRegForInlineAsmConstraint`；**不得**顺手新增 `"b"`/`"f"`（用户裁定：**不立约定**）。
  2. **重建**（`build-mc`+`install-host`；申报耗时；>10 min ⇒ `setsid nohup` + `XXX_EXIT`；`JOBS=8`、禁全核、一次一个；`124` 判 FAIL）。
  3. **picolibc 全量 test 重跑**（`make check-picolibc-tests-full`）⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ **解锁用例清单**。
  4. `.tao/knowledge/milestones.md` 流水更新 `LLVM-086t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**最小改动**（只 `"r"`）；**不改** `spec/`、`contracts/`、`tests/vectors/`；计数不写死。
  - ⚠️ **若你发现"只映射 `"r"` 不够"**（如某源还需 `"f"`/`"b"`/其它）⇒ **停下报告**（`lessons §3.17`：禁自拟选项自答；**不擅自扩范围**）。

## 验收标准

1. **`"r"` 可用**：最小用例（整数 input/output、**指针 input**、`+ "memory"` clobber）**rc=0**；汇编产物真出现该寄存器（可给 `-S` 片段）。
2. **解锁**：`memset_s`/`memset_explicit` 两源 **`clang -c` rc=0**；对应 picolibc test **真跑 rc=0**（≥2 条）。
3. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单；**`fail` 仍须 0**）。
4. **门控**：`make check`、`check-lit`、`check-patch-tree`、`check-index-blobs`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
5. **反例可失败**：注入（回退该 hook / 改错期望）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
6. **未扩范围**：**未**新增 `"b"`/`"f"`、**未**改 `spec/`（`git diff` 证据）。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-086t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
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
