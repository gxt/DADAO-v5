# INFRA-067t: 提供 `__muldc3`/`__mulsc3`（复数乘编译器辅助）

**模块**：infra
**项目里程碑**：M7
**依赖**：`LLVM-088t` 等（**同改 `components/picolibc/patches` ⇒ 与 picolibc 侧任务串行**）
**状态**：待开始

> 立项来源：用户 2026-10-12 裁定「先在 M7 内做解锁件再归档」+ 本轮讨论（**从易到难第 4 项**）；依据 `ISS-196`（clang 对 `_Complex` 乘生成 `__muldc3`/`__mulsc3`；picolibc 不提供 ⇒ 链接 `undefined` ⇒ blocked **6**）。**模块归属**：产物在 `components/picolibc/**` ⇒ `infra`（同 `INFRA-057t`/`066t`）。

## 用户裁定（2026-10-12，**原话/选项标签**）

- 议题：`__muldc3`/`__mulsc3` 从哪来。
- 选项：(a)「**移植 compiler-rt 单文件（推荐）**」／(b) 自带简化实现（极端值语义不同）／(c) 改前端语义。
- **用户选择 = (a) 移植 compiler-rt 单文件**。
- 取得渠道：**经主会话问答**取得（2026-10-12）。

## 目的 / 根因（事实）

- clang 对 C `_Complex` 乘法生成 **`__muldc3`（double）/`__mulsc3`（float）** 调用（编译器辅助的**缩放复乘**，用于避免中间量溢出；**语义 ≠ 普通复乘**）。
- **picolibc 不提供**这两个符号 ⇒ 链接期 `undefined` ⇒ `ISS-196` 的 **6 条** test blocked。
- 注意：`LLVM-084t` 已解锁的复数函数（`ccos/csqrt/…`）**不依赖**它（picolibc 自带实现在 `libm/complex/**`）⇒ 本任务只补**编译器期望的辅助符号**。

## 接口规范

- **输出**：
  1. **移植 compiler-rt 的 `muldc3.c` / `mulsc3.c`** 入 `components/picolibc/patches/**`（**一文件一补丁**；`series` 追加）：
     - **必须标注出处与许可**：来源 = `compiler-rt/lib/builtins/{muldc3.c,mulsc3.c}`（LLVM 系，**Apache-2.0 WITH LLVM-exception**）；在补丁/文件头写明**文件路径 + 版本（commit 或 llvmorg tag）+ 许可**（`AGENTS.md`「参考来源」：第三方源码随产物入库须标出处，**不得**只写在 commit message）。
     - **不得修改其算法**（保持与 clang 期望的语义一致）；如与 picolibc 现有符号/头冲突（重名/宏）⇒ **停下报告**（不擅自改名/改语义）。
  2. **重建 picolibc**（`make build-picolibc`；~秒级）+ 链接验证（目标端 `ld.lld` 解析到符号）。
  3. **全量 test**：`make check-picolibc-tests-full` ⇒ **四分类 before/after**（before：`pass 152 / fail 0 / excluded 18 / blocked 65`）+ **解锁用例清单**（预期 6 条）。
  4. `.tao/knowledge/milestones.md` 流水更新 `INFRA-067t` 行（状态 `待验收`，`完成时间` `—`）。
- **约束**：**最小改动**（只加 2 个符号的实现）；**不改** `spec/`、`contracts/`、`tests/vectors/`；**不改** LLVM 侧；**计数不写死**。

## 验收标准

1. **符号存在**：`nm` 在 **picolibc sysroot** 中证明 `__muldc3`/`__mulsc3` **有定义**（真实输出；`T`）。
2. **可链接可跑**：原 blocked 用例（抽 ≥3，含复数乘路径）**链接 + QEMU 真跑 rc=0**（真实输出/退出码）；**`fail` 仍须 0**。
3. **全量 test**：`pass` **上升**、`blocked` **下降**（before/after 现场统计 + 解锁清单）。
4. **出处许可**：补丁/文件头含**来源路径 + 版本 + 许可**（`grep` 证据）；**算法未被修改**（相对上游 diff 仅移植适配，逐条说明）。
5. **门控**：`make check`、`check-patch-tree`、`check-no-residue`、`check-picolibc-tests`（快档）各 EXIT=0。
6. **反例可失败**：注入（移除该符号 / 改错期望）⇒ 断言/门控 **FAIL** ⇒ `cp`+md5 还原 ⇒ 回绿。
7. **完成区**（≤30 行）与真实输出逐条对齐。

## 硬约束（下发提示必带）

1. 临时目录 `/tmp/opencode/INFRA-067t/`；**命令一律在 workdir（= 仓库根）内、相对路径；禁 `cd` 出界**；禁仓库内临时文件。
2. **不提交 git**；补丁导出纪律（写 `/tmp`、行数下限、**非空 blob**、`check-patch-tree` 断言⑥、`.work/source/picolibc` = `base+N`、`series` 一致）。
3. 完成区与真实输出逐条对齐；**禁 `cmd | tee` 吞码**。
4. 只动任务范围（`components/picolibc/**`、任务书、`milestones.md` 行）；越界须披露。
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
