/*
 * tests/arch/common/env/env.lds — 运行模式环境的镜像布局（m16-testcases-015）
 *
 * 四段互不重叠（驱动按 ENV_BODY_OFF / ENV_TAIL_OFF / ENV_PERM_OFF 现场传入，
 * 不写死）：
 *
 *   ENTRY + 0x0000  .env     环境入口（进入目标模式；按模式选择 env.S）
 *   ENTRY + 0x1000  .body    测试 body（与模式无关；umon 会拷到 U 页）
 *   ENTRY + 0x2000  .envtail 退出与签名输出（umon 会一起拷到 U 页）
 *   ENTRY + 0x4000  .envperm cfx 权限准备/还原（m16-testcases-017；只在 hypv 跑，
 *                            不拷进 U 页 ⇒ 不挤占 body/tail 的 4 KiB 窗口）
 *
 * 为什么 body 在 +0x1000 而不是紧跟 env：body 起始地址对 `-kernel` 的
 * flat bin 是固定的，且 umon 需要按 8 字节粒度整段拷贝（`ld.o/st.o`）。
 * 为什么权限准备单列一段：三个 env 共用同一批宏（`cfx_perm.inc`），全部内联到
 * `.envcode`/`.envtail` 会超出 4 KiB 窗口（smon 曾达 4383 B）。
 */

ENTRY(_start)

SECTIONS
{
  . = ENTRY;
  .env : { *(.envcode) }
  . = ENTRY + ENV_BODY_OFF;
  .body : { *(.bodycode) }
  . = ENTRY + ENV_TAIL_OFF;
  .envtail : { *(.envtail) }
  . = ENTRY + ENV_PERM_OFF;
  .envperm : { *(.envperm) }
  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}
