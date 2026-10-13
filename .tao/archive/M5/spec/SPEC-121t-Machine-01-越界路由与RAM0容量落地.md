# SPEC-121t: Machine-01 §1 越界路由与 RAM@0 容量落地（+ Machine-01 入锁 / Process-06 同步 / 门控措辞）

**模块**：spec
**项目里程碑**：M5
**依赖**：`QEMU-049t`（**已验证**；三条实现口径的来源）、`SPEC-119t`（锁/门控机制：`manifests/spec-readonly.lock.toml` + `tools/infra/check_spec_readonly.py` + `make check-spec-readonly`）；与其它改 `spec/` 或锁文件的任务**串行**
**状态**：已验证

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

**测试结果**：验收 9/9 项**通过**（全部可跑，无 BLOCKED）；一键证据脚本 `EVIDENCE: PASS`（`SCRIPT_EXIT=0`，含 6 组合成反例注入：B1–B6，各自「注入→目标断言 FAIL→`cp`+md5 还原→回绿」全部成立）。失败原因：无。

**基准 commit**：`4cc1f3862eec44b583bb19a55120cbf5ea3e032e`（下发基线 `HEAD`；本任务**不提交 git**，据 `git diff`/`git status` 核对）。日志：`.work/log/spec/SPEC-121t-verify.log`、`-make-check.log`、`-evidence.log`。证据脚本：`.work/evidence/SPEC-121t/run.sh`（gitignored）。

**修改文件**（与 `git -c core.quotePath=false status -uall` 一致）：
1. `spec/Machine-01-测试机运行环境.md`（§1 三处：§1.1 表 RAM@0 行 + §1.2 新增「精确路由」条 + §1.2 末条改写）
2. `spec/Process-06-spec目录保护规范.md`（仅 §5 标题/正文 + §6 标题/表格/注记）
3. `manifests/spec-readonly.lock.toml`（头注同步 + 末尾新增 `[[spec]]` `Machine-01`；其余 20 册 `sha256` 逐字不动）
4. `tools/infra/check_spec_readonly.py`（**仅措辞**：docstring / `--help` / 成功输出行去「upstream」；逻辑零改动）
5. `Makefile`（仅 help L101 + 注释 L354 措辞）
6. `.tao/knowledge/issues.yaml`（`ISS-166` → `closed` / `resolved_by: SPEC-121t` / notes 追加）
7. 本任务书（状态 + 完成区 + 审阅记录）
- gitignored：`.work/evidence/SPEC-121t/run.sh`、`.work/log/spec/SPEC-121t-*.log`。
- **未改**：`.tao/knowledge/contract-see.md` / `contract-semihosting.md`（见「验收结果·7」grep 判据）；`spec/` 其它册零改动。

**验收结果**（真实输出；基准 `HEAD=4cc1f38`）：

1. **§1.1 RAM@0 容量**（`grep`，`EXIT` 逐条）：
   ```
   $ grep -nF '16 MiB' spec/Machine-01-测试机运行环境.md          # EXIT=0
   25:| **RAM@0（新）** | `0x0000_0000_0000` | 16 MiB | 0 / `umon` | 供 bootrom/SEE（C1 step1 双映射引入） |
   $ grep -cF '【待 `QEMU-049t` 定】' spec/Machine-01…            # 0 命中（grep EXIT=1）
   0
   $ grep -cF '【待 QEMU-049t 定】' spec/Machine-01…              # 0 命中（grep EXIT=1）
   0
   ```
2. **§1.2 新增条 + 末条**：
   ```
   $ grep -nF '精确路由（`QEMU-049t` 已按' spec/Machine-01…       # EXIT=0
   40:- **精确路由（`QEMU-049t` 已按 `ADR-0020 D15` 落地）**：**`umon` 段（`addr[47:42]==0`）的越界访问/越界取指 ⇒ `CFXMEM`（`0x81`）**；**其余段（含旧 `power` 段 63）的越界访问/越界取指 ⇒ 测试机约定 `unmapped`（`0x87`）**。[ADR-0020 D15]
   $ grep -nF '并以 `check-interface` 断言固化' spec/Machine-01…  # EXIT=0
   43:- 精确路由与 RAM@0 容量由 `QEMU-049t` 落地（`umon` 段 ⇒ `0x81`、其余 ⇒ `0x87`；RAM@0 = 16 MiB），并以 `check-interface` 断言固化。[ADR-0020 D15]
   ```
