# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..6>/m<i>-retrospective.md`。
>
> **M6 达成（2026-10-11，architect 实测核验）**：门槛 `make check` **EXIT=0** + **opt-in** `make test-m6` **EXIT=0**（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）；6 个模块 `m` 全置 `里程碑` ⇒ **项目里程碑 M6 = 达成**。M6 任务书/回顾/已关 issue 已归档至 `.tao/archive/M6/`（回顾 `m6-retrospective.md`、清单 `README.md`、快照 `issues-closed.md`）。核验命令/证据见各 `m`「核验」与 `.work/log/integ/INTEG-026m-*.log`。

## 项目里程碑

> 项目里程碑（M1–M6 及达成日/主题/成就）见 README.md「项目里程碑」。

**M6 模块里程碑**（均已 `里程碑`）：`INFRA-052m` / `SPEC-125m` / `LLVM-067m` / `QEMU-054m` / `TESTCASES-040m` / `INTEG-026m`。

**M7 模块里程碑**（规划，均 `待开始`）：`INFRA-072m` / `SPEC-136m` / `LLVM-090m` / `QEMU-059m` / `TESTCASES-043m` / `INTEG-034m`（整体收敛点）+ `INTEG-035m`（M7 归档，`Process-04`）。

## 任务流水

> 本表 = **当前里程碑（M7）**逐任务一行。**细则**：列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**每格单行**（不换行）；`状态` 取值 = `待开始` / `待验收` / `待返工` / `已验证`（`m` 行另用 `里程碑`）；`完成时间` = 该任务**落地提交时间**（`git log --format='%h %ci'` 现场取证，**精确到分钟 `YYYY-MM-DD HH:MM`**），`待开始` 行写 `—`；`一句改动` ≤1 行、只留摘要，**细节指针到各任务书**。**新立任务（任务书落盘）时即加 `待开始` 行**（不等到开工/落地），使队列始终可见。
> M6 的 **46** 份任务流水（含实质改动）已随归档移入 `.tao/archive/M6/`（清单见 `.tao/archive/M6/README.md §1`）；M7 任务分解 `INTEG-033k` 已建立，逐任务流水见下表（按各模块现有最大号递增）。

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
| INFRA-071t | 待开始 | — | `contract-*.md`→`contracts/`（Phase B）+ `check-contracts-dir` 白名单门控（**待用户授权 3 项**：只读锁册 / `contracts/` 内嵌字段 / 扩到 `tools`·`components`·`tests`） |
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
| SPEC-136m | 待开始 | — | M7 spec 模块里程碑核验（**未通过：`ISS-201` 待用户逐条确认**） |
| LLVM-090m | 里程碑 | 2026-10-13 01:32 | M7 llvm 模块里程碑核验 |
| QEMU-059m | 里程碑 | 2026-10-13 01:50 | M7 qemu 模块里程碑核验 |
| TESTCASES-043m | 里程碑 | 2026-10-13 01:13 | M7 testcases 模块里程碑核验（含用户裁定「记为达成」+ 现场四数） |
| INTEG-034m | 待开始 | — | M7 integ 模块里程碑核验（整体收敛点；L3 `check-full`） |
| INTEG-035m | 待开始 | — | M7 归档与回顾（`Process-04`） |

## 当前进度

