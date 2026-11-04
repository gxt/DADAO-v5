# SPEC-184t: Node identity 与 ISS-340 收口

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-183t`（`Machine-v5` 两 profile 真源）、`QEMU-080t`（Node identity 实现与现场）、`GEM5-016t`（Node identity FS 实现与现场）、`TESTCASES-092t`（`machine-profiles.yaml`/`hmon.S` 资产口径）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

`ISS-340`（open）：`spec/Machine-v5 §6` 的 Node 装载语义仍写旧页表口径——`L1 index 0x1000–0x1003`、`VA 0x0200_0000_0000–0x0200_7fff_ffff → PA [0, 2 GiB)`。而 `QEMU-080t` 与 `GEM5-016t` 已按用户口径落地 **identity**：

- 首张页表：`PTBR=0`（PA 0 放 64 KiB L1 表），L1 index **0–3** 共 4 个 512 MiB 超页，**VA=PA `[0, 2 GiB)`**；每项 `PPN=i*0x2000`（`0`/`0x2000`/`0x4000`/`0x6000`）、`SPF=0xFF`、`HSJU=0xF`、flags `0xEF`；`ptw_enable=1`。
- 测试本体入口 `0x10_0000`、`SP=0x7fff_0000`——这两个值**只在 identity 映射下成立**；旧 `0x0200...` 窗口会把入口/SP 解释到错误的 PA。

冲突已在 `QEMU-080t`/`GEM5-016t` 登记为 `ISS-340`，两任务均按用户口径实现 identity、**未改 `spec/`**。本任务只订正规范侧（及必要投影），把 `ISS-340` 关闭；不改 QEMU/gem5/tests/tools 的实现或资产。

## 用户口径（本任务依据）

用户已明确（经主会话转达，2026-11-03/04）：

> 「Node 入口/SP 为 identity：entry `0x10_0000`、SP `0x7fff_0000`；L1 index `0–3`，4×512 MiB 超页覆盖 VA `0–2 GiB`，`SPF=0xFF`。」

可溯源落点：`QEMU-080t` 任务书 §现状 4 / §2；`GEM5-016t` 任务书 §1/§说明 1；`TESTCASES-092t` §2；`tests/shared/bootrom/step5/hmon.S` 的 4 个 PTE；`tests/shared/machine-profiles.yaml` 的 `node.entry`/`node.sp`；`tests/shared/linker/dadao-node.lds` 的 “VA=PA identity, PTW on”。

## 目标

1. 订正 `spec/Machine-v5 §6` 的 Node 装载语义：identity 首张页表（L1 0–3、4×512 MiB、VA=PA 2 GiB、`SPF=0xFF`）、入口 `0x10_0000`、SP `0x7fff_0000`；旧 `0x0200...`/`L1 0x1000–0x1003` 从 §6 清除。
2. 同步 `spec/Machine-v5` 附录 `0.3.2-rc`（未发布段）一条变更记录；版本号不变（仍 `0.3.2-rc`）。
3. 同步必要投影：`contract-elf §5.2`（Node VA→PA 装载）、`contract-see §1`（Node 首张 identity 页表一句）、`ADR-0039`/`ADR-0040` 的**平台口径**、`ADR-0043` 的 `D10`/`D11`/`D12` 适用范围（见 §接口规范）。
4. 同笔重算 `manifests/spec-readonly.lock.toml` 的 `Machine-v5` `sha256` 并写授权注记；`DADAO-12` 及其它册不动。
5. `ISS-340` 关闭（`status: closed`、`resolved_by: SPEC-184t`），证据脚本与门控全绿。

## 接口规范（精确改动）

### 1. `spec/Machine-v5-测试机运行环境.md` §6

保持所有 `##`/`###` 标题与编号不变（`[Machine-01 §1/§6]` 被合约引用）。把 `§6` 的 Node 装载语义 bullet 替换为（语义等价即可，数值/字段不得变）：

