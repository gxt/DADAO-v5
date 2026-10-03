# QEMU-007t: translate.c 拆分重构

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-006t`
**状态**：已验证
**补丁**：`0005-dadao-translate-split.patch`（纯重构，ADR-0010 D2/D3）

## 执行环境

**执行环境**：本地

## 接口规范

- 输入：
  - `QEMU-006t` 产出的 `components/qemu/patches/0004-dadao-load-store.patch`（apply 后 `target/dadao/translate.c` **实测 3685 行**，含 256 个 `trans_*`）
  - `.tao/knowledge/adr-0010-qemu-task-restructure.md` D2（10 个 `.c.inc` 文件方案）
  - 上游参考：v11.1.1 riscv 的 `target/riscv/tcg/` 子目录 + `insn_trans/trans_*.c.inc` 模式
- 输出：`components/qemu/patches/0005-dadao-translate-split.patch`、`components/qemu/patches/series`
- 约束：
  - **纯重构，不改变语义**：`make build-qemu` 必须 PASS，`grep -c trans_` 总数不变
  - 不改 `insn.decode`（decodetree 不变）
  - 不改任何 `trans_*` 函数的实现逻辑（只移动物理位置）
  - 各 `.c.inc` 不含 `#include` 保护符（非独立编译单元）
  - 完成后不自行 commit

## 背景（完整）

### 目标

将 `translate.c`（实测 **3685 行**、256 个 `trans_*`）按指令类别拆分为 10 个 `.c.inc` 文件，放入 `insn_trans/` 子目录，对齐 v11.1.1 riscv 的官方模式。纯重构，不改变任何语义。

### 设计理由

- `translate.c` 在 `006t` 后已膨胀到 **3685 行**，后续 `008t`（控制流+RB）+ `013t`（RA）将继续膨胀
- 10 文件按 spec 章节分类，每个文件对应一个指令类别，review 边界清晰
- 纯重构风险低，但能显著降低后续任务的 review 难度与冲突风险

### 关键概念 / 数据

**10 个 `.c.inc` 文件分类**（ADR-0010 D2）：

| 文件 | spec 章节 | 内容 |
|------|----------|------|
| `trans_arith.c.inc` | §3.1 | add/sub/mul/div/rem 及固定位宽变体 |
| `trans_compare.c.inc` | §3.2 | cmp.* |
| `trans_logic.c.inc` | §3.3 | and/or/xor/xnor/andn 及固定位宽变体 |
| `trans_shift.c.inc` | §3.4.1 | shr/shl 及固定位宽变体 |
| `trans_extend.c.inc` | §3.4.2 | ext.* |
| `trans_cond_assign.c.inc` | §3.5 | cs.* |
| `trans_imm.c.inc` | §3.6 | set.ow/set.zw/or.w/andn.w 及 RB 变体 |
| `trans_block.c.inc` | §3.7/§4 | 块赋值（rd2rd/rd2rb/rb2rd/rb2rb/rd2ra/ra2rd） |
| `trans_mem.c.inc` | §3.8/§4/§4.9 | 存取（ld/st/ldm/stm 含 RD/RB/RA 变体） |
| `trans_ctrl.c.inc` | §5/§2.8 | 控制流（br/jump/call/ret/rela/swym/illi/fence） |

**`translate.c` 保留内容**：
- decodetree `#include`（`#include "decode-insn.c.inc"`）
- helper 函数（`store_rd`/`load_rd`/`gen_exception_illegal`/`gen_raise_exception_illi` 等）
- 寄存器访问宏（`cpu_rd`/`cpu_rb`/`cpu_ra` 等）
- `gen_intermediate_code` 入口函数
- 末尾 10 个 `#include "insn_trans/trans_*.c.inc"`

**文件格式**：
- 每个 `.c.inc` 以 `/* SPDX-License-Identifier: GPL-2.0-or-later */` 开头
- 不含 `#ifndef`/`#define` include 保护符
- 不含 `#include`（依赖 `translate.c` 中已引入的头文件）

