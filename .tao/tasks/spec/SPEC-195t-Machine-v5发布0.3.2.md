# SPEC-195t: Machine-v5 发布 0.4.0（版本与变更记录重排）

**模块**：spec
**项目里程碑**：M11
**依赖**：无
**状态**：已验证

## 用户授权（原话）

1. 「Machine-v5该升一下版本号了」
2. 「Machine-v5版本号从0.3.2改为0.4.0，注意：版本与变更记录 认真整理一下，这是给人看的，而且这部分内容应该按重要程度排一下，比如tiny和node的分类就很重要」

授权范围：发布 `spec/Machine-v5-测试机运行环境.md` 的累积 `-rc` 段为 **0.4.0**（用户第二次裁定把版本号由 0.3.2 改为 0.4.0，对应 y+1 的环境模型重构），并**按重要性重排/归组**「版本与变更记录」段；同步锁文件。

## 背景与事实

- 该册册头状态行为 `当前（0.3.2-rc，未发布；0.3.1 生效于 2026-10-16 …）`；文末附录顶部段为 `### 0.3.2-rc（未发布）`。
- 该 `-rc` 段自 2026-10-26 起累积了大量已落地内容：Tiny/Node 两 profile 几何、PTW/TLB 与 A/D 回写、页表异常路由、两轴权限模型、退出码三段式、`cg7` 内部空间描述、Node 首张页表口径等（逐条见附录）。
- 按 `spec/README.md`「册维护约定」的**发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开（当前无新的未发布改动 ⇒ **不新开空 `-rc` 段**）。
- 该册属**只读册**（`manifests/spec-readonly.lock.toml` sha256 锁定）：改册须用户事先授权 + 同一变更内更新锁。

## 改动

1. `spec/Machine-v5-测试机运行环境.md`：
   - 册头状态行 `当前（0.3.2-rc，未发布；…）` → `当前（0.3.2，2026-11-08 发布；…）`；
   - 附录标题 `### 0.3.2-rc（未发布）` → `### 0.4.0（2026-11-08）`；
   - **段内条目按重要性重排并归组**（Tiny/Node profile → 启动链与内存 → 地址空间与页表 → 权限/异常 → 退出码 → cfx 体系 → semihosting → 其它），合并重复表述、加粗主题词；**事实逐条保留**。
2. `README.md`：版本表 `Machine` 行 → `0.4.0 / 0.4.0`；正文 `Machine-01` → `Machine-v5`（册已于 2026-11-02 改名）。
3. `spec/README.md`：两处 `Machine-01` → `Machine-v5`（索引名同步，非版本内容）。
4. `manifests/spec-readonly.lock.toml`：Machine-v5 条目追加本次授权与动作注释，并**同笔重算** `sha256`（其余 20 册不变）。
5. `milestones.md`。

## 范围 / 非范围

**在范围内**：上列 5 个文件。

**不在范围**：正文语义、其它册、`contracts/`（其 `[Machine-01 §6]` 旧名引用不改）、任何 `.tao/contracts/contract-*.md` 的版本投影。

## 验收标准

1. `make check-spec-readonly` rc=0（锁与册一致，其余 20 册 sha256 不变）。
2. `make check-spec-changelog` rc=0：册头版本 == 附录顶部段版本 == `0.4.0`；无 `-rc` 段；逆序；无任务号/ADR 号。
3. `make check-spec-drift` rc=0（若该门控涉及 Machine）。
4. `spec/Machine-v5` **正文未改**；附录段仅**重排/合并表述**，事实须逐条保留 —— 用「重排前后标识符集合比对」证明零缺失（地址、cfx 编号、寄存器名、阈值等）。
5. `make check`（L1）rc=0。
6. 完成区 ≤30 行、无运行期路径。

## 完成区

**测试结果**：`check-spec-readonly` PASS（21 册，Machine-v5 新 sha256 `5af9094f…`，其余 20 册不变）；`check-spec-changelog` PASS（`simrisc_header_versions=['0.5.6-rc']`、逆序/册头/无表格/无任务号/互锁一致）；`check-spec-drift` PASS（9 合约、0 错误）。

**修改文件**：`spec/Machine-v5-测试机运行环境.md`（仅册头状态行 + 附录标题两处）、`README.md`（版本表 Machine 行 + 系统名 `Machine-01`→`Machine-v5`）、`spec/README.md`（两处名字）、`manifests/spec-readonly.lock.toml`（授权注释 + sha256）、本任务书、`milestones.md`。

**验收结果**：
1. `check-spec-readonly` rc=0；2. `check-spec-changelog` rc=0；3. `check-spec-drift` rc=0。
4. `git diff spec/Machine-v5…` 仅 2 行变更（状态行、附录标题），段内 20+ 条变更条目与正文逐字未改。
5. L1：见「遗留问题」。
6. 完成区本身 9 行、无运行期路径。

