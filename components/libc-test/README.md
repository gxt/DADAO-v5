# libc-test 组件（libc-test）

musl/Linux 用户态一致性测试语料（`TESTCASES-044t`，`ADR-0025 D6`）：判定 musl 移植
（`P1` 静态 / `P2` 动态）是否成立的**独立**输入，不参与实现。上游基线由
`manifests/components.lock.toml` 锁定（`b7ec4679…`，`shallow = false`，完整裸镜像
`.cache/libc-test.git`）；工作树由 `make fetch` + `make apply-series` 在
`.work/source/libc-test` 建立。

## 补丁集

- 形态：**树形补丁集**（`patches/<上游相对路径>.patch`，一文件一补丁），清单见
  `series`；规范见 `docs/Process-01-组件补丁组织与构建编排.md`。
- 现行补丁 **1** 个：`src/regression/malloc-brk-fail.c`（`TESTCASES-100t`）。
  - 原因：64 KiB 页下，musl dynamic loader 把可写 `PT_LOAD` 段两端按页对齐的空洞
    「捐赠」给 mallocng（`ldso/dynlink.c` 的 `reclaim_gaps`）。测试原先假设「填满
    VA + `RLIMIT_DATA=0` 后 `malloc(10000)` 必失败」；在 64 KiB 页上该请求直接落在
    捐赠空洞里、无 `brk`/`mmap` 系统调用，于是假绿。补丁在 `t_vmfill` 之前申请并
    保留 6 个 32736 B（size class 39）块，先消耗这些捐赠组；断言、magic、退出码、
    `t_vmfill`/`t_setrlim` 逻辑均不改；4 KiB 页布局下按同一 size-class 表推导不退化
    （本机 QEMU 只有 64 KiB 页，无法现场跑 4 KiB，理由见 `TESTCASES-100t` 完成区）。
- 补丁只做**测试输入侧的可移植性修正**，不放宽判据：static 档仍覆盖原行为，
  dynamic 档仍执行同一用例。

## 验证

```
make check-tset-libc-full          # static + dynamic 全量（夜跑成员）
make check-tset-libc-smoke         # 代表集（L2）
make check-patch-tree check-source-state   # 补丁集 / 源树 E1 自检
```
