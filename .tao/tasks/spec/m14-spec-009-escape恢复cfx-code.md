# m14-spec-009: `escape` 恢复 `inner_cfx_code`（补 `excp_prev_cfx_code`，spec + QEMU）

**模块**：spec
**项目里程碑**：M14
**依赖**：无（与 `m14-linux-017` 串行：本任务改 QEMU，017 只读它）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（spec + 组件补丁 + 契约）
**状态**：已验证

## 背景与授权（用户 2026-11-18 裁定 B）

`m14-linux-017` 的 F36 定位：同步帧内到达 tick ⇒ `§5.2 步骤 6` 把 `inner_cfx_code` 改为目标 cfx ⇒ 该帧随后的 `escape cfx_smon` 必然报 `CFXESC`（`§5.3 步骤 0`：`cfxha != inner_cfx_code`）。实测关闭该 tick 后同路径连做 3 次 escape 全成功。

**spec 缺口**：`§5.3` 对 `inner_run_mode` 有保存/恢复（`excp_prev_run_mode`），对 `inner_cfx_code` **只有保存、没有恢复**。

**用户裁定（2026-11-18，逐条）**：

1. **采纳方案 B**（改 spec + QEMU）。
2. `excp_prev_cfx_code` **放 cg5，与 `excp_prev_run_mode` 并列**（即现 `cg5 rc1` 的 reserved 槽）。
3. **版本号不变**（`DADAO-12` 不升版，只加附录变更条目）。
4. QEMU 改完后 017 才继续。

## 目标（spec + QEMU 同笔）

### 1. `spec/DADAO-12-SEE-主管系统运行环境.md`

- **§3.6 cg5 表**：把 `rc1` 从 `reserved` 改为
  `excp prev cfx code` / `cfx_⟨cfxname⟩_excp_prev_cfx_code` / 初始 `0` / `RW` / 「异常前当前核芯功能扩展编号，硬件陷入时保存，软件可写」。
- **§5.2 步骤 5（保存现场）**：增加「`excp_prev_cfx_code` 记录异常前的 `inner_cfx_code`」。
- **§5.2 伪代码**：`cfx_⟨cfxname⟩_excp_prev_cfx_code <= inner_cfx_code`（在 `inner_cfx_code` 被改写**之前**）。
- **§5.3 步骤 2（恢复运行模式）**：改为「恢复运行模式**与当前 cfx**」：`inner_run_mode <= prev_run_mode`、`inner_cfx_code <= prev_cfx_code`。
- **§5.3 伪代码**：加 `inner_cfx_code <= cfx_⟨cfxname⟩_excp_prev_cfx_code`。
- **附录变更记录**：加一条内容条目（**版本号不变**）；说明动机（异常帧被异步事件污染后无法正确返回）与影响（`escape` 后 `inner_cfx_code` 与 `run_mode` 同进退）。
- 同步 `§5.3` 顶部那句「`escape` 恢复 `excp_prev_run_mode`，以及 trap 进入时保存的 `global_cfx_intr_mask`」→ 加「与 `excp_prev_cfx_code`」。

### 2. `components/qemu/patches/target/dadao/**`

- `cpu.h`：`struct` 加 `uint64_t prev_cfx_code;`（注释 `cg5 rc1`）。
- `cpu.c`：复位初始化。
- `helper.c`：
  - trap 进入（保存现场处）：`env->cfx[ci].prev_cfx_code = env->inner_cfx_code;`（**必须在 `inner_cfx_code` 被改写之前**；注意 `ci` 是目标 cfx 的下标，保存的是**进入前**的值）；
  - `escape`（恢复运行模式处）：`env->inner_cfx_code = env->cfx[ci].prev_cfx_code & 0xff;`（位宽按 spec 的 cfx 编号范围）；
  - cg5 rc1 的读写：`helper.c` 的寄存器分发表里把 `case 1` 从 reserved 改为 `&r->prev_cfx_code`。
- **走 `make_patch qemu` 重导出补丁**（禁手改 index）；`--source-state qemu` 必须 `base+1 clean`。

### 3. 契约同步

