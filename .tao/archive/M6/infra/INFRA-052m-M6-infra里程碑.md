# INFRA-052m: M6 infra 里程碑

**模块**：infra
**项目里程碑**：M6
**状态**：里程碑
**目标**：LLVM/Host 工具**一次构建 + 双落点**（`LLVM_TARGETS_TO_BUILD="DADAO;X86"` 产出 `clang`/`llc`/`ld.lld`/`lli`；交叉工具链 → `.dadao/cross-toolchain/bin/`；host `lli` → `.dadao/host-tools/bin/`〔可选〕）就位；**Embench 组件接入**（`manifests/components.lock.toml` 翻 `enabled=true` + `components/embench-iot/{patches/**,series,changelog.md}` + `make fetch` 落 `.work/source/embench-iot`）；`make check`/`make check-patch-tree` 绿。
**关联任务**：`INFRA-050t`、`INFRA-051t`

## 核验
- 关联任务是否均已 `已验证`
- 产出是否存在：`.dadao/cross-toolchain/bin/{clang,llc,ld.lld}`；`.dadao/host-tools/bin/lli`（若采纳可选落点）；`components/embench-iot/{patches/**,series,changelog.md}`；`manifests/components.lock.toml` 的 Embench 条目 `enabled=true`
- 一次构建目标（由 `INFRA-050t` 定名）EXIT=0 且产出四工具；`make fetch` 落 `.work/source/embench-iot`
- 不回归：`make check`/`make check-patch-tree` EXIT=0
（核验通过后，主会话将 `**状态**` 置为 `里程碑`）

## 完成区（核验结论，2026-10-11）
- **关联任务**：`INFRA-050t` → `已验证`；`INFRA-051t` → `已验证`（读各自任务书 `**状态**`）✔
- **产出存在**：
  - `.dadao/cross-toolchain/bin/{clang,llc,ld.lld}` 存在；`--version` → `clang version 23.1.1 (… 47eb2396…)` / `LLD 23.1.1 (…47eb2396…)` / `llc` LLVM ✔
  - `.dadao/host-tools/bin/lli` 存在；`--version` LLVM ✔（`.dadao/` 为 gitignore 构建产物，不入库）
  - `components/embench-iot/{patches/**,series,changelog.md}` 存在：4 补丁（examples/dadao ×3 + src/md5sum/md5.c ×1），series 4 行，changelog.md ✔
  - `manifests/components.lock.toml` embench 条目 `enabled = true`（commit `09c2ed8c…`，role IoT benchmark suite）✔
  - `.work/source/embench-iot` 存在（`make fetch` 落点）✔
- **门控**：`make check` **EXIT=0**（lit 89/89 PASS；`check_issues: 24 open, 18 closed (0 blocking)`；`repository checks: PASS`）；`make check-patch-tree` **EXIT=0**（3 组件、109 补丁 OK）✔
- **证据指针**：`.work/log/infra/INFRA-052m-make-check.log`（md5 `9cdfd49c…`）、`.work/log/infra/INFRA-052m-check-patch-tree.log`（md5 `ecfceb29…`）
- **结论**：四条核验项全部通过 ⇒ 置 `**状态**` = `里程碑`。

## 审阅记录

#### 第 1 轮 reviewer 验收
（审查者独立验证：关联任务状态、产出存在性、构建/门控重跑、判决）
