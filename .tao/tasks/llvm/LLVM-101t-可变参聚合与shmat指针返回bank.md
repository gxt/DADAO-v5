# LLVM-101t: 可变参聚合（`union semun`）与指针返回 bank 两个 codegen/ABI 缺陷

**模块**：llvm
**项目里程碑**：M8
**依赖**：`TESTCASES-047t`（现场来源 = 静态档第 2 轮重跑）、`ISS-249`（argmask 缺陷已 `closed`；本册承接其重跑后余下两例）、`ISS-256`（本册对应 issue）；契约依据 `contract-abi §4.4`（指针返回）/`§6.4`（聚合传参）/`§5`（变参）；`ADR-0025`（M8 范围）
**状态**：待开始

## 执行环境
**执行环境**：本地

## 问题根源

`TESTCASES-047t` 静态档在 `ISS-249`（argmask 12→245 + 三载体同步）收口后重跑：`pass 299 → 301 / fail 10 → 8`、**无回归**（原 pass 集全在）。余下 8 条 fail 中 **2 条** 是本册要修的两个**互相独立**的编译器 ABI 面缺陷（**与 argmask 表无关**：表已 245 条，`make check-syscall-abi` 69/69 rc=0）：

**A（`functional/ipc_sem`）——变参聚合参数两侧取法不一致**
- 现场（逐字）：`ipc_sem.c:58: semctl(semid, 0, IPC_STAT, arg) failed: Bad address`（guest exit 1）。
- 形态：musl `semctl` 是**变参**函数（`int semctl(int, int, int, ...)`），语料以 `union semun arg; arg.buf = &ds;` 作为**第 4 个（可变）实参**传入；实测 callee 侧 `arg.buf` 读到 **0** ⇒ `EFAULT`。
- 症状方向（待诊断确认，不预设）：一侧按**值**把 8 B 聚合放进寄存器槽、另一侧 `va_arg` 按**间接指针**读（或反之）。
- 契约依据：`contract-abi §6.4` —— `union` **不满足** HFA/HPA 同质判定 ⇒ 归**通用聚合**：`≤ 64 B` 拆 **1–8 个 8 B 块入 RD bank**，`> 64 B` 走**间接指针**；`§5` 记「聚合对齐、`> 8B` 聚合变参的拆分规则不变」（真源 `DADAO-21 §可变参数`）。**调用点与 `va_arg` 必须同取法**。

**B（`functional/ipc_shm`）——指针返回值未落 `rb8`**
- 现场（逐字）：`ipc_shm.c:80: shmdt(p) failed: Invalid argument`（该例 `mode` 断言 `ipc_shm.c:57` 已过；宿主 `shmat` 返回 `0x2aaaaaaab000`，而 guest 侧 `p` 实测为**栈地址**）。
- 形态：musl `shmat()` = `return (void *)syscall(SYS_shmat, id, addr, flag);`，`syscall()` 宏 → `__syscall_ret()` **尾调用**；`shmat.o` 反汇编显示尾调用路径**无 `rb8` 落值**。
- 契约依据：`contract-abi §4.4` —— **指针返回直接落 `rb8`**（「不经 `rd8` 中转」；`ADR-0018 C5`）；`§4.6` `call` 的 `Defs` 含 `rb8–rb15`。
- 症状方向（待诊断确认）：`i64 → ptr` 的尾调用返回 bank 不匹配（callee 结果在 `rd8`、caller 按 `rb8` 取），或尾调用 lowering 丢弃 bank 搬运。

> **两条都是「真缺陷」，不得用改语料 / 改期望 / 改标签过关**（`TESTCASES-047t` 判据 = 用例自身 `t_error → t_status → main` 退出码）。

## 接口规范

- **输入**：
  - `.work/source/musl/`（端口源；`arch/dadao/**`、`src/time/**` 等）
  - `.work/source/libc-test/`（`patchless = true` ⇒ **只读**，禁改）
  - `.dadao/cross-toolchain/`（安装根；本册改 `components/llvm-project/**` ⇒ 必须 `install-host` 后才新鲜）
  - `.work/build/qemu/qemu-dadao`（或安装根 `qemu-dadao`；**须在证据里注明用的是哪一个**）
  - 语料调用点：`src/functional/ipc_sem.c:58`、`src/functional/ipc_shm.c:57`/`:80`
