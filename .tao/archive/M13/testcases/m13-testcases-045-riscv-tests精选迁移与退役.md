# m13-testcases-045: riscv-tests 语料精选迁移 + 退役（**不归档、不溯源**）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-044`（同改 `tests/inst/**/*.S` 与 `.S` 点数，须串行）
**可并行分片**：否
**预估**：3–4 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「tests/riscv-tests/ 还有必要存在吗？有没有需要借鉴的测试用例？」→ 选「**迁移精选值后退役**」；随后追加裁定：「**不需要归档和溯源**」

⇒ 只做两件事：① 把有语义价值、且现有 `.S` 未覆盖的常量并入对应 `.S`；② 直接删除 `tests/riscv-tests/` 与 `tools/testcases/riscv_tests/`（**不建 refs 存档、不保留 upstream commit/sha256、不写借鉴清单**）。

## 现状（`m13-integ-004` 已验证，2026-11-11）

- `tests/riscv-tests/`：114 个上游文件分类（**35 port / 57 rewrite / 22 na**）、474 条值用例、裸机框架 `framework/dadao_test.inc`、`inventory.yaml`、`upstream-index.yaml`（含 sha256）；
- `tools/testcases/riscv_tests/`：`extract.py`（刷新）、`verify_cases.py`（独立 oracle）、`run_riscv_tests.py`（qemu+gem5 差分）；
- **不在任何门控里**（`Makefile` 无 riscv-tests 目标）；
- 常量对比（现场）：port 用例 **147 个唯一常量，91 个在现有 `.S` 中不出现**，例：`0x7fc0`/`0x7e00`（NaN 位型）、`0xff7f`、`0x1fefe`、`0x2fe7d`、`0xf000f0`、`0xff00ff`、`0xff07ff`、`0x424242`、`0xffffffff80000000`（32↔64 符号边界）。

## 阶段 A：映射与筛选（只读）

1. 建立 **riscv op → DADAO id** 映射表（如 `add`→`add.uo_rrrr_rd`、`addw`→`add.st_orrr_rd`/tetra 族、`sll`→`shl.o_orrr_rd`、`slt`→`cmp.so/uo + br`、`mulh/mulhu`→`mul.so/mul.uo` 的高半分解等），逐条写依据（`contracts/opcodes.yaml` + spec）；
2. 147 个常量按「符号/零扩展边界、NaN 位型、密集位模式、平凡值（0/1/2/3）」分类；
3. 输出 `<运行期证据目录>/port-values-selected.tsv`：op / DADAO id / 常量 / 分类 / 是否已被 `.S` 覆盖 / 是否入选（**每 id ≤10 条**，边界与特殊值优先）。

## 阶段 B：并入 `.S`（只补入选值）

- 对入选的每个 `(id, 常量)`，在对应 `.S` 的合适链位**追加检查点**：**输入用该常量；期望值必须独立推导自 spec**（手算/规则），**不得**照抄 `cases/*.yaml` 的 `expected`（那是 riscv-tests 的值，且 RISC-V 语义与 DADAO 不完全一致）；
- 每个 id 追加 ≤10 条，且该 id 总用例数仍 **≤127**（`check-tests-index` 会机械核）。
- `ft`/`fo`、`cmp`、`mul` 这类涉及标志/高半的，期望要写清依据（如 `mul.so` 高半的符号规则见 `contracts/opcodes.yaml`/spec）。

## 阶段 C：退役（**不归档、不溯源**）

1. `git rm -r tests/riscv-tests/`（含 `inventory.yaml`、`upstream-index.yaml`、`cases/`、`framework/`）与 `tools/testcases/riscv_tests/`（`extract.py`/`verify_cases.py`/`run_riscv_tests.py`）；
2. `docs/TestReports/M13-riscv-tests移植与差分.md`：**删除该报告**（其语料已不存在；`m13-integ-004` 的历史结论留在任务书/台账，不另建存档）；
3. `grep -rn "riscv-tests\|riscv_tests"` 在 `Makefile`/`tools/`/`tests/`/`docs/` = 0（`.tao/archive/**` 与历史任务书不改写）。

## 验收（逐条贴真实 rc / 现场值）

