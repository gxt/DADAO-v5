# SPEC-105t: `contract-elf §2–§4` 重定位正文（按 ADR-0019）

**模块**：spec
**项目里程碑**：M4
**依赖**：无
**状态**：待验收

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**（自包含；决策已定，本任务只落正文）：
  - `.tao/adr/adr-0019-dadao-relocation-types.md`（**Accepted**，用户 2026-10-05 逐条确认 D1–D8）——本任务**唯一决策来源**（类型/编号/公式/溢出/RELA/ABS48/禁用 relaxation）。
  - `.tao/knowledge/contract-elf.md`：§1（ELF 头字段，`e_flags[7:0]=1` namespace）、§2–§4（当前标题为 `` `Deferred to M2`：… ``，**待改写为规范正文**）、文件头「M1 范围 / `Deferred to M2`」说明、`## 附录 A：来源对照`。
  - `.tao/knowledge/contract-isa.md` §2.3–§2.4（指令格式/字段位置/位宽）、§1.3.2（`rb0` = 当前指令地址）；`contracts/opcodes.yaml`（`imms12`/`imms18`/`imms24`、`rwii` 的 `immu16` + `wyde-position wp0–wp3`）——**仅核对字段**，不重定义。
  - `spec/Process-02-合约编写规范.md`（合约编写/来源标注格式）。
- **输出**：`.tao/knowledge/contract-elf.md` 的 **§2（重定位类型）、§3（重定位溢出策略）、§4（重定位松弛）由 `Deferred to M2` 转为规范正文**，内容严格等于 `ADR-0019` D1–D8：
  - **§2 类型与编号**（`e_flags[7:0]=1` namespace 内独立编号，**不复用** legacy `Dadao.def`）：
    | 编号 | 名 | 场景 | 编码字段 |
    |---|---|---|---|
    | 0 | `R_DADAO_ABS48` | `set.zw`/`or.w`/`andn.w` 序列（≤3 片 wyde） | 3×`immu16`（按 `wyde-position`） |
    | 1 | `R_DADAO_REL26` | `call`/`jump`（iiii） | `imms24`（有效 26 位） |
    | 2 | `R_DADAO_REL20` | `br.n/nn/z/nz/p/np`（riii） | `imms18`（有效 20 位） |
    | 3 | `R_DADAO_REL14` | `br.eq`/`br.ne`（rrii） | `imms12`（有效 14 位） |
    | 4 | `R_DADAO_NUM` | 计数 | — |
    - ELF 记录类型 = **`SHT_RELA`**（`.rela.*`，显式 `r_addend`）；reloc **逐指令**挂载，linker 依指令内 `wyde-position`（`wp`）判定该片对应地址的哪 16 位。
  - **§3 公式**（`S`=符号值、`A`=addend、`P`=重定位处地址；v5 **无 −4**，与 0628 `(val-4)>>2` 不同，因 `rb0` 读出为当前指令地址）：
    - `REL26/REL20/REL14`：`field = (S + A − P) >> 2`（字偏移）。
    - `ABS48`：`value = S + A`（48 位，按 `wyde-position` 分片写入 3×`immu16`）。
    - 溢出策略：越界 ⇒ **link-time error**（不截断、不 wrap）。
  - **§4 松弛**：`ABS48` 最多 **3 片**且**一律发射固定 max 3 片**（禁用 relaxation）；`RELA_PAGE`/`RELA_LO`（`rb0`/数据段相对寻址）**本期不实现、留后**；不做 `ABS32`（地址空间 48 位）。
  - 同步更新：文件头「`Deferred to M2`」清单（移除 §2–§4）与 M1 范围说明；`## 附录 A：来源对照` 中 §2/§3/§4 行的 ADR 指针改为 `ADR-0019 §D1–D8`；每条规范断言句末保留来源标注（`[ADR-0019 §DN]` / `[contract-isa.md §N]`）。
  - **门控对齐**：若 `spec/README.md` 投影表或任何 checker/注释含 `contract-elf §2–§4 = Deferred/缺口` 表述，同步更新；`make check` 全绿。
