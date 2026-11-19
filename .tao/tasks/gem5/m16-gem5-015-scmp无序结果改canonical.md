# m16-gem5-015: `scmp` 无序结果改 canonical quiet NaN（spec 已改）

**模块**：gem5
**项目里程碑**：M16
**依赖**：spec 修改已落盘（`a6f11e23`）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-19 授权，版本号不变）

`spec/SimRISC-07 §4` 已把 signaling compare 的无序结果从 **sNaN** 改为 **canonical quiet NaN**（对齐 IEEE 754-2019 §6.2.1 的 `shall`）；quiet/signaling 的差别只剩 `NV` 标志。

## 要做

`components/gem5/patches/src/arch/dadao/exec/b7.cc.patch`（及 `b7.hh`/`b7_test.cc` 如涉及）：无序分支的 `fp::snanBits(spec.fmt)` 改为 **canonical quiet NaN**（`qnanBits`），`NV` 规则不变。

## 验收

1. 重建 gem5（按仓库既有流程）；跑 Vast/Tiny 侧浮点归属用例不回归（`tests/inst/07-floating-point/*scmp*`）；
2. **新增/临时**无序用例（qNaN、sNaN、双 NaN × ft/fo）验证结果 == canonical、`NV` 符合规则（真实输出）；
3. 可达 FAIL：改回 sNaN ⇒ 红（`cp`+md5 还原 + 重建）；
4. `check-patch-tree`（gem5 侧）、`check-index-blobs` rc=0。

## 完成区

（待填）
