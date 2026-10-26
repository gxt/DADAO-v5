# TESTCASES-067t: 测试框架梳理与 `tests/` 重组方案（调研，不改代码）

**模块**：testcases
**项目里程碑**：M10
**依赖**：SPEC-176t、ADR-0038
**状态**：已验证

## 执行环境
只读调研 + 方案文档；**不移动/不修改任何测试或工具代码**。

## 背景（用户 2026-10-26）
用户指出：`tests/` 目录太乱，找不到实际测试向量与覆盖范围；要求先梳理**完整测试框架**，给出**主流 ISA 的通行做法**，确定方案后再重组 `tests/`；并明确生成物落点（是否都在 `.dadao/tests/`）、重生成是否**逐字节相同**、该目录自身的整理方案。

## 现状事实（architect 2026-10-26 实测）
- `tests/`：338 文件 / 10 个顶层项 —— `llvm`(216)、`e2e`(45)、`scripts`(30)、`vectors`(25)、`atomics`/`clmul`/`fma`/`minmax`/`roundint`(各 4–5)、`qemu`(1)、`case-ledger.tsv`。
- `tests/vectors/`：`isa` + `atomics`/`bitcnt`/`clmul` 子目录 + `inventory.md` + `README.md`；与顶层 `atomics/clmul/...` 并存，职责重叠。
- `.dadao/tests/`：**19967 文件 / 1.2 GB**，`.gitignore` 忽略 `.dadao/`；子目录 = `bootrom`/`codegen-e2e`/`codegen-m6`/`elf-*`/`embench-user`/`harness`/`ir-lli-diff`/`libc-*`/`lit-output`/`llvm-ts-user`(16112)/`llvm-ts-user-050t`/`m5-e2e`/`m6-embench`/`probes`(空)/`smoke`。
- 生成物落点混用：`check-qemu-smoke` 日志落 `.work/log/qemu/`；`test-codegen` 产物落 `.dadao/tests/codegen-e2e/`；`case-ledger.tsv` 由 `tools/infra/check_case_ledger.py --write` 生成（实测重生成 **byte-identical**）。
- 门控：`check-qemu-semantics`（L3）、`check-qemu-smoke`/`check-lit`（L2）、`check-case-ledger`（L1，身份清单）。
- 覆盖：`tests/vectors/isa` 无 cfx；cfx 5/6/15/16/17/62 零向量；系统探针 044/045/047/049 手工。

## 目标输出（仅文档）
1. `tests/INVENTORY.md`：全部测试资产一览（目录/文件数/用途/层级/门控/手工-自动/覆盖对象），计数现场派生。
2. `docs/Process-09-测试组织规范.md`（方案；08 已被《测试运行产物与日志组织规范》占用）：
   - **主流 ISA/项目调研**：RISC-V（`riscv-tests`、`riscv-arch-test`）、ARM（Arm Architecture Tests、`kvm-unit-tests`、kselftest）、x86（`kvm-unit-tests`、selftests）、QEMU（`tests/tcg`/`qtest`/`functional`/`unit`）、LLVM（lit/FileCheck、llvm-test-suite）、Linux（kselftest、KUnit）——各自「源码 vs 生成物 / 层级 / 自检 oracle / 门控」做法。
   - **DADAO 方案**：I（指令级）/ S（系统级）/ E（端到端）/ U（工具单测）四层；目录、ID（`I-*`/`S-*`/`E-*`/`U-*`）、YAML schema、独立 oracle、门控分层。
   - **生成物**：落点（`.work/build/tests/` vs `.dadao/tests/` vs 其它）、目录镜像规则、`manifest/coverage`、`make clean-tests`。
   - **确定性**：逐字节可重生成的条件（排序/无时间戳/相对路径/`SOURCE_DATE_EPOCH`）+ `make test-repro` 判据。
   - **迁移分期**：先建索引与 runner、再按 I→S→E 迁移；每期门控。
3. `tests/README.md`：源码树索引 + 如何跑 + 生成物去哪 + 覆盖矩阵指针。
4. **待用户决策清单**：生成物落点、是否保留 `case-ledger.tsv` 为提交物、`tests/llvm` 是否并入 `tests/isa`、确定性目标（严格/仅产物）。

## 约束
- **不移动、不改写**任何测试/工具/Makefile；只新增上述 3 份文档。
- 调研每条给来源（项目/文档），DADAO 现状给 file:line/路径。
- 临时目录 `/tmp/opencode/TESTCASES-067t/`；不提交。

