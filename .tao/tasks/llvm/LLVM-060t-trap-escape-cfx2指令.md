# LLVM-060t: `trap`/`escape`/`cfx2rc`/`cfx2rd`（MC parser/printer/disassembler/编码 + 必要 CodeGen）

**模块**：llvm
**项目里程碑**：M5
**依赖**：`INFRA-047t`（2026-10-07 用户裁定 1 重排：**去掉 `SPEC-115t`**——本任务**前置**于 `SPEC-115t`；编码 `op`/`mask`/`value` 在 `SPEC-115t` 前后不变，re-scope 只改 `scope`/`decode`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - **现行** `contracts/opcodes.yaml`（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx` **编码已定义**，现 `scope: excluded`/`decode: ILLI`——**本任务阶段不改其 `scope`**；`op`/`mask`/`value` 与 `SPEC-115t` re-scope 后一致）+ `contracts/legality_rules.yaml` + `.tao/knowledge/contract-isa.md`/`contract-asm.md`/`contract-asm-list.md`。
  - **说明（2026-10-07 用户裁定 1 重排）**：本任务**前置**于 `SPEC-115t`——按现有编码实现 `.td`/MC；`SPEC-115t` 随后 re-scope（`excluded`→`m1`）并收口门控。本任务产出的 `.td` def 与 lit `; OBJ:` 是 `SPEC-115t` 转绿的**前置**。
  - `spec/SimRISC-11-其它.md`（§陷入指令 `trap cfxHA, immu18`；§退出指令 `escape cfxHA, [excp_cause_ip, imms20]`；§寄存器传输指令 `cfx2rc`/`cfx2rd cfxHA, cgHB, rcHC, rdHD`；**两种 cfx 写法** `cfx<cfxha>`（如 `cfx63`）与 `cfx_<cfxname>`（如 `cfx_power`/`cfx_umon`）；**简化 regname 写法** `cfx2rd cfx_umon_excp_cause_ip, rd2` 等价标准三操作数写法）。
  - `spec/Toolchain-01-汇编语言.md §3.2`（**字段名映射**：汇编 `imms20`（字节，`%4==0`）⇔ 编码 `imms18`（`field = bytes >> 2`）；`Addr = excp_cause_ip + (imms18 << 2)`）；`§2.5`（寄存器名）；`§4`（寄存器组/条件）。
  - `.tao/knowledge/contract-cfx-aliases.md`（cfxname ↔ cfxha 别名表，供 `cfx_<name>` 解析）+ `tools/spec/check_cfx_aliases.py`。
  - `INFRA-047t` 后的 install 根：构建用工具从 `$(HOST_TOOLCHAIN_BIN)` 取（如适用）；构建树仍 `.work/build/llvm`（`build-mc`/`build-mc-lite`）。
  - **参照范式（只读）**：RISC-V/PPC 的 `crrr`/`ciii` 类指令在 `llvm/lib/Target/{RISCV,PPC}/` 的 AsmParser/InstPrinter/Disassembler 写法；`DADAOAsmParser.cpp`/`DADAOInstPrinter`/`DADAODisassembler` 现有结构。
- **输出**（组件源码改在 `.work/source/llvm-project`；**导出补丁**）：
  1. **编码/汇编支持**（`llvm/lib/Target/DADAO/**`）：`trap`（`ciii`）、`escape`（`ciii`）、`cfx2rc`/`cfx2rd`（`crrr`）——`.td` 指令定义（op/ha/mask/value 与 `contracts/opcodes.yaml` 一致）、**AsmParser**（含 `cfx<ha>` 与 `cfx_<name>` 两种写法解析等价、`cfx2rd/cfx2rc` **简化 regname 写法**展开为标准三操作数）、**InstPrinter**、**Disassembler**。
  2. **`escape` 位宽关系**：汇编层接受 `imms20`（字节、`%4==0`，越界/非 4 倍数**报错**），编码层写 `imms18 = bytes >> 2`；**反汇编**由 `imms18` 还原（`bytes = imms18 << 2`）。与 `Toolchain-01 §3.2` 一致。
  3. **cfxha 解析**：`cfx<ha>`（0–63）与 `cfx_<name>`（经 `contract-cfx-aliases`）等价编码为 6 位 `cfxha`。**reserved cfxha（7–14、19–61）的汇编期处置**：按 spec（`SimRISC-11 L121`：reserved ⇒ ILLI；但那是**执行期**语义）——**汇编期是否拒绝 reserved cfxha** 依 `contracts/legality_rules.yaml`（`SPEC-115t` 定），**以契约为准**，不臆断。
  4. **必要 CodeGen**：`trap`/`escape` 为 `ciii`（无寄存器结果）、`cfx2rd` 有 rd 结果——是否需 `DADAOInstrInfo.td`/内建/intrinsic 支持，**以“能编出 bootrom 所需最小序列”为界**（bootrom 由 `QEMU-047t` 编写；如只需汇编层，CodeGen 可最小）。**不得**超出 `SimRISC-11 §其它` 4 条范围（`SimRISC-12` 保持 deferred）。
  5. **L1 MC 向量（自带，`Process-05 §3`「一能力一向量」）** + **编码 oracle**（独立派生自 `contracts/opcodes.yaml`，**禁从 `llvm-mc` 反推**）：落 `tests/llvm/lit/MC/DADAO/`。**重排后本任务为本 M5 指令链首发**（`SPEC-115t` 在后）⇒ **本任务自带最小向量**（`TESTCASES-033t` 后续复用/扩展）。**往返**（汇编↔反汇编）覆盖。
  5b. **门控前置产出（2026-10-07 用户裁定 1 重排新增）**：① `tests/llvm/lit/MC/DADAO/*.s` **须含 `crrr`/`ciii` 的 `; OBJ:` 覆盖**（4 条 cfx 的编码），供 `SPEC-115t` re-scope 后 `check-interface` 的「每 M1 `format` 族须有 lit `; OBJ:`」转绿；② `tools/llvm/validate_instrinfo.py`：把 4 条 id **加入** `MC_ONLY_EXCLUDED_IDS`（本任务阶段 4 条仍 `scope: excluded` 但 MC 层需 `.td` def，与既有 `fence_oiii_imm` 同理；否则 `non-m1` 检查 FAIL）。**移除**由 `SPEC-115t` 在 re-scope 时执行（跨任务契约，见其任务书）。
  6. **补丁集导出**：`components/llvm-project/patches/**` + `series`（`make_patch.py`）；`changelog.md` 追加一条。
  6b. **别名表生成器随产物入库（2026-10-07 增补，规则缺口修复）**：`DADAOCfxAlias.inc.patch` 的内容由**生成器**从 `contract-cfx-aliases.md`（复用 `tools/spec/gen_cfx_aliases.py` 的同一投影逻辑）生成 ⇒ 按 `AGENTS.md`「生成器随产物保留」，判据 = **产物是否入库**（本例产物 `components/llvm-project/patches/**/AsmParser/DADAOCfxAlias.inc.patch` 已入库；**「一次性」只描述用途，不等于可丢弃**），生成器**须随产物入库**——落点 `tools/llvm/gen_cfx_alias_table.py`：由 engineer 从 `.work/LLVM-060t/gen_cfx_cpp_table.py` **迁入**（跨任务可复用、可审计），并使其**可复现生成**该 `.inc` 的 patch 内容；**不得**只留在 `.work/`（`.work/` 被 gitignore ⇒ 不入库）。
- **约束（硬）**：
  - **补丁导出纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/llvm-project` 工作树；`commit --amend` 收敛 base+1 → `make_patch.py` 导出（裸 `git diff`）；**不手改补丁**；`make check-patch-tree`（含**断言⑥**应用产物一致性）通过；补丁写 `/tmp` 不确定时按 `Process-01`。
  - **生成器随产物入库（2026-10-07 增补）**：`tools/llvm/gen_cfx_alias_table.py`（别名表生成器，见输出 6b）**属允许文件集**，须与产物 `DADAOCfxAlias.inc.patch` 一并入库；**不得**只留 `.work/`（gitignored）。
  - **不改** `SimRISC-12` 范围（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*` 保持 excluded/decode ILLI）。
  - **期望值独立派生**（`Process-05 §4`）：L1 向量期望编码来自 `contracts/opcodes.yaml`，**不从 `llvm-mc` 反推**。
  - **组件锁**：以 `manifests/components.lock.toml` 的 commit 为 base；不改基线。
  - **重建成本申报**：`build-mc` 首次视现状可能重配 + 编译（**LLVM 全量 30–90 分钟；本任务多为 MC 增量，开工前写明预计耗时**）；受 `JOBS`（默认 8）限制；失败即停、**禁自动重试**。
  - 临时目录 `/tmp/opencode/LLVM-060t/`；**不提交 git**；复杂命令输出留存 `.work/log/llvm/`（**禁 `tee`**）。
  - **注入/还原纪律**：注入反例后**还原须含重建**（源码还原 ≠ 二进制还原）；还原用 `cp`+`md5` 对账，**禁 `git checkout`/`git restore`/`git stash`**。

## 验收标准

1. **构建**：`make build-mc`（或经 install 根的等价）EXIT=0；给真实输出。
2. **汇编正例**：`llvm-mc --triple=dadao-unknown-elf` 对 `trap cfx_smon, 1`、`trap cfx63, 0`、`escape cfx_umon, [excp_cause_ip, 4]`、`cfx2rd cfx_umon_excp_cause_ip, rd2`、`cfx2rc cfx_power_ctrl, rd2` 各 EXIT=0，字节 == `contracts/opcodes.yaml` 派生期望（给真实输出）。
3. **`cfx_<name>`/`cfx<ha>` 等价**：`cfx_power` ≡ `cfx63`、`cfx_umon` ≡ `cfx0` 编码一致（≥2 对）。
4. **简化 regname 写法**：`cfx2rd cfx_umon_excp_cause_ip, rd2` ≡ `cfx2rd cfx_umon, cg5, rc3, rd2`（给真实输出）。
5. **`escape` 位宽**：`escape cfx0, [excp_cause_ip, 8]` 编码 `imms18 == 2`；`escape cfx0, [excp_cause_ip, 6]`（非 4 倍数）**报错非零**；越界 `imms20` 报错（给真实输出）。
6. **反汇编/往返**：`llvm-objdump -d --triple=dadao-unknown-elf` 还原助记符（≥1 往返用例）。
7. **独立 oracle + 反例门控**：L1 向量经独立 oracle（`validate_mc_vectors.py` 扩展或本任务自带）EXIT=0；注入反例（改一条期望字节/改一条 `.s`）⇒ oracle **非零退出** ⇒ 还原回绿（给真实输出）。
8. **不回归**：`make check` EXIT=0；`make check-patch-tree` EXIT=0（断言⑥）；`make check-lit` EXIT=0。
9. **一键证据脚本**：`.work/evidence/LLVM-060t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（源码注入 → 重建 → FAIL → 还原 → 重建 → 回绿），结尾**禁 `tee`**；给真实输出与退出码。
10. **无残留**：`git status --untracked-files=all` 仅组件补丁（`components/llvm-project/**`）+ L1 向量（`tests/llvm/lit/MC/DADAO/**`，含 `crrr`/`ciii` 的 `; OBJ:`）+ `tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` += 4 条）+ **`tools/llvm/gen_cfx_alias_table.py`（别名表生成器，随产物入库，见输出 6b）** + 本任务书；`.work/source/llvm-project` worktree clean（`check-source-state`）。

