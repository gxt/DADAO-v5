# m12-chipyard-010: 位操作 + 原子 + 杂项（含 fence）

**模块**：chipyard
**项目里程碑**：M12
**依赖**：`m12-chipyard-009`（控制流 + RAS，已合入）+ `022`（预取回归修复，已合入）；两者已合入
**可并行分片**：否（单核实现，单写者）
**状态**：已验证

## 背景

用户 2026-11-08 确认：`lr`/`sc`/`swym` 与 `fence` 纳入 M12；M12 指令覆盖 = 全部非 cfx 指令。

## 目标

1. **位操作**：`SimRISC-04/08/09/10` 中的位操作（`ctpop`/`ctlz`/`cttz`/`rol`/`clmul` 等）与整数补齐。
2. **原子**：`lr`/`sc` 的 24 条形式（`<lr|sc>.<b|w|t|o>.<nn|an|ar|nr>`）、`swym`（`SimRISC-12`）；`sc` 的 `rdHB=rd0 ⇒ ILLI`。
3. **`fence`**：`SimRISC-11 §5`——`hb!=0` 或保留 `cfxha` ⇒ ILLI；`pred==succ==0` 合法 no-op；非零掩码在单周期核上天然满足（顺序执行）。
4. **合法性**：全部保留编码 ⇒ ILLI（按 `contracts/legality_rules.yaml`）。

## 验收标准

1. `tests/inst` 的 `atomics/` 与位操作用例在 chipyard 上与 QEMU 逐例一致
2. `fence` 的 ILLI 与 no-op 两条路径各有至少 3 例
3. `sc` 的 `rd0` 合法性规则有专门断言
4. `swym` 合法 no-op、保留编码 ILLI
5. Verilator 构建 rc=0（主控机）；`apply-series`/`check-source-state`/`check-patch-tree`/L1/L2 rc=0
6. 一键证据脚本（含可达 FAIL 注入）
7. 完成区 ≤30 行、无运行期路径

## 非范围

FP（`009`–`013`）、cfx 本身（`trap`/`escape`/`cfx2rd`/`cfx2rc` 不实现）

## 说明

- 参考实现 `.cache/refs/DADAO/SOC-chipyard/` 可作结构参考（**只读溯源，非执行依赖**）。
- 构建/运行在节点（**单任务单机，不迁移**）；仓库修改在主控机。

## 硬约束

1. 临时目录 `/tmp/opencode/m12-chipyard-008/`；禁仓库内临时文件（**此前有任务留过 `scratch/`、`pico-math/`**）。
2. **不提交 git**；不改共享台账；**收尾用显式 `git add <path>`，禁 `git add -A`**。
3. 完成区与真实输出逐条对齐；只动任务书范围。
4. 失败保留现场并继续推进；只在需用户语义裁定时留问。
5. 复杂命令输出留存 运行期日志目录；命令在 worktree 根内、相对路径。
6. **组件单写者**：chipyard 源树独占；发现其它任务在改先停下报告。
7. 长构建先申报耗时，落 PID/日志/`*_EXIT`；构建期间同机不得跑基线。
8. **单任务单机**：整个任务固定在一台节点做完，不跨机迁移。
9. 节点构建/运行后 `DADAO_NODES='gxt@100.79.255.16,gxt@100.81.9.54' make sync-node-repo` 并记录。
10. 不要删除其它任务的临时目录。

## 完成区

**测试结果**：一键证据脚本 **PASS=93 FAIL=0**（A 结构 / B 构建 / C 273+控制流+访存回归 / D 位操作 / E 原子+3 探针 / F 整数补齐 / G 153 故障镜像 / H QEMU 逐例 / I 周期 / J 门控）；注入自检 **2/2**（`ctpop` 差一 ⇒ D 红；期望字节篡改 ⇒ E 红；均 `cp`+md5 还原回绿）。
**修改文件**（7 项，与 `git status -uall` 逐项一致）：① 本任务书；②–④ `components/chipyard/patches/generators/dadao-wuming/src/main/scala/wuming/common/{WumingDecoder,WumingALU,WumingCore}.scala.patch`；⑤ `components/chipyard/README.md`；⑥ `components/chipyard/changelog.md`；⑦ `tools/chipyard/bit_sweep.py`（新增）。`series` 未变（无新增源文件），工作树无临时产物。

