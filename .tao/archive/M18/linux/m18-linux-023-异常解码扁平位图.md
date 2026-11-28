# m18-linux-023: Linux 侧异常解码适配扁平位图

**模块**：linux
**项目里程碑**：M18
**依赖**：`m17-spec-002`（扁平位图正文）、`m17-qemu-001`（已验证）、`m18-linux-022`（已验证，`beb70bb9`）。
**依赖口径（用户 2026-11-25 裁定）**：本任务**运行在 QEMU 上，不依赖 chipyard**——验证判据 = `check-linux-k1`/`k2`/`k5`/`k6` 在 QEMU 上真绿；`m17-chipyard-001`（Vast RTL）与本任务**无关**（Vast 三方对照属 chipyard 侧任务），不得作为前置或验收项。
**为什么放宽**：安装根 qemu 已是扁平位图模型（`7148dbca`），内核 105 补丁仍按旧「大类+子原因」解码 ⇒ 任何 PTW 故障都判 `unknown cause=0x10000000000000`（bit 52），导致 K1 61/109、K2 47/89、K5/K6 亦红，`m18-linux-006/015/016/017` 全线无法验证。
**可并行分片**：否
**预估**：4–8 h
**档位**：中改（复核 ≤40 min）
**状态**：已验证

## 背景

扁平位图后，Vast 的 PTW 权限/访存故障不再带 `CFXPERM`/`CFXMEM`（父 cause=0），改由高位位图 `[32..38]`/`[48..56]` 表示。Linux `arch/dadao` 的缺页/权限处理目前按 `CFXMEM`/`CFXPERM` 解码，必须同步，否则内核把页错误当「未知异常」。

## 要做

1. `arch/dadao/mm/fault.c`、`traps.c`（或等价入口）按 ADR 的位图解码：识别 `[32..38]`/`[48..56]` 为页错误，并映射到 `vm_fault` 的 `FAULT_FLAG_*`；
2. `cause_info` 语义按 ADR（PTW 故障 = 访问 VA；ADWBFAIL = PTE PA）；
3. 保留非 PTW 的 `CFXMEM`（cfx 空间非法访问等）与 cfx 掩码 `CFXPERM` 的既有处理；
4. 补 K2/K5 相关探针或单测（至少一例页权限、一例页缺失走新解码）；
5. 不改 spec/契约与其它组件。

## 不做

- 不改 QEMU/gem5/chipyard/IDL；不改 M14 之外的架构；
- 不定义 monitor 路由（由硬件/ADR 决定）。

## 约束

- 独立 `git worktree`；组件补丁按 `docs/Process-01`；不提交 git；
- 只动 `components/linux/patches/arch/dadao/**`、`components/linux/{README.md,changelog.md}`、必要测试、本任务书；完成区 ≤30 行。

## 跨里程碑依赖与冲突（2026-11-24 核对）

- **同组件串行**：`m18-linux-022`（内核异步新模型，待开始）与 `m18-linux-006`（LTP 子集，进行中）同改 `arch/dadao`；本任务须与之串行并 rebase。
- **门控期望**：K2/K5/K6（`check-linux-k2/k5/k6`）的故障码/退出码期望按扁平模型更新；`m18-linux-015..018` 的 KERNEL_BUG/SUITE_ENV 用例可能受异常解码变化影响。
- **组件**：属 `components/linux` 补丁流程；与 QEMU/gem5/chipyard 的 Vast 侧先落地顺序为「平台 → Linux」。

## 验证

1. 页权限/页缺失各一例：内核按新位图识别并正确处理（guest rc=0）；
2. 非 PTW 的 `CFXMEM` 与 cfx 掩码 `CFXPERM` 不回归；
3. **可达 FAIL ≥2 路**：把位图判断改回只认 `CFXPERM`/`CFXMEM` ⇒ 探针红；`cause_info` 单位错 ⇒ 红；`cp`+md5 还原回绿；
4. `check-patch-tree` linux 段 0 problem；K2/K5 门控 rc=0。

## 待裁定/阻塞

- Vast 路由/退出码未定时，先按「硬件把页错误交给当前 monitor」的既有路径接入，具体向量待 ADR；
- 版本号不变。

## 完成区

**测试结果**：`make check-linux-k1` → `check-linux-k1: PASS (113/113)` rc=0（基线 61/109）；`make check-linux-k2` → `PASS (170/170)` rc=0（内含 K0 回归 146/146；基线 47/89）；`make check-linux-k5` → `check_k5: 285/285 passed` rc=0（含新增 G 组位图断言；7 次复跑 6 次 285/285，唯一一次红 = 024 窗口 + F7 顺序）；`make check-linux-k6` → `check_k6: 82/82 passed` rc=0（该门控**不在**本任务验收面；5 次中 1 次 82/82，另 1 次仅 E 组判据误红已修，3 次为 `m18-linux-024` 窗口，见遗留①）。`check-patch-tree` **linux 段 0 problem**（105 补丁，计数自 `series` 现场派生）；`check-config-pins` rc=0（93 项）；`check-component-changelog` rc=0；`check-knowledge-refs` rc=2 = **base 差异**（本 worktree 的 base 早于 `m17-spec-004` 合入，唯一悬空 = 其 `ADR-0063`；同命令在 master 上 rc=0）。

