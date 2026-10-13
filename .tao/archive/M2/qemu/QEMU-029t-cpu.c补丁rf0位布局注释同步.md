# QEMU-029t: `cpu.c.patch` 的 rf0 位布局注释同步（ADR-0012 D6）

**模块**：qemu
**项目里程碑**：M2
**依赖**：`SPEC-060t`（已 Accepted，ADR-0012 D6 落地）
**状态**：已验证

## 问题

`components/qemu/patches/target/dadao/cpu.c.patch` 的 rf0 复位注释块仍写**旧位布局**（缺口 `rela.si` 无关，纯注释漂移）：

```
+    /* rf0 = FCSR reset value (per ADR-0004 D2, derived from SimRISC-00 §浮点状态寄存器)
+     * Bits [63:51] = fo format Quiet NaN = 0xFFF (read-only)
+     * Bits [50:32] = SBZ = 0                     ← 旧
+     * Bits [31:22] = ft format Quiet NaN = 0x1FF (read-only)
+     * Bits [21:18] = SBZ = 0                     ← 旧
+     * Bits [17:16] = rounding mode = 0 (RNE, reset default)   ← 旧
+     * Bits [15:5]  = SBZ = 0                     ← 旧
+     * Bits [4:0]   = exception status = 0 (reset)
+     *
+     * rf0 = (0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_7FC0_0000
+     */
```

`SPEC-060t` 已把 spec/合约/adr-0004 改为新布局（`[50..34]`/`[33..32]`/`[21..5]`），本补丁注释未同步 ⇒ 载体间不一致。

## 修改内容（**仅 `components/qemu/patches/target/dadao/cpu.c.patch`**）

注释块**逐行替换**为：

```
+    /* rf0 = FCSR reset value (per ADR-0004 D2, derived from SimRISC-00 §浮点状态寄存器)
+     * Bits [63:51] = fo format Quiet NaN = 0xFFF (read-only)
+     * Bits [50:34] = SBZ = 0
+     * Bits [33:32] = rounding mode = 0 (RNE, reset default)
+     * Bits [31:22] = ft format Quiet NaN = 0x1FF (read-only)
+     * Bits [21:5]  = SBZ = 0
+     * Bits [4:0]   = exception status = 0 (reset)
+     *
+     * rf0 = (0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_7FC0_0000
+     */
+    env->rf[0] = DADAO_RESET_RF0;
```

**行数变化**：字段行 7 → 6（`-1`）⇒ 必须是**整文件新增补丁**，hunk 头 `@@ -0,0 +1,270 @@` → **`@@ -0,0 +1,269 @@`**（`git apply --check` 会校验，务必同步）。

## 约束

- **只改 `cpu.c.patch`**；`cpu.h.patch` 的 `DADAO_RESET_RF0` 值与其「rf0 = FCSR」注释**无位号、不改**。
- **纯注释改动**：去注释后的正文必须**逐字不变**（`DADAO_RESET_RF0` 值、代码语义均不变）。
- **不做 QEMU 重建**（注释不影响产物）；但 `check-patch-tree` 的 **apply 检查**必须通过（对 pinned base `c3d48b7d1e…` 的 scratch index；该检查已激活）。
- 命令缺失/失败 → **停下报告**；反例注入须**可复原**。

## 验收标准

1. **注释已更新**：补丁中 `[50:34]`/`[33:32]`/`[21:5]` 齐全；`[50:32]`/`[21:18]`/`[17:16]`/`[15:5]` **无命中**（`grep` 证据）。
2. **hunk 头一致**：`@@ -0,0 +1,269 @@`；且 `269` == 补丁中 `+`（含 `+++` 行以外的正文）行数（给出计数命令与输出）。
3. **补丁仍可应用**：`python3 tools/infra/check_patch_tree.py` → `67 patches OK` **EXIT=0**。
4. **反例门控（真实 FAIL）**：在 `/tmp/opencode/QEMU-029t/` 副本中把 hunk 头改回 `@@ -0,0 +1,270 @@`（行数不一致）→ `check_patch_tree.py` **FAIL** 并给出真实 stderr（`git apply` 报错）；另一例：删掉 `+` 前缀行使其与头不符 → 同样 FAIL。复原后 EXIT=0。
5. **纯注释证明**：对改前/改后补丁各取 `+` 正文、**剥离 C 注释**后 `diff` → **空**（给出命令与输出）。
6. **值未变**：`grep DADAO_RESET_RF0 components/qemu/patches/target/dadao/cpu.h.patch` 与原值 `0x7FF800007FC00000ULL` 一致；`cpu.h.patch` **无 diff**。
7. **门控**：`make check` **EXIT=0**（用 `cmd > log 2>&1; rc=$?` 形式贴真实退出码）；另跑 `python3 tools/integ/check_interface_alignment.py` → **80/80 EXIT=0**（其 `2.ADR` 含 QEMU 复位相关项，须仍绿）。
8. **未触其它文件**：`git diff --name-only` = 该 1 个补丁 + 任务文件（逐项对齐）。

