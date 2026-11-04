# SPEC-183t: Machine-v5 Tiny/Node 规范与 ADR 收口

**模块**：spec
**项目里程碑**：M11
**依赖**：无（口径取自 `.tao/knowledge/discussing.md` 2026-11-02 裁定与用户最终口径；`TESTCASES-091t` §2 的 Tiny 入口/SP 与 Node VA 口径**落后于**本册，按 §测试侧约束注记登记交其同步；下游 `QEMU-079t`/`QEMU-080t`、`TESTCASES-091t` 依赖本任务）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户授权（2026-11-02，经主会话转达）

> 「DADAO-12 只要求 cfx_power BootROM **≥64 KiB**，实际大小由 Machine-v5 规定；删除 `cfx_power` 不设 SRAM 的绝对句。」
> 「Machine-v5-Tiny：BootROM 64 KiB `0xffff_ffff_0000`..，SRAM 8 MiB `0xffff_ff00_0000`..；宿主装载，无 hmon/PTW/异常路径。Machine-v5-Node：BootROM 4 MiB `0xffff_ffc0_0000`..，复位 `0xffff_ffff_0000`；PA RAM 2 GiB；hmon/PTW/hypv，测试本体在 hypv；smon 路径保留。」
> 「不做双映射；不新立 ADR；修改 ADR-0004/0039/0040/0043 与 `spec/Machine-v5-测试机运行环境.md`；如 DADAO-12 需改，按只读册授权更新锁。」
> 最终口径（覆盖旧稿）：「Tiny：地址高 6 位恒 `0x3F`；**无任何 cfx（含 cfx_power）**；不能进入 user 模式；允许 semihosting（`trap` 只作 host 陷入开关，不算 cfx 类）；Tiny 只负责非 cfx `inst` + `embench` + `picolibc`。」「raw `-kernel` 基址 `0xffff_ff01_0000`，前 `0x100` 全零，应用入口 `0xffff_ff01_0100`，SP `0xffff_ff7e_ff00`；ELF 的 crt/stub 在 `0xffff_ffff_0000`，`e_entry` 在 ROM、跳应用入口；raw/ELF 统一入口/SP。」「picolibc A：crt/stub 在 ROM，应用 `.text` 在 `0xffff_ff01_0100`，picolibc `__start` 在 SRAM 清 BSS；链接脚本命名 `dadao-tiny.lds` / `dadao-node.lds`，不保留泛名（属后续 testcases，不在本任务改 tests）。」「用户已逐条确认 ADR-0004/0039/0040/0043 四项修订。」

授权范围：`spec/Machine-v5-测试机运行环境.md`、`spec/DADAO-12-SEE-主管系统运行环境.md` 正文 + `manifests/spec-readonly.lock.toml` 对应两册 sha256/注记（`Process-06 §2/§5`）；ADR-0004/0039/0040/0043 的四项修订（已逐条确认）。`contract-see`/`contract-elf` 若与改后 spec 矛盾，按「最小同步 + 完成区说明」处置（用户最终口径第 6 条）。

## 目标

1. `spec/Machine-v5` 正文由「单一几何」改为 **Tiny / Node 两个 FS profile**，成为两 profile 几何的唯一规范真源（含复位、BootROM、RAM/SRAM、页表/SPF、模式、smon 保留）。
2. `spec/DADAO-12 §2.1` 把 `cfx_power` BootROM 由「固定 256 KiB」改为「**≥64 KiB、实际大小由平台规范规定**」，删「`cfx_63`（power）不设 SRAM」的绝对句；复位向量 `0xffff_ffff_0000` 不动。
3. ADR-0004/0039/0040/0043 记录与上述口径的**覆盖关系/平台口径/事实订正**（不新立 ADR）。
4. 两册只读锁 sha256 + 授权注记同笔更新；全部门控绿（基线红见 §基线）。

## 两 profile 参数（规范正文写真源；以用户最终口径为准）

