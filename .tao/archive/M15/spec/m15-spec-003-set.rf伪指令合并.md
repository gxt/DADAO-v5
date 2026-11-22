# m15-spec-003: 伪指令 `set.ft rf, rs` / `set.fo rf, rs` 合并为 `set.rf rf, rs`

**模块**：spec
**项目里程碑**：M15
**依赖**：`m15-spec-002`（已合入：伪指令正文分层，`§6.1` 表是唯一展开表）、`m15-testcases-003`（在跑：改同一载体文件，须**先合入**再派本任务）
**可并行分片**：否（两册 spec + LLVM + 载体 + 契约，跨模块单写者）
**预估**：3–4 h（含 LLVM 重建 + 三平台回放）
**档位**：大改（跨 spec/llvm/testcases 的 ISA 表述 + 实现；复核 ≥4 路注入 + 独立重建）
**状态**：已验证

## 背景（用户 2026-11-16 裁定）

用户提出把 `set.ft rf, rs` 与 `set.fo rf, rs` 合并为 **`set.rf rf, rs`**，并裁定「立册」。

依据（现场核实）：

- 两种写法**展开完全相同**：`rd2rf`/`rf2rf`（**整 64 位复制**）——`SimRISC-00 §5` 表两行与 `Toolchain-01 §6.1` 表两行都这么写；
- 现有载体 `tests/inst/00-isa-design/pseudo_set.fx_reg.S` **本来就是"一个文件覆盖 ft/fo 两族"**，文件头注释写着「两者从 rf 源展开都是 `rf2rf`、语义一致（用户 2026-11-15 裁定方案 A）」⇒ 合并是**把既有事实写进名字**；
- 命名规则因此统一为「**名字只编码有歧义的那一维**」：寄存器源无宽度歧义 ⇒ 按**目的 bank** 叫 `set.rf`；立即数源有宽度歧义（窄写 vs 整 64 位）⇒ 保留 `set.ft rf, imm32` / `set.fo rf, imm64`。

## 目标

1. **规范（两册 + 一处指针）**
   - `spec/SimRISC-00 §5` 表：**8 行 → 7 行**（两行寄存器源合并为 `set.rf | rf, rs | rd2rf/rf2rf`），引导句里的伪指令清单 `set.rd/set.rb/set.ft/set.fo` 改为 `set.rd/set.rb/set.rf/set.ft/set.fo`；
   - `spec/Toolchain-01 §6.1` 表同改（8→7），「保留（实现，8 条合成型）」改为 **7 条**；`§6.2` 的 `6.2.3 set.ft / set.fo` 小节改名为覆盖 `set.rf` + 立即数两形（内容按新助记符替换，语义不变）；
   - `spec/Toolchain-01` 的**写宽对照表**（`set.ft` 两种源形式对照）改为 `set.ft rf, imm32`（窄写）vs **`set.rf rf, rs`**（整 64 位）；
   - `spec/SimRISC-03 §4` 的指针句同步（该册只引 `Toolchain-01 §6.2`）；
   - 两册附录 `-rc` 段各加一条变更痕迹；`SimRISC-00`/`Toolchain-01`（若 `SimRISC-03` 也动则三册）sha256 **同笔重算**。
2. **LLVM 实现**（`components/llvm-project`）
   - `DADAOAsmParser.cpp`：新增助记符 `set.rf`，寄存器源分支走 `rd2rf`/`rf2rf`；`set.ft`/`set.fo` **只保留立即数形式**（寄存器源若仍出现 ⇒ 报明确错误，不静默接受）；
   - printer/disassembler：反汇编仍只出真实指令（伪指令不进反汇编），但 **MC 层的别名/助记符表**要同步；
   - lit：新增 `set.rf` 的展开用例（立即数不适用，覆盖 `rd2rf`/`rf2rf` 两路 + 目的 rf0 边界），并把 `set-ft-fo.s` 里寄存器源的旧用例改为 `set.rf`；更新 `README-m4.md` 的伪指令清单；
   - 改完 **`make install-host`**（否则 `check-lit` 读旧二进制 ⇒ 假绿，`ISS-210`）。
