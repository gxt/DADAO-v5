# INTEG-005t: `check_interface_alignment` 同类缺陷修复（非递归 glob → 递归 + 空补丁集硬错误）

**模块**：integ
**项目里程碑**：M1→M2（过渡期任务，见 `.tao/README.md` 与 `.tao/knowledge/milestones.md`）
**依赖**：`INTEG-003t`（本脚本的产出任务，已验证）；参照 `QEMU-024t`（**同类缺陷的先例修复**）
**状态**：已验证
**上游发现**：`QEMU-024t` 第 1 轮 reviewer 主动证伪时发现（2026-09-25），主会话独立复核确认
**来源登记**：`.tao/knowledge/deferred.md`（`llvm / qemu / integ` 节，「`tools/integ/check_interface_alignment.py` 同类缺陷」条）

## 执行环境

**执行环境**：本地

## 背景（已实测确认）

**上游事件**：2026-09-23 组件补丁集重整（`ADR-0002 D4` rev.）——`components/<name>/patches/` 由**扁平** `NNNN-*.patch` 改为**树形** `<上游相对路径>.patch`（补丁进入子目录）。形态见 `docs/spec/component-patching.md` §2。

**缺陷**：`tools/integ/check_interface_alignment.py` 有 **3 处非递归 glob**，均扫 `components/<name>/patches/`：

| 行 | 位置 | 作用 |
|---|---|---|
| L70 | `check_elf_fields()` | 拼 LLVM 补丁全文 → 校验 ELF 字段 |
| L209 | `check_adr_alignment()` | 拼 QEMU 补丁全文 → 校验 ADR-0003/0004 常量 |
| L654 | `check_qemu_trans()` | 统计 QEMU 补丁中 `trans_*` 定义数 |

三处均写作 `glob.glob(os.path.join(patches_dir, "*.patch"))`，树形化后命中 **0** 份文件 ⇒ 拼接内容为空 ⇒ 依赖补丁内容的断言全部 FAIL。

**实测影响**（2026-09-25，主会话复核）：

```
$ python3 tools/integ/check_interface_alignment.py
总计: 80 项 | PASS: 57 | FAIL: 23 | MANUAL: 0
  1.ELF: 5 项 (PASS=0 FAIL=5)
  2.ADR: 26 项 (PASS=9 FAIL=17)
  3.Schema: 41 项 (PASS=41 FAIL=0)
  4.Opcodes: 8 项 (PASS=7 FAIL=1)
EXIT=1
```

- **23 FAIL = 5（ELF）+ 17（ADR）+ 1（trans_* 定义数）**，**全部**源于上述 3 处空扫描；
- `4.Opcodes` 的 `LLVM lit # OBJ: patterns`（L635，扫 `tests/lit/MC/Dadao/*.s`）**不受影响**（该目录为平铺，非补丁树）；
- **与 `QEMU-024t` 同类**：均为 2026-09-23 重整引入的**静默回归**。

**影响面**：`INTEG-003t` 的验收记录「80 项 0 FAIL，EXIT 0」与 `MEMORY.md` 的「80/80/0」**已不成立**。该脚本**不在** `make check` 内（`Makefile:122` 的 `check` 目标不含它），故不阻断门控；但它是 `INTEG-003t`（M1 接口对齐）的**唯一机械证据**，其失效意味着「跨模块接口对齐」目前**无有效门控**。

## 目标

1. 三处扫描改为**递归**，使树形补丁集下能读到全部补丁；
2. **空补丁集硬错误**：扫描到 0 份补丁时以**明确错误**非零退出（`无法校验` ≠ `校验失败`），避免把「扫描失效」误报成 23 个接口违约。

## 接口规范

