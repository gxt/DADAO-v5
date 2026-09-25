# QEMU-024t: `check_qemu_trans` 假绿修复（非递归 glob → 递归 + 扫不到补丁即失败）

**模块**：qemu
**项目里程碑**：M1→M2（过渡期任务，见 `.tao/README.md` 与 `.tao/knowledge/milestones.md`）
**依赖**：`QEMU-019t`（本脚本的产出任务，已验证）
**状态**：已验证
**上游发现**：2026-09-25 主会话在核查组件补丁规范落地时实测发现
**决策依据**：用户裁定（2026-09-25）——采方案 **B**（补任务书 + reviewer 独立证伪后提交）；过渡期任务标记 `M1→M2` 亦为用户同日裁定

## 执行环境

**执行环境**：本地

## 背景（已实测确认）

**上游事件**：2026-09-23 组件补丁集重整（`ADR-0002 D4` rev.）——`components/<name>/patches/` 由**扁平** `NNNN-*.patch` 改为**树形** `<上游相对路径>.patch`（补丁进入子目录，如 `patches/target/dadao/translate.c.patch`）。形态见 `docs/spec/component-patching.md` §2。

**缺陷 1 — 扫描失效**：`tools/qemu/check_qemu_trans.py` 原第 35 行用**非递归** glob：

```python
patch_files = sorted(glob.glob(os.path.join(src_dir, "*.patch")))
```

树形化后该 glob 匹配 **0** 个文件（实测）：

| 取法 | 命中数 |
|---|---|
| 非递归 `glob(patches/*.patch)` | **0** |
| 递归 `glob(patches/**/*.patch, recursive=True)` | **31** |
| `pathlib.Path(patches).rglob("*.patch")`（交叉核对） | **31** |

**缺陷 2 — 假绿（更严重）**：扫描到 0 个补丁时脚本**不报错**，把全部 256 条判为 MISSING，末尾仍 `exit 0`：

```
$ python3 <HEAD 版脚本> check_qemu_trans.py --yaml contracts/opcodes.yaml --src components/qemu/patches
MISSING: ld.ub-rd -> trans_ld_ub_rd [M1]
...（共 256 行 MISSING）...
check_qemu_trans: 0/256 insns have trans impl (M1 0/178)
EXIT=0
```

即：**检查器失去判别力后仍报「通过」**——与 `AGENTS.md`「只会报 PASS 的脚本不是证据」「不得留下跑不了就报 PASS 的空间」直接冲突。

**对照值（M1 门槛）**：`docs/m1-retrospective.md:45` 记载该脚本产出时（`QEMU-019t`）报 `256/256 insns have trans impl (M1 178/178)`；本修复后恢复该值。可见 2026-09-23 重整时发生**静默回归**。

## 目标

1. 扫描改为**递归**，使树形补丁集下能找到全部补丁；
2. **fail-closed**：扫不到任何补丁文件时**无条件非零退出**（「无法校验」不得等于「通过」）。

## 接口规范

- 输入：`tools/qemu/check_qemu_trans.py`（`collect_trans_defs()`、`main()`）
- 输出：`tools/qemu/check_qemu_trans.py`（递归 glob + 补丁计数 + 空集非零退出 + docstring 同步）
- 约束：
  - **不改** `--strict` 既有语义（默认有缺失仍 exit 0；`--strict` 有缺失 exit 1）
  - **不改** `trans_*` 匹配正则；**不改** `validate_decodetree.build_unique_func_names()` 的复用（DRY）
  - **不改** `--yaml` / `--src` CLI 形态
  - **不修** `deferred.md:106` 的「`+`/`-`/上下文行一视同仁」隐患（独立条目，见「新发现」）
  - 本脚本**不在** `make check` 内（standalone lint）；改动不得使 `make check` 变红

## 交付物

