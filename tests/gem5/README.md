# gem5 验收向量入口

gem5 ISA 期望值读取 `tests/vectors/isa/*.yaml`，指令清单与编码掩码读取
`contracts/opcodes.yaml`；两者均以 `spec/` 为语义依据，不以 QEMU 或 gem5
执行结果生成期望值。

运行 `python3 tools/gem5/vector_inventory.py` 可核对 YAML 编码向量、
运行期 M1 用例、FP probe 函数和 excluded 门控形成的逐 opcode 覆盖证据，
并列出尚待补齐的条目。`--require-complete` 用于覆盖收口；缺失时返回非零。

`make test-gem5` 从规范向量生成大端 ROM 字节，交由
`AtomicSimpleCPU` 的全系统夹具执行。ISA 夹具回读目的寄存器、
`rd0`、`rb0`、PC、模式和 FCSR，并核对复位时的 RA/RF 状态及 `rf0` 与 FCSR
双向别名；非法、保留或未对齐取指编码按 `Machine-01` 核对
`0x88`/`0x89`/`0x8d` 退出码。已定义编码的判别表由
`contracts/opcodes.yaml` 生成，可用
`python3 tools/gem5/generate_opcode_table.py --check` 核对补丁中的快照。
执行驱动接受 `--gem5` 或 `DADAO_GEM5_BINARY` 指定二进制，构建或执行
未就绪时门控必须失败。
`python3 tools/gem5/test_isa.py --profile skeleton` 固定运行
`GEM5-003t` 的 61 条 ISA 骨架用例；`--vector-root` 可指向临时向量副本，
用于注入错误期望而不修改真源。默认 `current` profile 保持运行当前代表集。
`python3 tools/gem5/test_isa.py --profile remaining` 运行 M3、M8、`aip.si`
独立向量和 11 条 excluded `ILLI` 用例；`--inject-excluded` 模拟误接受并要求
门控失败。
`make test-gem5-fp` 复用四份从规范独立派生的 FP probe 输入，核对 RF/FCSR、
特殊值、四种舍入模式、异常标志、转换和比较；`--inject` 注入错值。
`make check-gem5-full` 依次运行 235/235 覆盖、current、Machine-01、
remaining、完整 FP 和程序集全量。

`GEM5-004t` 已把当前代表集扩到 517 条，覆盖标量运算、访存、控制流和
RegRAS/MemRAS；003 skeleton 固定为 61 条，另有三条 smoke 序列。

`make test-gem5-machine` 独立构造 ELF64/MSB/PT_LOAD、raw boot ROM 和
Machine-01 参数块，运行 47 项机器检查：复位到 boot ROM、`hypv→user`
移交、ELF/BSS 装载及错误头/越界段拒绝、trap/escape、cfx 权限与异常路由，
规范 cg5 现场布局、RO/非法寄存器、跨 cfx escape，以及 25 个 semihosting
服务。文件服务验证真实宿主副作用，
`SYS_EXIT`/`SYS_EXIT_EXTENDED` 核对退出状态；未知服务和坏参数必须返回失败。
`tools/gem5/test_machine.py --inject` 会破坏启动期望，用于验证门控可达 FAIL。

`make test-gem5-toolchain` 消费 `make build-bootrom` 与 `make test-elf` 已生成
的真实产物，固定运行 `bootrom.bin + multi_tu_call.elf`，独立期望退出状态
为 42；该入口证明 LLVM/LLD 产物无需转换即可由 gem5 的 Machine-01 路径启动。

`tests/gem5/programs.yaml` 是跨程序清单：对 `tests/e2e/*.{c,s}` 做闭包，
逐项记录独立退出期望或排除理由。`tools/gem5/test_programs.py` 构建并运行
清单中的程序及 Embench；代表档从每个 E2E 类别机械选一例，并选择原始
`LOCAL_SCALE_FACTOR` 最小的 Embench，完整档运行全部适用 E2E 和 19 个
Embench 的 `O0/O2`。Embench 正确性档只在临时源码副本中关闭 warmup、把
计时重复数降为 1，仍由 `verify_benchmark` 判定，不产生性能结论。报告记录
命令退出码、guest 退出事件、IP、模式、CFX 及逐字段差分；超时、非
semihosting 退出和缺失退出码均失败。`--inject-result` 与
`--inject-drop-exit` 分别验证错结果和退出码丢失的可达 FAIL。
