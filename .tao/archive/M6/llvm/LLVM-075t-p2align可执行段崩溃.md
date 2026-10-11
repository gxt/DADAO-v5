# LLVM-075t: `.p2align`（可执行段）使 `llvm-mc` 崩溃【缺陷】

**模块**：llvm
**项目里程碑**：M6
**依赖**：`INFRA-050t`（一次构建 `DADAO;X86`）、`LLVM-062t`/`LLVM-063t`/`LLVM-069t`（均已 `已验证`）、`QEMU-052t`（ELF 加载，`已验证`）；**与 Wave 2 其它 llvm 任务同改 `components/llvm-project/patches` ⇒ 串行**
**状态**：已验证

> **覆盖缺口**：**`ISS-182`**（缺陷）。

## 用户裁定（2026-10-10，原话/结论）

> 用户 **2026-10-10 裁定：4 条缺口（`ISS-182` / `ISS-185` / `ISS-186` / `ISS-181`）全部纳入 M6**（「10 点前完不成 ⇒ 全加、跑一晚上」）。本任务 = 其中 **`ISS-182`（缺陷，优先）**。

## 执行环境
**执行环境**：本地

## 背景 / 问题根源（自包含）

- **现象（缺陷）**：`.text`（可执行段）内 `.p2align N`（N≥1）或 `.align N`（N≥2）⇒ `llvm-mc` **rc=134/141**，断言 `MCAssembler.cpp:588 The stream should advance by fragment size`；**`.rodata` 内同指令正常**（rc=0）。
- **最小复现**：`printf '.text\n.byte 1\n.p2align 3\n.byte 2\n' | llvm-mc --triple=dadao-unknown-elf -filetype=obj -o /tmp/x.o /dev/stdin`（**须先自行复现**，给真实 rc + 断言原文）。
- **可疑根因**：`DADAOAsmBackend::writeNopData`（源 `MCTargetDesc/DADAOAsmBackend.cpp:299`，**已实现**）——当前实现按 `for (I=0; I<Count; I+=4) OS.write("\x77\x88\x00\x00", 4);` 每次写 **4 字节**；当所需对齐填充 `Count` **非 4 的倍数**时**写超**（向上取整）⇒ 实际推进字节数 ≠ fragment 尺寸 ⇒ 触发该断言。**须先诊断确认根因**（区分「`writeNopData` 尺寸错」与「对齐 fragment 尺寸算错」两说），再修。
- **影响**：真实 C 代码在 `.text` 内做块对齐即触发（`llc` 会发 `.p2align`）——**编译期显式失败**（非静默错码）。
- **性质 = 缺陷（`llvm-mc`/汇编路径崩溃）**。

**证据指针**：`.work/log/integ/pending-registrations.md §R2`；issue `ISS-182`；可疑根因源 `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`。

## 接口规范

- **输入**：
  - `components/llvm-project/patches/llvm/lib/Target/DADAO/**`（源树 `.work/source/llvm-project`），重点 `MCTargetDesc/DADAOAsmBackend.{h,cpp}`（`writeNopData`）。
  - `.tao/knowledge/contract-isa.md`（指令宽度 4 字节、`swym` NOP 语义）；`spec/Process-01-组件补丁组织与构建编排.md`（补丁纪律）。
- **输出**（`components/llvm-project/patches/llvm/lib/Target/DADAO/**` + 必要的 `tests/llvm/**`/`tests/e2e/**`）：
  1. **修复**：可执行段 `.p2align`/`.align` 汇编 **rc=0**，且**填充字节数正确**（对齐后偏移 = 目标对齐；填充内容为**合法** NOP/填充，不越界写）。
  2. 受影响 `tests/llvm/**`/`tests/e2e/**` 期望值按册/契约**重新派生**（**不从实现反填**）；新增向量覆盖 `.text` 内 `.p2align`。
  3. `series`/`changelog.md` 随任务追加（`Process-01`）。
