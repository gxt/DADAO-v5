# QEMU-004t: Decodetree 解码

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-003t`、`SPEC-003t`、`SPEC-008t`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-003t` 产出的 `target/dadao/` 骨架
  - `.tao/knowledge/contract-isa.md` §2（编码）、附录 A（完整编码清单：A.1 QFC 主表 + A.2–A.7 MISC 子表）
  - `contracts/opcodes.yaml`（256 条机器可读编码表，`op`/`mask`/`value`/`fields`/`legality`）
  - `contracts/legality_rules.yaml`（UNDI/ILLI 触发条件）
- 输出：`components/qemu/patches/0002-dadao-decodetree.patch`、`components/qemu/patches/series`
- 约束：
  - decodetree 覆盖 M1 全部 opcode；每条指令有对应 `trans_*` 函数
  - 未命中（保留 opcode）→ UNDI；`trans_*` 主动拒绝（非法操作数）→ ILLI；两者用不同 helper
  - MISC 子表必须按 `ha`（minor-opcode）继续解码，不得将整个子表 op 当单一指令
  - 不修改 `cpu.h` 的 CPUState 字段布局（`QEMU-003t` 已固定）
  - decodetree 文件随补丁完整交付，apply 后即可编译
  - 完成后不自行 commit

## 背景（完整）

### 目标

用 QEMU decodetree 机制为全部 M1 opcode 生成解码表，将 `translate.c` 的手写分派替换为 decodetree 生成的 `decode()` 调用。所有 `trans_*()` 存根默认调用 `gen_exception_illegal()`（唯一例外：`swym` 直接返回 `true`，即 NOP），使任何指令仍触发 ILLI，与 `QEMU-003t` 行为一致。0628 对应任务 `DL-014a` 经评审 Accepted（87 个 trans 函数）。

### 设计理由

- decodetree 是 QEMU 官方指令解码生成器，把编码表与翻译函数解耦，便于按 `opcodes.yaml` 机械生成，减少手写位域错误。
- 骨架期存根不实现语义，只验证解码覆盖完整、UNDI/ILLI 分离正确。
- 与 oracle 对齐：pattern 的 `mask`/`value` 直接来自 `opcodes.yaml`，期望值不从实现反推。

### 关键概念 / 数据

**字段声明**（`target/dadao/insn.decode` 顶部）：
```
%op    24:8
%ha    18:6
%hb    12:6
%hc     6:6
%hd     0:6
```
即 op[31:24]、ha[23:18]、hb[17:12]、hc[11:6]、hd[5:0]。

**主表结构（0.5.3，与 0628 完全不同）**：opcode 分配以 `contract-isa.md` 附录 A.1 与 `contracts/opcodes.yaml` 为准，覆盖范围含：
- 系统/原子：`illi`(0x00)、`fence`(0x01)、LR/SC（0x04–0x07、0x0C–0x0F）
- RD 单 load/store（byte/wyde/tetra/octa，0x10–0x1A、0x20–0x21）
- RB/RA/RF 单 load/store（0x22–0x27）
- RD/RB/RA/RF 多 load/store（0x28–0x3F）
- MISC 子表（0x40 MISC-AMO、0x41 MISC-octa、0x42 MISC-tetra、0x43 MISC-wyde、0x44 MISC-byte、0x45 MISC-RF）
- rwii 立即数设置（0x48–0x4F：`or.w`/`andn.w`/`set.zw`/`set.ow`/`set.w`）
- 算术/乘除（0x50–0x57：`add.uo`/`add.so`/`sub.uo`/`sub.so`/`mul.uo`/`mul.so`/`ftmadd`/`fomadd`）
- `add.si`(0x59)、`rela.si`(0x5A)、`add.si-rb`(0x5B)、`cmp.ui`/`cmp.si`(0x5C/0x5D)、`cs.*-rf`(0x5E/0x5F)
- 条件赋值 `cs.n/z/p/eq/ne`（0x60–0x67）
- 条件跳转 `br.*`（0x68–0x6F）
- 跳转/调用/返回/占位（0x70–0x77：`jump`/`br.z-rb`/`br.nz-rb`/`call`/`ret`/`swym`）
- 特权（0x7A–0x7F：`cfx2rd`/`cfx2rc`/`cfxld`/`cfxst`/`escape`/`trap`）

**MISC 子表**：以 `ha`（minor-opcode）继续解码。A.2 MISC-octa（`and.o`/`or.o`/`xor.o`/`xnor.o`/`ext.*`/`shr.*`/`shl.*`/`add.so-rb`/`sub.so-rb`/`cmp.*`/`rd2rd`/`rd2ra`/`ra2rd`/`rb2rb`/`rd2rb`/`rb2rd`/`div.*`/`rem.*`/`rd2rf`/`rf2rd`）、A.3 MISC-tetra、A.4 MISC-wyde、A.5 MISC-byte、A.6 MISC-RF、A.7 MISC-AMO。**须逐行对照 `contract-isa.md` 附录 A 与 `opcodes.yaml` 换算，不得自行推断。**

