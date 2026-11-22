# M15 归档（Archive）

> **归档日期**：2026-11-22 ｜ **范围**：M15 里程碑（2026-11-12 起，**2026-11-22 达成**）的全部任务书与相关记录 —— **ISA 语义结构化（IDL v0 + 12 册 operation + 渲染/门控）**
> **归档判据**：任务书字段 `**项目里程碑**：M15` 且状态 ∈ {`已验证`,`里程碑`}（**66** 册 = gem5 2 / idl 20 / infra 10 / integ 1 / qemu 2 / spec 8 / testcases 23；全部 `已验证`）；任务流水冻结 **66** 条；`issues.yaml` `closed_in: M15` 关闭项 **1** 条（见 `issues-closed.md`，`tools/infra/archive_issues.py --check` 可复核）；`MEMORY.md` 纯 M15 行移除、摘要见 §4。
> **自归档说明**：`m15-integ-001`（本归档任务自身）按 `docs/Process-04 §4.1` 迁入 `integ/`；§1 `integ` 计数（1）与 §2 流水（66 行）均已含它。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见 `m15-retrospective.md`，后续路线见 `.tao/knowledge/milestones-m16.md`（M16）、`milestones-m17.md`（M17，IDL 执行）、`milestones-m18.md`。

## 1 任务清单（66 个，按模块）

| 模块 | 数量 |
|---|---|
| gem5 | 2 |
| idl | 20 |
| infra | 10 |
| integ | 1 |
| qemu | 2 |
| spec | 8 |
| testcases | 23 |

> 任务书位于同目录下模块子目录（`git mv` 保留 `R` rename 历史，逐册 md5 搬前/搬后相等）。模块目录按 M15 实际出现者建（M15 无 `chipyard`/`linux`/`llvm` 册）。

## 2 任务流水（冻结）

