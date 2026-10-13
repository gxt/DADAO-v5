# LLVM-065t: lld reloc 完善（`REL12` + 新类型 + `FK_Data_*`）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`SPEC-123t`（reloc 正文 + 锁）、`INFRA-050t`（一次构建含 `ld.lld`）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 接口规范

- **输入**：
  - `.tao/knowledge/contract-elf.md §2–§4`（`SPEC-123t` 落定的 reloc 正文：`REL12` + 新专用类型 + `ABS48` 数据 8B 字段）。
  - 已 `Accepted` 的 reloc 体系 ADR（拟 `.tao/adr/adr-0021-*.md`）。
  - `.tao/adr/adr-0019-dadao-relocation-types.md`（现有 reloc 集 D1–D8；`ABS48` 数据 8 字节字段）。
  - `.tao/knowledge/issues.yaml`：`ISS-151`（访存符号偏移落 `REL20`）、`ISS-161`（`REL12` 缺失 + `FK_Data_1/2/4` 静默 0）、`ISS-154`（`ABS48` 数据表示）、`ISS-108`（文件 >1000 行）。
- **输出**：
  1. `components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp`（+ `Target.{cpp,h}` 注册）：实现 **`REL12`** + **新专用类型**（`ISS-151`/`ISS-161`；**不复用 `REL20`**；覆盖**超出 `REL12`** 情形；与 `contract-elf §2–§4` 一致）。
  2. `DADAOELFObjectWriter`/`DADAOMCCodeEmitter`/`DADAOFixupKinds`：**`FK_Data_1/2/4`（`.byte/.short/.long <sym>`）不再静默出 0**（发对应 reloc）；`ABS48` **数据 8 字节字段表示**（`ISS-154`：48 位地址、大端、高 16 位 0）。
  3. `ISS-108`：**拆分** >1000 行文件（`DADAOInstrInfo.td` 1304 / `DADAOAsmParser.cpp` 1091）。
  4. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 与 `SPEC-123t` 的正文/ADR **一致**；**不**沿用 legacy `Dadao.def` 编号/公式（`contract-elf §2`）。
  - 越界 ⇒ link-time error（`adr-0019 D6`：不截断、不 wrap）。
  - **`spec/` 交集为空**。
  - 与 Wave 2 **同改 `components/llvm-project/patches` ⇒ 串行**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-065t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-065t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁 `tee`**。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **重建成本申报**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLD（增量），预计 N 分钟」；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-065t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **`REL12` + 新类型**：`ld/st …, [rb1, sym]` 产生**正确 reloc 类型**（新专用类型；不再落 `REL20`）；超出 `REL12` 情形有**明确处理**（给 `readelf -r` 真实输出 + `ISS-151/161` 收口证据）。
2. **`FK_Data_1/2/4` 不再静默 0**：**可重定位符号 ⇒ 显式报错**（报错路径可达、非凑绿）；**`.quad`/`.dd.o64 <sym>` 发 `ABS48` 且链接正确**（给真实输出）。
   > **更正说明（2026-10-10，据 reviewer 判定）**：原措辞「`.byte/.short/.long <sym>` 发对应 reloc 且链接结果正确」**不可达**（`contract-elf §2.2` 类型集无更窄数据 reloc、`ADR-0019 D8` 禁 `ABS32`），按 Spec-first 以契约为准取「显式报错」，实现与验收结论不变。
3. **`ABS48` 数据表示**：数据 8 字节字段 = 48 位地址、大端、高 16 位 0（`ISS-154`；给真实输出）。
4. **`ISS-108`**：目标文件拆分后仍 ≤1000 行（或给「不拆」的正当理由）；`grep`/`wc -l` 证据。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-065t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：`make build-mc`/`build-lld`/`install-host` EXIT=0；`make check` EXIT=0（83 门控项全 PASS、`validate-vectors` 149/149、lit 全绿）；`make check-patch-tree` EXIT=0（3 组件 / 109 patches）；`make check-lit` EXIT=0（**79 discovered / 79 PASS**，不下降）。证据脚本 `.work/evidence/LLVM-065t/run.sh` `RUN_EXIT=0`（默认 16 项 + `--source-inject` 4 项）。日志 `.work/log/llvm/LLVM-065t-*.log`。

