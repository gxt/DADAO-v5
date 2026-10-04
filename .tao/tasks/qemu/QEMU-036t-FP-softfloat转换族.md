# QEMU-036t: FP softfloat 转换族（convert_ff 4 + convert_f2i 8 + convert_i2f 8 = 20 条）

**模块**：qemu
**项目里程碑**：M2
**依赖**：`QEMU-034t`（**必须先 `已验证`**：骨架/`load_rf`/`store_rf`/legality helper/探针范式）、`QEMU-035t`（建议先 `已验证`；非硬依赖，但同改 `trans_fp.c.inc` ⇒ 串行）。相关：`SPEC-087t`（合约）。
**状态**：已验证

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

**测试结果**：探针 `tools/qemu/min_rom_probe_036t.py` **113/113 PASS，EXIT=0**；`--selftest` 四类断言 FAIL 路径可达 + **期望值独立派生自检**（`verify_derivations()`）全部 PASS，EXIT=0；一键证据 `.work/evidence/QEMU-036t/run.sh` 默认 **EXIT=0**、`--inject` **EXIT=0**（5 处注入→重建→93/113、20 FAIL、17 个必需例全命中→还原清洁→**重建**→113/113）；`check_qemu_trans` **227/227 (M1 152/152) EXIT=0**；`make check` **EXIT=0**（semantics 149/149、lit 29/29、patch-tree 69、scope/fp-contract/no-residue PASS）；M1 探针 14 个 + `_034t` 与 `_035t` 后基线**逐字节 IDENTICAL**（`_035t` 77/77、`_034t` 59/59）。构建 `JOBS=8 make build-qemu` EXIT=0（增量）。

**修改文件**：
1. `.work/source/qemu/target/dadao/helper.c` — 314→**474 行**：`+ #include "fpu/softfloat.h"`；新增 softfloat 接入骨架 `rf0_round_mode`/`fp_status_init`/`fp_status_commit`/`fp_status_commit_nv_only` 与 3 个 helper `helper_fp_cvt_ff`/`helper_fp_cvt_f2i`/`helper_fp_cvt_i2f`。**局部 `float_status`，未新增 `cpu.h` 字段**。
2. `.../helper.h` — 23→**28 行**：`DEF_HELPER_3(fp_cvt_ff/fp_cvt_f2i/fp_cvt_i2f, i64, env, i64, i32)`。
3. `.../insn_trans/trans_fp.c.inc` — 846→**928 行**：20 条 ILLI 桩 → 真实实现；新增 `gen_convert_ff`（含 `fp_check_mreg_overlap`）/`gen_convert_f2i`/`gen_convert_i2f` 三个通用块处理 + kind 枚举；头注释同步（余 14 条桩归 `QEMU-037t`）。
4. `components/qemu/patches/target/dadao/{helper.c,helper.h,insn_trans/trans_fp.c.inc}.patch` — 由 `make_patch qemu` 重生成（480/34/934 行；**无新增补丁**，qemu 仍 32、全仓仍 **69**）。
5. `components/qemu/changelog.md` — 追加 `QEMU-036t` 一条。
6. `tools/qemu/min_rom_probe_036t.py` — **新建**（113 例 + `--selftest` + 独立派生自检；产物经 `_probe_artifact_dir()`）。
7. `.work/evidence/QEMU-036t/run.sh` — **新建**（默认 + `--inject` 5 处反例自检）。
8. `.work/log/qemu/QEMU-036t-*.log` — 构建/探针/证据/注入/回归完整输出（非易失）。
- 未提交 DADAO-v5 仓库；`.work/source/qemu` 已 amend 至 base+1（`HEAD=750c12b`，`rev-list --count c3d48b7..HEAD=1`，porcelain 空）。

**验收结果**（真实命令 + 退出码；日志 `.work/log/qemu/`，临时产物 `/tmp/opencode/QEMU-036t/`）：

| # | 验收项 | 命令/证据 | 真实输出 | 判定 |
|---|--------|-----------|----------|------|
| 1 | 构建 | `JOBS=8 make build-qemu`（`QEMU-036t-build.log`） | `BUILD_EXIT=0`，增量 | ✅ |
| 2 | 探针全绿 | `python3 tools/qemu/min_rom_probe_036t.py` | `Main: 113/113 passed, 0 failed` / `Overall: PASS`，`PROBE_EXIT=0` | ✅ |
| 2b | 断言 FAIL 路径 + 派生自检 | `... --selftest` | RF 值 / FCSR flags / RD 值 / fault 退出码 / E2E exit-port 五类「错期望必检出」+ 28 条独立派生自检 PASS，`Self-test: PASS`，EXIT=0 | ✅ |
| 3 | 反例门控 | `bash .work/evidence/QEMU-036t/run.sh --inject` | 5 edits → 重建 → `93/113 passed, 20 failed` → 必需 17 例 `FF13 FF15 FF22 FF24 FF27 FI03 FI04 FI05 FI06 FL01 FL02 FL06 FL07 FL08 FL09 IF07 IF08` 全命中 → `source restored clean` → 还原+重建 → 113/113；`INJECT_EXIT=0` | ✅ |
| 4 | 一键证据（默认） | `bash .work/evidence/QEMU-036t/run.sh` | trans / probe / selftest / patch-tree / source-state 全 PASS，`OVERALL: PASS`，EXIT=0 | ✅ |
| 5 | 不误伤 M1 | 14 个 M1 探针 + `_034t` 与 `_035t` 后基线逐字节 diff | **全部 `IDENTICAL`**（含预存在失败 006t/008t/009t/010t/013t/028t）；`_034t` 59/59 | ✅ |
| 6 | 编码门控不回归 | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)`，EXIT=0 | ✅ |
| 7 | `make check` 全绿 | `make check`（`QEMU-036t-make-check.log`） | `repository checks: PASS`；`check-patch-tree: 69 patches OK`；`check-qemu-semantics: 149 total, 149 passed`；lit `Passed: 29`；`check-scope`/`check-fp-contract`/`check-no-residue` PASS，EXIT=0 | ✅ |
| 8 | 不变量（零改动） | `git status --porcelain -- contracts spec tests/vectors components/llvm-project` | 空 | ✅ |
| 9 | 残留/E1 | `make check-no-residue`；`check_patch_tree.py --source-state` | `check-no-residue: PASS`；`qemu: OK HEAD=750c12b8ccfc count=1 clean=True` | ✅ |

真实输出摘录（命令 + 退出码）：
```
$ python3 tools/qemu/min_rom_probe_036t.py ; echo EXIT=$?
Main: 113/113 passed, 0 failed
Overall: PASS
EXIT=0

