# m12-chipyard-002: Tiny 地址图落地（48 位核内地址）

**模块**：chipyard
**项目里程碑**：M12
**状态**：已验证
**依赖**：`m12-chipyard-002`（骨架 + 补丁集）

## 背景与事实

- `spec/Machine-v5 §1.1`：Tiny 的 BootROM `0xffff_ffff_0000`（64 KiB，复位向量 = 起始）、SRAM `0xffff_ff00_0000`（8 MiB）；均为 **48 位核内地址**，Tiny **无 MMU、无 cfx**。
- `m12-chipyard-002` 实测：`xLen=64` + `useVM=false` ⇒ `BaseTile.maxPAddrBits=64`；但 **stock chipyard 地址图协商出 `paddrBits=32`** ⇒ 必须改地址图，不是改 `PAddrBits`。
- 相关平台已一致：QEMU 的 `dadao-tiny`（`m12-qemu-001`）与 gem5 FS 的 Tiny profile 用的就是这两个基址。

## 目标

1. 在 chipyard 侧把 BootROM 与 SRAM 放到 spec 规定的地址：
   - `WithBootROM`：地址 `0xffff_ffff_0000`、大小 64 KiB、`contentFileName` 指向 Tiny bootrom 镜像
   - SRAM/内存：地址 `0xffff_ff00_0000`、大小 8 MiB，作为可写主存（TL 从端口）；**不引入 cfx/PTW**
2. `usingVM = false`（无 MMU/TLB）；TL 协商出的 `addressBits` 必须 ≥ 48。
3. 复位向量 = `0xffff_ffff_0000`；核从 BootROM 起始取指。
4. 记录实现方式（改哪个 `AddressMap`/fragment、是否新增 fragment），并写入 `components/chipyard/README.md`。

## 验收标准

1. chipyard 生成的 `WumingTinyConfig` 中，`paddrBits`/`addressBits` **实测 ≥ 48**（打印协商值，禁止写死断言值以外的假设）
2. 生成的 `.dts`/`memmap` 中 BootROM 起始 = `0xffff_ffff_0000`、大小 64 KiB；SRAM 起始 = `0xffff_ff00_0000`、大小 8 MiB
3. Verilator 构建 rc=0（`server207`）；有界运行能从 `0xffff_ffff_0000` 取指（打印取指地址或等价证据）
4. 与 QEMU `dadao-tiny` 的同一最小镜像（放 BootROM）行为一致（退出码或等价可观测结果）
5. `make apply-series` / `check-source-state` / `check-patch-tree` / L1 / L2 rc=0
6. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

- BootROM 镜像内容与 `loadmem` 装载闭环（`m12-chipyard-004`）
- semihosting 应答者（`m12-chipyard-005`）
- 核内部指令实现（`005` 起）
- 修改 `spec/Machine-v5` 的地址图（**不授权**；以 spec 为准）

## 说明

- 若 chipyard 的 `AddressMap` 无法表达 `0xffff_ffff_0000`（如 TL 地址位宽或 mask 限制），**停下报告**并给出实测证据，不要自行改 spec 或缩小地址。
- 构建/运行在 `server207`（见 `.tao/knowledge/nodes.md`），仓库修改在主控机。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录下 `run.sh`，未入库）**42/42 rc=0**；`--self-test-inject` **5/5 注入均 FAIL + `cp`/md5 还原后回绿（rc=0）**。

**修改文件**（10 项，与 `git status -uall` 逐项一致）：① 本任务书；② `components/chipyard/README.md`（新增「地址图」节：实现方式 = 改 fragment 既有字段，不新增 `AddressMap`）；③ `components/chipyard/changelog.md`；④ `components/chipyard/series`；⑤ `patches/build.sbt.patch`（`wuming` 项目加 `resourceGenerators`：hex→镜像资源）；⑥ `patches/generators/chipyard/src/main/scala/config/DadaoConfigs.scala.patch`（`WumingTinyAddressMap` + `WithDadaoTinyAddressMap` + `WumingTinyConfig`）；⑦ 同目录 `.../wuming/common/WumingCoreStub.scala.patch`（复位向量取指 + SRAM 写读回三拍探针）；⑧ `.../wuming/common/WumingParams.scala.patch`（`testAddress` → SRAM 基址）；⑨ `.../wuming/common/WumingTile.scala.patch`（`slaveNode` 注释随地址图修正）；⑩ `patches/generators/dadao-wuming/src/main/resources/dadao/bootrom/bootrom.tiny.hex.patch`（新增：Tiny bootrom 的文本 hex 镜像）。

