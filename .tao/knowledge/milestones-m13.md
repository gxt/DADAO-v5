# 项目里程碑

> **项目里程碑 = M13**（M13 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；`milestones-m12.md` 是 M12；M11 台账已随归档删除）

> **本页只维护 M13 任务台账**：M11 及以前已归档（`.tao/archive/M11/`）；M12 见 `milestones-m12.md`；历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **M13 定位（用户 2026-11-09）**：三平台（qemu / gem5 / chipyard）的**多方差分对比**，含指令语义，尤其是**浮点**；起点 = gem5 超时与运行时间可比性。

本页分三张**任务表**，**表位置 = 任务状态**（不另设状态列）：

| 表 | 收录 | 列 |
| --- | --- | --- |
| 待开始（未开工） | 尚未派单的 `待开始` | `编号` / `预估时间` / `一句改动` |
| 进行中（已派单） | 已派单未合并：`待开始`（实现中）、`待验收`、`待返工` | `编号` / `派单时间` / `预估时间` / `一句改动` |
| 已验证 | `已验证` | `编号` / `完成时间` / `一句改动` |

- **派单即移入**：「待开始」表 = 尚未派单；**派单时**把该行移入「进行中」表并填**派单时间**（不引入新状态）。
- **派单时间**：`YYYY-MM-DD HH:MM`，派单动作发生时由主会话填写。
- **预估时间**：人工估值，只作参考；格式 `N h` / `N–M h` / `N 天` / `N–M 天` / `N min`。
- **完成时间**：`YYYY-MM-DD HH:MM`；「已验证」表按完成时间**倒序**（同时间按编号升序）。
- **一句改动**：≤120 字符，只作索引，细节在任务书。

## 待开始（未开工）