- `tools/qemu/check_qemu_trans.py`：递归 glob + `collect_trans_defs()` 返回补丁计数 + 空集非零退出 + docstring
- 完成区附：改前/改后对照、反例门控真实输出、`make check` 结果

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | 递归扫描：树形 `patches/` 下命中 **31** 份补丁，与 `rglob` 交叉核对一致 | 现在可跑 | 验收 4 的证据表 |
| 2 | 修复后基线 = `256/256 (M1 178/178)`，与 `docs/m1-retrospective.md:45` 记载一致 | 现在可跑 | 真实输出 |
| 3 | **改前复现假绿**：HEAD 版脚本在同一 `--src` 下报 `0/256 (M1 0/178)` 且 **exit 0** | 现在可跑 | 证明缺陷真实存在（非推测） |
| 4 | **fail-closed**：`--src` 指向空目录 / 不存在目录 → **非零退出** + 明确错误消息 | 现在可跑 | 反例门控 |
| 5 | 反例门控（既有语义未被破坏）：只给 1 份补丁 → 报 `0/256`；默认 exit 0、`--strict` exit 1 | 现在可跑 | 反例门控 |
| 6 | `--strict` 语义不变；`--yaml`/`--src` CLI 不变；正则与 DRY 复用不变 | 现在可跑 | 代码审查 + 用例 |
| 7 | `make check` EXIT 0 | 现在可跑 | 完整输出 |
| 8 | 反例注入可**还原**：工作区无残留，`git status` 仅预期文件 | 现在可跑 | 还原证据 |

## 关键证据（主会话代行，2026-09-25）

> **⚠️ 说明**：本次改动由**主会话代行**（非 engineer 子代理），因此下列证据**仅为待验证材料**，**不构成验收结论**；须由 `reviewer` **独立复跑 + 主动证伪**后方可判 Accepted。日志见 `.work/log/qemu/QEMU-024t-*.log`。

| # | 命令 | 输出 | EXIT | 日志 |
|---|---|---|---|---|
| 1 | `python3 tools/qemu/check_qemu_trans.py` | `check_qemu_trans: 256/256 insns have trans impl (M1 178/178)` | **0** | `QEMU-024t-baseline.log` |
| 2 | HEAD 版脚本 + 同一 `--src`（改前复现） | 256 行 `MISSING:` … 末尾 `0/256 … (M1 0/178)` | **0**（假绿） | `QEMU-024t-head-baseline.log` |
| 3 | `--src /tmp/opencode/QEMU-024t/empty`（空目录） | `ERROR: 在 …/empty 下未找到任何 .patch 文件；无法校验（补丁集为树形，请检查 --src 是否为 patches/ 根）` | **1** | `QEMU-024t-counter-empty-src.log` |
| 4 | `--src /tmp/opencode/QEMU-024t/nope`（不存在） | 同上 ERROR | **1** | `QEMU-024t-counter-missing-src.log` |
| 5 | `--src …/partial`（仅 1 份补丁，无 trans 定义） | `check_qemu_trans: 0/256 insns have trans impl (M1 0/178)` | 默认 **0** / `--strict` **1** | `QEMU-024t-counter-partial.log` |
| 6 | 非递归 vs 递归 glob 计数 | `0` / `31` / `31`（rglob 交叉核对） | — | `QEMU-024t-glob-count.log` |
| 7 | `make check` | `repository checks: PASS`（`check-patch-tree: 2 component(s), 67 patches OK`；`check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)`） | **0** | `QEMU-024t-make-check.log` |

**HEAD 版复现方式**（可重复）：`git show HEAD:tools/qemu/check_qemu_trans.py` 与 `validate_decodetree.py` 复制到 `/tmp/opencode/QEMU-024t/head/tools/qemu/`，再以 `--yaml <repo>/contracts/opcodes.yaml --src <repo>/components/qemu/patches` 运行。

## 完成区

**修改文件**：

| 文件 | 改动 |
|---|---|
| `tools/qemu/check_qemu_trans.py` | **本任务主改动**（+14 / −5） |
| `.tao/README.md` | 同批：新增「过渡期任务」条目（用户裁定 2026-09-25） |
| `.tao/knowledge/milestones.md` | 同批：新增「过渡期任务（`M<i>→M<i+1>`）」段 |
| `docs/m2-spec-planning.md` | 同批：头部状态行 + §6 + §7-8 标注「❌ 不采纳（2026-09-25 用户裁定）」 |

