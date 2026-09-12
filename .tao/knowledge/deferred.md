# 暂缓 / 备忘（Deferred / Backlog）

记录**各模块**中"知道但当前不做 / 被移除 / 属后续阶段 / 无法确定"的内容，避免遗忘。按模块分节；新增内容追加到对应模块下。

> 本文件只记录**结论性备忘**，不是任务书；正式工作仍走 `.tao/tasks/`。

## spec

- **ISA 归一化完成里程碑（原 `SPEC-005m`，已移除）**：曾用独立 `m` 标记 `SPEC-002t`+`003t` 完成。因 `k`↔`m` 一一对应规则移除；其意义由 `SPEC-002t`/`003t` 的完成 + `SPEC-009m`（M1 spec 里程碑）覆盖。
- **`SPEC-002t`/`003t` 产出需重新生成**：`contract-isa.md`、`verif/opcodes.yaml` 在 spec 重排后**重新生成**；旧文件暂作参考。
- **ABI 合约（`SPEC-004t`）的 M2 / CodeGen 内容**：完整调用约定（参数寄存器分配、栈帧、prologue/epilogue）服务 **M2 BasicCodeGen**，非 M1；M1 只需 test machine 所需的最小 ABI 事实（SP=rb1 等）。→ 待定：`SPEC-004t` 是否收窄到 M1 最小事实、把完整 ABI 后移。
- **ABI `[OPEN]` 项**：`rd1`/`rb3`/`rb4` 的 callee-saved 分类（wiki 为 `-`）、窄返回值扩展规则、多返回值（wiki 自相冲突）——不得当规范性要求。
- **Object ABI（`SPEC-005t`）**：`EM_DADAO` 注册状态（未注册 upstream，project-custom）、`e_flags` 命名空间策略、**M1 是否用 target linker（LLD）**。
- **Spec 冻结（`SPEC-008t`）**：`impact matrix` 是否覆盖 M1 之外的实现目标（CodeGen/gem5/Sail）——M1 只需覆盖 M1 相关。

## infra

（暂无）

## testsuite / llvm / qemu / verif

（待各模块规划时补充）