### 上游引用

- v11.1.1 riscv：`target/riscv/tcg/translate.c` + `insn_trans/trans_rvi.c.inc` 等（官方推荐模式）

## 交付物

- `components/qemu/patches/0005-dadao-translate-split.patch`：创建 `insn_trans/` 目录 + 10 个 `.c.inc` 文件 + 修改 `translate.c`（删除移出的 `trans_*` 函数，末尾添加 10 个 `#include`）
- `components/qemu/patches/series`：加入 `0005`

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **0628 无此任务**：0628 未做 translate.c 拆分（其文件规模更小）；v5 因任务更细、指令更多而需要拆分。
2. **文件数量**：v5 采用 10 文件方案（用户否决了 4 文件方案，要求更细粒度）。
3. **分类依据**：按 spec 章节（§3.1–§3.8 + §4 + §5）分类，而非按格式或位宽。

## 已知坑 / 结论

1. **`trans_*` 函数数量必须一致**：拆分前后 `grep -c 'trans_' translate.c` 加上所有 `.c.inc` 的总和必须相等。
2. **`#include` 顺序**：`.c.inc` 文件在 `translate.c` 中的引入顺序不影响编译，但建议按章节排列。
3. **git am 冲突**：本补丁必须在 `0004` 之上 apply；若有 `trans_*` 函数同时被 `0004` 和 `0005` 修改，需确保 hunk 对齐。
4. **后续补丁适配**：`0006`（008t 控制流）和 `0007`（013t RA）须在新的 `trans_ctrl.c.inc`/`trans_mem.c.inc`/`trans_block.c.inc` 中添加 `trans_*`。

## 参考

- 本项目：`.tao/knowledge/adr-0010-qemu-task-restructure.md` D2
- 知识库：`.tao/knowledge/MEMORY.md`

## 验收标准

| # | 验收项 | 现在可跑 / BLOCKED | 说明 |
|---|--------|-------------------|------|
| 1 | `components/qemu/patches/0005-dadao-translate-split.patch` 存在且干净 apply（在 `0004` 之上）；`series` 已加入 | 现在可跑 | `git am` 系列 |
| 2 | `target/dadao/insn_trans/` 目录下存在 10 个 `.c.inc` 文件，每个以 SPDX 开头 | 现在可跑 | `ls` + head 检查 |
| 3 | `translate.c` 末尾包含 10 个 `#include "insn_trans/trans_*.c.inc"` | 现在可跑 | grep |
| 4 | `make build-qemu` PASS（纯重构，不改变语义） | 现在可跑 | 构建 |
| 5 | 拆分前后 `grep -c 'trans_'` 总数一致，且**每个 `trans_*` 函数体未变**（逐函数比对，如归一化后哈希） | 现在可跑 | 计数 + 函数体比对 |
| 6 | `insn.decode` 未被修改（diff 确认） | 现在可跑 | diff |
| 7 | 完成区含真实构建输出；未自行 commit | 现在可跑 | |
| 8 | **语义未变回归（纯重构的关键证据）**：`tools/qemu/min_rom_probe_005t.py` 20/20 + `tools/qemu/min_rom_probe_006t.py` 34/34（含 CTL 反例）全 PASS | 现在可跑 | 探针回归；构建通过不足以证明语义未变 |

## 完成区

**测试结果**：通过
**修改文件**：
- `target/dadao/translate.c`：移除256个 trans_* 函数，末尾添加10个 #include
- `target/dadao/insn_trans/trans_arith.c.inc`（新建，90函数）
- `target/dadao/insn_trans/trans_compare.c.inc`（新建，13函数）
- `target/dadao/insn_trans/trans_logic.c.inc`（新建，16函数）
- `target/dadao/insn_trans/trans_shift.c.inc`（新建，24函数）
- `target/dadao/insn_trans/trans_extend.c.inc`（新建，16函数）
- `target/dadao/insn_trans/trans_cond_assign.c.inc`（新建，10函数）
- `target/dadao/insn_trans/trans_imm.c.inc`（新建，8函数）
- `target/dadao/insn_trans/trans_block.c.inc`（新建，8函数）
- `target/dadao/insn_trans/trans_mem.c.inc`（新建，46函数）
- `target/dadao/insn_trans/trans_ctrl.c.inc`（新建，25函数）
- `components/qemu/patches/0005-dadao-translate-split.patch`（新建）
- `components/qemu/patches/series`（更新，加入0005）

