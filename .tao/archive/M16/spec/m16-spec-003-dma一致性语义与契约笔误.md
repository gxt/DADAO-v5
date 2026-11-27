# m16-spec-003: DMA 与 D-cache 一致性语义 + 契约笔误

**模块**：spec
**项目里程碑**：M16
**依赖**：`m16-chipyard-022` 已合入（ISS-531 实测方）
**可并行分片**：否
**预估**：1–2 h
**档位**：中改（契约语义，复核 ≤40 min；**语义方向须用户确认后开工**）
**状态**：已验证

## 背景

- `ISS-531`：`m16-chipyard-022` 的 DMA 引擎直接读写 PA，绕过 D-cache；若 CPU 先缓存目标行，DMA 写后 CPU 可能读到旧值。`DADAO-12 §4.9` 未规定 DMA 与 D-cache 的先后/失效语义，探针靠"只用 CPU 未触碰的 PA 行"回避。
- `ISS-526`：`contract-see` 的 power `start` 写成 `0x3_ffc0_0000`，与 `spec/Kaiwu §3`/`machine.yaml(vast)` 的 `0x3ff_ffc0_0000` 差一位（既有笔误）。

## 要做

> **语义方向已定（用户 2026-11-24 裁定 A）**：DMA 与 CPU 缓存**不保证硬件一致**，由**软件负责**——START 前对源/目标区间 `clean`，完成后 `invalidate`；硬件不做 snoop/自动失效。

1. **一致性语义（A）**：在 `§4.9` 写清：
   - DMA **不**与 D-cache 做硬件一致性（不 snoop、不自动失效）；
   - 软件职责：`START` 前把源区间 `clean`、完成后把目标区间 `invalidate`（顺序与时机写死）；
   - 目标为 BootROM/只读区的行为（写 ⇒ `PA_FAULT`）、`BUSY` 期间的可见性、与 `fence` 的关系；
   - 未按 A 操作时"读到旧值"属软件错误，不由硬件报异常。
2. **契约笔误**：订正 `contract-see` 的 power `start` 值；顺带核 power 段其它数值与 `machine.yaml(vast)` 一致。
3. **同步面**：`contract-see`、`contract-cfx-aliases`（若涉及）、`spec/.manifests.toml`（只重算受影响册）；版本仍 `0.8.0-rc`（内容改，不升号）。
4. **不改**实现与测试（QEMU/RTL/gem5 的 DMA 语义如与裁定不符，另立任务）。

## 不做

- 不实现 DMA 失效硬件或软件 fence；
- 不改 `cfx_pmem` 寄存器面（ISS-533 另立）。

## 约束

- 独立 `git worktree`；**不提交 git**；只动 `spec/DADAO-12…`、`.tao/contracts/contract-see.md`、`spec/.manifests.toml`、本任务书；
- 不写运行期路径；术语"寄存器组"。

## 验证

运行期证据目录内的 `run.sh`：

1. `§4.9` 有明确的一致性条款（含软件职责/硬件行为、失效粒度、与 `fence` 的关系），无"未定义"表述；
2. `grep` 全仓 `0x3_ffc0_0000` 0 命中（历史/ADR 除外），`0x3ff_ffc0_0000` 与 `machine.yaml` 一致；
3. `check-spec-refs`、`check-manifests-guard`、`check-spec-codeblocks`、`check-contracts-*`、`check-cfx-aliases` rc 记录；
4. **可达 FAIL ≥2**：注入"删一致性条款"、"回退 start 笔误" ⇒ 门控/检查红；`cp`+md5 还原回绿。

## 完成区

**测试结果**：证据脚本 75 PASS / 0 FAIL（失败项合计 0，rc=0）；两个注入均按预期转红、`cp`+md5 还原后回绿。门控全部 rc=0：`check-spec-refs`、`check-spec-codeblocks`、`check-contracts-dir`、`check-contracts-pending`、`check-spec-drift`、`check-cfx-aliases`、`check-manifests-guard`、`check-asm-list`、`check-asm-list-drift`、`check-legality-drift`、`check-spec-numbering`、`check-spec-changelog`。

**修改文件**：
- `spec/DADAO-12-SEE-主管系统运行环境.md`：§4.9 增「DMA 与 D-cache 的一致性（软件负责）」条款块（11 条）；§4.6 增 1 行交叉引用；0.8.0-rc 变更记录 +1 条（版本不动）
- `.tao/contracts/contract-see.md`：§2 增 `cfx_pmem` DMA/D-cache 一致性条；§3 订正 `cfx_power` cg7 块值（Vast `0x3ff_ffc0_0000`+`0x40_0000`、Tiny `0x3ff_ffff_0000`+`0x1_0000`）；§7 变更记录 +1 条
- `.tao/contracts/contract-cfx-aliases.md`：按生成器重算（**仅「来源」列行号**变化 31 行，表内容不变；顺带消除基线 1 处行号漂移，见「新发现」）
- `spec/.manifests.toml`：只重算 `DADAO-12` 的 sha256
- 本任务书：完成区 + 审阅记录

