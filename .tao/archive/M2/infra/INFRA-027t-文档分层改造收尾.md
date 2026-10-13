# INFRA-027t: 文档分层改造收尾 — 生成投影门控与陈旧内容订正

**模块**：infra（**跨模块说明见下**）
**项目里程碑**：M2
**依赖**：`SPEC-084t`、`SPEC-085t`、`INFRA-026t`（三者均已 `已验证`）
**状态**：已验证

> **跨模块归属说明**：本任务是「文档分层改造」T1/T2/T3（`SPEC-084t`/`SPEC-085t`/`INFRA-026t`）`/complete` 时登记的**跨任务遗留**的统一收口。6 项中 **①④⑤⑥ 属 infra/工具**（新门控 + `Makefile`、`fetch.py` 注释、`Process-01` 流程正文、路径检查注意），**②③ 属 spec/docs 文档订正**（`spec/Toolchain-01`、`docs/README.md`）。因**工具占多数**且收尾需**原子完成**（门控与文档同步），归 `infra`（前缀 `INFRA`）；若评审认为应拆分，见文末「开放问题」（可拆出 `SPEC-086t` 专做 ②③）。编号已核对：`.tao/tasks/infra/` 最大 `026` → `027`；`.tao/tasks/spec/` 最大 `085`。

## 一、覆盖范围（以 `.tao/knowledge/deferred.md` 现行条目为准）

| # | 来源 | 内容 | 归属 |
|---|---|---|---|
| ① | T2-① | `contract-asm-list.md` 缺**生成器-diff 型**专门漂移门控（`make check-asm-list` 只比对 `spec/SimRISC-*` 内嵌表，**不读**生成物 `.tao/knowledge/contract-asm-list.md`；与 `contract-cfx-aliases.md` 的 `check-cfx-aliases` 不对称） | infra（新门控 + `Makefile`） |
| ② | T2-② | `spec/Toolchain-01-汇编语言.md` **陈旧计数**（§11 L221「177 条 M1」；§12 L235「五断言」等）→ 按实测重算 | spec（文档） |
| ③ | T2-③ | `docs/README.md` L18 Toolchain-01 行仍写「**单位后缀 `i`**」（`SPEC-082t` 已取消 `i`） | spec（文档） |
| ④ | T3-1 | `tools/infra/fetch.py` L178-181 陈旧注释（称 worktree「dirty/HEAD 停在 base」，与新 E5 不符；**行为正确，仅注释**） | infra |
| ⑤ | T3-2 | `spec/Process-01` §7 补 **E5 恢复步骤**（本地 commit 已存在后再改补丁 ⇒ 先 `reset` 到 base 再重放） | infra（流程正文） |
| ⑥ | T1-④（**可选**） | 路径类 grep 检查的坑：`tools/**/__pycache__/*.pyc` 内嵌旧字符串导致 `grep` 报 `binary file matches` | infra（文档/可选） |

- **T1-⑤（历史文档旧路径保留）** 属 **by design**，**无需动作**（本任务不处理，仅此注明）。
- **不做**：不改任何**决策**语义（E1–E8、ADR 判据、投影层级均不变）；不改历史台账/已验收任务书；不改 `spec/SimRISC-0.5.3/`。

## 二、接口规范

### 输入（执行前须先读）
- `.tao/knowledge/deferred.md`（§`spec` 的「文档分层改造 T1/T2/T3 收尾遗留」及「跨任务遗留」条目）
- `.tao/knowledge/contract-asm-list.md`（生成投影，由 `tools/llvm/gen_asm_list.py` 生成）
- `tools/spec/check_cfx_aliases.py`（**对称参照**）、`tools/spec/check_asm_list_consistency.py`、`tools/llvm/gen_asm_list.py`
- `tools/infra/check_spec_drift.py`、`tools/infra/check_spec_refs.py`（两处排除名单）
- `Makefile`（`check` 依赖行、`check-cfx-aliases`/`check-asm-list` 目标）
- `spec/Toolchain-01-汇编语言.md`（§11 L217-229、§12 L233-240）
- `docs/README.md`（L18）、`tools/infra/fetch.py`（L178-181）、`spec/Process-01-组件补丁组织与构建编排.md`（§7 L97-111、§12 L166）
- `contracts/opcodes.yaml`（计数来源）