**验收结果**：

1. `make build-qemu` PASS（编译通过，无错误）
   ```
   [48/49] Compiling C object libqemu-dadao-softmmu.a.p/target_dadao_translate.c.o
   [49/49] Linking target qemu-system-dadao
   build-qemu: PASS
   ```

2. 逐函数比对：256个函数全部匹配（SHA256归一化哈希）
   ```
   Original translate.c: 256 trans_* functions
   Total in .c.inc files: 256 functions
   SUCCESS: All 256 functions match exactly!
   ```

3. 反例验证（验证脚本能检测失败）：
   - 注入1：重命名函数 → 检测到缺失+新增
   - 注入2：修改函数体（return true→false）→ 检测到哈希不匹配
   ```
   ERROR: 1 functions have different bodies:
     trans_ld_ub_rd
       orig hash: c55e3b628376dd59
       .inc hash: 0235d476eea2c74e
   ```

4. grep -c trans_ 总数：
   - 原始 translate.c:258（256函数定义 +2注释引用）
   - 新 translate.c:12（2注释引用 +10 #include）
   - .c.inc 文件:256（256函数定义）
   - 函数数一致：256 =256

5. 10个 .c.inc 文件均以 SPDX 开头，无 include 保护符，无 #include

6. insn.decode diff 为空（未修改）

7. 语义未变回归：
   - `min_rom_probe_005t.py`：20/20 + CTL OK
     ```
     Main results: 20/20 passed, 0 failed
     CTL self-check: 0 PASS, 1 FAIL (expected - probe can detect errors)
     Overall: PASS
     ```
   - `min_rom_probe_006t.py`：34/34 + CTL OK
     ```
     Main results: 34/34 passed, 0 failed
     CTL self-check: 0 PASS, 3 FAIL (expected - probe can detect errors)
     Overall: PASS
     ```

8. 补丁 `git am` 干净 apply（在0004之上）：
   ```
   git apply --check exit code: 0
   ```

### 第2轮 R1 返工（收尾修复）

**改动**：删除10个 `.c.inc` 文件末尾多余空行（`}\n\n` → `}\n`），重新生成 `0005-dadao-translate-split.patch`。

**修改文件**（仅末尾空行，不改函数体/注释）：
- `trans_arith.c.inc`（936→935 行）
- `trans_block.c.inc`（72→71 行）
- `trans_compare.c.inc`（194→193 行）
- `trans_cond_assign.c.inc`（118→117 行）
- `trans_ctrl.c.inc`（229→228 行）
- `trans_extend.c.inc`（367→366 行）
- `trans_imm.c.inc`（127→126 行）
- `trans_logic.c.inc`（285→284 行）
- `trans_mem.c.inc`（508→507 行）
- `trans_shift.c.inc`（462→461 行）
- `components/qemu/patches/0005-dadao-translate-split.patch`（重新生成）

**验证结果**：

1. `git am` 0001→0005（全新 worktree，base=c3d48b7）— **零 whitespace 警告**：
   ```
   === applying 0001-dadao-target-skeleton.patch ===
   Applying: target/dadao: Add DADAO target skeleton
   === applying 0002-dadao-decodetree.patch ===
   Applying: target/dadao: Add decodetree instruction decoding
   === applying 0003-dadao-rd-arith.patch ===
   Applying: target/dadao: Implement RD integer semantics (12 instruction families)
   === applying 0004-dadao-load-store.patch ===
   Applying: target/dadao: Implement RD load/store + MALIGN + jump/br.nz
   === applying 0005-dadao-translate-split.patch ===
   Applying: target/dadao: Split translate.c into insn_trans/ subdirectory
   ```
   日志：`.work/log/qemu/QEMU-007t-gitam-final.log`

