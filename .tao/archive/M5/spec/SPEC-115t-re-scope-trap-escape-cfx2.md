# SPEC-115t: re-scope——`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `excluded` → 已实现

**模块**：spec
**项目里程碑**：M5
**依赖**：`SPEC-114t`、`SPEC-113t`、`SPEC-119t`、**`LLVM-060t`**（2026-10-07 用户裁定 1 重排：`LLVM-060t` **前置**于本任务；见下）
**状态**：已验证

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

> **（重排后第 2 次实现，2026-10-08；前置 `LLVM-060t`〔`ebb9ef2`，已验证/push〕就绪）** 本任务此前 BLOCKED 的根因分析与可逆探针证据见 §审阅记录「第 1 轮 engineer 自审」与「第 2 轮 architect 重排落纸」；本轮按用户裁定 1/2/3 落地，下述内容取代旧 BLOCKED 完成区。

**测试结果**：通过 10/10（验收 1–10 全部可跑且绿；`make check` EXIT=0）。失败原因：无。

**修改文件**（与 `git status --porcelain -uall` 逐一致；共 10 个）：

| 文件 | 改动 |
|---|---|
| `contracts/opcodes.yaml` | 生成物重跑（4 条 `scope: excluded→m1`、去 `decode: ILLI`）；md5 `965feb70769880c7c846fdb797e546b2` |
| `tools/spec/generate_opcodes.py` | 4 条 `rec(...)` `scope="excluded"→"m1"`；docstring 计数 151→155 / 15→11 |
| `tools/spec/check_scope.py` | `EXPECTED_M1 151→155`、`EXPECTED_EXCLUDED 15→11` |
| `tests/vectors/inventory.md` | 标题 `151→155`；末尾 +4 行（`deferred TESTCASES-033t`） |
| `tools/llvm/validate_instrinfo.py` | `MC_ONLY_EXCLUDED_IDS` 移除 4 条（保留 `fence_oiii_imm`） |
| `spec/SimRISC-11-其它.md` | LEGALITY 段（`gen_legality_list.py --apply` 重生成） |
| `manifests/spec-readonly.lock.toml` | `spec/SimRISC-11-其它.md` 的 `sha256` 更新 |
| `.tao/knowledge/contract-isa.md` | 投影：新增 §13.6；§2.3/§2.7/§13/§13.2/§14/§14.3/§15/§15.1/A.1/A.7 同步 |
| `.tao/knowledge/contract-asm.md` | 投影：§1/§5/§11/§13 的 excluded 表述同步 |
| `.tao/knowledge/contract-asm-list.md` | `gen_asm_list.py` 重生成（仅 header 计数 151→155 / 15→11） |

（**未改**：`contracts/legality_rules.yaml`、`spec/SimRISC-12-待定.md`、其它上游册、`tests/llvm/lit/MC/DADAO/**`〔复用 `LLVM-060t` 产出〕、`components/**`。）

**验收结果**（真实输出；完整日志 `.work/log/spec/SPEC-115t-*.log`）：

**验收 1（re-scope 落地）** — `python3` 直读 `contracts/opcodes.yaml`：
```
cfx2rd_crrr_cfx    op=0x7A mask=0xFF000000 value=0x7A000000 scope=m1       decode=<none> legality=[] rule_refs=[]
cfx2rc_crrr_cfx    op=0x7B mask=0xFF000000 value=0x7B000000 scope=m1       decode=<none> legality=[] rule_refs=[]
cfxld_crii_cfx     op=0x7C mask=0xFF000000 value=0x7C000000 scope=excluded decode=ILLI   legality=[] rule_refs=[]
cfxst_crii_cfx     op=0x7D mask=0xFF000000 value=0x7D000000 scope=excluded decode=ILLI   legality=[] rule_refs=[]
escape_ciii_cfx    op=0x7E mask=0xFF000000 value=0x7E000000 scope=m1       decode=<none> legality=[] rule_refs=[]
trap_ciii_cfx      op=0x7F mask=0xFF000000 value=0x7F000000 scope=m1       decode=<none> legality=[] rule_refs=[]
```
`spec/SimRISC-11-其它.md` LEGALITY 段重生成后为「（本章无适用规则）」（`sed -n '20,27p'`）：
```
<!-- LEGALITY_START -->
## 合法性检查

（本章无适用规则）
<!-- LEGALITY_END -->
```

**验收 2（计数对齐）** — `python3 tools/spec/check_scope.py` **EXIT=0**：
```
[PASS] m1 计数: 期望=155 实际=155
[PASS] fp 计数: 期望=60 实际=60
[PASS] excluded 计数: 期望=11 实际=11
[PASS] m3 计数: 期望=1 实际=1
[PASS] total 计数: 期望=227 实际=227
[PASS] scope==excluded ⇒ decode=ILLI: 期望=0 条 实际=0 条
[PASS] scope∈{m1,fp,m3} ⇒ 无 decode/旧字段: 期望=0 条 实际=0 条
[PASS] scope:fp ⇔ id 以 _rf 结尾: 期望=0 条 实际=0 条
[PASS] 旧字段在非历史文件中消失: 期望=0 个文件 实际=0 个文件
check-scope: PASS
```

**验收 3（编码不变）** — `git diff contracts/opcodes.yaml`（`1 file changed, 5 insertions(+), 9 deletions(-)`）：仅 header 计数行 + 4 条 `scope/decode` 行变化，`op/mask/value` 零变化，`legality`/`rule_refs` 保持 `[]`：
```
-# 共 227 条：M1 151 条 + scope fp 60 条 + scope excluded 15 条 + scope m3 1 条
+# 共 227 条：M1 155 条 + scope fp 60 条 + scope excluded 11 条 + scope m3 1 条
@@ （4 条各）
-  scope: excluded
-  decode: ILLI
+  scope: m1
```

**验收 4（投影一致）** — 均 **EXIT=0**：
```
check-asm-list-consistency: 12 spec files OK
check-asm-list-drift: PASS (byte-identical)
check-legality-drift: PASS
check-interface: 总计 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
```

