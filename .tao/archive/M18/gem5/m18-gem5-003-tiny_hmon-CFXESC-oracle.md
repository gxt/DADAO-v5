# m18-gem5-003: `check_tiny_hmon` 的 `CFXESC` oracle 从「旧 monitor 路由」改为「当前 cfx」

**模块**：gem5
**项目里程碑**：M18
**依赖**：`m18-gem5-002`（CFXESC 投当前 cfx）已合入 `bb937707`；`m18-spec-005`（R2 规格）已验证
**可并行分片**：否（单文件 oracle + 共享签名数据）
**预估**：1–2 h
**档位**：小改（复核 ≤20 min）
**状态**：已验证

## 背景（`m18-gem5-002` reviewer 实测，2026-11-25）

`tests/unit/gem5/check_tiny_hmon.py` 当前 **rc=1 / 29 FAIL**，属**基线即红**：该例的 `CFXESC` 记录按**旧 monitor 路由**写 oracle（期望进当前运行模式 monitor），而按 `spec/DADAO-12 §5.1/§5.3` 与 `m18-gem5-002` 的实现，`CFXESC` 应投**当前 cfx**（该例实际以 cfx63 运行：`imms18=1` 走 `tinyEscape`，不经 `inst.cc` fallback）。

已证：`git archive HEAD` 基线树与修复后树的 29 条 FAIL **逐行相同**（md5 同 `bfcd47e6…`）⇒ 与 `m18-gem5-002` 无关，是 oracle 自身陈旧。

## 目标

1. **按 spec 重写 oracle**：`CFXESC`（escape 帧/目标错误）期望改为「投递到**当前 cfx**（本例 cfx63），monitor 不被写」；期望值必须从 `spec/DADAO-12 §5.1/§5.3`（及 `Kaiwu §7.1` 的停机码段规则）**独立派生**，不得从 gem5 实测反推。
2. 若该例还断言了 monitor 侧的记录（cause_ip/cause_info/段），一并改为「monitor 无写入」的**反向断言**。
3. 不得为过门控而放宽其它断言；修改后逐条给证据。

## 验收（逐条贴真实 rc）

1. `python3 tests/unit/gem5/check_tiny_hmon.py` **rc=0**（0 FAIL）；改动前后 FAIL 集对比表（29 → 0）并说明每条的归因。
2. **可达 FAIL ≥2 路**：① 把期望改回「进 monitor」⇒ 红；② 把「monitor 无写入」反向断言删掉 ⇒ 红（或注入一次 monitor 写）；均 `cp`+md5 还原。
3. 期望的 spec 派生链写进任务书（引原文位置），reviewer 可独立复算。
4. 相关门控：`check-gem5-decode`、`check-patch-tree`（gem5 段）、`check-tests-index`、`check-knowledge-refs` 真 rc；若 `check-patch-tree` 总 rc 受他人 linux/musl 基线影响，按「gem5 段 0 problem」口径并披露。
5. 若同步了 `tests/data/inst-signature/**` 或 `case-ledger.tsv`，须由生成器产出（`inst-signature-data` / 对应生成器），禁手改。

## 约束

独立 `git worktree`（分支 = `m18-gem5-003`）；不提交 git；只改 `tests/unit/gem5/**`（及必要生成物）与本任务书；**不改 `components/**`、`spec/`、契约、`Makefile`**；术语「寄存器组」；完成区不写具体 `.work/**` 路径。

## 期望值派生链（spec 原文，禁从 gem5 实测反推）

**A. `CFXESC` 的交付目标 = 当前 cfx（本例 = cfx63）**

