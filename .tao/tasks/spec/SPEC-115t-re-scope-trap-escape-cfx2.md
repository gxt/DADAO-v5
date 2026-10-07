# SPEC-115t: re-scope——`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `excluded` → 已实现

**模块**：spec
**项目里程碑**：M5
**依赖**：`SPEC-114t`、`SPEC-113t`、`SPEC-119t`、**`LLVM-060t`**（2026-10-07 用户裁定 1 重排：`LLVM-060t` **前置**于本任务；见下）
**状态**：待开始

> **⚠️ 前置（硬约束，2026-10-07 用户裁定 1「A 重排」新增）**：本任务**依赖 `LLVM-060t`（先行）**。`scope: excluded → m1` 会把 4 条 cfx 加入 **M1 身份集**，而 M1 身份集被 **3 个跨模块门控**（`validate-vectors` 的 `inventory.md` M1 行集 / `check-interface` 的 M1 计数 + 每 M1 `format` 族 lit `; OBJ:` / `check-instrinfo` 的每 M1 唯一 `.td` def，均在 `make check` 内）强绑定；其中 `check-instrinfo` **必须**由 `LLVM-060t` 的 `.td` def 满足。故本任务**必须在 `LLVM-060t` 之后**执行，且落地文件集须含 `tests/vectors/inventory.md`（+4 行）与 `tools/llvm/validate_instrinfo.py`（从 `MC_ONLY_EXCLUDED_IDS` 移除 4 条——`LLVM-060t` 阶段临时加入），方能使 `make check` 一次转绿（engineer BLOCKED 证据摘要见 §审阅记录「第 2 轮 architect 重排落纸」）。

> **⚠️ 前置（硬约束，2026-10-07 用户裁定新增）**：本任务将修改**上游只读册** `spec/SimRISC-11-其它.md`。按新规则「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」（`spec/Process-06`；机制见 `SPEC-119t`）——**下发前必须取得用户明确允许，并将授权原话落盘；否则 BLOCKED**。落地时须**在同一变更内更新 `manifests/spec-readonly.lock.toml` 中 `spec/SimRISC-11-其它.md` 的 `sha256` 锁**并在完成区记录用户授权原话；未更新锁 ⇒ `make check-spec-readonly` **FAIL**（`make check` 红）。（`spec/SimRISC-12-待定.md` 仅**只读引用**、不改。）

## 执行环境
**执行环境**：本地

## 接口规范

- **定位**：`trap`/`escape`/`cfx2rc`/`cfx2rd` 4 条在 `contracts/opcodes.yaml` 中现为 `scope: excluded` + `decode: ILLI`（`ISS-110`）。M5 要把这 **4 条**从 `excluded` **re-scope 为已实现**（跨组件原子：`spec/SimRISC-11` + `contracts/*` + 投影 + 门控计数 + （后续）LLVM/QEMU）。**`SimRISC-12` 的 `cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*` 保持 deferred**（`INTEG-019k C13`）。
- **输入（自包含）**：
  - `spec/SimRISC-11-其它.md`：`ASSEMBLY_LIST`（`cfx2rc`/`cfx2rd`/`escape`/`swym`/`trap` 5 条；`escape` 汇编形式 `escape cfxHA, [excp_cause_ip, imms20]`）；`LEGALITY` 段（**当前**：`scope: excluded（decode ILLI）` 列 `cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`/`escape_ciii_cfx`/`trap_ciii_cfx`）；`指令行为说明`（L80：`trap/escape/cfx2rd/cfx2rc/cfxld/cfxst` 可在任意运行模式执行；L121：读写不存在的 `cfx_<cfxname>_cgHB_rcHC` 组合 ⇒ CFXREG）；§陷入指令/§退出指令/§寄存器传输指令。
  - `spec/SimRISC-12-待定.md`（**保持 deferred**：`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）。
  - `contracts/opcodes.yaml`（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`，现 `scope: excluded`/`decode: ILLI`）；`contracts/legality_rules.yaml`。
  - **生成器（2026-10-07 用户裁定 2）**：`tools/spec/generate_opcodes.py` —— `contracts/opcodes.yaml` **由本生成器产出**（git 历史中二者恒同改）；本任务**改生成器 + 重跑生成 yaml**（**不得**只手改 yaml 使生成器失同步）。
  - `tools/spec/check_scope.py`（**计数门控**：现 `EXPECTED_M1=151`/`EXPECTED_FP=60`/`EXPECTED_EXCLUDED=15`/`EXPECTED_M3=1`/`EXPECTED_TOTAL=227`；`excluded ⇔ decode ILLI`）。
  - **`LLVM-060t` 产出（前置，2026-10-07 用户裁定 1）**：`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOInstrInfo.td.patch`（4 条 cfx 的 `.td` def）+ `tests/llvm/lit/MC/DADAO/*.s`（`crrr`/`ciii` 的 lit `; OBJ:` 覆盖）+ `tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` 临时含 4 条）。
  - **门控载体**：`tests/vectors/inventory.md`（M1 行集须 == `opcodes.yaml` 的 `scope==m1` 集）、`tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS`）。
  - 投影：`.tao/knowledge/contract-isa.md`、`contract-asm.md`、`contract-asm-list.md`（生成投影）；`toolchain-01 §3.2`（**字段名映射**：汇编 `imms14/20/26` ⇔ 编码 `imms12/18/24`；`escape` 汇编层 `imms20`（字节，`%4==0`）⇔ 编码层 `imms18`（`field = bytes >> 2`），`Addr = excp_cause_ip + (imms18 << 2)`）。
