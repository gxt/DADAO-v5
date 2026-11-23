# `tests/inst/` 重构台账（YAML → 汇编 + 宏）

> **目标**：让每条**操作码**的测试可读、可审、可三方差分。YAML 退出，改为 `.S` + 宏，期望值内联。
> **判据**：一个 id 一个文件；一个文件一个 ELF；失败点号 = 用例序号（退出码 `0x01`–`0x7F`，见 `spec/Kaiwu §7.1`）。

## 1. 大类（= SimRISC 册）

| 目录 | SimRISC 册 | id 数（初估，待按各册附录 A 校准） |
|---|---|---|
| `01-load-store/` | 01 取数存数 | 38（单元素 19 + `ldm`/`stm` 19，均已在盘） |
| `02-reg-copy/` | 02 寄存器复制 | 16 |
| `03-wyde-imm/` | 03 16 位立即数操作 | 8 |
| `04-arith-logic-octa/` | 04 64 位数据运算 | 60 |
| `05-arith-addr/` | 05 64 位地址运算 | 5 |
| `06-control-flow/` | 06 控制流 | 15（已迁） |
| `07-floating-point/` | 07 浮点运算 | 44 |
| `08-arith-logic-tetra/` | 08 32 位数据运算 | 16 |
| `09-arith-logic-wyde/` | 09 16 位数据运算 | 16 |
| `10-arith-logic-byte/` | 10 8 位数据运算 | 16 |
| `11-cfx/` | 11 核芯功能扩展 | 29 |
| `12-misc/` | 12 其它指令 | 28（`lr`/`sc` 24 + `swym`/`ct*` 4；全部已迁） |

> id 总数应恰为 **263**（`contracts/opcodes.yaml`；`m13-spec-010` 删 `ft2ft`/`fo2fo`、加 `rf2rf` 后）。校准任务：建「id → 册」映射表并机械校验（每个 id 恰好属一册、01–12 册合计 263；非 id 载体在 `00-isa-design`，不计入）。

## 2. 小类（= 一个 opcode id）

- 文件名 = **`<id>.S`**（id 里已含 format 与 bank，不重复写，如 `ld.o_rrii_rd.S`）
- 目录内不再按 bank 分层
- 一行一个用例，期望值**内联**（宏层 `tests/inst/macros/inst_test.inc`）：

```
	TEST_LD        3, ld.ub,  rd2,   rb4,   TEST_DATA,          0x000,    0x0000000000000001
	TEST_ST       10, st.w,   rd2,   rb3,   TEST_DATA,          0x044,    0xDEADBEEFCAFEF00D, 0x00000000F00DFFFF
	TEST_FAULT    16, ld.ub,  rd0,   ILLI,  rb3,                TEST_DATA, 0x000
```

| 宏 | 参数 | 判据 |
|---|---|---|
| `TEST_LD` / `TEST_LD_RB` / `TEST_LD_RA` / `TEST_LD_RF`（`_LO32` 只比低 32 位） | `检查点, 助记符, 目的, 基址, 基址值, 偏移, 期望值` | 目的寄存器 == 期望值 |
| `TEST_ST` / `TEST_ST_RB` / `TEST_ST_RA` / `TEST_ST_RF` | `检查点, 助记符, 源, 基址, 基址值, 偏移, 源值, 数据单元期望` | 存储后该 8 字节数据单元逐字节相等（b/w/t 只改其中几个字节，其余保持） |
| `TEST_FAULT` | `检查点, 助记符, 目的/源, 故障名, 基址, 基址值, 偏移` | 该指令触发 `CFXMEM`/`CFXREG`/`ILLI`/`MALIGN`/`IALIGN`，退出码 = `0xF0|异常位索引` |

- **镜像 = 每 `.S` 一个**（`m15-testcases-007`）：一个 `.S` 产出**一个** ELF/镜像 ——
  链例（非故障用例顺序跑，逐检查点把实测 8 字节写进结果缓冲并打印）跑完**接着**跑该
  文件的**全部**故障例（异常不返回被测指令之后，由 `.faulttab` 顺序续跑）。
  `-defsym CASE_N=<检查点>` = **调试用单例模式**（`_start` 直接跳该例，只比退出码，
  不进 `check-inst-asm`）。检查点数 ≤ 127，失败点号 = 用例序号。
- 三方比较（同一份 ELF）：`tests/ee-tiny/run_inst_tiny.py`（chipyard
  `WumingTinyConfig` / QEMU `kaiwu-tiny` / gem5 FS `tiny`）。

## 3. 每个 id 的用例设计模板（5 类）

| 类 | 写什么 | 每 id 条数 |
|---|---|---|
| encoding | 该 id 的唯一编码（mask/value 校验） | 1–2 |
| legality | 该 id 适用的合法性规则（rd0/rb0、双目的、保留编码…） | 2–4 |
| semantic | 正常路径：宽度 × 符号 × 形式 | 4–8 |
| boundary | 该族特有边界（进位/借位/最值/次正规/对齐/窗口…） | 4–8 |
| overlap | 源=目、部分重叠、块复制重叠 | 1–3 |

合计每 id 约 15–25 条；一文件一个 ELF，检查点 ≤127。

## 4. 任务拆分（18 个，编号已落册；**id 清单以各册附录 A 为准**）

| # | 任务号 | 覆盖 | id 数 |
|---|---|---|---|
| 1 | `m13-testcases-012` | `01-load-store` 单元素（`ld`/`st`） | 19 |
| 2 | `m13-testcases-013` | `01-load-store` 多元素（`ldm`/`stm`） | 19 |
| 3 | `m13-testcases-014` | `02-reg-copy`（复制 + `cs.*`） | 16 |
| 4 | `m13-testcases-015` | `03-wyde-imm` | 8 |
| 5 | `m13-testcases-016` | `04-arith-logic-octa` 算术 | 15 |
| 6 | `m13-testcases-017` | `04-arith-logic-octa` 逻辑/移位/扩展 | 14 |
| 7 | `m13-testcases-018` | `04-arith-logic-octa` 位操作 | 4 |
| 8 | `m13-testcases-019` | `05-arith-addr` | 6 |
| 9 | `m13-testcases-020` | `06-control-flow` | 15 |
| 10 | `m13-testcases-021` | `07-floating-point` 算术与最小最大 | 18 |
| 11 | `m13-testcases-022` | `07-floating-point` 转换/比较/分类 | 26 |
| 12 | `m13-testcases-023` | `07-floating-point` 取整/缩放/符号 | 8 |
| 13 | `m13-testcases-024` | `08-arith-logic-tetra` | 21 |
| 14 | `m13-testcases-025` | `09-arith-logic-wyde` | 21 |
| 15 | `m13-testcases-026` | `10-arith-logic-byte` | 21 |
| 16 | `m13-testcases-027` | `11-cfx`（5 条 cfx/system） | 5 |
| 17 | `m13-testcases-028` | `12-misc` 原子（`lr`/`sc`） | 24 |
| 18 | `m13-testcases-029` | `12-misc` 其余（`swym`/`ct*`） | 4 |
| — | `m13-testcases-030` | `.S` 接入门控 + YAML 退役（`ISS-413`） | 3 册 / 30 id（见 §5.4） |

合计 **264** 个 id（与 `contracts/opcodes.yaml` 一致；各册实测：01 38 / 02 16 / 03 8 / 04 33 / 05 6 / 06 15 / 07 52 / 08 21 / 09 21 / 10 21 / 11 5 / 12 28）。

## 5. YAML 台账（迁移与删除）

现状：**30 个 YAML 文件、1586 条用例、覆盖 229 个 id**；`opcodes.yaml` 有 **264** 个 id ⇒ **36 个 id 无 YAML 载体**；另有 16 个 id 出现在多个文件里。

**删除规则**：一个 YAML 文件里的**所有 id** 都迁完后，才 `git rm` 该文件，并在本表勾掉。

| YAML 文件 | 用例 | 涉及 id 数 | 状态 |
|---|---|---|---|
| `atomics/atomics-fence.yaml` | 17 | 1 | 待迁 |
| `atomics/atomics-lrsc.yaml` | 108 | 24 | 待迁 |
| `atomics/sc-rd0.yaml` | 14 | 24 | 待迁 |
| `base/aip-si.yaml` | 12 | 1 | **id 全部已迁**（`aip.si_riii_rb`，见 §6/019）；文件未删（§5.1 前置） |
| `base/bitcnt.yaml` | — | — | 待迁 |
| `base/reg-arith.yaml` | 224 | — | 部分迁移（05 族 3 个 id `add.o_bbd`/`add.si_riii_rb`/`sub.o_bbd` 见 §6/019；余 32/16/8 位待 024/025/026） |
| `base/reg-compare.yaml` | — | — | 部分迁移（05 族 `cmp.uo_orrr_dbb` 见 §6/019；余各宽度 id 待 024/025/026） |
| `base/reg-cond-assign.yaml` | 25 | 5 | **id 全部已迁**（5 个 `cs.*_rrrr_rd`，见 §6）；文件未删（§5.1 四个门控阻塞） |
| `base/reg-imm-block.yaml` | 48 | 7+6 | **id 全部已迁**（6 个块复制 id 见 §6/014，7 个 rwii id 见 §6/015）；文件未删（§5.1 前置） |
| `base/reg-logic.yaml` | 16 | 4 | **id 全部已迁**（4 个逻辑 id，见 §6/017）；文件未删（§5.1 前置） |
| `base/reg-shift-extend.yaml` | 112 | — | 部分迁移（10 个 64 位 id 见 §6/017；其余 32/16/8 位待 024/025/026） |
| `base/ctrl-br.yaml` | 40 | 9 | **id 全部已迁**（`br.*` 9 个 id，见 §6/020；`br.z_riii_rd` 原本无 YAML 载体）；文件未删（见 §5.2） |
| `base/ctrl-jump.yaml` | 6 | 2 | **id 全部已迁**（`jump` 2 个 id，见 §6/020）；文件未删（见 §5.2） |
| `base/ctrl-call.yaml` | 11 | 2 | **id 全部已迁**（`call` 2 个 id，见 §6/020）；文件未删（见 §5.2） |
| `base/ctrl-ret.yaml` | 10 | 1 | **id 全部已迁**（`ret` 1 个 id，见 §6/020）；文件未删（见 §5.2） |
| `base/mem-rd.yaml` | 122 | 22 | **已删**（`m13-testcases-030`，`git rm`；载体 = `01-load-store/<id>.S`，见 §5.4） |
| `base/mem-ra.yaml` | 22 | 4 | **已删**（`m13-testcases-030`；同上） |
| `base/mem-rb.yaml` | 23 | 4 | **已删**（`m13-testcases-030`；同上） |
| `base/misc.yaml` | — | — | 待迁 |
| `base/reserved.yaml` | 9 | 4+3 | 部分迁移（`ld.`/`st.` 的 6 条 reserved-cfx `CFXMEM` 已迁；3 条 reserved-opcode `UNDI` 无 id，待 `12-misc`） |
| `fp/*.yaml`（`arith`/`convert`/`divrem`/`cond-assign`） | — | — | **id 全部已迁**：`cond-assign.yaml` 的 3 个 `cs.*_rrrr_rf`（§6/014）、`arith.yaml` 的 8 个算术最小最大（§6/021）+ 4 个比较（§6/022）、`divrem.yaml` 的 6 个（§6/021）、`convert.yaml` 涉及的 5 个 id（§6/022，另 13 个转换 id 原本无 YAML 载体）；文件**未删** —— `divrem.yaml` 是 `check-inst` 的 L3 载体、其余受 §5.1 前置阻塞 |
| `bitcnt/`、`clmul/`、`fma/`、`minmax/`、`rev/`、`rol/`、`roundint/` 各自 | 414/81/… | — | 部分迁移（`clmul.o`/`rev.o`/`rol.o` 的 64 位形式见 §6/018；其余宽度与 `bitcnt` 待迁） |

> 精确「文件 → id」清单由 `tools/testcases/` 现场导出（不写死在本表，避免漂移）。

