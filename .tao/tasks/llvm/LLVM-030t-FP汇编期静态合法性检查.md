# LLVM-030t: FP 汇编期静态合法性检查（`dst_rf0` / `mreg_range_overlap` / `mreg_range_overflow` / `encode_fp_root_n`）

**模块**：llvm
**项目里程碑**：M2
**依赖**：**`LLVM-029t`（FP 编码层，须先 `已验证`）**；`SPEC-088t`（FP 合法性归并，已验证）。相关：`contracts/legality_rules.yaml`（规则描述，Spec-first 来源）、`contracts/fp_semantics.yaml`（`legality_refs` 逐条映射）、`LLVM-028t`（M1 同类先例，汇编期重叠检查）。
**状态**：已验证

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
- **构建**：`make prepare && make build-mc` EXIT=0（增量；AsmParser 编译+链接 3 步，实测单文件增量重建 **11.45 s**，`JOBS=8`）。源文件 1177→**1342** 行（本任务净 **+165**）。
- **一键证据**：`.work/evidence/LLVM-030t/run.sh` → **24 checks, 0 failure, EVIDENCE: PASS**（12 正例 rc=0 + 11 反例 rc=1 且 stderr 含规则名 + lit 1）。`--inject` → **EXIT=0**：4 类检查同时放宽后重建，4 条代表反例全部静默 rc=0；`git checkout` 还原 sha256 复原（`90d05678…`）、重建后 24/24 回绿。
- **lit**：`llvm-lit fp-legality.s` PASS；`make check-lit` **28→29**（29/29 PASS）。
- **`make check`**：**EXIT=0**（`repository checks: PASS`；`check-patch-tree 2 component(s), 68 patches OK`；`check-interface 80 项 PASS 80 FAIL 0`；`check-scope: PASS`；`check-rule-refs: PASS (规则 16 条 / 指令引用 198)`；`check-fp-contract: PASS`；`check-no-residue: PASS`；lit 29/29）。
- **E1/E7**：`make check-source-state` EXIT=0（llvm-project `HEAD=a38b3ebec00e count=1 clean=True`；qemu 不变）。
- **不变量**：`contracts/**`、`spec/**`、`tests/vectors/**`、`components/qemu/**`、`tools/{spec,qemu,testcases}/**` 零改动（`git diff --stat` 空）；补丁数仍 **68**（llvm 37 + qemu 31；仅改写既有第 37 份）。

