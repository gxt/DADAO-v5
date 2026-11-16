# m15-testcases-008: 退役 clmul C/IR 探针（4 文件 + 驱动/oracle + L3 成员）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无（`m15-testcases-005` 已合入）
**可并行分片**：否（改 `Makefile` / `tests/inst.yaml` / `tools/**` 共享文件，单写者）
**预估**：1.5–2 h
**档位**：中改（多文件 + 改门控组成；复核 ≥2 路注入 + 相关门控）
**状态**：待验收

## 背景（用户 2026-11-16 指令 + 两项裁定）

用户原话：「关于 clmul 的指令测试，`tests/inst/clmul/clmul_ir.ll` 你来判断要不要移动到 unit/llvm 中，其余三个可以删除」；随后两项裁定：**① L3 的 `fp-clmul` 成员直接删该行；② `run_clmul_probe.py` 与 `oracle_clmul.py` 两个都删**。

**`clmul_ir.ll` 判定 = 不搬、直接删**（现场对比）：

- `tests/inst/clmul/clmul_ir.ll` 定义 4 个函数（`clmul_generic_lo` / `clmul_intr_hi` / `clmul_pair_lo` / `clmul_pair_hi`），**文件内无断言**；结构核对在 Python 驱动（`objdump` + `ctx.add`）；
- `tests/unit/llvm/lit/CodeGen/DADAO/clmul.ll` 定义 **8 个**（上述 4 个的对应 + `clmul_pair` / `clmul_wide` / `clmul_wide_lo` / `clmul_wide_hi`），**有 `FileCheck` 结构断言**（`clmul.o {rd0, rd8}` / `{rd8, rd0}` / `{rd8, rd9}`，钉 ADR-0035 D2 的「高半在前」），跑在 **L2 `check-lit`**；
- 另有 `tests/unit/llvm/e2e/lit/clmul_builtin.test` 覆盖 `__builtin_dadao_clmul` 的编译产物。
⇒ 搬过去是**重复一份更弱的用例**，不搬。

**退役模式先例**：`m13-testcases-044`（fma/minmax/roundint）、`m13-testcases-050`（atomics 五探针）同一模式；`clmul` 是最后一个。

## 覆盖披露（须写进完成区，不得只写"退役"）

- **保住**：ISA 语义 = `tests/inst/04-arith-logic-octa/clmul.o_rrrr_rd.S`（**19 链例检查点 + 2 故障例**，`run_asm_suite.scan_source` 现场派生，含在 904/904 内）；编译器侧 = 上述 lit 两处；
- **丢掉**：① i128 **composite 的运行期**（把高低半拼回 128 位再比）只在 `clmul_edges.c`；② **GHASH、CRC-32C** 两条真实算法链路的运行期覆盖。

## 目标（一处不漏，否则门控红）

1. 删 `tests/inst/clmul/`（4 文件：`clmul_edges.c`、`clmul_ghash.c`、`clmul_crc32c.c`、`clmul_ir.ll`）；
2. `tests/inst.yaml`：删 `inst-clmul-002`…`inst-clmul-005` 四条；**头部注释**去掉 `check-{rnd,minmax,fma,clmul}-probe` 的 clmul 提法（改为「探针已全部退役」）；
3. `Makefile`：删 `check-clmul-probe` 目标（`_locked-check-clmul-probe` 及其 2 条 recipe）、`.PHONY` 清单、`reconfig` 清单、`help` 行；
4. 删 `tools/testcases/run_clmul_probe.py`（587 行）与 `tools/testcases/oracle_clmul.py`；
5. `tools/infra/check_writer_guards.py`：去掉 `tools/testcases/run_clmul_probe.py` 条目（**注意不改变其余被护栏脚本的行为**）；
6. `tools/testcases/l3_run.py`：`DEFAULT_MEMBERS` 删 `("inst", "fp-clmul", "make check-clmul-probe")`，并把上方注释改成「四类 FP 探针（rnd/minmax/fma/clmul）已全部退役，FP 由 `07-floating-point` 的 `.S` + lit + e2e 承担」（L3 余 3 成员：`check-arch` / `check-unit-full` / `test-m6`）；
7. `tests/README.md`、`tests/INVENTORY.md`：记录退役（**保留历史**，写明退役任务号与覆盖承接方），删掉"clmul 探针保留"这类过期口径；
8. `tools/qemu/user_mode_smoke.py` 第 629 行注释若仍以 `run_clmul_probe.py` 作参照，改写成不依赖已删文件的表述。

