# inst scope — 指令级测试用例（`tests/inst/`）

本目录是 **inst scope**（`docs/Process-09` §3）：单指令/短序列执行语义的**源码用例**，
另含 `atomics/clmul/fma/minmax/roundint` 探针源。向量是 LLVM/QEMU/gem5 的**独立 oracle**。

> `TESTCASES-072t`（2026-10-27）从 `tests/vectors/` 与 `tests/{atomics,clmul,fma,minmax,roundint}/`
> 迁入；执行 harness 在 `tools/testcases/{lib,inst}/`。

- 向量**独立派生自锁定的规范与合约**（`spec/`、`.tao/contracts/contract-isa.md`、
  `contracts/opcodes.yaml`、`contracts/legality_rules.yaml`、
  `.tao/adr/adr-0004-test-machine.md`），**不从 LLVM 汇编输出或 QEMU 运行结果生成**。
- 每条向量记录输入状态、编码字、期望输出状态/PC/异常，期望值可回溯到 `spec_cite`。
- 覆盖率主键为 `id`（对应 `contracts/opcodes.yaml` 的 `id`，**唯一**）；`format` 为普通字段，不入主键。M1 scope 以
  `contracts/opcodes.yaml` 中 `scope == "m1"` 为唯一判据（**156 条**）。

## 文件

| 文件 | 说明 |
|------|------|
| `schema.md` | **历史**：向量 YAML 字段规范（含 `expected_pc`、class 定义、encoding 豁免、deferred 规则）；YAML 已全退役（`m13-testcases-043`），保留作类别/故障词表与独立派生规则 |
| `inventory.md` | M1 覆盖矩阵（以 `id` 为行，含 `format`/`file` 列与 deferred reason） |
| `00-isa-design/undi_reserved.S` | **非 id 载体**（保留编码 ⇒ UNDI，3 条；逐文件登记，见 `check_tests_index.NON_ID_CARRIERS`） |
| `base/`（已删） | 原 YAML 向量目录（`TESTCASES-003t`~`007t` 生成；**YAML 已全退役**，`m13-testcases-043`） |
| `MIGRATION.md` | YAML → 汇编+宏 的迁移台账（大类/小类/用例模板/任务拆分/删除规则） |
| `macros/inst_test.inc` | 汇编宏层（`TEST_LD*`/`TEST_ST*`/`TEST_MOV1`/`TEST_CS*`/`TEST_WI*`/`TEST_FAULT*`/`__CHECK_*`，期望值内联） |
| `01-load-store/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（单元素 `ld.*`/`st.*`，19 个；含 `st.o rb0`（IP 作源/作基址）与 `ld.o ra0`（RAS 窗口读写）补测） |
| `01-load-store/inst-tiny.lds` | 上面这册的链接布局（固定段地址 + ASSERT 钉住）；`02-reg-copy`/`03-wyde-imm` 复用同一布局 |
| `02-reg-copy/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（块复制 8 + `cs.*` 8，共 16 个） |
| `03-wyde-imm/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（`set.zw`/`set.ow`/`or.w`/`andn.w`/`set.w`，8 个） |
| `04-arith-logic-octa/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（算术族 `add.*`/`sub.*`/`mul.*`/`div.*`/`rem.*`/`cmp.*` 15 个；逻辑/移位/扩展 14 个；位操作 `rev.o`/`rol.o`/`clmul.o` 4 个） |
| `04-arith-logic-octa/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（算术族 `add.*`/`sub.*`/`mul.*`/`div.*`/`rem.*`/`cmp.*`，15 个；逻辑/移位/位操作见后续任务） |
| `05-arith-addr/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（64 位地址运算 `add.o`/`sub.o` 的 bbd·dbb、`cmp.uo`、`add.si`、`aip.si`，6 个） |
| `06-control-flow/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（控制流 `br.*` 10 个、`jump` 2、`call` 2、`ret` 1，共 15 个；含 RAS 溢出/下溢与跳转距离边界） |
| `07-floating-point/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（`foadd/fosub/fomul/fodiv/forem`、`ftadd/ftsub/ftmul/ftdiv/ftrem`、`fofma/ftfma`、`fomin/fomax/ftmin/ftmax`、`foroot/ftroot` 18 个；转换 `f2f/f2i/i2f` 双向 18 个；块复制 `ft2ft/fo2fo` 2 个；分类 `ftcls/focls` 2 个；比较 `ftqcmp/ftscmp/foqcmp/foscmp` 4 个 —— 共 44 个；含 FCSR 五类标志、六档舍入方向、NaN/±0/次正规/溢出/下溢边界） |
| `07-floating-point/inst-tiny-fp.lds` | 浮点册专用链接布局（`.text` 上限 0x4000；`.testdata` 0x5000–0x7000；结果缓冲 0x7000） |