$ python3 tools/qemu/check_qemu_trans.py ; echo EXIT=$?
check_qemu_trans: 227/227 insns have trans impl (M1 152/152)
EXIT=0

$ make check ; echo EXIT=$?
repository checks: PASS
EXIT=0
```
最终 sha（还原+重建后，可复现）：
- 源 `.../helper.c`：`1a723005aab9ae0c1d05108c9cd67b183b96d265df611414d097c6f7649f94cb`
- 源 `.../helper.h`：`1ab89af734e4ec0b0f48223c1908d13951878b2e7ffe54153b2413658cc96ee4`
- 源 `.../trans_fp.c.inc`：`89cc81d0bb97f226ec3aab7d9795bf231def128f4c48467bb9b241a437e1de63`
- 二进制 `.work/build/qemu/qemu-system-dadao`：`ad152ec1bf3f29af19fa22f8ac7b03f4cc0e3dc9f575a7818fe6f067a7768229`（二进制 sha 非稳定判据，以重建后探针回绿为证）

**独立期望值派生（铁律，§6.1；**未**用 LLVM/QEMU 生成/校准）**：
- **派生方法**（脚本 `/tmp/opencode/QEMU-036t/derive.py`；并**内联进探针** `verify_derivations()`，在 `--selftest` 中逐条复算）：
  - RNE（f32↔f64、int→f32/f64）：宿主 `struct`/`float` 锚点（任务允许）。
  - **非 RNE**（RTZ/RDN/RUP）：`fractions.Fraction` 精确有理数舍入器（按 IEEE754 就近偶数/向零/向下/向上逐位推导），对 `1±2^-24`、`1±2^-24±2^-30` 等**精确二元分数**输入逐例手算并复核。
  - f→i：`int()` 向零截断 + 整型饱和上下界（`INT32/INT64/UINT32/UINT64`）独立常量。
  - NaN payload：IEEE754 规则 `f32 尾数 << 29`（加宽）/保留高尾数位（收窄）；sNaN⇒静默。
- 探针内 113 例期望值为**写死常量**，`verify_derivations()`（28 条）从第一性原理复算并比对全部 PASS，证明常量非「跑 QEMU 反填」。

**口径选定（spec 开放点 / 任务书需固定项，须在完成区记录）**：
1. **`ft` 高 32 位（承 034t §8-决策 2/3、035t 口径）**：
   - `ft2ft`/`fo2fo`：**全 64 位寄存器搬移**（`mov`），不置标志。依据 spec「浮点寄存器间搬移」+ `contract-fp.md §14`（`set.ft` 寄存器传值展开为 `ft2ft`/`fo2fo`），并满足验收「位不变」。**披露**：任务 §1.4 表「ft2ft 按 32 位」与验收「位不变」字面冲突——本实现取「`ft` **格式**为 32 位、寄存器搬移保 64 位」的解释（探针 FF16 用 `0x12345678DEADBEEF` 全 64 位验证）。若用户裁定改为「只搬低 32、高 32 清零/保持」，须同步改实现与 FF16。
   - `fo2ft` 与全部 `i2f→ft` 的**计算结果**：低 32 位为结果、**高 32 位清零**（`zero-extend`）。选「清零」（而非「保持」）因其为结果的确定函数、不依赖目的旧值。
2. **`convert_f2i` 舍入与标志（§8-决策 2，采纳任务书建议）**：用 softfloat `_round_to_zero` 变体**向零截断**；NaN/Inf/超范围→**饱和最大/最小 + NV**；**不置 NX**（spec 未明，按「不臆造」仅传播 `float_flag_invalid`）。探针 FI01/FI07 断言 NX 未置。
3. **`convert_i2f`**：rf0 舍入、softfloat 标志 `&0x1F` 全量合并（inexact⇒NX）；32 位源 `it` 取低 32 符号扩展、`ut` 零扩展；32 位结果 `it` 符号扩展、`ut` 零扩展（对齐 M1 `add.st/ut` 口径）。
4. **NaN/Inf/sNaN**：由 softfloat 处理，符合 spec「传播 payload / sNaN⇒NV+qNaN」；探针 FF12–FF15 逐位验证。

**新发现/坑**：
1. **`ft2ft` 的「32 位 vs 位不变」字面冲突**（见口径选定 1）：任务书 §1.4 与 §6.2 相互矛盾，本任务取「全 64 位搬移」并由探针显式验证；此为需用户/后续固定的开放点。**建议沉淀**：任务书撰写时应避免同一指令的「格式宽度」与「搬移宽度」混用。
2. **f2i「不置 NX」须在 helper 层过滤**：softfloat `_round_to_zero` 对 inexact 会置 `float_flag_inexact`；按裁定 f→i 只传播 `float_flag_invalid`（`fp_status_commit_nv_only`），否则 FI01/FI07 会误置 NX。**建议沉淀**：spec 未明的标志语义必须在 helper 层显式过滤，不能依赖 softfloat 默认行为。
3. **softfloat `&0x1F` 掩码的承重来自 sNaN**：`float_flag_invalid_snan`(0x2000) 等高位标志在赋值运算中会被置起；若不 `&0x1F` 会污染 rf0。注入 (b) 因 sNaN 用例 FF13/FF15 才可失败——普通 inexact/invalid/overflow 均在低 5 位，无法暴露该缺陷。**建议沉淀**：验证「标志合并掩码」须用会触发**高位** softfloat 标志的输入（sNaN）。
4. **二进制 sha 非稳定判据**：源码 commit 未变（同一 `750c12b`）时重建二进制 sha 仍可不同（QEMU 嵌入构建期信息）。验收以「源码 blob sha 复原 + 重建后探针回绿」为证，不要求二进制 sha 相等。
5. **`--inject` 合并注入的独立归因**：5 处注入对应 20 个 FAIL 用例，逐例仅由单一注入触发（如 `IF06`（RTZ）在注入 (a) 恒等映射下与 RDN 同结果而**不 FAIL**，故 RTZ 承重改由 `IF08`/`FF22` 等区分用例证明）——避免「多注入抵消」假绿。注入后**唯一**失败集 = `FF13 FF15 FF22 FF24 FF27 FL01–FL05 FL06–FL09 FI03–FI06 IF07 IF08`（20 条），无意外失败。
6. **`float32_to_int64` 可作「去饱和」注入的良定义替代**：注入 (c) 将 `ft2it` 改经 `float32_to_int64` 再截断 int32，对 NaN/Inf/超范围产生确定性的回绕值（非 UB），使「去饱和⇒用例 FAIL」可安全证明。**建议沉淀**：反例注入应优先选**良定义**的等价改写，避免 C UB 导致可复现性风险。

**遗留问题**：
- ⏸延后（开放口径，非缺陷）：口径选定 1 的 `ft2ft` 高 32 位解释、口径选定 2 的 f2i「不置 NX」为 spec/任务书未明处，本任务按任务书建议固定并披露；若用户另有裁定，须同步改实现与探针期望值。
- ⏸延后（范围外，任务书未列）：未新增 `GOLDEN-*` 独立 oracle（`QEMU-034t §8-决策 3`）；本任务以「探针内独立派生 + 反例门控」承担，独立 oracle 后置。
- ✅已修：本任务范围内 finding 全部处置（见自审表），无未修项。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`helper.c`（474 行，+160）、`helper.h`（+5）、`trans_fp.c.inc`（928 行，20 条真实转换 + 3 通用块函数）、探针 `min_rom_probe_036t.py`（113 例 + selftest + 派生自检）、证据脚本 `run.sh`（默认 + 5 注入）、补丁导出（69 不变），自主逐行审查 + 全流程实跑。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `--selftest` 第 4 项（fault 路径）初稿用**非法**用例作「期望 fault」⇒ 恒成立、无法证伪 | ✅已修 | 改用**合法**转换 `ft2fo(4,8,1)` 期望 ILLI（实际 exit 0） | `--selftest` 由 FAIL→PASS；EXIT=0 |
| 2 | 期望值仅写死常量，§6.1 要求「派生过程可回溯」 | ✅已修 | 探针内新增 `verify_derivations()`：有理数舍入器 + 宿主锚点复算 28 条 | `--selftest` 派生自检 28/28 PASS |
| 3 | 20 条语义与 spec 双向一致性（舍入/饱和/传播/块序/字段角色） | ✅已验 | 见实现与口径说明 | FF01–FF28 / FL01–FL12 / FI01–FI34 / FJ01–FJ05 / IF01–IF25 / IG01–IG06 全 RF/RD/fault 精确匹配；`-d cpu` 独立通道 |
| 4 | 合法性检查承重（`dst_rf0` 用 `a->hb`；`mreg_zero`/`mreg_range_overflow` 源/目的双侧；`mreg_range_overlap` 含完全重合） | ✅已验 | `fp_check_*` 复用 034t helper | FL01–FL12 / FJ01–FJ05 / IG01–IG06 = `0x88`；注入 (d)/(e) 分别使 FL01–FL05 / FL06–FL09 FAIL |
| 5 | 舍入模式映射非恒等（`0→RNE,1→RTZ,2→RDN,3→RUP`） | ✅已验 | `rf0_round_mode` | FF21–FF28 / IF06–IF08 四种模式结果可区分；注入 (a) 使 FF22/FF24/FF27/IF07/IF08 FAIL |
| 6 | 标志合并掩码承重 | ✅已验 | `fp_status_commit` 的 `& 0x1F` | 注入 (b) 使 sNaN 用例 FF13/FF15 FAIL |
| 7 | f2i 饱和 + NV、且不置 NX | ✅已验 | `_round_to_zero` + `fp_status_commit_nv_only` | FI03–FI06 = max/min+NV；FI01/FI07 RF0 无 NX；注入 (c) 使 FI03–FI06 FAIL |
| 8 | i2f 舍入 + inexact NX；32 位源/结果符号性扩展 | ✅已验 | `helper_fp_cvt_i2f` | IF04/05/11/12/14/18/21/24 验证 NX；IF02/03/10/15/17 验证符号扩展；IF22/23 验证低位/高 32 忽略 |
| 9 | 是否引入 M1 回归 / 外部依赖 / 新 `cpu.h` 字段 | ✅已验 | 仅改 FP 相关 + `helper.c/h`；局部 `float_status` | 14 M1 探针 + `_034t` 与基线逐字节 IDENTICAL；`make check` EXIT=0；零新增依赖、零新字段 |
| 10 | 反例注入有效性/可复原（含重建） | ✅已验 | 5 处注入一轮 | `git diff --name-only` 非空；还原 porcelain 空、源码 sha 复原、**重建**后 113/113 |
| 11 | 合并注入「独立归因」（防抵消） | ✅已验 | 选 20 个单一归因 FAIL 用例；RTZ 承重改用可区分的 IF08/FF22 | 注入后**唯一**失败集 20 条，无意外/抵消 |
| 12 | `ft2ft`/`fo2ft`/`i2f-ft` 高 32 位口径与「按 32 位」冲突 | ⏸延后（口径） | 取「全 64 位搬移」并披露 | 见「口径选定 1」「新发现 1」 |
| 13 | `verify_derivations` 依赖后置定义的模块常量（运行时解析） | ✅已验 | `verify_derivations` 在 `--selftest` 中调用，常量此时已定义 | `--selftest` EXIT=0 |

**逻辑正确性核对**：
- `rf0_round_mode`：`(rf0>>32)&3` → `0:nearest_even / 1:to_zero / 2:down / 3:up`，与 `SimRISC-00 §浮点状态寄存器` 一致（非恒等）。
- `fp_status_init`：`memset` 归零 + 舍入模式 + `tininess_after_rounding`；局部 `float_status`，无 `cpu.h` 字段。
- `fp_status_commit`：`rf0[4:0] |= flags & 0x1F`（softfloat 低 5 位与 rf0 位对位一致）；`_nv_only` 仅 `float_flag_invalid`。
- `helper_fp_cvt_f2i`：8 分支均 `_round_to_zero`；32 位结果按 `int32→int64` 符号扩展 / `uint32→uint64` 零扩展；`fo2ft` 与 `i2f-ft` 结果 `(uint32_t)` 零扩展。
- `helper_fp_cvt_i2f`：`it` 取 `(int32_t)(uint32_t)src`（low32 符号扩展），`ut` 取 `(uint32_t)src`，`io/uo` 全 64 位。
- trans：三族均先做 `dst_rf0`（仅 ff/i2f）/双侧 `mreg`（zero+overflow）检查；`gen_convert_ff` 额外 `mreg_range_overlap`；块循环 `i` 升序、先读后写；`ft2ft/fo2fo` 用 `tcg_gen_mov_i64` 全 64 位搬移。
- 未改任何已有函数签名；未新增外部依赖；未动 `cpu.h`/`cpu.c`/`meson.build`/`insn.decode`/`opcodes.yaml`/合约/向量/lit。

**判决**：本任务范围内 finding 全部 ✅已修/已验；一条开放口径（#12）已披露并登记「遗留问题」。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查日期**：2026-10-03

---

##### 1. 重跑记录（独立执行，非采信 engineer 完成区）

| # | 验收项 | 命令 | 真实输出 | 退出码 | 判定 |
|---|--------|------|----------|--------|------|
| 1 | 探针全绿 | `python3 tools/qemu/min_rom_probe_036t.py` | `Main: 113/113 passed, 0 failed` / `Overall: PASS` | 0 | ✅ |
| 2 | 探针 selftest | `python3 tools/qemu/min_rom_probe_036t.py --selftest` | 5 类 FAIL 路径全部可达 + 28 条派生自检 PASS / `Self-test: PASS` | 0 | ✅ |
| 3 | check_qemu_trans | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)` | 0 | ✅ |
| 4 | make check | `make check` | semantics 149/149, lit 29/29, patch-tree 69, scope/fp-contract/no-residue PASS, repository checks: PASS | 0 | ✅ |
| 5 | 证据脚本默认 | `bash .work/evidence/QEMU-036t/run.sh` | trans/probe/selftest/patch-tree/source-state 全 PASS, OVERALL: PASS | 0 | ✅ |
| 6 | 证据脚本注入 | `bash .work/evidence/QEMU-036t/run.sh --inject` | 5 edits → rebuild → `93/113 passed, 20 failed` → 17 必需例全命中 → restore+rebuild → `113/113` / OVERALL: PASS | 0 | ✅ |
| 7 | M1 探针基线 | 14 个 M1 探针 + `_034t` + `_035t` | `_034t` 59/59 PASS, `_035t` 77/77 PASS; M1 探针预存在失败集（006t/008t/009t/010t/013t/028t）未变 | — | ✅ |
| 8 | 源码状态 | `check_patch_tree.py --source-state` | qemu: OK HEAD=750c12b8ccfc count=1 clean=True | 0 | ✅ |
| 9 | 残留检查 | `make check-no-residue` | `check-no-residue: PASS` | 0 | ✅ |
| 10 | 不变量零改动 | `git status --porcelain -- contracts spec tests/vectors components/llvm-project` | 空 | — | ✅ |

