# QEMU-061t: `aip.si` 的解码与语义（原 `rela.si`，用户 2026-10-16 裁定改名；`0x5A` / `rbHA = IP + (imms18 << 12)` / 目的 `rb0` ⇒ ILLI）

**模块**：qemu
**项目里程碑**：M8
**依赖**：`ADR-0029`（**`Accepted`**，2026-10-16 用户逐条确认 —— 本册 = `D1`（语义 / 目的 `rb0` ⇒ ILLI）/ `D7③` 的执行落点）、**`SPEC-145t`**（**前置**：编码 / 语义**冻结**后才可动译码与执行 ⇒ 其 `已验证` 前**不得开工**）、**`LLVM-095t`**（**串行在前**：与 `tests/vectors/**` 共用载体，`AGENTS.md`「同改共享文件一律串行」）、`ADR-0012 D5`（**被本册回退**的解码项：`0x5A` → UNDI）、`ADR-0019 D3`（`rb0` = 当前指令地址）/ `D6`（越界报错口径的同族「禁静默」纪律）；契约真源 = `.tao/contracts/contract-isa.md §1.3.2`（`rb0`）/ `contract-fp` 无关；现场来源 = `QEMU-060t`（本模块最近落地的回退任务）、`ISS-230`；纪律 = `ISS-210`（改组件后安装根须同步）/ `ISS-229`（重建串行）、`docs/Process-01`（组件补丁树）、`docs/Process-05`（L2 冒烟 / L3 语义）
**状态**：已验证

> **改名注记（2026-10-16，追加）**：用户 2026-10-16 裁定「**改为：aip.si，在正文中，避免使用pc，应该用ip；而且，在SimRISC中，ip明确是当前正在执行的指令的地址，而非主流ISA的下一条指令地址**」⇒ 本册**正文**已同步 `rela.si` → **`aip.si`**、`PC` → **`IP`**（用户原话引录 / 现场复核的代码与注释原文**不改** ✓）；**完成区 / 审阅记录 = 历史记录，不改写** ✗。真源 = `ADR-0029` §修订注记、`spec/SimRISC-05 §3.4`、`spec/Toolchain-01 §3.2`/`§5`。

> **本册边界** ✗：只做 **QEMU 侧解码 + 语义 + 本模块向量 / 证据**；**不改** `spec/` ✗（归 `SPEC-145t`）、**不改** LLVM / lld ✗（归 `LLVM-095t`）、**不建**重定位类型 ✗。判据 = **执行语义**（L3 + 独立 oracle），**非**「能编译」。

## 执行环境
**执行环境**：本地

## 目标（交付物）

1. **解码**：`0x5A` 由「保留（UNDI）」变为**合法指令** `aip.si`（`riii`）；`components/qemu/patches/target/dadao/insn.decode.patch` 与 `contracts/opcodes.yaml`（`SPEC-145t` 冻结）**逐条一致**。
2. **语义**：`rbHA = IP + (sign_extend(imms18) << 12)`；其中 **`IP` = 该指令自身地址** = `rb0` 读出值（**非下一条**）；**`<< 12` = 4 KB 块、无 `<< 2`**；`imms18` **有符号**；**IP 低位不清零**（`IP` = 当前正在执行的指令的地址）。
3. **合法性与异常**：目的 `ha == rb0` ⇒ **ILLI**（= `dst_rb0` 规则；与既有 `rb0` 只读语义同形）；**「`0x5A` ⇒ UNDI」路径消失**（回归面：既有「未知编码 ⇒ UNDI」类向量须同步）。
4. **向量 / 证据**：QEMU 语义向量（`docs/Process-05`：**L3** 全量 + **L2** 冒烟代表集，机械派生）；一键证据**可达 FAIL**。

## 现场事实（**architect 只读预核，2026-10-16**；执行时逐条复核）

1. **解码补丁现状**：`components/qemu/patches/target/dadao/insn.decode.patch:78` 现为
   `# 0x5A: rela.si deleted (ADR-0012 D5) → reserved → UNDI`（**手写注释行**，位于 `add_si_riii_rd`(`0x59`) 与 `add_si_riii_rb`(`0x5B`) 之间）⇒ 本册须把它替换为 `aip.si` 的合法 pattern（命名 / 函数名由生成器定，见 3）。
2. **生成器与产物计数不一致（⚠️ 现场核实项）**：补丁头写 `# 234 patterns; blank cells trigger UNDI`，而生成器 `tools/qemu/generate_decodetree.py:105` 写死 `# 256 patterns`（现场核：该行为字面量，非派生）⇒ **重生成后须以产物为准**，并**核对 / 订正**该计数文案（**不留漂移**；`SPEC-145t` 后正确值应为 **235**）。
3. **生成 / 校验工具链**（复用优先，不另造）：`tools/qemu/generate_decodetree.py`（由 `contracts/opcodes.yaml` 生成）/ `tools/qemu/validate_decodetree.py`（补丁 ↔ `opcodes.yaml` 一致性、pattern 与 `trans_*` 对应）/ `tools/qemu/check_qemu_trans.py`（每条 insn 是否有 `trans_*` 定义；**默认 rc=0、`--strict` 非零**；扫不到补丁时**无条件非零**）。
4. **`rb0` / ILLI 现状**：`translate.c.patch` 已有「`rb0` = `PC` = current instruction address」（翻译期计算）与「写 `rb0` 触发 ILLI（`rb0` = PC、只读）」的既有实现（现场核：`Load rb[n] into a TCG temp. rb0 = PC` / `Writes to rb0 trigger ILLI`）⇒ 本册**复用**，不新引入寄存器模型。
5. **历史探针**：`tools/qemu/min_rom_probe_009t.py` 明标 **OBSOLETE**（`rela.si` 已删、`0x5A` = UNDI；保留为历史产物）⇒ **不改它** ✗；本册**新建** `tools/qemu/min_rom_probe_061t.py`（命名随任务号；**生成器 / 探针随产物保留**）。
6. **门控载体**：`check-qemu-semantics`（**L3**）现取 `tests/vectors/isa/{reg-shift-extend,reg-compare}.yaml` **全量**；`check-qemu-smoke`（**L2**）按 (class, mnemonic) **机械派生**代表集 ⇒ 新指令进代表集的路径由派生规则决定（**不手工挑**）。

## 范围（做项）

1. **解码**：重生成 / 更新 `insn.decode.patch` ⇒ `0x5A` 为 `aip.si`（`@main`，`ha` / `imms18` 字段位与 `add.si` 同族）；删去 `0x5A … UNDI` 手写注释；**头部 pattern 计数与产物一致**（见「现场事实 2」）。
2. **语义**：在新 `trans_*`（或既有地址运算转译）内实现 `rbHA = IP + (sign_extend(imms18) << 12)`；`IP` 取**该指令自身地址**（复用既有 `rb0` 计算口径）；`imms18` 符号扩展；目的 `rb0` ⇒ **ILLI**（复用既有检查）。
3. **异常 / 回归面**：确认「保留编码 ⇒ UNDI」路径不再覆盖 `0x5A`；排查既有把 `0x5A` 当 UNDI 的测试 / 探针（**逐条处置或登记**，不留静默悬挂）。
4. **向量**：
   - **L1 编码**（与 `SPEC-145t` 共用载体 ⇒ **串行在后**）：如需在本地复跑编码向量，复用 `SPEC-145t` 产物，**不重复造**；
   - **L3 语义**：`tests/vectors/isa/**` 增 `aip.si` 语义例（**独立 oracle**：按 `ADR-0029 D1` 公式在 host 侧派生期望值，**不从 QEMU 反推**；边界 = IP 基准是**自身地址**、`<<12`、负立即数、目的 `rb0` ⇒ ILLI、大端）；
   - **L2 冒烟**：确认机械派生代表集纳入新指令（**不手工挑**）。
5. **一键证据** `.work/evidence/<任务ID>/run.sh`（含**反例注入 ⇒ FAIL ⇒ 还原 ⇒ 回绿**；还原用 `cp` 备份 + md5 对账，**禁** `git checkout`/`restore`/`stash`）。
6. **重建与安装**：改 `components/qemu/patches/**` ⇒ `make build-qemu` rc=0 + `make install-host` rc=0（**安装根须与构建树同步**，否则 `check-qemu-semantics` 读**旧二进制** ⇒ **假绿**，`ISS-210` 同类纪律）。