3. **锁（21 条）+ 新增 `Machine-01` + 其余 20 册零变动**：
   ```
   $ grep -c '^\[\[spec\]\]' manifests/spec-readonly.lock.toml   # 21
   21
   $ grep -A2 'path = "spec/Machine-01-测试机运行环境.md"' manifests/spec-readonly.lock.toml
   path = "spec/Machine-01-测试机运行环境.md"
   group = "machine-01"
   sha256 = "de4cd6d81751f3c1a79c7714ffda280372d41c9614c1a073a629de843bf43e40"
   $ sha256sum spec/Machine-01-测试机运行环境.md
   de4cd6d81751f3c1a79c7714ffda280372d41c9614c1a073a629de843bf43e40  spec/Machine-01-测试机运行环境.md   # 逐位相等 ✓
   ```
   `git diff -- manifests/spec-readonly.lock.toml`：**仅 2 hunk**——① 头注计数/说明（`清单 = 20 册上游只读册` → `21 册只读册 = 20 上游 + 1 v5 自定`；新增 `machine-01` 分组行；「注意」行 `Machine-01` 移出「不在锁内」）；② 末尾新增 `[[spec]]` 块。**既有 20 册 `sha256` 行的 `-`/`+` 计数 = 0**（`diff` 中无任何 `sha256 =` 行被改）。
4. **`Process-06 §5/§6` 同步**：
   ```
   $ grep -nF '## 5. 只读册哈希锁机制' spec/Process-06…          # EXIT=0
   28:## 5. 只读册哈希锁机制（MUST）
   $ grep -nF '## 6. 只读册清单（判据，21 册）' spec/Process-06…   # EXIT=0
   35:## 6. 只读册清单（判据，21 册）
   $ grep -cF '| `machine-01` | `spec/Machine-01-测试机运行环境.md` |' spec/Process-06…   # 1
   $ grep -cF '不在锁内**：`spec/Machine-01`' spec/Process-06…     # 0（grep EXIT=1）
   $ grep -cF '不在锁内**：`spec/Process-0x`' spec/Process-06…     # 1
   ```
   §5 正文 `上游只读册以 …` → `只读册（上游 20 册 + v5 自定册 spec/Machine-01）以 …`（**去「只覆盖上游」限定**）；§6 注记 `哈希锁只覆盖**上游只读册**` → `……**锁内只读册**——上游只读册 + spec/Machine-01`。
5. **门控措辞（去「upstream」）**：
   ```
   $ grep -cF 'upstream' tools/infra/check_spec_readonly.py       # 0（grep EXIT=1）
   $ grep -cF 'upstream read-only' Makefile                       # 0（grep EXIT=1）
   $ grep -nF 'read-only spec volume' tools/infra/check_spec_readonly.py Makefile   # EXIT=0
   tools/infra/check_spec_readonly.py:2/86/143 、Makefile:101
   $ python3 tools/infra/check_spec_readonly.py --help | sed -n '2,4p'
   Verify read-only spec volumes against a sha256 lock (SPEC-119t).   # 不含 upstream
   ```
   `Makefile` 其余 `upstream`（L5 `upstream mirrors`、L51 `upstream commit`）**与该门控无关，保留**（逐条判明）。
6. **`spec/` 改动范围**（授权边界）：
   ```
   $ git -c core.quotePath=false diff --name-only -- spec/
   spec/Machine-01-测试机运行环境.md
   spec/Process-06-spec目录保护规范.md
   ```
   `Machine-01` 的 `git diff` **仅 §1 三处 hunk**（L25 / 新增 L40 / L43），`§2`–`§7` **零改动**。
7. **门控 EXIT=0**：
   ```
   $ python3 tools/infra/check_spec_readonly.py
   check-spec-readonly: 21 read-only spec volume(s) OK        # EXIT=0
   $ JOBS=8 make check        # EXIT=0（完整输出 .work/log/spec/SPEC-121t-make-check.log）
   … check-spec-readonly: 21 read-only spec volume(s) OK …
   repository checks: PASS
   ```
   **投影判据（输出 7）**：`grep -cF '16 MiB'`/`'精确路由'` 在 `contract-see.md` 与 `contract-semihosting.md` **均 = 0**（两册**不含** RAM@0 尺寸/精确路由明细，仅泛述「地址划分 / CFXMEM=0x81 / unmapped=0x87」）⇒ **不改**（符合任务「否则不改并说明」）；`make check` 的 `contract-see`/`contract-semihosting` 投影检查仍 `[PASS]`（无漂移）。
