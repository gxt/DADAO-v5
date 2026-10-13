; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=obj %s -o %t
; RUN: %llvm_objdump -d --triple=dadao-unknown-elf %t | %FileCheck %s --check-prefix=OBJ
; RUN: %llvm_mc --triple=dadao-unknown-elf -filetype=asm %s | %FileCheck %s --check-prefix=ASM

; FP (scope: fp) encoding round-trip: all 60 instructions.
; Bytes are hand-computed from contracts/opcodes.yaml:
;   32-bit big-endian word = (op<<24)|(ha<<18)|(hb<<12)|(hc<<6)|hd
;   rrii : ha=ra, hb=rb, [11:0]=imm12
;   rrri : ha=ra, hb=rb, hc=rc, hd=immu6
;   rwii : ha=ra, hb[5:4]=wp, [15:0]=immu16 (hb[3:0]:hc:hd)
;   rrrr : ha=ra, hb=rb, hc=rc, hd=rd
;   orrr : ha=opx, hb=rb, hc=rc, hd=rd
;   orri : ha=opx, hb=rb, hc=rc, hd=immu6
; Block forms: {start:end} count = end-start+1, encoded into the shared imm6.


; ld.t rf4, [rb2, 16]
; op=0x16  word = 0x16102010  bytes = 16 10 20 10
; OBJ: {{[0-9a-f]+:}} 16 10 20 10{{.*}}ld.t{{.*}}rf4, [rb2, 16]
; ASM: ld.t rf4, [rb2, 16]
ld.t rf4, [rb2, 16]

; st.t rf6, [rb3, 24]
; op=0x17  word = 0x17183018  bytes = 17 18 30 18
; OBJ: {{[0-9a-f]+:}} 17 18 30 18{{.*}}st.t{{.*}}rf6, [rb3, 24]
; ASM: st.t rf6, [rb3, 24]
st.t rf6, [rb3, 24]

; ld.o rf8, [rb4, 32]
; op=0x26  word = 0x26204020  bytes = 26 20 40 20
; OBJ: {{[0-9a-f]+:}} 26 20 40 20{{.*}}ld.o{{.*}}rf8, [rb4, 32]
; ASM: ld.o rf8, [rb4, 32]
ld.o rf8, [rb4, 32]

; st.o rf10, [rb5, 40]
; op=0x27  word = 0x27285028  bytes = 27 28 50 28
; OBJ: {{[0-9a-f]+:}} 27 28 50 28{{.*}}st.o{{.*}}rf10, [rb5, 40]
; ASM: st.o rf10, [rb5, 40]
st.o rf10, [rb5, 40]

; ldm.t {rf4:rf6}, [rb2, rd3]
; op=0x2E  word = 0x2E1020C3  bytes = 2e 10 20 c3
; OBJ: {{[0-9a-f]+:}} 2e 10 20 c3{{.*}}ldm.t{{.*}}{rf4:rf6}, [rb2, rd3]
; ASM: ldm.t {rf4:rf6}, [rb2, rd3]
ldm.t {rf4:rf6}, [rb2, rd3]

; stm.t {rf8:rf10}, [rb4, rd5]
; op=0x2F  word = 0x2F204143  bytes = 2f 20 41 43
; OBJ: {{[0-9a-f]+:}} 2f 20 41 43{{.*}}stm.t{{.*}}{rf8:rf10}, [rb4, rd5]
; ASM: stm.t {rf8:rf10}, [rb4, rd5]
stm.t {rf8:rf10}, [rb4, rd5]

; ldm.o {rf12:rf14}, [rb6, rd7]
; op=0x3E  word = 0x3E3061C3  bytes = 3e 30 61 c3
; OBJ: {{[0-9a-f]+:}} 3e 30 61 c3{{.*}}ldm.o{{.*}}{rf12:rf14}, [rb6, rd7]
; ASM: ldm.o {rf12:rf14}, [rb6, rd7]
ldm.o {rf12:rf14}, [rb6, rd7]

; stm.o {rf16:rf18}, [rb8, rd9]
; op=0x3F  word = 0x3F408243  bytes = 3f 40 82 43
; OBJ: {{[0-9a-f]+:}} 3f 40 82 43{{.*}}stm.o{{.*}}{rf16:rf18}, [rb8, rd9]
; ASM: stm.o {rf16:rf18}, [rb8, rd9]
stm.o {rf16:rf18}, [rb8, rd9]

