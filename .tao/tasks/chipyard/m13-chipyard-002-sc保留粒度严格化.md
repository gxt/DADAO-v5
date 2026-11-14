# m13-chipyard-002: `sc` 保留判据去掉「整字值比较」（严格按 spec 的精确地址+宽度）

**模块**：chipyard
**项目里程碑**：M13
**依赖**：无（与 `m13-qemu-014` 并行无冲突，但**共用 `m13-testcases-037`** 的三平台复验）
**可并行分片**：否（RTL 单写者）
**预估**：2–3 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「ISS-435：严格按spec来」

- 落地含义：保留标记粒度 = **精确地址 + 访问宽度**（`spec/SimRISC-12 §1`「保留机制」段）；`sc` 的成败**只能**由「保留标记是否仍持有 + 键是否匹配」决定，**不得**因为「同一 8 字节字的值变了」而失败。

## 现状（现场）

- `generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala`：
  - 保留键**已经**是精确地址 + 宽度（`resvValid`/`resvAddr`/`resvWidth`，L467-472 的 `scHit` 用 `resvAddr === lrscAddr(47,0)` 与宽度比较）；
  - 但**额外**保存了 `resvWord`（`lr` 读到的整字），`sc` 时若该字值变化就失败（注释自述「legal spurious failure」）。
- 实测（`m13-testcases-028` 的 `probe_gran.S`，同 ELF）：**同 hart 改同字另一字节 ⇒ chipyard 的 `sc` 失败**（`rc=2`），gem5 通过、QEMU 另有一处不一致。
- 严格口径下，「同字另一字节被写」**不属于** spec 列出的清除事件 ⇒ `sc` 必须成功；把它做成确定性失败等于把粒度偷偷放大到整字值。

## 目标

1. **去掉 `sc` 的整字值比较**：`sc` 的成功条件 = `resvValid && resvAddr === 精确地址 && resvWidth === 访问宽度`；删除 `resvWord` 寄存器与其比较路径（若保留用于诊断，必须在 `sc` 判据中**不参与**，并注释说明）。
2. **清除事件严格按 spec**：另一条 `lr`、异常/中断进入、`sc` 自身（成败都清）。**普通 store 不清除**（同 hart 写同地址也不清）。
3. 注释同步改述：删掉「matches QEMU's word-granularity reservation」与「changed word is a legal spurious failure」的旧口径，改为「按 spec 精确地址+宽度；多 hart 同址 store 的清除依赖一致性事件，当前单 hart 无载体（GAP）」。

## 验收（逐条贴真实输出）

1. **改前正证**：改前 RTL 构建的 harness 跑 `probe_gran.S` 的「同字另一字节」点 ⇒ `sc` 失败（贴 rc/输出 + harness md5）。
2. **改后**：同点 ⇒ `sc` 成功；「同地址同宽度写后再 `sc`」按 strict 口径仍成功（同 hart 写不清除）——若你认为该点应失败，停下写「待裁定」。
3. **既有 `lr`/`sc` 用例不回归**：`tests/inst/12-misc/` 的 24 个原子 id 三平台逐字节；`sc` 成功/失败的既有断言点全绿。
4. `check-patch-tree` chipyard 段 0 问题、`--source-state` chipyard OK、changelog M13 一条、补丁重导出。
5. ≥1 路可达 FAIL 注入（`cp`+md5 还原）：把 `scHit` 改回带 `resvWord` 比较 ⇒ 对应点红。
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`；不改台账/`discussing.md`。

## GAP（写进完成区，不伪造）

- **多 hart 对同一精确地址+宽度 store 的清除**：`WumingTinyConfig` 单 hart，无观测载体；RTL 侧仅保证键与清除时机，不造用例。
- 值无关的「同值写也应清除」同理不可测。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host` / `check-modules`**；chipyard 组件**单写者** —— 开工前 `pgrep -af "build-chipyard|make verilog|verilator"` 并确认主会话已放行（`m12-chipyard-016` 可能仍在跑）。
3. 构建纪律：改 RTL 后必须删 `.classpath_cache/chipyard.jar` 与 `generated-src/<cfg>` 再 `make verilog`（否则静默沿用旧 RTL）。
4. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
5. 只改 `generators/dadao-wuming/src/main/scala/wuming/**` + 对应补丁 + `components/chipyard/changelog.md`；**不改** `spec/`、`contracts/`、`tests/**`。
6. 大文件落 `/tmp/opencode/m13-chipyard-002/` 并测完即删。

## 待裁定

