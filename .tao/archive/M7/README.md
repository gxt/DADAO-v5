# M7 归档（Archive）

> **归档日期**：2026-10-13 ｜ **范围**：M7 里程碑（**picolibc 移植（自带 test）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle**）的全部任务书与相关记录。
> **状态（如实）**：**项目里程碑 M7 = 达成（2026-10-13）**——`SPEC-136m`/`INTEG-034m` 均置 `里程碑`（L3 `check-full` 已绿）；本归档为 **M7 收尾归档**。原「未达成（待 `ISS-201`）」为过时表述，见下行「更正说明」。
> **更正说明（2026-10-13，随 `归档补齐`）**：原文「**项目里程碑 M7 尚未标记『达成』**……`SPEC-136m`（模块里程碑）**未通过**（`ISS-201`）……**M7 达成待用户裁定**」⇒ **更正为「项目里程碑 M7 = 达成（2026-10-13）」**。理由：`AGENTS.md`「不得置里程碑」**只针对未处置的*跨模块*影响**；`ISS-201`（规范是否补记未定义弱符号**防御分支**）属 **spec 模块内 backlog**、**不阻断** ⇒ `SPEC-136m`/`INTEG-034m` 置 `里程碑`、项目 M7 达成。**用户指正原话**（2026-10-13）：「M7都已经归档了，你留着ISS-201是有什么意义？」
> **归档判据**：任务书字段 `**项目里程碑**：M7` 且状态终态（**40** 个 = `infra 16 / llvm 11 / qemu 3 / spec 5 / testcases 2 / integ 3`）；`milestones.md`「任务流水」M7 已终态行（**40** 条，见 §2）；`MEMORY.md` 纯 M7 行（**0** 行）；`issues.yaml` `closed` 项（**12** 条 = M7 期关闭 5 + M6 遗留台账收敛 7，见 `issues-closed.md`）。
> **范围说明（如实）**：**项目里程碑 M7 = 达成（2026-10-13）** ⇒ 归档上界 = **达成日 2026-10-13**（原「未达成 ⇒ 无机械界」表述随 2026-10-13 口径纠正失效）；范围 = 「M7 期 = 开启日 2026-10-11 ~ 达成/归档日 2026-10-13」。
> **未归档（仍留 `.tao/tasks/`）**：**仅** `infra/INFRA-071t`（`待开始`，**项目里程碑已改标 `M8`**〔用户 2026-10-13 裁定〕，待用户授权 3 项，见 §4）。`SPEC-136m`/`INTEG-034m`/`INTEG-035m` 均已归档入本目录（见 §1）；`INTEG-028t` 属 `M6` 范围、已补入 `.tao/archive/M6/`（见 §4）。
> **说明**：本目录是**历史归档**，不再活跃；权威摘要见本目录 `m7-retrospective.md`，路线/未决项见 `.tao/knowledge/milestones.md`。

## 1. M7 任务清单（40，按模块）

| 模块 | 数量 |
|---|---|
| infra | 16 |
| llvm | 11 |
| qemu | 3 |
| spec | 5 |
| testcases | 2 |
| integ | 3 |

> 任务书位于同目录下 `infra/` `spec/` `llvm/` `qemu/` `testcases/` `integ/` 子目录（`git mv` 保留 `R` rename 历史）。
> **特别项**：`integ/INTEG-035m`（**本归档任务自身**）按 `Process-04 §4.1` 末条**已自归档**入本目录 `integ/`（2026-10-13，`归档补齐`；状态已置 `里程碑`）。
> **未归档（仍留 `.tao/tasks/`，见 §4）**：**仅** `infra/INFRA-071t`（`待开始`，**已改标 `M8`**，待用户授权 3 项）。

## 2. 任务流水与实质改动（M7 时期，2026-10-11 ~ 2026-10-13，40 条）