### 输出
1. **新门控** `tools/spec/check_asm_list_drift.py`（生成器-diff 型；对称 `check_cfx_aliases.py`）。
2. `Makefile`：新增 `.PHONY` `check-asm-list-drift` + 目标，并**并入 `check`** 依赖行。
3. `spec/Toolchain-01-汇编语言.md`：陈旧计数订正（§11 `177→152`；§12「五断言→九断言」；全文复扫无残留旧计数）。
4. `docs/README.md`：Toolchain-01 行去除「单位后缀 `i`」。
5. `tools/infra/fetch.py`：注释更新（**仅注释**，不改逻辑）。
6. `spec/Process-01-组件补丁组织与构建编排.md`：§7 补 E5 恢复步骤；§12 变更记录追加一行（rev. 2026-10-03）。
7. 可选：在 `spec/Process-01`（§12 或合适处）补「路径类 grep 检查须排除 `__pycache__`」说明。
8. `spec/README.md`：**若**投影表 Toolchain-01 行列出了具体门控名，则同步加入 `check-asm-list-drift`（否则不动）。

### 约束
- 全程中文；**不提交 git**；只动任务书范围，越界须披露。
- **不改决策语义**：E1–E8、ADR 判据、投影层级、`Process-01`/`Process-03` 的规范实质一律不变（只做技术性订正/补充）。
- **新增生成投影须同步两处排除名单**（既有约定）：本任务**不新增**投影，但须**核对** `contract-asm-list.md` 已在 `tools/infra/check_spec_drift.py`（`EXCLUDED_CONTRACTS`）与 `tools/infra/check_spec_refs.py`（`_EXCLUDED_CONTRACTS`）**两处**；若新门控引入任何生成物，同样加入两处。
- **不得**让门控覆盖/改写已入库的 `.tao/knowledge/contract-asm-list.md`（生成到临时路径后再比对）。
- 历史台账（`changelog.md`/`deferred.md` 历史条目）、已验收任务书、`spec/SimRISC-0.5.3/` 不改。
- 临时产物 `/tmp/opencode/INFRA-027t/`；证据留 `.work/log/infra/INFRA-027t-*.log`（用 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"` 捕获退出码）。
- 遵循 `AGENTS.md`「子代理硬约束」。

## 三、实施步骤

### 0. 基线
- `git status --porcelain` 干净（或仅本任务书）。
- 记录基线：`make check-asm-list`、`make check-cfx-aliases`、`make check-spec-drift`、`python3 tools/infra/check_spec_refs.py` 的退出码与输出。

### 1. ① 生成器-diff 型漂移门控（`contract-asm-list.md`）
- 新建 `tools/spec/check_asm_list_drift.py`（**镜像** `tools/spec/check_cfx_aliases.py` 的接口与退出码约定）：
  - 通过 `tools/llvm/gen_asm_list.py` **生成到临时路径**（`-o <tmp>`，**不得**写 `.tao/knowledge/contract-asm-list.md`），与已入库文件**逐字节比较**；
  - 退出码：`0`＝PASS（byte-identical）；`1`＝MISMATCH；`2`＝ERROR（生成器非零退出 / 源缺失 / 生成物缺失）。
  - 实现方式二选一（engineer 定）：(a) `subprocess` 调 `gen_asm_list.py -o <tmp>` 后 `filecmp`；(b) 复用生成器的渲染函数在内存生成。**须**保证与生成器默认输出**逐字节**可比。
- `Makefile`：`check-asm-list-drift` 目标 + 加入 `.PHONY` + 加入 `check:` 依赖行（建议紧随 `check-asm-list`）。
- **排除名单核对**：确认 `contract-asm-list.md` 已在 `check_spec_drift.py` 与 `check_spec_refs.py` 两处（现状应已满足；若缺则补）。
- `spec/README.md` 投影表 Toolchain-01 行的 ③门控 列若列具体门控名，则加入 `check-asm-list-drift`。

