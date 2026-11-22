# m16-gem5-024: gem5 cfx5 两轴权限 / trap / escape

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-023`（off no-op）合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 选 A）

`m16-gem5-023` 的遗留①：gem5 的 cfx5 **不进 `kCfxhaMap`**，所以 `trap cfx_cache`/`escape cfx_cache` 与 `<mode>_cfxtrap/cfxreg/cfxmem/cfxexe` 两轴掩码路径没接；QEMU/RTL 都有。用户要求每个 cfx 在 H/S/U 下跑，权限路径必须齐。

## 要做

1. **进 map**：cfx5 加入 `kCfxhaMap`（或等价通用路径），获得 `<mode>_cfxtrap/cfxreg/cfxmem/cfxexe` 行与异常向量。
2. **trap/escape**：`trap cfx_cache`、`escape cfx_cache` 按通用路径进入/返回；目标 cfx 的向量与帧字段按契约。
3. **两轴权限**：默认仅 hmon 可访问；smon/umon 访问按掩码 ⇒ `CFXPERM`；`m16-testcases-017` 的 env 打开掩码后允许。
4. **不回归**：023 的寄存器面、off/on 的 cfx5 命令语义、021 的 D/I 维护不回归；Tiny 无 cfx5。
5. **三方一致**：与 QEMU 的 `dadao_cfxha_map`、RTL 的通用 cfx 权限行对齐；差异登记 `expected-divergences.yaml`。

## 不做

- 不改 cache 数据通路/命令语义（021/023）；
- 不改 QEMU/RTL；
- 不加多核/uart。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py gem5` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx5 在 `kCfxhaMap` 中可查；`trap`/`escape cfx_cache` 进入/返回正确；
2. 默认 hmon 可访问、smon/umon 访问 ⇒ `CFXPERM`；env 打开掩码后允许（若 017 未合入，先用探针直接改掩码）；
3. off/on 的 023 寄存器面与 021 D/I 语义不回归；Tiny 无 cfx5；
4. **可达 FAIL**：注入「cfx5 不进 map」⇒ trap/权限用例红；注入「smon 默认放行」⇒ 红；`cp`+md5 还原并重建回绿；
5. `check-gem5-decode`、`check-patch-tree` gem5 段、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