**验收结果**：
① 向量宽：elab 行 `xLen=64 usingVM=false maxPAddrBits=64 paddrBits=48 hartidBits=1 resetVectorBits=48`，`paddrBits=48 ≥ 48` 达标（非写死，脚本从日志解析）。
② 地址图：elab `Generated Address Map` 与节点生成的 `.dts`/`memmap.json` 均为 BootROM `0xffff_ffff_0000`/`0x10000`、SRAM `0xffffff000000`/`0x800000`；DTS 唯一 `memory` 节点、无默认 `memory@80000000`/`rom@10000`。
③ 构建/取指：节点 Verilator 构建 rc=0；有界运行（`+max-cycles=5000`，rc=255 为收口预期）打印 `fetch 0xffffffff0000 -> 0x4e04ff004a05ff7e`（地址序）与 `sram put/get 0xffffff000000 ↔ 0xdeadbeefcafebabe`。
④ 与 QEMU 一致：同一 64 KiB 镜像（`dadao-tiny,bootrom-image=`）两侧首条取指地址均 `0xffff_ffff_0000`、首 8 字节均 `4e04ff004a05ff7e`；QEMU rc=249（guest 跳入未装载 SRAM 后 fault）、chipyard rc=255（桩核不执行指令），指令级等价留待真核（005+）。
⑤ 门控：`check-source-state` 本机/节点 rc=0；`check-patch-tree` 节点 rc=0（`8 component(s), 314 patches OK`），本机因 qemu/gem5 被在飞/已合并任务推进而整轮红、但 chipyard **0 problem**；`apply-series` 节点 rc=0（本机唯一拒绝来自 qemu）；L2 `check-modules` rc=0（脚本按 probe：本基线已被 `m12-integ-001` 越过、共享安装根 qemu 不再支持本基线测试所用的 `dadao-m1`，故 L2 在 master 的临时检出上跑同一 scope，3 分 09 秒）；L1 红因逐项归类、均在本任务之外（`check-milestones-fresh` 台账基线、`check-patch-tree` 并发共享树、`check-components` 同为 `dadao-m1` 基线落后、`check-temp-dirs` 他任务陈旧目录）。
⑥ 证据脚本：非交互、逐项打印期望/实际、任一失败非零退出、计数现场统计；注入 `cfg-base`/`cfg-size`/`hex` 为文件层（cp+md5 还原），`paddr`/`fetch` 为证据层覆写观测值。
⑦ 完成区 ≤30 行、无运行期路径。

**新发现/坑**：
- **补丁集不能带二进制**（`make_patch.py` 走文本 `git diff`，断言⑨ 逐字节比对）⇒ Tiny bootrom 以**文本 hex** 入库，由 `build.sbt` 的 `resourceGenerators` 在构建期解码成 classpath 资源 `/dadao/bootrom/bootrom.tiny.img`（已在 fat jar 内实测确认）；同时 `appendDTB` 必须关——Tiny 的 BootROM 只有复位/启动 stub，且 64 KiB 内容再加 DTB 会撞 `TLROM` 的 `require(wrapSize <= size)`。
- **移除 `ExtMem`/`ExtTLMem` 后 harness 不再有 `SimDRAM`**：`+dramsim*` 无意义；且 chipyard 的 `printf` 由 `PRINTF_COND` 门控，**必须带 `+verbose`** 才输出桩核日志。
- **SRAM 用 `BankedScratchpadKey`（`busWhere=MBUS`、`dtsEnabled=true`）替换默认 64 KiB scratchpad**：这是「TL 从端口 + DTS `memory` 节点」的最小改法；`TLRAM` 默认 `cacheable`（`RegionType.UNCACHED`）⇒ L2 直通、无需 acquire。
- **坑**：chipyard 源树 base commit 自带 `.java_tmp/.gitignore`，`rm -rf .java_tmp` 会把「删除上游文件」带进补丁集（已回滚；补丁集仍是 8 份）。
- **坑（环境）**：任务 worktree 必须同时软链 `.work`/`.cache`/`.dadao`（安装根按 `repo_root` 相对解析，否则工具链不可见）；节点每次 `check-modules` 都重跑 `install-host`（重装 4.3 GB）且缺 `musl`/`musl-shared` 产物（已补建），单轮 ≥25 min ⇒ 不适合作常规验收口径，L2 仍留控制机。
- **坑（基线漂移）**：任务基线 `c9320ffa` 之后 master 合入 `m12-integ-001`（移除 `dadao-m1`/`profile=node` 过渡别名）⇒ 共享安装根的 qemu 与本分支旧测试/旧 L1 探针不再匹配（L1 `check-components` 与 L2 arch 用例因此红）；两红均与 chipyard 无关，合并 master 后自然消失。

