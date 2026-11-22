# IDL 与 UDB 的差异盘点（结论索引）

> **性质**：`m15-idl-020 IDL 差异盘点` 的**结论汇总**（只读分析的产出），**不是实现判据**——判据在 `spec/` 与 `.tao/contracts/`。逐条原文（两侧引用 + 分类 + 优先级）在本任务书「盘点结论」段（`.tao/tasks/idl/m15-idl-020-IDL差异盘点.md`）。
> **对照物**：`riscv-unified-db`（UDB，`manifests/reference-snapshots.toml` 锁 tarball 快照）的 ISA Description Language 与 `spec/std/isa/isa/*.idl`；另以三执行机（QEMU / gem5 / RTL）交叉核对「实现是否忠实于 IDL」。
> **规模**：263 条 operation 逐条判定 —— **一致 100 / 偏离 68 / 特有 95**；`idl/lib/fp.idl` DADAO 108 函数 vs UDB 60（移植 49、未移植 11、新增 59）。
> **整改权**：由用户逐项决定；D1/D2 已立 `m15-idl-021`，D3 已按平台拆三件（`m15-qemu-002`/`m15-gem5-002`/`m16-chipyard-014`）。

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
