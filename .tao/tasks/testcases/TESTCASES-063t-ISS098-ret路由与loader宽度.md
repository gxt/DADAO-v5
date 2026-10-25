# TESTCASES-063t: harness ret 路由与 loader 宽度推导修复（ISS-098）

**模块**：testcases
**项目里程碑**：M10
**依赖**：无
**状态**：已验证

## 执行环境
**执行环境**：本地（无 LLVM 重建；必要时重跑向量）

## 接口规范

### 背景（ISS-098，architect 复核）
- `tests/scripts/build_test_binary.py` 把 `ret` 语义用例路由到 `build_call_ret_binary`：该构造**合成** `call→ret→landing`（`call` 压 `ra63`，`ret` 从 `ra63` 弹出）并明确 `loader_words=0 for expected_state.ra`；这会**覆盖**向量自身的 RA 输入，导致 `ctrl-ret[0..3]`（0x01）无法按向量语义判定。
- loader 对 `call` 的宽度推导抛 `ValueError`（`ctrl-call[5]`）。
- 与 `ret rd0` 语义无关，属构建/装载侧缺陷。

### 输入
- `tests/scripts/build_test_binary.py`（`build_call_ret_binary` 与 `derive_width_from_mnemonic` 等）
- `tests/vectors/**` 中 `ctrl-ret*` / `ctrl-call*` 用例及其 YAML

### 输出
- `ret` 用例按**向量语义**构造（不覆盖 `expected_state.ra`；若必须合成调用，需让 RA 由向量决定并写明理由）。
- loader 对 `call`/`ret` 的宽度推导不再 `ValueError`（未知 mnemonic ⇒ 明确报错并指出用例，而非崩栈）。
- 不放松既有断言；不放宽向量期望值。

### 约束
- 只改 harness/loader；不改 `spec/`、不改 ISA 语义。
- 每个修复有可达 FAIL 的反例（改回旧路由/旧推导 ⇒ 复现失败）。

## 验收标准
1. `ctrl-ret[0..3]`、`ctrl-call[5]` 按向量语义**真实通过**（贴命令、输出、退出码）。
2. 相关套件 0 fail / 0 blocked（除已登记项）。
3. 反例注入（还原旧路由/旧推导）⇒ 复现失败 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿。
5. 完成区贴真实输出。

