# TESTCASES-086t: reserved cfx 异常期望修正（ctrl-ret[9] 及同类审计）

**模块**：testcases
**项目里程碑**：M10
**依赖**：`INTEG-038t`（已验证；引入「reserved cfx（6–14、19–61）⇒ CFXMEM」）、`INTEG-049t`（已验证；A/B 证明该红为 pre-existing 并登记遗留）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库 `/mnt/tao/DADAO-v5`，分支 `TESTCASES-086t`）。QEMU 安装根 `.dadao/cross-toolchain/bin/qemu-system-dadao`（现场存在，mtime `2026-10-31 14:39`）；trampoline `tools/testcases/lib/trampoline.bin`；单例 runner `tools/testcases/lib/run_qemu_test.py`；载体门控 `tools/qemu/semantics_gate.py`（经 `make check-inst`）。

## 用户授权原话（主会话转述；用户原话含「安排」）
> 在 /mnt/tao/DADAO-v5，master 干净。创建 `TESTCASES-086t` 任务书：修正 `tests/inst` 中 reserved cfx 访问的旧异常期望（至少 `tests/inst/base/ctrl-ret.yaml[9]`）。文件名放 `.tao/tasks/testcases/`；先确认 086 未占用。
>
> 1. 审计 `tests/inst/**` 中 reserved cfxha 普通 ld/st 的异常期望，不只看 ctrl-ret[9]；找出所有同类旧期望。
> 2. 把期望改为与 `DADAO-12 §2.1/§5` 一致（reserved cfx 普通 ld/st ⇒ `CFXMEM`；trap/escape 到 reserved ⇒ `ILLI`；不要一刀切）。
> 3. 更新对应 case ledger/清单/文档（若需要），不改 QEMU/spec/ADR。
> 4. 验收：`run_qemu_test.py tests/inst/base/ctrl-ret.yaml --case 9` 通过；`make check-inst` rc=0；L1/L2；必要时 `check-full` 的 `inst:base` 不再红；证据注入（把期望改回 UNMAPPED ⇒ FAIL ⇒ 还原回绿）。
> 5. 不跑夜跑/长套件；`check-full` 只在收尾前按需跑单成员 `inst:base`，不跑全量。

用户授权词（逐字）：「**安排**」。

## 背景（实测，非推测）

1. `INTEG-038t`（commit `e601034b`，2026-10-29）落地地址空间 Step 1：`addr[47:42]` 选 cfxha，**reserved cfx（6–14、19–61）** 的普通 `ld/st`／取指 ⇒ `CFXMEM`（`0x81`）；已分配 cfx 在 RAM/ROM 之外仍为测试机历史约定 `unmapped`（`0x87`）。
2. `tests/inst/base/ctrl-ret.yaml[9]` 末次改动 `7fce080d`（TESTCASES-072t，2026-10-27），**早于** `e601034b`，仍期望 `UNMAPPED`。
3. 现场单例复现（architect 本会话实测）：`python3 tools/testcases/lib/run_qemu_test.py tests/inst/base/ctrl-ret.yaml --case 9` ⇒ **rc=1**，输出 `Exit code: 0x81` / `Status: FAIL - Expected UNMAPPED, got CFXMEM`；日志 `/tmp/opencode/TESTCASES-086t/baseline.log`。
4. `make check-inst`（上次运行日志 `.work/log/qemu/check-inst.log`）为 `978 total, 972 passed, 1 failed, 5 deferred`，唯一红项即该例。
5. 该例语义：`ret` 从 MemRAS 弹出返回目标 `0xBBBB00000000`；`(0xBBBB00000000 >> 42) & 0x3F = 46` ∈ `19–61` ⇒ **reserved cfxha** ⇒ 取指 `CFXMEM`（目标 cfx46）。RAS 在取指前已消费，故该例只能是 `legality`。

## 问题根源

期望值来源滞后于已冻结的 spec 口径：`ctrl-ret.yaml` 是**生成物**（文件头 `DO NOT EDIT`），首行事实源是 `tools/testcases/generate_ctrl_jump_call_ret.py`；`INTEG-038t` 只改实现/spec，未回头修生成器与产物，于是「spec 已改 + 生成器/向量/ledger 未改」形成三处不一致（生成器注释与常量、向量 `[9]`、`tests/case-ledger.tsv` 的 fault 列）。

`ADR-0004 D5.8` 的码表未变：`CFXMEM = 0x80|(1<<1) = 0x81`、`unmapped = 0x87`（测试机约定、无 spec cause）。**不是码表变更，是分类归属变更**。

## 目标（范围）

