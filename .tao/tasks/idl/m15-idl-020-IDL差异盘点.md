# m15-idl-020: IDL 差异盘点（对照 `riscv-unified-db` + 三执行机交叉）

**模块**：idl
**项目里程碑**：M15
**依赖**：无（**只读分析**：不改 `.idl`，可与在跑任务并行）
**可并行分片**：是
**预估**：3–4 h
**档位**：小改（只读 + 写结论）
**状态**：待验收

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

## 盘点结论

**口径**（全部现场派生；断言脚本 `run.sh`、逐条映射 `mapping.tsv` 在运行期证据目录）
- operation：263（IDL `^# id:` 条数 = `contracts/opcodes.yaml` 的 `^- id:` 条数；两集合相等由脚本断言，不按 IDL 自证）
- fp.idl 函数：DADAO 108 / UDB 60；移植 49（改名 13）/ 未移植 11 / DADAO 新增 59
- 执行机：三侧补丁共 24+91+16=131 个文件；按家族抽 10 条（QEMU 6 / gem5 2 / RTL 2，去重 10 个文件）
- 对照物：UDB 快照 `176fc36…`（`manifests/reference-snapshots.toml`）
- 枚举命令：`cat idl/SimRISC-*.idl | grep -c '^# id: '`、`grep -c '^- id: ' contracts/opcodes.yaml`、`grep -cE '^(builtin )?function [A-Za-z_0-9]+\?? \{' idl/lib/fp.idl`（UDB 侧同式）、`find components/{qemu/patches/target/dadao,gem5/patches/src/arch/dadao,chipyard/patches/generators/dadao-wuming} -type f | wc -l`

**1. operation 分类（合计 263：一致 100 / 偏离 68 / 特有 95）**
- 全局口径：DADAO **大端**、无 NaN-boxing（ft 只写低 32 位）；UDB 小端、flw/fadd 等对高半 NaN-box。属内存/寄存器模型差异，按条只单列 `ld.t`，其余不重复计。
- 一致 100（SimRISC-01:13、04:16、05:5、06:12、07:42、08:12）；寄存器组/宽度换名不计偏离。D2 的 8 条 rf 访存在 UDB 侧无对齐对照，故不改变本表分类。
- 偏离 68（UDB 有对应、语义不同；每条均有 spec 依据，**无「无依据」项**）：
  - `cmp.*` 三值 −1/0/+1（7；SimRISC-04 §1.3、SimRISC-08 §1.2）P1
  - `add/sub` 双目的进位·借位（4）、`mul` 双目的 128 位积（2）、`clmul.o`（1）（SimRISC-04 §1.1/§1.4/§1.5）P1
  - `andn.w`/`or.w` 只改选中 wyde（4；SimRISC-03 §1/§2）P2
  - `rol` 立即数（2）、`ext.*` 任意位段（4）、`rev.o`/`rev.t` 通用块反转（2）（SimRISC-04 §2.2/§2.2.1）P2
  - `call`/`ret` 经 RAS 压/弹栈（3；SimRISC-00 §2.4.1/§2.4.2）P2
  - `ld.t`/`ld.o` 的 rf 写宽/写掩码（2；SimRISC-00 §2.3/§2.3.1，UDB `flw` NaN-box、`fld` 写全寄存器）P2
  - ft/fo 四比较三值 + 无序返回 canonical qNaN（4；SimRISC-07 §4）P1
  - 32 位零扩展变体 `add/sub/mul/div/rem.ut`（5；SimRISC-08 §1）P2
  - `lr`/`sc` 8/16/32/64 位 + 窄读保留高位 + an/ar（24；SimRISC-12 §1.1/§1.2）P1
  - `ctlz`/`cttz`/`ctpop` 以 hd 为上界（3；SimRISC-12 §3）P1
  - `swym` 对 UDB `pause`（1；SimRISC-12 §2）P2