- **输出**：
  1. **`spec/SimRISC-11` 的 `LEGALITY` 段 re-scope**：`trap`/`escape`/`cfx2rc`/`cfx2rd` 4 条由 `scope: excluded（decode ILLI）` **移出 excluded**（改为已实现口径——本任务落地时依 `<PSEUDO/LEGALITY 生成流程>` 与用户确认的标记方式；**保持 `SimRISC-12` 相关条目不动**）。
  2. **生成器改动 → 重跑生成 `contracts/opcodes.yaml`（2026-10-07 用户裁定 2）**：改 `tools/spec/generate_opcodes.py` 中 4 条 cfx 记录（`build_misc_amo` 的 `rec(...)`：`scope="excluded"`→`"m1"`；`rec()` 对 `scope=="excluded"` 附加的 `decode: ILLI` 随之消失），**重跑 `python3 tools/spec/generate_opcodes.py` 重新生成 `contracts/opcodes.yaml`**（改生成器与重跑**同改**，二者同一变更；再跑一次须 **byte-identical / 幂等**，可复核）。4 条 `legality`/`rule_refs` **保持 `[]`**（**用户裁定 3**：**不引 `encode_cfx`**——reserved cfxha→ILLI 属**实现/运行期**语义，非汇编/编码期 legality；见 §审阅记录「第 2 轮 architect 重排落纸」原话）。**计数**：`m1 151→155`、`excluded 15→11`、`total 227` 不变。`contracts/legality_rules.yaml` **本任务不改**（4 条不引规则；`encode_cfx` 的处置另立 `SPEC-120t`）。
  3. **`tools/spec/check_scope.py`**：更新 `EXPECTED_M1`/`EXPECTED_EXCLUDED`（151→155 / 15→11），保持 `excluded ⇔ decode ILLI`、`fp ⇔ _rf` 等结构性断言；`make check` 全绿。
  3b. **门控载体收口（2026-10-07 用户裁定 1 重排新增）**：① `tests/vectors/inventory.md` M1 行集 **+4 行**（`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`/`escape_ciii_cfx`/`trap_ciii_cfx`，各至少声明一类覆盖 / `deferred <reason>`），使 `validate-vectors` 的行集 == `opcodes.yaml` 的 `scope==m1` 集；② `tools/llvm/validate_instrinfo.py`：从 `MC_ONLY_EXCLUDED_IDS` **移除**这 4 条（`LLVM-060t` 阶段为「MC-only excluded」临时加入；本任务 re-scope 为 `m1` 后须移除，否则 `missing_mc_only` FAIL）；③ 复用 `LLVM-060t` 已落 `tests/llvm/lit/MC/DADAO/` 的 `crrr`/`ciii` `; OBJ:` 覆盖（**若缺失则本任务补齐**——见 §审阅记录归属裁定）。
  4. **投影刷新**：`contract-isa.md`/`contract-asm.md`/`contract-asm-list.md` 相应条目由「excluded/decode ILLI」更新为已实现；`escape` 位宽关系（汇编 `imms20` ⇔ 编码 `imms18`，`%4==0`）在 spec **写清**（`SimRISC-11 §退出指令` 或 `Toolchain-01 §3.2` 已述，本任务确保 spec 侧无歧义）。
  5. **`ISS-110` 部分收口**：任务完成区登记（`ISS-110` 的 crrr/crii/ciii + `cfx2rd`/`cfx2rc`/`escape`/`trap` 实现部分由 `SPEC-115t`+`LLVM-060t` 收口；`cfxld`/`cfxst`（`SimRISC-12`）与 `SPEC-075t` 的 uart2..30 别名缺口**另计**）。