- **输出**：
  - `components/llvm-project/patches/**` 的补丁更新（一文件一补丁，`docs/Process-01`）+ `series` 如增删 + `components/llvm-project/changelog.md` 条目
  - 证据落 `.work/evidence/<任务号>/`（执行时创建）：`run.sh` 一键可跑、含可达 FAIL；反汇编文本、编译/运行日志同目录（长日志另存 `.work/log/llvm/`）
  - 本任务书完成区（与真实输出逐条对齐）
- **约束**：只改 `components/llvm-project/**`（必要时 `tools/testcases/run_libc_test_user_suite.py` 的 `CASE_NOTES` 过期叙述）+ 本任务书 + `milestones.md`（如需）；**不动** `spec/` / `.tao/contracts/` / `contracts/` / 语料源。

## 最小复现（自包含；不依赖外部仓库）

**A：变参聚合实参**

```c
/* /tmp/opencode/LLVM-101t/repro_sem.c */
#include <sys/sem.h>
#include <stdio.h>
#include <string.h>
union semun { int val; struct semid_ds *buf; unsigned short *array; };
int main(void) {
    struct semid_ds ds; union semun arg;
    int id = semget(IPC_PRIVATE, 1, IPC_CREAT | 0666);
    if (id < 0) { perror("semget"); return 1; }
    memset(&ds, 0, sizeof ds); arg.buf = &ds;
    if (semctl(id, 0, IPC_STAT, arg) < 0) { perror("semctl"); return 1; }
    printf("mode=%o\n", ds.sem_perm.mode & 0x1ff);
    semctl(id, 0, IPC_RMID);
    return 0;
}
```

**B：指针返回经尾调用**

```c
/* /tmp/opencode/LLVM-101t/repro_shm.c */
#include <sys/shm.h>
#include <stdio.h>
int main(void) {
    int id = shmget(IPC_PRIVATE, 4096, IPC_CREAT | 0666);
    if (id < 0) { perror("shmget"); return 1; }
    void *p = shmat(id, 0, 0);
    if (p == (void *)-1) { perror("shmat"); return 1; }
    printf("p=%p\n", p);
    if (shmdt(p) != 0) { perror("shmdt"); return 1; }
    shmctl(id, IPC_RMID, 0);
    return 0;
}
```

编链口径（与 `TESTCASES-047t` 静态档一致；`<MUSL>` = `.work/source/musl`，头文件集合照该册「链接与运行口径」）：`clang -target dadao-unknown-elf -nostdinc -I <MUSL>/{arch/dadao,arch/generic,obj/src/internal,src/include,src/internal,obj/include,include} -std=c99 -O2 -c` ⇒ `ld.lld -o X.elf <MUSL>/lib/crt1.o X.o <MUSL>/lib/libc.a` ⇒ `qemu-dadao X.elf`。

**反汇编取证（诊断第一步，证据入 `.work/evidence/<任务号>/`）**
- A：`clang -S -O2` 看调用点 4 个实参如何落槽（第 4 个 = 8 B 聚合：`rd16+` 槽？间接指针？）；`llvm-objdump -d` 看 `__semctl` 里 `va_arg` 取法（读槽 vs `ld` 解引用）。
- B：`llvm-objdump -d <MUSL>/src/.../shmat.o`（或语料 `ipc_shm.o`）：尾调用 `jump` 前后的返回 bank（`rd8` vs `rb8`）。
- **结论必须写「哪一侧偏离契约 + 条款号」**（`§4.4` / `§6.4` / `§5`），不预设修法。

## 验收标准

