# SimRISC待定指令

> **版本：0.5.5-rc**（与 SimRISC-00 一致）
> **分类：待定 [deferred]**（27 条）— cfxld/cfxst/fence/lr.*/sc.*

<!-- ASSEMBLY_LIST_START -->
## 1. 汇编指令速查

### 1.1 待定（27 条）｜ **deferred** — 暂不归类，待必须启用时

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cfxld` | `crii` | `cfx` | `cfxld cfxHA, [rbHB, immu12]` | `cfxld_crii_cfx` |
| `cfxst` | `crii` | `cfx` | `cfxst cfxHA, [rbHB, immu12]` | `cfxst_crii_cfx` |
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

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 2. 合法性检查


**scope: excluded（decode ILLI）：**
* `cfxld_crii_cfx`：decode ILLI
* `cfxst_crii_cfx`：decode ILLI
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


## 3. 原子指令

### 3.1 fence指令

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

### 3.2 LR-SC指令

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

对于 lr/sc 指令，要求 rbHD 寄存器中的地址是按数据宽度对齐的，即8字节对齐，否则会触发 MALIGN 异常。

> **保留机制**（参考 RISC-V RV64A）：一条 lr 指令在 hart 上设置保留标记。sc 指令在保留标记仍在时写入内存并返回 0，否则不写入并返回非 0 值。sc 可能偶发性失败（spurious failure），软件应在循环中重试。以下事件清除 hart 上的保留标记：另一 hart 对保留地址的 store（或另一 hart 对保留地址所在 cache line 的 store，取决于平台实现的保留粒度）、当前 hart 执行另一条 lr 指令、异常或中断进入。如果 hart 在 lr 和 sc 之间执行了异常处理程序，sc 必定失败。保留标记的粒度由平台定义（可实现为精确地址或 cache line）。

## 4. SRAM块传输指令

这类指令用于核芯功能扩展的内部存储与内存之间的块传输，要求 64 字节对齐，并且是 64 字节的倍数。

操作数类型为：`crii`

```simrisc
cfxld    cfxHA, [rbHB, immu12]
cfxst    cfxHA, [rbHB, immu12]
```

其中：
- cfx_<cfxname> 指定核芯功能扩展名称。
- rbHB 指定内存地址，要求 64 字节对齐。
- 传输长度 = immu12 × 64 字节。
- 内部存储侧的目标块由 `cfx_⟨cfxname⟩_sram_block_sel`（cg7 rc0）选择，块内起始偏移由 `cfx_⟨cfxname⟩_sram_addr`（cg7 rc1）指定。`cfx_⟨cfxname⟩_sram_addr` 及内存侧 `rbHB` 均需 64 字节对齐。
- cfxld：将内存数据传输到核芯功能扩展的内部存储中。
- cfxst：将核芯功能扩展的内部存储数据传输到内存中。
- 若 cfx_<cfxname> 为 reserved 核芯功能扩展（7-14、19-61），触发 ILLI 异常。

---

## 附录：版本与变更记录

> **发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期，再于其上方新开空 `-rc` 段。

### 0.5.5-rc（未发布）

- 标题章节号统一为 `N` / `N.M` / `N.M.K`。
- `fence` 编码改 `100-000`（`ha=0x20`），`immu18` 按 `fm[17:12]`/`pred[11:6]`/`succ[5:0]` 解释，新增 `PRED_*`/`SUCC_*` 常量与 `|` 组合写法。
- LR-SC 改名并重排编码：`<lr|sc>.<b|w|t|o>.<nn|an|nr|ar>` 共 24 条；删除 `lr.*.nr` 与 `sc.*.an`；语义不变、仍 `scope: excluded`。
- 引入 `scope: excluded`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）。
- 新增「合法性检查」章（生成区）。
- 全量删除 `rela.si`；0 号寄存器作源操作数语义澄清。
- cfx 系列记法约定；cfx 字段重命名。
- 新增「汇编指令速查」章（生成区）。

### 0.5.4（2026-09-28）

- 本册由原《SimRISC 系统类指令》的原子指令部分拆出，独立成「待定」分册（`fence` / LR-SC / `cfxld`/`cfxst` / SRAM 块传输）。

### 0.5.2（2026-07-18）

- 修复 `lr`/`sc` 描述不一致；`fence` 编码整理。

### 0.4.1（2026-07-14）

- 初版：同步上游原子指令（`fence` / LR-SC）。
