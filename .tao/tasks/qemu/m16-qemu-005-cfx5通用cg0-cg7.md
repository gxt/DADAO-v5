# m16-qemu-005: cfx5 通用 `cg0-cg7`

**模块**：qemu
**项目里程碑**：M16
**依赖**：`m16-qemu-003`（cfx5 命令）合入
**可并行分片**：否
**预估**：2–3 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-23 纠正）

`contract-see §3` 明确：**每个 cfx 提供 `cg0–cg7` 共有寄存器**，`cg3 rc12`（`hypv_cg_reg_deleg`）也是每个 cfx 都有。cfx5 目前只实现 `cg8`，其余 cg 报 `CFXREG`（qemu-001 的 CACHE-04 口径）——这是实现缺口，不是设计取舍。

后果：cfx5 的 `cg3` 不可写 ⇒ supv 无法访问 cfx5（017 的 supv 阻塞）。

## 要做

1. **cfx5 走通用行**：`cfx2rd`/`cfx2rc` 对 cfx5 的 `cg0–cg7` 走 `cfx_reg_ptr` 的通用表（模式掩码、`switch_run_mode`/`excp_vector`、`cg3 rc12` deleg、`cg4` 计数、`cg5` 异常帧、`cg6` scratch、`cg7` 空间描述）；`cg8` 保持 CACHE-03 的专属寄存器。
2. **deleg**：`cg3 rc12` 复位全 1、RW、bit3 固定 1（软件写 0 无效、读回 1）；hmon 写 `0x8` 后 supv 可访问 cfx5。
3. **两模型**：`cache-model=off|on` 都不改变 `cg0–cg7` 的存在；`cg8` 按 CACHE-27（off=`exist=0`/合法命令 no-op、on=`0b11`/真维护）。
4. **契约对齐**：按 `contract-see §3` 通用表；`contract-cache` CACHE-03/04 只描述 `cg8` 专属，不改契约正文（用户已认定 cg0-cg7 是契约要求）。
5. **验证**：cfx5 的 `cg0–cg7` 读写/保留、`cg3 rc12` 可写且 bit3 固定 1；supv 访问 cfx5 成功（hmon 写 `0x8` 后）；off/on 两模型都可用；`arch-umon-002` 等回归。

## 不做

- 不改 cfx5 的 `cg8` 专属语义（001/003）；
- 不改 gem5/RTL（另由 024/019 覆盖）；
- 不改影子数据通路。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出，`make_patch.py qemu` 幂等；
- 不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. cfx5 的 `cg0–cg7` 读写/保留；`cg3 rc12` 写 `0x8` 后读回 `0x8`、bit3 恒 1；
2. supv 访问 cfx5（hmon 写 deleg 后）成功；未写 deleg 时 `CFXPERM`；
3. off/on 两模型下 `cg0–cg7` 都在；`cg8` 按 CACHE-27；
4. **可达 FAIL**：注入「cfx5 仍走 `CFXREG`」⇒ 红；注入「deleg bit3 可清 0」⇒ 红；`cp`+md5 还原回绿；
5. `check-patch-tree` qemu 段 0 problem、`check-index-blobs`、`check-tasks`、`check-issues` 记录 rc；`--inject` ≥2 路。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
