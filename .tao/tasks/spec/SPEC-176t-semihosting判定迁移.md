# SPEC-176t: semihosting 判定迁移至 0x3FF00–0x3FFFF（ADR-0038）

**模块**：spec
**项目里程碑**：M10
**依赖**：ADR-0038（Accepted）、SPEC-175t（HBI `0x30001`）
**状态**：已验证

## 执行环境
本地（纯文档；`spec/Machine-01`、`spec/DADAO-23` 只读锁按本任务授权更新）

## 接口规范

### 背景（用户 2026-10-26 裁定）
`SPEC-175t` 的 HBI 初始化 `0x30001` 与旧 semihosting tag（`immu18[17:16]==0b11`）冲突。用户裁定：**semihosting 判定迁到 `0x3FF00–0x3FFFF`**，`HBI_<name>_INIT` 保持 `0x30001`；D1/D2/D4/D5 已确认，D3（SBI `0x3FFFF`）待定（ISS-334）。

**用户原话**：「**0x3ff00-0x3ffff**」。

### 输入
- `.tao/adr/adr-0038-semihosting-tag-range.md`（D1–D5）
- `spec/Machine-01-测试机运行环境.md` §4.1/§4.3/§5.1/§5.2
- `.tao/contracts/contract-see.md` §4、`.tao/contracts/contract-semihosting.md` §1
- `spec/DADAO-23-HBI-超管系统二进制接口.md` §3

### 改动清单（逐条）

#### 1. `spec/Machine-01`（版本 0.3.1 → **0.3.2-rc**）
- 册头「状态」行改为「当前（`0.3.2-rc`，未发布；`0.3.1` 生效于 2026-10-16，…）」；文末附录**新开** `### 0.3.2-rc（未发布）`，条目：semihosting 判定迁至 `0x3FF00–0x3FFFF`（`ADR-0038`）。
- §4.1：`immu18[17:16] ≠ 2'b11` → **`immu18 < 0x3FF00`**（即不在 `0x3FF00–0x3FFFF`）。
- §4.3 表：
  - 一般 trap：`immu18 < 0x3FF00`；
  - semihosting：**`0x3FF00 ≤ immu18 ≤ 0x3FFFF`**（`immu18[17:8] == 0x3FF`）。
- §5.1：
  - 判定改为 **`immu18[17:8] == 0x3FF`**（`0x3FF00–0x3FFFF`），仍与 `cfxha` 无关；
  - 调用示例 `trap <any cfxha>, 0x30000` → **`0x3FF00`**；
  - 「两条路」同步。
- §5.2 传参/返回不变；如提到 `0x300xx` 的 op 值，改为「`0x3FF00 + op`（op 仍占低 8 位）」。
- 全文不得再出现 `immu18[17:16]` / `2'b11` 的 semihosting 判定。

#### 2. `.tao/contracts/contract-see.md` §4
- 两条（一般 trap / semihosting 分离）改为新判定：`immu18 < 0x3FF00` 走向量；`immu18[17:8] == 0x3FF` 走 semihosting 短路。

#### 3. `.tao/contracts/contract-semihosting.md` §1
- 判定：`immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）；
- 调用形如 `trap <any cfxha>, 0x3FF00`；
- 「两条路」同步；op 值仍在低 8 位（`0x3FF00 + op`）。

#### 4. `spec/DADAO-23` §3（版本 0.1.3 → **0.1.4-rc**）
- `HBI_<name>_INIT` 编码条补一句：
  > 该编码**不落在 semihosting 区**（`0x3FF00–0x3FFFF`），按一般 trap 进入目标 cfx 向量。
- 册头版本 `0.1.4-rc`；附录新开 `### 0.1.4-rc（未发布）`，条目：补 semihosting 区排除说明。

#### 5. 只读锁
- `manifests/spec-readonly.lock.toml` 文件头追加 2026-10-26（SPEC-176t）授权说明（用户原话「0x3ff00-0x3ffff」+ D1/D2/D4/D5 确认）；重算 `spec/Machine-01`、`spec/DADAO-23` 的 sha256。

### 约束
- **只改**上述 4 个文档 + 锁 + 本任务书 + `milestones.md`；**不改** `spec/DADAO-22` 的 `0x3FFFF`（D3 待定，ISS-334）、不改 QEMU/测试（QEMU-076t）、不改 ADR-0020 正文（注记已在 ADR-0038 落笔）。
- **不**顺手改其它 `0x3FFFF` 出现处（SBI 的掩码提取 `0x3FFFF` 是 immu18 掩码，不是保留值，**不动**）。
- 临时目录 `/tmp/opencode/SPEC-176t/`。

## 验收标准
1. `make check` rc=0（含 `check-spec-refs`、`check-spec-changelog`、`check-contracts-*`、`check-spec-readonly`）。
2. grep 断言（贴输出）：
   - `spec/Machine-01`、`contract-see.md`、`contract-semihosting.md` 中 **`2'b11` / `immu18[17:16]` 的 semihosting 判定 = 0**；
   - 三处均含 `0x3FF00` 与 `0x3FF`；
   - `DADAO-23` 含「不落在 semihosting 区」；
   - `DADAO-22:863` 的 `0x3FFFF` **未改**（D3 待定）。
