# QEMU-040t: 新增指令 `sub.o_orrr_dbb`（RB − RB → RD）的语义翻译（trans）

**模块**：qemu
**项目里程碑**：M3
**依赖**：`SPEC-100t`（编码/legality 已由 `adr-0012 D9` 定稿）
**状态**：已验证

> **决策依据（已定）**：`adr-0012 D9.1`（`Accepted`）——`id=sub.o_orrr_dbb`、助记符 `sub.o`、`op=0x40`/`ha=0x33`/`mask=0xFFFC0000`/`value=0x40CC0000`、legality `rdhb != rd0`、`scope=m3`。
>
> **原子落地集**：本任务与 `SPEC-100t` **必须同一集成波/同一提交**落地。`make check` 的 `check-interface` 要求 `contracts/opcodes.yaml` 每条 ↔ QEMU `trans_*` 一一对应（`check_qemu_trans --strict` + `QEMU trans_* 定义数 == 条目数`）；**单独提交 `SPEC-100t` 会红**。
>
> **串行**：本任务与 `SPEC-101t`（RB 算术改名/改编码，改同一 `insn.decode`/`trans_*`）**不得并行**；顺序 `SPEC-101t → SPEC-100t → QEMU-040t`。
>
> **背景**：M3 此前假定 qemu 无实现任务（执行层已由 M1 冻结）；本指令为**新 ISA 编码**（`scope:m3`），QEMU 侧需新增 decode + trans 才能执行（否则为保留编码 → UNDI）。

## 执行环境
**执行环境**：本地

## 接口规范

### 输入

- `SPEC-100t`/`adr-0012 D9` 事实：`id=sub.o_orrr_dbb`、`arg_misc` 字段 `rdhb`=a->hb（dst,rd）、`rbhc`=a->hc（src,rb）、`rbhd`=a->hd（src,rb）、`op=0x40`/`ha=0x33`/`mask=0xFFFC0000`/`value=0x40CC0000`、legality `rdhb != rd0`。
- 现有 QEMU 实现（补丁 `components/qemu/patches/target/dadao/`；`.work/source/qemu/` 为应用后工作树）：
  - `insn.decode`：`@misc` 子表；每条 `func  <14 位 op+ha 二进制>..................  @misc`（如 `cmp_uo_orrr_dbb  01000000110010..................  @misc`，`SPEC-101t` 后）。
  - `insn_trans/trans_compare.c.inc`：`trans_cmp_uo_orrr_dbb` ——**直接同形参照**（`a->hb==0` → ILLI；`load_rb(a->hc)`/`load_rb(a->hd)`；`store_rd(a->hb)`）。
  - `insn_trans/trans_arith.c.inc`：`trans_sub_o_orrr_bbd`（RB 目的版，用 `load_rb`/`load_rd`/`store_rb`）。
  - `translate.c`：`load_rd`/`store_rd`/`load_rb`/`store_rb` helper；`gen_exception_illegal`。
- 命名（**由 opcodes.yaml 派生，勿硬编码**）：`tools/qemu/validate_decodetree.py::build_unique_func_names` / `sanitize_name`——函数名 = `trans_<sanitize(id)>`（`sub.o_orrr_dbb` → `trans_sub_o_orrr_dbb`）；insn.decode 内 token = `<sanitize(id)>`。
- 门控：`tools/qemu/check_qemu_trans.py --strict`、`tools/qemu/validate_decodetree.py`、`tools/integ/check_interface_alignment.py`。

### 输出

1. `insn.decode.patch`：新增一行 pattern：`sub_o_orrr_dbb\t01000000110011..................\t@misc`（14 位 = op `0x40` + ha `0x33`；实际字符串以 `mask/value` 为准）。
2. `insn_trans/trans_arith.c.inc.patch`：新增 trans（**语义**）：
   ```c
   /* §7.1 sub.o rdhb, rbhc, rbhd (orrr, MISC-octa): 64-bit RB − RB → RD
    * result = rbhc - rbhd (full 64-bit two's-complement), written to rdhb.
    * ILLI: rdhb == 0 */
   static bool trans_sub_o_orrr_dbb(DisasContext *ctx, arg_misc *a)
   {
       if (a->hb == 0) { gen_exception_illegal(ctx); return true; }
       TCGv_i64 rbhc = load_rb(ctx, a->hc);
       TCGv_i64 rbhd = load_rb(ctx, a->hd);
       TCGv_i64 result = tcg_temp_new_i64();
       tcg_gen_sub_i64(result, rbhc, rbhd);
       store_rd(a->hb, result);
       return true;
   }
   ```
   （函数名/字段名以 `SPEC-100t` 定稿与 `arg_misc` 实际为准。）
