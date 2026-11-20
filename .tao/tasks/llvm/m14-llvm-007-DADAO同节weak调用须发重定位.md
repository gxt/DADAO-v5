# m14-llvm-007: DADAO 后端：同节 weak 调用须发重定位（`shouldForceRelocation`）

**模块**：llvm
**项目里程碑**：M14
**依赖**：无（工具链组件在本仓）
**可并行分片**：否（改 LLVM 后端 + 重建安装根）
**预估**：3–5 h（含重建与内核 A/B 验证）
**档位**：大改（编译器后端 + 重装工具链）
**状态**：待验收

## 背景（根因已定位，证据见 `ISS-482`）

clang 23 在 DADAO 目标下，调用**同一节内的 `weak` 定义**时**不发重定位**，把位移本地固化；外部对象里的强定义因此永远无法覆盖它。

最小复现（已验证）：

- `a.c`：`__attribute__((weak)) void hook(int){}` + `void caller(int x){ if (x) hook(x); }`
- `b.c`：`volatile int marker; void hook(int x){ marker = 1; }`
- `clang --target=dadao-unknown-elf -O2 -c`（**不加** `-ffunction-sections`）⇒ `a.o` 里**没有** `hook` 的重定位，调用已固化为对 4 字节空体的位移；
- `ld.lld -r a.o b.o` ⇒ 符号表只剩强定义（GLOBAL），但调用仍指向空体（一条无名的 `ret rd0, 0`）；
- **加 `-ffunction-sections`**（弱定义进独立节）⇒ 发出 `R_DADAO_REL26`，lld 正解到强定义；
- 对照：x86_64 同场景（`-O0` 防内联）发 `R_X86_64_PLT32`；GCC+DADAO 不存在（无后端）。

**内核侧影响**：`m14-linux-045` 的 `arch_do_signal_or_restart`（强定义在 `arch/dadao/kernel/entry_common.c`）从未被调用——generic 空桩在 `kernel/entry/common.c` 同节内、调用被本地固化 ⇒ 退出循环自旋（A/B：带桩 22/29、删桩 43/43）。用户裁定：**不删通用空桩，修 LLVM**。

## 目标

1. **复现**：把最小复现落成 lit 用例（先红），断言「同节 weak 调用必须带重定位」；
2. **修复**：根因候选 = `llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp` 的 `DADAOAsmBackend` **未覆写 `shouldForceRelocation`**（对照 `X86AsmBackend`）。规则：**被引用符号是 linker-visible（非 local/temporary）时强制发重定位**；本地标签/临时符号仍走解析（避免无谓的重定位与代码膨胀）；
3. **回归**：既有 lit/CodeGen 用例全绿；`-ffunction-sections` 开关两种情形都正确；不改变已解析的本地跳转编码（`br.*` 到本地标签不得多出重定位）；
4. 组件补丁按 `docs/Process-01` 树形补丁集导出（`make_patch llvm` 幂等）。

## 验收（逐条贴真实 rc）

1. **最小复现先红后绿**：新增 lit 用例在修复前 FAIL、修复后 PASS（贴两次输出；可在临时树验证「先红」）；
2. **对象级证据**：修复后 `a.o` 含 `R_DADAO_REL26 hook`；`ld.lld -r a.o b.o` 的调用目标 = 强定义（给 `llvm-objdump` 输出）；
3. **不回归**：`make check-lit`（或对应 lit 子集）真实 rc；`check-instrinfo`/`check-gem5-decode`（如受影响）rc=0；
4. **内核 A/B（关键，证明修到了根上）**：重建工具链后，在 `m14-linux-045` 的树上**保留通用空桩**重新构建内核 ⇒ 探针 **51/51**、K0–K5 回归全绿（`045` 当前是 22/29 自旋）；同时确认 `vmlinux` 的 `exit_to_user_mode_loop` 调用目标 = arch 强定义；
5. **重建纪律**：`make install-host`（LLVM 增量：改一个后端文件 + 链接），记录耗时与 md5；安装根只由 `install-host` 写入；
6. 补丁树：`check-patch-tree` llvm 段 0 问题；`make_patch llvm` 二次 0 written。