## 完成区
**测试结果**：**通过 20/20**（`.work/evidence/TESTCASES-063t/run.sh` rc=0；该计数 = 正常路径 `check` 调用数，**不含** D/E 段「注入落到源码」守卫——注入时按 md5 变化跳过）：`ctrl-ret[0..3]`、`ctrl-ret[8]`、`ctrl-call[5]` 逐例 PASS；ret+call 两册批量 **21/21（0 fail / 0 deferred）**；L3 `make check-qemu-semantics` = **980 total / 975 passed / 0 failed / 5 deferred**（仅既有 C-27；ISS-098 6 条已消失）rc=0；L1 `make check` rc=0；L2 `make check-modules` rc=0。
**修改文件**：`tests/scripts/build_test_binary.py`（删 `build_call_ret_binary`；新增 `build_ret_binary`、`derive_memory_width`、`known_mnemonics`、`_relocate_code_addr`、`IMAGE_WINDOW`）；`tools/testcases/generate_ctrl_jump_call_ret.py`（6 条恢复 active、D4b 两条返回目标改 canonical、新增 1 条 legality UNMAPPED）；`tests/vectors/isa/{ctrl-ret,ctrl-call}.yaml`（重生成）；`tools/qemu/semantics_gate.py`（KNOWN_DEFERRED 删 6 条 ISS-098）；`tests/vectors/inventory.md`；`tests/case-ledger.tsv`（`--write` 重生成）；`tests/scripts/README.md`（PC-affecting 布局说明）；`.tao/knowledge/milestones.md`（本册流水状态 `待开始`→`待验收`，`check-milestones-fresh` A1 要求；非决策改动）。**未改** `spec/`、`contracts/`、ISA 语义；未提交 git。
**验收结果**：
1) `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-ret.yaml --case 0..3,8` / `ctrl-call.yaml --case 5` ⇒ 每例 `Result: PASS`，`rc=0`（日志 `.work/log/testcases/TESTCASES-063t-case-*.log`）。
2) 两册批量：`Results: 21 total, 21 passed, 0 failed, 0 deferred, 0 errors`（rc=0；`.work/log/testcases/TESTCASES-063t-batch-retcall.log`）。
3) `make check-qemu-semantics` ⇒ `Results: 980 total, 975 passed, 0 failed, 5 deferred, 0 errors`；`deferred 登记: 5/5 条（既有 C-27 5；一致）`；`check-qemu-semantics: PASS`。
4) 反例注入（证据脚本 D/E/F 段，`cp` + md5 对账，未用 git 还原）：① 恢复旧路由 ⇒ `ctrl-ret[0] rc=1`；② 恢复旧宽度推导 ⇒ `ctrl-ret[2] rc=1` **且** `ctrl-call[5] rc=1`；③ 临时树把 ret[0] 期望 `ra63` count 2→3 ⇒ `rc=1`；三者还原后均回绿（md5 前后一致 `a90ba4d1…`）。
5) L1 `make check` rc=0（`.work/log/testcases/TESTCASES-063t-make-check.log`）；L2 `make check-modules` rc=0（`…-make-check-modules-2.log`，`module checks (L2): PASS`）；`validate_vectors` 156/156、708 cases、gaps 0；`check-case-ledger` PASS。
**新发现/坑**：① 合成 `call` 无法替代：call 必须位于 `BINARY_BASE` 才能压出向量写的 `PC+4`，而 loader 又必须先执行 ⇒ 只能「用向量自身 RA + 在 `expected_pc` 处放 landing pad」。② 旧宽度推导还有**静默错值**：`derive_width_from_mnemonic('ret')` 末字符 `t` ⇒ 按 4B 存 8B MemRAS 条目（不是崩栈），deferred 期间无人发现。③ call 的 RA 重定位原为「整体 +loader_bytes」，会连 MRPTR/spill 值一起搬 ⇒ `expected_state.memory`（MRPTR-8）对不上，C3b 即使不崩也不会绿；现只搬 `IMAGE_WINDOW` 内的代码地址。④ 原 D4b 两条 semantic 的返回目标 `0xBBBB…`/`0xCCCC…` 不在 RAM（cfxha 46）⇒ `ret` 取指即 UNMAPPED，状态比对永远跑不到（现场实测 `rc=135`）；故改用 canonical `0xFC0000000004`，原形态保留为 1 条 legality `UNMAPPED` 用例（断言数未减）。⑤ `.work/log/` 下完成标记不可用 `*.EXIT` 后缀（`check-run-artifacts` A3 判非法 ⇒ L1 红），标记应落 `/tmp/opencode/<task>/`。
**遗留问题**：① 无功能遗留。② L2 日志产生于最终两条 fail-closed 守卫（`expected_pc is None` / `sequence` 不支持 ⇒ 显式 ValueError）加入前；该两守卫只在非法输入上抛错（现场核：无 ret 用例含 `sequence`、无 active ret 缺 `expected_pc`），其后已复跑 L1+L3 全绿（证据脚本 H 段）。③ 请 architect/reviewer 确认 ④ 的向量输入改动（替代方案 = 保留 2 条 deferred + 另建 QMP/gdbstub 通道读状态，成本高）。④ 建议主会话：`ISS-098` 置 `closed`（`resolved_by: TESTCASES-063t`）、同步 `milestones.md`。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查范围**：`git diff` 全量（`build_test_binary.py` 逐行：layout 序号/跳转立即数/重定位/宽度/错误路径；生成器；门控；inventory/ledger/README）。**判决**：可交验收（证据 20/20，L1/L3 绿）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 新增 legality 用例插在中部 ⇒ 既有用例序号后移（`ctrl-ret[8]` 变成 ILLI 例，证据 C 段先红） | ✅已修 | 新用例移到册尾（index 9），既有 0–8 序号不变 | 逐例打印 0–9 + 证据 C 段 6/6 PASS |
| F2 call 的 RA 重定位「整体挪」会搬 MRPTR/spill 值，`expected_state.memory` 地址对不上 | ✅已修 | `_relocate_code_addr` 只搬 `IMAGE_WINDOW` 内的代码地址（输入/期望同规则） | `ctrl-call[5]`（含 memory 断言）PASS；注入②后 FAIL |
| F3 非宽度族助记符若不校验真源，拼错的 mnemonic 会被静默当 octa | ✅已修 | `known_mnemonics()` 读 `contracts/opcodes.yaml`；未知 ⇒ ValueError 带用例名 | 代码复核 + 未知名路径 ValueError |
| F4 `build_ret_binary` 对 `expected_pc=None` / `sequence` 无守卫（直接调用会 TypeError 或静默） | ✅已修 | 两条显式 ValueError（fail-closed） | 现场两例 ValueError 输出（含用例名） |
| F5 证据脚本首版 C 段写死序号 8 ⇒ 序号漂移即误红（恒真/恒假风险） | ✅已修 | 序号现场取自用例集（0,1,2,3,8）+ 断言 active/期望值齐全 | 重跑 C 段 6/6 PASS |
| F6 完成标记 `*.EXIT` 落 `.work/log/` ⇒ L1 `check-run-artifacts` A3 红（rc=2） | ✅已修 | 删除该文件；标记改放 `/tmp/opencode/<task>/` | 证据 H 段 L1 rc=0 |
| F7 把「ret 目标不在 RAM」从 semantic 改成 legality 是否丢覆盖 | ✅已修（补证） | 新增 legality `UNMAPPED` 用例承接该形态（原 0xBBBB 地址） | 该例 PASS（Expect UNMAPPED 0x87）；批量 21/21 |
| F8 `HEX48_FMT` 在改后成为孤儿常量 | ✅已修 | 删除 | `grep HEX48_FMT` 零命中 |

