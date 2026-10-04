# LLVM-024t: 汇编注释符由 `#` 改为 `;`（ADR-0013 D9）

**模块**：llvm（跨 testcases / docs）
**项目里程碑**：M2
**依赖**：无（但**先于** `LLVM-025t` 与文档迁移；两者同改 `components/llvm-project/patches/**` ⇒ **串行**）
**ADR**：`ADR-0013 D9`（注释符 `#`→`;`；`#` 留给 C 预处理器；弃 `//`/`/* */`）—— 已 Accepted
**状态**：已验证

## 目标

把 DADAO 汇编行注释符由 `#` 改为 **`;`**，使 **`#` 释放给 C 预处理器**（`#include`/`#define`/`#if` 等）。**影响面必须同轮原子落地**，否则 `#` 行会被当代码报错。`//` 与 `/* */` **不采用**。

## 改动清单（原子）

1. **LLVM 补丁**：`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`
   - `CommentString = "#";` ⇒ **`";"`**（并同步该行上方注释文字）。
   - 依据：`ADR-0013 D9.1`。
2. **规范正文**：`docs/spec/assembly-language.md §2.2`
   - 改为：`;` 起至行尾为注释（`CommentString = ";"`）；**`#` 不作注释**（保留给 cpp）；**不采用** `//`、`/* … */`。
3. **全部 `.s`（`git ls-files '*.s'`）**：`tests/lit/MC/Dadao/*.s` + `tests/e2e/*.s`，**约 441 处 `#` ⇒ `;`**（含行首指令行 `# RUN:`/`# CHECK:`/`# OBJ:`/`# REQUIRES:` 等 ⇒ `; RUN:` …）。
   - ⚠️ **不要改** `tests/lit/MC/Dadao/lit.cfg.py`（那是 **Python**，其 `#` 是 Python 注释，与汇编无关 ✗）。
   - ⚠️ `#` 出现在**行尾/注释文本内**的，一并按行首注释符处理（转换后行内多余 `;` 无害 ✓）。
4. **解析 `#` 的工具**：`tools/llvm/check_lit_bytes.py` 的 `# OBJ:` 正则与字面计数 ⇒ **`; OBJ:`**；**全库 grep 穷尽**其它解析 `#` 的 llvm 工具（`tools/llvm/*.py`、`tools/testcases/*.py`）。
5. **重建 `llvm-mc`**（`make build-mc`；改 1 个 `.cpp` ⇒ **增量，秒级–1 分钟**）。

## 范围外 ✗

- **不改** cfx 相关（属 `LLVM-025t`）；
- **不改** `tests/vectors/**`、`.work/`、历史文件（`spec/SimRISC-0.5.3/`、`.tao/tasks/**` 既有、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`）；
- **不做**检测器 / 文档迁移（属 `SPEC-075t`/`SPEC-076t`）。

## 验收标准（须真实可失败）

1. **规范**：`docs/spec/assembly-language.md §2.2` 与 `ADR-0013 D9` 一致。
2. **无残留**：全库 `.s` 中**作注释的 `#` = 0（含行内）**（贴 `git grep -n '#' -- '*.s'` 输出，应为 0）。
3. **汇编通过**：`llvm-mc` 汇编全部 `.s` 成功（lit MC **22/22**、E2E **3/3**、`check_lit_bytes` 53 patterns、oracle 全过）✓。
4. **`#` 确已释放（反例，证明改动承重）** ⚠️：
   - **注入**：把 `DADAOMCAsmInfo.cpp` 的 `CommentString` 改回 `"#"`，**重建** `llvm-mc` ⇒ 用 `;` 注释的 `.s` 应**汇编失败**（`;` 不再是注释）✓；
   - **复原**：改回 `";"` + **重建**，`make check` 回 EXIT=0 ✓。
   - （须**含重建**；仅还原源码不算还原 ✗。）