---

##### 2. 期望值独立性审查（铁律，§6.1）

探针 `verify_derivations()` 包含 28 条检查，**独立重跑全部 PASS**。来源分析：

| 类别 | 派生方法 | 独立于 QEMU/LLVM？ |
|------|----------|-------------------|
| fo2ft（17 例，含 RNE/RTZ/RDN/RUP 四种舍入） | `_round_mag_to_f32_bits()` + `fractions.Fraction` 精确有理数运算，从二进制浮点位模式逐位推导 | ✅ 纯数学 |
| ft2fo（1 例） | `struct.pack/unpack` 宿主 `float` 锚点（任务允许） | ✅ 宿主锚点 |
| NaN payload（1 例） | IEEE754 规则 `f32 mantissa << 29` | ✅ 手推 |
| it2ft 非 RNE（8 例） | `_derive_int_to_f32()` 有理数舍入器，四种模式逐例推导 | ✅ 纯数学 |
| f2i 边界（1 例） | `INT32_MAX/MIN` 等整型常量 + Python `int()` 截断行为 | ✅ 纯常量 |

**结论**：28 条派生检查均为第一性原理推导，**未使用 QEMU/LLVM 输出**。硬编码期望值由派生器生成并逐条校验，**不存在自证循环**。`--selftest` 的5个 FAIL 路径（RF 值/标志/RD 值/故障码/E2E exit-port）均可独立 FAIL，无恒真断言。