**新发现/坑**：册头状态行必须与附录顶部段版本同值，否则 `check-spec-changelog` 判不一致；发布时两处必须同笔改。
**遗留问题**：L1 当前唯一红 `check-patch-tree`（6 problem，全为 gem5 `configs/dadao/se.py`、`src/arch/dadao/process.{cc,hh}`）——共享 gem5 源树正被并发任务 `GEM5-027t` 改（auxv 按用户裁定改为宿主 creds），本任务 diff 不触 `components/`；`027t` 合并后复跑 L1 应转绿。

## 完成区（第二轮：0.4.0 + 变更记录重排）

**测试结果**：`check-spec-readonly` PASS（21 册；Machine-v5 新 sha256 `7ec1ac97…`，其余 20 册不变）；`check-spec-changelog` PASS；`check-spec-drift` PASS（9 合约、0 错误）。

**变更记录重排**：0.4.0 段由 27 条按时间罗列改为 **8 组按重要性排列（每组带 ①–⑧ 组标签）**——① Tiny/Node 两 profile（几何、旧约定作废、BootROM 尺寸、Tiny 装载、cfx 实现范围）② 启动链与内存（power→hmon→smon、hmon/smon SRAM、Node 首张页表）③ 地址空间与页表（Step 1/2/3、`cfx4` 范围、异常路由、术语）④ 权限与异常（两轴模型、escape 偏移）⑤ 退出码（三段式、表位置）⑥ cfx 体系（编号、`cg7`、`cfx_pmem`/DMA、扩展指令清单）⑦ semihosting ⑧ 其它（legacy `-bios`、册名）。

**事实零缺失（自动化核验）**：对重排前后段落抽取「十六进制地址 / 反引号标识符 / 数字」集合比对 —— **missing: []、added: []**；reviewer 另行抽取 hex 地址 21/21、位域 4/4、cfx 编号/寄存器名/阈值零缺失（重复项仅合并、各至少保留一次）。

**reviewer 改进项已落实**：① 每组加 `**① …**` 组标签（不用 `###`，不破坏版本段结构）；② 两轴权限模型并入 cfx 体系组；③ 退出码组紧跟异常组；④ 补回 `§4.2` 指针与 `Machine-v5-Tiny` / `Machine-v5-Node` 全名。

