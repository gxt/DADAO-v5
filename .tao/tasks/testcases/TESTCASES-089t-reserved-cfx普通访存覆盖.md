# TESTCASES-089t: reserved cfx 普通 ld/st 覆盖（CFXMEM）

**模块**：testcases
**项目里程碑**：M10
**依赖**：`TESTCASES-086t`（已验证；审计确认「reserved cfx 的普通 ld/st 无 active 向量」为覆盖缺口，登记遗留）、`INTEG-038t`（已验证；`addr[47:42]` 选 cfxha，reserved cfx 普通 `ld/st` ⇒ `CFXMEM`）
**状态**：已验证

## 执行环境
**执行环境**：本地（仓库 `/mnt/tao/DADAO-v5`，分支 `TESTCASES-089t`）。QEMU 安装根 `.dadao/cross-toolchain/bin/qemu-system-dadao`（mtime `2026-11-01 06:09`，35169320 B）；trampoline `tools/testcases/lib/trampoline.bin`（16 B，10-27）；单例 runner `tools/testcases/lib/run_qemu_test.py`（`--case` 为 0-based）；门控 `make check-inst`（= L3 成员 `inst:base`）。

## 用户授权原话（主会话转述，逐条引文）

> **TESTCASES-089t：reserved cfx 普通 ld/st 覆盖**
> - 目标：为 `tests/inst` 增加 **active** 的 reserved cfx（6–14、19–61）普通 `ld` 与 `st` 向量（至少各 1 条），期望 `CFXMEM`（不是 `ILLI`/`UNMAPPED`）；不改 QEMU/spec/契约。
> - 形式：优先在 `tests/inst/base/reserved.yaml` 增加手写用例，或新增专用 `reserved-mem.yaml` 并登记 inventory；用 `addr[47:42]` 落 reserved（示例 cfxha 6：`6 << 42`），确保 fault 优先级不与 MALIGN/UNDI 冲突；编码从 `contracts/opcodes.yaml` 手推，不从 QEMU 反推。
> - 更新 `tests/inst/inventory.md`、`tests/case-ledger.tsv`（现场 `--write`）；`check-inst` 的 total/passed 计数按现场，不写死。
> - 验收：新向量在 `check-inst` 实际执行且 `CFXMEM`；旧向量零回退；L1/L2；反例（把期望改 `ILLI` ⇒ FAIL；还原回绿）。
> - 文件范围只列 `tests/inst/base/reserved.yaml`（或新 yaml）、inventory、case-ledger、任务书；不改 `schema.md`（除非必要字段说明，先报告）。

## 背景（architect 实测，非推测）

1. `TESTCASES-086t` 审计结论：`tests/inst/**` 中 reserved cfx 的**普通 `ld/st` 无任何 active 向量**（`ld/st/ldm/stm/lr/sc` 的基址现场只有 cfx63 RAM 与 addr=0 的 cfx0 形态），登记为遗留；同任务已把 reserved cfx 的**取指**期望修正为 `CFXMEM`（`ctrl-ret.yaml[9]`）。
2. 规范口径（原文）：`spec/DADAO-12-SEE-主管系统运行环境.md:78`「保留 cfx（6–14、19–61）的普通 `ld/st` 触发 CFXMEM」；`:775`（§5.2 异常进入流程）同口径；`:20-34` 的 cfxha 表给出 6-14 / 15 / 16 / 17 / 18 / 19-61 / 62 / 63 分配。QEMU 侧 `target/dadao/cpu.h:166` `DADAO_CFX_IS_RESERVED(h)` = `6..14 || 19..61`，与规范一致。
3. **可行性已实测**（architect 本会话，单例 `run_qemu_test.py --case`，`/tmp/opencode/TESTCASES-089t/`）：
   - `ld.ub` `word=0x10043000`、`rb3=0x180000000000`（cfxha 6）⇒ `Exit code 0x81` / `PASS - Expected CFXMEM, got CFXMEM`；
   - `ld.o` `word=0x20043000`、`rb3=0x380000000000`（cfxha 14）⇒ 同上 PASS；
   - `st.b` `word=0x18043000`（`rd1=0x42`）、`rb3=0x4c0000000000`（cfxha 19）⇒ PASS；`rb3=0xf40000000000`（cfxha 61）⇒ PASS；
   - `st.o` `word=0x21043000`（`rd1=0x42`）、`rb3=0xf40000000000`（cfxha 61）⇒ PASS；cfxha 19 ⇒ PASS。