> **冻结日期**：2026-11-22。65 条「已验证」行按活台账 `.tao/knowledge/milestones-m15.md`「已验证」表**原值**搬入（状态按任务书规范化 `已验证`；次序 = 完成时间倒序，与台账一致），另加本归档任务（`已验证`）一行；台账文件随本归档删除。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| m15-integ-001 | 已验证 | 2026-11-22 12:44 | M15 归档（66 册迁 `.tao/archive/M15/`；台账/MEMORY/README/issue 快照收口） |
| m15-testcases-023 | 已验证 | 2026-11-22 12:41 | ansibench 四件（coremark/dhrystone/linpack/whetstone）Tiny+picolibc 5/5；clock 修后 probe 差 0.1% |
| m15-infra-010 | 已验证 | 2026-11-22 11:37 | `times()` 按 `SYS_TICKFREQ` 缩放（ISS-502 闭合）；补 lds `.text.start` 段首（009 漏项） |
| m15-infra-009 | 已验证 | 2026-11-21 20:44 | picolibc Tiny 地址图 + `.stack :NONE`（删 513 行 lds 副本；PT_LOAD memsz 0x7dfe00→0xa70） |
| m15-testcases-022 | 已验证 | 2026-11-21 11:03 | Tiny 执行环境命名：`power_tiny`/`hmon_tiny` → `cfx_power_tiny`/`cfx_hmon_tiny`（4 文件 + 引用；镜像字节不变 `a5d78816…`） |
| m15-testcases-021 | 已验证 | 2026-11-20 23:29 | 伪指令收口（`LOAD_ADDR`→`set.rb/set.rd` 528 处、`LD64` 168 处；删两个 `.inc`；bootrom `a5d78816…`） |
| m15-spec-009 | 已验证 | 2026-11-20 23:12 | SimRISC 0.5.7 发布投影（README 版本表、契约版本头与引用、`archive/SimRISC-0.5.7` 快照） |
| m15-spec-008 | 已验证 | 2026-11-20 22:44 | SimRISC 0.5.7 发布（13 册去 `-rc`；变更记录按主题重排 21→5 组；清单 sha256） |
| m15-gem5-002 | 已验证 | 2026-11-20 16:16 | 窄 `lr` 高位保持（`exec/b6.cc` 切片写；单测 30/30、12 检查点逐字节） |
| m15-qemu-002 | 已验证 | 2026-11-20 16:14 | 窄 `lr` 高位保持（`store_rd_narrow`；9 载体期望订正 + case-ledger；272/272） |
| m15-idl-021 | 已验证 | 2026-11-20 16:05 | IDL 修复批（D1 `jump` 写 64 位；D2 8 条 rf 对齐守卫；补回丢失守卫；清 spec-006 遗留） |
| m15-spec-006 | 已验证 | 2026-11-20 15:37 | IDL 语言规范迁 `spec/IDL-ISA语义描述语言与语义库.md`（`idl/README` 428→22 行） |
| m15-idl-020 | 已验证 | 2026-11-20 13:02 | IDL 差异盘点（263 条；一致 100/偏离 68/特有 95；D1/D2 应改 IDL） |
| m15-spec-005 | 已验证 | 2026-11-20 10:52 | IDL 块布局改造（节末集中 + 三级标题 + 导语；12 册散文零改动） |
| m15-idl-019 | 已验证 | 2026-11-20 09:08 | `ftsclb` 改调库 `ft_scale`（260 个 n 下溢→溢出=修 bug；等价 11875 例 0 失配） |
| m15-testcases-020 | 已验证 | 2026-11-20 00:05 | `scmp` 无序向量改 canonical（18 检查点/144 B 双 lane 0；死宏与旧口径清理） |
| m15-qemu-001 | 已验证 | 2026-11-19 23:10 | `scmp` 无序结果改 canonical quiet NaN（QEMU 侧；20/20 含可达 FAIL） |
| m15-idl-007 | 已验证 | 2026-11-19 21:40 | `SimRISC-07` 全册 50 条（±0 相等修复、scmp canonical、oracle 特殊值池；93/93） |
| m15-spec-007 | 已验证 | 2026-11-19 21:25 | `contract-fp.md` 对齐 spec（scmp 无序 canonical；11 处 sNaN 逐条处置） |
| m15-gem5-001 | 已验证 | 2026-11-19 21:05 | gem5 `scmp` 无序结果改 canonical quiet NaN（`check_b7` 3946 vectors） |
| m15-idl-017 | 已验证 | 2026-11-19 18:02 | ft 族补正（tininess 后判、类型缺陷、i32/u32→fo、ft_scale；108 函数 0 例外） |
| m15-idl-016 | 已验证 | 2026-11-19 17:20 | 浮点库 fo 族 + remainder（105 函数；oracle 30698 例） |
| m15-idl-015 | 已验证 | 2026-11-19 13:00 | 浮点语义库 ft 族 53 函数（`idl/lib/fp.idl`；oracle 10478 例） |
| m15-infra-008 | 已验证 | 2026-11-19 12:52 | CONFIG_DADAO_* 钉子全集门控（13 脚本×15 符号×41 镜像；C2 逃逸口） |
| m15-idl-014 | 已验证 | 2026-11-19 12:05 | 解码变量 7 处代码修正 + 04/08/09 注释 61 处统一记号 + 门控 |
| m15-idl-008 | 已验证 | 2026-11-19 11:40 | `SimRISC-08` 21 条 operation（sem 改从 `.idl` 取语句；155 条/10 册） |
| m15-idl-001 | 已验证 | 2026-11-19 11:25 | `SimRISC-01` 38 条 operation（rf 对齐按裁定、静态先；68/68） |
| m15-idl-009 | 已验证 | 2026-11-19 11:23 | `SimRISC-09` 21 条 operation（shamt 取内容低 4 位；96 条/10 册一致） |
| m15-idl-004 | 已验证 | 2026-11-19 11:04 | `SimRISC-04` 33 条 operation（52/52、18 路反例） |
| m15-idl-012 | 已验证 | 2026-11-19 10:53 | `SimRISC-12` 28 条 operation（sc 用 `store_conditional`；lr 窄读只写低位；83/83） |
| m15-idl-006 | 已验证 | 2026-11-19 10:44 | `SimRISC-06` 15 条 operation（call/ret 走 `ras_*`；52 检查项） |
| m15-idl-010 | 已验证 | 2026-11-19 10:44 | `SimRISC-10` 21 条 operation（`rev.b` 逐块反转；62/62） |
| m15-idl-002 | 已验证 | 2026-11-19 10:43 | `SimRISC-02` 17 条 operation（cs.* 条件按 §3.2 位级；38/38） |
| m15-idl-011 | 已验证 | 2026-11-19 10:06 | `SimRISC-11` 5 条 operation（escape/cfx2rd/cfx2rc/fence 按语义库 v1；37/37） |
| m15-idl-003 | 已验证 | 2026-11-19 09:52 | `SimRISC-03` 8 条 operation（wyde 切片写；30/30、384 向量） |
| m15-idl-005 | 已验证 | 2026-11-19 09:42 | `SimRISC-05` 6 条 operation（`aip.si` 用 `ip()`；13/13、4 路注入） |
| m15-idl-013 | 已验证 | 2026-11-19 09:14 | 语义库 v1（`ip()` 64 位、cfx 访问/escape/fence、rf 专用表述）；T1–T7 落地 |
| m15-testcases-018 | 已验证 | 2026-11-19 03:05 | gem5 lane 补 `--semihost on`（`run_inst_tiny`/`check_tiny_hmon`/`run_parity --direct-check`；21/21、42/42） |
| m15-testcases-019 | 已验证 | 2026-11-19 02:15 | 11-cfx 链例12 SRAM 哨兵显式清零（chipyard TLRAM 上电非 0；双 lane 96 B 相同） |
| m15-spec-001 | 已验证 | 2026-11-19 00:38 | ISA 语义源迁 `idl/`（`.idl` 为源 + `render.py` 生成 spec 块；5 条样板、4 路注入） |
| m15-testcases-017 | 已验证 | 2026-11-18 23:11 | RF 窄写补测（`ld.t`/`ldm.t` 高 32 位保持）+ 11-cfx 两载体按新 escape 语义（272/272） |
| m15-infra-007 | 已验证 | 2026-11-18 19:02 | 死引用收口（台账改自动发现、删退役 `check_005t_coverage`；NON_LIVE 11→3） |
| m15-infra-006 | 已验证 | 2026-11-18 18:44 | `components/` 目录防护（8 目录 + `[subdir_owners]`；新增目录须用户同意） |
| m15-infra-005 | 已验证 | 2026-11-18 16:05 | `.manifests.toml` 第一波（spec/.tao/.tao-knowledge + 必需清单注册表；删清单/删注册表/游离清单即红） |
| m15-infra-002 | 已验证 | 2026-11-18 11:42 | refs 清空（9 孤儿删除；其余 20 份由 004 承接：迁 13 + 删 7） |
| m15-infra-004 | 已验证 | 2026-11-18 11:42 | refs 13 份活数据源迁 `tests/data/` + refs 清空 + `check_dead_refs`（未接门控） |
| m15-infra-003 | 已验证 | 2026-11-18 11:09 | 文件防护门控盘点（64 行清单 + 缺口：spec 新增册逃锁 / 6 目录无白名单） |
| m15-testcases-016 | 已验证 | 2026-11-18 10:01 | `tests/ee-*` 统一 `<role>_<ee>`（51 mv + 删 `k0_README`；272/272、k0 101/101） |
| m15-infra-001 | 已验证 | 2026-11-18 09:00 | 三契约消费点迁移（machine_profile 拆读 machine/exec-envs/tests-matrix + `ee-*/runtime.yaml`；删旧 machine-profiles） |
| m15-testcases-015 | 已验证 | 2026-11-18 08:27 | 剩余 bootrom：`k0_*` 7 件 → `tests/ee-vast/`、4 散件 → `tests/ee-tiny/`（k0 101/101、k0/k1 119/112） |
| m15-testcases-014 | 已验证 | 2026-11-18 07:30 | `inst-tiny.lds` 移入 `tests/ee-tiny/`（202 .S 头注释同步；272/272） |
| m15-testcases-013 | 已验证 | 2026-11-18 07:05 | vast 资产集中到 `tests/ee-vast/`（step5 bootrom 7 + kaiwu-vast.lds；md5 8/8） |
| m15-testcases-012 | 已验证 | 2026-11-18 06:41 | user 资产集中到 `tests/ee-user/`（12 脚本 + 5 crt/lds/runtime；与 011 双 `-L` 并存） |
| m15-testcases-011 | 已验证 | 2026-11-17 23:33 | tiny 资产集中到 `tests/ee-tiny/`（4 脚本 + 10 bootrom + 3 lds；272/272、bootrom md5 不变） |
| m15-testcases-010 | 已验证 | 2026-11-17 21:51 | 01 册 38 文件：opc 0x16→0x20、boundary 正/负/全1、rb0 imm 负/零/正；272/272 |
| m15-testcases-009 | 已验证 | 2026-11-17 08:56 | 「一例一镜像」→「每 `.S` 一镜像」（209 文件 248 行注释 + 6 文档）；`__PRINT` 零长硬化双保险（注入必红 rc=124） |
| m15-testcases-007 | 已验证 | 2026-11-17 07:47 | 故障例链式合并（`.faulttab`+哨兵；904→272 镜像；271/271 行为与 meta 全等） |
| m15-testcases-006 | 已验证 | 2026-11-16 22:55 | 装载一律用规范伪指令（set.rd/set.rb/set.fo）+ lds 统一 FP 布局；行为等价 A′↔C 903、A↔A′ 899，差异均为地址/布局类 |
| m15-testcases-008 | 已验证 | 2026-11-16 21:53 | 退役 clmul C/IR 探针（删 7 文件 −2528 行；yaml 472；L3 成员 4→3 + `check_l3_report` 现场派生） |
| m15-testcases-005 | 已验证 | 2026-11-16 20:56 | 2 行级结构重复宏化（净收益>0 + S9 门控；净省 553 行/569 处；`__RF_`→`__PREP_`） |
| m15-testcases-004 | 已验证 | 2026-11-16 18:17 | 整例宏化（`__PT_` 前缀 + 台账身份 + S6/S7/S8 防藏；`sc.*` −38%、rf2rf 回退） |
| m15-spec-003 | 已验证 | 2026-11-16 14:55 | `set.ft/set.fo rf, rs` → `set.rf rf, rs`（两册表 8→7、LLVM 新助记符 + 5 负例、载体改名 `pseudo_set.rf_reg.S`） |
| m15-testcases-003 | 已验证 | 2026-11-16 12:03 | 文件内结构重复段宏化·试点（7775→5850 行 −24.8%；册宏 6+文件内 3；A1–A6 81/81、点号 30/30） |
| m15-spec-002 | 已验证 | 2026-11-16 11:15 | 伪指令正文分层（`SimRISC-00 §5` 130→19 行表格化；`Toolchain-01 §6.2` 逐条语义原文迁入；删原 §6.2；4 册锁重算） |
| m15-testcases-002 | 已验证 | 2026-11-16 11:00 | 汇编宏作用域下沉（共享层 132→24 宏/2134→661 行；7 册 .inc 75 宏；18 单文件宏；删 15 死宏；`check-inst-macro-scope`） |
| m15-testcases-001 | 已验证 | 2026-11-15 21:30 | `tests/inst` 载体汇编宏去重下沉（10 宏入共享层、8 文件删 32 处重复定义，镜像 904/904 不变） |