**本任务主改动明细**（`tools/qemu/check_qemu_trans.py`）：

| 改动 | 内容 |
|---|---|
| docstring | 默认搜索改为「递归 `**/*.patch`（树形补丁集）」；补「扫不到补丁文件时**无条件**非零退出（无法校验 ≠ 通过）」 |
| `collect_trans_defs()` | `glob.glob(os.path.join(src_dir, "**", "*.patch"), recursive=True)`；返回值由 `set` 改为 `(trans_defs, 补丁文件数)` |
| `main()` | `trans_defs, n_patches = collect_trans_defs(args.src)`；`n_patches == 0` → `sys.exit("ERROR: …")` |

**测试结果**（主会话实测，日志见上表）：改前 `0/256 (M1 0/178)` 且 exit 0（假绿）→ 改后 `256/256 (M1 178/178)` exit 0；3 组反例全部按预期失败（空目录/不存在目录 exit 1；部分补丁集默认 0 / `--strict` 1）；`make check` EXIT 0。

**新发现/坑**：

1. **`deferred.md:106` 的隐患已「活化」**：`collect_trans_defs()` 对 `+`/`-`/上下文行一视同仁（理论上「后序补丁删除某 `trans_*` 且未重现」会被前序 `+` 行误判为存在）。修复前脚本扫 0 个文件、该隐患无从发生；修复后实际扫描 31 份补丁，风险面**真实存在**。当前实测无假阳性（`256/256` 全部找到）。**本任务不修**（属独立条目，建议后续按 `deferred.md:106` 的建议只计 `+`/上下文行）。
2. **`gen_asm_list.py` 的默认输出会覆盖已入库文件**（主会话在排查期间误触）：`python3 tools/llvm/gen_asm_list.py --syntax old --plain` 这类看似「只读查询」的调用会**默认写入 `docs/assembly-list.md`**，把新语法表覆盖为旧语法清单。已 `git checkout` 还原并用默认参数重生成确认一致（`git status` 空）。**建议**：为 `--plain` 增加「无 `--output` 时输出到 stdout」或强制 `--output`。属 `llvm` 模块工具，另行处置。

**遗留问题**：

- `deferred.md:106`（`+`/`-` 行分类）与「`gen_asm_list.py` 默认覆盖」两项**均未在本任务处理**，按上述「新发现」登记。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-09-25）

> 结论：**Accepted**。全部 8 条验收在 reviewer 独立重跑下通过；B 部分反例证明「递归」与「fail-closed」两个改动**均承重**。仅 1 项同类缺陷（另模块工具）标为非阻塞观察 N1。

**审查对象**：`tools/qemu/check_qemu_trans.py`（工作区未提交版，`sha256=500b527a…8995`）；同批约定文档 `.tao/README.md`、`.tao/knowledge/milestones.md`、`docs/m2-spec-planning.md`。日志全部落 `.work/log/qemu/QEMU-024t-review-*.log`（reviewer 自跑，未采信主会话 `.work/log/qemu/QEMU-024t-*.log`）。

#### 1. 验收标准逐条重跑

