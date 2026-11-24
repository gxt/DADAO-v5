# m16-chipyard-027: RTL 缺面补齐（power common face + cfx5 S/U 可达）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-testcases-009` 复核结论（`DIV-16` 是否成立）；`m16-chipyard-023` 已合入
**可并行分片**：否（同改 `components/chipyard`）
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

- `ISS-524`：RTL 的 `cfx_power` 未开 common face（`cg4`/`cg6` 读出 `CFXREG`），而 `DADAO-12 §3.5/§3.7` 要求每个非 reserved cfx 都实现（QEMU/gem5 合规范）。
- `DIV-16`（`m16-testcases-009` 登记，待复核确认）：RTL 的 `cfx5` 只有 `cg8` 面，`cg0–cg3`（含 `user/supv_cfxreg`、`cg3 rc12`）不存在 ⇒ cfx5 的 S/U 访问在 RTL 不可达，`rtl-coverage.yaml` 记四条 mode gap。

## 要做

1. **`cfx_power` common face**：按 `commonRows` 打开 `cg4`（计数）与 `cg6`（scratch，≥2 个）；`cfx_id = 63`；不改变 `cg7`（BootROM 空间描述）与 `cg8 rc1`（power ctrl）语义。
2. **`cfx5` 的模式面**：按 `§3.1–§3.4` 给 cfx5 打开 `cg0–cg3`（至少 `user/supv_cfxreg` 与 `cg3 rc12`），使其 S/U 访问可达；**不放宽** `cfx5` 的维护命令语义。顺带修 **ISS-534**：维护端口把 `cache_addr_start` 截到 48 位（`CACHE-18` 要求 56 位不截断），补一条 ≥48 位向量。
3. **探针**：
   - `tests/arch/power/` 的 `arch-power-001` 把 `cg4/cg6` 纳入比较面（删 `DIV-13`）；
   - `tests/arch/cache/` 的 `arch-cache-001/002` 加 smon/umon 的 RTL 承载（删/收窄 `DIV-16` 的 mode gap）。
4. **不回归**：Tiny 无 cfx5/cfx_power 的 common face 变化；cfx0/2 两轴判权、cfx15/32/34、cfx5 的 H 模式用例、Tiny `11-cfx`/`01-load-store`。

## 不做

- 不改 `cfx_power_ctrl` 写侧（ISS-525，另立 qemu/gem5/RTL 分件）；
- 不改 QEMU/gem5/spec；
- 不支持多 hart。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `cfx_power` 的 `cg4`/`cg6` 读写符合 `§3.5/§3.7`（`cfx_id=63`、scratch 可读写），`arch-power-001` 槽位全绿、`DIV-13` 删除；
2. `cfx5` 的 `cg0–cg3` 在 S/U 可达（`arch-cache-001/002` 的 smon/umon RTL 段跑通），`DIV-16` 收窄或删除；
3. **可达 FAIL ≥2**：注入"关掉 power common face"、"关掉 cfx5 的 supv 行" ⇒ 红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、index-blobs/tests-index/tasks/component-changelog/no-residue、`run_arch.py --self-test` 记录 rc。

## 完成区

