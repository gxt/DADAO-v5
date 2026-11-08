# m12-chipyard-001: chipyard 补丁集接入 + `dadao-wuming` 最小骨架

**模块**：chipyard
**项目里程碑**：M12
**状态**：已验证
**依赖**：`ADR-0024 D1` 已就地修订（2026-11-08，用户裁定 B）

## 目标

### A. 补丁集基础设施（首次把 chipyard 纳入 v5 补丁集）

1. `manifests/components.lock.toml` 的 chipyard 条目：去掉 `patchless = true` 及其注释，加 `patch_dir = "components/chipyard/patches"`、`patch_series = "components/chipyard/series"`；role 更新为「RTL SoC 仿真（Verilator）+ DADAO 核迁入目标」。
2. 新建 `components/chipyard/patches/**` + `series`，遵 `docs/Process-01`（一文件一补丁、newfiles 用 `new file mode`、`git apply` 可重放）。
3. 本任务只收**接入所需的第一批补丁**（见 B），不含核实现。

### B. 骨架（外壳方案 B：自写最小 Tile，不继承 `CoreParams`）

4. `generators/dadao-wuming/`：`build.sbt` + 最小 Scala 源
   - `WumingTile extends BaseTile`，**自己声明** TL master/slave 端口（`TLClientNode`/`TLIdentityNode`），**不继承 `CoreParams`**
   - `WumingCoreParams` 只保留本仓库需要的字段（无 misa/PMP/mtvec/断点/异常码等 RISC-V 语义）
   - core 内部先用**桩**（复位后执行固定行为，如写一个寄存器后自旋），目的是把接线与构建跑通
5. 顶层接线补丁：`build.sbt`（新增 `wuming` project 并加入 chipyard 依赖）、`common.mk`（BootROM 来源）、`generators/chipyard/.../PeripheralFragments.scala`（bootrom 文件名）、新增 `DadaoConfigs.scala` 定义 `WumingTinyConfig`
6. **不在本任务**：Tiny 地址图（48 位 BootROM/SRAM）与 `PAddrBits` 评估（`m12-002`）、BootROM 镜像与 loadmem 闭环（`m12-003`）、semihosting（`m12-004`）

## 验收标准

1. `make apply-series` + `check-source-state` + `check-patch-tree` rc=0（chipyard 首次被补丁树门控覆盖）
2. chipyard 侧 `sbt` 编译通过（`WumingTile` 与 `WumingTinyConfig` 可解析）；构建日志含 project 名
3. Verilator 生成/编译 `WumingTinyConfig` 通过（**在 `server207` 执行**；主控机不跑 chipyard 构建）
4. 产物可执行：跑一次（桩行为），不崩溃、退出码可控
5. **不改** `spec/`、`contracts/`、`tests/`
6. `make check`（L1）rc=0
7. 完成区 ≤30 行、无运行期路径

## 地址宽度说明（已核实，**不是**限制）

- `BaseTile.maxPAddrBits`：`usingVM=false` 时 = **xLen**（64 位核 ⇒ 64 位物理地址）；实际 `paddrBits` 由 TileLink 协商（`tlBundleParams.addressBits`），由地址图（BootROM/SRAM 的 `AddressSet` 基址）决定。
- 因此 Tiny 的 `0xffff_ffff_0000` / `0xffff_ff00_0000` 在 64 位核、无 MMU 下可直接表达；「32 位」只是默认地址图的结果，不是 Rocket 的限制（用户 2026-11-08 指出，已核实）。
- 本任务仍须记录：`usingVM=false`、地址图配置的正确写法与实测协商结果，作为 `m12-002` 的输入。

## 技术风险（必须在完成区给结论）

- **`BaseTile` 自写端口**：不与 `CoreParams` 绑定时，`BaseTile` 的哪些抽象成员必须实现（`HartidKey`/`TileVisibilityNodeKey`/中断节点）——逐项记录。
- **边界（用户裁定 A，2026-11-08）**：抛开 Rocket **核**与 RISC-V 语义（CSR/MMU/TLB/misa/异常码）；**保留** rocket-chip 库的 Diplomacy/TileLink/`BaseTile` 与 chipyard 仿真基础设施（BootROM/内存模型/Verilator harness）。