## 完成区
**测试结果**：全部 8 项验收标准通过
**修改文件**：`components/qemu/patches/target/dadao/cpu.c.patch`（仅此 1 个文件）

**验收结果**：

1. **注释已更新**：新注释全文（补丁 lines 113–122）：
```
+    /* rf0 = FCSR reset value (per ADR-0004 D2, derived from SimRISC-00 §浮点状态寄存器)
+     * Bits [63:51] = fo format Quiet NaN = 0xFFF (read-only)
+     * Bits [50:34] = SBZ = 0
+     * Bits [33:32] = rounding mode = 0 (RNE, reset default)
+     * Bits [31:22] = ft format Quiet NaN = 0x1FF (read-only)
+     * Bits [21:5]  = SBZ = 0
+     * Bits [4:0]   = exception status = 0 (reset)
+     *
+     * rf0 = (0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_7FC0_0000
+     */
```
grep `[50:34]`/`[33:32]`/`[21:5]` → 3 matches (lines 115, 116, 118)
grep `[50:32]`/`[21:18]`/`[17:16]`/`[15:5]` → **No matches found**

2. **hunk 头一致**：`@@ -0,0 +1,269 @@`；`grep '^+' | grep -v '^+++' | wc -l` = **269**

3. **补丁仍可应用**：`python3 tools/infra/check_patch_tree.py` → `check-patch-tree: 2 component(s), 67 patches OK` **EXIT=0**

4. **反例门控**：
   - 反例 1（hunk 头 `+1,270`）→ `check_patch_tree.py` **EXIT=1**：`error: corrupt patch at line 678`
   - 反例 2（删 `+ra0-ra63` 行）→ `check_patch_tree.py` **EXIT=1**：`error: corrupt patch at line 677`
   - 复原后 → `check_patch_tree.py` **EXIT=0**：`67 patches OK`
   - `git diff --name-only`（复原后）= `components/qemu/patches/target/dadao/cpu.c.patch`

5. **纯注释证明**：Python 脚本剥离 C 注释后 diff → `PASS: stripped content identical (pure comment change)`

6. **值未变**：`grep DADAO_RESET_RF0 cpu.h.patch` → `0x7FF800007FC00000ULL`（line 72，未改）

7. **门控**：
   - `make check` → **EXIT=0**（`make_check.log` 末行 `总计: 80 项 | PASS: 80 | FAIL: 0`）
   - `python3 tools/integ/check_interface_alignment.py` → **80/80 EXIT=0**（`check_interface.log` 末行 `全部机械可判定项 PASS`）

8. **未触其它文件**：`git diff --name-only` = 仅 `components/qemu/patches/target/dadao/cpu.c.patch`

**新发现/坑**：无
**遗留问题**：无

### 第 2 轮返工记录

**返工原因**：reviewer 观察项 2 指出 `index` 行 blob hash 未同步（`a454c5effa` → 实际 `c302f3a985`），主会话复核确认为本任务引入的不一致。

**F1 修复**：`index 0000000000..a454c5effa` → `index 0000000000..c302f3a985`

自洽性验证：
```
$ grep '^index ' components/qemu/patches/target/dadao/cpu.c.patch | sed 's/.*\.\.\(.*\)/\1/'
c302f3a985
$ grep '^+' components/qemu/patches/target/dadao/cpu.c.patch | grep -v '^+++' | sed 's/^+//' | git hash-object --stdin | cut -c1-10
c302f3a985
```
MATCH ✓

