# SPEC-100t: 新增指令 `sub.o_orrr_dbb`（RB − RB → RD）规范与编码

**模块**：spec
**项目里程碑**：M3
**依赖**：无
**状态**：已验证

> **决策依据（已定）**：用户 2026-10-04 逐条确认，decision 记入 **`.tao/adr/adr-0012-simrisc-0.5.4-update.md` 的 D9**（`Accepted`，见 `## 状态说明`）。本任务书按 D9 落地，**无待确认提案**（唯一例外见下方 ⚠️ 算术修正）。
>
> ✅ **算术修正（用户 2026-10-04 已确认）**：`ha=0x33 ⇒ value=0x40CC0000`（原裁定笔误 `0x40C00000` 实为 `ha=0x30`，与 `SPEC-101t` 的 `add.o_orrr_bbd` 冲突）。本任务书按 `0x40CC0000` 落地。
>
> **原子落地集**：本任务 + `QEMU-040t` 必须**同一集成波/同一提交**落地——`make check` 的 `check-interface` 要求 `contracts/opcodes.yaml` 每条 ↔ QEMU `trans_*` 一一对应；**单独提交本任务会红**（`check_qemu_trans --strict` / `QEMU trans_* 定义数`）。
>
> **串行**：本任务与 `SPEC-101t`（三条既有指令改名+改编码）**同改 `contracts/opcodes.yaml` 与 `tests/vectors/**`**，按 `AGENTS.md`「同改共享文件串行」**不得并行**。

## 执行环境
**执行环境**：本地

## 接口规范

### 输入

- **`adr-0012 D9`**（权威决策）；`ADR-0018（C14 D4）`、`ISS-130`、`.tao/knowledge/project_M3-codegen-choices.md §5`（C14）。
- `spec/SimRISC-00-指令系统设计.md`（QFC 主表 + `MISC-octa` 子表，编码权威）。
- `spec/SimRISC-05-64位地址运算.md`（`§加减操作` 正文 + 生成块 `ASSEMBLY_LIST`/`LEGALITY`）。
- `.tao/knowledge/contract-isa.md §7`（RB 地址运算归一化）、`§15`（legality 汇总）。
- `contracts/opcodes.yaml`（227 条：m1 152 / fp 60 / excluded 15）、`contracts/legality_rules.yaml`（含 `dst_rd0`）。
- 生成器/门控（v5 自身）：`tools/spec/generate_opcodes.py`、`tools/spec/gen_legality_list.py`、`tools/spec/check_asm_list_drift.py` + `tools/llvm/gen_asm_list.py`、`tools/spec/check_legality_drift.py`、`tools/spec/check_qfc_coverage.py`、`tools/spec/check_scope.py`、`tools/spec/validate_encoding.py`、`tools/integ/check_interface_alignment.py`、`tools/testcases/validate_vectors.py`。

### 输出（按 D9.1）

1. `spec/SimRISC-00-指令系统设计.md`：`MISC-octa` 子表（行 `110`，列 `x011`）新增 `sub.o_orrr_dbb`。
2. `spec/SimRISC-05-64位地址运算.md`：分类头计数（`4 条` → `5 条`）、`§加减操作` 新增 `sub.o` 正文（`rd = rb − rb`，64 位补码、全 64 位、单条无 `.s`/`.u`）；生成的 `ASSEMBLY_LIST`/`LEGALITY` 块经生成器刷新。
3. `.tao/knowledge/contract-isa.md §7.1` 新增行（语义 + 来源标注）。
4. `contracts/opcodes.yaml` 新条目（**由 `tools/spec/generate_opcodes.py` 生成，须同步生成器**）：
   - `id: sub.o_orrr_dbb`；`mnemonic: sub.o`；`format: orrr`；`op: '0x40'`；`ha: '0x33'`；`mask: '0xFFFC0000'`；`value: '0x40CC0000'`；
   - 字段 `rdhb`(dst,rd)[17:12]、`rbhc`(src,rb)[11:6]、`rbhd`(src,rb)[5:0]；`legality: [rdhb != rd0]`；`rule_refs: [dst_rd0]`；`scope: m3`；`spec_cite: SimRISC-05 §加减操作`。