- **约束**：
  - **只落正文、不重新决策**：`ADR-0019` 已 `Accepted`；**不得**新增/修改任何 relocation 决策。发现与 ADR-0019 表述冲突时**阻断并报告**，不自行改契约。
  - **不改** `ADR-0003`、`ADR-0019`；**不改** `contract-elf` §1/§5/§6（§5/§6 调整归 `SPEC-107t`）；**不改** `contracts/opcodes.yaml`；**不实现** LLVM/LLD/QEMU。
  - `spec/`、`contracts/`、`.tao/knowledge/` 为共享文件，**串行**（`AGENTS.md`「同改共享文件一律串行」）。
  - 临时目录 `/tmp/opencode/SPEC-105t/`；**不提交 git**。

## 验收标准

1. **正文落地**：`grep -n "Deferred to M2" .tao/knowledge/contract-elf.md` 对 **§2–§4 无命中**；§2 含完整 5 行类型表（`ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`/`NUM=4`）与 `SHT_RELA`；§3 含 `S + A − P`、`>> 2`、`ABS48` 公式与 **link-time error**；§4 含「≤3 片 / 一律 max 3 片 / 禁用 relaxation / `RELA_PAGE`+`RELA_LO` 留后 / 不做 ABS32」。
2. **无 −4**：`grep -n "− 4\|- 4\|−4\|-4"` 对 §2–§4 无「相对类公式含 −4」的表述（"无 −4" 的说明本身允许出现）。
3. **来源标注**：§2–§4 每条规范断言句末有 `[ADR-0019 §DN]` 或 `[contract-isa.md §N]`；人工逐条与 `ADR-0019` D1–D8 对照**无矛盾**（完成区给出对照表）。
4. **反例门控**：任务自带可复跑检查脚本（`.work/evidence/SPEC-105t/run.sh`）逐条断言上列文本/编号/公式；对注入反例（改 `REL26` 编号、删「无 −4」、把「link-time error」改成「截断」）**必须 FAIL**，还原后回绿；完成区贴真实输出（`cmd > log 2>&1; rc=$?`，**无 `tee`**）。
5. **门控**：`make check` EXIT=0（含 `check-spec-refs`）；`git status --untracked-files=all` 仅本任务应有改动；未改 `ADR-*`/`contracts/**`/实现。

## 完成区

**测试结果**：通过 5/5；失败原因：无。

| # | 检查 | 命令 | 退出码 | 日志 |
|---|------|------|--------|------|
| 1 | 正文落地（grep 断言） | `bash .work/evidence/SPEC-105t/run.sh --check` | EXIT=0（33 项断言全 PASS） | `.work/log/spec/SPEC-105t-evidence-check.log` |
| 2 | 反例门控（3 项注入） | `bash .work/evidence/SPEC-105t/run.sh` | EXIT=0（注入→FAIL→还原→回绿 ×3） | `.work/log/spec/SPEC-105t-evidence-full.log` |
| 3 | 仓库门控 | `make check` | EXIT=0 | `.work/log/spec/SPEC-105t-check.log` |
| 4 | spec 引用审计 | `make check-spec-refs` | EXIT=0 | `.work/log/spec/SPEC-105t-check-spec-refs.log` |
| 5 | spec 漂移审计 | `make check-spec-drift` | EXIT=0 | `.work/log/spec/SPEC-105t-check-spec-drift.log` |

**修改文件**：
- `.tao/knowledge/contract-elf.md`（**唯一受控改动**，`git diff --stat` = 51 insertions(+), 28 deletions(-)）。
- 非入库证据（`.work/` 已被 gitignore，不计入 `git status`）：`.work/evidence/SPEC-105t/run.sh`、`.work/log/spec/SPEC-105t-*.log`。
- **未改**：`ADR-0003`/`ADR-0019`、`contract-elf §1/§5/§6`（正文未动 §1/§5/§6 段落）、`contracts/**`、LLVM/LLD/QEMU 实现。

**验收结果**（真实输出逐条粘贴，均用 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

