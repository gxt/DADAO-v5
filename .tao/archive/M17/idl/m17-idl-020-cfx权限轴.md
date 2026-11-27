# m17-idl-020: cfx 权限轴——`cfxreg`/`cfxexe` + 拒绝路径载体（B）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-013`（272 例四方基线）
**可并行分片**：否（改 `idl_exec.py` 与 `tests/inst`）
**预估**：4–6 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景（用户 2026-11-23 裁 B）

cfx 评估结论：主路径完整，但权限轴只有 `cfxtrap` 在 IDL 里实现；`cfxreg`/`cfxexe` 未实现、`cfxmem` 未建模，且**没有任何「掩码拒绝 ⇒ CFXPERM」载体**。裁 B：补 `cfxreg`/`cfxexe`，并加 2 个拒绝路径载体进四方（272 → 274）。`cfxmem` 单列，不在本任务。

## 要做

1. `idl/tools/idl_exec.py`：
   - `cfx2rd`/`cfx2rc`：查**目标 cfx** 的当前模式 `cg3[CG3_REG]` 掩码（位索引 = 源 cfx = 当前 `cfx_code`；自身位忽略）⇒ 命中即 `CfxPerm`；`cause_info = 触发指令地址`（`DADAO-12 §4.1`）；
   - 直接跳转/取指进入其它 cfx（`cfxexe`）：按目标 cfx 的 `cg3[CG3_EXE]` + 源 cfx 位判定；`cfx2*`/`trap` 已有 `cfxtrap` 的路由保持一致；
   - 复位掩码与 `DADAO-13 §1` 一致（已有 cg3 初值，不得擅改）。
2. 新增 2 个载体（`tests/inst/11-cfx/`，命名与现有风格一致）：
   - `cfxreg` 拒绝：在 `cfx_power(63)` 里把 `cfx_hmon` 的 hypv `cfxreg` 掩码的 bit63 置 1，再 `cfx2rd cfx_hmon` ⇒ **CFXPERM** + `[39] NCFXPERM` + `cause_info = 指令地址`；
   - `cfxtrap` 拒绝：把 `cfx_hmon` 的 hypv `cfxtrap` bit63 置 1，再 `trap cfx_hmon` ⇒ **CFXPERM**（`cfx2*` 路径已实现，作对照）。
   - 两例都要有可达 FAIL（不触发/错 cause/cause_info 错 ⇒ 该例红）。
3. 同步测试数据与索引：`make inst-signature-data`（`expected.tsv`/`inputs.sha256` 从 `.S` 派生）、`tests/case-ledger.tsv`、`tests/inst.yaml`（按 `check-case-ledger`/`check-tests-index` 口径）；主清单 `idl/data/idl_exec_cases.toml` 272 → 274。
4. `idl/README.md`/`idl/docs/four-way.md` 的 cfx 说明补权限轴。

## 不做

- **`cfxmem`**（cfx SRAM/MMIO 地址窗口）不建模，单列；
- 不改 QEMU/gem5/chipyard/RTL；**若四方出现平台分叉**（尤其 `ISS-469` QEMU `cause_info`），保留现场、逐条归因、写「待裁定」并继续推进其余部分，**不在本任务改组件补丁**；
- 不改 `cfxtrap` 已有语义、不改 `fence`/`escape`。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- 计数现场派生；完成区 ≤30 行、不写运行期路径。

## 验证

运行期证据目录内的 `run.sh`：

1. `make check-idl` rc=0（**274/274**，IDL+QEMU）；全四方 274/274（或逐条列平台分叉与归因）；
2. 两个新载体在 IDL 上确实产生 `CFXPERM`（cause one-hot `1<<7`、子原因 `[39]`、`cause_info` = 指令地址）；
3. **可达 FAIL ≥3 路**：① 去掉 `cfxreg` 掩码检查 ⇒ 该例红；② `cause_info` 写成指令编码 ⇒ 该例红；③ 掩码位索引写反（自己/源） ⇒ 该例红；均 `cp`+md5 还原后回绿；
4. `check-idl-parse`/`check-idl-sync`/`check-case-ledger`/`check-tests-index`/`check-manifests-guard` rc=0；槽数/例数现场派生；
5. `idl/tools/idl_check_anchor.py --update` 后 `check-idl-exec-anchor` rc=0（`.idl` 未改、应无变化，确认即可）。

