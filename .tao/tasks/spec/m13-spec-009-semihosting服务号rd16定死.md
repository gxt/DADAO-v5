# m13-spec-009: semihosting 服务号通道定死为 `rd16`（修 contract §1 / Machine-v5 / DDLN 的「immu18 低 8 位」旧句）

**模块**：spec
**项目里程碑**：M13
**依赖**：无（`m12-chipyard-016` 已按 rd16 实现并实测通过）
**可并行分片**：否（契约 + spec + 讲义 + 只读锁同笔）
**预估**：1–2 h
**状态**：待开始

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

（实现中写）

## 审阅记录

（待填）
