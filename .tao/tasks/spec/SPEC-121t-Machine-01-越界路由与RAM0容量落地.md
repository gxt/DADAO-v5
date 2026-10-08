# SPEC-121t: Machine-01 §1 越界路由与 RAM@0 容量落地（+ Machine-01 入锁 / Process-06 同步 / 门控措辞）

**模块**：spec
**项目里程碑**：M5
**依赖**：`QEMU-049t`（**已验证**；三条实现口径的来源）、`SPEC-119t`（锁/门控机制：`manifests/spec-readonly.lock.toml` + `tools/infra/check_spec_readonly.py` + `make check-spec-readonly`）；与其它改 `spec/` 或锁文件的任务**串行**
**状态**：待开始

> **⚠️ 前置（硬约束；用户授权原话逐字落盘，2026-10-08）**：本任务将改 **`spec/`**（`spec/Machine-01-测试机运行环境.md §1` + `spec/Process-06-spec目录保护规范.md §5/§6`）**及门控措辞**（`tools/infra/check_spec_readonly.py` / `Makefile` help）。按「**所有针对 spec 目录的修改，都应该经过我的允许，不能擅自进行**」（`spec/Process-06 §2`）——须**用户事先明确允许**并将授权原话落盘；否则 **BLOCKED**。
>
> **本任务已取得的用户授权（原话，逐字）**：
> - ① 「**授权按拟改文本改（推荐）**」——把 `QEMU-049t` 审阅记录 / `ISS-166` 的**拟改文本**（3 处）落入 `spec/Machine-01-测试机运行环境.md §1`；
> - ② 「**把 Machine-01 新增进锁**」——`manifests/spec-readonly.lock.toml` **新增** `spec/Machine-01-测试机运行环境.md` 一条（architect 澄清问的选项答复）；
> - ③ 「**授权含 Process-06 同步（推荐）**」——`spec/Process-06-spec目录保护规范.md §5/§6` 相应同步（architect 澄清问的选项答复）。
> - ④ 「**确认两条，按此下发（推荐）**」——确认：① **`Machine-01` 新增进锁（20→21）**；② **授权 `spec/Process-06 §5/§6` 同步**（**2026-10-08 范围补正**）。
> - ⑤ 「**并入 SPEC-121t 一并更正**」——`tools/infra/check_spec_readonly.py` 输出与 `Makefile` help 的「**upstream read-only spec volume(s)**」**措辞**一并更正（**2026-10-08 范围补正**）。
>
> **授权范围（严格遵守，超出即 BLOCKED）**：
> - `spec/Machine-01-测试机运行环境.md` **仅 §1.1 表 RAM@0 行 1 处 + §1.2 两条（新增 1 条 + 末条改写）**；**该册其它节（`§2`–`§7`）一律禁改**。
> - `spec/Process-06-spec目录保护规范.md` **仅 §5/§6**：**锁内册清单 / 类目 / 计数**同步（`Machine-01` 移出「不在锁内」）**且语义相应扩面**——由「只保护**上游** 20 册」改为「**含 v5 自定册**（`spec/Machine-01`）」，措辞与门控输出同步为准确表述（去除「**只**覆盖上游」限定）；§1–§4/§7 除非复述计数/口径否则不改。
> - `manifests/spec-readonly.lock.toml`：**新增 `Machine-01` 一条**（+ 头注计数/说明同步）；**其余 20 册 `sha256` 逐字不动**。
> - `tools/infra/check_spec_readonly.py`：**仅措辞**（docstring / `--help` 描述 / 成功输出行）——**去除「upstream」限定**；**不改**校验逻辑（`fail-closed`）。`Makefile`：**仅 help 行（L101）+ 紧邻注释（L354）**措辞同步；**不改**目标逻辑。
> - **`spec/` 下其它册**（`SimRISC-*`/`DADAO-*`/`Toolchain-01`/`spec/README.md`）**一律不改**。
>
> **口径更正（architect 立案时实测；已由用户裁定 ② 定案）**：原拟「更新锁中**该册** `sha256`（其余 19 册不得变）」——**实测该锁不含 `Machine-01`**（20 册均为**上游只读册**；`spec/Process-06 §6` 明文「**不在锁内**：`spec/Machine-01`…」）。经用户裁定「**把 Machine-01 新增进锁**」⇒ 本任务改为**新增**该册条目（锁内 **21** 条 = 上游 20 + `Machine-01` 1），**其余 20 册零变动**（原「其余 19 册」系基于错误前提的表述，以本口径为准）。