**测试结果**：通过 61/61（`run.sh --base` 48 + `run.sh --inject` 13）；失败原因：无。关键面：`arch-power-001` QEMU/gem5 三模式 + RTL 35 槽全绿（含 cg4/cg6）；`arch-cache-001/002` hmon/smon/umon 六个 RTL 运行全绿（`DIV-16` 四条 gap 已删）；`cfx5_maint` 31 记录/121 缓存事件全绿（含新增 56 位 `addr_start` 向量）；`cfx5_regs` 22 记录、time/hart/pmem/ptw 回归全绿；Tiny `01-load-store` 38/38、`11-cfx` 基线 4/5（DIV-11）。
**修改文件**：`components/chipyard/{README.md,changelog.md}`；补丁 `patches/generators/dadao-gewu/.../GewuFile.scala.patch`、`patches/generators/dadao-wuming/.../{WumingParams,WumingCache}.scala.patch`；`tests/arch/{README.md,expected-divergences.yaml}`；`tests/arch/power/{power_vast.py,expected.yaml}`；`tests/arch/cache/{README.md,cache_rtl.S,check_cache_rtl.py,rtl-coverage.yaml,cfx5_maint.S,check_cfx5_maint.py,gen_cfx5_maint_tables.py}`。
**验收结果**：`check-patch-tree` chipyard 段 0 problem（全局 rc=1 仅 linux/musl 既有红）；`make_patch chipyard` 0 written、补丁集 md5 前后相同；`check-index-blobs`/`check-tests-index`/`check-component-changelog`/`check-no-residue`/`run_arch --self-test` rc=0。注入：关 power+cfx5 common face ⇒ power rc=1（guest 126）、cache smon rc=1；tag 截回 48 位 ⇒ cfx5_maint rc=1 且日志断言命中；均 `cp`+md5 还原并强制重建后回绿（Vast 重建 287/304/293/296 s、Tiny 72 s；sim md5 基线 `ed4be537…`、末版 `8b3f221d…`、Tiny `65ca3a5a…`，ISS-453 行为为准）。
**新发现/坑**：① 从 hypv 降模式只能用目标 cfx 的 hypv 行 `cg3 rc8`，而 hmon 无 `commonRows`（该行是常量 3）⇒ 首版 S/U 卡在 hypv；改为经 cfx_smon/umon 降模式后，两轴源位分别是 2/0，掩码只清对应位。② 手工编辑 new-file 补丁后必须同步 `@@ +1,N` 与 index blob，否则 `git apply` 截掉文件尾、sbt 报 eof。③ `run_inst_tiny` 需在仓库根运行才能解析 `tests/inst` 的 include。④ 同源重建 Vast md5 会变（`ed4be537…`/`8b3f221d…`），按行为判。
**遗留问题**：`cfx_power cg4 rc1 version` 为 HW 值、spec/合约不规定 ⇒ 不入逐槽；Tiny 的 `cfxreg/cfxtrap_deny_cfxperm` 两载体因 Tiny 无来源掩码结构性红（非本任务回归面）；全局 `check-patch-tree` 的 linux/musl 红为已知基线。


## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 降模式用了 hmon `cg2/cg0` 行，但 hmon 无 `commonRows`、`cg3 rc8` 为常量 ⇒ S/U 实际停在 hypv | ✅已修 | `cache_rtl.S` 改为目标 cfx_smon/umon 的 `cg3 rc10/cg8`；cfx5 掩码按源位 2/0 清 | `check_cache_rtl 001/002 × hmon/smon/umon` 6/6 PASS |
| 新日志断言无自检变异，不能证明可失败 | ✅已修 | `check_cfx5_maint.py` 增「日志按低 48 位别名」变异 | `--self-test` 报 `56-bit addr_start logged truncated rejected` |
| 手工编辑 new-file 补丁后 hunk 计数/index 过期 | ✅已修 | 修正 3 份补丁 `@@ +1,N` 与 index blob | `apply-series` 成功、`check-index-blobs` rc=0、sbt 编译通过 |
| Tiny 测例从证据目录启动，找不到 `tests/inst` 相对 include | ✅已修 | 证据脚本在仓库根子 shell 内跑 `run_inst_tiny.py` | `01-load-store 38/38`、`11-cfx` 4/5 |
| 证据脚本注入后重建 md5 与基线不同，需确认是重建非确定性而非源码未还原 | ✅已验 | 还原后逐文件 md5 与备份相同、`git status` 干净 | 注入日志 `restore md5` PASS；两次重建行为全绿 |

**判决**：所有 finding 已修/已验，可进入 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-25，全部自跑，未采信完成区）

