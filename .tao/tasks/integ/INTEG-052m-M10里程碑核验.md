# M10 里程碑核验（integ）：cfx 空间/权限/启动链 + 工具链与测试收口

**模块**：integ
**项目里程碑**：M10
**状态**：待验收
**里程碑结论**：M10 达成（2026-11-01，`check-night` 4/4 PASS）——**收尾门控待 `INFRA-114t` 修复后置回 `里程碑`**
**目标**：核验 M10 = cfx 五步（地址空间 / PTE / TLB / DMA / 启动链）+ 两轴权限模型 + cfx_time 与异步中断仲裁 + 规范/工具链/测试框架收口。

## 达成判据

1. 本期 `t` 册全部 `已验证`（清单见下节，取 `milestones.md` 流水现场；总数不写死；`INFRA-114t` 为 M10 收尾补丁，待开工）；
2. 夜跑 `make check-night` **4/4 PASS**：tset libc-test / llvm-ts / embench + arch cfx 四行 `rc=0`，`NIGHT_EXIT=0`；报告 `.dadao/tests/night/2026-11-01-08/`（`manifest.tsv` / `run.log`）；
3. **open issue 0**：`check_issues.py` 报 `0 open, 17 closed`；
4. L1 `make check` rc=0（2026-11-01）；L2 `make check-modules` rc=0（同日）；L3 全量戳 `20261031T170934Z`（8 行 `rc=0`，`check-l3-report` PASS）；夜跑报告 `check-night-report` PASS；
5. `ADR-0017` D10（数组 stride）修订已落地；`SPEC-180t` 的 ADR 待用户逐条裁定，属遗留、不阻塞 M10；
6. **收尾门控 `make check-milestone` rc=0**——现卡在 `check-sync-nonmaskable`（`PMEM_DMA` 白名单缺口），
   须由 `INFRA-114t` 修复后复跑（本册随该依赖置回 `里程碑`）。

## 本期任务（除 `INFRA-114t` 待开工外全部 `已验证`；现场取流水表）

`TESTCASES-089t`, `TESTCASES-088t`, `SPEC-180t`, `LLVM-141t`, `INTEG-051t`, `INFRA-112t`, `INTEG-050t`, `TESTCASES-087t`, `TESTCASES-086t`, `INTEG-049t`, `TESTCASES-085t`, `INTEG-048t`, `SPEC-179t`, `INTEG-047t`, `INTEG-046t`, `INTEG-045t`, `INTEG-044t`, `INTEG-043t`, `INTEG-042t`, `INTEG-041t`, `SPEC-178t`, `INTEG-040t`, `LLVM-140t`, `INTEG-039t`, `INTEG-038t`, `TESTCASES-084t`, `LLVM-139t`, `LLVM-138t`, `LLVM-137t`, `LLVM-136t`, `TESTCASES-076t`, `TESTCASES-083t`, `TESTCASES-082t`, `TESTCASES-077t`, `TESTCASES-081t`, `TESTCASES-078t`, `TESTCASES-080t`, `TESTCASES-079t`, `TESTCASES-075t`, `TESTCASES-074t`, `TESTCASES-073t`, `TESTCASES-072t`, `TESTCASES-071t`, `TESTCASES-069t`, `TESTCASES-068t`, `TESTCASES-070t`, `INFRA-110t`, `SPEC-177t`, `LLVM-135t`, `TESTCASES-067t`, `QEMU-076t`, `SPEC-176t`, `SPEC-175t`, `TESTCASES-063t`, `SPEC-174t`, `QEMU-075t`, `INFRA-108t`, `LLVM-134t`, `TESTCASES-064t`, `LLVM-132t`, `INFRA-109t`, `LLVM-133t`, `TESTCASES-065t`, `QEMU-074t`, `SPEC-173t`, `INFRA-107t`, `LLVM-131t`, `INFRA-106t`, `LLVM-130t`

M10 收尾补丁（`待开始`）：`INFRA-114t`（`check-sync-nonmaskable` 白名单补 `PMEM_DMA`；M10 收尾门控依赖它回绿）

## 说明

- `INFRA-113t`（M10 后清理：退役失效 M1 门控判据 + 清 ADR-0030/M9 过时 known-fail 基准）**不纳入 M10**：M10 达成后登记，状态 `待开始`。
- `INTEG-037m`（M9 核验册）已于 2026-11-01 移入 `.tao/archive/M9/`，不属本期；留在活目录会被 `check-milestone` 误判为当前 M10 的 m 册。
- **册内不写自身任务号**（本册任务号只在文件名出现）：`check-milestones-fresh` A2 要求 m 册列出的
  任务号都在流水表或归档，而 m 册按 `里程碑` 状态不入流水（流水只收 `待开始/待验收/待返工/已验证`）
  ⇒ 自指必假红。原始 `INTEG-037m` 靠一条 `已验证` 流水行绕开，本册沿用「不入流水」口径。
- **M10 收尾依赖 `INFRA-114t`**：`check-sync-nonmaskable` 现 **红**——`spec/DADAO-12` 异常原因表把异步源 `PMEM_DMA` 标「可」（自 `INTEG-042t` 起，语义正确），而门控白名单只认 `IPI`/`TIMER`/`UART<n>`/`...`；修白名单（不改 spec 语义）后 `make check-milestone` 方可回绿，届时本册置回 `里程碑`。
- 遗留（不阻塞 M10）：L3 报告戳 `20261031T170934Z` 为 M10 期内最后一次全量；`ADR-0046` 仍 `Proposed`；`SPEC-180t` 的 ADR 待裁定。

## 核验

- 关联任务是否均已 `已验证`：除 `INFRA-114t`（`待开始`，M10 收尾补丁）外全部 `已验证`（`check_milestones_fresh` A1 逐行核对通过）；
- 各任务产出的任务书是否存在：是（`check_milestone_tasks` 列出任务号全部命中 `.tao/tasks/** ∪ .tao/archive/**`，缺失 0）；
- `check_milestone_tasks.py` rc=0；`check_milestones_fresh.py` rc=0；`check_tasks.py --strict` rc=0（漏收尾 0）；
- `make check-milestone` **rc=2**：`check-spec-archive` / `check-spec-archive-verify` 绿（内容 sha 逐版 OK）、`check-night-report` 与 `check-l3-report` 单独跑 rc=0；整链停在 `check-sync-nonmaskable`（本册引入后未变，待 `INFRA-114t` 修）。

## 关键事件

- **cfx 五步**：地址空间/PTBR/PTW（038）→ PTE 页表步进（039）→ TLB/G/AD/PTWERR（040）→ pmem SRAM + SRAM↔PA DMA（042/043）→ 启动链 power→hmon→smon（046）。
- **权限与空间**：两轴权限模型（044）+ `cg_reg_deleg` 强制检查（048）+ cg7 空间描述（049）+ reserved cfx 清理（045/089）。
- **时限与中断**：`cfx_time` + 单 hart `cfx_hart` 定时器（050）；统一异步中断仲裁（051）；`cfx_pmem` DMA 的 SBI 契约（047）。
- **工具链/测试**：cfx 别名表（135/141）+ 代码模型/代码跨度（131/106）+ 测试框架迁移与门控（067–088）+ 夜跑/L3 报告门控（076/083）。
