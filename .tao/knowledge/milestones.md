# 项目里程碑

> 只承载**当前进度**；历史见 `.tao/archive/M<1..6>/m<i>-retrospective.md`。
>
> **M6 达成（2026-10-11，architect 实测核验）**：门槛 `make check` **EXIT=0** + **opt-in** `make test-m6` **EXIT=0**（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）；6 个模块 `m` 全置 `里程碑` ⇒ **项目里程碑 M6 = 达成**。M6 任务书/回顾/已关 issue 已归档至 `.tao/archive/M6/`（回顾 `m6-retrospective.md`、清单 `README.md`、快照 `issues-closed.md`）。核验命令/证据见各 `m`「核验」与 `.work/log/integ/INTEG-026m-*.log`。

## 项目里程碑（当前）

| 项目里程碑 | 主题 | 达成日 | 归档 |
| --- | --- | --- | --- |
| M1 | MC + QEMU 标量核心 + MC↔QEMU 集成 | 2026-09-22 | `.tao/archive/M1/` |
| M2 | 规范与接口冻结（Normative Freeze） | 2026-10-04 | `.tao/archive/M2/` |
| M3 | Basic CodeGen（纯整数） | 2026-10-05 | `.tao/archive/M3/` |
| M4 | ELF 文件支持 + LLD 链接 + 汇编器遗留收口 | 2026-10-07 | `.tao/archive/M4/` |
| M5 | SEE/HEE 运行环境 + semihosting | 2026-10-08 | `.tao/archive/M5/` |
| **M6** | 整数完整调用约定 + LLVM 欠账收口 + ELF 直载 + clang target + Embench | **2026-10-11** | `.tao/archive/M6/` |
| M7 | 待规划（`k` 未立） | — | — |

**M6 模块里程碑**（均已 `里程碑`）：`INFRA-052m` / `SPEC-125m` / `LLVM-067m` / `QEMU-054m` / `TESTCASES-040m` / `INTEG-026m`。

## 任务流水（仅当前里程碑）

> M6 的 **46** 份任务流水（`infra 5 / spec 9 / llvm 17 / qemu 4 / testcases 6 / integ 5`）已随归档移入 `.tao/archive/M6/`（清单见 `.tao/archive/M6/README.md §1`；各任务状态取自其任务书 `**状态**` 字段）。**M7 任务分解待 M7 规划 `k` 后建立**——届时本表按各模块现有最大号 \(+1\) 新建。

## 当前进度

- **里程碑**：M6（**达成 2026-10-11**）；M7 规划未启（无 `k`）。
- **M6 遗留（M6→M7，均已登记 = 已处置）**：
  - `ISS-187` 窄位指令利用不足（8/16/32 位算术未用；`mul32` 用 `mul.uo` 而非 `mul.ut`）——**M7 优化候选，非缺陷**（用户 2026-10-10「先只登记，暂不改」）；指针 `.work/log/integ/pending-registrations.md §R3`。
  - `ISS-188` FP 完备性缺口（`fcmp` 取值 / `fabs`/`frem`/`copysign` / `fma`/`fminnum`/`fmaxnum`/`floor`/`ceil`/`round`/`trunc` / `fpclass` / `f16` / `bitcast`(FP↔RD)；**全部显式失败、不产错码**）——**M7**；指针 `.work/log/integ/pending-registrations.md §R4`。
  - `ISS-189` 其它 LLVM 内建数据指导符（`.2byte/.4byte/.8byte/.value/.int/.dc.b/.single/.double` 等）仍被 `llvm-mc` 受理——裁定口径外的剩余面（未授权扩大）；**M7** 按 `spec/Toolchain-01 §7` 唯一集口径收口；指针 `.tao/archive/M6/llvm/LLVM-078t-*.md`「遗留问题」。
  - `check-spec-refs` 1 违规（`contract-asm.md` 引 `Toolchain-01 §7.2` 被误判「无引用」）——根因 = `SPEC_PREFIX_MAP` 不认 `Toolchain-01`、匹配器 `_TEXT_LEAD_IN` 不含数值节号；**M7** 立 `tools/infra` 任务（补前缀映射 + 改数值节号解析；仅补前缀会把 1→91）。
  - `components/qemu/README.md:10` 旧述（「规模（2026-09-23 M1 重整后）：31 份 = 新增 25 + 修改 6」；实为 **34**）——**M7** 随补丁规模刷新。
  - `LLVM-074t` 遗留：`tailjmp` 不参与 `BranchRelaxation` ⇒ 远距离尾调用由 `lld` 报 relocation overflow（**非静默**）；栈实参/变参尾调用未优化（可选增强）——**M7**；指针 `.tao/archive/M6/llvm/LLVM-074t-*.md`。
  - `ISS-108`（`DADAOInstrInfo.td` 1502 行 / `DADAOAsmParser.cpp` 2349 行）未拆分——**M7**（用户 2026-10-09 裁定推迟；**非功能性重构**）。
  - `ISS-164`（cfx mask 屏蔽路径不可观测）、`ISS-074`（`cs.*` 条件赋值 overlap 语义未定）、`ISS-167`（`DADAO-12 §5` prose 与伪代码张力，须授权改上游只读册）——**挂账**（按既有裁定，待相应实现/授权时定）。
  - **台账待收敛**：`ISS-043`/`045`/`138`/`148`/`156`/`159`/`162` 七条由 M6 任务完成区**声称已修/已收口**，但 `issues.yaml` 中 `resolved_by` 未回填、仍 `open`——**M7** 归档前置 `Process-04 §3` 梳理时回填 `closed`（或经用户裁定）；指针 `.tao/archive/M6/issues-closed.md`「待收敛」。
    - **已收敛（`INTEG-028t`，2026-10-11）**：7 条已逐条独立核实为「已修（可关）」并回填 `resolved_by` + `closed`（活台账 17 open / 7 closed，`check_issues` rc=0）；指针 `.work/log/integ/ISS-reconcile.md`、`.tao/tasks/integ/INTEG-028t-待收敛issue核实回填.md`。