### 2. ② `spec/Toolchain-01-汇编语言.md` 陈旧计数订正
- 以 `contracts/opcodes.yaml` 与生成器为准**实测重算**：现状 **总 227 = M1 152 + `excluded_m1` 75**。
- 订正：§11 L221「9 个 M1 格式类与 **177 条** M1 指令」→「… **152 条** M1 指令」；§12 L235「组件补丁集**五断言**」→「**九断言**」（与 `Process-01 §8` 现行 9 条一致）。
- 全文复扫其它陈旧计数（`grep -nE "177|251|254|196|195|176|五断言" spec/Toolchain-01-汇编语言.md`），逐条按实测处置或注明「非计数/仍有效」。
- **不改** §11 的其它缺口条目语义与 §13 cfx 约定。

### 3. ③ `docs/README.md` 陈旧措辞
- L18 Toolchain-01 行：删除「单位后缀 `i`」（`SPEC-082t` 已取消），保留其余描述。

### 4. ④ `tools/infra/fetch.py` 陈旧注释
- 更新 L178-181 注释：反映新 E5——**fresh 检出**时 HEAD==base 且工作树干净（`head == commit` 分支＝「已 fetch 未打补丁」或「已 fetch+已收敛」，均 leave it alone）；**打补丁后** HEAD 为 base+1。**仅改注释，不改任何代码逻辑**（`git diff` 应只显示注释行变化）。

### 5. ⑤ `spec/Process-01` §7 补 E5 恢复步骤
- 在 §7 补一节/一条（不改 E5 决策，仅展开操作）：当本地 commit 已存在**后又改了补丁**时，`apply_series.py` 因 HEAD（base+1 的内容 ≠ 新补丁集）而**拒绝应用**；**恢复步骤**：
  1. `git -C .work/source/<component> reset --hard <base>`（丢弃旧本地 commit，回到纯 base）；
  2. `python3 tools/infra/apply_series.py`（或 `make apply-series`）重放补丁集并自动收敛为新的 base+1；
  3. `python3 tools/infra/check_patch_tree.py --source-state` 确认 E1（clean + count=1）。
- §12 变更记录追加一条（rev. 2026-10-03）。

### 6. ⑥（可选）路径检查注意
- 若实现：在 `spec/Process-01`（§12 或合适处）补一句说明——**路径类** grep 检查须排除 `__pycache__`（`.pyc` 内嵌旧字符串致 `binary file matches`），或以 `--exclude-dir=__pycache__` 运行；**不新增独立门控**。
- 若判定价值不足：**省略**并在完成区说明理由。

## 四、验收标准（每项均可失败；反例注入须给出真实输出并还原）

> 证据统一留 `.work/log/infra/INFRA-027t-*.log`；反例注入后须确认还原（`git status` 无残留）。

1. **① 门控存在且对称**：`python3 tools/spec/check_asm_list_drift.py` → **EXIT=0**（byte-identical）；`make check-asm-list-drift` → EXIT=0；`grep -n "check-asm-list-drift" Makefile` 命中 `.PHONY`、目标、`check:` 依赖行三处。
2. **① 可失败（反例，两组）**：
   - **注入期望值**：`sed -i` 改 `.tao/knowledge/contract-asm-list.md` 一处计数（如 `227 条`→`228 条`）→ `check_asm_list_drift.py` **EXIT=1（MISMATCH）** → `git checkout`/还原 → EXIT=0。给注入前后真实输出。
   - **缺失生成物**：临时 `mv .tao/knowledge/contract-asm-list.md <tmp>` → **EXIT=2（ERROR，缺生成物）** → 还原 → EXIT=0。
3. **① 不覆盖产物**：跑 `check_asm_list_drift.py` 后 `git status --porcelain -- .tao/knowledge/contract-asm-list.md` 为空、其 `sha256` 不变。**排除名单**：`grep -l "contract-asm-list.md" tools/infra/check_spec_drift.py tools/infra/check_spec_refs.py` 两个文件均命中。
4. **② 计数订正（可失败）**：
   - `grep -nE "177 条 M1|五断言" spec/Toolchain-01-汇编语言.md` → **零命中**；
   - `grep -n "152 条 M1" spec/Toolchain-01-汇编语言.md` 命中；§12 表述为「九断言」。
   - **可失败证明**：在订正前先跑同一 grep（现文为 `177 条 M1`）→ 命中（FAIL），订正后 → 零命中（PASS）。附两段真实输出。
   - **独立重算**：`python3 -c`（或等效）从 `contracts/opcodes.yaml` 计得 `total=227, m1=152, excluded=75`，与文档数字一致。
