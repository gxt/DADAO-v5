# 跨模块接口对齐核对清单（INTEG-003t）

**日期**：2026-09-22（返工修订）
**状态**：核对完成
**核对脚本**：`tools/integ/check_interface_alignment.py`

---

## 汇总（实跑数据）

| 类别 | 总项数 | PASS | FAIL | MANUAL |
|------|--------|------|------|--------|
| 1. LLVM MC ELF emitter ↔ QEMU loader | 5 | 4 | 1 | 0 |
| 2. ADR-0003 ↔ ADR-0004 | 26 | 26 | 0 | 0 |
| 3. testcases schema ↔ QEMU harness | 41 | 41 | 0 | 0 |
| 4. opcodes.yaml ↔ LLVM/QEMU 交叉核对 | 8 | 8 | 0 | 0 |
| **合计** | **80** | **79** | **1** | **0** |

---

## 类别 1：LLVM MC ELF emitter ↔ QEMU loader（5 项）

QEMU 消费 flat binary（不解析 ELF），ELF 头字段仅由 LLVM MC emitter 设置。

| # | 接口 | 来源 | LLVM 侧取值 | 判定 | 证据 |
|---|------|------|-------------|------|------|
| 1.1 | `e_machine = EM_DADAO = 0x0DA0` | ADR-0003 §D1 | `EM_DADAO = 0x0DA0` | ✅一致 | `0002-dadao-target-skeleton.patch` L235 |
| 1.2 | `EI_CLASS = ELFCLASS64 (2)` | ADR-0003 §D1 | `Is64Bit_=true` | ✅一致 | `MCELFObjectTargetWriter(Is64Bit_=true, ...)` |
| 1.3 | `EI_DATA = ELFDATA2MSB (2)` | ADR-0003 §D1 | `IsLittleEndian = false` | ✅一致 | `DADAOMCAsmInfo` 构造函数 |
| 1.4 | `EI_OSABI = ELFOSABI_NONE (0)` | ADR-0003 §D1 | `ELF::ELFOSABI_NONE` | ✅一致 | `createDadaoELFObjectWriter(ELF::ELFOSABI_NONE)` |
| 1.5 | `e_flags = 0x00000001` | ADR-0003 §D1 | **未设置**（无 `getEFlags` override，默认 0） | ❌不一致 | 脚本解析 `getEFlags()` 返回常量：未找到 override ⇒ 默认返回 0。ADR-0003 §D1 要求 `0x00000001`（bits 0–7 = 版本号 1，bits 8–31 = 0）。 |

### 发现的真实不一致

**[1.5] e_flags 未设置**：
- **LLVM 侧**：`DADAOELFObjectWriter` 继承 `MCELFObjectTargetWriter`，未 override `getEFlags()`，默认返回 0。
- **合约期望**：ADR-0003 §D1 要求 `e_flags = 0x00000001`（M1 对象/ABI 格式版本 = 1）。
- **影响**：LLVM 产出的 `.o` 文件 `e_flags = 0`，按 ADR-0003 consumer 规则应被拒绝（版本 0 = legacy DADAO object）。QEMU 不受影响（消费 flat binary）。
- **建议处置**：在 `DADAOELFObjectWriter` 中 override `getEFlags()` 返回 `0x00000001`。仅影响 LLVM 侧。

---

## 类别 2：ADR-0003 ↔ ADR-0004（26 项）

