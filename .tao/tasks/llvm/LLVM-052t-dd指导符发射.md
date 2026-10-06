# LLVM-052t: `.dd.{b08,w16,t32,o64}` 指导符发射

**模块**：llvm
**项目里程碑**：M4
**依赖**：`LLVM-050t`
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `spec/DADAO-11-AEE-应用程序运行环境.md` §汇编兼容性 §指导符（`.dd.b08`=1B、`.dd.w16`=2B、`.dd.t32`=4B、`.dd.o64`=8B；**DADAO octa = 8 字节**，与 GAS `.octa`=16B 不同）；`.tao/knowledge/contract-asm.md §7`（当前 v5 汇编器未实现、报 `unknown directive`；`.word` 被拒）。
  - 现有 AsmParser（`AsmParser/DADAOAsmParser.cpp`）与 MC 流式发射设施；`DADAOMCAsmInfo`（大端、`CommentString=";"`）。
- **输出**（组件源码改在 `.work/source/llvm-project`；导出补丁）：
  - `DADAOAsmParser` 实现 `parseDirective`（或等价）接受 **`.dd.b08` / `.dd.w16` / `.dd.t32` / `.dd.o64`**，按大端序发射对应宽度数据（表达式可含常量与符号；符号/可重定位引用按需发数据 reloc）。
  - 保持 `.word`/`.octa` 等的既有拒绝/未识别行为（与 `contract-asm §7` 一致）。
- **约束**：
  - **大端序**（`contract-elf §1.1`：`ELFDATA2MSB`）；字节序逐例核对（如 `.dd.w16 0x1234` → `12 34`）。
  - **octa=8B**（非 GAS 16B）；**不得**把 `.dd.o64` 实现为 16 字节。
  - **reloc/fixup 坑预防（5 条，同 `LLVM-050t`）**，尤其⑤大常量/大地址不得折入受限字段；数据符号引用须发对应 reloc（数据 reloc 类型若超出 `ADR-0019` 4 类，须**停下报告**，不得自行新增类型）。
  - **补丁纪律（`spec/Process-01`）**；`commit --amend` 收敛 base+1 → `make_patch.py` → `check-patch-tree`；不手改补丁。
  - 构建/串行/临时目录/留证纪律同 `LLVM-050t`；`ninja -j8`；失败即停。
  - 临时目录 `/tmp/opencode/LLVM-052t/`；**不提交 git**。

## 验收标准

1. 构建 EXIT=0。
2. **宽度/字节序**：`.dd.b08 0x12`→`12`；`.dd.w16 0x1234`→`12 34`；`.dd.t32 0x11223344`→`11 22 33 44`；`.dd.o64 0x1122334455667788`→`11 22 33 44 55 66 77 88`——用 `llvm-mc -filetype=obj` + `llvm-objdump -s`/hexdump 逐条真实核对（给出 hexdump 输出）。
3. **表达式/符号**：`.dd.o64 sym` / 含表达式的数据项可汇编；符号/可重定位引用在 `llvm-readobj -r` 可见对应数据 reloc（若需新类型则**停并报告**）。
4. **拒绝一致性**：GAS `.word`/`.octa` 仍不被接受（非零退出或明确报错），与 `contract-asm §7` 一致。
5. **lit 向量**：`tests/llvm/lit/MC/DADAO/` 新增 `.dd.*` 用例（宽度/字节序 + 反例）；`make check-lit` EXIT=0 不回归；`make check` EXIT=0。
6. 一键证据脚本 `.work/evidence/LLVM-052t/run.sh`（含 `--inject`：把 `.dd.w16` 改小端/把 `.dd.o64` 改成 16B → 期望 FAIL → 还原+重建 → 回绿）；完成区贴真实输出。

## 完成区

**测试结果**：通过 25/25（一键证据 `.work/evidence/LLVM-052t/run.sh` 正常模式 25 项全 PASS，EXIT=0）+ 反例注入 15/15（`--inject` 2 轮：小端 / `.dd.o64` 16 字节 → FAIL → 还原+重建 → 回绿，EXIT=0）。`make check` EXIT=0；`make check-lit` 46/46（42→46，新增 4，无回归）；`make test-codegen` 15/15；`check-patch-tree` 83 patches OK；`check-source-state` llvm-project clean+count=1。失败原因：无。

