# SPEC-101t: RB 算术三条指令改名 + 改编码槽（跨组件，原子）

**模块**：spec（跨组件：spec + llvm MC + qemu + testcases 工具）
**项目里程碑**：M3
**依赖**：无（**但是**：与 `SPEC-100t` **同改 `contracts/opcodes.yaml` 与 `tests/vectors/**` ⇒ 串行**；本任务按用户 2026-10-04 裁定**先于** `SPEC-100t` 执行）
**状态**：已验证

> **决策依据（已定）**：用户 2026-10-04 逐条确认，decision 记入 **`.tao/adr/adr-0012-simrisc-0.5.4-update.md` 的 D9.2/D9.3/D9.4/D9.6**（`Accepted`）。本任务书按 D9 落地。
>
> **原子落地（不得半改）**：`spec/` 正文 + `opcodes.yaml` + 向量/inventory + 生成器 + MC + QEMU 必须**一次改完**——改名/改槽后若任一载体滞后，`validate_vectors`/`check-interface`/`check_qemu_trans`/`validate_decodetree` 必红，且 QEMU 会执行到保留编码（UNDI）。
>
> **串行**：与 `SPEC-100t`（共享 `opcodes.yaml`/向量）、`LLVM-043t`（共享 `DADAOInstrInfo.td`）、`QEMU-040t`（共享 `insn.decode`/`trans_*`）**一律串行**。建议顺序：**`SPEC-101t → SPEC-100t → {LLVM-043t, QEMU-040t}**。

## 执行环境
**执行环境**：本地

## 接口规范

### 输入 / 权威事实（`adr-0012 D9`）

| 旧 id | 新 id | 旧助记符 | 新助记符 | 旧 ha | 新 ha | value（=`op<<24\|ha<<18`，op=0x40） |
|---|---|---|---|---|---|---|
| `add.so_orrr_rb` | `add.o_orrr_bbd` | `add.so` | `add.o` | `0x20` | `0x30` | `0x40C00000` |
| `sub.so_orrr_rb` | `sub.o_orrr_bbd` | `sub.so` | `sub.o` | `0x28` | `0x31` | `0x40C40000` |
| `cmp.uo_orrr_rb` | `cmp.uo_orrr_dbb` | `cmp.uo`（名不变） | `cmp.uo` | `0x29` | `0x32` | `0x40C80000` |

- **字段/语义不变**：`add.o_orrr_bbd`=`(rbhb,rbhc,rdhd)`→`rb=rb+rd`；`sub.o_orrr_bbd`→`rb=rb−rd`；`cmp.uo_orrr_dbb`=`(rdhb,rbhc,rbhd)`→整 64 位无符号比较结果 −1/0/1 写 rd。legality 不变（`dst_rb0` / `dst_rd0`）。op 保持 `0x40`，mask `0xFFFC0000`。
- **id 后缀 = bank 签名**（D9.3）：`bbd`=(rb,rb,rd)、`dbb`=(rd,rb,rb)。**仅**本 3 条（+ `SPEC-100t` 新增 1 条）适用；其它既有 id（如 `cmp.uo_orrr_rd`、`add.si_riii_rb`）**不改**。
- **并存**：rrrr 双目的 `add.so {rdHA,rdHB},…` / `sub.so …`（rd 双目的）**保持 `add.so`/`sub.so` 不变**。

### 输出（各载体，原子）

1. **`spec/SimRISC-00-指令系统设计.md`** `MISC-octa` 子表：`100-xxx`/`101-xxx` 行的 `add.so_orrr_rb`/`sub.so_orrr_rb`/`cmp.uo_orrr_rb` **移除**（0x20/0x28/0x29 → reserved），改列 `110-xxx` 行的 `x000/x001/x010`：`add.o_orrr_bbd`(0x30)、`sub.o_orrr_bbd`(0x31)、`cmp.uo_orrr_dbb`(0x32)。
2. **`spec/SimRISC-05-64位地址运算.md`**：`§加减操作`/`§比较操作` 正文中 `add.so`→`add.o`、`sub.so`→`sub.o`（**仅 orrr RB 形态**；rrrr 双目的说明另在其章、勿误改）；生成块 `ASSEMBLY_LIST`/`LEGALITY` 经生成器刷新。分类计数**仍 4 条**（仅改名/改槽）。
3. **`.tao/knowledge/contract-isa.md`**：§7.1/§7.3 正文、附录 A `MISC-octa` 编码表（约 L1299–1301）的 id/助记符/ha 同步。
4. **`contracts/opcodes.yaml`**：3 条 `id`/`mnemonic`/`ha`/`value` 同步（**改生成器 `tools/spec/generate_opcodes.py` 的 `build_misc_octa` 后重生成**，零漂移）。
5. **`contracts/legality_rules.yaml`**：规则集不变（`dst_rb0`/`dst_rd0`），若描述含被改名指令则同步；`tools/spec/gen_legality_list.py --apply` 重生成 spec 合法性清单（`check-legality-drift` 绿）。
6. **`.tao/knowledge/contract-asm-list.md`**：`tools/llvm/gen_asm_list.py` 重生成（`check-asm-list-drift` 绿）。
7. **向量**：`tests/vectors/isa/reg-arith.yaml`（`add.so_orrr_rb`→`add.o_orrr_bbd`、`sub.so_orrr_rb`→`sub.o_orrr_bbd`）、`tests/vectors/isa/reg-compare.yaml`（`cmp.uo_orrr_rb`→`cmp.uo_orrr_dbb`）的 `id:` 字段；`tests/vectors/inventory.md` 对应行；`tools/testcases/generate_isa_vectors.py` 的 `ARITH_MISC_OCTA`/`_base_mnem`/docstring 等常量——重生成与交付逐字节一致。
8. **`tools/qemu/check_005t_coverage.py`**：RB 覆盖清单中的 3 个旧 id → 新 id。
9. **MC（`components/llvm-project/patches/llvm/lib/Target/DADAO/`）**：
   - `DADAOInstrInfo.td`：`add_so_rb`→新助记符 `add.o`（建议 def 名 `add_o_bbd`）、`sub_so_rb`→`sub.o`（def `sub_o_bbd`）、`cmp_uo_rb`→def `cmp_uo_dbb`（助记符 `cmp.uo` 不变），`ha` 改 `0x30/0x31/0x32`；**rrrr 的 `add_so_rd`/`sub_so_rd` 不动**。
   - AsmParser/InstPrinter/decode：TableGen 自动；如需手写分支在完成区说明。
10. **QEMU（`components/qemu/patches/target/dadao/`）**：
    - `insn.decode.patch`：3 行 token `add_so_orrr_rb`→`add_o_orrr_bbd`、`sub_so_orrr_rb`→`sub_o_orrr_bbd`、`cmp_uo_orrr_rb`→`cmp_uo_orrr_dbb`，pattern 前 14 位改 `01000000110000/…110001/…110010`。
    - `insn_trans/trans_arith.c.inc.patch`：`trans_add_so_orrr_rb`→`trans_add_o_orrr_bbd`、`trans_sub_so_orrr_rb`→`trans_sub_o_orrr_bbd`；`insn_trans/trans_compare.c.inc.patch`：`trans_cmp_uo_orrr_rb`→`trans_cmp_uo_orrr_dbb`。
    - **同步所有硬编码旧 `ha` 的探针/脚本**（至少 `tools/qemu/min_rom_probe_008t.py`；以 grep 全仓核对为准），使其编码指向新槽。
11. **v5 文档同步**：散列为 `add.so-rb`/`sub.so-rb` 的 v5 自身文档（如任务书）改 `add.o`/`sub.o`。**不**改写 `adr-0018` / `.tao/knowledge/project_M3-codegen-choices.md` 的既有 decision 文本（其助记符引用由 `adr-0012 D9` 取代，语义不变）。

### 约束

- **原子**：1–11 一次改完；不得留中间态。
- **回归验证**：向量/opcodes/清单重生成**零漂移**；`check-interface`/覆盖率脚本绿；**全仓库无旧 id 残留**（见验收 1）。
- **id 约定仅限表列 3 条**；不得顺手迁移其它 id。
- **不改指令语义/legality/字段/op/mask**；仅 id/助记符/ha/value。
- 临时目录 `/tmp/opencode/SPEC-101t/`；构建（LLVM MC、QEMU）按 `AGENTS.md` 限制 `JOBS`、大构建前在回复写明预计耗时；复杂命令输出留存 `.work/log/{spec,llvm,qemu}/`（不 `tee` 吞退出码）；**不提交 git**；失败即停、不自动重试。

## 验收标准

1. **无旧 id 残留（活载体）**：`grep -rn "add\.so_orrr_rb\|sub\.so_orrr_rb\|cmp\.uo_orrr_rb" spec/ contracts/ tests/ tools/ components/ .tao/knowledge/contract-isa.md .tao/knowledge/contract-asm-list.md` 为空；贴真实输出与退出码。（**允许** `.tao/adr/adr-0012*.md`、`.tao/tasks/**`、`.tao/knowledge/issues.yaml` 的「旧→新」映射表保留旧 id——它们是决策/映射记录，非活载体。）
2. **编码一致（四处）**：`spec/SimRISC-00` 子表、`contract-isa.md` 附录、`contracts/opcodes.yaml`、QEMU `insn.decode` 的 ha/value 一致；无冲突（逐槽核对表）。
3. **生成物零漂移**：`generate_opcodes.py`/`gen_asm_list.py`/`gen_legality_list.py`/`generate_isa_vectors.py` 重跑与交付逐字节一致；`validate_encoding.py`/`check-asm-list-drift`/`check-legality-drift` EXIT=0。
4. **向量/inventory**：`validate_vectors.py` EXIT=0（M1 152/152，含改名后 id）；`inventory.md` 与 opcodes M1 集合一致。
5. **MC**：`make build-mc` 退出 0；`llvm-mc` 对 `add.o rb8, rb9, rd10` / `sub.o rb8, rb9, rd10` / `cmp.uo rd8, rb9, rb10` 的编码 = 新 `value`；`llvm-objdump -d` 往返一致；`check_lit_bytes.py`、`llvm-lit` 不回归。
6. **QEMU**：`make build-qemu` 退出 0；`validate_decodetree.py` EXIT=0；`check_qemu_trans.py --strict` EXIT=0（227/227）；相关探针在新槽下语义正确（给出真实输出）。
7. **门控**：`make check` EXIT=0；`check-interface` EXIT=0（**总计仍 227、M1 仍 152**）。
8. **反例门控**：注入（改回一个旧 ha / 改向量 id / 改 QEMU pattern）→ 对应门控 **FAIL**（非零退出）；复原（含重建）→ 回绿；真实输出留存。
9. **一键证据脚本** `.work/evidence/SPEC-101t/run.sh`（规格同 `LLVM-033t`）。
10. **未越界**：仅改本任务列出的文件；`git status --untracked-files=all` 干净（除本任务应有改动）；`adr-0018`/`project_M3-codegen-choices.md` 未被改。

## 完成区

**测试结果**：通过（全绿）。一键证据脚本 `.work/evidence/SPEC-101t/run.sh` → `EXIT=0`，`18 checks, 0 failed`（含 3 类反例注入自检）。

**修改文件**（21 个，均在本任务书 §输出 1–11 范围内）：
- `spec/SimRISC-00-指令系统设计.md`（MISC-octa 子表 100/101→reserved、110-000/001/010 新列；L73 分类表 mnemonic）
- `spec/SimRISC-05-64位地址运算.md`（分类头 + §加减操作正文；ASSEMBLY_LIST/LEGALITY 由生成器刷新）
- `.tao/knowledge/contract-isa.md`（§7.1 表 + 附录 A.2）
- `.tao/knowledge/contract-asm-list.md`（生成物，`gen_asm_list.py` 重生成）
- `contracts/opcodes.yaml`（生成物，`generate_opcodes.py` 重生成）
- `tests/vectors/isa/reg-arith.yaml`、`tests/vectors/isa/reg-compare.yaml`、`tests/vectors/inventory.md`
- `tools/testcases/generate_isa_vectors.py`、`tools/spec/generate_opcodes.py`
- `tools/qemu/check_005t_coverage.py`、`tools/qemu/min_rom_probe_{008t,009t,010t,033t}.py`
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`
- `components/qemu/patches/target/dadao/insn.decode.patch`、`.../insn_trans/trans_arith.c.inc.patch`、`.../insn_trans/trans_compare.c.inc.patch`
- v5 文档同步（§输出 11）：`.tao/tasks/spec/SPEC-096k-M3启动与分解.md`、`.tao/tasks/llvm/LLVM-043t-sub-rb-rb-MC编码.md`
- 未改：`contracts/legality_rules.yaml`（规则集/描述不含被改名指令，grep 无匹配，无需改）；`adr-0018`/`project_M3-codegen-choices.md`（豁免，实测未改，见验收 10）。
- 证据/生成物（非易失）：`.work/evidence/SPEC-101t/{run.sh,check_encoding.py,check_mc_roundtrip.py,check_vector_generator_sync.py,check_injections.py}`；日志 `.work/log/{spec,llvm,qemu}/SPEC-101t-*.log`。

**验收结果**（真实命令 + 输出 + 退出码）：

1. **活载体无旧 id 残留**（验收 1）：
   `grep -rn "add\.so_orrr_rb\|sub\.so_orrr_rb\|cmp\.uo_orrr_rb" spec/ contracts/ tests/ tools/ components/ .tao/knowledge/contract-isa.md .tao/knowledge/contract-asm-list.md`
   → 无输出，`grep EXIT=1`（=无匹配，PASS）。允许保留旧 id 的映射记录仅存于 `adr-0012`/`.tao/tasks/**`/`issues.yaml`。

2. **编码四处一致**（验收 2）：`python3 .work/evidence/SPEC-101t/check_encoding.py` → `EXIT=0`，`check_encoding: PASS`。逐槽：
   | 新 id | mnemonic | ha | value(=op<<24\|ha<<18) | SimRISC-00 槽 | contract-isa 槽 | QEMU token/pattern |
   |---|---|---|---|---|---|---|
   | `add.o_orrr_bbd` | `add.o` | 0x30 | 0x40C00000 | 110-000 | 110-000 | `add_o_orrr_bbd` 01000000110000… |
   | `sub.o_orrr_bbd` | `sub.o` | 0x31 | 0x40C40000 | 110-001 | 110-001 | `sub_o_orrr_bbd` 01000000110001… |
   | `cmp.uo_orrr_dbb` | `cmp.uo` | 0x32 | 0x40C80000 | 110-010 | 110-010 | `cmp_uo_orrr_dbb` 01000000110010… |
   旧槽 0x20/0x28/0x29（op=0x40）已 reserved：`check_encoding` 断言 `old slots 0x20/0x28/0x29 reserved` OK，且 QEMU patch 中旧 token/旧 pattern 均 absent、pattern 数 227。

3. **生成物零漂移**（验收 3）：重跑 `generate_opcodes.py`/`gen_asm_list.py`/`gen_asm_list.py --embed-spec`/`gen_legality_list.py --apply` 后 `git diff` 哈希前后一致 → `ZERO-DRIFT: PASS`（`f0c642b0…` == `f0c642b0…`）。`validate_encoding.py` EXIT=0（227 条 OK）、`check-asm-list-drift` EXIT=0（byte-identical）、`check-legality-drift` EXIT=0（12 chapters OK）。
   **向量 `generate_isa_vectors.py`**：受 **ISS-125 预存漂移**限制（见「遗留问题」），按用户 2026-10-05 裁定采「定向手改 + 生成器常量同步」；`.work/evidence/SPEC-101t/check_vector_generator_sync.py` EXIT=0：生成器对 3 条新 id 共输出 11 条受影响用例（arith 8 + compare 3），**全部**可在交付向量中按 (class,id,mnemonic,word) 复现。

4. **向量/inventory**（验收 4）：`python3 tools/testcases/validate_vectors.py` → `EXIT=0`，`152/152 M1 identities covered OK（15 data files, 694 cases; gaps: 0）`。

5. **MC**（验收 5）：`make build-mc` EXIT=0（log `.work/log/llvm/SPEC-101t-build-mc.log`）。`check_mc_roundtrip.py` EXIT=0：
   ```
   add.o rb8, rb9, rd10  -> 40 c0 82 4a   (0x40C0824A; &0xFFFC0000==0x40C00000)
   sub.o rb8, rb9, rd10  -> 40 c4 82 4a   (0x40C4824A; &0xFFFC0000==0x40C40000)
   cmp.uo rd8, rb9, rb10 -> 40 c8 82 4a   (0x40C8824A; &0xFFFC0000==0x40C80000)
   llvm-objdump -d 往返一致；旧形 `add.so rb8, rb9, rd10` 被拒（rc=1）
   ```
   `check_lit_bytes.py` EXIT=0（113 patterns）；`llvm-lit` 31/31（见 make check）。

6. **QEMU**（验收 6）：`make build-qemu` EXIT=0（log `.work/log/qemu/SPEC-101t-build-qemu.log`）。`validate_decodetree.py <source>` EXIT=0；`check_qemu_trans.py --strict` EXIT=0（227/227，M1 152/152）。探针（新槽）：
   - `min_rom_probe_008t.py`：`36/37 passed`，唯一失败 `T20 st.o-rb rb0 → ILLI` 与 `QEMU-038t/baseline/probe_008t.log` **逐字相同**（pre-existing，与本次改名无关）；关键用例 `T27 add.o full 64-bit` PASS、`T28 sub.o full 64-bit` PASS、`T33–T36 cmp.uo` 全 PASS。
   - `min_rom_probe_009t.py` 0/12、`min_rom_probe_010t.py` 26/28、`min_rom_probe_033t.py` PASS —— 三者与 baseline **完全一致**，无回归（033t 整体 PASS 直接覆盖 `cmp.uo dbb` 新槽语义）。

7. **门控**（验收 7）：`make check` EXIT=0（`repository checks: PASS`；lit `Passed: 31 (100.00%)`）。`check_interface` EXIT=0：`总计: 80 项 | PASS: 80 | FAIL: 0`，其中 `opcodes.yaml 条目数` = **总计 227、M1 152**。

8. **反例门控**（验收 8）：`check_injections.py` EXIT=0，真实输出：
   ```
   [OK] inject A opcodes ha/value revert -> gate must FAIL — rc=1   (validate_vectors)
   [OK] restore A -> gate must PASS — rc=0
   [OK] inject B vector id revert -> gate must FAIL — rc=1          (validate_vectors)
   [OK] restore B -> gate must PASS — rc=0
   [OK] inject C QEMU decode pattern revert -> gate must FAIL — rc=1 (validate_decodetree)
   [OK] restore C -> gate must PASS — rc=0
   ```
   三处注入目标均为**静态门控**（不涉及已编译二进制），还原为字节级备份还原，无需重建；构建产物未被污染（`git -C .work/source/qemu status --short` 空）。

9. **一键证据脚本**（验收 9）：`.work/evidence/SPEC-101t/run.sh`（非交互、任一检查失败非零退出、逐项打印「检查名+期望/实际+退出码」、内置注入自检、结尾不 `tee` 吞码）→ EXIT=0，`18 checks, 0 failed`。

10. **未越界**（验收 10）：`git status --untracked-files=all --short` 仅列本任务 21 个改动文件、无未跟踪残留；`git status` 对 `adr-0018`/`project_M3-codegen-choices.md` 为空（未改）。

**新发现/坑**：
1. **D9.3 的 id 后缀是「bank 签名」而非单 bank，会破坏按末段取 bank 的旧代码**：`generate_isa_vectors.py::_bank_from_id` 取 id 末段，旧 id `cmp.uo_orrr_rb`→`rb`、新 id `cmp.uo_orrr_dbb`→`dbb`，导致 `gen_compare_semantic` 的 `bank == "rb"` 判断失效，把 dbb 形态误当 rd 源（预置 rd2/rd3）——已改为**从记录 src 字段的 `bank` 推导**。凡读 id 末段当 bank 的代码在 D9.3 后都要复核。
2. **`validate_encoding.py` 不校验 `ha` 字段与 `value` 位的一致性**：把 opcodes 里 `add.o` 的 value 改回旧值它仍报 `227 条记录 OK`。能捕获该错误的门控是**跨载体**的 `validate_vectors`（向量 word↔opcodes）与 `check_interface`。设计注入用例时不能依赖 validate_encoding。
3. **`check_lit_bytes.py` 没有覆盖 RB orrr 三条指令的 lit 字节**，故 opcodes 改槽不会被它捕获；`validate_vectors` 才是这三条的主门控。
4. **向量全量重生成是破坏性的**（ISS-125）：`generate_isa_vectors.py reg-arith.yaml reg-compare.yaml` 会把 224→184 / 36→33 例（删掉 `SPEC-081t` D8.2 追加用例并回退 notes）。与 `SPEC-081t` 先例一致，正确做法是定向手改。
5. `generate_opcodes.py` 的 `_SPECIAL_IDS["add.so"/"sub.so"]="rb"` 与 `generate_isa_vectors.py` 的 `ARITH_MISC_OCTA` 现为死代码；按最小修改未删（前者），`ARITH_MISC_OCTA` 按任务书同步为新 id。

**遗留问题**：
1. **ISS-125（open）**：`reg-arith.yaml`/`reg-compare.yaml` 的生成器↔向量预存漂移仍在（与本次改名无关的其它条目）。用户 2026-10-05 裁定本任务采「定向手改 + 生成器常量」，故验收 3 的向量「逐字节一致」按**受影响条目**核验（`check_vector_generator_sync.py`，生成器受影响输出 ⊍ 交付）；全量零漂移仍归 ISS-125/testcases 专任务。**非本次引入**。
2. 历史审计物 `docs/testcases-009t-audit.md`、`tools/testcases/009t-audit.py` 仍含旧连字符写法 `add.so-rb`/`sub.so-rb`/`cmp.uo-rb`（历史审计记录，且已含已删除的 `rela.si`），不在本任务列出的活载体与验收 1 范围内，未改。
3. 未新增覆盖新助记符的 `tests/lit/MC/Dadao/*.s`（任务书 §输出未列；编码/往返由 `check_mc_roundtrip.py` 证据脚本承担）。如后续要求 lit 覆盖，可另立小任务。
4. `min_rom_probe_008t.py` 的 `T20 st.o-rb rb0 → ILLI` 失败为 **pre-existing**（同 baseline），与本次改名无关，未处置。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围与一致性逐行审查**（改动 21 文件；重点载体逐条核对）：

- `spec/SimRISC-00`：MISC-octa `100-xxx` 全空、`101-xxx` 的 x000/x001 清空、`110-xxx` 的 x000/x001/x010 = `add.o_orrr_bbd`/`sub.o_orrr_bbd`/`cmp.uo_orrr_dbb`（列序对应 ha 0x30/0x31/0x32）；L73 分类表 mnemonic 同步。`check_qfc_coverage`（独立解析 SimRISC-00）报 `QFC 227 / YAML 227 / 差异 0`，佐证槽位一致。✅
- `spec/SimRISC-05`：分类头与正文 mnemonic 同步；ASSEMBLY_LIST/LEGALITY 块重生成后分类计数仍 4 条、legalities 正确（`dst_rd0→cmp.uo_orrr_dbb`；`dst_rb0→add.si_riii_rb, add.o_orrr_bbd, sub.o_orrr_bbd`）。`check-asm-list-consistency`/`check-legality-drift` 绿。✅
- `contract-isa.md`：§7.1 两行 mnemonic、附录 A.2 删 3 旧行/增 3 新行（110-000/001/010），与 opcodes 一致；`check_spec_refs` PASS（0 violations）。✅
- `generate_opcodes.py`：仅改 `build_misc_octa` 3 条 rec（insn `add.o-bbd`/`sub.o-bbd`/`cmp.uo-dbb` → id 后缀 bbd/dbb；ha 0x30/0x31/0x32）。`_get_id` 对「-后缀非格式」取后缀为 feature，产出 `add.o_orrr_bbd` 等，验证重生成 `value` 正确。✅
- `generate_isa_vectors.py`：⇒ 4 处常量/docstring + `is_arith_rb` 判定 + `gen_compare_semantic` 源 bank 推导（见「新发现 1」）。作用域检查：`_bank_from_id` 其余调用点均为 `_rd`/`_rb`/`_ra` 结尾 id，不受影响。✅
- 向量：脚本定向替换仅命中 3 条旧 id 的块（用 `- class:` 界定），word 映射唯一且各文件内唯一；8+6 条受影响 case 的 id/mnemonic/word/notes 已更新；`validate_vectors` 152/152、`check-qemu-semantics`（跑 reg-compare 全部 case）PASS —— 证明新 word 在 QEMU 端语义正确。✅
- MC/QEMU 补丁：经 `.work/source` 改源码→`git commit --amend` 收敛 base+1→`make_patch.py` 裸 `git diff` 导出；`check_patch_tree`（9 断言）+`--source-state` 均 OK；重建成功。✅
- 探针：仅 4 个真正硬编码旧 ha 的脚本被改（008t/009t/010t/033t）；全仓 grep 复核，`037t` 的 `0x40A00000` 系 IEEE754 浮点数据（5.0f）**非指令编码**，未误改。✅
- 注入自检：三注入均先证 FAIL、后证还原回绿；无「恒真断言」；脚本结尾 `exit 1` 非零传播（无 `tee` 吞码）。✅

**判决**：所有 finding 已处置，无未修项 → 状态置 `待验收`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| dbb 后缀致 `gen_compare_semantic` 误判源 bank | ✅已修 | 改从记录 src 字段 `bank` 推导 | 生成器 cmp.uo_orrr_dbb 预置 rb2/rb3；`check_vector_generator_sync` OK |
| 反例 A 用 `validate_encoding` 不报错（该门控不校验 ha↔value） | ✅已修 | 注入门控改为 `validate_vectors` | `check_injections.py` A 注入 rc=1、还原 rc=0 |
| `check_encoding.py` 首版误取 MISC-AMO 的 `110-xxx` 行 | ✅已修 | 限定在 `### MISC-octa` 段落内取行 | `check_encoding.py` 全部 OK |
| `check_mc_roundtrip.py` cmp 期望 asm 误写 rd10 | ✅已修 | 期望改 `cmp.uo rd8, rb9, rb10` | 往返 OK |
| 输出 11 遗漏 `SPEC-096k`/`LLVM-043t` 旧助记符引用 | ✅已修 | 同步为新名/新 def+ha | grep 复核（仅 ADR/archive/映射记录保留旧名） |

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查日期**：2026-10-05

---

##### 1. 证据脚本审阅（先审后跑）

**`run.sh`**：
- 非交互 ✅、任一检查失败非零退出（`set -u` + `TMP_FAIL` 计数器 + `exit 1`）✅、逐项打印 PASS/FAIL+退出码 ✅、结尾无 `tee` 吞码 ✅
- 18 项检查覆盖验收 1–9，合理完整

**`check_encoding.py`**：
- 逐条断言均有可达 FAIL 路径（opcodes.yaml 值、旧槽 reserved、SimRISC-00 行、contract-isa 附录、QEMU patch token/pattern、LLVM MC def/ha）✅
- **小瑕疵**：不校验 `value = op<<24 | ha<<18` 的数学校验（仅比对字面值），但 engineer 已在完成区「新发现 2」中披露，且跨载体门控（validate_vectors、check_interface）可覆盖 ✅ 不阻断

**`check_mc_roundtrip.py`**：
- **小瑕疵**：若 `llvm-mc assemble` 失败，`ok` 仍为 True 脚本仍 EXIT=0（字/round-trip 检查在 `if r.returncode == 0` 内不执行，但 `ok` 未翻转）。实际运行中 assemble 成功，不影响结果，不阻断

**`check_vector_generator_sync.py`**：
- 备份→生成→比对→还原（finally），路径正确；只比较受影响条目（NEW_IDS 过滤）✅
- 每个文件有独立 OK/BAD 输出 ✅

**`check_injections.py`**：
- 三注入均有可达 FAIL 路径：A(opcodes value revert → validate_vectors)、B(vector id revert → validate_vectors)、C(QEMU pattern revert → validate_decodetree) ✅
- 注入非空（`assert old in text`）、可还原（`finally: shutil.copy2`）✅
- `sys.exit(0 if ok else 1)` 不吞码 ✅

**结论**：证据脚本合格，可作为验收依据。

---

##### 2. 独立重跑（真实输出 + 退出码）

```
$ cd /mnt/tao/DADAO-v5 && .work/evidence/SPEC-101t/run.sh
== SPEC-101t evidence ==
PASS [1] live-carrier old-id residue (grep no-match)
PASS [0] four-carrier encoding agreement
PASS [0] MC assemble/objdump round-trip
PASS [0] validate_encoding
PASS [0] validate_vectors
PASS [0] validate_decodetree (source)
PASS [0] check_qemu_trans --strict
PASS [0] check_005t_coverage
PASS [0] check_interface
PASS [0] check-asm-list-drift
PASS [0] check-asm-list-consistency
PASS [0] check-legality-drift
PASS [0] check-scope
PASS [0] check-patch-tree
PASS [0] check_lit_bytes
PASS [0] check_qfc_coverage (informational)
PASS [0] vector<->generator scoped sync (ISS-125)
PASS [0] counter-example injections

== summary: 18 checks, 0 failed ==
SPEC-101t evidence: PASS
EXIT=0
```

---

##### 3. 独立反例注入（reviewer 自行执行，非 engineer 自检）

**注入点**：`contracts/opcodes.yaml` — `add.o_orrr_bbd` 的 `value` 从 `0x40C00000` 改回旧值 `0x40800000`

**注入有效性**：`git diff --name-only` 含 `contracts/opcodes.yaml`（非空注入）✅

**注入后重跑**（预期 FAIL）：
```
$ cd /mnt/tao/DADAO-v5 && .work/evidence/SPEC-101t/run.sh
== SPEC-101t evidence ==
PASS [1] live-carrier old-id residue (grep no-match)
FAIL [1] four-carrier encoding agreement   ← opcodes.yaml value 不匹配
PASS [0] MC assemble/objdump round-trip
PASS [0] validate_encoding                 ← 不校验 ha↔value（已知瑕疵）
FAIL [1] validate_vectors                  ← 4 cases word≠0x40800000
FAIL [1] validate_decodetree (source)      ← mask/value mismatch
PASS [0] check_qemu_trans --strict
PASS [0] check_005t_coverage
PASS [0] check_interface
PASS [0] check-asm-list-drift
PASS [0] check-asm-list-consistency
PASS [0] check-legality-drift
PASS [0] check-scope
PASS [0] check-patch-tree
PASS [0] check_lit_bytes
PASS [0] check_qfc_coverage (informational)
PASS [0] vector<->generator scoped sync (ISS-125)
FAIL [1] counter-example injections        ← assert 失败（value 已被改）

== summary: 18 checks, 4 failed ==
EXIT=1
```

**还原**：`cp backup → contracts/opcodes.yaml`，`diff` 确认字节一致 ✅

**还原后重跑**（预期回绿）：
```
== SPEC-101t evidence ==
PASS [1] live-carrier old-id residue (grep no-match)
PASS [0] four-carrier encoding agreement
PASS [0] MC assemble/objdump round-trip
PASS [0] validate_encoding
PASS [0] validate_vectors
PASS [0] validate_decodetree (source)
PASS [0] check_qemu_trans --strict
PASS [0] check_005t_coverage
PASS [0] check_interface
PASS [0] check-asm-list-drift
PASS [0] check-asm-list-consistency
PASS [0] check-legality-drift
PASS [0] check-scope
PASS [0] check-patch-tree
PASS [0] check_lit_bytes
PASS [0] check_qfc_coverage (informational)
PASS [0] vector<->generator scoped sync (ISS-125)
PASS [0] counter-example injections

== summary: 18 checks, 0 failed ==
EXIT=0
```

**工作区状态**：还原后 `git diff contracts/opcodes.yaml` 仅含任务本身的改动，无注入残留 ✅

---

##### 4. 约束核验

| 约束 | 结果 |
|---|---|
| 原子（1–11 一次改完） | ✅ 21 文件改动，无中间态 |
| 回归验证（零漂移/门控绿） | ✅ generate_opcodes/asm_list/legality/vectors 零漂移（ISS-125 范围内） |
| id 约定仅限表列 3 条 | ✅ grep 复核无旧 id 残留于活载体 |
| 不改指令语义/legality/字段/op/mask | ✅ 仅改 id/助记符/ha/value |
| 临时目录 | ✅ `/tmp/opencode/SPEC-101t/` |
| 不提交 git | ✅ 任务状态仍 `待验收` |
| 复杂命令输出留存 | ✅ `.work/log/{spec,llvm,qemu}/SPEC-101t-*.log` |

---

##### 5. 风险/已知局限

1. **`check_encoding.py` 不做 ha↔value 数学校验**：仅比对字面值。被跨载体门控（validate_vectors、check_interface）覆盖，不阻断。
2. **`check_mc_roundtrip.py` assemble 失败时 EXIT=0**：理论盲区，实际 assemble 成功，不阻断。
3. **ISS-125 预存漂移**：非本次引入，engineer 已按用户裁定采定向手改 + 生成器常量同步，验证脚本按受影响条目核验，合理。
4. **历史审计物 `docs/testcases-009t-audit.*`**：含旧连字符写法，不在活载体范围内，engineer 未改，合理。

---

##### 6. 判决

**Accepted**

验收命令块在 reviewer 独立重跑下全部通过（18/18 PASS，EXIT=0）；独立反例注入确认门控可失败（4 FAIL，EXIT=1）→ 还原回绿（18/18 PASS，EXIT=0）；约束无违反。
