# INFRA-109t: 归档门控移到里程碑收尾（`check-spec-archive` + `--verify`）

**模块**：infra
**项目里程碑**：M10
**依赖**：INFRA-107t（`--verify` 已能跳过 `-rc`）
**状态**：待开始

## 执行环境
**执行环境**：本地（纯 Makefile/文档，无构建）

## 接口规范

### 背景（用户 2026-10-25 裁定）
- 归档是**只读历史快照**，只在发布/里程碑边界变化；用户要求：**结构与 sha 校验都只在里程碑收尾做一次**，不进每任务 L1。
- 现状：`check-spec-archive`（结构）在 L1 `_locked-check`；`gen_spec_archive.py --verify`（内容 sha）未接线、靠手动。

### 输出
1. `Makefile`：
   - 从 L1 `_locked-check` **移除** `check-spec-archive`；
   - 新增 `check-spec-archive-verify`：`$(PYTHON) tools/spec/gen_spec_archive.py --verify`；
   - `check-milestone` 依赖/步骤加入 `check-spec-archive` 与 `check-spec-archive-verify`；
   - help / phony 同步（标注「里程碑收尾」）。
2. `docs/Process-07-门控分层规范.md`：门控表把 `check-spec-archive` 从 L1 行移到「里程碑收尾」行，登记 `--verify`。
3. 不改 `check-milestones-fresh` 的 archive 回退（任务号解析，非归档校验）。

### 约束
- 不改变 `check-spec-archive` / `--verify` 的判据本身（只改触发层）。
- 不引入新依赖。

## 验收标准
1. `make check`（L1）不再包含 `check-spec-archive`（`make -n` 不含该目标），且 rc=0。
2. `make check-milestone` 实际跑 `check-spec-archive` 与 `--verify`，rc=0（贴输出）。
3. `docs/Process-07` 与 Makefile 实际分层一致（贴对照）。
4. 反例注入（临时让 `--verify` 红）⇒ `check-milestone` 红 ⇒ 还原 ⇒ 绿。
5. 完成区贴真实输出与退出码。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
#### 第 1 轮 reviewer 验收
