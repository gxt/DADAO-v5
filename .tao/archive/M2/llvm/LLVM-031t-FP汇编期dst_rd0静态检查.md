# LLVM-031t: FP `dst_rd0` 汇编期静态检查（rd-目的 15 条）

**模块**：llvm
**项目里程碑**：M2
**依赖**：`SPEC-089t`（FP 合法性 `dst_rd0` 回填，**已验证**）；相关先例 `LLVM-028t`（`rd2rd`/`rb2rb` 汇编期重叠静态检查）、`LLVM-027t`（`ret rd0` 汇编期硬报错）、`LLVM-030t`（FP 汇编期 4 类静态检查）。
**状态**：已验证

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。
> **范围边界**：只做 **LLVM 汇编期静态检查**（`Error` 级硬报错，`llvm-mc` 非零退出）。**不含** QEMU 运行期 ILLI（`QEMU-038t`，串行其后）、**不含**向量/生成器（`TESTCASES-*`）、**不含**合约/生成物改动（`SPEC-089t` 已完成）。

---

## 0. 背景与本任务判断

`SPEC-089t`（`已验证`）已在**合约层**为 FP 的 **rd-目的 15 条指令**补 `dst_rd0`（用户裁定 R2b = (A) 全补 15 条）：

- `convert_f2i` 8：`ft2it`/`ft2io`/`ft2ut`/`ft2uo`/`fo2it`/`fo2io`/`fo2ut`/`fo2uo`（orri，目的 `rdhb`）
- `classify` 2：`ftcls`/`focls`（orri，目的 `rdhb`）
- `compare` 4：`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp`（orrr，单目的 `rdhb`）
- `rf_move` 1：`rf2rd`（orri，目的 `rdhb`）

体现在 `contracts/opcodes.yaml`（`legality` 含 `rdhb != rd0`、`rule_refs` 含 `dst_rd0`）与 `contracts/fp_semantics.yaml`（`legality_refs` 含 `dst_rd0`），并有 `check_fp_contract` 的 **Check 8** 交叉断言防漂移。

**但 LLVM 当前不检 `dst_rd0@FP`**（`SPEC-089t §1.6` 已确认；本轮 architect 于 `.work/build/llvm/bin/llvm-mc` 复测，见 §1.3）：`LLVM-030t` 只做了 `dst_rf0`/FP `mreg_range_overlap`/`mreg_range_overflow`/`encode_fp_root_n`，这 15 条 rd-目的指令目的为 `rd0` 时被**静默汇编**。⇒ **合约要求 ILLI，实现不报** ⇒ 必须补齐（**不得回退合约**）。

**判断（供用户确认）**：`dst_rd0` 是 `active` 规则，且 `rd0` 在汇编语法中可显式表达（`rd1` 是合法寄存器名），R2b(A) 已把它落到合约；按 `LLVM-027t`/`LLVM-028t`/`LLVM-030t` 体例，**kind 侧可静态表达 ⇒ 汇编期 `Error` 级硬报错**。（若用户裁定「FP 静态规则只在 QEMU 报」，本任务取消，须在 `.tao/knowledge/issues.yaml` 登记「`dst_rd0@FP` 无汇编期检查」——**不得**改回合约。）

---

## 1. 事实核实（本轮 architect 实测；file:line 为 `.work/source/llvm-project/` 当前行号，执行时以重跑为准）

### 1.1 规则来源与逐条映射（Spec-first）
- `contracts/legality_rules.yaml` `dst_rd0`（`active`）：描述已由 `SPEC-089t` 扩写覆盖本次 15 条（orri 目的字段 `rdhb`：`convert_f2i`/`classify`/`rf2rd`；orrr 单目的 `rdhb`：`compare`）。
- `contracts/fp_semantics.yaml`（`.tao/knowledge/contract-fp.md §15` 为叙述投影）：15 条 `legality_refs` 含 `dst_rd0`（`ft2it..fo2uo` 8 + `ftcls/focls` 2 + `ftqcmp..foscmp` 4 + `rf2rd` 1，共 15；逐 id 见 §2.1）。
- `contracts/opcodes.yaml` 同 15 条 `rule_refs` 含 `dst_rd0`（`check-pass` 由 `check-fp-contract` Check 8 机械保证）。

### 1.2 AsmParser 结构（`AsmParser/DADAOAsmParser.cpp`，源 1342 行）
- `isFPDstRfMnemonic`（L850–859）：FP `dst_rf0` 的 30 条 mnemonics（**不含** 本次 15 条）。
- **展开后** FP 静态检查（L1251–1289）：`dst_rf0` 用 `Flat[1]`（orrr/orri 目的）、`cs.n/z/p` 用 `Flat[2]`、`cs.eq/ne` 用 `Flat[3]`；`encode_fp_root_n` 用 `Flat[3]`。
- `matchAndEmitInstruction` 分解规则（L1089–1098）：`kRegGroup` 只把**首寄存器**压入 `Flat`（含 `{a:b}` 的 `a`）；`orri` 块指令在分解末追加 saved count 作末操作数（L1147–1154）。⇒ 对本次 15 条，**目的起始寄存器统一位于 `Flat[1]`**（orri 的组首 / orrr 的单目的）。
- `dst_rd0` 检查应放在**展开后**（与 `dst_rf0` 同处），用 `Flat[1]->isReg() && Flat[1]->getReg() == DADAO::rd0`；`{rd0:rd2}` 组在分解后 `Flat[1]` 即 `rd0`，自然覆盖。

