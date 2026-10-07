# SPEC-115t: re-scope——`trap`/`escape`/`cfx2rc`/`cfx2rd` 由 `excluded` → 已实现

**模块**：spec
**项目里程碑**：M5
**依赖**：`SPEC-114t`、`SPEC-113t`、`SPEC-119t`
**状态**：待开始

> **⚠️ 前置（硬约束，2026-10-07 用户裁定新增）**：本任务将修改**上游只读册** `spec/SimRISC-11-其它.md`。按新规则「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」（`spec/Process-06`；机制见 `SPEC-119t`）——**下发前必须取得用户明确允许，并将授权原话落盘；否则 BLOCKED**。落地时须**在同一变更内更新 `manifests/spec-readonly.lock.toml` 中 `spec/SimRISC-11-其它.md` 的 `sha256` 锁**并在完成区记录用户授权原话；未更新锁 ⇒ `make check-spec-readonly` **FAIL**（`make check` 红）。（`spec/SimRISC-12-待定.md` 仅**只读引用**、不改。）

## 执行环境
**执行环境**：本地

## 接口规范

- **定位**：`trap`/`escape`/`cfx2rc`/`cfx2rd` 4 条在 `contracts/opcodes.yaml` 中现为 `scope: excluded` + `decode: ILLI`（`ISS-110`）。M5 要把这 **4 条**从 `excluded` **re-scope 为已实现**（跨组件原子：`spec/SimRISC-11` + `contracts/*` + 投影 + 门控计数 + （后续）LLVM/QEMU）。**`SimRISC-12` 的 `cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*` 保持 deferred**（`INTEG-019k C13`）。
- **输入（自包含）**：
  - `spec/SimRISC-11-其它.md`：`ASSEMBLY_LIST`（`cfx2rc`/`cfx2rd`/`escape`/`swym`/`trap` 5 条；`escape` 汇编形式 `escape cfxHA, [excp_cause_ip, imms20]`）；`LEGALITY` 段（**当前**：`scope: excluded（decode ILLI）` 列 `cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`/`escape_ciii_cfx`/`trap_ciii_cfx`）；`指令行为说明`（L80：`trap/escape/cfx2rd/cfx2rc/cfxld/cfxst` 可在任意运行模式执行；L121：读写不存在的 `cfx_<cfxname>_cgHB_rcHC` 组合 ⇒ CFXREG）；§陷入指令/§退出指令/§寄存器传输指令。
  - `spec/SimRISC-12-待定.md`（**保持 deferred**：`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）。
  - `contracts/opcodes.yaml`（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`，现 `scope: excluded`/`decode: ILLI`）；`contracts/legality_rules.yaml`。
  - `tools/spec/check_scope.py`（**计数门控**：现 `EXPECTED_M1=151`/`EXPECTED_FP=60`/`EXPECTED_EXCLUDED=15`/`EXPECTED_M3=1`/`EXPECTED_TOTAL=227`；`excluded ⇔ decode ILLI`）。
  - 投影：`.tao/knowledge/contract-isa.md`、`contract-asm.md`、`contract-asm-list.md`（生成投影）；`toolchain-01 §3.2`（**字段名映射**：汇编 `imms14/20/26` ⇔ 编码 `imms12/18/24`；`escape` 汇编层 `imms20`（字节，`%4==0`）⇔ 编码层 `imms18`（`field = bytes >> 2`），`Addr = excp_cause_ip + (imms18 << 2)`）。