- `spec/DADAO-12:878`（§5.1）：`escape` 的 `cfxha` 必须是**当前执行的 cfx**；所选 `cg5` 帧无效（`excp_cause_id = 0`）时，**在切换任何状态前触发当前 cfx 的 `CFXESC`**。
- `spec/DADAO-12:910`（§5.2(一) 末行）：`escape` 帧错误或目标错误 → `CFXESC` → **当前核芯功能扩展（不属于 monitor 路由）**；`spec/DADAO-12:1019`（§5.3 step 0）同口径；`spec/Kaiwu:495`（§7.1）另规定该编码走「其它 cfx」段（`0x80–0xBF`），同样不是 monitor 段。
- **当前 cfx = 63**：power(cfx63) 的 `trap cfx_hmon` 进 cfx3 时按 §5.2(三) step 4 保存 `excp_prev_cfx_code = 63`，hmon 的 `escape` 按 §5.3 step 1 恢复它 ⇒ 应用体 current cfx = 63。故 `f_esc` 的 `escape cfx_power(63)` **目标合法**；失败点是**帧无效**——此前没有任何异常投递到 cfx63（5 类同步异常与 `trap cfx_hmon` 都按 §5.2(一) 进当前 monitor），cfx63 的 `cg5 excp_cause_id` 保持初值 0（§3.6 cg5 表）。

**B. 记录 34 四个字（cfx63 自己的 cg5）**

| 字段 | 期望 | 派生 |
| --- | --- | --- |
| `cause_id` | `0x8` | `1 << 3`（§5.2(二)；§3.6(一)） |
| `cause_ip` | `f_esc` | §5.2(三) step 4：同步异常的 `cause_ip` = 触发指令地址 |
| `cause_info` | `0x7EFC0001` | §4.1 异常表 `CFXESC` 的 info = **指令编码**；编码按 ciii（`SimRISC-00:239`：cfxha 在 `hb[5:0]`+…，opc `0111-1110` = `0x7E`，`SimRISC-11 §3`）；`cfxha[23:18]=63`，`imms18[17:0] = imms20>>2 = 4>>2 = 1`（§5.1：`imms20=4` ⇒ cg5 帧、字节偏移 +4）⇒ `0x7E000000 \| 63<<18 \| 1` |
| `prev_cfx_code` | `63` | §5.2(三) step 4：异常**前**的 `inner_cfx_code`（第 5 步才改写） |

**C. 反向断言「monitor 无写入」**

- hmon SRAM `0xE0/0xE8/0xF0` 只由 hmon handler 写（`Kaiwu §6.2` + m13-integ-007 最小 handler 布局），`0xF8` 由框架写。`CFXESC` 不进 monitor ⇒ 三槽仍是**上一次 monitor 记录**：记录 32 的 `trap cfx_hmon, 0x123` ⇒ `cause_id = 1`（§5.2(一) 合法 trap → CFXTRAP）、`cause_ip = f_trap`、`cause_info = 0x7F<<24 \| 3<<18 \| 0x123`（§4.1 trap info = 指令编码）；`0xF8 = land_esc`（框架值未被覆盖）。
- 计数侧同断言：hmon 的 `excp_sync_num`（§5.2(三) step 3：非 trap 同步异常计数）= **15**（此前 5 类 × 3 例全部进当前 monitor），`CFXESC` 不增加。

**D. `CFXPERM`（记录 37，原用例前提错误故一并改正）**

- 旧用例用 `trap cfx_power`（源 = 目标 = cfx63）+ 写 cfx63 自己的 mask：§3.4 rc0 明确「位索引=源 cfx；**自身对应位忽略**」⇒ 不可能产生 `CFXPERM`（会变成进 cfx63 的 `CFXTRAP`）。
- 改正：在 **hmon 的 hypv cfxtrap**（cg3 rc0）里屏蔽源 cfx63（`bit63=1`，§3.4：0=允许/1=屏蔽，位索引=源 cfxha），再 `trap cfx_hmon, 0` ⇒ `CFXPERM` 进当前运行模式 monitor（§5.2(一)；Tiny 恒 hypv ⇒ cfx3，`Kaiwu §2`）。`cause_info` = 触发指令地址 = `cause_ip`（§3.6(六)）；`return_slot = land_perm`（框架写 `0xF8`）。用完立即恢复 mask。

## FAIL 归因表（改动前 29 FAIL → 改动后 0）

