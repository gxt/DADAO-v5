# QEMU-036t: FP softfloat 转换族（convert_ff 4 + convert_f2i 8 + convert_i2f 8 = 20 条）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`QEMU-034t`（**必须先 `已验证`**：骨架/`load_rf`/`store_rf`/legality helper/探针范式）、`QEMU-035t`（建议先 `已验证`；非硬依赖，但同改 `trans_fp.c.inc` ⇒ 串行）。相关：`SPEC-087t`（合约）。
**状态**：待开始

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景与范围

- 本棒 4 任务之一（拆分见 `QEMU-034t §0`）。本任务实现 **20 条转换族**，是**首次引入上游 softfloat** 的任务。
- 本任务同时建立 softfloat 接入骨架（`float_status` 初始化/提交、舍入模式映射、标志合并），供 `QEMU-037t` 复用。
- 只改 `trans_fp.c.inc` + `helper.c` + `helper.h`（不改 `cpu.h`/`meson.build`/`insn.decode`）。

---

## 1. 事实核实（本轮 architect 实测；softfloat 可用性见 `QEMU-034t §1.4`）

### 1.1 现有桩（`QEMU-034t` 后位于 `trans_fp.c.inc`）
`ft2fo`/`ft2ft`/`fo2ft`/`fo2fo`（convert_ff 4）；`ft2it`/`ft2io`/`ft2ut`/`ft2uo`/`fo2it`/`fo2io`/`fo2ut`/`fo2uo`（convert_f2i 8）；`it2ft`/`io2ft`/`ut2ft`/`uo2ft`/`it2fo`/`io2fo`/`ut2fo`/`uo2fo`（convert_i2f 8）。

### 1.2 字段/编码（`contracts/opcodes.yaml`）
- convert_ff / convert_i2f：orri，目的 `rfhb`=a->hb，源 `rfhc`(ff)/`rdhc`(i2f)=a->hc，`immu6`=a->hd。
- convert_f2i：orri，目的 `rdhb`=a->hb，源 `rfhc`=a->hc，`immu6`=a->hd。

### 1.3 语义（`contract-fp.md §2/§3/§4`；`spec/SimRISC-07 §格式转换指令`）
- **convert_ff**：舍入由 rf0[33:32]；溢出→±Inf+OF；下溢按舍入模式+UF；NaN 传播 payload；sNaN 作算术输入⇒NV+qNaN；**源/目的范围有交集（含完全重合）⇒ ILLI**（`mreg_range_overlap`）；目的 rf0 ⇒ ILLI；`immu6==0` 或起始+`immu6>64` ⇒ ILLI。
- **convert_f2i**：NaN/Inf/超范围 ⇒ 整型**饱和值（最大/最小）** + **NV**；目的 rd（无 `dst_rf0`）；`immu6` 范围检查。**精度损失是否置 NX：spec 未明**（`contract-fp.md §16`）⇒ 标 `UNSPECIFIED`，实现选定并记录（建议：按 softfloat 行为即置 NX，或按「spec 未明不臆造」不额外处理——**须在任务书确认后固定**）。**f2i 的舍入方向亦未明**（rf0 舍入模式 vs 向零截断）：spec 仅在 convert_ff/i2f 段明写 rf0 控制，f2i 段未提；建议按 IEEE754/惯例采用**向零截断**（`float32_to_int32_round_to_zero` 等），并在完成区记录（见 §8-决策 2）。
- **convert_i2f**：可能 inexact，舍入由 rf0，标志按 IEEE754；目的 rf0 ⇒ ILLI；`immu6` 范围检查。
- 整数宽度：`it`=32 位有符号、`io`=64 位有符号、`ut`=32 位无符号、`uo`=64 位无符号；`ft`=32 位单精、`fo`=64 位双精。

### 1.4 softfloat 接口映射（本任务）
| 指令 | softfloat API |
|---|---|
| `ft2fo` | `float32_to_float64` |
| `fo2ft` | `float64_to_float32` |
| `ft2ft`/`fo2fo` | 搬移（`ft2ft` 按 32 位、`fo2fo` 按 64 位；高 32 位口径见 §8-决策 1） |
| `ft2it`/`ft2io` | `float32_to_int32`(`_round_to_zero`) / `float32_to_int64` —— **饱和 + invalid** 由 softfloat 提供，需核对是否满足 spec 的「最大/最小 + NV」 |
| `ft2ut`/`ft2uo` | `float32_to_uint32` / `float32_to_uint64` |
| `fo2it`/`fo2io`/`fo2ut`/`fo2uo` | `float64_to_int32` / `_int64` / `_uint32` / `_uint64` |
| `it2ft`/`io2ft`/`ut2ft`/`uo2ft` | `int32_to_float32` / `int64_to_float32` / `uint32_to_float32` / `uint64_to_float32` |
| `it2fo`/… | `int32_to_float64` / `int64_to_float64` / `uint32_to_float64` / `uint64_to_float64` |

