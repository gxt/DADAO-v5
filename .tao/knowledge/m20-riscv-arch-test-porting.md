# M20 riscv-arch-test 可移植清单（评估，不写向量）

> 上游取证：只读参考仓 `.cache/refs/riscv-arch-test`（锁 `manifests/references.lock.toml`，head `0a2f8c8b`）；表中「已核」= 已在该仓 `tests/rv64i/**` 见到对应 `.S`，未核名称不写。
> 基线：`tests/inst` **274** 个 `.S`（现场 `find`）；`tests/arch` **39** 条（`tests/arch.yaml` 现场计数）。只移植**测试意图/边界值/判据**，不复制 RISC-V 代码；op 一律按 `contracts/opcodes.yaml` 的 `id`。
> 表中「参考条数」仅用于估算，实际按缺口调整，不作为上限或验收门槛。

## A. 指令相关候选（落 `tests/inst`）

| # | 上游族（已核） | 移植意图 | DADAO op / spec | 现有覆盖 | 建议落点/参考条数（估算，不是上限） |
|---|---|---|---|---|---|
| A1 | `rv64i/I/I-add-00.S` 等 | 进位/借位、极值、源=目的 | `add.so_rrrr_rd`/`add.uo_rrrr_rd`；`SimRISC-04 §1.1` | `04/add.so_rrrr_rd.S` 等；inventory semantic+boundary ✓ | inst 4 |
| A2 | `I-sll-00.S`/`I-sra-00.S`/`I-srl-00.S` | 移位量 0/N、符号/零扩展、越界 ILLI | `shl.o_orrr_rd`/`shr.so_orrr_rd`；`SimRISC-04 §2.2` | `04/shl.o*`、`shr.*`、`ext.*`；boundary ✓ | inst 4 |
| A3 | `I-beq-00.S`/`I-bne-00.S`/`I-blt-00.S` | 前/后向、极距、等值边界 | `br.eq_rrii_rd`/`jump_iiii_rb`；`SimRISC-06 §1/§2` | `06/br.*` 10 + jump/call/ret；boundary ✓ | inst 3 |
| A4 | `rv64i/M/M-div-00.S`/`M-rem-00.S` | 除零、INT_MIN/−1、商余关系、符号 | `div.so_orrr_rd`/`rem.so_orrr_rd`；`SimRISC-04 §1.4` | `04/div.so*` 20 点含两类定值；各宽度 boundary ✓ | inst 5 |
| A5 | `I-lb-00.S`…`I-ld-00.S` | 宽度、符号/零扩展、自然对齐/MALIGN、大端 | `ld.o_rrii_rd`/`ld.ub_rrii_rd`；`SimRISC-01 §1` | `01/ld.*` 各 20+ 点含 MALIGN/CFXMEM；boundary ✓ | inst 5 |
| A6 | `Zbc-clmul-00.S`/`Zbb-clz-00.S`/`Zbb-cpop-00.S`/`Zbb-rol-00.S` | 高/低半、全 0 定值、one-hot k、rev/rol 组合 | `clmul.o_rrrr_rd`/`ctlz_orri_rd`/`rev.o_orri_rd`/`rol.o_orrr_rd`；`SimRISC-04 §1.5/§2.2.1/§2.2.2`、`SimRISC-12 §3` | `04/clmul.o` 21 点、`ctlz/cttz/ctpop` 各 22 点、`rev.*`/`rol.*`；boundary ✓ | inst 6（优先 clmul 高半/`clmulr` 组合） |
| A7 | `Zalrsc-lr.d-00.S`/`Zalrsc-sc.d-00.S` | 成败返回、精确地址+宽度、单 hart 清标记 | `lr.o.nn_orrr_rd`/`sc.o.nn_orrr_rd`；`SimRISC-12 §1.1` | `12-misc/lr.*`/`sc.*` 24 个 id + `00/atomic_rmw.S` 15 点；异常/中断清标记 GAP 见 S3 | inst 4（仅单 hart 值语义） |
| A8 | `rv64i/F/F-fadd.s-00.S`/`F-fdiv.s-00.S`/`F-fmadd.s-00.S` | 单精 NaN/次正规/六档舍入/NX/OF/UF、转换饱和 | `ftadd_orrr_rf`/`ftfma_rrrr_rf`/`ftrnd_orri_rf`/`ftcls_orri_rf`；`SimRISC-07 §1.1/§1.3/§2.1–2.5/§5` | `07/*` 50 个 `.S`，每文件约 20–35 点；boundary ✓ | inst 6（优先转换饱和/NaN 传播） |
| A9 | `rv64i/D/D-fadd.d-00.S`/`D-fdiv.d-00.S`/`D-fmadd.d-00.S` | 双精 FMA 单次舍入、min/max 的 ±0/NaN、溢出方向 | `foadd_orrr_rf`/`fofma_rrrr_rf`/`fomin_orrr_rf`/`fornd_orri_rf`；`SimRISC-07 §2.3/§2.4/§2.5` | `07/fofma` 25 点、`fomin` 21 点、`fornd` 28+ 点；boundary ✓ | inst 6 |
| A10 | `I-lui-00.S`/`I-auipc-00.S`/`I-addi-00.S` | 16 位分片拼装、PC 相对、负立即数 | `set.zw_rwii_rd`/`add.si_riii_rd`/`aip.si_riii_rb`；`SimRISC-03 §1/§2`、`SimRISC-05 §4` | `03` 8 文件 + `00/pseudo_set.*` 7 个；boundary ✓ | inst 3（低优先） |

## B. 系统相关候选（落 `tests/arch`）