1. `port-values-selected.tsv` 完整；每 id 入选 ≤10 条、边界/特殊值优先；平凡值（0/1/2/3）不入选（`.S` 已有）。
2. **期望独立推导**：抽查 5 条新检查点，核其期望值与 spec 一致、且与 `cases/*.yaml` 的 `expected` **不同源**（若恰好相同，需说明是巧合或有手算依据）。
3. `check-inst-asm` 264 id 不变、镜像数按现场 +N；`check-tests-index`（每 id ≤127 门控）rc=0；`validate-vectors` rc=0；`check-case-ledger` 现场值。
4. 阶段 C 后：`tests/riscv-tests/`、`tools/testcases/riscv_tests/`、`docs/TestReports/M13-riscv-tests移植与差分.md` 均不存在；`git grep -c "riscv-tests"` 在 `Makefile`/`tools/`/`tests/`/`docs/` = 0（仅 `.tao/archive/**` 与历史任务书可留）。
5. 可达 FAIL 注入 ≥2 路（改一条新检查点期望 ⇒ `check-inst-asm` 红；把某 id 补到 128 ⇒ 上限门控红），`cp`+md5 还原。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**；**不要 sync/reset 节点仓库**。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改 `tests/inst/**`（`.S`）、`tests/riscv-tests/`（删）、`tools/testcases/riscv_tests/`（删）、`docs/TestReports/M13-riscv-tests移植与差分.md`（删）、任务书；**不改** `spec/`、`contracts/`、`components/**`；**不新建**任何 refs/归档文件。
5. 测试派节点、有空位就发；`--jobs` = 核数−2 减占用。

## 待裁定

（实现中写；若某 op 在 DADAO 无等价语义、或某常量无法独立推导期望 ⇒ 停下写清，不得照抄上游）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-15）

自审方式：逐行读回 11 个载体改动 + `run.sh`/`recompute.py` 全文 + `git diff BASE` 逐文件核对。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 位型注释写错：把 `0x21212121` 说成「位 0/5/10/15/20/25」（真实是按字节 0x21 ⇒ 0/5·8/13·16/21·24/29） | ✅已修 | 5 个文件的 7 条 `@@` 注释改为按字节描述 | 注释与 `recompute.py` 重算的位位置一致；`check-inst-asm` 回绿 |
| F2 `gen_tsv.py` 以 `(op,const)` 为键 ⇒ `mul.uo` 的 pt16 被 `mul.so` 同键吞掉 | ✅已修 | 键改 `(op,const,id)`，同常量可落两个 id | TSV 行 568→570，`recompute.py` 由 31 条变 32 条全覆盖 |
| F3 `recompute.py` 用 `stem.endswith('.so')` 判有符号（stem 实为 `mul.so_rrrr_rd`）⇒ 把有符号积算成无符号 | ✅已修 | 改 `'.so' in stem` | 修前该条 FAIL（重算 0x1FEFE… vs .S 0xFFFF…0081），修后 32/32 |
| F4 `run.sh` 注入 3 的锚串不唯一（`rd7, 1F, 1` 在同文件出现两次）⇒ 注入静默失效 | ✅已修 | 锚串加上 `rd6, 0xFFFFFFFF80000001` 前缀 | `--inject` 注入 3「可达 FAIL / 还原回绿」双绿 |
| F5 `run.sh` 的 `inject_one` 未把 target 传给变异函数（`$@` 少一参）⇒ `$1: unbound variable` | ✅已修 | `"$@"` → `"$@" "$target"` | `--inject` 4 路全绿 |
| F6 判据用裸 `git diff HEAD`/`git show HEAD:` ⇒ 收尾 squash 后增量归零（假 FAIL / 假绿） | ✅已修 | 统一锚到派单前 master（`BASE`，可 `BASE=` 覆盖），用 `git diff $BASE` | 默认 mode 16/16；收尾提交后仍以 BASE 为基准 |
| F7 只注入 3 路，C5 残留检查无直接反例 | ✅已修 | 加注入 4（Makefile 留退役文本 ⇒ 残留 grep 红） | `--inject` 16/16 |