| # | 结果 | reviewer 真实输出（摘要） | EXIT | 日志 |
|---|---|---|---|---|
| 1 | ✅ | 非递归 `0` / 递归 `31` / `rglob` `31`（交叉一致） | 0 | `…-review-glob-count.log` |
| 2 | ✅ | `check_qemu_trans: 256/256 insns have trans impl (M1 178/178)` | 0 | `…-review-baseline.log` |
| 3 | ✅ | HEAD 版：256 行 `MISSING:` + 末行 `0/256 … (M1 0/178)`（`grep -c '^MISSING:'`=256，`wc -l`=257） | **0**（假绿复现） | `…-review-head-baseline.log` |
| 4 | ✅ | 空目录 / 不存在目录：`ERROR: 在 … 下未找到任何 .patch 文件；无法校验（补丁集为树形，请检查 --src 是否为 patches/ 根）` | **1 / 1** | `…-review-empty-src.log`、`…-review-missing-src.log` |
| 5 | ✅ | 仅 1 份 `meson.build.patch`：`0/256 … (M1 0/178)` | 默认 **0** / `--strict` **1** | `…-review-partial-default.log`、`…-review-partial-strict.log` |
| 6 | ✅ | 见「约束核验」；固定版 `--strict`（全量）`256/256 (M1 178/178)` | 0 | `…-review-strict-full.log` |
| 7 | ✅ | `check-patch-tree: 2 component(s), 67 patches OK`；`check_issues: 66 open, 8 closed (0 blocking M1-gate: 0)`；`repository checks: PASS` | 0 | `…-review-make-check.log` |
| 8 | ✅ | 注入全部在 `/tmp`；`git status --short` 仅 4 个预期 `M` + 任务文件 `??`，`components/`、`tools/` 无残留 | — | 见 §3 |

> #2 与 `docs/m1-retrospective.md:45`（`256/256 insns have trans impl (M1 178/178)`）逐字一致，已核对。

#### 2. 约束核验（逐条）

- ✅ **`--strict` 语义未变**：`if args.strict and missing_total > 0: sys.exit(1)`（L111）未在 diff 中；实测全量 `--strict` exit 0、缺 256 条时 exit 1。
- ✅ **`--yaml` / `--src` CLI 未变**：L57 / L60 的 `add_argument` 未动；`--src` 别名 `--patches` 保留。
- ✅ **`trans_*` 正则未变**：L42 `re.compile(r'static\s+bool\s+(trans_\w+)\s*\(')` 未动。
- ✅ **DRY 复用未变**：L22 `from validate_decodetree import build_unique_func_names` + L73 调用未动；`validate_decodetree.py` 工作区无修改。
- ✅ **未碰契约/断言/其它检查**：`git diff HEAD --stat` 仅 4 文件（脚本 +19/−5 总量，脚本部分 +14/−5）；未改 `MISSING`/汇总输出格式、未弱化 `--strict`、未删检查。
- ✅ **不在 `make check` 内**：`Makefile:122` `check: manifest-check validate-vectors check-spec-drift check-patch-tree` + `check_issues.py`，不含本脚本（standalone）。`make check` EXIT 0。
- ✅ **docstring 与实现一致**：docstring 已同步递归搜索 + 无条件非零退出。

#### 3. B 部分——主动证伪（反例注入，全部在 `/tmp/opencode/QEMU-024t-review/`）

**B1（仅回退递归，保留 fail-closed）**：`inject/tools/qemu/check_qemu_trans.py` 将 L40-41 改回 `glob.glob(os.path.join(src_dir, "*.patch"))`；`diff` vs 仓库版非空（40,41c40）。
- 真实输出：`ERROR: 在 …/components/qemu/patches 下未找到任何 .patch 文件；无法校验…`，**EXIT=1**。
- ⚠️ 与任务提示的预期「仍 exit 0」**不符**：回退递归后 `n_patches==0`，fail-closed 分支**恰在其路径上**，故脚本不是假绿而是 fail-closed 生效。日志 `…-review-inject-b1-glob.log`。

**B1b（回退递归 + 删去 fail-closed，隔离「递归」）**：`inject-b1b/` 同时应用上述两项；`diff` 非空。
- 真实输出：`check_qemu_trans: 0/256 insns have trans impl (M1 0/178)`、256 行 `MISSING:`，**EXIT=0**（假绿重新出现）。
- 结论：**「递归」承重**——无它则要么 fail-closed 拦下（B1），要么在无 fail-closed 时复现假绿（B1b）。日志 `…-review-inject-b1b.log`。

**B2（保留递归 + 删去 `n_patches==0` 的 `sys.exit`，隔离 fail-closed）**：`inject-b2/`；`diff` vs 仓库版非空（77,79d76）。
- 真实输出：空 `--src` 下 `check_qemu_trans: 0/256 … (M1 0/178)`，**EXIT=0**（空目录退回假绿）。
- 结论：**「fail-closed」承重**——删去即空集假绿。日志 `…-review-inject-b2.log`。

