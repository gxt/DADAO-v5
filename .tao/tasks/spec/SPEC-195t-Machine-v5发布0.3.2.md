# SPEC-195t: Machine-v5 发布 0.3.2

**模块**：spec
**项目里程碑**：M11
**依赖**：无
**状态**：待验收

## 用户授权（原话）

> 「Machine-v5该升一下版本号了」

授权范围：发布 `spec/Machine-v5-测试机运行环境.md` 的累积 `-rc` 段（`0.3.2-rc` → `0.3.2`）并同步锁文件。

## 背景与事实

- 该册册头状态行为 `当前（0.3.2-rc，未发布；0.3.1 生效于 2026-10-16 …）`；文末附录顶部段为 `### 0.3.2-rc（未发布）`。
- 该 `-rc` 段自 2026-10-26 起累积了大量已落地内容：Tiny/Node 两 profile 几何、PTW/TLB 与 A/D 回写、页表异常路由、两轴权限模型、退出码三段式、`cg7` 内部空间描述、Node 首张页表口径等（逐条见附录）。
- 按 `spec/README.md`「册维护约定」的**发布动作**：把顶部 `-rc` 段去 `-rc` 并补发布日期；`-rc` 段只在确有未发布改动时新开（当前无新的未发布改动 ⇒ **不新开空 `-rc` 段**）。
- 该册属**只读册**（`manifests/spec-readonly.lock.toml` sha256 锁定）：改册须用户事先授权 + 同一变更内更新锁。

## 改动

1. `spec/Machine-v5-测试机运行环境.md`：
   - 册头状态行 `当前（0.3.2-rc，未发布；…）` → `当前（0.3.2，2026-11-08 发布；…）`；
   - 附录标题 `### 0.3.2-rc（未发布）` → `### 0.3.2（2026-11-08）`；段内条目**不动**。
2. `README.md`：版本表 `Machine` 行 `0.3.0 / 0.3.0` → `0.3.2 / 0.3.2`；正文 `Machine-01` → `Machine-v5`（册已于 2026-11-02 改名）。
3. `spec/README.md`：两处 `Machine-01` → `Machine-v5`（索引名同步，非版本内容）。
4. `manifests/spec-readonly.lock.toml`：Machine-v5 条目追加本次授权与动作注释，并**同笔重算** `sha256`（其余 20 册不变）。
5. `milestones.md`。

## 范围 / 非范围

**在范围内**：上列 5 个文件。

**不在范围**：正文语义、其它册、`contracts/`（其 `[Machine-01 §6]` 旧名引用不改）、任何 `.tao/contracts/contract-*.md` 的版本投影。

## 验收标准

1. `make check-spec-readonly` rc=0（锁与册一致，其余 20 册 sha256 不变）。
2. `make check-spec-changelog` rc=0：册头版本 == 附录顶部段版本 == `0.3.2`；无 `-rc` 段；逆序；无任务号/ADR 号。
3. `make check-spec-drift` rc=0（若该门控涉及 Machine）。
4. `spec/Machine-v5` 正文与附录条目**逐字未改**（仅版本行/标题两处）；给出 `git diff --stat` 与 diff 片段。
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
