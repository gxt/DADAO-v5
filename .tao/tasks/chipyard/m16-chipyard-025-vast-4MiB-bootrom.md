# m16-chipyard-025: RTL Vast 4 MiB BootROM（窗口 + 稀疏镜像 + 启动路径）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-024` 合入（同改 `components/chipyard`，串行）；`m16-testcases-016` 已合入（DIV-12 登记方）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待验收

## 背景（用户 2026-11-23 裁定 B：修 RTL）

`m16-testcases-016` 实测登记 **DIV-12**：RTL 的 `cfx_power cg7` 块 0 报 **64 KiB** BootROM（`start=0x3ff_ffff_0000`、`size=0x1_0000`），而 `spec/Kaiwu §3` 与 `contracts/machine.yaml(vast)` 规定 **4 MiB**（`0xffff_ffc0_0000`、`0x40_0000`）。根因：`DadaoConfigs.scala` 的 `WumingVastAddressMap.bootROMBase/bootROMSize` 直接继承 Tiny，`bootROMImage` 也继承 `/dadao/bootrom/bootrom.tiny.img`。

**口径**：窗口 base/size 与复位向量规则（`base + size − 64 KiB`）是硬件；镜像内容与布局（偏移 0 索引表 + payload + 末 64 KiB 启动段）是构建/装载侧。改窗口不会断启动，前提是镜像按 profile 构建。

**现成件**：`tools/testcases/arch/build_step5_bootrom.py` 已产出标准 Vast 4 MiB 镜像（索引表 + hmon/smon ELF + 零填充 + 末 64 KiB power flat 段，链接在 `RESET_PC`）；chipyard 资源生成器吃**稀疏 hex**（`@<offset>` 行，见 `build_tiny_bootrom.py --hex-out`），组件补丁集不携带二进制。

## 要做

1. **硬件窗口**：`WumingVastAddressMap` 改 `bootROMBase = 0xffff_ffc0_0000`、`bootROMSize = 0x40_0000`、`bootROMImage = "/dadao/bootrom/bootrom.vast.img"`；**Tiny 保持 64 KiB 不变**。
2. **Vast 镜像稀疏 hex**：给 `build_step5_bootrom.py` 加 `--hex-out`（与 `build_tiny_bootrom.py` 同一格式），产出组件的 `bootrom.vast.hex`（稀疏，零区用 `@offset` 跳写），资源生成器解码为 `/dadao/bootrom/bootrom.vast.img`。
3. **启动路径**：确认 RTL harness 能用 4 MiB ROM 并从索引表把 hmon/smon 装入各自 SRAM（现有 `+loadmem` 仍用于测试本体）；若探针 prelude 需要自有 payload，按同一镜像格式生成（不改 QEMU/gem5 的镜像构建语义）。
4. **登记收尾**：`m16-testcases-016` 的 `arch-power-001` 槽 5/6 改为规范值（`0x3ff_ffc0_0000`/`0x40_0000`）；删 `expected-divergences.yaml` 的 **DIV-12**（或按"例外被修好即提示删登记"的流程走）；`tests/arch/README.md` 的 power 小节同步。
5. **不回归**：Tiny 64 KiB BootROM 与 step5 启动链；现有 RTL 探针（`tests/arch/hart`、`ptw`、`power`）与 `run_arch --level smoke`。

## 不做