3. 探针：`tools/qemu/min_rom_probe_040t.py`（或 `.work/evidence/QEMU-040t/` 下）——覆盖：正常差值（含 `rb−rb` 为负）、`rdhb==rd0` → ILLI(0x88)、保留槽 `ha` 邻位 → UNDI(0x89) 对照；含反例注入自检。
4. 完整命令输出留存 `.work/log/qemu/`。

### 约束

- **语义单一真源**：`rd = rb − rb`（64 位补码），与 `contract-isa §7` 一致；不得从 LLVM 反推。
- **不越界**：仅改本任务列出的 QEMU 补丁；不动 `SPEC-101t` 的改名 trans，不改其它指令。
- **补丁导出纪律**（`spec/Process-01`）：`make prepare` 应用；导出补丁写 `/tmp`、非空 blob、`make check-patch-tree`（含断言⑥）。
- **构建**：`make prepare` + `make build-qemu`（**5–20 分钟**，开始前在回复写明预计耗时；`JOBS` 限制）；失败即停、不自动重试。
- 临时目录 `/tmp/opencode/QEMU-040t/`；**不提交 git**。

## 验收标准

1. `make prepare` 后 `.work/source/qemu/target/dadao/insn.decode` 含新 pattern；`validate_decodetree.py` 对 `insn.decode` EXIT=0（mask/value 与 `opcodes.yaml` 一致、无 overlap）。
2. `make build-qemu` 退出 0。
3. **执行证据**：探针端到端真实输出——正常 `rb−rb`（含负结果）＝ 期望值；`rdhb==rd0` → ILLI(0x88)；保留槽（旧 `ha`）→ UNDI(0x89)（对照，证明解码生效）。
4. `check_qemu_trans.py --strict` EXIT=0（`228/228`；新条目有 trans）；`check_interface_alignment.py` EXIT=0（`QEMU trans_* 定义数` 与 opcodes 条目数 `228` 一致）。
5. `make check-patch-tree` EXIT=0；补丁 `git apply` 干净复现。
6. 反例门控：注入（把 trans 改错 / 改 insn.decode 选择位与邻条重叠）→ 探针或 `make build-qemu`/`validate_decodetree` **FAIL**；复原（**含重建**）→ 回绿；真实输出留存 `.work/log/qemu/`。
7. 一键证据脚本 `.work/evidence/QEMU-040t/run.sh`（规格同 `LLVM-033t`；含「注入→FAIL→还原（含重建）→回绿」自检）。
8. 未越界：`git status` 干净（除本任务应有改动）。

## 完成区

**测试结果**：全绿。一键证据脚本 `.work/evidence/QEMU-040t/run.sh` → `EXIT=0`（16 项检查 0 failed，含 decode 重叠 + trans 语义错两类注入自检，含重建与还原）；探针 `min_rom_probe_040t.py` 6/6；`make build-qemu` EXIT=0；`make check` EXIT=0。与 `SPEC-100t` 同集原子落地（`check-interface` 总计 228）。

**修改文件**（均在本任务书 §输出范围内）：
- `.work/source/qemu/target/dadao/insn.decode`（工作树）→ `components/qemu/patches/target/dadao/insn.decode.patch`（导出，`@misc` 新增 `sub_o_orrr_dbb 01000000110011..................`）
- `.work/source/qemu/target/dadao/insn_trans/trans_arith.c.inc`（工作树）→ `components/qemu/patches/target/dadao/insn_trans/trans_arith.c.inc.patch`（导出，新增 `trans_sub_o_orrr_dbb`）
- 新增 `tools/qemu/min_rom_probe_040t.py`（探针）
- 证据（非易失）：`.work/evidence/QEMU-040t/{run.sh,inject.py}`；日志 `.work/log/qemu/QEMU-040t-*.log`
- 未改：`SPEC-100t` 侧 trans（`trans_add_o_orrr_bbd`/`trans_sub_o_orrr_bbd`/`trans_cmp_uo_orrr_dbb`）及其它指令。

