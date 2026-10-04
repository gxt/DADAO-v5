# QEMU-028t: `st.*` 源为 0 号寄存器被误判 ILLI 的修复

**模块**：qemu
**项目里程碑**：M2
**依赖**：`SPEC-055t`（`ADR-0015` Accepted；合约澄清）
**状态**：已验证

## 问题

QEMU 的 4 个翻译函数把 `st.*` 的**源**字段 `ha` 当成**目的**，误判 ILLI：

```c
static bool trans_st_b_rrii_rd(...)  { if (a->ha == 0) { gen_exception_illegal(ctx); return true; } ... }
static bool trans_st_w_rrii_rd(...)  { if (a->ha == 0) { ... } }
static bool trans_st_t_rrii_rd(...)  { if (a->ha == 0) { ... } }
static bool trans_st_o_rrii_rd(...)  { if (a->ha == 0) { ... } }
static bool trans_st_o_rrii_rb(...)  { if (a->ha == 0) { ... } }   ← 源为 rb0
```

`stm.*` 的 RRRI 变体同理（须逐条核查）。

按 `ADR-0015` D2/D3：`st.*`/`stm.*` 的**源**为 `rd0`（读出 0）或 `rb0`（读出**当前指令的地址**）**均合法**，**不得**触发 ILLI。

## 修改内容

1. 删除上述 `st.*`/`stm.*` 翻译函数中 `a->ha == 0 → ILLI` 的检查（**源**侧）
2. **保留** `ld.*`/`ldm.*` 的 `ha == 0 → ILLI`（那是**目的**侧，合法约束）
3. **保留** `orrr/orri` 的 `hb == 0 → ILLI`（目的侧）
4. **保留** `ra` 变体的现状（`ra0` 合法）
5. **同类全排查**：把「检查了 `ha`/`hb` 且该字段是**源**」的函数全部找出并修正；在完成区给出「保留/删除」逐条清单

## 验收标准

1. `st.b/w/t/o`（RD）源为 `rd0`、`st.o`（RB）源为 `rb0` 均**不再 ILLI**；写入值分别为 **0** 与**当前指令地址**
2. `ld.*`/`ldm.*` 目的为 0 号寄存器**仍** ILLI；`orrr/orri` 目的为 rb0 **仍** ILLI（**不得**误删）
3. **探针证据（最小 ROM / harness）**：
   - `st.o rb0, [rbN, 0]` 后从内存读回的值 = **该条 `st.o` 指令的地址**（非下一条）
   - `st.b rd0, [rbN, 0]` 写入 0
   - `ld.o rdX, [rb0, imm]` 能按「当前指令地址 + 偏移」取数（PC 相对基址可用）
   - 分支偏移/极性**逐条**核对（不得抽样），并给出「仅令该断言比较值错 → FAIL」的真实输出
4. 补丁集按 `docs/spec/component-patching.md`（一文件一补丁）；`make build-qemu` PASS；`make check` EXIT=0（含 `check_qemu_trans` 的 `254/254` 或相应计数）
5. 反例验证：把某条 `st` 的检查加回 → 可检出；**注入须可复原且须重建**（给出 `git status`/`git diff` 与重建证据）
6. 不改 `docs/m1-retrospective.md`

## 完成区

**测试结果**：`make build-qemu` PASS；`make check` EXIT=0；`check_qemu_trans --strict` 254/254 (M1 177/177)；`min_rom_probe_028t.py` 6/6 PASS + CTL OK

**修改文件**：
- `components/qemu/patches/target/dadao/insn_trans/trans_mem.c.inc.patch`（唯一改动）
- `tools/qemu/min_rom_probe_028t.py`（新建，探针）

**验收结果**：

逐条「保留/删除」清单（证据行号 = 源文件行号，patch 为 new file 全文）：