## 验收标准

1. **解码**：`0x5A` 在 QEMU 侧解为 `aip.si`（无 UNDI）；`python3 tools/qemu/validate_decodetree.py <生成物>` rc=0；`python3 tools/qemu/check_qemu_trans.py --strict` rc=0（`aip.si` 有对应 `trans_*`）；补丁 ↔ `contracts/opcodes.yaml` **逐条一致**。
2. **语义（L3 + 独立 oracle）**：`aip.si` 语义例全通过；期望值**独立派生**（`ADR-0029 D1` 公式 + host 侧计算），**不从 QEMU / LLVM 反推**；覆盖 = **正 / 负** `imms18`、`ha != rb0`、**IP 基准 = 自身地址**（**关键**：与 0628 的 `PC + 4` 口径**不同** ✗）、大端。
3. **目的 `rb0` ⇒ ILLI**：≥1 例断言 ILLI（**可达 FAIL**：把检查关掉应转红）。
4. **UNDI 路径消失**：原「`0x5A` ⇒ UNDI」断言已改指向（**新目标现场派生**，禁按记忆挑）；其余保留编码仍 UNDI（**不回归**）。
5. **门控**：`make check-qemu-smoke`（L2）rc=0；`make check-qemu-semantics`（L3）rc=0 且计数**现场派生**（不写死）；`make check`（L1）rc=0；`check-patch-tree` / `check-index-blobs` / `check-no-residue` rc=0。
6. **证据**：`.work/evidence/<任务ID>/run.sh` 跑通 + 反例注入节；日志 `.work/log/qemu/QEMU-061t-*.log`。
7. **重建留痕**：`build-qemu` / `install-host` 的 rc + **申报耗时 vs 实测耗时** + 安装根二进制 mtime 晚于源码改动（防假绿）。

## 前置申报（**必读**）

- **本册必改 `components/qemu/patches/**`**（编译输入变化）⇒ **须 `make build-qemu` + `make install-host`**；**启动前现场评估并申报预计耗时**；**`JOBS=8`、禁全核**；**单跑一个长任务**、日志落 `.work/log/qemu/`、`setsid nohup` 脱离 + 落 `XXX_EXIT=$rc`（长任务由**主会话**发起；**子代理不得在会话内等待**）。
- **不得**与 `build-*` / L2 / L3 / 其它会话的重建**并发**（`ISS-229`）。
- **串行**：本册**在 `SPEC-145t` 与 `LLVM-095t` 之后**（同改 `tests/vectors/**` 载体）。
- 补丁纪律 = `docs/Process-01`（树形补丁集 / 一文件一补丁 / `git apply`）+ `check-patch-tree`。

## 不做项（显式）

1. **改 `spec/`** ✗（归 `SPEC-145t`）；**LLVM / lld / CodeGen** ✗（归 `LLVM-095t`）；**重定位类型**（`PCREL_HI`/`PCREL_LO`）✗。
2. **改 `tools/qemu/min_rom_probe_009t.py`** ✗（明标 OBSOLETE 的历史产物；新建 `…_061t.py` 代替）。
3. **`dadao-m1` 的 syscall 服务** ✗（用户 2026-10-15 裁定撤回，`QEMU-060t`；不重引入）；**`qemu-user`** ✗（`P3`）。
4. **relaxation** / **`ABS48` 两段式** / **自写 `ld.so`** ✗。
5. 跳过「重建 + 安装」直接改门控期望值 ✗（**假绿**）。
6. `ISS-222` / `ISS-223` 收口 ✗（撞上即登记 + 转出，**不得**静默跳过）。

## 完成区

**测试结果**：一键证据 `.work/evidence/QEMU-061t/run.sh` 默认 **14/14 rc=0**（`RUN_EXIT=0`）、`--inject all` **20/20 rc=0**（`RUN_INJECT_FINAL_EXIT=0`；`.work/log/qemu/QEMU-061t-run-final.log` / `-run-inject-final.log`）。分项：探针 `min_rom_probe_061t` **8/8**；L3 `run_qemu_test --batch` = `aip-si.yaml` **12/12**、`reserved.yaml` **3/3**（UNDI 不回归）、门控集（reg-shift-extend+reg-compare）**149/149**；L2 等价 `run_qemu_smoke` **86/86**；`check_qemu_trans --strict` **235/235 (M1 156/156)**；`validate_decodetree` **235/235 (0 错误)**；`validate_vectors` **156/156（712 cases, 0 gap）**；`check-patch-tree` **5 comp/147**；`check-index-blobs` **108 new + 39 skipped**；`make check`(L1) rc=0。失败原因：无。**未跑** `make check-qemu-smoke`/`check-qemu-semantics`（二者读**安装根**旧二进制 ⇒ 假绿；见遗留①）。
**修改文件**（v5 跟踪面 **6 改 + 1 新**）：`components/qemu/patches/target/dadao/insn.decode.patch`、`components/qemu/patches/target/dadao/insn_trans/trans_arith.c.inc.patch`（二者均 `make_patch` 重生成，非手改）、`components/qemu/changelog.md`、`tools/qemu/generate_decodetree.py`、`tests/vectors/isa/aip-si.yaml`、`tests/vectors/inventory.md`、**新** `tools/qemu/min_rom_probe_061t.py`；新增证据器（未入 git，`.work/**`）：`.work/evidence/QEMU-061t/{run.sh,oracle_aip.py,decode_check.py,smoke_derive.py,inject.py}`。**未改** `spec/`·`contracts/`·`.tao/contracts/`·`components/llvm-project/**`·`tests/**` 既有他件。⚠ 工作树里 `components/llvm-project/**`+`tests/llvm/lit/MC/DADAO/pcrel-specifier.s`+`.tao/tasks/llvm/LLVM-095t*` 的改动**非本笔**（前序串行册 LLVM-095t）。
**验收结果**（逐条对齐任务书「验收标准」）：① 解码：`0x5A` → `aip_si_riii_rb 01011010…@main`（**无 UNDI**），`validate_decodetree` rc=0、`check_qemu_trans --strict` rc=0、补丁 ↔ `opcodes.yaml` 一致（235 条、逐条一致）；② 语义：6 条 L3 例全通过，期望值由 `oracle_aip.py` **独立派生**（`contracts/opcodes.yaml` field 位 + SimRISC-05 §3.4 公式 + harness 布局 `IP = BINARY_BASE + 4*loader_words`）覆盖 正/负 imms18、`ha != rb0`、**IP = 自身地址**（例 9）、大端（harness 原生）；③ 目的 `rb0` ⇒ ILLI：探针 `aip_dst_rb0_illi` + 向量 Case 5（`expected_fault: ILLI`）通过，且**关掉该检查 ⇒ 探针+向量转红**（注入证明）；④ UNDI：`reserved.yaml` 3/3 仍 UNDI（Case 2 已改指向 op=0x58），`0x5A` 不再是 UNDI（旧安装根二进制跑同 6 例 ⇒ 全 `UNDI 0x89` 失败，反向佐证）；⑤ 门控见「测试结果」；⑥ 证据脚本跑通 + 三路注入节（见审阅记录）；⑦ 重建留痕：**仅做**针对性增量自检 `ninja -C .work/build/qemu -j8 qemu-system-dadao` rc=0（首测 **8.72 s**，注入往返各 rc=0）；`make build-qemu`/`make install-host` 按指令**未跑**（归主会话）。
**新发现/坑**：① **生成器硬编码 `256 patterns` 属长期漂移**（`SPEC-109t`/`QEMU-040t`/`SPEC-100t` 均只改产物、注「工具非门控、属既有漂移」）⇒ 本笔改为 `len(records)` 派生（根因消除），并加「committed insn.decode == 生成器输出 ⇔ 未手改」断言；② **`aip-si.yaml` 2 条 L1 word 与 notes 声明的 `imms18` 不符**（`0x5A04FFFF`→实际 +65535 而 notes 称 −1；`0x5AFCFFFF`→+65535 而 notes 称 +131071；`validate_vectors` 只校验 `(word&mask)==value`，**结构检查抓不到**）⇒ 判据 = field 独立派生；③ 手写期望值**必须现场验证**：本笔自写 Case 8 期望值多一个 `F`，正是被 harness 现场 FAIL 抓出；④ harness 的「比较失败」路径表现为 QEMU `abort`（`Unsupported SemiHosting SWI 0x00` / exit `0x-6`）而非 exit 1（`br.nz` 偏移落在 pass 段 trap 上、块未写入）——排障时勿误判为模拟器缺陷；⑤ **安装根未同步 ⇒ 假绿**：旧二进制跑门控集 **149/149 全绿**、而跑 `aip-si.yaml` 6 例**全红 UNDI**（`ISS-210` 的现场实证）。
**遗留问题**：① **`make build-qemu` + `make install-host` 须由主会话执行**（本笔按指令只做 `.work/build/qemu` 增量自检）：之后须复核 `make check-qemu-smoke`(L2)/`check-qemu-semantics`(L3) 且核安装根二进制 mtime 晚于 `components/qemu/patches/**` 改动（本笔临时二进制 `.work/build/qemu/qemu-system-dadao` = `0x35063904`@18:35 vs 安装根 `0x35062136`@**10-15 21:59**）。② **L2 门控载体未含 `aip-si.yaml`** ⇒ 机械派生代表集**未**纳入 `aip.si`（86 条中 0 条；加入后 90 条、含 4 条 `aip.si` 组，见 `smoke_derive.py`）；扩载体（`run_qemu_smoke.py::GATE_VECTORS` + `Makefile` 的 `for v in …`）属共享文件且只能在 `install-host` 后以真门控验证 ⇒ **登记待裁定**。③ `tools/qemu/min_rom_probe_009t.py` 顶部仍写「op=0x5A is now UNDI…DO NOT RUN」（本册不做项 2 明令不改）⇒ 现已在语义上可达、且按已废止的页对齐口径期望 ⇒ **登记**。④ `tools/testcases/009t-audit.py` 对 `aip.si` **无 oracle**（`Recomputed: 0`；其现存 mismatch 全在**未改**文件、非本笔引入）⇒ 本笔以 `oracle_aip.py` 补该缺口，audit 侧**登记**。⑤ 按下发指令**未改任务 `**状态**`**（仍 `待开始`）。