- 输入：`tools/integ/check_interface_alignment.py`（`check_elf_fields()` / `check_adr_alignment()` / `check_qemu_trans()` 中的 glob）
- 输出：`tools/integ/check_interface_alignment.py`（3 处递归 glob + 空集硬错误）
- **约束（关键，防「改测试以通过」）**：
  - **不得**改动任何 `EXPECTED_*` 期望值（`EXPECTED_LIT = 53`、`EXPECTED_TRANS = 256`、`e_flags`/`EM_DADAO`/地址常量等）；
  - **不得**删除、跳过或弱化任何断言；**不得**把 FAIL 降级为 SKIP/MANUAL；
  - **不得**改 `docs/integ-interface-alignment.md` 的期望表以迁就实现；
  - 恢复 80/80 **必须**来自「真的读到补丁」，**不得**来自放宽判据；
  - L635 的 `tests/lit/MC/Dadao/*.s` glob **不动**（该目录平铺，非缺陷）；
  - 不改 `docs/spec/component-patching.md`；不改 `components/` 下任何补丁；
  - 本脚本不在 `make check` 内；改动不得使 `make check` 变红。

## 交付物

- `tools/integ/check_interface_alignment.py`：3 处递归 glob + 空补丁集硬错误
- 完成区附：改前/改后对照（23 FAIL → 0 FAIL 的逐类分解）、反例门控真实输出、`make check` 结果

## 关键概念 / 数据

**「递归」的正确取法**（与 `QEMU-024t` 一致，保持单一实现）：`glob.glob(os.path.join(d, "**", "*.patch"), recursive=True)`。若三处重复，可提取一个 helper（如 `iter_patch_files(patches_dir)`）以符合 DRY——**但须保持三处行为一致**。

**「空补丁集」的判定**：三处各自的目录若一份补丁都没扫到，即为**环境/路径失效**，应 `raise SystemExit(...)` 或以明确 ERROR 退出，**不得**继续产出「未找到 X」的 23 个 FAIL（那是误导性诊断）。

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 三处 glob 改为递归；树形 `patches/` 下分别扫到 LLVM **36** / QEMU **31** 份补丁（与 `rglob` 交叉核对一致） | 现在可跑 | 计数脚本 |
| 2 | **`python3 tools/integ/check_interface_alignment.py` → `总计: 80 项 | PASS: 80 | FAIL: 0`，EXIT 0** | 现在可跑 | 真实输出 |
| 3 | **改前基线复现**：HEAD 版脚本报 `PASS: 57 / FAIL: 23`、EXIT 1；且 23 FAIL 与本文「背景」逐条一致 | 现在可跑 | `git show HEAD:…` 到临时树运行 |
| 4 | **空补丁集硬错误**：`patches_dir` 指向空目录（或临时改名）→ 明确 ERROR 非零退出，**不**产出 23 个误导性 FAIL | 现在可跑 | 反例门控 |
| 5 | **零期望值改动**：`git diff` 中不出现 `EXPECTED_LIT`/`EXPECTED_TRANS`/`0x0DA0`/`0x00000001`/地址常量等期望值的变更 | 现在可跑 | `git diff` 逐行核对 |
| 6 | **零断言删减**：断言总数仍为 **80**（`总计: 80 项`），无 SKIP/MANUAL 新增 | 现在可跑 | 输出 + diff |
| 7 | **反例门控**：回退递归（→ 23 FAIL 重现）与删去空集硬错误（→ 空目录下产出误导 FAIL）各自注入并确认；注入须 `git diff --name-only` 非空；**还原**后复跑 80/80 | 现在可跑 | 反例注入真实输出 |
| 8 | L635 的 lit glob 未改；未改 `components/`、`docs/integ-interface-alignment.md`、`docs/spec/component-patching.md` | 现在可跑 | `git diff --stat` |
| 9 | `make check` EXIT 0 | 现在可跑 | 完整输出 |
| 10 | 收尾同步：`docs/integ-interface-alignment.md` 若含「运行方式/计数」描述须与新行为一致（**不改期望表**） | 现在可跑 | diff |

## 完成区

