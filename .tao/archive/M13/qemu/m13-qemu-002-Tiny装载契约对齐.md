# m13-qemu-002: QEMU 对齐 Tiny hmon 装载契约（BootROM 固定固件 + power 搬运）

**模块**：qemu
**项目里程碑**：M13
**依赖**：`m13-qemu-001`（Tiny hmon 已实现）、`m12-spec-004`（契约已合入）
**可并行分片**：否（组件单写者）
**状态**：已验证

## 背景

`m12-spec-004` 已把 Tiny 的 hmon 装载改成：

- BootROM 是**固定固件镜像**（64 KiB：power 8K / hmon 8K / 保留 40K 全零 / 表 8K）
- power 校验 image index table → **逐 8 字节复制** hmon 段到 hmon SRAM `0x0fff_0000_0000` → 写向量（幂等）→ `trap cfx_hmon, 0x30001` → hmon `escape` 回 stub → 跳 `0xffff_ff01_0100`
- 宿主 loader **只装应用段**（`PT_LOAD` 只允许落 SRAM；向 BootROM 下发段或 `e_entry ≠ 0xffff_ff01_0100` ⇒ 显式失败）
- `crt` 与测试程序一起链接、整体落 SRAM
- `cg3 rc10`：初值 = 该 cfx 内部 SRAM 起始；写入忽略低 2 位
- `switch_run_mode`：Tiny 写入被忽略、保存值保持 3、读回保存值

`m13-qemu-001` 与 `m13-gem5-001` 实现的是**旧的**「宿主直装 hmon 段」；`m12-chipyard-007` 已按新契约实现（BootROM 固件 + power 搬运）。

**用户裁定**：这条契约「先在 qemu 中验证，然后 gem5/chipyard 可共用」——本任务即 QEMU 侧的验证与对齐。

## 目标

1. **装载路径**：QEMU 的 Tiny 装载改为「固定 BootROM 固件 + 应用」两件；宿主不再向 BootROM 下发 `PT_LOAD`；`e_entry` 必须 = `0xffff_ff01_0100`；违规**显式失败**（非默默忽略）。
2. **镜像格式**：支持 `bootrom-image`（64 KiB 原样装入 `0xffff_ffff_0000`）；image index table 格式与 `§6.1` 一致（magic `DBOT`、version 1、count 1、`boot_magic=0x30001`）。
3. **power 行为**：若 QEMU 以「执行固件」方式实现，需真实执行 power stub 的复制逻辑；若以「模型直接映射」方式实现，**必须**在日志/状态上等价（hmon 段落在 hmon SRAM、向量已写），并在任务书里说明选择与理由。
4. **`rc10` 与 `switch_run_mode`**：按 `spec-003/004` 口径对齐（写未对齐 ⇒ 掩掉低 2 位；Tiny 的 `switch_run_mode` 读回 3）。
5. **与 chipyard 共用**：用 `m12-chipyard-007` 的 BootROM 镜像与同一 app ELF，在 QEMU 上跑通；给出逐字节对齐证据（hmon 在 SRAM 的内容、向量值、入口）。

## 非范围

- 不改 gem5（`m13-gem5-005` 并行做）
- 不改 chipyard
- 不改 spec

## 验收标准

1. 新契约下 `power → hmon → app` 闭环在 QEMU 上可观测（向量写入、`trap` magic、hmon 入口、`escape` 返回、跳入口）
2. 反例三条各 rc≠0 且报错具名：向 BootROM 下发 `PT_LOAD`、`e_entry ≠ 0xffff_ff01_0100`、BootROM 镜像非 64 KiB
3. 与 chipyard 共用同一 `bootrom.tiny.img` + 同一 app ELF：hmon SRAM 内容**逐字节相同**、入口/向量一致
4. `rc10` 未对齐写入 ⇒ 掩低 2 位；`switch_run_mode` 写 0 ⇒ 读回 3
5. 回归：`tests/inst` Tiny 子集 44/44、Vast 980/985 不变；`check-inst`/`check-arch-smoke`/L2 rc=0
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 说明