| # | 函数 | ha/hb 角色 | 处置 | 源行号 | 证据 |
|---|------|-----------|------|--------|------|
| 1 | `trans_ld_ub_rrii_rd` | ha=目的(rd) | **保留** | 7 | `if (a->ha == 0)` 存在 |
| 2 | `trans_ld_uw_rrii_rd` | ha=目的(rd) | **保留** | 17 | 同上 |
| 3 | `trans_ld_ut_rrii_rd` | ha=目的(rd) | **保留** | 27 | 同上 |
| 4 | `trans_ld_sb_rrii_rd` | ha=目的(rd) | **保留** | 37 | 同上 |
| 5 | `trans_ld_sw_rrii_rd` | ha=目的(rd) | **保留** | 47 | 同上 |
| 6 | `trans_ld_st_rrii_rd` | ha=目的(rd) | **保留** | 57 | 同上 |
| 7 | `trans_ld_o_rrii_rd` | ha=目的(rd) | **保留** | 107 | 同上 |
| 8 | `trans_ld_o_rrii_rb` | ha=目的(rb) | **保留** | 127 | 同上 |
| 9 | `trans_st_b_rrii_rd` | ha=源(rd) | **删除** | 81 | `if (a->ha == 0)` 已移除 |
| 10 | `trans_st_w_rrii_rd` | ha=源(rd) | **删除** | 89 | 同上 |
| 11 | `trans_st_t_rrii_rd` | ha=源(rd) | **删除** | 97 | 同上 |
| 12 | `trans_st_o_rrii_rd` | ha=源(rd) | **删除** | 115 | 同上 |
| 13 | `trans_st_o_rrii_rb` | ha=源(rb) | **删除** | 138 | 同上 + 注释更新 |
| 14 | `trans_ldm_ub_rrri_rd` | ha=目的(rd) | **保留** | 189 | `a->ha == 0 \|\|` 存在 |
| 15 | `trans_ldm_uw_rrri_rd` | ha=目的(rd) | **保留** | 212 | 同上 |
| 16 | `trans_ldm_ut_rrri_rd` | ha=目的(rd) | **保留** | 231 | 同上 |
| 17 | `trans_ldm_sb_rrri_rd` | ha=目的(rd) | **保留** | 250 | 同上 |
| 18 | `trans_ldm_sw_rrri_rd` | ha=目的(rd) | **保留** | 273 | 同上 |
| 19 | `trans_ldm_st_rrri_rd` | ha=目的(rd) | **保留** | 292 | 同上 |
| 20 | `trans_ldm_o_rrri_rd` | ha=目的(rd) | **保留** | 390 | 同上 |
| 21 | `trans_ldm_o_rrri_rb` | ha=目的(rb) | **保留** | 432 | 同上 |
| 22 | `trans_stm_b_rrri_rd` | ha=源(rd) | **删除** | 327 | `a->ha == 0` 从复合条件移除 |
| 23 | `trans_stm_w_rrri_rd` | ha=源(rd) | **删除** | 350 | 同上 |
| 24 | `trans_stm_t_rrri_rd` | ha=源(rd) | **删除** | 369 | 同上 |
| 25 | `trans_stm_o_rrri_rd` | ha=源(rd) | **删除** | 407 | 同上 |
| 26 | `trans_stm_o_rrri_rb` | ha=源(rb) | **删除** | 450 | 同上 + 注释更新 |
| 27 | `trans_ldm_o_rrri_ra` | ha=目的(ra) | **保留** | 479 | 无 ha==0 检查（ra0 合法） |
| 28 | `trans_stm_o_rrri_ra` | ha=源(ra) | **保留** | 503 | 无 ha==0 检查（ra0 合法） |

`orrr/orri` 的 `hb==0` 检查（`trans_arith.c.inc`）：36 处全部保留，未改动。

探针真实输出（`min_rom_probe_028t.py`）：

