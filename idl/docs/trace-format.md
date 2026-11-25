# 逐指令 trace 格式（`m17-idl-004`）

> **定位**：一个**机器可读、模型无关**的逐指令 trace 格式，当前真源实现是 `idl/tools/idl_exec_trace.py`（IDL 执行器）与 `idl/tools/idl_qemu_trace.py`（QEMU 观测面派生）。**消费方**：`m17-idl-004` 的 QEMU 逐指令差分；`m20-gem5-001`（gem5 Minor）与 `m20-chipyard-001`（wuqing）复用同一字段口径（M20 的 golden = wuming RTL）。
> **样例**：[`trace-sample.jsonl`](trace-sample.jsonl) 由脚本生成（禁止手改），生成/校验命令见 §5。
> **不引入 ISA 语义**：本文只定义「观测到的架构变化」如何记录与比较；指令语义仍以 `spec/SimRISC-*` + `idl/*.idl` 为准。

## 1. 记录与文件

- 一行一个 JSON 对象（JSONL，UTF-8），按**退休顺序**排列。
- 一条记录 = 一条**退休指令**（取指异常见 §3 E2）。
- 记录按**退休顺序**排列，`seq` 用本次 trace 内的 1-based 序号；`idl/docs/trace-sample.jsonl` 是**异常前后窗口**（`seq` 保留原序号，故不从 1 开始）。
- 单文件超过 **1 MiB** 时由 `TraceWriter` 滚动成 `<stem>.part-001.jsonl`、`<stem>.part-002.jsonl`……（任务约束：不得逐条落盘成巨文件）。

字段（实现的固定顺序）：

- `seq`：整数，本次 trace 内 1-based 序号。
- `pc`：`"0x" + 16 位十六进制`，该指令的地址（= 当前 IP；DADAO 的 IP 是当前指令地址）。
- `insn`：`"0x" + 8 位十六进制`，指令字（大端取指）；`null` 表示该记录没有取到指令（正常 trace 不出现）。
- `id`：`contracts/opcodes.yaml` 的 operation id（助记符 + 格式 + 寄存器组；例 `ld.o_rrii_rd`）。
- `mn`：助记符（例 `ld.o`）。
- `dst`：架构寄存器名列表（`rd0`…`ra63`），**只列值发生变化**的寄存器；顺序固定为 `rd`→`rb`→`rf`→`ra`、组内下标升序。
- `val`：与 `dst` 并列的 64 位值列表（`"0x" + 16 位十六进制`）。
- `exc`：`null`，或本指令触发的异常对象：
  - `cfx`：发生异常的 cfx id（Tiny 用例为 `3` hmon 或 `63` power）；
  - `cause`：`cfx_⟨cfxname⟩_excp_cause_id` 原值（64 位；低 16 位 one-hot cause，wyde3/wyde2 为子原因，见 `spec/DADAO-12 §3.6`）；
  - `ip`：`excp_cause_ip`；`info`：`excp_cause_info`。

`dst`/`val` 是**写回集合**而不是指令操作数字段：同值写回不可观测（两侧同规则），不列出。两条不变量：

- `rb0` 永不列出（`rb0` = IP，由 `pc` 承载）；`rd0` 永不列出（恒 0，写丢弃）。
- `ra1..ra63` 只列 **`RACNT` 有效区内**（`ra[64−RACNT .. 63]`）的条目；有效区外内容未定义（`spec/SimRISC-00 §2.4`），即使被硬件改动也不列出。

## 2. 派生口径（两侧一致）

- `pc`/`insn`：来自**同一份镜像**（ELF `PT_LOAD` 段 + BootROM 的 hmon 段）；`id`/`mn` 由 `contracts/opcodes.yaml` 的编码表译码，不解释语义。
- `dst`/`val`：指令执行前后四寄存器组的差；异常进入不改寄存器组，故异常指令的写回集合通常为空。
- `exc`：执行器取本条指令的异常帧（`cfx3`/`cfx63` 的 `cg5`）；QEMU 侧取「记录间 `cfx3`/`cfx63` 的 `TRAPN/SYNCN/ASYNCN` 计数增量 + 新帧 `CG5`」。两侧都要求 `cfx` 的大类计数确实增长，避免「帧值陈旧」误判。
- **运行模式/cfx code**：不放进记录（字段面只到「寄存器组 + 异常」），但 QEMU 逐指令差分**逐条比较**每条指令后的 `mode` 与 `cfx`（`idl/tools/idl_check_trace.py`）。
- **内存**：`-d cpu` 不提供内存观测，本格式暂不含内存写回字段。M20 的两个模型都能观测内存时按「新增可选字段 `mem`，缺省 = 未观测」扩展，不改既有字段语义。

### 2.1 已知限制（`m17-idl-021` 记录，M20 复用时必须知道）

