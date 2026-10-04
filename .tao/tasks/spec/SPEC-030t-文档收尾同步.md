# SPEC-030t: contract-isa.md 空行清理 + docs/README.md 同步

**模块**：spec
**项目里程碑**：M2
**依赖**：无
**状态**：已验证

> **处置（2026-10-04，`SPEC-090k` 核验）：改范围（继续执行，范围收窄）。**
> 原两项：① **`docs/README.md:17` 同步已完成**（现为当前口径 `227 = M1 152 + scope fp 60 + scope excluded 15`，非本任务旧描述的 `254/178/76`）；② **`contract-isa.md` 附录 A FP 表断表空行仍有效**——实测 `.tao/knowledge/contract-isa.md:1416` 有一个空行夹在 `| 0x4F | set.w-rf | …`（L1415）与 `| 0x5E | cs.eq-rf | …`（L1417）之间，**该表头 + 分隔行在 L1404–L1405，空行使 L1417–L1432 脱离表格**（markdown 断表，后续 `| … |` 行不再渲染为表）。**本任务收窄为**：删除 L1416 空行（使 L1417+ 回到 L1404 表内）。
> 实测依据：`awk` 列 1404–1445 行确认断表位置；L1433 起的空行属「新节前空行」，**不动**。

## 问题描述

审核发现两处收尾，收窄后仅剩一处：

1. **contract-isa.md 附录 A FP 表断表空行**（**仍有效**）：`| 0x4F | …`（L1415）与 `| 0x5E | …`（L1417）之间有一个空行（L1416）；该表头 + 分隔行在 L1404–L1405，空行使 L1417–L1432 **脱离表格**（markdown 断表）。
2. ~~**docs/README.md:17 未同步**~~（**已完成**，2026-10-03/04：现为当前口径 `227`，指向 `.tao/knowledge/contract-asm-list.md`）

## 修改内容

### 1. contract-isa.md 附录 A FP 表断表空行清理（仅此项）

找到附录 A 中：
```
| 0x4F | set.w-rf | `set.w` | RF 立即数 | [SimRISC-00 §SimRISC QFC] |


| 0x5E | cs.eq-rf | ...
```
删除该空行，使 `| 0x5E | …` 起的行回到 L1404 表内（删除后该表数据行 L1406–L1432 连续、无空行）。

### 2.（已完成，不执行）原 `docs/README.md:17` 更新

> 已于 2026-10-03/04 完成：`docs/README.md:17` 现为当前口径 `227 = M1 152 + scope fp 60 + scope excluded 15`，指向 `.tao/knowledge/contract-asm-list.md`。以下旧内容仅存历史。

### 2. docs/README.md 第17行更新

旧内容：
```
| `assembly-list.md` | **DADAO 汇编指令表（新语法）**：256 条，按 **8位数据运算/16位数据运算/32位数据运算/64位数据运算/64位地址运算/浮点/存储/控制流/寄存器复制/16位立即数操作/其它/待定** 分章，...；**浮点（46）与待定（14）两章整章 deferred**，其余 196 条为当前有效书写形式 |
```

新内容（顺序、名称、计数对齐 SimRISC-00~12）：
```
| `assembly-list.md` | **DADAO 汇编指令表（新语法）**：254 条，按 **取数存数/寄存器复制/16位立即数操作/64位数据运算/64位地址运算/控制流/浮点运算/32位数据运算/16位数据运算/8位数据运算/其它/待定** 分章，...；**浮点运算（46）与待定（12）两章整章 deferred**，其余 196 条为当前有效书写形式 |
```

## 约束

- 逐条精确替换，**禁止正则批量替换**
- 不改动其他内容

## 验收标准

1. `contract-isa.md` 附录 A 中 L1404 表头下的数据行（L1406–L1432）**连续无空行**（L1416 已删除）。
2. 其他内容未改动（`git diff` 只含 `.tao/knowledge/contract-isa.md` 的一行删除）。
3. 一键证据脚本：非交互、任一失败即非零退出、逐项打印「检查名 + 期望/实际 + 退出码」+ 注入反例自检（如重新插入空行 → 自检 FAIL）。落点 `.work/evidence/SPEC-030t/`。

