# SPEC-081t: ADR-0012 D8.2 修订落地（`cmp.uo-rb` 取整 64 位）

**模块**：spec（`spec/` + `contracts/` 无改）+ qemu（补丁）+ testcases（向量）
**项目里程碑**：M2
**依赖**：`ADR-0012 D8.2`（**2026-10-02 就地修订**，`b2510ea`）
**状态**：已验证

## 背景

`D8.2` 已由「`cmp.uo-rb` = 低 48 位比较」**就地修订为「整 64 位」**（理由：RB 高 16 是合法内容 D8.1；判断/比较非「地址使用」D8.7；高 16 非 0 应**暴露**而非隐藏）。本任务把该修订落到实现/文档/向量（即**撤销** `SPEC-079t`/`QEMU-031t` 中 `cmp.uo-rb` 的 48 位部分）。

## 改动清单

1. **QEMU**：`components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch` 的 `trans_cmp_uo_orrr_rb` **删除**比较前的 `tcg_gen_andi_i64(..., 0x0000FFFFFFFFFFFF)`（恢复整 64 位无符号比较）；**重建 QEMU**。
2. **spec**：`spec/SimRISC-05-64位地址运算.md` L58：「对两个操作数的**低 48 位**进行无符号比较」⇒「对两个操作数的**整 64 位**进行无符号比较（`bits[63:48]` 参与）」。
3. **contract**：`.tao/knowledge/contract-isa.md`
   - L700：`cmp.uo rdhb, rbhc, rbhd` ⇒「**整 64 位**无符号比较…」；
   - L702：删/改「比较限于低 48 位、bits[63:48] 不参与」⇒「比较按整 64 位；仅**作地址使用时**取低 48（见 D8.7）」。
4. **spec（br）**：`spec/SimRISC-06-控制流.md` 明确 `br.z-rb`/`br.nz-rb` 条件按**整 64 位**判零（与 `-rd` 一致；`-rb`/`-rd` 区别仅在寄存器组）。
5. **向量**：`tests/vectors/isa/reg-compare.yaml` 中 `QEMU-031t` 新增的 3 条「48-bit D8.2 boundary」用例改为**64 位语义**（高 16 参与比较）并在 `notes` 注明；期望值**独立派生自 `ADR-0012 D8.2`**（不得从实现反推 ✗）。

## 范围外 ✗
- 不改 `components/**/patches/**` 的其它文件；不改 D8.3 相关（已定稿）；
- 不改 `QEMU-031t` 的 `rb0`/控制流部分（保持）；
- 不改历史文件（`spec/SimRISC-0.5.3/*`、`docs/testcases-009t-audit.md` 等快照文件）。
- ~~不改 `SimRISC-00`~~（**第 2 轮返工作废**：reviewer 指出 `ADR-0012 D8.6` 同步面含 `SimRISC-00`；主会话裁定纳入）

## 验收标准（须真实可失败）

1. **QEMU 64 位**：`cmp.uo-rb` 对 `rbhc`/`rbhd` 的**整 64 位**做无符号比较；构造 `rbhc=0x0001_0000_0000_0001` vs `rbhd=0x2` ⇒ 64 位下 `+1`（**≠** 48 位下的 −1）✓；用 `-d cpu`/探针或向量取真实结果。
2. **向量有鉴别力**（你亲自注入 + 复原）：**加回** 48 掩码 ⇒ 相应向量 **FAIL**；复原 ⇒ PASS（贴真实退出码）。期望值与 `D8.2` 一致（64 位）。
3. **spec/contract 一致**：`SimRISC-05`/`contract-isa` 无「低 48 位比较」残留（`grep` 证据）；`SimRISC-06` 明示 `br.*-rb` 64 位。
4. **patch 合规**：QEMU 补丁经**裸 `git diff`** 重导出（`INFRA-023t` §6.1）；`check-patch-tree` 断言 ①–⑥全过（含**断言⑥**：应用产物 == `.work/source`）✓。
5. **无回归**：`make check` **EXIT=0**；`check-qemu-semantics`（含更新的 `reg-compare`）；lit 25/25。
6. **未越界**：`git diff --name-only` ⊆ `components/qemu/patches/.../trans_compare.c.inc.patch` + `spec/SimRISC-05`/`06` + `contract-isa.md` + `tests/vectors/isa/reg-compare.yaml` + 任务书。
7. 构建 `JOBS=8`、一次一个、重建前报耗时；退出码 `cmd >log 2>&1; rc=$?`（禁管道吞码 ✗）；命令失败 ⇒ 停下报告。

