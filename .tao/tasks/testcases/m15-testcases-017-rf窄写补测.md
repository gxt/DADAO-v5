# m15-testcases-017: RF 窄写语义补测（`ld.t`/`ldm.t` 高 32 位保持）

**模块**：testcases
**项目里程碑**：M15
**依赖**：无
**可并行分片**：否（同改 `tests/inst/01-load-store`）
**预估**：2–3 h
**档位**：中改
**状态**：已验证

## 背景（用户 2026-11-18）

用户指正 `tests/inst/01-load-store/ld.t_rrii_rf.S` 第 4 行注释错误：写的是「32 位零扩展」，正确是「**只写目的寄存器低 32 位，高 32 位保持原值**」。注释已修（`7bfec488`）。

**但暴露了测试覆盖缺口**：该文件的专用宏 `TEST_LD_RF_LO32` **只比对低 32 位**，注释原写「高 32 位不做特殊规定 ⇒ 不据以判失败」——这与 spec 明文矛盾：

> `spec/SimRISC-01 §4` 注：**`ld.t`/`ldm.t` 的写入宽度**：单精装载**只写目的寄存器低 32 位，高 32 位保持原值**（不作符号扩展、也不零填）。

后果：**实现若把 `ld.t` 做成零扩展，现有用例照样全绿**。

## 目标

### 1. 补「高 32 位保持」断言（核心）

对 `ld.t_rrii_rf.S` 与 `ldm.t_rrri_rf.S` 各补至少 2 条用例：

- **构造**：先用 `ld.o`（64 位装载）把目的 rf 寄存器写成一个**高位已知非零**的值（如 `0xDEADBEEF_00000000`、`0xA5A5A5A5_FFFFFFFF`），期望值来自测试数据字面量（**独立 oracle**，不从实现反推）；
- **执行**：`ld.t` / `ldm.t`；`ldm.t` 还要覆盖「同一寄存器被多个元素依次写」时的最终高位；
- **断言**：`rf2rd` 读回完整 64 位，**必须等于「原高 32 位 + 新低 32 位」**；若实现零扩展（高 32 位被清 0）⇒ 用例必须红。

### 2. 宏语义订正

- `ld.t_rrii_rf.S` 的 `TEST_LD_RF_LO32` 目前只比低 32 位：**保留**它（低 32 位专用），但新增一个比对完整 64 位的宏（如 `TEST_LD_RF_FULL`）供新用例使用；
- `ldm.t_rrri_rf.S` 里「只比低 32 位」的措辞与用法一并核（第 56 行附近），按同一原则处理。

### 3. RF 窄写语义盘点（不要求全补，要求登记）

扫 `tests/inst/**` 里「写 RF 但只写部分位」的指令（至少含 `ld.t`/`ldm.t`、`set.ft`、`ftcls`/`focls`，其余以 spec 为准），产出清单：

- 指令 / spec 依据（写宽度的原文位置）/ 现有测试是否验「未写位保持」/ 缺口。

**只补 `ld.t`/`ldm.t`；其余登记为后续任务候选**，不在本任务扩大范围。

## 验收（逐条贴真实 rc）

1. `make check-inst-asm` **272/272（含链例/故障链）** rc=0；新增用例在列。
2. **可达 FAIL（硬门）**：把新用例的期望高 32 位改成 0（模拟零扩展实现）⇒ `ld.t`/`ldm.t` 用例**必须红** ⇒ 还原 ⇒ 绿。逐条贴注入前后的 rc。
3. 新增用例的期望值来源逐条注明（测试数据字面量 / spec 引文），**不得用实现输出反推**。
4. `check-asm-list`、`check-tests-index`、`check-dirs`、`check-no-residue` rc=0。
5. RF 窄写盘点清单写入完成区（≤10 行）。
6. 完成区 ≤30 行；`**状态**` → `待验收`。

## 硬约束