## 3 终局证据

| 套件 | 结果 |
|---|---|
| 收口判据 ①：263 条 operation | `m15-idl-020` 盘点：`contracts/opcodes.yaml` 三处自洽；12 册合计 **263** 条（38+17+8+33+6+15+50+21+21+21+5+28） |
| 收口判据 ②：12 册渲染逐字节一致 | `make check-idl-sync`（`render.py --check`，L1 成员，`m15-spec-001` 起）；本任务现跑 rc=0 |
| 收口判据 ③：`.idl` sha256 锁 | `idl/*.idl` 12 份 + `idl/lib/fp.idl` 逐文件 sha256 入 `idl/.manifests.toml`（N21，2026-11-20 收口） |
| 语义库 | `m15-idl-013` v1（`ip()` 64 位、cfx 访问/escape/fence、`ras_*`）；`015`/`016`/`017` 移植与补正浮点库（`ft` 53 函数 / `fo`+remainder 105 函数 / `ft` 补正 108 函数 0 例外），oracle 例数见各册 |
| 版本发布 | SimRISC **0.5.7**（`m15-spec-008`：13 册去 `-rc`、变更记录按主题重排 21→5 组、清单 sha256）+ 发布投影（`m15-spec-009`） |
| 测试资产 | 每 `.S` 一镜像（904→**272** 镜像，`m15-testcases-007`）；`tests/ee-tiny`/`ee-user`/`ee-vast` 三执行环境资产集中（`011`–`016`）；装载统一伪指令（`021`）；`m15-testcases-023` ansibench 四件 Tiny+picolibc 5/5 |
| 三平台语义修正 | `scmp` 无序结果 canonical quiet NaN（`qemu-001` / `gem5-001` / `testcases-020`）；窄 `lr` 高位保持（`qemu-002` 9 载体 + 272/272；`gem5-002` 单测 30/30） |
| 归档门控（2026-11-22，本任务现跑） | `check-archive` rc=0；`check-milestones-fresh` M15 已不在列表（M16 两条预估时间红为**既有基线**，`f88c726a` 引入、非本任务）；`check_issues` / `archive_issues --check` / `check-knowledge-refs` / `check-dirs` / `check-no-residue` rc=0 |
| L1 / L2 / L3 全量 | 本归档任务**不跑**测试/构建（硬约束）；M15 期未做里程碑级全量重跑 ⇒ **无该期全量 rc 记录，不代填** |

