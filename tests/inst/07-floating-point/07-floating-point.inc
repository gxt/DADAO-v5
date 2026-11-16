@@ tests/inst/07-floating-point/07-floating-point.inc — **07-floating-point 册专用**宏层（m15-testcases-002 下沉）
@@
@@ 口径：本文件只放**本册**用的宏；跨册宏在 `tests/inst/macros/inst_test.inc`，
@@ 单文件宏直接写在该 `.S` 内（门控 `check-inst-macro-scope` 机械判）。
@@ 本册每个 `.S` 在共享层之后 `.include`：
@@   .include "tests/inst/macros/inst_test.inc"
@@   .include "tests/inst/07-floating-point/07-floating-point.inc"
@@
@@ FCSR 环境：清异常状态（wp0 只命中 [4:0]）+ 设舍入模式（wp2 只命中 [33:32]）
.macro __FP_ENV rm
	set.w	rf0, wp0, 0x0000
	set.w	rf0, wp2, \rm
.endm
@@ 标志断言 + 结果比较（共用一个点号；结果追加进结果缓冲）
.macro __FP_CHECK pt, w, dst, exp, flags
	rf2rd	{rd21:rd21}, {rf0:rf0}
	ext.uo	rd21, rd21, 4
	__VERIFY_RD \pt, rd21, \flags
	rf2rd	{rd21:rd21}, {\dst:\dst}
	.ifc	\w, ft
	ext.uo	rd21, rd21, 31
	.endif
	__CHECK_RD \pt, rd21, \exp
.endm
@@ 标志断言 + 整 64 位结果比较（ft 只写低 32、高 32 必须保持）；判据同 `__CHECK_RD`
.macro __FP_CHK64 pt, dst, exp, flags
	rf2rd	{rd21:rd21}, {rf0:rf0}
	ext.uo	rd21, rd21, 4
	__VERIFY_RD \pt, rd21, \flags
	rf2rd	{rd21:rd21}, {\dst:\dst}
	__LI	rd20, \exp
	__REC	rd21
	br.eq	{rd20, rd21}?, [rb0, __fpchk_\@]
	__EXIT	\pt
__fpchk_\@:
.endm
@@ 源初值经 `__LI_RF`（不经浮点指令）；目的预置 0xDEADBEEFCAFEF00D（ft 只写低 32）
.macro __FP_RD1 dst, src, sval
	.ifnc	\src, rf0
	__LI_RF	\src, \sval
	.endif
	.ifnc	\dst, \src
	__LI_RF	\dst, 0xDEADBEEFCAFEF00D
	.endif
.endm
@@ 源初值（rf）与指数（rd，rd0 不装载）经整数通路装配；目的预置 0xDEADBEEFCAFEF00D
.macro __FP_RD2 dst, src, sval, ereg, eval
	.ifnc	\src, rf0
	__LI_RF	\src, \sval
	.endif
	.ifnc	\ereg, rd0
	__LI	\ereg, \eval
	.endif
	.ifnc	\dst, \src
	__LI_RF	\dst, 0xDEADBEEFCAFEF00D
	.endif
.endm
@@ 两个 rf 源 + 目的预置（rf0 作符号源时经 `__FP_ENV` 建立，不装载）
.macro __FP_RD3 dst, src, sval, d, dval
	.ifnc	\src, rf0
	__LI_RF	\src, \sval
	.endif
	.ifnc	\d, rf0
	.ifnc	\d, \src
	__LI_RF	\d, \dval
	.endif
	.endif
	.ifnc	\dst, \src
	.ifnc	\dst, \d
	__LI_RF	\dst, 0xDEADBEEFCAFEF00D
	.endif
	.endif