## 验收（真实 rc + 输出）

1. **零残留引用**：`git grep -n 'clmul-probe\|run_clmul_probe\|oracle_clmul\|inst-clmul-00'` = 0（`.tao/archive/**` 的历史记录**不算**残留，须显式排除并说明）；
2. `make check-tests-index` PASS，条数 = 476 − **4** = **472**（现场核）；
3. `make check-writer-guards` PASS（清理后仍能检出注入：临时给某被护栏脚本加未授权 writer 调用 ⇒ 红，`cp`+md5 还原 ⇒ 绿）；
4. `make -n check-full` 不再出现 `check-clmul-probe`；**L3 成员表 = 3 条**（`check-arch` / `check-unit-full` / `test-m6`），并核 `tools/testcases/l3_run.py` 无残余 `fp-clmul`；
5. `make check-inst-asm` **904/904**（`tests/inst` 其余载体不受影响）；`make check-inst-macro-scope`、`check-case-ledger`、`check-tests-index`、`check-dirs`、`check-no-residue` 全 rc=0；L1 `make check`（外部红须逐项归因）；
6. **2 路注入**（`cp`+md5 还原）：① 在 `tests/inst.yaml` 恢复一条 `inst-clmul-002` 指向已删文件 ⇒ `check-tests-index` 红；② 在 `Makefile` 恢复 `check-clmul-probe` 目标 ⇒ 其 recipe 报"找不到 `run_clmul_probe.py`"（红），证明依赖已断且未留假绿；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **不改变任何其它用例/门控的语义**；`check-full` 只因成员退役而少一项，不得顺带改其它成员；
- 只动：`tests/inst/clmul/**`（删）、`tests/inst.yaml`、`Makefile`、`tools/testcases/run_clmul_probe.py`（删）、`tools/testcases/oracle_clmul.py`（删）、`tools/infra/check_writer_guards.py`、`tools/testcases/l3_run.py`、`tests/README.md`、`tests/INVENTORY.md`、`tools/qemu/user_mode_smoke.py`（仅注释）、本任务书；
- **不动** `tests/unit/llvm/**`（lit 用例已覆盖，不改判据）、`tests/inst/04-arith-logic-octa/clmul.o_rrrr_rd.S`、`components/**`、`spec/`、`contracts/`；
- 不提交 git；注入还原 `cp`+md5（**禁 `git checkout/restore`**）；基线钉死 commit（`ISS-458`）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-16）

**审查范围**：13 个改动文件逐行审查（`git diff` 全量 + 删除清单核对 + 三处清单同步核对：
`.PHONY` / `GATE_LOCKED_TARGETS` / `WRITER_TARGET_COMPONENTS`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. `check_l3_report.py` 仍要求「四 scope（含 inst）」，删掉最后一个 inst 成员后与新成员表冲突 | ⏸延后（越界：不在硬约束清单，须授权） | 未改；写入「待裁定」 | `check_l3_report --self-test` 11/12、`l3_run --self-test` 8/9（红因相同） |
| 2. `l3_run.py` 自检断言写死「manifest ≥4 scope」，3 成员必假红 | ✅已修 | 改为按 `DEFAULT_MEMBERS` **现场派生**精确相等（缺任一成员 scope ⇒ FAIL） | 自检 `manifest covers every member scope (['arch','tset','unit'] vs ['arch','tset','unit'])` PASS |
| 3. 「保留历史」与「`git grep` 零残留」冲突：INVENTORY 直接写目标名会命中 | ✅已修 | 历史行改写为「（`clmul` 探针目标）已退役」+ 承接方 | 零残留 grep 0 行 / rc=1 |
| 4. 越界文档仍称「clmul 保留 C/LL 探针」（`tests/inst/README.md:4`、`tests/inst/MIGRATION.md:220`、`docs/Process-07 §1.1`） | ⏸延后（不在硬约束清单） | 未改；列入遗留 | 已逐处核对，见「遗留问题」 |
| 5. 证据脚本 C7 断言 `grep -c ==1`，但 suite 汇总打印两次 ⇒ 假红 | ✅已修 | 改 `-ge 1` 并保留 rc=0 断言 | 全量重跑末行 `m15-testcases-008: PASS (0 失败)` rc=0 |
| 6. 删目录后是否有门控按目录存在性判红 | ✅已核 | 未改代码 | `check-dirs` / `check-no-residue` / `check-tests-index` 全 rc=0 |