**Machine-v5-Tiny**（宿主装载的精简 FS 平台；`addr[47:42]` 恒 `0x3F`）
- BootROM：64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`（cfxha 63 段内，内部偏移 `0x3_ffff_0000`）；复位地址 = 基址 = `0xffff_ffff_0000`（镜像偏移 0）；全部为复位/启动 stub，**无 image index table**。
- SRAM：8 MiB `0xffff_ff00_0000`–`0xffff_ff7f_ffff`（cfxha 63 段内，内部偏移 `0x3_ff00_0000`）；宿主 loader 按 ELF `PT_LOAD` 装入 `.text/.rodata/.data/.bss`，**不塞 BootROM**。
- 装载：raw `-kernel` 基址 `0xffff_ff01_0000`，镜像前 `0x100` 全零，应用入口 `0xffff_ff01_0100`，`SP = 0xffff_ff7e_ff00`；ELF 的 crt/启动 stub 在 `0xffff_ffff_0000`、应用 `.text` 在 `0xffff_ff01_0100`、`e_entry` 在 ROM，picolibc `__start` 在 SRAM 清 BSS；**raw/ELF 统一入口 `0xffff_ff01_0100`、统一 `SP`**。
- 页表/SPF：**无**——`ptw_enable` 恒 0，无 PTBR/页表/TLB。
- 模式：不提供模式切换，复位后即在特权态（名义 `hypv`/cfxha 63）执行，**不能进入 `user`**；无 hmon/smon、无异常向量与异常处理路径；`jail` 不启用。
- cfx：**不实现任何 cfx（含 `cfx_power`）**；cfx 寄存器访问/`cfx2rd`/`cfx2rc` ⇒ `CFXREG`，非 semihosting 的 `trap`/`escape` ⇒ `ILLI`。`trap` 只在 semihosting 区有效，**只作陷入宿主的开关**，不算 cfx 类。
- semihosting：**允许**（控制台 + `SYS_EXIT` 退出）。
- 退出：semihosting `SYS_EXIT`/`SYS_EXIT_EXTENDED`。
- 测试范围：非 cfx `inst` + `embench` + `picolibc`。

**Machine-v5-Node**（完整系统节点，单核，可扩展多核/NUMA）
- BootROM：4 MiB `0xffff_ffc0_0000`–`0xffff_ffff_ffff`（cfx63 内部偏移 `0x3_ffc0_0000`）；复位地址 `0xffff_ffff_0000`（镜像偏移 `0x3f_0000`）；布局沿用 `ADR-0043 D2`（偏移 0 image index table + ELF + 末 64 KiB 复位/启动代码）。
- RAM：PA `[0, 0x8000_0000)` = 2 GiB（内存窗口 `addr[47:42]=0`，`ptw_enable=1`）。
- 页表/SPF：PTBR=0（PA 0 放 64 KiB L1 表），L1 index `0x1000`–`0x1003` 4 个 512 MiB 超页 ⇒ VA `0x0200_0000_0000`–`0x0200_7fff_ffff` 映射 PA `0`–2 GiB；每项 `S=1,U=J=H=0,R=W=X=1,P=1,SP=1,SPF=0xFF`，A/D 硬件维护（`ADR-0040 D4/D10`）。
- 装载：4 MiB BootROM 经 `bootrom-image` 装入；测试镜像 `PT_LOAD`/入口须落在上述 VA 区间（映射到 PA），入口/SP 由镜像与启动 stub 给出（首版由 `QEMU-080t` 实测校准）。
- 模式：`power`(hypv) → `hmon`(hypv) → 测试本体在 **hypv** 运行；`power → hmon → smon` 路径**保留**给内核/smon 测试（M11 不覆盖）；`jail` 不启用。
- cfx：`cfx0/1/2/3/63` + `cfx4`（PTW/TLB）+ `cfx17`（pmem 64 KiB SRAM + `cg15` DMA）+ `cfx15/18`（时间）；`cfx5` 已分配未实现。
- smon：保留（64 KiB SRAM `0x0bff_0000_0000`）；hmon SRAM 64 KiB `0x0fff_0000_0000`。
- 退出：semihosting `SYS_EXIT`。
- 测试范围：完整 `inst` + `arch` + `embench`，不含 `picolibc`。

**两 profile 共同**
- 复位地址固定 `0xffff_ffff_0000`；`addr[47:42]` 分区键、VA 42 位 / PA 56 位、64 KiB 页/512 MiB 超页不变。
- **不做双映射**：Tiny SRAM 只在 `0xffff_ff00_0000`；Node PA RAM 只在 `[0, 2 GiB)` 并经页表 VA 映射；两 profile 都不设同一存储的多地址别名。
- `power` 不设 SRAM 为**本机约定**（两 profile 都不设），DADAO-12 不再作为架构禁令。
- legacy `-bios` 64 KiB 复位窗口语义不变（Tiny 恰为该窗口）。

## 接口规范（正文落点，禁改章节编号）

`spec/Machine-v5`：**保持全部现有 `##`/`###` 编号与标题**（`[Machine-01 §1/§3/§4/§5.x]` 被 19 处合约引用，改号会连带破引用），只改内容：