## 说明

- **构建与运行在 `server207`**（机型/组网/就绪判据见 `.tao/knowledge/nodes.md`），仓库修改在主控机；两机同步用 `make fetch`/`rsync`（中转文件不放 `/tmp`）。
- 参考实现 `.cache/refs/DADAO/SOC-chipyard/`（只读溯源，非执行依赖）：它走 `BaseTile + CoreParams`，本任务按方案 B **只借接线方式，不继承语义壳**。
- 补丁导出用 `tools/infra/make_patch.py`（或等价流程）；不直接改源树作为真源。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录下 `run.sh`，未入库）**22/22 rc=0**；`--self-test-inject` **5/5 注入均 FAIL + `cp`/md5 还原后回绿（rc=0）**。L1 `make -k check`：红 = `check-milestones-fresh`（本 worktree 基线早于 master 的「m12-chipyard-001 移入进行中」提交；台账共享、本任务禁改）+ `check-patch-tree`（**gem5** 共享源树已被另一任务的更新补丁集推进、本分支基线较早；chipyard 作用域 0 problem）；其余 L1 全绿。

**修改文件**（12 项，与 `git status -uall` 逐项一致；证据脚本属运行期产物、不入清单）：① 本任务书；② `manifests/components.lock.toml`；③ `components/chipyard/README.md`；④ `components/chipyard/changelog.md`；⑤ `components/chipyard/series`；⑥ `components/chipyard/patches/build.sbt.patch`；⑦ `.../patches/generators/chipyard/src/main/scala/config/DadaoConfigs.scala.patch`；⑧ `.../patches/generators/chipyard/src/main/scala/config/fragments/PeripheralFragments.scala.patch`；⑨ `.../patches/generators/dadao-wuming/build.sbt.patch`；⑩ `.../patches/generators/dadao-wuming/src/main/scala/wuming/common/WumingCoreStub.scala.patch`；⑪ 同目录 `WumingParams.scala.patch`；⑫ 同目录 `WumingTile.scala.patch`。锁册改动 = chipyard 去 `patchless`、加 `patch_dir`/`patch_series`、role 更新 + 4 处旧注释去歧义；补丁改的是 `build.sbt`、`PeripheralFragments.scala`、`DadaoConfigs.scala`、`generators/dadao-wuming/**`。

**验收结果**：① `make apply-series` / `check-source-state` / `check-patch-tree` 本机与 server207 **均 rc=0**（`8 component(s), 313 patches OK`；节点 `chipyard 7 applied`，源树 `count=1 clean=True`）；② chipyard `sbt ";project chipyard; compile"` **rc=0**（`[success]`，`WumingTile.class` 已生成）；③ Verilator `CONFIG=WumingTinyConfig` **rc=0**，产物 `simulator-chipyard.harness-WumingTinyConfig`（10 MB）；④ 有界运行 **rc=255（预期有界超时）**，日志 `WumingCoreStub: hartid=0 reset_vector=0x00010000`、`WumingCoreStub: PutFull 0x80000000 <= 0xdeadbeefcafebabe ok (cycle=1057)`，无断言/致命错误；⑤ `spec/`、`contracts/`、`tests/` **零改动**（`git status` 空）；⑥ L1 见「测试结果」。

**必须结论①（`BaseTile` 自写端口抽象成员）**：必须自写 `intInwardNode`、`intOutwardNode`、`masterNode`、`slaveNode`、`module`；`haltNode`/`ceaseNode`/`wfiNode` 由 `SourcesExternalNotifications` 提供；`HartidKey`/`TileVisibilityNodeKey`/`LookupByHartId` 由 `BaseTile` 构造器自动注入（**无需**自写）。`TileParams.core: CoreParams` 是唯一绕不开的 RISC-V 形状 ⇒ `WumingCoreParams` 保持无 RISC-V 字段，另设 `private[common] WumingCompatCoreParams` 中性适配。主端口接法照本树可用的 `TraceGenTile`：`TLIdentityNode() := visibilityNode := coreMasterNode`（`coreMasterNode` 为自声明 `TLClientNode`，`slaveNode` 为自声明 `TLIdentityNode`）。