### 5.1 删除规则的一个前置（`m13-testcases-013` 现场结论）

「所有 id 迁完」是**必要**条件，不是**充分**条件：`inventory.md` 的类清单列仍是
YAML 载体真源，`validate_vectors.py` 按它做数据覆盖门控、`check-generator-sync`
按它校验生成器落盘。把 `base/mem-{rd,ra,rb}.yaml` 移走后实测：

- `validate_vectors.py` rc=1：`DATA COVERAGE: 116 gap(s)`（30 个 id 声明了
  类但 `tests/inst/base/*.yaml` 里已无 active 用例）；
- `check_case_ledger.py` rc=1：清单多 167 行（需 `--write` 重生成）；
- `make check-generator-sync` 的 `generate_mem_vectors.py --check` 无输入。

⇒ 删除须与「`inventory.md` 载体/类登记改为 `.S` 载体 + 数据覆盖门控认得 `.S` +
mem 生成器退役 + 台账重生成」同一批次做（`m13-testcases-013` 已把结论与实测
输出写进任务书「待裁定」）。**已由 `m13-testcases-030` 同批完成，见 §5.4。**

### 5.2 删除规则的前置（`m13-testcases-020` 现场结论：4 个 ctrl YAML）

`ctrl-br`/`ctrl-jump`/`ctrl-call`/`ctrl-ret` 的 id 已全部有 `.S` 载体，但**删除仍被
四条门控阻塞**（`cp` 备份 → `mv` 走 → 逐门控跑 → 还原，md5 对账一致）：

- `tests/inst/inventory.md` 的类清单仍以 YAML 为真源 ⇒ `validate_vectors.py` rc=1
  （**44 条** `DATA COVERAGE GAP`：inventory 声明 ✓ 但 `tests/inst/base/*.yaml`
  里已无 active 用例）；
- `tests/case-ledger.tsv` 逐条身份清单 ⇒ `check_case_ledger.py` rc=1（多 67 行）；
- `tests/inst.yaml` 里有 4 条 `file:` 指向这 4 个 YAML ⇒ `check_tests_index.py` rc=1；
- `check-generator-sync`（L2）的 `generate_ctrl_br.py --check` 与
  `generate_ctrl_jump_call_ret.py --check` **以这 4 个文件为渲染目标** ⇒ 缺文件 rc=1。

⇒ 与 §5.1 同批处理（`m13-testcases-030`）：inventory 载体登记改 `.S` + 数据覆盖门控
认得 `.S` + 生成器退役 + 台账重生成，四条一起做才可 `git rm`。
**`m13-testcases-030` 只做 §5.1 的三册**：执行覆盖已经具备（L2 `check-inst-asm` 覆盖
`tests/inst/` 下**全部含 `.S` 的册**，含 ctrl 4 册），但这 4 册的 YAML **同时是** L3
`check-inst`（`semantics_gate`）的载体，且 `validate_vectors` 的 `br.*` 双路径守卫
（`taken` + `not-taken`，按 `expected_pc` 分类）只在 YAML case 上有结构字段 ⇒ 删这 4 册
会缩小 L3 用例集并把双路径守卫变成空判。故 `030` 不删它们，须另立任务（双路径守卫改由
`.S` 派生的同一批里做）。`base/reg-{arith,compare,shift-extend,logic,cond-assign,imm-block}.yaml`、
`base/aip-si.yaml`、`rol/rol.yaml`、`base/reserved.yaml` 同理**不删**：它们是 chipyard
`inst_sweep` 的输入（273 例 sweep 的 md5 是既有验收基线）或 `generate_isa_vectors`
的渲染目标（六册一次 `--check`）。

## 5.4 YAML 退役（`m13-testcases-030`，`ISS-413` 收口）

**删除**：`base/mem-rd.yaml`、`base/mem-ra.yaml`、`base/mem-rb.yaml`（`git rm`；167 条用例、
30 个 id）。`tests/inst.yaml` 同步去掉 3 条 `file:` 条目（489 → 486），`tests/case-ledger.tsv`
由 `check_case_ledger.py --write` 重生成（现场身份 2200 → 2033，只减 167 行）。

**载体切换的四处改动**（缺一条就会红，见 §5.1 的四条阻塞）：

1. `inventory.md`：30 个访存 id 的 `file` 列改 `<册>/<id>.S`；新增「`.S` 载体覆盖」节
   （12 册 → `check-inst-asm`）；「门控覆盖（L2/L3）」表删 3 行 mem 册（该表只登记 YAML 载体）。
2. `validate_vectors.py`：YAML 载体仍按 `(id, class)` 做类级覆盖；**`.S` 载体改为执行型** ——
   只断言结构（stem 是 `opcodes.yaml` 身份、含用例行、检查点号 1..N 连续，复用
   `run_asm_suite.scan_source`），类级覆盖交给执行门控。另加 `inventory` `file` 列表无悬空引用。
3. 新门控 L2 `make check-inst-asm`：`run_asm_suite.py --books-root tests/inst --platforms qemu`
   ——263 个 id + 非 id 载体（`00-isa-design`）/ 现场镜像数（`check-inst-asm` 现 903）全部跑 QEMU `kaiwu-tiny`，链例比结果
   字节流、故障例比 monitor 段退出码。**单平台**：三方逐字节仍是各册任务的验收口径。
4. `generate_mem_vectors.py` 退役（`git rm`）：它的唯一产物就是这三册；`check-generator-sync`
   从 6 个生成器改 5 个（ctrl×2 + isa + misc + bitcnt 仍在）。

**判据变化**（不是放宽，是换载体）：L3 `check-inst` 由 1141 例降到 1020 例（0 failed、
5 deferred），Tiny 段 44 → 14 例 —— 差额正是这三册的 Tiny 画像用例，现由 L2
`check-inst-asm` 的 897 个镜像在**同一平台**上执行（更强：真跑而非 schema）。
273 例 chipyard sweep（`inst_sweep`）的输入不含 mem 三册 ⇒ md5 不变。

**未删的册与原因**见 §5.2 末段（ctrl 4 册：L3 载体 + `br.*` 双路径守卫；reg/aip-si/rol/
reserved：`inst_sweep` 输入与 `generate_isa_vectors` 渲染目标）。

**已处置**（`m13-testcases-040`）：`tools/chipyard/mem_sweep.py` 已**退役**（`git rm`）——它的
输入（YAML oracle 的期望寄存器/内存值）随这三册一起消失；`.S` 载体自带内联期望，由
`run_asm_suite.py` 在 chipyard/qemu/gem5 上执行。其 `dump_reg`/`dump_mem` 两个共用 helper
移入 `inst_sweep.py`（`ctrl_sweep.py` 的消费点同步改指）。

## 5.3 并行分片协议（用户 2026-11-14）

18 册目录彼此独立，可**并行**派到不同节点。为免共享清单互相覆盖，**每个分片任务只写自己的片段**，由主会话串行合并：

- 分片任务的产物：`tests/inst/<册>/*.S`（本册目录，独占）+ 两个片段文件
  - `tests/inst/.fragments/<任务号>.inst.fragment` —— 本任务要加入 `tests/inst.yaml` 的条目（**只写自己的条目，内容为 YAML 列表文本**，格式同根清单）。
    **扩展名不用 `.yaml`**：`check-tests-index` 规则 11（`m13-testcases-043`）禁止 `tests/inst/` 下出现任何 `*.yaml`（载体模型只有 `.S`），片段只是待合并的索引文本、不是载体，故用 `.fragment` 后缀避免与门控冲突（`m13-testcases-037` 现场发现，2026-11-15）。
  - `tests/inst/.fragments/<任务号>.migration.md` —— 本任务要追加到 §1/§6 的行（**只写自己的行**）。
  - 用**任务号**而非册名：同一册可能同时有两个任务在改不同文件，按册名会撞车。
- 分片任务**不改** `tests/inst.yaml`、`tests/inst/MIGRATION.md`、`tests/inst/README.md`、`macros/inst_test.inc`、`run_asm_suite.py`；若确需改后三者，在任务书「待裁定」写清并停下。
- 主会话合并时：读所有片段 → 按册序并入根清单 → **重跑** `check-tests-index`/`check-case-ledger`/`validate_vectors` → 删除 `.fragments/`。
- 节点侧：各分片用**独立** `~/eval/<任务>/` staging 与**独占** work-dir；`--jobs` 用脚本默认（核数/2）。

## 5.5 YAML 全退役（`m13-testcases-043`，用户 2026-11-14 裁定）

**判据先行**：先用覆盖等价审计（204 个 YAML id × 四类断言：encoding / semantic+boundary /
legality / overlap）确认 `.S` 有对应类，再删。**返工后审计结论 = 204 个 id 全绿**
（`REVIEW` 0）。唯一曾判 REVIEW 的 `ret_riii_ra` 是**第 1 轮判读错误**：YAML 该例的
MemRAS 条目是 `0x0001BBBB00000000`（**计数 = 1**、返回地址 `0xBBBB00000000`，不是「计数 0」）
⇒ 按 `SimRISC-00 §2.4.2` D4b 消费条目并跳到该地址，`Kaiwu §1.2`（Tiny 只映射
cfxha 63 / 3，cfxha 46 ⇒ 其它 cfxha 段取指）⇒ **`CFXMEM`（0xF1）期望正确**。
**已补**：`ret_riii_ra.S` 增点 23 `TEST_FAULT_RAS 23, CFXMEM, ret rd0, 0`
（`TEST_FAULT_RAS` 宏增 `CFXMEM` 分支），QEMU 实跑 `0xF8/0xF8/0xFB/0xFB/0xF1` 全通过。
`clmul.o`/`ctlz`/`cttz`/`ctpop` 的「点数 < YAML 例数」（4 个 id）是抽样口径差异
（`.S` 一条宏/一个点覆盖多条 YAML 例），头部类计数比的 7 个 id 逐个核在审计记录里，
类覆盖全在位。

**删除**：27 个 YAML（1,315 例 / 204 id + 3 条无 id 保留编码；入库 768 KB）；
`tests/inst/{base,fp,rev,rol,bitcnt}/` 目录随空删除（`atomics`/`clmul` 的 C/LL 探针**当时保留**，
后分别由 `m13-testcases-050`/`m15-testcases-008` 退役删除 —— 现行载体只有 `.S`；
`fma`/`minmax`/`roundint` 三个目录**不是**空目录 —— 各含 3–4 个 `.c/.h` 探针，保留并
留给 `m13-testcases-044`；该任务已核对 lit/e2e/picolibc 覆盖、把缺的边界点抽进
`07-floating-point` 的 `.S` 载体后**删除**这三个目录（探针退役）。`tests/inst.yaml` 305 → 283 条（删 23 条 YAML 载体条目，
加 1 条非 id 载体条目）。

**保留编码迁入 `00-isa-design/undi_reserved.S`**：3 条无 id 保留编码（word
`0x08040001` / `0x1B040001` / `0x58040001`）断言 **UNDI**（monitor 码 `0xF9`），
QEMU 实跑 3/3 通过。文件名**不是** opcode id ⇒ 在 `check_tests_index.NON_ID_CARRIERS`
与 `validate_vectors.NON_ID_CARRIERS` **逐文件**登记（同目录出现未登记 `.S` ⇒ 红），
并由 `tests/inst.yaml` 的 `inst-00-isa-design-001` 索引（载体↔索引双向断言不放宽）。

**5 条 `cs.*` 别名 overlap**（C-27）：`cs.{n,z,p,eq,ne}_rrrr_rd` 各补 1 条「条件寄存器与
源寄存器同名」链例（`rdHA==rdHC` / `rdHA==rdHD`），按 `spec/SimRISC-02 §2`「先判断、再赋值」
⇒ 读后写序确定、不涉及 C-27 快照问题；`dest↔条件` 同名仍 deferred。QEMU 实跑 5/5 通过
（每 id 链例 14→15 点，镜像 +5）。

**门控与工具退役**（逐项）：

