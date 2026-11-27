# m17-spec-003: `generate_opcodes.py` 与 `opcodes.yaml` 漂移收口（ISS-416）

**模块**：spec
**项目里程碑**：M17
**依赖**：无
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

`ISS-416`（P2，`m13-spec-005` 发现）：自 `SPEC-194t` 起只改 `contracts/opcodes.yaml`、未重跑 `tools/spec/generate_opcodes.py` ⇒ 现在重跑会改 **93 行 FP 记录**。两份都可被门控/工具消费（`validate-encoding`、`check-isa-coverage`、`check-qemu-forms`、`check-decodetree-repro` 等），漂移会造成「改 yaml 不改生成器」的静默不一致。

## 要做

1. 在临时副本里重跑生成器，与入库 `contracts/opcodes.yaml` 做**逐行 diff**，把 93 行按「纯格式/顺序 / 字段值」分类；
2. 确定唯一真源与生成方向（写进任务书）：若生成器为准 ⇒ 重生成 yaml；若 yaml 为准 ⇒ 修生成器并补对照断言（推荐后者：yaml 是长期真源）；
3. 加一条**机械门控**（或并入现有）：生成器输出 == 入库 yaml（或字段级等价），禁再漂移；
4. 不改任何指令的编码语义（opc/mask/字段位域）；版本号不升。

## 不做

- 不改 fp 语义、QEMU/gem5/RTL/IDL；
- 不动 spec 正文。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 只动 `tools/spec/generate_opcodes.py`、`contracts/opcodes.yaml`、必要门控/文档、本任务书；完成区 ≤30 行。

## 验证

1. `make validate-encoding check-isa-coverage check-qemu-forms check-instrutinfo`（或现场对应目标）rc=0；
2. 重跑生成器 ⇒ 与入库 yaml **零 diff**（或字段级等价断言通过）；
3. **可达 FAIL**：手改 yaml 一行 ⇒ 新门控红；`cp`+md5 还原回绿；
4. diff 审计：93 行逐条归因（格式 vs 语义），语义行数必须为 0。

## 结论（实现时认定）

- **人读真源**：`spec/`（SimRISC-00 编码主表）+ `.tao/contracts/contract-isa.md`/`contract-fp.md`。
- **机器数据真源**：`contracts/opcodes.yaml`（`validate-encoding`/`check-rule-refs`/`check-fp-contract`/`check-instrinfo` 等只读它）；**唯一写者 = `tools/spec/generate_opcodes.py`**：生成器必须逐字节复现入库 yaml。
- **生成方向：yaml 为准、修生成器**。门控 `make check-opcodes-repro`（L1）双向哨兵——手改 yaml ⇒ 红；改生成器表未重跑 ⇒ 红。与历史处置一致：`cb8ca30d` 按 SPEC-194t「舍入三分」改生成器表；`5cc2c0ac` 按契约修正 `af7ffb09` 先改生成器表再重生成。
- **现状**：HEAD 上二者零 diff（重渲染与入库同 md5）；本任务**未改 yaml 一个字节**、未改任何编码语义（opc/mask/value/字段位域）、未升任何版本号。

## 漂移归因（逐条）

复现法：把 `<rev>` 的 `generate_opcodes.py`（+ `gen_asm_list.py`）取到临时树跑该版生成器，与同 rev 入库 yaml 逐行 diff；再由 `audit.py` 按记录 id 归因（编码字段差异须为 0）。

| 快照 | 记录 | 行级 diff | 触及记录 | 字段值（legality/rule_refs） | 纯格式 | 编码字段 |
|------|------|-----------|----------|------------------------------|--------|----------|
| A `d89810f7`（m13-spec-005 合入） | 264/264 | 删 38 / 增 53 = 91 行 | 19 | 18 条 FP `orri` 转换记录（ft2fo…uo2fo）：yaml 侧 = SPEC-194t 六档 one-hot / 精确 SBZ，生成器侧 = 旧通用 mreg 约束 | 1 条 `ft2ft_orri_rf`（load 后等价，PyYAML anchor 复用） | 0 |
| B `c5cbcbf2`（m18-spec-003 合入前） | 263/263 | 删 20 / 增 8 = 28 行 | 8 | 8 条 rf 形式访存 ld/st/ldm/stm 的 `.t`/`.o`（`af7ffb09` 契约修正只补了 yaml 的 `aligned(4/8)`+`excp_malign`） | 0 | 0 |
| HEAD | 263/263 | 0 / 0 | 0 | 0 | 0 | 0 |