- `.tao/contracts/contract-see.md` 若含 cg5 寄存器表 ⇒ 同步 rc1 行。
- `spec/.manifests.toml` 的 `DADAO-12` 条目 **sha256 同笔重算**（这是 `check-manifests-guard` 的硬要求）。
- 若 `contracts/` 下有机器可读的 cfx 寄存器投影 ⇒ 同步。

## 验收（逐条贴真实 rc）

1. `make check-manifests-guard` rc=0（`DADAO-12` 新 hash 与清单一致）。
2. `make check-patch-tree` 的 **qemu 段** rc=0（0 problem）；`--source-state qemu` rc=0（`base+1 clean`）；`make_patch qemu` 二次运行 **0 written**（幂等）。
3. **QEMU 行为验证**（最小、可失败）：
   - 构造场景：supv 帧内投递 tick ⇒ 该帧 `escape` 成功后 `inner_cfx_code` 回到进入前的值；
   - 反例：把 `escape` 的恢复那行临时删掉 ⇒ 必须复现 `CFXESC` ⇒ 还原 ⇒ 恢复正常。
   - 用现有 `m14-qemu-*` 探针或最小裸机探针；**不要求跑 Linux**（017 会做端到端）。
4. `check-spec-drift`、`check-spec-purity`、`check-spec-refs`、`check-spec-numbering`、`check-spec-changelog` rc=0（spec 改动不得破坏这些）。
5. `check-syscall-abi`、`check-interface` rc=0（若受影响）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. **版本号不变**（用户裁定 3）：`DADAO-12` 的版本行与 `-rc` 段一字不动，只加附录条目。
3. 只动：`spec/DADAO-12`、`spec/.manifests.toml`、`components/qemu/**`（补丁经 `make_patch`）、`.tao/contracts/contract-see.md`（若需）、`docs/Process-06`（若需）、本任务书。
4. **不碰 `components/linux`**（017 在途）。
5. `cp`+md5 还原（禁 checkout/restore/stash/show）。
6. **禁并发构建与门控**（017 踩过）。

## 待裁定

（执行中如有 → 写入本节并返回）

## 审阅记录

### 第 1 轮 engineer 自审

逐行审了 `spec/DADAO-12` 的 6 处改动、`helper.c`/`cpu.h`/`cpu.c` 的 3 处实现、两份手写合约与两件生成投影、探针与 `run.sh`。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 探针初版把 `cfx_hart` 的 supv 向量设成「CFXESC 报告器」，异步投递也走该向量 ⇒ 探针恒红/语义混淆 | ✅已修 | 同一入口按帧内 `excp_cause_id` 分流（`0x400`=TIMER 正常路径，含 `1<<3` ⇒ 0x31） | 注入「删恢复行」得 0x31、正常得 0；`run.sh` 两次回绿 |
| F2 `cfx_enter` 里「after a delivery the frame restores only the run mode」注释与改后语义矛盾 | ✅已修 | 改写为「过滤行只由运行模式选定」 | `git diff` + `check-qemu-forms` rc=0 |
| F3 `.tao/contracts/contract-see.md` §6.2/§6.4 明文写「帧内没有 `prev_cfx`」「`escape` 不恢复 `inner_cfx_code`」，与改后 spec 直接冲突 | ✅已修 | §6.2 两条、§6.4 旋钮条、附录 A §6 行同笔改；§7 加变更条目（版本号不动） | `check-spec-drift` rc=0、`check-contract-relocs` rc=0 |
| F4 `contract-syscall §8` 的 cg5 现场字段清单由 5 项变 6 项 | ✅已修 | 清单加 `excp_prev_cfx_code` + §12 变更条目 | `check-syscall-abi` rc=0 |
| F5 `contract-cfx-aliases.md` 与 `contracts/cfx-aliases.txt` 是 spec 投影，cg5 rc1 改定义会改计数（1272→1284、1308→1320） | ✅已修 | 用 `tools/spec/gen_cfx_aliases.py`、`tools/llvm/gen_cfx_alias_table.py` 重导，未手改 | `check-cfx-aliases`、`check-cfx-alias-table`、`check-isa-coverage` 全 rc=0 |
| F6 是否给 QEMU `-d cpu` 的 CFX 行加 `prev_cfx_code` | ❌不修 | 不改 dump 格式（既有探针解析该行，改格式超出本任务） | 探针用 `cfx2rd` 架构读取，不依赖 dump |
| F7 时序假设「定时器在 hmon 里已 armed」会造成假绿（tick 早投递 ⇒ 嵌套不在 smon 帧内） | ✅已修 | 改为在 `cfx_smon` 帧内 arm；断言 `cfx_hart` `cg5 rc1 == 2`（早投递会是 3 ⇒ 红 0x57）；有界等待失败 0x52 | 把该断言期望改成 99 后实跑得 `guest exit 0x57`（断言可达 FAIL）；正常 run 六项观测全过 |
| F8 「`make check-patch-tree` 全仓」红：11 problem 全在 `components/linux` | ⏸延后 | 017 在途（linux 源树 `base+1 clean` 但补丁集属 017 分支），与本任务无关；qemu 段单独复核 0 problem | `check_patch_tree.check_component("qemu")` → `problems=0`；`--source-state` linux/qemu 均 OK |

