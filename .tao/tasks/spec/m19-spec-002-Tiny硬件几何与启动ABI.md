# m19-spec-002: Tiny 硬件几何与启动 ABI（8K ROM / 8K hmon / 256K SRAM）

**模块**：spec
**项目里程碑**：M19
**依赖**：无
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待验收

## 背景

用户 2026-11-27 定稿 Tiny 的硬件几何与软件布局；本任务把地址、尺寸、启动 ABI 写入 spec/契约，作为 QEMU/gem5/chipyard/testcases 的共同真源。

```
BOOT_ROM_BASE  = 0xFFFF_FFFF_0000  SIZE = 0x2000（8 KiB）
  power      0x0000–0x07FF（≤2 KiB）
  hmon 源    0x0800–0x13FF（≤3 KiB）
  table      0x1F00–0x1F2F（48 B）

HMON_SRAM_BASE = 0x0FFF_0000_0000  SIZE = 0x2000（8 KiB）
  code       0x0000–0x0BFF（≤3 KiB）
  data       0x0C00–0x0CFF（256 B）
  stack      0x0D00–0x1FFF（SP = 0x2000）

MAIN_SRAM_BASE = 0xFFFF_FF00_0000  SIZE = 0x40000（256 KiB）
  0x0000  VERSION（=1，loader 写）
  0x0020  MAILBOX（8 B）
  0x0030  EXIT_BLOCK（16 B；code 在 +0x38）
  0x0800  DUMP_BASE，DUMP_SIZE = 0x800（pt_regs 顺序）
  0x1000  SIGNATURE，0x800
  0x2000  ENTRY / raw 镜像基址
  0x38000 guard_lo
  0x39000 STACK，24 KiB，SP = 0x3F000
  0x3F000 MemRAS，4 KiB，MRPTR = 0x40000
```

- `DUMP_BASE` 四段：`rd[64]`@+0x000（rd0=status）、`rb[64]`@+0x200（rb0=ip）、`ra[64]`@+0x400、`rf[64]`@+0x600，总计 0x800。
- `image_window = 0x2_0000`（128 KiB）；`kernel_base = MAIN_SRAM_BASE+0x2000`、`kernel_reserved = 0`。
- MemRAS 与 Stack 之间**不设 guard_hi**（用户 2026-11-27 接受 4 KiB MemRAS 预算）；guard_lo 只挡栈溢出。
- `VERSION=1` 由 loader 写；power 必须同时检查 VERSION 与 MAILBOX magic 才放核。

## 目标

1. `spec/Kaiwu §1.1/§6/§6.2` 写入上表与启动/装载 ABI；删除 64 KiB BootROM、8 MiB SRAM、64 KiB hmon 的旧口径。
2. `contracts/machine.yaml` 的 `tiny.bootrom.size=0x2000`、`tiny.ram.size=0x40000`。
3. 明确 hmon 4 KiB→8 KiB、Boot ROM 布局、DUMP/signature/EXIT/MAILBOX 的角色与大小。
4. 版本号升级（spec/contracts）**待用户确认**；未确认前只落内容、不升号。

## 验收（逐条贴真实 rc）