## 完成区

**测试结果**：全绿。`make build-mc` EXIT=0；`make check` EXIT=0（含 `check-instrinfo`/`check-interface`/`check-lit` 62/62）；`check-patch-tree` EXIT=0；一键证据脚本 `.work/evidence/LLVM-060t/run.sh` **pass=22 fail=0，EXIT=0**（含注入自检两轮：向量注入 → oracle FAIL → 还原 → 回绿；源码注入 → 重建 → lit FAIL → 还原+重建 → 回绿）。

**修改文件**（与 `git status --untracked-files=all` 逐条一致）：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAO.h.patch`（+FK_crrr=9/FK_ciii=10）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrFormats.td.patch`（+`DADAOCrrr`/`DADAOCiii` 格式类）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`（+cfxha/cg/rc 操作数类与类型 + 4 条 def）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（cfx 操作数解析/别名表/escape 特例/ciii 立即数范围）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOCfxAlias.inc.patch`（**新增** 生成别名表）
- `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCInstPrinter.cpp.patch`（+FK_crrr/FK_ciii 打印；删死分支）
- `components/llvm-project/series`（+1 行）
- `tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s`（**新增** L1 向量，含 crrr/ciii 的 `; OBJ:`）
- `tests/llvm/lit/MC/DADAO/cfx2-trap-escape-err.s`（**新增** 反例）
- `tests/llvm/lit/MC/DADAO/validate_cfx_vectors.py`（**新增** 独立 oracle）
- `tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` += 4 条 + `FMT_BY_CLASS` += crrr/ciii）
- 本任务书

组件源码改在 `.work/source/llvm-project`（worktree clean、HEAD=base+1，`check-source-state` EXIT=0）；补丁由 `make_patch.py` 导出（6 written / 52 unchanged，`series` 57→58 条）。

**验收结果**（真实输出/rc；日志 `.work/log/llvm/LLVM-060t-*.log`）：