| # | 上游族（已核） | 移植意图 | DADAO op / spec | 现有覆盖 | 建议落点/参考条数（估算，不是上限） |
|---|---|---|---|---|---|
| S1 | `priv/Sv/**` 异常路径 | 同步 cause/ip/info、返回精确、连续进入 | `trap_ciii_cfx`/`escape_ciii_cfx`；`SimRISC-11 §2/§3`、`DADAO-12 §5.2/§5.3` | `11-cfx/escape` 37 点、`trap` 15 点；`arch-umon-010`、`arch-ptw-*`、`arch-power-*`；连续/嵌套进入未见专门用例 | arch 4（W3 后、006 前） |
| S2 | `priv` 异步中断面 | TIMER/DMA 进入-ack-返回、同界多源、mask/pending | `trap_ciii_cfx`/`escape_ciii_cfx`；`DADAO-12 §5.4`、`§4.7/§4.9` | `arch-hart-001/002`、`arch-pmem-001/002`（timer/DMA）boundary ✓ | arch 4（只补跨切面，不重测矩阵） |
| S3 | `Zalrsc` + 异常进入 | `lr` 后异常/中断进入 ⇒ `sc` 必败、不写内存 | `lr.o.nn_orrr_rd`/`sc.o.nn_orrr_rd`；`SimRISC-12 §1.1`、`DADAO-12 §5.2/§5.4` | **无**：`12-misc/lr.*` 与 `00/atomic_rmw.S` 显式 GAP（异常/中断清标记；三平台分歧） | arch 5（最高优先，需先裁决 ISS-440/443） |

## 不可移植清单（依据）

- **C 压缩**：`SimRISC-00 §3` 规定每条指令 32 位、4 字节对齐；无 16 位编码/IALIGN 模型。
- **V 向量**：`contracts/opcodes.yaml` 无 vector id（`grep 'id: v'` = 0）；`SimRISC-00 §3` 定长 32 位。
- **Zicsr/Zifencei**：无 CSR/`mstatus/mcause/mepc`，由 `cfx` + `trap`/`escape`/`cfx2rd`/`cfx2rc` 替代（`DADAO-12 §3`、`SimRISC-11 §1`）；无 `fence.i`（`fence_ciii_cfx` 仅资源域）。
- **Sv39/MMU/PMP**：`DADAO-12 §2.2` 为 42 位 VA / 56 位 PA / 64 KiB 页 / 单 PTBR；无 PMP（`grep -c PMP spec/*` = 0）。
- **H 扩展**：`DADAO-12 §1/§4.4` 为四运行模式 + `cfx_hmon`；无 `hstatus`/VS-stage/`vs*` 寄存器。
- **AMO**：`SimRISC-12 §1.1` 只有 `lr/sc`；`contracts/opcodes.yaml` 无 `amo*` id。
- **Zbs 位操作**：`bset/bclr/binv/bext` 在 DADAO 无直接 op（`grep 'id: bset'` 等 = 0）；位操作只到 `rev`/`rol`/`clmul`/`ctlz`/`cttz`/`ctpop`。
- **RVWMO**：无 RVWMO 定义；`fence` 只约束本 hart 访存顺序/可见性且不等待 DMA（`DADAO-12 §4.9`、`SimRISC-11 §5`），单 hart 无可观测重排。
- **非对齐正例**：DADAO 要求自然对齐，未对齐为 `MALIGN`（`SimRISC-01 §1`）；ACT misaligned 正例不可移植。
- **F/D 寄存器模型**：`ft` 窄写高 32 保持、无 NaN-boxing（`SimRISC-07` 开篇）；ACT F/D 的寄存器位型判据不可直接照搬。
- **多 hart**：测试机单 hart（`DADAO-12 §4.7`）；ACT 多 hart/lr-sc 争用、跨 hart 失效不可构造。

## 分批队列

1. **指令批**：`007` 完成后即可开始（不必等 006）；加 A1–A10（按缺口逐条立项，不设总数上限），先 A6→A8/A9→A4/A5，再 A1–A3/A10；只依赖 `tests/inst` 共享生成物，必须与 `m20-testcases-006`、`m20-infra-002`（若在改生成器）**串行写**，不得并行；预估 4–8 h。
2. **系统批**：保持 cfx 大调整（W1–W3 + `m20-integ-002`）**之后**、`m20-testcases-006` **之前**加 S1–S3（按缺口逐条立项，不设总数上限）；只测异常/异步/lr-sc 跨切面，**不重复** `m20-integ-001/002` 的 cfx/cg/rc 矩阵与 006 的 cfx 向量迁移；预估 4–8 h（含三平台逐槽，S3 依赖 ISS-440/443 裁决）。
3. **时间顺序** = `007` → 指令批（可与 cfx W1–W3 并行，但避开 `m20-infra-002`/`006` 的共享写者）→ cfx W1–W3 → `m20-integ-002` → 系统批 → `m20-testcases-006`；006 最后统一收口，若两批都先落地，006 只需一次重生成。

## 未核实与结论

- 上游只核对了上述 `rv64i/{I,M,F,D,Zalrsc,Zbb,Zbc,Zbs,Zba}` 的文件名/存在；**未逐文件统计 ACT 用例数/签名槽数**，故参考条数仅为估算，不是上限；也不是上游条数。
- `priv` 只核对了 `PMP/Sv/...` 目录与少量文件名，未逐条映射 RISC-V privileged 语义；`C/V/Zicsr/Zifencei` 未展开（已判不可移植）。
- **结论**：A 族多数已「边界齐」，ACT 增量主要是独立签名/寄存器字段组合，不建议整族照搬；系统批仅 **S3** 为明确缺口，S1/S2 只补跨切面，不替代现有 arch 用例。