**测试结果**：验收 #1~#10 全部通过（详见下方逐条结果表）

**修改文件**：
- `tools/integ/check_interface_alignment.py`（1 文件，+11 行 / -3 行）

**逐行改动说明**：

| 改动 | 位置 | 说明 |
|------|------|------|
| 新增 `iter_patch_files()` helper | L37-L42 | 递归 glob `**/*.patch` + 空集 `SystemExit` 硬错误 |
| L70 → L78 | `check_elf_fields()` | `sorted(glob.glob(…, "*.patch"))` → `iter_patch_files(patches_dir)` |
| L209 → L217 | `check_adr_alignment()` | 同上 |
| L654 → L662 | `check_opcodes_cross()` | `sorted(glob.glob(…, "*.patch"))` → `iter_patch_files(qemu_patches_dir)` |

**验收结果**（逐条真实输出）：

| # | 验收项 | 结果 | 输出摘要 | 日志 |
|---|--------|------|---------|------|
| 1 | 递归 glob 计数 | ✅ PASS | LLVM 36 份 / QEMU 31 份（`find … -name "*.patch" \| wc -l` 交叉核对一致） | — |
| 2 | 改后 80/80 EXIT 0 | ✅ PASS | `总计: 80 项 \| PASS: 80 \| FAIL: 0 \| MANUAL: 0`，EXIT 0 | `INTEG-005t-check_post.log` |
| 3 | 改前基线复现 | ✅ PASS | HEAD 版：`总计: 80 项 \| PASS: 57 \| FAIL: 23`，EXIT 1；23 FAIL = 5(ELF)+17(ADR)+1(trans_*) | `INTEG-005t-check_pre.log`（**已重采**，见下 N1） |
| 4 | 空补丁集硬错误 | ✅ PASS | `ERROR: …/patches 下未找到任何 .patch 文件（空补丁集，无法校验）`，EXIT 1 | — |
| 5 | 零期望值改动 | ✅ PASS | `git diff` 中无 `EXPECTED_LIT`/`EXPECTED_TRANS`/`0x0DA0`/`0x00000001`/地址常量变更 | `INTEG-005t-git_diff.log` |
| 6 | 零断言删减 | ✅ PASS | `总计: 80 项`，无 SKIP/MANUAL 新增 | 同 #2 |
| 7 | 反例门控 | ✅ PASS | 注入 #1（回退递归）→ ERROR+EXIT 1；注入 #2（删空集硬错误）→ 56 PASS / 24 FAIL 误导性诊断；还原后 80/80 | — |
| 8 | L635 lit glob 未改 | ✅ PASS | `git diff` 无 lit/Dadao 相关变更；仅 `tools/integ/check_interface_alignment.py` 1 文件改动 | `INTEG-005t-git_diff.log` |
| 9 | `make check` EXIT 0 | ✅ PASS | `check-patch-tree: 2 component(s), 67 patches OK`；`repository checks: PASS`；EXIT 0 | `INTEG-005t-make_check.log` |
| 10 | docs 同步 | ✅ PASS | `docs/integ-interface-alignment.md` 无「运行方式/计数」描述需更新；`git diff` 无该文件变更 | — |

**反例门控详情**：

**注入 #1 — 回退递归（验证非递归 glob 确实是根因）**：
- 注入方式：在仓库文件上 `sed` 把 `iter_patch_files` 中的 `**/*.patch` 改回 `*.patch`
- `git diff --name-only`：`tools/integ/check_interface_alignment.py`（非空 ✅）
- 注入后输出：`ERROR: …/patches 下未找到任何 .patch 文件（空补丁集，无法校验）`，EXIT 1
- 说明：空集硬错误正确拦截了非递归 glob 的回归

**注入 #2 — 删去空集硬错误（验证空集硬错误的必要性）**：
- 注入方式：在临时副本上 `sed` 把 `SystemExit` 改为 `return []`
- 注入后输出：`总计: 80 项 | PASS: 56 | FAIL: 24`（误导性诊断，空目录不应产出 24 个接口违约 FAIL）
- 说明：无空集硬错误时，空目录导致静默回归，与原缺陷同类