| 旧 FAIL 项 | 条数 | 归因 |
| --- | --- | --- |
| record 34 `cause` / `cause_ip` / `cause_info` | 3 | oracle 写成「CFXESC 进 hmon」；实际按 §5.2(一) 投当前 cfx（cfx63）、hmon handler 未运行 ⇒ 三槽仍是上一次 monitor 记录 |
| record 6 `check 6`（hmon `trap_num`，期望 1 实测 5） | 1 | 旧用例没给 cfx63 装 hypv 向量（平台初值 = BootROM 基址，§3.4 rc10）⇒ CFXESC 进入后机器从复位重来，每次重启都重放 power→hmon 移交 `trap`，`trap_num` 被累加（实测 5） |
| `gem5 guest exit`（0x21 → 0x71） | 1 | 上一条在 guest 侧的同一失配（failcnt>0 ⇒ 0x71） |
| `record count`（旧 oracle 期望 43 / 实测 42） | 1 | 旧 `f_perm` 的 self-trap 前提无效（§3.4 自身位忽略）⇒ 变成进 cfx63 的 `CFXTRAP` 并改写 cfx63 帧；下一趟 `f_esc` 的 escape 因此「成功」并跳到旧 `excp_cause_ip+4`（= `land_perm`），跳过 `land_esc` 落点记录 ⇒ 少 1 条 |
| record 35–41 的逐字比对 | 23 | 纯位置错行（少一条记录后整体前移一行），值本身未变 |

29 = 3 + 1 + 1 + 1 + 23（逐行取自改动前日志；`29/201 FAIL`）。

**机制复现（受控诊断，非交付改动）**：在修复后的用例上临时删掉「安装 cfx63 hypv 向量」3 行（其余不变）⇒ `record 6`（`trap_num`）实测 **3**、记录数 **43 ≠ 45**、guest 退出 `0x71`；`cp`+md5 还原（`c1094558…`）后重跑回到 213 checks / 45 records / rc=0。据此确认「CFXESC 投 cfx63 + 未装向量 ⇒ 按平台初值回 BootROM ⇒ 重启并重放移交 trap」这一机制；原用例的 `trap_num = 5` 还叠加了旧 `f_perm` self-trap 路径的额外重启。

## 完成区

**测试结果**：`python3 tests/unit/gem5/check_tiny_hmon.py` **rc=0 / 213 checks / 45 records / 0 FAIL**（改动前 rc=1、29 FAIL / 201 checks）。证据脚本（运行期证据目录 `run.sh`）**60/60 PASS rc=0**；`--inject` 三路各自「注入→红→`cp`+md5 还原→绿」：① oracle 期望改回「进 monitor」⇒ `record 35 monitor untouched: still CFXTRAP: expected=0x8 actual=0x1`（rc=1）；② 删掉 app 侧反向断言记录 ⇒ `record count: expected=45 actual=44`（rc=1）；③ 注入一次 monitor 写（改 `0xF0`）⇒ `record 35 monitor untouched cause_info: expected=0x7f0c0123 actual=0x0`（rc=1）；三路还原后 md5 与备份逐字节相同并回绿。

**修改文件**：`tests/unit/gem5/tiny_hmon/tiny_hmon.S`、`tests/unit/gem5/tiny_hmon/expected.yaml`、`tests/unit/gem5/check_tiny_hmon.py`、`tests/unit/gem5/tiny_hmon/README.md`、本任务书。未改 `components/**`/`spec/`/契约/`Makefile`；无签名数据/台账生成物。

**验收结果**：`check-gem5-decode` **rc=0**（positive 263/263、negative 391/391、legality 28/28、legacy 2/2）；`check-tests-index` **rc=0**（PASS 502 条）；`check-patch-tree` gem5 段 **106 patch(es) / 0 assertion**（总 rc=1，12 problem（chipyard 6 + linux 4 + musl 2，均非 gem5 段） 他方基线，已披露）；`check-knowledge-refs` **rc=1（已知基线）**：唯一悬空 `.tao/knowledge/milestones-m17.md:36 ADR-0063`（属 `m17-spec-004`，本任务未触碰该文件，日志无 `tiny_hmon`/`gem5/tiny` 命中）。长命令全部 `setsid nohup` + 日志 + `*_EXIT`。

