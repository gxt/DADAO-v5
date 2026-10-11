# TESTCASES-037t: lit 量产（骨架生成 + 期望机械派生，禁反填）

**模块**：testcases
**项目里程碑**：M6
**依赖**：`LLVM-062t`（整数调用约定）、`QEMU-052t`（load_elf）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `contracts/opcodes.yaml` / `contracts/legality_rules.yaml`（**单一真源**）。
  - `spec/Process-05-里程碑TDD规范.md`（三层向量 + 反例门控）、`spec/Process-01-组件补丁组织与构建编排.md`。
  - 既有 lit 体例：`tests/llvm/lit/**`（MC/CodeGen/E2E）、`tests/e2e/lit/**`。
  - `INTEG-023k §A（#19 lit 量产）`（骨架 agent 生成 + 期望值从 `spec`/`contracts` **机械派生**、**禁从 `llc`/QEMU 反填**；目标**数百**；分层：**快档入 `make check`、全量档 opt-in**）。
- **输出**：
  1. **骨架生成器**（落 `tools/testcases/`，随产物入库）：由模板/真源批量生成 lit 用例**骨架**。
  2. **期望值机械派生**：CHECK 串/期望值**由脚本从 `spec`/`contracts` 派生**（**禁**从 `llc`/QEMU 结果反填）。
  3. **分层**：**快档**入 `make check`；**全量档** opt-in（新 target，如 `check-lit-full`，**不进 `make check`**）。
- **约束**：
  - **禁反填**（硬约束）：期望值来源可追溯到 `spec`/`contracts`。
  - **计数不写死**：用例条数/通过数由脚本/门控**现场统计**；门控断言写「**不下降 / 逐项相等**」，**不得**硬编码数字。
  - 生成器**非易失位置**（`tools/testcases/`，入库）；临时产物放 `/tmp/opencode/TESTCASES-037t/`。

## 硬约束

- **临时目录** `/tmp/opencode/TESTCASES-037t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **一键证据脚本** `.work/evidence/TESTCASES-037t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/testcases/TESTCASES-037t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **骨架生成器可用**：给定真源生成 lit 骨架；生成器落 `tools/testcases/`（入库）；可重跑、幂等（给真实输出）。
2. **期望机械派生**：CHECK/期望值由脚本从 `spec`/`contracts` 派生；给「来源可追溯」证据，**无**从 `llc`/QEMU 反填。
3. **规模达标**：用例总数达目标量级（**由脚本现场统计**，任务书/验收**不写死数字**）。
4. **分层生效**：快档入 `make check` 且 EXIT=0；全量档 opt-in target 可跑（给真实输出）。
5. **反例门控**：检查器能对**注入反例**失败（给注入→FAIL→还原→回绿真实输出）。
6. **不回归**：`make check`/`check-lit` EXIT=0（通过数**不下降 / 逐项相等**）。
7. **一键证据脚本**：`.work/evidence/TESTCASES-037t/run.sh` 逐项通过、`RUN_EXIT=0`；给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**用户裁定（原话，落盘）**：「期望值机械派生、禁反填」「快档入 make check、全量档 opt-in」（主会话预检转述 `INTEG-023k §A #19`）。

**测试结果**（计数**现场统计**，不写死）：
- 生成器 `generate_lit_vectors.py`：`opcodes.yaml` **227** 记录 → 正例（可汇编）**217** + 反例（`scope: excluded` 且汇编器不实现）**10**；操作数形态 **22** 类 → 快档每类首条 **22**；全量档 **12** 文件。rc=0。
- `check_lit_gen.py`（结构+编码检查器）：**64 passed / 0 failed**，rc=0。
- `make check-lit`（快档入 `make check`）：**76 discovered / 75 passed / 1 unsupported**，rc=0（改前 **75/74/1**）；`gen-fast.s` 在内且 PASS。
- `make check-lit-full`（opt-in 全量档）：`check_lit_gen` 64 passed + `llvm-lit` **12 discovered / 12 passed**，rc=0。
- `make check`：**EXIT=0**（`repository checks: PASS`；含 `check-interface`/`check_lit_bytes` = **185 patterns OK**，改前 163）。
- 一键证据脚本：**checks PASS=25 FAIL=0，EVIDENCE: PASS，RUN_EXIT=0**。

