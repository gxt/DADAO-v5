# SPEC-101t: RB 算术三条指令改名 + 改编码槽（跨组件，原子）

**模块**：spec（跨组件：spec + llvm MC + qemu + testcases 工具）
**项目里程碑**：M3
**依赖**：无（**但是**：与 `SPEC-100t` **同改 `contracts/opcodes.yaml` 与 `tests/vectors/**` ⇒ 串行**；本任务按用户 2026-10-04 裁定**先于** `SPEC-100t` 执行）
**状态**：待开始

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
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