- **约束（硬）**：
  - **只 re-scope 这 4 条**；`SimRISC-12`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）**保持 `excluded`/deferred**，**不得**顺手改。
  - **编码值不变**（`op`/`mask`/`value` 保持；只改 `scope`/`decode`）。
  - **改生成器 + 重跑（用户裁定 2）**：只改 `tools/spec/generate_opcodes.py` 后重跑，产出 `contracts/opcodes.yaml`；**禁**只手改 yaml（否则生成器失同步）。重跑须 **byte-identical / 幂等**。
  - **`legality`/`rule_refs` 保持 `[]`（用户裁定 3）**：**不引 `encode_cfx`**、**不改** `contracts/legality_rules.yaml`（`encode_cfx` 的处置另立 `SPEC-120t`）。
  - **门控载体同变更落地**：`tests/vectors/inventory.md`（+4 行）、`tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS` 移除 4 条）；lit `; OBJ:` 复用 `LLVM-060t` 产出，缺则补。
  - 本条**改 `scope` ⇒ 跨组件原子**：`contracts/opcodes.yaml` ↔ LLVM MC（`LLVM-060t`，**前置**）↔ QEMU（`QEMU-044t`/`045t`）计数须一致；`check-interface`/`check_scope`/`check_qemu_trans`/`check-instrinfo`/`validate-vectors` 须绿。
  - `spec/`/`contracts/`/`tests/`/`tools/` 为共享文件，与 `SPEC-116t` 及其它改 `spec/`/`contracts/`/`tests/` 的任务**串行**。
  - `make check` EXIT=0；失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-115t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **re-scope 落地**：`grep -n "scope" contracts/opcodes.yaml` 显示 4 条（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`）不再 `excluded`、无 `decode: ILLI`；`SimRISC-12` 条目仍 `excluded`；`spec/SimRISC-11` LEGALITY 段同步。给真实 `grep`/`sed` 输出。
2. **计数对齐**：`python3 tools/spec/check_scope.py` EXIT=0（`m1=155`/`excluded=11`/`total=227`）；给真实输出。
3. **编码不变**：4 条的 `op`/`mask`/`value` 与改前**逐字段相等**（`git diff contracts/opcodes.yaml` **仅** `scope`/`decode` 行变化；`legality`/`rule_refs` 保持 `[]`）；给真实 `git diff`。
4. **投影一致**：`contract-isa.md`/`contract-asm.md`/`contract-asm-list.md` 相应条目更新；`make check`（`check-asm-list*`/`check-legality-drift`/`check-interface`）EXIT=0。
5. **`escape` 位宽关系**：spec 侧写明「汇编 `imms20`（字节，`%4==0`）⇔ 编码 `imms18`（`>>2`），`Addr = excp_cause_ip + (imms18<<2)`」（`grep` 证据）。
6. **一键证据脚本**：`.work/evidence/SPEC-115t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（把某条改回 `excluded`/改一条 `op` 字节 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
7. **无残留**：`git status --untracked-files=all` 仅 `spec/SimRISC-11-其它.md` + `manifests/spec-readonly.lock.toml` + `contracts/opcodes.yaml` + `tools/spec/generate_opcodes.py` + `tools/spec/check_scope.py` + `tests/vectors/inventory.md` + `tools/llvm/validate_instrinfo.py`（+ 必要时 `tests/llvm/lit/MC/DADAO/**`）+ `.tao/knowledge/contract-*.md` + 本任务书。（**不含** `contracts/legality_rules.yaml`。）
8. **只读锁同步（前置的机械核验）**：改动 `spec/SimRISC-11-其它.md` 后须**重算并写入**该册的新 `sha256`（`sha256sum spec/SimRISC-11-其它.md` 的值与 lock 中该册 `sha256` **逐位相等**）；`make check-spec-readonly` **EXIT=0**（给真实输出，含退出码，**禁 `tee`**）；且**其余 19 册锁值不得变动**（`git diff manifests/spec-readonly.lock.toml` **仅** `spec/SimRISC-11-其它.md` 一段 `sha256` 变更——给真实 `git diff`）。
9. **生成器同改 + 重跑（用户裁定 2）**：`git diff` 同含 `tools/spec/generate_opcodes.py` 与 `contracts/opcodes.yaml`；重跑 `python3 tools/spec/generate_opcodes.py` **两次**输出 **byte-identical**（`md5sum` 相等、幂等），且产出与手工核对一致（给真实输出）。
10. **门控载体收口（用户裁定 1）**：`tests/vectors/inventory.md` 的 M1 行集（155）== `opcodes.yaml` 的 `scope==m1` 集（`validate-vectors` EXIT=0）；`tools/llvm/validate_instrinfo.py` 的 `MC_ONLY_EXCLUDED_IDS` **不再含** 4 条（`check-instrinfo` EXIT=0，baseline 155/155）；`crrr`/`ciii` 的 lit `; OBJ:` 覆盖存在（`check-interface` EXIT=0）（各给真实输出/退出码）。

