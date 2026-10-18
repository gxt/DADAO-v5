# LLVM-109t: 汇编注释符 `;`→`@@`（实现与迁移：`CommentString = "@@"` + `SeparatorString = ";"`）

**模块**：llvm
**项目里程碑**：M8
**依赖**：`SPEC-147t`（规范面已冻结：`@@` 注释、`;` 语句分隔符；`spec/Toolchain-01` 0.5.3）、`.tao/contracts/contract-asm.md §2.2`（0.5.3）、`docs/Process-01`（组件补丁树）、`docs/Process-05`（TDD/可达 FAIL）、`ADR-0013 D9.1`（被用户 2026-10-19 裁定**部分取代**；ADR 处置待用户确认，本册不改 ADR）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 用户授权（原话逐字，渠道 = 经主会话问答，2026-10-19）
> 「**很好，就改成 `@@` 了**」

`SPEC-147t` 已把规范改为「`@@` = 注释、`;` = 语句分隔符」；本册只做**实现 + 语料/工具迁移**，**不改 `spec/`**（`docs/Process-06` 授权只覆盖 `SPEC-147t` 的既有改动）。

## 问题根源

1. **当前实现**：`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch` 第 46 行 `CommentString = ";"`；`SeparatorString` 沿用 `MCAsmInfo` 默认 `";"`（`.work/source/llvm-project/llvm/include/llvm/MC/MCAsmInfo.h:133`）。`AsmLexer::LexToken` **先**判注释、**后**判语句分隔符（`AsmLexer.cpp:836-857`）⇒ 当前 `;` 永远被当注释，**一行多条语句不可达**。
2. **目标**：`CommentString = "@@"`、`SeparatorString = ";"`。单字符 `@` 不可用：clang 产出 `.type add,@function`、`.section ".note.GNU-stack","",@progbits`，单字符注释会误吞。
3. **LLVM 通用 MC 的 `@` 特例（关键坑）**：源码用 `CommentString.starts_with("@")` 判「ARM 式单 `@` 注释」，对 `@@` 也成立：
   - `llvm/lib/MC/MCParser/ELFAsmParser.cpp:721`：`if (!AllowAt && !getCommentString().starts_with("@")) setAllowAtInIdentifier(true);` ⇒ `@@` 下**不启用** `@` 标识符，`.type add,@function` 在 `:739-742` 报 `expected ...` **FAIL**。这是**功能必修点**，改成 `!= "@"`（仅单字符 `@` 触发 ARM 特例）。
   - `AsmLexer.cpp:113`（`AllowAtInIdentifier = !starts_with("@") && useAtForSpecifier()`）与 `ELFAsmParser.cpp:400`（错误文案分支）语义上是同一特例；DADAO `useAtForSpecifier()` 为 false、`:400` 只影响文案 ⇒ **最小改 `:721` 即可**，另两处**仅在探针证明需要时**改并记录理由。
   - `AsmParser.cpp:1651` 已是 `== "@"`，无需改。
4. **语料现状（现场实测，2026-10-19）**：`tests/**/*.s` 共 **99** 个文件、**3440** 行行首为 `;`、`;` 总出现 **3580** 次；`tests/llvm/lit/MC/DADAO/*.s` 的 **87** 条 `CHECK` 全为 `;` 前缀；`tests/llvm/lit/MC/DADAO-gen/*.s` 12 个文件由 `tools/testcases/generate_lit_vectors.py` 生成（**禁手改**）。
5. **直接翻 `CommentString` 的后果**：旧 `;` 注释行变成「空语句 + 若干标识符」⇒ 通常报 `unrecognized instruction mnemonic`，但若注释文本碰巧像指令则**可能静默编错**。因此迁移必须**先改语料、再翻常量**（同一提交内），让中间态**响亮失败**而不是静默错。

## 接口规范

### A. MC 配置（`DADAOMCAsmInfo.cpp`）

```cpp
// DADAO uses "@@" as the comment string and ";" as the statement separator.
CommentString = "@@";
SeparatorString = ";";   // 显式写出（默认已是 ";"；同时作为规范锚点）
```

- `AllowAdditionalComments = false` 不变。
- 变更须在 `.work/source/llvm-project` 改源码 → 按 `docs/Process-01` 用 `tools/infra/make_patch.py` 重新导出补丁；**禁**手工编辑 `.patch`。

### B. 迁移顺序（硬约束，同一提交）

1. **先**迁移语料与工具（`tests/**/*.s`、生成器、解析器）；
2. **再**改 `CommentString`；
3. **同一提交**内完成，**不得**分两次提交。中间态**不可运行**（先翻常量 ⇒ 旧注释当语句；先改语料 ⇒ `@@` 尚未成为注释），故 1/2 之间**不得**跑门控下结论。

### C. 语料迁移规则

- 逐文件：每行**第一个** `;`（**字符串字面量之外**）是注释引导符 ⇒ 改 `@@`；注释文本内后续 `;` **保留**（如 `0x11; the ...`）。
- 行首 `;`（含 `; RUN:`/`; CHECK:`/`; OBJ:`/`; ASM:`/`; @src`）⇒ `@@ ...`。
- `tests/llvm/lit/MC/DADAO-gen/*.s`：改 `tools/testcases/generate_lit_vectors.py` 的模板后**重生成**（`python3 tools/testcases/generate_lit_vectors.py`），**禁**手改生成物。
- **不动** `.ll`（LLVM IR 注释 `;` 与汇编无关）、不动 `.c/.h` 的 C 分号、不动 `tests/**` 外的上游源码。
- `.asciz/.string` 内的 `;` 若存在，**不得**改；迁移后须用 `grep` 复核无字符串被误改。