4. **fault 优先级已实测**：`ld.uw` `word=0x11043001`（imms12=1，EA 相对 reserved cfx 基址**未对齐**）⇒ `Exit code 0x8C` **MALIGN**（不是 CFXMEM）⇒ **MALIGN 优先于 CFXMEM**，新用例必须用**对齐**的 EA（`imms12=0` / `rd2` 偏移对齐）。UNDI 不适用：新用例是**已定义编码**，不是 QFC 空白单元格。
5. `tests/inst/base/reserved.yaml` 现 3 例（`encoding.reserved: true`，`class: legality`，`expected_fault: UNDI`，无 `id`），文件头写「保留编码 → UNDI 向量（TESTCASES-008t，方案 A）」；该册已在 `tests/inst/inventory.md`「门控覆盖」表登记 `base/reserved.yaml`（L3 ✓），L2 列 `—`。
6. `tests/inst/schema.md`：`expected_fault` 允许 `CFXMEM`；`encoding.reserved: true` **仅**表示「QFC/子表空白单元格」且**强制** `class=legality` + `expected_fault: UNDI` + 无 `id` —— 本任务的新用例是「合法编码 + reserved **地址空间**」，**不得**带 `encoding.reserved`。

## 问题根源

地址空间 Step 1（`INTEG-038t`）把「reserved cfx 的普通 `ld/st` ⇒ CFXMEM」写进实现与规范，但向量侧只覆盖了它的两个近邻形态：`addr[47:42]=0`（ptw off ⇒ CFXMEM，32 例）与已分配 cfx 的 RAM/ROM 之外（⇒ UNMAPPED，11 例）。**真正的 reserved cfxha（6–14、19–61）普通访存一条 vector 都没有** ⇒ 该分支只有实现自证、没有独立 oracle；若实现把 reserved cfx 错判成「已分配但未实现」（CFXREG）或「未映射」（UNMAPPED），现有门控全绿也发现不了。086t 修正 `ctrl-ret[9]` 只补了**取指**路径，数据访存路径仍空。

## 目标（范围）

1. 在 `tests/inst/base/reserved.yaml` **追加 4 条 active legality 用例**（保留既有 3 例的序号/内容不变，追加在文件末尾）：
   - Case 3：`ld.ub`，`word=0x10043000`，`rb3=0x180000000000`（cfxha **6**，首段下界）；
   - Case 4：`ld.o`，`word=0x20043000`，`rb3=0x380000000000`（cfxha **14**，首段上界）；
   - Case 5：`st.b`，`word=0x18043000`，`rd1=0x0000000000000042`、`rb3=0x4c0000000000`（cfxha **19**，次段下界）；
   - Case 6：`st.o`，`word=0x21043000`，`rd1=0x0000000000000042`、`rb3=0xf40000000000`（cfxha **61**，次段上界）。
2. 文件头注释同步：说明本册现覆盖**两类** reserved —— ①保留**编码** ⇒ UNDI（原 3 例）；②保留 **cfx 地址空间**的普通 `ld/st` ⇒ CFXMEM（新 4 例，带 `id`）。删除「不参与 id 覆盖率门控（无身份）」这类只对旧 3 例成立的表述。
3. 登记与清单：`tests/inst/inventory.md` 增**一行**说明（M1 矩阵表下方纯文本，非机械表行）：reserved cfx 普通 `ld/st` 的 CFXMEM 覆盖位于 `base/reserved.yaml` 的 4 条 legality 例；**不改** M1 矩阵行、**不改**「门控覆盖（L2/L3）」表（追加形态不改变载体集）。`tests/case-ledger.tsv` 由 `python3 tools/infra/check_case_ledger.py --write` 重生成。
4. **不新增向量册**：若现场发现追加形态被 schema/校验/门控阻断（先跑 `validate_vectors.py` + `check_case_ledger.py` 复现），**停下报告**（含真实输出），由主会话裁定是否改「新增 `reserved-mem.yaml` + 登记门控表」形态；**不得**自行改判断。
5. 不动：`tests/inst/schema.md`、其它 `tests/inst/**/*.yaml`、生成器脚本、QEMU/`components/**`、`spec/**`、`contracts/**`、`Makefile`。

