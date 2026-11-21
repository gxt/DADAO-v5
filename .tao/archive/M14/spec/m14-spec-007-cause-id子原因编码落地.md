# m14-spec-007: `cause_id` 子原因编码落地（`DADAO-12` 三处 + `contract-see §6.1` 扩列）

**模块**：spec
**项目里程碑**：M14
**依赖**：`ADR-0056`（Accepted，D1–D7）；`m15-spec-003`（在跑：**同改 `manifests/spec-readonly.lock.toml`** ⇒ 必须先合入）
**可并行分片**：否（上游册 + 契约 + 锁）
**预估**：2–3 h
**档位**：大改（上游只读册正文 + 契约 + 锁重算；复核 ≥4 路注入）
**状态**：已验证

> **位图版本注记（2026-11-16，用户三次裁定；以此为准）**：子原因位图最终为 **wyde2 `[47:32]` 专供 `CFXPERM`**（低字节 `[39:32]` 8 位权限原因、`[47:40]` 保留）+ **wyde3 `[63:48]` 专供 `CFXMEM`**（低字节 `[55:48]` 8 位缺失类、`[56] ADWBFAIL`、`[57] NONPTW`、`[63:58]` 保留），共 **18 位**；`[31:16]` 保留给未来新的大类 cause。本任务书下方「背景/目标/验收」中的 **17 位 / `[32:16]`** 表述是首版派单文本，已被三次裁定取代（过程见「审阅记录 F7/F10」），**实现与验收一律按本注记**。

## 背景（`ADR-0056` D1–D7，用户 2026-11-16 逐条确认）

M11 的 `SPEC-186t`/`SPEC-189t` 把页表异常的细粒度原因名（`IGPTRAP`…`DSPFTRAP`、`NUPERM`…`NRPERM`）并入了 `CFXMEM`/`CFXPERM`，用户 2026-11-16 指出**收敛过头**。`ADR-0056` 确定的落地方式：

- **低 16 位不变**（11 项 one-hot cause）；
- **`cause_id[32:16]`（17 位）为子原因 one-hot**，**仅 `CFXMEM`/`CFXPERM` 有效**，其它 cause 必须全 0；
- 位图：`[16..23]` 缺失类（I/D × 4）、`[24..30]` 内存权限类（HSJU 4 + R/W/X 3）、`[31] NCFXPERM`（cfx 访问被来源掩码拒绝）、`[32] ADWBFAIL`（A/D 回写失败）；
- **`CFXMEM`/`CFXPERM` 的 `cause_info` 恒为地址**（`cfxtrap`/`cfx2r*` 拒绝时填**触发指令地址**，与 `excp_cause_ip` 同值，规范须写明"刻意统一"）；其它 cause 的 `info` 语义不变；
- `§7.1` 退出码**不受影响**（仍取低位 cause 索引）。

## 目标

1. **`spec/DADAO-12 §3.6`**：把「所有异常原因编码为 one-hot（64 位）」改写为分层表述 —— `[15:0]` = cause one-hot；`[32:16]` = 子原因 one-hot（仅 `CFXMEM`/`CFXPERM` 有效，其它 cause 必须全 0，非 0 ⇒ 按"未列出位被错误触发"处理）；`[63:33]` 保留。
2. **`spec/DADAO-12 §4.1–§4.6`**（各 monitor/其它 cfx 的原因表）：在 `CFXMEM`/`CFXPERM` 两行注明"`cause_info` = 地址"并**给出 17 位子原因表**（或指向 §3.6 的表 + 一条指针，避免表格重复三处）。
3. **`spec/DADAO-12 §2.2.6`**：把 7 步优先级与子原因对齐（每步对应哪个子原因位），并保留"仅触发优先级最高的异常"表述。
4. **`contract-see §6.1`**：11 项表增「子原因」列（`CFXMEM`/`CFXPERM` 两行给出 17 位映射），并注明"`info` 恒为地址 + `NCFXPERM` 时 = 指令地址"。
5. **锁**：`spec/DADAO-12` sha256 同笔重算 + 注记（引用户 2026-11-16 原话：「收敛过头了…」/「放在31位，然后ADWBFAIL放到32位」/「agree」的确认语）；`contract-see` 版本处理按 `docs/Process-02`（ADR-sourced，版本头不动）。
6. **`discussing.md` 那条"待裁定"改为已定**（由主会话改，不在本任务范围）。

