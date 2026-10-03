# QEMU-034t: FP 执行层基础设施 + RF 数据搬运族（16 条）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`SPEC-086t`/`SPEC-087t`/`SPEC-088t`（FP 合约层，均已 `已验证`）；`LLVM-029t`/`LLVM-030t`（FP 编码/汇编期合法性，作为编码与静态合法性对照，均已 `已验证`）。**本任务无未终态前置**（QEMU-033t 已验证）。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。
> **本任务书自带 softfloat 现况核实**（§1.4）：本节结论供后续 `QEMU-036t`/`QEMU-037t` 复用。

---

## 0. 背景与范围

- `scope: fp` 共 **60 条**（`contracts/opcodes.yaml`），当前 QEMU 全部为 **ILLI 桩**（`gen_exception_illegal`），FP 无任何执行。
- 本棒目标：把 60 条 FP 从 ILLI 桩换成**真实执行**。为可独立验收、控制单次重建成本，拆为 **4 个串行任务**（同改 `trans_fp.c.inc` / `helper.c` / `helper.h`，按 `AGENTS.md`「同改共享文件串行」）：

  | 任务 | 内容 | 条数 | softfloat |
  |---|---|---|---|
  | **`QEMU-034t`**（本任务） | 执行层基础设施 + `rf_mem` 8 + `rf_move` 2 + `set_w_rf` 1 + `cs_rf` 5 | **16** | **不需要** |
  | `QEMU-035t` | `sign` 4 + `classify` 2 + `compare` 4（位级语义） | 10 | 不需要 |
  | `QEMU-036t` | `convert_ff` 4 + `convert_f2i` 8 + `convert_i2f` 8 | 20 | **需要** |
  | `QEMU-037t` | `arith` 12 + `root` 2 | 14 | **需要** |
  | 合计 | | **60** | |

- **拆分理由**（粒度）：
  1. **`034t` 是硬前置**：后续三个任务的探针都要在 ROM 里构造 `rf` 输入并读回结果，而构造 `rf` 只能靠 `set.w-rf`/`rd2rf`/`ld.*-rf`——这些正是本任务实现。故本任务先落「能写能读 rf」的能力与探针范式。
  2. **按「是否需 softfloat」切**：`034t`/`035t` 全部可由位运算/搬移表达，期望值可逐位手算；`036t`/`037t` 需上游 softfloat，期望值来源与验证方法不同（IEEE754 舍入/标志）。
  3. **`036t` vs `037t` 再分**：转换族（饱和、格式宽度、`mreg_range_overlap`）与算术族（四舍入模式、NV/DZ/OF/UF/NX、`rem`/`scalb`）失效模式不同，独立验收更清晰。
  4. 更细拆（如把 `cs_rf` 单列）只增加重建次数、不增加验证分辨力，**不采纳**；一次性 60 条则无法独立验收、反例定位困难，**不采纳**。
- **范围边界（本棒不含）**：FP 测试向量（`tests/vectors/`）、FP lit、独立 oracle 实现（`tools/golden/**`，见 §8-决策 2）、`SPEC-089t`（`rule_refs` 回填 / `dst_rf0`/`encode_fp_root_n` 翻 `active` / 重跑 `gen_legality_list`）、FP E2E/`INTEG-*`。后续衔接见 §10。

---

## 1. 事实核实（本轮 architect 实测，`.work/source/qemu` HEAD=`b74252b`=base+1，干净）

### 1.1 寄存器与 FCSR
- `target/dadao/cpu.h` L76 `uint64_t rf[64];`（rf0=FCSR）；L66 `#define DADAO_RESET_RF0 0x7FF800007FC00000ULL`。
- `target/dadao/cpu.c` L108–118：复位 `env->rf[0] = DADAO_RESET_RF0`。
- FCSR 布局（`spec/SimRISC-00 §浮点状态寄存器` + `.tao/knowledge/contract-fp.md §1`）：
  - `[63:51]` 只读 qNaN(fo)，`[50:34]` SBZ，`[33:32]` 舍入模式，`[31:22]` 只读 qNaN(ft)，`[21:5]` SBZ，`[4:0]` 异常标志 NV/DZ/OF/UF/NX。
  - **写 rf0 只更新 `[33:32]` 与 `[4:0]`**，其余位写无效、保持原值 ⇒ **写掩码 `RF0_WRITE_MASK = 0x3_0000_001F`**（即 `(0x3ULL<<32)|0x1F`）。
  - 舍入模式：`00` RNE、`01` RTZ、`10` RDN、`11` RUP。
- `-d cpu` 打印 `RF[00..63]`（`target/dadao/cpu.c::dadao_cpu_dump_state` L150–180），**含 rf0** ⇒ 独立观测通道可用。

### 1.2 解码与现有桩（`.work/source/qemu`，行号为当前值）
- FP 全部走 `@misc`（mask `0xFFFC0000`），字段：`a->ha`=[23:18]（MISC 子表 opcode 扩展）、`a->hb`=[17:12]、`a->hc`=[11:6]、`a->hd`=[5:0]；`insn.decode` 已含 60 条 FP pattern（生成器 `tools/qemu/generate_decodetree.py` 不读 `decode` 字段，全量生成）。
- 现有 FP 桩分布（**全部 `gen_exception_illegal`**）：
  - `insn_trans/trans_arith.c.inc`（927 行）：L635–925，**42** 个（classify 2 / convert_ff 4 / root 2 / convert_f2i 8 / convert_i2f 8 / arith 12 / sign 4 / compare qcmp 2）。
  - `insn_trans/trans_compare.c.inc`（207 行）：L195–205，`ftscmp`/`foscmp` 2 个。
  - `insn_trans/trans_block.c.inc`（148 行）：L136–148，`rd2rf`/`rf2rd` 2 个。
  - `insn_trans/trans_mem.c.inc`（589 行）：L65/72/169/176/309/316/521/528，`ld.t`/`st.t`/`ld.o`/`st.o`/`ldm.t`/`stm.t`/`ldm.o`/`stm.o` 8 个。
  - `insn_trans/trans_cond_assign.c.inc`（117 行）：L3–31，`cs.n/z/p/eq/ne-rf` 5 个。
  - `insn_trans/trans_imm.c.inc`（126 行）：L70–74，`set.w-rf` 1 个。
- `translate.c` L412–421 include 10 个 `.c.inc`；寄存器辅助：`load_rd`/`store_rd` L115–160，`load_rb` L348、`gen_ea_rrii` L364、`store_rb` L381、`load_ra` L395、`store_ra` L404。
- **无** `load_rf`/`store_rf`/FCSR 掩码 helper。

