# INFRA-115t: tests/docs 小项收口（M1 计数 / 生成器 `--check` 措辞 / anti_forgery 路径 / `check-generator-sync` 入 L2）

**模块**：infra
**项目里程碑**：M11
**依赖**：无（与 `QEMU-077t` 同改 `milestones.md` ⇒ 两者串行，不得并行）
**状态**：已验证

## 执行环境
**执行环境**：本地（纯 Python + 文档 + `Makefile`；不重建任何组件）

## 问题根源（现场 2026-11-01 11:2x 核，**逐条实测**，带“先实测再决定”项）

1. **M1 计数口径**：`contracts/opcodes.yaml` 中 `scope: m1` 现场 **156** 行（`grep -c 'scope: m1' contracts/opcodes.yaml`）；`validate_vectors.py` 打印 `156/156 M1 identities covered OK`。
   - `tests/inst/README.md:14` 写「`scope == "m1"` 为唯一判据（**152 条**）」⇒ **错**（把“已覆盖 152”当成“身份总数 156”）。
   - `tests/README.md:51,203` **已是 156** ⇒ 下发清单的「152 → 156 同步」**现场不成立**，本任务改为**只核验零残留**、不改。
   - `tests/INVENTORY.md:56,217` 的 `m1 152/156` 是**覆盖/总数**（4 条 `m1` cfx `cfx2rc`/`cfx2rd`/`escape`/`trap` deferred，见同文件 L217）⇒ **语义正确、默认不改**；须**先实测**（覆盖数 = 152、总数 = 156、deferred = 4），实测不符才改并在完成区说明。
2. **生成器 `--check` 措辞**：`tests/README.md:211` 写「生成器 `--check` **全部** byte-identical」——泛化表述。现场含 `--check` 的脚本 **7 个**：`generate_ctrl_jump_call_ret` / `generate_ctrl_br` / `generate_mem_vectors` / `generate_isa_vectors` / `generate_misc` / `generate_bitcnt_vectors` / `generate_rev_vectors`（架构师预探：7 个 `--check` 全 PASS，合计 ≈41 s，`generate_misc` 32.4 s 最慢；engineer 须自跑复核）。
3. **`tools/testcases/test_anti_forgery_008t.py`**（TESTCASES-008t 验收 6 的注入脚本，**不在任何门控**，`tests/INVENTORY.md:210` 已如此登记）仍指 `tests/vectors/{isa,inventory.md}`（该目录**已不存在**）：常量 `ISA_DIR`、`VECTORS_DIR`、`setup_workdir()` 的复制源与 `inventory.md` 路径共 4 处过期。当前目录布局 = `tests/inst/base/*.yaml` + `tests/inst/inventory.md`。
   - **可适配，勿删**（架构师在 `运行期临时目录` 副本实测：改上述 4 处后 5 类注入全 PASS + 1 valid PASS，rc=0）。注意 `VECTORS_DIR` 一行也须改（漏改 ⇒ valid 用例因 `inventory.md not found` 假红）。
4. **生成器 `--check` 未入任何 L2 门控**：目前只有 `rev` 有门控（`check-rev-vectors`，**L1**，`Makefile:1595`）；`ctrl_jump_call_ret`/`ctrl_br`/`mem`/`isa`/`misc`/`bitcnt` 仅靠人工自跑 ⇒ 生成器与落盘向量漂移无人守。

## 目的

- 文档计数/措辞与现场一致（不再把“已覆盖 152”写成“身份 152”）。
- `test_anti_forgery_008t.py` 重新可用（路径与当前布局一致），且**保持**其「不在门控」的既有定位（不新增门控、不改 `tests/INVENTORY.md:210` 的口径）。
- 新增 `check-generator-sync`（6 个生成器 `--check`）并入 **L2**，使生成物漂移在任务收尾即可发现。

## 接口规范

