# TESTCASES-099t: libc-test dynamic malloc-brk-fail 差异诊断

**模块**：testcases
**项目里程碑**：M11
**依赖**：`TESTCASES-076t`（夜跑驱动）、`TESTCASES-083t`（libc-test tset 驱动）；无 spec 前置
**状态**：待开始

## 执行环境
本地；**只诊断，不改 QEMU、不改 libc-test 期望、不改 musl**。允许在运行期目录写复现脚本/日志。

## 背景（2026-11-05 夜跑现场）

M11 收口夜跑 `check-night` 结果：

- `tset:llvm-ts` rc=0
- `tset:embench` rc=0
- `arch:cfx` rc=0
- `tset:libc-test` **rc=2**（dynamic）

失败用例：`regression/malloc-brk-fail`

```text
malloc(10000) succeeded after memory is filled
```

已复现（dynamic，`-R 4G`）：

- 启动：`brk(NULL)=0x50000` → `brk(0x70000)=0x70000`（musl mallocng 预扩 2 页）
- 之后 `t_vmfill` 填满 VA，`prlimit64(RLIMIT_DATA, {0,0})=0`
- 成功的那次 `malloc(10000)` **无任何 mmap/brk 系统调用** ⇒ 使用启动时预扩的堆
- static 同用例（`-R 4G`）通过

初步判断（待独立复核）：这是 musl dynamic 启动堆与测试假设的交互，不是 QEMU `mmap`/`RLIMIT_DATA` 直接失效。

## 目标

1. 用**独立命令**复现 dynamic 失败、static 通过；保留 QEMU 版本、ELF md5、`-R` 参数、退出码。
2. 定位启动 `brk(0x50000)→brk(0x70000)` 的来源：
   - 是 musl mallocng 首次 malloc（`ctx.brk` 初始化）还是 QEMU ELF loader；
   - 用 `-strace`/`-d`/符号/最小复现区分；给出证据。
3. 验证 `RLIMIT_DATA=0` 对 guest `brk` 与 `mmap` 的实际作用：
   - 构造最小 guest 程序，分别测 `brk`/`mmap`/`malloc`；
   - 判断是否存在 QEMU user-mode 未执行 guest rlimit 的缺陷。
4. 给出三种处置的证据与影响，不自行选择：
   - **A. known-fail**：登记 issue（musl dynamic 启动堆导致测试假设不成立），dynamic 记 known-fail；static 覆盖。
   - **B. dynamic 排除**：该用例仅 static 运行，README/驱动写原因。
   - **C. 测试修正**：在测试侧填满初始堆（改 libc-test 资产或驱动），需另立授权。
5. 若确认 QEMU 缺陷：给出最小 reproducer、涉及代码路径（linux-user `brk`/`mmap`/rlimit）和修复建议；**不在本任务改 QEMU**。

## 接口规范 / 边界

- 只读仓库代码、构建产物、测试资产；复现脚本写运行期临时目录。
- 不改 `tests/**`、`tools/testcases/tset/**`、`components/**`、`spec/**`、`contracts/**`、`Makefile`。
- 不改 `KNOWN_*`/known-fail registry；只给建议。
- 不把“未复现”写成结论；每个判断附命令与真实输出。

## 验收标准

1. **复现**：dynamic 失败、static 通过；退出码、QEMU 版本、ELF md5、`-R 4G` 记录齐全。
2. **系统调用证据**：dynamic 成功 malloc 前后无 `mmap`/`brk`；static 对照有对应失败路径。
3. **启动 brk 来源**：有证据区分 musl mallocng 与 QEMU ELF loader；不只凭推测。
4. **RLIMIT_DATA 验证**：最小程序证明 guest `brk`/`mmap` 是否受 `RLIMIT_DATA=0` 约束；给出 QEMU 是否有缺陷的结论。
5. **处置建议**：A/B/C 逐项写影响、风险、需要的授权；给推荐但不替用户决定。
6. **不改动**：`git status` 仅任务书/milestones（如有）；无 `tests/**`/`components/**`/`tools/**` 改动。
7. **体例**：完成区 ≤30 行；证据落运行期目录（已留档，未入库）；状态 `待验收`。

## 完成区

**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审

#### 第 1 轮 reviewer 验收
