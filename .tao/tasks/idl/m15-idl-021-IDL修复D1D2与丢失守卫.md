# m15-idl-021: IDL 修复批（D1 `rb0` 写宽 + D2 8 条 rf 对齐守卫 + 补丢失守卫 + 注释订正）

**模块**：idl
**项目里程碑**：M15
**依赖**：无（`m15-idl-020` 盘点已给依据；`spec-006` 的册名不影响本任务）
**可并行分片**：否（改 `.idl` 源 → 重渲染 spec）
**预估**：3–4 h
**档位**：中改
**状态**：待开始

## 背景（`m15-idl-020 IDL 差异盘点` 的 D1/D2 + N31 的丢失守卫）

1. **D1（P1）`jump`/`br.*` 的 `rb0` 写回宽度**：IDL 的 `jump()` 只写 `target[47:0]`；而 `spec/SimRISC-06 §1/§2`、`ADR-0012 D8.3/D8.4`（「`rb0[63:48]` 恒为 0」已**作废**）、三执行机（QEMU `tcg_gen_st_i64`、gem5 `branchTo(uint64_t)`+b5.hh「over all 64 bits」、RTL `jumpTarget=(…)(63,0)`）都**写完整 64 位、取低 48 位去取指**。
2. **D2（P1）8 条 rf 访存缺对齐守卫**：`ld.t_rrii_rf`/`st.t_rrii_rf`/`ld.o_rrii_rf`/`st.o_rrii_rf`/`ldm.t_rrri_rf`/`stm.t_rrri_rf`/`ldm.o_rrri_rf`/`stm.o_rrri_rf` —— `SimRISC-01 §4` 正文（`.t`=4 / `.o`=8 字节）+ 附录 B `excp_malign` **32 条含这 8 条** + `contracts/opcodes.yaml` 的 `aligned(4/8)`/`rule_refs:[excp_malign]` **三方一致**。
3. **丢失守卫（N31）**：`m15-idl-001` 的 8 条 rf 守卫曾实现（证据 md5 `828191b0…`）但**未提交即丢失**，合入版（`0c5df887…`）无守卫；本次一并补做。
4. **过期注释**：8 条 rf 的「本册附录 B 的 `excp_malign` 未列本族 ⇒ 不判 MALIGN」前提已被 `af7ffb09` 推翻，且注释里的「§4 正文与附录 B 不一致，两处待统一」也不再成立。

## 要做

1. **D1**：改 `idl/SimRISC-06.idl` 的 `jump()`/分支写回——`rb[0]` 写**完整 64 位**（`target` 为 `Bits<64>`），取指侧取低 48 位（由 `ip()` 的语义或调用点体现，按 spec 措辞）；
2. **D2**：8 条 rf 各加对齐守卫（`.t` 族 `is_naturally_aligned(32, ea)`、`.o` 族 `is_naturally_aligned(64, ea)` ⇒ `raise(Malign)`），**顺序按 `m15-idl-001` R1 裁定「静态先」**；
3. **订正过期注释**（8 条 rf 块头）：删「附录 B 未列本族 ⇒ 不判 MALIGN」与「两处待统一」，改为指向 §4 + 附录 B + 合同一致；
4. **重渲染**：`python3 idl/render.py` 更新 12 册 spec 块；`spec/.manifests.toml` 相应 sha256 同笔重算；
5. **顺带清 `spec-006` 遗留**（若 `spec-006` 已合入）：
   - `.idl` 注释里 **9 处 `idl/README §N`** 改成新册 `spec/IDL-ISA语义描述语言与语义库.md` 的 §N；
   - 新册 §4.7 的 **3 处 `m15-idl-016/017`** 任务号去掉（改为「实现见 `discussion.md` N30」或直接删）。

## 验收（逐条贴真实 rc）

1. `python3 idl/render.py --check` rc=0（263 条 / 12 册逐字节一致）；
2. `check-idl-sync`、`check-manifests-guard`、`check-fp-contract`、`check-legality-drift`、`check-spec-*`、`check-knowledge-refs` 全 rc=0；
3. **D1 行为**：`jump` 的 `rb[0]` 为 64 位（`Bits<64>`），与三执行机一致；用 `compile_expression` 核 `rb[0]` 的 `type.width == 64`；
4. **D2 行为**：8 条 rf 的 `Malign` 守卫在位且顺序在静态判定之后（用 `check_semantics.py` 或等价核）；
5. **可达 FAIL ≥2 路**：① 去掉 `ld.t_rrii_rf` 的对齐守卫 ⇒ 对应用例/断言红；② 把 `jump()` 改回只写 `[47:0]` ⇒ 宽度断言红（`cp`+md5 还原）；
6. 散文零改动（基线固定 commit，剥块后逐字节比对）。

## 完成区

（待填）