- **里程碑**：M6（**达成 2026-10-11**）；**M7 规划启动**（`INTEG-033k`，`已验证`；任务分解见该 `k`）。
- **M6 遗留（M6→M7，均已登记 = 已处置）**：
  - `ISS-187` 窄位指令利用不足（8/16/32 位算术未用；`mul32` 用 `mul.uo` 而非 `mul.ut`）——**M7 优化候选，非缺陷**（用户 2026-10-10「先只登记，暂不改」）；指针 `.tao/knowledge/issues.yaml`（`ISS-187`）。
  - `ISS-188` FP 完备性缺口（`fcmp` 取值 / `fabs`/`frem`/`copysign` / `fma`/`fminnum`/`fmaxnum`/`floor`/`ceil`/`round`/`trunc` / `fpclass` / `f16` / `bitcast`(FP↔RD)；**全部显式失败、不产错码**）——**M7**；指针 `.tao/knowledge/issues.yaml`（`ISS-188`）。
  - `ISS-189` 其它 LLVM 内建数据指导符（`.2byte/.4byte/.8byte/.value/.int/.dc.b/.single/.double` 等）仍被 `llvm-mc` 受理——裁定口径外的剩余面（未授权扩大）；**M7** 按 `spec/Toolchain-01 §7` 唯一集口径收口；指针 `.tao/archive/M6/llvm/LLVM-078t-*.md`「遗留问题」。
  - `check-spec-refs` 1 违规（`contract-asm.md` 引 `Toolchain-01 §7.2` 被误判「无引用」）——根因 = `SPEC_PREFIX_MAP` 不认 `Toolchain-01`、匹配器 `_TEXT_LEAD_IN` 不含数值节号；**M7** 立 `tools/infra` 任务（补前缀映射 + 改数值节号解析；仅补前缀会把 1→91）。
  - `components/qemu/README.md:10` 旧述（「规模（2026-09-23 M1 重整后）：31 份 = 新增 25 + 修改 6」；实为 **34**）——**M7** 随补丁规模刷新。
  - `LLVM-074t` 遗留：`tailjmp` 不参与 `BranchRelaxation` ⇒ 远距离尾调用由 `lld` 报 relocation overflow（**非静默**）；栈实参/变参尾调用未优化（可选增强）——**M7**；指针 `.tao/archive/M6/llvm/LLVM-074t-*.md`。
  - `ISS-108`（`DADAOInstrInfo.td` 1502 行 / `DADAOAsmParser.cpp` 2349 行）未拆分——**M7**（用户 2026-10-09 裁定推迟；**非功能性重构**）。
  - `ISS-164`（cfx mask 屏蔽路径不可观测）、`ISS-074`（`cs.*` 条件赋值 overlap 语义未定）、`ISS-167`（`DADAO-12 §5` prose 与伪代码张力，须授权改上游只读册）——**挂账**（按既有裁定，待相应实现/授权时定）。
  - **台账待收敛**：`ISS-043`/`045`/`138`/`148`/`156`/`159`/`162` 七条由 M6 任务完成区**声称已修/已收口**，但 `issues.yaml` 中 `resolved_by` 未回填、仍 `open`——**M7** 归档前置 `Process-04 §3` 梳理时回填 `closed`（或经用户裁定）；指针 `.tao/archive/M6/issues-closed.md`「待收敛」。
    - **已收敛（`INTEG-028t`，2026-10-11）**：7 条已逐条独立核实为「已修（可关）」并回填 `resolved_by` + `closed`（活台账 17 open / 7 closed，`check_issues` rc=0）；指针 `.work/log/integ/ISS-reconcile.md`、`.tao/tasks/integ/INTEG-028t-待收敛issue核实回填.md`。
