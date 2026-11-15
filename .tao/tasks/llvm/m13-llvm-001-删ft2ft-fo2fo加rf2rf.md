# m13-llvm-001: LLVM 侧删 `ft2ft`/`fo2fo`、加 `rf2rf`（.td/MC/AsmParser/MCInstPrinter + lit）

**模块**：llvm
**项目里程碑**：M13
**依赖**：`m13-spec-010`（spec 侧已合 `cb8ca30d`：删 `ft2ft`/`fo2fo`、加 `rf2rf`；id 264→263）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（看 diff + ≥2 路注入 + 相关门控）
**状态**：待开始

## 背景

`m13-spec-010` 只改了 spec 侧。现场仍有一处**仓库自相矛盾**：`contracts/opcodes.yaml` 已无 `ft2ft`/`fo2fo`，但 `tests/inst/07-floating-point/{ft2ft,fo2fo}_orri_rf.S` 仍在且被 `tests/inst.yaml` 索引（2 条），**没有任何门控能发现**。本任务把该组件面与 spec 对齐。

## 任务

1. `components/llvm-project` 补丁：`DADAOInstrInfo{,FP}.td` 删两条定义、加 `rf2rf`（`opc=OPC-octa`、`opx=111-100`、`orri`/`rf` 组、目的含 `rf0` ⇒ 由 legality 诊断/报错）；`AsmParser` 助记符、`MCInstPrinter` 反汇编；
2. lit：`tests/unit/llvm/lit/MC/DADAO/` 与 `CodeGen/DADAO/` 增删对应用例；`DADAO-gen` 生成矩阵同步；
3. 补丁用 `make_patch.py llvm` 导出，`check-patch-tree` **llvm 段 0 问题**、`--source-state` llvm OK。

## 验收（逐条贴真实 rc）

1. 旧指令在**本组件面**归零：`grep -rn "ft2ft\|fo2fo"` 在 `components/llvm-project/**`、`tests/unit/llvm/**` = 0（历史归档/ADB/任务书豁免）；
2. 新指令 `rf2rf` 在本组件面落地：`rf2rf` 可汇编/反汇编、编码与 `contracts/opcodes.yaml` 一致、`ft2ft`/`fo2fo` 报未知助记符；
3. 门控：`check-lit`、`check-patch-tree`（llvm 段）、`--source-state` llvm、`check-component-changelog` 全 rc=0；
4. **≥2 路可达 FAIL 注入**（`cp`+md5 还原）：① 把 `rf2rf` 的 `opx` 改一位 ⇒ 编码 lit 应红；② 删 `dst_rf0` 相关诊断 ⇒ 负例 lit 应红；
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束

- 只改 `components/llvm-project/**`、`tests/unit/llvm/**`、本任务书；
- 不改 `spec/`、`contracts/`（已由 `m13-spec-010` 定稿；如需改，停下写「待裁定」）；
- 禁 `install-host`/`check-modules`/`build-*`（组件重建除外，按需并在完成区申报耗时）；不 sync/reset 节点；
- 不提交 git；注入还原用 `cp`+md5。
