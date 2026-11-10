# m12-chipyard-019: `cfx_power` / `cfx3` 寄存器组 + 同步异常进 hmon

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-007`（BootROM 固件 + power 搬运 + 最小 hmon 已通）、`m12-chipyard-018`（双端口/骨架）
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 用户裁定（2026-11-10）

- Tiny **恒 `hypv`**：异常进入强制 `hypv`；**`switch_run_mode` 写入被忽略、保存值保持 3、读回保存值**
- **`cg3` 仅 `hypv` 可访问**：其它模式访问 ⇒ `CFXREG`
- **`cg3 rc10`（`excp_vector`）**：初值 = 该 cfx 内部 SRAM 起始；写入**忽略低 2 位**（按 4 字节对齐落盘），不报错
- **同步异常直接进 hmon 向量**（不经 `trap` 指令）；`trap` 的 semihosting 判定只看 `immu18 ∈ 0x3FF00–0x3FFFF`
- **IALIGN：IP 停留非法地址**，`excp_cause_ip` = 该地址，触发指令的正常写回照常完成
- **R15 = B**（无嵌套上限）、**R16 = B**（无硬件 `halted` 兜底）
- **`escape`**：目标 cfx 恒为当前 cfx；偏移只 0 / +4

## 目标

1. **cfx 寄存器组**：`cfx_power`（cfx63）与 `cfx3 hmon` 的 cg0–cg8 必要寄存器（`excp_cause_id/ip/info`、`excp_vector`、四类同步 mask、`cfx_intr_mask`、`switch_run_mode`、`cg7` 空间块、`cg8 rc1` ⇒ `CFXREG`）。
2. **异常进入**：五类同步异常（`CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN`）写 `excp_cause_*` 并跳向量；`escape` 返回（0/+4）。
3. **`cg3` 权限**：非 `hypv` 访问 ⇒ `CFXREG`。
4. **`rc10` 语义**：初值 = hmon SRAM 起始；写入忽略低 2 位。
5. **Tiny 恒 `hypv`**：`switch_run_mode` 读回 3。

## 非范围

- BootROM 固件/power 搬运/hmon handler 主体（`007`）
- 双端口/取指缓冲（`018`）
- 访存指令语义（`008`）、FP（`011`–`015`）
- QEMU/gem5 侧对齐（M13 任务）

## 验收标准

1. 五类同步异常**各 ≥3 例**进 hmon 向量，`excp_cause_id`（one-hot）/`ip`/`info` 正确
2. **IALIGN 专门断言**：`ip` 停在非法地址、`cause_ip` = 非法地址、触发指令写回完成
3. `cg3` 在非 `hypv` 模式访问 ⇒ `CFXREG`（用例 + 反例）
4. `rc10` 写入未对齐值 ⇒ 落盘为对齐值（低 2 位清零），读回一致
5. `switch_run_mode` 写 0 后读回 3、运行模式仍 `hypv`
6. `escape` 的 0 与 +4 两路各有用例
7. 273 例零回归 + Tiny 44/44
8. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
9. 一键证据脚本（含可达 FAIL 注入）
10. 完成区 ≤30 行、无运行期路径

## 说明

- 构建/调试在主控机；不占用 207/208。
- 组件单写者；补丁走 `make_patch` 导出。
- 与 `Machine-v5 §4.4` 的 `excp_cause` 表逐条对齐；发现冲突停下登记。

## 硬约束（子代理必读）

1. 临时目录 `/tmp/opencode/<任务ID>/`，禁仓库内临时文件。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-11）

**审查范围**：`WumingCore`（cfx 寄存器组读写面、五类异常入口、`escape` 恢复、safe 合法性）、`hmon.S` 分派、`app.S`/`check_log.py` 判据；逐条核对「精确异常不写回」「cg3 仅 hypv」「rc10 掩低 2 位」「IALIGN IP 停留」与 `spec/Machine-v5 §4.4`。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `cfx2rd` 到未实现寄存器（cfx3/cfx63 的 cg8、cg4…）时 `execW0` 仍为真 ⇒ 目的寄存器被写入 `cfxRdata`（非精确异常） | ✅已修 | 新增 `cfxFault = d.isCfx2 && !cfxRegOk`，门掉 `execW0`/`w1En` | app 侧 sentinel（`rd20/rd22=0xbeef`）在两次被拒读后不变；日志 oracle 226 条全绿 |
| F2 `TLEdge.Get/Put` 的 `legal` 为 **fast** 解码，未映射地址被判"合法"而上总线，被 TL monitor 打断（`A channel carries Get ... can't support`） | ✅已修 | CFXMEM 判定改用 `manager.supportsGetSafe`/`supportsPutFullSafe`；预取加同款合法性门；A 通道 `valid` 只在合法时置起 | 非法地址 3 例稳定 `CFXMEM`（`cause_info`=访问地址），无 monitor 断言 |
| F3 故障指令（`escape cfx7`、`cfx2rd cfx7`）在**未执行**时也打印 `escape`/`cfx2` 诊断，日志 oracle 事件序错位 | ✅已修 | 两条 printf 加 `!execFault`；`cfx2` 增 `wdata=`（写值与读值分开） | oracle 的 escape 计数=19 条（18 入口 + 伪造帧）逐条对齐 |
| F4 IALIGN 的 `escape 0` 与 `+4` 语义未端到端验证（只在 RTL 推理） | ✅已修 | hmon 分派：IALIGN 用 `cfx2rc cg5 rc3` 改写 `cause_ip` 后 `escape 0`；`app.S` 用 `.org`+linker ASSERT 固定落点 | 3 例 `cause_ip` 均为非法地址；`escape` 的 cause_ip=target=`(ip&~3)+4`；对齐字+4 处恢复执行 |
| F5 `cfx2` 读值 mux 对非法访问回落到 cg7 数据（诊断打印垃圾） | ⏸延后 | — | 仅诊断打印受影响（`ok=0` 已表达拒绝），不影响架构状态；改动需再扩 mux，留 M13 与 cg4/cg6 一起做 |
| F6 `switch_run_mode` 写被忽略但需可观测 | ✅已修 | 写入接受（`ok=1`）不落盘；读回常量 3 | `cfx2 rc8 write=1 wdata=0` 后读回 3；故障后 `excp_prev_run_mode=3` |
| F7 cg3 非 hypv 用例需可达路径（Tiny 恒 hypv） | ✅已修 | 用例用 RW 的 `cg5 rc3/rc0` 伪造帧后 `escape +4` 进入 supv；hmon 返回前复位 prev mode | supv 下 `cfx2rd cg3 rc10` `ok=0 mode=2`；hypv 下同一访问 `ok=1 mode=3` |
| F8 证据脚本的三组注入都是程序侧（不重建），未覆盖 RTL 语义 | ⏸延后 | — | RTL 侧注入须重建 elab+Verilator（约 5 min/次），交 reviewer 独立注入承担 |