## 执行环境
**执行环境**：本地

## 接口规范

- **定位（问题根源）**：`QEMU-049t` 按 `ADR-0020 D15` 在机器模型落地**三条实现口径**——① `umon` 段（`addr[47:42]==0`）越界访问/取指 ⇒ `CFXMEM`（`0x81`）；② 其余段（含旧 `power` 段 63）越界访问/取指 ⇒ 测试机约定 `unmapped`（`0x87`）；③ RAM@0 容量 = **16 MiB**。但 `spec/Machine-01 §1` 现行措辞**未完全覆盖**（`ISS-166`）：`§1.1` 表 RAM@0「大小」列仍是占位 `【待 QEMU-049t 定】`；`§1.2` 末条把「精确路由与 RAM@0 容量」**委派**给 `QEMU-049t`（未写口径）；`§1.2`「层次与适用」条的 `CFXMEM` 措辞按字面**也覆盖 `power` 段 63**，与已落地路由（`power` 63 ⇒ `0x87`）**歧义**。⇒ 本任务把口径**落纸**（spec 为准），并把 `Machine-01` **纳入只读锁**（用户裁定 ②）。

- **输入（自包含）**：
  - **拟改文本真源**：`.tao/tasks/qemu/QEMU-049t-RAM0双映射.md` 审阅记录「第 1 轮 architect 提交（WIP）→ Machine-01 §1 差异清单」+ `.tao/knowledge/issues.yaml` 的 `ISS-166`。
  - `spec/Machine-01-测试机运行环境.md §1`（现行三处：L25〔§1.1 表 RAM@0 行〕、L39〔§1.2「层次与适用」条〕/L42〔§1.2 末条〕）。
  - `.tao/adr/adr-0020-see-semihosting.md`（`D15`）；`spec/DADAO-12-SEE-主管系统运行环境.md §2.1`（**只读引用**，`CFXMEM` 出处）。
  - `manifests/spec-readonly.lock.toml`（20 册体例 + 头注）+ `tools/infra/check_spec_readonly.py`（`--root`/`--verbose`，**fail-closed**）+ `make check-spec-readonly`（∈ `make check`）。
  - `spec/Process-06-spec目录保护规范.md §2/§5/§6`（授权规则 + 锁机制 + 清单）。
  - **口径实证（只读）**：`tools/qemu/min_rom_probe_049t.py`（`oob_data/fetch_cfxmem` ⇒ `0x81`、`oob_data/fetch_unmapped` ⇒ `0x87`）、`tools/integ/check_interface_alignment.py`（`RAM0_SIZE=16MiB`、`EXIT_CFXMEM=0x81`、`CFXHA_UMON=0`）。

