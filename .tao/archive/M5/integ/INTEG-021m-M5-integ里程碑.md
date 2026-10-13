# INTEG-021m: M5 integ 里程碑（整体收敛点）

**模块**：integ
**项目里程碑**：M5
**状态**：里程碑
**目标**：M5 端到端闭环——`自有工具链编 bootrom → QEMU 启动 bootrom（初始权限/向量）→ guest 经 trap（semihosting tag = `immu18[17:16]==2'b11`）→ 共享层 `do_common_semihosting`（ARM 号值）→ SYS_EXIT / 控制台输出替代 exit-port`；门槛 **`make test-semihost`** 五组成全绿（正向 / 权限反例 / 服务表各条至少 1 例 / 不回归〔`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit`〕/ `INTEG` 开闭）；harness stdio 捕获落定；`make check` 收口。**M5 整体收敛点**——依赖的各模块 `m` 均 `里程碑` ⇒ 主会话置项目里程碑 `达成`（`spec/Process-04 §1`）。
**关联任务**：`INTEG-020t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`tools/integ/run_m5_e2e.py`（`TESTCASES-033t` 产出，`INTEG-020t` **复用、不另建 `run_semihost_e2e.py`**）、`Makefile::test-semihost`（`tests/e2e/lit/**` 判定不适用，见 `INTEG-020t` 遗留问题）
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

**M5 integ 里程碑核验 + M5 项目里程碑达成判定（2026-10-08，architect 代主会话）**　**判决：满足，置 `里程碑`；M5 达成条件全满足**

证据来源：`INTEG-020t` 完成区/审阅记录、`.work/log/integ/INTEG-020t-test-semihost.log`（+`-probe/-test-elf/-test-codegen/-check/-check-lit/-evidence-run` 同名日志）、`.work/evidence/INTEG-020t/run.sh`；独立只读复核（`ls`/`grep`/`check_dirs.py --residue`）。

| # | 核验项 | 证据（真实） | 结论 |
| --- | --- | --- | --- |
| 1 | 关联任务 `INTEG-020t` `已验证` | 头部 `**状态**：已验证` | ✅ |
| 2 | 产出：`tools/integ/run_m5_e2e.py` + `Makefile::test-semihost` | `Makefile:505 test-semihost: install-host build-bootrom test-elf test-codegen check`；`tools/integ/run_m5_e2e.py` 存在（**复用、不另建 `run_semihost_e2e.py`**） | ✅ |
| 3 | `make test-semihost` EXIT=0（实测 59s），五组成逐项 | `INTEG-020t-test-semihost.log` 末 `===== EXIT=0 (make test-semihost, five components) =====` | ✅ |
| 4 | 正向：`-bios` bootrom + bin 经 `-semihosting`、console 捕获、`SYS_EXIT` 码 | 同 log：`run_m5_e2e: 10 programs, bootrom …/bootrom.bin`；`PASS m5_semi_writec expected=64 …`；`console … (byte-exact)`（`41` / `4f 4b 0a`）；逐例命令行**全含 `-bios`** | ✅ |
| 5 | 权限反例（cfx 级 `ILLI`/`CFXREG`） | 同 log：`m5_perm_reserved_illi`(80,`ILLI`)/`m5_perm_mask_illi`(81,`ILLI`)/`m5_perm_unimpl_cfxreg`(82,`CFXREG`)/`m5_perm_badcombo_cfxreg`(83,`CFXREG`) | ✅ |
| 6 | 服务表：25 服务各 ≥1（计数=25） | 同 log：[2/2] `service coverage: all 25 service ids exercised` / `RESULT: PASS`；`--list` → `distinct 25 / required 25` | ✅ |
| 7 | 不回归：`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit` | 同 log 前置链：`test-elf: PASS`（5/5）、`test-codegen: PASS`（15/15）、`repository checks: PASS`（含 lit 62/62）、`check-no-residue: PASS` | ✅ |
| 8 | `INTEG` 开闭登记 | 本文件（`INTEG` 模块 `m`）+ `INTEG-020t` 遗留「INTEG 开闭登记材料」；门控 recipe 末行回显 `INTEG registration` | ✅ |
| 9 | harness stdio 捕获（传参方 + 落点/比对一致） | `-semihosting-config enable=on,target=native,chardev=semi` **仅由驱动传**（`grep semihosting-config Makefile` 0 命中）；console = chardev 文件（`.dadao/tests/m5-e2e/<stem>.console`）；比对 = 逐字节（`res_console_ok = (console == want)`） | ✅ |
| 10 | **各模块 `m` 均 `里程碑`** | `INFRA-049m`/`SPEC-118m`/`LLVM-061m`/`QEMU-048m`/`TESTCASES-035m` 已于本次核验置 `**状态**：里程碑` | ✅ |
| 11 | 跨模块影响：`ADR-0004 R3` 判定已登记；`RAM@0` step2 随 M6（`ISS-165`）；`-bios`+ELF 组合随 M6（`ISS-168`）；上游变更已处置 | 各模块 `m` 核验记录「跨模块影响处置」表：`ISS-163/164/165/166/167/168/169/110` 逐条登记/结案/M6；`spec/` 实现口径由 `contracts/`（权威）保证、门控绿 | ✅ |
| 12 | `make check`/`check-no-residue` EXIT=0 | `INTEG-020t-check.log` `repository checks: PASS`；本次跑 `check_dirs.py --residue` → `check-no-residue: PASS` | ✅ |

**M5 项目里程碑达成判定**（依 `spec/Process-04 §1`）：

| 达成条件 | 证据 | 结论 |
| --- | --- | --- |
| 门槛 `make test-semihost` EXIT=0（五组成全绿） | `INTEG-020t-test-semihost.log` EXIT=0 | ✅ |
| 不回归（`test-elf` 5/5、`test-codegen` 15/15、`check`、`check-lit` 62/62） | 同 log 前置链 + `-check/-check-lit` 日志 | ✅ |
| 下游模块 `m`（`INFRA/SPEC/LLVM/QEMU/TESTCASES`）**均 `里程碑`** | 本次核验（见上第 10 项） | ✅ |
| `INTEG` 模块 `m`（本文件）置 `里程碑` | 本记录 | ✅ |

⇒ **M5 达成条件全部满足**；已在 `.tao/knowledge/milestones.md` 将 **M5 行**置 **`✅ 达成`**。19 个 M5 `t` 任务 + `INTEG-019k` 全 `已验证`，6 个模块 `m` 全 `里程碑`。

**归档准备（评估，未执行；按 M4 先例 `INTEG-018t`）**：**需要**一个 M5 归档任务（建议编号 `INTEG-022t`「M5 归档与回顾」，待 M5 正式收尾后 `/plan` 立之）。范围建议：
- **归档前置**（`spec/Process-04 §3` 遗留台账梳理，步骤 3–6）：由**主会话**执行（M2/M3/M4 先例）——关闭 M5 已消解项、校正 `scope`、判定 moot、头部同步（`issues.yaml` 头部 M5 → ✅ 达成）。
- **归档判据**（`§4`）：`**项目里程碑**：M5` **且终态**的任务书 `git mv` 入 `.tao/archive/M5/<module>/`。**预期 26 个**（`infra 3 / spec 9 / llvm 2 / qemu 6 / testcases 3 / integ 3`，含 `INTEG-019k`）+ **自归档** `INTEG-022t` 自身 ⇒ 归档后 `archive/M5/` 各模块 **27**（`integ 4`）。清单：`infra`=`INFRA-047t/048t/049m`；`spec`=`SPEC-113t/114t/115t/116t/117t/118m/119t/120t/121t`；`llvm`=`LLVM-060t/061m`；`qemu`=`QEMU-044t/045t/046t/047t/048m/049t`；`testcases`=`TESTCASES-033t/034t/035m`；`integ`=`INTEG-019k/020t/021m`（+自归档 `INTEG-022t`）。
- **产物**（`§5/§6`）：`.tao/archive/M5/README.md`（任务清单/changelog 摘录/MEMORY 摘录/指针）+ `m5-retrospective.md`（目的/门槛/决策〔`ADR-0020`、`ADR-0004 R1–R3`、`ADR-0016`〕/落地链/坑与教训/遗留 M6）+ `issues-closed.md`（M5 期间 `closed` 项快照）。
- **纪律**（`§7/§8`）：只动 `.tao/**`；不改写历史行；`git mv` 保 rename 历史；不误伤并行未提交工作。

## 口径对齐记录（architect，2026-10-08）

**依据**：已确认的 **`ADR-0020 D9`**——M5 权限范围只做 `cfx0/1/2/3/63`；`NUPERM/NJPERM/NSPERM/NHPERM` 属 `DADAO-12 §2.2` PTBR 权限层、不在 M5；M5 可观测的权限反例 = cfx 级 `ILLI`/`CFXREG`。

**改动**：核验「权限反例」行由「未授权模式 ⇒ `NUPERM/NJPERM/NSPERM/NHPERM`」对齐为 **cfx 级 `ILLI`/`CFXREG`**（保留 `NUPERM…` 出处说明）。**性质 = 与既定决策的一致性修正，非新增范围**。

**边界**：仅改本文件该 1 行 + 本记录；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`；未新增/删除任务。

## 审阅记录

#### 第 1 轮 architect 修订（2026-10-08，只追加）

**改动**：核验「产出是否存在」由 `tools/integ/run_semihost_e2e.py` 就地更正为 `tools/integ/run_m5_e2e.py`（另注 `tests/e2e/lit/**` 判定不适用）。

**依据**：既定判定 **复用 `tools/integ/run_m5_e2e.py`、不另建 `run_semihost_e2e.py`**——见 `INTEG-020t` 审阅记录「主会话判定落纸（architect，2026-10-08）」判定 3 + 「下发前预检修订」F2（该判定的原始落点），以及 `TESTCASES-033t` 审阅记录（`run_m5_e2e.py` 为 `TESTCASES-033t` 实际交付驱动）；`INTEG-020t` 遗留问题「INTEG 开闭登记材料」亦登记此为待更正项。本次为**与既定判定的一致性更正，非新增范围**。

**边界**：仅改本文件核验 1 行 + 本记录；**`spec/` 交集为空**；未改 `contracts/**`/`components/**`/`Makefile`/`tools/**`；未新增/删除任务。

#### M5 模块里程碑核验 + M5 达成判定（architect，2026-10-08）

**判决**：**满足 ⇒ `**状态**` 置 `里程碑`**；**M5 达成条件全部满足 ⇒ `milestones.md` M5 行置 `✅ 达成`**。逐条证据见上「核验记录（主会话）」：`make test-semihost` EXIT=0（五组成全绿）、不回归全绿、6 个模块 `m` 全 `里程碑`、跨模块项均处置。

**跨模块项**：`ISS-163`（用户裁定「暂登记遗留」）/`ISS-164`（跟踪）/`ISS-165`（M6）/`ISS-166`（closed）/`ISS-167`（登记+建议另立 spec 任务）/`ISS-168`（M6）/`ISS-169`（M6）——**无未处置项、不阻断 M5 收敛**。`ISS-170` **不存在**（`issues.yaml` 最大 id = `ISS-169`）。

**归档准备**：**需立归档任务**（建议 `INTEG-022t`），范围见上「归档准备（评估）」；**本次不执行归档**。

**边界**：本次仅改本文件 + `milestones.md`（M5 行 + 达成注）；**`spec/` 交集为空**；未触 `contracts/**`/`components/**`/`Makefile`/`tools/**`；未新增/删除任务。

#### architect 提交与文件集审核（2026-10-08）

**档位**：**正常提交**（本次为架构师里程碑核验步，验收通过 ⇒ 无 `WIP:` 前缀）；**只 `commit`、未 `push`**。

**提交号**：`e4db3b1`（`M5 模块里程碑核验（6 个）+ M5 达成判定`）。

**显式 staging（禁 `git add -A`）**：逐个路径 `git add` **7** 文件——`milestones.md` + 6 个 `m` 文件（`INFRA-049m`/`SPEC-118m`/`LLVM-061m`/`QEMU-048m`/`TESTCASES-035m`/`INTEG-021m`）。

**对账结论**（`git -c core.quotePath=false diff --cached --name-only` ↔ 声明文件集）：
- **漏提 0**：声明 7 = staged 7；
- **多提 0 / 越界 0**：staged 全部 `.tao/**`（`grep -vE '^\.tao/'` → 空）；**`spec/` 交集为空**（`grep -E '^spec/'` → 空）；未触 `contracts/**`/`components/**`/`Makefile`/`tools/**`；
- `git show --stat`：7 files changed, 245 insertions(+), 13 deletions(-)。

#### 第 1 轮 reviewer 独立复核（2026-10-08）

**审查者**：reviewer 子代理（独立验证，非执行者）
**审查范围**：M5 里程碑达成判定（重大结论），独立证伪
**基础**：`7616559`（INTEG-020t 提交）→ HEAD = `d89ef2a`（architect 留痕）

##### 1. M5 `t` 任务全 `已验证`

独立 `grep` 逐个核验 M5 全部 20 个 `t` 任务 + `INTEG-019k`：

```
INFRA-047t → 已验证（第 2 轮 Accepted，line 6）
INFRA-048t → 已验证
INTEG-019k → 已验证
INTEG-020t → 已验证
LLVM-060t  → 已验证
QEMU-044t  → 已验证
QEMU-045t  → 已验证
QEMU-046t  → 已验证
QEMU-047t  → 已验证
QEMU-049t  → 已验证
SPEC-113t  → 已验证
SPEC-114t  → 已验证
SPEC-115t  → 已验证
SPEC-116t  → 已验证
SPEC-117t  → 已验证
SPEC-119t  → 已验证
SPEC-120t  → 已验证
SPEC-121t  → 已验证
TESTCASES-033t → 已验证
TESTCASES-034t → 已验证
```

**注**：`INFRA-047t` 文件含多条 `**状态**` 行（审阅中间态），最终状态为 `已验证`（line 678 `Accepted`）。`QEMU-044t/045t/046t` 同理（审阅记录中提及 `待验收` 为中间态，最终 `已验证`）。

**结论**：20/20 `t` + `INTEG-019k` 全部 `已验证` ✓

##### 2. 6 个 `m` 全 `里程碑`

```
INFRA-049m    → 里程碑 ✓
SPEC-118m     → 里程碑 ✓
LLVM-061m     → 里程碑 ✓
QEMU-048m     → 里程碑 ✓
TESTCASES-035m → 里程碑 ✓
INTEG-021m    → 里程碑 ✓
```

**结论**：6/6 全部 `里程碑` ✓

##### 3. 门槛证据（独立重跑）

**独立重跑 `make test-semihost JOBS=8`**（非读日志）：
```
[PASS] svc_tickfreq         SYS_TICKFREQ returns the tick frequency -> ok
[PASS] iserror_be64         argument block field read as 64-bit big-endian -> ok
[PASS] service coverage: all 25 service ids exercised
RESULT: PASS
test-semihost: PASS (forward + permission + 25-service + no-regression + INTEG registration)
EXIT=0
```

日志 `.work/log/integ/INTEG-020t-test-semihost.log` 末段一致：10/10 m5_e2e PASS、25-service coverage PASS、62/62 MC PASS、`EXIT=0`。

**结论**：五组成全绿，EXIT=0 ✓

##### 4. 不回归证据（独立读日志）

| 日志 | 通过数 | EXIT |
|------|--------|------|
| `INTEG-020t-test-elf.log` | 5/5 PASS | EXIT=0 |
| `INTEG-020t-test-codegen.log` | 15/15 PASS | EXIT=0 |
| `INTEG-020t-check.log` | 62/62 MC + repository checks PASS | EXIT=0 |
| `INTEG-020t-check-lit.log` | 62/62 PASS | EXIT=0 |

**独立重跑 `make check JOBS=8`**：`repository checks: PASS`，EXIT=0 ✓
**独立重跑 `make check-no-residue`**：`check-no-residue: PASS`，EXIT=0 ✓

**结论**：不回归全绿 ✓

##### 5. 跨模块项处置（独立核 `issues.yaml`）

| ISS | 状态 | 处置 | 阻断 M5? |
|-----|------|------|----------|
| ISS-163 | open | 用户裁定「暂登记遗留」，收口须另行授权 | 否 |
| ISS-164 | open | 登记跟踪（cfx mask 可观测性局限） | 否 |
| ISS-165 | open (scope: M6) | 用户裁定随 M6（RAM@0 step2 迁移） | 否 |
| ISS-166 | closed (by SPEC-121t) | Machine-01 §1 越界路由已由 SPEC-121t 收口 | 否 |
| ISS-167 | open | 登记 + 建议另立 spec 任务（§5 prose 措辞张力） | 否 |
| ISS-168 | open (scope: M6) | 用户裁定移 M6（-bios+ELF 组合/ELF loader） | 否 |
| ISS-169 | open (scope: M6) | 披露 6 探针保留 exit-port 例外，进门控项均迁 SYS_EXIT | 否 |

**独立判据**（`AGENTS.md`「因其它模块影响而需修复类型的任务」）：
- ISS-163/167：文档措辞类，不影响实现/门控，显式 deferred
- ISS-164：测试机可观测性局限，当前 cfx 全不可屏蔽 cause，非实现缺陷
- ISS-165/168：用户裁定移 M6，step1 已落地且门控全绿
- ISS-166：已 closed
- ISS-169：迁移例外已披露，进门控的测试侧均已迁 SYS_EXIT

**结论**：无未处置跨模块影响，不阻断 M5 收敛 ✓

##### 6. 3 处口径偏差（独立核）

1. **SPEC-118m（Machine-01 落点）**：原措辞「`spec/DADAO-12`」实际落 `spec/Machine-01`（用户 2026-10-07 裁定），上游只读册零改动。**非缺口**。
2. **TESTCASES-035m（L1 复用）**：L1 MC 向量复用 `LLVM-060t` 的 `cfx2-trap-escape.s`（DRY 判定），不重复引入 `m5-*.s`。**非缺口**。
3. **QEMU-048m（check-interface 86→85）**：

**独立重跑 `python3 tools/integ/check_interface_alignment.py`**：
```
总计: 85 项 | PASS: 85 | FAIL: 0 | MANUAL: 0
EXIT=0
```

RAM@0 断言全部保留（RAM0_BASE=0x0 PASS、RAM0_SIZE=16MiB PASS、RAM0 hw registration PASS）。86→85 因 `TESTCASES-034t` 移除 1 条 `harness.EXIT_PORT` 断言（harness 已不用 EXIT_PORT），属正常迁移。**非缺口**。

**结论**：3 处偏差均经用户裁定/DRY/正常迁移，非缺口 ✓

##### 7. 未越界

```
$ git diff --name-only 7616559..HEAD | wc -l
7
```

文件清单：`milestones.md` + 6 个 `m` 文件。`spec/` 交集为空。

**注**：任务书声称「8 文件」，实为 7 文件（INTEG-021m 被双算——既是 6m 之一又被单独计入）。非阻塞，属计数笔误。

**结论**：未越界，`spec/` 交集为空 ✓

##### 判决：**成立**

M5 达成判定成立。全部 7 项核验通过：
1. 20/20 `t` + `INTEG-019k` 全 `已验证` ✓
2. 6/6 `m` 全 `里程碑` ✓
3. 门槛 `make test-semihost` EXIT=0（**独立重跑**确认）✓
4. 不回归全绿（**独立重跑** `make check` + `check-no-residue` 确认）✓
5. 7 个 ISS 均处置，无未处置跨模块影响 ✓
6. 3 处口径偏差均为正常变更，非缺口 ✓
7. 未越界，git diff = 7 文件，`spec/` 交集空 ✓

**独立实跑部分**：`make test-semihost JOBS=8`、`make check JOBS=8`、`make check-no-residue`、`python3 tools/integ/check_interface_alignment.py`——全部由 reviewer 独立执行，非采信 engineer/主会话转述。