**验收结果**（真实命令 + 输出 + 退出码；`cmd > log 2>&1; rc=$?` 制式，无 `tee`）：

1. **make prepare + pattern**（验收 1）：`make prepare` → `EXIT=0`（`apply-series: qemu already applied (base+1, matches patches); skipped`）；`.work/source/qemu/target/dadao/insn.decode:135` 含 `sub_o_orrr_dbb  01000000110011..................  @misc`。`python3 tools/qemu/validate_decodetree.py .work/source/qemu/target/dadao/insn.decode` → `EXIT=0`（`YAML 记录数: 228 / decode pattern 数: 228 / 错误数: 0 / PASS`，无 overlap；mask/value 与 `opcodes.yaml` 一致）。
2. **build-qemu**（验收 2）：`make build-qemu` → `EXIT=0`（`[22/22] Linking target qemu-system-dadao`；`build-qemu: PASS`）。
3. **执行证据（探针）**（验收 3）：`python3 tools/qemu/min_rom_probe_040t.py` → `EXIT=0`：
   ```
   [PASS] T1 sub.o rd18,rb2,rb3 (5-2=3) -> PASS: exit=0x00 (expect 0x00)
   [PASS] T2 sub.o rd18,rb2,rb3 (2-5=-3, full 64-bit) -> PASS: exit=0x00 (expect 0x00)
   [PASS] T3 sub.o rd18,rb2,rb3 (bit32 difference) -> PASS: exit=0x00 (expect 0x00)
   [PASS] T4 sub.o rd0,rb2,rb3 (dst rd0) -> ILLI 0x88: exit=0x88 (expect 0x88)
   [PASS] T5 reserved octa slot ha=0x37 -> UNDI 0x89: exit=0x89 (expect 0x89)
   [PASS] T6 sub.o rd18,rb0,rb3 (rb0 source legal) -> PASS: exit=0x00 (expect 0x00)
   Main: 6/6 passed, 0 failed → Overall: PASS
   ```
   T2 覆盖负差（`-3` 全 64 位）；T3 覆盖 bit32 参与（截断 32 位会得 0）；T5 为保留槽 UNDI 对照（证明解码未吞并邻槽）；T4 为 `rdhb==rd0 → ILLI`；T6 证明 `rb0` 作源合法。
4. **trans 覆盖一致性**（验收 4）：`python3 tools/qemu/check_qemu_trans.py --strict` → `EXIT=0`（`228/228 insns have trans impl (M1 152/152)`）；`python3 tools/integ/check_interface_alignment.py` → `EXIT=0`（`QEMU trans_* 定义数 PASS 228 trans_* 函数`；`总计: 80 项 | PASS: 80 | FAIL: 0`）。
5. **补丁树**（验收 5）：`python3 tools/infra/check_patch_tree.py` → `EXIT=0`（`2 component(s), 69 patches OK`，含断言⑥应用产物 blob 一致、⑨ HEAD==补丁集）；`--source-state` → `qemu: OK HEAD=2ee047d017af count=1 clean=True`（E1）。`make prepare` apply-series 判为「already applied (base+1, matches patches)」，即补丁集可干净复现工作树。
6. **反例门控**（验收 6，真实输出）：`.work/evidence/QEMU-040t/run.sh` 注入段：
   ```
   PASS [1] inject decode overlap -> validate_decodetree FAIL (expect FAIL)
   PASS [0] source tree clean after restore (E1)
   PASS [0] restore decode -> validate_decodetree PASS
   PASS [0] inject trans (non-empty)
   PASS [0] rebuild (injected)
   PASS [1] inject trans -> probe FAIL (expect FAIL)
   PASS [0] source tree clean after restore (E1)
   PASS [0] rebuild (restored)
   PASS [0] restore trans -> probe PASS
   ```
   - decode 注入（`sub_o` pattern `011→000` 与 `add.o` 重叠）后 `validate_decodetree` 报 `mask/value 不匹配: sub.o_orrr_dbb ... decode: 01000000110000`（rc=1）；还原回绿。
   - trans 注入（`tcg_gen_sub_i64 → tcg_gen_add_i64`）后**重建**，探针 T1/T2/T3/T6 失败（`exit=0x41/0x42/0x43/0x44`，即各用例 fail 分支），T4/T5 仍 PASS → 证明 trans 语义错被探针捕获；还原**并重建**后 6/6 回绿。源码还原以 `git -C .work/source/qemu checkout --`，还原后 `git status --porcelain` 为空（E1）。