1. **修生成器（真源）**：`tools/testcases/generate_ctrl_jump_call_ret.py` 中 D4b「非 RAM 返回目标」用例改为 `CFXMEM`；同步常量 `SC_RET_D4B_UNMAPPED`（改名 `..._CFXMEM`）、`spec_cite`、`notes`，以及 3 处描述「0xBBBB… ⇒ UNMAPPED(0x87)」的注释（约 :444、:468、:587 段）。**只改该例，不动其它 9 例 ret 语义/序号**。
2. **再生成产物**：重跑生成器，`tests/inst/base/ctrl-ret.yaml` 随之更新；`ctrl-jump.yaml`/`ctrl-call.yaml` 必须 **byte-identical**（`git status` 只允许 ctrl-ret.yaml 变）。
3. **期望值**（`[9]`）：`expected_fault: CFXMEM`；`class: legality`、`expected_pc: null`、`expected_state: null` 不变；`notes` 写明 `cfxha 46（reserved，19–61）→ 取指 CFXMEM (0x81)`；`spec_cite` 增引 `DADAO-12: 核内地址空间`（不带 `§`）与 `DADAO-12: 异常进入流程`（保留原有 SimRISC/ADR 段，`;` 分段）。
4. **ledger 同步**：`tests/case-ledger.tsv` 由 `python3 tools/infra/check_case_ledger.py --write` 重生成；**允许且仅允许** `ctrl-ret.yaml … UNMAPPED` 那一行变为 `CFXMEM`（行数不变）。其它清单（`tests/inst/inventory.md`、`tests/INVENTORY.md`）为覆盖矩阵/身份盘点，**不含 fault 期望 ⇒ 不改**。
5. **审计（不是只改一处）**：对 `tests/inst/**` 全部 1454 例（门控载体集 978 例）逐条判定「目标地址 cfxha → 期望 fault 是否与 spec 一致」，产出清单（文件[序号] / 目标或基址 / cfxha / 现行期望 / 依据 / 判定）。至少覆盖下表基线；审计须**机械可复跑**（写进证据脚本，不靠肉眼）。
6. **证据**：`.work/evidence/<任务ID>/run.sh` 一键跑验收 + 注入反例（期望改回 `UNMAPPED` ⇒ 单例 FAIL ⇒ `cp` 还原 + md5 对账 ⇒ 回绿）。

## 接口规范（期望值定义，Spec-first）

- 目标地址 `0xBBBB00000000`：`addr[47:42] = 46` ∈ reserved（19–61）⇒ 该 cfx 段内非法取指 ⇒ **`CFXMEM`**，目标 cfxha 46。[DADAO-12 §2.1 核内地址空间；§5.2 异常进入流程「CFXMEM … 否则根据地址高 6 位指定 cfxha」；Machine-01 §异常码「CFXMEM 适用核内地址空间内的非法访问/取指」]
- `trap`/`escape` 到 reserved cfx ⇒ **`ILLI`**（不是 CFXMEM）。[DADAO-12 §5.1]
- 已分配 cfx（如 62 `uart`）在 RAM/ROM 之外 ⇒ 仍 **`UNMAPPED`（0x87）**，本轮**不得**改。[Machine-01「其余未映射地址 ⇒ 0x87」]
- `addr[47:42]=0` 且 `ptw_enable=0` 的普通访存/取指 ⇒ `CFXMEM`（原有 32 例 CFXMEM 即此形态，**不变**）。
- 码表：`CFXMEM=0x81`（`0x80|1<<1`）、`unmapped=0x87`。[ADR-0004 D5.8；ADR-0020 D15]

## 审计基线（architect 实测；engineer 须独立复核并出具清单）

现场统计：`tests/inst/**` 共 **1454** 例；`expected_fault` 非空的分布 = `UNMAPPED` 12、`CFXMEM` 32、其余 `ILLI`/`MALIGN`/`RASOF`/`RASUF`/`UNDI`。

- **`UNMAPPED` 12 例**：`ctrl-br.yaml[3,7,11,15,19,23,27,31,35,39]`（目标 `0xFBFFFFFFC000` / `0xFBFFFFFFF000` ⇒ cfxha **62**，已分配 `uart`）、`ctrl-jump.yaml[2]`（同 62）、`ctrl-ret.yaml[9]`（`0xBBBB00000000` ⇒ cfxha **46**，reserved）。
  ⇒ **只有 `ctrl-ret.yaml[9]` 错**；其余 11 例 cfxha=62 属「已分配 cfx 的 RAM/ROM 之外」，保持 `0x87`。
- **`CFXMEM` 32 例**：`ctrl-call[10]`、`ctrl-jump[5]`、`mem-ra[2,7,13,19]`、`mem-rb[3,8,14,20]`、`mem-rd` 22 例 —— 均为 `base=0` / `ptw_enable=0` 的 `addr[47:42]=0` 形态，**正确、不改**。
- **reserved cfx 的普通 `ld/st`**：现有向量**无**此类（`ld/st/ldm/stm/lr/sc` 的基址寄存器现场只有 cfx63 RAM）⇒ 无「一刀切改 fault」的对象；**本轮不新增用例**（覆盖缺口见「遗留」）。
- **`trap`/`escape` 到 reserved ⇒ `ILLI`**：`tests/inst/inventory.md` 中 `trap_ciii_cfx`/`escape_ciii_cfx` 全列 `deferred TESTCASES-033t`，`tests/inst/**` 无 active 向量；该 ILLI 语义由 `tests/unit/llvm/lit/MC/DADAO/cfx2-trap-escape*.s` 与 arch 探针覆盖 ⇒ **本轮不改、不复制**。

## 验收标准

