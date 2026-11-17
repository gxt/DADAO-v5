# m14-testcases-006: 固件把全部 cfx 的 supv 权限转交 smon（除 hmon 自身）

**模块**：testcases
**项目里程碑**：M14
**依赖**：无（`tests/shared/bootrom/k0/hmon.S` 现状）
**可并行分片**：否（单一 bootrom 镜像）
**预估**：1–1.5 h
**档位**：小改（固件宏 + 负例 + 门控重跑）
**状态**：待验收

## 背景（用户 2026-11-17 裁定）

> 用户：「hmon 应该把所有 cfx 权限转交给 smon，除了 hmon 自己。」

起因：`m14-linux-016` 的 F5（U-mode 帧往返）卡在测试固件权限——启动 SEE 只给源 cfx 2（smon）放行 `cfx_pmem/ptw/smon/hart/time` 的 `cfxreg` 轴，内核首次 `cfx2rd cfx_umon` 即 `CFXPERM(0x80) info=0x7a000208`。

现状（`tests/shared/bootrom/k0/hmon.S` 的 `OPEN_SUPV_REGS`）：

- 只清目标 cfx 的 `cg2 rc2`（supv `cfxreg` mask）的源位 bit2（smon）与 bit15（hart 约定），并设 `cg3 rc12`（`cg_reg_deleg`）= `0x8`（打开除 cg3 外所有 cg）。
- **没有清** `cg2 rc0`（`cfxtrap`）、`rc1`（`cfxmem`）、`rc3`（`cfxexe`）的 smon 位 ⇒ smon 只能通过 `cfx2rd/cfx2rc` 访问，不能 `trap`/`escape`/`ld/st`/直接跳转进入其它 cfx。

## 目标

1. **新增/改造宏**：对**除 hmon (`cfx3`) 外的全部已定义 cfx**，把 supv 行的四类同步 mask（`cg2 rc0–rc3`）中的**源 smon 位（bit2）清 0**：
   - `cfx_umon(0)`、`cfx_jmon(1)`、`cfx_smon(2)`、`cfx_ptw(4)`、`cfx_cache(5)`、`cfx_hart(15)`、`cfx_pmem(32)`、`cfx_llc(33)`、`cfx_time(34)`、`cfx_uart(62)`、`cfx_power(63)`；
   - **排除 `cfx_hmon(3)`**（hmon 自身不向 smon 开放）；
   - 每个目标 cfx 同时保持现有 `cg3 rc12 = 0x8`（打开除 cg3 外的 cg 访问）。
2. **保留现有特例**：`cfx_pmem` 的 supv `cfxmem` 需要 smon 访问（页表暂存区）——由「rc1 清 bit2」覆盖，无需额外宏；如与既有 `OPEN_SUPV_REGS cfx_pmem` 重复，合并为一条。
3. **负例机制**：沿用现有 `K2_TIME_PERM=0` 的做法，新增一个可汇编的负例开关（例如 `OPEN_SUPV_ALL=0`），使固件**不放行**这些位；用它证明「权限来自固件而不是硬件默认」：不放行时内核首次 `cfx2rd cfx_umon` 必须 `CFXPERM`，放行后成功。
4. **K0 固件镜像变化**：bootrom 镜像会变 ⇒ 记录新 md5；所有依赖 bootrom 的探针/门控（`check-linux-k0/-k1/-k2/-k3`、`check-arch` 中的 bootrom magic/镜像断言）必须重跑并回绿。

## 验收（逐条贴真实 rc）

1. **正向**：内核/探针在 supv 下对 `cfx_umon` 的 `cfx2rd`（cg0/cg5 等）成功；对 `cfx_umon` 的 `trap`/`escape`/`ld/st` 按 `OPEN_SUPV_ALL` 放行后不再 `CFXPERM`（按任务书构造的最小探针，内核侧或固件侧均可）。
2. **负例**：`OPEN_SUPV_ALL=0` 时同一访问 ⇒ `CFXPERM`，且 `cause_info` 为目标地址/指令地址（按 `contract-see §6.1`）；证明权限来自固件。
3. **不开放 hmon**：对 `cfx_hmon` 的 supv 访问仍 `CFXPERM`（至少一条断言）。
4. **镜像与门控**：bootrom 新 md5 记录；`check-linux-k0/-k1/-k2/-k3` 全 rc=0；`check-arch` 中 bootrom 相关断言回绿（若断言写死旧 md5，按 `Process-07 §4a` 改现场派生并说明）。
5. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