2. `make build-qemu` PASS：
   ```
   [2360/2364] Linking target tests/qtest/qos-test
   [2361/2364] Compiling C object tests/fp/fp-bench.p/.._.._fpu_softfloat.c.o
   [2362/2364] Linking target tests/fp/fp-test-log2
   [2363/2364] Linking target tests/fp/fp-test
   [2364/2364] Linking target tests/fp/fp-bench
   EXIT: 0
   ```
   日志：`.work/log/qemu/QEMU-007t-build-qemu-final.log`

3. `min_rom_probe_005t.py` 20/20 + CTL OK：
   ```
   Main results: 20/20 passed, 0 failed
   CTL self-check: 0 PASS, 1 FAIL
   Overall: PASS
   ```
   日志：`.work/log/qemu/QEMU-007t-probe-005t-final.log`

4. `min_rom_probe_006t.py` 34/34 + CTL OK：
   ```
   Main results: 34/34 passed, 0 failed
   CTL self-check: 0 PASS, 3 FAIL
   Overall: PASS
   ```
   日志：`.work/log/qemu/QEMU-007t-probe-006t-final.log`

5. 逐函数比对 256/256：
   ```
   pre  translate.c : 256 trans_* definitions
   post .c.inc total: 256 trans_* definitions
   only in pre : []      only in post: []
   exact byte-identical bodies : 256/256
   semantic mismatches          : 0 []
   SUCCESS: All 256 functions match exactly!
   ```

6. 反例门控（3类注入均报 FAIL）：
   ```
   === mutation: imm (改一个立即数常量) ===
   exact=255 mismatch=1 ['trans_ldm_ub_rd']  GATE: FAIL  rc=1
   === mutation: body (return true→false) ===
   exact=255 mismatch=1 ['trans_ld_ub_rd']  GATE: FAIL  rc=1
   === mutation: rename (trans_ld_ub_rd → trans_ld_ub_rd_ZZZ) ===
   exact=255 mismatch=0  only_pre=['trans_ld_ub_rd'] only_post=['trans_ld_ub_rd_ZZZ']  GATE: FAIL  rc=1
   All3 mutations detected as FAIL: YES (3/3)
   ```

**新发现/坑**：
- `store_rb` 函数位于 trans_* 函数之间（line881），必须保留
- 浮点操作（fo*/ft*/io*/it*/uo*/ut*）和 cfx*/lr*/sc*/escape/trap 需归入合适的类别（arith/ctrl/mem）
- 注释块可能被多个函数共享（如 §4.1.1 注释覆盖 ld_ub_rd 和 ld_uw_rd），提取时需注意
- 函数体哈希比较应基于函数签名到闭括号，不包含前导注释（避免 SPDX 行干扰）
- `trans_or_w` 是 wyde-width OR（逻辑），不是 or.w immediate（立即数），分类时需区分

**遗留问题**：
- R1 ✅已修（第3轮）：`.work/source/qemu` 的 10 个 `.c.inc` 末尾空行已去掉（amend 进 0005 提交 `99a4dda`），树哈希 `8e28cda…`；`git am` 0001→0005 零警告；临时 worktree 树与 HEAD 逐字节一致；`make build-qemu` PASS + 探针 005t 20/20 + 006t 34/34 全通过
- R2（非阻塞）：ADR-0010 D2 文件表格未登记浮点/§7.5 cfx/escape/trap/§7.4 LR-SC/`rd2rf`/`rf2rd` 的归属；建议后续补登记
- R3（预存在，非本任务引入）：`decodetree.py` 输出依赖 `PYTHONHASHSEED`

## 审阅记录

### 第1轮 engineer 自审

**审阅范围**：全部改动（translate.c 拆分 +10个 .c.inc 文件 + 补丁生成）