## 接口规范（逐字段，Spec-first）

每条新用例的形态（`class: legality` 的 fault 期望，`expected_state`/`expected_pc` 必须 `null`）：

- `class: legality`；`status: active`；`format: rrii`；`mnemonic` ∈ {`ld.ub`,`ld.o`,`st.b`,`st.o`}；
- `id` ∈ {`ld.ub_rrii_rd`,`ld.o_rrii_rd`,`st.b_rrii_rd`,`st.o_rrii_rd`}（`contracts/opcodes.yaml` 中 `scope: m1` 的身份，**不得**自造 id）；
- `encoding.word`：`(opc << 24) | (ha << 18) | (hb << 12) | imms12`，取 `ha=1`（`rd1`）、`hb=3`（`rb3`）、`imms12=0`；`opc` 取 `contracts/opcodes.yaml` 对应记录（`ld.ub=0x10`、`ld.o=0x20`、`st.b=0x18`、`st.o=0x21`），并**机械断言** `(word & mask) == value`（`mask=0xFF000000`）。**不得**从 QEMU/LLVM 输出反推编码。
- `input_state`：
  - load：`rb: {rb3: "<cfxha<<42>"}`（48 位 hex，`bits[63:48]=0`）；
  - store：另加 `rd: {rd1: "0x0000000000000042"}`（源值，宽度无关；`st.b` 只写低 1 字节，但本任务期望 fault ⇒ 不校验内存内容）。
- `expected_state: null`、`expected_pc: null`、`expected_fault: CFXMEM`；
- `spec_cite`：`SimRISC-01: <助记符>; DADAO-12: 核内地址空间`（`;` 分段；不带 `§`/节号；`check_spec_cite_targets.py` 校验通过）；
- `notes`：须写明 `addr[47:42]=<cfxha>（reserved，6–14/19–61）`、`EA=<hex>`、`⇒ CFXMEM (0x81)`，并说明 EA 对齐（`imms12=0`）。

码表：`CFXMEM = 0x81`（`0x80|1<<1`）、`UNMAPPED = 0x87`、`MALIGN = 0x8C`（ADR-0004 D5.8 / ADR-0020 D15）。

## 验收标准

1. `tests/inst/base/reserved.yaml` 共 7 例；Case 0–2 与任务前**逐字节相同**（`git diff -U0` 只在文件头注释与文件末尾有新行，既有 3 例内容零改动）；Case 3–6 满足「接口规范」全部字段，且**不带** `encoding.reserved`。
2. 单例实跑（每例一条，rc 与输出留证）：`python3 tools/testcases/lib/run_qemu_test.py tests/inst/base/reserved.yaml --case 3|4|5|6` 均 **rc=0**，输出 `Status: PASS - Expected CFXMEM, got CFXMEM`（`Exit code: 0x81`）。
3. **编码独立复核**（写进证据脚本，机械断言）：从 `contracts/opcodes.yaml` 取 4 条记录的 `opc`/`mask`/`value`，重算 `(word & mask) == value`；并断言 `(int(rb3,16) >> 42) & 0x3F` ∈ {6,14,19,61}、`int(rb3,16) <= 0xFFFFFFFFFFFF`、`imms12 == 0`（对齐，防 MALIGN 抢占）。
4. **旧向量零回退**：`git diff --quiet -- tests/inst/base/` 除 `reserved.yaml` 外全为 0 diff；`python3 tools/testcases/lib/run_qemu_test.py tests/inst/base/reserved.yaml --case 0|1|2` 仍 rc=0（UNDI 不回归）。
5. `make check-inst` **rc=0**，`0 failed`、`0 errors`；`total` = 修前现场 total **+4**（修前现场 `978 total … 5 deferred`，以现场读数为准、**不写死**），`deferred` 不变。
6. L1 `make check` rc=0；L2 `make check-modules` rc=0；`python3 tools/testcases/validate_vectors.py` rc=0（用例数 = 修前 +4）；`python3 tools/infra/check_case_ledger.py` rc=0（`--write` 后）；`python3 tools/spec/check_spec_cite_targets.py` rc=0。
7. **可达 FAIL 注入**：`cp` 备份 `reserved.yaml`（+ md5）→ 把 Case 3 的 `expected_fault: CFXMEM` 改为 `ILLI`（md5 必须变化）→ `--case 3` **rc=1** 且输出含 `Expected ILLI` → `cp` 还原、md5 与备份一致 → `--case 3` **rc=0**。**禁** `git checkout/restore/stash/show` 还原。
8. 证据脚本 `.work/evidence/<任务ID>/run.sh` **rc=0**（含第 1/2/3/4/5/6/7 条真实输出与 rc）；日志命名以 `TESTCASES-089t-` 起头（L1 `check-run-artifacts` A3 强制）；`git status --untracked-files=all` 无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留。

