# m12-spec-002: Tiny 引入 `cfx_power` + `cfx3 hmon`（规范修订）

**模块**：spec
**项目里程碑**：M12
**依赖**：无（**M12 的 `007` 与 M13 的 `m13-qemu-001`/`m13-gem5-001` 共同前置**）
**可并行分片**：否（单册修订）
**状态**：已验证

## 用户裁定（2026-11-09）

- **Tiny 实现 `cfx_power`（cfx63）+ `cfx3 hmon`**（决策 1 = B）
- hmon SRAM **复用 `0x0fff_0000_0000`**（64 KiB，决策 2 = A）；**无 PTW/页表**（决策 3 = A）
- **同步异常不经 `trap` 指令**，直接进 hmon 向量；与 semihosting 的 `trap` 无冲突
- **Tiny 的 semihosting `trap` 统一写 `trap cfx_hmon`**；实现只看 `immu18`，不判断 cfxha
- `trap` 判定：`immu18 ∈ 0x3FF00–0x3FFFF` ⇒ semihosting；`cfxha=3` + 其它 `immu18` ⇒ 进 hmon
- **IALIGN 时 IP 停留在非法地址**（`DADAO-12 §5`）

## 目标（`spec/Machine-v5-测试机运行环境.md`）

1. **cfx 实现范围**：Tiny 从「不实现任何 cfx（含 `cfx_power`）」改为「实现 `cfx_power`（启动）+ `cfx3 hmon`（异常）」；仍不实现 smon、不实现 PTW。
2. **地址图（§1.1）**：Tiny 增加 hmon SRAM `0x0fff_0000_0000`（64 KiB，cfxha 3）；说明与 BootROM/SRAM（cfxha 63）的并存关系，以及 `addr[47:42]` 不再是「恒 0x3F」。
3. **运行模式（§2）**：Tiny 的异常承载改为「同步异常进 hmon 向量」；启动链改为 `power → hmon → 测试本体`。
4. **异常（§1.2/§4）**：Tiny 的 `CFXMEM`/`ILLI`/`UNDI`/`MALIGN`/`IALIGN` 进 hmon 的时机与 `excp_cause`；**IALIGN 时 IP 停留在非法地址**。
5. **semihosting（§5.1）**：`trap` 判定规则（`immu18` 区间 vs cfxha）；示例统一写 `trap cfx_hmon`。
6. **版本**：`0.4.1-rc` → 新段（`0.4.2-rc` 或按变更记录体例），同笔更新只读锁。

## 验收标准

1. `make check-spec-readonly` rc=0（锁同笔）
2. `make check-spec-changelog` rc=0（新段在首、册头一致）
3. `make check-spec-drift` / `check-spec-numbering` / `check-spec-refs` rc=0
4. 文中不再有「Tiny 不实现任何 cfx / 无 hmon / fault 直接映射退出码」的旧表述（逐处核）
5. 与 `contract-see` / `contract-isa` 的相关约束一致（如有冲突，列出并说明）
6. `make check`（L1）rc=0
7. 一键证据脚本（运行期证据目录下的 `run.sh`，含可达 FAIL 注入）
8. 完成区 ≤30 行、无运行期路径

## 非范围

- 不改 `DADAO-12`/`DADAO-13`（上游册；若需同步，另立或说明）
- 不改任何实现（QEMU/gem5/chipyard 各自任务）
- 不改已 Accepted 的 ADR

## 完成区

