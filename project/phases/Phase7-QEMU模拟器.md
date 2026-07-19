# Phase 7：QEMU 模拟器

> 对应 DADAO-0628 的 DL-013a~018a + DL-023a~030a + DL-041a~042b（QEMU 标量核心）

## 目标

创建 DADAO 的 QEMU 目标，实现 bare-metal 模式下的指令执行（MMU-off，无 OS）。QEMU 作为功能模拟器，与 Phase 3 的 Python golden model 构成差分验证的第一对支线。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 1 | `contracts/isa/spec.md` | ISA 语义规范 |
| Phase 1 | `verif/opcodes.yaml` | 编码表 |
| Phase 1 | `verif/legality_rules.yaml` | 合法性规则 |
| Phase 3 | `verif/dadao_interp.py` | Golden model 参考实现 |
| Phase 4 | `project/adr/0004-test-machine.md` | 测试机定义 |
| Phase 5 | `.work/source/qemu/` | QEMU 源码 |
| DADAO-0628 | `components/qemu/patches/` | 12 个参考补丁 |

## 输出文件

```
DADAO-v5/components/qemu/patches/
├── series
├── 0001-dadao-target-skeleton.patch     # 目标骨架（CPU、译码器）
├── 0002-dadao-hw-meson-subdir.patch     # 构建集成
├── 0003-dadao-decodetree.patch          # Decodetree 译码
├── 0004-dadao-rd-arith.patch            # RD 算术指令
├── 0005-dadao-load-store.patch          # 加载/存储
├── 0006-dadao-ctrl-flow.patch           # 控制流
├── 0007-dadao-branch-call-fix.patch     # 分支/调用修复
├── 0008-dadao-fix-helper-exit.patch     # 退出协议
├── 0009-dadao-ldo-align-malign.patch    # 对齐和 MALIGN
├── 0010-dadao-reserved-undi.patch       # 保留编码 UNDI
├── 0011-dadao-rela-pc-base.patch        # PC 相对寻址
└── 0012-dadao-ras-stack.patch           # RegRAS 栈
```

## 子代理分解

### Agent H1：QEMU 目标骨架 + 译码

**职责**：创建 QEMU 目标骨架和 decodetree 译码器

**提示词**：
```
你是 DADAO-v5 的 QEMU 工程师。创建 QEMU DADAO 目标骨架和译码器。

读取：
- DADAO-v5/contracts/isa/spec.md
- DADAO-v5/verif/opcodes.yaml
- DADAO-v5/wiki/AGENTS.md
- DADAO-0628/components/qemu/patches/0001~0003（参考）

创建补丁 0001-0003：

**补丁 0001：目标骨架**
1. `target/dadao/cpu.h`：CPU 状态结构
   - rd[64], rb[64], rf[64], ra[64]（uint64_t 数组）
   - pc（uint64_t）
   - 异常状态寄存器
   - ras_count（ra63 引用计数辅助）
2. `target/dadao/cpu.c`：CPU 初始化、复位
3. `target/dadao/helper.h`：helper 函数声明
4. `target/dadao/translate.c`：译码主入口
5. `target/dadao/Makefile.objs`：构建

**补丁 0002：构建集成**
1. `meson.build`：在目标列表中加 DADAO
2. `configs/targets/dadao-softmmu.mak`：配置
3. 添加到 `hw/` 的 meson 集成

**补丁 0003：Decodetree 译码**
从 opcodes.yaml 生成 decodetree 文件 (.dec)：
每条指令一个 pattern，格式：
```
# add-rd-orrr
{op[8], ha[6], hb[6], hc[6], hd[6]} 0010-0xxx-... -> trans_add_rd_brrr
```

注意 DADAO-v5 相比 DADAO-0628 的新格式：
-brri 格式需要  字段提取
- brrr 在 ha[5:0]
- ciii/crrr/crii 格式需要 cfxcode 字段提取
- rwii 格式需要 wpN 字段提取
```

### Agent H2：指令执行

**职责**：实现所有指令的 TCG 翻译

**提示词**（量大，可拆多个子 agent 并行）：