### 输入（现场事实）
- 计数：`grep -c 'scope: m1' contracts/opcodes.yaml` = 156；`python3 tools/testcases/validate_vectors.py` 输出 `156/156`。
- `generate_*` 的 `--check` 均为**只读**（`render` 与写盘共用同渲染函数），无写盘副作用；`rev` 的 `--check` 已在 L1。
- `_locked-check-modules` 现行成员：`check-inst-smoke check-arch-smoke check-unit check-tset-libc-smoke check-tset-llvm-smoke check-tset-embench-smoke`（`Makefile:1007`）。

### 输出（逐条）
1. **`tests/inst/README.md`**：L14 `（**152 条**）` → `（**156 条**）`；同句其它文字不动。
2. **`tests/README.md`**：① L211「生成器 `--check` 全部 byte-identical」→ 按现场列名（`ctrl-jump/call/ret`、`ctrl-br`、`mem`、`isa`、`misc`、`bitcnt`、`rev` 各 `--check` 逐字节一致），去掉“全部”泛化；② L51/L203 的 156 **不动**（已正确）。
3. **`tests/INVENTORY.md`**：**默认零改动**；仅当「⑵ 实测」不成立（覆盖≠152 或总数≠156 或 deferred≠4）时按实测修正 `m1 x/156` 两处，并在完成区贴实测输出与理由。
4. **`tools/testcases/test_anti_forgery_008t.py`**：4 处路径改为 `tests/inst/base` / `tests/inst/inventory.md`（含 `VECTORS_DIR` 常量）；脚本语义、5 类注入内容、`PASS_CASES` 一律不动；仍不进 `Makefile`。
5. **`Makefile`**：
   - 新目标（体例同 `check-rev-vectors`，带注释说明来源与层）：
     ```
     check-generator-sync:
     	@$(PYTHON) tools/testcases/generate_ctrl_jump_call_ret.py --check
     	@$(PYTHON) tools/testcases/generate_ctrl_br.py --check
     	@$(PYTHON) tools/testcases/generate_mem_vectors.py --check
     	@$(PYTHON) tools/testcases/generate_isa_vectors.py --check
     	@$(PYTHON) tools/testcases/generate_misc.py --check
     	@$(PYTHON) tools/testcases/generate_bitcnt_vectors.py --check
     ```
     （`rev` **不列**：已在 L1 `check-rev-vectors`，遵循 `docs/Process-07 §4`「一个检查只在一层」）
   - 挂载：`_locked-check-modules` 成员加 `check-generator-sync`（**只加挂载，不改该行语义/顺序说明**）；`.PHONY` 清单加该名；`make help` 加 1 行说明（L2；本任务号）。
6. **`docs/Process-07-门控分层规范.md`**：门控清单表加 **1 行**（`make check-generator-sync`｜**L2**｜6 个生成器 `--check` 逐字节一致，`rev` 在 L1 不重复）；L2 行（§1 表）文本**不改**。（依据 `docs/Process-07 §4`「迁移须同步 Makefile + 本表」；属**范围追加**，已披露。）
7. `milestones.md` 表首插 1 行；本任务书填完成区/审阅记录。

### 约束
- **不改向量内容**（`tests/inst/**` 的 YAML 一律不动）、不改 QEMU/LLVM/spec/contracts。
- 生成器脚本本身**不改**（只跑 `--check`）。
- 成本门槛（先实测再决定）：`check-generator-sync` 现场合计应 ≈40 s。若实测 **> 120 s** 或某脚本有环境前置依赖 ⇒ **列方案**（如 `misc` 单独按需、或只挂未门控的 5 个）+ 替代证据，**不得静默不做**，在完成区写明决定。
- `make check`（L1）/`make check-modules`（L2）受 `gate.lock` 串行：占用时先取直调证据，锁空后补跑；**rc=75 不作通过证据**。
- 还原纪律：注入还原一律 `cp` 备份 + `md5sum` 对账；**禁** `git checkout`/`restore`/`stash`。
- 临时目录 `运行期临时目录`；仓库内不留临时/探针文件。