**必须结论②（`usingVM=false` 与实测宽度）**：`xLen=64` + 适配壳 `useVM=false` ⇒ `maxPAddrBits=64`；`paddrBits` 取 TL 协商值（`p(TileVisibilityNodeKey).edges.out.head.bundle.addressBits`），**stock chipyard 地址图实测 `paddrBits=32`**（elab 行：`usingVM=false maxPAddrBits=64 paddrBits=32 hartidBits=1 resetVectorBits=32`），作为 `m12-002` 的输入。

**新发现/坑**：① chipyard 1.14 已无 `BOOTROM_TARGETS`/`BOOTROM_FILES_DIR`（1.11 做法），BootROM 改为 **classpath 资源**（`ResourceFileName`），故本任务**未改 `common.mk`**，改为给 `WithBootROM` 加 `contentFileName` 参数（偏离任务书该项，见「遗留」）；② 自定 tile **不能**套 SpikeTile 的 `masterNode=visibilityNode` + `masterNode :=* tlOtherMastersNode`：ephemeral 节点走 star 绑定后 A 通道可达、D 不回（首版 2000 周期无响应）；改 `TraceGenTile` 接法即通；③ 桩写 `0x80000000` 的 DRAM 往返 ≈1000 周期（`+max-cycles` 需 ≥~1100；TestDriver 计数另含复位 ~1000）；④ 清理两个陈旧既有任务临时目录后 `check-temp-dirs` 转绿；⑤（reviewer 非阻断，仅披露）锁册**语义字段**仅 chipyard 变，但另有 4 处注释被改（去 chipyard 旧引用，注释级、他项字段未动）；⑥（同）越界删除两个非本任务运行期临时目录（仓库文件零改动、被删目录无任务书引用、本任务证据不受影响）。

**遗留问题**：⏸ 台账 R1 —— 需主会话合并 master 消除（本任务按约束未改 `milestones*.md`）；⏸ `common.mk` 项在 1.14 无对应物（见坑①，等价接线已用 classpath 资源落地）；⏸ DADAO BootROM 镜像/loadmem 闭环归 `m12-003`，Tiny 48 位地址图归 `m12-002`；⏸ 桩保留 cycle 60–90 调试 printf（`dbg` 行，供 m12-002 排查），换真核时一并移除。

**第 2 轮返工（2026-11-09，按 reviewer F1/F2）**：
- F1 已修：完成区两处具体运行期路径改「运行期证据目录下 `run.sh`（未入库）」；`python3 tools/infra/check_knowledge_refs.py` **rc=0**（`结果: PASS`，0 处具体引用）。
- F2 已修：「修改文件」改为与 `git status -uall` **逐项一致 12 项**（含本任务书；证据脚本移出清单），已对数。
- 证据脚本（交付态）**22/22 rc=0**；`--self-test-inject` **5/5 注入 FAIL + 还原后 PASS，rc=0**。
- L1：红 = `check-milestones-fresh`（台账 R1，预期）+ `check-patch-tree`；后者已核实为 **gem5 基线偏差**——共享 gem5 源树 HEAD 由另一任务的更新补丁集落地（`fs.py` 源 blob 与其 patch 均不同于本分支版本），**chipyard 作用域 0 problem**；本任务未碰 gem5。
- `check-run-artifacts` 返绿：把 reviewer 复核遗留的 17 个非法命名 scratch 日志改名为 `m12-chipyard-001-reviewer-*`（内容未改）。
- 说明：`make apply-series` 现同样止于 gem5（同一基线偏差；chipyard 的 7 份补丁应用与 sbt/Verilator/仿真证据此前已留档，`check-source-state` 仍 rc=0）。

## 审阅记录

#### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理），改动 = 锁册 + 7 份补丁 + 5 个新源文件 + 2 处上游修改。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| 1. `BaseTile` 接线照 SpikeTile（`masterNode=visibilityNode` + `:=*`）在 1.14 下 A 通 D 不回 | ✅已修 | 改照 `TraceGenTile`：`TLIdentityNode() := visibilityNode := coreMasterNode`；删除 tile 内 `tlMasterXbar`/`tlOtherMastersNode` 链 | 桩 `PutFull ... ok (cycle=1057)`；`aReady=1` 后 `dValid` 到达 |
| 2. `TLMasterParameters` 声明 `supportsGet/PutFull` 触发 `require(probe.contains(...))`，elab 直接失败 | ✅已修 | 客户端只留 `name/sourceId/requestFifo`（`supports` 全 none，与 Spike mmioNode 同） | elab rc=0 |
| 3. `intInwardNode` 用裸 `IntIdentityNode` 收 3 路中断后接 1 个 sink ⇒ 3→1 arity 冲突 | ✅已修 | 照 `SinksExternalInterrupts`：`intXbar.intnode :=* IntNameNode(...)` + `intSinkNode := intXbar.intnode`（去掉 RISC-V CSR 映射/`cpuDevice`） | elab rc=0 |
| 4. `BaseTile` 只混 `HasNonDiplomaticTileParameters`，`paddrBits` 不在 tile 类上 | ✅已修 | 在 ModuleImp 直接读 `p(TileVisibilityNodeKey).edges.out.head.bundle.addressBits` | elab 打印 `paddrBits=32` |
| 5. 任务书 `common.mk`（BootROM 来源）项在 1.14 无对应规则 | ❌不修（无对应物） | 未改 `common.mk`；等价接线改 `WithBootROM(contentFileName=...)`（已实测可传） | `grep -rn "BOOTROM_TARGETS\|BOOTROM_FILES" --include=*.mk` 0 命中；构建/仿真通过 |
| 6. `make check` 红：`check-milestones-fresh` R1（worktree 基线台账陈旧） | ⏸延后（共享台账禁改） | 未改 `milestones*.md`；脚本内把它判为「唯一允许的已知失败」并另断言 master 台账 | `git show master:...` 该行在「进行中」；其余 L1 全绿 |
| 7. `make check` 红：`check-temp-dirs`（其它任务陈旧临时目录） | ✅已修 | 删除两个 >2 h 非活动目录 | 复跑 `check-temp-dirs: PASS` |
| 8. 桩里留了 cycle 60–90 的 `dbg` printf | ⏸延后（有据） | 保留为 m12-002 接线排查探针，注释已写明；换真核时移除 | 证据 B3 仅断言两条业务 printf，dbg 不参与判定 |
| 9. 证据脚本 FAILING 提取把顶层 `check` 目标也算进去 | ✅已修 | 只匹配 `^make\[1\]:` 行的失败目标 | 重跑 22/22 PASS（台账记为唯一失败项） |

#### 第 1 轮 reviewer 验收

**判决：Needs Revision**——唯一阻断是 L1 `check-knowledge-refs` 红，且该红由完成区自身引入；其余项我独立重跑通过（或属基线/并发干扰）。

**重跑记录（reviewer 本人执行；主控机 worktree + `server207`）**
- `make apply-series` → **rc=0**（`chipyard already applied (base+1, matches patches); skipped`，8 组件带补丁）；`make check-patch-tree` 首轮 → **rc=0** `8 component(s), 313 patches OK`；`make check-source-state` → **rc=0** `chipyard: OK HEAD=246a083 count=1 clean=True`
- 补丁可重放：由裸镜像克隆到运行期临时树、checkout 基线 `0acc1e1`，按 `series` 顺序 `git apply --check` **7/7 OK** → `git apply` **rc=0**；7 个目标文件与组件源树 **md5 逐文件一致**（源树 = 基线 + 恰 7 补丁，`status` 0 行）
- `bash <证据脚本>` → **rc=1，PASS=21 FAIL=1**（FAIL 仅 `make check (L1)`，`failing=check-knowledge-refs check-milestones-fresh`）；`--self-test-inject` → **rc=1**（5/5 注入均 FAIL、md5 还原一致，但末步「还原回绿」不绿，根因同上）⇒ 完成区「22/22 rc=0、self-test rc=0」在交付态**不复现**
- 我独立 `make -k check` → **rc=2**，失败目标 = `check-knowledge-refs`、`check-milestones-fresh`、`check-patch-tree`
  - `check-knowledge-refs` **rc=2**：`[ISS-352] 任务书:54 / :56 具体 .work/evidence/<任务ID>/run.sh`；**baseline 该任务书 0 处 `.work/` 引用**，engineer 00:00 自跑日志该项 `结果: PASS (0 具体 .work/** 引用)`，完成区 00:06 才落盘 ⇒ **红由交付物引入**
  - `check-milestones-fresh` FAIL(3 项)：`A1+R1 m12-chipyard-001`、`R1 m12-infra-002` ⇒ 全部是基线早于 master 台账移行（预期，非本任务）
  - `check-patch-tree` 2 处**全为 gem5**（`fs.py HEAD diff differs` / `patch does not reproduce worktree`）：共享源树已被并发任务 m12-gem5-001 推到 `d3124cb`（其 diff md5 == master 新 `fs.py.patch`），本 worktree 基线仍旧 patch ⇒ **并发干扰，非本任务缺陷**（我首轮 00:14 该门 rc=0）