**验收 5（`escape` 位宽关系）** — `grep -n "imms18 << 2" spec/SimRISC-11-其它.md`：
```
99:其中，cfx_<cfxname> 指定核芯功能扩展名称；imms20 指定目标地址偏移（字节，须 `%4==0`；实际地址 = excp_cause_ip + imms20；编码层 `Addr = excp_cause_ip + (imms18 << 2)`）。
```
（另 `contract-isa.md §13.6` 写明 `imms18 = imms20 >> 2`。）

**验收 6（一键证据脚本）** — `.work/evidence/SPEC-115t/run.sh` → `EVIDENCE EXIT=0`，**ALL CHECKS PASS**；含 3 类注入自检（全文见 `.work/log/spec/SPEC-115t-evidence.log`）：
```
I1 trap->excluded        => check_scope FAIL (EXIT=1) [expected] → 还原 md5 一致 → 回绿
I2 trap value 字节改错    => 编码不变性断言 FAIL [expected]        → 还原 md5 一致 → 回绿
I3 lock sha256 改错       => check_spec_readonly FAIL (EXIT=1) [expected] → 还原 md5 一致 → 回绿
```

**验收 7（无残留）** — `git status --porcelain -uall` 仅上述 10 个文件；脚本检查 7「no unexpected changes」**PASS**。

**验收 8（只读锁同步）** — `sha256sum spec/SimRISC-11-其它.md` = `12da1f319c828cc87201cd9e95642965770fea4665420d911939ca364746b552` == lock 值；`python3 tools/infra/check_spec_readonly.py` **EXIT=0**（`20 upstream read-only spec volume(s) OK`）；`git diff manifests/spec-readonly.lock.toml` 仅 `spec/SimRISC-11-其它.md` 一段 `sha256` 变更（其余 19 册零变动，脚本断言 `only one lock sha256 changed: expected=2 actual=2`）。

**验收 9（生成器同改 + 重跑幂等）** — `git diff --name-only` 同含 `tools/spec/generate_opcodes.py` + `contracts/opcodes.yaml`；重跑两次 `md5sum contracts/opcodes.yaml` 均 = `965feb70769880c7c846fdb797e546b2`（== 提交物，byte-identical）。

**验收 10（门控载体收口）**：
```
validate-vectors: 155/155 M1 identities covered OK (inventory sync OK; 15 data files, 693 cases; data coverage gaps: 0)
check-instrinfo: PASS: baseline — 155/155 条 M1 记录各有唯一 .td def; PASS: format — [... 'ciii','crrr',...]
check-interface : LLVM lit format 族覆盖 PASS 11/11 族有 lit 覆盖（ciii(5), crrr(4), ...）
```

**`make check`** — **EXIT=0**：
```
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
Total Discovered Tests: 62
  Passed: 62 (100.00%)
repository checks: PASS
```

**新发现/坑**：
1. `contract-isa.md §2.3` 与 `contract-asm.md §1` 的「**9 种 M1 格式类**」源自 `spec/Toolchain-01 §1`（上游只读册，**本任务授权范围外，未改**）。re-scope 后 `m1` 实含 `crrr`/`ciii`（共 11 类），故两处**叙述与 `opcodes.yaml` 的 `scope` 口径出现偏差**——已在两文件加注说明，但 `Toolchain-01 §1` 仍写「`crrr`/`crii`/`ciii` 属 `scope: excluded`」。**建议**：后续经用户授权后同步 `Toolchain-01 §1`（并更新其 sha256 锁）。
2. `tools/spec/check_qfc_coverage.py`（**不在 `make check`**）为信息型工具，其「M1 外条目」按 QFC 类别（含「特权 cfx=6」）分类；re-scope 后报「QFC 与 yaml 的 M1 外集合不一致：仅 QFC 4，仅 yaml 15」——**exit 0（informational）**，不影响门控，但其 M1-外分类口径需后续与 `scope` 对齐。
3. 4 条 re-scope 指令的 **M1 向量**（`tests/vectors/isa/*.yaml`）尚未生成（属 `TESTCASES-033t`）；`inventory.md` 相应 4 行以 `deferred` 声明，故 `validate_vectors` 的 data-coverage 门控不触发（`deferred` 不计缺口）。
4. `gen_legality_list.py --apply` 在 `SimRISC-11` 的 excluded 列表清空后渲染为「（本章无适用规则）」，与 `check-legality-drift`（精确比对）一致；**未**触碰其它 11 册（逐册报 `unchanged (idempotent)`）。

**遗留问题**：
1. 4 条 cfx 的 **M1 语义向量 + exec 覆盖**：待 `TESTCASES-033t`（inventory 已 `deferred` 声明）。
2. **QEMU 执行层**：`QEMU-044t`/`045t` 尚未实现这 4 条的运行语义（当前 `trans_*` 为占位；`check_qemu_trans --strict` 227/227 仍绿）。
3. `Toolchain-01 §1`「9 种 M1 格式类 / `crrr`/`ciii` excluded」与现行 `scope` 偏差（见「新发现」1）——**需用户授权**方可改上游册。
4. `check_qfc_coverage.py` 的 M1-外分类口径未同步（`make check` 外，informational）。
5. `ISS-110` 部分收口登记：crrr/crii/ciii + `cfx2rd`/`cfx2rc`/`escape`/`trap` 实现部分由 `SPEC-115t`+`LLVM-060t` 收口；`cfxld`/`cfxst`（SimRISC-12）与 `SPEC-075t` uart2..30 别名缺口另计（本任务书登记）。


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

#### 第 2 轮 engineer 自审（2026-10-08，重排后实现）

**结论：实现完成，所有 finding 已修/无未决项 ⇒ 置 `待验收`。** `LLVM-060t`（`ebb9ef2`）就绪后按裁定 1/2/3 执行；`make check` EXIT=0，一键证据脚本 `EVIDENCE EXIT=0`。

**自审范围（逐行核对改动）**：

