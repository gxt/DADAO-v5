# M1 与 FP 指令逐条 golden 判定说明

本文件为每个标量**指令身份**单列一节，描述“给定执行前状态，应得到什么结果”。同名指令的不同格式、位宽、寄存器组均分开说明。本文是当前规范的可读投影，不是新增ISA规范；若与规范正文冲突，应报告并裁定，不能以本文覆盖规范。

**使用范围**：原有整数、RD/RB/RA访存与传送、地址运算、控制流、swym，以及合约中 66 条 RF/浮点指令。后来新增的特权指令、原子指令和 fence 仍未实现。浮点转整数的 NX、`rootn(-0,2)`及部分 remainder/scaleB 边界仍待规范裁定；不能据此声称完整符合所有输入。

**阅读顺序**：先读共同规则，再按目录查指令。每条包含独立的操作数解释、编码字段、计算步骤、异常/边界、例子和依据。例子仅用于解释，不代表穷尽测试。

**维护方式**：语义文字在 `generate_instruction_guide.py` 中按规范编写，编码身份/位域来自 `contracts/opcodes.yaml`；生成器不导入解释器，不从LLVM/QEMU计算期望。运行 `python3 -B ./components/golden/generate_instruction_guide.py` 更新，`--check` 检查产物一致；一致不等于语义证明。

## 共同规则

这一节解释后文反复使用的概念。阅读某条指令时，应将这里的共同约定与该条指令的具体规则一起使用。例如，条目中写“结果写入目的寄存器”，默认还包括本节说明的旧值读取、PC推进和异常时不提交修改等要求。

这里需要区分三种信息：**架构规范规定的行为**、**golden为了运行测试采用的模型约定**，以及**当前模型尚不能给出答案的情况**。下面会分别说明，避免把模型的简化当成硬件必须遵守的规则。

### 1. golden的一步执行，输入和输出分别是什么

本模型一次执行一条32位机器指令。输入除了指令字，还包括执行前的寄存器值、内存内容和当前指令地址。golden根据这些输入计算本条指令的效果，返回执行后的状态，或者返回本条指令触发的架构异常。

例如，执行一条加法时，需要知道两个源寄存器的旧值；执行一次加载时，还需要知道基址寄存器、偏移量和相应内存位置的内容。因此，只给出“执行add”不足以确定正确答案，必须同时明确操作数和执行前状态。

模型中的 `run()` 不会自动从内存取下一条指令。需要连续执行时，由调用者提供下一条机器指令，并把上一步返回的状态作为新的输入。执行成功后，返回状态中的PC已经指向下一条指令；执行失败时，本条指令的修改不会提交。

后文中的算例只列出与解释有关的输入。正式编写测试时，还应给出需要检查的结果；没有写进断言的寄存器或内存，不能视为已经验证。

### 2. 如何读寄存器名和操作数字段

DADAO有RD、RB、RA、RF四组寄存器，每组64个，每个寄存器64位。RD主要用于整数数据，RB用于基址和地址运算，RA用于返回地址栈，RF用于浮点。本次golden执行前三组相关的标量指令与 RF 浮点指令；浮点有限值由独立整数/有理数 oracle 计算，不使用宿主浮点结果。

`rd1` 是一个具体寄存器名，而 `rdha` 是指令格式中的占位名称，表示“由ha字段指定的RD寄存器”。例如，ha字段的值为3时，`RD[ha]` 就是 `rd3`。`RB[hb]`、`RA[hc]` 等写法也按这个方法理解。

本文计算式右侧出现的寄存器值，除非明确说明为中间结果，均指**本条指令执行前的值**。这样才能正确处理源和目的使用同一寄存器的情况。例如，一条运算同时读取并写入rd3，计算时使用的是旧rd3，不能先写入结果再把新值当作源。双目的运算也必须先取得两个源值，再写高、低两个结果。

多寄存器加载同样需要保存原始地址。例如，加载范围恰好覆盖了用作索引的RD寄存器，后续元素仍按最初的基址和索引计算地址，不能因前一次加载改写了索引而改变地址。

### 3. 零号寄存器不能一概视为普通寄存器

`rd0` 固定读出0。它可以作为整数运算和存数的源，但通常不能作为目的：这种非法目的应触发ILLI，不能只把写入丢掉就算执行成功。当前范围中的两个例外是：双目的加减乘允许其中一个目的为rd0，用于丢弃对应半结果；`ret rd0, 0` 允许只返回、不设置返回值。双目的同时为rd0，或者 `ret rd0, 非零立即数`，仍然非法。

`rb0` 保存当前控制流值。指令读取它时，得到的是**本条指令执行前**的值，而不是自动加4后的值。它可以作为基址或存数源，但不能作为普通指令的显式目的；成功执行后对rb0的推进或跳转更新，由控制流规则完成。

`ra0` 与rd0不同，它不是常数零，而是可读写的返回栈管理寄存器。对它的写入要遵守后文的字段限制。RF组的rf0是FCSR，其读写规则及其余浮点寄存器语义见浮点逐条说明。

因此，判断0号操作数是否合法时，必须同时看**寄存器组、源/目的角色和具体指令**。尤其要注意：从rd0存数表示存入0，从rb0存数表示存入当前rb0值，两者在现行规范下都是合法的。

### 4. 位宽、有符号数和结果写回

寄存器虽然都是64位，一条指令实际参与运算的数据却可能只有8、16、32或64位。后缀b、w、t、o分别表示这四种宽度。本文用W表示当前运算宽度。

`x mod 2^W` 表示只保留x的低W位。例如，在8位范围内，`0x1234` 只保留为 `0x34`；255加1后保留低8位，结果是0。这种截断是定宽运算的一部分，不自动等于触发溢出异常。

同一串位如何解释，取决于指令的有符号或无符号属性。例如，8位的 `0xFF` 按无符号数解释是255，按有符号补码解释是−1。有符号运算应以**当前运算宽度的最高位**判断符号，不能直接拿原64位寄存器的bit63代替8位运算的bit7。

将窄结果写回64位寄存器时，主要有两种扩展方式：

| 写回方式 | 做法 | 8位结果0x80写回64位的例子 |
| --- | --- | --- |
| 零扩展 | 结果放在低位，新增高位全部填0 | `0x0000000000000080` |
| 符号扩展 | 结果放在低位，新增高位复制窄结果的符号位 | `0xFFFFFFFFFFFFFF80` |

当前定宽算术、比较和移位按各自后缀扩展，**写满目的寄存器的64位**。目的寄存器旧高位不会被保留。与此不同，`or.w`、`andn.w` 这类16位段操作只改指定段，其他段保留旧值；应以每条指令的写回说明为准。

比较产生−1、0或1后，也要应用相应的扩展规则。例如，8位无符号比较中“小于”的结果是 `0x00000000000000FF`；8位有符号比较中“小于”的结果是 `0xFFFFFFFFFFFFFFFF`。不要把两者都写成同一个64位−1。

有符号除法采用向零截断：−7除以3的商为−2，余数为−1。计算golden时不能直接用Python对负数的向下取整除法替代。除零和最小负数除以−1在现行整数规范中有明确的定值结果，详见各条除余指令；它们不再一律触发ILLI。

本架构不通过一个额外的整数条件码寄存器保存这类运算结果。后续分支通常读取数据寄存器的值来判断条件。

### 5. PC、rb0和下一条指令地址的关系

需要同时保留两个概念：**参与地址计算的完整64位控制流值**，以及**实际用于取指的低48位地址**。模型用 `rb0` 保存前者，用 `pc` 保存后者。两者的低48位应当一致。

对于成功执行的普通指令，完整控制流值按64位加4；对于分支、jump、call和ret，则按相应条目计算新值。新的完整值写入rb0，再取其低48位作为下一条取指地址。模型返回成功状态时，`pc` 和 `pc_next` 都表示这个下一取指地址；`pc_next` 是模型接口字段，不是额外的硬件寄存器。

例如，当前rb0为 `0x0000FFFFFFFFFFFC`，顺序执行一条指令后，rb0变为 `0x0001000000000000`，而下一取指地址为0。这个例子说明：不能先把rb0截成48位并丢弃进位，再声称完整控制流值已经正确更新。

相对跳转的基准是当前rb0。例如，当前地址为0x1000，分支立即数为2且条件成立时，目标为 `0x1000 + 2×4 = 0x1008`，不是0x100C。偏移立即数的单位是指令字，即4字节；访存指令的字节偏移则不能套用这个乘4规则。

如果jump产生了一个低两位非0的目标，本条jump先完成；下一次尝试从该地址取指时才报告IALIGN。不要把下一次取指的异常提前当成本条jump自身的失败。

默认测试入口 `0xFC0000000000` 来自当前向量约定。它不是本模型对芯片硬件复位地址的规定，调用者可以提供其他起始地址。

### 6. 内存中的字节顺序和地址范围

内存按字节寻址，数据采用大端顺序，即一个多字节数的高字节放在较低地址。例如，把32位值 `0x12345678` 存到0x1000后，0x1000、0x1001、0x1002、0x1003四个地址依次存放12、34、56、78这四个十六进制字节。

实际访存使用计算结果的低48位。RB中的高16位在普通寄存器运算中仍然有效，不能因为它以后可能被用作地址，就在此前的算术、比较或传送中一律清掉。

2、4、8字节访问分别要求地址是2、4、8的整数倍，否则触发MALIGN；1字节访问没有额外对齐要求。一次多寄存器访存还要检查整个寄存器区间是否合法，并按元素宽度依次计算地址。

测试向量中的内存预置值也要结合访问宽度理解。例如，byte访问的预置项 `value=0x1234` 按宽度写入低1字节，因此该地址得到的是0x34，不是把一个64位数写入后再从第一个字节读取。具体预置格式由向量schema规定，不能用它替代指令本身的访存语义。

当前golden用稀疏字节表表示内存，没有预置的字节读作0。**这是为了让单步测试可运行而采用的模型约定，不是硬件保证所有未初始化内存都为0。** 模型不模拟地址映射、访问权限、MMU、ROM或设备，因此不能用它判断UNMAPPED、CFXMEM等机器层异常是否正确。

### 7. 译码成功、执行成功和模型有能力判断，是三件事

译码先回答“这个32位字属于哪条指令”。本文件每条提供的mask/value表示匹配条件：`(word & mask) == value`。字段表随后说明，剩余位如何组成寄存器编号和立即数。

匹配到某个身份，不代表操作数一定合法。例如，一个字可以成功译码为加法，但其目的寄存器组合可能被规范禁止。因此，译码之后仍需做合法性检查。反过来，一个已删除指令的旧机器字如果被当前编码表重新分配，应按当前身份解释；只有当前表未定义的编码才按保留编码处理。

本模型区分以下结果：

| 结果 | 含义 | 测试中应如何理解 |
| --- | --- | --- |
| 执行成功 | 指令属于本模型范围，输入可判定，并完成了规定效果 | 继续比较寄存器、内存和PC断言 |
| ILLI、UNDI、IALIGN、MALIGN、RASOF、RASUF | 本模型覆盖的架构异常 | 核对异常类型，并检查执行前状态未被破坏 |
| `Unsupported` | 编码有定义，但本模型尚未实现，例如原子、fence 或特权指令 | 不能当成该指令在完整机器上必然非法 |
| `SpecificationGap` | 当前规范的文字不足以唯一确定结果 | 需要裁定，不能选一个实现的输出当标准 |
| `ValueError`等输入错误 | 调用参数或测试数据格式无效，例如指令字超过32位 | 先修正测试输入，不能作为ISA异常来验收 |

`sub.uo` 的借位高半已由 `ADR-0049` 裁定为 0/1（`rdHC < rdHD` 时 1，否则 0），不再报 `SpecificationGap`；详见下文“规范口径与验证边界”§1。

### 8. 异常发生时，为什么必须保留执行前状态

“精确异常”在本模型中的要求是：如果本条指令失败，就像它尚未提交任何架构修改一样。目的寄存器不能只写了一半，内存不能只存入前几个元素，call/ret也不能先改栈再报错；PC应仍停在失败的这条指令，而不是正常推进到下一条。

例如，一条ret在读取返回栈时发现无有效返回地址，应报告RASUF。此时既不能修改返回值寄存器，也不能推进MRPTR或改变RACNT。只检查“报了RASUF”而不检查这些状态，仍可能漏掉实现错误。

解释器在状态副本上执行，成功后才返回新状态；发生架构异常则返回执行前状态。这是实现精确异常的一种软件办法，不要求真实硬件也必须复制整份状态。验证器检查的是最终可见行为，而不是硬件内部采用什么实现方法。

当前模型不执行异常处理程序，也不模拟特权异常入口。文档中的“异常后状态不变”，指失败指令自身没有提交副作用，不应被理解为完整系统的异常处理过程永远不会修改任何状态。

### 9. 返回地址栈中究竟保存了什么

call需要记住“函数返回后从哪里继续执行”，ret随后按后入先出的顺序取回这个地址。DADAO为此设置了返回地址栈RAS，其中一部分放在寄存器中，称为RegRAS；寄存器容纳不下时，可使用内存中的MemRAS。

RegRAS使用ra1到ra63，共63个槽位，ra63始终表示栈顶。每个有效条目的低48位是返回地址，高16位是递归计数。计数表示这个条目合并保存了多少次相同返回地址；它与有效槽位数不是同一个概念。

ra0用于管理栈，其字段如下：

| 字段 | 位置 | 含义 |
| --- | --- | --- |
| MRPTR | bits[47:0] | MemRAS中下一个待弹出条目的地址；0表示未启用MemRAS |
| RACNT | bits[53:48] | RegRAS当前有效条目数，范围0–63 |
| SBZ | bits[63:54] | 保留为零，写入这些位无效 |

判断栈内哪些寄存器有效，必须看RACNT。例如RACNT=2时，只有ra63和ra62属于有效栈，ra61即使残留一个非零数也不算条目。无效槽位的内容不能用来推断栈深，也不应成为规范测试的固定期望值。

递归计数的作用可以用一个例子理解：第一次压入返回地址0x1004时，栈顶记录为“计数1、地址0x1004”。如果再次压入的仍是0x1004，而且计数尚未饱和，可以直接把计数改为2，不必再占用一个寄存器槽位。之后两次ret分别将计数减1和真正移除该条目。

下面两个流程是所有call/ret条目共同定义的一部分。表述中的“移动条目”描述的是软件可见的RA寄存器状态；硬件可以采用其他内部结构实现相同效果。

### 共同规则：call压栈

call先根据执行前的rb0计算返回地址：`(旧rb0 + 4) mod 2^48`。要压入的是**调用指令之后的地址**，而不是函数入口地址。函数入口由call自身的跳转操作数另行计算。

随后依次判断以下情况，前面的情况满足后就不再继续选择后面的分支：

1. **寄存器返回栈为空。** 当RACNT=0时，在ra63放入新返回地址，递归计数设为1，RACNT改为1。旧ra63中即使有残留数据，也不能把它当作有效旧栈顶。
2. **可以合并同一个返回地址。** 当RACNT>0、新返回地址与栈顶地址相同，而且栈顶计数小于65535时，只把计数加1，RACNT不变。这一步优先于满栈处理，因此RACNT已经是63也仍可能成功call，不需要访问MemRAS。
3. **需要新条目，而且寄存器栈还有空位。** 如果不能合并，但RACNT<63，就把现有有效条目向较低编号移动一个位置，新条目放ra63，计数为1，RACNT加1。例如原来只有ra63有效，插入后原栈顶移到ra62。即使返回地址相同，只要递归计数已经饱和，也需要走这个分支或下一分支。
4. **需要新条目，但寄存器栈已满。** 此时RACNT=63。若MRPTR=0，表示没有可用的MemRAS，报告RASOF，原状态不变。否则，计算待写地址 `(MRPTR−8) mod 2^48`，检查8字节对齐，将最旧的条目ra1写入该地址，并把MRPTR更新到这里；原ra2至ra63向较低编号移一格，再把新条目放到ra63。这样移出一个、加入一个，RACNT仍为63。

例如，满栈时MRPTR原为0x2000，需要溢出的条目会写到0x1FF8，新的MRPTR也是0x1FF8。这里的“指针减8”来自一个返回栈条目占8字节，不是调用指令的长度。

MemRAS是否有足够的已分配空间由系统管理；本模型不检查OS分配边界。它会检查本次访问是否对齐，并保证失败时RA、内存和PC都保持原状。只有压栈成功，call的跳转结果才一并提交。

### 共同规则：ret弹栈

ret先检查自己的显式操作数是否合法，例如 `ret rd0, 非零立即数` 必须报ILLI。通过后，再从RAS取得返回地址。不能总是假定返回地址直接来自ra63，因为寄存器栈为空时可能需要读取MemRAS。

**当RACNT>0时，栈顶在ra63：**

1. 栈顶递归计数为0，说明有效条目无法提供一次合法返回，报告RASUF，状态不变。
2. 栈顶递归计数大于1，取它的低48位作为返回地址，只把计数减1。这个条目还要供后续ret使用，因此RACNT不变。
3. 栈顶递归计数等于1，取出返回地址并移除这个条目。下层有效条目向较高编号移动一个位置，新的栈顶仍在ra63，RACNT减1。退出有效区的槽位以后不再参与栈语义，不要求它具有某个固定值。

**当RACNT=0时，需要检查MemRAS：**

1. MRPTR=0，表示寄存器栈为空且未启用MemRAS，报告RASUF。即使某个RA槽位还残留非零值，也不能据此返回。
2. MRPTR非0，先检查8字节对齐，再读取该地址的一个8字节条目。此时先不要修改指针，要先检查条目计数。
3. 读出的计数为0，报告RASUF，MRPTR和所有其他状态均不变。
4. 读出的计数为1，使用条目的低48位作为返回地址；该条目本次就消耗完，MRPTR按48位加8，RACNT仍为0。
5. 读出的计数大于1，本次返回消耗其中一次。把“计数减1、地址不变”的剩余记录放到ra63，RACNT设为1，同时MRPTR按48位加8。后续ret就可以从寄存器栈继续返回。

例如，RACNT=0、MRPTR=0x2000，内存条目保存“计数3、地址0x1004”。一次ret之后，下一取指地址是0x1004，ra63保留“计数2、地址0x1004”，RACNT变为1，MRPTR变为0x2008。

弹栈成功后，ret还会按照自身的立即数设置返回值寄存器，并将取得的48位返回地址零扩展写入rb0。若任一检查失败，这些写回都不能发生。返回目标是否4字节对齐，则在下一次取指时检查。

### 10. 伪代码中使用的函数、常量与记号

本节把后文伪代码用到的所有函数和记号先集中声明，避免出现没有解释的名字。伪代码采用 Python 风格语法：`for`、`in`、`if/else`、`range()`、`all()`、`bool()`、`and/or/not` 只表示控制流，不是架构函数；`True/False` 是布尔常量。其余函数都是本文定义的抽象操作，**不是 Python 标准库**，实际实现位置见表。各条中的局部变量（`A`、`B`、`R`、`tmp`、`val`、`flg` 等）由该指令节当场赋值。

#### 10.1 状态、异常与位模式约定

- `state`：调用者传入的完整架构状态。`S = snapshot(state)` 是执行前快照；`S.RD[i]`、`S.RB[i]`、`S.RA[i]`、`S.RF[i]` 是四组寄存器第 i 项，`S.mem` 是稀疏大端内存，`S.pc` 是当前指令地址，`S.RAS` 是返回地址栈。
- `D`：暂定的执行后状态。伪代码先写 `D`，只有末尾 `commit(D)` 才整体生效；任何 `assert` 失败、架构异常或 `SPECIFICATION-GAP` 都不会提交 `D`，返回执行前状态。
- `assert 条件`：条件不成立时，按该条“合法性、异常与边界”报 ILLI（或文中明确的其他异常/`SPECIFICATION-GAP`），并丢弃 `D`。这里的 `assert` 是“检查失败即架构异常”的简写，不是宿主 Python 的断言。
- `EA`：访存有效地址；`EA[i]` 是多寄存器/块访问第 i 个元素的地址。
- `mod 2^64`、`& ((1 << 64) - 1)`：保留低 64 位；`(1 << n) - 1` 是低 n 位全 1 掩码。`X[a:b]` 是左闭右开区间。
- `NV`/`DZ`/`OF`/`UF`/`NX`：FCSR 累积标志，数值 1/2/4/8/16，用按位或合并。`RNE`/`RTZ`/`RDN`/`RUP`：`rf0[33:32]` 的四种舍入方向。
- `FCSR_WRITE_MASK`：写 `rf0` 时允许修改的位 `[33:32]` 与 `[4:0]`，其余位保持。
- `SPECIFICATION-GAP`：规范未给唯一答案，模型拒绝输出；它不是 ISA 异常，也不计作执行通过。
- `positive_qnan` / `positive_snan`：当前格式下符号位为 0 的规范 quiet/signaling NaN 位模式；`ft*` 为 binary32，`fo*` 为 binary64。

#### 10.2 通用与整数函数

| 伪代码写法 | 输入 → 输出 | 含义 | 实际实现 |
| --- | --- | --- | --- |
| `snapshot(state)` | state → S | 深拷贝执行前状态，后续只读 | `dadao_interp_v5.run` 中的复制 |
| `commit(D)` | D → 新状态 | 全部检查通过后一次性提交，返回 D | `run` 末尾替换工作状态 |
| `sext(value, bits)` | 整数、位宽 → 有符号整数 | 取低 `bits` 位按补码解释 | `_sext` |
| `sint(value, width)` | 整数、位宽 → 有符号整数 | 同上；用于完整寄存器/内存值的低 `width` 位 | `_sext` |
| `uint(value, width)` | 整数、位宽 → 无符号整数 | 取低 `width` 位按无符号解释 | 掩码 `& ((1 << width) - 1)` |
| `zext(value, bits)` | 整数、位宽 → 整数 | 取低 `bits` 位并零扩展到 64 位 | 掩码后写回 |
| `trunc0(ratio)` | 有理数 → 整数 | 向零截断（丢弃小数部分） | `div`/`rem` 的整数商实现 |
| `overlap([a,b), [c,d))` | 两个半开区间 → 布尔 | 两个寄存器区间是否有交集；空区间不算 | `_check_blockcopy` 的区间判断 |
| `or_flags(flg)` | 标志列表 → 整数 | 把所有标志按位或合并 | `_fp_flags` 的累积方式 |
| `be_load(mem, addr, size)` | 内存、地址、字节数 → 无符号整数 | 从 `addr` 读 `size` 字节，大端拼成整数；未预置字节按 0（测试模型约定） | `State.load_mem` |
| `be_bytes(value, size)` | 整数、字节数 → 字节列表 | 把低 `size×8` 位按大端拆成 `size` 个字节 | `int.to_bytes(size, "big")` |
| `ras_push(S, addr)` | 快照、返回地址 → (D, ok) | 按共同规则压栈并更新复制的 RAS/内存；`ok=False` 表示 RASOF/MALIGN | `_ras_push` |
| `ras_pop(S)` | 快照 → (return_pc, D.RAS, D.mem, ok) | 按共同规则弹栈；`ok=False` 表示 RASUF/MALIGN | `_ras_pop` |

#### 10.3 浮点编解码与转换函数

| 伪代码写法 | 输入 → 输出 | 含义 | 实际实现 |
| --- | --- | --- | --- |
| `decode_fp(bits, format=...)` | 位模式 → (sign, kind, value, payload) | 解码符号位、类别（finite/zero/inf/nan）、精确有理数值、NaN payload | `fp_ref.decode` |
| `encode_fp(decoded, format=...)` | 解码值 → 位模式 | 把运算结果按格式编码；NaN 使用规范 quiet 位型 | `fp_ref.encode_fraction` 与特殊值路径 |
| `classify_fp(bits)` | 位模式 → 整数 | 返回 10 位分类掩码，伪代码再 `& 0x3ff` | `fp_ref.classify` |
| `convert_fp(bits, src, dst, rounding)` | 位模式、源/目标格式、舍入 → (bits, flags) | 浮点格式转换 | `fp_ref.convert_float` |
| `fp_to_int(bits, signed, width, rounding, saturate=True)` | 位模式、符号、宽度、舍入 → (整数, flags) | 浮点转整数；NaN/Inf/越界饱和并置 NV | `fp_ref.convert_to_int` |
| `int_to_fp(value, signed, width, dst, rounding)` | 整数、符号、宽度、目标格式、舍入 → (bits, flags) | 整数转浮点 | `fp_ref.convert_int` |
| `is_nan(X)` | 解码值 → 布尔 | 是否为 NaN | `fp_ref.decode(...)[1] == "nan"` |
| `has_signaling_nan(A, B)` | 两个解码值 → 布尔 | 任一为 signaling NaN；quiet NaN 返回假 | payload 的 quiet 位判断 |
| `is_negative_zero(X)` | 解码值 → 布尔 | 是否为 `−0` | 符号位与数值判断 |
| `sign(X)` | 解码值 → 0/1 | 符号位 | 解码结果第 0 项 |
| `positive_qnan` / `positive_snan` | 常量 | 符号位 0 的规范 quiet/signaling NaN 位模式 | `Format.canonical_qnan/snan` |