## 验收标准

1. **计数一致**：`grep -c 'scope: m1' contracts/opcodes.yaml` = 156；`make validate-vectors` 输出 `156/156`；`tests/inst/README.md` 出现 `**156 条**`；`grep -rn '152 条\|152 行' tests/` ⇒ **0 行**（rc=1）。
2. **INVENTORY 实测复核**：贴实测输出证明 `m1` 覆盖 152 / 总数 156 / deferred 4（列 4 个 id）；若与 `tests/INVENTORY.md:56,217` 不一致 ⇒ 已按实测修正并说明；一致 ⇒ 该文件 `git diff` 为空。
3. **措辞对齐**：`tests/README.md:211` 不再含「全部 byte-identical」；列名与实际 `--check` 脚本集合一致（`ls` + 逐个 `--check` 输出为据）；`tests/README.md` 无其它改动（`git diff --stat` 只 1 行区）。
4. **anti_forgery 可用**：`python3 tools/testcases/test_anti_forgery_008t.py` ⇒ **rc=0**，输出 5 条 `PASS: inject…` + `PASS: valid reserved case` + `ALL 5 INJECTION + 1 VALID TEST PASSED`；脚本内 `grep -n 'tests", "vectors"'` ⇒ **0 行**；`运行期临时目录` 工作目录已自清。
5. **新门控绿**：`make check-generator-sync` ⇒ **rc=0** 且 6 段 PASS（贴逐段末行）；`grep -n 'check-generator-sync' Makefile` ⇒ 定义 + `.PHONY` + `_locked-check-modules` 挂载 + help 共 4 处命中；`make check-modules` ⇒ rc=0 且新段在其成员内。
6. **Process-07 登记**：表内新增 1 行且层级 = L2；`git diff docs/Process-07-*` 只多该行。
7. **L1**：`make check` ⇒ **rc=0**。
8. **反例可达 FAIL（≥2 条，`cp` + `md5`）**：
   - a. `cp` 备份 `tests/inst/base/misc.yaml` + `md5sum` → 改 1 个期望字节 → `make check-generator-sync` **rc≠0**（`generate_misc --check: FAIL`）→ `cp` 还原 + md5 一致 → 复跑 rc=0；
   - b. `cp` 备份 `tools/testcases/test_anti_forgery_008t.py` → 把 `INJECT1` 改成与 `PASS_CASES` 相同（即“未注入”）→ 脚本 **rc=1** 并打印 `FAIL: inject1` → `cp` 还原 + md5 一致 → 复跑 rc=0。
9. **体例**：`make check-milestones-fresh` rc=0；`make check-tasks` rc=0；完成区 **≤30 行**。
10. **证据脚本**：`运行期证据（已清理，未归档）` 下一键脚本跑通（`checks=N failures=0` + 自身 rc 落盘），每条断言有**可达 FAIL** 路径。

## 文件范围

- 允许：`tests/inst/README.md`、`tests/README.md`、`tools/testcases/test_anti_forgery_008t.py`、`Makefile`（仅新目标 + `.PHONY` + 挂载 + 1 行 help）、`docs/Process-07-门控分层规范.md`（+1 行）、`.tao/tasks/infra/INFRA-115t-*.md`、`.tao/knowledge/milestones.md`、`运行期证据（已清理，未归档）`。
- **条件允许**：`tests/INVENTORY.md`（仅当验收 2 实测不符）。
- 禁止：`tests/inst/**` 的 YAML 内容、生成器脚本、QEMU/LLVM/musl、`spec/`、`contracts/`、`.tao/contracts/`、`.tao/adr/`、其它 Makefile 目标。

## 下发前预检（5 项，均为现场核）