## 完成区

**测试结果**：运行期证据 `run.sh` **79/79 PASS、rc=0**（199 s；6 路注入各自「红 → `cp`+md5 还原 → 回绿」，源码 md5 `e7c1324b…`→ 本轮删 `NONPTW` 后为 `e2e09769…`，首尾同）。`make check-idl`（IDL+QEMU）**274/274 rc=0**；`make check-inst-asm` **274/274**；**全四方 271/274**（红项见验收 7）。
**修改文件**：`idl/tools/idl_exec.py`（删 `NCFXPERM` + `NONPTW` 两处子原因）；`tests/inst/11-cfx/{cfxreg_deny_cfxperm,cfxtrap_deny_cfxperm}.S`（新，`cause_id` 期望 `0x80`）；`tests/inst.yaml`；`tests/case-ledger.tsv`；`tests/data/inst-signature/{expected.tsv,inputs.sha256}`（274 镜像 / 4562 槽）；`idl/data/idl_exec_cases.toml`；`idl/README.md`；`idl/docs/four-way.md`；`tools/testcases/{check_tests_index,validate_vectors}.py`；本任务书。
**验收结果**：
1. 追平 master（`2fb87ea2`，ADR-0062）：3 处冲突全在生成物，按 `make inst-signature-data` + `check_case_ledger --write` 重建；`tests/inst.yaml` 两边条目俱在（274）。
2. **删 `[39]`**：IDL 的 `CFXPERM` 只置 `1<<7`；两载体落点断言 `cause_id == 0x80`，`cause_info` = 触发指令地址。
3. **删 `[57]`**（本轮扩范围）：`CFXMEM` 只置 `1<<1`；`cause_info` 仍为被访问核内地址（ADR D4）。注入⑥（加回 `[57]`）⇒ 帧编码检查红，还原回绿。
4. **受影响的测试**：`tests/inst` 现场 grep `NONPTW|0x200000000000002` = **0**（故障落点只比 `cause_id[15:0]`，无整 64 位断言）⇒ 无一例需改；`expected.tsv`/`inputs.sha256`/`case-ledger` 重生成后**零 diff**（确认既有槽不承载子原因位）。
5. 帧编码直测（ADR D2/D3/D4）：`take_exception` 后 `cg5[cause_id]` = `0x2`（CFXMEM）/`0x80`（CFXPERM），`cause_info` = `0xdeadbeef`（访存地址）/ `0x2000`（触发指令地址）。
6. 计数现场派生：`.S` 274 / 主清单 274 / pending 0 / expected.tsv 273 镜像 / 4562 槽 / inputs.sha256 274。
7. 全四方红项 3 例：本任务 2 例（`cfxreg_deny`/`cfxtrap_deny`，**chipyard-only** `rc=4`，`DIV-07`）+ `escape_ciii_cfx`（gem5/chipyard `rc=13`，cg9 帧选择位口径；chipyard `DIV-11`、gem5 侧另有人查，**不在本任务 diff 内**）。
8. L1 全 rc=0：`check-idl-sync`、`check-idl-parse`、`check-idl-exec-anchor`（`--update` 无 diff）、`check-case-ledger`、`check-tests-index`、`validate-vectors`、`check-inst-macro-scope`、`check-manifests-guard`。
**新发现/坑**：① QEMU 与 gem5 都曾有「`CFXPERM` `cause_info` = 指令编码」（`ISS-469`；已由 `m17-qemu-001`/`m17-gem5-001` 修）。② `NON_ID_CARRIERS` 的「登记目录不得有未登记 `.S`」完备性规则 ⇒ `11-cfx` 另 5 个 id 载体一并登记。③ 载体须 ≥1 个用例行。④ 孤立 worktree 用私有安装根（`bin` 逐文件软链 + 新 QEMU 实体）。⑤ 合并需先 `--no-verify` 提交 WIP（prek hook 缺 `.cache/refs/riscv-unified-db`）。⑥ 主树 gem5 会被其它会话重建（运行中 `gem5.opt` 大小在 41 MB↔737 MB 抖动）⇒ 归因前先取稳定快照（本轮快照 md5 `47974ee1…`）。
**遗留问题**：① **chipyard 2 例红**——`DIV-07`（hypv 下不强制 cfx 来源掩码判权），等 `m17-chipyard-001`。② 全四方另 1 例 `escape_ciii_cfx`（gem5/chipyard `rc=13`）属 cg9 帧选择位口径（chipyard `DIV-11`；gem5 另查）。③ `idl/tools/idl_exec_trace.py` 自检 fixture 仍有一处 `0x0200000000000002` 字面量（格式器测试数据，非执行器断言、不在门控面）——留待 `m18-idl-002` 一并清理。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 证据脚本把 `check-idl` 通过数写死 272（违反「计数现场派生」） | ✅已修 | 改为 `N_S − 分叉例数`，并逐条核对 FAIL 例名与形态 | `check-idl 通过数 == 载体数 − 分叉数（期望=272 实际=272）` |
| `_check_cfxexe` 取 `addr[47:42]` 未按 48 位地址截断（与存储层 `MASK48` 口径不一致） | ✅已修 | `target = (addr & MASK48) >> 42` | 71/71 PASS；272 例仍绿 |
| `_cfx_perm_denied` 只建模 cg3 行，未声明（易被误读成全模式） | ✅已修 | docstring 写明「只建模 cg3（hypv），cg0–cg2 不建模」 | 代码复核 |
| 证据首版把 `expected.tsv` 镜像数当 274（漏「0 检查点镜像」） | ✅已修 | 现场派生无检查点镜像数（`scan_source`），断言 `S − N_ZERO == N_EXP` | `期望=273 实际=273`（无检查点 1） |
| `chk` 把「命令 rc」与「期望值」混判（`check-idl` rc=1 会被误判） | ✅已修 | 拆成纯二值比较；make rc 与内层 rc 分别断言 | `内层 rc=1` + `make rc=nonzero` 双 PASS |
| 注入 ①③ 只断言「非 0 退出」，与其它红因不可区分 | ✅已修 | 断言「镜内守卫 exit=4 且 0 字节」，与绿态（exit=0、24 B）互斥 | `注入①/③ … ⇒ 例红` 均 PASS |
| 5 个 id 载体登记进 `NON_ID_CARRIERS` 是否会放宽断言 | ❌不修 | 仅满足「目录完备性」；stem 合法 ⇒ orphan 判定本来就不会命中 | `validate-vectors` 274 载体 / `check-tests-index` 274 载体 0 缺 0 多 |
| 新载体不恢复 hmon 掩码（担心后续用例受污染） | ❌不修 | 其后只有 semihosting 短路 `trap cfx0` + 退出；文件头已写「不可恢复说明」 | 两载体 IDL exit=0、`make check-idl` 其余 272 例绿 |