- 特有 95（UDB 无对应）：
  - `ldm`/`stm` 19（rd 11、rb 4、ra 4）+ rf 组 4
  - `cs.*` 8、跨组/块搬移 9、`set.ow`/`set.w`/`set.zw` 4
  - `ftrem`/`ftsclb`/`forem`/`fosclb` 4（RISC-V 无 remainder/scaleB）
  - 16 位 ALU 21、8 位 ALU 21（RISC-V 无窄位宽 ALU）
  - cfx 5（`trap`/`escape`/`cfx2rd`/`cfx2rc`/`fence`）

**2. fp.idl 对照**
- 同名 36：33 条语义等同（含签名逐字相同 15；其余仅 `U32`→`Bits<32>` 别名/注释）+ 3 条改口径（下条）
- 改名 13（`f32_*`→`ft_*`、`round_f32_to_integral`→`round_ft_to_integral`、两条 `*_no_flag`）
- 未移植 11：`mark_f_state_dirty`/`nan_box`/`check_f_ok`、F16 两条、`approxRecipSqrt32_1`、f32↔i64/u64 四条（改在 `ft2io`/`ft2uo`/`io2ft`/`ut2ft` operation 内联）、`shiftRightJam64Extra`（内联）
- 新增 59：fo/binary64 族 45（UDB 0 个 f64 函数）+ ft 侧补齐 14（`ft_clz32/64`、`ft_isqrt64`、`ft_scale`、`ft_rem`、i32/ui32→fo、i64/ui64→fo、no_flag 舍入）
- 口径改变（同名但语义变）：`RoundingMode` 以 RNA 取代 RMM、无 DYN（SimRISC-07 §1.1）；`rm_to_mode` 改 6 位 one-hot + `rf0[33:32]`；`set_fp_flag` 写 `rf0[4:0]`；tininess 改「舍入后」；`ft_sqrt` 用精确整数开方；5 处 UDB 转写 bug 未照抄；新增 remainder/scaleB

**3. 执行机一致性（10 条对照 / 8 个 operation + 补查）**
- 7 个一致：`cmp.ut`、`rev.t`、`ctlz`、`ftmin`、`ldm.o`、`ftsclb`、`div.sb`（jump 的 RTL/gem5 目标计算亦一致）。
- 补查发现 3 项分歧（按家族看边界/异常路径；D1/D2 = **IDL 缺陷**，D3 = **实现偏离 IDL**）：
  - **D1**（P1，**应改 IDL**）：`jump`/`br.*` 的 rb0 写回宽度。IDL `jump()` 只写 `target[47:0]`（并称 IP 高 16 位恒 0）；QEMU/RTL/gem5 与 spec 散文（SimRISC-06 §1/§2、ADR-0012 D8.3/D8.4）均写**完整 64 位**、取低 48 位取指。修 `jump`/`ip()` 模型 + 15 条控制流与 `aip.si` 注释。
  - **D2**（P1，**应改 IDL**）：8 条 rf 访存（`ld`/`st`/`ldm`/`stm` × `.t`/`.o` 的 `_rf` 形式）缺 MALIGN 判定。`SimRISC-01 §4` 正文要求 `.t` 4 字节、`.o` 8 字节对齐；附录 B `excp_malign` 现 32 条、**含全部 8 条 rf 形式**，`contracts/opcodes.yaml` 对应 `legality: [aligned(4/8)]` + `rule_refs: [excp_malign]`（用户 2026-11-19 裁定，master `af7ffb09`；`m15-idl-001` R2）；三执行机亦判 MALIGN（QEMU `MO_ALIGN_4/8`、gem5 width>1、RTL `memAlignFail`）。IDL 的「附录 B 未列本族」注释前提已过期 ⇒ 补 `is_naturally_aligned` + `Malign` 并订正注释（注释订正同属本条）。
  - **D3**（P1，**应改执行机**）：窄 `lr`（`.t/.w/.b`×3 序，9 条）只写低 W 位、高位保持。IDL 按用户 2026-11-19 裁定（`m15-idl-012` R2）切片写；QEMU/gem5/RTL 仍整 64 位零扩展（QEMU 注释仍引 `LLVM-121t` 旧口径）。`MEMORY.md`「窄读不改高位」已登记实现侧待修。

