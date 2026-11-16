# inst scope — 指令级测试用例（`tests/inst/`）

本目录是 **inst scope**（`docs/Process-09` §3）：单指令/短序列执行语义的**源码用例**，
另含 `clmul` 探针源（`atomics` 探针已于 `m13-testcases-050` 退役）（`fma/minmax/roundint` 三个 C 探针已由 `m13-testcases-044` 退役，
其边界点已抽进 `07-floating-point` 的 `.S` 载体）。向量是 LLVM/QEMU/gem5 的**独立 oracle**。

> `TESTCASES-072t`（2026-10-27）从 `tests/vectors/` 与 `tests/{atomics,clmul,fma,minmax,roundint}/`
> 迁入；执行 harness 在 `tools/testcases/{lib,inst}/`。`fma/minmax/roundint` 探针于
> `m13-testcases-044` 退役（覆盖核对见该任务书；抽点进 `.S` 后删目录与 oracle/runner）。

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
| `00-isa-design/pseudo_set.*.S` | **非 id 载体**：7 个伪指令展开形态（`set.rd`/`set.rb` 的 imm/reg 四条 + `set.rf rf, rs` + `set.ft rf, imm32` + `set.fo rf, imm64`；逐文件登记，索引 id `inst-00-isa-design-002`…`-008`）；**写宽对照**见下节 |
| `00-isa-design/atomic_rmw.S` | **非 id 载体**（原子 RMW 的**合成序**：`lr` → 寄存器计算 → `sc` → 失败重读重试，13 条；跨 24 条 `lr`/`sc` 身份而非单个 id，故不入 `01`–`12` 册——那 12 册保持「一个 opcode id 一个文件」；逐文件登记 + `inst-00-isa-design-009` 索引） |
| `base/`（已删） | 原 YAML 向量目录（`TESTCASES-003t`~`007t` 生成；**YAML 已全退役**，`m13-testcases-043`） |
| `MIGRATION.md` | YAML → 汇编+宏 的迁移台账（大类/小类/用例模板/任务拆分/删除规则） |
| `macros/inst_test.inc` | **跨册**共享宏层（`__LI`/`__EXIT`/`__CHECK_*`/`__FAULT_GUARD`/`TEST_FAULT_ENC`/`TEST_AR_ORRR` 等，期望值内联）；只放 **≥2 个册**用到的宏（`m15-testcases-002`） |
| `<册>/<册>.inc` | **册专用**宏层（`01-load-store`…`07-floating-point`、`12-misc` 各一份）；只放本册用的宏与数据区布局，由该册各 `.S` 在共享层之后 `.include`（`12-misc` 的数据区与 `lr/sc` 准备段见 `m15-testcases-003`） |
| `01-load-store/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（单元素 `ld.*`/`st.*`，19 个；含 `st.o rb0`（IP 作源/作基址）与 `ld.o ra0`（RAS 窗口读写）补测） |
| `01-load-store/inst-tiny.lds` | 上面这册的链接布局（固定段地址 + ASSERT 钉住）；`02-reg-copy`/`03-wyde-imm` 复用同一布局 |
| `02-reg-copy/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（块复制 9 + `cs.*` 8，共 17 个） |
| `03-wyde-imm/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（`set.zw`/`set.ow`/`or.w`/`andn.w`/`set.w`，8 个） |
| `04-arith-logic-octa/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（算术族 `add.*`/`sub.*`/`mul.*`/`div.*`/`rem.*`/`cmp.*` 15 个；逻辑/移位/扩展 14 个；位操作 `rev.o`/`rol.o`/`clmul.o` 4 个） |
| `04-arith-logic-octa/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（算术族 `add.*`/`sub.*`/`mul.*`/`div.*`/`rem.*`/`cmp.*`，15 个；逻辑/移位/位操作见后续任务） |
| `05-arith-addr/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（64 位地址运算 `add.o`/`sub.o` 的 bbd·dbb、`cmp.uo`、`add.si`、`aip.si`，6 个） |
| `06-control-flow/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（控制流 `br.*` 10 个、`jump` 2、`call` 2、`ret` 1，共 15 个；含 RAS 溢出/下溢与跳转距离边界） |
| `07-floating-point/*.S` | 已迁移的汇编载体：一个 opcode id 一个文件（`foadd/fosub/fomul/fodiv/forem`、`ftadd/ftsub/ftmul/ftdiv/ftrem`、`fofma/ftfma`、`fomin/fomax/ftmin/ftmax`、`foroot/ftroot` 18 个；转换 `f2f/f2i/i2f` 双向 18 个；分类 `ftcls/focls` 2 个；比较 `ftqcmp/ftscmp/foqcmp/foscmp` 4 个、取整/缩放/符号 `fornd/ftrnd/fosclb/ftsclb/fosgnj/fosgnn/ftsgnj/ftsgnn` 8 个 —— 共 50 个；含 FCSR 五类标志、六档舍入方向、NaN/±0/次正规/溢出/下溢边界。同组块复制不分浮点宽度 ⇒ 唯一载体 `rf2rf_orri_rf.S` 归 `02-reg-copy`） |
| `07-floating-point/inst-tiny-fp.lds` | 浮点册专用链接布局（`.text` 上限 0x4000；`.testdata` 0x5000–0x7000；结果缓冲 0x7000） |

## 汇编载体（M13 起）

用户 2026-11-12 裁定：YAML 不可读、转汇编易错 ⇒ **汇编 + 宏**，期望值内联。
一行一个用例，失败即 `SYS_EXIT(检查点号)`（`0x01`–`0x7F`）；机器异常例单独成像，
退出码 = monitor 段编码（`0xF0|异常位索引`）。格式、宏签名与两种镜像形态见
`MIGRATION.md §2`；跑法：

宏的**作用域分三层**（用户 2026-11-15/16 口径，L1 门控 `check-inst-macro-scope` 机械判）：
跨册（≥2 册）⇒ `macros/inst_test.inc`；册专用 ⇒ `<册>/<册>.inc`；单文件专用 ⇒ 直接写在
该 `.S` 内（`.include` 之后、首个用例之前）。死宏必须为 0。

**宏化判据 = 净收益 > 0 且表达一个可复用的准备动作**（用户 2026-11-16 裁定 B；
`check-inst-macro-scope` 的 S9）：

- `净收益 = k×n − (n+2+k)`，`n` = 模式行数、`k` = 出现（展开）次数、`2` = `.macro`/`.endm`。
  ⇒ **2 行模式要 k ≥ 5、3 行模式要 k ≥ 3、4 行模式要 k ≥ 3** 才有正收益
  （按公式代入：n=4 时 k=2 的净收益恰为 0，仍不满足 `> 0`）；
  净收益 ≤ 0 的宏化"做了不如不做"——S9 默认**告警**（`[WARN]`），`--strict` 时 rc≠0。
- **光省行不够，必须表达一个可复用的准备动作**（装地址 / 存到地址 / 取落点跳转 / 置权限…）。
  反例：「两条 `__LI` 粘一起」这类**双装值段**不携带准备段语义，属"为省行而抽象"⇒ **不做**
  （`m15-testcases-005` 曾落地又按用户 2026-11-16 裁定 1 全部回退）。
- **含用例/断言行的模式不得合并**：模式内出现 `TEST_*` / `__CHECK_*` / `__PT_*` /
  `__VERIFY_*` / `__REC` 一律跳过——合并它们会把两个检查点压成一个（用例身份丢失）。

**宏前缀三分类**（用户 2026-11-16 裁定 2；`check-inst-macro-scope` 机械判 S6/S7/S9）：

| 前缀 | 含义 | 计数（每行/每次调用） |
|---|---|---|
| `TEST_*` / `__CHECK_*` | 用例行 / 断言行（**扫描器按这些计点**） | 1 个检查点 |
| `__PT_*` | **整例宏**：一次调用 = 恰 1 个检查点 | 1 |
| `__PREP_*` | **准备段宏**：0 个检查点（准备数据/地址/权限） | 0 |

- **`__RF` 前缀禁用**（后接下划线）：DADAO 的寄存器组是 `rd/rb/rf/ra`，`RF` 天然读作
  「浮点寄存器组」，`__RF` 开头的准备宏会被误读成"浮点装地址" ⇒ 准备段一律 `__PREP_*`
  （`m15-testcases-004` 留下的准备宏已随本次改名收敛为 `__PREP_ST_VERIFY`）。
- 已落地的准备段宏（`m15-testcases-005`）：`__PREP_LI_ADDR`（装立即数 + 装地址）、
  `__PREP_ST_ADDR`（存到地址）——`12-misc.inc`，`lr.*` 12 文件共用；
  `__PREP_LAND_JUMP`（`06`：`__LAND_IP` + `jump` 到落点）；`__PREP_MEM2`（`02`：两次
  `__SET_MEM` 建两块浮点寄存器数据区）；`__PREP_ST_VERIFY`（`02` 文件内：存 + 核对）。

```
python3 tools/testcases/inst/run_asm_suite.py --id ld.o_rrii_rd   # 单个 id
python3 tools/testcases/inst/run_asm_suite.py                     # 01-load-store 全册
python3 tools/testcases/inst/run_asm_suite.py \
    --vectors tests/inst/00-isa-design                            # 00 册（非 id 载体：
                                                                  # 保留编码 + 原子 RMW 合成序）
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
    --lds tests/inst/07-floating-point/inst-tiny-fp.lds           # 07 全册 42 个 id
                                                                  # （算术/最小最大 18 + 转换/比较/分类 24）
python3 tools/testcases/inst/run_asm_suite.py \
    --vectors tests/inst/00-isa-design \
    --lds tests/inst/01-load-store/inst-tiny.lds                  # 00 册（UNDI 3 例 + 7 个伪指令载体）
```

判据 = **同一份 ELF** 在 chipyard `WumingTinyConfig` / QEMU `kaiwu-tiny` / gem5 FS
`tiny` 上，链例的结果字节流逐字节一致、故障例的退出码一致。

### 伪指令载体（`00-isa-design/pseudo_set.*`，`m13-testcases-048`）

伪指令**不是硬件指令**（`spec/SimRISC-00 §5`）：汇编器前端展开为一条或多条真实指令，
反汇编器只输出真实指令 ⇒ 载体名字不是 opcode id，按**非 id 载体**逐文件登记
（两处 `NON_ID_CARRIERS` + `tests/inst.yaml` 索引）。7 个载体按**展开形态**分（失败归因
可定位到具体形态），期望的**可观察结果只有一个**：目的寄存器的最终位型（由 spec 的立即数
/ 源寄存器位型派生），**不从 qemu/llvm 输出反推**。

| 载体 | 形态 | 可观察判据 |
|---|---|---|
| `pseudo_set.rd_imm.S` | `set.rd rd, imm64`（1–4 条） | 目的 rd = 立即数完整 64 位；全 0 / 全 1 / 稀疏位 / 各 wyde 极性 |
| `pseudo_set.rd_reg.S` | `set.rd rd, rs`（`rb2rd`/`rf2rd`/`ra2rd`/`rd2rd`） | 四种源各覆盖，**整 64 位**搬运 |
| `pseudo_set.rb_imm.S` | `set.rb rb, imm64`（`set.zw`+`or.w`） | 目的 rb = 完整 64 位；rb **无 `set.ow`** ⇒ 负值/全 1 形态与 rd 不同（结果相同） |
| `pseudo_set.rb_reg.S` | `set.rb rb, rs`（`rd2rb`/`rb2rb`） | 两种源，**整 64 位** |
| `pseudo_set.ft_imm32.S` | `set.ft rf, imm32`（2× `set.w`） | **写宽对照第一行：高 32 位保持写前值**（结果 = `(旧值 & 0xFFFFFFFF00000000) \| imm32`） |
| `pseudo_set.fo_imm64.S` | `set.fo rf, imm64` | **整 64 位**；`imm = 0` 走 `rd2rf rd0`（旧值整 64 位清零） |
| `pseudo_set.rf_reg.S` | `set.rf rf, rs` ⇒ `rd2rf`（rd 源）/`rf2rf`（rf 源） | **写宽对照第二行：高 32 位被覆盖**（整 64 位逐位复制） |

展开**形状**（「只能一条 `set.zw`/`set.ow`」「全 0/全 1 ≤1 条」「rb 无 `set.ow`」「`set.fo
imm=0` 只有 `rd2rf`」）guest 观察不到 ⇒ 由 `m13-testcases-048` 的证据脚本对 `llvm-mc` +
`llvm-objdump` 逐形态静态断言，不写进检查点。

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

`.S` 载体侧另有一条**身份断言**（`validate_vectors.scan_asm_carriers`）：每个
`tests/inst/<册>/<stem>.S` 的 `stem` 必须是 `contracts/opcodes.yaml` 里的 id（非 id 载体
须在 `NON_ID_CARRIERS` 逐文件登记）—— opcodes 删除/改名而载体未跟 ⇒ `ASM CARRIER ORPHAN`
红（M13 起，计数与 id 集合现场派生，不写死）。
