# `tests/inst/` 重构台账（YAML → 汇编 + 宏）

> **目标**：让每条**操作码**的测试可读、可审、可三方差分。YAML 退出，改为 `.S` + 宏，期望值内联。
> **判据**：一个 id 一个文件；一个文件一个 ELF；失败点号 = 用例序号（退出码 `0x01`–`0x7F`，见 `spec/Machine-v5 §7.1`）。

## 1. 大类（= SimRISC 册）

| 目录 | SimRISC 册 | id 数（初估，待按各册附录 A 校准） |
|---|---|---|
| `01-load-store/` | 01 取数存数 | 38（单元素 19 已迁；`ldm`/`stm` 19 待 `01-b`） |
| `02-reg-copy/` | 02 寄存器复制 | 16 |
| `03-wyde-imm/` | 03 16 位立即数操作 | 8 |
| `04-arith-logic-octa/` | 04 64 位数据运算 | 60 |
| `05-arith-addr/` | 05 64 位地址运算 | 5 |
| `06-control-flow/` | 06 控制流 | 15 |
| `07-floating-point/` | 07 浮点运算 | 44 |
| `08-arith-logic-tetra/` | 08 32 位数据运算 | 16 |
| `09-arith-logic-wyde/` | 09 16 位数据运算 | 16 |
| `10-arith-logic-byte/` | 10 8 位数据运算 | 16 |
| `11-cfx/` | 11 核芯功能扩展 | 29 |
| `12-misc/` | 12 其它指令 | 1（待校准） |

> id 总数应恰为 **264**（`contracts/opcodes.yaml`）。校准任务：建「id → 册」映射表并机械校验（每个 id 恰好属一册、12 册合计 264）。

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
| `TEST_ST` / `TEST_ST_RB` / `TEST_ST_RA` / `TEST_ST_RF` | `检查点, 助记符, 源, 基址, 基址值, 偏移, 源值, beat 期望` | 存储后该 8 字节 beat 逐字节相等（b/w/t 只改几条通道，其余保持） |
| `TEST_FAULT` | `检查点, 助记符, 目的/源, 故障名, 基址, 基址值, 偏移` | 该指令触发 `CFXMEM`/`CFXREG`/`ILLI`/`MALIGN`/`IALIGN`，退出码 = `0xF0|异常位索引` |

- **一个 `.S` = 两种镜像**：`CASE_N=0`（缺省）= 链例（非故障用例顺序跑，逐检查点把
  实测 8 字节写进结果缓冲并打印）；`CASE_N=<检查点>` = 该故障例单独成像（异常不返回
  被测指令之后，故故障例一例一镜像）。检查点数 ≤ 127，失败点号 = 用例序号。
- 三方比较（同一份 ELF）：`tools/testcases/inst/run_asm_suite.py`（chipyard
  `WumingTinyConfig` / QEMU `dadao-tiny` / gem5 FS `tiny`）。

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
| — | `m13-testcases-030` | `.S` 接入门控 + YAML 退役（`ISS-413`） | — |

合计 **264** 个 id（与 `contracts/opcodes.yaml` 一致；各册实测：01 38 / 02 16 / 03 8 / 04 33 / 05 6 / 06 15 / 07 52 / 08 21 / 09 21 / 10 21 / 11 5 / 12 28）。

## 5. YAML 台账（迁移与删除）

现状：**30 个 YAML 文件、1586 条用例、覆盖 229 个 id**；`opcodes.yaml` 有 **264** 个 id ⇒ **36 个 id 无 YAML 载体**；另有 16 个 id 出现在多个文件里。

**删除规则**：一个 YAML 文件里的**所有 id** 都迁完后，才 `git rm` 该文件，并在本表勾掉。

