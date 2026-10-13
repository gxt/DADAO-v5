# LLVM-014t: ELF `e_flags` 修复（`DADAOELFObjectWriter` 未设置对象格式版本）

**模块**：llvm
**项目里程碑**：M1
**依赖**：`LLVM-003t`（triple 注册）、`LLVM-006t`（AsmParser/CodeEmitter，`.o` 产出链）、`LLVM-015m`
**状态**：已验证

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

### 设计（用户已于 2026-09-22 确认，D1–D4 生效）

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

**测试结果**：全部通过
- `make build-mc` PASS（含 `llvm-readobj` 新目标）
- `llvm-lit tests/lit/MC/Dadao/` 22/22 PASS（21 原有 + 1 新增 `e_flags.s`）
- `python3 tools/llvm/check_lit_bytes.py` exit 0（53 patterns OK）
- `python3 tools/llvm/test_encoding_oracle.py` 68/68 PASS
- `python3 tools/llvm/validate_instrinfo.py` 0 errors, 0 warnings
- `python3 tools/integ/check_interface_alignment.py` 80/80/0 EXIT 0
- `make check` PASS

**修改文件**：
- `.work/source/llvm-project/llvm/lib/Target/DADAO/MCTargetDesc/DADAOTargetStreamer.h`（新建，24 行）
- `.work/source/llvm-project/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCTargetDesc.cpp`（修改：+28 行，`git numstat`）
- `components/llvm-project/patches/0008-dadao-elf-e_flags.patch`（新建）
- `components/llvm-project/patches/series`（修改：+1 行）
- `Makefile`（修改：`build-mc` 目标加入 `llvm-readobj`）
- `tests/lit/MC/Dadao/lit.cfg.py`（修改：+2 行，`%llvm_readobj` 替换）
- `tests/lit/MC/Dadao/e_flags.s`（新建，lit 测试）
- `tools/integ/check_interface_alignment.py`（修改：e_flags 检查只在 diff `+` 非注释代码行搜索，支持标识符回查常量定义）

**验收结果**：

1. **readelf 前后对比**：
```
修复前: Flags:  0x0
修复后: Flags:  0x1
其它字段不变: Class=ELF64, Data=big endian, Machine=0xda0, OS/ABI=UNIX - System V
```

2. **llvm-readobj 输出**：
```
Flags [ (0x1)
  0x1
]
```

3. **D4 独立佐证**：
```
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
全部机械可判定项 PASS。
```

4. **反例门控**：
```
注入: EF_DADAO_ABIV1 = 0x00000002
结果: FAIL: DADAO-MC :: e_flags.s (Flags [ (0x2) ≠ expected 0x1)
还原: sed 恢复 0x00000001 + make build-mc PASS + 22/22 PASS
git diff --name-only: llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCTargetDesc.cpp（注入时非空）
```

5. **补丁流程校验**：
```
worktree git am 0001→0008: ALL PATCHES APPLIED CLEAN
tree hash 一致: 0e058573eb70da9e57db6995d6caef6bbe8985da
```

**新发现/坑**：
1. **实现路径差异**：任务书设计 D1 提到「在 `DADAOELFObjectWriter` 中 override `getEFlags()`」，但 LLVM 的 `MCELFObjectTargetWriter` 基类**没有** `getEFlags()` 虚方法。正确路径是通过 `RegisterObjectTargetStreamer` 注册 `DADAOTargetStreamer`，在其构造函数中调用 `MCELFStreamer::getWriter().setELFHeaderEFlags()`。这是 LLVM 所有 target 设置 e_flags 的标准模式（CSKY、ARM、RISC-V、LoongArch 等均如此）。
2. **llvm-readobj 未在构建目标**：原 `Makefile` 的 `build-mc` ninja 目标不含 `llvm-readobj`，需手动加入（教训同 LLVM-013t 的 `not`）。
3. **check_interface_alignment.py 路径适配**：原脚本只识别 `getEFlags()` override 模式，需扩展为同时识别 `setELFHeaderEFlags(CONST)` 模式。检测须限定在 diff `+` 非注释代码行（排除 commit message 和 C/C++ 注释行），否则注释中的字面量可造成假阴性/假阳性。标识符实参须回查常量定义。
4. **git amend 陷阱**：若当前 HEAD 已是某个 patch 的 commit，`git commit --amend` 会将新改动合并进该 patch 而非新建 commit。正确做法是 `git reset --soft HEAD` 后 `git commit` 创建独立 commit。
5. **patch 中的 UTF-8 字符**：patch 注释可能包含 em dash（U+2013, `\xe2\x80\x93`）等非 ASCII 字符，字符串替换时须使用精确字节，不能用 ASCII 近似（如用 `-` 代替 `–`）。

**遗留问题**：无

## 审阅记录

**确认记录（2026-09-22，用户）**：D1–D4 **全部确认**。备选（修订 ADR-0003 放宽 `e_flags`）**未采用**。

### 第 1 轮 engineer 自审（2026-09-22）

**审查范围**：DADAOTargetStreamer.h、DADAOMCTargetDesc.cpp、e_flags.s、lit.cfg.py、Makefile、check_interface_alignment.py、0008 patch、series

**发现**：

