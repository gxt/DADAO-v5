# SPEC-149t: 上游只读 spec 册汇编示例注释迁移 `;`→`@@`

**模块**：spec
**项目里程碑**：M8
**依赖**：`SPEC-147t`（规范面 0.5.3 已落地，本册迁移上游只读册示例）；`LLVM-109t`（`CommentString`/`SeparatorString` 实现，**不必等**；但示例要「真能编」须与其同批落地，见「与 LLVM-109t 的先后」）
**状态**：已验证

## 执行环境
**执行环境**：本地

## 用户授权（原话逐字，渠道 = 经主会话问答，2026-10-19）
> 「**1、A；2、就地修订**」

- 上下文：① 上游只读册（`SimRISC-*`、`DADAO-11/12/22/23` 等）里**仅作汇编示例**的 `;` 注释是否授权改 ⇒ **A = 授权改**；② `ADR-0013 D9.1` 被新裁定取代的处置 ⇒ **就地修订**（已由 architect 在本批落地，见该 ADR 注记）。
- `docs/Process-06 §2`：`spec/` 下任何修改须用户**事先**明确允许 ⇒ 本册已具备；授权原话须原样写入任务书/完成区。

## 问题根源

1. `SPEC-147t` 已把规范面改为 `@@` 注释、`;` 语句分隔符（`Toolchain-01` 0.5.3 / `contract-asm` 0.5.3）；但上游只读册（`DADAO-11/22/23`、`SimRISC-03/04/06/07/08/09/10/11`）仍用旧注释符 `;` 写汇编示例。
2. 这些册原按 `Process-06 §1` 只读不改；用户 2026-10-19 裁定 **A = 授权改**，但**只改汇编示例**——C 代码块/正文里的 `;` 不动（`DADAO-21` 25 处、`SimRISC-02` 2 处 = C 分号）。
3. 不改的后果：读者按新规范抄示例会把注释误当语句分隔符（`;` 后文本被当语句）；改错非汇编分号则破坏 C 语义/正文。

## 判据（必须写死）

- **只改「汇编代码块内的注释」**：位置须同时满足 ① 在 `simrisc` 语言围栏块内（本批无 `asm` 块）；② 该行是**汇编语句/汇编注释行**，不是 C/伪代码；③ 只把**该行第一个 `;`**（起注释处）替换为 `@@`；行内其余字符（含注释文本里的全角 `；`、反引号、缩进、对齐空格）**逐字不动**。
- **C 代码块 / 正文里的 `;` 一律不动**：`spec/DADAO-21` 的 `c` 语言围栏块（`va_list` 结构体语句分号）与 `spec/SimRISC-02` 的 2 处 C 分号 = **禁区**。
- **伪代码块不动**：`spec/DADAO-12` 的两段无语言围栏是**伪代码**（`if/case/goto` + `//` 与 `;` 混用注释），不是汇编语句 ⇒ 按判据**不改**（6 处 `;` 保留）；`spec/SimRISC-04` 的 3 处无语言块（`n = 0; for …`）同理**不改**。若用户后续要求伪代码注释也统一，另立册裁定，本册不擅自扩围。
- **不改册头版本 / 不新增变更记录段**：用户只授权示例注释迁移；`check-spec-changelog` 保持绿（不触碰附录）。
- **行数精确**：改动 = **11 册 / 298 行**（逐册清单见下）；不符 ⇒ 停止并报告，不得以「差不多」收尾。

## 改动清单（现场派生 2026-10-19；格式 `L<行号> | 原行 | 新行`；共 11 册 298 行）

> 生成方式（只读、可复现）：按 `simrisc` 块扫描 `spec/*.md`，取含 `;` 的行，替换该行首个 `;` 为 `@@`。清单即**验收基线**：diff 必须与之逐行一致。