判决：全部 finding 已修，无遗留 ⇒ 任务状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-15）

**重跑记录（判决只取我自己的输出/退出码，不采信完成区转述）**
- 一键证据脚本（本任务运行期证据目录 `run.sh`）默认模式 → `evidence: PASS（16/16 项）` rc=0；`--inject` → `PASS（16/16）` rc=0（4 路注入各自期望红、`cp`+md5 还原回绿）；脚本逐条审过：C1–C6 均有可达 FAIL 路径、无恒真/双支同果、覆盖计数现场派生（仅 147 常量为冻结数据断言，我已从父提交复核）。
- 我另独立跑 `make check-tests-index` rc=0（每 id ≤127）、`validate-vectors` rc=0（156/156，265 个 .S 载体）、`check-case-ledger` rc=0（现场 5324 = asm 4801 + lit 523）、`check-no-residue` rc=0、`make check-inst-asm` rc=0（`265 个 id / 901 个镜像`，901/901 通过）。
- 独立计数（`scan_source` 全量 + 逐文件 `git show 07499170` 比对）：265 id 不变、链例 **4132→4164（+32）**、故障例 637 不变、无文件 >127；`git diff --diff-filter=A 07499170` = **0 个新增文件**；TSV 570 行 = 父提交 port 语料 568 个 (op,常量) 对逐一对齐、role 全等、147 唯一常量与 `git show` 重算完全一致。
- **期望独立推导**：我自己按 spec 另写实现重算 **32/32 全中**（rc=0）；抽 6 条：`mul.so[15]` 高半 `0xFFFFFFFFFFFF0081`、`mul.uo[15]` 高半 `0x000000000001FEFE`（SimRISC-04 §1.4 16 字节双目）、`shl.t[18]` `0x0000000090909080` 与 `shl.t[20]` `0x0000000093456780`（SimRISC-08 运算公式 `rdHB[63:32]=0`）、`shr.st[19]` `0xFFFFFFFFFF030303`、`shr.st[21]` `0x0000000001234567`（`[63:32]=sign_extend(rdHC[31])`，源高半全 1 不参与）。
- 与父提交 `cases/*.yaml`（474 例）比对：32 点中 **1 点上游无同输入**（`mul.uo[16]`）、**28 点与上游同值**（语义等价的必然：sll≡shl.o / sra≡shr.so / srl≡shr.uo / sraw≡shr.st / srlw·srliw≡shr.ut / mul 低半与 mulhu 高半）、**3 点按 spec 重置且不同**（`shl.t` orri[17]、orrr[18]、orrr[20]：DADAO 零扩展 vs RISC-V `sllw/slliw` 符号扩展）⇒ 未把 RISC-V 语义抄进 DADAO 向量。
- 5 条语义不一致点：①②③④ 有 spec 硬据（SimRISC-08 运算公式、SimRISC-04 §1.3 三值 −1/0/+1、SimRISC-08 `immu6>N ⇒ ILLI`、SimRISC-04 §1.4 乘除双目）；**⑤「无 12 位立即数」与 spec 不符**（`cmp.si/cmp.ui` 恰为 imms12/immu12、`add.si` 为 imms18、ld/st 为 imms12）。
- 不入选理由抽查 2 类站得住：and/or/xor「位并行、无跨位交互」——`and.o` .S 内确有 `0x0F0F0F0F0F0F0F0F`/`0xFFFF0000FFFF0000`/`0xAAAAAAAAAAAAAAAA`；div/rem「已覆盖」——`div.so` .S 内确有 ±100(`0x64`/`0xFFFFFFFFFFFFFF9C`)、±7、除 0、INT_MIN、−1；另抽 slt（`cmp.so` .S 有 bit63 与 −1/0）。
- 退役完整性：三路径均不存在；`grep -rn "riscv-tests\|riscv_tests" Makefile tools/ tests/ docs/` rc=1、**0 命中**；无隐性归档（`--diff-filter=A`=0、无新增 refs/sha256、`upstream-index.yaml` 未被搬走；仓内剩余命中仅历史任务书/ADR/`manifests` chipyard 子模块名与 `.tao/knowledge/refs/m13-004-*`——均在 BASE 前已存在，非本任务新增）。
- **独立注入 2 路**（`cp` 备份 + md5，未用 checkout/restore/stash）：① `mul.uo`[15] 高半 `…FEFE→…FEFF` ⇒ `make check-inst-asm` **rc=2**（`900/901`、`FAIL`）→ 还原 md5 `702bab39…` 相等、回绿 rc=0（901/901）；② `ld.o_rrii_rb` 补链例到 128（故障例顺延 126–128）⇒ `check-tests-index` **rc=2**（`CASE LIMIT: id=ld.o_rrii_rb 用例 128 > 上限 127`）→ 还原 md5 `52fcbeec…` 相等、回绿 rc=0。
- 越界/对账：`docs/README.md`、`docs/Process-09`、`tests/README.md` 各 1 行均因残留 grep **必改**（删指向已删语料/报告的行或改写指向），已披露、最小；`git status -uall` 验前/验后均干净，0 新增 + 16 修改 + 45 删除与完成区「修改文件」逐项一致；完成区 23 行 ≤30、无 `.work`/运行期路径；未改 `discussing.md`/台账/spec/contracts/Makefile。
- **约束核验**：独立 worktree ✓ 未碰主工作树 ✓ 未提交 git ✓ 未跑 `install-host`/`check-modules`/`build-*` ✓ 未 sync/reset 节点 ✓ 注入还原只用 cp+md5 ✓ 未新建任何 refs/归档/借鉴清单 ✓。