1. 构建 `make build-mc` EXIT=0（`LLVM-060t-build-mc.log` 末 `build-mc: PASS`）。
2. 汇编正例（`llvm-mc --triple=dadao-unknown-elf -filetype=obj` + `llvm-objdump -d`，均 rc=0）：
   ```
   7f 08 00 01  trap cfx2, 1                        # trap cfx_smon, 1
   7f fc 00 00  trap cfx63, 0
   7e 00 00 01  escape cfx0, [excp_cause_ip, 4]     # escape cfx_umon, [excp_cause_ip, 4]
   7a 00 50 c2  cfx2rd cfx0, cg5, rc3, rd2          # cfx2rd cfx_umon_excp_cause_ip, rd2
   7b fc 80 42  cfx2rc cfx63, cg8, rc1, rd2         # cfx2rc cfx_power_ctrl, rd2
   ```
   与 `contracts/opcodes.yaml` 独立派生值一致（`trap`=0x7F/`escape`=0x7E/`cfx2rd`=0x7A/`cfx2rc`=0x7B，mask 0xFF000000）。
3. `cfx_<name>`/`cfx<ha>` 等价（≥2 对）：`trap cfx_power, 0` ≡ `trap cfx63, 0` = `7f fc 00 00`；`trap cfx_umon, 0` ≡ `trap cfx0, 0` = `7f 00 00 00`。
4. 简化 regname ≡ 长形：`cfx2rd cfx_umon_excp_cause_ip, rd2` ≡ `cfx2rd cfx_umon, cg5, rc3, rd2` = `7a 00 50 c2`；`cfx2rc cfx_power_ctrl, rd2` ≡ `cfx2rc cfx_power, cg8, rc1, rd2` = `7b fc 80 42`。
5. `escape` 位宽：`escape cfx0, [excp_cause_ip, 8]` = `7e 00 00 02`（imms18=2）；`… , 6` ⇒ rc=1 `error: escape offset must be a multiple of 4 bytes (imms20)`；`…, 524288`/`-524292` ⇒ rc=1 `escape byte offset out of range`（给真实输出）。
6. 反汇编/往返：`llvm-objdump -d` 还原助记符（如 `cfx2rd cfx0, cg5, rc3, rd2`）；`llvm-mc -filetype=asm` 规范化 → 重汇编 → `cmp` 对象文件一致（roundtrip rc=0）。
7. 独立 oracle：`python3 tests/llvm/lit/MC/DADAO/validate_cfx_vectors.py` **14 向量 0 错 EXIT=0**（不调用 llvm-mc；从 `contracts/opcodes.yaml` + `contract-cfx-aliases.md` 派生）。注入反例（改一条 `@enc`）⇒ oracle EXIT=1 且打印 `期望 7f080002，独立派生 7f080001`；还原 ⇒ EXIT=0（真实输出见 run.sh 日志）。
8. 不回归：`make check` EXIT=0（`check-instrinfo` PASS 157 defs/6 non-m1 均在 allow-list；`check-interface` `check_lit_bytes: 157 patterns OK`；`check-lit` 62/62）；`make check-patch-tree` EXIT=0（断言⑥）；`make check-lit` EXIT=0。
9. 一键证据脚本：`.work/evidence/LLVM-060t/run.sh` EXIT=0，`SUMMARY: pass=22 fail=0`（非交互、逐项打印、失败非零、结尾 `exit` 非 `tee`）。
10. 无残留：`git status --untracked-files=all` 仅上列文件；`.work/source/llvm-project` worktree clean（`check-source-state` EXIT=0）。

**新发现/坑**：
1. **DADAOAsmParser 诊断枚举与基类 `MatchResultTy` 数值撞车（既存潜在缺陷）**：`DADAOAsmParser` 的 `GET_OPERAND_DIAGNOSTIC_TYPES` 匿名 `enum` **无 `= FIRST_TARGET_MATCH_RESULT_TY` 偏移**（对照 X86：`enum X86MatchResultTy { Match_Unsupported = FIRST_TARGET_MATCH_RESULT_TY; ... }`）。故只新增一个诊断类型名（如 `InvalidCFXOperand`，字母序在 `InvalidImmediate` 前）就把 `Match_InvalidImmediate` 由 **0** 挤到 **1**（= `Match_InvalidTiedOperand`），使 `wpn_err_*` 三条既有 lit 由「invalid operand」变「invalid tied operand」而 FAIL。**规避**：本任务 3 个 cfx 操作数类复用 `DiagnosticType = "InvalidImmediate"`（`std::set` 去重 ⇒ 仍只有 1 个枚举项，数值与改前逐字节相同）。**建议后续**：按 X86 加偏移 + 在 `matchAndEmitInstruction` 显式加 `case Match_Invalid…:`，消除该隐患（本任务未改，属任务外范围）。
2. **cfx 反汇编取「`cfx<ha>`」而非「`cfx_<name>`」**：`cfx_<name>` 仅作输入糖（ADR-0017 D6/D10）；反汇编输出 `cfx<ha>, cgN, rcN, rdHD` 规范长形，对全部 cfxha（含 reserved）都可往返；spec §特权指令明列两种写法等价。若后续要求输出别名名，再补反查表。
3. **reserved cfxha 汇编期处置**：`contracts/legality_rules.yaml::encode_cfx` 为 `status: deferred`（执行期 ILLI，非汇编期）⇒ 汇编器**接受** cfxha 7–14/19–61 并原样编码（未臆断拒绝）。若 `SPEC-115t` 将其转 active，需另加汇编期检查。
4. **别名表生成器落点**：`DADAOCfxAlias.inc` 由 `.work/LLVM-060t/gen_cfx_cpp_table.py` 从 `tools/spec/gen_cfx_aliases.py` 的同一投影逻辑生成（保证与漂移门控的 `contract-cfx-aliases.md` 不漂移）。因 `验收 10` 限定残留文件集（`tools/**` 只允许 `validate_instrinfo.py`），生成器按 `AGENTS.md`「生成器随产物保留」的**次选**规则留在 `.work/LLVM-060t/`；**建议**主会话裁定是否迁入 `tools/llvm/` 随产物入库。

**遗留问题**：
1. **CodeGen 未扩展**（`Pattern = []`）：`trap`/`escape`/`cfx2rd`/`cfx2rc` 仅 MC 层（汇编/反汇编/编码）。任务输出 4 允许「如只需汇编层，CodeGen 可最小」。若 `QEMU-047t` 的 bootrom 需从 C 发射这些指令，再补 intrinsic/CodeGen（本任务不越界）。
2. **`escape` 的符号偏移不支持**：非常量偏移（如 `[excp_cause_ip, sym]`）显式报错（`escape offset must be a constant (imms20)`）。因 `excp_cause_ip` 非 PC，符号相对重定位无定义；若将来需要，须先定重定位类型。
3. **cfx 数组寄存器**：仅实现单下标 `cfx_<…>[N]`（ADR-0017 D10）；generic `scratch_regs[0..N−1]` 因 N 为硬件参数，按 `[0..63]` 接受（汇编器无法得知 per-cfx N）。
4. **`SimRISC-12` 范围未动**：`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*` 保持 `excluded`/decode ILLI（任务约束）。