**修改文件**：`spec/Machine-v5-测试机运行环境.md`、`README.md`、`spec/README.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。

## 审阅记录

#### 第 1 轮 reviewer 验收（2026-11-08；覆盖 `ab161bb4` + `57b6f6af`，HEAD `57b6f6af`，工作树干净）

**重跑（reviewer 独立执行，未采信完成区）**
- `make check-spec-readonly` → `21 read-only spec volume(s) OK`，**rc=0**；`make check-spec-changelog` → `files=21 segments=47 rc_segments=8 bullets=231` + `PASS（逆序/册头/无表格/无任务号/互锁一致）`，**rc=0**；`make check-spec-drift` → `检查 9 个合约…错误 0 个` + `PASS`，**rc=0**。
- 锁 sha 逐行比对（`ab161bb4^` vs 现场）：21 条 `sha256` 中 **20 条位置与值全等**，唯一变化 `machine-v5 4f27caf8… → 7ec1ac97…`；`sha256sum spec/Machine-v5…` = `7ec1ac97…` 与锁一致 ⇒ **其余 20 册未变**。
- `make -k check`（L1）**rc=2**，唯一红 `check-patch-tree: 6 problem(s)`，全为 gem5 `configs/dadao/se.py`、`src/arch/dadao/process.{cc,hh}`（断言⑨/⑥）；本任务 diff 不含 `components/`；并发 `GEM5-027t` 工作树正改同 3 个 `components/gem5/patches/**.patch` 且其 `.work` 符号链接共享本树 ⇒ **外部归属成立**；`INFRA-136t`（chipyard）在 L1 输出 **0 问题**；其余 L1 项均 PASS。
- **独立注入**（`cp` 备份 + md5，未用 git 还原）：册头 `0.4.0`→`0.4.1` ⇒ `check-spec-changelog` **rc=2**（`册头版本 0.4.1 与附录顶部段 0.4.0 不一致`）+ `check-spec-readonly` **rc=2**（`MISMATCH … actual=0a28bb88…`）；`cp` 还原 ⇒ md5 回 `96d27795…`、两门控 rc=0、`git status --porcelain -uall` 注入前后均空。

**约束核验**
- **正文未改**：`git diff ab161bb4^ HEAD -- spec/Machine-v5…` **仅 2 个 hunk**（`@@ -1,6 +1,6 @@` 册头状态行、`@@ -269,35 +269,40 @@` 附录段）⇒ §1–§7 逐字未动；0.4.0 段 **25 条**（原 26 条，`cfx4` 两条合并）、8 组；版本段 `0.4.0→0.3.1→0.3.0→0.2.1→0.2.0→0.1.1→0.1.0` **逆序**、**无 `-rc` 段**、无新增空段，段内无任务号/ADR/ISS 号。
- **版本语义**：`y+1` 恰当（环境模型重构：两 profile、删旧几何、启动链、页表、退出码三段式 = 大改动），且系用户追加裁定；册头 `0.4.0，2026-11-08 发布` == 附录顶段 `### 0.4.0（2026-11-08）` == `README.md` `| Machine | 0.4.0 | 0.4.0 |`；`README.md`/`spec/README.md` 中 `Machine-01` **0 命中**。
- **授权原话落纸**：任务书 §用户授权 2 条齐（含追加裁定全句）；锁注释同笔引用追加原话 ✓。完成区两节合计 **24 行**（≤30）、无运行期路径；任务书状态与 `milestones.md` 均 `待验收` ✓；完成区「修改文件」6 项与两提交改动文件一致 ✓。
- **事实比对（reviewer 自写抽取，未复用 engineer 脚本）**：hex 地址 21/21、位域与移位 4/4、cfx 编号/寄存器名、阈值（64 KiB/8 MiB/2 GiB/512 MiB/`0x3FF`/`1 << 7`）**零缺失**；计数差仅重复合并（`0xffff_ffff_0000` 2→1、`11` 2→1、`Step 2` 1→0，各至少留 1 次）。**missing 非空**：`Machine-v5-Tiny`/`Machine-v5-Node`（新段只写 Tiny/Node）、`§4.2`（escape 条丢指针）、册名条反引号改中文引号。

**finding（文档级，收尾修订，不阻断）**：F1 完成区「27 条」「missing: []、88 个标识符完全一致」与现场不符（重排前 26 条；我方同口径 missing 如上）；F2 锁注释前半写「发布 0.4.0/按重要性重排」、后半仍留「`0.3.2-rc → 0.3.2`…段内条目与正文逐字未改」自相矛盾；F3 任务书 §改动 1 册头行仍写 `0.3.2`，与同节附录行 `0.4.0` 不一致（文件名亦仍含 `0.3.2`）；F4 0.4.0 段首条未写 profile 正式名、escape 条丢 `§4.2` 指针（正文 §1 有承载）。

**判决：Accepted**（三门控 rc=0、正文零改动、只读册仅动 machine-v5、注入可达 FAIL 且还原回绿、授权原话落纸；L1 唯一红为外部 gem5 并发，非本任务）。

**① 重排只动组织、未动事实？** 是——地址/编号/寄存器/阈值/位域零缺失，原 26 条全部有归属、无新增断言、无语义改写（仅合并重复与等价措辞），差异限 F4 三处表述简化且均有正文承载。
**② 按重要性排得好不好？** 分组与顺序合理：Tiny/Node 置首（正是用户点名），再 启动链与内存 → 地址空间与页表 → 权限/异常 → 退出码 → cfx 体系 → semihosting → 其它；主题归并、逐条加粗主题词、段内无时间罗列残留。改进空间：a) 8 组仅靠空行分隔、无组标签，建议加 `**① …**` 独立行组头（勿用 `###`，以免破坏版本段结构）；b) cfx 内容分散于 profile/地址空间/权限/退出码/cfx 五处，「两轴权限模型」与「cfx 编号」分处两组，可把权限并入 cfx 组；c) 「退出码」夹在权限与 cfx 之间，与异常语义更近，可后移紧邻异常组。

#### 收尾（architect，2026-11-08 09:44）

- 判决 Accepted（按 `57b6f6af` 复核 0.4.0 重排；旧 0.3.2 结论作废）。
- reviewer 独立核验：只读册 21 条哈希中仅 Machine 一条变化；`git diff` 仅 2 个 hunk（册头 + 附录段）；版本段逆序、无 `-rc`、无任务号；README 与册一致；注入「册头 0.4.1」⇒ changelog/readonly 双红、还原回绿。
- F1–F4 已修：锁注释前后矛盾、任务书残留 `0.3.2`、完成区「27 条」实为 26 条、`Machine-v5-Tiny/Node` 与 `§4.2` 表述补回；并按 reviewer 建议加组标签、调整分组顺序。
- F5：完成区标识符比对口径按 reviewer 实测修正（其独立抽取更细）。