- §1 开头：补「本机分 `Machine-v5-Tiny` / `Machine-v5-Node` 两个 profile，由机器属性选择；复位地址两 profile 相同」。
- §1.1：标题不变，表改为**两张 profile 表**（Tiny / Node，行 = 区域/起始/大小/cfxha/说明），正文 bullet 改为 profile 差异清单（含「不做双映射/不设多地址别名」「power SRAM 本机约定」「BootROM ≥64 KiB 由本册规定」）。
- §1.2：越界/取指路由按 profile 写明（Tiny：cfxha 63 段内非 SRAM/BootROM ⇒ `CFXMEM`；`addr[47:42]=0` 且 `ptw_enable=0` ⇒ `CFXMEM`；Node：`ptw_enable=1` 走页表、页表异常进 `cfx_ptw`）；`CFXMEM=0x81`/`unmapped=0x87` 码表冻结不动。
- §2：模式与启动链按 profile 分述（Tiny 无 hmon/smon/异常向量、不能进入 `user`、启动 stub 普通跳转；Node 保留 smon 路径、测试本体 hypv）；`jail` 两 profile 均不启用。
- §3：cfx 实现范围按 profile 分述（Tiny **无任何 cfx**，仅 semihosting；Node 见上）；两轴权限模型不动。
- §6：BootROM 几何/装载语义/模式移交按 profile 分述；Tiny 无 image index table（64 KiB 全部为复位/启动代码）、raw/ELF 统一入口与 SP。
- §4/§5/§7 语义不动（仅当措辞与 profile 冲突时做最小订正：§4.1 补 Tiny 一般 trap ⇒ `ILLI`、§5 补 Tiny 的 semihosting 口径）。

`spec/DADAO-12`（上游只读册，授权已给）：
- §2.1 表 row 63 power：起始/大小改为「自 2^48 向下的 BootROM，顶端 64 KiB 起点 `0xffff_ffff_0000`，大小 **≥64 KiB**（具体由平台规范规定）」。
- §2.1 说明 bullet：删「`cfx63`（power）不设 SRAM」；BootROM 段落改为「≥64 KiB、复位向量固定 `0xffff_ffff_0000`（BootROM 末 64 KiB 起点，镜像内偏移 = size − 64 KiB）」；cg7 校验示例改为两例（64 KiB ⇒ `start=0x3_ffff_0000`；4 MiB ⇒ `start=0x3_ffc0_0000`，`start+size=2^42`）。
- 附录 `0.7.3-rc（未发布）` 段：**就地修订**与上述直接冲突的旧条目 + 追加一条聚合说明（该段为未发布累积段；`0.7.2` 及更早历史**一字不动**）。

`manifests/spec-readonly.lock.toml`：两册 `sha256` 同笔重算 + 逐册授权注记（含用户授权原话摘要与日期）。

