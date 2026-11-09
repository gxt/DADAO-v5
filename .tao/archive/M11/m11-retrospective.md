# M11 回顾（gem5 第二参考实现 + 全 ISA 收敛 + 测试体系收口）

> **状态**：M11 已于 2026-11-09 达成并归档。本文件是里程碑回顾（历史摘要），不是现行判据；现行规则见 `spec/`、`.tao/contracts/`、`docs/`。

## 1 里程碑目标

M11 的核心是**引入 gem5 作为独立第二参考实现**，把「QEMU 单引擎自证」升级为「QEMU ↔ gem5 同模式双向一致性」，并完成工具链、规范与测试体系的收口：

- gem5 覆盖 **FS + SE**，使用 `AtomicSimpleCPU`，锁 `v25.1.0.1 / c8222cc6`（`ADR-0047`）；
- 同模式配对：gem5 FS 只对 QEMU system、gem5 SE 只对 QEMU user（`ADR-0048` D1）；
- 全 ISA 解码与执行收敛（264 条），SE 覆盖完整 `tset`（静态先行、动态/TLS/线程后补，不降级）；
- 工具链与规范发布：Machine-v5 0.4.0、SimRISC 0.5.6；退出码三段式与转换指令舍入编码迁移收口。

## 2 主要交付

- **gem5 内核**：B0 解码（264 断言，388 反例）→ B1–B7 执行核心（整数/立即数/窄位宽/块搬移/RAS/系统原子屏障/浮点）→ 全 264 执行收敛。
- **gem5 平台**：SE 平台骨架（G1）；FS Machine-v5-Tiny / Node；FS↔QEMU parity、semihosting、`SYS_ELAPSED`/`TICKFREQ`、CFXREG 目标对齐。
- **gem5 SE 能力**：heap/VMA（brk/mmap/mremap）、文件 IO 与时钟、信号与 rlimit、IPC/多进程、线程/futex/TLS、动态链接装载器、mmap+ldso、syscall 语义对齐、mprotect/rlimit、`chmod`/`fchmodat`。
- **QEMU 收敛**：Tiny/Node 系统机、user 页大小 12→16、`cfx_power` 按 profile、CFXREG 目标改当前 monitor、guest rlimit、mremap 限额检查。
- **测试体系**：L3 探针/异步/boot-chain、lit/codegen/ir-lli 基线、QEMU↔gem5 矩阵重生成、timing 探针去 icount、SE 基线预算与动态档、G3 完整 tset 双向一致性、回归运行（原夜跑）加 gem5 SE/FS 成员。
- **工具链/规范**：退出码迁移（SPEC/LLVM/QEMU/gem5/tests 五面）、转换指令舍入编码三分（`ADR-0050`）、Machine-v5 发布 0.4.0、SimRISC 发布 0.5.6。
- **基础设施**：ccache 接入 LLVM/QEMU、任务书运行期路径清零、节点引导/远程派单/镜像同步、chipyard 子模块离线镜像、里程碑三分表与引用/临时目录门控。

## 3 关键决策

- `ADR-0047` gem5 版本与组件基线（完整 commit 锁定，tag 仅作标识）。
- `ADR-0048` QEMU/gem5 同模式一致性与 M11 测试覆盖（D1 配对、D2 比较内容、D3 测试复用、D4 全覆盖、D5 差异处置）。
- `ADR-0049` 测试运行环境分层（Tiny / Node / SE）。
- `ADR-0050` 转换指令舍入方向编码（六档 / SBZ / 计数三分）。
- 历史注记：`ADR-0046`（CFX 寄存器实现裁剪与 usage profile）在本里程碑结束时仍为 `Proposed`。

## 4 未决与遗留（不阻塞达成）

- **B7 浮点 BLOCKED**：picolibc `math_test`（`GEM5-015t` 记录）。根因已由 `GEM5-032t` 定位为「缺陷已关闭、可注销登记」；注销执行待 `GEM5-033t`（`待开始`，待用户裁定后派）。归档时仍按 BLOCKED 计，不计入通过数。
- **6 条 open issue 转入后续里程碑**：`ISS-345`（gem5 futex 细节）、`ISS-355`（`build_gem5.py` 首次构建目录）、`ISS-356`（`check_milestone_tasks.py` 基线残留）、`ISS-357`（SE stdout/stderr 顺序）、`ISS-358`（semihosting 句柄越界）、`ISS-359`（SE loader `.bss` 对齐）。详见活台账 `.tao/knowledge/issues.yaml`。
- **回归运行（原夜跑）**：M11 期最后一次完整报告为 2026-11-05-13（4/4 成员 `rc=0`）；2026-11-06-09 启动后无产物（未完成）；`TESTCASES-105t` 新增 gem5 SE/FS 成员后尚未跑完整成员集。按用户 2026-11-08 裁定，回归运行**不作为 M11 收口条件**，只作观测记录。
- **M10 后（维护）任务**：`INFRA-113t`/`115t`/`116t`/`117t`/`118t`、`QEMU-077t` 字段为 `M10 后（维护）`，不属 M11 字段、不入本归档，仍留活台账。

## 5 教训（可复用）

1. **跨引擎输出比较要先固定可见面**：gem5 SE 的 stdout/stderr 交错顺序与参考不同，导致至少 4 例仅差输出串接顺序（`ISS-357`）。比较口径必须显式（逐 fd 或显式串接），不能假定「日志一样」。
2. **基线驱动「写完报告即 rc=0」会假绿**：`TESTCASES-103t`/`104t` 的驱动写完 JSON 就成功，交叉失败不会让回归成员变红 ⇒ 成员命令必须自带结果 guard（`TESTCASES-105t`）。
3. **「跑过了」不等于「可复核」**：L3 报告引用运行期日志路径，工作树清理后日志消失会使 `check-l3-report` 红。里程碑收口要在**持久证据目录**重跑一次，报告与日志同时可用。
4. **归档白名单要跟模块演进**：M11 首次归档 gem5 任务，`check_archive` 的子目录白名单原先不含 `gem5`，本期已同步（机械扩展，不改归档语义）。

## 附录 A：归档边界

- 本归档收录字段 `**项目里程碑**：M11` 且状态 `已验证` 的任务书 **106** 个；任务流水冻结在本目录 `README.md` §2。
- `GEM5-033t`（`待开始`）与归档任务 `INTEG-061t` 不入本快照；前者留活按用户裁定派工，后者验收后由 architect 最后 `git mv` 入 `integ/`。
- M11 期关闭 issue 快照见本目录 `issues-closed.md`（14 条）；活台账只留 6 条 `open`。
