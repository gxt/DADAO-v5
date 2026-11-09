# SPEC-188t: 删除无效屏蔽寄存器定义

**模块**：spec
**项目里程碑**：M11
**依赖**：`SPEC-186t`（A/A1 使用模型：monitor 用 `cfx_intr_mask` + `excp_pending`）；`INTEG-053t`（cfxha 新号）
**状态**：已验证

## 执行环境
本地；只改 SPEC/合约中的寄存器定义，不改 QEMU/gem5/tests 实现。

## 背景

`SPEC-186t` 已定 A1：

- 删除 `inner_cfx_mask`（内部）
- 删除 `switch_cfx_mask`（cg0–3 rc9）
- 删除 `excp_prev_cfx_mask`（cg5 rc1）
- 删除 `excp_cause_mask`（cg0–3 rc11）：同步异常不可屏蔽，不能有 cause mask
- 删除 `excp_cause_nonmaskable`（cg5 rc63）：所有同步原因不可屏蔽，RO 位图冗余
- monitor 用自己的 `cfx_intr_mask`（cg0–3 rc4）过滤异步来源，用 `excp_pending`（cg5 rc5）保存屏蔽期间事件
- `global_cfx_intr_mask` 保留（monitor 全局异步来源掩码，trap 保存/escape 恢复）
- `escape` 不再恢复 `excp_prev_cfx_mask`

但这些寄存器的**定义**仍散落在：

- `DADAO-12 §3.1–3.4`：`<mode>_switch_cfx_mask`（rc9）
- `DADAO-12 §3.6`：`excp_prev_cfx_mask`（cg5 rc1）
- `DADAO-13`：hypv 模式对应行
- `DADAO-12 §3.1–3.4`：`<mode>_excp_cause_mask`（rc11）
- `DADAO-12 §3.6`：`excp_cause_nonmaskable`（cg5 rc63）
- `Machine-v5`、`contracts`、`.tao/contracts`：寄存器投影/访问行为
- `DADAO-12 §1`：`inner_cfx_mask` 注记（186t 已改，本任务复核）

## 目标

1. 删除以下寄存器的**语义定义**，不重排 `cg/rc`：
   - `cg0`–`cg3` `rc9` 标 `reserved`（不再定义 `switch_cfx_mask`）
   - `cg0`–`cg3` `rc11` 标 `reserved`（不再定义 `excp_cause_mask`）
   - `cg5` `rc1` 标 `reserved`（不再定义 `excp_prev_cfx_mask`）
   - `cg5` `rc63` 标 `reserved`（不再定义 `excp_cause_nonmaskable`）
   - `inner_cfx_mask` 从内部寄存器描述中删除
   - 访问 reserved 寄存器 ⇒ `CFXREG`（沿用现有 reserved 规则）
2. `escape` 文本删除“恢复 `excp_prev_cfx_mask`”的表述；`global_cfx_intr_mask` 的 trap 保存/escape 恢复保留（它是 monitor 的全局中断来源掩码，不在三件套内）。
3. 同步 `DADAO-13` hypv 行、`Machine-v5` 与 contracts 投影；`cfx_intr_mask`（rc4）与 `excp_pending`（cg5 rc5）保留，作为 monitor 的异步来源表/pending。
4. 同笔重算 `manifests/spec-readonly.lock.toml` 的 `dadao-12`/`dadao-13`/`machine-v5` sha；其它册不变。
5. 登记后续实现任务（QEMU/gem5/tests）的范围，不在本任务改实现。

## 接口规范

### 1. `DADAO-12`

- §3.1–3.4：删除 rc9 与 rc11 行或改为 `reserved`（推荐后者，保留编号；访问 ⇒ `CFXREG`）。不重排 rc8/rc10。
- §3.6：`cg5 rc1` 与 `cg5 rc63` 改为 `reserved`；删除 `excp_prev_cfx_mask`/`excp_cause_nonmaskable` 说明。
- §1：`inner_*` 注记删除 `inner_cfx_mask`；如仍出现，改为“A1 下不存在”。
- §5.1/§5.3：`escape` 文本删除 mask 恢复；`cfx_intr_mask`/`excp_pending` 保留。
- 历史段不改；变更记录追加一条（无任务号/ADR/ISS）。