## 验收（真实 rc + 输出）

1. **表完整性**：`§3.6` 或 §4.x 的 17 位表**逐位齐全**（16…32 共 17 行，无重号、无缺号，脚本现算）；`CFXMEM`/`CFXPERM` 两行都注明"`info` = 地址"；
2. **不越界**：低 16 位 11 项 cause 表**一字未改**（`git diff` 该段为空）；`§7.1` 退出码表**零改动**；
3. **契约**：`contract-see §6.1` 增「子原因」列且与 spec 逐项一致（脚本比 17/17）；
4. 门控：`check-spec-readonly`（DADAO-12 重算后 21 册 OK）、`check-spec-refs`、`check-spec-purity`、`check-spec-changelog`、`check-rule-refs`、`check-contracts-dir`、`check-contract-relocs`、`check-interface`、`check-knowledge-refs`、L1 `make check`；
5. **≥4 路注入**（`cp`+md5 还原）：① 删子原因表某一行 ⇒ 完整性判据红；② 把某子原因位号改成 31（与 `NCFXPERM` 撞）⇒ 重号判据红；③ 把 `CFXPERM` 的 `info` 改回"地址或指令编码" ⇒ 判据红；④ 锁 sha 改 1 字符 ⇒ `check-spec-readonly` 红；
6. 完成区 ≤30 行、无运行期路径；`**状态**` → `待验收`。

## 硬约束

- **只改规范/契约/锁**，不改实现与测试（三实现归后续任务）；不改 `.tao/archive/**`、`.tao/adr/**`（`ADR-0040`/`ADR-0020` 的旧名注记由主会话单独处置）；
- 上游册改动须与锁同笔（`docs/Process-06 §5`）；
- 不提交 git；注入还原 `cp`+md5。

## 审阅记录

### 第 1 轮 engineer 自审（2026-11-16）

**范围**：`spec/DADAO-12 §3.6/§2.2.6/§4.1–§4.6` + 附录 1 条、`contract-see §6.1/§6.1.1/§6.6/附录 A/§7`、`contract-cfx-aliases`（生成物重生成）、`manifests/spec-readonly.lock.toml`、运行期证据脚本。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 契约 §6.1.1 插在 §6.1 三个既有 bullet **之前** ⇒ 那三条被归到新子节下（结构错位） | ✅已修 | 「子原因位」「info 恒为地址」两条并入 §6.1 bullet 序列，§6.1.1 移到 §6.1 末、§6.2 前 | 现树 §6.1（L85–L109）→ §6.1.1（L111）→ §6.2（L135）；`check-spec-refs` rc=0 |
| F2 证据脚本契约表解析 **0 行**（正则不认反引号名；区段以 `---` 收尾撞表头分隔线） | ✅已修 | 契约表专用正则；区段终点改下一节标题 | `check all` C1 = **18/18**（改前 0/18） |
| F3 `check-cfx-aliases` 红（DADAO-12 行号位移，139 行来源列全变） | ✅已修 | 重生成 `.tao/contracts/contract-cfx-aliases.md`（生成器 `gen_cfx_aliases.py`，仅来源行号变） | `check-cfx-aliases: PASS (byte-identical)` |
| F4 证据脚本 `check all` 漏跑 D 组；D5 判据用「填 0」过宽（任意处可命中） | ✅已修 | 顺序改 A/B/C/D/E；D5 改逐字匹配归属互斥 + 两 wyde 全 0 + handler 取值 | `check all` ⇒ 当时 30 条断言全 PASS（第 3 轮 A10 改为产物派生后总数 32，见「第 3 轮 R1b」）；注入 3 命中 D2/D3 |
| F5 注入 4 只验自写判据，未验任务验收点名的官方门控 `check-spec-readonly` | ✅已修 | 注入/还原两处都跑该门控并判 rc | 注入态 rc=1（命中 `MISMATCH … DADAO-12`）、还原后 rc=0（21 册 OK） |
| F6 §3.6「（三）保留段」夹在（二）与其「位表见下」之间 | ✅已修 | 保留段说明移到对应表之后 | 现树顺序：（一）（二）→ wyde2 表 →（四）wyde3 表 →（五）归属与用法 →（六）info |
| F7 **位图三次改版**（17 位 `[32:16]` → 18 位 `[63:40]` 三段 → **wyde2/wyde3 分段**，用户 2026-11-16 三次裁定） | ✅已重写 | spec §3.6/§2.2.6/§4.x、契约 §6.1/§6.1.1/§7/附录 A、锁注记、证据脚本、任务书**全部**改为 wyde 表述；`[32:16]`/`[63:40]`/三段 已零残留 | `grep -n '\[32:16\]\|\[63:40\]\|三段'` 在 spec/契约命中 0；`check all` A1–A16 PASS |
| F8 契约 §6.6 原文「`spec/` 正文**不改**（sha256 锁不动）」与本任务现实矛盾 | ✅已修 | 改为「`spec/` 正文修订走 `docs/Process-02`；上游补文另立 spec 面任务并同笔重算锁文件（`m14-spec-007` 即此类）」 | `check-spec-refs`/`check-knowledge-refs` rc=0 |
| F9 `spec/DADAO-13 §2` hmon 表 `CFXPERM` info 仍「访存地址或指令编码」，与「info 恒为地址」冲突；`Kaiwu §4.4` 把它指为 `CFXPERM` info 的规范来源 | ✅已修（第 2 轮，用户授权后） | `DADAO-13 §2` 该行 info → 「访存地址」；附录 `0.1.4-rc` 补 1 条（不写 ADR/任务号，规避 `check-spec-changelog` 禁用项）；`DADAO-13` sha256 同笔重算 + 注记 | `check-spec-readonly` rc=0（21 册）；证据 F1/F2 三处一致；注入 6 可达 FAIL |
| F10 本 worktree 的 `ADR-0056` 副本仍是 17 位旧图（无 wyde/`NONPTW`），而 spec 已按三次裁定落笔 | ✅无需改 | **master 上的 `ADR-0056` 已是 wyde2/wyde3 新版**（主会话改版并经用户确认，`grep wyde2` 命中 5 处）；本 worktree 基线 `98d9426c` 早于该改版 ⇒ 本任务**不动 ADR** | `git show master:.tao/adr/adr-0056-…` 中 D3 已列 wyde2/wyde3 与 `NONPTW` |