- 必须在独立 `git worktree` 内作业（`ISS-368`）；不占用 207/208。
- 组件单写者；补丁走 `make_patch`。
- 若 QEMU 侧无法真实执行 power 固件（只做模型映射），**必须在任务书写明等价条件与限制**，不得静默降级。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号），禁改主工作树。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进；需要裁定写进任务书并返回主会话。
6. 复杂命令输出留存运行期日志目录。
7. 一键证据脚本；反例注入须「注入→FAIL→还原（`cp`+md5）→回绿」。
8. 不得写入未经主会话转达的用户裁定；自定事项写「自决」。
9. 命令作用域 = workdir（仓库根），用相对路径。

## 待裁定（交主会话）

1. **`-bios` 路径口径**：`spec/Machine-v5 §6` 说 Tiny 的 legacy `-bios` 与 `bootrom-image` 装同一固定固件；但 `tests/inst` Tiny 子集 44/44 中 43 例是 `expected_fault`，依赖「hmon 向量不可达 ⇒ 机器 fault 退出码」，而当前最小 hmon 对非 `CFXTRAP` 故障 park（故障分派属未开工的 `m12-chipyard-019`）。若把 `-bios` 立即收紧为固定固件，44/44 会全部超时。
   - 方案 A（本任务自决、已实现）：契约路径 = `bootrom-image`（严格 64 KiB、应用 SRAM-only、固定入口、真执行 power/hmon）；`-bios` 的 64 KiB 文件按同一固定固件走契约路径，≤4096 B 保留为 pre-contract 的 raw trampoline 窗口（trampoline 显式把 hmon 向量指到不可达地址，保持机器 fault 退出码）。
   - 方案 B：等 `m12-chipyard-019` 的故障分派 hmon 落地后收紧 `-bios`，并同步改 44 例 oracle（不再依赖向量不可达）。
   - 建议：A 随本任务合入，B 另立任务。若要求 `-bios` 立即严格，需同时改 44 例 harness/oracle，属验收标准变更。

## 完成区

**测试结果**：一键证据脚本：常规 **33/33 PASS**、`--inject` **46/46 PASS**（注入 rc10 掩码/switch_run_mode 可写 ⇒ 契约 app 分别退出 0x13/0x14；`cp`+md5 还原 ⇒ 回绿）；回归 `check-inst` Vast **980/985** + Tiny **44/44**、`check-inst-smoke`、`check-arch-smoke`（10/10 + 25 服务）、`check-arch`（13 探针全绿）、L2 `check-modules` 全 PASS、L3 `test-m6` PASS（lit full + lli 差分 + Embench 38/38）。
**修改文件**：`components/qemu/patches/` 4 份（`hw/dadao/dadao-machine.c`、`target/dadao/{cpu.c,cpu.h,helper.c}`）+ `components/qemu/changelog.md`；`Makefile`；测试侧 `tools/testcases/lib/{gen_trampoline.py,trampoline.bin}`、`tools/testcases/unit/run_elf_e2e.py`、`tools/testcases/picolibc_tests.py`、`tools/testcases/arch/min_rom_probe_integ046t.py`、`tools/testcases/tset/embench/run_embench_e2e.py`、`tests/shared/linker/{dadao-tiny-app.lds(新),picolibc-tiny.ld}`、`tests/unit/llvm/e2e/lit/{lit.cfg.py,9 个 ELF .test}`。
**验收结果**：BootROM 65536 B、md5 `777b6bc9ba66c19783fb7f0a487249fd` == chipyard 签入 hex；hmon 段 56 B、md5 `9db9d9cc373debacf5389ac16ef91dc6`；表 `DBOT/1/1/boot_magic=0x30001`、表项 `type=1 flags=0x3 offset=0x2000 size=56`；真执行链 `power 0xffffffff0000 → trap 0xffffffff0134(7f0f0001) → hmon 0x0fff00000000(7e0c0001 escape) → 0xffffffff0138 → app 0xffffff010100`；`rc10` 写入 `…0002` 读回 `…0000`、`switch_run_mode` 写 0 读回 3、hmon SRAM 逐字节 == 镜像段；反例（BootROM PT_LOAD/hmon PT_LOAD/e_entry≠固定入口/镜像 65535 B/无固件）均 rc=1 且具名。
**新发现/坑**：① 固定固件的最小 hmon 对非 `CFXTRAP` 故障 park，原有 Tiny `expected_fault` 用例的机器 fault 退出码依赖「向量不可达」；legacy trampoline 需显式写不可达向量（见待裁定）。② lld 的 `MEMORY` 区域会把未显式给地址的输出段钉在 region origin，`. =` 对首段无效 ⇒ 固定入口段必须显式写地址。③ 新契约下所有 Tiny ELF 应用（lit/test-elf/picolibc/embench）都必须改用 SRAM 应用链接脚本 + `bootrom-image`。④ 旧 `tests/arch/hmon/tiny_hmon.S` 仍按旧「宿主直装 BootROM/hmon」构造，未在 QEMU 门控内，需 gem5 任务同步。
**遗留问题**：① `m12-chipyard-019`（故障分派 hmon）未开工 ⇒ `-bios` 严格化与 44 例 oracle 迁移待其落地（方案 B）；② `m13-gem5-005` 需按本任务结论对齐（同一镜像/同一 app ELF/同一 rc10 与 switch_run_mode 口径）；③ L1 `make check` 的红项均为外部（gem5/chipyard 并发脏树、他任务的 `.work` 引用/运行期日志名/陈旧临时目录），qemu 补丁树断言 0 问题、`check-source-state` qemu clean+base+1。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行审查）