**4. 抽查原文（IDL ↔ UDB，5 对）**
- `SimRISC-08.idl:49` `cmp.ut`：`if (a < b) rd[rdHB] = {64{1'b1}}` ↔ `inst/I/sltu.yaml:36` `X[xd] = (X[xs1] < X[xs2]) ? 1 : 0;`（0/1 → −1/0/+1）
- `SimRISC-04.idl:130` `mul.so`：128 位积写 rdHA（高）/rdHB（低）↔ `inst/M/mul.yaml:46` 取低半 + `inst/M/mulh.yaml:50` 取高半（UDB 拆两条）
- `SimRISC-07.idl:941` `ftmin`：单 NaN 返回另一数、双 NaN canonical、sNaN 置 NV ↔ `inst/F/fmin.s.yaml:44–72` 同规则（一致）
- `SimRISC-06.idl:75` `jump_iiii`：`jump(ip() + $signed(scaled));` ↔ `inst/I/jal.yaml:37–40` `X[xd] = return_addr; jump_halfword($pc + $signed(imm));`（一致；rb0 宽度见 D1）
- `SimRISC-12.idl:227` `ctlz`：`hd = immu6` 为有效位上界、全 0 返回 hd+1 ↔ `inst/Zbb/clz.yaml:32` 全 64 位前导零（UDB 无 hd 上界）
（`ldm.o` 无 UDB 对应文件，按 DADAO 特有记账。）

**5. 待办**
- **P1**：立任务修 IDL 缺陷 D1（`jump` 写 64 位、`ip()` 读 64 位），同步 `idl/README` §2/§4.3 与相关注释；本任务只读、未改 `.idl`。
- **P1**：立任务修 IDL 缺陷 D2（8 条 rf 访存补 `is_naturally_aligned` + `Malign`，按 `.t`=4/`.o`=8 字节；订正「附录 B 未列本族」过期注释）；依据已由 `af7ffb09`/`m15-idl-001` R2 落定，**无需再裁定**。
- **P1**：三执行机窄 `lr` 按 `m15-idl-012` R2 改切片写（D3；已登记，另立执行机任务）。
- **P2**：非一致项共 163（P1 45 / P2 118：偏离项的形态差 + 特有项的差异说明），已在 `mapping.tsv` 逐条给出 UDB 符号与依据；需要生成对照表时可直接消费，本任务不落地。

## 审阅记录

### 第 1 轮 engineer 自审

审查对象：本任务结论、`mapping.py`、`run.sh`。逐项自审：
- 计数是否自证：`run.sh` C1 用 `contracts/opcodes.yaml` 做独立集合断言，非按 IDL 自数；C4 断言分类和 = 条数；C4' 断言 fp 两侧加和守恒。✅
- 映射是否可失败：删一条 `rule(...)` ⇒ `classify` 断言「0 条规则命中」非零；重复 id ⇒ 集合断言非零（C6/C7 实测 rc=1）。✅
- 抽样是否真引原文：C5 逐条 `sed -n` 取 IDL 行、grep 取执行机行，期望/实际逐字比对；`--inject` 改坏一条期望 ⇒ rc=1。✅
- 结论与脚本是否对齐：`一致 100/偏离 68/特有 95`、`108/60/49/11/59` 均取脚本输出，未手写估算。✅
- 分类边界：`ldm/stm` 与 Zcmp `cm.push/pop` 形似但语义不同（固定栈帧 vs 连续区间），记「特有」并在依据写明；32 位零扩展变体核心算术 UDB 有（W 类），只差扩展约定 ⇒ 记「偏离 P2」不记「特有」。✅
- **复核发现并修正**：`ld.t`/`ld.o` 初判「一致」；对照 UDB `flw` 会 NaN-box 高半、`fld` 写全寄存器，而 DADAO rf 写宽/写掩码不同（`ld.o` 到 rf0 只写 FCSR 可写位）⇒ 已改判「偏离 P2」（依据 SimRISC-00 §2.3/§2.3.1），计数同步为 100/68/95。
- 路径合规：结论只写 `.cache/refs/...` 与「运行期证据目录」，无运行期目录的具体路径。✅
判决：finding 全部处置；状态置 `待验收`。