```
你是 DADAO-v5 的 QEMU TCG 工程师。实现 DADAO 指令的 TCG 翻译。

每个补丁实现一组指令：

**补丁 0004：RD 算术（translate_rd_arith.c）**
- addi-rd-rrii：gen_helper_addi_rd
- add-rd-rrrr：128 位，gen_helper_add_rd（调用 helper，因为 C 无法直接表示 128 位）
- sub-rd-rrrr
- muls/mulu-rd-rrrr：64×64→128 位乘法，helper
- divs/divu-rd-rrrr：64 位除法，helper
- add-rd-orrr/sub-rd-orrr：带  的加减
- muls-rd-orrr/mulu-rd-orrr：带  的乘
- divs-rd-orrr/divu-rd-orrr：带  的除
- rems-rd-orrr/remu-rd-orrr：带  的取余
- rd0 特殊处理：写入 rd0 时丢弃结果（合法）或触发 ILLI（非法）

**补丁 0005：加载/存储（translate_ldst.c）**
- ldbs/ldbu/ldws/ldwu/ldts/ldtu/ldo-rd-rrii：单 load，大端序
- stb/stw/stt/sto-rd-rrii：单 store，大端序
- ldmbs/.../ldmo-rd-rrri：多 load，顺序存取
- stmb/.../stmo-rd-rrri：多 store
- ldo-rb-rrii/sto-rb-rrii：RB 存取
- ldo-ra-rrii/sto-ra-rrii：RA 存取
- ldt-rf-rrii/stt-rf-rrii/ldo-rf-rrii/sto-rf-rrii：RF 存取
- 对齐检查：各宽度对齐要求不同
- MALIGN 异常触发

**补丁 0006：控制流（translate_control.c）**
- brn/brnn/brz/brnz/brp/brnp-riii：6 种条件分支
- breq/brne-rrii：双寄存器分支
- jump-iiii/jump-rrii：无条件跳转
- call-iiii/call-rrii：调用 + RAS push
- ret-riii：返回 + RAS pop + 返回值赋值
- PC 相对地址计算（imms << 2）

**补丁 0007：分支/调用修复（fixes）**
- 分支延迟槽处理（如果没有延迟槽，注明）
- call 指令的 ra63 压栈逻辑
- ret 指令的 ra63 弹栈逻辑

**补丁 0008：退出协议 + 其他**
- 实现 exit port MMIO：sto 到 0x10000000 时退出 QEMU
- 退出码提取：store 值的低 8 位
- swym（NOP）实现
- illi（ILLI 异常）实现

**补丁 0009：对齐和 MALIGN**
- 各宽度加载/存储的对齐检查
- MALIGN 异常精确处理（无副作用）

**补丁 0010：保留编码 UNDI**
- 未分配 opcode → UNDI 异常
- 与 ILLI 区别（ILLI = 合法编码但非法操作数，UNDI = 未定义编码）

**补丁 0011：PC 相对寻址**
- rela-rb-riii 指令实现
- imms18 << 12 + (PC[47:12] << 12)

**补丁 0012：RAS 栈**
- RegRAS 完整实现（ra63 压栈/弹栈/引用计数）
- RASOF/RASUF 检测
- 注意：MemRAS 可以在 M4（系统阶段）实现，M1 只需 RegRAS

参考 DADAO-0628 的对应补丁，但适配 SimRISC 0.5.1 的新指令集。
关键差异：
- 更多brri 格式指令需要  处理
- 浮点寄存器和指令基础支持（即使不实现完整浮点执行）
- cfx 指令 skeleton（未实现详细功能时不触发异常即可）
- RA 寄存器存取（ldo-ra/sto-ra）
- RF 寄存器存取骨架
```

### Agent H3：QEMU 测试

**职责**：创建 QEMU 测试验证

**提示词**：
```
你是 DADAO-v5 的 QEMU 测试工程师。创建 QEMU 的验证测试。

1. 创建裸机测试脚本 `tests/scripts/run_qemu_test.py`：
   - 调用 qemu-system-dadao -M dadao-m1 运行测试
   - 加载 flat binary
   - 捕获退出码
   - 输出 PASS/FAIL

2. 创建集成测试脚本 `tests/scripts/build_test_binary.py`：
   - 使用 LLVM MC 汇编 -> flat binary
   - 加载到 QEMU 运行

3. 创建 `tests/e2e/` 下的 smoke 测试：
   - `smoke_add.s`：加载两个数，相加，退出
   - `smoke_arith.s`：多指令测试
   - `smoke_jump.s`：跳转测试
   - `smoke_call.s`：调用/返回测试
   使用手写汇编（通过 llvm-mc 汇编）或直接使用 raw encoding

4. 验证 QEMU 与 golden model 的一致性：
   - 同一个测试程序在 interp 和 QEMU 中运行结果一致
```

## 阶段验证

- `qemu-system-dadao -M dadao-m1` 可启动并加载测试程序
- smoke 测试退出码正确
- 基本指令：算术、加载、存储、分支、调用、返回运行正确
- MALIGN/ILLI/UNDI 异常被正确触发

## 依赖关系

- 依赖 Phase 1（ISA 规范、opcodes.yaml）
- 依赖 Phase 4（Test machine ADR-0004）
- 依赖 Phase 5（QEMU 组件已获取）