## 约束

- **只改**「文件范围」列出的文件；`tests/inst/schema.md`、其它 `tests/inst/**/*.yaml`、`tests/inst/README.md`、`tests/INVENTORY.md`、生成器脚本、`components/**`、`spec/**`、`contracts/**`、`.tao/adr/**`、`Makefile` **一律不改**。
- 不新增/删除既有 3 例；不改任何既有用例的字段值。
- 不改 `UNMAPPED`/`CFXMEM` 既有 43 例（086t 审计基线）；不改 `ctrl-ret.yaml[9]`。
- 不用 `encoding.reserved: true`（该标记强制 UNDI 且无 `id`，与本任务语义冲突）。
- 不跑夜跑/长套件；不跑全量 `check-full`（`check-inst` 即其 `inst:base` 成员）。
- 临时目录 `/tmp/opencode/TESTCASES-089t/`；不提交、不 push（提交权归 architect）。
- 失败保留现场并继续推进（自行处置 / 绕行 / 有据重试并记次数）；只在需用户语义裁定时留问。
- 完成区 ≤30 行；每轮审阅记录 ≤40 行；长输出留 `.work/log/testcases/` 或 `.work/evidence/`。

## 文件范围（计划修改）

1. `tests/inst/base/reserved.yaml`（文件头注释 + 追加 Case 3–6）
2. `tests/inst/inventory.md`（M1 矩阵表下方**一行**覆盖来源说明；机械表行不动）
3. `tests/case-ledger.tsv`（`check_case_ledger.py --write` 重生成）
4. `.tao/tasks/testcases/TESTCASES-089t-reserved-cfx普通访存覆盖.md`（完成区/审阅记录）
5. `.work/evidence/<任务ID>/{run.sh,*.log}`（不入库）

**明确不改**：`tests/inst/schema.md`（若确需补字段说明 ⇒ **先停下报告**）、`tests/inst/base/` 其它册、`tests/inst/base/mem-*.yaml`、生成器脚本、`components/**`、`spec/**`、`contracts/**`、`Makefile`、`.tao/knowledge/discussing.md`。

## 下发前预检（5 项，architect 现场结论）

1. **任务书内部一致：PASS** —— 验收 1–8 与「文件范围」一一对应；「追加 4 例」与「既有 3 例零改动」不矛盾（追加在末尾）；「不改 schema.md」与「新用例字段」不矛盾（现有 schema 已允许 `CFXMEM`、`rrii` 字段与 `class=legality`）；「inventory 增一行」与「不改门控表」不矛盾（追加形态不改变载体集，`semantics_gate.derive_carriers` 仍覆盖 `base/*.yaml` 全量，`reserved.yaml` 已登记 L3 ✓）；`check-inst` 即 L3 成员，不重复跑全量。
2. **本任务验证手段的全部前置可用：PASS（实测）** —— ① QEMU 安装根存在且可执行（35169320 B / 2026-11-01 06:09）；② trampoline 存在（16 B）；③ `run_qemu_test.py --case N` 可用（086t 已用，本会话 6 次单例实跑均得预期结果）；④ `make -n check-inst` / `-n check` / `-n check-modules` 均 rc=0；⑤ `check_case_ledger.py --write` 可用（`tests/case-ledger.tsv` 现存 1969 行、含 `reserved.yaml` 3 行）；⑥ `validate_vectors.py` / `check_spec_cite_targets.py` 均存在且仓内可用；⑦ 4 条候选向量**已单例实测 PASS**（见「背景」第 3 条）。
3. **验收逐条可跑性**：1–8 均「现在可跑」；**BLOCKED：无**。全量 `check-full`/`check-night` 按任务要求**不跑**（范围排除，非 BLOCKED）。
4. **与 `contracts/`、`tests/inst/` 一致：PASS** —— `spec/DADAO-12:78` / `:775` 明文；`tests/inst/schema.md` 允许 `expected_fault: CFXMEM`、`format: rrii`；`contracts/opcodes.yaml` 4 条身份 `scope=m1` 且 `mask/value` 与本任务 word 匹配；`contracts/**` 无 fault 期望表 ⇒ 无需改合约数据。
5. **拟改文件 × `spec/` 清单：0 命中** —— 4 个拟改路径均在 `tests/` 与 `.work/` 下，不触 `spec/**` ⇒ 无需 spec 锁 sha/changelog，也无需额外授权。

