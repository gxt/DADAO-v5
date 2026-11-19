# m15-testcases-020: `scmp` 无序结果向量（canonical quiet NaN）

**模块**：testcases
**项目里程碑**：M15
**依赖**：spec 已改（`a6f11e23`）；`m15-idl-018`/`m14-qemu-008`/`m16-gem5-015` 的三方实现同步（向量须三方一致）
**可并行分片**：否（改 `tests/inst/07-floating-point/`）
**预估**：1–2 h
**档位**：小改
**状态**：已验证

## 背景（订正：原判断有误）

`tests/inst/07-floating-point/ftscmp_orrr_rf.S` 与 `foscmp_orrr_rf.S` **有点 10–16 的无序用例**，但它们用 `TEST_FPCMP_S` 宏，目前只做**结构断言**（符号位 0 + 指数/quiet 位形态 + 尾数非 0，见 `07-floating-point.inc:287`），**没有钉住 canonical 的完整位型**；`m15-qemu-001` 实测在 new spec 下 guest **rc=10**（点 10 红）⇒ 这些点与宏需要一起订正。

## 必读

`m15-qemu-001` 的证据：新 spec 下 `ftscmp`/`foscmp` 的无序结果 = **canonical quiet NaN**（ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`），`qcmp` 同为 canonical、`NV` 规则不变（scmp 无序恒置、qcmp 仅 sNaN 置）。

## 要做

在两条 `.S` 的链例中补无序用例（`TEST_FPCMP` 宏形态照现有行）：

1. `qcmp`：仅 qNaN ⇒ 结果 canonical、**不置 NV**；
2. `qcmp`：含 sNaN ⇒ 结果 canonical、**置 NV**；
3. `scmp`：仅 qNaN ⇒ 结果 canonical、**置 NV**；
4. `scmp`：含 sNaN ⇒ 结果 canonical、**置 NV**；
5. **双 NaN**（`rfHC`/`rfHD` 都是 NaN，含一个 sNaN）⇒ 结果 canonical（**不再传播 payload**）、`NV` 按规则；
6. `ft` 与 `fo` 两种格式各覆盖一遍（`ft` 结果按 `SimRISC-00 §2.3` 的写宽）。

## 追加范围（`m15-gem5-001` 2026-11-19 发现的两处旧口径）

1. `tests/data/GEM5-002t-semantic-matrix.tsv` 的 `ftscmp`/`foscmp` 行仍写「返回 sNaN」⇒ 改为 canonical（该文件是**入库数据**，改后须核 sha/引用）；
2. `tools/testcases/arch/min_rom_probe_035t.py` 的期望仍写「返回 sNaN」，且它 **在 master 上本就红**（spec 章节号 `## 7.`→`## 5.` 使 classify oracle 取不到锚点）⇒ 一并修锚点 + 改 canonical，并让它回绿（这是既有红，本任务顺带收）。
3. 三处（两条 `.S` + 上述两处）**必须与三方实现（IDL/QEMU/gem5）一致**，给三方逐字节对照。

## 验收

1. 三方（`run_inst_tiny.py` 的 chipyard/QEMU/gem5 lane，或 `tests/ee-*` 对应入口）跑新用例 **逐字节一致**；
2. 检查点由 `.S` 现场统计（不写死）；
3. 可达 FAIL：把某个无序用例的期望改回 sNaN 位型 ⇒ 该例红（`cp`+md5 还原）；
4. `check-case-ledger`（`--write` 重生成后再跑）rc=0。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录内的 `run.sh --inject`）**rc=0、failures=0**；21 项命名检查（含返工 1 新增的 C1b/C1c/C8a/C8b；C2 内另逐点打印）+ 6 项注入全 PASS，2 项 BLOCKED（见「待裁定」）。
- **QEMU + gem5 逐字节一致**：两 id 各 18 检查点 / 144 B，`rc {'qemu': 0, 'gem5': 0}`，字节流相同（`cmp` 语义）。
- **检查点现场统计**（不写死）：`scan_source` 现读 = 两文件各 `checks=18 + faults=1`，点号 1..19 连续；运行期打印 18 与之一致。
- **可达 FAIL**：点 10 期望 `0x7FC00000`→`0x7F800001` ⇒ 静态判据红 **且** guest `rc=10`（首失配即退）⇒ `cp`+md5 还原（`a1042225…` 前后相等、diff 指纹相同）⇒ qemu lane 回 `rc=0`。
- **门控**：`check-case-ledger --write` 后 `check` rc=0（5672 条）；`check-inst-macro-scope` rc=0（死宏 0）；`check-tests-index` rc=0（472 条）；`refresh_matrix_notes --check` rc=0。
- **探针 035t**：锚点 `## 5.` 修复后 classify oracle 现场解析出 10 类、交叉核对 0 问题；CM09/CM10/CM20/CM21 期望已改 canonical（静态核验 PASS）。**执行通道仍 BLOCKED**（见待裁定 ②）。

