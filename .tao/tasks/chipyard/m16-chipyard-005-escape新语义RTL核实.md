# m16-chipyard-005: chipyard RTL 的 `escape` 新语义核实/补（`prev_cfx_code`）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m14-spec-009`（spec + QEMU 已实现）、`spec/Kaiwu` 已对齐（`ede7f6b3`）、`m15-testcases-017`（11-cfx 载体已按新语义重写）
**可并行分片**：可与 `m16-gem5-013` 并行（不同组件）
**预估**：3–4 h（若需补 RTL 则含 `make verilog` 与 sim md5 登记）
**档位**：中改（跨 RTL + 补丁集）
**状态**：待开始

## 背景（用户 2026-11-18 裁定）

`m14-spec-009` 把 `escape` 改为**恢复 `inner_cfx_code ← excp_prev_cfx_code`**（`cg5 rc1`，异常进入时保存），spec + QEMU 已落地，`spec/Kaiwu` 已同笔对齐。

三方里 **chipyard RTL 是否实现该语义尚未核实**——RTL 若按旧语义（escape 不改 `inner_cfx_code`），则与 spec 冲突，且会影响任何依赖 cfx 切换的探针/仿真结论。

**本任务必须先核、后决定补不补**，不允许「假定 RTL 没问题」。

## 目标

### 1. 核实（先做，产出结论）

在 `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/**`（`WumingCore.scala`、cfx 相关文件）与 `dadao-gewu/**` 中确认：

- 是否存在「异常进入时保存当前 cfx」的寄存器（对应 `cg5 rc1`）；
- `escape` 路径是否恢复该寄存器；
- `cg5 rc1` 的读写在 RTL 里如何实现（reserved？可读写？）。

**产出**：代码位置（文件 + 行/信号名）+ 结论（已实现 / 未实现 / 部分实现）。

### 2. 若未实现（或部分实现）⇒ 补

- 补 `prevCfxCode` 寄存器：异常进入时在改写 `cfxCode` **之前**保存；`escape` 通过步骤 0 检查后恢复；`cg5 rc1` 可读写。
- 按 `AGENTS.md` 单二进制纪律：`make verilog` rc=0、**sim md5 登记**（与既有冻结基线对比要说明）。
- 补丁经 `make_patch chipyard` 重导出（禁手改 index）。

### 3. 行为验证（无论补不补，都要有可失败证据）

- 用现有 cfx 探针（`tools/chipyard/excp/`）构造「supv 帧内投递异步事件 ⇒ 该帧 escape 成功、cfx 回到进入前值」；
- 若补了 RTL：**删掉恢复那行 ⇒ 必须复现 `CFXESC`** ⇒ 还原 ⇒ 恢复；
- 若确认 RTL 已是新语义：给出**代码位置 + 一条断言**（探针里断言 `cfx` 回退值），不能只靠读代码。

## 验收（逐条贴真实 rc）

1. 核实结论：代码位置 + 判定（已实现/未实现/部分）；若「已实现」必须附探针断言。
2. 若补：`make verilog` rc=0、sim md5 记录、`make_patch chipyard` 幂等、`--source-state chipyard` = `base+1 clean`。
3. 行为验证：删恢复 ⇒ `CFXESC`（或对应断言红）⇒ 还原 ⇒ 绿。
4. `make check-patch-tree` 的 chipyard 段 0 problem。
5. `check-component-changelog` rc=0（若改组件需追加 changelog）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. **不碰 `components/gem5`、`components/qemu`**（分别由 `m16-gem5-013` 与已完成的 spec-009 负责）。
3. **不改 spec**；不改 `tests/inst`。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。
5. 严格串行：先 `make verilog`、再跑探针，不并发。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