**验收结果**：
1. 位操作 **621 例**（bitcnt 414 / rol 64 / rev 62 / clmul 81）：核上 byte-exact（5184 B）、QEMU 同镜像 byte-exact、QEMU 逐例 harness **621/621**。
2. 原子 **141 例**（lr/sc 24 形式 + fence 17 + sc-rd0 14 + swym 2）：核/QEMU/期望三方一致（4464 B）；QEMU 逐例 **139/139**。fence 合法 no-op **11** 例、ILLI **6** 例；`sc` 的 `rdHB=rd0` ILLI **12** 例（12 条形式各 1）；`swym` 合法 no-op **2** 例；保留编码 UNDI **3** 例。
3. 保留标记 3 条专测：异常进入清除（sc 失败）、同 hart 改写字（sc 失败）、成功 sc 消费标记（二次 sc 失败），均 byte-exact。
4. 整数补齐 **202 例**（wyde/byte 算术/比较/移位 + `cs.*` + 块赋值）：三方一致（792 B）；QEMU 逐例 441 例 **436 过 / 5 既有 deferred / 0 失败**。
5. 故障镜像 **153/153**（ILLI 117 / MALIGN 27 / UNDI 9）：期望类 = 最后一次异常、PRE 均输出、退出码 0。
6. 回归：273 例 md5 `2d4d94651346ef673c5a855e024c1489`（= m12-005 基线）、控制流 67 例 md5 `ab4ec3fe05ecd8d16bb7fba16156d005`（= m12-009）、访存 167 例 md5 `95901d7595c3f379f4d85fa8d431c624`（= m12-008）；三套旧故障镜像 165 张重跑全绿。
7. 周期实测（trace，非估计）：`fence`/`swym`/`cs.*` 1 拍；`ctpop`/`ctlz`/`cttz`/`rev`/`rol`/`clmul` 2 拍；`rd2rd` 8 寄存器 9 拍；`lr.o.nn` 9 拍；`sc.o.nn` 命中 17 拍、未命中 1 拍。
8. 门控：elab/Verilator rc=0（`%Error`=0）；`apply-series`/`check-source-state`/`check-patch-tree` rc=0；L2 rc=0；L1 红仅 `check-run-artifacts`/`check-temp-dirs`（offender 均为他任务，本任务 0 条）。
9. 完成区 ≤30 行、无运行期路径；未使用节点（构建/运行按 2026-11-10 裁定在主控机）。

**新发现/坑**：
- 任务书写「全部保留编码 ⇒ ILLI」，但 `spec/SimRISC-00 §6.2` 与 `contracts/legality_rules.yaml`（`excp_undi`）定的是**空白单元格 ⇒ UNDI**：实测 3 例保留编码全为 UNDI，ILLI 只用于「已定义但未实现」（现仅剩 FP/RF 形式）。按 spec/向量实现。
- QEMU 的保留标记是「8 字节字 + 值比对」（`ADR-0034 D6`），spec 是「精确地址 + 宽度」。两者只在「同 hart 于 lr 与 sc 之间改写同一字」时不同；实现按 spec 取键、另比对读到的字值（spec 允许 spurious failure），同时满足两条口径，3 条探针把差别钉住。
- 复用 `inst_sweep` 辅助函数时踩坑：`asm_print_buffer`/`asm_sys_exit` 用它模块级 `BUF`/`EXITBLOCK`（ENTRY+0x8000），本任务结果缓冲在 ENTRY+0x40000 ⇒ 须自带副本（否则打印出 0x8000 处代码字节）。
- Verilator 的 `printf` 由 `PRINTF_COND=+verbose` 门控：不带 `+verbose` 就没有 `exec`/`excp cause` trace，故障判据会全假红。
- 仿真器会读 stdin（UART）：在 `while read … done < file` 里直接跑仿真会吞掉后续行（键名截断）；所有仿真/QEMU 调用须 `</dev/null`。
- `sc` 命中要重读 + 写两次 SRAM 往返（17 拍）；若后续关注性能可退化为纯标记判断（spec 允许），但会与 QEMU 的字值判据分歧。