**还原证据**：`git checkout` 还原后重新应用修改，`python3 tools/integ/check_interface_alignment.py` → `总计: 80 项 | PASS: 80 | FAIL: 0`，EXIT 0。

**新发现/坑**：
- `SystemExit("message")` 的退出码为 1（非 2），Python 对带字符串参数的 `SystemExit` 默认 exit 1
- 三处 glob 的变量名不统一（前两处用 `patches_dir`，第三处用 `qemu_patches_dir`），提取 helper 时需注意参数名
- **管道退出码陷阱（reviewer N1 发现，主会话已订正）**：验收 #3 首采的 `INTEG-005t-check_pre.log` 末行记为 `EXIT=0`，而 HEAD 版真实退出码为 **1**——采集时用了 `… | tee; echo $?`，取到的是**管道末端 `tee`** 的退出码而非被检脚本的。**结论值 `EXIT 1` 本身正确**，仅日志指针与结论矛盾。**已重采**该日志（`cmd > out 2>&1; rc=$?; … ; echo "EXIT=$rc"`），末行为 `EXIT=1`。**教训**：留证时必须捕获**被检命令自身**的退出码（`PIPESTATUS[0]` 或先落盘再 `echo $?`），不得取管道退出码。

**遗留问题**：无（reviewer 的 N1~N5 均为非阻塞；N1 已由主会话订正日志；N3/C1 的守卫不一致已登记 `deferred.md`）

---

## 审阅记录

### 第 1 轮 engineer 自审

**审查项**：

| 检查项 | 结论 |
|--------|------|
| 期望值改动 | ✅ 无。`git diff` 中仅有 `iter_patch_files` helper 和三处 glob 替换，无 `EXPECTED_*`/常量变更 |
| 断言总数 | ✅ 仍为 80 项，无 FAIL→SKIP/MANUAL 降级 |
| 空集硬错误误伤 | ✅ 不会。正常运行时 LLVM 目录 36 份补丁、QEMU 目录 31 份补丁，`iter_patch_files` 返回非空列表，不触发 `SystemExit` |
| helper 一致性 | ✅ 三处均调用 `iter_patch_files(patches_dir)` 或 `iter_patch_files(qemu_patches_dir)`，行为完全一致 |
| L635 lit glob | ✅ 未改（`git diff` 无 lit/Dadao 相关变更） |
| L635 平铺目录 | ✅ 该目录 `tests/lit/MC/Dadao/*.s` 为平铺非树形，非缺陷，不动正确 |

**判决**：全部 finding 为 0，可标「待验收」。

### 第 1 轮 reviewer 验收（2026-09-25）

> **结论：Accepted**。验收 #1~#10 在 reviewer 独立重跑下**全部通过**，约束无违反；B 部分两组反例证明「递归」与「空集硬错误」**均承重**。附 5 项非阻塞观察（N1~N5），其中 N1（engineer 改前日志 `EXIT=0` 记错）需注意但**不构成本任务返工理由**（完成区 #3 的结论值 `EXIT 1` 正确且 reviewer 独立复现）。

**审查对象**：`tools/integ/check_interface_alignment.py`（工作区未提交版，`sha256=9d1afe50…c46f86`；`git diff --stat` = 1 文件 +11/−3）。全部重跑日志落 `.work/log/integ/INTEG-005t-review-*.log`（reviewer 自跑，未采信 engineer `.work/log/integ/INTEG-005t-*.log`）。反例注入全部在 `/tmp/opencode/INTEG-005t-review/` 临时树，**未触碰仓库**。

#### 1. 验收 #1~#10 逐条重跑