## 完成区

> **🚫 BLOCKED：任务书不可达（未实施任何改动，工作树保持干净）。**
> `scope: excluded → m1` 会把 4 条 cfx 加入 **M1 身份集**，而 M1 身份集被 **3 个跨模块门控**（`validate-vectors`/`check-interface`/`check-instrinfo`，**均在 `make check` 内**）强绑定；其中至少 1 个（`check-instrinfo`）**必须**有 `LLVM-060t` 的 `.td` def 才能满足，而 `LLVM-060t`/`TESTCASES-033t` 在当前 Wave 顺序中**在 `SPEC-115t` 之后**（`INTEG-019k` Wave 2/4）。故本任务**无法作为独立任务使 `make check` 绿**；「验收 4（`check-interface` EXIT=0）/ 验收 7（allowlist）」与 Wave 顺序自相矛盾。
> 还原核对：`cp` 回 base，`md5sum contracts/opcodes.yaml` = `38e9d09c02bc6b0284f6ada76b7609f6`（= base）；`git status --porcelain -uall` **空**；`check-scope` 回绿 EXIT=0（日志 `.work/log/spec/SPEC-115t-restore-verify.log`）。

**测试结果**：未实施（见根因）。**可逆探针实验**——仅对 `contracts/opcodes.yaml` 的 4 条应用 re-scope（`cp` 备份 + md5），逐门控实跑：

| 门控 | 改动前 | 改动后 | 关键输出（日志：`.work/log/spec/`） |
|---|---|---|---|
| `validate_vectors.py` | EXIT=0 | **EXIT=1** | `INVENTORY MISSING: M1 id 'cfx2rc_crrr_cfx'/'cfx2rd_crrr_cfx'/'escape_ciii_cfx'/'trap_ciii_cfx' has no inventory.md row`（4 条）→ `SPEC-115t-probe_validate_vectors.log` |
| `check_interface_alignment.py` | EXIT=0 | **EXIT=1** | `opcodes.yaml M1=155，inventory.md M1=151（跨载体不一致）` + `M1 format 族缺少 lit 覆盖: ['ciii','crrr']` → `SPEC-115t-probe_check_interface.log` |
| `validate_instrinfo.py` | EXIT=0 | **EXIT=1** | `FAIL: baseline — 151/155 条 M1 记录匹配到 .td def` + `FAIL: format — 格式类集合不一致`（5 errors）→ `SPEC-115t-probe-check-instrinfo.log` |
| `check_scope.py` | EXIT=0 | EXIT=1（预期：任务书需改 `EXPECTED_*`） | `SPEC-115t-probe-check-scope.log` |
| `check_legality_drift.py` | EXIT=0 | EXIT=1（预期：需重跑 `gen_legality_list.py`） | `FAIL: 其它 (SimRISC-11-其它.md): LEGALITY content drift` → `SPEC-115t-probe-check-legality-drift.log` |
| `check_asm_list_drift.py` | EXIT=0 | EXIT=1（预期：需重跑 `gen_asm_list.py`） | `MISMATCH`（M1 155/excluded 11 vs 151/15）→ `SPEC-115t-probe-check-asm-list-drift.log` |
| `check_rule_refs.py` | EXIT=0 | EXIT=0 | —— |
| `validate_encoding.py` | EXIT=0 | EXIT=0 | —— |
| `check_qemu_trans.py --strict` | EXIT=0 | —（未变；`227/227`） | `SPEC-115t-base_check_qemu_trans.log` |

