# m12-chipyard-007: Tiny 的 BootROM 固定固件 + power 搬运 + 最小 hmon handler

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-018`（双 TL 端口 + 8-beat 取指 + FSM 骨架）；`m12-spec-003/004` 已合入
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 用户裁定（2026-11-10 实现基线，R1–R16 + 补充）

- **R1 = C**：移位/位操作 2 拍、简单算术 1 拍；**以 1 GHz 时序可行**为约束
- **R2**：乘法周期可配（初值 3 拍），评测后再定；考虑面积
- **R3 = A**（radix-4），保留 radix-2 备选
- **R4 = A**：按 hardfloat 设计移植（不引入 Chisel 依赖）
- **R5**：预取缓冲 **8 beat（64 B，`FETCH_DEPTH=8`）**
- **取指与访存用两个 TileLink**（M12 就拆）：`IdRange(0,3)`，两个独立 `TLBundle` 与状态机
- **power SRAM（8 MiB）与 hmon SRAM（64 KiB）是两个不同 SRAM**
- **R7**：`ldm`/`stm` 整段预检 + **逐个元素精确重入**（整条指令可重执行，不记进度）；**中途总线拒绝 ⇒ 报当前运行模式 `CFXMEM`**
- **R8**：寄存器堆 2 读 2 写（做不到则保守 1 读 1 写并说明）
- R9–R12 = A（1 条/拍、`swym` 1 拍、M12 不流水、扩展 + 较大改动 005 核）
- **R13**：hmon 编入 BootROM，power 搬运（`Machine-v5 §6.1/§6.2`）
- **R14 = A**：新写最小 Tiny hmon handler（8 KiB 上限）
- **R15 = B**（当前版本无嵌套）、**R16 = B**（去掉硬件 `halted` 兜底）

### BootROM 固定固件布局（`Machine-v5 §6.2`）

| 偏移 | 内容 | 大小 |
|---|---|---|
| `0x0000`–`0x1FFF` | power 启动 stub | 8 KiB |
| `0x2000`–`0x3FFF` | hmon 运行段 | 8 KiB（校验阈值） |
| `0x4000`–`0xDFFF` | 保留区（必须全零） | 40 KiB |
| `0xE000`–`0xFFFF` | image index table | 8 KiB |

- `crt` **与测试程序一起链接**、整体落 SRAM；入口固定 `0xffff_ff01_0100`；宿主只装 SRAM。
- `cg3 rc10` 初值 = 该 cfx 内部 SRAM 起始；写入忽略低 2 位。

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，同 Vast，决策 2 = A）
- **无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **三平台 Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**（实现上仍只看 `immu18`，不判断 cfxha）
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon

## 目标（本任务只做「装载与移交」，不做异常分派）

1. **BootROM 固定固件构建器**：产出恰好 64 KiB 镜像，布局 `0x0000–0x1FFF` power（8 KiB）/ `0x2000–0x3FFF` hmon（8 KiB）/ `0x4000–0xDFFF` 保留全零（40 KiB）/ `0xE000–0xFFFF` image index table（8 KiB，`§6.1` 格式、`count=1`、`type=1`、`boot_magic=0x30001`）。
2. **power stub（≤8 KiB）**：校验表头/表项 → 逐 8 字节复制 hmon 段到 `0x0fff_0000_0000` → 写 `excp_vector`（幂等）→ `trap cfx_hmon, 0x30001` → hmon `escape` 回 stub → 跳 `0xffff_ff01_0100`。
3. **最小 hmon handler（≤8 KiB）**：入口即向量；校验 `CFXTRAP` + magic；`escape cfx_hmon, [excp_cause_ip, 4]` 返回。**不做**异常分派/退出码（`019`）。
4. **SoC 侧**：hmon SRAM 与 power SRAM 作为两个独立从设备；BootROM 按 `bootrom-image` 原样装入。
5. **装载契约**：宿主只装应用段（SRAM）；`crt` 与测试程序一起链接；入口固定 `0xffff_ff01_0100`。

## 验收标准

1. **BootROM 镜像可构建**：恰好 65536 字节；四段偏移/大小与上表一致；表头字段与 `§6.1` 逐字段一致；保留区全零
2. **power→hmon 移交闭环**：能观测「复制完成 → 写向量 → `trap` → hmon 入口 → `escape` 回 stub → 跳到应用入口」，且 hmon 段内容与 BootROM 内一致（逐字节比对）
3. **hmon handler ≤8 KiB**（实测大小写入完成区），power stub ≤8 KiB
4. **应用装载契约**：宿主向 BootROM 下发 `PT_LOAD` ⇒ 显式失败；`e_entry ≠ 0xffff_ff01_0100` ⇒ 显式失败；`crt` 在 SRAM 内（可观测）
5. 273 例整数测试零回归；Tiny 44/44
6. Verilator 构建 rc=0（主控机）、`%Error`=0；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
7. 一键证据脚本（含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- QEMU/gem5 的 Tiny hmon（按用户决策，**排在 M13 前置**）
- 访存/控制流/FP（`008` 起）
- smon（Tiny 不实现）

## 说明

- 与 `006` 的设计定稿保持一致；若实现中发现设计需调整，**停下报告**（不要自行改设计）。
- **构建与调试在主控机**（用户 2026-11-10：chipyard 后续构建/调试一律主控机）；小规模仿真也在主控机。**长仿真才上节点**（且节点须自行构建，Verilator 产物机器相关，不跨机复制）。仓库修改在主控机；节点操作后 `make sync-node-repo`。

## 审阅记录

### 第 1 轮 engineer 自审

逐行核对 `WumingDecoder`/`WumingCore` 新增分支（`br.*`/`trap→CFXTRAP`/`escape`/`cfx2rd`/`cfx2rc`）、`tiny/power.S`、`tiny/hmon.S`、`tiny_crt.S`、`build_tiny_bootrom.py`、`WumingLoadMem` 契约检查；实跑 `make build-bootrom`、`make verilog` + Verilator、证据脚本（FAST 与 `--self-test-inject`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 非 semihosting 的 `trap` 不进 `sTrap`（`sExec` 只按 `d.isSemi` 判）⇒ `trap cfx_hmon` 被当 NOP 静默执行 | ✅已修 | `sExec` 改按 `d.isTrap` 进 `sTrap`，`semiIsHost := d.isSemi` | 闭环日志出现 `cfxtrap`/hmon 入口/`escape`/应用入口；273 例 md5 不变 |
| `MuxLookup` 中 `2.U -> v === 0.U` 被按 `->` 优先解析成元组比较（Scala 编译失败） | ✅已修 | 加括号 `(v === 0.U)` / `(v =/= 0.U)` | `make verilog` rc=0 |
| 反例注入 `copy`/`hex` 在 `make build-bootrom` 之前篡改镜像，注入点被覆盖 | ✅已修 | 先重建再篡改，注入只作用于被检产物 | 5 个注入全部 FAIL，还原 md5 一致 |
| 契约反例 ELF 单段落在 BootROM/hmon 时先命中 `e_entry` 检查，掩盖窗口检查 | ✅已修 | 反例改为两段：`e_entry` 合法 + 第二段落在禁写窗口 | 三条具名错误各自命中 |
| `hmon` 表项 `size` 需 8 字节对齐（§6.1） | ✅已修 | builder 补零对齐（`align8`）并写入 `size` | `size=56`、`size % 8 == 0` |
| 证据脚本「还原回绿」调用把 `FAST=1` 当成了脚本参数（写成 `bash $0 FAST=1`） | ✅已修 | 改为 `FAST=1 INJECT= bash "$0"` | `--self-test-inject` 全绿 |
| `chain` 注入靠改脚本自身，bash 预读缓冲导致时红时绿（非确定） | ✅已修 | 改为注入应用 ELF 侧（跳过 crt ⇒ 入口不合法） | 该注入每次必红（`closed-loop run rc`=1） |
| `FAST=1` 复用旧镜像，注入还原后仍用注入过的 ELF | ✅已修 | 证据脚本始终重跑 `make build-bootrom`（秒级） | 还原后回绿 |

### 第 1 轮 reviewer 验收

**重跑记录（全部 reviewer 亲跑：两次完整跑证据脚本 + 多次单项）**
- 镜像：`make build-bootrom` rc=0，65536 B、md5 `777b6bc9ba66c19783fb7f0a487249fd`；**独立解析二进制**（不采信 builder 输出）：表 @`0xe000` magic `0x44424f54`/version 1/count 1/boot_magic `0x30001`/reserved 0；表项 type=1 **flags=0x3** offset `0x2000` **size=56** rsv=0；`[0x4000,0xe000)` 40 KiB 与表尾**全零**；power 336 B、hmon 56 B(=7×8)，objcopy 平坦段与镜像对应区间**逐字节相同**。
- 闭环：我自写解析（非脚本输出）得 157 条 exec，顺序 power `0xffffffff0000` → hmon `0x0fff00000000` → 应用 `0xffffff010100`；复制 **7 ld + 7 st** 源/目的/值与镜像逐字节全等（hmon 窗口外仅 1 条应用自身 store）；`cfx2 cg3 rc10 write=1 data=0x00000fff00000000` → `cfxtrap ip=0xffffffff0134 magic=0x30001` → hmon `rc2=0x1`/`rc4=0x7f0f0001`（`&0x3ffff == 0x30001`）→ `escape target=0xffffffff0138` → `exec ip=0xffffff010100 inst=0x4e04ff00`；与 power/hmon ELF 反汇编地址逐条对上（cfx2rc@`…0130`、trap@`…0134`、escape@`0x0fff00000030`）；`fault` 仅应用体末尾 1 条（harness `*** PASSED ***`）。
- 装载契约反例（**reviewer 自己构造 ELF**，不复用脚本产物）：BootROM `PT_LOAD` ⇒ rc=1 具名报错；hmon `PT_LOAD` ⇒ rc=1；`e_entry=0xffffff010104` ⇒ rc=1；同批合法镜像 ⇒ rc=0。
- 回归：亲算 273 例运行输出 md5 = `2d4d94651346ef673c5a855e024c1489` == 期望文件 == 005/018 任务书基线；Tiny `44 total, 44 passed`（check-inst PASS 44/44）。
- 注入：`--self-test-inject` **rc=0**（5/5 全红、还原 md5 一致、回绿）；**自选注入**：builder 表项 `size` 改 `hmon_size-8`(=48) ⇒ **rc=1**（`table hmon size expected=56 actual=48` 等 4 条红）⇒ `cp`+`md5sum -c` 还原（md5 复原）⇒ **回绿 rc=0**（PASS=61 FAIL=0）。
- 门控：第 1 次完整跑 `PASS=67 FAIL=0`；第 2 次完整跑 **rc=1**、`PASS=66 FAIL=1`（唯一红项是 L1 白名单外的第 4 个外部目标，见下）。Verilator/elab rc=0、`%Error`=0（up-to-date：源 16:39 < 烘焙镜像 17:39 < 仿真器 17:41，且 classpath 镜像 cmp 通过）；L2 rc=0；check-patch-tree chipyard 0 问题（⑥/⑨ 真跑）；source-state 12 组件全 clean+base+1。
- L1 红项逐条（**全部非本任务**）：① patch-tree 7 条全 gem5 —— 共享 gem5 源 HEAD `2b00a96` 含仅存在于 m13-gem5-004 补丁集的 `src/sim/process.cc.patch`（我比对其工作树确有、本工作树无）；② run-artifacts 唯一非法名 = `m13-gem5-004-reviewer-dirty_page.c`；③ temp-dirs 5 项全为 m13-gem5-002/003、m13-infra-001、m13-testcases-004 的临时目录；④ 第 2 次新增的 milestones-fresh：违反者是 **m13-testcases-006**（18:48 才派单建 worktree，晚于我第 1 次跑 18:33；本工作树台账副本停在分支基线、无该行，同一命令在主仓 rc=0）—— 与 007 无关且本树不可修。apply-series rc=1 仅因 gem5 拒（manifest 顺序 llvm→qemu→gem5，中止于 chipyard 之前）。
- 纪律：工作树快照 before/after 逐行相同、目标文件 md5 相同、HEAD 仍 `d7132a49`（**未 commit/push**）；完成区 23 行 ≤30、无运行期路径；声明 7 新增+3 改+10 patch = 20 文件与 `git status -uall` 一一对应、无未声明改动、无注入备份残留；台账未改。

**组件树（`git checkout -q .` 事件，reviewer 独立判断）**：chipyard 源树 `status` 空、HEAD `86f1c6f`（committer 今日 17:06、reflog 多次 amend）、check-patch-tree ⑥（patch 还原 == 源树文件）与 ⑨（`base..HEAD` diff == 补丁集）**均通过**，源树 `bootrom.tiny.hex` md5 == 补丁集值 `dae8df0e…`；其余 11 组件同样 clean + base+1。⇒ **恢复可信**：源树与补丁集逐文件一致、无残留脏改；唯一无法从盘上证伪的是「是否另有他任务未提交 WIP 被一并清掉」，但全部组件均 clean 且与各自补丁集一致，未发现任何失配痕迹。

**finding（非阻断，交 architect）**：① 脚本 `no_stray_stores` 恒真（输入已按窗口过滤），建议删除或改为「窗口外仅允许应用 1 条 store」（该性质我已人工核过）；② `apply-series: no chipyard refusal` 在当前环境恒真（gem5 先拒即中止、chipyard 永不被跑到），实际由 ⑥/⑨ + source-state 兜底（二者的 FAIL 路径已被 `hex` 注入打红过）；③ L1 白名单只列 3 个外部目标，任何新增外部红都会让脚本 rc=1（本次即如此），是否放宽由 architect 定；④ spec §6.2 第 5 步（写 `switch_run_mode`）未实现，任务书目标 2 亦未列、该写入在 Tiny 下被忽略（无可观测差异）。

**判决：Accepted** —— 007 自有检查两轮全绿；两次出现的红项均逐条证实为并发他任务/共享工作区产物。

## 完成区

**测试结果**：证据脚本 rc=0（完整跑 `PASS=67 FAIL=0`，含 chipyard 重建 + L1/L2；L1 的 3 项失败均为外部，已按外部白名单判定，见遗留问题）；注入自检 5/5 全部 FAIL、md5 一致、回绿；273 例 md5 `2d4d94651346ef673c5a855e024c1489` 与 m12-005 基线一致；Tiny `44/44`；Verilator rc=0、`%Error`=0；L2 `check-modules` PASS。
**修改文件**：
- 新增：`tests/shared/bootrom/tiny/{power.S,hmon.S,power.lds,hmon.lds,tiny_common.inc}`、`tests/shared/bootrom/tiny_crt.S`、`tools/testcases/arch/build_tiny_bootrom.py`
- 改：`tests/shared/bootrom/tiny_smoke.S`（crt 前导、入口改名）、`Makefile`（`build-bootrom` 产 Tiny 固定固件）、`components/chipyard/changelog.md`
- chipyard 补丁集（`make_patch` 导出，10 个 patch 变更）：`build.sbt`（稀疏 hex 解码）、`DadaoConfigs.scala`（hmon SRAM 第二从设备 + 入口/窗口参数）、`Wuming{Core,Decoder,Params,Tile}.scala`、`WumingLoadMem.{scala,cc,v}`、`bootrom.tiny.hex`
**验收结果**：
- 镜像 65536 B：`magic=0x44424f54 version=1 count=1 boot_magic=0x30001`；表项 `type=1 flags=0x3 offset=0x2000 size=56`；保留区 40 KiB 与表尾全零；power 336 B / hmon 56 B（均 ≤8 KiB）
- 闭环（可观测）：`cfx2rc vector<=0x0fff00000000` → `cfxtrap ip=0xffffffff0134 magic=0x30001` → `exec ip=0x0fff00000000` → `cg5 rc2=0x1` / `cg5 rc4=0x7f0f0001` → `escape target=0xffffffff0138` → `exec ip=0xffffff010100`；复制 7 个字与镜像逐字节一致（`ld`/`st` 双向核对）
- 装载契约：BootROM `PT_LOAD`、hmon `PT_LOAD`、`e_entry≠0xffff_ff01_0100` 三者 rc=1 且各具名报错；合法镜像仍 rc=0；crt 首指令 `4e04ff00`（设 SP）在 SRAM 入口执行
- 门控：`check-patch-tree` chipyard 0 问题、`check-source-state` chipyard OK、L2 PASS
**新发现/坑**：
1. `sExec` 只在 `d.isSemi` 时进 `sTrap`，非 semihosting `trap` 被**静默当 NOP**（编译与静态门控全绿）；只有端到端日志能暴露 —— 协议类「静默成功」须按缺陷处理。
2. BootROM 镜像在 elaboration 时烘进 Verilog ⇒ 改固件必须重跑 `make verilog`，不能只换 hex 验证。
3. 稀疏 `@offset` hex 让 64 KiB 镜像的入库文本从 ~197 KB 降到 ~3 KB。
4. DADAO 汇编不支持符号算术重定位 ⇒ `LOAD_ADDR rb, symbol` 不可用；crt 采用「入口设 SP 后顺序落入应用」。
5. 在组件树里用 `git checkout .` 当「清空重置」会清掉未提交改动；重置应走 `git reset --hard <base>`（先导出 WIP）。
6. 注入自检会临时改仓库文件，**不得与 L1/L2 并发**（曾致 `check-inst-smoke` 误红）。
**遗留问题**：
- L1 的三项失败均为外部：`check-patch-tree` 的 gem5 断言（并发任务 `m13-gem5-004` 已改写并提交共享组件源的 gem5，与本工作树 master 的 gem5 补丁集不一致）、`check-run-artifacts`（其它任务留在共享日志根的非法文件名）、`check-temp-dirs`（其它任务的过期临时目录）。合并/清理后应回绿。
- 五类同步异常进 hmon、完整 cfx 寄存器组、`escape` 0/+4 完整语义未做（`m12-chipyard-019`）；当前非法 cfx 寄存器访问按 CFXREG 进 hmon 后由最小 handler park。
- QEMU 仍用旧 trampoline（Tiny 固定固件镜像在 M13 三平台统一）；本镜像与构建器已备好供其复用。

#### 收尾（architect，2026-11-10 19:24）

- reviewer **Accepted**：镜像 65536 B（md5 `777b6bc9…`），独立二进制解析核过表头/表项（`type=1 flags=0x3 offset=0x2000 size=56`）、40 KiB 保留区与表尾全零、power 336 B / hmon 56 B；闭环 157 exec、7 ld+7 st 与镜像逐字节全等、关键日志与 ELF 反汇编对址。
- 装载契约反例（reviewer 自建）：BootROM `PT_LOAD` / hmon `PT_LOAD` / `e_entry=0x…104` 各 rc=1 且具名报错；合法镜像 rc=0。
- 273 例 md5 `2d4d9465…` 三方一致；Tiny 44/44；注入 5/5 + 自选（`size=48`）红→还原→绿。
- 门控：Verilator 0、L2 0、chipyard ⑥/⑨+`--source-state` 全绿；L1 红项逐条外部（gem5 补丁集、他任务日志名/临时目录/台账）。
- **`git checkout -q .` 事件**：reviewer 独立核 `check-patch-tree` ⑥（patch 还原==源树）与 ⑨（`base..HEAD` diff==补集）均过、源树 `bootrom.tiny.hex` md5 == 补集值 ⇒ 组件树可信。
- 非阻断（转 `ISS-369`）：`no_stray_stores` 断言恒真、`apply-series` 的 chipyard 归因当前环境恒真（由 ⑥/⑨ 兜底）、L1 白名单只 3 项外部目标。
- spec `§6.2` 第 5 步（写 `switch_run_mode`）未单独实现：Tiny 下写入被忽略、无可观测差异，记录在案。
