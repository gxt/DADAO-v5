# 项目里程碑路线图

项目级里程碑（跨模块），由各模块的里程碑支撑（模块里程碑见 `.tao/tasks/<module>/` 的 `m` 文件）。主会话在依赖的模块里程碑均达成为 `里程碑` 后，将本项目里程碑置为 `达成`。

路线参考 DADAO-0628（`.work/DADAO-0628`）。

**M1 — MC + QEMU 标量核心 + MC↔QEMU 集成**

目的：`llvm-mc` 能汇编/反汇编全部 M1 指令；`qemu-system-dadao` 能在 MMU-off 裸机模式执行标量程序；独立测试向量经「MC 汇编 → QEMU 执行 → 结果比对」一致，形成 MC↔QEMU 集成闭环。门槛：`make build-mc` / `build-qemu` / `test-interface` 全绿。

**M2 — Basic CodeGen**

目的：`llc` 将标量整数/指针函数（LLVM IR）编译为 DADAO 汇编，经 MC → obj → 链接 → QEMU 执行结果正确（freestanding、same-TU，不含变参/聚合）。门槛：`make test-codegen` 全绿，至少一个算术/访存/分支/调用函数端到端在 QEMU 得到期望结果。

| 项目里程碑 | infra | spec | testsuite | golden | llvm | qemu | verif | gem5 | sail | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M1 | `INFRA-008m` | `SPEC-011m` | `TESTSUITE-010m` | — | `LLVM-011m` | `QEMU-013m` | `VERIF-012m` | — | — | 待开始 |
| M2 | — | — | — | 待规划 | 待规划 | — | 待规划 | — | — | 待开始 |
