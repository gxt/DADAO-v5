# m16-chipyard-012: RTL `scmp` 无序结果改 canonical quiet NaN（对齐 spec）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：无（spec 已定，`SimRISC-07 §4` canonical；等 `m16-chipyard-006` 释放 chipyard 写者）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改
**状态**：待开始

## 背景（`m15-testcases-020` 实测发现，四方对齐漏了 RTL）

spec 已把 signaling compare 的无序结果从 **sNaN** 改为 **canonical quiet NaN**（`a6f11e23`，用户 2026-11-19 裁定，版本号不变）。IDL / QEMU / gem5 三方已对齐（`m15-idl-*`、`m15-qemu-001`、`m15-gem5-001`），但 **chipyard RTL 未改**：

`components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingFP.scala.patch` 的 `WumingCompareRecFN`：

```scala
val quietNan = expOnes | (BigInt(1) << (sigWidth - 2))
val sigNan   = expOnes | 1
val nanBits  = Mux(io.signaling, sigNan.U(fmtW.W), quietNan.U(fmtW.W))   // ← 旧口径
```

实测后果：`tests/inst/07-floating-point/{ftscmp,foscmp}_orrr_rf.S` 在 chipyard lane 上 **rc=10**（点 10 红）；QEMU/gem5 两 lane 已 0。

## 要做

1. `WumingCompareRecFN` 的无序结果**一律** canonical quiet NaN（删 `sigNan` 或使其不再被选中）；
2. **`flags` 规则不变**：signalcing compare 无序恒置 `NV`；quiet compare 仅 `sNaN` 置——即 `io.flags` 那一行保持不动；
3. `WumingMinMax` 已用 canonical（`canon` 常量），**不要**误改成同一份常量以外的行为；若能把两处 canonical 常量合并复用则合并，不能则各自保留并注明；
4. 检查同文件/同目录是否还有其它 `sigNan` 结果路径（`grep -rn "sigNan"`），**结果**用 sigNan 的一并订正，**标志**用途的保留。

## 验收（逐条贴真实 rc）

1. **两册回流**：`ftscmp_orrr_rf.S`/`foscmp_orrr_rf.S` 在 chipyard lane **rc=0**（改前 rc=10），给逐检查点输出；
2. **四方一致**：同一批 `.S` 在 IDL/QEMU/gem5/chipyard 四方结果**逐字节一致**（给对照）；
3. **不回归**：`ftqcmp`/`foqcmp`、`ftmin/ftmax/fomin/fomax` 等既有 FP 册 rc=0；`m16-chipyard-001` 的周期基线镜像**抽测不回退**；
4. **可达 FAIL**：把 `nanBits` 改回 `Mux(signaling, sigNan, quietNan)` ⇒ 两册 rc=10（`cp`+md5 还原 + 重建）；
5. `check-patch-tree` chipyard 段 0 问题；`check-gem5-decode`/`check-index-blobs` rc=0；合并态（`Process-07 §5a`）。

## 完成区

（待填）