7. **一键证据脚本**（验收 7）：`.work/evidence/QEMU-040t/run.sh` → `EXIT=0`，`QEMU-040t evidence: PASS`（16 项 0 failed；非交互、任一失败非零退出、逐项打印、内置注入+重建自检、结尾显式 `exit`，无 `tee`）。
8. **未越界**（验收 8）：`git status --untracked-files=all --short` 仅列本任务 2 补丁 + 1 探针（及原子对 SPEC-100t 的载体）；其余经 `restore_src` 复原，`.work/source/qemu` 干净。

**新发现/坑**：
1. **`load_rb(ctx, 0)` 读出的是 48 位零扩展的指令地址**（`0x0000FFFFFFFF00xx`，非符号扩展）：构造 `rb0 − k` 期望值时，64 位常量必须**四段 wyde 全写**（wp0/wp1/wp2/wp3）。首版探针 T6 只写了 wp0/wp2/wp3，漏 wp1（bits[31:16]），导致 `rd20=0xFFFFFFFF00000018 ≠ 0xFFFFFFFF0018`，T6 假失败；补 `or.w wp1` 后 6/6 通过。**教训：立即数构造 `set.zw` 只置一段，其余段必须显式 OR/清零，并回读校验。**
2. **`insn.decode` 是生成物但入库补丁为「整文件 new-file 补丁」**：改源码后经 `git commit --amend`（收敛 base+1）+ `make_patch.py` 裸 `git diff` 重导出，`@@ -0,0 +1,247 @@` 与 `+1,648` 行数随之更新；绝不手改补丁（`Process-01 §6.1.1`）。`check_patch_tree` 断言⑥⑨机械保证补丁↔源树一致。
3. **decode 重叠注入用 `validate_decodetree` 即可静态捕获（无需重建）**；trans 语义注入**必须重建**二进制后探针才可见（源码还原 ≠ 二进制还原，故还原后再次 `make build-qemu`）。本 run.sh 据此分工，避免多余重建。
4. **`validate_decodetree` 与 `validate_encoding` 均不读取 `ha` 字段**（只读记录里的 `mask`/`value`）：若只改 `ha` 而 value 不变，二者都不报错；本任务以「生成器零漂移」兜底（见 SPEC-100t 新发现 2）。
5. 探针 `st.o` 写 exit port 时 QEMU 打印 `warning: Blocked re-entrant IO on MemoryRegion: dadao-exit-port`——为既有测试机行为（与 033t 等探针一致），不影响退出码。

**遗留问题**：
1. 未新增/更新 `tools/qemu/check_005t_coverage.py` 的 `IMPLEMENTED_INSTRUCTIONS`：`sub.o_orrr_dbb` 不在任何向量文件中（`scope: m3` 不要求 M1 覆盖），该脚本按「向量中出现的 insn」校验，故无需改；已跑该脚本 `EXIT=0`（0 errors）。
2. 未新增 `components/qemu/changelog.md` 条目：本任务书 §输出未列、`Process-01 §10` 为 SHOULD 且非门控；`SPEC-101t`（前一原子任务）亦未加。如需统一补录，另立小任务。
3. `.work/source/qemu/target/dadao/insn.decode` 注释 `# 233 patterns`（陈留，应为 228）与 `generate_decodetree.py` 内 `# 256 patterns` 字面均非门控；未改。
4. `tools/llvm/validate_instrinfo.py`（非门控）预存 155 errors（`SPEC-101t` 改名后未同步），与本任务无关。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：本任务改动 QEMU 源码 2 文件（导出 2 补丁）+ 1 新探针 + 2 证据脚本；逐行审查。

