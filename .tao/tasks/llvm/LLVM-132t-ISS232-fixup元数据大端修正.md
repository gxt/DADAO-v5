# LLVM-132t: ISS-232 fixup 元数据大端修正（--show-encoding）

**模块**：llvm
**项目里程碑**：M10
**依赖**：无（用户 2026-10-25 裁定方案 a）
**状态**：已验证

## 执行环境
**执行环境**：本地（LLVM 重建由主会话执行）

## 接口规范

### 背景（ISS-232，实测 2026-10-25）
- `llvm-mc --show-encoding` 对 `ld.o rb4, [rb4, %pcrel_lo(.Lhi0)]` **rc=134**（上游断言 `Encoder wrote into fixed up bit!`）；`rb1/2/3` rc=0，`rb4/8/16/32/63` 全 rc=134。
- 根因：`DADAOAsmBackend::getFixupKindInfo` 的 `TargetOffset=0, TargetSize=12` 按**小端位序**描述；DADAO 是**大端**，`--show-encoding` 实际标记到最高 12 位（`opcode + ra[5:2]`），`ra≥4` 时标记位非零 ⇒ 断言。
- 影响面：仅 `--show-encoding` 显示；`-filetype=obj`、链接、运行均正常。

### 输出
- `getFixupKindInfo` 的 `TargetOffset` 改为**大端字节流**位置：12 位 → **20**、18 位 → **14**、24 位 → **8**、32 位（整字）→ **0**；`TargetSize` 不变。
- **不改**：`applyFixup`（自定义位写入，不读 `TargetOffset`）、编码/链接行为、`spec/`、契约正文。
- 补一条 `--show-encoding`（`rb≥4`）用例（lit 或脚本），防回归。

### 约束
- 若发现门控/文档钉住该表（issue 提到 `check_mc` A7，现场未找到），**停下报告**，不擅自改契约。
- 共享文件（`MCAsmStreamer.cpp` 等）**不碰**（方案 a 只改目标侧）。

## 验收标准
1. `llvm-mc --show-encoding` 对 `rb4/8/16/32/63` 均 rc=0；`rb1` 仍 rc=0。
2. `-filetype=obj` 产物与修复前**逐字节一致**（md5 对账）。
3. 反例注入（`20` 改回 `0`）⇒ 复现 SIGABRT（rc=134）⇒ `cp` 还原 ⇒ 绿。
4. `make install-host` 后 L1 / L2 绿。
5. 完成区贴真实输出与退出码。

## 完成区