**修改文件**：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp.patch`（加 4 类 FP 静态检查；净 +165 行；补丁体与源树逐字节一致）
- `tests/lit/MC/Dadao/fp-legality.s`（新建；22 正例 + 11 反例 RUN）
- `components/llvm-project/changelog.md`（追加 LLVM-030t 行）
- `.work/evidence/LLVM-030t/run.sh`、`.work/log/llvm/LLVM-030t-*.log`（证据/日志，`.work/` 不入库）
- `.work/source/llvm-project/...`（组件工作树，`commit --amend` 收敛为 base+1，E1 干净；补丁集为真源）
- （工作外动作，已披露）`DADAOInstrInfoFP.td`、`MCInstPrinter` **未改**——本任务只改 AsmParser。

**验收结果**（真实输出摘要，完整见 `.work/log/llvm/`）：
- 正例 rc=0：`ftadd rf1, rf2, rf3`、`ftadd rf1, rf0, rf3`（**rf0 源**）、`ftsgnj rf1, rf0, rf3`、`rf2rd {rd3}, {rf0}`、`rd2rf {rf0}, {rd5}`（例外）、`ldm.t {rf0:rf3}, [rb1, rd0]`（例外）、`ldm.t {rf0:rf62}, …`（count=63 边界）、`set.w rf0, wp0, 1`、`ftroot rf1, rf2, 2`、`ft2fo {rf4:rf6}, {rf8:rf10}`（不重叠）、`ft2fo {rf1}, {rf0}`、`cs.n {rd1}?, rf4, rf0, rf8`。
- 反例 rc=1 且含规则名：`ftadd rf0, rf2, rf3` / `it2ft {rf0}, {rd2}` / `cs.n {rd1}?, rf0, rf2, rf3` / `cs.eq {rd1, rd2}?, rf0, rf3` → `dst_rf0`；`ft2fo {rf3:rf4}, {rf2:rf3}` / `ft2ft {rf3:rf3}, {rf3:rf3}`（完全重合）/ `fo2fo {rf2:rf3}, {rf3:rf4}` → `mreg_range_overlap`；`ftroot rf1, rf2, 3` / `foroot rf1, rf2, 0` → `encode_fp_root_n`；`ft2fo {rf0:rf63}, {rf1:rf62}` / `ldm.t {rf0:rf63}, [rb1, rd0]` → `mreg_range_overflow`。
- 反例门控（`--inject`）：`inject: applied 6 loosenings` → `git diff --name-only` 非空 → 重建 → 4 反例静默 rc=0 → 还原（sha256 `90d05678…` 复原、worktree clean）→ 重建 → 24/24 回绿。
- 边界补充：`ftroot rf1, rf2, foo`/`-1`/`4` → 报错（非常量/非 2）；`ftroot rf0, rf2, 2` → `dst_rf0`；`ftqcmp rd4, rf0, rf3`/`foscmp rd4, rf1, rf0` 放行；M1 `ldm.o {rd0:rd63}` 与 `rd2rd`/`rb2rb` 行为**不变**。

**新发现/坑**：
1. **任务书 §6.2 正例与 §6.3 反例自相矛盾**：§6.2 把 `ftadd rf0, rf2, rf3` 列为「正例（rf0 源合法）」，但 §6.3/§2.1 把同一串列为 `dst_rf0` 反例。按规则语义（`ftadd` 目的为第一个操作数）与 §2.1/§6.3，该串**必须报错**；rf0 作**源**的正确正例是 `ftadd rf1, rf0, rf3`（本任务据此实现与测试）。建议 spec/任务书侧订正 §6.2 该条。
2. **`mreg_range_overflow` 与 `LLVM-029t` count-不等加固的优先级**：convert_ff 的 `{rf0:rf63}` 必然与另一组 count 不等，若沿用原顺序会先报「counts differ」而非规则名 `mreg_range_overflow`；故新检查置于 LLVM-029t 加固**之前**（仍只对 FP 组；M1 `rd2rd`/`rb2rb` 行为不变）。已实测两条 overflow 反例均报 `mreg_range_overflow`。
3. **`{rf0:rf63}`（count=64）唯一语法可达的溢出**：`parseRegGroup` 上限 64，故 `count>63` 即精确等价于拒绝 count=64（覆盖 `mreg_zero` 的 64→0 截断路径）；纯 count=0 语法不可表达。
4. **M1 RD 侧 `{rd0:rd63}` 仍静默截断（本任务范围外）**：`ldm.o {rd0:rd63}, [rb1, rd0]` 仍产出 `encoding [0x38,0x00,0x10,0x00]`（hd=0，非法）。本任务按 FP 范围仅检查 RF 组，未动 M1（任务书「明确不改」）。属既有 `mreg_range_overflow`（M1 active）实现缺口，建议另立任务补 M1 侧。
5. **`decode` 侧无对应**：本任务只做汇编期；运行期 ILLI 仍归 `QEMU-034t`（FP 尚未被 QEMU 执行）。

**遗留问题**：
- 无本任务遗留项（4 类检查 + lit + 门控 + 注入全部落地并通过）。
- 范围外建议（非本任务、未做）：① M1 RD 多寄存器 `{rd0:rd63}` 的 `mreg_range_overflow` 汇编期检查（见「新发现」4）；② `dst_rf0`/`encode_fp_root_n` 在 `legality_rules.yaml` 仍为 `deferred`、`opcodes.yaml` FP `rule_refs` 仍空（任务书 §8.3 明确不依赖其翻 `active`，建议由 `SPEC-089t` 回填）；③ 任务书 §6.2 正例笔误订正。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**：`DADAOAsmParser.cpp` 净 +165 行（helper 4 个 + 3 处检查块）、`fp-legality.s`、`run.sh`；逐条核对规则映射（`legality_rules.yaml`/`fp_semantics.yaml`）与任务书 §2/§6。

**逐行审查发现与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `mreg_range_overflow` 若排在 `LLVM-029t` count-不等检查之后，convert_ff 的 `{rf0:rf63}` 会报错但**规则名不符**（lit ERR 无法匹配） | ✅已修 | 将该检查独立成块，置于既有 `if (Operands.size()==3)` 加固**之前**（仅 FP 组） | `ft2fo {rf0:rf63}, {rf1:rf62}` → rc=1 且含 `mreg_range_overflow`（证据脚本 + 手测） |
| F2 `dst_rf0` 对 cs 目的操作数位置：任务书给的是展开后 `Flat[2]`/`Flat[3]`，但 **pre-expansion** 下 cond 组是单操作数（`Operands[2]`），若照搬会错位 | ✅已修 | cs 检查放在**展开后**按 `Flat` 取值（`cs.n/z/p`→`Flat[2]`，`cs.eq/ne`→`Flat[3]`），与任务书一致 | `cs.n {rd1}?, rf0, …`/`cs.eq {rd1, rd2}?, rf0, …` → rc=1、定位列正确 |
| F3 helper `firstRegisterOf` 对非 reg/group 返回 0；`isRFRegister(0)` 为 false，需确保不误判 | ✅已修 | 调用点均先判 `Kind==kRegGroup`（overflow）或 `isReg()`（dst_rf0） | `ldm.o {rd0:rd63}`（非 RF）不触发 FP overflow；M1 行为不变 |
| F4 任务书 §6.2 把 `ftadd rf0, rf2, rf3` 列为正例，与规则/§6.3 矛盾 | ✅按规则实现并披露 | 未把该串当正例；正例改用 `ftadd rf1, rf0, rf3`（rf0 源） | 规则语义 + §2.1/§6.3；「新发现/坑」1 |
| F5 `ftroot` 的 n 非常量/负数/符号需拒绝 | ✅已修 | root 判定用 `getImmExpr()!=nullptr || getImm()!=2` | `ftroot rf1, rf2, foo`/`-1`/`4` 均 rc=1 |
| F6 注入脚本需保证「注入确实改动文件」且「还原 sha256 复原」 | ✅已修 | `run.sh --inject`：`git diff --name-only` 断言非空 + 前后 `sha256sum` 比对 + `git checkout` 还原 | inject 日志：`injected diff: …`、`restored sha256=90d05678… (matches)` |

**判决**：所有 finding 已修，无未修项；正/反例、lit、`make check`、注入门控全绿。**通过**（状态 → 待验收）。

**验证方式声明**：本任务独立验证由 reviewer 承担（重跑 `.work/evidence/LLVM-030t/run.sh` + 独立注入一次反例）。engineer 自审为自主逐行审查。

#### 第 1 轮 reviewer 验收

**审查范围**：`DADAOAsmParser.cpp.patch`（+165 行）、`fp-legality.s`、`run.sh`；逐条重跑验收命令 + 独立注入一次反例。

---

##### 1. 证据脚本重跑（正常模式）

```
$ bash .work/evidence/LLVM-030t/run.sh
== positive (must assemble, rc=0) ==
  [PASS] pos:ftadd rf1, rf2, rf3      expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:ftadd rf1, rf0, rf3      expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:ftsgnj rf1, rf0, rf3     expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:rf2rd {rd3}, {rf0}       expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:rd2rf {rf0}, {rd5}       expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:ldm.t {rf0:rf3}, [rb1, rd0] expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:ldm.t {rf0:rf62}, [rb1, rd0] expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:set.w rf0, wp0, 1        expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:ftroot rf1, rf2, 2       expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:ft2fo {rf4:rf6}, {rf8:rf10} expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:ft2fo {rf1}, {rf0}       expected=rc=0               actual=rc=0               rc=0
  [PASS] pos:cs.n {rd1}?, rf4, rf0, rf8 expected=rc=0               actual=rc=0               rc=0