- **`id`/`mn` 不是独立证据**：两侧都由 `contracts/opcodes.yaml` 的**同一张**编码表译码（QEMU 侧不用其反汇编，见 `idl/tools/idl_qemu_trace.py`）。因此两侧 `id`/`mn` 相等只证明「同一指令字经同一张表译成同一 id」，**不能**证明编码表本身与 ISA 一致——该字段的证据力由此让位；编码表与语义的一致性由其它判据承担（`check-idl` 的签名槽对 `tests/data/inst-signature/expected.tsv` 逐槽比对，期望值由 `.S` 内联常量派生）。
- **E3/E4 放宽量（skip 覆盖率）**：`idl_check_trace.py` 逐例打印 `rd8_skip`/`ra_skip`；全清单（274 例）在 2026-11-25 实测为 **249457 条指令记录**，其中
  - `rd8_skip` = **149766/249457 条记录（60.0%）**——链例在每个检查点用 semihosting 打印，`SYS_WRITEC` 之后 `rd8` 长期处于「不可比」态（E3 的 taint 只在非 semihosting 指令重新写入 `rd8` 且值变化时解除）；
  - `ra_skip` = **72462 个条目**（≈0.29 条目/记录；每条记录最多 63 个 `ra` 比较点，分母上界 249457×63 ≈ 15.7M ⇒ ≈0.46%）——E4 只丢「来源未定义」的条目（有效区外提升、`call`/`ret` 整栈搬移自未定义来源）。
  - 口径：`rd8_skip` 计**记录数**、`ra_skip` 计**条目数**，都随用例集变化，引用须用脚本当次输出、不得写死。**覆盖率偏大的直接含义**：这两项被放宽的字段（`rd8` 值、有效区外 `ra`）证据力弱，M20 复用本格式时不得把它们当独立功能证明，`rd8`/`ra` 相关指令的功能判据须另配签名槽/定向用例。

## 3. QEMU 逐指令比对口径与文档化等价

QEMU 侧命令固定为 `-accel tcg,one-insn-per-tb=on -d cpu -D <log>`（QEMU 11 system 模式无 `-singlestep`）。`-d cpu` 每条记录是该指令**执行前**的状态，所以第 i 条指令的效果 = `record[i+1] − record[i]`；入口 = 第一条 `PC == e_entry` 的记录。

以下四类等价**必须**逐条计数（`check_trace_parity.py` 输出 `dup/ffetch/ra_skip/rd8_skip`）：

- **E1（连续重复记录）**：QEMU TB 日志会偶发「同 PC 且状态逐字段相同」的连续记录；折叠。计数 = `dup`。
- **E2（取指异常不出记录）**：`IALIGN`/取指 `CFXMEM` 的目标地址没有 QEMU 记录，其异常帧落在下一条（handler）记录上；执行器侧没有独立指令记录，异常归并到**前一条**指令。计数 = `ffetch`。
- **E3（semihosting 定义值）**：`SYS_WRITEC`/`SYS_EXIT*` 无返回值，QEMU 写 `rd8=0xdeadbeef`（`common_semi_dead_cb`，实现约定）；`SYS_CLOCK` 返回宿主时钟（`contract-semihosting §3`：自启动起百分秒，运行间不可复现）。二者都不是架构语义 ⇒ 该步起 `rd8` 退出比对；后续若被非 semihosting 指令重新写入且值变化，恢复比对。计数 = `rd8_skip`（记录数）。
- **E4（RAS 未定义区）**：`ra1..ra63` 在 `RACNT` 有效区外内容未定义（`spec/SimRISC-00 §2.4`）；QEMU 的物理缓冲布局（弹出时移动条目）与执行器（保留旧值）不同，两者都合规。只比有效区；「内容来源未定义」的条目不参与比对——包括从有效区外**提升**进有效区的条目，以及 `call`/`ret` **整栈搬移**自未定义来源的条目（搬移不是写，可比性按来源槽继承）；直接写仍参与。两侧派生各记跳过集，比较器取**并集**后成对剔除 `dst`/`val`。计数 = `ra_skip`（条目数，信息量）。

除这四类外**不得**放宽：记录数、`pc/insn/id/mn/dst/val/exc`、每条后的 `mode`/`cfx`、退出码、semihosting 字节流都必须相等。

## 4. 与 M20 的复用约定

`m20-gem5-001` 的 gem5 Minor 与 `m20-chipyard-001` 的 wuqing（golden = wuming RTL）各自把逐指令观测**投影成同一记录字段**：

- 必须保留：`pc`、`insn`、`id`、`mn`、`dst`/`val`、`exc`；`seq` 用于顺序校验。
- 可新增：`mem`（访存写回，`[{"addr","width","value"}]` 或缺省）、`cycle`（时序，仅供报告，不参与功能比对）。
- **不得改既有字段语义**；新增字段的消费者必须能忽略未知字段。

## 5. 生成、比对与样例

命令（`<镜像目录>` = `tests/ee-tiny/run_inst_tiny.py --work-dir` 的运行期目录；`<bootrom>` = Tiny BootROM 镜像）：

```text
# QEMU 侧 trace（同时写出入口态）
python3 idl/tools/idl_qemu_trace.py --elf <elf> --bootrom <bootrom> \
    --entry-out <entry.json> --trace-out <qemu.jsonl>

# 执行器侧 trace（用同一入口态）
python3 idl/tools/idl_exec_trace.py --elf <elf> --bootrom <bootrom> \
    --init <entry.json> --out <exec.jsonl>

# 逐指令差分（≥20 例；--trace-dir 落两侧 trace，--json-out 落汇总）
python3 idl/tools/idl_check_trace.py --images <镜像目录> \
    --bootrom <bootrom> [--trace-dir <dir>] [--json-out <f>]

# 样例：重新生成 / 校验（样例由脚本产出，禁止手改）
python3 idl/tools/idl_check_trace.py --images <镜像目录> \
    --bootrom <bootrom> --sample-case trap_ciii_cfx --sample-around-exc \
    --sample-records 6 --sample-out idl/docs/trace-sample.jsonl
python3 idl/tools/idl_check_trace.py --images <镜像目录> \
    --bootrom <bootrom> --sample-case trap_ciii_cfx --sample-around-exc \
    --sample-records 6 --sample-check idl/docs/trace-sample.jsonl
```

自检：`python3 idl/tools/idl_exec_trace.py --self-test`（RA 有效区、`rb0`/`rd0`、写回集合、异常对象）。
