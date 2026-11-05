# SPEC-192t: 退出码表迁移到 §7.1

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-187t`（已验证；退出码表已写入）、`SPEC-185t`（同改 `Machine-v5`，须先行收口，避免同文件冲突）
**状态**：已验证

## 执行环境
本地；只移动章节位置并同步指针，不改退出码语义。

## 背景（主会话造因，需修正）

`SPEC-187t` 把完整退出码表放进了：

- `spec/Machine-v5-测试机运行环境.md §1.2`（“越界访问与越界取指异常”）

章节语义不匹配：退出码是停机后 host `$?` 的映射，不是地址空间/越界异常内容。随后又在 4 处写了指针：

- `.tao/contracts/contract-see.md`：`完整位域见 spec/Machine-v5 §1.2`
- `ADR-0020 D15` 正文与修订
- `ADR-0004 D5.8`

移动章节时必须同笔更新这些指针，否则全仓不一致。

## 目标

1. 在 `## 7. 退出` 下新增：

   ```markdown
   ### 7.1 退出码（测试机约定）
   ```

2. 把 `§1.2` 中的退出码表整体移动到 `§7.1`：
   - 三段总表
   - monitor 段编码 + 11 个位索引表
   - `CFXTRAP`/`CFXESC` 的 cfx 编码
   - 未映射 / A-D / reserved cfx 落点
   - “编码冻结、不得重排”
   - 删除 `§1.2` 中的重复内容，`§1.2` 只保留内存/越界异常语义。
3. 同步 4 处指针到 `spec/Machine-v5 §7.1`：
   - `contract-see`
   - `ADR-0020 D15` 正文 + 修订
   - `ADR-0004 D5.8`
4. 不改任何退出码数值、位域、monitor 位索引或语义。

## 接口规范

- `§7` 原内容保留，新增 `### 7.1` 在其下；不重排 §1–§6 编号。
- `§1.2` 删除退出码表后，保留原有内存/越界异常段落；若出现悬空引导句，最小修改并披露。
- 指针统一写 `spec/Machine-v5 §7.1`；不复制表内容到 ADR/contract。
- 同笔重算 `machine-v5` 锁 sha；其它册不变。
- 历史段/变更记录追加 1 条（无任务号/ADR/ISS）。

## 范围 / 非范围

**在范围内**：`spec/Machine-v5-测试机运行环境.md`（§1.2/§7 + 变更记录）、`.tao/contracts/contract-see.md`（仅指针）、`ADR-0020` D15 正文/修订、`ADR-0004` D5.8、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

**不在范围内**：退出码语义/数值、QEMU/gem5/tests、其它 spec 册、`contracts/**`、`.tao/knowledge/**`（除 milestones）。

## 验收标准

1. **表只在 §7.1**：`§7.1` 含三段表 + 11 位索引 + 落点；`§1.2` 不再含退出码表；全册退出码表恰 1 份。
2. **指针同步**：`Machine-v5 §1.2` 在 4 处指针中 0 命中（指向退出码的语境）；全部改为 `§7.1`；ADR/contract 不复制表。
3. **语义零改动**：表内容、位域、11 个索引逐字不变；只移动/改指针。
4. **编号**：§1–§6 标题不变；新增 `### 7.1`；`check-spec-numbering` rc=0。
5. **锁**：仅 `machine-v5` sha 变化且逐字相等。
6. **门控**：`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-milestones-fresh`、`make check`（L1）rc=0。
7. **反例可达 FAIL**：把表残留一处到 §1.2，或指针留 `§1.2` ⇒ FAIL；`cp`+`md5sum -c` 还原回绿。
8. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是修正主会话的错误位置与错误指针，不是新增语义。
- 先等 `SPEC-185t` 对 `Machine-v5` 的引用清理合入，再执行本任务；避免同文件并发。
- 若移动后发现 §1.2 标题语义不再覆盖退出码，不改标题，只在 §7.1 承载退出码。

## 完成区