1. `python3 tools/testcases/lib/run_qemu_test.py tests/inst/base/ctrl-ret.yaml --case 9` ⇒ **rc=0**（修前 rc=1 已实测）。
2. `tests/inst/base/ctrl-ret.yaml[9]`：`expected_fault: CFXMEM`；`notes` 含 `cfxha 46` 与 `CFXMEM (0x81)`；`spec_cite` 含 `DADAO-12: 核内地址空间` 与 `DADAO-12: 异常进入流程`（不带 `§`）；其余字段（`class`/`encoding.word`/`input_state`/`expected_pc`/`expected_state`/`status`）与修前一致。
3. 生成器重跑后 `git status --porcelain -uall` 只显示 `tests/inst/base/ctrl-ret.yaml`（另两册 byte-identical；若漂移 ⇒ 停下报告，不得顺带接受）。
4. `make check-inst` ⇒ **rc=0**，`failed=0 errors=0`（total/deferred 以现场输出为准，须与修前 978/5 一致）。
5. L1 `make check` rc=0；L2 `make check-modules` rc=0。
6. 收尾前按需单成员 L3：`python3 tools/testcases/l3_run.py --member 'inst:base=make check-inst'` ⇒ `check-full: PASS (1/1 member(s) green)`；**不跑**全量 `check-full`、不跑 `check-night`。
7. 审计清单落完成区（≤30 行限长 ⇒ 明细写 `.work/evidence/<任务ID>/audit.tsv`）：覆盖 12 例 `UNMAPPED` + 32 例 `CFXMEM` 逐条判定，结论与「审计基线」一致或给出差异与本任务处置。
8. 证据脚本 `.work/evidence/<任务ID>/run.sh` rc=0：含**注入→FAIL→还原→回绿**真实输出（`cp` 备份 ctrl-ret.yaml + md5 对账；注入 = 把 `[9]` 的 `CFXMEM` 改回 `UNMAPPED`，单例 rc=1 且含 `Expected UNMAPPED`）；**禁** `git checkout/restore/stash/show` 还原。
9. `python3 tools/testcases/validate_vectors.py` rc=0；`python3 tools/infra/check_case_ledger.py` rc=0（重生成后）；`python3 tools/spec/check_spec_cite_targets.py` rc=0。
10. `git status --untracked-files=all` 无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 等临时残留；`.work/evidence/<任务ID>/` 有脚本 + 日志（不入库）。

## 约束

- **只改**「文件范围」列出的文件；不改 QEMU/`components/**`、`spec/**`、`.tao/adr/**`、`.tao/contracts/**`、`contracts/**`、`Makefile`、其它向量册、`tests/unit/**`、`tests/arch/**`。
- **不新增/删除用例**、不改用例序号与 `id`；本轮只修期望值 + 生成器真源。审计发现「缺 reserved cfx ld/st 覆盖」⇒ 写完成区遗留，不擅自加 vector。
- 不改 `UNMAPPED=0x87` 的 11 例（cfxha 62）；不改 32 例 `CFXMEM`（cfx0/ptw-off）。
- 不跑夜跑/长套件；单成员 L3 仅在收尾前跑一次。
- 临时目录 `/tmp/opencode/TESTCASES-086t/`；不提交、不 push（提交权归 architect）。
- 失败保留现场并继续推进（自行处置 / 有据重试并记次数）；只在需用户语义裁定时留问。
- 完成区 ≤30 行；每轮审阅记录 ≤40 行；长输出留 `.work/log/testcases/` 或 `.work/evidence/`。

## 文件范围（计划修改）

1. `tools/testcases/generate_ctrl_jump_call_ret.py`（真源：常量/注释/notes/fault）
2. `tests/inst/base/ctrl-ret.yaml`（生成物，重跑生成器）
3. `tests/case-ledger.tsv`（`check_case_ledger.py --write`；期望仅 `ctrl-ret.yaml` 一行 fault 列变化）
4. `.work/evidence/<任务ID>/{run.sh,audit.tsv,*.log}`（不入库）

**明确不改**：`tests/inst/base/ctrl-jump.yaml`、`tests/inst/base/ctrl-call.yaml`（生成器重跑须 byte-identical）、`tests/inst/inventory.md`、`tests/INVENTORY.md`、`tests/README.md`。

## 下发前预检（5 项，architect 现场结论）

1. **任务书内部一致：PASS** —— 验收命令与文件范围一一对应；「不改 QEMU/spec」与「修期望值」无冲突；`make check-inst` 即 L3 的 `inst:base` 成员（`l3_run.py` 默认清单 `("inst","base","make check-inst")`），故第 6 条与第 4 条同源、不重复执行。
2. **本任务验证手段的全部前置可用：PASS（实测）** —— ① QEMU 二进制存在且可执行（`-rwxrwxr-x … qemu-system-dadao`）；② `run_qemu_test.py --help` 正常（`--case` 可指定 0-based 序号）；③ trampoline 存在；④ `make check-inst` 目标与 `semantics_gate.py` 存在；⑤ `l3_run.py --help` 含 `--member`；⑥ 单例基线已复现 rc=1（`/tmp/opencode/TESTCASES-086t/baseline.log`）。
3. **验收逐条可跑性**：1/2/3/4/5/6/8/9/10 均「现在可跑」；7 为审计产出（无外部依赖）。**BLOCKED：无**。全量 `check-full`/`check-night` 按用户要求**不跑**（非 BLOCKED，是范围排除）。
4. **与 `contracts/`、`tests/inst/` 一致：PASS** —— `.tao/contracts/contract-see.md`：「保留 cfx（6–14、19–61）的普通 `ld/st` 也触发 `CFXMEM`；`0x87` 为测试机约定、无 spec cause」；`spec/Machine-01` §异常码同口径（含「非法访问/取指」）；`tests/inst/schema.md` 的 `expected_fault` 允许 `CFXMEM`；`contracts/*.yaml` 无 fault 期望表 ⇒ 无需改合约数据。
5. **拟改文件 × `spec/` 清单：0 命中** —— 4 个拟改路径均在 `tools/`、`tests/`、`.work/` 下，不触 `spec/**` ⇒ 无需 spec 锁 sha / changelog 更新，也无需用户额外授权。

## 已知旁证（不在本任务修，完成区「新发现」登记）

