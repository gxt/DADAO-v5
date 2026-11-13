# m14-infra-002: initramfs + semihosting 控制台/退出闭环

**模块**：infra
**项目里程碑**：M14
**依赖**：`m14-linux-001`（目标 `linux-initramfs` / `linux-semihosting-smoke` 与 `tools/linux/paths.py` 由该任务声明/提供）
**可并行分片**：否（init、cpio、runner 单链路）
**预估**：5–6 h
**状态**：待开始

## 背景

M14 K0 的 MVP 需要「内核日志 → 内置 initramfs 的静态 `/init` → 至少一次 syscall 往返」，控制台与测试退出闭环走 **semihosting**（不引入 UART、不新增 cfx）。K0 还没有内核，因此本任务先把**可被 K1 直接消费**的三件产物做出来并各自可验证：

1. 静态 musl 的 `init`（`write`/`getpid`/`brk` + 错误路径）；
2. 可复现的 cpio newc initramfs；
3. `SYS_EXIT` → host `$?` 的运行期脚本（先用既有 bare-metal semihosting 探针证明映射）。

现成可复用：`make build-musl` 产出 `libc.a`/crt，`make build-bootrom` 产出 `semihost_smoke.elf`/`semihost_fail.elf`，`qemu-system-dadao` 支持 `-semihosting-config` 且把 guest `SYS_EXIT` 码忠实传播到 host `$?`（实测 `semihost_fail.elf` ⇒ `64`）。

## 目标

1. **init 程序**（`tests/linux/init/`）：静态链接 musl，仅用 `write`/`getpid`/`brk`/`exit_group`：
   - 向 fd 1 写完整 banner（含 `init: pid=<n>`；处理部分写，循环补写）；
   - `getpid()` 结果 `> 0` 才继续；
   - `brk(0)` 读当前断点 → `brk(cur + 65536)` 扩一页（DADAO 普通页 = 64 KiB）→ `brk(0)` 复核（失败路径可区分）；
   - 成功 `exit_group(0)`；错误路径：写失败 `2`、`getpid` 异常 `3`、`brk` 失败 `4`（失败信息尽量写 fd 2，写不出去也按对应码退出）。
2. **host 侧错误路径单测**：用 host C 编译器 + syscall shim（`-DHOST_TEST`）注入写失败/`getpid<=0`/`brk` 失败，断言退出码 `2/3/4`；成功路径 `0`。
3. **cpio 生成**（`tools/linux/make_initramfs.py`，目标 `make linux-initramfs`）：
   - newc 格式；条目仅 `.`（dir）+ `init`（文件 0755）+ `TRAILER!!!`；
   - 确定性：mtime 固定 `0`、uid/gid `0`、条目字典序、4 字节对齐、无 build-id；
   - 产物含 initramfs 清单 JSON（路径由 `tools/linux/paths.py::linux_initramfs_manifest()` 给出；字段至少：init ELF sha256、cpio sha256、cpio 大小、syscall 号集合），供 `m14-infra-003` 读取；**不入库运行期路径**。
4. **semihosting 闭环脚本**（`tools/linux/run_semihosting_smoke.py`，目标 `make linux-semihosting-smoke`）：
   - 直接捕获 QEMU 进程 `$?`（**禁** `| tee`/管道吞码）；`semihost_smoke.elf` ⇒ `0`，`semihost_fail.elf` ⇒ `64`；
   - stdout 与源文本 oracle 逐字节一致（oracle 由 `tests/shared/bootrom/semihost_msg.inc` 独立派生，不复用 QEMU 输出）；
   - 期望值错误时非零退出（可达 FAIL）。
5. 不引入 UART/cfx/cache/DTB；不改 QEMU/gem5/chipyard 源码。

## 接口规范

**init 使用的 syscall（号值从锁定内核 `scripts/syscall.tbl` 现场取，不写死）**

| 名称 | 用途 | 备注 |
|---|---|---|
| `write` | banner/错误信息 | `fd`/`buf`/`len`，按 `contract-syscall §3` 传参 |
| `getpid` | pid 校验 | 返回值 `> 0` |
| `brk` | 堆断点 | `brk(0)` 读、`brk(x)` 设；失败返回 `-errno` |
| `exit_group` | 退出 | 退出码见上 |

- 通过 musl 的 `syscall(2)`/`write(2)` 调用（走 `rd15` + `rd16..`/`rb16..` + `rd8` 返回）；不使用 stdio/`malloc`。
- 编译：`clang --target=dadao-unknown-elf -static -O2`（或矩阵建议的等价参数），链接 `libc.a` + crt；产物必须 `ET_EXEC`、无 `PT_INTERP`、无 `DT_NEEDED`。
- 可复现：`SOURCE_DATE_EPOCH` 固定、`-ffile-prefix-map`、`--build-id=none`；`initramfs` 二次生成 sha256 相同。
- **cpio 布局**（`newc`，大端字段按 ASCII hex）：`.`（`S_IFDIR|0755`，size 0）、`init`（`S_IFREG|0755`，内容 = init ELF）、`TRAILER!!!`。
- **退出码映射**：guest `SYS_EXIT`（`0x18`，参数块 `{ADP_Stopped_ApplicationExit, code}`）⇒ host `$? = code`（`spec/Machine-v5 §5.5`）；`SYS_EXIT_EXTENDED` 同码规则；不得把 guest 码与 QEMU 自身错误码混淆（QEMU 启动错误另判）。

