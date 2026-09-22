# LLVM-014t: ELF `e_flags` 修复（`DADAOELFObjectWriter` 未设置对象格式版本）

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-003t`（triple 注册）、`LLVM-006t`（AsmParser/CodeEmitter，`.o` 产出链）、`LLVM-015m`
**状态**：待开始

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `.tao/knowledge/adr-0003-object-abi.md`（§D1：ELF 头字段期望值）
  - `.tao/knowledge/contract-elf.md`（ELF 合约）
  - `.work/source/llvm-project/llvm/lib/Target/DADAO/MCTargetDesc/`（`DADAOELFObjectWriter` 源码）
- 输出：
  - 新补丁 `components/llvm-project/patches/0008-*.patch` + `components/llvm-project/patches/series` 更新
  - 验证用例（lit 或等价机械检查）
  - 完成区附真实输出
- 约束：
  - **只改 `e_flags` 的产出**，不动其它 ELF 字段（`EI_CLASS`/`EI_DATA`/`e_machine`/`EI_OSABI` 均已符合 ADR-0003，见 `INTEG-003t` 核对结果）
  - 不改 `tests/vectors/isa/*.yaml`

## 背景（完整）

### 问题（`INTEG-003t` 发现，2026-09-22）

`INTEG-003t` 的跨模块接口核对脚本（`tools/integ/check_interface_alignment.py`）报出**唯一 FAIL**：

```
$ .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj x.s -o x.o
$ readelf -h x.o
  Class: ELF64
  Data:  2's complement, big endian
  OS/ABI: UNIX - System V
  Machine: <unknown>: 0xda0
  Flags:  0x0                      # ← ADR-0003 §D1 要求 0x00000001
```

**根因**：`DADAOELFObjectWriter` 未 override `getEFlags()`（在 `components/llvm-project/patches/*` 与 `.work/source/llvm-project/llvm/lib/Target/DADAO/` 中 `grep getEFlags` **零命中**），`e_flags` 默认为 0。

**为何要修**：ADR-0003 §D1 规定 `e_flags = 0x00000001`（bits 0–7 = 对象/ABI 格式版本，M1 = 1；bits 8–31 保留必须为 0），并明确 **consumer 必须拒绝** `e_flags ≠ 1`、版本未知或保留位非 0 的对象（ADR-0003 L55/L120）。当前产出的 `.o` 会被合规 consumer 拒绝，属**契约不符**。

**影响面**：M1 影响为零（QEMU 走 flat binary，无消费者读 `e_flags`），但须修复以符合 ADR-0003。

### 设计（提案，须经用户确认后固化）

1. **D1**：在 `DADAOELFObjectWriter` 中 override `getEFlags()`，返回 **`0x00000001`**（即 ADR-0003 §D1 的 M1 对象/ABI 格式版本；bits 8–31 自然为 0）。
2. **D2**：补丁编号 **`0008`**（现有 `0001`–`0007`）；更新 `series`。
3. **D3**：新增**机械验证**（lit 或等价脚本），断言 `.o` 的 `e_flags == 0x00000001`；验证工具若为 `llvm-readobj` 且**未在构建目标内**，须按先例（`llvm-objcopy`/`not`）加入 `Makefile` 的 `build-mc` ninja 目标，并在完成区说明。
4. **D4**：验证后，`INTEG-003t` 的核对脚本第 1 类 `e_flags` 项应转为 **PASS**（可复跑 `tools/integ/check_interface_alignment.py` 佐证）。

> 备选（未采用）：不改产出、改为修订 ADR-0003 放宽 `e_flags` 要求 —— 与 ADR-0003 既有决策（版本字段用于前向兼容拒绝）冲突，且 ADR 已 `Accepted`，改动需走 ADR 修订流程。

## 交付物

- `components/llvm-project/patches/0008-*.patch`（`DADAOELFObjectWriter::getEFlags()` override）+ `series` 更新
- 验证用例（`tests/lit/MC/Dadao/` 或 `tools/llvm/` 下脚本），机械断言 `e_flags == 0x00000001`
- 完成区附真实输出（含 `readelf`/等价工具的前后对比）

## 已知坑 / 结论

1. **只改 `e_flags`**：其它 ELF 字段已符合 ADR-0003（`INTEG-003t` 已核对 4/5 项 PASS），不要顺手改动。
2. **工具可用性**：若用 `llvm-readobj`，先确认其在 `.work/build/llvm/bin/` 且**在构建目标内**；若不在，按先例加入 Makefile（同 `llvm-objcopy`/`not`），否则干净构建下验证会失败（**教训**：`LLVM-013t` 因 `not` 未入目标导致干净构建 19/21）。
3. **补丁生成流程**：`.work/source/llvm-project` 树 amend → `git format-patch` 覆盖到 `components/llvm-project/patches/NNNN-*.patch`；**不得手工追加 hunk**；校验：临时 worktree 依序 `git am 0001`→`0008` 干净 + 落地 tree 与源树 HEAD tree 一致。
4. **反例门控**：验证必须能失败——回退 `getEFlags()`（或改为返回 `0x02`）时，新增验证必须 FAIL。
5. **跨模块佐证**：`tools/integ/check_interface_alignment.py` 第 1 类 `e_flags` 项由 FAIL → PASS 是**独立佐证**（期望值来自 ADR-0003，非从实现反推）。

## 参考

- `.tao/tasks/integ/INTEG-003t-跨模块接口对齐.md`（发现现场 + 核对清单 + 完成区）
- `docs/integ-interface-alignment.md`（第 1 类 ELF 接口核对）
- `.tao/knowledge/adr-0003-object-abi.md`（§D1、L31/L39/L55/L120）
- `.tao/knowledge/contract-elf.md`
- `.work/source/llvm-project/llvm/lib/Target/DADAO/MCTargetDesc/`

## 验收标准

1. `llvm-mc --triple=dadao-unknown-elf -filetype=obj` 产出的 `.o`，其 `e_flags == 0x00000001`（机械验证，含 bits 8–31 为 0）
2. 其它 ELF 头字段不变（`EI_CLASS=2`/`EI_DATA=2`/`e_machine=0x0DA0`/`EI_OSABI=0`）
3. `make build-mc` PASS；`llvm-lit tests/lit/MC/Dadao/` 0 failures
4. `python3 tools/llvm/check_lit_bytes.py` exit 0；`python3 tools/llvm/test_encoding_oracle.py` 全 PASS
5. **独立佐证**：`python3 tools/integ/check_interface_alignment.py` 的 `e_flags` 项 **PASS**（该脚本总体仅剩 0 个 FAIL，EXIT 0）
6. **反例门控**：回退/改错 `getEFlags()`（如返回 `0x02`）时新增验证 **FAIL**（真实输出 + 还原证据，还原含**重建**）
7. 补丁流程规范：`0008` 无手工 hunk；`series` 正确；临时 worktree `git am 0001`→`0008` clean + tree hash 一致
8. 未修改 `tests/vectors/isa/*.yaml`

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
