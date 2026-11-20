# m16-chipyard-014: 窄 `lr` 三条序改「只写低 W 位、高位保持」（RTL）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无（`m15-idl-020` D3 已给依据；IDL 侧已于 2026-11-19 裁定完成）
**依赖补充**：`m16-chipyard-007` 合入（同组件单写者）
**可并行分片**：否（chipyard 单写者）
**预估**：1–2 h
**档位**：小改
**状态**：待开始

## 背景（`m15-idl-020 IDL 差异盘点` D3）

**用户 2026-11-19 裁定**：窄 `lr`（`lr.t`/`lr.w`/`lr.b`，各 `.nn`/`.an`/`.ar` 三序，**共 9 条**）**只写目标寄存器低 W 位、高位保持原值**（非零扩展、非符号扩展）。IDL 已按此实现（`idl/SimRISC-01.idl` 的 9 条 `lr` body）。

**RTL 侧仍是整 64 位零扩展**：`components/chipyard/patches/generators/dadao-wuming/**` 的 `WumingCore.scala`（`memSignedLat:=false.B // lr zero-extends` 处）

`MEMORY.md` 与 `m15-idl-012` R2 已登记「实现侧需据此修正」，本任务即该修正。

## 要做

把 9 条窄 `lr`（`lr.{t,w,b}.{nn,an,ar}`）的结果写回改成：**读目标寄存器旧值 → 只替换低 W 位（`.t`=32、`.w`=16、`.b`=8）→ 写回**；`lr.o`（64 位）**不动**。

**oracle 是 IDL**：以 `idl/SimRISC-01.idl` 对应 9 条 body 的语义为准（`render.py` 已保证它与 spec 一致），**不得**按 RISC-V/ARM 的零扩展习惯实现。

## 验收（逐条贴真实 rc）

1. **行为与 IDL 一致**：9 条各给「高位置哨兵旧值 → `lr` → 高 W 位保持、低 W 位为新值」的实测（chipyard 侧用例或探针）；
2. **`lr.o` 不回归**（仍整 64 位）；
3. **不回归**：Tiny 首册 38 镜像、`m16-chipyard-001` 周期基线抽测
4. **可达 FAIL**：把某条改回整 64 位零扩展 ⇒ 对应用例红（`cp`+md5 还原 + 重建）；
5. `check-patch-tree` **chipyard 段 0 问题**；合并态（`Process-07 §5a`）。

## 完成区

（待填）