## 完成区
**测试结果**：`make check` EXIT=0；`check-qemu-semantics` EXIT=0；`check-lit` EXIT=0；`check-patch-tree` EXIT=0（67 patches OK）

**修改文件**：
1. `components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch` — 删除 `trans_cmp_uo_orrr_rb` 的两行 `tcg_gen_andi_i64(..., 0x0000FFFFFFFFFFFFULL)` + 更新注释为 64-bit
2. `spec/SimRISC-05-64位地址运算.md` L58 — 「低 48 位」→「整 64 位（`bits[63:48]` 参与）」
3. `.tao/knowledge/contract-isa.md` L700 — 「低 48 位」→「整 64 位」；L702 — 「比较限于低 48 位…不参与」→「比较按整 64 位；仅作地址使用时取低 48（见 D8.7）」
4. `spec/SimRISC-06-控制流.md` L74 — 「根据rbHA是否为0进行判断」→「按**整 64 位**判零（与 `-rd` 变体一致；`-rb`/`-rd` 区别仅在寄存器组）」
5. `tests/vectors/isa/reg-compare.yaml` — 3 条 D8.2 boundary 向量改为 64 位语义；L132 `bits=48 (D8.2)` → `bits=64 (D8.2 revised)`
6. `spec/SimRISC-00-指令系统设计.md` L74 — 「**低 48 位**无符号比较…bits[63:48] 不影响」→「**整 64 位**无符号比较（`bits[63:48]` **参与**）」（**第 2 轮返工新增**）

**`cmp.uo-rb` 64 位证据（含 48 位对照）**：
- 向量 `[8]`：`rb2=0x0001_0000_0000_0001` vs `rb3=0x0002` → 64 位：`0x0001…0001 > 0x0002` → result=**+1**（48 位下：`0x0001 < 0x0002` → −1）
- 向量 `[9]`：`rb2=0x0001_0000_0000_0001` vs `rb3=0x0001` → 64 位：`0x0001…0001 > 0x0001` → result=**+1**（48 位下：`0x0001 == 0x0001` → 0）
- 向量 `[10]`：`rb2=0x0001_0000_0000_0000` vs `rb3=0x0000_FFFF_FFFF_FFFF` → 64 位：`0x0001… > 0x0000_FFFF…` → result=**+1**（48 位下：`0x0000 < 0xFFFF_FFFF_FFFF` → −1）

**向量注入 FAIL + 复原**：
- **注入**：在 `.work/source/qemu` 的 `trans_cmp_uo_orrr_rb` 加回两行 `tcg_gen_andi_i64(..., 0x0000FFFFFFFFFFFFULL)` → 重建 → `check-qemu-semantics` EXIT=2（`reg-compare.yaml[8]`/`[9]`/`[10]` FAIL，code 0x01）
- **复原**：删除注入行 → 重建 → `check-qemu-semantics` EXIT=0
- **注入有效性**：`git diff c3d48b7 -- trans_compare.c.inc | grep -c "INJECT"` = 1（注入行含 `INJECT` 注释）

**spec/contract 残留 grep**：
```
$ grep -rn "低 48 位.*比较\|低48位.*比较\|比较.*低 48\|48 位.*cmp\|cmp.*48 位\|bits=48" spec/ .tao/knowledge/contract-isa.md tests/vectors/
EXIT=0 (仅 contract-isa.md:702 为新措辞「比较按整 64 位…仅作地址使用时取低 48」)

$ grep -rn "bits=48" tests/vectors/
EXIT=1 (无匹配)
```
其余 "低 48 位" 引用均为地址使用语境（D8.3/D8.7），非比较，正确不改：
- `SimRISC-00` L64/73/75/76/80：RB 地址相关
- `SimRISC-05` L34：add.so-rb 地址计算
- `SimRISC-06` L42/55/70/93/101/116/124：跳转目标取低 48 位
- `contract-isa.md` L125/684/712/714/727/764/776：地址使用相关
- `spec/SimRISC-0.5.3/*`、`docs/testcases-009t-audit.md`：历史文件，不改

**`check-patch-tree` / `make check` 真实退出码**：
```
$ python3 tools/infra/check_patch_tree.py  →  EXIT=0, 2 component(s), 67 patches OK
$ make check  →  EXIT=0
$ make check-qemu-semantics  →  EXIT=0
$ make check-lit  →  EXIT=0
```