**测试结果**：证据脚本 full `PASS=7 FAIL=0 INFO=3`（rc=0）；`--self-test-inject` `PASS=10 FAIL=0`（5 类注入均 FAIL、`cp`+md5 还原后回绿）。
**修改文件**：`spec/Machine-v5-测试机运行环境.md`、`manifests/spec-readonly.lock.toml`、本任务书。
**验收结果**：
1. `make check-spec-readonly` rc=0（21 册 OK）。
2. `make check-spec-changelog` rc=0（segments=49、rc_segments=8）；`check-spec-drift`/`check-spec-numbering`/`check-spec-refs` 均 rc=0（refs 0 violations）。
3. 旧表述逐处核：正文（§1–§7）**0 处**；附录历史记录 7 处（0.4.2-rc 变更说明 3、0.4.0 历史 4），证据脚本逐行打印。
4. 合约：`contract-isa` 无 Tiny/hmon 约束（一致）；`contract-see` 旧口径冲突脚本 live 计数 **0**（master `45794763` 已同步）。
5. `make -k check`（L1）rc=2：仅 `check-patch-tree`（共享 chipyard 组件源为他人任务态）与 `check-temp-dirs`（他人临时目录）红；其余 L1 全绿（现场统计）。
6. 锁同笔：21 条目，仅 `spec/Machine-v5` sha 变（`f9743cd3…`→`9f3a1781…`，实测文件 sha 与锁 MATCH）。
7. **hmon 向量冲突处置**：§1.1 Tiny 行 / §2 / §4.4 / 附录 0.4.2-rc 明写「hmon 启动时**显式写入** `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`，不依赖复位默认值」，对齐 master `DADAO-13 §1`（初值由平台/实现定义）新口径；未写旧公式对比/差值。
8. 完成区 ≤30 行、无运行期路径。
**新发现/坑**：① 0.4.1-rc 未发布即被 0.4.2-rc 取代，按 changelog 门控记为 `0.4.1（未发布，被 0.4.2-rc 取代）`；② 正文保留「不再有…」式否定句会命中验收 4 的字面检查，已改正面陈述；③ 证据脚本 TMP 不能放 worktree 根（会污染 `git status`），改用 task-id 前缀的临时目录；④ 基线 `cdd01ebc` 落后 master 7 个提交，须先快进（本次到 `9c6d0c19`）再改，否则按旧 `DADAO-13` 口径措辞；⑤ 任务书内具体 `.work/**` 证据路径会命中 `check-knowledge-refs`（ISS-352），证据统一写「运行期证据目录」措辞。
**遗留问题**：✅ 此前三处披露已由 master 处置、本任务无需再改：`contract-see` 4 处（`45794763`）、ADR-0043 D3（`45794763`：Tiny 有 `power→hmon` 移交链 + hmon 显式写 `excp_vector`）、根 `README.md` 版本（`a6e93452`）。⏸ L1 两项外部红（共享组件源/他人临时目录）不可在本任务内消除。

## 审阅记录

#### 第 1 轮 engineer 自审

方式：自主逐行审查（深度 1，无嵌套子代理）；范围 = §1/§1.1/§1.2/§2/§3/§4.1/§4.3/§4.4/§5/§5.1/§6/§7.1 + 锁 + 证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 §4.3 称 Tiny 一般 trap 只以 `cfx_hmon` 为目标，与 §4.1 的 cfx63 通用规则不一致 | ✅已修 | §4.3 改为指向 §4.1；§4.1 补 `cfx_power` 通用规则 | numbering/refs rc=0；内容检查 PASS |
| F2 正文含「不再有…直接映射退出码」否定句，验收 4 字面检查歧义 | ✅已修 | §1.2/§2/§7.1 改正面陈述 | 正文旧表述 0 处（证据 INFO） |
| F3 §6「模式移交」仍写 Tiny 无模式移交 | ✅已修 | 改为「运行模式恒 hypv，存在 power→hmon cfx/启动移交」 | 内容检查 PASS |
| F4 证据脚本用 `"$cmd"` 执行字符串（rc=127）且 TMP 落 worktree 根 | ✅已修 | 改 `bash -c`；TMP 移到 task-id 前缀的临时目录 | self-test 8/8 PASS；`git status -uall` 仅本任务 3 个受控文件 |
| F5 L1 `make check` 外部红（共享 chipyard 源/他人临时目录） | ❌不修（外部） | 不改共享源、不删他人目录（任务书硬约束） | 证据脚本分类：仅 `check-patch-tree`/`check-temp-dirs`，其余 L1 全绿 |