1. **任务书内部一致**：4 项问题 ↔ 7 项输出 ↔ 验收 1–10 ↔ 文件范围逐条对齐；编号 `INFRA-115` 未占用（`.tao/tasks/infra/` 仅 `INFRA-113t`；`.tao/archive/**` 最大 `INFRA-114t`）。
2. **验证前置可用**：`python3` 可跑 7 个 `--check`（预探 7 个 rc=0，≈41 s）；`validate_vectors.py` 可跑（`156/156`）；`make` 目标可跑；`gate.lock` 是否占用需现场看。
3. **验收逐条可跑性**：1/2/3/4/5/6/8/9/10 **现在可跑**；7（`make check`）与 5 的 `make check-modules` **受锁** ⇒ 占用时取直调证据 + 锁空补跑（rc=75 不算通过）。
4. **与 `contracts/`、`tests/inst/` 一致**：contracts 零改动；`tests/inst/**` **YAML 零改动**（新增门控只读）；`tests/inst/README.md` 计数以 `contracts/opcodes.yaml` 现场 156 为准。
5. **拟改文件 × `spec/` 清单**：全部不在 `spec/` ⇒ **无命中、无 BLOCKED**；`Makefile`/`docs/` 改动不动 `spec/`。

## 风险

- **R1 计数“修错”**：`152/156` 的“152”是已覆盖数，**不是**笔误（4 条 `m1` cfx deferred）⇒ 只改 `tests/inst/README.md` 的“152 条”，`INVENTORY` 默认不动。
- **R2 anti_forgery 假绿**：只改 `ISA_DIR` 而漏 `VECTORS_DIR` ⇒ valid 用例因 `inventory.md not found` 报错或路径回落真实仓库而假绿/假红 ⇒ 必须**跑通脚本**（rc=0 + 6 条 PASS）为判据，不以“改了路径”为完成。
- **R3 L2 成本**：`misc --check` 32 s 为大头；若实测 >120 s 须列方案（见“约束”）。
- **R4 与 `QEMU-077t` 抢 `milestones.md`** ⇒ 串行下发；`Makefile` 为共享文件 ⇒ 不得与其它改 `Makefile` 的任务并行。
- **R5 Process-07 增行**属范围追加（规则 §4 要求同步本表）；若用户不同意，则该条降为“记录不落地”，须在完成区显式写明。

## 用户授权原话

> 「**INFRA-115t：tests/docs 小项收口** … `tests/inst/README.md` M1 计数 152 → 现场 156；`tests/README.md` 同步 152 → 156。… 生成器 `--check` 是否入 L2：新增一个 `check-generator-sync` 目标 … 若成本过高，列出方案与替代证据后再决定，不要静默不做。」
> （2026-11-01 11:2x，主会话下发；现场核出 `tests/README.md` 已 156、`INVENTORY` 的 `152/156` 语义正确，按“先实测再决定”处理。）

## 完成区

**测试结果**：
- `make check-generator-sync` **rc=0**，6 段 PASS（ctrl-jump/call/ret 3 册、ctrl-br 1、mem 3、isa 6、misc 1、bitcnt；逐段 ~1.2/1.3/1.5/2.0/32.7/2.0 s，合计 **41.2 s** < 120 s 门槛）
- `make check`（L1）**rc=0**：末行 `repository checks (L1): PASS`（`运行期日志（已清理，未归档）`）
- `make check-modules`（L2）**rc=0**：日志末 6 条 `generate_* --check: PASS` + `module checks (L2): PASS`（`运行期日志（已清理，未归档）`）
- `python3 tools/testcases/test_anti_forgery_008t.py` **rc=0**：5×`PASS: inject…` + `PASS: valid reserved case` + `ALL 5 INJECTION + 1 VALID TEST PASSED`；`运行期临时目录` 已自清
- `validate_vectors.py` rc=0：`156/156 M1 identities covered OK`
- 证据脚本 `运行期证据脚本（已清理，未归档）`：默认 **checks=41 failures=0 GREEN rc=0**；`--inject` **checks=9 failures=0 GREEN rc=0**（a 改 misc.yaml 1 字节 ⇒ `FAIL tests/inst/base/misc.yaml: mismatch`；b INJECT1=PASS_CASES ⇒ `FAIL: inject1`；均 `cp`+md5 还原后回绿）