**修改文件**：**无**（工作树干净）。仅新增证据日志 `.work/log/spec/SPEC-115t-*.log`（`.work/` 为 gitignore，不入库）。

**验收结果**：**未通过（任务书不可达）**，逐条：
1. **未做（阻塞）**。
2. 可行（改 `check_scope.py` 计数 → EXIT=0）但未做（整任务阻塞，工作树须保持可重启）。
3. 可行但未做。
4. ❌ **不可达**：`check-interface` 必然 EXIT=1（inventory 计数 + `crrr`/`ciii` 无 lit 覆盖）。
5. 可行（`spec/SimRISC-11` L104 已含位宽关系，`grep` 可证）但未做。
6. 未做。
7. ❌ **不可达**：修复需改 `tests/vectors/inventory.md` + `tests/llvm/lit/MC/DADAO/*`（**均在允许文件集外**）。
8. 不可达：lock 同步可行，但整体受 4 阻塞。

**根因**：`m1` 是**跨模块强绑定身份集**——
- `tools/testcases/validate_vectors.py:728`：`inventory.md` 的 M1 行集 **必须等于** `opcodes.yaml` 的 `scope==m1` 集（多/少即 FAIL）。
- `tools/integ/check_interface_alignment.py:666`：`inventory.md` M1 计数 == `opcodes` M1 计数；`:740/:766`：`scope==m1` 记录的**每个 `format` 族**须有 lit `; OBJ:` 覆盖 —— `crrr`/`ciii` 无（`tests/llvm/lit/MC/DADAO/*.s` 的 `; OBJ:` 首字节实测无 `0x7A`–`0x7F`）。
- `tools/llvm/validate_instrinfo.py:229/237/292`：每条 `scope==m1` 记录须有**唯一 `.td` def**（4 条 cfx 的 def 属 `LLVM-060t` 未做），且 `.td` 的 M1 def 格式集 == M1 记录格式集。
⇒ 该 re-scope 是**跨组件原子**（任务书自述），但当前分解把 `LLVM-060t`（`.td`/MC）与 `TESTCASES-033t`（inventory/lit/向量）放在其后 ⇒ `SPEC-115t` 单独下发**必然红**。这是**下发前预检项 2（依赖链实际可用性）/项 3（验收可执行性）**未覆盖的缺口。

**建议（供 architect/主会话裁定，三选一）**：
- **A（推荐）**：把 `SPEC-115t` 的 `contracts/*`+`spec` 改动与 `LLVM-060t`（`.td`/MC）+ `TESTCASES-033t`（`inventory.md`/lit/向量）的**门控相关部分合并为一次跨组件原子变更**，`make check` 一次性转绿——顺序改为「LLVM/QEMU 先就绪（或 `.td`+lit 骨架先行）→ spec re-scope 收口」。
- **B**：为 re-scope 引入**新 scope**（如 `m5`/`see`，非 M1 身份，类比 `m3`：`m1` 保持 151、新 scope 4、`excluded` 15→11），`check_scope.py` 增该 scope 断言；**避免**触碰 inventory/lit/`.td` 门控。代价：与任务书/`SPEC-118m` 的「`m1 155`」口径冲突，**须用户裁定**。
- **C**：保留 `m1` 目标，但**放宽本任务验收**为「`check_scope`/`check-legality-drift`/`check-asm-list*`/`check-spec-readonly` 绿；`validate-vectors`/`check-interface`/`check-instrinfo` **预期红**（由 `LLVM-060t`/`TESTCASES-033t` 收口）」，同时把 `tests/vectors/inventory.md`（+4 行 `deferred` 覆盖）与 lit 骨架加入 allowlist。