1. 独立 `git worktree`（分支 = 任务号）；`git rev-parse --show-toplevel` 自证；禁改主工作树。
2. 只动：`tests/shared/bootrom/k0/hmon.S`（+ 若 bootrom 镜像断言在 `tools/`/`tests/` 需同步则一并，逐条披露）、本任务书。**不动** `spec/`、`contracts/`、`components/`、根 `Makefile`。
3. **不改任何版本号**（版本号升级须用户认可，见 `AGENTS.md`）。
4. 不提交 git；注入还原用 `cp`+md5（禁 `git checkout/restore/stash/show`、禁 `reset --hard`）。
5. 固件是只读基线的一部分：改后必须重建并记录新镜像 md5，门控不得写死旧值。

## 待裁定

（无；用户 2026-11-17 已明确「全部 cfx 转交 smon，除 hmon 自身」）

**reviewer 第 1 轮追加（2026-11-17，转 architect/用户裁定）**：

- **F7 `cause_info` 口径**：`contract-see §6.1`/`DADAO-12 §3.6` 要求 `cfx2rd`/`cfxtrap` 来源掩码拒绝的 `cause_info` = **触发指令地址**（与 `excp_cause_ip` 同值），QEMU 实测给**指令编码**（`0x7a0c508a`），`tests/arch/hmon/expected.yaml` 注释亦写「CFXPERM = instruction word」⇒ 验收 2 的该子句在本机不满足。属 QEMU/跨册实现与合约分歧，硬约束 2 禁改 `components/`，engineer 不可修 ⇒ 建议单立 qemu/spec 任务裁定。
- **F1 清单口径**：按「本机已实现集合」放行（cache/llc/uart 不在列）已由 reviewer 实测佐证（见审阅记录注入 F：加回 `cfx_cache` ⇒ 退出码 `0xB8`），请 architect 确认后在收尾固化。

### 实现期偏差（engineer 披露，待 architect 确认口径）

- **任务书的 11 个目标 cfx 里有 3 个在本机 profile 上不存在**：`spec/Kaiwu §「测试机 cfx 实现范围（按 profile）」` 规定 `Kaiwu-Vast` 只实现 cfx0/1/2/3/63 + cfx4(ptw) + cfx15(hart) + cfx32(pmem) + cfx34(time)，并明写「cfx5（cache）为已分配未实现，访问其寄存器 ⇒ `CFXREG`」（cfx33 llc、cfx62 uart 同理）。实测按任务书清单逐个 `cfx2rd` 会让 hmon 在 `cfx_cache` 上取 `CFXREG`、异常重回 hmon 向量，启动链退化为 `0xB8`（`k0_boot_probe` 101→全红）。
- **临时处置**：只对「本机已实现」的 cfx 清位（umon/jmon/smon/ptw/hart/pmem/time/power，除 hmon），并在 `hmon.S` 注释与 `k0/README.md` 写明理由与扩列指引。这与用户「全部 cfx」的意图一致（未实现的 cfx 没有可开放的 mask 行）。
- **待确认**：若后续某个平台实现 cache/llc/uart，是否需要单独任务把该清单扩成按 profile 派生（或让固件按 cg4 的 `cfx_id` 探测实现范围）。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书清单含 3 个未实现 cfx（见上「实现期偏差」） | ⏸延后（需 architect 确认口径） | 固件只列已实现 cfx，注释 + README 写明 | 按清单版实测 `k0_boot_probe` 全红（`0xB8`）；收窄后 101/101 |
| F2 旧宏只清 `cg2 rc2`，任务要求 rc0–rc3 | ✅已修 | `OPEN_SUPV_REGS` 改为四个 rc 的读-改-写，源位仍 `{2,15}` | 镜像 dump：8 个目标 supv 四 mask = `…7ff3`；`cfx_hmon` 保持 `…fff7` |
| F3 `cfx_pmem` 的 supv cfxmem 特例与旧独立块重复 | ✅已修 | 删掉独立块，由宏的 `rc1` 覆盖 | K1/K2/K3 门控里 smon 的 DMA 页表暂存全绿（119/112/170/263） |
| F4 负例开关必须仍让启动链走到内核 | ✅已修 | `OPEN_SUPV_ALL=0` 只关「新增目标」，pmem/ptw/smon 常开 | 负例镜像内核实跑：首个 `cfx2rd cfx_umon` ⇒ `CFXPERM`，链路未断 |
| F5 「不开放 hmon」需独立断言 | ✅已修 | 证据探针 case 4 在正/负两个镜像各断言一次 | `cfx2rd cfx_hmon` ⇒ `CFXPERM`+`NCFXPERM`，`ip` 落该指令 |
| F6 证据脚本被 kill 会留在注入态 | ✅已修 | `run.sh` 加 `trap … INT TERM HUP EXIT` + `cp` 还原；QEMU 加 `RLIMIT_FSIZE` 防日志打满 tmpfs | 实测被 `timeout` 杀掉后仍 `cp` 还原到基线 md5 |
| F7 `cause_info` 疑与契约不符（cfx2rd 拒绝） | ⏸延后（非本任务范围） | 探针按**实测**断言「info = 触发指令编码」，并在断言名里点名 deviation | 实测 `info=0x7a0c508a`（= `cfx2rd cfx_hmon` 编码），`ip=0x20000100048`；`contract-see §6.1`/`DADAO-12 §4.1` 要求 = 触发指令地址 |