- 不改 QEMU/gem5 的镜像构建与装载语义；
- 不改 spec/契约（4 MiB 已是契约值）；
- 不动 `cfx_power` 的 common face（ISS-524）与 `cfx_power_ctrl` 写侧（ISS-525）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `cfx_power cg7` 块 0：`start=0x3ff_ffc0_0000`、`size=0x40_0000`，块 1–15 `exists=0`；`m16-testcases-016` 的 28 槽逐槽全绿（DIV-12 删除）；
2. 复位从 `0xffff_ffff_0000` 起执行、hmon/smon 由索引表装入各自 SRAM，测试本体经 `+loadmem` 正常起跑；
3. **可达 FAIL ≥2**：注入「几何改回 64 KiB」与「镜像仍按 base 放置 64 KiB」⇒ 探针/启动链红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog` 记录 rc；
5. Vast/Tiny 重建耗时与 md5 记录。

## 完成区

**测试结果**：`run.sh`（基线+门控）**25/25 PASS**；`run.sh --no-gates` **18/18 PASS**；`run.sh --inject` **35/35 PASS**（注入 1/2 真实红 → `cp`+md5 还原 → 强制重建回绿）。`arch-power-001` **28 槽全绿、无 DIVERGED**，槽 5/6 = `0x3ff_ffc0_0000`/`0x40_0000`；`arch-power-002` 3 槽绿；`run_arch --self-test` rc=0；`run_arch --level smoke --platforms qemu` 10/10；`check_cfx15` 三模式 `--self-test`/`--expected`/`--stream` 全 rc=0（56/16/16 槽）。
**修改文件**：`Makefile`、`tools/testcases/arch/build_step5_bootrom.py`、`tests/ee-vast/power_vast.S`、`tests/arch/expected-divergences.yaml`、`tests/arch/README.md`、`components/chipyard/{README.md,changelog.md,series}`、`components/chipyard/patches/{build.sbt.patch,DadaoConfigs.scala.patch,System.scala.patch,IOBinders.scala.patch,DadaoSparseBootROM.scala.patch,bootrom.vast.hex.patch}`、本任务书。
**验收结果**：
- 重建：Vast 全量 **283–305 s**（本轮返工最终 `b219fd0c75683dbe8c12c2f95902ba20`），Tiny **74 s**（`318860b6b3e2d2f0a6aaadf798fe2140`）；`make verilog`/`make` rc=0、`%Error`=0。
- 镜像：`bootrom.vast.hex` `429075eb…`；`bootrom_vast.bin` **4194304 B** / `4d9451f4…`（索引表 count=2、hmon@0x50/smon@0x1550、power@0x3f0000）；资源解码 `bootrom.vast.img` 同 md5；Tiny 镜像 `a5d78816…` 不变。
- 启动链：`reset_vector=0xffffffff0000`；HMON/SMON 首 8B = `0x21fc00d87a0c50bf`/`0x4e060bff4a04fff0`（与两份 ELF 首段逐字节相同，证明索引表装入各自 SRAM）。
- 门控：`check-patch-tree` rc=0（11 套 462 patches OK）、`make_patch` 二次 0 written/30 unchanged、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog`/`check-no-residue`/`check-knowledge-refs` rc=0。
- 注入：几何回 64 KiB ⇒ 槽 5/6 = `0x3ff_ffff_0000`/`0x1_0000` 红；vast hex 换成 64 KiB Tiny 镜像（base 放置）⇒ 复位落入零区、仿真 180 s 超时红；还原 md5 后回绿。
**新发现/坑**：① 上游 `TLROM` 把 4 MiB 内容展成 `wire [524287:0][63:0]`，Verilator 生成模型 5 h+ 未完成；新增 `SparseTLROM`（只物化非零区段、零间隙返回 0，与整镜像逐字节等价）后 Vast 全量重建 ~5 min。② RTL power 变体不能把 hmon `0xF8` 直接指 `appEntry`（hmon 的 `escape` 会把 `cg5 rc3` 改写成非 ROM 地址，`arch-power-001` 槽 3 红）；改为指 `trap+4`、由 power 在 trap 后跳 `appEntry`。③ `check_cfx15.py` 的 §4.7 断链是 **`m18-spec-005`（5834e2b9）措辞改动 + 024 新增断言**造成（现文「软件只读（写忽略）」/「合法值仍为 `{0,4,8}`」），不是长期基线红；本任务 1 行放宽（两版措辞都接受 + `仍为` 可选）后三模式 rc=0。④ 稀疏 ROM 的零间隙此前无判据：本轮在 `run.sh` 的 boot-chain 探针加两处零间隙读（`base+0x10000`/`base+0x3e0000` 期望 0）；注入默认返回 `0xDEADBEEF` 时该断言精确判红（16/18），还原后回绿。注入还暴露 `Mux1H` 的 `true.B` 默认与零默认会 OR 进块内字，已改为 `Mux(hit, Mux1H, 0)`（块内读不受零间隙默认影响）。
**遗留问题**：`arch-ptw-010` rc=50 仍是既有基线红（master sim 同 run.json，非本任务引入）；其余无。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `sparseChunks` 首版把「首个非零→全镜像末非零」合成一个区段，`SparseTLROM` 仍生成 524288 宽信号 | ✅已修 | 按 `mergeGap=0x10000` 截断零间隙，产出 [0,0x2e50) 与 [0x3f0000,0x3f26b8) 两个小区段 | `SparseTLROM.sv` 83 KB / 2×2048 词；Vast 重建 301 s；power 28 槽绿 |
| RTL power 变体把 hmon `0xF8` 指 `appEntry`，槽 3（cause_ip 在 ROM）红 | ✅已修 | `power_vast.S` 改为写 `trap+4`，并在 trap 后 `.if POWER_RTL_BODY` 跳 `0xffffff010100` | 槽 3 回 1；28 槽绿 |
| `build_step5_bootrom.py` 返回 tuple 后 `self_test`/`main` 调用需同步 | ✅已修 | 更新两处调用；`--check-hex` + hex 往返/注入自检 | `--self-test` rc=0；`check-hex` PASS |
| `System.scala` 返回类型与 `IOBinders` 的 `.module.contents` 不兼容 | ✅已修 | `bootROM` 统一为 `LazyModule`；IOBinders 只对 `TLROM` 取 bootrom 字符串 | `sbt ;project chipyard; compile` rc=0；Vast/Tiny 构建 rc=0 |
| Tiny 回归面 | ✅已验 | 未改 Tiny 几何/镜像；资源生成器同时解码两份 | `bootrom.tiny.img` md5 `a5d78816…`；Tiny sim 构建 rc=0 |
| `power_vast.S` 增加 `.if` 后 QEMU/gem5 标准 power 字节可能漂移 | ✅已验 | 默认 `POWER_RTL_BODY=0`；与 HEAD 源分别汇编 `llvm-objcopy` | 两份 `power.bin` md5 同为 `e14ec38c…`，`cmp` 相同 |
| `check_cfx15.py` §4.7/§5.1 断言被 `m18-spec-005` 措辞改动打红（三模式 rc=2） | ✅已修 | 接受「软件写忽略」与「软件只读（写忽略）」两版；`imms20` 正则允许「合法值仍为」；docstring/错误串同步 | 三模式 `--self-test`/`--expected`/`--stream` 全 rc=0（56/16/16 槽） |
| `run.sh` 对稀疏 ROM 零间隙读无可达 FAIL（F1） | ✅已修 | boot-chain 探针加 `base+0x10000`/`base+0x3e0000` 两槽期望 0，纳入 `run.sh` 判据 | 注入零间隙默认 `0xDEADBEEF` ⇒ 16/18、精确 [FAIL] 零间隙；还原后 18/18 |
| `SparseTLROM` 的 `Mux1H(... :+ true.B, ... :+ 0)` 默认恒高，零默认掩盖了块内 OR | ✅已修 | 改为 `Mux(hit, Mux1H(...), 0.U)`；块内只由 one-hot 命中驱动 | 零间隙注入只影响间隙两槽；块内 HMON/SMON 与 power 28 槽仍绿 |
| `arch-ptw-010` rc=50 | ⏸延后 | 既有基线红；master sim 同 run.json | 主仓同命令 rc=1 |

