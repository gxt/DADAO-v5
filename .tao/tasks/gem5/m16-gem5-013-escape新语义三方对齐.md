# m16-gem5-013: `escape` 新语义三方对齐（gem5 + chipyard）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m14-spec-009`（spec + QEMU 已实现）；`spec/Kaiwu` 已同笔对齐（`ede7f6b3`）
**可并行分片**：否（两个组件，同一语义）
**预估**：3–4 h
**档位**：中改（跨两个组件）
**状态**：待开始

## 背景（用户 2026-11-18 裁定）

`m14-spec-009` 按用户裁定 B 把 `escape` 改成**恢复 `inner_cfx_code ← excp_prev_cfx_code`**（`cg5 rc1`，异常进入时保存），spec 与 QEMU 已落地，`m15-testcases-017` 的 11-cfx 载体也已按新语义重写（272/272）。

但三方里还有两边没跟上：

- **gem5**：`components/gem5/patches/src/arch/dadao/node_cfx.hh` 只有 `prevRunMode`，**没有 `prevCfxCode`**；`node_cfx.cc` 的 trap/escape 路径也只保存/恢复运行模式。
- **chipyard**：RTL 是否实现待核；若未实现，需补并存进补丁集。

## 目标

### 1. gem5（`components/gem5/patches/src/arch/dadao/**`）

- `node_cfx.hh`：加 `uint64_t prevCfxCode = 0;`（注释 `cg5 rc1`）。
- `node_cfx.cc`：trap 进入时**在改写 `cfxCode` 之前**保存 `prevCfxCode = cfxCode`；`escape` 通过步骤 0 检查后恢复 `cfxCode = prevCfxCode`。
- cg5 rc1 的读写分发：从 reserved 改为可读写 `prevCfxCode`（与 QEMU `helper.c` 的 `case 1` 对齐）。
- 若 `tiny_cfx` 也有同类路径，一并核。

### 2. chipyard（`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/**`）

- 先**核实** RTL 的 cfx 状态机（`WumingCore.scala` 等）是否有 `prev_cfx_code` 寄存器与 escape 恢复路径；有则确认语义与 spec 一致，无则补。
- 补的话要过 `make verilog` + sim md5 登记（按 `AGENTS.md` 单二进制纪律）。

### 3. 一致性验证（两边都要能失败）

- **gem5**：构造「supv 帧内投递异步事件 ⇒ 该帧 escape 成功、`cfxCode` 回到进入前值」；**删掉恢复那行 ⇒ 必须复现 `CFXESC`** ⇒ 还原 ⇒ 恢复。
- **chipyard**：若补了 RTL，用现有 cfx 探针（`tools/chipyard/excp/`）做同一件事；若确认 RTL 已是新语义，给出**代码位置 + 断言**证明。
- 与 QEMU 的 cg5 rc1 值（复位 `cfx_power`=63、boot trap 后 0x3F）逐项对齐。

## 验收（逐条贴真实 rc）

1. gem5 补丁经 `make_patch gem5` 重导出；`--source-state gem5` = `base+1 clean`；`make check-patch-tree` 的 gem5 段 0 problem。
2. gem5 行为注入：删恢复行 ⇒ `CFXESC`；还原 ⇒ 绿（贴两侧 rc）。
3. `make check-wuming-cycles`、gem5 段 `check_component` rc=0。
4. chipyard：核实结论 + （若补）`make verilog` rc=0、sim md5 登记、cfx 探针绿；补丁经 `make_patch chipyard` 重导出。
5. 三方对照：QEMU / gem5 / chipyard 对同一场景的 `inner_cfx_code` 与 `cg5 rc1` 值一致。
6. `make check-inst-asm` 272/272（确认测试载体与新语义一致）。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. **不改 spec**（已由 `ede7f6b3` 对齐）；不改 `tests/inst`（`m15-testcases-017` 已改）。
3. 两个组件**串行**修改（先 gem5、后 chipyard），避免同时持两个组件写权。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 严格串行：先构建、再跑门控。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
