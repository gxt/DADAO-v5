# m16-chipyard-025: RTL Vast 4 MiB BootROM（窗口 + 稀疏镜像 + 启动路径）

**模块**：chipyard
**项目里程碑**：M16
**依赖**：`m16-chipyard-024` 合入（同改 `components/chipyard`，串行）；`m16-testcases-016` 已合入（DIV-12 登记方）
**可并行分片**：否
**预估**：2–4 h
**档位**：中改（复核 ≤40 min）
**状态**：待开始

## 背景（用户 2026-11-23 裁定 B：修 RTL）

`m16-testcases-016` 实测登记 **DIV-12**：RTL 的 `cfx_power cg7` 块 0 报 **64 KiB** BootROM（`start=0x3ff_ffff_0000`、`size=0x1_0000`），而 `spec/Kaiwu §3` 与 `contracts/machine.yaml(vast)` 规定 **4 MiB**（`0xffff_ffc0_0000`、`0x40_0000`）。根因：`DadaoConfigs.scala` 的 `WumingVastAddressMap.bootROMBase/bootROMSize` 直接继承 Tiny，`bootROMImage` 也继承 `/dadao/bootrom/bootrom.tiny.img`。

**口径**：窗口 base/size 与复位向量规则（`base + size − 64 KiB`）是硬件；镜像内容与布局（偏移 0 索引表 + payload + 末 64 KiB 启动段）是构建/装载侧。改窗口不会断启动，前提是镜像按 profile 构建。

**现成件**：`tools/testcases/arch/build_step5_bootrom.py` 已产出标准 Vast 4 MiB 镜像（索引表 + hmon/smon ELF + 零填充 + 末 64 KiB power flat 段，链接在 `RESET_PC`）；chipyard 资源生成器吃**稀疏 hex**（`@<offset>` 行，见 `build_tiny_bootrom.py --hex-out`），组件补丁集不携带二进制。

## 要做

1. **硬件窗口**：`WumingVastAddressMap` 改 `bootROMBase = 0xffff_ffc0_0000`、`bootROMSize = 0x40_0000`、`bootROMImage = "/dadao/bootrom/bootrom.vast.img"`；**Tiny 保持 64 KiB 不变**。
2. **Vast 镜像稀疏 hex**：给 `build_step5_bootrom.py` 加 `--hex-out`（与 `build_tiny_bootrom.py` 同一格式），产出组件的 `bootrom.vast.hex`（稀疏，零区用 `@offset` 跳写），资源生成器解码为 `/dadao/bootrom/bootrom.vast.img`。
3. **启动路径**：确认 RTL harness 能用 4 MiB ROM 并从索引表把 hmon/smon 装入各自 SRAM（现有 `+loadmem` 仍用于测试本体）；若探针 prelude 需要自有 payload，按同一镜像格式生成（不改 QEMU/gem5 的镜像构建语义）。
4. **登记收尾**：`m16-testcases-016` 的 `arch-power-001` 槽 5/6 改为规范值（`0x3ff_ffc0_0000`/`0x40_0000`）；删 `expected-divergences.yaml` 的 **DIV-12**（或按"例外被修好即提示删登记"的流程走）；`tests/arch/README.md` 的 power 小节同步。
5. **不回归**：Tiny 64 KiB BootROM 与 step5 启动链；现有 RTL 探针（`tests/arch/hart`、`ptw`、`power`）与 `run_arch --level smoke`。

## 不做

- 不改 QEMU/gem5 的镜像构建与装载语义；
- 不改 spec/契约（4 MiB 已是契约值）；
- 不动 `cfx_power` 的 common face（ISS-524）与 `cfx_power_ctrl` 写侧（ISS-525）。

## 约束

- 独立 `git worktree`；**不提交 git**；补丁按 `docs/Process-01` 导出、`make_patch.py chipyard` 幂等；
- 重建环境写进证据脚本；失败路径短 timeout、禁长时间 `-d cpu` dump（ISS-522）；不写运行期路径；术语「寄存器组」。

## 验证

运行期证据目录内的 `run.sh`：

1. `cfx_power cg7` 块 0：`start=0x3ff_ffc0_0000`、`size=0x40_0000`，块 1–15 `exists=0`；`m16-testcases-016` 的 28 槽逐槽全绿（DIV-12 删除）；
2. 复位从 `0xffff_ffff_0000` 起执行、hmon/smon 由索引表装入各自 SRAM，测试本体经 `+loadmem` 正常起跑；
3. **可达 FAIL ≥2**：注入「几何改回 64 KiB」与「镜像仍按 base 放置 64 KiB」⇒ 探针/启动链红；`cp`+md5 还原并强制重建后回绿；
4. `check-patch-tree` chipyard 段 0 problem、`make_patch` 幂等、`check-index-blobs`/`check-tests-index`/`check-tasks`/`check-component-changelog` 记录 rc；
5. Vast/Tiny 重建耗时与 md5 记录。

## 完成区

（待填：测试结果 / 修改文件 / 验收结果 / 新发现/坑 / 遗留问题）