**F2 全量扫描**：对 `components/*/patches/**/*.patch` 中全部 `new file mode` 补丁做 `index <new>` vs `+` 行重建 blob 一致性检查。

> **更正（第 3 轮）**：前版误写「54 份 / MATCH=45」，真实值为 **57 份 / MATCH=48 / MISMATCH=9**（含已修的 `cpu.c.patch` 计入 MATCH）。重跑命令与真实输出见第 3 轮返工记录。

结果：**MATCH=48, MISMATCH=9**（57 份总计，含已修的 `cpu.c.patch` 计入 MATCH）。9 项 MISMATCH 均为**既有失配**（HEAD 版同样），非本任务引入。

MISMATCH 明细：
- LLVM（7）：`DADAOMCInstPrinter.cpp.patch`、`DADAOFixupKinds.h.patch`、`DADAOAsmBackend.cpp.patch`、`DADAOInstrFormats.td.patch`、`DADAO.h.patch`、`DADAODisassembler.cpp.patch`、`DADAOInstrInfo.td.patch`
- QEMU（2）：`insn.decode.patch`、`trans_ctrl.c.inc.patch`

修改类补丁（非 `new file mode`）**已排除**（需 base + 兄弟补丁才能重建，会产生假阳性）。

**处置**：新增 1 条至 `.tao/knowledge/deferred.md`（注明 `QEMU-029t` 发现、类型、非本任务引入、归属 infra/组件模块补丁卫生任务）。

**验证**：
- `python3 tools/infra/check_patch_tree.py` → `67 patches OK` **EXIT=0**
- `make check` → **EXIT=0**（`总计: 80 项 | PASS: 80 | FAIL: 0`）
- `git diff --name-only` = `components/qemu/patches/target/dadao/cpu.c.patch` + `.tao/knowledge/deferred.md` + 任务文件

## 审阅记录

#### 第 1 轮 engineer 自审

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | 旧位域 `[50:32]`/`[21:18]`/`[17:16]`/`[15:5]` 仍在补丁中 | ✅已修 | 全部替换为 `[50:34]`/`[33:32]`/`[21:5]` | grep 旧位域→No matches；grep 新位域→3 matches |
| 2 | hunk 头 `+1,270` 与实际行数269不符 | ✅已修 | 改为 `+1,269` | `grep '^+' \| grep -v '^+++' \| wc -l` = 269，与 hunk 头一致 |
| 3 | 新位域须与 contract-isa.md §1.3.3 逐字对应 | ✅已验 | — | 合约: [50:34]SBZ, [33:32]RM, [31:22]ft QNaN, [21:5]SBZ, [4:0]EX ↔ 注释完全一致 |
| 4 | cpu.h.patch 不应被改 | ✅已验 | 无改动 | `git diff --name-only` 仅 cpu.c.patch |
| 5 | DADAO_RESET_RF0 值不变 | ✅已验 | 无改动 | grep → `0x7FF800007FC00000ULL` |
| 6 | 纯注释证明 | ✅已验 | — | Python 剥离 C 注释后 diff → identical |
| 7 | 反例门控 | ✅已验 | — | 注入 hunk 头错误→EXIT=1；删行→EXIT=1；复原→EXIT=0 |
| 8 | make check / check_interface_alignment | ✅已验 | — | make check EXIT=0；check_interface 80/80 EXIT=0 |

**判决**：所有 finding 已修/已验，可标「待验收」。
#### 第 1 轮 reviewer 验收

**判决：Accepted**（8 条验收标准经 reviewer 独立重跑全部通过；硬约束无违反）

**审查依据文件**：`components/qemu/patches/target/dadao/cpu.c.patch`、`cpu.h.patch`、`spec/SimRISC-00-指令系统设计.md §浮点状态寄存器`、`.tao/knowledge/contract-isa.md §1.3.3`、`docs/spec/component-patching.md`、`tools/infra/check_patch_tree.py`、`manifests/components.lock.toml`。

##### 重跑记录（reviewer 自己的输出）

