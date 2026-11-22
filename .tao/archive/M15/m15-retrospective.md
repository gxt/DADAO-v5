# M15 回顾 — ISA 语义结构化（IDL v0 + 12 册 operation + 渲染/门控）

> **里程碑**：M15（2026-11-12 起，**2026-11-22 达成**）｜ **归档**：2026-11-22（`.tao/archive/M15/`）
> **性质**：本册是 M15 的**权威摘要**；任务细节在 `README.md §2` 指向的各任务书（本目录模块子目录）。
> **收口判据（用户 2026-11-20 确认）**：① **263 条 operation 全量**（`contracts/opcodes.yaml` 三处自洽）；② **12 册渲染逐字节一致**（`render.py --check`）；③ **`.idl` 全部 sha256 锁**（`idl/*.idl` 12 份 + `idl/lib/fp.idl`）。三条均于 2026-11-20 成立。

## 1 定位与边界（用户 2026-11-12/13）

**ISA 语义结构化**：把 `spec/` 升级为「每条指令一段**可解析的 operation**」，**不执行**（执行归 M17）。设计取向：以 `riscv-unified-db` 的 **IDL 为准**（`doc/idl.adoc`），优先复用其语法与工具（`idlc`、`yamlidl`），**只在不合适处扩展**，不自造新语言；执行方式为**边写边改**（先 5 条样板，语法随样板修正）。模块名统一 `idl`（`m15-idl-*`；首件 `m15-spec-001` 为命名前立册，保留 `spec` 前缀）。

## 2 交付推进

| 批 | 交付 | 代表任务 |
|---|---|---|
| 语义源与样板 | `idl/` 立为语义源（`.idl` + `render.py` 生成 `spec/` 块），5 条样板 + 4 路注入；伪指令正文分层 | `m15-spec-001`–`003` |
| 12 册 operation | `SimRISC-01`–`12` 全量 **263** 条（38/17/8/33/6/15/50/21/21/21/5/28），逐册带 30–96 检查项 | `m15-idl-001`–`012` |
| 语义库 | v1（`ip()` 64 位、cfx 访问/escape/fence、`ras_*`、`read/write/fetch_memory`、`raise`、`is_naturally_aligned`）；浮点库 `idl/lib/fp.idl`（`ft` 53 函数 → `fo`+remainder 105 函数 → `ft` 补正 108 函数 0 例外） | `m15-idl-013`、`015`–`017`、`019` |
| 语法与渲染收口 | 解码变量当内容用 7 处修正 + 注释记号统一 + 机械门控；`ftsclb` 改调库 `ft_scale`；IDL 差异盘点 263 条（一致 100/偏离 68/特有 95）；IDL 块布局改造（节末集中 + 三级标题） | `m15-idl-014`、`019`–`021`、`m15-spec-005` |
| 语言规范与发布 | 语言规范迁 `spec/IDL-ISA语义描述语言与语义库.md`；SimRISC **0.5.7** 发布（13 册去 `-rc`、变更记录按主题重排 21→5 组、清单 sha256）+ 发布投影 | `m15-spec-006`–`009` |
| 契约与渲染一致性 | `contract-fp` 对齐 spec（`scmp` 无序 canonical；11 处 sNaN 逐条处置） | `m15-spec-007` |
| 测试资产 | 每 `.S` 一镜像（904→272）；宏化三批（整例/结构重复/两行级，净省 553 行）；`ee-tiny`/`ee-user`/`ee-vast` 资产集中（51 mv + 7 bootrom + lds）；装载统一伪指令（`LOAD_ADDR`→`set.rb/set.rd` 528 处、`LD64` 168 处）；`scmp` 向量 canonical；Tiny 执行环境命名 `cfx_power_tiny`/`cfx_hmon_tiny` | `m15-testcases-001`–`023` |
| picolibc / ansibench | Tiny 地址图 + `.stack :NONE`（删 513 行 lds 副本）；`times()` 按 `SYS_TICKFREQ` 缩放；ansibench 四件 Tiny+picolibc 5/5 | `m15-infra-009/010`、`m15-testcases-023` |
| 基础设施 | 三契约消费点迁移（删 `machine-profiles`）；`refs/` 清空（13 份活数据源迁 `tests/data/`）；文件防护门控盘点；`.manifests.toml` 第一波；`components/` 目录防护；死引用收口；`CONFIG_DADAO_*` 钉子全集门控 | `m15-infra-001`–`008` |
| 三平台语义修正 | `scmp` 无序结果改 canonical quiet NaN（qemu/gem5/向量三处）；窄 `lr` 高位保持（qemu 9 载体 272/272、gem5 单测 30/30） | `m15-qemu-001/002`、`m15-gem5-001/002`、`m15-testcases-020` |