5. **`;` 前缀 lit 可用**：`; RUN:`/`; CHECK:`/`; OBJ:` 能被 lit/FileCheck 正常解析（贴真实 lit 通过输出）✓。
6. **E2E lit 3/3**：`tests/e2e/*.s` 全部通过（含 `smoke_arith.s` 行内注释）✓。
7. **全量 `.s` 汇编**：正例 EXIT=0（正例 `.s` 全部汇编成功）；负例 `wpn_err_*` 按 `%not` 预期 FAIL ✓。
8. **`make check` EXIT=0**（`check-asm-list`/lit/oracle/`check-interface` 等全 PASS）✓。
9. **未越界**：`git diff --name-only` = `components/llvm-project/patches/.../DADAOMCAsmInfo.cpp.patch`、`docs/spec/assembly-language.md`、`tests/lit/MC/Dadao/*.s`、`tests/e2e/*.s`、`tools/llvm/check_lit_bytes.py`（+ 必要时其它解析 `#` 的工具）、任务书；历史文件干净 ✓。
10. 命令缺失/失败 ⇒ **停下报告** ✗。

## 完成区（第 2 轮返工后）

**测试结果**：lit MC 22/22 PASS；E2E 3/3 PASS；check_lit_bytes 53 patterns OK；oracle 全过；`make check` EXIT=0（80/80 PASS）

**修改文件**（含 `.s` 计数）：
- `components/llvm-project/patches/.../DADAOMCAsmInfo.cpp.patch`（`CommentString = "#"` → `";"`）
- `docs/spec/assembly-language.md`（§2.2 注释说明更新 + §9 非法记号示例移除 `;`）
- 25 × `.s`（`tests/e2e/*.s` 3 个 + `tests/lit/MC/Dadao/*.s` 22 个，共 443 处 `#` → `;`，含行内注释）
- `tools/llvm/check_lit_bytes.py`（正则 + 文档字符串 `# OBJ:` → `; OBJ:`）
- `tools/llvm/test_encoding_oracle.py`（`'# OBJ:'` → `'; OBJ:'`）
- `tools/integ/check_interface_alignment.py`（正则 + 注释 `# OBJ:` → `; OBJ:`）
- 合计 30 files changed, 464 insertions(+), 464 deletions(-)

**`#` 残留 grep（应为 0）**：`git grep -n '#' -- '*.s'` = 0 ✓（含行内扫描）

**注入/复原证据（含重建）**：
1. **注入**：将 `.work/source/.../DADAOMCAsmInfo.cpp` 的 `CommentString` 改回 `"#"` → `make build-mc`（4 targets）→ `llvm-lit` 结果：**21/25 FAIL**（84%），证明 `;` 注释的 `.s` 在 `#` 模式下汇编失败 ✓
2. **复原**：改回 `";"` → `make build-mc` → `llvm-lit` 结果：**25/25 PASS**（100%）；`make check` **EXIT=0**（80/80 PASS）✓
3. 注入后 `git diff --name-only`（注入期间）= 仅 `DADAOMCAsmInfo.cpp`（.work 内，非 git 跟踪）；复原后工作区干净

**`make check` 与 lit 真实退出码**：
- `llvm-lit tests/lit/MC/Dadao/ -v`：22/22 PASS
- `llvm-lit tests/lit/E2E/ -v`：3/3 PASS
- 全量 25 个 `.s` 逐个 `llvm-mc` 汇编：22 正例 EXIT=0，3 负例 `wpn_err_*` EXIT=1（预期）
- `python3 tools/llvm/check_lit_bytes.py --min-obj 53`：53 patterns OK，EXIT=0
- `make check`：EXIT=0，80/80 PASS

**`git diff --name-only`**：仅预期文件（30 个），未越界 ✓；`lit.cfg.py` 未修改 ✓

**新发现/坑**：
- 第 1 轮只用 `git grep -nE '^\s*#'`（行首）扫描遗漏了行内注释（`smoke_arith.s:15-16`），教训：改注释符必须全量 `git grep -n '#'` 不限行首。
- `docs/spec/assembly-language.md §9` 的 `;` 非法记号示例与 §2.2 矛盾，本轮已修正（`#` 替代 `;` 作示例）。

**遗留问题**：无

## 审阅记录

#### 第 1 轮 engineer 自审

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | §9 诊断中 `;` 仍列为非法记号，与更新后 §2.2 矛盾 | ⏸延后 | 未改（任务范围仅 §2.2） | 任务书改动清单仅列 §2.2；§9 清理属 SPEC-075t/076t |
| 2 | `check_interface_alignment.py` 注释中 `# OBJ:` 需同步更新 | ✅已修 | 注释 2 处 + 正则 1 处 `#` → `;` | `grep 'OBJ:' tools/integ/check_interface_alignment.py` 全部为 `; OBJ:` |
| 3 | 反例注入后需确认 `.work/source/` 还原干净 | ✅已修 | 复原 `CommentString = ";"` + 重建 | `llvm-lit` 22/22 PASS + `make check` EXIT=0 |