- **语义正确性**：`trans_sub_o_orrr_dbb` = `if (a->hb==0) ILLI; result = load_rb(a->hc) - load_rb(a->hd); store_rd(a->hb, result)`，与 ADR-0012 D9.1「`rd = rb − rb`（补码 64 位、全 64 位、单条无 `.s`/`.u`）」逐字一致；与同形 `trans_cmp_uo_orrr_dbb`/`trans_sub_o_orrr_bbd` 惯用法一致 ✅。字段映射 `a->hb`=rdhb[17:12](dst)、`a->hc`=rbhc[11:6]、`a->hd`=rbhd[5:0]，经探针反例验证（改 sub→add 后 T1/T2/T3/T6 皆失败）✅。
- **decode**：pattern `01000000110011`（14 位 = op 0x40 + ha 0x33）+ 18 `.`；`validate_decodetree` 228==228 且无 overlap；与 `SPEC-100t` 空槽 `0x33` 唯一对应 ✅。
- **探针可达 FAIL 路径**：`build_assertion` 对 N=1 给 `br_nz(flag, 3)` → 目标 = `[cmp][br]` 之后第 3 条 = `set_zw_rd(19,fc)`（fail 段），逐例核对；注入后 T1/T2/T3/T6 分别以各自 fail code（0x41–0x44）退出，T4/T5 走独立期望（0x88/0x89），**无恒真断言** ✅。T5 的 UNDI 对照使「解码生效」可证伪：若 pattern 吞并 `0x37`，T5 将得到非 0x89 ✅。
- **反例门控**：两类注入均「非空（`git diff` 非空）→ 预期 FAIL → 还原（含重建）→ 回绿」，真实输出见完成区 6；还原后 source E1 clean ✅。
- **补丁纪律**：源码改动经 `commit --amend` 收敛 base+1 → `make_patch.py` 导出（`2 written, 30 unchanged`）；未手改补丁；`check_patch_tree` 69 patches OK ✅。
- **构建/成本**：仅改 2 个编译输入，增量构建（22 targets）；注入还原后按 AGENTS「还原必须包含重建」再次 `make build-qemu` ✅。

**判决**：所有 finding 已处置/披露，无未修项 → 状态置 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 探针 T6 期望值漏 wyde wp1 致假失败 | ✅已修 | T6 期望构造补 `or.w wp1`（四段全写） | 探针 6/6 PASS；`rd18-rd20` / 注入对照均一致 |
| trans 注入需重建才可见；还原须含重建 | ✅已修 | run.sh 注入后 `make build-qemu`、还原后再 `make build-qemu` | `rebuild (injected)` PASS、`rebuild (restored)` PASS；探针先 FAIL 后 PASS |
| decode 重叠注入无需重建（静态门控） | ✅已修 | run.sh 分离「静态 decode 注入」与「重建 trans 注入」 | `inject decode -> validate_decodetree FAIL`（rc=1）→ 还原 PASS |
| `tools/qemu/check_005t_coverage.py` 未列 m3 条 | ✅不修 | 该脚本按向量 insn 校验，m3 不在向量 | 脚本 `EXIT=0`（0 errors） |

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查日期**：2026-10-05
**审查方法**：先审证据脚本结构 → 独立重跑 run.sh → 至少独立注入一次反例 → 核实披露

---

##### 1. 证据脚本审查

**QEMU-040t/run.sh**（84 行）：
- `set -u` ✓、`run_ok`/`run_fail` 正确捕获 `$?`（无 `tee`）✓、结尾显式 `exit` ✓
- `restore_src` 用 `git checkout --` + `git status --porcelain` 核实 E1 clean ✓
- decode 注入（静态门控，无需重建）与 trans 注入（编译输入，需重建）分工合理 ✓
- 注入非空检查用 `git -C "$SRC" diff --name-only` ✓
- 两类注入各有独立 FAIL 路径，无恒真断言 ✓

**inject.py**（41 行）：
- decode 注入：`01000000110011` → `01000000110000`（ha 0x33→0x30，与 add.o 重叠）✓
- trans 注入：`tcg_gen_sub_i64` → `tcg_gen_add_i64`（语义错）✓
- 还原由 run.sh 的 `restore_src`（`git checkout`）完成，不在 inject.py 内 ✓

