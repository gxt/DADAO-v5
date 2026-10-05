	.file	"ptr_add_offset.ll"
	.text
	.globl	main                            ; -- Begin function main
	.type	main,@function
main:                                   ; @main
; %bb.0:                                ; %entry
add.si rb1, -40
set.zw rd8, wp0, 0x14
st.o rd8, [rb1, 0]
rb2rb {rb8}, {rb1}
add.si rb8, 8
ld.o rd8, [rb1, 0]
add.o rb8, rb8, rd8
set.zw rd8, wp0, 0xab
st.b rd8, [rb8, 0]
ld.ub rd31, [rb8, 0]
add.si rb1, 40
ret rd0, 0
.Lfunc_end0:
	.size	main, .Lfunc_end0-main
                                        ; -- End function
	.section	".note.GNU-stack","",@progbits