8. **一键证据脚本** `.work/evidence/SPEC-121t/run.sh`（`SCRIPT_EXIT=0`，`EVIDENCE: PASS`）：
   - 绿态：真仓库 16 项断言全 PASS（A0–A10）。
   - 注入（临时树 `/tmp/opencode/SPEC-121t/evidence/tree`，**真仓库零触碰**）：
     `B1` 容量改回占位 ⇒ `A1` FAIL；`B2` 删路由条 ⇒ `A3` FAIL；`B3` 改锁内 `Machine-01` `sha256` ⇒ `A6` FAIL；`B4` 改上游册（SimRISC-00）`sha256` ⇒ `A7` FAIL；`B5` 把 `Machine-01` 重列进 `Process-06 §6`「不在锁内」⇒ `A8b`/`A8c` FAIL；`B6` 给 checker 重新加回 `upstream` 措辞 ⇒ `A9a`/`A10` FAIL。
     每次注入先验「md5 变化（非空注入）」，再 `cp`+md5 还原（md5 相等）⇒ 回绿。
   - 结尾 `rc=$?; echo "EXIT=rc"`（**无 `tee`**）。
9. **无残留**：`git -c core.quotePath=false status --untracked-files=all` 仅上述 6 个已改文件（+ 本任务书）；**无** `*.orig`/`*.rej`/`*_tmp*`/`*.preinject`（`git status` 与 `/tmp` 树 `find` 均干净）。

**新发现/坑**：
- **`check-spec-readonly` 生成式断言曾写错**：初版证据脚本用「`不在锁内` 行不含 `spec/Machine-01`」判 `Process-06 §6`——但 §6 新注记在「哈希锁只覆盖**锁内只读册**——上游只读册 + `spec/Machine-01`」中**合法地**出现 `Machine-01`，致绿态误报 FAIL。**判据须精确定位「不在锁内」枚举本身**（`不在锁内**：\`spec/Machine-01\`` 计数），已改为精确串断言（见自审 F1）。教训：断言「不含 X」时须限定到目标子串，不能整行粗判。
- **临时树校验须用「树内」checker**：`run_checks` 初版对任意树都调用**仓库**的 `check_spec_readonly.py`，导致针对树内 checker 措辞的注入（`B6`）无法影响 `--help` 断言（`A10`）。已改为调用被检树自身的 `<root>/tools/infra/check_spec_readonly.py`（见自审 F2）。
- **脚本文本编辑须避免 `sed` 对含反引号/中文串的转义风险**：注入统一用 `python3` 精确 `str.replace`（带「替换未命中即断言失败」保护），避免空注入假绿。
- **`Process-06 §1` 与 §6 的引用张力**：§6 由「上游只读册清单」扩为「只读册清单（21 册，含 v5 自定册）」后，§1 正文「不得把上游只读册（清单见 §6）列为可改对象」中「（清单见 §6）」现指向含 `Machine-01` 的清单，字面略不精确。**§1 不在用户授权范围（仅 §5/§6）**，故未改，登记于「遗留问题」。

**遗留问题**：
- **`Process-06 §1` 的清单指代（未处置，越界风险）**：§1 首段「上游只读册（清单见 §6）」现指向的 §6 已含 v5 自定册 `Machine-01`。**授权范围明文仅 §5/§6**（文件头「授权范围」/「约束（硬）」），改 §1 即 **BLOCKED**，故**未动**。**建议**：如用户认可，另授权把 §1 该括注改为「（锁内只读册清单见 §6）」或等价准确表述（一行措辞，可并入后续任务）。
- **`contract-see.md §2`（原任务写 §1）未同步尺寸/路由明细**：该册仅泛述口径，按任务「如实测含对应口径则同步，否则不改」判为**不含** ⇒ 不改（grep 见验收 7）。如后续希望投影出 `16 MiB`/路由，需另立（非本任务范围）。
- **`QEMU-049t` 遗留的 `ISS-165`（C1 step2 迁移）**：与本任务无关、仍 `open`（本任务只关 `ISS-166`）。

## 审阅记录

按轮次追加，每次返工新增一轮，避免多轮记录混杂。

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（`subagent_depth=1`，engineer 不再起嵌套子代理）。范围：`spec/Machine-01 §1`（3 处改动）、`spec/Process-06 §5/§6`、`manifests/spec-readonly.lock.toml`、`tools/infra/check_spec_readonly.py`、`Makefile`、`.tao/knowledge/issues.yaml`、证据脚本 `.work/evidence/SPEC-121t/run.sh`。