---

##### 3. 脚本审计（`.work/evidence/QEMU-036t/run.sh`）

**5 处注入审计**：

| 注入 | 改动位置 | 目的 | 非空？ | 可还原？ | 含重建？ | FAIL 路径 |
|------|---------|------|--------|---------|---------|----------|
| (a) | `helper.c` `rf0_round_mode` switch → identity | 舍入模式映射恒等 | ✅ | ✅ `git checkout` | ✅ | FF22/FF24/FF27/IF07/IF08 |
| (b) | `helper.c` `fp_status_commit` 移除 `& 0x1F` | 标志高位泄漏 | ✅ | ✅ | ✅ | FF13/FF15 |
| (c) | `helper.c` ft2it 改经 `float32_to_int64` 再截断 | 去饱和 | ✅ | ✅ | ✅ | FI03/FI04/FI05/FI06 |
| (d) | `trans_fp.c.inc` 删除 `fp_check_mreg_overlap` 体 | 去重叠检查 | ✅ | ✅ | ✅ | FL01/FL02 |
| (e) | `trans_fp.c.inc` `fp_check_dst_rf0(ctx, a->hb)` → `a->hc` | dst_rf0 字段错 | ✅ | ✅ | ✅ | FL06/FL07/FL08/FL09 |

**注入质量**：
- 5 处均使用精确文本替换（`sub()` 含出现次数校验），非空注入已由 `git diff --name-only` 验证。
- 还原使用 `git checkout -- .`，源码 sha 复原后**重建**（非仅源码还原），探针回绿113/113。
- 17 个 MUST_FAIL_CASES 逐例由单一注入独立触发（无交叉抵消）。额外3个失败（FL03/FL04/FL05）同属注入 (d) 范围。
- `check_probe inject 0` 逻辑：`PROBE_RC -ne 0`（非零退出）为 PASS，正确。