| # | finding | 处置 | 改了什么 | 复验证据 |
|---|---------|------|---------|---------|
| 1 | D1 设计写「override getEFlags()」但 LLVM 基类无此虚方法 | ❌不修 | 任务书 D1 是高层描述，实际实现遵循 LLVM 标准模式（TargetELFStreamer + setELFHeaderEFlags），效果等价 | llvm-readobj 确认 Flags=0x1；check_interface_alignment.py 80/80 PASS |
| 2 | `static_cast<MCELFStreamer &>(S)` 若 streamer 非 ELF 类型会 UB | ❌不修 | RegisterObjectTargetStreamer 的回调仅在 ELF object emission 路径调用，此时 streamer 必为 MCELFStreamer（CSKY/ARM/RISC-V 均用同模式） | 所有 22 个 lit test + make check 均 PASS |
| 3 | `#include "llvm/BinaryFormat/ELF.h"` 未实际使用 ELF:: 常量 | ❌不修 | EF_DADAO_ABIV1 是自定义常量不引用 ELF::，但保留 include 无害且符合 LLVM 惯例（其它 target 也 include） | 编译无 warning |
| 4 | e_flags.s 的 CHECK 行假设 Flags 输出格式固定 | ⏸延后 | llvm-readobj 的 Flags 输出格式在 LLVM 版本间稳定，但若升级可能需调整 | 当前版本 22/22 PASS |

**判决**：所有 finding 已处置或有充分理由不修。可标「待验收」。

### 第 1 轮 reviewer 验收（2026-09-22）

**Needs Revision**：`check_interface_alignment.py` 存在假阴性——脚本搜索整个 patch 文本（含 commit message），commit message 中的 `setELFHeaderEFlags(0x1)` 在代码常量改为 `0x02` 后仍命中，报假 PASS。

### 第 2 轮 engineer 返工（2026-09-22）

**修复**：e_flags 检测改为只在 diff 的 `+` 新增代码行搜索（排除 `+++` 文件头行和 commit message）。标识符实参（如 `EF_DADAO_ABIV1`）回查同一 patch 代码内的常量定义。

**4 组注入验证**（副本 `/tmp/opencode/LLVM-014t/inject-patches/`）：

| 注入 | 代码 | commit msg | 结果 |
|------|------|-----------|------|
| 常量→`0x02` | `EF_DADAO_ABIV1 = 0x00000002;` | `(0x1)` 不变 | **FAIL** ✓ |
| call→`(0x02)` | `setELFHeaderEFlags(0x00000002)` | 不变 | **FAIL** ✓ |
| 基线 `0x01` | `EF_DADAO_ABIV1 = 0x00000001;` | 不变 | **PASS** ✓ |
| 删除 eflags 代码 | 无 setELFHeaderEFlags | 不变 | **FAIL** ✓ |

还原证据：md5 `d324a74be54eb8c868af3b5936f4fda0` 一致。

**完成区订正**：`DADAOMCTargetDesc.cpp` 行数由 +31 修正为 **+28**（`git numstat` 为准）。

## 审阅记录

**确认记录（2026-09-22，用户）**：D1–D4 **全部确认**。备选（修订 ADR-0003 放宽 `e_flags`）**未采用**。

### 第 1 轮 reviewer 验收（2026-09-22）

**判决：Needs Revision**（唯一阻断项：`tools/integ/check_interface_alignment.py` 的 `e_flags` 新增检测路径存在**假绿/假阴性**，见 §4/§9）。

**范围**：任务书、ADR-0003 §D1、`0008` patch、`series`、`Makefile`、`lit.cfg.py`、`e_flags.s`、`check_interface_alignment.py`；期望值取自 ADR-0003 §D1（`e_flags=0x00000001`，bits 8–31=0），非从实现反推。

#### 1. 独立验证 `e_flags`（重跑，非采信）

```
$ .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj x.s -o x.o      # exit 0
$ readelf -h x.o
  Class: ELF64                     <- EI_CLASS=2
  Data:  2's complement, big endian<- EI_DATA=2
  OS/ABI: UNIX - System V          <- EI_OSABI=0
  Machine: <unknown>: 0xda0        <- e_machine=0x0DA0
  Flags:  0x1                      <- 期望 0x00000001  OK
$ xxd -s48 -l4 x.o
  00000030: 0000 0001               <- bits 8-31 = 0  OK
$ .work/build/llvm/bin/llvm-readobj -h x.o
  Flags [ (0x1)
    0x1
  ]
```

**「修复前」由我独立复现**（非采信 INTEG-003t）：`git checkout HEAD~1 -- DADAOMCTargetDesc.cpp` + 删 `DADAOTargetStreamer.h` + 重建 `llvm-mc`（exit 0）→ `Flags: 0x0`，其它字段完全一致；恢复 `git reset --hard HEAD` + 重建 → `Flags: 0x1`。**结论：`0x0 -> 0x1` 确由本补丁造成，其它字段不变。**

#### 2. D1 机制偏离判定：**偏离正当**