**修改文件**：`tests/inst/README.md`（152→156 条）、`tests/README.md`（L211 措辞列名化，L51/L203 未动）、`tools/testcases/test_anti_forgery_008t.py`（4 处路径 → `tests/inst/base`/`tests/inst/inventory.md`）、`Makefile`（新目标 + `.PHONY` + `_locked-check-modules` 挂载 + 1 行 help）、`docs/Process-07-门控分层规范.md`（+1 行 L2 登记）、`.tao/knowledge/milestones.md`、本任务书；证据 `运行期证据（已清理，未归档）`

**验收结果**：
1. `grep -c 'scope: m1'`=156；`tests/inst/README.md` 含 `**156 条**`；`grep -rn '152 条\|152 行' tests/`=0 ✓
2. INVENTORY 实测 `total=156 deferred=4 covered=152`（`deferred_ids=cfx2rc_crrr_cfx,cfx2rd_crrr_cfx,escape_ciii_cfx,trap_ciii_cfx`）⇒ 与 `152/156` 一致，**该文件零改动**（`git status` 空）✓
3. `全部 byte-identical` 残留=0；列名与 7 个 CLI `--check` 脚本一致（6+`rev`）✓
4. anti_forgery rc=0 + 6 条 PASS；`tests", "vectors"` 残留=0；WORK 自清 ✓
5. `make check-generator-sync` rc=0/6 段；Makefile 命中 4 处（定义/`.PHONY`/挂载/help）；L2 rc=0 且新段在内 ✓
6. Process-07 表 +1 行、层级 **L2**，`git diff` 仅 +1 行 ✓
7. L1 rc=0 ✓；8. 反例 2 条均 FAIL→md5 还原→回绿 ✓；9. `check-milestones-fresh`/`check-tasks` rc=0 ✓；10. 证据脚本 rc 落盘 `last-run.rc`=0 ✓

**新发现/坑**：
- `tests/INVENTORY.md` 的 `152/156` 实测成立（总数 156、整身份 deferred 4、覆盖 152），但**向量级 active id=153**（`escape_ciii_cfx` 有 1 条 active legality；另 5 条 `cs.*` 仅 overlap 一类 deferred）——与文件自身「deferred 身份计未覆盖」定义自洽，故不改；改成 153 会与同文件「m1 cfx 4 未覆盖」矛盾。
- `generate_lit_vectors.py` **无 `--check` 开关**（源码里的 `--check-prefix` 是 FileCheck 参数）；真 `--check` 脚本恰 7 个 = 6（新门控）+ `rev`（L1）。误传 `--check` 会走默认生成路径（产物 byte-identical，`git status` 无 diff）。
- `_locked-check-modules` 上方注释仍写「L2 = 四 scope smoke」，新成员是只读生成器同步（按任务书「只加挂载、不改说明」保留）⇒ 建议后续统一措辞。
- 改 `Makefile` mtime 会使 L2 内 `install-host` 增量重建 qemu（行为不变，耗时上升）。

**遗留问题**：无。F4（L2 注释措辞）按任务书显式保留并已登记，非未完成项。

## 审阅记录

#### 第 1 轮 engineer 自审