## 范围（改哪些文件）

- `tests/linux/init/init.c`、`tests/linux/init/host_test.c`（或同文件 `-DHOST_TEST` 分支）、`tests/linux/init/README.md`
- `tools/linux/make_initramfs.py`、`tools/linux/run_semihosting_smoke.py`（新建）
- 本任务书

**不改**：`Makefile`（目标已由 `m14-linux-001` 声明）、`components/`、`spec/`、`contracts/`、安装根、`tests/shared/bootrom/**`（只读复用）。

## 验收标准

1. `make linux-initramfs` rc=0；产物含 init ELF + cpio + 清单 JSON；`llvm-readelf -h/-d/-l` 证明 init 为 `ET_EXEC`、`EM_DADAO`、无 `PT_INTERP`/`DT_NEEDED`。
2. cpio 解析（独立脚本/`python3` 解析器，不复用生成器代码）：仅 `.`/`init`/`TRAILER!!!`，`init` mode `0o100755`，内容 sha256 = init ELF 现场 sha256；二次生成 cpio sha256 相同（打印两次值）。
3. syscall 集合：`llvm-objdump -d` 提取 `trap cfxha, 0` 前后的 `rd15` 常量，断言 ⊆ {`write`,`getpid`,`brk`,`exit_group`}（号值从 `scripts/syscall.tbl` 现场派生）；**不得**出现 `open/mmap/execve` 等。
4. host 单测：成功路径 rc=0；三路注入（写失败/getpid≤0/brk 失败）分别 rc=2/3/4；每例贴真实输出。
5. `make linux-semihosting-smoke` rc=0（前置 `make install-host build-bootrom`；缺前置须明确失败并提示）：`semihost_smoke.elf` ⇒ `0`、`semihost_fail.elf` ⇒ `64`；smoke 的 stdout 与源文本 oracle 逐字节一致；runner **直接**读取 `$?`（代码审查 + 注入「期望码改 65」⇒ FAIL 证明非恒真）。
6. 可复现：在同一工具链下连续两次 `make linux-initramfs`，init ELF 与 cpio 的 sha256 均相同；给出两次现场值。
7. 不引入 UART/cfx/DTB：`git status` 无 `spec/`/`components/qemu`/`components/gem5` 改动；`grep -i uart` 新增文件无命中。
8. 一键证据脚本（含注入→FAIL→`cp`+md5 还原→回绿）；完成区 ≤30 行、无运行期路径（清单 JSON 内的路径由脚本解析，不写进任务书/报告）。

## 说明

- **为什么 K0 能验 `SYS_EXIT` 映射**：既有 bare-metal semihosting 探针在 QEMU 上走同一台机器/同一 `SYS_EXIT` 服务；用它证明「guest 码 → host `$?`」链路，K1 接内核后复用同一 runner 即可。
- **init 不能在本任务运行**：DADAO 无 `linux-user`（P3 未实现），K0 无反内核；因此 init 的**语义**验收 = 静态（ELF/syscall 集合/cpio）+ host 单测（错误路径逻辑），不伪造「跑起来了」。
- **musl 依赖**：`make build-musl` 完成后再跑；缺 `libc.a`/crt 时目标须明确失败并提示，不得静默降级到 picolibc。
- 参考实现只读：`.cache/refs/DADAO/ENV-linux` 的 initramfs 构建方式可对照（**内容溯源，非执行必需**），不复制。

## 硬约束（子代理必读）

1. 必须在独立 `git worktree` 内作业（分支名 = 任务号）；禁改主工作树；临时文件放 `/tmp/opencode/<任务ID>/`。
2. 不提交 git（提交权归 architect）。
3. 完成区与真实输出逐条对齐；计数/sha/退出码写现场值。
4. 只动「范围」列出的文件；越界须披露。
5. 失败保留现场并继续推进；只有需要用户语义裁定才写「待裁定」并返回主会话。
6. 用户裁定/授权原话不得编造；自定事项标「自决」。
7. 命令作用域 = workdir（仓库根），用相对路径。
8. 反例注入一律「注入→FAIL→`cp`+md5 还原→回绿」；**禁** `git checkout/restore/stash` 还原。
9. 复杂命令输出/构建日志留存运行期日志目录（`docs/Process-08`）。
10. 证据脚本基线钉**派单前 commit 常量**或现场文件 md5，不得取 `HEAD`。
11. runner 不得用 `| tee`/`| tail` 等管道吞掉被检进程退出码。

## 用户授权

（本任务不改 `spec/`/`docs/Process-*`；如必须改，先停并登记「待裁定」。）

## 待裁定

（需用户语义裁定的事项写这里：问题 + 选项 + 建议 + 自决的临时处置；返回主会话。）

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

### 第 1 轮 engineer 自审（待填）

### 第 1 轮 reviewer 验收（待填）