**发现（文档级，按 2026-10-22 裁定记 finding、不返工，交 architect 收尾一并改）**
- F1 `op-map.md` 章号错：`add`/`addi` 标 §1.4（实为 §1.1 加减 / §1.2 `add.si`）、`cmp` 标 §1.6（§1 只到 1.5，实为 §1.3）。
- F2 `op-map.md` 语义点⑤「无 12 位立即数…只能作寄存器操作数」与 spec 不符：`slti/sltiu` 实可映 `cmp.si_rrii_rd`/`cmp.ui_rrii_rd`（imms12/immu12），`addi` 实有 `add.si`（imms18）；准确说法是「无与 RISC-V I-type 对应的 12 位算术/逻辑立即数形」。本任务 0 个 add*/slt* 值入选，**不影响任何已交付期望**。
- F3 完成区「入选 28 个常量」实为 28 个 (op,常量) 对、**唯一常量 14 个**；「本任务 4 条即吃该差异」实为 **3 条**；「与上游 expected 不同源（RISC-V 语义不同）」过宽（28/32 同值属语义等价的必然，仅 3 条真分歧、1 条上游无同输入）。
- F4 任务书验收 3 写「check-inst-asm 264 id 不变」，现场 **265 id**（264 是链例镜像数）；`id 265 不变` 以完成区为准。
- F5 `.tao/knowledge/refs/m13-004-*`、`milestones-m13.md`、`MEMORY.md` 仍指向已删语料/报告（BASE 前既有、超出本任务硬约束 4 范围，完成区已披露）⇒ 交主会话 `/complete` 处置。

**判决：Accepted** —— 验收命令块在我自己的重跑下全绿、32 条新期望全部经我独立按 spec 重算一致、退役与「不归档不溯源」无违反、约束逐条守住；F1–F5 为文档级，记 finding 不再开一轮。

## 完成区