1. **诊断先落盘**：两条各自的「偏离侧 + 契约条款号 + 反汇编片段」写入完成区；若诊断证明**契约本身有缺口**或**musl 用法越界** ⇒ **留问**（不擅改契约、不改语料、不改 musl 去迁就）。
2. **复现 A**：修后 `qemu-dadao` 打印 `mode=666`；修前现场 `semctl: Bad address`（须在同一证据脚本里给出修前/修后对照）。
3. **复现 B**：修后 `shmdt` rc=0 且 `p` 落在映射区间（打印 `/proc/self/maps` 对照或等价独立证据）；修前 `shmdt: Invalid argument`。
4. **独立 oracle**（不从 LLVM/QEMU/下游实现反推）：`mode` = `0666`（由 `semget` 创建参数独立得出）；`p` 的判据 = `shmdt(p)` rc=0 + `p` 不落在 guest 栈区间（栈范围由 `/proc/self/maps` 或 auxv/`SP` 独立取）。
5. **`TESTCASES-047t` 静态档重跑**：`functional/ipc_sem`、`functional/ipc_shm` 转 `pass`，`pass 301 → 303`、`fail 8 → 6`、`known-fail 3` / `blocked 25` / `excluded 30` 不变；**无回归**（原 301 条 pass 全在，逐条比对 JSON）。重跑前 `make build-musl`（新工具链）并核受影响对象 mtime 新鲜。
6. **可达 FAIL**（≥2 处注入，形状自选但须与判据绑定，例如：把 `va_arg` 聚合取法临时改回间接、把返回 bank 临时指 `rd8`）⇒ 对应判据 `[FAIL]`、脚本 rc=1 ⇒ `cp` + md5 还原 ⇒ 回绿、脚本 rc=0。
7. **门控**（各自 rc，现场计数不写死）：`check-patch-tree`（现 **177**，本册改后现场计数）、`check-instrinfo`（若改 `.td`）、`check-component-changelog`、`make check`(L1)。
8. **`install-host` 前置申报**：改 `components/llvm-project/**` ⇒ **单跑** `install-host`（`JOBS=8`、不并发、`ISS-210`；**启动前申报预计耗时**、完成后核安装根 `clang --version` 新鲜并复跑 A/B）。
9. **同步过期叙述**：`tools/testcases/run_libc_test_user_suite.py` 的 `CASE_NOTES` 目前仍写「`ipc_sem`/`ipc_shm` = argmask gap」（`ISS-249` 前的旧结论），须按本册诊断为真值改写（只改注释性质文本，**不改分类逻辑**）。

## 不做

- **不**改 musl 侧规避（如 `syscall()` → `__syscall`）当作「修复」；诊断若证明编译器符合契约、缺陷在 musl 用法 ⇒ **留问**，本册不擅自动 musl。
- **不**改语料 / 期望值 / `known-fail` 标签。
- **不**跑 `TESTCASES-047t` 动态档；**不**做 `long double`（`ISS-250` → M9）、`strptime`（`ISS-251` → `INFRA-087t`）、线程面（`ISS-252` → M9）。
- **不**动 `spec/` / `.tao/contracts/` / `contracts/`。

## 硬约束

1. 临时目录 `/tmp/opencode/LLVM-101t/`；命令在 workdir 内、**相对路径**；**禁**出界 `cd`；禁仓库内临时文件。
2. **不提交 git**（提交权归 architect）；**禁** `git add -A`/`.`；**禁** `git checkout`/`restore`/`stash` 还原（一律 `cp` + md5）。
3. 完成区与真实输出逐条对齐，留证捕**被检命令自身**退出码（禁 `cmd | tee` 吞码）；复杂命令输出留 `.work/log/llvm/`。
4. 只动任务书范围，越界须披露。
5. 失败保留现场并继续推进（自行处置：查证 / 绕行 / 有据重试并记录次数 / 登记后跳过）；**只在需用户语义裁定**时留问。
6. 用户裁定须把**原话**写入本任务书。
7. `check-patch-tree` / `check-index-blobs` / `check-source-state` 须绿（改 `components/**` 的补丁集完整性）。

## 完成区
**测试结果**：
**修改文件**：
**验收结果**：
**新发现/坑**：
**遗留问题**：

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