; set.w rf4, wp0, 0x1234
; op=0x4F  word = 0x4F101234  bytes = 4f 10 12 34
; OBJ: {{[0-9a-f]+:}} 4f 10 12 34{{.*}}set.w{{.*}}rf4, wp0, 0x1234
; ASM: set.w rf4, wp0, 0x1234
set.w rf4, wp0, 0x1234

; cs.eq {rd8, rd0}?, rf4, rf6
; op=0x5E  word = 0x5E200106  bytes = 5e 20 01 06
; OBJ: {{[0-9a-f]+:}} 5e 20 01 06{{.*}}cs.eq{{.*}}{rd8, rd0}?, rf4, rf6
; ASM: cs.eq {rd8, rd0}?, rf4, rf6
cs.eq {rd8, rd0}?, rf4, rf6

; cs.ne {rd10, rd2}?, rf8, rf10
; op=0x5F  word = 0x5F28220A  bytes = 5f 28 22 0a
; OBJ: {{[0-9a-f]+:}} 5f 28 22 0a{{.*}}cs.ne{{.*}}{rd10, rd2}?, rf8, rf10
; ASM: cs.ne {rd10, rd2}?, rf8, rf10
cs.ne {rd10, rd2}?, rf8, rf10

; cs.n {rd12}?, rf4, rf6, rf8
; op=0x61  word = 0x61304188  bytes = 61 30 41 88
; OBJ: {{[0-9a-f]+:}} 61 30 41 88{{.*}}cs.n{{.*}}{rd12}?, rf4, rf6, rf8
; ASM: cs.n {rd12}?, rf4, rf6, rf8
cs.n {rd12}?, rf4, rf6, rf8

; cs.z {rd14}?, rf10, rf12, rf14
; op=0x63  word = 0x6338A30E  bytes = 63 38 a3 0e
; OBJ: {{[0-9a-f]+:}} 63 38 a3 0e{{.*}}cs.z{{.*}}{rd14}?, rf10, rf12, rf14
; ASM: cs.z {rd14}?, rf10, rf12, rf14
cs.z {rd14}?, rf10, rf12, rf14

; cs.p {rd16}?, rf16, rf18, rf20
; op=0x65  word = 0x65410494  bytes = 65 41 04 94
; OBJ: {{[0-9a-f]+:}} 65 41 04 94{{.*}}cs.p{{.*}}{rd16}?, rf16, rf18, rf20
; ASM: cs.p {rd16}?, rf16, rf18, rf20
cs.p {rd16}?, rf16, rf18, rf20

; ftadd rf4, rf6, rf8
; op=0x44 ha=0x10(opx)  word = 0x44404188  bytes = 44 40 41 88
; OBJ: {{[0-9a-f]+:}} 44 40 41 88{{.*}}ftadd{{.*}}rf4, rf6, rf8
; ASM: ftadd rf4, rf6, rf8
ftadd rf4, rf6, rf8

; ftsub rf4, rf6, rf8
; op=0x44 ha=0x11(opx)  word = 0x44444188  bytes = 44 44 41 88
; OBJ: {{[0-9a-f]+:}} 44 44 41 88{{.*}}ftsub{{.*}}rf4, rf6, rf8
; ASM: ftsub rf4, rf6, rf8
ftsub rf4, rf6, rf8

; ftmul rf4, rf6, rf8
; op=0x44 ha=0x12(opx)  word = 0x44484188  bytes = 44 48 41 88
; OBJ: {{[0-9a-f]+:}} 44 48 41 88{{.*}}ftmul{{.*}}rf4, rf6, rf8
; ASM: ftmul rf4, rf6, rf8
ftmul rf4, rf6, rf8

; ftdiv rf4, rf6, rf8
; op=0x44 ha=0x13(opx)  word = 0x444C4188  bytes = 44 4c 41 88
; OBJ: {{[0-9a-f]+:}} 44 4c 41 88{{.*}}ftdiv{{.*}}rf4, rf6, rf8
; ASM: ftdiv rf4, rf6, rf8
ftdiv rf4, rf6, rf8

; ftrem rf4, rf6, rf8
; op=0x44 ha=0x14(opx)  word = 0x44504188  bytes = 44 50 41 88
; OBJ: {{[0-9a-f]+:}} 44 50 41 88{{.*}}ftrem{{.*}}rf4, rf6, rf8
; ASM: ftrem rf4, rf6, rf8
ftrem rf4, rf6, rf8