- **规划中（M7 起，跨里程碑）**：
  - **门控分层（用户 2026-10-09 裁定）——推迟到 M7**：三层 = **L1 完整性/可用性**（默认 `make check`，秒~几十秒）/ **L2 各模块功能代表集**（几十~几百秒）/ **L3 较完整**（几百~几千秒）+ **模块完整按需**；落地要点 = `check` 收缩为 L1（`check-qemu-semantics` 移出 + 新增 `check-qemu-smoke` 机械派生代表集）、每层须「能失败 + 结构断言」、触发点写 `AGENTS.md`；**第 0 步 = 逐门控计时**。**已立项 `INFRA-058t`**（`INTEG-036t §收口核对`，2026-10-11）。**追加（用户 2026-10-11「认 + 并入 `INFRA-058t`」）**：`.work/log/` **四分类判据**（`spec/`=规范正文／`.tao/knowledge/`=结论·设计·口径〔含长文〕／`.work/log/`=一次性过程〔可删〕／**被引用材料不得只放 `.work/`**）落 `AGENTS.md` + 新增门控 **`check-knowledge-refs`**（扫 `.work/**` 引用、悬空即红）+ **被引用材料搬迁升格**（详见 `INFRA-058t §追加范围`，`INTEG-037t`）。**分层明细**见 `docs/Process-07-门控分层规范.md`（`INFRA-070t` 落地；原设计稿已归档 `.tao/archive/M7/notes/gate-tiering-design.md`）。
  - **`GOLDEN-*` 里程碑候选（M7 起，用户 2026-10-09 裁定）**：为 **golden model（结果级 / FP 独立 oracle）另立** `golden` 模块专用里程碑——承载 `ISS-019`（结果级 / FP 独立 oracle）、`ISS-026`（encoding `imm` 语义守卫依赖 golden）二者整体，以及 `ISS-081` 拆分后的 FP 独立 oracle 部分（`ISS-081` 的 FP 向量 / harness RF 部分**已在 M6 交付**：`LLVM-066t`/`TESTCASES-036t`/`041t`）。**仅登记归属，不在本轮立项**。
  - **GP（`rbgp`）候选（M7/优化期，M6 不做——用户 2026-10-09 裁定）**：`rb2=rbgp` 现由 M6 寄存器重排（`SPEC-128t`）列为 **reserved**；启用需：小数据区（`.sdata/.sbss` + 阈值）× 链接脚本聚到 `_gp` × 启动设 `rb2=_gp` × 后端 `getGlobalBaseReg`；**reloc 已备**——`ABS12`（基址 `rb1–rb63` 相对、字节）恰为 GP 相对所需、访存偏移 ±2 KiB = 小数据区自然上限。代价：**改变 `rb2` 的 ABI 语义**（独立裁定）。
  - **`lessons.md` 瘦身**：**已执行**（`INFRA-063t`，2026-10-11）——判据层保留、过程叙事删/迁 `.tao/archive/`、按触发时机分 4 节；新增条目口径见 `lessons.md` 文件头（**不设行数/条数上限**，「关键是精简」）。
  - **目录三分界与规范版本号（用户 2026-10-11 裁定）**：`docs/` = 工程流程规范（`Process-0x`）+ 索引 + `DDLN/`（**给别人看**）；`.tao/knowledge/` = 结论/设计/口径（**给自己看**）；`.work/log/` **非默认落点**；`Process-0x` **迁入 `docs/`**、`Process` **不设版本号**；`Toolchain-01`/`Machine-01` **设 `0.x.y` 版本号**（`x=0`；大改 `y+1`、小改 `z+1`）+ 文末 changelog（不用表格、不写“依据”）；`docs/` 6 个过期文件**可删**。**草案任务书**：`.tao/tasks/infra/INFRA-060t-目录三分界与规范版本号落地.md`（**待用户逐条裁定**后方写 B 段版本号）。
  - **M7 主题（`INTEG-033k` 裁定，2026-10-11）**：M6 已交付「整数完整调用约定 + 欠账收口 + ELF 直载 + clang target + Embench」；M7 主题 = **picolibc 移植（自带 test 100%）+ FP 后端完备（P0/P1）+ ISA↔后端覆盖矩阵 + 过渡 oracle**（见下「M7 裁定」；`Process-04 §1`，INTEG 开闭）。
  - **`ISS-193`(a) 类：无序谓词 `SETO`/`SETUO`/`SETUNO`（30/41 过滤条目）**——单独立 LLVM 任务可一次删 30 条过滤；**待用户裁定是否于 M7 内做**（`INFRA-066t` 收尾登记候选）。
  - **`LLVM-081t` 矩阵 `--check` 纳入门控**（生成投影漂移防护，`lessons §2.11`）——`--check` 现已可对「矩阵与真源不一致」报 FAIL，但未进门控；**待排期**。（**已由 `INFRA-069t` 落地，2026-10-12**：并入 L1 `make check` target `check-isa-coverage`；须现场重生成矩阵以消除 `081t` 后累积的漂移。）
  - **`check_numbering` / `check_spec_changelog` 并入 `make check`**（两器未入门控 ⇒ 附录后标题/变更记录**静默漂移**风险；`lessons §2.11`）——待排期。（**已由 `INFRA-069t` 落地，2026-10-12**：L1 target `check-spec-numbering` / `check-spec-changelog`。）
  - **M7 test 现状（`TESTCASES-042t` 现场，2026-10-12）**：picolibc 自带 test total 235 / pass 132 / fail 0 / excluded 18 / blocked 85（解锁路径量化见 `TESTCASES-042t` 任务书「遗留问题」）——**是否 M7 内继续解锁待用户裁定**（blocked 85 = REL26 弱符号 26〔`ISS-194`〕+ `ISS-193` 57 + QEMU softfloat 1〔`ISS-195`〕+ `setjmp` 桩 1）。**收口（2026-10-13）**：续解锁已完成（现场 total 235 / pass 213 / fail 0 / excluded 22 / blocked 0），用户 2026-10-12 裁定「**记为达成（推荐）**」；核验归 `TESTCASES-043m`。
  - **`ADR-0019`/`contract-elf` 增补「未定义弱符号」条款**（PC 相对分支/call 解析为**本位自循环**；`call-iiii`→`jump-iiii` 改写理由 = 免 RegRAS 失衡；含 `--noinhibit-exec` 下**未定义强亦落自循环**的情形）——待排期（**命中 ADR 判据：外部契约/结论固化**）。
  - **子代理 workdir 作用域 + 权限 fail-fast（用户 2026-10-11 裁定）**：越界 `cd`（绝对 / `~` / `..`）由"无人应答的 ask"改 **hard-deny**（fail-fast）；规则层钉 workdir **已落地 ✅**；**已立项 `INFRA-065t`**。权限层 = **agent frontmatter `external_directory` deny**（**当前服务下未生效 ⏳**，canary3 实为 `ask` + 用户人工 reject；`message` 字面不可区分、`POST /api/location/reload` 未见效）；`experimental.policies` 已撤销（v2.0.22 schema 不接受 `action:"permission"`）。
  - **`INFRA-065t` 待复验（待办 · 用户操作）**：出界 `cd` fail-fast 在当前服务下**未生效**（agent frontmatter `external_directory` deny + `POST /api/location/reload` 无效）⇒ **用户操作：`opencode service restart` → 越界 `cd` canary 复验**（期望：不弹询问、命令未执行 = 生效）；登记 `ISS-199`（open）。**核验归 `INFRA-072m`**。
  - **`INFRA-070t` Phase B 待授权（待办 · 用户裁定）**：9 个 `contract-*.md` → `contracts/` 因引用冲突（只读锁册 / `contracts/` 内嵌字段 / 范围外目录）**需用户逐条授权** ⇒ 已立 **`INFRA-071t`**（`待开始`，依赖用户授权）；登记 **`ISS-202`**（open）。裁定后由主会话 `/dispatch`。**核验归 `INFRA-072m`**。
  - **`SPEC-136m` 待裁定（待办 · 用户裁定）**：M7 spec 模块里程碑核验**未通过**——`ISS-201`（open，`scope: spec`）未处置 ⇒ **待用户逐条确认**是否把未定义弱符号**防御分支**补入 **`ADR-0019 D9`** / **`contract-elf §3.3`**（改已确认 `D9` 须逐条确认）。裁定后由主会话 `/dispatch`。**核验归 `SPEC-136m`**。