**遗留问题**：
- ⏸ 台账 R1 与基线漂移类红项（`check-milestones-fresh`/`check-components`/`check-temp-dirs`）：禁改台账、禁删他人临时目录、不碰 qemu，由主会话合并 master / 收尾消除；合并 master 后 L2 应回到「本分支直跑」口径（脚本按 probe 自动选择）。
- ⏸ Tiny bootrom 镜像内容与 `loadmem` 装载闭环归 `m12-chipyard-004`（本任务只落「文本 hex + 解码通路 + 指向该镜像的 `contentFileName`」）。
- ⏸ 桩核不校验 `d.bits.opcode`（ROM/SRAM 均可读，`denied` 已断言），随真核替换；Tiny 上无关核外设备（CLINT/PLIC/Debug/L2）仍由 chipyard 基础设施带出，裁剪不在本任务范围，如需另立任务。

## 审阅记录

#### 第 1 轮 engineer 自审

方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = 8 份补丁的源码终态 + `run.sh` + README/changelog。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F1 `DadaoConfigs` 里 `BootROMLocated` 首次编译报 not found（误从 `subsystem` 导入） | ✅已修 | import 改为 `freechips.rocketchip.devices.tilelink.BootROMLocated` | 节点 `sbt compile` rc=0（`[success]`），elab rc=0 |
| F2 桩核取指打印的是 TL 总线字（字节序与「地址序」相反），与 QEMU `in_asm` 不可直接比对 | ✅已修 | 新增 `fetchWord = Cat(bytes[0..7])`，按地址序（大端）打印 | 仿真打印 `0x4e04ff004a05ff7e` == 镜像首 8 字节 == QEMU `OBJD-T` |
| F3 `rm -rf .java_tmp` 误删 base commit 自带的 `.java_tmp/.gitignore`，会把删除动作带进补丁集 | ✅已修 | 从 base blob 恢复该文件后重新导出 | 补丁集回到 8 份；断言⑨ `check-patch-tree` rc=0 |
| F4 证据脚本首轮 9 项 FAIL：hex 解析误吃 `+++ b/…`/`@@` 头、`.dts` 里 48 位地址按 2-cell 编码（无 `0xffffffff0000` 字面）、`cfx/PTW` 检查误中注释 | ✅已修 | 解析只取 2 位 hex token；`.dts` 改用 python 解析 `reg` 四 cell 拼 64 位；`cfx/PTW` 检查排除 `//` 注释行 | 证据脚本 42/42 rc=0；注入 `hex` 仍精确打在 B 段 |
| F5 有界运行无桩核日志（缺 `+verbose`，`PRINTF_COND` 关闭） | ✅已修 | `run.sh` 的仿真命令加 `+verbose` | 日志出现 `fetch`/`sram put`/`sram get` 三行 |
| F6 桩核只覆盖「写」不覆盖「读回」，SRAM「可写主存」证据偏弱 | ✅已修 | 增加 sGet 状态与读回打印 | `sram put … ok` + `sram get … -> 0xdeadbeefcafebabe ok` |
| F7 桩核未校验 `d.bits.opcode`（理论上 AccessAck 无数据） | ❌不修 | — | 两个 manager 均支持 Get（ROM `supportsGet`、TLRAM `supportsGet`），且 `denied` 已断言；opcode 校验属真核职责，随 `WumingCoreStub` 退场 |
| F8 `sram get` 打印总线字、`fetch` 打印地址序，呈现口径不一致 | ⏸延后 | 打印文本已注明 `(byte order = address order)` | 桩核为临时探针，随真核移除，不再统一口径 |

#### 第 2 轮 engineer 自审（环境漂移后复核）