; ftsclb rf4, rf6, rf8
; op=0x44 ha=0x15(opx)  word = 0x44544188  bytes = 44 54 41 88
; OBJ: {{[0-9a-f]+:}} 44 54 41 88{{.*}}ftsclb{{.*}}rf4, rf6, rf8
; ASM: ftsclb rf4, rf6, rf8
ftsclb rf4, rf6, rf8

; ftsgnn rf4, rf6, rf8
; op=0x44 ha=0x16(opx)  word = 0x44584188  bytes = 44 58 41 88
; OBJ: {{[0-9a-f]+:}} 44 58 41 88{{.*}}ftsgnn{{.*}}rf4, rf6, rf8
; ASM: ftsgnn rf4, rf6, rf8
ftsgnn rf4, rf6, rf8

; ftsgnj rf4, rf6, rf8
; op=0x44 ha=0x17(opx)  word = 0x445C4188  bytes = 44 5c 41 88
; OBJ: {{[0-9a-f]+:}} 44 5c 41 88{{.*}}ftsgnj{{.*}}rf4, rf6, rf8
; ASM: ftsgnj rf4, rf6, rf8
ftsgnj rf4, rf6, rf8

; foadd rf4, rf6, rf8
; op=0x44 ha=0x18(opx)  word = 0x44604188  bytes = 44 60 41 88
; OBJ: {{[0-9a-f]+:}} 44 60 41 88{{.*}}foadd{{.*}}rf4, rf6, rf8
; ASM: foadd rf4, rf6, rf8
foadd rf4, rf6, rf8

; fosub rf4, rf6, rf8
; op=0x44 ha=0x19(opx)  word = 0x44644188  bytes = 44 64 41 88
; OBJ: {{[0-9a-f]+:}} 44 64 41 88{{.*}}fosub{{.*}}rf4, rf6, rf8
; ASM: fosub rf4, rf6, rf8
fosub rf4, rf6, rf8

; fomul rf4, rf6, rf8
; op=0x44 ha=0x1A(opx)  word = 0x44684188  bytes = 44 68 41 88
; OBJ: {{[0-9a-f]+:}} 44 68 41 88{{.*}}fomul{{.*}}rf4, rf6, rf8
; ASM: fomul rf4, rf6, rf8
fomul rf4, rf6, rf8

; fodiv rf4, rf6, rf8
; op=0x44 ha=0x1B(opx)  word = 0x446C4188  bytes = 44 6c 41 88
; OBJ: {{[0-9a-f]+:}} 44 6c 41 88{{.*}}fodiv{{.*}}rf4, rf6, rf8
; ASM: fodiv rf4, rf6, rf8
fodiv rf4, rf6, rf8

; forem rf4, rf6, rf8
; op=0x44 ha=0x1C(opx)  word = 0x44704188  bytes = 44 70 41 88
; OBJ: {{[0-9a-f]+:}} 44 70 41 88{{.*}}forem{{.*}}rf4, rf6, rf8
; ASM: forem rf4, rf6, rf8
forem rf4, rf6, rf8

; fosclb rf4, rf6, rf8
; op=0x44 ha=0x1D(opx)  word = 0x44744188  bytes = 44 74 41 88
; OBJ: {{[0-9a-f]+:}} 44 74 41 88{{.*}}fosclb{{.*}}rf4, rf6, rf8
; ASM: fosclb rf4, rf6, rf8
fosclb rf4, rf6, rf8

; fosgnn rf4, rf6, rf8
; op=0x44 ha=0x1E(opx)  word = 0x44784188  bytes = 44 78 41 88
; OBJ: {{[0-9a-f]+:}} 44 78 41 88{{.*}}fosgnn{{.*}}rf4, rf6, rf8
; ASM: fosgnn rf4, rf6, rf8
fosgnn rf4, rf6, rf8

; fosgnj rf4, rf6, rf8
; op=0x44 ha=0x1F(opx)  word = 0x447C4188  bytes = 44 7c 41 88
; OBJ: {{[0-9a-f]+:}} 44 7c 41 88{{.*}}fosgnj{{.*}}rf4, rf6, rf8
; ASM: fosgnj rf4, rf6, rf8
fosgnj rf4, rf6, rf8

; ftqcmp rd4, rf6, rf8
; op=0x44 ha=0x20(opx)  word = 0x44804188  bytes = 44 80 41 88
; OBJ: {{[0-9a-f]+:}} 44 80 41 88{{.*}}ftqcmp{{.*}}rd4, rf6, rf8
; ASM: ftqcmp rd4, rf6, rf8
ftqcmp rd4, rf6, rf8

