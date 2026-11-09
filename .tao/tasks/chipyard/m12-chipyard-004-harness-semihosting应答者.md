# m12-chipyard-004: harness 侧 semihosting 应答者（最小 5 服务）

**模块**：chipyard
**项目里程碑**：M12
**可并行分片**：否（单次 Verilator 构建 + 单次运行，不可拆）
**状态**：已验证
**依赖**：`m12-chipyard-003`（BootROM + loadmem 闭环）

## 背景与已定方案

- semihosting 是 FS/SE 共用、profile 无关的机制：guest 执行 `trap <any cfxha>, 0x3FF00+op`（判定只看 `immu18[17:8]`），由宿主完成 I/O 并把结果写回 `rd8`（`spec/Machine-v5 §5`）。
- **用户裁定**：应答者放 **harness 侧 C++**，与 QEMU `semihosting/arm-compat-semi.c`、gem5 `src/arch/dadao/semihosting.cc` 同层；**核内不实现宿主 I/O**。
- **M12 不考虑 fesvr/pk**；Tiny 阶段不涉及 syscall。

## 目标

1. **核内「抬到边界」**：命中 semihosting tag 时，把 `(op, 参数寄存器值/指针, 返回寄存器号)` 通过一个可观测通道（DPI 导出端口或预留 MMIO，二选一并写明理由）交给 harness；**核不做任何宿主调用**。
2. **harness 侧应答者**（C++，table-driven）：
   - 最小服务：`SYS_WRITEC(0x03)` / `SYS_WRITE0(0x04)` / `SYS_WRITE(0x05)` / `SYS_EXIT(0x18)` / `SYS_CLOCK(0x10)`
   - 语义严格按 `spec/Machine-v5 §5.3` 表；返回 `rd8`；`SYS_EXIT` 触发有界停机（不依赖 TestDriver 超时）
   - 未实现的服务号 ⇒ 明确报错（不静默当 0）
3. **三平台一致**：同一 ELF 在 QEMU `dadao-tiny`、gem5 FS Tiny、chipyard 的 stdout 与退出码一致（判据 = 与 qemu/gem5 一致，不用独立 oracle）。
4. 文档：`components/chipyard/README.md` 记录通道形态、服务集、未实现语义。

## 验收标准

