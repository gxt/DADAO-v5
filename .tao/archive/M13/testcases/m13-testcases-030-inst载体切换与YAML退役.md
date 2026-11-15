# m13-testcases-030: `tests/inst` 载体切换（`.S` 入门控）+ YAML 退役

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-012`/`013`（`.S` 套件已建）+ `m13-spec-001`（退出码表）
**可并行分片**：否（改门控集合，需与语料任务串行）
**状态**：已验证

## 背景（`ISS-413`，P1）

`base/mem-rd/mem-ra/mem-rb` 三册里 `ld`/`st`/`ldm`/`stm` 的 id 已全部有 `.S`，但删 YAML 会让**四个门控**立刻红：`validate_vectors`（116 gap）、`check_case_ledger`（多 167 行）、`check-generator-sync`（无输入）、`check-tests-index`（file 不存在）。

根因：`.S` 套件**不在任何门控里**，而 `inventory.md`/`case-ledger`/生成器同步仍以 YAML 为真源。

## 目标

1. **载体切换**：`tests/inst/inventory.md` 的「类/载体」登记改为指向 `.S`（或由 `.S` 注释派生），`validate_vectors` 接受 `.S` 载体
2. **新门控**：`run_asm_suite.py` 进 L2（如 `check-inst-asm`），至少覆盖已迁移的 38 个 id
3. **生成器退役**：`generate_mem_vectors` 等对已迁移族的 `--check` 退役；`check-generator-sync` 改指
4. **YAML 删除**：三册清空后 `git rm`，`tests/inst.yaml` 索引条目同步，`check_case_ledger --write` 重生成
5. `MIGRATION.md` §5 台账勾掉

## 前置（已知红，接入前必须处置）

- **`ld.o_rrii_ra` 链例点 20 在 QEMU/gem5 红**（`ISS-426`：`ra0` 写未丢弃 SBZ `[63:54]`；chipyard 合规）。本任务把 `run_asm_suite.py` 接入 L2 时，该红会让 `check-inst-asm` 直接红 ⇒ **先修 `ISS-426`（或在本门控里按「已知缺陷 pin + 到期清算」处理并写清判据）**，不得放宽用例期望。
- 另：`m12-chipyard-028` 已撤 hmon 自装 workaround，故障例按固件 hmon 口径（返回槽 `0xF8`、cause_id `0xE0`）读数；`m13-testcases-031` 提示 `st.o_rrii_rb.S` 的 `.text` 已到 `0x1920`（上限 `0x1E00`），若收紧上限需复查。

## 验收

1. 删除三册 YAML 后：`validate_vectors` / `check_case_ledger` / `check-tests-index` / `check-generator-sync` **全部 rc=0**
2. 新门控 `check-inst-asm` rc=0，且**能失败**（注入一个错误期望 ⇒ 红）
3. 273 例 md5 不变；`check-inst` rc=0
4. 完成区 ≤30 行、无运行期路径；「修改文件」与 `git status` 对账

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号），**动手前 `git rev-parse --show-toplevel` 自证**；禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；「修改文件」与 `git status` 对账；计数现场值。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需裁定写进任务书返回主会话。
6. 一键证据脚本；反例注入「注入→FAIL→还原（`cp`+md5）→回绿」。
7. 禁 `reset --hard`/`checkout -- .`（`ISS-402`）。
8. 命令作用域 = workdir，用相对路径。

## 完成区

**测试结果**：通过（逐项真实 rc 见下）。新门控 `check-inst-asm` rc=0（**264 id / 897 镜像**全绿 = 链例 264 + 故障例 633）；`check-inst` rc=0（Vast `1020 total / 1015 passed / 0 failed / 5 deferred`，Tiny `14/14`）；`check-tests-index` rc=0（486 条）、`check-case-ledger` rc=0（现场 2033 = vector 1510 + lit 523）、`validate-vectors` rc=0（156/156、gaps 0、264 `.S` 载体）、`check-generator-sync` rc=0（5 个生成器）、`check-rev-vectors`/`check-inst-smoke`(90/90)/`check-writer-guards`(27/27)/`check-dirs`/`check-no-residue`/`check-knowledge-refs`/`check-spec-cite-targets` rc=0；273 例 sweep md5 `2d4d9465…c1489`（covered 273）**不变**；`check-lit` 176/176、`test-codegen` 19/19。L1 `make check` 红 3 项均非本任务（patch-tree=并行 chipyard 改动、musl-freshness=他任务重建戳、temp-dirs=他任务陈旧 /tmp）。
**修改文件**（24 改 / 6 删，与 `git status -uall` 逐项一致）：`Makefile`、`docs/Process-07`；`tests/inst.yaml`、`tests/case-ledger.tsv`、`tests/inst/{inventory.md,MIGRATION.md,schema.md}`；`tools/testcases/{validate_vectors.py,README.md}`、`tools/testcases/inst/{run_asm_suite.py,run_qemu_smoke.py}`、`tools/testcases/lib/{run_qemu_test.py,verify_harness_dump.py,test_harness_exit_path.py,README.md}`、`tools/testcases/{unit/run_codegen_e2e.py,parity/{run_parity.py,README.md},riscv_tests/run_riscv_tests.py,diff_ir_lli.py,arch/min_rom_probe_010t.py,arch/min_rom_probe_031t.py}`、`tools/qemu/semantics_gate.py`、`tools/infra/check_writer_guards.py`；删 `tests/inst/base/mem-{rd,ra,rb}.yaml`、`tools/testcases/generate_mem_vectors.py`、`tools/testcases/lib/{gen_trampoline.py,trampoline.bin}`。
**验收结果**：① 新门控设计与覆盖数：`_locked-check-inst-asm`（L2 成员 + `GATE_LOCKED_TARGETS`）= `run_asm_suite.py --books-root tests/inst --platforms qemu`，载体集=含 `.S` 的子目录（12 册现场派生）、每册取本册 `.lds`；链例比结果字节流（8×检查点数）、故障例比 monitor 段退出码；**不挂** `build-bootrom` 前置（L2 不重建共享产物）。② YAML 删除清单：`base/mem-rd|mem-ra|mem-rb.yaml`（167 例 / 30 id），`tests/inst.yaml` 489→486、ledger 2200→2033（只减 167 行）。③ 生成器/ledger 改指：`generate_mem_vectors.py` 退役（`git rm`），`check-generator-sync` 6→5；`check_case_ledger --write` 重生成；`inventory.md` 30 个访存 id 载体列改 `01-load-store/<id>.S` + 新增「`.S` 载体覆盖」节、L2/L3 表删 3 行 mem；`validate_vectors` 增 `.S` 载体结构断言（stem 属 opcodes 身份 / 含用例行 / 点号 1..N 连续，复用 `run_asm_suite.scan_source`）+ `file` 列无悬空。④ trampoline 退役：`gen_trampoline.py`+`trampoline.bin` 删；`--trampoline`→`--bootrom`（`run_qemu_test`/`semantics_gate`/`run_qemu_smoke`/`parity`/`diff_ir_lli`/`riscv_tests`/`verify_harness_dump`/`test_harness_exit_path`/`min_rom_probe_031t`/`check_writer_guards` 调用点），默认值经 `paths.py` 解析 `bootrom/{tiny,step5}`；`run_codegen_e2e` 删 deprecated 开关；Makefile 传参与 4 处注释清掉。
**新发现/坑**：① `ISS-426`（`ld.o_rrii_ra` 点 20 的 `ra0` SBZ）在现安装根 QEMU 上**已不复现**（897 镜像全绿）⇒ 无需「已知缺陷 pin」；建议主会话核实 gem5 侧后关/改该 issue。② 共享 `gate.lock` 被并行 gem5 构建长期持有（`make` 把 75 折成 2）⇒ 取证用 `GATE_LOCK=` 隔离锁 + 证据脚本内置「锁忙→重试 1 次」分支；`run_asm_suite` 的 read guard 改为**只登记本平台集合真会用的二进制**（QEMU 门控不被 gem5/chipyard 构建挡住）。③ `tools/chipyard/mem_sweep.py` 的 `SOURCES` 仍指三册（范围外，已无输入）；`tests/INVENTORY.md` 与 `docs/Process-09 §7` 仍把 `gen_trampoline`/`trampoline.bin` 当现状描述（范围外）；`min_rom_probe_*`/`chipyard/*_sweep` 里的 `trampoline` 指**镜像内跳转桩**（非被删资产）。
**遗留问题**：① ctrl 4 册与 `reg-*`/`aip-si`/`rol`/`reserved` **未删**（L3 `check-inst` 载体 / `br.*` 双路径守卫只在 YAML 有结构字段 / `inst_sweep` 273 例输入 / `generate_isa_vectors` 渲染目标），判据与后续做法写在 `MIGRATION.md §5.2 末段`；② `mem_sweep.py` 载体改造或退役须另立任务（含 chipyard 域）；③ 上述两处越界文档残留待主会话决定是否随批次修。
**返工（reviewer 第 1 轮）**：C9 扫描面改为 `git grep`（只搜 **git 已跟踪** 的 `*.py`/`*.mk`/`Makefile`，不再扫 `.cache/refs`/`.work`）⇒ 命中 3 处全为已登记遗留（`tools/chipyard/mem_sweep.py`，`ISS-441` 范围），**非登记残留 = 0**（条数只打印、不判等）；新增 I4 证明 C9 判据仍可红。`Makefile` help 的 `Six` → `Five vector generators`；`inventory.md`「`.S` 载体覆盖」如实写明覆盖边界（**整册删除无人拦**：实测删 `03-wyde-imm/` + 其 `inst.yaml` 条目后 `validate-vectors` rc=0 264→256、`check-tests-index` rc=0；`.S` 无逐条删除哨兵），补双向断言记为后续（`ISS-441` 同批或另立）。
**返工复验（第 1 轮）**：本机 `run.sh` **rc=0**（46 s，C1–C9 + I1/I1′/I2/I2′/I3/I3′/I4 全 PASS）；节点 `ics170` **rc=0**（`NODE_RC=0`，墙钟 **57 s**，`--jobs=38` = 核数−2，`qemu_md5=b34ed7f99d8b1d90821f4b819eeb15c9` 与本机一致，C2 `264 id / 897 镜像` 全绿，C9 扫描面 269 个已跟踪文件 / 命中 3（全登记）/ 非登记 0）；节点跑完工作树与注入文件 md5 与本机一致，节点仓 `HEAD=a4c84ae60 dirty=0`。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

审查范围：本任务全部改动（Makefile 目标/L2 装配、`run_asm_suite` 多册与 read guard、`validate_vectors` 载体模型、`semantics_gate`/`run_qemu_test`/`run_qemu_smoke` 的参数改名与默认值、脚本删除面、台账重生成、三层文档同步）。逐项结论与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `--books-root` 与默认 `--vectors` 叠加导致 01 册被扫两遍（302 id） | ✅已修 | `--vectors` 仅在显式给出或未给 `--books-root` 时生效 | 扫描输出 264 id（C1） |
| F2 同一目录重复传入仍会重复跑镜像 | ✅已修 | `dirs` 去重 | `--vectors 01 --books-root tests/inst` ⇒ 264/897 |
| F3 `--scan-only` 传空 read-guard 清单被解释为「全组件」⇒ 误挡并行构建 | ✅已修 | scan-only 不建 guard（`guard=None`） | 扫描 rc=0（C1） |
| F4 QEMU-only 门控被并行 gem5 构建挡住（rc=75） | ✅已修 | read guard 只登记本平台集合真会用的二进制 | `check-inst-asm` rc=0（C2）；gem5 构建在跑时亦绿 |
| F5 `verify_harness_dump` 新 import 的 `paths` 路径层级算错（`ModuleNotFoundError`） | ✅已修 | 改 `dirname×2 + infra` | `import verify_harness_dump` 成功、`BIOS` 解析到 tiny 固件 |
| F6 `test_harness_exit_path` 的「真超时」用例在固定固件下不再超时（raw `-kernel` 被拒：小于 256 B 保留前缀） | ✅已修 | spin 镜像改为 `256 B 前缀 + spin 字`，并注明契约 | 该自测 5/5 PASS |
| F7 `check-inst` 注释里 Tiny 例数写死 44（现状 14） | ✅已修 | 改为「条数现场统计」并注明访存族转 `.S` | Makefile 注释；`check-inst` 输出 14/14 |
| F8 注入取证时若进程被中断，被注入的 `.S` 可能留在盘上 | ✅已修 | 证据脚本加 `trap restore_all`（cmp+cp 兜底）与 `timeout 180` | 二次运行前后 md5 一致（C/I 段） |

**判决**：finding 全部已修，无未修项 → 可交付 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-14）

**判决：Needs Revision**（1 项阻断 = 一键证据脚本在派单节点必红；其余全部验收项在 reviewer 亲跑下全绿）

**重跑记录（reviewer 亲跑，括号内为真实 rc）**
- `make check-inst-asm`（主控机，真实 `gate.lock`、未用隔离锁）(0)：现场 `264 id / 897 镜像 / jobs=62`、`897/897`（链 264 + 故障 633）
- 节点 `ics170`：`remote.py status` (0)（load 0.09 / disk 26% / running=none）；`sync_node_artifacts.sh ics170` (0) verify OK，qemu md5 安装根 `b34ed7f99d8b1d90821f4b819eeb15c9`、`.work/build` `725c5da788cf4ca7ceba569221f9f1f6`（与主控机逐件相同）；分支经 bundle 落节点、干净检出
- 节点 `make check-inst-asm` (0)：`NPROC=40`、`264 id / 897 镜像 / jobs=38`、`897/897`、墙钟 13 s；注入还原后复跑 (0)（14 s，节点 `dirty=0`）
- `make check-inst` (0)：Vast `1020/1015/0/5`（载体 25 册）+ Tiny `14/14`；`check-inst-smoke` (0, 90/90)；`check-tests-index` (0, 486=11+286+3+186)；`check-case-ledger` (0, 2033=vector1510+lit523)；`validate-vectors` (0, 156/156、264 `.S` 载体、gaps 0)；`check-generator-sync` (0, 5 生成器)；`check-lit` (0, 176/176)；`test-codegen` (0, 19/19，`-o install-host` 避开禁跑项)；`check-rev-vectors`/`check-writer-guards`(27/27)/`check-dirs`/`check-no-residue`/`check-knowledge-refs`/`check-spec-cite-targets` (0)；`inst_sweep emit` covered=273、`sweep_expect.bin` md5 `2d4d94651346ef673c5a855e024c1489`
- 证据脚本（reviewer 在 `ics170` 重跑，一键证据脚本 run.sh，运行期证据目录）：⇒ **`SCRIPT_RC=1`**；C1–C8、I1/I1′、I2/I2′、I3/I3′ 全 PASS（C2 `897/897 / 264 id`、I1 注入 rc=1、I2 rc=2、I3 rc=2，还原 md5 一致），**唯 C9 FAIL**：`期望=6 个资产不存在 / 非登记引用 0 处｜实际=gone=1 refs=50 非登记=47`

**覆盖等价性（独立核）**
- 被删三册 **167 例 / 30 id**（rd 122 + rb 23 + ra 22；class = encoding30 + legality77 + semantic30 + boundary30，全 active）；30 id 全有 `01-load-store/<id>.S` 且在 `check-inst-asm` 逐例执行：**30 链例 + 159 故障例 = 189 镜像全 PASS**，每 id ≥1 个 CFXMEM `0xF1` PASS（合计 66，MISS=0）
- Tiny `expected_fault` **43 = 30（被删 mem，由 `check-inst-asm` 的 `0xF1` 故障例承接）+ 13（仍在 YAML，`check-inst` Tiny 段照跑）**；44→14 差额恰为这 30 条（现场：被删册 `profiles:[tiny]` 恰 30、全 legality/CFXMEM；现存 14 = 13 fault + aip-si 1）⇒ 承接成立
- 计数对账：`inst.yaml` 289→286 条（`check-tests-index` 489→486）；`case-ledger` 2204→2037 行 = **2200→2033 条，净减 167 行、0 新增**，逐行归属 rd122/rb23/ra22

**独立注入（`cp`+md5，均回绿）**：① 改 `st.w_rrii_rd.S` 期望 ⇒ `make check-inst-asm` **rc=2**（内层 1，`896/897`，`[FAIL] … 检查点 15 … rc {'qemu': 3}`），还原 md5 `250d7f3f…` ⇒ 复跑 rc=0；② 删 inventory 引用的 `.S` ⇒ `validate-vectors` **rc=2**（`DATA COVERAGE GAP … no .S carrier exists` ×4）；③ 整册删 `03-wyde-imm`（8 个 `.S`）⇒ `validate-vectors` rc=0（264→256 载体）+ `--scan-only` rc=0（256 id/882 镜像）= 静默变少

**约束核验**：worktree 自证 = `/tmp/opencode/m13-testcases-030/wt`；未 commit/push（`git status -uall` 起止皆空、注入 md5 对账一致）；未跑 `install-host`/`check-modules`；并行度 节点 38（40−2）/ 主控机 62（64−2），未手写小 `--jobs`；多镜像批次全在 `ics170`（本机只留秒级静态门控与单例注入）；取证**未用** `GATE_LOCK=` 隔离锁（日志无 rc=75/BUSY，`gate.lock` 事后无持有者）；改动面 31 文件 = 完成区 24 改 + 6 删 + 任务书，越界命中 **0**（`spec/|contracts/|components/`）

**阻断 finding**
- **F1 证据脚本 C9 在节点必红（脚本缺陷，reviewer 不代改）**：`run.sh:115/119` 的 grep 未排除 `.cache/refs/**` 只读参考树 ⇒ 同一条命令主控机仓根得 88、`ics170` 得 50、裸 worktree 才得 3；且 `refs -eq 3` 把残留数写死（将来关掉 `ISS-441` 反而假红）。**改法**：① grep 面改 `git ls-files`（或 `--exclude-dir=.cache`）；② 阈值现场派生（非登记引用=0、登记残留只允许落在 `tools/chipyard/mem_sweep.py`，条数只打印不设限）；③ 在 `ics170` 重跑 `run.sh` 至 `SCRIPT_RC=0`，并把节点/并行度/墙钟写进完成区。

**非阻断 finding**：② `inventory.md`「`.S` 载体覆盖」表明写「不参与双向比对」⇒ 非 inventory 引用的册整册删除静默（实测③），建议补「表 ↔ 现场载体集」双向断言或另立任务；③ `Makefile:311` help 仍写 `Six vector generators`（现 5）；④ `mem_sweep.py` `SOURCES` 3 行悬挂 ⇒ 实跑 `list` rc=1 `FileNotFoundError`（**响亮失败非静默**；无任何门控/Makefile 引用，`ctrl_sweep` 仅 import 不加载）⇒ 主会话已登 `ISS-441`；⑤ `tests/INVENTORY.md`、`docs/Process-09 §7` 文档残留，完成区已披露为范围外。

**L1**：`make -k check` rc=2，红 5 项 —— `check-patch-tree`（18 问题全在 qemu/gem5/chipyard 组件树，本任务 `components/` 命中 0）、`check-musl-freshness`（他任务重建戳）、`check-temp-dirs`（他任务陈旧临时目录）、`check-milestones-fresh`（R1: `m13-qemu-015` 有 worktree 未入表 → 主会话）、`check-knowledge-refs`（reviewer 首稿写了具体证据路径 ⇒ 当场改写后 rc=0）；均不在本任务改动面。

**未跑/采信**：chipyard/gem5 三方逐字节、`check-inst` 之外的 L3 探针不在本轮范围；三方一致与 `ISS-426` 结论采信 `m13-qemu-015`/`m13-testcases-034` 记录（本轮仅核 QEMU 侧 897/897）。

### 第 2 轮 reviewer 验收（2026-11-14，返工复验）

**判决：Accepted**（上轮唯一阻断 F1 已修，并经 reviewer 双端重跑 + 三路独立注入验证；其余验收项复跑全绿）

**重跑（reviewer 亲跑，括号=真实 rc）**
- 本机任务树一键证据 (0)：45 s，C1–C9 + I1/I1′/I2/I2′/I3/I3′/I4 全 PASS；C9 `扫描面 269 / 命中 3（全登记）/ 非登记 0`
- 节点 `ics170`：`remote.py status` (0)（load 0.50 / mem 126 GB / disk 26% / running=none）；`sync_node_artifacts.sh ics170` (0) verify OK，**qemu md5 `b34ed7f99d8b1d90821f4b819eeb15c9`**（与本机逐件相同）；bundle 落节点干净检出 `85a46f27`；一键证据 **`NODE_RC=0`**（57 s，`--jobs=38`，C2 `264 id / 897 镜像` 全绿，C9 同 269/3/0）
- 门控复跑 (0)：`validate-vectors`（156/156、264 `.S` 载体、gaps 0）、`check-tests-index`（486）、`check-case-ledger`（2033 = vector 1510 + lit 523）、`check-generator-sync`、`check-knowledge-refs`、`check-inst-asm`（897/897）

**C9 不随机器状态漂移**：`git ls-files .cache` = 0（`.cache/` 在 `.gitignore` 第 5 行）；在任务树造**未跟踪** `.cache/refs/<probe>/probe.py`（含 `trampoline.bin`，全盘 grep 能命中该文件）⇒ C9 仍 `surface 269 / 命中 3 / 非登记 0` = **PASS**；删探针并 `rmdir .cache` 还原到开工态后 `surface 269 / 命中 3` 不变
**C9 仍可失败（reviewer 自设，非 I4 复制）**：新建 `tools/testcases/lib/c9_probe_tramp.py`（含 `trampoline.bin`）并**只 `git add`、不 commit** ⇒ 整脚本 **rc=1**、`[FAIL] C9 … gone=1 refs=4 非登记=1`（surface 270）；`git rm --cached` + 删文件还原 ⇒ `surface 269 / refs 3 / 非登记 0`、`git diff --cached` 空、`git status` 干净
**非登记阈值未写死**：临时删掉 `mem_sweep.py` 的 3 处 `SOURCES` ⇒ C9 打印 `refs=0 登记=0 非登记=0` = **PASS**（不再依赖 `refs -eq 3`）；`cp` 还原 md5 `3b732c096085c0ce9171bd2c693e8e06` 与备份一致

**M4 两处非阻断已修**：`Makefile:311` = `Five vector generators` ✓；`inventory.md` 新增「### 覆盖边界（如实）」，明写「拦不住整册删除（实测 `03-wyde-imm` + 同步删 `inst.yaml` 条目 ⇒ `validate-vectors`/`check-tests-index` 均 rc=0）」「**在补上之前，本表不声称已双向校验**」——未越权声称已校验 ✓

**交付物未变**：`git diff efafe50a..85a46f27 -- tests/inst/04-arith-logic-octa tests/inst/01-load-store tests/inst.yaml tests/case-ledger.tsv` = **空**；返工仅 `Makefile`（1 行 help）、`inventory.md`（+14/−4）、任务书（+31）

**约束核验**：未 commit/push（`git status -uall` 起止皆空、`git diff --cached` 空、注入目标 md5 全部与备份一致）；未跑 `install-host`/`check-modules`；节点并行度 38（40−2）；跑完已 `sync-node-repo`（节点回 `master@8a4098ce1`、`dirty=0`）并删任务分支；完成区 9 行 ≤30，第 1 轮审阅记录 27 行原样保留

**未决（非阻断，转后续）**：① 整册删除无人拦 ⇒ 待补「载体册集 / id 集 ↔ 注册集」双向断言（`inventory.md` 已如实登记，建议与 `ISS-441` 同批）；② `mem_sweep.py` `SOURCES` 3 行悬挂（`list` rc=1 响亮失败、无门控引用）待 `ISS-441` 处置；③ `tests/INVENTORY.md`、`docs/Process-09 §7` 文档残留待主会话随批次修。
