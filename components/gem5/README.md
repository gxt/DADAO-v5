# gem5 组件（gem5）

DADAO 的 gem5 功能参考（M11）。上游基线与补丁序列由
`manifests/components.lock.toml` 锁定；工作树由 `make fetch` +
`make apply-series` 在 `.work/source/gem5` 建立。

## 当前状态（GEM5-004t / B0 + GEM5-005t + GEM5-006t / B1 + GEM5-007t / B2 + GEM5-008t / B3 + GEM5-009t / B4 + GEM5-010t / B5 + GEM5-011t / B6 + GEM5-012t / B7）

- **解码核心**：`src/arch/dadao/**` 骨架 + 契约驱动的解码表
  （格式/字段/opcode/6 位子表分派/助记符/非法与保留编码；
  `rule_refs` + `legality` 表达式作为执行批次的合法性数据）。
- **B1 执行语义**（`exec/b1.{hh,cc}`，38 条取数存数）：RD/RB/RA/RF 的
  单/多 load/store，纯 C++（不依赖 gem5 头），由 `inst.cc` 的
  `Gem5B1Context` 适配寄存器组/内存；ILLI → `IllegalInstruction`、
  MALIGN → `MalignInstruction`（先 panic 报地址/宽度，B6 接 trap 向量）、
  内存 fault 原样返回。大端字节序与 48 位地址回绕在核内完成。
- **B2 执行语义**（`exec/b2.{hh,cc}`，8 条 rwii 立即数）：`or.w`/`andn.w`/
  `set.zw`/`set.ow` 的 RD/RB 变体与 `set.w` RF 变体，按 `entry->id` 分派
  （同名助记符 RD/RB 不混淆）；`wpN` 选择 wyde、`immu16` 无符号分片拼接、
  其余 48 位按各指令清 0/置 1/保持；RD/RB 目的 0 ⇒ ILLI（先于寄存器访问），
  `set.w rf0` 合法且按 FCSR 写掩码（`wp2`→`[33:32]`、`wp0`→`[4:0]`、
  `wp1`/`wp3` 写无效）。共享接口（`Fault`/`Bank`/`Target`/`RegAccess`/
  `fieldValue`）上移到 `exec/common.hh`，B1 语义不变。
- **B3 执行语义**（`exec/b3.{hh,cc}`，42 条 64 位运算/地址运算）：128 位
  加减乘与无进位乘（`rrrr` 双目的高低半 + 进位/借位）、18/12 位立即数算术与
  比较、位扫描/位计数（有效位上界 `hd`）、64 位逻辑与移位/循环移位、符号/零
  扩展、逐块反转、除余定值语义（除零/`INT_MIN÷−1`）与 RB 加减/比较、`aip.si`
  IP 相对寻址；按 `entry->id` 分派，静态 ILLI 先于任何寄存器读。
- **B4 执行语义**（`exec/b4.{hh,cc}`，63 条 32/16/8 位运算 +
  `rev.t/w/b`）：源先按宽度截断再运算，结果写满 64 位（`u` 零扩展、
  `s` 符号扩展），`cmp` 的 −1 为 64 位全 1；除零/`INT_MIN÷−1` 定值；
  `orrr` 移位量取 `rdhd` 低位（天然 mod W），`orri` 的 `immu6 ≥ W`
  ⇒ ILLI；`rev.t/w/b` 每块内按 one-hot `k` 反转单元顺序（`k ≥ S` ⇒ ILLI）。
  按 `entry->id` 分派，静态 ILLI 先于任何寄存器读；无访存路径。
- **B5 执行语义**（`exec/b5.{hh,cc}`，28 条块搬移/条件赋值/控制流/RAS）：
  8 条寄存器块搬移（RD/RB/RA/RF 组间与组内，64 位二进制不变；`immu6=0`/
  越界/目的 0/同组重叠 ⇒ ILLI，`rf0` 目的按 FCSR 写掩码、`ra0` 按不透明
  64 位传输）；5 条条件赋值（`cs.n/z/p` 写 `rdhb`、`cs.eq/ne` 写 `rdhc`，
  先读全部源再写、条件不成立写回原值）；10 条条件跳转 + 2 条 `jump` +
  2 条 `call` + `ret`，地址按 64 位全宽计算（`rb0 + (sext(imm)<<2)`，
  `rrii` 为 `rbha + rdhb + (sext(imms12)<<2)`），48 位截断交地址空间；
  RegRAS/MemRAS 状态机 C1/C2/C3a/C3b 与 D1/D2/D3/D4a/D4b（`RACNT`/
  `MRPTR`、递归折叠、MemRAS 大端换出/读回、RASOF/RASUF 与访存异常精确）。