**另一需裁定项（`legality`/`rule_refs` 口径）**：任务书「填 `legality`/`rule_refs`（据 spec）」有两种读法（请裁定）：
- **(i) 保持 `[]`**（倾向）：spec 对这 4 条无**静态编码**合法性约束——`reserved cfxha → ILLI` 属**运行期** mask/权限语义（`contract-see.md:35`、`ADR-0020 D11`、`spec/DADAO-12 §5`）；故 `legality: []`/`rule_refs: []`，`SimRISC-11` LEGALITY 生成区渲染为「（本章无适用规则）」。改动最小（**不触** `gen_legality_list.py`）。
- **(ii) 引用 `encode_cfx`**（`contracts/legality_rules.yaml:198`，reserved cfxha→ILLI）：需 `encode_cfx` `deferred→active` + 为 4 条填 `legality` 表达式；但 `tools/spec/gen_legality_list.py` 的 `RULE_SUMMARY['encode_cfx']` 硬编码含「（deferred）」也须同步（**允许文件集外**）。

**新发现/坑**：
1. `contracts/opcodes.yaml` 由 **`tools/spec/generate_opcodes.py` 生成**（实测重跑 byte-identical）；无 drift 门控，但 git 历史中两者**恒同改**。直接改 yaml 会使生成器失同步，而 `generate_opcodes.py` **不在允许文件集**。→ 建议明确「改生成器 + 重跑」（与历史一致），并把它加入 allowlist。
2. `spec/SimRISC-01..12` 的 `LEGALITY` 段与 `.tao/knowledge/contract-asm-list.md` 均为**生成物**（`gen_legality_list.py` / `gen_asm_list.py`），分别由 `check-legality-drift`（精确比对）/`check-asm-list-drift`（字节比对）把守；改 `contracts/*` 后须重跑对应生成器。
3. **M1 身份集三绑定**（`validate-vectors`/`check-interface`/`check-instrinfo`）在 spec 层 re-scope 任务书中未被识别为前置——凡把指令从 `excluded` 移入 `m1` 的任务都须同时处理 `inventory.md`、lit `; OBJ:`、`.td` def。
4. `manifests/spec-readonly.lock.toml` 需同步 `spec/SimRISC-11-其它.md` 的 `sha256`（可行，`SPEC-119t` 机制）——本任务未实施故未改。

**遗留问题（未做，待重规划）**：
1. 整任务 BLOCKED；`contracts/opcodes.yaml`/`legality_rules.yaml`、`tools/spec/check_scope.py`、`spec/SimRISC-11-其它.md`、`manifests/spec-readonly.lock.toml`、投影 `contract-{isa,asm,asm-list}.md` **均未改动**。
2. `ISS-110` 部分收口登记 **未做**。
3. `.work/evidence/SPEC-115t/run.sh`（一键证据脚本）**未产**——本任务验收命令（`make check`）无法转绿，无「可跑通」的证据基线；待重规划后随新边界一并补。
4. 等待 architect 依「建议 A/B/C」重定边界（含 `legality`/`rule_refs` 口径 (i)/(ii)）后**重新下发**。

## 审阅记录

#### 第 1 轮 engineer 自审
**结论：BLOCKED（无代码改动，故无 finding 处置表）。** 在改动任何文件前，逐条核对任务书的**跨模块前置**，发现 `scope: excluded → m1` 会触发 3 个跨模块门控（`validate-vectors`/`check-interface`/`check-instrinfo`）失败，且其中 `check-instrinfo` 需 `LLVM-060t` 的 `.td` def 才可满足 ⇒ 本任务在给定文件集/Wave 顺序下**不可达**。

**取证方法**（可复现、可还原、无残留）：
1. `cp contracts/opcodes.yaml /tmp/opencode/SPEC-115t/backup/opcodes.yaml.base` + `md5sum`（base `38e9d09c02bc6b0284f6ada76b7609f6`）。
2. 脚本对 4 条记录改 `scope: m1` + 删 `decode: ILLI`（**探针**，非交付）。
3. 逐门控实跑并落日志 `.work/log/spec/SPEC-115t-probe-*.log`（记录 `EXIT=`）。
4. `cp` 回 base → md5 一致 + `git status --porcelain -uall` 空 + `check-scope` 回绿（`SPEC-115t-restore-verify.log`）。
5. **未使用** `git checkout/restore/stash`。

