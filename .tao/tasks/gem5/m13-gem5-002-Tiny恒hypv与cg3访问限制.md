# m13-gem5-002: gem5 Tiny 恒 `hypv` 与 `cg3` 访问限制（ISS-363）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-gem5-001`（Tiny `cfx_power` + `cfx3 hmon` 已合入）
**可并行分片**：否（组件单写者）
**状态**：待开始

## 背景

`m13-gem5-001` 的 reviewer 在交叉比对 QEMU 实现时发现一处实现分歧（登记为 `ISS-363`）：

- gem5 的 `tinyEnter`（`.work/source/gem5/src/arch/dadao/fs_machine.cc`）在异常进入时**直接取** `cfx_⟨cfxname⟩_hypv_switch_run_mode` 的值作为新运行模式。
- QEMU 侧对**非 user profile** 强制 `inner_run_mode = HYPV`（引 `Machine-v5 §2`「`Machine-v5-Tiny` 运行模式恒 `hypv`，不能进入 `user`/`jail`/`supv`」）。
- 后果：guest 先把 `switch_run_mode` 写成 `≠3`，再触发任意同步异常，gem5 上就会**离开 `hypv`**；QEMU 不会 ⇒ 三平台差分时 Tiny 的越权路径分叉。
- 同时 gem5 未实现 `cg3` 的访问限制（`DADAO-13 §1`：`cg3` 为 `hypv` 模式寄存器，其它运行模式访问 ⇒ `CFXREG`）。

## 目标

1. **Tiny 恒 `hypv`**：非 user profile（Tiny）的异常进入一律 `inner_run_mode ← HYPV`，不再读 `switch_run_mode`；user profile（Vast）保持既有行为（按寄存器值切换）。
2. **`cg3` 访问限制**：非 `hypv` 模式下访问 `cg3` 寄存器（`cfx_⟨cfxname⟩_hypv_*`、`rc0`–`rc11`）⇒ 当前运行模式 monitor 的 `CFXREG`（`excp_cause_id` 位索引 2），不得静默成功。
3. **`excp_prev_run_mode` 正确**：异常进入时保存的是**进入前**的运行模式（Tiny 恒 3）。
4. 与 QEMU（`m13-qemu-001` 已合入）**逐条一致**：同一客程序在两边得到相同的 `excp_prev_run_mode`、`excp_cause_id`、`excp_cause_ip` 与 `inner_run_mode`。

## 非范围

- 不改 `Machine-v5`/`DADAO-13`（本任务按现行 spec 实现，spec 无缺口）
- 不改 QEMU / chipyard
- 不实现 `smon`、不改 Vast 的多模式语义（只保证不回归）
- 不处理 `ISS-357`/`ISS-358`/`ISS-359`（`m13-gem5-003` 与 testcases 侧）

## 验收标准

1. 新用例（`tests/arch/hmon/` 内扩展或新增）：guest 写 `switch_run_mode = 0`（user）后触发 `CFXMEM` ⇒ 断言 `excp_prev_run_mode == 3` 且异常处理期间运行模式仍为 `hypv`（handler 内再读 `cg3` 成功）
2. 非 `hypv` 模式下访问 `cg3` ⇒ `CFXREG`（位索引 2）；正常 `hypv` 下访问 `cg3` 成功
3. 与 QEMU 同程序逐条一致（`excp_prev_run_mode`/`cause_id`/`cause_ip`/模式）；chipyard 侧留给 `m12-chipyard-007` 之后补
4. 现有 `check_tiny_hmon` **148 条**零回归；`check-inst`（Vast 980/985 + 5 deferred、Tiny 44/44）、`check-arch`、`check-inst-smoke`、`check-unit` 零回归
5. `build-gem5` / `install-host` / `check-patch-tree` / `check-source-state` / L1 / L2 rc=0（外部红须逐条核实归属）
6. 补丁由 `make_patch.py gem5` 导出（非手改），`components/gem5/patches/` + `series` + `changelog.md` 同笔
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 说明

- `m13-gem5-001` reviewer 第 1 轮 finding 3 的原始描述见该任务书；`ISS-363` 为正式登记。
- 组件单写者：本任务期间不得有其它任务改 `.work/source/gem5`。
- 构建在主控机（`JOBS=8`），不占用 207/208。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进（自行处置：派修/绕行/有据重试并记录次数/登记后跳过）；只在需用户语义裁定时留问。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 用户裁定须原样写入任务书。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

（待填）