**第 2 轮（生成器随产物入库）**（2026-10-07，规则缺口修复；architect 修订输出 6b/约束/验收 10 后补做）：

- **用户裁定（原话）**：迁入 `tools/llvm/gen_cfx_alias_table.py` 时，生成物内 provenance 注释行（`// Generator: …`）的处置——主会话以 `question` 给出三选一，用户选定 **「更新为 tools/llvm/gen_cfx_alias_table.py 并重新导出 patch」** ⇒ **授权改动** `DADAOCfxAlias.inc.patch` 的该 1 行注释（无表数据/编码变更）。
- **迁入**：`.work/LLVM-060t/gen_cfx_cpp_table.py` → `tools/llvm/gen_cfx_alias_table.py`（**复用** `tools/spec/gen_cfx_aliases.py` 的投影函数，未另造轮子；新增 `--out` 便于对临时路径校验；provenance 行按项目惯例（对齐 `tools/llvm/gen_asm_list.py`）改为生成器当前路径）。
- **可复现性（真实 `cmp` 输出与退出码）**：重跑生成器后 worktree `.inc` 逐字节不变（`git -C .work/source/llvm-project status --porcelain -uall` **空**）；`git diff <base> -- …/DADAOCfxAlias.inc`（`<base>` = `manifests/components.lock.toml` 的 `6dfe167…`）与已入库 patch：
  ```
  $ git -C .work/source/llvm-project diff 6dfe1677… -- llvm/lib/Target/DADAO/AsmParser/DADAOCfxAlias.inc > regen.patch
  $ cmp regen.patch components/llvm-project/patches/…/AsmParser/DADAOCfxAlias.inc.patch
  cmp EXIT=0
  $ md5sum regen.patch components/…/DADAOCfxAlias.inc.patch
  56814bc235fe6f6462c71dc9b2d7371a  regen.patch
  56814bc235fe6f6462c71dc9b2d7371a  components/…/DADAOCfxAlias.inc.patch
  ```