1. `check-spec-refs` / `check-spec-numbering` / `check-contract-*` 真实 rc=0（基线红给逐行对照）。
2. 新表中所有地址/大小可 grep；`DUMP_BASE+0x800`、`SIGNATURE+0x800`、`ENTRY=0x2000` 与 `pt_regs` 偏移一致。
3. **可达 FAIL ≥2 路**：① 把 `BOOT_ROM_SIZE` 写回 64 KiB ⇒ 契约/派生检查红；② 把 `ENTRY` 写成 `0x100` ⇒ 交叉核对红。
4. 不改 QEMU/gem5/chipyard/testcases 源码；不升版本号（除非用户当轮确认）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `spec/Kaiwu*`、`contracts/machine.yaml` 与必要索引；完成区不写具体 `.work/**` 路径。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| ① 正文旧口径（64 KiB ROM / 8 MiB SRAM / 64 KiB hmon / 0x10100 入口 / 旧 SP） | ✅已修 | §1.1/§2/§3 cg7/§6/§6.2 全量替换；附录 0.4.0/0.4.4 历史条目保留 | 证据脚本 `cross.entry.legacy...absent`/`cross.sp.legacy...absent` PASS；check-spec-* 全 0 |
| ② `cg7` 的「start+size=2^42」对 8 KiB ROM 不成立 | ✅已修 | §3 改为 Tiny `start=2^42−64 KiB`、`start+size=2^42−56 KiB`；Vast 仍等于 2^42 | 手工核算 + §1.1/§6.2 交叉 grep |
| ③ 主 SRAM 表算术（DUMP+0x800、SIGNATURE+0x800、SP、MRPTR、guard） | ✅已修并机器校验 | 表与 §6.2.1 同值 | 证据脚本 `arith.*` 共 10 项 PASS |
| ④ hmon 数据槽 `0xD8`–`0xF8` 落在新 code 区 | ⏸延后 | 属 `tests/ee-tiny` hmon 源与下游任务 | 已记「遗留问题」与完成区 |
| ⑤ `MAILBOX` magic / `VERSION` 宽度未定 | ⏸延后 | spec 标 `[OPEN]` + 8 B 推定 | 已记「待裁定 2/3」 |
| ⑥ 上游 `DADAO-12 §2.1` 的 ≥64 KiB / 末 64 KiB 复位点与 Tiny 8 KiB 冲突 | ⏸延后（显式披露） | §1.1 增偏离说明；不改上游册 | 已记「待裁定 4」 |
| ⑦ 版本号未升但有内容变更 | ✅符合要求 | 附录 0.4.7-rc 增一条，册头不动 | 证据脚本 `version.*` PASS；check-spec-changelog rc=0 |
| ⑧ `machine.yaml` 改动使旧 `runtime.yaml` 触发 ProfileError | ❌不修（越界） | 属 `m19-testcases-002` | check-interface/check-tests-index 红因已记录，并对照基线 |
| ⑨ 证据脚本可达 FAIL | ✅已验证 | 两路注入（ROM=64 KiB、ENTRY=0x100） | `--inject` rc=0：基线 PASS、两路 FAIL 后回绿 |
| ⑩ `check-manifests-guard` 红 | ❌不修（基线红） | master `e23518a0` 同样两行（m16 缺失） | 逐行相同 |

### 第 1 轮 reviewer 验收（2026-11-27）

**重跑（仓库根，reviewer 独立执行，不采信完成区）**：
- `check-spec-refs` / `check-spec-numbering` / `check-spec-changelog` / `check-spec-purity` / `check-spec-drift` / `check-contracts-dir` / `check-contracts-pending` / `check-contract-relocs` / `check-spec-codeblocks` / `check-spec-cite-targets` / `check-knowledge-refs` ⇒ **11 项全 rc=0**；另 `check-dirs` / `check-no-residue` / `check-scope` / `check-spec-archive` rc=0。
- 证据脚本（仓库根执行运行期证据目录内的 `run.sh`）rc=0、**63 项全 PASS**；`run.sh --inject` rc=0：基线 PASS、注入①（ROM=64 KiB）1 项 FAIL、注入②（ENTRY=0x100）3 项 FAIL。
- **reviewer 独立注入（`cp` 备份 + md5，改被测产物而非副本）**：① `contracts/machine.yaml` ROM→`0x1_0000` ⇒ 同一脚本 1 项 FAIL、rc=1；② `§1.1` ENTRY 行→`0x100` ⇒ 3 项 FAIL、rc=1；两次还原后 md5 与注入前逐一相等、回绿 rc=0、`git status --porcelain -uall` 空、无 `.preinject` 残留。
- `check-manifests-guard` rc=2、`check-interface` / `check-tests-index` / `check-temp-dirs` rc=2 —— reviewer 逐项复现，与完成区所述 rc 一致。

**基线对照（`e23518a0` detached 临时树）**：
- `check-manifests-guard` 基线亦 rc=2，ERROR 两行（`issues-m16.yaml` / `milestones-m16.md`）与本分支 **逐行相同** ✅（M16 归档删文件、清单仍登记，与本任务无关）。
- `check-tests-index` 基线 **rc=0** → 本任务 rc=2 ⇒ **本任务引入的红**（`runtime.yaml` 旧 `sp` 落在新 256 KiB RAM 外）。
- `check-interface` 基线 rc=2 但红因为 `[4.Opcodes] N(294) != independent count (309)`，本任务后替换为 `ProfileError` ⇒ **错误集不同，非逐行相同**。

