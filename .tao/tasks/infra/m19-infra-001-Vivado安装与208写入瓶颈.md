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
4. 证据落运行期证据目录（按任务号分子目录），长任务落 PID/日志/`*_EXIT`；两节点工作树保持 `dirty=0`（只往 `/tools` 写，不动仓库）。

## 约束

- **不动仓库内被跟踪文件**（装机只落 `/tools`）；节点仓库 `dirty` 必须保持 0。
- 复制走主控机中继，不用节点直连公网下载（用户口径）；`zstd -3 -T8` 压缩以压缩隧道耗时。
- 不扩分区、不改 RAID 级别、不动盘阵（破坏性操作须用户另行确认）；写测试文件用后即删。
- 不追求「6 台全装」：本任务只做 207/208，其余节点由用户后续决定。

## 完成区

1. **复制（两台）**：主控机中继 `ssh zzx 'sudo tar -C /tools -cf - Xilinx' | zstd -3 -T8 | ssh <node> 'zstd -d | tar -C /tools -xf -'`；两节点均 `EXIT=0`，与源端**逐字节一致**：`140,641,898,105` B / **455,198** 文件 / 133 G；装完 `/` 剩 452 G（207）、458 G（208）。日志与退出码落运行期证据目录（`vivado-207`/`vivado-208` 的 `.log` 与 `.EXIT`）。
2. **license**：四份 `.lic` 落两节点 `/tools/Xilinx_lic/`（`644`；主控机在运行期证据目录里留一份缓存）。**三路对照（207，干净 `HOME`，同一 blinky，2026-11-23）**：`XILINXD_LICENSE_FILE=/tools/Xilinx_lic/vivado_lic2037.lic`（**带 `D`**）⇒ `rc=0`/`SYNTH_OK`；只设 `XILINX_LICENSE_FILE`（不带 D）⇒ `rc=1` + `ERROR: [Common 17-345]`；两者都不设 ⇒ `rc=1` + 同一错误。**坑**：成功跑过一次后 Vivado 会把 `XILINXD_LICENSE_FILE=/tools/Xilinx_lic` 写进 `$HOME/.flexlmrc`，此后不设变量也 `rc=0`（复测时的缓存假象；`HOME` 指空目录即复现失败）。
3. **综合验证（两台）**：`vivado -version` ⇒ `vivado v2025.1 (64-bit)` rc=0；`synth_design -top blinky -part xc7k325tffg900-2` 两节点均 **rc=0 / `SYNTH_OK`**（207：综合 34 s、峰值内存 2.5 GB；`report_utilization` = `Device: xc7k325tffg900-2`、`Design State: Synthesized`）。证据：节点 `~/m19-infra-001/synth-{207,208}.log` + `synth/utilization.rpt`；验证件（`blinky.v`/`synth.tcl`/`run.sh`）在运行期证据目录内。
4. **208 写瓶颈定位**：`dd oflag=direct conv=fdatasync` 4 GiB = **35.1 MB/s**；`iostat -x` 272 写/秒 × 128 KB、`%util 97–98 %`、`w_await 18.6 ms`、`aqu-sz ≈ 5`；`/sys/block/sda/queue/write_cache = write through`；控制器 `iMR(0MB)`（无缓存）；`max_hw_sectors_kb=128`（改 1024 → `EINVAL`）；盘阵 4×`ST3300657SS` 15k SAS RAID5/898 GB，4 盘 SMART 全 OK（`grown defect` 59/37/0/0）；顺序读 451 MB/s、207 写入 31.4 MB/s（同配置同表现）。
5. **结论（非坏盘）**：瓶颈 = 写通 RAID5 的 IOPS 上限（每个 128 KB 逻辑写落 3 份物理写 + ext4 journal）。可行改进：加控制器 cache/BBU（唯一实质）；改 RAID10（重建阵列，破坏性，待用户确认）；OS 调参无效（已实测 `max_sectors_kb` 被硬件卡住）。
6. **文档**：`nodes.md §11.7` 改写为「源 `zzx-NF5280` / 207+208 已装」，含 `XILINXD_LICENSE_FILE` 口径与综合证据；§1 清单 207/208 标注「Vivado 2025.1 已装」；§2 新增控制器/写通结论。
7. **未做（明确遗留）**：不做「6 台全装」（用户本次只定 207/208）；未做实现/布线/bitstream（只验证到综合）；Vivado 版本入 `manifests/` 锁属 `m19-chipyard-001` 范围。
8. 修改文件：`.tao/knowledge/nodes.md`、`.tao/knowledge/milestones-m19.md`、本任务书（节点侧只写 `/tools`，两节点仓库 `dirty=0`）。
9. **reviewer 第 1 轮阻断项（license 口径）已修**：原写「必须带 D、不带 D 必失败」在已生成 `$HOME/.flexlmrc` 的机器上不可复现。补做**干净 `HOME` 三路对照**（207 与 208 各一次）：带 `XILINXD_LICENSE_FILE` ⇒ `rc=0`/`SYNTH_OK`；只设不带 D ⇒ `rc=1` + `17-345`；都不设 ⇒ `rc=1` + `17-345`；并把「成功一次后写 `.flexlmrc`、此后不设变量也通过」的缓存机制写进 `nodes.md §11.7` 与本条。
10. 附带转绿：本任务书原先有 4 处字面运行期路径，`check-knowledge-refs` 由 FAIL（3 条）转 **PASS（0 具体引用 / 0 悬空）**，已按「运行期证据目录」措辞改写。