**判决**：finding 2/3/5/6 已修；finding 1/4 当时为范围缺口（需 architect 扩范围），已按第 2 轮指令处置。

### 第 2 轮 engineer 自审（2026-11-16，返工轮：收口三项未决项）

**审查范围**：本轮 4 个改动文件 + 证据脚本（`check_l3_report.py` 全文、两处 docs、任务书）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. 第 1 轮 finding 1：scope 必需集写死四 scope | ✅已修 | 删 `REQUIRED_SCOPES` 常量，新增 `required_scopes()` 按 `l3_run.DEFAULT_MEMBERS` 现场派生；`check()` 用它并改错误文案 | 自检 13/13；三 scope 真报告 PASS；缺 `arch` 报告 FAIL |
| 2. 第 1 轮 finding 4：三处过期文字 | ✅已修 | `tests/inst/README.md` 首段、`tests/inst/MIGRATION.md` 删除段、`docs/Process-07 §1.1` L3 行 | 逐处重读，见「完成区」 |
| 3. `--self-test` 的「缺成员」用例写死 `fp-clmul`（成员表已无此成员 ⇒ 用例会空转、断言退化为恒过） | ✅已修 | 改为现场派生「丢清单首项」并**断言错误文本**含 `缺 L3 成员行：<成员>` | `missing arch:cfx member => FAIL (errors=…缺 L3 成员行：arch:cfx)` |
| 4. 「旧报告仍可读」未被任何用例覆盖 | ✅已修 | 新增用例：GREEN_ROWS + 已退役 `inst:fp-clmul` 行 ⇒ 期望 PASS（只查缺不查多） | `legacy report with retired inst:fp-clmul => PASS` |
| 5. 改门控后 `docs/Process-07` 的 `check-l3-report` 行仍写「覆盖四 scope」「十二类注入」 | ✅已修 | 改为「覆盖成员表所列 scope（现场派生）」+「十三类注入」 | 与 `--self-test` 实测 13 条一致 |
| 6. 证据脚本 C1 把 `.tao/tasks/**` 也算残留 ⇒ rebase 后 `m14-qemu-006` 任务书 1 行历史引用假红 | ✅已修 | 分母改为「代码/门控/文档/`Makefile`」，`git grep` 排 `.tao/archive` + `.tao/tasks`；任务书命中单独 `[INFO]` 打印（不隐藏） | C1 0 行 rc=1；INFO 16 行（本书 15 + `m14-qemu-006` 1） |
| 7. 未自行复核 rebase 后 `check-patch-tree` 是否真绿 | ✅已核 | 未改代码 | rc=0 / 10 patch set / 416 patches OK / 0 problem |

**判决**：7 条 finding 全部已修/已核，无未修项；`check_l3_report.py` 与 `l3_run.py` 的自检从 11/12、8/9 恢复到 13/13、9/9。

### 第 3 轮 engineer 自审（2026-11-16，用户裁定追加：删孤儿生成器）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. `tools/qemu/generate_clmul_vectors.py` 是孤儿（产物从未存在 / 无索引条目 / 无 Make 入口）；且其写入路径指向已删目录，一旦被跑会重建 `tests/inst/clmul/` 并让 `check-tests-index` 假红 | ✅已修（用户裁定「删掉（推荐）」） | 删该文件 | `git grep 'generate_clmul_vectors'`（排 `.tao/archive` + 任务书）= rc=1 / 0 行；`check-writer-guards` 27/27、`check-tests-index` 472、`check-dirs`/`check-no-residue`/`compileall tools` 全 rc=0 |
| 2. 删除是否影响门控名单（writer-guard 等） | ✅已核 | 未改名单 | `git grep` 在 `tools/infra/`、`Makefile` 零命中 |
| 3. 证据脚本未覆盖此项 | ✅已修 | 新增 C11a（文件不存在）/C11b（零活引用）+ 归档提及 `[INFO]` 打印 | 全量重跑 34 PASS / 0 FAIL / `PASS (0 失败)` |

**判决**：3 条 finding 全部已修/已核，无未修项。

