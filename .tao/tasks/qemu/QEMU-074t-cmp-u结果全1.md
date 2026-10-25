# QEMU-074t: `cmp.{ut,uw,ub}` 结果去掉零扩展（ADR-0037）

**模块**：qemu
**项目里程碑**：M10
**依赖**：SPEC-173t（语义已定）、ADR-0037
**状态**：已验证

## 执行环境
**执行环境**：本地（需增量重建 qemu）

## 接口规范

### 背景（ADR-0037）
- `trans_cmp_{ut,uw,ub}` 在 `gen_cmp_three_way`（已给 i64 -1/0/1）之后又做 `ext32u/ext16u/ext8u(result)` ⇒ `cmp.ut(-1)` = `0x00000000FFFFFFFF`，`br.n` 判负失效。
- 新语义：`-1 = 0xFFFF_FFFF_FFFF_FFFF`；`0/1` 不变；源操作数仍按 width 截断。

### 输入
- `components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch`
- 现有语义测试/向量（`tests/vectors/isa/reg-compare.yaml` 由 TESTCASES-065t 同步）

### 输出
1. `cmp.ut` / `cmp.uw` / `cmp.ub` 删除结果零扩展（保留源截断与 `gen_cmp_three_way`）；
2. 补/改 QEMU 语义测试：`cmp.ut(0xA,0x14) ⇒ rd = 0xFFFFFFFFFFFFFFFF`，且 `br.n` 命中；
3. **耦合项（避免中间态红，必须同笔）**：同步更新 `tests/vectors/isa/reg-compare.yaml` 中 `cmp.ut/uw/ub` 的 **-1 期望值**为 `0xFFFFFFFFFFFFFFFF`（`TESTCASES-065t` 负责复核与新增 `br.n` 用例）；否则 L2 `check-qemu-smoke` 会因向量仍按零扩展而红；
4. 不改 `cmp.st/sw/sb`、不改 `cmp.uo/so`。

### 约束
- 只改上述补丁 + 测试；不改 spec/（SPEC-173t 负责）。
- 若 qemu 增量重建 >10 分钟，停下报主会话。