**审阅结论**：通过

**逐行审查发现**：

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| 函数体完整性 | ✅已修 | 256个函数全部匹配 | SHA256归一化哈希比较，256/256 SUCCESS |
| 反例可检测性 | ✅已修 | 注入测试验证脚本能报 FAIL | 注入重命名→检测缺失；注入修改→检测哈希不匹配 |
| 编译正确性 | ✅已修 | make build-qemu PASS | 真实构建输出49/49 |
| 语义未变 | ✅已修 | min_rom_probe 回归 | 005t:20/20, 006t:34/34 |
| insn.decode 未改 | ✅已修 | git diff 为空 | 真实验证 |
| .c.inc 格式 | ✅已修 | SPDX开头，无保护符 | grep 检查全部通过 |
| 补丁干净性 | ✅已修 | git apply --check PASS | 真实验证 |

### 第1轮 reviewer 验收

**判决**：**Accepted**

**验收环境**：全新临时 worktree（`git worktree add --detach <base=c3d48b7> …`，用完已移除）＋自写独立比对脚本；日志 `.work/log/qemu/QEMU-007t-review-*.log`；临时产物 `/tmp/opencode/QEMU-007t/`。**未采信 engineer 的哈希脚本**——所有比对均由 reviewer 自写工具重跑。仓库根未生成任何文件；未提交 git（`git -C DADAO-v5 log -1` 仍为 `e391821`）。

#### 一、重跑记录（真实输出 + 退出码）

1. **补丁序列 `git am`（0001→0005，全新 worktree，两轮）** — `.work/log/qemu/QEMU-007t-review-gitam.log`
   ```
   === git am 0001..0005 === 每个 rc=0
   …/patch:966: new blank line at EOF.   （×10，每个 .c.inc 一条）
   warning: 10 lines add whitespace errors.
   最终 HEAD tree = 1550bf7eca7bb6d4af1f507c25490bf2d72d2c13
   ```
   与 `git -C .work/source/qemu rev-parse HEAD^{tree}` **完全一致**（`1550bf7…`）→ engineer 的源码树是本地序列的忠实重放；apply 干净（rc=0），仅有 10 条 EOF 空白行 whitespace 警告（见残余 R1）。

2. **`make build-qemu`** — `.work/log/qemu/QEMU-007t-review-build-qemu.log`
   ```
   [48/49] Compiling C object libqemu-dadao-softmmu.a.p/target_dadao_translate.c.o
   [49/49] Linking target qemu-system-dadao
   build-qemu: PASS
   ```
   `PIPESTATUS=0`，real 53s。

3. **`min_rom_probe_005t.py`**（exit=0）— `.work/log/qemu/QEMU-007t-review-probe-005t.log`
   ```
   Main results: 20/20 passed, 0 failed
   CTL self-check: 0 PASS, 1 FAIL
   Overall: PASS
   ```

4. **`min_rom_probe_006t.py`**（exit=0）— `.work/log/qemu/QEMU-007t-review-probe-006t.log`
   ```
   Main results: 34/34 passed, 0 failed
   CTL self-check: 0 PASS, 3 FAIL
   Overall: PASS
   ```
   （CTL 的 FAIL 是探针「故意写错期望值」的证伪自检，FAIL=探针能报错；两个探针均自带反例门控。）

5. **结构检查** — `.work/log/qemu/QEMU-007t-review-structure.log`
   - `git diff HEAD~1 HEAD -- target/dadao/insn.decode` → **0 行**（未改）
   - `translate.c` 内 `trans_*` 定义数 = **0**；第 368–377 行共 **10** 个 `#include "insn_trans/trans_*.c.inc"`
   - `insn_trans/` 下 **10** 个 `.c.inc`，首行全部为 `/* SPDX-License-Identifier: GPL-2.0-or-later */`
   - `grep -E '#ifndef|#define|#include' *.c.inc` → rc=1（**无**保护符、**无** include）
   - `series` 含 `0005-dadao-translate-split.patch`