**审查要点与结论**：
- **逻辑/边界**：`Machine-01` 三处 hunk **逐字取自任务书「输出」**（与 `QEMU-049t` 审阅记录拟改文本一致）；`§1.2` 插入位置在「层次与适用」条之后、「取指路径同等对待」条之前（紧接「层次与适用」，符合任务「建议」）；`§2`–`§7` 零改动。
- **锁纪律**：`Machine-01` `sha256` 在 §1 **改毕后**实测（`sha256sum`）；`git diff` 确认**无任何既有册 `sha256` 行被改**（`-`/`+` 计数 0）；新增块置于文件末尾。锁头注与体例自洽（`format=1`/`policy` 不变）。
- **规范自洽（`Process-06`）**：§5 标题/正文去「只覆盖上游」限定；§6 标题 `20 册`→`21 册`、表增 `machine-01` 分组、「不在锁内」移除 `Machine-01`（保留 `Process-0x`/`README.md`）。§2（授权纪律）实质未动。
- **门控措辞**：`check_spec_readonly.py` 仅 docstring/`--help`/成功行去「upstream」，**校验逻辑（`fail-closed`）与退出码零改动**；`Makefile` 仅 help/注释措辞。
- **防造假**：所有结论均有真实命令输出（`.work/log/spec/SPEC-121t-*.log`）；证据脚本含 6 组非空注入与 `cp`+md5 还原。
- **未引入**：新外部依赖、函数签名变更、`components/**` 改动、（除 `spec/` 授权 2 册与 `Makefile`/checker 措辞外的）越界改动。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 证据脚本 `A8b` 断言写错：以「`不在锁内` 行不含 `spec/Machine-01`」判定，但 §6 注记在「锁内只读册——…+`spec/Machine-01`」中合法含该串 ⇒ 绿态误报 FAIL | ✅已修 | `run.sh`：改为精确串 `不在锁内**：\`spec/Machine-01\`` 计数 = 0（并保留 `A8c` `不在锁内**：\`spec/Process-0x\`` = 1） | 重跑 `run.sh`：绿态 `A8b`/`A8c` PASS，`real repo: green again`（`.work/log/spec/SPEC-121t-evidence.log`） |
| F2 证据脚本对任意树调用**仓库** checker，`B6`（树内 checker 措辞）无法触达 `A10`（`--help`） | ✅已修 | `run.sh`：`run_checks` 改用被检树自身 `<root>/tools/infra/check_spec_readonly.py` | `B6` 注入后 `A9a`（count=2）与 `A10`（`has`）均 FAIL；还原回绿 |
| F3 锁头注 L2「上游只读册：sha256 锁」在纳入 v5 自定册后不准确 | ✅已修 | `manifests/spec-readonly.lock.toml` L2 → 「只读册（上游 20 册 + v5 自定 1 册）：sha256 锁」 | 头注计数/分组/注意行三处同步；`check-spec-readonly` 21 OK |
| F4 checker docstring 枚举 `every read-only spec volume (…)` 未含新增 `Machine-01` | ✅已修 | `check_spec_readonly.py` docstring 列表补 `spec/Machine-01`（仍属**仅措辞**，逻辑未动） | `grep 'upstream'` = 0；`--help`/`run.sh` `A9c`/`A10` PASS |
| F5 `Process-06 §1`「上游只读册（清单见 §6）」指向已含 v5 自定册的 §6，字面略不精确 | ⏸延后 | 无（§1 不在用户授权「仅 §5/§6」范围，改即 BLOCKED） | 已在完成区「新发现/坑」「遗留问题」登记，建议另授权后一行措辞修正 |

**判决**：F1–F4 **已修**；F5 属**授权边界外的观察项**（非本次改动缺陷，已落纸待用户裁定）⇒ 无「本任务范围内的未修 finding」。**状态置「待验收」**，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理（mimo-v2.5-pro）
**审查时间**：2026-10-08
**基准 commit**：`4cc1f38`（HEAD = `85b80ba`，WIP 提交）

---

##### 一、证据脚本审查（`.work/evidence/SPEC-121t/run.sh`）

**结构**：非交互；6 组注入（B1–B6）均在**临时树** `/tmp/opencode/SPEC-121t/evidence/tree` 执行，真仓库零触碰；结尾 `rc=$?; echo "EXIT=$rc"`（**无 `tee`**）；每组注入用 `python3` 精确 `str.replace`（带 `assert s2 != s` 保护，防空注入）。

**断言 FAIL 路径逐条核对**：

