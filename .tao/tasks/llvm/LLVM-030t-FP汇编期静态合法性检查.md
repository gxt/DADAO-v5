# LLVM-030t: FP 汇编期静态合法性检查（`dst_rf0` / `mreg_range_overlap` / `mreg_range_overflow` / `encode_fp_root_n`）

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：**`LLVM-029t`（FP 编码层，须先 `已验证`）**；`SPEC-088t`（FP 合法性归并，已验证）。相关：`contracts/legality_rules.yaml`（规则描述，Spec-first 来源）、`contracts/fp_semantics.yaml`（`legality_refs` 逐条映射）、`LLVM-028t`（M1 同类先例，汇编期重叠检查）。
**状态**：待开始

> 本任务书是**架构师规划产物**，尚未经用户确认、未下发。执行前须按 `AGENTS.md`「任务分解与执行确认」由用户逐条确认。
> **范围边界**：只做 **LLVM 汇编期静态检查**（`Error` 级硬报错，`llvm-mc` 非零退出）。**不含** QEMU 运行期 ILLI（`QEMU-034t`）、**不含** 向量/生成器（`TESTCASES-*`）、**不含** `opcodes.yaml` 规则回填/翻 status（spec 侧）。

---

## 0. 背景与本任务判断

`SPEC-087t`/`SPEC-088t` 在**纸面**落地了 FP 合法性：`contracts/legality_rules.yaml` 的 `dst_rf0`（`deferred`）、`encode_fp_root_n`（`deferred`）、`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`（共享，`active`）。`contracts/fp_semantics.yaml` 逐条给出 `legality_refs`。但 **LLVM 侧无任何 FP 检查**——`LLVM-029t` 之外，非法 FP 形式会被静默汇编（同 `LLVM-028t` 前态）。

**判断（供用户确认）**：与 `LLVM-028t` 体例一致，`kind: static` 且在**汇编语法中可表达**的规则应做汇编期硬报错。逐条可达性分析：

| 规则 | 适用条数 | 语法可表达？ | 本任务是否实现 |
|---|---|---|---|
| `dst_rf0`（目的 rf0 → ILLI） | 35 | ✅（`rf0` 是合法寄存器名） | ✅ |
| `mreg_range_overlap`（convert_ff 同组范围交集） | 4 | ✅（两组 `{start:end}`） | ✅ |
| `encode_fp_root_n`（`ftroot`/`foroot` n≠2） | 2 | ✅（n 是立即数） | ✅ |
| `mreg_range_overflow` | 28 | ⚠️ **仅 `count=64` 可达**（见 §1.3） | ✅（实现为 `count > 63`） |
| `mreg_zero`（immu6=0） | 28 | ❌（`{start:end}` 最小 count=1） | 由 `count>63` 覆盖「截断为 0」的路径；纯 0 不可表达 |
| `excp_*` / `encode_sbz` 等 | — | 动态/不适用 | ❌（非本任务） |

---

## 1. 事实核实（本轮 architect 实测，file:line 为 `.work/source/llvm-project/` 当前行号）

### 1.1 规则来源与逐条映射（Spec-first）
- `contracts/legality_rules.yaml`：`dst_rf0`、`mreg_range_overlap`、`mreg_range_overflow`、`encode_fp_root_n` 的 `description` **已明列**每条的适用指令族与示例（可作为实现依据，无需重推）。
- `contracts/fp_semantics.yaml`：60 条 `id → legality_refs`，分布为 `dst_rf0` 35、`mreg_zero/mreg_range_overflow` 28、`mreg_range_overlap` 4、`encode_fp_root_n` 2（`SPEC-088t` 门控 `check-fp-contract` 断言 28/28/4/35/2）。

### 1.2 AsmParser 结构（`AsmParser/DADAOAsmParser.cpp`）
- `matchAndEmitInstruction`（L845 起）：先 `rd2rd`/`rb2rb` 重叠检查（L872–904，**展开前**读 `Operands[]` 的 `kRegGroup`），再复杂操作数展开（L906–973），再 `ret` 静态检查，最后匹配。
- **FP 检查应同样放在展开之前**（组 count/范围在展开后被丢弃——`LLVM-028t` 新发现 F1）；标量检查可放展开后按 `Flat[]` 操作数取。
- 操作数顺序（实测）：标量 orrr/orri 为 `[token, dst, src…]`；`cs.n/z/p`-rf 为 `[token, cond(rd), dst(rf), src, src]`；`cs.eq/ne`-rf 为 `[token, cond1, cond2, dst(rf), src]`。

