# m13-gem5-003: gem5 SE 缺陷修复（`SYS_WRITE` 句柄越界、非对齐 `.bss` 装载）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-002`（同一组件单写者，须串行）
**可并行分片**：否（组件单写者）
**状态**：待开始

## 背景

M13 差分要覆盖 dynamic 链接的 `llvm-ts`/`libc-test`，但 gem5 SE 有两个已登记的缺陷（`issues.yaml`）：

- **`ISS-358`（P2）**：`BaseSemihosting::callWrite` 用 `handle > files.size()` 判越界（应为 `>=`）。未 `SYS_OPEN` 时 `handle=1` 会读 `files[1]` 越界，`m12-chipyard-004` 探针实测 **segfault**。
- **`ISS-359`（P2）**：`src/sim/process.cc:196` 的 `fatal_if((seg.base & 3) != 0, ...)` 在 `p_vaddr + p_filesz` 非 4 字节对齐时直接 fatal，`dynamic llvm-ts` **7 例**因此 blocked（QEMU 可正常装载），名单见 `refs/INTEG-059t-se-parity-summary.json` 的 `new_findings`。

两者都直接压缩 M13 的可比样本（7 例 blocked + `SYS_WRITE` 崩溃风险），且都是 gem5 实现缺口，不是 spec 语义问题。

## 目标

1. **`ISS-358`**：边界判断改 `handle >= files.size()`；未打开句柄的 `SYS_WRITE` 返回错误码（按 Arm Semihosting 约定）而不是越界读。**不得**改变已打开句柄的正常路径。
2. **`ISS-359`**：删 `fatal_if`，改为「按段对齐要求零填到下一个对齐边界」（先按 `p_align` 向下对齐映射起点，再零填到下一 4 字节/页边界，具体以 gem5 loader 现有语义为准）；保持已对齐段行为不变。
3. **7 例 dynamic 复测**：`ISS-359` 名单中的 7 例在 gem5 SE 上从 `blocked` 转为可装载并可跑（pass 或按 oracle 判 fail，但**不得**死于 loader）。
4. **回归**：既有 SE 用例（static/dynamic）零回归；`check-inst`/`check-inst-smoke`/`check-arch`/L2 全绿。
5. `SYS_WRITE` 句柄用例：未 `SYS_OPEN` 直接 `SYS_WRITE` ⇒ 无崩溃、返回错误；`SYS_OPEN` 后正常写。

## 非范围

- 不改 `ISS-357`（stdout/stderr 写序，属 SE 驱动层口径，另立 testcases 任务）
- 不改 Tiny `hypv`/`cg3`（`m13-gem5-002`）
- 不改 QEMU / chipyard / spec
- 不重跑 3600s 长尾（`m13-testcases-003`）

## 验收标准

1. `ISS-358`：新增/复用探针证明「未 `SYS_OPEN` 的 `SYS_WRITE` 不再 segfault」，且打开句柄的正常写不变
2. `ISS-359`：7 例名单逐例从 blocked 转可跑（给出每例前后状态），并说明零填语义
3. 现有 SE 用例零回归（static/dynamic 抽样 + `check-inst` 全量）
4. `build-gem5` / `install-host` / `check-patch-tree` / `check-source-state` / L1 / L2 rc=0（外部红逐条核实归属）
5. 补丁由 `make_patch.py gem5` 导出（非手改），`patches/` + `series` + `changelog.md` 同笔
6. 一键证据脚本（含可达 FAIL 注入：改回 `>` 与改回 `fatal_if` 应各 FAIL）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 两处改动分别属 `src/base/semihosting.cc`（或等价实现文件）与 `src/sim/process.cc`；以实际源码路径为准，任务书不写死行号。
- 组件单写者：与 `m13-gem5-002` 串行。
- 构建在主控机（`JOBS=8`），不占用 207/208。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 用户裁定须原样写入任务书。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