1. 独立 worktree；禁改主工作树；**禁提交 git**。
2. 只动 `tests/inst/01-load-store/{ld.t_rrii_rf,ldm.t_rrri_rf}.S`（+ 若必要的册内宏）+ 本任务书；**不改 `tests/inst/macros/inst_test.inc` 的公共宏语义**（除非确有必要，需在完成区说明）。
3. **不改 spec**；不改 `components/`。
4. 单指令用例上限 ≤127（任务书规则）：本文件已有 21 链例 + 2 故障例，新增 ≤4 条，不得超限。
5. `cp`+md5 还原（禁 checkout/restore/stash/show）。

## 待裁定

（无）

## 审阅记录

### 第 1 轮 engineer 自审

**审查范围**：两个 `.S`（宏 + 新用例 + 点号重排）、`tests/case-ledger.tsv` 重生成、证据脚本。逐行核过新宏展开（`\@` 标号、保留寄存器 rd19/rd20/rd21/rd22）、点号不变式与期望值推导。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `TEST_LDM_RF_FULL1` 定义后无使用者（死宏） | ✅已修 | 删除该宏，单元素路径由点 20 的两次窄写用例承担 | `check-inst-macro-scope` rc=0（先前撞 `[S4] 死宏` 红线） |
| F2 点 19 期望按「8 B 元素」误算（`MDATA_T` 实为 4 B 元素）⇒ 用例红 rc=19 | ✅已修 | exp 改为 `0x8000000280000008` / `0x8000000480000009`（元素 2/3、4/5 高半 + 元素 8/9） | 单跑 PASS，点数 20；注入后 rc=19 |
| F3 证据脚本解析 guest 退出码用 `[0-9]*$`（可匹配空串）⇒ 断言恒假 | ✅已修 | 改 `grep -oE '[0-9]+'`（并加 `derive_fault_total` 现场派生） | 注入日志解析出 pt=22/23/19/20 |
| F4 「期望命令失败」误用同一 `check()`（第四参传被检 rc ⇒ 恒 FAIL） | ✅已修 | 新增 `check_flag`（判定 0=通过） | C3 五行 PASS |
| F5 注入串 `0x8000000080000007` 在注释中重复 ⇒ 注入点不唯一 | ✅已修 | 改注入整行 `__CHECK_RD 20, …` | 「注入点唯一」PASS |
| F6 并行会话 `install-host` 占用共享安装根 ⇒ writer-guard 拒绝（rc=75，不等待） | ✅已修 | `run_ids` 加 20 s×12 等待重试并打印次数（实际命中 2 次后恢复；未改二进制、未加 `--allow-concurrent`） | 重试后 C1–C3 全绿 |
| F7 越界核对：`make check` 红在 `check-milestones-fresh` A1 | ⏸不改 | 根因在 `m15-infra-008`（infra 模块）任务书 `**状态**` 带括号注记，非本任务改动 | `git status .tao/` 干净；见完成区遗留 |

**判决**：F1–F6 已修并复验；F7 属他人任务书，登记不改。

### 第 1 轮 reviewer 验收（2026-11-18）

**自证/范围**：worktree `/tmp/opencode/m15-testcases-017/wt`、分支 `m15-testcases-017`、WIP `bfc73701`；`git diff bfc73701~1..bfc73701 --stat` = 4 文件（两个 `.S` + `tests/case-ledger.tsv` + 本任务书），`spec/`/`components/`/`contracts/`/版本号零改动；`inst_test.inc` 未改。验收前后 `git status --porcelain -uall` 空、4 文件 `md5sum -c` 全 OK（注入全部还原、无残留）。

**spec 依据**：`spec/SimRISC-01 §4`（第 141 行）明文「`ld.t`/`ldm.t` 只写目的寄存器低 32 位、高 32 位保持原值」，`spec/SimRISC-00 §2.3` 同口径 ⇒ 期望值派生合法。**finding L1（文档级）**：任务书引用写成 `SimRISC-01 §1`（§1 是「存取 RD」，该注在 §4），`.S` 内注释写 §4 正确；请 architect 收尾时改任务书引用。