全部 finding 已处置，标「待验收」。

#### 第 1 轮 reviewer 验收

**结论：Needs Revision**（验收标准 3 不满足：`tests/e2e/smoke_arith.s` 汇编失败；且存在 `.s` 残留 `#` 与 §9 自相矛盾）。

**审查范围**：任务书、`git diff` 全量、5 处原子改动、`.s` 全量汇编扫描、lit MC + E2E、`check_lit_bytes`、oracle、`make check`；**亲自注入反例并重建**（`.work/source` 内改 `CommentString` → `make build-mc`）。

##### 一、重跑记录（真实输出 / 退出码）

| # | 命令 | 真实结果 |
|---|------|---------|
| R1 | `llvm-lit tests/lit/MC/Dadao/ -v` | **EXIT=0**，`Passed: 22 (100.00%)` ✓ |
| R2 | `python3 tools/llvm/check_lit_bytes.py --min-obj 53` | **EXIT=0**，`check_lit_bytes: 53 patterns OK` ✓ |
| R3 | `python3 tools/llvm/test_encoding_oracle.py` | **EXIT=0**，`61 passed, 0 failed`；`Cross-check OK: oracle tests (61) >= lit OBJ lines (53)` ✓ |
| R4 | `JOBS=8 make check` | **EXIT=0**，`总计: 80 项 | PASS: 80 | FAIL: 0`；`repository checks: PASS` ✓ |
| R5 | `git grep -nE '^\s*#' -- '*.s'; echo $?` | 无匹配，**EXIT=1**（行首 `#` = 0 ✓） |
| R6 | `.work/build/llvm/bin/llvm-lit tests/lit/E2E/ ` | **EXIT=1**，`Passed: 2 (66.67%)，Failed: 1 (33.33%)`，`FAIL: DADAO-E2E :: smoke_arith.test` ✗ |
| R7 | `llvm-mc --triple=dadao-unknown-elf -filetype=obj tests/e2e/smoke_arith.s` | **EXIT=1**，stderr：`smoke_arith.s:15:34: error: unexpected token at start of statement`、`:16:34` 同上 ✗ |
| R8 | 全量 25 个 `.s` 逐个 `llvm-mc` 汇编 | **4 个 FAIL**：`smoke_arith.s`（真实回归）+ `wpn_err_foo/range/wp4.s`（**负向测试**，`; RUN: %not %llvm_mc`，预期失败，非缺陷） |
| R9 | `git diff --name-only` | 30 个文件（补丁+docs+25×.s+3×py），**未越界** ✓；`lit.cfg.py` 未改 ✓ |

##### 二、五处原子改动核验

| 改动 | 核验 | 结论 |
|------|------|------|
| ① 补丁 `CommentString "#"→";"` | `git diff` 确认 `+  CommentString = ";";`，上方注释文字同步 | ✓ |
| ② `assembly-language.md §2.2` | 改为 `;` 注释 / `#` 留给 cpp / 不采用 `//`·`/* */` | ✓ |
| ③ 全部 `.s` | 原 HEAD 共 **443** 个 `#`，现存 **2**（均在 `smoke_arith.s`），已转 **441** = 工程师所述；但 **2 处漏转** ✗ | ✗（不完整） |
| ④ 解析 `#` 的工具 | `check_lit_bytes.py`（正则+字面计数+docstring）、`test_encoding_oracle.py`、`check_interface_alignment.py`（正则+注释）均改 `;` | ✓ |
| ⑤ 重建 `llvm-mc` | 基线 sha `1d2ccafc…f12372`（mtime 2026-10-02 10:41），工作正常 | ✓ |

**④ 补充穷尽**：全库 grep 其它 `#` 解析工具（`tools/**/*.py`）只命中 `validate_decodetree.py`/`test_m1_asm.py`/`apply_series.py`/`check_patch_tree.py`，均为 **Python 语法注释**（`startswith('#')`），与汇编注释符无关，未改**正确** ✓。

##### 三、反例承重（reviewer 亲自注入 + 重建）