**验收 1 — 正文落地 / `Deferred to M2` 无命中**：
```
$ grep -n "Deferred to M2" .tao/knowledge/contract-elf.md
（无输出）
grep EXIT=1
```
§2 类型表（§2.2）5 行编号 `0 ABS48 / 1 REL26 / 2 REL20 / 3 REL14 / 4 NUM` 齐全；§2.1 含 `SHT_RELA`（显式 `r_addend`）；§2.3 逐指令挂载 + `wyde-position` 分片。证据脚本对应断言 `type_row_*`/`sht_rela`/`r_addend` 全 PASS。

§3 含 `(S + A − P) >> 2`（相对类字偏移）、`value = S + A`（`ABS48`，3×`immu16`）、`link-time error`（不截断/不 wrap）。断言 `rel_formula`/`abs48_formula`/`link_time_error` 全 PASS。

§4 含 `≤3 片` + `一律发射固定 max 3 片` + `禁用 relaxation` + `RELA_PAGE`/`RELA_LO` 本期不实现留后 + `不做 ABS32`。断言 `abs48_max3_pieces`/`disable_relaxation`/`rela_page_lo_deferred`/`no_abs32` 全 PASS。

**验收 2 — 无 −4**：
```
$ grep -n "− 4\|- 4\|−4\|-4" .tao/knowledge/contract-elf.md
99:相对类公式为 `(S + A − P) >> 2`，即**字偏移**（`P` 为重定位处地址本身）。**v5 无 `− 4`**：不引入 `PC+4` 修正；这与 0628 的 `(val-4)>>2` 不同——...
181:| §3 | 重定位公式与溢出策略（无 −4、link-time error） | `ADR-0019` §D3、§D6 |
grep EXIT=0
```
第 99 行是「**无 `− 4`**」说明 + 0628 对照（本任务接口规范第 28 行明确要求）；第 181 行是附录「无 −4」摘要。**无任何相对类公式含 −4**：断言 `no_minus4_in_rel_formula`（正则 `\(S \+ A − P[^)]*[−-]\s*4` 不命中）PASS，且 `has_no_minus4_note`（「无 −4」说明存在）PASS。注入 B（删除「无 `− 4`」）→ `has_no_minus4_note` FAIL。

**验收 3 — 来源标注**：§2–§4 每条规范断言句末标注齐备（断言 `src_adr0019_D1`…`D8` 8/8 PASS；`src_contract_isa_1_3_2`/`src_contract_isa_2_4` PASS）。与 `ADR-0019` D1–D8 逐条对照（下表，**无矛盾**）：

| ADR-0019 | 决策 | `contract-elf.md` 落点 | 一致性 |
|----------|------|------------------------|--------|
| D1 | RELA（`SHT_RELA`，显式 `r_addend`） | §2.1 | ✅ |
| D2 | 类型集 `ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`/`NUM=4`；`e_flags[7:0]=1` namespace、不复用 legacy | §2.2 表 | ✅（场景列含 `andn.w`，为任务接口规范所列地址构造序列；ADR D2 列 `set.zw`/`or.w`、ADR Context 亦含 `andn.w`，并集无矛盾） |
| D3 | `REL26/20/14 = (S + A − P) >> 2`；`ABS48 = S + A`；v5 无 −4 | §3.1 | ✅ |
| D4 | `ABS48` ≤3 片 + 一律发射固定 max 3 片 | §4 | ✅ |
| D5 | 逐指令挂 reloc，linker 依 `wyde-position` 分片 | §2.3 | ✅ |
| D6 | 溢出 ⇒ link-time error（不截断/不 wrap） | §3.2 | ✅ |
| D7 | 禁用 relaxation；`RELA_PAGE`/`RELA_LO` 留后 | §4 | ✅ |
| D8 | 不做 `ABS32` | §4 | ✅ |