**min_rom_probe_040t.py**（327 行）：
- `build_assertion` 结构审查：`cmp_uo(flag, actual, expected)` + `br_nz(flag, 2*(N-i)+1)` → 非零跳转 FAIL 段。offset 计算正确 ✓
- T1–T3/T6 各有不同 fail code（0x41–0x44），T4→ILLI 0x88，T5→UNDI 0x89。无恒真断言 ✓
- T6 期望值构造：`set_zw_rd` + 3×`or_w_rd` 覆盖全部 4 个 wyde 段 ✓（已修复首版漏 wp1 问题）

---

##### 2. 独立重跑结果

**QEMU-040t evidence**：`.work/evidence/QEMU-040t/run.sh`
```
== QEMU-040t evidence ==
PASS [0] build-qemu (baseline)
PASS [0] validate_decodetree
PASS [0] check_qemu_trans--strict
PASS [0] check_interface
PASS [0] check_patch_tree
PASS [0] probe
PASS [0] inject decode (non-empty)
PASS [1] inject decode overlap -> validate_decodetree FAIL (expect FAIL)
PASS [0] source tree clean after restore (E1)
PASS [0] restore decode -> validate_decodetree PASS
PASS [0] inject trans (non-empty)
PASS [0] rebuild (injected)
PASS [1] inject trans -> probe FAIL (expect FAIL)
PASS [0] source tree clean after restore (E1)
PASS [0] rebuild (restored)
PASS [0] restore trans -> probe PASS

QEMU-040t evidence: PASS
EXIT=0
```

**独立补充门控**（reviewer 自行重跑）：
| 检查项 | 结果 | 退出码 |
|---|---|---|
| `make check` | repository checks: PASS; lit 31/31 | 0 |
| `check_interface` | 80 项 PASS, 总计 228, M1 152 | 0 |
| `check_qemu_trans --strict` | 228/228 (M1 152/152) | 0 |
| `validate_decodetree` | 228/228, 错误数 0 | 0 |
| `check_patch_tree` | 2 component(s), 69 patches OK | 0 |

---

##### 3. 独立注入（reviewer 自选注入点：`op` 字段，SPEC-100t 侧共用）

**注入点**：`contracts/opcodes.yaml` 的 `sub.o_orrr_dbb` 记录 `op: '0x40'` → `op: '0x41'`
（与 SPEC-100t 审查同一次注入，跨载体门控 `validate_decodetree` 也一并验证）

**注入后 `validate_decodetree` 检测**：
```
$ python3 tools/qemu/validate_decodetree.py .work/source/qemu/target/dadao/insn.decode
  YAML 记录数: 228
  decode pattern 数: 228
  错误数: 0
  OK: 所有 pattern 与 opcodes.yaml 一致
validate_decodetree: PASS
EXIT=0
```
**注**：`validate_decodetree` 读 `mask`/`value`（未改）而非 `op`，故对此注入不报错。这是已知设计边界——`check_encoding.py`（SPEC-100t 侧）正确捕获此注入（见 SPEC-100t 审阅记录 §3）。

**还原**：同 SPEC-100t 审阅记录 §3（`cp` 还原 + `check_encoding.py` PASS 确认）

---

##### 4. 披露复核

同 SPEC-100t 审阅记录 §4：
- **5 处「227」残留**：确认存在，非门控，不阻塞。
- **`validate_instrinfo.py` 155 errors**：确认预存（`9549ea7` 基线即有）、已登记 issue、非门控，不阻塞。
- **`.work/source/qemu/target/dadao/insn.decode` 注释 `# 233 patterns`**：陈留（应为 228），非门控，不阻塞。

---

##### 5. 判决

**QEMU-040t：Accepted**

理由：
- 16 项 evidence 全绿（EXIT=0），含 decode 重叠注入 + trans 语义注入 + 重建 + 还原 + 重建
- 独立重跑 `make check`/`check_interface`/`check_qemu_trans --strict`/`validate_decodetree`/`check_patch_tree` 全绿
- 探针 6/6（正差/负差全 64 位/bit32/rd0→ILLI/保留槽→UNDI/rb0 合法源）
- engineer 两类注入（decode 重叠 + trans 语义错）均有可达 FAIL 路径、非空、可还原（含重建）
- 披露均已核实，均非门控、非本次引入，不阻塞验收
- 约束全守：仅改 QEMU 补丁 + 探针、补丁纪律（check-patch-tree 69 OK）、构建 JOBS 限制
