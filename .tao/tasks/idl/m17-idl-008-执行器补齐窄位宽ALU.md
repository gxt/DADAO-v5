# m17-idl-008: 执行器补齐——窄位宽 ALU（8/16 位）

**模块**：idl
**项目里程碑**：M17
**依赖**：`m17-idl-005`（四方驱动与清单机制）；与 `006`/`007` 串行
**可并行分片**：否（同改 `idl/idl_exec.py`）
**预估**：3–4 h
**档位**：大改（复核 ≤60 min）
**状态**：已验证

## 背景

8/16 位 ALU 是 RISC-V 无对应的 DADAO 特有族（`SimRISC-08`/`09`/`10`），也是「宽度与符号」规则最集中的地方：`set.zw`/`set.ow` 已通过，其余窄位宽算术/逻辑/移位/比较全在本组。

范围（2026-11-22 实测缺失数；执行时脚本重算，不采信本文数字）：
- `tests/inst/08-arith-logic-tetra`：20 个缺失 id；
- `tests/inst/09-arith-logic-wyde`：21 个；
- `tests/inst/10-arith-logic-byte`：20 个；
- `tests/inst/03-wyde-imm` 剩余 6 个镜像（id 均已注册，只加清单并跑绿，不补语义）。

**覆盖口径 = 上述四册的全部镜像**（含其 id 已注册但尚未进主清单的）；本组 `pending` 必须清零。

## 要做

1. 按 `.idl` 正文逐 id 实现；函数上方注明 id 与出处册；
2. 本组镜像从 `pending` 移入主清单，逐例四方零红；
3. 重点按正文落实：窄位宽的符号扩展/零扩展、写回只改选中半字、标志位（如有）与 `hd` 目的寄存器约定；
4. 同一族的立即数/寄存器两种形式必须共用一条实现路径（按族参数化），不为每个 id 复制一份。

## 不做

- 不改已通过 id 的语义；不改 `tests/inst`、`.idl` 源、QEMU/gem5/RTL；
- 不做 FP；不碰其它册（`006`/`007`）。

## 约束

- 独立 `git worktree`；不提交 git；术语「寄存器组」；
- `U10`（二元运算结果宽度 + 赋值截断）未裁 ⇒ 严格按 `.idl` 正文与 `opcodes.yaml` 字段位域实现；正文不足以判定者写「待裁定」并保持 `ExecError`，禁按 UDB/RISC-V 猜；
- 只动 `idl/idl_exec.py`、`idl/idl_exec_cases.toml`、`idl/README.md`（如需）、本任务书；计数现场派生；完成区 ≤30 行。

## 验证

1. 本组全部镜像四方一致（例数/槽数现场派生）；
2. 其余组无回归；
3. **可达 FAIL ≥2**：① 8 位变体写成 64 位运算 ⇒ 高半脏的用例红；② 有符号/无符号变体对调 ⇒ 边界负值用例红；`cp`+md5 还原后回绿；
4. `make check-idl` rc=0、`check-idl-parse` rc=0。

## 完成区