**逐条几何核验（脚本 + reviewer 独立复算，两法一致）**：ROM 五区 `0x800+0xC00+0xB00+0x30+0xD0=0x2000`；hmon `0xC00+0x100+0x1300=0x2000`、`SP=0x2000`；`DUMP 0x800+0x800=0x1000=SIGNATURE`、`SIG+0x800=0x1800`、`EXIT 0x30`（code `+0x38`）、`MAILBOX 0x20`、`guard 0x38000+0x1000=STACK 0x39000`、`STACK+0x6000=0x3F000=SP=MemRAS`、`MemRAS+0x1000=0x40000=RAM.size`、`ENTRY 0x2000+0x20000=0x22000≤0x38000`；表 48 B = 表头 16 B + 表项 32 B（§6.1）成立。`pt_regs` 四组 `rd/rb/ra/rf` @ `0/0x200/0x400/0x600` 与独立源 linux uapi 探针断言（`status==0`、`ip==512`、`ra==1024`、`rf==1536`）**逐项一致** ✅。

**版本与口径**：册头仍 `0.4.7-rc` 未动、附录仅增一条并注明「版本仍 0.4.7-rc」；`contracts/machine.yaml` 无版本字段；`MAILBOX` magic **仍标 `[OPEN]`**（未写成已定）；`VERSION` 8 B 标「按 8 字节字推定…确认后冻结」；正文旧口径（`8 MiB` / `0xffff_ff01_0100` / `0xffff_ff7e_ff00`）残留 0，22 处 `64 KiB` 全为 Vast/上游/页对齐合法上下文；变更集 = 4 文件（无 QEMU/gem5/chipyard/testcases）✅。

**finding ①（阻断·断言）**：证据脚本 `spec.bootrom.budget.sum` 为**恒真断言** —— `total = 0x800+0xC00+0xB00+0x30+0xD0` 硬编码自比 `0x2000`，**不读被测产物、无可达 FAIL 路径**，并虚增 63 项计数（其余 62 项均从产物解析，两路注入已证可达 FAIL）。违反 `AGENTS §4`「每条断言有可达 FAIL、禁恒真、禁两支同源」。

**finding ②（路线层，交 architect 定夺）**：本任务使 `check-tests-index` 绿→红、`check-interface` 红因被替换；受「不改 testcases」约束 engineer 无法消除，完成区已给根因与依赖任务，但**未写明基线 `tests-index` rc=0、基线 `interface` 红因** ⇒ 合入顺序须由 architect 保证 `m19-testcases-002` 紧跟，否则合入后 L1/L2 必红。

**判决：Needs Revision**（仅因 finding ①；验收 1–4 与约束其余**全部满足**）。最小返工点：① 改 `spec.bootrom.budget.sum` 为从 `§6.2` 表行解析五区 size **现场求和**（或删该条并说明覆盖由 row/limit 承担），重跑 `run.sh` 与 `run.sh --inject` 保持全绿 + 两路 FAIL；② 完成区补两行基线事实（`tests-index` 基线 rc=0、`interface` 基线红因 `Opcodes 294≠309`）。

**返工处置（engineer，针对上轮 Needs Revision；未改动上方 reviewer 内容）**：
- finding ① ✅已修：`spec.bootrom.budget.sum` 改为从 `§6.2` 表行解析五区（`start`/`end`）**现场求和**并比 `contracts/machine.yaml` 的 ROM size；新增 `rows.count`/`rows.contiguous`/`rows.cover.rom`，证据项 62→65。可达 FAIL 已证：注入③（`§6.2` hmon 源段 `0x13FF`→`0x12FF`）⇒ `budget.sum expected=0x2000 actual=0x1f00`；ROM=64 KiB ⇒ `budget.sum expected=0x10000 actual=0x2000`。
- finding ② ✅已处置：完成区补「基线事实」两行（`tests-index` 基线 rc=0；`interface` 基线红因 `[4.Opcodes] 294 != 309`，本任务后变为 `ProfileError`）。
- 实产物 `cp`+md5 注入/还原：`machine.yaml` md5 `50c7eb77bbf992d4628a8cd6ecb905bf`、`Kaiwu` md5 `ac0eafb385caa596b64ed72d19947ffe`；两路注入均 rc=1，`cp` 还原后 `md5sum -c` OK、`run.sh` rc=0。