**修改文件**：
- 组件源码（`.work/source/llvm-project`，已 amend 收敛为 base+1：`6dfe1677a..3aea19491`，worktree clean）：
  - `llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp`（+`parseDirective` override + `parseDDDirective`；显式拒绝 GAS `.octa`）
  - `llvm/lib/Target/DADAO/MCTargetDesc/DADAOELFObjectWriter.cpp`（`getRelocType` 增 `FK_Data_8 → R_DADAO_ABS48`）
  - `llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp`（`applyFixup` 处理 `FK_Data_8`：未解析→`maybeAddReloc`，已解析→大端写入）
- 补丁集：`components/llvm-project/patches/llvm/lib/Target/DADAO/{AsmParser/DADAOAsmParser.cpp,MCTargetDesc/DADAOAsmBackend.cpp,MCTargetDesc/DADAOELFObjectWriter.cpp}.patch`（`make_patch.py` 导出；`series` 仍 51，未手改）。
- 台账：`components/llvm-project/changelog.md`（+LLVM-052t 一条）。
- 测试向量（新增 4）：`tests/llvm/lit/MC/DADAO/dd-width.s`、`dd-expr.s`、`dd-symbol.s`、`dd-reject.s`。
- 证据脚本：`.work/evidence/LLVM-052t/run.sh`（新增）；日志 `.work/log/llvm/LLVM-052t-*.log`。
- 本任务书（完成区/自审/状态）。

**验收结果**（真实输出，`cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`，无 `tee`）：

1. **构建 EXIT=0**（`.work/log/llvm/LLVM-052t-build.log`）：`ninja -j8 -C .work/build/llvm llvm-mc llvm-objdump llvm-readobj` → `EXIT=0`（3 源文件重编译 + relink `llvm-mc`/`llvm-objdump`）。
2. **宽度/字节序**（`llvm-mc -filetype=obj` + `llvm-objdump -s`，日志 `LLVM-052t-acceptance.log`）：
   ```
   	.dd.b08	0x12
   	.dd.w16	0x1234
   	.dd.t32	0x11223344
   	.dd.o64	0x1122334455667788
   Contents of section .text:
    0000 12123411 22334411 22334455 667788    ..4."3D."3DUfw.
   ```
   逐字节：`.dd.b08`→`12`；`.dd.w16`→`12 34`；`.dd.t32`→`11 22 33 44`；`.dd.o64`→`11 22 33 44 55 66 77 88`（**8 字节**，非 GAS 16）。证据脚本另做**逐指令独立字节**核对（`dd-b08/w16/t32/o64-bytes`，4/4 精确相等）+ 合并序列核对。
3. **表达式/符号**（`llvm-readobj -r --expand-relocs`）：`.dd.o64 ext` / `.dd.o64 ext+8` →
   ```
   Relocation { Offset: 0x0  Type: R_DADAO_ABS48 (0) Symbol: ext (1) Addend: 0x0 }
   Relocation { Offset: 0x8  Type: R_DADAO_ABS48 (0) Symbol: ext (1) Addend: 0x8 }
   ```
   在 **`.rela.text` / `SHT_RELA`（无 `SHT_REL`）** 中；常量表达式 `.dd.t32 1+2*3, 0x10`→`00000007 00000010`、`.dd.w16 -1`→`ffff`、`.set` 常量→无 reloc。数据 reloc **复用 `R_DADAO_ABS48`**（未新增类型，见用户裁定）。窄字段符号（`.dd.t32 ext`）显式报错 `relocatable operand ... not supported`。
4. **拒绝一致性**：
   ```
   $ .octa 0x1     → EXIT=1  error: unsupported directive '.octa' (GAS 16-byte octa); DADAO's octa is 8 bytes -- use '.dd.o64'
   $ .word 0x1234  → EXIT=1  error: unknown directive
   ```
   另有反例：`.dd.b08 0x1234`→`error: value evaluated as 4660 is out of range.`（EXIT=1）。
5. **lit**：新增 4 文件 `llvm-lit` → `Passed: 4 (100.00%)`；`make check-lit` → `Passed: 46 (100.00%)` EXIT=0（42→46，无回归）；`make check` → `repository checks: PASS` EXIT=0；`make test-codegen` → `Results: 15/15 passed, 0 failed`。
6. **一键证据**（`.work/log/llvm/LLVM-052t-evidence-run.log` / `-inject.log`）：正常模式 `RESULT: PASS (0 failures)` EXIT=0（25 项）；`--inject` EXIT=0：
   - 小端注入（`IsLittleEndian=true`）：字节变 `123412443322118877665544332211` → `inject-little-endian-FAIL`；`git checkout` + md5 一致 + `ninja` 重建 → `restore-green`。
   - `.dd.o64` 16 字节注入（多 emit 一份）：字节变 `...6677881122334455667788` → `inject-o64-16B-FAIL`；还原+重建 → 回绿。
