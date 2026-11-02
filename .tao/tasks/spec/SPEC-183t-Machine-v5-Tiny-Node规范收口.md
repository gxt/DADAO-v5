# SPEC-183t: Machine-v5 Tiny/Node 规范与 ADR 收口

**模块**：spec
**项目里程碑**：M11
**依赖**：无（口径取自 `.tao/knowledge/discussing.md` 2026-11-02 裁定与 `TESTCASES-091t` §2 profile 表，本任务须与之逐项一致；下游 `QEMU-079t`/`QEMU-080t`、`TESTCASES-091t` 依赖本任务）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户授权（2026-11-02，经主会话转达）

> 「DADAO-12 只要求 cfx_power BootROM **≥64 KiB**，实际大小由 Machine-v5 规定；删除 `cfx_power` 不设 SRAM 的绝对句。」
> 「Machine-v5-Tiny：BootROM 64 KiB `0xffff_ffff_0000`..，SRAM 8 MiB `0xffff_ff00_0000`..；宿主装载，无 hmon/PTW/异常路径。Machine-v5-Node：BootROM 4 MiB `0xffff_ffc0_0000`..，复位 `0xffff_ffff_0000`；PA RAM 2 GiB；hmon/PTW/hypv，测试本体在 hypv；smon 路径保留。」
> 「不做双映射；不新立 ADR；修改 ADR-0004/0039/0040/0043 与 `spec/Machine-v5-测试机运行环境.md`；如 DADAO-12 需改，按只读册授权更新锁。」

授权范围：`spec/Machine-v5-测试机运行环境.md`、`spec/DADAO-12-SEE-主管系统运行环境.md` 正文 + `manifests/spec-readonly.lock.toml` 对应两册 sha256/注记（`Process-06 §2/§5`）。**ADR 的每个决策级改动仍须逐条确认**（`AGENTS.md`「ADR decision 逐条确认」），见 §未决 4。

## 目标

1. `spec/Machine-v5` 正文由「单一几何」改为 **Tiny / Node 两个 FS profile**，成为两 profile 几何的唯一规范真源（含复位、BootROM、RAM/SRAM、页表/SPF、模式、smon 保留）。
2. `spec/DADAO-12 §2.1` 把 `cfx_power` BootROM 由「固定 256 KiB」改为「**≥64 KiB、实际大小由平台规范规定**」，删「`cfx_63`（power）不设 SRAM」的绝对句；复位向量 `0xffff_ffff_0000` 不动。
3. ADR-0004/0039/0040/0043 记录与上述口径的**覆盖关系/平台口径/事实订正**（不新立 ADR）。
4. 两册只读锁 sha256 + 授权注记同笔更新；全部门控绿（基线红见 §基线）。

## 两 profile 参数（规范正文写真源；逐项与 `TESTCASES-091t` §2 对齐）

