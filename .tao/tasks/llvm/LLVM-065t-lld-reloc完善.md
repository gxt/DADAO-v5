# LLVM-065t: lld reloc 完善（`REL12` + 新类型 + `FK_Data_*`）

**模块**：llvm
**项目里程碑**：M6
**依赖**：`SPEC-123t`（reloc 正文 + 锁）、`INFRA-050t`（一次构建含 `ld.lld`）
**状态**：待开始

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
2. **`FK_Data_1/2/4` 不再静默 0**：`.byte/.short/.long <sym>` 发对应 reloc 且链接结果正确（给真实输出）。
3. **`ABS48` 数据表示**：数据 8 字节字段 = 48 位地址、大端、高 16 位 0（`ISS-154`；给真实输出）。
4. **`ISS-108`**：目标文件拆分后仍 ≤1000 行（或给「不拆」的正当理由）；`grep`/`wc -l` 证据。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等**）。
6. **`spec/` 交集为空**：`git diff --name-only | grep -E '^spec/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-065t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检，给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

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

## 归属登记（architect 追加，2026-10-09）

- **`ld.*/st.* [rbN, sym]` 的 MC 侧符号偏移 fixup 未实现**（`TESTCASES-036t` 实证）：`llvm-mc --triple=dadao-unknown-elf -filetype=obj` 吃 `ld.o rd8,[rb0,target]` ⇒ `LLVM ERROR: DADAO: no PC-relative fixup kind …`、`Aborted`、`rc=134`（即 `llvm-mc` 在 MC 层就失败，先于 LLD）。
- **归属判定**：本任务**输出 2** 已含 `DADAOFixupKinds`/`DADAOMCCodeEmitter`（MC 侧 fixup），**验收 1** 覆盖 `ld/st …, [rb1, sym]` 的 reloc ⇒ 该 MC 侧 fixup 缺口**属本任务范围**（无需另立 issue）。
- `TESTCASES-036t` 已落 L1 期望向量 `tests/llvm/lit/MC/DADAO/m6-ldst-symbol.s`（`REQUIRES:` 暂缓）；本任务就绪后去除 `REQUIRES:` 即转正常 lit。**本登记仅记归属，不改任何 decision。**
