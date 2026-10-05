# SPEC-109t: 删 `illi` / `fence`→`0x00` / `swym`→`0x22`（MISC-AMO 编码调整，跨组件原子）

**模块**：spec
**项目里程碑**：M4
**依赖**：无
**状态**：待开始

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含；决策已定，本任务只落正文/编码，**不重新决策**）：
  - `.tao/adr/adr-0012-simrisc-0.5.4-update.md` 的 **D3 第 5 项**（2026-10-06 用户逐条确认，就地增补；`Accepted`）——**本任务唯一决策来源**。
  - **用户裁定原话（ADR-0012 D3.5，原文引用）**：「① **删除 `illi` 指令**（`op=0x77, ha=0x00`）——**ILLI 异常保留**（由非法操作数/非法条件触发，**不再**有专门的 `illi` 指令）；② **`fence` 编码 `ha` 由 `0x01` 移至 `0x00`**：`value` `0x77040000` → **`0x77000000`**（`fence` 仍 `excluded`，见 `ADR-0014`）；③ **`swym` 编码 `ha` 由 `0x02` 移至 `0x22`**：`op=0x77` 不变，`value` `0x77080000` → **`0x77880000`**。**落地**：`spec/SimRISC-00/11` + `contract-isa §13` + `contract-asm §6` + `contracts/opcodes.yaml` + LLVM MC + QEMU `insn.decode`/`trans_ctrl` + `tests/vectors` + `ADR-0004`「全零字 UNDI」注 + crt0 `swym 0`。」
  - **编码算术（自包含）**：`value = op<<24 | ha<<18`（`mask=0xFFFC0000`，`op=0x77` 不变）。
    - `fence`：`0x77<<24 | 0x00<<18 = 0x77000000`。
    - `swym`：`0x77<<24 | 0x22<<18`；`0x22<<18 = 0x880000` ⇒ **`0x77880000`**。
    - illi 记录删除；**`0x77000000` 的语义由「`illi`（m1，恒 ILLI）」变为「`fence`（`scope: excluded`，decode ILLI）」**（仍触发 ILLI，但经 fence 的 excluded 路径）。
  - **现状实测**（须以 `grep -rn` 实测为准，下为已知落点）：
    - `contracts/opcodes.yaml`：`illi_oiii_imm`（`op=0x77/ha=0x00/value=0x77000000/scope:m1`）、`fence_oiii_imm`（`ha=0x01/value=0x77040000/scope:excluded`）、`swym_oiii_imm`（`ha=0x02/value=0x77080000/scope:m1`）；总量 **228**、`m1=152`、`excluded=15`。
    - `tools/spec/check_scope.py`：`EXPECTED_M1=152`、`EXPECTED_TOTAL=228`，docstring 计数。
    - LLVM MC 补丁：`DADAOInstrInfo.td`（`def illi`/`def fence`(ha=0x01)/`def swym_oiii`(ha=0x02)）；`MCTargetDesc/DADAOAsmBackend.cpp` 的 **`writeNopData()` 硬编码 `\x77\x08\x00\x00`**（NOP = swym 0）；注释 `DADAO.h`（`FK_oiii` 示例）、`DADAOMCInstPrinter.cpp`、`DADAOInstrFormats.td`。
    - QEMU 补丁：`target/dadao/insn.decode`（`illi_oiii_imm 01110111000000…`、`fence_oiii_imm 01110111000001…`、`swym_oiii_imm 01110111000010…`）；`target/dadao/insn_trans/trans_ctrl.c.inc`（`trans_illi_oiii_imm`/`trans_swym_oiii_imm`/`trans_fence_oiii_imm`）。
    - `tools/qemu/generate_decodetree.py`（由 `opcodes.yaml` 生成 `insn.decode`/stubs）、`tools/qemu/check_qemu_trans.py`（正文数量对齐）、`tools/integ/check_interface_alignment.py`（断言 **QEMU `trans_*` 定义数 == `opcodes.yaml` 条目数**；并调 `check_lit_bytes.py`/`check_qemu_trans.py --strict`）。
    - `tests/vectors/isa/misc.yaml`（swym word `0x77080000` ×2、illi word `0x77000000` 恒 ILLI）、`tests/vectors/inventory.md`、`tests/vectors/schema.md`、`tests/vectors/isa/*` 头部计数。
    - `tests/lit/MC/Dadao/oiii.s`（`illi 0`/`swym 0`/`swym 42`，含 `; OBJ:` 字节）、`tests/lit/MC/Dadao/basic-encoding.s`（swym 注释 `0x77080000`）。
    - `tests/scripts/build_test_binary.py`（`encode_swym()`→`0x77080000`、`encode_illi()`→`0x77000000` 作 poison）、`tests/scripts/verify_harness_dump.py`（`struct.pack(">I", 0x77080000)`）、`tests/scripts/codegen_crt0.s`（`swym 0`）、`tests/e2e/smoke_*.s`（`swym 0`）。
    - `.tao/knowledge/contract-isa.md §13.1/§13.2/§13.4/§13.5/§15.1` + 附录 A.6/A.7；`.tao/knowledge/contract-asm.md §6/§8/§11`（228/152）；`.tao/adr/adr-0004-test-machine.md` 注记（第 33/137/273–281 行附近的 `illi`/`0x77000000` 表述）。
  - `spec/SimRISC-00-指令系统设计.md` §MISC-AMO 指令编码（`000-xxx` 行：`illi`/`fence`/`swym`）、`spec/SimRISC-11-其它.md`（头部「其它（6 条）」+ §占位指令 swym + §非法指令 illi）。
