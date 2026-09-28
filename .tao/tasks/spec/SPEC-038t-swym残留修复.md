# SPEC-038t: swym 旧编码残留修复

**模块**：spec
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

SimRISC 0.5.4 将 `swym` 改为 **`oiii` 格式、18 位立即数、op=0x00/ha=0x02（word=0x00080000）**。
`spec/`、`contracts/opcodes.yaml`、LLVM、QEMU decode、lit、向量**均已正确**，但以下位置**仍为旧编码**（`iiii`/24 位/op=0x77）：

| 文件 | 位置 | 旧内容 |
|------|------|--------|
| `.tao/knowledge/contract-isa.md` | L233 | QFC 表把 swym 放在 `0111-0xxx` |
| 同上 | L1061 | `### §13.1 占位指令 swym（iiii 格式）` |
| 同上 | L1068 | 「后 **24 位**立即数为时延参数」 |
| 同上 | L1269 | `| 0x77 | 0111-0111 | iiii | swym | ...` |
| `tests/scripts/build_test_binary.py` | L127-129 | `encode_swym()` 返回 `0x77000000` |
| `tests/scripts/verify_harness_dump.py` | L392 | 写 `0x77000000` 作 swym NOP |
| `tools/qemu/min_rom_probe_005t.py` | L9,157 | `op=0x77` |
| `tools/spec/generate_opcodes.py` | L150 | 注释举例 `swym-iiii` |

（历史记录**不改写**：`changelog.md`、`deferred.md` 历史条目、已完成任务文件。）

## 修改内容

1. **`contract-isa.md`**：swym 改为 `oiii`/18 位/`op=0x00,ha=0x02`；QFC 表位置改 MISC-AMO `000-010`；§13.1 标题与描述更新；附录行 `0x77` → `0x00`（或按 §2 QFC 口径）
2. **`tests/scripts/build_test_binary.py`**：`encode_swym()` → `0x00080000`（注释同步 `oiii, op=0x00, ha=0x02`）
3. **`tests/scripts/verify_harness_dump.py`**：`0x77000000` → `0x00080000`
4. **`tools/qemu/min_rom_probe_005t.py`**：swym op=0x77 → 新编码
5. **`tools/spec/generate_opcodes.py`**：注释举例更新

## 约束

- **只改编码/描述**，不改语义
- **历史记录不改写**（changelog/已完成任务文件）
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0；`check_qfc_coverage` 0 差异

## 验收标准

1. `contract-isa.md` 中 swym = `oiii`/18 位/`op=0x00`（无 `0x77`/`iiii` 残留）
2. `build_test_binary.py`/`verify_harness_dump.py`/`min_rom_probe_005t.py` 的 swym = `0x00080000`
3. 全仓库（排除 `.work`/`.git`/0.5.3 归档/历史记录）无旧 swym（`swym.*iiii`/`0x77.*swym`）
4. `make check` EXIT=0；`check_qfc_coverage` 0 差异
5. 反例验证

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）