**逐行复核要点**：landing pad 立即数 `exit_index - pad_pos`（jump-iiii 以自身 PC 为基）与入口 `landing+1` 均按词序推算，与 `pad_pos == landing` 一致；`ret` 后 poison 只在「ret 未跳转」时可达；`loader_words=0` 显式传入且 `relocate_ra=False` ⇒ 期望值按向量原样比对；宽度选择仅命中 `_WIDTH_BEARING_FAMILIES` 时按后缀，其余按 octa。

#### 第 1 轮 reviewer 验收

**判决：Accepted**（2026-10-26；全部命令由 reviewer 在 workdir 独立重跑，未采信工程师转述）

**重跑记录（命令 / 真实输出 / 退出码）**
1. 逐例 `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/ctrl-ret.yaml --case {0,1,2,3,8}` 与 `ctrl-call.yaml --case 5` ⇒ 6 例均 `Exit code: 0x00 / Result: PASS`，`rc=0`（日志 `.work/log/testcases/TESTCASES-063t-reviewer-case-*.log`）。新增 legality 例 `[9]` 单跑 ⇒ `Exit code: 0x87 / Expected UNMAPPED, got UNMAPPED`，`rc=0`。
2. 两册批量（symlink 到 `/tmp/opencode/TESTCASES-063t-review/batch`，`--batch --jobs 8`）⇒ `Results: 21 total, 21 passed, 0 failed, 0 deferred, 0 errors`，`rc=0`；现场派生用例数 `live total = 21`（一致）。
3. `bash .work/evidence/TESTCASES-063t/run.sh` ⇒ `PASS=20 FAIL=0 / RESULT: GREEN / EVIDENCE_EXIT=0`（A–H 全段贴 `.work/log/testcases/TESTCASES-063t-reviewer-evidence.log`）。
4. L1 `make check` ⇒ `repository checks (L1): PASS`，`rc=0`；`validate_vectors: 156/156 … 708 cases; gaps: 0`、`check-case-ledger: PASS`。
5. L2 `make check-modules` ⇒ `module checks (L2): PASS`，`rc=0`（**在最终两条 fail-closed 守卫已入库的现树上重跑**，消解完成区遗留②）。
6. L3（run.sh H 段）`make check-qemu-semantics` ⇒ `980 total, 975 passed, 0 failed, 5 deferred`（仅既有 C-27），`rc=0`。

**独立反例注入（reviewer 自做，`cp`+md5，未用 git checkout/restore/stash）**
- ①整份旧 harness（`git show a2702368:tests/scripts/build_test_binary.py` 即 ISS-098 现场）注入 ⇒ `ctrl-ret[0] rc=1`（`Exit code: 0x01 FAIL`）；`cp` 还原 md5 `a90ba4d1…` 对账一致 ⇒ `rc=0 PASS`。
- ②旧宽度推导（把 `derive_memory_width` 的宽度族判断改为全命中，末字符 b/w/t/o）⇒ `ctrl-ret[2] rc=1`（`Unexpected fault: RASUF 0x8B`，即 8B MemRAS 条目被 4B 写入的静默错值）**且** `ctrl-call[5] rc=1`（`Unknown mnemonic suffix … call`）；还原 md5 一致 ⇒ 两例均回 `rc=0`。
- 快照对账：审前后 `git status --porcelain -uall` 均为空；9 个声明改动文件 `md5sum -c` 全 `OK`、`git diff HEAD` 为空。

**约束核验**：① `build_test_binary.py` 已无 `build_call_ret_binary`（`grep` 零命中），blob 内无 `0x74*` 合成 call，loader 原样装载向量 RA、`loader_words=0` 不重定位；landing pad 由 `expected_pc` 推导（`words[0]=jump imm=landing+1`、`pad_pos==landing`、pad 跳 exit，现场解 blob 核过）；`expected_pc=None`/`sequence`/越窗/非 4B 对齐 ⇒ 四条均显式 `ValueError` 且报文含用例名（独立探针逐条实测）。② 宽度：`call`/`ret` 均 octa（8）、`ld/st/ldm/stm` 各后缀 1/2/4/8、`lr.o.nn`=8、`sc.t.ar`=4、未知助记符/未知后缀 ⇒ `ValueError` 带用例名（19 项探针全 PASS）。③ 断言总数**增不减**：ctrl-ret 4→19、ctrl-call 20→24；逐条比对确认**既有 active 用例 expected_state 无一被改**，D4b 仅按用户裁定改 canonical 并保留原 `0xBBBB` 形态为 legality UNMAPPED；`KNOWN_DEFERRED` 删 6 条与向量转 active 严格对齐（gate 因此更严）。④ 改动范围 = 完成区声明的 9 文件 + 任务书本身，`spec/`、`contracts/`、`run_qemu_test.py` 未动；证据脚本 8 段断言均有可达 FAIL 路径（D/E/F 段注入→红→还原→回绿在我方重跑中真实复现），无恒真。

**非阻塞 finding（留 architect 收尾改）**：完成区「通过 20/20」与 run.sh `check` 调用数（正常路径 20 次）一致，但完成区未注明该计数不含 D/E 段的「注入落到源码」守卫（md5 变化时跳过）——措辞级，不影响判决。
