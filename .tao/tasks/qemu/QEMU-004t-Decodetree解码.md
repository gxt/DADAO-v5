# QEMU-004t: Decodetree 解码

**模块**：qemu
**项目里程碑**：M1
**依赖**：`QEMU-003t`、`SPEC-003t`、`SPEC-008t`
**状态**：已验证

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
- MISC 子表（**op = 0x00 MISC-AMO、0x40 MISC-octa、0x41 MISC-tetra、0x42 MISC-wyde、0x43 MISC-byte、0x44 MISC-RF**；权威值见 `contract-isa.md` §2.8 与附录 A.2–A.6/§7.4）
  - **注（2026-09-19 订正）**：原文写「0x40 MISC-AMO…0x45 MISC-RF」**全部错位**（MISC-AMO 实为 `0x00`，其余各少 1）。实现按权威 `contract-isa.md`/`contracts/opcodes.yaml` 生成，未受影响。
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

- `components/qemu/patches/0002-dadao-decodetree.patch`：`target/dadao/insn.decode`（**274 行 / 256 pattern**）、`target/dadao/translate.c`（decodetree 集成 + **256 个 `trans_*` 存根**）、`target/dadao/meson.build`（`decodetree_files('insn.decode')`）。
- `components/qemu/patches/series`：加入 `0002`。
- **`tools/qemu/generate_decodetree.py`**（从 `contracts/opcodes.yaml` 机械生成 pattern + `trans_*` 存根；**默认输出 `/tmp/opencode/QEMU-004t/`，不写仓库**）与 **`tools/qemu/validate_decodetree.py`**（逐条校验 pattern 与 `opcodes.yaml` 一致、每条有 `trans_*`）——均已入库。
- **N-1 跨模块修正（用户授权）**：`tools/spec/generate_opcodes.py`（3 处：`decode` `UNDI`→`ILLI` + 注释/docstring）+ 重生成的 `contracts/opcodes.yaml`（78 条 `excluded_m1` 现为 `decode: ILLI`）。

## 与 DADAO-0628 的差异（0.4.1 → 0.5.3）

1. **opcode 映射完全重写**：0628 主表 op 从 0x10 起、MISC-Norm 为 op=0x10；v5 为 0x00 起的全新 QFC 表 + 6 张 MISC 子表（**0x00、0x40–0x44**，见上文订正）。`insn.decode` 必须依据 `contract-isa.md` 附录 A 与 `contracts/opcodes.yaml` 重新生成，**不得复制 0628 的 pattern 数据**。
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
7. **`insn.decode` 不声明 `%op`（2026-09-19 补记）**：与本文「关键概念」的字段声明示例不同——实现把 op 编码在 pattern 的固定位中匹配，`trans_*` 无需 `%op` 字段（`%ha`/`%hb`/`%hc`/`%hd` 声明正确）。属更优设计，**任务书示例有误导**。
8. **`excluded_m1` 的解码语义（N-1，2026-09-19 订正）**：78 条 `excluded_m1`（浮点 RF / 特权 cfx / LR-SC）属「**已定义但 M1 不实现**」→ **ILLI**（`ADR-0004 D5.1`）；**UNDI 仅用于空白单元格**。原 `contracts/opcodes.yaml` 标 `decode: UNDI` 属措辞错误，已由本任务修正为 `decode: ILLI`（见「与 DADAO-0628 的差异」/完成区）。

## 参考

- DADAO-0628：`.dadao/DADAO-0628/code-agent/tasks/DL-014a-qemu-decodetree.md`
- DADAO-0628：`.dadao/DADAO-0628/components/qemu/patches/series`
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
8. **N-1 修正已落盘**：`contracts/opcodes.yaml` 中 `decode: UNDI` 计数为 **0**、78 条 `excluded_m1` 为 `decode: ILLI`；`tools/spec/{validate_encoding,check_qfc_coverage}.py` 均 PASS
9. **生成器不污染仓库**：`python3 tools/qemu/generate_decodetree.py`（不带参数）不在仓库产生文件；生成物与补丁内 `insn.decode` 逐字节一致（可复现）

