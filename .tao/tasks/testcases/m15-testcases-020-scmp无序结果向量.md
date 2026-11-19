# m15-testcases-020: `scmp` 无序结果向量（canonical quiet NaN）

**模块**：testcases
**项目里程碑**：M15
**依赖**：spec 已改（`a6f11e23`）；`m15-idl-018`/`m14-qemu-008`/`m16-gem5-015` 的三方实现同步（向量须三方一致）
**可并行分片**：否（改 `tests/inst/07-floating-point/`）
**预估**：1–2 h
**档位**：小改
**状态**：待开始

## 背景（订正：原判断有误）

`tests/inst/07-floating-point/ftscmp_orrr_rf.S` 与 `foscmp_orrr_rf.S` **有点 10–16 的无序用例**，但它们用 `TEST_FPCMP_S` 宏，目前只做**结构断言**（符号位 0 + 指数/quiet 位形态 + 尾数非 0，见 `07-floating-point.inc:287`），**没有钉住 canonical 的完整位型**；`m15-qemu-001` 实测在 new spec 下 guest **rc=10**（点 10 红）⇒ 这些点与宏需要一起订正。

## 必读

`m15-qemu-001` 的证据：新 spec 下 `ftscmp`/`foscmp` 的无序结果 = **canonical quiet NaN**（ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`），`qcmp` 同为 canonical、`NV` 规则不变（scmp 无序恒置、qcmp 仅 sNaN 置）。

## 要做

在两条 `.S` 的链例中补无序用例（`TEST_FPCMP` 宏形态照现有行）：

1. `qcmp`：仅 qNaN ⇒ 结果 canonical、**不置 NV**；
2. `qcmp`：含 sNaN ⇒ 结果 canonical、**置 NV**；
3. `scmp`：仅 qNaN ⇒ 结果 canonical、**置 NV**；
4. `scmp`：含 sNaN ⇒ 结果 canonical、**置 NV**；
5. **双 NaN**（`rfHC`/`rfHD` 都是 NaN，含一个 sNaN）⇒ 结果 canonical（**不再传播 payload**）、`NV` 按规则；
6. `ft` 与 `fo` 两种格式各覆盖一遍（`ft` 结果按 `SimRISC-00 §2.3` 的写宽）。

## 验收

1. 三方（`run_inst_tiny.py` 的 chipyard/QEMU/gem5 lane，或 `tests/ee-*` 对应入口）跑新用例 **逐字节一致**；
2. 检查点由 `.S` 现场统计（不写死）；
3. 可达 FAIL：把某个无序用例的期望改回 sNaN 位型 ⇒ 该例红（`cp`+md5 还原）；
4. `check-case-ledger`（`--write` 重生成后再跑）rc=0。

## 完成区

（待填）