**测试结果**：`make check-idl` rc=0（222/222，IDL+QEMU）；全四方 `--platforms qemu,gem5,chipyard` rc=0（222/222）；`check-idl-parse`/`check-idl-sync` rc=0；`idl_exec --self-test` 30/30。本组 71 镜像（`03` 全册 8 + `08/09/10` 各 21；其中 4 张已在主清单，新增 67）全部进主清单，`pending` 67 → 0；`SEMANTICS` 152 → 213。
**修改文件**：`idl/idl_exec.py`（新增 08/09/10 窄位宽 ALU 参数化实现 + 61 个 id 注册）、`idl/idl_exec_cases.toml`（67 条迁入主清单、pending 段清零）、`idl/README.md`（008 段落）、本任务书。
**验收结果**：`check_four_way: 222/222 例四方一致（parties=idl,qemu,gem5,chipyard；主清单 222 / pending 0 / 现场派生 222）`；证据脚本（运行期证据目录内的 `run.sh`）PASS（manifest main=222/group=71/group_ids=71/pending=0/sem=213；four_way slots=3552；注入 A/B 红→cp+md5 还原→回绿；末态 md5 `f632b92e…`）。
**新发现/坑**：① 窄移位的立即数上界是 `bits−1`（32/16/8 ⇒ 31/15/7），初版误用值掩码（0xFFFF）比较，`shr.sw` 的 `immu6=16` 用例未触发 ILLI（已修，复验 subset + 全量绿）；② `rdHD` 寄存器形式移位量取低 log2(bits) 位（不抛 ILLI），与 orri 共用同一 `_narrow_shift`/`_narrow_rol` 路径；③ `set.w rf0` 的「wp2 只写 [33:32]、wp0 只写 [4:0]、wp1/wp3 写无效」由 `Machine.set` 的 rf0 掩码 + 通用切片写自然满足，无需在 op 内分支；④ 8 位循环左移用 `dup={2{val}}`（16 位）避免 s=0 时对 8 位值右移 8 位。
**遗留问题**：无。U10 未裁但 08/09/10 正文对每个结果宽度均已明示（「结果宽 = 两操作数最大宽 ⇒ 高半丢弃」/定值表），无「正文不足」的 id，故无待裁定项、无保留 `ExecError` 的 id。

## 审阅记录

### 第 1 轮 engineer 自审

| finding | 处置 | 改了什么 | 复验证据 |
| --- | --- | --- | --- |
| orri 移位/循环立即数上界误用 `mask`（0xFFFF）比较，`immu6=16` 未触发 ILLI | ✅已修 | `_narrow_shift`/`_narrow_rol` 改 `sh > bits - 1` | subset `shr.sw_orri_rd` 由 FAIL 转 PASS；全量 222/222 |
| 有符号结果是负 Python int，依赖 `m.set` 截 64 位 | ❌不修 | 确认 `Machine.set` 首行 `value &= MASK64`；且 `_narrow_ext` 已 `& MASK64` | 全部 signed 用例四方一致 |
| 注入 A 仅 1/2 目标例变红（`shl.b` 无高半脏值） | ❌不修 | 断言仍可达（`shr.ub` 例 6 高半脏）；另一例无该覆盖，非缺陷 | `injectA_red rc=1 红例=1`，还原后两个均绿 |

### 第 1 轮 reviewer 复核

**重跑记录（reviewer 自跑，仓库根，2026-11-22）**
1. 运行期证据目录内的 `run.sh`（L2 口径）⇒ **rc=0** `run.sh: PASS`（共跑 3 次均 rc=0）：`manifest_set main=222 group=71 group_ids=71 group_pending=0 sem=213 rc=0`、`manifest_inject_reachable rc=2`、`self_test 30/30`、`check_idl_parse rc=0`、`check_idl_sync rc=0`、`four_way rc=0 PASS=222/222 FAIL=0 slots=3552`、injectA `red rc=1 红例=1`/injectB `red rc=1 红例=2` → `restored md5=f632b92e…` → `green rc=0`、`source_restored_final md5=f632b92e…`
2. `make check-idl` ⇒ **rc=0，19 s**，`check_four_way: 222/222 例四方一致（parties=idl,qemu）`、`check-idl: PASS`
3. `make check-idl-parse` ⇒ **rc=0**（拒绝集+接受集 16/16）；`make check-idl-sync` ⇒ **rc=0**（operation=263 条 / 12 册 / 263 块逐字节）
4. 全四方 `python3 tools/idl/check_four_way.py --platforms qemu,gem5,chipyard --jobs 60` ⇒ **rc=0（1 m39 s）、222/222、`[FAIL]`=0**；writer-guard 各方 md5：qemu `a9ca4aec…`、bootrom `a5d78816…`、llvm-mc `ad34d612…`、ld.lld `fb4b1f13…`、gem5.opt `b9db6a94…`、chipyard sim `6d699cc3…`；日志 md5 `2ce20f43…`
5. 集合断言 FAIL 可达（独立注入）：删 `09/add.sw_orrr_rd` 整块 ⇒ `主清单缺 1 个应纳入镜像：…` **rc=2**；同变异跑 `run.sh` ⇒ `MANIFEST-PROBLEM`、`main=221`、`run.sh: FAIL 6 项` **rc=1**；`cp` 还原 md5 `69ef0b45…` ⇒ 回绿 rc=0
6. 新注入两路（工程 A/B 之外）：**C** `shr.s` 改零扩展 ⇒ rc=1、`[FAIL]` 4（shr.st/sw/sb×2）；**D** `rol` 改 64 位循环 ⇒ rc=1、`[FAIL]` 5（rol.t/w/b orri+orrr）；均 `cp`+md5 还原 `f632b92e…` 后 rc=0

