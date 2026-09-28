# INFRA-015t: fetch.py 支持浅取（按 ADR-0006 浅 bare 预填充）

**模块**：infra
**项目里程碑**：M1→M2
**依赖**：无
**状态**：待开始

## 问题描述

ADR-0006 D2 决定 LLVM 源的获取方式为**浅 bare 预填充**：
```
git clone --bare --depth 1 --branch llvmorg-23.1.1   # 实测 43.7 s、376.53 MiB
```
但该浅取是 `INFRA-009t` 时的**一次性手工步骤**，**从未在 `tools/infra/fetch.py` 中实现**：

```python
# tools/infra/fetch.py:47-50
def sync_mirror(mirror, repository, commit):
    if not mirror.exists():
        run("git", "clone", "--mirror", repository, str(mirror))   # ← 全量
```

后果：`.cache/` 一旦为空（全新环境/被清），`fetch.py` 退回**全量 `--mirror`**（完整历史 + 全部 refs），
服务端对象枚举耗时数分钟、下载数 GB——与 ADR-0006 的浅取决策**不一致**。

（`.tao/knowledge/mirrors.md:27` 已承认该张力：「若流程需要完整历史（…或现有 `fetch.py` 的 `git clone --mirror` 语义），则不能浅下载」。）

## 目标

让 `fetch.py` 按 ADR-0006 支持**浅取**，使无缓存时可快速落地（分钟级），消除「决策（浅）与实现（全量）」的不一致。

## 修改内容

### tools/infra/fetch.py

1. **组件级浅取配置**：`manifests/components.lock.toml` 增加字段（如 `shallow = true` + `shallow_ref = "llvmorg-23.1.1"`），`fetch.py` 据此选择：
   - 浅取：`git clone --bare --depth 1 --branch <ref> <repo> <mirror>`
   - 默认（无该字段）：保持现有 `git clone --mirror` 行为
2. **增量刷新语义**：浅镜像上的 `git fetch --prune` 语义受限（ADR-0006 C5）——`fetch.py` 须处理：
   - 浅镜像已有 pinned commit → 跳过（现有 `has_commit` 逻辑需在浅镜像上可判定）
   - 需更新时：说明浅镜像限制（或 `--unshallow`），不得静默失败
3. **`mirrors.md` 同步**：更新「浅下载」节，说明 `fetch.py` 现已支持（按组件配置）

### manifests/components.lock.toml

**所有组件**（`llvm-project`、`qemu`、`gem5` 等，即 `components.lock.toml` 中全部条目）**均启用浅取**；**例外**：`manifests/references.lock.toml` 的**参考仓库**（`DADAO-0628`、`DADAO`）**不用浅取**（用户裁定 2026-09-28）。
- 浅取配置：每组件加 `shallow = true` + 对应 `shallow_ref`（tag/ref，如 llvm `llvmorg-23.1.1`、qemu `v11.1.1`——以其 ADR 为准）
- 无 `shallow_ref` 的组件（如 gem5 未定 tag）须按 commit 浅取（`--depth 1` + fetch 指定 commit）或由用户另行指明

## 约束

- **不得破坏现有全量行为**（未配置浅取的组件不受影响）
- **不得中断正在运行的 LLVM fetch**（若 `LLVM-019t` 正在进行，先与其隔离：测试用独立临时仓库/.cache 路径）
- 逐条核对，禁止正则批量替换
- 完成后 `make check` EXIT=0

## 验收标准

1. `fetch.py` 在组件配置浅取时执行 `--bare --depth 1 --branch <ref>`（可用小仓库或独立路径验证，贴真实命令与耗时）
2. 未配置浅取的组件行为不变（回归）
3. 浅镜像已含 pinned commit 时 `make fetch` 幂等（无网络）
4. ADR-0006 的浅取决策与实现一致（或在 ADR 就地注明修订）
5. `mirrors.md` 已同步
6. `make check` EXIT=0

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决；Needs Revision 返工后，下一轮标 `第 2 轮`）