**修改文件**：9 份补丁重导出（`arch/dadao/include/asm/{cause-sub,trap,pgtable}.h`、`kernel/{traps.c,k2_selftest.c,process.c,k4_switch_selftest.c}`、`mm/{fault.c,k1_pt.c}`；linux 源树折进 `base+1` 单提交后重导，series 仍 105）；`components/linux/changelog.md`；8 个门控/探针（`tests/unit/linux/{check_k1,check_k2,check_k5,check_k6,k1_pt_probe,k2_trap_probe,k4_cow_probe,k4_stack_probe}.py`）；本任务书。**未动** `spec/`、契约、`Makefile`、QEMU/gem5/chipyard/IDL 补丁、`tests/arch/**`、`expected-divergences.yaml`。

**验收结果**：运行期证据目录 `run.sh`（默认面：K1/K2/K5 + patch-tree linux 段 + pins/changelog/header/known-red）→ `8/8 checks passed`、`EXIT=0`；`run.sh --inject` 两路真实注入：① 回退旧两级解码（位图 id 判 FOREIGN）⇒ K1 复红且命中 `unrecoverable supv exception cause=PTWMEM(0x10000000000000)`；② `[48..56]` 段掩码整体移一位 ⇒ K1 复红且命中 `unknown cause=0x10000000000000`；两路均 `cp`+md5（含空注入核查）还原后 K1 回绿，`--inject` 汇总 `21/21 checks passed`、`EXIT=0`。另：独立探针 `k2_trap_probe`（不在任何 `make` 目标内）修好其 `contract-see §4` 解析器后可跑 `80/88`——解码相关组 `C5/C8/C10/C11/C12/C13` 全过，余 `C6/C7`（P2 重试与 P5 帧，最后改于 `m18-linux-022` 的 `trap.S`/`entry.h`）与 `C14`（`escape` 目标错误未再报 `CFXESC`，硬件侧行为）为**基线既有**；`k4_cow_probe --cases 3` 在启动阶段 `rc=124`、未到 `K4 cow: begin`（同为基线既有，独立探针、不在门控内）。`cause_info` 口径未改：PTW 位 = 访问 VA、`ADWBFAIL` = PTE PA。

**新发现/坑**：① 扁平位图下页故障**没有**低位 cause ⇒ `dadao_cause_name()` 须按区给名（`PTWPERM`/`PTWMEM`），「查名」与 `dadao_die` 都要用原始 id；② 探针注册/匹配须用原始 id（K1/K2 探针改注册 `1 << DGPTRAP`），否则「探针被分类并续跑」不再成立；③ §7.1 索引表仅 Tiny（ADR-0062 D6）⇒ 位图 die 码取位号低半字节、`__ffs(0)` 显式给 0，门控按 `contract-see §6.1.1` 位号现场派生、不写死；④ 删掉的 `NONPTW` 分支改由「`CFXMEM`/`CFXPERM` 低位 cause」具名判词（`die-cfxmem`/`die-cfxperm`）；⑤ 既有 `m18-linux-024` 窗口在解码修好后成为唯一残留红：异步交付落 umon 恢复/异步返程窗口 ⇒ `rb3` 被清零/取错 ⇒ `va=0x208`/`0x18` `die 0xe4`，或异步恢复里 `MALIGN`（`ip=0x20000153xxx`、info=掩码值）；K6 实测 3 次 024 窗口红、1 次绿；⑥ `check_k6` 的 E 组原判据取「控制台最后一行」，tick 在 `exit 7` 后打印 `K2 async user:` 即误红——改为「最后一条 shell 提示符行」（与模块文档串同义，未放宽语义）。

**遗留问题**：① **需 architect 裁定顺序**：`check-linux-k6`（及 K5 的低概率）要等 `m18-linux-024` 修好才能稳定绿；本任务只做解码、未改异步模型与路由。② Vast 三方对照属 chipyard 侧任务（用户 2026-11-25 裁定），不在本任务。③ `check-knowledge-refs` 的红只是 base 落后（master 已随 `m17-spec-004`/ADR-0063 转绿），合并后应消失；④ 同族 flaky 已由 `ISS-539` 登记（信号投递死在异步异常入口 ~1/10）。

## 审阅记录

### 第 1 轮 engineer 自审