## 约束

独立 `git worktree`；**不提交 git**；只改 LLVM 组件（`components/llvm-project/patches/**`）+ 必要时 lit 用例；**不改内核源码**（`045` 的通用 hunk 由 `045` 自己撤）；术语「寄存器组」；完成区不写具体 `.work/**` 路径；重建是长任务，落 PID/日志/`*_EXIT`。

## 完成区

**测试结果**：验收 6 项中 5 项全绿、第 5 项（内核 A/B）部分：探针 51/51 与调用目标均绿，K0–K5 的 12 个门/探针中 11 个绿、1 个红（K4 `k4_switch` S7，内核侧，见「遗留问题」）。`make check-lit` 180/180 rc=0；`check-inst-asm` PASS；证据脚本 `--with-kernel` 23 项自检全绿 rc=0。

**修改文件**：
- `components/llvm-project/patches/llvm/lib/Target/DADAO/MCTargetDesc/DADAOAsmBackend.cpp.patch`（实现改动：`evaluateFixup` 同节解析加「linker-visible ⇒ 发重定位」判据；注释重写）
- `tests/unit/llvm/lit/MC/DADAO/weak-same-section-reloc.s`、`local-branch-no-reloc.s`（新增）
- `tests/unit/llvm/e2e/weak_same_section_{a,b}.c` + `lit/weak_same_section.test`（新增，clang 复现）
- `tests/unit/llvm/lit/MC/DADAO/branch-range-{12,18}.s`（目标标签改本地：linker-visible 目标的越界改由链接期判，`contract-elf.md §3.2`）

**验收结果**：
1. 先红后绿：新 MC/E2E 用例在 pre-fix 工具链 `REL: expected string not found` rc=1，修复后 PASS；`local-branch-no-reloc` 两态均 PASS（断言非恒真）。
2. 对象级：`a.o` 含 `R_DADAO_REL26 hook`；`ld.lld -r` 后重定位仍在、符号表只剩强定义；最终链接 `call [rb0, 16]` → `0xffffff00004c` = 强定义 `hook`。
3. 不回归：`make check-lit` rc=0（180/180）；`make check-inst-asm` PASS（272/272 镜像、632 例）；本地标签 `.text` 逐字节相同（0 重定位）；同节 global 调用 0→6 条 REL26，但最终链接镜像逐字节相同。
4. 重建：`make install-host` rc=0、7.6 min；安装根 md5 clang `5ec67d1c…`、llvm-mc `ad34d612…`、lld `29058efd…`。
5. 内核 A/B（**保留通用空桩**）：探针 43/43（仅用例）、**51/51**（含 2 路注入）；`exit_to_user_mode_loop` 在 `0x200001e01e4` 的 `call`（imm −580004）目标 = `arch_do_signal_or_restart`（`0x20000152840`）。
6. 补丁树：`check-patch-tree` llvm-project 段 0 断言；`make_patch.py llvm-project` 二次 `0 written`。
7. K0–K5：k0/k1/k2/k3 rc=0；k4 fork 104/104、kthread 112/112、cow 86/86、stack 44/44；k5 syscall 104/104、clone 97/97、futex 174/174；**k4_switch 50/51（S7 红）**，见遗留问题。