**还原证据**：三次注入均在临时树，未触碰仓库；`git status --short` 仅预期 4 个 `M` + 任务文件 `??`（§1 #8）。纯 Python，无需重建。

#### 4. 完成区逐条对齐（B4）

- 「改动」三行（docstring / `collect_trans_defs` / `main`）与真实 diff 逐字相符 ✅。
- 「测试结果」与 reviewer 重跑数字一致 ✅；+14/−5 核对属实 ✅。
- 「新发现 1 / 2」「遗留问题」见 §5 C 部分，无夸大 ✅。
- **遗漏（N2，非阻塞）**：完成区「修改文件」只列 `check_qemu_trans.py`，未列同批的 3 份约定文档（`.tao/README.md` / `milestones.md` / `docs/m2-spec-planning.md`）。任务背景将其列为「同批改动」，完成区宜一并登记。

#### 5. C 部分结论

- **C1（`deferred.md:106` 隐患「活化」）——成立**。源码 L43-50 对 `+`/`-`/上下文行**一视同仁**（仅注释提及）。修复后确实扫描 31 份补丁，风险面真实存在。reviewer 独立全量扫描：`patches=31`、命中 `trans_*` 名 **256**、仅出现在删除行（dangling）**0** 个 ⇒ **当前无假阳性**（`256/256` 全部找到）。本任务不修属合理（独立条目）。日志 `…-review-inject-*.log` 同批。
- **C2（`gen_asm_list.py` 默认覆盖）——成立**（**仅读源码，未执行**）。`L356: parser.add_argument("-o","--output", default=str(ROOT/"docs/assembly-list.md"))`；`--plain` 分支 `L380-381: out = Path(args.output); out.write_text(header+…)` ⇒ `--plain` 无 `--output` 时确实覆盖 `docs/assembly-list.md`。`docs/assembly-list.md` 当前 `git status` 干净，未见残留。
- **C3（三份约定文档一致性）——一致，无矛盾**。`.tao/README.md:54`、`milestones.md:20-22`、`docs/m2-spec-planning.md:4/134/154` 对「过渡期任务 `M<i>→M<i+1>`：只能是 `t`、不入 `milestones.md` 模块列、判据=无未终态任务、不重开已置 `里程碑` 的 `m`」表述互相吻合；`m2-spec-planning.md` 的「❌ 不采纳」标注与 §6 原文（L136-140）、§7-1~7-8 原文（L146-153）**并存、原文保留**，标注明确指向「不予采纳」，无冲突。

#### 6. 非阻塞观察

- **N1（重要，本任务无需返工，但需另行处置）**：同类缺陷（`2026-09-23` 树形化致非递归 glob 失效）**仍存在于 `tools/integ/check_interface_alignment.py`**（L70、L209、L654 三处 `glob.glob(..., "*.patch")`，均扫 `components/*/patches`）。实测 `python3 tools/integ/check_interface_alignment.py` → **EXIT=1**，`总计: 80 项 | PASS: 57 | FAIL: 23`，含 `[4.Opcodes] QEMU trans_* 定义数：期望 256 trans_*，实际 0`（日志 `…-review-integ-align.log`）。该工具**不在 `make check` 内**，故不影响本任务验收；但按 `AGENTS.md`「修复须修一类」，建议**登记 deferred 或新建 `integ` 模块任务**修复。归属：`integ`，非 `QEMU-024t`。
- **N2**：完成区未登记 3 份约定文档改动（见 §4）。
- **N3**：任务提示 B1 的预期「仍 exit 0」不准确（实测 exit 1，fail-closed 在路径上）；此为提示表述问题，非工程师缺陷。

#### 7. 判决

**Accepted** —— 8/8 验收在独立重跑下通过；两处改动经反例证明均承重；`make check` EXIT 0；工作区无残留；约束无违反。**N1（integ 同类缺陷）不构成本任务返工理由**，但建议尽快另行建任务/登记 deferred，由架构师/主会话定夺。任务状态可置 `已验证`。
