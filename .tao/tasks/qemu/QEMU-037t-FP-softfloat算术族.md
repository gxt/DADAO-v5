# QEMU-037t: FP softfloat 算术族（arith 12 + root 2 = 14 条）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`QEMU-034t`（**必须先 `已验证`**）、`QEMU-036t`（**必须先 `已验证`**：提供 `fp_status_init`/`fp_status_commit`/舍入映射）。相关：`SPEC-087t`（合约）。
**状态**：待开始

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景与范围

- 本棒 4 任务之一（拆分见 `QEMU-034t §0`），也是**收口任务**：完成后 `scope: fp` 60 条全部真实执行。
- 实现 **14 条**：`ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb`、`foadd/fosub/fomul/fodiv/forem/fosclb`（arith 12）+ `ftroot/foroot`（root 2）。
- 只改 `trans_fp.c.inc` + `helper.c` + `helper.h`。

---

## 1. 事实核实（本轮 architect 实测）

### 1.1 现有桩（`QEMU-034t` 后位于 `trans_fp.c.inc`）
`ftadd`/`ftsub`/`ftmul`/`ftdiv`/`ftrem`/`ftsclb`、`foadd`/`fosub`/`fomul`/`fodiv`/`forem`/`fosclb`、`ftroot`/`foroot`。

### 1.2 字段/编码（`contracts/opcodes.yaml`）
- arith（orrr）：目的 `rfhb`=a->hb，源 `rfhc`=a->hc、`rfhd`=a->hd。
- root（orri）：目的 `rfhb`=a->hb，源 `rfhc`=a->hc，`immu6`=a->hd（=n，**仅 2**）。

### 1.3 语义（`contract-fp.md §5/§6`；`spec/SimRISC-07 §S2D1 / §S1D1`）
- S2D1：硬件先读全部源再写结果（源被目的覆盖前已捕获）。NV/DZ/OF/UF/NX 按 IEEE754。
- `ftrem`/`forem`：IEEE754 remainder（`rfHC − n×rfHD`，n 为最近整数，**平局取偶**）；除零/Inf/NaN 遵循 IEEE754。
- `ftsclb`/`fosclb`：scaleB `rfHC × 2^rfHD`（**rfHD 取整数值**），舍入由 rf0；NaN/Inf/溢出/下溢遵循 IEEE754。
- `ftroot`/`foroot`：`rootn(x, n)`，n 存 `immu6`，**仅 n=2**；其他 n ⇒ ILLI。`rootn(-0, 2)` **不做具体要求**（`contract-fp.md §16`）。
- 目的 rf0 ⇒ ILLI（`dst_rf0`；arith 12 + root 2 = 14 条全部适用）。

### 1.4 softfloat 接口映射
| 指令 | ft (32) | fo (64) |
|---|---|---|
| add/sub/mul/div | `float32_add/sub/mul/div` | `float64_add/sub/mul/div` |
| rem | `float32_rem` | `float64_rem` |
| root (n=2) | `float32_sqrt` | `float64_sqrt` |
| scalb | `float32_scalbn(x, n, st)` | `float64_scalbn(x, n, st)` |

- `n` 来源：`ftsclb`/`fosclb` 的 rfHD 为浮点格式数，须**先按其格式转整数**（`float32_to_int32` / `float64_to_int32`，再传给 `scalbn`）；`immu6` 仅用于 root 的 n。
- 舍入/标志：复用 `QEMU-036t` 的 `fp_status_init`/`fp_status_commit`（映射与 `& 0x1F` 见 `QEMU-034t §1.4`）。

### 1.5 高风险/未明点（spec 开放，`contract-fp.md §16`）
- `ftrem`/`forem`、`ftsclb`/`fosclb` 在**除零/Inf/NaN** 的逐位细则按 IEEE754，spec 未展开。
- `rootn(-0, 2)` 结果**不做具体要求** ⇒ 不设期望值（或接受任一结果）。
- NaN payload 传播细则同 `QEMU-036t §1.5`。
- `ftsclb` 的 rfHD 转换（浮点→整数）在 rfHD 为 NaN/Inf 时的行为按 IEEE754 / softfloat，须实测并记录。