```
$ grep -rn "getEFlags" .work/source/llvm-project/llvm/include/llvm/MC/
  （无命中）
$ MCELFObjectTargetWriter.h
  （无 getEFlags；ELFObjectWriter 提供 getELFHeaderEFlags()/setELFHeaderEFlags()）
$ grep -rn setELFHeaderEFlags llvm/lib/Target/ | grep -v DADAO
  Mips/ARM/RISCV/CSKY/LoongArch/PowerPC/Sparc/AVR/Hexagon/AMDGPU 均用此路径
```
`MCELFObjectTargetWriter` **确无** `getEFlags()` 虚方法 → 任务书 D1「override `getEFlags()`」在 LLVM 上不可实现；engineer 改用 `setELFHeaderEFlags(0x1)`（经 `RegisterObjectTargetStreamer`）是 LLVM 标准模式，设置整个 32 位 `e_flags=1`（bits 8–31=0），与 D1 意图**语义等价**。engineer 已在完成区「新发现/坑 #1」如实记录，**未静默改设计** → 通过。（建议：任务书 D1 表述后续顺手订正为「经 TargetStreamer 设 `e_flags=1`」，非阻断。）

#### 3. 干净构建可复现（`llvm-readobj`）

移走 `.work/build/llvm/bin/llvm-readobj` → `make build-mc`（`exit 0`；`real 13m12s`；末行 `build-mc: PASS`）→ `bin/llvm-readobj` 被重建（原 319408248 B → 新 319400352 B）。备份副本已删除。**通过。**

#### 4. 专项：`check_interface_alignment.py` 修改 —— **假阴性，需返工**

`git diff` 新增路径 (b) `setELFHeaderEFlags(0x...)`。脚本对**全部 patch 拼接文本**做 `search`，而 patch 文本**包含 commit message**。实测 `patch_content` 首个命中是**提交信息**第 10 行 `setELFHeaderEFlags(0x1)`，**不是代码**（代码是 `setELFHeaderEFlags(EF_DADAO_ABIV1)`，实参为标识符，正则本就匹配不到）。

在**真实 patch 文件**上注入（每次注入后 `md5sum`/`diff` 确认还原为 `d324a74be54eb8c868af3b5936f4fda0`）：

| 注入 | 代码 | commit msg | 脚本结果 |
|------|------|-----------|---------|
| 基线 | `=0x1` / call `EF_DADAO_ABIV1` | `(0x1)` | PASS，`EXIT 0`，detail=`setELFHeaderEFlags(0x1)` |
| inj1：常量 `EF_DADAO_ABIV1 = 0x00000002` | **0x02** | `(0x1)` | **PASS，EXIT 0** ← 假阴性 |
| inj4：call 改字面量 `setELFHeaderEFlags(0x02)` | **0x02** | `(0x1)` | **PASS，EXIT 0** ← 假阴性 |
| inj2：常量 0x02 + msg 也改 `(0x02)` | 0x02 | `(0x02)` | FAIL，`EXIT 1`（`期望 0x1`） |
| inj3：去掉 msg 中数值括号 | 0x1 | 无数值 | FAIL，`EXIT 1`（「未设置 e_flags」） |

**判定：不是「阈值放宽」，但**是**检测面失效——脚本读的是提交信息文字，而非决定产出 `e_flags` 的代码常量。**用户要求的两条注入（`setELFHeaderEFlags(0x02)` ⇒ FAIL）**未达成**：只要能匹配到提交信息里的 `(0x1)`，即使代码把 `e_flags` 产成 `0x02`，脚本仍报 PASS。这使验收第 5 条的「独立佐证」不成立（假绿）。**违反** AGENTS.md「验证脚本必须能失败」「reviewer 必须主动证伪」的精神。

#### 5. D4 佐证真实输出

```
$ python3 tools/integ/check_interface_alignment.py ; echo $?
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
全部机械可判定项 PASS。
0
```
`e_flags` 项确为 PASS。**独立性削弱程度（reviewer 判定）**：(a) 检查器由**同一 agent**修改；(b) 更严重的是 §4 的假阴性——`e_flags` 项 PASS **源自 commit message 文本**而非代码取值，故该 PASS **不可采信**，不能作为「独立佐证」。（真实佐证由 §1 readelf/readobj + §6 lit 反例门控承担，二者均可靠。）

#### 6. 反例门控（新 lit）：**真实可失败**

注入源码 `EF_DADAO_ABIV1 = 0x00000002`（`git diff --name-only` 非空：`.../DADAOMCTargetDesc.cpp`）→ `ninja llvm-mc` → `.work/build/llvm/bin/llvm-lit tests/lit/MC/Dadao/`：
```
FAIL: DADAO-MC :: e_flags.s
  e_flags.s:14:10: error: CHECK: expected string not found in input
  # CHECK: Flags [ (0x1)
  <stdin>:23:2: note: possible intended match here
   Flags [ (0x2)
  Passed: 21 ; Failed: 1   (lit exit 1)
```
还原：`git reset --hard HEAD` + `ninja llvm-mc`（**含重建**）→ `Flags: 0x1`、lit **22/22**、`git status` clean、HEAD tree `0e058573eb70da9e57db6995d6caef6bbe8985da`。
> 教训（本轮踩到并已修正）：`git checkout -- <file>` 会从**已污染的 index** 还原，导致「源码看似还原、二进制未变、ninja no work to do、Flags 仍 0x0」；改用 `git reset --hard HEAD` + 重建后复验通过。已在最终状态确认 `git status` clean。

#### 7. 补丁流程与无回归