## 汇编载体（M13 起）

用户 2026-11-12 裁定：YAML 不可读、转汇编易错 ⇒ **汇编 + 宏**，期望值内联。
一行一个用例，失败即 `SYS_EXIT(检查点号)`（`0x01`–`0x7F`）；机器异常例单独成像，
退出码 = monitor 段编码（`0xF0|异常位索引`）。格式、宏签名与两种镜像形态见
`MIGRATION.md §2`；跑法：

```
python3 tools/testcases/inst/run_asm_suite.py --id ld.o_rrii_rd   # 单个 id
python3 tools/testcases/inst/run_asm_suite.py                     # 01-load-store 全册
python3 tools/testcases/inst/run_asm_suite.py \
    --vectors tests/inst/02-reg-copy \
    --lds tests/inst/01-load-store/inst-tiny.lds                  # 02-reg-copy 全册
python3 tools/testcases/inst/run_asm_suite.py \
    --vectors tests/inst/03-wyde-imm \
    --lds tests/inst/01-load-store/inst-tiny.lds                  # 03-wyde-imm 全册
python3 tools/testcases/inst/run_asm_suite.py \
    --vectors tests/inst/04-arith-logic-octa \
    --lds tests/inst/01-load-store/inst-tiny.lds                  # 04 全册（算术 + 逻辑/移位/扩展）
python3 tools/testcases/inst/run_asm_suite.py \
    --vectors tests/inst/06-control-flow \
    --lds tests/inst/01-load-store/inst-tiny.lds                  # 06 全册（br.*/jump/call/ret）
python3 tools/testcases/inst/run_asm_suite.py \
    --vectors tests/inst/07-floating-point \
    --lds tests/inst/07-floating-point/inst-tiny-fp.lds           # 07 全册 44 个 id
                                                                  # （算术/最小最大 18 + 转换/比较/分类 26）
```

判据 = **同一份 ELF** 在 chipyard `WumingTinyConfig` / QEMU `dadao-tiny` / gem5 FS
`tiny` 上，链例的结果字节流逐字节一致、故障例的退出码一致。

### 特殊寄存器取值的期望怎么给（补测）

- **`rb0`（当前指令地址）**：期望值随链接布局变化，而 `llvm-mc` 只折装绝对常量（标签差
  被静默折 0，`ISS-424`）⇒ 三种写法：①`aip.si rbX, 0` + `add.si rbX, <delta>`；
  ②`rb2rb rbX, rb0, 1` + `add.si rbX, <delta>`（`delta` = 被测指令与取指指令的**字节差**，
  相邻两条即 4）；③`.org` 钉住被测指令后写 `ENTRY + <字面偏移>`（钉真实地址，防「两条
  IP 通路同错也自洽」）。实测经 `__CHECK_MEM_RB`（期望在 RB 时先 `rb2rd` 再比）。
- **`ra0`（`{SBZ(10), RACNT(6), MRPTR(48)}`）**：读用 `call`/`ret` 构造已知 `RACNT`/`MRPTR`
  后 `ra2rd` 拷出；写用 `ld.o ra0, …` 装入含 SBZ 置位的值再读回，`[63:54]` 必须仍为 0。
  **该写语义 QEMU/gem5 与 RTL 不一致**（前者保留写入的 SBZ 位）⇒ `ld.o_rrii_ra` 链例在
  QEMU/gem5 红、chipyard 绿（issue 候选号见 `m13-testcases-031` 任务书「遗留问题」；期望**不放宽**）。

## 校验

```
python3 tools/testcases/validate_vectors.py   # 或 make check（L1）
```

校验 schema 字段、class/fault 取值、编码 mask/value、`expected_pc`、`inventory`
同步与覆盖率；有错误时 `exit(1)` 并列出文件 + case 序号。
