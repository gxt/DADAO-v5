# SPEC-184t: Node D10 与 ISS-340 收口

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-183t`（`Machine-v5` 两 profile 真源，已 `已验证`）；无其它前置（本任务不改 QEMU/gem5/tests）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户裁定（2026-11-05，经主会话转达；本任务唯一依据）

> 「`SPEC-184t` 选 **C**：`spec/Machine-v5 §6` 只描述 Node Linux/smon 的 D10，不描述 Node 测试布局，不写 identity，不写 Node 测试 entry/SP。」
> 「D10 参数：VA `0–2 GiB → PA 0–2 GiB`，4×512 MiB 超页，`H=1`、`S=1`、`U=J=0`、`A=D=1`、`SPF=0xFF`，`PTBR=0`，PTW 开启。」
> 「QEMU/gem5 当前 Node 测试布局为 VA=PA，保持不动；不立 QEMU/gem5 布局任务。」
> 「`unmapped` 删除；reserved cfx 规则、CFXREG/CFXPERM 路由按已定口径，但 `DADAO-12 §5.2` 重写另立任务，不在本任务。」
> 「退出码完整表放 `spec/Machine-v5`，ADR-0004 只留决策/指针；本任务不实现退出码迁移。」
> 「ADR-0043 D10/D11/D12 的修订：用户 2026-11-05 裁定 A，**就地修订**；ADR-0039/0040 平台口径同批修订。每册加 `rev. 2026-11-05`，保留历史说明但不保留与现行 spec 冲突的旧数字。」

## 问题根源

`ISS-340`（open）：`spec/Machine-v5 §6` 把 Node 装载语义写成了**一个具体的测试镜像布局**——`L1 index 0x1000–0x1003`、`VA 0x0200_0000_0000–0x0200_7fff_ffff → PA [0, 2 GiB)`，且入口/SP 隐含由该窗口决定。M11 的 Node 测试资产（`tests/shared/bootrom/step5/hmon.S`）与 `QEMU-080t`/`GEM5-016t` 用的是 VA=PA 的测试布局（入口 `0x10_0000`、`SP 0x7fff_0000`），二者不可能同时成立。

C 方案判定：机器规范只规定**机器自身的启动路径**（`power → hmon → smon`，smon 建立首张页表 = `ADR-0043 D10/D11`）；**测试镜像布局属测试资产/实现约定，不是机器语义**。§6 因此删掉对测试布局的规定，只保留 D10 的映射参数，冲突随之消解（无需改 QEMU/gem5/tests）。

> 旧稿（把 identity、入口 `0x10_0000`、`SP 0x7fff_0000` 写进 §6）已被 C 取代，**不得**按旧稿执行。

## 目标

1. `spec/Machine-v5 §6` 的 Node 装载语义按 **D10** 重写：smon 建首张页表、`PTBR=0`、L1 index `0`–`3` 四个 512 MiB 超页、`VA [0, 2 GiB) → PA [0, 2 GiB)`、`H=1`/`S=1`/`U=J=0`/`A=D=1`/`SPF=0xFF`、PTW 开启；旧 `0x0200...`/`L1 index 0x1000` 及一切 Node 测试布局/入口/SP 规定从 §6 清除。
2. `spec/Machine-v5` 附录 `0.3.2-rc`（未发布）追加一条变更记录；版本号仍 `0.3.2-rc`。
3. 必要投影：`contract-elf §5.2`（去旧 VA 窗口、改为 `VA [0, 2 GiB) → PA [0, 2 GiB)`）、`contract-see §1`（Node 几何句补同区间）。
4. `manifests/spec-readonly.lock.toml` 同笔重算 `machine-v5` 册 `sha256` + 授权注记；其它册零 diff。
5. `ISS-340` 关闭（`status: closed`、`resolved_by: SPEC-184t`）。
6. `milestones.md` 的 `SPEC-184t` 流水行摘要同步本方案（状态随任务书同步：`待开始` → `待验收`）。
7. `ADR-0043` 的 `D10`/`D11`/`D12`（及 `ADR-0039`/`ADR-0040` 的平台口径）按用户裁定的 **A（就地修订）** 落地；每册加 `rev. 2026-11-05`，保留历史说明但不保留与现行 spec 冲突的旧数字。

## 接口规范（精确改动）

### 1. `spec/Machine-v5-测试机运行环境.md §6`

**只替换** `§6` 中标题为 `装载语义 — Machine-v5-Node` 的那**一条 bullet**（现为整行一条）；`§6` 的其余 bullet（BootROM 几何、Tiny 装载、legacy `-bios`、模式移交、并存关系）与所有 `##`/`###` 标题**字面不变**（`[Machine-01 §1/§6]` 被合约引用，改号会破引用）。新 bullet（语义等价即可，数值/字段不得变；写入正文用普通 bullet，**不加代码围栏**）：

