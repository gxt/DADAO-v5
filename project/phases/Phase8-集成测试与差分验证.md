# Phase 8：集成测试与差分验证

> 对应 DADAO-0628 的 Phase 4（MC↔QEMU Integration）+ DL-019a~022c + DL-029a~030a

## 目标

将 LLVM MC（Phase 6）和 QEMU（Phase 7）与 Python golden model（Phase 3）通过统一的测试向量进行交叉验证。实现 interp ↔ QEMU 两路差分验证，确保语义一致。这是四路验证链的第一步。

## 输入文件

| 来源 | 文件 | 用途 |
|------|------|------|
| Phase 2 | `tests/vectors/isa/*.yaml` | 测试向量 |
| Phase 3 | `verif/dadao_interp.py` | Golden model |
| Phase 3 | `verif/validate_interp.py` | 向量验证器 |
| Phase 3 | `verif/run_differential.py` | 差分运行器骨架 |
| Phase 6 | `verif/llvm-mc` | LLVM MC 汇编结果 |
| Phase 7 | `verif/qemu-system-dadao` | QEMU 执行结果 |
| Phase 4 | `project/adr/0004-test-machine.md` | 测试机定义 |
| DADAO-0628 | `docs/adr/0007-testing-methodology.md` | 测试方法论 |

## 输出文件

```
DADAO-v5/
├── verif/
│   ├── run_differential.py        # 更新：支持 interp ↔ QEMU 双路
│   └── validate_vectors.py        # 向量验证（从 validate_interp.py 升级）
├── tests/
│   ├── scripts/
│   │   ├── run_qemu_test.py       # QEMU 测试运行器
│   │   ├── run_gem5_test.py       # gem5 测试运行器（骨架）
│   │   ├── run_e2e.py             # E2E 测试运行器
│   │   ├── build_test_binary.py   # 测试二进制构建
│   │   ├── crt0.s                 # 启动代码
│   │   └── dadao.ld               # 链接脚本
│   ├── e2e/
│   │   ├── smoke_add.s            # 加法测试
│   │   ├── smoke_arith.s          # 算术测试
│   │   ├── smoke_jump.s           # 跳转测试
│   │   ├── smoke_call.s           # 调用/返回测试
│   │   └── smoke_ras.s            # RAS 栈测试
│   ├── lit/
│   │   ├── MC/
│   │   │   └── Dadao             # LLVM MC 测试（来自 Phase 6）
│   │   └── E2E/
│   │       ├── lit.cfg            # LIT 配置
│   │       └── *.test             # E2E LIT 测试
│   └── interface/
│       └── README.md              # 接口测试说明
└── scripts/
    ├── check_codegen_abi.py       # CodeGen↔ABI 一致性检查
    ├── check_legality_matrix.py   # 合法性矩阵检查（骨架）
    └── check_wiki_refs.py         # Wiki 引用检查
```

## 子代理分解

### Agent I1：测试基础设施

**职责**：创建测试运行器和验证脚本

**提示词**：
```
你是 DADAO-v5 的测试基础设施工程师。创建测试运行器、启动代码和链接脚本。

1. 创建 `tests/scripts/crt0.s`（启动代码）：
```
; DADAO crt0 — bare-metal test startup
; Loaded at 0x80000000, jumps to _start

.org 0x80000000
_start:
    ; 初始化栈指针
    setzw   rb1, wp3, 0x8000    ; rb1 = 0x8000_0000 附近
    orw     rb1, wp0, 0x0000
    ; 跳转到 main
    call    main
    ; 退出
    sto     rd31, rb0, 0         ; 返回值写入 exit port
    illi    0                    ; 不应该到达这里