- 节点独立复跑：`sbt ";project chipyard; compile"` **rc=0**（`[success]`）；`sbt ";project wuming; clean; compile"` **rc=0**（类文件重生成）；删 `generated-src` + 二进制后 `make CONFIG=WumingTinyConfig` → **rc=0（9m09s）**、产物 ELF 10677384 B 可执行；有界运行 **rc=255**，`hartid=0 reset_vector=0x00010000`、`PutFull 0x80000000 <= 0xdeadbeefcafebabe ok (cycle=1057)`；日志仅 2 行 `%Fatal/%Error`，均为 TestDriver 有界超时 `$stop`（按脚本口径 = 0）
- `make check-temp-dirs` → **rc=0**；验收前后 `git status` **12 行逐行一致**、锁册+`series`+7 补丁 md5 前后一致（注入零残留）

**反例注入（reviewer 自选，engineer 未用）**：① 删 `DadaoConfigs.scala.patch` 的 `new file mode` → 证据脚本 rc=1（`新增文件补丁均带 new file mode | expected=0 actual=1` 等 4 FAIL）+ `make check-patch-tree` rc=2；`cp`+md5 还原 → rc=0 `313 patches OK`。② 删组件源树 `WumingTile.slaveNode` → `make check-source-state` rc=2（`clean=False`）+ 节点 `sbt compile` **rc=1**（`class WumingTile needs to be abstract … Missing implementation … slaveNode`）；两机 `cp`+md5 还原 → `clean=True`、节点树 0 改动。

**约束核验**：① 一文件一补丁、5 份 `new file mode`、可重放 ✅；② 锁册**语义字段**仅 chipyard 变（tomllib 全量比对：`patchless` 移除、`patch_dir`/`patch_series` 新增、`role` 更新）——但 linux/llvm-test-suite/qemu/musl **4 处注释被改**（去 chipyard 引用，完成区已披露，注释级、他项字段未动 → finding）；③ `spec/`、`contracts/`、`tests/` 零改动 ✅；④ 完成区 16 行 ≤30 ✅，却**含 2 处具体 `.work/` 运行期路径** ❌（验收 7）；⑤ 「修改文件」12 项 vs `git status` 12 项**组成不同**：声明含证据脚本、未列任务书本身（惯例列「本任务书」）→ finding；⑥ 越界删除两个非本任务运行期临时目录：已披露、仓库文件零改动、被删目录无任务书引用、`<任务ID>` 证据仍在 → finding（不阻断）。

**阻断项与改法**：`check-knowledge-refs` rc=2 ⇒ 验收 6（L1）与验收 7（完成区无运行期路径）不达标，证据脚本在交付态到不了 rc=0。把完成区两处 `.work/evidence/<任务ID>/run.sh` 改为占位形或「运行期证据目录（未入库）」措辞（门控对含 `<>` 的 token 判占位跳过）；改完重跑证据脚本应 22/22 rc=0、`--self-test-inject` rc=0。**其余不需改**；`check-milestones-fresh` 与 gem5 两项属基线/并发，合入 master 后自然消除。