| 依赖点 | 处置 |
|---|---|
| `check-inst`（L3，Vast 全量 + Tiny 子集） | **删除**。Vast 的 ISA 级执行覆盖**明确放弃**（用户裁定）；Vast 的 ISA 语义由 `spec/` + M13 三平台差分矩阵承担 |
| `check-inst-smoke`（L2，YAML 代表集） | **删除**（与 `check-inst` 同语料；`.S` 全量已由 L2 `check-inst-asm` 覆盖） |
| `tools/qemu/semantics_gate.py` | YAML 执行模式**退役**（不带 `--form-check` 调用 ⇒ rc=2 显式失败）；只保留 `--form-check`（L1 `check-qemu-forms`） |
| `validate_vectors` | 只留 `.S` 分支（载体结构 + inventory 同步 + 覆盖率声明）；YAML 逐 case 校验删除 |
| **两条 br 守卫** | **直接退役**（用户裁定）：`expected_pc` 必须存在、`br.*` 必须 taken+not-taken 双路径。**改由执行证据承担**：`.S` 的 `__LAND_IP` 查目标 IP（现场 **71** 处 / 16 个载体 ≫ 原 YAML **34** 条 non-null `expected_pc`）+ 三平台跑批 |
| 6 个 YAML 生成器 | **删除**（唯一产物已删）⇒ `check-generator-sync`（L2）与 `check-rev-vectors`（L1）两个目标同步退役 |
| `check-case-ledger` | vector 侧由 YAML 改派生 **`.S` 用例行**（`asm` 行 = 路径 + 用例行文本 + 同内容序号，复用 `run_asm_suite` 同一组正则）⇒ `.S` 逐条删除哨兵到位（闭合 `ISS-441` 的「`.S` 无删除哨兵」缺口） |
| `run_parity.py` 的 `inst` scope | **退役**（显式 setup error）：它是 YAML 唯一残余消费者；inst 三平台逐字节改用 `run_asm_suite.py --platforms chipyard,qemu,gem5`（Tiny） |

**chipyard sweep 工具退役**（阶段四）：`bit_sweep` / `ctrl_sweep` / `fp_sweep` /
`inst_case_run` 删；`inst_sweep.py` **降为库**（只留编码器 / ELF 布局 / `dump_reg` /
`dump_mem`，供 `fetch_probe/gen_probe.py`）；`fp_ref.py` 保留为**生成期工具，不作判据**
（FP 判据 = `.S` 内联期望 + `fp_unit` 的 hardfloat 对照）。

## 5.6 多 hart / 内存序 GAP（`m13-testcases-050`；挂 `ISS-440`/`ISS-443`）

**背景**：`tests/inst/atomics/` 的 5 个 C 探针（`aba_treiber`/`atomic_builtins`/
`barrier_probe`/`c11_alltypes`/`counter`）连同其驱动脚本与 oracle 脚本已按用户 2026-11-15
裁定 A **退役**：它们从未进任何门控（无 make 目标、不在 `l3_run.py`），且其判据（多线程争用）
在单 hart 的 Tiny 上不可观测。退役后的三层分工：

| 层 | 载体 | 判据 |
|---|---|---|
| 指令层：`lr`/`sc` 的 RMW 合成序（含 `sc` 失败重试） | `tests/inst/00-isa-design/atomic_rmw.S`（`m13-testcases-049`） | L2 `check-inst-asm` 逐镜像执行 |
| 编译器层：`__atomic_*` builtin 与 C11 `<stdatomic.h>` 的**值语义** | `tests/unit/llvm/e2e/atomics_e2e.c` + `lit/atomics_e2e.test` | `check-lit`：QEMU `kaiwu-tiny` 真跑，guest 退出码 = 判据（0 = 20 例全过，N = 第 N 例失败） |
| 争用 / 内存序**强度** | **无载体（本 GAP）** | 待多 hart 机型 |

**GAP 清单**（单 hart 不可判定，未经实验验证前不得声称覆盖）：

- **ABA**：Treiber 栈「`{ver:16,ptr:48}` 打包 + 计数器回绕」的不变量只在真并发下才有意义；
  单 hart 的 `lr/sc` 循环首次即成功，观察不到 ABA。
- **互斥计数丢更新**：N 线程 × M 次 `fetch_add` 的总和守恒需要真并行（或至少抢占式调度）；
  Tiny 单 hart 的顺序执行恒满足。
- **`a_barrier()` 观测量**：探针原用「`fence` 计数 == 源码站点数、立即数 0xFFF」的结构断言；
  这只是**代码形状**，不证明屏障语义。形状部分现已由 e2e 的 `ASM: fence cfx_umon, 4095`
  承担，**语义**仍缺。
- **`fence` 顺序强度**：`__ATOMIC_RELAXED` 与 `__ATOMIC_SEQ_CST` 在单 hart 上产生**可观察差异
  为零**的同一结果，无法区分「正确实现」与「一律发全屏障」或「完全不发屏障」。e2e 只钉
  「seq_cst 处出现 `fence cfx_umon, 4095`」这一**形状**，强度（acquire/release/relaxed 的
  实际约束）未验证；`spec/SimRISC-12` 的 `fence` 语义强度须另立验证（多 hart 机型 + 竞争
  重放），见 `ISS-440`（多 hart 机型/测试面）与 `ISS-443`（内存序强度口径）。

**恢复覆盖的入口**：多 hart 机型落地后，新载体应是**执行型**（`.S` 或 e2e）而非回到
「C 探针 + 手工 oracle」——争用类用例须自带失败点号（退出码即判据），并进 L2/L3 门控。

## 6. 已完成

### `m13-testcases-030`：`.S` 入 L2 门控 + mem 三册 YAML 退役（`ISS-413`）

- **新门控**：`make check-inst-asm`（L2，`_locked-check-modules` 成员；`GATE_LOCKED_TARGETS`
  同表）。目标体 = `run_asm_suite.py --books-root tests/inst --platforms qemu --jobs $(TEST_JOBS)`；
  载体集/镜像数/检查点数全部现场派生，不挂 `build-bootrom` 前置（L2 不重建共享产物）。
- **`run_asm_suite.py`**：新增 `--books-root`（扫全部含 `.S` 的子目录）、每册目录内 `.lds`
  自动选定、`--vectors` 可重复；read guard 只登记**本平台集合真的会用**的二进制
  （`--platforms qemu` 不再被并行的 gem5/chipyard 构建挡住）；`--scan-only` 不登记二进制。
- **`validate_vectors.py`**：载体二选一 —— YAML（类级覆盖不变）/ `.S`（执行型：只断言
  stem 是 `opcodes.yaml` 身份、含用例行、点号 1..N 连续）；`inventory` `file` 列无悬空引用。
- **`inventory.md`**：30 个访存 id 的载体列 → `01-load-store/<id>.S`；新增「`.S` 载体覆盖」节。
- **删除**：`base/mem-{rd,ra,rb}.yaml`（167 例 / 30 id）、`generate_mem_vectors.py`；
  `tests/inst.yaml` 489 → 486 条；`case-ledger.tsv` 2200 → 2033（只减 167 行）。
- **判据**：`check-inst-asm` 264 id / 897 镜像全绿（QEMU `kaiwu-tiny`）；`check-inst`
  1020 例 0 failed（Tiny 段 14 例）；273 例 chipyard sweep md5 不变。详见 §5.4。

### `m13-testcases-033`：`ext.uo`/`ext.so` orrr 的 `rdHD` 越界值（64 / 67 / 2^64−1）三平台用例

- 改动（**只追加、不改既有点号**）：`tests/inst/04-arith-logic-octa/ext.uo_orrr_rd.S` 与
  `ext.so_orrr_rd.S` 各 +6 链例（点号 17–22）；原故障例 `dst_rd0` 点号 17 → 23（点号仍
  连续 1..23 = 链例 22 + 故障例 1）。文件头的分类计数同步为 encoding 2 / semantic 6 /
  boundary 11 / overlap 3，并把「越界未收录」注释改为「已收录」。**无宏层/驱动器改动**。
- 语义（`spec/SimRISC-04 §2.2`，`m13-spec-008` 定稿）：`orrr` 的 `hd = rdHD[5:0]`，更高位
  被忽略、**不触发异常**（用户裁定 2026-11-13）。覆盖 `rdHD=0` 基线、`64 ⇒ hd=0`、
  `67 ⇒ hd=3`、`63 ⇒ hd=63`、`2^64−1 ⇒ hd=63`；`ext.so` 取 bit0=1 / bit3=1 的源值暴露
  符号扩展（`rdHD=64` 用例结果为全 1 而非零扩展的 `0x1`）。
- 跨用例不变量：同源值的 `rdHD=64` 组与 `rdHD=0` 组实测 8 字节**逐字节相同**（每 id 两对，
  配对由 `.S` 源现场派生；三方各自成立）。
- 三方逐字节：`run_asm_suite.py --vectors tests/inst/04-arith-logic-octa
  --id ext.uo_orrr_rd --id ext.so_orrr_rd --platforms chipyard,qemu,gem5` rc=0
  （4 镜像 = 链例 2 + 故障例 2；链例各 176 B = 22 检查点 × 8）。
- **YAML**：这两个 id 在 `base/reg-shift-extend.yaml` 的旧用例（`shamt=2`/`63`）已由
  `017` 并入；本任务无新增 YAML 条目 ⇒ 无删除动作（§5.1 前置未解）。


### `m13-testcases-034`：Tiny `expected_fault` oracle 迁到 hmon 分派口径

- 用例/期望值不变：Tiny 子集 44 例（43 例 `expected_fault`）仍逐条断言同一异常
  （CFXMEM `0xF1`、UNDI `0xF9` …）；变的只是「谁产生退出码」。
- 旧口径：legacy `-bios` 短 trampoline 把 hmon 向量指到不可达地址 ⇒ QEMU 以
  「机器 fault」兜底退出码结束，测试镜像不参与。
- 新口径（`spec/Kaiwu §4.4`/`§7.1`）：镜像在触发前把落点写进固件 hmon 的
  返回槽（hmon SRAM +0xF8，`§6.2`「框架可覆盖」）；异常进入 cfx3 hmon，固件把
  `cause_id` 存到 +0xE0 后 `escape` 回落点；落点核对 one-hot 后
  `SYS_EXIT(0xF0|异常位索引)`。与 `tests/inst/macros/inst_test.inc` 的
  `.faultpad` 同一口径。
- 载体：`tools/testcases/lib/build_test_binary.py`（落点生成）；
  `make check-inst` 的 Tiny 段改用固定 64 KiB 固件（`$(TINY_BOOTROM)`）作 `-bios`。


### `m13-testcases-032`：`rootn(±0,2)=+0`、结果 NaN canonical、quiet compare sNaN 的 `NV`（YAML 向量）

- 只改**已登记**的 fp 册用例（无新载体文件、无新 `.S`）：`tests/inst/fp/{divrem,arith,scaleb,convert}.yaml`；
  `tests/case-ledger.tsv` 由 `check_case_ledger.py --write` 重生成。
- **`rootn(±0,2)=+0`**（`divrem.yaml` 新增 4 例）：`foroot`/`ftroot` 的 `−0` 与 `+0`（对照组）；
  fo 例先把目的 `rf4` 经 `ld.o` 预置 `0xDEADBEEF_DEADBEEF` ⇒ `rd5=0` 证明写满 64 位；
  ft 例把目的高 32 位预置 `0xAAAAAAAA`/`0x55555555` ⇒ `rd5` 高 32 位保持、低 32 位清 0（§1.3 单精写入宽度）。
- **结果 NaN canonical**（`divrem.yaml[26]/[27]` 的 `forem` sNaN/qNaN、`arith.yaml` 的 `ftadd`/`foadd`
  负号带 payload qNaN、`scaleb.yaml` 的 `ftsclb`/`fosclb`、`convert.yaml` 的 `fo2ft`/`ft2fo`）：
  期望一律 `0x7FF8_0000_0000_0000`/`0x7FC0_0000`（符号 0、payload 0）。**旧口径退役**：
  `forem qNaN rem 2.0` 的「payload 传播」期望（即 `divrem.yaml[23]`，`check-inst` 的既有唯一红 pin）
  按 `spec/SimRISC-07 §1.4` 改为 canonical ⇒ `make check-inst` 红集由 `{divrem.yaml[23]}` 变空。