审查范围：`Makefile`（新目标/`.PHONY`/挂载/help）、`tests/README.md`/`tests/inst/README.md` 文本、`test_anti_forgery_008t.py` 4 处路径、`docs/Process-07` +1 行、`运行期证据脚本（已清理，未归档）`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 evidence 的「README 列名」断言锚在含 `byte-identical` 的行；本任务已删该词 ⇒ 6 条假 FAIL | ✅已修 | 锚点改为 `make check-generator-sync` 所在行 | 修复后 `checks=41 failures=0 RESULT: GREEN`（修复前 41/6） |
| F2 inject-a 用 `check_rc` 比较 `nonzero`（整数比较会报错）| ✅已修 | 改 `check_eq` 字符串比较 | `--inject` checks=9 failures=0，注入段打印 `FAIL tests/inst/base/misc.yaml: mismatch` |
| F3 `generate_lit_vectors.py` 源码含 `--check-prefix` 字串，易被误判为第 8 个 `--check` 生成器 | ❌不修 | —（无 `--check` 开关；实跑该参数走默认生成路径、产物 byte-identical） | `git status --porcelain` 无 lit 产物改动；6+`rev`=7 与任务书一致 |
| F4 `_locked-check-modules` 上方注释仍写「L2 = 四 scope smoke」，新增成员非 smoke | ⏸延后 | 按任务书「只加挂载、不改该行说明」保留原文 | 完成区「新发现」登记，供 Process-07 后续统一措辞 |
| F5 anti_forgery 断言只有「rc≠0」，未校验 fail 原因 | ❌不修 | —（脚本语义/`PASS_CASES` 按任务书一律不动） | 5 类注入均已打印对应规则行（R2/R8/R4）|
| F6 `make check-modules` 因 `Makefile` mtime 变更触发 qemu 增量重建（成本上升，非功能影响）| ❌不修 | —（`install-host` 前置的既有行为） | L2 日志见 `运行期日志（已清理，未归档）` |

判决：F1–F3 已修并复验；F4 按任务书显式保留（已登记）；F5/F6 不修有据。**无未修 finding** ⇒ 可标「待验收」。

#### 第 1 轮 architect 交叉复核（2026-11-01 13:02，主线授权：无行为代码/纯文档+门控⇒免 reviewer 独立轮）

自跑证据（均在 `运行期临时目录`，与完成区逐条对齐）：

- `make check-generator-sync` **rc=0**，6 段逐段 PASS（ctrl-jump/call/ret 3、ctrl-br 1、mem 3、isa 6、misc 1、bitcnt）
- `python3 tools/testcases/test_anti_forgery_008t.py` **rc=0**：5×`PASS: inject…` + `PASS: valid reserved case`；`运行期临时目录` 已自清
- `make check`（L1）**rc=0**（`repository checks (L1): PASS`）；`make check-modules`（L2）**rc=0**（`module checks (L2): PASS`，含新段 6 条 `--check`）
- `make check-tasks` rc=0；`make check-milestones-fresh` rc=0
- `validate_vectors.py`：`156/156 M1 identities covered OK`

文件集核：`git status -uall` 恰 7 项且逐项落在「修改文件」声明内；`tests/inst/**` YAML、`contracts/`、`spec/`、生成器脚本零改动；`tests/INVENTORY.md` 零改动（其 `152/156` 与实测 deferred=4/覆盖=152 自洽）。
关键抽查：`grep -c 'scope: m1'`=156、`tests/inst/README.md` 含 `**156 条**`、`tests/` 无 `152 条|152 行` 残留、`全部 byte-identical` 在 `tests/` 下 0 残留、脚本内 `tests/vectors` 0 残留、`Makefile` 4 处命中（定义/`.PHONY`/挂载/help）、`docs/Process-07` 仅 +1 行且层级 L2。

判决：**Accepted**（无 finding 遗留；engineer 自审 F1–F3 已修可复核，F4 属任务书显式保留项）。

发现并修：置 `已验证` 后 `check-milestones-fresh` A4 报「L13 QEMU-077t → L14 INFRA-115t 逆序」（完成时间 13:02 > 11:45）⇒ 流水行上移至首行，复跑 rc=0（`PASS (74 行)`）；`make check-tasks` re-rc=0。

遗留（非本任务未完成项）：① `_locked-check-modules` 上方注释仍写「L2 = 四 scope smoke」，建议后续统一措辞；② `.tao/knowledge/discussing.md` 仍留「README 措辞待对齐三生成器」条目，待主会话收尾时清除（子代理不得改该文件）；③ 证据落 `运行期临时目录`（未跟踪，按仓库既有惯例）。
