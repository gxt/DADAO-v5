# m16-chipyard-019: RTL cfx0/2 寄存器面与权限（A）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-017`（cfx5 命令接线）合入
**可并行分片**：否
**预估**：3–4 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景（用户 2026-11-22 裁定：先 A 再做 B）

004 盘点：RTL 的 `WumingCfxHa` 只有 hmon/power/ptw，**cfx0 umon 与 cfx2 smon 全缺**——无寄存器行、`cfx2rd`/`cfx2rc` 访问直接 `CFXREG`；同步异常还固定进 hmon（`WumingParams.scala.patch:154` 的 `monitor = 0`）。

本任务只做 **A：寄存器面 + 权限**；U/S 模式进入路由由 `m16-chipyard-020`（B）另做。

## 要做

1. **cfx 序列**：`WumingParams.scala` 的 `WumingCfxHa`（Vast）加入 cfx0、cfx2；Tiny 不加（Tiny 不跑 Linux，保持现状）。
2. **寄存器行**：`GewuFile` 为 cfx0/cfx2 提供 cg/rc 行（模式行、id/version/计数、异常帧、scratch、全局中断掩码等，按 `DADAO-12 §3` 与 `contract-see` 的 cfx 寄存器表）；保留 rc 仍 `CFXREG`。
3. **权限**：`cfx2rd`/`cfx2rc` 访问 cfx0/2 时走通用两轴掩码；未实现的寄存器/保留位按 CACHE 类同法报 `CFXREG`。
4. **探针**：RTL 探针读 cfx0/2 寄存器、写读回、保留 rc ⇒ `CFXREG`；只测寄存器面，不测 U/S 模式进入。
5. **不回归**：Tiny 的 cfx 序列不变；cfx3/4/5/63 现有行为不变。

6. **三方用例（B）**：cfx0/2 的 case 定义/期望只写一份；RTL 探针与 QEMU/gem5 后端复用同一 case（非必要不为每个平台写三份载体），由 `check-arch-vast` 按需跑三方。

**H/S/U 三模式**（用户 2026-11-22）：cfx0/2 的寄存器面与权限应在 `hmon`/`smon`/`umon` 三种运行模式下各跑一次（复用 `tests/arch/common/env/`）；020 未合入前，U/S 模式若不可用必须显式标注 `modes` 排除原因，合入后补跑。

## 不做