**重跑记录**
- 运行期证据目录内的 `run.sh --base`：**48/48 PASS、EXIT=0**；`run.sh --inject`：**13/13 PASS、EXIT=0**。注入 A：power rc=1（guest 126、签名 0≠280）+ cache smon 红；注入 B：`cfx5_maint` 红（record21 别名行被删 0x…602≠0x…601 + 56 位截断断言命中）；`cp`+md5 还原（`a505a0bb…`/`fdcd744c…`，与开审快照一致）→ 强制重建 → 回绿（35 槽 / 31 记录 121 事件）。
- 环境干扰与绕行：验收窗口内共享组件源树被并发的 m17-chipyard-001 会话自 04:27 起重建占用（其后又覆盖共享 Tiny/Vast 仿真器）。按「优先在临时树注入」，注入与独立 `check-patch-tree` 在**同脚本的隔离副本树**执行；base 的 Tiny 四项因二进制被换，已在本任务源 Tiny 上复验：`01-load-store` 38/38（rc=0）、`11-cfx` 4/5（rc=1，DIV-11）。base 其余 44 项均跑在本任务源 Vast 仿真器上（结束 md5 与完成区一致）。
- `check-patch-tree`（隔离副本自跑）：chipyard 段 **0 assertion**；全局 rc=1、仅 linux/musl **26 行**，与 run.sh 窗口内跑、我另一次跑**逐行相同**。`make_patch chipyard` rc=0 且补丁集 md5 前后相同；index-blobs/tests-index/component-changelog/no-residue/`run_arch --self-test` rc=0；`check-tasks` rc=0（报告型）；`check_cache_rtl`/`check_power_rtl --selfcheck`、`check_cfx5_maint --self-test`（56 位日志变异被拒）均 PASS。隔离副本同源重建的 Vast md5 与原证据不同，属同源重建非确定性，按行为判（全绿）。

**实现核验**：① power：`commonRows = p.useVM`（Vast 开、Tiny 不开），cg4 rc0=`cfx_id`63、四计数 0、cg6 rc0/rc1 RW 哨兵入 35 槽（三方三模式全绿）；cg7/cg8 rc1 路径未动（diff 仅 require 允许清单 + 两处 `commonRows`）。② cfx5：`commonRows = true` 且在 useVM 块内；两轴判权/复位掩码**零改动**，探针在 hypv 只清目标源位（smon/umon=2/0）+ deleg 0x8，与 env 授权同类；`mode_problem` 断言进入目标模式后不得回退。③ 56 位：`tagBits/tagOf/lineBaseOf = PA[55:0]`，`reqAddr` 64 位容器、索引位（低 index+offset）不变 ⇒ VIPT 索引与既有别名行为不变（48 位总线高位恒 0，命中判定等价）；范围比较/日志用 56 位重建 PA；`PA_HIGH` 向量真断言「寄存器读回 + 别名行未被删」。

**DIV/覆盖**：DIV-13、DIV-16 已从 `expected-divergences.yaml` 删除（grep 无）；DIV-07、DIV-09（已收窄）、DIV-11、DIV-14 仍在；`rtl-coverage.yaml` 仅剩 `arch-cache-004` off gap；`cfx5_maint` 31 记录/121 事件、`cfx5_regs` 22 记录回归绿。

**遗留判定**：① `cg4 rc1 version` 不入逐槽——合理（`§3.5` 为 HW、合约未定值，`--diagnose` 仍报）；② 两 deny 载体红为 m17-idl-020 登记的 DIV-07（chipyard-only），本任务 diff 不含 Tiny 掩码路径，与本任务无关；③ 全局 linux/musl 红与基线逐行相同。

**finding（文档级，不阻断）**：`cache_rtl.S` 顶部注释与 `tests/arch/cache/README.md` 仍写「经 cfx_hmon 降模式、只清 hmon 位、`inner_cfx_code` 保持 hmon」，与实际代码（`trap cfx_smon/umon`、清源位 2/0）及完成区新发现①不符——请 architect 收尾订正。
**给架构师**：m17-chipyard-001 在本任务待验收期间并发写共享组件源树（同组件任务应串行），本验收已绕开，供裁定。
**快照对账**：开审/收尾 `git status` 快照逐行相同（17 个修改文件），6 个关键交付物 md5 与开审一致；未提交 git。

**判决：Accepted**（验收命令块在本人重跑下全过，硬约束逐条守住）。