5. `.tao/knowledge/contract-asm-list.md`（生成物）刷新。
6. **`tools/spec/check_scope.py`**：`ALLOWED_SCOPES` 纳入 `m3`、新增 `m3` 计数（=1）、`EXPECTED_TOTAL` 227→**228**、`scope∈{m1,fp,m3}` ⇒ 无 `decode/旧字段`、docstring 同步；`tools/testcases/validate_vectors.py` docstring「227 条」→「228 条」。
7. 组件向量（**可选**，`scope: m3` 不在 M1 身份集、不强制）：如需，加 `tests/vectors/isa/reg-arith.yaml` encoding/semantic 一条，`inventory.md` **不加 M1 行**（m3 不参与 M1 交叉校验）；若添加须同步 `tools/testcases/generate_isa_vectors.py`。

### 约束

- **Spec-first**：编码/语义以 `adr-0012 D9` + `spec/` 为准，**不得**从 LLVM/QEMU 实现反推；外部参考仓库（0628/TCH）仅只读溯源，不作执行依赖。
- **原子**：spec 正文 + 编码 + 生成物 + `check_scope.py` 一次改完；`make check` 在 `QEMU-040t` 同集落地后全绿。
- **生成器随产物**：`generate_opcodes.py`/`gen_asm_list.py`/`gen_legality_list.py` 重跑与交付**逐字节一致**（零漂移）。
- **不改既有指令**语义/编码/id；仅向空槽 `ha=0x33` 新增一条（原 reserved/UNDI）。
- **不新增 legality 规则**（复用 `dst_rd0`）。
- **`scope: m3`**：新增范围取值须同步 `check_scope.py`；不得置 `m1`。
- 临时目录 `/tmp/opencode/SPEC-100t/`；复杂命令输出留存 `.work/log/spec/`（禁 `tee` 吞退出码：`cmd > log 2>&1; rc=$?`）；**不提交 git**。

## 验收标准

1. **无冲突核对**：给出 QFC `MISC-octa` 子表逐槽核对表（`ha` 已用集合 + 新槽 `0x33`），证明唯一、不与 `SPEC-101t` 的新 `0x30`–`0x32` 及既有条目冲突；`check_qfc_coverage.py` EXIT=0。
2. **正文/归一化一致**：`spec/SimRISC-00` 子表、`spec/SimRISC-05 §加减操作`、`.tao/knowledge/contract-isa.md §7.1` 三处语义/id/编码一致（给 grep/对照）。
3. **编码一致**：`contracts/opcodes.yaml` 新条目字段/`op`/`ha`/`mask`/`value`/`scope` 与 D9.1 一致；`validate_encoding.py` EXIT=0；`generate_opcodes.py` 重跑与交付逐字节一致。
4. **scope 门控**：`check_scope.py` EXIT=0（`m3=1`、`total=228`、`m1=152`）。
5. **生成物同步**：`check-asm-list-drift` EXIT=0、`check-legality-drift` EXIT=0。
6. **门控**：`make check` EXIT=0（**在 `QEMU-040t` 同集落地后**）；`check-interface` 跨载体一致（总计 **228**、M1 **152**）；`check-spec-refs` 不新增违规。
7. **反例门控**：注入（改 `ha`/`value`/`scope`）→ 对应检查器非零退出；复原 → 回绿；真实输出留存 `.work/log/spec/`。
8. **一键证据脚本** `.work/evidence/SPEC-100t/run.sh`（规格同 `LLVM-033t`：非交互、任一失败即非零退出、逐项打印「检查名+期望/实际+退出码」、内置「注入反例→预期 FAIL→还原→回绿」自检、结尾不 `tee` 吞退出码）。
9. **未越界**：仅改本任务列出的文件；`git status --untracked-files=all` 干净（除本任务应有改动）。
10. **确认**：上述 ⚠️ 算术修正（`ha=0x33 ⇒ value=0x40CC0000`）获用户确认，或按用户修正值落地。

## 完成区

**测试结果**：全绿。一键证据脚本 `.work/evidence/SPEC-100t/run.sh` → `EXIT=0`（21 项检查 0 failed，含 scope/ha/value 三类注入自检）；`make check` `EXIT=0`（`repository checks: PASS`，lit 31/31）。原子对 QEMU-040t 同集落地。