`components/qemu/patches/target/dadao/helper.c.patch:847` 的注释写 `reserved cfxha (7-14, 19-61)`，而宏 `DADAO_CFX_IS_RESERVED` 是 `6–14`（`cpu.h:166`）；**仅注释笔误**，实现正确。修它要动组件补丁 + 重建，**超出本任务范围**；请 engineer 在完成区登记，由主会话决定是否另立 issue。

## 完成区

**测试结果**：通过 20/20（`.work/evidence/TESTCASES-086t/run.sh` rc=0，含注入反例）；失败：无。
**修改文件**：
1. `tools/testcases/generate_ctrl_jump_call_ret.py`（常量改名 `SC_RET_D4B_CFXMEM`、spec_cite 增 DADAO-12 两段、fault/notes/4 处注释；另 docstring 与 [2] 交叉引用中的 UNMAPPED 字样同步为 CFXMEM，非语义）
2. `tests/inst/base/ctrl-ret.yaml`（生成物；[9] fault→CFXMEM、notes/spec_cite 更新；[2] 仅 notes 交叉引用字样）
3. `tests/case-ledger.tsv`（`check_case_ledger.py --write`；git diff = 1 增 1 删，仅 ctrl-ret 该身份 fault 列）
4. `.work/evidence/TESTCASES-086t/{run.sh,audit.py,logs/audit-baseline.tsv,logs/audit-worktree.tsv,logs/*.log}`（不入库；第 2 轮 F1 返工后 `audit.tsv`/`audit-HEAD.tsv` 更名为 `logs/audit-baseline.tsv`/`logs/audit-worktree.tsv`）
**验收结果**（真实输出）：
- 单例：`run_qemu_test.py tests/inst/base/ctrl-ret.yaml --case 9` rc=0，`Status: PASS - Expected CFXMEM, got CFXMEM`（修前 rc=1）。
- `make check-inst` rc=0：`check-inst: PASS（973/978，载体 20 册）`，5 deferred（=978，failed=0 errors=0）。
- L1 `make check` rc=0；L2 `make check-modules` rc=0（`module checks (L2): PASS`）。
- L3 单成员：`l3_run.py --member 'inst:base=make check-inst'` rc=0，`check-full: PASS (1/1 member(s) green)`。
- `validate_vectors` rc=0（708 cases）；`check_case_ledger` rc=0；`check_spec_cite_targets` rc=0（unresolved=0）。
- 审计：基线 `9d334a1d`（修前）44 例 = 12 UNMAPPED + 32 CFXMEM，恰好 `ctrl-ret[9]` INCONSISTENT（rc=1，反例路径可达）；工作树 11+33 全 OK（rc=0）；两版仅 `ctrl-ret[9]` UNMAPPED(46)→CFXMEM(46) 变化。cfxha 62 的 11 例 UNMAPPED、cfx0 的 32 例 CFXMEM 均判 OK。
- 注入：`[9]` CFXMEM→UNMAPPED（md5 变）⇒ 单例 rc=1 且 `Expected UNMAPPED` ⇒ `cp` 还原、md5 `86858a…` 复原 ⇒ 单例 rc=0。旁册 `git diff --quiet` rc=0。
**新发现/坑**：① **生成器输出路径已漂移**：`generate_ctrl_jump_call_ret.py` 的 `OUT_DIR` 仍是 `tests/vectors/isa`（TESTCASES-072t 迁移后未更新；`generate_ctrl_br.py` 同病），重跑不会更新 `tests/inst/base`。本任务用「重跑到 tests/vectors/isa → diff 逐字节核对 → `cp` 单册」落地，并在 run.sh 建 `generator-reproducible` 检查（跑完即删该未跟踪目录，防残留）；**未擅自改 OUT_DIR**。② `components/qemu/patches/.../helper.c.patch:847` 注释 `7-14` 与宏 `6–14` 不一致（仅注释，超范围）。③ ledger 行因排序换位（增 1 删 1），非整表重排。
**遗留问题**：① reserved cfx 的普通 ld/st 仍无 active 向量（覆盖缺口，按任务书不新增用例）；② `generate_ctrl_jump_call_ret.py`/`generate_ctrl_br.py` 的 `OUT_DIR` 漂移待另立任务修；③ helper.c.patch 注释笔误待另立 issue。

## 审阅记录

#### 第 1 轮 engineer 自审

逐行审查 `generate_ctrl_jump_call_ret.py`、`ctrl-ret.yaml`、`case-ledger.tsv` 与证据脚本，findings/处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 run.sh 的 `expect_fail` 多传了 `"nonzero"` 形参，被当成命令 → rc=127 假 PASS | ✅已修 | 删除两处多余形参 | 重跑 `run.sh` rc=0，`audit-HEAD-catches-old rc=1 PASS`、`inject-single-case-9 rc=1 PASS` |
| F2 ledger 断言用 BRE `\t`（匹配不到制表符），可能假绿/假红 | ✅已修 | 改 `grep -P '^\+vector\t…'` | `ledger-one-line rc=0`（1 增 1 删逐字匹配） |
| F3 注入只按首个 `CFXMEM` 替换，若同册多例会注入错对象 | ✅已修 | 注入前断言 `grep -c '^  expected_fault: CFXMEM$' == 1` | `injection-unique-target CFXMEM lines=1 PASS` |
| F4 注入了还要证明「注入生效」，不能只看 git status | ✅已修 | 注入后 md5 与备份比对必须变化；还原后再次比对 | `injection-applied md5 changed`、`restore-md5 86858a…==86858a…` |
| F5 审计脚本须有可达 FAIL 路径，不能恒绿 | ✅已修 | 对 HEAD 跑同一审计，断言恰 `ctrl-ret[9]` INCONSISTENT | HEAD rc=1 且 `found ctrl-ret[9]`；工作树 rc=0；两版 diff 仅该行 |
| F6 生成器 `OUT_DIR=tests/vectors/isa` 漂移，重跑不更新 `inst/base`，「生成物可复现」无法直接验证 | ✅已修（检查层） | run.sh 增 `generator-reproducible`：重跑→逐字节 diff 三册→`trap` 清理未跟踪 `tests/vectors` | `generator-reproducible rc=0`；`ls tests/vectors` 不存在；`git status` 仅 3 个计划内文件 |
| F7 `[2]` 的 notes 交叉引用仍写「legality UNMAPPED 用例」，指向已改名用例 | ✅已修 | 同步为「legality CFXMEM 用例」（非语义、同册内） | 已在 yaml diff 中披露；[2] 除该字样外字节不变 |
| F8 范围自查：未动 QEMU/spec/ADR/其它册/用例数；[9] 的 class/word/input_state/expected_pc/expected_state/status 未变 | ✅确认 | — | run.sh `yaml-case9-fields`；`sibling-vectors-identical`；ledger 1 增 1 删 |