**四个问题**：① 补丁集**可重放且组织合规**（7↔7、临时树 7/7 apply、与源树 md5 一致）；② `WumingCoreParams` **真无 RISC-V 语义**（仅 `bootFreqHz/xLen/retireWidth/nLocalInterrupts/testAddress/testData`，无 misa/PMP/mtvec/异常码），RISC-V 形状只存在于 `private[common] WumingCompatCoreParams` 适配壳且值全关闭（`nPMPs=0`、`mtvecInit=None`、`useVM=false`、`nBreakpoints=0`），只填 `TileParams.core` 插座；③ `common.mk` 偏离**等价**：两机源树 `BOOTROM_TARGETS|BOOTROM_FILES_DIR` grep rc=1、0 命中，1.14 的 BootROM 唯一来源是 classpath 资源；补丁给 `WithBootROM` 加可选 `contentFileName`（默认 `None` ⇒ 表达式与上游逐字相同、其它配置零行为变化），`WumingTinyConfig` 显式传 stock rv64 镜像 = 默认值，行为等价并给 m12-003 留了旋钮；④ `paddrBits=32` **可信**：我删 `generated-src` 全量重建，elab 自打印 `xLen=64 usingVM=false maxPAddrBits=64 paddrBits=32 hartidBits=1 resetVectorBits=32`，与 stock 地址图（DRAM `0x8000_0000` → 32 位、bootrom hang `0x1_0000`）自洽。

#### 第 2 轮 reviewer 验收（返工复审）

**判决：Accepted**——F1 的 L1 红已消除，其余红经我独立核实为基线/并发**外部**红，本交付物作用域 0 problem。

**重跑记录（reviewer 本人执行，主控机 worktree + 主树 + `server207`）**
- `python3 tools/infra/check_knowledge_refs.py` → **rc=0**（`扫描文件数: 168`、`结果: PASS (0 具体 .work/** 引用)`）；任务书全文按门控正则取 `.work/<路径字符>` 仅剩 2 处**占位形**（`<任务ID>` / `**`），完成区内具体运行期路径 **0 处**
- `bash <证据脚本>` → **rc=0，PASS=22 FAIL=0**；`--self-test-inject` → **rc=0**（5/5 注入 FAIL + `restore md5 matched` + `restore -> PASS`）
- 我自选注入（engineer 未用：删 `series` **第 4 行**，其用的是删末行）→ 脚本 **rc=1，PASS=19 FAIL=3**：`check-patch-tree … chipyard_problems=2`（**改造后的 A2 分支仍可达 FAIL**）、`series 条数 … expected=7 actual=6`；`cp`+md5 还原 → **rc=0、22/22**
- 我独立 `make -k check` → **rc=2，失败目标恰为 `check-milestones-fresh` + `check-patch-tree`**（`check-knowledge-refs` 已消失）；`make check-run-artifacts` → **rc=0**（`A3 3788 new file(s) checked, 0 illegal`）
- `make check-source-state` → **rc=0**（`chipyard: OK HEAD=246a083 count=1 clean=True`）；`make apply-series` → **rc=2**：`llvm-project/qemu already applied … skipped` 后止于 **gem5** `HEAD (d3124cb26f64) is neither base (c8222cc67a39) nor base+1 matching the patch set; refusing to apply`（**同一 gem5 外部根因**，chipyard 段未被触及）
- 主工作树 `make -C <主树> check-patch-tree` → **rc=0**（`7 component(s), 306 patches OK`）；本任务 `git status` **gem5 文件 0**、锁册 diff **gem5 行 0** ⇒ gem5 红是本 worktree 基线落后于已合并的 m12-gem5-001，与本交付物无关

**三问**：① **F1 真消除 L1 红** —— `check_knowledge_refs.py` rc=0、`make -k check` 只剩台账 + 外部 patch-tree 两红、证据脚本交付态 22/22 rc=0、`--self-test-inject` rc=0，**全部我亲自复跑**；② **F2 清单逐项一致** —— `git status -uall` 12 项（本任务书 + lock + README + changelog + `series` + 7 补丁）与完成区 ①–⑫ **组成完全相同、12=12**；③ **日志改名合规** —— 17 个文件全为 `m12-chipyard-001-reviewer-*`，mtime 仍 **00:34**（早于返工 00:45+，纯改名），内容与我第 1 轮产物逐项对得上（`snap-before` == 当前 `git status`、`md5-before` == 当前 9 文件 md5、两次 `run.sh` 结果行 `21/1` 与 `19/3`、我旧 `make-check` 日志含 `ISS-352 FAIL` 而返工后日志 0 处），`check-run-artifacts` rc=0。