- **quiet compare 遇 sNaN 置 `NV`**（`arith.yaml` 新增 4 例 sNaN 左/右 + 2 例 qNaN 对照）：
  两操作数经**各自** `ld.o` 装入**不同**寄存器（`rf7`/`rf9`，非重叠写序），并把两侧实际值
  `rf2rd` 到 `rd13`/`rd14` 一并断言 —— 直接防 `ISS-407` 的「左右两例机器状态相同」。
- 三平台：QEMU（`run_qemu_test.py` 全册 + `make check-inst`）、chipyard（`inst_case_run.py` 同镜像）、
  gem5（B7 探针 `--vectors`）逐例同 16 B（目的寄存器 + FCSR）字节流一致。
- 本任务不新增 `tests/inst.yaml` 条目；§1 表行不变（07 浮点册 id 数不变）。


### `m13-testcases-029`：`12-misc` 其余（`swym` + `ctlz`/`cttz`/`ctpop`，4 个 id）

- `tests/inst/12-misc/{ctlz,ctpop,cttz}_orri_rd.S` 与 `swym_oiii_imm.S`（4 个）；链接布局复用
  `01-load-store/inst-tiny.lds`；**无宏层改动**（三目 orri 用既有 `TEST_AR_ORRI`，故障例用既有
  `TEST_FAULT_ALU_ORRI`；`swym` 无操作数，用例体在 `.S` 内直接书写既有宏 `__CHECK_RD`/`__VERIFY_*`）。
- 语义要点（`spec/SimRISC-12 §3`）：`ctlz`/`cttz`/`ctpop` **无位宽后缀**，有效位宽由立即数
  `hd`（`immu6` = 有效位上界，0..63）运行时给出——参与运算的是 `rdHC[hd:0]`，`[63:hd+1]`
  **不参与**；结果 ∈ 0..64 **写满 64 位**（值语义）。定值：`rdHC[hd:0]` 全 0 ⇒ `ctlz` = `cttz` =
  `hd+1`（规范消除 UB，不是未定义值），`ctpop(0)` = 0。合法性只有 `dst_rd0`（`rdhb=rd0` ⇒ ILLI），
  **`hd` 无非法值**；`rdhc` 可为 `rd0`（读出 0）、`rdhb == rdhc`（原地）允许。
- `swym N`（`spec/SimRISC-12 §2`，oiii）：除 IP 自增（+4）外**无架构副作用**；`N` 只是硬件时延
  提示。用例以 `aip.si rb,0` 差值观测 IP（两次 `aip.si` 之间只放被测 `swym` ⇒ 差值 = 8），并核
  寄存器/内存/rb 寄存器组哨兵不变；`swym` 无合法性规则 ⇒ **无故障例**；`overlap` 类对该 id **不适用**
  （oiii 无寄存器操作数），以「插入访存序列中间」与「rb 寄存器组哨兵」等价观测替代。
- 用例：`ct*` 每 id 18 链点 + 1 故障例（encoding 2 / semantic 6 / boundary 7 / legality 2 /
  overlap 1），`swym` 13 链点（encoding 3 / semantic 5 / boundary 5）。目的初值一律全 1 ⇒
  只写低位/不清高位的实现必红（fail-closed）。合计 67 链点 + 3 故障例。
- 三方逐字节：`run_asm_suite.py`（同一份 ELF：chipyard / QEMU / gem5）7 个镜像全一致；
  结果缓冲逐点与独立复算（位循环模型）相等。
- **YAML**：`bitcnt/bitcnt.yaml`（`ctl*`/`ct*` 各 138 例）与 `base/misc.yaml`（`swym` 2 例）
  的用例已另有 `.S` 载体；两文件**未删** —— `base/misc.yaml` 里 `escape_ciii_cfx` 4 例属
  `11-cfx`，且删除受 §5.1（`inventory.md` 载体登记 + 数据覆盖门控 + 台账重生成）与根清单
  `file:` 条目阻塞，与 §5.1/§5.2 同批处理。
- GAP（不写用例、不伪造）：`swym N` 的**时延倍数/上限**属性能语义，功能层无观测点。

### `m13-testcases-012`：`01-load-store` 单元素（`ld.*` + `st.*`，19 个 id）

- `tests/inst/macros/inst_test.inc`：宏层（`TEST_LD*`/`TEST_ST*`/`TEST_FAULT`/
  `__CHECK_RD`/`__CHECK_MEM`；失败 ⇒ `SYS_EXIT(检查点号)`；结果缓冲逐字节打印）。
- `tests/inst/01-load-store/{<id>.S}`（19 个）+ `inst-tiny.lds`（固定布局，ASSERT 钉住）。
- 用例：每 id 16–18 条（encoding 2 / legality 2–5 / semantic 5 / boundary 5–6 /
  overlap 2）；四处 YAML 中属于这 19 个 id 的用例已并入（含 `reserved.yaml` 的
  reserved-cfx `CFXMEM` 6 例）。
- 三方逐字节：`tests/ee-tiny/run_inst_tiny.py` 跑 19 链例 + 49 故障例
  （同一 ELF：chipyard / QEMU / gem5），链例比较结果字节流、故障例比较 monitor
  段退出码。
- **YAML 未删**：`mem-rd.yaml`/`mem-ra.yaml`/`mem-rb.yaml` 仍含 `ldm`/`stm` id，
  `reserved.yaml` 仍含 3 条无 id 的 reserved-opcode 例 ⇒ 按本文件 §5 的删除规则，
  要等 `01-b`/`12-misc` 迁完才 `git rm`。

### `m13-testcases-013`：`01-load-store` 多元素（`ldm.*` + `stm.*`，19 个 id）

- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_LDM`（装入 → 同宽度/同组
  `stm.*` 回写 → 逐 8 字节数据单元比内联期望）、`TEST_STM`（同宽度/同组 `ldm.*` 预装 →
  存储 → 逐个数据单元比期望，期望含保持字节）、`TEST_FAULT_M`（rrri 故障例）、
  `TEST_FAULT_ENC`（汇编器拒绝的编码：`immu6=0`、组首+`immu6>64`）。
  一行 = 一个检查点（宏内单次 `__REC`），点号仍 = 用例序号。
- 数据区新增（`.testdata`，与单元素用例的 0x000–0x0E8 区不重叠）：`MDATA_B/W/T/O`
  （逐元素可辨）、`MUNI`（同值数据单元，最大个数例）、`MDUMP`（装入回写落点）、
  `MSTORE`（存储落点 + 保持区模式）。`.testdata` 0x1000→0x2000、结果缓冲
  0x3000→0x4000、退出参数块 0x4000→0x5000（`inst-tiny.lds` ASSERT 同步）。
- 用例：每 id 13–21 点；多元素例 `count>1` 占多数（1/2/3/8/9/16 与 63；63 只出现在
  `ldm.o_rd`/`ldm.ub_rd`/`ldm.o_ra`/`ldm.o_rf`）；`stm.b` 9 元素 = 2 个数据单元且第二个数据单元只写
  1 个字节；存储例都带左右保持区核对；`ldm` 抽样元素用 `__CHECK_RD` 独立核对。
- 故障：`immu6=0`/组首+`immu6>64`/目的 rd0·rb0/`ldm` 重叠 ⇒ ILLI；`MALIGN`；
  CFXMEM 三形态（cfxha 0 段、整段越 SRAM 尾、保留 cfx 段）。
  **多元素不要求无副作用**（用户 2026-11-13 裁定：允许部分元素已生效）⇒ 故障例**只比异常码**，
  不判目的寄存器/目标内存；「中途访存 denied」在 Tiny 不可构造（`ISS-381` F-c）。
- **overlap**（规范 `SimRISC-01` + `mreg_range_addr_overlap`，`m13-spec-005` 定稿）：`ldm` **禁重叠**
  —— RD 形式索引 `rdHC`、RB 形式基址 `rbHB` 落在传送范围内 ⇒ ILLI；`stm` **允许重叠**（只读，
  行为确定）⇒ 正常执行并核源组未被改写；RA/RF 形式结构上不可能相交 ⇒ 不适用。
  实现进度：QEMU（`m13-qemu-006`）/ gem5（`m13-gem5-008`）已合入；chipyard 待 `m12-chipyard-027`。
- **`immu6=63` 的索引选择**：RD 形式的 `{rd1:rd63}` 已把 RD 组占满，索引只能用 `rd0`
  （rd0 读出 0 ⇒ EA = 基址）；用 `rd19` 会落进传送范围 ⇒ ILLI（`mreg_range_addr_overlap`）。
- 三方逐字节：`run_asm_suite.py`（同镜像 chipyard / QEMU / gem5）链例比字节流、
  故障例比 monitor 段退出码；故障例走 BootROM **固件** hmon（写 `0xF8` 返回槽、
  读 `0xE0` cause_id），三方固件自 `m12-chipyard-028` 起同版，不再自装处理器（`ISS-410` 已修）。
- **YAML**：三册里 30 个 id（含 `012` 的 19 个单元素 id）全部有 `.S` 载体；文件
  删除被 §5.1 的前置阻塞，未删。

### `m13-testcases-014`：`02-reg-copy`（块复制 + `cs.*`，16 个 id）

- `tests/inst/02-reg-copy/{<id>.S}`（16 个）：8 个块复制（`rd2rd`/`rb2rb`/`rb2rd`/`rd2rb`/
  `ra2rd`/`rd2ra`/`rd2rf`/`rf2rd`）+ 5 个 `cs.*_rrrr_rd` + 3 个 `cs.*_rrrr_rf`；
  链接布局复用 `01-load-store/inst-tiny.lds`（段地址由宏层固定，见该 .lds 头注释）。
- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_MOV1`（单寄存器块复制）、
  `TEST_CS1`/`TEST_CS2`/`TEST_CS1_RF`（条件赋值）、`TEST_FAULT_MOV`/`TEST_FAULT_CS`/
  `TEST_FAULT_CS2`（故障例）、`__VERIFY_RD`/`__VERIFY_MEM`/`__VERIFY_EQ_RD`（同判据但
  **不占检查点**，一个用例可含多条断言）、`__SET_MEM`（RDATA → ra/rf 的装载通路）。
- **探针不借被测指令**：目的在 rd 直接比；在 rb/ra/rf 用**同组 `st.o`** 落到
  `SCRATCH`（`TEST_DATA+0x1400`）再逐字节比 —— 期望不依赖另一条复制指令。
  ra/rf 初值只能经内存给（`set.zw`/`or.w` 无 ra/rf 形式）⇒ `RDATA`（`TEST_DATA+0x1300`，
  16 个 8 字节数据单元字面量）；`+0x70` 的 `[63:54]=0` 值专供 `ra0` 作目的。
- **覆盖**：每 id 15–17 点；块复制含 encoding（助记符 + 规范编码字 `.dd.t32`）、
  semantic（1/2/3/7 元素、源含 0 号寄存器）、boundary（组顶端、最大个数：同组 31 /
  跨组 63）、legality（`dst_rd0`/`dst_rb0`、`immu6=0`、两侧 `起始+immu6>64`）、
  overlap（`rd2rd`/`rb2rb` 部分交错与完全重合 ⇒ ILLI；跨组同号合法）。
- **`cs.*` 的 C-27**：条件/候选与目的**同名**的别名语义仍 deferred（`inventory.md`）⇒
  用例一律不同名，「未被选中侧不被改写」用 `__VERIFY_*` 断言；`rf0` 作目的只断言
  「不触发 ILLI」（FCSR 掩码写内容不断言），`rf0` 作源用「与当前 `rf0` 相等」断言。