**新发现/坑**：
- 根因确在 `evaluateFixup`：本版 LLVM **已无 `shouldForceRelocation` 钩子**（X86/RISCV 同样用 `evaluateFixup`）；该钩子绕过了 `ELFObjectWriter::isSymbolRefDifferenceFullyResolvedImpl` 的「同节 + STB_LOCAL」保守判据，把 STB_GLOBAL/STB_WEAK 同节符号全部就地折叠。修法＝该判据为 false 时 `return std::nullopt`（交回默认路径），不另造 binding 判据；7 类自定义 fixup 中只有 PCRel_12/18/24 与 REL12 走折叠分支，ABS12/ABS48/PCREL_HI/LO 本就总是重定位。
- 修复波及**全部** linker-visible 同节引用：内核只多 8 条重定位 = 7×`sched_clock`（`kernel/sched/build_utility.o`）+1×`release_thread`（`kernel/exit.o`），.text 仅差 23 B。`sched_clock` 由此从「弱 jiffies 回退」改绑 `kernel/time/sched_clock.c` 真实现——`CONFIG_GENERIC_SCHED_CLOCK` 要求的正是这个，即 ISS-482 同类 bug 的第二处实例。
- 诊断要诀：`ld -r`（kbuild 的 `build_utility.o`）对**弱符号引用保留**重定位（后续强定义可覆盖），对已折叠的立即数无能为力。

**遗留问题**：
- **K4 `k4_switch` S7（唯一红项，内核侧）**：隔离副本同一源码/配置下旧工具链 52/52、新工具链 50/51；差异只有上述 8 条重定位。S7 在 `Run /init.musl` 后 `kernel/fork.c:725 BUG_ON(mm == &init_mm)` panic——长期被同一条静默折叠掩盖的内核缺陷，`sched_clock` 绑定改正后暴露。**本任务不改内核源码**，需内核任务（045/021）处置或用户裁定。
- `check-patch-tree` 全仓 rc=1（46 条断言）全部来自 `linux`（045 在途 99 vs 基线 96）与 `chipyard`（m16-chipyard-008 在途），llvm-project 段 0 问题。

## 审阅记录

### 第 1 轮 engineer 自审
逐行审 `DADAOAsmBackend.cpp` 改动与 4 个测试载体，findings 与处置：

| finding | 处置 | 改了什么 | 复验证据 |
|---|---|---|---|
| F1 判据自造 binding 判据的风险 | ✅已修 | 直接用 `Asm->getWriter().isSymbolRefDifferenceFullyResolvedImpl(*Add,F,false,true)`，与默认路径同一判据 | `check-lit` 180/180；本地标签 `.text` 逐字节相同 |
| F2 同节 global 调用新增重定位是否改变代码 | ✅已修（改为可证） | 加 `global-link-identical` 检查：`-O0` 同节 global 调用 0→6 条 REL26，最终链接镜像逐字节相同 | 证据脚本 `global-link-identical want=0 got=0` |
| F3 ABS12/ABS48/PCREL_HI/LO 是否漏覆盖 | ❌不修（已核实无折叠） | 它们走 `!IsPCBranch && !IsLdstPCRel` 分支或恒 `return false`，改动不影响；测试补 REL12/ABS12 断言 | `weak-same-section-reloc.s` REL/ABS12 通过 |
| F4 `branch-range-{12,18}` 因新语义变红 | ✅已修 | 目标标签改本地标签，并注明 linker-visible 目标改由链接器按 `§3.2` 判（`mcmodel.test` 已覆盖） | 两例 rc=0 |
| F5 断言是否恒真 | ✅已修 | 保存 pre-fix 工具链二进制，脚本内置「旧工具链 ⇒ 必红、本地例 ⇒ 必绿」自检 | `inject-old-toolchain-red want=1 got=1`；`restore-old-toolchain-green want=0 got=0` |
| F6 K0–K5 全绿是否可达 | ⏸延后（需裁定） | 已定位到 8 条重定位（7 `sched_clock` + 1 `release_thread`），内核侧缺陷，见遗留问题 | 隔离副本 A/B：旧 52/52、新 50/51 |

判决：代码与工具链侧 findings 全部处理完毕；F6 属内核源码范围（本任务禁止改动），按「需用户语义裁定」留问。

### 第 1 轮 reviewer 验收（2026-11-21，大改档，约 17 min）