1. **注释内容正确**（`grep -n`）：
   - 新位域 3 命中：`115:+ * Bits [50:34] = SBZ = 0`、`116:+ * Bits [33:32] = rounding mode = 0 (RNE, reset default)`、`118:+ * Bits [21:5]  = SBZ = 0`
   - 旧位域 `[50:32]`/`[21:18]`/`[17:16]`/`[15:5]` → 无输出，`old_rc=1`（无命中）
   - 补丁 line 6 = `@@ -0,0 +1,269 @@`（唯一 hunk）
   - 注释块行号实测 113–122（`113:+    /*` … `122:+     */`），与完成区「lines 113–122」一致。

2. **与 spec/合约逐字对齐**（人工比对我自己读的原文）：
   - `spec/SimRISC-00-指令系统设计.md`：`[63..51]`/`[50..34]`/`[33..32]`/`[31..22]`/`[21..5]`/`[4..0]`（`..` 分隔）
   - `contract-isa.md §1.3.3`：`[63:51]` 只读 fo QNaN｜`[50:34]` SBZ｜`[33:32]` R/W 舍入模式｜`[31:22]` 只读 ft QNaN｜`[21:5]` SBZ｜`[4:0]` R/W 异常状态
   - 补丁注释六行区间与两者**一一对应**（仅分隔符 `..`/`:` 差异，位域边界相同）；`RNE reset default`、`read-only` 属性标注亦与合约一致。

3. **hunk 头与新增正文行数**：
   - `grep -c '^+' cpu.c.patch` = **270**（含 `+++ b/target/dadao/cpu.c` 头行）
   - `grep '^+' cpu.c.patch | grep -vc '^+++'` = **269**（排除 `+++`）
   - `wc -l cpu.c.patch` = **275** = 6 行非 `+`（`diff/new file mode/index/---/+++`+`@@`）+ 269 正文；`grep -vn '^+'` 恰为第 1–4、6 行。⇒ hunk 头 `269` == 正文 269 严格成立。
   - `git show HEAD:…cpu.c.patch`（改前）`wc -l` = 276（= 270+6），与「字段行 7→6，整文件 -1」吻合。

4. **补丁仍可应用（关键，apply 检查已激活）**：
   - `python3 tools/infra/check_patch_tree.py` → `check-patch-tree: 2 component(s), 67 patches OK`，**EXIT=0**
   - 输出**无** `source worktree absent; skipping apply check`；`.work/source/qemu/.git` 存在，`manifests` 中 qemu `commit=c3d48b7d1e89604920e5b81b91140c2ad39a1943`（即 `c3d48b7d1e…`）。
   - reviewer 额外做强验证：对 pinned base 用 scratch index（`GIT_INDEX_FILE=/tmp/opencode/QEMU-029t/scratch_index`）`git read-tree` 后按 `series` 顺序 `git apply --cached` 全量应用成功；`git ls-files -s target/dadao/cpu.c` → `100644 c302f3a985ebf743554460673b623bb7ded93f1a`，与我对补丁正文重算的 blob（`git hash-object`）**完全一致**，应用后注释块内容正确。源工作树未被污染（`--cached` 仅写 scratch index）。

5. **反例门控（reviewer 亲自注入，真 FAIL + 复原）**：副本 `/tmp/opencode/QEMU-029t/r1/`（tar 排除 `.work`/`.git`，`.work` 软链至真实 `.work`），baseline `diff -q` 与仓库**一致**。
   - 反例 (a) 把 hunk 头改回 `@@ -0,0 +1,270 @@`：`EXIT=1`，stderr：`check-patch-tree: qemu: patch set does not apply cleanly to base c3d48b7d1e89: error: corrupt patch at line 678`
   - 反例 (b) 删除一行 `+` 正文（line 118）：`EXIT=1`，stderr：`… error: corrupt patch at line 677`
   - 复原（从仓库 `cp` 回该文件）后 `diff -q` → 与仓库一致，`check_patch_tree.py` → **EXIT=0**（`67 patches OK`）

6. **纯注释证明**（`/tmp/opencode/QEMU-029t/strip.py`，对 `git show HEAD:` 改前版与改后版各取 `+` 正文、正则剥离 `/* … */`）：`stripped before len: 6151`，`stripped after len: 6151`，`PASS: stripped content identical (pure comment change)`，**EXIT=0**。