### 第 1 轮 reviewer 验收（小改档）

**重跑**（均在任务 worktree 仓库根；证据脚本 = 运行期证据目录内的 `run.sh`）
- `run.sh` → `ALL PASS`，exit=0（28 项；现场 `operation=263`、`一致=100，偏离=68，特有=95`、`fp DADAO=108 UDB=60`、`49+11=60 / 49+59=108`）
- `run.sh --inject` → exit=1（反例被检出）
- **独立注入 1 路**（`cp` 备份 + md5，未用 git checkout）：把 QEMU `components/qemu/patches/target/dadao/translate.c.patch` 的 `store_rd(a->hc, val)` 改坏 → 重跑 `FAIL C5b D3 QEMU lr 整 64 位写`、exit=1；`cp` 还原后 md5=`6f51734b221533e50d8aba2795b9a782` 相等 → 重跑 `ALL PASS` exit=0；`git status --porcelain -uall` 空
- 门控：`make check-knowledge-refs` → PASS exit=0；`make check-tasks` → exit=0（报告型，①1 条=本任务待验收）；`python3 idl/render.py --check` → PASS exit=0（263 条逐字节一致，`.idl` 未动）

**抽查 10 条**（一致/偏离/特有 = 3/3/4，两侧 `sed -n`/`grep` 原文）
- 一致：`st.t_rrii_rf`（IDL `write_memory(32, ea, rf[rfHA])` ↔ UDB `inst/F/fsw.yaml:39 write_memory(32, …, F[fs2][31:0])`）；`shr.so`（`$signed(rd[rdHC]) >>> rd[rdHD][5:0]` ↔ `inst/I/sra.yaml:33`）；`br.eq`（`rd[rdHA]==rd[rdHB]` ↔ `inst/I/beq.yaml:42`）
- 偏离：`cmp.ui`（−1/0/+1 ↔ `inst/I/sltiu.yaml:42 …? 1 : 0`）；`lr.w.an`（`rd[rdHC][15:0]=value[15:0]` ↔ `inst/Zalrsc/lr.w.yaml:100 sext(…,32)`）；`ftqcmp`（三值+canonical qNaN ↔ `inst/F/feq.s.yaml:44`）
- 特有：`forem`/`rd2ra`/`cs.p`/`ldm.o` → UDB 侧词计数全 0。**10/10 对得上。**

**计数抽验（自有口径）**：`grep -c '^# id: '` = 263 = `grep -c '^- id: ' contracts/opcodes.yaml`；`fp.idl` 108 / UDB 60；同名 36、UDB 独有 24、DADAO 独有 72 ⇒ 移植 49=36+13 改名、未移植 11=24−13、新增 59=72−13；`mapping.tsv` 现场 100+68+95=263。与报数一致。

**D1 成立**：IDL `jump()` body `rb[6'd0] = target[47:0]`、`ip()` 描述「高 16 位恒 0」；`spec/SimRISC-06 §1`「计算结果（64 位）写回 `rb0`，随后取 `rb0[47:0]`」+ §2 各式；`ADR-0012 D8.3/D8.4`（Accepted、用户逐条确认）明写「`rb0[63:48]` 恒为 0」作废；QEMU `tcg_gen_st_i64(target, …, rb[0])`、gem5 `branchTo(uint64_t target64)` + b5.hh「written to rb0 over all 64 bits」、RTL `jumpTarget=(…)(63,0)`→`finish(jumpTarget)`、取指 `ip(addrBits-1,3)`。⇒ 「该改 IDL」方向成立。

**D3 成立**：9 条窄 `lr` IDL 切片写（`rd[rdHC][31:0]/[15:0]/[7:0]`）；QEMU `store_rd(a->hc, val)`、gem5 `executeLr`→`writeInt(Bank::Rd, rd, value)`（`beToHost` 零扩展）、RTL `memSignedLat:=false.B // lr zero-extends` + `extractElem` zx ⇒ 三侧整 64 位；`MEMORY.md`「窄读不改高位（用户 2026-11-19，`m15-idl-012` R2）」与该任务 R2「实现侧需据此修正」均在。⇒ 「应改执行机」成立。