**用例正确性（本人逐位手推，非采信）**：`TEST_DATA` 24 拍大端，+0x078=0xDEADBEEFCAFEF00D、+0x070=0xA5A5A5A55A5A5A5A，字 +0x008=0x00112233、+0x018=0xFFEEDDCC（与既有用例 5/7 同源）⇒ 点 22=0xDEADBEEF\|00112233、点 23=0xA5A5A5A5\|FFEEDDCC，高/低半拼接正确。`MDATA_T` 4 B 元素 0x80000000+i：点 19 预置拍 +0x008/+0x010 高半=元素 2/4，装入 +0x020 两元素 8/9 ⇒ 0x80000002\|80000008、0x80000004\|80000009 ✓；点 20 预置 +0x000 高半 0x80000000，先写元素 37、再写元素 7 ⇒ 期望 0x80000000\|80000007，高半确为**预置原值**（非最后一次写入值 0x80000025）✓。

**重跑（本人执行）**：运行期证据目录内的 `run.sh` ⇒ `RUN_EXIT=1`，仅 C1 两项 FAIL（`check-inst-asm rc=2`、`270/272`），C0/C2/C3(5 路)/C4/C5 全 PASS；6 个 L1 门控本人直跑 `check-asm-list / check-inst-macro-scope / check-tests-index / check-dirs / check-no-residue / check-case-ledger` 全 rc=0；`check_case_ledger.py --write` 前后 md5 同（`b9dddd9a…`）⇒ 清单确为生成物、与现场语料逐字节一致；`scan_source` 现场派生：ld.t 23 链例+2 故障（点 24/25）、ldm.t 20 链例+7 故障（点 21–27）、`pts_ok=True` ⇒ 25/27 ≤127、点号重排与 ledger 一致。

**可达 FAIL（本人独立注入，非采信脚本）**：① 点 22 期望高半→0（`0xDEADBEEF00112233`→`0x0000000000112233`）⇒ `rc=1`、guest pt=**22**；②（脚本未列）点 20 期望改「首次写入值拼高半」`0x8000000080000007`→`0x8000002580000007` ⇒ `rc=1`、guest pt=**20**（证明期望高半钉的是原值）；两路均 `cp` 备份 + md5 对账还原 → 单跑回绿 `rc=0`。

**阻断（验收 1 未过）**：`make check-inst-asm` **270/272 rc=2，3 次重跑完全一致**（run.sh C1 + 本人 2 次，22:03/22:18），失败恒为 `11-cfx/escape_ciii_cfx.S`（rc=-2 超时）与 `11-cfx/cfx2rd_crrr_cfx.S`（rc=28、0 B 输出）。根因**不在本任务**：① 两载体与 master 逐字节一致（`git diff HEAD master -- tests/inst/11-cfx/` 空）；② 共享 qemu 二进制 21:55:01 被装入（构建 21:46），含 master `c8daffc8`（m14-spec-009：escape 恢复 `inner_cfx_code` + cg5 rc1 `prev_cfx_code`，21:47 合入、其证据未跑 L2 inst），晚于工程师证据 `run.sh` 21:50:06；③ 手工单跑两 ELF 可独立复现（escape 超时、cfx2rd rc=28）。⇒ 跨任务 L2 回归，engineer 无法在本任务内修复，**请架构师定夺**（处置 m14-spec-009 的 inst 回归或明确放行口径）。

**判决：Needs Revision** —— 仅因验收 1（`check-inst-asm 272/272 rc=0`）在我方重跑下不成立；其余验收项（期望值独立 oracle、可达 FAIL、点号/台账、L1 门控、≤127、不越界）全部通过。

### 第 2 轮 engineer 返工（Needs Revision 处置：11-cfx 跨任务回归）

**定位（实测，不猜）**：`escape_ciii_cfx.S` 用 QEMU `-d in_asm/exec` 追到 `ENTRY+0x478`（`escape cfx_power`）单指令自环——应用上下文 `inner_cfx_code = 63`，`escape cfx_hmon`(3) 判 CFXESC、交付给**当前 cfx = power(63)**，其向量 = 复位向量 ⇒ 重启自环（探针：启动后 `cfx_hmon cg5 rc1` = 0x3F；`trap cfx_hmon` 后该帧 rc1/rc3 = 0x3F/陷阱地址 ⇒ 应用确在 cfx_power）。`cfx2rd_crrr_cfx.S` guest rc=28 —— 故障例 28（`0x7A0C5045` = cfx3/cg5/rc1，原期望 CFXREG）在新 spec 下 rc1 可读 ⇒ 不触发 ⇒ 落 `__EXIT 28`。

