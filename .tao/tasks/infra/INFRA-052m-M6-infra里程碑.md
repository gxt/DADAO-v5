# INFRA-052m: M6 infra 里程碑

**模块**：infra
**项目里程碑**：M6
**状态**：待开始
**目标**：LLVM/Host 工具**一次构建 + 双落点**（`LLVM_TARGETS_TO_BUILD="DADAO;X86"` 产出 `clang`/`llc`/`ld.lld`/`lli`；交叉工具链 → `.dadao/cross-toolchain/bin/`；host `lli` → `.dadao/host-tools/bin/`〔可选〕）就位；**Embench 组件接入**（`manifests/components.lock.toml` 翻 `enabled=true` + `components/embench-iot/{patches/**,series,changelog.md}` + `make fetch` 落 `.work/source/embench-iot`）；`make check`/`make check-patch-tree` 绿。
**关联任务**：`INFRA-050t`、`INFRA-051t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.dadao/cross-toolchain/bin/{clang,llc,ld.lld}`；`.dadao/host-tools/bin/lli`（若采纳可选落点）；`components/embench-iot/{patches/**,series,changelog.md}`；`manifests/components.lock.toml` 的 Embench 条目 `enabled=true`
- 一次构建目标（由 `INFRA-050t` 定名）EXIT=0 且产出四工具；`make fetch` 落 `.work/source/embench-iot`
- 不回归：`make check`/`make check-patch-tree` EXIT=0
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、产出存在性、构建/门控重跑、判决）