- **输出**：
  1. **`spec/Machine-01 §1.1` 表 RAM@0 行「大小」**：`【待 QEMU-049t 定】` → **`16 MiB`**（拟改文本 ①）：
     ```
     | **RAM@0（新）** | `0x0000_0000_0000` | 16 MiB | 0 / `umon` | 供 bootrom/SEE（C1 step1 双映射引入） |
     ```
  2. **`spec/Machine-01 §1.2` 新增「精确路由」条**（位于「层次与适用」条〔现 L39〕**之后**、末条〔现 L42〕**之前**；**建议紧接「层次与适用」条**；拟改文本 ②）：
     ```
     - **精确路由（`QEMU-049t` 已按 `ADR-0020 D15` 落地）**：**`umon` 段（`addr[47:42]==0`）的越界访问/越界取指 ⇒ `CFXMEM`（`0x81`）**；**其余段（含旧 `power` 段 63）的越界访问/越界取指 ⇒ 测试机约定 `unmapped`（`0x87`）**。[ADR-0020 D15]
     ```
  3. **`spec/Machine-01 §1.2` 末条**（现 L42）改为**落地陈述**（拟改文本 ③）：
     ```
     - 精确路由与 RAM@0 容量由 `QEMU-049t` 落地（`umon` 段 ⇒ `0x81`、其余 ⇒ `0x87`；RAM@0 = 16 MiB），并以 `check-interface` 断言固化。[ADR-0020 D15]
     ```
  4. **`manifests/spec-readonly.lock.toml`**：**新增** 一条（置于文件末尾）：
     ```toml
     [[spec]]
     path = "spec/Machine-01-测试机运行环境.md"
     group = "machine-01"
     sha256 = "<§1 改动后实测 sha256sum>"
     ```
     并同步**头注**：`清单 = 20 册上游只读册` → `锁内清单 = 20 册上游只读册 + 1 册 v5 自定册（spec/Machine-01）= 21 册`；头注原「注意：`spec/Machine-01`、`spec/Process-0x`、`spec/README.md` 为 v5 自定册，不在本锁内」**移除 `Machine-01`**（改为「`spec/Machine-01` 已于 2026-10-08 纳入本锁（用户授权）；`spec/Process-0x`、`spec/README.md` 为 v5 自定册，不在本锁内」）。**其余 20 册 `sha256` 逐字不动**。
  5. **`spec/Process-06 §5/§6` 同步（含语义扩面）**：§6 把「**上游只读册清单（判据，20 册）**」按实同步为**只读册清单（判据，21 册 = 上游 20 + `spec/Machine-01`）**；「**不在锁内**」注记**移除 `spec/Machine-01`**（保留 `spec/Process-0x`/`spec/README.md`）。**§5（关键）语义扩面**：由「**只保护上游 20 册**」扩为「**含 v5 自定册**（`spec/Machine-01`）」——把标题/正文中「**上游只读册哈希锁**」的「**只**覆盖上游」限定改写为**锁内只读册**（上游只读册 + `spec/Machine-01`），使规范与机制自洽（措辞去「只覆盖**上游**只读册」）。**不改变 §2**（任何 `spec/` 改动须用户事先授权）的实质。
  6. **门控措辞同步（去除「upstream」限定；用户裁定 ⑤）**：`tools/infra/check_spec_readonly.py`——把 docstring（`every upstream read-only spec volume` / `Those volumes are upstream inputs`）、`--help` 描述（`Verify upstream read-only spec volumes …`）、成功输出行（`… upstream read-only spec volume(s) OK`）中描述**锁/册**的「**upstream**」限定**去除**（如 `every read-only spec volume` / `read-only inputs` / `Verify read-only spec volumes …` / `… read-only spec volume(s) OK`）；**校验逻辑（`fail-closed`）零改动**。`Makefile` help 行（L101 `Verify upstream read-only spec volumes … (SPEC-119t)`）+ 紧邻注释（L354「上游只读册」）**同措辞同步**（去「upstream」/「上游」限定，改为「只读册」）。
  7. **投影（如含对应口径则最小同步，否则不动并说明）**：核 `.tao/knowledge/contract-see.md §1`（现仅泛述「地址划分 + RAM 基址全 0、复位向量/ROM/exit port 不变」，**未见** RAM@0 尺寸/路由明细）与 `.tao/knowledge/contract-semihosting.md`——**如实测含对应口径**（`16 MiB`/`0x81`/`0x87`）则最小同步；否则**不改**并在完成区记明（`grep` 真实输出）。
  8. **`ISS-166` 结案**：`.tao/knowledge/issues.yaml` 的 `ISS-166` → `status: closed`、`resolved_by: SPEC-121t`、`notes` 追加「已由 `SPEC-121t` 收口（用户授权 2026-10-08；`spec/` 改动仅 `Machine-01 §1` + `Process-06 §5/§6`）」。