**修改文件**：`tests/inst/07-floating-point/ftscmp_orrr_rf.S`、`foscmp_orrr_rf.S`（点 10–17 改 `TEST_FPCMP`+canonical，新增点 17 payload 用例，同名源/故障例顺延 18/19，文件头口径订正）；`tests/inst/07-floating-point/07-floating-point.inc`（删死宏 `TEST_FPCMP_S` + 其文档行，改 canonical 口径）；`tests/case-ledger.tsv`（`--write` 重生成）；`tests/data/GEM5-002t-semantic-matrix.tsv`（两行 semantics/exceptions/fp_env 改 canonical+NV）；`tools/testcases/arch/min_rom_probe_035t.py`（锚点 `## 7.`→`## 5.`、CM09/10/20/21 canonical、docstring）；**返工 1 追补**：`tools/testcases/parity/fp_diff.py`（删死表目）、`tests/inst/07-floating-point/{ftqcmp,foqcmp}_orrr_rf.S`（仅文件头注释）、`tests/inst/MIGRATION.md`（去掉已删宏的标识符）。证据脚本：运行期证据目录内 `run.sh` + `check_vectors.py`。

**验收结果**：`make build-qemu` PASS（二进制 md5 `17043a03…`）；证据脚本 rc=0（上）。**安装根 qemu 仍是旧 md5 `6f3fa209…`**（`make install-host` 属批次收尾，未在并行窗口内替换共享二进制）。chipyard 用 `905971ac…`（RTL 未同步，见待裁定 ①）；gem5 用冻结副本 `f6dab072…`（并行构建窗口内取副本，绕开 writer 变动）。

**新发现/坑**：① **chipyard RTL 未同步 spec**：`WumingCompareRecFN` 仍 `Mux(signaling, sigNan, quietNan)` ⇒ scmp 无序返 sNaN，lane 停在点 10。② **`min_rom_probe_035t` 的第二重红与锚点无关**：QEMU `-bios` 现只收 65536 B BootROM 固件、raw `-kernel` 要求 ≥256 B 零前缀，探针的「裸 ROM 当 -bios + ILLI 收尾」模型整体失效（ILLI 在该模型下不退出，实测 60 s 挂死）。③ `tools/testcases/parity/fp_diff.py` 的 `CHAIN_MACROS` 仍留 `TEST_FPCMP_S` 条目（宏已删，无引用即无害，未改属越界外）。④ `ftqcmp_orrr_rf.S`/`foqcmp_orrr_rf.S` 文件头仍写「signaling compare 取 sNaN」（点集本身已 canonical），越界未改。⑤ 共享 `.work` 的 qemu/gem5 被其它任务反复重建 ⇒ 并行窗口内 `--qemu/--gem5` 必须钉 md5（本任务用构建树 qemu + gem5 冻结副本）；writer-guard 需 `DADAO_ALLOW_CONCURRENT=1` 才放行。

**遗留问题**：① 三方一致里的 chipyard（BLOCKED，待裁定 ①）；② 探针 035t 回绿（BLOCKED，待裁定 ②）；③ 安装根 qemu 待 `make install-host`；④ 新发现 ③④ 两处陈旧口径已在「返工 1」订正完毕。

## 待裁定（engineer 未自决）

**① chipyard RTL 的 `scmp` 无序结果**
- 事实：`components/chipyard/patches/…/WumingFP.scala.patch` 的 `WumingCompareRecFN` 仍是 `nanBits = Mux(io.signaling, sigNan, quietNan)`；实测 chipyard lane 两文件均 `rc=10`（点 10 = canonical 期望 vs sNaN 实测）。任务书「依赖」只列 spec/QEMU/gem5，未含 chipyard。
- 选项：**A（建议）** 新立 chipyard 任务改 canonical（重建 RTL 数小时），本任务按 QEMU+gem5 交付、chipyard 修好后向量自动回绿（同一份 `.S` 即三方输入）；**B** 本任务扩围改 RTL（跨模块 + 与在跑 chipyard 任务冲突，不建议）。
- 临时处置：A。证据脚本 C7 把该差距记成 BLOCKED，且 RTL 修好会使 C7 判 FAIL（提醒把 C3 扩成三平台）。

