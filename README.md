# DADAO for SimRISC 0.5.3

基于 `wiki/` 目录下 11 份规范文档，实现 LLVM 编译器、QEMU 模拟器、Chipyard 仿真器和 Linux 内核的全栈支持。

## 当前版本号

| 组件 | 版本 |
|------|------|
| SimRISC | 0.5.3 |
| AEE / ABI | 0.9.2 |
| SEE / SBI | 0.7.1 |
| HEE / HBI | 0.1.2 |

版本同步要求：AEE ↔ ABI、SEE ↔ SBI、HEE ↔ HBI 必须一致，全部基于同一 SimRISC 版本号。

## 11 阶段总览

| 阶段 | 名称 | 对应 DADAO-0628 | 关键交付物 | 估算 |
|------|------|----------------|-----------|------|
| **Phase 0** | 基础设施与规范锁定 | M0 | spec.lock.toml、AGENTS.md、角色规则、阶段计划 | ✅ 已完成 |
| **Phase 1** | ISA 规范合约与编码表 | Phase 0.5A + DL-001a/b | spec.md、opcodes.yaml、legality_rules.yaml | ~3 个 agent |
| **Phase 2** | 测试向量基础设施 | DL-001c/019a/020a | schema、inventory、YAML 向量文件 | ~3 个 agent |
| **Phase 3** | Python Golden Model | ADR-0009 M2a + DL-040b | dadao_interp.py、validate_interp.py | ~3 个 agent |
| **Phase 4** | ABI 合约与架构决策 | DL-002a/003a/004a | abi/elf/sbi spec、ADRs | ~3 个 agent |
| **Phase 5** | 组件基线 | DL-005a/006a | 组件锁、补丁目录、Docker | ~2 个 agent |
| **Phase 6** | LLVM MC 后端 | DL-007a~012a | LLVM MC 补丁 | ~3 个 agent |
| **Phase 7** | QEMU 模拟器 | DL-013a~018a + 023a~030a | QEMU 补丁 | ~3 个 agent |
| **Phase 8** | 集成测试与差分验证 | Phase 4 (MC↔QEMU) | 差分运行器、E2E 测试 | ~3 个 agent |
| **Phase 9** | gem5 第二参考 | DG-001a~005a | gem5 补丁 | ~3 个 agent |
| **Phase 10** | Sail 形式化规范 | SL-001a~003a | sail 模块、Sail C 模拟器 | ~3 个 agent |
| **Phase 11** | LLVM CodeGen | Phase 5 (Basic CodeGen) | CodeGen 补丁、E2E 测试 | ~4 个 agent |

## 依赖关系图

```
Phase 0 (Foundation)
  ├──→ Phase 1 (ISA Contract + Encoding)
  │     ├──→ Phase 2 (Test Vectors)
  │     │     └──→ Phase 3 (Golden Model)
  │     │           ├──→ Phase 8 (Integration & Differential) ←─── Phase 7 (QEMU)
  │     │           │     ├──→ Phase 9 (gem5) ──→ Phase 10 (Sail)
  │     │           │     └──→ Phase 11 (CodeGen) ←── Phase 6 (LLVM MC)
  │     │           │
  │     └──→ Phase 6 (LLVM MC) ──→ Phase 11 (CodeGen)
  │
  ├──→ Phase 4 (ABI/ELF/SBI Contract)
  │     ├──→ Phase 6 (LLVM MC)
  │     └──→ Phase 11 (CodeGen)
  │
  └──→ Phase 5 (Component Baseline)
        ├──→ Phase 6 (LLVM MC)
        ├──→ Phase 7 (QEMU)
        ├──→ Phase 9 (gem5)
        └──→ Phase 11 (CodeGen)
```