| 断言 | 注入目标 | FAIL 路径 | 恒真？ |
|------|---------|----------|--------|
| A0 Machine-01 entry | — | 无入口 → `grep -c` = 0 ≠ 1 → FAIL | ✅ 可达 |
| A1 RAM@0 16 MiB | B1 | 改回占位 → `grep -c` = 0 ≠ 1 → FAIL | ✅ 可达 |
| A2 no 待 | B1 | 改回占位 → `grep -c` = 1 ≠ 0 → FAIL | ✅ 可达 |
| A3 routing bullet | B2 | 删路由条 → `grep -c` = 0 ≠ 1 → FAIL | ✅ 可达 |
| A3b routing content | B2 | 删路由条 → `a3b=bad` ≠ `ok` → FAIL | ✅ 可达 |
| A4 末条 landing | B2 | 删路由条（末条也被删）→ 0 ≠ 1 → FAIL | ✅ 可达 |
| A5 lock count | B3/B4 | 篡改 sha256 不影响 count → count 仍 21 → PASS（但 A6/A7 FAIL） | ✅ 不恒真 |
| A6 sha256 match | B3 | 改锁 sha256 → `want` ≠ `got` → FAIL | ✅ 可达 |
| A7 checker EXIT | B3/B4 | sha 不匹配 → checker EXIT=1 ≠ 0 → FAIL | ✅ 可达 |
| A8 §6 title 21 | — | 标题不含 21 → 0 ≠ 1 → FAIL（注入 B5 不改标题） | ✅ 可达 |
| A8b 不在锁内无 M-01 | B5 | 重列 Machine-01 → `grep -c` = 1 ≠ 0 → FAIL | ✅ 可达 |
| A8c 不在锁内有 P-0x | B5 | 替换为 Machine-01 → Process-0x 被删 → 0 ≠ 1 → FAIL | ✅ 可达 |
| A9a py no upstream | B6 | 加回 upstream → `grep -c` = 2 ≠ 0 → FAIL | ✅ 可达 |
| A9b mk no upstream | — | 加回 upstream read-only → 1 ≠ 0 → FAIL（B6 不改 Makefile） | ✅ 可达 |
| A9c py has volume | — | 删该串 → 0 ≠ 1 → FAIL（注入 B6 不删） | ✅ 可达 |
| A10 --help no upstream | B6 | 加回 upstream → `a10=has` ≠ `no` → FAIL | ✅ 可达 |

**结论**：所有 16 条断言均有可达 FAIL 路径，无恒真结构。6 组注入均非空（`snap_after` 验证 md5 变化），均用 `cp`+md5 还原（md5 相等）。脚本**合格**。

---

##### 二、脚本重跑（真实输出）

```
====[1] green phase: real repo assertions ====
PASS  A0 lock has Machine-01 entry                         expected=1 actual=1
PASS  A1 RAM@0 row size=16 MiB                             expected=1 actual=1
PASS  A2 no 待 placeholder                                expected=0 actual=0
PASS  A3 §1.2 routing bullet present                      expected=1 actual=1
PASS  A3b routing covers umon=>0x81 / else=>0x87           expected=ok actual=ok
PASS  A4 末条 landing + check-interface                  expected=1 actual=1
PASS  A5 lock [[spec]] count                               expected=21 actual=21
PASS  A6 Machine-01 lock sha == file sha                   expected=de4cd6d8…actual=de4cd6d8…
PASS  A7 check-spec-readonly --root EXIT                   expected=0 actual=0
PASS  A8 Process-06 §6 title (21 册)                     expected=1 actual=1
PASS  A8b 不在锁内 does not list Machine-01            expected=0 actual=0
PASS  A8c 不在锁内 keeps Process-0x                    expected=1 actual=1
PASS  A9a py no 'upstream'                                 expected=0 actual=0
PASS  A9b Makefile no 'upstream read-only'                 expected=0 actual=0
PASS  A9c py has 'read-only spec volume'                   expected=1 actual=1
PASS  A10 --help no 'upstream'                             expected=no actual=no
PASS  real repo: green again

B1–B6 每组：注入有效（md5 变化）→ 目标断言 FAIL → cp+md5 还原 → 回绿
EVIDENCE: PASS
EXIT=0
```

**脚本退出码**：`SCRIPT_EXIT=0` ✅

---

##### 三、独立注入（reviewer 自行执行）

**注入方式**：改**真仓库** `spec/Machine-01-测试机运行环境.md` §1.1 容量 `16 MiB` → `【待 QEMU-049t 定】`，用 `cp`+md5 备份还原（**禁 `git checkout/restore/stash`**）。

```
$ cp spec/Machine-01-测试机运行环境.md spec/Machine-01-测试机运行环境.md.preinject
$ md5sum spec/Machine-01-测试机运行环境.md spec/Machine-01-测试机运行环境.md.preinject
08bcc0ed9f78d8bd386f4f8b79ad2602  两者一致 ✓

$ python3 -c "...replace('16 MiB', '【待 QEMU-049t 定】')..."
injected: replaced 16 MiB with placeholder

$ md5sum spec/Machine-01-测试机运行环境.md
a6bbd4f336d36a75db78a34a44f1f8d2  # md5 变化 → 注入有效 ✓

$ python3 tools/infra/check_spec_readonly.py 2>&1; echo "CHECKER_EXIT=$?"
check-spec-readonly: MISMATCH spec/Machine-01-测试机运行环境.md: expected=de4cd6d8… actual=5f0e750f… 
check-spec-readonly: FAIL (1/21 volume(s) mismatched or missing)
CHECKER_EXIT=1  # 注入后 FAIL ✓

$ cp spec/Machine-01-测试机运行环境.md.preinject spec/Machine-01-测试机运行环境.md
$ md5sum spec/Machine-01-测试机运行环境.md
08bcc0ed9f78d8bd386f4f8b79ad2602  # 还原后 md5 一致 ✓

$ python3 tools/infra/check_spec_readonly.py 2>&1; echo "CHECKER_EXIT=$?"
check-spec-readonly: 21 read-only spec volume(s) OK
CHECKER_EXIT=0  # 还原后回绿 ✓
```