**结论**：脚本合格，FAIL 路径均可达，注入/还原/重建流程完整。

---

##### 4. reviewer 独立注入

**注入内容**：`helper.c` 的 `fp_status_commit` 函数，`& 0x1F` → `& 0x0F`（抑制 NX 标志 0x10 的传播）。

此注入**不同于**脚本自带5处——脚本注入 (b) 是移除整个掩码（让高位 snan 标志泄漏），而本注入是收窄掩码（让 NX 标志丢失）。两者方向相反、检测不同缺陷。

| 步骤 | 命令 | 真实输出 | sha256 |
|------|------|---------|--------|
| 注入前 | `sha256sum helper.c` | `1a723005aab9ae0c1d05108c9cd67b183b96d265df611414d097c6f7649f94cb` | — |
| 注入 | `python3 -c "…0x1F→0x0F…"` | `independent inject: 0x1F -> 0x0F applied` | — |
| 注入后 sha | `sha256sum helper.c` | `b7a7acdde0d670e15f9b4368e8b0cb42aae19326ad4afd22c308f699c3e67fb2` | ✅ 变更 |
| 注入后 diff | `git -C .work/source/qemu diff --name-only` | `target/dadao/helper.c` | ✅ 非空 |
| 重建 | `JOBS=8 make build-qemu` | `build-qemu: PASS` | — |
| 探针 | `python3 tools/qemu/min_rom_probe_036t.py` | `Main: 90/113 passed, 23 failed` / `EXIT=1` | ✅ 非零 |
| 失败集 | grep FAIL | FF08/FF09/FF10/FF11/FF21–FF28/IF04/IF05/IF06/IF07/IF08/IF11/IF12/IF14/IF18/IF21/IF24（23 例） | ✅ 全为 NX 依赖例 |
| 还原 | `git checkout -- .` | porcelain 空 | — |
| 还原后 sha | `sha256sum helper.c` | `1a723005aab9ae0c1d05108c9cd67b183b96d265df611414d097c6f7649f94cb` | ✅ 复原 |
| 还原重建 | `JOBS=8 make build-qemu` | `build-qemu: PASS` | — |
| 回绿探针 | `python3 tools/qemu/min_rom_probe_036t.py` | `Main: 113/113 passed, 0 failed` / `EXIT=0` | ✅ |