### 台账迁入（2026-10-18，`INFRA-091t`；原只在 `milestones.md` 流水行）

- `ISS-237`：`smoke_derive.py` 派生逻辑过时 ⇒ **脚本 stale、非功能缺陷**（不影响 L2/L3 判定）。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：`insn.decode.patch`/`trans_arith.c.inc.patch`（`.work/source/qemu` → `make_patch` 重生成，2 行 + 18 行）、`generate_decodetree.py`（1 行）、`aip-si.yaml`（+6 例、订正 2 word、头部注记）、`inventory.md`（1 行）、`min_rom_probe_061t.py`（新）、证据器 5 份；逐行核对语义/边界/复原/防造假。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（真值对齐）自写 Case 8 期望值 `0xFBFFFFFFFFF000` 多一个 `F`（正确 `0xFBFFFFFFF000`） | ✅已修 | `aip-si.yaml` Case 8 期望值 + notes | harness `aip-si.yaml[8]` FAIL(`0x-6`) → 改后 12/12 rc=0；`oracle_aip.py` 同值 PASS |
| F2（抓到的既有缺陷）Case 2/3 的 word 与其 notes 声明的 `imms18` 不符（`bits[17:0]` 各为 `0x0FFFF`） | ✅已修 | word → `0x5A07FFFF`（−1）/`0x5AFDFFFF`（+131071），notes 加「word 订正记」 | field 派生（`oracle_aip.py`：rbha/imms18 由 `opcodes.yaml` 位域 + `0x5A` 重算）PASS；`validate_vectors` rc=0 |
| F3（漂移根因）生成器写死 `256 patterns`；产物 `234` | ✅已修 | `generate_decodetree.py`：`f"# {len(records)} patterns; …"`；产物重生成（**不手改生成物**） | `decode_check.py`：`committed == 生成器输出`、`header==len(records)==235`、旧 UNDI 注记 0 处、`0x5A` 落在 `0x59`/`0x5B` 之间 ⇒ PASS |
| F4 L2 门控载体（`GATE_VECTORS`）未含 `aip-si.yaml` ⇒ 代表集不含 `aip.si` | ⏸延后（登记） | 无（不擅自扩共享门控载体） | `smoke_derive.py` 现场机械派生：现状 86 条（aip.si 0 条）/加入后 90 条（4 条 aip.si 组）PASS；`run_qemu_smoke` 86/86 rc=0 |
| F5 `min_rom_probe_009t.py` 顶部注记仍称 `0x5A`=UNDI（本册明令不改） | ⏸延后（登记） | 无 | 完成区遗留③；该文件不在任何 Makefile 目标（`MIN_ROM_PROBE` 仅 046t） |
| F6 `009t-audit.py` 对 `aip.si` 无 oracle（`Recomputed: 0`）；其 mismatch 全在未改文件 | ⏸延后（登记） | 无（非门控） | `git status -uall`：mismatch 涉及文件均未改；本笔另立 `oracle_aip.py` 补该族 |
| F7 还原纪律：注入还原一律 `cp`+md5，禁 `git checkout/restore/stash` | ✅已核 | `inject.py`（备份+md5 对账）；`inject.py` 的 apply 由「备份存在即拒」改为「**仅当目标==备份**才续跑」（可重跑） | `--inject all`：3 路注入 apply/restore 的 md5 三态一致（`a95158aa…`/`82499847…`）⇒ 20/20 rc=0；`git -C .work/source/qemu status --porcelain` 空 |
| F8 证据脚本自审：`chk()` 用 `out=$(…)` 捕 rc（**无管道吞码**）；`inject_cycle` 原用 `cmd || {…}; rc=$?` 会把 rc 记成块内末命令 | ✅已修 | `run.sh` 改为直接 `cmd; rc=$?`，再 `[ rc -eq 0 ] ||` 计 FAIL | `--inject all` 20/20 rc=0；日志 `.work/log/qemu/QEMU-061t-run-inject-final.log` |
| F9 实现一致性自审：imm18 重建/符号扩展与 `add.si_riii_rb` 同族；`((int64_t)imm18)<<12` 先窄化前转换（避 int32 UB）；`a->ha==0` 检查先于 `store_rb`（`store_rb(0)` 静默）；结果全 64 位 | ✅已核 | 无（实现即如此） | 探针 `aip_max_pos`（imm=+131071 ⇒ bit48=1）PASS ⇒ 证明无 48 位截断；`dst_rb0` 注入转红 ⇒ 检查确实生效 |

**判决**：F1/F2/F3/F7/F8 已修并复验，F9 核过；F4/F5/F6 为**延后 + 登记**项（附原因与替代证据），**无未修 finding**。按下发指令**不改任务 `**状态**`**（仍 `待开始`），由主会话处置。


#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

#### 第 1 轮 reviewer 验收（QEMU-061t，2026-10-17）

**重跑记录**（独立执行）：
- `make check`(L1)：**rc=0**（末行 `repository checks (L1): PASS`）
- `make check-qemu-smoke`(L2)：**rc=0**（90/90，aip.si present: True）
- `make check-qemu-semantics`(L3)：**rc=0**（161/161 = 113+36+12）
- `make check-full`(L3)：**rc=0**（check-qemu-semantics 161/161、check-lit-full 12/12、diff_ir_lli 19/19、run_embench 38/38）
- `bash .work/evidence/QEMU-061t/run.sh`：13 passed / 1 failed（L2 derivation 脚本逻辑过时，见下）
- `bash .work/evidence/QEMU-061t/run.sh --inject vector`：注入→FAIL→还原→回绿 ✓

