# m13-chipyard-003: chipyard 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（译码/执行 + sim 重建 + 三平台差分复核）

**模块**：chipyard
**项目里程碑**：M13
**依赖**：`m13-spec-010`（已合 `cb8ca30d`）；`m13-llvm-001`/`m13-qemu-016`/`m13-testcases-047`/`m13-gem5-015` 均已合入，**三平台其余两方已有 `rf2rf`**
**可并行分片**：否（chipyard 组件单写者）
**预估**：2–3 h（含 sim 重建 20–40 min）
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：待开始

## 语义真源

`spec/SimRISC-02`（`rf2rf` 段）+ `contracts/opcodes.yaml::rf2rf_orri_rf`：`opc=OPC-octa(0x40)`、`opx=111-100(ha=0x3C)`、`orri`/`rf`；整 64 位逐位复制、不置标志；`immu6=0`/两端越界/任意重叠 ⇒ ILLI；**目的含 `rf0` ⇒ ILLI**、源 `rf0` 合法。

## 任务

1. `WumingDecoder.scala`：删两条旧译码、加 `rf2rf`（`opx=111-100`）；
2. `WumingFP.scala`（或块复制所在文件）：实现整 64 位逐元素搬移 + 六类非法（**在任何寄存器写之前判定**）；
3. 删 `ft2ft`/`fo2fo` 的执行路径；
4. 重建 sim（`make verilog`/`build-chipyard` 按现有 Makefile 目标，申报耗时），记录**新 sim md5**（旧基线 `079ae015…` 作废，需在完成区登记新值）；
5. **三平台复核**：用 `run_asm_suite.py` 对 `tests/inst/02-reg-copy/rf2rf_orri_rf.S`（17 点/7 镜像）跑 **qemu + gem5 + chipyard**，三点逐字节一致；若 chipyard 侧因机型不支持某故障例 ⇒ 记 GAP 并给 spec 依据，不伪造。

## 验收（真实 rc）

1. `rf2rf` 在 chipyard Tiny 上：`immu6=3` 三元素逐位复制、源不变；六类非法各 `ILLI`；源 `rf0` 合法；
2. 旧指令编码 ⇒ 非法（与 qemu `0xF9`、gem5 `FaultUNDI` 同口径说明）；
3. 三平台差分：`rf2rf` 7 镜像逐字节一致（贴三平台 rc 与字节数）；**新 sim md5** 登记；
4. 门控：`check-patch-tree`（chipyard 段 0 问题）、`--source-state` chipyard OK、`check-component-changelog`、`check-no-residue`、`check-inst-asm`（应仍 PASS：qemu 侧）；
5. **≥2 路注入**（`cp`+md5 还原）：① 放行目的 `rf0` ⇒ 负例红；② 重叠放宽为"仅完全重合" ⇒ 部分重叠负例红；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/chipyard/**`、本任务书；不改 `spec/`、`contracts/`、`tests/inst/**`、其它组件；
- 构建按需（`JOBS=32`，**申报耗时**）；**禁 `install-host`/`check-modules`**；**禁 `git reset --hard`**；不 sync/reset 节点；
- 注意：`server208` 与 `ics170` 上可能仍有 M12 遗留 sim 进程，**禁 kill**（若非本任务进程）；
- 不提交 git；注入还原 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
