# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..7>/m<i>-retrospective.md`。
>
> **M7 收尾归档（2026-10-13，`INTEG-035m`）**：M7 期（2026-10-11 ~ 2026-10-13）任务书/回顾/已关 issue **收尾归档**至 `.tao/archive/M7/`（`README.md` / `m7-retrospective.md` / `issues-closed.md`）；**项目里程碑 M7 尚未标记「达成」**——`SPEC-136m` 未通过（`ISS-201` 待用户逐条确认）、`INTEG-034m`（整体收敛）L3 已绿而残项同 `ISS-201` ⇒ **M7 达成待裁定**。**未决项**（`INFRA-071t` / `SPEC-136m` / `INTEG-034m`）仍留 `.tao/tasks/`，见本页「当前进度」与 `m7-retrospective.md §7`。
>
> **M6 达成（2026-10-11，architect 实测核验）**：门槛 `make check` **EXIT=0** + **opt-in** `make test-m6` **EXIT=0**（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）；6 个模块 `m` 全置 `里程碑` ⇒ **项目里程碑 M6 = 达成**。M6 任务书/回顾/已关 issue 已归档至 `.tao/archive/M6/`（回顾 `m6-retrospective.md`、清单 `README.md`、快照 `issues-closed.md`）。核验命令/证据见各 `m`「核验」与 `.work/log/integ/INTEG-026m-*.log`。

## 项目里程碑

> 项目里程碑（M1–M6 及达成日/主题/成就）见 README.md「项目里程碑」。

**M6 模块里程碑**（均已 `里程碑`）：`INFRA-052m` / `SPEC-125m` / `LLVM-067m` / `QEMU-054m` / `TESTCASES-040m` / `INTEG-026m`。

**M7 模块里程碑**（**收尾归档 2026-10-13**；`里程碑` 4 = `INFRA-072m`/`LLVM-090m`/`QEMU-059m`/`TESTCASES-043m`；**未通过 2** = `SPEC-136m`〔`ISS-201` 阻断〕/ `INTEG-034m`〔整体收敛，L3 已绿、残项同〕）：`INFRA-072m` / `SPEC-136m` / `LLVM-090m` / `QEMU-059m` / `TESTCASES-043m` / `INTEG-034m`（整体收敛点）+ `INTEG-035m`（M7 收尾归档，`Process-04`；**`里程碑`**，任务书**已自归档**入 `.tao/archive/M7/integ/`）。

## 任务流水

> 本表 = **M7 未决项**逐任务一行（M7 已终态任务流水已随归档移入 `.tao/archive/M7/README.md §2`）。**细则**：列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**每格单行**（不换行）；`状态` 取值 = `待开始` / `待验收` / `待返工` / `已验证`（`m` 行另用 `里程碑`）；`完成时间` = 该任务**落地提交时间**（`git log --format='%h %ci'` 现场取证，**精确到分钟 `YYYY-MM-DD HH:MM`**），`待开始` 行写 `—`；`一句改动` ≤1 行、只留摘要，**细节指针到各任务书**。**新立任务（任务书落盘）时即加 `待开始` 行**（不等到开工/落地），使队列始终可见。
> M6 的 **46** 份任务流水（含实质改动）已随归档移入 `.tao/archive/M6/`（清单见 `.tao/archive/M6/README.md §1`）；M7 的**已终态任务流水（37 条）已随 M7 收尾归档移入 `.tao/archive/M7/README.md §2`**（2026-10-13）；下表列 M7 **未决 4 行**（`INFRA-071t` / `SPEC-136m` / `INTEG-034m` / `INTEG-035m`〔**`里程碑`**；任务书已自归档入 `.tao/archive/M7/integ/`〕）。

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| INFRA-071t | 待开始 | — | `contract-*.md`→`contracts/`（Phase B）+ `check-contracts-dir` 白名单门控（**待用户授权 3 项**：只读锁册 / `contracts/` 内嵌字段 / 扩到 `tools`·`components`·`tests`） |
| SPEC-136m | 待开始 | — | M7 spec 模块里程碑核验（**未通过：`ISS-201` 待用户逐条确认**） |
| INTEG-034m | 待开始 | — | M7 integ 模块里程碑核验（整体收敛点；L3 `check-full` 已绿；项目 M7 达成待 `ISS-201` 用户裁定） |
| INTEG-035m | 里程碑 | 2026-10-13 03:16 | M7 归档与回顾（`Process-04`；任务书**已自归档**入 `.tao/archive/M7/integ/`） |

## 当前进度

- **里程碑**：M6（**达成 2026-10-11**）；**M7 收尾归档（2026-10-13，`INTEG-035m`）**——M7 期任务书/回顾/已关 issue 已归档 `.tao/archive/M7/`；**项目里程碑 M7 尚未标记「达成」**（`SPEC-136m` 未通过 `ISS-201`、`INTEG-034m` 残项同 ⇒ **待用户裁定**；4 模块 `m` 已 `里程碑`）。M7 未决 4 行见上「任务流水」；待裁定/操作清单见 `.tao/archive/M7/m7-retrospective.md §7`。开启任务 `INTEG-033k`（`已验证`）已归档 `.tao/archive/M7/integ/`。
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
  - **目录三分界与规范版本号（用户 2026-10-11 裁定）**：`docs/` = 工程流程规范（`Process-0x`）+ 索引 + `DDLN/`（**给别人看**）；`.tao/knowledge/` = 结论/设计/口径（**给自己看**）；`.work/log/` **非默认落点**；`Process-0x` **迁入 `docs/`**、`Process` **不设版本号**；`Toolchain-01`/`Machine-01` **设 `0.x.y` 版本号**（`x=0`；大改 `y+1`、小改 `z+1`）+ 文末 changelog（不用表格、不写“依据”）；`docs/` 6 个过期文件**可删**。**草案任务书**：`.tao/archive/M7/infra/INFRA-060t-目录三分界与规范版本号落地.md`（**待用户逐条裁定**后方写 B 段版本号；2026-10-13 随 M7 归档）。
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
  - **`INTEG-034m` / M7 达成待裁定（待办 · 用户裁定）**：M7 integ 整体收敛核验 **L3 已绿**（`make check-full` rc=0，manifest 追加 13 条 exclude）；**唯一残项 = `ISS-201`**（open，`scope: spec`）待用户逐条确认 ⇒ **项目里程碑 M7 达成待 `ISS-201` 裁定**（指向 `ISS-201`）。**核验归 `INTEG-034m`**。

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

> **M7 收尾归档指针（2026-10-13）**：M7 期（2026-10-11 ~ 2026-10-13）的**已终态任务流水（37 条）**已移入 `.tao/archive/M7/README.md §2`（历史指针，不再在此追加；归档任务 `INTEG-035m` **已自归档**入 `.tao/archive/M7/integ/`〔**`里程碑`**〕，其行留活表列**已达成**）；**里程碑回顾** `m7-retrospective.md`、**已关 issue 快照（12 条）** `issues-closed.md` 见同目录。**项目里程碑 M7 尚未标记「达成」**（`SPEC-136m` 未通过 `ISS-201` 待裁定）⇒ 活表保留 M7 未决 4 行（`INFRA-071t`/`SPEC-136m`/`INTEG-034m`/`INTEG-035m`）。