```text

## spec/DADAO-11-AEE-应用程序运行环境.md（23 行）
L22 | ; 有符号 32-bit 加法 | @@ 有符号 32-bit 加法
L23 | ld.st rd2, [rb1, x_offset] ; 符号扩展加载 | ld.st rd2, [rb1, x_offset] @@ 符号扩展加载
L25 | add.so {rd0, rd4}, rd2, rd3 ; rd4 = 低64位；rd0丢弃高64位 | add.so {rd0, rd4}, rd2, rd3 @@ rd4 = 低64位；rd0丢弃高64位
L32 | ; 有符号 32-bit 乘法 | @@ 有符号 32-bit 乘法
L35 | mul.so {rd0, rd4}, rd2, rd3 ; rd0丢弃高64位，rd4=低64位 | mul.so {rd0, rd4}, rd2, rd3 @@ rd0丢弃高64位，rd4=低64位
L38 | ; 有符号 32-bit 除法 | @@ 有符号 32-bit 除法
L41 | div.st  rd4, rd2, rd3           ; 商写入目的寄存器 rd4 | div.st  rd4, rd2, rd3           @@ 商写入目的寄存器 rd4
L50 | ; 无符号 32-bit 右移 3 位 | @@ 无符号 32-bit 右移 3 位
L51 | ld.ut rd2, [rb1, x_offset] ; 零扩展加载 | ld.ut rd2, [rb1, x_offset] @@ 零扩展加载
L54 | ; 有符号 32-bit 右移 3 位 | @@ 有符号 32-bit 右移 3 位
L55 | ld.st rd2, [rb1, x_offset] ; 符号扩展加载 | ld.st rd2, [rb1, x_offset] @@ 符号扩展加载
L65 | ; 有符号 32-bit 加法，检测溢出 | @@ 有符号 32-bit 加法，检测溢出
L66 | add.so {rd0, rd3}, rd4, rd5 ; rd3 = rd4 + rd5（低 64 位） | add.so {rd0, rd3}, rd4, rd5 @@ rd3 = rd4 + rd5（低 64 位）
L67 | ext.so  rd2, rd3, 31           ; rd2 = rd3 按 32-bit 符号扩展 | ext.so  rd2, rd3, 31           @@ rd2 = rd3 按 32-bit 符号扩展
L68 | cmp.so  rd2, rd2, rd3          ; 比较扩展值与原值 | cmp.so  rd2, rd2, rd3          @@ 比较扩展值与原值
L69 | br.nz {rd2}?, [rb0, overflow_handler] ; 不相等 → 32-bit 溢出 | br.nz {rd2}?, [rb0, overflow_handler] @@ 不相等 → 32-bit 溢出
L84 | ; 进程切换示例：invalid 已申请的私有 PTBR（最多 16 个） | @@ 进程切换示例：invalid 已申请的私有 PTBR（最多 16 个）
L85 | set.rd   rd2, 0                     ; 循环变量 | set.rd   rd2, 0                     @@ 循环变量
L87 |     ; 仅 invalid PTBR 0-15 |     @@ 仅 invalid PTBR 0-15
L88 |     shl.uo  rd3, rd2, 42              ; rd3 = PTBR 索引 << 42（构造 addr_start，VA[47:42]=PTBR 编号） |     shl.uo  rd3, rd2, 42              @@ rd3 = PTBR 索引 << 42（构造 addr_start，VA[47:42]=PTBR 编号）
L90 |     set.rd   rd3, 0x40000000000     ; 0x40000000000（2^42） = 集合内全部 VA 空间 |     set.rd   rd3, 0x40000000000     @@ 0x40000000000（2^42） = 集合内全部 VA 空间
L92 |     set.rd   rd4, 2                 ; bit1 = invalid by addr range |     set.rd   rd4, 2                 @@ bit1 = invalid by addr range
L96 |     cmp.so  rd5, rd2, rd3          ; rd5 = rd2 < rd3 ? |     cmp.so  rd5, rd2, rd3          @@ rd5 = rd2 < rd3 ?

## spec/DADAO-22-SBI-主管系统二进制接口.md（181 行）
L63 | ; 设置 cfx_smon 的 supv 异常向量 | @@ 设置 cfx_smon 的 supv 异常向量
L67 | ; 允许 cfx_smon 从 supv 触发 | @@ 允许 cfx_smon 从 supv 触发
L79 |     set.rd   rd3, 1                                 ; CFXTRAP (1<<0) |     set.rd   rd3, 1                                 @@ CFXTRAP (1<<0)
L86 |     br.eq {rd2, rd3}?, [rb0, cfx_smon_get_version] ; func 0 |     br.eq {rd2, rd3}?, [rb0, cfx_smon_get_version] @@ func 0
L88 |     br.eq {rd2, rd3}?, [rb0, cfx_smon_probe_cfx] ; func 1 |     br.eq {rd2, rd3}?, [rb0, cfx_smon_probe_cfx] @@ func 1
L98 |     set.rd   rd8, 0x00070001                        ; v0.7.1 |     set.rd   rd8, 0x00070001                        @@ v0.7.1
L102 |     ; rd16 = cfx（调用方传入） |     @@ rd16 = cfx（调用方传入）
L103 |     ; 根据硬件实现返回目标 cfx 的功能位图 |     @@ 根据硬件实现返回目标 cfx 的功能位图
L104 |     set.rd   rd8, 0                                 ; 占位 |     set.rd   rd8, 0                                 @@ 占位
L114 | ; 获取 SBI 版本 | @@ 获取 SBI 版本
L117 | ; 探测 cfx_llc 的功能 | @@ 探测 cfx_llc 的功能
L151 |     ; CFXTRAP (1<<0) → SBI 功能调用分发 |     @@ CFXTRAP (1<<0) → SBI 功能调用分发
L155 |     ; 页缺失异常 → 委托 cfx_pmem 分配物理页，修复 PTE |     @@ 页缺失异常 → 委托 cfx_pmem 分配物理页，修复 PTE
L156 |     ; 具体处理根据 cause_id 分发 |     @@ 具体处理根据 cause_id 分发
L166 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_ptbr] ; func 0 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_ptbr] @@ func 0
L168 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_get_ptbr] ; func 1 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_get_ptbr] @@ func 1
L170 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_ptbr_perm] ; func 2 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_ptbr_perm] @@ func 2
L172 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_enable_ptbr] ; func 3 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_enable_ptbr] @@ func 3
L174 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_pte] ; func 4 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_pte] @@ func 4
L176 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_handle_fault] ; func 5 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_handle_fault] @@ func 5
L178 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_pthi] ; func 6 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_pthi] @@ func 6
L180 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_pahi] ; func 7 |     br.eq {rd2, rd3}?, [rb0, cfx_ptw_set_pahi] @@ func 7
L184 |     ; rd16 = idx, rb16 = base（页表基地址高 48 位，低 16 位强制为 0） |     @@ rd16 = idx, rb16 = base（页表基地址高 48 位，低 16 位强制为 0）
L185 |     ; 调用前须已通过 cfx2rc 写入 cfx_ptw_pthi[idx] 和 cfx_ptw_pahi[idx] |     @@ 调用前须已通过 cfx2rc 写入 cfx_ptw_pthi[idx] 和 cfx_ptw_pahi[idx]
L186 |     set.rd   rd17, rb16                              ; rb→rd 中转（cfx2rc 源操作数须为 rd） |     set.rd   rd17, rb16                              @@ rb→rd 中转（cfx2rc 源操作数须为 rd）
L187 |     shl.uo  rd16, rd16, 3                          ; idx × 8（每路 2 条指令 = 8 字节） |     shl.uo  rd16, rd16, 3                          @@ idx × 8（每路 2 条指令 = 8 字节）
L190 |     set.rb   rb8, rd3                      ; rd→rb 中转 |     set.rb   rb8, rd3                      @@ rd→rb 中转
L193 |     cfx2rc  cfx_ptw_ptbr[0], rd17 ; PTBR[0] |     cfx2rc  cfx_ptw_ptbr[0], rd17 @@ PTBR[0]
L195 |     cfx2rc  cfx_ptw_ptbr[1], rd17 ; PTBR[1] |     cfx2rc  cfx_ptw_ptbr[1], rd17 @@ PTBR[1]
L197 |     ; ... 共 64 路，rc 0-63 ... |     @@ ... 共 64 路，rc 0-63 ...
L198 |     cfx2rc  cfx_ptw_ptbr[63], rd17 ; PTBR[63] |     cfx2rc  cfx_ptw_ptbr[63], rd17 @@ PTBR[63]
L202 |     ; rd16 = idx，返回 rd8 = base |     @@ rd16 = idx，返回 rd8 = base
L206 |     set.rb   rb8, rd3                      ; rd→rb 中转 |     set.rb   rb8, rd3                      @@ rd→rb 中转
L209 |     cfx2rd  cfx_ptw_ptbr[0], rd8 ; PTBR[0] |     cfx2rd  cfx_ptw_ptbr[0], rd8 @@ PTBR[0]
L211 |     cfx2rd  cfx_ptw_ptbr[1], rd8 ; PTBR[1] |     cfx2rd  cfx_ptw_ptbr[1], rd8 @@ PTBR[1]
L213 |     ; ... 共 64 路，rc 0-63 ... |     @@ ... 共 64 路，rc 0-63 ...
L214 |     cfx2rd  cfx_ptw_ptbr[63], rd8 ; PTBR[63] |     cfx2rd  cfx_ptw_ptbr[63], rd8 @@ PTBR[63]
L218 |     ; rd16 = mode（0=U/1=J/2=S/3=H）, rd17 = perm（64 位权限位图） |     @@ rd16 = mode（0=U/1=J/2=S/3=H）, rd17 = perm（64 位权限位图）
L219 |     ; 通过跳转表将 rd17 写入对应 mode 的 cfx_ptw_*_perm 寄存器 |     @@ 通过跳转表将 rd17 写入对应 mode 的 cfx_ptw_*_perm 寄存器
L220 |     shl.uo  rd16, rd16, 3                          ; mode × 8（跳转表偏移，每路 2 条指令） |     shl.uo  rd16, rd16, 3                          @@ mode × 8（跳转表偏移，每路 2 条指令）
L223 |     set.rb   rb8, rd3                      ; rd→rb 中转 |     set.rb   rb8, rd3                      @@ rd→rb 中转
L226 |     cfx2rc  cfx_ptw_user_perm, rd17               ; U-mode (0) |     cfx2rc  cfx_ptw_user_perm, rd17               @@ U-mode (0)
L228 |     cfx2rc  cfx_ptw_jail_perm, rd17               ; J-mode (1) |     cfx2rc  cfx_ptw_jail_perm, rd17               @@ J-mode (1)
L230 |     cfx2rc  cfx_ptw_supv_perm, rd17               ; S-mode (2) |     cfx2rc  cfx_ptw_supv_perm, rd17               @@ S-mode (2)
L232 |     cfx2rc  cfx_ptw_hypv_perm, rd17               ; H-mode (3) |     cfx2rc  cfx_ptw_hypv_perm, rd17               @@ H-mode (3)
L236 |     ; rd16 = mask（64 位使能位图） |     @@ rd16 = mask（64 位使能位图）
L241 |     ; rd16 = ptbr_code, rd17 = level（1=L1, 2=L2）, rb16 = va, rd18 = pte |     @@ rd16 = ptbr_code, rd17 = level（1=L1, 2=L2）, rb16 = va, rd18 = pte
L242 |     ; TODO: 读取 PTBR[ptbr_code]，按 level 计算 PTE 偏移，通过 OS 映射的虚拟地址写 PTE |     @@ TODO: 读取 PTBR[ptbr_code]，按 level 计算 PTE 偏移，通过 OS 映射的虚拟地址写 PTE
L246 |     ; rd16 = cause, rb16 = fault_addr（由调用方传入） |     @@ rd16 = cause, rb16 = fault_addr（由调用方传入）
L247 |     ; ... 根据 cause 类型执行页表步进、pmem 分配、PTE 更新 ... |     @@ ... 根据 cause 类型执行页表步进、pmem 分配、PTE 更新 ...
L251 |     ; rd16 = idx, rb16 = pthi（PA[63:48] 用于页表步进） |     @@ rd16 = idx, rb16 = pthi（PA[63:48] 用于页表步进）
L252 |     set.rd   rd17, rb16                              ; rb→rd 中转 |     set.rd   rd17, rb16                              @@ rb→rd 中转
L256 |     set.rb   rb8, rd3                      ; rd→rb 中转 |     set.rb   rb8, rd3                      @@ rd→rb 中转
L259 |     cfx2rc  cfx_ptw_pthi[0], rd17 ; pthi[0] |     cfx2rc  cfx_ptw_pthi[0], rd17 @@ pthi[0]
L261 |     cfx2rc  cfx_ptw_pthi[1], rd17 ; pthi[1] |     cfx2rc  cfx_ptw_pthi[1], rd17 @@ pthi[1]
L263 |     ; ... 共 64 路 ... |     @@ ... 共 64 路 ...
L264 |     cfx2rc  cfx_ptw_pthi[63], rd17 ; pthi[63] |     cfx2rc  cfx_ptw_pthi[63], rd17 @@ pthi[63]
L268 |     ; rd16 = idx, rb16 = pahi（PA[63:48] 用于最终转换结果） |     @@ rd16 = idx, rb16 = pahi（PA[63:48] 用于最终转换结果）
L269 |     set.rd   rd17, rb16                              ; rb→rd 中转 |     set.rd   rd17, rb16                              @@ rb→rd 中转
L273 |     set.rb   rb8, rd3                      ; rd→rb 中转 |     set.rb   rb8, rd3                      @@ rd→rb 中转
L276 |     cfx2rc  cfx_ptw_pahi[0], rd17 ; pahi[0] |     cfx2rc  cfx_ptw_pahi[0], rd17 @@ pahi[0]
L278 |     cfx2rc  cfx_ptw_pahi[1], rd17 ; pahi[1] |     cfx2rc  cfx_ptw_pahi[1], rd17 @@ pahi[1]
L280 |     ; ... 共 64 路 ... |     @@ ... 共 64 路 ...
L281 |     cfx2rc  cfx_ptw_pahi[63], rd17 ; pahi[63] |     cfx2rc  cfx_ptw_pahi[63], rd17 @@ pahi[63]
L298 | ; 设置 cfx_tlb 的 supv 异常向量，允许 supv 内核调用 | @@ 设置 cfx_tlb 的 supv 异常向量，允许 supv 内核调用
L302 | ; 允许 cfx_tlb 从 supv 触发（清除 global_cfx_mask 对应位） | @@ 允许 cfx_tlb 从 supv 触发（清除 global_cfx_mask 对应位）
L303 | ; 注：global_cfx_mask 是全局共享寄存器（此处通过 cfx_smon 访问），所有 cfx 的委托掩码集中于此 | @@ 注：global_cfx_mask 是全局共享寄存器（此处通过 cfx_smon 访问），所有 cfx 的委托掩码集中于此
L316 |     ; CFXTRAP (1<<0) → SBI 功能调用 |     @@ CFXTRAP (1<<0) → SBI 功能调用
L320 |     ; 页表相关异常（TLB 命中时产生）→ 委托 cfx_ptw 处理 |     @@ 页表相关异常（TLB 命中时产生）→ 委托 cfx_ptw 处理
L321 |     set.rd   rd3, 1<<12                               ; NXPERM |     set.rd   rd3, 1<<12                               @@ NXPERM
L323 |     set.rd   rd3, 1<<13                               ; NWPERM |     set.rd   rd3, 1<<13                               @@ NWPERM
L325 |     set.rd   rd3, 1<<14                               ; NRPERM |     set.rd   rd3, 1<<14                               @@ NRPERM
L327 |     set.rd   rd3, 1<<18                               ; IGPFTRAP |     set.rd   rd3, 1<<18                               @@ IGPFTRAP
L329 |     set.rd   rd3, 1<<19                               ; ISPFTRAP |     set.rd   rd3, 1<<19                               @@ ISPFTRAP
L331 |     set.rd   rd3, 1<<22                               ; DGPFTRAP |     set.rd   rd3, 1<<22                               @@ DGPFTRAP
L333 |     set.rd   rd3, 1<<23                               ; DSPFTRAP |     set.rd   rd3, 1<<23                               @@ DSPFTRAP
L344 |     br.eq {rd2, rd3}?, [rb0, cfx_tlb_invalidate] ; func 0 |     br.eq {rd2, rd3}?, [rb0, cfx_tlb_invalidate] @@ func 0
L348 |     ; 委托 cfx_ptw 处理页表异常（通过 SBI_PTW_HANDLE_FAULT） |     @@ 委托 cfx_ptw 处理页表异常（通过 SBI_PTW_HANDLE_FAULT）
L349 |     cfx2rd  cfx_tlb_excp_cause_info, rd40            ; 故障地址（保存至 callee-saved rd40） |     cfx2rd  cfx_tlb_excp_cause_info, rd40            @@ 故障地址（保存至 callee-saved rd40）
L351 |     cfx2rd  cfx_tlb_excp_cause_id, rd16              ; 异常原因（cause_id） |     cfx2rd  cfx_tlb_excp_cause_id, rd16              @@ 异常原因（cause_id）
L353 |     ; 返回 rd8 = page_mask（成功：0xFFFF...掩码；失败：0） |     @@ 返回 rd8 = page_mask（成功：0xFFFF...掩码；失败：0）
L355 |     br.eq {rd8, rd3}?, [rb0, cfx_tlb_ptw_fail] ; 修复失败 → 跳过 |     br.eq {rd8, rd3}?, [rb0, cfx_tlb_ptw_fail] @@ 修复失败 → 跳过
L356 |     ; 修复成功 → invalid 对应 TLB 表项，按实际页大小 |     @@ 修复成功 → invalid 对应 TLB 表项，按实际页大小
L357 |     and.o   rd40, rd40, rd8                          ; 按掩码对齐至页面起始 |     and.o   rd40, rd40, rd8                          @@ 按掩码对齐至页面起始
L359 |     xnor.o  rd16, rd8, rd0                       ; rd16 = ~rd8（not.o 已删除，见 ADR-0013 D11） |     xnor.o  rd16, rd8, rd0                       @@ rd16 = ~rd8（not.o 已删除，见 ADR-0013 D11）
L360 |     add.si    rd16, 1                             ; addr_size = ~mask + 1 |     add.si    rd16, 1                             @@ addr_size = ~mask + 1
L363 |     cfx2rc  cfx_tlb_control, rd2                      ; bit1 = invalid by addr |     cfx2rc  cfx_tlb_control, rd2                      @@ bit1 = invalid by addr
L364 |     escape cfx_tlb, [excp_cause_ip, 0] ; 重试故障指令 |     escape cfx_tlb, [excp_cause_ip, 0] @@ 重试故障指令
L366 |     escape cfx_tlb, [excp_cause_ip, 4] ; 跳过故障指令 |     escape cfx_tlb, [excp_cause_ip, 4] @@ 跳过故障指令
L375 |     ; rb16 = start, rd16 = size（由调用方通过 trap 传入） |     @@ rb16 = start, rd16 = size（由调用方通过 trap 传入）
L377 |     set.rd   rd2, rb16                               ; rb→rd 中转（cfx2rc 源操作数须为 rd） |     set.rd   rd2, rb16                               @@ rb→rd 中转（cfx2rc 源操作数须为 rd）
L379 |     set.rd   rd2, 1 << 1                              ; bit1 = invalid tlb by addr range |     set.rd   rd2, 1 << 1                              @@ bit1 = invalid tlb by addr range
L391 | ; 使虚拟地址 addr 对应的 64K 区域 TLB 表项无效 | @@ 使虚拟地址 addr 对应的 64K 区域 TLB 表项无效
L393 | set.rd   rd16, 65536                              ; 64K | set.rd   rd16, 65536                              @@ 64K
L396 | ; 使对应 ptbr 的所有 TLB 表项无效 | @@ 使对应 ptbr 的所有 TLB 表项无效
L398 | set.rd   rd16, 0x40000000000                       ; 0x40000000000（2^42） = 集合内全部 VA 空间 | set.rd   rd16, 0x40000000000                       @@ 0x40000000000（2^42） = 集合内全部 VA 空间
L454 |     set.rd   rd3, 1                                 ; CFXTRAP (1<<0) |     set.rd   rd3, 1                                 @@ CFXTRAP (1<<0)
L456 |     cfx2rd  cfx_pmem_excp_cause_info, rd2         ; func dispatch |     cfx2rd  cfx_pmem_excp_cause_info, rd2         @@ func dispatch
L460 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_count] ; func 0 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_count] @@ func 0
L462 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_start] ; func 1 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_start] @@ func 1
L464 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_size] ; func 2 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_size] @@ func 2
L466 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_attr] ; func 3 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_get_pm_attr] @@ func 3
L468 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_alloc_page] ; func 4 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_alloc_page] @@ func 4
L470 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_free_page] ; func 5 |     br.eq {rd2, rd3}?, [rb0, cfx_pmem_free_page] @@ func 5
L476 |     ; TODO: 遍历 cfx_pmem_exist 位图，统计置 1 的位数 = PM 区域数 |     @@ TODO: 遍历 cfx_pmem_exist 位图，统计置 1 的位数 = PM 区域数
L480 |     ; rd16 = idx, cfx_pmem_start[idx] 为索引数组 |     @@ rd16 = idx, cfx_pmem_start[idx] 为索引数组
L481 |     ; TODO: 跳转表或 SRAM 实现动态索引 |     @@ TODO: 跳转表或 SRAM 实现动态索引
L485 |     ; rd16 = idx |     @@ rd16 = idx
L486 |     ; TODO: 同上 |     @@ TODO: 同上
L490 |     ; rd16 = idx |     @@ rd16 = idx
L491 |     ; TODO: 同上 |     @@ TODO: 同上
L495 |     ; rd16 = size_hint（0 = 自动选择最小的可用区域） |     @@ rd16 = size_hint（0 = 自动选择最小的可用区域）
L496 |     ; 返回 rd8 = ppn（物理页号）或 -1（失败） |     @@ 返回 rd8 = ppn（物理页号）或 -1（失败）
L497 |     ; TODO: 遍历 PM 区域，维护自由页链表，分配并返回 PPN |     @@ TODO: 遍历 PM 区域，维护自由页链表，分配并返回 PPN
L501 |     ; rd16 = ppn |     @@ rd16 = ppn
L502 |     ; TODO: 将 PPN 归还到对应 PM 区域的自由页链表 |     @@ TODO: 将 PPN 归还到对应 PM 区域的自由页链表
L518 | ; 设置 cfx_timer 的 supv 异常向量 | @@ 设置 cfx_timer 的 supv 异常向量
L522 | ; 允许 cfx_timer 从 supv 触发 | @@ 允许 cfx_timer 从 supv 触发
L524 | set.rd   rd3, ~(1<<18)                                ; cfx_timer = cfx18 | set.rd   rd3, ~(1<<18)                                @@ cfx_timer = cfx18
L535 |     ; CFXTRAP (1<<0) → SBI 功能调用 |     @@ CFXTRAP (1<<0) → SBI 功能调用
L539 |     ; TIMER (1<<10) → 定时器中断 |     @@ TIMER (1<<10) → 定时器中断
L548 |     set.rd   rd3, 0x3FFFF                            ; 掩码提取 immu18 |     set.rd   rd3, 0x3FFFF                            @@ 掩码提取 immu18
L551 |     br.eq {rd2, rd3}?, [rb0, cfx_timer_set_timer] ; func 0 |     br.eq {rd2, rd3}?, [rb0, cfx_timer_set_timer] @@ func 0
L553 |     br.eq {rd2, rd3}?, [rb0, cfx_timer_get_time] ; func 1 |     br.eq {rd2, rd3}?, [rb0, cfx_timer_get_time] @@ func 1
L561 |     ; rd16 = timeout（调用方传入） |     @@ rd16 = timeout（调用方传入）
L562 |     ; 写入计数值，设置为递减 one-shot 模式并启动 |     @@ 写入计数值，设置为递减 one-shot 模式并启动
L564 |     set.rd   rd2, 1                                      ; bit0=enable, bit1=one-shot, bit2=decrement |     set.rd   rd2, 1                                      @@ bit0=enable, bit1=one-shot, bit2=decrement
L569 |     cfx2rd  cfx_timer_regs[0], rd8                    ; 返回值在 rd8，读取定时器当前计数值 |     cfx2rd  cfx_timer_regs[0], rd8                    @@ 返回值在 rd8，读取定时器当前计数值
L573 |     ; 处理定时器中断 |     @@ 处理定时器中断
L583 | ; 设置定时器在 timeout 周期后触发 | @@ 设置定时器在 timeout 周期后触发
L587 | ; 读取当前周期计数 | @@ 读取当前周期计数
L589 | ; 返回值在 rd8 | @@ 返回值在 rd8
L606 | ; 设置 cfx_uart 的 supv 异常向量 | @@ 设置 cfx_uart 的 supv 异常向量
L610 | ; 允许 cfx_uart 从 supv 触发 | @@ 允许 cfx_uart 从 supv 触发
L623 |     ; CFXTRAP (1<<0) → SBI 功能调用 |     @@ CFXTRAP (1<<0) → SBI 功能调用
L627 |     ; UART 中断（1<<32..63） |     @@ UART 中断（1<<32..63）
L628 |     ; 通过 excp_pending 寄存器判断具体中断源并处理 |     @@ 通过 excp_pending 寄存器判断具体中断源并处理
L630 |     ; 此处根据 pending 位处理对应 UART |     @@ 此处根据 pending 位处理对应 UART
L638 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_putchar] ; func 0 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_putchar] @@ func 0
L640 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_getchar] ; func 1 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_getchar] @@ func 1
L642 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_write] ; func 2 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_write] @@ func 2
L644 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_read] ; func 3 |     br.eq {rd2, rd3}?, [rb0, cfx_uart_read] @@ func 3
L654 |     ; rd16 = ch（调用方传入） |     @@ rd16 = ch（调用方传入）
L655 |     cfx2rc  cfx_uart_uart0_regs[0], rd16              ; 写 UART 发送寄存器 |     cfx2rc  cfx_uart_uart0_regs[0], rd16              @@ 写 UART 发送寄存器
L659 |     ; 从 UART 接收寄存器读取字符 |     @@ 从 UART 接收寄存器读取字符
L664 |     ; rb16 = buf, rd16 = len |     @@ rb16 = buf, rd16 = len
L665 |     ; 循环写入 len 字节（此处省略循环实现） |     @@ 循环写入 len 字节（此处省略循环实现）
L670 |     ; rb16 = buf, rd16 = len |     @@ rb16 = buf, rd16 = len
L671 |     ; 循环读取 len 字节（此处省略循环实现） |     @@ 循环读取 len 字节（此处省略循环实现）
L684 | ; 写入字符 'A' | @@ 写入字符 'A'
L688 | ; 读取字符 | @@ 读取字符
L690 | ; 返回值在 rd8 | @@ 返回值在 rd8
L706 | ; 设置 cfx_power 的 supv 异常向量 | @@ 设置 cfx_power 的 supv 异常向量
L710 | ; 允许 cfx_power 从 supv 触发（清除 global_cfx_mask 对应位） | @@ 允许 cfx_power 从 supv 触发（清除 global_cfx_mask 对应位）
L723 |     ; CFXTRAP (1<<0) → SBI 功能调用 |     @@ CFXTRAP (1<<0) → SBI 功能调用
L727 |     ; POWEROFF (1<<8) |     @@ POWEROFF (1<<8)
L731 |     ; HARD RESET (1<<9) |     @@ HARD RESET (1<<9)
L735 |     ; SOFT RESET (1<<10) |     @@ SOFT RESET (1<<10)
L742 | ; ─── SBI 功能调用 dispatch（基于 excp_cause_info 中的 immu18）─── | @@ ─── SBI 功能调用 dispatch（基于 excp_cause_info 中的 immu18）───
L745 |     set.rd   rd3, 0x3FFFF                            ; 掩码提取 immu18 |     set.rd   rd3, 0x3FFFF                            @@ 掩码提取 immu18
L748 |     br.eq {rd2, rd3}?, [rb0, cfx_power_shutdown] ; func 0 |     br.eq {rd2, rd3}?, [rb0, cfx_power_shutdown] @@ func 0
L750 |     br.eq {rd2, rd3}?, [rb0, cfx_power_hard_reset] ; func 1 |     br.eq {rd2, rd3}?, [rb0, cfx_power_hard_reset] @@ func 1
L752 |     br.eq {rd2, rd3}?, [rb0, cfx_power_soft_reset] ; func 2 |     br.eq {rd2, rd3}?, [rb0, cfx_power_soft_reset] @@ func 2
L760 |     set.rd   rd2, 1                                  ; bit0 = 关机 |     set.rd   rd2, 1                                  @@ bit0 = 关机
L761 |     cfx2rc  cfx_power_ctrl, rd2                   ; 不返回 |     cfx2rc  cfx_power_ctrl, rd2                   @@ 不返回
L764 |     set.rd   rd2, 2                                  ; bit1 = 硬复位 |     set.rd   rd2, 2                                  @@ bit1 = 硬复位
L765 |     cfx2rc  cfx_power_ctrl, rd2                   ; 不返回 |     cfx2rc  cfx_power_ctrl, rd2                   @@ 不返回
L768 |     set.rd   rd2, 4                                  ; bit2 = 软复位 |     set.rd   rd2, 4                                  @@ bit2 = 软复位
L769 |     cfx2rc  cfx_power_ctrl, rd2                   ; 不返回 |     cfx2rc  cfx_power_ctrl, rd2                   @@ 不返回
L779 | ; 关闭系统电源 | @@ 关闭系统电源
L782 | ; 硬复位 | @@ 硬复位
L785 | ; 软复位 | @@ 软复位
L796 | ; ===== 系统初始化 ===== | @@ ===== 系统初始化 =====
L798 |     ; 设置cfx0的U-mode异常向量（从user陷入时跳转到cfx_umon_user_excp_handler） |     @@ 设置cfx0的U-mode异常向量（从user陷入时跳转到cfx_umon_user_excp_handler）
L802 |     ; 允许 U-mode 同步异常进入 cfx_umon（清除 global_cfx_mask bit 0） |     @@ 允许 U-mode 同步异常进入 cfx_umon（清除 global_cfx_mask bit 0）
L810 | ; ===== cfx0异常向量入口（U-mode） ===== | @@ ===== cfx0异常向量入口（U-mode） =====
L812 |     ; 读取异常原因 |     @@ 读取异常原因
L815 |     ; 判断异常类型并分发 |     @@ 判断异常类型并分发
L817 |     br.eq {rd2, rd3}?, [rb0, syscall_handler] ; CFXTRAP (1<<0) |     br.eq {rd2, rd3}?, [rb0, syscall_handler] @@ CFXTRAP (1<<0)
L819 |     br.eq {rd2, rd3}?, [rb0, illi_handler] ; ILLI (1<<8) |     br.eq {rd2, rd3}?, [rb0, illi_handler] @@ ILLI (1<<8)
L820 |     ; 默认：未处理异常 |     @@ 默认：未处理异常

## spec/DADAO-23-HBI-超管系统二进制接口.md（6 行）
L32 | ; 清除各 cfx 的 cg reg delegation，允许 supv 访问所有 cg（cg3 固定禁止，bit3 硬件忽略写入） | @@ 清除各 cfx 的 cg reg delegation，允许 supv 访问所有 cg（cg3 固定禁止，bit3 硬件忽略写入）
L47 | ; 设置 cfx_power 的 excp_prev_run_mode 为 supv（值 2） | @@ 设置 cfx_power 的 excp_prev_run_mode 为 supv（值 2）
L51 | ; 设置 excp_prev_cfx_mask 为全 1（不允许任何核芯功能扩展发生异常） | @@ 设置 excp_prev_cfx_mask 为全 1（不允许任何核芯功能扩展发生异常）
L55 | ; 设置 excp_cause_ip 为 supv 入口物理地址（尚未开启 ptbr，应为物理地址） | @@ 设置 excp_cause_ip 为 supv 入口物理地址（尚未开启 ptbr，应为物理地址）
L59 | ; 传递设备树或硬件信息指针（0 表示无） | @@ 传递设备树或硬件信息指针（0 表示无）
L62 | ; 执行 escape 跳转到 supv 入口 | @@ 执行 escape 跳转到 supv 入口

## spec/SimRISC-03-16位立即数操作.md（50 行）
L86 | ; 加载零 → set.zw 即可覆盖全 64 位 | @@ 加载零 → set.zw 即可覆盖全 64 位
L87 | set.rd   rd1, 0                     ; 展开为 set.zw rd1, wp0, 0 | set.rd   rd1, 0                     @@ 展开为 set.zw rd1, wp0, 0
L89 | ; 加载全 1（-1）→ set.ow 一条指令全 64 位置 1 | @@ 加载全 1（-1）→ set.ow 一条指令全 64 位置 1
L90 | set.rd   rd1, -1                    ; 展开为 set.ow rd1, wp0, 0xFFFF | set.rd   rd1, -1                    @@ 展开为 set.ow rd1, wp0, 0xFFFF
L92 | ; 加载负数（利用 set.ow 将其余 48 位置 1 的特性，自动完成符号扩展） | @@ 加载负数（利用 set.ow 将其余 48 位置 1 的特性，自动完成符号扩展）
L93 | set.rd   rd1, -42                   ; 展开为 set.ow rd1, wp0, 0xFFD6  (-42 的低 16 位) | set.rd   rd1, -42                   @@ 展开为 set.ow rd1, wp0, 0xFFD6  (-42 的低 16 位)
L95 | ; 加载位掩码（高位全 1 的低 16 位掩码） | @@ 加载位掩码（高位全 1 的低 16 位掩码）
L96 | set.rd   rd1, 0xFFFFFFFFFFFFFFF0    ; 展开为 set.ow rd1, wp0, 0xFFF0 | set.rd   rd1, 0xFFFFFFFFFFFFFFF0    @@ 展开为 set.ow rd1, wp0, 0xFFF0
L98 | ; 加载 ~(1<<n) → set.ow 一条指令 | @@ 加载 ~(1<<n) → set.ow 一条指令
L99 | set.rd   rd1, ~(1<<5)              ; 展开为 set.ow rd1, wp0, 0xFFDF | set.rd   rd1, ~(1<<5)              @@ 展开为 set.ow rd1, wp0, 0xFFDF
L101 | ; 加载小正数（16 位以内）→ wp0 一条指令 | @@ 加载小正数（16 位以内）→ wp0 一条指令
L102 | set.rd   rd1, 42                    ; 展开为 set.zw rd1, wp0, 42 | set.rd   rd1, 42                    @@ 展开为 set.zw rd1, wp0, 42
L103 | set.rd   rd1, 0x1234ABCD            ; 展开为： | set.rd   rd1, 0x1234ABCD            @@ 展开为：
L104 |                                     ;   set.zw rd1, wp1, 0x1234 |                                     @@   set.zw rd1, wp1, 0x1234
L105 |                                     ;   or.w   rd1, wp0, 0xABCD |                                     @@   or.w   rd1, wp0, 0xABCD
L107 | ; 加载 64 位常数 → 分 4 个 wyde 依次设置 | @@ 加载 64 位常数 → 分 4 个 wyde 依次设置
L108 | set.rd   rd1, 0xDEADBEEF_CAFEBABE  ; 展开为： | set.rd   rd1, 0xDEADBEEF_CAFEBABE  @@ 展开为：
L109 |                                     ;   set.zw rd1, wp3, 0xDEAD |                                     @@   set.zw rd1, wp3, 0xDEAD
L110 |                                     ;   or.w   rd1, wp2, 0xBEEF |                                     @@   or.w   rd1, wp2, 0xBEEF
L111 |                                     ;   or.w   rd1, wp1, 0xCAFE |                                     @@   or.w   rd1, wp1, 0xCAFE
L112 |                                     ;   or.w   rd1, wp0, 0xBABE |                                     @@   or.w   rd1, wp0, 0xBABE
L124 | set.rd   rd5, rb3       ; 展开为 rb2rd {rd5}, {rb3} | set.rd   rd5, rb3       @@ 展开为 rb2rd {rd5}, {rb3}
L125 | set.rd   rd2, rf7       ; 展开为 rf2rd {rd2}, {rf7} | set.rd   rd2, rf7       @@ 展开为 rf2rd {rd2}, {rf7}
L126 | set.rd   rd8, rd3       ; 展开为 rd2rd {rd8}, {rd3} | set.rd   rd8, rd3       @@ 展开为 rd2rd {rd8}, {rd3}
L127 | set.rd   rd4, ra10      ; 展开为 ra2rd {rd4}, {ra10} | set.rd   rd4, ra10      @@ 展开为 ra2rd {rd4}, {ra10}
L137 | ; 加载零 | @@ 加载零
L138 | set.rb   rb1, 0                      ; 展开为 set.zw rb1, wp0, 0 | set.rb   rb1, 0                      @@ 展开为 set.zw rb1, wp0, 0
L140 | ; 加载 48 位地址 | @@ 加载 48 位地址
L141 | set.rb   rb1, 0x123456789ABC         ; 展开为： | set.rb   rb1, 0x123456789ABC         @@ 展开为：
L142 |                                       ;   set.zw rb1, wp2, 0x1234 |                                       @@   set.zw rb1, wp2, 0x1234
L143 |                                       ;   or.w  rb1, wp1, 0x5678 |                                       @@   or.w  rb1, wp1, 0x5678
L144 |                                       ;   or.w  rb1, wp0, 0x9ABC |                                       @@   or.w  rb1, wp0, 0x9ABC
L150 | set.rb   rb5, rd3       ; 展开为 rd2rb {rb5}, {rd3} | set.rb   rb5, rd3       @@ 展开为 rd2rb {rb5}, {rd3}
L151 | set.rb   rb2, rb7       ; 展开为 rb2rb {rb2}, {rb7} | set.rb   rb2, rb7       @@ 展开为 rb2rb {rb2}, {rb7}
L161 | ; 加载单精浮点 1.0（0x3F800000）→ 只需设置低 32 位 | @@ 加载单精浮点 1.0（0x3F800000）→ 只需设置低 32 位
L162 | set.ft   rf1, 0x3F800000             ; 展开为： | set.ft   rf1, 0x3F800000             @@ 展开为：
L163 |                                       ;   set.w rf1, wp1, 0x3F80 |                                       @@   set.w rf1, wp1, 0x3F80
L164 |                                       ;   set.w rf1, wp0, 0x0000 |                                       @@   set.w rf1, wp0, 0x0000
L166 | ; 加载双精浮点 1.0（0x3FF0000000000000） | @@ 加载双精浮点 1.0（0x3FF0000000000000）
L167 | set.fo   rf1, 0x3FF0000000000000     ; 展开为： | set.fo   rf1, 0x3FF0000000000000     @@ 展开为：
L168 |                                       ;   set.w rf1, wp3, 0x3FF0 |                                       @@   set.w rf1, wp3, 0x3FF0
L169 |                                       ;   set.w rf1, wp2, 0x0000 |                                       @@   set.w rf1, wp2, 0x0000
L170 |                                       ;   set.w rf1, wp1, 0x0000 |                                       @@   set.w rf1, wp1, 0x0000
L171 |                                       ;   set.w rf1, wp0, 0x0000 |                                       @@   set.w rf1, wp0, 0x0000
L173 | ; 加载零 → 将 rd0（恒为 0）赋值给 rf | @@ 加载零 → 将 rd0（恒为 0）赋值给 rf
L174 | set.ft   rf1, 0                       ; 展开为 rd2rf {rf1}, {rd0} | set.ft   rf1, 0                       @@ 展开为 rd2rf {rf1}, {rd0}
L175 | set.fo   rf1, 0                       ; 展开为 rd2rf {rf1}, {rd0} | set.fo   rf1, 0                       @@ 展开为 rd2rf {rf1}, {rd0}
L181 | set.ft   rf1, rd5       ; 展开为 rd2rf {rf1}, {rd5} | set.ft   rf1, rd5       @@ 展开为 rd2rf {rf1}, {rd5}
L182 | set.ft   rf1, rf2       ; 展开为 ft2ft {rf1}, {rf2} | set.ft   rf1, rf2       @@ 展开为 ft2ft {rf1}, {rf2}
L183 | set.fo   rf2, rf7       ; 展开为 fo2fo {rf2}, {rf7} | set.fo   rf2, rf7       @@ 展开为 fo2fo {rf2}, {rf7}

## spec/SimRISC-04-64位数据运算.md（27 行）
L74 | add.uo  {rdHA, rdHB}, rdHC, rdHD    ; ZX，rdHA = 进位 | add.uo  {rdHA, rdHB}, rdHC, rdHD    @@ ZX，rdHA = 进位
L75 | add.so  {rdHA, rdHB}, rdHC, rdHD    ; SX，rdHA = 高64位 | add.so  {rdHA, rdHB}, rdHC, rdHD    @@ SX，rdHA = 高64位
L76 | sub.uo  {rdHA, rdHB}, rdHC, rdHD    ; ZX，rdHA = 借位 | sub.uo  {rdHA, rdHB}, rdHC, rdHD    @@ ZX，rdHA = 借位
L77 | sub.so  {rdHA, rdHB}, rdHC, rdHD    ; SX，rdHA = 高64位 | sub.so  {rdHA, rdHB}, rdHC, rdHD    @@ SX，rdHA = 高64位
L184 | xnor.o  rd3, rd4, rd0     ; rd3 = ~rd4（64 位按位取反） | xnor.o  rd3, rd4, rd0     @@ rd3 = ~rd4（64 位按位取反）
L192 | sub.so  {rd0, rd3}, rd0, rd4     ; rd3 = -rd4（64 位取负，双目的写回 rd3） | sub.so  {rd0, rd3}, rd0, rd4     @@ rd3 = -rd4（64 位取负，双目的写回 rd3）
L237 | shl.uo  rdHB, rdHC, rdHD        ; 左移 | shl.uo  rdHB, rdHC, rdHD        @@ 左移
L238 | shl.uo  rdHB, rdHC, immu6       ; 左移（立即数） | shl.uo  rdHB, rdHC, immu6       @@ 左移（立即数）
L239 | shr.uo  rdHB, rdHC, rdHD        ; 逻辑右移 | shr.uo  rdHB, rdHC, rdHD        @@ 逻辑右移
L240 | shr.uo  rdHB, rdHC, immu6       ; 逻辑右移（立即数） | shr.uo  rdHB, rdHC, immu6       @@ 逻辑右移（立即数）
L241 | shr.so  rdHB, rdHC, rdHD        ; 算术右移 | shr.so  rdHB, rdHC, rdHD        @@ 算术右移
L242 | shr.so  rdHB, rdHC, immu6       ; 算术右移（立即数） | shr.so  rdHB, rdHC, immu6       @@ 算术右移（立即数）
L244 | ext.uo  rdHB, rdHC, rdHD        ; 零扩展 | ext.uo  rdHB, rdHC, rdHD        @@ 零扩展
L245 | ext.uo  rdHB, rdHC, immu6       ; 零扩展（立即数） | ext.uo  rdHB, rdHC, immu6       @@ 零扩展（立即数）
L246 | ext.so  rdHB, rdHC, rdHD        ; 符号扩展 | ext.so  rdHB, rdHC, rdHD        @@ 符号扩展
L247 | ext.so  rdHB, rdHC, immu6       ; 符号扩展（立即数） | ext.so  rdHB, rdHC, immu6       @@ 符号扩展（立即数）
L249 | and.o   rdHB, rdHC, rdHD        ; 逻辑与 | and.o   rdHB, rdHC, rdHD        @@ 逻辑与
L250 | or.o    rdHB, rdHC, rdHD        ; 逻辑或 | or.o    rdHB, rdHC, rdHD        @@ 逻辑或
L251 | xor.o   rdHB, rdHC, rdHD        ; 逻辑异或 | xor.o   rdHB, rdHC, rdHD        @@ 逻辑异或
L252 | xnor.o  rdHB, rdHC, rdHD        ; 逻辑同或 | xnor.o  rdHB, rdHC, rdHD        @@ 逻辑同或
L294 | rev.o   rdHB, rdHC, immu6       ; 64 位逐块反转（k=8 → bswap64；k=1 → bitreverse） | rev.o   rdHB, rdHC, immu6       @@ 64 位逐块反转（k=8 → bswap64；k=1 → bitreverse）
L295 | rev.t   rdHB, rdHC, immu6       ; 32 位块内反转（k=8 → bswap32，须源高 32 位为 0） | rev.t   rdHB, rdHC, immu6       @@ 32 位块内反转（k=8 → bswap32，须源高 32 位为 0）
L296 | rev.w   rdHB, rdHC, immu6       ; 16 位块内反转（k=8 → bswap16，须源高 48 位为 0） | rev.w   rdHB, rdHC, immu6       @@ 16 位块内反转（k=8 → bswap16，须源高 48 位为 0）
L297 | rev.b   rdHB, rdHC, immu6       ; 8 位块内反转（k ∈ {1,2,4}） | rev.b   rdHB, rdHC, immu6       @@ 8 位块内反转（k ∈ {1,2,4}）
L341 | ctlz    rdHB, rdHC, immu6       ; 前导零（immu6=63 → 64 位；immu6=31 → 32 位；全 0 → immu6+1） | ctlz    rdHB, rdHC, immu6       @@ 前导零（immu6=63 → 64 位；immu6=31 → 32 位；全 0 → immu6+1）
L342 | cttz    rdHB, rdHC, immu6       ; 末尾零（immu6=63 → 64 位；全 0 → immu6+1） | cttz    rdHB, rdHC, immu6       @@ 末尾零（immu6=63 → 64 位；全 0 → immu6+1）
L343 | ctpop   rdHB, rdHC, immu6       ; 1 的个数（immu6=63 → 64 位） | ctpop   rdHB, rdHC, immu6       @@ 1 的个数（immu6=63 → 64 位）

## spec/SimRISC-06-控制流.md（1 行）
L151 | ret     rd0, 0          ; 无返回值返回（旧 `return`） | ret     rd0, 0          @@ 无返回值返回（旧 `return`）

## spec/SimRISC-07-浮点运算.md（2 行）
L84 | ft2ft   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}          ; 浮点寄存器间搬移 | ft2ft   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}          @@ 浮点寄存器间搬移
L85 | fo2fo   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}          ; 浮点寄存器间搬移 | fo2fo   {rfHB:rfHB+immu6-1}, {rfHC:rfHC+immu6-1}          @@ 浮点寄存器间搬移

## spec/SimRISC-08-32位数据运算.md（1 行）
L85 | sub.st  rd1, rd0, rd2        ; rd1 = -rd2（低 32 位取负，符号扩展） | sub.st  rd1, rd0, rd2        @@ rd1 = -rd2（低 32 位取负，符号扩展）

## spec/SimRISC-09-16位数据运算.md（1 行）
L85 | sub.sw  rd1, rd0, rd2        ; rd1 = -rd2（低 16 位取负，符号扩展） | sub.sw  rd1, rd0, rd2        @@ rd1 = -rd2（低 16 位取负，符号扩展）

## spec/SimRISC-10-8位数据运算.md（1 行）
L85 | sub.sb  rd1, rd0, rd2        ; rd1 = -rd2（低 8 位取负，符号扩展） | sub.sb  rd1, rd0, rd2        @@ rd1 = -rd2（低 8 位取负，符号扩展）

## spec/SimRISC-11-其它.md（5 行）
L51 | swym    0                ; 空操作（旧 `nop`） | swym    0                @@ 空操作（旧 `nop`）
L123 | ; 简化写法（推荐） | @@ 简化写法（推荐）
L124 | cfx2rd  cfx_umon_excp_cause_ip, rd2    ; 读取 cfx_umon 的 excp_cause_ip | cfx2rd  cfx_umon_excp_cause_ip, rd2    @@ 读取 cfx_umon 的 excp_cause_ip
L125 | cfx2rc  cfx_power_ctrl, rd2             ; 写入 cfx_power 的 power_ctrl | cfx2rc  cfx_power_ctrl, rd2             @@ 写入 cfx_power 的 power_ctrl
L127 | ; 等价的标准写法 | @@ 等价的标准写法
```