判决：finding 全部已处置（F6 明确不修、F8 责任归属 017），状态 → `待验收`。

### 第 1 轮 reviewer 验收（2026-11-18）

**重跑记录（均本人在任务 worktree 执行，命令 → 真实 rc/输出）**
- 证据脚本 `bash .work/evidence/m14-spec-009/run.sh` ⇒ `RUNSH_RC=0`，`PASS=16 / FAIL=0`：source-state、patch-tree `problems=0`、`make_patch` 两次 `0 written`、`build-qemu`、probe `guest exit 0`、注入 `escape_restore → 0x31`、`rc1_dispatch → 0x41`、两次 `restore (cp+md5)` 一致、两次回绿 `0`。
- 自注入①（删 §5.2 保存行 `env->cfx[ci].prev_cfx_code = env->inner_cfx_code & 0x3F`）：`run.sh --no-inject` ⇒ `rc=1`、5 FAIL（source-state `clean=False`、patch-tree `problems=2`、make_patch `actual=1 1`＝脏树拒导出 E1/E3 故补丁未被改写、probe `actual=harness-rc=1`、guest TIMEOUT）。
- 自注入②（删 §5.3 恢复行 `env->inner_cfx_code = env->cfx[ci].prev_cfx_code & 0x3F`）：同脚本 ⇒ `rc=1`、probe `expected=0 actual=0x31`（CFXESC）。
- 两次还原均 `cp` + `md5sum -c` OK（helper.c `ea8a789f…`、helper.c.patch `16bc63c0…` 均与注入前相同）；还原后 `run.sh --no-inject` ⇒ `RC=0`（6/6 PASS）。
- 门控本人重跑 rc=0：`check-manifests-guard`、`check-spec-drift/-purity/-refs/-numbering/-changelog`、`check-syscall-abi`(80/80)、`check-interface`、`check-qemu-forms`、`check-cfx-aliases`、`check-cfx-alias-table`(12 scalars/1320 regs)、`check-isa-coverage`、`check-index-blobs`、`check-contract-relocs`、`check-asm-prose`。
- `check-patch-tree` 全局 `rc=1`：**11 problem 全部为 `linux:` 前缀、qemu 段 0**；`--source-state` `rc=0` ⇒ `qemu: OK HEAD=97ee1ebe00eb count=1 clean=True expected=1`（linux 同为 base+1 clean）；`make_patch qemu` 连跑两次均 `0 written, 69 unchanged`、跑后 `git status` 空。