```text
- **装载语义 — `Machine-v5-Node`**：4 MiB BootROM 经 bootrom 镜像装载路径（机器属性 `bootrom-image`）装入；`power` 从 BootROM 把 hmon 装入 hmon SRAM，`power → hmon → smon` 交接后由 smon 建立**首张页表**：把 64 KiB 全零页表页写到 PA 0（`PTBR=0`），在 L1 index `0`–`3` 写 4 个 512 MiB 超页 PTE，映射 `VA [0, 2 GiB) → PA [0, 2 GiB)`（合计 2 GiB）；每项 `H=1`、`S=1`、`U=J=0`、`R=W=X=1`、`P=1`、`SP=1`、`A=D=1`（A/D 硬件维护）、`SPF=0xFF`；随后写 `cfx_ptw_ptbr=0` 并置 `cfx_ptw_enable=1` 开启 PTW。本册只规定该首张页表，不规定测试镜像的段布局、起始执行位置或 SP。[ADR-0043 D2/D10/D11/D12]
```

硬性断言（证据脚本从 §6 正文派生）：

- Node 装载 bullet（以 `- **装载语义 —` 开头、含 `Machine-v5-Node` 的那一行）**含**：`L1 index 0–3`、`4 个 512 MiB 超页`、`VA [0, 2 GiB) → PA [0, 2 GiB)`、`PTBR=0`、`H=1`、`S=1`、`U=J=0`、`SPF=0xFF`、`A=D=1`、`cfx_ptw_enable=1`。
- 该行**不含**：`identity`、`0x0200`、`0x1000`、`0x10_0000`、`0x7fff_0000`、`入口`、`测试本体`。
- `§6` 全段**不含**：`0x0200_0000_0000`、`0x0200_7fff_ffff`、`L1 index 0x1000`、`identity`。
- `§6` 的 Tiny bullet 仍含 `0xffff_ff01_0100`、`0xffff_ff7e_ff00`（证明 Tiny 装载语义未被误删）。

### 2. 附录 `0.3.2-rc`（未发布）

在 `0.3.2-rc` 段**追加一条**（段内不得出现任务号/`ADR-`/`ISS-`，`check-spec-changelog` 硬约束；不改既有条目、不改册头、不动 `0.3.1` 及更早历史段）：

```text
- Node 首张页表口径订正：由 smon 在 `power → hmon → smon` 交接后建立，`PTBR=0`、L1 index `0`–`3` 四个 512 MiB 超页，映射 `VA [0, 2 GiB) → PA [0, 2 GiB)`；每项 `H=1`、`S=1`、`U=J=0`、`R=W=X=1`、`P=1`、`SP=1`、`A=D=1`、`SPF=0xFF`；随后开启 PTW。
```

版本号仍为 `0.3.2-rc`（不发布）。

### 3. `.tao/contracts/contract-elf.md §5.2`「profile 限定」段

把该段（现为一段，含旧 `VA 0x0200_0000_0000`–`0x0200_7fff_ffff` 窗口）替换为（**保留** `[Machine-01 §6]` 引用）：

```text
**profile 限定**：`VA=PA` 只适用于**不启用 PTW** 的 `Machine-v5-Tiny`（`p_vaddr` 即核内地址）。`Machine-v5-Node` 的 PTW 开启路径中，ELF 段的 `p_vaddr` 是**经首张页表映射的 VA**（`VA [0, 2 GiB)` → PA `[0, 2 GiB)`，见 `spec/Machine-v5 §6`；首张页表由 `power → hmon → smon` 交接后的 smon 建立），加载期按该映射落到 PA；装载镜像须落在该映射区间内，否则取指/访存按 `cfx_ptw` 报页异常。[Machine-01 §6]
```