### 第 1 轮 reviewer 验收（2026-11-17；中改档，≥2 路注入）

**自证/快照**：`git rev-parse --show-toplevel` = `/tmp/opencode/m15-testcases-011/wt`，分支 `m14-testcases-006`，HEAD `067e46e4`；验收前后 `git status --porcelain -uall` **均空**，三文件 md5 前后一致（`hmon.S` = `02e68edee832c6daf4979dd41be8ebd1`），前后快照逐行对账通过。

**重跑记录（我自己的输出/rc）**

1. 证据脚本 `./.work/evidence/m14-testcases-006/run.sh` ⇒ **rc=1**（`EVIDENCE: FAIL (1 failed)`）：baseline 40/40 PASS、注入 A/B/C 均「注入→指定 case 转红→`cp` 还原→md5 一致」；但 [5/6] `git diff confined…` **FAIL** —— HEAD 已含改动，裸 `git diff --name-only` 为空 ⇒ 空行判不通过。完成区「40/40 PASS」在 HEAD **不可复现** ⇒ 阻断（AGENTS「提交后仍须回绿、禁裸 `git diff`」）。
2. `make check-linux-k0/-k1/-k2/-k3` ⇒ **rc=0/0/0/0**，`119/119`、`112/112`、`170/170`、`263/263`（17/22/75/51 s）；`check-arch` 后复跑 k0 仍 rc=0 / 119。
3. `make build-bootrom` **rc=0**；`tiny/bootrom_tiny.bin` md5 `514300876ea66ec108396334f3ef2b0f` == `tests/arch/hmon/expected.yaml::shared_bootrom_md5`；`grep -rn 'b662183a\|3c178b55' tools/ tests/ contracts/ Makefile` **空**（门控无写死）；probe 现场重建镜像 md5 = `b662183a…`(pos) / `3c178b55…`(neg)，与完成区逐字一致。
4. **`make check-arch` ⇒ EXIT=0（82 s）**：安静窗口存在（`ps` 无 make/qemu、load 0.32、llvm/qemu 源树 `git status` 空）⇒ `install-host: PASS` + `build-bootrom: PASS` + `check-arch-smoke: PASS` + 15 个 min-ROM 探针全 PASS ⇒ engineer 的 BLOCKED **已解除**。
5. 正/负例现场：`umon_cfx2rd/pos exit=0x00`、`/neg exit=0x80 perm_sub=0x80 ip=0x20000100048`；`hmon_cfx2rd/pos|neg 均 exit=0x80 perm_sub=0x80 info=0x7a0c508a`；`umon_roundtrip/pos exit=0x42`（`rd31=0x5a5a5a5a`）；`power_ld/neg info=0xffffffc00000 ≠ ip`。

**独立注入（3 路，均非 run.sh 的 A/B/C；`cp`+md5 还原，后置 `git status` 空）**

- **D** 掩码改 `0x7fff`（不清 bit2）⇒ `umon_cfx2rd/pos` 转红（exit `0xE1`）；**E** `OPEN_SUPV_ALL=0` 下强开 `cfx_umon` ⇒ `umon_cfx2rd/neg` 5 条断言全红（128→0）⇒ 负例可达、非恒真；**F** 把未实现 `cfx_cache` 加回清单 ⇒ 退出码 **184 = `0xB8`**，与 F1 披露一致 ⇒ **收窄实证**。三次均 `RESTORE_OK=yes`。

**约束核验**

