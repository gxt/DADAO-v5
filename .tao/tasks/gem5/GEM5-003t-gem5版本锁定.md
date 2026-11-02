# GEM5-003t: gem5 版本锁定

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-001k`
**状态**：已验证

## 用户授权

用户 2026-11-01 确认：gem5 基线锁定 **v25.1.0.1**，commit `c8222cc67a399bfc01e8658dd14b30d5bfd634f9`；主下载地址 `https://github.com/gem5/gem5.git`。

## 目标

1. 在 `manifests/components.lock.toml` 填入：
   - `commit = "c8222cc67a399bfc01e8658dd14b30d5bfd634f9"`
   - `shallow_ref = "v25.1.0.1"`
   - `role = "functional second reference: FS + SE (AtomicSimpleCPU)"`
2. **保持 `enabled = false`**：当前 `components/gem5` 补丁集/骨架尚未建立，启用会让 `fetch/apply-series/check-components` 在空组件上产生噪声；G1 建骨架后再单独启用。
3. 核验 GitHub API：tag 直接指向该 commit（轻量 tag）；记录 tarball 只作校验物、不作组件源。

## 文件范围

- `manifests/components.lock.toml`
- 本任务书、`.tao/knowledge/milestones.md`

## 验收

1. manifest 字段与上述一致，`enabled=false`。
2. `python3 tools/infra/manifest_check.py` rc=0。
3. `git diff` 仅本任务范围；不改 `components/gem5`/`tests`/`Makefile`。
4. 完成区 ≤30 行，状态 `待验收`。

## 完成区

**测试结果**：`manifest_check.py` rc=0；GitHub API 已核 tag `v25.1.0.1` 直接指向 commit `c8222cc6…`。
**修改文件**：`manifests/components.lock.toml`；本任务书；`.tao/knowledge/milestones.md`。
**验收结果**：commit/shallow_ref/role 已写入，`enabled=false`；未改 components/tests/Makefile。
**新发现/坑**：先在 G1 建 `components/gem5` 骨架/补丁集后再启用，避免空组件门控噪声。
**遗留问题**：G1 启用组件并补 `components/gem5`。

## 审阅记录

#### 第 1 轮 architect 提交与文件集审核
档位：正常提交（状态 `已验证`）。对账：显式 staging 3 项 = 完成区「修改文件」(`manifests/components.lock.toml`、本任务书、`.tao/knowledge/milestones.md`)，无多提 / 漏提 / 越界；`manifest_check.py` rc=0（PASS）。提交落分支 `GEM5-003t`，见 `git log GEM5-003t`；未 push。