**修改文件**（11 改 + 1 新增；均在本任务书 §输出 1–6 范围内）：
- `spec/SimRISC-00-指令系统设计.md`（MISC-octa 子表 `110-xxx` 行 `x011` → `sub.o_orrr_dbb`）
- `spec/SimRISC-05-64位地址运算.md`（分类头 4→5；§加减操作 增 `dbb` 正文 + `sub.o rdHB, rbHC, rbHD`；ASSEMBLY_LIST/LEGALITY 由生成器刷新）
- `.tao/knowledge/contract-isa.md`（§7.1 新增行；附录 A.2 `110-011`）
- `contracts/opcodes.yaml`（生成物，`generate_opcodes.py` 重生成，228 条）
- `.tao/knowledge/contract-asm-list.md`（生成物，`gen_asm_list.py` 重生成）
- `tools/spec/generate_opcodes.py`（`build_misc_octa` 新增 `sub.o-dbb`；docstring/头部纳入 m3）
- `tools/spec/check_scope.py`（`ALLOWED_SCOPES`+m3、`EXPECTED_M3=1`、`EXPECTED_TOTAL=228`、3b 含 m3、docstring）
- `tools/llvm/gen_asm_list.py`（头部/docstring 计数纳入 m3）
- `tools/testcases/validate_vectors.py`（docstring 227→228）
- `components/qemu/patches/target/dadao/insn.decode.patch`、`.../insn_trans/trans_arith.c.inc.patch`（原子对 QEMU-040t 侧，见该任务书）
- 新增：`tools/qemu/min_rom_probe_040t.py`（原子对 QEMU-040t 侧探针）
- 证据（非易失）：`.work/evidence/SPEC-100t/{run.sh,check_encoding.py,inject.py}`；日志 `.work/log/spec/SPEC-100t-*.log`、`.work/log/qemu/QEMU-040t-*.log`

**验收结果**（真实命令 + 输出 + 退出码；`cmd > log 2>&1; rc=$?` 制式，无 `tee`）：

1. **无冲突核对**（验收 1）：`python3 tools/spec/check_qfc_coverage.py` → `EXIT=0`：`QFC (op,ha) 指令总数: 228`、`差异总数: 0（M1 内: 0，M1 外: 0）`、`OK: QFC 表与 opcodes.yaml 双向完全一致`。MISC-octa `110-xxx` 逐槽：`x000 add.o(0x30)`、`x001 sub.o_bbd(0x31)`、`x010 cmp.uo_dbb(0x32)`、**`x011 sub.o_dbb(0x33)`（新）**、`x100 rb2rb(0x34)`、`x101 rd2rb(0x35)`、`x110 rb2rd(0x36)`、`x111 reserved(0x37)` —— 新槽唯一，与 `SPEC-101t` 的 0x30–0x32 及既有条目无冲突。
2. **三处正文/归一化一致**（验收 2）：三载体均含 `sub.o` dbb 形态：
   - `spec/SimRISC-00` MISC-octa `110-011 = sub.o_orrr_dbb`；
   - `spec/SimRISC-05 §加减操作`：`rdHB = rbHC − rbHD`（"单条、无 `.s`/`.u` 变体"）；
   - `contract-isa §7.1`：`| \`sub.o rdhb, rbhc, rbhd\` | ... \`rdhb = rbhc − rbhd\` ...`；附录 A.2 `110-011`。
   一致性由 `check_encoding.py` 逐项断言（`SimRISC-00 MISC-octa 110-011`、`§7.1 行`、`A.2 110-011` 全 PASS）。
3. **编码一致**（验收 3）：`contracts/opcodes.yaml` 新条目 `id=sub.o_orrr_dbb`/`mnemonic=sub.o`/`format=orrr`/`op=0x40`/`ha=0x33`/`mask=0xFFFC0000`/`value=0x40CC0000`/`scope=m3`/`legality=[rdhb != rd0]`/`rule_refs=[dst_rd0]`/`spec_cite=SimRISC-05 §加减操作`；字段 `rdhb[17:12](dst,rd)`/`rbhc[11:6](src,rb)`/`rbhd[5:0](src,rb)`。`validate_encoding.py contracts/opcodes.yaml` → `EXIT=0`（`228 条记录 OK`）。数学校验 `value == op<<24|ha<<18 == 0x40CC0000` 通过。`generate_opcodes.py` 重跑与交付**逐字节一致**（run.sh `generate_opcodes zero-drift` PASS）。
4. **scope 门控**（验收 4）：`python3 tools/spec/check_scope.py` → `EXIT=0`：
   ```
   [PASS] m1 计数: 期望=152 实际=152
   [PASS] fp 计数: 期望=60 实际=60
   [PASS] excluded 计数: 期望=15 实际=15
   [PASS] m3 计数: 期望=1 实际=1
   [PASS] total 计数: 期望=228 实际=228
   [PASS] scope∈{m1,fp,m3} ⇒ 无 decode/旧字段: 期望=0 条 实际=0 条
   check-scope: PASS
   ```