**`git diff --name-only`**：
```
.tao/knowledge/contract-isa.md
components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch
spec/SimRISC-00-指令系统设计.md
spec/SimRISC-05-64位地址运算.md
spec/SimRISC-06-控制流.md
tests/vectors/isa/reg-compare.yaml
```
6 文件，全部在任务书清单内（含第 2 轮返工新增的 SimRISC-00），无越界。

**新发现/坑**：
- QEMU 补丁的 `trans_compare.c.inc.patch` 是 `new file mode`（从 `/dev/null` 创建），因此 `git diff` 导出的是完整文件内容而非增量 diff。`check-patch-tree` 断言⑥ 正确处理了这种情况。
- `trans_cmp_ut_orrr_rd` 和 `trans_cmp_uw_orrr_rd` 中也有 `andi_i64(..., 0xFFFF/0xFFFFFFFF)` 用于 32/16 位截断，注入验证时 grep 需区分 `cmp.uo_orrr_rb` 和其他函数。
- **第 2 轮教训**：`ADR-0012 D8.6` 明确列出同步面含 `SimRISC-00`；任务书「范围外：不改 SimRISC-00」与 ADR 真源冲突。`SimRISC-00` 的 RB 高 16 位行为表（L68-76）是各指令的汇总视图，必须与各 spec 一致。类似地，`QEMU-031t` 引入向量时的 `bits=48 (D8.2)` 注释也需随 D8.2 修订一并清理（「修一类」原则）。
- `docs/testcases-009t-audit.md:102` 含旧口径「bits[63:48] 不影响」，属历史审计快照，不改（第 2 轮 reviewer F3 确认）。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：5 个改动文件逐行审查

| # | 文件 | 审查项 | 判决 |
|---|------|--------|------|
| 1 | `trans_compare.c.inc.patch` | `trans_cmp_uo_orrr_rb` 无 `andi_i64` 掩码；注释更新为 "64-bit" + "D8.2 (revised)"；`load_rb` → `gen_cmp_three_way(result, rbhc, rbhd, false)` → `store_rd` 流程正确 | ✅ |
| 2 | `SimRISC-05` L58 | 「整 64 位」+「bits[63:48] 参与」措辞准确 | ✅ |
| 3 | `contract-isa.md` L700 | 「整 64 位无符号比较」与 D8.2 一致 | ✅ |
| 4 | `contract-isa.md` L702 | 「比较按整 64 位；仅作地址使用时取低 48（见 D8.7）」与 D8.2/D8.7 一致 | ✅ |
| 5 | `SimRISC-06` L74 | 「按整 64 位判零（与 `-rd` 变体一致；`-rb`/`-rd` 区别仅在寄存器组）」准确 | ✅ |
| 6 | `reg-compare.yaml` 向量 3 条 | 期望值独立派生：rb2 > rb3 → +1（64 位），与 48 位下结果不同（-1/0），鉴别力充分 | ✅ |
| 7 | 注入/复原 | 加回掩码→EXIT=2（3 FAIL）；复原→EXIT=0；注入含 `INJECT` 注释可确认 | ✅ |
| 8 | 范围 | `git diff --name-only` 仅 5 文件，全部在任务书清单内 | ✅ |

**逻辑正确性**：
- `gen_cmp_three_way(result, rbhc, rbhd, false)` 第三参数 `false` = unsigned，正确
- ILLI 检查 `a->hb == 0` 保持不变，正确
- 向量期望值：`0x0001_0000_0000_0001` vs `0x0000_0000_0000_0002` → 64 位无符号：`0x0001_0000_0000_0001` > `0x0000_0000_0000_0002` → result=+1 ✓
- 向量期望值：`0x0001_0000_0000_0001` vs `0x0000_0000_0000_0001` → 64 位无符号：`0x0001_0000_0000_0001` > `0x0000_0000_0000_0001` → result=+1 ✓
- 向量期望值：`0x0001_0000_0000_0000` vs `0x0000_FFFF_FFFF_FFFF` → 64 位无符号：`0x0001_0000_0000_0000` > `0x0000_FFFF_FFFF_FFFF` → result=+1 ✓

**无遗留 finding**。所有验收标准已满足。
#### 第 1 轮 reviewer 验收