**QEMU 语义 + oracle 独立性**：
- oracle_aip.py 声明：仅读 `contracts/opcodes.yaml`（编码）+ `spec/SimRISC-05 §3.4`（语义）+ harness 布局，不读 QEMU/LLVM ✓
- 独立重算 2 例：① case[9] IP=0xFC0000000004（自身地址，非 PC+4）+ imms18=0 ⇒ rb1=0xFC0000000004 ✓ ② case[5] rbha=rb0 ⇒ expected_fault=ILLI ✓
- 语义覆盖：正/负 imms18、IP=自身地址、大端、dst_rb0⇒ILLI ✓

**门控真实性**：L3 载体含 aip-si.yaml（Makefile:881）✓；计数 149→161（+12 aip-si cases）✓；注入 aip-si.yaml[7] 期望值 ⇒ 真门控 rc≠0 + 日志 `FAIL aip-si.yaml[7]` ⇒ `cp` 还原 ⇒ rc=0 ✓

**安装根新鲜度**：qemu-system-dadao mtime=18:35:19、md5=`a11b2a4e…` 与构建树产物相同、晚于补丁 mtime ✓

**finding**：smoke_derive.py L2 derivation 检查失败（脚本导入 GATE_VECTORS 后再加 aip-si.yaml 无增量，`k[0]=="aip-si.yaml"` 不匹配）——属脚本逻辑过时，非功能缺陷（实际 L2 gate 90/90 + aip.si present=True）。

**边界/如实性**：完成区数字与真实输出一致 ✓；reserved.yaml 3/3 UNDI 不回归（Case 2 已改指向 op=0x58）✓；ISS-232/234/235/236 如实登记 ✓

**判决**：**Accepted**（QEMU-061t）。语义正确、oracle 独立、门控全绿、反例可达 FAIL。smoke_derive.py 的逻辑过时为非阻塞 finding（登记）。

### 新安装根复核 完成记录（2026-10-16；**只读**复核；**未**重建 / **未**改代码 / **未**改 `**状态**`）

**背景**：工具链已由主会话重建 —— `install-host` **PASS**、`INSTALL_EXIT=0`（`.work/log/llvm/QEMU-061t-install.log`：`start=2026-10-16 18:37:06` → `end=18:43:18`）。本块 = 对新安装根复核本册交付（LLVM 侧见 `LLVM-095t` 册同名块）。

**① 安装根新鲜度**：安装根 `qemu-system-dadao` mtime = **18:35:19**、md5 = `a11b2a4e4885c37393736f0ba0feaacf`，与**同代构建树产物**（`.work/build/qemu/qemu-system-dadao`）**md5 相同**（同一二进制），且**晚于**两件 QEMU 补丁（`insn.decode.patch` / `insn_trans/trans_arith.c.inc.patch` mtime = **18:21:27**，md5 `3418721f…` / `13fca19d…`）⇒ 非旧根度量（`ISS-210`）；**尺寸 35063904 ≠ 交付时记录的旧根 `35062136`@10-15 21:59** ⇒ 确已换新。LLVM 侧三件（`clang`/`llvm-mc`/`lld`）同表见 `LLVM-095t` 块。

**② L2 / L3 门控（真 rc + 现场计数）**：`make check-qemu-smoke`（**L2**）**rc=0**（`QEMU: total=86 passed=86 failed=0 deferred=0 errors=0`；代表集 86 条 = boundary 14 + encoding 24 + legality 24 + semantic 24，源 = `reg-shift-extend.yaml` + `reg-compare.yaml`、24 个 mnemonic）；`make check-qemu-semantics`（**L3**）**rc=0**（`Results: 149 total, 149 passed, 0 failed, 0 deferred, 0 errors`）。二者取 `QEMU_BIN = $(HOST_TOOLCHAIN_BIN)/qemu-system-dadao`，`python3 tools/infra/paths.py host_toolchain_bin` 现场 = `/mnt/tao/DADAO-v5/.dadao/cross-toolchain/bin` ⇒ **门控读的就是本笔新安装根**（日志 `.work/log/qemu/QEMU-061t-recheck-L2-smoke.log`、`.work/log/qemu/QEMU-061t-recheck-L3-semantics.log`，即门控自写的 `.work/log/qemu/check-qemu-smoke.log`、`.work/log/qemu/check-qemu-semantics.log`）。

**③ 新安装根跑 `aip-si` 绿**：`python3 tests/scripts/run_qemu_test.py --batch … --qemu .dadao/cross-toolchain/bin/qemu-system-dadao --jobs 8` ⇒ `aip-si.yaml` **12 total / 12 passed / 0 failed rc=0**；`reserved.yaml`（保留编码 ⇒ UNDI 不回归）**3/3 rc=0**；`tools/qemu/min_rom_probe_061t.py --qemu <安装根>` **8/8 PASS rc=0**（含 `aip_ip_low_bits` / `aip_ip_tracks_pc` / `aip_max_pos` / `aip_min_neg` / `aip_dst_rb0_illi`）。

**④ 证据脚本现场**：`bash .work/evidence/QEMU-061t/run.sh --inject vector` ⇒ **16 passed / 0 failed、`RUN_EXIT=0`**（`.work/log/qemu/QEMU-061t-recheck-inject-vector.log`）；注入（改向量期望值 `0xFC0000001000`→`…2000`）⇒ `vectors rc=1` + `oracle rc=1` **真红**（可达 FAIL）⇒ 还原 ⇒ `probe/vectors/oracle rc=0` **回绿**；还原三态 md5 一致 = `8249984794c2ad04b01f48a11b7f79de`（另经 `cp` 安全备份 `cmp` 复核 ✓ —— **未**用 `git checkout/restore/stash`）。

**⑤ 独立复核（不复用既有判定）**：`bash .work/evidence/recheck-061t/run.sh [--inject]` ⇒ **37/37 rc=0** / **`--inject` 45/45 rc=0**（含本册面：C1 新鲜度、C4 L2 86/86、C5 L3 149/149、C6 安装根 qemu `aip-si` 12/12 + `reserved` 3/3）。

**测试结果**：见上（L2 rc=0 86/86；L3 rc=0 149/149；安装根 qemu 12/12 + 3/3 + 探针 8/8；证据脚本 16/16；独立复核 37/37 + 45/45）。**修改文件**：**无**（本册交付文件一字未改 —— `git status -uall` 项数与开工一致 = **12**，且 `tests/vectors/isa/aip-si.yaml` md5 未变 `82499847…`）；本笔只**追加**本块 + 新增只读复核证据器 `.work/evidence/recheck-061t/`。
**新发现/坑**：① 旧根「`0x5A` ⇒ UNDI」假红的**对照现场不可重跑**（旧二进制已被 `install-host` 覆盖）⇒ 本笔以「安装根尺寸 `35062136`→`35063904` + 与构建树 md5 相同 + `reserved.yaml` 3/3 UNDI 不回归」替代（附披露）；② 本册 `run.sh --inject all` **会 `ninja` 重建构建树二进制**（`inject_cycle scale|dst_rb0`）⇒ 本笔按「**不重建**」指令只跑 `--inject vector`（不需重编译，注入只在向量面）。
**遗留问题**：① **L2 门控载体未含 `aip-si.yaml`**（机械派生代表集 86 条中 `aip.si` **0** 条；扩载体属共享文件）⇒ 与交付时一致，**本笔复核未改**，待裁定；② 旧根对照不可重跑（见「新发现①」）；③ `check_mc` A16 跨笔陈旧期望（安装根无关）⇒ 见 `LLVM-095t` 册块「遗留问题①」；④ 按下发指令**未改任务 `**状态**`**（仍 `待开始`）。

#### 第 2 轮 engineer 自审（新安装根复核）