- `0008` 与 `git -C .work/source/llvm-project format-patch -1 HEAD --stdout` **byte 相同**（md5 `d324a74b...`）→ 无手工 hunk；`series` 顺序 `0001...0008` 正确。
- 临时 worktree（base `6dfe1677a`）依序 `git am 0001->0008`：`EXIT 0`，8 个 patch 全部 `Applying:`，**重放后 tree `0e058573eb70da9e57db6995d6caef6bbe8985da` == 源树 HEAD tree**。worktree 已移除。
- `llvm-lit tests/lit/MC/Dadao/`：22/22 PASS（exit 0）。
- `check_lit_bytes.py`：`53 patterns OK`，exit 0。
- `test_encoding_oracle.py`：`68 passed, 0 failed`，exit 0。
- `validate_instrinfo.py`：`0 errors, 0 warnings`，exit 0。
- `make check`：`repository checks: PASS`，exit 0。
- `git status tests/vectors/`：无改动；`tests/vectors/isa/*.yaml` 未改。OK

#### 8. 完成区一致性与改动范围

- 数字核对：lit 22/22、check_lit_bytes 53、oracle 68、validate 0、check_interface 80/80/0、patch tree hash 均与真实输出一致。**唯一不符**：完成区「`DADAOMCTargetDesc.cpp`（修改：+31 行）」，实际 `git show --numstat` 为 **+28** 行（`0008` 补丁亦为 28）。次要，随返工一并订正。
- D1 机制偏离已如实记录（通过）。
- 改动范围：7 条路径（`0008` 新建、`series`+1、`Makefile` `build-mc` 加 `llvm-readobj`、`lit.cfg.py`+`%llvm_readobj`、`e_flags.s` 新建、源改动 `DADAOMCTargetDesc.cpp`+`DADAOTargetStreamer.h`、`check_interface_alignment.py` 改）。除 §4 那处外，其余均**必要且只涉 `e_flags`**，未动其它 ELF 字段（§1 已核）。

#### 9. 精确返工清单（仅此一处）

**改 `tools/integ/check_interface_alignment.py` 的 `e_flags` 检测（约 L118–161）**：
1. **只在 diff 新增代码行里搜索**，剔除 mail header/commit message 与上下文行：
   ```python
   code = "\n".join(ln[1:] for ln in patch_content.splitlines()
                    if ln.startswith("+") and not ln.startswith("+++"))
   ```
2. **解析实参：数字字面量或标识符常量**。`setELFHeaderEFlags(X)` 的实参为标识符（本任务为 `EF_DADAO_ABIV1`）时，回到同一 patch 代码里解析其定义：
   ```python
   m2 = re.search(r'setELFHeaderEFlags\s*\(\s*([A-Za-z_]\w*|0x[0-9a-fA-F]+|\d+)\s*\)', code)
   if m2:
       arg = m2.group(1)
       if re.fullmatch(r'0x[0-9a-fA-F]+|\d+', arg):
           actual = int(arg, 16) if arg.lower().startswith("0x") else int(arg)
       else:
           cm = re.search(rf'\b{re.escape(arg)}\s*=\s*(0x[0-9a-fA-F]+|\d+)\s*;', code)
           actual = int(cm.group(1), 16) if cm else None   # 找不到定义 ⇒ FAIL
   ```
   （或更强：直接跑 `llvm-mc`+`llvm-readobj` 读真实 `e_flags`；若改动过大，最小修复采用上式。）
   **不得**再从 commit message 匹配数值。
3. **复验（必须做，附真实输出）**：
   - 代码常量改 `0x02`（commit message 不变）⇒ 该项 **FAIL**、`EXIT 1`；
   - call 改字面量 `setELFHeaderEFlags(0x02)`（message 不变）⇒ **FAIL**、`EXIT 1`；
   - 正确 `0x1` ⇒ **PASS**；两条路径都不存在 ⇒ **FAIL**；
   - 还原后 `md5sum`/`git diff` 证明 patch 复原。
4. 顺带订正完成区 `+31 行` → `+28 行`。

**未阻断项**：`e_flags` 修复本体、`e_flags.s`、`Makefile`、`lit.cfg.py`、`0008`/`series`、D1 机制偏离记录——均经验证通过，返工只需处理上述脚本一处。

### 第 2 轮 reviewer 复核（2026-09-22）

**判决：Needs Revision**（第 1 轮阻断项已修复；残留一处**同类假绿边界**——`+` 注释行可遮蔽真实代码，见 §3/§7）。

**结论摘要**：第 1 轮指出的「读 commit message 而非代码」**已修复**——4 组规定注入全部行为正确（§2）。但检测仍在**全部 `+` 行（含注释）**上 `search`，注释行内的字面量可先于真实 call 命中：注释写 `setELFHeaderEFlags(0x1)`、代码实际 `0x02` ⇒ 仍报 **PASS（EXIT 0）**（我实测，§3）。

#### 1. 基线（真实 patch，无注入）

```
$ python3 tools/integ/check_interface_alignment.py ; echo $?
1.ELF  e_flags=0x00000001  PASS  setELFHeaderEFlags(EF_DADAO_ABIV1=0x1)   <- 标识符已正确回查常量
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
0
```
commit message（patch L10 `setELFHeaderEFlags(0x1)`）**不再被匹配**；命中来自代码 `EF_DADAO_ABIV1=0x1`。✔

#### 2. 4 组规定注入（真实 patch 文件；每次注入后 `md5sum` 核对还原 `d324a74be54eb8c868af3b5936f4fda0`）