### 第 4 轮 engineer 自审（2026-11-16，用户指令：清 `semantics_gate.py` docstring 的过时路径）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. `tools/qemu/semantics_gate.py` docstring 的载体清单仍写 `tests/inst/clmul/*.yaml`（该 YAML 载体 `m13-testcases-043` 已退役、C/IR 探针与目录由本任务删除） | ✅已修（仅注释） | 该条改为「`clmul` 的 YAML 载体曾同列此集：载体已随 `m13-043` 全量退役、探针与目录由 `m15-008` 删除 ⇒ 现场已无该目录」；断言条列全 `CARRIER_DIRS` 并注明 `clmul` 目录已删 | `compileall` rc=0；`git grep 'tests/inst/clmul'`（排 `.tao/archive`）仅任务书命中；`check-dirs` rc=0；`check-qemu-forms` rc=0（唯一活用途未被扰动） |
| 2. 是否动了逻辑/判据 | ✅已核 | `git diff` 仅 docstring 文本；`CARRIER_DIRS`/`derive_carriers`/`--form-check` 一字未改 | 同上 `check-qemu-forms` PASS（扫描 335 文件，0 命中） |

**判决**：2 条 finding 已修/已核，无未修项。

### 第 1 轮 reviewer 验收（2026-11-16；基线 `92fdb9d3..736bb818`，独立重跑，rc 均取命令自身）

**重跑**：`check-tests-index`=0（`PASS（472 条`；基线现场数 476→472，`11+272+3+186`）；`check-writer-guards`=0（27/27，`entries=17`）；`check-inst-asm`=0（`904/904 镜像通过`，第 1 次即绿、未遇 guard 冲突）；`check-inst-macro-scope`/`check-case-ledger`/`check-dirs`/`check-no-residue`/`check-qemu-forms`/`compileall tools` 全=0；`check_l3_report --self-test`=0（13/13）；`l3_run --self-test`=0（9/9）；证据脚本 `.work/evidence/m15-testcases-008/run.sh` 重跑=**0（34 PASS / 0 FAIL）**，与完成区逐条一致。
**删除与零引用**：`git diff --name-status` = 20 文件（7 D：4 探针+2 工具+1 生成器；13 M），7 个被删文件盘上均不存在、`tests/inst/clmul/` 目录已删；`git grep -E 'clmul-probe|run_clmul_probe|oracle_clmul|inst-clmul-00|generate_clmul_vectors|tests/inst/clmul'` 排 `.tao/archive`+`.tao/tasks` ⇒ **rc=1 / 0 行**（活区命中仅本任务书 18 行、归档 7 处、`m14-qemu-006` 任务书 1 行历史引用，均显式列出）；`make help | grep clmul`=1、`make -n check-full` 2 行无 clmul、`grep check-clmul Makefile` 与 `READER_ENTRIES`=1。
**`check_l3_report` 自造三例**（独立 writer，未复用其 `_write_report`）：① 仅 2 scope ⇒ rc=1，报 `缺 scope 行：tset` + `缺 L3 成员行：tset:m6-integration`；② 全 3 成员但 tset rc=1 ⇒ rc=1 `manifest 有非零 rc 行`；③ 旧四 scope（含 `inst:fp-clmul`）⇒ rc=0 PASS。**自证性结论**：必需集取自代码、报告是独立持久化产物 ⇒ 「缺项」可被发现（路 B 实证）；缩表方向会跟随成员表（进程内实测：表缩到 arch ⇒ PASS）——属单源设计固有属性、非放水，须靠成员表改动走 code review 兜底。
**自设计注入（`cp`+md5，不复用 engineer 3 路）**：A 删活条目 `inst-00-isa-design-002` ⇒ `check-tests-index` **rc=2**（载体未入索引）→ 还原 md5 EQUAL → rc=0/472；B 给 `DEFAULT_MEMBERS` 加成员 ⇒ `check_l3_report` **rc=1**（`缺 L3 成员行：arch:fp-review-injected`）→ 还原 EQUAL → rc=0；C `run_asm_suite.py` 绕开 `writer_guard.start_guard(` ⇒ `check-writer-guards` **rc=2**（`S1 … missing=[run_asm_suite.py]`）→ 还原 EQUAL → 27/27。
**复位对账**：`git status --porcelain -uall`=**0 行**；6 个关键文件 md5 与注入前快照 `diff` 全等（首轮注入因我备份目录笔误 `cp` 失败 ⇒ 用「读 `736bb818` blob→临时文件→`cp`→md5 等于注入前基线」还原，**未用** checkout/restore/stash；注入前快照 status=0 行，故无他人未提交改动风险）。
**L1 `make -k check` 5 红逐项归因（均非本任务）**：`check-patch-tree` 5 problems（`.work/source/qemu target/dadao/helper.c`、`linux` 2 文件被并行任务改脏 ⇒ 完成区「0 problem」为当时真值，现因并发转红）；`check-knowledge-refs` 2 条（`m14-linux-011`/`m15-testcases-004` 任务书）；`check-milestones-fresh` R1（`m14-qemu-003` 有 worktree 但台账在「待开始」）；`check-run-artifacts` 43（`m14-qemu-006` 日志）；`check-temp-dirs` 5（`m14-linux-005..009`）。
**覆盖披露核验**：`clmul.ll` 8 `define` + FileCheck 覆盖 `{rd0,rd8}`/`{rd8,rd0}`/`{rd8,rd9}`/`{N,rd8}`·`{rd8,N}` 四拼写与高低半绑定；`clmul_builtin.test`（5 RUN）在 `_locked-check-lit` 的 `tests/unit/llvm/e2e/lit` 路径内（结构核验；lit 未实跑——`install-host` 被并行任务占用，且本 diff 不触 `tests/unit/**`）；`clmul.o_rrrr_rd.S` 未被本任务改动（md5=基线）。
**Findings（doc 级，不阻断，交 architect 收尾改）**：① 「12 检查点」不准——现场 `run_asm_suite.scan_source` = **19 链例检查点 + 2 故障例（点号 1..21 连续 pts_ok=True）**，含在 904/904 内（任务书:26/:142 与 `tests/INVENTORY.md:223`；覆盖方向只强不弱）；② `docs/Process-09-测试组织规范.md:237` 仍写 L3 含「4 个 FP 探针」，与实际 3 成员矛盾（该文件不在本任务允许清单，engineer 未越界改）；③ 证据脚本 `BASE_SHA=d485d348` 标签过期（真实基线 `92fdb9d3`，仅打印、不参与判据）。
**约束核验**：4 项用户裁定全落实（4 探针删 / `clmul_ir.ll` 不搬 unit/llvm / 两工具删 / `fp-clmul` 成员删 / 生成器删）；硬约束守住——`user_mode_smoke.py`、`semantics_gate.py` 仅注释，`READER_ENTRIES` 只减 clmul 一条、其余行为未改松，`tests/unit/**`、`components/**`、`spec/`、`contracts/`、`tests/inst/*.S` 零改动，无越界。
**判决：Accepted**（验收命令块在我自己的重跑下全部通过、约束无违反；3 条 doc 级 finding 由 architect 收尾处理，不另开一轮）。