**判决**：F1–F4、F6、F7 已修并复验；F5、F8 记录理由延后；状态 → `待验收`。

### 第 1 轮 reviewer 验收（2026-11-11）

**重跑（本人命令 + 真实输出/退出码）**
- 一键证据脚本 `run.sh` ⇒ `== summary: PASS=59 FAIL=0 ==`、`RUN_EXIT=0`；另前台补跑 `make check-modules` ⇒ `module checks (L2): PASS`、`rc=0`。
- 分段实测：镜像 65536 B / hmon 段 120 B / `--check-hex` rc=0；elab rc=0 且 `%Error`=0；Verilator rc=0 且 `%Error`=0；`check_log: PASS=226 FAIL=0`；`apply-series` rc=0；`check-patch-tree` `9 patch set(s), 331 patches OK`（chipyard 0 问题）；组件树 base+1 clean；L1 `rc=2 failed: check-knowledge-refs,check-temp-dirs`。
- 门控归属：该两项 L1 红**均非本任务**——`check-knowledge-refs` 的 2 条具体引用在 `m13-testcases-008/009` 任务书（master 复跑 `FAIL (4 …)` 更红、本任务 0 条）；`check-temp-dirs` 5 项全为他任务陈旧目录；273 例 `md5=2d4d94651346ef673c5a855e024c1489`（1240 B，我方 `md5sum` 亲算）== m12-005 基线；Tiny `44/44`。
- 注入自检 `--self-test-inject` ⇒ `3/3 injection -> FAIL as expected`、`restore md5 matched`、`restore -> PASS`、`rc=0`。
- 独立注入①（越界用例地址改为 hmon SRAM **末合法字**）⇒ `PASS=51 FAIL=1`、`rc=1`；日志 18 条 excp、**无**该指令异常、无 FAULT/monitor 断言 ⇒ 合法边界未被误判；`cp`+md5 还原 `bb4a4f31…` ⇒ `PASS=52 FAIL=0`。
- 独立注入②（RTL：`cfxVector` 写入去掉低 2 位掩码）⇒ `case run rc expected=0 actual=66`（0x40+2 = rc10 自检）+ oracle rc=1、`rc=1`；`cp`+md5 还原 `f02af739…`、组件树 `status` 空。**有据重试 1 次**：`cp -p` 保留旧 mtime 致 elaboration 被跳过（复跑仍 66、`rc=1`）；`touch` 后复跑 ⇒ `PASS=59 FAIL=0`、`rc=0`。