- **B6 执行语义**（`exec/b6.{hh,cc}`，30 条系统/原子/屏障）：
  `swym`（no-op + `swymHint` 时延提示，`immu18` 非功能操作数）；`trap`/
  `escape`/`cfx2rd`/`cfx2rc`（cfxha 保留 6–14/19–61 ⇒ ILLI；`escape`
  `imms18[17:1] != 0` ⇒ ILLI、字节偏移仅 0/4；`cfx2rd/cfx2rc` 未建模组合 ⇒
  CFXREG、`trap` 控制转移 `trapTo`、帧错误 ⇒ CFXESC；`cfx2rd` 目的 `rd0`
  丢弃写不 ILLI）；`fence`（`immu18[17:12]` SBZ、`pred/succ` 六位掩码、
  `cfxha=0` = all cfx、`pred=succ=0` 合法 no-op，`ordering()` 为平台接入点）；
  `lr.*`/`sc.*` 各 12 条（宽度 8/4/2/1 × 存储序 nn/an|nr/ar，按 `entry->id`
  分派；`lr` 零扩展大端读并置保留、`sc` 精确地址+宽度匹配后条件写并置
  `rdHB=0/1`，无论成败清本 hart 保留；`lr` 的 `hb != rd0` ⇒ ILLI、`sc` 的
  `rdHB = rd0` ⇒ ILLI；非 `.b` 未对齐 ⇒ MALIGN；MALIGN/访存 fault 精确、
  不消费保留）。保留标记由每线程 `ISA` 单槽持有（精确地址 + 宽度，F8.1），
  `clear()` 复位、不做检查点序列化。
- **B7 执行语义**（`exec/b7.{hh,cc}` + `exec/fp_soft.{hh,cc}`，55 条浮点）：
  12 族 = fma 2 / cs_rf 3 / classify 2 / convert_ff 4 / root 2 / convert_f2i 8 /
  convert_i2f 8 / roundint 2 / arith 12（add/sub/mul/div/rem/sclb）/ sign 4 /
  compare 4 / minmax 4，按 `entry->id` 分派（`ft*`/`fo*`、`2it`/`2ut`、
  `qcmp`/`scmp`、`sgnn`/`sgnj` 只差表项）。值语义在 `exec/fp_soft.cc`：
  **纯整数、位精确**的 IEEE 754-2019（`unsigned __int128` 精确积/127 位窗口
  对齐/长除法/整数开方），**不使用**宿主 `float`/`double`、`<cmath>` 结果、
  `fesetround`/`fetestexcept` 或外部 softfloat 库；四种舍入（RNE/RTZ/RDN/RUP）
  共用单一 round-and-pack，UF 按 **舍入后** tininess 且仅 tiny+inexact 置位，
  fma 精确积只舍入一次，rem 用整数长除法（商最近、平局取偶、结果精确无标志）、
  scaleB 指数 `rdHD`（rd 组有符号 64 位，大 `n` 直接判 OF/UF，不迭代）、
  f2i 饱和 + NX/ NV、root 仅 n=2（整数 `isqrt` + 精确中点比较）、
  minmax 为 `minimumNumber`/`maximumNumber` 严格版（−0<+0、单 NaN 返回数、
  双 NaN canonical、sNaN⇒NV）。
  静态合法性（`dst_rf0`/`dst_rd0`/`mreg_zero`/`mreg_range_overflow`/
  `mreg_range_overlap`/`encode_onehot`/`encode_fp_root_n`）先于任何寄存器读；
  块形式按序号递增逐对先读后写；标志 sticky-OR 进 `rf0[4:0]`，无标志不写 `rf0`。