## 验收标准
1. 重建后 `cmp.ut/uw/ub` 的 -1 结果 = 全 1（贴运行输出）。
2. `cmp.ut → br.n` 用例：分支命中（贴 guest 退出码）。
3. 反例注入（恢复零扩展）⇒ 上述用例失败 ⇒ `cp` 还原 ⇒ 绿。
4. L1 / L2 绿（含 qemu smoke / semantics 相关集）。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：探针 `min_rom_probe_074t.py` 21/21 PASS（`--selftest` 4/4 断言均可失败）；`make check`(L1) PASS；`make check-modules`(L2) PASS（`CHECK_MODULES_EXIT=0`）；`check-qemu-smoke` 90/90 PASS；`check-qemu-semantics`(L3) 967/978 PASS（11 条既有 deferred，0 failed）；反例注入 16/16（注入后 probe 12/21、L2 `failed=3` ⇒ cp+md5 还原 ⇒ 全绿）。
**修改文件**：
1. `components/qemu/patches/target/dadao/insn_trans/trans_compare.c.inc.patch`（删 `trans_cmp_{ut,uw,ub}` 的 `ext32/16/8u` 共 3 处；源截断 `0xFFFFFFFF/0xFFFF/0xFF` 保留；由 `.work/source/qemu` amend 后 `tools/infra/make_patch.py qemu` 重导出，patch 194→192 行）
2. `tests/vectors/isa/reg-compare.yaml`（`cmp.ut/uw/ub` 语义 −1 期望值 → `0xFFFFFFFFFFFFFFFF`；0/+1 用例未动）
3. `tools/qemu/min_rom_probe_074t.py`（新增：值断言 14 例 + `br.n` 判负 5 例 + 控制 2 例）
4. `tools/qemu/min_rom_probe_005t.py`（**越界披露**：其 V3 断言的是旧零扩展语义，实测 17/18 FAIL；改为 64 位全 1 → 18/18 PASS）
（证据脚本 `.work/evidence/QEMU-074t/{run.sh,inject_zero_ext.py,check_semantics_static.py}`，`.work/**` 不入库）
**验收结果**：
- `probe`: `[PASS] UT-1 cmp.ut(0xA,0x14) -> 0xFFFF_FFFF_FFFF_FFFF  exit=0x00 (expect 0x00) OK`；`[PASS] BR-UT-1 cmp.ut(0xA,0x14) -> br.n TAKEN  exit=0x00 (expect 0x00) OK`；`Main: 21/21 passed, 0 failed`；`rc=0`
- L2: `QEMU: total=90 passed=90 failed=0 deferred=0 errors=0` → `check-qemu-smoke: PASS`
- L1/L2/L3: `repository checks (L1): PASS` / `module checks (L2): PASS` / `check-qemu-semantics: PASS（967/978，载体 20 册）`，均 `rc=0`
- 反例注入：`Main: 12/21 passed, 9 failed`（`[FAIL] UT-1 / BR-UT-1`，`[PASS] UT-3`）＋ L2 `failed=3`（reg-compare[13][19][25]）→ `restore: md5 src=b3d96d3c… backup=b3d96d3c… -> MATCH` → `Main: 21/21 passed`
- 日志：`.work/log/qemu/QEMU-074t-*`；证据脚本：`.work/evidence/QEMU-074t/run.sh`（默认 11/11、`--inject` 16/16）
**新发现/坑**：
- `set.ow rd,wp,imm` = 「该 wyde=imm，其余 48 位全 1」，**不是**符号扩展（`trans_imm.c.inc:31-33`）；拼 `rd16=0x18` 会得到 `0xFFFF_FFFF_FFFF_0018` ⇒ semihosting 报 `Unsupported SemiHosting SWI 0xffff0018`（abort）。小常量用 `set.zw`。
- `-d cpu` 在 `dadao-m1` 上只 dump 一次（复位态），不能用来读指令后的寄存器值 ⇒ 断言改为 guest 内 `xor.o`+`br.z` 比较（退出码承载结论）。
- orrr 基字必须抄 `contracts/opcodes.yaml` 的 `value`：手算 `ha<<18` 易错（`xor.o`=0x40280000，误写 0x400A0000 ⇒ UNDI 0x89）。
- 结果扩展一改即牵连向量与旧探针：`grep 0x00000000FFFFFFFF tests/ tools/` 是本类改动的固定清查动作。
- 证据脚本日志名含括号会触发 L1 `check-run-artifacts` A3 非法命名（9 条红）；`.work/log` 名须 `QEMU-nnn[a-z]-[A-Za-z0-9._-]+.(log|json|txt)`。
**遗留问题**：
- 生成器 `tools/testcases/generate_isa_vectors.py::_cmp_result`（约 263–279 行）仍按零扩展算 `.u*` 的 −1；本任务按任务书只改 yaml，**重跑该生成器会回退期望值** ⇒ 归 `TESTCASES-065t`（模块归属：testcases）。
- `cmp.ut → br.n` 的**向量**用例未新增（任务书把向量侧新增留给 `TESTCASES-065t`）；QEMU 侧已由 `min_rom_probe_074t.py` 覆盖。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 探针初版用 `-d cpu` 读寄存器，实际只 dump 复位态 ⇒ 12 例误报 | ✅已修 | 值断言改为 guest 内 `xor.o`+`br.z`（等/不等分别走 PASS/`0x13` 退出码）；删除 dump 解析 | `Main: 21/21 passed`；`--selftest` 首项 `exit=0x13` 证明值断言可失败 |
| 初版 trampoline 用 `set.ow` 写 SYS_EXIT 号 ⇒ `Unsupported SemiHosting SWI 0xffff0018`（全 21 例 abort） | ✅已修 | 改 `set_zw_rd(16,0x18)`；注释按 `trans_imm.c.inc` 实测语义写 | 同上 21/21；008t/072t 同法 |
| `xor.o` 基字手算成 0x400A0000 ⇒ UNDI 0x89 | ✅已修 | 改 0x40280000（`opcodes.yaml value`） | value 用例由 0x89 变 0x00 |
| 证据脚本日志名带括号 ⇒ L1 `check-run-artifacts` A3 报 9 条非法名 | ✅已修 | `logname()` 白名单化命名；`.EXIT` 标记改名 `*.log` | `check-run-artifacts: PASS`（0 illegal）+ `make check` L1 PASS |
| `min_rom_probe_005t.py` V3 仍断言零扩展（本改动的连带红） | ✅已修 | V3 期望改 64 位全 1，复用 `_exact_cmp(insns,1,6,-1)` | 005t 由 `17/18, 1 failed` → `Main: 18/18 | CTL: OK`，`rc=0` |
| 注释/文档与实现不一致（`cfxld` poison 写成 UNDI；分支覆盖描述过宽）；死代码 `re`/`ILLI_EXIT`/`SEMI_BLOCK`/`set_ow_rd`/`br_n` | ✅已修 | 注释改为 ILLI(0x88)、覆盖范围收紧；删死代码 | `py_compile` OK，21/21 复跑 PASS |
| 证据脚本"注入未生效"无断言 | ✅已修 | 增加 `git diff --name-only` 非空断言（空注入即 FAIL） | `--inject`: `[PASS] injection touched the build input`（16/16） |