**解码分派语义**：
- `decode(ctx, insn)` 返回 `true` → 已处理（存根不生成 TCG，继续执行下一条）
- 返回 `false` → UNDI（保留编码），调用 `gen_exception_undi()`
- `trans_*` 主动触发 ILLI → `gen_exception_illegal()`
- `swym` → `return true`（NOP），不生成 TCG

**meson 集成**：`target/dadao/meson.build` 添加 `decodetree_files('insn.decode')` 并加入 `dadao_ss`，参考所选 QEMU 版本 `target/riscv/meson.build`。

### 上游引用

- DADAO-0628：`code-agent/tasks/DL-014a-qemu-decodetree.md`（完整转述：ISA 编码结构、`insn.decode` 字段、主 opcode 组、MISC-Norm 子表、translate.c 集成、meson、约束、完成区与 Architecture Review）。
- DADAO-0628：`components/qemu/patches/0003-dadao-decodetree.patch`（仅参考结构，不复制 0.4.1 编码数据）。

## 交付物

- `components/qemu/patches/0002-dadao-decodetree.patch`：`target/dadao/insn.decode`、`target/dadao/translate.c`（decodetree 集成 + 全部 `trans_*` 存根）、`target/dadao/meson.build`。
- `components/qemu/patches/series`：加入 `0002`。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **opcode 映射完全重写**：0628 主表 op 从 0x10 起、MISC-Norm 为 op=0x10；v5 为 0x00 起的全新 QFC 表 + 6 张 MISC 子表（0x40–0x45）。`insn.decode` 必须依据 `contract-isa.md` 附录 A 与 `contracts/opcodes.yaml` 重新生成，**不得复制 0628 的 pattern 数据**。
2. **指令数量**：v5 `opcodes.yaml` 共 256 条，远超 0628 的 87 条；`trans_*` 存根数量随之增加。
3. **命名**：全部使用 0.5.3 助记符（`add.uo`/`add.so`、`div.so`/`div.uo`、`cs.n`、`br.n`/`br.nz`、`set.zw`、`ld.o`、`st.o`、`illi`）；decodetree 的 pattern 名与 `trans_*` 名须与之一致。
4. **MISC 子表结构不同**：0628 的 `MISC-Norm`（op=0x10）在 v5 拆为 byte/wyde/tetra/octa/RF/AMO 六张子表；子表内 minor-opcode 位宽为 `ha[5:0]`（或 `ha[5:3]:ha[2:0]` 三段编码），以附录 A 为准。
5. **字段声明相同**：`%op 24:8` / `%ha 18:6` / `%hb 12:6` / `%hc 6:6` / `%hd 0:6` 与 0628 结构一致，可沿用。
6. **浮点/RF 子表**：M1 范围排除 §6 浮点，但 MISC-RF 子表仍须解码为 ILLI 桩（不静默）。

## 已知坑 / 结论

摘自 0628 `DL-014a` 完成区与 Architecture Review：

1. **UNDI vs ILLI 分离**：decodetree 未命中 → UNDI；`trans_*` 主动拒绝 → ILLI，两个异常用不同 helper，不得混淆。
2. **op 值换算**：0628 经验是「op 值由 `op[7:3]:op[2:0]` 拼合」，v5 须逐行对照附录 A/`opcodes.yaml` 换算，不得自行推断。
3. **MISC 嵌套解码**：子表 op 必须用 `ha` 继续解码，不得把整个子表当单一指令。
4. **存根策略**：所有存根 `gen_exception_illegal()` 并 `return true`，唯一例外 `swym`（NOP）。
5. **不修改 CPUState**：字段布局由 `QEMU-003t` 固定。
6. **`make build-qemu` 必须 PASS**：patch 顺序 apply 后 ninja 干净编译。

## 参考

- DADAO-0628：`.work/DADAO-0628/code-agent/tasks/DL-014a-qemu-decodetree.md`
- DADAO-0628：`.work/DADAO-0628/components/qemu/patches/series`
- 本项目：`.tao/knowledge/contract-isa.md` §2、附录 A；`contracts/opcodes.yaml`；`contracts/legality_rules.yaml`
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

1. `components/qemu/patches/0002-dadao-decodetree.patch` 存在且干净 apply；`series` 已加入
2. `insn.decode` 字段声明正确；M1 全部 opcode（含 6 张 MISC 子表）均有 pattern，与 `contracts/opcodes.yaml` 的 `mask`/`value` 一致
3. 每条 pattern 有对应 `trans_*` 函数，无遗漏
4. 未命中 → UNDI、`trans_*` 拒绝 → ILLI，二者分离
5. `swym` 为 NOP；其余存根触发 ILLI
6. `make build-qemu` PASS；任意指令仍触发 ILLI（与 `QEMU-003t` 行为一致）
7. 完成区含真实构建输出与 `grep` 证据；未自行 commit

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