**自审方式**：自主逐行审查本笔在 qemu 面上的全部复核动作 + 共用只读复核器（`.work/evidence/recheck-061t/recheck.py`、`run.sh`，F1–F4 详见 `LLVM-095t` 册同名自审轮）；真值全部取自当次输出（`.work/log/qemu/QEMU-061t-recheck-*.log`、`.work/log/recheck-061t/run.log`、`.work/log/recheck-061t/run-inject.log`）。（本卷 `subagent_depth=1` ⇒ 不另起子代理。）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·**误跑重建面**）本册 `run.sh --inject all` 的 `scale`/`dst_rb0` 两路会 `ninja` 重建构建树二进制 ⇒ 与「**不重建**」指令冲突，且会扰动安装根 ↔ 构建树的 md5/mtime 对账 | ✅绕行（记录） | 只跑 `--inject vector`（向量面注入，零重编译）；`--inject all` **未跑**并披露 | `--inject vector` ⇒ 16/16 rc=0；构建树/安装根 md5 全程未变（`a11b2a4e…`） |
| F2（自审发现·**写死计数**）C6 期望条数原为字面量 12/3 | ✅已修 | 改 `count_cases(<向量文件>)` 现场统计 | `C6 … total=12 passed=12 (文件 case 数=12)`、`reserved 3/3 (文件 case 数=3)` |
| F3（核过·非 finding）L2/L3 门控**确实**读安装根（非构建树） | ✅已核 | 不改 | `QEMU_BIN = $(HOST_TOOLCHAIN_BIN)/qemu-system-dadao`；`python3 tools/infra/paths.py host_toolchain_bin` = `…/.dadao/cross-toolchain/bin` |
| F4（核过·非 finding）向量注入的**还原**是否可信（共享工作树文件） | ✅已核（附安全备份） | 不改（沿用 `inject.py` 的 `cp`+md5；本笔另做 `cp` 安全备份与 `cmp`） | 三态 md5 = `8249984794c2ad04b01f48a11b7f79de`；`cmp` 对安全备份一致；`git status -uall` 仍 12 项 |
| F5（真值对齐）块内数字（86/86、149/149、12/12、3/3、8/8、16/16、37/37、45/45）逐字取自当次输出 | ✅已核 | 不改 | 上述日志现场输出 |

**判决**：F2 已修并复验；F1 为**指令冲突的绕行 + 披露**；F3–F5 核过。**无未修 finding**（L2 载体未含 `aip-si.yaml` = 交付时既有登记项，非本笔引入）。⇒ 复核结论：**安装根本册面新鲜度成立**、L2/L3 **真 rc=0**（86/86、149/149）、**安装根** qemu 跑 `aip-si` **12/12 绿** + `reserved` 3/3（UNDI 不回归）+ 探针 8/8、证据脚本 `--inject vector` **16/16**（含可达 FAIL + 还原回绿）。按指令**不改 `**状态**`**。

### 收尾遗留处置 + L2/L3 全卷 完成记录（2026-10-16；按主会话裁定处置四条遗留）

**背景 / 判据边界**：主会话裁定处置四条遗留 —— ① 修 `check_mc` **A16**（改**按 field 派生**，**不**放宽断言）② `--show-encoding` **不动**（登记保持）③ 把 `aip-si.yaml` **纳入 L2 代表集** ④ **补跑全卷 L2/L3**。⚠️ 全程**未重建**、**未** commit/push、**未改**任务 `**状态**`（`LLVM-095t` 册同名块 = A16 证据侧详录）。

**① A16 派生化（`LLVM-095t` 证据侧；本册面 = 承认其现场红为「他笔陈旧期望」）**：改前 `check_mc.py` A16 硬编码 **6 个 `encoding.word`**（含 `0x5A04FFFF`/`0x5AFCFFFF`）**且**写死 `id/mnemonic == 6`（现场 `aip-si.yaml` 实为 **12** 例）⇒ `check_mc` 现状 **16 passed / 1 failed**（`FAIL A16 vectors … id=12 mnem=12 words=[]`）。改后 A16 拆四面：`A16`（跟名，条数按 YAML 现场统计）/ `A16b`（**field 派生编码**：`opcodes.yaml` 位域+掩码覆盖 32 位、`encode(全零)==value`，及 `encoding` 类 notes 等价**字节**写法 `imms18 = bytes >> 12` 派生 word）/ `A16c`（`SimRISC-05 §3.4` 语义重算，`IP = BINARY_BASE + 4*loader_words` 由 harness **现场派生**）/ `A16d`（位宽派生极值覆盖 `rbha ⊇ {0,63}`、`imms18 ⊇ {-131072,+131071}` + `dst_rb0` 规则）⇒ **期望值零字面量**；`check_mc --root .` = **20 passed / 0 failed rc=0**；`inject.py` **31/31 rc=0**（基线 + **30 条**定点反例，含新增 6 条 A16 派生面）。**可达 FAIL 演示**（真实仓库；`cp` 备份 + md5 对账还原，**未**用 `git checkout`/`restore`/`stash`）：Case 3 word 还原 `0x5AFDFFFF → 0x5AFCFFFF` ⇒ **rc=1** 且 `FAIL A16b vectors-decode … ['case[3] notes「aip.si rb63, 536866816」派生 word=0x5AFDFFFF ≠ 实际 0x5AFCFFFF']` ⇒ `cp` 还原（`cmp` 逐字节一致、md5 三态 `8249984794c2ad04b01f48a11b7f79de`）⇒ **rc=0、20/0**（日志 `.work/log/llvm/QEMU-061t-A16-inject-rerun.log` / `-restore-rerun.log`）。

**② L2 代表集纳入 `aip-si.yaml`（本笔唯一 v5 跟踪面改动）**：**现场定位** L2 载体 = `tests/scripts/run_qemu_smoke.py::GATE_VECTORS`（`make check-qemu-smoke` 调它；代表集按 `(class, mnemonic)` **机械派生**，Makefile **不**列向量）⇒ 改为 `(reg-shift-extend.yaml, reg-compare.yaml, aip-si.yaml)`。**条数变化**：源 mnemonic **24 → 25**、代表集 **86 → 90**（+4 = `aip.si` 的 encoding/legality/semantic/boundary 各 1 条；现场派生清单 = `0x5A040000`/`0x5A000000`/`0x5A040000`/`0x5A21FFFF`）；**未**把全部 ISA 向量塞进 L2（保持代表集语义）。门控 `make check-qemu-smoke` **rc=0、90/90**（`QEMU: total=90 passed=90 failed=0 deferred=0 errors=0` + 结构断言 PASS）。

**③ 补跑全卷（真 rc / 计数）**：**L1** `make check` **rc=0**（31 s；末行 `repository checks (L1): PASS`、`Error` 0 处）；**L2** `make check-modules` **rc=0**（94 s；末行 `module checks (L2): PASS` —— `check-interface`(INTEG-003t) 全 PASS、`check-lit` **109/109**〔含 `pcrel-specifier.s` #27、`aip-si-imm.s` #108〕、`check-qemu-smoke` **90/90**、`test-codegen`/`test-elf`/`test-semihost`/`check-picolibc-tests` PASS）；**L3** `make check-full` **rc=0**（64 s；`CHECK_FULL_EXIT=0`；末行 `full checks (L3): PASS` —— `check-qemu-semantics` **149/149**、`check-lit-full` **12/12**、`diff_ir_lli` **19/19**、`run_embench_e2e` **38/38**）。日志 `.work/log/qemu/QEMU-061t-L1-make-check.log` / `-L2-make-check-modules.log` / `-L3-make-check-full.log`；marker `.work/log/qemu/QEMU-061t-L3-full.EXIT`。⚠️ **披露**：`test-m6` 的**前置**含 `install-host` ⇒ L3 顺带跑了 `build-mc`/`build-lld`/`build-qemu`/`install-host`：`ninja: no work to do`（mc/lld **零编译**）、`build-qemu` 仅 `[1/20] Generating qemu-version.h` ⇒ **零重编译**；安装根四件二进制 md5 与 18:3x 记录**逐件相同**（`457f62b0…`/`59f5b7f2…`/`7413f669…`/`a11b2a4e…`）、mtime 未变 ⇒ **未重建**（单跑、无并发；`ISS-229` 未犯）。

