package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOLoadExecSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOLoadExec"

  private val params = DADAOParams()
  private val baseAddress = BigInt("fc0000000100", 16)
  private val octaResponse = BigInt("8001ff7f7f80fe01", 16)

  private def setField(
      word: BigInt,
      offset: Int,
      value: BigInt,
      width: Int = 6
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (word & ~mask) | ((value << offset) & mask)
  }

  private def codedWord(id: String, dest: Int, base: Int): BigInt = {
    val index = DADAODecoderTable.ids.indexOf(id)
    val word = DADAODecoderTable.entries(index).value
    setField(setField(word, 18, dest), 12, base)
  }

  private def prepare(
      dut: DADAOLoadExec,
      id: String,
      dest: Int,
      baseReg: Int,
      responseData: BigInt
  ): Unit = {
    val index = DADAODecoderTable.ids.indexOf(id)
    dut.io.decoded.word.poke(codedWord(id, dest, baseReg).U(32.W))
    dut.io.decoded.id.poke(index.U)
    dut.io.baseValue.poke(baseAddress.U)
    dut.io.responseData.poke(responseData.U)
    dut.io.responseValid.poke(true.B)
    dut.io.responseFault.poke(false.B)
    dut.clock.step()
  }

  it should "execute all nine single-register load forms" in {
    test(new DADAOLoadExec(params)) { dut =>
      val cases = Seq(
        ("ld.sb_rrii_rd", 1, 2, DADAORegBank.Rd, 0,
          BigInt("ffffffffffffff80", 16)),
        ("ld.ub_rrii_rd", 1, 2, DADAORegBank.Rd, 0,
          BigInt("80", 16)),
        ("ld.sw_rrii_rd", 1, 2, DADAORegBank.Rd, 1,
          BigInt("ffffffffffff8001", 16)),
        ("ld.uw_rrii_rd", 1, 2, DADAORegBank.Rd, 1,
          BigInt("8001", 16)),
        ("ld.st_rrii_rd", 1, 2, DADAORegBank.Rd, 2,
          BigInt("ffffffff8001ff7f", 16)),
        ("ld.ut_rrii_rd", 1, 2, DADAORegBank.Rd, 2,
          BigInt("8001ff7f", 16)),
        ("ld.o_rrii_rd", 1, 2, DADAORegBank.Rd, 3,
          octaResponse),
        ("ld.o_rrii_rb", 1, 2, DADAORegBank.Rb, 3,
          octaResponse),
        ("ld.o_rrii_ra", 1, 2, DADAORegBank.Ra, 3,
          octaResponse)
      )

      cases.foreach { case (id, dest, base, bank, size, expected) =>
        val selectedResponse = size match {
          case DADAOMemSize.Byte =>
            expected & BigInt("ff", 16)
          case DADAOMemSize.Wyde =>
            expected & BigInt("ffff", 16)
          case DADAOMemSize.Tetra =>
            expected & BigInt("ffffffff", 16)
          case _ =>
            expected
        }
        prepare(dut, id, dest, base, selectedResponse)
        dut.io.isLoad.expect(true.B)
        dut.io.isMemory.expect(true.B)
        dut.io.baseRegAddr.expect(base.U)
        dut.io.requestAddr.expect(baseAddress.U)
        dut.io.requestSize.expect(size.U)
        dut.io.write.valid.expect(true.B)
        dut.io.write.bank.expect(bank.U)
        dut.io.write.addr.expect(dest.U)
        dut.io.write.data.expect(expected.U)
      }
    }
  }

  it should "suppress register writes for faulty responses" in {
    test(new DADAOLoadExec(params)) { dut =>
      prepare(dut, "ld.o_rrii_rd", 1, 2, 0)
      dut.io.responseFault.poke(true.B)
      dut.clock.step()
      dut.io.write.valid.expect(false.B)
    }
  }
}