1. `SYS_WRITE0` 输出在 harness stdout 逐字节正确（含中文/长字符串不截断）
2. `SYS_EXIT` 退出码映射到宿主退出码（按 `spec §7.1` 的 guest 段 `0x00–0x3F` = PASS）
3. `SYS_CLOCK` 返回单调递增、单位与 `spec` 一致
4. 未实现服务号（如 `SYS_OPEN`）⇒ 明确报错并给出服务号，不静默
5. 同一 ELF 三平台 stdout + 退出码一致
6. Verilator 构建 rc=0（`server207`）；`make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- 完整 25 服务（后续任务按需补）
- fesvr/pk、TSI（不在 M12）
- 核内部指令实现（`005` 起）

## 说明

- 通道形态（DPI 端口 vs MMIO）会影响后续核实现，**必须在任务书完成区给出选择理由**；若发现与 `003` 的启动路径冲突，停下报告。
- 构建/运行在 `server207`；仓库修改在主控机。

## 完成区

**测试结果**：一键证据脚本 `PASS=70 FAIL=0`（rc=0）；`--self-test-inject` **5/5 注入均令脚本 FAIL**，`cp`+md5 还原一致，还原后完整重跑 `PASS=70 FAIL=0`。

**修改文件**（13 项，与 `git status -uall` 逐项一致；另本任务书）：① `components/chipyard/README.md`；② `components/chipyard/changelog.md`；③ `components/chipyard/series`；④–⑥ 新增补丁 `WumingSemi.{scala,v,cc}`；⑦–⑨ 改 003 补丁 `WumingCoreStub.scala`/`WumingTile.scala`/`DadaoConfigs.scala`；⑩ `Makefile`（4 个 `--defsym` 变体）；⑪–⑬ 新增 `tests/shared/bootrom/semihost_smoke.{S,lds}` + `semihost_msg.inc`。任务 worktree 内无未跟踪临时产物（`git status -uall` 与本清单逐项一致）。

**验收结果**：
① `SYS_WRITE0`：QEMU/gem5/chipyard 的 guest stdout 均 **1136 B**，与源文本 oracle 逐字节相同；消息 1135 B（>1 KiB，含中文 UTF-8），harness 诊断 `1135 byte(s) written`，无截断/重编码；core 日志 `semihost 0x04 -> rd 8=0xdeadbeef` 证明返回值已写回 rd8。
② `SYS_EXIT`：code 0 → 三平台 rc=0；code 0x40 → 三平台 rc=64（guest FAIL 段）；映射 `reason=0x20026 ⇒ 子码作宿主退出码`。
③ `SYS_CLOCK`：chipyard 两次 `1114/1114` 百分秒（raw 11146150/11148121，CPS=1e6，`N=raw/(CPS/100)`），单调不减；宿主模型单元测试 0→4 百分秒严格递增。
④ 未实现 `SYS_OPEN`：chipyard rc=1，stderr 含 `semihosting op 0x01 is not implemented`（给出服务号 0x01）。
⑤ 三平台：同一 `semihost_smoke.elf` 的 stdout 三平台逐字节相同、退出码同为 0；`semihost_fail.elf` 三平台同为 64。
⑥ 构建/门控：`make verilog` 与 Verilator 构建 EXIT=0（`%Error`=0、`WumingSemi.o` 已链接）；`apply-series`/`check-source-state`/`check-patch-tree` rc=0；L1 rc=2 的红因逐项核实为他人（`check-milestones-fresh`=INTEG-059t 台账、`check-run-artifacts`=他人 integ 文件、`check-temp-dirs`=他人陈旧目录）；L2 在 master 检出 rc=0。
⑦ 证据脚本含可达 FAIL 注入；⑧ 本区 ≤30 行、无运行期路径；⑨ 节点同步 `sync-node-repo` rc=0（`head=34e10fb1 dirty=0`）。

**通道选择（任务要求写明理由）**：**DPI 导出端口**，不用 MMIO。请求/应答天然同步（无需轮询、无需新增地址图区间）；应答者要读 guest 内存（字符串/参数块），DPI 桥可像 `+loadmem` 加载器一样自带 TileLink 主端口；MMIO 方案仍需要这条总线，且多一层寄存器协议。核内只发 `(op=immu18[7:0], arg=rb16, ret=rd8, pc=IP)`，无任何宿主调用。

**新发现/坑**：
- **gem5 `BaseSemihosting::callWrite` 越界**：判断写作 `handle > files.size()`（应为 `>=`）；未 `SYS_OPEN` 时 handle=1 读 `files[1]` 越界 → segfault。QEMU arm-compat 模式 guest fd 0/1/2 未预置，`SYS_WRITE` 需先 `SYS_OPEN(":tt",4)`。故 `SYS_WRITE` 单独成像（harness 句柄 1/2 约定），不进入三平台比对集。
- **DPI + TL 双通道要两拍**：`mem_valid` 在 A 通道接收后立即撤销并锁存地址，否则 TL source 复用 / 地址漂移。
- **`SYS_CLOCK` 用宿主 `clock()`**：模拟器启动已耗 ~11 s CPU，相邻两次调用常相等；单调性以「非递减 + 单元测试严格递增」证明。
- **未实现服务号必须非零退出**：`semihost_unimpl.elf` 在写足前序输出后 rc=1，不静默当 0。

**遗留问题**：
- ⏸ 临时执行器仍只有 5 类指令 + semihosting `trap`；真核 `005` 替换。
- ⏸ 完整 25 服务 / `SYS_OPEN` / fesvr/pk 不在本任务（后续按需）。

## 审阅记录

#### 第 1 轮 engineer 自审

方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = 新增/改动 6 份补丁终态（Scala/Verilog/C++）、4 个 ELF 变体与链接脚本、Makefile、README/changelog、一键证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `readRb(16)` 传 Int ⇒ Scala 编译失败 | ✅已修 | 改 `readRb(16.U)`（两处） | 节点 `make verilog` 由 Error 转 EXIT=0 |
| F2 C++ 单元测试链接缺 `vpi_get_vlog_info`（harness 由 Verilator 提供） | ✅已修 | 测试驱动内提供返回 0 的 VPI 桩 | 单元测试构建 rc=0、运行 rc=0 |
| F3 证据脚本 README 断言用双引号包裹含反引号字符串 ⇒ 被 shell 命令替换 | ✅已修 | 期望串改单引号 | 自检 `--self-test-inject` 全 PASS；正式跑该断言 PASS |
| F4 guest 字节与模拟器自身 stdout 混杂，无法逐字节比对 | ✅已修 | 新增 `+semiout=<file>`（VPI 解析）隔离 guest 控制台 | 三平台 stdout 逐字节一致（1136 B） |
| F5 gem5 裸句柄 1 的 `SYS_WRITE` 崩溃 / QEMU 需先 `SYS_OPEN` ⇒ 不能进三平台集 | ✅已修 | `SYS_WRITE` 单独成像 + README/完成区记录理由 | `semihost_write.elf` chipyard rc=0、stdout 1200 B == oracle |
| F6 DPI 桥的 TL 地址必须在 A 通道接收后锁存、`mem_valid` 撤销 | ✅已修 | 增加 `mem_taken` 握手 + `RegEnable` 锁存地址 | 硬件运行通过（长字符串 1135 B、参数块读取正确） |
| F7 执行器仍只覆盖 5 类指令 + semihosting trap | ❌不修 | — | 属任务边界（真核 `005` 替换），非 semihosting 编码显式 halt 并打印 |

#### 第 1 轮 reviewer 验收

方式：独立重跑、不采信完成区；范围 = 14 文件、证据脚本、三平台、节点构建、门控。命令均在 worktree 内以相对路径执行。

**重跑记录（本人真实输出 / 退出码）**
- 一键证据脚本 `run.sh`（运行期证据目录）→ `== summary: PASS=70 FAIL=0 ==`、`EXIT=0`；A3 门控 `check-patch-tree/check-source-state/apply-series` 均 `rc=0`。
- `run.sh --self-test-inject` → 5 条 `injection '<key>' -> FAIL as expected` + `restore md5 matched`（与验收前快照同值）+ `restore -> PASS`、`EXIT=0`；分项：excl 4 FAIL（三平台逐字节 + tests 计数）、exitcode 4 FAIL（`QEMU/gem5/chipyard smoke 退出码 expected=0 actual=64`）、series `16→15`、core-tag / clock-unit 各 1 条内容断言 FAIL。
- **独立反例（engineer 未用）**：`cp` 备份后把 `WumingSemi.cc.patch` 与其在 apply-series 建立的 chipyard 组件源树中的同名 `WumingSemi.cc` 一并把 `reason == kAdpStoppedApplicationExit` 改为 `== 0x20027ULL` ⇒ `run.sh` `PASS=63 FAIL=7`、`EXIT=1`，含 **`单元测试 … actual=14`**（语义命中 SYS_EXIT 映射）+ `check-patch-tree`/`check-source-state`/`apply-series` 检出；`cp` 还原 + `md5sum -c OK`（`59cb4aa0…`/`7a574094…`）⇒ 重跑 `PASS=70 FAIL=0`、`EXIT=0`。
- 三平台：`md5sum expected_smoke.bin qemu-smoke.out gem5-smoke.out chipyard-smoke.out` 四者同为 `24a650c33f04c18b0c561bf56c3c6345`（1136 B）；`expected_write.bin == chipyard-write.out` = `a29b577543250051c79861d7425550c6`（1200 B）。
- QEMU `semihost_write.elf` 独跑：`QEMU_WRITE_RC=0` 但输出 1136 B（缺 64 B 缓冲）⇒ 未 `SYS_OPEN` 时不写 handle 1；gem5 同 ELF 独跑：`GEM5_WRITE_RC=139`（segfault），`gdb -batch -ex run -ex bt` → `#1 BaseSemihosting::callWrite (handle=1) at src/arch/generic/semihosting.cc:272`（守卫在 `:264` `handle > files.size()`，ctor `:127 files.push_back(nullptr)` ⇒ size=1 时 handle=1 越过守卫）。
- 节点复跑（reviewer 自建脚本、chipyard 独占、期间无基线）：`make verilog` `EXIT=0`、Verilator `EXIT=0`、`grep -c '^%Error'`=0、最终链接行含 `WumingSemi.o`、`simulator-chipyard.harness-WumingTinyConfig` 于 13:57:27 重链；6 个 applied 源文件 md5 本地==节点。随后 `make sync-node-repo` → `SYNC_RC=0`、`head=b7cc4f5a28 dirty=0`。
- 门控：`make -k check` `L1_RC=2`，红项 `check-milestones-fresh`（`VIOLATION: R1 … INTEG-059t` 有 worktree 却在「待开始」）、`check-temp-dirs`（5 项陈旧目录，无一是 m12-chipyard-004）——均外部；`check-run-artifacts` 清理本人日志名后 `rc=0`；`make check-modules` 本分支直跑 `L2_BRANCH_RC=0`。
- 快照对账：验收前后 `git status --porcelain -uall` 均 14 行、14 个 md5 逐项相等；无 `scratch/`、`*.orig`/`*.rej`、无 `.inj-bak` 残留。