审查范围：4 份 QEMU 补丁全 diff、测试侧链接/驱动改动、证据脚本；对照 `spec/Machine-v5` 0.4.4-rc §2/§6/§6.1/§6.2、`spec/DADAO-13` §1、`Machine-v5 §7.1`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 固定固件最小 hmon 对非 `CFXTRAP` 故障 park，`tests/inst` 43 个 `expected_fault` 用例依赖「向量不可达 ⇒ 机器 fault」 | ✅已修（兼容路径） | legacy trampoline 先写不可达 hmon 向量；契约路径走 `bootrom-image`；差异写入「待裁定」 | `check-inst` Tiny 44/44、`check-inst-smoke` PASS |
| F2 `-bios` 严格 64 KiB 与旧 harness 的短 trampoline 冲突；截断的 65535 B 固件也可能被当 trampoline | ✅已修（口径分离 + 尺寸护栏） | `bootrom-image` 严格 64 KiB；`-bios` 只接受 64 KiB 固件或 ≤4096 B legacy trampoline，中间尺寸具名报错；ELF 应用要求 `bootrom-image` | 反例 65535 B（`bootrom-image`/`-bios`）rc=1 具名；44/44 |
| F3 lld 的 `MEMORY` 区域使 `. =` 对首输出段无效，应用入口被钉到 region origin | ✅已修 | `dadao-tiny-app.lds` 在 `.text.start` 上显式写 `0xffffff010100` | `llvm-readelf` e_entry = 0xffffff010100；e2e 5/5、lit 163/163 |
| F4 新契约下令 `tests/inst` 之外的 Tiny ELF 测试（lit/test-elf/picolibc/embench）仍走旧「ELF-only + crt-in-ROM」 | ✅已修 | 应用 lds + `bootrom-image`，`Makefile` 补 `build-bootrom` 前置 | `check-lit` 163/163、`test-elf` 5/5、picolibc 18 pass/0 fail、L2 PASS |
| F5 `cg3 rc10` 初值改为内部 SRAM 起始后，Vast 探针 `integ046t` 仍断言 smon VEC ≠ smon entry | ✅已修 | 探针期望改为 `smon VEC == smon entry`（新 spec 口径） | `check-arch` 13 探针全绿 |
| F6 `rc10` 掩低 2 位分支先于泛型写分支，是否误伤其它 rc10 使用者 | ❌不修（正确） | 按 `DADAO-13 §1` 对 cg0-3 rc10 统一掩码；读回为落盘值 | 契约 app rc10 校验通过；`check-arch`/`check-inst` 零回归 |
| F7 Tiny `switch_run_mode` 写入忽略分支仅按 profile 开关，是否误伤 Vast | ❌不修（正确） | 仅 Tiny `switch_run_mode_write_ignored=true`；Vast 保持原语义 | 契约 app 写 0 读回 3；Vast 980/985 不变 |