; ftscmp rd4, rf6, rf8
; op=0x44 ha=0x21(opx)  word = 0x44844188  bytes = 44 84 41 88
; OBJ: {{[0-9a-f]+:}} 44 84 41 88{{.*}}ftscmp{{.*}}rd4, rf6, rf8
; ASM: ftscmp rd4, rf6, rf8
ftscmp rd4, rf6, rf8

; foqcmp rd4, rf6, rf8
; op=0x44 ha=0x28(opx)  word = 0x44A04188  bytes = 44 a0 41 88
; OBJ: {{[0-9a-f]+:}} 44 a0 41 88{{.*}}foqcmp{{.*}}rd4, rf6, rf8
; ASM: foqcmp rd4, rf6, rf8
foqcmp rd4, rf6, rf8

; foscmp rd4, rf6, rf8
; op=0x44 ha=0x29(opx)  word = 0x44A44188  bytes = 44 a4 41 88
; OBJ: {{[0-9a-f]+:}} 44 a4 41 88{{.*}}foscmp{{.*}}rd4, rf6, rf8
; ASM: foscmp rd4, rf6, rf8
foscmp rd4, rf6, rf8

; ftcls {rd4:rd6}, {rf8:rf10}
; op=0x44 ha=0x00(opx)  word = 0x44004203  bytes = 44 00 42 03
; OBJ: {{[0-9a-f]+:}} 44 00 42 03{{.*}}ftcls{{.*}}{rd4:rd6}, {rf8:rf10}
; ASM: ftcls {rd4:rd6}, {rf8:rf10}
ftcls {rd4:rd6}, {rf8:rf10}

; ft2fo {rf4:rf6}, {rf8:rf10}
; op=0x44 ha=0x01(opx)  word = 0x44044203  bytes = 44 04 42 03
; OBJ: {{[0-9a-f]+:}} 44 04 42 03{{.*}}ft2fo{{.*}}{rf4:rf6}, {rf8:rf10}
; ASM: ft2fo {rf4:rf6}, {rf8:rf10}
ft2fo {rf4:rf6}, {rf8:rf10}

; ft2ft {rf10:rf12}, {rf14:rf16}
; op=0x44 ha=0x02(opx)  word = 0x4408A383  bytes = 44 08 a3 83
; OBJ: {{[0-9a-f]+:}} 44 08 a3 83{{.*}}ft2ft{{.*}}{rf10:rf12}, {rf14:rf16}
; ASM: ft2ft {rf10:rf12}, {rf14:rf16}
ft2ft {rf10:rf12}, {rf14:rf16}

; ftroot rf4, rf6, 2
; op=0x44 ha=0x06(opx)  word = 0x44184182  bytes = 44 18 41 82
; OBJ: {{[0-9a-f]+:}} 44 18 41 82{{.*}}ftroot{{.*}}rf4, rf6, 2
; ASM: ftroot rf4, rf6, 2
ftroot rf4, rf6, 2

; focls {rd8:rd10}, {rf12:rf14}
; op=0x44 ha=0x08(opx)  word = 0x44208303  bytes = 44 20 83 03
; OBJ: {{[0-9a-f]+:}} 44 20 83 03{{.*}}focls{{.*}}{rd8:rd10}, {rf12:rf14}
; ASM: focls {rd8:rd10}, {rf12:rf14}
focls {rd8:rd10}, {rf12:rf14}

; fo2ft {rf4:rf6}, {rf8:rf10}
; op=0x44 ha=0x09(opx)  word = 0x44244203  bytes = 44 24 42 03
; OBJ: {{[0-9a-f]+:}} 44 24 42 03{{.*}}fo2ft{{.*}}{rf4:rf6}, {rf8:rf10}
; ASM: fo2ft {rf4:rf6}, {rf8:rf10}
fo2ft {rf4:rf6}, {rf8:rf10}

; fo2fo {rf10:rf12}, {rf14:rf16}
; op=0x44 ha=0x0A(opx)  word = 0x4428A383  bytes = 44 28 a3 83
; OBJ: {{[0-9a-f]+:}} 44 28 a3 83{{.*}}fo2fo{{.*}}{rf10:rf12}, {rf14:rf16}
; ASM: fo2fo {rf10:rf12}, {rf14:rf16}
fo2fo {rf10:rf12}, {rf14:rf16}

