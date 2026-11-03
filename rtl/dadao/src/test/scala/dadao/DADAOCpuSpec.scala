package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOCpuSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAOCpuTop"

  private val params = DADAOParams()

  private def setField(
      word: BigInt,
      offset: Int,
      value: BigInt,
      width: Int = 6
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (word & ~mask) | ((value << offset) & mask)
  }

  private def encoded(id: String, fields: Seq[(Int, BigInt, Int)]): BigInt =
    fields.foldLeft(
      DADAODecoderTable.entries(
        DADAODecoderTable.ids.indexOf(id)
      ).value
    ) { case (word, (offset, value, width)) =>
      setField(word, offset, value, width)
    }

  private def holdReset(
      dut: DADAOCpuTop,
      pc: BigInt
  ): Unit = {
    dut.io.pcInitValid.get.poke(true.B)
    dut.io.pcInit.get.poke(pc.U)
    dut.io.testRegWrite.get.valid.poke(false.B)
    dut.io.testRegWrite.get.bank.poke(DADAORegBank.Rd.U)
    dut.io.testRegWrite.get.addr.poke(0.U)
    dut.io.testRegWrite.get.data.poke(0.U)
    dut.io.debugRegBank.get.poke(DADAORegBank.Rd.U)
    dut.io.debugRegAddr.get.poke(0.U)
    dut.reset.poke(true.B)
    dut.clock.step(2)
    dut.reset.poke(false.B)
    dut.clock.step()
  }

  private def writeReg(
      dut: DADAOCpuTop,
      bank: Int,
      address: Int,
      value: BigInt
  ): Unit = {
    dut.io.testRegWrite.get.valid.poke(true.B)
    dut.io.testRegWrite.get.bank.poke(bank.U)
    dut.io.testRegWrite.get.addr.poke(address.U)
    dut.io.testRegWrite.get.data.poke(value.U)
    dut.clock.step()
    dut.io.testRegWrite.get.valid.poke(false.B)
  }

  private def waitForPc(
      dut: DADAOCpuTop,
      expected: BigInt,
      maxCycles: Int = 256
  ): Unit = {
    var cycles = 0
    while (
      dut.io.debugPc.get.peek().litValue != expected &&
      !dut.io.debugFault.get.peek().litToBoolean &&
      cycles < maxCycles
    ) {
      dut.clock.step()
      cycles += 1
    }
    dut.io.debugPc.get.expect(expected.U)
    dut.io.debugFault.get.expect(false.B)
  }

  private def expectReg(
      dut: DADAOCpuTop,
      bank: Int,
      address: Int,
      expected: BigInt
  ): Unit = {
    dut.io.debugRegBank.get.poke(bank.U)
    dut.io.debugRegAddr.get.poke(address.U)
    dut.clock.step()
    dut.io.debugRegData.get.expect(expected.U)
  }

  it should "boot from ROM and use TileLink RAM for store and load" in {
    val setZeroWyde = encoded(
      "set.zw_rwii_rd",
      Seq((18, 1, 6), (16, 0, 2), (0, BigInt("1234", 16), 16))
    )
    val store = encoded(
      "st.w_rrii_rd",
      Seq((18, 1, 6), (12, 2, 6), (0, 0, 12))
    )
    val load = encoded(
      "ld.uw_rrii_rd",
      Seq((18, 3, 6), (12, 2, 6), (0, 0, 12))
    )
    val swym =
      DADAODecoderTable.entries(DADAODecoderTable.swymId).value
    val beat0 = (setZeroWyde << 32) | store
    val beat1 = (load << 32) | swym
    val romContents = Seq(
      DADAOTLEndian.reverseBeatValue(beat0),
      DADAOTLEndian.reverseBeatValue(beat1)
    )
    val dataAddress = params.ramBase + 0x100

    test(
      new DADAOCpuTop(
        params,
        testMode = true,
        romContents = romContents
      )
    ) { dut =>
      holdReset(dut, params.bootRomBase)
      writeReg(dut, DADAORegBank.Rb, 2, dataAddress)
      dut.io.pcInitValid.get.poke(false.B)
      dut.clock.step()

      waitForPc(dut, params.bootRomBase + 4)
      dut.io.debugWord.get.expect(setZeroWyde.U)
      expectReg(dut, DADAORegBank.Rd, 1, BigInt("1234", 16))

      waitForPc(dut, params.bootRomBase + 8)
      expectReg(dut, DADAORegBank.Rb, 2, dataAddress)

      waitForPc(dut, params.bootRomBase + 12)
      expectReg(dut, DADAORegBank.Rd, 3, BigInt("1234", 16))

      waitForPc(dut, params.bootRomBase + 16)
    }
  }
}