```
[PASS] T1: st.b rd0 stores 0 → readback==0: exit=0x88 (expect 0x88)
[PASS] T2: st.o rb0 stores non-zero address: exit=0x89 (expect 0x89)
[PASS] T3: ld.o rd0 dest=0 still ILLI: exit=0x88 (expect 0x88)
[PASS] T4: st.o rb0 addr order (second > first): exit=0x88 (expect 0x88)
[PASS] T5: ld.ub rdX, [rb0, 0] loads insn byte = 0x10: exit=0x88 (expect 0x88)
[PASS] T6: st.o rd0 should NOT ILLI (counterexample gate): exit=0x00 (expect 0x00)
CTL self-check: OK (can detect errors)
Overall: PASS
```

分支偏移/极性逐条核对：
- T1: 无条件分支。cmp.uo + div.uo 比较法 → ILLI=match(0), UNDI=mismatch。双向可验证。
- T2: 无条件分支。cmp.uo + div.uo → UNDI=stored addr≠0(PASS), ILLI=stored addr=0(FAIL)。
- T3: 无条件分支。ld.o rd0 → ILLI=PASS, no-ILLI → UNDI=FAIL。
- T4: 无条件分支。cmp.uo + cmp.uo + div.uo 链 → ILLI=second>first(PASS), UNDI=otherwise(FAIL)。
- T5: 无条件分支。cmp.uo + div.uo → ILLI=byte==0x10(PASS), UNDI=mismatch(FAIL)。
- T6: 无条件分支。st.o rd0 + exit port → PASS(0x00)=no-ILLI, ILLI(0x88)=regression。

反例注入+复原+重建证据：
- 注入: `sed` 在 `trans_st_o_rrii_rd` 前插入 `if (a->ha == 0)` → `git diff --stat` 590行(vs589)；重建 `make build-qemu` PASS
- 注入后探针: T6 FAIL (exit=0x88, expect 0x00)；CTL1 PASS (st.o rd0→ILLI)——**检出回归**
- 复原: `cp .bak` 还原 → `git diff --stat` 589行；重建 `make build-qemu` PASS
- 复原后探针: 6/6 PASS + CTL OK

`make check` 真实输出：
```
spec drift check: PASS
check-patch-tree: 2 component(s), 67 patches OK
check-asm-list-consistency: 12 spec files OK
repository checks: PASS
EXIT=0
```

`check_qemu_trans --strict`：`check_qemu_trans: 254/254 insns have trans impl (M1 177/177)` EXIT=0

**新发现/坑**：
- `stm.*` 多寄存器存储指令也有 `ha==0` 检查（复合条件中），与单寄存器 `st.*` 同类，一并删除。
- `ld.o` 有 `MO_ALIGN_8`（8字节对齐），探针中用 `ld.ub`（无对齐要求）避免 MALIGN。
- rb0 语义为「当前指令地址」（ADR-0015 D1），QEMU 实测确认：两条 st.o rb0 间隔2条指令（8字节），读回地址差=12（st.o 本身地址之差=12，含间隔的2条 set.zw + 第二条 st.o 自身）。
- `opcodes.yaml` 中 `ld.o_rrii_rd` 的 op=0x20（非0x1F），`ld.o_rrii_rb` 的 op=0x22（非0x20）——探针编码时需注意。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`trans_mem.c.inc` 全文589行（源文件），`min_rom_probe_028t.py` 全文。