- **输出**：
  1. **`spec/SimRISC-11` 的 `LEGALITY` 段 re-scope**：`trap`/`escape`/`cfx2rc`/`cfx2rd` 4 条由 `scope: excluded（decode ILLI）` **移出 excluded**（改为已实现口径——本任务落地时依 `<PSEUDO/LEGALITY 生成流程>` 与用户确认的标记方式；**保持 `SimRISC-12` 相关条目不动**）。
  2. **`contracts/opcodes.yaml`**：4 条 `scope: excluded`→**已实现 scope**（`m1`，与 `check_scope.py` 的合法集合一致），**移除 `decode: ILLI`**（与旧字段），填 `legality`/`rule_refs`（据 spec）。**计数**：`m1 151→155`、`excluded 15→11`、`total 227` 不变。`contracts/legality_rules.yaml` 同步（4 条不再 `decode ILLI`）。
  3. **`tools/spec/check_scope.py`**：更新 `EXPECTED_M1`/`EXPECTED_EXCLUDED`（151→155 / 15→11），保持 `excluded ⇔ decode ILLI`、`fp ⇔ _rf` 等结构性断言；`make check` 全绿。
  4. **投影刷新**：`contract-isa.md`/`contract-asm.md`/`contract-asm-list.md` 相应条目由「excluded/decode ILLI」更新为已实现；`escape` 位宽关系（汇编 `imms20` ⇔ 编码 `imms18`，`%4==0`）在 spec **写清**（`SimRISC-11 §退出指令` 或 `Toolchain-01 §3.2` 已述，本任务确保 spec 侧无歧义）。
  5. **`ISS-110` 部分收口**：任务完成区登记（`ISS-110` 的 crrr/crii/ciii + `cfx2rd`/`cfx2rc`/`escape`/`trap` 实现部分由 `SPEC-115t`+`LLVM-060t` 收口；`cfxld`/`cfxst`（`SimRISC-12`）与 `SPEC-075t` 的 uart2..30 别名缺口**另计**）。
- **约束（硬）**：
  - **只 re-scope 这 4 条**；`SimRISC-12`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）**保持 `excluded`/deferred**，**不得**顺手改。
  - **编码值不变**（`op`/`mask`/`value` 保持；只改 `scope`/`decode`/`legality`/`rule_refs`）。
  - 本条**改 `scope` ⇒ 跨组件原子**：`contracts/opcodes.yaml` ↔ LLVM MC（`LLVM-060t`）↔ QEMU（`QEMU-044t`/`045t`）计数须一致；`check-interface`/`check_scope`/`check_qemu_trans` 须绿。
  - `spec/`/`contracts/` 为共享文件，与 `SPEC-116t` 及其它改 `spec/`/`contracts/` 的任务**串行**。
  - `make check` EXIT=0；失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-115t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **re-scope 落地**：`grep -n "scope" contracts/opcodes.yaml` 显示 4 条（`trap_ciii_cfx`/`escape_ciii_cfx`/`cfx2rc_crrr_cfx`/`cfx2rd_crrr_cfx`）不再 `excluded`、无 `decode: ILLI`；`SimRISC-12` 条目仍 `excluded`；`spec/SimRISC-11` LEGALITY 段同步。给真实 `grep`/`sed` 输出。
2. **计数对齐**：`python3 tools/spec/check_scope.py` EXIT=0（`m1=155`/`excluded=11`/`total=227`）；给真实输出。
3. **编码不变**：4 条的 `op`/`mask`/`value` 与改前**逐字段相等**（`git diff contracts/opcodes.yaml` 仅 `scope`/`decode`/`legality`/`rule_refs` 行）；给真实 `git diff`。
4. **投影一致**：`contract-isa.md`/`contract-asm.md`/`contract-asm-list.md` 相应条目更新；`make check`（`check-asm-list*`/`check-legality-drift`/`check-interface`）EXIT=0。
5. **`escape` 位宽关系**：spec 侧写明「汇编 `imms20`（字节，`%4==0`）⇔ 编码 `imms18`（`>>2`），`Addr = excp_cause_ip + (imms18<<2)`」（`grep` 证据）。
6. **一键证据脚本**：`.work/evidence/SPEC-115t/run.sh`——非交互、失败非零、逐项打印；**内置注入自检**（把某条改回 `excluded`/改一条 `op` 字节 ⇒ 断言 **FAIL** ⇒ 还原 ⇒ 回绿），结尾**禁 `tee`**；给真实输出。
7. **无残留**：`git status --untracked-files=all` 仅 `spec/SimRISC-11-其它.md` + `contracts/{opcodes,legality_rules}.yaml` + `tools/spec/check_scope.py` + `.tao/knowledge/contract-*.md` + 本任务书。

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
（审查者独立验证：`run.sh` 审核 + 重跑 + **独立注入一次反例**〔改 scope/改编码字节〕+ 逐条核计数/编码不变/SimRISC-12 未动 + 判决）