7. **补丁/源态**：`check-patch-tree` → `83 patches OK`；`check-source-state` → `llvm-project: OK HEAD=3aea19491850 count=1 clean=True`。

**新发现/坑**：
- **`.octa` 此前被 generic MCParser 按 GAS 16 字节静默接受**（实测 `.octa 0x1122334455667788` → `.text` 出 16 字节、rc=0），与任务书「既有拒绝行为」前提及 `contract-asm §7`「MUST NOT 使用 GAS `.octa` 语义」冲突——任务书前提有误。已按用户裁定（原文见下）在 `parseDirective` 显式拒绝。
- **`.octa` 拒绝点**：`MCTargetAsmParser::parseDirective` 先于 generic parser 被调用，返回 `Failure` 可覆盖 generic 的 `DK_OCTA` 处理；`.word` 本就不在 generic `DirKind` 表中（保持 `unknown directive`），无需改动。
- **数据符号引用复用 `R_DADAO_ABS48`**（用户裁定「ABS48 是绝对地址，不区分指令和数据」）：`.dd.o64 <sym>` 与 **`.quad <sym>`（既有 `FK_Data_8` 路径）** 现均发 ABS48 reloc；后者此前**静默出 0、无 reloc**（既有缺陷），本改动一并修正（与 `LLVM-055t`「`.quad sym` 数据 reloc」方向一致）。`needsRelocateWithSymbol` 对 ABS48 返回 true，故保留真实符号名（非 `STT_SECTION`）。
- **ADR-0019 D2/D4/D5 措辞**现把 ABS48 限定为「`set.zw`/`or.w` 序列，3×`immu16`，按 wyde-position 分片」；本次按用户裁定将其**扩用为数据绝对地址**（8 字节字段，linker 写 48 位值）。实现与 `ADR-0019` 正文措辞存在张力，**需主会话走 ADR 流程更新/补记**（见遗留）。
- **窄字段符号操作数**（`.dd.b08/.w16/.t32 <sym>`）显式报错：DADAO 地址 48 位，1/2/4 字节字段无法承载，避免「发 6 字节 ABS48 到 4 字节字段」的错配与静默截断（`contract-asm §9` 报错原则）。`ADR-0019 D6` 的 link-time overflow 仍适用于 8 字节字段内 >48 位的情形。
- **指令大小写敏感**：`.DD.W16` → `unknown directive`（与既有 `.section`/`.text` 等 generic 指令一致；`DADAO-11` 写作小写）。未做大小写不敏感扩展。
- **用户裁定原文**（`AGENTS.md` 子代理硬约束 #9）：
  - 问 `.octa` 前提不符：**「拒绝 .octa（推荐）」**
  - 问数据符号 reloc：**「ABS48是绝对地址，不区分指令和数据；你倒是提醒我了，load/store指令如果需要相对寻址的话，还需要一个REL12；根据前面的讨论，REL12可以放在M4之后，如果你认为现在需要的话，也可添加」**

**遗留问题**：
- **ADR-0019 需更新/补记**：把 ABS48 明确定为「绝对地址重定位，指令/数据通用」，并说明数据场景（8 字节字段、D6 overflow）。归主会话 ADR 流程（`spec/Process-03`）。属**文档/决策层**待办，不阻塞本实现（用户已口头裁定）。
- **REL12（load/store 相对寻址）**：按用户原文「可以放在 M4 之后」，本任务不涉及（`.dd.*` 为数据、无相对寻址），**未添加**；建议另立任务/ADR（新增第 5 类会改动 Accepted ADR-0019，须用户逐条确认）。属**能力缺口**（非错值）。
- **非 8 字节数据指令的既有静默 0**：`FK_Data_1/2/4`（如 `.long <sym>`/`.short <sym>`）仍为既有「静默出 0、无 reloc」行为（本任务只处理 `FK_Data_8`，范围外，未触及）。属**既有缺陷**，建议另立任务（与 `LLVM-055t` 数据 reloc 一并处理）。
- 其余：无；无未修 finding。

## 审阅记录

#### 第 1 轮 engineer 自审