## 裁定结果（原「待裁定」项，已由 architect 指令选 A 并落地）

原问题：L3 成员 4→3 后 `inst` 无成员，而 `check_l3_report.py` 的 `REQUIRED_SCOPES = {inst, arch, unit, tset}`
写死 ⇒ ① `make check-l3-report` 在退役后新报告上必红；② `l3_run --self-test` 8/9；③ `check_l3_report --self-test` 11/12。

**处置（本轮落地）**：按选项 A —— scope 必需集按 `l3_run.DEFAULT_MEMBERS` **现场派生**，不另抄常量；
`--self-test` 的缺成员用例改现场派生并断言错误文本，新增「旧报告（含已退役 `inst:fp-clmul` 行）仍 PASS」用例；
`docs/Process-07 §1.1`（L3 行 + `check-l3-report` 行）口径同步。旧报告与新三 scope 报告均 PASS，缺 `arch` 的报告仍 FAIL（可达 FAIL 路径保留）。

## 完成区

**测试结果**：一键证据脚本（C1–C11 + 3 路注入）末行 `m15-testcases-008: PASS (0 失败)` rc=0

**第 1 轮（主体，已合入 `b0079cf7`）**
- 删 6 文件（`tests/inst/clmul/*` ×4 + `run_clmul_probe.py`/`oracle_clmul.py`，−2219 行）；改 7 文件（`tests/inst.yaml`、`Makefile`、`check_writer_guards.py`、`l3_run.py`、`tests/README.md`、`tests/INVENTORY.md`、`user_mode_smoke.py` 注释）
- 真数：`check-tests-index` **472**、`check-inst-asm` **904/904**、`l3_run.DEFAULT_MEMBERS` **3**、`check-writer-guards` 27/27；3 路注入（护栏未改松 / yaml 恢复一条 / Makefile 恢复目标）均红 → `cp`+md5 还原 → 绿