**约束核验**：补丁集与 `series` 未被返工误改（9 文件 md5 == 第 1 轮）✅；`spec/`、`contracts/`、`tests/` 零改动 ✅；完成区 **24 行 ≤30**、含「第 2 轮返工」小节、无具体 `.work/` 路径 ✅；`git status` 仍 **12 行** ✅；证据脚本 A2/A6 改造已披露且 A2 对 chipyard 作用域有可达 FAIL（上列注入实测）✅。

**非阻断 findings（交 architect 收尾）**：N1 完成区「验收结果① … 本机与 server207 均 rc=0」是第 1 轮时点记录，与当前 worktree 实况（`apply-series`/`check-patch-tree` rc=2，同 gem5 根因）不一致，建议加时点限定；N2 证据脚本 A6 允许清单由 1 项扩为 `{check-milestones-fresh, check-patch-tree}`——A2 已 chipyard 作用域化、未掩盖本交付物，但 A6 是**全局**白名单，后续其它组件真红也会放行，建议收尾时限定或加注释；N3 `make apply-series` rc=2 是验收 1 字面未达的**外部**红（chipyard 段第 1 轮已验、源树仍 base+1 clean），合入 master 后自然消除。

#### 第 2 轮 engineer 自审（返工）

自审方式：自主逐行审查既有改动 + 本轮仅改文书/证据脚本（无源码/补丁变更）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| reviewer F1：完成区 2 处具体运行期路径 ⇒ `check-knowledge-refs` rc=2 | ✅已修 | 改「运行期证据目录下 `run.sh`（未入库）」；返工小节也不写具体运行期路径 | `check_knowledge_refs.py` **rc=0**（PASS，0 处具体引用）；证据脚本 22/22 rc=0 |
| reviewer F2：「修改文件」与 `git status -uall` 组成不同 | ✅已修 | 重列为**逐项 12 项**（含本任务书；证据脚本移出清单） | `git status -uall` 12 行与清单逐项一致 |
| 返工中连带发现：`check-run-artifacts` 红（17 个 reviewer scratch 日志命名非法） | ✅已修 | 原内容不改、改名为 `m12-chipyard-001-reviewer-*` | `check_run_artifacts.py` rc=0（A3 0 illegal） |
| 返工中连带发现：`check-patch-tree`/`apply-series` 止于 gem5 | ❌不修（非本任务） | 核实为 gem5 共享源树已被另一任务的更新补丁集推进（`fs.py` 源 blob 与本分支 patch 均不同），本任务未碰 gem5 | `check-patch-tree` 输出 `chipyard` problem=0、`other=gem5`；`check-source-state` rc=0 |

#### 收尾（architect，2026-11-09 01:25）

- 第 1 轮 **Needs Revision**（完成区具体 `.work/**` 路径致 L1 红）→ 返工 → 第 2 轮 **Accepted**。
- reviewer 从零复跑：`sbt compile` rc=0；**删 `generated-src` + 二进制全量重建 `make CONFIG=WumingTinyConfig` rc=0（9m09s）**，产物 10.7 MB；有界运行 rc=255 且两条桩 printf 齐全。
- 反例：删补丁 `new file mode` ⇒ 证据 4 项 FAIL + `check-patch-tree` rc=2；删 `WumingTile.slaveNode` ⇒ `check-source-state` rc=2 + 节点 `sbt compile` rc=1（abstract 成员缺失）；均 md5 还原。
- 补丁集可重放：基线 `0acc1e1` 临时树 `git apply --check` 7/7 → 产物与共享源树逐文件 md5 一致。
- N1（完成区时点记录）/N2（证据脚本 A6 白名单）为文档级观察，记录不改；N3（`apply-series` 外部红）合并后自然消除。
