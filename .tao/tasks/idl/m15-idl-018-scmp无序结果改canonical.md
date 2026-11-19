# m15-idl-018: `scmp` 无序结果改 canonical quiet NaN（spec 已改）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-007`（`SimRISC-07` 50 条已合入）；spec 修改已由主会话落盘（`a6f11e23`）
**可并行分片**：否（改 `idl/SimRISC-07.idl`）
**预估**：1–2 h
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-19 授权，版本号不变）

`spec/SimRISC-07 §4` 原写「Signaling Compare 的无序结果为 **sNaN**」，违反 IEEE 754-2019 §6.2.1 的 `shall`（一般计算类操作收到 signaling NaN 必须返回 **quiet** NaN）。已改为：

> NaN：unordered，**四种比较一律返回 canonical quiet NaN**（符号位 0、payload 全零）；quiet 与 signaling 的差别只体现在 `NV` 标志。

`SimRISC-00` 的「NaN 结果统一为 canonical」例外清单也删掉了 `signaling compare` 一项。

## 要做

1. `idl/SimRISC-07.idl` 的 `ftscmp_orrr_rf`/`foscmp_orrr_rf`：无序分支由 `snanBits(...)` 改为**canonical quiet NaN**（库里有 `DP_CANONICAL_NAN` 与 ft 侧 canonical 常量，直接复用）；
2. 重渲染 `spec/SimRISC-07` 的对应块；`spec/.manifests.toml` 本册 sha256 重算；
3. 更新 `m15-idl-007` 的 oracle/证据脚本中依赖旧语义的期望（若有），或在 `m15-idl-018` 自带 oracle 覆盖：
   - `qcmp`/`scmp` × {有序、qNaN、sNaN、双 NaN} 四类 × `ft`/`fo`，**≥200 例**，断言无序结果一律 canonical、`NV` 置位规则不变；
4. **可达 FAIL**：把 `scmp` 的无序结果改回 `snanBits` ⇒ 新增用例红（`cp`+md5 还原）。

## 验收

`idlc` 两段式（本册 50 条复跑）rc=0；`render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` rc=0；散文零改动（基线锚固定 commit，**禁 `HEAD`**——`Process-07 §5b`）。

## 完成区

（待填）