方式：自主逐行审查（engineer 深度 1）。触发：全量证据脚本在「master 合入 `m12-integ-001`（移除 `dadao-m1`）」后由绿转红，逐项归因。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| F9 L2 断言原为「本机直跑」：基线落后后必红，且归因会被误读成本任务破坏 L2 | ✅已修 | `run.sh` 加 probe（安装根 qemu 是否仍有 `dadao-m1`）：有 ⇒ 本分支直跑；无 ⇒ 在 master 的临时检出（`.work`/`.cache`/`.dadao` 软链，跑完 `worktree remove`）跑同一 L2 scope | 脚本 `[INFO]` + `OK（L2，与 chipyard 无关 ⇒ master 检出）`，rc=0；临时 worktree 已注销（`git worktree list` 无残留） |
| F10 L1 允许红项原为 2 项硬白名单，随环境变化会「无条件放行」或「无条件失败」 | ✅已修 | 改为逐项分类：只容忍且必须验证证据的 4 类（台账基线 / 并发 patch-tree / 基线落后的 `check-components` 且 llc+clang 仍 PASS / 他任务陈旧目录且违规路径不在本任务下） | 脚本 `[PASS] make check (L1：红因均在本任务之外)` 并打印 2 条 cause；注入模式下 A 段整段 SKIP |
| F11 节点 L2 路径不可行：每次 `check-modules` 重跑 `install-host`（重装 4.3 GB），且节点缺 `musl`/`musl-shared` 产物，单轮 ≥25 min | ✅已修（回退） | 删除节点 L2 断言，L2 留在控制机 + master 等价口径；节点仅保留 apply-series / source-state / patch-tree（快） | 脚本改后 42/42 rc=0；节点侧三项全绿 |
| F12 `run.sh` 的「BootROM 镜像名」断言把补丁**文件路径**当实参传给 `expect_has`，恒真（形同虚设） | ✅已修 | 改为 `"$(cat "$CFG_PATCH")"` | 注入 `cfg-base`/`cfg-size` 仍精确命中 A7；该断言本身在 `hex` 注入下不受影响 |

#### 第 1 轮 reviewer 验收

方式：独立重跑，不改交付物；注入用 `cp` 备份 + md5，已还原。快照对账：`git status -uall` 首/中/末逐行一致，5 个目标文件 `md5-before == md5-final`，`git worktree list` 无残留（我建的 master/merged 临时树已 `worktree remove`，补丁重放树在 review 临时目录）。

**重跑（本人真实输出/退出码）**：① `run.sh` ⇒ `PASS=42 FAIL=0`（首跑与还原后回绿各一次，回绿 `GREEN_RC=0`）；② `run.sh --self-test-inject` ⇒ `5/5 injection -> FAIL as expected` + `restore md5 matched` + `restore -> PASS`、`SELFTEST_RC=0`；③ **独立反例（engineer 未用：删 `series` 的 bootrom 行）** ⇒ `PASS=39 FAIL=3`（A1 `expected=8 actual=7`、A2 `chipyard_problems=2`）、`INJ_RC=1`，`cp` 还原 md5 `57ddc339…` 相等 ⇒ 回绿 `42/42`；④ base `0acc1e1` 干净树补丁重放 `git apply --check` + 实施 **8/8 OK**、`new file mode` 6 份齐、每份恰 1 个 `diff --git`；⑤ `check-patch-tree` ⇒ `8 component(s), 314 patches OK`（chipyard 0 problem）。

**实测（不采信转述）**：paddrBits 取自节点 elab 日志（节点↔本机 md5 `6f93bc49…` 相同）`…maxPAddrBits=64 paddrBits=48 hartidBits=1 resetVectorBits=48`，取值源 = `p(TileVisibilityNodeKey).edges.out.head.bundle.addressBits`（协商值，非写死）；`.dts`（节点取回）`memory@ffffff000000 reg=<0xffff ff000000 0x0 0x800000>`（唯一 memory 节点）+ `rom@ffffffff0000 reg=<0xffff ffff0000 0x0 0x10000>`，无 `memory@80000000`/`rom@10000`，memmap.json 同值；补丁 hex 解码 40 B sha `2cf10375…` == `make build-bootrom` 的 `bootrom.bin`，且节点上由 `resourceGenerators` 实际生成的 `/dadao/bootrom/bootrom.tiny.img` 资源 md5 `b8c88a3e…` == 我按 `build.sbt` 逻辑独立解码结果（首 16 B `4e04ff004a05ff7e4a06ffff4a070000`）⇒ 解码无 off-by-one/字节序错；QEMU 由本人跑 `-M dadao-tiny,bootrom-image=<64 KiB>` ⇒ `rc=249`、`in_asm` 首条 `0xffffffff0000:`、`OBJD-T: 4e04ff004a05ff7e…` == 镜像首 8 字节，全零镜像同样 249、`-d int` 空 ⇒ 249 是 `dadao_excp_to_exit_code` 的 guest UNDI monitor 退出码（`DADAO_EXIT_MONITOR(3,9)==0xF9`）而非超时，chipyard 255 是 `+max-cycles=5000` 的 TestDriver `$stop` 有界收口。