**finding（未处置，交主会话/architect）**：
| # | finding | 处置 | 证据 |
|---|---|---|---|
| F1 | `m1` 绑定 `inventory.md` 行集（`validate_vectors.py:728`）⇒ 需改 `tests/vectors/inventory.md`（allowlist 外） | ⏸延后（需裁定 A/B/C） | `SPEC-115t-probe_validate_vectors.log` EXIT=1（4×`INVENTORY MISSING`） |
| F2 | `m1` 绑定 `format` 族 lit 覆盖（`check_interface_alignment.py:740`）⇒ `crrr`/`ciii` 无 lit `.s`，需 `LLVM-060t` | ⏸延后 | `SPEC-115t-probe_check_interface.log` EXIT=1 |
| F3 | `m1` 绑定 `.td` def（`validate_instrinfo.py:229/292`）⇒ 需 `LLVM-060t` | ⏸延后 | `SPEC-115t-probe-check-instrinfo.log` EXIT=1（`151/155`） |
| F4 | `contracts/opcodes.yaml` 为生成物（`generate_opcodes.py`，allowlist 外）——改 yaml vs 改生成器口径未定 | ⏸延后 | 实测生成器重跑 byte-identical |
| F5 | 「填 `legality`/`rule_refs`」两解（保持 `[]` vs 引用 `encode_cfx`），后者牵出 `gen_legality_list.py`（allowlist 外） | ⏸延后（需裁定 (i)/(ii)） | `contracts/legality_rules.yaml:198`、`gen_legality_list.py:79` |

**判决**：无 finding 已修 ⇒ **不置 `待验收`**，保持 `**状态**：待开始`，返回主会话。

#### 第 1 轮 reviewer 验收
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**〔改 scope/改编码字节〕+ 逐条核计数/编码不变/SimRISC-12 未动 + 判决）

#### 下发前预检修订（architect，2026-10-07）
**F1（真冲突，已改）**：任务书顶部「⚠️ 前置」要求本任务修改上游只读册 `spec/SimRISC-11-其它.md` 时**须在同一变更内更新 `manifests/spec-readonly.lock.toml` 中该册的 `sha256` 锁**（否则 `make check-spec-readonly` FAIL ⇒ `make check` 红）；但原「验收标准 7」的 `git status --untracked-files=all` 允许清单**未含**该锁文件 ⇒ 工程师要么不更新锁（违反前置），要么更新锁就违反验收 7，二者不可兼得。
**改法**：①「验收标准 7」清单**加入** `manifests/spec-readonly.lock.toml`；②新增「验收标准 8」明确 **改后须重算并写入 `spec/SimRISC-11-其它.md` 的新 `sha256`**、`make check-spec-readonly` **EXIT=0**（给真实输出），并断言**其余 19 册锁值不得变动**。

**用户授权原话（本任务改上游只读册的授权，落盘于此）**：
> 「允许（re-scope SimRISC-11）」