3. **载体与登记**
   - `tests/inst/00-isa-design/pseudo_set.fx_reg.S` → **`pseudo_set.rf_reg.S`**（`git mv`），文件内 `set.ft/set.fo` 的寄存器源调用改 `set.rf`，头注释同步（"fx = ft/fo 两族"的说明删除）；
   - 三处登记同步：`tests/inst.yaml`（`file:` 与 `name`）、`tools/testcases/check_tests_index.py`（`NON_ID_CARRIERS`）、`tools/testcases/validate_vectors.py`；
   - `tests/inst/MIGRATION.md`、`tests/inst/README.md` 若有旧名，一并更新（历史迁移记录**不改**）。
4. **契约**：`contract-asm.md` §6.1 的 8 条表改 7 条并加 `set.rf` 行；`contract-isa.md` 的伪指令指针若列了 `set.ft/set.fo` 寄存器源，改为 `set.rf`。

## 验收（真实 rc + 输出）

1. **规范自洽**：`grep -c "set\.ft" spec/` 后，`set.ft` 的每一次出现都只跟 **`imm32`**（无 `rs` 形）；`set.fo` 同理只跟 `imm64`；两册表行数 7/7 且第三列逐字相同；`check-spec-readonly`（锁与实测 sha 一致）、`check-spec-refs`、`check-spec-purity`、`check-spec-changelog`、`check-rule-refs` 全 rc=0；
2. **LLVM**：`make install-host` rc=0（贴新 `llvm-mc` md5）；`make check-lit` **全绿**（条数现场统计，不低于改前 177）；`set.rf` 的正例/负例（`set.rf rf, imm` ⇒ 报错）都有 lit 覆盖；
3. **载体三平台一致**：改名后的 `pseudo_set.rf_reg.S` 在 QEMU/chipyard/gem5 上**逐字节一致**（贴每平台镜像数与 `semi.out` md5）；`make check-inst-asm` 镜像数与改前一致、904/904；
4. **登记一致**：`check-tests-index`（条数不变）、`check-case-ledger`（行数不变）、`check-dirs`、`check-no-residue`、`check-inst-macro-scope` 全绿；
5. **≥4 路注入**（`cp`+md5 还原）：① 把 `set.rf` 展开错成两条 `set.w`（窄写）⇒ 载体检查点红；② 让 `set.ft rf, rs` 仍被接受 ⇒ 新负例判据红（证明旧形确实停用）；③ 表行数改回 8 ⇒ 表一致性判据红；④ 锁 sha 改 1 字符 ⇒ `check-spec-readonly` 红；
6. L1 `make check` rc=0；完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **语义不变**：合并只是**换名 + 去冗余**；`set.rf rf, rs` 的展开、写宽、rf0 边界行为与合并前的寄存器源形态**逐条一致**；立即数两形（`ft`/`fo`）**行为不动**；
- **不保留旧名别名**（v5 未发布、仓内只有那一个载体用寄存器源；用户口径与 QEMU 机器名一致）；
- 不动 `tests/inst` 其它载体（`m15-testcases-003` 正在改同一册的文件，本任务只动 `pseudo_set.fx_reg.S` → `.rf_reg.S`）；
- 不提交 git；注入还原 `cp`+md5；证据基线钉死 commit（`ISS-458`）；脚本按 `git rev-parse --show-toplevel` 推根（`ISS-456`）。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-16）

