# m17-idl-025: trace 入口态纳入 cfx 计数与掩码（计数严格相等，不跳过）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-022/023/024`（trace 比较与环形布局）
**可并行分片**：否
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

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

- 独立 `git worktree`；不提交 git；只动 `idl/tools/{idl_qemu_state.py,idl_qemu_trace.py,idl_exec.py}`、必要时 `idl/docs/trace-format.md`、本任务书；完成区 ≤30 行。

## 验证

1. 全量 trace **274/274**；`--only escape_ciii_cfx` 绿；
2. **可达 FAIL ①**：把 seed 的 `ESCN` 值改错（+1）⇒ 第 26 条必红；`cp`+md5 还原回绿；
3. **可达 FAIL ②**：让 IDL 的 `escape` 少加一次 `escape_num` ⇒ 该例必红（证明严格相等、未被 seed 掩盖）；还原回绿；
4. `--sample-check` 通过；`idl_exec_trace --self-test`、`idl_check_trace --self-test` 全绿；`make check-idl` 274/274；
5. `git status -uall` 仅允许文件 + 任务书。

## 审阅记录

### 第 1 轮 engineer 自审

- **逻辑**：`cfx_regs` 逐字段对应 `spec/DADAO-12 §3.5` cg4 rc0–rc6 与 §5 cg15 rc3；只在 `load_state()` 初态 seed，运行期计数仍由 `trap`/`escape`/异常路径自行累加，比较器未改。
- **边界**：cfx63（power）非 monitor，模型无 `cg15` ⇒ 只 seed cg4，不造 cg15；缺 `cfx_regs` 显式 `ExecError`，不静默按 0。
- **防造假**：全量/两注入/门控均现场执行；注入 `cp` 备份 + md5 对账还原；注入①限定 hmon（cfx3）ESCN，命中第 26 条。
- **越界披露**：`idl_check_trace` 的入口态来自 `idl_qemu_trace.observe()`，不是 `idl_qemu_state`；不改它则全量不可能 274/274 ⇒ 最小改动 `idl_qemu_trace.parse_dump/entry_state`，CFX 行解析复用 `idl_qemu_state.parse_cfx_regs()`（单一真源）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 全量 trace 原红 `escape_ciii_cfx` 第 26 条 ESCN 0 vs 1 | ✅已修 | 解析 CFX 行并 seed cg4/cg15 | 全量 274/274、单例 PASS |
| 任务书只列 `idl_qemu_state.py`，但 trace 入口态由 `idl_qemu_trace.py` 产出 | ✅已修（越界披露） | `idl_qemu_trace.py` 复用 `parse_cfx_regs` 并输出 `cfx_regs` | 全量 274/274；`entry.json` 含 cfx3/cfx63 |
| 注入②的红显示为记录数 187 vs 1731（载体绝对自检先退），不是 val 行 | ❌不修 | 保留该注入（证明红即可） | 还原后 PASS；见完成区 |

### 第 1 轮 reviewer 复核