判决：findings 全部处置，无未修项 ⇒ 状态置 `待验收`。

#### 第 1 轮 reviewer 验收（2026-10-31，reviewer 独立重跑，不采信叙述）

**重跑记录（真实输出/退出码）**：① 分支 `TESTCASES-086t`、HEAD=`8f0705ff`、`git status --porcelain -uall` 验收前后均干净；`git diff master...HEAD --stat` = 3 实现文件 + 任务书 + milestones 行（立任务提交），与完成区对账一致；`components/spec/.tao/adr/contracts/Makefile/tests/unit/tests/arch` 命中 0（grep rc=1）。② 单例 `run_qemu_test.py ctrl-ret.yaml --case 9` rc=0（`Expected CFXMEM, got CFXMEM`）。③ `make check-inst` rc=0：`978 total, 973 passed, 0 failed, 5 deferred`。④ `make check` **rc=2**（见 F2）；`make check-modules` rc=0（L2 PASS）；`l3_run.py --member 'inst:base=make check-inst'` rc=0（`check-full: PASS (1/1)`）；未跑全量/夜跑。⑤ `validate_vectors` rc=0（708 cases）、`check_case_ledger` rc=0、`check_spec_cite_targets` rc=0。

**审计/一致性（reviewer 独立复算）**：全量重扫 `tests/inst/**` = 1454 例，工作树 UNMAPPED 11 / CFXMEM 33（其余 ILLI 195/MALIGN 51/RASOF 1/RASUF 2/UNDI 3）；`audit.py --rev master` rc=1 恰抓 `ctrl-ret[9] INCONSISTENT`，工作树 rc=0，两版 diff 仅该行 UNMAPPED→CFXMEM（cfxha 均 46）。32 例 CFXMEM 逐一核 cfxha=0（cfx0/ptw-off 形态，正确）；11 例 UNMAPPED 目标 cfxha=62（uart，正确）。yaml 深比对 master：仅 [9]（fault/notes/spec_cite）与 [2]（notes 交叉引用字样，已披露）差异，[9] 其余字段（class/word/input_state/expected_pc/expected_state/status）与 master 逐字段一致。`ctrl-jump.yaml`/`ctrl-call.yaml` 对 master `git diff --quiet` rc=0（byte-identical）。ledger git diff = 1 增 1删，仅该身份 fault 列（排序位移）。无 QEMU/spec/ADR 改动。

**证据脚本与注入**：`.work/evidence/TESTCASES-086t/run.sh` 重跑 **rc=1**（见 F1）；其中注入段全 PASS：CFXMEM→UNMAPPED（md5 变化）⇒ 单例 rc=1 含 `Expected UNMAPPED` ⇒ cp 还原 md5 `86858af1…==86858af1…` ⇒ 回绿 rc=0。reviewer 另做独立注入（非 engineer 点，改 ledger 该行 CFXMEM→UNMAPPED，cp `/tmp/opencode/TESTCASES-086t-review/` + md5 纪律）：`check_case_ledger.py` rc=1（缺 1 行/多 1 行）⇒ 还原 md5 `915c97cb…` 一致 ⇒ 回绿 rc=0。禁 `git checkout/restore` 纪律遵守。

**其它核验**：生成器 `OUT_DIR=tests/vectors/isa` 旧路径未改（两册生成器同病）、`helper.c.patch:641/847` 注释 `7-14` 未改——均登记遗留，符合「不擅自改」约束；reserved ld/st 无 active 向量（`reserved.yaml` 3 例均 UNDI；trap/escape cfx 全 deferred 033t）——覆盖缺口属实、按任务书不新增。完成区 18 行、自审轮 16 行（限长合规）；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`tests/vectors` 残留；`.work/evidence/…/{run.sh,audit.py,*.tsv,logs/}` 与 `.work/log/testcases/TESTCASES-086t-*.log` 齐全。

**F1（阻断）**：`run.sh` 提交后不可复跑（rc=1，3 项 FAIL）：`ledger-one-line`/`audit-only-one-change` 依赖「工作树 vs HEAD」diff、`audit-HEAD-catches-old` 用 `--rev HEAD`，architect 提交 `8f0705ff` 后 HEAD 已含修复 ⇒ 三检查必然失效，验收标准 8「run.sh rc=0」当前不可复现。**修复建议**：基线钉死为不可变引用——`--rev master`（或 `3f9fc8e3`）；ledger 比对改 `git diff -U0 master -- tests/case-ledger.tsv`；`sibling-vectors-identical` 建议加 `git diff --quiet master --`；改后重跑 rc=0。

