# LLVM-021t: swym 编码同步到 0.5.4

**模块**：llvm
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述（跨模块遗留）

SimRISC 0.5.4 修改了 `swym` 编码（`SPEC-023t`/`SPEC-028t`）：
- **格式**：`iiii` → `oiii`
- **立即数**：`immu24` → `immu18`
- **编码位置**：主表 `0111-0xxx/xxx-111`（op=0x77）→ **MISC-AMO `000-xxx/xxx-010`**（op=**0x00**、ha=**0x02**，word=**0x00080000**）

spec/`contracts/opcodes.yaml` 已同步为 `op=0x00, ha=0x02`，但 **LLVM 侧未同步**：

```
.work/source/llvm-project/llvm/lib/Target/DADAO/DADAOInstrInfo.td:566
def swym_iiii : DADAOIiii<"swym"> { let op = 0x77; ... }   # ← 旧
```

后果：`tools/llvm/check_lit_bytes.py` 报 **2 处 no-match**（`iiii_jump.s` 的 swym 字节 `0x77000000`/`0x7700002A` 在 opcodes.yaml 中无匹配）。

**注**：`check_lit_bytes.py` **不在 `make check` 依赖链中**，故 `make check` 仍绿——属校验覆盖缺口（见验收）。

## 修改内容

### 1. LLVM TableGen：`DADAOInstrInfo.td`

- `swym_iiii`（`DADAOIiii`，op=0x77，24 位 imm）→ 改为 **`oiii` 格式、18 位 imm、op=0x00 + ha=0x02**
  - 参考同类 `oiii` 定义（如 `illi`/`fence`）
- 同步 `DADAOInstrFormats.td`（如需格式定义）
- 更新 `components/llvm-project/patches/`（按 `docs/spec/component-patching.md`：**裸 `git diff`**，一文件一补丁）

### 2. `tools/llvm/check_lit_bytes.py` / lit / 字节 oracle

- 更新 swym 相关期望字节（`0x00080000` 等）
- `tests/lit/MC/Dadao/iiii_jump.s`（及含 swym 的 lit）改为新语法/新字节
- `tools/llvm/test_encoding_oracle.py`（若含 swym）

### 3. 校验覆盖

- 将 `tools/llvm/check_lit_bytes.py` **接入 `make check`**（或说明为何不接入，并确保其被某处门控）

## 约束

- 可改 TableGen（用户 2026-09-28 放宽，见 LLVM-019t）
- **命令缺失/构建失败 → 停下报告，禁止自行安装/下载**
- 完成后 `make check` EXIT=0

## 验收标准

1. LLVM `swym` 定义 = 0.5.4（`oiii`、18 位、op=0x00/ha=0x02）
2. `echo "swym 0" | llvm-mc -triple=dadao-unknown-elf -show-encoding` = `0x00080000`（对照 `opcodes.yaml`）
3. `tools/llvm/check_lit_bytes.py` **EXIT=0**（无 no-match）
4. 反汇编 `0x00080000` → `swym 0`
5. 补丁格式合规（每份恰 1 个 `diff --git`）
6. `make check` EXIT=0

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