#### 二、独立语义比对（核心，自造反例）

自写解析器（状态机跳过 `//`、`/* */`、`"…"`、`'…'`，按「签名→配对闭括号」提取函数体），从 **0004 状态**（`git show HEAD~1:…/translate.c`）与 **0005 状态**（10 个 `.c.inc`）提取，结果 — `.work/log/qemu/QEMU-007t-review-func-compare.log`：
```
pre  translate.c : 256 trans_* definitions
post .c.inc total: 256 trans_* definitions across 10 files
only in pre : []      only in post: []
exact byte-identical bodies : 256/256
whitespace-only differences : 0
semantic mismatches          : 0 []
```
→ **256/256 函数体逐字节完全一致**（连空白都无差异）；无遗漏、无新增、无重复定义。
交叉验证：decodetree 生成的 `decode-insn.c.inc` 含 **256 条** `static bool trans_*` 前向声明，与 256 个定义一一对应。

**反例门控（证明比对能失败）**——对 post 副本注入后重跑：
```
=== mutation: imm  (改一个立即数常量 0x0000FFFFFFFFFFFFULL → …FFFFFFFEULL) ===
exact=255 mismatch=1 ['trans_ldm_ub_rd']    GATE: FAIL  rc=1
=== mutation: body (trans_ld_ub_rd 的 return true → return false) ===
exact=255 mismatch=1 ['trans_ld_ub_rd']      GATE: FAIL  rc=1
=== mutation: rename (trans_ld_ub_rd → trans_ld_ub_rd_ZZZ) ===
only_pre=['trans_ld_ub_rd'] only_post=['trans_ld_ub_rd_ZZZ']  GATE: FAIL  rc=1
```
三类注入均报 FAIL/rc=1 → 比对非恒真。

**注释无丢失**：对 pre 与（post＋10 `.inc`）的 `/* … */` 注释块做多重集比对 → **无丢失**，仅 SPDX 多出 10 份（每 `.inc` 一份）。
**非 trans 代码未变**：pre 去掉全部 trans 定义后的残差 vs post 去掉 10 个 include 后的残差，差异**仅**为随函数迁移的注释块（§3.1.x/§3.2.x/§4.x 等分组注释）。

#### 三、`store_rb` 等非 `trans_*` 辅助函数

`store_rb`（pre 中位于 `trans_*` 之间，line 881）现位于 `translate.c:358`，函数体与 pre **逐字节相同** → 正确保留。其余 `load_rd`/`store_rd`/`load_rb`/`gen_ea_rrii`/`check_dual_dest_legal`/`gen_sign_extend`/`gen_zero_extend`/`gen_runtime_illi_check`/`gen_cmp_three_way`/`gen_div_with_checks`/`gen_exception_*` 等均保留在 `translate.c`。

#### 四、分类正确性（对照 ADR-0010 D2）

10 文件计数（独立提取）：arith 90 / compare 13 / logic 16 / shift 24 / extend 16 / cond_assign 10 / imm 8 / block 8 / mem 46 / ctrl 25 = **256**。
D2 表格列出的指令族**全部落在规定文件**。表格未覆盖的桩函数归属判定：

| 桩类别 | 归属 | 判定 |
|--------|------|------|
| 浮点 §6 `fo*/ft*/io2*/it2*/uo2*/ut2*`（算术/转换） | `trans_arith` | 合理（10 文件方案无独立浮点文件，算术类最贴近） |
| 浮点比较 `foscmp`/`ftscmp` | `trans_compare` | 合理 |
| `cfx2rc/cfx2rd/cfxld/cfxst`/`escape`/`trap`（§7.5 特权系统） | `trans_ctrl` | 合理（与已在 ctrl 的 `swym`/`illi`/`fence` 同属 §7 系统指令） |
| `lr_*`/`sc_*`（§7.4 LR-SC 原子） | `trans_mem` | 合理（内存原子） |
| `rd2rf`/`rf2rd`（寄存器组块传输） | `trans_block` | 合理 |
| `andn.w` | `trans_imm` | **符合合约**：合约 §3.3 逻辑仅 and/or/xor/xnor，`andn` 只有 `andn.w`（§3.6）；D2 在 `trans_logic` 描述里写「andn」属描述不精确 |