- **YAML**：`base/reg-cond-assign.yaml`（5 个 rd 变体）、`base/reg-imm-block.yaml` 的 6 个
  复制 id、`fp/cond-assign.yaml`（3 个 rf 变体）的用例均已有 `.S` 载体（`rd2rf`/`rf2rd`
  原本无 YAML 载体）。
  三文件**未删**，实测阻塞（`cp`+md5 备份后 `mv` 走再逐门控跑，随后还原）：
  `reg-cond-assign.yaml` ⇒ `validate_vectors` rc=1（**15 gap**）、`check_case_ledger`
  rc=1（多 25 行）、`check_tests_index` rc=1（`file` 不存在）、`generate_isa_vectors
  --check` rc=1（missing）；`fp/cond-assign.yaml` ⇒ `check_case_ledger` rc=1（多 6 行）、
  `check_tests_index` rc=1、`generate_isa_vectors --check` rc=1、
  `semantics_gate --check-only` rc=1（缺册 + 门控覆盖表登记不符）。⇒ 与 §5.1 同批处理。

### `m13-testcases-015`：`03-wyde-imm`（16 位立即数操作，8 个 id）

- `tests/inst/03-wyde-imm/{<id>.S}`（8 个）：`set.zw`（rd/rb）、`set.ow`（rd）、
  `or.w`（rd/rb）、`andn.w`（rd/rb）、`set.w`（rf）；链接布局复用
  `01-load-store/inst-tiny.lds`（段地址由宏层固定）。
- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_WI_{RD,RB,RF}`（一行一个用例、
  期望内联）、`TEST_WI_{RD,RB,RF}_MEM`（期望**从 WDATA 装载**的独立 oracle ——
  `__LI` 自身用 `set.zw`/`or.w` 拼常量，故这组变体防「期望由被测指令自证」）、
  `TEST_WI_RF0_NOOP`/`TEST_WI_RF0_WRITE`（rf0 的 FCSR 写掩码，见下）、
  `TEST_FAULT_WI`（`dst_rd0`/`dst_rb0` ⇒ ILLI）。数据区新增 WDATA（`+0x1500`，
  16 个 8 字节数据单元）/ WSCRATCH（`+0x1580`，rf0 例的前/后 8 B）。
- **探针不借被测指令**：目的在 rd 直接比；在 rb/rf 用同组 `st.o` 落到 SCRATCH
  再逐字节比。初值：rd 用 `set.rd`、rb 用 `set.rb`、rf 用 `set.fo`（整 64 位；`m15-testcases-006` 起装载一律用规范伪指令）。
- 用例：每 id 14 点（encoding 2 / semantic 5 / boundary 6 / overlap 1），`set.w` 17 点
  （多 3 点 rf0 写语义：wp1/wp3 写无效、wp2/wp0 只管各自可写域）+ 故障例 1；
  `set.w_rwii_rf` 无合法性规则（`spec/SimRISC-03 附录 B`）⇒ **无故障例**。
  16 位立即数分片按 `wp0`..`wp3` 全覆盖；`immu16` 取 0 / `0xFFFF` / `0x8000` /
  最小非零 / 最大正 15 位等边界；`set.zw` 另钉「高 16 位归零」（rb 地址溢出检测用法）。
- **rf0（FCSR）写语义**：wp2 立即数的**低 2 位**命中 `[33:32]`（舍入模式）、
  wp0 的低 5 位命中 `[4:0]`（异常状态），其余位写无效（写掩码
  `0x000000030000001F`，QEMU/chipyard/gem5 实测一致）。用例前置把该域清 0，
  期望 = 写前值对应字节 + 增量 ⇒ 若实现忽略了「写无效」位，断言必红（fail-closed）。
- 三方逐字节：`run_asm_suite.py`（同一份 ELF：chipyard / QEMU / gem5，15 个镜像 =
  链例 8 + 故障例 7）。
- **YAML**：`base/reg-imm-block.yaml` 的 7 个 rwii id 用例已并入
  （`set.w_rwii_rf` 原本无 YAML 载体）；文件**未删**（§5.1 前置未解）。

### `m13-testcases-016`：`04-arith-logic-octa` 算术族（15 个 id）

- `tests/inst/04-arith-logic-octa/{<id>.S}`（15 个）：6 个双目的 rrrr（`add/sub/mul` 的
  `.uo`/`.so`）+ `add.si`（riii）+ 2 个 rrii（`cmp.ui`/`cmp.si`）+ 6 个单目的 orrr
  （`cmp`/`div`/`rem` 的 `.uo`/`.so`）；链接布局复用 `01-load-store/inst-tiny.lds`。
- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_AR_DUAL`（双目的：高半
  `__VERIFY_RD` + 低半 `__CHECK_RD`，共用点号）、`TEST_AR_ORRR`/`TEST_AR_SI`/`TEST_AR_CMPI`、
  `TEST_FAULT_{DUAL,ALU3,ALU_SI,ALU_CMPI}`（`dst_dual_same` / `dst_rd0` ⇒ ILLI）。
  **rd0 一律不装载**（写 rd0 会 ILLI）；双目的中为 rd0 的那一半不比对，点号落在另一半。
- 语义要点（`spec/SimRISC-04 §1`）：`add.uo`/`sub.uo` 的 `rdHA` 是**进位/借位 0/1**
  （不是 128 位高位）；`.so` 变体 `rdHA` = 符号扩展高 64 位；`div.*`/`rem.*` 的除零与
  `INT64_MIN ÷ −1` 走**定值表**（不触发异常）；`cmp.*` 结果 −1/0/1 写满 64 位。
- 用例：每 id 14–15 链例 + 1–2 故障例（encoding 2 / semantic 4–7 / boundary 5–6 /
  overlap 3）；覆盖进位·借位·跨符号·最值·双目的丢弃·源=目别名·两源同名，
  以及 `div`/`rem` 的除零、溢出定值与 `cmp` 的零扩展/符号扩展立即数。
- 三方逐字节：`run_asm_suite.py`（同一份 ELF：chipyard / QEMU / gem5，36 个镜像 =
  链例 15 + 故障例 21）。
- **YAML**：`base/reg-arith.yaml`（11 个 id）与 `base/reg-compare.yaml`（4 个 id）的用例
  已并入；两文件仍含其它宽度 id，**未删**（按 §5 删除规则等 024/025/026 迁完）。

### `m13-testcases-017`：`04-arith-logic-octa` 逻辑/移位/扩展族（14 个 id）

- `tests/inst/04-arith-logic-octa/{and.o_orrr_rd,or.o_orrr_rd,xor.o_orrr_rd,xnor.o_orrr_rd,
  shl.o_orrr_rd,shl.o_orri_rd,shr.uo_orrr_rd,shr.uo_orri_rd,shr.so_orrr_rd,shr.so_orri_rd,
  ext.uo_orrr_rd,ext.so_orrr_rd,ext.uo_orri_rd,ext.so_orri_rd}.S`（14 个）；链接布局复用
  `01-load-store/inst-tiny.lds`。
- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_AR_ORRI`（orri 移位/扩展：目的/源C/
  immu6）、`TEST_FAULT_ALU_ORRI`（orri 的 `dst_rd0`）。驱动器 `run_asm_suite.py` 的
  `FAULT_AR_RE` 增补 `ALU_ORRI`。
- 语义要点（`spec/SimRISC-04 §2`）：`and`/`or`/`xor`/`xnor` 全 64 位逐位运算；`xnor` 的源
  为 rd0（读出 0）时得到**另一源的按位取反**（规范明示的 not 用法）；`shl.o`/`shr.uo`/`shr.so`
  的移位量取 `rdHD[5:0]`（寄存器形式）或 `immu6`（立即数形式），**64 与更大值只取低 6 位、
  不触发 ILLI**；`ext.uo/ext.so` 的起始位同口径 —— orrr 的 `hd = rdHD[5:0]`（低 6 位、
  越界位忽略、**不抛 ILLI**；用户裁定 2026-11-13），orri 的 `immu6` 是 6 位域天然满足。
- **QEMU/gem5 缺陷 `ISS-422`（未收录为用例，待修）**：`ext.*` orrr 的 `rdHD = 64`（hd 越界）
  实测 chipyard 按裁定口径 `hd = rdHD[5:0] = 0` 执行（**正确**），QEMU/gem5 判 ILLI（0xF8）
  ⇒ 判 ILLI 一侧是缺陷。`.S` 里只保留注释说明、不写故障例；QEMU/gem5 修好后补 `TEST_FAULT`
  一例（任务书「待裁定」1）。`spec/SimRISC-04 §2.2` 的「hd ≤ N 否则 ILLI」措辞待 spec 任务修正。
- 用例：每 id 12–16 链例 + 1 故障例（encoding 2 / semantic 5–6 / boundary 3–5 / overlap 1–3）；
  覆盖 0/1/31/32/62/63 边界、移位量 64 的掩码、`immu6=0` 合法、ext 起始位 0 与 63、
  符号扩展按 `rdHC[hd]` 取值、源=目与两源同名。
- 三方逐字节：`run_asm_suite.py`（同一份 ELF：chipyard / QEMU / gem5，28 个镜像 =
  链例 14 + 故障例 14）。
- **YAML**：`base/reg-logic.yaml`（4 个 id）与 `base/reg-shift-extend.yaml` 的 10 个 64 位 id
  用例已并入；`reg-logic.yaml` 的 id **全部已迁**，但文件**未删**（§5.1 前置：删后
  `validate_vectors` 数据覆盖出现 gap），`reg-shift-extend.yaml` 仍含 32/16/8 位 id。

### `m13-testcases-018`：`04-arith-logic-octa` 位操作族（4 个 id）

- `tests/inst/04-arith-logic-octa/{rev.o_orri_rd,rol.o_orri_rd,rol.o_orrr_rd,
  clmul.o_rrrr_rd}.S`（4 个）；链接布局复用 `01-load-store/inst-tiny.lds`。
- 复用 `016`/`017` 的宏层：单目的 orri/orrr 用 `TEST_AR_ORRI`/`TEST_AR_ORRR`，双目的
  `clmul.o` 用 `TEST_AR_DUAL`（高半 `__VERIFY_RD` + 低半 `__CHECK_RD`），故障例用
  `TEST_FAULT_ALU_ORRI`/`TEST_FAULT_ALU3`/`TEST_FAULT_ENC`（**无宏层改动**）。
- 语义要点（`spec/SimRISC-04 §2.2.1/§2.2.2/§1.5`）：`rev.o` 把 64 位切成 `64/k` 个
  `k` 位单元倒序（k=8 ⇒ bswap64、k=1 ⇒ bitreverse64），k 须 one-hot 且 k<64；`rol.o`
  是 64 位循环左移，orrr 的旋转量取 `rdHD[5:0]`（64/65 只取低 6 位、**不触发 ILLI**），
  orri 的 `immu6 = 0..63` 全部合法；`clmul.o` 是 GF(2) 无进位乘（128 位高/低半），
  两个目的不得同为 rd0、也不得同号，单半丢弃合法，源先读后写。
- 用例：`rev.o` 13 链例 + 4 故障、`rol.o` orri 12+1、orrr 14+1、`clmul.o` 19+2
  （encoding / semantic / boundary / overlap 五类；点号 1..N 连续）。
- 三方逐字节：`run_asm_suite.py`（同一份 ELF：chipyard / QEMU / gem5，12 个镜像 =
  链例 4 + 故障例 8；故障例全 `0xF8` ILLI）。
- **YAML**：`rev/rev.yaml` 的 `rev.o`（16 例，含全部非随机类例）、`rol/rol.yaml` 的
  `rol.o` 两形式（17 例）已并入；`clmul/clmul.yaml` 的 `clmul.o`（81 例，其中 60+ 为
  满宽随机 semantic）取全部非随机类例 + 2 例随机代表（19 点）——`.text` 上限
  `0x1E00`（`.lds` ASSERT）不容纳 81 个双目的检查点。三文件均**未删**：`rev`/`rol`
  仍含 32/16/8 位 id，`clmul.yaml` 是 `make check-inst` 的 L3 载体（§5.1）。
### `m13-testcases-019`：`05-arith-addr`（64 位地址运算，6 个 id）
- `tests/inst/05-arith-addr/{add.o_orrr_bbd,sub.o_orrr_bbd,cmp.uo_orrr_dbb,sub.o_orrr_dbb,
  add.si_riii_rb,aip.si_riii_rb}.S`（6 个）；链接布局复用 `01-load-store/inst-tiny.lds`。
- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_AR_BBD`（目的 RB、源 = RB + RD）、
  `TEST_AR_DBB`（目的 RD、两源 RB）、`TEST_AR_RB_SI`（riii rb，目的兼源）；
  故障宏 `TEST_FAULT_{BBD,DBB,RB_SI}`（`dst_rb0` / `dst_rd0` ⇒ ILLI）；驱动器
  `run_asm_suite.py` 的 `FAULT_AR_RE` 增补这三个名字。**目的只写不读** ⇒ 不装初值；
  目的在 RB ⇒ 同组 `st.o` 落 SCRATCH 再 `__CHECK_MEM`。