## 审阅记录

### 第 1 轮 reviewer 验收（2026-11-23，中改档 40 min；重跑均为本人执行，rc=被检命令自身）

1. **复制对账 — PASS**：`ssh server207 'sudo -n du -sb /tools/Xilinx; sudo -n find /tools/Xilinx -type f | wc -l'` ⇒ `140641898105` / `455198`（rc=0）；`server208` 同命令同值；`zzx-NF5280` 同命令同值（rc=0）；`du -sh` = `133G` ✓。`df -h /` ⇒ 207 `452G` 可用（完成区 452 G ✓）、208 `458G`（✓），与验收起点无漂移。
2. **license 正反两路 — ①PASS / ②FAIL（结论不可复现）**：① 只设带 D 变量跑同一 blinky ⇒ `RC1=0`、`INFO: [Common 17-349] Got license`、`SYNTH_OK`、无 17-345。② 只设 `XILINX_LICENSE_FILE=<同一 lic>`（unset 带 D）⇒ **`RC2=0`、`SYNTH_OK`、无 17-345**，与完成区第 2 条相反。旁证：全不设变量 ⇒ `RC3=0`；不带 D 指向不存在路径 ⇒ `RC4=0`；`HOME` 指向空目录（隐藏 `.flexlmrc`）⇒ `RC6=1` + `ERROR: [Common 17-345]`。根因：节点用户家目录 `.flexlmrc`（39 B，mtime 02:22:25，内容 `XILINXD_LICENSE_FILE=/tools/Xilinx_lic`）比 02:21 那次 17-345 失败晚 1 分钟 ⇒ 「不带 D 导致失败」无因果证据。
3. **208 写瓶颈 — PASS**：`dd if=/dev/zero of=<家目录临时文件> bs=1M count=1024 oflag=direct conv=fdatasync` ⇒ `34.2 / 34.5 MB/s`（rc=0；完成区 35.1，差 ≤3%）。并发 `iostat -x 2 6`：`w/s 259–294`（272 ✓）、`wareq-sz 128` ✓、`%util 97.55–98.15` ✓、`w_await 18.56–24.15 ms`（含 18.6 ✓）、`aqu-sz 4.96–5.34`（≈5 ✓）。`write_cache=write through`、`max_hw_sectors_kb=128`、`dmesg: controller type : iMR(0MB)` ✓；`smartctl -d megaraid,{4,7,10,11}` ⇒ 4 盘 `SMART Health Status: OK`、`Elements in grown defect list: 59/37/0/0` ✓。我的测试文件与临时目录已删。
4. **文档一致性 — PASS（第 2 条口径除外）**：`nodes.md` §1 两行标「Vivado 2025.1 已装，见 §11.7」✓；§2 两行控制器/写通数字与我实测逐项相符 ✓；§11.7 体积/文件数/133 G/452 G ✓；「综合 34 s」= 其日志 `Synthesis Optimization Runtime elapsed = 00:00:34` ✓；`utilization.rpt` 报 `Device: xc7k325tffg900-2`、`Design State: Synthesized` ✓。`git show --stat 2340c916` ⇒ 仅 3 文件（`nodes.md`、`milestones-m19.md`、本任务书），全在「修改文件」清单内 ✓。
5. **无越界/无残留 — PASS**：两节点 `git status --porcelain -uall` 均空（rc=0）；主控机验收起点 `git status` 空，本记录写入后仅本任务书变更。
6. **门控 `make check-knowledge-refs` — FAIL（基线红，非本轮新增）**：rc=2，报 3 条具体 `.work/**` 引用（本任务书 30/42/43 行）；`git show HEAD:<本任务书>` 同样含同样引用 ⇒ 与基线错误集相同；本审阅记录段内 `.work/` 计数 = 0 ⇒ 我未新增悬空引用。

**采信未复测**（任务清单未要求）：顺序读 451 MB/s、207 写 31.4 MB/s、`max_sectors_kb` 试改 1024 → `EINVAL`。**未复测 208 综合**：采信其 `synth-208.log` 内 `SYNTH_OK`（grep=2）与证据目录 `EXIT=0`。

**判决：Needs Revision**（阻断项仅一类——语义：完成区第 2 条「不带 D 必报 17-345 / 必须用带 D 变量」在同机同设计上不可复现，且被 `nodes.md` §11.7 与 `run.sh` 注释沿用）

**最小修复清单**
1. 改本任务书完成区第 2 条、`nodes.md` §11.7「许可」「踩坑」两行、运行期证据目录内 `run.sh` 注释：删去「不带 D 报 17-345」的因果表述，改为实测可复现口径（`.flexlmrc` 指向许可目录后，带/不带 D 乃至不设变量均 rc=0；17-345 只在该文件不可见时出现）。
2. 若坚持原口径：在覆盖 `.flexlmrc` 影响的条件下（如 `HOME` 指向空目录）重跑正①带 D → rc=0、反②不带 D → 失败且含 17-345，贴两路 rc；跑完删临时件并确认两节点 `git status` 空。
3. 复制对账、综合 rc=0、写瓶颈证据三项已由我独立复核 PASS，无需重做。
4. 把本任务书 30/41/42/43 行的具体 `.work/**` 路径改为「运行期证据目录」措辞（或升格入库数据），使 `make check-knowledge-refs` 由基线红转绿；改后重跑该门控贴 rc。