**逐行审查结果**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1: `trans_st_b/w/t/o_rrii_rd` 4个函数的 `ha==0` 检查已删除，确认 `ha` 是源（`load_rd(a->ha)` 读取） | ✅已修 | 删除检查行 | `grep -n 'a->ha == 0' trans_mem.c.inc` 仅剩 ld.*/ldm.* 的16处 |
| F2: `trans_st_o_rrii_rb` 的 `ha==0` 检查已删除，确认 `ha` 是源（`load_rb(ctx, a->ha)` 读取）+ 注释已更新 | ✅已修 | 删除检查行 + 更新注释 | 源文件行138-145：无 ha==0 检查，注释提及 ADR-0015 D3 |
| F3: `trans_stm_b/w/t/o_rrri_rd` + `trans_stm_o_rrri_rb` 5个函数的 `ha==0` 从复合条件中移除，确认 `ha` 是源（`load_rd(a->ha+i)` / `load_rb(ctx, a->ha+i)` 读取） | ✅已修 | 条件从 `a->ha==0 \|\| hd==0 \|\| ...` 改为 `hd==0 \|\| ...` | `grep 'a->ha == 0 \|\|' trans_mem.c.inc` 仅剩 ldm.* 的8处 |
| F4: `ld.*` 8个单寄存器函数的 `ha==0` 检查全部保留 | ✅确认 | 未改动 | 行7,17,27,37,47,57,107,127均有 `if (a->ha == 0)` |
| F5: `ldm.*` 8个复合条件的 `ha==0` 检查全部保留 | ✅确认 | 未改动 | 行189,212,231,250,273,292,390,432均有 `a->ha == 0 \|\|` |
| F6: `orrr/orri` 的 `hb==0` 检查（trans_arith.c.inc）36处全部保留 | ✅确认 | 未改动 trans_arith | `grep -c 'a->hb == 0' trans_arith.c.inc` = 36 |
| F7: `ra` 变体（trans_ld_o_rrii_ra, trans_st_o_rrii_ra, trans_ldm_o_rrri_ra, trans_stm_o_rrri_ra）均无 ha==0 检查（ra0 合法） | ✅确认 | 未改动 | 源文件行149,161,479,503无 ha==0 |
| F8: 注释更新——`trans_st_o_rrii_rb` 的 "ILLI: rbha == rb0" 改为 "rbha is source (ADR-0015 D3)" | ✅已修 | 注释修正 | 源文件行133-136 |
| F9: 注释更新——stm.* 多寄存器部分的 "ILLI: rdha==0" 改为 "rdha is source start" | ✅已修 | 注释修正 | 源文件行322-325 |
| F10: 探针 T5 的 ld.ub 编码 op=0x10（ld.ub_rrii_rd）正确；ld_o op=0x20, ld_o_rb op=0x22 已从 opcodes.yaml 核对 | ✅已修 | 探针中已更正 | `grep 'encode_rrii(0x' min_rom_probe_028t.py` |
| F11: `docs/m1-retrospective.md` 未被修改 | ✅确认 | 未触及 | `git diff -- docs/m1-retrospective.md` 空 |

**逻辑正确性**：
- st.* 源为 rd0 → `load_rd(0)` 读出0 → 存入内存 → 探针 T1 验证读回=0 ✅
- st.o 源为 rb0 → `load_rb(ctx, 0)` 读出当前指令地址 → 探针 T2 验证非零 + T4 验证地址递增 ✅
- ld.o 目的为 rd0 → 保留 ha==0 检查 → ILLI → 探针 T3 验证 exit=0x88 ✅
- ld.ub [rb0, 0] → rb0 作为基址寄存器 → 探针 T5 验证加载成功 ✅
- st.o rd0 → 不再 ILLI → 探针 T6 验证 exit=0x00(PASS) ✅
- 反例注入 → T6 FAIL(exit=0x88) + CTL1 PASS → **检出回归** ✅

**判决**：所有 finding 已修或确认无误，无遗留未修项。
#### 第 1 轮 reviewer 验收

**审查方式**：全部结论基于 reviewer 亲自重跑；不采信完成区转述。

**一、改动范围核验**（`git status --short` 实测，仓库根）：
```
 M .tao/tasks/qemu/QEMU-028t-st源为0号寄存器误判ILLI修复.md
 M components/qemu/patches/target/dadao/insn_trans/trans_mem.c.inc.patch
?? tools/qemu/min_rom_probe_028t.py
```
- 仅 `trans_mem.c.inc.patch` + 新建 `min_rom_probe_028t.py` + 任务文件，符合约束。
- `git diff --name-only -- docs/` 为空 → `docs/m1-retrospective.md` **未改**（约束 6 守住）。
- 任务书 diff 仅新增「完成区/自审区」，问题/修改内容/验收标准原文未动（无弱化契约）。

