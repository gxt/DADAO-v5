# m13-spec-009: semihosting 服务号通道定死为 `rd16`（修 contract §1 / Machine-v5 / DDLN 的「immu18 低 8 位」旧句）

**模块**：spec
**项目里程碑**：M13
**依赖**：无（`m12-chipyard-016` 已按 rd16 实现并实测通过）
**可并行分片**：否（契约 + spec + 讲义 + 只读锁同笔）
**预估**：1–2 h
**状态**：已验证

## 用户裁定（2026-11-14，原话）

> 「确认 rd16，修 §1 措辞（推荐）」

- 依据（用户同日追问后确认的惯例）：**ARM** 用 `SVC #0x123456` / `HLT #0xF000`（立即数只是**固定标记**），服务号在 `R0`/`X0`、参数块在 `R1`/`X1`；**RISC-V** 用 `ebreak` + magic 序列（`0x01f01013/0x00100073/0x40705013`），服务号在 `a0`、参数块在 `a1`。⇒「标记在指令、服务号在寄存器」是两家共同惯例，DADAO 的 `rd16`/`rb16`/`rd8` 正与之对应；`immu18` 低 8 位携带 `op` 无同类先例。

## 现状（现场实测，三处实现一致、三处文档不一致）

- **实现都取 `rd16`**：QEMU `target/dadao/common-semi-target.c`（`common_semi_arg(0) = env->rd[16]`、`arg(1) = rb[16]`）；guest（`tests/shared/crt0/minimal_crt0.s` L50-51、picolibc `semihost-dadao.S`、embench `boardsupport.c`）都是 `trap cfx, 0x3FF00` + op 在 `rd16`；chipyard RTL（`m12-chipyard-016` 分支）`semiOp := rf.io.r0Data(7,0)`（A/B 实测：旧 `inst(7,0)` ⇒ `semihosting op 0x00 not implemented` rc=1；新 rd16 ⇒ rc=7）。
- **文档有三处旧句**（均含「服务号仍占 `immu18` 低 8 位（`0x3FF00 + op`）」）：
  1. `.tao/contracts/contract-semihosting.md` **L18**（§1）；
  2. `spec/Machine-v5-测试机运行环境.md` **L175**（§5.2 附近）；
  3. `docs/DDLN/D-运行平台/DD-D002-运行平台--测试机运行环境.md` **L67**（讲义，且同句已写「服务号在 `rd16`」⇒ 自相矛盾）。

## 目标（只改措辞，不改语义实现）

1. 三处统一为：**`immu18[17:8] == 0x3FF` 是 semihosting 的固定标记（`trap <any cfxha>, 0x3FF00`）；服务号由 `rd16` 给出，参数块指针 `rb16`，返回 `rd8`；`immu18` 低 8 位不携带服务号**。
2. 顺带核 `SimRISC-11`（陷入指令）与 `DADAO-22 §1` 是否有同类旧句；有则一并按上述口径改（同笔，不改其它语义）。
3. `manifests/spec-readonly.lock.toml`：重算 `Machine-v5`（以及若改了别的册）的 sha256 + 注记（授权依据 = 本次用户裁定原话）；**只重算本次实际改动的册**，其余保持原值。
4. 讲义（DD-D002）与契约同步，避免"讲义与 spec 打架"。

## 验收（逐条贴真实 rc / 命中数）

