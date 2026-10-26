# INFRA-110t: semihosting 旧口径文档清理（ISS-337）

**模块**：infra
**项目里程碑**：M10
**依赖**：ADR-0038 / SPEC-176t
**状态**：待开始

## 背景
semihosting 判定已迁至 `0x3FF00–0x3FFFF`（`ADR-0038`），但以下文档仍是旧口径 `immu18[17:16]==2'b11` / `0x30000`：
- `README.md:60`（M5 历史段）；
- `docs/DDLN/D-运行平台/DD-D002`、`TT-D002`（现行/教学口径，含 §8「为什么用 tag」）；
- `docs/Machine-00-执行环境分层-Draft.md:12`；
- `.tao/knowledge/audits/cfx-audit-2026-10-26.md`（审计快照）。

## 改动
1. `README.md` M5 历史段：**不改写历史**，在句末加注「（M10 已迁 `0x3FF00–0x3FFFF`，见 `ADR-0038`）」。
2. `docs/DDLN/D-运行平台/DD-D002` 与 `TT-D002`：判定改为 `immu18[17:8] == 0x3FF`（`0x3FF00–0x3FFFF`）；一般 trap 为 `< 0x3FF00`；示例 `0x30000` → `0x3FF00`；§8 的「为什么用 tag」按新范围改写（保留历史动机说明，不删对比内容）。
3. `docs/Machine-00-执行环境分层-Draft.md:12`：同判定更新；Draft 仍标 Draft。
4. `audits/cfx-audit-2026-10-26.md`：**不改快照正文**，在文件头加一行「审计时 semihosting 为旧 tag；M10 已迁 `0x3FF00–0x3FFFF`（ADR-0038）」。
5. `issues.yaml`：ISS-337 `closed`，`resolved_by: INFRA-110t`。

## 验收
- `make check` rc=0。
- grep：`README.md`/`docs/Machine-00*`/`docs/DDLN` 中**现行口径**的 `2'b11`/`0x30000` = 0（历史注记/对比说明允许保留，须明确标「历史」）。
- 快照正文未改（仅头注）。

## 约束
- 只改上述 4 份文档 + `issues.yaml` + 任务书/`milestones.md`；不改 spec 正文/ADR/contracts。
- 临时目录 `/tmp/opencode/INFRA-110t/`；不提交。

## 完成区

**状态**：待开始

### 修改文件
（待填）

### 验收命令与结果
（待填）

### 遗留
（待填）