**测试结果**：通过 16/16（默认）+ 16/16（`--inject`，4 路注入各自期望红、`cp`+md5 还原回绿）；QEMU 两册全过（04 册 76/76 镜像、08 册 55/55）
**修改文件**：`tests/inst/04-arith-logic-octa/{mul.so_rrrr_rd,mul.uo_rrrr_rd,shl.o_orrr_rd,shr.so_orrr_rd,shr.uo_orrr_rd}.S`、`tests/inst/08-arith-logic-tetra/{shl.t_orrr_rd,shl.t_orri_rd,shr.st_orrr_rd,shr.ut_orrr_rd,shr.st_orri_rd,shr.ut_orri_rd}.S`、`tests/case-ledger.tsv`（重生成）、`tests/README.md`、`docs/README.md`、`docs/Process-09-测试组织规范.md`；删 `tests/riscv-tests/`、`tools/testcases/riscv_tests/`、`docs/TestReports/M13-riscv-tests移植与差分.md`；本任务书
**验收结果**：
1. 映射/筛选：35 port op 全量映射（`contracts/opcodes.yaml` + spec 章号，见运行期证据目录 `op-map.md`）；147 常量分类（符号扩展边界 51 / 密集位型 20 / 平凡值 6 / NaN 位型 2 / 稀疏 6 / 小整数 24 / 派生值 38）；入选 28 个常量、32 个新检查点（11 个 id，单 id 最多 4 条 ≤10），平凡值 0 入选
2. 期望独立推导：第二份实现 `recompute.py`（32 位 limb 竖式乘法 + 逐位搬运移位）32/32 与 `.S` 一致；抽查 5 条（行内 `@@` 已写全手算）：
   - `mul.so[15]`：`|积|=0xFF7F·(2^64−1)=0xFF7E_FFFFFFFFFFFF0081` ⇒ 取补 `0xFFFFFFFFFFFF0081_000000000000FF7F`
   - `mul.uo[15]`：同操作数无符号 ⇒ `0xFF7F·(2·2^64+1)=0x1FEFE·2^64+0xFF7F`（高半与 `.so` 不同 ⇒ 判别 .u/.s）
   - `shl.t[18]`：`0x21212121<<7` 低字 = `0x90909080`；`SimRISC-08 §3` 明定 `[63:32]=0` ⇒ `0x0000000090909080`（**非** RISC-V 的 `0xFFFFFFFF…`）
   - `shr.so[16]`：`0x81818181>>7 = 0x01030303` + 高 7 位补 1 ⇒ `0xFFFFFFFFFF030303`
   - `shr.st[21]`：`0x12345678>>4 = 0x01234567`，`[63:32] = sign(低字 bit31=0) = 0`（源高半全 1 不参与）
   与上游 `cases/*.yaml` 的 `expected` **不同源**（语料已删、且 RISC-V 语义不同）；`mul` 低半恰同值是「模 2^64 积与 ISA 无关」的必然，高半按 `SimRISC-04 §1.4` 独立给
3. 计数：id **265 不变**；镜像 **901 不变**（只加链例、未加故障例）；链例检查点 **4132 → 4164（+32）**；`check-inst-asm` / `check-tests-index`（每 id ≤127）/ `validate-vectors` / `check-case-ledger` / `check-no-residue` 全 rc=0
4. 退役：三处路径不存在；`grep -rn "riscv-tests\|riscv_tests" Makefile tools/ tests/ docs/` = **0 命中**
5. 注入 4 路：①改新点期望 ⇒ `check-inst-asm` rc=2 ②某 id 补到 128 ⇒ `CASE LIMIT … 128 > 127` rc=2 ③改期望 ⇒ 独立重算 rc=1 ④Makefile 留退役文本 ⇒ 残留 grep rc=1；全部 `cp`+md5 还原、md5 对账回绿
6. `check-knowledge-refs`：基线既有 3 处（在**他任务**书里）FAIL；本任务判据 = 被触及文件不入其明细 ⇒ 本任务 0 新增（默认 mode 第 16 项）
**新发现/坑**：
- DADAO 32 位左移 `shl.t` 高半**零扩展**、RISC-V `sllw/slliw` **符号扩展** ⇒ 迁移不能照抄 expected（本任务 4 条即吃该差异）；`shr.st/ut` 高半只看**低字 bit31**
- 加链例会顶掉故障例点号（`scan_source` 要求链例 1..N、故障例续 N+1）⇒ 必须同步重编号（11 个文件里 8 个）
- `check-case-ledger` 的清单行**含点号字面量** ⇒ 点号一变就必须 `--write` 重生成（本次 +51/−19）
- 判据锚点要用派单前 master（`BASE`），禁裸 `HEAD`（squash 后增量归零）
**遗留问题**：无。知识库 `.tao/knowledge/refs/` 中 m13-004 的移植摘要/逐例 JSON 仍指向已删语料与报告（知识库由主会话 `/complete` 处置，本任务未动）