判决：可修 finding 已全部修复并复验；F1/F2 为需用户裁定的口径差异，已写入「待裁定」并给出临时处置。状态置 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-11，以下命令均由 reviewer 亲跑）

**重跑记录（命令 → 真实退出码 + 关键输出）**

1. 一键证据脚本 → `rc=0`、`== RESULT: PASS=33 FAIL=0 ==`；5 条反例均 `rc expected=1 actual=1` 且具名（`targets the BootROM` / `targets the hmon SRAM` / `is not the fixed application entry` / `expected exactly 65536 bytes` / `requires the fixed BootROM firmware`）。
2. 同脚本 `--inject` → `rc=0`、`== RESULT: PASS=46 FAIL=0 ==`（rc10 掩码注入 ⇒ `19`=0x13；switch_run_mode 注入 ⇒ `20`=0x14；表 `boot_magic` 注入 ⇒ `124`；三处 `cp`+md5 还原 `da957b85…`/`9cb0bac2…`/`777b6bc9…` 相等）。
3. **reviewer 独立注入**（去掉 BootROM 拒绝：QEMU 源码 md5 `897b2c6f…` → `052fe413…`）→ 同脚本 `rc=1`、`== RESULT: PASS=32 FAIL=1 ==`、`FAIL bad-bootrom-ptload phrase='targets the BootROM' not found`；`cp`+md5 还原（`897b2c6f…` 相等、源码树 `git status` 干净）→ 复跑 `rc=0`、`PASS=33 FAIL=0`，安装根二进制重建且该具名串回位。**重试记录**：第 1 次注入被共享 gate lock（他任务跑 L2）挡住、`build-qemu` 等锁超时 ⇒ 环境性重试 1 次后成功，未以重试掩盖根因。
4. `make check-inst` → `rc=0`：Vast `985 total, 980 passed, 0 failed, 5 deferred, skipped_profile=44`；Tiny `44 total, 44 passed`（与 m13-qemu-001/m12-testcases-001 基线逐字一致）。
5. `make check-modules`(L2) → `rc=0`：inst-smoke、arch-smoke `10/10 + 25 服务`、lit `Passed: 163 (100.00%)`、test-codegen、test-elf `5/5`、picolibc `total=20 pass=18 fail=0 blocked=0`、ir-lli、tset×3、generator-sync 全 PASS。
6. `make check-arch` → `rc=0`（13 探针全 PASS，含改过 oracle 的 `integ046t`）。
7. 镜像独立核算（reviewer 按 `§6.1/§6.2` 自行解码 chipyard hex 补丁，未复用 engineer 脚本）→ `777b6bc9ba66c19783fb7f0a487249fd` == `bootrom_tiny.bin`；hmon 段 `9db9d9cc…`、56 B。
8. `-bios` 补测 → 64 KiB 固件 + ELF 应用 `rc=0`（`END-OF-MESSAGE`）；65535 B + ELF `rc=1` 具名；65535 B + raw `rc=1` 中间尺寸护栏具名。