**重跑（全部我自己执行，退出码取命令自身 `echo $?`，不采信完成区转述）**
1. 运行期证据目录内的 `run.sh` → `run.sh: PASS (21 checks)`，exit 0（29 s）；同场 `make-patch-2-written want=0 got=0 rc=0`、`check-patch-tree` llvm 段 0 断言。
2. `make check-lit` → `Total Discovered Tests: 180 / Passed: 180 (100.00%)`，exit 0。
3. `make check-inst-asm` → `272/272 镜像通过（272 个 id；链例 + 故障链 632 例）`、`check-inst-asm: PASS`，exit 0（与 master 现状一致）。
4. `make check-instrinfo` → `Result: 0 errors`，exit 0。
5. master 树 `JOBS=32 make linux-vmlinux` → `make_vmlinux: PASS`、`check-code-range: PASS`，exit 0。
6. master 内核 + 共享修复版安装根（`clang` md5 `5ec67d1c…` 与完成区一致）：`k4_switch_probe` → `k4_switch_probe: 76/76 passed`，exit 0（24 条 `INJECT` 断言全 PASS、无 `[FAIL]`）；`k5_futex_probe` → `k5_futex_probe: 174/174 passed`，exit 0。
7. `exit_to_user_mode_loop` 调用目标（我自跑 `llvm-objdump -d/-t` 现场解析）→ `arch=0x200001e26d4 calls=…, 0x200001e2784->0x200001e26d4, … match=1`，exit 0（地址与完成区不同仅因本轮 fresh 构建的时间戳 banner 平移，绑定判定相同）。
8. 写入本记录前 `make check-knowledge-refs` → `PASS (0 具体引用; 0 悬空)`，exit 0；**写入后复跑同样 rc=0**。

**可达 FAIL（我自注入，只用临时目录符号链接换掉工具链，未动共享安装根、未改被测文件）**：`TOOLBIN=<旧工具链目录>` 重跑**同一** `run.sh` → exit 1、`run.sh: 4 check(s) FAILED`（`lit-new-vectors`、`a-o-rel26-hook`、`ld-final-call-target-hook`、`global-calls-relocated`），而 `restore-old-toolchain-green`、`local-text-identical`、`ffunction-sections` 仍绿 ⇒ 每条断言有可达 FAIL 路径且非恒真；旧工具链下 `weak-same-section-reloc.s`、`weak_same_section.test` FAIL、`local-branch-no-reloc.s` PASS（先红后绿 + 本地例两态都绿）。

**约束逐条**：① 修法回到共享判据——补丁调用 `isSymbolRefDifferenceFullyResolvedImpl(*Add, F, /*InSet=*/false, /*IsPCRel=*/true)`，与 `MCAssembler.cpp` 默认路径 `(*Add, F, false, true)` 逐字一致（头文件声明顺序即 `InSet, IsPCRel`），**未自造 binding 规则**；本地标签仍折叠（`.text` 逐字节相同、`local-branch-relocs=0`）。② `branch-range-{12,18}` 改本地标签不削弱覆盖：linker-visible 目标的越界改由链接期判，`mcmodel.test` 的 `REL26: relocation R_DADAO_REL26 out of range` 仍在 180 内。③ 范围：`git status -uall` = 任务书 + `DADAOAsmBackend.cpp.patch` + 2 个 `branch-range` + 5 个新测试载体，**无内核源码改动**；验收前后快照逐行一致、9 个目标文件 md5 相同（我未改任何被测文件）。④ 未提交 git；⑤ 记录无具体运行期路径。

**Finding（非阻断，交 architect 收尾处置）**：完成区「证据脚本 `--with-kernel` 23 项自检全绿」本轮**未重跑**——该节依赖 `m14-linux-045` 分支才有的探针脚本（我在 master 树实测 rc=2、`can't open … m45_entry_probe.py`），且会把共享内核源切到 045 在途补丁集，判据外、不代跑他人在途工作树；我读到的运行期日志与完成区转述一致（`run.sh: PASS (23 checks)`、`m45_entry_probe: 51/51 passed`、`match=1`）。完成区「探针 51/51」是 045 探针口径，本轮派单判据的 k4 76/76、k5 174/174 已由我独立重跑通过。

**判决**：**Accepted** —— 7 项核心判据与全部硬约束在我自己的重跑下通过；架构师仍需终审。