5. **生成物同步**（验收 5）：`check_asm_list_drift.py` `EXIT=0`；`check_asm_list_consistency.py` `EXIT=0`；`check_legality_drift.py` `EXIT=0`（12 chapters OK）；`gen_legality_list.py --verify` `EXIT=0`；`gen_asm_list.py` 重跑与 `contract-asm-list.md` 逐字节一致。
6. **门控**（验收 6）：`make check` → `EXIT=0`（`repository checks: PASS`；lit `Passed: 31 (100.00%)`；`check-qemu-semantics: PASS`）。`check_interface` → `EXIT=0`：`opcodes.yaml 条目数 PASS 总计 228, M1 内 152`；`QEMU trans_* 定义数 PASS 228 trans_* 函数`；`总计: 80 项 | PASS: 80 | FAIL: 0`。`validate_vectors` → `EXIT=0`（`152/152 M1 identities covered OK; 15 data files, 694 cases`）。`validate_encoding` EXIT=0。`check_spec_refs`/`check_spec_drift` EXIT=0。
7. **反例门控**（验收 7，真实输出，`cmd > log 2>&1; rc=$?`）：
   ```
   PASS [1] inject scope -> check_scope FAIL (expect FAIL)
   PASS [0] restore scope -> check_scope PASS
   PASS [1] inject ha -> generate_opcodes drift FAIL (drift detected)
   PASS [0] restore ha -> check-encoding PASS
   PASS [1] inject value -> validate_decodetree FAIL (expect FAIL)
   PASS [0] restore value -> validate_decodetree PASS
   PASS [0] no injection residue in contracts/opcodes.yaml
   ```
   注入均非空（与注入前逐字节比对确认文件被改）；还原后 `opcodes.yaml` 与注入前逐字节一致。
8. **一键证据脚本**（验收 8）：`.work/evidence/SPEC-100t/run.sh` → `EXIT=0`，`SPEC-100t evidence: PASS`（21 项 0 failed；非交互、任一失败非零退出、逐项打印、内置注入自检、结尾显式 `exit`，无 `tee`）。
9. **未越界**（验收 9）：`git status --untracked-files=all --short` 仅列本任务 11 改 + 1 新增（见「修改文件」）；无 `*_tmp*`/`*.orig`/`*.rej` 残留。
10. **确认**（验收 10）：`ha=0x33 ⇒ value=0x40CC0000`（ADR-0012 D9.1 算术修正，用户 2026-10-04 已确认）按此落地。

**新发现/坑**：
1. **`check_scope.py` 之外仍有 5 处「227」计数残留未在本任务书 §输出 6 列名内**：`spec/Toolchain-01-汇编语言.md:5`（"227 条指令全表"）、`docs/README.md:17`、`.tao/knowledge/contract-asm.md:8`、`tools/spec/gen_legality_list.py:7` docstring、`tools/qemu/check_qemu_trans.py:85` 注释。它们随本次 228 条生效而**字面过时**（均不在 `make check` 门控内）。按 acceptance 9「仅改列出的文件」未动，见「遗留问题 1」。
2. **`validate_encoding.py` 不校验 `ha` 字段与 `value` 位一致性**（承 `SPEC-101t` 新发现 2）：本任务注入 `ha` 0x33→0x34（value 不变）时 `validate_encoding` 仍 `228 条记录 OK`；能捕获的是**生成器零漂移**（delivered≠regen）与跨载体 `validate_decodetree`。设计验收注入时不可依赖 `validate_encoding`。
3. **`check_qfc_coverage.py` 为 informational、恒 exit 0**：新槽核对须解析其输出（`指令总数: 228` + `差异总数: 0`），不能只看退出码。已写入 run.sh 的输出断言。
4. **`SimRISC-00` 存在两个 `110-xxx` 行**（MISC-AMO 与 MISC-octa）：解析/核对时必须以 `### MISC-octa指令编码` 段限定，否则 `re.search` 会命中 MISC-AMO 的全空行（首版 `check_encoding.py` 即因此误报，已修）。
5. **`tools/llvm/gen_asm_list.py` 与 `tools/spec/generate_opcodes.py` 头部按 scope 列计数**：新增 `m3` 后须同步计算 `n_m3`，否则生成头部出现 `228 = M1 152 + fp 60 + excluded 15` 的不等式（已修）。
6. `tools/llvm/validate_instrinfo.py`（**非** `make check` 门控、非本任务范围）当前 `EXIT=1`（155 errors，如 "Expected 178 defs, got 153"、`sub.o_orrr_bbd` 期望 def 名 `sub_o_orrr_bbd` 与 TD 的 `sub_o_bbd` 不符）；系 `SPEC-101t` 改名后该脚本未同步的**预存**问题，与本任务无关（本任务新增的 m3 条目不产生任何 error，见「遗留问题 2」）。