**范围**：对增量改动逐行审查（`parseDirective`/`parseDDDirective`、`getRelocType` 的 `FK_Data_8` 分支、`applyFixup` 的 `FK_Data_8` 分支）+ 4 个 lit 文件逐条核 FAIL 路径 + 证据脚本逐条核断言可失败性；对照 `DADAO-11 §指导符`、`contract-asm §7/§9`、`ADR-0019`、`contract-elf §1.1` 与验收 1–6。

**判决**：实现完成，验收 1–6 均有真实输出支撑；无未修阻断项 → 状态置 `待验收`。

**逐行审查要点**：
- `parseDirective`：仅拦 `.octa`（`Error`→`ParseStatus::Failure`，框架断言 `isFailure()==hasPendingError()` 成立）与 4 条 `.dd.*`，其余 `NoMatch` 交还 generic parser，**不影响** `.section/.text/.quad` 等既有指令。
- `parseDDDirective`：`do/while` 逐值 `parseExpression` + `emitValue`（大端由 `DADAOMCAsmInfo::IsLittleEndian=false` 保证）；宽度=1/2/4/8 精确对应；越界由 `emitValueImpl` 的 `isUIntN/isIntN` 检查报错；窄字段非绝对表达式显式报错（不静默截断）；无 operand/尾随记号均由框架报错（实测）。
- `getRelocType`：`FK_Data_8` 加在 `default: llvm_unreachable` 之前，语义=ABS48（绝对，用户裁定），`needsRelocateWithSymbol(ABS48)=true` 保证符号名保留；`FK_Data_1/2/4` 未映射（走既有路径，未改变）。
- `applyFixup`：`FK_Data_8` 未解析→`maybeAddReloc`（尊重 `IsResolved`，不发预链接占位）；已解析→大端写 8 字节。**未触碰** PCRel 位移/掩码逻辑与 ABS48 分支。
- 边界（实测）：尾随记号报错；无 operand 报错；前向同段符号→ABS48 reloc；`.set` 常量→无 reloc 常量；`.data` 段内工作；`.dd.o64 .`→对 `.L0` 的 ABS48（合理）；`end-start` 同段差分→常量 8、无 reloc。
- 防造假：所有留证 `cmd > log 2>&1; rc=$?; echo "EXIT=$rc"`；脚本内无 `tee`；期望字节手算自指令宽度/大端（非从 llvm-mc 反推），由精确相等判定；`--inject` 校验 `git diff --name-only` 非空 + md5 还原 + 重建后回绿。
- 范围/纪律：仅改 3 个组件源文件；未手改 `components/**/patches/**`（`make_patch.py` 导出，仅 3 份变更、`series` 不变）；临时目录 `/tmp/opencode/LLVM-052t/`；未提交 git；未改函数签名、未引入依赖。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务书前提「`.octa` 既有拒绝」与实测不符（此前按 GAS 16 字节静默接受） | ✅已修（经用户裁定） | `parseDirective` 显式 `Error` 拒绝 `.octa` | `.octa 0x1` → EXIT=1 + `unsupported directive '.octa'`；`dd-octa-rejected` PASS |
| F2 数据符号引用此前静默 0、无 reloc（`.quad <sym>`）/ `.dd.o64 <sym>` 无落地路径 | ✅已修 | `getRelocType` 映射 `FK_Data_8→ABS48`；`applyFixup` 未解析→`maybeAddReloc`、已解析→大端写入 | `readobj -r` 显示 2×`R_DADAO_ABS48`（offset 0x0/0x8、addend 0x0/0x8）；`dd-symbol-relocs`/`dd-symbol-rela` PASS |
| F3 若放行 `.dd.b08/.w16/.t32 <sym>` 会发 6 字节 ABS48 到 1/2/4 字节字段（错配/截断） | ✅已修（决策为显式报错） | `parseDDDirective` 窄字段非绝对表达式 `Error` | `.dd.t32 ext` → EXIT=1 + `relocatable operand ... use '.dd.o64'`；`dd-narrow-symbol-rejected` PASS |
| F4 `.quad <sym>` 行为改变（静默 0 → ABS48 reloc，机制必然副作用） | ❌不修（披露，非缺陷） | 无（`FK_Data_8` 映射的必然结果） | `.quad ext` → ABS48 reloc；`.quad 0` 常量无 reloc；`make check-lit` 46/46、`make test-codegen` 15/15 无回归；与 `LLVM-055t` 方向一致 |
| F5 证据脚本 `dd-width-not-little-endian` 与合并检查重复；且 `local a=.. b=..` 触发 `set -u` unbound | ✅已修 | 拆为 4 个**逐指令独立字节**检查 + 合并序列检查；`local` 赋值拆行 | 重跑正常模式 25/25 PASS EXIT=0；`bash -n` 语法 OK；两轮注入 15/15 PASS EXIT=0 |
| F6 指令大小写敏感（`.DD.W16` 不被接受） | ❌不修（与既有指令一致） | 无 | 实测 `.DD.W16` → `unknown directive`；`DADAO-11` 写作小写；generic 指令同样大小写敏感 |
| F7 ADR-0019 措辞把 ABS48 限定为指令 wyde 片，与数据重用冲突 | ❌不修（归主会话 ADR 流程） | 无（代码注释已标注用户裁定） | 用户口头裁定原文已记录；已在遗留登记，待 ADR 更新 |