| # | 审查点 | 结论 |
|---|---|---|
| R1 | `generate_opcodes.py` 仅 4 条 `rec(...)` 的 `scope` 由 `"excluded"`→`"m1"`；`cfxld`/`cfxst` 保持 `"excluded"`；`op/mask/value/fields/legality` 未动 | ✅ 见 `git diff`；生成 `md5` 幂等 |
| R2 | `check_scope.py` 仅计数常量 `151→155`/`15→11`；`excluded ⇔ ILLI`、`fp ⇔ _rf`、旧字段断言结构未改 | ✅ 结构断言保留，EXIT=0 |
| R3 | `validate_instrinfo.py` 仅从 `MC_ONLY_EXCLUDED_IDS` 移除本任务 4 条；`fence_oiii_imm` 保留；`FMT_BY_CLASS` 的 crrr/ciii 映射保留 | ✅ baseline 155/155、non-m1 仅 2 条 |
| R4 | `inventory.md` 4 行用 `deferred`（非 `✓`），正确规避 data-coverage 门控（无数据即不得声明 ✓） | ✅ `data coverage gaps: 0` |
| R5 | `spec/SimRISC-11` 仅 LEGALITY 段变化（生成物），未手改正文；锁同步 | ✅ `git diff` 单段；`check-spec-readonly` EXIT=0 |
| R6 | `contract-isa.md`/`contract-asm.md` 为叙述投影，仅更新 excluded→已实现相关表述与计数，无凭空编码/错误引用（`ADR-0020 D11` 已核实原文） | ✅ |
| R7 | 越界检查：未改 `Toolchain-01`/`SimRISC-12`/`legality_rules.yaml`/`components/**`/`tests/llvm/lit/**` | ✅ 脚本检查 7 PASS |
| R8 | 还原纪律：证据脚本 3 处注入均 `cp`+`md5` 对账还原（未用 `git checkout/restore/stash`） | ✅ I1/I2/I3 还原 md5 一致 |
| R9 | 防造假：`make check`/各门控 rc 均**真实捕获**（`cmd > log; rc=$?`，无 `tee`） | ✅ 日志留 `.work/log/spec/` |

**finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 无 | — | — | — |

#### 第 1 轮 architect 提交（WIP）

**档位**：**WIP**（reviewer 尚未验收，engineer 已置 `待验收` 未判 Accepted）⇒ 前缀 `WIP:` 提交。

**文件集对账**（`git diff --cached --name-only` vs 完成区「修改文件」声明 + 任务范围）：
- 完成区声明 10 个文件（`contracts/opcodes.yaml`、`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tests/vectors/inventory.md`、`tools/llvm/validate_instrinfo.py`、`spec/SimRISC-11-其它.md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/contract-{isa,asm,asm-list}.md`）+ 本任务书 = **11**；
- `git diff --cached --name-only` 实测 **11 个**，逐项一致；**漏提：无 / 多提：无 / 越界：无**。

**`spec/` 授权范围核对**（`git diff --cached --name-only -- spec/`）：
```
"spec/SimRISC-11-\345\205\266\345\256\203.md"
```
仅 `spec/SimRISC-11-其它.md`；**未出现** `SimRISC-12`、`DADAO-*`、`Toolchain-01`、`Process-*` ⇒ 在授权范围内。

**提交**：`WIP:` 前缀（reviewer 验收完成前不 push）。|

#### 第 1 轮 reviewer 验收（2026-10-08）

**判决：Needs Revision**（证据脚本 2 个 FAIL 属脚本 bug，实际产出全部达标；需 engineer 修脚本后重跑）。

##### 1. 证据脚本审核（`.work/evidence/SPEC-115t/run.sh`）

**逐条核对可达 FAIL 路径**：
- `assert_scope_state()`：4 条 re-scoped 要求 `scope=m1` 且无 `decode`；3 条 excluded 要求 `scope=excluded`+`decode=ILLI`；LR-SC 要求 `excluded`。**非恒真**——注入 I1 改 scope 时确实 FAIL。
- `assert_encoding()`：逐条比对 `op/mask/value` 硬编码期望值。**非恒真**——注入 I2 改 value 时确实 FAIL。
- `assert_legality_empty()`：4 条要求 `legality=[]`+`rule_refs=[]`。**非恒真**（若改 legality 即 FAIL）。
- `assert_inventory()`：计数==155 + 4 条 ID 存在。**非恒真**。
- `assert_instrinfo_ids()`：`fence_oiii_imm` 存在 + 4 条已移除。**非恒真**。
- 注入 I1/I2/I3：均 `cp`+`md5` 对账还原，**未用 `git checkout/restore/stash`**；注入后 md5 确实变化；还原后 md5 确实回绿。✅
- 结尾 `rc=$?`（line 241/245/273/277），**未用 `tee`**。✅

**2 个脚本 bug**（脚本设计假设"工作树未提交"，但 architect 已 WIP 提交）：
1. **line 21** `[FAIL] 8 only one lock sha256 changed: expected=2 actual=0` —— `git diff -- manifests/spec-readonly.lock.toml` 对已提交的变更返回空（`git diff` 比较 HEAD 内容 vs 工作树）。应改为 `git diff ebb9ef2..HEAD -- manifests/spec-readonly.lock.toml`。
2. **line 24** `[FAIL] 9 generator modified` —— `git diff --name-only` 无输出（生成器已在 WIP 提交中）。应改为 `git diff ebb9ef2..HEAD --name-only | grep -qx "tools/spec/generate_opcodes.py"`。

**脚本其余33项 PASS**（含 I1/I2/I3 注入自检全绿）。

##### 2. 重跑证据脚本（真实输出）