**测试结果**：`check_content.py` 24/24 PASS；注入自检 2/2（表残留 §1.2、指针留 §1.2 ⇒ rc=1；`cp`+`md5sum -c` 还原 ⇒ 回绿，注入前后 git status 逐行一致）；门控 `check-spec-{readonly,refs,drift,changelog,numbering,purity,cite-targets,codeblocks}`、`check-milestones-fresh`、`make check`（L1）均 rc=0。
**修改文件**：`spec/Machine-v5-测试机运行环境.md`（§1.2 退出码块→§7.1 + 0.3.2-rc 1 条）、`.tao/contracts/contract-see.md`（指针）、`.tao/adr/adr-0020-see-semihosting.md`（状态行/D15 正文/Rationale/修订）、`.tao/adr/adr-0004-test-machine.md`（D5.8 正文/修订）、`manifests/spec-readonly.lock.toml`（仅 machine-v5 sha + 注记）、`.tao/knowledge/milestones.md`、本任务书。
**验收结果**：`make-check-L1.log` 末行 `repository checks (L1): PASS`；`check-spec-readonly: 21 read-only spec volume(s) OK`；`check-numbering: PASS`（h2=100 h3=137 total=258）；`check-spec-changelog: PASS`（bullets=231，0.3.2-rc +1）；`check-spec-drift: PASS`；`check_content`：`C 旧表块逐字入 §7.1`、`D 三文件 §1.2 零命中`、`E 仅 machine-v5 一项变化`、`A §7.1 11 个位索引行` 全 PASS。
**新发现/坑**：① `make check` 首跑 rc=2，唯一失败 `check-run-artifacts`（并发任务临时日志 4 个非法名）；重试 1 次（等该任务收尾）后 rc=0，本任务未触碰其文件。② 本 worktree `.work` 是主仓 `.work` 的软链，并行任务的瞬态日志会影响 `check-run-artifacts`。
**遗留问题**：无。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审方式**：自主逐行审查（`subagent_depth=1`，无嵌套子代理）。逐行核对 Machine-v5 §1.2/§7.1/0.3.2-rc、contract-see、ADR-0020/ADR-0004 指针、锁 diff 与证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 §1.2 首句「`CFXTRAP`/`CFXESC` 除外，见下表」在表迁走后悬空 | ✅已修 | 改为「见 `§7.1`」 | `check_content` B/C PASS；§1.2 无「见下表」 |
| F2 「层次与适用」的「按上表归当前 monitor」悬空 | ✅已修 | 改为「按 `§7.1` 的 monitor 段编码归当前 monitor」 | `check_content` A/B PASS |
| F3 移动「未映射/A-D/reserved」是否丢失内存语义 | ❌不修（核实无丢失） | — | §1.2「精确路由」保留三者 ⇒ `CFXMEM`/`ILLI`（Node 未映射/A-D、保留 cfx `ld/st` 与 `trap`/`escape`） |
| F4 指针是否有遗漏 | ✅已修 | contract-see 1 处、ADR-0020 4 处、ADR-0004 2 处全部 §7.1 | `check_content` D：三文件 `§1.2` 0 命中 |
| F5 锁是否只改 machine-v5 | ✅已修（核验） | 仅替换 machine-v5 sha + 1 条注记 | `check_content` E：changed=`[machine-v5]`，条目 21 |

#### 第 1 轮 reviewer 验收

**重跑**（分支 `SPEC-192t`，HEAD `700b81e6`，reviewer 独立执行，非采信完成区）：
- 9 门控逐条 `make <t>`：`check-spec-readonly`（21 read-only spec volume(s) OK）、`check-spec-refs` PASS(0)、`check-spec-drift` PASS、`check-spec-changelog` PASS(bullets=231)、`check-spec-numbering` PASS(h2=100 h3=137 h4=21 total=258)、`check-spec-purity` PASS(hits=0)、`check-spec-cite-targets` PASS(unresolved=0)、`check-spec-codeblocks` PASS(542)、`check-milestones-fresh` PASS(61 行) ⇒ **全部 rc=0**。
- `make check`（L1）**rc=0**，末行 `repository checks (L1): PASS`；`check-run-artifacts: PASS`（SPEC-193t 并发日志未再致红，环境红已消）。
- 证据脚本 运行期证据脚本 **rc=0**（11 项期望 rc=实际 rc=0，`RUN_EXIT=0`）；`run.sh --inject` **rc=0**（inject-1/inject-2 期望 rc=1 实际 rc=1、md5 还原 rc=0、git status 逐行一致）。

