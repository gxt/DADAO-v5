# SimRISC寄存器复制指令

> **版本：0.5.4**（与 SimRISC-00 一致）
> **分类：寄存器复制**（18 条）— cs.*/ra2rd/rb2rb/rb2rd/rd2ra/rd2rb/rd2rd/rd2rf/rf2rd

<!-- ASSEMBLY_LIST_START -->
## 汇编指令速查

### 寄存器复制（18 条）

| 助记符 | format | feature | 汇编形式 | id |
|---|---|---|---|---|
| `cs.eq` | `rrrr` | `rd` | `cs.eq {rdHA, rdHB}?, rdHC, rdHD` | `cs.eq_rrrr_rd` |
| `cs.eq` | `rrrr` | `rf` | `cs.eq {rdHA, rdHB}?, rfHC, rfHD` | `cs.eq_rrrr_rf` |
| `cs.n` | `rrrr` | `rd` | `cs.n {rdHA}?, rdHB, rdHC, rdHD` | `cs.n_rrrr_rd` |
| `cs.n` | `rrrr` | `rf` | `cs.n {rdHA}?, rfHB, rfHC, rfHD` | `cs.n_rrrr_rf` |
| `cs.ne` | `rrrr` | `rd` | `cs.ne {rdHA, rdHB}?, rdHC, rdHD` | `cs.ne_rrrr_rd` |
| `cs.ne` | `rrrr` | `rf` | `cs.ne {rdHA, rdHB}?, rfHC, rfHD` | `cs.ne_rrrr_rf` |
| `cs.p` | `rrrr` | `rd` | `cs.p {rdHA}?, rdHB, rdHC, rdHD` | `cs.p_rrrr_rd` |
| `cs.p` | `rrrr` | `rf` | `cs.p {rdHA}?, rfHB, rfHC, rfHD` | `cs.p_rrrr_rf` |
| `cs.z` | `rrrr` | `rd` | `cs.z {rdHA}?, rdHB, rdHC, rdHD` | `cs.z_rrrr_rd` |
| `cs.z` | `rrrr` | `rf` | `cs.z {rdHA}?, rfHB, rfHC, rfHD` | `cs.z_rrrr_rf` |
| `ra2rd` | `orri` | `ra` | `ra2rd {rdHB:rdHB+immu6-1}, {raHC:raHC+immu6-1}` | `ra2rd_orri_ra` |
| `rb2rb` | `orri` | `rb` | `rb2rb {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}` | `rb2rb_orri_rb` |
| `rb2rd` | `orri` | `rb` | `rb2rd {rdHB:rdHB+immu6-1}, {rbHC:rbHC+immu6-1}` | `rb2rd_orri_rb` |
| `rd2ra` | `orri` | `ra` | `rd2ra {raHB:raHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2ra_orri_ra` |
| `rd2rb` | `orri` | `rb` | `rd2rb {rbHB:rbHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2rb_orri_rb` |
| `rd2rd` | `orri` | `rd` | `rd2rd {rdHB:rdHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2rd_orri_rd` |
| `rd2rf` | `orri` | `rf` | `rd2rf {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}` | `rd2rf_orri_rf` |
| `rf2rd` | `orri` | `rf` | `rf2rd {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}` | `rf2rd_orri_rf` |

<!-- ASSEMBLY_LIST_END -->

<!-- LEGALITY_START -->
## 合法性检查

* `dst_rd0`：目的 rd0 → ILLI — `cs.eq_rrrr_rd`, `cs.n_rrrr_rd`, `cs.ne_rrrr_rd`, `cs.p_rrrr_rd`, `cs.z_rrrr_rd`, `ra2rd_orri_ra`, `rb2rd_orri_rb`, `rd2rd_orri_rd`（8 条）
* `dst_rb0`：目的 rb0 → ILLI — `rb2rb_orri_rb`, `rd2rb_orri_rb`（2 条）
* `mreg_zero`：immu6=0 → ILLI — `ra2rd_orri_ra`, `rb2rb_orri_rb`, `rb2rd_orri_rb`, `rd2ra_orri_ra`, `rd2rb_orri_rb`, `rd2rd_orri_rd`（6 条）
* `mreg_range_overflow`：起始+immu6>64 → ILLI — `ra2rd_orri_ra`, `rb2rb_orri_rb`, `rb2rd_orri_rb`, `rd2ra_orri_ra`, `rd2rb_orri_rb`, `rd2rd_orri_rd`（6 条）
* `mreg_range_overlap`：源/目的范围交集 → ILLI — `rb2rb_orri_rb`, `rd2rd_orri_rd`（2 条）

**excluded_m1（decode ILLI）：**
* `cs.eq_rrrr_rf`：decode ILLI
* `cs.n_rrrr_rf`：decode ILLI
* `cs.ne_rrrr_rf`：decode ILLI
* `cs.p_rrrr_rf`：decode ILLI
* `cs.z_rrrr_rf`：decode ILLI
* `rd2rf_orri_rf`：decode ILLI
* `rf2rd_orri_rf`：decode ILLI
<!-- LEGALITY_END -->


## 赋值类指令

> **立即数常数赋值**（rwii 格式：set.zw/set.ow/set.w/or.w/andn.w 的 rd/rb/rf 形式，以及 set.rd/set.rb/set.ft/set.fo 伪指令）详见 SimRISC-03（16位立即数操作）。

