# m19-testcases-001: swym N 测试程序（12 位、1+N、SBZ/ILLI、原子）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-001`；`m19-gem5-001` / `m19-chipyard-003`（周期与中断用例）
**可并行分片**：否
**预估**：2–4 h
**档位**：小改
**状态**：待开始

## 背景

现有 `tests/inst/12-misc/swym_oiii_imm.S` 只覆盖 `swym 0` 的功能/编码，明确把 N 的时延倍数列为 GAP。用户 2026-11-27 定了 N=12 位、1+N 拍、高位 SBZ/ILLI、原子中断；需要一个测试程序把这几条固定下来。

## 目标

1. 在 `tests/inst/12-misc/`（或现有 `swym_oiii_imm.S` 扩展）增加一个测试程序，覆盖：
   - `swym 0` ⇒ 1 拍；`swym 1` ⇒ 2 拍；`swym 4095` ⇒ 4096 拍（以 trace/cycle 为准）；
   - `immu18[17:12] != 0` ⇒ `ILLI`；
   - 原子：`swym` 期间 pending 中断不进入，完成后才取（若 Tiny 无中断源，按 `m19-chipyard-003` 的披露口径处理）。
2. 签名/退出码：功能项走现有 signature；周期项允许用引擎 trace 断言，不把宿主时间当 guest 时间。
3. 跨引擎：QEMU 只验功能（NOP，不验时延）；gem5 与 chipyard 验 1+N 与原子。

## 验收（逐条贴真实 rc）

1. 新测试在 QEMU / gem5 / chipyard 上跑通；功能项退出码/签名一致。
2. 周期断言：N=0/1/4095 分别为 1/2/4096 拍；给出 trace 证据。
3. 高位非零 ⇒ ILLI，`cause`/槽位正确。
4. **可达 FAIL ≥2 路**：① 改期望周期 ⇒ 红；② 把高位非零期待成成功 ⇒ 红。
5. `check-inst-asm` / `check-tests-index` 真实 rc=0。

## 约束

独立 `git worktree`；**不提交 git**；不改 QEMU/gem5/chipyard 源码（只加测试资产）；不接板；完成区不写具体 `.work/**` 路径。
