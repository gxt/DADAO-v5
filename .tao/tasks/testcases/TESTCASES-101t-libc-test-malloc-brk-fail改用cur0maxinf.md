# TESTCASES-101t: libc-test `malloc-brk-fail` 改用 {cur=0,max=inf}（收口 rlimit 实现后的夜跑红）

**模块**：testcases
**项目里程碑**：M11
**依赖**：`QEMU-084t`（已验证；guest rlimit 记账落地）、`TESTCASES-100t`（已验证；该用例 64 KiB 页修正）
**状态**：待开始

## 用户裁定（2026-11-06）

> 「A：改语料用 {cur=0,max=inf}（推荐）」——改 libc-test 补丁：用 cur=0、保留 max=inf 代替 `t_setrlim`；测试意图不变（VA 满时 malloc 失败、腾出后成功），与内核 Valgrind workaround 一致。

## 现状

`QEMU-084t` 实现 guest `RLIMIT_AS/DATA/STACK` 记账后，夜跑 `tset:libc-test` 的 static 与 dynamic 两档都红：

```
FAIL regression/malloc-brk-fail  exit=1
  malloc(10000) failed (eventhough 64k is available to mmap): Out of memory
```

根因：该用例用 `t_setrlim(RLIMIT_DATA, 0)`，而 `t_setrlim` 会把 **`rlim_cur` 与 `rlim_max` 都设成 0**。内核 `may_expand_vm()` 的 Valgrind workaround 要求：

```
rlimit(RLIMIT_DATA) == 0 && 请求量 <= rlimit_max(RLIMIT_DATA)
```

`max` 也是 0 时 workaround 不成立 ⇒ `munmap` 之后的新 `mmap` 仍被拒 ⇒ 用例报错。

宿主实测（Linux 6.8）：

- `RLIMIT_DATA={0,0}` + RW `mmap(64 KiB)` ⇒ `ENOMEM`
- `RLIMIT_DATA={cur=0,max=infinity}` + RW `mmap(64 KiB)` ⇒ 成功

即该用例的期望只在 `max` 保持 infinity 时成立；此前能过是因为 QEMU 把 rlimit 当 no-op。

## 目标

1. 修改 `tests/tset/libc-test/patches/src/regression/malloc-brk-fail.c.patch`：把 `T(t_setrlim(RLIMIT_DATA, 0));` 改为**只降 `rlim_cur`、保留 `rlim_max`** 的调用（等价 `{cur=0, max=infinity}`），并在补丁注释里写明依据（内核 `may_expand_vm()` 的 Valgrind workaround；`t_setrlim` 会连 `max` 一起降，使 workaround 失效）。
2. 保持用例语义与断言不变：先 `t_vmfill` 填满 VA ⇒ 首个 `malloc(10000)` 仍必须失败且 `errno=ENOMEM`；`munmap` 64 KiB 后 ⇒ 第二个 `malloc(10000)` 必须成功。不得删除断言、不得放宽退出码。
3. 组件补丁按既有流程重导出（一文件一补丁、`series`/`changelog.md` 更新），锁 commit 不变。
4. 更新 `tests/tset/libc-test/README.md` 与 `tests/tset/libc-test/changelog.md` 的说明（该用例为何用 `cur=0/max=inf`）。

## 范围 / 非范围

**在范围内**：`tests/tset/libc-test/patches/src/regression/malloc-brk-fail.c.patch`、`tests/tset/libc-test/{series,changelog.md,README.md}`（如系列不变则不动 `series`）、本任务书、`milestones.md`。

**不在范围**：QEMU/gem5 实现与补丁、其它语料用例、`spec/**`、`contracts/**`、测试判据/门控逻辑。

## 验收标准

1. 该用例在 QEMU 下 static 与 dynamic 两档均 PASS（真实 rc=0）。
2. `make check-tset-libc-smoke` rc=0；`make check-tset-libc-full`（static+dynamic）rc=0。
3. `make check-patch-tree`、`make check-source-state`（libc-test base+1 clean）、`make check-index-blobs`、`make check`（L1）rc=0。
4. 反例：把补丁改回 `t_setrlim(RLIMIT_DATA, 0)` ⇒ 该用例 FAIL；`cp`+`md5sum -c` 还原并重建后回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- 这是**语料假设**修正，不是 QEMU 语义回退：QEMU 行为与 Linux 6.8 实测一致，保持不动。
- `TESTCASES-100t` 的 6×32736 启动堆 prime 逻辑保留（64 KiB 页下仍需消耗 loader 捐赠堆）。
- 修好后由 architect 重跑完整夜跑（一次全绿）再收口 M11。