**自验命令退出码**：`run.sh`（正常）EXIT=0（25/25）；`run.sh --inject` EXIT=0（15/15）；`make check` EXIT=0；`make check-lit` EXIT=0（46/46）；`make test-codegen` EXIT=0（15/15）；`check-patch-tree` EXIT=0（83 patches OK）；`check-source-state` EXIT=0（clean, count=1）。

#### 第 1 轮 reviewer 验收

**审查者**：reviewer 子代理
**审查日期**：2026-10-06
**工作目录**：`/tmp/opencode/LLVM-052t-review/`

---

##### 一、证据脚本审查

**文件**：`.work/evidence/LLVM-052t/run.sh`（288行）

| 检查项 | 结果 |
|---|---|
| FAIL 路径：每个 `check()` 用 `[ "$expected" != "$actual" ]` 独立判定 | ✅ 独立 FAIL，无恒真 |
| 注入非空：`inject_round()` 校验 `git diff --name-only` 非空 | ✅ |
| 注入可还原：`git checkout` + md5 校验 + 重建 + 回绿 | ✅ |
| 结尾无 `tee`：所有命令用 `> file 2>&1`，末行 `[ "$FAILS" -eq 0 ]` | ✅ |
| `set -u` 启用（`local` 赋值已拆行，无 unbound 陷阱） | ✅ |
| `bash -n` 语法检查 | ✅（engineer 自验） |
| 反例注入有效性：两轮注入（小端 / o64-16B）均导致字节变化 | ✅ 见下方重跑记录 |

**结论**：证据脚本合格，可作为验收依据。

---

##### 二、重跑记录（独立执行，非采信 engineer 输出）

**2.1 正常模式**（`run.sh`，25 项）