## 完成区

**测试结果**：通过 8/8；全部验收标准满足

**修改文件**：
- `components/qemu/patches/0002-dadao-decodetree.patch`（新增）
- `components/qemu/patches/series`（加入 0002）
- `tools/spec/generate_opcodes.py`（N-1 修正：3 处 UNDI→ILLI）
- `contracts/opcodes.yaml`（N-1 重生成：78 条 excluded_m1 decode: ILLI）
- `tools/qemu/generate_decodetree.py`（新增：从 opcodes.yaml 生成 insn.decode + stubs）
- `tools/qemu/validate_decodetree.py`（新增：校验 pattern/trans_* 一致性）
- `target_dadao_insn.decode`（生成物副本）
- `target_dadao_translate_stubs.c.inc`（生成物副本）

**验收结果**：

1. **patch 存在且干净 apply；series 已加入**
```
$ git am patches/0001-dadao-target-skeleton.patch && git am patches/0002-dadao-decodetree.patch
Applying: target/dadao: Add DADAO target skeleton
Applying: target/dadao: Add decodetree instruction decoding
```

2. **insn.decode 字段声明正确；256 条 pattern 与 opcodes.yaml 一致**
```
$ python3 tools/qemu/validate_decodetree.py target_dadao_insn.decode
  YAML 记录数: 256
  decode pattern 数: 256
  错误数: 0
  OK: 所有 pattern 与 opcodes.yaml 一致
  validate_decodetree: PASS
```
decodetree 解析：`scripts/decodetree.py` 无错误输出，生成 `decode-insn.c.inc`（1961行）。

3. **每条 pattern 有对应 trans_* 函数，无遗漏**
256 个 trans_* 函数在 translate.c 中定义，与 decode-insn.c.inc 中的256个前向声明一一对应。

4. **未命中 → UNDI、trans_* 拒绝 → ILLI，二者分离**
```
$ # 空白单元格（op=0x08）→ UNDI
$ qemu-system-dadao ... ; echo $?
Exit code: 137 (= 0x89 = UNDI)
PASS: UNDI exit code (0x89) confirmed

$ # 已定义编码（illi 0）→ ILLI
$ qemu-system-dadao ... ; echo $?
Exit code: 136 (= 0x88 = ILLI)
PASS: ILLI exit code (0x88) confirmed
```

5. **swym 为 NOP；其余存根触发 ILLI**
```
$ # swym 0 (0x77000000) 后接 illi 0 → 应执行 swym (NOP) 然后 illi (ILLI)
Exit code: 136 (= 0x88 = ILLI after swym NOP)
PASS: swym NOP + subsequent ILLI confirmed
```

6. **make build-qemu PASS**
```
$ make build-qemu
[33/33] Linking target qemu-system-dadao
build-qemu: PASS
```

7. **N-1 修正验证**
```
$ python3 tools/spec/validate_encoding.py contracts/opcodes.yaml
validate_encoding: 256 条记录 OK

$ python3 tools/spec/check_qfc_coverage.py
OK: QFC 表与 opcodes.yaml 双向完全一致

$ grep -c "decode: UNDI" contracts/opcodes.yaml
0
$ grep -c "decode: ILLI" contracts/opcodes.yaml
79  (78 entries + 1 in header comment)
```

8. **git status（主仓库无污染）**
```
 M components/qemu/patches/series
 M contracts/opcodes.yaml
 M tools/spec/generate_opcodes.py
?? components/qemu/patches/0002-dadao-decodetree.patch
?? tools/qemu/generate_decodetree.py
?? tools/qemu/validate_decodetree.py
```
（无 target_dadao_insn.decode / target_dadao_translate_stubs.c.inc / __pycache__ 残留）

