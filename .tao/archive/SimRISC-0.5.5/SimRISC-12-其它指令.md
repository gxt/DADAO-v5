# SimRISC其它指令

> **版本：0.5.5**（与 SimRISC-00 一致）
> **分类：其它指令** — fence/lr.*/sc.*/swym/ctlz/cttz/ctpop

## 1. 原子指令

### 1.1 fence指令

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

### 1.2 LR-SC指令

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

## 2. 空转指令

当指令地址需要对齐或特意留出空白时，需要使用到空转指令。通常需要的空转指令是 no-operation 指令。SimRISC借鉴Knuth的创意，采用了 swym 助记符作为空转指令，可称之为"划水"指令。Swym一词参考Knuth的MMIX中的定义，含义为 sympathize with your machinery，Knuth是这样描述的：

> It does, however, keep the machine runnning smoothly, just as real-world swimming helps to keep programmers healthy.

操作数类型为 `oiii`：

```simrisc
swym    immu18
```

- `swym 0` 除 IP 自增外无任何架构副作用，等价于其它指令系统中的「空操作」；需要空操作/对齐时**直接书写真实指令 `swym 0`**
- `swym N` 可作为硬件时延指令，后18位立即数为时延参数：具体时延由硬件实现确定，其时延约为 `swym 0` 的 N+1 倍。
  - 硬件可设时延上限，N 超过阈值后时延不再增加。
  - 无论 N 取何值，指令仍为单条 32 位指令，不占用额外指令带宽。

## 3. 位扫描与位计数 ctlz/cttz/ctpop（orri 格式）

`ctlz`/`cttz`/`ctpop` 提供**位扫描与位计数**。三条指令**没有位宽后缀**（指令名不指示
8/16/32/64 位）——有效位宽由操作数给出的**有效位上界 `hd`** 在运行时确定：参与运算的
是源的**低 `hd+1` 位** `rdHC[hd:0]`，`hd` 以上的位**不参与**运算。

`hd` = `orri` 立即数（`immu6`，6 位无符号，`0..63`）= **有效位上界**：

```
valid = rdHC[hd:0]        // 共 hd+1 位；rdHC[63:hd+1] 不参与运算
```

| 指令 | 语义（均在有效位 `rdHC[hd:0]` 内） | 定值（`rdHC[hd:0]` 全 0） |
|------|-----------------------------------|--------------------------|
| `ctlz` | 从 bit `hd` **向下**数的**前导零**个数 | `hd + 1` |
| `cttz` | 从 bit 0 **向上**数的**末尾零**个数（到 bit `hd` 止） | `hd + 1` |
| `ctpop` | `rdHC[hd:0]` 内 **1 的个数** | `0` |

```
n = 0; for i = hd down to 0:  if rdHC[i] == 1: break;  n++    // ctlz → n
n = 0; for i = 0  up to   hd: if rdHC[i] == 1: break;  n++    // cttz → n
n = 0; for i = 0  to      hd: n += rdHC[i]                    // ctpop → n
```

- **结果 ∈ `0..64`，写满 64 位**（值语义，高位置 0；非「只写低位」）。
- **定值**：`rdHC[hd:0]` **全 0** 时 `ctlz` = `cttz` = **`hd + 1`**（= 有效位范围宽度，
  **消除未定义行为**）；口径与 RISC-V `clz`/`ctz`（返回 XLEN）、x86 `lzcnt`/`tzcnt`
  （返回操作数宽度）、ARM `CLZ(0)`（= 32/64）一致。对比 C 的 `__builtin_clz(0)` 为 **UB**，
  本指令**不是** UB。`ctpop(0)` = `0`（自然值，无特例）。
- **合法性**：`hd ∈ 0..63`（6 位立即数域）⇒ **全部合法**，**无非法 `hd` 值**，**不新增**
  合法性规则；沿用既有规则 `dst_rd0` —— `rdHB`（目的）不得为 `rd0`。`rdHC` **可为 `rd0`**
  （读出 0 ⇒ 结果 = `hd+1` 或 `0`，合法）；`rdHB == rdHC` **允许**（原地运算）。

用途映射（供后端参考）：`ctlz` **单条**即覆盖 `clz8`/`clz16`/`clz32`/`clz64`
（`hd` = 7/15/31/63），对比 RISC-V 需 `clz` + `clzw` 两条才覆盖到 32 位；`ctlz`/`cttz`/`ctpop`
分别与 LLVM `int_ctlz`/`int_cttz`/`int_ctpop`、C++20 `std::countl_zero`/`countr_zero`/`popcount`
一一对应。

```simrisc
ctlz    rdHB, rdHC, immu6       @@ 前导零（immu6=63 → 64 位；immu6=31 → 32 位；全 0 → immu6+1）
cttz    rdHB, rdHC, immu6       @@ 末尾零（immu6=63 → 64 位；全 0 → immu6+1）
ctpop   rdHB, rdHC, immu6       @@ 1 的个数（immu6=63 → 64 位）
```

**格式**：三条为 `orri` 格式但**无位宽后缀**，位于 `OPC-MISC` 子表的 `100-101`/`100-110`/`100-111` 格位（见 SimRISC-00 §4.1）；**有效位宽**由立即数 `hd` 在运行时给出。

<!-- ASSEMBLY_LIST_START -->
## 附录 A：汇编指令速查

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `ctlz` | `orri` | `rd` | `ctlz rdHB, rdHC, immu6` | `ctlz_orri_rd` |
| `ctpop` | `orri` | `rd` | `ctpop rdHB, rdHC, immu6` | `ctpop_orri_rd` |
| `cttz` | `orri` | `rd` | `cttz rdHB, rdHC, immu6` | `cttz_orri_rd` |
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

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 附录 B：合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `ctlz_orri_rd`, `ctpop_orri_rd`, `cttz_orri_rd`（3 条）
* `encode_sbz`：SBZ 非零 → ILLI — `fence_oiii_imm`（1 条）
<!-- LEGALITY_END -->
