# gem5 验收向量入口

gem5 ISA 期望值读取 `tests/vectors/isa/*.yaml`，指令清单与编码掩码读取
`contracts/opcodes.yaml`；两者均以 `spec/` 为语义依据，不以 QEMU 或 gem5
执行结果生成期望值。

运行 `python3 tools/gem5/vector_inventory.py` 可核对已有 active 编码向量
的 ID 与 mask/value，并列出尚待补齐的条目。`--require-complete` 用于
覆盖收口；缺失时返回非零。

`make test-gem5` 从现有 RD/RB `add.si`、双目的 `add.uo` 和保留编码向量生成大端 ROM
字节，交由 `AtomicSimpleCPU` 的全系统夹具执行一步。夹具回读目的寄存器、
`rd0`、`rb0`、PC、模式和 FCSR，并核对复位时的 RA/RF 状态及 `rf0` 与 FCSR
双向别名；非法、保留或未对齐取指编码按 `Machine-01` 核对
`0x88`/`0x89`/`0x8d` 退出码。已定义编码的判别表由
`contracts/opcodes.yaml` 生成，可用
`python3 tools/gem5/generate_opcode_table.py --check` 核对补丁中的快照。
执行驱动接受 `--gem5` 或 `DADAO_GEM5_BINARY` 指定二进制，构建或执行
未就绪时门控必须失败。
`python3 tools/gem5/test_isa.py --profile skeleton` 固定运行
`GEM5-003t` 的 16 条 ISA 骨架用例；`--vector-root` 可指向临时向量副本，
用于注入错误期望而不修改真源。默认 `current` profile 保持运行当前代表集。
`make check-gem5-full` 额外要求全部 opcode 具备 active 编码向量；
剩余执行覆盖将在后续 gem5 任务补足，当前门控不表示全量执行通过。

`GEM5-004t` 的阶段性门控又纳入现有 `reg-imm-block.yaml`、
`reg-compare.yaml`、`ctrl-br.yaml` 与 `ctrl-jump.yaml` 的代表向量，
fixture 用可配置指令装载地址在 RAM 执行控制流。当前 50 条运行用例
只证明已纳入的指令和状态；访存、返回地址栈、ELF 与 semihosting 仍待后续门控。