## 已知风险 / 遗留（不在本任务修，完成区登记）

- `tests/inst/base/reserved.yaml` 名称含「reserved」，追加 CFXMEM 例后语义分两类；文件头已要求写清。若评审认为应拆册，由主会话裁定（本任务按用户「优先追加」执行）。
- `components/qemu/patches/target/dadao/helper.c.patch` 注释写 `7-14`，宏为 `6–14`（既有 discussing 条目）——仅注释笔误，不改。
- `trap`/`escape` 到 reserved cfx ⇒ ILLI 的 active 向量仍缺（全 deferred `TESTCASES-033t`），不在本任务范围。
- `tests/inst/README.md` 所述 M1 条数（152）与现场（156）不一致，属既有文档漂移——本任务不改。

## 完成区

**测试结果**：单例 Case 3–6 全 PASS（`Status: PASS - Expected CFXMEM, got CFXMEM`、`Exit code: 0x81`、rc=0）；Case 0–2 UNDI 不回归（`Exit code: 0x89`、rc=0）。`make check-inst` rc=0：**986 total / 981 passed / 0 failed / 5 deferred / 0 errors**（修前现场 982 +4，deferred 5 不变）。L1 `make check` rc=0；L2 `make check-modules` rc=0；`validate_vectors` rc=0（156/156 M1、716 cases = 修前 712 +4）；`check_case_ledger` rc=0（+4 行）；`check_spec_cite_targets` rc=0。证据脚本 default rc=0、`--inject` rc=0。

**修改文件**：`tests/inst/base/reserved.yaml`（文件头改两类说明 + 追加 Case 3–6；Case 0–2 逐字节不动；`git diff -U0` 删除行仅 3 行旧头注释）；`tests/inst/inventory.md`（M1 矩阵表下方 +1 行来源说明，机械表行 0 改动）；`tests/case-ledger.tsv`（`check_case_ledger.py --write` 重生成，+4 行）；本任务书；`.tao/knowledge/milestones.md`（行状态 → 待验收，L1 A1 要求）。证据：`.work/evidence/TESTCASES-089t/{run.sh,logs/}`、`.work/log/testcases/TESTCASES-089t-*.log`（不入库）。