`.tao/contracts`（**仅最小同步，用户最终口径第 6 条**）：`contract-see` §1 的几何/启动链/cfx 范围/cg7 power 块，与 `contract-elf` 的 BootROM/RAM 上下限、`-bios` 窗口、VA=PA 的 profile 限定；Node 的 VA→PA 装载口径在合约里标注由 `QEMU-080t` 落地。

## 测试侧约束注记（不在本任务改 tests）

- **picolibc A 方案**：Tiny picolibc 自测 ELF 的 crt/stub 在 ROM `0xffff_ffff_0000`，应用 `.text` 在 `0xffff_ff01_0100`，picolibc `__start` 在 SRAM 清 BSS，`e_entry` 在 ROM（本任务只在 `Machine-v5 §6` 写机器侧装载语义）。
- **链接脚本命名**：`dadao-tiny.lds` / `dadao-node.lds`，不再保留泛名 `dadao.lds`；由 testcases 任务落地（`contract-elf` 中的 `dadao.lds` 字样待 tests 改名时同步）。
- **`TESTCASES-091t` §2 与本册不一致处（登记，交该任务同步）**：Tiny `entry`/`sp`/`default_run_mode`（本册：入口 `0xffff_ff01_0100`、SP `0xffff_ff7e_ff00`、无 `user`/无 `cfx_umon`）；Node 的 `entry=0x10_0000`/「VA=PA 恒等」须按 `Machine-v5 §1.1/§6` 的 VA 区间与 `QEMU-080t` 实测校准。

## 范围 / 非范围

**在范围内**：上述两册 `spec/` 正文；`manifests/spec-readonly.lock.toml`（仅两册条目）；`.tao/adr/adr-0004/0039/0040/0043`；`.tao/contracts/contract-{see,elf}.md`（最小同步）；本任务书；`.tao/knowledge/milestones.md` 流水行。

**不在范围内**（违反即越界）：`components/**`（QEMU/gem5 补丁）、`tests/**`、`tools/**`、`Makefile`、门控脚本、`spec/README.md`、`.tao/archive/**`（**历史归档不重写**，含归档任务书/回顾里的 256 KiB、16 MiB 旧引用）、`.tao/knowledge/discussing.md`（仅主会话可改）。

## 验收标准

1. **两 profile 自洽（脚本化、可 FAIL）**：证据脚本从规范正文派生并断言——Tiny BootROM 64 KiB 首尾（`0xffff_ffff_0000`/`0xffff_ffff_ffff`）且复位=基址；Tiny SRAM 8 MiB 首尾、与 BootROM 不重叠；Tiny 入口 `0xffff_ff01_0100`、SP `0xffff_ff7e_ff00`、raw 基址 `0xffff_ff01_0000` 且前 `0x100` 全零；Node BootROM 4 MiB 首尾、复位 = `base+0x3f_0000`；Node PA RAM = 2 GiB 且 4×512 MiB 超页覆盖、`SPF=0xFF` 出现；Tiny 无 cfx 表述（`不实现任何 cfx`）。
   - **旧几何清零**：`Machine-v5` 的**规范正文（`## 附录` 之前）+ `0.3.2-rc` 段**不再含 `0xFC00_0000_0000`、`0xffff_fffc_0000`、`256 KiB`、`16 MiB`、`PA 0 别名`；`DADAO-12` 全文不再含 `256 KiB`/`0xffff_fffc_0000`/「power）不设 SRAM」。**已发布历史段（`0.3.0` 及更早）按版本记录保留、一字不改**（另断言其 `git diff` 为空）。