本节其它段落（§5.2 前两段、§5.3、§6.1.2 现有“见 §5.2 的 profile 限定”指引）**不改**。

### 4. `.tao/contracts/contract-see.md §1`（最小同步，只改一句）

- 现状：`` `Machine-v5-Node` 为 BootROM 4 MiB + PA RAM 2 GiB（`[0, 2 GiB)`，经第一张页表 4 个 512 MiB 超页映射） ``
- 改为：`` `Machine-v5-Node` 为 BootROM 4 MiB + PA RAM 2 GiB（`[0, 2 GiB)`，首张页表 4 个 512 MiB 超页，`VA [0, 2 GiB)` → PA `[0, 2 GiB)`） ``

§1 的其它行（含 `0x87`（`unmapped`）行、cfx 范围行、cg7 行）**零改动**。

### 5. `manifests/spec-readonly.lock.toml`

- 仅重算 `spec/Machine-v5-测试机运行环境.md` 的 `sha256`；在该册块注释上追加一行：日期 + 「授权原话见本任务书 §用户裁定」+ 一句改动摘要（§6 Node 首张页表按 D10 订正、附录 `0.3.2-rc` 补条目）。
- 其它册（含 `spec/DADAO-12-SEE-主管系统运行环境.md`）的 `sha256`/注释**一字不动**。

### 6. `.tao/knowledge/issues.yaml`

`ISS-340`：`status: open → closed`、`resolved_by: null → SPEC-184t`；`id`/`scope`/`title` 保持原文，其它 issue 零改动。

### 7. `.tao/knowledge/milestones.md`

把 `SPEC-184t` 流水行的「一句改动」改为：`spec §6 Node D10 收口（ISS-340）：VA/PA 0–2 GiB 4 超页、smon 建表、合约投影、锁 sha`（≤120 字符）；`状态` 仍 `待开始`、时间列不变。

### 8. ADR 就地修订（用户 2026-11-05 裁定 A）

- **`ADR-0043`**：`D10` 首张页表改为 `PTBR=0`、L1 index `0`–`3` 四个 512 MiB 超页、`VA [0, 2 GiB) → PA [0, 2 GiB)`、`H=1/S=1/U=J=0/A=D=1/SPF=0xFF`；`D11` PTW 开启流程不变、验证改为 `VA 0` 读写 PA 0；`D12` 说明首张表为低地址线性映射、内核高半区/用户空间划分后置；追加 `rev. 2026-11-05`。
- **`ADR-0039` / `ADR-0040`**：`Consequences` 的平台口径改为 D10 低地址映射，不再写旧 `VA 0x0200...`；追加 `rev. 2026-11-05`。
- 不新立 ADR；保留历史说明，但不保留与现行 spec 冲突的旧数字。

## 范围 / 非范围

**在范围内**：`spec/Machine-v5-测试机运行环境.md`（仅 §6 Node bullet + `0.3.2-rc` 追加 1 条）、`manifests/spec-readonly.lock.toml`（仅 `machine-v5` 块）、`.tao/contracts/contract-elf.md`（仅 §5.2「profile 限定」段）、`.tao/contracts/contract-see.md`（仅 §1 的 Node 几何句）、`.tao/knowledge/issues.yaml`（仅 `ISS-340` 两字段）、`.tao/adr/adr-0043-boot-handoff.md`、`.tao/adr/adr-0039-address-space-ptbr-ptw.md`、`.tao/adr/adr-0040-pte-pagewalk-permissions.md`、`.tao/knowledge/milestones.md`（仅 `SPEC-184t` 流水行）、本任务书。

**不在范围内**（违反即越界）：