**验收结果**（真实输出，日志见 `.work/evidence/TESTCASES-089t/logs/`）：
- 编码独立重算：`ld.ub word=0x10043000 / ld.o 0x20043000 / st.b 0x18043000 / st.o 0x21043000`，`(word & 0xFF000000)==value` 全成立；ha=1、hb=3、imms12=0；`rb3>>42 ∈ {6,14,19,61}`、`rb3 ≤ 0xFFFF_FFFF_FFFF`、EA % 宽度 == 0。
- 计数现场派生：`carriers=20 live_cases=986 | baseline total=982 + delta=4 == post total=986`；`passed=981 failed=0 deferred=5 errors=0`。
- 反例注入：Case 3 `CFXMEM→ILLI`，md5 `1b111de8→ba263c33`（非空注入），`--case 3` rc=1 且含 `Expected ILLI`；`cp` 还原后 md5 一致、`--case 3` rc=0 回绿（未用 git 还原）。
- `git status --untracked-files=all`：5 个 M（3 数据文件 + 任务书 + milestones），无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`。

**新发现/坑**：① 任务书预检查写的「修前 978 total」与现场不符，实测基线 **982**（以现场为准，已在证据脚本内从修前日志读取、不写死）。② 证据脚本最初用 `git diff --quiet $BASE -- tests/inst/base/` 作「其它册零改动」断言，**目录 pathspec 会把 `reserved.yaml` 也算进去** ⇒ 恒假 FAIL；改为「显式文件列表 = 全部 base 册 − reserved.yaml」并断言列表长度 = 全部−1（防空集假绿）。③ 比对基线**不能钉 HEAD**（architect 提交/合并后会前移），钉不可变 commit `870b64e2`。④ 合法编码 + 保留地址的用例**不得**带 `encoding.reserved`（validate_vectors R2 强制 UNDI 且禁 id）。

**遗留问题**：`trap`/`escape` 到 reserved cfx ⇒ ILLI 的 active 向量仍缺（全 deferred `TESTCASES-033t`，不在本任务范围）；`helper.c.patch` 注释写 `7-14`（宏为 6–14）笔误未改；`tests/inst/README.md` 的 M1 条数漂移未改；任务书「已知风险」第 1 条（reserved.yaml 语义分两类，是否拆册）留主会话裁定。

## 审阅记录

### 第 1 轮 engineer 自审（逐行审查）

**范围**：`reserved.yaml`（头部 5 行 + Case 3–6 共 72 行）、`inventory.md`（+2 行）、`case-ledger.tsv`（重生成）、`run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `run.sh` 的「其它 base 册零改动」用目录 pathspec 会把 reserved.yaml 自身算入 ⇒ 实际 rc=1 假红 | ✅已修 | 改为显式文件列表（全部 base 册 − reserved.yaml）+ 断言列表长度 = 全部−1（防空集） | 全量脚本 rc=0；`old-base-vectors-unchanged` PASS（`15 of 16 files`） |
| F2 `run.sh` 以 `HEAD` 作基线：architect 提交后 diff 为空 ⇒ 「删除行 == 3 行旧头」断言变假红/恒真 | ✅已修 | 钉不可变 commit `BASE=870b64e2`（可用 `TESTCASES_089T_BASE` 覆盖），`git diff/git show` 统一用 `$BASE`，并 `export BASE` 供内层 bash/python 取用 | `bash -n` 通过；全量脚本 rc=0 |
| F3 `case-ledger.tsv` 是否只需重生成、无手写期望 | ✅已确认（无改动） | 未手写；`--write` 生成 4 行（id/class/word/fault/status 与 yaml 逐字段对齐） | `check-case-ledger: PASS`；diff 仅 +4 行 |
| F4 Case 3/4（load）的 `rd1` 不预置是否安全（dest 无需预置；合法编码检查/覆盖率守卫只对 semantic 要求 src 预置） | ✅已确认（无改动） | — | 单例 PASS；`validate_vectors` rc=0 |
| F5 notes 要求「addr[47:42]/EA/⇒ CFXMEM (0x81)/imms12=0」四项是否齐全 | ✅已确认（无改动） | 证据脚本逐项断言 4 条 notes | `yaml-structure-and-fields` PASS |
| F6 台账/清单是否越界（矩阵行、门控表、schema、其它 yaml） | ✅已确认（无改动） | 只加 1 行引用块说明 | `git diff --name-only $BASE -- tests/inst` == {reserved.yaml, inventory.md}；L1/L2 rc=0 |

**判决**：6 条 finding 全部处置完毕（F1/F2 已修并复验），无未修项 ⇒ 状态置 `待验收`。

### ARCH 复核与提交（architect，第 1 轮）

