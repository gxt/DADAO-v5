# m16-gem5-023: `cache-model=off` 下 cfx5 存在但 no-op

**模块**：gem5
**项目里程碑**：M16
**依赖**：`m16-gem5-021`/`022` 已合入；`m16-spec-002`（CACHE-27 补维度）
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-22 已定）

Linux 内核缺省带 cache 维护逻辑，不能为“无 cache”单独编译内核。因此 `cache-model=off` 时 cfx5 必须**存在但 no-op**（`cache_exist=0`，命令被接受、不报 `CFXREG`、不产生效果），而不是 021 现在的“cfx5 不在 `kCfxhaMap` ⇒ `CFXREG`”。

## 要做

1. **cfx5 存在**：`node_cfx.cc` 的 `kCfxhaMap` 加入 cfx5（或在 `CfxhaCache` 路径单独处理），使 `cfx2rd`/`cfx2rc` 在 `exist=0` 时仍可访问寄存器，不报 `CFXREG`。
2. **off no-op**：`exist=0` 时 `cache_enable`/`cache_ctrl`/`cache_addr_start`/`cache_addr_size` 可读写（或按契约），`cache_ctrl` 合法编码被接受但不发维护、不产生效果；非法编码仍按契约报 `CFXREG`。
3. **on 不变**：`exist=0b11` 时按 021 的 D/I 维护语义执行（clean/invalidate/flush、范围/使能/异常）。
4. **契约对齐**：按 `m16-spec-002` 更新后的 CACHE-27 实现，不自行扩语义。

## 不做

- 不改 021 的 D/I 维护实现（只改 off 的存在/门控）；
- 不改 QEMU/RTL；
- 不升契约版本号。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py gem5` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `cache-model=off`：`cache_exist=0`；读/写 cfx5 寄存器不报 `CFXREG`；`cache_ctrl` 合法编码 no-op；非法编码仍 `CFXREG`；
2. `cache-model=on`：021 的 D/I 语义（A–F 0x10）不回归；
3. `off` 下 01 册 38/38、vast 10/10；
4. **可达 FAIL**：注入「off 下 cfx5 仍 `CFXREG`」⇒ 判据红；注入「off 下命令真发维护」⇒ 统计/行为红；`cp`+md5 还原并重建后回绿；
5. `check-gem5-decode`、`check-patch-tree` gem5 段、`check-index-blobs`、`check-tasks` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