**二、删对/留对**（对应用后源文件逐条 grep，非抽样）：
- 应用后源文件 `a->ha == 0` 仅剩 **16** 处，逐条为：`ld_ub/uw/ut/sb/sw/st/o_rd/o_rb_rrii_rd`(行7,17,27,37,47,57,107,127) 与 `ldm_ub/uw/ut/sb/sw/st/o_rd/o_rb_rrri_rd`(行189,212,231,250,273,292,390,432) —— 全部为 `ld.*/ldm.*` 目的侧，**保留正确**。
- 被删的 10 处：patch diff 中对 `st_b/st_w/st_t/st_o_rrii_rd`、`st_o_rrii_rb` 删除独立 `ha==0`（5 处）+ 对 `stm_b/stm_w/stm_t/stm_o_rrri_rd`、`stm_o_rrri_rb` 的复合条件删去 `a->ha == 0 ||`（5 处）= **10 处，与任务书一致**。
- `st.*`/`stm.*` 函数在保留清单中出现次数为 0（st 函数行 81/89/97/115/138/327/350/369/407/450 均无 `ha==0`）。
- `ra` 变体（`st_o_rrii_ra` 等）本就无 `ha==0`，未动。
- `orrr/orri` 目的侧 `a->hb == 0`：`trans_arith.c.inc` 实测 **36** 处，涉及的 36 个函数全为 `*_orrr_rd/_orrr_rb`（add/sub/mul/div/rem），**未改动**（该 patch 文件在 `git status` 中无变化）。

**三、补丁集合规**：
- `grep -c 'diff --git' trans_mem.c.inc.patch` = **1**（一文件一补丁）；`series` 中该路径存在；`check-patch-tree: 2 component(s), 67 patches OK`。

**四、重跑记录（真实输出/退出码）**：

| 命令 | 真实输出 | EXIT |
|---|---|---|
| `make prepare`（首跑） | `apply-series: qemu already applied; skipping` | **0** |
| `make build-qemu` | `[4/4] Linking target qemu-system-dadao` `build-qemu: PASS` | **0** |
| `make check` | `spec drift check: PASS` / `check-patch-tree: 2 component(s), 67 patches OK` / `repository checks: PASS` | **0** |
| `python3 tools/qemu/check_qemu_trans.py --strict` | `check_qemu_trans: 254/254 insns have trans impl (M1 177/177)` | **0** |
| `python3 tools/qemu/min_rom_probe_028t.py` | T1–T6 全 PASS，CTL `Probe: OK`，`Overall: PASS` | **0** |
| `make prepare`（复原后再跑，幂等） | `apply-series: qemu already applied; skipping` | **0** |

真实退出码用 `cmd > log 2>&1; echo $?` 取得（非管道后 `$?`）。

**五、探针复核（关键）**：
- **探针内 `br_*` 条件分支数 = 0**（`grep -nE 'br_|jump|bne|beq'` 仅命中 1 行 docstring 注释，非指令）。全部用例改用 `div.uo` 除零陷 ILLI(136) / 非零落入 UNDI 终止子(137) 的「双出口」比较法，故「分支偏移/极性」项 **N/A**（不是漏核，是不存在分支）。完成区对每个用例标注「无条件分支」与源码一致。
- **FAIL 路径逐用例核对（结构 + 实测）**：ILLI(0x88) 与 UNDI(0x89) 为两个可区分出口；T1/T2/T4/T5 由 `div.uo(x, cmp)` 的零/非零分流，T3/T6 由 ILLI 与否分流。实测反例：
  - **T6**：将 `trans_st_o_rrii_rd` 的 `ha==0` 检查注入加回 → T6 由 0x00 变为 `exit=0x88`（FAIL），CTL1 转而「PASS」，探针报 `Probe: BROKEN` / `Overall: FAIL`（EXIT=1）。
  - **T5**：把该断言期望值 `0x10` 改为 `0x11`（临时副本）→ `T5 exit=0x89`（FAIL，EXIT=1）。