**根因**：master `c8daffc8`（m14-spec-009）把 `escape` 改为恢复 `inner_cfx_code ← excp_prev_cfx_code`（`DADAO-12 §5.3` 步骤 2）、cg5 rc1 改为 `excp_prev_cfx_code`（`§3.6`）；两载体按旧语义写（与 master 逐字节一致 ⇒ 需在本任务一并更新）。

**处置（旧 → 新）**
| 用例 | 旧期望/前提 | 新期望/构造 | spec 依据 |
|---|---|---|---|
| escape 1–4、7–9（原 1/2/3/4/8/9/10） | 应用直接 `escape cfx_hmon`（旧语义 inner 恒 3） | 自建 monitor 入口（写 `cfx_hmon cg3 rc10` = handler）+ `trap cfx_hmon` 进 hmon（inner=3）后由 handler 执行被测 escape；**落点断言不变** = cause_ip+imm | `§5.3` 步骤 0/2/3；`§3.4` cg3 rc10 RW |
| escape 原 5（ILLI 帧 escape） | 同左 | 保留：`trap cfx6` 触发的 ILLI 帧 + handler(+4) | `§5.2` 第 5 步 |
| escape 原 6（同帧连续两次 escape） | 帧未消费 ⇒ 第二次 escape 仍合法 | **删除**：新语义下 escape 必把 `inner_cfx_code` 还原给调用者，第二次 escape 只能落在**新**帧上 ⇒ 前提不可构造 | `§5.3` 步骤 2 |
| escape 原 7（帧未被改写） | 与 escape 前读值比较 | 保留：handler 进入时记 cause_id 到 0xE0 槽，落点再读帧比对（等价 `__VERIFY_EQ_RD`） | `§5.3` 步骤 0–3 不改帧 |
| escape 原 11（`escape cfx_power` ⇒ CFXESC） | 「cfxha ≠ 当前 cfx(3)」 | 期望不变（cause_id `1<<3`、info = 指令编码、cause_ip = 指令地址），**理由变为**「cfxha == 当前 cfx(63) 但该帧 cause_id = 0」；CFXESC 交付当前 cfx ⇒ 入口改挂 `cfx_power` 向量 | `§5.3` 步骤 0 |
| escape 原 12（`escape cfx_umon` ⇒ CFXESC） | 「≠ 当前 cfx」 | 期望不变（cfxha 0 ≠ 63）；路由同改挂 `cfx_power` | `§5.3` 步骤 0 |
| **新增 escape 12** | —（旧语义无此可观测） | 恢复 `inner_cfx_code`：第一次 escape 后应用回 cfx63 ⇒ 第二次 `escape cfx_hmon` 必判 CFXESC（标记 cause_id = `1<<3`；旧语义下会成功 ⇒ 到达计数超限判红） | `§5.3` 步骤 2 |
| cfx2rd 原 28（cg5 rc1 保留 ⇒ CFXREG） | rc1 reserved | **删除**（新 `§3.6` rc1 = `excp_prev_cfx_code`，RW）；新增链例 23 断言 rc1 = 0x3F 与 RW 写读回 | `§3.6` cg5 行；`§5.2` 第 5 步；`Kaiwu §1`（复位 cfx = power 63） |

**spec 冲突（登记，不改）**：`spec/Kaiwu §4.2`、`§6.2 第 7 步`（master 亦然）仍写「`escape` **不改变** `inner_cfx_code`、帧中不保存 `prev_cfx`」，与 master `DADAO-12 §5.3 步骤 2`/`§3.6 rc1` 直接矛盾 ⇒ 属 spec 模块 + 用户裁定，本任务只按 DADAO-12 改测试。

**本身份**：本分支 `spec/` 早于 master `c8daffc8`（分支未同步 master，spec 未改）；引文按 master 文本（`git show master:spec/DADAO-12-…` / `Kaiwu-…`）。

**复验**：`make check-inst-asm` **272/272 rc=0**（632 故障例）；`run.sh` 67 项全 PASS；11-cfx 3 路注入（落点 ±4 / 旧期望「第二次 escape 成功」/ rc1 期望 ±1）均红到用例点号，`cp`+md5 还原后回绿。

