# m16-testcases-004: Vast arch 三平台盘点与落点方案

**模块**：testcases
**项目里程碑**：M16
**依赖**：无（只读；与 `m16-testcases-005` 可并行）
**可并行分片**：是（9 个 cfx 可分片）
**预估**：中（只读盘点 + 文档，不设硬时限）
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定）

M16 的三方差分收敛为 **Vast arch scope**，裁定见 `.tao/knowledge/discussing.md`「M16 三方差分（Vast arch）批次裁定」：

- 只测 Kaiwu-Vast，不含 Tiny、不含 linux-user；cfx = 0/2/3/4/5/15/32/34/63；
- 三方（QEMU/gem5/RTL）签名逐槽一致，期望值独立派生自 `spec/`/`contract`，用户是 oracle；
- 仿真不进常规门控；
- 用例/脚本/数据集中 `tests/arch/`，签名机制集中 `tests/shared/`；
- 不预先造通用启动链，按 cfx 选最小载体。

本任务只做**盘点与方案**，不改组件代码、不改规范正文、不跑仿真。

## 要做

### 1. 三平台 cfx 盘点矩阵

对以下 9 个 cfx，逐项列 QEMU / gem5 / RTL 三侧状态：

`cfx0 umon`、`cfx2 smon`、`cfx3 hmon`、`cfx4 ptw`、`cfx5 cache`、`cfx15 hart`、`cfx32 pmem`、`cfx34 time`、`cfx63 power`。

每个 cfx 至少覆盖五面：**寄存器面 / 命令与副作用 / 异常与子原因 / 现有测试载体 / 现有门控**。每一格必须给证据：

- 有实现：`path:line`（组件源码树或补丁树，按 `docs/Process-01` 口径）；
- 没有：写「缺」并给判定依据（例如全树 grep 0 命中、或契约存在但实现无对应行）；
- 载体：写清是「QEMU bootrom 探针 / RTL ELF+loadmem / gem5 FS / 无」；
- 门控：写清在 `check-arch`、`check-arch-smoke`、手工脚本、无 中的哪一种。

矩阵落 `tests/arch/data/vast-arch-inventory.md`（新文件）。**27 格（9 cfx × 3 平台）必须全覆盖**，不许留空。

### 2. `tests/arch` 落点方案

落 `tests/arch/PLAN.md`（新文件），至少包含：

- 目录结构：`tests/arch/<cfx>/`（用例、`.lds`、生成器、`check_*.py`、`expected.yaml`）、`tests/arch/run_arch.py`、`tests/arch/common/`、`tests/arch/data/`；
- `run_arch.py` 的接口：`--cfx <0|2|3|4|5|15|32|34|63>`、`--platforms qemu,gem5,chipyard`、`--cache-model on|off`（arch 固定 on）、`--self-test`；
- `tests/arch.yaml` 字段方案：`machine: vast`（固定）、载体类型（`asm` / `driver`）、`platforms: [system]`；
- 迁移清单：`tools/chipyard/{ptw,tlb,dcache,icache,excp}/**`、`tools/testcases/arch/min_rom_probe_tlb.py`、`tests/arch/hmon/`（Tiny，移出 arch）的去向；
- 与 `m16-testcases-005` 的接口：签名脚本落 `tests/shared/signature.py`，arch 通过 `tests/arch/common/` 薄壳调用。

### 3. 直接修订 `docs/Process-09-测试组织规范.md`

用户 2026-11-22 裁定：Process-09 **可以直接修订**。按以下四条改正文：

- §3 scope→目录映射：arch 专用脚本/数据随 `tests/arch/`；
- §5 根级清单：支持驱动型 case 与 `machine` 字段；
- §6 落点：scope 专用脚本随 scope，`tools/` 只放跨 scope 共享；
- §7 目录结构：`tests/arch/` 增加 `run_arch.py`/`common/`/`data/`，`tools/testcases/arch/` 标待迁。

同时在 `tests/arch/PLAN.md` 记录「原文 → 新文」对照，便于复核与后续任务引用。只改 `docs/Process-09`，不改 `tests/arch.yaml` 与校验器实现（留给落点实施任务）。