- **约束（硬）**：
  - **授权范围内改动**（见文件头「授权范围」），超出即 **BLOCKED**：`Machine-01` 其它节、`Process-06` §1–§4/§7（除复述计数/口径外）、`spec/` 其它册、`tools/`/`Makefile` 的**逻辑**（**仅措辞**可改）**一律不改**。
  - **锁纪律**：**新增** `Machine-01` 条目 + 头注同步；**其余 20 册 `sha256` 零变动**（`git diff` 不得出现任何既有册 `sha256` 行的 `-`/`+`）。
  - **改后重算锁**：`sha256` 必须在 `Machine-01 §1` **改毕后**实测（`sha256sum`），不得沿用旧值、不得臆填。
  - **Spec-first / 口径来源**：期望值以 `ADR-0020 D15` + `QEMU-049t` 落地口径 + `check-interface` 断言为准，**不从实现反推**。
  - **不立 ADR**：属规范正文 + 过程规范的同步/扩面（可逆、单项目），不命中 `spec/Process-03` 判据（同 `SPEC-119t`/`SPEC-116t` 体例）。
  - 与其它改 `spec/`/锁文件的任务**串行**；`make check` EXIT=0。
  - 失败即停、**禁自动重试**；临时目录 `/tmp/opencode/SPEC-121t/`；**不提交 git**；复杂命令输出留存 `.work/log/spec/`（**禁 `tee`**）；**禁 `git checkout/restore/stash`**（还原一律 `cp`+md5 对账）。
  - **重建成本申报**：不触发组件重建。

## 验收标准

1. **`§1.1` 表 RAM@0 容量**：`grep -nF '16 MiB' spec/Machine-01-测试机运行环境.md` 命中 RAM@0 行；`grep -nF '【待 QEMU-049t 定】' spec/Machine-01-测试机运行环境.md` = **0 命中**（给真实输出/退出码，**禁 `tee`**）。
2. **`§1.2` 新增「精确路由」条 + 末条改落地陈述**：`grep` 显示新增条含「`umon` 段…⇒ `CFXMEM`（`0x81`）」「其余段（含旧 `power` 段 63）…⇒ 测试机约定 `unmapped`（`0x87`）」；末条为落地陈述（含 `check-interface` 断言固化）（给真实输出）。
3. **锁新增（21 条）+ 其余 20 册零变动**：`grep -c '^\[\[spec\]\]' manifests/spec-readonly.lock.toml` = **21**；**新增** `Machine-01` 条目 `sha256` == `sha256sum spec/Machine-01-测试机运行环境.md` 实测（逐位相等）；**其余 20 册 `sha256` 逐条不变**——`git diff -- manifests/spec-readonly.lock.toml` **仅 +1 段**（新增 `[[spec]]` 块 + 头注行），既有册 `sha256` 行的 `-`/`+` 计数 = **0**（给真实 `git diff`）。
4. **`Process-06 §5/§6` 同步（含语义扩面）**：`grep` 显示 §6 清单/计数按实（**21** 册）且「不在锁内」**不含** `Machine-01`（保留 `Process-0x`/`README.md`）；§5 措辞已完成**扩面**（不再限定「**只**覆盖上游」）且与「锁内只读册」自洽（给真实输出）。
5. **门控措辞已更正（去「upstream」；用户裁定 ⑤）**：`grep -nF 'upstream' tools/infra/check_spec_readonly.py` = **0 命中**；`grep -nF 'upstream read-only' Makefile` = **0 命中**（`Makefile` 其它与 spec 锁无关的「upstream」行——组件镜像等——**保留**，须逐条判明）；`grep -nF 'read-only spec volume' tools/infra/check_spec_readonly.py Makefile` **有命中**；`python3 tools/infra/check_spec_readonly.py --help` 描述不含「upstream」；给真实 `grep`/`--help` 输出与退出码。
6. **`spec/` 改动范围（授权边界）**：`git diff --name-only <base>..HEAD -- spec/` = **仅** `spec/Machine-01-测试机运行环境.md` + `spec/Process-06-spec目录保护规范.md`（`<base>` = 下发基线，须记明）；`Machine-01` 的 `git diff` **仅 §1 三处**（逐 hunk 核对；`§2`–`§7` 零改动）。
7. **门控**：`python3 tools/infra/check_spec_readonly.py` **EXIT=0**（`21 … OK`）；`make check` **EXIT=0**（含 `check-spec-readonly` / `check-spec-refs` / `manifest-check`；给真实输出/退出码，**禁 `tee`**）。
8. **一键证据脚本**：`.work/evidence/SPEC-121t/run.sh`——非交互、失败非零、逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入自检**：① 把 `§1.1` 容量改回占位 `【待 QEMU-049t 定】`；② 删/改 `§1.2` 路由条；③ 改锁内 `Machine-01` `sha256` ⇒ 对应断言 **FAIL** ⇒ `cp`+md5 还原 ⇒ **回绿**；结尾 `rc=$?; echo "EXIT=$rc"`（**禁 `tee`**）；给真实输出。
9. **无残留（含锁文件 + 门控措辞文件）**：`git -c core.quotePath=false status --untracked-files=all` 仅：`spec/Machine-01-测试机运行环境.md` + `manifests/spec-readonly.lock.toml` + `spec/Process-06-spec目录保护规范.md` + `tools/infra/check_spec_readonly.py` + `Makefile`（+ 如确需同步的 `.tao/knowledge/contract-see.md`）+ `.tao/knowledge/issues.yaml` + 本任务书；**无** `*.orig`/`*.rej`/`*_tmp*`/`*.preinject` 残留。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