**五类异常 + IALIGN 逐条对 spec（我方独立抽日志 / 自建 ELF 反汇编）**
- 19 条 excp（1 移交 + 18 同步）、20 条 escape、`fault` 0 条：`CFXTRAP 0x1`、`CFXREG 0x4`×3、`MALIGN 0x1000`×3、`ILLI 0x100`×3、`UNDI 0x200`×3、`CFXMEM 0x2`×3、`IALIGN 0x2000`×3，`vector` 恒 `0x0fff00000000` ⇒ 与 `Machine-v5 §4.4` 表 + `§7.1` 位索引逐条一致。
- `info` 逐类核：MALIGN/CFXMEM=访存地址（`0xffffff000001/…04/…02`、`0x1000000000`、`0xffffff800000`、`0x0fff00010000`）；ILLI/UNDI/CFXREG=指令编码（`7f1c0000/7a1c0012/7e1c0001`、`08040001/1b040001/58040001`、`7a0c8054/7afc8056/7a0c329a`）；IALIGN=IP ⇒ 全中 spec。
- `cause_ip` 对址：`jump` 落 `0xffffff014110`、`rd20=0xff1` ⇒ `0xffffff015101`（site1 `0x4210+0xff2=0x5202`、site2 `0x4310+0xff3=0x5303`），与日志逐条同址。
- IALIGN：`cause_ip = info = 非法地址`（IP 停留、不写回下一条）；hmon `cfx2rc cg5 rc3`（`DADAO-12 §3.6` rc3=RW ⇒ 合法）写 `0x5101→0x5104` 等 3 组，随后 `escape 0`、`target=(ip&~3)+4`；触发指令 `jump` 无寄存器写回，用例断言前置写回保持 + 对齐字+4 恢复——**写回断言对 `jump` 空真**（子集内唯一改 IP 指令本就无写回），记观察项、不阻断。
- `escape`：四类 + 移交共 17 条 `target=cause_ip+4`（`cause_ip` 不变），IALIGN 3 条 `escape 0`（`cause_ip` 已改写、`target` 同值），伪造帧 `escape` `target=LAND`、前置 `mode=3` ⇒ 0/+4 两路均正确。

**寄存器语义（实测）**
- `rc10` 初值 `0x0fff00000000`、写 `base|3`（`ok=1`）读回 `base`（掩低 2 位）；`rc8` 读 3、写 0 `ok=1` 不落盘、再读 3；`cg3 rc0=0x7ffffffffffffff7`、`rc4=全1`；`cg7` hmon `3/0x3ff00000000/0x10000/7`、power `5/0x3ffffff0000/0x10000/5`（`start=base-(cfxha<<42)` ≡ `§3.8` 42 位偏移）、块1=0；两 cfx `cg8 rc1` `ok=0` 且进向量 cause `0x4`。
- cg3 仅 hypv：伪造帧 `escape` 后 `mode=2`、`cfx2rd cg3 rc10 ok=0`；进 hmon 复位 `prev=3` 后同一访问 `ok=1 mode=3`。

**两个自审修复（读 RTL 复核 + 边界用例）**
- `cfxFault = d.isCfx2 && !cfxRegOk` 门 `execW0/w1En`（`cfxWriteEn` 亦要求 `cfxRegOk`），分支序 `execFault(ILLI/UNDI) → cfxFault(CFXREG) → trap` 与「编号层 ILLI 先于寄存器层 CFXREG」一致；sentinel `rd20/rd22=0xbeef` 不变 ⇒ 被拒读不再改目的寄存器。
- `supportsGetSafe/supportsPutFullSafe` 用于取指/预取/ld/st、`sMreq` 断言同源，未映射地址在 `sFreq`/`sExec` 即 CFXMEM（不再上总线被 monitor 打断）；末合法字不触发（注入①）、越界一字触发、273+44 零回归 ⇒ **无过判、无漏判**。

