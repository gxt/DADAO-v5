# QEMU-037t: FP softfloat 算术族（arith 12 + root 2 = 14 条）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`QEMU-034t`（**必须先 `已验证`**）、`QEMU-036t`（**必须先 `已验证`**：提供 `fp_status_init`/`fp_status_commit`/舍入映射）。相关：`SPEC-087t`（合约）。
**状态**：已验证

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

**测试结果**：探针 `tools/qemu/min_rom_probe_037t.py` **91/91 PASS，EXIT=0**；`--selftest` 四类断言 FAIL 路径可达 + **40 项期望值独立派生自检**（`verify_derivations()`，精确有理数/整数开方，无 LLVM/QEMU）全部 PASS，EXIT=0；一键证据 `.work/evidence/QEMU-037t/run.sh` 默认 **EXIT=0**（check_qemu_trans 227/227、探针 91/91、selftest、17 个回归探针逐字节 IDENTICAL、patch-tree 69、source-state、ILLI 桩计数=4）；`run.sh --inject` **EXIT=0**（5 处注入→重建→**62/91、29 FAIL**、23 个必需例全命中→还原清洁→源码 sha 复原→**重建**→91/91）；`check_qemu_trans` **227/227 (M1 152/152)**；`make check` **EXIT=0**（semantics 149/149、lit 29/29、patch-tree 69、scope/fp-contract/no-residue PASS）；M1 探针 14 个 + `_034t`/`_035t`/`_036t` 与 pre-037t 基线**逐字节 IDENTICAL**。构建 `JOBS=8 make build-qemu` EXIT=0（增量，见 `.work/log/qemu/QEMU-037t-build*.log`）。

**修改文件**：
1. `.work/source/qemu/target/dadao/helper.c` — 474→**571 行**：新增 `helper_fp_arith`（kind 0..5 ft / 6..11 fo，经 `float32/64_{add,sub,mul,div,rem,scalbn}`）与 `helper_fp_root`（ft/fo sqrt）；`fp_status_init` 补 `set_float_default_nan_pattern(0b01000000)`（见「新发现 1」）。
2. `.../helper.h` — 28→**32 行**：`DEF_HELPER_4(fp_arith, i64, env, i64, i64, i32)`、`DEF_HELPER_3(fp_root, i64, env, i64, i32)`。
3. `.../insn_trans/trans_fp.c.inc` — 928→**968 行**：14 条 ILLI 桩 → 真实实现；新增 `FP_AR_*` kind 枚举、`gen_fp_arith`（先读全源再写目的，`dst_rf0`⇒ILLI）、`gen_fp_root`（`a->hd != 2`⇒ILLI，`dst_rf0`⇒ILLI）；头注释同步（FP 60/60 全落地）。
4. `components/qemu/patches/target/dadao/{helper.c,helper.h,insn_trans/trans_fp.c.inc}.patch` — `python3 tools/infra/make_patch.py qemu` 重生成（577/38/974 行；**无新增补丁**，qemu 仍 32、全仓仍 **69**）。
5. `components/qemu/changelog.md` — 追加 `QEMU-037t` 一条（FP 60 条收口）。
6. `tools/qemu/min_rom_probe_037t.py` — **新建**（91 用例 + `--selftest` + 独立派生 oracle）。
7. `.work/evidence/QEMU-037t/run.sh` + `baseline/` — 一键证据脚本。

**FP 60/60 全实现汇总核对**：`trans_fp.c.inc` 内 `static bool trans_` 计数 = **60**；`gen_exception_illegal` 仅 **4** 处（3 个共享合法性 helper + root 的 n 检查），**无残留 ILLI 桩**；`check_qemu_trans` **227/227 (M1 152/152)**；探针族 `_034t` 59/59、`_035t` 77/77、`_036t` 113/113、`_037t` 91/91。**16+10+20+14 = 60/60**。

**验收结果**（真实命令 + 退出码）：