**④ `--show-encoding`（只复核登记、不修）**：登记文本与现状**逐条一致** —— ① 低半 `rb4`（`rbha ≥ 4`）`--show-encoding` ⇒ **SIGABRT rc=134**、文案逐字 `Assertion \`Bit == 0 && "Encoder wrote into fixed up bit!"' failed.`（`MCAsmStreamer.cpp:134`）；② `rb1` 同文本 ⇒ **rc=0** 且打印 `fixup … kind: DADAO_FK_PCREL_HI/LO`；③ `-filetype=obj` ⇒ **rc=0** 且两条记录（`R_DADAO_PCREL_HI extg 0x0` + `R_DADAO_PCREL_LO .text 0x4`）⇒ 缺陷**只影响该显示模式**、判据未变 ⇒ **按裁定不修**、登记保持（日志 `.work/log/llvm/QEMU-061t-show-encoding-recheck.log`；install root `llvm-mc` md5 `59f5b7f2…`）。

**测试结果**：`bash .work/evidence/LLVM-095t/run.sh --inject` ⇒ **22/22 rc=0**（`checks: 22 passed, 0 failed`，203 s；含 `check_mc` **20/0**、`x1_roundtrip` 7/0、`post_build` 25/0、lit `pcrel-specifier.s` PASS、三套注入 `31/0`·`27/0`·`10/0`、`make check`(L1) rc=0、`check-isa-coverage` rc=0）；L1/L2/L3 见 ③。日志 `.work/log/qemu/QEMU-061t-runsh-final.log` / `-final2.log`。
**修改文件**：`tests/scripts/run_qemu_smoke.py`（`GATE_VECTORS` +1 载体 + 注记 —— **唯一** v5 跟踪面改动）；`.work/evidence/LLVM-095t/{check_mc.py,inject.py,run.sh,README.md}`（证据侧；`git status` 不显示）；本任务书 + `LLVM-095t` 册（**追加**本块与自审轮；**未改** `**状态**`）。**未改** `spec/`·`contracts/`·`.tao/contracts/`·`components/**`·`Makefile`·`tests/vectors/**`（后者仅他笔既有改动）。⚠ `git status -uall` = **13** 项（开工 12 + `run_qemu_smoke.py`），无残留。
**验收结果**（门控；写块前/后各复跑一次，rc 与计数一致；日志 `.work/log/qemu/QEMU-061t-final-<gate>.log`）：`check-patch-tree` **rc=0（5 comp / 147 patches）**、`check-index-blobs` rc=0（108 new + 39 modification）、`check-source-state` rc=0、`check-no-residue` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0（0 悬空）、`check-component-changelog` rc=0、`check-issues` rc=0（41 open / 13 closed）；`make check`(L1) rc=0。
**新发现/坑**：① **陈旧期望不止字面 word**：`aip-si.yaml` 由 6 例增至 12 例 ⇒ `id/mnemonic == 6` 的**写死计数**同样转红 ⇒ 期望值须「**现场派生**」（word 由位域/notes 派生、条数由 YAML 派生；`inject.py` 的基线亦去掉写死条数）。② **派生读新真源 ⇒ 注入器的复制清单须同步**：A16 新增读 `contracts/opcodes.yaml` + `tests/scripts/build_test_binary.py` ⇒ `inject.py` 的 `REL` 必须同步（否则临时树副本缺文件 ⇒ 基线假红）；缺 harness ⇒ `A16c` **响亮 FAIL**（非静默跳过；临时树探针实测 rc=1）。③ **`make check-full` 的 `install-host` 前置**：源码未变时 `ninja` = `no work to do`、安装步骤重跑但 md5/mtime 不变 ⇒ 「未重建」须以 `ninja` 输出 + md5 对账取证，不能只看目标名。④ L3 门控 `check-qemu-semantics` 的载体清单仍是 Makefile 内**硬编码两文件**（`for v in …`）⇒ `aip.si` 的 L3 语义证据来自本册证据器/探针 + L2 代表集，**未**并入 L3 载体（登记）。⑤ **门控自伤复发**：新块初稿的 `.work/**` 引用写了「花括号 + 通配」缩写（`L{1,2,3}-*.log`）⇒ `check-knowledge-refs` 当场打红（rc=1 / 1 悬空，落点在被引册）——**该坑本册第 2 轮已记过一次**（F4）⇒ 结论：`任务书/台账` 内的 `.work/**` 引用一律写**显式完整路径**，禁用花括号/通配缩写。
**遗留问题**：① **L3 载体未含 `aip-si.yaml`**（`Makefile` 的 `for v in …`）⇒ 登记待裁定（本笔按指令只扩 L2）；② `--show-encoding` 低半缺陷**保持不修**（登记）⇒ 修法仍归下一笔（须动 `DADAOAsmBackend` 元数据，且被 `A7`/契约 §2.2 钉住）；③ 本册原遗留 ③④（`tools/qemu/min_rom_probe_009t.py` 顶注仍称 `0x5A`=UNDI；`tools/testcases/009t-audit.py` 对 `aip.si` 无 oracle）**仍未处置**（不在这四条裁定内）；④ 按下发指令**未改任务 `**状态**`**（仍 `待开始`）。

#### 第 3 轮 engineer 自审（收尾遗留处置 + L2/L3 全卷）

**自审方式**：自主逐行审查本笔改动（`run_qemu_smoke.py` 的载体行 + 注记；证据侧 `check_mc.py` 的 A16 四面、`inject.py` 复制清单/注入/基线、`run.sh` 与 `README.md` 标签）+ 逐条反查新断言的**可达 FAIL** + 全卷/门控日志逐条对账；真值全部取自当次真实输出（本卷 `subagent_depth=1` ⇒ 不另起子代理）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·L2 载体面）扩载体后代表集 +4，是否触碰结构断言（`class`/`mnemonic` 全覆盖）或引入非代表语义 | ✅已核（真门控实测） | 不加例外、不手工挑（保持机械派生） | `make check-qemu-smoke` **rc=0、90/90**；`源 mnemonic 25 个`、`代表集 90 条`、`结果: PASS（代表集全绿 + 结构断言通过）` |
| F2（自审发现·**写死计数**）`inject.py` 基线期望 `17 passed` 写死 ⇒ 补检查即假红 | ✅已修 | 改 `re.fullmatch(r"checks: \d+ passed, 0 failed", 末行)`；`run.sh`/`README.md` 同步去写死标签 | `inject.py` ⇒ `inject: 31 passed, 0 failed`（基线行 `checks: 20 passed, 0 failed` 现场给出）；`run.sh --inject` ⇒ 22/22 |
| F3（核过·披露）L3 顺带跑 `install-host` 是否等于「重建」（与指令冲突） | ✅已核（附对账） | 不改：以 `ninja` 输出 + 安装根 md5/mtime 取证「零重编译」 | `ninja: no work to do`（mc/lld）；`build-qemu` 仅 `qemu-version.h`；四件安装根 md5 = `457f62b0…`/`59f5b7f2…`/`7413f669…`/`a11b2a4e…`（与 18:3x 记录相同）、mtime 未变 |
| F4（核过·登记复核）`--show-encoding` 三探针是否与登记文本一致 | ✅已核 | 不改（按裁定不修） | ①`rb4` rc=134 + 逐字断言文案；②`rb1` rc=0 + `fixup` 行；③`-filetype=obj` rc=0 + 两条记录（日志 `.work/log/llvm/QEMU-061t-show-encoding-recheck.log`） |
| F5（自审发现·**门控抓到的自伤**）新块初稿用 `QEMU-061t-L{1,2,3}-*.log` 花括号+通配缩写引用 `.work/**` ⇒ `check-knowledge-refs` **rc=1（1 悬空）** | ✅已修 | 改为**显式三条路径**（另册（`LLVM-095t`）同处同步改） | 修前 `结果: FAIL (1 悬空 .work/** 引用)`（`.tao/tasks/llvm/LLVM-095t-…md:344 QEMU-061t-L`）；修后 **rc=0**（0 悬空）；`check-no-residue` rc=0 |
| F6（真值对齐自审）本块数字是否逐字来自真实输出 | ✅已核 | 不改：86→90、109/109、149/149、12/12、19/19、38/38、20/0、31/0、22/22、rc 与耗时均可回溯至同名日志；**未** commit/push、**未**重建、**未改** `spec/`·契约·`**状态**` | 上述日志现场输出 + `git status -uall` = 13 项 |

