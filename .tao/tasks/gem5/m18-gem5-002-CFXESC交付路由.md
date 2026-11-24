# m18-gem5-002: gem5 `CFXESC` 交付路由（fallback 进当前 cfx，而非当前模式 monitor）

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-gem5-001`（`escape` frame selector 语义/断言）合入；`m18-spec-005`（R2 规格）已验证
**可并行分片**：否（同改 `components/gem5`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（`m18-gem5-001` 现场发现，2026-11-24）

`m18-gem5-001` 已按 R2 让 `imms18=2`（`imms18[1]=1` 走 `cg9`）在 `exec/b6.cc::executeEscape()` 里恒投 `Fault::CfxEsc`。但该故障在 `exec/inst.cc` 的既有 fallback 分支里走：

```cpp
case exec::Fault::CfxEsc:
    // Tiny's escape hook raises CFXESC into the current cfx itself; this
    // branch is only a fallback and still enters the current monitor.
    if (fs) return DadaoISA::machineFaultAt(DadaoISA::FaultCfxEsc, ip, word);
```

`machineFaultAt(...)` 进的是**当前运行模式的 monitor**：`m18-gem5-001` 的 reviewer 已实测确认——Tiny 上 `Fault::CfxEsc` 走 `machineFaultAt(target=-1)` ⇒ `target<0` 时 `TinyCfxhaHmon`；Node 上 `target = runMode` ⇒ 当前运行模式 monitor。而 `spec/DADAO-12 §5.1/§5.3` 要求 `CFXESC`（escape 帧/目标错误）交付给**当前核芯功能扩展**、不属于 monitor 路由。对照：`cg5` 帧走 hook（`target = cfxCode`）是**正确**的，**只有 cg9/无帧路径错**。
  ⇒ 修点明确：`inst.cc.patch` 里 `Fault::CfxEsc` 的 fallback 需把目标从 `-1`/`runMode` 改成**当前 cfx 编号**（若该处拿不到，就从 decoder/helper 带下来）。

## 目标

1. **坐实差异**（先做）：构造最小例（`escape` 合法帧但目标 cfx 走 fallback 路径），在 gem5 上观测到「进当前模式 monitor」；与同 ELF 的 QEMU 行为对比（QEMU 应进当前 cfx），给出两侧 trace/日志。
2. **修路由**：fallback 改为投递给**当前 cfx**（与 `cfx` 的处理入口一致，权重/优先级按 `DADAO-12 §5.1`），删除 `inst.cc` 里「only a fallback and still enters the current monitor」的自述注释；若 gem5 侧确实无法在 fallback 里定位当前 cfx，应在 decoder/exec helper 层把 cfx 编号带下来，**不得**降级为「进当前 monitor」。
3. **三方一致**：同一 ELF 的 QEMU / gem5（/ chipyard 若可跑）签名流逐字节一致；不一致项逐条归因。

## 验收（逐条贴真实 rc）

1. 最小例在修前红（进错 monitor）、修后绿（进当前 cfx），两侧证据齐全。
2. `escape` 合法帧 + `CFXESC` 可达路径至少 2 例覆盖（cg5 帧、cg9 捕获缓冲各一），且**不影响** `imms18=3`/`[17:2]` 非零/reserved cfx 的 ILLI 判定顺序。
3. 可达 FAIL ≥2 路（把路由改回 monitor ⇒ 红；把 `imms18` 判定顺序改坏 ⇒ `check-gem5-decode` 红），`cp`+md5 还原。
4. 补丁由 `make_patch.py gem5` 重导出，`check-patch-tree` gem5 段 0 problem；`check-gem5-decode`（positive/negative 全量）rc=0。
5. `build-gem5` rc=0；长命令 `setsid nohup` + 日志 + `*_EXIT`。
6. 若 QEMU/RTL 侧同样存在「fallback 进 monitor」⇒ 在完成区列出并建议后续任务，**不在本任务扩范围**。

## 约束

独立 `git worktree`（分支 = `m18-gem5-002`）；不提交 git；只改 `components/gem5/**`（含重导补丁）与必要探针/任务书；不改 `spec/`/契约；术语「寄存器组」；完成区不写具体 `.work/**` 路径。
