# m19-chipyard-004: chipyard Tiny 新几何与装载（8K ROM / 8K hmon / 256K SRAM）

**模块**：chipyard
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：已验证

## 背景

`WumingTinyConfig` 当前是 BootROM 64 KiB / SRAM 8 MiB / hmon 64 KiB、entry `0xFFFF_FF01_0100`。按 `m19-spec-002` 改为：ROM 8 KiB、SRAM 256 KiB、hmon 8 KiB、entry `MAIN_SRAM_BASE+0x2000`、raw 基址 `0x2000`、header/mailbox/exit/DUMP/signature 地址按新布局。

## 目标

1. `DadaoConfigs.scala` / `WithDadaoTinyAddressMap`：BootROM 8 KiB、SRAM 256 KiB、hmon 8 KiB；`appEntry=0xFFFF_FF00_2000`。
2. `WumingParams` / `WumingTile`：`loadMemBase/Size`、`loadMemEntry`、`hmonBase/Size`、`bootromBase/Size` 按新值；`+loadmem` 窗口 256 KiB。
3. BootROM 资源：`bootrom.tiny.hex` 按 8 KiB 布局重生成（power@0、hmon@0x800、table@0x1F00）；classpath 镜像名不变。
4. 头区/DUMP/signature 仅作为地址常量与测试资产约定；本任务不实现 TSI。
5. 保持 `WumingVastConfig` 不变。

## 验收（逐条贴真实 rc）

1. `make verilog`（WumingTinyConfig）rc=0；Verilator `+loadmem` 装载新 entry 成功。
2. 生成的地址图/参数打印：BootROM 0x2000、RAM 0x40000、hmon 0x2000、entry 0x2000。
3. **可达 FAIL ≥2 路**：① 把 RAM 写回 8 MiB ⇒ 参数/窗口断言红；② 把 entry 写回 0x10100 ⇒ 装载/启动用例红。
4. `check-patch-tree` chipyard 段 0 problem；`check-component-changelog` rc=0。
5. 不改 QEMU/gem5；不接板。

## 约束

独立 `git worktree`；**不提交 git**；只动 `dadao-wuming`/`DadaoConfigs`/bootrom 资源与必要补丁；完成区不写具体 `.work/**` 路径。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 7 个改动文件（chipyard 补丁 5 个 + `components/chipyard/README.md` / `changelog.md`），重点看「Vast 是否被动到」「hex 是否真由固件源产出」「停机/拒绝判据是否可误判」。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 Vast 继承 Tiny 的 `sramSize`/`hmonSize`/`appEntry` ⇒ 改 Tiny 会连带改 Vast | ✅已修 | `WumingVastAddressMap` 三项改为显式常量（8 MiB / 64 KiB / `0xffffff010100`） | `phase vast`：地址图 6 项 + 参数 5 项 rc=0；与未改动前的 Vast 地址图逐行相同 |
| F2 资源解码尺寸写死 64 KiB ⇒ 8 KiB hex 会解码成 64 KiB 假绿 | ✅已修 | `build.sbt.patch` 的 `bootrom.tiny.img` 尺寸 `8 * 1024` | 解码产物 8192 B 且与入库镜像逐字节相等（rc=0） |
| F3 hex 若不是由固件源产出就是伪造资源 | ✅已修 | 证据脚本从 `tests/ee-tiny` 源 + `m19-spec-002` 常量重打包，并与入库 hex 双向对账 | `checked-in-hex-equals-fresh-build` rc=0；源侧迁移见「待裁定」1 |
| F4 停机判据只看进程 rc 会把 `+max-cycles` 超时当绿 | ✅已修 | `checks.py sim-run` 断言 `SYS_EXIT(0x18) reason=0x20026 code=0x0` 行 + 标记串 | 绿跑 `cycle=1839 ... host exit status 0`，rc=0 |
| F5 老 entry 被拒只证明 loader 会拒，未证明 `e_entry` 来自配置 | ✅已修 | 注入②核 `.ENTRY` 参数（red）+ 老 entry ELF 实跑拒绝（rc=1） | inject 两路均 red→还原→回绿 |
| F6 过程中曾误改主工作树（`tests/ee-tiny/*.S`） | ✅已修 | 用 `cp` 还原并 md5 对账（= `HEAD` blob），改动只留在本 worktree 的 chipyard 文件 | 主树 `git status` 仅剩另一会话的 `?? m5out/`；两文件 md5 与 blob 相等 |

