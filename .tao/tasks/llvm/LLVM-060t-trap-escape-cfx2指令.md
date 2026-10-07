# LLVM-060t: `trap`/`escape`/`cfx2rc`/`cfx2rd`（MC parser/printer/disassembler/编码 + 必要 CodeGen）

**模块**：llvm
**项目里程碑**：M5
**依赖**：`INFRA-047t`（2026-10-07 用户裁定 1 重排：**去掉 `SPEC-115t`**——本任务**前置**于 `SPEC-115t`；编码 `op`/`mask`/`value` 在 `SPEC-115t` 前后不变，re-scope 只改 `scope`/`decode`）
**状态**：待开始

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
- **约束（硬）**：
  - **补丁导出纪律（`spec/Process-01`）**：改动**只能**在 `.work/source/llvm-project` 工作树；`commit --amend` 收敛 base+1 → `make_patch.py` 导出（裸 `git diff`）；**不手改补丁**；`make check-patch-tree`（含**断言⑥**应用产物一致性）通过；补丁写 `/tmp` 不确定时按 `Process-01`。
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
10. **无残留**：`git status --untracked-files=all` 仅组件补丁（`components/llvm-project/**`）+ L1 向量（`tests/llvm/lit/MC/DADAO/**`，含 `crrr`/`ciii` 的 `; OBJ:`）+ `tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` += 4 条）+ 本任务书；`.work/source/llvm-project` worktree clean（`check-source-state`）。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**（改 `DADAO*.td`/AsmParser → 重建 → FAIL → 还原+重建 → 回绿）+ 补丁树核验 + 判决）

#### 第 1 轮 architect 重排落纸（2026-10-07，用户裁定 1）
本任务**前置**于 `SPEC-115t`（原为 `SPEC-115t` 之后）。

- **用户原话**：「**A 重排：先 LLVM-060t 再 SPEC-115t（推荐）**」（经主会话转达；子会话问答对父会话不可见，见 `lessons §7.3`）。
- **改动**：`依赖` 去掉 `SPEC-115t`（保留 `INFRA-047t`）；接口「输入」改为**现行** `contracts/opcodes.yaml`（编码已定义；re-scope 只改 `scope`/`decode`）；新增输出 5b（`crrr`/`ciii` 的 lit `; OBJ:` + `validate_instrinfo.py` 的 `MC_ONLY_EXCLUDED_IDS` += 4 条）；验收 10 无残留清单相应补入。
- **理由**：`SPEC-115t` re-scope 为 `m1` 后，`check-instrinfo` 需本任务的 `.td` def、`check-interface` 需本任务的 lit `; OBJ:` ⇒ 本任务必须先行。本任务阶段 4 条仍 `excluded`，其 `.td` def 与既有 `fence_oiii_imm` 同理（MC 层需要）⇒ 临时挂 `MC_ONLY_EXCLUDED_IDS`，由 `SPEC-115t` re-scope 时移除。