### 寄存器组之间块赋值

不同寄存器组或相同寄存器组之间，可以互相进行块传输，块传输过程中不进行数据类型的转换，保持64位二进制不变，但是必需是多个连续的寄存器。
操作数类型为 `orri`，指令如下：

```simrisc
rd2rd   {rdHB:rdHB+immu6-1}, {rdHC:rdHC+immu6-1}

rb2rd   {rdHB:rdHB+immu6-1}, {rbHC:rbHC+immu6-1}
rd2rb   {rbHB:rbHB+immu6-1}, {rdHC:rdHC+immu6-1}
rb2rb   {rbHB:rbHB+immu6-1}, {rbHC:rbHC+immu6-1}

ra2rd   {rdHB:rdHB+immu6-1}, {raHC:raHC+immu6-1}
rd2ra   {raHB:raHB+immu6-1}, {rdHC:rdHC+immu6-1}

rf2rd   {rdHB:rdHB+immu6-1}, {rfHC:rfHC+immu6-1}
rd2rf   {rfHB:rfHB+immu6-1}, {rdHC:rdHC+immu6-1}
```

以 `rb2rd` 为例，指令语义为，将rbHC开始的immu6个寄存器复制到rdHB开始的immu6个寄存器中。
immu6为立即数，存在hd位域中，用来指定寄存器的个数，有效范围为1~63。

限制如下：

- 根据语义，rb/rf/ra之间不能进行直接赋值，ra与ra之间不能进行相互赋值
- `immu6` = 0 时触发 ILLI 异常
- 目的寄存器**不可为 `rd0`/`rb0`**时触发 ILLI 异常；`ra0`（`RACNT` + `MRPTR`，见 D7）与 `rf0`（FCSR，见 D6）作目的**合法**（见 SimRISC-01 §存取RA寄存器、SimRISC-00 §浮点状态寄存器）。
- 任一起始寄存器 + immu6 > 64 时触发 ILLI 异常
- 源范围与目的范围有交集时触发 ILLI 异常（即不允许源和目的寄存器范围有任何重叠）

> **注**：`rd2rf` 中 `rf0` 可作目的（含 `{rf0:rf0+immu6-1}`，immu6≥2 允许），写入按 SimRISC-00 写语义（只更新舍入模式与异常状态，其余位写无效）；`rf2rd` 中 `rf0` 可作源，读出完整 64 位。

### 条件赋值：Conditional Assignment

第一类条件赋值指令需要先根据`rdHA`的内容进行条件判断，然后分别将`rdHC`或`rdHD`赋值给`rdHB`，即 `if (rdHA is negative/zero/positive) rdHB = rdHC; else rdHB = rdHD`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.n    {rdHA}?, rdHB, rdHC, rdHD
cs.z    {rdHA}?, rdHB, rdHC, rdHD
cs.p    {rdHA}?, rdHB, rdHC, rdHD
```

第二类条件赋值指令需要先根据`rdHA`与`rdHB`是否相等进行条件判断，如果条件成立则将`rdHD`的值赋值给`rdHC`，即 `if (rdHA ==/!= rdHB) rdHC = rdHD`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.eq   {rdHA, rdHB}?, rdHC, rdHD
cs.ne   {rdHA, rdHB}?, rdHC, rdHD
```

> **注**：rd0 目的寄存器约定见 SimRISC-00。

### 浮点条件赋值

第一类浮点条件赋值指令需要先根据`rdHA`的内容进行条件判断，然后分别将`rfHC`或`rfHD`赋值给`rfHB`，即 `if (rdHA is negative/zero/positive) rfHB = rfHC; else rfHB = rfHD`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.n    {rdHA}?, rfHB, rfHC, rfHD
cs.z    {rdHA}?, rfHB, rfHC, rfHD
cs.p    {rdHA}?, rfHB, rfHC, rfHD
```

第二类浮点条件赋值指令需要先判断`rdHA`与`rdHB`是否相等，如果条件成立则将`rfHD`的值赋值给`rfHC`，即 `if (rdHA ==/!= rdHB) rfHC = rfHD`。
操作数类型为 `rrrr`，指令如下：

```simrisc
cs.eq   {rdHA, rdHB}?, rfHC, rfHD
cs.ne   {rdHA, rdHB}?, rfHC, rfHD
```

此类指令与浮点比较指令配合使用（比较结果编码见 SimRISC-07 §浮点比较指令）。浮点比较结果存放在 rd 寄存器中：`1`（大于）、`0`（等于）、`-1`（小于）、NaN（unordered）。浮点比较结果为 NaN 时，其值按整型解读是**正数**，且**不等于 1**。若要检测比较结果是否为 1（大于），先将 1 加载到某个 rd 寄存器，再与比较结果做 `cs.eq`；若要检测是否不为 0（不相等），用 `cs.ne` 判断即可。若在已确认结果为正数（通过 `cs.p` 排除 0 和 -1）的前提下需进一步区分正数 1 与 NaN，检查结果是否为 1（bits[63:1]=0 且 bit0=1），否则为 NaN。

> **注**：`cs.eq`/`cs.ne`/`cs.n`/`cs.z`/`cs.p` 的 rf 变体中，**目的**（`rfHB`/`rfHC`）为 `rf0` → ILLI；**源**（`rfHC`/`rfHD`）为 `rf0` 合法（`rf0` 作源读出完整 64 位）。