## 完成区
**测试结果**：一键证据脚本 8/8 检查项 PASS（EXIT=0）；`make check` EXIT=0（lit 31/31 Passed、repository checks: PASS）。证据：`.work/log/spec/SPEC-030t-evidence.log`、`.work/log/spec/SPEC-030t-make-check.log`。
**修改文件**：`.tao/knowledge/contract-isa.md`（删除 L1416 空行，1 行删除、0 行新增、单 hunk）。新增证据脚本 `.work/evidence/SPEC-030t/check.sh`（`.work/` 已 gitignore，不入库）。未改动其他文件。
**验收结果**：
- `git diff --numstat -- .tao/knowledge/contract-isa.md` → `0	1	.tao/knowledge/contract-isa.md`（仅一行删除）。
- `git diff` 内容：仅 `-`（删空行），位于 `| 0x4F | set.w-rf | …`（现 L1415）与 `| 0x5E | cs.eq-rf | …`（现 L1416）之间。
- 附录 A FP 表数据行现连续：表头 L1404/分隔 L1405，数据行 L1406–L1431 共 **26 行**，无中间空行；L1432 为空行、L1433 `---`（新节前空行，未动）。
- 证据脚本输出（节选）：`[PASS] C2_table_contiguous | expected=26rows no-gap actual=26rows(first_nonrow=L1432) rc=0`；`[PASS] C3_isa_diff_one_deletion | numstat=[0 1 .tao/knowledge/contract-isa.md] hunks=1 removed=[-] rc=0`。
- 反例自检：插回空行后 `[PASS] C4_inject_detected | … 10rows(gap_at=L1416:'')`（脚本报 FAIL），还原后 `[PASS] C4_restored | actual=26rows(first_nonrow=L1432)`，`[PASS] C5_restored_diff_clean`。
**新发现/坑**：
1. 任务书行号描述近似：附录 A FP 表**数据行实为 26 行（L1406–L1431）**，任务书写的 "L1406–L1432" 把删除前的空行/末行位置算入；原 HEAD 中 L1432 为最后一条数据行，删空行后最后数据行落在 L1431。判据应以「表头下连续 `|` 数据行 26 行、无中间空行」为准，而非固定行号。
2. **并发他任务改动**：本任务窗口内工作树另有 `.tao/knowledge/contract-abi.md`（`SimRISC-02`→`SimRISC-06`）与 `tools/testcases/generate_isa_vectors.py` 被修改，**非本任务所改**（基线 `git status` 为空，属并行任务）。故「`git diff` 只含 contract-isa.md」在该共享工作树上无法整体成立；证据脚本 C3 收窄为对 isa.md 自身的 diff 断言（0 增/1 删/单 hunk/删空行），并增设 C3b 无未跟踪残留硬检查 + C3c 信息项披露其它被改文件。
**遗留问题**：本任务范围内无。披露：工作树存在他任务对 `contract-abi.md`、`tools/testcases/generate_isa_vectors.py` 的并发未提交改动，本任务未触碰。

## 审阅记录

#### 第 1 轮 engineer 自审
**逐行审查对象**：`.tao/knowledge/contract-isa.md`（改动 1 行删除）+ `.work/evidence/SPEC-030t/check.sh`（证据脚本）。

**审查要点与判决**：
- 逻辑正确性：删除的正是 L1416 空行；删除后 `| 0x4F |`（L1415）与 `| 0x5E |`（L1416）相邻，表数据行连续。`| 0x5F |`…`| MISC-AMO 011-xxx |` 保持在表内。✅
- 边界情况：表尾 `L1432`（空行）/`L1433`（`---`）为「新节前空行」，未动；未误删表尾空行。
- 设计/惯用法：仅一行删除，`git diff` 单 hunk、0 增 1 删，符合「逐条精确替换、禁止正则批量替换」。
- 防造假：证据脚本真实执行；反例注入用 sha256 前后比对确认文件确被改动（因注入后文件回到 HEAD 状态，`git diff --name-only` 不再显示该文件，故不能用它判「注入已生效」——已改用哈希，修正原始设计的缺陷）。
- 脚本健壮性：C2/C4 期望值由「27」修正为真实值「26」（见完成区新发现 1）；C3 收窄到 isa.md 自身 diff 并显式披露 C3c 他任务改动，避免在共享工作树上得出错误结论。