```
- **装载语义 — `Machine-v5-Node`**：4 MiB BootROM 经 bootrom 镜像装载路径（机器属性 `bootrom-image`）装入；power 从 BootROM 把 hmon 装入 hmon SRAM，并在移交前设 `SP = 0x7fff_0000`。M11 测试路径由 hmon 建立**首张 identity 页表**：`PTBR=0`（PA 0 放 64 KiB L1 表），L1 index `0`–`3` 共 4 个 512 MiB 超页（合计 2 GiB），**VA=PA** 覆盖 `[0, 2 GiB)`；每项 `HSJU=0xF`、`SPF=0xFF`、PPN `i*0x2000`（`i=0..3`）、flags `0xEF`（`P/SP/D/A/G/X/W/R` 全 1），A/D 硬件维护；置 `cfx_ptw_enable=1` 后，测试本体在 hypv 运行，入口 `0x10_0000`。测试镜像的 `PT_LOAD`、入口与 `SP` 均须落在这张 identity 页表覆盖的 VA=PA 区间（`[0, 2 GiB)`），否则取指/访存按 `cfx_ptw` 报页异常。`power → hmon → smon` 保留路径的内核高半区页表不在 M11 测试路径。[ADR-0043 D2/D10/D11/D12]
```

硬性断言（脚本从正文派生）：

- §6 出现 `L1 index `0`–`3``（或等价 `0–3`）、`4 个 512 MiB 超页`、`VA=PA`、`[0, 2 GiB)`、`SPF=0xFF`、`PTBR=0`、`entry 0x10_0000`、`SP = 0x7fff_0000`。
- §6 **不再出现** `0x0200_0000_0000`、`0x0200_7fff_ffff`、`L1 index 0x1000`、`0x1000`–`0x1003`。
- `§1.1`/`§1.2`/`§2` 的 Node 几何（4 MiB BootROM、PA RAM 2 GiB、PTW/hypv、smon 保留）**不动**；如措辞必须微调，只允许最小字面调整并在完成区逐条说明。

### 2. 附录 `0.3.2-rc`（未发布）

在 `0.3.2-rc` 段追加一条（**不得写任务号/ADR/ISS 号**，`check-spec-changelog` 硬约束）：

```
- Node 装载语义订正：M11 测试路径的首张页表为 identity（`PTBR=0`、L1 index `0`–`3` 四个 512 MiB 超页、VA=PA `[0, 2 GiB)`、`SPF=0xFF`），测试本体入口 `0x10_0000`、`SP=0x7fff_0000`；`power → hmon → smon` 保留路径的内核高半区页表不在 M11 测试路径。
```

版本号仍为 `0.3.2-rc`（不发布、不改册头）。

### 3. `.tao/contracts/contract-elf.md §5.2`

把 “profile 限定” 段替换为（保留 `[Machine-01 §6]` 引用，`check-spec-refs` 需要）：

```
**profile 限定**：**不启用 PTW** 的 `Machine-v5-Tiny` 中 `p_vaddr` 即核内地址（VA=PA）。`Machine-v5-Node` 的 M11 测试路径启用 PTW，但首张页表为 **identity**（L1 index `0`–`3` 四个 512 MiB 超页，`VA=PA [0, 2 GiB)`，`SPF=0xFF`），故 `PT_LOAD` 的 `p_vaddr`/`p_paddr` 相等并直接落 PA；测试本体入口 `0x10_0000`、`SP=0x7fff_0000`。`power → hmon → smon` 保留路径的内核高半区映射（`VA 0x0200_0000_0000` 起）不在 M11 测试路径，其 ELF 装载口径后置。[Machine-01 §6]
```

### 4. `.tao/contracts/contract-see.md §1`（最小同步）

Node 几何句补 identity 限定，不改其它内容：

- 现状：“`Machine-v5-Node` 为 BootROM 4 MiB + PA RAM 2 GiB（`[0, 2 GiB)`，经第一张页表 4 个 512 MiB 超页映射）”
- 改为：“`Machine-v5-Node` 为 BootROM 4 MiB + PA RAM 2 GiB（`[0, 2 GiB)`，首张 identity 页表 4 个 512 MiB 超页，VA=PA）”

