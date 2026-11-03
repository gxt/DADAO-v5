package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOALUNegativeGateSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOALU negative gate"

  it should "fail intentionally when the negative gate is enabled" in {
    if (sys.env.get("DADAO_ALU_NEGATIVE").contains("1")) {
      test(new DADAOALU) { dut =>
        dut.io.operation.poke(DADAOExecOperation.Add.U)
        dut.io.widthCode.poke(DADAOExecWidth.W64.U)
        dut.io.signed.poke(false.B)
        dut.io.dualResult.poke(false.B)
        dut.io.operandA.poke(1.U)
        dut.io.operandB.poke(1.U)
        dut.io.operandC.poke(0.U)
        dut.io.operandD.poke(0.U)
        dut.io.auxIndex.poke(0.U)
        dut.io.resultLo.expect(3.U)
      }
    } else {
      succeed
    }
  }
}