| # | 结果 | reviewer 真实输出（摘要） | EXIT | 日志 |
|---|------|--------------------------|------|------|
| 1 | ✅ | `llvm-project: glob-recursive=36 rglob=36 equal=True`；`qemu: 31/31 equal=True`；对照非递归 `0/0` | 0 | `…-review-A1-count.log` |
| 2 | ✅ | `总计: 80 项 \| PASS: 80 \| FAIL: 0 \| MANUAL: 0`；逐类 `1.ELF 5/0`、`2.ADR 26/0`、`3.Schema 41/0`、`4.Opcodes 8/0` | **0** | `…-review-A2-post.log` |
| 3 | ✅ | HEAD 版（临时树，symlink 补齐 components/contracts/docs/tests + tools/{llvm,qemu,spec,testcases,infra}）：`总计: 80 项 \| PASS: 57 \| FAIL: 23`；FAIL 分解 = `1.ELF 5` + `2.ADR 17` + `4.Opcodes 1`（= trans_* 定义数）；与 `deferred.md`/背景逐条一致 | **1** | `…-review-A3-head-base.log` |
| 4 | ✅ | `llvm patches` 空目录 → `ERROR: …/components/llvm-project/patches 下未找到任何 .patch 文件（空补丁集，无法校验）`，**无** 23 FAIL 清单 | **1** | `…-review-A4-empty.log` |
| 5 | ✅ | `git diff -U0` 仅 4 个 hunk：helper 新增 + 3 处调用替换；无 `EXPECTED_*`/`0x0DA0`/`0x00000001`/地址常量/`record(`/PASS/FAIL/MANUAL 变更 | 0 | 见表下 |
| 6 | ✅ | `record(` 计数 HEAD=80 / WORK=80；输出 `总计: 80 项`；`MANUAL: 0`，无 SKIP/MANUAL 新增 | 0 | `…-review-A2-post.log` |
| 7 | ✅ | 反例见 §2；均确认承重 | 1 / 1 | `…-review-B1-*.log`、`…-review-B2-*.log` |
| 8 | ✅ | `git diff --stat` 仅 `tools/integ/check_interface_alignment.py`；`docs/integ-interface-alignment.md`、`docs/spec/component-patching.md`、`components/`、`tools/qemu/check_qemu_trans.py`、`tests/lit/MC/Dadao/` 均无改动；L635(lit `*.s` glob) 上下文与 HEAD **逐字 IDENTICAL** | 0 | `git diff` |
| 9 | ✅ | `check-patch-tree: 2 component(s), 67 patches OK`；`check_issues: 66 open, 8 closed`；`repository checks: PASS` | **0** | `…-review-A9-make_check.log` |
| 10 | ✅ | `docs/integ-interface-alignment.md` 整文件**未改**（`git diff` 空）；该文无「运行方式/计数」需同步，期望表 80/79/1/0 未动 | 0 | `git diff` |

**#5 逐行核对**：`git diff -U0` 全文仅
`+ iter_patch_files()`（8 行新增：def/文档串/glob/if/raise/return）与 3 处 `-sorted(glob.glob(…"*.patch"))` → `+iter_patch_files(…)`。全文检索 diff 中的 `EXPECTED_/0x0DA0/0x00000001/record(/PASS/FAIL/MANUAL` **零命中**（唯一命中是 hunk 头 `@@ … def record(…)` 的上下文行）。

#### 2. B 部分——主动证伪（反例注入，全部在临时树）

**B1（回退递归，保留空集硬错误）**：`/tmp/…/b1/`，把 helper 的 `glob.glob(os.path.join(patches_dir, "**", "*.patch"), recursive=True)` 改回 `glob.glob(os.path.join(patches_dir, "*.patch"))`；`diff` vs 仓库版**非空**（`39c39`，1 行变更）。
- 真实输出：`ERROR: …/components/llvm-project/patches 下未找到任何 .patch 文件（空补丁集，无法校验）`，**EXIT=1**。
- 结论：**「递归」承重**。注：任务书/验收 #7 括注「→ 23 FAIL 重现」表述不准——回退递归后空集硬错误**恰在其路径上**，故表现为 fail-closed 而非 23 FAIL；23 FAIL 的复现由 A#3（HEAD = 非递归 **且** 无硬错误）承担。

