# m19-infra-001: server207/208 装 Vivado 2025.1（自 zzx-NF5280 复制）+ 208 写入瓶颈定位

**模块**：infra
**项目里程碑**：M19
**依赖**：无（`m19-chipyard-001` 的前置）
**可并行分片**：否（共享隧道带宽，两节点串行）
**预估**：5–8 h
**档位**：大改（节点软件安装 + 磁盘/控制器诊断）
**状态**：待验收

## 背景

- 用户 2026-11-22 裁定：**完整安装**（不裁剪 Vendor/Vitis/器件族），装到 **`server207`/`server208`**（这两台有外网），**从 `zzx-NF5280` 的 `/tools/Xilinx` 同路径 rsync 复制**（133 G，同系统 Ubuntu 24.04），随后处理 license 并验证可用；另要求在 `server208` 上查明「顺序写只有约 39 MB/s」的原因。
- 现场事实（2026-11-22 实测）：`server207` `/` 可用 **584 G**、`server208` **591 G**，均为单盘卷 `/dev/sda2`（ext4，`relatime`）；`zzx-NF5280` 的 `/tools/Xilinx` = **133 G**（`data` 50 / `SharedData` 39 / `tps` 18 / `Vivado` 7.0 / `lnx64` 6.4 / `Vitis` 5.5 / `gnu` 2.5 / `Model_Composer` 2.3 / `DocNav`+`xic` 1.1）。
- 两节点控制器：`megaraid_sas`，**`iMR(0MB)`**（无缓存模块）；`/sys/block/sda/queue/write_cache = write through`、`max_hw_sectors_kb = 128`；盘阵 = 4×`ST3300657SS`（300 GB 15k SAS），卷 898 GB（RAID5），4 盘 SMART 均 OK（`grown defect` 59/37/0/0）。
- 隧道实测：`zzx-NF5280 → 主控机` 约 **10 MB/s**、`主控机 → server207` 约 **10 MB/s**（500 MiB 各约 50 s）；`gzip -1` 压缩比约 **2.0×**（712 MB → 359 MB）。

## 目标

1. **复制安装**：主控机做中继（`ssh zzx 'tar -cf -' | zstd | ssh 207 'zstd -d | tar -xf -'`），同路径落到 `/tools/Xilinx`；**先 `server207`，验证通过后再 `server208`**。
2. **license**：把 `/tools/Xilinx_lic/*.lic` 一并复制，按「`XILINX_LICENSE_FILE` 指向许可文件」处理（`HOSTID=ANY`、`permanent`），并记录 `ubuntu` 账号下的可用方式。
3. **可用性验证**：`vivado -version` + **一次真实综合**（Genesys2 器件 `xc7k325t`，小模块，`synth_design`）证明 license checkout 与器件数据可用。
4. **写性能定位（`server208`）**：给出「是否坏盘 / 是否缺优化」的证据与结论；如可优化，给出可复现的调整与前后对比。

## 验收（真实 rc）

1. 两节点 `/tools/Xilinx` 体积/文件数与源一致（`du -sb` 与 `find | wc -l` 对账，允许 ≤1 % 偏差并说明来源）。
2. 两节点 `vivado -version` rc=0；**各跑一次 `synth_design` rc=0** 且日志无 license 错误（贴关键输出）。
3. 写性能：给出 `dd oflag=direct conv=fdatasync` 的 MB/s、`iostat -x` 的 `%util`/`w_await`/`wareq-sz`、控制器 `iMR(0MB)`/`write_cache`/`max_hw_sectors_kb` 证据；结论须明确区分「盘故障」与「控制器无缓存/RAID5 写惩罚」。
4. 证据落运行期日志目录（主控机 `.work/log/infra/m19-infra-001/`），长任务落 PID/日志/`*_EXIT`；两节点工作树保持 `dirty=0`（只往 `/tools` 写，不动仓库）。

## 约束