**F2（非 engineer 缺陷，流程内）**：L1 rc=2 唯一红项 `check-milestones-fresh`：流水行 `TESTCASES-086t 表=待开始` ≠ 任务书 `待验收`（状态翻转在 15:06 L1 绿之后、随提交入库）。由 `/complete` 主会话同步 `**状态**`+流水行即回绿，其余 L1 检查全 PASS（已逐项核输出）。**F3（文档级）**：run.sh 注释段号「# 4.」重复（旁册段/ledger 段），不阻断。

**判决：Needs Revision** —— 仅 F1 指名失败项（`run.sh` rc=1）；实现本体（yaml/生成器/ledger/审计/门控）经独立重跑与反例注入全部核实合格，修 F1 一处脚本 ref 后即可再验收。
#### 第 1 轮 architect 提交审核（2026-10-31）

- **分支/现场**：`TESTCASES-086t`；`git status --porcelain -uall` 仅 4 项（本任务书 + 3 个实现文件），无未跟踪残留、无 `tests/vectors`。
- **档位**：**正常提交**（协调者本轮显式指定消息 `fix(testcases): TESTCASES-086t reserved cfx 异常期望`）。**偏离默认规则披露**：状态仍 `待验收`、reviewer 未判决，按默认应 `WIP:`；本次按用户指令执行，reviewer 通过后不另改消息。
- **文件集对账**：显式 staging 4 项 = 完成区「修改文件」3 项（生成器 / ctrl-ret.yaml / case-ledger.tsv）+ 本任务书（流程记录）；**无漏提 / 多提 / 越界**。`.work/evidence/**` 与 `/tmp` 证据不入库；`milestones.md` 未改，其任务行 `待开始` 由主会话在 `/complete` 更新。
- **独立复核（architect 现场实测，不采信叙述）**：单例 `--case 9` rc=0（`Expected CFXMEM, got CFXMEM`）；`check_case_ledger.py` / `validate_vectors.py` / `check_spec_cite_targets.py` 均 rc=0；重跑生成器后三册逐字节一致（`diff` rc=0，跑完 `tests/vectors` 已清、`git status` 无新项）；worktree `expected_fault` = UNMAPPED 11 / CFXMEM 33，HEAD = 12 / 32，差集仅 `ctrl-ret[9]`；`ctrl-jump.yaml`/`ctrl-call.yaml` 对 HEAD `git diff --quiet` rc=0；`components/`、`spec/`、`.tao/adr/`、`contracts/`、`Makefile` 0 改动。
- **证据脚本复核**：重跑 `.work/evidence/TESTCASES-086t/run.sh` rc=0（20/20 PASS，含 `audit-HEAD-catches-old` rc=1 与注入 `Expected UNMAPPED` rc=1 两条可达 FAIL 路径）；前后 `ctrl-ret.yaml` md5 一致 `86858af1f9cac4edddff3d2bfb2add95`（= `ctrl-ret.yaml.bak`）。
- **门槛证据核对**（日志）：`.work/log/testcases/TESTCASES-086t-check-inst.log` = `973/978` + 5 deferred（failed=0）；L1 `…-check.log` = `repository checks (L1): PASS`；L2 `…-check-modules.log` = `module checks (L2): PASS`；L3 单成员 = `check-full: PASS (1/1)`。
- **新发现核对**：生成器 `OUT_DIR` 仍为 `tests/vectors/isa`（`generate_ctrl_br.py` 同病）、`helper.c.patch:847` 注释 `7-14` 未改 —— 与本任务「不改 + 登记遗留」一致，处置正确。
- **提交**：本任务分支内单个提交，**未 `push`**；sha 见本分支 `git log -1`。

#### 第 2 轮 engineer 返工（F1，2026-10-31）

**范围**：仅未跟踪证据脚本 `.work/evidence/TESTCASES-086t/run.sh`；`ctrl-ret.yaml`（md5 `86858af1…`）/生成器/ledger **零改动**。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 基线依赖 HEAD/工作树，提交后 rc=1（`audit-HEAD-catches-old`、`ledger-one-line`、`audit-only-one-change`） | ✅已修 | 脚本顶部钉死 `BASE=9d334a1d` + `git cat-file -e` 守卫；`sibling-vectors-identical` 改 `git diff --quiet "$BASE"`；`ledger-one-line` 改 `git diff -U0 "$BASE"`；审计改 `--rev "$BASE"`、check 更名 `audit-baseline-catches-old`、tsv 改 `audit-baseline.tsv`；`audit-only-one-change` 比较基线审计 vs 工作树审计 | 提交态重跑 rc=0 **×2**（`RUN1==RUN2`，20/20 PASS，failures=0） |
| F3 段号重复（文档级） | ✅已修 | 注释重排 1..10，无重复 | `grep '^# [0-9]'` 顺序正确 |
| 残留检查补强 | ✅已修 | `no-temp-residue` 加 `[ ! -e tests/vectors ]` | 重跑 PASS；`ls tests/vectors` 不存在 |

**基线偏离披露**：reviewer 建议 `master` 或 `3f9fc8e3`。`master` 在 `/complete` squash 合并后会前移含修复（同 bug 复发）；`3f9fc8e3` 为分支私有提交，删分支后可能不可达 ⇒ 钉死 `9d334a1d`（现 master tip、永久在 master 历史、修复前树；其 `tests/` 树与 `3f9fc8e3` 相同）。