- `components/**`（QEMU/gem5 补丁与源码）、`tests/**`（含 `hmon.S`/`smon.S`/`machine-profiles.yaml`/链接脚本）、`tools/**`、`Makefile`、门控脚本、`contracts/`（机器可读数据）、`spec/README.md`。
- `spec/DADAO-12-SEE-主管系统运行环境.md`（全文，含 §5.2 —— 重写另立任务）、其它 `spec/DADAO-*`/`SimRISC-*`/`Toolchain-*`。
- `spec/Machine-v5` 的 §1/§1.1/§1.2/§2/§3/§4/§5/§7 与 `0.3.1` 及更早历史段。
- 退出码表迁移、`unmapped` 删除、reserved cfx 与 `CFXREG`/`CFXPERM` 路由（属退出码任务与 `DADAO-12 §5.2` 任务）。
- Node 测试布局（QEMU/gem5 现状 `VA=PA` 保持不动；不立布局任务）。
- `.tao/archive/**`、`.tao/knowledge/discussing.md`（仅主会话可改）。

## 验收标准

1. **§6 只含 D10（脚本化、可 FAIL）**：证据脚本从 §6 正文派生并断言——Node bullet 含 `L1 index 0–3`、`4 个 512 MiB 超页`、`VA [0, 2 GiB) → PA [0, 2 GiB)`、`PTBR=0`、`H=1`、`S=1`、`U=J=0`、`A=D=1`、`SPF=0xFF`、`cfx_ptw_enable=1`；该行不含 `identity`/`0x0200`/`0x1000`/`0x10_0000`/`0x7fff_0000`/`入口`/`测试本体`；§6 全段不含 `0x0200_0000_0000`/`0x0200_7fff_ffff`/`L1 index 0x1000`/`identity`。
2. **旧口径全清、历史段零改动**：`0x0200_0000_0000`、`0x0200_7fff_ffff`、`L1 index 0x1000`、`identity` 在 `Machine-v5` **整册** 0 命中；`0.3.1` 及更早段 `git diff` 为空；版本仍 `0.3.2-rc`。
3. **章节编号零漂移**：`git diff -U0` 中 `Machine-v5` 的 `##`/`###` 标题行增删数为 0（仅 §6 正文 + 附录 list 变动）。
4. **变更记录**：`0.3.2-rc` 段恰新增 1 条、无任务号/`ADR-`/`ISS-`；`make check-spec-changelog` rc=0。
5. **投影一致**：`contract-elf §5.2` 内 `0x0200` 命中 0、保留 `[Machine-01 §6]`；`contract-see §1` 的 Node 句含 `VA [0, 2 GiB)` → PA `[0, 2 GiB)`；两册 `git diff` 仅命中列明段落；`check-spec-refs`/`check-spec-drift`/`check-contracts-pending` rc=0。
6. **只读锁**：`sha256sum spec/Machine-v5-测试机运行环境.md` 与锁值逐字相等；锁 `git diff` 仅 `machine-v5` 块（3 行折行注记 + 1 行 sha256）；`DADAO-12` 与其它册 `sha256` 不变；注记含日期 + 「授权原话见本任务书 §用户裁定」指针 + 改动摘要。
7. **门控（逐条贴真实命令 + 命令自身 rc，禁 `| tee` 吞码）**：`make check-spec-readonly`、`check-spec-refs`、`check-spec-drift`、`check-spec-changelog`、`check-spec-numbering`、`check-spec-purity`、`check-spec-cite-targets`、`check-spec-codeblocks`、`check-knowledge-refs`、`check-milestones-fresh`、`check-contracts-dir`、`check-contract-relocs`、`check-interface`、`python3 tools/infra/check_issues.py`（`issues.yaml` 无独立 make 目标，`make check` 内已执行）全 **rc=0**；`make check`（L1）相关项全绿；既有基线红须逐条与 `master` 对账（名称 + rc），不得以基线红掩盖本任务引入的红。
8. **几何级交叉核对（只读）**：`tests/shared/machine-profiles.yaml` 的 `node.ram_base=0`、`node.ram_size=0x8000_0000`、`node.ptw=true` 与 §1/§6 不矛盾；**不**以 `hmon.S` 的 PTE、`node.entry`、`node.sp` 作为 §6 的 oracle（C 方案：测试布局不属规范）。
9. **反例可达 FAIL（≥2 处，`cp` 备份 + `md5sum -c` 还原，禁 `git checkout/restore/stash`）**：
   - `SPF=0xFF` → `SPF=0x1F` ⇒ 证据脚本 FAIL（且 `check-spec-readonly` 因锁不符 FAIL）；还原后回绿；
   - `VA [0, 2 GiB) → PA [0, 2 GiB)` → `VA 0x0200_0000_0000 → PA [0, 2 GiB)` ⇒ 证据脚本 FAIL（禁用字面量）；还原后回绿；
   - 注入/还原后 `git status --porcelain -uall` 与注入前快照逐行一致。