**独立重跑**（日志 `/tmp/opencode/TESTCASES-089t-review/`）：单例 `--case 3|4|5|6` 全部 `Exit code: 0x81` / `PASS - Expected CFXMEM, got CFXMEM` rc=0；`--case 0|1|2` `0x89` UNDI rc=0（不回归）；`make check-inst` rc=0（`986 total, 981 passed, 0 failed, 5 deferred, 0 errors` = 基线 982 + 4）；L1 `make check` rc=0；L2 `make check-modules` rc=0；`validate_vectors` rc=0（156/156、716 cases）；`check_case_ledger` rc=0（1969 身份）；`check_spec_cite_targets` rc=0（unresolved=0）；证据脚本 `run.sh --inject` rc=0。
**独立核字段/编码**（本方脚本，不采信叙述）：7 例；Case 0–2 与基线 `870b64e2` YAML 等值（`git diff -U0` 删除行仅 3 行旧头注释）；Case 3–6 均 `class=legality`/`active`/`rrii`/`expected_state|expected_pc=null`/`expected_fault=CFXMEM`、`encoding` 仅 `word`（无 `reserved`）；`(word & 0xFF000000) == value` 对 `contracts/opcodes.yaml` 4 条 `scope=m1` 记录全成立、ha=1/hb=3/imms12=0；`rb3>>42 ∈ {6,14,19,61}`、≤48 位、EA 按宽度对齐。
**独立反例（本方）**：Case 3 `CFXMEM→ILLI`（`cp` 备份 md5 `1b111de8`）⇒ `--case 3` rc=1 `Expected ILLI, got CFXMEM` ⇒ `cp` 还原 md5 一致 ⇒ rc=0（未用 git 还原）。
**档位/提交**：`待验收`（reviewer 未判决）⇒ 按主会话派单原话用 `feat(testcases): TESTCASES-089t reserved cfx 普通访存覆盖`（非 `WIP:`，偏差已声明）；分支 `TESTCASES-089t`，**未 push、未 merge**，哈希见 `git log -1`。
**文件集对账**：`git status -uall` 5 项 == 完成区「修改文件」（`reserved.yaml`、`inventory.md`、`case-ledger.tsv`、本任务书、`milestones.md`）；无 `schema.md`/其它 yaml/生成器/`components/**`/`spec/**`/`contracts/**`/`Makefile`。`milestones.md` 改 1 行状态 = L1 `check_milestones_fresh` A1 门控强制（非越界）；`inventory.md` 实为 1 行引用 + 1 空行分隔（机械表行 0 改动）。
**遗留（交主会话）**：`reserved.yaml` 是否拆册（现含两类语义）；`trap`/`escape` → reserved cfx ⇒ ILLI 仍全 deferred（`TESTCASES-033t`）；`helper.c.patch` 注释 `7-14` 笔误（宏为 6–14）；`tests/inst/README.md` M1 条数漂移（152 vs 现场 156）。

### 第 1 轮 reviewer 验收（独立重跑，非采信叙述）

**重跑记录（workdir=仓库根，本方命令/输出）**
- `./.work/evidence/TESTCASES-089t/run.sh` ⇒ **`EXIT=0`**，39 项检查全 PASS、0 FAIL（含 L1 `make check` rc=0「repository checks (L1): PASS」、L2 `make check-modules` rc=0「module checks (L2): PASS」）。
- 单例（脚本 S2/S4 逐条 rc）：Case 3/4/5/6 ⇒ rc=0、`Exit code: 0x81`、`Status: PASS - Expected CFXMEM, got CFXMEM`；Case 0/1/2 ⇒ rc=0、`Exit code: 0x89`、`Expected UNDI, got UNDI`（不回归）。
- `make check-inst`（本方跑，`.work/log/testcases/TESTCASES-089t-check-inst.log:33`）：`Results: 986 total, 981 passed, 0 failed, 5 deferred, 0 errors`（rc=0）。基线本方独立复算（20 载体 × `git show 870b64e2:…` 逐册计数）= **982** ⇒ 982+4=986、deferred 5 不变、「+4 且零回退」成立。
- `validate_vectors.py` rc=0（`156/156 M1 … 716 cases` = 修前 712+4）；`check_case_ledger.py` rc=0（`1969 身份 … PASS`）；`check_spec_cite_targets.py` rc=0（`unresolved=0`）——均本方重跑。
- 字段/编码本方独立核：7 例；Case 0–2 与 `870b64e2` YAML 逐字段相等（`git diff -U0` 删除行仅 3 行旧头注释）；Case 3–6 = `legality/active/rrii`、`expected_state|expected_pc=null`、`expected_fault=CFXMEM`、`encoding` 仅 `word`（无 `reserved`）；`(word & 0xFF000000)==value` 对 `contracts/opcodes.yaml` 4 条 `scope=m1` 全成立（`opc=0x10/0x20/0x18/0x21`），ha=1、hb=3、imms12=0；`rb3>>42 ∈ {6,14,19,61}`、`rb3 ≤ 0xFFFFFFFFFFFF`、EA 按 1/8 字节宽度对齐；`spec_cite`/`notes` 四要素齐全。

