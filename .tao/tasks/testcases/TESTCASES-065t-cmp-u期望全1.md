# TESTCASES-065t: `cmp.{ut,uw,ub}` 向量期望改为 64 位全 1

**模块**：testcases
**项目里程碑**：M10
**依赖**：SPEC-173t、QEMU-074t、ADR-0037
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

### 背景（ADR-0037）
- 向量 `tests/vectors/isa/reg-compare.yaml` 现按**零扩展**写期望（如 `cmp.ut` 的 -1 = `0x00000000FFFFFFFF`）。
- 新语义：`-1 = 0xFFFF_FFFF_FFFF_FFFF`；`0/1` 不变。

### 输出
1. **校验**（QEMU-074t 已同笔更新）：`tests/vectors/isa/reg-compare.yaml` 中 `cmp.ut/uw/ub` 的 −1 期望应为 `0xFFFFFFFFFFFFFFFF`（3 条），0/+1 未动；确认无遗漏。
2. **修生成器**：`tools/testcases/generate_isa_vectors.py::_cmp_result` 现按 `mask` 返回 `.u*` 的 −1（零扩展）⇒ 重跑生成器会把 yaml 改回去。改为 **−1 一律 `0xFFFFFFFFFFFFFFFF`**（signed/unsigned 同值），同步 docstring（`SPEC-069t` → `ADR-0037`）。
3. 若向量格式支持多指令序列，新增一条 `cmp.ut` + `br.n` 的语义用例（判负命中）；不支持则在完成区说明（QEMU 侧已由 `min_rom_probe_074t.py` 覆盖）。
4. 不改 `cmp.st/sw/sb` 及其它指令期望。

### 约束
- 期望值从 ADR-0037 / SPEC-173t 派生，**不从 QEMU 实现反推**；改完须全量重算而非抽样。
- 只改向量与必要说明；不改 `spec/`。