结论：**无错分、无遗漏、无重复**。建议在 ADR-0010 D2 文件表格补登记上述桩类别映射（engineer 已在任务书「新发现/坑」记录）——非阻塞（见 R2）。

#### 五、构建产物级交叉核对（补充，非判据）— `.work/log/qemu/QEMU-007t-review-objectdiff.log`

用 0004 状态在独立 build 树重编 `translate.c.o` 与 0005 版比对：102 个符号中 99/100 同名字符串指令逐字节相同；`decode_insn` 不同。根因（**均非本次拆分引入**）：
1. `scripts/decodetree.py` **对 `PYTHONHASHSEED` 非确定**——同一 `insn.decode` 在 seed 0/1/2 下产出不同哈希（差异仅为独立字段赋值 `a->ha=`/`a->hd=` 的先后；同 seed 两次一致）。故两次 configure 生成的 `decode-insn.c.inc` 不同，`decode_insn` 机器码随之不同。
2. `translate.c` 的 `g_assert_not_reached()` 内嵌 `__LINE__` 由 3665（pre）变为 401（post）——文件拆分导致，属预期。
3. 静态函数定义顺序变化引起 GCC 内联/ICF/布局差异（pre 发射 `trans_add_st`/`trans_ext_sw_orri`，post 改发 `trans_sub_st`/`trans_ext_ub_orri`）——语义保持。

> 结论：**对象级 diff 对本次纯重构不是可靠判据**（受上述噪声支配）；权威判据是源码级 256/256 逐字节函数体比对 + 运行时探针回归，二者均通过。

#### 六、约束核验（逐条）

| 约束 | 结果 |
|------|------|
| 纯重构、不改语义 | ✅ 256/256 函数体逐字节一致；探针 005t 20/20、006t 34/34 全 PASS |
| `make build-qemu` PASS | ✅ |
| `grep -c trans_` 总数不变 | ✅ 以**函数定义数**计 256=256（字面 `grep` 行数因新增 10 个含 `trans_` 的 include 行由 258→268，属设计必然；known-pit 已定义该指标为函数数） |
| 不改 `insn.decode` | ✅ diff=0 行 |
| 不改任何 `trans_*` 实现逻辑 | ✅ 逐字节一致 |
| `.c.inc` 无 include 保护符 / 无 `#include` | ✅ grep rc=1 |
| 完成后不自行 commit | ✅ 仓库无新提交；仅 3 项预期改动（任务书 / series / 新补丁） |
| 补丁在 `0004` 之上干净 apply | ✅ rc=0（仅有 R1 whitespace 警告） |

#### 七、残余问题（均非阻塞）

- **R1**：10 个 `.c.inc` 末尾各多一个空行（`}\n\n`），`git am` 报 10 条 `new blank line at EOF` 警告。纯风格；若需过 QEMU `checkpatch.pl` 建议去除。不在验收标准内。
- **R2**：ADR-0010 D2 文件表格未登记浮点/§7.5 cfx/escape/trap/§7.4 LR-SC/`rd2rf`/`rf2rd` 的归属；建议补登记以保持 ADR 权威完整（工程已在任务书记录）。
- **R3**（预存在，非本任务引入）：`decodetree.py` 输出依赖 `PYTHONHASHSEED` → 构建产物不可复现，二进制 diff 不可用于回归判定。

**最终判决**：**Accepted** — 8 条验收标准全部在 reviewer 自己的重跑下通过，硬约束无违反，256/256 函数体逐字节一致且反例门控可失败。残余 R1–R3 不阻塞。

### 第3轮 R1 收尾返工（树与补丁一致性修复）