**独立反例（Case 4 → UNMAPPED，不照搬 Case 3→ILLI）**：`cp` 备份 md5 `1b111de8` → 改 Case 4 `expected_fault: CFXMEM→UNMAPPED`（md5 `c595e9a8`，非空注入）→ `run_qemu_test.py --case 4` **rc=1**、`Status: FAIL - Expected UNMAPPED, got CFXMEM` → `cp` 还原 md5 `1b111de8` 相等 → `--case 4` **rc=0** 回绿。全程未用 `git checkout/restore/stash`；还原后 `git status --porcelain -uall` = 0 行。

**约束逐条**：① 文件集 = 5 项（`reserved.yaml`/`inventory.md`/`case-ledger.tsv`/任务书/`milestones.md`，`git diff --name-only 870b64e2 e1e6d494` 核），**无** schema/其它 yaml/生成器/`components/**`/`spec/**`/`contracts/**`/`Makefile` 改动；`milestones.md` 不在任务书文件范围，但为 L1 `check_milestones_fresh` A1 强制（表行状态 == 任务书 `**状态**`），完成区已声明 ⇒ 判非越界。② 既有 3 例与既有 UNMAPPED/CFXMEM 43 例、`ctrl-ret[9]` 零 diff。③ 未用 `encoding.reserved`（schema 该标记强制 UNDI+无 id）。④ 未跑夜跑/`check-full`；日志名均 `TESTCASES-089t-` 起头；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej`。

**脚本审核**：`run.sh` 各断言均有可达 FAIL 路径（逐项 rc/子串判定），计数现场派生、基线钉 `870b64e2` 非 HEAD，含防空集断言，无恒真/两支同果；注入非空 + `cp`+md5 还原 ⇒ 合格（不合格项：无）。

**发现（均不阻断）**：① 任务书预检「修前 978」与现场 982 不符（文档笔误，验收按现场，任务书已写「以现场为准」）；② `inventory.md` 实际 +2 行（1 说明 + 1 空行分隔），机械表行 0 改动、说明内容符合任务意图 ⇒ **可接受**；③ `reserved.yaml` 现含两类语义，文件头已分①②写清、任务书「已知风险 1」本就交主会话裁定 ⇒ **非阻断**，拆册与否由 architect 收尾裁定；④ 完成区「+1 行」与实际 +2 行措辞差 1 空行（文档级）。

**判决：Accepted** —— 验收标准 1–8 在本方重跑下全部通过、约束无违反（仅写本审阅记录，未提交）。

### /complete 交叉复核与提交（architect）

**交叉复核（本人现场）**：分支 `TESTCASES-089t`、HEAD `e1e6d494`、起始工作树仅本任务书（reviewer 记录）；`git diff --name-status 870b64e2 e1e6d494` = 5 项，与完成区「修改文件」一致；单例 Case 3–6 均 rc=0 / `Exit code: 0x81` / `Expected CFXMEM, got CFXMEM`；`check_case_ledger` rc=0（1969 身份）；L1 `make check` rc=0（`repository checks (L1): PASS`，含 `check-milestones-fresh` A1/A5 绿）；`make check-inst` rc=0（`986 total, 981 passed, 0 failed, 5 deferred, 0 errors`）。
**收尾改**：`**状态**` 待验收→已验证；`milestones.md` 089t 行 `待验收`→`已验证`、时间 `2026-11-01 06:25（登记）`→`2026-11-01 08:19`（去 `（登记）`，L1 A5 强制），并按 A4 倒序上移至 088t 行之前。
**档位/提交**：reviewer Accepted ⇒ 正常提交 `review: TESTCASES-089t Accepted（reviewer + architect 交叉复核）`；文件集 2 项（本任务书、`milestones.md`）；分支 `TESTCASES-089t`，**未 push、未 merge**，哈希见 `git log -1`。
**遗留（交主会话）**：`reserved.yaml` 是否拆册（现含两类语义）；`trap`/`escape` → reserved cfx ⇒ ILLI 全 deferred（`TESTCASES-033t`）；`helper.c.patch` 注释 `7-14` 笔误（宏 6–14）；`tests/inst/README.md` M1 条数漂移（152 vs 现场 156）；任务书预检「修前 978」笔误（现场 982）。