**契约逐条核验**：布局 8K/8K/40K 全零/8K 表、`DBOT v1 count1 boot_magic=0x30001`、表项 `type1 flags0x3 off0x2000 size56` ✓；宿主只装 SRAM（BootROM/hmon `PT_LOAD`、`e_entry≠0xffff_ff01_0100`、镜像≠64 KiB、缺固件 ⇒ 显式失败）✓；真执行闭环（reviewer 日志）`0xffffffff0000 → 0xffffffff0134(7f0f0001, imm=0x30001) → 0xfff00000000 → 0xffffffff0138 → 0xffffff010100`、`CFX03 CID:1 CIP:…0134 CINFO:7f0f0001`、`SWMODE:3 VEC:0x0fff00000000` ✓；rc10 初值 = 内部 SRAM 起始、写 `…0002` 读回 `…0000`（对齐 `DADAO-13 §1`）、`switch_run_mode` 写 0 读回 3 ✓；hmon SRAM 7×8 B 与镜像段逐字节一致（契约 app 分码 0x11–0x15）✓。

**约束核验**：独立 worktree 作业 ✓；reviewer 未提交任何 commit ✓；完成区 9 行（≤30）、无运行期路径 ✓；改动集 23 个文件与完成区逐条对账（lit 实为 **8 个 `.test`** + `lit.cfg.py`，完成区写「9 个」⇒ 记数笔误）✓；脚本每条断言有可达 FAIL、无 `tee` 吞码、还原 `cp`+md5 ✓；「待裁定」已落盘且标「自决」、无擅写用户裁定 ✓；快照对账：审前 6 个未提交文件已由 architect `b76850bd` 补提交，审后 HEAD `b76850bd`、`git status` 仅剩本审阅记录一处、共享 QEMU 源树 clean + md5 复原 ✓（L1 两处红项 `check-knowledge-refs`/`check-run-artifacts` 均命中他任务文件，本任务 0 命中）。

**finding（不阻断，交 architect 终审）**：① F1 `-bios` 是**真 spec 层差异**（`§6` 字面要求 `-bios` 装同一固定固件、不再带 trampoline；实现保留 ≤4096 B legacy 窗口）——临时处置可接受（契约路径严格、暴露面限于 raw+legacy、44/44 依赖它），但**须用户裁定**（方案 B 绑 `m12-chipyard-019`，或修订 spec 措辞），不得视作已解决。② F2 非独立口径（护栏机制），两条报错路径已实测具名。③ 「共用同一镜像」目前仅对 **chipyard** 成立，仓库内尚无 gem5 侧镜像（`m13-gem5-005` 并行）。④ 完成区记数笔误：lit「9 个」实为 8、文件「24」实为 23（文档级，随收尾改）。⑤ L1 `check-run-artifacts` 红项 3 条均属他任务产物（night 报告、gem5-004 reviewer 文件），非本任务。

**判决：Accepted** —— 7 项验收标准在 reviewer 亲跑下全部达标、无约束违反；F1 口径差异留待用户裁定，最终接受权在 architect。

#### 收尾（architect，2026-11-11 00:33）

- reviewer **Accepted**：装载契约逐条对齐（5 条反例各具名 rc=1）、power **真执行固件**（trace 完整）、`rc10` 掩低 2 位、`switch_run_mode` 读回 3、hmon SRAM 与镜像段逐字节一致。
- **共用同一镜像**：独立解码 chipyard `bootrom.tiny.hex.patch` ⇒ md5 `777b6bc9…` == QEMU 产物；hmon 段 `9db9d9cc…`(56 B) 一致。
- reviewer 独立注入（去掉 BootROM 拒绝）⇒ `FAIL bad-bootrom-ptload` ⇒ 还原回绿；首注入因**共享 gate lock 被他任务 L2 占用**超时，属环境性重试 1 次（记录在案）。
- **L2 `check-modules` rc=0** ⇒ E2E 8 例已随本任务修复，`m12-testcases-002` 取消正确。
- 文档级更正：lit 用例 **8 个**（非 9）、文件总数 **23**（非 24）。
- **F1 待用户裁定**：`§6` 字面要求 `-bios` 装同一固定固件、不再带 trampoline；实现保留 **≤4096 B legacy 窗口**（44 例中 43 例 `expected_fault` 依赖它）。临时处置可接受（契约路径严格），但需用户选择：① 绑 `m12-chipyard-019` 迁移 44 例 oracle 后删 legacy；② 修 `Machine-v5 §6` 措辞承认该窗口。