- **B7 模型选择**（spec 未规定处，**非 spec 断言**）：① `ft` 结果只写低 32 位、
  保留 `[63:32]`（与 B1 `ld.t` 一致）；② `rootn(-0,2) = -0`（spec 明示不作要求）；
  ③ compare 的 unordered 结果按 ft 为 `0x7FC0_0000`/`0x7F80_0001` **零扩展**到 64 位
  rd，fo 为 `0x7FF8_...`/`0x7FF0_..._0001`（符号位 0）；④ `ft2it`/`ft2ut` 等 32 位
  f2i 结果按 SimRISC 约定**符号/零扩展**到 64 位 rd（与 SimRISC-08 的 `.st`/`.ut`
  一致）；⑤ signaling compare 的 unordered 置 NV（用户 2026-11-02 裁定 3）。
- **B0–B7 全覆盖**：264 条全部有执行核；`inst.cc` 的 `batch<1 || batch>7`
  仅作防御分支（返回 `UnimplementedInstruction`），未匹配/保留编码仍返回
  `IllegalInstruction`（ILLI）。不做跨批混写。
- **断言**：264 行逐条解码断言（`decode-assertions.tsv`）+ 388 条非法/保留/
  身份回归用例（`decode-negative.tsv`），由 `make check-gem5-decode` 运行；
  B1 执行断言 `exec/b1_test.cc`（38/38）由 `tools/gem5/check_b1.py`、
  B2 执行断言 `exec/b2_test.cc`（8/8、逐 wyde/立即数分片/FCSR 掩码/ILLI）
  由 `tools/gem5/check_b2.py`、B3 执行断言 `exec/b3_test.cc`（42/42、128 位
  高低半/立即数边界/one-hot/循环移位/有符号无符号比较/除余定值/64 位写满）
  由 `tools/gem5/check_b3.py`、B4 执行断言 `exec/b4_test.cc`（63/63、non-B4
  201/201、窄位宽截断/扩展/舍入/比较/移位/rev/ILLI）由 `tools/gem5/check_b4.py`、
  B5 执行断言 `exec/b5_test.cc`（28/28、non-B5 236/236、块搬移范围/重叠/
  `rf0`/`ra0`、条件边界、64 位地址、RAS C1–C3b/D1–D4b、精确异常）由
  `tools/gem5/check_b5.py`、B6 执行断言 `exec/b6_test.cc`（30/30、non-B6
  234/234、`rule_refs` 5/14/12、swym/fence 掩码 4096×2/`lr` 零扩展+MALIGN+
  hb、`sc` 成功失败+宽度截断+精确 fault、CFXREG/CFXESC、保留单槽覆盖与消费）
  由 `tools/gem5/check_b6.py` 编译运行；B7 执行断言 `exec/b7_test.cc`
  （55/55、non-B7 209/209、静态 ILLI 零读写、各族边界/标志/舍入/NaN/Inf/±0/rem/
  sclb/f2i/fma/minmax/compare、FCSR sticky、ft 高 32 位、`rdHD` 字段陷阱）由
  `tools/gem5/check_b7.py` 编译运行，并由 `tools/gem5/b7_ref.py`（独立
  `Fraction` 精确模型）做 **3980 条**位级差分（目标寄存器 + 新 FCSR 逐位相等，
  `oracle mismatch=0`；fma/minmax/roundint 另与 `tests/inst` 的 oracle 三方交叉）
  （均不进 gem5 二进制，不改 `tests/**`）。
- **GEM5-005t 增量**：`ftsclb`/`fosclb` 第三操作数 `rfhd/rf` → `rdhd/rd`
  （同 `orrr` 编码，SPEC-181t F5.2 C1；旧 rf 写法为负例守护）；12 条 `sc.*`
  的 `rdhb != rd0`（`dst_rd0`）合法性数据 + 28 条合法性断言（sc 目的 rd0
  ⇒ ILLI、`rdhc=rd0` 仍合法、scaleB 指数 `rdhd=0` 合法）。
- **B1–B7 边界**（GEM5-002t-REPORT §5）：38 / 8 / 42 / 63 / 28 / 30 / 55。

## SE 平台（GEM5-014t）

- **构成**：`DadaoAtomicSimpleCPU`（`BaseAtomicSimpleCPU` + `DadaoISA`/
  `DadaoDecoder`/`DadaoMMU`/`DadaoInterrupts`）、`DadaoMMU`/`DadaoTlb`
  （宿主页表直通翻译，无 PTW/PTBR）、`DadaoInterrupts`（无中断源）、
  `DadaoSEWorkload`（`Process::Loader` 钩子 + syscall 分发）、
  `DadaoISA::Process`（ET_EXEC 装载、初始栈/argv/auxv、MemRAS）。