**遗留问题**：FP/RF 形式（`ld/st/ldm/stm … rf`、`set.w rf`、`cs.* rf`、opc `0x44`/`0x5E`/`0x5F`）仍 ILLI，归 `011`–`015`；L1 两项红为他人既存（旧日志名、旧临时目录），非本任务。

## 审阅记录

### 第 1 轮 engineer 自审

自审方式：自主逐行审查（engineer 深度 1，无嵌套子代理）；范围 = 3 个 RTL 源及其导出补丁、`tools/chipyard/bit_sweep.py`、证据脚本、README/changelog。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `bit_sweep` 复用 `inst_sweep` 的 `asm_print_buffer`/`asm_sys_exit`（模块级 BUF=ENTRY+0x8000）⇒ 打印出代码字节 | ✅已修 | 自带 `asm_print_buffer`/`asm_sys_exit`（本任务 BUF/EXITBLOCK） | 三组镜像 byte-exact（5184/4464/792 B） |
| F2 故障判据按 `cause=0x100` 字面匹配，实际 trace 为 16 位零填充 | ✅已修 | 解析 `excp cause=0x…` 取最后一次异常、与期望值数值比较 | G 153/153 |
| F3 仿真器读 stdin，`while read` 循环被吞行（键名截断、镜像名错） | ✅已修 | 所有 SIM/QEMU 调用加 `</dev/null` | E 探针 3/3、G 153/153 |
| F4 QEMU 逐例断言用 `passed == total`，intfill 有 5 条既有 C-27 deferred | ✅已修 | 改为 `passed + deferred == total`（另断 failed=0） | H 621/139/441 全绿 |
| F5 `bit_sweep` 探针段重定义模块级 `ST_O_RD`（=0x21000000）⇒ `enc_mem` 产出超宽字 | ✅已修 | 删除该重定义 | emit 成功、三组镜像一致 |
| F6 Scala 语法/类型：三元 `? :`、`condAssign` 的 `class1: Bool`、w0Data 括号数、core 引用 decoder 局部 `hb/hc/hd` | ✅已修 | 改 `Mux`/`Boolean`/括号；core 用 `d.w0Idx`/`d.srcAIdx`/`d.imm` | elab rc=0 |
| F7 `cmp.so` 64 位有符号比较用 `b32`（低 32 位）而非整操作数（m12-005 遗留笔误） | ✅已修 | 统一为 `bS = extVal(io.b, true)` 后比较 | 273 例 md5 不变；reg-compare 全过 |
| F8 临时产物写在任务 worktree 内，`git status` 脏 | ✅已修 | 全部改到运行期证据目录；worktree 仅 7 项改动 | `git status -uall` 与「修改文件」一致 |
| F9 任务 worktree 缺共享组件源与工具链（两者固定在主工作树的运行期目录） | ✅已修 | worktree 内建指向主工作树的符号链接（gitignore，不入库）；任务书第 41 行的临时目录名系从 008 复制的笔误，实际用本任务号 | `apply-series`/emit/构建全部可用 |

**判决**：finding 全部已修；证据脚本 93/93 全绿 + 注入 2/2 先红后绿。

### 第 1 轮 reviewer 验收

重跑均为 reviewer 亲跑、命令在任务 worktree 根（运行期证据目录 `run.sh`、运行期日志目录 `m12-chipyard-010-reviewer-*`；reviewer 自写 `reviewer-oracle.py`/`reviewer-lr2-probe.py`/`reviewer-oldfaults.py`/`reviewer-inject.sh` 同目录）。