- 语义要点（`spec/SimRISC-05`）：`add.o`/`sub.o`（bbd 与 dbb 两形态）与 `add.si` 都是
  **全 64 位二进制补码**加减、**不做地址截断**（`[63:48]` 只是地址溢出指示，仅访存时取 `[47:0]`）；
  `cmp.uo` 是**整 64 位无符号**比较（`bits[63:48]` 参与）⇒ 0x0000FFFF.. < 0x0001_0000_0000_0000，
  只比低 48 位会判「相等」；`aip.si` 的 `IP` = **该指令自身地址**（非下一条、无 ±4、低位不清零），
  立即数按 4 KiB 块（汇编层字节、编码层 `>>12`）。
- **`aip.si` 的链接期期望值**：llvm-mc 只把**绝对常量**表达式折进指令立即数，标签差
  （`. - _start`、`L1 - L0`）在立即数里被**静默折成 0**（本任务现场实测，`__LI`/`set.zw`
  均如此，无诊断）⇒ 该文件把 `aip.si` 用 `.org 0x200` 钉在 `ENTRY+0x200` 起的连续 4 B 槽
  （`jump` 跳过填充的零字），期望一律写 `ENTRY + <字面偏移>`。**不要**在本仓其它 `.S` 里
  用标签算术造立即数（会得到 0 而静默失败）。
- 用例：每 id 11–13 链例 + 1 故障例（encoding 2 / semantic 3–5 / boundary 3–6 / overlap 2）；
  覆盖 `[63:48]` 参与的比较、跨 2^64 进位/借位、48 位边界内的进位与借位、立即数 ±上下界、
  `rd0` 作源、源=目（bbd）与同源（dbb）、`aip` 的 IP=自身/`<<12`/低位不清零/同目的连写。
  链例 6 + 故障例 6）。
- **YAML**：`base/aip-si.yaml`（1 个 id）的 12 条用例、`base/reg-arith.yaml` 的
  `add.o_bbd`/`add.si_riii_rb`/`sub.o_bbd` 与 `base/reg-compare.yaml` 的 `cmp.uo_orrr_dbb`
  用例已并入（`sub.o_orrr_dbb` 无 YAML 载体）；三文件**未删** —— `aip-si.yaml` 的 id 虽
  全迁，删除仍受 §5.1 前置阻塞，另两文件仍含 32/16/8 位 id。

### `m13-testcases-020`：`06-control-flow`（`br.*`/`jump`/`call`/`ret`，15 个 id）

- `tests/inst/06-control-flow/{<id>.S}`（15 个）：`br.*` 10 个（`eq`/`ne` 的 rrii，
  `n`/`nn`/`z`/`nz`/`p`/`np` 的 riii-rd，`z`/`nz` 的 riii-rb）+ `jump` 2 + `call` 2 +
  `ret` 1；链接布局复用 `01-load-store/inst-tiny.lds`。
- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_BR2`（rrii 条件分支）、
  `TEST_BR1`/`TEST_BR1_RB`（riii rd/rb）、`__LAND_IP`（落点 IP 捕获：`aip.si rb24, 0`
  + `rb2rd` ⇒ 期望可写成 `ENTRY + <字面偏移>`）、故障宏 `TEST_FAULT_CF`/`CF1`
  （原始编码）、`TEST_FAULT_BR1/BR2`（目标不可取指 ⇒ UNDI）、`TEST_FAULT_RAS`
  （建立 RA 状态后执行 call/ret ⇒ RASOF/RASUF）、`TEST_FAULT_RASUF_MEM`（D4b）、
  `TEST_FAULT_ADDR0`（rrii 目标地址 0 ⇒ CFXMEM）。`__FAULT_GUARD` 增
  UNDI `0xF9` / RASOF `0xFA` / RASUF `0xFB`；数据区新增 `MEMRAS`（`TEST_DATA+0x1700`）。
  驱动器 `run_asm_suite.py`：`FAULT_CODE` 增三类、新增 `TEST_FAULT_CF1`/`_BR1/2`/
  `_ADDR0`/`_RAS`/`_RASUF_MEM` 的行识别、链例行识别增 `TEST_BR*`。
- **跳转距离/落点**：条件分支与 `jump` 的「距离」用例把被测指令用 `.org` 钉在固定槽位，
  目标用**字面字节偏移**（如 `+0x800` / `-0x420` / `+0xEC0`），落点用 `__LAND_IP` 捕获后
  与 `ENTRY + <槽位偏移>` 比对 ⇒ 同时钉住「目标计算」与「落点地址」。`br.rrii` 的立即数
  只有 ±8 KiB（够不到 Tiny 的 8 MiB SRAM 边界）⇒ 越界目标只能落在 SRAM 内的非代码区
  （零字 ⇒ UNDI）；`br.riii`（±512 KiB）、`jump`（±32 MiB）用 CFXMEM 覆盖越界方向。
- **RAS**：`call` 的压栈按 C1/C2/C3a 覆盖（冷栈、同返回地址的递归折叠、异地址压栈并
  把旧顶下移 `ra62`），`ret` 按 D2/D3（计数 > 1 只减计数、= 1 弹栈）与 D4a/D4b
  （MRPTR = 0 / MemRAS 条目计数 0 ⇒ RASUF）覆盖；`RACNT` 与 `MRPTR` 都在 `ra0`
  （`[53:48]` / `[47:0]`），用例用 `rd2ra` 全 64 位写建立状态、`ra2rd` 只读观测。
  返回地址一律核「`call` 地址 + 4」与递归计数（1 或 2）。
- 故障例：`dst_rd0_nonzero`（`ret rd0, 1` / `ret rd0, -1` ⇒ ILLI，汇编器拒绝故给编码字）、
  RASOF（C3b）、RASUF（D4a、D4b）、CFXMEM（`br.riii`/`jump`/`call` 越界目标、
  rrii 目标地址 0）、UNDI（`br.eq`/`br.ne` 落到零字）。
- 三方逐字节：链例比结果字节流、故障例比 monitor 段退出码；**同一份 ELF** 在 chipyard /
  QEMU / gem5 上 34 个镜像全一致（含 `0xF1`/`0xF8`/`0xF9`/`0xFA`/`0xFB` 五种故障码）。
- **独立复算**：`oracle` 是自写的 Tiny 子集解释器（控制流 + 宏层用到的指令 + RAS
  压/弹流程），逐检查点把实测值与内联期望比对（194 点），并把结果字节流与三平台输出
  逐字节比对；`encode_check` 另核原始编码字的 `opc`/`mask`/`value` 与「编码字段 ↔
  装载寄存器」一致。
- **YAML**：4 个 ctrl 册的 id 全部有 `.S` 载体，但**未删**（§5.2 的四条阻塞实测）。

### `m13-testcases-031`：补 `st.o rb0` / `ld.o ra0`（`01-load-store` 三文件）

- 改动（**不改已通过用例**，只追加段）：`st.o_rrii_rb.S`（+3 链例点，`rb0` 作**源** =
  当前指令地址）、`st.o_rrii_rd.S`（+1 点，`rb0` 作**基址**，该 id 的源寄存器组是 rd ⇒ 只有
  `rbhb` 能编 `rb0`）、`ld.o_rrii_ra.S`（+7 点 = `ra0` 读 4 + 写 3）；故障例点号顺延。
  宏层新增 `__CHECK_MEM_RB`（内存数据单元 vs **运行期派生**的 RB 期望：先 `rb2rd` 到 rd22 再比）；
  驱动器 `run_asm_suite.py` 的链例行识别放宽为 `__CHECK_(?:RD|MEM)\w*`。
- **`rb0` 期望值**：`llvm-mc` 只折装绝对常量（标签差折 0，`ISS-424`）⇒ ①`aip.si rbX, 0`
  + `add.si rbX, <delta>`；②`rb2rb rbX, rb0, 1` + `add.si rbX, <delta>`；③`.org` 钉住
  被测指令后写 `ENTRY + <字面偏移>`。**`delta` = 被测指令与取指指令的字节差**（相邻即 4；
  本册 `aip.si`/`rb2rb` 后隔一条 `add.si` ⇒ 8，注释逐条写清）。`rb2rb`/`aip.si` 的地址
  差用 ELF 反汇编核算（oracle），写错 delta 必红。
- **`rb0` 作基址**（`st.o_rrii_rd`）：EA = 本条 `st.o` 地址 + imms12 ⇒ 目标只能落在
  `.text` 内；用例用 `.org` 留出**被 `jump` 跳过的零填充槽**（只写不执行），两侧都是链接期
  常量。三平台一致（写 RAM 无只读保护）。
- **`ra0` 读写**：写 = `ld.o ra0, [rbX, imm]` 装入含 SBZ 置位的值（源值就地 `st.o` 预置，
  不新增数据区字节——`.testdata` 恰 0x2000 已满），`ra2rd` 读回，`[63:54]` 必须为 0；
  读 = `call`（C1/C3a）、满栈 `call`（C3b ⇒ MRPTR −= 8）、`ret`（D4b ⇒ MRPTR += 8）构造
  已知 `RACNT`/`MRPTR` 后 `ra2rd` 拷出。**顺序先读后写**：写段是三平台分歧点（见下）。
- **跨平台分歧（issue 候选号见 `m13-testcases-031` 任务书「遗留问题」）**：`ld.o ra0` 的 `[63:54]`（SBZ，`SimRISC-00 §2.4` 规定写无效）
  chipyard（RTL `WumingRegFile.writeRa` 丢弃 SBZ、读回恒 0）**绿**；QEMU/gem5 **全 64 位
  可写**（读回保留写入位）⇒ 点 20（第一例）红。期望**不放宽**，红按文档化处理。
  读段（16–19 点）三平台一致。
- **独立复算**：`oracle.py`（自写）= ELF 反汇编取指令地址（`rb0` 期望 + delta 核算）+
  自写 RAS 状态机（C1/C2/C3a/C3b、D1–D4b ⇒ `ra0` 两字段）+ SBZ 掩码；并把派生期望与
  三平台结果字节流逐点比对。
- **门控**：`.S` 不入 `check-inst`（YAML 载体）⇒ `check-inst` 红集仍**恰**
  `{divrem.yaml[23]}`；`check-tests-index`/`check-case-ledger`/`validate_vectors`/
  273 例 sweep md5/`check-generator-sync` 全绿。

### `m13-testcases-021`：`07-floating-point` 算术与最小最大（18 个 id）

- `tests/inst/07-floating-point/{<id>.S}`（18 个）：`foadd/fosub/fomul/fodiv/forem`、
  `ftadd/ftsub/ftmul/ftdiv/ftrem`、`fofma/ftfma`、`fomin/fomax/ftmin/ftmax`、`foroot/ftroot`；
  另有 `inst-tiny-fp.lds`（**本册专用布局**：`.text` 0x0000–0x4000 / `.faultpad` 0x4000 /
  `.testdata` 0x5000–0x7000（`TEST_DATA` = +0x5800）/ 结果缓冲 0x7000 / 退出块 0x7800；
  01 册的 `.text` 已用到 0x1E00，浮点册每条用例更长，故另起布局）。
- 宏层（`tests/inst/macros/inst_test.inc`；`m15-testcases-006` 起**单一 FP 布局**，
  原「浮点册走独立布局」的切换分支已删除，段址由 `linker/inst-tiny.lds` 一处钉住）：
  `TEST_FP3`（orrr 双源）/
  `TEST_FP4`（fma 三源）/`TEST_FPROOT`（orri）/`TEST_FPENC*`（原始编码字）/`TEST_FAULT_FP`；
  `__FP_ENV` 清 `rf0[4:0]` 并按参数设 `rf0[33:32]`，`__FP_CHECK` **先断言标志**再比结果
  （共用点号；期望标志 NV=1/DZ=2/OF=4/UF=8/NX=16）。初值一律 `set.fo`（按需先 `set.rd`+`rd2rf` 的场合仅限被测伪指令自身），不借浮点指令；
  ft 只比低 32 位（高 32 位不作规定）。
- 用例：链例 318 + 故障例 20（每 id 16–21 链例 + 1–2 故障；encoding 2 / semantic 4 / boundary 6 /
  overlap 2 为骨架）。覆盖：五类标志全部至少一条；RNE/RTZ/RDN/RUP 四档（含 `1.0±2^-25`
  中点、`1/3`、`sqrt(2)`、溢出形态 ±Inf 与 ±max）；canonical qNaN 与 sNaN⇒NV（含
  `qNaN rem 0`/`qNaN×0` 不置 NV 的优先级、`0×Inf+qNaN` 置 NV）；±0 的加减零符号随 RDN、
  min/max 的 `-0<+0` 定序、`rootn(±0)=+0`；次正规精确（不置 UF）与 tiny+inexact（UF|NX）；
  `forem/ftrem` 的 IEEE 余数（平局取偶、符号随被减数、除零是 NV 不是 DZ、qNaN 传播按 §1.4 取 canonical 而非 payload —— 与既有 `divrem.yaml[23]` 的旧口径相反，该例即 `check-inst` 的既有红 pin）；`fofma/ftfma`
  单次舍入反例（`(1±2^-23)(1∓2^-23)−1`）与溢出；root 的负数/±Inf⇒NV、n≠2⇒ILLI。
- 三方逐字节：`run_asm_suite.py`（同一份 ELF：chipyard / QEMU / gem5）38 个镜像全绿 ——
  链例比结果字节流、故障例比 monitor 段退出码（20 例全 `0xF8` ILLI：目的 rf0 / root 的 n≠2）。
  故障例走 BootROM **固件** hmon（写 `0xF8` 返回槽、读 `0xE0` cause_id），三方固件同版。
- **YAML**：`fp/divrem.yaml` 的 6 个 id 全部有 `.S` 载体，但文件**未删**（它是 `check-inst`
  的 L3 载体，且 §5.1 前置未解）；`fp/arith.yaml` 的 8 个 id 已并入（余 4 个比较 id 待 022）；
  `fosub`/`ftadd`/`ftsub`/`ftmax` 原本无 YAML 载体。

### `m13-testcases-022`：`07-floating-point` 转换/比较/分类（26 个 id；现存 24）

- `tests/inst/07-floating-point/{<id>.S}`（26 个）：转换 18（`ft2it`/`ft2io`/`ft2ut`/`ft2uo`、
  `fo2it`/`fo2io`/`fo2ut`/`fo2uo`、`it2ft`/`io2ft`/`ut2ft`/`uo2ft`、`io2fo`/`uo2fo`、
  `it2fo`/`ut2fo`、`fo2ft`、`ft2fo`）+ 块复制 2（FT 与 FO 各自的同组复制；`m13-testcases-047`
  起并入 `02-reg-copy/rf2rf_orri_rf.S`，本册不再有同组复制载体）+ 分类 2（`ftcls`/`focls`）
  + 比较 4（`ftqcmp`/`ftscmp`/`foqcmp`/`foscmp`）；链接布局复用 `inst-tiny-fp.lds`。
- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_FPCVT_{F2I,I2F,F2F}`（源在 rf/rd、
  目的在 rd/rf 三种几何）、`TEST_FPCVT_ENC_{RD,RF,F2F}`（原始编码字）、
  `TEST_FPCMP`/`TEST_FPCMP_ENC`（比较：无序（任一操作数 NaN）结果一律 canonical quiet NaN，
  直接钉整 64 位 —— `m15-testcases-020` 起 signaling 与 quiet 的差别只剩 `NV`；原先
  signaling 专用的「符号/指数/尾数结构断言」宏已随 spec 订正删除）、
  `TEST_FPCLS1..4`/`_ENC1`/`_RF0`/`_IDX`/`_TOP4`、`TEST_FPCOPY1..4`/`_ENC2`/`_TOP4`/`_TOP1`/
  `_31`/`_ADJ`/`_RF0`、`__FP_CHECK_RD`、`__CHECK/_VERIFY_FP_RF`、`__CHECK/_VERIFY_FP_RF_MEM`。
  三个转换宏把「`immu6` 六档方向」与「`rf0[33:32]`」拆成两个参数 ⇒ 可直接断言
  「静态档不受 `rf0` 影响」（§1.1）。
