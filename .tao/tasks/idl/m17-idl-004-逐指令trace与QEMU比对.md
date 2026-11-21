# m17-idl-004: 逐指令 trace 与 QEMU 比对

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-003`（执行器核心）
**可并行分片**：否
**预估**：2–3 天
**档位**：中改
**状态**：待开始

## 拆分说明（用户 2026-11-21）

从原 `m17-idl-003` 拆出：trace 格式、文档化与逐指令比对独立成件，便于单独验收。

## 目标

1. 逐指令 trace：`pc / 助记符 / 目的寄存器 / 值 / 异常码`；字段与 M20 的 Minor/wuqing 复用一致；
2. trace 格式落 `docs/`（一份格式说明 + 示例），不复制任务流水；
3. 与 QEMU 同镜像**逐指令 trace** 比对 ≥20 例（挑 `tests/inst` 已有载体，不新造向量）；
4. trace 输出不得逐条落盘成巨文件（>1 MiB 须分块或摘要）。

## 验收（真实 rc）

1. ≥20 例逐指令 trace 与 QEMU 逐行相等（允许文档化的等价写法，逐条说明）；
2. 格式文档存在并与实现一致（样例由脚本生成，不手抄）；
3. **可达 FAIL ≥2 路**：① trace 少记一条指令 ⇒ 比对红；② 异常码映射错 ⇒ 异常例红；
4. 门控：`check-idl-parse`、`check-idl-sync`、`check-knowledge-refs` rc=0。

## 约束

独立 `git worktree`；不提交 git；不改 QEMU/gem5/RTL；术语「寄存器组」；完成区 ≤30 行。

## 从 `m17-idl-003` 交接的坑（2026-11-21，实测）

1. QEMU `-accel tcg,one-insn-per-tb=on -d cpu` 记录的是「指令执行前」状态，且会在部分 `br.nz` 处**重复一条记录**、**不为取指异常（IALIGN/CFXMEM fetch）出记录** ⇒ 逐指令比对必须按 **PC 对齐**，不能逐行（escape 例 QEMU 1160 记录 vs 执行器 295 条指令）。
2. QEMU 对「无返回」semihosting 服务写 `rd8=0xdeadbeef`（`common_semi_dead_cb`），非架构语义；`ra1..ra63` 在 `RACNT` 有效区外未定义（`SimRISC-00 §2.4`）——这两处只能**文档化等价**。
3. QEMU 11 system 模式没有 `-singlestep`，只能用 `-accel tcg,one-insn-per-tb=on`。
4. 执行器是「按 `.idl` 正文逐 id 手写」而非通用 AST 求值器；28 例实际执行 54 个 id，未注册 id 一律显式 `ExecError`（`add.ut`/`ld.t` 等模型不确定的刻意不注册）；`U04`–`U10` 宽度裁定仍未取。