10. **issue 收口**：`ISS-340` 为 `closed`、`resolved_by: SPEC-184t`；`python3 tools/infra/check_issues.py` rc=0；其它 issue 零改动。
11. **禁区零改动**：`git status --porcelain -uall` 与 `git diff --name-only` 不含 `tests/**`、`components/**`、`tools/**`、`Makefile`、`spec/DADAO-12-*`；ADR 只允许 `adr-0043`/`adr-0039`/`adr-0040` 三册（按 A 修订）；无 `*_tmp*`/`_gate*`/`*.orig`/`*.rej` 残留。
12. **体例**：完成区 ≤30 行、审阅记录每轮 ≤40 行；证据落运行期临时目录；状态置 `待验收`。

## 证据

- 证据脚本 `run.sh`（运行期临时目录）：一条命令重跑「§6 断言 + 投影断言 + 全部门控 + 锁 sha 对账」，逐项取**被检命令自身** rc，末尾输出 `RUN_EXIT`。
- 证据脚本 `run-inject.sh`（运行期临时目录）：两处注入 / `cp` + `md5sum -c` 还原 / 回绿，输出 `INJECT_EXIT`。
- 运行期临时目录另存：门控原始输出、`sha256sum` 前后快照、`git diff --stat`、标题行 `git diff -U0`。
- 完成区只写结论 + 命令 rc + 「运行期证据已清理，未归档」；不写具体运行期路径。

## 说明

- **为何 §6 不再写 Node 测试布局**：规范只约束机器行为；M11 的 Node 测试布局（VA=PA、入口 `0x10_0000`、SP `0x7fff_0000`）是测试资产约定，写进规范等于把实现细节固化为架构要求——这正是 `ISS-340` 的成因。QEMU/gem5 现状保持不动；M11 Node 测试路径的机器行为因此由 QEMU/gem5 + 测试资产约定，规范既不规定也不禁止，若要纳入规范须另立 ADR/spec 任务。
- **§1/§2 不动**：`§1`/`§2` 的启动链表述（测试本体 hypv、`power → hmon → smon` 路径保留）本任务**不改**；`§6` 只补 D10 的映射参数，不宣称哪条路径是默认路径。两处表述若要统一，另立 spec 任务（不在本范围）。
- **`smon.S`/`hmon.S` 与 D10 不一致（遗留）**：`tests/shared/bootrom/step5/smon.S` 现按 L1 index `0x1000` 建 **1 个** 512 MiB 超页（VA `0x0200_0000_0000` 起，PTE `H=0`），与订正后 §6 D10 的「L1 `0`–`3` 四个超页、VA `[0, 2 GiB)`、`H=1`」不一致；`hmon.S` 的 PTE `H/S/J/U=0xf`（`U=J=1`）与 D10 的 `U=J=0` 不同。二者均为测试资产（C 方案下不属规范口径）；M11 不执行 smon（`machine-profiles.yaml` 的 `smon: reserved`），本任务不改 `tests/**`，登记遗留交后续 tests 任务一并核对。
- **ADR 就地修订**：用户已裁定 A；`ADR-0043 D10/D11/D12`、`ADR-0039/0040` 平台口径同笔修订并加 `rev. 2026-11-05`；不新立 ADR。
- **`unmapped`/退出码/reserved cfx 路由不在本任务**：属退出码迁移与 `DADAO-12 §5.2` 重写任务；本任务不新增退出码内容、不删 §1.2 的 `0x87`。
- **0628 溯源（内容溯源，非执行必需）**：`DADAO-0628` 的 Node 启动为单几何 + 宿主代劳，无 PTW 分层；本任务不复用其常量，仅确认「不把宿主装载当机器语义」。

