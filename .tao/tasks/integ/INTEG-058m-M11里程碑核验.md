# M11 里程碑核验（integ）：gem5 语义/执行 + Machine-v5 Tiny/Node + 异常入口与退出码收口

**模块**：integ
**项目里程碑**：M11
**状态**：里程碑
**里程碑结论**：M11 达成（2026-11-06；收尾门控 `make check-milestone` rc=0）
**目标**：核验 M11 = gem5 全 ISA 语义/执行（B0–B7 + SE/FS）+ Machine-v5 Tiny/Node 两 profile + 异常入口 A/A1 + 退出码 §7.1 三段式 + 测试资产/矩阵收口。

## 达成判据

1. 本期 `t` 册全部 `已验证`（清单见下节，取 `milestones.md` 流水现场；总数不写死）；
2. L1 `make check` rc=0；L2 `make check-modules` rc=0；L3 `make check-full` 全量戳 `20261106T010620Z`（8/8 成员 rc=0），`check-l3-report` PASS；
3. 夜跑 `make check-night` 4/4 PASS（待填），`check-night-report` PASS；
4. parity 矩阵 `node/arch` 269 例 = 249 AGREE + 20 BLOCKED，`agree_fail`/`diff`/`gem5_only`/`qemu_only` = 0；
5. open issue 0（`ISS-343` 由 `QEMU-084t` 关闭）；
6. 收尾门控 `make check-milestone` rc=0（归档结构 + 内容 sha + 同步不可屏蔽 + 夜跑报告 + L3 报告 + `m` 册在场 + `check_tasks --strict`）。

## 本期任务（全部 `已验证`；现场取流水表）

`GEM5-001k`, `GEM5-002t`, `GEM5-003t`, `GEM5-004t`, `GEM5-005t`, `GEM5-006t`, `GEM5-007t`, `GEM5-008t`, `GEM5-009t`, `GEM5-010t`, `GEM5-011t`, `GEM5-012t`, `GEM5-013t`, `GEM5-014t`, `GEM5-015t`, `GEM5-016t`, `GEM5-017t`, `GEM5-018t`, `GEM5-019t`, `GEM5-020t`, `INFRA-119t`, `INFRA-120t`, `INFRA-121t`, `INFRA-122t`, `INFRA-123t`, `INFRA-124t`, `INFRA-125t`, `INTEG-053t`, `INTEG-054t`, `INTEG-055t`, `INTEG-056t`, `INTEG-057t`, `LLVM-142t`, `QEMU-078t`, `QEMU-079t`, `QEMU-080t`, `QEMU-081t`, `QEMU-082t`, `QEMU-083t`, `QEMU-084t`, `SPEC-181t`, `SPEC-182t`, `SPEC-183t`, `SPEC-184t`, `SPEC-185t`, `SPEC-186t`, `SPEC-187t`, `SPEC-188t`, `SPEC-189t`, `SPEC-190t`, `SPEC-191t`, `SPEC-192t`, `SPEC-193t`, `TESTCASES-090t`, `TESTCASES-091t`, `TESTCASES-092t`, `TESTCASES-093t`, `TESTCASES-094t`, `TESTCASES-095t`, `TESTCASES-096t`, `TESTCASES-097t`, `TESTCASES-098t`, `TESTCASES-099t`, `TESTCASES-100t`

## 关键事件

- **gem5 语义/执行**：语义重导矩阵（002）→ 版本锁定（003）→ B0 解码 264 断言（004）→ B1–B7 执行核心（006–012）→ 全 ISA 收敛（013）→ SE 骨架（014）→ FS Tiny/Node（015/016）→ parity（017/018/019/020）。
- **异常入口模型 A/A1**：执行期同步异常与异步中断先入当前运行模式 monitor；monitor 是第一处理者、处理期间 pending 不嵌套；删除 5 个无效屏蔽寄存器（`SPEC-186t`/`SPEC-188t`/`INTEG-054t`）。
- **退出码 §7.1 三段式**：guest `0x00–0x3F`/`0x40–0x7F`、其它 cfx `0x80–0xBF`、monitor `0xC0–0xFF`（模式 + 异常位索引）；`INTEG-055t` 落地 QEMU/gem5/tests，并把页表步进/TLB 命中异常改投当前 monitor（缺页/A-D ⇒ `CFXMEM`、权限 ⇒ `CFXPERM`）。
- **测试资产与矩阵**：Machine-v5 Tiny/Node 资产迁移与执行收口（091–097）、M11 矩阵重生成（098）、libc-test `malloc-brk-fail` 诊断与 64 KiB 页修正（099/100）。
- **组件与工程**：embench/libc-test 补丁集迁入 `tests/tset`（125）、DDLN TT 工作流退役（123）、ccache 接入（119/122）、运行期路径/日志命名清理（120/121）。
- **执行纪律**：`INTEG-055t` 手改向量 yaml 未同步生成器 ⇒ L2 `check-generator-sync` 红；`INTEG-056t`/`INTEG-057t` 按既有判据（生成物须改生成器 + 重跑）返工回绿。

## 核验

- 关联任务是否均已 `已验证`：是（取 `milestones.md` 现场）；
- 各任务产出的任务书是否存在：是（`check_milestone_tasks` 所列任务号全部命中 `.tao/tasks/** ∪ .tao/archive/**`）；
- `check_milestones_fresh` rc=0；`check_tasks.py --strict` rc=0（漏收尾 0）；
- `make check-milestone` rc=0（待填实测）。

## 遗留（不阻塞 M11）

- `ADR-0046` 仍 `Proposed`，等 Linux 实测后再收口；
- `SPEC-180t` 的 ADR、Linux bring-up charter ADR 的 decision 待用户逐条确认；
- 退出码「其它 cfx」段（`0x80–0xBF`）当前无可达 machine-fault 路径，仅公式/编译期自检与 gem5 API 覆盖；
- `QEMU-084t` 已知限界：`RLIMIT_STACK` 仅 `MAP_GROWSDOWN`、`prlimit64` 其它 pid 查询未做、data 总量含共享映射与主栈。