按轮次追加，每次返工新增一轮，避免多轮记录混杂。

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### 范围补正（architect，2026-10-08）

**用户裁定原话（逐字）**：
- ④ 「**确认两条，按此下发（推荐）**」——确认：① **`Machine-01` 新增进锁（20→21）**；② **授权 `spec/Process-06 §5/§6` 同步**；
- ⑤ 「**并入 SPEC-121t 一并更正**」——`tools/infra/check_spec_readonly.py` 输出与 `Makefile` help 的「**upstream read-only spec volume(s)**」**措辞**一并更正。

**依据（主会话核实，architect 复述）**：① `manifests/spec-readonly.lock.toml` 实测**仅 20 册上游册**（`SimRISC-00..12` 13 + `DADAO-11/12/13` 3 + `DADAO-21/22/23` 3 + `Toolchain-01` 1），**不含** `spec/Machine-01`；② `spec/Process-06 §6` 明文「**不在锁内**：`spec/Machine-01`、`spec/Process-0x`、`spec/README.md`」，且 §5 标题「上游只读册哈希锁机制」、§6 标题「上游只读册清单（判据，20 册）」——均**只覆盖上游册**。

**补正内容（已落纸到本任务书）**：
1. 文件头「⚠️ 前置」补 ④/⑤ 原话 + 授权范围增列 `tools/infra/check_spec_readonly.py`（**仅措辞**）/`Makefile` help 措辞；
2. 「输出」增补「**`Machine-01` 作为『v5 自定册同样受保护』纳入锁**」的**语义扩面**要求——`Process-06` 由「只保护上游 20 册」扩为「**含 v5 自定册**」⇒ §5/§6 相应改写、措辞与门控输出同步（「upstream read-only spec volume(s)」去「upstream」）；新增第 6 项「门控措辞同步」；
3. 「验收」增补：锁 **21** 条 + **新增** `Machine-01` 且其余 20 册 `sha256` **逐条不变**（`git diff` **仅 +1 段**）；门控措辞 `grep` 真实输出（`check_spec_readonly.py` 去「upstream」、`Makefile` 去「upstream read-only」）；`check-spec-readonly`/`make check` EXIT=0；无残留清单含 `Makefile`/`check_spec_readonly.py`。