**B2（删去空集硬错误）**：`/tmp/…/b2/`，删除 helper 中 `if not files: raise SystemExit(...)` 两行（llvm/qemu patches 均为空目录）；`diff` vs 仓库版**非空**（`40,41d39`）。
- 真实输出：`总计: 80 项 | PASS: 56 | FAIL: 24 | MANUAL: 0`，**EXIT=1**；24 FAIL = `1.ELF 5` + `2.ADR 17` + `4.Opcodes 2`（`QEMU trans ↔ opcodes.yaml` + `QEMU trans_* 定义数：期望 256 trans_*，实际 0`），**而非明确 ERROR**。
- 结论：**「空集硬错误」承重**。与完成区 #7-注入#2 的 `56/24` **逐字复现一致**。

**还原证据**：全部注入在 `/tmp/opencode/INTEG-005t-review/`，仓库文件未被改动。`git status --short` 仍仅 `M tools/integ/check_interface_alignment.py` + 任务文件 `??`；`git diff --stat` 仍 1 文件 +11/−3；重跑 `python3 tools/integ/check_interface_alignment.py` → `总计: 80 项 | PASS: 80 | FAIL: 0`，EXIT 0（`…-review-final-post.log`）。脚本 sha256 与审查前一致（`9d1afe50…`）。

#### 3. C 部分结论

- **C1（第三处调用的 `isdir` 守卫不一致）——实测成立，但判为 N（非阻塞）**。
  - 隔离实测：临时树令 `components/qemu/patches` 不存在，直接加载模块并**仅调用** `check_opcodes_cross()` → **不抛异常**（`isdir=False` 跳过 helper），静默产出 `FAIL 4.Opcodes QEMU trans_* 定义数 → 期望 256 trans_*，实际 0`（另有 `QEMU trans ↔ opcodes.yaml FAIL`）。日志 `…-review-C1-isolated-opcodes.log`。
  - 但**整脚本**实测：同一临时树跑 `python3 tools/integ/check_interface_alignment.py` → `check_adr_alignment()`（同路径、**无** `isdir` 守卫）先于 `check_opcodes_cross()` 触发 → `ERROR: …/components/qemu/patches 下未找到任何 .patch 文件…`，**EXIT=1**。日志 `…-review-C1-full-qemu-missing.log`。
  - 判定：因 `check_adr_alignment()` 与 `check_opcodes_cross()` 使用**同一路径**且前者在 `main()` 中**先执行**，第三处的 `isdir` 守卫在正常执行路径下**不可达**，脚本整体仍满足「目标 2：扫描到 0 份补丁 → 明确错误非零退出」。故**不构成阻塞**。但完成区/自审「三处行为完全一致」的表述**不严格成立**：三处 `iter_patch_files` 调用本身一致，而第三处多了一层前置 `isdir` 守卫（**系 HEAD 原有、非本次引入**）。建议（非阻塞）后续移除该守卫或将其下沉到 helper，以消除潜在洞。
- **C2（完成区 #4 与反例 #1/#2 原始日志/`git diff --name-only` 缺失）——属实，判为 N（非阻塞）**。完成区 #4「日志」列 `—`；反例 #1 给了 `git diff --name-only` 结论但未贴原始行，反例 #2 用「临时副本」故无 git diff。经 reviewer 独立复现，#4 的 ERROR 文本、#1 的 `ERROR+EXIT1`、#2 的 `56/24` **均逐字吻合**，结论无夸大/无矛盾，故属**证据呈现完整度**问题，非结论错误。
- **C3（helper 三处一致性 / 有无第 4 处非递归补丁 glob）——无遗漏**。全文件 `glob.glob` 仅 2 处：L39（helper，递归）与 L643（lit `*.s`，属正常平铺目录，未改）；`iter_patch_files` 调用点 3 处（L78/L217/L662）。L657 的 `components/qemu/patches/*.patch` 仅为注释文本。**无第 4 处非递归补丁 glob**。
- **C4（完成区两条「新发现」）——均属实**。
  - `SystemExit("message")` 退出码 =1（实测 `python3 -c 'raise SystemExit("ERROR: boom")'` → EXIT 1；`raise SystemExit(2)` → EXIT 2）。
  - 变量名不统一属实：L76/L215 用 `patches_dir`，L659 用 `qemu_patches_dir`。