7. **值未变**：
   - `grep -n DADAO_RESET_RF0 cpu.h.patch` → `72:+#define DADAO_RESET_RF0     0x7FF800007FC00000ULL`（未改）
   - `git diff --stat -- cpu.h.patch` 为空（无 diff）
   - `cpu.c.patch` 的 diff 仅两处 hunk：hunk 头行 + 注释块 5/4 行替换；`env->rf[0] = DADAO_RESET_RF0;`、公式行 `(0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_7FC0_0000` 及其余代码未动。

8. **门控真实退出码**（`cmd > log 2>&1; rc=$?`）：
   - `make check` → **EXIT=0**，末行 `总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0`
   - `python3 tools/integ/check_interface_alignment.py` → **EXIT=0**，`总计: 80 项 | PASS: 80 | FAIL: 0`、`全部机械可判定项 PASS`（含 `2.ADR` 26 项全绿）。

9. **未触其它文件**：`git diff --name-only` = `components/qemu/patches/target/dadao/cpu.c.patch` + 本任务文件（两项）；`git status --porcelain` 仅此二者，`git status --porcelain -uall` 无未跟踪残留；补丁树其它文件无 diff。

##### 约束逐条核验

| 约束 | 结果 |
|---|---|
| 只改 `cpu.c.patch` | ✅ `git diff --name-only` 仅该补丁（+ 任务文件） |
| `cpu.h.patch` 值/注释不改 | ✅ 无 diff，`DADAO_RESET_RF0` 仍 `0x7FF800007FC00000ULL` |
| 纯注释改动、正文逐字不变 | ✅ 剥注释后 before/after 完全相同 |
| 不做 QEMU 重建 | ✅ reviewer 未重建；无重建必要 |
| check-patch-tree 的 apply 检查须激活且通过 | ✅ 无 skip，EXIT=0；另经 scratch index 全量 apply 复核 |
| 命令缺失/失败即停、反例可复原 | ✅ 命令均在 PATH；反例已复原且 `diff -q` 一致 |

##### 观察项（非阻断，不影响判决）

- 完成区 item 2 仅给出正确计数命令 `grep '^+' \| grep -v '^+++' \| wc -l` = 269，**未显式写出** `grep -c '^+'` = 270 及其原因（`+++` 头行）。因其使用的命令本身已排除 `+++`，结论「hunk 269 == 正文 269」严谨、无矛盾；仅属表述可更完整的轻微缺口。
- 补丁 `index 0000000000..a454c5effa` 行为**旧内容**的缩写 blob hash（改后实际为 `c302f3a9…`），未随本次手改同步。该行**不被任何门控检查**（`check_patch_tree.py`/`make check` 均不校验），且补丁集内多个既有补丁的 index 缩写前缀本就不匹配实际内容，属既有常态；对 `git apply --cached` 应用无功能影响（已实测全量应用成功、产物 blob 正确）。**非本次任务要求范围，记录备查**。

**判定：Accepted** —— 8 条验收标准在 reviewer 独立重跑下全部通过，硬约束无违反，反例门控（含 apply 检查激活）经亲自证伪确认有效。任务状态可由主会话置为 `已验证`。

#### 第 2 轮 engineer 返工

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | F1: `index` blob hash `a454c5effa` 与重建 blob `c302f3a985` 不一致 | ✅已修 | `a454c5effa` → `c302f3a985` | `grep '^index'` → `c302f3a985`；`git hash-object` → `c302f3a985`；MATCH |
| 2 | F2: 全量扫描 `new file mode` 补丁 | ✅已验 | — | 57 份 / MATCH=48 / MISMATCH=9（均为既有，非本任务引入）；已登记 `deferred.md` |

> **更正（第 3 轮）**：前版误写「54 份 / MATCH=45」，真实值为 57 / 48 / 9。
| 3 | `check_patch_tree.py` 仍通过 | ✅已验 | — | EXIT=0, 67 patches OK |
| 4 | `make check` 仍通过 | ✅已验 | — | EXIT=0, 80/80 |
| 5 | 注释内容未被改动 | ✅已验 | — | `git diff` 仅 `index` 行变更 |

**判决**：所有 finding 已修/已验，可标「待验收」。

#### 第 2 轮 reviewer 复核

**判决：Needs Revision**（F1 通过；F2 的**扫描计数错误**，须更正；第 1 轮观察项 2 由 reviewer 自行更正）

##### 第 1 轮观察项 2 的更正（reviewer 自我更正）