**D2 不成立（阻断）**：任务书写「附录 B 未列 ⇒ 按附录 B 改执行机 ⇒ 需先裁定 spec」，但 `spec/SimRISC-01` **附录 B `excp_malign` 现 32 条、含全部 8 条 rf 形式**（`ld.t_rrii_rf`/`st.t_rrii_rf`/`ldm.t_rrri_rf`/`stm.t_rrri_rf`…），来源 master `af7ffb09`「用户 2026-11-19 裁定：8 条 rf 补 `aligned(4/8)` + `rule_refs:[excp_malign]`、重生成附录 B」；`contracts/opcodes.yaml` 的 `ld.t_rrii_rf` = `legality:[aligned(4)]` + `rule_refs:[excp_malign]`；`check-legality-drift` rc=0（附录 B 与合同逐字节一致）；`m15-idl-001` R2 已记录该裁定。⇒ §4 正文 / 附录 B / 合同**三方一致要求 MALIGN，无 spec 冲突、无需再裁定**；真实分歧仅「IDL 不判（注释前提已过期）vs 三执行机判（QEMU `MO_ALIGN_4`、gem5 `width>1`→`Fault::Malign`、RTL `memAlignFail`→MALIGN）」⇒ 方向应为**改 IDL**。附注：① `run.sh` 对「附录 B」0 断言，绿灯不覆盖该结论；② `m15-idl-001` 自审称「8 条 rf 已加对齐守卫、旧注释已删」与盘上不符（该文件全史仅 2 次提交、§4 无守卫），供架构师核。

**口径与范围**：`git show --name-only HEAD` 仅本任务书；`git diff --name-only 06066c59 HEAD` 仅本任务书（派单提交按设计含三份只读盘点任务书）；`git status -uall` 空、未改 `.idl`/源码；`aip.si` 注释确含「`ip()` 为 64 位、高 16 位恒 0」。

**判决：Needs Revision** —— 仅 D2：把「盘点结论 §3 D2」「完成区新发现②」「遗留问题」改为「IDL 缺陷、应改 IDL（依据 §4 正文 + 附录 B 32 条 + 合同 `aligned(4)`；裁定已在 `af7ffb09` / `m15-idl-001` R2）」，删「按附录 B ⇒ 改执行机」「需 spec 裁定」两处；建议 `run.sh` 补一条「附录 B 含 8 条 rf 形式」断言。D1/D3/计数/抽查/门控均通过。

### 第 2 轮 reviewer 验收（D2 返工）

**D2 回改 ✅**：§3 D2 改为「应改 IDL（P1）」，依据写全——`SimRISC-01 §4` 正文 4/8 字节、附录 B `excp_malign` **32 条含 8 条 rf**、`contracts/opcodes.yaml` `legality:[aligned(4/8)]`+`rule_refs:[excp_malign]`、裁定 `af7ffb09`/`m15-idl-001` R2、三执行机亦判 MALIGN；§5 待办 P1 写「依据已落定、**无需再裁定**」；完成区新发现③、遗留问题同步。「按附录 B ⇒ 改执行机」「需 spec 裁定」在结论/完成区/遗留三处已删净（仅存于第 1 轮 reviewer 原文与其自审引述，不改）。

**`check_d2.py` ✅（我方 2 路独立注入，均 `cp`+md5）**：
- 附录 B 行内删一条 rf → `appendix_B total=31 rf=7`、`FAIL 附录 B 条数 31 != 32`、`FAIL rf 7 != 8` → **exit=1**；`cp` 还原 md5=`d89e9177…` 相等 → `total=32 rf=8 / OK` → **exit=0**。
- 合同 `ld.t_rrii_rf` 删 `aligned(4)` → `FAIL 合同 ld.t_rrii_rf 缺 aligned(4/8)` → **exit=1**；还原 md5=`c89ea53e…` 相等 → **exit=0**。
- 另核：逐条查 8 条 rf 的 `aligned(4/8)` 与 `rule_refs`、§4 正文两式均在，非恒真。（非阻断小注：`EXPECT_N=32/EXPECT_RF=8` 写死，建议改由合同 `rule_refs` 现场派生，避免日后新增对齐条目误判红。）