== negative dst_rf0 ==
  [PASS] neg:dst_rf0 ×4              rc=1, 含 dst_rf0
== negative mreg_range_overlap ==
  [PASS] neg:mreg_range_overlap ×3   rc=1, 含 mreg_range_overlap
== negative encode_fp_root_n ==
  [PASS] neg:encode_fp_root_n ×2     rc=1, 含 encode_fp_root_n
== negative mreg_range_overflow ==
  [PASS] neg:mreg_range_overflow ×2  rc=1, 含 mreg_range_overflow
== lit fp-legality.s ==
  [PASS] lit:fp-legality.s            rc=0

TOTAL: 24 checks, 0 failure(s)
EVIDENCE: PASS
EXIT=0
```

##### 2. 逐项独立验证（reviewer 自己的输入）

**dst_rf0 四格式位置**（独立输入，非脚本内用例）：

| 格式 | 测试指令 | 期望 | 实际 | rc |
|---|---|---|---|---|
| orrr | `ftadd rf0, rf2, rf3` | dst_rf0 报错 | ✅ `error: invalid 'ftadd': rf0 is the FCSR...` | 1 |
| orri | `it2ft {rf0}, {rd2}` | dst_rf0 报错 | ✅ `error: invalid 'it2ft': rf0 is the FCSR...` | 1 |
| cs.n | `cs.n {rd1}?, rf0, rf2, rf3` | dst_rf0 报错 | ✅ `error: invalid 'cs.n': rf0 is the FCSR...` | 1 |
| cs.eq | `cs.eq {rd1, rd2}?, rf0, rf3` | dst_rf0 报错 | ✅ `error: invalid 'cs.eq': rf0 is the FCSR...` | 1 |

**dst_rf0 例外（rf0 目的合法）**：

| 指令 | 期望 | 实际 | rc |
|---|---|---|---|
| `rd2rf {rf0}, {rd5}` | rc=0 | ✅ | 0 |
| `ldm.t {rf0:rf3}, [rb1, rd0]` | rc=0 | ✅ | 0 |
| `set.w rf0, wp0, 1` | rc=0 | ✅ | 0 |

**rf0 作源**：`ftadd rf1, rf0, rf3` → rc=0 ✅

**mreg_range_overlap**：

| 测试 | 期望 | 实际 | rc |
|---|---|---|---|
| `ft2fo {rf3:rf4}, {rf2:rf3}` 部分重叠 | overlap 报错 | ✅ | 1 |
| `ft2ft {rf3:rf3}, {rf3:rf3}` 完全重合 | overlap 报错 | ✅ | 1 |
| `fo2fo {rf2:rf3}, {rf3:rf4}` 目的在前 | overlap 报错 | ✅ | 1 |
| `ft2fo {rf4:rf6}, {rf8:rf10}` 不重叠 | rc=0 | ✅ | 0 |
| `ft2it {rd4:rd6}, {rf8:rf10}` 跨组 | rc=0（不适用） | ✅ | 0 |

**mreg_range_overflow**：

| 测试 | 期望 | 实际 | rc |
|---|---|---|---|
| `ft2fo {rf0:rf63}, {rf1:rf62}` count=64 | overflow 报错 | ✅ `register range too long (mreg_range_overflow)` | 1 |
| `ldm.t {rf0:rf63}, [rb1, rd0]` count=64 | overflow 报错 | ✅ | 1 |
| `ldm.t {rf0:rf62}, [rb1, rd0]` count=63 | rc=0 | ✅ | 0 |
| `ldm.o {rd0:rd63}, [rb1, rd0]` M1 RD | rc=0（不适用） | ✅ | 0 |

**encode_fp_root_n**：

| 测试 | 期望 | 实际 | rc |
|---|---|---|---|
| `ftroot rf1, rf2, 2` n=2 | rc=0 | ✅ | 0 |
| `ftroot rf1, rf2, 3` n=3 | root_n 报错 | ✅ | 1 |
| `foroot rf1, rf2, 0` n=0 | root_n 报错 | ✅ | 1 |
| `ftroot rf0, rf2, 2` 目的 rf0 | dst_rf0 报错 | ✅ | 1 |

##### 3. 门控验证

```
$ make check-lit
Total Discovered Tests: 29
  Passed: 29 (100.00%)