### 4. Tiny hmon 迁出方案

现有 `tests/arch.yaml` 的 `arch-hmon-001`（`tests/arch/hmon/tiny_hmon.S`，gem5 Tiny FS）与 arch 只 vast 冲突。给出迁移落点（建议 `tests/unit/gem5/`）与需要同步改的文件（`arch.yaml`、`tests/arch/README.md`、`checks`/门控引用），只给方案，不执行。

## 不做

- 不改 QEMU/gem5/chipyard 源码或补丁；
- 不改 `tests/arch.yaml` 与 `check-tests-index` 校验器（留给落点实施任务）；
- 不建 `run_arch.py` 实现、不写新用例、不跑仿真/不重建。

## 约束

- 独立 `git worktree`；**不提交 git**；只写 `tests/arch/PLAN.md`、`tests/arch/data/vast-arch-inventory.md` 与 `docs/Process-09-测试组织规范.md`（外加运行期证据目录）；
- 不写运行期路径（`.work/**`、家目录、临时目录）到入库文件；
- 术语用「寄存器组」「核芯功能扩展」；
- 每条结论可回溯到真实 `path:line` 或现场 grep 输出，禁止凭记忆。

## 验证

运行期证据目录内的 `run.sh`，至少检查：

1. 矩阵 9 cfx × 3 平台 = 27 格全部有值（缺也要写「缺」），现场统计并与文中声明对账；
2. 矩阵内所有 `path:line` 落在文件行数内；
3. `docs/Process-09` 的 §3/§5/§6/§7 四条已落正文，`git diff` 可逐条复核；`tests/arch/PLAN.md` 保留「原文 → 新文」对照；
4. 不改代码：变更集 ⊆ {本任务书, `tests/arch/PLAN.md`, `tests/arch/data/vast-arch-inventory.md`, `docs/Process-09-测试组织规范.md`} ∪ `.tao/**`；
5. `--inject` 至少 2 路（删一格矩阵 / 伪造一条引用）⇒ FAIL，`cp`+md5 还原后回绿；
6. `make check-knowledge-refs` 与 `make check-tasks` 只读跑，记录 rc。

## 完成区

**测试结果**：`run.sh` 7/7 PASS（rc=0）；`run.sh --inject` 9/9 PASS（rc=0，含注入 A/B）。`make check-knowledge-refs` rc=0、`make check-tasks` rc=0（另跑 `check-dirs`/`check-tests-index` 各 rc=0，未改索引）。
**修改文件**：`.tao/tasks/testcases/m16-testcases-004-Vast-arch三平台盘点与落点方案.md`（同步主工作树 `1c50f253` 新范围 + 状态/完成区）、`tests/arch/PLAN.md`（新）、`tests/arch/data/vast-arch-inventory.md`（新）、`docs/Process-09-测试组织规范.md`（§1 范围注记 + §3/§5/§6/§7.1）。
**验收结果**：矩阵现场统计 `blocks=27 expected=27`；`path:line` 151 条全部在文件行内；PLAN 四节齐全且「原文/新文」各 4；Process-09 diff 新增行 50、§1 注记与 §3/§5/§6/§7.1 要素全含；变更集 4 文件全在允许范围。注入 A（删 cfx5 RTL 块）⇒ `FAIL missing block`、还原 md5 相同后回绿；注入 B（伪造 `helper.c.patch:999999`）⇒ `FAIL out-of-range`、还原后回绿。
**新发现/坑**：① QEMU/gem5 实现集合含 cfx1 jmon，本范围不含它，后续 arch 不得把它算入覆盖；② RTL 只有 cfx3/4/63（`WumingCfxHa` 三常量），cfx0/2/15/32/34 全缺、cfx5 只有阵列无命令面，是三方差分最大缺口；③ gem5 无任何 Vast cfx 载体（仅 Tiny hmon），需先建 gem5 FS 载体；④ 未跟踪文件不能用 `git diff` 判「空注入」，改用 md5 前后对账；⑤ 本册「§7」是平台，任务书所称「§7 目录结构」实为 §3 树，已在 PLAN §8 记录并另加 §7.1。
**遗留问题**：`tests/arch.yaml` 与 `check-tests-index` 未改（按范围留落点任务）；Tiny hmon 迁出只给方案未执行；`platforms` 与 engine 词汇是否合并待裁定；gem5/RTL 缺口见 §10。