```
=== SPEC-115t evidence (repo=/mnt/tao/DADAO-v5) ===
re-scope state OK
[PASS] 1 re-scope state
[PASS] 2 check-scope (EXIT=0)
[PASS] 2 m1=155
[PASS] 2 excluded=11
[PASS] 2 total=227
encoding invariant OK
[PASS] 3 encoding invariant
legality/rule_refs [] OK
[PASS] 3 legality/rule_refs []
[PASS] 4 check-asm-list (EXIT=0)
[PASS] 4 check-asm-list-drift (EXIT=0)
[PASS] 4 check-legality-drift (EXIT=0)
[PASS] 4 check-interface (EXIT=0)
[PASS] 5 escape width relation in SimRISC-11
[PASS] 5 escape width relation in contract-isa
[PASS] 7 no unexpected changes
[PASS] 8 lock sha256 == file sha256: expected=12da1f... actual=12da1f...
[PASS] 8 check-spec-readonly (EXIT=0)
[FAIL] 8 only one lock sha256 changed: expected=2 actual=0    ← 脚本 bug
[PASS] 9 generator run rc: expected=0 actual=0
[PASS] 9 generator idempotent (committed==run1==run2): expected=965feb... actual=965feb...
[FAIL] 9 generator modified                                    ← 脚本 bug
inventory M1 rows=155 OK
[PASS] 10 inventory M1 rows
MC_ONLY_EXCLUDED_IDS OK (only fence)
[PASS] 10 MC_ONLY_EXCLUDED_IDS
[PASS] 10 validate-vectors (EXIT=0)
[PASS] 10 check-instrinfo (EXIT=0)
[PASS] 10 lit crrr coverage present
[PASS] 10 lit ciii coverage present
=== injection self-tests ===
[PASS] I1 injection changed file (md5 differs)
[PASS] I1 trap->excluded => check_scope FAIL (EXIT=1) [expected]
[PASS] I1 restored (md5 match)
[PASS] I1 after restore => check_scope green
[PASS] I2 injection changed file (md5 differs)
[PASS] I2 value-corrupt => encoding check FAIL [expected]
[PASS] I2 restored (md5 match)
[PASS] I2 after restore => encoding check green
[PASS] I3 injection changed file (md5 differs)
[PASS] I3 lock sha corrupt => check_spec_readonly FAIL (EXIT=1) [expected]
[PASS] I3 restored (md5 match)
[PASS] I3 after restore => check_spec_readonly green
=== summary: failures=2 ===
EVIDENCE FAILED (2)
EXIT=1
```

##### 3. 独立注入测试（reviewer 自行执行）

**注入**：`cp contracts/opcodes.yaml /tmp/opencode/SPEC-115t-review/opcodes.preinject`（md5=`965feb70769880c7c846fdb797e546b2`）→ Python 改 `cfx2rc_crrr_cfx` scope `m1`→`excluded` + 加 `decode: ILLI`。

**注入后**：
- md5 = `12473451dfc592615e06f3eebe624175`（≠ preinject，注入非空）✅
- `check_scope.py` EXIT=1：`m1=154 ≠ 155, excluded=12 ≠ 11` ✅
- `git diff --name-only` = `contracts/opcodes.yaml`（注入有效性确认）✅

**还原**：`cp /tmp/opencode/SPEC-115t-review/opcodes.preinject contracts/opcodes.yaml`

**还原后**：
- md5 = `965feb70769880c7c846fdb797e546b2`（== preinject，还原成功）✅
- `check_scope.py` EXIT=0：`m1=155, excluded=11, total=227` ✅
- `git status --porcelain -uall` = 空（工作区干净）✅

##### 4. 验收 1–10 逐条独立核验

| # | 验收项 | 独立结果 | 证据 |
|---|--------|---------|------|
| 1 | re-scope 落地 | ✅ PASS | Python 直读：4 条 `scope=m1`/无 `decode`；`cfxld`/`cfxst` 仍 `excluded`/`ILLI`；SimRISC-11 LEGALITY 段「（本章无适用规则）」 |
| 2 | 计数对齐 | ✅ PASS | `check_scope.py` EXIT=0：`m1=155 / excluded=11 / total=227` |
| 3 | 编码不变 | ✅ PASS | `git diff ebb9ef2..HEAD -- contracts/opcodes.yaml`：仅 header 计数行 + 4 条 `scope/decode` 行变；`op/mask/value` 零变化；`legality/rule_refs=[]` |
| 4 | 投影一致 | ✅ PASS | `make check` EXIT=0（含 `check-asm-list`/`check-legality-drift`/`check-interface` 80/80 PASS） |
| 5 | escape 位宽关系 | ✅ PASS | `spec/SimRISC-11` line 99：`imms20 指定目标地址偏移（字节，须 %4==0；编码层 Addr = excp_cause_ip + (imms18 << 2))`；`contract-isa.md` line 1123 同 |
| 6 | 一键证据脚本 | ⚠️ 脚本 EXIT=1 | 33/35 PASS + 2 FAIL（脚本 bug：检测已提交变更的逻辑错误）；注入自检 I1/I2/I3 全绿 |
| 7 | 无残留 | ✅ PASS | `git diff --name-only ebb9ef2..HEAD` = 11 文件，与声明一致；`git status --porcelain -uall` 空 |
| 8 | 只读锁同步 | ✅ PASS | `sha256sum spec/SimRISC-11-其它.md` = `12da1f...` == lock 值；`check_spec_readonly.py` EXIT=0（20 册 OK）；lock diff 仅 SimRISC-11 一段 sha256 变更 |
| 9 | 生成器同改+幂等 | ✅ PASS | `git diff ebb9ef2..HEAD --name-only` 含 `generate_opcodes.py`+`opcodes.yaml`；重跑两次 md5=`965feb...` 相同 |
| 10 | 门控载体收口 | ✅ PASS | `validate-vectors` 155/155 EXIT=0；`check-instrinfo` 155/155 PASS；lit `cfx2-trap-escape.s` PASS（含 `crrr`/`ciii`） |

##### 5. `spec/` 授权范围

`git diff --name-only ebb9ef2..HEAD -- spec/`：
```
"spec/SimRISC-11-\345\205\266\345\256\203.md"
```
**仅** `spec/SimRISC-11-其它.md`；**无** `SimRISC-12`、`DADAO-*`、`Toolchain-01`、`Process-*`。✅ 授权范围内。