- 语义要点（`spec/SimRISC-07 §1/§4/§5`）：`immu6` 三套语义互斥（六档 one-hot / SBZ=0 /
  复制个数）；浮点→整数「有限且取整在范围内 ⇒ inexact 置 NX」，NaN/Inf/越界 ⇒ 饱和 + NV
  且**不置** NX；整数→浮点本任务值域不产生 OF/UF（`2^64 < ft_max`、整数 ≥ 1）；
  `fo2ft` 溢出结果形态只由方向决定（RNE/RNA ⇒ ±Inf，RTZ ⇒ ±max，RUP 正/RDN 负 ⇒ ±Inf），
  轻微溢出（无界指数舍入仍回到 max）**只置 NX**；下溢按 tiny∧inexact 置 UF|NX；
  NaN 结果一律 canonical qNaN（`fo2ft`/`ft2fo`/quiet compare）；复制类不改位、不置标志；
  分类结果只占 `[9:0]`，`ftcls` 只看源**低 32 位**。
- 用例：链例 **493** + 故障例 84（每 id 12–30 链例 + 1–5 故障；encoding 2 / semantic 3–9 /
  boundary 4–20 / overlap 1–2 为骨架）。覆盖：六档方向（RNE/RNA/RTZ/RUP/RDN + 动态档，
  含「`2.7` 非平局四方向」「`2.5` 平局」「静态档忽略 `rf0`」）、`±0`/`±Inf`/`qNaN`/`sNaN`
  （含**负号 NaN**：转换饱和取 max、比较取 canonical qNaN）、ties（`2.5`、`2^24+1`、`2^53+1`）、
  目标整型四宽度的最值/越界、`ft` 次正规与最小正规、`fo2ft` 四方向溢出 + 轻微溢出 + `f64` 最大有限
  RTZ、`±ft_max`、**下溢三类**（`2^-150 RNE → +0`、`-2^-150 RTZ → -0`、`1.5×2^-149 → 2^-149`
  非零次正规 + UF|NX，以及 `2^-149`/`2^-126` 的 tiny 但精确 ⇒ 不置 UF/NX）、复制 1/2/3/4
  与 31 个元素（`{rf1:rf31} ← {rf32:rf62}`，逐元素核「目的 == 源内存」）、寄存器窗口顶端
  （起始 60 + 4 = 64）、`rf0` 作源（复制/分类）、分类十类位掩码与 `[63:10]` 清零。
- 故障例（84）覆盖 `dst_rd0`/`dst_rf0`/`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`/
  `encode_onehot`/`encode_sbz`，全部经原始编码字（汇编器会拒绝的编码）⇒ 期望 `0xF8` ILLI。
- **`ft` 目的写入的高 32 位**：受控探针（7 检查点，目的寄存器先写满 64 位已知值）在**当前
  master 构建**上三方**逐字节一致**（md5 `e33e7b65c2f2b6b6ff9bd9d6bcca427c`）：当时的 FT
  同组复制载体与 `fo2ft` **只写低 32 位、高 32 位保留**（FT 同组复制已被
  `m13-testcases-047` 的 `rf2rf` 取代：后者是**整 64 位**位型复制），`ft2fo` 写满 64 位。
  同一探针在早先的旧构建（QEMU/RTL）上是**整 64 位搬移**（gem5 仍为低 32 写）⇒ 该行为属
  `contract-fp §1` 的「高 32 位不作规定」，且在构建间变过 ⇒ `ft` 目的用例只比低 32 位、
  **不计红**；`contract-fp §1` 与「复制类 64 位二进制不变」措辞冲突，建议 spec 收窄
  （见任务书「新发现/坑」；`rf2rf` 已按 `SimRISC-02 §1` 明确为整 64 位复制）。
- **YAML 逐条并入**（`fp/convert.yaml` 15 例 + `fp/arith.yaml` 15 例，共 30 条操作数全部有
  对应 `.S` 用例）：`convert.yaml` ⇒ `ft2it` 的 `2.7f` 四方向（RTZ/RNE/RUP/RDN）+ 负号 `-2.7 RTZ`
  + 动态档 RTZ + `2^31 越界 ⇒ INT32_MAX+NV` + `RNA 2.5` + `immu6=3 ⇒ ILLI`；`fo2io` 的
  `2.7 RNE`；`io2ft` 的 `2^24+1` 在 RUP 与动态 RTZ 下两例；`ut2fo` 的 `UINT32_MAX` 精确；
  `fo2ft` 的 `f64 最大有限 RTZ ⇒ +ft_max+OF|NX` 与 `2^-150 RNE ⇒ 0+UF|NX`。
  `arith.yaml` ⇒ 四个比较 id 的 `1.0<2.0 ⇒ -1`、`+0 == -0 ⇒ 0`、qNaN/sNaN 左右与**负号 NaN**
  的 quiet/signaling 无序结果与 NV 口径、`foqcmp` 目的 `rd0 ⇒ ILLI`。
  两文件**未删**（`convert.yaml` 仍含其它 id 的旧措辞、`arith.yaml` 与本册同属 §5.1 前置）。

### `m13-testcases-037`：`sc` 保留粒度（精确地址 + 访问宽度）正式向量

> **本任务无 `tests/inst.yaml` 片段**：5 个新检查点挂在**既有** id `sc.b.nn_orrr_rd` 的链例尾部
> （`contracts/opcodes.yaml` 无独立「保留粒度」身份；另建 `.S` 会撞 `validate_vectors` 的
> 「同一 stem 只能一个 `.S`」与 `check_tests_index` 的载体↔索引双向断言）⇒ id 数 / 镜像数不变。
> 另：L1 `check_tests_index` 现拒绝 `tests/inst/` 下**任何** `*.yaml`（§5.5 的 YAML 退役），
> 与 §5.3 的 `.fragments/<任务>.inst.yaml` 协议冲突——需新增清单条目的分片任务会撞红，待架构侧处置。

- **载体**：`tests/inst/12-misc/sc.b.nn_orrr_rd.S` **只追加**点 17–21（链例 16 → 21），原故障例
  点号 17 → 22（点号仍连续 1..22 = 链例 21 + 故障例 1）；文件头分类计数改 semantic 7 → 12，
  「保留粒度」写入头部（键 = 精确地址 + 访问宽度）、GAP 段收窄。**无新 id / 无新文件 / 无宏层改动**。
- **id 归属判据**：`contracts/opcodes.yaml` **没有**独立的「保留粒度」身份 ⇒ 不能新建 `.S`
  ——`validate_vectors` 断言「同一 stem 只能有一个 `.S`」（新文件与既有 `sc.b.nn_orrr_rd.S` 撞 stem）
  且 `check_tests_index` 断言「载体集 == 索引集」（新文件须改根清单，属串行合并面）。故按任务书
  允许的形态挂在既有 `sc.<w>.<序>` 的链例尾部：点号 +5、影像数不变（265 id / 901 镜像）。