**约束核验**
- 计数：现场 main=222 / pending=0 / 派生=222（run.sh 与我方独立 `tomllib` 重算一致）；`SEMANTICS` 152→213、added=61、removed=0、61 个 id 全在 `contracts/opcodes.yaml`、`_sem_params` 重复注册抛 `ExecError`（模块可导入 ⇒ 无重复）；本组 71 ⊆ 主清单、`group_pending=0`；HEAD 155 例 ⊆ 222 且全绿（007 无回归）
- 语义抽查 12 个 id（逐条对 `.idl` 正文 + 四方绿）：`shl.t/shr.ut/shr.st/rol.t/rev.t`(08)、`add.sw/add.uw/sub.sw/cmp.sw/shr.sw`(09)、`shl.b/shr.sb/rol.b/rev.b`(10) —— 符号/零扩展、整 64 位扩展写回、`immu6>bits−1 ⇒ ILLI`（shl/shr/rol 三族 × 32/16/8 同一路径）、orrr 移位量取低 log2(bits) 不抛 ILLI、`rev` 逐块单元反转，均与正文一致；`set.w rf0` 仍走 `Machine.set` 的 rf0 [33:32]/[4:0] 掩码（镜像含 rf0 用例且绿）
- 复用：orri/orrr 同一次 `_sem_params` 注册同一函数（shl/shr.u/shr.s/rol ×3 宽度），无按 id 复制实现
- 越界：`git status -uall` 仅完成区 4 文件（快照前后逐行一致、4 文件 md5 未变）；未动 `tests/inst`、`.idl`、`spec/`、`.tao/contracts/`、QEMU/gem5/RTL；`idl/` 无 `__pycache__`
- 基线红：`check-knowledge-refs` rc=2，唯一悬空 `.tao/knowledge/milestones-m18.md:39 ADR-0059`（M18，无本任务条目）；`check-run-artifacts` rc=2，566 问题全为运行期日志命名类（chipyard/linux/arch/infra/llvm/ansibench 目录），grep `m17|idl-008|/idl/` 0 命中

**finding 表**

| # | finding | 处置 |
| --- | --- | --- |
| F1 | 完成区「本组 71 镜像（03 剩余 6 + 08/09/10 各整册）」括注相加=69；实际 71 = 03 全册 8 + 三册 63，其中 `03/or.w_rwii_rb`、`03/set.zw_rwii_rb`、`08/add.st`、`10/add.ub` 4 张 HEAD 已在主清单（本次新增 67） | 文档级数字笔误，architect 收尾改 |
| F2 | 完成区写死证据脚本的运行期绝对路径，与「证据脚本固定写『运行期证据目录内的 `run.sh`』」口径不符 | 文档级，architect 收尾改 |
| F3 | 派单口径「写回只改选中半字」与 08/09/10 正文不符：正文为整 64 位符号/零扩展写回（如 `rd[rdHB] = {{48{sum[15]}}, sum}`），「只改选中半字」适用于 03 的 `set.w`/`or.w`；实现按正文且四方绿 | 非缺陷，记口径说明 |

**判决：Accepted** —— 上述验收命令块在我方重跑下全绿、集合断言与语义断言的可达 FAIL 均已实证（含自选 2 路新注入）、约束无违反；F1–F3 均为文档级，不阻断。**状态**未改。