1. **旧句归零**：`grep -rn "0x3FF00 + op"`、`grep -rn "服务号.*低 8 位"`、`grep -rn "immu18.*低 8 位"` 在 `spec/`、`.tao/contracts/`、`docs/DDLN/`、`contracts/` 内**命中 0**（排除 `.tao/adr/` 与 `.tao/archive/` 的历史记录）。
2. **新口径在位**：`grep -rn "服务号.*rd16"` 在三处（contract §1/§2、Machine-v5、DD-D002）各 ≥1；`grep -n "0x3FF"` 仍保留（标记语义不变）。
3. 门控 rc=0：`check-spec-readonly`（21 册 OK）、`check-spec-changelog`、`check-spec-purity`、`check-spec-refs`、`check-spec-cite-targets`、`check-spec-numbering`、`check-asm-list`、`check-asm-prose`、`check-rule-refs`、`check-knowledge-refs`、`check-legality-drift`、`check-legality-invariants`。
4. **可达 FAIL 注入 ≥2 路**（`cp`+md5 还原）：① 把某处改回「低 8 位」⇒ 旧句归零断言红；② 只改锁里 `Machine-v5` 的 sha256 ⇒ `check-spec-readonly` MISMATCH。
5. 一键证据脚本 rc=0；完成区 ≤30 行、无运行期路径；「修改文件」与 `git status -uall` 对账；`**状态**` → `待验收`；不改台账/`discussing.md`。

## 硬约束（子代理必读）

1. 独立 `git worktree`（分支 = 任务号）；动手前自证 toplevel；禁改主工作树。
2. 不提交 git；**禁跑 `install-host`/`check-modules`/`build-*`**（本任务只改文档与锁）。
3. 禁 `git checkout/restore/stash`；注入还原用 `cp`+md5。
4. 只改：`.tao/contracts/contract-semihosting.md`、`spec/Machine-v5-*`、`docs/DDLN/D-运行平台/DD-D002-*`、必要时 `spec/SimRISC-11-*`/`spec/SimRISC-00-*` 的变更记录、`manifests/spec-readonly.lock.toml`、任务书；**不改**实现（`components/**`）、`tests/**`。
5. `spec/` 正文禁止出现任务号/ADR/ISS 号（`check-spec-purity`）；变更记录只写「服务号由 `rd16` 给出，`immu18[17:8]==0x3FF` 为标记」这类判据句。
6. 大文件落 `/tmp/opencode/m13-spec-009/` 并测完即删。

## 待裁定

1. **`Machine-v5` 自身附录是否补一条**：按本次要求，变更记录只落 `SimRISC-00` 的 `0.5.7-rc` 段；`Machine-v5` 附录 `0.4.7-rc`（版本保持）未增条目。若要逐册留痕，建议在该段追加一条（内容同 `SimRISC-00` 的新增条目）。
2. **`check-knowledge-refs` 既有红**：见完成区「遗留问题」；是否修他人任务书由主会话裁定（本任务限定改动文件，未动）。

## 审阅记录

### 第 1 轮 engineer 自审

**审查面**：5 个改动文件逐行 + 锁注释 + 证据脚本两路注入。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 新句若沿用「`immu18` 低 8 位」措辞，与验收 grep `immu18.*低 8 位` = 0 自相矛盾 | ✅已修 | 三处统一写 `immu18[7:0]` 不携带服务号 | 三判据命中 0/0/0 |
| F2 变更记录若引用旧句原文会破坏归零断言 | ✅已修 | `SimRISC-00` 条目只写正向口径、不引旧句 | 三判据命中 0/0/0 |
| F3 `DD-D002` 原句自相矛盾（低 8 位 vs `rd16`） | ✅已修 | 固定标记 + `immu18[7:0]` 不携带 + 服务号在 `rd16` | 该文件新口径 1 行、旧句 0 |
| F4 锁只重算 1 册会漏 `SimRISC-00`（本任务也改了它） | ✅已修 | 两册 sha256 同笔重算 + 注记 | 21 册现场重算逐一 PASS |
| F5 `check-knowledge-refs` 全局 rc=2（HEAD 既有、他人任务书） | ⏸延后 | 未改（越界）；脚本改为对 HEAD 临时树做违规集合比较 | 集合相同（各 1 条）+ 基线 rc=2 |

**判决**：F1–F4 已修并复验；F5 属既有红、越界未改（已登记待裁定）⇒ 交付「待验收」，完成区照实标注该门控状态。

### 第 1 轮 reviewer 验收（2026-11-14，HEAD `85490bd2`，工作树干净）