- 改动范围：`git diff --name-only <merge-base>..HEAD` = `hmon.S`、`k0/README.md`、两本任务书（改名提交）；未动 `spec/`、`contracts/`、`components/`、根 `Makefile`，无版本号变更，未提交 git ✓。
- **收窄成立**：`spec/Kaiwu §3`（Vast 实现 0/1/2/3/63+4+32；`cfx5` 已分配未实现 ⇒ `CFXREG`；保留集 6–14/16–31/35–61 见 `DADAO-12 §1`，故 5/33/62 属「已分配未实现」）+ QEMU `cpu.h:279-283`（实现集另含 cfx15/cfx34）+ 注入 F 实测 `0xB8` + `check-arch integ049t [PASS] cfx5 … CFXREG`。
- **四轴/清单**：我独立 `llvm-mc`+`llvm-objdump` 反汇编 ⇒ 8 目标（umon/jmon/smon/ptw/hart/pmem/time/power）各 **4 条 `cg2 rc0–rc3` 写 + 掩码 `0xffff_ffff_ffff_7ffb`（= `~((1<<2)|(1<<15))`，wyde0=LSB）+ `cg3 rc12=0x8`**；**无** `cfx_hmon/cache/llc/uart` 展开；`cfx_hmon` 正/负例均 `CFXPERM+NCFXPERM`，注入 B 使其转红。

**判决：Needs Revision** —— 唯一阻断 = 证据脚本提交后不回绿。**修改建议**：`run.sh` [5/6] 改为基线锚定（`git diff --name-only $BASE..HEAD` ∪ 工作树 diff，或 `git show --name-only --stat HEAD`），保留「只限 hmon.S / README / 本任务书」判据；修后复跑期望 **rc=0、断言 40**，完成区「40/40 PASS」即可复现。

**待裁定**：见上「待裁定 → reviewer 第 1 轮追加」（F7 `cause_info` 口径；F1 清单口径确认）。**非阻断 finding**：a) `k0/README.md` 不在硬约束 2 白名单内（已披露，收尾请确认口径）；b) `cfxexe` 轴无运行期专属断言（宏与反汇编已覆盖，trap/ld/cfx2rd 三轴有实测）；c) `hmon.S` 注释把 cfx15/cfx34 出处写作「cfx 实现范围」节，该节 Vast 条目只明列 0/1/2/3/63+4+32 与 cfx5 未实现（结论正确、出处略宽）。

### 第 2 轮 engineer 返工（回应 reviewer Needs Revision，2026-11-17）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1（阻断）`run.sh` [5/6] 裸 `git diff --name-only`：HEAD 已含改动 ⇒ 提交后恒红 | ✅已修 | 改为基线锚定：`BASE=$(git merge-base master HEAD)`（缺省 `c632031a`，可用 env `BASE=` 覆盖），`git -C… -c core.quotepath=false diff --name-only "$BASE"` 一次覆盖「已提交 + 工作树」；白名单保留 `k0/hmon.S`/`k0/README.md`/本任务书，并补入改名前的 `m15-testcases-011-*.md`（改名提交删除项）；新增「非空（≥3 路径）」断言堵住「空 diff ⇒ 假绿」 | `run.sh` ⇒ **rc=0、`EVIDENCE: PASS (0 failed)`**、probe 断言 **40/40**，[5/6] 两条均 PASS（`base=c632031a…`）。**可达 FAIL 复验**：把 `k0/smon.S` 追加一行注释（集合外改动）⇒ 该断言 `want=true got=false` rc=1、`EVIDENCE: FAIL (1 failed)`；`cp` 还原后 md5 回 `5126d83a…`、工作树仅剩两个声明文件 |
| R2（非阻断）`k0/README.md` 不在硬约束 2 白名单 | ✅已确认 | 不改代码；architect 已认可该同步说明（放行集合 + 两个负例开关）属必要文档 | 范围断言的实际输出：4 个路径 = 两本任务书（改名）+ `hmon.S` + `k0/README.md` |
| R3（非阻断）`cfxexe` 轴无运行期专属断言 | ⏸延后（已知限制，登记） | 不改代码：cfxexe 的位由宏统一清（与 cfxtrap/cfxmem/cfxreg 同一段代码），cfx_umon 无 cfx 地址空间（`cfxha 0` = 内存窗口，`spec/Kaiwu §1.2`）故无法用 `ld`/取指构造，强行取指只会得到同一权限检查的下游效应 | 反汇编 8 目标各 4 条 `cg2 rc0–rc3` 写；运行期 trap/ld/cfx2rd 三轴实测（见第 1 轮 reviewer 注入 A/B/C/D/E/F） |
| R4（非阻断）`hmon.S` 注释出处「cfx 实现范围」略宽 | ✅已修 | 注释改准：Vast 集合以 `spec/Kaiwu §「测试机 cfx 实现范围（按 profile）」` 为据（cfx0/1/2/3/63 + cfx4 ptw + cfx32 pmem；cfx5 已分配未实现 ⇒ `CFXREG`）；`cfx15`/`cfx34` 另引 `spec/DADAO-12 §4.7`/`§4.10`；`cfx33`/`cfx62` 属 `cfx32`–`cfx63` per-system 段（`§1`）但本机未实现 | 仅注释改动：重建镜像 md5 仍 `b662183a…`（未变） |
| R5 `check-arch` BLOCKED 解除 | ✅已记录 | 不跑（reviewer 已整跑）；完成区 4 改为引用 reviewer 的 `make check-arch` **EXIT=0（82 s）** | reviewer 第 1 轮验收第 4 条 |
| R6 F7（QEMU `cause_info` 偏离契约） | ✅已转登记 | 主会话已登记 `ISS-469`；探针仍按实测断言并在断言名点名 deviation | 完成区「遗留问题」 |