### 5. ADR 投影（`ADR-0043` 的 D10/D11/D12 需用户逐条确认）

- **`ADR-0039`（Proposed）**：`Consequences` 的“平台口径”改为——`Machine-v5-Node` 为 PA 2 GiB；M11 测试路径首张页表为 identity（L1 index `0`–`3`、VA=PA `[0, 2 GiB)`、`SPF=0xFF`）；`smon` 保留路径的内核高半区映射（VA `0x0200_0000_0000` 起）不在 M11。追加 `rev. 2026-11-04` 注记与用户口径原话。`D1`–`D8` 不变。
- **`ADR-0040`（Accepted）**：`Consequences` 的“平台使用”同上补 identity 限定；追加 `rev. 2026-11-04` 注记。`D1`–`D11`、PTE 格式与异常优先级不变。
- **`ADR-0043`（Accepted）**：把 `D10`/`D11` 明确为 `power → hmon → smon` **保留路径**（M11 不覆盖）；M11 测试路径由 hmon 建 identity 首张页表（数值同 §6）。`D12` 的内核高半区布局保留给后续 OS/smon 路径、不适用于 M11 测试页表。`D10` 原文 “`S=1,U=J=H=0`” 与 `DADAO-12 §2.2.3` 的 HSJU 位定义及 `hmon.S`/`GEM5-016t` 的 `HSJU=0xF` 不一致，按 `HSJU=0xF` 作**事实订正**。追加 `rev. 2026-11-04` 注记与用户口径原话；`**状态**` 行标 rev。PTE 位定义、PTW 开启语义不变。
- **不新立 ADR**。上述 `ADR-0043` 的 `D10`/`D11`/`D12` 变更属**已 Accepted 决策的修订**：开工前须由主会话把三条提案交用户**逐条确认**，确认原话写入任务书 §用户确认；未确认前不得执行 ADR-0043 改动，也不得把任务置 `待验收`（见 §未决 1）。

### 6. `manifests/spec-readonly.lock.toml`

- 仅重算 `spec/Machine-v5-测试机运行环境.md` 的 `sha256`；在 `machine-v5` 块注释追加 `2026-11-04（SPEC-184t，授权原话见任务书 §用户口径）` + 一句改动摘要。
- `spec/DADAO-12-SEE-主管系统运行环境.md` 与其它册的 `sha256`/注释**一字不动**；`DADAO-12 §5` 尤其零 diff。

### 7. `.tao/knowledge/issues.yaml`

`ISS-340` 置 `status: closed`、`resolved_by: SPEC-184t`；`title` 保留原文（可加一句“已由 SPEC-184t 订正 spec §6”），不改其它 issue。

## 范围 / 非范围

**在范围内**：`spec/Machine-v5-测试机运行环境.md`（§6 + `0.3.2-rc` 附录）、`manifests/spec-readonly.lock.toml`（仅 `machine-v5` 块）、`.tao/contracts/contract-elf.md`（§5.2）、`.tao/contracts/contract-see.md`（§1 一句）、`.tao/adr/adr-0039|0040|0043-*.md`（经逐条确认的投影/修订）、`.tao/knowledge/issues.yaml`（仅 ISS-340）、本任务书、`.tao/knowledge/milestones.md`（流水行状态）、`.work/evidence/SPEC-184t/`。

**不在范围内**（违反即越界）：

- `components/**`（QEMU/gem5 补丁与源码）、`tests/**`（含 `hmon.S`/`smon.S`/`machine-profiles.yaml`）、`tools/**`、`Makefile`、门控脚本、`contracts/`（机器可读数据）、`spec/README.md`。
- `spec/DADAO-12-SEE-主管系统运行环境.md`（全文，含 §5）、其它 `spec/DADAO-*`/`SimRISC-*`/`Toolchain-*`。
- 新立 ADR；cfxha/cfx 编号重排；QEMU/gem5 行为或测试期望值变更。
- `.tao/archive/**`（历史归档不重写）、`.tao/knowledge/discussing.md`（仅主会话可改）。