## 4 MEMORY 摘录（M15 时期）

| 项目 | 内容 |
|---|---|
| 定位 | M15 = **ISA 语义结构化**：`spec/` 每条指令一段**可解析的 operation**，**不执行**（执行归 M17）；以 `riscv-unified-db` 的 IDL 为准，只在不合适处扩展，不自造新语言 |
| 12 册 IDL | `idl/SimRISC-01..12.idl`（**263** 条 operation，`m15-idl-001`–`012`）+ 语义库 v1（`013`）+ 浮点库 `idl/lib/fp.idl`（`015`–`017`） |
| 渲染 | `idl/render.py` 生成 `spec/` 内 IDL 块，`check-idl-sync` 逐字节守护；块布局改造为节末集中 + 三级标题（`m15-spec-005`） |
| 语言规范 | 迁入 `spec/IDL-ISA语义描述语言与语义库.md`（`m15-spec-006`；`idl/README` 428→22 行） |
| 与 UDB 差异 | 263 条逐条判定：一致 100 / 偏离 68 / 特有 95（`m15-idl-020`，`idl/diff-vs-udb.md`） |
| 发布 | SimRISC **0.5.7**（13 册去 `-rc`，清单 sha256，`m15-spec-008/009`） |
| 测试资产 | `ee-tiny`/`ee-user`/`ee-vast` 三执行环境资产集中；每 `.S` 一镜像（272）；装载统一 `set.rd`/`set.rb`/`set.fo`→`set.rf` |
| 基础设施 | refs 清空（活数据源迁 `tests/data/`）、`.manifests.toml` 第一波 + `components/` 目录防护、`CONFIG_DADAO_*` 钉子全集门控（13 脚本 × 15 符号 × 41 镜像） |
| picolibc | Tiny 地址图 + `.stack :NONE`（`m15-infra-009`）；`times()` 按 `SYS_TICKFREQ` 缩放（`m15-infra-010`，`ISS-502` 闭合） |