**约束核验**：① 核内无宿主调用——`WumingCoreStub` 无 `import "DPI"`/`vpi_`/`wuming_semi_*`，只驱动 `io.semi.req{op=immu18[7:0],arg=readRb(16.U),ret=rd8,pc=ip}` 与 `io.semi.resp`（printf 仅为 `+verbose` 日志，003 已有）；② DPI 握手——`mem_taken=(sIdle&&mem_valid)` 单拍，同拍 `RegEnable` 锁存地址、下一拍 `mem_valid` 撤、`state=sReq` 才拉 `tl.a.valid`，`sourceId=IdRange(0,1)` 单 outstanding；长 1135 B 串跨字实跑通过；③ 5 服务对 `spec/Machine-v5 §5.3`：WRITEC/WRITE0 无返回→`0xdeadbeef`、WRITE 返回未写字节、CLOCK=`raw/(CLOCKS_PER_SEC/100)` 百分秒且单调、EXIT `0x20026`→子码（`§7.1` 0x00–0x3F PASS / 0x40–0x7F FAIL，0→0、0x40→64）、返回写 rd8 + `IP+=4`（`§5.4`）；④ 未实现服务号 rc=1 且 stderr 含 `semihosting op 0x01 is not implemented`；⑤ spec/contracts 零改动、tests 仅新增 3 文件；⑥ 完成区 19 非空行（≤30）、无运行期路径；⑦ reviewer 未 commit/push、未改共享台账。