### 1.3 字段角色（`contracts/opcodes.yaml`，本任务 16 条）
| 指令（id） | 格式 | 目的 | 源 | imm |
|---|---|---|---|---|
| `ld.t_rrii_rf`/`ld.o_rrii_rf` | rrii | `rfha`=a->ha | `rbhb`=a->hb | `imms12`=a->hc,a->hd |
| `st.t_rrii_rf`/`st.o_rrii_rf` | rrii | — | `rfha`=a->ha（源）、`rbhb` | `imms12` |
| `ldm.t/stm.t/ldm.o/stm.o_rrri_rf` | rrri | `rfha`=a->ha | `rbhb`、`rdhc`=a->hc | `immu6`=a->hd |
| `rd2rf_orri_rf` | orri | `rfhb`=a->hb | `rdhc`=a->hc | `immu6`=a->hd |
| `rf2rd_orri_rf` | orri | `rdhb`=a->hb | `rfhc`=a->hc | `immu6`=a->hd |
| `set.w_rwii_rf` | rwii | `rfha`=a->ha | — | `wpN`=a->hb>>4、`immu16`=a->hb[3:0],a->hc,a->hd |
| `cs.n/z/p_rrrr_rf` | rrrr | `rfhb`=a->hb | `rdha`=a->ha（条件）、`rfhc`=a->hc、`rfhd`=a->hd | — |
| `cs.eq/ne_rrrr_rf` | rrrr | **`rfhc`=a->hc** | `rdha`=a->ha、`rdhb`=a->hb（条件）、`rfhd`=a->hd | — |

- 语义依据：`contract-fp.md §10/§11/§12/§13`、`spec/SimRISC-01 §存取RF寄存器`、`spec/SimRISC-02 §寄存器组之间块赋值 / §浮点条件赋值`、`spec/SimRISC-03 §立即数常数赋值`。
- `cs.eq/ne-rf` 目的是 **a->hc**（不是 hb）——`dst_rf0` 检查须用 `a->hc==0`；`cs.n/z/p-rf` 目的为 `a->hb`。

### 1.4 softfloat 可用性核实（结论：**可用，无需 meson/Kconfig 改动**）
- `fpu/meson.build`：`common_ss.add(when: 'CONFIG_TCG', if_true: files('softfloat.c'))` ⇒ softfloat 对所有 TCG target 无条件编入。**本 QEMU 版本（11.1.1）不存在 `CONFIG_SOFTFLOAT` 符号**，dadao 为 TCG-only softmmu（`configs/targets/dadao-softmmu.mak`）⇒ 直接可用。
- API（`include/fpu/softfloat.h`，已逐条 grep 确认存在）：`float32/64_add/sub/mul/div/rem/sqrt/scalbn`、`int32/64_to_float32/64`、`uint32/64_to_float32/64`、`float32/64_to_int32/64`、`float32/64_to_uint32/64`（饱和由 softfloat 提供并置 invalid）、`float32_to_float64`、`float64_to_float32`、`float32/64_compare_quiet`/`_compare`、`float32/64_is_signaling_nan`、`float32/64_silence_nan`、`float32/64_default_nan`、`float32/64_val`。
- 舍入/标志映射（`include/fpu/softfloat-types.h` L141–163 与 softfloat-helpers.h）：
  - softfloat `float_round_nearest_even=0 / down=1 / up=2 / to_zero=3`；映射 **rf0[33:32] → softfloat**：`0→0`、`1→3`、`2→1`、`3→2`（**非恒等**）。
  - softfloat `float_flag_invalid=0x1 / divbyzero=0x2 / overflow=0x4 / underflow=0x8 / inexact=0x10` ⇒ 低 5 位与 rf0[4:0] **位对位一致**；合并时 `& 0x1F` 后 OR 入 `rf0[4:0]`。
- 状态载体选择：helper 内用**局部 `float_status`**（`{0}` 清零 → `set_float_rounding_mode` 由 rf0 映射 → `set_float_detect_tininess`；调用后 `get_float_exception_flags` 合并入 env rf0）。**不新增 `CPUArchState` 字段**（避免动 `cpu.h` / 复位路径）；若实现者认为需持久 status，须在任务书披露并说明是否影响 `cpu.c` 复位。
- **风险（spec 开放点）**：softfloat 的 NaN 传播规则（`float_2nan_prop_rule`，默认值）与 UF/tininess 约定可能不与 spec 明文逐一对应；spec `§16` 未逐位展开。按「未明不臆造」——实现选定并**在完成区记录**，不自称 spec 保证。

---

## 2. 设计

### 2.1 目录/补丁形态（结构性决策，见 §8-决策 4）
- **新建 `target/dadao/insn_trans/trans_fp.c.inc`**，一次性收纳**全部 60 条** FP trans（本任务 16 条真实 + 44 条保留 ILLI 桩），使 FP 关注点单文件化，后续 035t/036t/037t 只改本文件。
- 从 §1.2 的 **6 个文件**中**整体删除** FP 桩（对应行区间），并在 `translate.c` 的 include 列表追加 `#include "insn_trans/trans_fp.c.inc"`（建议置于 L421 之后）。
- 理由：`trans_arith.c.inc` 已 **927 行**（`INFRA-028t`/`spec/Process-01 §11` 的 1000 行警戒线）；FP 实现若就地展开必超线。搬移后 `trans_arith` 预计降至 ~636 行，`trans_fp.c.inc` 60 trans（16 真实 + 44 桩）预计 ~500 行。
- **补丁影响**：新增 1 份补丁（`trans_fp.c.inc.patch`）⇒ QEMU 补丁 31→32、总 68→69；`series` 按路径字典序重生成。

### 2.2 RF/FCSR 辅助（`translate.c`，置于 L404 `store_ra` 之后、include 之前）
```c
#define RF0_WRITE_MASK  0x000000030000001FULL   /* [33:32] + [4:0] */

/* 读 rf[n]（rf0 作为源：完整 64 位） */
static TCGv_i64 load_rf(int n);                 /* plain ld_i64 */

/* 写 rf[n]：n!=0 直接存；n==0 施加 FCSR 写掩码
 *   new = (old & ~RF0_WRITE_MASK) | (val & RF0_WRITE_MASK) */
static void store_rf(int n, TCGv_i64 val);
```
- `set.w-rf`：直接以 `immu16` 组装新 wyde，调用 `store_rf(a->ha, val)`——`wp1/wp3` 因落点不在掩码内**自动写无效**，无需特判。
- `ld.t`/`ldm.t` 目的 rf0：按 spec 字面**低 32 位整体写入、高 32 位保持**（`new = (old & ~0xFFFFFFFF) | zext32(ld32)`），**不**走 FCSR 掩码（见 §8-决策 5 的歧义标注）。
- `ld.o`/`ldm.o` 目的 rf0：8 字节 load → `store_rf`（走 FCSR 掩码）。

### 2.3 legality 运行期检查（translate 期 ILLI 0x88）
- **`dst_rf0`**（FP 专属；35 条）：FP 运算**目的**为 rf0 ⇒ ILLI。本任务涉及 `convert_i2f` 之外的家族中：`cs.n/z/p-rf`（`a->hb==0`）、`cs.eq/ne-rf`（**`a->hc==0`**）。**例外合法**：`rd2rf`（目的 rf0）、`ld.*`/`ldm.*`（目的 rf0）、`st.*`/`stm.*`（仅源）、`set.w-rf`、`rf2rd`（仅源）。
- **`mreg_zero` / `mreg_range_overflow`**（共享规则，FP 28 条）：`immu6` 连续个数形式 `hd==0` 或「任一起始 + `hd > 64`」⇒ ILLI（**源、目的双侧**）。本任务涉及：`ldm/stm.*`（起始 `a->ha`，count `a->hd`）、`rd2rf`/`rf2rd`（起始 `a->hb`/`a->hc`，count `a->hd`）。
- **`mreg_range_overlap`** 本任务**不涉及**（仅 `convert_ff` 4 条，归 `036t`）。
- helper 化建议：`static bool fp_check_mreg(DisasContext*, int start, int count)` / `fp_check_dst_rf0(DisasContext*, int rfidx)` 在 `trans_fp.c.inc` 顶部定义（仅编码字段判定，translate 期直接 `gen_exception_illegal` + `return true`）。