```
$ cd /mnt/tao/DADAO-v5 && bash .work/evidence/LLVM-052t/run.sh > /tmp/opencode/LLVM-052t-review/run.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

逐项输出：
```
[PASS] build | expected: ninja EXIT=0 | actual: see LLVM-052t-evidence-build.log | rc=0
[PASS] dd-b08-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] dd-b08-bytes | expected: 12 (big-endian) | actual: 12 | rc=0
[PASS] dd-w16-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] dd-w16-bytes | expected: 1234 (big-endian) | actual: 1234 | rc=0
[PASS] dd-t32-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] dd-t32-bytes | expected: 11223344 (big-endian) | actual: 11223344 | rc=0
[PASS] dd-o64-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] dd-o64-bytes | expected: 1122334455667788 (big-endian) | actual: 1122334455667788 | rc=0
[PASS] dd-width-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] dd-width-sequence | expected: 121234112233441122334455667788 (combined) | actual: 121234112233441122334455667788 | rc=0
[PASS] dd-expr-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] dd-expr-bytes | expected: 0000000700000010ffff | actual: 0000000700000010ffff | rc=0
[PASS] dd-symbol-assemble | expected: llvm-mc EXIT=0 | actual: rc=0 | rc=0
[PASS] dd-symbol-relocs | expected: 2 x R_DADAO_ABS48 against ext (offset 0x0/0x8) | actual: abs48=2 ext=2 off8=1 add8=1 | rc=0
[PASS] dd-symbol-rela | expected: SHT_RELA present, SHT_REL absent | actual: rela=1 rel=0 | rc=0
[PASS] dd-octa-rejected | expected: non-zero + unsupported directive '.octa' | actual: rc=1 ... unsupported directive '.octa' ... | rc=0
[PASS] dd-word-rejected | expected: non-zero + unknown directive | actual: rc=1 ... unknown directive | rc=0
[PASS] dd-range-rejected | expected: non-zero + out of range | actual: rc=1 ... out of range | rc=0
[PASS] dd-narrow-symbol-rejected | expected: non-zero + relocatable operand | actual: rc=1 ... relocatable operand | rc=0
[PASS] lit-new | expected: 4/4 passed | actual: Passed: 4 (100.00%) | rc=0
[PASS] check-lit | expected: all passed (46 expected) | actual: Passed: 46 (100.00%) | rc=0
[PASS] make-check | expected: repository checks: PASS | actual: repository checks: PASS | rc=0
[PASS] test-codegen | expected: 15/15 passed | actual: Results: 15/15 passed, 0 failed | rc=0
[PASS] check-patch-tree | expected: 83 patches OK | actual: 83 patches OK | rc=0
[PASS] check-source-state | expected: llvm-project OK count=1 clean=True | actual: ... OK HEAD=3aea19491850 count=1 clean=True | rc=0
RESULT: PASS (0 failures)
```

**2.2 注入模式**（`run.sh --inject`，15 项）

```
$ cd /mnt/tao/DADAO-v5 && bash .work/evidence/LLVM-052t/run.sh --inject > /tmp/opencode/LLVM-052t-review/inject.log 2>&1; rc=$?; echo "EXIT=$rc"
EXIT=0
```

逐项输出：
```
== inject: little-endian ==
[PASS] inject-little-endian-effective | changed file (non-empty diff) | actual: llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp | rc=0
[PASS] inject-little-endian-rebuild | ninja EXIT=0 | rc=0
[PASS] inject-little-endian-FAIL | wrong bytes => mismatch with 121234112233441122334455667788 | actual: 123412443322118877665544332211 | rc=0
[PASS] inject-little-endian-restore-clean | empty git diff | actual: 0 bytes | rc=0
[PASS] inject-little-endian-restore-md5 | source byte-identical | actual: identical | rc=0
[PASS] inject-little-endian-restore-rebuild | ninja EXIT=0 | rc=0
[PASS] inject-little-endian-restore-green | expected bytes restored | actual: 121234112233441122334455667788 | rc=0
== inject: o64-16B ==
[PASS] inject-o64-16B-effective | changed file (non-empty diff) | actual: .../DADAOAsmParser.cpp | rc=0
[PASS] inject-o64-16B-rebuild | ninja EXIT=0 | rc=0
[PASS] inject-o64-16B-FAIL | wrong bytes => mismatch | actual: 1212341122334411223344556677881122334455667788 | rc=0
[PASS] inject-o64-16B-restore-clean | empty git diff | actual: 0 bytes | rc=0
[PASS] inject-o64-16B-restore-md5 | source byte-identical | actual: identical | rc=0
[PASS] inject-o64-16B-restore-rebuild | ninja EXIT=0 | rc=0
[PASS] inject-o64-16B-restore-green | expected bytes restored | actual: 121234112233441122334455667788 | rc=0
RESULT: PASS (0 failures)
```

---

##### 三、独立 hexdump 核验

Reviewer 独立执行 `llvm-mc -filetype=obj` + `llvm-objcopy -O binary` + `od`，未使用证据脚本：

```
$ cat > /tmp/opencode/LLVM-052t-review/dd_width.s <<'ASM'
	.text
	.dd.b08	0x12
	.dd.w16	0x1234
	.dd.t32	0x11223344
	.dd.o64	0x1122334455667788
ASM
$ .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj ... -o dd_width.o
EXIT=0
$ .work/build/llvm/bin/llvm-objcopy -O binary --only-section=.text dd_width.o dd_width.bin
$ od -An -v -tx1 dd_width.bin | tr -d ' \n'
121234112233441122334455667788
```

逐字节拆分：`.dd.b08`→`12`（1B）；`.dd.w16`→`1234`（2B，大端）；`.dd.t32`→`11223344`（4B，大端）；`.dd.o64`→`1122334455667788`（**8B**，非 GAS 16B）。✅

`.llvm-objdump -s` 输出（与 engineer 完成区一致）：
```
Contents of section .text:
 0000 12123411 22334411 22334455 667788    ..4."3D."3DUfw.