| # | 注入 | commit msg | 真实输出（`e_flags` 行） | EXIT |
|---|------|-----------|------------------------|------|
| ① | 常量 `EF_DADAO_ABIV1 = 0x00000002` | `(0x1)` 不变 | `FAIL setELFHeaderEFlags(EF_DADAO_ABIV1=0x2)，期望 0x1` | **1** ✔ |
| ② | call 字面量 `setELFHeaderEFlags(0x02)` | `(0x1)` 不变 | `FAIL setELFHeaderEFlags(0x2)，期望 0x1` | **1** ✔ |
| ③ | 基线 `0x00000001` | `(0x1)` | `PASS setELFHeaderEFlags(EF_DADAO_ABIV1=0x1)` | **0** ✔ |
| ④ | 删除 call（仅留常量定义） | `(0x1)` 不变 | `FAIL LLVM patch 未设置 e_flags（…）` | **1** ✔ |

还原证据：4 次注入后均 `cp` 回原文件，`diff -q` ⇒ `IDENTICAL`，`md5sum = d324a74be54eb8c868af3b5936f4fda0`。**第 1 轮假阴性已消除。**

#### 3. 逐行审查 + 边界判定（**残留问题**）

逐行审 `git diff tools/integ/check_interface_alignment.py`：
- `code_lines` = 仅 `+` 行且排除 `+++`（L101–104）→ commit message/mail header 已排除。✔
- 路径 (a) `getEFlags()`、路径 (b) `setELFHeaderEFlags` 均只在 `code_lines` 上 `search`。✔
- 实参为标识符时回查 `\b<arg>\s*=\s*(0x…|\d+)\s*;`（L141–148）；**查不到定义 ⇒ `actual` 保持 `None` ⇒ FAIL**（有 FAIL 路径）。✔
- 两个 `if actual is not None:` 分支分别给 PASS / FAIL，`else` 给 FAIL → 无恒真结构。✔

**但 `search` 不区分「代码语句」与「注释」**，注释行以 `//` 开头仍是 `+` 行。实测两向：

| 边界 | 注入 | 真实结果 | 判定 |
|------|------|---------|------|
| A | 注释（在 call 前）：`+// NOTE: do not use setELFHeaderEFlags(0x02) …`，代码实为 `0x1` | `FAIL setELFHeaderEFlags(0x2)`，**EXIT 1** | **误报 FAIL**（fail-safe，但脆） |
| B | 注释（在 call 前）：`+// ADR-0003 §D1 sets setELFHeaderEFlags(0x1) …`，代码实为 `setELFHeaderEFlags(0x02)` | `PASS setELFHeaderEFlags(0x1)`，**EXIT 0** | **假绿**（同一后果：脚本未读真实代码值） |

边界 B 意味着：只要 patch 的某条 `+` 注释在真实 call 之前**引用了该调用 + 数值字面量**，且该字面量恰为 `0x1`/`0x01`，脚本就会漏判代码已改错。这与第 1 轮被点名的缺陷**后果同类**（检查未落到实现取值），属 AGENTS.md「修复须修一类」覆盖范围，**不可接受**。
（注：现有 `0008` 的 `+` 行中除真实 call 外**无**含 `setELFHeaderEFlags(` 的注释，故当前这份 patch 未触发；但脚本作为长期佐证工具须封住该类。完成区 L109「只在 diff `+` **代码**行搜索」的表述与实际（含注释）不符。）

#### 4. 断言集复核（`ast`）

```
record() 调用总数: 79
第三个实参为字面量状态的分组: {'PASS': 32, 'FAIL': 47}
恒真 assert / 恒真或恒假 if: 无
```
本次改动**仅**触及 `e_flags` 一个块（`git diff` 单一 hunk 区间），该块两条 PASS/FAIL 分支齐备、`else` 必 FAIL → **未引入新的无 FAIL 路径或恒真断言**。

#### 5. D4 真实输出 + 独立性最终判定

```
$ python3 tools/integ/check_interface_alignment.py ; echo $?      # 无管道，真实退出码
总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0
0
```
**独立性最终判定**：相较第 1 轮**显著改善**——`e_flags` PASS 现已来自**代码常量**（`EF_DADAO_ABIV1=0x1`）而非 commit message，**该 PASS 可采信**。但仍有「检查器由同一 agent 修改」的独立性折扣；且在第 1 轮的问题被修掉后，**真实证据链**仍以 §6 的 readelf/readobj 与 `e_flags.s`（真实产物 + FileCheck）为主，`check_interface_alignment.py` 为**佐证**而非主证。

#### 6. `e_flags` 本体 + 补丁流程 + 无回归 + 完成区一致性