### 1.3 ⚠️ 可达性发现：`count=64` 会静默截断为 immu6=0
- 语法 `{rfA:rfB}` ⇒ `count = B-A+1`，`rfB ≤ rf63` ⇒ `start+count ≤ 64`；故 `start+immu6>64` 经语法**不可达**。
- **但** `{rf0:rf63}` ⇒ `count = 64`，而 `immu6` 仅 6 位（0–63），`64` 截断为 **0**（即 `mreg_zero` 的非法编码）。**M1 实测**：`ldm.o {rd0:rd63}, [rb0, rd0]` → `encoding: [0x38,0x00,0x00,0x00]`（hd=0，静默非法）。
- ⇒ FP 侧必须拒绝 `count > 63`（覆盖 `{rf0:rf63}`）；**`mreg_range_overflow` 的 `description`（`start+immu6>64`）漏掉 `start=0,count=64` 这一例**，属规范口径缺口，须在 `SPEC-08xt`（见 §7）一并订正（建议改为「`immu6` 不在 1–63 或 `start+immu6>64`」）。本任务按其**语义意图**实现 `count>63 ⇒ Error`。

### 1.4 先例
- `tests/lit/MC/Dadao/ret-rd0-legality.s`、`tests/lit/MC/Dadao/overlap-legality.s`（`%not %llvm_mc` + `FileCheck --check-prefix=ERR`）。

---

## 2. 设计（全部在 `DADAOAsmParser.cpp::matchAndEmitInstruction`）

### 2.1 `dst_rf0`（目的 rf0 → Error）
对下列 **35 条**，取目的操作数，若为 `rf0` 则 `Error`：
- **scalar orrr（16）**：`arith` 12（`ftadd/ftsub/ftmul/ftdiv/ftrem/ftsclb/foadd/fosub/fomul/fodiv/forem/fosclb`）+ `sign` 4（`ftsgnj/ftsgnn/fosgnj/fosgnn`）→ 目的 = 第 1 个寄存器操作数（`Flat[1]`）。
- **orri 目的 rf（14）**：`convert_ff` 4（`ft2fo/fo2ft/ft2ft/fo2fo`）+ `convert_i2f` 8（`it2ft/io2ft/ut2ft/uo2ft/it2fo/io2fo/ut2fo/uo2fo`）+ `root` 2（`ftroot/foroot`）→ 目的 = 组/寄存器首（`Flat[1]`）。
- **cs_rf（5）**：`cs.n/cs.z/cs.p` → 目的 = `Flat[2]`；`cs.eq/cs.ne` → 目的 = `Flat[3]`。
- **不适用**（不得误伤）：`rf2rd`、`st.t/st.o/stm.t/stm.o`-rf、`convert_f2i` 8、`classify` 2、`compare` 4（目的均为 rd 或无 rf 目的字段）。
- **例外（rf0 作目的合法，必须放行）**：`rd2rf`、`ld.t/ld.o/ldm.t/ldm.o`-rf、`set.w`-rf（FCSR 写掩码）。

### 2.2 `mreg_range_overlap`（convert_ff 4 条同组范围交集 → Error）
与 `LLVM-028t` 同法：`ft2fo/fo2ft/ft2ft/fo2fo` 的两个 `{rfA:rfB}` 组，半开区间 `[start, start+count)` 有交集（含完全重合，两种次序）⇒ `Error`。
- 仅 `convert_ff`；跨组 `rd2rf/rf2rd`、`convert_f2i`（rd 目的）、`convert_i2f`（rd 源）、`classify` 结构性不重叠，**不检查**。

### 2.3 `encode_fp_root_n`（`ftroot`/`foroot` n≠2 → Error）
- 语法 `ftroot rfHB, rfHC, immu6`：n = 末操作数（`Flat[3]`）。仅 `n == 2` 合法；`n != 2` ⇒ `Error`。
- 非常量/符号操作数一并拒绝（`getImmExpr() != nullptr`，对齐 `LLVM-027t`）。

