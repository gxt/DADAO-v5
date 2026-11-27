# m17-idl-004: 逐指令 trace 与 QEMU 比对

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-003`（执行器核心）
**可并行分片**：否
**预估**：2–3 天
**档位**：中改
**状态**：已验证

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

## 完成区

**测试结果**：通过 21/21（运行期证据目录内 `run.sh`，rc=0）；逐指令差分 **28/28**（共 **24790** 条指令记录）；`exec_trace --self-test` 11/11；`idl_exec --self-test` 28/28；003 的 `check_exec_parity` 仍 28/28（无回归）。
**修改文件**：新增 `tools/idl/trace_common.py`、`tools/idl/exec_trace.py`、`tools/idl/qemu_trace.py`、`tools/idl/check_trace_parity.py`、`docs/idl-trace-format.md`、`docs/idl-trace-sample.jsonl`；修改 `idl/idl_exec.py`（trace 观察面；CFXMEM 子原因按规范）、`idl/README.md`、`docs/README.md`、本任务书状态。
**验收结果**：
- 验收 1：28/28 `[PASS]`；逐条比较 `pc/insn/id/mn/dst/val/exc` + 每条后 `mode`/`cfx` + 退出码 + `SYS_WRITEC` 字节流；四类等价逐例计数（dup/ffetch/ra_skip/rd8_skip）见差分输出。
- 验收 2：格式文档 + 脚本生成样例；`--sample-check` 实测一致 rc=0，改样例 1 字节 ⇒ rc=1（`cp`+md5 还原）。
- 验收 3：注入①少记一条 ⇒ `记录数 765 != QEMU 766`、rc=1；注入② `NONPTW_SUBCAUSE` 57→56 ⇒ 第 319/234 条 `exc.cause` 差异、rc=1；两路 `cp`+md5 还原后回绿。
- 验收 4（真实 rc）：`check-idl-parse`=0、`check-idl-sync`=0、`check-knowledge-refs`=0、`check-no-residue`=0，另 `check-manifests-guard`=0。
**新发现/坑**：
- 003 把 CFXMEM 子原因写成地址低 16 位；规范是 `[57] NONPTW`（`DADAO-12 §3.6(四)`）——逐指令比对才暴露（003 只比寄存器/退出码）。
- QEMU TB **重复记录是非确定性的**（同镜像不同次 dup=0/1）；折叠判据必须是「同 PC 且状态逐字段相同」。
- `-d cpu` 含 `CFX00..63` 的 `CG5`（PREVM/CID/CIP/CINFO/PEND）与 cg4 计数：`TRAPN/SYNCN` 增量是「本步发生异常」的可靠判据（CID 可能与上次同值）。
- 取指异常：QEMU 把它记在**跳转指令**的区间（下一条记录直接是 handler），执行器在下一步才取指失败 ⇒ 必须按记录区间归并，否则 jump/escape 错位。
- `SYS_CLOCK` 返回宿主时钟、`SYS_WRITEC` 后 QEMU 写 `rd8=0xdeadbeef` 且持续保留 ⇒ `rd8` 只能整段退出比对（非单步）。
- `call/ret` 的 QEMU RAS 物理布局与执行器不同（弹出时移动条目）；有效区外按 `SimRISC-00 §2.4` 未定义 ⇒ 只比有效区。
**遗留问题**：
1. `U04`–`U10` 宽度裁定仍未取；执行器仍是 54 id 手写语义，新增用例需补注册。
2. 逐指令差分依赖安装根 QEMU + `tests/inst` 镜像，未接 L1 门控（与 003 同口径）；一键证据在运行期证据目录。
3. 内存写回 `mem` 仅为 M20 预留，本任务不比对（`-d cpu` 无内存观测）。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 003 的 CFXMEM 子原因 = 地址低位，与 §3.6 不符 | ✅已修 | `take_exception` 改 `NONPTW_SUBCAUSE`（`1<<57`） | 28/28 记录全等；003 差分 28/28 |
| 取指异常记录归并时漏更新 mode/cfx | ✅已修 | fetch-fault 分支同步覆盖 `states[-1]` | jump/ret/escape 三例转绿 |
| `--sample-check` 先写目标再比较 ⇒ 恒真 | ✅已修 | 只读原文件、临时文件重生成后比较 | 改样例 seq ⇒ rc=1；还原 rc=0 |
| 导入 `idl_exec` 生成 `idl/__pycache__`（清单门控红） | ✅已修 | 设 `sys.dont_write_bytecode=True` | `check-manifests-guard` rc=0 |
| 证据脚本把「预期红」计成失败项 | ✅已修 | 新增 `probe_red`（期望 rc=1，不计 FAIL） | 证据 21/21 PASS |
| 注入①入口写成立即 pop ⇒ 连续丢记录（不是「少一条」） | ✅已修 | 改为 `del records[5]` 单条 | 红信息 `765 != 766` |
| `rd8` 在 semihosting 后持续污染后续记录 | ✅已修 | taint 规则：no-return/CLOCK 起退出比对，非 semihost 重写后恢复 | 28/28 全等（E3 计数逐例） |
| RA 有效区外条目参与比对（QEMU 物理布局不同） | ✅已修 | 只比有效区 + 「提升但未写」条目排除（E4） | ret/call 转绿；`ra_skip` 逐例计数 |

### 第 1 轮 reviewer 验收（2026-11-21，全部本人重跑，命令在仓库根）

**重跑记录**
1. `python3 tools/idl/check_trace_parity.py --images <运行期镜像目录> --bootrom <BootROM>` ⇒ **rc=0 / 28/28 / 共 24790 条记录**，`[FAIL]`=0；连跑 2 次两侧 trace 逐字节相同（`dup` 每例 0/1 抖动而结果稳定 ⇒ E1 折叠确有必要）。
2. `python3 tools/idl/check_exec_parity.py --cases idl/idl_exec_cases.toml …` ⇒ **rc=0 / 28/28**（003 判据未破）。
3. `bash 运行期证据目录内 run.sh` ⇒ **rc=0 / `EVIDENCE: PASS（21 项检查通过）`**；另单独重跑 `check-idl-parse`、`check-idl-sync`、`check-knowledge-refs`、`check-no-residue`、`check-manifests-guard` ⇒ **均 rc=0**；`exec_trace --self-test` 11/11、`idl_exec --self-test` 28/28。
4. 样例：`--sample-out` 重生成与入库样例**逐字节相同**；`--sample-check` rc=0；改 1 字节 ⇒ **rc=1**，`cp`+md5 还原后 md5 复原。
5. **独立注入 5 路**（自备 `cp` 备份 + md5，不复用 run.sh 的注入）：
   - A `qemu_trace.py` 少记一条 ⇒ rc=1 `记录数 766 != QEMU 765`；md5 `760878a7…` 还原 ⇒ 回绿 rc=0。
   - B `exec_trace.py` 篡改 `val` ⇒ rc=1 `第 51 条 … exec ['0x0000ffffff017129'] != QEMU ['0x0000ffffff017128']`；还原 ⇒ rc=0。
   - C `NONPTW` `1<<57`→`1<<56` ⇒ rc=1，`ld.o`/`escape` 红 `cause 0x0100000000000002 != 0x0200000000000002`（`trap` 仍绿，符合只作用于 CFXMEM）；md5 `50faba90…` 还原 ⇒ rc=0。
   - D 每步 `cfx` 置 0 ⇒ rc=1 `第 1 条指令后 cfx: exec 0 != QEMU 63`（**`mode`/`cfx` 逐条比对可达 FAIL**）；还原 ⇒ rc=0。
   - E 翻转 `ra63` ⇒ rc=1，`call_iiii_ra`/`ret_riii_ra` 双红；还原 ⇒ rc=0（**E4 未掩盖 RA 写回**）。
   - 注入前后 `git status --porcelain -uall` 快照逐行相同、9 个目标文件 md5 全等。

**约束核验**
- **语义修正按 spec**：`spec/DADAO-12 §3.6(四)` wyde3 `[63:48]`、位号 `[57] NONPTW`、触发条件含 `ptw_enable = 0`；`idl_exec.py` 无 PTW 实现，5 处 `Fault("CfxMem", info=addr)` 均非页表来源，`info` = 被访问核内地址（§3.6(六)）⇒ `1<<57` 取自 spec 原文位号，**非按 QEMU 反推**（QEMU 产出 `(1<<1)|(1<<57)` 仅属印证）；003 的 `(info&0xFFFF)<<48` 与「低字节 `[55:48]` 为 one-hot 缺失原因」冲突，确属改正。
- **格式文档**：字段/顺序/滚动命名与实现逐条对上；E1–E4 各有计数口径与出处——E1 仅在 pc/mode/cfx/四寄存器组/cfx5/cfx4 全同才折叠（只会假红不假绿）、E2 归并点两侧一致且 `mode`/`cfx` 仍逐条比、E3 窗口有界且与 003 `rd8_defined` 同口径、E4 已实测可达 FAIL。
- **尺寸**：最大单文件 278271 B、>1 MiB 个数 0；8 KiB 上限下滚动 21 片。
- **范围**：未改 QEMU/gem5/RTL/spec；变更 = 任务书 + `docs/README.md` + `idl/README.md` + `idl/idl_exec.py` + 6 个新增，与完成区「修改文件」逐条对齐；无 `__pycache__` 入清单。

**非阻断 finding**：① `probe_red` 只断言 rc=1、不断言输出含 `[FAIL]`（本次输出确含真实 FAIL，且已独立复现）；② `id`/`mn` 两侧同源于 `contracts/opcodes.yaml`（文档 §2 已如实声明），该两字段非独立证据；③ `dst`/`val` 派生函数两侧共用（输入分别来自 QEMU dump 与执行器状态，非同源自比，`exec_trace --self-test` 11/11 兜底）；④ `rd8_skip` 15283/24790、`ra_skip` 39173 量级偏大，M20 复用时建议在格式文档补覆盖率。

**判决：Accepted** —— 验收 1–4 在本人重跑下全部通过、硬约束无违反；4 条 finding 均非阻断，交 architect 收尾处置。