**返工后复跑（本次输出/rc）**：`./.work/evidence/m14-testcases-006/run.sh` ⇒ rc=0、`EVIDENCE: PASS (0 failed)`、40/40；`make check-linux-k0` ⇒ rc=0、**119/119**（12.6 s）；`build-bootrom`/tiny md5/`min_rom_probe_046t` 未变（本轮只改注释与证据脚本）。

### 第 2 轮 reviewer 验收（R1 返工复验，2026-11-17；小改复核档）

**自证/快照**：分支 `m14-testcases-006`，HEAD `25effe78`（上轮 `067e46e4`）；验收期间 `git status --porcelain -uall` **空**，`hmon.S` md5 `a17278ec8b5a3b6b8aa1ea65b127ea23`（本轮仅注释改动，`git diff 067e46e4..HEAD -- hmon.S` 已核为纯注释）。

1. **`run.sh` 在 HEAD 态复跑 ⇒ rc=0**：`EVIDENCE: PASS (0 failed)`、baseline **40 断言**（现场计数）；`base=c632031a…`（`git merge-base master HEAD`）、`git -C… -c core.quotepath=false diff --name-only "$BASE"` 覆盖已提交+工作树；`changes confined… want=true got=true rc=0`、`not vacuous (>=3 changed paths) PASS`、`final assertion count 40==40`。白名单 4 模式（`k0/hmon.S`、`k0/README.md`、`m14-testcases-006-*.md`、`m14…m15-testcases-011-*.md`）核对无误。
2. **可达 FAIL（我独立注入，非 engineer 自检）**：给白名单外 `m14-testcases-005-arch-TLB探针.md` 追加一行 ⇒ `changes confined… want=true got=false rc=1`、`EVIDENCE: FAIL (1 failed)`、`RUNSH_INJECT_EXIT=1`；`cp` 还原 md5 `8c3396e0… → e7088973…` 相等、`git status` 空；再复跑 ⇒ **回绿 rc=0**。
3. **非回归**：`make check-linux-k0` ⇒ **rc=0、119/119**（12.4 s）；probe 现场镜像 `b662183a70586e2f463f0811a04a6e0e`(pos) / `3c178b55…`(neg) 与上轮一致。
4. **披露核对**：完成区第 4 条已写入 `make check-arch` **EXIT=0（82 s）**（原 BLOCKED 撤销）；F7 ⇒ **ISS-469** 已在主工作树 `.tao/knowledge/issues.yaml` 登记（scope=qemu，title 与 F7 逐字对应）；3 条非阻断 finding 逐条处置（R2 `k0/README.md` architect 已认可、R3 `cfxexe` 登记为已知限制、R4 注释出处已改准），完成区「遗留问题」四条齐全。

**判决：Accepted** —— 上轮唯一阻断（证据脚本裸 `git diff` 提交后假 FAIL）已消除，重跑/反例注入/还原/回绿证据齐备；改动范围仍限 `hmon.S`+`k0/README.md`+两本任务书，未提交 git、未动 spec/contracts/components/根 Makefile。

## 完成区

