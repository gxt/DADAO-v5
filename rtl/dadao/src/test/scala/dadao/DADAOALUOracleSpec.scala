package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOALUOracleSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOALU independent oracle"

  it should "match every generated ALU oracle vector" in {
    assert(DADAOALUOracleTable.vectors.size == 128)

    test(new DADAOALU) { dut =>
      DADAOALUOracleTable.vectors.foreach { vector =>
        dut.io.operation.poke(vector.operation.U)
        dut.io.widthCode.poke(vector.widthCode.U)
        dut.io.signed.poke(vector.signed.B)
        dut.io.dualResult.poke(vector.dual.B)
        dut.io.operandA.poke(vector.operandA.U)
        dut.io.operandB.poke(vector.operandB.U)
        dut.io.operandC.poke(vector.operandC.U)
        dut.io.operandD.poke(vector.operandD.U)
        dut.io.auxIndex.poke(vector.aux.U)

        dut.io.resultLo.expect(vector.expectedLo.U)
        dut.io.resultHi.expect(vector.expectedHi.U)
        dut.io.primaryCommit.expect(vector.expectedCommit.B)
        dut.io.validOp.expect(true.B)
      }
    }
  }
}