##### 6. 未越界

`git diff --name-only ebb9ef2..HEAD` = 11 文件，与完成区声明一致：
```
.tao/knowledge/contract-asm-list.md
.tao/knowledge/contract-asm.md
.tao/knowledge/contract-isa.md
.tao/tasks/spec/SPEC-115t-re-scope-trap-escape-cfx2.md
contracts/opcodes.yaml
manifests/spec-readonly.lock.toml
spec/SimRISC-11-其它.md
tests/vectors/inventory.md
tools/llvm/validate_instrinfo.py
tools/spec/check_scope.py
tools/spec/generate_opcodes.py
```
✅ 11 文件，无多提/漏提/越界。

##### 7. Toolchain-01 §1 偏差确认

`git diff --name-only ebb9ef2..HEAD -- spec/Toolchain-01*` 无输出 —— **该册确实未被改动**。该册 line 15 仍写「9 种 M1 格式——rrrr rrri rrii riii iiii rwii orrr orri oiii（crrr/crii/ciii 属特权 cfx，scope: excluded）」，与 re-scope 后 `m1` 实含 `crrr`/`ciii`（共 11 类）的事实**不一致**。`contract-asm.md` line 18 已加注「SPEC-115t re-scope 后 m1 另含 crrr/ciii」作缓冲。此偏差属**授权范围外**，须另请用户授权后同步 `Toolchain-01 §1`（并更新其 sha256 锁）。**如实记录，不阻塞本次验收。**

##### 最小必改清单（Needs Revision）

**仅需修复证据脚本** `.work/evidence/SPEC-115t/run.sh` 中 2 处：

1. **line 193**：`git diff -- manifests/spec-readonly.lock.toml` → `git diff ebb9ef2..HEAD -- manifests/spec-readonly.lock.toml`
2. **line 205**：`git diff --name-only | grep -qx "tools/spec/generate_opcodes.py"` → `git diff ebb9ef2..HEAD --name-only | grep -qx "tools/spec/generate_opcodes.py"`

（或更通用：令脚本接受 `BASE_COMMIT` 环境变量，默认 `HEAD~1` 或由调用者传入。）

实际产出（代码/契约/锁/门控）全部达标，`make check` EXIT=0，注入自检全绿。**仅脚本需修。**

#### 第 2 轮 engineer 自审（证据脚本修复，2026-10-08）〔完成区补记〕

**触发**：第 1 轮 reviewer 验收判 **Needs Revision**——唯一必改项 = 证据脚本 `.work/evidence/SPEC-115t/run.sh` 中 2 处「检测已提交变更却用裸 `git diff`」的假 FAIL；交付物（代码/契约/锁/门控）全部达标。本轮**只改证据脚本 + 本任务书**，未触碰任何交付物。

**同类排查（修一类）**：`grep -nE 'git (diff|status|log|show)' .work/evidence/SPEC-115t/run.sh` 全脚本仅 3 处 git 调用：

| 位置 | 原写法 | 判定 | 处置 |
|---|---|---|---|
| 检查 7 | `git status --porcelain -uall`（工作树残留） | 合法：residue 检测**必须**查工作树，且不依赖变更是否已提交（提交后仍能发现游离文件） | **保留**，并**另加**一条基于 `$BASE_COMMIT..HEAD` 的越界检查（见下），使「提交后」该检查不再空转 |
| 检查 8 | `git diff -- manifests/spec-readonly.lock.toml` | **bug**（复审点名） | ✅ 改 `git diff "$BASE_COMMIT"..HEAD -- …` |
| 检查 9 | `git diff --name-only` | **bug**（复审点名） | ✅ 改 `git diff "$BASE_COMMIT"..HEAD --name-only` |

**改动**（`.work/evidence/SPEC-115t/run.sh`；`git` 断言全部带提交范围）：

1. 新增 `BASE_COMMIT="${BASE_COMMIT:-ebb9ef2}"`（默认 = 前置 `LLVM-060t` 提交；可用环境变量覆盖以验证 FAIL 路径），并加注释说明「产物已提交后裸 `git diff` 会假 FAIL」。
2. 检查 8：`git diff "$BASE_COMMIT"..HEAD -- manifests/spec-readonly.lock.toml`。
3. 检查 9：`git diff "$BASE_COMMIT"..HEAD --name-only | grep -qx "tools/spec/generate_opcodes.py"`。
4. 检查 7 **追加**（原有工作树残留检查保留、改名 `7 no unexpected worktree changes`）：
   ```
   out_of_scope="$(git diff "$BASE_COMMIT"..HEAD --name-only | sed 's/^"//;s/"$//' | grep -vE "$allowed_re" || true)"
   if [ -z "$out_of_scope" ]; then pass "7 committed changes in scope ($BASE_COMMIT..HEAD)"; else fail "7 out-of-scope committed changes: $out_of_scope"; fi
   ```
   （`sed 's/^"//;s/"$//'` 剥离 `core.quotePath` 对中文路径的引号/转义，复用同一 `allowed_re`。）

**重跑真实输出与退出码**（`bash .work/evidence/SPEC-115t/run.sh`；日志 `.work/log/spec/SPEC-115t-evidence-r2.log`；`cmd > log 2>&1; rc=$?`，**未用 `tee`**）：