**范围**：`cause-sub.h`（位图解码/形状判据）、`traps.c`（名称/分派/探针匹配/退出码）、`mm/fault.c`（位图判词）、`k1_pt.c`+`k2_selftest.c`（探针注册）、注释类（`trap.h`/`pgtable.h`/`process.c`/`k4_switch_selftest.c`）、8 个门控/探针、`changelog.md`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 名称检查用类掩码 ⇒ 位图故障仍 `unknown`（K1 首轮复红） | ✅已修 | 查名/探针匹配/die 全改原始 id；`dadao_cause_name()` 按区给名 | K1 113/113 |
| 探针按低位 cause 注册（`1<<1`）⇒ 位图故障不匹配 | ✅已修 | K1/K2 探针注册 `1 << DGPTRAP`，K1 打印位名 | K1 P5 / K2 C5 位号断言 |
| 位图 die 无 §7.1 索引 | ✅已修（口径） | 位号低半字节 + `__ffs(0)` 显式 0，注释引 D6 | K2 X6 = 0xe4；K1 注入 0xe4 |
| 删 `NONPTW` 后非页表故障无判词 | ✅已修 | `CFXMEM→die-cfxmem`、`CFXPERM→die-cfxperm` | `k2_time` C8 仍 `CFXPERM(0x80)` |
| 门控旧期望（`CFXMEM`/0xe1） | ✅已修 | 改按 §6.1.1 现场派生位号与码 | K1/K2/K4 自检全绿 |
| `__ffs(0)` 未定义 | ✅已修 | `dadao_cause_index()` 显式返回 0 | 编译通过；K2 P4 unknown 仍在 monitor 段 |
| K5 首跑 flaky（024 窗口 + F7 顺序化） | ⏸延后（非本任务） | 未改异步模型；`check_k6` E 组判据取「提示符行」 | K5 285/285；K6 82/82 |

**判决**：finding 全部处置（5 修 + 1 口径 + 1 延后归 024）；K1/K2/K5 真绿，K6 绿有记录（flaky 归 024），补丁/静态门控全过。状态 → 待验收。

### 第 1 轮 reviewer 验收（2026-11-25）

**重跑记录**（仓库根执行运行期证据目录内的 `run.sh` 及其参数；rc 一律取被检命令自身、无 `tee`；日志落审查用临时树）：
- `run.sh`（默认面）→ `8/8 checks passed, 0 failed` **rc=0**；`run.sh --inject` → `21/21 checks passed` **rc=0**。
- 注入①「回退旧两级解码」：K1 **rc=2**，真实输出 `dadao: unrecoverable supv exception cause=PTWMEM(0x10000000000000)`；`cp`+md5 还原（两侧相等）→ 回绿 `check-linux-k1: PASS (113/113)`。
- 注入②「`[48..56]` 整体移位」：K1 **rc=2**，真实输出 `dadao: unknown cause=0x10000000000000 (not in the 11-item table)`；还原 → 回绿 `PASS (113/113)`。
- `check-linux-k1` **rc=0 `PASS (113/113)`**；`check-linux-k2` **rc=0 `PASS (170/170)`**（R 组 K0 146/146、K1 113/113；E8/E9/X6 = `0xe4`/`PTWMEM`；X8 `cfxmem=0xe1`；E2 预声明 CFXMEM 命中 1）。
- `check-linux-k5` **连跑 5 次全 rc=0、全 `285/285`**（S44 C41 F40 T34 G29 P35 R62）；G 组新断言实测 `id=0x2000000000`（=1<<§6.1.1 NWPERM）、`PTWPERM/NWPERM`。
- `check-linux-k6` **连跑 5 次 rc = 0,2,0,0,2（3 绿 2 红）**。两红签名：`dadao: die mode=2 code=0xe4` + `K3 pf: id=0x10000000000000 cause=PTWMEM sub=DGPTRAP ip=0x20000153520 va=0x10` / `ip=0x20000151cb4 va=0x208 … result=die-no-vma`，且两次 `[PASS] 无 unknown cause` ⇒ 解码字段全对、**无 `unknown cause`、无 PTW 解码错**，属 `ISS-539`/`m18-linux-024` 异步交付窗口族，**非本任务引入**。
- `check-patch-tree`：全仓 rc=1（chipyard/musl 14–15 problem，属其它会话在飞），**linux 段 0 problem、`linux: 105 patch(es)`**；注入前后 linux 段 problem 集合逐行相同。
- `check-config-pins` rc=0（93 项）、`check-component-changelog` rc=0、`check-index-blobs` rc=0（357 new-file OK）、`make_patch.py --dry-run linux` rc=0（105 补丁，E1 通过）。
- `check-knowledge-refs` rc=2，唯一悬空 = `milestones-m17.md` 的 `ADR-0063`；**同命令在 master 由我亲跑 rc=0（悬空 0）** ⇒ base 差异，非本任务。
- 独立注入（第三路，非 engineer 两路）：`dadao_cause_name()` 区名三元式互换 → `check-linux-k2` **rc=2**，`E3 期望=PTWMEM 实际=PTWPERM`、`E9 期望=PTWMEM 实际=PTWPERM`（K0 R1/R2 亦红）；`cp` 还原 md5 相等、源树 0 注入残留；回绿 `PASS (170/170)` ×2。