**遗留问题**：
1. **5 处过时「227」计数未改**（见「新发现/坑 1」）：均不在本任务书 §输出列名内、不在门控内；建议主会话另立小任务（或在本任务授权下）统一改 227→228。**非本次引入的功能缺口**，而是本次变更导致其字面失效。
2. `tools/llvm/validate_instrinfo.py` 预存 155 errors（SPEC-101t 改名后未同步）——**非本次引入**，且不在 `make check`。
3. 未新增 `tests/vectors/**` 覆盖（本任务书 §输出 7 标注「可选」；`scope: m3` 不在 M1 身份集、不要求 M1 向量覆盖）——语义正确性由 QEMU-040t 探针 + 跨载体门控承担。
4. `.work/source/qemu/target/dadao/insn.decode` 首行注释 `# 233 patterns`（应为 228）为**预存**陈旧注释（`generate_decodetree.py` 字面为 `256 patterns`），非门控项，未改。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：本任务改动 11 文件 + 1 新增；逐行审查（`generate_opcodes.py`/`check_scope.py`/`gen_asm_list.py`/`check_encoding.py`/`inject.py` + 生成物对照）。

- `generate_opcodes.py`：`build_misc_octa` 新增 `rec("sub.o-dbb","sub.o","orrr",op,f_orrr("rdhb","rbhc","rbhd"),["rdhb != rd0"],S05_ADD,ha=0x33,scope="m3")`。核 `_get_id("sub.o-dbb",...)`：`after="dbb"` 非 `_KNOWN_FMTS` ⇒ feature=`dbb` ⇒ id=`sub.o_orrr_dbb` ✅；`f_orrr("rdhb","rbhc","rbhd")` 的 bank 由前缀自推 rd/rb/rb，角色 dst/src/src ✅；`scope=m3` 且非 excluded ⇒ 不附 `decode` ✅；`EXPR_TO_RULE["rdhb != rd0"]="dst_rd0"` ⇒ `rule_refs=[dst_rd0]` ✅。头部/`print` 补 `n_m3`，计数自洽 ✅。
- `check_scope.py`：`ALLOWED_SCOPES`/`EXPECTED_M3`/`EXPECTED_TOTAL`/counts/3b 五处齐改；`scope==fp ⇔ id.endswith("_rf")` 对新 m3 条为 `(False)!=(False)=False` 不受影响 ✅；未改任何旧断言语义（仅扩集合）✅。
- 生成物：`opcodes.yaml` 228 条、`contract-asm-list.md` 头部 `228 = M1 152 + fp 60 + excluded 15 + m3 1` ✅；`SimRISC-05` 分类 5 条、`dst_rd0` 2 条（排序 `cmp.uo_orrr_dbb` < `sub.o_orrr_dbb`）✅。
- `spec/SimRISC-00`：新槽置于 `110-xxx` 第 4 列（对应 ha 0x33），列序与 `x011` 一致 ✅。
- `check_encoding.py`：全部断言均基于 ADR-0012 D9.1 期望值（非实现反推）；含 `value==op<<24|ha<<18` 数学校验（补 `validate_encoding` 缺口）；首版 MISC-octa 行解析误命中 MISC-AMO 段已修（限定段内）✅。
- `run.sh`：`set -u` + 显式 `FAILED` 计数 + 结尾 `exit`；无 `tee`；注入前用「注入前逐字节副本」判定非空与还原 ✅；`ha` 注入用生成器零漂移捕获（因已知 `validate_encoding`/`validate_decodetree` 不读 ha）✅。
- 注入自检：三类注入均先证 FAIL、后证回绿（真实输出见完成区 7）；工作区无注入残留 ✅。