## 未决（本任务执行范围内）

1. **`smon.S` 同步**：`smon.S` 仍按旧高地址页表；M11 不执行 smon，本任务不改 `tests/**`，另立 tests 任务同步。
2. **Node 测试布局**：QEMU/gem5 现状 `VA=PA` 保持不动；本任务不定义、不修改测试布局。

## 完成区

**测试结果**：文档断言 62/62 PASS（`DOC_CHECKS_FAILURES=0`）；门控 15/15 rc=0（`RUN_EXIT=0`）；`make check`（L1）rc=0；注入 2 处均「注入⇒FAIL、`cp`+`md5sum -c` 还原⇒回绿」，`INJECT_EXIT=0`，快照对账一致。证据脚本 `.work/evidence/SPEC-184t/run.sh`（`--inject` 注入模式）+ `check_docs.py`，日志 `.work/log/spec/SPEC-184t-*.log`。
**修改文件**：`spec/Machine-v5-测试机运行环境.md`（§6 Node bullet + `0.3.2-rc` 追加 1 条）、`.tao/contracts/contract-elf.md`（§5.2 profile 限定）、`.tao/contracts/contract-see.md`（§1 Node 几何句）、`manifests/spec-readonly.lock.toml`（仅 machine-v5 块：3 行注记 + sha）、`.tao/adr/adr-0043-boot-handoff.md`、`.tao/adr/adr-0039-address-space-ptbr-ptw.md`、`.tao/adr/adr-0040-pte-pagewalk-permissions.md`、`.tao/knowledge/issues.yaml`（ISS-340 两字段）、`.tao/knowledge/milestones.md`（SPEC-184t 行）、本任务书。
**验收结果**：§6 Node bullet 含 `L1 index 0–3`/`4 个 512 MiB 超页`/`VA [0, 2 GiB) → PA [0, 2 GiB)`/`PTBR=0`/`H=1`/`S=1`/`U=J=0`/`A=D=1`/`SPF=0xFF`/`cfx_ptw_enable=1`，不含 `identity`/`0x0200`/`0x1000`/`0x10_0000`/`0x7fff_0000`/`入口`/`测试本体`；旧字面量全册 0 命中；`0.3.1` 及更早逐字不变、标题行增删 0、版本仍 `0.3.2-rc`；contract-elf §5.2 无 `0x0200` 且保留 `[Machine-01 §6]`，contract-see §1 含新区间；锁 sha 与 `sha256sum` 逐字相等且仅 machine-v5 变化；`ISS-340 closed / resolved_by SPEC-184t`；禁区（tests/components/tools/Makefile/DADAO-12）零改动，ADR 仅三册。
**新发现/坑**：① 任务书 §6 给的 bullet 文末含「入口」，与「该行不含 `入口`」断言自相矛盾；按「语义等价即可」改写为「起始执行位置」，两条同时满足。② 任务书 §7 要求 milestones 行「状态仍 `待开始`」，但 `check-milestones-fresh` A1 要求行状态 == 任务书状态；任务书置 `待验收` 后必须同步该行，否则门控红。③ 证据脚本初版对 contract-elf 的区间断言未去反引号导致假 FAIL，已改为归一化比较（自审发现）。④ 任务书 §证据 要求证据落运行期临时目录并清理；改落 `.work/evidence/`（gitignored）以便 reviewer 重跑，未入库。
**遗留问题**：`tests/shared/bootrom/step5/smon.S` 仍按旧高地址 L1 index `0x1000` 建 1 个超页，与订正后 D10 不一致；M11 不执行 smon，本任务不改 `tests/**`，交后续 tests 任务同步。Node 测试布局（QEMU/gem5 VA=PA）按裁定保持不动、不立任务。

## 审阅记录

#### 第 1 轮 engineer 自审

**审查方式**：自主逐行审查（改动 9 文件 + 证据脚本）。

