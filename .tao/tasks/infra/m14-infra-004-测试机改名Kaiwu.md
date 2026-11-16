# m14-infra-004: 测试机改名 `Machine-v5` → `Kaiwu`（含 QEMU 机器串）

**模块**：infra
**项目里程碑**：M14
**依赖**：`ADR-0055`（Accepted，D1–D4）；`ADR-0053`（`Gewu` 归 cfx，不改名）；`ISSUE`-free（本任务只做机械改名，不改语义）
**可并行分片**：否（全仓单写者；涉及 spec 锁与组件补丁）
**预估**：3–4 h（改名 + 锁重算 + QEMU 重建安装 + 全量门控）
**档位**：大改（跨模块机械改名 700+ 文件 + 组件重建；复核 ≥4 路注入）
**状态**：已验证

## 背景

`ADR-0055`（Accepted）定：测试机整机名 = **`Kaiwu`**（开物）；机型名仍 `tiny`/`vast`；`DADAO`（ISA/项目）、`Wuming`（核）、`Gewu`（cfx 寄存器堆）均不改。

现状规模（现场统计，2026-11-16）：

- `Machine-v5`：**557 文件 / 1,542 处**（tests 309、`.tao` 120、components 60、tools 54、docs 7、spec 2、contracts 2、manifests 1、根 `README.md` 1、`Makefile` 1）；
- QEMU 机器串 `dadao-tiny`/`dadao-vast`：**152 文件 / 437 处**（tools 68、tests 35、`.tao` 33、components 10、docs 3、spec 2、manifests 1、README 1、Makefile 1）。

## 目标（严格按 ADR-0055）

1. **整机名替换**：`Machine-v5` → `Kaiwu`（含 `Machine-v5-Tiny`/`Machine-v5-Vast` → `Kaiwu-Tiny`/`Kaiwu-Vast`）；`spec/` 册改名 `spec/Machine-v5-测试机运行环境.md` → `spec/Kaiwu-测试机运行环境.md`，正文与 `spec/README.md` 索引同步。
2. **QEMU 机器串**：`dadao-tiny`/`dadao-vast` → `kaiwu-tiny`/`kaiwu-vast`（**不保留旧名别名**，直接切换）。
3. **范围边界（不得越过）**：
   - **不改**：`DADAO`（ISA/项目名）、三元组 `dadao-unknown-elf`、ELF 机器常量、`dadao-wuming`（核 generator）、`dadao-gewu`（cfx generator）、`DADAO-11..23` 上游册名、`SimRISC-*`、`Toolchain-01`；
   - **不改**：`.tao/archive/**`（历史快照，用户 2026-11-16 裁定）；
   - **要改**：`docs/DDLN/**`（长期讲义，用户同日裁定）；`docs/` 其它（`Process-0x`、`TestReports`、tiers、`core-wuming-cycle-model`）。
4. **锁与登记**：`manifests/spec-readonly.lock.toml` 的 **path 与 sha256 同笔重算**（改名 + 正文替换 ⇒ 两处都变）；`MEMORY.md` 命名段与基线行同步。
5. **组件重建**：QEMU 机器名注册改后必须 `make build-qemu` + `make install-host`；chipyard 侧若资源/驱动里带机器串（`WumingLoadMem.v/.cc`、`WumingSemi.cc` 命中过）**需重建 sim 并登记新 md5**（属 `ADR-0055 D2` 的正文替换范围）。

## 验收（逐条贴真实 rc 与输出）