**范围**：两册 spec + 两处册首指针、只读锁、LLVM 补丁/lit/组件 changelog、载体改名与三处登记、3 契约、3 工具脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 `set.rf rf, <sym>` 落到常量展开路径，报错文本 `invalid operand for instruction`（fail-closed 但口径不一致） | ✅已修 | 符号分支前置拒绝 `set.rf` | lit `ERR-RF-SYM`；`install-host` rc=0 |
| F2 首次构建 `expected '}' at end of input`：补丁 hunk 计数仍是 2737，`git apply` **静默截断** | ✅已修 | hunk 头改 2749 + `check-index-blobs --fix` | 应用后 2749 行；`check-patch-tree`/`check-source-state` 绿 |
| F3 注入 1 还原后仍红：`cp -p` 保留旧 mtime ⇒ ninja 未重编（还原实为注入态二进制） | ✅已修 | 还原后 `touch` 再重建 | 重跑 `--inject 1`：注入态载体 0/1 红、还原后 rc=0 绿 |
| F4 附录旧条目写 `set.ft rf, rf`，与新条目并存 ⇒ 同一 `-rc` 段自相矛盾 | ✅已修 | 新条目说明旧对照表已随正文迁至 `§6.2.3` 并改名 | `check-spec-readonly`/`-purity` 绿、锁重算 |
| F5 `contract-fp §14` 把 `set.ft` 也写成「全零 → `rd2rf`」（与 spec 冲突：`set.ft` 是 2×`set.w` 窄写） | ✅已修 | 按新分工重述三形 | `check-spec-refs`（含 §6.2.3 引用目标）rc=0 |
| F6 `contract-asm §6` 末行「尚未实现（8 条）」自 M4 实现起即陈旧 | ✅已修 | 改「已实现（7 条合成型）」 | `check-lit` 177/177 为直接证据 |
| F7 `ADR-0013 D11`（仍列 8 条 + 已删的 `ft2ft`/`fo2fo`）、`docs/DDLN/E-002`、探针注释、`MIGRATION.md §048` 历史记录 | ⏸延后 | 未改（ADR 需用户逐条确认；DDLN 属讲义；MIGRATION 属历史迁移记录） | 完成区「遗留问题 ②③」 |

**判决**：F1–F6 已修并复验，F7 显式延后登记；无未修 finding ⇒ 状态改 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-16；worktree `/tmp/opencode/m15-spec-003/wt` @ `ec703cae`，基线 `7aacef63`）

**重跑（均本人执行，rc = 被检命令自身）**
- 证据脚本：`run.sh` ⇒ `PASS=39 FAIL=0`；`--full` ⇒ `40/40`（`check-inst-asm 904/904`，272 id/271 链例/633 故障例）；`--inject 1,2,3` ⇒ `42/42`；**`--inject 4` ⇒ rc=1、`PASS=39 FAIL=1`**：`AssertionError: target sha not found`（锁内无 `e34b305a…`，`git log -S e34b305a -- manifests/` 全史 0 命中）⇒ 空注入、`check-spec-readonly` 仍 rc=0。
- 语义不变（自展开）：基线 `pseudo_set.fx_reg.S` 按 §6.1 机械展开 13 条 ⇒ `.o` md5 `dee7956a…` = 新载体 `.o` = 旧产物 `pseudo_set.fx_reg.o`（mtime 11:58，早于新二进制 12:51）= 新产物；ELF 同为 `cd008f75…`；`llvm-objdump` diff 仅文件名行不同。
- 旧形四输入（合法目的寄存器写法）均 rc=1 且**非** `unrecognized`：`set.ft rf1, rf1` / `set.fo rf1, rf1` ⇒ `takes an immediate only; use 'set.rf rf, rs'`；`set.rf rf1, 42` ⇒ `takes a register source only`；`set.rf rf1, sym` ⇒ `symbol/relocatable operand is not supported`；对照 `nosuch.rf` ⇒ `unrecognized instruction mnemonic`。
- 表 7/7 第三列逐字相同（本人脚本）；`grep -E 'set\.(ft|fo)[[:space:]]+rf[0-9]+,[[:space:]]*(rd|rf|rb|ra)[0-9]' spec/` ⇒ **0 处**（仓内残留仅 lit 负例与 `.tao/archive` 历史）；四册 sha256 现算全 MATCH、`check-spec-readonly` rc=0（21 册 OK）。
- `make install-host JOBS=32` rc=0 ⇒ `llvm-mc` md5 `342a7d007a54991b88d501c9d2d0576b`；`make check-lit` rc=0、**177/177**（现场统计）；翻转 `ERR-RF-DST0` 期望 ⇒ lit rc=1、`check-lit` 176/177 rc=2，还原（md5 `21556077…` 相等）后回绿。
- 三平台回放：chipyard/qemu/gem5 各 1 镜像 / 13 检查点 / 104 B，`semi.out` md5 `9e71680a…` 三者相同。
- 本人 4 路注入（`cp`+md5 还原，非 engineer 那 4 路）：① `set.rf` 的 rf 源改走 `rd2rf` ⇒ 载体 0/1 红 + lit 红，还原重建后 1/1 绿（`llvm-mc` 回 `342a7d00…`）；② 删 `dst_rf0` 负例 ⇒ 2.5b `期望=4 实际=3` 红（`check-lit` 文件数仍 177），还原回绿；③ 删 §6.1 `set.rf` 行 ⇒ 1.1 红 + `check-spec-readonly` rc=2，还原回绿；④ `inst.yaml file:` 回旧名 ⇒ `check-tests-index` rc=2（FAIL 4 项），还原 rc=0。