- 本体复验：`readelf -h` → `Flags: 0x1`；`llvm-readobj -h` → `Flags [ (0x1) / 0x1 ]`；raw `@48 = 0000 0001`（bits 8–31=0）；`Class=ELF64`/`Data=big endian`/`OS/ABI=UNIX - System V`/`Machine=0xda0` **不变**。✔
- 补丁流程：`0008` 与 `git format-patch -1 HEAD --stdout` **byte 相同**（md5 均 `d324a74b…`）；worktree（base `6dfe1677a`）`git am 000[1-8]-*.patch` **EXIT 0**（8 个 `Applying:`），重放 tree `0e058573eb70da9e57db6995d6caef6bbe8985da` == 源树 HEAD tree；worktree 已移除。✔
- 无回归（均真实退出码）：lit **22/22**（EXIT 0）、`check_lit_bytes` **53 patterns OK**（EXIT 0）、oracle **68/68**（EXIT 0）、`validate_instrinfo` **0 errors/0 warnings**（EXIT 0）、`make check` **PASS**（EXIT 0，`repository checks: PASS`）；`git status tests/vectors/` 无改动，`tests/vectors/isa/*.yaml` 未改。✔
- 完成区一致性：`+31` 已订正为 **+28**（与 `git numstat` 28/24、补丁 28 一致）；其余数字与真实输出一致。唯一不符见 §3 末（L109 表述）。
- 改动范围：仍为 7 条路径，除 `tools/integ/` 那处外均**只涉 `e_flags`**；`check_interface_alignment.py` 本次改动仅 `e_flags` 一个块。✔

#### 7. 精确返工清单（最小改动，一处）

`tools/integ/check_interface_alignment.py` L101–104，把「`+` 行」细化为「`+` 行且**非注释**」：
```python
def _is_comment(s: str) -> bool:
    s = s.strip()
    return s.startswith("//") or s.startswith("/*") or s.startswith("*") or s.startswith("*/")

code_lines = "\n".join(
    ln[1:] for ln in patch_content.splitlines()
    if ln.startswith("+") and not ln.startswith("+++") and not _is_comment(ln[1:])
)
```
（更稳的可选方案：直接对**真实产物**取值——用 `llvm-mc`+`llvm-readobj` 解析 `Flags`；若改动过大，上式即最小修复。**两点说明**：路径 (a) `getEFlags()` 的 `return` 亦同理须在非注释行内匹配；标识符回查常量定义也须在非注释行内。）

**复验（须附真实输出 + EXIT）**：
- 边界 B 重现：注释含 `setELFHeaderEFlags(0x1)` + 代码 `setELFHeaderEFlags(0x02)` ⇒ **必须 FAIL、EXIT 1**；
- 边界 A 重现：注释含 `setELFHeaderEFlags(0x02)` + 代码 `0x1` ⇒ **必须 PASS、EXIT 0**（消除误报）；
- 重跑第 2 轮 §2 的 4 组注入，全部保持 ①②④FAIL / ③PASS；
- 还原后 `md5sum` = `d324a74be54eb8c868af3b5936f4fda0`；
- 顺带把完成区 L109「只在 diff `+` 代码行搜索」订正为「只在 diff `+` **非注释**代码行搜索」。

**未阻断项（本轮已实测通过，无需再动）**：`e_flags` 修复本体（readelf/readobj）、`e_flags.s`（lit 22/22）、`Makefile`、`lit.cfg.py`、`0008`/`series`、补丁流程、无回归、D1 机制偏离记录、完成区 `+28` 订正。若架构师判定「注释行遮蔽」属可接受边界，本轮可作为**已知限制**记录后接受；reviewer 依 AGENTS.md「修复须修一类 / 不许假绿」判定为**应先封堵的同类缺陷**。

### 第 3 轮 engineer 返工（2026-09-22）

**修复**：`code_lines` 提取增加 `_is_comment()` 过滤，排除 C/C++ 注释行（`//`、`/*`、`*`、`*/`）。标识符常量定义搜索同样限定在 `code_lines`（已排除注释）中。

**边界 + 4 组注入验证**（真实 patch 文件，每次注入后 md5 核对还原）：

| # | 注入 | 真实结果 | EXIT | 判定 |
|---|------|---------|------|------|
| 边界 B | 注释 `(0x1)` + 代码 `EF_DADAO_ABIV1 = 0x00000002` | FAIL (EF_DADAO_ABIV1=0x2) | 1 | ✓ |
| 边界 A | 注释 `(0x02)` + 代码 `0x00000001` | PASS (EF_DADAO_ABIV1=0x1) | 0 | ✓ |
| ① 常量 0x02 | 代码 `0x00000002` | FAIL (EF_DADAO_ABIV1=0x2) | 1 | ✓ |
| ② call 字面量 0x02 | `setELFHeaderEFlags(0x00000002)` | FAIL (0x2) | 1 | ✓ |
| ③ 基线 0x01 | 正确值 | PASS (EF_DADAO_ABIV1=0x1) | 0 | ✓ |
| ④ 删除 call | 无 setELFHeaderEFlags | FAIL (not set) | 1 | ✓ |

还原证据：md5 `d324a74be54eb8c868af3b5936f4fda0` 6 次注入后均一致。

**完成区订正**：L109 表述改为「只在 diff `+` **非注释**代码行搜索」。

### 第 3 轮 reviewer 复核（2026-09-22）

**判决：Accepted**（第 2 轮残留的全行注释遮蔽已封堵；对「行尾/内嵌注释」这一**更窄且无实际触发**的残留，判为**可接受的已知限制**，见 §4）。

#### 1. 边界 A/B 复验（真实 patch；每次注入后 `cp` 还原并 `diff -q` ⇒ `IDENTICAL`）