### 第 1 轮 reviewer 验收

**重跑（均 reviewer 亲自执行；证据脚本 = 运行期证据目录内 `run.sh`，rc 取被检命令自身）**
- `run.sh`（基线+门控）rc=0 ⇒ **24/24 PASS**；`run.sh --inject` rc=0 ⇒ **34/34 PASS**；`run.sh --no-gates`（注入 3 态）17/17。
- 槽值实测 `slots=[63,3,1,1,5,4398042316800,4194304,…]`（=`0x3ff_ffc0_0000`/`0x40_0000`），28 槽无 `DIVERGED`；`arch-power-002` rc=0。
- 注入 1（几何回 64 KiB）重建 301 s ⇒ 槽 5/6=`4398046445568/65536` 真红；`cp`+md5 还原配置=`f7e9707a…`。
- 注入 2（vast hex←Tiny 镜像）重建 296 s ⇒ 复位落零区真红；`cp`+md5 还原 hex=`429075eb…`；强制重建 287 s ⇒ sim `afd25230…`、28 槽回绿。
- 注入 3（reviewer 独立）：改 `DadaoSparseBootROM.scala` 令零间隙返回 `0xDEADBEEF`，重建 282 s（sim `9ce5d4e3…`）⇒ 独立探针零间隙读到非零、非零两槽仍与镜像逐字节同；`cp`+md5 还原源码=`66a45865…`，重建 286 s 回 `afd25230…`、探针 4/4 MATCH。