## 审阅记录

### 第 1 轮 engineer 自审

审查范围：`tests/arch/PLAN.md`、`tests/arch/data/vast-arch-inventory.md`、`docs/Process-09` 改动、`run.sh` 与两个检查脚本；逐条核对引用行号与现场 grep。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 矩阵大量 `:NNN` 简写引用，无法机械校验 | ✅已修 | 全部展开为仓库根全路径；`check_refs.py` 支持 `Makefile` | refs 148→151，bad=0 |
| 未跟踪文件用 `git diff` 判空注入恒为空 | ✅已修 | 改 md5 注入前后对账 + 注入脚本失败分支 | 注入 A/B 均 FAIL、md5 相同、还原 PASS |
| Process-09 §5 把 inst/arch 两个文件放同一 yaml fence | ✅已修 | 拆成两个 fence，加「驱动型 case」引导句 | `git diff` 复核 |
| PLAN §8.4 嵌套 ```markdown/```text 破坏渲染 | ✅已修 | 外层改四反引号 | 渲染结构复核 |
| 迁移清单 `ptw/tlb/` 未在目录树体现 | ✅已修 | §2 ptw 行注明 `tlb/` | PLAN:33 |
| PLAN 引用的 `tests/unit/README.md` 不存在 | ✅已修 | 标注「当前不存在，新建或在现有说明补」 | PLAN:151 |
| cfx5 QEMU 只引 `ci = cfx_idx` 未引 raise 行 | ✅已修 | 改引 `helper.c.patch:2953` | check_refs bad=0 |
| RTL cfx63 只引 vectorBase，未引 space desc/attr | ✅已修 | 补 `WumingParams:143`/`:145` | check_refs bad=0 |
| RTL/ gem5 多处 file-level `:1` 证据过弱 | ✅已修 | 改 `WumingPtw:415`、`WumingTlb:65`、`WumingCache:135`、`node_tlb:127/146` | check_refs bad=0 |
| QEMU cfx63 几何引 `cpu.c:60`（profile 结构起点） | ✅已修 | 改 `cpu.h:227`（Vast ROM base） | check_refs bad=0 |

### 第 1 轮 reviewer 验收（2026-11-22）

**重跑记录**（全部本人执行，workdir=仓库根，相对路径）：
- 运行期证据目录内 `run.sh` ⇒ `PASS: 7/7 checks`，`EXIT=0`；`run.sh --inject` ⇒ `PASS: 9/9 checks`，`EXIT=0`（注入 A `inject rc=1`、注入 B `inject rc=1`，还原 md5 `3e1b506108903bbc7e5744ba73bfd4d6` 前后相同、回绿 rc=0）。
- reviewer 独立注入（非采信脚本自检）：`cp` 备份 → 删 `### cfx15 hart — gem5` 整块 → 跑 `run.sh` ⇒ `rc=1`，`FAIL missing block cfx15 gem5`／`FAIL: 1/7` → `cp` 还原 → md5 与注入前一致 → 重跑 `run.sh` ⇒ `PASS: 7/7`，`rc=0`。
- 门控独立重跑：`make check-knowledge-refs` rc=0（PASS，0 悬空）、`make check-tasks` rc=0、`make check-dirs` rc=0、`make check-tests-index` rc=0（472 条 PASS）。