### 1.3 实测当前行为（本机已构建 `.work/build/llvm/bin/llvm-mc`）
15 条 rd0 目的**全部 rc=0 静默汇编**（示例）：

```
$ printf 'ft2it {rd0}, {rf4}\n' | llvm-mc -triple=dadao -show-encoding
ft2it {rd0}, {rf4}   ; encoding: [0x44,0xc0,0x01,0x01]          rc=0
$ printf 'ftqcmp rd0, rf1, rf2\n' | llvm-mc -triple=dadao -show-encoding
ftqcmp rd0, rf1, rf2 ; encoding: [0x44,0x80,0x00,0x42]          rc=0
$ printf 'rf2rd {rd0}, {rf4}\n' | llvm-mc -triple=dadao -show-encoding
rf2rd {rd0}, {rf4}   ; encoding: [0x40,0xf8,0x01,0x01]          rc=0
```

非 rd0 对照 `ft2it {rd1}, {rf4}`/`ftqcmp rd1, rf1, rf2`/`rf2rd {rd1}, {rf4}` 亦 rc=0（应继续 rc=0）。
（15 条 op/value 实测：`ft2it` 0x44C00000、`ftcls` 0x44000000、`ftqcmp` 0x44800000、`rf2rd` 0x40F80000 …，完整见 `contracts/opcodes.yaml`；本任务**不写编码**，仅补检查。）

### 1.4 先例
- `tests/lit/MC/Dadao/fp-legality.s`（`LLVM-030t`，`%not %llvm_mc` + `FileCheck --check-prefix=ERR` 体例）。
- 报错消息含规则名（`dst_rf0`/`mreg_range_overlap`…）以便 lit ERR 串与 grep/门控核对；本任务消息须含 `dst_rd0`。
- `make check-lit` 当前 **29/29**（26 MC `.s` + 3 E2E `.test`）；补丁当前 **69**（llvm 37 + qemu 32）。

---

## 2. 设计（全部在 `DADAOAsmParser.cpp::matchAndEmitInstruction`，源含 `LLVM-030t` 改动）

### 2.1 新增 helper `isFPDstRdMnemonic`
在 `isFPDstRfMnemonic` 附近新增（仅字符串判定，**不新增补丁**）：

```cpp
// FP instructions subject to the `dst_rd0` rule (SPEC-089t) whose destination is
// an RD register, i.e. `rd0` is illegal.  These are the 15 FP rd-destination
// forms: convert_f2i (8), classify (2), compare (4) and rf2rd (1).  rf2rd's
// destination is an RD register; rd2rf's destination is RF (rf0 legal) and is
// NOT listed.
static bool isFPDstRdMnemonic(StringRef M) {
  return M == "ft2it" || M == "ft2io" || M == "ft2ut" || M == "ft2uo" ||
         M == "fo2it" || M == "fo2io" || M == "fo2ut" || M == "fo2uo" ||
         M == "ftcls" || M == "focls" ||
         M == "ftqcmp" || M == "ftscmp" || M == "foqcmp" || M == "foscmp" ||
         M == "rf2rd";
}
```

### 2.2 新增检查块（展开后，紧接 `dst_rf0` 检查块）
在 FP 静态检查区（L1251 起）内、`dst_rf0` 判定之后加入：

```cpp
  // `dst_rd0` (SPEC-089t): the FP rd-destination forms (convert_f2i 8,
  // classify 2, compare 4, rf2rd 1) must not write rd0 (the hard-wired zero
  // register).  The destination start register is Flat[1] for both the orri
  // group forms and the orrr single-destination compare (see decomposition).
  if (isFPDstRdMnemonic(Mnemonic) && Flat.size() >= 2 && Flat[1]->isReg() &&
      Flat[1]->getReg() == DADAO::rd0)
    return Error(Flat[1]->getStartLoc(),
                 "invalid '" + Mnemonic.str() +
                     "': rd0 is the hard-wired zero register and cannot be a "
                     "destination (dst_rd0)");
```

- 与既有 `dst_rf0` 检查**并列、互斥**（`isFPDstRdMnemonic` 不含 `dst_rf0` 的 mnemonics，反之亦然），不误伤。
- 顺序提示：`mreg_range_overflow`/count-不等 在**展开前**先报；本检查在展开后。组合非法（如 `{rd0:rd63}`）由先执行者报出，**不影响本任务各自的反例**（反例均单独触达 `dst_rd0`）；engineer 实测确认每条 rd0 反例均报 `dst_rd0`。
- `rf0` 作**源**（`ft2it {rd1}, {rf0}`）不受影响；`rd2rf`/`ld.*`/`set.w` 不受影响。