**约束核验**
1. `git diff 88bf322d..HEAD` = **10 文件**（3 契约 + 3 qemu 补丁 + spec + spec 清单 + `contracts/cfx-aliases.txt` + 任务书）；`components/linux`、`tests/` 改动 **0**；无 Makefile/工具/门控改动。
2. spec：§3.6 cg5 rc1 `reserved` → `excp prev cfx code` / `cfx_⟨cfxname⟩_excp_prev_cfx_code` / 初值 `0` / `RW` / 说明齐；§5.2 步骤 5 与伪代码均**在第 6 步改写 `inner_cfx_code` 之前**；§5.3 步骤 2 与伪代码含 `inner_cfx_code <= cfx_⟨cfxname⟩_excp_prev_cfx_code`。
3. **版本行与全部 `0.7.3-rc` 行 base↔HEAD `diff` 完全一致**；附录只 +1 条（70→71 行），spec `numstat 8+/5-`、5 条删除行全属被改写的 4 处正文 + 1 处伪代码注释。
4. `spec/.manifests.toml` 的 `d5d395a1b53971e90f97931bd6971428f149af3dc013ca64282bc1b307e0a034` 与现文件 `sha256sum` 相符。
5. `contracts/cfx-aliases.txt` 由 `gen_cfx_alias_table.py --out` 重导 **逐字节相同**（非手改）；contract-see §6.2/§6.4/附录 A §6/§7、contract-syscall §8 六项 + §12、contract-cfx-aliases 表行与计数 1284/1320 与 spec 同笔一致。
6. 实现语义：`cfx_enter` 的 `prev_cfx_code` 采样在 `inner_cfx_code = target` 之前、`escape` step 2 恢复 `& 0x3F`、cg5 分发 `case 1: return &r->prev_cfx_code`（RW，与 spec RW 一致）。
7. 脚本审计：每条断言均有可达 FAIL 路径（本人两路注入即证 5 条 FAIL），无恒真/双支同值/写死覆盖计数；还原只用 `cp`+`md5`，未用 checkout/restore/stash。
8. 未提交 git；主工作树 `master` `git status --porcelain -uall` 空；`.work` 源树/补丁/构建已回基线（md5 相等），主树无写入污染。

**判定：Accepted**（未闭合项 1 条、非阻断：全局 `check-patch-tree` 红 11 条全属 `components/linux`，责任在在途 `m14-linux-017`，随其收口复核）。

## 完成区

**测试结果**：运行期证据目录内的 `run.sh` 共 16 项检查全 PASS（rc=0）；两路注入「红→cp+md5 还原→回绿」各 1 次
**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`、`spec/.manifests.toml`、`components/qemu/patches/target/dadao/{cpu.h,cpu.c,helper.c}.patch`（经 `make_patch qemu` 重导出，`series` 未变）、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-syscall.md`、`.tao/contracts/contract-cfx-aliases.md`、`contracts/cfx-aliases.txt`、本任务书
**验收结果**：
1. `make check-manifests-guard` rc=0（`DADAO-12` 新 sha256 `d5d395a1…` 与清单一致，22 项 sha256 全符）
2. qemu 段 `problems=0`；`--source-state` 输出 `qemu: OK HEAD=97ee1ebe00eb count=1 clean=True expected=1`；`make_patch qemu` 二次运行 `0 written`
3. 行为验证（运行期证据目录内 `run.sh`）：supv 帧内投递 `TIMER` ⇒ 嵌套 `cfx_hart` 帧 escape 后外层 `escape cfx_smon` 成功、`inner_cfx_code` 回 15；注入删 `escape` 恢复行 ⇒ 客态 exit `0x31`（`CFXESC`）⇒ 还原 ⇒ 回绿；注入删 `cg5 rc1` 分发 ⇒ 客态 exit `0x41` ⇒ 还原 ⇒ 回绿
4. `check-spec-drift` / `-purity` / `-refs` / `-numbering` / `-changelog` 全 rc=0
5. `check-syscall-abi`、`check-interface`、`check-qemu-forms`、`check-index-blobs`、`check-cfx-aliases`、`check-cfx-alias-table`、`check-cfx-vectors`、`check-asm-prose`、`check-asm-list(-drift)`、`check-isa-coverage` 全 rc=0
**新发现/坑**：① 异步帧同样调 `cfx_frame_block_async`（把**当前模式 monitor** 的 `global_cfx_intr_mask` 置全 1、escape 时恢复），帧内 arm 定时器需知道这点，否则会误判「被屏蔽」；② `cfx_hart` 的 supv 向量同时承载「异步投递」与「`CFXESC` 改写该帧」，只能靠 `excp_cause_id` 区分；③ 全仓 `check-patch-tree` 当前因 017 在途而红（11 problem 全在 `components/linux`），复核须按组件看
**遗留问题**：无（Linux 端到端由 `m14-linux-017` 承担）