**越界披露核验**
- `expected.yaml::shared_bootrom_md5`→`33bfe14af0e47d9e6f9c2d4a34fc5ae0` == 我方 `md5sum` 实测 64 KiB 镜像（hmon 段 120 B）；全仓 `git grep` 仅该 yaml 自身出现该键 ⇒ 无门控读取、无破坏。`tiny_smoke.S` 终止 UNDI → `SYS_EXIT(0)` 必要（019 后同步异常走 `escape +4` 不再停机），结果写在终止之前、L1/L2 绿。组件树 `base+1`（`974cfa4`）clean、`check-patch-tree` 0 问题 ⇒ 补丁可复现。

**跨任务发现（非 019 交付物，提请 architect 处置）**
- `m13-gem5-005` 完成区声明新增的 `tests/arch/hmon/{tiny_hmon_handler.S,tiny_hmon_handler.lds,tiny_hmon_layout.inc}` 与 `tools/gem5/check_tiny_hmon.py` 改动**从未进入任何 commit**（`git log --all` 无、磁盘无、合入 `611f9920` stat 不含）⇒ 现 `tiny_hmon.S` 缺 include 不可汇编、`check_tiny_hmon.py` 实测 `exit=2`；其证据脚本另硬编码旧镜像 md5 `777b6bc9…`（重跑必红）。
- `m13-qemu-002` 证据两侧均为**动态**比对（脚本无硬编码 md5、无 `56` 常数）⇒ 与新镜像同步、不受影响。两者均不在 `make`/工具门控内。

**纪律**：HEAD 仍 `9aaa83a3`（未 commit/push、未改台账）；`git status` 仅 3 个新增 `tools/chipyard/excp/{app.S,app.lds,check_log.py}`（与完成区一致）；10 个交付文件 md5 审前=审后；组件树 `status` 空、无 `*.preinject/*.inj-bak/*.orig/*.rej` 残留；完成区 25 行 ≤30、无宿主绝对路径/临时目录。观察项：worktree 根有 11 个 `*.log` 构建日志（gitignore、随 worktree 删除），建议收尾清理。

**判决：Accepted**（engineer 达标；跨条发现单独提请 architect，不改本判决）。

## 完成区