- **输出**（**跨组件原子，须同一落地波/提交**；否则 `check-interface`/`check_qemu_trans` 会红）：
  1. **`spec/SimRISC-00-指令系统设计.md`**：`MISC-AMO` 子表删除 `illi`；`fence` 移至 `000-000`；`swym` 移至 **`100-010`**（`ha=0x22`）；表外说明与 `op=0x77` 注同步。
  2. **`spec/SimRISC-11-其它.md`**：删除「非法指令 illi」小节的**规范性定义**（ILLI 异常本身**保留**——改述为「由非法操作数/条件/保留编码触发」）；`swym` 节明确新编码 `0x77880000`；头部「其它（6 条）— cfx2rc/cfx2rd/escape/illi/swym/trap」改为 **5 条**（去 `illi`）。
  3. **`contracts/opcodes.yaml`**（生成器 `tools/spec/generate_opcodes.py` 同步）：删除 `illi_oiii_imm` 记录；`fence_oiii_imm` `ha 0x01→0x00`、`value 0x77040000→0x77000000`；`swym_oiii_imm` `ha 0x02→0x22`、`value 0x77080000→0x77880000`。**派生计数**：`total 228→227`、`m1 152→151`、`excluded 15` 不变。
  4. **`tools/spec/check_scope.py`**：`EXPECTED_M1=152→151`、`EXPECTED_TOTAL=228→227`、docstring 同步（含 `SPEC-086t`/`ADR-0012 D9` 引用行的计数）。
  5. **`.tao/knowledge/contract-isa.md`**：§13.2 `illi` 删除（留「ILLI 异常由非法操作数/条件/保留编码触发」的说明）；§13.1 `swym`/§13.4/§13.5/§15.1（删「`illi` 指令本身」项）/附录 A.6（删 `000-000 illi`；`swym` 改 `100-010`）/A.7（`fence` `000-001`→`000-000`）；如有 228/152 计数同步。**§13.3 `nop` 伪指令归 `SPEC-106t`**（本任务不动，串行）。
  6. **`.tao/knowledge/contract-asm.md`**：§6（`nop`→`swym 0` 的编码值注，如需）；§8/§11 中 228→227、152→151。
  7. **LLVM MC**（`.work/source/llvm-project` 工作树改 → 导出补丁）：`DADAOInstrInfo.td` 删 `def illi`、`fence` `ha=0x01→0x00`、`swym_oiii` `ha=0x02→0x22`；`DADAOAsmBackend.cpp` 的 `writeNopData()` **`\x77\x08\x00\x00` → `\x77\x88\x00\x00`**；注释同步（`DADAO.h`/`DADAOMCInstPrinter.cpp`/`DADAOInstrFormats.td`）。AsmParser/Disassembler 由 `.td` 生成，无需手改（须重 build 验证）。
  8. **QEMU**（`.work/source/qemu` 工作树改 → 导出补丁）：`target/dadao/insn.decode` 删 `illi_oiii_imm` 行、`fence` pattern `…000001…`→`…000000…`、`swym` pattern `…000010…`→`…100010…`；`target/dadao/insn_trans/trans_ctrl.c.inc` 删 `trans_illi_oiii_imm`（`trans_fence_oiii_imm`/`trans_swym_oiii_imm` 保留）。`generate_decodetree.py` 由 `opcodes.yaml` 驱动（若需重生成以核验）。
  9. **测试/向量/工具**：`tests/vectors/isa/misc.yaml`（swym 2 条 word→`0x77880000`；illi 条目删除；header 注释「2 M1 identities」→1）；生成器 `tools/testcases/generate_misc.py` 同步；`tests/vectors/inventory.md`（删 illi 行、M1 身份计数同步）；`tests/vectors/schema.md`（illi/全零字 UNDI 表述）；`tests/lit/MC/Dadao/oiii.s`（删 `illi 0` 块、swym word/`ha` 注释更新、必要时补 `fence` 用例）；`tests/lit/MC/Dadao/basic-encoding.s`（swym 字节/注释）；`tests/scripts/build_test_binary.py`（`encode_swym()`→`0x77880000`；`encode_illi()`：`0x77000000` 现为 `fence`（excluded→ILLI），须改名/改述并确认 poison 语义仍为 ILLI）；`tests/scripts/verify_harness_dump.py`（`0x77080000`→`0x77880000`）；`tests/scripts/codegen_crt0.s`、`tests/e2e/smoke_*.s` 的 `swym 0` **源不变**，重新汇编后字节更新（`test-codegen` 不回归）。
  10. **`.tao/adr/adr-0004-test-machine.md`**：**注记同步**（第 33/137/273–281 行附近的 `illi`/`0x77000000` 表述），依据 `ADR-0012 D3.5` 明确列出的落地项。**边界**：仅同步**注记/示例**；若某处实为 **decision 语义**（非注记），**停下报告**并请用户逐条确认（`AGENTS.md`「已 Accepted ADR 的 decision 改动须逐条确认」）。