**Machine-v5-Tiny**（宿主装载的精简 FS 平台）
- BootROM：64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`（cfx63 内部偏移 `0x3_ffff_0000`）；复位地址 = 基址 = `0xffff_ffff_0000`（镜像偏移 0）。
- SRAM：8 MiB `0xffff_ff00_0000`–`0xffff_ff7f_ffff`（cfx63 内部偏移 `0x3_ff00_0000`）；宿主 loader 按 ELF `PT_LOAD` 装入 `.text/.rodata/.data/.bss`，**不塞 BootROM**；入口 = SRAM 基址。
- 页表/SPF：**无**——`ptw_enable=0`，不使用 `addr[47:42]=0` 内存窗口，无 PTBR/页表/TLB。
- 模式：`power` 复位 → 最小配置 → `trap cfx_umon` 进入 `user`（测试本体）；不配置 hmon/smon 向量，无异常处理路径；`jail` 不启用。
- cfx 范围：`cfx0`（umon）、`cfx63`（power）；不实现 `cfx2/3/4/17`。
- 退出：semihosting `SYS_EXIT`（实现层短路，不进向量，`ADR-0020 D4/D10`）。
- smon：无（不保留）。

**Machine-v5-Node**（完整系统节点，单核，可扩展多核/NUMA）
- BootROM：4 MiB `0xffff_ffc0_0000`–`0xffff_ffff_ffff`（cfx63 内部偏移 `0x3_ffc0_0000`）；复位地址 `0xffff_ffff_0000`（镜像偏移 `0x3f_0000`）；布局沿用 `ADR-0043 D2`（偏移 0 image index table + ELF + 末 64 KiB 复位/启动代码）。
- RAM：PA `[0, 0x8000_0000)` = 2 GiB（内存窗口 `addr[47:42]=0`，`ptw_enable=1`）。
- 页表/SPF：PTBR=0（PA 0 放 64 KiB L1 表），L1 index `0x1000`–`0x1003` 4 个 512 MiB 超页 ⇒ VA `0x0200_0000_0000`–`0x027f_ffff_ffff` 映射 PA `0`–2 GiB；每项 `S=1,U=J=H=0,R=W=X=1,P=1,SP=1,SPF=0xFF`，A/D 硬件维护（`ADR-0040 D4/D10`）。
- 模式：`power`(hypv) → `hmon`(hypv) → 测试本体在 **hypv** 运行；`power → hmon → smon` 路径**保留**给内核/smon 测试；`jail` 不启用。
- cfx 范围：`cfx0/1/2/3/63` + `cfx4`（PTW/TLB）+ `cfx17`（pmem 64 KiB SRAM + `cg15` DMA）+ `cfx15/18`（时间，按现文）。
- smon：保留（64 KiB SRAM `0x0bff_0000_0000`）；hmon SRAM 64 KiB `0x0fff_0000_0000`。
- 退出：semihosting `SYS_EXIT`。

**两 profile 共同**
- 复位地址固定 `0xffff_ffff_0000`；`addr[47:42]` 分区键、VA 42 位 / PA 56 位、64 KiB 页/512 MiB 超页不变。
- **不做双映射**：Tiny SRAM 只在 `0xffff_ff00_0000`（无 PA 侧别名）；Node RAM 只在 PA `[0,2 GiB)` 并仅经上述 VA 映射；删除现行「PA 0 别名（16 MiB DRAM 在 `[0,16 MiB)` 另设别名）」约定——Node 的 PA 0 就是真 RAM，不是别名。
- `power` 不设 SRAM 为**本机约定**（两 profile 都不设），但 DADAO-12 不再作为架构禁令。
- legacy `-bios` 64 KiB 复位窗口语义不变（Tiny 恰为该窗口）。

## 接口规范（正文落点，禁改章节编号）

`spec/Machine-v5`：**保持全部现有 `##`/`###` 编号与标题**（`[Machine-01 §1/§3/§4/§5.x]` 被 19 处合约引用，改号会连带破引用），只改内容：

- §1 开头：补「本机分 `Machine-v5-Tiny` / `Machine-v5-Node` 两个 profile，由机器属性选择；复位地址两 profile 相同」。
- §1.1：标题不变，表改为**两张 profile 表**（Tiny / Node，行 = 区域/起始/大小/cfxha/说明），正文 bullet 改为 profile 差异清单（含「删除 PA 0 别名」「不做双映射」「power SRAM 平台约定」）。
- §1.2：越界/取指路由按 profile 写明（Tiny：cfx63 段内非 SRAM/BootROM ⇒ `CFXMEM`；`addr[47:42]=0` 且 `ptw_enable=0` ⇒ `CFXMEM`；Node：`ptw_enable=1` 走页表、页表异常进 `cfx_ptw`）；`CFXMEM=0x81`/`unmapped=0x87` 码表冻结不动。
- §2：模式与启动链按 profile 分述（Tiny 无 hmon/smon；Node 保留 smon 路径）；`jail` 两 profile 均不启用。
- §3：cfx 实现范围按 profile 分述（Tiny 仅 `cfx0/63`；Node 见上）；两轴权限模型不动。
- §6：BootROM 几何/装载语义/模式移交按 profile 分述；Tiny 无 image index table（64 KiB 全部为复位/启动代码）。
- §4/§5/§7 语义不动（仅当措辞与 profile 冲突时做最小订正）。

`spec/DADAO-12`（上游只读册，授权已给）：
- §2.1 表 row 63 power：起始/大小改为「自 2^48 向下的 BootROM，顶端 64 KiB 起点 `0xffff_ffff_0000`，大小 **≥64 KiB**（具体由平台规范规定）」。
- §2.1 说明 bullet：删「`cfx63`（power）不设 SRAM」；BootROM 段落改为「≥64 KiB、复位向量固定 `0xffff_ffff_0000`（BootROM 末 64 KiB 起点，镜像内偏移 = size − 64 KiB）」；cg7 校验示例改为两例（64 KiB ⇒ `start=0x3_ffff_0000`；4 MiB ⇒ `start=0x3_ffc0_0000`，`start+size=2^42`）。
- 附录 `0.7.3-rc（未发布）` 段：**就地修订**与上述直接冲突的旧条目 + 追加一条聚合说明（该段为未发布累积段；`0.7.2` 及更早历史**一字不动**）。

