# gem5 组件

gem5 DADAO 裸机全系统目标，基线为官方 `v25.1.0.1` 的完整提交
`c8222cc67a399bfc01e8658dd14b30d5bfd634f9`（`ADR-0024`）。

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

截至 2026-10-12 的阶段性进度：`GEM5-003t` ISA 骨架经独立审阅，
`GEM5-004t` 已加入部分标量立即数和控制流语义，`make test-gem5`
有 50 条运行用例通过。任务 004 的访存、调用返回和 RAS，以及任务
005–008 的平台与全量验收仍未完成。状态和复现证据见
`evidence/GEM5-003t.md`、`evidence/GEM5-004t-checkpoint.md`。