**判决**：F1–F9 已修并复验（F9 于第 2 轮授权后修），F10 显式延后（属 Accepted ADR 修订，交主会话）；内容侧无未修 finding ⇒ 状态保持 `待验收`。

### 第 1 轮 reviewer 验收（2026-11-16）

**重跑（基线 `98d9426c`，全部命令在任务 worktree 内执行，退出码为真值非管道码）**：`.work/evidence/<任务ID>/run.sh` ⇒ 6 组 32 断言全 PASS、`rc=0`；`run.sh --self-inject` ⇒ 6 路各「注入 FAIL → cp+md5 还原（md5 一致）→ 回绿」、`rc=0`；`python3 tools/infra/check_spec_readonly.py` ⇒ `21 read-only spec volume(s) OK`、`rc=0`；点名门控 9 项（`check-spec-refs`/`-purity`/`-changelog`/`check-rule-refs`/`check-contracts-dir`/`check-contract-relocs`/`check-interface`/`check-knowledge-refs`/`check-cfx-aliases`）逐一 `rc=0`；L1 `make check` ⇒ `repository checks (L1): PASS`、`rc=0`（`check-patch-tree` 414 patches OK，此前并发红已消）。
**独立判据（reviewer 自写 `check_indep.py`，16 项，`rc=0`）**：§3.6 现场抓 18 行 ⇒ wyde2 恰 `[39:32]` 8 位、wyde3 低字节恰 `[55:48]`、`[56] ADWBFAIL`/`[57] NONPTW`、无跨 wyde；`[31:16]`/`[47:40]`/`[58:63]` 均有保留声明且占用 ∅；§2.2.6 七步引用位名与 §3.6 表逐位同名；契约 §6.1.1 与 spec 18/18 同名 + wyde 列 18/18；三处 `CFXPERM` info 均「地址」、全 `spec/`+`.tao/contracts/` 无「或指令编码」残留；锁 DADAO-12/DADAO-13 sha256 自算与锁逐字一致；§5.2（二）与基线**逐字相同**、§4.1 11 项 (位索引,名称) 相同、`spec/Kaiwu`（§7.1 所在册）整册 md5 与基线相同。
**低 16 位零改动（diff 证据）**：`git diff 98d9426c..HEAD -- spec/` 仅 9 个 hunk（基线行 284/382/437/456/466/476/525/542/972），基线 §5.2 区间为 758–898 ⇒ **无 hunk 落入**；§4.1/§4.6 的 `CFXMEM`/`CFXPERM` 行仅 **info 列**按验收 1 要求改动，位索引与名称列逐字未改（§4.2–§4.5 为「cause_info 恒为地址 + 指针」散文行）。
**4 路自设计注入（不复用其 6 路；`cp`+md5 还原）**：① `[36] NRPERM`↔`[37] NWPERM` 对调 ⇒ 我方 R7/R8 + 方 C1/E1 红；② `[57] NONPTW`→`[58]` ⇒ 我方 R4/R6 + 方 A2/A8/A9/A13/C1–C3/E1 红；③ `[31:16]` 塞 `[24]` 位 ⇒ 我方 R1/R2/R5/R6 + 方 A1/A2/A5/A6/A9/A14/C1/C2 红；④ 契约 §6.1.1 `[32]` 行 wyde 列写反 ⇒ 我方 R9 + 方 C2 红；四路均「注入红 → 还原 md5 一致 → 双方回绿」，终态 `rc=0/0`。
**快照对账**：注入前后 `git status --porcelain -uall` 均空、DADAO-12/DADAO-13/contract-see/锁 4 文件 md5 与注入前快照逐一相等（`fc2b2341…`/`359d05fe…`/`7494c9da…`/`2336341b…`），无残留。
**越界**：`git diff --name-only 98d9426c..HEAD` = 6 文件（`spec/DADAO-12`、`spec/DADAO-13`、`.tao/contracts/contract-see.md`、`.tao/contracts/contract-cfx-aliases.md`、`manifests/spec-readonly.lock.toml`、本任务书）；`tests/`、`components/`、`tools/`、`.tao/archive/**`、`.tao/adr/**` **0 改动**；`contract-cfx-aliases` 36 行改动归一化行号后差异 0（仅来源行号）。
**硬约束**：两册与锁同笔重算 ✓；锁注记含用户三次裁定原话与第 2 轮授权原话 ✓；未提交 git ✓；注入还原只用 `cp`+md5 ✓；证据基线钉 `98d9426c` ✓；任务书无运行期路径 ✓。
**阻断 finding（唯一）**：证据脚本 `checks.py` **A10 恒真**——`32 % 8 == 0 and 48 % 8 == 0 and 56 % 8 == 0` 为常量运算、不读产物，任何注入都不可能使其 FAIL（违反「每条断言须有可达 FAIL 路径、禁恒真」），完成区「32 条断言」计数含此空断言。**修法**：A10 改为对现场解析的 18 行表现算段内位字节对齐（或删除该断言并把计数改为实数），重跑 `run.sh` 全绿 + ≥1 路注入回红回绿，完成区计数同步。
**非阻断 finding**：① 完成区「修改文件」漏列 `spec/DADAO-13-HEE-超管系统运行环境.md`（第 2 轮追加段已写明，architect 对账时补）；② `ADR-0056` D2/D3 仍为 17 位 `[32:16]` 旧图（无 wyde、无 `NONPTW`），与任务书「位图版本注记」不一致——位名 17/17 与 D3 逐字一致、`NONPTW` 为三次裁定新增，属任务书遗留②已登记事项，改 Accepted ADR 须用户逐条确认，非本任务可修。
**判决**：**Needs Revision**（仅因 A10 恒真断言；位图/零改动/三处 info/契约 18/18/锁/越界全部核验通过，证据见上）。返工仅需修 A10 + 同步计数，不改 spec/契约/锁正文。