- **边界**：仅静态 `ET_EXEC`（明确拒绝 `ET_DYN`/static PIE/`PT_INTERP`）；
  syscall 面 = `set_tid_address`/`write`/`writev`/`exit`/`exit_group` +
  `ioctl` 的 `TIOCGWINSZ`/`TCGETS` 子集（musl `__stdout_write` 探测终端所需，
  返回 `-ENOTTY`）；其余号与未建模的 ioctl request 一律 `fatal` **带号与 pc**
  （不静默）；无 `brk`/`mmap`/TLS/线程/动态链接。
- **页大小**：`PageShift = 16`（64 KiB），`AT_PAGESZ = 65536`（与架构页一致）。
- **初始状态**：PC = `e_entry`、SP = `rb1`、`rf0 = 0x7FF800007FC00000`、
  `ra0` 指向 1 MiB 预置 MemRAS（`MRPTR = 区顶 − 8`，invalid entry = 0）。
- **CLI**：`configs/dadao/se.py --binary <elf> [--args "a b"] [--env K=V]
  [--mem-size] [--max-stack] [--guest-stdout/-stderr/-stdin] [--cwd]
  [--max-insts]`；退出码 = guest `status & 0xff`，非 guest 退出为 125。
- **已知限制**：无 gdb/checkpoint/多核/非 ATOMIC CPU；SEE 异常帧仍 panic。
- **页大小对照**：`qemu-dadao` 的 4 KiB 页是 QEMU 侧缺陷，已由 `QEMU-081t`
  改为 `TARGET_PAGE_BITS=16`；本任务现场 `pagesz` 在 gem5 与 qemu 两侧均
  `$?==0`（65536）。

## FS 平台（GEM5-015t，Machine-v5-Tiny）

- **构成**：`DadaoFsAtomicSimpleCPU`（`DadaoAtomicSimpleCPU` 的 Python
  子类，`mmu = DadaoFsMMU()`）、`DadaoFsTlb`（identity 翻译 + ROM/SRAM 段
  检查）、`DadaoFsMMU`（独立 SimObject，`itb`/`dtb` 为 `DadaoFsTlb`）、
  `DadaoFsWorkload`（BootROM/SRAM 装载、复位、ELF 校验）、
  `DadaoSemihosting`（v5 25 服务、`rd16`/`rb16`/`rd8`、大端 64 位）、
  `configs/dadao/fs.py`。**无** cache/PTW/PTBR/cfx/user/hmon/smon/设备/GDB/
  checkpoint/多核；`mem_mode=atomic` 为唯一模式。
- **几何**（与 `tests/shared/machine-profiles.yaml` `tiny` 逐项一致）：
  BootROM `0xffff_ffff_0000` 64 KiB（读/取指；写 ⇒ ILLI）；SRAM
  `0xffff_ff00_0000` 8 MiB；raw 基址 `0xffff_ff01_0000`、前 `0x100` 零、
  应用入口 `0xffff_ff01_0100`、`SP=0xffff_ff7e_ff00`；ELF `e_entry` 在
  BootROM（crt 设 SP 后跳应用入口）。`--dump-geometry` 打印实际生效值。
- **装载**：`--bootrom <flat>`（≤64 KiB）；raw `--kernel` 必须配
  `--bootrom`（否则 fatal）；ELF 自动识别并校验 `ELFCLASS64`/
  `ELFDATA2MSB`/`ET_EXEC`/`e_flags&0xff==1`/无 `PT_INTERP`/
  `p_vaddr==p_paddr`/`p_filesz<=p_memsz`/段与入口均在 ROM∪SRAM；ELF 与
  `--bootrom` 同给 ⇒ fatal。平台不写 SP。
- **fault → 退出码**（无异常向量，首个 fault 锁定）：`CFXMEM 0x81`、
  `CFXREG 0x84`、`ILLI 0x88`、`UNDI 0x89`、`RASOF/RASUF 0x8A/0x8B`、
  `MALIGN 0x8C`、`IALIGN 0x8D`。SE 仍保持 panic 语义（由 workload 类型
  判定，不用全局开关）。
