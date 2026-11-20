# m14-llvm-007: DADAO 后端：同节 weak 调用须发重定位（`shouldForceRelocation`）

**模块**：llvm
**项目里程碑**：M14
**依赖**：无（工具链组件在本仓）
**可并行分片**：否（改 LLVM 后端 + 重建安装根）
**预估**：3–5 h（含重建与内核 A/B 验证）
**档位**：大改（编译器后端 + 重装工具链）
**状态**：待开始

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