2. **门控（每条贴真实命令 + rc）**：`make check-spec-readonly`、`make check-spec-refs`、`make check-spec-drift`、`make check-spec-changelog`、`make check-spec-numbering`、`make check-spec-cite-targets`、`make check-knowledge-refs`、`make check-milestones-fresh`、`make check-spec-purity`；另 `make check`（L1）与 `make check-modules`（L2，不改代码预期绿）。
3. **只读锁**：两册 `sha256sum` 与锁值逐字相等；锁 diff 仅这两册块（注释 + 1 行 sha256），未误伤其它册；授权注记含日期与用户原话摘要。
4. **章节编号零漂移**：`git diff -U0` 证明所有 `##`/`###` 标题行未变（仅正文变动）。
5. **归档零改动**：`git status --porcelain -uall` 与 `git diff --name-only` 均不含 `.tao/archive/**`。
6. **反例可达 FAIL**：至少两处注入（把 Tiny BootROM 大小改成 `0x2_0000`、或把 DADAO-12「≥64 KiB」改回「256 KiB」固定）⇒ 证据脚本 FAIL；`cp` 备份 + `md5sum -c` 还原后回绿；**禁** `git checkout/restore/stash`。
7. **基线诚实**：`check-knowledge-refs` 在**主工作树**为 PASS（现行盘上证据齐全）；在独立 worktree 内因 `运行期临时目录` 未随 worktree 复制而显示悬空，须以主工作树结果为准并在证据中记录两侧差异，**不得**为凑绿改任务书或删证据路径。
8. 完成区 ≤30 行；状态置 `待验收`。

## 证据

- `运行期证据脚本（已清理，未归档）*`：一条命令重跑全部门控，逐项取**命令自身** rc（禁 `| tee` 吞码），输出 profile 自洽断言明细与锁 sha256 对账；`--inject` 走注入/还原（`cp` + `md5sum -c`）。
- `运行期证据（已清理，未归档）`：门控原始输出、`sha256sum` 前后快照、`git diff --stat`。
- 完成区只写结论 + 命令 rc + 证据路径。

## 已裁定（2026-11-02，替代旧稿「未决」）

1. **契约投影纳入**：`contract-see`/`contract-elf` 按**最小同步**处理（用户最终口径第 6 条）；更深语义（Node ELF VA→PA 装载口径、`dadao.lds` 改名）登记为跨模块遗留，由 `QEMU-080t`/`TESTCASES-091t` 落地后再同步。
2. **Tiny 移交方式**：**普通跳转**（启动 stub 设 SP 后跳应用入口），**不实现 `cfx_umon`/不用 `trap` 移交**；旧稿的 `cfx0`+`user` 假设作废。
3. **Tiny 的 `cfx17`/`cfx4`**：**都不实现**（无 DMA/无 PTW）；Tiny 不实现任何 cfx。
4. **ADR 四项修订**：用户 2026-11-02 **已逐条确认**，按下列清单落地并各记日期 + 授权原话，不新立 ADR：
   - ADR-0004：新增 `## 修订` rev. 2026-11-02，**覆盖** `D1` 地址表 RAM/BootROM 行、`R3`/rev-2026-10-11 的 RAM 基址与容量口径 ⇒ 「几何由 `Machine-v5` 两 profile 规定」；`-bios` 64 KiB 窗口、`SYS_EXIT`、故障码表不变。
   - ADR-0039：`D6` 保留 cfx「7–14」订正为「**6–14**」；补平台口径（Node 2 GiB 经 4 超页映射；Tiny 无内存窗口/PTW）。
   - ADR-0040：`Consequences` 补平台使用说明（Node 第一张页表 L1 4 项、`SPF=0xFF`；Tiny 不用页表）；PTE/异常优先级不改。
   - ADR-0043：就地修订 `D1`（BootROM 大小由平台规定、power 不设 SRAM 为本机约定）、`D2`/`D3`（Tiny 无 index table/复制链）、`D10`（4 超页覆盖 2 GiB）、`D11`/`D12` 同步。
5. **README 版本表陈旧**：本任务**不改版本号**、不改 `README.md`；登记为遗留（`README.md` Machine 行仍写 `0.3.0`，而册头为 `0.3.2-rc`）。

## 参考对照（0628 溯源，非执行必需）