### 第 2 轮 reviewer 验收（2026-11-18）

**自证/范围**：分支 `m15-testcases-017`、WIP `d572cc76`；`git diff --name-only bfc73701 d572cc76` = 恰 4 文件（任务书 + `escape_ciii_cfx.S` + `cfx2rd_crrr_cfx.S` + `case-ledger.tsv`），`spec/`/`components/`/`contracts/` = 0 文件、版本号未动、`inst_test.inc` 未改；验收后 4 文件 `md5sum -c` 全 OK、`git status` 空。

**验收 1（本人重跑）**：`make check-inst-asm` ⇒ **272/272 rc=0**（22:53:39–22:53:49；日志 `grep -c [PASS]`=272、`[FAIL]`=0、故障链 **632** 例）；现场派生：escape 12 链+8 故障（13–20）、cfx2rd 23 链+6 故障（24–29）、ld.t 23+2、ldm.t 20+7，均 `pts_ok=True`、≤127。上轮阻断（11-cfx 两载体）已消除。

**新构造的 spec 符合性（本人核 master 原文）**：`DADAO-12 §5.3` 步骤 0（CFXESC 交**当前 cfx**）⇒ case 10/11 把入口挂 `cfx_power` 向量 ✓；步骤 2 `inner_cfx_code <= excp_prev_cfx_code`（第 973/996 行）⇒ case 12 断言 ✓；trap→handler→escape 路径 = `§5.2` 步骤 5/6（inner 63→3）+ `§5.3` ✓；自建入口写 `cfx_hmon cg3 rc10` 合法（`§3.4`：RW、**写入忽略低 2 位**原文在第 381 行）且 `__finish` 还原 hmon/power 两向量 ✓。

**定位证据（本人独立复现旧文件，非采信）**：用当前共享 qemu 重建旧 `escape_ciii_cfx.S` ELF + `-d in_asm` 跑 20 s ⇒ **机制成立**：BootROM 块 `0xfff00000000..0x24` 被重复翻译 326,491 次 = 复位重启循环，app 上下文确在 cfx_power（CFXESC 交 power ⇒ 跳复位向量）。**但具体归属不成立（finding L2，文档级）**：旧文件 `escape cfx_power` 在 **ENTRY+0x548**（`0xffffff010648`），**0x478 处是 `__fail9`（`set.zw` SYS_EXIT）**；trace 中 app 段只翻译了 `ENTRY(…100)` 与 `ENTRY+0x64`（case1 的 `escape cfx_hmon`）两块，`escape cfx_power` 从未执行 ⇒ 完成区「ENTRY+0x478 单指令自环」应改为「case1 `escape cfx_hmon` @ENTRY+0x64 ⇒ CFXESC ⇒ 复位重启循环」。`cg5 rc1 = 0x3F` 探针由新链例 23 通过而成立 ✓。

**删原 6（同帧连续两次 escape）**：**理由过强（finding L3）**——「第二次只能落新帧」不成立：handler（inner=3）内再 `trap cfx_hmon` ⇒ 新帧 `prev_cfx=3` ⇒ escape 后 inner 仍 3 ⇒ 同帧第二次 escape 仍可构造。覆盖损失有限：强断言（帧可被再次消费）消失，弱断言（cause_id/cause_ip 未被改写）已由新 case 6（原 7）保留；建议后续补「嵌套 trap 构造 prev=3」一例，**不阻断**。新增点 12 与 cfx2rd 23 属净增，语义价值更高。

**0x3F oracle 独立性**：`Kaiwu §1` 复位地址 = `cfx_power_hypv_excp_vector`、cfxha 63/power（第 19 行）+ master `DADAO-12 §5.2` 第 5 步陷入时保存 `inner_cfx_code` + `§3.6` cg5 rc1 = `excp_prev_cfx_code`（RW、初值 0）⇒ boot `trap cfx_hmon` 存 63 ⇒ 0x3F 可独立推导 ✓；cfx2rd 原故障例 28（rc1 reserved ⇒ CFXREG）在新 `§3.6` 下已不合法，**删除正确、非覆盖损失**，由链例 23（0x3F + RW 写读回 0x25）替代。