- 不补 U/S 模式进入路由（`monitor` 仍固定 hmon）——留给 `m16-chipyard-020`；
- 不改 `WumingCore` 的异常进入主控制流；
- 不改 QEMU/gem5。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py chipyard` 幂等；
- 重建环境（JDK/conda/`RISCV`）写进证据脚本；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. RTL 探针：cfx0/2 的寄存器读写、保留 rc ⇒ `CFXREG`；Vast 上 `cfx2rd`/`cfx2rc` 不再一律 `CFXREG`；
2. Tiny 的 cfx 序列不变、代表例不回归；cfx3/4/5/63 现有探针不回归；
3. **可达 FAIL**：注入「Vast 去掉 cfx0」⇒ 探针 `CFXREG`、红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`check-index-blobs`、`check-tests-index`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

**测试结果**：运行期证据目录内 `run.sh`（A–G）**PASS=58 / FAIL=0**、rc=0；`run.sh --inject`（H）**PASS=31 / FAIL=0**、rc=0。Vast 探针 **47 条记录 / 376 B** 逐条等于从 `spec/DADAO-12` §2.1/§3.1/§3.3/§3.4/§3.6–§3.8 与 `contract-see` §3/§6.1 现场派生的期望；`--self-test` 47 条记录 mutation + 短/长/非 8 字节流全部被拒。Tiny `11-cfx` 5/5、`01-load-store` 38/38，与 017 的 **pre-019** 基线逐镜像结果字节差 **0**。016 `cfx5_regs` 22 条、017 `cfx5_maint` 29 条记录 + 118 事件在新 Vast 上全绿；cfx4 legacy `vastptw` 仍是 017 记录的同一 TL 断言（KNOWN-RED，基线既有）。
**修改文件**：组件源 4（`generators/dadao-gewu/.../GewuFile.scala`、`generators/dadao-wuming/.../common/{WumingParams,WumingCore}.scala`、`generators/chipyard/.../config/DadaoConfigs.scala`；已收敛 base+1 并重导 4 份补丁，`make_patch.py chipyard` 26 patches / 0 written）；`components/chipyard/{README.md,changelog.md}`；新增 `tests/arch/umon/{cfx02_regs.S,cfx02_regs.lds,check_cfx02_regs.py}`；`tests/arch/{README.md,umon/README.md}`；本任务书。`series` 不变（26 条）；未改 `WumingCore` 的 U/S 路由/异常进入主控制流；未改 QEMU/gem5/spec/契约。
**验收结果**：① 探针记录：cfx0 模式行（cg2 rc0 mask 复位 `0xFF..F7`、cg0 rc4 全 1、cg1 rc8=2、cg2 rc10=0、写 `0x..FF` 读回 `0x..FC`）；四 mask 独立（写 cg0 rc2 后 cg3 rc2 仍复位）；cg3 rc12 复位全 1/写 0 读回 8；cg4 cfx_id=0、三个计数=0、scratch_num=4；cg6 rc0/rc1 写读回；cg8 rc1 复位全 1/写读回；cg7 四字段全 0；cfx2 的 cg3 rc10=`0x0bff_0000_0000`、cfx_id=2、cg0 rc8=2、cg7 块 0=`3/0x3ff_0000_0000/0x10000/7`；5 条保留 rc/写 RO ⇒ `CFXREG`（cause_id=0x4）。② 可达 FAIL：inj1「Vast 去 cfx0」⇒ guest rc=126、0 记录、oracle rc=1；inj2「Vast 去 cfx2」⇒ guest rc=126、0 记录、oracle rc=1；各 `cp`+md5 还原（`5f1be6e2…` 前后相同）并强制重建后回绿（stream 与参考相同）。③ 构建：Vast 全量 **295 s**、Tiny **99 s**，`%Error`=0；注入重建 311/315/336/332 s；Vast sim md5 `22466d7c…`、Tiny `34c26203…`（只作记录，ISS-453）；环境 JDK `20.0.2-internal`、conda gcc `13.2.0`、Verilator `5.020`、`RISCV` 指向组件 `.conda-env/riscv-tools`。④ 门控：`apply_series`/`check-source-state` chipyard clean+base+1；`check-patch-tree` chipyard 段 **0 problem**（全局 rc=2 为他人组件 KNOWN-RED，错误集逐行等于基线）；`make_patch` 幂等 0 written；`check-index-blobs`/`check-tests-index`/`check-tasks` 均 rc=0。
**新发现/坑**：① 公共面读数据不能按「命中公共 cfx」整段覆盖，否则 cfx0/cfx2 的 cg3/cg5/cg7 基行被 0 吃掉（首跑记录 6/7/31–34 全 0）；须按「公共面行命中」选择。② **两轴 `cfxreg` 强制判定不能在本 profile 打开**：chipyard BootROM 链以 `cfx_power`（cfx63）跑测试体，规范复位掩码只允许 `cfx_hmon`（bit3），首跑第一条 cfx0 访问即 `CFXPERM`（`0x8000000080`），且会同样打断既有 cfx4/5 探针 ⇒ 判定留 020（见遗留①）。③ `cg3 rc0–rc3` 原实现四个名字共用一个向量，`cfxreg`（rc2）不是独立掩码；已拆四个寄存器（probe 记录 5–7 为独立性与复位的可达证据）。④ cfx2 的 cg7 声明 64 KiB SRAM 必须有 backing：地址图新增 `kaiwu-vast-smon-sram` 且 `WumingCore.inSpecWindow` 放行，否则描述与访存能力不一致。⑤ 注入「去 cfx2」若返回槽残留前一故障例的回落点，会反复触发 CFXREG 直到 `+max-cycles`（首版 rc=134、2.2M 周期）；cfx2 段前把 `0xF8` 复位为 `abort` 后 fail-fast（rc=126）。⑥ 016/017 的探针可作 019 的独立回归基线，但 Tiny 的「改前」二进制被重建覆盖 ⇒ 用 017 的 pre-019 输出做逐镜像字节对照。⑦ cfx4 legacy `vasttlb.S` 仍用已删除的 `LOAD_ADDR` 宏，无法汇编（018 迁移）；`vastptw` 的 TL 断言是 017 已记录的基线既有。
**遗留问题**：① **CFXPERM 强制判定延后到 `m16-chipyard-020`**：需要 U/S 进入链让测试体在 monitor 内运行，并由环境按 `discussing.md`（`m16-testcases-017`）打开目标 cfx 的 `<mode>_cfx*` 掩码；本轮只落掩码**存储面**（cg0–cg3 四个独立同步 mask、cg3 rc12）与通用 `readOk`/`writeOk` 行判（未实现行/保留 rc ⇒ `CFXREG`）。② **H/S/U 三模式补跑待 020**：本探针只跑 hmon（hypv），smon/umon 的排除原因已显式写入 `tests/arch/umon/README.md`；020 合入后须用 `tests/arch/common/env-{smon,umon}` 补跑。③ cfx1（jmon）仍未实现：`contract-see §3` 的 Vast 约定含 cfx0/1/2/3/63，但 arch 范围与 020 均不含 J ⇒ 待裁定是否另立任务。④ cfx4 的 RTL 探针迁移/`vastptw` 断言归 `m16-chipyard-018`（前置未合入）；本轮只断言失败模式未变。⑤ 探针未登记 `tests/arch.yaml`（chipyard 后端 fail-closed，与 016/017 同口径），登记与否待后端接通后统一处理。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：`GewuFile` 的 `CommonRegs`/`CommonEntry`、公共面读写译码与 rdata 选择、四 mask 拆分、`GewuCfxParams.commonRows` 的展开期门控；`WumingParams` 的 cfx0/2 序列与 smon 地址参数；`WumingCore.inSpecWindow`；`DadaoConfigs` 的 smon SRAM 与参数接线；探针 47 条记录、故障回落槽与 lds ASSERT；checker 的现场解析、range 记录与 self-test；run.sh 的 rc 捕获、注入还原、Tiny 基线对照与 KNOWN-RED 处置。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `io.rdata` 按 `isCommonTarget` 选公共面 ⇒ cfx0/2 的 cg3・cg5・cg7 基行被 0 覆盖（首跑记录 6/7/31–34 全 0） | ✅已修 | 改 `Mux(commonRead, commonRdata, basePtwCache)` | 探针 47/47 PASS、376 B |
| F2 两轴 `cfxreg` 强制判定会让 cfx_power 测试体（复位掩码只允许 hmon）失去 cfx0/2 及既有 cfx4/5 | ⏸延后（依赖 020） | 判定不启用；掩码存储面已落，文档写明由 020 落地 | 首跑日志 `CFXPERM 0x8000000080`；016/017 探针在新 RTL 全绿；登记遗留① |
| F3 cg3 rc0–rc3 四名共用一向量 ⇒ rc2 不是独立 cfxreg 掩码 | ✅已修 | 拆成四个独立寄存器；`maskData`/写路径按 rc 索引 | 记录 5–7 证明写 cg0 rc2 不动 cg3 rc2；Tiny 11-cfx 字节流不变 |
| F4 cfx2 cg7 声明 64 KiB SRAM 但无 backing | ✅已修 | 加 `kaiwu-vast-smon-sram` + `inSpecWindow` 放行 | elab 地址图 `bff00000000 - bff00010000` |
| F5 Vec 动态索引位宽告警（5/4 项 Vec 用 6 位 rc） | ✅已修 | `rc(2,0)`、`log2Ceil(scratchRegs)`；mode 索引钳位 | Vast/Tiny elab `%Error`=0；GewuFile 无 W004 |
| F6 注入「去 cfx2」因 0xF8 残留 f3 回落点而反复触发 CFXREG 至 max-cycles | ✅已修 | cfx2 段前把 0xF8 复位为 abort | inject-run-2 inj2 guest rc=126、0 记录、oracle rc=1 |
| F7 run.sh 用不存在的 `check_patch_tree.py --component` CLI | ✅已修 | 改 Python API 兜底（`check_component`） | A 段 `chipyard-only … rc=0` |
| F8 cfx4 legacy `vasttlb.S` 用已删的 `LOAD_ADDR` 宏；`vastptw` 仍是基线 TL 断言 | ⏸不修（前置 018） | run.sh 只断言 vastptw 失败模式不变，vasttlb 记 KNOWN-GAP | G 段 `same pre-existing TL assertion` PASS |

判决：F1、F3–F7 已修并复验；F2 为 020 依赖的口径/范围外显式登记（不是代码缺陷），F8 为 018 前置。状态 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-23，独立重跑）

**重跑记录**（命令与输出均为我自己的；仓库根执行；B 段强制重建按档位跳过、改采信工程师日志 295 s/99 s 与 `%Error`=0）：

1. `ONLY=A,C,D,E,F,G bash 运行期证据目录内的 run.sh` → **rc=0，`summary: PASS=44 FAIL=0`**：`apply_series` base+1、`check-patch-tree` chipyard 段 **0 problem**、`make_patch` 0 written、源树 clean；探针 `guest rc=0` / `stream 376 B` / `oracle PASS (47 records)`；`--self-test` 47 条 mutation + 短/长/非 8 B 全拒；Tiny `11-cfx` 5/5、`01-load-store` 38/38 对 017 pre-019 基线**字节差 0**；016 `PASS (22 records, 176 B)`、017 `PASS (29 records, 118 cache events)`；`vastptw` 仍是同一条 TL 断言（KNOWN-RED）。
2. `INJ_ONLY=1 bash 运行期证据目录内的 run.sh --inject`（去 cfx0）→ **rc=0，PASS=17/FAIL=0**：注入 applied → 重建 319 s（elab/verilator rc=0、`%Error`=0）→ **红** `inj-inj1: RED guest rc=126 oracle rc=1`、`records: got 0, expected 47`（sim 日志 `SYS_EXIT code=0x7e` = 探针 `abort` 落点，ELF 1163 字回读逐字节一致，非构建失败）→ `cp`+md5 还原 `5f1be6e2…` 前后相同 → 重建 311 s → **回绿** `stream == reference` / `oracle rc=0`；注入后 `make_patch` 0 written、源树 clean。全程无 `git checkout/restore/stash`。
3. 快照对账：注入前后 `git status --porcelain -uall` **逐行相同**；4 份补丁 + 3 个新测试文件 md5 **前后相同**；组件源树 clean、`ffa8dd1 dadao: chipyard patch series`（base+1）。

**实现核验**（读源与补丁）：`WumingCfxHa.umon=0/smon=2` 仅 `useVM` 注入（`grep -c`=1）；cfx2 `spaceDesc=0x3 / spaceSize=smonSize / vectorBase=smonBase` + 地址图 `kaiwu-vast-smon-sram` + `inSpecWindow` 放行；`commonRows` 只给 cfx0/cfx2（`require id ∈ 0..3`），cg0–cg2、cg3 rc12、cg4、cg5 rc5、cg6、cg8 rc1 与 `commonRead/commonWrite` 逐项对齐，cg4 不入 `commonWrite`（写 RO ⇒ CFXREG）、保留 rc 不入读写集；`sourceMask` 拆为每 cfx 4 个独立寄存器，读 `sourceMask(sel)(rcMaskIndex)` 与写路径同索引；cfx3/cfx63 `commonRows=false` ⇒ `commonEntries` 空、`commonRead=false.B`，行集不变。期望值由 checker 现场解析 `DADAO-12` §2.1/§3.1/§3.3/§3.4/§3.7/§3.8 与 `contract-see` §3/§6.1（smon 表行、mask 初值、`bit3 恒 1`、switch 初值 0/2/3、`start = base − (cfxha<<42)`、CFXREG 位号），与实现不共享常量；`.lds` 10 条 ASSERT 有链接期 FAIL 路径。

**遗留 1 判定：延后合理，不阻断 019**。静态复核成立：`maskInitCfx = 0xFFFFFFFFFFFFFFF7`（ADR-0045 D4「只允许 hmon」）；测试体由 `cfx_power` stub 第 8 步 `jump` 到 `0xffffff010100` ⇒ `curCfx = 63`，目标 cfx 的 hypv `cfxreg` 位 63 = 屏蔽；`WumingCore` 现无任何来源掩码判权门（`m16-chipyard-003` 已按「结构性不存在」Accepted）。此刻打开判定 ⇒ 探针首条 cfx0 访问即 `CFXPERM|NCFXPERM = 0x8000000080`（cause `1<<7` + wyde2 `[39]`，与 `GewuCauseId.PERM_NCFXPERM=7` 吻合），并同时打断 016/017 的 cfx5 探针 ⇒ 必须先有 020 的 monitor 内运行与 `m16-testcases-017` 的掩码准备。本任务「验证」§1–§4 不含 CFXPERM，全部达成；存储面（四独立 mask、cg3 rc12）与行判（CFXREG）已落地。

**遗留 2/3/4 核验**：smon/umon 排除原因已显式写入 `tests/arch/umon/README.md`（020 后用 `env-{smon,umon}` 补跑）；cfx1/jmon 按用户口径 J 不纳入（020 §6「J-mode 不测」）⇒ 不另立任务；`vasttlb.S` 仍用已删 `LOAD_ADDR`（我 grep 实证）、`vastptw` 失败模式不变 ⇒ 归 018。

**findings（均不阻断，交 architect 收尾）**：
- **F-A 两轴 `CFXPERM` 判定无承接任务**：遗留①写「延后到 020」，而 020 的「不做」写「不改 cfx0/2 的寄存器行/权限（019）」、其「要做」亦无判权项 ⇒ 互指成空档（chipyard 任务全量 grep 无 RTL 判权承接者）。请 architect 把该项显式写进 020「要做」或另立任务。
- **F-B** 完成区「非 chipyard 错误集**逐行等于基线**」在我重跑时不成立：多出 4 行 qemu 断言（并行 `m16-qemu-005` 在跑，脚本按 ISS-463/507 打 `[KNOWN-RED]` 并贴 diff、**不判红**）；chipyard 段 0 problem 不受影响。该比对无 FAIL 路径，建议改名或补 `bad`。
- **F-C** 遗留③「待裁定是否另立任务」与 020 已记录的用户口径（J 不纳入）不一致；README「cfx3/63 行为不变」宜限定为「行集不变（cg3 四 mask 的存储已按 spec 拆开，无用例观测到差异）」。

**判决：Accepted** —— 我重跑 44 + 17 条断言全绿、注入红与还原回绿实证、快照与产物 md5 对账一致、约束无违反；3 条文档级 finding 交 architect 收尾。B 段重建为采信（未重跑），其余全部亲跑。
