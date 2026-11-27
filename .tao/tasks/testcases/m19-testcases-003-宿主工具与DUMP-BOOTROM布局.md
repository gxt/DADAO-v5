# m19-testcases-003: 宿主工具与 DUMP/BOOTROM 布局迁移（pt_regs 0x800、ROM 8 KiB）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`、`m19-testcases-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

`m19-testcases-002` 改了测试侧地址；宿主工具仍按旧 `DUMP_SIZE=0x408`、旧偏移和 64 KiB BootROM 工作。本任务把 DUMP 改成 `pt_regs` 0x800 布局，并把 BootROM 构建器改成 8 KiB 新布局。

## 目标

1. `tools/testcases/lib/build_test_binary.py`：`DUMP_SIZE=0x800`；四段偏移 `rd@0x000`、`rb@0x200`、`ra@0x400`、`rf@0x600`；`rd[0]=status`、`rb[0]=ip`；`EXIT_BLOCK=0x30`。
2. `verify_harness_dump.py` / `run_qemu_test.py`：pmemsave 大小/偏移与 0x800 布局一致；旧 `0x408` 偏移删除。
3. `machine_profile.py`：`REQUIRED_RUNTIME_FIELDS` 增 `dump_size`、`signature_base`（若 `m19-testcases-002` 已加字段）；交叉核对 `runtime.yaml`。
4. `check_tests_index.py`：假布局改 entry 0x2000、signature 0x1000、EXIT 0x30、DUMP 0x800、stack/MemRAS 新地址。
5. `tools/testcases/arch/build_tiny_bootrom.py`：`BOOTROM_SIZE=0x2000`；power@0–0x7FF、hmon@0x800–0x13FF、table@0x1F00；更新 hex 输出 `bootrom.tiny.hex`（8 KiB 稀疏 hex）。
6. 同步引用旧 `0x408`/64 KiB/`0x10100` 的注释与断言；不改 QEMU/gem5/chipyard 源码。

## 验收（逐条贴真实 rc）

1. QEMU `--dump` 读回 0x800：`rd0=status`、`rb0=ip`、四组顺序正确；旧偏移不再命中。
2. `build_tiny_bootrom.py` 产出的镜像 **恰好 8192 B**；power/hmon/table 偏移与 `m19-spec-002` 一致；`--check-hex` 通过。
3. **可达 FAIL ≥2 路**：① 把 `DUMP_SIZE` 写回 0x408 ⇒ dump 断言红；② 把 `BOOTROM_SIZE` 写回 0x10000 ⇒ 镜像大小/装载红。
4. `check-tests-index` / `check-run-artifacts` 真实 rc=0（基线红逐行对照）。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tools/testcases`、`tools/qemu` 中宿主工具与 bootrom 构建器；不改 QEMU/gem5/chipyard 源码；完成区不写具体 `.work/**` 路径。