**验收 4 — 反例门控**（`.work/evidence/SPEC-105t/run.sh`，真实输出见 `.work/log/spec/SPEC-105t-evidence-full.log`）：
- 注入 A（`R_DADAO_REL26` 编号 `1→9`）：md5 变化确认非空注入 → `[FAIL] type_row_1_REL26` → `INJECT(A) EXIT=1`；还原 md5 回基线 → `RESTORE(A) EXIT=0`。
- 注入 B（删「无 `− 4`」）：→ `[FAIL] has_no_minus4_note` → `INJECT(B) EXIT=1`；还原回绿 `EXIT=0`。
- 注入 C（`link-time error` → `截断`）：→ `[FAIL] link_time_error` → `INJECT(C) EXIT=1`；还原回绿 `EXIT=0`。
- 收尾 `final md5 = 3ae9fd23b9d8831dce90522cbb897ba7` = 基线；脚本结尾 `exit 0`，未使用 `tee`。

**验收 5 — 门控**：
```
$ make check   → EXIT=0（末尾 `repository checks: PASS`，lit 34/34）
$ make check-spec-refs → EXIT=0（`Check 2 — 无引用规范断言 命中数: 0`；`结果: PASS (0 violations)`）
$ make check-spec-drift → EXIT=0（`[PASS] contract-elf.md` / `ADR-sourced: adr-0003-object-abi.md (状态: Accepted)` / `ADR-sourced: adr-0019-dadao-relocation-types.md (状态: Accepted)`）
```
`git status --porcelain --untracked-files=all` → 仅 `.tao/knowledge/contract-elf.md`。未改 `ADR-*`/`contracts/**`/实现。

**投影/checker 同步核验**（任务要求）：
```
$ grep -n "contract-elf\|§2–§4" spec/README.md      → 无输出（EXIT=1）
$ grep -rn "contract-elf.*§2\|§2–§4.*Deferred\|contract-elf.*Deferred" tools/ → 无输出（EXIT=1）
$ grep -n "contract-elf" spec/Process-02-合约编写规范.md → 第 12 行：`| contract-elf.md | ELF 格式：machine ID、重定位类型、endian | 现行 |`（无 Deferred/缺口 表述）
```
结论：`spec/README.md` 投影表、`tools/**` checker/注释均无 `contract-elf §2–§4 = Deferred/缺口` 表述，**无需同步**。

**新发现/坑**：
1. **§6.3 残留陈旧表述**（不改，归 `SPEC-107t`）：§6.3 第 169 行「M2 若需要多 object/重定位，再决策 linker 与 §2/§3/§4」、第 171 行「D2/D3/D4 不得在 M1 实现」在 §2–§4 已冻结（M4/ADR-0019）后语义过期。因任务硬约束「不改 §5/§6」，本任务未动；**建议 `SPEC-107t` 同步**。
2. **`check_spec_drift` 的 ADR 引用正则要求完整文件名**（`adr-(\d{4})-[\w-]+\.md`）：`[ADR-0019 §DN]` 简写**不被**该检查识别。为使 ADR-0019 进入漂移审计（避免「新增 ADR 却未被审计」的洞），已在文件头「来源」补写完整文件名 `.tao/adr/adr-0019-dadao-relocation-types.md`，`check-spec-drift` 因此对 `contract-elf.md` 同时校验 adr-0003 与 adr-0019 的 Accepted 状态（真实输出见上）。
3. **`check-spec-refs` 的 Check2**：新增 §2–§4 断言行均带 `[ADR-0019 §DN]` 决策标记（脚本将同行 `ADR-\d{4}` 视作决策排除）或 `[contract-isa.md §N]` 引用，故 Check2 命中保持 0（无回归）。

**遗留问题**：
- 见「新发现/坑 1」：`contract-elf §6.3` 两处陈旧表述（§6 范围，归 `SPEC-107t`），本任务按硬约束未改。除此之外无未完成项。
- 无阻塞、无失败命令。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`contract-elf.md` 全部改动（`git diff` 逐 hunk）+ `.work/evidence/SPEC-105t/run.sh` 逐行。审查方式：自主逐行审查（`subagent_depth=1`，无嵌套）。