### 第 3 轮 engineer（Needs Revision 修复，2026-11-16）

**范围**：只改证据脚本（`checks.py`/`run.sh`）与任务书；**spec/契约/锁正文零改动**（复核已通过）。

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| R1 `checks.py` 的 **A10 恒真**：`32 % 8 == 0 and 48 % 8 == 0 and 56 % 8 == 0` 是常量运算、不读产物 ⇒ 任何注入都无法 FAIL | ✅已修（改为产物派生） | A10 改为「**段边界声明 `[hi:lo]` == 实际占用位集合**」：从 §3.6（三）（四）首段解析「低字节 `[39:32]`/`[55:48]`」声明（`declared_byte_range`，仅取「低字节」起的那段，避开段标题的 wyde 编号），再与 18 行表的实际位集合逐位比对 | 默认 A10 PASS（`wyde2 声明 [32..39] = 实际 [32..39]；wyde3 声明 [48..55] = 实际 [48..55]`）；**注入 7**（把声明改成 `[39:33]`、表格位号不动）⇒ `合计 FAIL 1 项: ['A10 段边界声明 …']`、rc=1；`cp`+md5 还原后 rc=0 回绿 |
| R1b 完成区「32 条断言」计数需订正 | ✅已订正 | 测试结果行改为「A/B/C/D/E/F **32 条断言**（A16+B5+C3+D5+E1+F2）」——A10 是**替换**（非删除），故总数仍 32；`--self-inject` 由 5 路改 7 路 | `run.sh` 实测 `[PASS]` 计数 = **32**；`--self-inject` 7 注入 × (FAIL + 回绿) 全符合预期 |
| R1c 扫描其它「常量自比」断言 | ✅已扫、无残留 | `grep -n "% 8\|assert True\|len(…) == len(…)"` 现仅剩 A4（重名检测）与 C1（`len(smap)==len(cmap)==18`，两边是不同来源的解析结果）；其余断言均读产物或与基线 commit 比对 | 见下「扫描结论」 |