## 验收标准
1. `python3 tools/testcases/validate_elf_vectors.py`（或向量校验入口）rc=0；`make check` rc=0。
2. 全量语义跑：相关 cmp 用例 pass，0 fail / 0 blocked（贴计数）。
3. 反例注入（保留一条零扩展期望）⇒ 该用例红 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：任务书验收 1–5 全过。①`validate_vectors` rc=0（156/156，707 例）；②`make check`(L1) rc=0、`make check-modules`(L2) rc=0（smoke 90/90）；③生成器漂移 rc=0（reg-compare 37 例逐字节）；④反例注入（`_cmp_result` 改回 `mask`）漂移红（4 处期望回退）→ `cp` 还原 md5 一致 → 回绿；⑤QEMU 实跑新用例 rc=0。另顺带 L3 `check-qemu-semantics` rc=0（968/979 passed，11 deferred，0 failed）。
**修改文件**：`tools/testcases/generate_isa_vectors.py`（`_cmp_result` −1 一律 `0xFFFFFFFFFFFFFFFF`、docstring `SPEC-069t`→`ADR-0037`；新增 `gen_cmp_ut_br_n_sequence` 并在 `generate_file` 接线）；`tests/vectors/isa/reg-compare.yaml`（生成器重跑新增 1 条 `cmp.ut→br.n` sequence 用例，+29 行、既有行零改动）；`tests/case-ledger.tsv`（`check-case-ledger --write` 重生成，+1 行）；`.tao/knowledge/milestones.md`（流水行状态 `待开始`→`待验收`，L1 `check-milestones-fresh` 要求表/册一致）；`.work/evidence/TESTCASES-065t/run.sh`（证据脚本，`.work/` 不入库）。
**验收结果**：
- 向量校验：`validate_vectors: 156/156 M1 identities covered OK (inventory sync OK; 16 data files, 707 cases; data coverage gaps: 0)` rc=0。`cmp.ut/uw/ub` 语义 −1 期望均为 `0xFFFFFFFFFFFFFFFF`（QEMU-074t 同笔已改），全部 15 条 cmp 语义期望∈{−1,0,+1} 64 位形态，全库仅 `reg-compare.yaml` 含 `cmp.u*`，无遗漏。
- 漂移（临时树重生成后 diff）：`PASS C2 生成器漂移检查 rc=0 | 重生成 37 例逐字节一致 | sha256 f3dc6329b6646da3 == f3dc6329b6646da3`。
- 注入：`PASS C3a 注入 ⇒ 漂移检查红 drift_rc=1 | 期望行被回退 4/4 处`（3 条 cmp.u* + 新用例 rd1）；`PASS C3b 还原后回绿 drift_rc=0 | diff 行数 0`（md5 `be4f5c45…` 与备份一致）。
- L1：`check-case-ledger: PASS（清单 == 现场派生…）` + `repository checks (L1): PASS`（rc=0）。中途曾因 `check-case-ledger`（未登记新用例）红 → `--write` 后复跑绿；状态置 `待验收` 后再复跑 `check-milestones-fresh` rc=0（14 行状态一致）与 `make check` rc=0（终跑 `TESTCASES-065t-make-check-final.log`）。L2：`QEMU: total=90 passed=90 failed=0 errors=0` + `module checks (L2): PASS`（`MAKE_CHECK_MODULES_EXIT=0`）。
- L3（额外）：`Results: 979 total, 968 passed, 0 failed, 11 deferred, 0 errors` + `check-qemu-semantics: PASS`（rc=0；新用例在册内未被 deferred）。
- sequence 用例（`0x41A81083 / 0x68040002 / 0x4C140BAD`）：`C5b rc=0 Exit code: 0x00`；三分支真值表 `C5c 注入 A⇒PASS(未命中路径可达+标记值 0x0BAD)`、`B⇒FAIL(rd5 哨兵有效)`、`C⇒FAIL(命中路径未执行标记)`。
**新发现/坑**：① 生成器**无** `--check`/drift 模式，只能「临时树重生成 + diff」；`reg-compare` 是唯一与生成器逐字节一致的 M1 册，其余 5 册有既存漂移（`issues.yaml`），不得整册无条件覆盖。② 新增 vector 用例会连带 L1 `check-case-ledger` 红 —— 任务书未列的同步面：须 `python3 tools/infra/check_case_ledger.py --write`（+1 行生成物）。③ schema `sequence` 能承载多指令，但分支目标 = PC + (imm<<2)，**imm=2 才跳过 1 条**（首版写 imm=1 时 QEMU 直接红，已修）。④ `gen_divrem_by_zero` 的无符号除零结果仍零扩展（`div.ut` → `0x00000000FFFFFFFF`），ADR-0037 只裁 `cmp`；若要统一「窄运算结果扩展」口径需另立任务。⑤ 含分支的 `sequence` 用例，`expected_pc` **不可** spec 派生（末 PC 是 harness exit 段地址），故置 `null`（validator 仅对 `br.*` 助记符强制 `expected_pc`）。
**遗留问题**：无。（L3 已顺带全绿；div 除零口径见新发现④，非本任务范围。）

## 审阅记录

