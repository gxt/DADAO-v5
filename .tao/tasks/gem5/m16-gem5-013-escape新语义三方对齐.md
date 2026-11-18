# m16-gem5-013: gem5 侧 `escape` 新语义对齐（`prev_cfx_code`）

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m14-spec-009`（spec + QEMU 已实现）；`spec/Kaiwu` 已同笔对齐（`ede7f6b3`）
**可并行分片**：可与 `m16-chipyard-005` 并行（不同组件）
**预估**：3–4 h
**档位**：中改（单组件）
**状态**：待开始

## 背景（用户 2026-11-18 裁定）

`m14-spec-009` 按用户裁定 B 把 `escape` 改成**恢复 `inner_cfx_code ← excp_prev_cfx_code`**（`cg5 rc1`，异常进入时保存），spec 与 QEMU 已落地，`m15-testcases-017` 的 11-cfx 载体也已按新语义重写（272/272）。

但三方里还有两边没跟上：

- **gem5**：`components/gem5/patches/src/arch/dadao/node_cfx.hh` 只有 `prevRunMode`，**没有 `prevCfxCode`**；`node_cfx.cc` 的 trap/escape 路径也只保存/恢复运行模式。
- **chipyard**：见独立任务 `m16-chipyard-005`（RTL 核实/补），本任务**不碰** `components/chipyard`。

## 目标

### 1. gem5（`components/gem5/patches/src/arch/dadao/**`）

- `node_cfx.hh`：加 `uint64_t prevCfxCode = 0;`（注释 `cg5 rc1`）。
- `node_cfx.cc`：trap 进入时**在改写 `cfxCode` 之前**保存 `prevCfxCode = cfxCode`；`escape` 通过步骤 0 检查后恢复 `cfxCode = prevCfxCode`。
- cg5 rc1 的读写分发：从 reserved 改为可读写 `prevCfxCode`（与 QEMU `helper.c` 的 `case 1` 对齐）。
- 若 `tiny_cfx` 也有同类路径，一并核。

### 2. 一致性验证（gem5 侧，必须能失败）

- 构造「supv 帧内投递异步事件 ⇒ 该帧 escape 成功、`cfxCode` 回到进入前值」；
- **删掉恢复那行 ⇒ 必须复现 `CFXESC`** ⇒ 还原 ⇒ 恢复；
- 与 QEMU 的 cg5 rc1 值（复位 `cfx_power`=63、boot trap 后 0x3F）逐项对齐。

## 验收（逐条贴真实 rc）

1. gem5 补丁经 `make_patch gem5` 重导出；`--source-state gem5` = `base+1 clean`；`make check-patch-tree` 的 gem5 段 0 problem。
2. gem5 行为注入：删恢复行 ⇒ `CFXESC`；还原 ⇒ 绿（贴两侧 rc）。
3. `make check-wuming-cycles`、gem5 段 `check_component` rc=0。
4. **两方对照**：QEMU / gem5 对同一场景的 `inner_cfx_code` 与 `cg5 rc1` 值一致（chipyard 由 `m16-chipyard-005` 单独验收，其结论出来后由主会话补三方对照）。
6. `make check-inst-asm` 272/272（确认测试载体与新语义一致）。
7. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. **不改 spec**（已由 `ede7f6b3` 对齐）；不改 `tests/inst`（`m15-testcases-017` 已改）。
3. **不碰 `components/chipyard`**（由 `m16-chipyard-005` 负责）。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 严格串行：先构建、再跑门控。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