**逐行审查结论**：
- **§2.1–§2.3**：`SHT_RELA`/显式 `r_addend`（D1）、编号 0–4 与场景/字段映射（D2）、逐指令挂载 + `wyde-position`（D5）均与 ADR-0019 逐字一致；表格编号递增无缺号、无重号。
- **§3.1–§3.2**：相对类公式 `(S + A − P) >> 2` 与 `ABS48 = S + A`（D3）正确；`−` 统一为 U+2212；溢出 `link-time error`、不截断/不 wrap（D6）正确。
- **§4**：`≤3 片` + 一律 `max 3 片`（D4）、禁用 relaxation（D7）、`RELA_PAGE`/`RELA_LO` 留后（D7）、不做 `ABS32`（D8）齐备。
- **门控/引用**：`git diff` 仅覆盖头/§2–§4/附录；§1/§5/§6 正文零改动；`make check`/`check-spec-refs`/`check-spec-drift` 三门控 EXIT=0。
- **证据脚本**：`set -uo pipefail`、逐项打印、失败非零、结尾无 `tee`；注入就地在真实产物上执行并逐轮 md5 对账（注入→非基线、还原→回基线、final=基线），可证「非空注入」与「已还原」。

**finding 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 文件头「说明」原句「本合约由 ADR-0003 归一化投影而来」在 §2–§4 转 ADR-0019 后不准确 | ✅已修 | 改为「本合约（§1/§5/§6）由 ADR-0003…，§2–§4 由 ADR-0019…」 | 证据脚本基线回绿（`final md5=3ae9fd23…`，EXIT=0）；`make check`/`check-spec-refs`/`check-spec-drift` EXIT=0 |
| F2 §3 含 `(val-4)>>2` 0628 对照串，使 acceptance #2 grep 命中 line 99 | ❌不修 | — | 该串是任务接口规范第 28 行**明确要求**的 0628 对照说明，非 v5 公式；断言 `no_minus4_in_rel_formula`（正则 `\(S \+ A − P[^)]*[−-]\s*4` 不命中）证明无相对类公式含 −4。允许项 |
| F3 §2.2 `ABS48` 场景列含 `andn.w`，ADR-0019 D2 表仅列 `set.zw`/`or.w` | ❌不修 | — | 任务接口规范 §2 表明确列 `set.zw`/`or.w`/`andn.w`；ADR-0019 §Context 亦载「地址构造指令为 `set.zw`/`or.w`/`andn.w`」，为并集、无矛盾 |
| F4 `contract-elf §6.3` 两处表述（「M2…再决策 linker 与 §2/§3/§4」「D2/D3/D4 不得在 M1 实现」）在 §2–§4 冻结后陈旧 | ⏸延后 | — | 任务硬约束「不改 §5/§6」；属 §6 范围，归 `SPEC-107t` 同步（已记入完成区遗留） |

**判决**：本轮 4 项 finding 中 1 项已修、3 项为「允许项/范围外」并附证据；**无落在本任务范围内且未修的 finding**。任务状态 → 待验收。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（独立验证）
**审查日期**：2026-10-06

---

##### 一、证据脚本审阅

**脚本**：`.work/evidence/SPEC-105t/run.sh`（242 行）

审阅结论：**合格**。
- `set -uo pipefail` ✓
- 逐项打印 `[PASS]/[FAIL]` + 期望/实际 ✓
- 任一检查失败即非零退出（`sys.exit(fails)` + 外层 `$?` 检查）✓
- 注入函数含 `assert t2 != t`（空注入检测）✓
- 每轮注入后 md5 对账（注入→非基线、还原→回基线）✓
- 结尾 `exit 0`/`exit 1`，**未使用 `tee`** ✓
- 3 项注入均有独立 FAIL 路径：A→`type_row_1_REL26`、B→`has_no_minus4_note`、C→`link_time_error`，**无恒真/两支同结果** ✓
- `--check` 模式可单独跑基线 ✓

---

##### 二、重跑记录

**命令**：`bash .work/evidence/SPEC-105t/run.sh > log 2>&1; rc=$?; echo "EXIT=$rc"`