**内容核验（我方独立 diff/grep 计数）**：
- 旧块（`完整退出码表`→`reserved cfx`，30 行）与 §7.1 对应段 `diff` **零差异**；`编码冻结` 行逐字相同 ⇒ 三段总表、monitor 段编码、11 位索引（现场计数=11）、`CFXTRAP`/`CFXESC`、未映射/A-D/reserved 落点、编码冻结**逐字未变**。
- §1.2 表行数=0；全册 `完整退出码表（测试机约定）`=1、三段表头=1；§1.2 仅 2 处引导句最小改写（「见下表」→「见 `§7.1`」、「按上表」→「按 `§7.1` 的 monitor 段编码」），已由 engineer 披露。
- 标题 diff 仅 `+### 7.1 退出码（测试机约定）`，§1–§6 与 §7 原两条 bullet 不变；变更记录 +1 条（无任务号/ADR/ISS）。
- 指针：contract-see §7.1×1、ADR-0020 §7.1×4（状态行/D15 正文/Rationale/修订）、ADR-0004 §7.1×2（D5.8/修订）；三文件 `§1.2` **0 命中**；ADR/contract 未复制表（仅原有三分摘要，diff 未增）。
- 锁：文件 `sha256=4f27caf8…` = 锁值；锁 diff 仅 machine-v5 一行 sha + 1 条注记；其余 20 册经 `check-spec-readonly` rc=0 证不变；`check_content` E `changed=[machine-v5]`、条目 21。

**独立注入（reviewer 自行注入，`cp`+`md5sum -c` 还原，未用 git 还原）**：
- 注入①§1.2 残留退出码表（reviewer 措辞，非复用脚本注入）⇒ `run.sh` **rc=1**、`CONTENT_FAIL=3`（`B §1.2 无完整退出码表`、`B 全册退出码表恰 1 份`、`E 锁 sha == 文件 sha`）+ `check-spec-readonly: MISMATCH … actual=11ca6074…` + `make check` Error 2 ⇒ **可达 FAIL**。
- 注入② contract-see 指针改回 `§1.2` ⇒ `check_content` **rc=1**，`[FAIL] D contract-see §1.2 零命中`、`[FAIL] D contract-see 含 §7.1` ⇒ **可达 FAIL**。
- 还原：`md5sum -c` 均 OK（mv5 `9a255370…`、see `a141035f…`）；回绿 `run.sh` **rc=0**、`CONTENT_PASS`；`git status` 注入前/后逐行一致、仓库内无注入残留。

**约束逐条**：①表位置（§7.1 承载、§1.2 只留内存/越界语义、全册恰 1 份）✅ ②内容零改动 ✅ ③指针全改 `§7.1`、0 处 `§1.2`、不复制表 ✅ ④编号（`check-spec-numbering` rc=0，仅新增 7.1）✅ ⑤锁仅 machine-v5 变且逐字相等 ✅ ⑥9 门控 + `make check` 全 rc=0 ✅ ⑦反例注入→FAIL→还原→回绿 ✅ ⑧范围：改动 7 文件全在声明内，无 QEMU/gem5/tests/`contracts/` 改动；完成区 7 行（≤30）、无绝对/运行期路径 ✅。

**判决：Accepted**。非阻断 finding（文档级，交 architect 收尾改）：完成区「新发现/坑」写入并发任务日志路径 并发任务日志路径，建议精简为「并发临时日志致 `check-run-artifacts` 首跑 rc=2，等其收尾复跑 rc=0，本任务未触碰其文件」。

#### 收尾（architect，2026-11-05）

- 完成区并发日志路径已改为通用描述；证据脚本路径已改为“运行期证据脚本”。
- 观察项：`check_content` 的 D 断言当前按整文件不含 `§1.2`，将来其它合法语义引用需放宽；记入遗留，不阻断。
- 判决 Accepted，状态置 `已验证`。