**测试结果**：`run.sh --runtime` **16/16 rc=0**（静态 7 + 运行期 9：`syntax-only` rc=0 且日志 **0 字节**；`rb1/4/8/16/32/63` rc=0 且 A 标记精确、18 位高半、lit FileCheck、`-filetype=obj` md5 与修复前基线逐字节一致 `4b82a4edc45f0035f92797448c983e59`）；`run.sh --inject` **4/4 rc=0**；`run.sh --inject-syntax` **4/4 rc=0**（基线 rc=0/0 B → 注入语法错 rc=1/252 B → 还原 rc=0/0 B，TU md5 不变）。**返工说明**：① 首轮 rb16/rb32/rb63 三红 = **证据脚本解析笔误**（`spec` 行内 1 空格 vs `${spec%%  *}` 用 2 空格），已改 `read` + 守卫；② 第 2 次返工 = `syntax-only` **恒真**（`HERE` 相对路径，`cd` 后 `cat` 失败 ⇒ `eval ""` rc=0），已把 `HERE`/`LOGDIR` 改绝对 + `run_syntax_cmd` 对空命令文件显式返 2 + 断言日志 0 字节；修复前 `syntax.log` 实为 72 B 的 `cat` 报错。工具链行为已验证正确（build/install 同 md5 `98a33431…`）。
**修改文件**：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`：`PCREL_HI 0→14`、`PCREL_LO 0→20` + 大端说明注释；`TargetSize`/`Flags` 不变；index `efa72a2d5`、hunk `+1,386`。
- `tests/llvm/lit/MC/DADAO/show-encoding-fixup-bigendian.s`（新增回归锁）。
- `tests/llvm/lit/MC/DADAO/pcrel-specifier.s`（仅更新已失效注释）。
- `components/llvm-project/changelog.md`（Process-01 §10 的 M10 条目）。
- `.tao/knowledge/milestones.md`（流水行状态 `待开始→待验收`；`check-milestones-fresh` A1 要求）。
- `.work/evidence/LLVM-132t/{run.sh,check_table.py,baseline/*}`（证据，不入库；两次返工只改 `run.sh`：spec 解析 + `syntax-only` 绝对路径/0 字节断言/`--inject-syntax`）。
**验收结果**（真实输出）：
- `make apply-series` rc=0：`llvm-project 95 applied, 0 skipped`，源树 base+1 且 `git status` 空。
- `-fsyntax-only`（`compile_commands.json` 取真实命令）rc=0，日志 `.work/log/llvm/LLVM-132t-syntax.log` **0 字节**（`wc -c` = 0）。
- `make check-patch-tree` rc=0：`5 component(s), 200 patches OK`。
- `make check`（L1）rc=0：`repository checks (L1): PASS`。
- `bash .work/evidence/LLVM-132t/run.sh --runtime` rc=0：`RESULT: 16 passed, 0 failed`；`md5(llvm-mc)=md5(install-root)=98a334315530683bc275e965df7fdf7b`。
- `bash .work/evidence/LLVM-132t/run.sh --inject` rc=0：`RESULT: 4 passed, 0 failed`。
- `bash .work/evidence/LLVM-132t/run.sh --inject-syntax` rc=0：`RESULT: 4 passed, 0 failed`（基线 `gate=0 rc=0 bytes=0`；注入 `gate=1 rc=1 bytes=252`，`syntax-bad.cpp:1:27: error: expected primary-expression before ';'`；还原 `gate=0 rc=0 bytes=0`、TU md5 不变）。
**新发现/坑**：
① 任务书称「`check_mc` A7 现场未找到」——实际在 **`.work/evidence/LLVM-095t/check_mc.py` A7**（未入库的旧任务证据，非 Makefile 门控、非 `tools/`）：它以完整初始化器字面量钉 `{HI, 0, 18, 0}`/`{LO, 0, 12, 0}`，现报 `19 passed, 1 failed`（`width18=False width12=False`，日志 `/tmp/opencode/LLVM-132t/check_mc_095t.log`）。按「不擅自改他笔证据 / 不迁就实现改门控」**未改**，留裁定。
② `ABS48`（`TargetSize=16`、低 16 位）按同一大端规则应为 `TargetOffset=16`（上游 Sparc BE `fixup_sparc_13` 的 `19 = 32−13` 佐证），但任务只列举 12/18/24/32 ⇒ 本笔**未改**；它只影响 `set.zw/or.w/andn.w` 的 `--show-encoding` 标记（整字节标记，不会断言）。
③ 期望 A 标记 =「实际编码字节 + 契约字段位置」独立推导：Python 复刻 streamer 位图对修复前 rb1 输出逐字符一致、对 rb4 精确复现 `Bit == 0` 断言，并以 `MCAsmStreamer.cpp:82-134` 与上游 Sparc 大端表佐证；`--runtime` 实测 6×rb + 高半与推导逐字符一致。
④ **证据脚本解析类断言必须对输入形态设守卫**：`${spec%%  *}` 依赖字面两空格，表格行 1 空格即静默拼出畸形汇编并报「invalid operand」（假红）。已改 `read` 拆词 + `^[0-9]+$`/非空守卫；同类脚本建议照此。
⑤ **相对路径 + `eval "$(cat …)"` = 恒真**：`syntax-only` 曾用相对 `HERE`，在 `cd .work/build/llvm` 后 `cat` 失败、`eval ""` 返回 0、日志只留 72 B `cat` 报错 ⇒ 检查「绿」但 `-fsyntax-only` 从未执行。修复 = `HERE`/`LOGDIR` 绝对化 + `run_syntax_cmd` 对缺失/空命令文件显式 `return 2` + 同时断言日志 **0 字节**；`--inject-syntax` 实测 `rc=1/252 B` → 还原 `rc=0/0 B`。教训：`eval "$(cmd)"` 类断言必须校验命令文件可读且非空，并把「无诊断输出」本身纳入断言。
**遗留问题**：
- 验收标准 3 的**运行时**注入（`20→0` + 重建 ⇒ rc=134）仍未做（重建归主会话）；等价证据 = 修复前同代二进制实测 `rb4/8/16/32/63` rc=134（`LLVM-132t-prefix-repro.log`）+ 本笔静态注入（table check 双红 → 还原绿）。
- `.work/evidence/LLVM-095t/check_mc.py` A7 陈旧（见 ①），待架构师裁定：更新为 `14/20` 或改为只断言字段宽。
- `ABS48` 的 `--show-encoding` 标记仍指高 16 位（见 ②），建议另立小任务改 `0→16`。

## 审阅记录

#### 第 1 轮 engineer 自审

**方式**：自主逐行审查（`subagent_depth=1`，无嵌套）；对照 `MCAsmStreamer.cpp:82-134`（FixupMap MSB-first）、`SparcAsmBackend.cpp:180-205`（大端 `fixup_sparc_13` offset 19 = 32−13）、`contract-elf.md §2.2` 字段宽逐条核对。

**逐行结论**：
- 表项：`PCRel_12/18/24/REL12/ABS12` `TargetSize=32`（整字）⇒ offset 0 保持；`PCREL_HI 14/18`、`PCREL_LO 20/12`；`TargetSize/Flags` 未动。非 `lib/Target` 的 `getFixupKindInfo` 调用点仅 `MCAsmStreamer`（显示）与 z/OS `GOFFObjectWriter`（本 target 不走）⇒ 对象字节不受影响；`applyFixup` 按 LSB 位号写 word，不读 `TargetOffset`。
- lit：期望串由编码字节 + imms12/imms18 字段位置推导；Python 复刻位图与修复前 rb1 实际输出逐字符一致、rb4 精确复现断言；FileCheck 对合成输出 rc=0；整文件 `-filetype=obj` rc=0。
- 证据脚本：注入仅改 patch、`cp` 备份 + md5 对账（不动源码/构建树）；静态 7 项、注入 4 项均真实非零可达 FAIL。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 任务列举未含 `ABS48`（16 位），表内仍 `0` | ⏸延后 | 未改（严格按范围） | 新发现②；`check_table.py` 显式 NOTE |
| F2 `.work/evidence/LLVM-095t/check_mc.py` A7 钉旧字面量 | ⏸延后 | 未改（非当前门控；不擅自改他笔证据） | 现场 `19/1`，`/tmp/opencode/LLVM-132t/check_mc_095t.log` |
| F3 `pcrel-specifier.s` 注释称低半只能走 obj | ✅已修 | 注释改为指向新 lit + 说明偏移修正 | 该文件 RUN 未动；L1 绿 |
| F4 `run.sh` 原 `case ... [$want]` 会按 glob 字符类误配 | ✅已修 | 改 `grep -Fq` | `bash -n` rc=0；静态 run rc=0 |
| F5 `PIPESTATUS` 被后续赋值重置 | ✅已修 | 先存 `ps=("${PIPESTATUS[@]}")` | 本轮 `--runtime` 16/0（`lit-filecheck` PASS） |

#### 第 2 轮 engineer 自审（返工：仅证据脚本）

**触发**：主会话复跑 `run.sh --runtime` 报 rb16/rb32/rb63 三红；根因 = `spec` 行内分隔 **1 空格**、拆分却用 **2 空格**（`${spec%%  *}`）⇒ 拼出 `ld.o rb16 0x22,…` ⇒ `invalid operand`。纯脚本解析笔误，工具链行为经主会话手跑与本次 6×rb 实测均正确（build/install 同 md5 `98a33431…`）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 spec 解析依赖字面两空格，输入一空格即假红 | ✅已修 | `read -r rb want <<< "$spec"`（按 IFS 空白拆）+ `^[0-9]+$`/非空守卫（畸形 spec 直接 FAIL，不拼畸形汇编） | `bash -n` rc=0；`--runtime` **16/0 rc=0**；`--inject` **4/0 rc=0** |

**返工范围**：仅 `.work/evidence/LLVM-132t/run.sh`（+本册完成区/changelog 记述）；补丁/测试/代码零改动（patch md5 `fc78476f…` 不变）。

#### 第 3 轮 engineer 自审（第 2 次返工：syntax-only 恒真）

**触发**：reviewer 实测 `syntax-only` 恒真 —— `HERE` 为相对路径，`( cd .work/build/llvm && eval "$(cat "$HERE/syntax-cmd.txt")" )` 中 `cat` 失败、`eval ""` rc=0；旧 `syntax.log` 实为 **72 B** 的 `cat` 报错（不是「空」）。这是「检查从未执行却报绿」的假绿，属阻断级。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R2 `syntax-only` 因相对 `HERE` 恒真，且未断言日志为空 | ✅已修 | `HERE="$ROOT/.work/evidence/LLVM-132t"`、`LOGDIR` 绝对化；抽 `gen_syntax_cmd`/`run_syntax_cmd`（命令文件缺失/空 ⇒ `return 2`；先 `cat` 再 `eval`；生成失败亦 FAIL）；`syntax-only` 判据 = **rc=0 且日志 0 字节**；新增 `--inject-syntax` 自检 | `--inject-syntax` 4/0：基线 `gate=0 rc=0 bytes=0` → 注入 `gate=1 rc=1 bytes=252`（`expected primary-expression`）→ 还原 `gate=0 rc=0 bytes=0`、TU md5 不变；`--runtime` 16/0（`syntax-only rc=0 bytes=0`）；`--inject` 4/0；`wc -c syntax.log` = **0** |

**返工范围**：仍仅 `.work/evidence/LLVM-132t/run.sh` + 本册/日志记述；补丁/测试/代码零改动（patch md5 `fc78476f…`、lit md5 `9fd79d50…`/`6f411422…` 不变）。

#### 第 1 轮 reviewer 验收

**判决：Needs Revision**（唯一阻断：证据脚本 `syntax-only` 恒真假绿；交付物本身全部达标）

**重跑记录**（reviewer 独立执行，日志 `.work/log/llvm/LLVM-132t-reviewer-*.log`）：
- `run.sh --runtime` rc=0：`RESULT: 16 passed, 0 failed`（静态 7 + 运行期 9），`md5(llvm-mc)=md5(install-root)=98a33431…`。
- `run.sh --inject` rc=0：`4 passed, 0 failed`（LO `20→0` ⇒ table rc=1 ⇒ cp+md5 `fc78476f…` 还原 ⇒ 绿）。
- `make check` rc=0（`repository checks (L1): PASS`）；`make check-modules` rc=0（`module checks (L2): PASS`）。
- 手工 `--show-encoding`：rb1/4/8/16/32/63 **全 rc=0**（编码 `[0x22,0x04|0x10|0x20|0x41|0x82|0xff,…]`）；`-filetype=obj` 与基线 `cmp` rc=0、md5 `4b82a4ed…` 逐字节一致。
- **独立反例**（cp+md5，禁 git checkout）：patch `PCREL_LO 20→0` ⇒ 重跑 `--runtime` **rc=1，4 FAIL**（patch-table / apply-series「refusing to apply」/ check-patch-tree ⑥⑨ / L1——门控额外钉住该表）；还原 md5 回 `fc78476f…` ⇒ 回绿 16/0；源树全程零污染（status 空、HEAD `29919c5bc` 不变）。
- 核对项：补丁净 diff 仅 `getFixupKindInfo`（两数字 +5 行注释，`applyFixup`/`evaluateFixup` 零改动）；lit 断言非常量（改一期望字节 ⇒ FileCheck rc=1，可达 FAIL 实证）；首轮 3 红确为解析笔误（`${spec%%  *}` 对 1 空格行拆出整串 ⇒ 畸形汇编 ⇒ `invalid operand` rc=1，非工具问题）。

**阻断项（B1，证据脚本缺陷）**：`run.sh` L115 `( cd .work/build/llvm && eval "$(cat "$HERE/syntax-cmd.txt")" )` 中 `$HERE` 为相对路径，`cd` 后失效 ⇒ cat 失败 ⇒ `eval` 空串 ⇒ **rc=0 恒真**，`-fsyntax-only` 从未执行（FAIL 路径不可达，违反「每条断言须有可达 FAIL」）。实测：`.work/log/llvm/LLVM-132t-syntax.log` 内容为 `cat: …syntax-cmd.txt: No such file or directory`（72 字节，**非**完成区声称的「为空」），手工复现 rc=0 同错误。**修法**：L29 `HERE="$ROOT/.work/evidence/LLVM-132t"` 绝对化；修后重跑 `--runtime` 应 16/0 且 syntax log 真为空，并自证可达 FAIL（临时改坏源树 .cpp ⇒ 该检查应红，cp+md5 还原）；同步修正完成区该句陈述。

**约束核验**：共享文件未碰 ✓；`check_mc A7`（`.work/evidence/LLVM-095t/`）发现即停下留裁定、未擅改 ✓；完成区「修改文件」与两个 WIP commit 清单一致、未触碰 `docs/DDLN`/`spec/`/`contracts/` ✓；快照 pre/post 对账一致 ✓。其余验收标准（1/2/4/5）全达标，B1 修复并重跑 `--runtime` 后即可 Accepted。

#### 第 2 轮 reviewer 验收

**判决：Accepted**（B1 修复经 reviewer 独立复跑 + 独立反例证实封死；交付物与上轮一致未动）

**重跑记录**（reviewer 独立执行，日志 `.work/log/llvm/LLVM-132t-reviewer-r2-*.log`）：
- `run.sh --runtime` rc=0：`16 passed, 0 failed`；`syntax-only` 显示 `rc=0 bytes=0`，`LLVM-132t-syntax.log` 实测 **0 字节**。
- `run.sh --inject` rc=0：`4 passed, 0 failed`。
- `run.sh --inject-syntax` rc=0：`4 passed, 0 failed`（坏 TU ⇒ clang `error: expected primary-expression` ⇒ gate=1 rc=1 **bytes=252**；还原 gate=0、真 TU md5 `71adafbc…` 前后一致）。
- **独立 FAIL 抽查**（不经内置模式）：`cp`+md5 备份真 TU、末尾注入 `int reviewer_inject_syntax = ;` ⇒ 重跑 `--runtime` **rc=1**，`syntax-only` **FAIL `rc=1 bytes=320`**（clang 诊断指向注入行 388）；`cp` 还原 md5 回 `71adafbc…`、源树 status 空 ⇒ 重跑回绿 `16/0 rc=0`、syntax log 回 0 字节。恒真判定为**误报已封死**：空/缺命令文件 ⇒ `return 2` ⇒ FAIL；判据 = rc=0 **且** 0 字节。
- `syntax-cmd.txt` 首部 = `/usr/bin/c++ -fsyntax-only -D_DEBUG …`（`compile_commands.json` 真实命令去 `-o`、index 1 插入 `-fsyntax-only`，源文件 = 真实 TU 绝对路径）✓。
- 沿用项（md5 未变，本轮先核对）：补丁 `fc78476f…`（HI 14/18、LO 20/12、整字 0、`applyFixup` 未动）、lit `9fd79d50…`（非常量、可达 FAIL）、`check_table.py` `836e1515…`；L1 本轮 run.sh 内 PASS，L2 上轮 rc=0 沿用。

**约束核验**：`run.sh` 修复外零改动（`cec728c0` 仅任务书 + `.work` 不入库）；共享文件/`spec/`/`contracts/`/`docs/DDLN` 未碰；反例全程 `cp`+md5、未用 git checkout；pre/post 快照对账一致（主树与源树均干净，源树 HEAD `29919c5bc` 不变）。**Accepted**。
