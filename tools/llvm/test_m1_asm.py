#!/usr/bin/env python3
"""
Test all 178 M1 instructions can be assembled by llvm-mc.
Exit code 0 if all pass, 1 if any fail.
"""
import subprocess
import sys
import os

def test_asm_line(asm_line, llvm_mc):
    """Test if an assembly line can be assembled."""
    try:
        result = subprocess.run(
            [llvm_mc, '--triple=dadao-unknown-elf', '-filetype=obj', '-o', '/dev/null', '-'],
            input=asm_line.encode(),
            capture_output=True,
            timeout=10
        )
        return result.returncode == 0
    except Exception as e:
        return False

def main():
    llvm_mc = '/mnt/tao/DADAO-v5/.work/build/llvm/bin/llvm-mc'
    
    if not os.path.exists(llvm_mc):
        print(f"Error: llvm-mc not found at {llvm_mc}", file=sys.stderr)
        sys.exit(1)
    
    # Generate assembly lines
    import gen_m1_asm
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        gen_m1_asm.main()
    asm_lines = f.getvalue().strip().split('\n')
    
    # Filter out comment lines
    asm_lines = [l for l in asm_lines if not l.startswith('#')]
    
    passed = 0
    failed = 0
    failures = []
    
    for i, line in enumerate(asm_lines, 1):
        if test_asm_line(line, llvm_mc):
            passed += 1
        else:
            failed += 1
            failures.append((i, line))
            print(f"FAIL: {line}", file=sys.stderr)
    
    print(f"Results: {passed} passed, {failed} failed out of {len(asm_lines)} instructions", file=sys.stderr)
    
    if failures:
        print("\nFailed instructions:", file=sys.stderr)
        for idx, line in failures:
            print(f"  {idx}: {line}", file=sys.stderr)
        sys.exit(1)
    else:
        print("All M1 instructions assembled successfully!", file=sys.stderr)
        sys.exit(0)

if __name__ == '__main__':
    main()