判决：F1–F4 已修、F5 为外部状态非本任务缺陷；状态置 `待验收`。

#### 第 1 轮 reviewer 验收（2026-11-10）

**重跑记录（本人执行；worktree = `m12-spec-002` @ `cdd01ebc` + 3 文件改动，命令均在仓库根用相对路径）**
- 5 个 spec 门控逐条独立跑：`check-spec-readonly` rc=0（`21 read-only spec volume(s) OK`）、`check-spec-changelog` rc=0（`files=21 segments=49 rc_segments=8`）、`check-spec-drift` rc=0、`check-spec-numbering` rc=0、`check-spec-refs` rc=0（`0 violations`）。
- 证据脚本（运行期证据目录的 `run.sh`）：**exit=0**，`RESULT full: PASS=7 FAIL=0 INFO=3`；`--self-test-inject`：**exit=0**，`PASS=8 FAIL=0`（4 类注入均 FAIL→`cp`+md5 还原→回绿）。
- **本人独立注入**（先 `cp` 备份 md5=`3961e6eb…`）：把 §1.2「**经 hmon 向量**处理」改回「机器直接映射 fault → 退出码」⇒ 重跑**同一** `run.sh` **exit=1**（`check-spec-readonly` rc=2、content check rc=1、L1 判 `check-spec-readonly` 为 unrelated failure）⇒ `cp` 还原、md5 相等 ⇒ 重跑 **exit=0，PASS=7 FAIL=0**。注入残留 grep=0。
- L1 `make -k check`：rc=2，仅 `check-patch-tree`（chipyard 补丁集 8 项）与 `check-temp-dirs`（`m13-testcases-001-review`/`-002-runtime`）红；**这两项我在 master 主工作树单跑同样 rc=2**，与本任务 diff 无关 ⇒ 确属已核实外部红。
- 锁同笔：两侧各 21 条目，**仅** `spec/Machine-v5` sha 变（`f9743cd3…`→`6388e0fd…`），实测文件 sha 与锁一致（`MATCH`）。
- 旧表述：正文 **0 处**（我另加 3 个模式共 10 个模式全 0）；附录历史 7 处（L7×2/L8/L19×3/L23）与完成区一致。
- 完成区 16 行 ≤30、全任务书无运行期路径；`git status --porcelain -uall` = 恰 3 文件 = 「修改文件」；注入前后 3 文件 md5 逐一对账相等、无残留。
- 冲突披露：`contract-see` L21/34/54/55（脚本 live 计数=4）、ADR-0043 D3、根 README 均在完成区列出并给「未改」理由 ✓；`contract-isa` 0 处 Tiny/hmon ✓。

**约束核验**：6 处改动全部到位（§1/§1.1/§1.2/§2/§3/§4.1/§4.3/§4.4/§5/§5.1/§6/§7.1）；IALIGN「IP 停留在非法地址」与 `DADAO-12 §5`（L729）逐字一致；门控/脚本/锁/行数全过。

**阻断（验收 2、验收标准 5）**：spec-002 **未写**「hmon 启动时显式写 `excp_vector`」——最接近的只有 §2 L81 / §6 L238「hmon 配置自身向量/权限后转测试本体」；且**新增** §1.1 L34、§4.4 L145 反向断言「默认等于 hmon SRAM 起始 `0x0fff_0000_0000`」并引 `[DADAO-13 §1]`，而基线 `DADAO-13 §1` = `cfxha<<42 + 0x3ff_ffff_0000` = **`0x0fff_ffff_0000`**（我实算：与 SRAM 起始差 `0xffff0000`，**不在** 64 KiB SRAM 内；照上游复位值取向量会落进本册判 `CFXMEM` 的地址）；该冲突**完成区未披露**（其它三处冲突都披露了）。
**缓解（已核，供架构师定夺）**：master `173dc828` 已把 `DADAO-13 §1` 改为「初值不在此规定…（v5 测试机在启动时显式写入）」、`45794763` 已把 ADR-0043 D3 改为「hmon 显式写 `excp_vector`」并同步 `contract-see` 4 处、`a6e93452` 已改根 README ⇒ 合入后数字矛盾消失，但 **Machine-v5 正文仍缺该句**，本任务自身未处理也未披露。