- **规划中（M7 起，跨里程碑）**：
  - **门控分层（用户 2026-10-09 裁定）——推迟到 M7**：三层 = **L1 完整性/可用性**（默认 `make check`，秒~几十秒）/ **L2 各模块功能代表集**（几十~几百秒）/ **L3 较完整**（几百~几千秒）+ **模块完整按需**；落地要点 = `check` 收缩为 L1（`check-qemu-semantics` 移出 + 新增 `check-qemu-smoke` 机械派生代表集）、每层须「能失败 + 结构断言」、触发点写 `AGENTS.md`；**第 0 步 = 逐门控计时**。细节指针 `.work/log/integ/gate-tiering-design.md`（gitignored，摘要自足）。
  - **`GOLDEN-*` 里程碑候选（M7 起，用户 2026-10-09 裁定）**：为 **golden model（结果级 / FP 独立 oracle）另立** `golden` 模块专用里程碑——承载 `ISS-019`（结果级 / FP 独立 oracle）、`ISS-026`（encoding `imm` 语义守卫依赖 golden）二者整体，以及 `ISS-081` 拆分后的 FP 独立 oracle 部分（`ISS-081` 的 FP 向量 / harness RF 部分**已在 M6 交付**：`LLVM-066t`/`TESTCASES-036t`/`041t`）。**仅登记归属，不在本轮立项**。
  - **GP（`rbgp`）候选（M7/优化期，M6 不做——用户 2026-10-09 裁定）**：`rb2=rbgp` 现由 M6 寄存器重排（`SPEC-128t`）列为 **reserved**；启用需：小数据区（`.sdata/.sbss` + 阈值）× 链接脚本聚到 `_gp` × 启动设 `rb2=_gp` × 后端 `getGlobalBaseReg`；**reloc 已备**——`ABS12`（基址 `rb1–rb63` 相对、字节）恰为 GP 相对所需、访存偏移 ±2 KiB = 小数据区自然上限。代价：**改变 `rb2` 的 ABI 语义**（独立裁定）。
  - **`lessons.md` 瘦身**：下次里程碑归档时按新口径（新增条目 ≤3 行 + 指针，细节进 `.work/log/`；**不追溯重写**）瘦身（**行数现场统计、不写死**）。
  - **M7 主题待规划**：M6 已交付「整数完整调用约定 + 欠账收口 + ELF 直载 + clang target + Embench」；M7 主题（FP 完备 / golden model / libc/OS / fuzz / 门控分层等）由 **M7 规划 `k`** 裁定（`Process-04 §1`，INTEG 开闭）。

- **M7 候选主题（用户 2026-10-11）**：`musl` + **`pk`(proxy kernel)** + **更完整测试向量** + **benchmark**；**须分层、不混**：
  - **运行环境层**：`pk`（加载 ELF + trap/异常/syscall 转发）；**linux-user（qemu-user）列候选/后置**；
  - **链接层**：**静态优先（含 musl 静态最小集）**；**动态链接独立后置**（`.so`/`ld.so`/`GOT`/`PLT`/`-fPIC`/`-shared` + loader `PT_INTERP`/`.dynamic`）；
  - **用户裁定原话**：「不想把 proxy kernel 和动态链接混到一起」；且 `/plan` 时按 `AGENTS.md` 新增规则**先检索 `DADAO-0628`** 经验；ADR 判据（外部契约/多方案/高代价）**逐条提醒用户裁定**。