**结论**：独立注入非空、探针报 FAIL（23 例）、还原+重建后回绿。源码 sha 复原证据完整。

---

##### 5. 语义覆盖审查

| 语义维度 | 覆盖用例 | 审查 |
|----------|---------|------|
| 四种舍入模式（RNE/RTZ/RDN/RUP） | FF21–FF28（fo2ft）、IF06–IF08（it2ft） | ✅ 每种模式至少1例，结果可区分 |
| f→i 饱和（NaN/Inf/超范围→最大/最小+NV） | FI03/FI04/FI05/FI06（ft2it）、FI10–FI12（ft2io）、FI14–FI16（ft2ut）、FI18–FI20（ft2uo）、FI23–FI25（fo2it）、FI27/FI28（fo2io）、FI30（fo2ut）、FI32/FI33（fo2uo） | ✅ 4 种宽度 × NaN/Inf/超范围全覆盖 |
| f→i 截断方向（向零） | FI01（2.75→2）、FI02（-2.75→-2） | ✅ |
| f→i 不置 NX | FI01/FI07 RF0 无 NX 位 | ✅ 与任务书 §8-决策 2 一致 |
| i→f inexact (NX) | IF04/IF05/IF06/IF07/IF08/IF11/IF12/IF14/IF18/IF21/IF24 | ✅ |
| NaN payload 传播 | FF12（qNaN 缩窄）、FF14（qNaN 加宽）、FF13/FF15（sNaN→qNaN+NV） | ✅ 逐位验证 |
| sNaN→NV+qNaN | FF13（fo2ft sNaN）、FF15（ft2fo sNaN） | ✅ |
| 子正规/下溢 (UF) | FF08（2^-150→+0+UF\|NX）、FF09（1.25\*2^-149→subnormal+UF\|NX） | ✅ |
| ft2fo/fo2ft 宽度 | FF01–FF05（ft2fo）、FF06–FF11（fo2ft） | ✅ |
| ft2ft/fo2fo 位不变 | FF16（64位搬移 `0x12345678DEADBEEF`）、FF17–FF19 | ✅ |
| 源/目的重叠→ILLI | FL01（部分重叠）、FL02（完全重合） | ✅ |
| dst_rf0→ILLI | FL06–FL09（4 条 convert_ff）、IG01/IG02/IG06（convert_i2f） | ✅ |
| immu6 范围检查 | FL10/FL11/FL12、FJ01–FJ05、IG03–IG05 | ✅ |
| 块操作（先读后写） | FF05/FF18/FF19/IF22/FI34 | ✅ |

---

##### 6. 合法性审查

| 检查项 | 覆盖用例 | 审查 |
|--------|---------|------|
| `mreg_range_overlap`（含完全重合→ILLI 0x88） | FL01（部分）、FL02（完全重合）、FL03/FL04/FL05（各种重叠形态） | ✅ |
| `dst_rf0`（a->hb==0→ILLI） | FL06–FL09（ff）、IG01/IG02/IG06（i2f） | ✅ |
| `mreg_zero`/`mreg_range_overflow`（源+目的双侧） | FL11/FL12（dest/src 越界）、FJ02/FJ03/FJ05、IG04/IG05 | ✅ |
| 跨组不误报 | FF20（adjacent ranges legal, dest 4..6 src 7..9） | ✅ |

源码审查：`gen_convert_ff` 依次调用 `fp_check_dst_rf0` → `fp_check_mreg(hb)` → `fp_check_mreg(hc)` → `fp_check_mreg_overlap`；`gen_convert_f2i`/`gen_convert_i2f` 分别检查 rd/rf 双侧。正确。

---

##### 7. 3 处披露判定（spec 未明口径）