**扫描结论（`checks.py`）**：A1–A16/B1–B5/C1–C3/D1–D5/E1/F1–F2 全部读**产物**（spec/契约/锁文件/git 基线）或与**规范记录值**（用户裁定/ADR 的 18 位、11 项、18/18 等）比对；`A4`（名称去重）与 `C1`（`len` 相等）虽形如「自比」，但对象是**两处独立解析结果**（spec 表 vs 契约表；`rows` vs 去重集合），注入 1/2 与改契约均可令其 FAIL，**非恒真**。无 `assert True`、无「字面量取模」类断言残留。

### 第 2 轮 reviewer 验收（2026-11-16）

**重跑**：`run.sh` ⇒ `[PASS]` 计数 **32**、`[FAIL]` 0、`rc=0`（编号 A1–A16/B1–B5/C1–C3/D1–D5/E1/F1–F2，无重号，与完成区一致）；`--self-inject` ⇒ **7/7** 各「注入 FAIL → `cp`+md5 还原（md5 一致）→ 回绿」、`rc=0`（其注入 7 只红 A10，已复现）。
**A10 两向独立注入（我自设计，非它的 `[39:33]`）**：① 只改声明 `[39:32]`→`[40:32]`（表格不动）⇒ `checks.py check A` = **15 PASS / 仅 A10 FAIL**、A6/A7 绿，还原后 A 组 `rc=0`；全量 `run.sh` 另红 E1 —— 那是「锁 sha ↔ spec 现算哈希」的独立面（spec 变 ⇒ 锁必不符），不是 A10 的代偿。② 只改表格 `[36]`→`[41]`（声明不动）⇒ A2/A6/A9/**A10** + C1/C2/C3 + E1 红 ⇒ 两者覆盖**不同输入面**：A10 比「文档声明 ↔ 表格实际位集合」两处独立解析，A6 比「表格 ↔ 规范常量 WYDE2」——只改声明时 A6 必绿（①已证）、只改表时两者都红，**互不代偿**。
**恒真扫描**：`grep '% 8\|assert True\|assert False\|if False\|if True\|and True\|or False'` ⇒ **0 处**（旧 `32 % 8` 字面量取模已移除）；30 个 `record(` 调用点（D 组循环 2 次 ⇒ 运行时 32）逐条审 `ok` 表达式，全部读产物 / 基线 commit / 两处独立解析，无常量自比。
**三条形似自比的反例（各造一次，`cp`+md5 还原后均回绿）**：A4 —— `[33] NJPERM`→`NUPERM` ⇒ **A4 红**（连带 C1）；C1 —— 仅契约 `[33]` 名称→`NJPERMX`（spec 不动）⇒ **仅 C1 红**；E1 —— 锁 sha **末位**改 1 字符 ⇒ **E1 红**，且 `check-spec-readonly` 报 `MISMATCH … expected=d0b27146…d60`、`rc=1`，还原后 21 册 OK、`rc=0`。
**（补）B1 反例**：§5.2（二）`IALIGN` 位索引 13→14 ⇒ **仅 B1 红**，还原回绿 ⇒ B 组（低 16 位零改动）也具可达 FAIL。
**内容零改动**：`git diff 0bd7e225..HEAD -- spec/ .tao/contracts/ manifests/` = **0 行**；DADAO-12/DADAO-13/contract-see/锁 4 文件 md5 与第 1 轮快照逐一相等；本轮 diff 仅任务书（+19/−6）；`git status --porcelain -uall` 干净（全部注入已还原）。
**门控真数（逐一 `rc=0`）**：`check-spec-readonly` 21 册 OK / `check-spec-refs` PASS(0 violations) / `-purity` 22 册 / `-changelog` PASS / `check-rule-refs` PASS(18 规则) / `check-contracts-dir` PASS / `check-contract-relocs` PASS / `check-interface` PASS / `check-knowledge-refs` PASS(0 具体 `.work/**`) / `check-cfx-aliases` PASS(byte-identical)；L1 `make check` ⇒ `repository checks (L1): PASS`、`rc=0`（`check-patch-tree` 414 patches OK）。
**非阻断 finding**：① engineer 把我第 1 轮记录里证据脚本的**具体 `.work/…` 路径**改成占位形 `.work/evidence/<任务ID>/run.sh` —— 我原句确是可判定的具体 `.work/**` 引用、会被 `check-knowledge-refs`（扫描 `.tao/tasks/**`）判 FAIL，属合规修复，**我认**（该段仅此一行变动，其余逐字未动；我本轮也已按占位形书写）。② `ADR-0056` **D7 仍是二次改版位号**（「`[39:16]` 保留、`[47:40]` 权限类 8 位」），与同文 D3 及 spec `§3.6`（`[31:16]` 保留、权限类 `[39:32]`）矛盾 —— 遗留②「master 已是 wyde 新版」只对 D2/D3 成立；ADR 属主会话/用户（改 Accepted 须逐条确认），非本任务可修。
**判决**：**Accepted** —— A10 已改产物派生且两向注入可达 FAIL、32 条实数、恒真残留 0、内容零改动、10 项点名门控 + L1 全 `rc=0`；硬约束（不改正文、不提交 git、`cp`+md5 还原、基线钉 `98d9426c`）守住。

## 完成区

**测试结果**：证据脚本 `run.sh` ⇒ A/B/C/D/E/F **32 条断言全 PASS**（A1–A16 表完整性/两 wyde 归属/段边界声明/保留段、B1–B5 低 16 位与 §7.1 零改动、C1–C3 契约 18/18 + wyde 列一致、D1–D5 info 恒为地址 + 归属互斥 + handler 取值、E1 锁 sha、F1–F2 三处 `CFXPERM` info 一致）；`--self-inject` **7 路注入各「FAIL→还原→回绿」**（md5 对账一致，另验 `git diff` 非空防空注入）；点名门控 10 项全 rc=0（`check-spec-readonly` 21 册 OK / `-refs` 0 违规 / `-purity` 22 册 / `-changelog` / `check-rule-refs` / `check-contracts-dir` / `check-contract-relocs` / `check-interface` / `check-knowledge-refs` / `check-cfx-aliases`）。

**修改文件**：`spec/DADAO-12-SEE-主管系统运行环境.md`（§3.6 wyde 分层编码 + 两张子原因表 + 归属互斥 + handler 取值 + `cause_info`；§2.2.6 七步映射；§4.1–§4.6 注记；附录 0.7.3-rc 1 条）；`.tao/contracts/contract-see.md`（§6.1 加「子原因」列按 wyde、§6.1.1 位表加 wyde 列、§6.6 更正、附录 A §6 行、§7 变更记录）；`.tao/contracts/contract-cfx-aliases.md`（生成物重生成：仅 `DADAO-12:nnn` 来源行号）；`spec/DADAO-13-HEE-超管系统运行环境.md`（§2 hmon 表 `CFXPERM` 的 `info` → 「访存地址」+ 附录 `0.1.4-rc` 1 条）；`manifests/spec-readonly.lock.toml`（DADAO-12 sha256 + 三次裁定原话注记；DADAO-13 sha256 + 授权原话注记）。

**验收结果**：18 行逐位齐全、无重号缺号；**wyde2 恰 `[39:32]` 8 位、wyde3 低字节恰 `[55:48]` 8 位、高字节恰 `[56]`/`[57]`**、无跨 wyde、无越界位（`[31:16]`/`[47:40]`/`[58..63]` 均未占用，脚本现算并打印 18 行）；低 16 位：§5.2（二）编码表与基线**逐字相同**、§4.1 表 11 项 (位索引,名称) 与基线相同、`spec/Kaiwu` 整册**零改动**（§7.1 未动）；契约 §6.1.1 与 §3.6 表 **18/18 逐位一致**且 wyde 列 18/18 一致；`CFXMEM`/`CFXPERM` 两行均 info = 地址（无「或指令编码」）；DADAO-12 新 sha256 = `d0b27146a124a434920062900a3267fac642be2dfb6fbbab514033a8e78b1d65`；L1 除 `check-patch-tree` 外 **54/55 项 rc=0**（`check-patch-tree` 因并发任务写共享 Linux 源码构建树连红 3 次，属外来，见「新发现」③）。

**新发现/坑**：① `DADAO-12` 行号是 `.tao/contracts/contract-cfx-aliases.md` 的投影输入，改册后必须重跑 `tools/spec/gen_cfx_aliases.py`，否则 `check-cfx-aliases` 红（139 行来源列全变）；② 证据脚本解析契约表不能沿用 spec 表正则（契约单元格名称带反引号），且区段终点不能取 `---`（会命中表头分隔行）；③ `check-patch-tree` 读**共享**的组件源码构建树（非本任务 worktree 私有），有并发任务在写时必红（本轮先后撞 Linux 树的 `irqflags.h`/`time.c`/`traps.c`）——属外来，重试到并发收口即绿，不代改；④ 「无跨 wyde」判据必须按**表所属 wyde**判位号，不能只按位号反推 wyde（否则把 wyde2 行挪到 56 会漏判）——证据脚本 A5 按段解析，注入 5 可达 FAIL。

**第 2 轮追加（用户 2026-11-16 授权「`CFXPERM` 的 except_info 不应该有两种情况…应该就是地址」）**：本轮**越界改了第 2 册只读声明**——`spec/DADAO-13-HEE-超管系统运行环境.md` §2 hmon 表 `CFXPERM` 行 `info`：改前 `访存地址或指令编码` → 改后 `访存地址`；同册附录 `0.1.4-rc` 补 1 条（`CFXPERM` info 收敛为地址；为避免 `check-spec-changelog` 禁用项，附录内不写 ADR/任务号，授权出处只记在锁注记与本节）；`manifests/spec-readonly.lock.toml` 的 `DADAO-13` 条目 sha256 同笔重算 + 注记（引用户原话 + `ADR-0056` Accepted）。**DADAO-13 新 sha256 = `c06c94aff0aef80bc2f1d676e44a6100900eeb007028b33f22d6e7d1fef6402c`**（其余 20 册不变）。契约 `contract-see §6.1` 复查：`CFXPERM` 的 `info` 语义已是「地址」、`CFXMEM`/`CFXPERM` 两行均无「或指令编码」，**与 `DADAO-12 §3.6`/`DADAO-13 §2` 一致，未改契约**。证据脚本新增 F 组（`DADAO-12 §4.1` / `DADAO-13 §2` / `contract-see §6.1` 三处 `CFXPERM` 的 info 一致性，共 2 条断言，全 PASS，总 32 条）+ 注入 6（把该行改回「访存地址或指令编码」⇒ F1/F2 红，`cp`+md5 还原后回绿）。

**遗留问题**：① （已闭环，第 2 轮）`spec/DADAO-13 §2` hmon 表 `CFXPERM` 的 info 已收敛为「访存地址」，见「第 2 轮追加」；② （无待办）本 worktree 的 `ADR-0056` 副本是旧图，但 **master 上它已改为 wyde2/wyde3 新版并经用户确认**（worktree 基线早于该改版）⇒ 本任务不动 ADR，无需跟进；③ §4.7/§4.9 等 `cfx_*` 的 `CFXMEM` 行未逐行加注记（任务范围为 §4.1–§4.6），其子原因由 §3.6 总规则覆盖（非页表类 ⇒ `NONPTW`）。