- **共享 chipyard 源树的跨任务状态**：执行时共享组件源树（单写者）已提交 `m12-chipyard-016` 的 RTL 状态（`WumingSemi.cc/.v`、`WumingCore`、`WumingDecoder`、`WumingSemi`：semihosting 服务号取 rd16、guest 内存读写、cycle 字段等），而该任务的补丁导出仍是其 worktree 内未提交改动。任务书要求「`make_patch.py chipyard` 重导出 + chipyard 段 0 问题」⇒ 本任务做了**整体重导出**，于是本分支 5 份补丁中，除 `WumingCore.scala.patch`（本任务改动）外另有 4 份携带上述 `016` 状态。
  - 影响：`016` 合入时那 4 份两支内容相同（自动合并），`WumingCore.scala.patch` 冲突（本任务为超集，取本分支）；`016` 的 `--source-state` 仍 OK（HEAD=base+1、clean）。
  - 选项：(a) 接受整体导出（当前状态，`check-patch-tree` chipyard 0 问题）；(b) 只保留 `WumingCore.scala.patch`、另 4 份回退 master 内容 ⇒ `check-patch-tree` 回到 10 个**既有**问题（`016` 未导出所致），待其合入后再回零。
  - 建议：(a)，且**先合 `016`**（或合入后立即用源树再重导出一次）。请主会话裁定。

## 审阅记录

### 第 1 轮 engineer 自审

范围：`WumingCore.scala` 改动逐行 + 证据脚本六模式 + 探针（9 点）。判决：**Accepted**（findings 全修/全判）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `sc` 命中后的预写拍读是否应整段删除 | ❌不修（保留） | 值不参与判据，注释写明只作读写能力预检 | 删掉会改 CFXMEM 判据与拍数，超本任务口径；探针 P1/P3 已证值无关 |
| F2 注入只注「比较」漏注写回 ⇒ 读到旧 rdHB，注入假绿 | ✅已修 | 注入 8 处：`resvWord` 声明/赋值 + `scCheckFail` 声明/`w0En`/`w0Idx`/`w0Bank`/`w0Data` + 分支守卫 | 注入后 P1/P2/P3 实测 1（3 红点），还原后全绿 |
| F3 探针 P9 用 `ENTRY+(label-_start)` 作 hmon 返回槽 | ✅已修 | 改 `.text` 内 `.org 0x1D00` 固定偏移桩，返回槽写绝对常量 | P9 实测 1（改前/改后一致），sim rc=0 |
| F4 初版落点方案（`.testdata`/`.faultpad`）被 lds 尺寸/落点 ASSERT 拒绝 | ✅已修 | 改用 `.text` 固定偏移（`.text` ≤0x1E00 断言内） | link rc=0 |
| F5 脚本 `local d=$TMP/probe-$tag` 同句引用未定义变量 | ✅已修 | 拆成两条 `local` | 六模式 rc=0 |
| F6 gates 在 0 问题时误报 `missing` | ✅已修 | 改为现场统计 chipyard 段 problem 行数 | 0 问题判绿 |
| F7 注入的预期红计入总账 ⇒ EXIT=1 | ✅已修 | 注入探针跑在子 shell，只判 rc | `== inject: PASS=14 FAIL=0` |
| F8 删 `scCheckFail` 后 `1.U` 注释残留 "word changed" | ✅已修 | 注释改为 `// reservation miss` | `grep -E 'resvWord\|spurious\|granularity'` 空 |
| F9 旧口径注释（QEMU word-granularity / legal spurious failure / ADR-0034 D6） | ✅已修 | 三处注释改述为「键=精确地址+宽度；多 hart 依赖一致性事件（GAP）」 | 同上 grep 空 |

### 第 1 轮 reviewer 验收（2026-11-14，独立重跑；命令均在任务 worktree，脚本 `.work/evidence/m13-chipyard-002/run.sh`）

**重跑记录（reviewer 自己的真实输出 / 退出码）**
- `run.sh pre` → **EXIT=0**；pre sim md5 `ac35dffbc90cef736e5e0788cecb51d2`；P1/P2/P3 actual=1（spec 0），P4–P9=1,0,1,1,1 与 spec 同。
- `run.sh probe` → **EXIT=0**；sim md5 `4e2228ad7f18709f539d50124b6cda87`；P1..P9 = 0,0,0,1,0,1,1,1,1 全 match。
- `run.sh gates` → **EXIT=0**；`chipyard: 21 patch(es)` / 0 problem / rc=0（另直跑 `check_patch_tree.py` rc=0、全仓 0 problem）；`--source-state: chipyard: OK HEAD=bbb93b6ed711 count=1 clean=True`；`check-component-changelog: PASS`。
- `run.sh suite` → **EXIT=0**；`run_asm_suite: 66/66 镜像通过（24 个 id；链例 24，故障例 42）`；qemu `725c5da7…` / gem5 `6e436d1b…` / chipyard `4e2228ad…`，与完成区逐字一致。
- `run.sh checkinst` → **EXIT=0**；`run_asm_suite: 897/897 镜像通过（264 个 id）`、`check-inst-asm: PASS`。
- `run.sh inject`（engineer 方案，reviewer 重跑）→ **EXIT=0、PASS=14 FAIL=0**；inj sim `eea38ba6…` 下 P1/P2/P3 红（3 点）、`inject.restore_md5` 期望=实际 `3de213b5…`、还原后 sim 回 `4e2228ad…` 全绿。