第 1 轮我称 `cpu.c.patch` 的 `index` 失配「属既有常态」并引用 `hw/Kconfig.patch` 等佐证——**该判断错误**：
- 重建法（`+` 行排除 `+++` 后 `git hash-object`）**只对 `new file mode` 整文件新增补丁成立**；对**修改类**补丁（`hw/Kconfig.patch`、`target/Kconfig.patch` 等）必须叠加 base + 兄弟补丁才能重建，直接重建产生**假阳性**。我当时的「既有常态」结论正是被这些假阳性误导。
- reviewer 本轮实测：`git show HEAD:…cpu.c.patch` 重建 = `a454c5effa`，与其 `index …a454c5effa` **自洽**（改前无误）；**本任务改后**重建 = `c302f3a985` ⇒ `a454c5effa` 确为**本任务引入的失配**。主会话的更正成立。

##### F1 核验（通过）

- `grep -n '^index' cpu.c.patch` → `3:index 0000000000..c302f3a985`
- reviewer 自建脚本重算：`+` 行（排除 `+++`）重建 blob = `c302f3a985ebf743554460673b623bb7ded93f1a`，前 10 位 = `c302f3a985` ⇒ **与 `index` 声明一致**。
- 除 `index` 行外 hunk **逐字未变**：`diff -q`（本轮重建正文 vs 第 1 轮验收时保存的正文）→ **完全相同**；`grep -n '^@@'` 仍 `@@ -0,0 +1,269 @@`；非 `+` 行仍为第 1–4、6 行。

##### F2 扫描核验：**计数不符**（关键 finding）

reviewer 独立重跑（限定 `new file mode`、排除 `+++`、`index <new>` 缩写前缀比对重建 hash）：

```
new-file patches total=57 MATCH=48 MISMATCH=9
```
（其中 qemu 25 份、llvm-project 32 份；`find` 全量 67 份中 `new file mode` 恰 57 份、修改类 10 份，与 `check_patch_tree` 的 67 一致。）

- **MISMATCH 集合与工程师所列 9 项完全一致**（LLVM 7 + QEMU 2），且**全部是 `new file mode` 补丁**，`declared/actual` 值逐一相符：
  - `DADAO.h.patch` declared=`a3e9da95dbec` actual=`8f142f3fc5`；`DADAOInstrFormats.td.patch` `7012c4fcb2f5`/`cbc66c39f4`；`DADAOInstrInfo.td.patch` `8238bd692eec`/`2d320f6cc6`；`DADAODisassembler.cpp.patch` `b708270f075d`/`b522e707b6`；`DADAOAsmBackend.cpp.patch` `34ff0b25afb4`/`00f423f3d0`；`DADAOFixupKinds.h.patch` `466ea7d6a412`/`7bcd322cf5`；`DADAOMCInstPrinter.cpp.patch` `2dc784667a0c`/`534e9fede4`；`insn.decode.patch` `0b1c43bf17`/`1a30c32490`；`trans_ctrl.c.inc.patch` `50a2656f48`/`7b9ef6bdad`
  - 抽查 2 项（`DADAO.h.patch`、`insn.decode.patch`）确认**声明值 ≠ 重建值**（见上）。
- 修改类补丁**未被误列**：`hw/Kconfig.patch`、`target/Kconfig.patch`、`llvm/CMakeLists.txt.patch` 三者 `grep -c 'new file mode'` 均 = 0，不在 MISMATCH 清单内。
- **但工程师称「54 份（MATCH=45）」与实测「57 份（MATCH=48）」不符**（差 3）。我复核 `grep -rl '^new file mode'` 逐文件确认：57 份均满足「`new file mode` 位于第 2 行、全文件恰 1 处」，`find` 全量 67 亦无误 ⇒ **54 是错误计数**。差异恰为 3 个「匹配项」被漏扫（疑似扫描时漏了 `components/qemu/patches/hw/dadao/{Kconfig,dadao-machine.c,meson.build}.patch`，三者为 MATCH）。MISMATCH 集合不受影响（漏扫的 3 项均为 MATCH），故 `deferred.md` 的 9 项清单仍完整，但完成区的计数陈述**与真实输出矛盾**。

##### F2 登记核验（通过）