.endm
@@ TEST_FPRND(pt, 助记符, 目的, 源, 源值, immu6, rf0[33:32], 期望, 期望标志)
.macro TEST_FPRND pt, mnem, dst, src, sval, cvt, rfm, exp, flags
	__FP_ENV \rfm
	__FP_RD1 \dst, \src, \sval
	\mnem	\dst, \src, \cvt
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm
@@ TEST_FPRND_ENC(pt, 编码字, 目的, 源, 源值, rf0[33:32], 期望, 期望标志)
.macro TEST_FPRND_ENC pt, enc, dst, src, sval, rfm, exp, flags
	__FP_ENV \rfm
	__FP_RD1 \dst, \src, \sval
	.dd.t32	\enc
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm
@@ TEST_FPSCLB(pt, 助记符, 目的, 源, 源值, 指数源rd, 指数值, rf0[33:32], 期望, 期望标志)
.macro TEST_FPSCLB pt, mnem, dst, src, sval, ereg, eval, rfm, exp, flags
	__FP_ENV \rfm
	__FP_RD2 \dst, \src, \sval, \ereg, \eval
	\mnem	\dst, \src, \ereg
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm
@@ TEST_FPSCLB_ENC(pt, 编码字, 目的, 源, 源值, 指数源rd, 指数值, rf0[33:32], 期望, 期望标志)
.macro TEST_FPSCLB_ENC pt, enc, dst, src, sval, ereg, eval, rfm, exp, flags
	__FP_ENV \rfm
	__FP_RD2 \dst, \src, \sval, \ereg, \eval
	.dd.t32	\enc
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm
@@ TEST_FPSGN(pt, 助记符, 目的, 源, 源值, 符号源, 符号源值, 期望, 期望标志)
.macro TEST_FPSGN pt, mnem, dst, src, sval, d, dval, exp, flags
	__FP_ENV 0
	__FP_RD3 \dst, \src, \sval, \d, \dval
	\mnem	\dst, \src, \d
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm
@@ TEST_FPSGN_ENC(pt, 编码字, 目的, 源, 源值, 符号源, 符号源值, 期望, 期望标志)
.macro TEST_FPSGN_ENC pt, enc, dst, src, sval, d, dval, exp, flags
	__FP_ENV 0
	__FP_RD3 \dst, \src, \sval, \d, \dval
	.dd.t32	\enc
	__FP_CHK64 \pt, \dst, \exp, \flags
.endm
.macro TEST_FP3 pt, w, mnem, dst, a, aval, b, bval, rm, exp, flags
	__FP_ENV \rm
	__LI_RF	\a, \aval
	.ifnc	\b, \a
	__LI_RF	\b, \bval
	.endif
	\mnem	\dst, \a, \b
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm
.macro TEST_FP4 pt, w, mnem, dst, a, aval, b, bval, c, cval, rm, exp, flags
	__FP_ENV \rm
	__LI_RF	\a, \aval
	.ifnc	\b, \a
	__LI_RF	\b, \bval
	.endif
	.ifnc	\c, \a
	.ifnc	\c, \b
	__LI_RF	\c, \cval
	.endif
	.endif
	\mnem	\dst, \a, \b, \c
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm
.macro TEST_FPROOT pt, w, mnem, dst, src, sval, n, rm, exp, flags
	__FP_ENV \rm
	__LI_RF	\src, \sval
	\mnem	\dst, \src, \n
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm
@@ encoding 例：直接给**规范编码字**（钉 opc/mask/value 与字段位置），不写助记符
.macro TEST_FPENC pt, w, enc, dst, a, aval, b, bval, exp, flags
	__FP_ENV 0
	__LI_RF	\a, \aval
	.ifnc	\b, \a
	__LI_RF	\b, \bval
	.endif
	.dd.t32	\enc
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm
.macro TEST_FPENC4 pt, w, enc, dst, a, aval, b, bval, c, cval, exp, flags
	__FP_ENV 0
	__LI_RF	\a, \aval
	.ifnc	\b, \a
	__LI_RF	\b, \bval
	.endif
	.ifnc	\c, \a
	.ifnc	\c, \b
	__LI_RF	\c, \cval
	.endif
	.endif
	.dd.t32	\enc
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm
.macro TEST_FPENC_ROOT pt, w, enc, dst, src, sval, exp, flags
	__FP_ENV 0
	__LI_RF	\src, \sval
	.dd.t32	\enc
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm
@@ 原始编码故障例（汇编器拒绝的编码：目的 rf0 ⇒ ILLI；root 的 n≠2 ⇒ ILLI）
.macro TEST_FAULT_FP pt, fault, enc
	.if CASE_N == \pt
	.globl	__fault_case