**回归 ✅（串行重跑；我首轮并行双跑会互扰，已改串行）**：`run.sh` → **32 PASS / 0 FAIL、ALL PASS、exit=0**；`run.sh --inject` → **exit=1**（反例被检出）；跑后 `git status --porcelain -uall` 空、`spec/SimRISC-01` md5=`d89e9177…`。

**D1/D3 与计数未动 ✅**：`一致=100，偏离=68，特有=95`、`operation=263`、`fp DADAO=108 UDB=60`、`49+11=60 / 49+59=108` 与第 1 轮一致；D1/D3 结论行原文未改；`idl/SimRISC-01.idl` md5=`0c5df887…`（= 第 1 轮）。

**范围与门控 ✅**：`git show --name-only HEAD`、`git diff c491fd46 HEAD`、`git diff 06066c59 HEAD` 均**仅本任务书**；门控 rc：`check-knowledge-refs`=0、`check-tasks`=0、`idl/render.py --check`=0（263 条逐字节一致）、`check-legality-drift`=0（12 章 OK）。

**m15-idl-001 R2 独立判定 = 曾实现后被丢（不是凭空不实陈述）**：
- 已合入及全仓 **669 个悬空提交**里的该文件**均无 §4 守卫**；`git log --all` 全史仅 2 次提交，分支链 `bdc5c171`(批4) → `11136d55`(merge master) → `def353ac`(收审阅记录) 的 md5 **均为 `0c5df887`**，且 `def353ac` 只改任务书、`a336b448` 合入的也是 `0c5df887`；
- 但该任务证据脚本**开跑时**写的 `.md5_before`（2026-11-19 11:19:07）= **`828191b0`** ≠ `0c5df887`，该 md5 **不存在于任何 git 对象**、无 stash、无该分支 reflog；
- 其自报「§4 `rc=0`（Malign 8/8）」与注入B「对齐宽度期望 [32] / 实际 [16]、还原 md5=`828191b0` ⇒ 回绿」**只有盘上存在守卫时才可能产出**：用同一 `check_semantics.py --section 4` 对现树实测 → `Malign 判定: 实际 0 / 附录 B excp_malign∩§4 8`、8 条逐个「缺构造 `is_naturally_aligned(32|64, ea)`」、`RESULT: FAIL（16 处）`、**exit=1**。
- ⇒ **11:19 盘上确有守卫版 `828191b0`，11:25:57 合入提交时已回到无守卫版 `0c5df887`，实现丢在提交之前**；「完成区称已修、合入提交却没修」这一对外事实仍成立。丢失机制（checkout 类还原 / 未暂存即清理）盘上无法证实，**供 architect 定夺补救**（重做 §4 守卫或订正该任务完成区）。

**判决：Accepted** —— D2 回改到位、`check_d2.py` 两路注入可达 FAIL 且还原回绿、回归 32/0、D1/D3/计数未动、四门控 rc=0、未改代码。

### 第 2 轮 engineer 自审（D2 返工）