**判决**：F2 已修并复验；F1/F3/F4/F5/F6 核过（附现场证据）。**无未修 finding**（遗留①–③ = 登记项/裁定项，非本笔授权面）。⇒ 四条遗留**处置完成**：A16 改 field 派生（20/0，含注入⇒红⇒还原⇒绿）、`--show-encoding` 登记复核一致且不修、`aip-si.yaml` 入 L2 代表集（86→90、90/90）、全卷 L1/L2/L3 真 rc=0。按指令**不改 `**状态**`**。

#### architect 提交留痕（`QEMU-061t` 册；分支 `qemu-061t-commit`；**只追加**）

- **档位**：按下发指令取**正常提交**（无 `WIP:` 前缀）——**披露**：两册 `#### 第 1 轮 reviewer 验收` 仍为占位（**无 reviewer `Accepted` 判决**），严格按角色规则应为 `WIP:`；本笔依主会话明确指令执行，**不改任务 `**状态**`** ✗（仍 `待开始`；收尾在 reviewer 之后）。
- **提交（2 笔）**：① `260724a` = `LLVM-095t` 遗留①（4 文件，见另册留痕）；② `4a16a87` = 本册（**9 文件**：QEMU 补丁 **2** + `components/qemu/changelog.md` + `tools/qemu/generate_decodetree.py` + 新 `tools/qemu/min_rom_probe_061t.py` + `tests/vectors/isa/aip-si.yaml` + `tests/vectors/inventory.md` + `tests/scripts/run_qemu_smoke.py`（L2 载体）+ 本册）。
- **文件集对账**（`git diff --cached --name-status` vs 两册完成区「修改文件」声明）：开工 `git status --porcelain -uall` = **13 项**、`--cached` = **13 项**（11 `M` + 2 `A`）；**逐项一致、0 漏提 / 0 多提 / 0 越界**；`spec/` / `.tao/contracts/` / `contracts/` / 任务 `**状态**` = **0 命中** ✓；组件补丁 **2 份**（`insn.decode` / `insn_trans/trans_arith.c.inc`，`check-patch-tree` = 5 comp / **147** patches、无增删）。
- **完成区如实性核对**：L1/L2/L3 **真 rc** 与现场日志一致 ✓（`make check` rc=0；L2 `check-modules` rc=0〔`check-qemu-smoke` 90/90〕；L3 `check-full` rc=0〔149/149〕）；生成器「写死计数」根因消除 ✓（现场核 `generate_decodetree.py` = `f"{len(records)} patterns"`）；遗留**如实** ✓（L3 载体、`009t` 探针顶注、`009t-audit` 无 oracle 均明标未处置）⇒ **未改完成区内容** ✗。
- **issue**：`ISS-233`（L3 载体未含 `aip-si.yaml`；**现场核** `Makefile:880` 的 `for v in …` 仅两册、`check-qemu-semantics` 日志 `aip` 命中 **0**）/ `ISS-232`（`--show-encoding` 低半 SIGABRT rc=134，**须裁定**）/ `ISS-234`（`min_rom_probe_009t.py` 顶注仍称 `0x5A`=UNDI；`009t-audit.py` 对 `aip.si` 无 oracle，两件均**非门控**）—— 三条**现场复现**后登记；`check_issues.py` **rc=0（44 open / 13 closed）**。
- **门控（本笔重跑，真值 = 自身 rc）**：`make check`(L1) **rc=0**（末行 `repository checks (L1): PASS`）、`check-patch-tree` rc=0（**147**）/`check-index-blobs` rc=0/`check-source-state` rc=0/`check-no-residue` rc=0/`check-tasks` rc=0/`check-knowledge-refs` rc=0/`check-knowledge-dir` rc=0/`check-component-changelog` rc=0；日志 `.work/log/qemu/QEMU-061t-commit-make-check-L1.log`。
- **落盘**：`master` 由 `merge --ff-only` 落地、分支 `qemu-061t-commit` 已删；**未 push** ✗（`origin/master` 不动）。

### L3 载体补齐 完成记录（2026-10-17；`ISS-233` 处置 —— `aip-si.yaml` 纳入 L3 门控载体）

**背景 / 判据边界**：主会话**修正裁定** —— `ISS-233` 属**真覆盖缺口**（上一轮「已覆盖」判断不成立；现场 `Makefile:880` 的 `for v in …` **不含** `aip-si.yaml`、门控日志 `aip` **命中 0**）。本笔**只加载体这一项** ✗（不改清单其它项）、**未重建**、**未** commit/push、**未改**任务 `**状态**` ✗。

**① 载体改动（逐处原文；`git diff Makefile` = 2 hunk）**：㈠ **载体清单（唯一枚举点）** `Makefile:881`：原 `	  for v in reg-shift-extend.yaml reg-compare.yaml; do \` ⇒ 现 `	  for v in reg-shift-extend.yaml reg-compare.yaml aip-si.yaml; do \`。**别处是否另枚举**：现场 `grep -rn 'for v in reg-shift-extend.yaml'` = **1 处**（仅 `Makefile`）、`Makefile` 内 `reg-compare.yaml` 仅此 1 处 ⇒ **无第二枚举点** ✓（`tests/scripts/run_qemu_smoke.py::GATE_VECTORS` 是 **L2** 载体，早已含 `aip-si.yaml`）。㈡ **注记同步（非清单项）**：原 `# Runs all semantic/boundary cases in reg-shift-extend + reg-compare.` ⇒ `# Runs all cases in reg-shift-extend + reg-compare + aip-si (ISS-233: aip.si` / `# must be in the L3 carrier set, not only the L2 smoke set).`（防「注记 ↔ 清单」漂移）。**未改**清单其它项、未改 L2 载体、未改 `tests/vectors/**`。

**② 复跑 L3（真 rc + 现场计数）**：`make check-qemu-semantics` **rc=0**、`Results: 161 total, 161 passed, 0 failed`（**149 → 161** = `reg-shift-extend` 113 + `reg-compare` 36 + `aip-si` 12，**现场统计、不写死**）；`make check-full`(**L3**) **rc=0**（`CHECK_FULL_EXIT=0`；50 s；末行 `full checks (L3): PASS` —— `check-qemu-semantics` **161/161**、`check-lit-full` 12/12、`diff_ir_lli` 19/19、`run_embench_e2e` 38/38）。日志 `.work/log/qemu/QEMU-061t-L3carrier-L3-make-check-full.log`、marker `.work/log/qemu/QEMU-061t-L3carrier-L3-full.EXIT`。

**③ `aip` 命中（真值 / 分档披露）**：① 门控**默认摘要档**日志 `.work/log/qemu/check-qemu-semantics.log`（3 行）⇒ `grep -c aip .work/log/qemu/check-qemu-semantics.log` = **0**——该档**非 verbose（不逐例打印）**，非静默；② **同载体集 / 同命令 / 同安装根二进制 + `-v`** 的 verbose 镜像 ⇒ `grep -c 'aip-si.yaml' .work/log/qemu/QEMU-061t-L3-semantics-verbose.log` = **12**（12/12 `PASS aip-si.yaml[*]`）；③ **注入态真门控** ⇒ `grep -c aip .work/log/qemu/check-qemu-semantics.log` = **1**（`FAIL aip-si.yaml[7]`）。⇒ 覆盖**确实生效**（据 ②③ + 计数 149→161）。

**④ L2 复核**：`tests/scripts/run_qemu_smoke.py::GATE_VECTORS` = `(reg-shift-extend.yaml, reg-compare.yaml, aip-si.yaml)` **已含**；`make check-modules`(**L2**) **rc=0**（`check-qemu-smoke` **90/90**、`module checks (L2): PASS`）。日志 `.work/log/qemu/QEMU-061t-L3carrier-L2-make-check-modules.log`。

**⑤ 证据脚本（`cp`+md5 还原纪律）**：`.work/evidence/QEMU-061t-L3carrier/run.sh` ⇒ 默认 **7/7 rc=0**、`--inject` **14/14 rc=0**（C5：注入 `aip-si.yaml` case[7] 期望值 `0xFC0000001000→…2000` ⇒ 真门控 rc≠0 且日志 `aip` 命中 ≥1 ⇒ `cp` 还原（`cmp` 一致、md5 `8249984794c2ad04b01f48a11b7f79de`）⇒ 回绿）。日志 `.work/log/qemu/QEMU-061t-L3carrier-runsh.log`、`.work/log/qemu/QEMU-061t-L3carrier-runsh-inject.log`（**未**用 `git checkout`/`restore`/`stash`）。