__fault_case:
	__FAULT_GUARD \pt, \fault
	.dd.t32	\enc
	__EXIT	\pt
	.endif
.endm
@@ ---------------------------------------------------------------------------
@@ 格式转换 / 比较 / 分类（07-floating-point，`spec/SimRISC-07 §1/§4/§5`）
@@
@@ 一、转换（orri，单源单目的，`immu6` 语义分三套，见 §1.1/§1.2/§1.3）：
@@   TEST_FPCVT_F2I(pt, 助记符, 目的rd, 源rf, 源值, immu6, rf0[33:32], 期望, 期望标志)
@@   TEST_FPCVT_I2F(pt, 宽度, 助记符, 目的rf, 源rd, 源值, immu6, rf0[33:32], 期望, 期望标志)
@@   TEST_FPCVT_F2F(pt, 宽度, 助记符, 目的rf, 源rf, 源值, immu6, rf0[33:32], 期望, 期望标志)
@@     （`ft2fo` 的 immu6 = SBZ 写 0；`fo2ft` 写六档之一）
@@   TEST_FPCVT_ENC_RD / _RF / _F2F(pt, [宽度,] 编码字, 目的, 源, 源值, 期望, 期望标志)
@@   目的在 rd（f2i）⇒ 结果写满 64 位比较；目的在 rf ⇒ ft 只比低 32 位、fo 全比。
@@   标志与结果共用一个点号（先断言标志，再比结果）。
@@ 二、比较（orrr，目的 rd）：结果 −1/0/1 或 NaN 位型（写满 64 位）
@@   TEST_FPCMP / TEST_FPCMP_ENC(pt, [编码字,] 助记符, 目的, 源C, C值, 源D, D值, 期望, 期望标志)
@@   TEST_FPCMP_S(pt, 宽度, 助记符, 目的, 源C, C值, 源D, D值, 期望标志)
@@     —— signaling compare 的无序结果是 sNaN，`contract-fp §8` 只规定「sNaN、符号位 0、
@@        payload 不限」⇒ 用**结构断言**（指数全 1 / qNaN 位 0 / 尾数非 0 / 符号 0），不钉 payload。
@@ 三、分类（orri 块，目的 rd 窗口 ← 源 rf 窗口；结果 [9:0] 掩码，其余位清零）
@@   TEST_FPCLS1/2/3/4(pt, 助记符, 源值0, 期望0, [源值1, 期望1, ...])
@@   TEST_FPCLS_ENC1(pt, 助记符, 编码字, 目的, 源值, 期望) / TEST_FPCLS_RF0(pt, 助记符, 期望)
@@   TEST_FPCLS1_IDX（目的 rd40 / 源 rf40 同号）/ TEST_FPCLS_TOP4（{rd60:rd63} ← {rf60:rf63}）
@@ 四、块复制（orri 块，目的 rf ← 源 rf）：`TEST_FPCOPY*` 一族无使用者，已在
@@   `m15-testcases-002` 死宏清理中删除；同组块复制的唯一载体见 `02-reg-copy/rf2rf_orri_rf.S`。
@@ 五、块级合法性（`mreg_zero`/`mreg_range_overflow`/`mreg_range_overlap`/`dst_*0`/
@@   `encode_sbz`/`encode_onehot`）用 `TEST_FAULT_FP`（原始编码字）覆盖。
@@ ---------------------------------------------------------------------------

@@ 目的在 rd 的结果（浮点→整数/比较/分类）：先断言标志，再比 64 位结果
.macro __FP_CHECK_RD pt, dst, exp, flags
	rf2rd	{rd22:rd22}, {rf0:rf0}
	ext.uo	rd22, rd22, 4
	__VERIFY_RD \pt, rd22, \flags
	__CHECK_RD \pt, \dst, \exp