**真实输出**（完整，未截断）：
```
=== SPEC-105t 证据脚本：/mnt/tao/DADAO-v5/.tao/knowledge/contract-elf.md ===
--- [阶段 0] 备份基线 ---
baseline md5 = 3ae9fd23b9d8831dce90522cbb897ba7
--- [阶段 1] 基线检查（期望全 PASS / exit 0）---
[PASS] no_deferred_in_region  (§2–§4 不应含 'Deferred to M2')
[PASS] no_deferred_in_file  (全文不应含 'Deferred to M2')
[PASS] type_row_0_ABS48  (期望 '| 0 | `R_DADAO_ABS48`')
[PASS] type_row_1_REL26  (期望 '| 1 | `R_DADAO_REL26`')
[PASS] type_row_2_REL20  (期望 '| 2 | `R_DADAO_REL20`')
[PASS] type_row_3_REL14  (期望 '| 3 | `R_DADAO_REL14`')
[PASS] type_row_4_NUM  (期望 '| 4 | `R_DADAO_NUM`')
[PASS] sht_rela  (期望 'SHT_RELA')
[PASS] r_addend  (期望显式 'r_addend')
[PASS] rel_formula  (期望 '(S + A − P) >> 2')
[PASS] abs48_formula  (期望 'value = S + A' + 'immu16')
[PASS] no_minus4_in_rel_formula  (相对类公式不得含 −4)
[PASS] has_no_minus4_note  (期望含「无 −4」说明)
[PASS] link_time_error  (期望 'link-time error')
[PASS] abs48_max3_pieces  (期望 'max 3 片' + '≤3 片')
[PASS] disable_relaxation  (期望 '禁用 relaxation')
[PASS] rela_page_lo_deferred  (期望 'RELA_PAGE' + 'RELA_LO')
[PASS] no_abs32  (期望 '不做 `ABS32`')
[PASS] src_adr0019_D1  (期望 '[ADR-0019 §D1]')
[PASS] src_adr0019_D2  (期望 '[ADR-0019 §D2]')
[PASS] src_adr0019_D3  (期望 '[ADR-0019 §D3]')
[PASS] src_adr0019_D4  (期望 '[ADR-0019 §D4]')
[PASS] src_adr0019_D5  (期望 '[ADR-0019 §D5]')
[PASS] src_adr0019_D6  (期望 '[ADR-0019 §D6]')
[PASS] src_adr0019_D7  (期望 '[ADR-0019 §D7]')
[PASS] src_adr0019_D8  (期望 '[ADR-0019 §D8]')
[PASS] src_contract_isa_1_3_2  (期望 '[contract-isa.md §1.3.2]')
[PASS] src_contract_isa_2_4  (期望 '[contract-isa.md §2.4]')
[PASS] header_no_deferred  (文件头不应含 'Deferred to M2')
[PASS] appendix_§2_adr0019  (附录 §2 行应指向 ADR-0019)
[PASS] appendix_§3_adr0019  (附录 §3 行应指向 ADR-0019)
[PASS] appendix_§4_adr0019  (附录 §4 行应指向 ADR-0019)
── 检查结果: 失败 0 项 ──
BASELINE EXIT=0
--- [注入] A: REL26 编号 1→9 ---
[OK] A: REL26 编号 1→9: 注入生效（md5 3ae9fd23b9d8831dce90522cbb897ba7 → fee010dd00a6049c0270a7dea5bbad9b）
[FAIL] type_row_1_REL26  (期望 '| 1 | `R_DADAO_REL26`')
INJECT(A: REL26 编号 1→9) EXIT=1 (期望非 0)
[OK] A: REL26 编号 1→9: 注入后检查 FAIL（反例被捕获）
[OK] A: REL26 编号 1→9: 已还原（md5 回基线）
RESTORE(A: REL26 编号 1→9) EXIT=0 (期望 0)
[OK] A: REL26 编号 1→9: 还原后回绿
--- [注入] B: 删「无 −4」 ---
[OK] B: 删「无 −4」: 注入生效（md5 3ae9fd23b9d8831dce90522cbb897ba7 → 5b797c788e72a7cb6ba344526a9d7801）
[FAIL] has_no_minus4_note  (期望含「无 −4」说明)
INJECT(B: 删「无 −4」) EXIT=1 (期望非 0)
[OK] B: 删「无 −4」: 注入后检查 FAIL（反例被捕获）
[OK] B: 删「无 −4」: 已还原（md5 回基线）
RESTORE(B: 删「无 −4」) EXIT=0 (期望 0)
[OK] B: 删「无 −4」: 还原后回绿
--- [注入] C: link-time error→截断 ---
[OK] C: link-time error→截断: 注入生效（md5 3ae9fd23b9d8831dce90522cbb897ba7 → 1c4e7d343a300cdc54a41e47bde59a87）
[FAIL] link_time_error  (期望 'link-time error')
INJECT(C: link-time error→截断) EXIT=1 (期望非 0)
[OK] C: link-time error→截断: 注入后检查 FAIL（反例被捕获）
[OK] C: link-time error→截断: 已还原（md5 回基线）
RESTORE(C: link-time error→截断) EXIT=0 (期望 0)
[OK] C: link-time error→截断: 还原后回绿
--- [阶段 3] 收尾：确认产物已还原 ---
final md5 = 3ae9fd23b9d8831dce90522cbb897ba7
=== 结果: PASS（基线全绿 + 3 项注入均 FAIL 并还原回绿）===
EXIT=0
```