**约束核验**：
1. 矩阵 27 格：`check_matrix` `blocks=27 expected=27`；本人 `grep -c '^### cfx'` = 27；五面字段逐格非空、`缺` 格均带 grep 0 命中/掩码依据。
2. 引用 151 条：`check_refs` `refs_checked=151 bad=0`；本人独立复算 bad=[]，并扫描全文件 222 处 `path:line` 全部落在校验正则内（无绕过行号校验的引用）。
3. 抽查 25 条引用（QEMU 10 / gem5 8 / RTL 7）`sed -n` 核行号：`cpu.c.patch:55`（Vast 掩码 0/1/2/3/4/15/32/34/63，无 5）、`helper.c.patch:343`（U->0,S->2）、`cpu.h.patch:227`（VAST_ROM_BASE）、`Makefile:1708`（check-arch-smoke 目标）、`node_cfx.cc.patch:33`（kCfxhaMap 9 项无 5）、`fs.py.patch:23`（no caches）、`node_tlb.cc.patch:150`、`node_cfx.cc.patch:929`、`WumingParams.scala.patch:89`（WumingCfxHa 仅 hmon/power/ptw）、`WumingCache.scala.patch:49/158`（「cfx5 wiring later task」）、`WumingCore.scala.patch:1421`、`GewuFile.scala.patch:100`、`min_rom_probe_tlb.py:1`、`tests/arch.yaml:14` 等，均在文件行内且语义相符。
4. 关键事实三抽现场核：RTL `grep -rl cfx_{umon,smon,hart,pmem,time} components/chipyard/patches` = 0 命中（cfx0/2/15/32/34 全缺 ✓）；RTL cfx5 仅 `WumingCache` 阵列、命令面源码明写 later task、`WumingParams` cfx 序列仅 3 项（✓）；gem5 `tools/gem5/` 仅 `check_tiny_hmon.py`（Tiny）、tests 树无 vast+gem5 用例（✓ 无 Vast 载体）。
5. Process-09 `git diff` 逐条：§1 范围注记、§3 树（+3 条 bullet）、§5 驱动型 case/`machine`、§6 目标改写（scope 专用随 scope）+bullet、§7.1 新增，四条均落正文；与既有条款的唯一张力是 §6 旧文「全部收拢 tools/testcases/」被任务书授权改写，新旧对照在 PLAN §8.3；未触碰 inst/unit/tset 其它 scope 规则。
6. PLAN：目录结构/`run_arch.py` 四接口/`arch.yaml` 字段/迁移清单（`tools/chipyard/{ptw,tlb,dcache,icache,excp}` 与 `tools/testcases/arch/*` 逐个存在）/Tiny hmon 迁出 7 项同步文件（`arch.yaml` 条目、Process-07:96、`Makefile:811` 均现场吻合）均可执行。
7. 变更集 4 文件 ⊆ 允许范围；`git status` 无 `components/`、无 `tests/arch.yaml`、无 `tools/`；`git log -1` 仍 `0eb640c5`（未提交）；入库三文件无 `.work/`/家目录/`/tmp` 路径；无「银行」。
8. 注入前后快照对账：`git status` 4 行逐行相同，四文件 md5 与注入前一致（`fccbe3cd`/`589ad600`/`3e1b5061`/`0d7b4b02`）。

**Finding（均文档级，不阻断，交 architect 收尾订正）**：
- F1 `tests/arch/PLAN.md:131` 薄壳拟重导出 `load_expected`/`compare_slots`，但 005 已合入的 `tests/shared/signature.py` 实际 API 是 `parse`/`compare`/`unwritten`/`run`/`capture`/`Emitter`（全仓无 `compare_slots` 定义）；004 写作时 005 未落地、系预估名，实施前须按真源改名。
- F2 引用行号小偏移（同代码块内/相邻行）：`Makefile:1716` 实为 echo 行（调用在 1717）、`WumingCore:1578` 实为 `isCfx2` 分支头（tlb_control 注释在 1582）、`node_tlb:150` 覆盖 4 个子原因但该行仅 ISP/DSP、`helper.c:2953` 为块内注释（raise 在 2955）。
- F3 `Process-09` §1 表格 arch 行仍列 UART/IPI，与同节新注记「UART/J/多核不在 scope」并存，建议表格同步或指向注记。
- F4 运行期证据目录残留过期备份 `inventory.bak.2376965`（md5 `6529f238…` ≠ 当前 inventory `3e1b5061…`，系早期注入中断遗留）；当前 inventory 终态与注入前快照一致、`run.sh` 终态 7/7 绿，产物无损，收尾请清该 bak。

**判决：Accepted**——验收命令块在本人重跑下全部通过（7/7、9/9、四门控 rc=0），独立注入 FAIL→还原→回绿成立，约束 1–8 逐条守住，无凑绿/越界/未采信项。