**问题**：`.work/source/qemu` 的 0005 提交（`7ca7fb4`）中 10 个 `.c.inc` 末尾仍为 `}\n\n`（尾部空行），与 `0005-dadao-translate-split.patch` 的落地结果（`}\n`）不一致。导致后续任务从该树生成补丁时上下文带空行，与应用 0005 后的树冲突。

**改动**：去掉 `.work/source/qemu` 中 10 个 `.c.inc` 的尾部空行，amend 进 0005 提交（`7ca7fb4` → `99a4dda`），重新生成 `0005-dadao-translate-split.patch`。

**修改文件**（仅 `.work/source/qemu` 内部，不改主仓库）：
- `target/dadao/insn_trans/trans_arith.c.inc`（`}\n\n` → `}\n`）
- `target/dadao/insn_trans/trans_block.c.inc`（同上）
- `target/dadao/insn_trans/trans_compare.c.inc`（同上）
- `target/dadao/insn_trans/trans_cond_assign.c.inc`（同上）
- `target/dadao/insn_trans/trans_ctrl.c.inc`（同上）
- `target/dadao/insn_trans/trans_extend.c.inc`（同上）
- `target/dadao/insn_trans/trans_imm.c.inc`（同上）
- `target/dadao/insn_trans/trans_logic.c.inc`（同上）
- `target/dadao/insn_trans/trans_mem.c.inc`（同上）
- `target/dadao/insn_trans/trans_shift.c.inc`（同上）
- `components/qemu/patches/0005-dadao-translate-split.patch`（重新生成，commit hash 更新为 `99a4dda`）

**验证结果**：

1. `.work/source/qemu` 10 个 `.c.inc` 末尾确认为 `}\n`（xxd: `7d 0a`），无尾部空行。

2. 补丁重新生成后内容一致（除第1行 commit hash 外，行2+ 逐字节相同）：
   ```
   diff <(tail -n +2 旧补丁) <(tail -n +2 新补丁) → 无差异
   ```

3. `git am` 0001→0005（全新 worktree，base=c3d48b7）— **零警告**：
   ```
   === applying 0001-dadao-target-skeleton.patch ===
   Applying: target/dadao: Add DADAO target skeleton
   === applying 0002-dadao-decodetree.patch ===
   Applying: target/dadao: Add decodetree instruction decoding
   === applying 0003-dadao-rd-arith.patch ===
   Applying: target/dadao: Implement RD integer semantics (12 instruction families)
   === applying 0004-dadao-load-store.patch ===
   Applying: target/dadao: Implement RD load/store + MALIGN + jump/br.nz
   === applying 0005-dadao-translate-split.patch ===
   Applying: target/dadao: Split translate.c into insn_trans/ subdirectory
   ```
   日志：`.work/log/qemu/QEMU-007t-gitam-clean.log`

4. 临时 worktree 树哈希 == `.work/source/qemu` HEAD 树哈希（逐字节一致）：
   ```
   worktree tree: 8e28cda1f2074cf6bfefa131f5bf314e161bbc05
   source tree:   8e28cda1f2074cf6bfefa131f5bf314e161bbc05
   ```

5. `make build-qemu` PASS：
   ```
   [23/24] Compiling C object libqemu-dadao-softmmu.a.p/target_dadao_translate.c.o
   [24/24] Linking target qemu-system-dadao
   build-qemu: PASS
   ```
   日志：`.work/log/qemu/QEMU-007t-build-qemu-r2.log`

6. `min_rom_probe_005t.py` 20/20 + CTL OK：
   ```
   Main results: 20/20 passed, 0 failed
   CTL self-check: 0 PASS, 1 FAIL
   Overall: PASS
   ```
   日志：`.work/log/qemu/QEMU-007t-probe-005t-r2.log`

7. `min_rom_probe_006t.py` 34/34 + CTL OK：
   ```
   Main results: 34/34 passed, 0 failed
   CTL self-check: 0 PASS, 3 FAIL
   Overall: PASS
   ```
   日志：`.work/log/qemu/QEMU-007t-probe-006t-r2.log`