**授权范围**：`spec/SimRISC-11-其它.md` 的 **4 条 re-scope**（`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `excluded` → 已实现）+ **同步更新该册锁值**（`manifests/spec-readonly.lock.toml` 中 `spec/SimRISC-11-其它.md` 一段 `sha256`）。`spec/SimRISC-12-待定.md` 仅只读引用、不改。

#### 第 2 轮 architect 重排落纸（2026-10-07，用户裁定 1/2/3）

**背景（engineer BLOCKED，未实施、工作树零改动）**：本任务单发时 `scope: excluded → m1` 会撞 **3 个跨模块门控**（均在 `make check` 内），基线全绿（`make check`/`check_qemu_trans --strict` 均 EXIT=0）。实测证据（`.work/log/spec/SPEC-115t-probe-*.log`；`cp` 备份 + md5，还原后 `md5sum contracts/opcodes.yaml` = `38e9d09c02bc6b0284f6ada76b7609f6`（= base）、`git status --porcelain -uall` 空、`check-scope` 回绿 EXIT=0）：

| 门控 | 改动前 | 改动后（探针） | 关键输出 |
|---|---|---|---|
| `validate_vectors.py` | EXIT=0 | **EXIT=1** | `INVENTORY MISSING: M1 id 'cfx2rc_crrr_cfx'/'cfx2rd_crrr_cfx'/'escape_ciii_cfx'/'trap_ciii_cfx' has no inventory.md row`（4 条） |
| `check_interface_alignment.py` | EXIT=0 | **EXIT=1** | `opcodes.yaml M1=155，inventory.md M1=151` + `M1 format 族缺少 lit 覆盖: ['ciii','crrr']` |
| `validate_instrinfo.py` | EXIT=0 | **EXIT=1** | `FAIL: baseline — 151/155 条 M1 记录匹配到 .td def` + `FAIL: format — 格式类集合不一致`（5 errors） |

⇒ 该 re-scope 是**跨组件原子**，但原分解把 `LLVM-060t`（`.td`/MC）与 `TESTCASES-033t`（inventory/lit/向量）置于其后 ⇒ 本任务单发**必红**。这是**下发前预检第 2 项（依赖链实际可用性）**未覆盖的缺口（教训登记见 `lessons.md §7.6`）。

**用户裁定（原话，2026-10-07，经主会话转达——子会话问答对父会话不可见，见 `lessons §7.3`）**：

> 1. **「A 重排：先 LLVM-060t 再 SPEC-115t（推荐）」**
> 2. **「改生成器并重跑（推荐）」**
> 3. **「encode_cfx不应该存在，这个是实现层面的事情，不是汇编或者编码时需要处理的问题，单独建立一个任务解决该问题」**

**本轮落纸（依裁定）**：

1. **重排（裁定 1）**：`LLVM-060t` **前置**于本任务；本任务 `依赖 += LLVM-060t`（见文件头）。`LLVM-060t` 自身不再依赖本任务（见 `LLVM-060t` 任务书 + `INTEG-019k` 任务表/Wave/反向依赖同步）。
2. **改生成器（裁定 2）**：`contracts/opcodes.yaml` 由 `tools/spec/generate_opcodes.py` 生成（git 历史中二者恒同改，如 `4b865c4`/`0dcaf1f`/`a32cca8`）⇒ 本任务**改生成器 + 重跑**，**禁止**只手改 yaml；`tools/spec/generate_opcodes.py` 加入允许文件集（见接口/验收 9）。
3. **`legality`/`rule_refs` 口径（裁定 3）**：本任务 **保持 `[]`**（**不引 `encode_cfx`**）——`encode_cfx`（reserved cfxha→ILLI）属**实现/运行期**语义，非汇编/编码期 legality。`encode_cfx` 的处置**另立 `SPEC-120t`**（见其任务书）。
4. **门控载体收口（裁定 1 的下游）**：见「接口规范」输出 3b + 验收 7/10。**归属裁定（architect 判断，理由如下，列为待用户复核项）**：
   - **`tests/vectors/inventory.md`（+4 行）→ 并入本任务（SPEC-115t）**。理由：`validate_vectors.py` 要求 inventory.md 的 M1 行集 **==** `opcodes.yaml` 的 `scope==m1` 集；**行集只能在 re-scope 生效的同一变更内同步增加**（提前加 4 行则 inventory M1=155 ≠ opcodes M1=151 ⇒ FAIL）⇒ **原子性强制**，无第二种分工。另 `TESTCASES-033t` 依赖本任务（消费 re-scope 后的 contracts）⇒ 无法前置承接（否则成环）。
   - **lit `; OBJ:`（`crrr`/`ciii`）→ 由前置的 `LLVM-060t` 承接**。理由：lit MC 向量是 LLVM 模块的天然产出（`LLVM-060t` 输出本含 `tests/llvm/lit/MC/DADAO/` 的 L1 MC 向量），且在本任务之前就绪；本任务**复用**、仅在其缺失时补齐（兜底列于允许文件集 `tests/llvm/lit/MC/DADAO/**`）。
   - **`tools/llvm/validate_instrinfo.py`（`MC_ONLY_EXCLUDED_IDS`）→ 两任务先后各改一次**：`LLVM-060t` 阶段 4 条仍 `scope: excluded` 且 MC 层需 `.td` def（与既有 `fence_oiii_imm` 同理）⇒ `LLVM-060t` **加入** 4 条；本任务 re-scope 为 `m1` 后须**移除**（否则 `missing_mc_only` FAIL）⇒ 本任务**移除**。

**判决**：本任务边界已按裁定 1/2/3 重定；待 `LLVM-060t` 完成后重新下发。
