# SPEC-125m: M6 spec 里程碑

**模块**：spec
**项目里程碑**：M6
**状态**：待开始
**目标**：M6 决策与规范正文就位——`adr-0018 §C7 D4` 修订 + 新 reloc ADR（拟 `adr-0021`）+ Embench 上游选择 ADR（拟 `adr-0022`）+ 组合加载 ADR「不立」记录（`SPEC-122t`）；`contract-elf.md §2–§4` reloc 正文（`REL12`/新专用类型/`ABS48` 数据 8B 字段〔`ISS-154`〕）+ `spec/Toolchain-01 §6.1` 修订（`ISS-156`）+ 该册 `sha256` 锁同步（`SPEC-123t`）；`contract-abi.md §6` 三 `[OPEN]` 消解（`SPEC-124t`）；`make check`（含 `check-spec-*`/`check-spec-readonly`）绿。
**关联任务**：`SPEC-122t`、`SPEC-123t`、`SPEC-124t`、`SPEC-126t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.tao/adr/adr-0018-*.md`（修订）、新 reloc ADR、Embench ADR（`SPEC-122t`）；`.tao/knowledge/contract-elf.md §2–§4`、`spec/Toolchain-01-汇编语言.md §6.1`、`manifests/spec-readonly.lock.toml`（`SPEC-123t`）；`.tao/knowledge/contract-abi.md §6`（`SPEC-124t`）
- ADR 均为 `Accepted` 且 decision **逐条经用户确认**；`spec/` 只读册改动均在**用户授权**范围内且锁同步
- 不回归：`make check` EXIT=0（`check-spec-refs`/`check-spec-readonly`/`check-contracts` 等）
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、ADR `Accepted` 与逐条确认证据、正文/锁一致性、门控重跑、判决）