.endm

@@ 浮点→整数：源值经 `__LI_RF`（不经浮点指令），immu6 = 六档方向，rf0 档只对 0x20 生效
.macro TEST_FPCVT_F2I pt, mnem, dst, src, sval, cvt, rfm, exp, flags
	__FP_ENV \rfm
	__LI_RF	\src, \sval
	\mnem	\dst, \src, \cvt
	__FP_CHECK_RD \pt, \dst, \exp, \flags
.endm

@@ 整数→浮点：源值经 `__LI` 装 rd（不经浮点指令）
.macro TEST_FPCVT_I2F pt, w, mnem, dst, src, sval, cvt, rfm, exp, flags
	__FP_ENV \rfm
	__LI	\src, \sval
	\mnem	\dst, \src, \cvt
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm

@@ encoding 例（目的 rd）：给规范编码字，钉 opc/mask/value 与字段位置
.macro TEST_FPCVT_ENC_RD pt, enc, dst, src, sval, exp, flags
	__FP_ENV 0
	__LI_RF	\src, \sval
	.dd.t32	\enc
	__FP_CHECK_RD \pt, \dst, \exp, \flags
.endm

@@ encoding 例（目的 rf）
.macro TEST_FPCVT_ENC_RF pt, w, enc, dst, src, sval, exp, flags
	__FP_ENV 0
	__LI	\src, \sval
	.dd.t32	\enc
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm

@@ 浮点→浮点（ft2fo 精确 / fo2ft 六档）：源是 rf
.macro TEST_FPCVT_F2F pt, w, mnem, dst, src, sval, cvt, rfm, exp, flags
	__FP_ENV \rfm
	__LI_RF	\src, \sval
	\mnem	\dst, \src, \cvt
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm

@@ 浮点→浮点 encoding 例（源 rf）
.macro TEST_FPCVT_ENC_F2F pt, w, enc, dst, src, sval, exp, flags
	__FP_ENV 0
	__LI_RF	\src, \sval
	.dd.t32	\enc
	__FP_CHECK \pt, \w, \dst, \exp, \flags
.endm

@@ 比较（有序/quiet 无序）：结果 −1/0/1 或 canonical qNaN，全 64 位比较
.macro TEST_FPCMP pt, mnem, dst, a, aval, b, bval, exp, flags
	__FP_ENV 0
	__LI_RF	\a, \aval
	.ifnc	\b, \a
	__LI_RF	\b, \bval
	.endif
	\mnem	\dst, \a, \b
	__FP_CHECK_RD \pt, \dst, \exp, \flags
.endm

@@ 比较 encoding 例（原始编码字）
.macro TEST_FPCMP_ENC pt, enc, dst, a, aval, b, bval, exp, flags
	__FP_ENV 0
	__LI_RF	\a, \aval
	.ifnc	\b, \a
	__LI_RF	\b, \bval
	.endif
	.dd.t32	\enc
	__FP_CHECK_RD \pt, \dst, \exp, \flags
.endm

@@ signaling compare 的无序结果：sNaN 位型、符号 0、payload 不限 ⇒ 结构断言
.macro TEST_FPCMP_S pt, w, mnem, dst, a, aval, b, bval, flags
	__FP_ENV 0
	__LI_RF	\a, \aval
	.ifnc	\b, \a
	__LI_RF	\b, \bval
	.endif
	\mnem	\dst, \a, \b
	rf2rd	{rd22:rd22}, {rf0:rf0}
	ext.uo	rd22, rd22, 4
	__VERIFY_RD \pt, rd22, \flags
	shr.uo	rd21, \dst, 63		@@ 符号位必须 0
	__VERIFY_RD \pt, rd21, 0
	.ifc	\w, ft
	ext.uo	rd21, \dst, 31
	shr.uo	rd21, rd21, 22		@@ [9:0] = 指数 << 1 | qNaN 位（ft：8 位指数）
	__VERIFY_RD \pt, rd21, 0x1FE
	ext.uo	rd21, \dst, 21		@@ 尾数非 0
	.else
	shr.uo	rd21, \dst, 51		@@ [12:0] = 符号 << 12 | 指数 << 1 | qNaN 位
	ext.uo	rd21, rd21, 11		@@ 取低 12 位（符号位已单测）
	__VERIFY_RD \pt, rd21, 0xFFE
	ext.uo	rd21, \dst, 51		@@ 尾数非 0
	.endif
	__REC	\dst
	br.nz	{rd21}?, [rb0, __fps_\@]
	__EXIT	\pt
