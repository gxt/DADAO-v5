# 项目里程碑

> **项目里程碑 = M10**（当前里程碑；`check-milestone` 取 `项目里程碑 = M<n>` 断言的**最大 n**，本行是唯一断言）
>
> 只维护任务流水；历史任务见 `.tao/archive/`，当前讨论/规划见 `.tao/knowledge/discussing.md`。
>
> **M9 归档指针（2026-11-01）**：M9 任务书 **68** 册 + 根级核验册 `INTEG-037m` 与 M9 期关闭 issue **83** 条已冻结到 `.tao/archive/M9/`（`README.md` / `m9-retrospective.md` / `issues-closed.md`）；流水 **69** 行已冻结到 `.tao/archive/M9/README.md §2`，本页不再保留 M9 行。
>
> **M10 归档指针（2026-11-01）**：M10 任务书 **71** 册（含核验册 `INTEG-052m`）与 M10 期关闭 issue **17** 条已冻结到 `.tao/archive/M10/`（`README.md` / `m10-retrospective.md` / `issues-closed.md`）；流水 **70** 行已冻结到 `.tao/archive/M10/README.md §2`，本页仅留 M10 后维护行（`check-milestones-fresh` A1/A2 对归档册同样生效，已归档号豁免回填）。

## 任务流水

| 编号 | 状态 | 完成时间 | 一句改动 |
| --- | --- | --- | --- |
| GEM5-007t | 已验证 | 2026-11-02 12:26 | B2 16 位立即数执行：8 条 rwii（or.w/andn.w/set.zw/set.ow/set.w），含 wyde 选择与 rf0 FCSR 掩码 |
| GEM5-006t | 已验证 | 2026-11-02 11:52 | B1 取数存数执行核心：38 条 load/store + ldm/stm 语义与定向断言 |
| QEMU-078t | 已验证 | 2026-11-02 10:56 | scaleB C1 第三源 rdHD + sc rdHB=rd0 静态 ILLI；QEMU trans/helper |
| LLVM-142t | 已验证 | 2026-11-02 10:55 | scaleB C1（第三源 rf→rd）+ sc rd0 汇编期 ILLI；LLVM TD/MC/CodeGen |
| GEM5-005t | 已验证 | 2026-11-02 10:54 | scaleB C1 第三源 rf→rd + sc rd0 的 gem5 decode/断言更新 |
| SPEC-181t | 已验证 | 2026-11-02 10:53 | gem5 语义契约收口：ADR-0044 Accepted、FP remainder/scaleB/f2i、call IP+4、sc rd0、保留粒度 |
| TESTCASES-090t | 待验收 | 2026-11-02 07:07（登记） | scaleB/sc 测试；LLVM lit/isa matrix 已同步；QEMU/gem5 对照 BLOCKED |
| GEM5-004t | 已验证 | 2026-11-01 23:40 | B0 解码核心 + 264 条解码断言（388 反例）；gem5 骨架可构建，B1–B7 留边界 |
| GEM5-002t | 已验证 | 2026-11-01 22:28 | M11 指令语义重导矩阵：逐条对照当前 spec 与 0628/PR，禁止同助记符默认复用 |
| GEM5-003t | 已验证 | 2026-11-01 22:02 | gem5 锁定 v25.1.0.1 / c8222cc6；组件暂 disabled，G1 建骨架后启用 |
| GEM5-001k | 已验证 | 2026-11-01 21:42 | M11 启动：gem5 FS/SE 差距矩阵、测试复用与任务拆分 |
| INFRA-113t | 已验证 | 2026-11-01 15:31 | M10 后清理：退役失效 M1 门控判据（check_issues/Process-04）+ 清 ADR-0030/M9 过时 known-fail 基准 |
| INFRA-118t | 已验证 | 2026-11-01 15:04 | M9/M10 根级 INTEG m 册迁入 integ，归档根仅三件套 + 模块任务书 |
| INFRA-117t | 已验证 | 2026-11-01 14:33 | M1–M10 归档归一：M9/M10 流水冻结、M6/M2 状态、M7 notes 并入回顾 |
| INFRA-116t | 已验证 | 2026-11-01 14:06 | Process-04 归档规则修订（m 可选/流水落 README/三文件）+ check-archive 门控 |
| INFRA-115t | 已验证 | 2026-11-01 13:02 | tests/inst 计数 152→156、生成器 `--check` 措辞列名化、anti_forgery 迁 tests/inst；新 check-generator-sync 挂 L2 |
| QEMU-077t | 已验证 | 2026-11-01 11:45 | helper.c/cpu.h 注释 reserved cfx 7-14→6-14 与宏一致；补丁重导出，行为不变不重建 |