**结论**：33 项基线断言全 PASS；3 项注入（A/B/C）均正确 FAIL 并还原回绿；final md5 = 基线。**与完成区一致**。

---

##### 三、门控重跑

| 命令 | 退出码 | 结论 |
|------|--------|------|
| `make check` | EXIT=0 | ✅ |
| `make check-spec-refs` | EXIT=0 | ✅ |
| `make check-spec-drift` | EXIT=0 | ✅ |

`git status --porcelain --untracked-files=all`：
```
 M .tao/knowledge/contract-elf.md
 M ".tao/tasks/spec/SPEC-105t-contract-elf重定位正文.md"
```
仅本任务应有改动（contract-elf.md + 任务文件），无残留。

`git diff --name-only`：仅 `.tao/knowledge/contract-elf.md`。未改 `ADR-*` / `contracts/**` / 实现。

---

##### 四、独立注入（与 engineer 的 A/B/C 不同）

**注入方式**：`sed -i 's/SHT_RELA/SHT_REL/g'`（将 §2.1 的 `SHT_RELA` 改为 `SHT_REL`）

**注入后检查**：
```
INJECT EXIT=1
[FAIL] sht_rela  (期望 'SHT_RELA')
── 检查结果: 失败 1 项 ──
```
✅ 断言正确 FAIL，非空注入（`git diff` 确认改动非空）。

**还原后检查**：
```
RESTORE EXIT=0
── 检查结果: 失败 0 项 ──
```
✅ 还原后回绿。

---

##### 五、独立 D1–D8 对照（不采信完成区，自建）