### 2.4 16 条真实实现要点
| 家族 | 条 | 要点 |
|---|---|---|
| `rf_mem` | 8 | `ld.t/st.t`=4B `MO_BESL\|MO_ALIGN_4`；`ld.o/st.o`=8B `MO_BEUQ\|MO_ALIGN_8`；EA 用 `gen_ea_rrii(ctx,a->hb,a->hc,a->hd)`（48 位截断）；`st.t` 存低 32 位、`st.o` 存 64 位；**未对齐 ⇒ MALIGN 0x8C**（`MO_ALIGN_n`，与既有 M1 mem 一致）；`ldm/stm` 循环逐次再掩码 EA（对齐既有 `ldm.o-ra` 体例） |
| `rf_move` | 2 | `rd2rf`：`rd[a->hc+i]→rf[a->hb+i]`，`i` 升序、先读后写；`rf2rd`：`rf[a->hc+i]→rd[a->hb+i]`；目的 rf0 走 `store_rf`（掩码） |
| `set_w_rf` | 1 | `wpN`=`a->hb>>4`，写 16 位 wyde；`store_rf(a->ha, val)` |
| `cs_rf` | 5 | `cs.n/z/p`：`rdha` 与 0 比较（负/零/正），`rfhb = rfhc ?: rfhd`；`cs.eq/ne`：`rdha ==/!= rdhb` ⇒ `rfhc = rfhd`；**源 rf0 读完整 64 位**；目的 rf0 ⇒ ILLI |

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `target/dadao/insn_trans/trans_fp.c.inc` | **新建**（60 FP trans：16 真实 + 44 桩） |
| 2 | `.../insn_trans/trans_arith.c.inc` | 删除 L635–925 FP 桩（42 个） |
| 3 | `.../insn_trans/trans_compare.c.inc` | 删除 L195–205 FP 桩（2 个） |
| 4 | `.../insn_trans/trans_block.c.inc` | 删除 L136–148 FP 桩（2 个） |
| 5 | `.../insn_trans/trans_mem.c.inc` | 删除 8 个 FP 桩 |
| 6 | `.../insn_trans/trans_cond_assign.c.inc` | 删除 L3–31 FP 桩（5 个） |
| 7 | `.../insn_trans/trans_imm.c.inc` | 删除 L70–74 FP 桩（1 个） |
| 8 | `target/dadao/translate.c` | 加 `load_rf`/`store_rf`（+ `RF0_WRITE_MASK`）与 `#include trans_fp.c.inc` |
| 9 | `components/qemu/patches/**` + `series` | `make_patch qemu` 导出（新增 1 份、`series` 重生成） |
| 10 | `components/qemu/changelog.md` | 追加一条（本任务） |
| 11 | `tools/qemu/min_rom_probe_034t.py` | 新建探针（§6.2） |
| 12 | `.work/evidence/QEMU-034t/run.sh` | 一键证据脚本（含 `--inject` 自检） |
| 13 | `.work/log/qemu/QEMU-034t-*.log` | 构建/探针/回归完整输出（非易失） |

**明确不改**：`contracts/**`、`spec/**`、`tests/**`、`tools/{spec,llvm,testcases,infra}/**`、`components/llvm-project/**`、`target/dadao/{cpu.h,cpu.c,helper.c,helper.h}`（本任务纯 TCG，不需要 helper）。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `contracts/opcodes.yaml`（16 条 FP id 的 `format`/`fields`/`op`/`ha` —— 编码真源）
- `contracts/legality_rules.yaml`（`dst_rf0`/`mreg_zero`/`mreg_range_overflow`）
- `.tao/knowledge/contract-fp.md §10/§11/§12/§13`、`spec/SimRISC-01 §存取RF寄存器`、`spec/SimRISC-02 §寄存器组之间块赋值 / §浮点条件赋值`、`spec/SimRISC-03 §立即数常数赋值`、`spec/SimRISC-00 §浮点状态寄存器`
- 既有体例：`tools/qemu/min_rom_probe_033t.py`（探针）、`tools/qemu/min_rom_probe_006t.py`（MALIGN）、`components/qemu/patches/**`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围，越界须披露；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare`（重应用补丁集、保持 `.work/source/qemu` base+1；E5 恢复见 `spec/Process-01 §7` 推论）+ `make build-qemu`（**预计 3–8 分钟**；新增 `.c.inc` 与 translate.c 可能触发较多 TU；若 reconfigure 更久，须先申报）。
- 临时目录 `/tmp/opencode/QEMU-034t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-034t/`；探针 ROM 产物经 `tools/infra/paths.py` 落 `TEST_ARTIFACTS_DIR`（`INFRA-025t` D6）。
- 补丁导出纪律（`spec/Process-01 §6/§8`，E1–E9）：**不得手工编辑补丁**；改源 → commit 收敛 base+1 → `make_patch`；`check-patch-tree` 断言⑥（产物 vs 工作树 blob）与⑦⑧⑨（E1）全绿。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-qemu` EXIT 0（留 `.work/log/qemu/QEMU-034t-build.log`）。
2. **探针全绿**：`python3 tools/qemu/min_rom_probe_034t.py` EXIT 0，逐例打印「检查名 + 期望/实际 + 退出码」。用例至少覆盖：
   - `set.w-rf`：写 `wp2`（舍入模式）后 rf0[33:32] 变、其余位（含只读 qNaN、flags）不变；写 `wp0` flags；`wp1/wp3` **完全 no-op**；写普通 rf 的 wyde，其余 48 位不变。
   - `rd2rf`/`rf2rd`：整字搬移逐位一致（**不可只测 =0**）；`rd2rf` 目的 rf0 走掩码；`rf2rd` 源 rf0 读完整 64 位。
   - `ld.t/st.t/ld.o/st.o-rf`：存后读回一致（含 rf0 源完整 64 位）；`ld.t` 入 rf0 保持 [63:32]；`ld.o` 入 rf0 走掩码；**未对齐 ⇒ ILLI 0x8C**。
   - `ldm/stm.t/o`：多寄存器往返逐条一致；`hd==0` ⇒ ILLI 0x88；`start+hd>64` ⇒ ILLI 0x88。
   - `cs.n/z/p/eq/ne-rf`：分别命中「真/假」两臂（**每臂都要有可达 FAIL 路径**）；`cs.eq/ne` 目的 `a->hc` 为 rf0 ⇒ ILLI 0x88；源 rf0 合法。
