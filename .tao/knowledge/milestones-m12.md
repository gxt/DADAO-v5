# 项目里程碑

> **项目里程碑 = M12**（M12 台账的唯一断言；`check-milestones-fresh` 按本断言把任务号路由到本页；M11 台账已随归档删除）

> **本页只维护 M12 任务台账**：M11 及以前已归档（`.tao/archive/M11/`，活台账已删除）；历史任务见 `.tao/archive/`；当前讨论/规划见 `.tao/knowledge/discussing.md`。

> **双台账口径**（用户 2026-11-08）：「从 M12 开始，任务书都带上里程碑……milestones.md 也改为 milestones-m12.md」⇒ 任务号 `m12-<module>-<NNNN>`（无 k/t/m 后缀），台账按任务书 `**项目里程碑**` 字段分派，两文件互不影响；M12 任务的派单/完成只改本页。

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
| m12-chipyard-012 | 3–4 h | FP 转换（f2i/i2f/格式转换/SBZ/复制） |
| m12-chipyard-013 | 3–4 h | FP 算术（加/乘/FMA/比较/最小最大） |
| m12-chipyard-014 | 3–4 h | FP 除法/开方/取余（允许多周期状态机） |
| m12-chipyard-015 | 2–3 h | FP 取整/缩放/符号（收齐 47 条 FP 指令） |
| m12-chipyard-016 | 3–4 h | T0 冒烟（inst 全量非 cfx + embench + tset 子集，三平台） |
| m12-chipyard-017 | 4–6 h | T1 适配集 + M12 验收 |

## 进行中（已派单：待开始 / 待验收 / 待返工）

| 编号 | 派单时间 | 预估时间 | 一句改动 |
| --- | --- | --- | --- |
| m12-chipyard-011 | 2026-11-11 14:36 | 4–5 h | FP 基础设施（recFN 编解码 + 六档舍入 + 异常标志 + 分类） |

## 已验证

| 编号 | 完成时间 | 一句改动 |
| --- | --- | --- |
| m12-chipyard-010 | 2026-11-11 14:36 | 位操作 + 原子（`lr`/`sc` 24 形式、保留标记四路径）+ `fence`/`swym`（621/141/202 例） |
| m12-chipyard-022 | 2026-11-11 10:34 | 修预取回归（`pfAddrLegal` 判待发 beat；prefetch 0→338、p50 8→1）+ 补 `prefetch>0` 门控 |
| m12-chipyard-009 | 2026-11-11 09:29 | 控制流 + RAS（63 槽、溢出写 MRPTR-8、下溢先读再判，精确 RASOF/RASUF） |
| m12-chipyard-008 | 2026-11-11 07:12 | 访存：`ld`/`st` 全宽度 + `ldm`/`stm`（8B beat、byte mask、精确 MALIGN/CFXMEM） |
| m12-chipyard-019 | 2026-11-11 04:18 | `cfx_power`/`cfx3` 寄存器组 + 五类同步异常进 hmon（`escape` 0/+4） |
| m12-chipyard-020 | 2026-11-11 00:38 | 取指预取优化：4 预取槽 + 数据优先仲裁（跨 beat 8→p50=1） |
| m12-chipyard-007 | 2026-11-10 19:24 | Tiny BootROM 固定固件 + power 搬运 + 最小 hmon handler（56 B） |
| m12-chipyard-018 | 2026-11-10 16:21 | 核心结构改造：双 TL 端口 + 8-beat 取指 + FSM 骨架 |
| m12-spec-004 | 2026-11-10 12:14 | hmon 装载契约（BootROM→power 搬运）+ rc10 初值/对齐 + `cfx2*` 口径 + 退出码只定编码 |
| m12-spec-003 | 2026-11-10 09:30 | `Machine-v5` 口径统一（reserved 改为引用上游 / `switch_run_mode` 读回 3 / 修 `DADAO-12` 笔误） |
| m12-chipyard-005 | 2026-11-10 02:16 | 解码器 + 整数 ALU + 寄存器堆（273 例三方一致，含 ILLI/UNDI） |
| m12-spec-002 | 2026-11-10 02:16 | Tiny 引入 cfx_power + cfx3 hmon 规范 + 只读锁（0.4.2-rc） |
| m12-chipyard-006 | 2026-11-10 00:48 | 多周期状态机设计（12 态 FSM + 转移表 + hmon 异常/ip 语义 + §9 spec 偏差清单） |
| m12-infra-003 | 2026-11-09 19:02 | 子模块补丁机制（manifest/apply/make_patch/check_patch_tree + testchipip 试点） |
| m12-chipyard-004 | 2026-11-09 14:06 | harness 侧 semihosting 应答者（最小 5 服务 + 核内抬边界） |
| m12-chipyard-003 | 2026-11-09 11:24 | BootROM + `loadmem` 最小闭环（ELF 落 SRAM、复位跳转、可观测结果） |
| m12-chipyard-002 | 2026-11-09 05:22 | Tiny 地址图落地（BootROM `0xffff_ffff_0000` + SRAM 8 MiB，paddrBits≥48） |
| m12-integ-001 | 2026-11-09 03:17 | 移除过渡别名（`dadao-m1`、`profile=node`） |
| m12-testcases-001 | 2026-11-09 02:27 | 测试与 profile 迁移到 `tiny`/`vast`（yaml/inc/env/46 文件） |
| m12-chipyard-001 | 2026-11-09 01:25 | chipyard 补丁集接入 + `dadao-wuming` 最小骨架（外壳 B，core 桩） |
| m12-infra-002 | 2026-11-09 01:25 | 取消 m 册门控（m 册从必需改为可选，其余校验项保留） |
| m12-gem5-001 | 2026-11-09 00:25 | gem5 FS profile `node`→`vast`（保留 node 过渡别名） |
| m12-qemu-001 | 2026-11-08 23:19 | QEMU 拆两台机器 `dadao-tiny`/`dadao-vast`（保留 m1 过渡别名） |
| m12-spec-001 | 2026-11-08 22:25 | 机器命名定稿 Tiny/Vast（spec + contracts + docs，含锁更新） |
| m12-infra-001 | 2026-11-08 21:38 | M12 编号与独立台账脚手架（新旧编号并存 + A6 路由 + `--file`） |