**审查范围**：5 个改动文件 + `ADR-0012 D8.2/D8.6/D8.7`（真源）+ `SimRISC-00`（D8.6 同步面）；独立重跑全部验收命令、亲自注入反例并复原、原始寄存器 dump 取真实值、重新导出补丁比对。
证据目录 `/tmp/opencode/SPEC-081t-r1/`（日志 + dump）。**未采信完成区**。

##### 1. 重跑记录（我自己的输出/退出码）

**(a) `cmp.uo-rb` 64 位 —— 原始寄存器 dump（独立 oracle）**

`--dump`（QMP `pmemsave`）取 `DUMP_BASE+0x008`（rd1，**大端**）：
```
$ python3 ... --case 8 --dump   →  rd1 = 0x0000000000000001 (signed=+1)
$ python3 ... --case 9 --dump   →  rd1 = 0x0000000000000001 (signed=+1)
$ python3 ... --case 10 --dump  →  rd1 = 0x0000000000000001 (signed=+1)
```
对照：48 位下应分别为 `−1`/`0`/`−1`。**实测一律 `+1` ⇒ 整 64 位比较** ✓。
（说明：dump 为大端存储；初读小端会误得 `0x0100000000000000`，已用 `>Q` 修正。）

**(b) 向量鉴别力（亲自注入 + 重建 + 复原 + 重建）**
```
注入：.work/source/qemu/.../trans_compare.c.inc 加回两行 andi_i64(0x0000FFFFFFFFFFFF)
      git diff c3d48b7 -- <path> 非空，INJECT 计数 = 1（注入有效）
$ make build-qemu JOBS=8            → EXIT=0（6.3s，[3/3] Linking）
$ ... --case 8  → Exit code 0x01, EXIT=1   (FAIL)
$ ... --case 9  → Exit code 0x01, EXIT=1   (FAIL)
$ ... --case 10 → Exit code 0x01, EXIT=1   (FAIL)
$ make check-qemu-semantics         → EXIT=2（FAIL reg-compare.yaml[8]/[9]/[10]）
复原：cp 回原文件，sha256 == 原值 2aae8b61…，grep INJECT = 0
$ make build-qemu JOBS=8            → EXIT=0（6.3s）
$ make check-qemu-semantics         → EXIT=0，149 total, 149 passed, 0 failed
```
**⇒ 向量对 48 位掩码有真实鉴别力；复原（含重建）后恢复全绿** ✓。

**(c) patch 合规（INFRA-023t §6.1）**
```
$ git hash-object .work/source/qemu/.../trans_compare.c.inc
  33b54c50b3113d280aea1c1cedccf0ec0f95dcb8
patch 的 index 行 =..33b54c5  （blob 一致）
$ git -C .work/source/qemu diff c3d48b7 -- target/dadao/insn_trans/trans_compare.c.inc
  vs 已提交补丁 → diff 无输出（IDENTICAL）
$ python3 tools/infra/check_patch_tree.py → EXIT=0, 2 component(s), 67 patches OK
```
`.work/source/qemu/.git` 存在（未打印 skip 行）⇒ 断言 ④/⑥ 实际执行；断言 ⑥（应用产物 == `.work/source`）通过 ✓。补丁为**裸 `git diff` 重导出**（逐字节一致）✓。

**(d) 无回归**
```
$ make check  → EXIT=0；repository checks: PASS
   validate-vectors: 152/152 M1 identities covered OK（15 files, 689 cases）
   check-qemu-semantics: 149/149 PASS
   llvm-lit: 25 tests, Passed 25 (100.00%)
   check_issues: 63 open, 11 closed（0 blocking M1-gate）
```

**(e) 范围**
```
$ git diff --name-only
 .tao/knowledge/contract-isa.md
 components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch
 spec/SimRISC-05-64位地址运算.md
 spec/SimRISC-06-控制流.md
 tests/vectors/isa/reg-compare.yaml
+ 未跟踪：任务书本身
```
均为任务书清单内；补丁 diff 仅动 `trans_cmp_uo_orrr_rb`（注释 + 删 2 行掩码），**未动 `rb0`/控制流部分** ✓。

##### 2. 约束逐条核验