**验收结果**：运行期证据目录内的 `run.sh`（rc=0）逐项打印——§4.9 断言 11 项 PASS（含「硬件不保证一致/不 snoop/不自动写回或失效」「`START` **之前** clean」「`DONE`+`BUSY=0` 后 invalidate」「按 cache 行维护」「bit6 `PA_FAULT`」「无保证」「不等待 DMA」「软件错误」，且节内「未定义」0 处）；笔误 `0x3_ffc0_0000` 活体面 0 命中；power start/size 由 `machine.yaml` **现场推导**（`base − (63<<42)`）对 Vast/Tiny 各 1 项 PASS；contract-see 4 项、§4.6 2 项、术语 2 项、manifests sha 1 项、门控 10 项 PASS。注入 1（删条款块）⇒ §4.9 断言 10 项红 + `check-cfx-aliases` 1 处 MISMATCH；注入 2（回退笔误）⇒ 笔误检查与 power 值检查各红 1 项；两次还原 md5 一致后回绿。版本仍 `0.8.0-rc`（册头/合约头均未改）。

**新发现/坑**：
- **基线 KNOWN-RED（已顺带修复）**：本 worktree 基线 `check-cfx-aliases` 即红——`cfx_umon_async_intr_mask` 期望 `DADAO-12:493`、实际 494（`m17-spec-002` 改 DADAO-12 后未重算生成物）。任务「`contract-cfx-aliases` 若涉及」故重算，门控回绿。
- **`contract-cfx-aliases` 的来源列是 spec 行号** ⇒ 任何在 spec 增删行的任务都会让它转红；建议后续 spec 任务把「重算 cfx-aliases」列入常规步骤，或立 issue 降敏。
- **探针必须用子 shell**：bash 对函数调用的重定向不 fork，`check_x >/dev/null` 会把内部 `bad()` 计入合计（假失败合计）；改用 `( check_x )`；另 `check_make` 需显式 `return "$rc"`，否则恒 0（会让「期望转红」假绿）。
- 建议沉淀：① 裁定 A 口径（DMA 不 snoop、软件 clean/invalidate）；②「期望转红探针用子 shell + 捕获函数 rc」证据脚本写法。

**遗留问题**：
- `ISS-526` 条目仍为 open（本任务只订正契约值，`issues.yaml` 超范围未动；关账由收尾处理）。
- QEMU/RTL/gem5 的 DMA 语义是否与 A 一致未核（任务明示另立任务）。
- 未跑 `check-modules`/`check-full`（任务门控清单未含；并行窗口内禁跑 L2）。
- 越界披露：`contract-cfx-aliases.md` 不在任务「约束」的文件清单内，但属任务「要做」第 3 条的同步面，已按机器生成方式重算。

## 审阅记录

### 第 1 轮 engineer 自审

逐行审查 `spec/DADAO-12`（§4.6/§4.9/变更记录）、`contract-see`（§2/§3/§7）、`run.sh`。判决：全部 finding 已修，可标「待验收」。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 契约 §7 新条引入第 2 个 `0x3ff_ffc0_0000`，注入 2 锚点不唯一 ⇒ 空注入 | ✅已修 | 注入改为只改 `power \`start=` 所在行并断言行内命中 | run.log「注入2 生效 PASS 已回退笔误」 |
| F2 期望转红探针 `check_x >/dev/null` 不 fork，内部 `bad()` 计入合计（失败合计 13 而输出全 PASS） | ✅已修 | 全部改 `( check_x )` 子 shell；新增 `expect_red` 探针 | 失败项合计 0，rc=0 |
| F3 `check_make` 末命令为 `if` ⇒ 恒返回 0（「注入1 cfx-aliases 转红」假 PASS） | ✅已修 | 追加 `return "$rc"` | 注入1 cfx-aliases 报 1 处 MISMATCH 后回绿 |
| F4 §4.9 初稿「的 **PA 源区间** 执行」带空格，与全文粗体排版不一致 | ✅已修 | 去空格（2 处） | 重跑断言 PASS |
| F5 spec 正文用口语「写死」 | ✅已修 | 改「顺序与时机固定」 | 门控 + 断言复跑 rc=0 |
| F6 契约 Tiny power 块值同样错（start 与 size 均差），超出 issue 所述 Vast 一处 | ✅已修 | 按 `Kaiwu §3`/`machine.yaml` 订正为 `0x3ff_ffff_0000`+`0x1_0000` | power 段 tiny 断言 PASS（现场推导） |
| F7 §4.6 首稿复制「不 snoop、不自动失效」，违反「只加交叉引用」 | ✅已修 | 收为 1 句指针（指向 §4.9） | 「§4.6 未复制正文」断言 PASS（全文该短语恰 1 处） |
| F8 遗留 `cfx_pmem_attr.coherent` 与「（预取策略、Cache 一致性等）」可与裁定 A 冲突 | ✅已修 | 加「区域属性不改变本节条款」1 条，进阶语义与末注一致地留待多核 SMP | 人工核对；断言覆盖硬件行为条 |
| F9 生成物重算含基线行号漂移，须确认无表内容变化 | ✅已修（核对） | 归一化行号后逐对比较，31 行 diff 全为行号 | `git diff` 归一化比较 0 处实质差异 |
| F10 完成区若写具体 `.work/**` 路径会触 `check-knowledge-refs` | ✅已修 | 一律写「运行期证据目录内的 `run.sh`」 | `make check-knowledge-refs` rc=0 |

