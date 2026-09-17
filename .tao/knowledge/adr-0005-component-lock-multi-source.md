# ADR-0005: 组件锁多源

**状态**：Accepted
**日期**：2026-09-17
**关联**：`INFRA-009t`、ADR-0002（`.tao/knowledge/adr-0002-build-orchestration.md`）

## Context（背景）

v5 的组件锁（`manifests/components.lock.toml`）当前只有单个 `repository` 字段记录上游 Git URL。在特定网络环境下（如本机 `github.com:443` 不可达），需要使用教育网镜像（如 SJTU `https://mirror.sjtu.edu.cn/git/llvm-project.git`）获取源码。组件锁应支持记录多个可用源，而非硬编码单一 URL 或在工具层做隐式 URL 重写（后者被 ADR-0002 D6 否决）。

真实背景：本机 `github.com:443` 不可达；已用教育网镜像 SJTU 落地浅 bare 镜像到 `.cache/llvm.git`（376.53 MiB / 189,410 objects）。`llvmorg-23.1.1` 的 commit = `6dfe1677ab8dffbc6ec13d53a1e0215d75147689`。

## Decision（决策）

### D1：schema 形状

保留 `manifests/components.lock.toml` 现有 `repository` 字段（= 规范上游身份，必填，语义不变），**新增有序数组** `[[component.source]]`，每项含 `name`（字符串，组件内唯一）+ `url`（Git URL）。identity（`repository`）与获取途径（`source`）分离。`source` 为可选字段；若不存在，`fetch.py` 回退到 `repository`。

TOML 示例：
```toml
[[component]]
name = "llvm"
repository = "https://github.com/llvm/llvm-project.git"
# ... 其他字段不变

[[component.source]]
name = "sjtu"
url = "https://mirror.sjtu.edu.cn/git/llvm-project.git"
```

### D2：选源规则

`fetch.py` 的有效源序列 = `source` 列表（按序）；默认取**第一个**。若该组件**无 `source`** 则用 `repository`。环境变量 `COMPONENT_SOURCE_<组件名大写>`（如 `COMPONENT_SOURCE_LLVM`）按 `name` 显式指定源，保留名 `canonical` 表示 `repository`。**实际使用的源必须打印**。**失败即停，不自动换源/不重试**。

## Rationale（理由）

### 为什么用 `source` 数组而非写死单一镜像字段

**被否决方案 A：写死 `repository_sjtu` 单镜像字段**。在 `component` 中直接加 `repository_sjtu = "https://mirror.sjtu.edu.cn/..."` 字段。缺点：每新增一个镜像就需改 schema，字段名与具体镜像耦合，无法复用到其它组件。

**被否决方案 B：`repository_github` + `repository_sjtu` 两固定字段**。固定两个字段。缺点：同上，扩展性差，且语义不清（哪个是身份？哪个是获取途径？）。

**被否决方案 C：源列表放独立文件**。把源信息放到 `manifests/sources.toml` 等独立文件。缺点：增加文件数量，源信息与组件锁分离，维护不便；获取组件时需同时读两个文件。

**采纳方案**：`[[component.source]]` 有序数组，每项 `name`+`url`。扩展只需追加条目，不改 schema；`name` 支持环境变量按名选择；与组件锁同文件，维护简便。

### 为什么默认取第一个而非按序自动回退

**被否决方案：按序自动回退**。fetch 失败时自动尝试下一个源。缺点：可能掩盖网络问题，在 CI 环境中导致不确定行为；回退顺序对用户不透明；与 ADR-0002「失败即停」原则矛盾。

**采纳方案**：默认取第一个；失败即停。显式优于隐式——用户通过环境变量或调整 `source` 顺序控制行为，而非依赖隐式回退。

### 为什么用 `canonical` 保留名

环境变量 `COMPONENT_SOURCE_LLVM=canonical` 表示使用 `repository` 字段。这避免了在环境变量中写完整 URL，且 `canonical` 语义明确（规范上游）。`canonical` 是固定保留名，不出现在 `source` 列表中。

## Consequences（影响）

1. `manifest_check.py` 新增校验：`repository` 非空；`source` 若存在则每项 `name` 非空且唯一、`url` 非空。
2. `fetch.py` 的 `sync_mirror` 接收解析后的源 URL（而非固定 `repository`），但 mirror 目录仍按组件名索引（`.cache/<name>.git`）。
3. qemu/gem5 暂不添加 `source`（其上游基线 ADR 未定），待各自基线任务确定后补。
4. 未来新增镜像源只需在 `source` 列表追加条目，不改 schema。
5. 与 ADR-0002 的关系：D1（identity 与获取途径分离）扩展了 ADR-0002 的组件锁 schema；D2（失败即停）保持与 ADR-0002 一致的失败处理原则。

## 状态说明

- **Accepted**（2026-09-17）：D1、D2 经用户逐条确认后固化。
- **确认记录**：D1（schema 形状：`repository` + 有序 `[[component.source]]`）、D2（选源规则：默认取 `source` 首个、无 `source` 回退 `repository`、env 按 `name` 覆盖、保留名 `canonical`、实际源必须打印、失败即停不自动换源）均由用户判定为「保留」。
- 决策变更时新增 ADR 或标注 `Superseded`，不直接改写已 `Accepted` 的决策。