**测试结果**：证据脚本在 HEAD 状态下 **rc=0、40/40 PASS**（基线锚定后提交/未提交都可复现）+ 3 路注入全红后回绿；L2 门控 `check-linux-k0` 119/119（返工后复跑）、`-k1` 112/112、`-k2` 170/170、`-k3` 263/263 全 rc=0。
**修改文件**：`tests/shared/bootrom/k0/hmon.S`（宏改四轴 + `OPEN_SUPV_ALL` 负例开关 + 目标清单）、`tests/shared/bootrom/k0/README.md`（同步说明，逐条披露越界）、本任务书。
**验收结果**：
1. 正向：supv（cfx_smon）对 8 个已实现 cfx 的 `cfx2rd cg5 rc2` 全部成功；`trap cfx_umon → 向量 → escape cfx_umon` 往返完成（退出码 `0x42`，向量桩 `rd31=0x5a5a5a5a`）；`ld` 经 cfx_power 段读回 BootROM 头字 = 镜像头 8 字节（现场从新镜像读）。
2. 负例（`OPEN_SUPV_ALL=0`）：同一 `cfx2rd cfx_umon` ⇒ `CFXPERM(0x80)` + `NCFXPERM([39])`，`ip` 落在该指令；`trap cfx_umon` ⇒ 同；`ld` BootROM ⇒ 同且 `info` = 被访问地址（≠ `ip`）。放行版同一 `trap` 则转移后按 `CFXMEM` 收场（不再 `CFXPERM`）。
3. 不开放 hmon：正/负两个镜像均断言 `cfx2rd cfx_hmon` ⇒ `CFXPERM` + `NCFXPERM`。
4. 镜像：新生产镜像 md5 `b662183a70586e2f463f0811a04a6e0e`（负例变体 `3c178b5570bcd6d133a6a61724f836bb`，此后仅注释级改动、镜像 md5 未变）；`check-linux-*` 无写死 bootrom md5。`make build-bootrom` rc=0；tiny 镜像 md5 仍 == `tests/arch/hmon/expected.yaml::shared_bootrom_md5`（`514300876e…`）；`min_rom_probe_046t` `RESULT: PASS`；**`make check-arch` 由 reviewer 整跑 ⇒ EXIT=0（82 s）**，含 `install-host` + `build-bootrom` + `check-arch-smoke` + 15 个 min-ROM 探针全 PASS（原 BLOCKED 解除）。
5. 门控环境说明：k0/k1/k2/k3 在本任务**私有 linux 源/构建树**上跑（共享 `.work/source/linux` 被在途任务的新补丁集占据，`apply-series` 判「HEAD 既非 base 也非 base+1」⇒ K12 红；非本任务改动所致）。共享构建树 `.config` 已按快照还原（md5 `0c350eaa…`）。复查可直接复用本 worktree 的 `.work`（`source/linux`、`build/linux` 为私有，其余组件与 `log`/`evidence` 指向共享树）；门控期间镜像 md5 与最终一致（`b662183a…`，此后仅注释级源码改动）。
**新发现/坑**：①`Kaiwu-Vast` 未实现 cfx_cache/llc/uart（写其 mask 必 `CFXREG`），固件只能按已实现集合放行；②QEMU 对 `cfx2rd`/`cfxtrap` 掩码拒绝给 `cause_info` = **指令编码**，而 `contract-see §6.1`/`DADAO-12 §4.1` 要求 = 触发指令地址（与 `excp_cause_ip` 同值）；③`set.zw` 会把其余 48 位清零，`LD64` 的「全 f 高位」靠后续 `or.w` 补齐，改宏时勿省略；④`escape` 偏移只允许 `{0,4}`（汇编器校验，QEMU 另按 `imm<<2` 落盘），探针需以 `+4` 返回；⑤`-d cpu` 日志可把 tmpfs 打满（实测 12 GB/min），QEMU 侧须设 `RLIMIT_FSIZE`。
**遗留问题**：①F1（未实现 cfx 的清单口径）待 architect 确认；②F7（`CFXPERM` 的 `cause_info` 与契约不符）主会话已登记 **ISS-469**（QEMU 侧）；③`k0/README.md` 越界已由 architect 认可（同步说明属必要文档）；④`cfxexe` 轴仅由「宏统一清位 + 反汇编」覆盖，无运行期专属断言（`cfx_umon` 无 cfx 地址空间，`cfxha 0` = 内存窗口）——登记为已知限制。证据脚本与日志：运行期证据目录 `run.sh`（40 断言 + 3 路注入）、门控日志 `check-k0-priv.log`/`check-k0-round2.log` 等。