**重跑（全部自跑、`echo $?` 取真退出码）**
- 一键证据脚本（运行期目录，下称 run.sh）⇒ `RESULT: PASS` rc=0；`--inject` ⇒ `RESULT: INJECT PASS` rc=0（①DD-D002 改回旧句：三判据 1/1/1、注入态 rc=1，cp+md5 还原 rc=0；②锁 Machine-v5 sha256：`MISMATCH`、rc=2，还原 rc=0）。
- 门控：check-spec-readonly `21 read-only spec volume(s) OK` rc=0、-changelog rc=0、-purity rc=0、-refs rc=0、-cite-targets rc=0、-numbering rc=0、asm-list rc=0、asm-prose rc=0、rule-refs rc=0、legality-drift rc=0、legality-invariants rc=0；**check-knowledge-refs rc=2**（`FAIL (1 具体运行期路径引用)` → `.tao/tasks/qemu/m13-qemu-015…md:97`，他人文件）。
- 既有红独立复核：`git archive 5cf0f87f` 导出临时树跑同一脚本 ⇒ 同 1 条、同文件、FAIL ⇒ 基线既有、本任务未新增（非采信完成区）。
- 锁独立重算（自写 tomllib+sha256）：21 册全 MATCH；`SimRISC-00=dee1c73d…60c8`、`Machine-v5=534a9e7e…acfb` 与完成区一致；锁 `git diff` 仅 2 行 sha256 + 2 段注记 ⇒ 其余 19 册未动。
- 旧句归零（自扫 + 同义变体：`低八位`/`immu18 低字节`/`op 放立即数`/`服务号.*立即数`/`0x3FF00\+`/`低8位`）：四目录全 0；全仓（除 adr/archive/.work）仅剩任务书与 `milestones-m13` 的「修旧句」描述行 + **`tests/inst/11-cfx/trap_ciii_cfx.S` L24/L49**（见 findings）。
- 语义：三处新句均为「`immu18[17:8]==0x3FF` 固定标记、`immu18[7:0]` 不携带服务号、号 `rd16`/参 `rb16`/返 `rd8`」；`trap <any cfxha>, 0x3FF00`、`trap cfx_hmon, 0x3FF00`、`trap <cfxha>, 0x3FF00` 及「任意 cfxha 等效、判定只依赖 `immu18[17:8]`」全保留（0x3FF 命中 3/13/6 行）；Machine-v5 `§5.2` 引用真实存在且表列 rd16/rb16/rd8。
- 变更记录：`SimRISC-00` 0.5.7-rc 新增条无任务号/ADR/ISS（changelog 规则 6 PASS），版本仍 `0.5.7-rc`；规则**不**要求逐册逐条 ⇒ `Machine-v5 0.4.7-rc` 未加条目合规（已列待裁定）。
- 越界：`git diff --stat 5cf0f87f..HEAD` = 6 文件（3 文档 + SimRISC-00 + 锁 + 任务书），`components/`/`tests/`/`Makefile`/台账 0 命中；交付时 `git status --porcelain -uall` 空（本轮写入审阅记录后仅本任务书 M，已复跑 run.sh rc=0、knowledge-refs 回基线 1 条）。
- 独立注入（自设计第 3 路）：`contract-semihosting §1`「服务号由 `rd16` 给出」→「服务号占 `immu18` 低 8 位（`0x3FF00 + op`）」⇒ run.sh rc=1（旧句 1/1/1 + contract rd16 行数 0）；cp+md5 还原（`24f00407…` 复原）⇒ rc=0。另注入探针文件证明脚本检查4/6 有可达 FAIL（各 rc=1），已删、回绿 rc=0。

**约束核验**：独立 worktree/分支 ✓、未提交 git ✓、未跑 install-host/check-modules/build-* ✓、还原只用 cp+md5（未用 checkout/restore）✓、完成区 13 行 ≤30 ✓、状态=待验收 ✓。