**修改文件**：新增 `tools/testcases/{generate_lit_vectors.py,check_lit_gen.py}`；新增 `tests/llvm/lit/MC/DADAO/gen-fast.s`；新增 `tests/llvm/lit/MC/DADAO-gen/{lit.cfg.py,gen-{ciii,crrr,iiii,oiii,orri,orrr,riii,rrii,rrri,rrrr,rwii,excluded}.s}`；改 `Makefile`（**仅新增** opt-in 目标 `check-lit-full` + `.PHONY`/help 各一行）；本任务书。（`.work/evidence/TESTCASES-037t/run.sh`、`.work/log/testcases/TESTCASES-037t-*.log` 为工作产物，不入库。）

**验收结果**（一键证据脚本真实输出，`RUN_EXIT=0`）：`PASS A-generator rc rc=0` / `PASS B-idempotent diff files=14 identical`（连跑两次 md5 相等）/ `PASS C-no-backfill rc=1/0-hits`（生成器无 `subprocess` 系调用）/ `PASS D-check_lit_gen rc=0` + `D-regex-hits-proof(§8.34) full-src-hits PASS=11` + `D-structural-pairing(§8.35) full-paired PASS=11` / `PASS E-make check-lit rc=0 (76/75/1)` / `PASS F-make check-lit-full rc=0 (12/12)` / 反例门控 H1–H4 全 `PASS`（注入→FAIL rc=1→`cp`+md5 还原逐字相等→回绿 rc=0）/ `PASS I-make check rc=0`。**耗时**（`/usr/bin/time`，改前 vs 改后 `make check-lit`）：**0.94s / 75 → 1.78s / 76**（+1 用例，受控）。
反例门控明细：`H1` 改 `@enc` → `check_lit_gen` FAIL rc=1；`H2` 改 OBJ 字节 → `llvm-lit` FAIL rc=1（生成产物失败可达）；`H3` 删一条 `@src` → `full-id-set` FAIL rc=1（§8.35 结构收缩可见）；`H4` 删整个 `gen-iiii.s` → `full-file-set` FAIL rc=1；还原均 `cp`+md5 逐字相等（**未用** `git checkout/restore/stash`）。
机械派生来源可追溯：生成器仅读 `contracts/opcodes.yaml`（`op/value/mask/fields`）+ `spec/Toolchain-01 §5`（操作数语法）；生成物每例带 `; @src <record-id> <enc>` 与 `spec_cite`；**无** `llc`/QEMU 反填（`grep subprocess|Popen|os.system` rc=1）；字段级编码由 `llvm-mc`（被测实现）端到端 FileCheck 独立校验。

**新发现/坑**：① `scope: excluded` 的 `lr_*.o`/`sc_*.o` 用 `[rb1]` 触发的是「地址解析错误」而非 `unrecognized`，须用 `[rb1, 0]`（lr 2 操作数 / sc 3 操作数）方稳定命中 `unrecognized instruction mnemonic`。② `ftroot/foroot` 的 `immu6==2` 是**标量 3 操作数**形态（`ftroot rf8, rf9, 2`），**非** `{rf8:rf9}` 组形态；其余 `orri` 块移动用 `{dst}, {src}`。③ `orrr` 字段银行多样（rd/rb/rf 三族的 dst-src-src 顺序一致），可统一按「字段序 → 银行名」机械生成。④ `check_lit_bytes`（`check-interface` 内）会**自动**校验快档新文件，构成快档的第二独立 oracle（生成物在 `MC/DADAO/`，全量档在 `MC/DADAO-gen/` 不入其 glob）。