> 原样搬入 `.tao/knowledge/milestones.md`「任务流水」的 M7 **已终态**行（**40**，含各模块 `m`）；每格单行。M7 期**未决** 1 行（`INFRA-071t`〔**已改标 `M8`**〕）仍留活表。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| INTEG-033k | 已验证 | 2026-10-11 14:46 | M7 启动与任务分解（10 条裁定） |
| INFRA-055t | 已验证 | 2026-10-11 13:53 | 接入 picolibc 组件 |
| INFRA-056t | 已验证 | 2026-10-11 18:43 | 接入 clang++（软链）+ 核 2 个 .cpp 需求 |
| INFRA-057t | 已验证 | 2026-10-11 21:16 | picolibc 移植与构建集成（build-picolibc + printf E2E） |
| INFRA-058t | 已验证 | 2026-10-11 16:04 | 门控分层 + check-spec-refs 修复 |
| INFRA-060t | 已验证 | 2026-10-11 17:02 | 目录三分界 + 规范版本号 |
| INFRA-061t | 已验证 | 2026-10-11 17:32 | changelog 并入 milestones |
| INFRA-062t | 已验证 | 2026-10-11 18:10 | MEMORY 改纯指针页 |
| INFRA-063t | 已验证 | 2026-10-11 20:14 | 规则与台账分工收敛（AGENTS 瘦身 / lessons 精简） |
| INFRA-064t | 已验证 | 2026-10-11 22:21 | 入口文档分工收敛（README 瘦身 / 规则上移 AGENTS / 导航归 MEMORY） |
| INFRA-065t | 已验证 | 2026-10-12 23:03 | 子代理 workdir 作用域（规则层 ✅）+ 权限层 = **agent frontmatter `external_directory` deny**（**当前服务下未生效 ⏳**，待服务重启复验；`ISS-199`）；`experimental.policies` 已撤销 |
| INFRA-066t | 已验证 | 2026-10-12 00:49 | 恢复 picolibc `libm`（删整目录过滤；41 条最小集 + `ISS-193`；`libc.a` 1.24→1.69 MB） |
| INFRA-067t | 已验证 | 2026-10-12 18:01 | 提供 `__muldc3`/`__mulsc3`（移植 compiler-rt 单文件；`libc.a` 两符号 `T`；pass 197→203 / blocked 16→10；解锁 6） |
| INFRA-068t | 已验证 | 2026-10-12 20:21 | `setjmp`/`longjmp` 真实现（RA 存取/块赋值；`_JBLEN` 161；pass 203→205 / blocked 10→8；解锁 2：`test-setjmp`、`test-double-free`） |
| INFRA-069t | 已验证 | 2026-10-12 23:57 | LLVM 组件 changelog 补齐（现场统计缺口 9 条）+ 三检查（isa-coverage/spec-numbering/spec-changelog）并入 L1 |
| INFRA-070t | 已验证 | 2026-10-13 00:47 | `.tao/knowledge/` 顶层收拢（立 `docs/Process-07-门控分层规范.md` + 9 文件处置 + 白名单门控 `check-knowledge-dir`）；**Phase B（`contract-*.md`→`contracts/`）转 `INFRA-071t` 待用户授权** |
| LLVM-079t | 已验证 | 2026-10-11 23:07 | P0 后端补齐（f32→f64 载入/setcc/bitcast/select_cc/cttz 五类 ISel；convert_ff 早写约束） |
| LLVM-080t | 已验证 | 2026-10-12 00:11 | P1 后端补齐（取整六项/fmin-fmax libcall；fabs-copysign 用 ISA `fosgnj`） |
| LLVM-081t | 已验证 | 2026-10-12 01:12 | ISA↔后端覆盖矩阵（生成式两层分列；227 条，①受理 217/②ISel 86；缺口 141） |
| LLVM-082t | 已验证 | 2026-10-12 08:08 | 后端欠账收口（数据指导符唯一集 §7.1 全量收口 + 大小写洞 + 尾调用按裁定 A 登记） |
| LLVM-084t | 已验证 | 2026-10-12 10:00 | FP 无序谓词收口（`ISS-193`(a)：`SETUO`/`SETO`/`SETONE`/`SETUEQ` + don't-care 码 lowering）；删 30 条源过滤（41→11） |
| LLVM-085t | 已验证 | 2026-10-12 12:00 | 未定义弱函数 PC 相对引用可链接（REL26 自循环 + `call`→`jump`）；picolibc pass 152→174 / blocked 65→39 |
| LLVM-086t | 已验证 | 2026-10-12 13:00 | 内联汇编 `"r"` 约束解锁（`ISS-193`(e)）：`getRegForInlineAsmConstraint` 只映射 `"r"`→GPRD + picolibc 过滤表删 (e) 两条；picolibc pass 174→176 / blocked 39→37 |
| LLVM-087t | 已验证 | 2026-10-12 14:02 | f32 取整/极值 libcall 注册（`ISS-193`(b)：`RTLIB::{FLOOR,CEIL,TRUNC,ROUND,RINT,NEARBYINT,FMIN,FMAX}_F32`）+ 过滤表删 (b) 四条；picolibc pass 176→182 / blocked 37→31（解锁 6） |
| LLVM-088t | 已验证 | 2026-10-12 15:09 | 截断存储 `trunc f64→f32`（`ISS-193`(d)：`setTruncStoreAction(f64,f32,Expand)`）+ 过滤表删 (d) 两条；picolibc pass 182→196 / blocked 31→17（解锁 14） |
| LLVM-089t | 已验证 | 2026-10-12 16:46 | f32 `log` libcall 注册（`ISS-193`(b) 残余：`RTLIB::LOG_F32`→`logf`）+ 过滤表删最后一条 (b) `sf_log10.c`；picolibc pass 196→197 / blocked 17→16（解锁 1：`test-log10`） |
| QEMU-056t | 已验证 | 2026-10-11 19:34 | RAM 基址改 cfx63 段（QEMU/tests/tools/spec 同步） |
| QEMU-058t | 已验证 | 2026-10-12 21:26 | NaN 2-NaN 规则设 `float_2nan_prop_ab`（宿主机 SSE 实测）；picolibc pass 205→213 / blocked 8→0（解锁 8，`ISS-195`） |
| SPEC-131t | 已验证 | 2026-10-12 01:21 | 过渡 oracle 与 semihosting 口径 |
| SPEC-133t | 已验证 | 2026-10-11 22:09 | 21 册标题章节号统一与引用同步 |
| SPEC-134t | 已验证 | 2026-10-12 02:12 | 21 册「附录：版本与变更记录」+ `-rc` 版本口径 + `spec/README.md` 册维护约定 |
| SPEC-135t | 已验证 | 2026-10-13 00:18 | 未定义弱符号口径固化（`ADR-0019` 就地追加 `D9` + `contract-elf §3.3` 正文） |
| TESTCASES-042t | 已验证 | 2026-10-12 03:29 | picolibc 自带 test 接入 |
| INFRA-072m | 里程碑 | 2026-10-13 02:00 | M7 infra 模块里程碑核验（6 模块 `m` 之一） |
| LLVM-090m | 里程碑 | 2026-10-13 01:32 | M7 llvm 模块里程碑核验 |
| QEMU-059m | 里程碑 | 2026-10-13 01:50 | M7 qemu 模块里程碑核验 |
| SPEC-136m | 里程碑 | 2026-10-13 07:04 | M7 spec 模块里程碑核验（4 条口径均达成；`ISS-201` 为模块内 backlog，**不阻断**） |
| TESTCASES-043m | 里程碑 | 2026-10-13 01:13 | M7 testcases 模块里程碑核验（含用户裁定「记为达成」+ 现场四数） |
| INTEG-034m | 里程碑 | 2026-10-13 07:04 | M7 integ 模块里程碑核验（整体收敛点；L3 `check-full` 已绿；**项目 M7 = 达成**） |
| INTEG-035m | 里程碑 | 2026-10-13 03:16 | M7 归档与回顾（`Process-04`；**本归档任务自身**） |