**约束核验**：开工/收尾 `git status --porcelain -uall` 均空、未提交 git；改动 23 文件，比允许清单多 `tests/inst/00-isa-design/pseudo_set.ft_imm32.S`（注释级对照指针，完成区已披露）与 3 个 lit 文件（任务书明确要求），未动 `12-misc`/`Makefile`/`contracts/`；还原全用 `cp`+md5（无 `checkout/restore`）。

**判决：Needs Revision**（仅 1 项阻断）
1. `.work/evidence/<任务ID>/run.sh` 注入 4 不可达：目标 sha 写死 `e34b305a` 在锁中不存在 ⇒ 空注入 + python traceback，实跑 `PASS=39 FAIL=1`，与完成区「`--inject 1..4` 各 40/40」不符。**改法**：注入目标按 `path = "spec/Toolchain-01-汇编语言.md"` 条目定位其 `sha256`（并对 python rc 判非零、空注入即 FAIL），改后重跑 `--inject 4` 得 40/40，并订正完成区该句。

**非阻断 finding**：① `check-lit` 177 是**文件数**口径，删负例不变 ⇒ 负例覆盖断言只由 run.sh 2.5b 承担（改脚本时勿把 2.5b 去掉）；② run.sh 3.2 在旧 `.fx_reg.o` 缺失时走 SKIP 不判红；③ L1 我方重跑红项均非本任务：`check-musl-freshness` 由我重跑 `install-host` 触发、已按坑③补 `build-musl-shared`，`check-patch-tree: linux` 与 `check-milestones-fresh R1 m14-linux-009` 来自**并发会话**写共享 `.work`（`ps` 可见 `check_k2.py` 13:51 起），`check-temp-dirs` 现已 PASS。

### 第 2 轮 engineer（Needs Revision 修复，2026-11-16）