## 验收标准

1. **§6 自洽（脚本化、可 FAIL）**：证据脚本从 §6 正文派生并断言——L1 index `0–3`、`4 个 512 MiB 超页`（=2 GiB）、`VA=PA`、`[0, 2 GiB)`、`PTBR=0`、`SPF=0xFF`、`HSJU=0xF`、`flags 0xEF`、入口 `0x10_0000`、`SP=0x7fff_0000`；且 §6 不含 `0x0200_0000_0000`/`0x0200_7fff_ffff`/`L1 index 0x1000`/`0x1000–0x1003`。旧口径字面量（同前）在 `Machine-v5` **正文 + `0.3.2-rc` 段**为 0；已发布历史段（`0.3.0` 及更早）按版本记录保留、不改（另断言其 `git diff` 为空）。
2. **与实现/现场一致（只读交叉核对）**：
   - `tests/shared/machine-profiles.yaml` `node.entry=0x0000_0000_0010_0000`、`node.sp=0x0000_0000_7FFF_0000`、`node.ram_size=0x8000_0000`、`node.ram_base=0`、`node.ptw=true` 与 §6 逐项一致；
   - `tests/shared/bootrom/step5/hmon.S` 的 4 个 PTE（`0xffef`/PPN `0`/`0x2000`/`0x4000`/`0x6000`、`0xf000`）与 §6 的 `SPF=0xFF`/`flags 0xEF`/`HSJU=0xF`/PPN 规则逐位一致；
   - `tests/shared/linker/dadao-node.lds` 的 “VA=PA identity, PTW on”、`tools/infra/check_interface_alignment.py` 的 Node 断言、`components/gem5/patches/src/arch/dadao/node_*` 的 Node 常量与 §6 不矛盾；
   - `make check-interface` **rc=0**（Node 项无 `DEFERRED`）。
   - 若 `.work/evidence/QEMU-080t/` 或 `.work/evidence/GEM5-016t/` 在现场存在，追加读取其 `entry=0x10_0000`/`SP=0x7fff_0000`/`SPF=0xFF` 记录；不存在则以任务书完成区 + 上述源码/资产交叉核对为准并在证据中注明（不伪造现场日志）。
3. **门控（逐条贴真实命令 + 命令自身 rc，禁 `| tee` 吞码）**：`make check-spec-readonly`、`check-spec-refs`、`check-spec-drift`、`check-spec-changelog`、`check-spec-numbering`、`check-spec-purity`、`check-spec-cite-targets`、`check-spec-codeblocks`、`check-knowledge-refs`、`check-milestones-fresh`、`check-contracts-dir`、`check-contract-relocs`、`check-issues`、`check-interface` 全 **rc=0**；`make check`（L1）本任务相关项全绿；既有基线红须逐条与 `master` 对账（名称 + rc），不得以基线红掩盖本任务引入的红。
4. **只读锁**：`sha256sum spec/Machine-v5-测试机运行环境.md` 与锁值逐字相等；锁 diff 仅 `machine-v5` 块（注释 + 1 行 sha256）；`DADAO-12` 与其它册 `sha256` 不变；注记含日期 + 用户口径原话摘要。
5. **章节编号零漂移**：`git diff -U0` 证明 `Machine-v5` 的所有 `##`/`###` 标题行未变（仅正文/附录 list 变动）。
6. **投影一致**：`contract-elf §5.2`、`contract-see §1` 不再把 Node 的 `PT_LOAD` 指向旧 `0x0200...` 窗口；ADR 三册（若确认执行）与 §6 的 L1/VA/entry/SP/PTE 字段逐项一致；`check-spec-refs`/`check-spec-drift` rc=0。
7. **反例可达 FAIL（≥2 处，`cp` 备份 + `md5sum -c` 还原，禁 `git checkout/restore/stash`）**：
   - 把 §6 的 `SPF=0xFF` 改成 `SPF=0x1F` ⇒ 证据脚本 FAIL（并 `check-spec-readonly` 因锁不符 FAIL）；还原后回绿；
   - 把 §6 的 `SP=0x7fff_0000` 改成 `0x7ffe_0000`（或把 `L1 index 0–3` 改成 `0x1000–0x1003`）⇒ 证据脚本 FAIL；还原后回绿。
   - 注入/还原后 `git status --porcelain -uall` 与注入前快照逐行一致。