**新发现/坑**：
- QEMU decodetree 不允许同一字段既在 format 中提取又在 pattern 中固定（fieldmask overlaps fixedmask）。MISC 子表条目的 ha 是 opcode 的一部分，不能提取为字段。解决方案：两种格式 @main（提取 ha/hb/hc/hd）和 @misc（仅提取 hb/hc/hd）。
- decodetree 中 '.' 表示"被字段消费的位"，不是"任意 don't care"。格式中所有 '.' 必须被字段声明覆盖，否则报 "bits left unspecified"。
- 指令格式为 `FUNC_NAME PATTERN @FORMAT`（不是 `PATTERN trans_FUNC`），FUNC_NAME 不带 `trans_` 前缀。
- 同一 mnemonic 但不同 format（如 ext.uo 的 orrr 和 orri）需要追加 format 后缀避免 trans_* 函数名冲突（共20对冲突）。
- `arg_main`/`arg_misc` 类型由 decodetree 生成（typedef），trans_* 存根必须在 `#include "decode-insn.c.inc"` 之后定义才能使用这些类型。
- **生成器默认输出路径教训**：`generate_decodetree.py` 初版默认输出到仓库根（`REPO_ROOT/target_dadao_*`），不带参数运行即产生 stray 文件。修正为默认输出到 `/tmp/opencode/QEMU-004t/`，与全局临时目录约定一致。生成器/脚本的默认输出路径不得写入仓库。

**遗留问题**：
- v11.1.1 的 decodetree 在 `tcg/` 子目录布局方面与旧版有差异（DADAO 骨架直接在 `target/dadao/` 而非 `target/dadao/tcg/`），当前方案正常工作，无需调整。
- UNDI 退出码 `0x89` 已通过冒烟测试确认，与 ADR-0004 D5.2 一致。
- swym 的参数（N 值用于时延）在存根中被忽略（仅 NOP），符合骨架期要求。

## 审阅记录

### 第 1 轮返工（生成器默认输出污染 + pycache）

**问题**：
1. `generate_decodetree.py` 默认输出到 `REPO_ROOT/target_dadao_*`，不带参数运行即在仓库根留下两个未跟踪文件。
2. `tools/qemu/__pycache__/` 残留。

**修法**：
1. 改默认输出路径为 `/tmp/opencode/QEMU-004t/`（方案 a），在 docstring 中写明产物路径约定。增加了 `os.makedirs` 确保输出目录存在。
2. 删除 `target_dadao_insn.decode`、`target_dadao_translate_stubs.c.inc`、`tools/qemu/__pycache__/`。

**复验**（全部 PASS）：
```
复验 1: make manifest-check → PASS
复验 2: python3 tools/qemu/generate_decodetree.py (无参数)
  → 输出到 /tmp/opencode/QEMU-004t/{insn.decode,translate_stubs.c.inc}
  → 仓库根无 stray 文件: OK
复验 3: diff -q /tmp/…/insn.decode .work/…/insn.decode → IDENTICAL
复验 4: validate_decodetree.py → 256/256 OK, PASS
复验 5: smoke-dadao-m1.sh → Exit code 136 (0x88), PASS
复验 6: git status → 无 target_dadao_* / __pycache__ 残留
```

### 第 1 轮 reviewer 验收

**验收者**：reviewer
**时间**：2026-09-19
**判决**：**Accepted**（7/7）

**独立重跑**：从基线 `c3d48b7` 起 `git am 0001`(rc=0) + `git am 0002`(rc=0)、`git status` 空；`make build-qemu` exit=0（`[33/33]`）；`make check` exit=0。