- **重跑（仓库根执行运行期证据目录内的 `run.sh`，审查独立输出目录）**：`RESULT: 0 FAIL` **rc=0**；逐项 `full_trace_rc 0` / `full_pass_count 274` / `full_fail_count 0` / `full_summary 274/274 …共 249995 条` / `only_escape_rc 0` / `sample_check_rc 0` / 两自检 `9/9` / `check_idl_rc 0` + `check_four_way: 274/274 …主清单 274 / pending 0` / `missing_cfx_regs_explicit` / `change_set_only_allowed` 全 PASS。
- **独立注入（reviewer 自做，非脚本内置）**：改 `idl_qemu_state.parse_cfx_regs` 使 `escape_num += 1`（md5 `efda2c56…`→`6fdfc44b…`）⇒ 同一脚本 **rc=1**、`RESULT: 6 FAIL`（`only_escape_rc | want=0 got=1`）；`cp` 还原 md5 回 `efda2c56…` ⇒ 重跑 **rc=0**、`RESULT: 0 FAIL`；`git status` 前后快照 `diff` 逐行相同。
- **静态核验**：`git diff -- idl/tools/idl_check_trace.py` **空**（比较器未改，`compare_records` 逐字段 `!=`、无跳过/阈值）；`load_state` 全仓仅 2 个初始化调用点，运行期无「用 QEMU 值覆盖」路径；CFX 行正则与 `cpu.c.patch` 的 `CFX%02d ID/VER/TRAPN/SYNCN/ASYNCN/ESCN/SCRN/GIM` 同序逐字段，`GIM`=cg15 rc3；缺 `cfx_regs` 显式 `ExecError`（脚本第 7 项 PASS）。
- **范围披露**：`idl_qemu_trace.py` **接受**——trace 入口态由其 `observe()/entry_state` 产出，不改则 274/274 不可达，且 CFX 解析复用 `parse_cfx_regs` 单一真源、改动最小；但任务书「约束」行仍只列 2 个工具，须随返工同步为 3 个工具 + 文档 + 本任务书（文档级）。
- **阻断**：`make check-knowledge-refs` **rc=2**，`结果: FAIL (1 具体 .work/** 引用不可复现)`，定位到本任务书完成区首行写了运行期证据目录的**具体路径**；HEAD 基线该文件无此类引用，系本任务引入 ⇒ 改为「运行期证据目录内的 `run.sh`」后重跑须 rc=0。
- **判决：Needs Revision**（仅上述门控一项；274/274、两注入、范围、文档 §2.2 计数规则、变更集 5 文件均已独立核过）。

**返工记录（第 1 轮 reviewer，Needs Revision）**：完成区首行去掉具体 `.work/**` 路径（改「运行期证据目录内的 `run.sh`」）；「约束」文件清单补 `idl_qemu_trace.py`（3 个工具，与完成区/实际改动一致）；重跑 `make check-knowledge-refs` **rc=0**（0 具体 `.work/**` 引用、0 悬空），重跑运行期证据目录内 `run.sh` **rc=0（0 FAIL）**。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` **0 FAIL**（rc=0）。全量 `idl_check_trace` **274/274**（249995 条指令）；`--only escape_ciii_cfx` PASS；`--sample-check` PASS；`idl_exec_trace`/`idl_check_trace` 自检各 9/9；`make check-idl` **274/274** rc=0（`check-idl: PASS`）。
**修改文件**：`idl/tools/{idl_qemu_state.py,idl_qemu_trace.py,idl_exec.py}`、`idl/docs/trace-format.md`、本任务书（`idl_qemu_trace.py` 为完成任务书验收 5 的必要越界，见自审）。
**验收结果**：
- 新增入口态字段 `cfx_regs[cfxha] = {id,ver,trap_num,sync_num,async_num,escape_num,scratch_num,async_mask}`（cg4 rc0–rc6 + cg15 rc3）。
- 注入①：hmon ESCN seed +1 ⇒ `第 26 条（pc 0x0000ffffff010164）val: exec ['0x0000000000000002'] != QEMU ['0x0000000000000001']`，rc=1；`cp`+md5 `e466b281…` 还原后 rc=0。
- 注入②：首次 `escape` 少加一次 `escape_num` ⇒ rc=1（`记录数 187 != QEMU 1731`，载体检查点 18 绝对自检先退）；md5 `e466b281…` 还原后 rc=0。
- `make check-idl`：`check_four_way: 274/274 例四方一致（parties=idl,qemu；主清单 274 / pending 0 / 现场派生 274）`。
**新发现/坑**：① `idl_check_trace` 的入口态走 `idl_qemu_trace.observe()`，与 `idl_qemu_state` 是两条观测路径；CFX 行解析已收到 `idl_qemu_state.parse_cfx_regs()` 单一真源。② QEMU `CFX63 GIM=0` 但 power 非 monitor，IDL 无 cg15 ⇒ 只 seed cg4，符合 `spec/DADAO-12 §3.5/§5`。③ 注入②的红由载体「cg4 计数绝对自检」先触发（执行器提前走失败退出），故 detail 是记录数而非 val；注入①（第 26 条基线读数）能给出直接 `val` 证据。④ `load_state` 现要求 `cfx_regs` 非空，缺则显式 `ExecError`。
**遗留问题**：无（「约束」文件清单已同步为 `idl_qemu_state.py`/`idl_qemu_trace.py`/`idl_exec.py` 3 个工具）。