### 第 2 轮 reviewer 验收（2026-11-27，返工 `3ceeb4f8`）

**范围核验**：返工 commit 仅改任务书 1 文件（+31/−1）；`spec/Kaiwu` md5 `ac0eafb3…`、`machine.yaml` md5 `50c7eb77…`、`.manifests.toml` md5 `19b8ecd9…` 与第 1 轮逐一相同 ⇒ **spec 语义未动**，与「返工只改任务书/证据脚本」声明一致；`git status --porcelain -uall` 空。

**finding ① 复验（脚本审读 + 重跑 + 独立注入）**：
- `spec.bootrom.budget.sum` 现为 `sec = body.split("### 6.2 ")[1].split("#### 6.2.1")[0]` 解析五区 `start`/`end` 后 `sum(b-a+1)`，期望侧取 `vals["bootrom_size"]`（`machine.yaml`）⇒ **跨文件交叉、两侧不同源，恒真已消除**；另新增 `rows.count`（现场 `len(ranges)==5`）、`rows.contiguous`（首区=0 且逐区首尾相接）、`rows.cover.rom`（末区尾+1 == ROM size）。
- 重跑 `run.sh` rc=0、**65 项全 PASS**（62→65）；`run.sh --inject` rc=0：基线 PASS + 三路 FAIL（① ROM=64 KiB 3 项、② ENTRY=0x100 3 项、③ §6.2 hmon 源段 −256 B 2 项）。
- **reviewer 独立注入被测产物**（`cp`+md5，非副本）：③ `0x13FF`→`0x12FF` ⇒ `budget.sum expected=0x2000 actual=0x1f00` + `rows.contiguous` FAIL、rc=1；① ROM→`0x1_0000` ⇒ `budget.sum expected=0x10000 actual=0x2000` + `rows.cover.rom` FAIL、rc=1；另删 §6.2 末区行 ⇒ `rows.count expected=5 actual=4` + 2 项 FAIL、rc=1。三次还原 `md5sum -c` OK、回绿 rc=0、无 `.preinject` 残留、`git status` 空。
- **三条新断言均证可达 FAIL**；`budget.sum` 两向（改 spec 表 / 改 yaml）都能红。

**finding ② 复验**：完成区已增「基线事实①」`check-tests-index` 基线 `e23518a0` rc=0 → 本任务 rc=2、「基线事实②」`check-interface` 基线红因 `[4.Opcodes] N(294) != independent count (309)`、本任务后变 `ProfileError`、错误集不同非逐行相同 —— 与 reviewer 第 1 轮实测**逐条一致** ✅。

**记录与状态**：状态仍 `**待验收**`；第 1 轮 reviewer 审阅记录 4 处关键句逐字保留、未被改写（engineer 另起「返工处置」段追加）✅；完成区/记录无具体 `.work/**` 路径，`check-knowledge-refs` 写入后 rc=0 ✅。11 项 spec/契约门控重跑全 rc=0。

**判决：Accepted** —— 第 1 轮 finding ①② 均已闭环、三路注入与 reviewer 三次独立注入全红、还原回绿无残留、验收 1–4 与全部约束满足。finding ② 的**路线层风险仍在**（`check-tests-index`/`check-interface` 在 `m19-testcases-002` 落地前必红），交 architect 定合入顺序。

## 待裁定

1. **版本号**：`spec/Kaiwu` 仍为 `0.4.7-rc`、`contracts/machine.yaml` 无版本号；本次只落内容、未升号。是否升 `Kaiwu`（`0.4.7-rc`→下一版）请用户确认（属 AGENTS §1 的停止点）。
2. **MAILBOX 协议**：`MAILBOX`（`+0x0020`，8 B）的 magic 取值与写入顺序未定（对应 M19 未决项 N44）；spec 已写「power 必须同时检查 `VERSION==1` 与 `MAILBOX==magic`」但 magic 值标 `[OPEN]`，实现无法冻结。
3. **字段宽度**：`VERSION`/`MAILBOX` 宽度按 8 字节字推定（与 `EXIT_BLOCK` 的 8 字节对齐一致），请确认。
4. **上游冲突**：`DADAO-12 §2.1` 规定 `cfx_power` BootROM **≥64 KiB**、复位向量在**末 64 KiB 起点**；Tiny 取 8 KiB、复位点=ROM 起始，属 profile 级偏离。是放宽上游册还是维持 Tiny 偏离，请裁定（本任务不改 `spec/DADAO-12`）。
5. **口径措辞**：目标 3 的「hmon 4 KiB→8 KiB」与 2026-11-27 布局（hmon SRAM 8 KiB、源段 ≤3 KiB）不一致；已按布局落 spec，请确认以布局为准。