**独立注入（reviewer 自设计，非复用 engineer 方案）**：把源文件 `WumingCore.scala:1333` 的 `when(memAux === 3.U)` 改成 `when(memStore)`（＝任何 store 完成都清保留，违反 spec「普通 store 不清除」）；`cp`+md5 `3de213b5…`→`b8f4fe21…`，`run.sh build`（JOBS=32，1m50s）→ sim `6768fac8…`，`run.sh probe` **EXIT=1**、`[FAIL] P1/P2/P3 actual=1`、P4–P9 不变；`cp` 还原 md5 回 `3de213b5…`（MD5_MATCH=YES、chipyard 源树 clean）→ 重建 1m52s → sim 回 `4e2228ad…`、`probe` **EXIT=0** 全绿。

**判据核对**
- `grep -E 'resvWord|scCheckFail|spurious|granularity|word-changed|ADR-0034'` 源文件 + 5 份补丁 → **全空**；源文件 md5 `3de213b5…` = 由 `WumingCore.scala.patch` 重建内容 md5（逐字节相等）。
- `scHit = resvValid && (resvAddr === lrscAddr(47,0)) && (resvWidth === d.memWidth)` 三键合取，值不参与 ✓。
- 清除事件未动：`enterHmon` 清、`scFailNow` 分支清、sc 存储完成 `when(memAux===3.U)` 清、`lr` 置位；普通 store `memAux=0` 不清 ✓。
- 期望值由我按 `spec/SimRISC-12 §1`（粒度＝精确地址+访问宽度；清除＝另一 hart 同址同宽 store／另一条 lr／异常进入；`sc` 成败都清）独立推导，与 `probe_expect.tsv`／`probe_pre.tsv` 两表**逐点一致**。

**补丁超集判定**：`WumingSemi.cc/.v`、`WumingDecoder`、`WumingSemi` 4 份与 `m12-chipyard-016` 工作树 **md5 逐字节相同**（`f2f19f2b`／`5dd1d370`／`44c1f38c`／`fa2d1d1f`）；`WumingCore.scala.patch` 两支 diff **只有本任务改动**（resvWord/scCheckFail 删除＋注释改述）⇒ **无 016 之外的额外改动**；`merge-base..HEAD` 共 **7 文件**（任务书＋changelog＋5 补丁），无越界。
- 附带影响（交 architect）：共享 chipyard 源树 patch-series commit 已于 21:35:39 amend 成「016+002」⇒ 在 `m12-chipyard-016` 工作树直跑 `check_patch_tree.py` 现 **rc=1、chipyard 段 2 个问题**（`WumingCore.scala` 断言⑨/⑥）；同日志中 qemu 12／gem5 16 为既有问题，与本任务无关。

**合并顺序建议：先合 `m12-chipyard-016`，再合本任务。**
- 先 016：4 份自动无冲突；`WumingCore` 三方冲突时取本分支（＝016 内容＋本任务改动）；016 的非补丁文件（`picolibc-tiny.ld`、`tools/testcases/*`）归属正确、不随本任务搭车。
- 若先 002：016 仍「待验收」，其 semihosting RTL（rd16 服务号、cycle 字段）搭本任务入 master；且 016 合并时 `WumingCore` 反向冲突，取错即回退本任务改动。
- 前置动作：016 收尾前用共享源树**重导出一次**（否则其工作树 chipyard 段 2 问题挡其门控）；重导出后两支补丁完全相同，先合谁都不冲突。本任务合并前复核 4 份 md5 ＋ `diff WumingCore` 仍成立。

**约束核验**：独立 worktree/分支 ✓；reviewer **未提交 git**（只写本审阅记录）✓；未跑 `install-host`／`check-modules` ✓；重编 `JOBS=32` ✓；未 sync/reset 节点仓库（三平台全本地跑）✓；改动限 `components/chipyard/**`＋任务书 ✓；完成区 22 行 ≤30 ✓；未改 `discussing.md`／台账 ✓；审前快照＝任务工作树干净、7 文件 md5 如上，chipyard 源树 clean、SRC `3de213b5…`、sim `4e2228ad…`。