| # | 接口 | 来源 | 取值 | 判定 |
|---|------|------|------|------|
| 2.1 | machine_name = `dadao-m1` | ADR-0004 §D2.3 | `MACHINE_TYPE_NAME("dadao-m1")` | ✅ |
| 2.2 | RAM_BASE = `0xffff_0000_0000` | ADR-0004 §D1 | `0xffff00000000ULL` | ✅ |
| 2.3 | RAM_SIZE = 16 MiB | ADR-0004 §D1 | `(16 * 1024 * 1024)` | ✅ |
| 2.4 | EXIT_PORT_BASE = `0xffff_8000_0000` | ADR-0004 §D3 | `0xffff80000000ULL` | ✅ |
| 2.5 | EXIT_PORT_SIZE = 8 B | ADR-0004 §D3 | `8` | ✅ |
| 2.6 | ROM_BASE = `0xffff_ffff_0000` | ADR-0004 §D1 | `0xffffffff0000ULL` | ✅ |
| 2.7 | ROM_SIZE = 64 KiB | ADR-0004 §D1 | `(64 * 1024)` | ✅ |
| 2.8 | RESET_PC = ROM_BASE | ADR-0004 §D2.1 | `DADAO_ROM_BASE` | ✅ |
| 2.9 | dual_image (-bios + -kernel) | ADR-0004 §D2.3 | 缺少时报错 | ✅ |
| 2.10–2.17 | EXIT_PASS/UNMAPPED/ILLI/UNDI/RASOF/RASUF/MALIGN/IALIGN | ADR-0004 §D5.8 | 0x00/0x87–0x8D | ✅×8 |
| 2.18 | harness BINARY_BASE = RAM_BASE | ADR-0004 §D1 | `0xFFFF_0000_0000` | ✅ |
| 2.19 | harness EXIT_PORT = EXIT_PORT_BASE | ADR-0004 §D3 | `0xFFFF_8000_0000` | ✅ |
| 2.20–2.26 | harness FAULT_NAMES 与 ADR-0004 §D5.8 一致 | ADR-0004 §D5.8 | 0x87–0x8D 全匹配 | ✅×7 |

---

## 类别 3：testcases schema ↔ harness（41 项）

| 子类 | 项数 | 判定 | 说明 |
|------|------|------|------|
| schema 定义字段（14 项） | 14 | ✅×14 | mnemonic/insn/format/class/encoding/input_state/spec_cite + 7 可选字段 |
| harness 精确消费模式（13 项） | 13 | ✅×13 | `case.get("X")` / `case["X"]` 精确匹配 |
| encoding sub-fields（2 项） | 2 | ✅×2 | word/reserved |
| fault 类型定义（7 项） | 7 | ✅×7 | ILLI/UNDI/MALIGN/IALIGN/RASOF/RASUF/UNMAPPED |
| class 定义（5 项） | 5 | ✅×5 | encoding/legality/semantic/boundary/overlap |

---

## 类别 4：opcodes.yaml ↔ LLVM/QEMU 交叉核对（8 项）

| # | 检查项 | 判定 | 证据 |
|---|--------|------|------|
| 4.1 | opcodes.yaml 存在 | ✅ | 256 条 |
| 4.2 | 条目数 | ✅ | 总计 256, M1 内 178 |
| 4.3 | 结构完整性 | ✅ | 全部 256 条有 insn/mnemonic/format/op/mask/value |
| 4.4 | mask/value 内部自洽 | ✅ | 全部 256 条 `(value & mask) == value` |
| 4.5 | **LLVM lit ↔ opcodes.yaml** | ✅ | `check_lit_bytes.py` 53 patterns OK（**真调用**） |
| 4.6 | **QEMU trans ↔ opcodes.yaml** | ✅ | `check_qemu_trans.py --strict` 256/256（**真调用**） |
| 4.7 | LLVM lit # OBJ: patterns | ✅ | 53 patterns |
| 4.8 | QEMU trans_* 定义数 | ✅ | 256 trans_* 函数 |

---

## 反例门控验证（3 组，全绿基线 80/80/0 EXIT=0 下注入）

全绿基线构造：副本中给 LLVM patch 加 `getEFlags(){ return 0x00000001; }` → 80/80/0 EXIT=0。

| 反例 | 注入方式 | 预期 | 实际输出 | 还原后 |
|------|---------|------|---------|--------|
| ① e_flags 错值 | `getEFlags()` 返回 `0x00000002` | FAIL | `1.ELF e_flags FAIL: getEFlags() 返回 0x2，期望 0x1`；80/79/1；**EXIT=1** | 还原后 80/80/0 EXIT=0 |
| ② opcodes 跨模块不一致 | ld.ub value `0x10000000`→`0x11000000`（mask 不变，内部自洽） | FAIL | `4.Opcodes LLVM lit ↔ opcodes.yaml FAIL`；80/79/1；**EXIT=1** | 还原后 80/80/0 EXIT=0 |
| ③ harness 消费移除 | `case.get("class")`→`case.get("__REMOVED_CLASS__")` | FAIL | `3.Schema harness 消费 class FAIL: 未找到精确消费模式`；80/79/1；**EXIT=1** | 还原后 80/80/0 EXIT=0 |

所有反例均在全绿基线上注入（排除既有 e_flags FAIL 干扰），每组 EXIT=1 由注入本身导致。仓库 `git diff --name-only -- components/ contracts/ tests/ .tao/knowledge/` 为空。
