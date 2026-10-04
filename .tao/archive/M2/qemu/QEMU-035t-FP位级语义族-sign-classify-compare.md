# QEMU-035t: FP 位级语义族（sign 4 + classify 2 + compare 4 = 10 条）

**模块**：qemu
**项目里程碑**：M2
**依赖**：`QEMU-034t`（**必须先 `已验证`**：提供 `trans_fp.c.inc` 骨架、`load_rf`/`store_rf`、`dst_rf0` 检查 helper、探针范式）。相关：`SPEC-087t`（合约）、`LLVM-029t`/`LLVM-030t`（编码/汇编期对照）。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。

---

## 0. 背景与范围

- 本棒 4 任务之一：把 `scope: fp` 60 条从 ILLI 桩换成真实执行（拆分见 `QEMU-034t §0`）。
- 本任务实现 **位级语义**的 10 条（**不需要 softfloat**）：`sign` 4 + `classify` 2 + `compare` 4。全部可用 TCG 位运算 + 比较表达；期望值可逐位手算。
- 只改 `trans_fp.c.inc`（及必要时的 `helper.c`/`helper.h`，若实现者选择 helper 化 classify/compare，须在完成区披露）。

---

## 1. 事实核实（本轮 architect 实测）

### 1.1 现有桩（`trans_fp.c.inc` 由 `QEMU-034t` 建立后，本任务填充其中 10 条）
- `trans_arith.c.inc` 原桩：`ftsgnj/ftsgnn/fosgnj/fosgnn`（sign 4）、`ftcls/focls`（classify 2）、`ftqcmp/foqcmp`（qcmp 2）。
- `trans_compare.c.inc` 原桩：`ftscmp/foscmp`（scmp 2）。
- `QEMU-034t` 已把这 10 条搬入 `trans_fp.c.inc`，本任务只改该文件。

### 1.2 字段/编码（`contracts/opcodes.yaml`）
| 指令 | 格式 | 目的 | 源 |
|---|---|---|---|
| `ftsgnj/ftsgnn/fosgnj/fosgnn_orrr_rf` | orrr | `rfhb`=a->hb | `rfhc`=a->hc、`rfhd`=a->hd |
| `ftqcmp/ftscmp/foqcmp/foscmp_orrr_rf` | orrr | `rdhb`=a->hb | `rfhc`=a->hc、`rfhd`=a->hd |
| `ftcls/focls_orri_rf` | orri | `rdhb`=a->hb | `rfhc`=a->hc（起始）、`immu6`=a->hd（1–63） |

### 1.3 语义（`.tao/knowledge/contract-fp.md §7/§8/§9`；`spec/SimRISC-07 §浮点符号位操作指令 / §浮点比较指令 / §浮点分类指令`）
- **sign**：`sgnj = copySign(rfHC, rfHD)`（取 rfHC 除符号位外全部位，与 rfHD 符号位组合）；`sgnn` 用 **rfHD 符号位取反**。特例：`rfHD=rf0` ⇒ `sgnj=abs(rfHC)`、`sgnn=−abs(rfHC)`；`rfHC==rfHD` ⇒ `sgnj=copy`、`sgnn=negate`。`ft` 用符号位 bit31，`fo` 用 bit63。
- **classify**：对 ft（32 位）/fo（64 位）置位 `[9:0]`：0 negInf、1 negNormal、2 negSubnormal、3 negZero、4 posZero、5 posSubnormal、6 posNormal、7 posInf、8 sNaN、9 qNaN；`[63:10]` 清零；块形式 `immu6` 1–63 逐对递增、先读后写；`immu6==0` 或起始+`immu6>64` ⇒ ILLI。
- **compare**：`>`→1、`=`→0、`<`→−1；unordered：**Quiet Compare 返回 qNaN、Signaling Compare 返回 sNaN，符号位为 0**。结果写 rdHB（`rd` 组，不受 `dst_rf0` 约束）。`compare` 族**不置异常标志**（spec 未要求）。
- 三条族的目的：sign 目的 rf（⇒ `dst_rf0` 检查 `a->hb==0`）；classify/compare 目的 rd（无需检查）。

### 1.4 未明点（spec 开放，须按选定口径实现并记录）
- **`ft` 结果高 32 位**：spec「只使用低 32 位，高 32 位不做特殊规定」⇒ 本任务须固定一个口径（建议：sign 按**完整 64 位**做符号注入并保持非符号位；classify/compare 结果按 64 位整数写 rd）。`QEMU-034t §8-决策 3` 已请示用户；本任务沿用其裁定。
- **sNaN 的具体 payload**：spec 只说「Signaling Compare 结果为 sNaN，符号位为 0」，未给尾数 payload。建议取 **`0x7F800001`（ft）/`0x7FF0000000000001`（fo）**（符号 0、指数全 1、尾数最低位 1、MSB=0 ⇒ 确为 sNaN），并在完成区记录该选定。
- **NaN 检测与 qNaN/sNaN 区分**：按 IEEE754 位级判据（指数全 1：尾数 MSB=1 ⇒ qNaN；指数全 1 且尾数非 0、MSB=0 ⇒ sNaN）。

---

## 2. 设计

### 2.1 实现要点（`trans_fp.c.inc`）
- **sign（TCG）**：读取 `load_rf`（完整 64 位），按格式取符号位（ft bit31 / fo bit63），与 rfHC 的其余位组合；`sgnn` 取反 rfHD 符号位。**特例无需特判**（`rfHD=rf0` 的符号位为 0 自然给出 abs；`rfHC==rfHD` 自然给出 copy/negate）——须用探针证明。
  - 目的 rf0 ⇒ ILLI（`dst_rf0`）。