5. **③ 措辞（可失败）**：`grep -n "单位后缀" docs/README.md` → 订正前命中、订正后零命中；给两段输出。
6. **④ 注释（可失败）**：`grep -n "intentionally dirty" tools/infra/fetch.py` → 订正前命中、订正后零命中；且 `git diff -- tools/infra/fetch.py` **仅注释行变化**（无逻辑行）；`python3 -m compileall -q tools` EXIT=0。
7. **⑤ 恢复步骤（可失败）**：`grep -nE "reset --hard|恢复|重放" spec/Process-01-组件补丁组织与构建编排.md`（§7 区域）→ 订正前不含、订正后命中；E5 前置校验原句语义不变（人工核对，不删改 `{base, base+1 且内容==补丁集}`）。
8. **可选 ⑥**：若实现，grep 命中该注意说明；若省略，完成区写明理由。
9. **无越界**：`git diff --name-only` 仅本任务列明文件 + 任务书；`git diff --name-only -- components/ spec/SimRISC-0.5.3/` 为空。
10. **全量门控**：`make check` → **EXIT=0**（含新 `check-asm-list-drift`；lit 25/25、`repository checks: PASS`）；`python3 tools/infra/check_spec_refs.py` 仍为 `76(18+58)`（无新增）。日志 `.work/log/infra/INFRA-027t-check.log`。

## 五、下发前四项预检（主会话下发时须逐条给结论）

1. **任务书内部一致性**：✅ 覆盖 6 项与「§一 范围表」一一对应；「不改决策语义」与各步（仅订正/注释/展开）一致；验收 1–10 与产出对齐。无自相矛盾。
2. **依赖链实际可用性**：✅ `SPEC-084t`/`SPEC-085t`/`INFRA-026t` 均 `已验证`；所需文件（`contract-asm-list.md`、`gen_asm_list.py`、`check_cfx_aliases.py`、`opcodes.yaml` 等）均已核实存在；实测计数 `227/152/75` 已取得。
3. **验收可执行性**：「现在可跑」全部项（纯文档/工具/`Makefile`，**无需构建**）；`make check` 全量需构建产物——**当前在位**（`.work/build` 存在，T3 已跑通 25/25），若缺失则 **BLOCKED**，替代证据为针对性门控（`check-asm-list-drift`/`check-asm-list`/`check-cfx-aliases`/`check-spec-drift`/`check-no-residue`/`compileall`）。
4. **与 spec/vectors 一致**：本任务**不改**编码/期望值/向量；`contracts/opcodes.yaml` 是**只读计数来源**，不改；计数订正须与 `opcodes.yaml`/生成器实测一致。

## 完成区

**测试结果**：通过 10/10（任务书验收项 1–10 全部通过，均附真实命令输出与退出码，日志见 `.work/log/infra/INFRA-027t-*.log`）。`make check` **EXIT=0**（lit **25/25**、`repository checks: PASS`，日志 `INFRA-027t-check.log`）；`python3 -m compileall -q tools` EXIT=0。

**修改文件**：
- **新增** `tools/spec/check_asm_list_drift.py`（生成器-diff 型漂移门控；subprocess 生成到临时文件 + **逐字节** diff；退出码 0/1/2）。
- `Makefile`：`.PHONY` 增 `check-asm-list-drift`、`check:` 依赖行紧随 `check-asm-list` 增 `check-asm-list-drift`、新增目标与 help 行。
- `spec/README.md`：投影表 `Toolchain-01` 行 ③ 门控列增 `check_asm_list_drift.py`。
- `spec/Toolchain-01-汇编语言.md`：§11 L221 `177 条 M1`→`152 条 M1`；§12 L235 `五断言`→`九断言`。
- `docs/README.md` L18：删除「单位后缀 `i`」（保留其余描述）。
- `tools/infra/fetch.py` L178-183：**仅注释**更新（反映 E5：HEAD==base 为「已 fetch 未打补丁」/fresh；HEAD=base+1 由下方 is-ancestor 分支处理），`git diff` 仅注释行变化。
- `spec/Process-01-组件补丁组织与构建编排.md`：§7 补「本地 commit 已存在后再改补丁」恢复步骤（reset→重放→`--source-state` 复核 E1）；§8.1 补「路径类 grep/遍历检查须排除 `__pycache__`」（⑥）；§12 变更记录追加 rev. 2026-10-03（INFRA-027t 收尾）。

