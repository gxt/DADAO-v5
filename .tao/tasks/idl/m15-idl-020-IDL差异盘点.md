# m15-idl-020: IDL 差异盘点（对照 `riscv-unified-db` + 三执行机交叉）

**模块**：idl
**项目里程碑**：M15
**依赖**：无（**只读分析**：不改 `.idl`，可与在跑任务并行）
**可并行分片**：是
**预估**：3–4 h
**档位**：小改（只读 + 写结论）
**状态**：待开始

## 背景（用户 2026-11-20 裁定）

M15 的 12 册 IDL 已全部收尾（263 条 operation），语义库 `idl/lib/fp.idl` 的 ft/fo 族是从 UDB（`riscv-unified-db`）的 `fp.idl` 移植来的。需要一次**差异盘点**回答三件事：

1. 我们**照搬**了 UDB 多少、**偏离**了多少（偏离是有意的 DADAO 语义还是移植错误）；
2. 哪些 operation 是 **DADAO 特有**（UDB 无对应）；
3. 三执行机（QEMU / gem5 / RTL）的**实现是否忠实于 IDL**。

## 对照物（用户 2026-11-20 指定）

- **主参照**：`.cache/refs/riscv-unified-db`（已 `make fetch-refs` 拉取；版本以 `manifests/references.lock.toml` 为准）。
- **交叉参照**：三执行机 —— `components/qemu/patches/target/dadao/**`、`components/gem5/patches/src/arch/dadao/**`、`components/chipyard/patches/generators/dadao-wuming/**`。
- **不需要再做**：`.idl` 块与 spec 散文的一致性（`render.py --check` 已逐字节保证）。

## 要做（**只读**）

1. **operation 级映射**：263 条 IDL operation 逐条判定——
   - **UDB 有对应且语义一致**；
   - **UDB 有对应但语义偏离**（写清偏在哪、依据是 `spec/` 哪一条——**偏离有 spec 依据才算合法**，否则记缺陷）；
   - **DADAO 特有**（UDB 无对应，如 cfx/trap/escape/ldm/stm/`rf2rf` 等）；
2. **函数库映射**：`idl/lib/fp.idl` 的 ft/fo 族与 UDB `fp.idl` 的对应函数逐条比对（哪些是 1:1、哪些改名、哪些改了舍入/tininess/NaN 口径）；
3. **执行机一致性**：按 operation 家族抽查三执行机实现与 IDL 是否一致（重点：边界与异常路径），产出「实现偏离 IDL」清单并标注**哪一侧该改**；
4. **覆盖现场派生**：列清「比对了多少条 operation / 多少个库函数 / 多少个执行机文件」，条数由脚本现场统计。

## 产出格式

每条差异：`<IDL 文件>:<行>` ↔ `<UDB 路径/符号>`（或 `<执行机 文件:行>`）/ 分类（一致 / 偏离 / DADAO 特有 / 实现偏离）/ 依据（spec 章节或「无依据=缺陷」）/ 建议优先级（P0 阻塞在跑任务 / P1 影响正确性 / P2 形态差异）。

## 验收

1. 结论写进本任务书「盘点结论」段（≤80 行）；
2. **覆盖现场派生**（不写死条数），并写清枚举口径（命令）；
3. **抽查 ≥5 条**：UDB 侧与 IDL 侧各贴原文（`sed -n` / `yq` 均可），证明引用真实；
4. **不改任何代码**：`git show --name-only HEAD` 只含本任务书；不重建、不跑仿真。

## 完成区

（待填）