- 「内容溯源，非执行必需」：0628 的 `reset→hypv→supv` 核对报告（`0628 只读参考检出中的核对报告`，只读）指出**当时的 QEMU/gem5 都没有真实移交**——`-kernel` 裸加载 + host-side syscall 被当作启动，属已知坑。
- 0628 做法 → 本项目差异 → 建议落点：0628 单机几何 + 移交缺口 ⇒ v5 显式分 **Tiny（宿主装载、无 hmon/PTW/异常路径，承认是精简 profile）** 与 **Node（hmon/PTW/hypv + smon 保留，真移交）** ⇒ 落点 = `Machine-v5 §1/§2/§6` 的 profile 分述，禁止把 Tiny 的简化当"完整机器"。
- 0628 的 ADR-0004 reset PC `0x00100000` 与本机「复位 = `0xffff_ffff_0000`」不同 ⇒ 不复用其机地址。

## 完成区

**测试结果**：正文断言 **77/77 PASS**（`assert-assert.log`）；spec 门控 **9/9 rc=0**（`gate-*.log`）；反例注入 **2/2**「注入⇒FAIL、`cp`+`md5sum -c` 还原⇒回绿」（`run-inject.out`）；`run.sh` 全量 **RUN_EXIT=0**；`L1 make -k check` rc=2（唯一失败 `check-patch-tree`，gem5 补丁树与共享 `组件源树` 不一致，主工作树同样 rc=2，已基线登记）；`L2 make check-modules` **rc=0**。
**修改文件**：`spec/Machine-v5-测试机运行环境.md`、`spec/DADAO-12-SEE-主管系统运行环境.md`、`manifests/spec-readonly.lock.toml`、`.tao/adr/adr-0004|0039|0040|0043-*.md`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-elf.md`（最小同步）、本任务书、`.tao/knowledge/milestones.md`（流水行状态）。
**验收结果**：
- Tiny：BootROM 64 KiB `0xffff_ffff_0000`–`0xffff_ffff_ffff`、SRAM 8 MiB `0xffff_ff00_0000`–`0xffff_ff7f_ffff`、入口 `0xffff_ff01_0100`、SP `0xffff_ff7e_ff00`、raw 基址 `0xffff_ff01_0000`(+0x100=入口) 全部断言 PASS。
- Node：BootROM 4 MiB `0xffff_ffc0_0000`–`0xffff_ffff_ffff`、复位 = base+`0x3f_0000` = 末 64 KiB 起点、PA RAM 2 GiB、L1 `0x1000`–`0x1003` 4 超页 = 2 GiB、`SPF=0xFF` PASS。
- 旧几何清零（正文+0.3.2-rc）、`DADAO-12` 无 `256 KiB`/`fffc_0000`/「不设 SRAM」、`§5` 与 `0.3.0` 历史段与 HEAD 逐字节一致、标题 27/35 行零漂移；两册 `sha256sum` 与锁逐字相等。
**新发现/坑**：
- 原稿 Node VA 末址 `0x027f_ffff_ffff` 与「4×512 MiB」不自洽（实为 1024 超页）；按 `index<<29` 独立重算为 `0x0200_7fff_ffff`，全链修正。
- `Machine-v5` 已发布历史段（0.3.0/0.2.1）保留旧几何记录；判据改为「正文+`0.3.2-rc` 清零 + 历史段字节不变」。
- 独立 worktree 不带 `运行期临时目录`/`运行期安装根`：符号链接到主工作树后门控/工具链才与主树一致（否则 85 条假悬空）。
- 并发任务写共享 `运行期日志（已清理，未归档）` 会瞬时触发 `check-run-artifacts`（`QEMU-081t-*.EXIT` 非法名）；复跑即绿，非本任务引入（`baseline-说明.md`）。
**遗留问题**：
- `TESTCASES-091t` §2 的 Tiny `entry`/`sp`/`default_run_mode`、Node `entry=1 MiB`/「VA=PA 恒等」落后本册，交该任务同步（见 §测试侧约束注记）。
- Node ELF 的 VA→PA 装载口径（`contract-elf §5.2` 的 profile 限定）由 `QEMU-080t` 落地后回写；`dadao.lds` → `dadao-tiny.lds`/`dadao-node.lds` 由 testcases 落地。
- `README.md` Machine 行版本陈旧（0.3.0 vs 册头 `0.3.2-rc`），非本任务范围。
**收尾**：reviewer 第 1 轮判决 **Accepted**（2026-11-03）；任务书状态置 `已验证`，本行仅记收尾结论，不改既有完成区/审阅原文。

## 审阅记录

#### 第 1 轮 engineer 自审

自主逐行审查 10 个改动文件与证据脚本；判决：**无未修 finding**（F4 为判据改判、F7 为显式延后）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书 Node VA 末址 `0x027f_ffff_ffff` 与「L1 `0x1000`–`0x1003` 4×512 MiB」不自洽（该区间实为 1024 超页 = 512 GiB） | ✅已修 | 按 `index<<29` 独立重算为 `0x0200_7fff_ffff`，同步 spec / ADR-0039/0040/0043 / contract-elf / 本任务书 | `assert` 新增「超页数=4」「VA 覆盖=2 GiB」PASS |
| F2 旧稿 Tiny `cfx_umon`/`user`/`trap` 移交与用户最终口径冲突 | ✅已修 | Tiny = 无任何 cfx、普通跳转、不能进入 `user`、`trap` 仅 semihosting；§3/§4.1/§5 补口径 | `Tiny.cfx=无`、`Tiny.不能进入 user` PASS |
| F3 `contract-elf`「`PT_LOAD` 落 BootROM ⇒ 加载错误」与 picolibc A（crt 在 ROM）冲突 | ✅已修 | 加 Tiny ROM stub 例外；Node VA→PA 加 profile 限定（`QEMU-080t` 落地） | `check-spec-refs` / `check-spec-drift` rc=0 |
| F4 `Machine-v5` 已发布历史段（0.3.0/0.2.1）含旧几何字面量；「全文清零」会重写历史 | ❌不修（改判据） | 断言限定「正文 + `0.3.2-rc`」；另断言 `0.3.0` 段与 HEAD 逐字节一致 | `已发布历史未改` PASS |
| F5 证据脚本初版 stale-token 断言误传第 4 个位置参数 ⇒ 恒 FAIL | ✅已修 | 改为 3 参（`expected=False` + actual 布尔） | 77/77 PASS |
| F6 worktree 无 `运行期临时目录`/`运行期安装根` ⇒ 85 条假悬空 + 工具链缺失 | ✅已修（环境） | 符号链接指向主工作树（git 忽略、不入库），README 记录 | `check-knowledge-refs` rc=0；L1 仅剩基线 `check-patch-tree` |
| F7 Node 入口/SP 未写死具体值 | ⏸延后 | spec 只固定「须落在页表 VA 区间内」；首版值交 `QEMU-080t` 实测校准 | 本任务书 §测试侧约束注记 |

#### 第 1 轮 reviewer 验收

**重跑记录（独立执行，命令自身 rc）**：`运行期证据脚本（已清理，未归档）` → `RUN_EXIT=0`：断言 **77/77**（`合计 77 项，失败 0 项`）、**9/9 spec 门控 rc=0**（readonly/refs/drift/changelog/numbering/cite-targets/purity/knowledge-refs/milestones-fresh，逐条见 `gate-*.log` 尾行）；L1 `make -k check` **rc=2**，失败目标集合 = `check check-patch-tree` ⊆ `baseline-L1.txt`（主树独立复现 `make -s check-patch-tree` → `rc=2`、28 problem，gem5 补丁树 vs 共享 `组件源树`，**非本任务**）；L2 独立重跑 `make -k check-modules` → **rc=0**、`module checks (L2): PASS`。与工程师 `run-full.out` 逐行 diff 一致（仅 `RUN_EXIT` 行）。主树 `make -s check-knowledge-refs` → **rc=0**（验收标准 7 两侧 PASS）。

**独立反例注入（与 engineer 两处均不同）**：注入 Node VA 末址 `0x0200_7fff_ffff`→`0x027f_ffff_ffff` → **rc=1**，`FAIL Node.VA区间` + `FAIL 锁.sha256`；`cp` 备份 + `md5sum -c` 还原 → 回绿 **77/77 rc=0**（全程未用 `git checkout/restore/stash`）。另重跑 engineer `run.sh --inject` → `INJECT_RUN_EXIT=0`，2/2「注入⇒FAIL、还原⇒回绿」。

**约束核验（逐条）**：① Tiny（高 6 位 `0x3F`、无 cfx/无 user、允许 semihosting、BootROM 64 KiB、SRAM 8 MiB、raw `0xffff_ff01_0000`+`0x100` 零+entry `0xffff_ff01_0100`、SP `0xffff_ff7e_ff00`、ELF crt 在 ROM）与 Node（4 MiB BootROM、2 GiB RAM、4×512 MiB 超页、PTW/hypv、`SPF=0xFF`）逐句读过 §1/§1.1/§2/§3/§5/§6，**全中**；② Node VA 末址**独立重算** `0x1000<<29=0x0200_0000_0000`、`(0x1003<<29)+512MiB−1=0x0200_7fff_ffff`、覆盖 2 GiB/4 超页（旧值 `0x027f_ffff_ffff` 实为 512 GiB/1024 超页）**自洽**；③ 旧 `0xFC00_0000_0000`/16 MiB/256 KiB/双映射/PA 0 别名仅存于 `0.3.0` 已发布历史段（允许），正文+`0.3.2-rc` 清零，SEE 全文无 `256 KiB`/`fffc_0000`/「不设 SRAM」；④ DADAO-12 diff 仅 §2.1（`@@ -70/-74`）+ `0.7.3-rc`（`@@ -970/-974`），**§5 逐字节未变**（sha `13d1c7ff…` 相等）、`0.7.2` 及更早一字不动；⑤ 锁 diff 仅两册块，两册 `sha256sum` 与锁逐字相等（`002e1012…`/`2ae94664…`），注记含日期+授权原话；⑥ ADR-0004/0039/0040/0043 修订逐条、`rev. 2026-11-02`、用户原话在文，**无新 ADR**（untracked=0）；⑦ contracts 两册最小同步、无越界；⑧ 改动 11 文件全在授权范围，`tests/tools/Makefile/spec-README/archive` 命中 0，`git diff -U0` 无 `+/−` 标题行（27/27、35/35），完成区 **17 行 ≤30**，无 `*_tmp/_gate/*.orig/*.rej` 残留，快照对账 `WT_STATUS==快照`、主树 status=0 行、md5 全 OK。

**发现（非阻断，交 architect 收尾处置）**：F1 `check_spec_183t.py:92` `Tiny.raw_base+0x100=entry` 期望/实际均为脚本常量（`hex(entry)` vs `hex(raw+0x100)`）——**恒真**、不读正文；其语义已由 `Tiny.装载约定:*` 字面量断言覆盖（注入两处同改 ⇒ FAIL 实证），建议改为从 §6 解析或删除。F2 `Tiny.装载约定:*` 为文件级 token 匹配：仅改 §6 保留 `0.3.2-rc` 旧值并同步锁 ⇒ 77/77 仍 PASS（实测），断言粒度不能发现「§6 与变更记录互相矛盾」。F3 主树 `make -s check-milestones-fresh` **rc=2**（`L18 TESTCASES-091t 2026-11-03 00:01 应排在 L17 SPEC-183t 21:35 之前`）——由**已合入 master 的 `TESTCASES-091t`** 行序引入，非本任务（本 worktree rc=0）；合并时需主会话调整行序。

**判决：Accepted**（验收标准 1–8 在本人重跑下全部达成，硬约束无违反；F1–F3 为脚本粒度/并发台账问题，不构成本任务阻断）。