**验收结果**（逐条真实输出摘要，完整见日志）：

1. **① 门控存在且对称**（`INFRA-027t-verify-pos.log`）：`python3 tools/spec/check_asm_list_drift.py` → `check-asm-list-drift: PASS (byte-identical)` **EXIT=0**；`make check-asm-list-drift` → **EXIT=0**；`grep -n "check-asm-list-drift" Makefile` 命中 `.PHONY`(L44)、help(L84)、`check:` 依赖行(L218)、目标(L264)。
2. **① 可失败（两组反例）**（`INFRA-027t-verify-neg.log`、`INFRA-027t-verify-recheck.log`）：
   - 注入期望值：`sed` 改入库产物 `227 条`→`228 条` → 门控 `MISMATCH (314 actual vs 314 expected lines)` + 首差行 → **EXIT=1**；`git checkout` 还原 → **EXIT=0**。
   - 缺失生成物：`mv` 走产物 → `ERROR — generated file missing` → **EXIT=2**；还原 → **EXIT=0**。两次还原后 `git status --porcelain -- <产物>` 为空、`sha256=a021e16c…f079` 不变。
3. **① 不覆盖产物 + 排除名单**（`INFRA-027t-verify-pos.log`）：跑门控后 `git status --porcelain -- .tao/knowledge/contract-asm-list.md` 为空、`sha256` 不变；`grep -l contract-asm-list.md` 在 `check_spec_drift.py` 与 `check_spec_refs.py` **两处均命中**。
4. **② 计数订正（可失败）**（`INFRA-027t-baseline-greps.log` 前 / `INFRA-027t-verify-greps.log` 后）：订正前 `grep -nE "177 条 M1|五断言"` 命中 L221/L235（`rc=0`）→ 订正后**零命中**（`rc=1`）；`grep "152 条 M1"` 命中、`grep "九断言"` 命中。全文扫 `177|251|254|196|195|176|五断言` 零命中。独立重算 `python3 -c` 从 `opcodes.yaml` 得 `total=227, m1=152, excluded=75`（日志 `baseline-greps.log`）。
5. **③ 措辞（可失败）**（前 `baseline-greps.log` / 后 `verify-greps.log`）：订正前 `grep -n "单位后缀" docs/README.md` 命中 L18（`rc=0`）→ 订正后**零命中**（`rc=1`）。
6. **④ 注释（可失败）**（`verify-greps.log`、`verify-diff.log`）：`grep` 旧表述「dirty while HEAD」「intentionally」订正后**零命中**（`rc=1`）；`git diff -- tools/infra/fetch.py` **仅注释行变化**（无逻辑行）；`compileall` EXIT=0。
7. **⑤ 恢复步骤（可失败）**（`verify-greps.log`）：`grep -nE "reset --hard|恢复步骤|重放"` 订正后 §7 区域命中（L115/117/118），§12 命中 rev 行；§7 步骤 1 的 `{base, base+1 且该 commit 内容 == 补丁集}` 原句**未改**（人工核对）。
8. **⑥（已实现）**：§8.1 补「路径类 grep/遍历检查须排除 `__pycache__`」注意一句，`grep "__pycache__"` 命中（L151）；不新增独立门控。
9. **无越界**（`verify-diff.log`）：`git status --porcelain` 仅上列 6 改动文件 + 新增门控 + 本任务书；`git diff --name-only -- components/ spec/SimRISC-0.5.3/` **为空**。
10. **全量门控**（`check.log`）：`make check` **EXIT=0**（含新 `check-asm-list-drift: PASS`，lit **25/25**，`repository checks: PASS`）；`check_spec_refs.py` 仍为 `FAIL (76 violations: 18 Check1 + 58 Check2)`，与基线**同值无新增**。