; foroot rf4, rf6, 2
; op=0x44 ha=0x0E(opx)  word = 0x44384182  bytes = 44 38 41 82
; OBJ: {{[0-9a-f]+:}} 44 38 41 82{{.*}}foroot{{.*}}rf4, rf6, 2
; ASM: foroot rf4, rf6, 2
foroot rf4, rf6, 2

; ft2it {rd4:rd6}, {rf8:rf10}
; op=0x44 ha=0x30(opx)  word = 0x44C04203  bytes = 44 c0 42 03
; OBJ: {{[0-9a-f]+:}} 44 c0 42 03{{.*}}ft2it{{.*}}{rd4:rd6}, {rf8:rf10}
; ASM: ft2it {rd4:rd6}, {rf8:rf10}
ft2it {rd4:rd6}, {rf8:rf10}

; ft2io {rd10:rd12}, {rf14:rf16}
; op=0x44 ha=0x31(opx)  word = 0x44C4A383  bytes = 44 c4 a3 83
; OBJ: {{[0-9a-f]+:}} 44 c4 a3 83{{.*}}ft2io{{.*}}{rd10:rd12}, {rf14:rf16}
; ASM: ft2io {rd10:rd12}, {rf14:rf16}
ft2io {rd10:rd12}, {rf14:rf16}

; ft2ut {rd8:rd10}, {rf12:rf14}
; op=0x44 ha=0x32(opx)  word = 0x44C88303  bytes = 44 c8 83 03
; OBJ: {{[0-9a-f]+:}} 44 c8 83 03{{.*}}ft2ut{{.*}}{rd8:rd10}, {rf12:rf14}
; ASM: ft2ut {rd8:rd10}, {rf12:rf14}
ft2ut {rd8:rd10}, {rf12:rf14}

; ft2uo {rd14:rd16}, {rf18:rf20}
; op=0x44 ha=0x33(opx)  word = 0x44CCE483  bytes = 44 cc e4 83
; OBJ: {{[0-9a-f]+:}} 44 cc e4 83{{.*}}ft2uo{{.*}}{rd14:rd16}, {rf18:rf20}
; ASM: ft2uo {rd14:rd16}, {rf18:rf20}
ft2uo {rd14:rd16}, {rf18:rf20}

; it2ft {rf4:rf6}, {rd8:rd10}
; op=0x44 ha=0x34(opx)  word = 0x44D04203  bytes = 44 d0 42 03
; OBJ: {{[0-9a-f]+:}} 44 d0 42 03{{.*}}it2ft{{.*}}{rf4:rf6}, {rd8:rd10}
; ASM: it2ft {rf4:rf6}, {rd8:rd10}
it2ft {rf4:rf6}, {rd8:rd10}

; io2ft {rf10:rf12}, {rd14:rd16}
; op=0x44 ha=0x35(opx)  word = 0x44D4A383  bytes = 44 d4 a3 83
; OBJ: {{[0-9a-f]+:}} 44 d4 a3 83{{.*}}io2ft{{.*}}{rf10:rf12}, {rd14:rd16}
; ASM: io2ft {rf10:rf12}, {rd14:rd16}
io2ft {rf10:rf12}, {rd14:rd16}

; ut2ft {rf8:rf10}, {rd12:rd14}
; op=0x44 ha=0x36(opx)  word = 0x44D88303  bytes = 44 d8 83 03
; OBJ: {{[0-9a-f]+:}} 44 d8 83 03{{.*}}ut2ft{{.*}}{rf8:rf10}, {rd12:rd14}
; ASM: ut2ft {rf8:rf10}, {rd12:rd14}
ut2ft {rf8:rf10}, {rd12:rd14}

; uo2ft {rf14:rf16}, {rd18:rd20}
; op=0x44 ha=0x37(opx)  word = 0x44DCE483  bytes = 44 dc e4 83
; OBJ: {{[0-9a-f]+:}} 44 dc e4 83{{.*}}uo2ft{{.*}}{rf14:rf16}, {rd18:rd20}
; ASM: uo2ft {rf14:rf16}, {rd18:rd20}
uo2ft {rf14:rf16}, {rd18:rd20}

; fo2it {rd4:rd6}, {rf8:rf10}
; op=0x44 ha=0x38(opx)  word = 0x44E04203  bytes = 44 e0 42 03
; OBJ: {{[0-9a-f]+:}} 44 e0 42 03{{.*}}fo2it{{.*}}{rd4:rd6}, {rf8:rf10}
; ASM: fo2it {rd4:rd6}, {rf8:rf10}
fo2it {rd4:rd6}, {rf8:rf10}