```
=== SPEC-115t evidence (repo=/mnt/tao/DADAO-v5) ===
re-scope state OK
[PASS] 1 re-scope state
[PASS] 2 check-scope (EXIT=0)
[PASS] 2 m1=155
[PASS] 2 excluded=11
[PASS] 2 total=227
encoding invariant OK
[PASS] 3 encoding invariant
legality/rule_refs [] OK
[PASS] 3 legality/rule_refs []
[PASS] 4 check-asm-list (EXIT=0)
[PASS] 4 check-asm-list-drift (EXIT=0)
[PASS] 4 check-legality-drift (EXIT=0)
[PASS] 4 check-interface (EXIT=0)
[PASS] 5 escape width relation in SimRISC-11
[PASS] 5 escape width relation in contract-isa
[PASS] 7 no unexpected worktree changes
[PASS] 7 committed changes in scope (ebb9ef2..HEAD)
[PASS] 8 lock sha256 == file sha256: expected=12da1f319c828cc87201cd9e95642965770fea4665420d911939ca364746b552 actual=12da1f319c828cc87201cd9e95642965770fea4665420d911939ca364746b552
[PASS] 8 check-spec-readonly (EXIT=0)
[PASS] 8 only one lock sha256 changed: expected=2 actual=2
[PASS] 9 generator run rc: expected=0 actual=0
[PASS] 9 generator idempotent (committed==run1==run2): expected=965feb70769880c7c846fdb797e546b2 actual=965feb70769880c7c846fdb797e546b2
[PASS] 9 generator modified
inventory M1 rows=155 OK
[PASS] 10 inventory M1 rows
MC_ONLY_EXCLUDED_IDS OK (only fence)
[PASS] 10 MC_ONLY_EXCLUDED_IDS
[PASS] 10 validate-vectors (EXIT=0)
[PASS] 10 check-instrinfo (EXIT=0)
[PASS] 10 lit crrr coverage present
[PASS] 10 lit ciii coverage present
=== injection self-tests ===
[PASS] I1 injection changed file (md5 differs)
[PASS] I1 trap->excluded => check_scope FAIL (EXIT=1) [expected]
[PASS] I1 restored (md5 match)
[PASS] I1 after restore => check_scope green
[PASS] I2 injection changed file (md5 differs)
[PASS] I2 value-corrupt => encoding check FAIL [expected]
[PASS] I2 restored (md5 match)
[PASS] I2 after restore => encoding check green
[PASS] I3 injection changed file (md5 differs)
[PASS] I3 lock sha corrupt => check_spec_readonly FAIL (EXIT=1) [expected]
[PASS] I3 restored (md5 match)
[PASS] I3 after restore => check_spec_readonly green
=== summary: failures=0 ===
ALL CHECKS PASS
```
**退出码 `EXIT=0`**（原轮为 `EXIT=1 / failures=2`）。I1/I2/I3 注入自检仍全部有效（注入→FAIL→`cp`+md5 还原→回绿）。

**保持可失败性（新增/修改断言的可达 FAIL 路径，真实命令）**：

1. `BASE_COMMIT=HEAD bash run.sh`（空范围）⇒ 退出码 `EXIT=1`，两条修复断言如期 FAIL（证明非恒真）：
   ```
   [FAIL] 8 only one lock sha256 changed: expected=2 actual=0
   [FAIL] 9 generator modified
   ```
   （日志 `.work/log/spec/SPEC-115t-evidence-r2-basefail.log`；其余仍 PASS，注入段仍绿。）
2. 检查 7 新范围断言：以 `BASE_COMMIT=9fa4b14`（范围含 `ebb9ef2` 越界提交）重放脚本同款管道，`out_of_scope` 非空 ⇒ 该断言会 FAIL（示例越界项 `components/llvm-project/patches/…`、`tests/llvm/lit/MC/DADAO/…`、`tools/llvm/gen_cfx_alias_table.py`），证明可失败。

**还原/无残留核对**（运行后）：`md5sum contracts/opcodes.yaml` = `965feb70769880c7c846fdb797e546b2`（== 提交物）；`md5sum manifests/spec-readonly.lock.toml` = `796d3d22e5182858e34ba5178a720e05`；`git status --porcelain -uall` 仅 ` M .tao/tasks/spec/SPEC-115t-re-scope-trap-escape-cfx2.md`（`run.sh` 为 gitignore）。全程**未用** `git checkout/restore/stash`。

**finding 处置表**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（reviewer）`git diff --` 检测锁变更假 FAIL | ✅已修 | 检查 8 改 `git diff "$BASE_COMMIT"..HEAD -- …` | 重跑 `[PASS] 8 only one lock sha256 changed: expected=2 actual=2`；`BASE_COMMIT=HEAD` 时 FAIL |
| R2（reviewer）`git diff --name-only` 检测生成器改动假 FAIL | ✅已修 | 检查 9 改 `git diff "$BASE_COMMIT"..HEAD --name-only` | 重跑 `[PASS] 9 generator modified`；`BASE_COMMIT=HEAD` 时 FAIL |
| R3（同类排查）检查 7 在提交后空转 | ✅已修 | 保留工作树残留检查 + 追加 `$BASE_COMMIT..HEAD` 越界检查 | 重跑 `[PASS] 7 committed changes in scope (ebb9ef2..HEAD)`；越界 BASE 演示可 FAIL |

**完成区处置补记（本轮「遗留问题」）**：第 1 轮 reviewer 的 2 项必改 + 1 项同类隐患**全部 ✅已修**，无未决项。第 1 轮完成区「遗留问题」1–5（`TESTCASES-033t` 向量、`QEMU-044t/045t` 执行层、`Toolchain-01 §1` 授权偏差、`check_qfc_coverage` 口径、`ISS-110` 收口登记）**均系交付物/后续任务项，不在本轮修复范围，保持不变**。

**修改文件（本轮）**：`.work/evidence/SPEC-115t/run.sh`（gitignore）、`.tao/tasks/spec/SPEC-115t-re-scope-trap-escape-cfx2.md`（本任务书）。**未改任何交付物。**

**判决**：finding 全部已修 ⇒ 状态回 `**状态**：待验收`，返回主会话。

#### 第 2 轮 reviewer 验收（2026-10-08，复审返工）

**判决：Accepted**

##### 1. 核修复：全脚本 `git` 调用排查

`grep -nE '\bgit\s+(diff|status|log|show)\b' .work/evidence/SPEC-115t/run.sh` 真实输出：

