package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOALUSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOALU"

  private val allOnes64 = (BigInt(1) << 64) - 1

  private def evaluate(
      dut: DADAOALU,
      operation: Int,
      widthCode: Int,
      signed: Boolean,
      operandA: BigInt,
      operandB: BigInt,
      operandC: BigInt = 0,
      operandD: BigInt = 0,
      auxIndex: Int = 0,
      dualResult: Boolean = false
  ): Unit = {
    dut.io.operation.poke(operation.U)
    dut.io.widthCode.poke(widthCode.U)
    dut.io.signed.poke(signed.B)
    dut.io.dualResult.poke(dualResult.B)
    dut.io.operandA.poke(operandA.U)
    dut.io.operandB.poke(operandB.U)
    dut.io.operandC.poke(operandC.U)
    dut.io.operandD.poke(operandD.U)
    dut.io.auxIndex.poke(auxIndex.U)
  }

  private def expectResult(
      dut: DADAOALU,
      expected: BigInt
  ): Unit = {
    dut.io.resultLo.expect(expected.U)
    dut.io.primaryCommit.expect(true.B)
    dut.io.validOp.expect(true.B)
  }

  it should "extend narrow signed and unsigned add/sub results" in {
    test(new DADAOALU) { dut =>
      evaluate(
        dut,
        DADAOExecOperation.Add,
        DADAOExecWidth.W8,
        signed = false,
        operandA = 0xff,
        operandB = 2
      )
      expectResult(dut, 1)

      evaluate(
        dut,
        DADAOExecOperation.Add,
        DADAOExecWidth.W8,
        signed = true,
        operandA = 0xff,
        operandB = 0
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Sub,
        DADAOExecWidth.W16,
        signed = true,
        operandA = 0,
        operandB = 1
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Add,
        DADAOExecWidth.W32,
        signed = false,
        operandA = BigInt("ffffffff", 16),
        operandB = 1
      )
      expectResult(dut, 0)

      evaluate(
        dut,
        DADAOExecOperation.Add,
        DADAOExecWidth.W32,
        signed = true,
        operandA = BigInt("7fffffff", 16),
        operandB = 1
      )
      expectResult(dut, BigInt("ffffffff80000000", 16))
    }
  }

  it should "produce dual-destination carry borrow and high halves" in {
    test(new DADAOALU) { dut =>
      evaluate(
        dut,
        DADAOExecOperation.Add,
        DADAOExecWidth.W64,
        signed = false,
        operandA = allOnes64,
        operandB = 1,
        dualResult = true
      )
      dut.io.resultLo.expect(0.U)
      dut.io.resultHi.expect(1.U)
      dut.io.validOp.expect(true.B)

      evaluate(
        dut,
        DADAOExecOperation.Add,
        DADAOExecWidth.W64,
        signed = true,
        operandA = BigInt("8000000000000000", 16),
        operandB = BigInt("8000000000000000", 16),
        dualResult = true
      )
      dut.io.resultLo.expect(0.U)
      dut.io.resultHi.expect(allOnes64.U)

      evaluate(
        dut,
        DADAOExecOperation.Sub,
        DADAOExecWidth.W64,
        signed = false,
        operandA = 0,
        operandB = 1,
        dualResult = true
      )
      dut.io.resultLo.expect(allOnes64.U)
      dut.io.resultHi.expect(1.U)
      dut.io.validOp.expect(true.B)
    }
  }

  it should "compare with 64-bit all-ones result for less-than" in {
    test(new DADAOALU) { dut =>
      evaluate(
        dut,
        DADAOExecOperation.Cmp,
        DADAOExecWidth.W8,
        signed = false,
        operandA = 10,
        operandB = 20
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Cmp,
        DADAOExecWidth.W16,
        signed = false,
        operandA = 10,
        operandB = 20
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Cmp,
        DADAOExecWidth.W32,
        signed = false,
        operandA = 10,
        operandB = 20
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Cmp,
        DADAOExecWidth.W64,
        signed = false,
        operandA = 10,
        operandB = 20
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Cmp,
        DADAOExecWidth.W8,
        signed = true,
        operandA = 20,
        operandB = 10
      )
      expectResult(dut, 1)

      evaluate(
        dut,
        DADAOExecOperation.Cmp,
        DADAOExecWidth.W8,
        signed = true,
        operandA = 0xff,
        operandB = 1
      )
      expectResult(dut, allOnes64)
    }
  }

  it should "compute signed and unsigned multiply high and low halves" in {
    test(new DADAOALU) { dut =>
      val signedMin = BigInt("8000000000000000", 16)
      evaluate(
        dut,
        DADAOExecOperation.Mul,
        DADAOExecWidth.W64,
        signed = false,
        operandA = signedMin,
        operandB = signedMin,
        dualResult = true
      )
      dut.io.resultLo.expect(0.U)
      dut.io.resultHi.expect(BigInt("4000000000000000", 16).U)
      dut.io.validOp.expect(true.B)

      evaluate(
        dut,
        DADAOExecOperation.Mul,
        DADAOExecWidth.W64,
        signed = true,
        operandA = BigInt("fffffffffffffffe", 16),
        operandB = 3,
        dualResult = true
      )
      dut.io.resultLo.expect(BigInt("fffffffffffffffa", 16).U)
      dut.io.resultHi.expect(allOnes64.U)

      evaluate(
        dut,
        DADAOExecOperation.Mul,
        DADAOExecWidth.W8,
        signed = true,
        operandA = 0xff,
        operandB = 2
      )
      expectResult(dut, BigInt("fffffffffffffffe", 16))
    }
  }

  it should "implement unsigned division and remainder constants" in {
    test(new DADAOALU) { dut =>
      evaluate(
        dut,
        DADAOExecOperation.Div,
        DADAOExecWidth.W64,
        signed = false,
        operandA = 100,
        operandB = 7
      )
      expectResult(dut, 14)

      evaluate(
        dut,
        DADAOExecOperation.Rem,
        DADAOExecWidth.W64,
        signed = false,
        operandA = 100,
        operandB = 7
      )
      expectResult(dut, 2)

      evaluate(
        dut,
        DADAOExecOperation.Div,
        DADAOExecWidth.W32,
        signed = false,
        operandA = 100,
        operandB = 0
      )
      expectResult(dut, BigInt("ffffffff", 16))

      evaluate(
        dut,
        DADAOExecOperation.Rem,
        DADAOExecWidth.W32,
        signed = false,
        operandA = 100,
        operandB = 0
      )
      expectResult(dut, 100)
    }
  }

  it should "implement signed division truncation and overflow constants" in {
    test(new DADAOALU) { dut =>
      val negativeSeven = allOnes64 - 6
      evaluate(
        dut,
        DADAOExecOperation.Div,
        DADAOExecWidth.W64,
        signed = true,
        operandA = negativeSeven,
        operandB = 3
      )
      expectResult(dut, allOnes64 - 1)

      evaluate(
        dut,
        DADAOExecOperation.Rem,
        DADAOExecWidth.W64,
        signed = true,
        operandA = negativeSeven,
        operandB = 3
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Div,
        DADAOExecWidth.W8,
        signed = true,
        operandA = 0x80,
        operandB = 0xff
      )
      expectResult(dut, BigInt("ffffffffffffff80", 16))

      evaluate(
        dut,
        DADAOExecOperation.Rem,
        DADAOExecWidth.W8,
        signed = true,
        operandA = 0x80,
        operandB = 0xff
      )
      expectResult(dut, 0)

      evaluate(
        dut,
        DADAOExecOperation.Div,
        DADAOExecWidth.W64,
        signed = true,
        operandA = BigInt("8000000000000000", 16),
        operandB = allOnes64
      )
      expectResult(dut, BigInt("8000000000000000", 16))

      evaluate(
        dut,
        DADAOExecOperation.Rem,
        DADAOExecWidth.W64,
        signed = true,
        operandA = BigInt("8000000000000000", 16),
        operandB = allOnes64
      )
      expectResult(dut, 0)
    }
  }

  it should "implement 64-bit logic operations" in {
    test(new DADAOALU) { dut =>
      val a = BigInt("aaaaaaaaaaaaaaaa", 16)
      val b = BigInt("5555555555555555", 16)

      evaluate(
        dut,
        DADAOExecOperation.And,
        DADAOExecWidth.W64,
        signed = false,
        operandA = a,
        operandB = b
      )
      expectResult(dut, 0)

      evaluate(
        dut,
        DADAOExecOperation.Or,
        DADAOExecWidth.W64,
        signed = false,
        operandA = a,
        operandB = b
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Xor,
        DADAOExecWidth.W64,
        signed = false,
        operandA = a,
        operandB = b
      )
      expectResult(dut, allOnes64)

      evaluate(
        dut,
        DADAOExecOperation.Xnor,
        DADAOExecWidth.W64,
        signed = false,
        operandA = a,
        operandB = b
      )
      expectResult(dut, 0)
    }
  }

  it should "shift and extend with value semantics" in {
    test(new DADAOALU) { dut =>
      evaluate(
        dut,
        DADAOExecOperation.Shl,
        DADAOExecWidth.W8,
        signed = false,
        operandA = 0x80,
        operandB = 0,
        auxIndex = 1
      )
      expectResult(dut, 0)

      evaluate(
        dut,
        DADAOExecOperation.Shr,
        DADAOExecWidth.W8,
        signed = true,
        operandA = 0x80,
        operandB = 0,
        auxIndex = 1
      )
      expectResult(dut, BigInt("ffffffffffffffc0", 16))

      evaluate(
        dut,
        DADAOExecOperation.Ext,
        DADAOExecWidth.W64,
        signed = false,
        operandA = BigInt("1234", 16),
        operandB = 0,
        auxIndex = 7
      )
      expectResult(dut, BigInt("34", 16))

      evaluate(
        dut,
        DADAOExecOperation.Ext,
        DADAOExecWidth.W64,
        signed = true,
        operandA = 0x80,
        operandB = 0,
        auxIndex = 7
      )
      expectResult(dut, BigInt("ffffffffffffff80", 16))
    }
  }

  it should "implement conditional assignment commit semantics" in {
    test(new DADAOALU) { dut =>
      evaluate(
        dut,
        DADAOExecOperation.CsZ,
        DADAOExecWidth.W64,
        signed = true,
        operandA = 0,
        operandB = 0,
        operandC = 11,
        operandD = 22
      )
      expectResult(dut, 11)

      evaluate(
        dut,
        DADAOExecOperation.CsEq,
        DADAOExecWidth.W64,
        signed = true,
        operandA = 5,
        operandB = 5,
        operandC = 0,
        operandD = 33
      )
      dut.io.resultLo.expect(33.U)
      dut.io.primaryCommit.expect(true.B)

      evaluate(
        dut,
        DADAOExecOperation.CsNe,
        DADAOExecWidth.W64,
        signed = true,
        operandA = 5,
        operandB = 5,
        operandC = 0,
        operandD = 33
      )
      dut.io.resultLo.expect(33.U)
      dut.io.primaryCommit.expect(false.B)
    }
  }
}
