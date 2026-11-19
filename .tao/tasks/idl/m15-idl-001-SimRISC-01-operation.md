# m15-idl-001: `SimRISC-01`（取数存数）逐条 operation

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-spec-001`（语法基线、寄存器模型、语义库、`idl/render.py` 已就绪）
**可并行分片**：可与其它 `m15-idl-0xx` 并行（**各册独立文件**）；`idl/README.md §4` 语义库**不得自行动手**（缺函数 ⇒ 待裁定）
**预估**：5–7 天
**档位**：中改
**状态**：待开始

## 目标

把 `spec/SimRISC-01-取数存数.md` 里**每条指令**写成一段 operation，落到 **`idl/SimRISC-01.idl`**，再由 `idl/render.py` 生成 spec 内的 `<!-- IDL:<id> BEGIN/END -->` 块。

> 本册若已有 `m15-spec-001` 留下的样板 operation（01/04/06/11/12 各 1 条），按**同一风格**补齐其余指令，不重写已有样板。

## 用户裁定（2026-11-19，必须遵守）

1. **不修改原来的散文内容**——`spec/` 里只允许 `render.py` 写标记块，散文一字不动；
2. **发现散文不对、或与其它册/`spec` 冲突 ⇒ 停下来问用户**：写进任务书「待裁定」（问题 + 依据 + 候选解释），**不得自行改散文、不得自行改语义库**；
3. 正常情况下**每条指令一个 operation**（一 `# id:` 一段）；确需合并/拆分时同样记「待裁定」。

## 指令清单（本册 38 条，以 `contracts/opcodes.yaml` 的 `spec_cite` 为准）

- `ld.o_rrii_ra`
- `ld.o_rrii_rb`
- `ld.o_rrii_rd`
- `ld.o_rrii_rf`
- `ld.sb_rrii_rd`
- `ld.st_rrii_rd`
- `ld.sw_rrii_rd`
- `ld.t_rrii_rf`
- `ld.ub_rrii_rd`
- `ld.ut_rrii_rd`
- `ld.uw_rrii_rd`
- `ldm.o_rrri_ra`
- `ldm.o_rrri_rb`
- `ldm.o_rrri_rd`
- `ldm.o_rrri_rf`
- `ldm.sb_rrri_rd`
- `ldm.st_rrri_rd`
- `ldm.sw_rrri_rd`
- `ldm.t_rrri_rf`
- `ldm.ub_rrri_rd`
- `ldm.ut_rrri_rd`
- `ldm.uw_rrri_rd`
- `st.b_rrii_rd`
- `st.o_rrii_ra`
- `st.o_rrii_rb`
- `st.o_rrii_rd`
- `st.o_rrii_rf`
- `st.t_rrii_rd`
- `st.t_rrii_rf`
- `st.w_rrii_rd`
- `stm.b_rrri_rd`
- `stm.o_rrri_ra`
- `stm.o_rrri_rb`
- `stm.o_rrri_rd`
- `stm.o_rrri_rf`
- `stm.t_rrri_rd`
- `stm.t_rrri_rf`
- `stm.w_rrri_rd`


- **批 1**：§1. 存取RD寄存器 + §2. 存取RB寄存器
- **批 2**：§3. 存取RA寄存器 + §4. 存取RF寄存器


- **批 1**：§1. 存取RD寄存器
- **批 2**：§2. 存取RB寄存器
- **批 3**：§3. 存取RA寄存器
- **批 4**：§4. 存取RF寄存器

## 批次（每批 ≤4 h；做完一批返回，由主会话续派下一批）

> 任务号不拆（整册一起验收）；**同一个 `.idl` 文件，同册串行**。每批只做列出的节，做完即返回，不提交。全册 38 条 ⇒ 分 4 批。

- **批 1**：§1. 存取RD寄存器
- **批 2**：§2. 存取RB寄存器
- **批 3**：§3. 存取RA寄存器
- **批 4**：§4. 存取RF寄存器

## 前置（语义库 v1 连带，`m15-idl-013`）

本册样板 `.idl` 里若出现 `{16'd0, ip()}`（`m15-spec-001` 时代写法），按 T1 裁定改为 `ip()` —— `ip()` 现为 `Bits<64>`、高 16 位恒 0；旧写法会拼成 80 位，而 **idlc 不校验位宽、不会报错**，必须人工核。

## 交付

1. `idl/SimRISC-01.idl`：上述每条一个 `# id: <id>` + operation；
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
2. 只动 `idl/SimRISC-01.idl` + spec 本册的标记块 + 本任务书；**不动其它册**。
3. **不改 `idl/README.md`**（语义库）——缺函数就记「待裁定」。
4. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

（待填）