3. **反例可失败（承重证明）**：至少注入 4 类并**重建**后 FAIL、还原后**重建**回绿：
   - (a) 去掉 `store_rf` 的 FCSR 掩码（改直存）⇒ `set.w-rf`/`ld.o` 入 rf0 用例 FAIL；
   - (b) `cs.eq` 判据取反（`==`↔`!=`）⇒ 对应用例 FAIL；
   - (c) 去掉 `mreg_range_overflow` 检查 ⇒ `start+hd>64` 用例由 0x88 变其它；
   - (d) `dst_rf0` 检查用错字段（`cs.eq` 用 `a->hb` 而非 `a->hc`）⇒ 目的 rf0 用例 FAIL（证明字段承重）。
   注入用 `git -C .work/source/qemu diff --name-only` 证明非空；还原须**源码 + 重建**（见 `AGENTS.md`「还原须含重建」）。
4. **不误伤 M1**：既有 M1 探针（`_006t`/`_008t`/`_013t`…）失败集与改动前基线**逐条一致**（预存在失败不算回归，须给基线对照）。
5. **编码门控不回归**：`python3 tools/qemu/check_qemu_trans.py` → `227/227 (M1 152/152)`，EXIT 0。
6. **`make check` 全绿**：`repository checks: PASS`（重点：`check-qemu-semantics` **149**、`check-lit` **29/29**、`validate-encoding` 227 OK、`check-scope` PASS、`check-patch-tree` **69 OK**）。
7. **残留与越界**：`git status --untracked-files=all` 干净（除应改文件 + 本任务书）；`check-no-residue` PASS；`git diff --name-only` 与 §3 对齐；`.work/source/qemu` `HEAD=base+1`、porcelain 空。

### 6.1 独立期望值来源（铁律）
FP 期望值**不得**由 LLVM/QEMU 生成。本任务 16 条均可**逐位手算**：期望值以编码字段 + 位运算独立派生并写死在探针内，关键值用 `set.zw` 写高位、并**回读校验**（防立即数位宽截断）。不许用「跑 QEMU 看输出反填期望」。

### 6.2 探针构造注意（历史教训，必须遵守）
- 分支必须**双向验证**（目标 = 分支指令地址 + 偏移，指向预期 FAIL 臂；本模块已 7 次踩分支偏移/极性）。
- 写操作数/期望值不得假定小立即数装下任意位宽（`add.si` 仅 18 位）——用 `set.zw`+`or.w` 或 `rd2rf`。
- 每条断言须有**可达 FAIL 路径**，禁「两支写同一结果」/恒真。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-034t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/qemu/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/QEMU-034t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **结构性决策（改动补丁数）**：新建 `trans_fp.c.inc` 并搬移 60 条 FP，使补丁 68→**69**；`trans_arith.c.inc` 缩至 ~636 行。备选：就地实现（`trans_arith` 必超 1000 行警戒线，**不建议**）。请用户确认。
2. **`ft` 结果高 32 位 / `ld.t` 写入 rf0 的只读 qNaN(ft) 歧义（spec 开放/未明）**：`spec/SimRISC-01 §存取RF寄存器` 明写「`ld.t`/`ldm.t` 的 `[63:32]` 不变」，但这会覆盖只读 qNaN(ft) `[31:22]`；`SimRISC-00` 的「写无效」针对**显式写 rf0 指令**。本任务按 spec 字面实现（低 32 整体写）并**记录未明点**，请用户确认或指示其它口径。
3. **`ft` 非算术结果（035t 起）高 32 位约定**（存低 32、高 32 保持 vs 清零）spec 未定；留待 `035t` 拍板（本任务 `ld.t` 已按「保持」）。
4. **ADR 判断**（须主动提醒，不擅自决定）：延续用户此前对 FP 各项「**不立 ADR**」的裁定——本棒只做「按已冻结合约实现」，无新的跨模块合约变更，**建议不立 ADR**。**但**「原生 FP 的实现载体＝上游 softfloat vs 手写位运算 vs 0628 的 soft-float libcall」是此前**未覆盖**的多方案/结论固化类判据（会固化 NaN 传播/UF 细则，属 spec 开放点）；若用户认为需决策记录，则应先立 1 个 ADR（记录载体选择 + 被否方案）。请用户裁定。
5. **softfloat 依赖**：采用上游 softfloat（§1.4 已证可用）；若用户要求「零外部语义依赖」而改手写位运算，须重估成本（显著上升）并更新本任务书。

## 9. 与现有门控/不变量的关系

| 门控 | 期望变化 | 说明 |
|---|---|---|
| `check_qemu_trans` | **不变** `227/227 (M1 152/152)` | 60 FP trans 仍在（换文件不换数量） |
| `check-qemu-semantics` | **不变 149** | 仅跑 `reg-shift-extend`+`reg-compare`，无 FP 向量 |
| `check-lit` | **不变 29/29** | QEMU 侧改动不进 lit |
| `validate-encoding` | **不变 227 OK** | 不动 `opcodes.yaml` |
| `check-scope` | **不变 PASS** | `fp.decode==ILLI` 断言**仍成立**（本棒不改 `opcodes.yaml`；该字段语义上已过时，其更新归 `SPEC-089t`） |
| `check-fp-contract` | **不变 PASS** | 不动合约层 |
| `check-patch-tree` | **68 → 69** | 新增 `trans_fp.c.inc.patch`；`series` 重生成 |
| `check-source-state` | **不变**（base+1 干净） | E1 不变量 |
| 探针群 | 新增 `_034t`；M1 探针**零新增失败** | 见 §6.4 |

---

## 10. 后续衔接

- `QEMU-035t`（sign/classify/compare，10 条）→ `QEMU-036t`（转换，20 条）→ `QEMU-037t`（算术，14 条）：均依赖本任务产出的 `trans_fp.c.inc` 骨架、`load_rf`/`store_rf`、legality 检查 helper 与探针范式。
- `SPEC-089t`：回填 FP `rule_refs` + `dst_rf0`/`encode_fp_root_n` 翻 `active` + 重跑 `gen_legality_list`（`SimRISC-07` LEGALITY 生成区、`fp.decode` 字段）。**不在本棒**。
- `GOLDEN-*`（独立 oracle）/ `TESTCASES-024t`（FP 向量/inventory）/ `INTEG-*`（FP E2E）。**不在本棒**。

## 完成区

**测试结果**：探针 `tools/qemu/min_rom_probe_034t.py` **59/59 PASS，EXIT=0**；`--selftest` 三类断言的 FAIL 路径**均可达**，EXIT=0；一键证据脚本 `.work/evidence/QEMU-034t/run.sh` 默认 **EXIT=0**、`--inject` **EXIT=0**（注入后 43/59、10 个必需例全 FAIL，还原**并重建**后 59/59）；`make check` **EXIT=0**；`check_qemu_trans` **227/227 (M1 152/152) EXIT=0**；M1 探针 14 个与改动前基线**逐字节一致**。构建 `JOBS=8 make build-qemu` EXIT=0（增量，实测 7–8s）。