| # | 验收标准 | 我的核验 | 判决 |
|---|---------|---------|------|
| 1 | `cmp.uo-rb` 整 64 位 | 三例原始 dump rd1 均 `+1`（48 位应为 −1/0/−1） | ✅ |
| 2 | 向量有鉴别力（注入 FAIL + 复原 PASS） | 注入 ⇒ [8][9][10] FAIL EXIT=1、gate EXIT=2；复原 ⇒ 149/149 EXIT=0 | ✅ |
| 3 | spec/contract 无「低 48 位比较」残留；SimRISC-06 明示 `br.*-rb` 64 位 | `grep` EXIT=1（SimRISC-05/contract-isa/SimRISC-06）；SimRISC-06 L74「按**整 64 位**判零」；不矛盾 D8.7 | ⚠️ **部分**（见 F1） |
| 4 | patch 合规（§6.1 + 断言 ①–⑥） | 补丁 = 裸 `git diff` 逐字节重导出；blob 一致；check-patch-tree EXIT=0（含⑥） | ✅ |
| 5 | 无回归（`make check` EXIT=0；semantics；lit 25/25） | 全部 EXIT=0；149/149；25/25；152/152 | ✅ |
| 6 | 未越界 | `git diff --name-only` ⊆ 清单；`rb0`/控制流未动 | ✅ |
| 7 | 构建 JOBS=8、一次一个、真实退出码 | 两次增量 6.3s；退出码均用 `rc=$?` 捕获 | ✅ |

##### 3. Findings

- **F1【阻断 · 设计层/任务书 ↔ ADR 冲突】`spec/SimRISC-00-指令系统设计.md:74` 仍为旧口径**：
  ```
  | 算术运算类指令-比较 | `cmp.uo-rb` | **低 48 位**无符号比较，…；**bits[63:48] 不影响比较运算** |
  ```
  `ADR-0012 D8.6（同步面）` **明确把 `spec/SimRISC-00` 列入同步面**；且该行是 `SPEC-079t` 为旧 D8.2 改写的（`git log -S` 可溯）。D8.2 已就地修订为 64 位，本任务却把 `SimRISC-00` 列为「范围外」，导致**生效规范仍自相矛盾**（SimRISC-05 说整 64 位、SimRISC-00 说低 48 位）。这是**任务书范围与 ADR 真源的冲突**，非实现细节——**提交架构师定夺**：或把 `SimRISC-00` L74 一并纳入返工（对齐 D8.6），或在 ADR/任务书显式豁免它并给出理由。**在此裁定前不放行。**

- **F2【同类残留 · 必修】`tests/vectors/isa/reg-compare.yaml:132` 仍写 `bits=48 (D8.2)`**：
  ```
  notes: 'cmp.uo: rb2=0xa, rb3=0x14, bits=48 (D8.2), signed=False'
  ```
  该 note 由 `QEMU-031t`（`9ffb76b`）为旧 D8.2 引入（原为 `bits=64`）。本任务改动清单第 5 条只提「3 条 boundary 用例」，但**同文件同类 48 位残留未清**——与 AGENTS「修复须修一类」相悖，且直接与已修订 D8.2 矛盾。应改回 `bits=64`（该用例期望值不变，改 note 不影响门控）。

- **F3【提示】`docs/testcases-009t-audit.md:102`**：`cmp.uo-rb orrr | 无符号 64 位 RB 比较；bits[63:48] 不影响` —— 同句「64 位比较」与「bits[63:48] 不影响」互相矛盾（现行 D8.2 下高 16 **参与**比较）。属 `TESTCASES-009t` 审计快照，是否需同步由架构师/该模块定，本任务未列。

##### 4. 判决

**Needs Revision**。

- 工程实现层面：验收标准 1/2/4/5/6/7 在我独立重跑下**全部通过**（64 位实测 `+1`、注入 FAIL/复原 PASS、补丁裸 diff 重导出、`make check` EXIT=0、lit 25/25）。
- **不放行原因**：F1 为设计层阻断（`SimRISC-00` 生效规范与修订后 D8.2 矛盾，且与 ADR D8.6 同步面冲突，任务书范围待架构师裁定）；F2 为同文件同类 48 位残留，须一并清除。**F1 需架构师定夺范围后再返工；F2 可直接修。**

**待复核项**：F1 裁定 + F2 修复后，重跑 (a)(b)(c)(d) 即可复验。

#### 第 2 轮 engineer 返工

**返工项**：F1 + F2（主会话裁定 F1 纳入返工，F3 不改）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `SimRISC-00:74` 旧口径「低 48 位…bits[63:48] 不影响」 | ✅已修 | `spec/SimRISC-00-指令系统设计.md` L74 →「**整 64 位**无符号比较（`bits[63:48]` **参与**）」 | `grep -n "cmp.uo" spec/SimRISC-00-指令系统设计.md` → 仅一行，已为「整 64 位」 |
| F2 `reg-compare.yaml:132` `bits=48 (D8.2)` | ✅已修 | L132 → `bits=64 (D8.2 revised)` | `grep -n "bits=48" tests/vectors/` EXIT=1（无匹配） |
| F3 `testcases-009t-audit.md:102` | ⏸延后 | 历史审计快照，不改（reviewer F3 确认） | — |

