# LLVM-061m: M5 llvm 里程碑

**模块**：llvm
**项目里程碑**：M5
**状态**：待开始
**目标**：LLVM 支持 M5——实现 `trap`/`escape`/`cfx2rc`/`cfx2rd`（`SimRISC-11 §其它`）的 MC（parser/printer/disassembler/编码）+ 必要 CodeGen/内建；`escape` 位宽关系落地（汇编 `imms20`（字节，`%4==0`）⇔ 编码 `imms18`（`>>2`））；两写法 `cfx<ha>`/`cfx_<name>` 等价 + `cfx2rd/cfx2rc` 简化 regname 写法；L1 MC 向量 + 编码 oracle；`make check`/`check-patch-tree`/`check-lit` 绿。`SimRISC-12`（`cfxld`/`cfxst`/`fence`/`lr_*`/`sc_*`）保持 deferred。
**关联任务**：`LLVM-060t`（1 个）

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`components/llvm-project/patches/llvm/lib/Target/DADAO/**`（trap/escape/cfx2* 编码/AsmParser/InstPrinter/Disassembler）+ `series` + `changelog.md`；L1 MC 向量与独立 oracle
- `make build-mc` EXIT=0；`llvm-mc` 对 4 条指令正例 EXIT=0 且字节 == `contracts/opcodes.yaml` 派生期望；`cfx_<name>`/`cfx<ha>` 等价 ≥2 对；简化 regname 写法等价；`escape` 位宽/非 4 倍数报错/越界报错
- 往返（汇编↔反汇编）≥1
- 不回归：`make check` EXIT=0；`make check-patch-tree` EXIT=0（断言⑥）；`make check-lit` EXIT=0
- `check-source-state`：`.work/source/llvm-project` worktree clean、HEAD = base+1
- `SimRISC-12` 范围未越界（`grep` 证据）

## 核验记录（主会话）

（核验命令、输出与退出码；结论）
