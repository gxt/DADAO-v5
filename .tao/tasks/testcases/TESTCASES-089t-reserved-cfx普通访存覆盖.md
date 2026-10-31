# TESTCASES-089t: reserved cfx 普通 ld/st 覆盖（CFXMEM）

**模块**：testcases
**项目里程碑**：M10
**依赖**：`TESTCASES-086t`（已验证；审计确认「reserved cfx 的普通 ld/st 无 active 向量」为覆盖缺口，登记遗留）、`INTEG-038t`（已验证；`addr[47:42]` 选 cfxha，reserved cfx 普通 `ld/st` ⇒ `CFXMEM`）
**状态**：待开始

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

**测试结果**：（待填写）
**修改文件**：（待填写）
**验收结果**：（待填写）
**新发现/坑**：（待填写）
**遗留问题**：（待填写）

## 审阅记录

（待 engineer 自审后按轮次追加）