### 2.4 `mreg_range_overflow`（`count > 63` → Error）
- 适用 **28 条 RF 多寄存器/块**：`convert_ff` 4、`convert_f2i` 8、`convert_i2f` 8、`classify` 2、`ldm.t/stm.t/ldm.o/stm.o`-rf 4、`rd2rf/rf2rd` 2。
- 由 `{start:end}` 的 `GroupCount` 得 count；`count > 63` ⇒ `Error`（`{rf0:rf63}` 触达）。
- **不适用**：`root`（immu6 是 n，另由 §2.3 管）、`ld.t/st.t/ld.o/st.o`（单寄存器）、`set.w`。

> **实现顺序建议**：先做展开前检查（overlap / dst_rf0 组前缀 / range / count），再做展开后检查（标量 dst_rf0 / root n）。所有检查 `Error` 级；消息含规则名（如 `mreg_range_overlap`）以便 lit ERR 串与 `check-interface`/grep 可核。

---

## 3. 交付物

| # | 文件 | 动作 |
|---|---|---|
| 1 | `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch` | 加 4 类 FP 静态检查 |
| 2 | `tests/lit/MC/Dadao/fp-legality.s` | 新建 lit（正例 + 负例） |
| 3 | `components/llvm-project/changelog.md` | 追加任务行 |
| 4 | `.work/evidence/LLVM-030t/run.sh` | 一键证据脚本（含 `--inject`） |
| 5 | `.work/log/llvm/LLVM-030t-*.log` | 构建/lit/check/注入完整输出 |

**明确不改**：`contracts/**`、`spec/**`、`tools/{spec,qemu,testcases}/**`、`components/qemu/**`、`tests/vectors/**`、`DADAOInstrInfo.td`（除非 `LLVM-029t` 尚未覆盖某条——本任务原则上只改 AsmParser）、其它 lit。

---

## 4. 执行环境
**执行环境**：本地

## 5. 接口规范

### 输入
- `components/llvm-project/patches/.../AsmParser/DADAOAsmParser.cpp.patch`（`LLVM-029t` 后的版本）。
- `contracts/legality_rules.yaml`（4 规则 `description`）、`contracts/fp_semantics.yaml`（`legality_refs` 逐条）。

### 输出
见 §3。

### 约束
- 中文；**不提交 git**；只动任务书范围；**失败即停，禁自动重试**。
- **重建成本申报**：改 AsmParser ⇒ `make prepare && make build-mc`（增量，预计 **5–15 分钟**）。
- 临时目录 `/tmp/opencode/LLVM-030t/`；日志 `.work/log/llvm/`；证据 `.work/evidence/LLVM-030t/`。

---

## 6. 验收标准（可执行、可失败、含反例注入）

1. **构建**：`make prepare && make build-mc` EXIT 0。
2. **正例不误伤**（`llvm-mc` rc=0）：`ftadd rf1, rf2, rf3`、`ftadd rf0, rf2, rf3`（rf0 源合法）、`rf2rd {rd3}, {rf4}`、`rd2rf {rf0}, {rd5}`（rf0 目的例外）、`ldm.t {rf0:rf3}, [rb1, rd0]`、`set.w rf0, wp0, 1`、`ftroot rf1, rf2, 2`、`ft2fo {rf4:rf6}, {rf8:rf10}`（不重叠）。
3. **负例硬报错**（`%not %llvm_mc` + ERR，rc≠0，stderr 含规则名）：
   - `dst_rf0`：`ftadd rf0, rf2, rf3`（orrr）、`it2ft {rf0}, {rd2}`（orri 组）、`cs.n {rd1}?, rf0, rf2, rf3`、`cs.eq {rd1, rd2}?, rf0, rf3`。
   - `mreg_range_overlap`：`ft2fo {rf3:rf4}, {rf2:rf3}`（部分重叠）、`ft2ft {rf3:rf3}, {rf3:rf3}`（完全重合，需按语法可表达——`{rf3:rf3}` count=1）、`fo2fo {rf2:rf3}, {rf3:rf4}`（目的在前）。
   - `encode_fp_root_n`：`ftroot rf1, rf2, 3`、`foroot rf1, rf2, 0`。
   - `mreg_range_overflow`：`ft2fo {rf0:rf63}, {rf1:rf62}`（count=64）、`ldm.t {rf0:rf63}, [rb1, rd0]`。
