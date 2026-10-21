# gem5 组件

gem5 DADAO 裸机全系统目标，基线为官方 `v25.1.0.1` 的完整提交
`c8222cc67a399bfc01e8658dd14b30d5bfd634f9`（`ADR-0035`）。

`make fetch-gem5` 只取该组件并核对 tag 与锁定 SHA；
`make apply-gem5` 只重放 gem5 补丁，重复调用保持 base+1 的干净工作树。源码位于
`.work/source/gem5`，`.cache/gem5.git` 保存浅层对象；入库定制源码
仅通过 `patches/<上游相对路径>.patch` 和按路径排序的 `series` 保存。
补丁组织遵守 `docs/Process-01-组件补丁组织与构建编排.md`。

上游 SCons 编译需要 C++ 编译器、SCons、m4、Python 开发头与可嵌入库、
zlib 开发头；gem5 向量清单脚本另需 PyYAML。protobuf 只在需要 tracing 时使用。Ubuntu 主机可运行
`sh tools/gem5/bootstrap-ubuntu-deps.sh` 把缺少的依赖提取到
`.work/deps/gem5/`，不改系统目录；`tools/gem5/run-scons.sh` 自动选用
这份本地依赖。基线检验命令为
`tools/gem5/run-scons.sh build/NULL/gem5.opt -j8`；`make build-gem5`
构建 ISA 专用 `build/DADAO/gem5.opt`，`make test-gem5` 运行代表向量。
`.work/` 下的依赖与构建产物均不进入 git。

首阶段 `GEM5-002t` 建立精确锁、构建依赖与补丁可重放基线；后续任务
依次实现 DADAO ISA、`Machine-01` 平台和集成回归。未通过执行门控的
能力不得视为已实现。

截至 2026-10-21：`GEM5-003t` ISA 骨架与 `GEM5-004t` 标量语义均经
独立审阅并标记 `已验证`。004 已实现当前有 active 向量的全部 151 个
M1 指令 ID，包括整数/地址运算、RD/RB/RA 访存、控制流和 RegRAS/MemRAS；
current 510 条、003 skeleton 61 条及三条 smoke 序列均通过。005 已实现
Machine-01 的 ELF/PT_LOAD、boot ROM、16 MiB RAM、模式移交、cfx
trap/escape/异常路由和 25 项 semihosting，47 项机器门控通过；工具链生成的
真实 boot ROM + ELF 集成探针亦通过，已验收为 `已验证`。006 已补齐
RF/FCSR、60 条 FP、M3 `sub.o`、7 条 M8 指令；007 又同步实现 `aip.si`。
2026-10-21 随上游 M9 编码迁移补齐 `ext/shl` 新位置与 8 条 `rol`，
并保持 27 条 excluded（含 `fence` + 24 条 `lr/sc`）触发 `ILLI`；
静态覆盖为 259/259，完整门控包含 329 条独立 FP oracle、620 条 remaining、20 条适用 E2E
和 38 条 Embench 正确性用例。代表程序集接入 L2，完整程序集接入 L3；
Machine-00 的 gem5 能力逐格附证。008 专项代表/完整档与反例已复验，
仓库级 L1/L2/L3 与专项完整门控均通过，裸机闭环已置为 `里程碑`。状态和复现
证据见 `evidence/GEM5-003t.md`、`evidence/GEM5-004t.md`、
`evidence/GEM5-005t.md`、`evidence/GEM5-006t.md`、
`evidence/GEM5-007t.md`、`evidence/GEM5-008m.md`；早期 50 条阶段结果保留在
`evidence/GEM5-004t-checkpoint.md`。