---

## 2. 设计

### 2.1 实现（`trans_fp.c.inc` + helper）
- 每条 trans：**先查 `a->hb==0`（`dst_rf0`）⇒ ILLI**；再调 `gen_helper_fp_arith_*` / `gen_helper_fp_root_*`，helper 内 `fp_status_init` → softfloat → 结果写回 rf（`store_rf`，rf0 已被前置检查排除）→ `fp_status_commit`。
- helper 粒度：建议按「操作 + 格式」或「操作族」组织；`arith` 可用统一 helper（传 opc）或逐个，由 engineer 定并在完成区说明。**根**（root）单独 helper（需查 n）。
- `root`：translate 期先查 `a->hd != 2` ⇒ ILLI（`encode_fp_root_n`），再实现 sqrt。
- 源/目的是 rf 同组，arith 无 immu6 → 无 `mreg_*` 检查（root 的 `immu6` 是 n，非连续个数，**不适用** `mreg_zero`/`mreg_range_overflow`）。
- 读写顺序：先 `load_rf` 全部源到 TCG temp，再 `store_rf` 目的（防源被覆盖）。

### 2.2 不改动
不动 `cpu.h`/`cpu.c`/`meson.build`/`insn.decode`/`opcodes.yaml`/合约；不加向量/lit。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `target/dadao/insn_trans/trans_fp.c.inc` | 14 条 stub → 真实实现 |
| 2 | `target/dadao/helper.h` | 新增 FP 算术/root helper 声明 |
| 3 | `target/dadao/helper.c` | 新增算术/root helper（复用 `QEMU-036t` 骨架） |
| 4 | `components/qemu/patches/**` + `series` | `make_patch qemu`（预期无新增补丁，仍 32/69） |
| 5 | `components/qemu/changelog.md` | 追加一条（FP 60 条收口） |
| 6 | `tools/qemu/min_rom_probe_037t.py` | 新建探针（§6.2） |
| 7 | 独立期望值参考（见 §6.1） | 落 `tools/qemu/` 或探针内（非 LLVM/QEMU 来源） |
| 8 | `.work/evidence/QEMU-037t/run.sh` | 一键证据脚本（含 `--inject`） |
| 9 | `.work/log/qemu/QEMU-037t-*.log` | 构建/探针/回归完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tests/**`、`components/llvm-project/**`、`cpu.h`/`cpu.c`/`meson.build`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `contracts/opcodes.yaml`（14 条 id 的 `fields`）
- `.tao/knowledge/contract-fp.md §5/§6、§16`、`spec/SimRISC-07 §S2D1 / §S1D1`
- `QEMU-034t`/`QEMU-036t` 产出；`include/fpu/softfloat.h`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围，越界须披露；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare` + `make build-qemu`（**预计 3–8 分钟**）。
- 临时目录 `/tmp/opencode/QEMU-037t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-037t/`。
- 补丁纪律同 `QEMU-034t §5`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-qemu` EXIT 0（留日志）。
2. **探针全绿**：`python3 tools/qemu/min_rom_probe_037t.py` EXIT 0。用例至少覆盖：
   - **add/sub/mul/div**（ft/fo）：正常值（结果精确）+ 四种舍入模式各一例；`1/0` ⇒ ±Inf + **DZ**；`0/0`、`inf-inf`、`inf×0` ⇒ qNaN + **NV**；溢出 ⇒ ±Inf + **OF**；下溢 ⇒ **UF**（+NX）。
   - **rem**（ft/fo）：非平局与**平局取偶**各一例；除零/Inf/NaN 按 IEEE754（记录实测）。
   - **scalb**（ft/fo）：`x×2^n` 精确；n 为负；溢出/下溢；rfHD 为整数浮点值（含负数 n）。
   - **root**（ft/fo）：`ftroot rfX, rfY, 2` 精确平方根（如 4.0→2.0）；负数 ⇒ qNaN+NV；`n!=2`（如 1/3/0）⇒ **ILLI 0x88**；`immu6` 字段为 n 的验证。
   - **`dst_rf0`**：14 条各取一条，目的 rf0 ⇒ ILLI 0x88。
   - **先读后写**：`ftadd rf4, rf4, rf5`（源含目的）结果确定、与 `ftadd rf6, rf4, rf5` 一致。
3. **反例可失败（承重证明）**：至少注入并**重建**后 FAIL、还原后**重建**回绿：
   - (a) `ftdiv` 用 `float32_mul` 实现 ⇒ div 用例 FAIL；
   - (b) `ftrem` 用 `fmod` 式截断而非 IEEE 平局取偶 ⇒ 平局用例 FAIL；
   - (c) `root` 的 n 检查写成 `a->hd != 2` → `a->hd < 2` ⇒ n=3 用例由 0x88 变其它（证明 n=2 精确约束承重）；
   - (d) 去掉 `dst_rf0` 检查 ⇒ 目的 rf0 用例 FAIL；
   - (e) `ftsclb` 把 rfHD 当整数位直接取（不转浮点→整数）⇒ scalb 用例 FAIL。
   注入 `git diff --name-only` 非空；还原须**源码 + 重建**。
4. **不误伤 M1**：既有 M1 探针与 `_034t`/`_035t`/`_036t` 失败集零新增。
5. **编码门控不回归**：`check_qemu_trans` `227/227 (M1 152/152)` EXIT 0。
6. **`make check` 全绿**：`check-qemu-semantics` 149、`check-lit` 29/29、`check-patch-tree` 69 OK、`check-scope`/`check-fp-contract` PASS。
7. **FP 收口核对**：`scope: fp` 60 条**全部**无 ILLI 桩（`grep` 证据：`trans_fp.c.inc` 内 60 个 trans 均非「stub: ILLI」），并在完成区给出计数。
8. **残留/越界/不变量**：`git status --untracked-files=all` 干净；`check-no-residue` PASS；base+1 干净；改动与 §3 对齐。

### 6.1 独立期望值来源（铁律）
同 `QEMU-036t §6.1`：不得由 LLVM/QEMU 生成；优先 `GOLDEN-001t` oracle，否则任务内独立派生（RNE 用 `struct`/`float` 交叉锚点，非 RNE + 标志用精确有理数并逐例手算复核），来源与推导写入完成区。`rootn(-0,2)` 标 `UNSPECIFIED`、不设期望。

### 6.2 探针构造注意
同 `QEMU-034t §6.2`。浮点输入须用 `rd2rf`/`ld.o-rf` 构造**已知位模式**；期望值写死，禁反填。四种舍入模式用例须有鉴别力（结果互不相同）。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-037t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/qemu/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/QEMU-037t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **`ft` 高 32 位口径**：承 `QEMU-034t §8-决策 3`。
2. **`rootn(-0,2)` 不设期望**（spec 明确不要求）；`rem`/`scalb` 的 NaN/Inf 细则按 softfloat 实测记录（spec 未展开）。
3. **独立 oracle 先后**：承 `QEMU-036t §8-决策 3`（本棒头号待拍板项）。
4. **ADR**：承 `QEMU-034t §8-决策 4`（建议不立，请确认）。
5. **`ft` 与 softfloat 的 NaN/UF 约定**：spec 开放；实现选定并记录，不自称 spec 保证。

## 9. 与现有门控/不变量的关系

| 门控 | 期望变化 |
|---|---|
| `check_qemu_trans` | 不变 `227/227` |
| `check-qemu-semantics` | 不变 149 |
| `check-lit` | 不变 29/29 |
| `check-patch-tree` | 不变 **69** |
| `check-scope`/`check-fp-contract`/`validate-encoding` | 不变 PASS |
| 探针群 | 新增 `_037t`；M1 与 `_034t`~`_036t` 零新增失败 |

---

## 10. 后续衔接（本棒收尾之外的后续，均不在本棒）
- `SPEC-089t`：FP `rule_refs` 回填 + `dst_rf0`/`encode_fp_root_n` 翻 `active` + 重跑 `gen_legality_list`。
- `GOLDEN-*`（独立 oracle）、`TESTCASES-024t`（FP 向量/inventory）、`INTEG-*`（FP E2E）。

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