**新发现/坑**：① 「CFXESC 投当前 cfx」在本例的落地需要**初始化 cfx63 自己的 hypv 向量**（`cg3 rc10`，§3.4 初值由平台定义 = BootROM 基址），否则 CFXESC 进入后从复位重来（旧 29 FAIL 的 `trap_num=5` 即此），而 `expected.yaml` 无法自行表达该前置；② `cfx2rc` 的操作数在 **rd** 组，符号地址须 `LOAD_ABS rb5` + `rb2rd rd10, rb5, 1` 再写（`set.rd`/`cfx2rc` 都装不下 section-relative 标签）；③ `CFXPERM` 不能由 self-trap 产生（§3.4 自身位忽略），须屏蔽**目标** cfx 的 mask 且源 ≠ 目标；④ 驱动按 `kind` 分派后对未知 `kind` 显式失败（不再落入 `cause` 分支）；⑤ 证据脚本内 `REPO` 须按 `..` 词法上溯解析（`run.sh` 所在的运行期目录经符号链接接入共享构建树，`git rev-parse --show-toplevel` 会指到共享树），且跑例前必须 `cd` 到仓库根（固件源用仓库相对 include）。

**遗留问题**：1. `check-knowledge-refs` 的 `milestones-m17.md:36 ADR-0063` 悬空属 `m17-spec-004` 面（与本任务无关，未修）；2. `check-patch-tree` 总 rc 仍受 linux（4）/musl（2）基线影响（未修）；3. 本用例只覆盖 `escape` **帧无效**路径；**目标错误**（`escape` 到非当前 cfx）由 `m18-gem5-002` 的探针覆盖，若要并入本 unit 用例需另立任务。

## 审阅记录

### 第 1 轮 engineer 自审（自主逐行）

- `tiny_hmon.S`：`f_esc` 前只用 cfx2rc 改 cfx63 的 `cg3 rc10`（§3.4 自身轴不查 mask）；`esc_land` 位于 `.rcheck`（SRAM 段内、非线性流），记录 cfx63 `cg5 rc2/rc3/rc4/rc1` 后 `escape cfx_power, [excp_cause_ip, 4]` 按 §5.3 回 `f_esc+4`；`record_cause` 路径、0xF8 语义、其它 5 类异常与 check 1–16/36/38–42 逐行未动；`f_perm` 改为屏蔽 **hmon** 的 cfxtrap bit63 并 `trap cfx_hmon`，`land_perm` 后立即恢复（此后所有 semihosting `trap cfx_hmon` 不受影响）。
- `expected.yaml`：新增 `cfx_cause` 与 `monitor_unchanged` 两类记录，注释写明 spec 行号与编码位段；record 32/37 的 info 口径按 §4.1/§3.6(六) 复核（CFXPERM 由指令编码改为地址）。
- `check_tiny_hmon.py`：`kind` 分派改为显式四支 + 未知支 FAIL（不再 `else` 兜底当 `cause`）；`cfx_cause`/`monitor_unchanged` 各自 4 字段逐字比；dump 段「last fault」仍取 `kind == cause and ip == f_hypv`，未受新 kind 影响；未改任何 CLI/签名。
- 防造假：三路注入均 `cp` 备份 + `md5sum` 对账（备份/注入后/还原后逐次打印），还原后重跑 `check_tiny_hmon` 回 213/45 绿；`run.sh` 无 `| tee`，rc 取被检命令自身。

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| oracle 把 CFXESC 记为「进 hmon」（与 §5.2(一) 相反） | ✅已修 | record 34 改 `cfx_cause`（读 cfx63 cg5）；新增 monitor 反向断言记录 | 注入 ① 回红、还原回绿 |
| 用例未装 cfx63 向量 ⇒ CFXESC 后复位重来（trap_num 累加） | ✅已修 | 写 `cfx_power cg3 rc10 = esc_land` + `esc_land` 落点 | `record 6` 现值 1；45 条 records 顺序稳定 |
| `f_perm` 用 self-trap 期望 CFXPERM（§3.4 自身位忽略 ⇒ 永不成立） | ✅已修 | 改屏蔽 hmon 的 cfxtrap bit63 + `trap cfx_hmon`，用完恢复 | 记录 37 `0x80 / f_perm / f_perm / land_perm` 全 PASS |
| 旧 oracle 期望 43 / 实测 42（少一条落点记录） | ✅已修 | 同第 2 行（不再有「旧帧把 escape 导向 land_perm」的错位） | 记录数 45/45 PASS |
| 驱动 `else` 兜底把未知 `kind` 当 `cause` 比 | ✅已修 | 显式四支 + 未知 kind 报 FAIL | `grep` 全文件仅 4 个已知 kind；跑例 PASS |
| 证据脚本 `REPO` 指向共享构建树、跑例 cwd 非仓库根 | ✅已修 | `..` 词法上溯 + `cd "$REPO"` + 锚点 count 断言 | 首轮失败日志 → 修正后 60/60 PASS |