- **M7 候选主题（用户 2026-10-11）**：`musl` + **`pk`(proxy kernel)** + **更完整测试向量** + **benchmark**；**须分层、不混**：
  - **运行环境层**：`pk`（加载 ELF + trap/异常/syscall 转发）；**linux-user（qemu-user）列候选/后置**；
  - **链接层**：**静态优先（含 musl 静态最小集）**；**动态链接独立后置**（`.so`/`ld.so`/`GOT`/`PLT`/`-fPIC`/`-shared` + loader `PT_INTERP`/`.dynamic`）；
  - **用户裁定原话**：「不想把 proxy kernel 和动态链接混到一起」；且 `/plan` 时按 `AGENTS.md` 新增规则**先检索 `DADAO-0628`** 经验；ADR 判据（外部契约/多方案/高代价）**逐条提醒用户裁定**。

- **M7 裁定（用户 2026-10-11，10 条；落纸 + 指针）**——`INTEG-033k`（M7 启动）；原话/细节见该 `k`「裁定汇总」与 `lessons §3.3`：
  1. **`adr-0023` 立**（picolibc 上游 + 精确 commit 固化）：D1 上游 `https://github.com/picolibc/picolibc`；D2 commit `2ae376c6…`（= tag `1.8.12`；「保持 1.8.12」）；D3 `shallow_ref` 用 **tag**。指针 `.tao/adr/adr-0023-picolibc-upstream.md`。
  2. **picolibc test 验收 = 100%**（用户原话「要求 100%」）——归 `TESTCASES-042t`。
  3. **加 `clang++`** + 核 2 个 `.cpp` 测试需求——归 `INFRA-056t`。
  4. **P0 后端纳入 M7**（`f32→f64 anyext` 载入 / FP 比较取值 `setcc` / `f64↔i64 bitcast` / `f64 select_cc` / `i64 cttz`；**优先用 ISA 现成指令**如 `ft2fo`）——归 `LLVM-079t`。
  5. **「ISA↔后端覆盖矩阵」立即立项**（生成式；以 `contracts/opcodes.yaml` **全量**为真源；**两层分列**：汇编器可受理？／**ISel 是否用得上**？）——归 `LLVM-081t`。
  6. **P1 后端纳入 M7**（`floor/ceil/trunc/round/rint/nearbyint`、`fmin/fmax`、`fabs`/`copysign` 双精度）——归 `LLVM-080t`。
  7. **过渡 oracle 采用**：宿主机结果作参照 + **明确边界**（端序／`long double`=f64 vs 宿主 80-bit／`fenv`／UB／实现定义），**登记为「非判据真源」**（将来 `GOLDEN-*` 替换）——归 `SPEC-131t`。
  8. **M7 明确排除**：**动态链接 / linux-user / pk / Chipyard / golden**——见 `INTEG-033k §排除项`。
  9. **执行环境 `hypv`**；semihosting 用 `trap cfx3, 0x30000`——**须核 M6 探针 `cfx_umon`（= cfxha 0）是否为 cfx3（= `hmon`）；实测不一致，已登记**（`INTEG-033k §避坑`/`QEMU-056t`/`SPEC-131t`）。
  10. **RAM 基址改为 `0xFC00_0000_0000`**（`[47:42]≡63` 的 cfx63 段；加 cfx 后不变）；**16 MiB 够用 ⇒ 不改大**——`ADR-0004` 就地修订 + 归 `QEMU-056t`。