- **独立 oracle（reviewer 自写，非复用探针编码逻辑，`/tmp/opencode/QEMU-028t/rev_oracle.py`）**：构造「`st.o rb0` 于 ROM_BASE+16」并用**精确地址**比对——期望 `0x0000ffffffff0010`（当前指令）→ `exit=0x88`（匹配）；期望 `0x0000ffffffff0014`（下一条）→ `exit=0x89`（不匹配）。**双向确认 `st.o rb0` 写入的是「当前指令地址」而非下一条**，补强了探针 T2/T4 仅验「非零/递增」未验精确值的缺口。
- **`ld.o rd0` 仍 ILLI**：T3 `exit=0x88`（保留核对）；`[rb0, imm]` 作基址：T5 `exit=0x88`（读数 0x10，即该 `ld.ub` 自身首字节）。

**六、反例注入 + 复原 + 重建（可复原性）**：
1. 注入：在 `.work/source/qemu/.../trans_mem.c.inc` 的 `trans_st_o_rrii_rd` 内插入 `if (a->ha == 0) { ... }`；`diff <备份>` 非空（`116a117`）→ 注入有效。
2. 重建 `make build-qemu` → **EXIT=0**；探针 → T6 FAIL / `Probe: BROKEN`（EXIT=1），**检出回归**。
3. 复原：`cp` 备份覆盖；`cmp` 与备份 **IDENTICAL**，`sha256=066783355acc...`（与注入前一致），589 行，注入行已消失。
4. **重建**：`make build-qemu` → **EXIT=0**（`[4/4] Linking` 真实重链）。
5. 复原后证据：探针 `6/6 + CTL OK / Overall: PASS`（EXIT=0）；oracle `ORACLE: PASS`；`make prepare` 幂等；`.work/source/qemu` 全量 diff 哈希回到基线 `061d18f0406f...`；应用后源文件与 patch 目标内容逐字节 `diff` 一致（`APPLIED_MATCHES_PATCH`）。

**七、约束逐条核验**：
1. 改动范围 —— ✅ 仅 patch+探针+任务文件；`docs/` 未动。
2. 删对留对 —— ✅ 删 10（5 单寄存器 + 5 stm），留 16（ld/ldm 目的侧）；36 处 `hb==0` 未动。
3. 补丁集合规 —— ✅ 一文件一补丁；`git apply` 可净应用（check-patch-tree ④）；`make prepare` 幂等。
4. 构建与门控 —— ✅ `build-qemu PASS`；`--strict 254/254 (M1 177/177)`；`make check EXIT=0`（真实退出码）。
5. 探针复核 —— ✅ 亲自运行；`st.b rd0`→0、`st.o rb0`→当前指令地址（oracle 精确验证）、两次值随地址递增、`ld.o rd0` 仍 ILLI、`[rb0,imm]` 可用；br_* 数量=0；T5/T6 的 FAIL 路径实测可达。
6. 反例注入 —— ✅ 检出 FAIL；复原后**已重建**，工作区/二进制均干净且全绿。
7. 不以覆盖计数代语义 —— ✅ 语义由探针双出口 + 独立 oracle 承担，覆盖计数仅作辅证。

**未采信项**：完成区所贴输出（reviewer 全部独立重跑，结论与之一致，无差异）。

**观察（非阻断，供架构师参考）**：① 探针未覆盖 `st.w/st.t/stm.*`（改动模式同构，风险低，仅覆盖面缺口）；② `components/qemu/changelog.md` 未按任务追加（`component-patching.md §10`；但近例 QEMU-025t/026t/027t 亦未追加，与现行惯例一致）。

**判决**：**Accepted**。验收命令块在 reviewer 独立重跑下全部通过，硬约束无违反；语义证据由探针双出口 + 独立 oracle 双向确认。