## 验收
1. 三份文档落盘；`INVENTORY.md` 覆盖全部顶层项与 `.dadao/tests/` 子目录，计数现场。
2. 主流调研 ≥5 个项目，每项含「源码/生成物分离 + 层级 + oracle + 门控」四要素。
3. 方案含目录树、ID、schema、生成物落点、确定性判据、迁移分期、决策清单。
4. `git status` 证明无测试/工具改动；完成区贴命令/输出。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 计数锚点含本册新增文档，先记 340 后实为 341 ⇒ 必漂 | ✅已修 | 锚点改为稳定口径（含本册两份文档），`tests_files_total=341` | `run.sh` 23 键 0 mismatch |
| 证据脚本断言 `^### 6\.`，正文为 `## 6.` ⇒ 恒 FAIL | ✅已修 | 脚本改 `^## 6\.` | `spec_has:^## 6. 迁移分期 PASS` |
| `tests/scripts` 分类写「Embench 头（7）」，实为 6 | ✅已修 | 改 6；分类合计 24 = 30−6 pyc，与现场一致 | `find tests/scripts -type f` 复核 |
| L1 行误把 `check-code-range`(L2) 列为 L1 | ✅已修 | 删除该名，只列 L1 目标 | 对照 `Makefile:808` |
| 「11 个生成器」无依据（实为 5 带 check + 5 无 check + 1 库） | ✅已修 | 改为「5 + 5 + 1 库」并点名 | `grep -l --check tools/**/generate_*.py` |
| A 案与 `ADR-0016 D6` 冲突可能被忽略 | ✅已修 | 文档头 + §4.1 + §7.1 三处显式标注「需 ADR 修订」 | 文档 grep `ADR-0016 D6` |
| 事实/推断混写风险 | ✅已修 | 「推断（非事实）」「未测（如实标注）」分节 | §4.3 / §5.3 |

判决：7 项全部处置，无未修 finding。

### 第 1 轮 reviewer 验收

**判决：Needs Revision**（1 项计数锚点阻断 + 3 条非阻断 finding）。逐条证据：

**重跑命令与真实输出**
- `bash .work/evidence/TESTCASES-067t/run.sh` ⇒ **exit=1，PASS=26 FAIL=2**：`MISMATCH dadao_tests_bytes doc=1132542115 live=1132536346`（另 22 键全等）；`restore_count_check_green` 同因级联 FAIL。完成区「28/28 GREEN」在当前树不可复现。
- ledger 确定性：`check_case_ledger.py --write --ledger /tmp/…`（rc=0）+ `cmp tests/case-ledger.tsv /tmp/…` ⇒ **exit=0，byte-identical**（md5 `ffb154cd…` 双方一致）。
- `tools/testcases/generate_rev_vectors.py --check` ⇒ **exit=1 FAIL** 如实；独立 `--out /tmp/…` + `diff` ⇒ 恰 **62/62 行 `spec_cite`**（`Bit manipulating…`→`SimRISC-04: rev.o`），非 spec_cite 差异 **0**。其余 4 生成器 `--check` 均 exit=0。
- `git show --stat 0f5bc654`：仅 3 文档 + 任务书 + milestones 新增；`git status --porcelain -uall` 前后均**干净**（run.sh 注入已自还原，INVENTORY md5 `2f2f168d…` 未变，无越界/残留）。

**抽查计数（reviewer 现场独立派生）**：`tests/` 文件 341 ✓、pyc 9 ✓、顶层 13 项 ✓；`.dadao/tests` 文件 19967 ✓、**字节 1132536346 ✗（漂 −5,769 B）**；向量以 `yaml.safe_load` 独立解析 = **22 册/1456 例/193 id** ✓（分册数与 §3.1 逐册吻合）；ledger 1456 vector + 500 lit ✓。未接线清单抽查全实：atomics 5 源无目标、m6 8 程序、4 单测脚本 Makefile 零命中、9 个 e2e 死源 runner 零引用。

**Process-09 审读**：8 套件（RISC-V×2/ARM/kvm-unit-tests/kselftest/KUnit/QEMU/LLVM，含 x86）均含四要素 ✓；A/B/混合三案 + `ADR-0016 D6`+2026-10-06 裁定冲突（文档头/§4.1/§7.1）✓；I/S/E/U 定义、ID、schema、迁移分期、决策清单齐 ✓；09 编号说明成立（Process-08 在库未被覆盖）✓；**E 层口径差异已在 §7.9 如实列为待决策** ✓（无 finding）。

