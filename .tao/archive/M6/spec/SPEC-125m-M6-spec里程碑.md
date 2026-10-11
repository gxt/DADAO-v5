# SPEC-125m: M6 spec 里程碑

**模块**：spec
**项目里程碑**：M6
**状态**：里程碑
**目标**：M6 决策与规范正文就位——`adr-0018 §C7 D4` 修订 + 新 reloc ADR（拟 `adr-0021`）+ Embench 上游选择 ADR（拟 `adr-0022`）+ 组合加载 ADR「不立」记录（`SPEC-122t`）；`contract-elf.md §2–§4` reloc 正文（`REL12`/新专用类型/`ABS48` 数据 8B 字段〔`ISS-154`〕）+ `spec/Toolchain-01 §6.1` 修订（`ISS-156`）+ 该册 `sha256` 锁同步（`SPEC-123t`）；`contract-abi.md §6` 三 `[OPEN]` 消解（`SPEC-124t`）；`make check`（含 `check-spec-*`/`check-spec-readonly`）绿。
**关联任务**：`SPEC-122t`、`SPEC-123t`、`SPEC-124t`、`SPEC-126t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/adr/adr-0018-*.md`（修订）、新 reloc ADR、Embench ADR（`SPEC-122t`）；`.tao/knowledge/contract-elf.md §2–§4`、`spec/Toolchain-01-汇编语言.md §6.1`、`manifests/spec-readonly.lock.toml`（`SPEC-123t`）；`.tao/knowledge/contract-abi.md §6`（`SPEC-124t`）
- ADR 均为 `Accepted` 且 decision **逐条经用户确认**；`spec/` 只读册改动均在**用户授权**范围内且锁同步
- 不回归：`make check` EXIT=0（`check-spec-refs`/`check-spec-readonly`/`check-contracts` 等）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 完成区（核验结论，2026-10-11）
- **关联任务**（读各自任务书 `**状态**`）：`SPEC-122t`/`SPEC-123t`/`SPEC-124t`/`SPEC-126t` 均 `已验证` ✔
- **产出存在**：
  - `.tao/adr/adr-0018-m3-codegen-choices.md`（`§C7 D4` 四形态修订 + `§C7 D6` rev.）、`.tao/adr/adr-0021-ldst-symbol-reloc.md`、`.tao/adr/adr-0022-embench-upstream.md` ✔
  - `.tao/knowledge/contract-elf.md §2–§4`：`REL12`(4)/`ABS12`(5)/`NUM=6`、公式 `S+A−P`/`S+A`、`ABS48` 数据 8B 大端（`§2.2/§3.1/§3.2`）✔
  - `spec/Toolchain-01-汇编语言.md §6.1`：`set.fo` 展开（`ISS-156`，`rd2rf rf,rd0` + 非零 wyde `set.w`）✔
  - `manifests/spec-readonly.lock.toml`：`Toolchain-01` 项存在 ✔
  - `.tao/knowledge/contract-abi.md §6`：三 `[OPEN]` 消解（#1 多返回/聚合返回按声明序递增 K=8、超者 `sret` 经 `rb16`；#2 red zone 不采用；#3 `i128` 不支持）✔
- **ADR 状态**（grep `^**状态**`）：`adr-0018`=`Accepted`（rev. 2026-10-08 `§C7 D4` / 10-09 `§C7 D6`）；`adr-0021`=`Accepted`（rev. 2026-10-09 `D1` 扩为 `REL12`+`ABS12`）；`adr-0022`=`Accepted`。三者均记**用户逐条确认**（`0018` 见 `project_M3-codegen-choices.md §5`；`0021` 见 `INTEG-023k §A#8/#9+§B` 及用户原话；`0022` 见 `INTEG-023k §C/§D`）✔
- **只读锁一致**：`sha256sum spec/Toolchain-01-汇编语言.md` = `3d129ba8c7391aea291059d788b015a6fb9a3f965728434d2530eeb144aa7a4a` = 锁文件同项 ✔
- **门控**：`make check` **EXIT=0**（`check-spec-readonly` 21 册 OK、`check-spec-drift`、`check-spec-codeblocks` 623 行、`check-instrinfo`、`validate-vectors`、`check-no-residue`、`check-lit` 89/89 PASS、`repository checks: PASS`）✔
- **观察（非阻塞，非本里程碑回归）**：独立审计 `make check-spec-refs`（**明示不并入 `make check`**，`Makefile:421`）报 1 违规（`contract-asm.md:206` `.align MUST NOT …[Toolchain-01 §7.2]`）；根因＝该工具 `SPEC_PREFIX_MAP` 仅认 `SimRISC-*`/`DADAO-*`、**不认 `Toolchain-01`** ⇒ 引 `Toolchain-01` 的规范断言被误判「无引用」。该行由 `SPEC-130t`（`0f7d117`）引入，**`master` 上即存在**（本分支与 `master` 零差异）⇒ 非回归。登记为遗留（工具 prefix 覆盖缺口）；`check-contracts` 无同名 make 目标，契约门控＝`check-spec-codeblocks`/`check-instrinfo`/`check-fp-contract`/`validate-vectors`（均绿）。
- **证据指针**：`.work/log/spec/SPEC-125m-make-check.log`（md5 `c128e2aa…`）、`.work/log/spec/SPEC-125m-check-spec-refs.log`（md5 `b0ac8d62…`）
- **修改文件**：`.tao/tasks/spec/SPEC-125m-M6-spec里程碑.md`、`.tao/knowledge/milestones.md`
- **结论**：核验项全部通过 ⇒ `**状态**` = `里程碑`。

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、ADR `Accepted` 与逐条确认证据、正文/锁一致性、门控重跑、判决）