审查对象：第 1 轮 reviewer 对 D2 的阻断意见 + 本轮回改。
- **reviewer 证据复核**：附录 B `excp_malign` 现场 32 条、rf 8 条；`contracts/opcodes.yaml` 8 条 rf 均含 `aligned(4/8)` 与 `rule_refs: excp_malign`（多行列表形式）；`tools/spec/check_legality_drift.py` → `12 chapters OK` rc=0；`af7ffb09` 提交信息与 `m15-idl-001` R2 裁定一致。✅
- **原判断错因**：只读了 IDL 注释「附录 B 未列」与 §4 正文，未回查**已重生成的附录 B**与合同（`af7ffb09` 在本任务基线之前）。✅ 已改。
- **回改**：§3 D2 改为「IDL 缺陷、应改 IDL」（8 条 rf，P1），依据 = §4 正文 + 附录 B 32/8 + 合同 `aligned(4/8)`/`rule_refs` + 裁定（`af7ffb09`/`m15-idl-001` R2）；删除「按附录 B ⇒ 改执行机」「需 spec 裁定」两处；§5 待办、完成区新发现/遗留同步。
- **注释订正 finding**：IDL 8 条 rf 的「附录 B 未列本族 ⇒ 不判 MALIGN」前提已过期 ⇒ 作为 D2 的一部分（「补守卫 + 订正注释」），不另立 finding。
- **证据补强**：`run.sh` 增 C8（三方一致）与 C9（临时删附录 B 一条 rf ⇒ rc=1；`cp`+md5 还原后回绿），现 **32 项全 PASS**、`--inject` rc=1。
- **处置**：finding（D2）→ ✅已修（结论改写 + 删两处表述 + C8/C9 断言）；复验 = `run.sh` 32 PASS / `run.sh --inject` rc=1 / 附录 B md5 前后一致。D1/D3 结论与计数未动。
判决：唯一 finding 已处置；状态置 `待验收`。

## 完成区

**测试结果**：运行期证据目录内 `run.sh` → `ALL PASS`（32 项断言全 PASS，含 10 条抽样对照、D1×3/D3×4 现场证据、D2 三方一致 C8 与附录 B 注入 C9）；反例 `run.sh --inject` → rc=1（反例被检出）。
**修改文件**：`.tao/tasks/idl/m15-idl-020-IDL差异盘点.md`（仅任务书；无源码/`.idl` 改动）。
**验收结果**：`git diff --name-only HEAD` = 仅本任务书（派单提交 HEAD 按设计同时含三份只读盘点任务书；本任务相对 HEAD 无其它改动）；`git status -uall` 仅本任务书；未改 `.idl`/源码，未重建、未跑仿真（C9 注入会临时删附录 B 一行，随即 `cp`+md5 还原，`git status` 干净）。关键输出：`operation 总数：263`；`一致=100，偏离=68，特有=95`；`fp.idl 函数：DADAO 108，UDB 60；移植 49（改名 13），未移植 11，新增 59`。
**新发现/坑**：① IDL `jump()`/`ip()` 的 48 位模型与 ADR-0012 D8.3/D8.4 + 三执行机矛盾（D1，P1，应改 IDL）；② 三执行机窄 `lr` 仍零扩展，与用户 2026-11-19 裁定相反（D3，P1，应改执行机，已登记待修）；③ 8 条 rf 访存 IDL 缺 MALIGN，且注释「附录 B 未列本族」前提已过期（D2，P1，应改 IDL；依据 = §4 正文 + 附录 B 32 条含 8 条 rf + 合同 `aligned(4/8)`/`rule_refs:[excp_malign]`，裁定在 `af7ffb09`/`m15-idl-001` R2）；④ UDB `fmin/fmax` 即 IEEE `minimumNumber`，与 DADAO 一致，勿误判偏离；⑤ UDB `RMM`≡DADAO `RNA` 规则等价但编码不同（`rf0` 无 RNA 动态档）；⑥ UDB 版本实际记在 `manifests/reference-snapshots.toml`（`references.lock.toml` 无该条），且是 tarball 快照、无 git 历史；⑦ 建议沉淀「UDB 对照口径：operation 以 `contracts/opcodes.yaml` 为独立 oracle；fp 函数以 `^function` 现场计数」。
**遗留问题**：D1/D2 需另立任务修 IDL（D2 = 8 条 rf 对齐守卫 + 过期注释订正；依据已落定，无需再裁定）；D3 需另立执行机任务修三侧窄 `lr`。另：`m15-idl-001` R2 称「§4 已加对齐守卫、旧注释已删」，与盘上不符（`.idl` 全史仅 2 次提交、§4 无守卫），供主会话核（本任务只读）。执行机仅按家族抽 10 条 + 对齐/lr 补查，未做逐条全量；softfloat 逐例语义等价属 m17 执行语义范围，未覆盖。