| 编号 | 预估时间 | 一句改动 |
| --- | --- | --- |
| m13-testcases-031 | 1–2 天 | 补 `st.o rb0`（`aip.si` 构造期望）+ `ld.o ra0` 读写（SBZ 写忽略） |
| m13-testcases-014 | 4–5 天 | `02-reg-copy` 16 个 id 改汇编+宏（复制 + `cs.*`） |
| m13-testcases-015 | 2–3 天 | `03-wyde-imm` 8 个 id 改汇编+宏 |
| m13-testcases-016 | 3–4 天 | `04-arith-logic-octa` 算术 15 个 id 改汇编+宏 |
| m13-testcases-017 | 3–4 天 | `04-arith-logic-octa` 逻辑/移位/扩展 14 个 id 改汇编+宏 |
| m13-testcases-018 | 3–4 天 | `04-arith-logic-octa` 位操作 4 个 id 改汇编+宏 |
| m13-testcases-019 | 2 天 | `05-arith-addr` 6 个 id 改汇编+宏 |
| m13-testcases-020 | 3–4 天 | `06-control-flow` 15 个 id 改汇编+宏（含 RAS） |
| m13-testcases-021 | 4–5 天 | `07-floating-point` 算术与最小最大 18 个 id 改汇编+宏 |
| m13-testcases-022 | 4–5 天 | `07-floating-point` 转换/比较/分类 26 个 id 改汇编+宏 |
| m13-testcases-023 | 3–4 天 | `07-floating-point` 取整/缩放/符号 8 个 id 改汇编+宏 |
| m13-testcases-024 | 2–3 天 | `08-arith-logic-tetra` 21 个 id 改汇编+宏 |
| m13-testcases-025 | 2–3 天 | `09-arith-logic-wyde` 21 个 id 改汇编+宏 |
| m13-testcases-026 | 2–3 天 | `10-arith-logic-byte` 21 个 id 改汇编+宏 |
| m13-testcases-027 | 3–4 天 | `11-cfx` 5 个 id 改汇编+宏（cfx/system） |
| m13-testcases-028 | 1–2 天 | `12-misc` 原子 24 个 id 改汇编+宏（`lr`/`sc`） |
| m13-testcases-029 | 1–2 天 | `12-misc` 其余 4 个 id 改汇编+宏（`swym`/`ct*`） |
| m13-testcases-030 | 2–3 天 | `.S` 接入门控 + YAML 退役（ISS-413） |
| m13-spec-006 | 2–3 h | 融合乘加溢出按 IEEE 舍入模式（`SimRISC-07 §2.5`，ISS-399） |
| m13-qemu-007 | 2 h | `ld.t rf0` 只读位（QEMU，争议 6 裁定 A） |
| m13-qemu-008 | 2–3 h | 融合乘加溢出按 IEEE（QEMU） |
| m13-gem5-009 | 2–3 h | 融合乘加溢出按 IEEE（gem5） |
| m13-gem5-008 | 2 h | `ldm`/`stm` 基址重叠 ⇒ ILLI（gem5） |
| m13-qemu-006 | 2 h | `ldm`/`stm` 基址重叠 ⇒ ILLI（QEMU） |
| m13-integ-009 | 4–6 h | FP-IEEE 对齐审计（47 条，等 `015` 后执行） |
| m13-integ-002 | 5–7 h | FP 语义三平台差分（47 条，含舍入/标志） （**暂不进行**，用户 2026-11-11） |
| m13-integ-003 | 4–6 h | 整数与访存三平台差分（inst 全量非 cfx） （**暂不进行**，用户 2026-11-11） |
| m13-integ-005 | 3–4 h | M13 收口（差异归因 + 矩阵冻结） （**暂不进行**，用户 2026-11-11） |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m13-spec-005 | 2026-11-13 07:20 | 2–3 h | `ldm` 禁止基址/索引落入传送范围（ILLI）；`stm` 允许 |
| m13-testcases-013 | 2026-11-12 23:58 | 3–4 天 | `01-load-store` 多元素（`ldm`/`stm` 19 个 id）改汇编+宏 |
| m13-testcases-009 | 2026-11-11 00:09 | 2–3 天 | 208 接跑 A 组 17 例（qemu≤30s 但 7200s 超时）无实际上限 |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m13-spec-004 | 2026-11-13 07:20 | 多元素内存指令允许部分生效（例外收窄到 ldm/stm；寄存器类 12 条仍精确） |
| m13-testcases-012 | 2026-11-12 23:58 | `01-load-store` 单元素 19 个 id 改汇编+宏（331 例 / 68 镜像 / 三方逐字节） |
| m13-testcases-011 | 2026-11-12 18:18 | `fo2ft` 溢出向量 31 例（含轻微 10）+ 三方 496 B 逐字节 |
| m13-qemu-004 | 2026-11-12 16:13 | quiet compare 遇 sNaN 置 `NV`（nf_rule 两档；改前差分恰 4 例） |
| m13-gem5-007 | 2026-11-12 13:24 | `fo2ft` 溢出按 IEEE（gem5 + checker；18 格与 QEMU 逐字节，另测 8 格轻微溢出） |
| m13-spec-003 | 2026-11-12 12:38 | `forem` 的 NaN 优先级按 IEEE §7.2 f)（qNaN×±0 不置 NV、sNaN 置） |
| m13-qemu-005 | 2026-11-12 12:03 | `fo2ft` 溢出按 IEEE 舍入模式（QEMU 18 格 + 改前基线 8 格差） |
| m13-spec-002 | 2026-11-12 11:21 | `fo2ft` 溢出按 IEEE 754-2019 舍入模式（spec + 合约 + 13 册版本互锁升 0.5.7-rc） |
| m13-testcases-003 | 2026-11-12 10:53 | 长尾 7200 s 复跑：A 组 60 例（40/17/3）+ B 组 90 例（85/3/2），逐例表入 TestReports |
| m13-infra-002 | 2026-11-12 01:27 | 引导 ics150–ics180 四台（8 步全绿、check-inst 991/996+44/44、余 252 GB） |
| m13-qemu-003 | 2026-11-12 00:46 | 比较族标志对齐 IEEE（signaling compare 任一 NaN ⇒ `NV`；补上原本缺失的 sNaN 路径） |
| m13-testcases-010 | 2026-11-11 21:12 | 补 `cs.*` 的 not-taken 覆盖（rd 5 条 + rf 6 条；ISS-387 行动项） |
| m13-spec-001 | 2026-11-11 10:23 | 退出码表：`0x00`=PASS、`0x01`–`0x7F`=FAIL（127 点）+ ADR-0004 就地修订 |
| m13-integ-007 | 2026-11-11 05:48 | hmon 改「最小保存-跳转」（11 条指令/44 B，QEMU 先行验证通过） |
| m13-gem5-006 | 2026-11-11 04:52 | 补齐 gem5 hmon 检查器文件（handler/lds/layout + checker 动态派生 md5） |
| m13-integ-004 | 2026-11-11 03:07 | riscv-tests 移植（114 条，可移植 35）+ qemu/gem5 差分（474 例一致） |
| m13-qemu-002 | 2026-11-11 00:33 | QEMU 对齐 Tiny hmon 装载契约（共用 chipyard 同一 BootROM 镜像；L2 全绿） |
| m13-gem5-005 | 2026-11-10 23:58 | gem5 对齐 Tiny hmon 装载契约（共用 chipyard 同一 BootROM 镜像） |
| m13-testcases-008 | 2026-11-10 22:41 | 208 接跑 B 组差集（Y=0，前提过期；登记 4 项 run_pool 缺陷） |
| m13-testcases-007 | 2026-11-10 22:03 | 删除无意义探针 `start_busy_returns_busy`（陷入往返不是时间窗） |
| m13-testcases-006 | 2026-11-10 21:41 | 输出判据改分通道（stdout/stderr 分离；参考按源码拆两路） |
| m13-testcases-005 | 2026-11-10 21:04 | case 级批量测试池（多节点、即产即落、可续跑、xlong 隔离） |
| m13-gem5-004 | 2026-11-10 20:01 | gem5 SE 页表故障投递 guest + 脏页/帧回收修复（`lemon` 全量 0 panic） |
| m13-gem5-003 | 2026-11-10 11:27 | gem5 SE 缺陷：`SYS_WRITE` 句柄越界 + 非对齐 `.bss` 装载（ISS-358/359） |
| m13-integ-001 | 2026-11-10 10:50 | 差分产物归属 + 三平台矩阵生成器（165 行，chipyard 列 N/A） |
| m13-infra-001 | 2026-11-10 09:24 | 工具缺陷修复（gem5 首建 `ValueError`）+ 删除核验册机制 + 台账自动发现 |
| m13-testcases-004 | 2026-11-10 08:27 | 测试报告目录规范（`docs/TestReports/`）+ `check-test-reports` 门控 |
| m13-gem5-002 | 2026-11-10 06:34 | gem5 Tiny 恒 `hypv` + `cg3` 访问限制（ISS-363，与 QEMU 逐字节一致） |
| m13-gem5-001 | 2026-11-10 04:31 | gem5 的 Tiny `cfx_power` + `cfx3 hmon`（36 用例/oracle 148 条，与 QEMU 逐条一致） |
| m13-qemu-001 | 2026-11-10 03:54 | QEMU 的 Tiny `cfx_power` + `cfx3 hmon`（56 条断言，语义逐条对 spec） |
| m13-testcases-002 | 2026-11-09 23:46 | 3–4 h |
| m13-testcases-001 | 2026-11-09 18:26 | static 长尾 72 例 gem5 3600s + QEMU 计时，输出运行时间比率 |
