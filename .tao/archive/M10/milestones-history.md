# milestones.md 历史内容（迁出）

> 来源：`.tao/knowledge/milestones.md`；仅作历史留存，不再维护。


> 只承载**当前进度**；历史见 `.tao/archive/M<1..7>/m<i>-retrospective.md`。
>
> **M7 收尾归档（2026-10-13，`INTEG-035m`）**：M7 期（2026-10-11 ~ 2026-10-13）任务书/回顾/已关 issue **收尾归档**至 `.tao/archive/M7/`（`README.md` / `m7-retrospective.md` / `issues-closed.md`）；**项目里程碑 M7 = 达成**（2026-10-13 口径纠正：`AGENTS.md`「不得置里程碑」**只针对未处置的*跨模块*影响**，`ISS-201` 属 spec **模块内 backlog**、**不阻断** ⇒ `SPEC-136m`/`INTEG-034m` 置 `里程碑`）。**未决项**（`INFRA-071t` **已验证 2026-10-15**；后随 M8 收尾归档入 `.tao/archive/M8/infra/`）见本页「任务流水」。
>
> **M6 达成（2026-10-11，architect 实测核验）**：门槛 `make check` **EXIT=0** + **opt-in** `make test-m6` **EXIT=0**（`check-lit-full` 12/12 + `diff_ir_lli` 19/19 + Embench 38/38）；6 个模块 `m` 全置 `里程碑` ⇒ **项目里程碑 M6 = 达成**。M6 任务书/回顾/已关 issue 已归档至 `.tao/archive/M6/`（回顾 `m6-retrospective.md`、清单 `README.md`、快照 `issues-closed.md`）。核验命令/证据见各 `m`「核验」与 `.work/log/integ/INTEG-026m-*.log`。
>
> **M8 收口归档（2026-10-19，`INTEG-036m`）**：项目里程碑 **M8 = 达成**；M8 期 **68 册**任务书/回顾/**52 条**已关 issue 已归档 `.tao/archive/M8/`（`README.md` / `m8-retrospective.md` / `issues-closed.md`）。本页「任务流水」只保留未归档项（`LLVM-100t` = `M9`；`SPEC-141t` = 只读预研待开工）。


## 项目里程碑

> 项目里程碑（M1–M7 及达成日/主题/成就）见 README.md「项目里程碑」。

**项目里程碑 = M9 达成（2026-10-24）**：核验册 `INTEG-037m`（判据见该册）；本期 67 册 `t` 全验证、终局复跑 0 fail、open issue 11 条（全部 M10 登记项）。

**M6 模块里程碑**（均已 `里程碑`）：`INFRA-052m` / `SPEC-125m` / `LLVM-067m` / `QEMU-054m` / `TESTCASES-040m` / `INTEG-026m`。

**M8 模块里程碑**：仅 **`INTEG-036m`**（整体收敛点，已 `里程碑`，2026-10-19；M8 期未设各模块 `m`，由 68 册任务终态 + 本册判据收敛承担）。

**M7 模块里程碑**（**均 `里程碑`**：`INFRA-072m`/`SPEC-136m`/`LLVM-090m`/`QEMU-059m`/`TESTCASES-043m`/`INTEG-034m`〔整体收敛点〕）：`INFRA-072m` / `SPEC-136m` / `LLVM-090m` / `QEMU-059m` / `TESTCASES-043m` / `INTEG-034m`（整体收敛点）+ `INTEG-035m`（M7 收尾归档，`Process-04`；任务书**已自归档**入 `.tao/archive/M7/integ/`）。

## 当前进度（2026-10-22）

- **M9 进行中**：进度**只以本页任务流水为准**；细节写各任务书，计数以现场门控输出为准。
- **已收口（本批）**：ISA 链（`rol`）、线程链 T1–T5、原子链 4 册、门控互斥（`INFRA-099t`）、
  `fcls` 位序（`SPEC-156t`/`QEMU-069t`）、`clmul` 4 册、取整 5 册、`min/max`（进行中）。
- **队列**：`min/max` 剩余 → FMA 5 册 → `TESTCASES-057t` → `LLVM-126t` → `TESTCASES-053t` → 终局全量复跑。
- **M8 已归档**（2026-10-19）：`.tao/archive/M8/`（`README.md` / `m8-retrospective.md` / `issues-closed.md`）。
- **计数类口径**（用户 2026-10-22 裁定）：`contract-isa.md` 等分桶计数在**里程碑收尾**统一同步，不随单任务改。

### ISA 候选（`SPEC-141t` 结册）

> 判据（用户 2026-10-21 原话）：**目标应用域能力需求 + 软硬件代价比**；语料频次只回答"今天能否验证"。

- `f16`：**不做**（C23 可选、零语料、硬报错不静默）。
- `mulhu`：**已具备**（`mul.uo` 双目的出全 128 位），撤回候选。
- `fshl`/`fshr`：**保留候选（中）**；后端可先去冗余 mask（实测 9→4 条），将来加指令则 1 条。
- `clmul`：**已定案**（`ADR-0035`，已实现并验证）。
- `crc32c`：**候选（高）**，未立册。
- 未定：`bswap64` 用 `rev.o`；"hw 特化后置"分界（`ADR-0027 D3`）。

## M9（规划）

- 决策载体：`ADR-0030`（`long double`=binary128，排 M9）、`ADR-0031`（变参 ABI）、`ADR-0032`（`rol`，已落）、
  `ADR-0034`（原子）、`ADR-0035`（`clmul`）。
- 实现/排期细则**不在此重复**：见对应任务书与 `issues.yaml`；本段只作导航。

## 任务流水说明（迁出）

> 本表 = **未归档任务流水**（M9 及留活项）；M8 已终态流水（68 条）见 `.tao/archive/M8/README.md §2`，M7 及以前见 `.tao/archive/M*/README.md`。列 = `| 编号 | 状态 | 完成时间 | 一句改动 |`；**按完成时间倒序**（最新在上）；**未完成任务也列**（时间 = **登记时间**，加注 `（登记）`；同一时间按任务编号升序）。**一句改动 ≤120 字符**，只写「做了什么 + 关键数字/结论」；细节一律写各任务书（本表只做索引）。**新立任务（任务书落盘）时即加行**。

> **未完成任务册（现场派生，清单见下）**
> - 缺陷修复批（2026-10-20 立册，`ISS-302`；`LLVM-118t`/`119t`/`120t`、`INFRA-096t`/`INFRA-097t` 已 `已验证`）：`INFRA-098t`（`ISS-261` + `ISS-301`）、`INFRA-099t`（`ISS-229` 门控互斥）、`TESTCASES-053t`（`ISS-270`/`273`/`282`/`288` 陈旧证据脚本族）
> - `SPEC-141t`：`M9` / ISA 扩展预研 —— **结册未执行**（2026-10-21；未定项见下「ISA 扩展预研遗留」）
> - `ADR-0034`（2026-10-20 定案 / 2026-10-21 转正）：原子编码定案（`fence` `0x20`、`lr/sc` 24 条），规范面/合约/生成面已落；**实现 4 册全部 `已验证`**（`ISS-307` `closed`，2026-10-21）
> - **原子链 4 册（`ISS-307`）现状**：① `LLVM-121t`（返工修复 `ISS-312`/`ISS-313`，reviewer 第 3/4 轮 `Accepted`，20 条 XFAIL 已转 PASS）、② `QEMU-067t`、③ `INFRA-100t`、④ `TESTCASES-056t`（reviewer 第 2 轮 `Accepted`；两档 711/711、0 xfail）= **全部 `已验证`** ⇒ `ISS-307` `closed`，`ISS-294` 随 ③/④ 收口。
> - 说明：`M8` 已于 2026-10-19 达成；`LLVM-116t`/`QEMU-064t`/`SPEC-152t` = `已验证`（ISA 链收口）、`INFRA-095t`/`TESTCASES-052t` = `已验证`（线程链 T1/T3 收口，19 目标两档 19/19）；未解 `issue` 见 `issues.yaml`（不在此重复）。
