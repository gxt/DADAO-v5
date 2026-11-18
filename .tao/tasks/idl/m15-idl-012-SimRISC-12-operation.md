# m15-idl-012: `SimRISC-12`（其它指令）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：3–5 天
**档位**：中改
**状态**：待开始

## 目标

把 `spec/SimRISC-12-其它指令.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-12.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 28 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `ctlz_orri_rd`
- `ctpop_orri_rd`
- `cttz_orri_rd`
- `lr.b.an_orrr_rd`
- `lr.b.ar_orrr_rd`
- `lr.b.nn_orrr_rd`
- `lr.o.an_orrr_rd`
- `lr.o.ar_orrr_rd`
- `lr.o.nn_orrr_rd`
- `lr.t.an_orrr_rd`
- `lr.t.ar_orrr_rd`
- `lr.t.nn_orrr_rd`
- `lr.w.an_orrr_rd`
- `lr.w.ar_orrr_rd`
- `lr.w.nn_orrr_rd`
- `sc.b.ar_orrr_rd`
- `sc.b.nn_orrr_rd`
- `sc.b.nr_orrr_rd`
- `sc.o.ar_orrr_rd`
- `sc.o.nn_orrr_rd`
- `sc.o.nr_orrr_rd`
- `sc.t.ar_orrr_rd`
- `sc.t.nn_orrr_rd`
- `sc.t.nr_orrr_rd`
- `sc.w.ar_orrr_rd`
- `sc.w.nn_orrr_rd`
- `sc.w.nr_orrr_rd`
- `swym_oiii_imm`

## 交付

1. `idl/SimRISC-12.idl`：上述每条一个 `# id: <id>` + operation；
2. spec 内对应块由 `render.py` 生成（不得手写块内容）；
3. 若某条指令的语义在散文中缺失/矛盾 ⇒ 该条**不写 operation**，记「待裁定」。

## 验收（逐条贴真实 rc）

1. **覆盖率**：`.idl` 的 id 集合 == 本册 `opcodes.yaml` 的 id 集合（脚本比对，零缺零多；「待裁定」的条目单独列出并说明为何不计入）。
2. `python3 idl/render.py --check` rc=0（spec 块与 `.idl` 逐字节一致）。
3. `idlc` 两段式：库 `compile --root isa` rc=0；本册每条 operation `compile --root instruction_operation` 全 rc=0。
4. **语义抽查 ≥3 条**：把 operation 的每条语句与散文逐句对应（贴对照），不得出现散文没说而 operation 自行发明的前提。
5. 「待裁定」逐条列出（问题 + 依据 + 建议），**不得自行处置**。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**；**不改版本号**。
2. 只动 `idl/SimRISC-12.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