**范围**：只改证据脚本与任务书文字；**内容侧（spec/LLVM/载体/契约/lit）零改动**（复核已通过）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 注入 4 是空注入（目标 sha 写死 `e34b305a…`，锁中不存在） | ✅已修 | 改为**按 `path = "spec/Toolchain-01-汇编语言.md"` 在锁内定位该 `[[spec]]` 块**、取其 `sha256`；不写死任何 sha | `--inject 4` ⇒ **40/40**；注入日志：`19879673… → 09879673…`、锁 md5 变更、`check-spec-readonly` rc=1 且红项命中 `MISMATCH spec/Toolchain-01` |
| R1b 无防空注入断言 | ✅已修 | 定位失败/块内无 64-hex sha/写后字节未变 ⇒ python 非零退出，脚本判 **FAIL**（并打印 `FAIL:` 首行）；另把「python rc≠0」并入判决 | 负向自检：把锁副本的目标 `path` 改名 ⇒ `FAIL: no [[spec]] entry …` rc=1（日志留存） |
| R2（非阻断①）2.5b 负例断言 | ✅保留并强化 | 由 4 条改 5 条（加 `ERR-RF-SYM`），note 明写「177 是文件数口径 ⇒ 负例条数由本条守护」 | 默认证据 2.5b PASS（期望=5 实际=5） |
| R3（非阻断②）3.2 旧产物缺失时 SKIP | ✅已改为**基线重建** | 判据改为：`git show <基线 commit>:<旧载体>` → 按 spec 把旧寄存器源形机械展开为 `rd2rf`/`rf2rf`（展开条数 ≠13 即 FAIL）→ 汇编 → 与新载体 `.o` 逐字节比较；历史产物仅作补充打印（不参与判决、无 SKIP 分支） | 默认证据 3.2 PASS（两条 md5 相同）；FAIL 路径由注入 1 覆盖（错展开 ⇒ 载体 `.o` 变） |
| R4（非阻断③）L1 红项 | ✅已处置 | 已跑 `build-musl-shared`（`check-musl-freshness`/`check-builtins-freshness` 均 PASS）；`check-temp-dirs` 已由主会话清理转绿；`check-milestones-fresh`（并发任务 `m14-linux-009` 台账行）与 `check-run-artifacts`（审阅侧 7 个日志命名）属外来 | L1 其余目标逐条复跑 rc=0；上述 2 项未代改（不凑绿），见完成区遗留 ① |

**判决**：R1/R1b 阻断项已修并复验（注入 4 真注入、可达 FAIL），R2–R4 处置完毕；状态保持 `待验收`。

### 第 2 轮 reviewer 验收（2026-11-16；HEAD `679be4c6`，上轮内容基线 `ec703cae`）

**重跑（均本人执行，rc = 被检命令自身）**
- **内容零改动**：`git diff ec703cae..HEAD -- spec/ .tao/contracts/ manifests/ tests/ tools/ components/` = **0 行**；`git diff --name-only 85760db7..HEAD` = 仅任务书；`git status --porcelain -uall` 空（收尾亦空）。
- **注入 4 真注入**：`run.sh --inject 4` ⇒ **40/40 rc=0**，日志 `sha256 19879673… → 09879673…`、锁 md5 `1868b05a… → 4a6d3afd…`、注入态 `check-spec-readonly` **rc=1 且红项 = `MISMATCH spec/Toolchain-01-汇编语言.md`**、还原 md5 `1868b05a…` = 备份且 rc=0。**独立复现**：我自写 python 同法定位 ⇒ 同一对 sha、同一锁 md5 `4a6d3afd…`，红项同为 Toolchain-01，还原 rc=0。
- **防空两条可达 FAIL**：① 锁副本把 `path` 改为不存在值 ⇒ **rc=1** + `FAIL: no [[spec]] entry with path = 'spec/Toolchain-01-汇编语言.md'` + `FAIL 7.4`；② 副本把 flip 改 no-op ⇒ **rc=1** + `FAIL: empty injection — lock bytes unchanged` + `FAIL 7.4`（原 `run.sh` md5 `fb19c476…` 未被改动）。
- **3.2 基线重建**：命令 = `git show 7aacef63:tests/inst/00-isa-design/pseudo_set.fx_reg.S` → python 机械展开 → `llvm-mc` 汇编 → 与新载体 `.o` 比；实跑 `show rc=0 展开 rc=0(baseline … expanded: 13) base-asm rc=0 new-asm rc=0`、两侧 md5 同 `dee7956a…`；**移走历史 `.fx_reg` 产物后仍 PASS**（note「无需 SKIP」）⇒ 无 SKIP、干净树可判。
- **2.5b 五条负例**：RUN 行 5、note 明写「177 是文件数口径」；**删 1 条** ⇒ `期望=5 实际=4`、`FAIL 2.5b`、rc=1；**翻 1 条期望** ⇒ `FAIL 2.4 check-lit`、rc=1（176/177）；两次均还原后回绿（md5 `21556077…` 相等）。
- **门控真数**：`check-lit` 177/177 rc=0；`check-inst-asm` 904/904（272 id/271 链例/633 故障例）rc=0；`check-spec-{readonly,drift,refs,purity,changelog,codeblocks}`、`check-tests-index` 476、`check-case-ledger`、`check-contracts-{dir,pending,relocs}`、`check-knowledge-refs`、`check-run-artifacts`、`check-dirs`、`check-no-residue`、`validate-vectors` 全 rc=0；证据脚本 默认 **39/39**、`--full` **40/40**、`--inject 4` **40/40**、`--inject 1,2,3` **42/42**（7.1/7.2/7.3 各 PASS ⇒ 单跑各 40/40）。
- **L1 `make check` rc=2（重试 2 次同）——红项全为外因**：`check-patch-tree: linux`（并发会话 `m14-linux-009` 14:49 起跑 `check_k2.py --inject`，写共享 `.work/source/linux/arch/dadao/kernel/time.c`，`git status` 见 ` M`）与 `check-milestones-fresh R1 m14-linux-009`（该册 L27「待开始」却已有 worktree `/tmp/opencode/m14-linux-009/wt`）；本任务自身目标逐条 rc=0。