| YAML 文件 | 用例 | 涉及 id 数 | 状态 |
|---|---|---|---|
| `atomics/atomics-fence.yaml` | 17 | 1 | 待迁 |
| `atomics/atomics-lrsc.yaml` | 108 | 24 | 待迁 |
| `atomics/sc-rd0.yaml` | 14 | 24 | 待迁 |
| `base/aip-si.yaml` | 12 | 1 | 待迁 |
| `base/bitcnt.yaml` | — | — | 待迁 |
| `base/reg-arith.yaml` | 224 | — | 待迁 |
| `base/reg-compare.yaml` | — | — | 待迁 |
| `base/reg-cond-assign.yaml` | 25 | 5 | **id 全部已迁**（5 个 `cs.*_rrrr_rd`，见 §6）；文件未删（§5.1 四个门控阻塞） |
| `base/reg-imm-block.yaml` | 48 | 7+6 | **id 全部已迁**（6 个块复制 id 见 §6/014，7 个 rwii id 见 §6/015）；文件未删（§5.1 前置） |
| `base/reg-logic.yaml` | — | — | 待迁 |
| `base/reg-shift-extend.yaml` | 112 | — | 待迁 |
| `base/mem-rd.yaml` | 122 | 22 | **id 全部已迁**（`ld.*`/`st.*` 单元素 11 + `ldm.*`/`stm.*` 11，见 §6）；**文件未删** —— 删除依赖 inventory 载体登记改造（见 §5.1） |
| `base/mem-ra.yaml` | 22 | 4 | **id 全部已迁**（`ld.o`/`st.o` ra + `ldm.o`/`stm.o` ra）；文件未删（同 §5.1） |
| `base/mem-rb.yaml` | 23 | 4 | **id 全部已迁**（同上，rb 形式）；文件未删（同 §5.1） |
| `base/misc.yaml` | — | — | 待迁 |
| `base/reserved.yaml` | 9 | 4+3 | 部分迁移（`ld.`/`st.` 的 6 条 reserved-cfx `CFXMEM` 已迁；3 条 reserved-opcode `UNDI` 无 id，待 `12-misc`） |
| `fp/*.yaml`（`arith`/`convert`/`divrem`/`cond-assign`） | — | — | 部分迁移：`cond-assign.yaml` 的 3 个 `cs.*_rrrr_rf` id 已迁（见 §6，文件未删 §5.1）；其余四册待迁 |
| `bitcnt/`、`clmul/`、`fma/`、`minmax/`、`rev/`、`rol/`、`roundint/` 各自 | 414/81/… | — | 待迁 |

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
输出写进任务书「待裁定」）。在此之前三册保留在盘，`git status` 干净。

## 6. 已完成

### `m13-testcases-012`：`01-load-store` 单元素（`ld.*` + `st.*`，19 个 id）

- `tests/inst/macros/inst_test.inc`：宏层（`TEST_LD*`/`TEST_ST*`/`TEST_FAULT`/
  `__CHECK_RD`/`__CHECK_MEM`；失败 ⇒ `SYS_EXIT(检查点号)`；结果缓冲逐字节打印）。
- `tests/inst/01-load-store/{<id>.S}`（19 个）+ `inst-tiny.lds`（固定布局，ASSERT 钉住）。
- 用例：每 id 16–18 条（encoding 2 / legality 2–5 / semantic 5 / boundary 5–6 /
  overlap 2）；四处 YAML 中属于这 19 个 id 的用例已并入（含 `reserved.yaml` 的
  reserved-cfx `CFXMEM` 6 例）。
- 三方逐字节：`tools/testcases/inst/run_asm_suite.py` 跑 19 链例 + 49 故障例
  （同一 ELF：chipyard / QEMU / gem5），链例比较结果字节流、故障例比较 monitor
  段退出码。
- **YAML 未删**：`mem-rd.yaml`/`mem-ra.yaml`/`mem-rb.yaml` 仍含 `ldm`/`stm` id，
  `reserved.yaml` 仍含 3 条无 id 的 reserved-opcode 例 ⇒ 按本文件 §5 的删除规则，
  要等 `01-b`/`12-misc` 迁完才 `git rm`。

