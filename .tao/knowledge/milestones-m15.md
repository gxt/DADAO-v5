# 项目里程碑

> **项目里程碑 = M15**（M15 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M12/M13/M14 各另有分册）

> **本页只维护 M15 任务台账**：M11 及以前已归档（`.tao/archive/M11/`）；历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **模块名（用户 2026-11-13）**：M15/M17 统一用 `idl` 模块（`m15-idl-*` / `m17-idl-*`）。首件 `m15-spec-001` 是命名前立册，保留 `spec` 前缀不迁移。

> **收口判据（2026-11-20 确认）**：1) **263 条 operation 全量**（`contracts/opcodes.yaml` 三处自洽）；2) **12 册渲染逐字节一致**（`render.py --check`）；3) **`.idl` 全部 sha256 锁**（`idl/*.idl` 12 份 + `idl/lib/fp.idl`，`check-manifests-guard` 双向 + 校验）。三条均已于 2026-11-20 成立。
> **渲染形态（2026-11-20 定）**：保持现状——`spec/` 里显示**原始 IDL 块**（`render.py` 逐字节生成、`check-idl-sync` 守护）；「格式化伪代码」只是候选，不实施，转 `discussing.md` 未决项。

> **M15 定位（用户 2026-11-12/13）**：**ISA 语义结构化**——把 `spec/` 升级为「每条指令一段**可解析的 operation**」，**不执行**（执行归 M17）。**设计取向（用户 2026-11-13）**：以 `riscv-unified-db` 的 **IDL 为准**（`doc/idl.adoc`），优先复用其语法与工具（`idlc`、`yamlidl`）；**只在不合适处扩展**，不自造新语言。执行方式：**边写边改**（先 5 条样板，语法随样板修正）。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

- **派单即移入**：「待开始」表 = 尚未派单；**派单时**把该行移入「进行中」表并填**派单时间**。
- **派单时间**：`YYYY-MM-DD HH:MM`。
- **预估时间**：`N h` / `N–M h` / `N 天` / `N–M 天` / `N min`。
- **完成时间**：`YYYY-MM-DD HH:MM`；「已验证」表按完成时间**倒序**。
- **一句改动**：≤120 字符。

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m15-integ-001 | 1–2 h | M15 归档（**暂停**：先修 Tiny 测试脚本/bootrom，争取排在 M14 之后） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m15-testcases-021 | 2026-11-20 22:29 | 6–8 h | 测试资产伪指令收口：`LOAD_ADDR`→`set.rb`（100 文件/533 处）、`LD64`→`set.rd`，删两个 `.inc` |


## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m15-spec-009 | 2026-11-20 23:12 | SimRISC 0.5.7 发布投影（README 版本表、契约版本头与引用、`archive/SimRISC-0.5.7` 快照） |
| m15-spec-008 | 2026-11-20 22:44 | SimRISC 0.5.7 发布（13 册去 `-rc`；变更记录按主题重排 21→5 组；清单 sha256） |
| m15-gem5-002 | 2026-11-20 16:16 | 窄 `lr` 高位保持（`exec/b6.cc` 切片写；单测 30/30、12 检查点逐字节） |
| m15-qemu-002 | 2026-11-20 16:14 | 窄 `lr` 高位保持（`store_rd_narrow`；9 载体期望订正 + case-ledger；272/272） |
| m15-idl-021 | 2026-11-20 16:05 | IDL 修复批（D1 `jump` 写 64 位；D2 8 条 rf 对齐守卫；补回丢失守卫；清 spec-006 遗留） |
| m15-spec-006 | 2026-11-20 15:37 | IDL 语言规范迁 `spec/IDL-ISA语义描述语言与语义库.md`（`idl/README` 428→22 行） |
| m15-idl-020 | 2026-11-20 13:02 | IDL 差异盘点（263 条；一致 100/偏离 68/特有 95；D1/D2 应改 IDL） |
| m15-spec-005 | 2026-11-20 10:52 | IDL 块布局改造（节末集中 + 三级标题 + 导语；12 册散文零改动） |
| m15-idl-019 | 2026-11-20 09:08 | `ftsclb` 改调库 `ft_scale`（260 个 n 下溢→溢出=修 bug；等价 11875 例 0 失配） |
| m15-testcases-020 | 2026-11-20 00:05 | `scmp` 无序向量改 canonical（18 检查点/144 B 双 lane 0；死宏与旧口径清理） |
| m15-qemu-001 | 2026-11-19 23:10 | `scmp` 无序结果改 canonical quiet NaN（QEMU 侧；20/20 含可达 FAIL） |
| m15-idl-007 | 2026-11-19 21:40 | `SimRISC-07` 全册 50 条（±0 相等修复、scmp canonical、oracle 特殊值池；93/93） |
| m15-spec-007 | 2026-11-19 21:25 | `contract-fp.md` 对齐 spec（scmp 无序 canonical；11 处 sNaN 逐条处置） |
| m15-gem5-001 | 2026-11-19 21:05 | gem5 `scmp` 无序结果改 canonical quiet NaN（`check_b7` 3946 vectors） |
| m15-idl-017 | 2026-11-19 18:02 | ft 族补正（tininess 后判、类型缺陷、i32/u32→fo、ft_scale；108 函数 0 例外） |
| m15-idl-016 | 2026-11-19 17:20 | 浮点库 fo 族 + remainder（105 函数；oracle 30698 例） |
| m15-idl-015 | 2026-11-19 13:00 | 浮点语义库 ft 族 53 函数（`idl/lib/fp.idl`；oracle 10478 例） |
| m15-infra-008 | 2026-11-19 12:52 | CONFIG_DADAO_* 钉子全集门控（13 脚本×15 符号×41 镜像；C2 逃逸口） |
| m15-idl-014 | 2026-11-19 12:05 | 解码变量 7 处代码修正 + 04/08/09 注释 61 处统一记号 + 门控 |
| m15-idl-008 | 2026-11-19 11:40 | `SimRISC-08` 21 条 operation（sem 改从 `.idl` 取语句；155 条/10 册） |
| m15-idl-001 | 2026-11-19 11:25 | `SimRISC-01` 38 条 operation（rf 对齐按裁定、静态先；68/68） |
| m15-idl-009 | 2026-11-19 11:23 | `SimRISC-09` 21 条 operation（shamt 取内容低 4 位；96 条/10 册一致） |
| m15-idl-004 | 2026-11-19 11:04 | `SimRISC-04` 33 条 operation（52/52、18 路反例） |
| m15-idl-012 | 2026-11-19 10:53 | `SimRISC-12` 28 条 operation（sc 用 `store_conditional`；lr 窄读只写低位；83/83） |
| m15-idl-006 | 2026-11-19 10:44 | `SimRISC-06` 15 条 operation（call/ret 走 `ras_*`；52 检查项） |
| m15-idl-010 | 2026-11-19 10:44 | `SimRISC-10` 21 条 operation（`rev.b` 逐块反转；62/62） |
| m15-idl-002 | 2026-11-19 10:43 | `SimRISC-02` 17 条 operation（cs.* 条件按 §3.2 位级；38/38） |
| m15-idl-011 | 2026-11-19 10:06 | `SimRISC-11` 5 条 operation（escape/cfx2rd/cfx2rc/fence 按语义库 v1；37/37） |
| m15-idl-003 | 2026-11-19 09:52 | `SimRISC-03` 8 条 operation（wyde 切片写；30/30、384 向量） |
| m15-idl-005 | 2026-11-19 09:42 | `SimRISC-05` 6 条 operation（`aip.si` 用 `ip()`；13/13、4 路注入） |
| m15-idl-013 | 2026-11-19 09:14 | 语义库 v1（`ip()` 64 位、cfx 访问/escape/fence、rf 专用表述）；T1–T7 落地 |
| m15-testcases-018 | 2026-11-19 03:05 | gem5 lane 补 `--semihost on`（`run_inst_tiny`/`check_tiny_hmon`/`run_parity --direct-check`；21/21、42/42） |
| m15-testcases-019 | 2026-11-19 02:15 | 11-cfx 链例12 SRAM 哨兵显式清零（chipyard TLRAM 上电非 0；双 lane 96 B 相同） |
| m15-spec-001 | 2026-11-19 00:38 | ISA 语义源迁 `idl/`（`.idl` 为源 + `render.py` 生成 spec 块；5 条样板、4 路注入） |
| m15-testcases-017 | 2026-11-18 23:11 | RF 窄写补测（`ld.t`/`ldm.t` 高 32 位保持）+ 11-cfx 两载体按新 escape 语义（272/272） |
| m15-infra-007 | 2026-11-18 19:02 | 死引用收口（台账改自动发现、删退役 `check_005t_coverage`；NON_LIVE 11→3） |
| m15-infra-006 | 2026-11-18 18:44 | `components/` 目录防护（8 目录 + `[subdir_owners]`；新增目录须用户同意） |
| m15-infra-005 | 2026-11-18 16:05 | `.manifests.toml` 第一波（spec/.tao/.tao-knowledge + 必需清单注册表；删清单/删注册表/游离清单即红） |
| m15-infra-002 | 2026-11-18 11:42 | refs 清空（9 孤儿删除；其余 20 份由 004 承接：迁 13 + 删 7） |
| m15-infra-004 | 2026-11-18 11:42 | refs 13 份活数据源迁 `tests/data/` + refs 清空 + `check_dead_refs`（未接门控） |
| m15-infra-003 | 2026-11-18 11:09 | 文件防护门控盘点（64 行清单 + 缺口：spec 新增册逃锁 / 6 目录无白名单） |
| m15-testcases-016 | 2026-11-18 10:01 | `tests/ee-*` 统一 `<role>_<ee>`（51 mv + 删 `k0_README`；272/272、k0 101/101） |
| m15-infra-001 | 2026-11-18 09:00 | 三契约消费点迁移（machine_profile 拆读 machine/exec-envs/tests-matrix + `ee-*/runtime.yaml`；删旧 machine-profiles） |
| m15-testcases-015 | 2026-11-18 08:27 | 剩余 bootrom：`k0_*` 7 件 → `tests/ee-vast/`、4 散件 → `tests/ee-tiny/`（k0 101/101、k0/k1 119/112） |
| m15-testcases-014 | 2026-11-18 07:30 | `inst-tiny.lds` 移入 `tests/ee-tiny/`（202 .S 头注释同步；272/272） |
| m15-testcases-013 | 2026-11-18 07:05 | vast 资产集中到 `tests/ee-vast/`（step5 bootrom 7 + kaiwu-vast.lds；md5 8/8） |
| m15-testcases-012 | 2026-11-18 06:41 | user 资产集中到 `tests/ee-user/`（12 脚本 + 5 crt/lds/runtime；与 011 双 `-L` 并存） |
| m15-testcases-011 | 2026-11-17 23:33 | tiny 资产集中到 `tests/ee-tiny/`（4 脚本 + 10 bootrom + 3 lds；272/272、bootrom md5 不变） |
| m15-testcases-010 | 2026-11-17 21:51 | 01 册 38 文件：opc 0x16→0x20、boundary 正/负/全1、rb0 imm 负/零/正；272/272 |
| m15-testcases-009 | 2026-11-17 08:56 | 「一例一镜像」→「每 `.S` 一镜像」（209 文件 248 行注释 + 6 文档）；`__PRINT` 零长硬化双保险（注入必红 rc=124） |
| m15-testcases-007 | 2026-11-17 07:47 | 故障例链式合并（`.faulttab`+哨兵；904→272 镜像；271/271 行为与 meta 全等） |
| m15-testcases-006 | 2026-11-16 22:55 | 装载一律用规范伪指令（set.rd/set.rb/set.fo）+ lds 统一 FP 布局；行为等价 A′↔C 903、A↔A′ 899，差异均为地址/布局类 |
| m15-testcases-008 | 2026-11-16 21:53 | 退役 clmul C/IR 探针（删 7 文件 −2528 行；yaml 472；L3 成员 4→3 + `check_l3_report` 现场派生） |
| m15-testcases-005 | 2026-11-16 20:56 | 2 行级结构重复宏化（净收益>0 + S9 门控；净省 553 行/569 处；`__RF_`→`__PREP_`） |
| m15-testcases-004 | 2026-11-16 18:17 | 整例宏化（`__PT_` 前缀 + 台账身份 + S6/S7/S8 防藏；`sc.*` −38%、rf2rf 回退） |
| m15-spec-003 | 2026-11-16 14:55 | `set.ft/set.fo rf, rs` → `set.rf rf, rs`（两册表 8→7、LLVM 新助记符 + 5 负例、载体改名 `pseudo_set.rf_reg.S`） |
| m15-testcases-003 | 2026-11-16 12:03 | 文件内结构重复段宏化·试点（7775→5850 行 −24.8%；册宏 6+文件内 3；A1–A6 81/81、点号 30/30） |
| m15-spec-002 | 2026-11-16 11:15 | 伪指令正文分层（`SimRISC-00 §5` 130→19 行表格化；`Toolchain-01 §6.2` 逐条语义原文迁入；删原 §6.2；4 册锁重算） |
| m15-testcases-002 | 2026-11-16 11:00 | 汇编宏作用域下沉（共享层 132→24 宏/2134→661 行；7 册 .inc 75 宏；18 单文件宏；删 15 死宏；`check-inst-macro-scope`） |
| m15-testcases-001 | 2026-11-15 21:30 | `tests/inst` 载体汇编宏去重下沉（10 宏入共享层、8 文件删 32 处重复定义，镜像 904/904 不变） |