- **基线**：源码 `CommentString = ";"`，二进制 sha `1d2ccafc…f12372`，lit 22/22。
- **注入**：`.work/source/.../DADAOMCAsmInfo.cpp` 改回 `"#"` → `JOBS=8 make build-mc`（**EXIT=0**，ninja 重建 4 目标）→ 二进制 sha 变为 `6460218a…c0caff3`（**证明重编译真实生效**）。
  - `llvm-lit tests/lit/MC/Dadao/` → **EXIT=1，18/22 FAIL（81.82%）**；`rrrr.s:1:8: error: unexpected token at start of statement ; RUN:…`，`; RUN:` 被当代码 ⇒ **`;` 注释的有效性承重于 CommentString 改动** ✓
- **复原**：`cp` 回备份源码（`diff` 确认与备份逐字节相同）→ `make build-mc`（EXIT=0）→ 二进制 sha **`1d2ccafc…f12372`，与基线 byte-identical** ✓；`llvm-lit` **EXIT=0，22/22 PASS（回绿）** ✓。
- 反例注入**可复原且含重建**，工作区 `git status` 恢复为原 30 文件 + 任务书（`.work` 不入 git）。

##### 四、§9 自相矛盾判定（**阻断项**）

- **矛盾属实**：`docs/spec/assembly-language.md:204` 仍写 `- 非法记号（如 \`;\`、\`wp4\`）。`，与更新后 §2.2「`;` 起至行尾为注释」**同一文件、同一规范性文档内直接对立**。
- **判定：本任务阻断项**，依据：
  1. 同一文件、同一规范（§9 为 **MUST** 级规范性诊断清单），`;` 不可能同时是「注释符」与「非法记号」；保留即交付一份自相矛盾的规范。
  2. 任务书目标「`;` 起至行尾为注释……影响面**必须同轮原子落地**」——§9 属该注释符改动的直接语义面，非「检测器/文档迁移」（任务书 `范围外` 仅排除这两类）。
  3. 工程师所指「后续任务 SPEC-075t/076t」**在 `.tao/tasks/` 中并不存在**（`ls` 确认无 075/076），延后**无实际归属**，属悬挂矛盾。
  4. 修复成本为**一行**（`;` 从非法记号示例中移除，或改为真正非法记号如 `$`）。
- 备注：ADR-0013 D9.5 枚举的原子面**未列 §9**，若架构师显式将其拆到某个**已存在的**后续任务并登记，则可降为「非阻断」；但当前无该任务，故判阻断，请架构师定夺。

##### 五、完成区逐条复读

| 完成区声明 | 真实核对 | 结论 |
|-----------|---------|------|
| lit 22/22 PASS | R1 EXIT=0，22/22 | 一致 ✓ |
| check_lit_bytes 53 patterns OK | R2 EXIT=0，53 | 一致 ✓ |
| `make check` EXIT=0（80/80 PASS） | R4 EXIT=0，80/80 | 一致 ✓ |
| 25 × `.s`，共 441 处 `#`→`;` | 443 原 `#` − 2 残留 = 441 | 数字真实，但 **遗留 2 处应转未转** ✗ |
| `git grep -nE '^\s*#' -- '*.s'` = 0 | R5 EXIT=1，0 匹配 | 一致 ✓（但见下） |
| 注入 18/22 FAIL、复原 22/22 + make check EXIT=0 | 我方独立复现一致（§三） | 一致 ✓ |
| §9 矛盾「属后续任务」 | 矛盾属实；延后目标任务不存在 | **不成立** ✗ |
| 遗留问题：无 | 实有 2 处残留 `#` + §9 矛盾 | ✗ |

##### 六、判据汇总

- 验收标准 3「**汇编全部 `.s` 成功**」**不满足**：`smoke_arith.s`（正例 E2E）EXIT=1，E2E lit 2/3。
- 改动清单第 3 条「`#` 出现在行尾/注释文本内的，一并按行首注释符处理」**未完整执行**（漏 2 处，恰是导致汇编失败的行）。
- 验收标准 7（未越界）、2（行首 `#`=0）、5（`; RUN:`/`; CHECK:`/`; OBJ:` 可解析，由 R1 22/22 + R2 53 patterns 证明）、6（`make check` EXIT=0）**满足**。
- **注意**：任务书列出的验收命令（lit MC 22/22、check_lit_bytes、oracle、`make check`）**均不覆盖 `tests/e2e/*.s`**，故工程师全绿结果未暴露该回归——属覆盖盲区，非造假。