**范围未变项**：`spec/Machine-01 §1` 三处拟改文本**逐字不变**；`spec/` 改动仍**仅** `Machine-01 §1` + `Process-06 §5/§6`；锁其余 20 册零变动；不立 ADR。**未改动任何 `spec/` 文件**（本次仅为任务书 + 台账范围补正）。

## 说明

- **任务由来**：`QEMU-049t`（2026-10-08，已验证）落地 `ADR-0020 D15` 的三条机器模型口径后，核 `spec/Machine-01 §1` 发现**未完全覆盖**（占位 / 委派 / 歧义），登记 `ISS-166` 并**未改 `spec/`**（`spec/` 改动须用户事先授权，见 `lessons §8.5` / `Process-06`）。本任务即其**收口承接**（用户授权原话见文件头）。
- **为何含「`Machine-01` 入锁」**：`Machine-01` 原为 v5 自定册、**不在** `spec-readonly.lock.toml`；用户裁定「**把 Machine-01 新增进锁**」⇒ 本任务把该册纳入哈希锁（**锁内 21 条**），使其后续改动也受机械门控约束。**该入锁改变了 `Process-06` 的语义**——由「**只保护上游 20 册**」扩为「**含 v5 自定册**」；为保证规范与机制自洽，同任务同步 `Process-06 §5/§6`（用户裁定 ③/④）并同步门控措辞（去「upstream」，用户裁定 ⑤）。
- **为何沿用「`Process-06 §5/§6`」改动**：`Process-06 §6` 现明文把 `Machine-01` 列为「不在锁内」、清单标题为「上游只读册清单（判据，20 册）」，§5 标题为「上游只读册哈希锁机制」；入锁后若不同步，规范与机制矛盾（且「只覆盖上游」表述不再准确）。用户裁定 ③/④ 授权该同步。
- **ADR 说明（按 `AGENTS.md` 义务）**：本任务为规范正文口径落纸 + 过程规范/锁面同步，属**可逆、单项目、无外部契约新增**，**不命中** `spec/Process-03` ADR 判据（同 `SPEC-119t`/`SPEC-116t` 体例）⇒ **不立 ADR**（如用户另行裁定，按其指示）。
- **假设 / 边界**：`Machine-01 §1` 三处拟改文本**逐字**取自 `QEMU-049t` 审阅记录 / `ISS-166`，不得自由改写；`check-interface` 读的是**导出补丁**（属 `QEMU` 侧），本任务**只引其断言名**，不改 `components/`（**例外**：`tools/infra/check_spec_readonly.py` **仅措辞**去「upstream」，用户裁定 ⑤；`Makefile` 仅 help/注释措辞）。
- **范围补正（2026-10-08，用户裁定 ④/⑤）**：用户原话 ④「**确认两条，按此下发（推荐）**」（确认 `Machine-01` 进锁 **20→21** + 授权 `Process-06 §5/§6` 同步）、⑤「**并入 SPEC-121t 一并更正**」（`check_spec_readonly.py` 输出 / `Makefile` help 的「upstream read-only spec volume(s)」措辞一并更正）。据 ⑤，本任务在「`Machine-01` 入锁」后**语义扩面**：`Process-06` 由「**只保护上游 20 册**」改为「**含 v5 自定册**」⇒ §5/§6 相应改写、门控措辞去「upstream」；依据（主会话核实）：`manifests/spec-readonly.lock.toml` 实测**仅 20 册上游册**、`spec/Process-06 §6` 明文「不在锁内：`spec/Machine-01`…」。**`spec/Machine-01 §1` 三处拟改文本逐字不变**；`spec/` 改动仍**仅** `Machine-01 §1` + `Process-06 §5/§6`；锁其余 20 册零变动；不立 ADR。