3. Machine-01 = `0.3.2-rc`、HBI = `0.1.4-rc`，附录段/册头一致，无空 `-rc` 段以外的多余段。
4. 锁 2 个 sha256 匹配；`check-spec-readonly` rc=0。
5. 完成区 ≤30 行，贴命令/退出码；证据 `.work/evidence/SPEC-176t/run.sh`。

## 本任务新增用户裁定（2026-10-26，子代理问答摘要）

1. **HBI/HEE 版本互锁**：`check-spec-changelog` 的互锁组 `hee-hbi` 要求 HEE/HBI 顶部段版本一致，只升 HBI 会 FAIL（探针复现 rc=1：`互锁组 hee-hbi 组内顶部段版本不一致: ['0.1.3', '0.1.4']`）。用户选择「**HEE 同步升 0.1.4-rc（推荐）**」⇒ `spec/DADAO-13` 同步册头/附录，正文不变。
2. **既有门控红（非本任务引入）**：`check-knowledge-dir` 报 `.tao/knowledge/cfx-audit-2026-10-26.md` 白名单外（该文件由 `e64168cf` 引入，早于本任务，全仓无引用）。用户裁定「**取消这个 check**」；追问范围后明确「**从L1摘除，放到里程碑check里**」⇒ `Makefile` L1 依赖去掉、挂 `check-milestone`，`docs/Process-07` 登记同步。

## 完成区

**状态**：已验证

### 修改文件
- `spec/Machine-01-测试机运行环境.md`（0.3.2-rc；§4.1/§4.3/§5.1 + 附录）
- `.tao/contracts/contract-see.md`（§4 两条路）、`.tao/contracts/contract-semihosting.md`（§1 判定/调用形/两条路）
- `spec/DADAO-23-HBI-超管系统二进制接口.md`（0.1.4-rc；§3 补句 + 附录）
- `spec/DADAO-13-HEE-超管系统运行环境.md`（**用户裁定新增**：0.1.4-rc 同步，正文不变）
- `manifests/spec-readonly.lock.toml`（文件头授权段 + 3 册 sha256 重算）
- `Makefile` + `docs/Process-07-门控分层规范.md`（**用户裁定新增**：`check-knowledge-dir` 摘出 L1、挂 `check-milestone`）
- `.tao/tasks/spec/SPEC-176t-semihosting判定迁移.md`、`.tao/knowledge/milestones.md`（状态）
- 证据：`.work/evidence/SPEC-176t/run.sh`（`.work/**` 不入 git）

### 验收命令与结果
- `make check` → **rc=0**（尾行 `repository checks (L1): PASS`）
- `make check-spec-readonly` → rc=0（21 册 OK）；`make check-spec-changelog` → rc=0（`files=21 segments=43 rc_segments=5`，hee-hbi 互锁一致）
- `make check-contracts-dir/check-contracts-pending/check-contract-relocs` → rc=0
- grep：`immu18[17:16]`/`2'b11` 在三文件计数 **0**；三处均含 `0x3FF00` 与 `immu18[17:8] == 0x3FF`
- `DADAO-23` 含「不落在 semihosting 区」×2；`DADAO-22:863` 的 `0x3FFFF` 内容与 `git diff` 均未变
- 锁 sha256（现场=锁）：Machine-01 `78e1f8bc…`、DADAO-23 `04f3514d…`、DADAO-13 `76fd50a5…`
- `.work/evidence/SPEC-176t/run.sh` → **13 checks / 0 failures，rc=0**（含注入反例→FAIL→`cp`+md5 还原→回绿）