**finding 处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 脚本初版期望 27 行，实际 26 行 → C2/C4 误报 FAIL | ✅已修 | `check.sh` 期望值 27→26，注释与输出同步 | `[PASS] C2_table_contiguous … actual=26rows …` |
| 注入自检用 `git diff --name-only` 判「已改变」恒失败（注入后回到 HEAD） | ✅已修 | 改用 sha256 前后比对 | `[PASS] C4_inject_applied … hash eb8cc9f6… -> a750083c…` |
| 完成区「git diff 只含 isa.md」因他任务并发改动 abi.md/脚本而无法成立 | ✅已修（收窄+披露） | C3 断言收窄为 isa.md 自身 0/1 单 hunk 删空行；加 C3b、C3c | `[PASS] C3_isa_diff_one_deletion`、`[INFO] C3c … contract-abi.md` |

**判决**：全部 finding 已修，无未修项 → 状态置 `待验收`。

#### 第 1 轮 reviewer 验收

**审查模型**：mimo-v2.5-pro
**审查时间**：2026-10-04

##### 重跑记录

**1. `git diff --numstat -- .tao/knowledge/contract-isa.md`**
```
0	1	.tao/knowledge/contract-isa.md
```
✅ 0 增 1 删，符合预期。

**2. `git diff -- .tao/knowledge/contract-isa.md`（完整 diff）**
```diff
@@ -1413,7 +1413,6 @@ M1 范围内的异常：[SimRISC-00 §指令设计][SimRISC-00 §压栈流程（
 | 0x3F | stm.o-rf | `stm.o` | RF 存取 | [SimRISC-00 §SimRISC QFC] |
 | 0x44 | MISC-RF | （浮点子表） | 浮点 | [SimRISC-00 §MISC-RF指令编码] |
 | 0x4F | set.w-rf | `set.w` | RF 立即数 | [SimRISC-00 §SimRISC QFC] |
-
 | 0x5E | cs.eq-rf | `cs.eq` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
 | 0x5F | cs.ne-rf | `cs.ne` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
 | 0x61 | cs.n-rf | `cs.n` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
```
✅ 单 hunk，仅删一行空行，位于 `| 0x4F | set.w-rf |` 与 `| 0x5E | cs.eq-rf |` 之间。

**3. 附录 A FP 表数据行连续性（实测）**
```
L1404: | op (hex) / 位置 | insn | 助记符 | 类别 | 来源 |
L1405: |-----------------|------|--------|------|------|
L1406: | 0x16 | ld.t-rf | ...
...
L1415: | 0x4F | set.w-rf | ...
L1416: | 0x5E | cs.eq-rf | ...
...
L1431: | MISC-AMO 011-xxx | sc_nn/... | ...
L1432: （空行）
L1433: ---
```
✅ 数据行 L1406–L1431 共 26 行，全部以 `|` 开头，连续无中间空行。L1432 空行 / L1433 `---` 为新节前空行，未动。

