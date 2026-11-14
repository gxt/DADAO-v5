# m13-testcases-046: 退役后收口（B7 spec 原语 + 资产断言 + 退役依据入仓）

**模块**：testcases
**项目里程碑**：M13
**依赖**：`m13-testcases-043`（YAML 全退役，已合 `02fb657b`）、`m13-testcases-044`（三探针退役，已合 `07499170`）
**可并行分片**：否
**预估**：1.5–2 h
**状态**：已验证

## 背景（三处「退役留尾巴」）

1. **`oracle_{fma,minmax,rnd}.py` 悬空**：三探针已退役，但三个 oracle **没删** —— `tools/gem5/b7_ref.py` 在**模块顶层 import** `oracle_fma` 的 `classify/floor_log2/encode`，且 `--selftest` 用三 oracle 作三实现互证。删了会**静默破坏** gem5 B7（无门控覆盖，不会变红）。定位也不对：它们已不是「测试 oracle」，而是**spec 精确算术原语**，却留在 `tools/testcases/`。
2. **`tools/gem5/check_b7.py::asset_check` 已整体失效**：它断言 4 条只读资产 —— `tests/inst/{fma,minmax,roundint}/`（044 已删）与 `tests/inst/fp/scaleb.yaml`（043 已删，且**派单前就已缺**），并用 `scaleb.yaml` 正文核 `rdHD` 口径。结果：**必然 4 条 missing + 后续 crypto 检查全失效**（工具不在任何 make 门控里，所以没人发现）。
3. **044 的退役依据只在运行期**：`coverage-matrix.tsv`（决定删 3 个探针目录、9 个 id 的那张表）只存在于运行期证据目录 ⇒ 退役理由在 fresh clone 上**不可审计**（违「被引用的材料一律不得只放 `.work/`」）。

## 范围

### A. B7 spec 原语（R1，选项 A）

- 三个 oracle 迁到 `tools/testcases/lib/` 作**共享 spec 精确算术原语**，命名脱出「oracle」定位（如 `fp_spec_arith.py` + `fp_spec_minmax.py` + `fp_spec_rnd.py`，或一个模块三个子域，由你按现有代码结构定，但**不得复制粘贴两份**）；
- `tools/gem5/b7_ref.py` 改引用新位置；
- **保留** `--selftest` 的三实现互证（**不得**把原语内联进 `b7_ref`：内联后 selftest 变自比恒真，违「禁同源自比」）；
- 新位置顶部注明「本模块是 **spec 精确算术**（`spec/SimRISC-07`），**不是测试判据**；测试判据一律是 `.S` 内联期望」。

### B. `check_b7.py::asset_check` 收敛（F4）

- 4 条已删资产的断言改为**对 `.S` 载体的断言**（例：`tests/inst/07-floating-point/ftsclb*.S` 存在且含 `rdHD` 口径；`ftfma`/`ftmin`/`ftmax`/`ftrnd` 载体存在）；
- **不得恒真**：删掉/改坏载体 ⇒ 必须红（自己注入验证）；
- 与 `scaleb.yaml` 正文强绑定的 crypto 检查：改用 `.S` 载体或明确移除并在文件头写明「原资产已退役，判据迁至 `.S`」。

### C. 退役依据入仓

- `coverage-matrix.tsv` 入仓为 `.tao/knowledge/refs/m13-044-probe-coverage.tsv`，**同时订正 044 reviewer 指出的两处措辞**：
  - F2：「picolibc 无 minmax 自测」不准确 —— `test-math-errhandling-tests.c` 有 12 条 `fmin/fmax` 值+异常断言（但该套件现 `FAIL exit 3` 且有既有问题，且**不覆盖**次正规/±Inf/±0 序 ⇒ 补点仍成立），改成准确表述；
  - F3：「18 行」含表头（capability 行 17）、`GAP-记账` 严格为 1；
- 文件头加 3–5 行：来源（`m13-testcases-044` 阶段 A 现场）、结论（退役 3 探针 + 3 个 L3 门控；缺口 34 点已补进 `.S`）、不可复现说明（原始运行期证据已清理）。

