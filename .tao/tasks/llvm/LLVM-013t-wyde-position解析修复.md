# LLVM-013t: wyde-position 操作数解析修复（`wpN` 静默误编码）

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-005t`（rwii 指令格式 TableGen）、`LLVM-006t`（AsmParser 与 CodeEmitter）、`LLVM-014m`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.work/build/llvm/bin/llvm-mc`（DADAO target）
  - `contracts/opcodes.yaml`（rwii 编码）、`.tao/knowledge/contract-isa.md` §2.3/§2.4（wyde-position）
  - `.work/source/llvm-project/llvm/lib/Target/DADAO/`（TableGen + AsmParser 源码）
- 输出：
  - 新补丁 `components/llvm-project/patches/0007-*.patch` + `components/llvm-project/patches/series` 更新
  - 新增 lit 用例（`tests/lit/MC/Dadao/`）
  - 完成区附真实输出
- 约束：
  - **不改指令编码语义**（`wp` 字段仍为 2 位，`hb{5:4}`）
  - **不改 `llvm-mc -filetype=asm` 的打印形态**（仍打印数字）——既有 17 个 lit 的 `ASM:` 前缀依赖数字打印，改动会大面积回归
  - 不改 `tests/vectors/isa/*.yaml`

## 背景（完整）

### 问题（`INTEG-002t` 发现，2026-09-22）

`llvm-mc` 对 rwii 的 `wydepos` 操作数**只接受数字**；把 `wp0`/`wp1`/`wp2`/`wp3` 这类 token 传进去时**不报错**，而是当作未定义符号**静默取 0**，导致一律编码为 `wp0`：

```
$ .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj wpn.s -o wpn.o
$ .work/build/llvm/bin/llvm-objdump -d --triple=dadao-unknown-elf wpn.o
       0: 4e 04 ff ff  	set.zw	rb1, 0, 65535    # 源: set.zw rb1, wp2, 0xffff  ← 错！应为 4e 06 ff ff
       4: 4e 06 ff ff  	set.zw	rb1, 2, 65535    # 源: set.zw rb1, 2,   0xffff  ← 正确
       8: 4e 04 00 ff  	set.zw	rb1, 0, 255      # 源: set.zw rb1, wp1, 0x00ff  ← 错！应为 4e 05 00 ff
       c: 4e 05 00 ff  	set.zw	rb1, 1, 255      # 源: set.zw rb1, 1,   0x00ff  ← 正确
```

**静默误编译**属危险类别：无任何诊断，错误编码进入产物。当前影响面为零（现有 lit/生成器/脚本全用数字，`wpN` 仅出现在注释），但须修复。

### 设计（用户已于 2026-09-22 逐条确认，D1–D4 生效）

1. **接受** `wp0`/`wp1`/`wp2`/`wp3`（小写）作为数字 `0`–`3` 的等价写法；
2. **拒绝**其它非数字 token（如 `wp4`、`foo`）——**报错**，不得静默取 0；
3. 数字越界（如 `4`、`-1`）仍须报错；
4. **打印形态不变**（`llvm-mc -filetype=asm` / `llvm-objdump` 仍输出数字），故既有 `ASM:`/`OBJ:` lit 前缀不受影响。

> 方案备选（供参考，未采用）：仅做「非法 token 报错」而不接受 `wpN`（更小改动，但文档/注释里的 `wpN` 记法仍不可直接汇编）。

**确认记录（2026-09-22，用户）**：D1–D4 **逐条确认**。**ADR 判定**：D1 虽引入新的汇编器操作数语法（属工具链对外契约），但为**语法细节、可逆、非跨模块架构决策**，用户裁定**不生成 ADR**；理由记于此（对齐 `adr-authoring.md` 的判据）。

### 关键概念 / 数据

- rwii 格式：`hb{5:4}` = wyde-position（2 位）；`hb{3:0}:hc:hd` = immu16（`.tao/knowledge/contract-isa.md` §2.3/§2.4）
- 涉及指令（rwii 共 8 条）：`set.zw`/`set.ow`/`or.w`/`andn.w` × `-rd`/`-rb`
- 实现位置：
  - `llvm/lib/Target/DADAO/DADAOInstrInfo.td` 的 `def wydepos : Operand<i64>`（`ParserMatchClass = DADAOImmAsmOperand`）
  - AsmParser（`DADAOAsmParser.cpp`，`LLVM-006t` 产出）中的操作数解析路径
- **CodeEmitter 不受影响**：`getMachineOpValue()` 处理的是**已解析的整数**，本任务只改 **parser**

## 交付物

- 新补丁 `components/llvm-project/patches/0007-wyde-position-operand-parser.patch` + `series` 追加
- 新增 lit 用例（`tests/lit/MC/Dadao/`，例如 `wpn_operand.s`）：
  - `wp0`–`wp3` 各编码正确（`OBJ:` 字节级断言）
  - 数字 `0`–`3` 仍正确（不回归）
  - 非法 token（`wp4`/`foo`）→ **报错**（用 `not %llvm_mc ...` 断言失败）
- 完成区附全链路真实输出

## 已知坑 / 结论

1. **不要改打印形态**：现有 17 个 lit 用例的 `ASM:` 前缀依赖数字打印（如 `set.zw rb1, 2, 65535`）；若改为打印 `wp2` 会大面积回归。
2. **CodeEmitter 不动**：只改 parser。
3. **反例门控**：新增 lit 必须能对「`wpN` 回归为静默 0」失败——即**回退修复后新增 lit 必须 FAIL**。
4. **补丁生成流程**：`.work/source/llvm-project` 树 amend 提交 → `git format-patch` 覆盖 `components/llvm-project/patches/NNNN-*.patch`；**不得手工追加 hunk**；校验：临时 worktree 依序 apply（`0001`→`0007`）干净 + 落地 tree 与源树 HEAD tree 一致。
5. **`make build-mc` 需重编**：改 TableGen/AsmParser 后须重建（`make build-mc`）。

## 参考

- `.tao/tasks/integ/INTEG-002t-MC-QEMU-E2E冒烟.md`（发现现场与完成区）
- `contracts/opcodes.yaml`（rwii 编码）、`.tao/knowledge/contract-isa.md` §2.3/§2.4
- `.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.td`（`wydepos` 定义）
- `.tao/knowledge/adr-0006-llvm-baseline.md`

## 验收标准

1. `set.zw rb1, wp2, 0xffff` → 编码 `4e06ffff`（`wp0`–`wp3` 全部正确）
2. 数字 `0`–`3` 的编码与修复前**一致**（不回归）
3. 非法 token（`wp4`/`foo`）→ `llvm-mc` **报错**且**不产生**输出文件
4. `make build-mc` PASS
5. `llvm-lit tests/lit/MC/Dadao/` 0 failures（原 17 个 + 新增）
6. `python3 tools/llvm/check_lit_bytes.py` exit 0（N > 0）
7. `python3 tools/llvm/test_encoding_oracle.py` 全 PASS
8. `python3 tools/llvm/validate_instrinfo.py`（若适用于本改动）PASS
9. **反例门控**：回退修复后新增 lit 必须 FAIL（给出真实输出 + 还原证据；还原须含**重建**）
10. 未修改 `tests/vectors/isa/*.yaml`；未改动既有 lit 用例的 `ASM:`/`OBJ:` 期望

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