**4. engineer 证据脚本 `.work/evidence/SPEC-030t/check.sh` 重跑**
```
=== SPEC-030t 证据脚本 ===
target: /mnt/tao/DADAO-v5/.tao/knowledge/contract-isa.md
[PASS] C1_file_exists | expected=exists actual=exists rc=0
[PASS] C2_table_contiguous | expected=26rows no-gap actual=expected=26rows actual=26rows(first_nonrow=L1432) rc=0
[PASS] C3_isa_diff_one_deletion | expected=0+ 1-(blank) 1hunk actual=numstat=[0	1	.tao/knowledge/contract-isa.md] hunks=1 removed=[-] rc=0
[PASS] C3b_no_untracked_residue | expected=none actual=none rc=0
[INFO] C3c_other_modified_tracked_files | isa.md 之外被修改的文件：contract-abi.md, SPEC-033t, tests/vectors/isa/*.yaml, generate_isa_vectors.py
--- C4 反例注入自检 ---
[PASS] C4_inject_applied | expected=file content changed actual=hash eb8cc9f6... -> a750083c... rc=0
[PASS] C4_inject_detected | expected=table_check rc=1 (FAIL) actual=expected=26rows actual=10rows(gap_at=L1416:'') rc=0
[PASS] C4_restored | expected=table_check rc=0 (PASS) actual=expected=26rows actual=26rows(first_nonrow=L1432) rc=0
[PASS] C5_restored_diff_clean | expected=0 1 .tao/knowledge/contract-isa.md actual=0	1	.tao/knowledge/contract-isa.md rc=0
=== OVERALL=PASS ===
EXIT=0
```
✅ 8/8 检查项 PASS，EXIT=0。

**5. reviewer 独立注入反例**
```
# 注入前 hash
BEFORE_HASH=eb8cc9f650e489e5672ce1e0c1340398d1e6f5772781c08d66b63639700ffe43

# 注入空行（python3: lines.insert after | 0x4F | set.w-rf）
AFTER_HASH=a750083cdb16b512e6037b22e5792af2a8606f27f5153aade3a603c44285e4e5
INJECT_VERIFIED: hash changed ✅

# 注入后重跑 check.sh
[FAIL] C2_table_contiguous | expected=26rows actual=10rows(gap_at=L1416:'') rc=1
[FAIL] C3_isa_diff_one_deletion | expected=0+ 1-(blank) 1hunk actual=numstat=[] hunks=0 removed=[] rc=1
=== OVERALL=FAIL ===
EXIT=1

# 还原（cp backup）
RESTORE_HASH=eb8cc9f650e489e5672ce1e0c1340398d1e6f5772781c08d66b63639700ffe43
git status 确认：仅 contract-isa.md M（modified），与注入前一致 ✅

# 还原后重跑 check.sh
8/8 PASS, EXIT=0 ✅
```
✅ 注入→FAIL→还原→回绿，完整链路验证通过。

**6. `make check` 独立重跑**
```
lit 31/31 Passed
80 项 interg-check: 80 PASS / 0 FAIL
repository checks: PASS
EXIT=0
```
✅ EXIT=0，全部通过。

##### 约束核验

| 约束 | 判定 | 证据 |
|------|------|------|
| 仅删 `contract-isa.md` 该空行（`git diff --numstat` = `0 1`） | ✅ | `0 1 .tao/knowledge/contract-isa.md` |
| 附录 A FP 表数据行连续无中间空行 | ✅ | 26 行连续以 `|` 开头，L1432 空行为表尾 |
| 未触碰禁改区 / 表内容 | ✅ | diff 仅 `-`（删空行），无内容行改动 |
| 未触碰其它文件（本任务范围） | ✅ | contract-abi.md / test vectors / generate 脚本均为并行他任务改动 |
| 证据脚本合格（FAIL 路径存在、无恒真、注入非空可还原） | ✅ | 逐条审查 7 个断言 + 独立注入验证 |
| 工作树无未跟踪残留 | ✅ | C3b PASS |

##### 判决

**Accepted**

所有验收标准满足：
1. `contract-isa.md` 附录 A FP 表 L1404 表头下数据行（L1406–L1431）连续无空行（26 行）——L1416 空行已删除。
2. 仅删 1 行（`git diff --numstat` = `0 1`），单 hunk，未改动表内容或其它文件。
3. 证据脚本 8/8 PASS，独立注入反例验证通过（注入→FAIL→还原→PASS）。
4. `make check` EXIT=0（lit 31/31、80/80 interg-check、repository checks PASS）。
5. 工作树并发改动（contract-abi.md、test vectors、generate 脚本）已核实为非本任务所为。

