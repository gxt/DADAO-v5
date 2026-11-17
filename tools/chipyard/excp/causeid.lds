/*
 * causeid.lds — `tools/chipyard/excp/causeid.S` 的链接布局（`m16-chipyard-003`）。
 *
 * 与 `tests/ee-tiny/inst-tiny.lds` 同一套固定地址（同一宏层
 * `tests/inst/macros/inst_test.inc` 的 `.equ`：TEST_BUF / TEST_EXITB），差别只有
 * 本文件末尾的 ASSERT：每个用例的回落点必须是 `aip.si` 指令 + N B
 * （`aip → add.si(+16) → st.o(返回槽) → 故障指令 → 回落点`）。手写的 12 是立即数（标签差进不了
 * 立即数，`tests/inst/MIGRATION.md §6`），所以由链接器**回读校验**，错一位即链接失败。
 *
 *   ENTRY + 0x0000  .text       链例体（本探针只有链例）
 *   ENTRY + 0x7000  结果字节缓冲（运行时写，不进镜像：8 用例 × 16 B）
 *   ENTRY + 0x7800  SYS_EXIT 参数块（运行时写，不进镜像）
 */

ENTRY(_start)

PHDRS
{
  image PT_LOAD FLAGS(7);
}

SECTIONS
{
  . = 0xffffff010100;

  .text : {
    *(.text)
  } : image

  ASSERT(SIZEOF(.text) <= 0x4000, "causeid: .text 越过 16 KiB 窗口")

  /DISCARD/ : {
    *(.note.GNU-stack)
    *(.comment)
  }
}

ASSERT(c1_resume == c1_aip + 16, "causeid: case 1 resume must be aip + 16")
ASSERT(c2_resume == c2_aip + 24, "causeid: case 2 resume must be aip + 24")
ASSERT(c3_resume == c3_aip + 16, "causeid: case 3 resume must be aip + 16")
ASSERT(c4_resume == c4_aip + 16, "causeid: case 4 resume must be aip + 16")
ASSERT(c5_resume == c5_aip + 16, "causeid: case 5 resume must be aip + 16")
ASSERT(c6_resume == c6_aip + 16, "causeid: case 6 resume must be aip + 16")
ASSERT(c7_resume == c7_aip + 16, "causeid: case 7 resume must be aip + 16")
ASSERT(c8_resume == c8_aip + 24, "causeid: case 8 resume must be aip + 24")

ASSERT(c2_jump == c2_fault + 8, "causeid: case 2 jump must be the sub.o + 8 B")
ASSERT(c8_jump == c8_fault + 8, "causeid: case 8 jump must be the sub.o + 8 B")