**遗留问题**：无未修 finding。① 快档取「每操作数形态首条」= 受控子集（**宁少勿滥**）；如需更宽快档，扩 `shape` 选取即可（生成器一处）。② `check_lit_gen` 的 `full-enc` 校验 `@enc==OBJ`+`(word&mask)==value`+mnemonic，字段级正确性由 `make check-lit-full` 的 `llvm-lit`（`llvm-mc` 端到端）承担——两层互补，未加「生成器内重算字段」冗余实现。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：`tools/testcases/generate_lit_vectors.py`（真源遍历 / 逐 format 操作数生成 / `_selfcheck` / 渲染）、`tools/testcases/check_lit_gen.py`（正则 / 结构断言 / 编码校验）、`tests/llvm/lit/MC/DADAO-gen/lit.cfg.py`、`Makefile`（`check-lit-full`）、`.work/evidence/TESTCASES-037t/run.sh`。

**核对**：Spec-first（`contracts/opcodes.yaml` + `spec/Toolchain-01 §5` 操作数语法表）、防造假（真实执行、结尾 `rc=$?` 无 `tee`、注入 FAIL 可达且 `cp`+md5 还原）、边界（仅 `tests/**`、`tools/testcases/**`、`Makefile`、本任务书；未触 `spec/`/`contracts/`/`components/`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 生成器可能产出「不可判定」OBJ（word 命中多条 opcodes 记录） | ✅已修 | 新增 `_selfcheck`：逐例断言 `(word&mask)==value` **唯一**命中且 mnemonic 一致，否则 `SystemExit` | 217 条正例全通过自检；歧义即生成中止（非静默） |
| F2 反例（excluded）用 `[rb1]` 命中「地址解析错误」而非 `unrecognized` | ✅已修 | 改 `[rb1, 0]`（lr 2 操作数 / sc 3 操作数） | `gen-excluded.s` lit PASS；`make check-lit-full` 12/12 |
| F3 检查器仅比 `(word&mask)==value` 会漏字段级注入 | ✅已修 | `@src` 携带 `<enc>`，`full-enc` 逐条断言 `enc==OBJ` | H1 改 `@enc` → `FAIL full-enc` rc=1；H2 改 OBJ 字节 → `llvm-lit` FAIL rc=1 |
| F4 §8.34/§8.35 同类缺陷（0 命中全绿 / 删一条静默收缩） | ✅已修 | 检查器逐文件断言 `*-src-hits`/`*-obj-hits`>0（命中自证）+ `*-paired`/`*-id-set`/`full-file-set`/`full-coverage` 结构断言 | H3 删一条 `@src` → `full-id-set` FAIL rc=1；H4 删整文件 → `full-file-set` FAIL rc=1 |
| F5 生成器 docstring 含 `subprocess`/`os.system` 字面 token 致「无反填」检查误报 | ✅已修 | 改写措辞，杜绝字面 token | `grep -nE 'subprocess\|Popen\|os\.system' generate_lit_vectors.py` rc=1 |
| F6 快档误把「数百」塞入 `make check` | ✅已修 | 快档仅「每操作数形态首条」（22 例/1 文件）；全量档入 `DADAO-gen` + opt-in `check-lit-full` | `make check-lit` 75→76 discovered（+1），0.94s→1.78s；全量 12 文件不入门控 |