**可达 FAIL 反证（防「两支同结果」）**：① `audit.py --rev HEAD`（已修复）rc=0 ⇒ 旧 `expect_fail` 必 FAIL；② `git diff -U0 HEAD -- tests/case-ledger.tsv` changed_lines=0 ⇒ 旧 `ledger-one-line` 必 FAIL。旧写法即 F1 原 bug，新写法非恒真。

**提交态/脏态**：提交态 rc=0 ×2；脏态在临时 worktree（`9d334a1d` + 3 文件未提交拷贝 + `.dadao` 软链）跑同一脚本 **rc=0**（`/tmp/opencode/TESTCASES-086t/dirty-run.log`），验后 `git worktree remove`；主工作树 `git status` 仅任务书 + `milestones.md`，无 `tests/vectors`。

**第 2 轮 engineer 自审**：逐行审查 run.sh（BASE 守卫失败即 exit 2、`bash -c` 内 BASE 引号拼接、tsv 路径与 check 名一致、两条可达 FAIL 反证、残留检查含 `tests/vectors`），无未修 finding ⇒ 状态置 `待验收`。


#### 第 2 轮 architect 提交审核（F1 返工，2026-10-31）

- **现场**：分支 `TESTCASES-086t`；审核前 `git status --porcelain -uall` 仅任务书 + `milestones.md`，无未跟踪残留。
- **F1 核验（architect 独立重跑）**：`run.sh` 顶部 `BASE=9d334a1d` + `git cat-file -e` 守卫；审计 `--rev "$BASE"`（check 名 `audit-baseline-catches-old`）；ledger `git diff -U0 "$BASE"`；sibling `git diff --quiet "$BASE"`。提交态重跑 rc=0 **×2**（两份输出逐字节相同，20/20 PASS）；另建临时 worktree（`9d334a1d` + 3 文件未提交拷贝 + `.dadao` 软链）跑同一脚本 **脏态 rc=0**（20/20），验后 `git worktree remove`。`9d334a1d` 在 master 历史（现 master tip），squash 合并后仍可达 ⇒ 基线不随合并前移。
- **功能面零改动**：`ctrl-ret.yaml` md5 `86858af1…`；`tests/`、`tools/testcases/` 对 HEAD `git diff --quiet` rc=0。F3 段号 1..10 无重复。
- **台账同步（architect 代行）**：`milestones.md` 流水行 `待返工` → `待验收`（A1「表行 == 任务书状态」）；`check_milestones_fresh.py` rc=0、`make check` rc=0（L1 PASS），F2 随之消解。
- **档位/提交**：**正常提交**（reviewer 第 1 轮 Needs Revision 的返工已修）；显式 staging **2 文件**（任务书 + `milestones.md`），`git diff --cached --name-only` 与完成区一致；提交 `fix(testcases): TESTCASES-086t 证据基线固定`，sha 见本分支 `git log -1`；**未 push**。

#### 第 2 轮 reviewer 验收（F1 复审，2026-10-31，reviewer 独立重跑，不采信叙述）

**重跑记录（真实输出/退出码）**：① 分支 `TESTCASES-086t`、HEAD=`a538cc91`；`git status --porcelain -uall` 验收前后均空（快照 diff rc=0）；`git diff master...HEAD --stat` = 3 实现文件 + 任务书 + milestones 行，禁改区（components/spec/.tao/adr/contracts/Makefile/tests/unit/tests/arch）命中 0。② `run.sh` 提交态 rc=0 **×2**（20/20 PASS、failures=0）；脏态临时 worktree（`9d334a1d` + 3 文件未提交拷贝 + `.dadao` 软链）同一脚本 **rc=0**（20/20），验后 `git worktree remove`。③ 独立注入（非 engineer 点，ledger 该行 CFXMEM→UNMAPPED，`cp` `/tmp/opencode/TESTCASES-086t-review/` + md5）：`run.sh` **rc=1**（`ledger-gate`/`ledger-one-line` FAIL）⇒ 还原 md5 `915c97cb…==915c97cb…` ⇒ 重跑 **rc=0** 回绿。④ 单例 `--case 9` rc=0（`Expected CFXMEM, got CFXMEM`）；`make check-inst` rc=0（`978 total, 973 passed, 0 failed, 5 deferred, 0 errors`）；L1 `make check` rc=0；L2 `check-modules` rc=0；L3 单成员 rc=0（`check-full: PASS (1/1)`）；`validate_vectors`/`check_case_ledger`/`check_spec_cite_targets` 均 rc=0。

**基线核验**：`BASE=9d334a1d` 在 master 历史（`merge-base --is-ancestor` rc=0，现 master tip）、修复前树（`git show`：ctrl-ret[9]=UNMAPPED；其 `tests/` 树与 `3f9fc8e3` diff rc=0）；HEAD≠BASE，squash 合并后 9d334a1d 仍为 master 祖先 ⇒ 基线不前移、不复发。`audit --rev BASE`/ledger `git diff -U0 BASE`/sibling `git diff BASE` 均为 BASE vs 工作树语义；可达 FAIL 反证实测：`audit.py --rev HEAD` rc=0、`git diff -U0 HEAD -- ledger` changed=0（两种旧写法必 FAIL）⇒ 新检查非恒真。