__fps_\@:
.endm

@@ 分类（源 rf40..，目的 rd8..；[63:10] 必须清零 ⇒ 期望按全 64 位比较）
.macro TEST_FPCLS1 pt, mnem, v0, e0
	__FP_ENV 0
	__LI_RF	rf40, \v0
	\mnem	{rd8:rd8}, {rf40:rf40}
	__CHECK_RD \pt, rd8, \e0
.endm

.macro TEST_FPCLS2 pt, mnem, v0, e0, v1, e1
	__FP_ENV 0
	__LI_RF	rf40, \v0
	__LI_RF	rf41, \v1
	\mnem	{rd8:rd9}, {rf40:rf41}
	__VERIFY_RD \pt, rd9, \e1
	__CHECK_RD \pt, rd8, \e0
.endm

.macro TEST_FPCLS3 pt, mnem, v0, e0, v1, e1, v2, e2
	__FP_ENV 0
	__LI_RF	rf40, \v0
	__LI_RF	rf41, \v1
	__LI_RF	rf42, \v2
	\mnem	{rd8:rd10}, {rf40:rf42}
	__VERIFY_RD \pt, rd9, \e1
	__VERIFY_RD \pt, rd10, \e2
	__CHECK_RD \pt, rd8, \e0
.endm

.macro TEST_FPCLS4 pt, mnem, v0, e0, v1, e1, v2, e2, v3, e3
	__FP_ENV 0
	__LI_RF	rf40, \v0
	__LI_RF	rf41, \v1
	__LI_RF	rf42, \v2
	__LI_RF	rf43, \v3
	\mnem	{rd8:rd11}, {rf40:rf43}
	__VERIFY_RD \pt, rd9, \e1
	__VERIFY_RD \pt, rd10, \e2
	__VERIFY_RD \pt, rd11, \e3
	__CHECK_RD \pt, rd8, \e0
.endm

@@ 分类 encoding 例（原始编码字；count = 1；目的寄存器由调用者给出）
.macro TEST_FPCLS_ENC1 pt, mnem, enc, dst, v0, e0
	__FP_ENV 0
	__LI_RF	rf40, \v0
	.dd.t32	\enc
	__CHECK_RD \pt, \dst, \e0
.endm

@@ 分类源为 rf0：读出 FCSR 位型（低 32 位是 ft 的 canonical qNaN）
.macro TEST_FPCLS_RF0 pt, mnem, e0
	__FP_ENV 0
	\mnem	{rd8:rd8}, {rf0:rf0}
	__CHECK_RD \pt, rd8, \e0
.endm

@@ 分类的同号用例（目的 rd40 / 源 rf40，同号不同组）与范围上界（rd60.. ← rf60..）
.macro TEST_FPCLS1_IDX pt, mnem, v0, e0
	__FP_ENV 0
	__LI_RF	rf40, \v0
	\mnem	{rd40:rd40}, {rf40:rf40}
	__CHECK_RD \pt, rd40, \e0
.endm

.macro TEST_FPCLS_TOP4 pt, mnem, v0, e0, v1, e1, v2, e2, v3, e3
	__FP_ENV 0
	__LI_RF	rf60, \v0
	__LI_RF	rf61, \v1
	__LI_RF	rf62, \v2
	__LI_RF	rf63, \v3
	\mnem	{rd60:rd63}, {rf60:rf63}
	__VERIFY_RD \pt, rd61, \e1
	__VERIFY_RD \pt, rd62, \e2
	__VERIFY_RD \pt, rd63, \e3
	__CHECK_RD \pt, rd60, \e0
.endm