1. 全量 `bash …/run.sh`（含 B 构建 + L1/L2）**两轮**（审中、注入还原后）→ `== summary: PASS=93 FAIL=0 ==`、`EXIT=0`。逐条复现：273 md5 `2d4d9465…`、控制流 `ab4ec3fe…`、访存 `95901d75…`；QEMU 逐例 621/139/441（5 既有 deferred）；故障 153（ILLI 117 / MALIGN 27 / UNDI 9）；`fence_noop=11 fence_illi=6 swym_noop=2 sc_rd0_illi=12 reserved_undi=3`；周期 `fence/swym/cs=1`、`ct*/rev/rol/clmul=2`、`rd2rd x8=9`、`lr=9`、`sc 命中=17`、`sc 未命中=1`；`apply-series`/`check-source-state`/`check-patch-tree`/L2 rc=0；L1 红仅 `check-run-artifacts`/`check-temp-dirs`，offender = night×2、m13-gem5-004、m13 陈旧临时目录，**本任务 0 条**（另单跑 `make check-run-artifacts` 复核同）。
2. `bash …/run.sh --self-test-inject` → `EXIT=0`：ctpop +1 ⇒ D 红；`cp`+md5 `ee707154…` 还原 ⇒ 回绿；期望字节篡改 ⇒ E 红。
3. **reviewer 自选注入**：`WumingALU.revBlock` 块循环去 `.reverse`（多块宽度块位置互换）⇒ 重建 0/0 ⇒ `ONLY=D` ⇒ `PASS=3 FAIL=2`（`bitops: core == YAML expected actual=1`、`QEMU == core actual=1`）⇒ `cp`+md5 还原 `ee707154…` ⇒ 重建 0/0 ⇒ `ONLY=D` ⇒ `PASS=5 FAIL=0`；无 `*bak` 残留。
4. **独立 oracle**（reviewer 自写、只读 yaml）按 spec 重算 `rev/rol/bitcnt/clmul` 语义与合法性 **605 例 0 mismatch**（62/64/414/81 全覆盖）；另逐位手核 8 例：`rev.o k=8`=bswap64、`rev.t k=8`=两块各 bswap32、`rev.b k=4`=半字节交换、`rol.o orrr` ror 回原值、`rol.t orri 31` 合法 / `32` ILLI、`ctpop hd=63`（63 与 0）、`ctlz` 全 0=`hd+1`、`clmul` 全一×全一=`0x5555…`（128 位 hi/lo 均合）。
5. **旧故障 165 张**（当前 faults.json：整数 69 + 访存 77 + 控制流 19）在改动后的核上按各任务自身判据复跑 → **165/165 绿**（控制流 14 张 terminal 按 009 口径 rc=255+timeout，cause 逐条相符）。
6. **清标记第四路径（reviewer 自建）**：`lr[A] → lr[B] → sc[A]`：trace 见 `resvaddr` A→B、`sc hit=0`、该拍**零 `memop`/`beat`**、`rd5=1`、`[A]` 不变；对照 `lr[A] → sc[A]` ⇒ `rd5=0` 写入成功；核 == QEMU == 期望。
7. **未命中不访存 / 周期（原始 trace 亲算）**：`lr` 10606→10615=9；`sc` 命中 10615→10632=17（1 拍 exec + 8 拍重读往返 `beat ld`@10622 + 8 拍写往返 `beat st`/`sc-ok`@10631，比对不额外占拍）；`sc` 未命中 10632→10633=1 且窗口内无任何总线请求（下一 `memop` 属后继指令）。

**约束核验**：① `git show --stat HEAD` = 任务书 + README + changelog + 3 补丁 + `bit_sweep.py` 共 **7 文件**，与完成区①–⑦逐项一致；6 个交付文件 md5 审前=审中 `cdb81613 / 07d478a6 / f6781f6c / a8d95ed0 / 42600084 / 0f3b0cd7`；审前 `git status --porcelain -uall` 空、审后仅本审阅记录（任务书自身）为 `M`；HEAD 仍 architect WIP `9d643d86`、无 staged、reviewer 未 commit；applied 源与补丁经 `check-source-state` rc=0、无注入残留。② 完成区 20 行（含空行 25）≤30；完成区/审阅记录无宿主绝对路径、临时目录、构建/源码树引用。③ 未动 `spec/`、`contracts/`、`tests/`、台账；构建/运行全程主控机（用户 2026-11-10 口径），未占用 207/208。