4. **lit**：`make check-lit` → 总数 **28→29**（新增 `fp-legality.s`）全 PASS；负例确实使 `llvm-mc` 非零退出。
5. **`make check` 全绿**：`repository checks: PASS`（`check-patch-tree` **68** OK、`check-interface` 80/80、`check-lit` 29/29）。
6. **反例可失败（承重，逐一注入）**：分别移除/放宽 4 类检查之一（如 `dst_rf0` 的判定、overlap 的 `!` 极性、root 的 `n==2`、`count>63` 的边界），重建 ⇒ 对应负例静默通过、lit FAIL；还原**并重建** ⇒ 回绿。注入须 `git diff --name-only` 非空；还原后干净且 sha256 复原。
7. **残留与越界**：`git status --untracked-files=all` 仅应改文件 + 本任务书；`check-no-residue` PASS；补丁数仍 **68**（只改既有补丁，`LLVM-029t` 已引入第 68 个）。

---

## 7. 硬约束清单（下发提示必带）

1. 临时目录 `/tmp/opencode/LLVM-030t/`，禁仓库内临时文件。
2. 不提交 git。
3. 完成区结论与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败即停，禁自动重试。
6. 补丁导出纪律（`spec/Process-01 §6/§8`，E1–E8）：动组件前先 `make check-source-state` 自检 **E1**（`.work/source/llvm-project` 干净 + HEAD=base+1）；**E2** 起点不干净须先收敛；**E3** 导出前校验 E1，不满足拒绝导出（补丁写 `/tmp`，含有效 hunk，无 0 行/空 blob）；**E4** 收敛为恰好 1 个 commit；**E5** `apply_series` 应用后自动 commit、重复应用幂等；**E6** `check-patch-tree` 断言⑦⑧⑨ + ⑥（应用产物 blob == 源树）；**E7** 改动前后各查一次 `--source-state`；**E8** 补丁为裸 `git diff`，本地 commit 永不推送上游。
7. 复杂命令输出留存 `.work/log/llvm/`。
8. 一键证据脚本：`engineer` 产 `.work/evidence/LLVM-030t/run.sh` 并跑通；`reviewer` 审脚本 + 重跑 + **独立注入一次反例**。

---

## 8. 风险与需用户拍板的点

1. **是否需要 FP 汇编期静态检查**：本任务建议实现（§0）。若用户裁定只做编码、合法性留 QEMU，则本任务取消并在 `deferred.md` 登记「FP 静态规则无汇编期检查」。
2. **`count>63` 属规范口径缺口（§1.3）**：`mreg_range_overflow` 的 `description` 未覆盖 `{rf0:rf63}`（count=64，截断为 0）。本任务按语义意图实现 `count>63`，并建议 spec 侧订正规则文字（见下）。
3. **与 spec 回填的先后**：`dst_rf0`/`encode_fp_root_n` 现为 `deferred`、`opcodes.yaml` 的 FP `rule_refs` 为空。本任务**不依赖**其翻 `active`（依据直接取自 `legality_rules.yaml`/`fp_semantics.yaml`）。若用户希望门控同步反映，须先做 **`SPEC-089t`**（回填 FP `rule_refs` + 翻 `active` + 重跑 `gen_legality_list`，`SimRISC-07` 生成区会变）；**下载前须另行确认**。
4. **`mreg_zero` 纯 0 不可表达**：仅 `count=64` 截断路径可达，故不单独实现 `count==0` 检查（语法上 `{start:end}` 最小 count=1）；如需防御性检查可在实现中一并加。
5. **报错文本/位置**：须与 lit `ERR` 串一致，并含规则名（便于 grep 与跨模块核对）。

---

## 9. 范围边界与后续任务

- **不在本棒**：QEMU 运行期 ILLI（`QEMU-034t`）；向量/生成器（`TESTCASES-024t`）；`opcodes.yaml` rule_refs 回填 + `dst_rf0`/`encode_fp_root_n` 翻 `active` + 重跑 `gen_legality_list`（**`SPEC-089t`**，建议）；FP 值 oracle（`GOLDEN-001t`）；FP E2E（`INTEG-*`）。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（待填写）

#### 第 1 轮 reviewer 验收
（待填写）