**修改文件**：`components/llvm-project/patches/llvm/include/llvm/BinaryFormat/ELFRelocs/DADAO.def.patch`、`.../MCTargetDesc/{DADAOFixupKinds.h,DADAOMCCodeEmitter.cpp,DADAOELFObjectWriter.cpp,DADAOAsmBackend.cpp}.patch`、`components/llvm-project/patches/lld/ELF/Arch/DADAO.cpp.patch`、`components/llvm-project/changelog.md`、`tests/llvm/lit/MC/DADAO/m6-ldst-symbol.s`（去 `REQUIRES:`）、`tests/llvm/lit/MC/DADAO/m6-data-narrow-reject.s`（新增）、本任务书。（`series` 未变仍 71；未触 `spec/`/`contracts/`/`.opencode/`/`AGENTS.md`；`.work/**` 不入 git。）

**验收结果**（真实输出）：
- **①`REL12`/`ABS12`+越界**：`llvm-readobj -r ldst.o` → `Offset: 0x0 / Type: R_DADAO_REL12 (4)` + `Offset: 0x4 / Type: R_DADAO_ABS12 (5)`（**无 `REL20`**）；越界（far=+4104）⇒ `ld.lld: error: ... relocation R_DADAO_REL12 out of range: 4104 is not in [-2048, 2047]` rc=1（`ABS12` 同）。
- **②`FK_Data_1/2/4`**：`.long/.short/.byte ext` ⇒ `error: relocatable operand in a 1/2/4-byte data field ... cannot carry a 48-bit DADAO address; use '.dd.o64'/'.quad'`（3 条）rc=1——**不再静默 0**；`.quad/.dd.o64 <sym>` 仍发 `ABS48`。
- **③`ABS48` 数据 8B 字段**：链接后 `objcopy -O binary -j .data` = `00000000000000000000000000000010`（`ptr=.quad target(0x10)`；**48 位、大端、高 16 位 = 0**）。
- **④`036t` 遗留**：`llvm-mc … -filetype=obj ldst.s` **rc=0**（改前 `LLVM ERROR … no PC-relative fixup kind`、rc=134）。
- **⑤门控**：`build-mc`/`check-patch-tree`/`check-lit`/`check` 四者 rc=0（见上）。
- **⑥证据脚本**：`run.sh` → `EVIDENCE: PASS`；注入自检 C10（fixture `[rb0]→[rb1]`⇒`ABS12`⇒C1 FAIL⇒md5 还原⇒回绿）+ S1（源码 `REL12→REL14`⇒`make build-mc`⇒C1 FAIL⇒`cp`+md5 还原⇒重建⇒回绿）。
- **⑦`spec/` 交集**：`git diff --name-only | grep '^spec/'` 空；`git status` 无 `*_tmp*`/`*.orig`/`*.rej`。

**新发现/坑**：① **`FK_Data_1/2/4` 裁决**（用户问答未能取得裁定）：`contract-elf §2–§4` 数据 reloc **只有 8 字节 `ABS48`**、`ADR-0019 D8` 禁 `ABS32`/更窄类型 ⇒ 1/2/4 字节字段装不下 48 位地址，「**发对应 reloc 且链接结果正确**」（验收 2）**在合约下不可能**；按 Spec-first 取 **option ①**（可重定位符号 ⇒ **显式报错**，不静默 0/不截断），与 M4 `.dd.b08/.w16/.t32` 先例一致。**验收 2 措辞与合约冲突，已披露**，待主会话/reviewer 裁定。② `ld/st` 的选择器须查 `Inst.getOperand(1)` 的基址寄存器（`rb0=hw0`）——退化为「按指令格式」会漏掉基址区分。③ 同 section 的 `REL12` 就地解析走 `evaluateFixup`（与 `call` 同机制），跨 section/绝对才发 reloc。

**遗留问题**：① **`ISS-108`（拆分 `DADAOInstrInfo.td`/`DADAOAsmParser.cpp`）按用户 2026-10-09 裁定推迟 M7，本任务未做拆分**（任务书「输出 3 / 验收 4」相应不适用）。② 验收 2 措辞与合约冲突（见「新发现」①）。③ `ISS-151`/`ISS-161`/`ISS-154` 的实现面已收口；台账状态更新归主会话。

## 审阅记录

#### 第 1 轮 engineer 自审