| # | 口径 | 工程师选定 | spec/contract 依据 | reviewer 判定 |
|---|------|-----------|-------------------|--------------|
| 1 | `ft2ft`/`fo2fo` 全 64 位搬移 | 全 64 位搬移（`tcg_gen_mov_i64`），不置标志 | spec「浮点寄存器间搬移」+ contract-fp §14 `set.ft` 展开为 `ft2ft`/`fo2fo` | **合理**。spec 未限 32 位；寄存器为 64 位；「格式 32 位」≠「搬移 32 位」。探针 FF16 用 `0x12345678DEADBEEF` 显式验证。任务书 §1.4「ft2ft 按 32 位」与 §6.2「位不变」字面冲突——取后者为正确解释。**不需返工**，但建议任务书修订时澄清。 |
| 2 | `convert_f2i` 向零截断 + 不置 NX | `_round_to_zero` + `fp_status_commit_nv_only`（仅传播 NV） | contract-fp.md §16：spec 未说 f2i 是否置 NX | **合理**。按「spec 未明不臆造」原则，仅传播 softfloat 的 `float_flag_invalid`（NV），不额外置 NX。softfloat `_round_to_zero` 对 inexact 会置 `float_flag_inexact`，工程师通过 `fp_status_commit_nv_only` 显式过滤。探针 FI01/FI07 验证 NX 未置。**不需返工**。 |
| 3 | NaN payload `尾数<<29`、sNaN⇒NV+qNaN | IEEE754 标准规则：加宽 `f32 mantissa << 29`，收窄保留高位；sNaN 输入置 NV 并返回 qNaN | spec「传播 payload」「sNaN⇒NV+qNaN」+ IEEE754 | **合理**。softfloat 默认行为即满足 spec，工程师未额外包装。探针 FF12–FF15 逐位验证。**不需返工**。 |

---

##### 8. 越界与残留

- `git diff --stat`：仅 5 文件（任务书/changelog/helper.c.patch/helper.h.patch/trans_fp.c.inc.patch），`min_rom_probe_036t.py` 为新文件。
- `git status --porcelain -- contracts spec tests/vectors components/llvm-project`：**空**。
- `check-no-residue`：PASS。
- `check-source-state`：qemu OK HEAD=750c12b count=1 clean=True。
- helper.c/helper.h 在任务书 §3 交付物清单内（#2/#3），不属越界。
- `.work/` 目录（evidence/log/source/build）为工作产物，不入库。

**结论**：零越界、零残留。

---

##### 9. 完成区一致性

逐条核对 engineer 完成区声明与 reviewer 独立验证：

| 完成区声明 | reviewer 验证 | 一致？ |
|-----------|--------------|--------|
| 探针113/113 PASS, EXIT=0 | ✅ 独立重跑113/113, EXIT=0 | ✅ |
| --selftest 五类 FAIL +28条派生自检 PASS | ✅ 独立重跑 | ✅ |
| run.sh 默认 EXIT=0 | ✅ 独立重跑 | ✅ |
| run.sh --inject EXIT=0,93/113 (20 FAIL),17 必需例全命中 | ✅ 独立重跑确认 | ✅ |
| check_qemu_trans227/227 EXIT=0 | ✅ | ✅ |
| make check EXIT=0 (sem149, lit29, patch-tree69) | ✅ | ✅ |
| M1 探针 + _034t (59/59) + _035t (77/77) 基线 IDENTICAL | ✅ _034t 59/59, _035t 77/77 | ✅ |
| helper.c sha: `1a723005…` | ✅ | ✅ |
| trans_fp.c.inc sha: `89cc81d0…` | ✅ | ✅ |
| 补丁69不变 | ✅ patch-tree69 | ✅ |
| 口径选定1/2/3 已披露 | ✅ 逐条审查，见§7 | ✅ |

---

##### 10. 判决

**Accepted**。

所有验收命令在 reviewer 独立重跑下全部通过；脚本审计5处注入合格；reviewer 独立注入（`0x1F→0x0F`）确认探针可失败且还原含重建后回绿；3处披露判定均为合理口径，无臆造；零越界、零残留；完成区与真实输出逐条一致。

#### 第 1 轮 architect 交叉复核（§2.5 统一验收报告）

**复核者**：architect 子代理（deepseek/deepseek-flash）
**复核日期**：2026-10-03
**复核方式**：对照任务书 §1–§9 与 reviewer「第 1 轮 reviewer 验收」逐项比对；自行重跑关键项；**自行独立注入一处 reviewer/engineer 均未覆盖的反例**并还原+重建。

##### A. 独立重跑（不采信任何叙述）

| # | 项目 | 命令 | 真实输出 | 退出码 | 日志 |
|---|------|------|----------|--------|------|
| 1 | 探针全绿 | `python3 tools/qemu/min_rom_probe_036t.py` | `Main: 113/113 passed, 0 failed` / `Overall: PASS` | 0 | `.work/log/qemu/QEMU-036t-arch-probe.log` |
| 2 | 探针自检 | `... --selftest` | 5 类断言 FAIL 路径可达 + 28 条派生自检 PASS / `Self-test: PASS` | 0 | `.work/log/qemu/QEMU-036t-arch-selftest.log` |
| 3 | `-d cpu` 回读抽查 | 上表 #1 日志明细 | `FF22` RF[00]=`0x7FF800037FC00010` / RF[04]=`0x000000003F800001`；`FI01` RD[04]=`0x...02`；`FI05` RD[04]=`0xFFFFFFFF80000000` **均为真实寄存器读回（expect=got）** | — | 同上 |
| 4 | 期望值手算独立核对 | 手工推导 3 组 | ① NaN 加宽 `0x412345<<29=0x82468A000000` ⇒ `0x7FF82468A0000000` ✓；② `1+2^-24` RNE→`0x3F800000`/RUP→`0x3F800001` ✓；③ it2ft `2^24+3` RNE/RUP→`0x4B800002`、RDN/RTZ→`0x4B800001`，`2^24+1` RNE→`0x4B800000` ✓ | 全一致 | — |

