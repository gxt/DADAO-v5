package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOControlOracleSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOControlExec oracle"

  private val params = DADAOParams()

  private def pokeDecoded(
      dut: DADAOControlExec,
      vector: DADAOControlOracleVector
  ): Unit = {
    dut.io.decoded.word.poke(vector.word.U(32.W))
    dut.io.decoded.id.poke(vector.instructionId.U)
    dut.io.decoded.format.poke(0.U)
    dut.io.decoded.slot0.poke(
      ((vector.word >> 18) & 0x3f).U
    )
    dut.io.decoded.slot1.poke(
      ((vector.word >> 12) & 0x3f).U
    )
    dut.io.decoded.slot2.poke(
      ((vector.word >> 6) & 0x3f).U
    )
    dut.io.decoded.slot3.poke((vector.word & 0x3f).U)
    dut.io.decoded.imm12.poke((vector.word & 0xfff).U)
    dut.io.decoded.imm18.poke((vector.word & 0x3ffff).U)
    dut.io.decoded.imm24.poke((vector.word & 0xffffff).U)
    dut.io.currentRb0.poke(vector.currentRb0.U)
    dut.io.read0Value.poke(vector.read0Value.U)
    dut.io.read1Value.poke(vector.read1Value.U)
    dut.io.poppedReturnAddress.poke(
      vector.poppedReturnAddress.U(48.W)
    )
  }

  it should "cover every control instruction and required boundaries" in {
    val vectors = DADAOControlOracleTable.vectors
    assert(vectors.map(_.instructionId).distinct.size == 15)
    assert(vectors.count(_.expectedIsBranch) >= 20)
    assert(vectors.exists(_.category == "immediate-min"))
    assert(vectors.exists(_.category == "immediate-max"))
    assert(
      vectors.exists(vector =>
        vector.instructionId ==
          DADAODecoderTable.ids.indexOf("br.z_riii_rb")
      )
    )
    assert(vectors.exists(_.expectedIsCall))
    assert(vectors.exists(_.expectedIsRet))
  }

  DADAOControlOracleTable.vectors.foreach { vector =>
    it should s"match ${vector.name}" in {
      test(new DADAOControlExec(params)) { dut =>
        pokeDecoded(dut, vector)
        dut.io.isControl.expect(vector.expectedIsControl.B)
        dut.io.isBranch.expect(vector.expectedIsBranch.B)
        dut.io.isJump.expect(vector.expectedIsJump.B)
        dut.io.isCall.expect(vector.expectedIsCall.B)
        dut.io.isRet.expect(vector.expectedIsRet.B)
        dut.io.taken.expect(vector.expectedTaken.B)
        dut.io.target.expect(vector.expectedTarget.U)
        dut.io.nextRb0.expect(vector.expectedNextRb0.U)
        dut.io.callReturnAddress.expect(
          vector.expectedCallReturnAddress.U
        )
        dut.io.retRdWrite.expect(vector.expectedRetRdWrite.B)
        if (vector.expectedIsRet) {
          dut.io.retRdAddr.expect(vector.expectedRetRdAddr.U)
          dut.io.retRdValue.expect(vector.expectedRetRdValue.U)
        }
        dut.io.read0Bank.expect(vector.expectedRead0Bank.U)
        dut.io.read0Addr.expect(vector.expectedRead0Addr.U)
        dut.io.read1Bank.expect(vector.expectedRead1Bank.U)
        dut.io.read1Addr.expect(vector.expectedRead1Addr.U)
      }
    }
  }
}