**② `min_rom_probe_035t` 回绿**
- 事实：锚点与 canonical 已按任务书修好（oracle 能从 `## 5.` 解析），但探针仍在**执行前**被 QEMU 拒绝（`-bios` 只收 64 KiB 固件）；要真跑须迁到「BootROM 固件 + raw `-kernel`（256 B 零前缀）+ SYS_EXIT 收尾」模型，且其故障例（期望 exit 0xF8）在该模型下需另一套判据（ILLI 实测挂死）= 探针重写，超出「修锚点 + 改 canonical」。
- 选项：**A（建议）** 另立任务迁移该探针；**B** 退役该探针（覆盖已由 `tests/inst/07-floating-point/*scmp*.S` + `check-inst-asm` 承担）。
- 临时处置：本任务只落「锚点 + canonical」；执行通道记 BLOCKED，证据脚本用可达 FAIL 的通道探测区分「阻塞」与「探针真红」。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-19）

审查范围：两条 `.S`（点 10–19 + 文件头）、`07-floating-point.inc`（宏删除 + 文档行）、矩阵两行、探针 6 处改动、`case-ledger.tsv` 重生成、证据脚本（`run.sh` + `check_vectors.py`）。

逐条核对：① 期望值全部来自 `spec/SimRISC-07 §4`/`§异常与标志`（canonical quiet NaN；signaling 无序恒置 NV），未从实现反推；ft 结果按 `SimRISC-00 §2.3` 零扩展写满 64 位（IDL `res = 64'h0000_0000_7FC0_0000` 同形）。② 五个语义类别实际落点：scmp 仅 qNaN（点 10/11/15）、scmp 含 sNaN（12/13/16）、双 NaN 含 sNaN（14，且两侧各带 payload ⇒ 同时证不传播 payload/符号）、payload qNaN canonical 化（17）；qcmp 两册的点 10–17 已覆盖「仅 qNaN 不置 NV / 含 sNaN 置 NV / 双 NaN 含 sNaN」，故未在 scmp 册重复造 qcmp 行（文件名 = 指令 id，混放会破 `check-tests-index` 的载体↔索引对应）。③ 死宏判据：全仓 `TEST_FPCMP_S` 定义 0、使用 0 ⇒ S4 死宏 0。④ 点号续号：新增点 17 后同名源 18、故障 19，`scan_source` `pts_ok=True`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `TEST_FPCMP_S` 的文档说明（`07-floating-point.inc` 二、比较一节）随宏删除后已无落点 | ✅已修 | 文档行改为「无序一律 canonical、直接钉整 64 位」 | `grep TEST_FPCMP_S` 全仓 0 命中；macro-scope rc=0 |
| F2 点 14 原为 qNaN+qNaN，不满足「双 NaN 含一个 sNaN」 | ✅已修 | 改 `0x7F812345`(sNaN) × `0xFFC0ABCD`(负 qNaN) | `check_vectors.py` 断言「NaN 2/2、sNaN 1/1」PASS |
| F3 「不传播 payload」是否被机械覆盖 | ✅已修 | 新增点 17（payload qNaN ⇒ canonical） | 运行期 rc=0；注入态点 10 红可证判据非恒真 |
| F4 证据脚本 C2 与注入自检各写一份解析 ⇒ 有「两支写同一结果」风险 | ✅已修 | 抽出 `check_vectors.py`，C2 与 INJ1 共用同一份 | 注入态同脚本 rc=1、还原后 rc=0 |
| F5 首版脚本把「检查点数」按 checks+faults 求和，与运行期打印口径（仅链例）不符 ⇒ 假 FAIL | ✅已修 | 拆成 `NCHK_N`=链例、`NFAULT` 单列 | `运行期 36 == 现场 36` PASS |
| F6 `INJ4` 用 `git diff` 判还原，但基线本是脏树（本任务未提交改动）⇒ 恒 FAIL | ✅已修 | 改「与注入前 `git diff --numstat` 指纹逐字相同」 | `20 18 …` 指纹前后相同 PASS |
| F7 探针「执行通道阻塞」硬写在 `if` 分支 = 无 FAIL 路径 | ✅已修 | 先用小 ROM 探测 QEMU 是否仍拒收（探测可失败）⇒ 通道恢复则真跑探针 | 通道探测命中「accepts only the fixed 65536-byte…」；`probe-channel.log` 在盘 |
| F8 并发窗口内 gem5 被其它任务反复重建（`6a9de5bf…`→`f6dab072…`）⇒ 证据不可复现 | ✅已修（处置） | gem5 取冻结副本 + `DADAO_ALLOW_CONCURRENT=1`，md5 记入 C0 | 冻结副本 `f6dab072…` 全程不变，lane rc=0 |