**自审判决**：7 条 finding 全部 ✅已修，无未修项 ⇒ 置 `待验收`。
#### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 亲跑，日志 `QEMU-074t-reviewer-*.log`）：
- `make check`(L1) → **rc=2 FAIL**：`check-milestones-fresh` A1 唯一红项 `L49 QEMU-074t: 表=待开始 ≠ 册=待验收`（`.tao/knowledge/milestones.md:49` 未随状态翻转同步；master 上两者同为待开始故不红，红由本分支交付态引入）
- `make check-modules`(L2) → **rc=2 FAIL**：同一根因经 `test-semihost → make check` 级联；其余全绿（`check-qemu-smoke 90/90 PASS` 等）
- `run.sh`（默认）→ rc=0，11/11 PASS；`run.sh --inject` → rc=0，16/16 PASS（注入后 probe `Main: 12/21`，UT-1/BR-UT-1 `exit=0x13` FAIL、UT-3 PASS；L2 `failed=3`；restore md5 `b3d96d3c…=b3d96d3c… MATCH`；还原后 probe 21/21、smoke 绿）
- `min_rom_probe_074t.py` → rc=0 `Main: 21/21`；`--selftest` → rc=0 4/4（各断言均实证可 FAIL：0x13/0x12/0x33/0x88）
- `min_rom_probe_005t.py` → rc=0 `Main: 18/18 | CTL: OK`；`make check-qemu-semantics`(L3) → rc=0 `967/978，11 deferred，0 failed`（与完成区逐字一致）
- **reviewer 独立反例**（cp+md5，非 engineer 脚本）：向量 `reg-compare.yaml:344`（cmp.ut −1）改回 `0x00000000FFFFFFFF` ⇒ 静态检查 rc=1、`check-qemu-smoke` rc=2 `failed=1`（`reg-compare.yaml[13]`）⇒ `cp` 还原 md5 `b70d7f8c…` MATCH ⇒ smoke `90/90 PASS rc=0`

**约束核验**：① 三处 `ext32/16/8u` 已删、`gen_cmp_three_way`+源截断掩码保留（patch diff + 静态检查 + 注入反证三方一致）；② yaml 仅 3 条 −1 期望改全 1，0/+1 用例未动（`git diff master` 逐行核）；③ 005t 改动仅 V3 期望同步（旧断言在新语义下必红：074t selftest(1) 实证同型比较 `exit=0x13`），属连带必要；④ 074t 21 例覆盖 −1/0/+1、源截断（UT-4/UW-2/UB-2）、br.n 五例、控制两例（旧模式不命中/手工 −1 命中）+ st/sw/sb/uo 不变守卫；⑤ 重建耗时约 20s，未超 10 min；⑥ 快照对账：前后 `git status -uall` 干净、7 个目标文件 md5 前后逐一相等，构建树=安装根 qemu `0e4c739b…`；未改 spec/、未越界。

**完成区一致性**：probe/selftest/反例/L3/smoke 数字与真实输出逐条相符；**唯 L1/L2 "PASS" 声明与交付态不符**——其证据跑于 17:48（状态翻转前），翻转后未同步流水表。

**判决：Needs Revision**（阻断项仅 1 条，属「门控/退出码」类）：`.tao/knowledge/milestones.md:49` 状态列 `待开始` → `待验收`（单格修改）后，重跑 `make check`、`make check-modules` 应 rc=0；语义实现（补丁/向量/探针/反例）本身全部达标，无实现层返工项。

#### 第 2 轮 reviewer 验收

**修复项核验**：`git diff -- .tao/knowledge/milestones.md` 仅 1 处单格改动（`待开始` → `待验收`，时间格 `2026-10-25 16:52（登记）` 保持不动）；上一轮阻断项（`check-milestones-fresh` A1 `L49 表≠册`）对应消除。

**第 2 轮重跑**（reviewer 亲跑，非采信主会话日志；日志 `QEMU-074t-reviewer-r2-{l1,l2}.log`）：
- `make check`(L1) → **rc=0**，`repository checks (L1): PASS`；`check-milestones-fresh` A1 核验 14 行、全文 0 VIOLATION
- `make check-modules`(L2) → **rc=0**，`module checks (L2): PASS`；内含 `QEMU: total=90 passed=90 failed=0`，全文 0 VIOLATION

**其余实现证据沿用第 1 轮（校验和背书）**：第 2 轮收尾快照 7 个目标文件 md5 与第 1 轮 reviewer 全部独立重跑后的 AFTER 快照逐一相等（patch `23ecfdb8…`、yaml `b70d7f8c…`、005t `ae21fb24…`、074t `7ed093d0…`、src `b3d96d3c…`、build/install qemu 均 `0e4c739b…`），产物未变 ⇒ 第 1 轮已独立验证的证据（probe 21/21、selftest 4/4、005t 18/18、run.sh 11/11、--inject 16/16、reviewer 独立反例 注入红→还原绿、L3 967/978）继续成立。

**工作区对账**：`git status -uall` 仅 `milestones.md`（修复项）与任务书（审阅记录）两个预期改动，无越界、无临时残留。

**判决：Accepted**——第 1 轮唯一阻断项已修且经 reviewer 亲跑复证（L1/L2 rc=0），实现与约束无违反；主会话可按流程收尾（状态 → `已验证`、提交）。