- **补丁重导出**：`python3 tools/infra/make_patch.py llvm-project` ⇒ `make-patch: 1 written, 57 unchanged (skipped)`；`git diff` 该 patch == **1 provenance 行**（`- // Generator: .work/…` → `+ // Generator: tools/llvm/gen_cfx_alias_table.py`，另 new-file blob `index 000…157e2d6ec` → `…392d53913` 随内容更新，属必然）。`make check-patch-tree` **EXIT=0**（`90 patches OK`）；`make check` **EXIT=0**（`repository checks: PASS`，含 `check-lit 62/62`）。
- **证据脚本**：`.work/evidence/LLVM-060t/run.sh` 新增 section **2b** 三条断言（生成器存在且可运行 / 重跑不改 worktree / `cmp` 复现 patch）；保护既有断言与注入 A/B 自检；结尾 `exit 0|1`（无 `tee`）。重跑真实输出：**`SUMMARY: pass=25 fail=0`，`EXIT=0`**（`inject A`：oracle FAIL→还原→回绿；`inject B`：源码注入→重建→lit FAIL→还原+重建→回绿）。日志 `.work/log/llvm/LLVM-060t-r2-evidence.log`（终版实测 `.work/log/llvm/LLVM-060t-r2-evidence-final.log`，同 `pass=25 fail=0 EXIT=0`）。
- **修改文件**（与 `git status --untracked-files=all` 逐条一致）：
  - `tools/llvm/gen_cfx_alias_table.py`（**新增**，别名表生成器；见输出 6b）
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOCfxAlias.inc.patch`（1 行 provenance + new-file blob index）
  - `.work/source/llvm-project` HEAD 收敛为 base+1（`0e9e52f7b`，worktree `clean=True`，`check-source-state` EXIT=0）
  - 本任务书
- **遗留**：无新增（R1 遗留 1–4 不变）。

## 审阅记录

#### 第 2 轮 engineer 自审
自主逐行审查（subagent_depth=1，无嵌套子代理）。对象：新建 `tools/llvm/gen_cfx_alias_table.py` + `.work/evidence/LLVM-060t/run.sh` 新增 section 2b + 重导出的 `.inc.patch`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1 生成物 provenance 行仍指旧 `.work/…` 路径，迁入后失真 | ✅已修（经用户授权） | 生成器输出行改为 `tools/llvm/gen_cfx_alias_table.py`，`make_patch` 重导出 patch | 上述 `cmp EXIT=0` / `make check-patch-tree EXIT=0` |
| G2 迁入须复用 `gen_cfx_aliases.py` 投影逻辑，不得另造轮子 | ✅已修（设计即此） | 直接 `from tools.spec.gen_cfx_aliases import (parse_cfxcode_table, parse_register_tables, build_scalar_aliases, build_register_aliases, read_file)` | 输出 13 scalar/66 generic/34 specific，与 R1 完全一致；`cmp EXIT=0` |
| G3 重跑生成器不得弄脏组件 worktree（否则 E1/无残留破） | ✅已核 | 生成到 worktree `SRC_OUT`；内容不变 ⇒ `git status` 空 | `git -C .work/source/llvm-project status --porcelain -uall` 空；`check-source-state … clean=True` |
| G4 新断言须「可失败」（非恒真） | ✅已证 | section 2b 有 4 条可达 FAIL 路径（缺文件/非零退出/worktree 脏/`cmp!=0`） | 自审注入：篡改已入库 patch ⇒ `cmp EXIT=1`（`EOF … after byte 6070`）⇒ `cp`+`md5` 还原（`56814bc…` 相符）⇒ `cmp EXIT=0` |
| G5 清理新建脚本内的孤儿局部变量 | ✅已修 | 校验循环 `name` → `_name`（未使用） | 清理后重跑生成器 ⇒ `cmp EXIT=0`（输出无变化） |
| G6 允许文件集不得越界 | ✅已核 | 仅新增 `tools/llvm/gen_cfx_alias_table.py` + 改 1 patch + `.work/`（gitignored） | `git status -uall` 仅 2 项（1 `??` + 1 `M`），无 `spec/` 改动 |

判决：**全部 finding 已处置**，任务状态保持 `待验收`，返回主会话交 reviewer 独立验收（含对本新断言的独立反例注入）。

#### 第 1 轮 engineer 自审
自主逐行审查（subagent_depth=1，无嵌套子代理）。审查对象：本轮 5 个组件源文件改动 + 生成别名表 + lit 向量/反例 + oracle + `validate_instrinfo.py`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 新增 `DiagnosticType="InvalidCFXOperand"` 使 `Match_InvalidImmediate` 由 0→1，撞 `Match_InvalidTiedOperand`，`wpn_err_*` 3 条既有 lit FAIL | ✅已修 | 3 个 cfx 操作数类改用 `DiagnosticType="InvalidImmediate"`（枚举去重 ⇒ 数值与改前逐字节相同） | `make check-lit` 62/62 EXIT=0；`set.zw rb1, 1, 0xffff` ⇒ `invalid operand for instruction`（改前预期） |
| F2 `parseOperand` 的 cfx 分支须在「裸数字被拒」时显式失败（不得静默接受） | ✅已修（设计即此） | cfxha/cg/rc 为**独立** operand kind（`isCfxhaImm`/`isCfxCgImm`/`isCfxRcImm` 仅匹配各自记号） | `trap 2, 1`/`cfx2rd cfx0, 5, 3, rd2` ⇒ rc=1 `invalid operand`；run.sh reject 用例 |
| F3 `escape` 越界/非 4 倍数须报错而非静默环绕；负偏移须算术右移 | ✅已修（设计即此） | parse 期校验 `%4==0` + `[-524288,524284]`，`Bytes>>2` | `…, 6`/`…, 524288` ⇒ rc=1；`…, -8` ⇒ `7e 03 ff fe`（imms18=-2） |
| F4 别名表可能与 `contract-cfx-aliases.md` 漂移 | ✅已修 | 生成器直接复用 `tools/spec/gen_cfx_aliases.py` 的投影函数；生成头注明来源 | 生成输出 13 标量/66 通用/34 专有；抽查 `cfx_timer_regs`=rcBase 8（非 0，用 rc 列下界）、`cfx_ptw_ptbr`=count 64 |
| F5 反汇编需保证「往返一致」（含 reserved cfxha） | ✅已修（设计即此） | printer 输出 `cfx<ha>, cgN, rcN, rd`（对 reserved 亦可重汇编）；`cmp` 真往返 | `make check`/run.sh 的 `cmp` rc=0 |
| F6 oracle 的 `VEC_GLOB` 硬编码本目录，无法在临时副本上做注入自检 | ✅已修 | 加 `CFX_VEC_DIR` env 覆盖（镜像 `validate_mc_vectors.py` 的 `MC_VEC_DIR`） | run.sh 注入 A：临时副本改 `@enc` ⇒ oracle EXIT=1；还原 ⇒ EXIT=0 |
| F7 run.sh 注入 A 的临时向量误命名 `vec.s`，oracle 因「无 `cfx2-*.s`」假 FAIL | ✅已修 | 临时文件改名为 `cfx2-inject.s` | 注入 A 日志出现真正的 `[@enc] 期望 7f080002，独立派生 7f080001` |
| F8 `MCTargetDesc/DADAOMCInstPrinter.cpp` 的 FK_rrii 内 `escape` 分支为死代码（escape 现为 ciii），且其语义错误 | ✅已修 | 删除该死分支（与本任务同一助记符，非无关遗留） | esc 路径由 FK_ciii 处理；`make check` 全绿 |
| F9 `validate_instrinfo.py` 需能解析 `DADAOCrrr`/`DADAOCiii`（否则 allow-list 检查必 FAIL） | ✅已修 | `FMT_BY_CLASS` += crrr/ciii（任务书只点名 `MC_ONLY_EXCLUDED_IDS`，此为其必要条件，已披露） | `check-instrinfo` `PASS: non-m1 — 6 个非 m1 def 均在 allow-list`；157 defs / 0 errors EXIT=0 |
| F10 反例字节注入须「可失败」且无需重建（实现侧的注入另由 run.sh inject B 承担） | ✅已修 | oracle 与 `; OBJ:` 交叉校验；run.sh inject A/B 双路径 | run.sh `pass=22 fail=0`（A：oracle FAIL→还原→回绿；B：源码→重建→lit FAIL→还原+重建→回绿） |

判决：**全部 finding 已修**，任务状态可置 `待验收`。已知未修项（非 finding，属范围/契约）：`encode_cfx` deferred（reserved cfxha 不拦）、CodeGen 未扩展、escape 符号偏移不支持——均记入「遗留问题」并说明理由。

#### 第 1 轮 reviewer 验收（2026-10-07）

审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例** + 逐条验收 1–10 + 补丁树核验 + 判决。

**1. 证据脚本审核** `.work/evidence/LLVM-060t/run.sh`（185 行）：

| 检查项 | 结论 |
|--------|------|
| 结尾退出码 | `exit 0` / `exit 1`（非 `tee` 吞码）✓ |
| 注入 A（向量 `@enc`） | `sed` 改 `7f080001→7f080002` + `CFX_VEC_DIR` 覆盖 + 还原 `cp` ✓ |
| 注入 B（源码 `>>2→>>1`） | `python3` 锚点替换 + `JOBS=8 make build-mc` 重建 + `cp`+`md5` 还原 + 重建 ✓ |
| 注入 B 含重建 | 是（`JOBS=8 make build-mc` 两次：注入后 + 还原后）✓ |
| 可达 FAIL 路径 | 25 条断言各有独立 FAIL 分支，无恒真 ✓ |
| `CFX_VEC_DIR` 传播 | inline `VAR=val cmd` 语法正确，oracle 用 `os.environ.get("CFX_VEC_DIR")` ✓ |

**2. 重跑**（完整，含重建；真实输出）：

```
== LLVM-060t evidence ==
repo    : /mnt/tao/DADAO-v5
tools   : /mnt/tao/DADAO-v5/.work/build/llvm/bin
vec     : tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s
-------------------------------------------------------------
PASS: oracle(independent) rc=0
PASS: lit OBJ (bytes vs ; OBJ:) rc=0
PASS: lit ASM (canonical form) rc=0
PASS: roundtrip obj == reassembled obj rc=0
PASS: generator runs (tools/llvm/gen_cfx_alias_table.py) rc=0
PASS: regeneration byte-identical to committed worktree .inc (worktree clean)
PASS: generator reproduces committed DADAOCfxAlias.inc.patch byte-for-byte (cmp rc=0)
PASS: reject [escape %4==0] rc=1
PASS: reject [escape range hi] rc=1
PASS: reject [escape range lo] rc=1
PASS: reject [escape nonconst] rc=1
PASS: reject [escape base] rc=1
PASS: reject [trap immu18] rc=1
PASS: reject [cfxha bare num] rc=1
PASS: reject [cg bare num] rc=1
PASS: reject [bad alias] rc=1
PASS: reject [array no subscript] rc=1
PASS: reject [array subscript] rc=1
PASS: check-instrinfo (validate_instrinfo.py) rc=0
[inject A] oracle FAILs on corrupted @enc (rc=1)
  (inject A evidence: @enc 期望 7f080002，独立派生 7f080001)
PASS: oracle green after temp restore (rc=0)
[inject B] source injection (escape shift >>2 -> >>1) + rebuild
  injected: md5 b13e63a9… -> 5d9d739f…