**自审范围**（逐行）：`DADAO.def`、`DADAOFixupKinds.h`、`DADAOMCCodeEmitter.cpp`、`DADAOELFObjectWriter.cpp`、`DADAOAsmBackend.cpp`、`lld/ELF/Arch/DADAO.cpp`、`m6-ldst-symbol.s`、`m6-data-narrow-reject.s`、`run.sh`。**核对**：Spec-first（`contract-elf §2–§4`/`ADR-0019`/`ADR-0021`）、防造假（真实输出、注入可达 FAIL 且 `cp`+md5 还原、无 `tee`）、边界（仅 `components/llvm-project/**`+`tests/llvm/**`+本任务书）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 `FK_Data_1/2/4`：1/2/4 字节装不下 48 位地址、合约无更窄 reloc；验收 2 要求「发 reloc」不可达 | ✅已决（披露） | 取 option ①：可重定位符号 ⇒ 显式报错；已解析绝对值按大端写入（宽度检查） | C4（3 条 error，rc=1）；`--source-inject` 证明实现必要 |
| F2 `ld/st` 需按基址寄存器选型（`rb0`⇒`REL12`） | ✅已修 | `getMachineOpValue` 查 `Inst.getOperand(1)` 的 `dadaoRegHW` | C1a/C1b：`[rb0]⇒REL12(4)`、`[rb9]⇒ABS12(5)` |
| F3 `REL12`/`ABS12` 是**字节**偏移（**不 `>>2`**），易与 `REL14` 混淆 | ✅已修 | `applyFixup`/`relocateInSection` 对两类型直接写 `imms12`（无移位），改前 `Value==0` 捷径置于其后 | C6 链接字节 `20200010 21209010 ...`（偏移 0x10） |
| F4 `036t` 遗留（`llvm-mc` `rc=134`） | ✅已修 | 新增 ld/st 分支，不再落 `report_fatal_error`/`REL20` | C2 rc=0；C1c 无 `REL20` |
| F5 `ABS48` 数据 8B 高 16 位须为 0（`ISS-154`） | ✅已修 | lld `ABS48` 数据路径显式 `val & 0x0000FFFFFFFFFFFF` | C5：`.data` = `...0000000000000010` |
| F6 `series`/`changelog` 随任务追加 | ✅已办 | `series` 无新文件（仍 71，`make_patch` 幂等）；`changelog.md` 追加本行 | `check-patch-tree` EXIT=0 |
| F7 `iss108` 拆分 | ⏸延后 | 未拆（用户 2026-10-09 裁定推迟 M7） | 「遗留问题」① |

**判决**：finding 全部处置（F7 为授权延后）⇒ 状态置「待验收」，返回主会话 `/complete`。

#### 第 1 轮 reviewer 验收

**独立重跑记录**（全部 reviewer 自跑，非采信完成区；fixture 独立编写于 `/tmp/opencode/LLVM-065t-review/`）：
- **①reloc 类型+语义**（r1.s：`ld.o rd5,[rb0,targ]`/`st.o rd6,[rb3,targ]`/`ld.o rd7,[rb4,targ]`/`st.o rd2,[rb0,targ]`，前垫 2×swym 使 P≠0）：`llvm-readobj -r` → `Offset 0x8 REL12(4)/0xC ABS12(5)/0x10 ABS12(5)/0x14 REL12(4)`，**无 REL20**，rc=0；链接（targ S=0x18）后 `.text`=`77880000 77880000 20140010 21183018 201c4018 21080004`：**逐条自算**——0x8 低 12 位 `0x010`=S+A−P=0x18−0x8 ✓（非 `>>2`=4、非 −4=0xC）、0xC `0x018`=S+A ✓、0x10 `0x018`=S+A ✓、0x14 `0x004`=0x18−0x14 ✓；改前字低 12 位全 0，仅低 12 位变化 ✓（REL12=S+A−P 字节偏移、ABS12=S+A、按基址 rb0/非 rb0 选型均成立）。
- **②越界**：far.s（`.space 4096`）→ `ld.lld: error: ... relocation R_DADAO_REL12 out of range: 4104 is not in [-2048, 2047]` + `R_DADAO_ABS12 out of range: 4104 ...`，**link rc=1**、无产物、**不截断/不 wrap**（4104&0xfff=0x18 未落盘）。
- **③FK_Data_1/2/4**：`.long/.short/.byte ext` ⇒ 3 条 `error: relocatable operand in a 1/2/4-byte data field ... use '.dd.o64'/'.quad'`，**rc=1**，不再静默 0 ✓。
- **④ABS48 数据 8B**：`.quad ext` ⇒ `R_DADAO_ABS48 (0)`；`--defsym ext=0xABCD12345678` 链接后 `.data`=`0000abcd12345678`（**大端、48 位、高 16 位=0**）；`ext=0x1234ABCD12345678` ⇒ `R_DADAO_ABS48 out of range` rc=1（不截断）。
- **⑤036t 收口**：自写 `ld.o rd5,[rb0,targ]` 等 4 条 `llvm-mc -filetype=obj` **rc=0**（改前 134）。
- **⑥门控**（一次一个 make）：`make check-patch-tree` rc=0（3 组件/109 patches）；`make check-lit` rc=0（**79 discovered/79 PASS，0 failed/0 unsupported**）；`make check` rc=0（`repository checks: PASS`、gate **149 total/149 passed**）。
- **⑦证据脚本**：审 `.work/evidence/LLVM-065t/run.sh`（262 行）——期望 reloc 号**派生自 contract-elf §2.2 表**（REL12=4/ABS12=5 现场解析）、各断言有可达 FAIL 路径、无 `tee`、`rc=$?` 捕获自身码、C10 注入非空（md5 变）+ `cp`+md5 还原；重跑 **RUN_EXIT=0**（16 项全 PASS）。**独立注入**（与 S1a–d 不同，改 **LLD `checkInt` 边界 12→14**，`cp`+md5 备份=`8a6b807…`）⇒ `JOBS=8 make build-lld`（BUILD_RC=0）⇒ 重跑同一脚本 **RUN_EXIT=1**（`[FAIL] C7 ... actual=rc0`，`EVIDENCE: FAIL (1 failed)`）⇒ `cp` 还原（md5 与备份**相等**）⇒ 重建（BUILD_RC=0）⇒ 重跑 **RUN_EXIT=0**（`EVIDENCE: PASS`）⇒ `check_patch_tree.py --source-state` rc=0（3 组件 `clean=True`）。
- **⑧补丁/残留**：`components/llvm-project/series` = **71**（= 该组件补丁数，一文件一补丁）；`git status --porcelain -uall` 仅 6 补丁+`changelog.md`+2 lit+任务书（与完成区「修改文件」逐条对齐）；`git diff --name-only | grep '^spec/\|^contracts/'` 空；无 `_tmp/_orig/_rej`；**审查前后快照对账**：`snapshot-pre == snapshot-post`、改动文件 md5 **逐一相等**（还原纪律未用 git 还原命令）。