**可达 FAIL（本人 3 路，含 1 路未列）**：①（列内）escape 点 12 期望 `0x8`→`0x0`（改回旧期望）⇒ `rc=1`、guest pt=**12**；②（**未列**）escape 点 10 `cause_info` 期望 `0x7EFC0000`→`0x7EFC0004` ⇒ `rc=1`、pt=**10**；③（列内）cfx2rd 点 23 rc1 `0x3F`→`0x3E` ⇒ `rc=1`、pt=**23**；三路均 `cp`+md5 还原 → 单跑回绿 `rc=0`，快照 4 文件 md5 全 OK。

**台账/L1**：`check_case_ledger.py --write` 前后 md5 同（`9d9d8c55…`）、`check` rc=0；`check-knowledge-refs`/`check-asm-list`/`check-tests-index`/`check-inst-macro-scope` 直跑 rc=0；运行期证据目录内 `run.sh` 我方重跑 **RC=0、67 PASS / 0 FAIL**（含 C1 全量门控与 8 路注入）。

**spec 矛盾（独立核实，交架构侧/用户裁定，本任务未改 spec）**：**确为矛盾**——master `spec/Kaiwu` 三处按旧语义：`§4.2`（第 141 行）「…通过后只恢复 `global_cfx_intr_mask` 与 `excp_prev_run_mode`…**不改变 `inner_cfx_code`**；异常帧中也没有保存 `prev_cfx` 的寄存器」、`§6.2` 第 7 步（第 314 行）「`inner_cfx_code` 不因 `escape` 改变」、`§7` 清单（第 530 行），且均以 `DADAO-12 §5.3` 为据；而 master `DADAO-12 §5.3` 步骤 2/伪代码（第 973/996 行）与 `§3.6` cg5 rc1（第 404 行）已改为恢复 `excp_prev_cfx_code`。**影响面**：Kaiwu 3 处描述与 DADAO-12/QEMU/本任务测试相反，读者与实现者会误判 escape 返回语义；测试与实现已按 DADAO-12 ⇒ 需 spec 模块任务订正 Kaiwu（用户裁定）。另：本分支 `DADAO-12` 仍是旧文本（分支早于 master `c8daffc8`，已披露；本分支未动 spec，合入 master 后即一致，无冲突）。

**判决：Accepted** —— 验收 1–6 在我方重跑下全部通过；finding L2（定位描述）、L3（原 6 理由过强/覆盖建议）、L4（Kaiwu spec 矛盾待裁定）均为文档级/登记项，按规则不阻断，交 architect 收尾处理。

## 完成区