8. **issue 收口**：`ISS-340` 为 `closed`、`resolved_by: SPEC-184t`，`check-issues` rc=0；`title` 仍能检索到 `ISS-340`。
9. **归档/禁区零改动**：`git status --porcelain -uall` 与 `git diff --name-only` 不含 `.tao/archive/**`、`tests/**`、`components/**`、`tools/**`、`Makefile`、`spec/DADAO-12-*`；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留。
10. **体例**：完成区 ≤30 行；证据落 `.work/evidence/SPEC-184t/`（`run.sh`、`run.EXIT`、`*.log`）；状态置 `待验收`。

## 证据

- `.work/evidence/SPEC-184t/run.sh`：一条命令重跑“§6 断言 + 交叉核对 + 全部门控 + 锁 sha 对账”，逐项取**被检命令自身** rc；输出 `RUN_EXIT`。
- `.work/evidence/SPEC-184t/run.sh --inject`：两处注入 / `cp`+`md5sum -c` 还原 / 回绿，输出 `INJECT_EXIT`。
- `.work/evidence/SPEC-184t/*.log`：门控原始输出、`sha256sum` 前后快照、`git diff --stat`、标题行 `git diff -U0`。
- 完成区只写结论 + 命令 rc + 证据路径。

## 说明

- **规范正文与实现的关系**：本任务以已实现/已验证的 identity 为事实基准订正规范，不反向改 QEMU/gem5/tests；如发现 spec 与实现仍有第二处冲突，保留现场并登记，不静默扩大修改。
- **`tests/shared/bootrom/step5/smon.S` 仍写旧 `0x0200...`**：属 `power → hmon → smon` 保留路径（M11 不覆盖、不执行），本任务**不改**；在完成区“遗留问题”注明，避免被误读为 §6 冲突未清。
- **`D10` 的 `S=1,U=J=H=0` 与 `HSJU=0xF`**：以 `DADAO-12 §2.2.3` 位定义、`hmon.S`、`GEM5-016t` 现场为准；ADR-0043 按事实订正（需确认），spec 不复制旧措辞。
- **0628 溯源（内容溯源，非执行必需）**：`DADAO-0628` 的 Node 启动是单几何 + 宿主代劳，无 identity-PTW/4 MiB BootROM；本任务不复用其常量，仅确认“不要把宿主装载当机器语义”。

## 未决（下发前需处理）

1. **ADR-0043 D10/D11/D12 逐条确认**：`AGENTS.md`「ADR decision 逐条确认」要求已 Accepted ADR 的 decision 变更逐条确认。本任务已把三条提案写在 §接口规范 5；**主会话须在 `/dispatch` 前取得用户逐条确认并落原话**，否则 ADR 部分 BLOCKED、任务不得置 `待验收`（可先只做 spec/contracts/锁/issue，ADR 另记遗留）。
2. **`contract-see §1` 是否纳入**：本任务按“最小同步”只加一句 identity 限定；若用户认为合约不应提前于 spec 投影，可只保留 `contract-elf §5.2`，`contract-see` 留待后续同步（需在完成区说明）。
3. **QEMU-080t/GEM5-016t 现场日志缺失**：主工作树当前只有 `SPEC-183t` 证据目录；本任务按源码/资产/任务书完成区交叉核对，不要求重建 QEMU/gem5。若用户要求“现场重跑”，需另立任务并申报构建耗时。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