- **semihosting**：`trap <any cfxha>, 0x3FFxx` 短路（不进入向量）；号
  `rd16`、参数块 `rb16`、返回 `rd8`、完成 `IP += 4`；服务集 = 完整 25 个
  （含 `SYS_SYNCCACHE 0x19`，`--dump-semihost-services` 输出 C++ 表实际
  键）；控制台默认 stdout（`--console-out <path>` 可重定向）；`SYS_EXIT`/
  `SYS_EXIT_EXTENDED` 低 8 位忠实传播；`SYS_SYSTEM` 默认 deny，
  `--semihost-system=native` 显式开启；未知服务号 `fatal` 带号与 pc。
  `SYS_WRITEC`/`SYS_WRITE0` 无返回，`rd8` 写无返回保留标记 `0xdeadbeef`
  （QEMU 同模式对照）；`SYS_TICKFREQ` 返回 `1e9` ticks/s（M11 用户裁定
  基线，spec 只写「ticks/秒」；`SYS_ELAPSED` 仍走通用 `semiTick`）。
- **CLI**：`--kernel`（必填）、`--bootrom`、`--semihost {on,off}`、
  `--semihost-argv`/`--semihost-arg`、`--semihost-system {deny,native}`、
  `--console-out`、`--max-ticks`（命中 ⇒ 非 guest 125）、`--dump-geometry`、
  `--dump-semihost-services`。
- **已知限制**：无 cfx/PTW/user/hmon/smon/中断/设备/时序；不支持
  checkpoint/GDB/多核；`SYS_GET_CMDLINE` 来自 `--semihost-argv`。

## FS 平台（GEM5-016t，Machine-v5-Node）

- **构成**：`DadaoNodeAtomicSimpleCPU`（`DadaoAtomicSimpleCPU` 的 Python
  子类，`mmu = DadaoNodeMMU()`）、`DadaoNodeTlb`（guest TLB + 两级页表步进 +
  地址路由 + A/D 回写 + `cfx_ptw` 异常投递）、`DadaoNodeMMU`（`itb`/`dtb`）、
  `node_cfx.{hh,cc}`（cfx 寄存器文件、运行模式、`trap`/`escape` 帧、
  权限/委派、cfx_pmem DMA、cfx_time/cfx_hart 与异步仲裁）、
  `DadaoFsWorkload profile=node`。**无** cache/设备/GDB/checkpoint/多核；
  `mem_mode=atomic`。
- **几何**（`--dump-geometry`，与 `machine-profiles.yaml` `node` 逐项一致）：
  BootROM `0xffff_ffc0_0000` **恰好 4 MiB**（读/取指；写 ⇒ ILLI）、复位
  `0xffff_ffff_0000`；PA RAM `[0, 2 GiB)`；hmon `0x0fff_0000_0000` /
  smon `0x0bff_0000_0000`（保留，M11 不启动）/ cfx_pmem
  `0x47ff_0000_0000` 各 64 KiB；raw/ELF body 基址 `0x10_0000`，
  `entry=0x10_0000`、`SP=0x7fff_0000`（由 power 设置）。
- **复位**：`PC=rb0=0xffff_ffff_0000`，`rb1..=0`、`rf0=0x7FF8_0000_7FC0_0000`、
  其余 GPR/RA=0；`inner_run_mode=hypv`、`inner_cfx_code=63`、`ptw_enable=0`、
  `PTBR=0`、TLB 空、ASID=0；cfx 复位行按 `spec/DADAO-12 §3` / `DADAO-13 §1`。
- **地址路由**：`addr[47:42]==0` 且 `ptw_enable=0` ⇒ `CFXMEM`；`ptw_enable=1`
  ⇒ guest TLB → 两级步进（512 MiB 超页 / 64 KiB 页、SPF/GPF、HSJU、R/W/X、
  A/D）；页表异常进 `cfx_ptw`（`PTWERR` 的 cause_info = PTE PA）；cfx2/3/17
  内部 SRAM 段外 ⇒ `CFXMEM`；保留 cfxha 普通 ld/st ⇒ `CFXMEM`；其它未映射
  ⇒ `0x87`。
- **cfx/monitor**：cfx0/1/2/3/4/15/17/18/63 寄存器面（cg0–cg7，cg3 仅 hypv，
  cg6 scratch=4，cg7 只读空间描述符）、`trap`/`escape`/`cfx2rd`/`cfx2rc` 与
  `switch_run_mode`/`switch_cfx_mask`/`excp_vector`/mask/deleg；`cfx5`
  （cache）未实现 ⇒ `CFXREG`；保留 cfxha ⇒ `ILLI`；CFXPERM 进当前模式
  monitor，CFXREG 按访问目标 cfx 成帧。smon（cfx2）SRAM/寄存器保留。