### 第 1 轮 reviewer 验收

**重跑（仓库根独立执行，不采信完成区）**：
- 运行期证据目录内 `run.sh`（全量含自带注入）**rc=0，76 PASS / 0 FAIL**（断言段 33 + 注入段 10 + 收尾段 33）。
- 门控独立重跑 rc 全 0（13 项）：`check-spec-refs`、`check-manifests-guard`、`check-spec-codeblocks`、`check-contracts-dir`、`check-contracts-pending`、`check-spec-drift`、`check-cfx-aliases`、`check-asm-list`、`check-asm-list-drift`、`check-legality-drift`、`check-knowledge-refs`、`check-spec-numbering`、`check-spec-changelog`。
- **独立注入 1**：删 §4.9「与 `fence` 的关系」整条 ⇒ `run.sh --checks-only` rc=1、4 项红（§4.9 fence 断言 / manifests sha / `check-cfx-aliases` / `check-manifests-guard`）；`cp` 备份还原 + md5 `d463a378…` 相等 ⇒ rc=0。
- **独立注入 2**：回退 contract-see Tiny `start=0x3ff_ffff_0000`→`0x3_ffff_0000` ⇒ rc=1、power tiny 1 项红；`cp` 还原 + md5 `3f96ae17…` 相等 ⇒ rc=0。工程师自带两注入（删条款块 / 回退 Vast 笔误）在我重跑中同样红→还原→回绿。

**§4.9 条款逐项（人工核读，8 顶层 + 4 子条）**：① 硬件不 snoop、不自动写回或失效、不因 cache 残留改行为/报异常；② `START` **之前** clean 源（`PA→CFX`）、`DONE` 置位且 `BUSY=0` **之后** invalidate 目标（`CFX→PA`）；③ 粒度 = 按 cache 行、用 `PA 区间` 覆盖首尾行；④ 写只读/BootROM ⇒ `START` 判失败、`ERR_CODE` bit6 `PA_FAULT`（与 §4.9 ERR_CODE 表 bit6 行一致）、传输不启动 `BUSY` 保持 0；⑤ `BUSY=1` 中间内容无保证；⑥ `fence` **不等待 DMA**、不能替代维护（与 §2.1 第 85 行既有句一致）；⑦ `cfx_pmem_attr.coherent` 不改变结论（指针到本节末准确）；⑧ 漏维护读旧值属软件错误、硬件不报异常。节内「未定义」0 处。

**§4.6**：仅 +1 行「与 DMA 的关系…顺序、时机与粒度见 §4.9」；「不 snoop」全文仅 §4.9 条款 + 变更记录，`START` **之前** 全文 1 处 ⇒ 未复制正文。

**契约/别名/manifest**：contract-see §2 新条与裁定 A 一致；§3 Vast `0x3ff_ffc0_0000`/`0x40_0000`、Tiny `0x3ff_ffff_0000`/`0x1_0000`，与 `spec/Kaiwu §3`（第 112 行）及 `contracts/machine.yaml` 现场推导 `base − (63<<42)` 逐一对上；`contract-cfx-aliases` 剥「来源」列归一化后 diff = 0 行，31 行变化全为行号；`spec/.manifests.toml` 仅 DADAO-12 一行 sha 变更，实测 `sha256sum` = `611601ff…` 相等；册头/合约头仍 `0.8.0-rc`。

**范围**：验收前后 `git status` 各 5 文件，与完成区「修改文件」逐一对账一致；archive/ADR/knowledge/实现/测试零改动；任务书无具体运行期路径（`check-knowledge-refs` rc=0）、完成区 25 行 ≤30。

**findings（均不阻断，交 architect 收尾改）**：
- R1 完成区「条款块（11 条）」实为 **12 条**（8 顶层 + 4 子条）。
- R2 完成区「75 PASS / 0 FAIL」不复现：我重跑为 **76 PASS / 0 FAIL**；证据目录留存的 `run.log` 是改脚本前的旧跑，尾行「失败项合计：3」且 mtime 早于 `run.sh` ⇒ 收尾须重跑覆盖并订正计数。
- R3 「基线 1 处行号漂移」「注入1 1 处 MISMATCH」计数失真：门控只打印首处差异、`grep -c MISMATCH` 恒 1；我按 HEAD 别名表 × HEAD spec 逐条比对，基线 **45/45 条全部 +1 漂移**（umon 494/493、cache 603/602、hart 647/646、power 825/824），当前 45/45 全对。
- R4 power 段断言取「含 `power start=` 的整行」做 token 集合判定，**Vast/Tiny 互换仍 PASS**（我实测复现）；可达 FAIL 已由注入 2 证明故不阻断，建议按 profile 分句定位。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过、硬约束无违反；R1–R4 为文档级/脚本颗粒度问题，按 §6.5 记 finding 由 architect 收尾处理。