- 舍入模式映射（`RF_MODE`）：`0→float_round_nearest_even`、`1→float_round_to_zero`、`2→float_round_down`、`3→float_round_up`（见 `QEMU-034t §1.4`）。
- 标志：`get_float_exception_flags(&st) & 0x1F` OR 入 `env->rf[0][4:0]`。
- **饱和边界须实测**：softfloat 对 NaN/Inf/超范围的整型转换返回值与 NV 需与 spec「最大/最小 + NV」逐条比对；若有出入，在 helper 中显式包装（不得改 softfloat 源码）。

### 1.5 高风险/未明点
- `convert_f2i` 的 NX（§1.3）——spec 未明。
- NaN payload 传播（softfloat 规则 vs spec「传播 payload」）——spec 未逐位展开（`contract-fp.md §16`）。
- `ft2ft` 语义：spec 列为「浮点寄存器间搬移」；按 32 位搬移，高 32 位口径见 §8。

---

## 2. 设计

### 2.1 softfloat 接入骨架（`helper.c` + `helper.c` 内 FP 段；`helper.h` 声明）
```c
/* helper.c */
#include "fpu/softfloat.h"

static FloatRoundMode rf0_round_mode(uint64_t rf0);   /* 映射表 §1.4 */
static void fp_status_init(CPUDADAOState *env, float_status *st);
static void fp_status_commit(CPUDADAOState *env, float_status *st); /* flags &0x1F OR 入 rf0 */
```
- 每个转换 helper：`fp_status_init` → 调用 softfloat → 取结果 → `fp_status_commit`。
- 结果写回：convert_ff/convert_i2f 用 `store_rf(a->hb+i, res)`（rf0 走掩码，且**先做 `dst_rf0` ILLI 检查**）；convert_f2i 用 `store_rd(a->hb+i, res)`。
- 块形式：trans 内循环 `i=0..hd-1`，**先读后写**、按序递增；convert_ff **先查 `mreg_range_overlap`**（源 `[hc,hc+hd)` ∩ 目的 `[hb,hb+hd)` ≠ ∅ ⇒ ILLI）。

### 2.2 legality（translate 期，用 `QEMU-034t` helper）
- `dst_rf0`：convert_ff / convert_i2f 的 `a->hb==0` ⇒ ILLI（35 条中的 12 条）。
- `mreg_zero`/`mreg_range_overflow`：起始 `a->hc`/`a->hb` + `a->hd` 双侧。
- `mreg_range_overlap`：仅 convert_ff 4 条。