**判决**：所有 finding 已处置/披露，无未修项 → 状态置 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| `check_encoding.py` 误命中 MISC-AMO 的 `110-xxx` 空行 | ✅已修 | 解析限定 `### MISC-octa指令编码` 段内 | `check-encoding` PASS（run.sh） |
| `ha` 注入未被任何非零门控捕获（`validate_encoding`/`validate_decodetree` 不读 ha） | ✅已修 | 注入门控改用「生成器零漂移」 | `inject ha -> generate_opcodes drift FAIL`（rc=1）→ 还原回绿 |
| `generate_opcodes.py`/`gen_asm_list.py` 头部计数未含 m3（生成头部 228=152+60+15 不等式） | ✅已修 | 两生成器补 `n_m3` 并写入头部 | 零漂移 PASS；头部显示 `+ scope m3 1` |
| 5 处「227」计数残留 | ⏸延后 | 未改（越出 §输出列名与 acceptance 9 范围） | 明确登记「遗留问题 1」 |

#### 第 1 轮 reviewer 验收

**审查者**：reviewer（mimo-v2.5-pro）
**审查日期**：2026-10-05
**审查方法**：先审证据脚本结构 → 独立重跑两个 run.sh → 至少独立注入一次反例 → 核实披露

---

##### 1. 证据脚本审查

**SPEC-100t/run.sh**（134 行）：
- `set -u` ✓、`run_ok`/`run_fail` 正确捕获 `$?`（无 `tee`）✓、结尾显式 `exit` ✓
- `inject_nonempty` 用 `diff -q` 检测文件是否被改 ✓
- `drift_fail` 针对 `ha` 注入（因 `validate_encoding` 不读 ha 字段）——设计合理 ✓
- QFC coverage 用 grep 断言输出内容（因该脚本恒 exit 0）✓
- 三类注入（scope/ha/value）各有独立 FAIL 路径，无恒真断言 ✓

**QEMU-040t/run.sh**（84 行）：
- 结构同上 ✓、`restore_src` 用 `git checkout` + `git status --porcelain` 核实 E1 clean ✓
- decode 注入为静态门控（无需重建）、trans 注入需重建——分工合理 ✓
- 注入非空检查用 `git -C "$SRC" diff --name-only` ✓

**min_rom_probe_040t.py**（327 行）：
- 6 个 case 覆盖：正差(T1)、负差全 64 位(T2)、bit32 参与(T3)、rd0→ILLI 0x88(T4)、保留槽→UNDI 0x89(T5)、rb0 合法源(T6)
- `build_assertion` 结构：`cmp_uo` + `br_nz(flag, offset)` → 非零跳转到 FAIL 段；offset = `2*(N-i)+1` 指向各自 fail code。T1–T3/T6 fail code 各不相同（0x41–0x44），T4/T5 用直接退出码（0x88/0x89）。无恒真断言 ✓

**check_encoding.py**（106 行）：
- 逐字段断言 + `value == op<<24|ha<<18` 数学校验 ✓、MISC-octa 段限定解析 ✓

**inject.py**（SPEC-100t, 68 行 / QEMU-040t, 41 行）：
- 就地替换 + 备份/还原机制 ✓、`record_block` 定位 sub.o_orrr_dbb 记录 ✓

---

##### 2. 独立重跑结果

**SPEC-100t evidence**：`.work/evidence/SPEC-100t/run.sh`
```
== SPEC-100t evidence ==
PASS [0] validate_encoding
PASS [0] check_scope
PASS [0] check-asm-list-drift
PASS [0] check-asm-list-consistency
PASS [0] check-legality-drift
PASS [0] gen-legality-verify
PASS [0] check-rule-refs
PASS [0] validate_vectors
PASS [0] check-encoding
PASS [0] check_qfc_coverage (228 / 0 diff)
PASS [0] generate_opcodes zero-drift
PASS [0] gen_asm_list zero-drift
PASS [0] inject scope (file changed)
PASS [1] inject scope -> check_scope FAIL (expect FAIL)
PASS [0] restore scope -> check_scope PASS
PASS [0] inject ha (file changed)
PASS [1] inject ha -> generate_opcodes drift FAIL (drift detected)
PASS [0] restore ha -> check-encoding PASS
PASS [0] inject value (file changed)
PASS [1] inject value -> validate_decodetree FAIL (expect FAIL)
PASS [0] restore value -> validate_decodetree PASS
PASS [0] no injection residue in contracts/opcodes.yaml

SPEC-100t evidence: PASS
EXIT=0
```