- **语义行数（编码字段）= 0**：两个快照的差异键都只落在 `legality`/`rule_refs`，`id/mnemonic/format/opc/mask/value/fields/scope/spec_cite/decode` 全同。
- 两个快照现均已被后续重生成吸收（A ← `cb8ca30d`；B ← `5cc2c0ac`），故 HEAD 零 diff。

## 待裁定

- ① issue 记「93 行（39 删 + 54 增）」，本任务在 `d89810f7` 快照复现为 **91 行（38/53）**，记录集与分类一致（18 字段值 + 1 纯格式）。差 2 行推测为当时 WIP 侧快照的折行/空行（master 上不可复现）。关闭 `ISS-416` 时是否按复现值订正行数口径？
- ② 「yaml 为机器数据真源、生成器为唯一写者」是否需要立 ADR？（现只落 `contracts/README.md`、`docs/Process-07` 表与生成器 docstring）

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-24）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `main()` 由无参改为 `main(argv=None)`，可能影响调用方 | ✅已修 | 全文 grep 仅 `__main__` 调用；`sys.exit(main())` 返回值对齐 | `grep -rn generate_opcodes` 无外部调用者；`make check-opcodes-repro` rc=0 |
| F2 渲染与 main 各算一遍 scope 计数（DRY） | ✅已修 | 抽 `_counts()`/`_summary()`，render/main 共用 | 重渲染 md5 仍 `3d0535ff…`（字节不变） |
| F3 `--check` 遇缺失文件抛 traceback | ✅已修 | `OSError ⇒ FAIL + rc=2` | `--check --output 不存在` → rc=2 + FAIL 文案 |
| F4 证据脚本 `verdict()` 用了未传的 `$5`（`set -u` 下中断） | ✅已修 | 改成 `detail=${4:-}`，统一「期望/实际/detail」 | `run.sh` 16/16 PASS，无 unbound |
| F5 注入 B 锚点取的是不存在的字面量 ⇒ 假注入（`git diff` 命中来自本任务自身改动） | ✅已修 | 锚点改 `leg_convert_sbz = [...]`；判定改「注入前后 md5 变化」 | 注入后 md5 变 + 门控 rc=2；还原后 md5 复原 + rc=0 |
| F6 L1 全量 `make check` 有 9 项红，是否本任务引入 | ✅已修（核实为基线） | 不改代码 | 在 pristine `HEAD` 临时树跑同 9 目标：错误集与工作树**逐行相同**（仅 Makefile 行号/prereqs 计数/时间戳差） |
| F7 生成器默认写模式会直接覆盖 yaml（误用即绕开审阅） | ⏸延后（文档化） | docstring 写明「yaml 是生成物、单一写者、禁手改」；门控兜底 | 门控双向可达 FAIL（注入 A/B） |

### 第 1 轮 reviewer 复核（2026-11-24，中改 40 min 档）

