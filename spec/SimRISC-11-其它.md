# SimRISC其它指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：其它**（30 条）— cfx2rc/cfx2rd/escape/swym/trap/fence/lr.*/sc.*

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 其它（30 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfx2rc` | `crrr` | `cfx` | `cfx2rc cfxHA, cgHB, rcHC, rdHD` | `cfx2rc_crrr_cfx` |
| `cfx2rd` | `crrr` | `cfx` | `cfx2rd cfxHA, cgHB, rcHC, rdHD` | `cfx2rd_crrr_cfx` |
| `escape` | `ciii` | `cfx` | `escape cfxHA, [excp_cause_ip, imms20]` | `escape_ciii_cfx` |
| `fence` | `oiii` | `imm` | `fence immu18` | `fence_oiii_imm` |
| `lr.b.an` | `orrr` | `rd` | `lr.b.an rdHC, [rbHD]` | `lr.b.an_orrr_rd` |
| `lr.b.ar` | `orrr` | `rd` | `lr.b.ar rdHC, [rbHD]` | `lr.b.ar_orrr_rd` |
| `lr.b.nn` | `orrr` | `rd` | `lr.b.nn rdHC, [rbHD]` | `lr.b.nn_orrr_rd` |
| `lr.o.an` | `orrr` | `rd` | `lr.o.an rdHC, [rbHD]` | `lr.o.an_orrr_rd` |
| `lr.o.ar` | `orrr` | `rd` | `lr.o.ar rdHC, [rbHD]` | `lr.o.ar_orrr_rd` |
| `lr.o.nn` | `orrr` | `rd` | `lr.o.nn rdHC, [rbHD]` | `lr.o.nn_orrr_rd` |
| `lr.t.an` | `orrr` | `rd` | `lr.t.an rdHC, [rbHD]` | `lr.t.an_orrr_rd` |
| `lr.t.ar` | `orrr` | `rd` | `lr.t.ar rdHC, [rbHD]` | `lr.t.ar_orrr_rd` |
| `lr.t.nn` | `orrr` | `rd` | `lr.t.nn rdHC, [rbHD]` | `lr.t.nn_orrr_rd` |
| `lr.w.an` | `orrr` | `rd` | `lr.w.an rdHC, [rbHD]` | `lr.w.an_orrr_rd` |
| `lr.w.ar` | `orrr` | `rd` | `lr.w.ar rdHC, [rbHD]` | `lr.w.ar_orrr_rd` |
| `lr.w.nn` | `orrr` | `rd` | `lr.w.nn rdHC, [rbHD]` | `lr.w.nn_orrr_rd` |
| `sc.b.ar` | `orrr` | `rd` | `sc.b.ar rdHB, rdHC, [rbHD]` | `sc.b.ar_orrr_rd` |
| `sc.b.nn` | `orrr` | `rd` | `sc.b.nn rdHB, rdHC, [rbHD]` | `sc.b.nn_orrr_rd` |
| `sc.b.nr` | `orrr` | `rd` | `sc.b.nr rdHB, rdHC, [rbHD]` | `sc.b.nr_orrr_rd` |
| `sc.o.ar` | `orrr` | `rd` | `sc.o.ar rdHB, rdHC, [rbHD]` | `sc.o.ar_orrr_rd` |
| `sc.o.nn` | `orrr` | `rd` | `sc.o.nn rdHB, rdHC, [rbHD]` | `sc.o.nn_orrr_rd` |
| `sc.o.nr` | `orrr` | `rd` | `sc.o.nr rdHB, rdHC, [rbHD]` | `sc.o.nr_orrr_rd` |
| `sc.t.ar` | `orrr` | `rd` | `sc.t.ar rdHB, rdHC, [rbHD]` | `sc.t.ar_orrr_rd` |
| `sc.t.nn` | `orrr` | `rd` | `sc.t.nn rdHB, rdHC, [rbHD]` | `sc.t.nn_orrr_rd` |
| `sc.t.nr` | `orrr` | `rd` | `sc.t.nr rdHB, rdHC, [rbHD]` | `sc.t.nr_orrr_rd` |
| `sc.w.ar` | `orrr` | `rd` | `sc.w.ar rdHB, rdHC, [rbHD]` | `sc.w.ar_orrr_rd` |
| `sc.w.nn` | `orrr` | `rd` | `sc.w.nn rdHB, rdHC, [rbHD]` | `sc.w.nn_orrr_rd` |
| `sc.w.nr` | `orrr` | `rd` | `sc.w.nr rdHB, rdHC, [rbHD]` | `sc.w.nr_orrr_rd` |
| `swym` | `oiii` | `imm` | `swym immu18` | `swym_oiii_imm` |
| `trap` | `ciii` | `cfx` | `trap cfxHA, immu18` | `trap_ciii_cfx` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 2. 合法性检查


**scope: excluded（decode ILLI）：**
* `fence_oiii_imm`：decode ILLI
* `lr.b.an_orrr_rd`：decode ILLI
* `lr.b.ar_orrr_rd`：decode ILLI
* `lr.b.nn_orrr_rd`：decode ILLI
* `lr.o.an_orrr_rd`：decode ILLI
* `lr.o.ar_orrr_rd`：decode ILLI
* `lr.o.nn_orrr_rd`：decode ILLI
* `lr.t.an_orrr_rd`：decode ILLI
* `lr.t.ar_orrr_rd`：decode ILLI
* `lr.t.nn_orrr_rd`：decode ILLI
* `lr.w.an_orrr_rd`：decode ILLI
* `lr.w.ar_orrr_rd`：decode ILLI
* `lr.w.nn_orrr_rd`：decode ILLI
* `sc.b.ar_orrr_rd`：decode ILLI
* `sc.b.nn_orrr_rd`：decode ILLI
* `sc.b.nr_orrr_rd`：decode ILLI
* `sc.o.ar_orrr_rd`：decode ILLI
* `sc.o.nn_orrr_rd`：decode ILLI
* `sc.o.nr_orrr_rd`：decode ILLI
* `sc.t.ar_orrr_rd`：decode ILLI
* `sc.t.nn_orrr_rd`：decode ILLI
* `sc.t.nr_orrr_rd`：decode ILLI
* `sc.w.ar_orrr_rd`：decode ILLI
* `sc.w.nn_orrr_rd`：decode ILLI
* `sc.w.nr_orrr_rd`：decode ILLI
<!-- LEGALITY_END -->


## 3. 占位指令

当指令地址需要对齐或特意留出空白时，需要使用到占位指令。通常需要的占位指令是 no-operation 指令。SimRISC借鉴Knuth的创意，采用了 swym 助记符作为占位指令，可称之为"划水"指令。Swym一词参考Knuth的MMIX中的定义，含义为 sympathize with your machinery，Knuth是这样描述的：

> It does, however, keep the machine runnning smoothly, just as real-world swimming helps to keep programmers healthy.

操作数类型为 `oiii`：

```simrisc
swym    immu18
```

- `swym 0` 除 IP 自增外无任何架构副作用，等价于其它指令系统中的「空操作」；需要空操作/对齐时**直接书写真实指令 `swym 0`**（`nop` 伪指令已删除，见 `ADR-0013 D11`）
- `swym N` 可作为硬件时延指令，后18位立即数为时延参数：具体时延由硬件实现确定，其时延约为 `swym 0` 的 N+1 倍。
  - 硬件可设时延上限，N 超过阈值后时延不再增加。
  - 无论 N 取何值，指令仍为单条 32 位指令，不占用额外指令带宽。
- `swym` 的 op 为 0111-0111（0x77），`ha` 为 100-010（0x22），`swym 0` 的编码为 **0x77880000**。

### 3.1 nop 伪指令（已删除）

上游 `SimRISC-0.5.4` 曾定义 `nop` 伪指令；v5 **删除**（`ADR-0013 D11`），不再作为伪指令。需要空操作/对齐时，**直接书写真实指令 `swym 0`**：

```simrisc
swym    0                @@ 空操作（旧 `nop`）
```

## 4. 非法指令

ILLI（illegal instruction，非法指令）异常由**非法操作数、非法条件**或**已定义但本机器未实现的编码**触发；SimRISC 0.5.4 **不再**提供专门的非法指令助记符（原 `op=0x77, ha=0x00`）。

- 已定义编码但操作数/字段非法时触发 ILLI，例如很多指令不允许目的操作数为 `rd0`、SBZ 字段非零、多寄存器指令 `immu6 = 0` 等。
- `scope: excluded` 的已定义编码（特权 cfx、LR-SC 原子、`fence`）在未实现该语义的机器上执行时触发 ILLI（`fence`/`lr`/`sc` 的编码与命名已按 `ADR-0034` 重排，仍为 `excluded`）。
- 保留编码（QFC 主表 / MISC 子表空白单元格）触发 UNDI 异常，而非 ILLI；32 位全零指令字（0x00000000）为保留编码，触发 UNDI 异常。

## 5. 特权指令

用户态指令用于提供一个完备的应用程序运行环境，特权态指令用来进行资源管理和状态配置等功能。

特权态指令和用户态指令的指令域说明相类似。
一个32位的指令会被分解为5个部分：8/6/6/6/6，即op/ha/hb/hc/hd，其中ha专门用来指定核芯功能扩展编号。

指令中核芯功能扩展编号可以有两种写法：
- `cfx<cfxha>`：直接使用编号，如 `cfx63`、`cfx0`
- `cfx_<cfxname>`：使用名称，如 `cfx_power`、`cfx_umon`

汇编器对两种写法等价处理，均编码为 6 位的 cfxha。

trap/escape/cfx2rd/cfx2rc/cfxld/cfxst 指令可以在任意运行模式下执行，具体是否允许由各核芯功能扩展的 cfx mask 寄存器和指令类型 cfx mask 寄存器控制。详细异常路由规则见 SEE §5 异常进入流程。

### 5.1 陷入指令

陷入指令用于将控制权转移到相应核芯功能扩展的异常向量地址。

操作数类型为：`ciii`

```simrisc
trap    cfxHA, immu18
```

其中，cfx_<cfxname> 指定核芯功能扩展名称；immu18指定具体功能编号。

### 5.2 退出指令

退出指令用于退出当前的特权态，将控制权交还给陷入异常前的状态。

操作数类型为：`ciii`

```simrisc
escape  cfxHA, [excp_cause_ip, imms20]
```

其中，cfx_\<cfxname\> 指定核芯功能扩展名称；imms20 指定目标地址偏移（字节，须 `%4==0`；实际地址 = excp_cause_ip + imms20；编码层 `Addr = excp_cause_ip + (imms18 << 2)`）。

### 5.3 寄存器传输指令

这类指令用于核芯功能扩展的寄存器与rd寄存器之间进行相互赋值。

操作数类型为：`crrr`

```simrisc
cfx2rd    cfxHA, cgHB, rcHC, rdHD
cfx2rc    cfxHA, cgHB, rcHC, rdHD
```

其中，cfx_<cfxname> 指定核芯功能扩展名称，cgHB和rcHC指定该核芯功能扩展的寄存器组和寄存器号。
cfx2rc 是将 rdHD 的值设置到 cfx_<cfxname>_cgHB_rcHC 中。
cfx2rd 是将 cfx_<cfxname>_cgHB_rcHC 的值设置到 rdHD 中。

读写不存在的 cfx_<cfxname>_cgHB_rcHC 组合时触发 CFXREG 异常；cfx_<cfxname> 为 reserved 核芯功能扩展（7-14、19-61）时触发 ILLI 异常；读写权限不匹配时，触发非法核芯功能扩展寄存器访问异常（CFXREG）。

> **注意**：cfx2rd/cfx2rc 的数据通路仅连接 rd 寄存器组。若需要将 rb 或 rf 寄存器的值写入核芯功能扩展寄存器，须先通过 `rb2rd rd, rb, 1` 或 `rf2rd rd, rf, 1` 中转至 rd 寄存器。汇编器提供 `set.rd rd, rs` 伪指令简化此操作（展开为 `rb2rd`/`rf2rd`/`rd2rd`）。

为简化汇编代码的编写，寄存器传输指令支持一种简化的操作数写法，将 `cfx_<cfxname>, cgHB, rcHC` 三个参数合并为 `cfx_⟨cfxname⟩_regname` 的形式，其中 `regname` 为寄存器名称（即 SEE 文档 regname 列中的名称）。汇编器会根据寄存器名称自动查找对应的 cg 和 rc 编号，展开为标准的三个操作数格式。

```simrisc
@@ 简化写法（推荐）
cfx2rd  cfx_umon_excp_cause_ip, rd2    @@ 读取 cfx_umon 的 excp_cause_ip
cfx2rc  cfx_power_ctrl, rd2             @@ 写入 cfx_power 的 power_ctrl