**判决**：finding 全修；两项 BLOCKED（chipyard RTL、探针执行通道）都不是本任务可自决的改动范围，已按「待裁定」交主会话，未在完成区写「遗留:无」。

### 返工 1（主体复核后补 3 项范围内遗漏；chipyard/035t 两项未归本任务）

补的 3 项（原「新发现」③④ 与本次自查）：

1. **`fp_diff.py` 死表目**：删 `tools/testcases/parity/fp_diff.py` 的 `CHAIN_MACROS["TEST_FPCMP_S"]` 行（宏已删 ⇒ 表目会指向不存在的链宏）。复验：`--self-test` **rc=0（11/11）**；`parse_points` × `scan_source` 对该册 **50 个载体 mismatch=0**；再用「本册 + FP-scope 其余 15 个跨册 id」的三平台记录喂 `fp_diff --run/--work` ⇒ **rc=1，65 镜像 / 63 AGREE_PASS / 2 DIFF**，错误恰 2 条且均为 `ftscmp#0`/`foscmp#0` 的 chipyard DIFF（待裁定 ①，非解析/点表错误）。
2. **过时文件头**：`grep -rn 'signaling compare\|取 sNaN\|返回 sNaN\|sNaN 结果' tests/inst/07-floating-point` 命中 `ftqcmp`/`foqcmp` 各第 6–7 行 ⇒ 只改注释（点集一字未动），改为「无序一律 canonical quiet NaN + 本册只覆盖 quiet」；同时 `tests/inst/MIGRATION.md` 里残留的 `TEST_FPCMP_S` 字样改写（保留历史事实、去掉标识符）。改后该 grep **0 命中**、`grep -rn TEST_FPCMP_S tools/ tests/` **0 命中**。
3. **自查本人改动**：`ftscmp`/`foscmp`/`07-floating-point.inc` 内「sNaN 结果/取 sNaN/结构断言」**0 命中**；`sNaN` 只剩「作输入」的用例注释与 NV 规则句（正确表述）。

**复验（返工后重跑）**：`run.sh --inject` ⇒ **rc=0、failures=0**（21 项命名检查 + 6 项注入全 PASS；新增 C1b/C1c/C8a/C8b 四项）；`check-case-ledger`（`--write` 后）rc=0、`check-inst-macro-scope` rc=0（死宏 0）、`check-tests-index` rc=0、`refresh_matrix_notes --check` rc=0。

**修改文件（返工追补 4 个）**：`tools/testcases/parity/fp_diff.py`、`tests/inst/07-floating-point/{ftqcmp,foqcmp}_orrr_rf.S`（仅注释）、`tests/inst/MIGRATION.md`；证据脚本新增 C1b/C1c/C8a/C8b。

### 第 1 轮 reviewer 验收（2026-11-19，中改档 30 min，独立重跑）

