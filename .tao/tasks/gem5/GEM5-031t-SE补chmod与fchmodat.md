# GEM5-031t: gem5 SE 补 `chmod` / `fchmodat`（ISS-346）

**模块**：gem5
**项目里程碑**：M11
**依赖**：无（gem5 补丁串行；排在 `INTEG-060t` 之后）
**状态**：待开始

## 背景

`ISS-346`：QEMU linux-user 实现了 `chmod`/`fchmodat`（在模拟器内改宿主文件权限），gem5 SE 未实现。按「QEMU 有等价实现的 syscall，gem5 必须有」的口径应补齐，并加双引擎探针。

## 目标

1. `se_workload.cc` 实现 `chmod`（`SYS_chmod`）与 `fchmodat`（`SYS_fchmodat`，含 `AT_SYMLINK_NOFOLLOW`/`AT_EMPTY_PATH` 的处理按 Linux 口径）：
   - 目标 fd/路径经既有 `FileFDEntry` / 路径解析逻辑；
   - 返回值与 errno 与 QEMU 逐项一致（`ENOENT`/`EACCES`/`EPERM`/`ENOTDIR`/`ELOOP` 等按 Linux）。
2. 双引擎探针：mode 变更后可观察（`stat` 的 mode 位）、非法 mode、非属主、路径不存在、`fchmodat` 的 flag 组合。
3. 不改变其它 syscall 语义。

## 验收

1. 双引擎探针逐行一致（QEMU 作 oracle）。
2. 反例：去掉 mode 生效逻辑 ⇒ 探针 FAIL；`cp`+md5 还原重建回绿。
3. `build-gem5`、`check-gem5-decode`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1、L2 rc=0。
4. static libc-test 双引擎与当前基线逐例无回退。
5. 关闭 `ISS-346`；完成区 ≤30 行、无运行期路径。