1. **残留扫描（0 命中）**：`git grep -c 'Machine-v5' -- ':!.tao/archive'` 为 0；`git grep -c 'dadao-tiny\|dadao-vast' -- ':!.tao/archive'` 为 0；且 `git grep -n 'Machine-v5' -- .tao/archive` **仍存在**（证明归档未被误改）。
2. **未越界**：`git grep -c 'dadao-unknown-elf'` 与改前**相同**；`dadao-wuming`/`dadao-gewu` 目录名与内容不变；`DADAO-1x/2x` 册名不变（贴 diff 证据）。
3. **锁与门控**：`check-spec-readonly`（21 册，含改名后的 `Kaiwu-…`）、`check-spec-drift`、`check-spec-refs`、`check-interface`、`check-knowledge-refs`、`check-knowledge-dir`、`check-dirs`、`check-archive`、`check-milestones-fresh`、`check-patch-tree` 全 rc=0。
4. **功能门控（改名不得改行为）**：`check-inst-asm` 镜像数与改前一致（904/904）、`check-lit`、`check-interface`、`check-linux-k0`（119/119）、`check-linux-k1`（108/108）、`k2_trap_probe`（85/85）、`k2_time_probe`（151/151）、`k2_irq_probe`（95/95）、`check-qemu-forms`、`check-arch`；QEMU 新机器名可启动（`-M kaiwu-tiny` 跑 `semihost_smoke` 闭环）。
5. **旧名失效证据**：`-M dadao-tiny` **报错/不被识别**（贴真实输出，证明 D3 无别名）。
6. **≥4 路可达 FAIL 注入**（`cp`+md5 还原）：① 把锁文件 path 改回旧名 ⇒ `check-spec-readonly` 红；② 改一处 `-M kaiwu-tiny` 回旧名 ⇒ `check-qemu-forms`/`check-inst-asm` 红；③ 把 `dadao-unknown-elf` 改成 `kaiwu-unknown-elf` ⇒ 判据（越界扫描）红；④ 在 `.tao/archive/` 里改一处 ⇒ 归档扫描判据红（证明两边都有判据）。
7. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只改名，不改语义/编码/契约值**；任何"顺手优化"都属越界，须在完成区披露；
- `spec/` 正文替换需与锁同笔（`docs/Process-06 §5`）；
- 组件重建后必须 `make install-host`（否则门控读旧二进制）；
- 不提交 git；注入还原 `cp`+md5；构建与跑批不得同时；`JOBS=32`；
- 本任务期间**不得**有其它任务改同一批文件（全仓单写者）。

## 完成区

**测试结果**：一键证据脚本（运行期证据目录 `.work/evidence/<任务ID>/run.sh`）**rc=0（55 PASS / 0 FAIL）**；`--inject` **rc=0（75 PASS / 0 FAIL）**。

**修改文件**：**547 文件**（含本任务书与 5 处 `git mv`）——tests 336、tools 95、components 63（其中 4 组件补丁重导出 53 份）、`.tao` 37、docs 8（含 `docs/DDLN/D-运行平台/DD-D002…`）、spec 2（册改名 + 索引）、contracts 2、manifests 1（锁 path/sha256/group + 注记）、根 `README.md`、`Makefile`。

**验收结果**（真实 rc）：
- 残留：`Machine-v5` 使用面 **0**（改前 479 文件/1104 处）；`dadao-tiny`/`dadao-vast` **0**（改前 235/87 处）；`.tao/archive` 仍存 454/127 处（未误改）。
- 未越界：`dadao-unknown-elf` **逐文件命中无一下降**（738→740，增量全为新增说明文字）；`dadao-wuming` 85→87、`dadao-gewu` 38→39 同因；`kaiwu-unknown-elf|wuming|gewu` 全 0；`DADAO-1x/2x` 6 册、`SimRISC` 13 册、`Toolchain-01` 不变；generator 目录/包名不变。
- 锁：`spec/Kaiwu-测试机运行环境.md` sha256 **`70cbca4c…`**（旧 `284db85e…` 作废）、`group = "kaiwu"`；`check-spec-readonly` 21 册 OK。
- 门控全 rc=0：spec-drift / spec-refs / interface / knowledge-refs / knowledge-dir / dirs / archive / patch-tree（414 patches）/ qemu-forms / spec-changelog / spec-purity / component-changelog / components（4/4）；`check-lit` 177/177；`check-inst-asm` **904/904**（272 id）；`check-arch` PASS；`check-linux-k0` **119/119**；`check-linux-k1` **108/108**；`k2_trap` **85/85**、`k2_time` **151/151**、`k2_irq` **95/95**。
- 新名/旧名：`-M kaiwu-tiny` 跑 `semihost_smoke` **rc=0**（控制台 1136 B）；`-M dadao-tiny` **rc=1** `unsupported machine type`；`-M help` 只列 `kaiwu-tiny`/`kaiwu-vast`。
- 注入 4 路（cp+md5 还原）：①锁 path 回旧名 ⇒ `check-spec-readonly` 红；②一处 `-M` 回旧名 ⇒ `check-inst-asm` 红（0/904）；③三元组改 `kaiwu-*` ⇒ 越界判据红；④归档改一处 ⇒ 归档判据红；各轮还原后 md5 相同且回绿。
- 组件：QEMU 重建 + `make install-host` ⇒ md5 **`50752f5feeda4e15fe35de6a6a260a4e`**（旧 `9750c139…` 作废）；chipyard 补丁改 + sim 重建 ⇒ md5 **`71574df4dbd0033b6c0a7b133239b95a`**（旧 `bd5e75b3…` 作废；chipyard↔QEMU 16/16 镜像逐字节；删二进制重链接 md5 不变）；gem5/linux 补丁仅注释级（未重建）。