@@ 等价的标准写法
cfx2rd  cfx_umon, cg5, rc3, rd2
cfx2rc  cfx_power, cg8, rc1, rd2
```

这种简化写法使代码更具可读性，程序员无需记忆每个寄存器的cg和rc编号，直接通过寄存器名称即可定位目标寄存器。

## 6. 原子指令

### 6.1 fence指令

fence 指令对外部可见的访存请求,如设备 I/O 和内存访问等进行串行化。

操作数类型为：`oiii`

```simrisc
fence   immu18
```

`fence immu18` 的 18 位立即数**不拆成三段操作数**，汇编层仍书写一个 18 位无符号立即数；其位域为：

| 字段 | 位 | 含义 |
| --- | --- | --- |
| `fm` | `immu18[17:12]` | 屏障模式（fence mode） |
| `pred` | `immu18[11:6]` | 前序（predecessor）访问类型集合 |
| `succ` | `immu18[5:0]` | 后序（successor）访问类型集合 |

`pred`/`succ` 的位含义为 R/W/I/O 四类访问（`R` 读、`W` 写、`I`/`O` 为设备 I/O 访问，RISC-V `fence` 口径）；汇编层提供八个符号常量，按位或（`|`）组合：

| 访问类型 | `pred` 常量（值） | `succ` 常量（值） |
| --- | --- | --- |
| R | `PRED_R = 1<<6` | `SUCC_R = 1<<0` |
| W | `PRED_W = 1<<7` | `SUCC_W = 1<<1` |
| I | `PRED_I = 1<<8` | `SUCC_I = 1<<2` |
| O | `PRED_O = 1<<9` | `SUCC_O = 1<<3` |

例：`fence PRED_R|PRED_W|SUCC_R|SUCC_W`（= `immu18` 的 `0x00C3`，即 `pred = 000011`、`succ = 000011`）。

`fm` 取值：

| `fm` | 含义 |
| --- | --- |
| `0` | 已定义（常规屏障） |
| `8` | TSO 预留（当前未定义） |
| 其余 | 保留 |

保留编码 ⇒ ILLI：

- `fm ≠ 0`（其中 `fm = 8` 标注为「TSO 预留、当前未定义」）；
- `pred` 的 `immu18[11:10]` 与 `succ` 的 `immu18[5:4]` 为 SBZ，非零即保留。

### 6.2 LR-SC指令

LR 指令是 Load Reserved 的缩写，读取保留；SC 指令是 Store Conditional 的缩写，条件存储。设计参考 RISC-V RV64A 扩展（A 扩展）。

操作数类型为：`orrr`。lr 指令的 hb（rdHB）固定为 rd0，汇编代码仅需两个操作数。若手工编码时 hb ≠ 0，触发 ILLI 异常。

指令名形如 `<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>`——**数据宽度在前、存储序在后**，以 `.` 分隔：

```simrisc
lr.o.nn   rdHC, [rbHD]
lr.t.nn   rdHC, [rbHD]
lr.w.nn   rdHC, [rbHD]
lr.b.nn   rdHC, [rbHD]
lr.o.an   rdHC, [rbHD]
lr.t.an   rdHC, [rbHD]
lr.w.an   rdHC, [rbHD]
lr.b.an   rdHC, [rbHD]
lr.o.ar   rdHC, [rbHD]
lr.t.ar   rdHC, [rbHD]
lr.w.ar   rdHC, [rbHD]
lr.b.ar   rdHC, [rbHD]