#### 10.4 浮点运算函数

| 伪代码写法 | 输入 → 输出 | 含义 | 实际实现 |
| --- | --- | --- | --- |
| `fp_add(A,B,rounding=...)` | 两个解码值、舍入 → (bits, flags) | 加法 | `fp_ref.arithmetic("add", ...)` |
| `fp_sub(...)` | 同上 | 减法 | `arithmetic("sub", ...)` |
| `fp_mul(...)` | 同上 | 乘法 | `arithmetic("mul", ...)` |
| `fp_div(...)` | 同上 | 除法 | `arithmetic("div", ...)` |
| `fp_remainder(...)` | 同上 | IEEE 754 remainder（平局取偶） | `arithmetic("rem", ...)` |
| `fp_scaleB(...)` | 同上 | scaleB 指数缩放 | `arithmetic("scalb", ...)` |
| `fp_sqrt(X, rounding=...)` | 解码值、舍入 → (bits, flags) | 平方根；`rootn(-0,2)` 报 `SPECIFICATION-GAP` | `fp_ref.sqrt` |
| `fp_minimumNumber(A,B)` / `fp_maximumNumber(A,B)` | 两个解码值 → (bits, flags) | IEEE 754-2019 §9.6 严格版最小/最大值 | `fp_ref.minmax("min"/"max", ...)` |
| `round_to_integral(A, selector, rounding)` | 解码值、one-hot selector、舍入 → (bits, flags) | 六档取整；仅 selector=0x20 读取舍入并可置 NX | `fp_ref.round_to_integral` |
| `fp_fusedMultiplyAdd(A,B,C,rounding)` | 三个解码值、舍入 → (bits, flags) | 精确积加加数后单次舍入 | `fp_ref.fma` |

返回 `(bits, flags)` 或 `(value, flags)` 的函数，`flags` 只含本条产生的 NV/DZ/OF/UF/NX，调用方再累积到 `rf0[4:0]`。`fp_to_int` 的精度损失是否置 NX 仍是开放点（见 §16）；模型对未裁定的输入报 `SPECIFICATION-GAP`，不自行补答案。

共同规则的规范依据：[ISA合约](../../.tao/contracts/contract-isa.md) §1–3、§6、§8、§10–15；[浮点合约](../../.tao/contracts/contract-fp.md)；[SimRISC-00](../../spec/SimRISC-00-指令系统设计.md)。测试输入与内存预置约定见 [向量schema](../../tests/vectors/schema.md)。模型接口和范围限制见 [设计说明](DESIGN.md)。

## 指令目录

本次编码表现场统计：详细条目 **219** 个（scalar=153，fp=66）；范围外身份 **47** 个。下表按规范编码表顺序排列。

