; TESTCASES-030t / M4 L3 vector -- program "multi_section_loop", TU A (data + callee).
;
; Coverage:
;   * `.rodata`: @ro_tbl is a `constant` array (initialised read-only data).
;   * `.data`  : @rw_acc is a non-constant global with a non-zero initialiser.
;   * `.bss`   : @bss_cnt is a non-constant zero-initialised global (NOBITS).
;   * cross-TU : @get_ro is exported and called from TU B -> R_DADAO_REL26.
;   * ABS48    : every @ro_tbl / @rw_acc / @bss_cnt address in .text is
;                cross-section -> R_DADAO_ABS48.
;
; IR semantics (host independent oracle):
;   ro_tbl = {3, 5, 7, 9} ; rw_acc = 2 ; bss_cnt = 0
;   get_ro(i) = ro_tbl[i]   (8-byte elements; big-endian layout is irrelevant
;                            here because only whole i64 elements are touched)

@ro_tbl  = constant [4 x i64] [i64 3, i64 5, i64 7, i64 9], align 8
@rw_acc  = global i64 2, align 8
@bss_cnt = global i64 0, align 8

define i64 @get_ro(i64 %i) noinline {
entry:
  %p = getelementptr [4 x i64], [4 x i64]* @ro_tbl, i64 0, i64 %i
  %v = load i64, i64* %p, align 8
  ret i64 %v
}