- **约束**：
  - **只落正文/编码、不重新决策**：`ADR-0012 D3.5` 已 `Accepted`；不得增删其未列的编码或改 `op=0x77`。
  - **同一落地波/提交（原子）**：`tools/integ/check_interface_alignment.py`（`check-interface`）断言「QEMU `trans_*` 定义数 == `opcodes.yaml` 条目数」，并调 `tools/llvm/check_lit_bytes.py`（LLVM lit `; OBJ:` ↔ opcodes）与 `tools/qemu/check_qemu_trans.py --strict`。⇒ `opcodes.yaml`/LLVM MC/QEMU 三侧**必须一次改完**，分次落必使门控红。
  - **全库 grep 穷尽**：`grep -rn "illi\|swym\|fence\|0x77080000\|0x77040000\|0x77000000"`，逐个判定；**排除** `.tao/archive/`、`.work/`、历史 ADR 状态说明（`ADR-0012` 的 2026-10-06 增补行本身）、以及 `ADR-0012 D5/D9` 等历史项。`.tao/archive/**` 与 `docs/m1-retrospective.md` 为历史记录，**不改写**。
  - **补丁纪律（`spec/Process-01`）**：LLVM/QEMU 改动**只能**在 `.work/source/{llvm-project,qemu}` 工作树进行；`commit --amend` 收敛 base+1 → `tools/infra/make_patch.py` 导出裸 `git diff`；写 `/tmp`、非空 blob；`make check-patch-tree`（含断言⑥）通过；**不手改** `components/**/patches/**`。
  - **构建纪律**：LLVM 用 `ninja -j8 -C .work/build/llvm llvm-mc llvm-objdump llvm-readobj`（复用 `build-mc` 增量，勿全量 reconfigure）；QEMU 用 `make build-qemu`。受 `JOBS`（默认 8）限制、**禁 `-j$(nproc)`**；开始前写明预计耗时；失败即停、不自动重试。
  - **串行**：本任务为 M4 链首；与后续同改 `spec/`/`contracts/`/`components/`/`tests/` 的任务**串行**（`AGENTS.md`「同改共享文件一律串行」）。`SPEC-106t` 依赖本任务（共享 `SimRISC-00/11`、`contract-asm §6`）。
  - 临时目录 `/tmp/opencode/SPEC-109t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（LLVM/QEMU 输出另存 `.work/log/llvm/`、`.work/log/qemu/`）。

## 验收标准

1. **门控全绿**：`make check` EXIT=0（含 `validate-encoding`/`check-scope`/`check-interface`/`check-instrinfo`/`check-legality-drift`/`check-asm-list`/`check-asm-list-drift`/`check-spec-codeblocks`/`check-lit`）；`make check-patch-tree` EXIT=0；逐条给真实输出与退出码。
2. **编码表**：`grep -n "illi" contracts/opcodes.yaml` **无记录**；`fence` `value=0x77000000`、`swym` `value=0x77880000`；`check-scope` 输出 `m1=151`/`total=227`/`excluded=15`（真实输出）。
3. **LLVM MC**：重 build 后——`llvm-mc` 汇编 `swym 0` → 字节 `77 88 00 00`、`fence 0` → `77 00 00 00`；`illi 0` → `unrecognized instruction mnemonic`（非零退出）；`swym` 反汇编往返一致；`.align`/nop padding 用 `77 88 00 00`（给 `llvm-objdump`/hexdump 真实输出）。
4. **QEMU**：重 build 后——`swym`（`0x77880000`）执行 NOP 可达 exit；`0x77000000`（fence，excluded）→ ILLI（host `$?=0x88`）；`tools/qemu/check_qemu_trans.py --strict` EXIT=0；`trans_*` 定义数 == 227。
5. **不回归**：`make test-codegen`（M3 15/15）EXIT=0（crt0 的 `swym 0` 重汇编）；`make check-qemu-semantics` EXIT=0。
6. **残留清零**：全库 grep 后，除 `.tao/archive/**`、`.work/**` 与历史 ADR 说明外，`illi`（指令义）与 `0x77080000`/`0x77040000` **无残留**；`tests/vectors/isa/misc.yaml` swym word = `0x77880000`。
7. **反例门控**：一键证据脚本 `.work/evidence/SPEC-109t/run.sh`（非交互、失败非零、逐项打印、结尾无 `tee`）——`--inject` 至少 2 类：（a）把 `opcodes.yaml` swym `value` 改回 `0x77080000`；（b）把 `illi_oiii_imm` 记录加回（或把 `trans_illi_oiii_imm` 加回）——均须使 `make check`/`check-interface` **FAIL**；还原 + **重建 LLVM/QEMU** → 回绿。给真实输出与退出码。
8. `git status --untracked-files=all` 仅本任务应有改动（`spec/`/`contracts/`/`components/*/patches/**`/`tools/`/`tests/`/`.tao/knowledge/`/`.tao/adr/adr-0004…`）；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
