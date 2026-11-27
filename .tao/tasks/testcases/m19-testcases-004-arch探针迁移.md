# m19-testcases-004: tests/arch Tiny 探针迁移（entry 0x2000、SP/EXIT/DUMP）

**模块**：testcases
**项目里程碑**：M19
**依赖**：`m19-spec-002`、`m19-testcases-002`
**可并行分片**：否
**预估**：4–8 h
**档位**：中改
**状态**：待开始

## 背景

`m19-testcases-002` 只迁了 `tests/inst` 与 `tests/ee-tiny`。`tests/arch/**` 仍有 15 份 Tiny `.lds`/`.S` 按旧入口 `0xffffff010100`、旧 SP/EXIT/DUMP 展开；新几何下会装载/执行失败。

## 目标

1. 迁 `tests/arch/{hart,time,ptw,umon,pmem,cache}` 等 Tiny 探针的 `.lds`/`.S`：entry `0x2000`、SP `0x3F000`、EXIT `0x30`、DUMP `0x800`、signature `0x1000`（若该探针使用）。
2. 按新 `machine-tiny.inc` 重新生成/对齐常量；删除旧 `0x10100`、`0x7e...` 硬编码。
3. QEMU/gem5/chipyard 跑通代表探针；地址类 `cause_info`/CFXMEM 期望按新几何更新。
4. 不改 `tests/inst`/`tests/ee-tiny`（归 testcases-002）与 picolibc（另任务）。

## 验收（逐条贴真实 rc）

1. 15 份探针全部可构建；代表探针三平台跑通。
2. `entry=0x2000`、SP/EXIT/DUMP/signature 地址与 `runtime.yaml` 一致；无旧 `0x10100` 残留。
3. **可达 FAIL ≥2 路**：① 把某探针 entry 写回 0x10100 ⇒ 装载/执行红；② 把 EXIT 写回旧 `0x7e0000` ⇒ 退出/比对红。
4. `check-inst-asm`（arch 部分）/`check-tests-index` 真实 rc；基线红逐行对照。

## 约束

独立 `git worktree`；**不提交 git**；只动 `tests/arch/**` 与必要索引；不改 QEMU/gem5/chipyard 源码；不接板；完成区不写具体 `.work/**` 路径。