**全库同类 grep**（`bits=48`、`低 48 位`+比较/`cmp.uo` 相关）：
- `grep -rn "bits=48" tests/vectors/` → EXIT=1（无匹配）✓
- `grep -rn "低 48 位.*比较\|比较.*低 48" spec/ .tao/knowledge/contract-isa.md` → 无 `cmp.uo-rb` 相关匹配
- 其余 "低 48 位" 引用均为地址使用（D8.3/D8.7），非比较，正确不改

**本轮复验**（只改文档/向量，QEMU 补丁未变，不需重建）：
```
$ python3 tools/infra/check_patch_tree.py  →  EXIT=0, 2 component(s), 67 patches OK
$ make check-qemu-semantics               →  EXIT=0
$ make check-lit                          →  EXIT=0
$ make check                              →  EXIT=0
```

**`git diff --name-only`**（6 文件）：
```
.tao/knowledge/contract-isa.md
components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch
spec/SimRISC-00-指令系统设计.md
spec/SimRISC-05-64位地址运算.md
spec/SimRISC-06-控制流.md
tests/vectors/isa/reg-compare.yaml
```
均在清单内（含 SimRISC-00），无越界。QEMU 补丁 diff 不变（本轮未动实现）。

#### 第 2 轮 reviewer 复核

**范围**：仅第 1 轮 F1/F2 的消解复核（F3 登记、其余已过项不重复）。**未采信完成区**，全部亲自重跑；证据 `/tmp/opencode/SPEC-081t-r2/`（我的日志 `my-*`）。

##### 1. 重跑记录（我自己的输出/退出码）

**(a) F1 —— 三处口径一致性（直接读生效文件）**

```
$ sed -n '74p' spec/SimRISC-00-指令系统设计.md
  | 算术运算类指令-比较 | `cmp.uo-rb` | **整 64 位**无符号比较（`bits[63:48]` **参与**），结果 -1/0/1 区分小于/等于/大于 |
$ sed -n '58p' spec/SimRISC-05-64位地址运算.md
  `cmp.uo-rb` 对两个操作数的**整 64 位**进行**无符号**比较（`bits[63:48]` 参与）…
$ sed -n '700,702p' .tao/knowledge/contract-isa.md
  | `cmp.uo rdhb, rbhc, rbhd` | **整 64 位**无符号比较，结果 −1/0/1 … |
  - 比较按**整 64 位**无符号；仅**作地址使用时**取低 48（见 D8.7）。[ADR-0012 D8.2]
```
三处（SimRISC-00 / SimRISC-05 / contract-isa §7.3）口径**全部为「整 64 位、bits[63:48] 参与」**，不再自相矛盾；与 `ADR-0012 D8.2`（就地修订）逐字相符 ✓。`git diff` 显示 SimRISC-00 仅此一行改动，无越界。

**(b) F2 —— 同类残留清零（我自己的 grep）**

```
$ grep -rn "bits=48" tests/vectors/            → 无匹配（EXIT=1）
$ grep -rn "不影响" spec/SimRISC-00 spec/SimRISC-05 spec/SimRISC-06 .tao/knowledge/contract-isa.md
  → 无 cmp.uo-rb 相关命中（旧句「bits[63:48] 不影响比较运算」已从 SimRISC-00/0.5.3 生效面移除）
$ grep -rn "低 48 位" spec/ .tao/knowledge/contract-isa.md tests/vectors/ | grep -i "比较\|cmp"
  → 无 cmp/比较语境命中（余下「低 48 位」均属地址使用 D8.3/D8.7，正确不改）
$ grep -n "bits=48" tests/vectors/isa/reg-compare.yaml   → EXIT=1
```
生产面（`spec/`、`contract-isa`、`tests/vectors/`）**无 `bits=48`、无旧「低 48 位比较」残留** ✓。

**(c) QEMU 补丁未变 + 合规**