**独立补充门控**（reviewer 自行重跑，非 run.sh 内）：
| 检查项 | 结果 | 退出码 |
|---|---|---|
| `make check` | repository checks: PASS; lit 31/31 | 0 |
| `check_interface` | 80 项 PASS, 总计 228, M1 152 | 0 |
| `check_qemu_trans --strict` | 228/228 (M1 152/152) | 0 |
| `validate_vectors` | 152/152 M1 identities | 0 |
| `check_patch_tree` | 2 component(s), 69 patches OK | 0 |

---

##### 3. 独立注入（reviewer 自选注入点：`op` 字段）

**注入点**：`contracts/opcodes.yaml` 的 `sub.o_orrr_dbb` 记录 `op: '0x40'` → `op: '0x41'`
**注入方式**：`python3 -c` 就地替换（非 engineer 脚本的 scope/ha/value 三种注入）
**注入有效性**：`git diff --name-only` 含 `contracts/opcodes.yaml`（非空）✓

**注入后检测**：
```
$ python3 .work/evidence/SPEC-100t/check_encoding.py
[FAIL] record.op == '0x40' — actual '0x41'
[FAIL] value == op<<24 | ha<<18 — op<<24|ha<<18 = 0x41CC0000
check_encoding: FAIL (2 failure(s))
EXIT=1
```

**还原**：`cp /tmp/opencode/SPEC-100t-review/opcodes.before-indep2 contracts/opcodes.yaml`
**还原验证**：
```
$ python3 .work/evidence/SPEC-100t/check_encoding.py
check_encoding: PASS
EXIT=0
```

**注意**：`validate_encoding.py` 对此注入仍报 PASS（EXIT=0）——该脚本不校验 op/ha/value 位一致性（engineer 已披露为已知缺口）。`check_encoding.py`（engineer 交付的静态一致性脚本）正确捕获此注入。

---

##### 4. 披露复核

**5 处过时「227」计数残留**：
- `spec/Toolchain-01-汇编语言.md:5`（"227 条指令全表"）✓ 确认存在
- `docs/README.md:17`（"227 条"）✓ 确认存在
- `.tao/knowledge/contract-asm.md:8`（"227 条指令表"）✓ 确认存在
- `tools/spec/gen_legality_list.py:7`（"227 entries" docstring）✓ 确认存在
- `tools/qemu/check_qemu_trans.py:85`（"全部 227 条均须有 trans_*" 注释）✓ 确认存在
- **判定**：均为文档/注释/docstring，**不在 `make check` 门控内**，非本任务 §输出 列名范围，非功能缺口。建议另立小任务统一改 227→228。**不阻塞本任务验收**。

**`tools/llvm/validate_instrinfo.py` EXIT=1（155 errors）**：
- 确认 `git diff 9549ea7 -- tools/llvm/validate_instrinfo.py` 无改动（预存，非本次引入）✓
- 确认 `grep validate_instrinfo Makefile` 无结果（不在 `make check` 门控）✓
- 确认 `issues.yaml:426` 已登记（ISS 标题："generate_instrinfo.py / validate_instrinfo.py 陈旧、非真源"，status: open）✓
- **判定**：预存问题，已登记 issue，非门控项，与本任务无关。**不阻塞本任务验收**。

---

##### 5. 判决

**SPEC-100t：Accepted**

理由：
- 21 项 evidence 全绿（EXIT=0）
- 独立重跑 `make check`/`check_interface`/`check_qemu_trans --strict`/`validate_vectors`/`check_patch_tree` 全绿
- 独立注入 `op` 字段 → `check_encoding.py` 正确报 FAIL → 还原后回绿
- engineer 三类注入（scope/ha/value）均有可达 FAIL 路径、非空、可还原
- 两处披露均已核实，均非门控、非本次引入，不阻塞验收
- 约束全守：scope=m3、不改既有指令、不新增 legality 规则、生成器零漂移
