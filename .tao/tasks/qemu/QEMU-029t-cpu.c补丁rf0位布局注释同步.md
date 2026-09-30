# QEMU-029t: `cpu.c.patch` 的 rf0 位布局注释同步（ADR-0012 D6）

**模块**：qemu
**项目里程碑**：M1→M2
**依赖**：`SPEC-060t`（已 Accepted，ADR-0012 D6 落地）
**状态**：待开始

## 问题

`components/qemu/patches/target/dadao/cpu.c.patch` 的 rf0 复位注释块仍写**旧位布局**（缺口 `rela.si` 无关，纯注释漂移）：

```
+    /* rf0 = FCSR reset value (per ADR-0004 D2, derived from SimRISC-00 §浮点状态寄存器)
+     * Bits [63:51] = fo format Quiet NaN = 0xFFF (read-only)
+     * Bits [50:32] = SBZ = 0                     ← 旧
+     * Bits [31:22] = ft format Quiet NaN = 0x1FF (read-only)
+     * Bits [21:18] = SBZ = 0                     ← 旧
+     * Bits [17:16] = rounding mode = 0 (RNE, reset default)   ← 旧
+     * Bits [15:5]  = SBZ = 0                     ← 旧
+     * Bits [4:0]   = exception status = 0 (reset)
+     *
+     * rf0 = (0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_7FC0_0000
+     */
```

`SPEC-060t` 已把 spec/合约/adr-0004 改为新布局（`[50..34]`/`[33..32]`/`[21..5]`），本补丁注释未同步 ⇒ 载体间不一致。

## 修改内容（**仅 `components/qemu/patches/target/dadao/cpu.c.patch`**）

注释块**逐行替换**为：

```
+    /* rf0 = FCSR reset value (per ADR-0004 D2, derived from SimRISC-00 §浮点状态寄存器)
+     * Bits [63:51] = fo format Quiet NaN = 0xFFF (read-only)
+     * Bits [50:34] = SBZ = 0
+     * Bits [33:32] = rounding mode = 0 (RNE, reset default)
+     * Bits [31:22] = ft format Quiet NaN = 0x1FF (read-only)
+     * Bits [21:5]  = SBZ = 0
+     * Bits [4:0]   = exception status = 0 (reset)
+     *
+     * rf0 = (0xFFF << 51) | (0x1FF << 22) = 0x7FF8_0000_7FC0_0000
+     */
+    env->rf[0] = DADAO_RESET_RF0;
```

**行数变化**：字段行 7 → 6（`-1`）⇒ 必须是**整文件新增补丁**，hunk 头 `@@ -0,0 +1,270 @@` → **`@@ -0,0 +1,269 @@`**（`git apply --check` 会校验，务必同步）。

## 约束

- **只改 `cpu.c.patch`**；`cpu.h.patch` 的 `DADAO_RESET_RF0` 值与其「rf0 = FCSR」注释**无位号、不改**。
- **纯注释改动**：去注释后的正文必须**逐字不变**（`DADAO_RESET_RF0` 值、代码语义均不变）。
- **不做 QEMU 重建**（注释不影响产物）；但 `check-patch-tree` 的 **apply 检查**必须通过（对 pinned base `c3d48b7d1e…` 的 scratch index；该检查已激活）。
- 命令缺失/失败 → **停下报告**；反例注入须**可复原**。

## 验收标准

1. **注释已更新**：补丁中 `[50:34]`/`[33:32]`/`[21:5]` 齐全；`[50:32]`/`[21:18]`/`[17:16]`/`[15:5]` **无命中**（`grep` 证据）。
2. **hunk 头一致**：`@@ -0,0 +1,269 @@`；且 `269` == 补丁中 `+`（含 `+++` 行以外的正文）行数（给出计数命令与输出）。
3. **补丁仍可应用**：`python3 tools/infra/check_patch_tree.py` → `67 patches OK` **EXIT=0**。
4. **反例门控（真实 FAIL）**：在 `/tmp/opencode/QEMU-029t/` 副本中把 hunk 头改回 `@@ -0,0 +1,270 @@`（行数不一致）→ `check_patch_tree.py` **FAIL** 并给出真实 stderr（`git apply` 报错）；另一例：删掉 `+` 前缀行使其与头不符 → 同样 FAIL。复原后 EXIT=0。
5. **纯注释证明**：对改前/改后补丁各取 `+` 正文、**剥离 C 注释**后 `diff` → **空**（给出命令与输出）。
6. **值未变**：`grep DADAO_RESET_RF0 components/qemu/patches/target/dadao/cpu.h.patch` 与原值 `0x7FF800007FC00000ULL` 一致；`cpu.h.patch` **无 diff**。
7. **门控**：`make check` **EXIT=0**（用 `cmd > log 2>&1; rc=$?` 形式贴真实退出码）；另跑 `python3 tools/integ/check_interface_alignment.py` → **80/80 EXIT=0**（其 `2.ADR` 含 QEMU 复位相关项，须仍绿）。
8. **未触其它文件**：`git diff --name-only` = 该 1 个补丁 + 任务文件（逐项对齐）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