**约束核验（逐条）**
- 4 MiB 几何：`WumingVastAddressMap` = `ffffffc00000`/`0x400000`/`bootROMReset=base+size−0x10000`、镜像 `/dadao/bootrom/bootrom.vast.img`；Tiny `ffffffff0000`/64 KiB 未动（配置 grep 双侧通过）。
- `DIV-12` 整条删除（全仓 grep 仅剩 README/任务书叙述）；`DIV-14` reason 仅去掉「DIV-12 的同一几何」旧引用、其余语义不变；`tests/arch/README.md` power 小节同步。
- **SparseTLROM 等价性**：① TL `AddressSet(base,size−1)` 覆盖整 4 MiB；② 生成 RTL 两块外恒 `64'h0`，块界 `[base,base+0x2e50)` 与 `[base+0x3f0000,base+0x3f26b8)` 包住全部 2898 个非零字节（reviewer 自写解码器独立比对 hex↔bin 全等、非零集合相同）；③ 字节序 `foldRight` 与上游 `TLROM` 同式；④ 运行期探针 4/4（含两处零间隙=0）⇒ 结构 + 实测双向成立。
- 镜像/hex：bin **4194304 B** `4d9451f4…`、hex `429075eb…`、资源解码 `bootrom.vast.img` 同 md5、Tiny `a5d78816…`/`9334a87e…` 未变；`--check-hex` rc=0（reviewer 自跑）、`--self-test` 含坏 hex 拒绝。
- 启动链：`WumingCore: boot hartid=0 reset_vector=0xffffffff0000`；HMON/SMON SRAM 首 8B `0x21fc00d87a0c50bf`/`0x4e060bff4a04fff0` = 两份 ELF 首段；`+loadmem entry=0xffffff010100`。
- Tiny 不回归：`01-load-store` **38/38**、`11-cfx` chipyard **5/5**；chipyard+qemu 合跑 3/5（cfx2rc/cfx2rd 的 qemu 签名 0 B）⇒ 主仓同命令同结果、json 归一化后**逐字节相同** ⇒ 既有状态非本任务；Tiny sim md5 `318860b6…` ≠ 主仓 `a97fea2d…`（异树重建，ISS-453），镜像/hex 与行为均同基线。
- 门控：`check-patch-tree` rc=0（chipyard 30 patches、11 套 462 OK、无 problem）、`make_patch` 0 written/30 unchanged、index-blobs/tests-index/tasks/changelog/no-residue rc=0、`run_arch --self-test` PASS、smoke qemu **10/10**。

**两条基线红**
1. `arch-ptw-010`：本树 rc=50 与 master（主仓 sim）**run.json 全同**、`SYS_EXIT reason=0x20026 code=0x32 pc=0xffffff010204 arg=0xffffff017900` 同值，仅 cycle 与 loadmem 路径不同（逐行 diff）⇒ **既有红，非本任务引入**。
2. `check_cfx15.py` rc=2：断言由 **m16-chipyard-024 新增**（021 版无此行），而 **m18-spec-005（5834e2b9，11-23 22:36）** 已把 `src_frame` 行改成「软件只读（写忽略）」⇒ **spec-004 之后新引入的解析断链、024 合入即红，非长期既有红**；主仓同 rc=2（非本任务引入），且 `--stream`/`--expected`/`--self-test` 全 rc=2（`expected()` 必经 `facts()`）。**当前无 issue 登记，完成区「既有基线红」归类不准确。**

**判决：Needs Revision（仅 1 项阻断，其余全部在我自己的重跑下通过：24/24、34/34、38/38、10/10、门控 rc=0）**
- 阻断项：按裁定，`check_cfx15` §4.7 断链须 **1 行修复或登记 issue**（spec 行文改动须用户确认；判据侧放宽属断言变更，由 architect 定夺），并把完成区「既有基线红」订正为「spec-005 措辞 + 024 断言新引入」。
- 非阻断 findings：F1 `run.sh` 对零间隙读**无可达 FAIL**（注入 3 后仍 17/17 绿）⇒「与整镜像逐字节等价」未进门控，建议纳入探针或登记；F2「TLROM 4 MiB 展开致 Verilator 5 h+ 不收敛」无留档日志，仅补丁注释 + 生成物结构（`SparseTLROM.sv` 84 KB、2×2048 词、块外恒 0）佐证；F3 Tiny sim 跨树 md5 不同（ISS-453），不构成回归。
- 现场还原对账：工作区 `git status` 与开工快照逐行一致、无 `.preinject` 残留、配置/hex md5 复原、sim 回 `afd25230…`；reviewer 未提交任何 git。

### 第 2 轮 engineer 自审（返工）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| reviewer 阻断：`check_cfx15.py:150` 只认「软件写忽略」，`m18-spec-005` 已改「软件只读（写忽略）」 | ✅已修 | `tests/arch/hart/check_cfx15.py`：两版措辞都接受，docstring/错误串同步；另修同源的 `imms20` 正则（允许「合法值仍为」） | 三模式 `--self-test`/`--expected`/`--stream` 全 rc=0 |
| F1：零间隙读无判据（reviewer 注入 `0xDEADBEEF` 仍全绿） | ✅已修 | `run.sh` boot-chain 探针加两处零间隙读（`base+0x10000`/`base+0x3e0000`）并纳入判据 | 基线 18/18；注入默认非零 ⇒ 16/18，两处 `[FAIL]` 精确命中；还原重建后 18/18 |
| F1 注入暴露 `SparseTLROM` 的 `Mux1H` 默认恒高（块内字被 OR） | ✅已修 | 改为 `Mux(hit, Mux1H(selects), 0.U)`；块内只由 one-hot 命中驱动 | 注入时 power 28 槽仍绿、仅零间隙两槽红；还原后 sim `b219fd0c…` |
| reviewer 指出完成区把 spec-005 断链误归「既有基线红」 | ✅已修 | 完成区改为「spec-005 措辞 + 024 断言新引入，本任务 1 行修复」；`arch-ptw-010` 单独保留为既有红 | 本文件「新发现/坑」③/「遗留问题」 |