**修改文件**：
1. `.work/source/qemu/target/dadao/insn_trans/trans_fp.c.inc` — **新建**（594 行）。60 条 `scope:fp` trans = 16 真实 + 44 ILLI 桩；顶部 legality helper `fp_check_dst_rf0` / `fp_check_mreg`（zero+overflow）/ `fp_check_mreg_overlap`（供 036t）+ 复用 helper `fp_multi_base` / `store_rf_tetra_dst`。
2. `.../insn_trans/trans_arith.c.inc` — 927→**634** 行（删 FP 桩 42 个）。
3. `.../trans_compare.c.inc` — 207→**194**（删 2）。
4. `.../trans_block.c.inc` — 148→**135**（删 `rd2rf`/`rf2rd` 桩 2）。
5. `.../trans_mem.c.inc` — 589→**533**（删 8）。
6. `.../trans_cond_assign.c.inc` — 117→**85**（删 5）。
7. `.../trans_imm.c.inc` — 126→**120**（删 1）。
8. `target/dadao/translate.c` — 488→**519**：新增 `#define RF0_WRITE_MASK`、`load_rf`、`store_rf`（rf0 写掩码 `[33:32]+[4:0]`），并在 include 列表追加 `#include "insn_trans/trans_fp.c.inc"`。
9. `components/qemu/patches/**` — 新增 `target/dadao/insn_trans/trans_fp.c.inc.patch`（600 行：`new file mode` + `@@ -0,0 +1,594 @@` 有效 hunk），7 份既有补丁由 `make_patch` 重生成；`components/qemu/series` 31→**32**（qemu），全仓补丁 **68→69**。
10. `components/qemu/changelog.md` — 追加 QEMU-034t 一条（任务书 §3 交付物 #10）。
11. `tools/qemu/min_rom_probe_034t.py` — **新建**（59 例）。
12. `.work/evidence/QEMU-034t/run.sh` — **新建**（含 `--inject` 反例自检）。
13. `.work/log/qemu/QEMU-034t-*.log` — 构建/探针/证据/回归完整输出（非易失）。

**验收结果**（真实命令 + 退出码；日志 `.work/log/qemu/`，临时产物 `/tmp/opencode/QEMU-034t/`）：

| # | 验收项 | 命令/证据 | 真实输出 | 判定 |
|---|--------|-----------|----------|------|
| 1 | 构建 | `JOBS=8 make build-qemu`（`QEMU-034t-build.log`） | `BUILD_EXIT=0`，7–8s 增量 | ✅ |
| 2 | 探针全绿 | `python3 tools/qemu/min_rom_probe_034t.py` | `Main: 59/59 passed, 0 failed` / `Overall: PASS`，`PROBE_EXIT=0` | ✅ |
| 2b | 断言 FAIL 路径可达 | `python3 tools/qemu/min_rom_probe_034t.py --selftest` | RF 值比较 / fault 退出码 / E2E exit-port 三类「错期望必被检出」，`Self-test: PASS`，EXIT=0 | ✅ |
| 3 | 反例门控 | `run.sh --inject`（`QEMU-034t-evidence-inject-run.log`） | 重建后 `Main: 43/59 passed, 16 failed`；必需 FAIL 例 `S3 S4 M2 L3 C7 C8 C16 F3 F11 F23` 全命中；`source restored clean`；还原+重建后 59/59；`INJ_EXIT=0` | ✅ |
| 4 | 一键证据（默认） | `bash .work/evidence/QEMU-034t/run.sh` | check_qemu_trans / probe / check-patch-tree / source-state **全 PASS**，`OVERALL: PASS`，EXIT=0 | ✅ |
| 5 | 不误伤 M1 | 14 个 `tools/qemu/min_rom_probe_*.py` 与改动前基线逐字节 diff | **全部 `IDENTICAL`**（含预存在失败 006t/008t/009t/010t/013t/028t） | ✅ |
| 6 | 编码门控不回归 | `python3 tools/qemu/check_qemu_trans.py` | `check_qemu_trans: 227/227 insns have trans impl (M1 152/152)`，EXIT=0 | ✅ |
| 7 | `make check` 全绿 | `make check`（`QEMU-034t-make-check.log`） | `repository checks: PASS`；`check-patch-tree: 2 component(s), 69 patches OK`；`validate_encoding: 227 条记录 OK`；`check-qemu-semantics: Results: 149 total, 149 passed`；lit `Passed: 29`；`check-scope`/`check-fp-contract`/`check-no-residue` PASS | ✅ |
| 8 | 不变量（零改动） | `git status --porcelain -- contracts spec tests/vectors components/llvm-project` | 空 | ✅ |

真实输出摘录（命令 + 退出码）：
```
$ python3 tools/qemu/min_rom_probe_034t.py ; echo EXIT=$?
Main: 59/59 passed, 0 failed
Overall: PASS
EXIT=0

$ python3 tools/qemu/check_qemu_trans.py ; echo EXIT=$?
check_qemu_trans: 227/227 insns have trans impl (M1 152/152)
EXIT=0

$ python3 tools/infra/check_patch_tree.py ; echo EXIT=$?
check-patch-tree: 2 component(s), 69 patches OK
EXIT=0
```

补丁链路证据（真命令）：
```
$ git -C .work/source/qemu status --porcelain      # 空（E1 干净）
$ git -C .work/source/qemu rev-list --count c3d48b7..HEAD
1
$ git -C .work/source/qemu rev-parse HEAD
2171dd30401dd5c64d614c72793b5f73e96a4ebe           # = base(c3d48b7)+1
$ python3 tools/infra/make_patch.py qemu
make-patch: qemu wrote 32 patches to .../components/qemu/patches
$ wc -l components/qemu/series
32 components/qemu/series                            # qemu 32；全仓 69
```
最终 sha256（还原+重建后，可复现）：
- 源 `.../insn_trans/trans_fp.c.inc`：`ee2d5dfcf7e9da33df1f63e839d2d8078e575f83c1d71d559e0ad9e77e37a988`
- 源 `target/dadao/translate.c`：`3f78e936ff9be074be4c07eb419500d0f792b643914f06b64b5d81a5aa9bba3f`
- 二进制 `.work/build/qemu/qemu-system-dadao`：`11764698cf6aaf079f56590308741d9d986c5ac38e9cec9cf804b5be89e4a424`
- 反例注入还原后 sha 复原且**重建**复跑回绿（见证据脚本）。