**判决**：无未修 finding（F1–F6 均 ✅已修并附真实输出）⇒ 状态置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 亲自执行，rc=命令自身退出码；日志 `/tmp/opencode/TESTCASES-037t-review/`）：
1. **幂等**：`python3 tools/testcases/generate_lit_vectors.py` ×2，rc=0/0；14 产物 md5 run0=run1=run2（`diff` rc=0×2），`git status` 快照无变化。
2. **独立性**：`grep -nE 'subprocess|Popen|os\.system|llc|llvm-mc|qemu'` 仅命中注释/渲染模板串（L8/273/342/366），**无任何调用**；独立重算 8 条（reviewer 自写 `recompute.py`，人工读 ASM 派字段赋值，不 import 生成器）：add.o_orrr_bbd / ext.so_orri_rd / add.si_riii_rb / br.eq_rrii_rd / ldm.o_rrri_ra / st.w_rrii_rd / br.nz_riii_rb / ftroot_orri_rf 全 PASS（`recomputed==@enc==OBJ` 且 `(word&mask)==value`），rc=0。
3. **门控接线**：`check_lit_gen.py` 仅由 `check-lit-full`（Makefile:447）调用；`make check`（L348）含 `check-lit`、**不含** `check-lit-full` ✓；快档双 oracle 入 `make check`（`check-lit` 端到端 + `check-interface→check_lit_bytes` **185 patterns = 改前 163 + gen-fast.s 22 OBJ**）。**标注（非阻断）**：`DADAO-gen/` 结构完整性仅 opt-in 校验，contracts 漂移时 `make check` 不报警——受「全量档不进 make check」+「Makefile 只加新 opt-in target」双重范围约束，属必然结果；是否另立任务扩常驻门控，供架构师定夺。
4. **规模/耗时**：生成器现场统计 227 记录→正例 217+反例 10、shape 22（快档 22 条/1 文件）、全量 12 文件；`make check-lit` rc=0 **76/75/1**（`/usr/bin/time` 0.95s）；`llvm-lit --filter='^(?!.*gen-fast)'` 排除后 **75/74/1**（=改前，0.45s）——计数与完成区逐项一致；秒数同为亚秒级（负载差异，非造假）。
5. **检查器源码**（`check_lit_gen.py`）：命中自证 L96-99（src/obj-hits>0）、成对 L101-102、id-set L106-107、file-set L160-163、coverage L165-167、编码 L108-122；各断言均有可达 FAIL 路径（下述注入证）。
6. **独立注入**（非 H1–H4）：① 新增游离 `gen-stray.s` ⇒ rc=1 `FAIL full-file-set extra=['stray']`（+src/obj-hits FAIL）；② `gen-orri.s` 改 `@src …_TAMPERED` ⇒ rc=1 `FAIL full-id-set`+`full-coverage`。还原 `rm`/`cp`+md5（9b7f27e3…=备份逐字相等），回绿 rc=0 `64 passed/0 failed`；`git status` 快照 `diff` rc=0（**未用** git checkout/restore/stash）。
7. **门控**：`make check-lit` rc=0（76/75/1）；`make check-lit-full` rc=0（check_lit_gen 64 passed + lit 12/12）；`make check` rc=0（`repository checks: PASS`）；`run.sh` 重跑 **PASS=25 FAIL=0，RUN_EXIT=0**（脚本已源码审计：断言均有 FAIL 路径、注入非空校验、cp+md5 还原、结尾 `exit $rc` 无 tee）。
8. **范围/残留**：`git status` 仅 `Makefile`+本任务书（M）+声明新增（??）；`(spec|contracts|components)/` 交集**空**；无 `_tmp/.orig/.rej`；`Makefile` diff 3 hunk **纯新增**（.PHONY+help+`check-lit-full`），`check:` 与既有断言未动，既有 lit 用例零修改/零删除。

**约束核验**：禁反填 ✓（生成器仅读 `contracts/opcodes.yaml`，机械遍历全 227 记录，未覆盖即 ValueError 失败，无人工挑拣）；计数不写死 ✓（检查器集合比较、门控无硬编码门限）；生成器入库幂等 ✓；分层 ✓；`tools/testcases/` 入库 ✓。

**判决**：**Accepted**——判据 1–8 经独立重跑全部证实、反例门控可失败且可还原；第 3 条标注项为范围约束下的设计结果（非缺陷），供架构师定夺。