- **classify（TCG 或 helper）**：逐条按位提取符号/指数/尾数，判 10 类并映射为 `1<<k`；`[63:10]` 清零；块形式循环 `i` 递增、先读后写；起始/计数检查（`mreg_zero`/`mreg_range_overflow`）用 `QEMU-034t` 的 helper。
- **compare（TCG 或 helper）**：按格式判定 `>`/`=`/`<`；unordered 检测（任一方为 NaN）⇒ 写 qNaN（quiet）或 sNaN（signaling）常量。**qcmp 与 scmp 的唯一差异在 unordered 返回值**；其余（1/0/−1）相同。
  - 结果写 `store_rd(a->hb, …)`。
- 若 classify/compare 选择 helper 化：在 `helper.h` 加 `DEF_HELPER_*`，`helper.c` 实现（**不引入 softfloat**，纯位运算），并在完成区记录该选择与理由。

### 2.2 不改动
- 不动 `cpu.h`/`cpu.c`/`meson.build`/`insn.decode`；不动 `opcodes.yaml`；不加 FP 向量/lit。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `target/dadao/insn_trans/trans_fp.c.inc` | 10 条 stub → 真实实现 |
| 2 | `target/dadao/helper.h` / `helper.c` | **仅当** classify/compare helper 化时增声明/实现（否则不改） |
| 3 | `components/qemu/patches/**` + `series` | `make_patch qemu` 导出（预期**无新增**补丁，仍 32/69） |
| 4 | `components/qemu/changelog.md` | 追加一条 |
| 5 | `tools/qemu/min_rom_probe_035t.py` | 新建探针（§6.2） |
| 6 | `.work/evidence/QEMU-035t/run.sh` | 一键证据脚本（含 `--inject`） |
| 7 | `.work/log/qemu/QEMU-035t-*.log` | 构建/探针/回归完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tests/**`、`components/llvm-project/**`、`insn.decode`。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `contracts/opcodes.yaml`（10 条 id 的 `fields`/`op`/`ha`）
- `.tao/knowledge/contract-fp.md §7/§8/§9`、`spec/SimRISC-07 §浮点符号位操作指令 / §浮点比较指令 / §浮点分类指令`、`spec/SimRISC-00 §浮点寄存器`
- `QEMU-034t` 产出的 `trans_fp.c.inc`、`load_rf`/`store_rf`、legality helper、`tools/qemu/min_rom_probe_034t.py`

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围，越界须披露；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare` + `make build-qemu`（**预计 2–5 分钟**；单 `.c.inc` 增量）。
- 临时目录 `/tmp/opencode/QEMU-035t/`；日志 `.work/log/qemu/`；证据 `.work/evidence/QEMU-035t/`。
- 补丁纪律同 `QEMU-034t §5`。

---

## 6. 验收标准（可执行、可失败，含反例注入）

1. **构建**：`make prepare && make build-qemu` EXIT 0（留日志）。
2. **探针全绿**：`python3 tools/qemu/min_rom_probe_035t.py` EXIT 0。用例至少覆盖：
   - **sign**：`sgnj` 正常组合（rfHC 正/负 × rfHD 正/负四象限）；`sgnn` 同四象限；`rfHD=rf0` ⇒ abs / −abs（特例）；`rfHC==rfHD` ⇒ copy / negate；`ft`（bit31）与 `fo`（bit63）各一组；目的 rf0 ⇒ ILLI 0x88。
   - **classify**：对 ft/fo 各构造 **10 类**输入（±Inf、±Normal、±Subnormal、±Zero、sNaN、qNaN）逐位置位且 `[63:10]=0`；块形式（如 `{rd4:rd6},{rf8:rf10}`）逐对结果；`immu6==0` ⇒ ILLI 0x88；起始+`immu6>64` ⇒ ILLI 0x88。
   - **compare**：`>`/`=`/`<` 三值；unordered 在 `ftqcmp`/`foqcmp` 返回 qNaN、`ftscmp`/`foscmp` 返回 sNaN（**符号位 0**，payload 与选定口径一致）；正常结果与 qcmp/scmp 无关。
   - **NaN 区分**：qNaN 与 sNaN 输入下 compare 表现一致（unordered），但返回值按指令类型区分。
3. **反例可失败（承重证明）**：至少注入并**重建**后 FAIL、还原后**重建**回绿：
   - (a) `sgnn` 漏取反符号位 ⇒ sign 用例 FAIL；
   - (b) `ft` 符号位误用 bit63 ⇒ ft sign/classify 用例 FAIL；
   - (c) classify 类位顺序错（如 negZero/posZero 互换）⇒ 对应用例 FAIL；
   - (d) `ftscmp` 复用 qcmp 的 qNaN 返回 ⇒ scmp unordered 用例 FAIL；
   - (e) 去掉 classify 的 `mreg_range_overflow` ⇒ 越界用例由 0x88 变其它。
   注入 `git diff --name-only` 非空；还原须**源码 + 重建**。
4. **不误伤 M1**：既有 M1 探针失败集与基线逐条一致；`_034t` 保持全绿。
5. **编码门控不回归**：`check_qemu_trans` `227/227 (M1 152/152)` EXIT 0。
6. **`make check` 全绿**：`check-qemu-semantics` 149、`check-lit` 29/29、`check-patch-tree` 69 OK、`check-scope`/`check-fp-contract` PASS。
7. **残留/越界/不变量**：`git status --untracked-files=all` 干净；`check-no-residue` PASS；`.work/source/qemu` base+1 干净；改动与 §3 对齐。

### 6.1 独立期望值来源
同上，10 条可**逐位手算**；期望值独立派生并写死探针，禁「跑 QEMU 反填期望」。qNaN/sNaN 常量按 §1.4 选定口径手算。

### 6.2 探针构造注意
同 `QEMU-034t §6.2`（分支双向验证、位宽回读校验、可达 FAIL 路径）。classify 的 10 类输入须各自独立构造（用 `set.zw`/`rd2rf`，不可只测「=0」）。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/QEMU-035t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律：写 `/tmp`、行数下限、非空 blob、`check-patch-tree` 断言⑥。
7. 复杂命令输出留存 `.work/log/qemu/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/QEMU-035t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **`ft` 高 32 位口径**（§1.4-未明）：须与 `QEMU-034t` 的裁定一致；请在 `034t` 一并拍板。
2. **sNaN payload 选定**（§1.4）：建议 `0x7F800001`/`0x7FF0000000000001`，请确认（不改 spec，仅在实现/探针中固定）。
3. **ADR**：延续「FP 不立 ADR」；本任务无新跨模块合约变更，**建议不立**（承 `QEMU-034t §8-决策 4`）。请用户确认。
4. helper 化 classify/compare 与否属实现选择，不涉合约，由 engineer 定并披露。

## 9. 与现有门控/不变量的关系

| 门控 | 期望变化 |
|---|---|
| `check_qemu_trans` | 不变 `227/227` |
| `check-qemu-semantics` | 不变 149 |
| `check-lit` | 不变 29/29 |
| `check-patch-tree` | 不变 **69**（无新增补丁） |
| `check-scope`/`check-fp-contract`/`validate-encoding` | 不变 PASS |
| 探针群 | 新增 `_035t`；M1 探针与 `_034t` 零新增失败 |

---

## 10. 后续衔接
`QEMU-036t`（softfloat 转换）、`QEMU-037t`（softfloat 算术）。本任务的 `load_rf`/`store_rf`/`store_rd`/legality helper 被后续复用。

## 完成区

**测试结果**：探针 `tools/qemu/min_rom_probe_035t.py` **77/77 PASS，EXIT=0**；`--selftest` 四类断言 FAIL 路径均可达，EXIT=0；一键证据脚本 `.work/evidence/QEMU-035t/run.sh` 默认 **EXIT=0**、`--inject` **EXIT=0**（6 处注入→重建→55/77、22 FAIL、必需 FAIL 例全命中→还原**并重建**→77/77）；`check_qemu_trans` **227/227 (M1 152/152) EXIT=0**；`make check` **EXIT=0**；M1 探针 14 个与 `_034t` 后基线**逐字节一致**（`_034t` 59/59）。构建 `JOBS=8 make build-qemu` EXIT=0（增量实测 6.8s）。
**修改文件**：
1. `.work/source/qemu/target/dadao/insn_trans/trans_fp.c.inc` — 594→**846 行**：新增位级 helper（`fp_bool_not`/`fp_and2`/`fp_and3`/`fp_or2`/`fp_set_bit_if`/`gen_fp_sign`/`fp_is_nan`/`fp_classify_one`/`gen_fp_cmp`），把 10 条 ILLI 桩换成真实 TCG（sign 4 + classify 2 + compare 4）。**纯位运算，未用 softfloat；未改 `helper.c/.h`**。
2. `components/qemu/patches/target/dadao/insn_trans/trans_fp.c.inc.patch` — 由 `make_patch qemu` 重生成（852 行 new-file patch；**无新增**补丁，qemu 仍 32、全仓仍 69）。
3. `components/qemu/changelog.md` — 追加 QEMU-035t 一条。
4. `tools/qemu/min_rom_probe_035t.py` — **新建**（77 例 + `--selftest`；产物经 `_probe_artifact_dir()`）。
5. `.work/evidence/QEMU-035t/run.sh` — **新建**（默认检查 + `--inject` 6 处反例自检）。
6. `.work/log/qemu/QEMU-035t-*.log` — 构建/探针/证据/回归/注入完整输出（非易失）。
7. `.tao/tasks/qemu/QEMU-035t-FP位级语义族-sign-classify-compare.md` — 本完成区+自审。
- 未提交 DADAO-v5 仓库；`.work/source/qemu` 已 amend 至 base+1（`HEAD=abc0d0d`，`rev-list --count c3d48b7..HEAD=1`），porcelain 空。

**验收结果**（真实命令 + 退出码；日志 `.work/log/qemu/`，临时产物 `/tmp/opencode/QEMU-035t/`）：

| # | 验收项 | 命令/证据 | 真实输出 | 判定 |
|---|--------|-----------|----------|------|
| 1 | 构建 | `JOBS=8 make build-qemu`（`QEMU-035t-build.log`/`-build-final.log`） | `BUILD_EXIT=0`，增量 6.8s | ✅ |
| 2 | 探针全绿 | `python3 tools/qemu/min_rom_probe_035t.py` | `Main: 77/77 passed, 0 failed` / `Overall: PASS`，`PROBE_EXIT=0` | ✅ |
| 2b | 断言 FAIL 路径可达 | `python3 tools/qemu/min_rom_probe_035t.py --selftest` | RF 值 / RD 值 / fault 退出码 / E2E exit-port 四类「错期望必检出」，`Self-test: PASS`，EXIT=0 | ✅ |
| 3 | 反例门控（6 类注入） | `bash .work/evidence/QEMU-035t/run.sh --inject`（`QEMU-035t-evidence-inject-run.log`） | 6 edits applied → 重建 → `Main: 55/77 passed, 22 failed` → 必需 FAIL `SG5 SG6 SG13 CL01 CL05 CL14 CM09 CM10 FL3 FL6` 全命中 → `source restored clean` → 还原+重建 → 77/77；`INJECT_EXIT=0` | ✅ |
| 4 | 一键证据（默认） | `bash .work/evidence/QEMU-035t/run.sh` | check_qemu_trans / probe / selftest / check-patch-tree / source-state 全 PASS，`OVERALL: PASS`，EXIT=0 | ✅ |
| 5 | 不误伤 M1 | 14 个 `tools/qemu/min_rom_probe_*.py` 与 `_034t` 后基线逐字节 diff | **全部 `IDENTICAL`**（含预存在失败 006t/008t/009t/010t/013t/028t）；`_034t` 59/59 | ✅ |
| 6 | 编码门控不回归 | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)`，EXIT=0 | ✅ |
| 7 | `make check` 全绿 | `make check`（`QEMU-035t-make-check.log`） | `repository checks: PASS`；`check-patch-tree: 69 patches OK`；`check-qemu-semantics: 149 total, 149 passed`；lit `Passed: 29`；`check-scope`/`check-fp-contract`/`check-no-residue` PASS，EXIT=0 | ✅ |
| 8 | 不变量（零改动） | `git status --porcelain -- contracts spec tests/vectors components/llvm-project` | 空 | ✅ |
| 9 | 残留/越界 | `git status --untracked-files=all --short` | 仅 `changelog.md`(M) + `trans_fp.c.inc.patch`(M) + `min_rom_probe_035t.py`(??) + 本任务书 | ✅ |

真实输出摘录（命令 + 退出码）：
```
$ python3 tools/qemu/min_rom_probe_035t.py ; echo EXIT=$?
Main: 77/77 passed, 0 failed
Overall: PASS
EXIT=0

$ python3 tools/qemu/check_qemu_trans.py ; echo EXIT=$?
check_qemu_trans: 227/227 insns have trans impl (M1 152/152)
EXIT=0

$ python3 tools/infra/check_patch_tree.py ; echo EXIT=$?
check-patch-tree: 2 component(s), 69 patches OK
EXIT=0

$ make check ; echo EXIT=$?
repository checks: PASS
EXIT=0
```
最终 sha（还原+重建后，可复现）：
- 源 `.work/source/qemu/.../trans_fp.c.inc`：`4659dd100c20259e6fa49a8faad4b764ec83f84c34d1a5a447b19d42efc31d34`
- 二进制 `.work/build/qemu/qemu-system-dadao`：`f9d52a0a412ceb71218214f11988905309c8f65bd3a1946db9e567220dd56a3f`
- 反例注入还原后**源码 sha 复原**，且**重建**后探针 77/77 回绿（见 `run.sh --inject`）。

**口径选定（spec 开放点，按任务书 §1.4 记录）**：
- **`ft` 高 32 位**：sign 按**完整 64 位**做符号注入（仅替换 bit31，其余位—含高 32 位—保持 rfHC 原值）；classify/compare 对 ft 只看低 32 位，结果按 64 位整数写 rd。探针 SG13–SG16 用带高 32 位标记的 rfHC 显式验证该口径。
- **unordered NaN payload**：`ftqcmp`→`0x000000007FC00000`、`foqcmp`→`0x7FF8000000000000`（取与 FCSR qNaN(ft/fo) 字段一致、符号位 0 的规范 qNaN）；`ftscmp`→`0x000000007F800001`、`foscmp`→`0x7FF0000000000001`（任务书 §1.4 建议的 sNaN）。spec 未给 payload，本任务固定该口径，不改 spec。

**新发现/坑**：
1. **多类反例合并注入会相互抵消**：初版 `MUST_FAIL` 含 `CL04`（ft negZero）。注入 (b)（ft classify 用 bit63）使 `0x80000000` 的符号读为 0（表观正数），而注入 (c)（negZero/posZero 互换）又把「正数零」映射回 bit3 = 期望值 ⇒ `CL04` 在两注入下**同时抵消而 PASS**。教训：合并注入时每个 must-fail 用例必须能**独立归因**到单一注入；已改用 `CL05`（仅受 (c) 影响）与 `CL14`（fo，仅受 (c) 影响，不受 (b) 影响）。**建议沉淀**：一键证据脚本的 must-fail 清单需标注每例对应的注入项，避免「双注入抵消」假绿。
2. **二进制 sha 会随源码 commit 变化**（QEMU 嵌入源码 revision），即便 `.inc` blob 完全相同：amend 前的构建 `af0f…` 与 amend 后重建 `f9d5…` 不同。故「还原复原」应对**源码 blob** 断言 sha，二进制等价以**重建后探针回绿**为证，不应要求二进制 sha 相等。
3. **无 softfloat 的 classify/compare 完全可由整数位运算表达**：qNaN/sNaN 判据（exp 全 1；尾数 MSB 分 q/s）、±0 相等（同号走幅值序、异号仅当双零相等）、ft 只用低 32 位（`andi 0xFFFFFFFF`）——均无需 softfloat，逐位手算即可独立派生期望值。
4. **`classify` 的 10 类位互斥且穷尽**，故可用「逐谓词 `1<<k` 或和」实现；10 个谓词仅由 sign / exp_zero / exp_all / mant_zero / mant_msb 组合而成，易于逐位核对。

**遗留问题**：
- ⏸延后（spec 开放点，非缺陷）：`ft` 高 32 位口径与 unordered NaN payload 为本任务固定口径（见上）；若用户后续另有裁定，需同步改 `trans_fp.c.inc` 与探针期望值。
- ✅已修：本任务范围内 finding 全部处置（见自审表），无未修项。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`trans_fp.c.inc`（846 行；新增 9 个 static helper + 10 条真实 trans）、探针 `min_rom_probe_035t.py`（77 例 + selftest）、证据脚本 `.work/evidence/QEMU-035t/run.sh`（默认 + `--inject` 6 注入）、补丁导出（69 不变），自主逐行审查 + 全流程实跑。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | compare 异号分支 `gt_ds` 初稿误用 `sa`（会使正数判为不大于） | ✅已修（编译前自查） | 改为 `gt_ds = ~sa & not_both`、`lt_ds = sa & not_both` | 探针 CM01–CM23 全 PASS；注入 (b1) 使符号相关例 FAIL |
| 2 | 合并注入 (b)+(c) 对 `CL04` 相互抵消 ⇒ must-fail 恒绿 | ✅已修 | `MUST_FAIL` 由 `CL04` 改为 `CL05`（仅受 (c) 影响） | `run.sh --inject` 后 22 FAIL，必需 10 例全命中，EXIT=0 |
| 3 | 反例未覆盖任务 (b) 的「ft **sign** 误用 bit63」 | ✅已修 | 新增注入 (b1) `gen_fp_sign(a,31,false)→(a,63,false)`，`MUST_FAIL` 加 `SG13` | 注入后 SG13/SG15/SG17 命中 FAIL |
| 4 | 10 条语义与 spec 是否双向一致（sign 全 64 位注入；classify 位序/清零；compare ±0/符号/NaN） | ✅已验 | 见实现与口径说明 | SG1–SG20、CL01–CL23、CM01–CM23 全 RF/RD 精确匹配；`-d cpu` 独立通道 |
| 5 | 合法性检查承重（sign `dst_rf0`；classify `mreg_zero`+`mreg_range_overflow` 源/目的双侧） | ✅已验 | `fp_check_dst_rf0`/`fp_check_mreg` | FS1/FS2、FL1–FL6 = `0x88`；注入 (e) 去溢出即 FL3–FL6 FAIL |
| 6 | 是否引入 M1 回归 / 是否动 softfloat / helper | ✅已验 | 仅改 `trans_fp.c.inc`，纯位运算 | 14 个 M1 探针逐字节 IDENTICAL；`_034t` 59/59；`make check`/`check_qemu_trans` 全绿 |
| 7 | 反例注入有效性/可复原（含重建） | ✅已验 | 6 处注入合并一轮 | `git diff --name-only` 非空；还原 porcelain 空、源码 sha 复原、**重建**后 77/77 |
| 8 | ft 高 32 位 / qNaN payload 为 spec 开放 | ✅已验（披露） | 按任务 §1.4 固定并写入完成区 | SG13–SG16 显式验证全 64 位口径；CM08/CM11/CM19/CM22 验证 qNaN 常量 |
| 9 | 补丁纪律（无新增、非空 blob、base+1 干净） | ✅已验 | `make_patch qemu`（1 written） | `check-patch-tree: 69 OK`；`--source-state` EXIT=0 |

**逻辑正确性核对**：
- sign：`res = (rfHC & ~signmask) | ((rfHD & signmask) ^ (invert?signmask:0))`；`rfHD=rf0`（符号 0）自然给 `abs`/`-abs`，`rfHC==rfHD` 自然给 `copy`/`negate`；`ft` signpos=31、`fo`=63。
- classify：10 谓词 = sign/exp_zero/exp_all/man_zero/mant_msb 组合，结果 `1<<k`（k≤9），`[63:10]` 恒 0；orri 块 `i` 升序逐元素、先读 rf 后写 rd（跨组无重叠）；`immu6=0` 与 `start+count>64`（源、目的双侧）⇒ ILLI。
- compare：`res = unordered ? nan_const : (gt − lt)`；同号走幅值序（负号反向），异号 `+ > −` 但 ±0 相等（`not_both` 门控）；NaN 判据 exp 全 1 且尾数非 0；结果写 rdHB。
- 未改任何已有函数签名；未新增外部依赖；未动 `cpu.h`/`helper.*`/`insn.decode`。

**判决**：本任务范围内 finding 全部 ✅已修/已验；开放口径已披露并登记。可标「待验收」。

#### 第 1 轮 reviewer 验收

**审查范围**：`trans_fp.c.inc`（846 行；9 helper + 10 条真实 trans）、探针 `min_rom_probe_035t.py`（77 例 + selftest）、证据脚本 `.work/evidence/QEMU-035t/run.sh`（默认 + `--inject` 6 注入）、补丁（69 不变）。独立逐项重跑 + 脚本审计 + 独立注入。

---

##### 一、重跑记录（逐项真实命令 + 退出码）

| # | 验收项 | 命令 | 真实输出 | 退出码 | 判定 |
|---|--------|------|----------|--------|------|
| 1 | 探针全绿 | `python3 tools/qemu/min_rom_probe_035t.py` | `Main: 77/77 passed, 0 failed` / `Overall: PASS` | 0 | ✅ |
| 2 | selftest | `python3 tools/qemu/min_rom_probe_035t.py --selftest` | 4 类断言 FAIL 路径均可达（RF value / RD value / fault exit / E2E exit-port）`Self-test: PASS` | 0 | ✅ |
| 3 | check_qemu_trans | `python3 tools/qemu/check_qemu_trans.py` | `227/227 insns have trans impl (M1 152/152)` | 0 | ✅ |
| 4 | check-patch-tree | `python3 tools/infra/check_patch_tree.py` | `check-patch-tree: 2 component(s), 69 patches OK` | 0 | ✅ |
| 5 | source-state | `python3 tools/infra/check_patch_tree.py --source-state` | `qemu: OK HEAD=abc0d0d28dc5 count=1 clean=True` | 0 | ✅ |
| 6 | make check | `make check` | `repository checks: PASS`；semantics 149/149；lit 29/29；patch-tree 69 OK；scope PASS；fp-contract PASS | 0 | ✅ |
| 7 | _034t 回归 | `python3 tools/qemu/min_rom_probe_034t.py` | `Main: 59/59 passed, 0 failed` / `Overall: PASS` | 0 | ✅ |
| 8 | 证据脚本默认 | `bash .work/evidence/QEMU-035t/run.sh` | trans/probe/selftest/patch-tree/source-state 全 PASS | 0 | ✅ |
| 9 | 证据脚本注入 | `bash .work/evidence/QEMU-035t/run.sh --inject` | 6 edits → 重建 → `55/77 passed, 22 failed` → MUST_FAIL 10 例全命中 → 还原+重建 → `77/77` | 0 | ✅ |
| 10 | 源码 sha | `sha256sum .work/source/qemu/.../trans_fp.c.inc` | `4659dd100c20259e6fa49a8faad4b764ec83f84c34d1a5a447b19d42efc31d34` | — | ✅ 与完成区一致 |

---

##### 二、逐项核验

**1. sign（4 条）**：`ftsgnj`/`ftsgnn`/`fosgnj`/`fosgnn`
- SG1–SG12（fo bit63）：四象限 + rfHD=rf0 特例（abs/−abs）+ rfHC==rfHD 特例（copy/negate）—— 全部 RF 精确匹配。
- SG13–SG20（ft bit31，full 64-bit convention）：高 32 位保留、仅 bit31 操作 —— 全部 RF 精确匹配。
- FS1/FS2（dst rf0 ⇒ ILLI 0x88）—— exit=0x88 确认。
- 实现逻辑 `res = (rfHC & ~signmask) | ((rfHD & signmask) ^ (invert?signmask:0))` 正确；signpos ft=31/fo=63 与格式一致。
- ✅ 通过。

**2. classify（2 条）**：`ftcls`/`focls`
- CL01–CL10（ft 10 类）：±Inf/±Normal/±Subnormal/±Zero/sNaN/qNaN 各 1 例，`1<<k` 精确匹配，`[63:10]=0` 确认。
- CL11–CL20（fo 10 类）：同上。
- CL21（ft 块形式 `{rd4:rd6},{rf8:rf10}`）：negInf/posZero/qNaN 三元素 RD 精确匹配。
- CL22（fo 块形式）：negSubnormal/posInf/sNaN 三元素 RD 精确匹配。
- CL23（ft 单元素 immu6=1）：negZero RD 精确匹配。
- FL1/FL2（immu6=0 ⇒ ILLI）、FL3–FL6（src/dst start+count>64 ⇒ ILLI）—— exit=0x88 确认。
- 实现：10 谓词由 sign/exp_zero/exp_all/man_zero/mant_msb 组合，`fp_set_bit_if` 逐位置位，`acc` 初始 0 保证 `[63:10]=0`。isdbl=false 时 `tcg_gen_andi_i64(v, raw, 0xFFFFFFFF)` 确保 ft 只看低 32 位。
- ✅ 通过。

**3. compare（4 条）**：`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp`
- CM01–CM07（ft 正常比较）：`>`→1、`=`→0、`<`→−1（`0xFFFFFFFFFFFFFFFF`）、±0 相等 —— 全部 RD 精确匹配。
- CM08（ftqcmp + qNaN 输入 → qNaN 常量 `0x7FC00000`）、CM09/CM10（ftscmp + NaN → sNaN `0x7F800001`）、CM11（ftqcmp + sNaN → qNaN）—— RD 精确匹配。
- CM12（ftscmp 正常 → 与 qcmp 一致 = 1）、CM13（ft 忽略高 32 位）—— RD 精确匹配。
- CM14–CM18（fo 正常比较）：全 64 位 —— RD 精确匹配。
- CM19–CM22（fo NaN）：qNaN `0x7FF8000000000000` / sNaN `0x7FF0000000000001` —— RD 精确匹配。
- CM23（foscmp 正常 → −1）—— RD 精确匹配。
- E1–E3（E2E exit-port 断言）：exit=0x00 确认。
- 实现逻辑：`res = unordered ? nan_const : (gt − lt)`；同号走幅值序（负号反向），异号 `+ > −` 但 ±0 相等（`not_both` 门控）；NaN 判据 exp 全 1 且尾数非 0；qcmp/scmp 仅 unordered 返回值不同。
- ✅ 通过。

**4. 探针构造审计**
- `--selftest` 4 类断言（RF 值 / RD 值 / fault 退出码 / E2E exit-port）均可达 FAIL 路径，无恒真断言。
- 故意错误期望值均被检测为 FAIL（`ok is False`）。
- ✅ 通过。

**5. 补丁/不变量**
- `check-patch-tree: 69 patches OK`（无新增）。
- `contracts/`、`spec/`、`tests/vectors/`、`components/llvm-project/`：`git status --porcelain` 为空。
- `.work/source/qemu` porcelain 空、HEAD=abc0d0d count=1。
- ✅ 通过。

**6. 回归**
- `check_qemu_trans` 227/227 (M1 152/152)。
- `make check` EXIT=0（lit 29/29、semantics 149/149、patch-tree 69、scope/fp-contract/residue 全 PASS）。
- `_034t` 59/59 PASS（基线一致）。
- ✅ 通过。

---

##### 三、脚本审计（`.work/evidence/QEMU-035t/run.sh`）

**结构**：默认模式（trans + probe + selftest + patch-tree + source-state + sha）；`--inject` 模式（6 注入→重建→probe FAIL→MUST_FAIL 校验→还原→重建→probe 回绿）。

**6 处注入逐条审计**：

| # | 注入 | 目标 | 可定位性 | 非空 | 可还原 | 含重建 |
|---|------|------|----------|------|--------|--------|
| (a) | `fosgnn` sign inversion `true→false` | sign 语义 | ✅ 精确匹配 | ✅ | ✅ `git checkout` | ✅ |
| (b1) | ft sign bit31→bit63 | ft sign 语义 | ✅ 精确匹配 | ✅ | ✅ | ✅ |
| (b2) | ft classify signpos=63（取代 `isdbl?63:31`） | ft classify 语义 | ✅ 多行精确匹配 | ✅ | ✅ | ✅ |
| (c) | classify negZero/posZero 互换 | classify 位序 | ✅ 两行精确匹配 | ✅ | ✅ | ✅ |
| (d) | ftscmp 返回 qNaN（取代 sNaN） | compare unordered 编码 | ✅ 精确匹配 | ✅ | ✅ | ✅ |
| (e) | 去掉 `start+count>64` 检查 | classify 合法性 | ✅ 精确匹配 | ✅ | ✅ | ✅ |

**MUST_FAIL 清单调校**：
- `SG5 SG6` ← (a) fosgnn sign inversion
- `SG13` ← (b1) ft sign bit31→bit63
- `CL01` ← (b2) ft classify signpos 错（negInf 在 signpos=63 下符号读为 0，变为 posInf ⇒ bit7 不是 bit0）
- `CL05` ← (c) negZero/posZero 互换（posZero 期望 bit4 实际 bit3）
- `CL14` ← (c) fo negZero（fo 不受 b2 影响，仅受 c 影响）
- `CM09 CM10` ← (d) ftscmp 返回 qNaN 而非 sNaN
- `FL3 FL6` ← (e) range check 去掉后不再 ILLI

**双注入抵消问题**：工程师在自审中已识别并修复 —— 原 `MUST_FAIL` 含 `CL04`（ft negZero），该用例同时受 (b2) 和 (c) 影响而相互抵消。已改用 `CL05`（仅受 c）和 `CL14`（fo，仅受 c）。**结论：已正确处置。**

**脚本退出码处理**：`cmd > log 2>&1` + `$?` 直接捕获（非 `tee`），`FAIL=1` 累加，最终 `exit $FAIL`。✅ 正确。

**微瑕疵**：脚本注释 header 写 "5 regressions"，实际是 6 处。不影响功能。

✅ 脚本合格。

---

##### 四、独立注入（reviewer 自选，非脚本自带 6 处）

**注入选择**：将 `trans_ftqcmp_orrr_rf` 的 unordered 返回常量由 `FP_FT_QNAN`（`0x7FC00000`）改为 `FP_FT_SNAN`（`0x7F800001`），使 ftqcmp 的 quiet compare 返回 sNaN 而非 qNaN。

**注入后 `git diff --name-only`**：`target/dadao/insn_trans/trans_fp.c.inc`（1 file changed, 1 insertion(+), 1 deletion(-)）—— 非空确认。

**注入后重建**：`JOBS=8 make build-qemu` EXIT=0。

**注入后探针**：
```
Main: 75/77 passed, 2 failed
Failed:
  - CM08 ftqcmp with qNaN -> ft qNaN (sign 0)
  - CM11 ftqcmp with sNaN -> ft qNaN
INJECT_PROBE_EXIT=1
```
- CM08：expect `0x7FC00000`（qNaN），got `0x7F800001`（sNaN）—— MISMATCH ✅
- CM11：expect `0x7FC00000`（qNaN），got `0x7F800001`（sNaN）—— MISMATCH ✅

**还原**：`edit` 恢复原 `FP_FT_QNAN`；`git -C .work/source/qemu diff --stat` 为空（porcelain 空）。

**还原后重建**：`JOBS=8 make build-qemu` EXIT=0。

**还原后探针**：`Main: 77/77 passed, 0 failed` / `Overall: PASS` / EXIT=0。

**源码 sha 还原确认**：`4659dd100c20259e6fa49a8faad4b764ec83f84c34d1a5a447b19d42efc31d34` —— 与注入前一致。

✅ 独立注入验证通过：注入→FAIL→还原+重建→回绿，证据链完整。

---

##### 五、三方判定

**1. 合并注入互相抵消致假绿的 finding 是否属实**

工程师称 `CL04`（ft negZero）同时受注入 (b2)（ft classify signpos=63）和 (c)（negZero/posZero 互换）影响而相互抵消。Reviewer 逐逻辑核实：

- 注入 (b2) 使 signpos=63：`0x80000000` 的 bit63=0 ⇒ 被分类为「正数零」（posZero, bit4）
- 注入 (c) 将 posZero 映射到 bit3（原 negZero 位置）
- 两注入叠加：`0x80000000` → posZero → bit3 = `0x8` = 期望值 ⇒ 恒 PASS（假绿）

工程师改用 `CL05`（posZero, 仅受 c 影响：期望 bit4 实际 bit3）和 `CL14`（fo negZero, 仅受 c 影响，不受 b2 影响）。**核实属实，修复正确。**

**2. spec 开放口径是否忠实**

- **ft 高 32 位**：sign 按完整 64 位注入（仅替换 bit31，其余位保持 rfHC 原值）—— 与 `QEMU-034t §8-决策 3` 一致。探针 SG13–SG16 用 `0x12345678...` / `0xCAFEBABE...` 高 32 位显式验证。✅ 忠实。
- **classify/compare 对 ft 只看低 32 位**：实现中 `tcg_gen_andi_i64(v, raw, 0xFFFFFFFF)`。✅ 一致。
- **unordered NaN payload**：qNaN 用 FCSR 规范值（ft `0x7FC00000` / fo `0x7FF8000000000000`，符号位 0）；sNaN 用任务书建议（ft `0x7F800001` / fo `0x7FF0000000000001`，符号位 0，MSB=0 确为 sNaN）。✅ 忠实于 spec 未给 payload 的开放点，选定合理。
- **无过度臆造**：所有语义可从 `spec/SimRISC-07` 逐位推导，未引入 softfloat 或未定义行为。

---

##### 六、越界与残留

- `git status --porcelain -- contracts spec tests/vectors components/llvm-project`：空 ✅
- `git status --untracked-files=all --short`：仅本任务应有改动（`changelog.md`(M) + `trans_fp.c.inc.patch`(M) + `min_rom_probe_035t.py`(??) + 本任务书(M)）✅
- 无触碰 `.tao/archive/**`、`docs/**`、`.tao/knowledge/milestones.md` ✅

---

##### 七、完成区一致性

逐条核对完成区表格：
- 探针 77/77 ✅、selftest PASS ✅、check_qemu_trans 227/227 ✅、make check EXIT=0 ✅、_034t 59/59 ✅、patch-tree 69 ✅、source-state clean ✅、源码 sha 一致 ✅。
- 修改文件列表与 `git status` 一致 ✅。
- 口径选定与实现/探针一致 ✅。
- 新发现（双注入抵消、二进制 sha 变化、无 softfloat 可行性）均已记录且属实 ✅。

---

##### 判决

**Accepted**。

验收命令块在 reviewer 独立重跑下全部通过（探针 77/77、selftest PASS、check_qemu_trans 227/227、make check EXIT=0、patch-tree 69、_034t 59/59）。证据脚本 6 处注入合格，独立注入（ftqcmp qNaN→sNaN）确认 FAIL→还原+重建→回绿。合并注入抵消问题已正确处置。spec 开放口径忠实。无越界。完成区一致。

#### 第 1 轮 architect 交叉复核（`/complete` §2.5，只追加）

**范围**：独立抽查最关键项并自行重跑；校验 reviewer 判决松紧。

**独立重跑（真实命令 + 输出/退出码）**：

| # | 命令 | 真实输出 | 退出码 | 判定 |
|---|------|----------|--------|------|
| 1 | `python3 tools/qemu/min_rom_probe_035t.py` | `Main: 77/77 passed, 0 failed` / `Overall: PASS` | 0 | ✅ |
| 2 | `python3 tools/qemu/min_rom_probe_035t.py --selftest` | RF/RD/fault/E2E 四类断言 FAIL 路径均可达，`Self-test: PASS` | 0 | ✅ |
| 3 | `sha256sum .work/source/qemu/.../trans_fp.c.inc` | `4659dd100c20259e6fa49a8faad4b764ec83f84c34d1a5a447b19d42efc31d34`（与完成区一致） | — | ✅ |
| 4 | `python3 tools/infra/check_patch_tree.py --source-state` | `qemu: OK HEAD=abc0d0d28dc5 count=1 clean=True`；`llvm-project: OK HEAD=a38b3ebec00e count=1 clean=True` | 0 | ✅ |
| 5 | `git status --porcelain -- contracts spec tests/vectors components/llvm-project` | 空（零改动） | 0 | ✅ |

**独立注入（architect 自选，非脚本 6 处、亦非 reviewer 的 `ftqcmp`）**：
- 注入点：`fp_classify_one` 的 **classify 位序 5↔6 互换**（`posSubnormal` `5→6`、`posNormal` `6→5`），按**唯一内容**定位（非行号）。
- 注入后 `git -C .work/source/qemu diff --name-only`：`target/dadao/insn_trans/trans_fp.c.inc`（非空）；源码 sha `4659dd10…`→`46da0e41…`。
- 重建：`JOBS=8 make build-qemu` EXIT=0（增量单 `.c.inc`）。
- 注入后探针：`Main: 73/77 passed, 4 failed` / `PROBE_EXIT=1`，失败**恰为** `CL06 ftcls posSubnormal`、`CL07 ftcls posNormal`、`CL16 focls posSubnormal`、`CL17 focls posNormal`（与注入语义一一对应；其余 73 条不受影响）。
- 还原：`git -C .work/source/qemu checkout -- <tf>` → porcelain 空、源码 sha 复原 `4659dd10…`；**重建**后二进制 sha 回到 `f9d52a0a…`、探针 `77/77` / EXIT=0。
- 日志：`.work/log/qemu/QEMU-035t-crossreview-{inject-build,inject-probe,restore-build,restore-probe}.log`。

**对 reviewer 判决的复核**：reviewer 的重跑记录、脚本审计（6 注入逐条 FAIL 路径）、独立注入（`ftqcmp` qNaN→sNaN，CM08/CM11 FAIL）、三方判定与越界核对**均与落盘证据一致**，未发现遗漏或过松/过严。
**补充（非阻断）**：① 证据脚本头注释仍写 "inject 5 regressions"（实为 6 处）——reviewer 已记为微瑕疵，不影响功能；② engineer 的 6 处与 reviewer 的 1 处注入集中在 sign「取反/位点」、classify 3/4 号位、compare unordered；本次 architect 注入 **classify 5/6 号位**属新路径，补充证明 classify 断言非仅对单一 bit 调参敏感（覆盖增强，非缺陷）。
**结论：确认 Accepted。**

**越界/残留**：本交叉复核仅临时注入并已**还原+重建**；未触碰 `.tao/archive/**`、`docs/**`、`spec/**`、`.tao/knowledge/milestones.md`。
