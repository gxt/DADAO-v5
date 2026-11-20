# m17-idl-003: 执行器（四寄存器组状态 / ELF / 逐指令 trace / 最小 trap）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-002`（解析器）
**可并行分片**：否
**预估**：5–7 天
**档位**：大改
**状态**：待开始

## 目标

1. 四寄存器组状态（`rd`/`rb`/`rf`/`ra`）、48 位地址、大端显存模型；
2. ELF 加载：复用 `tools/testcases/lib/machine_profile.py` 的运行布局，**不另造第二份机器真源**；
3. **逐指令 trace**：`pc / 助记符 / 目的寄存器 / 值 / 异常码`；格式落 `docs/`（M20 的 Minor 与 wuqing 复用同一格式）；
4. 最小 trap/monitor：`trap`/`escape` 按 `contract-see`，够跑 `tests/inst` 的同步异常例；
5. 跑通 ≥20 条代表 operation（算术 / 访存 / 控制流 / 异常各类都要有）。

## 验收（逐条贴真实 rc）

1. 与 QEMU 同镜像**逐指令 trace** 比对 ≥20 例（挑 `tests/inst` 已有载体，不新造向量）；
2. trace 格式文档化，字段与 M20 复用一致；
3. **可达 FAIL ≥3 路**：① 破坏一条算术宽度规则 ⇒ 比对红；② 大端读改写小端 ⇒ 访存例红；③ 异常码映射错 ⇒ 异常例红；
4. 门控：`check-idl-parse`、`check-idl-sync`、`check-knowledge-refs` 真实 rc。

## 约束

独立 `git worktree`；**不提交 git**；**不改 QEMU/gem5/RTL**；trace 不得逐条落盘成巨文件（超 1 MiB 须分块或摘要）；完成区不写具体 `.work/**` 路径。