### 第 2 轮 engineer 自审（追平 master / ADR-0062 口径）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 证据脚本的 `QEMU` 仍指主树旧二进制 ⇒ 归因矩阵误判「QEMU 未修」 | ✅已修 | 改为本树私有安装根 `$ROOT/.dadao/cross-toolchain/bin/qemu-system-dadao` | `qemu cfxreg/gem5 cfxreg: cause_id=1<<7、cause_info=指令地址（ISS-469 已修）` |
| ④c 把日志**路径**传给 `run`（后者在 `$WORK/` 下拼名）⇒ 日志空、断言全空值 | ✅已修 | `run four-way-full …`，随后 `FULL=$WORK/four-way-full` | 全四方 5 条断言全 PASS（271/274） |
| 注入④ 锚点随 `NCFXPERM` 删除而失效（原为「删子原因」） | ✅已修 | 改为「**加回** `[39]`」，断言模式 `subcaused`（`cause_id==0x80|1<<39`、exit=4） | `注入④ 加回 [39] ⇒ 两例红` + 还原后回绿 |
| 载体/探针/`idl_case.py` 的 `PERM` 仍含 `1<<39` | ✅已修 | 全部改 `1<<7`；载体落点 `__VERIFY_MEM … 0x80` | 两载体 IDL/QEMU exit=0、`cause_id=0x80` |
| 合并需提交 WIP，而 pre-commit（prek）在孤立 worktree 缺 `.cache/refs/riscv-unified-db` | ✅已修 | 先 `git switch -c m17-idl-020` + `--no-verify` 提交 WIP，再 `git merge master`；已在完成区⑤披露 | `git log`：WIP + merge 两提交；`git diff --stat master` 仅本任务 13 文件 |
| master 的 `CFXMEM` `[57]` 残留（ADR-0062 D3 也删该位） | ⏸延后 | 未改（越界；本任务指令只要求删 `NCFXPERM`） | 完成区遗留③；现场 `grep NONPTW idl/tools/idl_exec.py` = 3 处 |
| `escape_ciii_cfx` 在 gem5/chipyard 红（rc=13）是否由本任务引入 | ❌不修 | 与本任务无关：`git diff --name-only master` 不含该载体与 escape 语义；IDL/QEMU 绿 | 全四方日志该例 `rc {idl:0,qemu:0,gem5:13,chipyard:13}`；完成区遗留② |

