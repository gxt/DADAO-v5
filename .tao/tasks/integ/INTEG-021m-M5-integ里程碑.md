# INTEG-021m: M5 integ 里程碑（整体收敛点）

**模块**：integ
**项目里程碑**：M5
**状态**：待开始
**目标**：M5 端到端闭环——`自有工具链编 bootrom → QEMU 启动 bootrom（初始权限/向量）→ guest 经 trap（semihosting tag = `immu18[17:16]==2'b11`）→ 共享层 `do_common_semihosting`（ARM 号值）→ SYS_EXIT / 控制台输出替代 exit-port`；门槛 **`make test-semihost`** 五组成全绿（正向 / 权限反例 / 服务表各条至少 1 例 / 不回归〔`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`〕/ `INTEG` 开闭）；harness stdio 捕获落定；`make check` 收口。**M5 整体收敛点**——依赖的各模块 `m` 均 `里程碑` ⇒ 主会话置项目里程碑 `达成`（`spec/Process-04 §1`）。
**关联任务**：`INTEG-020t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tools/integ/run_semihost_e2e.py`、`Makefile::test-semihost`、`tests/e2e/lit/**`
- `make test-semihost` EXIT=0，五组成逐项：
  - 正向：**bootrom（`-bios`）+ bin 应用**经 `-semihosting`、console 捕获、`SYS_EXIT` 码（原「单/多 TU ELF」正向用例移 M6——用户 2026-10-08 裁定，见 `INTEG-019k` §第 8 轮）
  - 权限反例（cfx 级）：**M5 可观测 = cfx 级**——`ILLI`〔mask 禁止 / reserved〕、`CFXREG`〔未实现 cfx / 不存在或超数量寄存器组合〕（**`NUPERM/NJPERM/NSPERM/NHPERM` 出自 `DADAO-12 §2.2` PTBR 层、不在 M5**；`ADR-0020 D9`）
  - 服务表：25 服务各 ≥1 例（计数=25）
  - 不回归：`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`
  - `INTEG` 开闭
- harness stdio 捕获：`-semihosting-config` 传参方 + console 捕获落点/比对方式已落定且与实现一致
- 各模块 `m` 均 `里程碑`：`INFRA-049m`/`SPEC-118m`/`LLVM-061m`/`QEMU-048m`/`TESTCASES-035m`
- 跨模块影响：`ADR-0004 R3`（RAM 基址）判定已登记（仅判定/记录）；**`RAM@0` C1 step2（旧向量迁移）随 M6**（用户 2026-10-08 裁定；`ISS-165`）+「`-bios`+ELF 组合语义 / ELF loader 扩展 / 组合 ADR」随 M6（`ISS-168`）——**均不在 M5 门槛内、不阻断 M5 收敛**；上游模块变更已处置；无未处置跨模块项
- `make check`/`check-no-residue` EXIT=0

## 核验记录（主会话）

（核验命令、输出与退出码；结论）

## 口径对齐记录（architect，2026-10-08）

**依据**：已确认的 **`ADR-0020 D9`**——M5 权限范围只做 `cfx0/1/2/3/63`；`NUPERM/NJPERM/NSPERM/NHPERM` 属 `DADAO-12 §2.2` PTBR 权限层、不在 M5；M5 可观测的权限反例 = cfx 级 `ILLI`/`CFXREG`。

**改动**：核验「权限反例」行由「未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`」对齐为 **cfx 级 `ILLI`/`CFXREG`**（保留 `NUPERM…` 出处说明）。**性质 = 与既定决策的一致性修正，非新增范围**。

**边界**：仅改本文件该 1 行 + 本记录；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。