判决：无未修 finding，状态置「待验收」。

### 第 2 轮 engineer 订正（reviewer Accepted 后的 4 条 finding）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1「待裁定 1/2 已过时」 | ✅已修 | 待裁定 1/2 改指 `m19-testcases-005`（power 表偏移/hmon 源/跳 ENTRY）与 `m19-testcases-006`（数据槽消费者），保留「本任务未改固件源」事实 | 任务书文本 |
| F2「高 128 KiB 是 image_window」不准 | ✅已修 | README 改为 `image_window = [0xffff_ff00_2000, 0xffff_ff02_2000)`（128 KiB 自 entry 起算），装载窗口仍是整段 `[+0x0000, +0x40000)` | README §地址图 |
| F3 `--inject` 死选项 | ✅已修 | 删除 `--inject` 选项 + `inject()` 函数 + docstring 中的探针说明（改指 005） | `--help` 已无该选项；`run.sh --phase static` 仍 PASS、镜像 md5 `3b1c0d2e…` 不变 |
| F4「76 项」口径 | ✅已修 | 完成区改为「76 verdict + 28 ck 断言 = 104 项」 | `grep -c '^check '`=76、`grep -c '^---- .*: rc='`=28 |

判决：4 条 finding 全修，实现语义未变（hex 与 RTL 参数逐项不变），状态仍 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-28）

**重跑记录（reviewer 本人执行，worktree 根，08:56–09:12；每条以本人输出+退出码为准）**

1. 运行期证据目录内 `run.sh`（`static,build,sim,inject,vast`）⇒ `======== run.sh: PASS`、`rc=0`（08:57:11→09:03:43）；现场计数 76 条 `check` verdict + 28 条 `ck` 断言，唯二 `rc=1` 即注入现场：`addr-map memory@ffffff000000 … actual=0xffffff000000-0xffffff800000 rc=1`、`loadmem ENTRY … actual=0xffffff010100 rc=1`，两条随即 `restore-*-md5` 回绿。
2. `make verilog CONFIG=WumingTinyConfig` rc=0、`grep -c '^%Error'` = **0**；地址图（本人从 chisel.log 抽取）`rom ffffffff0000-ffffffff2000`、`memory ffffff000000-ffffff040000`、`memory fff00000000-fff00002000`；`WumingLoadMem.sv` 现场值 `MEM_SIZE(262144)`、`ENTRY(60'd281474959941632)`=0xffffff002000、`BOOTROM_SIZE(8192)`、`HMON_SIZE(8192)`、`MEM_BASE(…33440)`=0xffffff000000。
3. Verilator 实跑（运行期日志目录）：`sim-ok.err` → `SYS_EXIT(0x18) reason=0x20026 code=0x0 cycle=1839 pc=0xffffff002078`，`semiout-ok.txt` = `TINY8K-OK`；负控 `sim-badentry.err` → `e_entry 0xffffff010100 is not the fixed Tiny entry 0xffffff002000`、rc=1。
4. Vast：`make verilog CONFIG=WumingVastConfig` rc=0、`%Error`=0；地址图 6 行 + `MEM_SIZE(8388608)` / `ENTRY(60'd281474959999232)`=0xffffff010100 / `BOOTROM_SIZE(4194304)` / `HMON_SIZE(65536)` 全等 ⇒ 未被 Tiny 连带。
5. 门控（本人重跑）：`make check-patch-tree` rc=0（12 集 / 464 补丁 OK；chipyard 31 + testchipip 2）、`make check-component-changelog` rc=0、`make check-source-state` rc=0；`make check-knowledge-refs` 于本记录写入后重跑（rc 见下）。
6. 独立数据核验：自行解码入库 hex ⇒ 8192 B、md5 `3b1c0d2e664a72f58a4827dbe4a07a1b`；power@0（292 B）/ hmon@0x800（44 B）/ 保留 `0x1400–0x1EFF` 与尾 `0x1F30–0x1FFF` 全零 / 表 48 B@`0x1F00`（magic `0x44424f54`、v1、cnt1、`boot=0x30001`；项 `type1 flags0x3 off0x800 size0x30`）；再用已合入的 `tools/testcases/arch/build_tiny_bootrom.py --dump` 复判 rc=0，其常量（`0x2000/0x0800/0x0C00/0x1400/0x1F00/0x30`、flags `1|2`、`>IHHII`+`>IIQQQ`、稀疏 hex 格式）与本任务打包器逐项相等 ⇒ 与 `m19-testcases-003` 口径一致；`spec/Kaiwu §1.1/§6.2` 与 `contracts/machine.yaml`（bootrom `0x2000`、ram `0x4_0000`）逐项相等。
7. **独立注入（改被测产物、重跑同一脚本）**：① `build.sbt.patch` 解码尺寸 `8*1024→64*1024` ⇒ `--phase static` **rc=1**（`resgen-tiny-size expected=8192 actual=65536 rc=1`），`cp`+md5 还原（`687525d6…`）⇒ rc=0；② `bootrom.tiny.hex.patch` hmon 首字节 `21→20` ⇒ **rc=1**（`patch-hex-equals-image … first diff at 0x0800 rc=1`），还原（`e26b4751…`）⇒ rc=0。

