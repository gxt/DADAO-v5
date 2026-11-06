# GEM5-025t: gem5 SE IPC 与多进程

**模块**：gem5
**项目里程碑**：M11
**依赖**：`GEM5-024t`（信号/资源限制；同改 gem5 补丁，须先合并）
**状态**：待开始

## 背景与事实（`GEM5-021t` gap inventory）

- **IPC/socket/pipe 6 例**：`pipe2`(59) 5 例（`functional/fscanf`、`popen`、`spawn`、`regression/daemon-failure`、`fgetwc-buffering`）+ `socket`(198) 1 例（`functional/socket`）
- **process creation/exec 1 例**：`execve`(221)（`regression/execle-env`）
- 其余 syscall 面（`fork`/`wait4`/`dup`/`close` 等）按现场补齐

## 目标

1. **pipe**：`pipe2`（含 `O_CLOEXEC`/`O_NONBLOCK`）、阻塞/EOF/`EPIPE`、与 `dup`/`fcntl` 协作；guest fd 表内 pipe 对象。
2. **socket（最小面）**：`socket`/`bind`/`connect`/`send`/`recv`/`shutdown`/`getsockname` 等按 `functional/socket` 实际调用；若语料只用 `AF_UNIX` 就只做该族，其它返回 `EAFNOSUPPORT`（如实登记）。
3. **多进程**：`fork`/`vfork`（SE 多 process 支持）、`execve`（按 `contract-syscall` 的 argv/envp/auxv 约定）、`wait4`；父进程等待与退出码传递。
4. 不改测试用例/期望；不改 QEMU。

## 范围 / 非范围

**在范围内**：`components/gem5/patches/src/arch/dadao/{se_workload.*,process.*,...}`、`components/gem5/changelog.md`、`components/gem5/README.md`、本任务书、`milestones.md`。

**不在范围**：线程/futex/TLS（`GEM5-026t`）、动态链接（`GEM5-027t`）、文件 I/O/时钟/信号（前序任务）、QEMU、测试用例与期望。

## 验收标准

1. 基线复跑：IPC/socket/pipe 与 process creation 两桶 blocked 归零（或转真实失败并给最小复现）；`qemu_only_fail` 0；`gem5_only_fail` 不新增。
2. 代表案例（`popen`、`spawn`、`daemon-failure`、`socket`、`execle-env`）各 ≥3 次一致；pipe 读写/EOF/EPIPE 抽测。
3. `build-gem5`、`check-inst`、`check-arch`、`check-patch-tree`、`check-source-state`、L1/L2 rc=0。
4. 反例：把 `pipe2` 改回未实现 ⇒ 代表案例回 blocked；`cp`+`md5sum -c` 还原重建回绿（禁 git 还原）。
5. 完成区 ≤30 行；状态 `待验收`。

## 说明

- `execve` 依赖 `GEM5-024t` 的 auxv/栈构造；若 `fork` 需要写时复制，先做最小可用（`fork` 复制地址空间）。
- `socket` 只做语料实际使用的最小族，其它显式 `EAFNOSUPPORT`/`ENOSYS`，不得静默成功。
