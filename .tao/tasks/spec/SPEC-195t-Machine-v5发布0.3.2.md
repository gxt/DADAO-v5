# SPEC-195t: Machine-v5 发布 0.4.0（版本与变更记录重排）

**模块**：spec
**项目里程碑**：M11
**依赖**：无
**状态**：待验收

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

**变更记录重排**：0.4.0 段由 27 条按时间罗列改为 **8 组按重要性排列**——① Tiny/Node 两 profile（几何、旧约定作废、BootROM 尺寸、Tiny 装载、cfx 实现范围）② 启动链与内存（power→hmon→smon、hmon/smon SRAM、Node 首张页表）③ 地址空间与页表（Step 1/2/3、`cfx4` 范围、异常路由、术语）④ 权限与异常（两轴模型、escape 偏移）⑤ 退出码（三段式、表位置）⑥ cfx 体系（编号、`cg7`、`cfx_pmem`/DMA、扩展指令清单）⑦ semihosting ⑧ 其它（legacy `-bios`、册名）。

**事实零缺失（自动化核验）**：对重排前后段落抽取「十六进制地址 / 反引号标识符 / 数字」集合比对 —— **missing: []、added: []**（88 个标识符完全一致）。

**修改文件**：`spec/Machine-v5-测试机运行环境.md`、`README.md`、`spec/README.md`、`manifests/spec-readonly.lock.toml`、本任务书、`milestones.md`。