## 3. MEMORY 摘录（M7 时期）

> `MEMORY.md` **无纯 M7 行**（`Process-04 §4.3` 判据）——`INFRA-062t`（2026-10-11）后该页为**纯指针页**；本次仅同步其「入口指针」表内归档指针（见 §4）。

## 4. 指针

- 里程碑定义/达成：`.tao/knowledge/milestones.md`
- 里程碑回顾：本目录 `m7-retrospective.md`（含 §7 **待用户裁定 / 操作清单**；**注**：该文件为**归档时快照、不再更新**——其 §1.2「M7 尚未标记『达成』」/§7 相关表述随 2026-10-13 口径纠正而**失效**，以本 `README.md` 头部「更正说明」为准）
- 台账快照：本目录 `issues-closed.md`（M7 阶段 closed **12** 条）
- M7 期补充记录：本目录 `notes/`（`gate-tiering-design.md`/`embench-analysis.md`/`LLVM-070t-rootcause.md`/`SPEC-129t-count-table.md`/`INTEG-027t-report.md`）
- 遗留台账：`.tao/knowledge/issues.yaml`（issue/待决）、`.tao/knowledge/lessons.md`（教训/方法论/过程记录）
- 任务流水（之后）：`.tao/knowledge/milestones.md`「任务流水」（M7 未决项**仅** `INFRA-071t`〔**已改标 `M8`**〕）
- **跨文件引用说明**：本归档**未更新**历史引用（`Process-04 §6`）；凡引用原 `.tao/tasks/<module>/<task>.md` 的 M7 任务书者，其内容现位于本目录 `<module>/`（历史指针）。
- **`INTEG-028t` 说明**：该任务书 `**项目里程碑**` 字段为 **`M6`**（收尾遗留收口），不符合 M7 判据 ⇒ **未归档至 M7**；已按 M6 历史遗漏回溯**补入 `.tao/archive/M6/integ/`**（2026-10-13，`归档补齐`）。