```

**符号 reloc**（独立执行）：
```
$ .work/build/llvm/bin/llvm-readobj -r --expand-relocs dd_symbol.o
Relocation { Offset: 0x0  Type: R_DADAO_ABS48 (0)  Symbol: ext (1)  Addend: 0x0 }
Relocation { Offset: 0x8  Type: R_DADAO_ABS48 (0)  Symbol: ext (1)  Addend: 0x8 }
```
在 `.rela.text`（SHT_RELA）中，offset/addend 正确。✅

**拒绝测试**（独立执行）：
| 输入 | 退出码 | 错误信息 | 判定 |
|---|---|---|---|
| `.octa 0x1` | 1 | `unsupported directive '.octa' (GAS 16-byte octa); DADAO's octa is 8 bytes -- use '.dd.o64'` | ✅ |
| `.word 0x1234` | 1 | `unknown directive` | ✅ |
| `.dd.b08 0x1234` | 1 | `value evaluated as 4660 is out of range.` | ✅ |
| `.dd.t32 ext` | 1 | `relocatable operand in '.dd.b08/.dd.w16/.dd.t32' is not supported` | ✅ |

---

##### 四、独立注入测试（与 engineer 不同的注入目标）

**注入目标**：`.dd.t32` 的 Size 从 4 改为 2（使 `0x11223344` 溢出2字节字段）。

```
$ cd .work/source/llvm-project
$ sed -i '887s/Size = 4;/Size = 2;/' llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
$ git diff --name-only
llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
$ git diff
-    Size = 4;
+    Size = 2;
```
diff 非空，注入有效。✅

```
$ ninja -j8 -C .work/build/llvm llvm-mc
REBUILD_EXIT=0
$ printf '\t.text\n\t.dd.t32\t0x11223344\n' | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /dev/null 2>&1
<stdin>:2:10: error: value evaluated as 287454020 is out of range.
T32_EXIT=1
```
注入后 `.dd.t32 0x11223344` 报错（溢出）。FAIL 确认。✅

**还原 + 重建**：
```
$ git checkout -- llvm/lib/Target/DADAO/AsmParser/DADAOAsmParser.cpp
$ git diff --name-only
（空）
$ md5sum .../DADAOAsmParser.cpp
db5dea8cb8e7a404a2d8b3516df0cfde  （与注入前一致）
$ ninja -j8 -C .work/build/llvm llvm-mc
RESTORE_REBUILD=0
$ printf '\t.text\n\t.dd.t32\t0x11223344\n' | .work/build/llvm/bin/llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/opencode/LLVM-052t-review/restore-test.o 2>&1
T32_RESTORE=0
$ .work/build/llvm/bin/llvm-objcopy -O binary --only-section=.text restore-test.o restore-test.bin
$ od -An -v -tx1 restore-test.bin | tr -d ' \n'
11223344
```
还原后 `.dd.t32 0x11223344` → `11223344`（4字节，大端）。回绿。✅

**注入后 git 状态**：
```
$ cd .work/source/llvm-project && git status --short
（空）
```
源码干净，无残留。✅

---

##### 五、门控重跑

| 门控 | 命令 | 输出 | 退出码 |
|---|---|---|---|
| `make check-lit` | `make -C /mnt/tao/DADAO-v5 check-lit` | `Passed: 46 (100.00%)` | EXIT=0 |
| `make check` | `make -C /mnt/tao/DADAO-v5 check` | `repository checks: PASS` | EXIT=0 |
| `make test-codegen` | `make -C /mnt/tao/DADAO-v5 test-codegen` | `Results: 15/15 passed, 0 failed` | EXIT=0 |
| `check-patch-tree` | `make -C /mnt/tao/DADAO-v5 check-patch-tree` | `83 patches OK` | EXIT=0 |
| `check-source-state` | `make -C /mnt/tao/DADAO-v5 check-source-state` | `llvm-project: OK HEAD=3aea19491850 count=1 clean=True` | EXIT=0 |

---

##### 六、约束核验

