# m17-idl-025: trace 入口态纳入 cfx 计数与掩码（计数严格相等，不跳过）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-022/023/024`（trace 比较与环形布局）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：待开始

## 背景（用户 2026-11-27 口径）

trace 比较规则按寄存器类别区分（`ISS-left-003`）：

- **确定性计数**（`cg4 rc2 trap_num`/`rc3 excp_sync_num`/`rc5 escape_num` 等，由复位态 + 指令流唯一决定）⇒ **必须严格相等**，不得跳过；
- **依赖时序/历史的计数**（如 `excp_async_num` 一类）⇒ 允许用增量/阈值（当前 Tiny 单 hart 无异步进入，暂无实例，不预先实现机制）；
- 平台不存在的寄存器 ⇒ 另行处置（`m17-testcases-008`），不属本任务。

实测（`/tmp/opencode/m17-trace-final.log`）：`escape_ciii_cfx` 第 26 条（pc `0xffffff010164`，`cfx2rd cfx_hmon, cg4, rc5`）exec `0` vs QEMU `1`。根因：trace 入口态（`idl/tools/idl_qemu_state.py`）只解析 `{ip, mode, cfx, rd/rb/rf/ra}`，**丢弃** QEMU `-d cpu` 已输出的 cfx 计数与掩码；IDL 从应用入口 seed 时计数从 0 起、QEMU 保留启动链结果。

## 要做

1. `idl/tools/idl_qemu_state.py`：解析同一条 `CFX%02d` 行的 `TRAPN/SYNCN/ASYNCN/ESCN/SCRN/GIM`（以及 `ID/VER`），按 cfxha 存入入口态（字段名自定，文档同步）；
2. `idl/tools/idl_exec.py:load_state()`：把上述 cfx 计数/掩码写入对应 cfx 面（`cg4`、`cg15 rc3`）；**只做初始状态 seed**，运行期不得用 QEMU 值覆盖/跳过任何比较；
3. 比较器不改：计数类在 trace 中天然经 `dst/val` 严格比较；
4. `idl/docs/trace-format.md`：写明入口态字段与「计数类比较规则」（确定性计数严格相等；历史依赖计数才允许阈值，当前无实例；平台缺失寄存器归用例/DIV，不在 trace 里跳过）；
5. 全量 `idl_check_trace` 应 **274/274**（不再有 `escape_ciii_cfx` 红）。

## 不做

- 不改 QEMU/gem5/chipyard/RTL（QEMU dump 已含所需字段）；
- 不改 `m17-testcases-008` 的用例（Tiny 缺寄存器属该任务）；
- 不预造阈值机制（无实例）。

## 约束

- 独立 `git worktree`；不提交 git；只动 `idl/tools/{idl_qemu_state.py,idl_exec.py}`、必要时 `idl/docs/trace-format.md`、本任务书；完成区 ≤30 行。

## 验证

1. 全量 trace **274/274**；`--only escape_ciii_cfx` 绿；
2. **可达 FAIL ①**：把 seed 的 `ESCN` 值改错（+1）⇒ 第 26 条必红；`cp`+md5 还原回绿；
3. **可达 FAIL ②**：让 IDL 的 `escape` 少加一次 `escape_num` ⇒ 该例必红（证明严格相等、未被 seed 掩盖）；还原回绿；
4. `--sample-check` 通过；`idl_exec_trace --self-test`、`idl_check_trace --self-test` 全绿；`make check-idl` 274/274；
5. `git status -uall` 仅允许文件 + 任务书。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
