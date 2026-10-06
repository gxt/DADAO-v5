; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=NOPSEUDO

; `set.rd rd, imm64` constant expansion (ADR-0013 D11; spec/SimRISC-03
; §set.rd).  A constant is materialized with the minimal number of
; set.zw/set.ow + or.w/andn.w instructions; only the real hardware
; instructions are emitted (never `set.rd` text).
;
; NOPSEUDO-NOT: set.rd
;
; rwii encoding: word = (op<<24)|(ha<<18)|((wp&3)<<16)|(immu16)
;   op: or.w=0x48, andn.w=0x49, set.zw=0x4C, set.ow=0x4D
; seed: highest-order wyde differing from the fill (set.zw fills 0, set.ow
; fills 0xFFFF); corrections are emitted high-to-low.

; set.rd rd1, 0 -> set.zw rd1, wp0, 0x0
; word = 0x4C<<24|1<<18|0<<16|0 = 0x4C040000
; OBJ: {{[0-9a-f]+:}} 4c 04 00 00{{.*}}set.zw{{.*}}rd1, wp0, 0x0
; ASM: set.zw rd1, wp0, 0x0
set.rd rd1, 0

; set.rd rd2, -1 -> set.ow rd2, wp0, 0xffff
; word = 0x4D<<24|2<<18|0<<16|0xffff = 0x4D08FFFF
; OBJ: {{[0-9a-f]+:}} 4d 08 ff ff{{.*}}set.ow{{.*}}rd2, wp0, 0xffff
; ASM: set.ow rd2, wp0, 0xffff
set.rd rd2, -1

; set.rd rd3, -42 -> set.ow rd3, wp0, 0xffd6 (-42 low 16 bits)
; word = 0x4D<<24|3<<18|0<<16|0xffd6 = 0x4D0CFFD6
; OBJ: {{[0-9a-f]+:}} 4d 0c ff d6{{.*}}set.ow{{.*}}rd3, wp0, 0xffd6
; ASM: set.ow rd3, wp0, 0xffd6
set.rd rd3, -42

; set.rd rd4, ~(1<<5) -> set.ow rd4, wp0, 0xffdf
; word = 0x4D<<24|4<<18|0<<16|0xffdf = 0x4D10FFDF
; OBJ: {{[0-9a-f]+:}} 4d 10 ff df{{.*}}set.ow{{.*}}rd4, wp0, 0xffdf
; ASM: set.ow rd4, wp0, 0xffdf
set.rd rd4, ~(1<<5)

; set.rd rd5, 42 -> set.zw rd5, wp0, 0x2a
; word = 0x4C<<24|5<<18|0<<16|0x2a = 0x4C14002A
; OBJ: {{[0-9a-f]+:}} 4c 14 00 2a{{.*}}set.zw{{.*}}rd5, wp0, 0x2a
; ASM: set.zw rd5, wp0, 0x2a
set.rd rd5, 42

; set.rd rd6, 0x1234ABCD -> set.zw rd6, wp1, 0x1234 ; or.w rd6, wp0, 0xabcd
; set.zw: 0x4C<<24|6<<18|1<<16|0x1234 = 0x4C191234
; or.w  : 0x48<<24|6<<18|0<<16|0xabcd = 0x4818ABCD
; OBJ: {{[0-9a-f]+:}} 4c 19 12 34{{.*}}set.zw{{.*}}rd6, wp1, 0x1234
; OBJ-NEXT: {{[0-9a-f]+:}} 48 18 ab cd{{.*}}or.w{{.*}}rd6, wp0, 0xabcd
; ASM: set.zw rd6, wp1, 0x1234
; ASM: or.w rd6, wp0, 0xabcd
set.rd rd6, 0x1234ABCD

; set.rd rd7, 0xDEADBEEFCAFEBABE -> set.zw wp3 ; or.w wp2 ; or.w wp1 ; or.w wp0
; set.zw wp3: 0x4C<<24|7<<18|3<<16|0xdead = 0x4C1FDEAD
; or.w   wp2: 0x48<<24|7<<18|2<<16|0xbeef = 0x481EBEEF
; or.w   wp1: 0x48<<24|7<<18|1<<16|0xcafe = 0x481DCAFE
; or.w   wp0: 0x48<<24|7<<18|0<<16|0xbabe = 0x481CBABE
; OBJ: {{[0-9a-f]+:}} 4c 1f de ad{{.*}}set.zw{{.*}}rd7, wp3, 0xdead
; OBJ-NEXT: {{[0-9a-f]+:}} 48 1e be ef{{.*}}or.w{{.*}}rd7, wp2, 0xbeef
; OBJ-NEXT: {{[0-9a-f]+:}} 48 1d ca fe{{.*}}or.w{{.*}}rd7, wp1, 0xcafe
; OBJ-NEXT: {{[0-9a-f]+:}} 48 1c ba be{{.*}}or.w{{.*}}rd7, wp0, 0xbabe
; ASM: set.zw rd7, wp3, 0xdead
; ASM: or.w rd7, wp2, 0xbeef
; ASM: or.w rd7, wp1, 0xcafe
; ASM: or.w rd7, wp0, 0xbabe
set.rd rd7, 0xDEADBEEFCAFEBABE

; set.rd rd8, 0x12340000FFFFFFFF -> set.ow rd8, wp3, 0x1234 ; andn.w rd8, wp2, 0xffff
; (2 corrections vs 3 or.w: the set.ow fill is cheaper)
; set.ow wp3: 0x4D<<24|8<<18|3<<16|0x1234 = 0x4D231234
; andn.w wp2: 0x49<<24|8<<18|2<<16|0xffff = 0x4922FFFF
; OBJ: {{[0-9a-f]+:}} 4d 23 12 34{{.*}}set.ow{{.*}}rd8, wp3, 0x1234
; OBJ-NEXT: {{[0-9a-f]+:}} 49 22 ff ff{{.*}}andn.w{{.*}}rd8, wp2, 0xffff
; ASM: set.ow rd8, wp3, 0x1234
; ASM: andn.w rd8, wp2, 0xffff
set.rd rd8, 0x12340000FFFFFFFF