### 2. `DADAO-13`

- hypv 模式 rc9/rc11 行改 `reserved`；cg5 rc1/rc63 同步；不改其它 HEE 语义。
- 变更记录追加一条。

### 3. `Machine-v5` / contracts

- 删除对三件套的寄存器名/行为投影；`cfx_intr_mask`/`excp_pending` 保留。
- reserved 访问按 `CFXREG`；不新增寄存器。

### 4. 锁

- 仅 `dadao-12`/`dadao-13`/`machine-v5` 重算；注记含日期 + 授权原话指针 + 改动摘要。

## 范围 / 非范围

**在范围内**：`spec/DADAO-12-*`、`spec/DADAO-13-*`、`spec/Machine-v5-*`、`.tao/contracts/**`（仅寄存器投影）、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

**不在范围内**：QEMU/gem5 实现、`tests/**`、`contracts/` 机器数据（若需同步另立）、`Makefile`、门控脚本、`DADAO-22` 其它语义。

## 验收标准

1. **活文件清零**：`switch_cfx_mask`、`excp_prev_cfx_mask`、`inner_cfx_mask`、`excp_cause_mask`、`excp_cause_nonmaskable` 在 `DADAO-12/13/Machine-v5/contracts` 活文件 0 命中（历史段/变更记录除外）。
2. **reserved 行为**：rc9/rc11/cg5 rc1/cg5 rc63 标 `reserved`；访问 ⇒ `CFXREG`；`escape` 文本不再恢复 `excp_prev_cfx_mask`，但保留 `global_cfx_intr_mask` 的恢复。
3. **保留项**：`cfx_intr_mask`（cg0–3 rc4）与 `excp_pending`（cg5 rc5）仍定义，作为 monitor 异步来源/pending。
4. **跨册一致**：DADAO-12/13/Machine-v5/contracts 对同一 rc/cg 的描述一致；锁 sha 与 `sha256sum` 逐字相等，仅三册变化。
5. **门控**：`check-spec-readonly/refs/drift/changelog/numbering/purity/cite-targets/codeblocks`、`check-contracts-dir`、`check-contract-relocs`、`check-issues`、`check-milestones-fresh`、`make check`（L1）rc=0。
6. **反例可达 FAIL**：把 `switch_cfx_mask` 写回一处 ⇒ 断言 FAIL；`cp`+`md5sum -c` 还原后回绿。
7. **体例**：完成区 ≤30 行；状态 `待验收`。

## 说明

- 本任务只做 SPEC/合约定义删除；QEMU/gem5/tests 的寄存器访问、`escape` 恢复、测试期望需另立实现任务（建议 QEMU/GEM5/TESTCASES 各一），并引用本任务定稿。
- `switch_cfx_mask`/`excp_prev_cfx_mask` 用 `reserved` 而非删号，避免 rc 重排波及 decode/contracts。
- 若发现 reserved 访问在现有 spec 中不是 `CFXREG`，先留问，不自行改语义。

## 未决（下发前确认）

1. `rc9`/`cg5 rc1` 是标 `reserved` 还是彻底删行；默认 `reserved`。
2. contracts 机器数据（`contracts/`）是否同笔同步；默认只改 `.tao/contracts` 人读投影，机器数据另立。
3. 后续 QEMU/gem5/tests 任务是否同批创建；默认本任务完成后按实际影响创建。

## 完成区