```
$ ; P=<...>/trans_compare.c.inc.patch; base=c3d48b7d1e…
$ GIT_INDEX_FILE=$tmp/idx git -C .work/source/qemu apply --cached "$P"   → apply_rc=0
$ post-image blob = 33b54c50b3113d280aea1c1cedccf0ec0f95dcb8
$ worktree blob   = 33b54c50b3113d280aea1c1cedccf0ec0f95dcb8   （断言⑥ 独立复现：相等）
$ git -C .work/source/qemu diff c3d48b7d1e… -- target/…/trans_compare.c.inc > my-regen.patch
$ diff my-regen.patch <committed patch>   → IDENTICAL（补丁 == 裸 git diff 重导出）
$ sha256(.work/source/.../trans_compare.c.inc) = 2aae8b61…  == 第 1 轮 orig.sha256（二进制对应源未变）
$ diff <第1轮 regen.patch> <当前 patch>   → IDENTICAL（sha256 均 013e3ba9…）⇒ 第 2 轮确未动实现
$ grep -c INJECT .work/source/.../trans_compare.c.inc → 0
```
补丁内 `trans_cmp_uo_orrr_rb` 无 `andi_i64(0x0000FFFFFFFFFFFF)` 掩码，仅 `gen_cmp_three_way(result, rbhc, rbhd, false)`；`git diff` 仅该函数（注释 + 删 2 行），rb0/控制流部分未动 ✓。

**(d) 独立 oracle（运行二进制确为 64 位，非「编译通过」）**

用 QMP `pmemsave` 取 `DUMP_BASE+0x008`（rd1，大端）：
```
--case 8  → rd1_be=0x0000000000000001 (+1)
--case 9  → rd1_be=0x0000000000000001 (+1)
--case 10 → rd1_be=0x0000000000000001 (+1)
```
48 位语义下三例应分别为 −1/0/−1；实测一律 **+1** ⇒ 运行二进制**整 64 位比较** ✓。
期望值我**独立重算**：8) 2^48+1 > 2 → +1；9) 2^48+1 > 1 → +1；10) 2^48 > 2^48−1 → +1。与向量 `expected_state.rd.rd1=0x…01` 一致 ✓。

**(e) 无回归 / 门控（真实退出码）**

```
$ python3 tools/infra/check_patch_tree.py   → EXIT=0, 2 component(s), 67 patches OK
  （.work/source/{qemu,llvm-project}/.git 均存在，无 "skipping apply check" ⇒ 断言①–⑥实际执行，含⑥）
$ make check-qemu-semantics                 → EXIT=0; 149 total, 149 passed, 0 failed
$ make check-lit                            → EXIT=0; 25 discovered, Passed 25 (100.00%)
$ make check                                → EXIT=0; repository checks: PASS
```

**(f) 范围 / 历史文件**

```
$ git diff --name-only（EXIT=0）:
  .tao/knowledge/contract-isa.md
  components/qemu/patches/…/trans_compare.c.inc.patch
  spec/SimRISC-00-指令系统设计.md
  spec/SimRISC-05-64位地址运算.md
  spec/SimRISC-06-控制流.md
  tests/vectors/isa/reg-compare.yaml
$ git status --short → 以上 6 个 M + 未跟踪任务书本身，别无其它
```
`spec/SimRISC-0.5.3/*`、`docs/testcases-009t-audit.md`、`trans_ctrl` 相关补丁**均未出现在 diff 中**（历史文件干净、rb0/控制流未动）✓。

##### 2. 约束逐条核验

| # | 第 2 轮复核项 | 我的核验 | 判决 |
|---|--------------|---------|------|
| 1 | F1 已消解（三处一致） | SimRISC-00 L74 / SimRISC-05 L58 / contract-isa L700-702 均「整 64 位」；与 ADR D8.2 相符 | ✅ |
| 2 | F2 已消解 + 修一类 | `tests/vectors` 无 `bits=48`；生产面无旧比较口径；SimRISC-00 旧句已除 | ✅（附 1 项非阻断观察，见下） |
| 3 | QEMU 补丁未变 + check-patch-tree ①–⑥ | patch == 裸 diff 重导出；blob 一致；无掩码；EXIT=0 且含断言⑥ | ✅ |
| 4 | make check / lit / semantics | EXIT=0；25/25；149/149 | ✅ |
| 5 | 范围（6 文件）+ 历史干净 | diff ⊆ 清单；0.5.3、audit、trans_ctrl 未动 | ✅ |
| 6 | F3 登记 | 完成区「新发现/坑」第 4 条登记 `docs/testcases-009t-audit.md:102` 为历史快照不改 | ✅ |

