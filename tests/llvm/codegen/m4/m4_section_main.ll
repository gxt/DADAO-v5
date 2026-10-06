; TESTCASES-030t / M4 L3 vector -- program "multi_section_loop", TU B (main).
;
; Coverage:
;   * cross-TU direct call : `call i64 @get_ro(...)` -> R_DADAO_REL26.
;   * cross-TU global      : @rw_acc / @bss_cnt defined in TU A are addressed
;                            here -> R_DADAO_ABS48.
;   * signed loop branch   : `icmp slt` + conditional br -> the riii signed
;                            compare-branch form (R_DADAO_REL20 field).
;   * run-time read/write  : @rw_acc and @bss_cnt are both loaded and stored.
;
; IR semantics (host independent oracle):
;   acc = rw_acc (= 2) ; i = bss_cnt (= 0)
;   while (i < 4) { acc += get_ro(i) ; i += 1 }   -> acc = 2+3+5+7+9 = 26
;   return acc + 4                                 -> 30.
;
;   The loop counter lives in a global (.bss) on purpose: no phi / no alloca,
;   so the host interpreter executes the very same straight-line + branch IR.
;
;   NOTE (backend finding, see task completion area): a *post-loop* equality
;   guard (br.eq/br.ne on a value produced after the loop) makes the M4 backend
;   crash in the Control Flow Optimizer ("Target didn't implement
;   TargetInstrInfo::insertBranch!").  The REL14 branch form is therefore
;   exercised by `multi_tu_call` instead, and this program keeps only the
;   signed (REL20) loop branch.

@rw_acc  = external global i64, align 8
@bss_cnt = external global i64, align 8

declare i64 @get_ro(i64)

define i64 @main() noinline {
entry:
  br label %cond

cond:
  %i = load i64, i64* @bss_cnt, align 8
  %c = icmp slt i64 %i, 4
  br i1 %c, label %body, label %done

body:
  %v = call i64 @get_ro(i64 %i)
  %a = load i64, i64* @rw_acc, align 8
  %s = add i64 %a, %v
  store i64 %s, i64* @rw_acc, align 8
  %i1 = add i64 %i, 1
  store i64 %i1, i64* @bss_cnt, align 8
  br label %cond

done:
  %sum = load i64, i64* @rw_acc, align 8
  %r = add i64 %sum, 4
  ret i64 %r
}