**测试结果**：一键证据脚本 `PASS=59 FAIL=0`（A–H；L1 两项外部红见遗留）；注入自检 3/3「注入→FAIL→`cp`+md5 还原→回绿」（`memaddr`/`ialign_off`/`dropcase`）；日志 oracle 226 条断言全绿；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 不变；Tiny 44/44；elab/Verilator rc=0 且 `%Error`=0；L2 `module checks (L2): PASS`。
**修改文件**：
- 新增 `tools/chipyard/excp/{app.S,app.lds,check_log.py}`（RTL 用例 + 独立日志 oracle）
- 改 `tests/shared/bootrom/tiny/hmon.S`（分派：现场三读 → CFXTRAP magic 校验 / IALIGN 改写 `cause_ip` 后 `escape 0` / 其余 `escape +4`；返回前 `excp_prev_run_mode=3`；段 56→120 B）
- 改 `tests/shared/bootrom/tiny_smoke.S`（终止 UNDI → `SYS_EXIT(0)`：019 后同步异常进 hmon，UNDI 不再停机）
- 改 `tests/arch/hmon/expected.yaml`（共享 BootROM 镜像 md5 随 hmon 段更新；无工具读取）、`components/chipyard/changelog.md`；chipyard 补丁 2 份（`WumingCore.scala`、`bootrom.tiny.hex`）
**验收结果**：
- 寄存器组实测：hmon `cg3 rc0=0x7fff_ffff_ffff_fff7`、`rc4=0xffff…ffff`、`rc8=3`（写 0 忽略）、`rc10=0x0fff_0000_0000`（写 `base|3` 落盘 `base`）；`cg5 rc0=3` + cause 帧；`cg7` 块0 `desc=3 start=0x3ff_0000_0000 size=0x1_0000 attr=7`、块1=0；power `cg7 5/0x3ff_ffff_0000/0x1_0000/5`、`cg3 rc10=0xffff_ffff_0000`、`rc0=0xffff…fff7`；两 cfx 的 `cg8 rc1` ⇒ `ok=0`（CFXREG）
- 五类各 3 例（18 次进 hmon）+ 移交 1 次：`cause_id` = 0x2 / 0x100 / 0x200 / 0x1000 / 0x2000（另 CFXREG 0x4）；`cause_ip` = ELF 符号地址；`info` = 访存地址（CFXMEM/MALIGN）/ 指令字（ILLI/UNDI/CFXREG）/ IP（IALIGN）
- IALIGN：`cause_ip` = `0xffffff015101` / `0x…5202` / `0x…5303`（非法且未对齐）；hmon 改写 `excp_cause_ip` 后 `escape 0`，`target=(ip&~3)+4` 并在该处恢复执行；其余四类与 CFXTRAP 走 `escape +4`
- cg3 权限：伪造帧 `escape` 后 run mode=2 ⇒ `cfx2rd cg3 rc10` `ok=0`；hmon 复位 prev mode=3 ⇒ 同一访问 `ok=1`（mode=3）；被拒的 `cfx2rd` 不改目的寄存器
- IALIGN 的写回：本子集唯一改 IP 的指令（`jump`）无寄存器写回，已断言其目标寄存器与前置写回保持、`excp_cause_ip` = 非法地址（不写回下一条 IP）
- 门控：`apply-series` rc=0、`check-patch-tree` 331 patches OK（chipyard 0 问题）、`check-source-state` chipyard base+1 clean
**新发现/坑**：
1. `TLEdge.Get/Put` 的 `legal` 是 **fast** 版（只解码已支持区间、假定地址合法）⇒ 未映射地址会"合法"发上总线并被 TL monitor 拒；CFXMEM 判定须用 `manager.supportsGetSafe`/`supportsPutFullSafe`。
2. `cfx2rd` 打到未实现寄存器时 `execW0` 原为真 ⇒ 目的寄存器被写入 `cfxRdata`（非精确异常）；现用 `cfxFault` 门掉写回，app 侧 sentinel 钉死。
3. hmon 段烘进 elaboration：改 `hmon.S` 必须让 BootROM 资源生成器重跑（资源变化 `make verilog` 不追踪，须清掉资源产物与 jar）。
4. 任务 worktree 的构建目录须指向共享构建树，否则 L2 会在本地重建 LLVM 并占满临时文件系统。
5. 故障指令的 `escape`/`cfx2` 诊断不加 `!execFault` 会在未执行时打印，污染日志 oracle。
**遗留问题**：
- L1 两项外部红（master 上同样红）：`check-knowledge-refs`（`m13-testcases-008/009` 任务书的 `.work/**` 引用）、`check-temp-dirs`（5 个他任务陈旧临时目录）。
- 本 profile 不实现 ⇒ `CFXREG`（较 QEMU/gem5 完整实现为窄）：`cg4`、`cg6` scratch、`cg3 rc12`、`cg5 rc5`、`cfx_hmon cg8 rc1`（Tiny 无异步源）。
- 四类同步 mask 在 Tiny 不可观测（同步异常不可屏蔽 + 唯一 trap 源是当前 cfx，自位被忽略），只验证 RW 与初值。
- `trap cfx_power` 仍按 007 判 ILLI（`spec §4.1` 为 CFXTRAP 进 cfx63），非本任务验收面。

#### 收尾（architect，2026-11-11 04:18）

- reviewer **Accepted**：五类异常逐类 3 例 + `CFXREG` 3 例，`cause_id`/`ip`/`info` 与 `Machine-v5 §4.4` 逐条一致（reviewer 自建 ELF + `llvm-objdump` 对址）；`escape` 四类 +4、IALIGN 改 `cause_ip` 后走 0。
- 两个自审修复经独立注入复核：`cfxFault` 门（未实现寄存器不写回）与 `supportsGetSafe/SupportsPutFullSafe`（未映射地址不上总线）——边界用例「hmon SRAM 末合法字」不误判。
- 273 例 md5 `2d4d9465…`（reviewer 亲算）、Tiny 44/44、elab/Verilator rc=0、`check-patch-tree` 331 patches（chipyard 0）、L2 PASS。
- 跨任务影响（reviewer 实测）：hmon 段 56→120 B ⇒ 镜像 md5 `33bfe14a…`；`qemu-002` 的证据脚本动态比对**不受影响**；`gem5-005` 的证据脚本硬编码旧值 + 其 4 个文件从未入库 ⇒ 转 `m13-gem5-006` 处理。
- 非阻断：worktree 根 11 个 `*.log` 随 worktree 删除；`cg3 rc12`/`cg5 rc5`/`cg8 rc1` 等未实现项已在遗留区披露。