#### 第 1 轮 architect 交叉复核（双模型互验）

**复核模型**：deepseek-flash
**复核时间**：2026-10-04
**结论**：**确认 Accepted**。未发现 reviewer 验收遗漏关键项、约束被违反或判决过严/过松。

##### 独立核验（真实命令 + 输出）

**1. `contract-isa.md` 仅删 1 行 + 附录 A FP 表连续**
```
$ git diff --numstat -- .tao/knowledge/contract-isa.md
0	1	.tao/knowledge/contract-isa.md
$ git diff -- .tao/knowledge/contract-isa.md
@@ -1413,7 +1413,6 @@ ...
 | 0x4F | set.w-rf | `set.w` | RF 立即数 | [SimRISC-00 §SimRISC QFC] |
-
 | 0x5E | cs.eq-rf | `cs.eq` | 浮点条件赋值 | [SimRISC-00 §SimRISC QFC] |
```
单 hunk、0 增 1 删，删的正是空行。实测附录 A（awk 1404–1434）：表头 L1404、分隔 L1405、数据行 **L1406–L1431 共 26 行**连续以 `|` 开头；L1432 为首个非 `|` 行（空行）、L1433 `---`（新节前空行，未动）。断表已消除。（独立 awk 计 `|` 起始行 = 27 行 = 1 分隔 + 26 数据，与脚本一致。）

**2. 证据脚本独立重跑**
```
$ bash .work/evidence/SPEC-030t/check.sh
... C1/C2/C3/C3b/C4_inject_applied/C4_inject_detected/C4_restored/C5 全 [PASS]
=== OVERALL=PASS ===   SCRIPT_EXIT=0
```
脚本跑完后 isa.md sha256 回到 `eb8cc9f6…`、`git status` 与基线逐字一致 → 脚本自还原无误。

**3. 独立注入反例（我的方式，不复用脚本内建）**
```
BK_HASH    = eb8cc9f650e489e5672ce1e0c1340398d1e6f5772781c08d66b63639700ffe43
注入空行(L1415 后) → INJ_HASH = a750083cdb16b512e6037b22e5792af2a8606f27f5153aade3a603c44285e4e5
$ bash check.sh → [FAIL] C2_table_contiguous … 10rows(gap_at=L1416:'')
                  [FAIL] C3_isa_diff_one_deletion … numstat=[] hunks=0
                  === OVERALL=FAIL ===   INJECTED_SCRIPT_EXIT=1
还原 cp backup → RESTORE_HASH = eb8cc9f6…（= BK_HASH）
$ bash check.sh → 8/8 [PASS] === OVERALL=PASS ===   RESTORED_EXIT=0
```
注入→FAIL→还原→回绿 完整链路独立复现；脚本 FAIL 路径真实可达、非恒真。

**4. `make check` 独立重跑**：`MAKE_CHECK_EXIT=0`；lit `Passed: 31 (100.00%)`；`总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0`；`repository checks: PASS`。（reviewer 记录的「80/80 interg-check」与日志 L129 实值一致。）

**5. 约束核验**：isa.md 之外被改文件均与「删空行」无关——`contract-abi.md` 仅溯源行 `SimRISC-02→SimRISC-06`、`tests/vectors/isa/*.yaml` 与 `generate_isa_vectors.py` 为指令编号重编号（44/44 等），属并行他任务；本任务对 `contract-isa.md` 的改动仅上述 1 行删除。工作树无未跟踪残留（C3b PASS）。

##### 备注（不影响判决）
- 验收标准 2 字面「`git diff` 只含 `contract-isa.md` 一行删除」在共享工作树上须按**文件级**理解：全树 diff 另含并行他任务文件。engineer 已收窄断言至 isa.md 自身并加 C3c 披露，reviewer 采纳合理，属**披露充分**而非违反。
- 复核期间一次 `git status` 与基线瞬时出现单行差异（仅 `contract-abi.md`），随即重测消失，判定为并行任务/索引瞬态，与本任务无关。

**复核判决**：双模型一致 **Accepted**，无需返工。