#### 4. 完成区逐条对齐

- 「修改文件」= 1 文件 +11/−3：✅ 与 `git diff --stat` 一致。
- 「逐行改动说明」四处行号（helper L37-L42、L70→L78、L209→L217、L654→L662）：✅ 逐条核对相符。
- 验收结果表 #1~#10 数值：✅ 除下述 N1 外，全部与 reviewer 重跑一致（#2 `80/80/0`、#3 `57/23`、#4 ERROR+1、#7 `ERROR+1` 与 `56/24`）。
- 「新发现/坑」两条：✅ 属实（见 C4）。
- 「遗留问题：无」：✅ 无功能遗留。
- **N1（证据缺陷，非阻塞）**：完成区 #3 引用的 `INTEG-005t-check_pre.log` 末行为 **`EXIT=0`**，而该 HEAD 版脚本真实退出码为 **1**（reviewer 重跑 `…-review-A3-head-base.log` 末行 `EXIT=1`，且 `deferred.md:116` 亦记 `EXIT=1`）。该日志正文（57/23 表体）与真实运行**逐字一致**，仅末行退出码系采集方式（疑 `… | tee; echo $?` 取到管道退出码）记错。完成区 #3 的**结论值 `EXIT 1` 正确**，故不影响验收；但「完成区结论须与真实输出逐条对齐」上存在**证据指针与自身结论相矛盾**。建议重采该日志（`cmd; echo $?`）。
- **N5（更正主会话注解）**：主会话注「engineer 注入 #2 报 56/24 即因缺 symlink」**不成立**。reviewer 在 **symlink 补齐**的临时树上复现出**同样**的 `56/24`（`…-review-B2-no-harderror.log`）；24 FAIL 的自然构成为 `5(ELF)+17(ADR)+2(Opcodes 侧 QEMU 依赖)`，与 symlink 缺失无关。

#### 5. 非阻塞观察汇总

- **N1**：改前日志 `EXIT=0` 记错（应 1）——证据采集应改 `cmd; echo $?`（见 §4）。
- **N2**：完成区 #4、反例 #1/#2 缺原始日志/注入 diff 行（结论已由 reviewer 独立复现，无夸大）。
- **N3**：第三处 `qemu_patches_dir` 的 `isdir` 守卫与另两处不一致（正常路径不可达，建议清理；见 C1）。
- **N4**：`SystemExit("…")` 退出码 1 与脚本 docstring「Exit 2: 脚本内部错误」不符，且与「存在不一致」的 Exit 1 同码——调用方无法仅凭退出码区分「无法校验」与「校验失败」（消息本身明确，任务目标 2 只要求非零）。
- **N5**：见 §4。

#### 6. 判决

**Accepted** —— 验收 #1~#10 在 reviewer 独立重跑下**全部通过**（含改前 57/23 EXIT 1 基线、改后 80/80 EXIT 0、空集 ERROR EXIT 1、`make check` EXIT 0）；两处改动经反例证明**均承重**；约束（零期望值改动、零断言删减、不改 docs/components/lit glob）逐条无违反；工作区仅 1 文件预期改动，反例均在临时树、仓库无残留。**N1~N5 均不构成返工理由**。任务状态可置 `已验证`（终审仍属架构师）。