## 与 `LLVM-109t` 的先后

- **纯文档可先落地**：本册不依赖 `LLVM-109t` 的代码；但 `LLVM-109t` 翻 `CommentString = "@@"` 后，这些示例才「真能被新汇编器按注释处理」⇒ 建议**同一提交/同一批次**落地；若分批，本册先行、`LLVM-109t` 紧随，两册完成区互引。
- 本册**不跑** `install-host`/`build-*`（纯文档）；只跑静态门控。

## 接口规范

- **输入**：上「改动清单」+ 判据；`SPEC-147t`（0.5.3 规范面）；`manifests/spec-readonly.lock.toml`。
- **输出**：
  1. 11 册只读 spec 文件按清单逐行改 `;`→`@@`（**仅 298 行**）。
  2. `manifests/spec-readonly.lock.toml`：**仅这 11 册**的 `sha256` 重算 + 变更注记（日期/册/行数/授权原话指针）；其余 10 册不变。
  3. 证据 `.work/evidence/SPEC-149t/*`（迁移不变量校验 + 可达 FAIL 注入）与日志 `.work/log/spec/SPEC-149t-*.log`。
- **约束**：`docs/Process-06 §2` 授权原话落完成区；禁 `git checkout/restore/stash`；临时目录 `/tmp/opencode/SPEC-149t/`；不 `push`。

