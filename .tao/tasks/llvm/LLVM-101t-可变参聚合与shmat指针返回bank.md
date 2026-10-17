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
**测试结果**：证据脚本 `.work/evidence/LLVM-101t/run.sh` **14/14 PASS（rc=0）**，含 2 处对象级注入（`semctl.o`/`shmat.o` 换回修前对象 ⇒ 对应 oracle `[FAIL]` ⇒ `cp`+md5 还原 ⇒ 回绿）；`TESTCASES-047t` 静态档 `pass 303 / fail 6 / known-fail 3 / blocked 25`（`discovered 367 / excluded 30 / total 337`），**无回归**（原 301 条 pass 逐条比对全在；唯一两处类别变化 = `functional/ipc_sem`、`functional/ipc_shm` fail→pass）；CodeGen lit **31/31**；`047t` 重跑 suite 自身 rc=1（余 6 条 fail 全属他册：`strptime` ⇒ `INFRA-087t`、5 条 `long double` ⇒ `ISS-250`）。
**修改文件**：`components/llvm-project/patches/clang/lib/CodeGen/Targets/DADAO.cpp.patch`、`components/llvm-project/patches/llvm/lib/Target/DADAO/DADAOISelLowering.cpp.patch`（由 `.work/source/llvm-project` 按 E1/E3 导出，`series` 仍 78）、`components/llvm-project/changelog.md`、`tools/testcases/run_libc_test_user_suite.py`（仅 `CASE_NOTES` 文本）、`.tao/knowledge/issues.yaml`（`ISS-256` `closed`/`resolved_by: LLVM-101t` + 处置注）、本任务书 + `.work/evidence/LLVM-101t/**`。
**验收结果**：**诊断 A**：偏离侧 = **callee 的 clang `DADAOABIInfo::EmitVAArg`**——它继承 `DefaultABIInfo` 的版本，而后者调**非虚** `DefaultABIInfo::classifyArgumentType`（任何聚合 ⇒ 间接），与调用点按 `§6.4` 的「≤64 B 按值」自相矛盾（修前 `semctl.o` 在 `%sw.bb` 里 `ld.o rd5,[rb1,120]` 后 `rd2rb {rb4},{rd5}` + `ld.o rd5,[rb4,0]` = 把槽值当指针解引用）；**诊断 B**：偏离侧 = **后端尾调用 lowering**——尾跳原样转发返回寄存器，`__syscall_ret` 的 `i64` 落在 `rd8`、`shmat` 的 `void*` 应在 `rb8`（修前 `shmat.o` 结尾 = `rd2rd {rd16},{rd8}` + `jump [rb0,__syscall_ret]`，全程无 `rb8` 落值）；契约条款 = `§6.4`+`§5`（A）/`§4.4`+`§4.6`（B）。修后 `shmat` = `call [rb0,__syscall_ret]` + `rd2rb {rb8},{rd8}` + `ret`；`semctl` 的 `va_arg` = 槽值直读。复现 A `mode=666` rc=0（修前 `semctl: Bad address` rc=1）、B `p=0x2aaaaaaab000` + `shmdt` rc=0（修前 `p=0x40554`、`shmdt: Invalid argument` rc=5）。独立 oracle：`mode`=0666 由 `semget` 创建参数独立得出；`p` 判据 = `shmdt` rc=0 且不落在 guest `/proc/self/maps` 的 `[stack]`（修后 `in_stack=0`）。门控（各留自身 rc）：`check-instrinfo` 0、`check_lit_gen` 0、`check-patch-tree` 0（**177**，2 份改、无增删）、`check-syscall-abi` 0（69/69）、`check-index-blobs` 0、`check-source-state` 0、`check-no-residue` 0、`check-tasks` 0、`check-knowledge-refs` 0、`check-component-changelog` 0、`check_issues` 0（57 open / 22 closed）、`make check`（L1）**0**（33s，`repository checks (L1): PASS`）、`ninja -C .work/build/llvm clang llc` 0（终版 3m38s；首轮 `clang` 4m22s / `llc` 1m26s）。
**新发现/坑**：① `DefaultABIInfo::EmitVAArg` 与「覆写了 `classifyArgumentType`」的 target 天然不自洽（`classify*` 非虚）——任何 target 只要改聚合/窄类型分类，就必须同步 `EmitVAArg`；② 尾调用路径**不可能**做返回位置搬运（尾跳后无本函数代码），资格判据必须含返回位置，而不只是实参；③ `GetReturnInfo` **不置 pointer 位**（`SelectionDAGBuilder::visitRet` 才按返回 IR 类型补），据此判 bank 会静默错判（本册踩到并已修）；④ `make build-musl` **不能**用构建树编译器：`build_musl.py` 把安装根**硬塞** PATH 且 toolchain stamp 只盯安装根 ⇒ 无 `install-host` 时只能另建 `/tmp` 副本（见遗留）。
**遗留问题**：① **未跑 `install-host`**（按下发要求）⇒ 安装根仍是旧工具链，`047t` 重跑的 musl 用 `.work/source/musl` 的副本在 `/tmp/opencode/LLVM-101t/musl` 由**构建树 clang** 同参数重建（`libc.a` 18:08 新于 clang）；注入用的**修前对象**已归档到 `.work/evidence/LLVM-101t/prefix-obj/`（故 `make build-musl` 之后注入仍可复现）；**待主会话 `install-host` 后须复跑 A/B + `047t`**（预期同为 303/6/3/25；届时 `run.sh` 的 `control-prefix-*` 两项会因旧树被刷新而报 FAIL，属预期，需以归档对象/历史 JSON 为对照）；② **`ISS-243`（i32 窄返回 canonical 化）未并入**：改点在 clang `classifyReturnType`（补 `signext`/`zeroext`），非本册的尾调用返回路径，且波及**每个 i32 返回函数**的 callee/caller 代码生成、验收需 L2/L3 与全量重生成 ⇒ 本册允许的门控覆盖不到，另册处置；③ `CASE_NOTES` 里 `ipc_msg`/`socket` 仍留「argmask gap」历史叙述（两例现已 pass，注记属已消解根因，未在本册范围）；④ 未跑 L2/L3（按下发要求），`make check`(L1) 见下；⑤ 任务书 `**状态**` 按下发要求**未改**。

