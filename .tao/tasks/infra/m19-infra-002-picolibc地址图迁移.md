# m19-infra-002: picolibc Tiny 地址图迁移（组件补丁）

**模块**：infra
**项目里程碑**：M19
**依赖**：`m19-spec-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

picolibc 安装根/cross 链接脚本仍按旧 Tiny 布局（entry `0x10100`、SP `0x7eff00`、8 MiB SRAM）。新几何为 entry `0x2000`、SP `0x3F000`、SRAM 256 KiB、EXIT `0x30`、signature `0x1000`；不改则 `check-picolibc-tests` 在新 QEMU/gem5/chipyard 下必红。

## 目标

1. 更新 `components/picolibc` 的 Tiny 链接脚本/补丁：`picolibc-tiny.ld` 的 RAM/entry/SP/EXIT/heap；按 256 KiB、`0x2000` 入口、`0x3F000` SP。
2. 更新 series/patches/changelog；重建安装根；确认 `make build-picolibc`（或等价）可重跑。
3. 版本号/组件补丁集变更**待用户确认**；未确认前只落内容，不擅自升号。
4. 不改 `tests/inst`/`tests/arch`（归 testcases-002/004）。

## 验收（逐条贴真实 rc）

1. picolibc 安装根重建成功；Tiny smoke/代表测试在新几何 QEMU 下跑通。
2. `check-patch-tree` picolibc 段 0 problem；`check-component-changelog` rc=0。
3. **可达 FAIL ≥2 路**：① 链接脚本 entry 写回 0x10100 ⇒ 装载红；② SP 写回 0x7eff00 ⇒ 栈越界/红。
4. 版本号未升级（除非用户当轮确认）；不接板。

## 约束

独立 `git worktree`；**不提交 git**；只动 `components/picolibc` 与必要清单/索引；不改 QEMU/gem5/chipyard/testcases；完成区不写具体 `.work/**` 路径。