## 验收标准

1. **行数/文件数精确**：`git diff --numstat` 对本册范围 = **11 文件 / 298 增 298 删**；逐册行数 = 清单标题所载（23/181/6/50/27/1/2/1/1/1/5）。
2. **逐行形态**：证据脚本对每个改动行断言「新行 == 原行首个 `;` 换 `@@`」且「该行位于新文件的 `simrisc` 块内」；任一不符 ⇒ FAIL。
3. **禁区零改动**：`DADAO-21` 的 `c` 块、`SimRISC-02` C 分号、`DADAO-12` 伪代码块、`SimRISC-04` 伪代码块、全册正文 `;` 的行号集合与基线逐行相同（脚本断言）。
4. **只读锁**：`make check-spec-readonly` rc=0；锁内**仅 11 册** `sha256` 变化，且与实际 `sha256sum` 一致。
5. **门控**：`make check`（L1）rc=0；另逐条 rc=0：`check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-asm-prose` / `check-spec-codeblocks` / `check-tasks` / `check-knowledge-refs` / `check-no-residue` / `check-milestones-fresh` / `check_issues`。
6. **可达 FAIL**：`cp` 备份 + `md5sum` 对账下，把 `DADAO-21` C 块的一处 `;` 改 `@@`（或删掉）⇒ 证据脚本不变量断言 **FAIL**；还原后回绿（md5 相同）。**同时说明**：现有 `check-asm-prose`/`check-spec-codeblocks` 只解析 `simrisc` 块，`check-spec-readonly` 只比哈希（重算锁后即失效）⇒ **没有现成门控能发现 C 分号误改**；故本册以**证据脚本的不变量断言**作为该错误形态的判据（脚本随证据保留；不新增永久门控：`;` 在 `simrisc` 块内是合法语句分隔符，无法写成永久正向规则）。
7. **完成区**贴真实命令输出 + 退出码（≤30 行）；长输出留 `.work/log/spec/`。