`manifests/spec-readonly.lock.toml`：两册 `sha256` 同笔重算 + 逐册授权注记（含用户授权原话摘要与日期）。

## 范围 / 非范围

**在范围内**：上述两册 `spec/` 正文；`manifests/spec-readonly.lock.toml`（仅两册条目）；`.tao/adr/adr-0004/0039/0040/0043`（见 §未决 4）；本任务书；`.tao/knowledge/milestones.md` 流水行。

**不在范围内**（违反即越界）：`components/**`（QEMU/gem5 补丁）、`tests/**`、`tools/**`、`Makefile`、门控脚本、`contracts/**`、`spec/README.md`、`.tao/archive/**`（**历史归档不重写**，含归档任务书/回顾里的 256 KiB、16 MiB 旧引用）、`.tao/knowledge/discussing.md`（仅主会话可改）。

## 验收标准

1. **两 profile 自洽（脚本化、可 FAIL）**：证据脚本从规范正文派生并断言——Tiny `base+size-1 == 0xffff_ffff_ffff`（64 KiB）且复位=基址；Tiny SRAM 8 MiB 首尾、与 BootROM 不重叠；Node BootROM 4 MiB 首尾、复位 = `base+0x3f_0000`；Node PA RAM = 2 GiB 且 4×512 MiB 超页覆盖、`SPF=0xFF` 出现；`Machine-v5` 全文不再含 `0xFC00_0000_0000`、`0xffff_fffc_0000`、`256 KiB`、`16 MiB`、`PA 0 别名`；`DADAO-12` 不再含「power）不设 SRAM」「256 KiB」作为现行口径（历史 0.7.2 段除外，需按段号限定）。
2. **门控（每条贴真实命令 + rc，主工作树）**：`make check-spec-readonly`、`make check-spec-refs`、`make check-spec-drift`、`make check-spec-changelog`、`make check-spec-numbering`（`check-numbering` 的实际 target 名）、`make check-spec-cite-targets`、`make check-knowledge-refs`、`make check-milestones-fresh`、`make check-spec-purity`；另 `make check`（L1）与 `make check-modules`（L2，AGENTS 任务收尾要求；不改代码预期绿，**启动前申报耗时**）。
3. **只读锁**：两册 `sha256sum` 与锁值逐字相等；锁 diff 仅这两册块（4+/1- 级），未误伤其它 20 册；授权注记含日期与用户原话摘要。
4. **章节编号零漂移**：`git diff -U0` 证明所有 `##`/`###` 标题行未变（仅正文变动）；若必须新增标题，只允许 `#### N.M.K` 且同级 ≥2、编号连续。
5. **归档零改动**：`git status --porcelain -uall` 与 `git diff --name-only` 均不含 `.tao/archive/**`；归档里的旧几何引用保持原样（历史快照，不追改）。
6. **反例可达 FAIL**：至少两处注入（如把 Tiny BootROM 改成 `0x2_0000`、或把「≥64 KiB」改回「256 KiB」固定）⇒ 证据脚本/门控 FAIL；`cp` 备份 + `md5sum -c` 还原后回绿；**禁** `git checkout/restore/stash`。证据脚本落 `.work/evidence/SPEC-183t/run.sh*`（`--inject` 模式）。
7. **基线诚实**：`check-knowledge-refs` 当前基线**红**（`TESTCASES-091t` 的 `.work/evidence/TESTCASES-091t/*` 尚未落盘，非本任务引入）。本任务要求「不新增悬空 + 基线红原样记录」，**不得**为凑绿去改 `TESTCASES-091t` 任务书或移除其证据路径。
8. 完成区 ≤30 行；状态置 `待验收`。

## 证据

- `.work/evidence/SPEC-183t/run.sh*`：一条命令重跑全部门控，逐项取**命令自身** rc（禁 `| tee` 吞码），输出 profile 自洽断言明细与锁 sha256 对账；`--inject` 走注入/还原（`cp` + `md5sum -c`）。
- `.work/evidence/SPEC-183t/*.log`：门控原始输出、`sha256sum` 前后快照、`git diff --stat`。
- 完成区只写结论 + 命令 rc + 证据路径。

## 未决（派单前须主会话确认）