**约束核验**：位图编码表由我自读 `ADR-0062` D1/D2/D4/D6 + `contract-see §6.1/§6.1.1` 独立列出（16 位：`[32..38]` 7 权限 + `[48..55]` 8 缺失 + `[56]` ADWBFAIL），与 `cause-sub.h` 逐位一致（`contract bits: 16 / header bits: 16 / mismatches {} / deleted bits still defined []`）；`NCFXPERM(39)`、`NONPTW(57)` 与 wyde 归属宏在 linux 补丁·门控·探针**零残留**（仅 changelog 历史条目与 `k4_cow_probe.py:154` 的反向守卫命中）。`traps.c` 三处：查名/探针匹配/`dadao_die` 全用原始 id，`dadao_cause_name()` 给 `PTWPERM`/`PTWMEM`，`dadao_cause_index()` = `__ffs(&0xf)` 且 `__ffs(0)` 显式 0，die 码 `0xc0|2<<4|(52&0xf)=0xe4` 实测一致（§7.1 索引表仅 Tiny，D6）。`fault.c`：`NONPTW` 分支已删 → `CFXMEM→die-cfxmem`、`CFXPERM→die-cfxperm`（`k2_time` 实测 `result=die-cfxperm`）；ADWBFAIL 先于 VMA 查找（info=PTE PA）、其余位图位 info=访问 VA，与 `ADR-0062 D4` 一致。范围：`git diff --name-only` 19 文件 = 9 补丁 + changelog + 8 测试 + 任务书，**无 `spec/`、契约、`Makefile`、`tests/arch/**`、`expected-divergences.yaml`、其它组件**；changelog 4 插入 0 删除（纯追加）；审查前后 `git status` 快照逐行相同、目标文件 md5 相同、无未跟踪残留；未为 chipyard 改任何测试侧文件（依赖口径按 2026-11-25 裁定）。

**Findings（不阻断，交 architect 定夺）**：
- **F1** `dadao_subcause_layout()` / `dadao_subcause_is_ptw()` 对 `ADR-0062 D1` 不变式①（64 位恰一位）有一个洞：`[31:16]` 单 bit + 恰一个位图 bit ⇒ 两函数都判 `OK`/`PTW`（我按 16 种形态逐例复算确认）；旧代码无条件校验 `[31:16]==0`，本次收窄，而函数自述「exactly one bit of the 64」过强。**不可达**（异步源不占 `excp_cause_id`、`[31:16]` 保留、ADR-0062 声明该段不属本 ADR 范围），且已无门控覆盖畸形 id ⇒ 建议一行收紧，或在注释写明覆盖域。
- **F2** 完成区的 K6 `82/82 rc=0` **取的是 5 次里最好的 1 次**（同句已内联披露「5 次中 1 次」与 3 次 024，非隐瞒，此处按要求点名）；我方 3/5 绿、2 红均 024 族 ⇒ **建议先 `m18-linux-024` 再收 K6**，与遗留①一致。
- **F3** `check-linux-k2` 的 T11（时序 margin）在 load≈8 下红过 1 次（169/170），随后 2 次 170/170；T11 未被本任务改动，属负载敏感的既有断言。
- **F4** `k2_time_probe` 实跑 **FAIL (1/201)**：`C8 …（info = 指令字）`要求 `info <= 0xffffffff`，实测 `info=0x20000115320`（== ip），与 `contract-see §6.1`「CFXPERM 恒为地址、触发指令地址与 `excp_cause_ip` 同值」矛盾，该断言自 2026-11-16 起即不可过，文件不在本任务改动集。完成区所引「`k2_time` C8 仍 `CFXPERM(0x80)`」**属实**（`cause=CFXPERM(0x80)` 与 rc=0xe7 均 PASS），但该探针整体是红的，收尾应写明；同一 run 另给出 `result=die-cfxperm` 的行为证据。
- **F5** 证据脚本第 4 条：若 `check_patch_tree.py` 自身崩溃，`grep -c` 得 0 会判 PASS（全仓 rc 只打印不门控）；真出 linux problem 时可达 FAIL（我方实跑 `actual=0`），建议补「日志含 linux 段汇总行」判据。

**判决：Accepted** —— 验收命令块在本人重跑下全部通过、约束逐条无违反；K6 的 2 次红定性为 024 族条件绿（不计入本任务），K5 5/5 真绿。