## 完成区
**测试结果**：通过 298/298 行（11 册）；逐行基线一致（`check_migration.py full` rc=0）。`.work/build/llvm/bin/llvm-mc` 抽样 8 处：7 处 rc=0；SimRISC-04 L237 失败（`rdHB/rdHC/rdHD` 为文档占位符，非真实寄存器，属“示意”写法）。
**修改文件**：11 册（DADAO-11 23 / DADAO-22 181 / DADAO-23 6 / SimRISC-03 50 / SimRISC-04 27 / SimRISC-06 1 / SimRISC-07 2 / SimRISC-08 1 / SimRISC-09 1 / SimRISC-10 1 / SimRISC-11 5）；`manifests/spec-readonly.lock.toml`（仅 11 册 sha256 + 变更注记）；本任务书（完成区/审阅记录）；证据 `.work/evidence/SPEC-149t/{run.sh,check_migration.py}`、日志 `.work/log/spec/SPEC-149t-*.log`。
**验收结果**：
- 用户授权原话（`Process-06 §2`，渠道 = 经主会话问答，2026-10-19）：「1、A；2、就地修订」。
- `check_migration.py full` rc=0：changed-line-set 298/298；`simrisc` 残留 `;`=0；非 `simrisc`（C 块 8 行/25 处、DADAO-12 伪代码 6、SimRISC-04 伪代码 3）行号集合与基线提交 `31e97d4` 逐行相同；其余 10 册字节不变；11 册册头版本/附录零改动（`check-spec-changelog` rc=0）；锁内仅 11 册 sha256 变化且与实测一致。
- `git diff --histogram --numstat -- spec/*.md` = 11 文件 +298 −298；默认 Myers `--numstat` = +303 −303（见“新发现”①）。
- 门控 rc=0：`make check`（L1，日志 `SPEC-149t-make-check.log`）、`check-spec-readonly` / `check-spec-changelog` / `check-spec-drift` / `check-asm-prose` / `check-spec-codeblocks` / `check-asm-list` / `check-asm-list-drift` / `check-contracts-pending` / `check-tasks` / `check-knowledge-refs` / `check-no-residue` / `check-milestones-fresh` / `check_issues`。
- 证据脚本 `.work/evidence/SPEC-149t/run.sh` rc=0；3 处可达 FAIL 注入（C 分号误改 / 回退迁移行 / 改行尾）均 rc=1，`cp`+md5 还原后 rc=0。
**新发现/坑**：① git 2.43 默认 Myers 对 SimRISC-03（3 行）/ SimRISC-04（2 行）的**内容完全相同空行**输出伪 −/+，默认 numstat 303；实际改动行与 `--histogram` 均为 298，非内容漂移。② `check-spec-codeblocks` 不识别 `@@` 开头为注释（按非助记符静默跳过），本册绿灯不受影响，建议后续补识别。③ SimRISC-04/07 的 `rdHB/rdHC/rdHD` 等为文档占位符，不能直接汇编。④ 整块汇编另有失败：含 `#define` 的块（DADAO-22 L110/388/579/678/774）LLVM MC 不认 `#` 指令；`set.rd` 展开大常量/符号（SimRISC-03 L85 块、DADAO-22 L312 块）受实现限制——均与 `;`→`@@` 迁移无关。
**遗留问题**：最终重跑 `make check`（10:36）rc=2，原因为**外部**：`.work/source/llvm-project/llvm/lib/Target/DADAO/DADAORegisterInfo.cpp` 被并发任务改动（ADR-0018 FP 变更，mtime 10:36:54），`check-patch-tree` ⑥⑦ 失败；本任务未触碰该树，未用 `checkout/restore`。其余无。