**独立注入结论**：注入有效（md5 变化）→ checker FAIL（EXIT=1）→ cp+md5 还原 → 回绿（EXIT=0）。✅

---

##### 四、逐条验收

| # | 验收项 | 真实输出 | 结果 |
|---|--------|---------|------|
| 1 | §1.1 RAM@0 = 16 MiB | `grep -nF '16 MiB'` → L25 命中；`grep -cF '【待 QEMU-049t 定】'` = 0（EXIT=1） | ✅ |
| 2 | §1.2 精确路由条 + 末条 | L40 含 `umon`/`0x81`/`power`/`0x87`；L43 含 `check-interface` 断言固化 | ✅ |
| 3 | 锁 21 条 + Machine-01 sha 匹配 + 20 册零变动 | `grep -c '^\[\[spec\]\]'` = 21；sha256 逐位相等 `de4cd6d8…`；diff 仅 +1 sha256 行（新增），既有 20 行 `-`/`+` = 0 | ✅ |
| 4 | Process-06 §5/§6 同步 | §5 标题「只读册哈希锁机制」；§6 标题「21 册」；表含 `machine-01`；`不在锁内` 不含 Machine-01（保留 Process-0x/README.md）；§5 正文「只读册（上游 20 册 + v5 自定册 spec/Machine-01）」 | ✅ |
| 5 | 门控措辞去 upstream | `grep -cF 'upstream' check_spec_readonly.py` = 0（EXIT=1）；`grep -cF 'upstream read-only' Makefile` = 0（EXIT=1）；`grep -nF 'read-only spec volume'` 有命中（py L2/86/143，Makefile L101）；`--help` 不含 upstream | ✅ |
| 6 | spec/ 改动范围 | `git diff --name-only -- spec/` = 仅 Machine-01 + Process-06；Machine-01 hunk 头 `@@ -22,7 @@` + `@@ -37,9 @@`（均在 §1）；Process-06 hunk 头 `@@ -25,14 @@`（§5/§6）+ `@@ -42,8 @@`（§6 表/注记） | ✅ |
| 7 | `check-spec-readonly` EXIT=0 | `21 read-only spec volume(s) OK`；`make check` EXIT=0（全 86+62 项 PASS） | ✅ |
| 8 | 一键证据脚本 | 已审（见一/二节），合格 | ✅ |
| 9 | 无残留 | `git status` 干净（WIP 提交后无未跟踪文件）；无 `*.orig`/`*.rej`/`*_tmp*`/`*.preinject` | ✅ |
| — | 全局 7 文件 | `git diff --name-only 4cc1f38..HEAD` = 7 文件（issues.yaml + 任务书 + Machine-01 + Process-06 + lock + checker + Makefile） | ✅ |
| — | ISS-166 结案 | `status: closed`，`resolved_by: SPEC-121t`，notes 完整 | ✅ |
| — | contract-see/semihosting 未改 | `git diff -- .tao/knowledge/` 仅 issues.yaml；两册均不含 `16 MiB`/`精确路由` | ✅ |

---

##### 五、遗留核验

| 遗留项 | 核验 | 结论 |
|--------|------|------|
| `Process-06 §1`「上游只读册（清单见 §6）」在 §6 含 v5 自定册后字面略不精确 | `git diff` 确认 §1 **未改**（hunk 均在 §5/§6）；§1 正文行 9 现文「上游只读册（清单见 §6）」确实指向含 Machine-01 的 §6 | 确认未改，属授权范围外观察项，已登记在完成区遗留问题 |
| `contract-see.md` 未同步尺寸/路由 | grep 确认不含 `16 MiB`/`精确路由` | 符合任务「否则不改并说明」 |

---

##### 六、判决

**Accepted** ✅

全部 9 项验收通过；证据脚本合格（16 条断言均有可达 FAIL 路径，6 组注入非空可还原）；独立注入验证 FAIL→还原→回绿 成功；授权范围内改动（`Machine-01 §1` 3 处 + `Process-06 §5/§6` + 锁新增 + 门控措辞）均符合；其余 20 册 sha256 零变动；`make check` EXIT=0；遗留问题已如实登记。

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