PASS: lit OBJ FAILs on injected build (rc=1)
PASS: source restored (md5 matches pre-injection)
PASS: lit OBJ green after restore+rebuild (rc=0)
PASS: source worktree clean after restore (git status empty)
-------------------------------------------------------------
SUMMARY: pass=25 fail=0
EXIT=0
```

独立验证退出码（非 tee）：`REAL_EXIT=0` ✓

**3. 独立注入**（审查者自行执行，非沿用 engineer 的注入 A/B）：

策略：改 `; OBJ:` 期望字节（`7f 08 00 01` → `7f 08 00 02`），不改 `@enc`，不需重建。

```
# 注入
$ sed -i 's/; OBJ: {{[0-9a-f]+:}} 7f 08 00 01/; OBJ: {{[0-9a-f]+:}} 7f 08 00 02/' tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s
$ md5sum tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s
714ab0021f9ea641a0a42e66b1daf9af  (changed from 19417824fb…)
$ git diff tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s
-; OBJ: {{[0-9a-f]+:}} 7f 08 00 01{{.*}}trap{{.*}}1
+; OBJ: {{[0-9a-f]+:}} 7f 08 00 02{{.*}}trap{{.*}}1

# oracle（应 PASS，因 @enc 未改；但 ; OBJ: 与独立派生不匹配 → 检测到 OBJ 错误）
$ python3 tests/llvm/lit/MC/DADAO/validate_cfx_vectors.py
FAIL tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s:26 [OBJ] 'trap cfx_smon, 1': ; OBJ: '7f080002'，独立派生 '7f080001'
向量 14 条，错误 1 条
EXIT=1

# lit OBJ（应 FAIL，因 FileCheck 检查 ; OBJ: 期望字节不匹配实际反汇编）
$ llvm-mc --triple=dadao-unknown-elf -filetype=obj ... | llvm-objdump -d ... | FileCheck ... --check-prefix=OBJ
LIT_OBJ_EXIT=1

# 还原（cp + md5）
$ cp /tmp/opencode/LLVM-060t-review/independent-inject/cfx2-trap-escape.s.orig tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s
$ md5sum tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s
19417824fb82bedf36908e133e974275  (matches original)