##### B. architect 独立注入（与 engineer 5 处、reviewer 1 处均不同）

**注入内容**：`helper.c` 的 `helper_fp_cvt_f2i` case 0（`ft2it`），把**向零截断** `float32_to_int32_round_to_zero(f32,&st)` 改为**就近舍入** `float32_to_int32(f32,&st)`——测试任务 §8-决策 2 / 完成区口径 2 的「f→i 向零截断」承重性（engineer 注入 (c) 测饱和、reviewer 注入测 NX 掩码，**均未覆盖截断方向**）。

| 步骤 | 命令 | 真实输出 | 退出码 |
|------|------|----------|--------|
| 注入前 sha | `sha256sum helper.c` | `1a723005aab9ae0c1d05108c9cd67b183b96d265df611414d097c6f7649f94cb` | — |
| 注入 | 精确文本替换（含出现次数=1 校验） | `architect independent inject: ft2it _round_to_zero -> round-nearest applied` | — |
| 注入后 diff | `git -C .work/source/qemu diff --name-only` | `target/dadao/helper.c`（**非空**） | — |
| 注入后 sha | `sha256sum helper.c` | `6a4a473df196367b0d458269dacf21644639ec3c212ab10666f5b413225f75f6`（变更） | — |
| 重建 | `JOBS=8 make build-qemu` | `build-qemu: PASS` | 0 |
| 探针 | `python3 tools/qemu/min_rom_probe_036t.py` | `Main: 109/113 passed, 4 failed`，失败集恰 **`FI01 FI02 FI34 E3`**（全为 2.75/−2.75 截断相关；NaN/Inf/饱和用例不受影响，符合预期） | **1** |
| 还原 | `git -C .work/source/qemu checkout -- .` | `porcelain:[]`（空） | — |
| 还原后 sha | `sha256sum helper.c/helper.h/trans_fp.c.inc` | `1a723005…` / `1ab89af7…` / `89cc81d0…`（**逐字节复原**） | — |
| 还原重建 | `JOBS=8 make build-qemu` | `build-qemu: PASS` | 0 |
| 回绿 | `python3 tools/qemu/min_rom_probe_036t.py` | `Main: 113/113 passed, 0 failed` / `Overall: PASS` | 0 |

日志：`.work/log/qemu/QEMU-036t-arch-{inject-build,inject-probe,restore-build,restore-probe}.log`。

##### C. 源码/覆盖复核（对照任务书）

- **语义**：`helper_fp_cvt_f2i` 8 分支均 `_round_to_zero`、`fp_status_commit_nv_only` 仅传播 `float_flag_invalid`（对照 `softfloat-types.h` L159 位 0，实测 FI03–FI06/FI15/FI23 等 NV 均置起）；`helper_fp_cvt_i2f` 32 位源/结果按 `it` 符号扩展、`ut` 零扩展（对齐 M1）。与任务 §1.3/§8-决策 2 一致。
- **legality 顺序**：`gen_convert_ff` = `dst_rf0 → mreg(dest) → mreg(src) → overlap`；`gen_convert_f2i` = `mreg(dest) → mreg(src)`；`gen_convert_i2f` = `dst_rf0 → mreg(dest) → mreg(src)` —— 与任务 §2.2 完全一致（overlap 仅 convert_ff）。
- **20 条覆盖**：探针逐条调用 `ft2ft/ft2fo/fo2ft/fo2fo/ft2it/ft2io/ft2ut/ft2uo/fo2it/fo2io/fo2ut/fo2uo/it2ft/io2ft/ut2ft/uo2ft/it2fo/io2fo/ut2fo/uo2fo` **各 ≥2 例**，值/fault/E2E 三通道齐备。
- **不变量**：reviewer 所列 `contracts/**`/`spec/**`/`tests/vectors/**`/`components/llvm-project/**` 零改动，`check_qemu_trans 227/227`、`make check` EXIT=0、patch-tree 69，与任务 §9 期望表一致。

##### D. 与 reviewer 的共识 / 分歧 / 补充发现

- **共识**：20 条实现、softfloat 接入骨架、期望值独立性、反例门控、3 处 spec 未明口径判定——architect 独立重跑与手算核对后**全部认同**。
- **过严/过松判定**：reviewer **无过严**（未要求任务书外事项）；**无关键遗漏**（§6 验收 1–7 逐条有独立证据；§2.5 要求的「既有 Accepted 仍需交叉复核」本记录补齐）。
- **补充发现（非阻断）**：`fp_status_init` 采用 `float_tininess_after_rounding` 判定 UF——`spec/SimRISC-07`/`contract-fp.md` **未规定** tininess 检测时机，属完成区未列的第 4 处 spec 开放点（当前实现取 QEMU 默认 after-rounding，与探针 FF08（`2^-150→+0+UF|NX`）/FF09（`1.25*2^-149→subnormal+UF|NX`）期望自洽）。**建议**：随 3 处口径一并登记 `deferred.md`，供 `SPEC-089t`/FP oracle 参照；不影响本任务验收。

##### E. 最终判决

**确认 Accepted**。reviewer 判决「无遗漏、不过严、不过松」经 architect 独立重跑 + 独立注入（截断方向）证伪路径验证后成立；完成区与真实输出逐条一致，无未处置 finding，无越界/残留。**状态置 `已验证`**。