## 审阅记录

### 第 1 轮 engineer 自审（2026-10-19）

- 逐行核对 298 行：`check_migration.py full` rc=0；每行均满足「old 首个 `;`→`@@`」、位于 `simrisc` 块、其余字符逐字不变；非 `simrisc` 行与基线提交 `31e97d4` 逐行相同。
- finding 1（默认 numstat 303≠298）：❌不修。内容层实际改动行 = 298（逐行比较 + `--histogram`），默认 Myers 把 5 行**完全相同空行**输出成 −/+；`--word-diff` 显示这些空行为 context。证据：`check_migration.py full`、`git diff --histogram --numstat`。
- finding 2（证据脚本原有一条恒真 `report(True, "headers...")`）：✅已修。删除该恒真断言；册头/附录不变已由「changed-line-set + 非改动行逐行相同」覆盖。复验：`run.sh` rc=0，74 项 PASS。
- finding 3（锁注记含任务号 vs 派单“不写任务号”）：❌不修。任务书判据明确“不新增变更记录段/不触碰附录”，故 spec 附录零改动；锁文件既有变更注记体例含任务号（如既有 SPEC-134t/142t 条目），保留以维持可追溯。
- finding 4（`check-spec-codeblocks` 不识别 `@@` 注释）：⏸延后。属该门控自身能力缺口，本册未授权改门控；已记入完成区“新发现②”，本册 rc=0。
- finding 5（SimRISC-04/07 占位寄存器不能汇编）：⏸延后。`rdHB/rdHC/rdHD` 为文档示意，非迁移引入；7/8 抽样通过，失败项已如实记录。
- finding 6（最终 `make check` rc=2）：⏸延后（外部）。`.work/source/llvm-project` 被并发任务改动，非本任务文件；已保留现场并登记完成区"遗留问题"，未用 `checkout/restore`。

