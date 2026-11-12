package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOMemoryNegativeGateSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAO memory negative gate"

  it should "fail intentionally when the negative gate is enabled" in {
    if (sys.env.get("DADAO_MEMORY_NEGATIVE").contains("1")) {
      val vector = DADAOMemoryOracleTable.vectors
        .find(_.name == "positive-st.t_rrii_rd")
        .get
      val baseValue = vector.initialRegisters
        .find(register =>
          register.bank == DADAORegBank.Rb && register.index == 2
        )
        .get
        .value
      val sourceValue = vector.initialRegisters
        .find(register =>
          register.bank == DADAORegBank.Rd && register.index == 8
        )
        .get
        .value
      val memory = vector.initialMemory.head
      val corruptedExpected = vector.expectedMemory.head.data ^ 1

      test(new DADAOMemoryOracleProbe(DADAOParams())) { dut =>
        dut.io.word.poke(vector.word.U(32.W))
        dut.io.baseValue.poke(baseValue.U)
        dut.io.offsetValue.poke(0.U)
        dut.io.address.poke(baseValue.U)
        dut.io.sourceValue.poke(sourceValue.U)
        dut.io.memoryBeat.poke(memory.data.U)
        dut.io.mergedBeat.expect(corruptedExpected.U)
      }
    } else {
      succeed
    }
  }
}