**新发现/坑**：
- **验收 #6 的 grep 字面量在基线即不命中**：`grep -n "intentionally dirty" tools/infra/fetch.py` 因原文 `intentionally`（行末）/`dirty`（次行行首）**跨行折断**，基线即 `rc=1`。故采用 `grep -nE "intentionally|dirty while HEAD"` 作为可失败对照（基线 `rc=0`、订正后 `rc=1`），而非伪造「订正前命中」。
- **门控比较用 `read_bytes()` 而非 `read_text()`**：文本模式的新行归一化（universal newlines）会把 `\r\n` 静默折叠为 `\n`，从而漏报「CRLF 注入」型漂移；改用字节比较后对任意字节差异均报 MISMATCH。已在自审第 1 轮修正并复验。
- `make check` 的 `check-no-residue` 仅匹配 `*_tmp*`/`*_gate*`/`*.orig`/`*.rej`，新增 `check_asm_list_drift.py`（未跟踪）不触发误报——全量 `make check` 通过佐证。
- 本任务未新增生成投影，故 `check_spec_drift.py`/`check_spec_refs.py` 两处排除名单**无需改动**（`contract-asm-list.md` 已在两处）；已程序化核对。

**遗留问题**：无。（①–⑥ 全部落地；T1-⑤ 历史文档旧路径保留属 by design，任务书已注明，无需动作。）

## 审阅记录

#### 第 1 轮 engineer 自审
**审查范围**：新增 `tools/spec/check_asm_list_drift.py`、`Makefile`、`spec/README.md`、`spec/Toolchain-01-汇编语言.md`、`docs/README.md`、`tools/infra/fetch.py`、`spec/Process-01-组件补丁组织与构建编排.md`（全部 diff 逐行审查）。

**finding 与处置**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 门控用 `read_text()` 比较，universal-newline 归一化会漏报 CRLF 型字节漂移（不满足「逐字节」要求） | ✅已修 | 改为 `read_bytes()` 比较，展示时再 decode | `verify-recheck.log`：正例 EXIT=0、注入 EXIT=1、还原 EXIT=0 |
| F2 门控可能覆盖产物？ | ❌不修（已正确） | 使用 `tempfile.TemporaryDirectory` + `-o <tmp>`，从不写入库路径 | `verify-pos.log`：跑后产物 sha256 不变、git status 为空 |
| F3 排除名单是否同步？ | ❌不修（现状已满足） | 未改（`contract-asm-list.md` 已在两处） | `verify-pos.log`：`grep -l` 两文件均命中 |
| F4 fetch.py 改动是否越出注释？ | ❌不修（已正确） | 仅注释行 | `verify-diff.log`：`git diff` 仅注释行 |
| F5 验收 #6 grep 字面量跨行不命中 | ✅已修（改用真实可失败对照） | 无代码改动；验收改用 `intentionally|dirty while HEAD` | `baseline-greps.log` 基线 rc=0 → `verify-greps.log` 订正后 rc=1 |
| F6 ⑥ 落点（§8.1 vs §12） | ❌不修（任务书允许「§12 或合适处」） | §8.1 补注意，§12 rev 行同时提及 | `verify-greps.log`：L151 命中 |

**判决**：所有 finding 已处置（无未修项），任务状态置 `待验收`。改动均在本任务书范围内，未越界；`make check` 全量 EXIT=0、lit 25/25。

#### 第 1 轮 reviewer 验收

**判决：Accepted**

**重跑记录**（独立执行，非采信完成区）：