#### 第 1 轮 architect 提交（WIP）（2026-10-08）

**档位**：reviewer **尚未验收** ⇒ **`WIP:`** 提交（待 reviewer 判 `Accepted` 后由 `/complete` 收尾，历史将由主会话 squash/amend 成单一「已验证」提交后再 push）。

**文件集对账（显式 staging，禁 `git add -A`）**：`git diff --cached --name-only` = 7 项，与完成区「修改文件」声明**逐条一致** ⇒ **无漏提、无多提、无越界**：

- `spec/Machine-01-测试机运行环境.md`
- `spec/Process-06-spec目录保护规范.md`
- `manifests/spec-readonly.lock.toml`
- `tools/infra/check_spec_readonly.py`
- `Makefile`
- `.tao/knowledge/issues.yaml`
- `.tao/tasks/spec/SPEC-121t-Machine-01-越界路由与RAM0容量落地.md`（本任务书）

**`spec/` 授权范围核对**：`git diff --cached --name-only -- spec/` **仅** `spec/Machine-01-测试机运行环境.md` + `spec/Process-06-spec目录保护规范.md`（2 项，无其它册）；`git diff --cached -- spec/Machine-01*` 的 hunk 头 **仅 2 个**——`@@ -22,7 +22,7 @@ v5 测试机使用的核内地址空间划分如下…`（§1.1，行 22）与 `@@ -37,9 +37,10 @@ v5 测试机使用的核内地址空间划分如下…`（§1.2，行 37）——**均落在 §1（文件行 13–46）**，共 3 处改动（§1.1 表 RAM@0 大小 1 处 + §1.2 精确路由 2 处），**无其它册、无其它节** ⇒ 与用户授权范围（`Machine-01 §1` 三处 + `Process-06 §5/§6`）**一致**。

#### 第 1 轮 architect 提交（正常）（2026-10-08）

**档位**：reviewer 判 **`Accepted`** ⇒ **正常提交**（**不加 `WIP:`**）。本提交含 §2.5 交叉复核 + `lessons.md`/`changelog.md`/`milestones.md`/`MEMORY.md` 知识沉淀 + 本任务书（审阅记录）；`spec/` 改动（`Machine-01 §1` + `Process-06 §5/§6`）与锁/门控措辞/`issues.yaml` 已在 base 后的 **WIP 提交**中落库，本提交**不含** `spec/`。

**文件集对账（显式 staging，禁 `git add -A`）**：`git diff --cached --name-only` = **5 项**（本任务书 + 知识沉淀 4 件），与本次提交预期**逐条一致** ⇒ **无漏提、无多提、无越界**：
- `.tao/tasks/spec/SPEC-121t-Machine-01-越界路由与RAM0容量落地.md`（本任务书：审阅记录）
- `.tao/knowledge/lessons.md`（§7.17 + §8.11）
- `.tao/knowledge/changelog.md`（+1 行）
- `.tao/knowledge/milestones.md`（M5 段完成标记）
- `.tao/knowledge/MEMORY.md`（M5 摘要行 +`SPEC-121t`）

**`spec/` 交集核对**：`git diff --cached --name-only -- spec/` = **空**（0 项）——本次提交不触及 `spec/`，与「**不得改 `spec/`**（`Process-06 §1` 措辞留待授权）」硬约束一致。

**只 `commit`、不 `push`**（推送由主会话在 `/complete` 收尾后 squash/amend 成单一「已验证」提交再执行）。

## 说明