##### 七、返工要求（Needs Revision）

1. `tests/e2e/smoke_arith.s:15-16` 行内 `# …` ⇒ `; …`（按任务书第 3 条「行尾/注释文本内一并处理」）；复验：`llvm-mc` 汇编 `smoke_arith.s` EXIT=0、`llvm-lit tests/lit/E2E/` **3/3 PASS**（当前 2/3）。
2. 判定并处置 §9:204 与 §2.2 的矛盾（建议本任务内一行修正，见 §四）。
3. 复验后须含：`.s` 全量 `llvm-mc` 汇编（正例 EXIT=0、负例 wpn_err 预期 FAIL）、lit MC 22/22 + E2E 3/3、`make check` EXIT=0。

**证据留档**：`/tmp/opencode/LLVM-024t-r1/`（含基线/注入/复原 sha、lit 日志、E2E 日志、make check 日志）。

#### 第 2 轮 engineer 迥工

**返工项处置**：

| # | 返工要求 | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | `smoke_arith.s:15-16` 行内 `#` 漏改 | ✅已修 | `# rb3[47:32]…` → `; rb3[47:32]…`（2 处） | `llvm-mc` EXIT=0 + `llvm-lit tests/lit/E2E/` 3/3 PASS |
| 2 | §9:204 `;` 作非法记号示例与 §2.2 矛盾 | ✅已修 | `非法记号（如 `;`、`wp4`）` → `非法记号（如 `#`、`wp4`）` | `git grep ';.*wp4' docs/spec/assembly-language.md` = 0 |
| 3 | 验收口径：行首 → 含行内 + E2E 3/3 + 全量汇编 | ✅已修 | 任务书验收标准 2/3/5-10 已更新 | 见任务书改动 |

**全量扫描**：`git grep -n '#' -- '*.s'` = 0（不限行首，含行内），443 处 `#` 全部转为 `;` ✓

**复验**：
- `llvm-lit tests/lit/MC/Dadao/ -v`：22/22 PASS
- `llvm-lit tests/lit/E2E/ -v`：3/3 PASS
- 全量 25 个 `.s` 逐个 `llvm-mc` 汇编：22 正例 EXIT=0，3 负例 `wpn_err_*` EXIT=1（预期）
- `check_lit_bytes --min-obj 53`：53 patterns OK
- `make check`：EXIT=0，80/80 PASS

**反例承重**：
- 注入 `CommentString` 改回 `"#"` + 重建 → 21/25 FAIL（含 E2E `smoke_arith.test`）
- 复原 `";"` + 重建 → 25/25 PASS + `make check` EXIT=0

自审无新 finding，标「待验收」。

#### 第 2 轮 reviewer 复核

审判范围：任务书全量、`git diff` 全量、`.s` 全库扫描、lit MC/E2E、全量 `.s` 汇编、`check_lit_bytes`/oracle、`make check`；**亲自注入 `CommentString` 反例 + 重建 + 复原 + 重建**；独立复核 §9 语义。证据留档 `/tmp/opencode/LLVM-024t-r2/`。

##### 一、重跑记录（我方真实输出 / 退出码）