1. **契约投影是否纳入**：`.tao/contracts/contract-see.md`（§1 的「RAM `0xFC00_0000_0000` 16 MiB + PA 0 别名 / BootROM 256 KiB」、§3 power 空间块 `0x3ff_fffc_0000/0x4_0000`）与 `contract-elf.md`（BootROM 区 256 KiB、trampoline 64 KiB）在改 spec 后会与规范矛盾；无门控强制。**建议纳入本任务**（纯文本，2 文件，`check-spec-drift` 不受影响——两册均为 ADR-sourced）。若维持「只改规范/ADR/锁」，须登记为跨模块遗留并另立任务。
2. **Tiny 移交方式**：`TESTCASES-091t` §2 写 `default_run_mode=user` 且「power 配置 `cfx_umon` 用户向量 → `trap cfx_umon`」。建议规范正文照此写死（Tiny 因此**实现 cfx0 寄存器**，仍无 hmon/PTW/异常处理路径）；若改为「直接跳转 SRAM 基址」，须同步 091t。请裁定。
3. **Tiny 是否需要 `cfx17`(pmem)/`cfx4`(ptw)**：建议都**不实现**（无 DMA/无 PTW 需求）；若有测试依赖，另裁。
4. **ADR 决策级改动逐条确认清单**（`AGENTS.md` 要求逐条确认，确认原话须回填本任务书）：
   - ADR-0004：新增「rev. 2026-11-02」条目，**覆盖** `D1` 地址表的 RAM/BootROM 行、`R3`/rev-2026-10-11 的 RAM 基址与容量口径 ⇒ 改为「几何由 `Machine-v5` 两 profile 规定」；`-bios` 64 KiB 复位窗口、`SYS_EXIT`、故障码表均不变。
   - ADR-0039：`D6` 保留 cfx「7–14」订正为「**6–14**」（与 `DADAO-12 §2.1`、`Machine-v5 §1.2` 一致）；补平台口径注记（PA RAM 大小/映射由平台规范定：Node 2 GiB、Tiny 无内存窗口）。
   - ADR-0040：`Consequences` 补 1 条平台使用说明（Node 第一张页表只用 L1 超页 4 项、`SPF=0xFF`；Tiny 不用页表）；PTE 格式/异常优先级**不改**。
   - ADR-0043：就地修订 `D1`（BootROM 大小由平台规定，Tiny 64 KiB / Node 4 MiB；power 不设 SRAM 改「本机约定」）、`D3`（Tiny 无 power→hmon 复制链，测试镜像由宿主装入）、`D10`（Node 第一张页表 4 超页覆盖 2 GiB）、`D11`/`D12` 同步；`## 修订` 记日期 + 授权原话。
   **未逐条确认 ⇒ ADR 部分 BLOCKED**；spec 正文与 ADR 须同笔落地，不拆两轮。
5. **README 版本表陈旧（既有问题，非本任务引入）**：`README.md` Machine 行 `已发布 0.3.0 / 在研 0.3.0`，而 `spec/Machine-v5` 册头为 `0.3.2-rc`、`0.3.1（2026-10-16）` 已发布。本任务**不改版本号**（`check-spec-changelog` 要求 `-rc` 段 = 下一段 z+1，不能跳 `0.4.0-rc`；与 `SPEC-179t/180t` 同法在 `0.3.2-rc` 段累积）。是否顺手修 README 该行请裁定；不修则登记遗留。

## 参考对照（0628 溯源，非执行必需）

- 「内容溯源，非执行必需」：0628 的 `reset→hypv→supv` 核对报告（`.cache/refs/DADAO-0628/docs/reviews/kernel-hypv-supv-handoff-20260721.md`，只读）指出**当时的 QEMU/gem5 都没有真实移交**——`-kernel` 裸加载 + host-side syscall 被当作启动，属已知坑。
- 0628 做法 → 本项目差异 → 建议落点：0628 单机几何 + 移交缺口 ⇒ v5 显式分 **Tiny（宿主装载、无 hmon/PTW/异常路径，承认是精简 profile）** 与 **Node（hmon/PTW/hypv + smon 保留，真移交）** ⇒ 落点 = `Machine-v5 §1/§2/§6` 的 profile 分述，禁止把 Tiny 的简化当"完整机器"。
- 0628 的 ADR-0004 reset PC `0x00100000` 与本机「复位 = `0xffff_ffff_0000`」不同 ⇒ 不复用其机地址。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（自审意见、finding 表、处置）

#### 第 1 轮 reviewer 验收
（独立重跑记录、约束核验、判决）