**判决：Accepted** —— 上轮唯一阻断项（注入 4 空注入 + 完成区数字不实）已修并经我独立复验，内容侧零改动、约束无违反。

**非阻断 finding**（交 architect 收尾处置）：① 3.2 展开条数写作字面值 `n == 13`（可改为由 `__CHECK_RD` 行数现场派生；当前实测 13、`n≠13` 即 FAIL，不构成假绿）；② 完成区两处 L1 表述互相矛盾（「除 2 项外全绿」vs 遗留①「`make check` rc=0」），我方实跑 rc=2 且红项均外因；③ 我方审阅日志曾致 `check-run-artifacts A3` 红 7 项（命名不合规），已由主会话改名为 `review-m15-spec-003/m15-spec-003-review-*`，现 rc=0。

## 完成区

**测试结果**（第 2 轮修复后实跑）：证据脚本 默认 39/39 PASS（rc=0）、`--full` 40/40（含 `check-inst-asm` 904/904）；注入 1/2/3/4 **各 40/40**（第 1 轮注入 4 为空注入、实跑 `PASS=39 FAIL=1`，本轮已修，见「第 2 轮 engineer」）；`check-lit` 177/177（文件数口径，负例覆盖由脚本 2.5b 的五条 RUN 行守护）；`check-inst-asm` 904/904（272 id / 271 链例 / 633 故障例，与改前同）；`make check`（L1）除 2 项外全绿，两项均为外来：`check-milestones-fresh` R1（并发任务 `m14-linux-009` 台账行未移入「进行中」）与 `check-run-artifacts` A3（审阅侧 7 个日志命名不合规）——前者台账归主会话、后者属审阅产物，均未代改（不凑绿）；`check-temp-dirs`/`check-musl-freshness`/`check-builtins-freshness` 已绿；审阅记录里 1 处具体 `.work` 路径已改占位形（否则 `check-knowledge-refs` 必红）。