**功能面**：`ctrl-ret.yaml` md5 `86858af1…` 与返工前一致；对 BASE diff 仅 [9]（fault/notes/spec_cite）+ [2] notes 交叉引用字样；`ctrl-jump`/`ctrl-call` 对 BASE `git diff --quiet` rc=0；ledger 对 BASE 恰 1 增 1 删（仅该身份 fault 列）；生成器 diff 限 D4b 用例/常量改名/注释，OUT_DIR 未动。任务书 `待验收` 与 milestones 流水行一致（`check_milestones_fresh` rc=0）；完成区 16 行、各轮审阅 ≤40 行；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`/`tests/vectors` 残留。

**F1-D（文档级，不阻断）**：完成区「修改文件」第 4 项写 `audit.tsv`/`audit-HEAD.tsv`，第 2 轮更名后实际为 `logs/audit-baseline.tsv`/`logs/audit-worktree.tsv`——由 architect 收尾提交更正。

**判决：Accepted** —— F1 已修且经独立重跑 + 独立注入（注入→FAIL→还原→回绿）核实；验收命令块在 reviewer 自己的重跑下全绿、约束无违反，可进入 `/complete`。

#### 第 2 轮 architect 交叉复核（/complete，2026-10-31，独立重跑，不采信叙述）

**现场/证据脚本**：分支 `TESTCASES-086t`、HEAD=`a538cc91`；复核前 `git status --porcelain -uall` 仅本任务书（reviewer 第 2 轮记录未提交）。`run.sh` 提交态 **rc=0**（20/20 PASS）；脏态另建临时 worktree（`9d334a1d` 检出 + 3 文件未提交拷贝 + `.dadao` 软链）同脚本 **rc=0**（20/20），验后 `git worktree remove` + `prune`。

**独立注入（architect 点位，与 engineer「[9] CFXMEM→UNMAPPED」、reviewer「ledger 该行」均不同）**：`[9] expected_fault: CFXMEM → MALIGN` ⇒ `run.sh` **rc=1**，10 项独立 FAIL（`single-case-9`/`yaml-case9-fields`/`generator-reproducible`/`ledger-gate`/`audit-only-one-change`/`injection-unique-target`/`inject-single-case-9`/`restored-single-case-9` 等）⇒ `cp` 还原、md5 `86858af1…` 一致 ⇒ 重跑 **rc=0** 回绿；`git status` 复原。

**基线稳定性**：`git merge-base --is-ancestor 9d334a1d master` rc=0（现 master tip）、`git diff 9d334a1d master` 空、与 HEAD 不同 ⇒ squash 合并后仍为祖先，基线不前移。

**功能面**：`ctrl-ret.yaml` md5 `86858af1f9cac4edddff3d2bfb2add95`（= `.bak`）；`ctrl-jump`/`ctrl-call` 对 BASE `git diff --quiet` rc=0；ledger 对 BASE 恰 2 行（+`CFXMEM` / −`UNMAPPED`，仅该身份 fault 列）；对 BASE 合计 3 文件 26+/23−；`components spec .tao/adr contracts Makefile tests/unit tests/arch .tao/contracts` 命中 **0**。

**门控（独立重跑）**：单例 `--case 9` rc=0；`make check-inst` rc=0（978 total / 973 passed / 0 failed / 5 deferred / 0 errors）；L1 `make check` rc=0；L2 `make check-modules` rc=0（`module checks (L2): PASS`）；L3 单成员 rc=0（`check-full: PASS (1/1)`）；`validate_vectors`/`check_case_ledger`/`check_spec_cite_targets`/`check_milestones_fresh` 均 rc=0。

**审计独立性**：`audit.py --rev 9d334a1d` rc=1 仅 `ctrl-ret[9] INCONSISTENT`；工作树 rc=0；tsv 分布 32×cfxha0 `CFXMEM` + 1×cfxha46 `CFXMEM` + 11×cfxha62 `UNMAPPED`，与任务书基线一致。抽查 `mem-rd[2]`/`ctrl-br[3]`/`ctrl-call[10]`/`ctrl-jump[5]`/`mem-ra[2]`：notes 与审计取址逐条吻合（`addr=0` 走 fallback 分支）。

**未覆盖面核查（防「过松」）**：全量扫「active 且 fault 非空」的用例，notes 目标落在保留 cfx（6–14/19–61）而 fault≠`CFXMEM` 仅 2 例 —— `ctrl-call[4] RASOF`（ra63=`0xCCCC…`，RACNT==63 压栈失败先于取指）、`ctrl-ret[4] RASUF`（MemRAS count=0 弹栈失败），fault 优先级正确、与 cfxha 无关；`atomics-fence[13–16]` 的 `ILLI` 有 spec 明文（`spec/SimRISC-00:403`、`spec/SimRISC-11:160`「保留 cfx ⇒ ILLI」），不属「普通 ld/st／取指 ⇒ CFXMEM」口径 ⇒ 审计范围（仅 `UNMAPPED`/`CFXMEM`）恰当。

**F1-D 处置（文字级，证据语义不变）**：完成区「修改文件」第 4 项更正为 `logs/audit-baseline.tsv`/`logs/audit-worktree.tsv`；同段「审计：HEAD（修前）」更正为「基线 `9d334a1d`（修前）」（提交后 HEAD 已含修复，原表述失真）。

**判决：无阻断** —— reviewer Accepted 经交叉复核成立；`**状态**` 保持 `待验收`（`已验证` 与 milestones 流水行由主会话 `/complete` 一并更新）。

#### 主会话统一收尾

reviewer 复审与 architect 交叉复核均为 **Accepted**，无分歧；主会话采信并置任务 `已验证`。本任务只修正 `tests/inst` 中 reserved cfx 的旧异常期望，未改 QEMU/spec/ADR。遗留：生成器 `OUT_DIR` 仍指旧 `tests/vectors/isa`、QEMU 注释 `7-14` 与宏 `6–14` 不一致、reserved cfx 普通 `ld/st` 无 active 向量；均另立任务。
