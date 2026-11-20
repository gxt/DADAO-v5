# m14-linux-046: 信号帧与投递（`rt_sigframe` / `setup_rt_frame` / `rt_sigreturn` / `force_sig`）

**模块**：linux
**项目里程碑**：M14
**依赖**：`m14-linux-045`（工作循环接线）；`m14-linux-022`（内核 `struct pt_regs` 四组全量）；本任务由 `m14-linux-027` 拆出
**可并行分片**：否（linux 单写者）
**预估**：6–8 h
**档位**：大改
**状态**：待开始

## 背景（盘点结论，用户 2026-11-20 批准）

`m14-linux-039 信号/退出 与主流 ISA 差异盘点`：**信号机制整体不存在**——

- 无 `kernel/signal.c`；`rt_sigframe` / `setup_rt_frame` / `restore_sigcontext` / `handle_signal` 链 **7 个符号全树 0 命中**；
- `sys_rt_sigreturn` 仍是 `-EINVAL` 桩（`kernel/syscalls.c:44-46`）；
- `force_sig` / `send_signal` / `sigaltstack` 全缺。

## 已裁定（用户 2026-11-20，**已关闭，不再询问**）

**帧 2048 B，四组各 64 槽；`rd` 组第 0 槽存 `status`、`rb` 组第 0 槽存 `ip`；C 用匿名 union 表达。**

```c
struct pt_regs {
	union {                                  /* rd 组：第 0 槽不是寄存器（`ld` 到它 ILLI） */
		unsigned long rd[64];
		struct { unsigned long status; unsigned long rd_rest[63]; };
	};
	union {                                  /* rb 组：第 0 槽在硬件上就是只读 IP */
		unsigned long rb[64];
		struct { unsigned long ip;     unsigned long rb_rest[63]; };
	};
	unsigned long ra[64];                    /* ra[0] = {RACNT, MRPTR} 元数据，原样保留 */
	unsigned long rf[64];                    /* rf[0] = FCSR */
};
```

- 尺寸 `4 × 64 × 8 = **2048 B**`（`_Static_assert` 改 2048）；
- **模式位：`status` 低 4 位**；`spec/DADAO-12 §1` 只定义 2 位（0b00 user / 0b01 jail / 0b10 supv / 0b11 hypv），**高 2 位留扩展**；`user_mode(regs) = ((regs->status & 0xF) <= 1)`；**bit 4–63 保留 0**（用户「以后再说」）；
- `asm-offsets.c` 的 `PT_IP`/`PT_STATUS` 保持 `offsetof(pt_regs, ip)`/`offsetof(pt_regs, status)`（匿名 union 成员可直接取）⇒ **12 处 asm 与 48 处 C 引用零改动**；
- **uapi 与 musl 同步更新**（用户原话）：`uapi/asm/ptrace.h` 的 `user_regs_struct` 与 musl 的 `sigcontext`/`mcontext_t` 按 2048 B 同形状改；**musl 侧作为本任务的连带项**（组件各自提交，不跨写者）。

## 要做

1. `kernel/signal.c`：`rt_sigframe`/`struct sigcontext` 布局、`setup_rt_frame()`、`restore_sigcontext()`、`handle_signal()`、`get_signal()` 接线；
2. `sys_rt_sigreturn` 真实现（返回用户态时按帧恢复 4 组寄存器 + `ip`/`status`）；
3. `force_sig` / `complete_signal` / `do_signal` 的最小闭环（用户进程能收到信号并按默认动作终止）；
4. `sigaltstack` 与 `SA_RESTORER`（若本端口无 vDSO，按 `SA_RESTORER` 约定或 `HAVE_GENERIC_VDSO` 二选一，写清依据）；
5. 探针 `tools/linux/k5_signal_probe.py` 的帧往返 case（原 `027` 的 S2 移到这里）。

## 验收（逐条贴真实 rc）

1. **帧往返**：装 handler → 触发信号 → `rt_sigreturn` 恢复，**`ra` 栈逐位相同**（含 `RACNT`/`MRPTR`）、`rf0` 架构值、`ip`/`rb1`/callee-saved 哨兵值一致；
2. **默认动作**：无 handler 时信号按默认动作终止进程（`SIGSEGV` 的投递归 `m14-linux-027`）；
3. **不回归**：k0–k5 全绿（同 045 的清单）；
4. **可达 FAIL ≥3 路**：① 帧不保存 `ra` 栈 ⇒ 帧往返红；② `rt_sigreturn` 不恢复 `rf0` ⇒ 红；③ `force_sig` 不置 `TIF_SIGPENDING` ⇒ 信号不到（`cp`+md5 还原 + 重建）；
5. `check-patch-tree` linux 段 0 问题；合并态（`Process-07 §5a`）。

## 完成区

（待填）