| 用例 | 注入 | 真实输出（`e_flags` 行） | EXIT |
|------|------|------------------------|------|
| **B** | `+// … setELFHeaderEFlags(0x1) …`（call 前）+ 代码 `setELFHeaderEFlags(0x02)` | `FAIL setELFHeaderEFlags(0x2)，期望 0x1` | **1** ✔ |
| **A** | `+// … setELFHeaderEFlags(0x02) …`（call 前）+ 代码 `setELFHeaderEFlags(EF_DADAO_ABIV1)`（`=0x1`） | `PASS setELFHeaderEFlags(EF_DADAO_ABIV1=0x1)` | **0** ✔ |

第 2 轮的两个边界均修正：B 不再假绿、A 不再误报。

#### 2. 4 组规定注入复跑（真实 patch 文件）

| # | 注入 | 真实输出 | EXIT |
|---|------|---------|------|
| ① | 常量 `EF_DADAO_ABIV1 = 0x00000002`（commit msg `(0x1)` 不变） | `FAIL setELFHeaderEFlags(EF_DADAO_ABIV1=0x2)` | **1** ✔ |
| ② | call 字面量 `setELFHeaderEFlags(0x02)`（msg 不变） | `FAIL setELFHeaderEFlags(0x2)` | **1** ✔ |
| ③ | 基线 `0x00000001` | `PASS setELFHeaderEFlags(EF_DADAO_ABIV1=0x1)` | **0** ✔ |
| ④ | 删除 call（仅留常量定义） | `FAIL LLVM patch 未设置 e_flags（…）` | **1** ✔ |

还原证据：4 次注入后 `cp` 回原文件，`diff -q` ⇒ `IDENTICAL`；最终 `md5sum = d324a74be54eb8c868af3b5936f4fda0`。

#### 3. 检测代码逐行审查

`_is_comment()`（L126–130）判定「行首去空白后以 `//`、`/*`、`*`、`*/` 开头」；`code_lines` = `+` 行 ∧ 非 `+++` ∧ 非注释；路径 (a)、(b) 与标识符常量回查**全部**只在 `code_lines` 上搜索；两分支 PASS/FAIL 齐备，`else` 必 FAIL。**与第 2 轮返工清单一致**，未引入额外放宽。

#### 4. 边界判定：**可接受的已知限制**

我进一步注入两向更窄的形态，确认仍有**可实测假绿**（但对本产物无实际触发）：

| 边界 | 注入（均为 `+` 行、且位于真实 call **之前**） | 真实结果 | EXIT |
|------|------|---------|------|
| **C** 行尾注释 | 先行 `+int dummy = 0; // matches W.setELFHeaderEFlags(0x1)` + 代码 `W.setELFHeaderEFlags(0x02);` | `PASS setELFHeaderEFlags(0x1)` | **0**（假绿） |
| **D** 块注释中间行（无前导 `*`） | `+/*` / `+  setELFHeaderEFlags(0x1) is documented here` / `+*/` + 代码 `0x02` | `PASS setELFHeaderEFlags(0x1)` | **0**（假绿） |

**判定：接受为已知限制，非阻断。** 理由：
1. **触发条件苛刻且与本产物无关**：需一条既非全行注释、又精确包含 `setELFHeaderEFlags(<正确值>)` 的 `+` 文本且出现在真实 call 之前。`0008` 的 `+` 行中除真实 call 外**无**任何 `setELFHeaderEFlags(` 文本（`grep` 已核），故检查在当前及可预见产物上不误判。
2. **全行注释（现实中最常见的形态，LLVM 风格块注释亦以 `*` 对齐）已封堵**；C/D 属「刻意构造的误导性注释」，非正常编码产物。
3. **真实回归不会漏网**：`e_flags` 的权威验证是读**真实 `.o`** 的 `e_flags.s`（FileCheck + `llvm-readobj`），其反例门控真实可失败（第 2 轮已实测：改 `0x02` ⇒ lit FAIL/EXIT 1）。`check_interface_alignment.py` 仅作**佐证**，非唯一防线。
4. **避免过度设计**：对 patch 文本做正则无法彻底区分「代码 vs 注释」，零残留的正解是改读产物（设计层改动），非本任务最小修复范畴。本轮返工正是按 reviewer 第 2 轮提出的 `_is_comment` 清单实施，不应再移动球门。
5. 该残留**不构成「为凑绿而放宽」**——当前产物无需依赖它即可 PASS。

> 非阻断建议（不要求本轮处理）：若团队要求零残留，可将 (b) 改为对**真实产物**取值（`llvm-mc`+`llvm-readobj` 解析 `Flags`），或把匹配限定为「赋值/调用语句行」（如要求行内出现 `setELFHeaderEFlags(` 前有 `.` 或 `->` 且行不含 `//`）。请架构师知悉此限制并决定是否登记。

#### 5. 断言集复核（`ast`）

```
record() 调用总数: 79
第三个实参为字面量状态的分组: {'PASS': 32, 'FAIL': 47}
恒真 assert / 恒真或恒假 if: 无
```
本次改动仅触及 `e_flags` 一块（`git diff` 单一 hunk 区间），该块 FAIL 路径齐备 → **未引入新的无 FAIL 路径/恒真断言**。

#### 6. D4 + 本体 + 补丁流程 + 无回归 + 完成区