### D. 工具同步（现场 grep 命中，逐文件）

- `tools/testcases/generate_lit_vectors.py`：`; RUN:`/`; @src`/`; OBJ:`/`; ASM:`/`; UNREC:`/banner 模板 → `@@`。
- `tools/testcases/check_lit_gen.py`：`; @src` / `; OBJ:` 正则与 docstring。
- `tools/testcases/validate_mc_vectors.py`：`; OBJ:` / `; @src` 解析。
- `tools/llvm/check_lit_bytes.py`：`OBJ_RE` / `OBJ_LITERAL_RE`（`;` → `@@`）。
- `tools/llvm/test_encoding_oracle.py:447`：`' ; OBJ:'` 判定。
- `tools/integ/check_interface_alignment.py`：注释/调用面（按实际 grep 结果改）。
- `tools/llvm/gen_isa_coverage.py`：若解析 `;` 前缀则同步（现场核查；无命中则不改）。
- 验收：`grep -rn '; OBJ:\|; RUN:\|; CHECK\|; @src' tools/ tests/ --include='*.py' --include='*.s'` 应为 **0**（历史 changelog/`.tao/archive` 除外）。

### E. 组件补丁与台账

- 更新 `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOMCAsmInfo.cpp.patch`（`CommentString`/`SeparatorString` 两行 + 注释）。
- 若 `:721` 通用修复必要：新增 `components/llvm-project/patches/llvm/lib/MC/MCParser/ELFAsmParser.cpp.patch`（一文件一补丁），加入 `series`（81 → 82，路径字典序），`check-patch-tree` 现场派生计数并记录。
- `components/llvm-project/changelog.md` 追加 `## M8` 条目（按任务一条，列表式）。

## 验收标准

1. **MC 配置**：`DADAOMCAsmInfo.cpp` 终态含 `CommentString = "@@"` 与**显式** `SeparatorString = ";"`；补丁树经 `make check-patch-tree` / `make check-source-state` rc=0。
2. **printer**：`clang --target=dadao-unknown-elf -S` 产物注释符为 `@@`（如 `@@ -- Begin function`、`@@ %bb.0:`），**无** `;` 注释。
3. **一行多条（端到端）**：
   ```bash
   printf 'add.si rb1, -8 ; add.uo {rd0, rd8}, rd17, rd16 ; ret rd0, 0\n' \
     | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/opencode/LLVM-109t/multi.o
   llvm-objdump -d --triple=dadao-unknown-elf /tmp/opencode/LLVM-109t/multi.o
   ```
   ⇒ 反汇编**恰 3 条**且顺序/字节正确；`-filetype=asm` 往返输出 3 行（可规范化分行）。
4. **`.type` / `@progbits` 不被误吞**：
   ```asm
   .text
   .globl add
   .type add,@function
   add:
     add.si rb1, -8
     ret rd0, 0
   .size add, .-add
   .section ".note.GNU-stack","",@progbits
   ```
   ⇒ `llvm-mc` rc=0；`llvm-readelf -s` 中 `add` 类型为 `FUNC`。修 `ELFAsmParser.cpp:721` 前应 FAIL（**可达 FAIL 证据**）。
5. **语料零残留**：`grep -rn -E '^[[:space:]]*;' tests/ --include='*.s'` = **0**；`grep -rn '; OBJ:\|; RUN:\|; CHECK\|; @src' tests/ --include='*.s'` = 0；迁移后 `lit` MC/DADAO **全部 PASS**、`check-lit-full`（DADAO-gen）PASS。
6. **工具/编码门控**：`check_lit_gen.py`、`check_lit_bytes.py`、`validate_mc_vectors.py`、`check-interface`（含 `check_interface_alignment`）rc=0；`make check`（L1）rc=0。
7. **安装根复验**：`make install-host` 后（`JOBS=8`、不并发、`ISS-210`；**先申报预计耗时**）用**安装根** `clang`/`llvm-mc` 重跑第 2–5 项（不得只凭 `.work/build` 树下结论）；L2 `make check-modules`、L3 `make check-full` 由主会话执行并如实记录。
8. **可达 FAIL（两处，均须注入→红→还原→绿）**：
   - ① 在临时副本 `.s` 加一行 `; note` ⇒ 汇编必须 FAIL（`;` 已是分隔符，`note` 非法）；还原用 `cp` + md5 对账。
   - ② 把 `CommentString` 临时改回 `";"` ⇒ 一行三条语句用例应只反汇编 1 条（后两条被吞）⇒ FAIL；还原回绿。
   - ③ 撤销 `:721` 修复 ⇒ `.type add,@function` 必须 FAIL；恢复后 PASS。
9. **证据**：`.work/evidence/<任务ID>/run.sh`（default + `--inject`）rc=0；日志落 `.work/log/llvm/LLVM-109t-*.log`；完成区贴真实输出/退出码。

## 不做项（显式）

- 不改 `.ll`、不改 C/C++ 源码注释。
- 不改上游 `spec/` 只读册（其 `;` 示例由上游另行生成新版）。
- 不把 `;` 重新定义为注释；不引入第三种注释符。
- 不改 ADR-0013 正文（处置待用户确认）。
- 不 `push`（提交后由主会话收尾）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录