| # | 命令 | 真实结果 |
|---|------|---------|
| R1 | `git grep -n '#' -- '*.s'; echo $?` | 无匹配，**EXIT=1** ⇒ `.s` 任意位置 `#` = 0 ✓ |
| R2 | `find . -name '*.s'`（去 `.work/.cache/.git`） | 恰 25 个，`grep -rn '#'` 无命中（EXIT=1）✓ |
| R3 | `llvm-lit tests/lit/MC/Dadao/ -v` | **EXIT=0**，`Passed: 22 (100.00%)` ✓ |
| R4 | `llvm-lit tests/lit/E2E/ -v` | **EXIT=0**，`Passed: 3 (100.00%)`（含 `smoke_arith.test`）✓ |
| R5 | `llvm-mc --triple=dadao-unknown-elf -filetype=obj tests/e2e/smoke_arith.s` | **EXIT=0**（第 1 轮该文件 EXIT=1 的回归已消）✓ |
| R6 | 全量 25 个 `.s` 逐个 `llvm-mc -filetype=obj` | 22 正例 **EXIT=0**；3 负例 `wpn_err_{foo,range,wp4}.s` **EXIT=1**（预期 FAIL）✓ |
| R7 | `python3 tools/llvm/check_lit_bytes.py --min-obj 53` | **EXIT=0**，`check_lit_bytes: 53 patterns OK` ✓ |
| R8 | `python3 tools/llvm/test_encoding_oracle.py` | **EXIT=0**，`61 passed, 0 failed`；`Cross-check OK` ✓ |
| R9 | `JOBS=8 make check`（基线二进制） | **EXIT=0**，`总计: 80 项 | PASS: 80 | FAIL: 0`；`repository checks: PASS` ✓ |
| R10 | `git diff --name-only` | **30** 个文件（补丁+docs+25×.s+3×py），无越界；`lit.cfg.py` 未改；历史文件（`spec/SimRISC-0.5.3/`、`docs/m1-retrospective.md`、`docs/testcases-009t-audit.md`、`.tao/tasks/**` 既有）干净 ✓ |
| R11 | `git diff -U0 -- '*.s'` 统计 | 删含 `#` 行 **443**、增含 `;` 行 **443**（与任务书 443 一致）✓ |

##### 二、承重反例（reviewer 亲自注入 + 重建，含复原重建）

- **基线二进制 sha256** = `1d2ccafc…f12372`（`CommentString = ";"`）。
- **注入**：`.work/source/.../DADAOMCAsmInfo.cpp` 的 `CommentString = ";"` → `"#"`（`diff` 确认仅此一行变），`JOBS=8 make build-mc` **EXIT=0**（ninja 重建 4 目标，13s）→ 二进制 sha 变为 **`6460218a…c0caff3`**（证明重编译真实生效）。
  - `llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/ -v` → **EXIT=1，Failed: 21 (84.00%) / Passed: 4**；`smoke_arith.s:1:16: error: unrecognized instruction mnemonic`、`; smoke_arith:…` 被当代码 ⇒ **`;` 注释的有效性承重于 `CommentString` 改动** ✓
- **复原**：`cp` 回备份源码（`cmp` 逐字节相同）→ `make build-mc` **EXIT=0**（13s）→ 二进制 sha 回到 **`1d2ccafc…f12372`，与基线 byte-identical** ✓；`llvm-lit tests/lit/MC/Dadao/ tests/lit/E2E/` **EXIT=0，25/25 PASS（回绿）** ✓；`JOBS=8 make check` **EXIT=0，80/80** ✓。
- 复原后 `git status`：仍为原 30 个跟踪文件 + 任务书，`.work` 不入 git ⇒ 工作区未污染 ✓。

##### 三、验收标准逐条核验

| 验收项 | 结论 |
|--------|------|
| 1. §2.2 与 ADR-0013 D9 一致 | ✓（`;` 注释 / `#` 留给 cpp / 不采用 `//`·`/* */`，与 D9.1–D9.3 逐条对应） |
| 2. `.s` 含行内 `#` = 0 | ✓（R1/R2） |
| 3. 汇编全部 `.s` 成功（lit 22/22、E2E 3/3、53 patterns、oracle） | ✓（R3/R4/R6/R7/R8） |
| 4. 反例承重（注入+重建 ⇒ FAIL；复原+重建 ⇒ 回绿） | ✓（§二，独立复现） |
| 5. `; RUN:`/`; CHECK:`/`; OBJ:` 可被 lit/FileCheck 解析 | ✓（R3 22/22 + R7 53 patterns；另核 `triple-smoke.s`/`e_flags.s` 首行 `; RUN:`） |
| 6. E2E 3/3（含 `smoke_arith.s` 行内注释） | ✓（R4；`smoke_arith.s:15-16,18` 行内 `;` 已生效） |
| 7. 全量 `.s`：正例 EXIT=0 / 负例 `wpn_err_*` 预期 FAIL | ✓（R6：22/3） |
| 8. `make check` EXIT=0 | ✓（R9/R10 两次真实 EXIT=0，80/80） |
| 9. 未越界、`lit.cfg.py` 未动、历史文件干净 | ✓（R10） |
| 10. 命令失败即停 | ✓（无命令缺失） |

##### 四、§9 语义判定（用户点名项）

