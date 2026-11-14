# m13-chipyard-002: `sc` 保留判据去掉「整字值比较」（严格按 spec 的精确地址+宽度）

**模块**：chipyard
**项目里程碑**：M13
**依赖**：无（与 `m13-qemu-014` 并行无冲突，但**共用 `m13-testcases-037`** 的三平台复验）
**可并行分片**：否（RTL 单写者）
**预估**：2–3 h
**状态**：待开始

## 用户裁定（2026-11-14，原话）

> 「ISS-435：严格按spec来」

- 落地含义：保留标记粒度 = **精确地址 + 访问宽度**（`spec/SimRISC-12 §1`「保留机制」段）；`sc` 的成败**只能**由「保留标记是否仍持有 + 键是否匹配」决定，**不得**因为「同一 8 字节字的值变了」而失败。

## 现状（现场）

- `generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala`：
  - 保留键**已经**是精确地址 + 宽度（`resvValid`/`resvAddr`/`resvWidth`，L467-472 的 `scHit` 用 `resvAddr === lrscAddr(47,0)` 与宽度比较）；
  - 但**额外**保存了 `resvWord`（`lr` 读到的整字），`sc` 时若该字值变化就失败（注释自述「legal spurious failure」）。
- 实测（`m13-testcases-028` 的 `probe_gran.S`，同 ELF）：**同 hart 改同字另一字节 ⇒ chipyard 的 `sc` 失败**（`rc=2`），gem5 通过、QEMU 另有一处不一致。
- 严格口径下，「同字另一字节被写」**不属于** spec 列出的清除事件 ⇒ `sc` 必须成功；把它做成确定性失败等于把粒度偷偷放大到整字值。

## 目标

1. **去掉 `sc` 的整字值比较**：`sc` 的成功条件 = `resvValid && resvAddr === 精确地址 && resvWidth === 访问宽度`；删除 `resvWord` 寄存器与其比较路径（若保留用于诊断，必须在 `sc` 判据中**不参与**，并注释说明）。
2. **清除事件严格按 spec**：另一条 `lr`、异常/中断进入、`sc` 自身（成败都清）。**普通 store 不清除**（同 hart 写同地址也不清）。
3. 注释同步改述：删掉「matches QEMU's word-granularity reservation」与「changed word is a legal spurious failure」的旧口径，改为「按 spec 精确地址+宽度；多 hart 同址 store 的清除依赖一致性事件，当前单 hart 无载体（GAP）」。

## 验收（逐条贴真实输出）

1. **改前正证**：改前 RTL 构建的 harness 跑 `probe_gran.S` 的「同字另一字节」点 ⇒ `sc` 失败（贴 rc/输出 + harness md5）。
2. **改后**：同点 ⇒ `sc` 成功；「同地址同宽度写后再 `sc`」按 strict 口径仍成功（同 hart 写不清除）——若你认为该点应失败，停下写「待裁定」。
3. **既有 `lr`/`sc` 用例不回归**：`tests/inst/12-misc/` 的 24 个原子 id 三平台逐字节；`sc` 成功/失败的既有断言点全绿。
4. `check-patch-tree` chipyard 段 0 问题、`--source-state` chipyard OK、changelog M13 一条、补丁重导出。
5. ≥1 路可达 FAIL 注入（`cp`+md5 还原）：把 `scHit` 改回带 `resvWord` 比较 ⇒ 对应点红。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## GAP（写进完成区，不伪造）

- **多 hart 对同一精确地址+宽度 store 的清除**：`WumingTinyConfig` 单 hart，无观测载体；RTL 侧仅保证键与清除时机，不造用例。
- 值无关的「同值写也应清除」同理不可测。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host` / `check-modules`**；chipyard 组件**单写者** —— 开工前 `pgrep -af "build-chipyard|make verilog|verilator"` 并确认主会话已放行（`m12-chipyard-016` 可能仍在跑）。
3. 构建纪律：改 RTL 后必须删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>` 再 `make verilog`（否则静默沿用旧 RTL）。
4. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
5. 只改 `generators/dadao-wuming/src/main/scala/wuming/**` + 对应补丁 + `components/chipyard/changelog.md`；**不改** `spec/`、`contracts/`、`tests/**`。
6. 大文件落 `/tmp/opencode/m13-chipyard-002/` 并测完即删。

## 待裁定

（实现中写）

## 审阅记录

（待填）
