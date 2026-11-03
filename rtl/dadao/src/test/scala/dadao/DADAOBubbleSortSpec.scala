package dadao

import chisel3._
import chiseltest._
import chiseltest.simulator.VerilatorBackendAnnotation
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOBubbleSortSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAO bubble-sort program"

  private val params = DADAOParams()

  private def loadEntry(
      dut: DADAOTestMemoryHarness,
      index: Int,
      address: BigInt,
      data: BigInt,
      writable: Boolean
  ): Unit = {
    dut.io.load.valid.poke(true.B)
    dut.io.load.index.poke(index.U)
    dut.io.load.address.poke(address.U)
    dut.io.load.data.poke(data.U)
    dut.io.load.writable.poke(writable.B)
    dut.io.load.fault.poke(false.B)
    dut.io.load.faultCode.poke(0.U)
    dut.clock.step()
    dut.io.load.valid.poke(false.B)
  }

  private def instructionBeats: Seq[BigInt] = {
    DADAOBubbleSortProgram.words.grouped(2).map {
      case Seq(low, high) => (low << 32) | high
      case Seq(low) => low << 32
      case other =>
        throw new IllegalArgumentException(
          s"incomplete instruction beat: $other"
        )
    }.toSeq
  }

  private def holdResetAt(dut: DADAOTestMemoryHarness): Unit = {
    dut.io.testRegWrite.valid.poke(false.B)
    dut.io.testRegWrite.bank.poke(DADAORegBank.Rd.U)
    dut.io.testRegWrite.addr.poke(0.U)
    dut.io.testRegWrite.data.poke(0.U)
    dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
    dut.io.debugRegAddr.poke(0.U)
    dut.io.testCfxWrite.valid.poke(false.B)
    dut.io.testCfxWrite.cfxha.poke(0.U)
    dut.io.testCfxWrite.cg.poke(0.U)
    dut.io.testCfxWrite.rc.poke(0.U)
    dut.io.testCfxWrite.data.poke(0.U)
    dut.io.testCfxStatusSet.valid.poke(false.B)
    dut.io.testCfxStatusSet.runMode.poke(DADAORunMode.Hypv.U)
    dut.io.testCfxStatusSet.cfxCode.poke(DADAOCfxCode.Power.U)
    dut.io.testCfxStatusSet.cfxMask.poke(
      BigInt("ffffffffffffffff", 16).U
    )
    dut.io.debugCfxRead.cfxha.poke(0.U)
    dut.io.debugCfxRead.cg.poke(0.U)
    dut.io.debugCfxRead.rc.poke(0.U)
    dut.io.pcInitValid.poke(true.B)
    dut.io.pcInit.poke(params.bootRomBase.U)
    dut.reset.poke(true.B)
    dut.clock.step(2)
    dut.reset.poke(false.B)
    dut.clock.step()
  }

  private def writeReg(
      dut: DADAOTestMemoryHarness,
      bank: Int,
      address: Int,
      value: BigInt
  ): Unit = {
    dut.io.testRegWrite.valid.poke(true.B)
    dut.io.testRegWrite.bank.poke(bank.U)
    dut.io.testRegWrite.addr.poke(address.U)
    dut.io.testRegWrite.data.poke(value.U)
    dut.clock.step()
    dut.io.testRegWrite.valid.poke(false.B)
  }

  private def readReg(
      dut: DADAOTestMemoryHarness,
      address: Int
  ): BigInt = {
    dut.io.debugRegBank.poke(DADAORegBank.Rd.U)
    dut.io.debugRegAddr.poke(address.U)
    dut.clock.step()
    dut.io.debugRegData.peek().litValue
  }

  it should "sort five values through machine instructions and RAM" in {
    test(new DADAOTestMemoryHarness(params, maxEntries = 40))
      .withAnnotations(Seq(VerilatorBackendAnnotation)) { dut =>
      val dataAddress = params.ramBase + 0x100
      val endPc =
        params.bootRomBase + DADAOBubbleSortProgram.words.size * 4

      holdResetAt(dut)
      instructionBeats.zipWithIndex.foreach {
        case (beat, index) =>
          loadEntry(
            dut,
            index,
            params.bootRomBase + index * 8,
            beat,
            writable = false
          )
      }
      loadEntry(
        dut,
        instructionBeats.size,
        dataAddress,
        0,
        writable = true
      )
      writeReg(dut, DADAORegBank.Rb, 2, dataAddress)
      dut.io.pcInitValid.poke(false.B)
      dut.clock.step()

      var cycles = 0
      while (
        dut.io.debugPc.peek().litValue != endPc &&
        !dut.io.debugFault.peek().litToBoolean &&
        cycles < 1024
      ) {
        dut.clock.step()
        cycles += 1
      }

      dut.io.debugPc.expect(endPc.U)
      dut.io.debugFault.expect(false.B)

      dut.io.pcInitValid.poke(true.B)
      dut.io.pcInit.poke(params.bootRomBase.U)
      dut.clock.step()

      DADAOBubbleSortProgram.expectedValues.indices.foreach { index =>
        readReg(dut, index + 1) should be(
          DADAOBubbleSortProgram.expectedValues(index)
        )
      }
      DADAOBubbleSortProgram.expectedValues.indices.foreach { index =>
        readReg(dut, index + 8) should be(
          DADAOBubbleSortProgram.expectedValues(index)
        )
      }

      dut.io.debugMemIndex.poke(instructionBeats.size.U)
      dut.clock.step()
      dut.io.debugMemData.expect(BigInt("0001000200030004", 16).U)

      dut.io.debugMemIndex.poke((instructionBeats.size + 1).U)
      dut.clock.step()
      dut.io.debugMemData.expect(BigInt("0005000000000000", 16).U)
    }
  }
}