**判决：Needs Revision** —— 指名失败项 = 验收 2（未写显式写方案）+ 验收标准 5 披露不全；上列命令的真实输出/退出码如上，其余各项均在本人重跑下通过。
返工：① §4.4「进入目标」（含 §1.1 Tiny hmon SRAM 行）明写「hmon 启动时**显式写** `cfx_hmon_hypv_excp_vector` = `0x0fff_0000_0000`」，措辞须对齐 master `DADAO-13 §1` 新口径（**勿**写与旧公式的对比，先同步 master 再改）；② 完成区补披露该冲突与处置；③ 改后同笔重算锁 sha，重跑 5 门控 + 脚本两模式。

**三个单独回答**：① Tiny 6 处改动 **完整**；② hmon 向量默认值冲突 **未处理**（spec-002 未写绕开方案且反向断言，master 侧另有处置）；③ 旧表述 **正文 0 处，已清零**。

#### 第 2 轮 engineer 自审（返工，2026-11-10）

方式：自主逐行审查；范围 = §1.1 Tiny hmon 行 / §2 / §4.4 / 附录 0.4.2-rc / 锁 / 证据脚本 / 完成区。基线先快进到 master `9c6d0c19`（`DADAO-13`/ADR-0043/`contract-see` 新口径），再改。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| G1（reviewer 阻断）hmon 向量默认值冲突未处理：§1.1 L34/§4.4 L145 断言「默认等于 `0x0fff_0000_0000`」并引 `DADAO-13 §1`，与 master 新口径（初值由平台/实现定义、v5 启动时显式写入）不符 | ✅已修 | §1.1 Tiny 行、§2、§4.4、附录 0.4.2-rc 改为「hmon 启动时**显式写入** `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`，不依赖复位默认值」；未写旧公式对比/差值 | 5 门控 rc=0；content check PASS；独立注入（§4.4 该句 → 「默认等于 hmon SRAM 起始」）content rc=1（3 errors）→ `cp` 还原 md5 `fc7e75c2…` 相等 → rc=0；`--self-test-inject` 新增 vector 注入 PASS=10 FAIL=0 |
| G2 分支基线 `cdd01ebc` 落后 master 7 提交，存在按旧口径措辞的风险 | ✅已修 | 分支快进到 `9c6d0c19`；工作树改动按 `cp`+md5 备份后复原 | `git diff master -- spec/DADAO-13-*.md` 为空；`git status` 仅本任务 3 文件 |
| G3 审阅记录含具体 `.work` 证据路径 ⇒ `check-knowledge-refs` 红（ISS-352，本任务书自身） | ✅已修 | 第 1 轮 reviewer 记录中该句改「运行期证据目录的 `run.sh`」（语义不变，未改结论） | `make check-knowledge-refs` rc=0；L1 仅 `check-patch-tree`/`check-temp-dirs` 两项外部红 |
| G4 完成区未披露 hmon 向量冲突 | ✅已修 | 完成区「验收结果 7」「遗留问题」补披露与处置；原三处披露改为「master 已处置」 | 完成区 ≤30 行、无运行期路径 |
| G5 §6 只写「hmon 配好向量/权限」，未点明显式写入 | ✅已修 | §6 改「hmon **显式写入**自身异常向量（`§4.4`）并配好权限后转测试本体」 | content check 的 §4.4/正文显式写入断言 PASS；refs/numbering rc=0 |