| 约束 | 来源 | 核验结果 |
|---|---|---|
| 大端序（`contract-elf §1.1`：`ELFDATA2MSB`） | 任务书 §约束 | ✅ `DADAOMCAsmInfo::IsLittleEndian=false`；hexdump 逐字节验证 |
| octa=8B（非 GAS 16B） | 任务书 §约束 | ✅ `.dd.o64 0x1122334455667788` → 8 字节 `1122334455667788` |
| 不碰 `lib/MC` | 任务书 §输出 | ✅ 改动限 `AsmParser/` + `MCTargetDesc/`（3 文件） |
| 补丁纪律（`spec/Process-01`） | 任务书 §约束 | ✅ `make_patch.py` 导出、`series` 仍51、未手改 |
| `make check` EXIT=0 | 验收标准5 | ✅ |
| `make check-lit` 46/46 EXIT=0 | 验收标准5 | ✅ |
| `make test-codegen` 15/15 | engineer 完成区 | ✅ |
| `check-patch-tree` 83 patches OK | engineer 完成区 | ✅ |
| `check-source-state` clean count=1 | engineer 完成区 | ✅ |
| 一键证据含 `--inject` | 验收标准6 | ✅ 两轮注入 + 还原 + 重建 + 回绿 |
| 临时目录 `/tmp/opencode/LLVM-052t/` | 任务书 §约束 | ✅ 证据脚本 WORK 变量指向该目录 |
| 不提交 git | 任务书 §约束 | ✅ 源码 commit 未变（`3aea19491`），工作区干净 |

---

##### 七、三项关注判定

**7.1 ADR-0019 张力：ABS48 从指令 wyde 片扩用到数据绝对地址**

- **事实**：ADR-0019 D2/D4/D5 措辞将 `R_DADAO_ABS48` 限定为「`set.zw`/`or.w` 序列，3×`immu16`，按 wyde-position 分片」——即指令级地址构造。本次实现将其扩用为 `.dd.o64 <sym>` / `.quad <sym>` 的数据绝对地址重定位（8字节字段，linker 写48位值）。
- **张力点**：指令场景 reloc 挂在3条指令上（逐指令，依 wyde-position 分片）；数据场景 reloc 挂在1个8字节数据字段上（整体写入）。两者复用同一 reloc 类型，但 reloc 语义不同。
- **判定**：用户已口头裁定「ABS48是绝对地址，不区分指令和数据」，代码注释已标注。**该扩用在功能上合理**（数据8字节字段可承载48位地址），但 ADR-0019 正文措辞需更新以反映扩用。**必须走 ADR 流程补记**（`spec/Process-03`），但属文档/决策层待办，**不阻塞本实现**。建议：ADR-0019 D2 追加一条说明「ABS48 亦用于数据绝对地址（`.dd.o64`/`.quad`），8字节字段整体写入48位值，D6 overflow 仍适用」。

**7.2 REL12 未添加**

- **事实**：用户原文「REL12可以放在M4之后，如果你认为现在需要的话，也可添加」。本任务（`.dd.*` 数据指导符）不涉及 load/store 相对寻址，未添加 REL12。
- **判定**：**非阻塞，留后**。REL12 是能力缺口（非错值），建议另立任务。新增第5类 reloc 会改动已 Accepted 的 ADR-0019，须用户逐条确认。

**7.3 FK_Data_1/2/4 静默0（既有缺陷）**

- **事实**：`FK_Data_1/2/4`（如 `.long <sym>`/`.short <sym>`）在 `getRelocType` 中未映射，走 default `llvm_unreachable` 或既有路径，仍为「静默出0、无 reloc」行为。本任务只处理 `FK_Data_8`，未触及。
- **判定**：**既有缺陷，非本任务引入**。归 `LLVM-055t`（数据 reloc 一并处理）或另立任务。不阻塞本任务。

---

##### 八、前提错误判定

**任务书前提**：「`.octa` 此前被拒绝（既有拒绝行为）」。

**实测事实**：`.octa 0x1122334455667788` 此前被 generic MCParser 按 GAS 16字节静默接受（`.text` 出16字节、rc=0），**非拒绝**。

**contract-asm §7** 明确：「DADAO 的 octa =8字节，与 GAS 的 `.octa`（16字节）不同，MUST NOT 使用 GAS 的 `.word`/`.octa` 语义。」

**判定**：任务书前提有误（`.octa` 此前被接受，非被拒绝）。Engineer 正确识别了该前提错误，经用户裁定（「拒绝 .octa（推荐）」）后在 `parseDirective` 显式拒绝。修正后的实现**与 contract-asm §7 MUST NOT 一致**——GAS `.octa`（16字节）被拒绝，错误信息指向 `.dd.o64`。✅

---

##### 九、判决

**Accepted**

验收命令块在 reviewer 独立重跑下全部通过（25/25 + 15/15 + 门控全绿）；独立注入（`.dd.t32` Size 4→2）确认 FAIL→还原+重建→回绿；约束全部守住；三项关注均已给出明确判定（ADR 流程补记/留后/既有）；前提错误已修正且与 contract-asm 一致。

主会话可将任务状态改为 `已验证`。
