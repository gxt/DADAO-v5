# VERIF-003t: QEMU 语义测试 harness

**模块**：verif
**项目里程碑**：M1
**依赖**：`QEMU-014m`、`TESTSUITE-003t`、`SPEC-006t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `tests/vectors/isa/*.yaml`（含 `class`、`encoding.word`、`input_state`、`expected_state`、`expected_fault`、`status` 字段）
  - `QEMU-014m` 交付的 `qemu-system-dadao`（构建路径以 `INFRA-006t` Makefile 为准）
  - `SPEC-006t` 的 Test Machine ADR（`.tao/knowledge/adr-0004-test-machine.md`）：ROM/RAM 地址、exit port、exit code 协议
  - `verif/opcodes.yaml`（trusted 指令集编码真相）
- 输出：
  - `tests/scripts/build_test_binary.py`
  - `tests/scripts/run_qemu_test.py`
  - `tests/scripts/gen_trampoline.py`
  - `tests/scripts/trampoline.bin`
  - `tests/scripts/README.md`
- 约束：
  - **不调用 `llvm-mc`**：测试 binary 全部由 Python `struct.pack('>I', word)` 直接生成（QEMU 测试路径与 LLVM 路径完全独立）
  - loader/dumper/exit 只用 trusted 指令集，编码逐条取自 `verif/opcodes.yaml`
  - state-dump region 不与 ROM/RAM/exit port 冲突
  - 依赖 `TESTSUITE-003t` 已填充的 `encoding.word`

## 背景（完整）

### 目标

实现 raw-encoding 语义测试 harness：从 vector YAML 的 `encoding.word` 直接构建测试 binary，通过 QEMU 运行，读取 state-dump region，与 `expected_state` 比较；**不依赖 LLVM 汇编器**。完成后对任意 vector（semantic/legality/boundary class）可运行：

```
python3 tests/scripts/run_qemu_test.py tests/vectors/isa/rd-arith.yaml
```

并得到 PASS/FAIL 报告。

### 设计理由

- QEMU 测试路径必须与 LLVM 路径完全独立，否则单一实现 bug 会穿透：直接用向量里的 raw encoding word 构 binary，绕开汇编器。
- 测试 binary 分四段（loader / test / dumper / exit），guest 自己加载输入寄存器、执行被测指令、导出状态、写 exit port 退出，harness 只负责构 binary、跑 QEMU、解析退出码/状态。
- 用 ROM trampoline 把控制权从复位地址交给 RAM 中的测试 binary。

### 关键概念 / 数据

**Binary 布局（写入 RAM @ BINARY_BASE）**

```
[section 1] loader   ← 设置 rd/rb 寄存器到 input_state 值
[section 2] test     ← 被测指令（struct.pack('>I', encoding_word)）
[section 3] dumper   ← 将 rd/rb/pc 写到 state-dump region
[section 4] exit     ← 写 exit code 到 exit port，触发 QEMU shutdown
```

**寄存器加载序列（section 1）**：64-bit 值分 4 个 16-bit chunk 加载，首 chunk 用 `set.zw` 清空+设值，后续用 `or.w` 合并：

```
set.zw  rdX, pos0, imm16_0   # bits[63:48]
or.w    rdX, pos1, imm16_1   # bits[47:32]
or.w    rdX, pos2, imm16_2   # bits[31:16]
or.w    rdX, pos3, imm16_3   # bits[15:0]
```

只加载 `input_state.rd` / `input_state.rb` 中明确列出的寄存器；未列出的保持复位值（rd0=0，rb0=PC 不手动设置）。RB 加载用 RB 变体（`set.zw`-rb / `or.w`-rb）。内存写入（`input_state.memory`）：先把值加载到临时 RD，再 `st.o rdX, rbY, offset`。

**state-dump region（section 3，RAM 上边界附近）**

```
offset 0x0000: rd[0..63]  (64 × 8 bytes = 512 bytes, big-endian)
offset 0x0200: rb[0..63]  (64 × 8 bytes = 512 bytes, big-endian)
offset 0x0400: pc          (8 bytes, 当前 rb0 值)
```

用一个临时 RB 指向 dump base，再批量 `st.o` 写入，减少指令数。

**exit section（section 4）**

把 exit code 装入一个 RD，把 exit port 地址装入一个 RB，`st.o` 写入 exit port。ILLI 情形由 QEMU 异常处理器直接写对应 fault code 到 exit port。

**Python API**

```python
def build_test_binary(vector_case: dict, trusted_instrs) -> bytes:
    """Return raw binary to load at BINARY_BASE."""
    ...
instr_word = int(vector_case["encoding"]["word"], 16)
instr_bytes = struct.pack('>I', instr_word)
```

**ROM trampoline**：复位后从 ROM 执行，设置 SP、跳转到 BINARY_BASE。trampoline raw bytes 由 `gen_trampoline.py` 硬编码生成（不依赖 llvm-mc），供 `-bios` 加载。

**run_qemu_test.py**：主运行器，跑 QEMU（`-M <machine> -nographic -bios trampoline -kernel test.bin`），解析退出码/state-dump，按 `expected_fault` 与 `expected_state` 判 PASS/FAIL；批量运行时允许 `status: deferred` 部分跳过。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-019a-phase3-harness.md`（完整转述：目标、前提、4 段 binary 布局、寄存器加载序列、state-dump region、exit section、Python API、trampoline、run_qemu_test、README、约束、验收步骤、完成区、两轮代码级 Architecture Review）
- DADAO-0628：`tests/scripts/build_test_binary.py`、`tests/scripts/run_qemu_test.py`、`tests/scripts/gen_trampoline.py`、`tests/scripts/trampoline.bin`、`tests/scripts/README.md`（形态参考，禁止复制代码/字节）
- DADAO-0628：`docs/adr/0004-test-machine.md`（exit port 协议、ROM/RAM 地址）

## 交付物

- `tests/scripts/build_test_binary.py`：raw `encoding.word` → flat binary（4 段布局）
- `tests/scripts/run_qemu_test.py`：跑 QEMU、解析退出码/状态、PASS/FAIL 报告
- `tests/scripts/gen_trampoline.py` + `tests/scripts/trampoline.bin`：ROM trampoline 生成
- `tests/scripts/README.md`：单条/批量运行方式、state-dump 读取机制、trampoline 生成方法

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **助记符与编码**：trusted 指令集（`set.zw`/`or.w`/`st.o`/`ld.o`/`add.si` 等）按 0.5.3 命名与 `verif/opcodes.yaml` 的 mask/value 生成，**不复制 0.4.1 的 `setzw`/`orw`/`sto` 编码与手写字节**。
2. **地址布局以 v5 ADR 为准**：BINARY_BASE / exit port / state-dump / ROM 地址从 `SPEC-006t` 的 `.tao/knowledge/adr-0004-test-machine.md` 读取，若与 0.4.1 数值有出入，以 v5 ADR 为准。
3. **halt 语义**：0.5.3 的退出/停机指令与 `halt` 助记符按 `contract-isa.md` §7.5 与 `verif/opcodes.yaml` 确定；exit port 写协议以 v5 ADR 为准。
4. **QEMU 构建路径**：v5 为 `.work/qemu/build/...`（以 `INFRA-006t` Makefile 为准），非 0628 的 `.work/source/qemu/build/`。
5. **state-dump 读取机制**：0.4.1 未定稿（在 README 里二选一），v5 实现时选最简可行方案（serial 输出 hex / QMP memory dump / 退出后读文件），并把选择记录进 README。
6. **向量来源**：`tests/vectors/` 由 `TESTSUITE` 模块交付，字段 schema 以 `TESTSUITE-002t` 为准，不沿用 0.4.1 向量正文。

## 已知坑 / 结论

摘自 DADAO-0628 DL-019a 完成区与两轮代码级 Architecture Review：

1. **不依赖 LLVM 汇编器**：`struct.pack('>I', word)` 直接产出大端 4 字节；这是 harness 独立性的关键。
2. **4 段布局**：loader/test/dumper/exit；exit code 约定 `0=pass`、`≥0x80=fault`（精确 fault code 见 VERIF-004t）。
3. **保留寄存器冲突**：0.4.1 harness 用 `TEMP_RB=63`/`TEMP_RD=63`/`EXIT_RD=62` 作 scratch，若测试向量占用这些寄存器会被覆盖。v5 需在向量 convention / README 中明确保留寄存器范围（具体编号由 DS 依 v5 向量占用选定）。
4. **`halt rd0` → ILLI**：0.4.1 `trans_halt` 对 `ha==0` 走 `gen_exception_illegal`；v5 对应语义以 `contract-isa.md`/QEMU 实现为准，harness 不假设。
5. **编码函数逐字段验证正确**（0.4.1 审查结论）：`reg<<18`=ha、`ww<<16`=wyde-pos、imm 分片映射到 hb/hc/hd；v5 需按 0.5.3 字段位重新核对。
6. **附带 QEMU bug 修复**（machine 名、CPU 注册、TLB flat-mapping、SysemuCPUOps/TCGCPUOps 回调）在 v5 属 `qemu` 模块职责，本任务只消费可运行的 QEMU。
7. **state-dump 读取是唯一未定稿点**：0.4.1 实现时在 README 记录最终方案，v5 同样处理，不得假装已定。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-019a-phase3-harness.md`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/build_test_binary.py`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/run_qemu_test.py`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/gen_trampoline.py`
- DADAO-0628：`.work/DADAO-0628/tests/scripts/trampoline.bin`
- DADAO-0628：`.work/DADAO-0628/docs/adr/0004-test-machine.md`
- 本项目：`.tao/knowledge/adr-0004-test-machine.md`、`verif/opcodes.yaml`、`tests/vectors/isa/`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `python3 tests/scripts/run_qemu_test.py tests/vectors/isa/rd-arith.yaml --case <semantic 用例>` 返回 PASS
2. legality 用例（如 rd0 目的）返回对应 fault（ILLI），退出码与 ADR 约定一致
3. 批量运行 `tests/vectors/isa/` 得 `N passed, M deferred, 0 failed`
4. `grep` 确认 `build_test_binary.py`/`run_qemu_test.py` 未调用 `llvm-mc`
5. `trampoline.bin` 由 `gen_trampoline.py` 生成且可被 QEMU `-bios` 加载进入 BINARY_BASE
6. `tests/scripts/README.md` 记录运行方式、state-dump 读取机制、保留寄存器约定

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