- **语义**（`spec/SimRISC-12 §1`「保留机制」+ `contract-isa §14.2` + 用户裁定 2026-11-14
  「ISS-435 严格按 spec」）：点 17 同字异址写（`st.b@A+1`）、点 18 同址异宽写（`st.t@A`）、
  点 19 同址同宽同 hart 写 ⇒ `sc` **必须成功（0）**（清除侧只列「另一 hart 同址同宽 store」）；
  点 20 本 hart 另一条 `lr`、点 21 `sc` 自消费后二次 `sc` ⇒ **失败（1）**。每点手算数据单元值内联断言
  （`__VERIFY_MEM`），每点一行、点号连续。
- **三方逐字节**：`run_asm_suite.py`（同一 ELF：chipyard / qemu / gem5）2/2 镜像（链例 21 点 =
  168 B、故障例 `0xF8`）三平台 rc=0 且字节流逐字节相同；点 17–21 实测 `0 0 0 1 1`。
- **改前正证**：同一 ELF 在改前二进制（qemu 安装根 `b34ed7f9…` / chipyard `pre-sim`
  `ac35dffb…`）上首红点 = 17；record-only 复刻探针逐点 `1 1 1`（spec `0 0 0`）⇒ 向量真的守护裁定。
- **门控**：`check-inst-asm`（目标体，`--qemu` = 改后二进制）265 id / 901 镜像全绿；检查点数
  +5（链例 21）；`check-tests-index`/`validate-vectors`/`check-case-ledger`/`check-no-residue`/
  `check-knowledge-refs` rc=0（`case-ledger.tsv` 由 `--write` 重生成：+6 行、1 行点号改）。
- **GAP（不伪造）**：① 多 hart 对同址同宽 store 清标记（Tiny 单 hart，无载体）；② **异常或中断
  进入清标记**：链例可构造（固件 hmon 返回槽指向固定 `.text` 桩），但三平台实测分歧 ——
  MALIGN/CFXMEM/ILLI 三路径 `chipyard 1 / qemu 1 / gem5 0`、CFXTRAP 路径 `1 / 0 / 0`
  （spec 均为 1）⇒ **不进正式向量**（不把任一平台行为写成期望），登记为待修实现缺口；
  ③ 存储序强度；④ `sc` 偶发失败。

### `m13-testcases-047`：`.S` 向量对齐 `rf2rf`（删 2 加 1）+ `.S` id ∈ opcodes 门控复核

- **组件面与 spec 对齐**：`contracts/opcodes.yaml` 已由 `m13-spec-010` 删去 FT/FO 各自的同组块复制、
  新增 `rf2rf_orri_rf`（`SimRISC-02 §1`，opc `0x40`/ha `0x3C`，目的含 `rf0` ⇒ ILLI）；本任务删
  `07-floating-point` 的两个旧同组复制载体（各 16 点 / 6 镜像），新增
  `02-reg-copy/rf2rf_orri_rf.S`（17 点 = 链例 11 + 故障例 6，7 镜像）。
- **册归属**：`rf2rf` 的类别是 SimRISC-02「寄存器复制」（同组块复制的唯一 `rf` 形式），故落在
  `02-reg-copy`（与 `rd2rd`/`rb2rb` 同册）；位型搬移与浮点宽度无关 ⇒ `07-floating-point` 不再有
  同组复制载体（README 计数 44 → 42，`02-reg-copy` 16 → 17）。
- **用例**（期望一律内联、由 `SimRISC-02 §1`「保持 64 位二进制不变」直接派生）：encoding 2（规范
  编码字 + 字段边界 `dst=rf63/src=rf62`）、semantic 4（1/2/3/4 元素；NaN payload 逐位保留、负号
  qNaN、±0、次正规；`个数 3` 额外断言**FCSR 位型复制前后不变** ⇒「不置标志」）、boundary 3
  （窗口顶端 `{rf60:rf63}`、`rf63 ← rf40`、最大个数 31 = `{rf1:rf31} ← {rf32:rf62}` 逐元素核
  「目的 == 源内存」）、overlap/rf0 2（相邻不相交窗口合法；`rf0` 作**源**合法且读完整 64 位）、
  故障 6（`dst_rf0`/`mreg_zero`/`mreg_range_overflow` 目的侧与源侧/`mreg_range_overlap` 完全重合与部分交错）。
- **宏层新增**（`tests/inst/macros/inst_test.inc`）：`__VERIFY_MEM_RF`/`__CHECK_MEM_RF`（rf 目的 vs
  内存数据单元，探针 = `rf2rd` 跨组读回 + `ld.o`；命名/参数与 `__CHECK_MEM_RB` 同形）、
  `TEST_MOV_RF0`（源 `rf0` 的单寄存器例：期望运行期取自 `rf0` 自身，不钉位型）、`TEST_MOV1` 增
  `rf2rf` 分支。
- **门控**：`check-tests-index`/`validate-vectors`/`check-case-ledger`/`check-no-residue`/
  `check-knowledge-refs` rc=0；载体 265 → 264（`rf2rf` 落地）、索引 274 → 273 条、镜像 901 → 896。
  「`.S` 载体 stem 必须能在 `contracts/opcodes.yaml` 找到 id」这条断言**已存在**于
  `tools/testcases/validate_vectors.py`（`scan_asm_carriers`，自 `m13-testcases-030`），本任务注入
  复核其**可达 FAIL**（本任务改前正是它报 2 条 `ASM CARRIER ORPHAN` 红）。
- **执行侧依赖**：`rf2rf` 的助记符/译码由 `m13-llvm-001` + `m13-qemu-016` 承担；两者合入并
  `install-host` 前，`check-inst-asm` 对本载体报「unrecognized instruction mnemonic」——与
  其它 263 个载体无关（本任务用语义等价的旧编码做**同构复核**：7/7 镜像绿，见完成区）。

### `m13-testcases-048`：伪指令的 7 个展开形态载体（`00-isa-design/pseudo_set.*`）

- **为什么按展开形态分 7 个**（用户 2026-11-15 裁定口径 a）：失败归因可定位到具体形态；
  `set.ft rf, imm32`（窄写）与 `set.ft rf, rf`（`rf2rf` 整 64 位）**语义相反**，合并会互相掩盖。
  文件名保留助记符点号（`pseudo_set.rd_imm.S` 等，与 `ld.o_*`/`sc.b.nn_*` 同风格）；第 7 个
  用 `fx`（= `ft`/`fo` 两族，两者从 rf 源展开都是 `rf2rf`）。
- **载体不是 opcode id**：伪指令不是硬件指令（`spec/SimRISC-00 §5`），反汇编器只输出真实指令 ⇒
  7 个文件在**两处** `NON_ID_CARRIERS`（`validate_vectors.py` / `check_tests_index.py`）逐文件
  登记，并在 `tests/inst.yaml` 以 `inst-00-isa-design-002`…`-008` 索引（载体↔索引双向断言）。
- **期望怎么给**：伪指令展开是**前端行为**，guest 能观察的只有目的寄存器最终位型 ⇒ 期望一律
  内联自 spec（`Toolchain-01 §6.1` 展开规则 + `SimRISC-03 §1–§4` 的 wyde 语义 + `SimRISC-02 §1`
  块复制「保持 64 位二进制不变」），**不从 qemu/llvm 输出反推**。检查点行复用现有宏
  （`__CHECK_RD`/`__CHECK_MEM`，rf/rb 目的先 `rf2rd`/`st.o` 落到 `SCRATCH`），未新增宏。
  113 个检查点的内联期望另有**独立重算**核对（证据脚本的 `recompute.py`：按上述 spec 规则
  重算目的寄存器终值，不经 LLVM/QEMU；期望被改坏 ⇒ 重算非 0）。
- **写宽对照（本任务核心回归）**：`pseudo_set.ft_imm32.S` 断言「高 32 位 = 写前值」；
  `pseudo_set.fx_reg.S` 断言「高 32 位 = 源高半」。两文件互为反例 ⇒ 任一实现把两者之一
  做成另一种语义，**必有一侧红**（两路注入各红一次，见完成区）。
- **形状类断言放在证据脚本**：「只能一条 `set.zw`/`set.ow`」「全 0/全 1 ≤1 条」「rb 无
  `set.ow`」「`set.fo imm=0` 只有一条 `rd2rf`」「`set.ft imm32` 恰好 2 条 `set.w`」——
  guest 观察不到，由 `llvm-objdump` 反汇编静态断言（期望逐条取自 `SimRISC-03 §2/§3/§4` 的
  文档示例）；形状与文档不符 ⇒ 证据脚本红，不改载体期望。
- **用例规模**：7 文件共 113 个检查点（20/10/20/20/15/15/13），点号 1..N 连续；链例镜像 7 个
  （无故障例——伪指令的非法操作数由**汇编器**拒绝，不是运行期异常，故不做 `CASE_N` 故障镜像）。
- **门控**：`check-tests-index`（271 个 `.S` 载体 / 280 条 inst 索引 / 8 个非 id 载体）/
  `validate-vectors`（271 载体，8 非 id）/ `check-case-ledger`（+113 行）/ `check-inst-asm`
  全绿，见完成区。
### `m13-testcases-049`：原子 RMW **合成序**载体（`00-isa-design/atomic_rmw.S`）

- **为什么需要**：`12-misc` 的 24 个 `lr.*`/`sc.*` 载体只测**单指令语义**（保留置位/清除、成败、
  失败不写、保留粒度）；现场实测 `br.` 回跳数 = 0、`lr` 与 `sc` 之间**无算术** ⇒ C11 `__atomic_*`
  编译出来的「`lr` → 计算 → `sc` → 失败重试」这条环**完全没有覆盖**。
- **册归属（用户 2026-11-15 裁定）**：「我建议放00，因为01-12的文件数量正好可以和指令数对上」
  ⇒ `01`–`12` 各册保持「**一个 opcode id 一个文件**」，**不再往册内塞非 id 载体**；合成序跨 24 条
  `lr`/`sc` 身份、不属任何单个 id ⇒ 落 `00-isa-design/atomic_rmw.S`（与 `undi_reserved.S` 同册）。
  登记：`check_tests_index.NON_ID_CARRIERS` + `validate_vectors.NON_ID_CARRIERS` 逐文件；索引
  `inst-00-isa-design-009`（`platforms: [system]`、`level: full`）。
- **载体**：13 点单文件（链例 13 / 故障例 0，1 镜像）。覆盖表 —— 点 1–3 `fetch_add`（首读 old /
  被抢后 `sc` 失败不写 / 重试成功）、4 `fetch_sub`、5 `fetch_and`、6 `fetch_or`、7 `fetch_xor`、
  8 `exchange`、9–10 `compare_exchange`（相等 ⇒ 执行 `sc`；不等 ⇒ **不执行 `sc`**，结果寄存器
  留哨兵、内存不变）、11–12「**重试必须重读**」（11 记录失败点与陈旧候选 `0x108`；12 用普通 `st`
  改内存后**重新 `lr`** 算 `新值+8`）、13 `fetch_add` 回绕边界（全 1 + 1 ⇒ 0，进位丢弃）。
- **期望推导**（`spec/SimRISC-12 §1` + `contract-isa §14.2`）：`lr` 读值并置标记、`sc` 命中才写且
  成败都清标记；单 hart 可构造的「被抢」只用「本 hart 另一条 `lr`」这**一条**清标记事件 ⇒ 不借
  多 hart / 异常 / 中断（那三条记 GAP）。「同 hart 同址同宽 `st` **不清**标记」是点 11–12 的序列
  依据（`st` 放在清除之后，故无论该事件成立与否都不改变期望）。
- **门控**：`check-inst-asm`（opcode id 数不变、镜像 +1）、`validate-vectors`（非 id 载体条数现场
  派生）、`check-tests-index`、`check-case-ledger`（`--write` 重生成，+13 行）、`check-no-residue`、
  `check-knowledge-refs` 全 rc=0。
- **GAP（不构造、不伪造）**：① 多 hart 争用（Tiny 单 hart）；② 内存序强度 `an`/`ar`/`nr` 的重排
  约束（单 hart 顺序执行不可观测）；③ `sc` 偶发失败（无可控手段）；④ 异常/中断进入清标记（与
  `m13-testcases-037` 同因：三平台实测分歧，不进正式向量）。均与 `ISS-440`/`ISS-443` 同线。