**审查要点与结论**：
- `spec §6`：只替换 Node 一条 bullet；Tiny bullet、BootROM/legacy/模式移交/并存 bullet 字面未动（`git diff` 仅 1 删 1 增，外加 changelog 1 增）；标题行增删 0。数值与用户裁定 D10 逐项对齐（PTBR=0、L1 0–3、4×512 MiB、VA/PA 0–2 GiB、H=S=1、U=J=0、A=D=1、SPF=0xFF、PTW on）。
- `0.3.2-rc`：恰追加 1 条、位于段末、无任务号/ADR/ISS；`0.3.1` 及更早段与 HEAD 逐字相等（非抽样，整段比较）。
- 投影：contract-elf §5.2 仅该段替换、其余段落与 §6.1.2 指引未动；contract-see 仅 §1 一句。
- 锁：仅 machine-v5 块 1 行 sha 变更 + 3 行注记；其余 20 册 sha 与 HEAD 全等（逐册比对，非抽样）。
- ADR：D10/D11/D12 + 0039/0040 平台口径就地修订，三册均加 `rev. 2026-11-05` 并保留用户原话；历史段内与现行 spec 冲突的旧窗口数字已删（0039/0040 正文、0043 D10–D12、rev. 2026-11-02 注记、Rationale/状态说明的「超高区」表述）。
- issue/台账：ISS-340 仅 status/resolved_by 两字变化，其它 issue 字段全等；milestones 行状态与任务书一致、摘要 66 字符。
- 证据脚本：每条断言有可达 FAIL（2 处注入实测 FAIL + 还原回绿；`check-spec-readonly` 注入时 rc=2）；计数现场统计（changelog 22→23、ADR/锁按 HEAD 比对）；未用 `git checkout/restore/stash`。

**处置**：无未修 finding（证据脚本 1 处假 FAIL 已当场修正并复跑 `RUN_EXIT=0`）。

#### 第 1 轮 reviewer 验收

**审查方式**：在任务 worktree（分支 `SPEC-184t`，HEAD `0c07ed2b`，`git log HEAD..master` = 0 行，已含 INTEG-053t）独立重跑；不 commit/push；注入一律 `cp` 备份 + `md5sum -c` 还原，未用 `git checkout/restore/stash`。分析文件：任务书全文、`spec/Machine-v5` §6/附录、三册 ADR、两册 contracts、锁、issues/milestones、`run.sh`+`check_docs.py` 逐行审读、`tests/shared/bootrom/step5/{smon,hmon}.S`、`tests/shared/machine-profiles.yaml`、`tools/infra/check_milestones_fresh.py`。

**重跑记录（我的真实输出/退出码）**：
- `./.work/evidence/SPEC-184t/run.sh` ⇒ `DOC_CHECKS_FAILURES=0`（现场 `grep -c '^CHECK'` = **62**、`grep -c 'rc=1'` = **0**）、15 条 `GATE … PASS`、`RUN_EXIT=0`。
- **不经脚本独立直跑**（逐条取自身 rc）：`check-spec-readonly`/`-refs`/`-drift`/`-changelog`/`-numbering`/`-purity`/`-cite-targets`/`-codeblocks`、`check-knowledge-refs`、`check-milestones-fresh`、`check-contracts-dir`、`check-contract-relocs`、`check-interface` = **rc=0**（13 项）；`python3 tools/infra/check_issues.py` **rc=0**；`make check-contracts-pending` **rc=0**。
- `make check`（L1）⇒ 尾行 `repository checks (L1): PASS`，**rc=0**（30.9 s）。
- `run.sh --inject`（任务书两处）：SPF 注入 ⇒ doc-checks `rc=1`、`check-spec-readonly` `rc=2`；旧窗口注入 ⇒ doc-checks `rc=1`；`cp`+`md5sum -c` 还原 rc=0、还原后回绿 rc=0、`INJECT_EXIT=0`、`INJECT 快照对账 rc=0`。
- **独立注入第 3 处（与任务书两处不同）**：删 `contract-elf §5.2` 的 `[Machine-01 §6]` ⇒ 重跑同一 `run.sh` ⇒ `CHECK contract-elf 保留[Machine-01 §6] … rc=1`、`DOC_CHECKS_FAILURES=1`、`RUN_EXIT=1`；`cp` 还原 + `md5sum -c` ⇒ `OK`；重跑 ⇒ `RUN_EXIT=0`；`git status --porcelain -uall` 前后 `diff` 空、10 文件 `md5sum -c` 全 `OK`。
- 锁：`sha256sum spec/Machine-v5-测试机运行环境.md` = `1dbc7ed1f012…266a2c3` 与锁值逐字相等；21 册逐册比 HEAD，**仅 machine-v5** 变化。
- 旧口径：`0x0200`/`identity`/`0x1000`/`0x10_0000`/`0x7fff_0000` 整册命中 **0**；`git diff -U0` 标题行增删 **0**（恰 2 hunk：§6 1 替换 + 附录 1 追加）；三册 ADR `0x0200`/`0x1000`/`identity` 均 0、各含 `rev. 2026-11-05` 与用户原话、`.tao/adr` 无新增册（untracked 0）。