### 第 2 轮 reviewer 验收

**重跑（reviewer 亲自执行，rc 取被检命令自身）**
1. `check_cfx15` 三组 × M=3/2/0：`--self-test` rc=0、`--expected` rc=0（56/16/16 槽）、`--stream` rc=0（`56/16/16 slot(s), 0 failure(s)`）；反例（把两版措辞都删）rc=2 ⇒ 断言仍有可达 FAIL、非恒真。
2. `run.sh` rc=0 ⇒ **25/25**；`run.sh --no-gates` rc=0 ⇒ **18/18**；`run.sh --inject` rc=0 ⇒ **35/35**（注入1 重建 294 s→`dcc1e685…` 真红、注入2 295 s→`d0bff600…` 真红、还原重建 273 s→`b219fd0c…` 28 槽回绿）。
3. **Mux 修复判定**：改前 `Mux1H(sels :+ true.B, datas :+ 0.U)` 的常真选择子载荷是 `0.U`，OR 进块内字**不改任何位**（第 1 轮基线零间隙读 0、非零区读镜像值即证）⇒ **无害，但违反 Mux1H 的 one-hot 前置条件**（依赖「多选按位或、未选置零」实现细节），自审「块内字被 OR」措辞偏强；改后 `Mux(hit, Mux1H(sels), 0.U)`：块不相交 ⇒ 命中即 one-hot 取块内字、未命中取 0，生成 RTL `… : (sel0 ? _GEN_0[…] : 64'h0) | (sel1 ? _GEN[…] : 64'h0) : 64'h0` 两支均正确。
4. 独立复比：自写解码器 hex 解码 == bin **全 4 MiB**、非零 2898 字节集合相同（段 `[0,0x2e50)`/`[0x3f0000,0x3f00c2)`/`[0x3f2000,0x3f26b5)`）；运行期 4 槽探针 MATCH（`44424f5400010002`/`0`/`0`/`4e057fff4c040001`）、`reset_vector=0xffffffff0000`。
5. **本轮独立反例（F1 门控可达 FAIL）**：Mux 未命中默认 → `0xDEADBEEF`（备份 `580de488…`）重建 290 s（sim `12e99d6e…`）⇒ `--no-gates` **rc=1、16/18、恰两处零间隙 FAIL**（两槽 `0xefbeadde00000000`、hmon/smon 不变）；`cp`+md5 还原、重建 287 s 回 `b219fd0c…` ⇒ **18/18 rc=0**。
6. power/Tiny/门控：`arch-power-001` 28 槽、槽 5/6 `4398042316800`/`4194304` 未回退，`arch-power-002` rc=0；`01-load-store` 38/38、`11-cfx` chipyard 5/5（json 与第 1 轮主仓基线逐字节相同）；6 门控 rc=0 + `make_patch` 0 written/30 unchanged、self-test PASS、smoke qemu 10/10；完成区归类已订正（③ = spec-005 措辞 + 024 断言新引入，遗留仅 `arch-ptw-010`）。
7. 现场还原对账：`git status` 16 项 = 第 1 轮快照 + 本轮 `check_cfx15.py`、无 `.preinject` 残留、配置/hex md5 复原、sim 回 `b219fd0c…`；reviewer 未提交 git。

**findings（文档级，不阻断）**：F-a 完成区「修改文件」漏列 `tests/arch/hart/check_cfx15.py`（`git status` 实有）⇒ 收尾补列，防 architect 漏 staging；F-b 自审「块内字被 OR」措辞偏强（实为 one-hot 契约违例，载荷为 0 故无害）；F-c 沿第 1 轮，「TLROM 4 MiB 展开致 Verilator 5 h+ 不收敛」仍无留档日志。

**判决：Accepted** —— 三组 `check_cfx15` rc=0、`run.sh` 25/25、`--no-gates` 18/18、`--inject` 35/35、独立反例红→还原→回绿，约束无违反。