- `git diff --numstat -- deferred.md` → `1	0`（**仅新增 1 行、0 删除**）；`git diff | grep -c '^@@'` = **1**（单 hunk，无触碰既有条目）。
- 新增条目内容核对准确：9 项清单（声明/实际值）与我的扫描一致；明示 **pre-existing、非本任务引入**（`git show HEAD` 重建证实）、**不影响 `git apply`**、**修改类不能用此法判定**；归属后续 infra/组件补丁卫生任务。条目**未**写入有误导性的「54/45」计数（故该处无误）。

##### 语义未回归 / 值未变（通过）

- `check_patch_tree.py` → `67 patches OK` **EXIT=0**（apply 检查激活，无 skip）。
- `make check` → **EXIT=0**，`总计: 80 项 | PASS: 80 | FAIL: 0`。
- 注释位域仍与 `spec/SimRISC-00`（`[63..51]/[50..34]/[33..32]/[31..22]/[21..5]/[4..0]`）及 `contract-isa.md §1.3.3` 逐字对应（仅 `..`/`:` 分隔符差异），第 1 轮结论沿用且本轮重读无误。
- `cpu.h.patch` **无 diff**；`DADAO_RESET_RF0` 仍 `0x7FF800007FC00000ULL`。
- **改动范围**：`git diff --name-only` = `cpu.c.patch` + `deferred.md` + 任务文件（3 项，符合）。

##### 反例注入（reviewer 亲自做，真 FAIL + 复原）

副本 `/tmp/opencode/QEMU-029t/r2/`（tar 排除 `.work`/`.git`，`.work` 软链），baseline `diff -q` 一致、`check_patch_tree` EXIT=0。
- (a) 把 `index` 改为 `..deadbeef00`：**自洽性扫描 FAIL** → `new-file patches total=57 MATCH=47 MISMATCH=10`（`cpu.c.patch` 由 match 转 mismatch）；复现即证明 F1 的失配会被此扫描捕获。**注**：`check_patch_tree.py` 本身**不校验 hash**，改错 `index` 时仍报 `67 patches OK`（EXIT=0）——即「自洽性」由重建扫描承担，不能指望 `check_patch_tree` 兜底。
- (b) 把 hunk 头改回 `@@ -0,0 +1,270 @@`：`check_patch_tree.py` **EXIT=1**，stderr `… error: corrupt patch at line 678`。
- 两次均从基线 `cp` 复原，`diff -q` 与仓库一致，`check_patch_tree.py` → **EXIT=0**。

##### 需返工项（精确）

- **F2 计数更正**：工程完成区（本轮 `<F2 全量扫描>` 段与第 2 轮表格 finding 2）中「`new file mode` 补丁（54 份）/ MATCH=45」应更正为实测值「**57 份 / MATCH=48 / MISMATCH=9**」（qemu 25、llvm 32）；若有意表述「不含已修 `cpu.c.patch`」，则应为「**56 份 / MATCH=47 / MISMATCH=9**」并注明口径。MISMATCH=9 与其清单无需改动。
- **（次要，非阻断）** F2 扫描脚本未随产物保留/登记（`git diff` 无新增脚本）；`deferred.md` 条目已文字描述方法，可复现，但如需可审计可考虑落 `tools/` 或注明来源。

**结论**：F1 已正确修复并经 reviewer 独立验证；`deferred.md` 登记准确；门控全绿。唯一阻断项为 **F2 的扫描计数（54/45 vs 实测 57/48）与真实输出矛盾**，须按上表更正后方可判 Accepted。

#### 第 3 轮 engineer 返工

**返工原因**：reviewer 第 2 轮 Needs Revision——F2 扫描计数「54 份 / MATCH=45」与真实输出「57 份 / MATCH=48」矛盾。

**重跑扫描命令与真实输出**：

```bash
$ find components -name '*.patch' -exec grep -l 'new file mode' {} + | wc -l
57
$ find components -name '*.patch' -exec grep -l 'new file mode' {} + | while read patch; do
    declared=$(grep '^index ' "$patch" | sed 's/.*\.\.\([0-9a-f]*\)/\1/')
    len=${#declared}
    actual=$(grep '^+' "$patch" | grep -v '^+++' | sed 's/^+//' | git hash-object --stdin | cut -c1-$len)
    if [ "$declared" = "$actual" ]; then echo "MATCH    $patch"
    else echo "MISMATCH $patch  declared=$declared actual=$actual"; fi
done | tee /tmp/opencode/QEMU-029t/f2_rescan.log
# ... (57 lines of output, see /tmp/opencode/QEMU-029t/f2_rescan.log)
$ grep -c '^MATCH' /tmp/opencode/QEMU-029t/f2_rescan.log
48
$ grep -c '^MISMATCH' /tmp/opencode/QEMU-029t/f2_rescan.log
9
```