- **直接矛盾已消解**：`assembly-language.md:204` 现为 `非法记号（如 \`#\`、\`wp4\`）`，不再把 `;` 列为非法记号，与 §2.2「`;` 起至行尾为注释」不再对立 ✓。
- **作为非法记号示例成立**：`#` 不属于本规范任何合法记号类；实测行内 `add.si rd8, 1 # trailing` → `error: unexpected token at start of statement`（EXIT=1）⇒ 「作为记号的 `#` 非法」可成立。
- **与 §2.2 不构成逻辑矛盾**：§2.2 陈述「`#` 不作注释、留给 cpp」，§9 陈述「汇编器遇到作为记号/操作数的 `#` 报错」；两阶段（预处理器 / 汇编器）分属，可同真。
- **⚠️ 非阻断观察（供架构师定夺，不在本任务验收项内）**：`#` 并非**无条件非法**——我方实测当前构建下**行首 `#` 被静默吞掉**：`# foo bar`、`#include "x.h"`、`# 123 "str"` 均 **EXIT=0**（根因：LLVM `MCAsmInfo::AllowAdditionalComments` 默认 `true`，`AsmLexer.cpp:821-838` 将行首 `#` 当附加注释 / hash directive）。即只有**行内/操作数位置**的 `#` 报错。对比：`@`/`` ` ``/`$`/`%` 行首均 `EXIT=1`（真非法）。故 `#` 恰是唯一「行首不非法」的候选，且它是 cpp 层记号，作为**纯汇编**「非法记号」示例略显跨层。
  - 结论：**语义可接受、非阻断**；建议（后续任务，非本任务返工）把示例改为跨层无歧义的记号（如 `@`），或加限定「行内位置的 `#`」。本任务验收标准 1–10 不含 §9 措辞精度，故不据此判返工。

##### 五、判决

**Accepted（工程师达标）**。

- 第 1 轮两个阻断项均已消解：①`smoke_arith.s` 行内 `#` 转 `;`，直跑 `llvm-mc` 与 E2E lit 均 EXIT=0；②§9:204 的 `;` 非法记号示例已改为 `#`，与 §2.2 的直接对立消除。
- 验收标准 1–10 **在审查者独立重跑下全部通过**；`git grep` 全量 `.s` `#`=0；反例注入+重建 21/25 FAIL、复原+重建 25/25 回绿且二进制 sha 与基线 byte-identical。
- 无越界、`lit.cfg.py` 未动、历史文件干净。
- 唯一遗留为**非阻断**文档措辞观察（§四），已具名交给架构师终审定夺。

**证据留档**：`/tmp/opencode/LLVM-024t-r2/`（`lit-mc.log`、`lit-e2e.log`、`asm-all.log`、`check_lit_bytes.log`、`oracle.log`、`make-check.log`、`lit-inject.log`、`lit-restore.log`、`make-check-restore.log`、`build-inject.log`、`build-restore.log`、`DADAOMCAsmInfo.cpp.bak`）。


#### 主会话收尾（2026-10-02）

1. **提交推送**：注释符 `#`→`;`（补丁 + §2.2 + 443 处 `.s` + 3 个检查器 + 重建）（见 git log）。
2. **过程**：reviewer 第 1 轮 Needs Revision —— ① `tests/e2e/smoke_arith.s` **行内** `#` 漏改致 E2E 2/3 回归（我的任务书验收口径过窄，只查**行首** `#` ✗）；② `assembly-language.md:204` 与 §2.2 对立 → 返工 → 第 2 轮 **Accepted**（E2E 3/3、全量 25 `.s` 正确、注入+重建承重 byte-identical）。
3. **非阻断观察**（已登记 `deferred.md`）：`#` **行首**仍被静默当注释（`AllowAdditionalComments` 默认 true）；"释放 `#`"不彻底 ⇒ 建议后续 `DADAOMCAsmInfo` 设 `AllowAdditionalComments = false` + §9 示例改 `@`/加"行内位置"限定。
4. **教训**：验收口径须用**语义口径**（"作注释的 `#` = 0"）而非"正则可枚举"（`^\s*#`）；且 `lit MC` 与 `make check` **均不覆盖 `tests/e2e/*.s`** ⇒ 属门控盲区（归 `INFRA-021t` 考虑纳入）。
