# QEMU 组件变更记录

> 粒度：**按任务一条**，追加式。补丁集的生成/应用/校验规范见 `spec/Process-01-组件补丁组织与构建编排.md`。

| 日期 | 任务 | 变更 |
|---|---|---|
| 2026-09-23 | — | **M1 补丁集重整**：由「16 份编号补丁 + `git am`」改为「树形补丁集 + `git apply`」（本组件 8 → **31** 份 = 新增 25 + 修改 6）。应用后最终 tree hash = `4a14d56ce4ecfc6f5edd2f2d181ec6628844233b`（与重整前一致，语义未变）。决策见 `ADR-0002 D4`（rev. 2026-09-23）。 |
| 2026-10-03 | `QEMU-034t` | **FP 执行层基础设施 + RF 数据搬运族（16 条）从 ILLI 桩换为真实 TCG**。新建 `target/dadao/insn_trans/trans_fp.c.inc`（60 条 `scope:fp` trans：16 真实 + 44 保留 ILLI 桩），并从 `trans_arith`（42 个）/`trans_compare`（2）/`trans_block`（2）/`trans_mem`（8）/`trans_cond_assign`（5）/`trans_imm`（1）删除对应 FP 桩；`translate.c` 新增 `RF0_WRITE_MASK`/`load_rf`/`store_rf`（rf0=FCSR，写掩码 `[33:32]+[4:0]`）并 include 新文件。实现家族：`rf_mem`（`ld.t/st.t/ld.o/st.o/ldm.t/stm.t/ldm.o/stm.o` 的 `-rf`）、`rf_move`（`rd2rf`/`rf2rd`）、`set.w-rf`、`cs.n/z/p/eq/ne-rf`；translate 期合法性 `dst_rf0`/`mreg_zero`/`mreg_range_overflow`。补丁 **31 → 32**（qemu），全仓 **68 → 69**；`check_qemu_trans` **227/227 (M1 152/152)** 不变。 | engineer |
| 2026-10-03 | `QEMU-035t` | **FP 位级语义族（10 条）从 ILLI 桩换为真实 TCG（纯位运算，无 softfloat）**：`sign` 4（`ftsgnj/ftsgnn/fosgnj/fosgnn`，`rfHD=rf0`→`abs`/`-abs`、`rfHC==rfHD`→`copy`/`negate` 自然成立；`ft` 用 bit31、`fo` 用 bit63，按完整 64 位注入并保持非符号位）、`classify` 2（`ftcls`/`focls`，10 类位 `[9:0]`、`[63:10]` 清零，orri 块形式 `immu6` 1–63 先读后写）、`compare` 4（`ftqcmp/ftscmp/foqcmp/foscmp`，结果 `1/0/-1` 写 rd；unordered 静默返回 qNaN / 信令返回 sNaN，符号位 0）。合法性：sign `dst_rf0`、classify `mreg_zero`/`mreg_range_overflow`（源/目的双侧）。仅改 `trans_fp.c.inc`；补丁**无新增**（仍 32/69）。`check_qemu_trans` **227/227 (M1 152/152)** 不变。 | engineer |