- **任务由来**：`QEMU-049t`（2026-10-08，已验证）落地 `ADR-0020 D15` 的三条机器模型口径后，核 `spec/Machine-01 §1` 发现**未完全覆盖**（占位 / 委派 / 歧义），登记 `ISS-166` 并**未改 `spec/`**（`spec/` 改动须用户事先授权，见 `lessons §8.5` / `Process-06`）。本任务即其**收口承接**（用户授权原话见文件头）。
- **为何含「`Machine-01` 入锁」**：`Machine-01` 原为 v5 自定册、**不在** `spec-readonly.lock.toml`；用户裁定「**把 Machine-01 新增进锁**」⇒ 本任务把该册纳入哈希锁（**锁内 21 条**），使其后续改动也受机械门控约束。**该入锁改变了 `Process-06` 的语义**——由「**只保护上游 20 册**」扩为「**含 v5 自定册**」；为保证规范与机制自洽，同任务同步 `Process-06 §5/§6`（用户裁定 ③/④）并同步门控措辞（去「upstream」，用户裁定 ⑤）。
- **为何沿用「`Process-06 §5/§6`」改动**：`Process-06 §6` 现明文把 `Machine-01` 列为「不在锁内」、清单标题为「上游只读册清单（判据，20 册）」，§5 标题为「上游只读册哈希锁机制」；入锁后若不同步，规范与机制矛盾（且「只覆盖上游」表述不再准确）。用户裁定 ③/④ 授权该同步。
- **ADR 说明（按 `AGENTS.md` 义务）**：本任务为规范正文口径落纸 + 过程规范/锁面同步，属**可逆、单项目、无外部契约新增**，**不命中** `spec/Process-03` ADR 判据（同 `SPEC-119t`/`SPEC-116t` 体例）⇒ **不立 ADR**（如用户另行裁定，按其指示）。
- **假设 / 边界**：`Machine-01 §1` 三处拟改文本**逐字**取自 `QEMU-049t` 审阅记录 / `ISS-166`，不得自由改写；`check-interface` 读的是**导出补丁**（属 `QEMU` 侧），本任务**只引其断言名**，不改 `components/`（**例外**：`tools/infra/check_spec_readonly.py` **仅措辞**去「upstream」，用户裁定 ⑤；`Makefile` 仅 help/注释措辞）。
- **范围补正（2026-10-08，用户裁定 ④/⑤）**：用户原话 ④「**确认两条，按此下发（推荐）**」（确认 `Machine-01` 进锁 **20→21** + 授权 `Process-06 §5/§6` 同步）、⑤「**并入 SPEC-121t 一并更正**」（`check_spec_readonly.py` 输出 / `Makefile` help 的「upstream read-only spec volume(s)」措辞一并更正）。据 ⑤，本任务在「`Machine-01` 入锁」后**语义扩面**：`Process-06` 由「**只保护上游 20 册**」改为「**含 v5 自定册**」⇒ §5/§6 相应改写、门控措辞去「upstream」；依据（主会话核实）：`manifests/spec-readonly.lock.toml` 实测**仅 20 册上游册**、`spec/Process-06 §6` 明文「不在锁内：`spec/Machine-01`…」。**`spec/Machine-01 §1` 三处拟改文本逐字不变**；`spec/` 改动仍**仅** `Machine-01 §1` + `Process-06 §5/§6`；锁其余 20 册零变动；不立 ADR。

#### 主会话统一验收报告（`/complete`，2026-10-08）

- **reviewer**：`Accepted`。证据脚本绿态 **15/15**、6 组注入（含「把 `Machine-01` 重列回 §6 不在锁内」「给 checker 加回 `upstream`」）各自 FAIL ⇒ `cp`+`md5` 还原 ⇒ 回绿；**独立注入**改真仓库 `RAM@0` 容量 ⇒ checker **MISMATCH**（`EXIT=1`，证明**锁对 `Machine-01` 实际生效**）⇒ 还原回绿。
- **architect 交叉复核**：**维持 `Accepted`**。独立核：`Machine-01` hunk **仅 2 处且均在 §1**（§2–§7 零改动）；锁 **21** 条、`Machine-01` sha == 实测、**其余 20 册 `sha256` 逐条未变**（diff 仅新增 1 行）；`Process-06` hunk **仅 §5/§6**（**§1 确未改**）；checker/`Makefile` **去 `upstream`**；`check-spec-readonly` **21 册 OK**、`make check` EXIT=0；`ISS-166` 结案。
- **交付**：`Machine-01 §1.1` RAM@0 = **16 MiB**（占位消失）；§1.2 **新增精确路由条**（`umon` ⇒ `0x81`；其余含旧 `power` 63 ⇒ `0x87`）+ **末条改已落地陈述**；**`Machine-01` 作为 v5 自定册纳入只读锁（20→21）**；`Process-06 §5/§6` 语义扩为「含 v5 自定册」；门控措辞去掉 `upstream`。
- **遗留（必报）**：`Process-06 §1`「上游只读册（清单见 §6）」在 §6 含 v5 自定册后**字面已不精确**——**§1 不在授权范围（仅 §5/§6）⇒ 未改**，建议后续经授权作一行措辞修正。
- **补充发现**：`contract-see.md`/`contract-semihosting.md` 不含对应明细 ⇒ 按判据**未改**（符合预期）；`ISS-165`（C1 step2）仍 `open`，与本任务无关。
- **知识沉淀**：`lessons §7.17`（立案前须实测锁**实际包含**哪些册，避免「更新某册锁」前提错误）+ **`§8.11`**（保护范围扩面须「机制正文 + 锁清单 + 门控措辞 + 判据注记」**四处一致**；越界相邻措辞只登记不顺手改）。
- **最终判决**：**`Accepted`** ⇒ 任务书 `**状态**` 置 `已验证`。