- **不动仓库内被跟踪文件**（装机只落 `/tools`）；节点仓库 `dirty` 必须保持 0。
- 复制走主控机中继，不用节点直连公网下载（用户口径）；`zstd -3 -T8` 压缩以压缩隧道耗时。
- 不扩分区、不改 RAID 级别、不动盘阵（破坏性操作须用户另行确认）；写测试文件用后即删。
- 不追求「6 台全装」：本任务只做 207/208，其余节点由用户后续决定。

## 完成区

1. **复制（两台）**：主控机中继 `ssh zzx 'sudo tar -C /tools -cf - Xilinx' | zstd -3 -T8 | ssh <node> 'zstd -d | tar -C /tools -xf -'`；两节点均 `EXIT=0`，与源端**逐字节一致**：`140,641,898,105` B / **455,198** 文件 / 133 G；装完 `/` 剩 452 G（207）、458 G（208）。日志与退出码 `.work/log/infra/m19-infra-001/vivado-{207,208}.{log,EXIT}`。
2. **license**：四份 `.lic` 落两节点 `/tools/Xilinx_lic/`（`644`，主控机缓存 `.work/log/infra/m19-infra-001/lic/`）。**关键口径**：必须 `export XILINXD_LICENSE_FILE=/tools/Xilinx_lic/vivado_lic2037.lic`（带 `D`）；不带 D 的 `XILINX_LICENSE_FILE` 在 Vivado 2025.1 下不生效，实测 207 上直接 `ERROR: [Common 17-345] A valid license was not found for feature 'Synthesis' and/or device 'xc7k325t'`。
3. **综合验证（两台）**：`vivado -version` ⇒ `vivado v2025.1 (64-bit)` rc=0；`synth_design -top blinky -part xc7k325tffg900-2` 两节点均 **rc=0 / `SYNTH_OK`**（207：综合 34 s、峰值内存 2.5 GB；`report_utilization` = `Device: xc7k325tffg900-2`、`Design State: Synthesized`）。证据：节点 `~/m19-infra-001/synth-{207,208}.log` + `synth/utilization.rpt`；验证件 `.work/log/infra/m19-infra-001/synth/`。
4. **208 写瓶颈定位**：`dd oflag=direct conv=fdatasync` 4 GiB = **35.1 MB/s**；`iostat -x` 272 写/秒 × 128 KB、`%util 97–98 %`、`w_await 18.6 ms`、`aqu-sz ≈ 5`；`/sys/block/sda/queue/write_cache = write through`；控制器 `iMR(0MB)`（无缓存）；`max_hw_sectors_kb=128`（改 1024 → `EINVAL`）；盘阵 4×`ST3300657SS` 15k SAS RAID5/898 GB，4 盘 SMART 全 OK（`grown defect` 59/37/0/0）；顺序读 451 MB/s、207 写入 31.4 MB/s（同配置同表现）。
5. **结论（非坏盘）**：瓶颈 = 写通 RAID5 的 IOPS 上限（每个 128 KB 逻辑写落 3 份物理写 + ext4 journal）。可行改进：加控制器 cache/BBU（唯一实质）；改 RAID10（重建阵列，破坏性，待用户确认）；OS 调参无效（已实测 `max_sectors_kb` 被硬件卡住）。
6. **文档**：`nodes.md §11.7` 改写为「源 `zzx-NF5280` / 207+208 已装」，含 `XILINXD_LICENSE_FILE` 口径与综合证据；§1 清单 207/208 标注「Vivado 2025.1 已装」；§2 新增控制器/写通结论。
7. **未做（明确遗留）**：不做「6 台全装」（用户本次只定 207/208）；未做实现/布线/bitstream（只验证到综合）；Vivado 版本入 `manifests/` 锁属 `m19-chipyard-001` 范围。
8. 修改文件：`.tao/knowledge/nodes.md`、`.tao/knowledge/milestones-m19.md`、本任务书（节点侧只写 `/tools`，两节点仓库 `dirty=0`）。