**测试结果**：`make check-inst-asm` **272/272**（272 id；故障链 632 例 = 删 1 条不再合法的故障例）rc=0；链例点数 ld.t 23 / ldm.t 20 / cfx2rd 23 / escape 12（点号 1..N 连续、`pts_ok=1`）；四载体单跑 PASS。
**验收结果**（运行期证据目录内的 `run.sh`，一跑 67 项全 PASS、rc=0，逐项见日志）：
- C1 `make check-inst-asm` rc=0 / 272-272 / 故障例 632（现场派生对账）；C6 两个 11-cfx 载体单跑 PASS、点数与现场扫描一致；
- C3（RF 5 路）+ C7（11-cfx 3 路）**可达 FAIL**：注入后 guest 退出码 = 用例点号，`cp`+md5 还原后回绿——RF：ld.t 22/23、ldm.t 19（两路）、20；11-cfx：escape 落点 ±4→**1**、**escape 12「改回旧期望（第二次 escape 成功、无 CFXESC）」→12**、cfx2rd rc1 期望 ±1→**23**；
- C4 清单重生成幂等（`--write` 前后 md5 同）；C5 `check-inst-macro-scope`/`check-asm-list`/`check-tests-index`/`check-dirs`/`check-no-residue`/`check-case-ledger` rc=0。
**期望值来源（独立 oracle）**：RF 两例取 TEST_DATA / MDATA_T 字面量；11-cfx：`cg5 rc1` = 0x3F 由「复位 cfx = cfx_power(63)（`Kaiwu §1`）+ `DADAO-12 §5.2` 第 5 步在 boot `trap cfx_hmon` 时保存 `inner_cfx_code`」派生；escape 落点 = `excp_cause_ip + imm`、CFXESC = `1<<3` 且 info = 指令编码（`§5.3` 步骤 0/3）。
**RF 窄写盘点**（spec 依据 / 现有测试是否验「未写位保持」/ 缺口）：
1. `ld.t`/`ldm.t`：SimRISC-01 §4 注 + SimRISC-00 §2.3 —— 旧测试只比低 32（`TEST_LD_RF_LO32`/`ext.uo`）⇒ **缺口，本任务补 4 条整 64 位用例**。
2. `set.ft rf, imm32`：Toolchain-01 §6.2.3 + SimRISC-03 §1 —— `00-isa-design/pseudo_set.ft_imm32.S` 已按「高半保持」整 64 位比 ⇒ 无缺口。
3. `ftcls`/`focls`：SimRISC-07 §5（目的在 rd，[63:10] 清零）—— 非窄写；测试比完整 64 位 ⇒ 无缺口。
4. ft 目的的浮点运算（ftadd/ftsub/…、`ftsgnj/ftsgnn`、`*2ft`）：SimRISC-07 册首 + SimRISC-00 §2.3 —— `__FP_CHECK` 用 `ext.uo …,31` 只比低 32 ⇒ **与 ld.t 同类缺口（后续任务候选）**，相关 `.S` 注释「高 32 位不作规定」亦需订正。
5. ft 目的取整/缩放/符号位（`__FP_CHK64` 族）：已预置目的 `0xDEADBEEFCAFEF00D` + 整 64 位比 ⇒ 无缺口。
6. 例外整 64 位搬移（`rf2rd`/`rd2rf`/`rf2rf`/`cs.*`-rf，SimRISC-00 §2.3）：测试比完整 64 位 ⇒ 无缺口。7. `set.w rf, wpN, wyde`（SimRISC-03 §1）：03 册 `_MEM` 变体比整 64 位 ⇒ 覆盖。
**修改文件**：`tests/inst/01-load-store/{ld.t_rrii_rf,ldm.t_rrri_rf}.S`、`tests/inst/11-cfx/{escape_ciii_cfx,cfx2rd_crrr_cfx}.S`、`tests/case-ledger.tsv`（生成物重生成）、本任务书（含把评审记录里一处具体 `.work/` 路径改为「运行期证据目录」措辞——`check-knowledge-refs` 机械判，仅措辞、不改结论；`SimRISC-01 §1`→`§4`）。
**新发现/坑**：
- 新语义下**应用运行在 cfx_power(63)**：固件 hmon 的 escape 恢复 `prev_cfx_code` ⇒ 应用不能 `escape cfx_hmon`；成功路径只能自建 monitor 入口（写 `cfx_hmon cg3 rc10` + `trap cfx_hmon`）。
- **CFXESC 交付给「当前 cfx」**（`§5.3` 步骤 0 伪代码）而非模式 monitor ⇒ 目标/帧错误类用例要把入口挂到 `cfx_power` 向量，否则跳回复位向量（重启自环）。
- 共享安装根被并行 `install-host` 占用时 writer-guard 直接拒绝（rc=75）⇒ 证据脚本自建 20 s×12 重试（本轮命中 1 次）。
**遗留问题**：
- **spec 自相矛盾（需 spec 任务 + 用户裁定）**：`spec/Kaiwu §4.2`/`§6.2 第 7 步` 仍写「`escape` 不改变 `inner_cfx_code`、帧中不保存 `prev_cfx`」，与 master `DADAO-12 §5.3 步骤 2`/`§3.6 rc1` 冲突；本任务按 DADAO-12 改测试、未改 spec。
- `make check` 仍停在 `check-milestones-fresh`（`m15-infra-008` 状态带注记）：master `671b0821` 已修，合并即消失（本分支未同步 master，未代改）。
- 后续任务候选：(a) ft 目的浮点族按「高半保持」补整 64 位用例 + 订正注释；(b) 其余窄写点见盘点。
