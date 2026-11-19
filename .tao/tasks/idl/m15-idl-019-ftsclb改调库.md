# m15-idl-019: `ftsclb` 改调库函数 `ft_scale`（先验等价）

**模块**：idl
**项目里程碑**：M15
**依赖**：`m15-idl-007`（`SimRISC-07` 50 条）合入；`m15-idl-017`（库补 `ft_scale`）已合入
**可并行分片**：否（改 `idl/SimRISC-07.idl`）
**预估**：1 h
**档位**：小改
**状态**：待开始

## 背景（用户 2026-11-19 裁定）

「**有库自然用库，用之前确定是一致的**」。

`ftsclb_orrr_rf` 目前用批 2 的**临时写法**：把 `rdHD` 的指数加到输入指数上，再交 `softfloat_normRoundPackToF32`。而库已有 `ft_scale`（`fo_scale` 的 f32 同构、指数饱和 ±4096、与 `SimRISC-07 §2.1` 口径一致）。

## 要做

1. **先验等价**：对 `ftsclb` 现有临时写法与 `ft_scale` 做**逐例对比**（输入覆盖 `±0/±Inf/qNaN/sNaN/次正规/最大有限/` 指数 ±4096 边界与越界、以及 `rdHD` 指数为 0/±1/±4096 等）；**先证明两者结果与标志完全一致**，再改；
2. 一致 ⇒ 把 `ftsclb` 的 body 改为一次 `ft_scale` 调用（保留原有合法性判定与 `rdHD` 取指口径）；
3. **不一致 ⇒ 停下登记「待裁定」**（写明哪类输入、差在哪、哪一侧符合 `SimRISC-07 §2.1`），**不得**为了换库而改语义。

## 验收

1. 等价性对比脚本输出（例数、失配数 = 0，或给出差异清单）；
2. 改后 `render.py --check`、`check-idl-sync`、`check-manifests-guard`、`check-fp-contract` rc=0；覆盖仍 50/50；
3. **可达 FAIL**：把 `ft_scale` 的饱和界改 ±1024 ⇒ `ftsclb` 用例红（`cp`+md5 还原）；
4. 散文零改动（基线锚**固定 commit**，禁 `HEAD`/`merge-base`——`Process-07 §5b`）。

## 完成区

（待填）