| # | 验收项 | 命令 | 真实输出/退出码 |
|---|--------|------|----------------|
| ① 正例 | `python3 tools/spec/check_asm_list_drift.py` | `check-asm-list-drift: PASS (byte-identical)` EXIT=0 |
| ① 正例 make | `make check-asm-list-drift` | EXIT=0 |
| ① sha256 | 跑门控后 `sha256sum .tao/knowledge/contract-asm-list.md` | `a021e16c…f079`（与基线同） |
| ① 反例·注入 | `sed -i 's/227 条/228 条/'` 后跑门控 | `MISMATCH (314 actual vs 314 expected lines)` + 首差行 4 EXIT=1 |
| ① 反例·注入还原 | `git checkout --` 后跑门控 | `PASS (byte-identical)` EXIT=0 |
| ① 反例·缺失 | `mv` 走产物后跑门控 | `ERROR — generated file missing` EXIT=2 |
| ① 反例·缺失还原 | `mv` 回后跑门控 | `PASS (byte-identical)` EXIT=0 |
| ① 排除名单 | `grep -l "contract-asm-list.md" tools/infra/check_spec_drift.py tools/infra/check_spec_refs.py` | 两文件均命中 |
| ① refs 76 | `python3 tools/infra/check_spec_refs.py` | `FAIL (76 violations: 18 Check1 + 58 Check2)` EXIT=1（与基线同值无新增） |
| ② 旧计数 | `grep -nE "177 条 M1\|五断言" spec/Toolchain-01-汇编语言.md` | EXIT=1（零命中） |
| ② 新计数 | `grep -n "152 条 M1"` / `grep -n "九断言"` | L221 命中 / L235 命中 |
| ② 全文扫残 | `grep -nE "177\|251\|254\|196\|195\|176\|五断言"` | EXIT=1（零命中） |
| ② 独立重算 | `python3 -c` 从 opcodes.yaml 计 | `total=227, m1=152, excluded=75` |
| ③ 措辞 | `grep -n "单位后缀" docs/README.md` | EXIT=1（零命中） |
| ④ 旧注释 | `grep -nE "intentionally\|dirty while HEAD" tools/infra/fetch.py` | EXIT=1（零命中） |
| ④ diff | `git diff -- tools/infra/fetch.py` | 仅注释行变化（L175-184），无逻辑行 |
| ④ compileall | `python3 -m compileall -q tools` | EXIT=0 |
| ⑤ 恢复步骤 | `grep -nE "reset --hard\|恢复\|重放" spec/Process-01` | L113/115/117/118 命中（§7 区域） |
| ⑤ __pycache__ | `grep -n "__pycache__" spec/Process-01` | L151 命中（§8.1） |
| ⑤ 变更记录 | `grep -n "2026-10-03" spec/Process-01` | L179 命中 |
| 全量门控 | `make check` | EXIT=0；`check-asm-list-drift: PASS`；lit 25/25；`repository checks: PASS` |
| 越界 | `git diff --name-only -- components/ spec/SimRISC-0.5.3/` | 空（未动） |
| diff 范围 | `git diff --stat` | 6 文件 + 1 新增门控 + 1 任务书，均为任务书列明文件 |

**字节比较核验**：`check_asm_list_drift.py` L63-65 使用 `read_bytes()` 比较（非 `read_text()`），不经 universal-newline 归一化，对任意字节差异均报 MISMATCH ✓

**约束核验**：不改决策语义 ✓；排除名单两处同步 ✓；门控不覆盖产物（tempfile + sha256 不变）✓；历史台账/SimRISC-0.5.3 未动 ✓；fetch.py 仅注释 ✓；check_spec_refs 76(18+58) 无新增 ✓；不提交 git ✓

**完成区一致性**：逐条核对，完成区声明与真实输出一致，无夸大/不实。

## 收尾与提交（用户裁定，2026-10-03）
- **执行期不提交**：engineer/reviewer 子代理**不得** `git commit`/`git add`。
- **收尾后各提交一次**：本任务经 `/complete` 通过、`**状态**` 置为 `已验证` 后，**主会话**为该任务做**一次独立提交**；**未收尾不得提交**。
- 提交前满足项目 `AGENTS.md`「任务收尾」的收尾检查。

## 开放问题（只列不决）
1. **模块归属/是否拆分**：本任务按「工具占多数 + 收尾原子性」归 `infra`。若评审要求严格模块边界，可拆为 `INFRA-027t`（①②④⑤⑥ 工具/流程）+ `SPEC-086t`（②③ 文档订正）——请裁定。
2. **① 门控实现方式**：`subprocess + 临时文件 diff` vs `内存复用生成函数`——engineer 择一并说明（须保证逐字节可比、不覆盖产物）。
3. **⑥ 是否实现**：可选；若认为价值不足可省略（完成区说明）。