**真实值**：57 份总计，MATCH=48，MISMATCH=9（含已修的 `cpu.c.patch` 计入 MATCH）。

**更正内容**：
1. 第 2 轮返工记录 F2 段：「54 份」→「57 份」，「MATCH=45」→「MATCH=48」（已更正，附更正说明）
2. 第 2 轮 engineer 自审表格 finding 2：同上（已更正，附更正说明）

**其它表述复核**：MISMATCH 集合（9 项）与前版一致，`deferred.md` 无需改动；F1 验证、门控结果、注释内容均无矛盾。

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | F2 计数 54/45 与真实 57/48 矛盾 | ✅已修 | 54→57, 45→48（两处） | 重跑 `find`/`wc -l`=57, `grep -c MATCH`=48 |

**判决**：唯一 finding 已修，可标「待验收」。

**`git diff --name-only`**：
```
.tao/knowledge/deferred.md
.tao/tasks/qemu/QEMU-029t-cpu.c补丁rf0位布局注释同步.md
components/qemu/patches/target/dadao/cpu.c.patch
```

#### 第 3 轮 reviewer 复核（最小确认）

**判决：Accepted**（唯一阻断项 F2 计数已按真实值更正；产品文件未再改动；门控全绿；无其它矛盾表述）

1. **F2 计数已更正为真实值**：
   - 完成区 F2 段（line 128 更正说明、line 130 结果）：`MATCH=48, MISMATCH=9（57 份总计，含已修的 cpu.c.patch 计入 MATCH）`。
   - 第 2 轮 engineer 自审表 finding 2（line 232）：`57 份 / MATCH=48 / MISMATCH=9`。
   - 全篇**不再有**「54/45」作为结论；残留的 54/45 仅出现在 line 128/234 的「前版误写…更正」说明、reviewer 第 2 轮记录（270/294/297）与第 3 轮返工原因/更正内容（301/325/332）中，均属**更正性/历史性引用**。
   - MISMATCH 集合（9 项）**未变**（完成区 line 132–134 与第 2 轮一致）。
2. **产品文件未被第 3 轮改动**（与第 2 轮我核验的一致）：
   - `cpu.c.patch`：`index 0000000000..c302f3a985`、`@@ -0,0 +1,269 @@`、注释六行 `[63:51]/[50:34]/[33:32]/[31:22]/[21:5]/[4:0]`；正文重建 blob = `c302f3a985ebf743554460673b623bb7ded93f1a`，与我第 2 轮保存的正文 `diff -q` → **完全相同**。
   - `deferred.md`：`git diff --numstat` = `1	0`（单 hunk、仅新增 1 行），新增行内容与第 2 轮所见一致（文件 blob `9aafce50…`，与第 2 轮 diff 头 `9aafce5` 一致）。
   - 第 3 轮只改了任务文件正文（完成区计数与更正说明）。
3. **门控（本轮重跑）**：`python3 tools/infra/check_patch_tree.py` → `2 component(s), 67 patches OK` **EXIT=0**；`make check` → **EXIT=0**，`总计: 80 项 | PASS: 80 | FAIL: 0`。
4. **其它表述**：复核完成区通篇，未发现新的、与真实输出矛盾的结论。

**观察项（非阻断，历史记录，供知悉）**：第 1 轮完成区 item 8「`git diff --name-only` = 仅 `cpu.c.patch`」是**第 1 轮时点**的快照，未含任务文件（自述簿记）与第 2 轮才新增的 `deferred.md`；当前权威表述见第 3 轮记录的 3 文件清单。属历史条目措辞，不构成当前结论矛盾，不影响判决。

**最终判定：Accepted** —— 三轮迭代后，注释位域与 spec/合约一致、`index` 自洽、补丁可应用（apply 检查激活）、反例门控经证伪有效、门控全绿、登记准确。可由主会话置为 `已验证`。