```

2. 创建 `tests/scripts/dadao.ld`（链接脚本）：
```
OUTPUT_FORMAT(elf64-big-dadao)
ENTRY(_start)
MEMORY {
    RAM (rwx): ORIGIN = 0x80000000, LENGTH = 128M
}
SECTIONS {
    . = 0x80000000;
    .text : { *(.text) } > RAM
    .data : { *(.data) } > RAM
    .bss : { *(.bss) } > RAM
}
```

3. 创建 `tests/scripts/build_test_binary.py`：
   - 输入：.s 汇编文件
   - 使用 llvm-mc 汇编 → .o
   - 使用 lld（或 ld.lld）链接 → ELF
   - 使用 objcopy → flat binary
   - 输出：flat binary + ELF 两种格式

4. 创建 `tests/scripts/run_qemu_test.py`：
   - 调用 qemu-system-dadao
   - 加载 flat binary
   - 捕获退出码
   - 输出测试结果

5. 创建 `tests/scripts/run_e2e.py`：
   - 自动发现 tests/e2e/*.s
   - 构建 + 运行
   - 验证退出码
```

### Agent I2：差分验证

**职责**：启用 interp ↔ QEMU 双路差分

**提示词**：
```
你是 DADAO-v5 的差分验证工程师。启用 golden model 与 QEMU 的差分验证。

更新 `verif/run_differential.py`：

功能要求：
1. 对 tests/vectors/isa/*.yaml 中每个向量：
   a. 在 golden model 中运行（已实现）
   b. 生成 QEMU 可执行的测试二进制（flat binary）
   c. 在 QEMU 中运行测试二进制
   d. 比较两个结果

2. 测试向量 → 可执行二进制的转换：
   - 编码向量（encoding class）：只需验证编码，不需要执行
   - 语义向量（semantic class）：
     a. 从 input_state 构造 QEMU 的初始状态（写寄存器值到内存）
     b. 插入测试指令
     c. 执行后转储状态
     d. 与 expected_state 比较

3. Harness 二进制协议（参考 DADAO-0628 的 harness 设计）：
   - 状态转储：执行后通过 MMIO 或特定地址输出寄存器状态
   - 退出码协议：QEMU 退出码表示测试结果

4. 输出格式：
```
=== run_differential ===
向量: rd-arith.yaml/add/semantic-1
  interp: PASS (rd3=0x0000000000000003)
  qemu:   PASS (rd3=0x0000000000000003)
  判决: AGREE
---
向量: rd-arith.yaml/add/legality-rd0
  interp: PASS (ILLI raised)
  qemu:   PASS (ILLI raised)
  判决: AGREE
---
总计: 200/200 AGREE, 0 DIVERGE, 10 SKIP
```

参考 DADAO-0628/tools/run_differential.py，但适配 DADAO-v5 的向量格式。
```

### Agent I3：一致性检查脚本

**职责**：创建各种一致性检查脚本

**提示词**：
```
你是 DADAO-v5 的验证工程师。创建系列一致性检查脚本。

1. 创建 `scripts/check_wiki_refs.py`：
   - 读取 `contracts/isa/spec.md`
   - 提取所有 `[wiki §N]` 引用
   - 验证对应的 wiki 文档中存在该章节
   - 输出缺失引用的列表

2. 创建 `scripts/check_codegen_abi.py`：
   - 读取 `verif/abi.yaml`（ABI 事实）
   - 读取 LLVM 后端生成的 CallingConv.td  RegisterInfo.td
   - 比对：参数寄存器集、callee-saved 寄存器集、DataLayout
   - 输出比对结果（匹配/不匹配）

3. 创建 `scripts/check_legality_matrix.py`（骨架）：
   - 读取 `verif/legality_rules.yaml`
   - 对每条 active 规则，检查是否存在对应 legality-class 的测试向量
   - 输出覆盖率报告

4. 更新 Makefile，添加 check target 系列：
   - `make check` → 运行所有检查
   - `make check-wiki-refs`
   - `make check-codegen-abi`
   - `make check-legality`
   - `make check-differential` → 运行差分验证
```

## 阶段验证

- `run_differential.py` 输出大多数向量 AGREE（至少 ≥ 80%）
- 分歧（DIVERGE）向量可追溯到实现差异而非规范差异
- E2E smoke 测试全部通过
- `make check` 全部通过

## 依赖关系

- 依赖 Phase 3（golden model）
- 依赖 Phase 6（LLVM MC）
- 依赖 Phase 7（QEMU）