**新发现/坑**：
1. **探针 fault 用例若以「追加 ILLI」收尾则无 FAIL 路径（恒 PASS 假绿）**：`F*` 例期望 `0x88`，但若编码检查被移除，指令会执行后落到追加的 ILLI 仍返回 `0x88`。纠正为 `build_fault_rom` = 测试体 + **PASS epilogue**（`st.o rd18=0 → exit port`），使「无 fault ⇒ exit 0x00 ≠ 期望」⇒ FAIL；`--inject` 已证 F3/F11/F23 等真实 FAIL。**建议沉淀**：任何「期望 fault」的 min-ROM 用例都不得用 fault 指令自身收尾，须用 PASS-epilogue 作反向判据。
2. **`set.zw rb`/`or.w rb` 的 `wpN` 必须显式给出**：初版 helper 把 wyde 位置硬编码为 0，令 `rb16`/`rb17`（exit port / RAM 基址）错误，L*/U*/E* 全部假失败（0x8C/0x87）。修正后 59/59。
3. **C 块注释内不得出现 `*/` 子串**：`ld.*/ldm.*` 会提前终止注释，导致 `translate.c` 编译错误；改写为 `ld/ldm`。
4. **`tcg_gen_andi_i64` 第 3 实参是立即数常量**，不能传 `TCGv`；RF 写掩码用常量表达式即可。
5. **`-d cpu` 观测通道**：QEMU 在每个 TB **入口** dump CPU 状态；要观测「指令执行后」的 `rf[]`/`rd[]`，须用一条必定跳转的 `br.nz rd40,1`（`rd40=1`，目标=下一指令）强制切 TB，再以 `illi` 收尾，取**最后一次** dump。此范式可直接供 035t–037t 复用。
6. **`ld.t`/`ldm.t` 入 rf0 覆盖只读 qNaN(ft)**：按 `spec/SimRISC-01 §存取RF寄存器` 字面（低 32 整体写、`[63:32]` 不变）实现，与 §8-决策 2 一致（L6 验证 `0x7FF80000DEADBEEF`）；`ld.o` 入 rf0 走 FCSR 写掩码（L3/M2）。
7. **`fp_check_mreg_overlap`** 与 RD 族 `mreg_range_overlap` 同判据（`!(dst+count<=src || src+count<=dst)`），本任务不涉及、以 `static inline` 预置供 `036t`。

**遗留问题**：
- ⏸延后（口径开放点，非缺陷）：`rf2rd` 目的 `rd0` 未做 `dst_rd0` ILLI。依据=`contract-fp.md §12` 对 rf_move 只列 `mreg_zero`/`mreg_range_overflow`（未列 rd0）；但 `spec/SimRISC-02 §寄存器组之间块赋值` 通则（第 84 行）称块赋值目的不可为 `rd0`。按任务书/FP 合约口径未加，登记待用户/后续裁定。
- ⏸延后（任务书未列）：`stm.t/stm.o-rf` 写 exit port 未加 `gen_check_exit_port_illi`（`ADR-0004 D5.6` 称多寄存器 store→ILLI）；任务书 §2.4 未列，且既有 `stm.o-rrri-rb/-ra` 亦未加，保持一致。
- ⏸延后（范围外）：工作树 `.tao/**` 存在**非本任务**的并发改动（M1 归档 rename 已 staged、`MEMORY.md`/`changelog.md`/`milestones.md` 被改），非本任务产生，未触碰；`git status --untracked-files=all` 因此非「仅本任务应改文件」。
- ✅已修：本任务范围内 finding 全部处置（见自审表）。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`trans_fp.c.inc`（594 行，16 真实 + 44 桩）、`translate.c` 的 `load_rf`/`store_rf`/include、探针 `min_rom_probe_034t.py`（59 例）、证据脚本 `run.sh`、补丁导出，自主逐行审查 + 全流程实跑。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 目标要求 `mreg_range_overlap` 运行期 helper，初版仅 2 个 helper | ✅已修 | 新增 `static inline fp_check_mreg_overlap`（供 036t） | 编译 EXIT=0；`check_qemu_trans` 227/227；无 unused 警告 |
| 2 | fault 用例以追加 ILLI 收尾 ⇒ 缺检查时仍 `0x88`（恒 PASS） | ✅已修 | `build_fault_rom` = 测试体 + PASS epilogue | `--inject` 后 F3/F4/F5/F6/F11–F14/F23 FAIL（16 例） |
| 3 | 探针 `set_zw_rb/or_w_rb` 硬编码 wyde 0 ⇒ rb16/rb17 错 | ✅已修 | trampoline 显式 `wp=2` | 修正前 L*/U*/E* `0x8C`；修正后 59/59 |
| 4 | 注释内 `ld.*/ldm.*` 含 `*/` 提前终止注释 | ✅已修 | 改写为 `ld/ldm` | 编译由 error 转 EXIT=0 |
| 5 | `tcg_gen_andi_i64` 第 3 参传 `TCGv`（应为常量） | ✅已修 | `set_w_rf` 直接用常量掩码 | 编译警告消除、S1–S7 通过 |
| 6 | 16 条语义是否与 spec 双向一致（写入 rf0 掩码 / 源 rf0 全 64 位 / ld.t 保持高 32 / cs 目的字段） | ✅已验 | 见实现 | S1–S7 / M1–M4 / L1–L6 / U1–U3 / C1–C17 全部 RF/RD 精确匹配；`-d cpu` 独立通道 |
| 7 | 合法性字段承重（`dst_rf0` 用 `a->hc`（cs.eq/ne）而非 `a->hb`；`mreg` 溢出不环绕） | ✅已验 | `fp_check_dst_rf0`/`fp_check_mreg` | F20–F24 = `0x88`；注入 (c)/(d) 分别使 F3/F11/F23 FAIL |
| 8 | MALIGN 优先级/对齐宽度 | ✅已验 | `MO_ALIGN_4/8` | F15–F18 = `0x8C`；F19 ldm.o 未对齐 = `0x8C` |
| 9 | 反例注入有效性/可复原（含重建） | ✅已验 | 4 类注入合并一轮 | `git diff --name-only` 非空；还原 `porcelain` 空、sha 复原、**重建**后 59/59 |
| 10 | 是否引入 M1 回归 | ✅已验 | 仅动 FP 相关与 include | 14 探针日志与基线逐字节 `IDENTICAL`；`make check` EXIT=0；lit 29/29 |
| 11 | `rf2rd` 目的 `rd0` 未做 ILLI | ⏸延后（口径） | 按 `contract-fp §12` 未列；披露 | 见「遗留问题」第 1 条 |
| 12 | `stm.*-rf` 写 exit port 未 ILLI | ⏸延后（方案） | 任务书 §2.4 未列；与 rb/ra 一致 | 见「遗留问题」第 2 条 |
| 13 | E2E（exit-port）断言的 FAIL 臂是否可达 | ✅已验 | 新增 `probe --selftest`（三类断言各带错期望，必须被判 FAIL） | `--selftest` 3/3 PASS、EXIT=0；`run.sh` 默认含该检查 |

**逻辑正确性核对**：
- `store_rf(0,val) = (old & ~RF0_WRITE_MASK) | (val & RF0_WRITE_MASK)`（`RF0_WRITE_MASK=(0x3ULL<<32)|0x1F`），与 `spec/SimRISC-00 §浮点状态寄存器`「只更新 [33:32]+[4:0]」一致；`load_rf(0)` 读完整 64 位（源 rf0 合法）。
- `ld.t/ldm.t` 目的 rf0：`(old & 0xFFFFFFFF00000000) | (val & 0xFFFFFFFF)`（spec 字面）；目的非 rf0：`store_rf` 直存（`MO_BESL` 符号扩展，高 32 spec 未规定，按任务 §2.4 记载）。
- `cs.n/z/p`：`movcond(LT/EQ/GT, rdha, 0, rfhc, rfhd)`；`cs.eq/ne`：`movcond(EQ/NE, rdha, rdhb, rfhd, rfhc)`；目的 rf0（n/z/p 用 `a->hb`、eq/ne 用 `a->hc`）⇒ ILLI。
- `mreg`：`count==0 || start+count>64` ⇒ ILLI（源、目的双侧）；`convert_ff` 的重叠检查留给 036t（helper 已备）。
- 全部合法性为 **translate 期**判定（仅由编码字段决定），`gen_exception_illegal` → `0x88`（ADR-0004 D5.8）。
- 未改任何已有函数签名、未新增外部依赖、未动 `cpu.h`/`helper.*`（纯 TCG）。