### 2.3 不改动
不动 `cpu.h`/`cpu.c`/`meson.build`/`insn.decode`/`opcodes.yaml`/合约；不加向量/lit。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `target/dadao/insn_trans/trans_fp.c.inc` | 20 条 stub → 真实实现 |
| 2 | `target/dadao/helper.h` | 新增 FP 转换 helper 声明（`DEF_HELPER_*`） |
| 3 | `target/dadao/helper.c` | 新增 softfloat 接入 + 转换 helper |
| 4 | `components/qemu/patches/**` + `series` | `make_patch qemu`（预期无新增补丁，仍 32/69） |
| 5 | `components/qemu/changelog.md` | 追加一条 |
| 6 | `tools/qemu/min_rom_probe_036t.py` | 新建探针（§6.2） |
| 7 | 独立期望值参考（见 §6.1） | 落 `tools/qemu/` 或探针内（须声明非 LLVM/QEMU 来源） |
| 8 | `.work/evidence/QEMU-036t/run.sh` | 一键证据脚本（含 `--inject`） |
| 9 | `.work/log/qemu/QEMU-036t-*.log` | 构建/探针/回归完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tests/**`、`components/llvm-project/**`、`cpu.h`/`cpu.c`/`meson.build`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `contracts/opcodes.yaml`（20 条 id 的 `fields`）
- `.tao/knowledge/contract-fp.md §2/§3/§4、§16`、`spec/SimRISC-07 §格式转换指令`
- `QEMU-034t`/`QEMU-035t` 产出；`include/fpu/softfloat.h`（API 真源）
- 既有体例：`helper.c`（`ra_load`/`ras_push` 等）、`tools/qemu/min_rom_probe_*.py`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围，越界须披露；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare` + `make build-qemu`（**预计 3–8 分钟**；首次引入 softfloat 头文件，若触发更多 TU 重建须先申报）。softfloat.c 本身已随 TCG 编入，无需 reconfigure。
- 临时目录 `/tmp/opencode/QEMU-036t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-036t/`。
- 补丁纪律同 `QEMU-034t §5`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-qemu` EXIT 0（留日志）。
2. **探针全绿**：`python3 tools/qemu/min_rom_probe_036t.py` EXIT 0。用例至少覆盖（每族「正常 + 边界 + 异常」）：
   - **convert_ff**：`ft2ft`/`fo2fo` 搬移（位不变）；`ft2fo`/`fo2ft` 精确值往返；**四种舍入模式**各一例（RNE/RTZ/RDN/RUP，结果可区分）；溢出→±Inf+OF；下溢→UF；**NaN payload 传播**；**sNaN ⇒ NV + qNaN**；源/目的重叠（含完全重合）⇒ ILLI 0x88；目的 rf0 ⇒ ILLI；`immu6==0`/越界 ⇒ ILLI。
   - **convert_i2f**：各宽度 × 各舍入模式；inexact ⇒ NX；负数/无符号边界；目的 rf0 ⇒ ILLI。
   - **convert_f2i**：NaN/±Inf/±超范围 ⇒ **饱和最大值/最小值 + NV**（4 种宽度逐一）；正常截断；`immu6` 检查。（NX 口径按 §8-决策 2 固定。）
3. **反例可失败（承重证明）**：至少注入并**重建**后 FAIL、还原后**重建**回绿：
   - (a) 舍入模式映射故意恒等（`rf0_mode` 直接当 softfloat 枚举）⇒ RTZ/RDN/RUP 用例 FAIL（证明映射承重）；
   - (b) 标志合并漏 `& 0x1F`（把 softfloat 高位标志也 OR 进 rf0）⇒ 标志用例 FAIL；
   - (c) convert_f2i 去掉饱和处理（直接整数转换）⇒ NaN/超范围用例 FAIL；
   - (d) `mreg_range_overlap` 检查去掉 ⇒ 重叠用例由 0x88 变其它；
   - (e) `dst_rf0` 检查字段错（用 a->hc 而非 a->hb）⇒ 目的 rf0 用例 FAIL。
   注入 `git diff --name-only` 非空；还原须**源码 + 重建**。
4. **不误伤 M1**：既有 M1 探针与 `_034t`/`_035t` 失败集零新增。
5. **编码门控不回归**：`check_qemu_trans` `227/227 (M1 152/152)` EXIT 0。
6. **`make check` 全绿**：`check-qemu-semantics` 149、`check-lit` 29/29、`check-patch-tree` 69 OK、`check-scope`/`check-fp-contract` PASS。
7. **残留/越界/不变量**：`git status --untracked-files=all` 干净；`check-no-residue` PASS；base+1 干净；改动与 §3 对齐。

### 6.1 独立期望值来源（铁律，本任务最关键）
FP 期望值**不得**由 LLVM/QEMU 生成。本任务建议：
- **优先**：由用户决定是否先落 `GOLDEN-001t`（独立 oracle，见 `QEMU-034t §8-决策 4`/本棒 §8-决策 3）。若选定「先 oracle」：本任务**依赖 `GOLDEN-001t` 先 `已验证`**，探针期望值由 oracle 生成（oracle 独立派生自 spec）。
- **否则**（oracle 后置）：探针期望值**独立派生**——RNE 可用宿主 `struct`（f32）/`float`（f64）交叉锚点，**非 RNE 模式与标志**须用精确有理数（`fractions`/整数尾数）在任务内独立实现并**逐例手算复核**；所有派生过程写入完成区，禁「跑 QEMU 反填」。
- **两种路径均须**：期望值来源与推导过程在完成区可回溯，且不得以 QEMU/LLVM 输出作校准。

### 6.2 探针构造注意
同 `QEMU-034t §6.2`。舍入模式用例须构造「四种模式结果互不相同」的输入（否则模式断言无鉴别力）；饱和用例须取明显超范围值。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-036t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/qemu/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/QEMU-036t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **`ft` 高 32 位口径**（`ft2ft`/`ft2fo` 等结果）：承 `QEMU-034t §8-决策 3`。
2. **`convert_f2i` 的 NX 与舍入方向（spec 未明）**：建议**向零截断**（`_round_to_zero` 变体）+ 按「spec 未明不臆造」**不额外置 NX**（仅 NV 饱和），并在完成区标 `UNSPECIFIED`；请用户确认（若改按 softfloat 行为置 NX 或用 rf0 舍入模式，须在任务书固定）。
3. **独立 oracle 先后**（本棒头号待拍板项）：本任务期望值来源依赖 §6.1 的选择——「先 `GOLDEN-001t`」还是「任务内独立派生」。architect 建议见 `QEMU-034t §8-决策 4` 与本棒汇总；请用户拍板。
4. **ADR**：承 `QEMU-034t §8-决策 4`（建议不立，请确认）。
5. **softfloat 饱和行为**（§1.4）：若与 spec「最大/最小 + NV」有出入，须 helper 包装并披露（不改 softfloat 源码）。

## 9. 与现有门控/不变量的关系

| 门控 | 期望变化 |
|---|---|
| `check_qemu_trans` | 不变 `227/227` |
| `check-qemu-semantics` | 不变 149 |
| `check-lit` | 不变 29/29 |
| `check-patch-tree` | 不变 **69** |
| `check-scope`/`check-fp-contract`/`validate-encoding` | 不变 PASS |
| 探针群 | 新增 `_036t`；M1 与 `_034t`/`_035t` 零新增失败 |

---

## 10. 后续衔接
`QEMU-037t`（`arith`/`root`，softfloat）复用本任务的 `fp_status_init`/`fp_status_commit`/舍入映射。

## 完成区

**测试结果**：
（待填写）

**修改文件**：
（待填写）

**验收结果**：
（待填写）

**新发现/坑**：
（待填写）

**遗留问题**：
（待填写）

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
