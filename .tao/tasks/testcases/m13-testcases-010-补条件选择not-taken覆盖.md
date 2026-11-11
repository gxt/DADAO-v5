# m13-testcases-010: 补条件选择指令的 not-taken 分支覆盖

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m12-chipyard-010`（已合入）、`m12-chipyard-011`（已合入，已顺手修 RTL）
**可并行分片**：否（共享 `tests/inst/`，单写者）
**状态**：已验证

## 背景（`ISS-387`）

`m12-chipyard-011` 发现并修好了一个既有 RTL 缺陷：

```scala
// 原（错）：cs.n/.z/.p 也被做成条件写
csTaken = !d.isCs || csCondTrue
// 新（对）：第一类恒写两源之一，只有 cs.eq/.ne 才是条件写
csTaken = !d.isCs || csCond <= 2 || csCondTrue
```

spec 依据：`SimRISC-02 §2` —— 第一类 `if (cond) rdHB=rdHC; else rdHB=rdHD`（**恒写两源之一**），第二类 `cs.eq/.ne` 才是「条件成立才写」。

**根因不是 oracle 写错，是向量没覆盖**：`tests/inst/base/reg-cond-assign.yaml` 的 5 条语义例**全部落在 taken 支**（`cs.n=−1`、`cs.z=0`、`cs.p=+1`、`cs.eq` 相等、`cs.ne` 不等），**else 支从未被执行**。因此 `m12-chipyard-010` 的 605 例自写 oracle 与该任务 reviewer 都看不见「不写」这个错误行为。

## 目标

1. 在生成器 `tools/testcases/generate_isa_vectors.py` 里，为**每个** `cs.*`（`cs.n`/`cs.z`/`cs.p`/`cs.eq`/`cs.ne`）补 **not-taken** 语义例：
   - 第一类（`cs.n/.z/.p`）not-taken ⇒ 期望 `rdHB = rdHD`（**必须写**，这是回归点）
   - 第二类（`cs.eq/.ne`）not-taken ⇒ 期望 `rdHC` 保持不变
2. `rd` 与 `rf` 两种形式都要覆盖（两者解码路径不同，共用 `csTaken/csCondTrue`）。
3. 重新生成 `tests/inst/base/reg-cond-assign.yaml`；**禁手改 YAML**（该文件由生成器产出）。
4. 同步 `tests/inst/inventory.md` 的覆盖声明（若条目变化）。

## 验收标准

1. `reg-cond-assign.yaml` 中 `cs.n/.z/.p` 的 not-taken 例 **≥3 条**（rd 形式），`cs.eq/.ne` 的 not-taken 例 ≥2 条；`rf` 形式各 ≥1 条
2. **可达 FAIL 反例**：把 RTL 的 `csTaken` 改回旧写法（`!d.isCs || csCondTrue`）⇒ 新向量必须红；还原后回绿
3. 新向量在 QEMU 与 chipyard 上逐例一致（chipyard 侧可与 `016` 合并跑，见「说明」）
4. `make check-inst`（Tiny）与 `make check-tests-index` rc=0；273 例 md5 不变
5. 一键证据脚本；完成区 ≤30 行、无运行期路径；**「修改文件」与 `git status` 对账**（`ISS-377`）

## 说明

- 与 `m12-chipyard-012`–`015` **串行**：它们改 chipyard 组件（单写者），本任务要跑 chipyard 验证，不能并行。
- 若排期上与 `012`–`015` 冲突，可先落「生成器 + YAML + QEMU 验证」，chipyard 侧验证并入 `016`（T0 冒烟）并在完成区注明。
- 本任务是 `ISS-387` 的行动项之一；另一项（`Process-09` 增加「条件语义须有 taken/not-taken 双支」判据）由 architect 另行处理，不在本任务范围。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树（`ISS-368`）；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」须与 `git status` 对账。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
8. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审

**自主逐行审查**（`tools/testcases/generate_isa_vectors.py` 新增/改动段、`tests/inst/fp/cond-assign.yaml` 全部 6 例、`reg-cond-assign.yaml` 新增 5 例、证据脚本）：重点核「not-taken 期望值是否真按 spec 派生」「注入是否可达 FAIL」「是否越界改文件」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `gen_cs_rf_semantic` 的期望值由入参 `taken` 推导，存在「生成器自证」风险 | ✅已修（以独立复算抵消） | 不改生成器；证据脚本 B 段从 `rd1` 符号/零值**独立**判定 taken，并断言 `rd5 ==` 被选中源 | B 段 26 条结构断言全 PASS（含 rf 6 例逐例复算） |
| F2 新例若插在册首会打乱 `semantics_gate.KNOWN_DEFERRED` 的 (册,索引) 钉定 | ✅已修 | 新 rd 例**追加在 deferred 块之后**（生成器注释说明原因） | `check-inst` 中 deferred 仍为 `reg-cond-assign.yaml[15..19]` |
| F3 加例后 `tests/case-ledger.tsv` 必然红（L1 `check-case-ledger`） | ✅已修 | `check_case_ledger.py --write` 重生成（+11 行 = 新增 11 例） | `make check` 中 `check-case-ledger: PASS`（现场 2025 条） |
| F4 新增 fp 册未入 `tests/inst.yaml` 与 inventory 门控覆盖表 ⇒ 索引缺条 + `check_inventory_coverage` 红 | ✅已修（越界披露：任务书只点 inventory） | `tests/inst.yaml` +`inst-fp-003`；inventory 门控覆盖表 +1 行 | `check-tests-index` PASS（244 条）；`check-inst` 报「载体 24 册」 |
| F5 注入首版用 `head` 变量遮蔽文件头，注入后写出坏 YAML（E 段当时 3 项红） | ✅已修 | 改名 `exp_part`；E 段加 `trap` 异常还原 | `ONLY=E` 12/12 PASS；三轮注入均「红(rc=1)→还原→绿」 |
| F6 调试临时件曾落在 worktree 根（`dbg*.yaml`/`sweep/` 等） | ✅已清 | 删除；临时件改落运行期临时目录 | `git status -uall` 仅 7 个交付文件（6 改 + 1 新增） |
| F7 L1 `check-knowledge-refs` 红：`m12-chipyard-012-FP转换.md` 含**具体** `.work/evidence/<该任务>/run.sh` 路径（非占位形） | ❌不修（§2.43 归属判定） | 未改该文件 | 该行来自 commit `c65eed8c`（他任务），本分支 `git diff` 不含该文件 |
| F8 rf 形式不能落 `base/`（validator 规则 7 限 M1 身份集） | ✅已修＋披露 | 单列 `tests/inst/fp/cond-assign.yaml`（`semantics_gate` CARRIER_DIRS 既有口径） | `validate_vectors` PASS；`check-inst` 载体 24 册 |

**判决**：finding 全部处置完毕（F7 为他任务归属、已登记遗留），状态置 `待验收`。

### 第 1 轮 reviewer 验收

**审阅对象**：任务书、`tools/testcases/generate_isa_vectors.py`（`gen_cs_not_taken`/`gen_cs_rf_semantic`/`_render_targets`）、`tests/inst/base/reg-cond-assign.yaml`、`tests/inst/fp/cond-assign.yaml`、`tests/inst.yaml`、`tests/inst/inventory.md`、`tests/case-ledger.tsv`、证据脚本 `<任务ID>/run.sh`（逐条审 FAIL 可达性）；对照 `spec/SimRISC-02 §2/§3`、`contracts/opcodes.yaml`、`tools/qemu/semantics_gate.py`、`tools/testcases/validate_vectors.py`、`tools/chipyard/inst_sweep.py`、`tools/chipyard/bit_sweep.py`、`tools/testcases/lib/build_test_binary.py`。

**重跑（全部本人执行，workdir=仓库根，输出落运行期证据日志目录 `<任务ID>-reviewer-*.log`）**：
- `make check-inst` → **rc=0**：vast `996 total, 991 passed, 0 failed, 5 deferred`，`deferred: reg-cond-assign.yaml[15..19]`，`载体 24 册`；tiny `44 total, 44 passed`。
- `make check-tests-index` → **rc=0**（`PASS（244 条）`）；`python3 tools/testcases/validate_vectors.py` → **rc=0**（`16 data files, 723 cases`，base 册合计我方现场数 723）；`make check-generator-sync` → **rc=0**（`generate_isa_vectors --check: PASS（7 册 byte-identical）`）；`make check-inst-smoke` → **rc=0**（`total=90 passed=90`）；`make check-case-ledger` → **rc=0**（`现场身份 2025 条`）。
- `python3 tools/chipyard/inst_sweep.py list|emit` → `covered=273`、`sweep_expect.bin` **md5=`2d4d94651346ef673c5a855e024c1489`（与基线一致）**；`bit_sweep list` → `intfill covered=207`、`total=969`，新例 `reg-cond-assign.yaml:20..24` 已入组、15–19 仍按 deferred 跳过。
- `bash <任务ID>/run.sh`（证据脚本）→ **rc=0，`summary: PASS=28 FAIL=0`**（含 3 轮注入「红 rc=1 → cp+md5 还原 → 绿 rc=0」）。
- **本人独立注入**：`cp`+md5 备份后把 `reg-cond-assign.yaml[22]`（cs.p not-taken）期望 `rd2` 由 `0x000000000000BBBB` 改 `0x000000000000AAAA` → `python3 tools/testcases/lib/run_qemu_test.py … --case 22` **rc=1 / `Status: FAIL`**；`cp` 还原后 md5=`16d0bd2a…` 与注入前一致 → 同例 **rc=0**；`git status --porcelain -uall` **0 行**。
- `make -k check` → **rc=2，红 4 项**（均非本任务所致）：`check-patch-tree`（组件源检出树里 4 个生成器文件带 011 的未提交 RTL 修复）、`check-knowledge-refs`（`m12-chipyard-012` 任务书 104 行）、`check-run-artifacts`（`night-*.md` + `gem5/m13-gem5-004-*`）、`check-temp-dirs`（5 个他任务陈旧目录）；我方新增日志命名合规（`check-run-artifacts` 仍仅上述 3 条非法名）。

**约束核验**：① 改动恰 7 文件，与 WIP `d3df8be1` 的 `git show --stat` 逐一对账一致，工作树干净；② YAML 纯生成器产出（`--check` 7 册 byte-identical），无手改；③ 新 rd 例**纯追加**（`+121/-0`，前 20 例与 `b08e1f32` 逐条相等），deferred 仍 15–19、`KNOWN_DEFERRED` 未被改；④ 期望值按 spec 派生（第一类 else→rdHD、第二类不写、rf else→rfHD），非照抄 RTL；⑤ 完成区 13 行、无运行期路径（仅 `<任务ID>`/`<该任务>` 占位形）；⑥ 覆盖计数现场派生（B 段 26 断言、C 段 20/6、D 段 244/723/996/90/273 均现场打印）；⑦ 未 commit、未 push、未动台账。

**三问**：① **能真正抓住旧行为**：旧码 `csTaken=!d.isCs||csCondTrue` ⇒ 条件假 ⇒ 不写 ⇒ `rd2` 保持 preset `0x1111222233334444`，而期望 `0x…BBBB`；两侧 harness 都先按 `input_state` 预置 `rd2`（QEMU `build_test_binary` loader / chipyard `bit_sweep.load_inputs`）再按 `expected_state` 逐字节比 ⇒ 必红；实证 = 期望改成 preset 的那轮注入（等价于旧实现输出）rc=1。**证据缺口**：对**真 RTL** 改回旧写法的重建注入未做（chipyard 单写者被 013 占用），完成区已登记交 `016`——本任务层面「旧实现会红」已由推演+等价输出注入证实，实际 RTL 红灯仍待 `016` 关闭。② **rf 通道可信**：`ld.o rf3/rf4`（0xAAAA/0xBBBB）→ 被测 → `rf2rd rd5←rf2`，taken/not-taken 各一条且期望相反、6 例全绿 ⇒ 载入互异且选择正确（读错寄存器或两源互换必有一支红）；**无写掩盖**：我用「删掉被测指令」的探针实测 `rf2` 初值=`0`（期望 `0x…0` PASS、期望 `0x…BBBB` FAIL）⇒ 旧「条件写」不写时读回 `0 ≠ 0x…BBBB` ⇒ 必红；残余：该初值是 QEMU harness 结论，chipyard 侧 rf 载体尚未接入本册，rf 硬件红灯仍归 `016`。③ **deferred 未扰动**：新例在 20–24，前 20 例与基线逐条相等，`KNOWN_DEFERRED` 仍 `(reg-cond-assign.yaml,15..19)`，`check-inst` 现场打印同一批 5 条。

**越界判定**：`tests/case-ledger.tsv` 机械必需（L1 `check-case-ledger` 现场重派生逐字节比对，不重生成必红，已 rc=0 验证）；`tests/inst.yaml` 条目**非门控必需**（`check-tests-index` 只校验已登记条目），但属 `Process-09 §5` 根级 case 清单登记、与 `TESTCASES-090t` 新增载体册先例一致且已披露 ⇒ 认可，不算违规。

**findings（文档级，不阻断）**：F-a 完成区写「L1 红 3 项」，本人实跑为 **4 项**（漏记 `check-patch-tree`，根因是组件源检出树里 011 的未提交 RTL 修复）；F-b 证据脚本 `inst_sweep covered` 期望写死 `273`（回归钉、实际值现场取）而标签写「现场派生」，措辞出入。请 architect 收尾时改。

**判决：Accepted**（附条件：上文两处证据缺口——真 RTL 重建注入、chipyard 侧 rf 载体——按完成区遗留登记由 `016` 关闭）。

## 完成区

**测试结果**：一键证据脚本 `PASS=28 FAIL=0`（rc=0）。关键项：`make check-inst` rc=0（vast `991/996` + tiny `44/44`，载体 24 册，deferred 仍 5 条）、`make check-tests-index` rc=0（244 条）、`validate_vectors` rc=0（16 册 723 例）、`check-generator-sync` rc=0（7 册 byte-identical）、`check-inst-smoke` rc=0（90/90）、273 例 md5 `2d4d9465…` 不变、QEMU `dadao-tiny` 逐例 base 20/20 + fp 6/6 全绿。
**修改文件**：`tools/testcases/generate_isa_vectors.py`、`tests/inst/base/reg-cond-assign.yaml`、`tests/inst/fp/cond-assign.yaml`（新）、`tests/inst/inventory.md`、`tests/inst.yaml`、`tests/case-ledger.tsv`、本任务书；`git status -uall` 对账一致（无其它改动/无残留）。
**验收结果**：
- 生成器改动 3 处：① `gen_cs_not_taken()`（rd 形式 else 支，追加在 deferred 块后）；② `gen_cs_rf_semantic()` + `generate_fp_cond_assign()`（rf 形式，`ld.o rf`×2 + 被测 + `rf2rd` 读回）；③ 渲染/写盘/`--check` 支持第二册（`FP_OUT`/`_render_targets`）。
- 新增例数：**rd 5 条**（`reg-cond-assign.yaml`：cs.n/cs.z/cs.p 各 1 条 not-taken=3、cs.eq/cs.ne 各 1 条 not-taken=2）；**rf 6 条**（`fp/cond-assign.yaml`：cs.n/cs.z/cs.p 各 taken+not-taken，其中 not-taken 3 条）。第一类 not-taken 期望 `rdHB=rdHD`（`0x…BBBB`，preset `0x1111…` 保证「不写」可检出）；第二类 not-taken 期望 `rdHC` 保持 preset。
- 可达 FAIL：3 轮**单注入**（cs.n rd 期望改回 preset / cs.eq rd3 改成 rd4 值 / cs.n-rf 期望改成 rfHC 值）⇒ 均 rc=1 且 `Status: FAIL`；`cp`+md5 还原（`16d0bd2a…` / `aac82a7e…`）后同例回绿。
- **自决**：rf 不能进 `base/`（validator 规则 7：base 册 id 须 ∈ M1 身份集，deferred 亦不豁免）⇒ 按 `semantics_gate` CARRIER_DIRS 既有口径单列 `tests/inst/fp/cond-assign.yaml`；rf 同时补 taken 支（否则「恒写 rdHD」的错实现仍会绿）；新例一律追加在 deferred 之后（保 gate 索引 15–19）。
- L1 `make -k check` rc=2：红 3 项均为**他任务既有**——`check-knowledge-refs`（`m12-chipyard-012` 任务书第 104 行，commit `c65eed8c`）、`check-run-artifacts`（`night-2026-11-1*.md` + `gem5/m13-gem5-004-*`）、`check-temp-dirs`（5 个他任务陈旧临时目录）；本任务涉及的门控（`check-case-ledger`/`check-dirs`/`check-no-residue`/`check-scope`/`check-rule-refs`/`check-spec-cite-targets`/`validate-vectors`/`check-tests-index`）全绿。
**新发现/坑**：① `semantics_gate.KNOWN_DEFERRED` 用 (册, 索引) 钉死 ⇒ 册内插例即静默错位，新例只能追加在 deferred 之后（建议后续改为按 id 登记）；② 增删向量必须重跑 `check_case_ledger.py --write`，否则 L1 `check-case-ledger` 红（生成物，禁手改）；③ 非 M1 身份（scope fp）不能进 `base/`，只能单列载体目录；④ `check-inst-smoke` 的代表集按 (class, mnemonic) 取**第一条** ⇒ not-taken 支只在 L3 `check-inst` 被执行（本任务新例故追加在后，不改变 L2 代表集）；⑤ `tools/qemu/check_005t_coverage.py` 仍把 `cs.*_rrrr_rf` 列为「应保持 ILLI」，与 `trans_fp.c.inc` 的 movcond 实现不符（该脚本不在门控路径、只扫 `base/`，本任务不触发）。
**遗留问题**：① RTL 注入反例（`csTaken` 改回 `!d.isCs || csCondTrue` ⇒ 新向量必须红）按派单交 `m12-chipyard-016`（T0 冒烟）执行；本任务按要求以「改期望值 ⇒ 必红」证明断言可达。② chipyard `tools/chipyard/bit_sweep.py` 的 intfill 组按 id 自动纳入新增 5 例（现场 207，整册 969），其基线须在后续 chipyard 任务重取并在该侧跑通 not-taken。③ 建议（非本任务）：`semantics_gate` deferred 键改 id、`check_005t_coverage.py` 的 ILLI 清单与 QEMU 实现对齐。

#### 收尾（architect，2026-11-11 21:12）

- reviewer **Accepted**：`check-inst` rc=0（vast 996=991+5 deferred、tiny 44/44、载体 24 册）、`check-tests-index` 244 条、`validate_vectors` 16 册 723 例、`check-generator-sync` 7 册 byte-identical、`check-inst-smoke` 90/90、`check-case-ledger` 2025 条全绿；273 例 md5 不变。
- **能抓住旧行为（推演 + 等价注入）**：旧码条件假 ⇒ 不写 ⇒ `rd2` 保持 preset，而期望是 `0x…BBBB`；两侧 harness 都先按 `input_state` 预置再逐字节比 ⇒ 必红。实证 = 把期望改成 preset（等价于旧实现输出）rc=1。
- **rf 通道可信**：`ld.o rf3/rf4` 载入互异值 → 被测 → `rf2rd` 读回；「删掉被测指令」探针实测 `rf2` 初值 = 0 ⇒ 旧「条件写」读回 0 ≠ 期望 ⇒ 必红。
- **deferred 未扰动**：新例纯追加（+121/−0），前 20 例与派单前逐条相等，`K2026-11-11 21:12N_DEFERRED` 未改，`check-inst` 仍打印同一批 5 条。
- **证据缺口（已登记，转 `016`）**：对真 RTL 的重建注入（`csTaken` 改回旧写法）因 chipyard 单写者被 `013` 占用未做；chipyard 侧 rf 载体（`fp_sweep` 仅 4 例 `cs.*` rf）也待接入。
- 文档级（转 `ISS-392`）：F-a 完成区写「L1 红 3 项」实为 4 项（漏 `check-patch-tree`）；F-b 证据脚本 `inst_sweep covered` 期望写死 273 而标签写「现场派生」。