```
20:# 工作树 diff 为空，用裸 `git diff` 会假 FAIL）。BASE_COMMIT 可用环境变量
185:bad="$(git status --porcelain -uall | awk '{print $2}' | sed 's/^"//;s/"$//' | grep -vE "$allowed_re" || true)"
188:out_of_scope="$(git diff "$BASE_COMMIT"..HEAD --name-only | sed 's/^"//;s/"$//' | grep -vE "$allowed_re" || true)"
201:lock_changes="$(git diff "$BASE_COMMIT"..HEAD -- manifests/spec-readonly.lock.toml | grep -c '^[+-]sha256' || true)"
213:git diff "$BASE_COMMIT"..HEAD --name-only | grep -qx "tools/spec/generate_opcodes.py" \
```

逐处判定：
| 位置 | 调用 | 判定 |
|---|---|---|
| L20 | 注释（非代码） | N/A |
| L185 | `git status --porcelain -uall` | ✅ 合理——检测**工作树残留**，必须查工作树 |
| L188 | `git diff "$BASE_COMMIT"..HEAD --name-only` | ✅ 已修复——检测已提交变更，带范围 |
| L201 | `git diff "$BASE_COMMIT"..HEAD -- manifests/…` | ✅ 已修复——检测已提交变更，带范围 |
| L213 | `git diff "$BASE_COMMIT"..HEAD --name-only` | ✅ 已修复——检测已提交变更，带范围 |

3 处检测**已提交变更**的 `git diff` 全部带 `ebb9ef2..HEAD` 范围；1 处 `git status` 检测**工作树残留**，合理保留。**修复彻底，「修一类」已落实**——L185 保留 + 新增 L188 越界检查，使提交后脚本不再空转。

##### 2. 重跑脚本（真实输出与退出码）

```bash
bash .work/evidence/SPEC-115t/run.sh
```

```
=== SPEC-115t evidence (repo=/mnt/tao/DADAO-v5) ===
re-scope state OK
[PASS] 1 re-scope state
[PASS] 2 check-scope (EXIT=0)
[PASS] 2 m1=155
[PASS] 2 excluded=11
[PASS] 2 total=227
encoding invariant OK
[PASS] 3 encoding invariant
legality/rule_refs [] OK
[PASS] 3 legality/rule_refs []
[PASS] 4 check-asm-list (EXIT=0)
[PASS] 4 check-asm-list-drift (EXIT=0)
[PASS] 4 check-legality-drift (EXIT=0)
[PASS] 4 check-interface (EXIT=0)
[PASS] 5 escape width relation in SimRISC-11
[PASS] 5 escape width relation in contract-isa
[PASS] 7 no unexpected worktree changes
[PASS] 7 committed changes in scope (ebb9ef2..HEAD)
[PASS] 8 lock sha256 == file sha256: expected=12da1f319c828cc87201cd9e95642965770fea4665420d911939ca364746b552 actual=12da1f319c828cc87201cd9e95642965770fea4665420d911939ca364746b552
[PASS] 8 check-spec-readonly (EXIT=0)
[PASS] 8 only one lock sha256 changed: expected=2 actual=2
[PASS] 9 generator run rc: expected=0 actual=0
[PASS] 9 generator idempotent (committed==run1==run2): expected=965feb70769880c7c846fdb797e546b2 actual=965feb70769880c7c846fdb797e546b2
[PASS] 9 generator modified
inventory M1 rows=155 OK
[PASS] 10 inventory M1 rows
MC_ONLY_EXCLUDED_IDS OK (only fence)
[PASS] 10 MC_ONLY_EXCLUDED_IDS
[PASS] 10 validate-vectors (EXIT=0)
[PASS] 10 check-instrinfo (EXIT=0)
[PASS] 10 lit crrr coverage present
[PASS] 10 lit ciii coverage present
=== injection self-tests ===
[PASS] I1 injection changed file (md5 differs)
[PASS] I1 trap->excluded => check_scope FAIL (EXIT=1) [expected]
[PASS] I1 restored (md5 match)
[PASS] I1 after restore => check_scope green
[PASS] I2 injection changed file (md5 differs)
[PASS] I2 value-corrupt => encoding check FAIL [expected]
[PASS] I2 restored (md5 match)
[PASS] I2 after restore => encoding check green
[PASS] I3 injection changed file (md5 differs)
[PASS] I3 lock sha corrupt => check_spec_readonly FAIL (EXIT=1) [expected]
[PASS] I3 restored (md5 match)
[PASS] I3 after restore => check_spec_readonly green
=== summary: failures=0 ===
ALL CHECKS PASS
```

**EXIT=0**，35/35 PASS，0 failures。✅

##### 3. 独立注入与还原证据

**3a. 非恒真验证（`BASE_COMMIT=HEAD`）**：

```bash
BASE_COMMIT=HEAD bash .work/evidence/SPEC-115t/run.sh
```

```
[FAIL] 8 only one lock sha256 changed: expected=2 actual=0
[FAIL] 9 generator modified
=== summary: failures=2 ===
EVIDENCE FAILED (2)
```

**EXIT=1**，精确 2 条 FAIL（检查 8 + 检查 9），与 engineer 声称一致。空范围 ⇒ 无 diff ⇒ 断言如期 FAIL。✅

**3b. reviewer 独立注入反例**（改 `contracts/opcodes.yaml` 一条 `scope`）：

- **注入前**：`cp contracts/opcodes.yaml /tmp/opencode/SPEC-115t-review2/opcodes.preinject`
- **注入前 md5**：`965feb70769880c7c846fdb797e546b2`
- **注入**：Python 改 `cfx2rd_crrr_cfx` scope `m1→excluded` + 加 `decode: ILLI`
- **注入后 md5**：`6f4f9a911475b8478aa4236e62995bfb`（≠ preinject，注入非空）✅
- **注入后 `check_scope.py`**：EXIT=1，`m1=154≠155, excluded=12≠11` ✅
- **还原**：`cp /tmp/opencode/SPEC-115t-review2/opcodes.preinject contracts/opcodes.yaml`
- **还原后 md5**：`965feb70769880c7c846fdb797e546b2`（== preinject）✅
- **还原后 `check_scope.py`**：EXIT=0，`m1=155, excluded=11, total=227` ✅
- **还原后 `git status --porcelain -uall`**：仅 `M .tao/tasks/spec/SPEC-115t-…`（任务书）✅
- **全程未用 `git checkout/restore/stash`** ✅