**发现（非阻断，交 architect 收尾处置）**：F-1 完成区「check-run-artifacts=他人 integ 文件」在复核中未复现（复核首跑 23 条非法日志名全为 reviewer 自有 `review-*`，改名后该门控已绿）；F-2 验收标准 6 字面写 L1 rc=0，实际 rc=2，两项红因已逐条核实为外部；F-3 run.sh 对 QEMU `SYS_WRITE` 只断言退出码、不断言 stdout（缺 64 B 由复核补测坐实）。

**判决：Accepted**（验收命令块在本人重跑下全部通过，硬约束无违反；F-1~F-3 为文档级/证据完备性问题，不阻断）

#### 收尾（architect，2026-11-09 14:06）

- 判决 **Accepted**：reviewer 独立反例（改 `kAdpStoppedApplicationExit` 判定）⇒ 7 项 FAIL + 门控检出 ⇒ 还原回绿；三平台 smoke md5 四者同值（`24a650c3…`，1136 B）；节点独占重建 `%Error`=0、`WumingSemi.o` 已链接。
- **`ISS-358` 由 reviewer 独立复现**：`callWrite(handle=1)` 在 `files.size()==1` 时读 `files[1]` 越界 → SIGSEGV（gdb 栈 `semihosting.cc:272`），根因 `handle > files.size()` 应为 `>=`。
- **`SYS_WRITE` 排除三平台比对**已核实合理：chipyard 1200 B / QEMU 1136 B（未 `SYS_OPEN` 缺 64 B）/ gem5 segfault；chipyard 侧有独立 oracle。
- 3 条 finding 处置：F-1 完成区表述已改（非法日志名是本任务 reviewer 产物、已改名）；F-2 验收 6 的 L1 红为外部（`INTEG-059t` 台账行 + 他人临时目录）；F-3 `run.sh` 补 QEMU `SYS_WRITE` stdout `cmp` 断言（71/71）。