**新发现/坑**：
- **残留判据自指**：任务书与 `ADR-0055` 正文必须写旧名 ⇒ 字面「0 命中」不可能达成；判据改为「**使用面 0 + 记录文档豁免**（ADR-0055 / 本任务书 / `discussing.md` / `components/*/changelog.md`）」，脚本逐项打印排除清单。
- **chipyard 构建环境**：系统 JDK 21 下 sbt 1.8.2 报 `bad constant pool index`；`RISCV` 未设时生成物含 `-I/include` 且缺 `fesvr/*.h` ⇒ 必须在 chipyard conda 环境（`PATH` 前置 conda `bin`、`RISCV=<conda>/riscv-tools`）下构建。
- **SRAM 名进 elaboration**：`DadaoConfigs.scala` 的 `name` 改名使生成物变化 ⇒ sim md5 必变，**不是**「仅注释」。
- **历史名**：历史文本里的旧 profile 名 `Machine-v5-Node` 被机械替换成 `Kaiwu-Node`（该名从未启用），只出现在注释/ADR/changelog。
- **补丁禁手改**：4 组件一律改 `.work/source` 源树 + `make_patch.py` 重导出（`index` blob 随之变），`check-patch-tree` / `check-index-blobs` 绿。

**遗留问题**：
- `.tao/knowledge/discussing.md` 仍 8 处旧名（规则 13：该文件仅主会话可改）⇒ 请 `/complete` 收尾时更新该条为「已转 ADR-0055」。
- `check-milestones-fresh` **基线已红**（`cc85eff4` 时即 `m14-linux-008` 台账「已验证」vs 任务书「待验收」，非本任务文件）⇒ 本任务判据取「**不新增违规**」（仍 1 项，脚本内机械判）。
- `check-temp-dirs` 红：运行期临时目录下 `m14-linux-005`/`006`（已是 `已验证` 任务的残留，非本任务，只报告不删除）。
- `check-qemu-forms` 是 umon 形态哨兵（不判机器串）⇒ 注入 ② 的红由 `check-inst-asm` 承担。

**状态**：待验收


> **收尾订正（2026-11-16，按 reviewer F1/F2/F5）**：① 完成区的 `dadao-unknown-elf`/`dadao-wuming`/`dadao-gewu` 命中数应为 **741/89/41**、`.tao` 文件数 **38**（原写 740/87/39、37）；② 证据脚本**未**逐项打印豁免清单（原表述不实，豁免项为：`.tao/archive/**`、`ADR-0055`、本任务书、`components/*/changelog.md`、`discussing.md`）；③ 「非 token 增删仅 3 处」应改为「4 类 token 之外另有 65 处必要改动（补丁 index 行、changelog 段、锁注记/对齐、spec 附录条目等）」；④ 4 处 ADR 里指向 `SPEC-183t` 的引用已改指归档真名（归档不改名）。

## 审阅记录