EXIT=0

$ make check
check-patch-tree: 2 component(s), 68 patches OK
check-interface: 80 项 PASS 80 FAIL 0
check-scope: PASS
check-fp-contract: PASS
check-no-residue: PASS
lit: 29/29
repository checks: PASS
EXIT=0

$ make check-source-state
llvm-project: OK HEAD=a38b3ebec00e count=1 clean=True
qemu: OK HEAD=b74252bfe2bd count=1 clean=True
EXIT=0
```

##### 4. 不变量核验

- `contracts/**`：零改动 ✅
- `spec/**`：零改动 ✅
- `tests/vectors/**`：零改动 ✅
- `components/qemu/**`：零改动 ✅
- 补丁数：68（llvm 37 + qemu 31）✅
- 源 HEAD：`a38b3ebec00e`，count=1，clean=True ✅

##### 5. 脚本审计结论

`run.sh` 审计结果：
- **退出码捕获**：`assemble_one()` 用 `$?` 捕获 `llvm-mc` 退出码，不经过管道吞退出码 ✅
- **正例 12 条**：覆盖 orrr/convert_i2f/root/cs/例外/边界(count=63) ✅
- **反例 11 条**：dst_rf0(4) + overlap(3) + root_n(2) + overflow(2) ✅
- **FAIL 路径**：每条 check_positive/check_negative 均有 PASS/FAIL 两分支，FAIL 时 FAILURES 递增 ✅
- **恒真检查**：无 `check(name, True)` 恒真断言；每条断言的期望值与实际值独立比较 ✅
- **注入模式（`--inject`）**：6 处放宽（dst_rf0 3 + overlap 1 + root_n 1 + overflow 1），非空还原，sha256 比对 ✅
- **脚本合格**：可失败、非恒真、有 FAIL 路径、退出码正确捕获 ✅

##### 6. 独立注入（reviewer 自选，非脚本自带 6 处）

**注入点**：`encode_fp_root_n` 的判定条件 `NOp->getImmExpr() != nullptr || NOp->getImm() != 2` → 改为 `NOp->getImmExpr() != nullptr || NOp->getImm() < 2`（使 n=3 静默通过）。

**注入前 sha256**：`90d056785c8105347b40197e74441bb6944cddd5650389324c2ff700c5a99009`

**注入后**：
- `git diff --name-only`：`llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（非空）✅
- sha256：`82abeaa0b89a00a2599fbcdacb16d153ee549089331278ba493fd5469fed4584`（变化）✅
- `make build-mc` EXIT=0 ✅
- `ftroot rf1, rf2, 3` → **rc=0**（注入后静默通过）✅
- 证据脚本 → **24 checks, 2 failures, EVIDENCE: FAIL, EXIT=1** ✅（encode_fp_root_n 负例 FAIL + lit FAIL）

**还原后**：
- `git checkout` 还原 → sha256：`90d056785c8105347b40197e74441bb6944cddd5650389324c2ff700c5a99009`（复原）✅
- `git diff --name-only`：空 ✅
- `make build-mc` EXIT=0 ✅
- 证据脚本 → **24 checks, 0 failures, EVIDENCE: PASS, EXIT=0** ✅
- `make check-source-state`：HEAD=a38b3ebec00e clean=True ✅

##### 7. §6.2 披露判定

任务书 §6.2 把 `ftadd rf0, rf2, rf3` 列为「正例（rf0 源合法）」，但该指令的**目的**操作数是第一个（`rf0`），源是第二/三个（`rf2`/`rf3`）。按 §2.1/§6.3，`ftadd` 目的 rf0 必须报 `dst_rf0` 错误。§6.2 与 §6.3/§2.1 自相矛盾。

**engineer 处理**：按规则语义实现，`ftadd rf0, rf2, rf3` 为反例；正例改用 `ftadd rf1, rf0, rf3`（rf0 作源）。

**判定**：engineer 处理**合理**，无需返工。该矛盾属任务书笔误，engineer 按规则语义正确实现并披露。

##### 8. 越界判定

engineer 额外实现了 `mreg_range_overflow` 检查（任务书 §2.4 明确要求，属任务范围）。实现方式：
- 仅检查 FP 多寄存器指令的 RF 组（`isFPMregMnemonic` + `ldm.t/stm.t/ldm.o/stm.o` 的 RF 组）
- M1 RD 侧 `{rd0:rd63}` 不受影响（`CheckRFGroups` 路径跳过非 RF 组）
- 置于 LLVM-029t count-不等检查之前，确保规则名 `mreg_range_overflow` 优先报出

**判定**：**必要、正确、最小**，无越界。

##### 9. 完成区一致性

| 项目 | engineer 声称 | reviewer 核实 | 一致？ |
|---|---|---|---|
| 补丁净增行数 | +165 | `git diff --stat` 167 insertions / 2 deletions → 净 +165 | ✅ |
| 源 1177→1342 | 1342 行 | 补丁 1348 行（含 diff header），源文件 1342 行 | ✅ |
| lit 28→29 | 29/29 | ✅ | ✅ |
| check-patch-tree 68 | 68 | ✅ | ✅ |
| check-interface 80/80 | 80/80 | ✅ | ✅ |
| check-scope PASS | PASS | ✅ | ✅ |
| check-fp-contract PASS | PASS | ✅ | ✅ |
| check-no-residue PASS | PASS | ✅ | ✅ |
| 源 HEAD a38b3ebec00e | a38b3ebec00e | ✅ | ✅ |
| 不变量零改动 | 零改动 | ✅ | ✅ |
| 注入 sha256 | 90d05678… | 90d056785c8105347b40197e74441bb6944cddd5650389324c2ff700c5a99009 | ✅ |

---

**判决：Accepted**

所有验收命令在 reviewer 独立重跑下全部通过（24/24 + lit 29/29 + make check EXIT=0）。独立注入确认脚本可失败（encode_fp_root_n 放宽 → 2 FAIL → EXIT=1）。还原含重建后回绿。约束无违反。§6.2 矛盾处理合理，越界判定无问题。