##### 4. 交付物未被本轮改动确认

| 核验项 | 结果 |
|---|---|
| `git status --porcelain -uall` | 仅任务书 `M .tao/tasks/spec/SPEC-115t-…` |
| `md5sum contracts/opcodes.yaml` | `965feb70769880c7c846fdb797e546b2` ✅ |
| `git diff ebb9ef2..HEAD --name-only` | 11 文件（与上轮一致） |
| `spec/` 仅 `SimRISC-11-其它.md` | ✅ |
| `make check` | 本轮未改任何交付物（仅改 gitignored 脚本 + 任务书），`opcodes.yaml` md5 不变，**采信上轮记录**（上轮 EXIT=0，80/80 PASS） |

##### 5. 修复是否彻底（修一类）结论

**彻底**。engineer 不仅修了 reviewer 点名的 2 处（检查 8/9 的 `git diff` 缺 base 范围），还：
1. 新增 `BASE_COMMIT` 环境变量（默认 `ebb9ef2`，可覆盖以验证 FAIL 路径）
2. 同类排查检查 7：保留工作树残留检查（`git status`，合理）+ 追加 `$BASE_COMMIT..HEAD` 越界检查（提交后不再空转）
3. 全脚本 5 处 `git` 调用逐一定性：3 处已提交变更检测带范围、1 处工作树残留检测保留、1 处注释

**最终判决：Accepted**

#### 第 1 轮 architect 提交（正常）

**档位**：**正常提交**（reviewer 第 2 轮判 `Accepted`，含返工后复审）⇒ **无 `WIP:` 前缀**。

**文件集对账**（**显式 staging**，禁 `git add -A`；`git diff --cached --name-only` vs 任务书「修改文件」声明 + 任务范围）：

- **累计交付**（`ebb9ef2..HEAD`，11 个文件；已由第 1 轮 `WIP` 提交）：`contracts/opcodes.yaml`、`tools/spec/generate_opcodes.py`、`tools/spec/check_scope.py`、`tests/vectors/inventory.md`、`tools/llvm/validate_instrinfo.py`、`spec/SimRISC-11-其它.md`、`manifests/spec-readonly.lock.toml`、`.tao/knowledge/contract-{isa,asm,asm-list}.md`、本任务书。
- **本轮（收尾提交）新增**：`.tao/knowledge/changelog.md`、`.tao/knowledge/milestones.md`、`.tao/knowledge/MEMORY.md`、`.tao/knowledge/lessons.md`、`.tao/knowledge/feedback_007-证据脚本断言已提交变更须带提交范围.md`、本任务书（审阅记录追加）。
- **对账结论**：`git diff --cached --name-only` 实测与上述一致 —— **漏提：无 / 多提：无 / 越界：无**。
- **`spec/` 授权范围核对**（`git diff --cached --name-only -- spec/`）：**空**（本轮不改 `spec/`）。累计 `spec/` 变更仅 `spec/SimRISC-11-其它.md`（已由第 1 轮 `WIP` 提交，在用户授权范围内）。

**提交**：**正常提交**（信息 `SPEC-115t re-scope trap/escape/cfx2rc/cfx2rd（+生成器/锁同步）（reviewer Accepted）`）；**只 `commit`、绝不 `push`**（push 由主会话在 `/complete` 收尾后、将本任务本地提交 squash 为单一「已验证」提交再执行）。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：第 1 轮 **`Needs Revision`**（仅证据脚本 2 处：裸 `git diff` 在已提交树上假 FAIL；**交付物本身全达标**）→ engineer 返工（**修一类**：全脚本 3 处 git 调用排查 + 新增提交范围越界断言）→ 第 2 轮 **`Accepted`**（重跑 35/35 EXIT=0；`BASE_COMMIT=HEAD` ⇒ 精确 2 条 FAIL，反证断言非恒真；独立注入改 `cfx2rd` scope ⇒ `check_scope` EXIT=1 ⇒ `cp`+md5 还原回绿）。
- **architect 交叉复核**：**确认两轮判决恰当**。独立核：`check_scope` = `m1 155 / excluded 11 / total 227`；4 条 `op/mask/value` **逐字段未变**；`MC_ONLY_EXCLUDED_IDS` 已移除 4 条（仅剩 `fence_oiii_imm`）；`inventory.md` +4 行；**锁仅 `SimRISC-11` 一段 sha256 变（其余 19 册零变动）**；生成器重跑两次 md5 相同（`965feb70…`，幂等）；各子门控独立重跑全 EXIT=0。
- **授权范围**：`spec/` 改动**仅** `spec/SimRISC-11-其它.md`（用户授权原话「允许（re-scope SimRISC-11）」已落盘）；`SimRISC-12`/`DADAO-*`/`Toolchain-01`/`Process-*` 未动。
- **补充发现（不阻塞）**：reviewer 未独立重跑**聚合** `make check`（第 2 轮明确"采信上轮记录"，因该轮只改 gitignored 脚本 + 任务书、交付物 md5 未变）；architect 因「不跑 make」约束以**逐子门控独立重跑**补强。
- **遗留（须用户另行授权）**：`spec/Toolchain-01 §1` 仍写「9 种 M1 格式 / `crrr`/`crii`/`ciii` 属 `scope: excluded`」，与 re-scope 后 `m1` 实含 11 类不符 ⇒ 该册属**本轮授权范围外**，未改（连带其 sha256 锁未变）。
- **收尾检查**：`make check` EXIT=0（engineer 实测，含 `check-instrinfo`/`check-interface` 80/80/`check-lit` 62/62）；`git status --porcelain -uall` 干净；证据留 `.work/evidence/SPEC-115t/`、`.work/log/spec/`；知识沉淀含 `lessons §7.8/§7.9`。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
