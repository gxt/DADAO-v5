# m17-gem5-001: gem5 Vast 的 TLB 改造（与 RTL 统一）

**模块**：gem5
**项目里程碑**：M17
**依赖**：无（gem5 侧独立）
**可并行分片**：否（改 `node_cfx.hh`/`node_tlb.cc`/`node_cfx.cc`）
**预估**：1–2 天
**档位**：大改
**状态**：待开始

## 背景

gem5 `DadaoNodeTlb`（Vast profile）当前实现是**单数组 16 条全相联 + 轮转替换**（`NodeState::tlb[16]`、`tlbNext`），超页与普通页混在同一数组靠 `sizeLog2` 区分；`DadaoNodeMMU` 有 `itb`/`dtb` 两个 port 但**指向同一套 `NodeState::tlb`**（统一表）。失效由 `tlbControlExec()` 遍历该数组。

**用户 2026-11-19 裁定**：gem5 要与 chipyard RTL **保持统一**——只设一级 TLB、**分 I/D**（I/D 分离是设计）、普通页 **16 条 = 2 组 × 8 路**、**超页 4 条全相联 + LRU**、**无特殊条目**、**I-TLB 无 dirty 位**。

## 目标

1. **拆成 I/D 两套表**：`NodeState` 里 `itlb[2][8]` / `dtlb[2][8]` + 各自超页 `itlb_sp[4]` / `dtlb_sp[4]`（或等价结构）；I 侧条目**无 D 位**；
2. **2 组 × 8 路的 set index**：**`VA[16]`**（64 KiB 页 ⇒ VPN 最低位）；超页走独立数组，**不进 set 索引**；
3. **替换策略改 LRU**（现为轮转）：实现一个 8 路 LRU 计数（每 set 一列），超页 4 条同样 LRU；
4. **`cfx_ptw_tlb_control` 双表失效**：`tlbControlExec` 遍历 **I、D 两表（含各自超页数组）**；`asidAny=0` 时跳过 `G=1` 条目；`clean`/`invalid` 保持**条目级 + 遇错即停**（现实现已如此，双表化时不能退化成"两侧都处理完才报错"）；
5. **A/D OR 合并**：同一 PTE 可能在 I、D 两表各有本地脏位 ⇒ 回写用 `writePteOr` 语义；**失败条目保留**，且「一条指令最多报一处失败」；
6. **`demapPage`/`flushAll` 保持空实现**（atomic 单核，缓存一致性不靠 gem5 的 demap）。

## 验收（逐条贴真实 rc，每条须能 FAIL）

1. **不回归**：既有 Vast 探针全绿（`k4_*` 不涉及；Vast 侧用既有 `tests/inst` 的 `ee-vast` 向量与 `tools/testcases/parity/run_parity.py --profiles vast`）；
2. **结构断言**：`--dump-*` 或在启动日志里现场打印「I/D 各 2×8 + 4 超页、替换=LRU」，并能被探针读回（不写死数量，从参数派生）；
3. **同 set 冲突**：两个 `VA[16]` 相同的页交替访问 ⇒ 触发互相淘汰并各自重走步查（用 PTW 计数现场统计）；
4. **超页 4 条**：5 个超页交替 ⇒ 必有淘汰；
5. **双表失效**：`scope=全表` 后 I、D 皆空；`scope=单 VA` 只清该 VA 的两表对应项；`asidAny=0` 不碰 `G=1`；
6. **A/D OR 合并**：I 置 A、D 置 A+D ⇒ `clean` 后 PTE 同时含 A、D；构造 D 侧回写失败 ⇒ 报 `CFXMEM+ADWBFAIL`（`cause_info` = PTE PA）、该条目保留；
7. ≥3 路注入（① set index 改 `VA[17]` ⇒ 冲突用例红；② 失效只清 I 表 ⇒ 双表用例红；③ A/D 回写改成覆盖 ⇒ 合并用例红），`cp`+md5 还原 + 重建回绿；
8. **合并态**（`Process-07 §5a`）：收尾前 `git merge master`，在合并态跑 `make check-arch`（或等价的 Vast 门控）与 `check-manifests-guard`。

## 待裁定

（无。容量/组相联/替换/双表失效/A/D 合并均由用户 2026-11-19 裁定；`TLB-02` 允许实现自定结构与替换，但既然要求统一，本任务按上述固定。）

## 完成区

（待填）