# 回绿
$ python3 tests/llvm/lit/MC/DADAO/validate_cfx_vectors.py
向量 14 条，错误 0 条
ORACLE_EXIT=0
$ ... | FileCheck ... --check-prefix=OBJ
LIT_OBJ_EXIT=0
```

注入有效（`git diff` 非空）、FAIL 路径可达、还原回绿 ✓

**4. 验收 1–10 逐条**：

| # | 验收项 | 结果 | 证据 |
|---|--------|------|------|
| 1 | `make build-mc` EXIT=0 | ✅ | evidence script inject B 重建两次均 EXIT=0 |
| 2 | 汇编正例 5 条 | ✅ | `trap cfx_smon,1`→`7f 08 00 01`；`trap cfx63,0`→`7f fc 00 00`；`escape cfx_umon,[excp_cause_ip,4]`→`7e 00 00 01`；`cfx2rd cfx_umon_excp_cause_ip,rd2`→`7a 00 50 c2`；`cfx2rc cfx_power_ctrl,rd2`→`7b fc 80 42`；均 rc=0 |
| 3 | `cfx_<name>`/`cfx<ha>` 等价 ≥2 对 | ✅ | `cfx_power≡cfx63`=`7f fc 00 00`；`cfx_umon≡cfx0`=`7f 00 00 00` |
| 4 | 简化 regname 等价 | ✅ | `cfx2rd cfx_umon_excp_cause_ip,rd2`≡`cfx2rd cfx_umon,cg5,rc3,rd2`=`7a 00 50 c2`；`cfx2rc cfx_power_ctrl,rd2`≡`cfx2rc cfx_power,cg8,rc1,rd2`=`7b fc 80 42` |
| 5 | `escape` 位宽 | ✅ | `…,8`→`7e 00 00 02`（imms18=2）；`…,6`→rc=1 `multiple of 4 bytes`；`…,524288`/`-524292`→rc=1 `out of range` |
| 6 | 反汇编/往返 | ✅ | `llvm-objdump -d` 还原 `trap cfx2, 1`；规范化→重汇编→`cmp` 对象文件一致 |
| 7 | 独立 oracle + 反例门控 | ✅ | oracle 14 向量 0 错 EXIT=0（不调 llvm-mc，从 opcodes.yaml + contract-cfx-aliases.md 派生）；注入 `@enc`→EXIT=1；注入 `; OBJ:`→EXIT=1；还原→EXIT=0 |
| 8 | 不回归 | ✅ | `make check` 62/62 EXIT=0；`check-patch-tree` 90 patches OK EXIT=0；`check-lit` 62/62 EXIT=0 |
| 9 | 一键证据脚本 | ✅ | `pass=25 fail=0 EXIT=0`（非交互、逐项打印、失败非零、结尾 `exit` 非 `tee`） |
| 10 | 无残留 | ✅ | `git status --porcelain -uall` 空；`git diff 6d61e66..HEAD` 仅声明范围 13 文件；无 `spec/`；`.work/**` 未入库；`check-source-state` clean=True |

**5. 补丁集与生成器**：

| 检查项 | 结果 |
|--------|------|
| `components/llvm-project/series` + 6 patch 文件 | ✅ 一文件一补丁，非空 blob |
| `check-patch-tree`（含断言⑥） | ✅ 90 patches OK EXIT=0 |
| `gen_cfx_alias_table.py` 已入库 | ✅ `tools/llvm/gen_cfx_alias_table.py` 存在 |
| 生成器可复现 | ✅ 重跑后 worktree clean；`cmp regen.patch DADAOCfxAlias.inc.patch` → byte-identical（md5 `56814bc235fe…`） |
| R2 patch 变更仅 provenance + blob index | ✅ `git diff 90b8b55..97580ae` 确认：`- // Generator: .work/…` → `+ // Generator: tools/llvm/gen_cfx_alias_table.py`；blob `157e2d6ec` → `392d53913`；表数据零变化 |
| `MC_ONLY_EXCLUDED_IDS` += 4 条 | ✅ `trap_ciii_cfx`, `escape_ciii_cfx`, `cfx2rc_crrr_cfx`, `cfx2rd_crrr_cfx` |
| `FMT_BY_CLASS` += crrr/ciii | ✅ `DADAOCrrr→crrr`, `DADAOCiii→ciii` |

**6. 未越界**：`git diff --name-only 6d61e66..HEAD` 共 13 文件，与任务书「修改文件」声明逐条一致；无 `spec/` 改动；`.work/**` 未入库（gitignored） ✓

**7. `.work/source/llvm-project` worktree clean**：`check-source-state` → `OK HEAD=0e9e52f7b count=1 clean=True` ✓

---

**判决：Accepted**

全部 10 条验收标准通过；证据脚本 25/25 全绿（含 engineer 两轮注入自检）；审查者独立注入（改 `; OBJ:` 期望字节）确认 FAIL 路径可达且还原回绿；补丁集合规、生成器可复现、未越界、worktree clean。

#### 第 1 轮 architect 重排落纸（2026-10-07，用户裁定 1）
本任务**前置**于 `SPEC-115t`（原为 `SPEC-115t` 之后）。

- **用户原话**：「**A 重排：先 LLVM-060t 再 SPEC-115t（推荐）**」（经主会话转达；子会话问答对父会话不可见，见 `lessons §7.3`）。
- **改动**：`依赖` 去掉 `SPEC-115t`（保留 `INFRA-047t`）；接口「输入」改为**现行** `contracts/opcodes.yaml`（编码已定义；re-scope 只改 `scope`/`decode`）；新增输出 5b（`crrr`/`ciii` 的 lit `; OBJ:` + `validate_instrinfo.py` 的 `MC_ONLY_EXCLUDED_IDS` += 4 条）；验收 10 无残留清单相应补入。
- **理由**：`SPEC-115t` re-scope 为 `m1` 后，`check-instrinfo` 需本任务的 `.td` def、`check-interface` 需本任务的 lit `; OBJ:` ⇒ 本任务必须先行。本任务阶段 4 条仍 `excluded`，其 `.td` def 与既有 `fence_oiii_imm` 同理（MC 层需要）⇒ 临时挂 `MC_ONLY_EXCLUDED_IDS`，由 `SPEC-115t` re-scope 时移除。

#### 第 1 轮 architect 修订（2026-10-07，规则缺口修复）
**修订对象**：允许文件集（验收 10 + 输出 + 约束）——增补别名表生成器 `tools/llvm/gen_cfx_alias_table.py`。

- **缺口**：engineer 把别名表生成器留在 `.work/LLVM-060t/gen_cfx_cpp_table.py`（见完成区「新发现/坑」第 4 条），因原验收 10 把 `tools/**` 允许范围限为 `validate_instrinfo.py`；而 `.work/` 被 `.gitignore` 整体忽略 ⇒ **生成器不入库**。
- **依据**：`AGENTS.md`「临时目录」条——**「凡产出被提交（入 git）的生成器或脚本，必须随产物一并保留在非易失位置——优先提交到 `tools/<module>/`……不得只放 `/tmp`。判据是产物是否入库，而不是『脚本是否只服务一个任务』；『一次性』只描述用途，不等于可丢弃」**。本例产物 `DADAOCfxAlias.inc.patch` 已入库 ⇒ 生成器须随产物入库。
- **改动**：① 输出新增 **6b**（生成器落 `tools/llvm/gen_cfx_alias_table.py`，由 engineer 从 `.work/LLVM-060t/gen_cfx_cpp_table.py` 迁入并使其**可复现生成**该 `.inc` patch 内容）；② 约束新增「生成器随产物入库」一条（明示该文件属允许文件集）；③ 验收 10 无残留清单补入 `tools/llvm/gen_cfx_alias_table.py`。
- **待办（engineer 补做）**：迁入生成器 → 以之复现 `DADAOCfxAlias.inc.patch` 内容（一致性核对）→ 更新完成区「修改文件」后重交 reviewer。
- **说明**：本次修订仅在既有内容之后**追加**，未改写完成区与既有审阅记录。

#### 第 1 轮 architect 提交（WIP）
- **档位**：**`WIP:`**（reviewer 尚未验收 ⇒ 非「正常提交」）。
- **文件集对账**（`git diff --cached --name-only` 逐条核对完成区「修改文件」声明；**显式 staging，未用 `git add -A`**）：
  - 组件补丁 5 改：`DADAO.h.patch` / `DADAOInstrFormats.td.patch` / `DADAOInstrInfo.td.patch` / `AsmParser/DADAOAsmParser.cpp.patch` / `MCTargetDesc/DADAOMCInstPrinter.cpp.patch` ✓
  - 组件补丁 1 新：`AsmParser/DADAOCfxAlias.inc.patch` ✓
  - `components/llvm-project/series` ✓
  - L1 向量 3 新：`tests/llvm/lit/MC/DADAO/{cfx2-trap-escape.s,cfx2-trap-escape-err.s,validate_cfx_vectors.py}` ✓
  - `tools/llvm/validate_instrinfo.py` ✓
  - 本任务书 ✓
  - **合计 12 文件**；无漏提、无多提、**无越界**（未卷入 `spec/`；`.work/**` 未入库——`.work/` 被 gitignore）。
- **待 engineer 补做的必要项（本次 WIP 未含）**：**别名表生成器「随产物入库」**——须将 `.work/LLVM-060t/gen_cfx_cpp_table.py` 迁入 `tools/llvm/gen_cfx_alias_table.py`（见本记录上一节「第 1 轮 architect 修订」及输出 6b），并使其可复现生成 `DADAOCfxAlias.inc.patch` 内容；engineer 迁入后更新完成区「修改文件」再交 reviewer。
- **说明**：commit **未 push**；无写死 SHA（收尾 push 前将本地 WIP 提交 squash/amend 为单一「已验证」提交）。

#### 第 2 轮 architect 提交（WIP）（2026-10-07）
- **档位**：**`WIP:`**（engineer 已补做「生成器随产物入库」，但 reviewer 尚未验收 ⇒ 非「正常提交」）。
- **文件集对账**（`git diff --cached --name-only` 逐条核对完成区「修改文件」声明；**显式 staging，未用 `git add -A`**）：
  - `tools/llvm/gen_cfx_alias_table.py`（**新增**，别名表生成器）✓
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOCfxAlias.inc.patch`（改）✓
  - 本任务书（完成区「第 2 轮」+ 自审）✓
  - **合计 3 文件**；无漏提、无多提、**无越界**（未卷入 `spec/`；`.work/**` 未入库——`.work/` 被 gitignore）。
- **patch 变更内容**：**仅 provenance 1 行**（`- // Generator: .work/…` → `+ // Generator: tools/llvm/gen_cfx_alias_table.py`）+ new-file blob index（`157e2d6ec` → `392d53913`，随内容更新，属必然）；**表数据/编码零变化**。
- **用户裁定**：原话见「第 2 轮（生成器随产物入库）」完成区——用户选定「更新为 `tools/llvm/gen_cfx_alias_table.py` 并重新导出 patch」。
- **说明**：commit **未 push**；无写死 SHA（收尾 push 前将本地 WIP 提交 squash/amend 为单一「已验证」提交）。

#### 第 2 轮 architect 提交（正常）（2026-10-07）

- **档位**：**正常提交**（reviewer 已判 **`Accepted`**，验收完成 ⇒ 非 `WIP:`）。
- **§2.5 交叉复核判决**：**复核通过（维持 `Accepted`）**，无补充缺陷。
  - **判决核验（不过严/不过松/无遗漏）**：reviewer 判 `Accepted` 与其证据一致；其**独立注入**（改 lit `; OBJ:` 期望 `7f 08 00 01 → 7f 08 00 02`，不改 `@enc`、不重建）**有鉴别力**——本任务 oracle `validate_cfx_vectors.py` **同时**校验 `@enc` 与 `; OBJ:`（`OBJ_RE` 抓取 + 独立派生比对，两条 FAIL 路径均可达），故注入后 oracle EXIT=1（`[OBJ] … 独立派生 7f080001`）且 lit `OBJ` FileCheck EXIT=1；`cp`+md5 还原回绿。
  - **补丁集合规（独立核，`Process-01`）**：`python3 tools/infra/check_patch_tree.py` → `check-patch-tree: 2 component(s), 90 patches OK` **EXIT=0**（含断言⑥）；`python3 tools/infra/check_index_blobs.py` → `73 new-file patch(es) OK; 17 modification patch(es) skipped` **EXIT=0**；`components/llvm-project/series` **58 行 == 58 patch 文件**；`AsmParser/DADAOCfxAlias.inc.patch` **非空 blob**（`index 000000000..392d53913`，154 行）。`check_patch_tree.py --source-state` → `llvm-project: OK HEAD=0e9e52f7baee count=1 clean=True`。
  - **生成器可复现（独立重跑，未采信他人输出）**：`python3 tools/llvm/gen_cfx_alias_table.py --out /tmp/opencode/LLVM-060t-cross/DADAOCfxAlias.inc` → `(13 scalar, 66 generic, 34 specific)` **EXIT=0**；与 worktree `.inc` `cmp` **EXIT=0**（md5 `0aa8a12770a970bc035558f92438184a`）；`git -C .work/source/llvm-project diff 6dfe1677ab8dffbc6ec13d53a1e0215d75147689 -- llvm/lib/Target/DADAO/AsmParser/DADAOCfxAlias.inc` 与已入库 patch `cmp` **EXIT=0**（md5 `56814bc235fe6f6462c71dc9b2d7371a`）。
  - **5b 门控前置**：lit `crrr`/`ciii` 的 `; OBJ:` 已覆盖（`tests/llvm/lit/MC/DADAO/cfx2-trap-escape.s`）；`tools/llvm/validate_instrinfo.py` 的 `MC_ONLY_EXCLUDED_IDS` **含 4 条**（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx` + 既有 `fence_oiii_imm`）；**「移除由 `SPEC-115t` 执行」的跨任务契约已写明**（`SPEC-115t` 任务书第 24/31/39/56 行：re-scope 后 `MC_ONLY_EXCLUDED_IDS` 移除 4 条、复用本任务 lit `; OBJ:`）。
  - **未越界**：`git diff --name-only 6d61e66..HEAD` = **13 文件**，与完成区「修改文件」声明逐条一致；**无 `spec/`**（`grep -c '^spec/'` = 0）。
- **文件集对账**（`git diff --cached --name-only` 逐条核对；**显式 staging，未用 `git add -A`**）：
  - 本任务书（第 1 轮 reviewer 验收记录 + 第 2 轮 architect 提交）✓
  - 知识沉淀 6 文件：`.tao/knowledge/changelog.md`（追加 1 行）/`milestones.md`（M5 段追加 1 条）/`MEMORY.md`（M5 摘要行补 `LLVM-060t`）/`lessons.md`（新增 `§7.7` 生成器随产物入库）/`issues.yaml`（新增 `ISS-162`：`DADAOAsmParser` 诊断枚举缺 `FIRST_TARGET_MATCH_RESULT_TY` 偏移）/`feedback_006-生成器随产物入库.md`（**新增**）✓
  - **合计 7 文件**；无漏提、无多提、**无越界**（未卷入 `spec/`；`.work/**` 未入库——`.work/` 被 `.gitignore`）。
  - **说明**：任务**交付物**（13 文件）已在前两次本地 `WIP:` 提交（`90b8b55`/`97580ae`）内；本次提交为**收尾提交**（任务书 + 知识沉淀）。
- **commit 信息**：`LLVM-060t trap/escape/cfx2rc/cfx2rd（MC+编码+5b 前置）（reviewer Accepted）`。
- **说明**：commit **未 push**；无写死 SHA（收尾 push 前由主会话把本地 WIP + 正常 + 台账 squash/amend 为单一「已验证」提交）。

#### 主会话统一验收报告（`/complete`，2026-10-07）

- **reviewer**：`Accepted`。证据脚本重跑 **25/25, EXIT=0**（含**重建**）；**独立注入**（改 `; OBJ:` 期望字节）⇒ **oracle 与 lit OBJ 双 FAIL** ⇒ `cp`+`md5` 还原（**含重建**）⇒ 回绿。
- **architect 交叉复核**：**维持 `Accepted`**。独立核：`check-patch-tree` **90 patches OK**（含断言⑥）、`check-index-blobs` OK、`--source-state` clean=True、`series` 58 行 == 58 patch；**生成器独立重跑 + `cmp` 逐字节一致**（worktree 与已入库 patch 双 0 退出）；`MC_ONLY_EXCLUDED_IDS` 含 4 条且「移除由 `SPEC-115t` 执行」契约已写明；`git diff --name-only 6d61e66..HEAD` = 13 文件、**`spec/` 0 条**。
- **交付**：`trap`/`escape`(ciii)、`cfx2rc`/`cfx2rd`(crrr) 的 `.td`+AsmParser+InstPrinter+Disassembler；`escape` `imms20`⇔`imms18` 与越界/非 4 倍数报错；`cfx_<name>`⇔`cfx<ha>` 等价；简化 regname 展开；**独立 oracle**（不调 `llvm-mc`）；**5b 前置**（lit `crrr/ciii` 的 `; OBJ:` + `MC_ONLY_EXCLUDED_IDS` +=4）为 `SPEC-115t` re-scope 铺路。
- **规则缺口已闭合**：别名表生成器从 `.work/`（gitignored）**迁入 `tools/llvm/gen_cfx_alias_table.py`**（随产物入库、可复现）；其 patch provenance 行按其取得的用户裁定更新（**内容仅 1 行注释**）。
- **新发现登记**：`ISS-162`（`DADAOAsmParser` 诊断枚举缺 `FIRST_TARGET_MATCH_RESULT_TY` 偏移）。
- **收尾检查**：`make check`/`check-patch-tree`/`check-lit`(62/62) EXIT=0；`git status --porcelain -uall` 干净；证据留 `.work/evidence/LLVM-060t/`、`.work/log/llvm/`；知识沉淀含 `lessons §7.7`、`feedback_006`、`ISS-162`。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