### 遗留
- D3（`DADAO-22:863` 保留值 `0x3FFFF` 现落入 semihosting 区）待定，`ISS-334`；本任务未改。
- QEMU 译码/测试迁移归 `QEMU-076t`。
- `docs/DDLN/D-运行平台/{DD,TT}-D002`、`docs/DDLN/README.md:48`、`docs/DDLN/A-发展历程/{DD,TT}-A003` 仍写旧 tag（不在本任务允许文件集，未改）——需另立任务同步。
- 根 `README.md`「在研版本」列未同步（Machine `0.3.0`、HEE/HBI `0.1.3-rc`；且 SPEC-175t 后 AEE/ABI 等列已滞后）——非本任务允许文件集。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-26）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `make check` 首轮 rc=2：`check-knowledge-dir` 报 `cfx-audit-2026-10-26.md` 白名单外（`e64168cf` 引入，非本任务） | ✅已修 | 经用户裁定「从L1摘除，放到里程碑check里」：`Makefile` L1 依赖去掉、挂 `check-milestone`；`docs/Process-07` 登记 | `make check` rc=0；evidence check 10/11 PASS |
| F2 只升 HBI ⇒ `check-spec-changelog` 互锁组 `hee-hbi` FAIL（探针 rc=1） | ✅已修 | 经用户裁定「HEE 同步升 0.1.4-rc」：`DADAO-13` 册头 + 附录新段（正文不变）+ 锁 sha256 | changelog rc=0（`segments=43`）；lock MATCH |
| F3 附录若写 `ADR-0038` 会被 `check_spec_changelog` 判禁用（ADR/任务号） | ✅已修 | 附录条目不含 ADR 号；授权/决策指针落锁文件头注释 | changelog rc=0；`grep ADR- spec/*` 附录 0 命中 |
| F4 Machine-01 附录初版含 `immu18[17:16]`/`2'b11`，与验收 grep（=0）冲突 | ✅已修 | 改为「原按 `immu18` 高位两比特的判定作废」 | evidence check 01 计数 0 |
| F5 evidence 断言 02 用 `grep -F 0x3FF` 被 `0x3FF00` 前缀覆盖（弱断言） | ✅已修 | 改为精确 token `immu18[17:8] == 0x3FF` | evidence check 02 PASS（缺项 0） |
| F6 DDLN 讲义 / README 索引仍写旧 tag | ⏸延后 | 未改（越出允许文件集） | 登记「遗留」；见 `grep` 输出 |
| F7 根 `README.md` 版本表「在研版本」列未同步 | ⏸延后 | 未改（越出允许文件集；SPEC-175t 后已滞后） | 登记「遗留」 |
| F8 `DADAO-23 §2` 版本常量仍 0.1.3（册头 0.1.4-rc） | ❌不修 | 按任务「其余版本常量不动」；版本常量在发布时同步（`SPEC-175t` 惯例），无门控要求两者相等 | `grep 0x00010003` 仍在册；changelog/numbering rc=0 |

**自审判决**：改动逐行核对（判定边界 `0x3FF00`、`immu18[17:8]`、附录段逆序/无 ADR 号、锁 3 册哈希、门控层归属）；未修项均已登记且不阻断门控。**可标「待验收」**。

### 第 1 轮 reviewer 验收（2026-10-26）—— **Accepted**

**重跑记录**（workdir=仓库根，退出码均现场取）：`make check` rc=0（尾行 `repository checks (L1): PASS`）；`make check-spec-readonly` rc=0（`21 read-only spec volume(s) OK`）；`make check-spec-changelog` rc=0（`files=21 segments=43 rc_segments=5`，互锁一致）；`check-contracts-dir`/`-pending`/`-relocs` 均 rc=0；`bash .work/evidence/SPEC-176t/run.sh` rc=0（`checks=13 failures=0`）——与完成区声明逐条一致。

**独立反例**（`cp` 备份 + md5 对账，禁 git checkout）：① Machine-01 §5.1 判定改回 `immu18[17:16] == 2'b11` → evidence rc=1（check 01/06/07/11/13 计 5 FAIL）、`check-spec-readonly` rc=2（`MISMATCH … expected=78e1f8bc… actual=b0709068…`）；② DADAO-23 §3 补句删除 → readonly rc=2、evidence 4 FAIL。还原后 md5 与注入前全等（`MD5-RESTORE-OK`），readonly rc=0 回绿。快照对账：验收前后 `git status --porcelain -uall` 均 0 行。

**约束核验**：改动 = 10 文件，与完成区「修改文件」声明一致、无越界（QEMU/测试/ADR-0020/DADAO-22 未动，`git diff 4b0982b0..c39997ed -- spec/DADAO-22*` 空）；`immu18[17:16]`/`2'b11` 三文件计数 0；`immu18[17:8]==0x3FF` ⇔ `0x3FF00–0x3FFFF`（18 位高 10 位全 1）等价、一般 trap `immu18 < 0x3FF00` 边界正确；`HBI_INIT=0x30001 < 0x3FF00` 落区外，DADAO-23 §3 原编码描述未动、补句不改服务语义；`DADAO-22:863` 保留值与 SBI 8 处掩码 `0x3FFFF` 均未改；版本/互锁（Machine `0.3.2-rc`、HBI/HEE `0.1.4-rc` 册头=附录）一致；锁 3 册 sha256 现场重算全 MATCH；完成区 30 行（≤30）、`.work/` 已 gitignore。两处用户裁定均落纸（摘要 + 锁头原话），Process-07 登记与 Makefile 依赖/help 同步（`.PHONY` 原先亦不含该目标，非本任务引入）。

**Finding（非阻断）**：F-r1 `check-milestone` 现因 `cfx-audit-2026-10-26.md` 白名单外**恒红**——红被挪走而非消除，下次里程碑收口会挡路；更小改法（仅记录）：把该文件移入子目录即可绿、无需动分层。F-r2 evidence 断言 3 期望 `>=1` 区分不了「正文补句/附录句」（删正文句仍 PASS），被锁哈希兜底不放水。F-r3 任务书验收标准 4 写「锁 2 个 sha256」（裁定前口径），实际 3 册（完成区已如实写 3）。F-r4 SBI 保留值 `0x3FFFF` 现落 semihosting 区、op `0xFF` 与现 25 服务（`0x01–0x31`）不冲突——D3/ISS-334 已登记，收口前须裁定。