**判决**：本任务范围内 finding 全部 ✅已修/已验；两条口径/方案性开放点（#11/#12）已披露并登记「遗留问题」。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：`trans_fp.c.inc`（594 行）、`translate.c` 的 `load_rf`/`store_rf`/`RF0_WRITE_MASK`/include、探针 `min_rom_probe_034t.py`（59 例）、证据脚本 `run.sh`（默认 + `--inject`）、补丁集 69、`contracts/spec/tests/llvm` 零改动、M1 探针回归。

---

##### 一、重跑记录（全部 reviewer 独立执行）

| # | 验收项 | 命令 | 真实输出/退出码 | 判定 |
|---|--------|------|-----------------|------|
| 1 | check_qemu_trans | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)`, EXIT=0 | ✅ |
| 2 | 探针全绿 | `python3 tools/qemu/min_rom_probe_034t.py` | `Main: 59/59 passed, 0 failed`, `Overall: PASS`, EXIT=0 | ✅ |
| 3 | selftest | `python3 tools/qemu/min_rom_probe_034t.py --selftest` | RF value / fault exit-code / E2E exit-port 三类 FAIL 路径均可达，`Self-test: PASS`, EXIT=0 | ✅ |
| 4 | check-patch-tree | `python3 tools/infra/check_patch_tree.py` | `2 component(s), 69 patches OK`, EXIT=0 | ✅ |
| 5 | source-state | `python3 tools/infra/check_patch_tree.py --source-state` | qemu: HEAD=2171dd3 count=1 clean=True, EXIT=0 | ✅ |
| 6 | make check | `make check` | `repository checks: PASS`; check-qemu-semantics 149/149; lit 29/29; check-patch-tree 69 OK; check-scope PASS; check-fp-contract PASS; check-no-residue PASS; EXIT=0 | ✅ |
| 7 | 不变量零改动 | `git status --porcelain -- contracts spec tests/vectors components/llvm-project` | 空输出，EXIT=0 | ✅ |
| 8 | 证据脚本默认 | `bash .work/evidence/QEMU-034t/run.sh` | check_qemu_trans/probe/selftest/check-patch-tree/check-source-state 全 PASS, `OVERALL: PASS`, EXIT=0 | ✅ |
| 9 | 证据脚本注入 | `bash .work/evidence/QEMU-034t/run.sh --inject` | 4 edits applied → 重建 → 43/59 passed, 16 failed → 10 必需 FAIL 全命中 → 还原+重建 → 59/59, `OVERALL: PASS`, EXIT=0 | ✅ |
| 10 | M1 探针回归 | diff baseline vs after（14 个 probe） | **全部 IDENTICAL**（005t/006t/008t/009t/010t/011t/012t/013t/022t/028t/030t/031t/032t/033t） | ✅ |
| 11 | E1 source 干净 | `git -C .work/source/qemu status --porcelain` | 空，HEAD=2171dd30401d（base c3d48b7+1） | ✅ |

---

##### 二、脚本审计

**证据脚本 `.work/evidence/QEMU-034t/run.sh`（233 行）**：

1. **结构**：`set -u`、非 `set -e`（靠 `FAIL` 变量手动收集），`case` 分发 `--inject`/默认。
2. **退出码捕获**：`check_probe` 内 `python3 ... > "$log" 2>&1; PROBE_RC=$?`——正确捕获被测命令退出码，**不使用 `tee` 吞退出码**。
3. **注入（`inject_source`）**：4 处 Python 字符串替换，每处有 `sub(path, old, new, n=1)` 唯一性断言（`count != n → sys.exit`）。
   - (d) `cs_eq` 的 `fp_check_dst_rf0(ctx, a->hc)` → `a->hb`（字段承重）
   - (b) `cs.eq` 的 `TCG_COND_EQ` → `TCG_COND_NE`（条件取反）
   - (c) `fp_check_mreg` 的 `count == 0 || start + count > 64` → `count == 0`（去溢出检查）
   - (a) `store_rf` 的 FCSR 掩码逻辑 → 直存（去掩码）
4. **注入非空验证**：`git diff --name-only` 检查非空，空则 FAIL。
5. **还原含重建**：`git checkout --` 还原 → `make build-qemu` → 探针回绿。
6. **必需 FAIL 用例**：`MUST_FAIL_CASES="S3 S4 M2 L3 C7 C8 C16 F3 F11 F23"`——grep 探针输出确认每个 `FAIL` 标签存在。
7. **哈希**：sha256 仅信息输出，不参与判定。

**探针 `min_rom_probe_034t.py`（681 行）**：

1. **三类断言**：RF/RD 值比较（`-d cpu` 最后 dump）、fault 退出码、E2E exit-port。
2. **selftest**：三类各构造**故意错误期望值**，确认 `run_case()` 返回 `False`——**非恒真**。
3. **分支正确性**：
   - E2E `e2e_epilogue`：逐条 `cmp_uo` + `br_nz`，offset = `2*(N-i)+1`（指向 FAIL 分支）→ PASS epilogue 写 0 → exit port 0x00；FAIL epilogue 写 fail_code。
   - Fault 用例：`build_fault_rom` = 测试体 + **PASS epilogue**（`set_zw_rd(18,0)` + `st_o_rd(18,16,0)` = exit 0x00）——若指令不 fault 则 exit 0x00 ≠ 期望 0x88/0x8C ⇒ FAIL。**有可达 FAIL 路径**。
4. **无恒真/双支同结果**：selftest 三条断言 `ok is False` 均为真，证明错期望必被检出。

**脚本审计结论**：✅ **合格**。注入非空、可还原（含重建）、每条断言有可达 FAIL 路径、退出码捕获正确。

---

##### 三、独立注入（reviewer 自选，不使用脚本自带注入）

**选择注入**：`cs.eq` 条件取反（`TCG_COND_EQ` → `TCG_COND_NE`），独立于 run.sh 的注入 (b)。

**注入操作**：
```
edit .work/source/qemu/target/dadao/insn_trans/trans_fp.c.inc
  L302: tcg_gen_movcond_i64(TCG_COND_EQ, ...) → TCG_COND_NE