| 序号 | 指令身份（点击查看） | 类别 |
| --- | --- | --- |
| 1 | [ld.ub_rrii_rd](#insn-001) | 访存 |
| 2 | [ld.uw_rrii_rd](#insn-002) | 访存 |
| 3 | [ld.ut_rrii_rd](#insn-003) | 访存 |
| 4 | [ld.sb_rrii_rd](#insn-004) | 访存 |
| 5 | [ld.sw_rrii_rd](#insn-005) | 访存 |
| 6 | [ld.st_rrii_rd](#insn-006) | 访存 |
| 7 | [ld.t_rrii_rf](#insn-007) | 浮点/FCSR |
| 8 | [st.t_rrii_rf](#insn-008) | 浮点/FCSR |
| 9 | [st.b_rrii_rd](#insn-009) | 访存 |
| 10 | [st.w_rrii_rd](#insn-010) | 访存 |
| 11 | [st.t_rrii_rd](#insn-011) | 访存 |
| 12 | [ld.o_rrii_rd](#insn-012) | 访存 |
| 13 | [st.o_rrii_rd](#insn-013) | 访存 |
| 14 | [ld.o_rrii_rb](#insn-014) | 访存 |
| 15 | [st.o_rrii_rb](#insn-015) | 访存 |
| 16 | [ld.o_rrii_ra](#insn-016) | 访存 |
| 17 | [st.o_rrii_ra](#insn-017) | 访存 |
| 18 | [ld.o_rrii_rf](#insn-018) | 浮点/FCSR |
| 19 | [st.o_rrii_rf](#insn-019) | 浮点/FCSR |
| 20 | [ldm.ub_rrri_rd](#insn-020) | 访存 |
| 21 | [ldm.uw_rrri_rd](#insn-021) | 访存 |
| 22 | [ldm.ut_rrri_rd](#insn-022) | 访存 |
| 23 | [ldm.sb_rrri_rd](#insn-023) | 访存 |
| 24 | [ldm.sw_rrri_rd](#insn-024) | 访存 |
| 25 | [ldm.st_rrri_rd](#insn-025) | 访存 |
| 26 | [ldm.t_rrri_rf](#insn-026) | 浮点/FCSR |
| 27 | [stm.t_rrri_rf](#insn-027) | 浮点/FCSR |
| 28 | [stm.b_rrri_rd](#insn-028) | 访存 |
| 29 | [stm.w_rrri_rd](#insn-029) | 访存 |
| 30 | [stm.t_rrri_rd](#insn-030) | 访存 |
| 31 | [ldm.o_rrri_rd](#insn-031) | 访存 |
| 32 | [stm.o_rrri_rd](#insn-032) | 访存 |
| 33 | [ldm.o_rrri_rb](#insn-033) | 访存 |
| 34 | [stm.o_rrri_rb](#insn-034) | 访存 |
| 35 | [ldm.o_rrri_ra](#insn-035) | 访存 |
| 36 | [stm.o_rrri_ra](#insn-036) | 访存 |
| 37 | [ldm.o_rrri_rf](#insn-037) | 浮点/FCSR |
| 38 | [stm.o_rrri_rf](#insn-038) | 浮点/FCSR |
| 39 | [or.w_rwii_rd](#insn-039) | 立即数设置 |
| 40 | [andn.w_rwii_rd](#insn-040) | 立即数设置 |
| 41 | [or.w_rwii_rb](#insn-041) | 立即数设置 |
| 42 | [andn.w_rwii_rb](#insn-042) | 立即数设置 |
| 43 | [set.zw_rwii_rd](#insn-043) | 立即数设置 |
| 44 | [set.ow_rwii_rd](#insn-044) | 立即数设置 |
| 45 | [set.zw_rwii_rb](#insn-045) | 立即数设置 |
| 46 | [set.w_rwii_rf](#insn-046) | 浮点/FCSR |
| 47 | [add.uo_rrrr_rd](#insn-047) | 双目的整数运算 |
| 48 | [add.so_rrrr_rd](#insn-048) | 双目的整数运算 |
| 49 | [sub.uo_rrrr_rd](#insn-049) | 双目的整数运算 |
| 50 | [sub.so_rrrr_rd](#insn-050) | 双目的整数运算 |
| 51 | [mul.uo_rrrr_rd](#insn-051) | 双目的整数运算 |
| 52 | [mul.so_rrrr_rd](#insn-052) | 双目的整数运算 |
| 53 | [add.si_riii_rd](#insn-053) | 地址与立即数算术 |
| 54 | [aip.si_riii_rb](#insn-054) | 地址与立即数算术 |
| 55 | [add.si_riii_rb](#insn-055) | 地址与立即数算术 |
| 56 | [cmp.ui_rrii_rd](#insn-056) | 整数比较 |
| 57 | [cmp.si_rrii_rd](#insn-057) | 整数比较 |
| 58 | [ftfma_rrrr_rf](#insn-058) | 浮点/FCSR |
| 59 | [fofma_rrrr_rf](#insn-059) | 浮点/FCSR |
| 60 | [cs.n_rrrr_rd](#insn-060) | 条件赋值 |
| 61 | [cs.n_rrrr_rf](#insn-061) | 浮点/FCSR |
| 62 | [cs.z_rrrr_rd](#insn-062) | 条件赋值 |
| 63 | [cs.z_rrrr_rf](#insn-063) | 浮点/FCSR |
| 64 | [cs.p_rrrr_rd](#insn-064) | 条件赋值 |
| 65 | [cs.p_rrrr_rf](#insn-065) | 浮点/FCSR |
| 66 | [cs.eq_rrrr_rd](#insn-066) | 条件赋值 |
| 67 | [cs.ne_rrrr_rd](#insn-067) | 条件赋值 |
| 68 | [br.n_riii_rd](#insn-068) | 控制流 |
| 69 | [br.nn_riii_rd](#insn-069) | 控制流 |
| 70 | [br.z_riii_rd](#insn-070) | 控制流 |
| 71 | [br.nz_riii_rd](#insn-071) | 控制流 |
| 72 | [br.p_riii_rd](#insn-072) | 控制流 |
| 73 | [br.np_riii_rd](#insn-073) | 控制流 |
| 74 | [br.eq_rrii_rd](#insn-074) | 控制流 |
| 75 | [br.ne_rrii_rd](#insn-075) | 控制流 |
| 76 | [jump_iiii_rb](#insn-076) | 控制流 |
| 77 | [jump_rrii_rb](#insn-077) | 控制流 |
| 78 | [br.z_riii_rb](#insn-078) | 控制流 |
| 79 | [br.nz_riii_rb](#insn-079) | 控制流 |
| 80 | [call_iiii_ra](#insn-080) | 控制流 |
| 81 | [call_rrii_ra](#insn-081) | 控制流 |
| 82 | [ret_riii_ra](#insn-082) | 控制流 |
| 83 | [swym_oiii_imm](#insn-083) | 其他标量指令 |
| 84 | [and.o_orrr_rd](#insn-084) | 逻辑运算 |
| 85 | [or.o_orrr_rd](#insn-085) | 逻辑运算 |
| 86 | [xor.o_orrr_rd](#insn-086) | 逻辑运算 |
| 87 | [xnor.o_orrr_rd](#insn-087) | 逻辑运算 |
| 88 | [shl.o_orrr_rd](#insn-088) | 移位与扩展 |
| 89 | [shr.uo_orrr_rd](#insn-089) | 移位与扩展 |
| 90 | [shr.so_orrr_rd](#insn-090) | 移位与扩展 |
| 91 | [shl.o_orri_rd](#insn-091) | 移位与扩展 |
| 92 | [shr.uo_orri_rd](#insn-092) | 移位与扩展 |
| 93 | [shr.so_orri_rd](#insn-093) | 移位与扩展 |
| 94 | [ext.uo_orrr_rd](#insn-094) | 移位与扩展 |
| 95 | [ext.so_orrr_rd](#insn-095) | 移位与扩展 |
| 96 | [ext.uo_orri_rd](#insn-096) | 移位与扩展 |
| 97 | [ext.so_orri_rd](#insn-097) | 移位与扩展 |
| 98 | [add.o_orrr_bbd](#insn-098) | 地址与立即数算术 |
| 99 | [sub.o_orrr_bbd](#insn-099) | 地址与立即数算术 |
| 100 | [cmp.uo_orrr_dbb](#insn-100) | 地址与立即数算术 |
| 101 | [sub.o_orrr_dbb](#insn-101) | 地址与立即数算术 |
| 102 | [cmp.uo_orrr_rd](#insn-102) | 定宽整数运算 |
| 103 | [cmp.so_orrr_rd](#insn-103) | 定宽整数运算 |
| 104 | [rd2rd_orri_rd](#insn-104) | 寄存器传送 |
| 105 | [rd2ra_orri_ra](#insn-105) | 寄存器传送 |
| 106 | [ra2rd_orri_ra](#insn-106) | 寄存器传送 |
| 107 | [rb2rb_orri_rb](#insn-107) | 寄存器传送 |
| 108 | [rd2rb_orri_rb](#insn-108) | 寄存器传送 |
| 109 | [rb2rd_orri_rb](#insn-109) | 寄存器传送 |
| 110 | [div.uo_orrr_rd](#insn-110) | 定宽整数运算 |
| 111 | [div.so_orrr_rd](#insn-111) | 定宽整数运算 |
| 112 | [rem.uo_orrr_rd](#insn-112) | 定宽整数运算 |
| 113 | [rem.so_orrr_rd](#insn-113) | 定宽整数运算 |
| 114 | [rd2rf_orri_rf](#insn-114) | 浮点/FCSR |
| 115 | [rf2rd_orri_rf](#insn-115) | 浮点/FCSR |
| 116 | [shl.t_orrr_rd](#insn-116) | 移位与扩展 |
| 117 | [shr.ut_orrr_rd](#insn-117) | 移位与扩展 |
| 118 | [shr.st_orrr_rd](#insn-118) | 移位与扩展 |
| 119 | [shl.t_orri_rd](#insn-119) | 移位与扩展 |
| 120 | [shr.ut_orri_rd](#insn-120) | 移位与扩展 |
| 121 | [shr.st_orri_rd](#insn-121) | 移位与扩展 |
| 122 | [add.ut_orrr_rd](#insn-122) | 定宽整数运算 |
| 123 | [add.st_orrr_rd](#insn-123) | 定宽整数运算 |
| 124 | [sub.ut_orrr_rd](#insn-124) | 定宽整数运算 |
| 125 | [sub.st_orrr_rd](#insn-125) | 定宽整数运算 |
| 126 | [cmp.ut_orrr_rd](#insn-126) | 定宽整数运算 |
| 127 | [cmp.st_orrr_rd](#insn-127) | 定宽整数运算 |
| 128 | [mul.ut_orrr_rd](#insn-128) | 定宽整数运算 |
| 129 | [mul.st_orrr_rd](#insn-129) | 定宽整数运算 |
| 130 | [div.ut_orrr_rd](#insn-130) | 定宽整数运算 |
| 131 | [div.st_orrr_rd](#insn-131) | 定宽整数运算 |
| 132 | [rem.ut_orrr_rd](#insn-132) | 定宽整数运算 |
| 133 | [rem.st_orrr_rd](#insn-133) | 定宽整数运算 |
| 134 | [shl.w_orrr_rd](#insn-134) | 移位与扩展 |
| 135 | [shr.uw_orrr_rd](#insn-135) | 移位与扩展 |
| 136 | [shr.sw_orrr_rd](#insn-136) | 移位与扩展 |
| 137 | [shl.w_orri_rd](#insn-137) | 移位与扩展 |
| 138 | [shr.uw_orri_rd](#insn-138) | 移位与扩展 |
| 139 | [shr.sw_orri_rd](#insn-139) | 移位与扩展 |
| 140 | [add.uw_orrr_rd](#insn-140) | 定宽整数运算 |
| 141 | [add.sw_orrr_rd](#insn-141) | 定宽整数运算 |
| 142 | [sub.uw_orrr_rd](#insn-142) | 定宽整数运算 |
| 143 | [sub.sw_orrr_rd](#insn-143) | 定宽整数运算 |
| 144 | [cmp.uw_orrr_rd](#insn-144) | 定宽整数运算 |
| 145 | [cmp.sw_orrr_rd](#insn-145) | 定宽整数运算 |
| 146 | [mul.uw_orrr_rd](#insn-146) | 定宽整数运算 |
| 147 | [mul.sw_orrr_rd](#insn-147) | 定宽整数运算 |
| 148 | [div.uw_orrr_rd](#insn-148) | 定宽整数运算 |
| 149 | [div.sw_orrr_rd](#insn-149) | 定宽整数运算 |
| 150 | [rem.uw_orrr_rd](#insn-150) | 定宽整数运算 |
| 151 | [rem.sw_orrr_rd](#insn-151) | 定宽整数运算 |
| 152 | [shl.b_orrr_rd](#insn-152) | 移位与扩展 |
| 153 | [shr.ub_orrr_rd](#insn-153) | 移位与扩展 |
| 154 | [shr.sb_orrr_rd](#insn-154) | 移位与扩展 |
| 155 | [shl.b_orri_rd](#insn-155) | 移位与扩展 |
| 156 | [shr.ub_orri_rd](#insn-156) | 移位与扩展 |
| 157 | [shr.sb_orri_rd](#insn-157) | 移位与扩展 |
| 158 | [add.ub_orrr_rd](#insn-158) | 定宽整数运算 |
| 159 | [add.sb_orrr_rd](#insn-159) | 定宽整数运算 |
| 160 | [sub.ub_orrr_rd](#insn-160) | 定宽整数运算 |
| 161 | [sub.sb_orrr_rd](#insn-161) | 定宽整数运算 |
| 162 | [cmp.ub_orrr_rd](#insn-162) | 定宽整数运算 |
| 163 | [cmp.sb_orrr_rd](#insn-163) | 定宽整数运算 |
| 164 | [mul.ub_orrr_rd](#insn-164) | 定宽整数运算 |
| 165 | [mul.sb_orrr_rd](#insn-165) | 定宽整数运算 |
| 166 | [div.ub_orrr_rd](#insn-166) | 定宽整数运算 |
| 167 | [div.sb_orrr_rd](#insn-167) | 定宽整数运算 |
| 168 | [rem.ub_orrr_rd](#insn-168) | 定宽整数运算 |
| 169 | [rem.sb_orrr_rd](#insn-169) | 定宽整数运算 |
| 170 | [ftcls_orri_rf](#insn-170) | 浮点/FCSR |
| 171 | [ft2fo_orri_rf](#insn-171) | 浮点/FCSR |
| 172 | [ft2ft_orri_rf](#insn-172) | 浮点/FCSR |
| 173 | [ftroot_orri_rf](#insn-173) | 浮点/FCSR |
| 174 | [focls_orri_rf](#insn-174) | 浮点/FCSR |
| 175 | [fo2ft_orri_rf](#insn-175) | 浮点/FCSR |
| 176 | [fo2fo_orri_rf](#insn-176) | 浮点/FCSR |
| 177 | [foroot_orri_rf](#insn-177) | 浮点/FCSR |
| 178 | [ft2it_orri_rf](#insn-178) | 浮点/FCSR |
| 179 | [ft2io_orri_rf](#insn-179) | 浮点/FCSR |
| 180 | [ft2ut_orri_rf](#insn-180) | 浮点/FCSR |
| 181 | [ft2uo_orri_rf](#insn-181) | 浮点/FCSR |
| 182 | [it2ft_orri_rf](#insn-182) | 浮点/FCSR |
| 183 | [io2ft_orri_rf](#insn-183) | 浮点/FCSR |
| 184 | [ut2ft_orri_rf](#insn-184) | 浮点/FCSR |
| 185 | [uo2ft_orri_rf](#insn-185) | 浮点/FCSR |
| 186 | [fo2it_orri_rf](#insn-186) | 浮点/FCSR |
| 187 | [fo2io_orri_rf](#insn-187) | 浮点/FCSR |
| 188 | [fo2ut_orri_rf](#insn-188) | 浮点/FCSR |
| 189 | [fo2uo_orri_rf](#insn-189) | 浮点/FCSR |
| 190 | [it2fo_orri_rf](#insn-190) | 浮点/FCSR |
| 191 | [io2fo_orri_rf](#insn-191) | 浮点/FCSR |
| 192 | [ut2fo_orri_rf](#insn-192) | 浮点/FCSR |
| 193 | [uo2fo_orri_rf](#insn-193) | 浮点/FCSR |
| 194 | [ftrnd_orri_rf](#insn-194) | 浮点/FCSR |
| 195 | [fornd_orri_rf](#insn-195) | 浮点/FCSR |
| 196 | [ftadd_orrr_rf](#insn-196) | 浮点/FCSR |
| 197 | [ftsub_orrr_rf](#insn-197) | 浮点/FCSR |
| 198 | [ftmul_orrr_rf](#insn-198) | 浮点/FCSR |
| 199 | [ftdiv_orrr_rf](#insn-199) | 浮点/FCSR |
| 200 | [ftrem_orrr_rf](#insn-200) | 浮点/FCSR |
| 201 | [ftsclb_orrr_rf](#insn-201) | 浮点/FCSR |
| 202 | [ftsgnn_orrr_rf](#insn-202) | 浮点/FCSR |
| 203 | [ftsgnj_orrr_rf](#insn-203) | 浮点/FCSR |
| 204 | [foadd_orrr_rf](#insn-204) | 浮点/FCSR |
| 205 | [fosub_orrr_rf](#insn-205) | 浮点/FCSR |
| 206 | [fomul_orrr_rf](#insn-206) | 浮点/FCSR |
| 207 | [fodiv_orrr_rf](#insn-207) | 浮点/FCSR |
| 208 | [forem_orrr_rf](#insn-208) | 浮点/FCSR |
| 209 | [fosclb_orrr_rf](#insn-209) | 浮点/FCSR |
| 210 | [fosgnn_orrr_rf](#insn-210) | 浮点/FCSR |
| 211 | [fosgnj_orrr_rf](#insn-211) | 浮点/FCSR |
| 212 | [ftqcmp_orrr_rf](#insn-212) | 浮点/FCSR |
| 213 | [ftscmp_orrr_rf](#insn-213) | 浮点/FCSR |
| 214 | [foqcmp_orrr_rf](#insn-214) | 浮点/FCSR |
| 215 | [foscmp_orrr_rf](#insn-215) | 浮点/FCSR |
| 216 | [ftmin_orrr_rf](#insn-216) | 浮点/FCSR |
| 217 | [ftmax_orrr_rf](#insn-217) | 浮点/FCSR |
| 218 | [fomin_orrr_rf](#insn-218) | 浮点/FCSR |
| 219 | [fomax_orrr_rf](#insn-219) | 浮点/FCSR |

<a id="insn-001"></a>

## 1. `ld.ub_rrii_rd`

**用途**：单次读取8位数据，写入RD寄存器。

**操作数形式**：`ld.ub rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x10000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 1) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 1 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 1) for i in range(N)
D.RD[ha + i] = zext(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占1字节，地址低处存高字节（大端）。
3. 按地址读取8位，零扩展到64位，写入 `RD[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 byte访问不要求额外对齐。

**算例**：基址0x1000、偏移0，内存该1字节全为FF；目的选寄存器1，结果 `0x00000000000000FF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.ub](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-002"></a>

## 2. `ld.uw_rrii_rd`

**用途**：单次读取16位数据，写入RD寄存器。

**操作数形式**：`ld.uw rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x11000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 2) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 2 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 2) for i in range(N)
D.RD[ha + i] = zext(v[i], 16) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占2字节，地址低处存高字节（大端）。
3. 按地址读取16位，零扩展到64位，写入 `RD[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 有效地址必须是2的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，内存该2字节全为FF；目的选寄存器1，结果 `0x000000000000FFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.uw](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-003"></a>

## 3. `ld.ut_rrii_rd`

**用途**：单次读取32位数据，写入RD寄存器。

**操作数形式**：`ld.ut rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x12000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
D.RD[ha + i] = zext(v[i], 32) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占4字节，地址低处存高字节（大端）。
3. 按地址读取32位，零扩展到64位，写入 `RD[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 有效地址必须是4的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，内存该4字节全为FF；目的选寄存器1，结果 `0x00000000FFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.ut](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-004"></a>

## 4. `ld.sb_rrii_rd`

**用途**：单次读取8位数据，写入RD寄存器。

**操作数形式**：`ld.sb rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x13000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 1) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 1 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 1) for i in range(N)
D.RD[ha + i] = sext(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占1字节，地址低处存高字节（大端）。
3. 按地址读取8位，将其最高位作为符号位，符号扩展到64位，写入 `RD[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 byte访问不要求额外对齐。

**算例**：基址0x1000、偏移0，内存该1字节全为FF；目的选寄存器1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.sb](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-005"></a>

## 5. `ld.sw_rrii_rd`

**用途**：单次读取16位数据，写入RD寄存器。

**操作数形式**：`ld.sw rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x14000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 2) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 2 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 2) for i in range(N)
D.RD[ha + i] = sext(v[i], 16) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占2字节，地址低处存高字节（大端）。
3. 按地址读取16位，将其最高位作为符号位，符号扩展到64位，写入 `RD[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 有效地址必须是2的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，内存该2字节全为FF；目的选寄存器1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.sw](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-006"></a>

## 6. `ld.st_rrii_rd`

**用途**：单次读取32位数据，写入RD寄存器。

**操作数形式**：`ld.st rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x15000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
D.RD[ha + i] = sext(v[i], 32) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占4字节，地址低处存高字节（大端）。
3. 按地址读取32位，将其最高位作为符号位，符号扩展到64位，写入 `RD[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 有效地址必须是4的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，内存该4字节全为FF；目的选寄存器1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.st](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-007"></a>

## 7. `ld.t_rrii_rf`

**用途**：按浮点合约执行 `ld.t`，格式和寄存器字段以编码表为准。

**操作数形式**：`ld.t rfha, rbhb, imms12`（rrii；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x16000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 4 == 4 else v[i] for i in range(N)
D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = 1
3. EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 4) & ((1 << 48) - 1) for i in range(N)
4. assert all(EA[i] % 4 == 0 for i in range(N))
5. v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
6. R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 4 == 4 else v[i] for i in range(N)
7. D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.t](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-008"></a>

## 8. `st.t_rrii_rf`

**用途**：按浮点合约执行 `st.t`，格式和寄存器字段以编码表为准。

**操作数形式**：`st.t rfha, rbhb, imms12`（rrii；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x17000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = S.RF[ha + i] & ((1 << 32) - 1) for i in range(N)
D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 4)[j] for i in range(N) for j in range(4)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = 1
3. EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 4) & ((1 << 48) - 1) for i in range(N)
4. assert all(EA[i] % 4 == 0 for i in range(N))
5. v[i] = S.RF[ha + i] & ((1 << 32) - 1) for i in range(N)
6. D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 4)[j] for i in range(N) for j in range(4)
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.t](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-009"></a>

## 9. `st.b_rrii_rd`

**用途**：单次存储8位数据，读出RD寄存器。

**操作数形式**：`st.b rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是源寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x18000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 1) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 1 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 8) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 1] = be_bytes(v[i], 1) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占1字节，地址低处存高字节（大端）。
3. 从 `RD[ha]` 读取原值，仅将低8位写入对应的1个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 byte访问不要求额外对齐。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `88`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.b](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-010"></a>

## 10. `st.w_rrii_rd`

**用途**：单次存储16位数据，读出RD寄存器。

**操作数形式**：`st.w rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是源寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x19000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 2) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 2 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 16) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 2] = be_bytes(v[i], 2) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占2字节，地址低处存高字节（大端）。
3. 从 `RD[ha]` 读取原值，仅将低16位写入对应的2个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 有效地址必须是2的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `77 88`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.w](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-011"></a>

## 11. `st.t_rrii_rd`

**用途**：单次存储32位数据，读出RD寄存器。

**操作数形式**：`st.t rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是源寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x1A000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 32) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 4] = be_bytes(v[i], 4) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占4字节，地址低处存高字节（大端）。
3. 从 `RD[ha]` 读取原值，仅将低32位写入对应的4个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 有效地址必须是4的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `55 66 77 88`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.t](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-012"></a>

## 12. `ld.o_rrii_rd`

**用途**：单次读取64位数据，写入RD寄存器。

**操作数形式**：`ld.o rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x20000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
D.RD[ha + i] = v[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 按地址读取64位，保留完整64位位模式，写入 `RD[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，内存该8字节全为FF；目的选寄存器1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-013"></a>

## 13. `st.o_rrii_rd`

**用途**：单次存储64位数据，读出RD寄存器。

**操作数形式**：`st.o rdha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是源寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x21000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 8] = be_bytes(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 从 `RD[ha]` 读取原值，仅将低64位写入对应的8个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `11 22 33 44 55 66 77 88`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-014"></a>

## 14. `ld.o_rrii_rb`

**用途**：单次读取64位数据，写入RB寄存器。

**操作数形式**：`ld.o rbha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x22000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
D.RB[ha + i] = v[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 按地址读取64位，保留完整64位位模式，写入 `RB[ha]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rbha` 不可为 `rb0`，否则 ILLI。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，内存该8字节全为FF；目的选寄存器1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-015"></a>

## 15. `st.o_rrii_rb`

**用途**：单次存储64位数据，读出RB寄存器。

**操作数形式**：`st.o rbha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是源寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x23000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RB[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 8] = be_bytes(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 从 `RB[ha]` 读取原值，仅将低64位写入对应的8个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rb0` 合法，读出本条执行前的完整rb0值。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `11 22 33 44 55 66 77 88`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-016"></a>

## 16. `ld.o_rrii_ra`

**用途**：单次读取64位数据，写入RA寄存器。

**操作数形式**：`ld.o raha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`raha` 是目的寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x24000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `raha` | `[23:18]` | ra字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
D.RA[ha + i] = v[i] for i in range(N)
D.RA[0] = (D.RA[0] & 0x003fffffffffffff) | (S.RA[0] & 0xffc0000000000000)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 按地址读取64位，保留完整64位位模式，写入 `RA[ha]`，覆盖旧值。
4. 若目的包含 ra0，只写 RACNT[53:48] 和 MRPTR[47:0]，SBZ[63:54] 不写入；其他RA条目保留完整64位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：ra0 作为源或目的均合法；它的写屏蔽规则仍有效。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，内存该8字节全为FF；目的选寄存器1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-017"></a>

## 17. `st.o_rrii_ra`

**用途**：单次存储64位数据，读出RA寄存器。

**操作数形式**：`st.o raha, rbhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`raha` 是源寄存器，`rbhb` 是地址基址；`imms12` 是12位有符号字节偏移（−2048至2047），不乘访问宽度。

**编码**：mask=`0xFF000000`，value=`0x25000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `raha` | `[23:18]` | ra字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RA[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 8] = be_bytes(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA = (旧RB[hb] + sign_extend(imms12)) mod 2^48`。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 从 `RA[ha]` 读取原值，仅将低64位写入对应的8个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：ra0 作为源或目的均合法；它的写屏蔽规则仍有效。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `11 22 33 44 55 66 77 88`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-018"></a>

## 18. `ld.o_rrii_rf`

**用途**：按浮点合约执行 `ld.o`，格式和寄存器字段以编码表为准。

**操作数形式**：`ld.o rfha, rbhb, imms12`（rrii；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x26000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 8 == 4 else v[i] for i in range(N)
D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = 1
3. EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
4. assert all(EA[i] % 8 == 0 for i in range(N))
5. v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
6. R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 8 == 4 else v[i] for i in range(N)
7. D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ld.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-019"></a>

## 19. `st.o_rrii_rf`

**用途**：按浮点合约执行 `st.o`，格式和寄存器字段以编码表为准。

**操作数形式**：`st.o rfha, rbhb, imms12`（rrii；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x27000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = 1
EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RF[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 8)[j] for i in range(N) for j in range(8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = 1
3. EA[i] = (S.RB[hb] + sext(imms12, 12) + i * 8) & ((1 << 48) - 1) for i in range(N)
4. assert all(EA[i] % 8 == 0 for i in range(N))
5. v[i] = S.RF[ha + i] & ((1 << 64) - 1) for i in range(N)
6. D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 8)[j] for i in range(N) for j in range(8)
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: st.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-020"></a>

## 20. `ldm.ub_rrri_rd`

**用途**：连续读取8位数据，写入RD寄存器。

**操作数形式**：`ldm.ub rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x28000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 1) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 1 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 1) for i in range(N)
D.RD[ha + i] = zext(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×1) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占1字节，地址低处存高字节（大端）。
3. 按地址读取8位，零扩展到64位，写入 `RD[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 byte访问不要求额外对齐。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0x00000000000000FF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.ub](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-021"></a>

## 21. `ldm.uw_rrri_rd`

**用途**：连续读取16位数据，写入RD寄存器。

**操作数形式**：`ldm.uw rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x29000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 2) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 2 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 2) for i in range(N)
D.RD[ha + i] = zext(v[i], 16) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×2) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占2字节，地址低处存高字节（大端）。
3. 按地址读取16位，零扩展到64位，写入 `RD[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是2的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0x000000000000FFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.uw](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-022"></a>

## 22. `ldm.ut_rrri_rd`

**用途**：连续读取32位数据，写入RD寄存器。

**操作数形式**：`ldm.ut rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x2A000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
D.RD[ha + i] = zext(v[i], 32) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×4) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占4字节，地址低处存高字节（大端）。
3. 按地址读取32位，零扩展到64位，写入 `RD[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是4的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0x00000000FFFFFFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.ut](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-023"></a>

## 23. `ldm.sb_rrri_rd`

**用途**：连续读取8位数据，写入RD寄存器。

**操作数形式**：`ldm.sb rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x2B000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 1) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 1 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 1) for i in range(N)
D.RD[ha + i] = sext(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×1) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占1字节，地址低处存高字节（大端）。
3. 按地址读取8位，将其最高位作为符号位，符号扩展到64位，写入 `RD[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 byte访问不要求额外对齐。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0xFFFFFFFFFFFFFFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.sb](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-024"></a>

## 24. `ldm.sw_rrri_rd`

**用途**：连续读取16位数据，写入RD寄存器。

**操作数形式**：`ldm.sw rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x2C000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 2) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 2 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 2) for i in range(N)
D.RD[ha + i] = sext(v[i], 16) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×2) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占2字节，地址低处存高字节（大端）。
3. 按地址读取16位，将其最高位作为符号位，符号扩展到64位，写入 `RD[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是2的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0xFFFFFFFFFFFFFFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.sw](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-025"></a>

## 25. `ldm.st_rrri_rd`

**用途**：连续读取32位数据，写入RD寄存器。

**操作数形式**：`ldm.st rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x2D000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
D.RD[ha + i] = sext(v[i], 32) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×4) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占4字节，地址低处存高字节（大端）。
3. 按地址读取32位，将其最高位作为符号位，符号扩展到64位，写入 `RD[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是4的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0xFFFFFFFFFFFFFFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.st](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-026"></a>

## 26. `ldm.t_rrri_rf`

**用途**：按浮点合约执行 `ldm.t`，格式和寄存器字段以编码表为准。

**操作数形式**：`ldm.t rfha, rbhb, rdhc, immu6`（rrri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x2E000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 4 == 4 else v[i] for i in range(N)
D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and ha + N <= 64
4. EA[i] = (S.RB[hb] + S.RD[hc] + i * 4) & ((1 << 48) - 1) for i in range(N)
5. assert all(EA[i] % 4 == 0 for i in range(N))
6. v[i] = be_load(S.mem, EA[i], 4) for i in range(N)
7. R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 4 == 4 else v[i] for i in range(N)
8. D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.t](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-027"></a>

## 27. `stm.t_rrri_rf`

**用途**：按浮点合约执行 `stm.t`，格式和寄存器字段以编码表为准。

**操作数形式**：`stm.t rfha, rbhb, rdhc, immu6`（rrri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x2F000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = S.RF[ha + i] & ((1 << 32) - 1) for i in range(N)
D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 4)[j] for i in range(N) for j in range(4)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and ha + N <= 64
4. EA[i] = (S.RB[hb] + S.RD[hc] + i * 4) & ((1 << 48) - 1) for i in range(N)
5. assert all(EA[i] % 4 == 0 for i in range(N))
6. v[i] = S.RF[ha + i] & ((1 << 32) - 1) for i in range(N)
7. D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 4)[j] for i in range(N) for j in range(4)
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.t](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-028"></a>

## 28. `stm.b_rrri_rd`

**用途**：连续存储8位数据，读出RD寄存器。

**操作数形式**：`stm.b rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个源寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x30000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 1) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 1 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 8) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 1] = be_bytes(v[i], 1) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×1) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占1字节，地址低处存高字节（大端）。
3. 从 `RD[ha+i]` 读取原值，仅将低8位写入对应的1个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 byte访问不要求额外对齐。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `88`。个数2时，寄存器2=1还会在 `0x1001` 写入1字节的值1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.b](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-029"></a>

## 29. `stm.w_rrri_rd`

**用途**：连续存储16位数据，读出RD寄存器。

**操作数形式**：`stm.w rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个源寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x31000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 2) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 2 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 16) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 2] = be_bytes(v[i], 2) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×2) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占2字节，地址低处存高字节（大端）。
3. 从 `RD[ha+i]` 读取原值，仅将低16位写入对应的2个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是2的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `77 88`。个数2时，寄存器2=1还会在 `0x1002` 写入2字节的值1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.w](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-030"></a>

## 30. `stm.t_rrri_rd`

**用途**：连续存储32位数据，读出RD寄存器。

**操作数形式**：`stm.t rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个源寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x32000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 4) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 4 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 32) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 4] = be_bytes(v[i], 4) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×4) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占4字节，地址低处存高字节（大端）。
3. 从 `RD[ha+i]` 读取原值，仅将低32位写入对应的4个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是4的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `55 66 77 88`。个数2时，寄存器2=1还会在 `0x1004` 写入4字节的值1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.t](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-031"></a>

## 31. `ldm.o_rrri_rd`

**用途**：连续读取64位数据，写入RD寄存器。

**操作数形式**：`ldm.o rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x38000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
D.RD[ha + i] = v[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×8) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 按地址读取64位，保留完整64位位模式，写入 `RD[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rdha` 不可为 `rd0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0xFFFFFFFFFFFFFFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-032"></a>

## 32. `stm.o_rrri_rd`

**用途**：连续存储64位数据，读出RD寄存器。

**操作数形式**：`stm.o rdha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是第一个源寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x39000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RD[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 8] = be_bytes(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×8) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 从 `RD[ha+i]` 读取原值，仅将低64位写入对应的8个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rd0` 合法，读出0。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `11 22 33 44 55 66 77 88`。个数2时，寄存器2=1还会在 `0x1008` 写入8字节的值1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-033"></a>

## 33. `ldm.o_rrri_rb`

**用途**：连续读取64位数据，写入RB寄存器。

**操作数形式**：`ldm.o rbha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x3A000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
D.RB[ha + i] = v[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×8) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 按地址读取64位，保留完整64位位模式，写入 `RB[ha+i]`，覆盖旧值。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的起点 `rbha` 不可为 `rb0`，否则 ILLI。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0xFFFFFFFFFFFFFFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-034"></a>

## 34. `stm.o_rrri_rb`

**用途**：连续存储64位数据，读出RB寄存器。

**操作数形式**：`stm.o rbha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是第一个源寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x3B000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RB[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 8] = be_bytes(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×8) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 从 `RB[ha+i]` 读取原值，仅将低64位写入对应的8个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：源 `rb0` 合法，读出本条执行前的完整rb0值。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `11 22 33 44 55 66 77 88`。个数2时，寄存器2=1还会在 `0x1008` 写入8字节的值1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-035"></a>

## 35. `ldm.o_rrri_ra`

**用途**：连续读取64位数据，写入RA寄存器。

**操作数形式**：`ldm.o raha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`raha` 是第一个目的寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x3C000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `raha` | `[23:18]` | ra字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
D.RA[ha + i] = v[i] for i in range(N)
D.RA[0] = (D.RA[0] & 0x003fffffffffffff) | (S.RA[0] & 0xffc0000000000000)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×8) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 按地址读取64位，保留完整64位位模式，写入 `RA[ha+i]`，覆盖旧值。
4. 若目的包含 ra0，只写 RACNT[53:48] 和 MRPTR[47:0]，SBZ[63:54] 不写入；其他RA条目保留完整64位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：ra0 作为源或目的均合法；它的写屏蔽规则仍有效。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，个数2，两元素分别为全1和1；目的起点选寄存器1，则寄存器1=0xFFFFFFFFFFFFFFFF、寄存器2=1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-036"></a>

## 36. `stm.o_rrri_ra`

**用途**：连续存储64位数据，读出RA寄存器。

**操作数形式**：`stm.o raha, rbhb, rdhc, immu6`（rrri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`raha` 是第一个源寄存器，`rbhb` 是地址基址；`rdhc` 是字节偏移，`immu6` 是寄存器个数。

**编码**：mask=`0xFF000000`，value=`0x3D000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `raha` | `[23:18]` | ra字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RA[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[EA[i]:EA[i] + 8] = be_bytes(v[i], 8) for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算地址：`EA[i] = (旧RB[hb] + 旧RD[hc] + i×8) mod 2^48，i=0…immu6−1`。基址与索引在任何写回前保存一次，目的覆盖基址/索引也不改变后续地址。
2. 每个元素占8字节，地址低处存高字节（大端）。
3. 从 `RA[ha+i]` 读取原值，仅将低64位写入对应的8个内存字节，其余内存不改。源寄存器不改。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：ra0 作为源或目的均合法；它的写屏蔽规则仍有效。 `immu6=0` 或 `ha+immu6>64` 为 ILLI；不得环绕到0号寄存器。 有效地址必须是8的整数倍，否则 MALIGN。

**算例**：基址0x1000、偏移0，源寄存器1=`0x1122334455667788`；内存从0x1000写入字节 `11 22 33 44 55 66 77 88`。个数2时，寄存器2=1还会在 `0x1008` 写入8字节的值1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md) §3.1–3.3、§1.3.4。

<a id="insn-037"></a>

## 37. `ldm.o_rrri_rf`

**用途**：按浮点合约执行 `ldm.o`，格式和寄存器字段以编码表为准。

**操作数形式**：`ldm.o rfha, rbhb, rdhc, immu6`（rrri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x3E000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 8 == 4 else v[i] for i in range(N)
D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and ha + N <= 64
4. EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
5. assert all(EA[i] % 8 == 0 for i in range(N))
6. v[i] = be_load(S.mem, EA[i], 8) for i in range(N)
7. R[i] = ((S.RF[ha + i] & 0xffffffff00000000) | v[i]) if 8 == 4 else v[i] for i in range(N)
8. D.RF[ha + i] = ((S.RF[ha + i] & ~FCSR_WRITE_MASK) | (R[i] & FCSR_WRITE_MASK)) if ha + i == 0 else R[i] for i in range(N)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: ldm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-038"></a>

## 38. `stm.o_rrri_rf`

**用途**：按浮点合约执行 `stm.o`，格式和寄存器字段以编码表为准。

**操作数形式**：`stm.o rfha, rbhb, rdhc, immu6`（rrri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x3F000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and ha + N <= 64
EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
assert all(EA[i] % 8 == 0 for i in range(N))
v[i] = S.RF[ha + i] & ((1 << 64) - 1) for i in range(N)
D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 8)[j] for i in range(N) for j in range(8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and ha + N <= 64
4. EA[i] = (S.RB[hb] + S.RD[hc] + i * 8) & ((1 << 48) - 1) for i in range(N)
5. assert all(EA[i] % 8 == 0 for i in range(N))
6. v[i] = S.RF[ha + i] & ((1 << 64) - 1) for i in range(N)
7. D.mem[(EA[i] + j) & ((1 << 48) - 1)] = be_bytes(v[i], 8)[j] for i in range(N) for j in range(8)
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-01: stm.o](../../spec/SimRISC-01-取数存数.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §11 (rf_mem)。

<a id="insn-039"></a>

## 39. `or.w_rwii_rd`

**用途**：用16位立即数修改RD寄存器。

**操作数形式**：`or.w rdha, wpN, immu16`（rwii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的兼源（读改写），`wpN` 选择16位段，`immu16` 范围0–65535。

**编码**：mask=`0xFF000000`，value=`0x48000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
old = S.RD[ha] & ((1 << 64) - 1)
imm = immu16 & 0xffff
D.RD[ha] = (old | (imm << shift))
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。
2. 将目标16位与立即数逐位或，其余48位保留。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rd0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。

**算例**：旧值 `0x00000000000F0001`、wp1、immu16=0x00F0，结果 `0x0000000000FF0001`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: or.w](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md) §5、§2.4。

<a id="insn-040"></a>

## 40. `andn.w_rwii_rd`

**用途**：用16位立即数修改RD寄存器。

**操作数形式**：`andn.w rdha, wpN, immu16`（rwii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的兼源（读改写），`wpN` 选择16位段，`immu16` 范围0–65535。

**编码**：mask=`0xFF000000`，value=`0x49000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
old = S.RD[ha] & ((1 << 64) - 1)
imm = immu16 & 0xffff
D.RD[ha] = (old & ~(imm << shift))
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。
2. 将目标16位与立即数的16位按位取反值逐位与，其余48位保留。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rd0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。

**算例**：旧值全1、wp1、immu16=0x00F0，结果 `0xFFFFFFFFFF0FFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: andn.w](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md) §5、§2.4。

<a id="insn-041"></a>

## 41. `or.w_rwii_rb`

**用途**：用16位立即数修改RB寄存器。

**操作数形式**：`or.w rbha, wpN, immu16`（rwii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是目的兼源（读改写），`wpN` 选择16位段，`immu16` 范围0–65535。

**编码**：mask=`0xFF000000`，value=`0x4A000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
old = S.RB[ha] & ((1 << 64) - 1)
imm = immu16 & 0xffff
D.RB[ha] = (old | (imm << shift))
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。
2. 将目标16位与立即数逐位或，其余48位保留。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rb0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。

**算例**：旧值 `0x00000000000F0001`、wp1、immu16=0x00F0，结果 `0x0000000000FF0001`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: or.w](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md) §5、§2.4。

<a id="insn-042"></a>

## 42. `andn.w_rwii_rb`

**用途**：用16位立即数修改RB寄存器。

**操作数形式**：`andn.w rbha, wpN, immu16`（rwii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是目的兼源（读改写），`wpN` 选择16位段，`immu16` 范围0–65535。

**编码**：mask=`0xFF000000`，value=`0x4B000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
old = S.RB[ha] & ((1 << 64) - 1)
imm = immu16 & 0xffff
D.RB[ha] = (old & ~(imm << shift))
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。
2. 将目标16位与立即数的16位按位取反值逐位与，其余48位保留。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rb0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。

**算例**：旧值全1、wp1、immu16=0x00F0，结果 `0xFFFFFFFFFF0FFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: andn.w](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md) §5、§2.4。

<a id="insn-043"></a>

## 43. `set.zw_rwii_rd`

**用途**：用16位立即数修改RD寄存器。

**操作数形式**：`set.zw rdha, wpN, immu16`（rwii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的，`wpN` 选择16位段，`immu16` 范围0–65535。

**编码**：mask=`0xFF000000`，value=`0x4C000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
old = S.RD[ha] & ((1 << 64) - 1)
imm = immu16 & 0xffff
D.RD[ha] = (imm << shift)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。
2. 把目标16位置为immu16，其余48位全部清零。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rd0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。

**算例**：旧值全1、wp1、immu16=0x1234，结果 `0x0000000012340000`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: set.zw](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md) §5、§2.4。

<a id="insn-044"></a>

## 44. `set.ow_rwii_rd`

**用途**：用16位立即数修改RD寄存器。

**操作数形式**：`set.ow rdha, wpN, immu16`（rwii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 是目的，`wpN` 选择16位段，`immu16` 范围0–65535。

**编码**：mask=`0xFF000000`，value=`0x4D000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
old = S.RD[ha] & ((1 << 64) - 1)
imm = immu16 & 0xffff
D.RD[ha] = ((~mask) & ((1 << 64) - 1)) | (imm << shift)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。
2. 把目标16位置为immu16，其余48位全部置一。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rd0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。

**算例**：旧值0、wp1、immu16=0x1234，结果 `0xFFFFFFFF1234FFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: set.ow](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md) §5、§2.4。

<a id="insn-045"></a>

## 45. `set.zw_rwii_rb`

**用途**：用16位立即数修改RB寄存器。

**操作数形式**：`set.zw rbha, wpN, immu16`（rwii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是目的，`wpN` 选择16位段，`immu16` 范围0–65535。

**编码**：mask=`0xFF000000`，value=`0x4E000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
old = S.RB[ha] & ((1 << 64) - 1)
imm = immu16 & 0xffff
D.RB[ha] = (imm << shift)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. wp0、wp1、wp2、wp3分别选 bits[15:0]、[31:16]、[47:32]、[63:48]。
2. 把目标16位置为immu16，其余48位全部清零。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rb0` 为 ILLI。立即数/段号超出编码范围属于输入/汇编错误，不应静默截断。

**算例**：旧值全1、wp1、immu16=0x1234，结果 `0x0000000012340000`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: set.zw](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md) §5、§2.4。

<a id="insn-046"></a>

## 46. `set.w_rwii_rf`

**用途**：按浮点合约执行 `set.w`，格式和寄存器字段以编码表为准。

**操作数形式**：`set.w rfha, wpN, immu16`（rwii；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x4F000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `wpN` | `[17:16]` | 16位段编号0…3 |
| `immu16` | `[15:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
shift = 16 * wpN
mask = 0xffff << shift
R = (S.RF[ha] & ~mask) | (immu16 << shift)
FCSR_WRITE_MASK = (0x3 << 32) | 0x1f
D.RF[ha] = (S.RF[ha] & ~(mask & FCSR_WRITE_MASK)) | (R & mask & FCSR_WRITE_MASK) if ha == 0 else R
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. shift = 16 * wpN
3. mask = 0xffff << shift
4. R = (S.RF[ha] & ~mask) | (immu16 << shift)
5. FCSR_WRITE_MASK = (0x3 << 32) | 0x1f
6. D.RF[ha] = (S.RF[ha] & ~(mask & FCSR_WRITE_MASK)) | (R & mask & FCSR_WRITE_MASK) if ha == 0 else R
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-03: set.w](../../spec/SimRISC-03-16位立即数操作.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §13 (set_w_rf)。

<a id="insn-047"></a>

## 47. `add.uo_rrrr_rd`

**用途**：64位无符号加法，产生高、低两个结果。

**操作数形式**：`add.uo {rdha, rdhb}, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 为高结果目的，`rdhb` 为低结果目的，`rdhc/rdhd` 为源。

**编码**：mask=`0xFF000000`，value=`0x50000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc], 64)
B = uint(S.RD[hd], 64)
R = A + B
U = R & ((1 << 128) - 1)
D.RD[ha] = (U >> 64) & ((1 << 64) - 1)
D.RD[hb] = U & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 一次读取旧RD[hc]和旧RD[hd]，按64位无符号整数解释，计算数学结果 `R=A+B`。
2. 将R取模2^128，高64位写RD[ha]、低64位写RD[hb]；两个源先读取，目的覆盖源不会改变本次计算。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。普通进位/溢出不触发异常。

**算例**：A=0xFFFFFFFFFFFFFFFF、B=1，高=1、低=0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: add.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.1、§6.1.4。

<a id="insn-048"></a>

## 48. `add.so_rrrr_rd`

**用途**：64位有符号加法，产生高、低两个结果。

**操作数形式**：`add.so {rdha, rdhb}, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 为高结果目的，`rdhb` 为低结果目的，`rdhc/rdhd` 为源。

**编码**：mask=`0xFF000000`，value=`0x51000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc], 64)
B = sint(S.RD[hd], 64)
R = A + B
U = R & ((1 << 128) - 1)
D.RD[ha] = (U >> 64) & ((1 << 64) - 1)
D.RD[hb] = U & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 一次读取旧RD[hc]和旧RD[hd]，按64位有符号补码解释，计算数学结果 `R=A+B`。
2. 将R取模2^128，高64位写RD[ha]、低64位写RD[hb]；两个源先读取，目的覆盖源不会改变本次计算。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。普通进位/溢出不触发异常。

**算例**：A=−1、B=1，高=0、低=0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: add.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.1、§6.1.4。

<a id="insn-049"></a>

## 49. `sub.uo_rrrr_rd`

**用途**：64位无符号减法：rdHB 为差，rdHA 为借位。

**操作数形式**：`sub.uo {rdha, rdhb}, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 为借位目的，`rdhb` 为低64位差目的，`rdhc/rdhd` 为源。

**编码**：mask=`0xFF000000`，value=`0x52000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc], 64)
B = uint(S.RD[hd], 64)
D.RD[hb] = (A - B) & ((1 << 64) - 1)
D.RD[ha] = 1 if A < B else 0
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 一次读取旧RD[hc]和旧RD[hd]，按64位无符号整数解释，计算数学结果 `R=A−B`。
2. 无借位时 rdHA=0、rdHB=(A−B) mod 2^64；有借位（A<B）时 rdHA=1、rdHB=(A−B) mod 2^64（ADR-0049）。低 64 位始终是差，不写 128 位结果的全 1 高半。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。借位按 ADR-0049 写 0/1，不触发异常。

**算例**：A=0、B=1，借位=1、低=0xFFFFFFFFFFFFFFFF；A=9、B=4，借位=0、低=5。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: sub.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.1。

<a id="insn-050"></a>

## 50. `sub.so_rrrr_rd`

**用途**：64位有符号减法，产生高、低两个结果。

**操作数形式**：`sub.so {rdha, rdhb}, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 为高结果目的，`rdhb` 为低结果目的，`rdhc/rdhd` 为源。

**编码**：mask=`0xFF000000`，value=`0x53000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc], 64)
B = sint(S.RD[hd], 64)
R = A - B
U = R & ((1 << 128) - 1)
D.RD[ha] = (U >> 64) & ((1 << 64) - 1)
D.RD[hb] = U & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 一次读取旧RD[hc]和旧RD[hd]，按64位有符号补码解释，计算数学结果 `R=A−B`。
2. 将R取模2^128，高64位写RD[ha]、低64位写RD[hb]；两个源先读取，目的覆盖源不会改变本次计算。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。普通进位/溢出不触发异常。

**算例**：A=0、B=1，高和低均为0xFFFFFFFFFFFFFFFF。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: sub.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.1、§6.1.4。

<a id="insn-051"></a>

## 51. `mul.uo_rrrr_rd`

**用途**：64位无符号乘法，产生高、低两个结果。

**操作数形式**：`mul.uo {rdha, rdhb}, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 为高结果目的，`rdhb` 为低结果目的，`rdhc/rdhd` 为源。

**编码**：mask=`0xFF000000`，value=`0x54000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc], 64)
B = uint(S.RD[hd], 64)
R = A * B
U = R & ((1 << 128) - 1)
D.RD[ha] = (U >> 64) & ((1 << 64) - 1)
D.RD[hb] = U & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 一次读取旧RD[hc]和旧RD[hd]，按64位无符号整数解释，计算数学结果 `R=A×B`。
2. 将R取模2^128，高64位写RD[ha]、低64位写RD[hb]；两个源先读取，目的覆盖源不会改变本次计算。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。普通进位/溢出不触发异常。

**算例**：A=0xFFFFFFFFFFFFFFFF、B=2，高=1、低=0xFFFFFFFFFFFFFFFE。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: mul.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.1、§6.1.4。

<a id="insn-052"></a>

## 52. `mul.so_rrrr_rd`

**用途**：64位有符号乘法，产生高、低两个结果。

**操作数形式**：`mul.so {rdha, rdhb}, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 为高结果目的，`rdhb` 为低结果目的，`rdhc/rdhd` 为源。

**编码**：mask=`0xFF000000`，value=`0x55000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc], 64)
B = sint(S.RD[hd], 64)
R = A * B
U = R & ((1 << 128) - 1)
D.RD[ha] = (U >> 64) & ((1 << 64) - 1)
D.RD[hb] = U & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 一次读取旧RD[hc]和旧RD[hd]，按64位有符号补码解释，计算数学结果 `R=A×B`。
2. 将R取模2^128，高64位写RD[ha]、低64位写RD[hb]；两个源先读取，目的覆盖源不会改变本次计算。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：两个目的同时为rd0或为同一个非零寄存器，触发ILLI。允许一个目的为rd0（丢弃该半）；源可为rd0。普通进位/溢出不触发异常。

**算例**：A=−2、B=3，高=0xFFFFFFFFFFFFFFFF、低=0xFFFFFFFFFFFFFFFA。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: mul.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.1、§6.1.4。

<a id="insn-053"></a>

## 53. `add.si_riii_rd`

**用途**：将有符号立即数加到原寄存器上。

**操作数形式**：`add.si rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdha` 同时为源和目的，imms18范围−131072至131071。

**编码**：mask=`0xFF000000`，value=`0x59000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[ha] = (S.RD[ha] + sext(imms18, 18)) & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 读取旧RD[ha]，将imms18符号扩展到64位；`结果=(旧值+立即数) mod 2^64`，写满64位。
2. 溢出回绕，不保留旧高位，也不设置额外整数标志寄存器。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rd0` 为ILLI。

**算例**：旧值0、立即数−1，结果0xFFFFFFFFFFFFFFFF。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: add.si](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.3、§7.2。

<a id="insn-054"></a>

## 54. `aip.si_riii_rb`

**用途**：将当前指令地址加上4KiB单位的有符号偏移写入RB。

**操作数形式**：`aip.si rbha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 是目的；`imms18` 是编码层有符号4KiB块偏移。

**编码**：mask=`0xFF000000`，value=`0x5A000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RB[ha] = (S.RB[0] + (sext(imms18, 18) << 12)) & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 读取执行前的完整 `rb0`（IP）。
2. 计算 `RB[ha] = (旧rb0 + (imms18 << 12)) mod 2^64`。
3. 只有后续访存使用该结果的低48位；本条写回保留完整64位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的为rb0时ILLI；偏移须由编码提供，源rb0取本条当前地址。

**算例**：旧rb0=0x1000、imms18=1，则rb1=0x2000。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-05: aip.si](../../spec/SimRISC-05-64位地址运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) SimRISC-05 §3.4。

<a id="insn-055"></a>

## 55. `add.si_riii_rb`

**用途**：将有符号立即数加到原寄存器上。

**操作数形式**：`add.si rbha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbha` 同时为源和目的，imms18范围−131072至131071。

**编码**：mask=`0xFF000000`，value=`0x5B000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RB[ha] = (S.RB[ha] + sext(imms18, 18)) & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 读取旧RB[ha]，将imms18符号扩展到64位；`结果=(旧值+立即数) mod 2^64`，写满64位。
2. 溢出回绕，不保留旧高位，也不设置额外整数标志寄存器。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 `rb0` 为ILLI。

**算例**：旧值0、立即数−1，结果0xFFFFFFFFFFFFFFFF。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-05: add.si](../../spec/SimRISC-05-64位地址运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1.3、§7.2。

<a id="insn-056"></a>

## 56. `cmp.ui_rrii_rd`

**用途**：将寄存器与立即数比较，返回−1/0/+1。

**操作数形式**：`cmp.ui rdha, rdhb, immu12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：rdha为目的，rdhb为源，immu12为12位无符号立即数（0…4095）。

**编码**：mask=`0xFF000000`，value=`0x5C000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `immu12` | `[11:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hb], 64)
B = immu12
R = -1 if A < B else (0 if A == B else 1)
D.RD[ha] = R & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 将RD[hb]按64位无符号整数解释，与立即数数值比较。
2. 小于写0xFFFFFFFFFFFFFFFF，相等写0，大于写1；完整覆盖RD[ha]。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：RD[hb]=5、立即数7，RD[ha]=0xFFFFFFFFFFFFFFFF；立即数5时为0、3时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: cmp.ui](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.2.1。

<a id="insn-057"></a>

## 57. `cmp.si_rrii_rd`

**用途**：将寄存器与立即数比较，返回−1/0/+1。

**操作数形式**：`cmp.si rdha, rdhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：rdha为目的，rdhb为源，imms12为12位有符号立即数（−2048…2047）。

**编码**：mask=`0xFF000000`，value=`0x5D000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hb], 64)
B = sext(imms12, 12)
R = -1 if A < B else (0 if A == B else 1)
D.RD[ha] = R & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 将RD[hb]按64位有符号补码解释，与立即数数值比较。
2. 小于写0xFFFFFFFFFFFFFFFF，相等写0，大于写1；完整覆盖RD[ha]。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：RD[hb]=5、立即数7，RD[ha]=0xFFFFFFFFFFFFFFFF；立即数5时为0、3时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: cmp.si](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.2.1。

<a id="insn-058"></a>

## 58. `ftfma_rrrr_rf`

**用途**：计算 rfHB×rfHC+rfHD，精确积与加数求和后只舍入一次。

**操作数形式**：`ftfma rfha, rfhb, rfhc, rfhd`（rrrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfha` 是目的，`rfhb`/`rfhc` 是乘数，`rfhd` 是加数；三个源先读后写，均可与目的重叠。

**编码**：mask=`0xFF000000`，value=`0x5E000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hb], format=binary32)
B = decode_fp(S.RF[hc], format=binary32)
C = decode_fp(S.RF[hd], format=binary32)
R, F = fp_fusedMultiplyAdd(A, B, C, rounding=S.RF[0][33:32])
D.RF[ha] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hb], format=binary32)
3. B = decode_fp(S.RF[hc], format=binary32)
4. C = decode_fp(S.RF[hd], format=binary32)
5. R, F = fp_fusedMultiplyAdd(A, B, C, rounding=S.RF[0][33:32])
6. D.RF[ha] = encode_fp(R, format=binary32)
7. D.RF[0][4:0] = S.RF[0][4:0] | F
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0为ILLI；0×Inf、Inf 与异号 Inf 相加置 NV 并返回 qNaN；OF/UF/NX 按单次舍入累积。

**算例**：(1+2⁻²³)×(1−2⁻²³)−1 得 −2⁻⁴⁶（0xA8800000）；先 ftmul 再 ftadd 会把积舍入成 +0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftfma](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §20 (fma)。

<a id="insn-059"></a>

## 59. `fofma_rrrr_rf`

**用途**：计算 rfHB×rfHC+rfHD，精确积与加数求和后只舍入一次。

**操作数形式**：`fofma rfha, rfhb, rfhc, rfhd`（rrrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfha` 是目的，`rfhb`/`rfhc` 是乘数，`rfhd` 是加数；三个源先读后写，均可与目的重叠。

**编码**：mask=`0xFF000000`，value=`0x5F000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfha` | `[23:18]` | rf字段 |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hb], format=binary64)
B = decode_fp(S.RF[hc], format=binary64)
C = decode_fp(S.RF[hd], format=binary64)
R, F = fp_fusedMultiplyAdd(A, B, C, rounding=S.RF[0][33:32])
D.RF[ha] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hb], format=binary64)
3. B = decode_fp(S.RF[hc], format=binary64)
4. C = decode_fp(S.RF[hd], format=binary64)
5. R, F = fp_fusedMultiplyAdd(A, B, C, rounding=S.RF[0][33:32])
6. D.RF[ha] = encode_fp(R, format=binary64)
7. D.RF[0][4:0] = S.RF[0][4:0] | F
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0为ILLI；0×Inf、Inf 与异号 Inf 相加置 NV 并返回 qNaN；OF/UF/NX 按单次舍入累积。

**算例**：(1+2⁻²³)×(1−2⁻²³)−1 得 −2⁻⁴⁶（0xA8800000）；先 ftmul 再 ftadd 会把积舍入成 +0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fofma](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §20 (fma)。

<a id="insn-060"></a>

## 60. `cs.n_rrrr_rd`

**用途**：根据条件选择或保留寄存器值。

**操作数形式**：`cs.n rdha, rdhb, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[ha]为条件源，RD[hb]为目的，RD[hc]/RD[hd]为两个候选源。

**编码**：mask=`0xFF000000`，value=`0x60000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[hb] = S.RD[hc] if ((S.RD[ha] >> 63) == 1) else S.RD[hd]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 在任何写入前读取条件和所需源值。
2. 若旧RD[ha]按64位补码为负数（bit63=1），RD[hb]=旧RD[hc]；否则RD[hb]=旧RD[hd]。
3. 赋值写满64位；条件不成立并不豁免非法目的检查。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rdhb=rd0时ILLI；源可为rd0。所有别名读取执行前值。

**算例**：旧RD[ha]=−1、RD[hc]=7、RD[hd]=9时，目的得7；旧RD[ha]=0时得9。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.n](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.5。

<a id="insn-061"></a>

## 61. `cs.n_rrrr_rf`

**用途**：按浮点合约执行 `cs.n`，格式和寄存器字段以编码表为准。

**操作数形式**：`cs.n rdha, rfhb, rfhc, rfhd`（rrrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x61000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RF[hb] = S.RF[hc] if (((S.RD[ha] >> 63) & 1) == 1) else S.RF[hd]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. D.RF[hb] = S.RF[hc] if (((S.RD[ha] >> 63) & 1) == 1) else S.RF[hd]
3. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
4. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.n](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §10 (cs_rf)。

<a id="insn-062"></a>

## 62. `cs.z_rrrr_rd`

**用途**：根据条件选择或保留寄存器值。

**操作数形式**：`cs.z rdha, rdhb, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[ha]为条件源，RD[hb]为目的，RD[hc]/RD[hd]为两个候选源。

**编码**：mask=`0xFF000000`，value=`0x62000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[hb] = S.RD[hc] if (S.RD[ha] == 0) else S.RD[hd]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 在任何写入前读取条件和所需源值。
2. 若旧RD[ha]全部64位为0，RD[hb]=旧RD[hc]；否则RD[hb]=旧RD[hd]。
3. 赋值写满64位；条件不成立并不豁免非法目的检查。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rdhb=rd0时ILLI；源可为rd0。所有别名读取执行前值。

**算例**：旧RD[ha]=0、RD[hc]=7、RD[hd]=9时，目的得7；旧RD[ha]=1时得9。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.z](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.5。

<a id="insn-063"></a>

## 63. `cs.z_rrrr_rf`

**用途**：按浮点合约执行 `cs.z`，格式和寄存器字段以编码表为准。

**操作数形式**：`cs.z rdha, rfhb, rfhc, rfhd`（rrrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x63000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RF[hb] = S.RF[hc] if (S.RD[ha] == 0) else S.RF[hd]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. D.RF[hb] = S.RF[hc] if (S.RD[ha] == 0) else S.RF[hd]
3. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
4. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.z](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §10 (cs_rf)。

<a id="insn-064"></a>

## 64. `cs.p_rrrr_rd`

**用途**：根据条件选择或保留寄存器值。

**操作数形式**：`cs.p rdha, rdhb, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[ha]为条件源，RD[hb]为目的，RD[hc]/RD[hd]为两个候选源。

**编码**：mask=`0xFF000000`，value=`0x64000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[hb] = S.RD[hc] if ((S.RD[ha] >> 63) == 0 and S.RD[ha] != 0) else S.RD[hd]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 在任何写入前读取条件和所需源值。
2. 若旧RD[ha]bit63=0且值不为0，RD[hb]=旧RD[hc]；否则RD[hb]=旧RD[hd]。
3. 赋值写满64位；条件不成立并不豁免非法目的检查。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rdhb=rd0时ILLI；源可为rd0。所有别名读取执行前值。

**算例**：旧RD[ha]=1、RD[hc]=7、RD[hd]=9时，目的得7；旧RD[ha]=0时得9。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.p](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.5。

<a id="insn-065"></a>

## 65. `cs.p_rrrr_rf`

**用途**：按浮点合约执行 `cs.p`，格式和寄存器字段以编码表为准。

**操作数形式**：`cs.p rdha, rfhb, rfhc, rfhd`（rrrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFF000000`，value=`0x65000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RF[hb] = S.RF[hc] if ((((S.RD[ha] >> 63) & 1) == 0 and S.RD[ha] != 0)) else S.RF[hd]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. D.RF[hb] = S.RF[hc] if ((((S.RD[ha] >> 63) & 1) == 0 and S.RD[ha] != 0)) else S.RF[hd]
3. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
4. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.p](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §10 (cs_rf)。

<a id="insn-066"></a>

## 66. `cs.eq_rrrr_rd`

**用途**：根据条件选择或保留寄存器值。

**操作数形式**：`cs.eq rdha, rdhb, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[ha]/RD[hb]为比较源，RD[hc]为目的，RD[hd]为赋值源。

**编码**：mask=`0xFF000000`，value=`0x66000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[hc] = S.RD[hd] if (S.RD[ha] == S.RD[hb]) else S.RD[hc]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 在任何写入前读取条件和所需源值。
2. 若RD[ha]与RD[hb]的完整64位相等，将旧RD[hd]写入RD[hc]；否则保留RD[hc]旧值。
3. 赋值写满64位；条件不成立并不豁免非法目的检查。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rdhc=rd0时ILLI；源可为rd0。所有别名读取执行前值。

**算例**：两个比较源相等、旧RD[hd]=9时，目的变9；相反条件下目的旧值保持。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.eq](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.5。

<a id="insn-067"></a>

## 67. `cs.ne_rrrr_rd`

**用途**：根据条件选择或保留寄存器值。

**操作数形式**：`cs.ne rdha, rdhb, rdhc, rdhd`（rrrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[ha]/RD[hb]为比较源，RD[hc]为目的，RD[hd]为赋值源。

**编码**：mask=`0xFF000000`，value=`0x67000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[hc] = S.RD[hd] if (S.RD[ha] != S.RD[hb]) else S.RD[hc]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 在任何写入前读取条件和所需源值。
2. 若RD[ha]与RD[hb]的完整64位不同，将旧RD[hd]写入RD[hc]；否则保留RD[hc]旧值。
3. 赋值写满64位；条件不成立并不豁免非法目的检查。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rdhc=rd0时ILLI；源可为rd0。所有别名读取执行前值。

**算例**：两个比较源不同、旧RD[hd]=9时，目的变9；相反条件下目的旧值保持。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: cs.ne](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.5。

<a id="insn-068"></a>

## 68. `br.n_riii_rd`

**用途**：当RD[ha]的bit63=1时跳转。

**操作数形式**：`br.n rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x68000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RD[ha] >> 63 == 1)
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]的bit63=1。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.n](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-069"></a>

## 69. `br.nn_riii_rd`

**用途**：当RD[ha]的bit63=0时跳转。

**操作数形式**：`br.nn rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x69000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RD[ha] >> 63 == 0)
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]的bit63=0。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.nn](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-070"></a>

## 70. `br.z_riii_rd`

**用途**：当RD[ha]的全部64位为0时跳转。

**操作数形式**：`br.z rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x6A000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RD[ha] == 0)
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]的全部64位为0。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.z](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-071"></a>

## 71. `br.nz_riii_rd`

**用途**：当RD[ha]的64位值不等于0时跳转。

**操作数形式**：`br.nz rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x6B000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RD[ha] != 0)
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]的64位值不等于0。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.nz](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-072"></a>

## 72. `br.p_riii_rd`

**用途**：当RD[ha]的bit63=0且值非0时跳转。

**操作数形式**：`br.p rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x6C000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool((S.RD[ha] >> 63 == 0) and (S.RD[ha] != 0))
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]的bit63=0且值非0。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.p](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-073"></a>

## 73. `br.np_riii_rd`

**用途**：当RD[ha]的bit63=1或值为0时跳转。

**操作数形式**：`br.np rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x6D000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool((S.RD[ha] >> 63 == 1) or (S.RD[ha] == 0))
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]的bit63=1或值为0。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.np](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-074"></a>

## 74. `br.eq_rrii_rd`

**用途**：当RD[ha]与RD[hb]的64位值相等时跳转。

**操作数形式**：`br.eq rdha, rdhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]和RD[hb]；imms12为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x6E000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RD[ha] == S.RD[hb])
target = (S.RB[0] + (sext(imms12, 12) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]与RD[hb]的64位值相等。
2. 成立：目标=(旧rb0 + (imms12<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.eq](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-075"></a>

## 75. `br.ne_rrii_rd`

**用途**：当RD[ha]与RD[hb]的64位值不同时跳转。

**操作数形式**：`br.ne rdha, rdhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RD[ha]和RD[hb]；imms12为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x6F000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RD[ha] != S.RD[hb])
target = (S.RB[0] + (sext(imms12, 12) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RD[ha]与RD[hb]的64位值不同。
2. 成立：目标=(旧rb0 + (imms12<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.ne](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-076"></a>

## 76. `jump_iiii_rb`

**用途**：无条件跳转。

**操作数形式**：`jump imms24`（iiii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：imms24是24位有符号指令偏移。

**编码**：mask=`0xFF000000`，value=`0x70000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `imms24` | `[23:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
target = ((S.RB[0] + (sext(imms24, 24) << 2))) & ((1 << 64) - 1)
D.RB[0] = target
D.pc = target & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 先用旧状态计算目标 `(旧rb0 + (imms24<<2)) mod 2^64`；立即数是有符号数、单位4字节。
2. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源可为rd0/rb0。目标低两位非0时，本条完成跳转；下一条取指才报IALIGN。

**算例**：旧rb0=0x1000，imms24=3，下一地址0x100C。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: jump](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.3–8.6。

<a id="insn-077"></a>

## 77. `jump_rrii_rb`

**用途**：无条件跳转。

**操作数形式**：`jump rbha, rdhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RB[ha]为基址源、RD[hb]为字节偏移源、imms12为有符号指令偏移。

**编码**：mask=`0xFF000000`，value=`0x71000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
target = ((S.RB[ha] + S.RD[hb] + (sext(imms12, 12) << 2))) & ((1 << 64) - 1)
D.RB[0] = target
D.pc = target & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 先用旧状态计算目标 `(旧RB[ha] + 旧RD[hb] + (imms12<<2)) mod 2^64`；立即数是有符号数、单位4字节。
2. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源可为rd0/rb0。目标低两位非0时，本条完成跳转；下一条取指才报IALIGN。

**算例**：旧rb0=0x1000，RB[ha]=0x2000、RD[hb]=8、imms12=−1，下一地址0x2004。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: jump](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.3–8.6。

<a id="insn-078"></a>

## 78. `br.z_riii_rb`

**用途**：当RB[ha]的全部64位为0时跳转。

**操作数形式**：`br.z rbha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RB[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x72000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RB[ha] == 0)
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RB[ha]的全部64位为0。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.z](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-079"></a>

## 79. `br.nz_riii_rb`

**用途**：当RB[ha]的64位值不等于0时跳转。

**操作数形式**：`br.nz rbha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：条件源为RB[ha]；imms18为有符号指令偏移（单位4字节）。

**编码**：mask=`0xFF000000`，value=`0x73000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
taken = bool(S.RB[ha] != 0)
target = (S.RB[0] + (sext(imms18, 18) << 2)) & ((1 << 64) - 1)
D.RB[0] = target if taken else ((S.RB[0] + 4) & ((1 << 64) - 1))
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 判断旧状态的条件：RB[ha]的64位值不等于0。
2. 成立：目标=(旧rb0 + (imms18<<2)) mod 2^64；不成立：目标=(旧rb0+4) mod 2^64。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源0号寄存器合法。无目的零号约束；不预判目标机器地址是否映射。

**算例**：旧rb0=0x1000、立即数2：条件成立则下一地址0x1008，否则0x1004；立即数−1且成立则0x0FFC。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: br.nz](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.1–8.2。

<a id="insn-080"></a>

## 80. `call_iiii_ra`

**用途**：调用函数并保存返回地址。

**操作数形式**：`call imms24`（iiii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：imms24是24位有符号指令偏移。

**编码**：mask=`0xFF000000`，value=`0x74000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `imms24` | `[23:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
target = ((S.RB[0] + (sext(imms24, 24) << 2))) & ((1 << 64) - 1)
return_pc = (S.RB[0] + 4) & ((1 << 48) - 1)
(D, ok) = ras_push(S, return_pc)
assert ok
D.RB[0] = target
D.pc = target & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 先用旧状态计算目标 `(旧rb0 + (imms24<<2)) mod 2^64`；立即数是有符号数、单位4字节。
2. 将 `(旧rb0+4) mod 2^48` 作为返回地址，执行本文“共同规则：call压栈”的完整流程；新条目递归计数为1。同址且未饱和时递归折叠。栈更新成功后才提交跳转。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源可为rd0/rb0。目标低两位非0时，本条完成跳转；下一条取指才报IALIGN。 返回栈满且未启用MemRAS时RASOF；MemRAS溢出写地址未8字节对齐时MALIGN；异常时返回栈、内存、PC全部不变。

**算例**：旧rb0=0x1000，imms24=3，下一地址0x100C。 若RACNT原为0，ra63变为0x0001000000001004，RACNT变1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: call](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.3–8.6。

<a id="insn-081"></a>

## 81. `call_rrii_ra`

**用途**：调用函数并保存返回地址。

**操作数形式**：`call rbha, rdhb, imms12`（rrii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RB[ha]为基址源、RD[hb]为字节偏移源、imms12为有符号指令偏移。

**编码**：mask=`0xFF000000`，value=`0x75000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbha` | `[23:18]` | rb字段 |
| `rdhb` | `[17:12]` | rd字段 |
| `imms12` | `[11:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
target = ((S.RB[ha] + S.RD[hb] + (sext(imms12, 12) << 2))) & ((1 << 64) - 1)
return_pc = (S.RB[0] + 4) & ((1 << 48) - 1)
(D, ok) = ras_push(S, return_pc)
assert ok
D.RB[0] = target
D.pc = target & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 先用旧状态计算目标 `(旧RB[ha] + 旧RD[hb] + (imms12<<2)) mod 2^64`；立即数是有符号数、单位4字节。
2. 将 `(旧rb0+4) mod 2^48` 作为返回地址，执行本文“共同规则：call压栈”的完整流程；新条目递归计数为1。同址且未饱和时递归折叠。栈更新成功后才提交跳转。
3. 计算出的完整64位目标写回rb0；下一取指地址取其低48位。除call/ret的返回栈效果外，不修改显式源寄存器。

**合法性、异常与边界**：源可为rd0/rb0。目标低两位非0时，本条完成跳转；下一条取指才报IALIGN。 返回栈满且未启用MemRAS时RASOF；MemRAS溢出写地址未8字节对齐时MALIGN；异常时返回栈、内存、PC全部不变。

**算例**：旧rb0=0x1000，RB[ha]=0x2000、RD[hb]=8、imms12=−1，下一地址0x2004。 若RACNT原为0，ra63变为0x0001000000001004，RACNT变1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: call](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.3–8.6。

<a id="insn-082"></a>

## 82. `ret_riii_ra`

**用途**：弹出返回地址，并可同时设置整数返回值。

**操作数形式**：`ret rdha, imms18`（riii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[ha]为返回值目的，imms18为18位有符号返回值；地址来自RAS而非立即数。

**编码**：mask=`0xFF000000`，value=`0x76000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdha` | `[23:18]` | rd字段 |
| `imms18` | `[17:0]` | 有符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
assert not (rdha == 0 and imms18 != 0)
(return_pc, D.RAS, D.mem, ok) = ras_pop(S)
assert ok
D.RD[ha] = sext(imms18, 18) & ((1 << 64) - 1) if ha != 0 else S.RD[0]
D.RB[0] = return_pc & ((1 << 48) - 1)
D.pc = D.RB[0]
commit(D)
```

**标准计算与写回**：

1. 先检查ret rd0的立即数限制，再执行本文“共同规则：ret弹栈”完整流程，取得返回地址。
2. 把imms18符号扩展写入RD[ha]；合法rd0形式丢弃写入。
3. 把弹出的48位返回地址零扩展写入rb0；pc和pc_next为该取指地址。

**合法性、异常与边界**：rdha=rd0且imms18非0为ILLI；有效栈顶计数0、空栈且无MemRAS、MemRAS条目计数0为RASUF；读取MemRAS地址未8字节对齐为MALIGN。所有异常都不改变原状态。

**算例**：RACNT=1、ra63=0x0001000000002000，ret rd1,−1后RD1=0xFFFFFFFFFFFFFFFF、RACNT=0、下一地址0x2000。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-06: ret](../../spec/SimRISC-06-控制流.md)；[指令合约](../../.tao/contracts/contract-isa.md) §8.5–8.6。

<a id="insn-083"></a>

## 83. `swym_oiii_imm`

**用途**：空操作/延时提示；单步golden只观察架构效果。

**操作数形式**：`swym immu18`（oiii；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：immu18为18位无符号提示值0…262143。

**编码**：mask=`0xFFFC0000`，value=`0x47880000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `immu18` | `[17:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D = S
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
D.pc = D.RB[0] & ((1 << 48) - 1)
commit(D)
```

**标准计算与写回**：

1. 不修改数据寄存器、RA、RF和内存。
2. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。
3. 不模拟周期；非零参数也不能被当成非法指令。

**合法性、异常与边界**：本条无额外操作数异常；共同的取指IALIGN检查仍适用。

**算例**：旧rb0=0x1000，无论immu18=0还是1，下一地址0x1004，其他架构状态不变。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-12: swym](../../spec/SimRISC-12-其它指令.md)；[指令合约](../../.tao/contracts/contract-isa.md) §13.1。

<a id="insn-084"></a>

## 84. `and.o_orrr_rd`

**用途**：逐位计算两个64位源。

**操作数形式**：`and.o rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]/RD[hd]为源。

**编码**：mask=`0xFFFC0000`，value=`0x40200000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RD[hc]
B = S.RD[hd]
R = (A & B) & ((1 << 64) - 1)
D.RD[hb] = R
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 两位都为1才得1。
2. 对全部64位运算并写满目的，不保留目的旧位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0xC、B=0xA，结果 `0x0000000000000008`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: and.o](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.3。

<a id="insn-085"></a>

## 85. `or.o_orrr_rd`

**用途**：逐位计算两个64位源。

**操作数形式**：`or.o rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]/RD[hd]为源。

**编码**：mask=`0xFFFC0000`，value=`0x40240000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RD[hc]
B = S.RD[hd]
R = (A | B) & ((1 << 64) - 1)
D.RD[hb] = R
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 至少一位为1就得1。
2. 对全部64位运算并写满目的，不保留目的旧位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0xC、B=0xA，结果 `0x000000000000000E`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: or.o](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.3。

<a id="insn-086"></a>

## 86. `xor.o_orrr_rd`

**用途**：逐位计算两个64位源。

**操作数形式**：`xor.o rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]/RD[hd]为源。

**编码**：mask=`0xFFFC0000`，value=`0x40280000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RD[hc]
B = S.RD[hd]
R = (A ^ B) & ((1 << 64) - 1)
D.RD[hb] = R
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 两位不同得1。
2. 对全部64位运算并写满目的，不保留目的旧位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0xC、B=0xA，结果 `0x0000000000000006`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: xor.o](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.3。

<a id="insn-087"></a>

## 87. `xnor.o_orrr_rd`

**用途**：逐位计算两个64位源。

**操作数形式**：`xnor.o rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]/RD[hd]为源。

**编码**：mask=`0xFFFC0000`，value=`0x402C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RD[hc]
B = S.RD[hd]
R = (A ^ B) & ((1 << 64) - 1)
R ^= ((1 << 64) - 1)
D.RD[hb] = R
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 两位相同得1（异或后按64位取反）。
2. 对全部64位运算并写满目的，不保留目的旧位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0xC、B=0xA，结果 `0xFFFFFFFFFFFFFFF9`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: xnor.o](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.3。

<a id="insn-088"></a>

## 88. `shl.o_orrr_rd`

**用途**：64位左移，低位补0。

**操作数形式**：`shl.o rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x40400000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 64
R = (S.RD[hc] & ((1 << 64) - 1)) << k & ((1 << 64) - 1)
D.RD[hb] = zext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低64位。
2. 左移，低位补0。
3. 结果只保留低64位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源 `0x8000000000000000`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: shl.o](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-089"></a>

## 89. `shr.uo_orrr_rd`

**用途**：64位逻辑右移，高位补0。

**操作数形式**：`shr.uo rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x40480000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 64
R = (S.RD[hc] & ((1 << 64) - 1)) >> k & ((1 << 64) - 1)
D.RD[hb] = zext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低64位。
2. 逻辑右移，高位补0。
3. 结果只保留低64位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源低64位全1、k=1，结果 `0x7FFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: shr.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-090"></a>

## 90. `shr.so_orrr_rd`

**用途**：64位算术右移，高位补源的符号位。

**操作数形式**：`shr.so rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x404C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 64
R = sint(S.RD[hc] & ((1 << 64) - 1), 64) >> k & ((1 << 64) - 1)
D.RD[hb] = sext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低64位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低64位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源低64位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: shr.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-091"></a>

## 91. `shl.o_orri_rd`

**用途**：64位左移，低位补0。

**操作数形式**：`shl.o rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x40600000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 64
R = (S.RD[hc] & ((1 << 64) - 1)) << k & ((1 << 64) - 1)
D.RD[hb] = zext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低64位。
2. 左移，低位补0。
3. 结果只保留低64位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源 `0x8000000000000000`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: shl.o](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-092"></a>

## 92. `shr.uo_orri_rd`

**用途**：64位逻辑右移，高位补0。

**操作数形式**：`shr.uo rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x40680000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 64
R = (S.RD[hc] & ((1 << 64) - 1)) >> k & ((1 << 64) - 1)
D.RD[hb] = zext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低64位。
2. 逻辑右移，高位补0。
3. 结果只保留低64位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源低64位全1、k=1，结果 `0x7FFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: shr.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-093"></a>

## 93. `shr.so_orri_rd`

**用途**：64位算术右移，高位补源的符号位。

**操作数形式**：`shr.so rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x406C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 64
R = sint(S.RD[hc] & ((1 << 64) - 1), 64) >> k & ((1 << 64) - 1)
D.RD[hb] = sext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低64位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低64位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源低64位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: shr.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-094"></a>

## 94. `ext.uo_orrr_rd`

**用途**：64位从第k位向高位扩展。

**操作数形式**：`ext.uo rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x40800000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 64
R = zext(S.RD[hc] & ((1 << (k + 1)) - 1), k + 1) & ((1 << 64) - 1)
D.RD[hb] = zext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；这是最后保留的位编号，不是位数。
2. 保留源bits[k:0]，其余高位清零，形成64位零扩展结果。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源0x180、k=7，结果0x0000000000000080。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: ext.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-095"></a>

## 95. `ext.so_orrr_rd`

**用途**：64位从第k位向高位扩展。

**操作数形式**：`ext.so rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x40840000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 64
R = sext(S.RD[hc] & ((1 << (k + 1)) - 1), k + 1) & ((1 << 64) - 1)
D.RD[hb] = sext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；这是最后保留的位编号，不是位数。
2. 保留源bits[k:0]，其余高位用源bit[k]填充，形成64位符号扩展结果。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源0x180、k=7，结果0xFFFFFFFFFFFFFF80。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: ext.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-096"></a>

## 96. `ext.uo_orri_rd`

**用途**：64位从第k位向高位扩展。

**操作数形式**：`ext.uo rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x40A00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 64
R = zext(S.RD[hc] & ((1 << (k + 1)) - 1), k + 1) & ((1 << 64) - 1)
D.RD[hb] = zext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；这是最后保留的位编号，不是位数。
2. 保留源bits[k:0]，其余高位清零，形成64位零扩展结果。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源0x180、k=7，结果0x0000000000000080。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: ext.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-097"></a>

## 97. `ext.so_orri_rd`

**用途**：64位从第k位向高位扩展。

**操作数形式**：`ext.so rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x40A40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 64
R = sext(S.RD[hc] & ((1 << (k + 1)) - 1), k + 1) & ((1 << 64) - 1)
D.RD[hb] = sext(R, 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；这是最后保留的位编号，不是位数。
2. 保留源bits[k:0]，其余高位用源bit[k]填充，形成64位符号扩展结果。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>63时ILLI；检查之前不能再按64取模。本格式编码的k本来就在0…63，所以64位情形不存在更大的合法编码量。

**算例**：源0x180、k=7，结果0xFFFFFFFFFFFFFF80。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: ext.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-098"></a>

## 98. `add.o_orrr_bbd`

**用途**：进行完整64位地址加减。

**操作数形式**：`add.o rbhb, rbhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：目的为RB[hb]，源A=旧RB[hc]，源B=旧RD[hd]。

**编码**：mask=`0xFFFC0000`，value=`0x40C00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbhb` | `[17:12]` | rb字段 |
| `rbhc` | `[11:6]` | rb字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RB[hb] = (S.RB[hc] + S.RD[hd]) & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. `RB[hb]=(A+B) mod 2^64`，不截到48位。
2. 源先读再写；高16位也参与运算。只在后续访存/取指时截到48位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rb0 为ILLI；0号源合法。

**算例**：A=0x0001000000000005、B=7，结果0x000100000000000C。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-05: add.o](../../spec/SimRISC-05-64位地址运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §7.1、§7.3。

<a id="insn-099"></a>

## 99. `sub.o_orrr_bbd`

**用途**：进行完整64位地址加减。

**操作数形式**：`sub.o rbhb, rbhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：目的为RB[hb]，源A=旧RB[hc]，源B=旧RD[hd]。

**编码**：mask=`0xFFFC0000`，value=`0x40C40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbhb` | `[17:12]` | rb字段 |
| `rbhc` | `[11:6]` | rb字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RB[hb] = (S.RB[hc] - S.RD[hd]) & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. `RB[hb]=(A−B) mod 2^64`，不截到48位。
2. 源先读再写；高16位也参与运算。只在后续访存/取指时截到48位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rb0 为ILLI；0号源合法。

**算例**：A=0x0001000000000005、B=7，结果0x0000FFFFFFFFFFFE。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-05: sub.o](../../spec/SimRISC-05-64位地址运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §7.1、§7.3。

<a id="insn-100"></a>

## 100. `cmp.uo_orrr_dbb`

**用途**：比较完整地址寄存器值。

**操作数形式**：`cmp.uo rdhb, rbhc, rbhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：目的为RD[hb]，源A=旧RB[hc]，源B=旧RB[hd]。

**编码**：mask=`0xFFFC0000`，value=`0x40C80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rbhc` | `[11:6]` | rb字段 |
| `rbhd` | `[5:0]` | rb字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[hb] = -1 if S.RB[hc] < S.RB[hd] else (0 if S.RB[hc] == S.RB[hd] else 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 按完整64位无符号比较A、B，小于/等于/大于分别写全64位−1/0/+1。
2. 源先读再写；高16位也参与运算。只在后续访存/取指时截到48位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rd0 为ILLI；0号源合法。

**算例**：A=0x0001000000000005、B=6，结果1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-05: cmp.uo](../../spec/SimRISC-05-64位地址运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §7.1、§7.3。

<a id="insn-101"></a>

## 101. `sub.o_orrr_dbb`

**用途**：进行完整64位地址加减。

**操作数形式**：`sub.o rdhb, rbhc, rbhd`（orrr；表内scope=m3）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：目的为RD[hb]，源A=旧RB[hc]，源B=旧RB[hd]。

**编码**：mask=`0xFFFC0000`，value=`0x40CC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rbhc` | `[11:6]` | rb字段 |
| `rbhd` | `[5:0]` | rb字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
D.RD[hb] = (S.RB[hc] - S.RB[hd]) & ((1 << 64) - 1)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. `RD[hb]=(A−B) mod 2^64`，不截到48位。
2. 源先读再写；高16位也参与运算。只在后续访存/取指时截到48位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的 rd0 为ILLI；0号源合法。

**算例**：A=0x0001000000000005、B=7，结果0x0000FFFFFFFFFFFE。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-05: sub.o](../../spec/SimRISC-05-64位地址运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §7.1、§7.3。

<a id="insn-102"></a>

## 102. `cmp.uo_orrr_rd`

**用途**：64位无符号比较。

**操作数形式**：`cmp.uo rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x40A80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 64) - 1), 64)
B = uint(S.RD[hd] & ((1 << 64) - 1), 64)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = zext(R & ((1 << 64) - 1), 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低64位，按无符号整数解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: cmp.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-103"></a>

## 103. `cmp.so_orrr_rd`

**用途**：64位有符号比较。

**操作数形式**：`cmp.so rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x40AC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 64) - 1), 64)
B = sint(S.RD[hd] & ((1 << 64) - 1), 64)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = sext(R & ((1 << 64) - 1), 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低64位，按有符号补码解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: cmp.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-104"></a>

## 104. `rd2rd_orri_rd`

**用途**：把RD连续寄存器复制到RD。

**操作数形式**：`rd2rd rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdhb` 是目的起点，`rdhc` 是源起点，`immu6` 是个数。

**编码**：mask=`0xFFFC0000`，value=`0x40B00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63
assert hb + N <= 64 and hc + N <= 64
assert not ("RD" == "RD" and overlap([hc, hc + N), [hb, hb + N)))
tmp[i] = S.RD[hc + i] for i in range(N)
D.RD[hb + i] = tmp[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 先检查两个寄存器区间，再按 i=0…n−1 将旧的 `RD[hc+i]` 复制到 `RD[hb+i]`；每个元素64位，不做符号转换或48位截断。
2. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：`n=immu6` 必须为1–63，`hb+n<=64` 且 `hc+n<=64`；否则 ILLI。 目的起点不可为 `rd0`。 两区间有任何交集（包括完全相同）即 ILLI。

**算例**：源寄存器1=5、2=9，目的起点10、个数2；执行后 `rd10=5`、`rd11=9`，其他显式寄存器不变。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: rd2rd](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §4、§3.3.3。

<a id="insn-105"></a>

## 105. `rd2ra_orri_ra`

**用途**：把RD连续寄存器复制到RA。

**操作数形式**：`rd2ra rahb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rahb` 是目的起点，`rdhc` 是源起点，`immu6` 是个数。

**编码**：mask=`0xFFFC0000`，value=`0x40B40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rahb` | `[17:12]` | ra字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63
assert hb + N <= 64 and hc + N <= 64
assert not ("RD" == "RA" and overlap([hc, hc + N), [hb, hb + N)))
tmp[i] = S.RD[hc + i] for i in range(N)
D.RA[hb + i] = tmp[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 先检查两个寄存器区间，再按 i=0…n−1 将旧的 `RD[hc+i]` 复制到 `RA[hb+i]`；每个元素64位，不做符号转换或48位截断。
2. 目的包含ra0时，丢弃写入值的SBZ[63:54]，只写其余54位。
3. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：`n=immu6` 必须为1–63，`hb+n<=64` 且 `hc+n<=64`；否则 ILLI。 不同寄存器组的同号区间不构成重叠；源可包含0号寄存器。

**算例**：源寄存器1=5、2=9，目的起点10、个数2；执行后 `ra10=5`、`ra11=9`，其他显式寄存器不变。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: rd2ra](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §4、§3.3.3。

<a id="insn-106"></a>

## 106. `ra2rd_orri_ra`

**用途**：把RA连续寄存器复制到RD。

**操作数形式**：`ra2rd rdhb, rahc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdhb` 是目的起点，`rahc` 是源起点，`immu6` 是个数。

**编码**：mask=`0xFFFC0000`，value=`0x40B80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rahc` | `[11:6]` | ra字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63
assert hb + N <= 64 and hc + N <= 64
assert not ("RA" == "RD" and overlap([hc, hc + N), [hb, hb + N)))
tmp[i] = S.RA[hc + i] for i in range(N)
D.RD[hb + i] = tmp[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 先检查两个寄存器区间，再按 i=0…n−1 将旧的 `RA[hc+i]` 复制到 `RD[hb+i]`；每个元素64位，不做符号转换或48位截断。
2. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：`n=immu6` 必须为1–63，`hb+n<=64` 且 `hc+n<=64`；否则 ILLI。 目的起点不可为 `rd0`。 不同寄存器组的同号区间不构成重叠；源可包含0号寄存器。

**算例**：源寄存器1=5、2=9，目的起点10、个数2；执行后 `rd10=5`、`rd11=9`，其他显式寄存器不变。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: ra2rd](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §4、§3.3.3。

<a id="insn-107"></a>

## 107. `rb2rb_orri_rb`

**用途**：把RB连续寄存器复制到RB。

**操作数形式**：`rb2rb rbhb, rbhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbhb` 是目的起点，`rbhc` 是源起点，`immu6` 是个数。

**编码**：mask=`0xFFFC0000`，value=`0x40D00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbhb` | `[17:12]` | rb字段 |
| `rbhc` | `[11:6]` | rb字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63
assert hb + N <= 64 and hc + N <= 64
assert not ("RB" == "RB" and overlap([hc, hc + N), [hb, hb + N)))
tmp[i] = S.RB[hc + i] for i in range(N)
D.RB[hb + i] = tmp[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 先检查两个寄存器区间，再按 i=0…n−1 将旧的 `RB[hc+i]` 复制到 `RB[hb+i]`；每个元素64位，不做符号转换或48位截断。
2. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：`n=immu6` 必须为1–63，`hb+n<=64` 且 `hc+n<=64`；否则 ILLI。 目的起点不可为 `rb0`。 两区间有任何交集（包括完全相同）即 ILLI。

**算例**：源寄存器1=5、2=9，目的起点10、个数2；执行后 `rb10=5`、`rb11=9`，其他显式寄存器不变。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: rb2rb](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §4、§3.3.3。

<a id="insn-108"></a>

## 108. `rd2rb_orri_rb`

**用途**：把RD连续寄存器复制到RB。

**操作数形式**：`rd2rb rbhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rbhb` 是目的起点，`rdhc` 是源起点，`immu6` 是个数。

**编码**：mask=`0xFFFC0000`，value=`0x40D40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rbhb` | `[17:12]` | rb字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63
assert hb + N <= 64 and hc + N <= 64
assert not ("RD" == "RB" and overlap([hc, hc + N), [hb, hb + N)))
tmp[i] = S.RD[hc + i] for i in range(N)
D.RB[hb + i] = tmp[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 先检查两个寄存器区间，再按 i=0…n−1 将旧的 `RD[hc+i]` 复制到 `RB[hb+i]`；每个元素64位，不做符号转换或48位截断。
2. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：`n=immu6` 必须为1–63，`hb+n<=64` 且 `hc+n<=64`；否则 ILLI。 目的起点不可为 `rb0`。 不同寄存器组的同号区间不构成重叠；源可包含0号寄存器。

**算例**：源寄存器1=5、2=9，目的起点10、个数2；执行后 `rb10=5`、`rb11=9`，其他显式寄存器不变。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: rd2rb](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §4、§3.3.3。

<a id="insn-109"></a>

## 109. `rb2rd_orri_rb`

**用途**：把RB连续寄存器复制到RD。

**操作数形式**：`rb2rd rdhb, rbhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rdhb` 是目的起点，`rbhc` 是源起点，`immu6` 是个数。

**编码**：mask=`0xFFFC0000`，value=`0x40D80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rbhc` | `[11:6]` | rb字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63
assert hb + N <= 64 and hc + N <= 64
assert not ("RB" == "RD" and overlap([hc, hc + N), [hb, hb + N)))
tmp[i] = S.RB[hc + i] for i in range(N)
D.RD[hb + i] = tmp[i] for i in range(N)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 先检查两个寄存器区间，再按 i=0…n−1 将旧的 `RB[hc+i]` 复制到 `RD[hb+i]`；每个元素64位，不做符号转换或48位截断。
2. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：`n=immu6` 必须为1–63，`hb+n<=64` 且 `hc+n<=64`；否则 ILLI。 目的起点不可为 `rd0`。 不同寄存器组的同号区间不构成重叠；源可包含0号寄存器。

**算例**：源寄存器1=5、2=9，目的起点10、个数2；执行后 `rd10=5`、`rd11=9`，其他显式寄存器不变。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: rb2rd](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md) §4、§3.3.3。

<a id="insn-110"></a>

## 110. `div.uo_orrr_rd`

**用途**：64位无符号求商。

**操作数形式**：`div.uo rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x40E00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 64) - 1), 64)
B = uint(S.RD[hd] & ((1 << 64) - 1), 64)
Q = trunc0(A / B) if B != 0 else ((1 << 64) - 1) if not False else -1
Q = -((1 << (64 - 1))) if (False and A == -(1 << (64 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = zext(R & ((1 << 64) - 1), 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低64位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. R的低64位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果2。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: div.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-111"></a>

## 111. `div.so_orrr_rd`

**用途**：64位有符号求商。

**操作数形式**：`div.so rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x40E40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 64) - 1), 64)
B = sint(S.RD[hd] & ((1 << 64) - 1), 64)
Q = trunc0(A / B) if B != 0 else ((1 << 64) - 1) if not True else -1
Q = -((1 << (64 - 1))) if (True and A == -(1 << (64 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = sext(R & ((1 << 64) - 1), 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低64位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. A=−2^63且B=−1时，返回−2^63。 不触发ILLI。
5. R的低64位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFE。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: div.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-112"></a>

## 112. `rem.uo_orrr_rd`

**用途**：64位无符号求余数。

**操作数形式**：`rem.uo rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x40E80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 64) - 1), 64)
B = uint(S.RD[hd] & ((1 << 64) - 1), 64)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (64 - 1))) if (False and A == -(1 << (64 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = zext(R & ((1 << 64) - 1), 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低64位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. R的低64位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: rem.uo](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-113"></a>

## 113. `rem.so_orrr_rd`

**用途**：64位有符号求余数。

**操作数形式**：`rem.so rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x40EC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 64) - 1), 64)
B = sint(S.RD[hd] & ((1 << 64) - 1), 64)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (64 - 1))) if (True and A == -(1 << (64 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = sext(R & ((1 << 64) - 1), 64)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低64位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. A=−2^63且B=−1时，返回0。 不触发ILLI。
5. R的低64位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFF。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-04: rem.so](../../spec/SimRISC-04-64位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-114"></a>

## 114. `rd2rf_orri_rf`

**用途**：按浮点合约执行 `rd2rf`，格式和寄存器字段以编码表为准。

**操作数形式**：`rd2rf rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x40F40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i] = src[i]
D.RF[hb:hb + N] = val[0:N]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i] = src[i]
7. D.RF[hb:hb + N] = val[0:N]
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: rd2rf](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §12 (rf_move)。

<a id="insn-115"></a>

## 115. `rf2rd_orri_rf`

**用途**：按浮点合约执行 `rf2rd`，格式和寄存器字段以编码表为准。

**操作数形式**：`rf2rd rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x40F80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i] = src[i]
D.RD[hb:hb + N] = val[0:N]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i] = src[i]
7. D.RD[hb:hb + N] = val[0:N]
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-02: rf2rd](../../spec/SimRISC-02-寄存器复制.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §12 (rf_move)。

<a id="insn-116"></a>

## 116. `shl.t_orrr_rd`

**用途**：32位左移，低位补0。

**操作数形式**：`shl.t rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x41400000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 32
R = (S.RD[hc] & ((1 << 32) - 1)) << k & ((1 << 32) - 1)
D.RD[hb] = zext(R, 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低32位。
2. 左移，低位补0。
3. 结果只保留低32位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>31时ILLI；检查之前不能再按32取模。

**算例**：源 `0x0000000080000000`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: shl.t](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-117"></a>

## 117. `shr.ut_orrr_rd`

**用途**：32位逻辑右移，高位补0。

**操作数形式**：`shr.ut rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x41480000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 32
R = (S.RD[hc] & ((1 << 32) - 1)) >> k & ((1 << 32) - 1)
D.RD[hb] = zext(R, 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低32位。
2. 逻辑右移，高位补0。
3. 结果只保留低32位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>31时ILLI；检查之前不能再按32取模。

**算例**：源低32位全1、k=1，结果 `0x000000007FFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: shr.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-118"></a>

## 118. `shr.st_orrr_rd`

**用途**：32位算术右移，高位补源的符号位。

**操作数形式**：`shr.st rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x414C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 32
R = sint(S.RD[hc] & ((1 << 32) - 1), 32) >> k & ((1 << 32) - 1)
D.RD[hb] = sext(R, 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低32位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低32位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>31时ILLI；检查之前不能再按32取模。

**算例**：源低32位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: shr.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-119"></a>

## 119. `shl.t_orri_rd`

**用途**：32位左移，低位补0。

**操作数形式**：`shl.t rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x41600000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 32
R = (S.RD[hc] & ((1 << 32) - 1)) << k & ((1 << 32) - 1)
D.RD[hb] = zext(R, 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低32位。
2. 左移，低位补0。
3. 结果只保留低32位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>31时ILLI；检查之前不能再按32取模。

**算例**：源 `0x0000000080000000`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: shl.t](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-120"></a>

## 120. `shr.ut_orri_rd`

**用途**：32位逻辑右移，高位补0。

**操作数形式**：`shr.ut rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x41680000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 32
R = (S.RD[hc] & ((1 << 32) - 1)) >> k & ((1 << 32) - 1)
D.RD[hb] = zext(R, 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低32位。
2. 逻辑右移，高位补0。
3. 结果只保留低32位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>31时ILLI；检查之前不能再按32取模。

**算例**：源低32位全1、k=1，结果 `0x000000007FFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: shr.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-121"></a>

## 121. `shr.st_orri_rd`

**用途**：32位算术右移，高位补源的符号位。

**操作数形式**：`shr.st rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x416C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 32
R = sint(S.RD[hc] & ((1 << 32) - 1), 32) >> k & ((1 << 32) - 1)
D.RD[hb] = sext(R, 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低32位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低32位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>31时ILLI；检查之前不能再按32取模。

**算例**：源低32位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: shr.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-122"></a>

## 122. `add.ut_orrr_rd`

**用途**：32位无符号相加。

**操作数形式**：`add.ut rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41800000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 32) - 1), 32)
B = uint(S.RD[hd] & ((1 << 32) - 1), 32)
R = (A + B) & ((1 << 32) - 1)
D.RD[hb] = zext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按无符号整数解释为A、B。
2. 计算 `R=A+B`，保留低32位；超出位宽的部分丢弃。
3. R的低32位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=2^31−1、B=1，结果 `0x0000000080000000`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: add.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-123"></a>

## 123. `add.st_orrr_rd`

**用途**：32位有符号相加。

**操作数形式**：`add.st rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41840000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 32) - 1), 32)
B = sint(S.RD[hd] & ((1 << 32) - 1), 32)
R = (A + B) & ((1 << 32) - 1)
D.RD[hb] = sext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按有符号补码解释为A、B。
2. 计算 `R=A+B`，保留低32位；超出位宽的部分丢弃。
3. R的低32位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=2^31−1、B=1，结果 `0xFFFFFFFF80000000`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: add.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-124"></a>

## 124. `sub.ut_orrr_rd`

**用途**：32位无符号相减。

**操作数形式**：`sub.ut rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41A00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 32) - 1), 32)
B = uint(S.RD[hd] & ((1 << 32) - 1), 32)
R = (A - B) & ((1 << 32) - 1)
D.RD[hb] = zext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按无符号整数解释为A、B。
2. 计算 `R=A−B`，保留低32位；超出位宽的部分丢弃。
3. R的低32位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0、B=1，结果 `0x00000000FFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: sub.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-125"></a>

## 125. `sub.st_orrr_rd`

**用途**：32位有符号相减。

**操作数形式**：`sub.st rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41A40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 32) - 1), 32)
B = sint(S.RD[hd] & ((1 << 32) - 1), 32)
R = (A - B) & ((1 << 32) - 1)
D.RD[hb] = sext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按有符号补码解释为A、B。
2. 计算 `R=A−B`，保留低32位；超出位宽的部分丢弃。
3. R的低32位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0、B=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: sub.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-126"></a>

## 126. `cmp.ut_orrr_rd`

**用途**：32位无符号比较。

**操作数形式**：`cmp.ut rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41A80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 32) - 1), 32)
B = uint(S.RD[hd] & ((1 << 32) - 1), 32)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = zext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按无符号整数解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: cmp.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-127"></a>

## 127. `cmp.st_orrr_rd`

**用途**：32位有符号比较。

**操作数形式**：`cmp.st rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41AC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 32) - 1), 32)
B = sint(S.RD[hd] & ((1 << 32) - 1), 32)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = sext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按有符号补码解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: cmp.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-128"></a>

## 128. `mul.ut_orrr_rd`

**用途**：32位无符号相乘。

**操作数形式**：`mul.ut rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41C00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 32) - 1), 32)
B = uint(S.RD[hd] & ((1 << 32) - 1), 32)
R = (A * B) & ((1 << 32) - 1)
D.RD[hb] = zext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按无符号整数解释为A、B。
2. 计算 `R=A×B`，保留低32位；超出位宽的部分丢弃。
3. R的低32位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=3、B=5，结果 `0x000000000000000F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: mul.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-129"></a>

## 129. `mul.st_orrr_rd`

**用途**：32位有符号相乘。

**操作数形式**：`mul.st rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41C40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 32) - 1), 32)
B = sint(S.RD[hd] & ((1 << 32) - 1), 32)
R = (A * B) & ((1 << 32) - 1)
D.RD[hb] = sext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按有符号补码解释为A、B。
2. 计算 `R=A×B`，保留低32位；超出位宽的部分丢弃。
3. R的低32位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=3、B=5，结果 `0x000000000000000F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: mul.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-130"></a>

## 130. `div.ut_orrr_rd`

**用途**：32位无符号求商。

**操作数形式**：`div.ut rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41E00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 32) - 1), 32)
B = uint(S.RD[hd] & ((1 << 32) - 1), 32)
Q = trunc0(A / B) if B != 0 else ((1 << 32) - 1) if not False else -1
Q = -((1 << (32 - 1))) if (False and A == -(1 << (32 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = zext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. R的低32位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果2。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: div.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-131"></a>

## 131. `div.st_orrr_rd`

**用途**：32位有符号求商。

**操作数形式**：`div.st rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41E40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 32) - 1), 32)
B = sint(S.RD[hd] & ((1 << 32) - 1), 32)
Q = trunc0(A / B) if B != 0 else ((1 << 32) - 1) if not True else -1
Q = -((1 << (32 - 1))) if (True and A == -(1 << (32 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = sext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. A=−2^31且B=−1时，返回−2^31。 不触发ILLI。
5. R的低32位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFE。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: div.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-132"></a>

## 132. `rem.ut_orrr_rd`

**用途**：32位无符号求余数。

**操作数形式**：`rem.ut rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41E80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 32) - 1), 32)
B = uint(S.RD[hd] & ((1 << 32) - 1), 32)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (32 - 1))) if (False and A == -(1 << (32 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = zext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. R的低32位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: rem.ut](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-133"></a>

## 133. `rem.st_orrr_rd`

**用途**：32位有符号求余数。

**操作数形式**：`rem.st rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x41EC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 32) - 1), 32)
B = sint(S.RD[hd] & ((1 << 32) - 1), 32)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (32 - 1))) if (True and A == -(1 << (32 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = sext(R & ((1 << 32) - 1), 32)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低32位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. A=−2^31且B=−1时，返回0。 不触发ILLI。
5. R的低32位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFF。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-08: rem.st](../../spec/SimRISC-08-32位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-134"></a>

## 134. `shl.w_orrr_rd`

**用途**：16位左移，低位补0。

**操作数形式**：`shl.w rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x42400000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 16
R = (S.RD[hc] & ((1 << 16) - 1)) << k & ((1 << 16) - 1)
D.RD[hb] = zext(R, 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低16位。
2. 左移，低位补0。
3. 结果只保留低16位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>15时ILLI；检查之前不能再按16取模。

**算例**：源 `0x0000000000008000`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: shl.w](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-135"></a>

## 135. `shr.uw_orrr_rd`

**用途**：16位逻辑右移，高位补0。

**操作数形式**：`shr.uw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x42480000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 16
R = (S.RD[hc] & ((1 << 16) - 1)) >> k & ((1 << 16) - 1)
D.RD[hb] = zext(R, 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低16位。
2. 逻辑右移，高位补0。
3. 结果只保留低16位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>15时ILLI；检查之前不能再按16取模。

**算例**：源低16位全1、k=1，结果 `0x0000000000007FFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: shr.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-136"></a>

## 136. `shr.sw_orrr_rd`

**用途**：16位算术右移，高位补源的符号位。

**操作数形式**：`shr.sw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x424C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 16
R = sint(S.RD[hc] & ((1 << 16) - 1), 16) >> k & ((1 << 16) - 1)
D.RD[hb] = sext(R, 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低16位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低16位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>15时ILLI；检查之前不能再按16取模。

**算例**：源低16位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: shr.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-137"></a>

## 137. `shl.w_orri_rd`

**用途**：16位左移，低位补0。

**操作数形式**：`shl.w rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x42600000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 16
R = (S.RD[hc] & ((1 << 16) - 1)) << k & ((1 << 16) - 1)
D.RD[hb] = zext(R, 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低16位。
2. 左移，低位补0。
3. 结果只保留低16位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>15时ILLI；检查之前不能再按16取模。

**算例**：源 `0x0000000000008000`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: shl.w](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-138"></a>

## 138. `shr.uw_orri_rd`

**用途**：16位逻辑右移，高位补0。

**操作数形式**：`shr.uw rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x42680000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 16
R = (S.RD[hc] & ((1 << 16) - 1)) >> k & ((1 << 16) - 1)
D.RD[hb] = zext(R, 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低16位。
2. 逻辑右移，高位补0。
3. 结果只保留低16位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>15时ILLI；检查之前不能再按16取模。

**算例**：源低16位全1、k=1，结果 `0x0000000000007FFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: shr.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-139"></a>

## 139. `shr.sw_orri_rd`

**用途**：16位算术右移，高位补源的符号位。

**操作数形式**：`shr.sw rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x426C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 16
R = sint(S.RD[hc] & ((1 << 16) - 1), 16) >> k & ((1 << 16) - 1)
D.RD[hb] = sext(R, 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低16位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低16位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>15时ILLI；检查之前不能再按16取模。

**算例**：源低16位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: shr.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-140"></a>

## 140. `add.uw_orrr_rd`

**用途**：16位无符号相加。

**操作数形式**：`add.uw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42800000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 16) - 1), 16)
B = uint(S.RD[hd] & ((1 << 16) - 1), 16)
R = (A + B) & ((1 << 16) - 1)
D.RD[hb] = zext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按无符号整数解释为A、B。
2. 计算 `R=A+B`，保留低16位；超出位宽的部分丢弃。
3. R的低16位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=2^15−1、B=1，结果 `0x0000000000008000`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: add.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-141"></a>

## 141. `add.sw_orrr_rd`

**用途**：16位有符号相加。

**操作数形式**：`add.sw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42840000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 16) - 1), 16)
B = sint(S.RD[hd] & ((1 << 16) - 1), 16)
R = (A + B) & ((1 << 16) - 1)
D.RD[hb] = sext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按有符号补码解释为A、B。
2. 计算 `R=A+B`，保留低16位；超出位宽的部分丢弃。
3. R的低16位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=2^15−1、B=1，结果 `0xFFFFFFFFFFFF8000`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: add.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-142"></a>

## 142. `sub.uw_orrr_rd`

**用途**：16位无符号相减。

**操作数形式**：`sub.uw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42A00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 16) - 1), 16)
B = uint(S.RD[hd] & ((1 << 16) - 1), 16)
R = (A - B) & ((1 << 16) - 1)
D.RD[hb] = zext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按无符号整数解释为A、B。
2. 计算 `R=A−B`，保留低16位；超出位宽的部分丢弃。
3. R的低16位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0、B=1，结果 `0x000000000000FFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: sub.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-143"></a>

## 143. `sub.sw_orrr_rd`

**用途**：16位有符号相减。

**操作数形式**：`sub.sw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42A40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 16) - 1), 16)
B = sint(S.RD[hd] & ((1 << 16) - 1), 16)
R = (A - B) & ((1 << 16) - 1)
D.RD[hb] = sext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按有符号补码解释为A、B。
2. 计算 `R=A−B`，保留低16位；超出位宽的部分丢弃。
3. R的低16位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0、B=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: sub.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-144"></a>

## 144. `cmp.uw_orrr_rd`

**用途**：16位无符号比较。

**操作数形式**：`cmp.uw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42A80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 16) - 1), 16)
B = uint(S.RD[hd] & ((1 << 16) - 1), 16)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = zext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按无符号整数解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: cmp.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-145"></a>

## 145. `cmp.sw_orrr_rd`

**用途**：16位有符号比较。

**操作数形式**：`cmp.sw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42AC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 16) - 1), 16)
B = sint(S.RD[hd] & ((1 << 16) - 1), 16)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = sext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按有符号补码解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: cmp.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-146"></a>

## 146. `mul.uw_orrr_rd`

**用途**：16位无符号相乘。

**操作数形式**：`mul.uw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42C00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 16) - 1), 16)
B = uint(S.RD[hd] & ((1 << 16) - 1), 16)
R = (A * B) & ((1 << 16) - 1)
D.RD[hb] = zext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按无符号整数解释为A、B。
2. 计算 `R=A×B`，保留低16位；超出位宽的部分丢弃。
3. R的低16位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=3、B=5，结果 `0x000000000000000F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: mul.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-147"></a>

## 147. `mul.sw_orrr_rd`

**用途**：16位有符号相乘。

**操作数形式**：`mul.sw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42C40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 16) - 1), 16)
B = sint(S.RD[hd] & ((1 << 16) - 1), 16)
R = (A * B) & ((1 << 16) - 1)
D.RD[hb] = sext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按有符号补码解释为A、B。
2. 计算 `R=A×B`，保留低16位；超出位宽的部分丢弃。
3. R的低16位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=3、B=5，结果 `0x000000000000000F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: mul.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-148"></a>

## 148. `div.uw_orrr_rd`

**用途**：16位无符号求商。

**操作数形式**：`div.uw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42E00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 16) - 1), 16)
B = uint(S.RD[hd] & ((1 << 16) - 1), 16)
Q = trunc0(A / B) if B != 0 else ((1 << 16) - 1) if not False else -1
Q = -((1 << (16 - 1))) if (False and A == -(1 << (16 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = zext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. R的低16位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果2。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: div.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-149"></a>

## 149. `div.sw_orrr_rd`

**用途**：16位有符号求商。

**操作数形式**：`div.sw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42E40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 16) - 1), 16)
B = sint(S.RD[hd] & ((1 << 16) - 1), 16)
Q = trunc0(A / B) if B != 0 else ((1 << 16) - 1) if not True else -1
Q = -((1 << (16 - 1))) if (True and A == -(1 << (16 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = sext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. A=−2^15且B=−1时，返回−2^15。 不触发ILLI。
5. R的低16位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFE。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: div.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-150"></a>

## 150. `rem.uw_orrr_rd`

**用途**：16位无符号求余数。

**操作数形式**：`rem.uw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42E80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 16) - 1), 16)
B = uint(S.RD[hd] & ((1 << 16) - 1), 16)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (16 - 1))) if (False and A == -(1 << (16 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = zext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. R的低16位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: rem.uw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-151"></a>

## 151. `rem.sw_orrr_rd`

**用途**：16位有符号求余数。

**操作数形式**：`rem.sw rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x42EC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 16) - 1), 16)
B = sint(S.RD[hd] & ((1 << 16) - 1), 16)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (16 - 1))) if (True and A == -(1 << (16 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = sext(R & ((1 << 16) - 1), 16)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低16位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. A=−2^15且B=−1时，返回0。 不触发ILLI。
5. R的低16位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFF。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-09: rem.sw](../../spec/SimRISC-09-16位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-152"></a>

## 152. `shl.b_orrr_rd`

**用途**：8位左移，低位补0。

**操作数形式**：`shl.b rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x43400000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 8
R = (S.RD[hc] & ((1 << 8) - 1)) << k & ((1 << 8) - 1)
D.RD[hb] = zext(R, 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低8位。
2. 左移，低位补0。
3. 结果只保留低8位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>7时ILLI；检查之前不能再按8取模。

**算例**：源 `0x0000000000000080`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: shl.b](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-153"></a>

## 153. `shr.ub_orrr_rd`

**用途**：8位逻辑右移，高位补0。

**操作数形式**：`shr.ub rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x43480000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 8
R = (S.RD[hc] & ((1 << 8) - 1)) >> k & ((1 << 8) - 1)
D.RD[hb] = zext(R, 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低8位。
2. 逻辑右移，高位补0。
3. 结果只保留低8位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>7时ILLI；检查之前不能再按8取模。

**算例**：源低8位全1、k=1，结果 `0x000000000000007F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: shr.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-154"></a>

## 154. `shr.sb_orrr_rd`

**用途**：8位算术右移，高位补源的符号位。

**操作数形式**：`shr.sb rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；RD[hd]给出k，仅读其低6位。

**编码**：mask=`0xFFFC0000`，value=`0x434C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = (S.RD[hd] & 0x3f)
assert 0 <= k < 8
R = sint(S.RD[hc] & ((1 << 8) - 1), 8) >> k & ((1 << 8) - 1)
D.RD[hb] = sext(R, 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=旧RD[hd] & 0x3F`；源只取低8位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低8位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>7时ILLI；检查之前不能再按8取模。

**算例**：源低8位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: shr.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-155"></a>

## 155. `shl.b_orri_rd`

**用途**：8位左移，低位补0。

**操作数形式**：`shl.b rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x43600000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 8
R = (S.RD[hc] & ((1 << 8) - 1)) << k & ((1 << 8) - 1)
D.RD[hb] = zext(R, 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低8位。
2. 左移，低位补0。
3. 结果只保留低8位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>7时ILLI；检查之前不能再按8取模。

**算例**：源 `0x0000000000000080`、k=1，移出有效宽度后结果0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: shl.b](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-156"></a>

## 156. `shr.ub_orri_rd`

**用途**：8位逻辑右移，高位补0。

**操作数形式**：`shr.ub rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x43680000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 8
R = (S.RD[hc] & ((1 << 8) - 1)) >> k & ((1 << 8) - 1)
D.RD[hb] = zext(R, 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低8位。
2. 逻辑右移，高位补0。
3. 结果只保留低8位，再零扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>7时ILLI；检查之前不能再按8取模。

**算例**：源低8位全1、k=1，结果 `0x000000000000007F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: shr.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-157"></a>

## 157. `shr.sb_orri_rd`

**用途**：8位算术右移，高位补源的符号位。

**操作数形式**：`shr.sb rdhb, rdhc, immu6`（orri；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的、RD[hc]为源；immu6直接给出k。

**编码**：mask=`0xFFFC0000`，value=`0x436C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
k = immu6
assert 0 <= k < 8
R = sint(S.RD[hc] & ((1 << 8) - 1), 8) >> k & ((1 << 8) - 1)
D.RD[hb] = sext(R, 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 计算 `k=immu6`；源只取低8位。
2. 算术右移，高位补源的符号位。
3. 结果只保留低8位，再符号扩展到64位写回；目的旧高位被覆盖。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。 k>7时ILLI；检查之前不能再按8取模。

**算例**：源低8位全1、k=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: shr.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.4、§10.4、§11.4、§12.4。

<a id="insn-158"></a>

## 158. `add.ub_orrr_rd`

**用途**：8位无符号相加。

**操作数形式**：`add.ub rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43800000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 8) - 1), 8)
B = uint(S.RD[hd] & ((1 << 8) - 1), 8)
R = (A + B) & ((1 << 8) - 1)
D.RD[hb] = zext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按无符号整数解释为A、B。
2. 计算 `R=A+B`，保留低8位；超出位宽的部分丢弃。
3. R的低8位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=2^7−1、B=1，结果 `0x0000000000000080`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: add.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-159"></a>

## 159. `add.sb_orrr_rd`

**用途**：8位有符号相加。

**操作数形式**：`add.sb rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43840000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 8) - 1), 8)
B = sint(S.RD[hd] & ((1 << 8) - 1), 8)
R = (A + B) & ((1 << 8) - 1)
D.RD[hb] = sext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按有符号补码解释为A、B。
2. 计算 `R=A+B`，保留低8位；超出位宽的部分丢弃。
3. R的低8位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=2^7−1、B=1，结果 `0xFFFFFFFFFFFFFF80`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: add.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-160"></a>

## 160. `sub.ub_orrr_rd`

**用途**：8位无符号相减。

**操作数形式**：`sub.ub rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43A00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 8) - 1), 8)
B = uint(S.RD[hd] & ((1 << 8) - 1), 8)
R = (A - B) & ((1 << 8) - 1)
D.RD[hb] = zext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按无符号整数解释为A、B。
2. 计算 `R=A−B`，保留低8位；超出位宽的部分丢弃。
3. R的低8位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0、B=1，结果 `0x00000000000000FF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: sub.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-161"></a>

## 161. `sub.sb_orrr_rd`

**用途**：8位有符号相减。

**操作数形式**：`sub.sb rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43A40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 8) - 1), 8)
B = sint(S.RD[hd] & ((1 << 8) - 1), 8)
R = (A - B) & ((1 << 8) - 1)
D.RD[hb] = sext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按有符号补码解释为A、B。
2. 计算 `R=A−B`，保留低8位；超出位宽的部分丢弃。
3. R的低8位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=0、B=1，结果 `0xFFFFFFFFFFFFFFFF`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: sub.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-162"></a>

## 162. `cmp.ub_orrr_rd`

**用途**：8位无符号比较。

**操作数形式**：`cmp.ub rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43A80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 8) - 1), 8)
B = uint(S.RD[hd] & ((1 << 8) - 1), 8)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = zext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按无符号整数解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: cmp.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-163"></a>

## 163. `cmp.sb_orrr_rd`

**用途**：8位有符号比较。

**操作数形式**：`cmp.sb rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43AC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 8) - 1), 8)
B = sint(S.RD[hd] & ((1 << 8) - 1), 8)
R = -1 if A < B else (0 if A == B else 1)
D.RD[hb] = sext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按有符号补码解释为A、B。
2. A小于B时R=−1，相等时R=0，大于时R=1；结果写满64位，不按操作宽度零扩展。
3. R写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=1、B=2，结果 `0xFFFFFFFFFFFFFFFF`；A=B时为0，A>B时为1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: cmp.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-164"></a>

## 164. `mul.ub_orrr_rd`

**用途**：8位无符号相乘。

**操作数形式**：`mul.ub rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43C00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 8) - 1), 8)
B = uint(S.RD[hd] & ((1 << 8) - 1), 8)
R = (A * B) & ((1 << 8) - 1)
D.RD[hb] = zext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按无符号整数解释为A、B。
2. 计算 `R=A×B`，保留低8位；超出位宽的部分丢弃。
3. R的低8位按零扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=3、B=5，结果 `0x000000000000000F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: mul.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-165"></a>

## 165. `mul.sb_orrr_rd`

**用途**：8位有符号相乘。

**操作数形式**：`mul.sb rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43C40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 8) - 1), 8)
B = sint(S.RD[hd] & ((1 << 8) - 1), 8)
R = (A * B) & ((1 << 8) - 1)
D.RD[hb] = sext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按有符号补码解释为A、B。
2. 计算 `R=A×B`，保留低8位；超出位宽的部分丢弃。
3. R的低8位按符号扩展写满RD[hb]的64位，不保留旧高位。
4. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=3、B=5，结果 `0x000000000000000F`。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: mul.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-166"></a>

## 166. `div.ub_orrr_rd`

**用途**：8位无符号求商。

**操作数形式**：`div.ub rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43E00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 8) - 1), 8)
B = uint(S.RD[hd] & ((1 << 8) - 1), 8)
Q = trunc0(A / B) if B != 0 else ((1 << 8) - 1) if not False else -1
Q = -((1 << (8 - 1))) if (False and A == -(1 << (8 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = zext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. R的低8位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果2。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: div.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-167"></a>

## 167. `div.sb_orrr_rd`

**用途**：8位有符号求商。

**操作数形式**：`div.sb rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43E40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 8) - 1), 8)
B = sint(S.RD[hd] & ((1 << 8) - 1), 8)
Q = trunc0(A / B) if B != 0 else ((1 << 8) - 1) if not True else -1
Q = -((1 << (8 - 1))) if (True and A == -(1 << (8 - 1)) and B == -1) else Q
T = A - Q * B
R = Q
D.RD[hb] = sext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回Q。
3. B按位宽截断后为0时，返回该宽度的全1。 不触发ILLI。
4. A=−2^7且B=−1时，返回−2^7。 不触发ILLI。
5. R的低8位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFE。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: div.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-168"></a>

## 168. `rem.ub_orrr_rd`

**用途**：8位无符号求余数。

**操作数形式**：`rem.ub rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43E80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = uint(S.RD[hc] & ((1 << 8) - 1), 8)
B = uint(S.RD[hd] & ((1 << 8) - 1), 8)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (8 - 1))) if (False and A == -(1 << (8 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = zext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按无符号整数解释为A、B。
2. 正常除法得到Q=floor(A/B)，余数T=A−Q×B；余数在0至B−1之间。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. R的低8位按零扩展写满RD[hb]的64位，不保留旧高位。
5. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=7、B=3，结果1。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: rem.ub](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-169"></a>

## 169. `rem.sb_orrr_rd`

**用途**：8位有符号求余数。

**操作数形式**：`rem.sb rdhb, rdhc, rdhd`（orrr；表内scope=m1）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：RD[hb]为目的，RD[hc]和RD[hd]为源；所有源在写目的前读取。

**编码**：mask=`0xFFFC0000`，value=`0x43EC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `rdhd` | `[5:0]` | rd字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = sint(S.RD[hc] & ((1 << 8) - 1), 8)
B = sint(S.RD[hd] & ((1 << 8) - 1), 8)
Q = trunc0(A / B) if B != 0 else A
Q = -((1 << (8 - 1))) if (True and A == -(1 << (8 - 1)) and B == -1) else Q
T = A - Q * B
R = T
D.RD[hb] = sext(R & ((1 << 8) - 1), 8)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. 取两个源的低8位，按有符号补码解释为A、B。
2. 正常除法得到Q=向零截断(A/B)，余数T=A−Q×B；非零余数与A同号。本指令返回T。
3. B按位宽截断后为0时，返回A。 不触发ILLI。
4. A=−2^7且B=−1时，返回0。 不触发ILLI。
5. R的低8位按符号扩展写满RD[hb]的64位，不保留旧高位。
6. 本条成功后 `rb0 = (旧rb0 + 4) mod 2^64`，下一取指地址取其低48位。

**合法性、异常与边界**：目的寄存器为 `rd0` 时触发 ILLI；源可为 rd0，读数为0。源与目的可同号，使用写入前的源值。

**算例**：A=−7、B=3，结果 0xFFFFFFFFFFFFFFFF。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-10: rem.sb](../../spec/SimRISC-10-8位数据运算.md)；[指令合约](../../.tao/contracts/contract-isa.md) §6.1–6.2、§10.1–10.2、§11.1–11.2、§12.1–12.2。

<a id="insn-170"></a>

## 170. `ftcls_orri_rf`

**用途**：按浮点合约执行 `ftcls`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftcls rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44000000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i] = classify_fp(src[i]) & 0x3ff
D.RD[hb:hb + N] = val[0:N]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i] = classify_fp(src[i]) & 0x3ff
7. D.RD[hb:hb + N] = val[0:N]
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftcls](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §9 (classify)。

<a id="insn-171"></a>

## 171. `ft2fo_orri_rf`

**用途**：按浮点合约执行 `ft2fo`，格式和寄存器字段以编码表为准。

**操作数形式**：`ft2fo rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44040000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = convert_fp(src[i], binary32, binary64, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = convert_fp(src[i], binary32, binary64, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ft2fo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §2 (convert_ff)。

<a id="insn-172"></a>

## 172. `ft2ft_orri_rf`

**用途**：按浮点合约执行 `ft2ft`，格式和寄存器字段以编码表为准。

**操作数形式**：`ft2ft rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44080000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = convert_fp(src[i], binary32, binary32, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = convert_fp(src[i], binary32, binary32, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ft2ft](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §2 (convert_ff)。

<a id="insn-173"></a>

## 173. `ftroot_orri_rf`

**用途**：按浮点合约执行 `ftroot`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftroot rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44180000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
assert immu6 == 2
X = decode_fp(S.RF[hc], format=binary32)
assert not (is_negative_zero(X))  # SPECIFICATION-GAP otherwise
R, F = fp_sqrt(X, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. assert immu6 == 2
3. X = decode_fp(S.RF[hc], format=binary32)
4. assert not (is_negative_zero(X))  # SPECIFICATION-GAP otherwise
5. R, F = fp_sqrt(X, rounding=S.RF[0][33:32])
6. D.RF[hb] = encode_fp(R, format=binary32)
7. D.RF[0][4:0] = S.RF[0][4:0] | F
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftroot](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §6 (root)。

<a id="insn-174"></a>

## 174. `focls_orri_rf`

**用途**：按浮点合约执行 `focls`，格式和寄存器字段以编码表为准。

**操作数形式**：`focls rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44200000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i] = classify_fp(src[i]) & 0x3ff
D.RD[hb:hb + N] = val[0:N]
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i] = classify_fp(src[i]) & 0x3ff
7. D.RD[hb:hb + N] = val[0:N]
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: focls](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §9 (classify)。

<a id="insn-175"></a>

## 175. `fo2ft_orri_rf`

**用途**：按浮点合约执行 `fo2ft`，格式和寄存器字段以编码表为准。

**操作数形式**：`fo2ft rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44240000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = convert_fp(src[i], binary64, binary32, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = convert_fp(src[i], binary64, binary32, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fo2ft](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §2 (convert_ff)。

<a id="insn-176"></a>

## 176. `fo2fo_orri_rf`

**用途**：按浮点合约执行 `fo2fo`，格式和寄存器字段以编码表为准。

**操作数形式**：`fo2fo rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44280000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = convert_fp(src[i], binary64, binary64, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = convert_fp(src[i], binary64, binary64, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fo2fo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §2 (convert_ff)。

<a id="insn-177"></a>

## 177. `foroot_orri_rf`

**用途**：按浮点合约执行 `foroot`，格式和寄存器字段以编码表为准。

**操作数形式**：`foroot rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44380000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
assert immu6 == 2
X = decode_fp(S.RF[hc], format=binary64)
assert not (is_negative_zero(X))  # SPECIFICATION-GAP otherwise
R, F = fp_sqrt(X, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. assert immu6 == 2
3. X = decode_fp(S.RF[hc], format=binary64)
4. assert not (is_negative_zero(X))  # SPECIFICATION-GAP otherwise
5. R, F = fp_sqrt(X, rounding=S.RF[0][33:32])
6. D.RF[hb] = encode_fp(R, format=binary64)
7. D.RF[0][4:0] = S.RF[0][4:0] | F
8. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
9. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: foroot](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §6 (root)。

<a id="insn-178"></a>

## 178. `ft2it_orri_rf`

**用途**：按浮点合约执行 `ft2it`，格式和寄存器字段以编码表为准。

**操作数形式**：`ft2it rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44C00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 32, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 32, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ft2it](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-179"></a>

## 179. `ft2io_orri_rf`

**用途**：按浮点合约执行 `ft2io`，格式和寄存器字段以编码表为准。

**操作数形式**：`ft2io rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44C40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 64, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 64, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ft2io](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-180"></a>

## 180. `ft2ut_orri_rf`

**用途**：按浮点合约执行 `ft2ut`，格式和寄存器字段以编码表为准。

**操作数形式**：`ft2ut rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44C80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 32, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 32, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ft2ut](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-181"></a>

## 181. `ft2uo_orri_rf`

**用途**：按浮点合约执行 `ft2uo`，格式和寄存器字段以编码表为准。

**操作数形式**：`ft2uo rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44CC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 64, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 64, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ft2uo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-182"></a>

## 182. `it2ft_orri_rf`

**用途**：按浮点合约执行 `it2ft`，格式和寄存器字段以编码表为准。

**操作数形式**：`it2ft rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44D00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 32, binary32, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 32, binary32, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: it2ft](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-183"></a>

## 183. `io2ft_orri_rf`

**用途**：按浮点合约执行 `io2ft`，格式和寄存器字段以编码表为准。

**操作数形式**：`io2ft rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44D40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 64, binary32, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 64, binary32, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: io2ft](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-184"></a>

## 184. `ut2ft_orri_rf`

**用途**：按浮点合约执行 `ut2ft`，格式和寄存器字段以编码表为准。

**操作数形式**：`ut2ft rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44D80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 32, binary32, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 32, binary32, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ut2ft](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-185"></a>

## 185. `uo2ft_orri_rf`

**用途**：按浮点合约执行 `uo2ft`，格式和寄存器字段以编码表为准。

**操作数形式**：`uo2ft rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44DC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 64, binary32, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 64, binary32, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: uo2ft](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-186"></a>

## 186. `fo2it_orri_rf`

**用途**：按浮点合约执行 `fo2it`，格式和寄存器字段以编码表为准。

**操作数形式**：`fo2it rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44E00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 32, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 32, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fo2it](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-187"></a>

## 187. `fo2io_orri_rf`

**用途**：按浮点合约执行 `fo2io`，格式和寄存器字段以编码表为准。

**操作数形式**：`fo2io rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44E40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 64, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], signed, 64, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fo2io](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-188"></a>

## 188. `fo2ut_orri_rf`

**用途**：按浮点合约执行 `fo2ut`，格式和寄存器字段以编码表为准。

**操作数形式**：`fo2ut rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44E80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 32, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 32, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fo2ut](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-189"></a>

## 189. `fo2uo_orri_rf`

**用途**：按浮点合约执行 `fo2uo`，格式和寄存器字段以编码表为准。

**操作数形式**：`fo2uo rdhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44EC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RF[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 64, rounding, saturate=True)
D.RD[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RF[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = fp_to_int(src[i], unsigned, 64, rounding, saturate=True)
7. D.RD[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fo2uo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §3 (convert_f2i)。

<a id="insn-190"></a>

## 190. `it2fo_orri_rf`

**用途**：按浮点合约执行 `it2fo`，格式和寄存器字段以编码表为准。

**操作数形式**：`it2fo rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44F00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 32, binary64, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 32, binary64, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: it2fo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-191"></a>

## 191. `io2fo_orri_rf`

**用途**：按浮点合约执行 `io2fo`，格式和寄存器字段以编码表为准。

**操作数形式**：`io2fo rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44F40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 64, binary64, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], signed, 64, binary64, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: io2fo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-192"></a>

## 192. `ut2fo_orri_rf`

**用途**：按浮点合约执行 `ut2fo`，格式和寄存器字段以编码表为准。

**操作数形式**：`ut2fo rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44F80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 32, binary64, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 32, binary64, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ut2fo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-193"></a>

## 193. `uo2fo_orri_rf`

**用途**：按浮点合约执行 `uo2fo`，格式和寄存器字段以编码表为准。

**操作数形式**：`uo2fo rfhb, rdhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44FC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rdhc` | `[11:6]` | rd字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
N = immu6
assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
src[i] = S.RD[hc + i] for i in range(N)
rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 64, binary64, rounding)
D.RF[hb:hb + N] = val[0:N]
D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. N = immu6
3. assert 1 <= N <= 63 and hb + N <= 64 and hc + N <= 64
4. src[i] = S.RD[hc + i] for i in range(N)
5. rounding = {0: RNE, 1: RTZ, 2: RDN, 3: RUP}[S.RF[0][33:32]]
6. for i in range(N): val[i], flg[i] = int_to_fp(src[i], unsigned, 64, binary64, rounding)
7. D.RF[hb:hb + N] = val[0:N]
8. D.RF[0][4:0] = S.RF[0][4:0] | or_flags(flg)
9. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
10. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: uo2fo](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §4 (convert_i2f)。

<a id="insn-194"></a>

## 194. `ftrnd_orri_rf`

**用途**：按 one-hot selector 指定的方向把浮点值取整，结果仍为同格式浮点。

**操作数形式**：`ftrnd rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfhb` 是目的，`rfhc` 是源，`immu6` 是 one-hot 取整 selector（0x01…0x20），不是寄存器个数。

**编码**：mask=`0xFFFC0000`，value=`0x440C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
assert immu6 in {0x01, 0x02, 0x04, 0x08, 0x10, 0x20}
R, F = round_to_integral(A, selector=immu6, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. assert immu6 in {0x01, 0x02, 0x04, 0x08, 0x10, 0x20}
4. R, F = round_to_integral(A, selector=immu6, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0、`immu6` 非 one-hot（含0x00）均为ILLI；仅 0x20 读取 rf0 方向且仅当结果≠输入时置 NX。

**算例**：源 1.5：0x01/0x02/0x08 得 2.0，0x04/0x10 得 1.0；0x20 按 rf0 方向并可置 NX；trunc(−0.5) 得 −0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftrnd](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §18 (roundint)。

<a id="insn-195"></a>

## 195. `fornd_orri_rf`

**用途**：按 one-hot selector 指定的方向把浮点值取整，结果仍为同格式浮点。

**操作数形式**：`fornd rfhb, rfhc, immu6`（orri；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfhb` 是目的，`rfhc` 是源，`immu6` 是 one-hot 取整 selector（0x01…0x20），不是寄存器个数。

**编码**：mask=`0xFFFC0000`，value=`0x442C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `immu6` | `[5:0]` | 无符号立即数 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
assert immu6 in {0x01, 0x02, 0x04, 0x08, 0x10, 0x20}
R, F = round_to_integral(A, selector=immu6, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. assert immu6 in {0x01, 0x02, 0x04, 0x08, 0x10, 0x20}
4. R, F = round_to_integral(A, selector=immu6, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0、`immu6` 非 one-hot（含0x00）均为ILLI；仅 0x20 读取 rf0 方向且仅当结果≠输入时置 NX。

**算例**：源 1.5：0x01/0x02/0x08 得 2.0，0x04/0x10 得 1.0；0x20 按 rf0 方向并可置 NX；trunc(−0.5) 得 −0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fornd](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §18 (roundint)。

<a id="insn-196"></a>

## 196. `ftadd_orrr_rf`

**用途**：按浮点合约执行 `ftadd`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftadd rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44400000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
(R, F) = fp_add(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. (R, F) = fp_add(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftadd](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-197"></a>

## 197. `ftsub_orrr_rf`

**用途**：按浮点合约执行 `ftsub`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftsub rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44440000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
(R, F) = fp_sub(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. (R, F) = fp_sub(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftsub](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-198"></a>

## 198. `ftmul_orrr_rf`

**用途**：按浮点合约执行 `ftmul`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftmul rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44480000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
(R, F) = fp_mul(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. (R, F) = fp_mul(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftmul](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-199"></a>

## 199. `ftdiv_orrr_rf`

**用途**：按浮点合约执行 `ftdiv`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftdiv rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x444C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
(R, F) = fp_div(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. (R, F) = fp_div(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftdiv](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-200"></a>

## 200. `ftrem_orrr_rf`

**用途**：按浮点合约执行 `ftrem`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftrem rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44500000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
(R, F) = fp_remainder(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. (R, F) = fp_remainder(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftrem](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-201"></a>

## 201. `ftsclb_orrr_rf`

**用途**：按浮点合约执行 `ftsclb`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftsclb rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44540000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
(R, F) = fp_scaleB(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. (R, F) = fp_scaleB(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftsclb](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-202"></a>

## 202. `ftsgnn_orrr_rf`

**用途**：按浮点合约执行 `ftsgnn`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftsgnn rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44580000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RF[hc] & ((1 << 32) - 1)
s = 1 ^ sign(S.RF[hd])
D.RF[hb] = (A & ((1 << (32 - 1)) - 1)) | (s << 31)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = S.RF[hc] & ((1 << 32) - 1)
3. s = 1 ^ sign(S.RF[hd])
4. D.RF[hb] = (A & ((1 << (32 - 1)) - 1)) | (s << 31)
5. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
6. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftsgnn](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §7 (sign)。

<a id="insn-203"></a>

## 203. `ftsgnj_orrr_rf`

**用途**：按浮点合约执行 `ftsgnj`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftsgnj rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x445C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RF[hc] & ((1 << 32) - 1)
s = sign(S.RF[hd])
D.RF[hb] = (A & ((1 << (32 - 1)) - 1)) | (s << 31)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = S.RF[hc] & ((1 << 32) - 1)
3. s = sign(S.RF[hd])
4. D.RF[hb] = (A & ((1 << (32 - 1)) - 1)) | (s << 31)
5. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
6. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftsgnj](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §7 (sign)。

<a id="insn-204"></a>

## 204. `foadd_orrr_rf`

**用途**：按浮点合约执行 `foadd`，格式和寄存器字段以编码表为准。

**操作数形式**：`foadd rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44600000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
(R, F) = fp_add(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. (R, F) = fp_add(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: foadd](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-205"></a>

## 205. `fosub_orrr_rf`

**用途**：按浮点合约执行 `fosub`，格式和寄存器字段以编码表为准。

**操作数形式**：`fosub rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44640000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
(R, F) = fp_sub(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. (R, F) = fp_sub(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fosub](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-206"></a>

## 206. `fomul_orrr_rf`

**用途**：按浮点合约执行 `fomul`，格式和寄存器字段以编码表为准。

**操作数形式**：`fomul rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44680000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
(R, F) = fp_mul(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. (R, F) = fp_mul(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fomul](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-207"></a>

## 207. `fodiv_orrr_rf`

**用途**：按浮点合约执行 `fodiv`，格式和寄存器字段以编码表为准。

**操作数形式**：`fodiv rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x446C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
(R, F) = fp_div(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. (R, F) = fp_div(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fodiv](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-208"></a>

## 208. `forem_orrr_rf`

**用途**：按浮点合约执行 `forem`，格式和寄存器字段以编码表为准。

**操作数形式**：`forem rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44700000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
(R, F) = fp_remainder(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. (R, F) = fp_remainder(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: forem](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-209"></a>

## 209. `fosclb_orrr_rf`

**用途**：按浮点合约执行 `fosclb`，格式和寄存器字段以编码表为准。

**操作数形式**：`fosclb rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44740000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
(R, F) = fp_scaleB(A, B, rounding=S.RF[0][33:32])
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. (R, F) = fp_scaleB(A, B, rounding=S.RF[0][33:32])
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fosclb](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §5 (arith)。

<a id="insn-210"></a>

## 210. `fosgnn_orrr_rf`

**用途**：按浮点合约执行 `fosgnn`，格式和寄存器字段以编码表为准。

**操作数形式**：`fosgnn rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44780000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RF[hc] & ((1 << 64) - 1)
s = 1 ^ sign(S.RF[hd])
D.RF[hb] = (A & ((1 << (64 - 1)) - 1)) | (s << 63)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = S.RF[hc] & ((1 << 64) - 1)
3. s = 1 ^ sign(S.RF[hd])
4. D.RF[hb] = (A & ((1 << (64 - 1)) - 1)) | (s << 63)
5. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
6. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fosgnn](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §7 (sign)。

<a id="insn-211"></a>

## 211. `fosgnj_orrr_rf`

**用途**：按浮点合约执行 `fosgnj`，格式和寄存器字段以编码表为准。

**操作数形式**：`fosgnj rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x447C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = S.RF[hc] & ((1 << 64) - 1)
s = sign(S.RF[hd])
D.RF[hb] = (A & ((1 << (64 - 1)) - 1)) | (s << 63)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = S.RF[hc] & ((1 << 64) - 1)
3. s = sign(S.RF[hd])
4. D.RF[hb] = (A & ((1 << (64 - 1)) - 1)) | (s << 63)
5. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
6. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fosgnj](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §7 (sign)。

<a id="insn-212"></a>

## 212. `ftqcmp_orrr_rf`

**用途**：按浮点合约执行 `ftqcmp`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftqcmp rdhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44800000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
R = positive_qnan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
D.RD[hb] = R & ((1 << 64) - 1)
D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. R = positive_qnan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
5. D.RD[hb] = R & ((1 << 64) - 1)
6. D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftqcmp](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §8 (compare)。

<a id="insn-213"></a>

## 213. `ftscmp_orrr_rf`

**用途**：按浮点合约执行 `ftscmp`，格式和寄存器字段以编码表为准。

**操作数形式**：`ftscmp rdhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44840000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
R = positive_snan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
D.RD[hb] = R & ((1 << 64) - 1)
D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. R = positive_snan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
5. D.RD[hb] = R & ((1 << 64) - 1)
6. D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftscmp](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §8 (compare)。

<a id="insn-214"></a>

## 214. `foqcmp_orrr_rf`

**用途**：按浮点合约执行 `foqcmp`，格式和寄存器字段以编码表为准。

**操作数形式**：`foqcmp rdhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44A00000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
R = positive_qnan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
D.RD[hb] = R & ((1 << 64) - 1)
D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. R = positive_qnan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
5. D.RD[hb] = R & ((1 << 64) - 1)
6. D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: foqcmp](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §8 (compare)。

<a id="insn-215"></a>

## 215. `foscmp_orrr_rf`

**用途**：按浮点合约执行 `foscmp`，格式和寄存器字段以编码表为准。

**操作数形式**：`foscmp rdhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：源操作数均取执行前的RF/RD值；连续形式的 `immu6` 表示元素个数，root 形式表示 n。

**编码**：mask=`0xFFFC0000`，value=`0x44A40000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rdhb` | `[17:12]` | rd字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
R = positive_snan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
D.RD[hb] = R & ((1 << 64) - 1)
D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. R = positive_snan if (is_nan(A) or is_nan(B)) else (-1 if A < B else (0 if A == B else 1))
5. D.RD[hb] = R & ((1 << 64) - 1)
6. D.RF[0][4:0] = S.RF[0][4:0] | (NV if has_signaling_nan(A, B) else 0)
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0或rd0、连续范围越界/为空、convert_ff范围重叠、root的n不为2均为ILLI；开放语义按文档标为SPECIFICATION-GAP。

**算例**：例如把所有源寄存器先读入临时值，再按本条格式写回目的寄存器，并把浮点异常标志累积到rf0。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: foscmp](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §8 (compare)。

<a id="insn-216"></a>

## 216. `ftmin_orrr_rf`

**用途**：按 IEEE 754-2019 minimumNumber/maximumNumber 选取较小/较大值。

**操作数形式**：`ftmin rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfhb` 是目的，`rfhc`/`rfhd` 是两个同格式源；先读后写，源与目的可重叠。

**编码**：mask=`0xFFFC0000`，value=`0x44980000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
R, F = fp_minimumNumber(A, B)
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. R, F = fp_minimumNumber(A, B)
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0为ILLI；单 NaN 返回那个数、双 NaN 返回 canonical qNaN、sNaN 置 NV；±0 按 −0<+0 比较。

**算例**：min(+0,−0)=−0、max(+0,−0)=+0；min(1.0,qNaN)=1.0；双 NaN 返回规范 qNaN。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftmin](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §19 (minmax)。

<a id="insn-217"></a>

## 217. `ftmax_orrr_rf`

**用途**：按 IEEE 754-2019 minimumNumber/maximumNumber 选取较小/较大值。

**操作数形式**：`ftmax rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfhb` 是目的，`rfhc`/`rfhd` 是两个同格式源；先读后写，源与目的可重叠。

**编码**：mask=`0xFFFC0000`，value=`0x449C0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary32)
B = decode_fp(S.RF[hd], format=binary32)
R, F = fp_maximumNumber(A, B)
D.RF[hb] = encode_fp(R, format=binary32)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary32)
3. B = decode_fp(S.RF[hd], format=binary32)
4. R, F = fp_maximumNumber(A, B)
5. D.RF[hb] = encode_fp(R, format=binary32)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0为ILLI；单 NaN 返回那个数、双 NaN 返回 canonical qNaN、sNaN 置 NV；±0 按 −0<+0 比较。

**算例**：min(+0,−0)=−0、max(+0,−0)=+0；min(1.0,qNaN)=1.0；双 NaN 返回规范 qNaN。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: ftmax](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §19 (minmax)。

<a id="insn-218"></a>

## 218. `fomin_orrr_rf`

**用途**：按 IEEE 754-2019 minimumNumber/maximumNumber 选取较小/较大值。

**操作数形式**：`fomin rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfhb` 是目的，`rfhc`/`rfhd` 是两个同格式源；先读后写，源与目的可重叠。

**编码**：mask=`0xFFFC0000`，value=`0x44B80000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
R, F = fp_minimumNumber(A, B)
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. R, F = fp_minimumNumber(A, B)
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0为ILLI；单 NaN 返回那个数、双 NaN 返回 canonical qNaN、sNaN 置 NV；±0 按 −0<+0 比较。

**算例**：min(+0,−0)=−0、max(+0,−0)=+0；min(1.0,qNaN)=1.0；双 NaN 返回规范 qNaN。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fomin](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §19 (minmax)。

<a id="insn-219"></a>

## 219. `fomax_orrr_rf`

**用途**：按 IEEE 754-2019 minimumNumber/maximumNumber 选取较小/较大值。

**操作数形式**：`fomax rfhb, rfhc, rfhd`（orrr；表内scope=fp）。字段名用于说明操作数位置，实际汇编须换成具体寄存器/立即数。

**输入与目的**：`rfhb` 是目的，`rfhc`/`rfhd` 是两个同格式源；先读后写，源与目的可重叠。

**编码**：mask=`0xFFFC0000`，value=`0x44BC0000`。

| 字段 | 指令字位域 | 含义 |
| --- | --- | --- |
| `rfhb` | `[17:12]` | rf字段 |
| `rfhc` | `[11:6]` | rf字段 |
| `rfhd` | `[5:0]` | rf字段 |

**伪代码（唯一执行顺序）**（函数与记号见共同规则 §10）：

```text
S = snapshot(state)
A = decode_fp(S.RF[hc], format=binary64)
B = decode_fp(S.RF[hd], format=binary64)
R, F = fp_maximumNumber(A, B)
D.RF[hb] = encode_fp(R, format=binary64)
D.RF[0][4:0] = S.RF[0][4:0] | F
D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
commit(D)
```

**标准计算与写回**：

1. S = snapshot(state)
2. A = decode_fp(S.RF[hc], format=binary64)
3. B = decode_fp(S.RF[hd], format=binary64)
4. R, F = fp_maximumNumber(A, B)
5. D.RF[hb] = encode_fp(R, format=binary64)
6. D.RF[0][4:0] = S.RF[0][4:0] | F
7. D.RB[0] = (S.RB[0] + 4) & ((1 << 64) - 1)
8. commit(D)

**合法性、异常与边界**：目的rf0为ILLI；单 NaN 返回那个数、双 NaN 返回 canonical qNaN、sNaN 置 NV；±0 按 −0<+0 比较。

**算例**：min(+0,−0)=−0、max(+0,−0)=+0；min(1.0,qNaN)=1.0；双 NaN 返回规范 qNaN。 算例中未特别指定的目的均选择合法非零寄存器。

**依据**：[SimRISC-07: fomax](../../spec/SimRISC-07-浮点运算.md)；[指令合约](../../.tao/contracts/contract-isa.md)；[浮点合约](../../.tao/contracts/contract-fp.md) contract-fp §19 (minmax)。

## 范围外指令身份清单

以下身份有定义，但本次没有为它们建立执行golden；调用当前解释器应得到 `Unsupported`。这不是它们在完整DADAO机器上的语义，也不将“机器暂定decode ILLI”混同为模型已经实现。

| 指令身份 | scope | 本次状态 |
| --- | --- | --- |
| `clmul.o_rrrr_rd` | m9 | 暂不支持 |
| `cfx2rd_crrr_cfx` | m1 | 暂不支持 |
| `cfx2rc_crrr_cfx` | m1 | 暂不支持 |
| `cfxld_crii_cfx` | excluded | 暂不支持 |
| `cfxst_crii_cfx` | excluded | 暂不支持 |
| `escape_ciii_cfx` | m1 | 暂不支持 |
| `trap_ciii_cfx` | m1 | 暂不支持 |
| `fence_oiii_imm` | m9 | 暂不支持 |
| `lr.o.nn_orrr_rd` | m9 | 暂不支持 |
| `lr.t.nn_orrr_rd` | m9 | 暂不支持 |
| `lr.w.nn_orrr_rd` | m9 | 暂不支持 |
| `lr.b.nn_orrr_rd` | m9 | 暂不支持 |
| `lr.o.an_orrr_rd` | m9 | 暂不支持 |
| `lr.t.an_orrr_rd` | m9 | 暂不支持 |
| `lr.w.an_orrr_rd` | m9 | 暂不支持 |
| `lr.b.an_orrr_rd` | m9 | 暂不支持 |
| `lr.o.ar_orrr_rd` | m9 | 暂不支持 |
| `lr.t.ar_orrr_rd` | m9 | 暂不支持 |
| `lr.w.ar_orrr_rd` | m9 | 暂不支持 |
| `lr.b.ar_orrr_rd` | m9 | 暂不支持 |
| `sc.o.nn_orrr_rd` | m9 | 暂不支持 |
| `sc.t.nn_orrr_rd` | m9 | 暂不支持 |
| `sc.w.nn_orrr_rd` | m9 | 暂不支持 |
| `sc.b.nn_orrr_rd` | m9 | 暂不支持 |
| `sc.o.nr_orrr_rd` | m9 | 暂不支持 |
| `sc.t.nr_orrr_rd` | m9 | 暂不支持 |
| `sc.w.nr_orrr_rd` | m9 | 暂不支持 |
| `sc.b.nr_orrr_rd` | m9 | 暂不支持 |
| `sc.o.ar_orrr_rd` | m9 | 暂不支持 |
| `sc.t.ar_orrr_rd` | m9 | 暂不支持 |
| `sc.w.ar_orrr_rd` | m9 | 暂不支持 |
| `sc.b.ar_orrr_rd` | m9 | 暂不支持 |
| `ctpop_orri_rd` | m8 | 暂不支持 |
| `ctlz_orri_rd` | m8 | 暂不支持 |
| `cttz_orri_rd` | m8 | 暂不支持 |
| `rol.o_orrr_rd` | m9 | 暂不支持 |
| `rol.o_orri_rd` | m9 | 暂不支持 |
| `rev.o_orri_rd` | m8 | 暂不支持 |
| `rol.t_orrr_rd` | m9 | 暂不支持 |
| `rol.t_orri_rd` | m9 | 暂不支持 |
| `rev.t_orri_rd` | m8 | 暂不支持 |
| `rol.w_orrr_rd` | m9 | 暂不支持 |
| `rol.w_orri_rd` | m9 | 暂不支持 |
| `rev.w_orri_rd` | m8 | 暂不支持 |
| `rol.b_orrr_rd` | m9 | 暂不支持 |
| `rol.b_orri_rd` | m9 | 暂不支持 |
| `rev.b_orri_rd` | m8 | 暂不支持 |

## 规范口径与验证边界

这一节说明当前golden在哪些地方可以提供参考答案，哪些地方仍然需要规范裁定、数据修正或额外验证。阅读前面的逐条说明时，也必须保留这些限制：**一条指令有了详细文字定义，不等于它的所有输入已经验证，更不等于完整DADAO系统已经通过验收。**

这里把问题分开记录，是因为它们的解决方式不同。规范歧义需要先确定正确行为；旧向量需要按已确定的规范修正；模型范围外的能力需要另行实现；环境缺失则需要补齐工具后重新执行检查。不能把这些情况统一写成“测试暂时没过”，也不能统一改成SKIP来消除失败。

### 1. sub.uo：借位高半已裁定为 0/1

`sub.uo {rdHA, rdHB}, rdHC, rdHD` 的语义已由 `ADR-0049` 冻结：

- `rdHB = (rdHC − rdHD) mod 2^64`
- `rdHA = 1` 当且仅当 `rdHC < rdHD`，否则 `0`
- 不写 128 位结果的全 1 高半；需要 128 位有符号高半时用 `sub.so`

原先 `SimRISC-04` 总述句的“高 64 位”与 `.uo` 变体句的“借位 0/1”冲突，已按变体句修正。QEMU 原本已按借位实现；向量生成器/审计与 golden 已对齐，并新增 `0−1`、`5−7` 借位向量。

### 2. 仓库存数向量已按现行零号源规则同步

合并远端 `origin/master` 后，原先把 `rd0/rb0` 存数源判为 ILLI 的 10 条旧向量已按现行规则更新：从 `rd0` 存入 0、从 `rb0` 存入执行前控制流值均合法。本次全量回放 710 条，FAIL=0、退出码 0，这组分歧不再存在。

若后续重新引入同类旧数据，应依据规范重写预期内存内容、源寄存器保持和 PC 推进等断言；不能把模型改回“零号源非法”，也不能无条件跳过。

### 3. 已有验证证据分别能证明什么

以下是本次实现审查的记录，不是每次生成文档都会重新运行的测试结果。后续代码、规范或向量有变化时，应重新执行对应检查，不能一直引用旧数字作为最新结论。

| 证据 | 本次记录 | 可以支持的结论 | 不能由此推出的结论 |
| --- | --- | --- | --- |
| 模型和验证器直接测试 | 46项测试通过 | 已编写的正常、边界及错误检测用例满足断言 | 所有机器字和操作数组合都正确 |
| 独立算术与移位矩阵 | 3402组算术、360组移位检查 | 所选位宽、符号和边界组合与独立计算一致 | 这些组合已经穷尽全部64位输入 |
| 仓库输入逐条独立重算 | 159条适用算术/比较输入、84条移位/扩展输入 | 本次选定类别中全部适用输入都已重算，而非只抽样 | 其他指令族也完成了相同方式的全量重算 |
| 仓库向量回放 | 710条：171条编码通过、490条执行通过、0条失败、49条跳过；退出码0 | 当前仓库向量与模型一致 | 全量回归已经通过 |
| 反例注入 | 修改计算或断言后失败，恢复后通过 | 检查器至少能检出这些实际注入的错误 | 检查器能检出任何可能的错误 |
| 文档范围和生成一致性检查 | 指令身份、链接及生成内容核对通过 | 文档条目与当前清单对齐，生成结果可复现 | 文档中的每一个语义判断都已被机械证明 |

完整审查记录和限制见 [本次任务书](../../.tao/tasks/golden/GOLDEN-001t-M1模型校正与设计说明.md)。可复现命令见 [README](README.md)。这里的“独立重算”是指期望值依据规范、使用独立计算推导，不从LLVM或QEMU的执行结果取答案。

#### 编码通过不能替代执行通过

`PASS-encoding` 检查机器字是否解码成向量声明的指令，以及静态操作数是否合法。它没有执行运算，因此不能证明乘法结果、加载的数据、返回地址栈变化或分支目标正确。汇报时应把171条编码检查与490条执行检查分开说明，不能把两者合并称为“661条语义全部正确”。

`PASS-execution` 也只证明本条向量实际断言的内容成立。例如，成功用例只检查rd1，就不能据此声称所有其他寄存器均未误改。当前异常用例会额外检查整份状态不变，swym的无副作用用例也有整体状态检查；这不等于每一个成功用例都穷尽了全部副作用。

#### 独立性也有具体边界

模型和测试的语义期望不依赖LLVM/QEMU，但编码身份和字段位置都使用仓库的 `contracts/opcodes.yaml`。如果这张共享编码表自身写错，模型和向量可能同时使用同一个错误编码并彼此一致。要独立证明编码正确，还需要把表中编码与规范正文的QFC/子表逐项核对，不能只依靠模型与向量相互比对。

同样，生成器的 `--check` 只是重新生成文字后比对文件。即使生成器中的某段解释本身有误，只要产物与它相同，一致性检查仍会通过。因此，文字语义还需要对照规范审查；本文件不能成为自己正确性的唯一证据。

### 4. 跳过的用例没有得到执行正确性的证明

本次回放中的49条跳过包括5条已标deferred的用例和44条机器层异常用例。它们没有计入执行通过数，也不能在汇报时视为“没有问题”。本次回放没有 FP 向量；FP 由 `test_fp_v5.py` 的专项测试覆盖，另有逐身份 66 条冒烟检查，整套单测共 46 项。

- **SKIP-deferred**：向量已明确暂缓，通常意味着其期望或验证前提尚未确定。本模型本次没有对它作出通过结论；后续需解决具体暂缓原因，再转为可执行的有效断言。
- **SKIP-machine**：用例期待UNMAPPED、CFXMEM等地址映射或权限结果，而当前单步模型没有这些机器机制。需要在具备相应地址图、权限配置和异常机制的环境中验证。
- **SKIP-scope**：被测指令在本模型实现范围外。当前 710 条 ISA 回放中这个计数为 0；特权、原子和 fence 仍在范围外，只说明本组向量没有相应项目。

即使一批测试的失败数为0，只要仍有跳过项，也应同时给出原因和范围。当前运行器对空输入或全部用例都跳过的情况返回非零，防止“什么都没有验证”被当成成功。

### 5. 当前模型明确不验证的能力

浮点 66 条 RF 指令现在纳入本模型范围；其有限值运算使用独立整数/有理数 oracle，舍入模式和累积标志按浮点合约处理。`rootn(-0,2)`、浮点转整数精度损失的NX，以及 remainder/scaleB的合约开放边界仍报告 `SPECIFICATION-GAP`，不能据此宣称所有输入都已裁定或完整符合 IEEE 754-2019。后来新增的特权指令、trap/escape、原子指令和fence仍在范围外。

内存模型只提供指令所需的字节读写、端序、地址截取和对齐检查，没有完整系统的页表、权限、地址映射、ROM或设备行为。模型中某个地址可以读写，不代表真实机器在该地址也一定可访问；未预置内存读0同样只是测试模型约定。

模型也不提供周期、流水线、缓存一致性或多核并发内存序的答案。`swym` 在架构状态上不改数据，并不表示已经验证其真实等待周期；未实现fence，也不能用顺序执行的单步结果证明屏障语义正确。

返回栈方面，本模型检查RACNT、递归计数、MemRAS指针与对齐等已覆盖行为，但不判断OS实际分配了多少MemRAS空间。有效区以外的RA槽位内容由规范视为未定义，测试也不能把当前Python实现恰好留下的值固化成硬件必须遵守的结果。

### 6. 当前已知不足与 L2 状态

**f2i 尚未收口。** `convert_to_int` 对任何 inexact 输入直接抛 `FPGap`（如 `1.5 → int` 没有答案），但规范只把 NX 列为未定，整数值本身可确定；舍入方向（golden 用 `rf0`，QEMU softfloat 对 f2i 用 toward-zero）以及 NaN/Inf/负无符号的饱和值也没有可机械判的口径，且缺少对应测试。

**FP 没有共享向量。** `tests/vectors` 目前只有标量；66 条 FP 由单测、逐身份冒烟和一次性 oracle 差分覆盖，差分脚本尚未入库。

**golden 未接入 make/CI。** 单测、710 条回放和本文件 `--check` 目前靠手工执行；没有 `check-golden` 目标，回归不会被项目门控自动拦住。`009t-audit.py` 对 `ctrl-br`、`ldm.o`、`shl.*` 仍有既存偏差（与本次 B 方案无关）。

**L2 尚未跑通。** 依赖已安装、组件已拉取并打补丁，LLVM/LLD/QEMU 正在构建；L2 的 `check-lit`、`check-qemu-smoke` 和 FP 探针需要完整工具链。构建完成后运行 `make check-modules JOBS=2` 并保留真实输出；在跑通前不能写“L2 通过”。

### 7. 伪指令、旧指令和范围变化应怎样理解

本文件以**当前编码表里的机器指令身份**为单位。`set.rd`等汇编伪指令可能展开成多条机器指令，因此这里不会再给它们建立一个独立的单步机器语义。验证伪指令时，需要另外检查汇编展开序列及整个序列的效果，不能只查看其中一条机器指令。

旧版本中的rela.si、专门的illi指令等，也不能按旧名字继续套用旧行为。对实际机器字，应先查当前编码表：若当前已分配给另一身份，就按新身份执行；只有未定义的编码才报UNDI。这里“illi指令已删除”也不表示ILLI异常被删除，非法操作数仍可能触发ILLI。

当前仓库的 `scope: m1` 标签还包含后来加入的特权能力，而本次用户确认的是原有标量范围。因此，文档详细条目数、编码表m1数量和完整项目已实现数量不必相同；汇报覆盖范围时应列明采用的是哪一份清单。

### 8. 当前结论与下一步应如何表述

本模型已按当前规范校正确认范围内的整数、访存、寄存器传送、控制流和 66 条 FP，并通过直接测试、独立重算及反例检查；仍保留 f2i 等开放语义、FP 共享向量缺口、golden 未入门控和系统能力边界。

要进一步完成验收，需要分别推进：

1. （已完成）`sub.uo` 借位高半已由 ADR-0049 裁定为 0/1，并同步规范、合约、golden 与向量。
2. （已完成）十条旧存数向量已随远端合并按现行零号源规则更新；回放 710 条、FAIL=0。
3. 裁定 f2i 的舍入/饱和/NX 口径并补向量；把 FP oracle 差分和 `check-golden` 纳入仓库门控。
4. （进行中）项目工具环境已配置，LLVM/LLD/QEMU 构建中；完成后运行 L2 并更新验收记录。

这些后续动作有不同的授权范围。本文把它们列为待办说明，不意味着已经修改共享规范、测试数据、ADR或系统环境；也不以文字补充代替实际执行证据。
