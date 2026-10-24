# QEMU-073t: `cpu_loop_exit` 的 longjmp 泄漏 MMIO 重入守卫（`ISS-064`）

**模块**：qemu
**项目里程碑**：M9（收尾前）
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 立项来源 / 现象（`ISS-064` 原文，执行前现场复核）

`cpu_loop_exit` 走 `longjmp` 跳出时，**MMIO 重入守卫 `engaged_in_io` 未复位**；
下一次进入 MMIO 路径时守卫仍为"忙" ⇒ 后续访问被误判为重入（可能直接 abort / 返回错误）。

## 目标

1. 找到 `engaged_in_io` 的置位/复位路径与 `cpu_loop_exit` 的 `longjmp` 落点（`accel/tcg` / `softmmu` / `exec`）。
2. 在**所有** `longjmp` 出口（不止一处）保证守卫被复位；优先用"`sigsetjmp` 返回后统一复位"这类**结构化**修法，而非逐点打补丁。
3. 给出触发路径：能构造一个"MMIO 访问 → 异常/退出 → 再次 MMIO"的用例，证明修复前会误判、修复后正常。

## 验收

1. **复现用例**：构造 1 个最小 guest 程序（或 qemu 内部测试）走"MMIO → `cpu_loop_exit` → 再 MMIO"，贴**修复前失败、修复后通过**的真实输出。
2. `make check`(L1) rc=0；`make check-modules`(L2) rc=0；`check_qemu_trans --strict` 266/266；`check_patch_tree` 绿。
3. **可达 FAIL**：注入"去掉复位" ⇒ 复现用例再次失败。
4. 证据 `.work/evidence/<任务ID>/run.sh`（rc 落盘、禁 `| tee`）。

## 接口规范

- **输入**：`components/qemu/patches/**`（`accel/tcg` / `softmmu` / `include/exec`）。
- **输出**：守卫复位修复 + 复现用例 + 证据。
- **约束**：不改 ISA/spec/contracts；不 commit/push；临时目录 `/tmp/opencode/QEMU-073t/`。

## 完成区
（执行后填写，≤30 行）

## 审阅记录
