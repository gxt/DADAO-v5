# m12-chipyard-009: 控制流 + RAS

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-008`（访存，已合入）+ `019`（异常进 hmon）；两者已合入
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

`m12-chipyard-008` 已完成访存；控制流与返回地址栈未实现。

## 目标

1. **控制流**：`SimRISC-06`（控制流）的条件分支、无条件跳转、`call`/`ret` 全形式；返回地址按 spec（`call` = 当前指令地址 + 4）。
2. **RAS**：返回地址栈的实现与深度按 spec；溢出/下溢行为按 spec（不得静默）。
3. **与 bootrom 的交互**：bootrom 的 `jump` 到应用入口路径必须保持（003 的闭环不回归）。

## 验收标准

1. `tests/inst` 中控制流指令族在 chipyard 上与 QEMU `dadao-tiny` 逐例一致
2. `call`/`ret` 的返回地址语义有专门断言（含嵌套调用）
3. RAS 溢出/下溢行为有至少 2 例（注入式）
4. bootrom→loadmem→semihosting 闭环不回归
5. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

位操作/原子/杂项（`008`）、FP（`009`–`013`）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-007/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。

## 完成区

**测试结果**：一键证据脚本 **PASS=95 FAIL=0**（A–K：结构/构建/273 回归/48 非故障控制流/19 故障/6 探针/周期/QEMU 向量 67/67/L1+L2）；注入自检 **2/2**「注入→FAIL→`cp`+md5 还原→回绿」（返回地址改 `ip+8` ⇒ D/G 红；`retRasUf` 置假 ⇒ E 红）。
**修改文件**（6 项，与 `git status -uall` 逐项一致）：① 本任务书；② `components/chipyard/README.md`；③ `components/chipyard/changelog.md`；④–⑥ `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/{WumingCore,WumingDecoder,WumingRegFile}.scala.patch`；⑦ `tools/chipyard/ctrl_sweep.py`（新增）。`series` 未变（无新增源文件），工作树无临时产物。
**验收结果**：
1. 控制流 67 例全部在核上执行：48 非故障例（30 br + 4 jump + 9 call + 5 ret）逐例与 YAML 期望 **byte-exact**（960 B，md5 `ab4ec3f…`），同一镜像在 QEMU `dadao-tiny` 上 **逐例一致**（同 md5）；`tests/inst` 控制流族经 QEMU harness 复核 **67/67**。
2. 返回地址 = `call` 当前地址 + 4：向量 7 例（C1/C2/C3a/C3b）逐例验 RA 值；三层嵌套探针（`L3→L2→L1→main` 各返回点打 tag、`ret rd1/rd2/rd3` 带值、末态 `RACNT=0`/`MRPTR=0`）byte-exact；64 层自然嵌套 + 63 次返回 byte-exact。
3. RAS 溢出 **3 例**（向量注入 1 + 64 层自然溢出 1 + C2 折叠边界 `count=0xFFFF` 1）；下溢 **6 例**（向量 2 = D4a/D4b-count0 + 三连冷栈 ret 3 + D1 1）。全部 `cause=1<<10 / 1<<11`、`cause_ip` 停在 `call`/`ret`、RA 与内存/`rd` 不变（精确）。
4. MemRAS：C3b 溢出把最旧条目写 `MRPTR-8`（内存逐字比对 + `MRPTR`/`RACNT`）、D4b 下溢的 consume/refill 两分支各 1 例；两者 QEMU 同镜像 byte-exact。
5. bootrom 闭环不回归：`CFXTRAP→hmon→escape→jump ENTRY→应用→SYS_EXIT` 各 1 次（trace 断言）。
6. 273 例 md5 `2d4d946…` 与 m12-005 基线一致；构建（主控机）elab/Verilator rc=0、`%Error`=0；`apply-series`/`check-source-state`/`check-patch-tree` rc=0（331 patches）、L2 rc=0；L1 红仅 `check-knowledge-refs`/`check-run-artifacts`/`check-temp-dirs`（offender 无本任务）。
7. 周期实测（trace 逐例）：不跳转分支 1；跳转/`jump`/`call`/`ret`（RegRAS）8（= 1 拍执行 + 一次需求取指 6 + 1）；MemRAS `call` 26、MemRAS `ret` 15。
8. 完成区 ≤30 行、无运行期路径。

**新发现/坑**：
- 本任务的故障镜像分两类：**可恢复**（`call`/`ret` 自身抛的 ILLI/RASOF/RASUF，hmon `escape +4` 回到下一条 ⇒ PRE+POST）与**终止**（`CFXMEM`/`UNDI` 落在目标取指上，`cause_ip` 就是坏目标，跳过也回不来 ⇒ 只能 `max-cycles` 截断，断言取 cause + 无 POST）。
- 对照 QEMU 时踩到两个自家 bug（都是**探针**的，不是 RTL）：`load_rd` 只 4 字却按「后面还会追加」推算返回地址 ⇒ `ret` 跳进自身 setup；以及 consume 分支漏算先前 refill 压入的栈顶。QEMU 同镜像比对是发现这类错误的关键。
- 取指预取在本任务全部 trace 中 **0 次发射**（48 例 trace 1996 次需求取指 / 0 次 prefetch），故每次跨 beat 的跳转都付 6 拍 SRAM 往返；属 `m12-chipyard-020` 范畴，提请后续任务复核（不阻断本任务语义）。
- `+max-cycles` 截断的用例 `$?` 是 255 且日志含 `(timeout)`；成功停机是 0——两者必须区分，不能只看 rc 非零就判失败。

## 审阅记录

### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = 3 个 RTL 源及其导出补丁、`tools/chipyard/ctrl_sweep.py`、证据脚本、README/changelog。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 解码器漏 `br.eq`/`br.ne`（0x6E/0x6F）：48 例里 6 例被当 ILLI 进 hmon | ✅已修 | 新增 0x6E/0x6F 解码 + 条件码 6/7（比较两个 rd） | 48 例 byte-exact；trace 意外 cause 归零 |
| F2 RAS 压/弹移位方向写反（`new(i)=old(i-1)` vs `old(i+1)`），C3a 后栈顶错位 | ✅已修 | 压= `raNext(i):=ra(i+1)`、弹= `raNext(i):=ra(i-1)` | 三层嵌套/64 层溢出/向量 C3a 全绿 |
| F3 `rasMemKind` 只在 RAS 路径置位、普通访存未清 ⇒ 后续 `ld/st` 走错完成分支 | ✅已修 | 普通访存锁存处加 `rasMemKind := 0.U`，完成分支全部按 kind 门控 | 273 例回绿；访存探针（spill/refill 后同程序继续 dumps）全绿 |
| F4 `ret rdHA, imms18` 的 rd 写回在 D4b 下先于 MemRAS 读判定 ⇒ 下溢时 rd 被写（非精确） | ✅已修 | `retDeferred` 门掉 EXEC 写回；改在 `sMwait` 读回且 entry 计非 0 时写（`rasRetW0`） | underflow 探针：4 次 RASUF 后 `rd1/2/3` 保持种子值 |
| F5 折叠边界未测（C2 要求 `count < 0xFFFF`） | ✅已修 | 新增 `overflow_ffff` 探针（`ra63={0xFFFF,ip+4}` ⇒ 必溢） | RASOF 证据 3 例（1 向量 + 2 探针） |
| F6 证据脚本把 `.stdout/.stderr` 写进运行期日志目录（非法名，L1 红） | ✅已修 | `qemu_run` 单文件重定向；清掉旧文件 | L1 自家 offender 归零（改后仅他人 targets） |
| F7 周期断言写「RegRAS=1」与实测不符 | ✅已修 | 改为「RegRAS `call`/`ret` == 跳转分支」+「MemRAS 更贵」，并单列实测值 | 8==8、15>8 |
| F8 运行中改脚本导致 bash 重读错位（`E2E_BAD: unbound variable`） | ✅已修 | 所有脚本编辑移到两轮运行之间；最终一轮不再改文件 | 末轮 PASS=95 FAIL=0 EXIT=0 |

**判决**：finding 全部已修；证据脚本 95/95 全绿 + 注入 2/2 先红后绿。

### 第 1 轮 reviewer 验收

**重跑记录**（reviewer 亲跑，worktree 根、相对路径）：
- `bash .work/evidence/m12-chipyard-009/run.sh` → `== summary: PASS=95 FAIL=0 ==`、`RERUN_EXIT=0`，逐条与完成区一致：273 例 md5 `2d4d9465…`；48 例 DUT/QEMU/期望三向 md5 `ab4ec3fe…`（960 B）；19 故障例（RASOF=1/RASUF=2/CFXMEM=12/ILLI=2/UNDI=2，resumable 5/terminal 14，`bad=` 空）；RASOF 3 / RASUF 6；周期「不跳 1、跳转·`call`·`ret`(RegRAS) 8、MemRAS `call` 26/`ret` 15」；`tests/inst` 67/67；L2 rc=0；L1 三红 offender 逐条核为 night/gem5/testcases 他任务，无本任务。
- `bash run.sh --self-test-inject` → `INJECT_EXIT=0`，2/2「注入→FAIL→`cp`+md5 还原→回绿」（retaddr 红 D/G、rasuf 红 E），源 md5 `31f5a9fe…` 还原一致。
- **reviewer 独立注入**：`WumingRegFile.scala` SPILL 分支 `mrptrNext := mrptr - 8.U`→`mrptr`（去 C3b `MRPTR-=8`）⇒ 重建 ⇒ `ONLY=B,H` ⇒ `[FAIL] spill == expected dump (byte-exact) expected=0 actual=1`、`PASS=14 FAIL=1`、`INJ2_EXIT=1`（refill 仍绿，符合 REFILL 不经 SPILL）；`cp` 还原 md5 `90d44908…`=审前 ⇒ `touch`+重建 ⇒ `[PASS] spill … actual=0`、`RESTORE2_EXIT=0`（首轮回绿失败系 `cp -p` 旧 mtime 致 make 跳过重编译，非还原失败）。
- **cause_ip 实测**：`call_4` → `cause=0x400 cause_ip=0xffffff010178 info=0xffffff01017c`，同拍 `exec ip=0xffffff010178 inst=0x74000002`（info=ip+4）；`ret_4`/`ret_5` → `cause=0x800` 停在 `inst=0x76000000`、`info=0`。
- **探针期望=实测逐字节**：nested `[b3,b2,b1,11,22,33,ra0=0]`、overflow `[ra0=0, rd5=0x40]`、underflow `[ra0,ra63,rd1..3 全不变]`、spill `[ra0={62,slot-8}, ra63 旧顶, 溢出字]`、refill、overflow_ffff `[63<<48, {0xFFFF,ip+4}]`。

**约束核验**：① `git show --stat HEAD` = 7 文件，与完成区①–⑦逐项一致（完成区「6 项」为笔误，应 7）；② 完成区 20 行 ≤30、全文无运行期/宿主路径；③ HEAD 仍 `b10da29a`、审前/审后 `git status --porcelain -uall` 均空（本记录为 reviewer 唯一写入）、7 文件 md5 审前=审后、无 `*.preinject`/`*.inj-bak` 残留；④ 门控 elab/Verilator/`apply-series`/`check-source-state`/`check-patch-tree`/L2 全 rc=0；⑤ QEMU 独立 oracle 三处互证（sweep 同镜像、67/67、probes 同期望）。

**发现（阻断级，供 architect 定夺；非 009 引入）**：**预取 0 次发射是真 bug、非用例太短**——reviewer 用 `xbeat`（400 条 `or.o` 直线流、无分支）实测 `prefetch=0 / demand_fetch=313 / exec=618`，跨 beat 全付 6 拍往返。根因（diff 级）：008 把 `specBacked(pfReqAddr)` 加进 `pfAddrLegal`，而 `pfReqAddr` 取自复位值 0 的 `pfReqBeat`，地址 0 不在 Tiny 三段窗口 ⇒ `pfWanted` 恒假 ⇒ **自 008 起预取全部失效**（020 的「4 槽 p50=1、在飞峰值 4」测于 008 合入之前故未暴露）。修复为 `pfAddrLegal` 改查待发的 `pfBeat`（一行）；`git diff d4349eef HEAD` 中 prefetch 相关行无变化，009 未触及该逻辑。完成区已如实披露该现象（归因「属 020 范畴」需修正为 008 回归）。

**覆盖缺口（不阻断）**：C3b/D4b 访存 `denied` 中间失败（RA/内存不变）无专门用例；`ra0[63:54]` 非零写入丢弃无专门用例。

**判决：Accepted** —— 009 验收标准 1–7 全部由 reviewer 重跑证实；预取回归不属 009 范围且非 009 引入，须 architect 立修复任务或回 008 定夺。

#### 收尾（architect，2026-11-11 09:29）

- reviewer **Accepted**：`call` 返回地址 = `ip+4`（`info` 实测吻合）、`ret` 的 rd 写回由 `retDeferred` 延迟到 `sMwait` 读回且非下溢；RASOF/RASUF 的 `cause_ip` 精确停在 `call`/`ret`。
- `ra0` = `{SBZ(10), RACNT(6), MRPTR(48)}`，写按 `[53:48]/[47:0]` 拆分、`[63:54]` 丢弃（spill 探针 ra0 = `0x003effffff0150f8` 佐证）。
- 先判定后修改：underflow/overflow 探针失败后 `ra0/ra63/rd1..3` 与内存逐字节不变。
- 一键脚本 95/95；reviewer 自选注入（去 C3b `MRPTR-=8`）⇒ FAIL ⇒ 还原回绿。
- **重大回归（`ISS-382`，转 `m12-chipyard-022`）**：`008` 把 `specBacked(pfReqAddr)` 加进 `pfAddrLegal`，而 `pfReqAddr` 取自复位值 0 的 `pfReqBeat` ⇒ 地址 0 不在三段窗口 ⇒ **`pfWanted` 恒假，预取全部失效**。reviewer 用 400 条直线 `or.o` 实测 `prefetch=0 / demand_fetch=313`，证明与「用例短/跳转打散」无关；`020` 的 p50=1 测于 008 之前，故未暴露。
- 文档级：完成区写「修改文件（6 项）」实为 7 项。