; fo2io {rd10:rd12}, {rf14:rf16}
; op=0x44 ha=0x39(opx)  word = 0x44E4A383  bytes = 44 e4 a3 83
; OBJ: {{[0-9a-f]+:}} 44 e4 a3 83{{.*}}fo2io{{.*}}{rd10:rd12}, {rf14:rf16}
; ASM: fo2io {rd10:rd12}, {rf14:rf16}
fo2io {rd10:rd12}, {rf14:rf16}

; fo2ut {rd8:rd10}, {rf12:rf14}
; op=0x44 ha=0x3A(opx)  word = 0x44E88303  bytes = 44 e8 83 03
; OBJ: {{[0-9a-f]+:}} 44 e8 83 03{{.*}}fo2ut{{.*}}{rd8:rd10}, {rf12:rf14}
; ASM: fo2ut {rd8:rd10}, {rf12:rf14}
fo2ut {rd8:rd10}, {rf12:rf14}

; fo2uo {rd14:rd16}, {rf18:rf20}
; op=0x44 ha=0x3B(opx)  word = 0x44ECE483  bytes = 44 ec e4 83
; OBJ: {{[0-9a-f]+:}} 44 ec e4 83{{.*}}fo2uo{{.*}}{rd14:rd16}, {rf18:rf20}
; ASM: fo2uo {rd14:rd16}, {rf18:rf20}
fo2uo {rd14:rd16}, {rf18:rf20}

; it2fo {rf4:rf6}, {rd8:rd10}
; op=0x44 ha=0x3C(opx)  word = 0x44F04203  bytes = 44 f0 42 03
; OBJ: {{[0-9a-f]+:}} 44 f0 42 03{{.*}}it2fo{{.*}}{rf4:rf6}, {rd8:rd10}
; ASM: it2fo {rf4:rf6}, {rd8:rd10}
it2fo {rf4:rf6}, {rd8:rd10}

; rd2rf {rf10:rf12}, {rd14:rd16}
; op=0x40 ha=0x3D(opx)  word = 0x40F4A383  bytes = 40 f4 a3 83
; OBJ: {{[0-9a-f]+:}} 40 f4 a3 83{{.*}}rd2rf{{.*}}{rf10:rf12}, {rd14:rd16}
; ASM: rd2rf {rf10:rf12}, {rd14:rd16}
rd2rf {rf10:rf12}, {rd14:rd16}

; io2fo {rf8:rf10}, {rd12:rd14}
; op=0x44 ha=0x3D(opx)  word = 0x44F48303  bytes = 44 f4 83 03
; OBJ: {{[0-9a-f]+:}} 44 f4 83 03{{.*}}io2fo{{.*}}{rf8:rf10}, {rd12:rd14}
; ASM: io2fo {rf8:rf10}, {rd12:rd14}
io2fo {rf8:rf10}, {rd12:rd14}

; rf2rd {rd14:rd16}, {rf18:rf20}
; op=0x40 ha=0x3E(opx)  word = 0x40F8E483  bytes = 40 f8 e4 83
; OBJ: {{[0-9a-f]+:}} 40 f8 e4 83{{.*}}rf2rd{{.*}}{rd14:rd16}, {rf18:rf20}
; ASM: rf2rd {rd14:rd16}, {rf18:rf20}
rf2rd {rd14:rd16}, {rf18:rf20}

; ut2fo {rf4:rf6}, {rd8:rd10}
; op=0x44 ha=0x3E(opx)  word = 0x44F84203  bytes = 44 f8 42 03
; OBJ: {{[0-9a-f]+:}} 44 f8 42 03{{.*}}ut2fo{{.*}}{rf4:rf6}, {rd8:rd10}
; ASM: ut2fo {rf4:rf6}, {rd8:rd10}
ut2fo {rf4:rf6}, {rd8:rd10}

; uo2fo {rf10:rf12}, {rd14:rd16}
; op=0x44 ha=0x3F(opx)  word = 0x44FCA383  bytes = 44 fc a3 83
; OBJ: {{[0-9a-f]+:}} 44 fc a3 83{{.*}}uo2fo{{.*}}{rf10:rf12}, {rd14:rd16}
; ASM: uo2fo {rf10:rf12}, {rd14:rd16}
uo2fo {rf10:rf12}, {rd14:rd16}