- D4（无管道真实退出码）：`总计: 80 项 | PASS: 80 | FAIL: 0 | MANUAL: 0`，`EXIT 0`；`e_flags` PASS detail = `setELFHeaderEFlags(EF_DADAO_ABIV1=0x1)`（源自代码常量，可采信）。✔
- 本体：`readelf Flags: 0x1`、`llvm-readobj Flags [ (0x1) / 0x1 ]`、raw `@48=0000 0001`；`Class=ELF64`/`big endian`/`OSABI=0`/`Machine=0xda0` 不变。✔
- 补丁流程：`0008` 与 `git format-patch -1 HEAD --stdout` **byte 相同**（md5 均 `d324a74b…`）；worktree（base `6dfe1677a`）`git am 000[1-8]-*.patch` **EXIT 0**（8 个 `Applying:`），重放 tree `0e058573eb70da9e57db6995d6caef6bbe8985da` == 源树 HEAD tree；worktree 已移除。✔
- 无回归（真实退出码）：lit **22/22**（0）、`check_lit_bytes` **53 patterns OK**（0）、oracle **68/68**（0）、`validate_instrinfo` **0 errors/0 warnings**（0）、`make check` **PASS**（0）；`tests/vectors/` 无改动。✔
- 完成区一致性：L109 已订正为「只在 diff `+` **非注释**代码行搜索」（与实际一致）；`+28` 与 `git numstat` 一致；其余数字与真实输出逐条对齐。✔
- 改动范围：7 条路径，除 `tools/integ/` 那处外均只涉 `e_flags`；`check_interface_alignment.py` 本次改动仅 `e_flags` 一块。✔

#### 7. 结论

验收标准 1–8 条款在**本次 reviewer 亲自重跑**下全部通过，硬约束无违反；`tools/integ/check_interface_alignment.py` 的修改为**合理的检测面扩展**（因 LLVM 无 `getEFlags()` 虚方法），非凑绿放宽；残留 C/D 为**已明确的轻度已知限制**（无实际触发、非唯一防线）。
→ **Accepted**。建议主会话将任务状态置为 `已验证`；并将 §4 的已知限制随 ADR/知识库或后续任务登记（非阻断）。

> 环境还原：patch md5 `d324a74be54eb8c868af3b5936f4fda0`、源树 `git status` clean、主仓仅 engineer 的 7 条路径、`Flags 0x1`、checker EXIT 0。

---

## 验收结论（2026-09-22，主会话；reviewer 三轮独立验收）

**判决**：**Accepted**（R1 Needs Revision → R2 Needs Revision → R3 Accepted）。

**本体（reviewer 亲自复跑）**：`llvm-mc --triple=dadao-unknown-elf -filetype=obj` 产出的 `.o`：`readelf -h` → `Flags: 0x1`（原 `0x0`）；`llvm-readobj -h` → `Flags [ (0x1) / 0x1 ]`；raw `@48 = 0000 0001`（bits 8–31 = 0）；`Class=ELF64`/`Data=big endian`/`OS/ABI=0`/`Machine=0xda0` **均未变**。

**D1 机制偏离（reviewer 判定正当）**：LLVM `MCELFObjectTargetWriter` **无** `getEFlags()` 虚方法（`grep -rn getEFlags llvm/include/llvm/MC/` 零命中）；实际采用 LLVM 标准模式 `RegisterObjectTargetStreamer` → `DADAOTargetStreamer` ctor → `setELFHeaderEFlags(EF_DADAO_ABIV1)`（CSKY/ARM/RISC-V/LoongArch 同模式），语义等价。已在完成区如实记录。

**补丁流程**：`0008-dadao-elf-e_flags.patch` 与 `git format-patch -1 HEAD` **byte 相同**（md5 `d324a74be54eb8c868af3b5936f4fda0`，无手工 hunk）；`series` 顺序正确；临时 worktree `git am 0001`→`0008` **全 clean**，replayed tree `0e058573eb70da9e57db6995d6caef6bbe8985da` == 源树 HEAD tree。

**反例门控（reviewer 亲自注入）**：① 代码常量 → `0x02`（commit message 不变）⇒ FAIL；② call 字面量 `(0x02)` ⇒ FAIL；③ `0x1` ⇒ PASS；④ 删除 call ⇒ FAIL；另边界 B（注释 `0x1` + 代码 `0x02`）⇒ FAIL、边界 A（注释 `0x02` + 代码 `0x1`）⇒ PASS。还原后 patch md5 复原。新 lit `e_flags.s` 亦在注入 `EF_DADAO_ABIV1=0x02` 时 FAIL。

**命令核验（真实输出）**：`make build-mc` PASS（`llvm-readobj` 已入 ninja 目标，干净构建可重建，13m12s）；`llvm-lit tests/lit/MC/Dadao/` **22/22**（21+1）；`check_lit_bytes` **53**；`test_encoding_oracle` **68/68**；`validate_instrinfo` **0 errors**；`make check` PASS。

**D4 独立佐证**：`tools/integ/check_interface_alignment.py` → **80/80/0、EXIT 0**（`e_flags` 项 PASS，detail `setELFHeaderEFlags(EF_DADAO_ABIV1=0x1)`）。

**已知限制（reviewer 判可接受，非阻断）**：该检查器的 `_is_comment()` 只识别**全行**注释；行尾注释 / 块注释中间行内的误导文本仍可遮蔽（假绿）。本产物无触发（`0008` 的 `+` 行除真实 call 外无该 token）。零残留正解为改读真实产物（`llvm-mc`+`llvm-readobj` 解析 `Flags`）。已登记 `deferred.md`。

**结论**：置 `已验证`。