sc.o.nn   rdHB, rdHC, [rbHD]
sc.t.nn   rdHB, rdHC, [rbHD]
sc.w.nn   rdHB, rdHC, [rbHD]
sc.b.nn   rdHB, rdHC, [rbHD]
sc.o.nr   rdHB, rdHC, [rbHD]
sc.t.nr   rdHB, rdHC, [rbHD]
sc.w.nr   rdHB, rdHC, [rbHD]
sc.b.nr   rdHB, rdHC, [rbHD]
sc.o.ar   rdHB, rdHC, [rbHD]
sc.t.ar   rdHB, rdHC, [rbHD]
sc.w.ar   rdHB, rdHC, [rbHD]
sc.b.ar   rdHB, rdHC, [rbHD]
```

o是 octa 的缩写，表示存取的数据是64位；t是 tetra 的缩写（32位）；w是 wyde 的缩写（16位）；b是 byte 的缩写（8位）。

`lr` 仅有 `nn`/`an`/`ar` 三种存储序（无 `nr`）；`sc` 仅有 `nn`/`nr`/`ar` 三种存储序（无 `an`）。其余组合的助记符不存在（汇编器拒绝），对应编码为 reserved。
a是 acquire 的缩写，表示该指令后序所有访问存储的指令不得被重排到该指令之前执行。
r是 release 的缩写，表示该指令前序所有访问存储的指令不得被重排到该指令之后执行。
n表示没有对应的a或r的顺序限制。

lr 指令是从内存地址 rbHD 中加载内容到 rdHC 寄存器，然后在 rbHD 对应地址上设置保留标记（reservation set）。
sc 指令会先判断 rbHD 内存地址是否有设置保留标记，如果设置了，则把 rdHC 值正常写入到 rbHD 内存地址里，并把 rdHB 寄存器设置成 0，表示写入成功；如果 rbHD 内存地址没有设置保留标记，则不执行写入操作，并把 rdHB 寄存器设置成 1， 表示写入失败；不管成功还是失败，sc 指令都会把当前 hart 上的所有保留标记全部清除。

对于 lr/sc 指令，要求 rbHD 寄存器中的地址**按数据宽度自然对齐**（`.b`=1 / `.w`=2 / `.t`=4 / `.o`=8 字节），否则触发 **MALIGN** 异常。

> **保留机制**（参考 RISC-V RV64A）：一条 lr 指令在 hart 上设置保留标记。sc 指令在保留标记仍在时写入内存并返回 0，否则不写入并返回非 0 值。sc 可能偶发性失败（spurious failure），软件应在循环中重试。以下事件清除 hart 上的保留标记：另一 hart 对保留地址的 store（或另一 hart 对保留地址所在 cache line 的 store，取决于平台实现的保留粒度）、当前 hart 执行另一条 lr 指令、异常或中断进入。如果 hart 在 lr 和 sc 之间执行了异常处理程序，sc 必定失败。保留标记的粒度由平台定义（可实现为精确地址或 cache line）。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- `trap`/`escape`/`cfx2rc`/`cfx2rd` 重新划分 scope（M5）。
- 伪指令集收缩：删除 `nop` 等 1:1 别名伪指令。
- 删除 `illi` 指令；`fence` 编码改 `0x00`、`swym` 编码改 `0x22`；引入 `scope` 标注。
- 汇编规范文档更新。
- 迁移新汇编格式、术语 `cfxcode`→`cfxha`。
- 新增「合法性检查」章（生成区）。
- `MISC-AMO` 编码移至 `0111-0111`；术语 `major-op`→`opc`、`minor-op`→`opx`。
- 正文术语 `PC` 统一为 **`IP`**（`swym 0` 条：`IP` = 当前正在执行的指令的地址；见 SimRISC-00 §基址寄存器）。
- cfx 系列记法约定；cfx 字段重命名（`cfxha`/`cghb`/`rchc`/`rdhd`）。
- 新增「汇编指令速查」章（生成区）。
- 新增「原子指令」章（`fence` / `lr`·`sc`），由 `SimRISC-12` 原样迁入；汇编速查与合法性检查生成区随之纳入（分类由「待定」改为「其它」）。

### 0.5.4（2026-09-28）

- 本册由原《SimRISC 系统类指令》演进（占位 / 非法 / 特权指令部分）；`swym`/`illi` 独立成二级标题，`nop` 伪指令归入本册。

### 0.5.3（2026-07-19）

- `MISC` 表重排，`illi` 移入 MISC-octa。

### 0.5.2（2026-07-18）

- `swym` 改 iiii 格式、`unimp`→`illi`（并为二者设独立二级标题）。

### 0.5.1（2026-07-16）

- `RASUP`→`RASUF`；特权模型与 SEE 对齐，删冗余 ILLI 声明。

### 0.5.0（2026-07-15）

- `swym`/`unimp` 编码整理（`swym`→iiii、`unimp`→MISC-Norm）。

### 0.4.1（2026-07-14）

- 初版：同步上游系统类指令（占位 / 非法 / 特权）。