## 审阅记录

#### 第 1 轮 engineer 自审
（工程师自审 subagent 的意见、问题、判决及 finding 处置）

**审查方式**：全局 `subagent_depth=1` ⇒ 无嵌套子代理，采用**自主逐行审查**（两处改动逐行 + 逐条核对契约 `§4.4/§4.6/§5/§6.4`）；真实执行证据见 `完成区` 与 `.work/evidence/LLVM-101t/run.sh`（14/14）。

| finding | 处置 | 改了什么 | 复验证据 |
|---------|------|---------|---------|
| F1 尾调用返回位置比较**看不到 pointer bank**：`GetReturnInfo` 只置 `InReg/SExt/ZExt`，不置 pointer 位 ⇒ 第一版判据把 `ptr` 返回也判成 `rd8`，与 callee 的 `rd8` 相同 ⇒ 判据恒真、T 修复无效（实测 `shmat` 仍 `jump`） | ✅已修 | 照 `SelectionDAGBuilder::visitRet` 补：返回类型是 pointer 时对 `SelfOuts` 逐项 `Flags.setPointer()`（并加注释说明出处，避免再漂移） | `shmat` 反汇编改为 `call [rb0,__syscall_ret]` + `rd2rb {rb8},{rd8}` + `ret`；`run.sh` 的 `asm-shmat-bank-move`/`repro-B`/`oracle-B`/`inject-B` 全 `[PASS]` |
| F2 只比 `LocReg` 过宽：`i32`/`i64`、`SExt`/`ZExt`/`AExt` 的尾转会把**未 canonical 化**的值原样交给调用者（`§4.4 C5`「caller 不截断」） | ✅已修 | 判据扩为 `LocReg` + `LocVT` + `LocInfo` 三元组逐一相等（`Eligible` 短路，任一不等即降级） | CodeGen lit **31/31**（含 `tail-call-lowering.ll` 的 5 个尾跳断言、`musttail` 拒绝例）⇒ 未过严降级既有向量；`047t` 无回归 |
| F3 A 侧若用 `EmitVAArgInstr` + DADAO 分类（`CreateVAArg(ap, {i64,…})`）会对 **>8B 聚合**产生多结果 `VAARG`，而后端 `LowerVAARG` 只处理单结果 ⇒ 断言/错值（把「静默错」换成「崩」） | ✅已修（改选实现） | 改用 `CodeGen::emitVoidPtrVAArg`（void* va_list 目标的标准路径）：≤64 B 按值读槽、>64 B 读指针再解引用、大端 `ForceRightAdjust` 与后端 `LowerVAARG` 的 `8-Size` 口径一致；**非聚合仍走 `DefaultABIInfo`**（缩放/窄标量路径零改动） | `semctl.s` 的 `%sw.bb` 块无 `rd2rb` 解引用（`asm-semctl-vaarg-direct`）；`repro-A`/`oracle-A`/`inject-A` `[PASS]`；`047t` 其余 336 例不变 |
| F4 注入必须「可达 FAIL」且不得用 `git checkout` 还原；对象级注入若对象本身没变会变成恒真 | ✅已修 | 注入用**修前真实对象**（`.work/source/musl/obj/src/ipc/*.o`）+ `ar r` 换入**拷贝**的 `libc.a`；先校验 `md5(修前对象) != md5(修后对象)` 才允许注入；还原 = `cp` 回原始归档 + md5 对账 + 重链重跑 | `inject-A`（`rc=1 semctl: Bad address`）、`inject-B`（`rc=5 shmdt`）⇒ 还原后 `rc=0`、md5 与注入前一致（`8985088e…`），同次前台闭合 |
| F5 证据脚本把 `047t` 的 `303/6` 写死（属「计数写死」） | ✅已修 | 改为**由基线 JSON 现场派生**：`pass == 基线pass+2`、`fail == 基线fail-2`、`known-fail`/`blocked` 不变、`pass` 集无回归、类别变化恰 2 条 | `run.sh` 的 `047t-static-303-6-3-25` 打印 `counts=… (base {'pass':301,'fail':8,'known-fail':3,'blocked':25})` |
| F6 `make build-musl` 无法用构建树编译器（脚本把安装根硬塞 PATH、stamp 只盯安装根）⇒ 未 `install-host` 时 047t 的 musl 来源须如实交代 | ✅已修（披露 + 替代证据） | 用 `.work/source/musl` 的**同源副本**在 `/tmp/opencode/LLVM-101t/musl` 由**构建树 clang**同 configure 参数重建；证据脚本第 1/2 项显式断言 `clang` 新于两处源码、`libc.a` 新于 `clang` | `toolchain-newer-than-sources`/`musl-built-by-new-clang` `[PASS]`；`047t` 的 `--musl` 指向该树（完成区遗留 ① 已登记 `install-host` 后复跑） |

**未修项**：F1–F6 全部 ✅已修；无 ⏸/❌。**判决**：可交独立验收（`ISS-243` 未并入属**范围判断**，已写入完成区遗留 ②，非缺陷遗留）。

#### 第 1 轮 reviewer 验收
（审查者独立验证的重跑记录、约束核验、判决）
