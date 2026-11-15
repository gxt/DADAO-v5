# m13-qemu-016: QEMU 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（`insn.decode`/`trans_fp`/`translate`）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-spec-010`（spec 侧已合 `cb8ca30d`：删 `ft2ft`/`fo2fo`、加 `rf2rf`；id 264→263）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（看 diff + ≥2 路注入 + 相关门控）
**状态**：待开始

## 背景

`m13-spec-010` 只改了 spec 侧。现场仍有一处**仓库自相矛盾**：`contracts/opcodes.yaml` 已无 `ft2ft`/`fo2fo`，但 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 仍在且被 `tests/inst.yaml` 索引（2 条），**没有任何门控能发现**。本任务把该组件面与 spec 对齐。

## 任务

1. `components/qemu` 补丁：`insn.decode` 删两条、加 `rf2rf`；`trans_fp.c.inc` 实现整 64 位逐位块复制（`immu6` 个数、`rf0` 作目的 ⇒ `ILLI`、重叠/越界/`immu6=0` ⇒ `ILLI`）；`translate.c` 接线；
2. 语义按 `spec/SimRISC-02`（`m13-spec-010` 定稿）实现，**不得从其它实现反推**；
3. 补丁导出 + `check-patch-tree` **qemu 段 0 问题**、`--source-state` qemu OK。

## 验收（逐条贴真实 rc）

1. 旧指令在**本组件面**归零：`grep -rn "ft2ft\|fo2fo"` 在 `components/qemu/**` = 0（历史归档/ADB/任务书豁免）；
2. 新指令 `rf2rf` 在本组件面落地：`rf2rf` 逐位复制且 6 条非法情形各报 `ILLI`；`ft2ft`/`fo2fo` 解码为非法；
3. 门控：`check-qemu-forms`、`check-patch-tree`（qemu 段）、`--source-state` qemu、`check-component-changelog` 全 rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 把 `immu6=0` 判成合法 ⇒ 负例应红；② 把目的 `rf0` 放行 ⇒ 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束

- 只改 `components/qemu/**`、本任务书；
- 不改 `spec/`、`contracts/`（已由 `m13-spec-010` 定稿；如需改，停下写「待裁定」）；
- 禁 `install-host`/`check-modules`/`build-*`（组件重建除外，按需并在完成区申报耗时）；不 sync/reset 节点；
- 不提交 git；注入还原用 `cp`+md5。
