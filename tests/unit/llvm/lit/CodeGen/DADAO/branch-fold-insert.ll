;
; RUN: %llc -march=dadao -O2 -verify-machineinstrs -stop-after=branch-folder %s -o - \
; RUN:   | %FileCheck %s
;
; LLVM-059t / ISS-158: DADAOInstrInfo::{analyzeBranch,insertBranch,removeBranch}.
;
; Shape under test: a signed loop (`icmp slt` -> `br.n`/`br.p`) whose body does a
; cross-TU call, followed by a post-loop equality guard (`br.eq`/`br.ne`).  The
; Control Flow Optimizer tail-merges the two return paths and must *insert* an
; unconditional `jump_iiii`; the loop/guard conditional branches exercise the
; `br_*` (fall-through) analysis.  Before LLVM-059t this aborted with
; "Target didn't implement TargetInstrInfo::insertBranch!" (SIGABRT, exit 134).
;
; The suite is wired into `make check-lit` (INTEG-016t): `lit.cfg.py` provides
; the `%llc`/`%FileCheck` substitutions and a build-tree `test_exec_root`.
;
; The expected branch sequence is derived from the M4 branch model (see the
; task / contract-isa): unconditional = `jump_iiii`; the loop counter test
; lowers to a signed `br.*` on rD; the equality guard lowers to `br.nz`/`br.z`.
;
; CHECK-LABEL: bb.{{[0-9]+}}.cond:
; CHECK:         br_{{.*}}_rd
; CHECK-LABEL: bb.{{[0-9]+}}.done:
; CHECK:         br_{{.*}}_rd
; CHECK-LABEL: bb.{{[0-9]+}}.fail:
; CHECK:         jump_iiii
;
; IR semantics (host independent oracle):
;   acc = rw_acc(2) + ro_tbl[0..3](3+5+7+9) = 26 ; guard true -> 26 + 4 = 30.
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
  %is26 = icmp eq i64 %sum, 26
  br i1 %is26, label %ok, label %fail

ok:
  %r = add i64 %sum, 4
  ret i64 %r

fail:
  ret i64 1
}