## 3 关键决策

- **IDL 来源**：以 `riscv-unified-db` IDL 为准、只扩展；`idlc`/Ruby **不进门控**（M17 执行器用 Python）。
- **寄存器模型（方案 C）**：四组数组 + `fo`/`ft` 视图；`ra` 逻辑栈序 + `ras_*`；`read_memory`/`write_memory`（无 `_be`）/`fetch_memory`/`raise(code,mode,addr)`/`is_naturally_aligned`。
- **渲染形态（2026-11-20 定）**：`spec/` 保持显示**原始 IDL 块**（`render.py` 逐字节生成、`check-idl-sync` 守护）；「格式化伪代码」只是候选，不实施，转 `discussing.md` 未决项。
- **锁与冻结**：`.idl`（12 册 + `idl/lib/fp.idl`）逐文件 sha256 入清单（N21，2026-11-20 收口，含新建 `idl/lib/.manifests.toml` 与目录注册）。
- **伪指令收口**：`set.ft/set.fo rf, rs` 合并为 `set.rf rf, rs`（LLVM 新助记符 + 载体改名 `pseudo_set.rf_reg.S`）。
- **测试装载口径**：一律用规范伪指令（`set.rd`/`set.rb`/`set.fo`）+ lds 统一 FP 布局。

## 4 终局证据（摘要；真实 rc 见 `README.md §3`）

- **收口判据**：263 条 operation 三处自洽；12 册渲染逐字节一致；`.idl` 全量 sha256 锁 —— 三条均于 2026-11-20 成立。
- **版本**：SimRISC **0.5.7**（根 `README.md` 版本表与 `archive/SimRISC-0.5.7` 快照）。
- **回归**：272/272 镜像行为一致（`m15-testcases-007`）；ansibench 四件 Tiny+picolibc 5/5（`023`）；`ftsclb` 11875 例 0 失配（`019`）。
- **归档门控**：`check-archive`、`check_issues`、`check-knowledge-refs`、`check-dirs`、`check-no-residue` 全 rc=0（本归档任务现跑）；`check-milestones-fresh` 的 M16 两条预估时间红为**既有基线**（非本任务），M15 已不在列表。

## 5 遗留与转交

- **转交 M16（open 项，`issues.yaml` 已改 `milestone: M16`）**：`ISS-504`（picolibc 自测 harness 的 `.done` 复用键在 qemu 引擎下 `sim_md5` 恒同 ⇒ 假绿）、`ISS-505`（`check-picolibc-tests fast pass=6` 是缓存复用导致的假绿，真实 18/2 口径）、`ISS-506`（`sysconf(_SC_CLK_TCK)` 仍返回 `SYS_TICKFREQ`=1e9，与 `times()` 缩放口径不一致）。
- **本里程碑关闭**：`ISS-502`（picolibc `clock()` 单位错 1000×，`m15-infra-010` 修 `times()` 缩放）。
- **未随本册关闭**：`ISS-507`（`check-patch-tree` 基线红，`milestone: null`，非 M15 项）。
- **未决项**：IDL 语言语义缺口 `U04`–`U10`（`discussing.md` N34，归 M17 待裁）；渲染形态与 `idlc` 取舍的讨论结论见 N16（已关闭）。

## 6 教训

1. **完成区为真 ≠ 交付物为真**：`m15-idl-001` 的守卫在「实现过、未提交即丢失」的 6 分钟窗口内蒸发，完成区当时为真而合入版没有守卫 ⇒ 对外事实以**合入版**为准，证据脚本须比对提交后的树（`m15-idl-020` 复盘）。
2. **两份语义源必漂移**：IDL 与 `spec/` 散文/契约三方必须机械对齐（渲染 + sha256 + 逐条差异盘点），否则「看起来一致」在盘点时批量暴露（263 条中偏离 68/特有 95）。
3. **假绿来自缓存**：picolibc 测试的 `.done` 复用键漏掉引擎/sim md5 ⇒ `pass` 计数虚高（`ISS-504/505`）；计数类判据须现场派生。
4. **资产集中的顺序有依赖**：`ee-*` 目录与链接 `-L` 并存（`011`/`012` 的 16 处链接冲突）需按「crt0/runtime/dadao-* → `ee-user`；`kaiwu-tiny*.lds` → `ee-tiny`」一次性解，避免逐批返工。
5. **门控判据按「名字子串」误判**：`check_spec_changelog` 的 `"SimRISC-" in rel` 被新册名 `IDL-SimRISC-*` 触发 ⇒ 谓词统一为 `Path(rel).name.startswith(...)`（`discussing.md` N32 记录追认状态）。