**⑥ 未重建证明**：安装根二进制 md5 与 18:3x 记录**逐件相同**（`qemu-system-dadao` = `a11b2a4e4885c37393736f0ba0feaacf`、`clang` = `457f62b093c6a60daeb359b9e5758aa8`、`llvm-mc` = `59f5b7f20780bcc0618880aaebcb0b75`）、`qemu-system-dadao` mtime 未变（`Oct 16 18:35`）；`make check-full` 顺带 `install-host` = `ninja: no work to do`（llvm 两次）+ `build-qemu` 仅 `[1/20] Generating qemu-version.h` ⇒ **零重编译**（单跑、无并发；`ISS-229` 未犯）。

**测试结果**：见 ②④⑤（L3 真门控 rc=0 / 161-161；L3 全卷 rc=0；L2 rc=0 / 90-90；证据脚本 7/7 与 14/14）。失败原因：无。
**修改文件**：`Makefile`（唯一 v5 跟踪面代码改动 = 载体清单 +1 项 + 注记 2 行）；`.tao/knowledge/issues.yaml`（`ISS-233`：`status→closed` + `resolved_by: QEMU-061t` + notes 追加）；本任务书（**追加**本块与自审轮）。**未改** `spec/`·`contracts/`·`.tao/contracts/`·`components/**`·`tests/**`·`tools/**`。`git status -uall` = 3 项（`Makefile` + `issues.yaml` + 本任务书），无残留。
**验收结果**（门控，真值 = 自身 rc；日志 `.work/log/qemu/QEMU-061t-L3carrier-<gate>.log`）：`make check`(L1) **rc=0**（末行 `repository checks (L1): PASS`）、`check-patch-tree` **rc=0（5 comp / 147 patches）**、`check-index-blobs` rc=0（108 new + 39 modification）、`check-source-state` rc=0、`check-no-residue` rc=0、`check-tasks` rc=0、`check-knowledge-refs` rc=0（0 悬空）、`check-component-changelog` rc=0；`check_issues.py` rc=0（**43 open / 14 closed**；`open ⇒ resolved_by null` 断言满足）。
**新发现/坑**：① **L3 门控日志「不逐例」**：`check-qemu-semantics` 默认档日志 = **3 行摘要**（对比 L2 `check-qemu-smoke` 打印载体名 + 现场计数 = **自证命中**）⇒ 想从门控日志直接看「跑了哪些向量 / 命中数」**须**加 `-v` 或另做 verbose 镜像；本笔**不改**门控 verbose（超出「只加一项」）。② **计数是强证据**：「门控是否消费某向量」可用「计数增量（现场）+ 定点注入（可达 FAIL）」双证，**不必**依赖逐例日志。③ **同族漂移点**：`tests/scripts/run_qemu_smoke.py:4` 的 docstring 仍称「全量 **149** 用例」（本笔后应为 161）——行文漂移（非门控）⇒ 登记，本笔**不改**（任务未授权改该文件）。④ **载体清单唯一真源**：L3 载体仅 `Makefile` 一处 `for v in …`；新增指令须同时考虑 L2（`GATE_VECTORS`）与 L3（`Makefile`）两处载体，否则「一能力一向量」在某一层零覆盖。
**遗留问题**：① `run_qemu_smoke.py:4` 「149」字面（行文漂移，见新发现③）——登记待裁定；② 本册原遗留 ②③（`--show-encoding` 低半不修；`min_rom_probe_009t.py` 顶注 + `009t-audit` 无 oracle = `ISS-234`）**仍未处置**；③ 按指令**未改任务 `**状态**`** ✗（仍 `待开始`）。

#### 第 4 轮 engineer 自审（L3 载体补齐）

**自审方式**：自主逐行审查本笔改动（`Makefile` 2 hunk；`issues.yaml` 的 `ISS-233` 三字段；证据脚本 `run.sh` 全部检查的**可达 FAIL**）+ 逐条反查真值取自当次输出（本卷 `subagent_depth=1` ⇒ 不另起子代理）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1（自审发现·**可达 FAIL**）门控扩载体是否**真消费** `aip-si.yaml`（非仅计数） | ✅已证 | 不改：定点注入 = 唯一解释 | 注入 `aip-si.yaml[7]` 期望值 ⇒ 真门控 `make check-qemu-semantics` **rc=1**（make rc=2）、日志 `FAIL aip-si.yaml[7]`；`cp` 还原 ⇒ **rc=0 / 161-161** |
| F2（自审发现·**任务书要求 vs 现场**）要求「门控日志 `aip` 命中 > 0」但默认档仅摘要 | ✅已披露 + 替代证据 | 不改门控 verbose（超范围） | verbose 镜像 `grep -c 'aip-si.yaml'` = **12**；注入态真门控日志 `grep -c aip` = **1**；默认档 = 0（3 行摘要，非静默） |
| F3（核过·无第二枚举点）载体清单是否别处另有一份 | ✅已核 | 不改 | `grep -rn 'for v in reg-shift-extend.yaml'` = 1 处（仅 `Makefile:881`）；`run_qemu_smoke.py::GATE_VECTORS` 是 L2 载体（已成三册） |
| F4（核过·未重建）`make check-full` 顺带 `install-host` 是否等于重建 | ✅已核（附对账） | 不改 | 安装根 md5 `a11b2a4e…`/`457f62b0…`/`59f5b7f2…` 与 18:3x 记录相同、mtime 未变；`ninja: no work to do` |
| F5（自审发现·还原纪律）注入后是否留残留 | ✅已核 | 不改 | `cp` 还原 + `cmp` 一致 + md5 = `8249984794c2ad04b01f48a11b7f79de`；`git status -uall` 无 `aip-si.yaml`；**未**用 `git checkout`/`restore`/`stash` |
| F6（核过·门控）`check_issues` 对 `closed` 条目的 `resolved_by` 约束 | ✅已核 | 不改 | `python3 tools/infra/check_issues.py` **rc=0**（43 open / 14 closed；`resolved_by 约束 OK`） |

**判决**：F1/F3/F4/F5/F6 核过（附现场证据）；F2 = **任务书要求与现场门控日志形态不符**，已**分档披露 + 给等价 ≥1 证据**（verbose 镜像 12 / 注入态真门控 1），**不擅自改门控 verbose**。**无未修 finding**（遗留①–③ = 登记项 / 裁定项，非本笔授权面）。按指令**不改任务 `**状态**`** ✗。

#### architect 提交 / 文件集审核留痕（L3 载体补齐；分支 `l3-carrier-commit`；**只追加**）

**档位**：**正常提交**（按主会话给定文案，**无 `WIP:` 前缀**）—— 本笔 = `ISS-233` 真覆盖缺口的补齐笔（非返工队列项）。
**提交**：`90234a3`（分支 `l3-carrier-commit`）⇒ `git merge --ff-only` 落地 `master`（`8b757b4` → `90234a3`）⇒ 分支已删；**未 push** ✗（`origin/master` 不动，仍 `8b757b4`）。
**文件集对账**（显式 staging，`git diff --cached --name-status` vs 完成区「修改文件」）：3 项**完全一致、无漏提 / 无多提 / 无越界** —— `Makefile`（+3/−2：载体清单 +1 项 + 注记 2 行）；`.tao/knowledge/issues.yaml`（+3/−3：`ISS-233` 的 `status`/`resolved_by`/`notes`）；本任务书（+37：本块与第 4 轮自审）。提交前 `git status -uall` 无第 4 项（`.work/**` 未入库 = 既有约定，非漏提）。
**另笔（独立提交，不在本笔）**：`tests/scripts/run_qemu_smoke.py:4` 陈旧计数 `149` → `161`（= 本册「新发现/坑 ③」行文漂移）+ 新立 `ISS-235`/`ISS-236` + `INFRA-085t`「阻塞解除（2026-10-17）」指针 + `milestones.md` 两处追加。