### 第 1 轮 reviewer 验收（2026-11-25）

**独立复算（只读 spec，不采信 gem5 实测）**：`cfx_cause` 四字段我自己推出——`cause_id = 1<<3 = 0x8`（DADAO-12 §5.2(二)；§4.12 cfx_power 异常原因表 `1<<3`=CFXESC，info=指令编码）；`cause_ip = f_esc`（§5.2(三) step4「触发指令地址」）；`cause_info = 0x7E<<24 | 63<<18 | 1 = 0x7EFC0001`（SimRISC-00 §4 主表 `0111-1110` = `escape_ciii_cfx` ⇒ opc `0x7E`；`ciii` 的 cfxha 在 `ha[5:0]`=[23:18]=63、18 位立即数在 [17:0]；`imms18 = imms20>>2 = 4>>2 = 1`，DADAO-12 §5.1 / SimRISC-11 §2）；`prev_cfx = 63`（§5.3 step1 自 `cg5 rc1` 恢复、§5.2(三) step4 存异常前 `inner_cfx_code`）。四值与 `expected.yaml` **逐字相同**，派生链无 gem5 反推痕迹。`monitor_unchanged` 亦独立推出：0xE0/0xE8/0xF0 只由 hmon handler 写、0xF8 由框架写（`tests/ee-tiny/cfx_hmon_tiny.S`），而 CFXESC 非 monitor 路由（§5.2(一) 末行；Kaiwu §1.2「CFXTRAP/CFXESC 除外」、§7.1 按「其它 cfx」段编码）⇒ 三槽仍是 record 32 的 CFXTRAP 帧 `0x1 / f_trap / (0x7F<<24)|(3<<18)|0x123`、`0xF8 = land_esc`；`excp_sync_num = 15` = CFXMEM/ILLI/UNDI/MALIGN/IALIGN 各 3 例（§5.2(一) + §5.2(三) step3，CFXTRAP/CFXPERM 不计入）。

**重跑（我自己的终端输出）**：① `python3 tests/unit/gem5/check_tiny_hmon.py` ⇒ **rc=0**，尾行 `check_tiny_hmon: PASS (213 checks, 45 records)`，`[FAIL]` 行数 **0**；关键行 `record 34 …0x8 / 0xffffff0104cc / 0x7efc0001 / 0x3f`、`record 35 monitor untouched … 0x1 / 0x7f0c0123`、`record 36 check 43 … 0xf`、`record 37 CFXPERM … ip == info == 0xffffff010500`。② 运行期证据目录的 `run.sh`（全量）⇒ **rc=0**、`== result: 60/60 checks passed ==`，base rc=0、三路注入各自「注入 → rc=1 → `cp`+md5 与备份相等 → 还原回绿」（A `876cf2be…`，B1/B2 `c1094558…`）。③ **我自己的独立注入**（engineer 三路之外，打 `cfx_cause` 字段）：`cp`+md5 备份后把 `info` 的 `|1` 改 `|2` ⇒ 同一脚本 **rc=1**、用例日志恰 1 条 `[FAIL] record 34 cfx cause_info: expected=0x7efc0002 actual=0x7efc0001`（另三字段仍 PASS ⇒ 四字段均可达 FAIL、非恒真）；`cp` 还原 md5 `876cf2be…` 与注入前相同 ⇒ **rc=0 / 27/27** 回绿。