**判决：Accepted**（3 条文档级 finding，交 architect 收尾改，不返工）
- F1 任务书目标 4 / 验收 4「保留编码 ⇒ ILLI」与 `spec/SimRISC-00 §6.2`、`contracts/legality_rules.yaml` `excp_undi`、`tests/inst/base/reserved.yaml`（UNDI）冲突；实现按 spec 正确——9 张保留编码镜像实测 UNDI，ILLI 只用于「已定义但未实现」（`ld.t rf` 等）。
- F2 硬约束 1 的临时目录名 `…-008` 系派单模板笔误（engineer 已在 F9 披露，实际用本任务号）。
- F3 完成区「三套旧故障镜像 165 张重跑全绿」未纳入 `run.sh`；reviewer 已独立复跑 165/165 证实，建议注明复核来源或纳入脚本。

**三个单独回答**：① **位操作与原子语义与 spec 一致**（`rev` 块内单元反序且块位置不变、`rol` 取模与 `orri` 越界 ILLI、`ct*` 的 `hd` 为有效位上界且全 0 ⇒ `hd+1`、`clmul` 128 位 XOR 归约写 `{rdHA,rdHB}`；`lr`/`sc` 24 形式、键=精确地址+宽度、对齐先判 MALIGN、`rdHB` 成 0 败 1）；原子另做 8 字节字值比对以对齐 QEMU，属 spec 明文允许的 spurious failure（完成区已披露）。② **四条清标记路径全部成立**：异常进入 / 成功 / 失败（含字值改变）由 engineer 3 探针覆盖（reviewer 重跑 byte-exact），「另一条 lr」由 reviewer 自建探针覆盖（trace + 三方一致）。③ **spec 侧对**：保留编码 = **UNDI**，任务书「ILLI」口径错（文档级，实现与既有测试向量均按 UNDI）。

#### 收尾（architect，2026-11-11 14:36）

- reviewer **Accepted**：用自写 oracle（只读 YAML、按 spec 重算）复算 **605 例 0 mismatch**（rev 62 / rol 64 / bitcnt 414 / clmul 81）；手核 `clmul` 全一×全一 = `0x5555…`、`rol.t orri 31` 合法 / `32` ILLI。
- `lr`/`sc` **四路径全成立**：异常进入 / 成功 / 失败 / **另一条 `lr`**（reviewer 自建 `lr[A]→lr[B]→sc[A]` 探针：`resvaddr` A→B、`sc hit=0`、该拍零总线事件、`rd5=1`、`[A]` 不变）；未命中不访存由 trace（exec 10632→10633，1 拍、无 `memop`）+ RTL（`scFailNow → finish(ip+4)` 不进 `sMreq`）双证。
- **口径订正（F1）**：任务书「保留编码 ⇒ ILLI」有误，真源为 `spec/SimRISC-00 §6.2` + `legality_rules.yaml`（`excp_undi`）+ `tests/inst/base/reserved.yaml` ⇒ **UNDI**；实测 9 张保留编码镜像均 UNDI，ILLI 仅用于「已定义但未实现」（117 张）。**实现与向量正确，任务书文字错**。
- 周期复核：`lr` 9 拍、`sc` 命中 17 拍（1 exec + 8 重读 + 8 写，两次 SRAM 往返）、未命中 1 拍、`fence`/`swym` 1 拍 —— 与完成区一致，17 拍属可优化项（非缺陷）。
- 注入：engineer 2/2 + reviewer 自选（`revBlock` 去 `.reverse`）⇒ `ONLY=D` FAIL=2 ⇒ 还原回绿。
- 遗留转 `ISS-386`：F2 硬约束临时目录名笔误；F3 「165 张旧故障重跑」未纳入 `run.sh`（reviewer 独立复跑证实 165/165）；`sc` 双次 SRAM 往返（可优化为单次读改写）。