- **审后快照对账**：任务工作树仅 `.tao/tasks/chipyard/m13-chipyard-002-*.md` 一处 `+34 行`（即本审阅记录），5 份补丁 md5 与审前逐字节相同（`f2f19f2b`/`5dd1d370`/`8d90af80`/`44c1f38c`/`fa2d1d1f`）；主工作树 clean（HEAD `4cd1c071`，审阅期间主会话在推进、非本任务改动）；chipyard 源树 clean、SRC `3de213b5…`、sim `4e2228ad…`；engineer 的 `*-manual.log` 已按原大小/时间还原。

**采信未复验**：改前二进制的出处（按指示用其备份 `pre-sim`，其行为与「整字值判据」自洽）；`check-run-artifacts` 红 471 条归 016 夜跑的归属说法；engineer 自审 9 条 finding 的处置叙述（其注入已由 reviewer 重跑复证）。

**Findings（非阻断）**：① `run.sh` 头注释写「8 点探针」实为 9 点；② 完成区「修改文件」未列任务书自身；③ 「门控全绿」措辞略宽（实为所列 4 项门控全绿，`check-run-artifacts` 已在遗留声明归 016）。

**判决：Accepted** —— 上述命令在 reviewer 重跑下全部 EXIT=0，独立注入→FAIL→还原→回绿，超集仅含 016＋本任务改动；补丁超集的合并顺序与源树 amend 影响交 architect 裁定。

## 完成区

**测试结果**：全部通过；探针 9 点、三平台 66/66、`check-inst-asm` 897/897、门控全绿、注入 14 项 PASS。
**修改文件**：
- `generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala`（删 `resvWord`/`scCheckFail` 及其写回路径；`sc` 命中后写拍改为无条件；三处注释改述）
- `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCore.scala.patch`（重导出）
- `components/chipyard/patches/.../{WumingSemi.cc,WumingSemi.v,WumingDecoder,WumingSemi}.patch`（整体重导出带入 `016` 状态，见「待裁定」）
- `components/chipyard/changelog.md`（M13 一条）
- 证据目录：`<运行期证据目录>`（`run.sh` 六模式、探针两份期望表、改前二进制、`out/*.log`）

**验收结果**（真实输出）：
- 改前正证（sim md5 `ac35dffb…`）：P1/P2/P3 = 1（spec 0）⇒ 旧「整字值」判据；P4–P9 已与 spec 一致。
- 改后（sim md5 `4e2228ad…`）：P1..P9 全 match ⇒ 同字另一字节/同字其余字节/同址同宽写后 `sc` 均成功；另一条 `lr`、自消费、二次 `sc`、异宽、异址、异常进入（P9）不变。
- 三平台逐字节（chipyard `4e2228ad…`、qemu `725c5da7…`、gem5 `6e436d1b…`）：66/66 镜像（24 链例 + 42 故障例）。
- `check-inst-asm`：897/897（264 id）rc=0。
- 门控：`check-patch-tree` chipyard 段 0 问题（重导出前为 10 个既有问题，来自 `016` 未导出）；`--source-state` chipyard OK（HEAD=bbb93b6d、count=1、clean）；`check-component-changelog` PASS。
- 注入（`cp`+md5 还原）：注回 `resvWord` + `scCheckFail` ⇒ P1/P2/P3 转 1（3 红点），还原后 md5 一致、回绿。
**新发现/坑**：
- 注入若只注「值比较」不注 `scCheckFail` 写回，`sc` 不进存储但不写 `rdHB` ⇒ 读到旧值，注入假绿；必须连写回路径一起注回。
- hmon 返回槽只接受**绝对立即数**：`ENTRY+(label-_start)` 在指令立即数域丢基址（只剩段内偏移）⇒ 用 `.org` 固定 `.text` 偏移桩。
- `__NCHECK` 是汇编期 `.set`，桩代码必须排在 `__TEST_END` **之前**展开，否则打印长度为 0、`br.nz` 上溢成 64K 字节长跑。
**遗留问题**：多 hart 对同址同宽 store 的清除无观测载体（GAP，未造用例）；跨任务补丁导出见「待裁定」；`check-run-artifacts`（L1，非本任务验收项）红 471 条、全部来自 `m12-chipyard-016` 的夜跑日志子目录（本任务 0 条），不代删、归属见该任务收尾。