- **约束**：
  - 语义/宽度口径来自 `spec/`/`contracts`（**不从实现反推**，Spec-first）。
  - **不改 `spec/`/`contracts/`**（`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出）；纯缺陷修复 ⇒ 无新决策、无需 ADR。
  - 若修复须触及 LLVM **通用 MC 代码**（`llvm/lib/MC/**`）⇒ **停下报告**（优先 target-scoped 修复，避免动上游共享层）。
  - 计数口径**派生自单一真源、不硬编码**。

## 硬约束

- **临时目录** `/tmp/opencode/LLVM-075t/`；禁仓库内临时文件（进 git 的产物/脚本除外）。
- **不提交 git**（提交由 architect 判断执行，须经用户确认）。
- **完成区与真实输出逐条对齐**：留证**捕获被检命令自身退出码**，**禁** `cmd | tee log; echo $?`（用 `rc=$?` / `${PIPESTATUS[0]}` / `set -o pipefail`）。
- **只动任务范围**；越界须在完成区披露。
- **失败即停、禁自动重试**（含换参数/换等价命令/改代码重跑）；保留失败现场并报告。
- **`Process-01` 补丁纪律**：树形补丁集 + 一文件一补丁 + `git apply`；`make check-patch-tree` 断言⑥绿。
- **一键证据脚本** `.work/evidence/LLVM-075t/run.sh`：非交互；**任一检查失败即非零退出**；逐项打印「检查名 + 期望/实际 + 退出码」；**内置注入反例 → 预期 FAIL → `cp`+md5 还原 → 预期回绿**；结尾**禁** `tee`。
- **还原纪律**：**禁** `git checkout`/`git restore`/`git stash`，**亦禁** `git show <commit>:<path> > <path>`；一律 `cp` 备份 + `md5sum` 对账（或优先临时树注入），以**注入前快照**（`git status --porcelain -uall` + 目标文件 md5）逐行对账；`git status`/`git diff` 干净**不作**「已还原」证据。
- **注入有效性**：注入后须验 `git -c core.quotepath=false diff --name-only` **非空**；还原须**含重建**（源码还原 ≠ 二进制还原）。
- **重建成本申报 + 脱离工作区生命周期**：改 `components/llvm-project/patches/**` ⇒ 开工前写明「重建 LLVM（增量），预计 N 分钟」；**长构建须 `setsid nohup … >log 2>&1 &` 脱离 opencode 工作区**（`lessons §8.21`），落盘完成标记（`EXIT=$rc`），**禁**会话内后台等待器；一次构建、勿零散重跑。
- **计数不写死**：文档/注释/任务书/验收**不硬编码计数**；需要时由脚本/门控**现场统计**，或写「**不下降 / 逐项相等**」；门控计数须**派生自单一真源**。
- 复杂命令输出留 `.work/log/llvm/LLVM-075t-<命令名>.log`（**不得只留 `/tmp`**）。

## 验收标准

1. **可执行段 `.p2align` 可汇编**：`.text` 内 `.byte 1` + `.p2align N`（N=1..4）`llvm-mc` **rc=0**（给真实命令 + rc），且**填充字节数正确**（对齐后偏移 = `2^N` 的倍数；如 `.byte 1`+`.p2align 3` ⇒ 段尺寸 8；给 `readelf`/`llvm-objdump`/`od` 实测证据），填充为**合法** NOP/填充字节。
2. **`.rodata` 不回归**：`.rodata` 内 `.p2align` 仍 rc=0 且填充正确（对齐前后逐字节核对）。
3. **`.align` 口径披露**：实测 `.align N`（若仍受理）= 字节语义、与 GAS 的 `2^N` 不同；**本任务不裁决 `.align` 去留**（该项归 `LLVM-078t`），但须**如实记录**其现状，若 `.align` 与 `.p2align` 共用同一修复路径则一并覆盖。
4. **E2E**：一段**含 `.text` 内对齐**的程序经「编译 → 链接 → QEMU 执行 → **正确退出码**」端到端通过（给真实命令 + 退出码）。
5. **不回归**：`make build-mc`/`make check`/`make check-patch-tree`/`make check-lit` EXIT=0（通过数与改前**逐项相等 / 不下降**）。
6. **`spec/` 交集为空**：`git -c core.quotepath=false diff --name-only | grep -E '^(spec|contracts)/'` → 无输出。
7. **一键证据脚本**：`.work/evidence/LLVM-075t/run.sh` 逐项通过、`RUN_EXIT=0`；含注入自检（**复现原缺陷**：如把 `writeNopData` 改回「每次写 4 字节 / 尺寸错误」⇒ 断言 FAIL/rc≠0 ⇒ `cp`+md5 还原 ⇒ 重建 ⇒ 回绿），给真实输出与退出码。
8. **无残留**：`git status --porcelain -uall` 仅本任务应有改动；无 `*_tmp*`/`*.orig`/`*.rej`。

## 完成区

**测试结果**：全绿。证据脚本 `.work/evidence/LLVM-075t/run.sh`：`PASS=11 FAIL=0 RUN_EXIT=0`。
① `.text` `.byte 1`+`.p2align N`（N=1..4）逐档 **rc=0**，段尺寸实测 **3/5/9/17**（=1+2^N−1，`llvm-objdump -h`），字节 `010002` / `0100000002` / `010000007788000002` / `0100000077880000778800007788000002`（`llvm-objdump -s`）；任务例 `.byte 1`+`.p2align 3` ⇒ **size 8**、填充 `00 00 00 77 88 00 00`（`swym 0`）。
② `.rodata` `.byte 1`+`.p2align 3`+`.byte 2` rc=0、size 9、字节 `010000000000000002`（纯 0 填充，不回归）。
③ E2E（真链接）：`llvm-mc`×2=0 → `ld.lld -T dadao.lds`=0 → `qemu -M dadao-m1 -kernel` guest exit=**0**（`main` 落穿 3 条 `swym 0` 对齐填充）。
④ 门控 EXIT：`build-mc`=0、`check-patch-tree`=0、`check-lit`=0（**87/87 Passed**）、`check`=0。
⑤ 反例自检：把 `writeNopData` 改回旧写法 ⇒ 复现断言 abort **rc=134**（`MCAssembler.cpp:588`）⇒ `cp`+md5 还原（`1941a5…`）⇒ **重建** ⇒ rc=0 回绿。
**修改文件**：`components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`（修复）；`components/llvm-project/changelog.md`；`tests/e2e/lit/lit.cfg.py`（+`%ld`/`%crt0`/`%linker_script`）；新增 `tests/e2e/p2align_e2e.s`、`tests/e2e/lit/p2align_e2e.test`、`tests/llvm/lit/MC/DADAO/p2align-{text,degrees,rodata}.s`。源树 `.work/source/llvm-project` 同步改并经 `make_patch.py` 重导出补丁（组件本地 amend 保持 E1=base+1，未推上游）。证据脚本 `.work/evidence/LLVM-075t/run.sh`。
**验收结果**：见上「测试结果」；`series` 仍 71（一文件一补丁，仅 DADAOAsmBackend.cpp.patch 变更）；`spec/`/`contracts/` 交集为空（grep 无输出）；`check-no-residue` PASS。
**新发现/坑**：① 根因 = `MCAssembler::writeFragment` 的 FT_Align 分支以**字节** `Count=(FragmentSize-FixedSize)/FillLen`（FillLen=1）调 `writeNopData`；`.text` 经 `MCAsmInfoELF::useCodeAlign`=true 走 nops 路径，`.rodata` 走 value-fill、**不经** writeNopData ⇒ 仅可执行段崩。② DADAO 定长 4B 且无子字指令 ⇒ 非 4 倍数填充只能以 0 字节补足（binutils/RISC-V 约定）；**不可**用 `getMinimumNopSize()=4`（`relaxAlign` 的 `Size += Alignment`，Alignment 为 2 的幂 ⇒ `Size%4` 永不变 ⇒ 死循环）。③ `.align N` 实测 = **N 字节**（非 GAS 2^N），与 `.p2align` 共用修复路径已一并覆盖；去留归 `LLVM-078t`。
④ 缺口原话（`ISS-182`）：「`.text` 内 `.p2align N`（N≥1）或 `.align N`（N≥2）⇒ `llvm-mc` abort：`MCAssembler.cpp:588` 断言 `The stream should advance by fragment size`（rc=134/141）；`.rodata` 内同指令正常（rc=0）」。
**遗留问题**：无（`.align` 去留不属本任务，见上）。

> **更正（arch 收尾）**：本区「**修改文件**」列 8 项，**实为 9 项（含本任务书）**。

## 审阅记录

#### 第 1 轮 engineer 自审
逐行审查 `writeNopData`（源树 + 补丁）、`lit.cfg.py` 增项与 5 个新测试。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 修复后「前导 0 字节填充」是否合法（DADAO 全零字=UNDI） | ❌不修 | 源码注释已阐明 | DADAO 无子字指令，非 4 倍数字节无法由整条 NOP 组成；沿用 binutils/RISC-V 字节填充约定；良构代码的 `.text` 偏移恒 4 对齐 ⇒ 填充恒为整字 `swym 0`（落穿执行的是合法 NOP），0 字节仅在 `.byte` 夹缝出现（E2E 落穿 3 条 swym exit=0 佐证） |
| F2 正常路径（Count 为 4 倍数）是否回归 | ✅已修（确认无回归） | — | 新老实现对 4 倍数 Count 均写 Count/4 条 `swym 0`，逐字节相同；`.text` 起始 `.p2align 3` size=0 不变 |
| F3 `while (Count % 4)` 是否可能不终止 | ✅已修（确认终止） | — | 每轮 `--Count`，最多 3 轮；`for (; Count != 0; Count -= 4)` 在 Count 为 4 倍数时终止；Count=0 ⇒ 0 字节（同旧行为） |
| F4 `.align N` 是否与 `.p2align` 共用修复路径且已覆盖 | ✅已修 | 新增 degrees/text 测试含 `.p2align`；`.align` 实测记录 | `.align 2/4/8` rc=0、段尺寸 3/5/9（=N 字节语义，非 2^N）；去留归 `LLVM-078t` |
| F5 证据脚本注入自检是否为「真失败」而非解析错 | ✅已修 | `asm()` 由 `printf '%s'` 改 `printf '%b'`（首轮误报 rc=1） | 注入后实测 rc=**134**（真断言 abort），非 rc=1 |
| F6 `lit.cfg.py` 新增 `%ld` 与 `%lds` 前缀冲突 | ✅已修 | `%lds`→`%linker_script` | 首轮 `%ld.llds` 报错；改名后 e2e 测试 PASS |
| F7 计数口径 | ✅已修 | 不硬编码；门控现场统计 | `check-lit` 现场 `Total Discovered 87 / Passed 87`；本任务新增 4 用例（3 MC + 1 E2E） |
| F8 越界/范围 | ✅已修 | 只动 `components/llvm-project/**`+`tests/**`+本任务书 | `git status --porcelain -uall`：仅 8 项（3 改 + 5 新），无 `spec/`/`contracts/`/`.opencode/` |

判决：所有 finding 已处置，无未修项 ⇒ 状态置「待验收」，返回主会话。


#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）

**环境**：分支 `LLVM-075t`；临时树 `/tmp/opencode/LLVM-075t-review/`；只审不改（唯一写操作=源树注入-还原-重建，`cp`+md5 对账）。
**1 独立复现+尺寸自算**：`.text .byte 1 + .p2align N + .byte 2`（N=1..4）逐档 rc=0/0/0/0，`llvm-objdump -h` 实测 0x3/0x5/0x9/0x11；自算 pad=2^N−1、`.byte 2`@2^N ⇒ size=2^N+1=3/5/9/17，逐档相符。
**2 填充合法性**：`llvm-objdump -s` 字节 `01 00 02` / `01 00 00 00 02` / `01 00 00 00 77 88 00 00 02` / `01 00 00 00 (77 88 00 00)×3 02` ⇒ 0x00 补齐至 4B 边界 + 整字 `swym 0`=0x77880000；对照 `contract-isa.md §13.1`（`swym 0` 编码 **0x77880000**、除 PC 自增外无副作用=nop）/`§13.3`（`nop`=`swym 0`，占位或对齐）✓。边界：Count=0（段起始）size=1 无填充；Count=12（4 倍数）=3 条 swym、size=0x11；Count=1/3 ⇒ 1/3 个 0 字节；均 rc=0 无异常。
**3 `.rodata` 不回归**：rc=0、size=0x9、字节 `01 00 00 00 00 00 00 00 02`（纯 0 value-fill、无 swym），与改前口径逐字节一致 ✓。
**4 E2E 独立**：自写 `main: swym 0; .p2align 4; set.zw rd8,wp0,7; ret`（3 条对齐填充 swym 落在执行路径内，`llvm-objdump -d` 0x34–0x3c 全 `swym 0`）⇒ `llvm-mc`=0、`ld.lld -T tests/scripts/dadao.lds`=0、`qemu -M dadao-m1 -kernel …` **rc=7**=手算期望（crt0 SYS_EXIT 取 rd8 低字节）⇒ 填充可执行、退出码传递正确；复跑 engineer 的 `p2align_e2e.s` rc=0（反汇编确认落穿 3 条 `swym 0`）✓。
**5 不回归+门控**：`make build-mc` rc=0（ninja: no work to do）；`make check` rc=0（repository checks: PASS）；`make check-lit` rc=0（Total Discovered 87 / Passed 87 100%，Failed/Unsupported 0：新 4 例 + 既有 83 例全 PASS）；`make check-patch-tree` rc=0（3 component(s), 109 patches OK）。`lit.cfg.py` 经 `git diff` 为**纯新增**（无删除行），`grep -rn '%ld|%crt0|%linker_script' tests/` 既有用例 rc=1（无既有用法）⇒ 既有 5 例 DADAO-E2E（smoke_add/smoke_jump/smoke_fp/clang_dadao_target/smoke_arith）全 PASS，不受影响 ✓。
**6 证据脚本**：审 `run.sh`（160 行）——6 项均有可达 FAIL 路径（bad() + FAIL>0 ⇒ exit 1）、计数现场累计不写死、无 `tee`、rc 用 `rc=$?` 自捕、注入非空且 `git diff` 非空校验、还原 `cp`+md5 **含重建** ✓。**重跑**：`PASS=11 FAIL=0 RUN_EXIT=0`；6a 复现断言 `MCAssembler.cpp:588 The stream should advance by fragment size` abort **rc=134**；6b md5 `1941a5a1…`；6c 回绿。
**我的独立注入**（与旧写法不同：改 `swym` 编码 0x77880000→0x77880001）：`cp` 备份 md5 `1941a5…`→注入后 `0551112c…`、源树 `git diff --name-only` 非空 ⇒ 重跑**同一脚本** ⇒ **FAIL=4 / RUN_EXIT=1**（2-p2align3/4、3-exact 实测 `…77880001…`≠期望、6a ineffective）⇒ `cp` 还原、md5 回 `1941a5…`（=备份）⇒ **重建**（ninja rc=0，3 edges）⇒ 再跑同一脚本 **PASS=11 FAIL=0 RUN_EXIT=0** 回绿 ✓。
**7 补丁纪律**：`series`=71；`DADAOAsmBackend.cpp.patch` 内 `diff --git`=1（一文件一补丁）、new file 334 行非空 blob、补丁正文与源树文件 `diff` 逐行一致 rc=0；源树 `git status --porcelain -uall` 空；`git diff --name-only | grep -E '^(spec|contracts)/'` 无输出（rc=1）、`| grep 'llvm/lib/MC/'` 无输出（rc=1）；主仓 `git status --porcelain -uall` 仅本任务 9 项（任务书/changelog.md/DADAOAsmBackend.cpp.patch/lit.cfg.py + 新 5 测试），无 `_tmp/_orig/_rej`。
**约束核验**：临时目录 `/tmp/opencode/LLVM-075t-review/` ✓；未提交 git ✓；未切分支 ✓；禁 `git checkout/restore/stash`/`git show>`——全程 `cp`+md5、以 md5 相等判还原 ✓；无 `tee`/`cmd|tail` ✓；长构建 `setsid` 脱离+完成标记 ✓；收尾快照与注入前快照逐行对账 rc=0、3 目标文件 md5 `OK` ✓。`.align N` 实测= N 字节语义（2/4/8 ⇒ 3/5/9），已如实披露、去留归 `LLVM-078t`（验收 3）✓。
**已知非阻断**：① 非 4 倍数填充的前导 0 字节非合法指令字（`contract-isa §13.5` 全零→UNDI），仅现于 `.byte` 数据夹缝；良构代码 `.text` 偏移恒 4 对齐 ⇒ 填充恒整字 `swym 0`（E2E 落穿 3 条 swym、rc=7 佐证），沿用 binutils/RISC-V 字节填充约定，engineer F1 已披露；② `run.sh` 的 `ir=1; [ -s $SRCFILE ] && ir=0` 实为「文件非空」而非 python 退出码（echo 文案误导），但 6a FAIL 路径仍可达，非阻断；③ 完成区 F8 称「8 项」实为 9 项（含任务书），记账口径差异，非阻断。

**判决：Accepted** —— 验收 1–8 在独立重跑下全部通过、硬约束无违反；改动 target-scoped（仅 `MCTargetDesc/DADAOAsmBackend.cpp`），`spec/`/`contracts/` 交集空、未动 `llvm/lib/MC/**`。