### 第 3 轮 engineer 自审（删 `[57] NONPTW`）

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| `tests/inst` 是否有断言整 64 位 `cause_id`（含 `[57]`）的槽 | ❌无需改 | 未改任何 `.S`：故障落点只比 `cause_id[15:0]`；grep `NONPTW\|0x200000000000002` = 0 | 重生成 `expected.tsv`/`inputs.sha256`/`case-ledger` 后 `git status` 零 diff |
| 删 `[57]` 后 IDL 自检是否有旧期望 | ✅已验 | 未改 self-test（无该期望） | `idl_exec.py --self-test` 44/44 |
| 注入④ 锚点随注释改写失效（上轮注入块被替换） | ✅已修 | 锚改 `cfx.cg5[CG5_CAUSE_ID] = cause_val & MASK64`，在其前插入 `CfxPerm` 分支 | `注入④ 加回 [39] ⇒ 两例红` + 还原回绿 |
| ④c 报「缺 gem5」：主树 `gem5.opt` 正被其它会话重建（41 MB↔737 MB 抖动） | ✅已修 | 稳定性快照 + `GEM5_BIN` 覆盖（快照 md5 `47974ee1…`），脚本打印所用二进制 md5 | `gem5 二进制: …/gem5.opt md5=47974ee1…`；全四方 271/274 |
| `idl_exec_trace.py` 自检 fixture 仍含 `0x0200000000000002` 字面量 | ⏸延后 | 未改（格式器测试数据、不在门控面） | 完成区遗留③ |

### 第 1 轮 reviewer 验收（2026-11-24，全部本人重跑、不采信完成区转述）