#### 第 1 轮 engineer 自审
| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `_cmp_result` 去掉 `mask` 分支后 `signed` 是否成死参 | ❌不修 | `signed` 仍用于**源操作数**符号解释（`_sext`）与合法性，非死参 | 漂移 diff=0（signed 册 `cmp.st/sw/sb/so` 期望未变） |
| F2 新用例 `br.n` 偏移写 `+1` 是否跳过标记 | ✅已修 | `_build_word_riii(br_n,1,2)`（PC+(imm<<2)，imm=2 才跨 1 条） | 首版 QEMU `Exit code 0x01` → 改后 `C5b rc=0 Exit code 0x00` |
| F3 新用例是否有**可达 FAIL** 路径（防恒真） | ✅已修 | 证据脚本补三分支真值表（A PASS / B FAIL / C FAIL，期望值各不相同） | `run.sh` C5c 三条输出（0x00 / 0x01 / 0x01） |
| F4 `sequence` 用例 `expected_pc` 应否给出 | ✅已处置（置 null + 理由落盘） | 用例 notes 与完成区新发现⑤写明「末 PC = harness exit 段地址，不可 spec 派生」 | validator 规则只对 `br.*` 助记符强制 `expected_pc`；`C5a` 断言 `expected_pc=None` 且用例 QEMU 实跑 rc=0 |
| F5 生成器缺 `br.n`/`set.zw` 编码真源时会不会静默降级 | ✅已修 | `BY_KEY` 查不到即 `raise KeyError`（fail-closed，无兼容桩） | 两键均命中时正常生成；`C5a` 断言序列字与 opcodes 派生一致 |
| F6 任务书未列的 `tests/case-ledger.tsv` 同步面 | ✅已修 | `check_case_ledger.py --write` 重生成（+1 行） | L1 `check-case-ledger: PASS` + `make check` rc=0 |
#### 第 1 轮 reviewer 验收
**判决：Accepted**（2026-10-25，HEAD=50745c0b，分支 TESTCASES-065t）
**重跑记录**（reviewer 亲自执行，非采信工程师转述）：
- 漂移：临时树重生成 `reg-compare.yaml` ⇒ `cmp` 逐字节 0 差异，sha256 `f3dc6329b6646da3…` 两处一致，rc=0。
- `validate_vectors.py` rc=0（156/156，16 册 707 例，与完成区数字逐字一致）；`validate_elf_vectors.py` rc=0（42 checks PASS）。
- `make check`(L1) rc=0（`repository checks (L1): PASS`）；`make check-modules`(L2) rc=0（`QEMU: total=90 passed=90 failed=0`，`module checks (L2): PASS`），日志 `.work/log/testcases/TESTCASES-065t-reviewer-make-check*.log`。
- `run.sh` 重跑 ALL PASS rc=0（C1 15 条 cmp 用例 0 违规；C5b `Exit code: 0x00`）；QEMU 实跑序列用例（idx=20）独立复跑 rc=0 / `Exit code: 0x00`；全册 37 例循环实跑 **37 PASS / 0 FAIL / 0 BLOCKED**。
- 独立反例（cp+md5）：`_cmp_result` 改回 `mask` ⇒ 漂移 rc=1、**恰 4 处**期望回退（3 条 cmp.u* + 新用例 rd1）；注入态 `run.sh` rc=1（C2 红，FAIL 路径可达）；`cp` 还原 md5 `be4f5c45…` 一致 ⇒ 漂移回绿 rc=0、`run.sh` ALL PASS。
**独立核对**：
- yaml diff（50745c0b^→HEAD）：**0 删 / 29 增**，仅新增序列用例，既有行零改动；`case-ledger.tsv` 恰 +1 行；`milestones.md` 仅 1 行状态变更；WIP 提交范围 = 完成区「修改文件」5 文件，无越界（未触 `spec/`、未动 `cmp.st/sw/sb`）。
- 编码字派生：独立脚本（不 import 生成器）按 opcodes.yaml `opc/ha` 合成 ⇒ `0x41A81083/0x68040002/0x4C140BAD` MATCH，非手填。
- `_cmp_result`：独立 oracle 穷举 8 位 + 16/32 位采样共 105,540 对×signed/unsigned=211,080 断言全匹配（−1 恒 `0xFFFFFFFFFFFFFFFF`，结果恒∈{全1,0,+1}）；docstring 引 ADR-0037、`SPEC-069t` 已除。
- 快照对账：5 目标文件 md5 预/后快照全一致；唯一工作树增量 `docs/DDLN/README.md`（mtime 19:17:19，写作约定散文，无工具生成，属**共享树外部并发编辑**，非本任务产出，未代还原，提请 architect 知悉）。
**采信未重跑**：完成区 L3 `check-qemu-semantics`（968/979，11 deferred）超出本次必跑清单，未独立复跑。
**脚本质量**：C1/C2/C3/C5a/C5c 均有可达 FAIL 路径（经注入实证）；计数现场统计无写死；C6 在已提交后 SKIP 属已知空转，已由 reviewer 独立 git diff 补足。

