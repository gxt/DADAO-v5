# m13-gem5-015: gem5 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（解码表 + exec + 周期表）

**模块**：gem5
**项目里程碑**：M13
**依赖**：`m13-spec-010`（已合 `cb8ca30d`）；`m13-llvm-001`（已合 `75364281`）、`m13-qemu-016`（已合 `ca916300`）可作**交叉检查**（不作期望来源）
**可并行分片**：否（gem5 组件单写者）
**预估**：2–3 h
**档位**：中改（≥2 路注入 + 相关门控）
**状态**：待开始

## 语义真源

`spec/SimRISC-02`（`rf2rf` 段）+ `contracts/opcodes.yaml::rf2rf_orri_rf`：`opc=OPC-octa(0x40)`、`opx=111-100(ha=0x3C)`、`orri`/`rf`；整 64 位逐位复制、不置标志；`immu6=0`/两端越界/任意重叠 ⇒ ILLI；**目的含 `rf0` ⇒ ILLI**、源 `rf0` 合法。

## 任务

1. `components/gem5` 补丁：`decode_table.inc` / `decode_assertions.inc` / `decode-assertions.tsv` 删两条旧、加 `rf2rf`（**由生成器产出，不手改**）；`inst.cc`/`exec` 实现整 64 位逐元素搬移与六类非法；
2. `b7.cc` / `b7_test.cc` / `fp_soft.cc` 内旧指令引用清理；
3. `wuming_cycles.cc`（周期表）删两条旧、加 `rf2rf` 行（值由 `docs/core-wuming-cycle-model.md` 现场解析；若文档无该行 ⇒ **停下写「待裁定」**，不要自拟拍数）；
4. 补丁导出 + `check-patch-tree` **gem5 段 0 问题** + `--source-state` gem5 OK + `check-component-changelog`。

## 验收（真实 rc）

1. `rf2rf` 语义：`immu6=3` 三元素逐位复制、源寄存器不变；六类非法各 `ILLI`；源 `rf0` 合法（贴实测）；
2. 旧指令编码 ⇒ 非法（UNKNOWN/UNDI 口径按 gem5 现状，与 qemu 的 `0xF9` 对齐说明）；
3. 门控：`check-gem5-decode`、`check-wuming-cycles`、`check-patch-tree`（gem5 段）、`--source-state` gem5、`check-component-changelog`、`check-no-residue`；
4. **≥2 路注入**（`cp`+md5 还原）：① 放行目的 `rf0` ⇒ 负例红；② 重叠判定放宽为"仅完全重合" ⇒ 部分重合负例红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- 只改 `components/gem5/**`、`tools/gem5/**`（生成器/周期表侧必要时）、本任务书；**不改** `spec/`、`contracts/`、`tests/inst/**`、其它组件；
- 构建按需（`JOBS=32`，申报耗时）；禁 `install-host`/`check-modules`；**禁 `git reset --hard`**；不 sync/reset 节点；
- 不提交 git；注入还原 `cp`+md5。

## 待裁定

（实现中写）

## 审阅记录

（待填）