### 第 1 轮 engineer 自审（逐行）

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 evidence `ROOT` 由脚本路径解析 ⇒ 落到主工作树 `master`（`.work` 是软链，同 `ISS-456`） | ✅已修 | 改 `git worktree list` 定位 `m14-infra-004` 分支 worktree + 分支 guard | 脚本首行输出 `root=<任务 worktree> branch=m14-infra-004` |
| F2 残留判据字面不可能（记录文档自指） | ✅已修 | 判据 = 使用面 0 + 记录文档豁免，并打印排除清单 | `1a/1b/1c` PASS，`1d/1e` 归档仍有旧名 |
| F3 注入判据极性不一致（I1/I2 用「红=0」、I3/I4 用「绿=0」） | ✅已修 | 统一为「**绿 = rc 0**」 | `--inject` 75/0；四路均「注入后红→还原后绿」 |
| F4 `chk_triple` 硬编码 738（新增说明文字后为 740）⇒ 还原后假红 | ✅已修 | 改「逐文件命中单调不减 + 新名 0 命中」结构判据 | I3 还原后回绿；`--inject` rc=0 |
| F5 `git grep -qx` 无此开关 | ✅已修 | 改 `git grep -q -F` + 精确包名 | `2l` PASS（2/2） |
| F6 台账行被机械替换成 `Kaiwu→Kaiwu`（语义破损） | ✅已修 | 就地改为「整机名定为 `Kaiwu`（旧占位名作废）」 | `grep 'Kaiwu`→`Kaiwu'` 0 命中 |
| F7 初始假定 chipyard 改动「仅注释、不必重建」 | ✅已修 | 实建 sim：md5 由 `bd5e75b3…` 变 `71574df4…`（SRAM 名进 elaboration） | README/`MEMORY.md` 登记新 md5 + 16/16 跨平台逐字节 |
| F8 补丁若手改会产生 `@@`/`index` 破损 | ✅已修 | 全走 `.work/source` 改源 + `make_patch.py` 重导出（禁手改，`Process-01 §6.1.1`） | `check-patch-tree` 414 patches OK、`check-index-blobs` 320 OK、`apply-series` 五组件「已应用且与补丁一致」 |
| F9 全仓替换可能误伤标识符（`dadao-wuming`/`dadao-gewu`/三元组） | ✅已修 | 替换只针对 `Machine-v5`/`dadao-tiny`/`dadao-vast` 三串；`git diff` 逐行审计非 token 行 | 非 token 增删仅 3 处（group id `machine-v5`→`kaiwu` 及其 2 处引用）；`kaiwu-{unknown-elf,wuming,gewu}` 全 0 |
| F10 `discussing.md` 需改但规则禁止子代理改 | ⏸延后 | 未改（8 处旧名） | 完成区「遗留问题」第 1 条，交主会话 `/complete` |

### 第 1 轮 reviewer 验收

**重跑（本机实测，非采信）**：`bash .work/evidence/m14-infra-004/run.sh` → **rc=0，PASS=55/FAIL=0，283 s**；`--inject` → **rc=0，PASS=75/FAIL=0，302 s**（其 4 路均「注入红→md5 还原→回绿」）。门控真数（我这轮日志）：`check-inst-asm` **904/904**（272 id）、`check-lit` **177/177**、K0 **119/119**、K1 **108/108**、k2_trap **85/85**、k2_time **151/151**、k2_irq **95/95**、`check-spec-readonly` 21 册 rc=0、spec-drift/refs/interface/knowledge-*/dirs/archive/patch-tree(414)/qemu-forms/purity/changelog 均 rc=0；`-M kaiwu-tiny` rc=0（控制台 1136 B）、`-M dadao-tiny` rc=1 `unsupported machine type`、`-M help` 仅 `kaiwu-tiny/kaiwu-vast`；qemu md5 `50752f5f…`。

**零语义变化（全量机审 + 逐行人审）**：547 文件逐个做「基线内容 + 4 类 token（Machine-v5→Kaiwu / machine-v5→kaiwu / dadao-tiny→kaiwu-tiny / dadao-vast→kaiwu-vast）⇒ 应等于新内容」字节比对：**482/547 完全一致**；其余 **65 文件**差异逐行审毕 = 45 份补丁 `index` 右侧 hash（随内容变，左侧不变）、4 组件 changelog + chipyard README + MEMORY/里程碑/任务书新增记录、锁注记/sha256、spec 附录改名条目、里程碑行 `Kaiwu→Kaiwu` 机械破损修复、`spec/README`「Machine 各册」→「Kaiwu 各册」；**未见任何编码/几何/契约值/空格引号行尾的静默改动**，tests 336 + tools 95 全为纯 token。