| ADR-0019 | 决策要求 | contract-elf.md 落点 | 一致性 | reviewer 核验方式 |
|----------|---------|---------------------|--------|------------------|
| D1 | RELA（`SHT_RELA`，显式 `r_addend`） | §2.1 L66 | ✅ | 逐字比对：`SHT_RELA` ✓、`r_addend` 显式 ✓、否决 `SHT_REL` ✓ |
| D2 | 类型集 `ABS48=0`/`REL26=1`/`REL20=2`/`REL14=3`/`NUM=4`；`e_flags[7:0]=1` namespace、不复用 legacy | §2.2 L72–78 表 | ✅ | 逐行比对：编号 0–4 ✓、名称 ✓、场景 ✓（含 `andn.w`，ADR-0019 Context 亦含）、编码字段 ✓ |
| D3 | `REL26/20/14 = (S + A − P) >> 2`；`ABS48 = S + A`；v5 无 −4 | §3.1 L92–99 | ✅ | 公式逐字比对 ✓；`−` 为 U+2212 ✓；「无 −4」说明 ✓（L99）；`rb0` = 当前指令地址引用 `[contract-isa.md §1.3.2]` ✓ |
| D4 | `ABS48` ≤3 片 + 一律发射固定 max 3 片 | §4 L109 | ✅ | `≤3 片` ✓、`一律发射固定 max 3 片` ✓ |
| D5 | 逐指令挂 reloc + `wyde-position` 分片 | §2.3 L84 | ✅ | `逐指令` ✓、`wyde-position` ✓、`hb[5:4]` ✓、`[contract-isa.md §2.4]` ✓ |
| D6 | 溢出 ⇒ link-time error（不截断/不 wrap） | §3.2 L103 | ✅ | `link-time error` ✓、`不截断、不 wrap` ✓ |
| D7 | 禁用 relaxation；`RELA_PAGE`/`RELA_LO` 留后 | §4 L109–110 | ✅ | `禁用 relaxation` ✓、`RELA_PAGE`/`RELA_LO` ✓、`本期不实现、留后` ✓ |
| D8 | 不做 `ABS32` | §4 L111 | ✅ | `不做 ABS32` ✓、`地址空间为 48 位` 理由 ✓ |

**来源标注**：§2–§4 每条规范断言句末均有 `[ADR-0019 §DN]`（D1–D8 全覆盖）或 `[contract-isa.md §N]`（§1.3.2、§2.4）。证据脚本断言 `src_adr0019_D1`…`D8`（8/8）+ `src_contract_isa_1_3_2` + `src_contract_isa_2_4` 全 PASS。

**`Deferred to M2` 清除**：`grep "Deferred to M2" contract-elf.md` 无输出（EXIT=1）。文件头 L11 已改为「M4 范围（§2–§4）」。

**相对类公式无 −4**：`grep -n "− 4\|- 4\|−4\|-4"` 命中 L99 和 L181，均为「无 −4」说明文本，非公式本身。正则 `\(S \+ A − P[^)]*[−-]\s*4` 不命中 → 断言 PASS。

**附录 A**：§2/§3/§4 行均指向 `ADR-0019`（L180–182）。断言 `appendix_§2/§3/§4_adr0019` 全 PASS。

**`git diff` 范围**：3 个 hunk——文件头（L2–17）、§2–§4（L59–90+）、附录 A（L153–174+）。§1/§5/§6 正文零改动。

---

##### 六、F4 判定：§6.3 两处陈旧表述

§6.3 L169：「M2 若需要多 object/重定位，再决策 linker 与 §2/§3/§4」
§6.3 L171：「D2/D3/D4 不得在 M1 实现」

**判定**：
- **如实登记**：✅ engineer 在完成区「新发现/坑 1」和「遗留问题」中明确登记，标注归 `SPEC-107t`。
- **非阻塞**：✅ 任务硬约束「不改 §5/§6」，§6.3 属 §6 范围，本任务不应动。两处表述在 §2–§4 已冻结后语义过期，但不影响 §2–§4 正文的正确性，属 §6 的独立维护范畴。
- **处置合理**：建议 `SPEC-107t` 同步处理，符合任务分解原则。

---

##### 七、判决

**Accepted**

**依据**：
1. 证据脚本审阅合格（FAIL 路径可达、注入非空可还原、无 tee）
2. 重跑 EXIT=0，33 项基线全 PASS，3 项注入均正确 FAIL 并还原回绿
3. 独立注入（`SHT_RELA`→`SHT_REL`）验证断言可失败，还原后回绿
4. D1–D8 逐条独立对照，§2/§3/§4 文本与 ADR-0019 决策**一致、无矛盾**
5. 门控 `make check` / `check-spec-refs` / `check-spec-drift` 全 EXIT=0
6. `git status` 仅本任务改动，未碰 ADR/contracts/实现
7. F4（§6.3 陈旧表述）如实登记、非阻塞、归 SPEC-107t 合理