##### 3. 非阻断观察（不影响判决，供架构师/主会话知悉）

- **O1（豁免清单未列全 `.tao/tasks/**`）**：`grep -rn "bits=48"` 全库（除 `.git/.work/.cache`）仍在 `.tao/tasks/qemu/QEMU-031t-D8地址语义实现.md`（L47/L62/L94）与 `.tao/tasks/spec/SPEC-081t-…md`（本轮任务书，描述修复）命中；`.tao/tasks/spec/SPEC-079t-…md` 亦含旧「低48位无符号比较」。这些是**已完成任务的历史记录**（与 `docs/testcases-009t-audit.md`、`spec/SimRISC-0.5.3/*` 同类），不应追溯改写（会伪造历史）。但完成区的豁免清单**只列了 0.5.3 与 audit，未列 `.tao/tasks/**`**。属「逐条说明」的列举不完整，**不影响生效规范/向量/实现的一致性**，建议在完成区补一句豁免说明即可，不构成打回。测试件里 `.cache/refs/`（只读参考仓库）亦有旧口径，与 v5 无关。
- **O2（contract-isa 对 `br.*-rb` 未显式写「整 64 位」）**：`contract-isa` §8.3 L750 与 §13 L1466 仍写 `rbha == 0`/`rbha != 0`（未加「整 64 位」字样），与 64 位判零**不矛盾**（对整寄存器判零未含掩码），且 `SimRISC-06` L74 已显式「按整 64 位判零」；`trans_ctrl` 的 `trans_br_z/nz_riii_rb` 亦为 `TCG_COND_EQ/NE` 全 i64、无掩码。属可选增强，非缺陷。

##### 4. 判决

**Accepted（第 2 轮 F1/F2 复核通过）**。

- F1：`SimRISC-00:74` 已改为「整 64 位」，且 SimRISC-00 / SimRISC-05 / contract-isa 三处口径一致，与 `ADR-0012 D8.2`（就地修订）相符 —— **消解**。
- F2：`reg-compare.yaml` 无 `bits=48`;生产面同类旧口径逐条清零（历史文件按类豁免）；**消解 + 修一类**（生产面）。
- QEMU 补丁**逐字节未变**（== 第 1 轮重导出），`check-patch-tree` 断言①–⑥全过（含⑥ blob 一致，我独立复现）；运行二进制经 `pmemsave` 原始 dump 证实为整 64 位比较。
- `make check` EXIT=0、lit 25/25、`check-qemu-semantics` 149/149，均为**我独立重跑**的真实退出码与输出。
- 约束逐条守住，`git diff` 严格 ⊆ 清单，历史文件/QEMU-031t 控制流未动。**无需进一步返工**。
- 遗留：O1/O2 为非阻断观察，供架构师终审参考（最终接受权在架构师）。


#### 主会话收尾（2026-10-02）

1. **提交推送**：QEMU 补丁（`trans_cmp_uo_orrr_rb` 去 48 掩码）+ `SimRISC-00/05/06` + `contract-isa.md` + `reg-compare.yaml`（见 git log）。
2. **过程**：reviewer 第 1 轮 **Needs Revision** —— **F1**（`SimRISC-00:74` 旧口径「低 48 位比较」与 `SimRISC-05` 矛盾；**我任务书的"不改 SimRISC-00"与 ADR `D8.6` 同步面冲突** ✗）⇒ 更正；**F2**（`reg-compare.yaml:132` `bits=48` 同类残留）⇒ 全库排查清零。第 2 轮 **Accepted**（F1/F2 消解；QEMU 补丁逐字节未变 sha `013e3ba9…`；断言⑥过；QMP `pmemsave` 独立 oracle 实测 64 位 `+1`）。
3. **教训**：写任务书时**「范围外」必须先对照 ADR 的同步面**（本轮 `D8.6` 要求同步 `SimRISC-00/05/06`，我误排除 `SimRISC-00`）✗。
4. **非阻断观察（供终审）**：
   - **O1**：`.tao/tasks/{qemu/QEMU-031t, spec/SPEC-079t}.md` 仍含旧口径（`bits=48`/「低48位」）——属**已完成任务的历史记录**，不追溯改写；完成区豁免清单未列 `.tao/tasks/**`，建议后续表述补齐。
   - **O2**：`contract-isa` 对 `br.*-rb` 写 `rbha == 0`（未加「整 64 位」字样），与 64 位判零不矛盾（实现无掩码）。
