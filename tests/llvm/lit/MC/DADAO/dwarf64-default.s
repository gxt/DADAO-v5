@@ DWARF64 default for DADAO on the paths that do not go through the C/C++
@@ compilation driver (LLVM-130t leftover, closed by LLVM-134t; ADR-0036 D1).
@@
@@ DADAO is a native 64-bit target whose ABI has no 32-bit address relocation
@@ channel, so DWARF32's 4-byte offset fields cannot carry the ABS48 relocations
@@ of the .debug_* sections: `clang -c x.s -g` used to fail late in cc1as with
@@ "relocatable operand in a 1/2/4-byte data field".  Both the integrated
@@ assembler (`clang -c x.s`, cc1as) and `llvm-mc -g` must therefore default to
@@ the 64-bit DWARF format, and an explicit `-gdwarf32` must be rejected by the
@@ driver with a diagnostic of its own (never a silent downgrade).
@@
@@ The CU header is read back from the object: `format = DWARF64` and a 64-bit
@@ address size.  llvm-dwarfdump may exit non-zero on DADAO .o files because
@@ libObject cannot apply the ABS48 relocations yet (LLVM-130t finding), so the
@@ dump is captured first (`|| true`) and the assertion is the FileCheck step
@@ on the captured text -- a missing/crashed dump leaves no CU line and fails.

@@ RUN: %clang --target=dadao-unknown-elf -c %s -g -o %t.o
@@ RUN: %llvm_dwarfdump --debug-info %t.o > %t.cu 2>&1 || true
@@ RUN: %FileCheck %s --check-prefix=CU < %t.cu
@@ RUN: %llvm_mc --triple=dadao-unknown-elf -g -filetype=obj %s -o %t-mc.o
@@ RUN: %llvm_dwarfdump --debug-info %t-mc.o > %t-mc.cu 2>&1 || true
@@ RUN: %FileCheck %s --check-prefix=CU < %t-mc.cu
@@ RUN: %clang --target=dadao-unknown-elf -c %s -g -### 2>&1 | %FileCheck %s --check-prefix=CC1AS
@@ RUN: %not %clang --target=dadao-unknown-elf -c %s -g -gdwarf32 -o %t32.o 2>&1 | %FileCheck %s --check-prefix=ERR32

@@ The cc1as command line carries the DWARF64 format even though the user only
@@ asked for `-g`; the driver, not the assembler, supplies the target default.
@@ CC1AS:      "-cc1as"
@@ CC1AS-DAG:  "-gdwarf64"

@@ .. and the emitted compile unit is really DWARF64 with 8-byte addresses.
@@ CU: format = DWARF64
@@ CU: addr_size = 0x08

@@ An explicit -gdwarf32 is a hard driver error (no 32-bit relocation channel).
@@ ERR32: unsupported option '-gdwarf32' for target

	.text
	.globl	main
main:
	set.zw	rd1, wp0, 0x1
	ret	rd0, 0