**测试结果**：运行期证据脚本 rc=0（25/25 PASS）；`make check`（L1）rc=0；`check-spec-readonly` 21/21；`check-cfx-aliases`/`check-cfx-alias-table`/`check-cfx-alias-install` PASS；`check-milestones-fresh` PASS。
**修改文件**：
- `spec/DADAO-12-SEE-主管系统运行环境.md`：§3.1–3.3 `rc9`/`rc11`、§3.6 `cg5 rc1`/`rc63` 改 `reserved`；§1 注记删 `inner_cfx_mask`；§5.1/§5.3 删 escape 恢复 prev mask（保留 global mask）；附录 0.7.3-rc 补 1 条。
- `spec/DADAO-13-HEE-超管系统运行环境.md`：`cg3 rc9`/`rc11` 改 `reserved`；附录 0.1.4-rc 补 1 条。
- `spec/Machine-v5-测试机运行环境.md`：删除 `switch_cfx_mask`/`excp_prev_cfx_mask` 投影。
- `.tao/contracts/contract-see.md`：同步寄存器投影。
- `.tao/contracts/contract-cfx-aliases.md`、`contracts/cfx-aliases.txt`：由生成器重生成（未手改）。
- `manifests/spec-readonly.lock.toml`：仅三册 sha256 + 注记。
- `.tao/knowledge/milestones.md`、本任务书：状态 `待验收`。
**验收结果**：活文件 5 名 0 命中（变更记录除外）；reserved 行 10 条；`cfx_intr_mask` rc4 4 行、`excp_pending` cg5 rc5 1 行保留；锁 21/21 逐字相等、变更 spec 仅三册；注入 `switch_cfx_mask` ⇒ live 检查 hit=1（FAIL 可达），`cp`+md5 还原后回绿。
**新发现/坑**：
- `contracts/cfx-aliases.txt` 是 spec 投影生成物；删寄存器会令 `check-cfx-alias-table` 红，须按生成器重生成并 `make install-cfx-aliases` 同步 build/install 副本（禁手改）。
- `git diff --name-only` 默认转义非 ASCII 路径，证据断言须 `-c core.quotepath=false`。
**遗留问题**：
- 跨册：`spec/DADAO-23`（HBI §3 启动移交）仍引用 `inner_cfx_mask`/`switch_cfx_mask`/`excp_prev_cfx_mask`；`docs/DDLN` 与 `tests/**` 有同名引用。均不在本任务范围，留问是否另立同步任务。
- 后续实现任务范围（本任务不改）：QEMU/gem5 删除 rc9/rc11、cg5 rc1/rc63 与 `inner_cfx_mask` 读写路径，reserved ⇒ `CFXREG`，escape 不再恢复 prev mask 且保留 global mask；tests 更新 `validate_m5_vectors`/`min_rom_probe_*`/bootrom `hmon.S` 等并重生成 aliases 依赖。

## 审阅记录

#### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `contracts/cfx-aliases.txt` 生成物随删名漂移 | ✅已修 | `tools/llvm/gen_cfx_alias_table.py` 重生成；`make install-cfx-aliases` 同步副本 | `check-cfx-alias-table` rc=0；`check-cfx-alias-install` 6/6 |
| F2 `.tao/contracts/contract-cfx-aliases.md` 生成物 | ✅已修 | `gen_cfx_aliases.py` 重生成（1428→1308） | `check-cfx-aliases` PASS byte-identical |
| F3 证据脚本非 ASCII 路径 + 注入断言可达性 | ✅已修 | 加 `core.quotepath=false`；注入后断言 hit=1 并 md5 对账还原 | `run.sh` PASS=25 FAIL=0；注入→FAIL→还原→回绿 |
| F4 后续实现任务范围未落盘 | ✅已修 | 完成区「遗留问题」登记 QEMU/gem5/tests 范围 | 完成区已列；本任务不改实现（任务书 §范围） |
| F5 `DADAO-23`/`DDLN`/`tests` 仍引用被删名 | ❌不修 | 任务书 §范围 未列，完成区登记留问 | `grep` 命中仅限上述范围；本任务只改 DADAO-12/13/Machine-v5/.tao/contracts |

#### 第 1 轮 reviewer 验收