**第 3 条判定**：`FK_Data_1/2/4` 显式报错**与合约一致**——`contract-elf §2.2` 类型集（0–5 + NUM=6）**无更窄数据 reloc**、`§3.2` 禁静默 0/截断、`ADR-0019 D8` 禁 `ABS32`，1/2/4 字节字段**不可能**承载 48 位地址 ⇒ **验收 2「发对应 reloc 且链接结果正确」措辞不可达，应改为**「可重定位符号 ⇒ **显式报错**（不再静默 0）；`.quad/.dd.o64 <sym>` 发 `ABS48` 且链接结果正确」。**非造假、非凑绿**：报错路径可达且非空，`.quad` 路径已验证发 `ABS48` 并链接正确。

**约束核验**：REL12/ABS12/NUM=4/5/6 与 `contract-elf §2.2` 逐项相等 ✓；越界 link-time error（ADR-0021 D3/ADR-0019 D6）✓；ISS-108 按用户裁定推迟 M7（不拆分，已披露）✓；`spec/`/`contracts/` 交集空 ✓；不回归（check/check-lit/check-patch-tree rc=0、79/79、149/149 不下降）✓；仅动任务范围 ✓。

**非阻断备注**：① run.sh C8 用 `git diff --name-only` 查 `spec/`，**漏 untracked**（C9 的 `git status` 部分补位）；② C7 只测 REL12 越界（ABS12 越界由 reviewer 独立补测，报错成立）；③ C5 用低地址 0x10，48 位高位特性由 reviewer 用 `0xABCD12345678` 独立补测。均不改判。

**判决**：**Accepted**（验收 1–8 全部经 reviewer 独立重跑通过；验收 2 措辞按上述判定改写，属任务书文字修订，非实现缺陷）。

## 归属登记（architect 追加，2026-10-09）

- **`ld.*/st.* [rbN, sym]` 的 MC 侧符号偏移 fixup 未实现**（`TESTCASES-036t` 实证）：`llvm-mc --triple=dadao-unknown-elf -filetype=obj` 吃 `ld.o rd8,[rb0,target]` ⇒ `LLVM ERROR: DADAO: no PC-relative fixup kind …`、`Aborted`、`rc=134`（即 `llvm-mc` 在 MC 层就失败，先于 LLD）。
- **归属判定**：本任务**输出 2** 已含 `DADAOFixupKinds`/`DADAOMCCodeEmitter`（MC 侧 fixup），**验收 1** 覆盖 `ld/st …, [rb1, sym]` 的 reloc ⇒ 该 MC 侧 fixup 缺口**属本任务范围**（无需另立 issue）。
- `TESTCASES-036t` 已落 L1 期望向量 `tests/llvm/lit/MC/DADAO/m6-ldst-symbol.s`（`REQUIRES:` 暂缓）；本任务就绪后去除 `REQUIRES:` 即转正常 lit。**本登记仅记归属，不改任何 decision。**