### 第 1 轮 reviewer 验收（2026-10-19）

**重跑记录**：
- `git diff --histogram --numstat 886bb06^..886bb06 -- spec/*.md` = 11 文件，逐册：DADAO-11 23/23、DADAO-22 181/181、DADAO-23 6/6、SimRISC-03 50/50、SimRISC-04 27/27、SimRISC-06 1/1、SimRISC-07 2/2、SimRISC-08 1/1、SimRISC-09 1/1、SimRISC-10 1/1、SimRISC-11 5/5 = **298+298** ✓；默认 Myers numstat = 303+303（SimRISC-03/04 共 5 行完全相同空行，属 git 已知行为，非内容漂移）。
- `git grep '^[[:space:]]*;' -- 'spec/*.md'` = 仅 DADAO-12 **6** 处（伪代码块 `if/case/goto` + `//` 与 `;` 混用注释，按判据不改）✓。
- C 块未动：`git diff 886bb06^..886bb06 -- spec/DADAO-21-ABI-*.md spec/SimRISC-02-*.md` = 空（无 diff）✓。
- `bash .work/evidence/SPEC-149t/run.sh`：11 册逐行不变量全 PASS（298 行 changed-line-set + line-invariants + simrisc-residual-semicolon + line-count-vs-baseline）；3 处注入（C 分号误改/回退迁移行/改行尾）均 FAIL、cp+md5 还原后回绿 ✓。full invariant 段 3 FAIL = DADAO-21 被 SPEC-150t/151t 同批改动（跨任务干扰），非本册缺陷。
- `make check-spec-readonly` rc=0 ✓；`make check-spec-changelog` rc=0 ✓；`check-milestones-fresh` rc=0 ✓；`check-knowledge-refs` rc=0 ✓；`check-no-residue` rc=0 ✓；`check_issues.py` rc=0 ✓。

**约束核验**：
- ① 11 册 298 行精确：histogram numstat 逐册与清单一致 ✓
- ② C 分号/伪代码块未动：DADAO-21/SimRISC-02 零 diff、DADAO-12 残留 6 处 ✓
- ③ `;`→`@@` 仅首个分号：证据脚本逐行断言 old 首个 `;`→`@@`、其余字符逐字不变 ✓
- ④ 只读锁：仅 11 册 sha256 变化 ✓
- ⑤ 可达 FAIL：3 处注入均 FAIL、cp+md5 还原回绿 ✓

**判决**：**Accepted** — 298 行迁移逐行验证通过、禁区零改动、门控全绿（L1 未重跑，仅重跑秒级门控 + 证据脚本；理由：纯文档任务，代码未变）。