## 完成区

**测试结果**：spec/契约门控全绿：`check-spec-refs` rc=0、`check-spec-numbering` rc=0、`check-spec-changelog` rc=0、`check-spec-purity` rc=0、`check-spec-drift` rc=0、`check-contracts-dir` rc=0、`check-contracts-pending` rc=0、`check-contract-relocs` rc=0、`check-spec-codeblocks` rc=0、`check-spec-cite-targets` rc=0、`check-knowledge-refs` rc=0。证据脚本（运行期证据目录 `run.sh`）rc=0（65 项，`budget.sum` 已改为现场解析 §6.2 表行求和）；`--inject` rc=0：基线 PASS、注入①ROM=64 KiB FAIL、注入②ENTRY=0x100 FAIL、注入③§6.2 hmon 源段 -256 B FAIL；实产物 `cp`+md5 注入/还原复验：两路注入 rc=1、还原 `md5sum -c` OK、`run.sh` 回绿 rc=0。
**修改文件**：`spec/Kaiwu-测试机运行环境.md`（§1.1/§2/§3 cg7/§6/§6.2 新增 §6.2.1/附录）；`contracts/machine.yaml`（tiny bootrom 0x2000、ram 0x40000）；`spec/.manifests.toml`（Kaiwu sha256 索引）。
**验收结果**：`check-manifests-guard` rc=2 —— 基线红且逐行相同（master `e23518a0` 同样报 `.tao/knowledge` 缺 `issues-m16.yaml`、`milestones-m16.md` 两行，与本改动无关）；`check-interface`/`check-tests-index` rc=2 —— 根因是 `tests/ee-tiny/runtime.yaml` 仍为旧布局（`sp` 落在新 256 KiB RAM 外），属 `m19-testcases-002` 依赖，本任务按约束不改 testcases；`check-dirs`/`check-no-residue` rc=0，`check-temp-dirs` rc=2 只报 `/tmp/opencode` 下 5 个**其它任务**的陈旧目录（非本任务）。版本号未升（`0.4.7-rc`，见待裁定 1）。
**基线事实①（tests-index）**：`check-tests-index` 基线（`e23518a0`）**rc=0**；本任务后 rc=2（`ProfileError`，旧 `runtime.yaml`）——即本任务引入的红，须 `m19-testcases-002` 紧跟合入消除。
**基线事实②（interface 错误集）**：`check-interface` 基线 rc=2 的红因是 `[4.Opcodes] N(294) != independent count (309)`；本任务后变为 `ProfileError`（`sp` 越界），**错误集不同、非逐行相同**。
**新发现/坑**：① `machine.yaml` 一改，`tools/testcases/lib/machine_profile.py` 会对旧 `runtime.yaml` 抛 `ProfileError`，`check-interface`/`check-tests-index` 不是干净 FAIL 而是 traceback ⇒ 本任务合入后到 `m19-testcases-002` 落地前，L1 里这两项必红，主会话需保证依赖任务紧跟合入。② `spec/.manifests.toml` 对每册有 sha256，改 spec 正文必须同步该索引，否则 `check-manifests-guard` 新增红项。③ 现行 tiny hmon handler 的数据槽 `0xD8`–`0xF8` 落在新 code 区（0x0000–0x0BFF）内，须迁到 data 区 `0x0C00`–`0x0CFF`（下游 testcases/integ）。
**遗留问题**：① 下游四平台任务（qemu/gem5/chipyard/testcases/integ）按本节实现；`runtime.yaml`、`machine-tiny.inc`、`hmon` 数据槽迁移不在本任务。② 待裁定 5 项见上。