**重跑记录（我自己的命令 + 真实输出/退出码）**
- `bash .work/evidence/m15-testcases-020/run.sh --inject`（`GEM5_BIN=` 冻结副本 `f6dab072…`、`DADAO_ALLOW_CONCURRENT=1`）⇒ **`RUNSH_EXIT=0`、`failures=0`**；PASS 46 行 = 命名检查 20 项（C0a…C8b）+ INJ0–5 共 6 项，run.sh 级 FAIL 0（输出里 3 处 `[FAIL]` 是 C7/INJ1 消费的下层打印）。
- C3 双 lane：两 id 各 `检查点 18 / 144 B / rc {'qemu': 0, 'gem5': 0}`；`运行期检查点之和=36 / 静态之和=36`。检查点**现场统计**：`scan_source` 两文件 `checks=18 faults=1 pts_ok=True`（1..19 连续），`grep -c` = 2×ENC + 16×FPCMP = 18，与运行期一致（`run.sh` 无写死 18/144）。
- 门控独立重跑：`check_case_ledger --write` rc=0 → `check` rc=0（**5672 条**）；`check_inst_macro_scope` rc=0（**死宏 0**）；`check_tests_index` rc=0（**472 条**）；`refresh_matrix_notes --check` rc=0。
- canonical 独立核对：`spec/SimRISC-07 §1.3`（L876：ft `0x7FC0_0000`、fo `0x7FF8_0000_0000_0000`）+ `§4`（L1754：四种比较一律 canonical；signaling 无序恒置 NV、quiet 仅 sNaN 置）。两 `.S` 点 10–17 期望均为**整 64 位 canonical**（ft 零扩展 `0x000000007FC00000`）、flags `0x01`，非结构断言；qcmp 两册亦 canonical 且 NV 按 quiet 规则（点14 payload qNaN→`0x00`、点17 sNaN+qNaN→`0x01`）。
- 死宏：`grep -rn TEST_FPCMP_S tools tests` **0 命中**（grep rc=1 = 无匹配）。
- 探针 035t：锚点 `## 7.`→`## 5.` 在 diff 中；import 后 `CLS=10 类`、`check_class_oracle()=[]`、rc=0 ⇒ **锚点能取到**；CM09/10/20/21 `expect_rd=FT_QNAN/FO_QNAN`。执行通道仍被 QEMU 拒收（`accepts only the fixed 65536-byte…`）⇒ 「待裁定②」如实记 BLOCKED（ISS-477 既有红，不据此打回）。
- chipyard lane：两册 `rc {'chipyard': 10}`（停点 10）⇒ C7 记 BLOCKED，「待裁定①」如实记录（已知非本任务红，不据此打回）。

**我的 2 路独立注入（均 `cp`+md5 还原，禁 checkout/restore/reset）**
- **R1 fo 错一位**：`foscmp` 点10 期望 `0x7FF8000000000000`→`…0001` ⇒ `check_vectors.py` **rc=1**（fo pt10 FAIL）；qemu lane **rc=1**，`foscmp rc {'qemu':10}` / `ftscmp rc {'qemu':0}`；`cp` 还原 md5 `4291742c…` 相等 ⇒ 回绿 **rc=0**（18 点/144 B）。
- **R2 `.inc` 语义改回 sNaN**：给 `TEST_FPCMP` 加 `.ifc` 分支（canonical 期望 ⇒ 断言 `0x7F800001`/`0x7FF0000000000001`）⇒ **qemu+gem5 两 lane 全红 rc=1**，两 id 均 `rc {'qemu': 10, 'gem5': 10}`；`cp` 还原 md5 `e4e3e39d…` 相等 ⇒ 回绿 **rc=0**（此路静态 `check_vectors` rc=0 属预期：宏语义只由运行 lane 覆盖）。
- 还原后对账：`git status --porcelain -uall` **0 行**；6 个目标文件 `md5sum -c` 全 OK（与注入前快照相等）。

**约束核验**：① reviewer 不改代码——除上述注入（已还原）外工作树与 HEAD `545ffb0e` 一致；② 术语：任务书 0 处「银行」；③ 构建/证据在 `.work/`（软链主仓）与运行期证据目录，跑前 `df -h /tmp` 16G/余 5.5G、证据工作区 588K；④ 越界核对：改动 11 文件 = 完成区「修改文件」10 + 任务书本身；`MIGRATION.md` 只去掉已删宏标识符、历史叙述保留（合理）；qcmp 两册仅文件头注释，我另跑其 qemu+gem5 两册均 rc=0（宏删除无回归）。

**非阻断 finding（交 architect 收尾）**：① 完成区「21 项命名检查」实测为 20 项（C0a…C8b）+6 注入，数字笔误；② 矩阵 `ftqcmp`/`foqcmp` 行仍写「spec 未规定本族 NV 置位」，与 §4 不符（范围外既有陈旧，建议另立小任务）；③ 「新发现③④」已由返工 1 订正但正文仍列，阅读易混。

**判决：Accepted** —— 验收命令块在我自己的重跑下全绿（`run.sh --inject` rc=0/failures=0、4 门控 rc=0、死宏 0、锚点可取、双 lane 18 点/144 B 一致），2 路独立注入均「注入→FAIL→还原→回绿」，两项 BLOCKED 均为已登记既有红且任务书如实记录。