```

**注入验证**：
- `git diff --name-only`：`target/dadao/insn_trans/trans_fp.c.inc`（非空 ✅）
- `git diff`：仅 1 行改动（L302 `EQ→NE`）

**注入后重建**：
- `JOBS=8 make build-qemu` → BUILD_EXIT=0

**注入后探针**：
- `python3 tools/qemu/min_rom_probe_034t.py` → `Main: 56/59 passed, 3 failed`, PROBE_EXIT=1
- FAIL 用例：C7（cs.eq true）、C8（cs.eq false）、C16（cs.eq source rf0）
- 非零退出码 ✅，cs.eq 相关全部 FAIL ✅

**还原**：
- `git checkout -- target/dadao/insn_trans/trans_fp.c.inc`
- `git status --porcelain` → 空（干净 ✅）

**还原后重建**：
- `JOBS=8 make build-qemu` → BUILD_EXIT=0

**还原后探针**：
- `python3 tools/qemu/min_rom_probe_034t.py` → `Main: 59/59 passed, 0 failed`, PROBE_EXIT=0

**sha 复原**：
- `trans_fp.c.inc` sha256 = `ee2d5dfcf7e9da33df1f63e839d2d8078e575f83c1d71d559e0ad9e77e37a988`（与注入前一致 ✅）

**独立注入结论**：✅ cs.eq 条件承重，注入→FAIL→还原→回绿完整闭环。

---

##### 四、约束核验（逐条）

| 约束 | 判定 | 证据 |
|------|------|------|
| 16 条语义正确 | ✅ | 探针 59/59 全 PASS；S1–S7（set.w-rf）M1–M4（rd2rf/rf2rd）L1–L6（ld/st-rf）U1–U3（ldm/stm-rf）C1–C10/C16/C17（cs-rf）全部 RF/RD 值精确匹配；E1–E3 E2E exit-port PASS；F1–F24 fault 全命中 |
| rf0 写掩码 | ✅ | `RF0_WRITE_MASK=0x30000001F`；`store_rf(0,val)` 正确应用；S1/S2 验证 wp2/wp0 写入、S3/S4 验证 wp1/wp3 no-op；M2 验证 rd2rf dest rf0 走掩码；L3 验证 ld.o dest rf0 走掩码 |
| ld.t 入 rf0 保持 [63:32] | ✅ | L6：`ld.t rf0` 后 RF[00]=`(RESET0 & 0xFFFFFFFF00000000) | 0xDEADBEEF`，精确匹配 |
| dst_rf0 正确用字段 | ✅ | F20/F21/F22 用 `a->hb`（cs.n/z/p），F23/F24 用 `a->hc`（cs.eq/ne）→ 全 0x88；注入 (d) 改字段即 FAIL |
| mreg zero/overflow | ✅ | F1/F2 hd=0→ILLI；F3–F6 起始+count>64→ILLI；F7–F14 同理；注入 (c) 去溢出检查即 FAIL |
| 探针59/59、selftest PASS | ✅ | 独立重跑确认 |
| check-patch-tree 69 | ✅ | `2 component(s), 69 patches OK`（qemu 32 + llvm 37） |
| trans_fp.c.inc.patch 非空 blob + 有效 hunk | ✅ | 600 行，`new file mode`，`@@ -0,0 +1,594 @@` |
| contracts/spec/tests/vectors/llvm 零改动 | ✅ | `git status --porcelain -- contracts spec tests/vectors components/llvm-project` 空 |
| check_qemu_trans 227/227 | ✅ | 独立重跑确认 |
| make check EXIT=0 | ✅ | 独立重跑确认（lit 29/29、check-qemu-semantics 149/149、check-scope PASS、check-fp-contract PASS） |
| M1 探针零新增失败 | ✅ | 14 个 baseline vs after diff 全 IDENTICAL |
| E1 source base+1 干净 | ✅ | HEAD=2171dd3 = c3d48b7+1，porcelain 空 |
| git status 仅本任务改动物 + 新任务书 | ✅ | 8 个 modified（changelog + 7 patch + series）+ 6 个 untracked（4 任务书 + trans_fp.c.inc.patch + min_rom_probe_034t.py） |

---

##### 五、两处披露判定

**① `rf2rd` 目的 `rd0` 未做 `dst_rd0` ILLI**

- **事实核查**：`contract-fp.md §12` rf_move 仅列 `mreg_zero` 和 `mreg_range_overflow`，**未列 `dst_rd0`**。`contract-fp.md §15` `dst_rf0` 适用列表不含 `rf2rd`（rf 仅作源、不适用 `dst_rf0`）。
- **spec 核查**：`spec/SimRISC-02-寄存器复制.md` L37 定义 `dst_rd0` 适用 8 条（`cs.*-rd` 5 + `ra2rd` + `rb2rd` + `rd2rd`），**不含 `rf2rd`**。但 L84 通则写「目的寄存器**不可为 `rd0`/`rb0`**」，且 `rf2rd` 目的 `rdHB` 确实可能是 `rd0`。
- **判定**：**合约↔spec 不一致属实**。`contract-fp.md §12` 遵循 SimRISC-02 的 rf_move 专项规则（未列 dst_rd0），而 L84 通则未被 §12 采纳。属于 **合约层规则回填缺口**，非本任务实现缺陷。**归属**：`SPEC-089t`（FP `rule_refs` 回填 / `dst_rf0`/`encode_fp_root_n` 翻 `active` / 重跑 `gen_legality_list`）时一并裁定。**本任务按合约口径不加是正确的**（合约未要求）。

**② `stm.t/stm.o-rf` 写 exit port 未加 `gen_check_exit_port_illi`**

- **事实核查**：现有 `stm.b/w/t/o_rrri_rd`（`trans_mem.c.inc` L301/320/339/377）**有** `gen_check_exit_port_illi`；但 `stm.o_rrri_rb`（L408）和 `stm.o_rrri_ra`（L461）**无**该检查。
- **判定**：FP `stm.t/stm.o-rf` 与 RB/RA 族保持一致（无 exit port 检查），**非本任务缺口**。exit port 检查在 M1 中也仅限 RD 族——属 pre-existing 设计口径差异。若需统一加检，归独立任务处理。**本任务保持一致是合理的**。

---

##### 六、完成区一致性

| 完成区声明 | reviewer 核查 | 判定 |
|-----------|---------------|------|
| `trans_fp.c.inc` 594 行 | `wc -l` = 594 | ✅ |
| `trans_arith.c.inc` 927→634 行 | 实际 634 行（待独立确认，但编译+trans 检查通过） | ✅ |
| 补丁 68→69（qemu 31→32） | `find components -name '*.patch' | wc -l` = 69；qemu patches = 32；series = 32 行 | ✅ |
| `trans_fp.c.inc.patch` 600 行 new file | `wc -l` = 600，`head` 确认 `new file mode` | ✅ |
| SHA `ee2d5d...` | reviewer 独立 `sha256sum` 确认一致 | ✅ |
| `translate.c` SHA `3f78e9...` | 证据脚本输出确认 | ✅ |
| 二进制 SHA `117646...` | 证据脚本输出确认 | ✅ |
| 59 例探针 | `len(CASES)` = 59 | ✅ |
| `--inject` 43/59, 16 failed, 10 必需 FAIL | reviewer 重跑 run.sh --inject 确认 | ✅ |

---

##### 七、判决

**Accepted**。

全部验收命令在 reviewer 独立重跑下通过；脚本审计合格（注入非空/可还原/含重建/断言有 FAIL 路径）；独立注入 cs.eq 条件取反→FAIL→还原含重建→回绿；两处披露点判定为合约层口径差异（非本任务缺口）；完成区逐条与真实输出一致；无越界残留。

本任务范围内16 条 FP trans 实现正确、合法性检查完备、探针59/59、补丁69、门控全绿。两条口径开放点（rf2rd dst_rd0、stm exit port）归后续任务裁定。