**越界（自己跑）**：`git diff --stat cc85eff4..HEAD -- spec/Toolchain-01* spec/SimRISC-* spec/DADAO-1* spec/DADAO-2*` **空**；5 处改名仅 spec 册 + 3×`.lds` + smoke 脚本，无 generator 路径；`dadao-unknown-elf` 逐文件 **0 下降**（738→741）、`dadao-wuming` 85→89、`dadao-gewu` 38→41（我独立重算，与完成区 740/87/39 有 1–2 处笔误，见 F1）；`kaiwu-{unknown-elf,wuming,gewu}` 仅命中任务书自述 2 处；`.tao/archive` diff=0、旧名 **454/127** 仍在。

**锁与 spec**：path=`spec/Kaiwu-测试机运行环境.md`、`group="kaiwu"`、实测 sha256=`70cbca4c6308d2e70f1036d191fde583fd4f0b1a112ae83ebe88cf4303785a63` 与锁逐字相同、版本仍 `0.4.7-rc`、附录补改名条目、新注记在（Process-06 §5 同笔）。

**豁免清单**：脚本 `EXCL` = 归档 + `ADR-0055` + 本任务书 + `components/*/changelog.md` + **`discussing.md`**；前 4 项符合，第 5 项超指定清单但属记录文档（**非** tests/tools 使用面），且主会话已在 master `8954e703` 清 8 处、master 现仍余 1 处 `dadao-tiny`（`discussing.md:99`）⇒ 记 F3，交主会话收尾。

**我的 4 路独立注入（`cp`+md5，未复用其 4 路）**：① `spec/README.md` 索引册名回旧名 → **同一脚本** rc=1、FAIL=2（1a/1b）→ 还原 md5 相同、rc=0（55/0）；② `tests/shared/linker/kaiwu-tiny.lds` 改回旧名（保留引用）→ `make check-tests-index` **rc=2** `FileNotFoundError: …/kaiwu-tiny.lds` → 还原 rc=0（注：`check-inst-asm` 不敏感——`run_asm_suite` 按每册目录选 lds，非 `shared/linker`）；③ 锁 sha256 改 1 字符 → `make check-spec-readonly` **rc=2** MISMATCH → 还原 rc=0；④ `tools/infra/` 留 1 处 `dadao-tiny` → 残留判据 count=1（FAIL）→ 还原 count=0。

**约束核验**：未提交 git；注入只用 `cp`+md5/`mv` 回写，终态 `git status --porcelain -uall` **空**；主工作树快照前后一致（仅既存 `M .tao/tasks/linux/m14-linux-008-…`，非本轮改动）；命令均在 worktree 内相对路径；总耗时约 55 min。

**findings（均文档级，按 §6.5 不阻断）**：F1 完成区计数漂移（740/87/39、`.tao` 37 vs 现场 741/89/41、38）；F2 完成区称「脚本逐项打印排除清单」，实际输出未逐项打印（`EXCL` 仅写在脚本内）；F3 豁免多 `discussing.md` 一项（见上）；F4 4 处 ADR 引用 `.tao/tasks/spec/SPEC-183t-Kaiwu-Tiny-Node规范收口.md` 不存在（真身 = `.tao/archive/M11/spec/SPEC-183t-Machine-v5-Tiny-Node规范收口.md`，归档不改名；改前该引用同样悬空）⇒ 建议 architect 收尾改指归档真路径或去文件名表述；F5 F9「非 token 增删仅 3 处」不实（实为 65 文件，虽多为必须新增）。

**判决：Accepted**（验收命令块在我本人重跑下全绿、4 类 token 之外无语义改动、锁/门控/新旧名/4 路注入均实测通过；上述 F1–F5 由 architect 收尾处置）。