**约束核验**：改动仅 chipyard 8 文件 + 本任务书（`git status --porcelain -uall` 前/后均 0 行、HEAD `9e04b7ab` 未提交）；未改 QEMU/gem5；记录内无具体 `.work/**` 路径；Vast 三值显式固定且实测未变；脚本两路注入与我两路独立注入均 FAIL→还原→回绿。

**findings（均文档级，不阻断，交 architect 收尾订正）**：F1 待裁定1/2 归属已过时——`m19-testcases-005-启动固件迁移` 已立册派单（其目标 1 即 power `0x1F00/0x800/0x2000` 迁移）、`m19-testcases-006-hmon数据槽消费者迁移` 覆盖 hmon 数据槽，「任何 M19 任务书都未明确归属 / 建议并入 003」应改为 005 / 006；F2 README「高 128 KiB 是 `image_window`」不准（实为 `[0x2000,0x22000)`）；F3 `build_tiny_rom_8k.py --inject` 是打印即返回 1 的死代码（`run.sh` 未用、docstring 选项名也不符），建议删；F4 完成区「76 项断言」实为 76 verdict + 28 ck = 104。

**判决：Accepted** —— 验收命令块在我本人重跑下全绿；几何 / spec / 契约逐项相等；8 KiB 解码尺寸与入库 hex 字节均经我独立反例证伪可达；硬约束无违反；4 条 findings 属文档级，按裁定不阻断。

## 完成区

**测试结果**：`run.sh`（`static,build,sim,inject,vast`）全 PASS，rc=0；合计 **76 verdict + 28 ck 断言 = 104 项**，**0 项非预期红**（仅注入段的两条「预期红」`addr-map memory@ffffff000000 rc=1` / `loadmem ENTRY rc=1`，随即由还原后的回绿证明）；逐项 `check <name>: expected=… actual=… rc=…` 见运行期证据目录 `run-all.log`。
- static rc=0：固件重打包 + 14 项布局断言；入库 hex 与新构镜像逐字节相同（8192 B、md5 `3b1c0d2e…`）；sbt 解码尺寸 8 KiB；Vast 三项数值断言。
- build rc=0：`make verilog CONFIG=WumingTinyConfig`、`%Error`=0；地址图 `rom ffffffff0000-ffffffff2000`、`memory ffffff000000-ffffff040000`、`memory fff00000000-fff000002000`；`WumingLoadMem` 参数 MEM_SIZE `0x40000` / ENTRY `0xffffff002000` / BOOTROM·HMON `0x2000`；解码资源 = 镜像。
- sim rc=0：Verilator 构建；新 entry 探针 `SYS_EXIT reason=0x20026 code=0x0 cycle=1839` + `TINY8K-OK`；老 entry ELF 被拒（rc=1，`is not the fixed Tiny entry 0xffffff002000`）。
- inject rc=0：① SRAM→8 MiB ⇒ 地址图红（`ffffff800000`）→ `cp`+md5 还原 → 回绿；② entry→`0xffffff010100` ⇒ `.ENTRY` 红 → 还原 → 回绿；还原后 apply-series `matches patches`。
- vast rc=0：`make verilog CONFIG=WumingVastConfig`、`%Error`=0；地址图 6 项 + 参数 5 项全等。
- 门控：`check-patch-tree` rc=0（12 集 / 464 补丁；chipyard 31 + testchipip 2，0 problem）、`check-component-changelog` rc=0、`check-knowledge-refs` rc=0、`check-patch-tree --source-state` rc=0。