**findings（不阻断，交 architect）**：① `tests/inst/11-cfx/trap_ciii_cfx.S` L24/L49 仍写「`immu18` 低 8 位携带（`0x3FF00 + op`）」，与新口径矛盾——硬约束 4 禁改 `tests/**`，本轮未改（合规），建议另立小任务；② 完成区未抄授权原话（Process-06 §5 要求完成区记录授权原话；原话在任务书 §用户裁定与锁注记），收尾补一行；③ 脚本检查4/6 基线用 `HEAD`+裸 `git diff`，WIP 提交后基线=本任务提交、判别力下降（既有红我已用 5cf0f87f 导出树独立复核，结论不受影响），建议改 `$BASE..HEAD`；④ `check-knowledge-refs` rc=2 为他人任务书既有红，待裁定。

**判决：Accepted**（验收命令块在我自己的重跑下除既有红外全绿；硬约束无违反）。

## 完成区

**测试结果**：一键证据脚本（运行期目录）rc=0；注入 2 路均「注入态 FAIL → cp+md5 还原 → 回绿」。`check-knowledge-refs` 全局 rc=2 为 HEAD 既有（见遗留）。
**修改文件**：`.tao/contracts/contract-semihosting.md`（§1 L18）、`spec/Machine-v5-测试机运行环境.md`（§5.1 L175）、`docs/DDLN/D-运行平台/DD-D002-运行平台--测试机运行环境.md`（L67）、`spec/SimRISC-00-指令系统设计.md`（0.5.7-rc 段 +1 条）、`manifests/spec-readonly.lock.toml`（`SimRISC-00`/`Machine-v5` 两条 sha256 + 注记）、本任务书。
**验收结果**：
- 旧句归零：`0x3FF00 + op` 0 命中；`服务号.*低 8 位` 0；`immu18.*低 8 位` 0（扫描 `spec/`、`.tao/contracts/`、`docs/DDLN/`、`contracts/`）。
- 新口径在位：contract §1 / Machine-v5 §5.1 / DD-D002 各 1 行「服务号 … `rd16`」；`0x3FF` 标记语义保留（三处命中 3/13/6 行）；`trap cfx_hmon, 0x3FF00` 调用形如各保留 1 行。
- 锁：`check-spec-readonly: 21 read-only spec volume(s) OK` rc=0；新 sha256 = `SimRISC-00` `dee1c73d…60c8`、`Machine-v5` `534a9e7e…acfb`（其余 19 册原值）。
- 门控 rc=0：check-spec-readonly、-changelog、-purity、-refs、-cite-targets、-numbering、check-asm-list、check-asm-prose、check-rule-refs、check-legality-drift、check-legality-invariants。
- 注入①：DD-D002 改回旧句 ⇒ 三判据各命中 1、rc=1；还原后 md5 一致、rc=0。
- 注入②：只改锁里 `Machine-v5` 的 sha256 ⇒ `check-spec-readonly` rc=2 且打印 `MISMATCH spec/Machine-v5-…`；还原后 rc=0。
**新发现/坑**：① 旧句原文**不得**出现在变更记录/任务书里，否则归零断言自破 ⇒ 记录只写正向口径「`immu18[7:0]` 不携带服务号」。② 可沉淀：semihosting「标记在指令、服务号在寄存器」的惯例（ARM `SVC #imm`/`R0`、RISC-V `ebreak` magic/`a0`）与三实现（QEMU/guest/RTL）取 `rd16` 一致；另复核 `SimRISC-11 §陷入指令`、`DADAO-22 §1` 无同类旧句（仅有「`immu18` 为功能编号」的一般表述，不动）。
**遗留问题**：`make check-knowledge-refs` rc=2 为 HEAD 既有——`.tao/tasks/qemu/m13-qemu-015-ldt写rf0不清33-32.md` 含一条具体运行期日志引用（`check-inst.log`）；本任务改动前后违规集合逐条相同、未新增（脚本以 HEAD 临时树为基线做集合比较）。越界未改，建议改为「运行期日志（已清理）」措辞或占位形。

## 授权原话（Process-06 §5）

> 「确认 rd16，修 §1 措辞（推荐）」（用户 2026-11-14，经主会话问答；依据：ARM/RISC-V 均「标记在指令、服务号在寄存器」）