- **cfx_pmem DMA**：cg15 rc0–rc4（`src`/`dst`/`size`/`ctrl`/`status`），
  DIR 0=CFX→PA / 1=PA→CFX，BUSY 期间写被忽略、DONE/ERROR W1C；
  ERR_CODE 一组一热 `status[15:3]`（SIZE/CFX_RANGE/PA_RANGE/PA_FAULT）；
  `IRQ_EN=1` 时置 `cfx_pmem` pending（`1<<8`）；完成事件在 START 后 1 µs
  （`AtomicSimpleCPU` 指令边界可观测 BUSY）。**hmon 的页表模板必须经 DMA
  写到 PA 0**，平台不代写。
- **时间/中断**：`cfx_time` 1 GHz、64 位，`= (curTick-reset)/1000` ns；
  `cfx_hart` rc2 `cycle` 同源、rc3 `insn` 每指令递增；TIMER 一次性
  （cmp/ctrl，ISTATUS 只读位）；异步源按 cfxha 升序（hart 15 → pmem 17），
  每次最多投递一个，mask/pending 保留与释放补投按 spec。
- **CLI**：`--profile {tiny,node}`（默认 tiny）、`--kernel`（Node 可选）、
  `--bootrom`（Node 必需，恰好 4 MiB）、`--trace-cpu <path>`（QEMU `-d cpu`
  兼容：`PC:` / `RD[nn]` / `RB[nn]` / `RF[nn]` / `RA[nn]` / `MODE:` / `CFX..`
  块）、`--max-ticks`、
  `--dump-geometry`、semihosting 选项同 Tiny。
- **已知限制**：无 cache/时序/设备/GDB/checkpoint/多核；smon 不启动也不验收；
  `spec/Machine-v5 §6` 的 `0x0200_...` 窗口未实现（依用户口径用 identity，
  冲突见 `ISS-340`）；picolibc 不跑（`node.picolibc=false`）。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），
  清单见 `series`；规范 `docs/Process-01-组件补丁组织与构建编排.md`。
- 规模（2026-11-04 现场统计，`series` 行数 = 磁盘补丁数）：**97 份**；
  相对 GEM5-015t 后新增 8（Node 的 `node_{cfx,tlb,mmu}` + 3 个 Python
  子类/别名），修改 `configs/dadao/fs.py`、`DadaoFsWorkload.py`、`SConscript`、
  `fs_machine.{hh,cc}`、`fs_workload.{hh,cc}`、`inst.cc`、`isa.{hh,cc}`。
- 解码表由 `tools/gem5/gen_decode_table.py` 从 `contracts/opcodes.yaml` +
  `GEM5-002t` 矩阵生成；`--check` 为漂移门控（不手工编辑 `.inc`）。
  生成器内置 SPEC-181t 守护：scaleB 第三操作数必须是 `rdhd/rd`（旧 `rfhd/rf`
  直接拒绝），12 条 `sc.*` 必须保留 `dst_rd0` + `rdhb != rd0`。

## 构建 / 校验

```
make build-gem5          # SCons；SCons 缺失时 rc=2（BLOCKED，不假 PASS）
make check-gem5-decode   # 264 行解码断言 + 388 条非法/回归用例
python3 tools/gem5/check_b1.py --source .work/source/gem5   # B1 执行断言（38/38）
python3 tools/gem5/check_b2.py --source .work/source/gem5   # B2 执行断言（8/8）
python3 tools/gem5/check_b3.py --source .work/source/gem5   # B3 执行断言（42/42）
python3 tools/gem5/check_b4.py --source .work/source/gem5   # B4 执行断言（63/63）
python3 tools/gem5/check_b5.py --source .work/source/gem5   # B5 执行断言（28/28）
python3 tools/gem5/check_b6.py --source .work/source/gem5   # B6 执行断言（30/30）
python3 tools/gem5/check_b7.py --source .work/source/gem5   # B7 执行断言 + 3980 条 oracle 差分
make check-patch-tree
```

gem5 自身只接受 `<src>/build/<variant>` 作为构建目录；
`make build-gem5` 成功后把 `.work/build/gem5` 链接到该目录，
二进制在 `.work/source/gem5/build/DADAO/gem5.opt`。