| # | 命令 | 输出 / 退出码 | 结论 |
|---|---|---|---|
| 1 | `JOBS=8 make build-qemu`（`QEMU-037t-build2.log`） | `[3/3] Linking target qemu-system-dadao`；`build-qemu: PASS`，EXIT=0 | ✅ |
| 2 | `python3 tools/qemu/min_rom_probe_037t.py` | `Main: 91/91 passed, 0 failed`；`Overall: PASS`，EXIT=0 | ✅ |
| 3 | `python3 tools/qemu/min_rom_probe_037t.py --selftest` | 4 类断言 FAIL 路径 + 40 项派生自检全 PASS，EXIT=0 | ✅ |
| 4 | `bash .work/evidence/QEMU-037t/run.sh` | `OVERALL: PASS`，EXIT=0（含 check_qemu_trans 227/227、17 回归 IDENTICAL、patch-tree 69、source-state、桩计数 4） | ✅ |
| 5 | `bash .work/evidence/QEMU-037t/run.sh --inject` | `OVERALL: PASS`，EXIT=0；注入后 `62/91 passed, 29 failed`，23 必需例全命中；还原后 91/91、源码 sha 复原 | ✅ |
| 6 | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)`，EXIT=0 | ✅ |
| 7 | `make check`（`QEMU-037t-make-check.log`） | `Results: 149 total, 149 passed`；lit `Passed: 29`；`check-patch-tree: 69 patches OK`；`check-scope`/`check-fp-contract`/`check-no-residue` PASS；`repository checks: PASS`，EXIT=0 | ✅ |
| 8 | 回归探针 17 个 vs pre-037t 基线 | 全部 `IDENTICAL`（含预存在失败 006t/008t/009t/010t/013t/028t） | ✅ |
| 9 | `python3 tools/infra/check_patch_tree.py --source-state` | `qemu: OK HEAD=cf13beb9b9d2 count=1 clean=True` | ✅ |
| 10 | 不变量（`contracts spec tests/vectors components/llvm-project cpu.h Makefile`） | `git status --porcelain` 空 | ✅ |

反例承重（`--inject`，每处注入独立归因、无抵消）：
- (a) `ftdiv`→`float32_mul` ⇒ FAIL：`AR04 AR17 AR18 AR19 AR21`；
- (b) `ftrem`→fmod 式截断（用临时 status，纯值差异）⇒ FAIL：`RE02 RE05 RE06 RE07`；
- (c) root n 检查 `!= 2`→`< 2` ⇒ FAIL：`RO12 RO14`（n=3；n=1/0 仍 ILLI）；
- (d) `fp_check_dst_rf0` 关闭 ⇒ FAIL：`DR01–DR14 RO16 RO17`；
- (e) `ftsclb` 取 rfHD 原始位 ⇒ FAIL：`SC01 SC02`。
注入后**唯一**失败集 = 上述 29 条，无意外/抵消；`git diff --name-only` 非空；还原后 `git status --porcelain` 空、`helper.c`/`trans_fp.c.inc` 源码 sha 复原（`15660d2b…`/`20d0de2c…`）、重建后 91/91。

**独立期望值来源（铁律，§6.1）**：全部期望值由**探针内精确有理数 oracle**（`fractions.Fraction` + 通用 round-to-format + `math.isqrt`）独立派生，**未用 LLVM/QEMU 生成**：
- 有限 add/sub/mul/div：精确结果按 rf0 四舍入模式 round；四个舍入模式用**正/负混合输入**取得 4 个互不相同的结果（RNE/RTZ/RDN/RUP）。
- `rem`：按 `x − n·y`，n 为最近整数、**平局取偶**（`3 rem 2 == −1`，fmod 会给 `+1`）；符号随被除数（`−5 rem 2 == −1`）。
- `scalb`：`x × 2^n`（n = rfHD 的整数值）；精确/溢出/下溢分别推导。
- `root`：整数开方后 round；`sqrt(4)=2`、`sqrt(2)=0x3FB504F3`（ft）/`0x3FF6A09E667F3BCD`（fo）。
- 标志（NV/DZ/OF/UF/NX）按 IEEE754 手推：`1/0`⇒DZ、`0/0`/`inf−inf`/`inf×0`/`rem(1,0)`/`rem(inf,2)`/`sqrt(−4)`⇒NV、`max+max`⇒OF|NX、`2^-149×0.5`⇒UF|NX。

**新发现/坑**：
1. **`fp_status_init` 必须设 `set_float_default_nan_pattern`**（否则 invalid 运算结果畸形/断言失败）：`memset(st,0)` 后 `default_nan_pattern==0`，而 `fpu/softfloat-parts.c.inc::partsN(default_nan)` 有 `assert(dnan_pattern != 0)`。QEMU-036t 的转换族不产生 default NaN 故未暴露；本任务算术族的 `0/0`、`inf−inf`、`rem`-invalid、`sqrt(−x)` 会命中。取 `0b01000000` 使 default NaN = FCSR qNaN(ft/fo) 模式（`0x7FC00000` / `0x7FF8000000000000`），与 035t 的 `FP_FT_QNAN`/`FP_FO_QNAN` 一致。**建议沉淀**：任何新增 softfloat 目标都必须显式设 `default_nan_pattern`。
2. **softfloat `rem` 语义**：`float32/64_rem` 即 IEEE754 remainder（`frac64_modrem` 的 `q & 1` 实现平局取偶）；`rem(x,0)`/`rem(inf,y)` 置 **NV（非 DZ）**，`rem(x,inf)=x`。
3. **`scalb` 的 n 的取整**：`floatXX_to_int32` 按当前 rf0 舍入模式取整；rfHD 非整数值时该转换会置 NX（`float_to_sint` 对分数置 inexact）——spec §S2D1 仅说「取整数值」，未展开，属开放口径（本任务测试仅用整数值 rfHD）。
4. **构建非字节确定**：同一源码两次增量重建的 `qemu-system-dadao` sha **不同**（`d893a18e…`→`e5e5cfd9…`），故「复原」证据以**源码 blob sha + 行为（91/91）**为准，不用二进制 sha。
5. `float32_rem` 等无效结果使用 default NaN，而**不依赖输入 NaN 的 payload**（输入 NaN 传播仍按 pick_nan）。

**遗留问题**：
- ⏸延后（spec 开放，非缺陷）：`rootn(−0,2)` 结果**不设期望**（`contract-fp.md §16`/`SimRISC-07 §S1D1` 明确不要求）；探针 RO06 仅断言「不触发 fault 且不置 NV」。
- ⏸延后（spec 开放，非缺陷）：`rem`/`scalb` 在 NaN/Inf/子正规的逐位细则 spec 未展开，实现/期望均按 softfloat 行为并记录（`新发现 2/3`）。
- ⏸延后（承前任务口径）：ft 结果高 32 位 **零扩展**（承 `QEMU-036t` 口径）；`rootn(−0,2)` 实测得 `−0`（未断言）。
- ⏸延后（范围外，任务书未列）：未新增 `GOLDEN-*` 独立 oracle；以「探针内独立派生 + 反例门控」承担（承 `QEMU-034t/036t §8`）。
- ✅已修：本任务范围内 finding 全部处置（见自审表），无未修项。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`.work/source/qemu/target/dadao/{helper.c,helper.h,insn_trans/trans_fp.c.inc}`、`tools/qemu/min_rom_probe_037t.py`、`.work/evidence/QEMU-037t/run.sh`（自主逐行审查；全局 `subagent_depth=1`，engineer 无法再起嵌套子代理）。

**逐项核对**：

| # | 审查点 | 判决 | 证据 |
|---|---|---|---|
| 1 | 14 条 trans 全部真实、无残留 ILLI 桩 | ✅ | `grep '^static bool trans_'`=60；`gen_exception_illegal` 仅 4 处（合法性 helper+root n 检查） |
| 2 | `dst_rf0` 运行期检查覆盖 14 条 | ✅ | `gen_fp_arith`/`gen_fp_root` 首行 `fp_check_dst_rf0`；DR01–14 探针 + 注入 (d) 全 FAIL |
| 3 | 先读后写（源可含目的） | ✅ | `gen_fp_arith` 先 `load_rf` 两个源到 temp 再 `store_rf`；RW01/RW02 通过 |
| 4 | root 仅 n=2，`immu6` 为 n | ✅ | `gen_fp_root` `if (a->hd != 2)`；RO11–15（n=1/3/0⇒ILLI）+ 注入 (c) |
| 5 | 舍入/标志复用 036t 骨架 | ✅ | `fp_status_init`/`fp_status_commit` 直接复用；四模式 AR09–16 互异 |
| 6 | `default_nan_pattern` 缺失风险 | ✅已修 | 自审发现，补 `set_float_default_nan_pattern(0b01000000)`；`0/0`⇒`0x7FC00000` 实测 |
| 7 | 每条断言/用例可达 FAIL | ✅ | `--selftest` 4 类 + `--inject` 29 FAIL 独立归因；无恒真/两支同值 |
| 8 | 期望值独立性 | ✅ | 40 项 `verify_derivations()` 精确有理数重算全 PASS；未查询 LLVM/QEMU |
| 9 | 探针寄存器构造可回读 | ✅ | 用 `set.zw`+`or.w`+`rd2rf` 构造已知位模式；关键用例 `-d cpu` 回读 |
| 10 | 反例注入有效且可复原 | ✅ | `git diff --name-only` 非空；还原 `porcelain` 空 + 源码 sha 复原 + **重建**后 91/91 |
| 11 | 回归零新增失败 | ✅ | 17 探针 vs 基线逐字节 IDENTICAL |
| 12 | 越界/不变量 | ✅ | 仅动授权文件 + 任务书列出的 changelog；`contracts/spec/tests/llvm-project/cpu.h/Makefile` 零改动 |

**finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `fp_status_init` 未设 `default_nan_pattern`（0），invalid 运算会畸形/触发断言 | ✅已修 | helper.c 增 `set_float_default_nan_pattern(0b01000000, st)` | `0/0`/`inf−inf`/`rem(1,0)`/`sqrt(−4)` 均得 `0x7FC00000`（ft）/`0x7FF8000000000000`（fo）；AR21/22/23/24/25/26、RE05/06/11/12、RO03/09 通过 |
| F2 `helper_fp_arith` `default` 分支兼作 kind=11，kind≥12 静默走 fosclb | ⏸延后 | 无（调用方 kind 均为编译期常量，不可达） | 14 个 trans 各传固定 kind，`check_qemu_trans` 227/227；无需运行期兜底（KISS） |
| F3 `scalb` 的 n 非整数时转换置 NX（spec 开放点） | ⏸延后（口径） | 无（任务书 §1.4 指定 `floatXX_to_int32`） | 测试仅用整数 rfHD；已在「新发现 3/遗留」披露 |
| F4 证据脚本桩计数检查 rc 显示为 4（grep 计数） | ❌不修 | 无 | 该行 actual/expected 均为 4 判 PASS；rc 字段仅为展示，不影响门控 |

**逻辑正确性核对**：
- `gen_fp_arith`：`src1=load_rf(hc)`、`src2=load_rf(hd)` 均先于 `store_rf(hb)`；helper 返回后再写目的 → 源被目的覆盖前已捕获（S2D1）。
- `gen_fp_root`：`dst_rf0` 检查 → `a->hd != 2` ILLI → 读源 → helper → 写目的（S1D1）；dbl 选择 `isdbl`。
- `helper_fp_arith`：ft 分支一律 `(uint32_t)` 零扩展、fo 分支完整 64 位；`scalb` 的 n 由对应格式整数化；末尾统一 `fp_status_commit`。
- `helper_fp_root`：`isdbl` 选择 `float64_sqrt`/`float32_sqrt`，格式转换一致。

**判决**：全部 finding 已修或按 spec/任务书口径显式延后（附理由）；无未修缺陷。状态置 **待验收**。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-03

---

##### 一、独立重跑记录（逐项真实命令 + 退出码）

| # | 命令 | 真实输出 | 退出码 |
|---|---|---|---|
| 1 | `bash .work/evidence/QEMU-037t/run.sh` | `[PASS] check_qemu_trans … 227/227`；`[PASS] probe (default) … 91/91`；`[PASS] probe --selftest`；17 回归全 IDENTICAL；`[PASS] check-patch-tree … 69 patches OK`；`[PASS] check-source-state`；`[PASS] trans_fp ILLI-stub count expected=4 actual=4`；`OVERALL: PASS` | **EXIT=0** |
| 2 | `python3 tools/qemu/min_rom_probe_037t.py` | `Main: 91/91 passed, 0 failed`；`Overall: PASS` | **EXIT=0** |
| 3 | `python3 tools/qemu/min_rom_probe_037t.py --selftest` |4 类断言 FAIL 路径全 PASS；40 项派生自检全 PASS；`Self-test: PASS` | **EXIT=0** |
| 4 | `python3 tools/qemu/check_qemu_trans.py` | `check_qemu_trans: 227/227 insns have trans impl (M1 152/152)` | **EXIT=0** |
| 5 | `make check` | `Results: 149 total, 149 passed`；lit `Passed: 29`；`check-patch-tree: 69 patches OK`；`check-scope: PASS`；`check-fp-contract: PASS`；`check-no-residue: PASS`；`repository checks: PASS` | **EXIT=0** |
| 6 | `bash .work/evidence/QEMU-037t/run.sh --inject` | `inject: 5 edits applied`；`injected diff touches: helper.c trans_fp.c.inc`；注入后 `62/91 passed, 29 failed`；23 必需例全 FAIL；`injected probe exit=1`；还原后源码 sha 复原；重建后 `91/91 passed, 0 failed`；`OVERALL: PASS` | **EXIT=0** |

**源码 blob sha（独立核对）**：
- `helper.c`: `15660d2b2d66acaee9f1bdf4354f909c8c328a19fc4b336933c57d8cafff8874` ✓
- `trans_fp.c.inc`: `20d0de2cffeb40972723adab9980f6d8b9a756b3396282d0a6eab5ad6a33b8fc` ✓

---

##### 二、脚本审计（`.work/evidence/QEMU-037t/run.sh`）

**结构审查**：
- `set -u` ✓（未使用 `set -e`，由 `FAIL` 变量手动门控，合理）
- `result()` 函数正确捕获退出码（直接 `$?`，非 `tee` 管道）✓
- `check_probe()` 用 `python3 tools/qemu/min_rom_probe_037t.py > log 2>&1` + `PROBE_RC=$?` 直接捕获退出码 ✓
- 无 `tee` 吞退出码问题 ✓
- `FAIL` 变量在任意 `[FAIL]` 时置1，脚本末尾 `exit 0/1` ✓

**5 处注入逐条审计**：

| 注入 | 目标文件 | 改动内容 | 独立归因？ | 非空/可还原？ |
|---|---|---|---|---|
| (a) ftdiv→mul | helper.c L520 | `float32_div` → `float32_mul` | ✓ 仅影响 div | ✓ |
| (b) rem→fmod | helper.c L522-523 | `float32_rem` → fmod 式截断（scratch status） | ✓ 仅影响 rem 平局 | ✓ |
| (c) root n | trans_fp.c.inc L733 | `a->hd != 2` → `a->hd < 2` | ✓ 仅影响 n=3 | ✓ |
| (d) dst_rf0 | trans_fp.c.inc L35 | `rfidx == 0` → `rfidx == -1` | ✓ 仅影响 dst=rf0 | ✓ |
| (e) scalb rfHD | helper.c L526-528 | `float32_to_int32(...)` → `(int32_t)(float32)b` | ✓ 仅影响 scalb | ✓ |

- 每处 `sub()` 函数验证替换前恰好 N 次出现（默认 `n=1`），防止空注入 ✓
- 5 处注入目标不同（div/rem/root_n/dst_rf0/scalb），无交叉抵消 ✓
- 还原用 `git -C "$SRC" checkout -- .` + sha256 核对 + 重建 ✓
- `git diff --name-only` 非空检查 ✓

**MUST_FAIL_CASES 枚举核对**：23 条，脚本声称注入后29 FAIL（23 必需 +6 附加），`check_probe inject 0` 验证23 条全命中 + 退出码非零。逻辑正确——gate 只要求必需例全 FAIL，附加失败不影响判定。

**结论：脚本合格，无需修改。**

---

##### 三、我的独立注入（不使用脚本自带5处）

**注入点**：`helper.c` 第 522 行，`case 4`（ftrem），将 `float32_rem` → `float32_div`。

**预期效果**：ftrem 使用 div 替代 rem，平局取偶语义被破坏——RE02 (`3.0 rem 2.0`) 应从 `-1` 变为 `+1.5`（div 结果）导致 FAIL；所有 ftrem 用例均受影响。

**执行记录**：

| 步骤 | 命令 | 输出 | 退出码 |
|---|---|---|---|
| 注入 | `edit helper.c`: `float32_rem` → `float32_div` | `1 replacement` | — |
| 验证 diff | `git diff --name-only` | `target/dadao/helper.c` | 非空 ✓ |
| 重建 | `JOBS=8 make build-qemu` | `[3/3] Linking target qemu-system-dadao` | **EXIT=0** |
| 探针 | `python3 tools/qemu/min_rom_probe_037t.py` | `Main: 84/91 passed, 7 failed`；FAIL: RE01-RE07 | **EXIT=1** ✓ |
| 还原 | `edit helper.c`: 恢复原代码 | `1 replacement` | — |
| 验证 sha | `sha256sum helper.c` | `15660d2b…` ✓ | 匹配原始 ✓ |
| 验证 clean | `git status --porcelain` | 空 | 干净 ✓ |
| 重建 | `JOBS=8 make build-qemu` | 成功 | **EXIT=0** |
| 探针回绿 | `python3 tools/qemu/min_rom_probe_037t.py` | `Main: 91/91 passed, 0 failed` | **EXIT=0** ✓ |

**关键 FAIL 用例**：RE02（平局取偶）`3.0 rem 2.0` 期望 `-1.0`，注入后得 `+1.5`（div 结果），确认 IEEE remainder 平局取偶语义承重。其余 RE01/03/04/05/06/07 同时 FAIL，证明 float32_rem 与 float32_div 行为差异显著。

**结论：独立注入验证通过——探针可失败、注入有效、还原含重建后回绿。**

---

##### 四、约束逐条核验

| # | 约束 | 判定 | 证据 |
|---|---|---|---|
| 1 | 临时目录 `/tmp/opencode/QEMU-037t/` | ✅ | 工程师用 `/tmp/opencode/QEMU-037t/`，reviewer 用 `/tmp/opencode/QEMU-037t-review/` |
| 2 | 不提交 git | ✅ | `git status` 仅显示本任务应有改动，无额外提交 |
| 3 | 完成区与真实输出逐条对齐 | ✅ | reviewer 独立重跑全部与完成区一致 |
| 4 | 只动任务书范围，越界须披露 | ✅ | `git status` 无 contracts/spec/tests/llvm-project/cpu.h/Makefile 改动 |
| 5 | 失败即停，禁自动重试 | � | 脚本用 `FAIL` 变量 + `set -u`，无自动重试 |
| 6 | 补丁纪律 | ✅ | `check-patch-tree: 69 patches OK`，无新增补丁 |
| 7 | 复杂命令输出留存 `.work/log/qemu/` | ✅ | 脚本写日志到 `.work/log/qemu/` |
| 8 | 一键证据脚本 | ✅ | `.work/evidence/QEMU-037t/run.sh` 合格，含 `--inject` |

---

##### 五、60/60 核对（重点）

| 检查项 | 结果 | 证据 |
|---|---|---|
| `trans_fp.c.inc` `static bool trans_` 计数 | **60** | `grep -c '^static bool trans_'` = 60 |
| `gen_exception_illegal` 调用数 | **4** | 全部为合法性检查：`fp_check_dst_rf0`(L36) + `fp_check_mreg`(L49,L64) + root n 检查(L734) |
| 残留 ILLI 桩 | **无** | 4 处均非"stub: ILLI"模式，是运行期合法性前置检查 |
| `check_qemu_trans` | **227/227 (M1 152/152)** | reviewer 独立重跑 ✓ |
| 探针族 `_034t` | IDENTICAL to baseline | 脚本重跑 ✓ |
| 探针族 `_035t` | IDENTICAL to baseline | 脚本重跑 ✓ |
| 探针族 `_036t` | IDENTICAL to baseline | 脚本重跑 ✓ |
| 探针族 `_037t` | 91/91 PASS | reviewer 独立重跑 ✓ |
| 汇总 | **16+10+20+14 = 60/60** | 与完成区一致 |

---

##### 六、期望值独立性（铁律）

**审查结论**：探针期望值来源**独立于 QEMU/LLVM**。

- `verify_derivations()` 函数使用 `fractions.Fraction` 精确有理数运算重算所有有限值期望值（40 项），全部 PASS
- `_sqrt_frac()` 使用 `math.isqrt` 整数开方——宿主 Python 标准库，非 QEMU/LLVM
- `_rem_exact()` 使用精确有理数计算 IEEE 754 平局取偶——宿主 Python，非 QEMU/LLVM
- `_round_bits()` 实现 IEEE 754 舍入（4 种模式）——从第一性原理，非 QEMU/LLVM
- `_f32v()`/`_f64v()` 解码已知位模式为精确有理数——纯算术
- selftest 4 类断言 FAIL 路径可达（RF 值/标志/故障码/E2E），证明断言非恒真

**自洽性风险**：`verify_derivations()` 与主探针使用**同一套** `_round_bits`/`_rem_exact`/`_sqrt_frac` 函数。若这些函数有系统性偏差，自检仍会 PASS 且主探针也会 PASS——这是自洽风险。但：(1) 这些函数直接编码 IEEE 754 规范，逻辑简洁可审计；(2) 注入测试（5+1 处）证明修改实现后探针确实 FAIL——若期望值自洽于实现，则注入不应产生差异。**可接受**。

---

##### 七、披露判定

| 发现 | 真实性 | 修复正确性 | 判定 |
|---|---|---|---|
| `fp_status_init` 缺 `default_nan_pattern` | ✅ 真实：`memset(st,0)` 后 `default_nan_pattern==0`，softfloat 的 `partsN(default_nan)` 有 `assert(dnan_pattern != 0)`，036t 的转换族不产生 default NaN 故未暴露 | ✅ 最小正确：`set_float_default_nan_pattern(0b01000000, st)` 设 qNaN 模式，与 FCSR 一致 | 接受 |
| softfloat `rem` 语义 | ✅ 真实：`float32/64_rem` 即 IEEE754 remainder，`rem(x,0)`/`rem(inf,y)` 置 NV（非 DZ） | 按 softfloat 行为固定，spec 未展开 | 接受（延后） |
| `scalb` 的 n 取整 | ✅ 真实：`floatXX_to_int32` 按当前舍入模式取整 | 仅测试整数 rfHD，已披露 | 接受（延后） |
| `rem(x,0)` ⇒ NV（非 DZ） | ✅ 探针 RE05/RE11 断言 NV 而非 DZ | 与 IEEE754 一致 | 接受 |

---

##### 八、越界与残留

- `git status --porcelain --untracked-files=all`：仅本任务应有改动（任务书/changelog/3 个 patch/探针）✓
- `check-no-residue: PASS` ✓
- 无 `contracts/spec/tests/vectors/components/llvm-project/cpu.h/Makefile` 改动 ✓

---

##### 九、完成区一致性

逐条核对完成区表格与 reviewer 独立重跑：

| 完成区声称 | reviewer 核实 | 一致？ |
|---|---|---|
| 探针 91/91 PASS EXIT=0 | 91/91 EXIT=0 | ✅ |
| --selftest 4 类断言 +40 项派生自检 PASS | 全 PASS | ✅ |
| run.sh 默认 EXIT=0 | EXIT=0 | ✅ |
| run.sh --inject EXIT=0 | EXIT=0 | ✅ |
| check_qemu_trans 227/227 | 227/227 | ✅ |
| make check EXIT=0 (sem149 lit29 pt69) | sem149 lit29 pt69 EXIT=0 | ✅ |
| M1 探针 + 034t/035t/036t IDENTICAL | 全 IDENTICAL | ✅ |
| FP 60/60 trans 计数 | 60 trans, 4 ILLI（合法性） | ✅ |
| helper.c sha `15660d2b…` | `15660d2b…` | ✅ |
| trans_fp.c.inc sha `20d0de2c…` | `20d0de2c…` | ✅ |
| 注入后29 FAIL,23 必需例全命中 | 23 必需例全 FAIL + exit=1 | ✅ |
| 还原后源码 sha 复原 + 重建后 91/91 | sha 复原 + 91/91 | ✅ |

**完成区与真实输出完全一致。**

---

##### 十、判决

**Accepted**。

全部验收标准在 reviewer 独立重跑下通过：
1. ✅ 探针 91/91（语义 14 条全覆盖：add/sub/mul/div/rem/scalb/root、4 舍入模式、NaN/Inf/零/子正规、DZ/OF/UF/NV、rem 平局取偶、scalb 取整、root n≠2⇒ILLI、dst_rf0⇒ILLI、先读后写）
2. ✅ selftest 4 类 FAIL 路径可达 + 40 项独立派生自检
3. ✅ 脚本5 处注入审计合格（非空/可还原/含重建/独立归因）
4. ✅ reviewer 独立注入（rem→div）：注入 FAIL (exit=1) → 还原+重建 → 回绿 (exit=0)
5. ✅ check_qemu_trans 227/227、make check 全绿、回归零新增失败
6. ✅ FP 60/60 无残留 ILLI 桩、4 处 gen_exception_illegal 均为合法性检查
7. ✅ 期望值独立于 QEMU/LLVM（精确有理数/整数开方）
8. ✅ fp_status_init NaN pattern 修复最小正确
9. ✅ 越界/残留/完成区一致性全部通过