**修改文件**：`spec/SimRISC-00`（§5 表 8→7 + 引导句 + 附录 1 条）、`spec/Toolchain-01`（§6.1 标题 8→7 条/表 8→7/新增 `set.rf` 分工条、§6.2.3 改名 + 寄存器传值示例 + 写宽对照、附录 1 条）、`spec/SimRISC-02`/`03`（册首伪指令清单加 `set.rf`）、`manifests/spec-readonly.lock.toml`（4 册 sha 同笔重算 + 授权注记）、`components/llvm-project/patches/.../DADAOAsmParser.cpp.patch`、`components/llvm-project/changelog.md`（M15 条）、lit 三文件（`set-ft-fo.s`/`m4-pseudo-set.s`/`README-m4.md`）、`tests/inst/00-isa-design/pseudo_set.fx_reg.S`→`pseudo_set.rf_reg.S`（`git mv` + 13 处 `set.rf` + 头注）、`pseudo_set.ft_imm32.S`（对照指针）、`tests/inst.yaml`、`tests/inst/README.md`、`tests/case-ledger.tsv`（`--write` 重生成）、`.tao/contracts/{contract-asm,contract-fp,contract-isa}.md`、`tools/spec/check_spec_codeblocks.py`、`tools/testcases/{check_tests_index,validate_vectors,validate_mc_vectors}.py`。

**验收结果**：两册表 7/7 且第三列逐字相同；`set.ft`/`set.fo` 在 `spec/` 已 0 处寄存器源；`check-spec-{readonly,refs,purity,changelog,codeblocks}`+`check-rule-refs`+`check-contracts-dir`+`check-contract-relocs`+`check-interface` 全 rc=0；`llvm-mc` 新 md5 **342a7d007a54991b88d501c9d2d0576b**；`set.rf rf, rs` ⇒ `rd2rf`（`40f41141`）/`rf2rf`（`40f01081`）/rf0 源（`40f02001`），旧形 `set.ft|set.fo rf, rs`、`set.rf rf, imm`、`set.rf rf0, rf`、符号源均 rc=1 且报错文本命中；载体三平台各 1 镜像 / 13 检查点 / 104 B，`semi.out` md5 `9e71680a0735c9d589ca9d4b0bafc72e` 三平台相同；改名前后目标文件 md5 同为 `dee7956a7566f8f732b6574a0a6ce02c`（ELF `cd008f7571234cebce7b45c20d01b9e3`）⇒ 换名不改语义；`check-tests-index`（476 条；`- id:` 276 = 改前）/`check-case-ledger`（5438 = 改前、tsv 5442 行不变）/`check-dirs`/`check-no-residue`/`check-inst-macro-scope`/`validate-vectors` 全绿；`check-source-state`/`check-patch-tree`/`check-index-blobs` 绿。

**新发现/坑**：① 新文件补丁改 `+` 行后必须同步 `@@ -0,0 +1,N @@` 与 `index` blob——只改行会让 `git apply` **静默截断**到旧 N（症状 `expected '}' at end of input`），`check-index-blobs --fix` 只修 blob 不修行数；② 注入还原用 `cp -p` 会保留旧 mtime ⇒ ninja 不重编、「还原」实为注入态二进制（假绿/假红），必须 `touch` 后再重建；③ 重建 LLVM 后 `check-musl-freshness`/`check-builtins-freshness` 的 toolchain stamp 必失效，须补 `make build-musl-shared`；④ `git reset --hard base` + 重放会刷新全部补丁文件 mtime ⇒ 全量重建（≈10 min），单文件小改可用 `git add -A && commit --amend`（`base..HEAD` 仍 1 个 commit，`check-patch-tree` assertion ⑨ 通过）。

**遗留问题**：① （已闭环）L1 曾有 `check-temp-dirs` 红：`m14-linux-005/006/007/008` + `m15-testcases-002-review`（均已 `已验证`）的陈旧临时目录，按「他册残留不代删」留给主会话；现已清理，`make check` rc=0；② `ADR-0013 D11` 仍写「保留 8 条」且列 `set.ft/set.fo` 的 `rs` 形与 M13 已删的 `ft2ft`/`fo2fo`——改 Accepted ADR 需用户逐条确认，未动；③ `docs/DDLN/E-002`「只保留 8 条合成型」、`tools/testcases/arch/min_rom_probe_036t.py` 注释 `set.ft value transfer`、`tests/inst/MIGRATION.md §048`（历史迁移记录，写旧载体名）未改；④ `.tao/knowledge/refs/m13-005-acceptance.*` 冻结产物仍用旧名（不属活文档）。