## 历史台账指针

> 各里程碑的**逐任务实质改动记录**（原 `changelog.md`）已随归档移入 `.tao/archive/M*/README.md`；本文件「任务流水」为**当前里程碑**流水，不再另设 `changelog.md`。

> **M1 归档指针（2026-10-03）**：2026-09-22 及之前的 89 条 M1 条目已归档至 `.tao/archive/M1/README.md`（历史指针，不再在此追加）。

> **M2 归档指针（2026-10-04）**：2026-09-23 ~ 2026-10-04 的 61 条 M2 条目已归档至 `.tao/archive/M2/README.md`（历史指针，不再在此追加）。

> **M3 归档指针（2026-10-05）**：2026-10-05 的 35 条 M3 条目已归档至 `.tao/archive/M3/README.md`（历史指针，不再在此追加）。

> **M4 归档指针（2026-10-07）**：2026-10-06 ~ 2026-10-07 的 28 条 M4 条目已归档至 `.tao/archive/M4/README.md`（历史指针，不再在此追加）。

> **M5 归档指针（2026-10-08）**：2026-10-07 ~ 2026-10-08 的 20 条 M5 条目已归档至 `.tao/archive/M5/README.md`（历史指针，不再在此追加）。

> **M6 归档指针（2026-10-11）**：2026-10-09 ~ 2026-10-11 的 M6 条目（**1** 条）已归档至 `.tao/archive/M6/README.md §2`（历史指针，不再在此追加）；M6 逐任务的实质改动记录见归档任务书 `.tao/archive/M6/<模块>/`。