**修改文件**：`DadaoConfigs.scala.patch`（Tiny 8 KiB/256 KiB/8 KiB + entry `0xffff_ff00_2000`；Vast 三项改显式常量、值不变）、`build.sbt.patch`（解码 8 KiB）、`bootrom.tiny.hex.patch`（8 KiB 布局重生成）、`WumingTile.scala.patch` / `WumingLoadMem.scala.patch`（几何注释）、`components/chipyard/README.md`、`components/chipyard/changelog.md`。

**验收结果**：见上（全部真实 rc；未伪造/未估算，日志落在运行期证据目录）。不改 QEMU/gem5；不接板。

**新发现/坑**：① `apply_series.py` 收尾 `git add -A` 会把 `.conda-env` 符号链接算进树 ⇒ 判等失败，需 `.git/info/exclude`；② `sims/verilator` 没有 `sim` 目标，默认目标即构建仿真器；③ 改 hex 后必须删 `.classpath_cache/chipyard.jar`，否则资源不刷新（假绿）；④ 解码资源落在 `generators/dadao-wuming/src/target/.../resource_managed`；⑤ 新源树首建全量 Scala 编译约 10 min，之后 `make verilog` 增量 ~1–2 min。

**遗留问题**：① 固件源侧 8 KiB 迁移（`tests/ee-tiny/cfx_power_tiny.S` 表基址/hmon 上限、`tools/testcases/arch/build_tiny_bootrom.py` 布局）无任务归属，见「待裁定」1；② hmon 数据槽仍在 `0xD8–0xFF`（spec 新数据区 `0xC00–0xCFF`），见「待裁定」2；③ 放核握手未实现（`MAILBOX` magic `[OPEN]`），见「待裁定」3。

## 待裁定

1. **固件源侧 8 KiB 迁移的归属**：`tests/ee-tiny/cfx_power_tiny.S`（镜像表基址 `0xE000`→`0x1F00`、hmon 源段上限 `0x2000`→`0xC00`、跳 `ENTRY = 0xffff_ff00_2000`）归 **`m19-testcases-005`（启动固件迁移，已立册派单）**；`tools/testcases/arch/build_tiny_bootrom.py` 的 8 KiB 布局归 `m19-testcases-003`。**本任务按约束未改固件源**，hex 由证据脚本从同一固件源 + `spec` 常量打包；005/003 落地后应以新构建器 `--hex-out` 重出本资源并对账（预期字节与本版相同）。
2. **hmon 数据槽位置**：`tests/ee-tiny/cfx_hmon_tiny.S` 的保存槽仍在 hmon SRAM `0xD8–0xFF`（spec §6.2 规定数据区 `0xC00–0xCFF`、栈 `0x0D00–0x1FFF`）。功能无影响（槽位在被复制代码段之外、SRAM 初值 0），但字面口径不一致；槽位迁移归 **`m19-testcases-005`**，其消费者（读槽的测试框架/载体）迁移归 **`m19-testcases-006`（hmon 数据槽消费者迁移，已立册）**。
3. **放核握手**：`MAILBOX` magic 仍 `[OPEN]`（`spec/Kaiwu §6.2.1`），power 未实现 `VERSION`/`MAILBOX` 检查（本任务书明示不实现）；magic 定稿后补 stub 与证据。