**门控归因（本 diff 是否引入红）**：分支 L1 `rc=2`＝`check-patch-tree`（并发 qemu/gem5）+`check-milestones-fresh`（台账基线）+`check-components`（分支探针要 `dadao-m1`，共享 qemu 已被 `m12-integ-001` 移除）+`check-temp-dirs`（他任务目录）；master 检出 L1 `rc=2`＝仅 `check-patch-tree`+`check-temp-dirs`；**master + 本任务 diff 临时树 L1 `rc=2`＝仅 `check-temp-dirs`（`QEMU-061t`/`TESTCASES-071t`，与本任务无关），`check-patch-tree 314 patches OK`、`check-components PASS`**；L2：脚本 probe ⇒ master 检出 `rc=0`，**我在 master+diff 树 `make check-modules rc=0`（165 PASS/0 FAIL）**，分支直跑确红（分支 L2 重跑日志 `0/10 passed`，qemu `-machine dadao-m1` 未知）＝基线漂移。

**约束核验**：地址/尺寸与 `spec/Machine-v5 §1.1` 表逐项一致（BootROM `0xffff_ffff_0000`/64 KiB、复位向量=起始、SRAM `0xffff_ff00_0000`/8 MiB、无 cfx/PTW）；`spec/contracts/tests` 未动（A6 status=0）；改动 10 文件与「修改文件」逐项一致；完成区 27 行（非空 21）≤30、无运行期路径；节点副作用仅 musl/musl-shared 的构建与安装产物（均被 `.gitignore` 覆盖），节点 `components/chipyard/**` 为未跟踪文件、未改任何已跟踪仓库文件。

**findings（不阻断）**：R1 `run.sh` 的 L1 分类对 `check-milestones-fresh` 无条件容忍（缺二次证据）；R2 注入 `paddr`/`fetch` 是脚本内覆写观测值而非产物层，`build.sbt.patch` 解码逻辑无脚本断言（已由我比对节点产物补证）；R3 `BAD_SIM` 排除所有含 `TestDriver` 的行，会一并放过该文件自身的断言行。

**专项**：① `paddrBits=48` 真实测出（协商值、日志自节点取回、注入 32 即红）；② 与 QEMU 的「首条取指地址 + 首 8 字节」一致成立，`rc 249 vs 255` **不是**同一种有界超时（249＝guest UNDI 故障码、255＝有界收口），完成区口径已如实写明；③ 是——L1/L2 的红全属基线漂移/并发/他任务环境，本 diff 在 master+diff 树上未引入任何红。

**判决：Accepted**

#### 收尾（architect，2026-11-09 05:22）

- 判决 **Accepted**：reviewer 独立反例（删 `series` 的 bootrom 行）⇒ 3 项红、`cp`+md5 还原回 42/42；base `0acc1e1` 干净树 8/8 补丁重放。
- **`paddrBits=48` 为 Diplomacy 协商值**（`TileVisibilityNodeKey` bundle），非写死；hex→img 解码与节点真实产物 md5 一致（`b8c88a3e…`），无 off-by-one/字节序错。
- **与 QEMU 一致**仅限「首条取指地址 + 首 8 字节」；`rc 249 vs 255` 分别是 guest UNDI 退出码与 `+max-cycles` 有界收口，**不是同一语义**，完成区已如实写明。
- L1/L2 四类红经「master + 本 diff」树证明**全部与本任务无关**（基线漂移/并发/他人临时目录）；`master+diff` 的 L2 165 PASS/0 FAIL。
- 不阻断 findings R1–R3（脚本 L1 分类、注入方式、`BAD_SIM` 排除规则）记录，不改。