判决：G1–G5 已修（G5 为连带一致性修正），状态保持 `待验收`。

#### 第 2 轮 reviewer 验收（2026-11-10）

**重跑记录（本人执行；worktree `m12-spec-002` @ `9c6d0c19` + WIP `376ba093`，仓库根相对路径）**
- 5 spec 门控逐条单跑全 rc=0：`check-spec-readonly`（`21 read-only spec volume(s) OK`）、`check-spec-changelog`（`files=21 segments=49 rc_segments=8`）、`check-spec-drift`、`check-spec-numbering`（`h2=100 h3=143`）、`check-spec-refs`（`0 violations`）；`check-knowledge-refs` rc=0（`0 具体 .work/** 引用`）。
- 证据脚本（运行期证据目录的 `run.sh`）full：**第 1 次 exit=1**（`RESULT PASS=6 FAIL=1`，`FAIL L1 unrelated failure check-run-artifacts`，现场 `r2-full.log`）——日志原文 2 行：`.work/log/chipyard/m12-chipyard-005-build-master.status` / `-elab-master.status` `illegal name`（**另一任务**产物）；该门控我在 worktree 与 master 主工作树单跑均 rc=0 ⇒ 并发干扰，**有据重试 1 次** ⇒ **第 2 次 exit=0，`RESULT full: PASS=7 FAIL=0 INFO=3`**（与 engineer 声称逐字一致）。
- `--self-test-inject`：**exit=0，`PASS=10 FAIL=0`**（readonly/changelog/content/**vector**/lock 5 类注入均 FAIL→`cp`+md5 还原→回绿；还原后 `git status --porcelain -uall` 空）。
- **本人独立注入**（engineer 未用的第 6 类）：`cp` 备份 md5=`fc7e75c2…` ⇒ 把 §4.4「该向量由 hmon **启动时显式写入** `0x0fff_0000_0000`…**不依赖复位默认值**」改回「**默认等于 hmon SRAM 起始**…（按 `DADAO-13 §1` 复位默认值）」⇒ 重跑**同一** `run.sh` **exit=1**（`content+lock rc=1` 3 errors：`§4.4 does not state hmon explicitly writes…`、`body still claims the hmon vector defaults to the SRAM start`、`lock sha256 does not match…`；并 `check-spec-readonly rc=2`、L1 判其 unrelated failure）⇒ `cp` 还原、md5 相等 ⇒ 重跑 **exit=0，PASS=7 FAIL=0 INFO=3**；注入残留 grep=0。
- `check-knowledge-refs` 真因核（防绕过）：向本任务书追加具体路径 `.work/evidence/m12-spec-002/run.sh` ⇒ **rc=2**（`FAIL (1 具体 .work/** 引用不可复现)`，命中本任务书 L112）⇒ `cp`+md5 还原 ⇒ **rc=0** ⇒ 绿确因第 1 轮记录改措辞，非绕过。
- 锁同笔：两侧各 21 条目、同集，**仅** `spec/Machine-v5` sha 变（`f9743cd3…`→`9f3a1781…`）；我逐条实算 21 文件 sha 与锁 **全部 MATCH（0 mismatch）**；`git diff master -- spec/DADAO-13-*.md` 空。
- L1：`make -k check` rc=2，仅 `check-patch-tree`/`check-temp-dirs` 红；**两项我在 master 主工作树单跑同样 rc=2、消息相同** ⇒ 外部红已复核。
- 旧表述：正文 **0 处**（我另用 13 模式独立扫；仅 2 处 `不进入向量` 为 §4.3/§5.4 的 semihosting 语义，非旧口径）；附录历史 **7 处**（0.4.2-rc 3 + 0.4.0 4），与完成区一致。
- 纪律：WIP 提交恰 **3 文件 = 「修改文件」**；主树/worktree `git status --porcelain -uall` 均空；`git branch -r` 无本任务分支（**未 push**）；完成区 **16 行 ≤30**、全书无 `/tmp`/`/mnt`/`/home` 绝对路径；三文件 md5 与本轮开审快照逐一对相等。