### `m13-testcases-013`：`01-load-store` 多元素（`ldm.*` + `stm.*`，19 个 id）

- 宏层新增（`tests/inst/macros/inst_test.inc`）：`TEST_LDM`（装入 → 同宽度/同组
  `stm.*` 回写 → 逐 8 B 拍比内联期望）、`TEST_STM`（同宽度/同组 `ldm.*` 预装 →
  存储 → 逐拍比期望，期望含保持字节）、`TEST_FAULT_M`（rrri 故障例）、
  `TEST_FAULT_ENC`（汇编器拒绝的编码：`immu6=0`、组首+`immu6>64`）。
  一行 = 一个检查点（宏内单次 `__REC`），点号仍 = 用例序号。
- 数据区新增（`.testdata`，与单元素用例的 0x000–0x0E8 区不重叠）：`MDATA_B/W/T/O`
  （逐元素可辨）、`MUNI`（同值拍，最大个数例）、`MDUMP`（装入回写落点）、
  `MSTORE`（存储落点 + 保持区模式）。`.testdata` 0x1000→0x2000、结果缓冲
  0x3000→0x4000、退出参数块 0x4000→0x5000（`inst-tiny.lds` ASSERT 同步）。
- 用例：每 id 13–21 点；多元素例 `count>1` 占多数（1/2/3/8/9/16 与 63；63 只出现在
  `ldm.o_rd`/`ldm.ub_rd`/`ldm.o_ra`/`ldm.o_rf`）；`stm.b` 9 元素 = 2 拍且第二拍只开
  1 lane；存储例都带左右保持区核对；`ldm` 抽样元素用 `__CHECK_RD` 独立核对。
- 故障：`immu6=0`/组首+`immu6>64`/目的 rd0·rb0/`ldm` 重叠 ⇒ ILLI；`MALIGN`；
  CFXMEM 三形态（cfxha 0 段、整段越 SRAM 尾、保留 cfx 段）。
  **多元素不要求无副作用**（用户 2026-11-13 裁定：允许部分元素已生效）⇒ 故障例**只比异常码**，
  不判目的寄存器/目标内存；「中途总线 denied」在 Tiny 不可构造（`ISS-381` F-c）。
- **overlap**（规范 `SimRISC-01` + `mreg_range_addr_overlap`，`m13-spec-005` 定稿）：`ldm` **禁重叠**
  —— RD 形式索引 `rdHC`、RB 形式基址 `rbHB` 落在传送范围内 ⇒ ILLI；`stm` **允许重叠**（只读，
  行为确定）⇒ 正常执行并核源组未被改写；RA/RF 形式结构上不可能相交 ⇒ 不适用。
  实现进度：QEMU（`m13-qemu-006`）/ gem5（`m13-gem5-008`）已合入；chipyard 待 `m12-chipyard-027`。
- **`immu6=63` 的索引选择**：RD 形式的 `{rd1:rd63}` 已把 RD 组占满，索引只能用 `rd0`
  （rd0 读出 0 ⇒ EA = 基址）；用 `rd19` 会落进传送范围 ⇒ ILLI（`mreg_range_addr_overlap`）。
- 三方逐字节：`run_asm_suite.py`（同镜像 chipyard / QEMU / gem5）链例比字节流、
  故障例比 monitor 段退出码；沿用 `012` 的 hmon 自装 workaround（`ISS-410` 未修）。
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
  16 拍字面量）；`+0x70` 的 `[63:54]=0` 值专供 `ra0` 作目的。
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
  16 拍）/ WSCRATCH（`+0x1580`，rf0 例的前/后 8 B）。
- **探针不借被测指令**：目的在 rd 直接比；在 rb/rf 用同组 `st.o` 落到 SCRATCH
  再逐字节比。初值：rd 用 `__LI`、rb 用 `__LI_RB`、rf 用 `__LI` + `rd2rf`。
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