### 2.3 lit（新建 `tests/lit/MC/Dadao/fp-dst-rd0-legality.s`）
- **正例（整文件干净汇编）**：4 族非 rd0 各覆盖 + 多寄存器非 rd0 + rf0 源对照：
  `ft2it {rd1}, {rf4}`、`ft2io {rd5}, {rf4}`、`ft2ut {rd2}, {rf4}`、`ft2uo {rd3}, {rf4}`、`fo2it {rd6}, {rf4}`、`fo2io {rd7}, {rf4}`、`fo2ut {rd8}, {rf4}`、`fo2uo {rd9}, {rf4}`、`ftcls {rd1}, {rf4}`、`focls {rd2}, {rf4}`、`ftqcmp rd1, rf2, rf3`、`ftscmp rd4, rf2, rf3`、`foqcmp rd5, rf2, rf3`、`foscmp rd6, rf2, rf3`、`rf2rd {rd1}, {rf4}`、`ft2it {rd4:rd6}, {rf8:rf10}`、`rf2rd {rd2:rd4}, {rf8:rf10}`、`ft2it {rd1}, {rf0}`（rf0 **源**合法）。
- **反例（`echo '…' | %not %llvm_mc … | FileCheck --check-prefix=ERR-RD0`）**：逐族至少 1 条、共 ≥11 条：
  `ft2it {rd0}, {rf4}`、`fo2uo {rd0}, {rf4}`、`ftcls {rd0}, {rf4}`、`focls {rd0}, {rf4}`、`ftqcmp rd0, rf2, rf3`、`ftscmp rd0, rf2, rf3`、`foqcmp rd0, rf2, rf3`、`foscmp rd0, rf2, rf3`、`rf2rd {rd0}, {rf4}`、`ft2it {rd0:rd2}, {rf4:rf6}`（组首 rd0）、`rf2rd {rd0:rd2}, {rf4:rf6}`。
- ERR 串匹配实际报错文本，须含 `dst_rd0`；体例照 `fp-legality.s`。
- **门槛**：`make check-lit` **29→30**（30/30 PASS）。