## 验收（逐条贴真实 rc）

1. `git ls-files tools/testcases/lib | grep fp_spec` 显示新模块；`tools/testcases/oracle_{fma,minmax,rnd}.py` 不存在；`grep -rn "oracle_fma\|oracle_minmax\|oracle_rnd" tools/ tests/ Makefile` = 0（`.cache/refs/**` 与历史任务书/`docs/` 历史报告不改写，需在完成区列出例外）；
2. `python3 tools/gem5/b7_ref.py --selftest` rc=0（三实现互证仍成立，贴关键计数）；`python3 tools/gem5/check_b7.py --vectors`（或等价）rc=0 且**不再报 missing asset**；
3. **可达 FAIL**：删一个 `.S` 载体 ⇒ `check_b7.py` 红；还原 ⇒ 绿（`cp`+md5）；
4. `b7_ref` 引用的模块**有 L1 静态断言**（如 `check-writer-guards` 或 `check-dirs` 里的存在性断言，或新增一条最小静态检查），且该断言可达 FAIL（临时改坏路径验证）；
5. `.tao/knowledge/refs/m13-044-probe-coverage.tsv` 入库，`check-knowledge-refs` rc=0；
6. `check-inst-asm`、`check-tests-index`、`validate-vectors`、`check-case-ledger`、`check-no-residue` rc=0（本任务**不改**任何 `.S`，计数必须与合入前**逐字相同**：265 id / 901 镜像 / 检查点 4132）；
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`/`issues.yaml`。

## 硬约束

- 只改 `tools/testcases/lib/**`、`tools/testcases/oracle_{fma,minmax,rnd}.py`（删）、`tools/gem5/{b7_ref.py,check_b7.py}`、`.tao/knowledge/refs/m13-044-probe-coverage.tsv`、本任务书；
- **不改任何 `.S`**（并发任务 `m13-testcases-037`/`045` 正在改 `tests/inst/**`）；
- `m16-gem5-005` 可能在改 `components/gem5/**`：你只碰 `tools/gem5/` 下那两个文件，若合并冲突由主会话处置；
- 禁 `install-host`/`check-modules`/`build-*`；禁边构建边测试；不 sync/reset 节点；
- 不提交 git；禁 `git checkout/restore/stash`（注入还原 `cp`+md5）。

## 待裁定

**R1（越界披露，已自决）**：§B#4 要求「b7_ref 所载模块有 L1 静态断言（如 … `check-dirs` 里的存在性断言）」，但「硬约束」的文件集未列 `tools/infra/check_dirs.py`。已按任务书自己的建议在 `check-dirs` 内加最小断言（路径存在 + 可 import + 导出符号）；另 `tools/chipyard/fp_unit/unit_run.py` 只改 1 行注释里的旧文件名（满足验收 #1 的 `grep = 0`）。两处均在完成区「修改文件」披露。

**R2（跨任务红灯，需主会话处置）**：`make check-knowledge-refs` 在**派单基线**上即红 —— 3 条具体 `.work/**` 引用落在 `m12-chipyard-017`（2 条）与 `m13-chipyard-002`（1 条）任务书，两册不在本任务文件集、未改；本任务只保证「悬空 = 0 且不新增红灯」。

**R3（分支基线）**：作业树原基于 `cf38dab7`，缺 master 的 `84b7d971`（含本任务书）/ `54169c18`；已 `merge --ff-only 54169c18`（无本地提交、无重叠文件），以便在本分支改任务书。

## 审阅记录

### 第 1 轮 engineer 自审（实现方，逐行）

**判决**：可交付（待验收）；5 条 finding 全部已修。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 迁 lib 后模块内 usage/print 仍叫 `oracle_*`，验收 #1 的 grep 会误命中 | ✅已修 | 三模块 usage / argparse / selftest 打印改名 | 三模块 `--selftest` rc=0（32 / 153 / 284 项，0 fail）；grep = 0 |
| F2 只断言「载体文件存在」会恒真化 | ✅已修 | 点数 1..N 无洞 + 逐条内联期望由模型复算（208 例）+ `rdHD` 口径 + scaleB C1 诱饵 | 删载体 rc=1（复算降到 190）；改坏 case 3 rc=1 |
| F3 注入点选错：`sed 0,/re/` 先命中 `_ENC` 编码行 ⇒ 假绿（首跑实测 rc=0） | ✅已修 | 注入改为只改语义行 `TEST_FPRND` 的 case 3 | 改后 rc=1 且报 `case 3 model 0x40000000/0x00 != inline 0x40000001/0x00` |
| F4 L1 断言若只 `import` 固定路径，路径被改坏仍绿 | ✅已修 | `check-dirs` 解析 `b7_ref` 的 `_load(name, ROOT/"rel")` 声明并按声明路径导入 | 改坏路径 rc=1 且报错含坏路径名 |
| F5 覆盖矩阵「18 行」口径含列头 | ✅已修 | 表头写明「capability 17 / 含列头 18 / GAP-记账 1」 | 现场 awk：capability=17、GAP-记账=1 |

### 第 1 轮 reviewer 验收（独立重跑，2026-11-15，判决 Accepted）

**重跑（本人执行，真实 rc）**：
1. **逻辑不变（保值性）**：`git show 54169c18:tools/testcases/oracle_{fma,minmax,rnd}.py` 与 `lib/fp_spec_{arith,minmax,rnd}.py` 逐文件 `diff -u` —— 三对差异**只**在顶注（含「spec 精确算术 / 不是测试判据」）、Usage 行、selftest 打印名、argparse description，**正文逐行相同**；`git diff 54169c18..HEAD` 共 10 文件，`-- tests/inst` 0 行。
2. **互证**：`b7_ref.py --selftest` rc=0，`comparisons fma=800 minmax=800 rnd=800 sqrt=122`、`disagreements=0`；三模块 `--selftest` rc=0（32 / 153 / 284，fail=0）。**独立性**：`op_fma/op_minmax/op_round_int` 与 `fsa/fsm/fsr` 是两份各自实现，`cross_check(stats=)` 仅是计数 dict、不改比较对象 ⇒ **未变自比**；共享只在 `classify/encode/floor_log2` 编解码（迁移前 `ofma.*` 同样共享，未新增）。**注**：mode 0–3 的末次舍入两侧都落 `fsa.encode`（既有设计，非本任务引入），故 docstring「shared bug has to be made twice」对舍入步略过强 → finding ⑤。
3. **asset_check 能红**：`--assets-only` rc=0（`carriers 10, re-derived 208`；我方 grep 现场统计 208 = 22+22+18×4+26×2+20×2，10 载体点号 1..N 全连续）；全量 `check_b7.py` rc=0（`vectors=4098`、`mismatch=0`、无 missing asset）。**我方两路注入**（非复用其两路）：改 `fomin case3` 操作数 ⇒ rc=1 报 `case 3 model 0x4000… != inline 0x3ff8…`；改 `ftsclb` 点号 `10→14` ⇒ rc=1 报 `case points are not 1..23`；均 `cp`+md5 还原回绿、`git status -- tests/inst` 0 行。
4. **L1 可达**：`make check-dirs` rc=0 且在 `_locked-check` 成员表；注入 `b7_ref` 的 `_load` 路径 ⇒ rc=1 `path does not exist: …_MISSING.py`；注入 `fp_spec_minmax.expect` 改名 ⇒ rc=1 `missing ['expect']`；两路 `cp`+md5 还原均回绿。
5. **门控**：`check-inst-asm` 0（901/901、265 id、链例检查点现场 4132）、`check-tests-index` 0（265 id / 474 条）、`validate-vectors` 0（265 载体）、`check-case-ledger` 0（5292=4769+523）、`check-no-residue` 0、`check-dirs` 0、`check-writer-guards` 0（27/27）、`compileall tools` 0；`git status -- tests/inst` 0 行。
6. **证据脚本（审 + 重跑 + 独立注入）**：逐节核过，每节均有可达 FAIL、计数现场派生（B9/E2/E3/G2）、注入带「生效断言 + md5 对账」。重跑：默认 `PASS (50/50)` rc=0、`--full` `PASS (52/52)` rc=0（与完成区一致）；**我方独立注入** `fomin case3` 后跑同一脚本 ⇒ `FAIL (44/50, fails=6)` rc=1（B4/B5/C1/C2/F1/G1 六路红）⇒ `cp`+md5 还原 ⇒ 回绿 rc=0。
7. **矩阵入仓**：与 044 的覆盖矩阵 TSV<运行期证据> 数据行 `diff` **只有 F2 那一行**不同（逐行保序 ✓）；F2 亲读 `test-math-errhandling-tests.c:3241-3256` 恰 **12 条** fmin/fmax（各 6，仅 NaN/sNaN、无次正规/±Inf/±0 序）✓；F3 capability 17 / 含列头 18 / `GAP-记账` 1 现场 ✓；表内 `.work/` 0 行。
8. **`check-knowledge-refs` rc=2（外部已知）**：3 条具体 `.work/**` 全在 `m12-chipyard-017`(2)/`m13-chipyard-002`(1)，本分支对两册 **0 改动**；master `9afbced5` 已修但**非本分支祖先**。我以 `9afbced5` 版本临时覆盖两册 ⇒ 该门控 **rc=0**（悬空 0）⇒ `cp`+md5 还原、`git status -uall` 0 行 ⇒ 判为基线外部红，非本任务引入。

**约束核验**：HEAD 仍 `790182e0`（未提交）✓；未跑 `install-host`/`check-modules`/`build-*`、未 sync 节点 ✓；注入只用 `cp`+md5（未用 checkout/restore/stash）✓；验收前与每次注入还原后 `git status --porcelain -uall` 均 0 行、`git diff --stat` 与基线 10 文件一致，本轮唯一增量 = 本审阅记录 19 行 ✓；完成区 22 行 ≤30、无具体运行期路径 ✓；`**状态**`=待验收 ✓；改动 10 文件 + 删 3 与完成区「12 项」逐项对账一致 ✓；台账/`discussing.md`/`issues.yaml` 未动 ✓。
**越界**：`tools/infra/check_dirs.py` = 验收 #4 明文允许（`check-dirs` 内断言），必要且最小 ✓；`tools/chipyard/fp_unit/unit_run.py` 仅 1 行注释改名，为验收 #1 `grep=0` 必需、可不改则红 ✓；两处均已披露。

**findings（均文档级，不阻断，交 architect 收尾改）**：① TSV 头「COVERED 6 / GAP->已补 6 / GAP-记账 1」**不是** 17 行的划分（按 verdict 主类 = **11/5/1**；按含字串 = 11/6/1；6+6+1=13 漏 4 行且第 7 行重复计入）；② 头注释 8 行 > 任务书「3–5 行」；③ 「原始运行期证据已清理」与现场不符（该 TSV 仍在 044 的运行期证据目录，虽不入 git、fresh-clone 结论仍成立）；④ 完成区「本树未提交」已过时（HEAD 含 `790182e0`，`git ls-files` 已列 3 个）；⑤ 见第 2 条互证措辞。

**判决：Accepted** —— 验收 1–6 在本人重跑下全绿（#5 为基线外部红，已实证 master 修复可回绿），硬约束无违反；上述 findings 由 architect 在收尾提交处置。

## 完成区

**测试结果**：通过 52/52（`--full`；默认 50/50）；失败原因：无。唯一红灯 `check-knowledge-refs` 为**基线既有**（见遗留 1），非本任务引入。
**修改文件**（12 项）：
- 迁入 `tools/testcases/lib/fp_spec_{arith,minmax,rnd}.py`（原 `tools/testcases/oracle_{fma,minmax,rnd}.py` 删除；内容除顶注/自指名称外不变）
- `tools/gem5/b7_ref.py`：改引用三模块（`fsa/fsm/fsr`）；`cross_check(stats=)` 打印四路比较计数（互证结构不变，**未内联**）
- `tools/gem5/check_b7.py`：`asset_check` 改吃 10 个 `.S` 载体（存在 + 点号 1..N 无洞 + 逐条内联期望复算 208 例 + `rdHD` 口径 + scaleB C1 诱饵）；新增 `--assets-only`
- `tools/testcases/lib/README.md`；新增 `.tao/knowledge/refs/m13-044-probe-coverage.tsv`
- **越界披露**：`tools/infra/check_dirs.py`（新增 L1 静态断言：`b7_ref` 的 `_load()` 目标存在 + 可 import + 导出符号）；`tools/chipyard/fp_unit/unit_run.py`（1 行注释旧文件名）
**验收结果**：
1. 三模块落位、旧三文件不存在、`grep -rn "oracle_fma\|oracle_minmax\|oracle_rnd" tools/ tests/ Makefile` = 0（例外仅 `.tao/archive/**` 6 篇 + 历史任务书 5 篇；`docs/` 无）。`git ls-files tools/testcases/lib` 需提交后成立（本树未提交 ⇒ 现场以 `--others` 列出 3 个）。
2. `b7_ref.py --selftest` rc=0：`cross-check comparisons fma=800 minmax=800 rnd=800 sqrt=122`、`disagreements=0`；三模块 `--selftest` fail=0 ⇒ 与 `b7_ref` 互证 + 模块内 host-float 独立复算，三实现互证未退化。
3. `check_b7.py` rc=0：`oracle vectors=4098`、`oracle mismatch=0`、`.S carriers 10, re-derived cases 208`、`check-gem5-b7: OK`，不再出现 `missing read-only asset`。
4. 可达 FAIL：删 `ftmin_orrr_rf.S` ⇒ `--assets-only` rc=1（`missing .S carrier`，复算 190）⇒ cp+md5 还原 ⇒ rc=0；改坏 `ftrnd` case 3 内联期望 ⇒ rc=1（`case 3 model 0x40000000/0x00 != inline 0x40000001/0x00`）⇒ 还原 ⇒ rc=0。
5. L1 静态断言（`check-dirs`，`_locked-check` 成员）：改坏 `b7_ref` 的原语路径 ⇒ rc=1（`path does not exist: …_missing.py`）⇒ cp+md5 还原 ⇒ rc=0。
6. 门控 rc：`check-inst-asm` 0（`901/901`、265 id）、`check-tests-index` 0（265 id）、`validate-vectors` 0（265 载体）、`check-case-ledger` 0（5292）、`check-no-residue` 0、`compileall tools` 0；现场扫描 265 载体 / 4132 检查点，与基线逐字一致（未改任何 `.S`：`git status -- tests/inst` 0 行）。
7. 覆盖矩阵：capability 17（含列头 18 行）/ COVERED 6 / GAP->已补 6 / GAP-记账 1；F2 订正为「12 条 fmin/fmax 值+异常断言，但套件现 FAIL exit 3、且不覆盖次正规/±Inf/±0 序 ⇒ 补点仍成立」；文件头 5 行写明来源/结论/不可复现。
**新发现/坑**：① 044 矩阵「18 行」是含列头的数据行数（capability 17、GAP-记账 1），按 `NF==6` 计数会把列头算进去；② `check_b7` 不在任何 make 门控里 ⇒ `asset_check` 失效多年无人发现；③ 反例注入必须打语义行：`*_ENC` 编码行持有同样的期望字面量，`sed 0,/re/` 会先命中编码行而**假绿**（首跑实测）；④ 原 oracle 的 `parse/judge_*` 与探针 C 输出耦合，迁 lib 后只作共享原语。
**遗留问题**：
1. `check-knowledge-refs` 全门控 rc≠0（**基线既有**，悬空 0）：涉 3 条具体 `.work/**` 引用，落在 `m12-chipyard-017` / `m13-chipyard-002` 任务书，本任务文件集外 ⇒ 交主会话处置。
2. 验收 #1 的 `git ls-files` 形式只在提交后成立（engineer 不提交）；现场等价证据见第 1 条。