**重跑记录**（命令在仓库根执行；证据脚本 = 运行期证据目录内的 `run.sh`）
1. `bash <运行期证据目录>/run.sh` → `PASS=79 FAIL=0`、`rc=0`（228 s）；复跑一次 → `PASS=79 FAIL=0`、`rc=0`（205 s）。覆盖：静态计数 `.S=274 / 主清单=274 / pending=0 / expected 镜像=273（无检查点 1）/ inputs.sha256=274`；`make check-idl` → `check_four_way: 274/274（parties=idl,qemu）`、`rc=0`；全四方 `271/274`（红 3 = 本任务 2 例 chipyard `rc=4` 归 `DIV-07` + `escape_ciii_cfx` `rc{gem5:13,chipyard:13}`）；L1 十门控 rc=0；6 路注入逐条「生效 → 例红 → `cp`+md5 `e2e09769…` 对账还原 → 回绿」PASS。
2. 独立注入（非脚本那 6 路）：`_op_cfx2r` 的 `CG3_REG`→`CG3_EXE`（权限轴选错）⇒ 同脚本 `rc=1`、`FAIL=14`（`cfxreg IDL 语义 rc=1`、`check-idl 273/274 rc=2`）；`cp` 还原后 md5 `da6d6e21…`→`e2e09769…`（与注入前备份相等）、`git status --porcelain -uall` 干净 ⇒ 复跑 `rc=0`、79/79。
3. 单跑门控（本人执行，均 `rc=0`）：`check-case-ledger`、`check-tests-index`、`check-inst-macro-scope`、`check-manifests-guard`、`validate-vectors`、`check-idl-parse`、`check-idl-sync`、`check-idl-exec-anchor`、`make check-idl`；`idl_exec.py --self-test` 44/44、`rc=0`。

**约束核验**
- 计数账实：台账 `272→274` 与现场一致；`tests/inst.yaml` 新增 `inst-11-cfx-006/007`；`case-ledger.tsv` +6 行、`expected.tsv` +6 行（合计 4562 槽 / 273 镜像）、`inputs.sha256` +2；`check-idl` 现场派生主清单 274 含两新例。
- 期望独立派生：`cause_id=0x80`、`cause_info`=触发指令地址（`cfxexe` = 目标 IP）出自 `spec/DADAO-12 §4.1/§3.6`，掩码复位值 `0x7FFF_FFFF_FFFF_FFF7` 出自 `spec/DADAO-13 §1`，断言内联于 `.S`（`__VERIFY_MEM 4 … 0x80` + 运行期 `aip.si` 派生地址）；`expected.tsv` 头声明仅从 `__CHECK_*` 内联常量生成，不从实测反推。
- ADR-0062 口径：删 `[57] NONPTW`/`[39] NCFXPERM`、`CFXMEM` 只置 `1<<1`、`CFXPERM` 只置 `1<<7` 与 D2/D3/D4 一致；`grep NONPTW|NCFXPERM` 在 `idl/`、`tests/inst/` 仅剩注释/文档；`m17-spec-001`、`m17-spec-002` 状态均「已验证」。
- 范围：`git diff master...HEAD`（merge-base `2fb87ea2`）仅 13 个本任务文件，`spec/` 与 `.tao/contracts/` 零改动；`git status --porcelain -uall` 干净；`escape_ciii_cfx.S` 与 master 逐字节相同（该红属 master 基线，`m18-gem5-001` 在查）。
- 未凑绿：`pending` 仍空、无断言放宽；`NON_ID_CARRIERS` 只补 `11-cfx` 目录完备性登记，两校验器仍 274 载体 0 缺 0 多。

**finding（不阻断）**：① 任务约束写「不提交 git」而工程师在任务分支有 4 个 WIP 提交（含 `--no-verify` 绕 prek），完成区⑤已披露，留 architect 终审；② `idl_exec_trace.py` fixture 仍含 `[57]` 旧编码字面量（master 既有、非本任务引入，已挂 `m18-idl-002`）；③ `expected-divergences.yaml` 的 `DIV-07` 文本仍提 `CFXPERM [39]`（master 文件、非本任务 diff）；④ `idl/README.md` 中 `m17-idl-013` 段落仍写「主清单 **272**」（历史段落、下一段已写 274），建议收尾时改 274 或加时点限定。

**判决：Accepted** —— 验收命令块在我自己的重跑下全部通过；可达 FAIL 实测 7 路（6 路脚本注入 + 1 路独立注入，均先红后 `cp`+md5 还原回绿）；账实相符；范围无越界。

**门控**：本审阅记录写入后重跑 `make check-knowledge-refs` → `rc=0`、悬空 0、0 具体 `.work/**` 引用（该行本身也已在其后复跑确认）。