### 2.4 补丁纪律（**不新增补丁**）
- 只改**既有** `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（当前 1348 行）；补丁总数**仍 69**（llvm 37 + qemu 32），`check-patch-tree` 仍 `2 component(s), 69 patches OK`。
- 按 `spec/Process-01 §6/§8` E1–E8：动组件前 `make check-source-state`（E1：`.work/source/llvm-project` clean + HEAD=base+1）；E2 起点不干净先收敛；E3 导出前校验 E1、补丁写 `/tmp`、非空 blob；E4 收敛为恰好 1 commit；E5 `apply_series` 幂等；E6 `check-patch-tree` 断言⑦⑧⑨+⑥；E7 改动前后各查一次 `--source-state`；E8 补丁为裸 `git diff`。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch` | 加 `isFPDstRdMnemonic` + 检查块（**不新增补丁**） |
| 2 | `tests/lit/MC/Dadao/fp-dst-rd0-legality.s` | 新建 lit（正例 + ERR-RD0 反例） |
| 3 | `components/llvm-project/changelog.md` | 追加本任务行 |
| 4 | `.work/evidence/LLVM-031t/run.sh` | 一键证据脚本（含 `--inject`） |
| 5 | `.work/log/llvm/LLVM-031t-*.log` | 构建/lit/check/注入完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tools/{spec,qemu,testcases}/**`、`components/qemu/**`、`tests/vectors/**`、其它 lit、`DADAOInstrInfoFP.td`/`MCInstPrinter`。

## 4. 执行环境
**执行环境**：本地

### 4.1 依赖说明（与 `QEMU-038t` 串行）
同源规则 `dst_rd0@FP` 的**汇编期半边**（本任务）与**运行期半边**（`QEMU-038t`）。二者**不并行**，理由：① `AGENTS.md`「长构建一次只跑一个」「避免同工作树并发 `make check`/构建污染证据」；② 同一 15 条两侧检查先汇编期、后运行期，便于逐条对照与审计。**非功能硬前置**（`QEMU-038t` 探针为 hand-encode，不依赖 `llvm-mc`）——串行是为构建/证据纪律。

## 5. 接口规范

### 输入
- `components/llvm-project/patches/.../AsmParser/DADAOAsmParser.cpp.patch`（`LLVM-030t` 后版本，源 1342 行）。
- `contracts/legality_rules.yaml`（`dst_rd0`）、`contracts/fp_semantics.yaml`（15 条 `legality_refs`）、`contracts/opcodes.yaml`（同 15 条 `rule_refs`）、`.tao/knowledge/contract-fp.md §3/§8/§9/§12/§15`（Spec-first 真源）。
- 先例：`tests/lit/MC/Dadao/fp-legality.s`、`overlap-legality.s`、`ret-rd0-legality.s`。

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围；**失败即停，禁自动重试**。
- **重建成本申报**：改补丁 ⇒ `make prepare && make build-mc`（增量，预计 **5–15 分钟**；`JOBS=8`，禁全核并行）。
- 临时目录 `/tmp/opencode/LLVM-031t/`；日志 `.work/log/llvm/`；证据 `.work/evidence/LLVM-031t/`。
- **Spec-first**：15 条清单以 `fp_semantics.yaml` 的 `legality_refs` 含 `dst_rd0` 为准，不从实现反推。

---

## 6. 验收标准（可执行、可失败、含反例注入）

> 通用：完成区贴**真实命令输出与退出码**；被检命令自身退出码须显式捕获（`cmd > log 2>&1; rc=$?`，**禁** `cmd | tee log` 后取 `$?`）；复杂命令留 `.work/log/llvm/`；engineer 交付一键证据脚本 `.work/evidence/LLVM-031t/run.sh`（非交互、任一失败即非零退出、逐项打印「检查名 + 期望/实际 + 退出码」、内置 `--inject`）。

1. **构建**：`make prepare && make build-mc` EXIT 0（留 `LLVM-031t-build.log`）。
2. **正例不误伤**（rc=0）：§2.3 正例全组干净汇编；`ft2it {rd1}, {rf0}`（rf0 源）rc=0；既有 `fp-legality.s`/`fp-encoding.s` 仍 PASS。
3. **反例硬报错**（rc≠0，stderr 含 `dst_rd0`）：§2.3 反例逐条；覆盖 **4 族**（convert_f2i / classify / compare / rf2rd）+ 多寄存器组首。
4. **lit**：`make check-lit` → 总数 **29→30** 全 PASS；新 lit 的每条 ERR-RD0 均使 `llvm-mc` 非零退出。
5. **`make check` 全绿**：`repository checks: PASS`（重点 `check-patch-tree` **69**、`check-interface` 80/80、`check-lit` 30/30、`check-fp-contract` PASS）。
6. **反例可失败（承重，独立归因）**：见 §6.1；注入须 `git diff --name-only` 非空；还原**含重建**且 sha256 复原后回绿。
7. **残留与越界**：`git status --untracked-files=all` 仅应改文件 + 本任务书 + 新 lit；`check-no-residue` PASS；补丁数仍 **69**。
8. **不变量**：`contracts/**`/`spec/**`/`tests/vectors/**`/`components/qemu/**` **零改动**；M1/FP lit（`ret-rd0-legality.s`/`overlap-legality.s`/`fp-legality.s`/`fp-encoding.s` 等）**零回归**；**M1 探针群 + FP 探针群零新增失败**——本任务只改 AsmParser（`make build-mc`），**不重建 QEMU**，故 `tools/qemu/min_rom_probe_*.py` 全部产出不变（engineer 须复跑对照改前基线，确认逐字节一致）。

### 6.1 反例注入（逐条真实 FAIL→还原→回绿，独立归因、避免互相抵消）
- **(a) 全量移除**：删除 §2.2 检查块（或令 `isFPDstRdMnemonic` 恒 `false`）⇒ 全部 rd0 反例静默汇编 rc=0、新 lit FAIL。
- **(b) 单族子集（防互相抵消）**：从 `isFPDstRdMnemonic` 仅移除 `compare` 4 条 ⇒ **仅** `ftqcmp/ftscmp/foqcmp/foscmp` 反例静默 rc=0，`convert_f2i`/`classify`/`rf2rd` 反例仍报 `dst_rd0`（证每族检查各自承重、非只看全量聚合）。
- 归档要求：`--inject` 须含 (a)+(b) 两轮（LLVM 单文件增量重建约十余秒，成本可承受），每轮打印 `git diff --name-only`、源码 sha256；还原后源码 sha256 与二进制回绿。
- **空注入防护**：注入后 `git diff --name-only` 非空 / `git hash-object` 变化。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-031t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. **补丁导出纪律**（`spec/Process-01 §6/§8` E1–E8）：动组件前 `make check-source-state` 自检 E1；E2 起点不干净先收敛；E3 导出前校验 E1、补丁写 `/tmp`、非空 blob、无 0 行/空 hunk；E4 收敛为恰好 1 commit；E5 `apply_series` 幂等；E6 `check-patch-tree` 断言⑦⑧⑨+⑥；E7 改动前后各查一次 `--source-state`；E8 补丁为裸 `git diff`。
7. 复杂命令输出留存 `.work/log/llvm/`（捕获被检命令自身退出码）。
8. 一键证据脚本：engineer 产 `.work/evidence/LLVM-031t/run.sh` 并跑通；reviewer 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **是否需要 FP 汇编期 `dst_rd0` 检查**：本任务建议实现（§0）。若用户裁定只在 QEMU 侧，本任务取消并登记遗留（**不得**回退合约）。
2. **报错文本/位置**：须含 `dst_rd0` 且与 lit `ERR-RD0` 一致；位置取目的操作数 `Flat[1]->getStartLoc()`。
3. **`{rd0:rd2}` 多寄存器组**：目的起始 `rd0` ⇒ 报错（覆盖）；engineer 须实测确认。
4. **与 `mreg_range_overflow` 组合非法**：如 `{rd0:rd63}`（count=64）会先由展开前 overflow 报出；本任务反例**不**依赖该组合，确保单独触达 `dst_rd0`。
5. **串行**：与 `QEMU-038t` 不并行（§4.1）。

## 9. ADR 判断（须主动提醒）
- **建议：不立 ADR**（与 `SPEC-089t` 及 FP 系列此前裁定一致）。理由：本任务是**机械落地** `SPEC-089t` 已 `Accepted`/已 `active` 的合约事实（`dst_rd0@FP`），属**既有规则框架内的实现棒**，非新架构决策、无多方案分歧、无跨组件合约变更（合约已冻结）。判据见 `spec/Process-03`（高代价/跨模块/多方案/外部契约/结论固化/定位）均不满足新增 ADR 的门槛。

## 10. 范围边界与后续
- **不在本棒**：QEMU 运行期 ILLI（`QEMU-038t`，串行其后）；FP 向量/独立 oracle（`TESTCASES-*`/`GOLDEN-*`）；FP E2E（`INTEG-*`）。

## 完成区

**测试结果**：
- **构建**：`make prepare && make build-mc` EXIT=0（增量；`DADAOAsmParser.cpp.o` 编译 + 11 步目标，实测 **21.36 s**，`JOBS=8`，未全核）。AsmParser 源 1342→**1366** 行（本任务净 **+24**）。日志 `.work/log/llvm/LLVM-031t-build.log`（末行 `BUILD EXIT=0`）。
- **一键证据（正常模式）**：`.work/evidence/LLVM-031t/run.sh` → **55 checks, 0 failure(s), EVIDENCE: PASS, EXIT=0**：18 正例 rc=0（4 族非 rd0 + 多寄存器组 + `ft2it {rd1},{rf0}` rf0 源）+ **17 反例均 rc=1 且 stderr 含 `dst_rd0`**（15 条逐条 + 2 条 `{rd0:rd2}` 组首）+ 新 lit PASS + `make check-lit` 30/30 + 探针群 17 条与基线**逐字节一致** + `probe_037t` 91/91。日志 `.work/log/llvm/LLVM-031t-evidence.log`。
- **反例门控（`--inject`，两轮独立归因）**：EXIT=0，`INJECT MODE: 55 checks, 0 failure(s), PASS`。日志 `.work/log/llvm/LLVM-031t-evidence-inject.log`：
  - **轮 (a) 全量移除**（`if (false && isFPDstRdMnemonic(...) ...)`）：`git diff --name-only` 非空（`.../DADAOAsmParser.cpp`，注入后 sha256=`810bee1b…`，pre=`c20d3f27…`）→ 重建 → **全部 17 反例静默 rc=0**、新 lit **FAIL（rc=1）** → `git checkout` 还原 → sha256 复原 `c20d3f27…` → 重建 → 回绿。
  - **轮 (b) 仅移除 `compare` 族**（从 `isFPDstRdMnemonic` 删 `ftqcmp/ftscmp/foqcmp/foscmp` 行）：注入后 sha256=`5ee48409…` → 重建 → **仅 4 条 compare 反例静默 rc=0**，其余 **13 条（convert_f2i/classify/rf2rd）仍 rc=1 且含 `dst_rd0`**（证每族检查各自承重）→ 还原 sha256 复原 `c20d3f27…` → 重建 → 全绿。
  - **异常退出防护**：run.sh EXIT-trap 在注入态异常退出时自动 `git checkout`+重建（独立复现测试 `/tmp/opencode/LLVM-031t/trap_test.sh`：注入 → `os._exit(2)` → 打印 `CLEANUP: … restoring + rebuilding`，源 sha256 复原、llvm-mc 已重建可用）。
- **lit**：`llvm-lit tests/lit/MC/Dadao/fp-dst-rd0-legality.s` PASS；`make check-lit` **29→30**（30/30 PASS，含新 lit）。日志 `.work/log/llvm/LLVM-031t-lit-new.log`、`LLVM-031t-check-lit.log`。
- **`make check` 全绿**：EXIT=0（`repository checks: PASS`；`check-patch-tree: 2 component(s), 69 patches OK`；`check-interface 80 项 PASS 80 FAIL 0`；`check-fp-contract: PASS`；`check-scope: PASS`；`check-no-residue: PASS`；lit 30/30）。日志 `.work/log/llvm/LLVM-031t-check.log`、`LLVM-031t-check-final.log`。
- **E1/E7**：`make check-source-state` 改动前 EXIT=0（llvm-project `HEAD=a38b3ebec00e count=1 clean=True`）；改动后 EXIT=0（`HEAD=c8e1d0edaa5a count=1 clean=True`）；qemu 不变（`cf13beb9b9d2`）。
- **不变量**：`contracts/**`、`spec/**`、`tests/vectors/**`、`components/qemu/**` **零改动**（`git status --porcelain -- <四路径>` 空）；补丁数仍 **69**；M1/FP lit 零回归（30/30 全 PASS）。
- **探针群**：18 个 `tools/qemu/min_rom_probe_*.py` 复跑；17 个与 `.work/evidence/QEMU-037t/baseline` **逐字节 identical**（其中 6 个 rc=1 系基线既有状态，非本任务新增失败），`probe_037t` rc=0 91/91；本任务未重建 QEMU（仅 `make build-mc`）。

**修改文件**：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（既有补丁，加 `isFPDstRdMnemonic` + 检查块；源净 **+24** 行，patch 文件 +26/−2；补丁集仍 69）
- `tests/lit/MC/Dadao/fp-dst-rd0-legality.s`（新建；18 正例 + 11 `ERR-RD0` 反例 RUN）
- `components/llvm-project/changelog.md`（追加 LLVM-031t 一行）
- `.work/evidence/LLVM-031t/run.sh`、`.work/log/llvm/LLVM-031t-*.log`（证据/日志，`.work/` 不入库）
- `.work/source/llvm-project/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（组件工作树，`commit --amend` 收敛为 base+1，E1 干净；补丁集为真源）

**验收结果**（真实输出，完整见 `.work/log/llvm/`）：
- 15 条 rd0 反例 rc=1，stderr 例：`<stdin>:1:7: error: invalid 'ft2it': rd0 is the hard-wired zero register and cannot be a destination (dst_rd0)`（`{rd0:rd2}` 组首同样报出）。
- 正例对照 rc=0：`ft2it {rd1}, {rf4}`、`ftqcmp rd1, rf2, rf3`、`rf2rd {rd1}, {rf4}`、`ft2it {rd1}, {rf0}`（rf0 源）、`rf2rd {rd2:rd4}, {rf8:rf10}`。
- 注入轮 (a)：17/17 反例 rc=0 静默、lit rc=1；轮 (b)：4/4 compare rc=0 静默、13/13 其余 rc=1 含 `dst_rd0`；两轮还原 sha256 均复原 `c20d3f27276afd99f8d682b9baa8e9570738271eccfe0f269466a954b95b6502` 并重建回绿。

**新发现/坑**：
1. **探针“改前基线”的来源**：任务 §6.8 要求“复跑对照改前基线”，本任务采用 `.work/evidence/QEMU-037t/baseline/`（pre-QEMU-037t 探针日志；QEMU-037t 自身已断言 17 条 identical）。已核实**全部 18 个探针脚本均不引用 `llvm*`**（`grep -l llvm tools/qemu/min_rom_probe_*.py` 空），且本任务**未重建 QEMU**，故 llvm-mc 变更结构性不可能影响探针输出；17 条逐字节一致、`probe_037t` 91/91。建议沉淀：LLVM 模块任务的探针回归可复用该 baseline，判据是“逐字节一致 / 零新增失败”，**不要求**探针 rc=0（6 条基线既有 FAIL 非本任务引入）。
2. **注入脚本首版缺陷（已修）**：`inject_all` 曾写成 `"if (false && " + old` 致 `if (false && if (...` 编译失败并把工作树留在注入态。修正为在 `if (` 后精确插入 `false && `，并给 run.sh 加 EXIT-trap 兜底还原+重建。教训：注入替换串必须包含完整条件前缀，且 `--inject` 须有异常退出回滚。
3. **`make build-mc` 的既有告警**：`isRegBankPrefix` / `ComputeAvailableFeatures` unused-function 告警为仓库既有，与本任务无关（非新增）。

**遗留问题**：
- 无本任务遗留项（检查 + lit + 门控 + 双轮注入全部落地并通过）。
- 范围外（非本任务、未做）：`QEMU-038t` 运行期 ILLI 半边（任务书明确串行其后）；FP 向量/oracle（`TESTCASES-*`/`GOLDEN-*`）。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`DADAOAsmParser.cpp` 净 +24 行（helper `isFPDstRdMnemonic` + `dst_rd0` 检查块）、`fp-dst-rd0-legality.s`、`run.sh`、`changelog.md`；逐条核对 `fp_semantics.yaml`（15 条 `legality_refs` 含 `dst_rd0`）与 `opcodes.yaml`（同 15 条 `rule_refs` 含 `dst_rd0`），并核操作数位置与先例体例。

**逐行审查发现与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 15 条 mnemonic 清单须与 Spec 真源逐条一致，不得多/少 | ✅已核 | helper 逐条对照 `fp_semantics.yaml`：convert_f2i 8 + classify 2 + compare 4 + rf2rd 1 = 15；不含 `rd2rf`（RF 目的，rf0 合法） | `python3` 统计 `legality_refs` 含 `dst_rd0` 恰 15 条，与 helper 清单逐条相符 |
| F2 目的操作数位置：orri 组首 vs orrr 单目的是否统一为 `Flat[1]` | ✅已核 | 读分解代码：`kRegGroup` 只压首寄存器（含 `{rd0:rd2}` 的 `rd0`）；orri 块末追加 count 不影响 `Flat[1]`；orrr compare 目的即 `Flat[1]` | 15 反例 + 2 组首反例均命中 `dst_rd0`（证据脚本 17/17 rc=1） |
| F3 与 `dst_rf0` 是否互相误伤 | ✅已核 | 两 helper mnemonic 集合不相交；分别并列判定 | 15 条 rd0 均报 `dst_rd0` 而非 `dst_rf0`；`fp-legality.s`（dst_rf0）零回归 30/30 |
| F4 正例不得误伤（非 rd0 / rf0 源 / 多寄存器组） | ✅已核 | 检查仅当 `Flat[1]->getReg()==DADAO::rd0` 才报错 | 18 正例 rc=0；`ft2it {rd1},{rf0}`、`rf2rd {rd2:rd4},{rf8:rf10}` 均 rc=0 |
| F5 必须 `Error` 级（llvm-mc 非零退出），不得降 warning | ✅已核 | 用 `return Error(...)`，消息含 `dst_rd0` | 15 反例 rc=1；lit `%not` 依赖 rc≠0，静默注入轮 (a) 时 lit rc=1 |
| F6 `--inject` 首版会把 `if (false && if (...)` 写坏并遗留注入态 | ✅已修 | `inject_all` 改为在 `if (` 后插入 `false && `；run.sh 加 EXIT-trap 异常退出自动还原+重建 | 修后两轮 `--inject` EXIT=0；`trap_test.sh` 证明异常退出下源 sha256 复原且二进重建 |
| F7 探针基线的适用性与“不要求 rc=0” | ✅已核/披露 | 复用 `QEMU-037t/baseline`；脚本判据为 diff 字节一致（非探针 rc） | 17 条 identical、037t 91/91；「新发现」1 |
| F8 补丁纪律 E1–E8、不新增补丁 | ✅已核 | 只改既有 AsmParser 补丁；`commit --amend` 收敛 base+1；`make_patch.py` 导出裸 `git diff` | `check-source-state` 前后 EXIT=0；`check-patch-tree 69 patches OK`（含断言⑥应用产物一致性） |

**判决**：所有 finding 已修/已核，无未修项；正/反例、lit、`make check`、双轮注入门控全绿。**通过**（状态 → 待验收）。

**验证方式声明**：本任务独立验证由 reviewer 承担（重跑 `.work/evidence/LLVM-031t/run.sh` + `--inject` + 独立注入一次反例）。engineer 自审为自主逐行审查。

#### 第 1 轮 reviewer 验收

**审查方式**：独立重跑 `.work/evidence/LLVM-031t/run.sh`（正常 + `--inject`）+ 独立注入一次反例 + 门控全量重跑。

---

##### 1. 脚本审计结论

| 审计项 | 结论 |
|---|---|
| `check_positive` FAIL 路径 | rc≠0 时 `[FAIL]`，非恒真 ✅ |
| `check_negative` FAIL 路径 | rc=0 或 stderr 不含 rule → `[FAIL]`，非恒真 ✅ |
| 注入 (a) 方法 | `if (false && isFPDstRdMnemonic(...))` 禁用整条检查 ✅ |
| 注入 (b) 方法 | 从 helper 删 compare 4 条 mnemonic，逐族归因 ✅ |
| 注入有效性校验 | `git diff --name-only` 非空 + sha256 对比 ✅ |
| 还原机制 | `git checkout` + sha256 校验 + 重建 ✅ |
| EXIT-trap 异常防护 | 注入态异常退出自动还原+重建 ✅ |
| `die()` 路径 | `exit 2` 触发 EXIT trap 正确回滚 ✅ |
| `tee` 吞退出码 | 未使用 `cmd | tee; echo $?`，直接捕获 `$?` ✅ |

**结论**：脚本合格，两轮注入独立归因、非空可还原、含重建。

---

##### 2. 证据脚本正常模式重跑

```
$ bash .work/evidence/LLVM-031t/run.sh
== positive (must assemble, rc=0) ==
  [PASS] pos:ft2it {rd1}, {rf4}              rc=0
  [PASS] pos:ft2io {rd5}, {rf4}              rc=0
  [PASS] pos:ft2ut {rd2}, {rf4}              rc=0
  [PASS] pos:ft2uo {rd3}, {rf4}              rc=0
  [PASS] pos:fo2it {rd6}, {rf4}              rc=0
  [PASS] pos:fo2io {rd7}, {rf4}              rc=0
  [PASS] pos:fo2ut {rd8}, {rf4}              rc=0
  [PASS] pos:fo2uo {rd9}, {rf4}              rc=0
  [PASS] pos:ftcls {rd1}, {rf4}              rc=0
  [PASS] pos:focls {rd2}, {rf4}              rc=0
  [PASS] pos:ftqcmp rd1, rf2, rf3            rc=0
  [PASS] pos:ftscmp rd4, rf2, rf3            rc=0
  [PASS] pos:foqcmp rd5, rf2, rf3            rc=0
  [PASS] pos:foscmp rd6, rf2, rf3            rc=0
  [PASS] pos:rf2rd {rd1}, {rf4}              rc=0
  [PASS] pos:ft2it {rd4:rd6}, {rf8:rf10}     rc=0
  [PASS] pos:rf2rd {rd2:rd4}, {rf8:rf10}     rc=0
  [PASS] pos:ft2it {rd1}, {rf0}              rc=0
== negative dst_rd0 ==
  [PASS] neg:dst_rd0:ft2it {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:ft2io {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:ft2ut {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:ft2uo {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:fo2it {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:fo2io {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:fo2ut {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:fo2uo {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:ft2it {rd0:rd2}         rc=1
  [PASS] neg:dst_rd0:ftcls {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:focls {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:ftqcmp rd0,rf2,rf3      rc=1
  [PASS] neg:dst_rd0:ftscmp rd0,rf2,rf3      rc=1
  [PASS] neg:dst_rd0:foqcmp rd0,rf2,rf3      rc=1
  [PASS] neg:dst_rd0:foscmp rd0,rf2,rf3      rc=1
  [PASS] neg:dst_rd0:rf2rd {rd0},{rf4}       rc=1
  [PASS] neg:dst_rd0:rf2rd {rd0:rd2}         rc=1
== lit + check-lit + probes ==
  [PASS] lit:fp-dst-rd0-legality.s           rc=0
  [PASS] make check-lit                       30/30 rc=0
  [PASS] probe_005t..probe_036t (17个)        byte-identical
  [PASS] probe_037t                           91/91 rc=0

TOTAL: 55 checks, 0 failure(s)
EVIDENCE: PASS, EXIT=0
```

---

##### 3. 证据脚本 `--inject` 模式重跑

```
$ bash .work/evidence/LLVM-031t/run.sh --inject
pre-injection source sha256=c20d3f27276afd99f8d682b9baa8e9570738271eccfe0f269466a954b95b6502

########## ROUND (a): remove the WHOLE check ##########
  injected diff: llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
  injected sha256=810bee1b60b5b0670e328896453f0cd99d9bb55e2d9f61701e44a79ff909d67a
  build rc=0
  (a) ALL 17 negatives → rc=0 (silent) ✅
  (a) lit FAILs (rc=1) ✅
  restored sha256=c20d3f27... (matches) ✅
  build rc=0

########## ROUND (b): remove ONLY the compare family ##########
  injected diff: llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
  injected sha256=5ee48409739fe4804a552b15ee379cc39fa0a528b8656f909c047e3ea7a3030c
  build rc=0
  (b) 4 compare negatives → rc=0 (silent) ✅
  (b) 13 other negatives → rc=1 (dst_rd0) ✅
  restored sha256=c20d3f27... (matches) ✅
  build rc=0

== restored: full check set green ==
INJECT MODE: 55 checks, 0 failure(s), EXIT=0
```

---

##### 4. 我的独立注入（不用脚本自带两轮）

**注入方式**：将 `DADAOAsmParser.cpp:1297` 的 `Flat[1]->getReg() == DADAO::rd0` 改为 `DADAO::rd1`（使检查只拦截 rd1，不拦截 rd0）。

**注入前**：
```
sha256=c20d3f27276afd99f8d682b9baa8e9570738271eccfe0f269466a954b95b6502
git diff --name-only: (empty)
```

**注入后**：
```
sha256=a53f59564b848dcaa7f27ca060753f5ab846cd3a0020f7fffc2b9c9509296d0a
git diff --name-only: llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp (non-empty ✅)
```

**注入后重建 + 验证**：
```
make build-mc → EXIT=0

17 条 rd0 反例全部 rc=0 (静默通过)：
  ft2it {rd0}, {rf4} → rc=0
  ft2io {rd0}, {rf4} → rc=0
  ft2ut {rd0}, {rf4} → rc=0
  ft2uo {rd0}, {rf4} → rc=0
  fo2it {rd0}, {rf4} → rc=0
  fo2io {rd0}, {rf4} → rc=0
  fo2ut {rd0}, {rf4} → rc=0
  fo2uo {rd0}, {rf4} → rc=0
  ftcls {rd0}, {rf4} → rc=0
  focls {rd0}, {rf4} → rc=0
  ftqcmp rd0, rf2, rf3 → rc=0
  ftscmp rd0, rf2, rf3 → rc=0
  foqcmp rd0, rf2, rf3 → rc=0
  foscmp rd0, rf2, rf3 → rc=0
  rf2rd {rd0}, {rf4} → rc=0
  ft2it {rd0:rd2}, {rf4:rf6} → rc=0
  rf2rd {rd0:rd2}, {rf4:rf6} → rc=0

lit fp-dst-rd0-legality.s → FAIL (rc=1) ✅
```

**还原**：
```
git checkout -- llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
sha256=c20d3f27276afd99f8d682b9baa8e9570738271eccfe0f269466a954b95b6502 (复原 ✅)
git diff --name-only: (empty) ✅
make build-mc → EXIT=0
```

**还原后回绿**：
```
ft2it {rd0}, {rf4} → rc=1 ✅
ftqcmp rd0, rf2, rf3 → rc=1 ✅
rf2rd {rd0}, {rf4} → rc=1 ✅
lit fp-dst-rd0-legality.s → PASS (rc=0) ✅
```

**结论**：独立注入成功证伪——改判据后检查失效，还原并重建后回绿。证明检查非恒真、每条承重。

---

##### 5. 门控重跑

| 门控 | 结果 |
|---|---|
| `make check` | EXIT=0，`repository checks: PASS` ✅ |
| `check-lit` | 30/30 (100.00%) ✅ |
| `check-patch-tree` | 2 component(s), 69 patches OK ✅ |
| `check-fp-contract` | PASS（dst_rd0: 15 refs）✅ |
| `check-interface` | 全部 PASS ✅ |
| `check-no-residue` | PASS ✅ |

---

##### 6. 约束核验

| 约束 | 状态 |
|---|---|
| 源 1342→1366 行（净+24） | ✅ 实测 1366 行 |
| 新 lit `fp-dst-rd0-legality.s` | ✅ 已创建，18正例+11 ERR-RD0 反例 |
| check-lit 29→30 | ✅ 30/30 |
| 补丁数仍 69 | ✅ `check-patch-tree: 69 patches OK` |
| `contracts/**`/`spec/**`/`tests/vectors/**`/`components/qemu/**` 零改动 | ✅ `git diff --name-only` 空 |
| 探针群零新增失败 | ✅ 17 条 byte-identical，probe_037t 91/91 |
| git status 仅本任务改动 | ✅ 修改 changelog.md + .cpp.patch；新建 fp-dst-rd0-legality.s + 任务文件 |
| 不提交 git | ✅ 未提交 |
| 临时产物 `/tmp/opencode/LLVM-031t-review/` | ✅ |
| 15 条 mnemonic 与合约一致 | ✅ `fp_semantics.yaml` 恰 15 条 `dst_rd0` |

---

##### 7. 判决

**Accepted**

所有验收命令在 reviewer 独立重跑下全部通过：
- 18 正例 rc=0、17 反例 rc=1 且 stderr 含 `dst_rd0`（覆盖 4 族 + 多寄存器组首）
- 新 lit PASS、`make check-lit` 30/30、`make check` EXIT=0
- 补丁 69、不变量零改动、探针零回归
- 脚本 `--inject` 两轮通过（全量移除 + 仅 compare 族），sha256 复原
- reviewer 独立注入（改 rd0→rd1 判据）证伪成功，还原+重建后回绿
- 无恒真断言、无未披露越界、完成区与真实输出一致