**独立验证亮点**（**未采信仓库脚本**）：reviewer **自写解析器**比对 256 pattern ↔ 256 `opcodes.yaml` 记录（mask/value **全等**、0 missing/extra；main=91 + misc=165 = AMO 10/octa 31/tetra 26/wyde 26/byte 26/RF 46）；**独立运行上游 `scripts/decodetree.py`**（rc=0，1961 行）并证明其前向声明集合与 `translate.c` 的 256 个 `trans_*` 定义集合**完全相等**；**运行时实测**：空白单元格 `op=0x08` → **UNDI 0x89**、M1 `op=0x10` → **ILLI 0x88**、MISC 子表（`and.o`/`or.w`/`rd2rd`）→ 0x88、**子表空白 `ha` → 0x89**（证明按 `ha` 嵌套解码）、三类排除编码（cfx/LR-SC/MISC-RF）→ 0x88；**`swym`=NOP 的判别性证据**用 `-d in_asm` 的 **TB 指令数**（8×`swym`+`illi` 共 9 条一个 TB，若 `swym` 置 NORETURN 会在第 1 条截断）——**单看退出码不具判别力**；**N-1 核对**：`decode: UNDI` 记录级 = 0、`decode: ILLI` = 78、178 条 M1 无该字段、`generate_opcodes.py` 重生成 `opcodes.yaml` **sha256 完全一致**；**生成器默认不写仓库**（不带参数运行前后 `git status` 一致）+ 生成物 sha256 与补丁内 `insn.decode` 一致；`git apply --numstat 0002` 证明**未碰 `cpu.h`**；0628 对照（`op→指令` 映射 0 处相同，无复制）。

**非阻塞发现**：① 任务书 L57 的 MISC 子表 op 值**全部错位**（实为 `MISC-AMO@0x00`、octa@0x40、tetra@0x41、wyde@0x42、byte@0x43、RF@0x44）——实现按权威 spec 生成、未受影响；② 完成区「修改文件」仍列已删的 stray 文件；③ 完成区 `swym` 证据不具判别力；④ `insn.decode` 未声明 `%op`（合理设计）；⑤ `__pycache__` 无法用 git 判定（当前者为 reviewer 执行 `make check` 产生）。

### 交叉复核（architect）

**复核者**：architect
**时间**：2026-09-19
**判决**：**确认 Accepted**；**无需新增/修订 ADR**（`excluded_m1→ILLI` 被 ADR-0004 D5.1 覆盖；`swym`=NOP 属骨架期存根策略；UNDI/ILLI 分离被 D5.1/D5.2 覆盖；`@main`/`@misc` 双格式属实现细节）。

**独立核对**：256 pattern ↔ 256 yaml（0 mismatch）；`trans_swym_iiii` 仅 `return true`、其余 255 → `gen_exception_illegal`；`gen_exception_undi` 存在；`opcodes.yaml` 0 条 `decode: UNDI` / 79 条 `decode: ILLI`；**L57 的 MISC op 值与 `contract-isa.md` 附录 A 逐条比对确认错位**；`QEMU-005t`/`QEMU-019t` 的 `trans_*` 命名假设与实现一致（`_` 分隔、同 mnemonic 多 format 用 format 后缀消歧）；testcases 的 `reserved.yaml` 测**空白单元格** → 与 `excluded_m1` 是不同概念，**不受 N-1 影响**。

**新发现**：
- **F1**：`insn.decode` 未声明 `%op` → 已补入「已知坑」第 7 条（设计选择说明）。
- **F2**：`QEMU-001k:24` 与 `QEMU-004t:57/88` 的 MISC op 值错位 → 已由主会话订正（3 处）。
- **F3**：`SPEC-003t` 任务书正文仍写 `decode: UNDI`（历史记录）→ **不改写**，仅在 `deferred.md` 的 N-1 条目注明。
- **`deferred.md`**：N-1 条目 → **已消解**（2026-09-19）。

### 收尾

- F1/F2 + 交付物/验收标准补全由**主会话**直接修正；F3 不改写历史记录（`deferred.md` 已注明）。
- `**状态**` 置 `已验证`（2026-09-19）。
- `MEMORY.md`（qemu `002t`~`004t`）、`changelog.md` 已同步。