**第 2 轮（本轮：收口三桩未决项）**
- `check_l3_report.py`：删写死 `REQUIRED_SCOPES`，新增 `required_scopes()` 按 `l3_run.DEFAULT_MEMBERS` **现场派生**；缺成员用例改现场派生 + 断言错误文本；新增旧报告（含已退役 `inst:fp-clmul` 行）PASS 用例 ⇒ 自检 **13/13**；`l3_run --self-test` **9/9**
- 正/反例：`l3_run` 现造三 scope 真报告 ⇒ `make check-l3-report` **PASS**（rc=0）；删 `arch` 行 ⇒ **FAIL**（rc=2，`缺 scope 行：arch` + `缺 L3 成员行：arch:cfx`）；真实旧报告（20261109T082411Z，四 scope）仍 PASS
- 口径清理（不改判据）：`tests/inst/README.md` 首段、`tests/inst/MIGRATION.md` 删除段、`docs/Process-07 §1.1` 的 L3 行 + `check-l3-report` 行
- `check-patch-tree` rebase 后 **rc=0 / 10 patch set / 416 patches OK / 0 problem**（上一轮 6 problems 确为基线陈旧：`d485d348` 早于 `m14-qemu-006` 改写的 qemu 三份 patch）
- **删孤儿生成器** `tools/qemu/generate_clmul_vectors.py`（用户裁定原话：「删掉（推荐）」；跨模块例外已授权）：依据 = 其产物 `tests/inst/clmul/clmul.yaml` **从未存在**（`git ls-files` 无此文件）、`tests/inst.yaml` 无该 yaml 条目（YAML 载体于 `m13-testcases-043` 全退役）、`Makefile` 无入口（`grep` 无命中）、**零活引用**（仅 `.tao/archive/M9/{QEMU-068t,SPEC-170t}` 历史 6 行）；`check_writer_guards` 等门控名单里无此条目

**L1 `make check`**：3 红，逐项归因（均非本次改动；主工作树同项同红）
- ① `check-knowledge-refs` 2 条具体 `.work/**`：`m14-linux-011` 任务书:88、`m15-testcases-004` 任务书:88
- ② `check-run-artifacts` 43 条非法名：全部属并行任务 `m14-qemu-006` 的运行期日志目录
- ③ `check-temp-dirs` 5 条陈旧任务临时目录（`m14-linux-005`…`009`，mtime 3.2–3.4 h）
- 另：`compileall tools` rc=0、`check_issues` rc=0、`check-writer-guards` 27/27、`check-dirs`/`check-no-residue`/`check-inst-macro-scope`/`check-case-ledger` 全 rc=0
- 修改文件（本轮）：`tools/testcases/check_l3_report.py`、`tests/inst/README.md`、`tests/inst/MIGRATION.md`、`docs/Process-07-门控分层规范.md`、`tools/qemu/generate_clmul_vectors.py`（删）、`tools/qemu/semantics_gate.py`（仅 docstring）、本任务书；逐项「期望/实际/rc」见证据脚本 `.work/evidence/<任务ID>/run.sh`

**覆盖披露**：
- 保住：ISA 语义 = `inst/04-arith-logic-octa/clmul.o_rrrr_rd.S`（12 检查点，含在 `check-inst-asm` 904/904 内）；编译器侧 = `lit/CodeGen/DADAO/clmul.ll`（8 函数 + `FileCheck` 高低半序）+ `e2e/lit/clmul_builtin.test`（`check-lit`）
- 丢掉：① i128 composite 的**运行期**（高低半拼回 128 位再比）只在被删的 `clmul_edges.c`；② GHASH、CRC-32C 两条真实算法链路的运行期覆盖

**新发现/坑**：① 门控里的「必需 scope 集」必须与成员表**同源派生**，否则成员一退役就假红（本轮已修）；② 钉死基线会让 `check-patch-tree` 因组件 patch 前进而必红（`ISS-458` 的代价，派单时须知会）；③ 零残留判据应把 `.tao/tasks/**` 与 `.tao/archive/**` 一并排除并**打印记录项**，否则他人任务书的历史引用会假红

**遗留问题**：已清（本任务内）——`tools/qemu/semantics_gate.py` docstring 的过时路径提法已改为退役说明（仅注释；`compileall`/`check-qemu-forms`/`check-dirs` 全 rc=0）；无未决项