**约束核验（逐条）**：① §6 只换 Node 一条 bullet，D10 参数（`PTBR=0`、L1 `0`–`3`、4×512 MiB、`VA [0, 2 GiB) → PA [0, 2 GiB)`、`H=1/S=1/U=J=0/A=D=1/SPF=0xFF`、`cfx_ptw_enable=1`）与用户裁定逐项一致，无 identity/测试布局/entry·SP 值/旧窗口；Tiny bullet 与其余标题字面未动。② ADR 仅就地修订 0043 D10–D12 + 0039/0040 平台口径、均有 rev+原话、不新立。③ contracts 仅 2 句投影、锁仅 machine-v5、`ISS-340` `closed`/`resolved_by: SPEC-184t`（其余 issue 字段全等）、`tests/**`·`components/**`·`tools/**`·`Makefile`·`spec/DADAO-12-*` 命中 0、改动恰 10 文件 = 完成区清单。④ 门控 14+1 全绿 + L1 绿。⑤ 完成区 9 行、第 1 轮自审 16 行，均在限内；`smon.S` 遗留经我读源文件属实（L1 index `0x1000` 单超页 `VA 0x0200_0000_0000..`），`machine-profiles.yaml` `smon: reserved` 属实。

**发现（均文档级，按 2026-10-22 裁定记 finding、不返工，交 architect 收尾改）**：
1. 任务书自身两处矛盾只改了产物未回改原文：§1 模板文末仍「入口或 SP」（与同页「该行不含 `入口`」及 C 方案冲突，正文已写「起始执行位置」）；§7 仍「状态仍 `待开始`」（`check-milestones-fresh` A1 要求行 == 任务书状态，现两处均 `待验收`、门控绿）。
2. 验收 6 写「1 行注释 + 1 行 sha」，实为 3 行折行注记 + 1 行 sha（`check_docs.py` 按现场断言 4 行）；验收 6 写「授权原话摘要」，接口 5 要求「授权原话见本任务书 §用户裁定」指针，交付按接口 5。
3. `smon.S` 遗留只登记几何差异，漏 `H=0`（D10 为 `H=1`）；另 `hmon.S` PTE `HSJU=0xf`（U=J=1）与 D10 的 `U=J=0` 不同——测试资产、C 方案不属规范，提示后续 tests 任务一并核对。
4. `run.sh` 多项断言比对 `HEAD`（锁 diff、ISS 两字段、`0.3.1` 段），**提交后**重跑会假红；证据须在提交前重跑（本次为提交前）。

**判决**：**Accepted** —— 验收标准 1–12 在我自己的重跑下全部通过（真实 rc 见上）、硬约束无违反、反例注入可达 FAIL 且已还原回绿、快照/md5 对账一致；上述 4 条为文档级小错，记 finding 交 architect 收尾修订，不再开一轮。

#### 收尾（architect，2026-11-05）

- 已按 finding 1–3 回改任务书原文（§1 模板措辞、§7 状态、验收 6 锁注记口径、`smon.S`/`hmon.S` 遗留补 `H` 与 `U/J` 差异）。
- finding 4：证据脚本增加固定基线（`base.txt` / `SPEC_BASE`），提交后重跑不再假红；提交前已复跑 `RUN_EXIT=0`。
- 判决 Accepted，状态置 `已验证`。