**重跑记录**（全部本人实测，工程态 worktree 仓库根执行；运行期证据目录内 `run.sh`）：
- `make check-opcodes-repro` rc=0（263 条，md5 `3d0535ff…`）；`make validate-encoding` rc=0（263 OK）；`make check-qemu-forms` rc=0；`make check-instrinfo` rc=0（0 errors）；`make check-isa-coverage` rc=0（accept 263/reject 0，llvm-mc 取自主工作树构建树，缺则 FAIL 不跳过）；证据脚本 rc=0 = PASS 16 / FAIL 0。
- **可达 FAIL 两路（本人独立注入，cp+md5 还原纪律）**：A 手改 yaml 首行 ⇒ make rc=2，diff 的 `-` 行带注入串 + 「禁手改 yaml」文案；B 改生成器 opc 表 ⇒ rc=2，diff 显示渲染侧 `ha/value` 变化 + 「改表后重跑」文案（两路差异即在差异行来源侧）；还原后两路均 md5 复原 + rc=0。另证 `--check --output 缺失` rc=2、`--output` 落盘与入库 diff 0 行、写模式重跑 yaml md5 不变。
- **9 项 L1 基线红**：本人在 pristine HEAD 独立副本与工作树各跑同 9 目标，均 rc=2；归一化（路径/Makefile 行号/prereqs 计数）后 8/9 逐行相同，`check-temp-dirs` 仅差「副本非 git 仓库⇒无排除集」与 mtime 取整（53.1/53.2 h），VIOLATION 同 5 条 ⇒ 基线红，非本任务引入。
- **越界/零语义变更**：`git status -uall` 恰 5 文件，与完成区逐一对账一致；`contracts/opcodes.yaml` git diff 空、md5 前后 `3d0535ff…`；263 条不变；未动 spec 正文与其它组件；注入前后 md5 对账通过。
- **93 vs 91**：本人独立重跑 `d89810f7` 旧生成器 ⇒ 删 38 / 增 53 = **91 行**；同一 diff 的 `diff -u` 含 `---`/`+++` 表头恰为 39/54 = **93** ⇒ issue 的 93 是表头计入的口径差。按 id 全字段比对两快照：编码字段（opc/mask/value/fields 等）差异 0，差异键仅 `legality`/`rule_refs`；触及 18 字段值 + 1 纯格式（`ft2ft_orri_rf`，PyYAML anchor 复用）与任务书归因一致。
- **关单数字建议：91 行（38 删 / 53 增）**，依据为 master 历史 `d89810f7` 可复现值；备注「93 = 91 + `diff -u` 表头 2 行」即可，不需另开返工。
- **ADR 建议**：命中 Process-03 判据 2（跨模块需一致：validate-encoding/check-instrinfo/check-qemu-forms 等多门控消费）、3（生成器为准 vs yaml 为准有取舍）、5（结论固化为长期约束）⇒ **建议立轻量 ADR**（主题「`opcodes.yaml` 单一写者 + 生成一致性 L1 门控」，Status Candidate，落 `.tao/adr/`），由用户确认；现有 README/Process-07/docstring 三处落点保留为规范正文引用。此为提醒，不阻断本任务。
- **非阻断 finding**：① 证据目前落易失临时区，收尾迁非易失位置；② 脚本注入 B 的锚点走 `EXPR_TO_RULE` 异常路径（仍 rc≠0），后续可换渲染值类锚点直接走 diff 路径（diff 路径本人已用 opc 锚点证可达）。
- 采信项：任务书表格中 `c5cbcbf2` 快照 20/8=28 行经本人复跑一致（此项为复算，非采信）。

**判决：Accepted**（验收命令块在本人重跑下全绿；硬约束无违反；状态字段未改）

## 完成区

**测试结果**：运行期证据目录内 `run.sh` = **PASS 16 / FAIL 0（rc=0）**；`audit.py` rc=0。
**修改文件**：
- `tools/spec/generate_opcodes.py`（抽 `build_records`/`render`/`_counts`/`_summary`；新增 `--check`/`--output`；docstring 写单一写者）
- `Makefile`（`.PHONY` + `check-opcodes-repro` 目标 + help + 并入 `_locked-check`）
- `docs/Process-07-门控分层规范.md`（门控清单加 1 行）
- `contracts/README.md`（`opcodes.yaml` 行注明生成物/唯一写者/门控）
- 本任务书（结论/归因/待裁定/审阅/完成区/状态）
**验收结果**：`gen --check` rc=0（263 条，md5 `3d0535ff…`）；`make check-opcodes-repro` rc=0；重渲染落盘 + `diff` 0 行；`validate-encoding` rc=0（263 条 OK）；`check-qemu-forms` rc=0；`check-instrinfo` rc=0（0 errors）；`check-isa-coverage` rc=0（accept 263/reject 0）——后者需 `llvm-mc`，本 worktree 无 `.work` 时由证据脚本取主工作树构建树（缺则 FAIL，不跳过）。
**可达 FAIL**：注入 A（手改 yaml 一行）⇒ 门控 rc=2 并打印注入串；`cp` 还原 ⇒ md5 复原 + rc=0。注入 B（改生成器表不重跑）⇒ rc=2；还原 ⇒ md5 复原 + rc=0。
**新发现/坑**：① 9 项 L1 红为**基线红**（pristine HEAD 树逐行相同）：`check-patch-tree`/`check-cfx-aliases`/`check-musl-freshness`/`check-run-artifacts`/`check-width-sizes`/`check-components`/`check-linux-toolchain`/`check-writer-guards`/`check-temp-dirs`，均来自共享 `.work`/`.dadao` 现场状态，与 `opcodes.yaml` 无关。② 本 worktree 无 `.work` 时 `check-isa-coverage` 报「找不到 llvm-mc」，需 `DADAO_ROOT=<主工作树>` 或 `.work` 软链。③ 建议沉淀：`contracts/` 生成物的「单一写者 + `--check` 门控」范式（与 `check-wuming-cycles` 同构），后续新增生成物照此办。
**遗留问题**：无（待裁定 ① 行数口径、② 是否立 ADR 由主会话定；两项均不影响实现与门控）。

