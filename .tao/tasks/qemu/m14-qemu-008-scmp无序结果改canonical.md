# m14-qemu-008: `scmp` 无序结果改 canonical quiet NaN（spec 已改）

**模块**：qemu
**项目里程碑**：M14
**依赖**：spec 修改已落盘（`a6f11e23`）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-19 授权，版本号不变）

`spec/SimRISC-07 §4` 已把 signaling compare 的无序结果从 **sNaN** 改为 **canonical quiet NaN**（对齐 IEEE 754-2019 §6.2.1 的 `shall`）；quiet/signaling 的差别只剩 `NV` 标志。

## 要做

`components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch` 的 `FP_CMP_NV_UNORDERED` 分支：无序结果由 sNaN 位型改为 **canonical quiet NaN**（`ft`/`fo` 各自格式），`NV` 置位规则**不变**（signaling 无序即置；quiet 仅 sNaN 置）。

## 验收

1. QEMU 重建后跑 `tests/inst/07-floating-point/ftscmp_orrr_rf.S` 与 `foscmp_orrr_rf.S` ⇒ 通过（现有用例无 NaN，需保证不回归）；
2. **新增/临时**无序用例（qNaN、sNaN、双 NaN × 两种格式）验证结果 == canonical 且 `NV` 符合规则（给真实输出）；
3. 可达 FAIL：改回 sNaN ⇒ 该用例红（`cp`+md5 还原）；
4. `check-patch-tree`（qemu 侧）rc=0。

## 完成区

（待填）