**阻断 finding（计数类：写死值 vs 现场值）**：锚点 `dadao_tests_bytes` 写死生成树精确字节。0f5bc654（12:56）后 QEMU-076t（ce308710, 13:45）改 tests 源并重跑门控，13:40–13:41 重生成 `.dadao/tests` 580 个文件 ⇒ 必漂；本项目每任务收尾跑 L2 都会重生成该树，该锚点**定义上必漂**，与 INVENTORY 自身 §5.1-⑧/§7-9（生成树含时间戳不可逐字节）结论自相矛盾。**修复（最小）**：锚点块删 `dadao_tests_bytes`，体积降为 §1 散文并注明「生成树，门控重跑后漂，非门控锚点」；`dadao_run_dirs=144` 同为生成树派生（跑一次 suites 即新增时间戳目录），建议一并降级；同步删 run.sh 对应 live 键后重跑应回绿（注入自检仍须红）。
**非阻断**：① §1「入库 330〔未提交〕」提交后 `git ls-files tests`=332，表述过时（architect 收尾顺手改）；② run.sh `restore_count_check_green` 复用全量锚点比对，掺混「还原成功」与「锚点新鲜」两判据（本次还原本身完好）；③ 完成区「28/28」未考虑并发任务漂移。

## 完成区

**测试结果**：一键证据 `bash .work/evidence/TESTCASES-067t/run.sh` ⇒ **28/28 PASS, RESULT: GREEN, EXIT=0**；注入 `vector_cases=1455` ⇒ 计数检查 FAIL，`cp` 还原 md5 一致后回绿。本册为只读调研，**未跑**被测语义门控（L2/L3）。

**修改文件**（仅新增 3 文档 + 台账/证据）：
- `tests/INVENTORY.md`、`tests/README.md`、`docs/Process-09-测试组织规范.md`（任务书写 08，但 08 已被《测试运行产物与日志组织规范》占用，改 09 并在文档头说明）
- `.work/evidence/TESTCASES-067t/run.sh`（不入库）、`.tao/knowledge/milestones.md` 状态行、本任务书
- 未改任何测试/工具/Makefile/spec/contracts

**验收结果**：
- `find tests -type f | wc -l` = **341**（入库 330 + 9 pyc + 本册 2 文档）；`find .dadao/tests -type f | wc -l` = **19967**，`du -sb .dadao/tests` = **1132542115**
- 向量 **1456 例 / 193 身份 / 22 YAML**；ledger **1956**（vector 1456 + lit 500）；lit **76+12+63+14**
- `check_case_ledger.py --write --ledger /tmp/…` + `cmp` ⇒ **byte-identical**（md5 `ffb154cd…`）
- `generate_{rol,atomics,clmul,bitcnt}_vectors.py --check` ⇒ 4/4 PASS（byte-identical）
- `generate_rev_vectors.py --check` ⇒ **FAIL（rc=1，62/62 例 `spec_cite` 漂移）**
- `llvm-mc` ×2 / `ld.lld` ×2 同输入 ⇒ 逐字节一致（md5 `b23de33a…` / `0bf12593…`）
- `git status --porcelain -uall -- tests tools Makefile spec contracts` ⇒ 仅 `?? tests/INVENTORY.md`、`?? tests/README.md`

**新发现/坑**：① 08 号已占用（编号冲突）；② `rev.yaml` 生成器确定但入库陈旧，因 `rev` 不在门控无人发现 ⇒ 生成器 `--check` 必须进门控；③ 未接线：atomics probe、m6 codegen 8 程序、9 个 e2e 源、4 个单测脚本；④ `.dadao/tests` 1.2 G 无清理目标，约 210 M 不可重生成；⑤ `lit-output/.lit_test_times.txt` 含时间戳 ⇒ 运行脚手架按定义不可复现，确定性判据须限定「入库生成物」；⑥ A 案（`.work/build/tests`）与 ADR-0016 D6 + 用户 2026-10-06 裁定冲突，须 ADR 修订。

**遗留问题**：待用户决策 4+5 项见 `docs/Process-09 §7`（生成物 A/B、`tests/llvm` 归属、`case-ledger.tsv` 是否入库、确定性严格度；附加：孤儿产物、9 个死源、手工资产升层、09 编号、E 层边界〔前册 E=Linux/busybox 与本册 E=程序级端到端的差异〕）。开工前工作树已有删除项 `.tao/tasks/testcases/TESTCASES-067t-QEMU测试向量盘点与ISE组织.md`（`D` 状态），非本册改动，未触碰。

### architect 收尾（2026-10-26）
- reviewer 阻断项已修：`tests/INVENTORY.md` 删除两个「生成树派生、定义上必漂」的锚点（`dadao_tests_bytes`、`dadao_run_dirs`），改为散文说明；`tests_files_total` 的入库数按提交后实况改为 332。
- 证据脚本同步：移除两个易漂锚点、允许 `tests/INVENTORY.md`/`README.md` 的文档级改动；重跑 **28/28 PASS**（`RESULT: GREEN`）。
- 无测试/工具/Makefile/spec 改动；按 reviewer 意见不再开新一轮。