**重跑记录（reviewer 独立执行，workdir=任务 worktree）**：
- 运行期证据脚本 → **rc=0，`PASS=25 FAIL=0`**，与完成区逐条一致；13 个门控 + `make check`（L1）全 rc=0；`check-spec-readonly: 21 read-only spec volume(s) OK`、`check-cfx-alias-install: PASS (6 checks)`、`check-milestones-fresh: PASS (56 行)`。
- `make -s check-spec-drift` → **rc=0**「spec drift check: PASS」——run.sh 未覆盖此项，reviewer 补跑；`check-issues` 无独立 make 目标，由 `make check` 承担（日志 `check_issues: 4 open, 1 closed`，rc=0）。
- 锁现场重算：21/21 sha256 与文件逐字相等；`git diff` 仅 3 条 sha 变化（dadao-12/13/machine-v5），其余 18 册与 HEAD 相同。
- **独立注入（异于任务书）**：`sed` 把 DADAO-12 `| 0 | 9 | reserved |` 改回 `excp_cause_mask` ⇒ 重跑同一 run.sh → **rc=1，PASS=18 FAIL=7**（live-files=1、reserved-row-count=9、lock-sha=20/21、check-spec-readonly rc=2、make check rc=2 等）；`cp` 备份还原 + `md5sum -c` → OK；再跑 run.sh → **rc=0，PASS=25 FAIL=0** 回绿。全程未用 git checkout/restore/stash。
- 快照对账：注入前后 `git status --porcelain -uall` diff 为空（9 文件）、D12 md5 `772fe5cc…` 复原 OK、无 `运行期临时目录` 残留。

**约束核验**：五名活文件 0 命中（仅 DADAO-12:983 / DADAO-13:59 变更记录，位于附录段后）；reserved 10 行（DADAO-12 cg0–2 rc9/rc11×6 + cg5 rc1/rc63×2，DADAO-13 cg3 rc9/rc11×2），rc8/rc10 未重排；`cfx_intr_mask` rc4 4 行、`global_cfx_intr_mask` cg8 rc1 4 行、`excp_pending` cg5 rc5 保留；escape 步骤 1/伪代码只恢复 `global_cfx_intr_mask`、无 prev mask 恢复；Machine-v5 §2/§3/§4.2 与 contract-see 投影同步；修改文件 9 个与完成区一致，无 QEMU/gem5/tests/components 改动；完成区 16 行 ≤30、状态 `待验收`；SPEC-186t 已合入 master、无并发 reviewer。

**findings（非阻断）**：
1. `run.sh` 未覆盖验收标准 5 的 `check-spec-drift`/`check-issues`（reviewer 已补跑均绿）；建议补入脚本断言。
2. 任务书「不在范围内：`contracts/` 机器数据（若需同步另立）」与实际改 `contracts/cfx-aliases.txt` 冲突——判定为**可接受的生成物机械同步**：该文件是 spec 派生生成物，L1 `check-cfx-alias-table`/`check-cfx-alias-install` 强制其随源同步，不同步则验收标准 5 必红；由生成器重生成（check-cfx-aliases byte-identical）、已在完成区与自审 F1/F2 披露。建议 architect 收尾时在范围条款补一句豁免说明，不判越界。
3. 范围外残留属实：`spec/DADAO-23` §3 共 7 处、`docs/DDLN` 2 文件、`tests/shared/bootrom/step5/hmon.S` 1 处，已登记完成区遗留、未声称全册一致。建议：DDLN/DADAO-23 文档同步另立任务（或由 architect 明确扩 `SPEC-189t` 范围并入），tests 侧归后续 QEMU/TESTCASES 实现任务。
4. `changed-spec-volumes` 断言取 `merge-base HEAD master`，master 前进后可能误报，健壮性提示。

**判决：Accepted**（验收命令块在 reviewer 自己的重跑下全绿、约束无违反、注入 FAIL 可达且回绿）

#### 收尾（architect，2026-11-05）

- reviewer finding 2：`contracts/cfx-aliases.txt` 属 spec 派生生成物，L1 `check-cfx-alias-table/install` 强制随源同步；判为**生成物机械同步**，不判越界，已在完成区说明。
- finding 1： reviewer 已补跑 `check-spec-drift`/`check-issues` 均绿；证据脚本补项属体例改进，不减损结论。
- finding 4：`changed-spec-volumes` 的 merge-base 健壮性提示记入遗留，不阻断。
- finding 3：DADAO-23 §3、DDLN、tests 的旧引用登记为遗留，另立任务处理。