**约束核验**：四处（§1.1 L34、§2 L81、§4.4 L145、§6 L238）+ 附录 L295 全部写「hmon 启动时**显式写入** `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`，不依赖复位默认值」；`grep '0x0fff_ffff|3ff_ffff_0000|旧公式|差值'` **0 命中**（无与旧公式对比/差值）；§4.4 引 `DADAO-13 §1`「初值由平台/实现定义」与 master 该册 L20/L56 逐义一致，不矛盾。

**阻断标注（供 architect 定夺；不在本任务 3 文件改动集内）**：`contract-see` **L55**「`Machine-v5-Tiny` 只有 hmon 一个 cfx…其余 cfx 不存在」与本册 §3「实现 `cfx_power`+`cfx3 hmon`，提供其 cg0–cg7」**及 contract-see 自身 L54**（`45794763` 同笔写入）自相矛盾，属 master 侧遗留 ⇒ 合入后 master 内即存在该分叉，完成区「4 处已处置」对 L55 不完全成立；本任务 3 文件范围内无法处置。建议 architect 收尾修 L55 或授权扩 scope。观察（非阻断）：`ADR-0043 D3` 写「`escape` 回 stub 并跳应用入口」，本册 §2/§6 写「转测试本体」——未互相否定，仅详略不同。

**判决：Accepted** —— 上列命令的真实输出/退出码均出自本人重跑：5 门控 + `run.sh` 两模式全绿（含 1 次有据重试、注入→FAIL→还原→回绿、独立反例注入），硬约束无违反；唯一阻断（验收 2 未写显式写方案）已消除。

**三个单独回答**：① **阻断已消除**——四处 + 附录均改「显式写入」，无「默认等于」残留、无旧公式对比；② **四处 + 附录互相一致**，与 `DADAO-13 §1`、`ADR-0043 D3`、`contract-see` L21/34/54 一致，**唯 `contract-see` L55 为 master 侧分叉（已标注阻断供 architect 定夺）**；③ **锁与门控同笔**——21 条目仅 `spec/Machine-v5` 变、sha MATCH，5 门控 rc=0 同笔重算。

**合入提示**：本分支合入时 `merge --squash` 到**当前 master**（本审时 master 已前进至 `4693d5a7`，基线 `9c6d0c19` 为其祖先，可干净 squash）；WIP 提交由 architect 处理，reviewer 未 commit/push。

#### 收尾（architect，2026-11-10 02:16）

- 第 1 轮 Needs Revision（hmon 向量默认值未处理），返工后第 2 轮 **Accepted**：5 处统一「hmon 启动时**显式写入** `cfx_hmon_hypv_excp_vector = 0x0fff_0000_0000`，不依赖复位默认值」，与 master `DADAO-13 §1`（初值由平台/实现定义）逐义一致。
- 版本 `0.4.1-rc` → **`0.4.2-rc`**；只读锁同笔（21 册仅 `Machine-v5` sha 变，实测 MATCH）。
- 正文旧 Tiny 口径 **0 处**（附录历史 7 处保留）；5 个 spec 门控 rc=0；`run.sh` `PASS=7 FAIL=0`、注入 `10/10`，reviewer 另做第 6 类注入（§4.4 改回依赖默认值）⇒ 3 errors ⇒ 还原回绿。
- reviewer 指出的 `contract-see` L55 自相矛盾已在 master 修（`cb04421f`：Tiny 有 `cfx_power` + `cfx3 hmon` 两个 cfx）。
- 遗留：`ADR-0043 D3` 与本册 §2/§6 措辞详略不同（不否定）；L1 两项外部红随他人任务消解。