> 摘录自 `.tao/knowledge/MEMORY.md` 的 M15 事实行（混合了后续里程碑内容的行只摘 M15 部分或整行不摘）。活 `MEMORY.md` 已移除纯 M15 滚动行（历史由本目录承载）。

## 5 指针

- 里程碑定义/达成：本目录 `README.md §1/§2`；后续路线 `.tao/knowledge/milestones-m16.md`（M16）、`milestones-m17.md`（M17，IDL 可执行参考模型）、`milestones-m18.md`（M18）、`milestones-m19.md`、`milestones-m20.md`
- 里程碑回顾：本目录 `m15-retrospective.md`
- 关闭 issue 快照：本目录 `issues-closed.md`（1 条；`tools/infra/archive_issues.py --milestone M15 --check <快照>` 可复核）
- IDL 源与差异盘点：`idl/`（`.idl` 为源）+ `idl/diff-vs-udb.md`
- 遗留台账：`.tao/knowledge/issues.yaml`（M15 期 open 项已转 `M16`）、`.tao/knowledge/discussing.md`
- 归档规范：`docs/Process-04-里程碑归档规范.md`；门控：`tools/infra/check_archive.py`
- 跨文件引用说明：本归档**未更新**历史引用；凡引用 `.tao/tasks/**` 中 M15 任务书路径者（现存 1 处：`idl/diff-vs-udb.md` 指向 `m15-idl-020`），其内容现位于本目录（历史指针），修正归后续任务。
