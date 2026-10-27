/* dadao-dyn.lds — DADAO dynamic-object (ET_DYN) link script — LLVM-094t 阶段 B。
 *
 * 用途：把 PIC 目标文件链接成 **ET_DYN**（`-shared` 共享库 / `-pie` 动态可执行），
 * 供「能产出 + 静态可核」的阶段 B 判据使用（运行 = P3）。
 *
 * 为什么需要单独一份脚本（而不是 lld 默认布局）：
 *   `-fPIC` 的 CodeGen 用 `ld.o rb, [rb0, <slot>]`（`R_DADAO_REL12`，PC 相对、
 *   `imms12` 立即数）访问 `.got` 槽 —— 单指令可及范围只有 **±2 KiB**
 *   （`contract-dynlink.md §3` / `ADR-0026 D5`：不引入 GOT 基址寄存器，取 GOT 槽
 *   一律 PC 相对 + 链接期常量偏移）。而 lld 的默认布局按权限把 RO/RX/RW 分到
 *   不同 PT_LOAD、各自按 `max-page-size`（DADAO = 64 KiB，`DADAO-12 §2.2.2`）对齐
 *   ⇒ `.got` 落在 `.text` 之后整整一页（实测 65592 B）⇒ 越界。按
 *   `contract-dynlink.md §10④`，越界**必须**是链接期报错（lld 确实报错，不静默），
 *   但那样就产不出 ET_DYN。
 *
 * 本脚本的做法 = 沿用 M4 的单一 RAM 区域模型（`ADR-0004 R3`、`tests/shared/linker/dadao.lds`
 * 的 `RAM (rwx)`）：把全部 allocatable 段放进**同一个 RWX PT_LOAD**，`.got` 紧随
 * `.text` ⇒ 槽落在 ±2 KiB 内。`.interp`/`.dynamic`/`.got`/`.got.plt` 另挂在
 * `PT_INTERP` / `PT_DYNAMIC` / `PT_GNU_RELRO`（eager ⇒ 装载后只读，`ADR-0026 D6`）。
 * 全部段必须显式列出：脚本给了 PHDRS 命令后，未列出的段不会自动进任何程序头
 * （实测：漏列 `.dynsym` 等合成段会让 `PT_INTERP.p_filesz` 被撑大）。
 *
 * 边界：本脚本只解决「小模块」的可及性；**通用**解法是 `ADR-0026 D5` 的两段式路径
 * （`ABS48` 序列 + `ldm.o_rrri_rb`，归 LLVM-094t 阶段 C）。
 */
PHDRS
{
  all    PT_LOAD     FLAGS(7);   /* R+W+X：M4 的单一 RAM 区域模型 */
  interp PT_INTERP;
  dyn    PT_DYNAMIC  FLAGS(6);
  relro  PT_GNU_RELRO FLAGS(4);
  stack  PT_GNU_STACK FLAGS(6);
}

SECTIONS
{
  /* ET_DYN：链接期 VMA 以 0 起，运行期偏置由装载器（QEMU user-mode，P3）给定。 */
  . = 0;

  .interp   : ALIGN(1)  { *(.interp) }                        :all :interp
  .dynsym   : ALIGN(8)  { *(.dynsym) }                        :all
  .gnu.hash : ALIGN(8)  { *(.gnu.hash) }                      :all
  .dynstr   : ALIGN(1)  { *(.dynstr) }                        :all
  .rela.dyn : ALIGN(8)  { *(.rela.dyn) }                      :all
  .rela.plt : ALIGN(8)  { *(.rela.plt) }                      :all

  .text     : ALIGN(4)  { *(.text .text.*) }                  :all

  /* `.got` 紧跟 `.text`：`ld.o [rb0, slot]` 的 ±2 KiB 可及性（见文件头）。 */
  .got      : ALIGN(8)  { *(.got) }                           :all :relro
  .plt      : ALIGN(16) { *(.plt) }                           :all
  .dynamic  : ALIGN(8)  { *(.dynamic) }                       :all :relro :dyn
  .got.plt  : ALIGN(8)  { *(.got.plt) }                       :all :relro

  .rodata   : ALIGN(8)  { *(.rodata .rodata.*)
                          *(.srodata .srodata.*) }            :all
  .data     : ALIGN(8)  { *(.data .data.*)
                          *(.sdata .sdata.*) }                :all
  .bss      : ALIGN(8)  { *(.bss .bss.*)
                          *(.sbss .sbss.*) *(COMMON) }        :all

  /DISCARD/ : { *(.note.GNU-stack) }
}