**门控（我重跑）**：`check-gem5-decode` **rc=0**（`positive 263/263, negative 391/391, legality 28/28, legacy 2/2, failures 0`）；`check-tests-index` **rc=0**（`结果: PASS（502 条…）`）；`check-patch-tree` 总 **rc=1**，`check-patch-tree: gem5: 106 patch(es)` 且日志无 `gem5: assertion` 行 ⇒ **gem5 段 0 problem**（实测 12 problem：chipyard 6 / linux 4 / musl 2，均他方基线）；`check-knowledge-refs` **rc=1**，唯一悬空 `milestones-m17.md:36 ADR-0063`（目标文件不存在；m18-gem5-002、m17-idl-021 记录同指 m17-spec-004 面，本任务未触碰该文件），日志无 `tiny_hmon`/`gem5/tiny` 命中。

**数字核**：`29 = 3+1+1+1+23` 我按两份独立日志复算成立（m18-gem5-002 的 `tiny-hmon.log` 与本任务 `base.log` 的 29 条 FAIL 行 `diff` **逐字节相同**）；`201 → 213` = 记录类报告 169 → 181（已检记录 42 → 45，+3×4），非记录检查两侧均 32 ⇒ 自洽；`43 → 45`（+`monitor_unchanged`、+`check 43`）。**采信未重跑**：改动前 rc=1/29（历史运行，我只做了日志交叉核对，未重放基线树）。

**约束核验**：`git diff --name-only` 仅 `tests/unit/gem5/**` 4 文件 + 本任务书（无 `spec/`、`components/**`、契约、`Makefile`、签名数据、台账）；注入备份已删、无 `.bak/.preinject` 残留；验收前后 `md5` 快照逐项相同（`0584baf0 / 876cf2be / c1094558 / 92bf2997 / b9870b14`）；未提交 git。**机制**：`cg3 rc10` 装 `esc_land` 是 §3.4 向量前置（cfx_power 无内部 SRAM、初值即复位向量），`esc_land` 读 cfx63 自己 `cg5 rc2/rc3/rc4/rc1`（与 §3.6 表位一致）再 `escape cfx_power, [excp_cause_ip, 4]` 按 §5.3 step1/2 回 `f_esc+4 = land_esc`——观测点就是被测投递路径本身，无绕过；`f_perm` 前提成立（§3.4「自身对应位忽略」⇒ self-trap 不可能 CFXPERM），改屏蔽 hmon hypv `cfxtrap` bit63 后 `trap cfx_hmon, 0` ⇒ §5.2 伪代码 CFXPERM → 当前运行模式 monitor，`cause_info = cause_ip` 合 §3.6(六)/§4.1；屏蔽窗内只有这一条 trap，§5.3 的 `escape` 不查来源 mask，用完立即恢复，未掩盖其它失败。

**findings（不阻断，交 architect 收尾改）**：① 完成区/遗留写「`check-patch-tree` 12 problem（chipyard 6 + linux 4 + musl 2，均非 gem5 段）」，我实测 **12 problem（chipyard 6 + linux 4 + musl 2）**——判据「gem5 段 0 problem」成立，属披露数字笔误（也可能他方在途窗口变化），改披露行即可；② `run.sh` 的 `problems attributed to gem5` 断言（`problem.*: gem5`）对实际行形恒真，真正兜底是已存在的 `^check-patch-tree: gem5: assertion` = 0（可达 FAIL），建议后续删掉恒真那条；③ 完成区写 `check-knowledge-refs` rc=1 是**直跑脚本**的码，我复测脚本 rc=1、而 `make check-knowledge-refs` 因配方失败由 make 归一为 **rc=2**（同一 1 条悬空，写入本记录前后均 `悬空: 1`、无 `tiny_hmon` 命中）——建议披露行注明两种码。

**判决：Accepted**——验收命令在我自己的重跑下全绿、期望值经 spec 独立复算逐字一致、四路注入（engineer 3 + 我 1）均真红并 `cp`+md5 还原回绿、范围与快照无越界。
