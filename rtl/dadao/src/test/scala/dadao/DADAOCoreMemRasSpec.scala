package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOCoreMemRasSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAOCore MemRAS"

  private val params = DADAOParams()
  private val testPc = BigInt("fc0000000000", 16)

  private def setField(
      value: BigInt,
      offset: Int,
      field: BigInt,
      width: Int
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (value & ~mask) | ((field << offset) & mask)
  }

  private def initCore(dut: DADAOCore, pc: BigInt): Unit = {
    dut.io.testRegWrite.get.valid.poke(false.B)
    dut.io.testRegWrite.get.bank.poke(DADAORegBank.Rd.U)
    dut.io.testRegWrite.get.addr.poke(0.U)
    dut.io.testRegWrite.get.data.poke(0.U)
    dut.io.debugRegBank.get.poke(DADAORegBank.Rd.U)
    dut.io.debugRegAddr.get.poke(0.U)
    dut.io.mem.req.ready.poke(false.B)
    dut.io.mem.resp.valid.poke(false.B)
    dut.io.mem.resp.bits.rdata.poke(0.U)
    dut.io.mem.resp.bits.fault.poke(false.B)
    dut.io.mem.resp.bits.faultCode.poke(0.U)
    dut.io.pcInitValid.get.poke(true.B)
    dut.io.pcInit.get.poke(pc.U)
    dut.reset.poke(true.B)
    dut.clock.step(2)
    dut.reset.poke(false.B)
    dut.clock.step()
    dut.io.pcInitValid.get.poke(false.B)
  }

  private def writeReg(
      dut: DADAOCore,
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

  private def readReg(
      dut: DADAOCore,
      bank: Int,
      address: Int
  ): BigInt = {
    dut.io.debugRegBank.get.poke(bank.U)
    dut.io.debugRegAddr.get.poke(address.U)
    dut.io.debugRegData.get.peek().litValue
  }

  private def completeFetch(
      dut: DADAOCore,
      word: BigInt
  ): Unit = {
    dut.io.debugMemOwner.get.expect(DADAOMemOwner.Idle.U)
    dut.io.mem.req.valid.expect(true.B)
    dut.io.mem.req.ready.poke(true.B)
    dut.clock.step()
    dut.io.mem.req.ready.poke(false.B)
    dut.io.debugMemOwner.get.expect(DADAOMemOwner.Fetch.U)
    dut.io.mem.resp.valid.poke(true.B)
    dut.io.mem.resp.bits.rdata.poke(word.U)
    dut.io.mem.resp.bits.fault.poke(false.B)
    dut.io.mem.resp.bits.faultCode.poke(0.U)
    dut.io.mem.resp.ready.expect(true.B)
    dut.clock.step()
    dut.io.mem.resp.valid.poke(false.B)
    dut.clock.step()
  }

  private def acceptRasRequest(
      dut: DADAOCore,
      address: BigInt,
      write: Boolean,
      wdata: BigInt = 0
  ): Unit = {
    dut.io.mem.req.valid.expect(true.B)
    dut.io.mem.req.bits.addr.expect(address.U)
    dut.io.mem.req.bits.write.expect(write.B)
    dut.io.mem.req.bits.size.expect(DADAOMemSize.Octa.U)
    dut.io.mem.req.bits.kind.expect(DADAOMemKind.Data.U)
    if (write) {
      dut.io.mem.req.bits.wdata.expect(wdata.U)
      dut.io.mem.req.bits.wstrb.expect(0xff.U(8.W))
    } else {
      dut.io.mem.req.bits.wstrb.expect(0.U)
    }
    dut.io.mem.req.ready.poke(true.B)
    dut.clock.step()
    dut.io.mem.req.ready.poke(false.B)
  }

  private def completeRasResponse(
      dut: DADAOCore,
      data: BigInt,
      fault: Boolean = false,
      faultCode: Int = DADAOFaultCode.None
  ): Unit = {
    dut.io.mem.resp.valid.poke(true.B)
    dut.io.mem.resp.bits.rdata.poke(data.U)
    dut.io.mem.resp.bits.fault.poke(fault.B)
    dut.io.mem.resp.bits.faultCode.poke(faultCode.U)
    dut.clock.step()
    dut.io.mem.resp.valid.poke(false.B)
    dut.io.mem.resp.bits.fault.poke(false.B)
  }

  it should "spill on a full RegRAS before committing call" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      initCore(dut, testPc)
      val mrPtr = BigInt("fc0000004000", 16)
      val oldest = (BigInt(7) << 48) |
        BigInt("fc0000000100", 16)
      writeReg(dut, DADAORegBank.Ra, 0, (BigInt(63) << 48) | mrPtr)
      writeReg(dut, DADAORegBank.Ra, 1, oldest)
      readReg(dut, DADAORegBank.Ra, 0) should be(
        (BigInt(63) << 48) | mrPtr
      )
      readReg(dut, DADAORegBank.Ra, 1) should be(oldest)

      val call = DADAODecoderTable.entries(
        DADAODecoderTable.ids.indexOf("call_iiii_ra")
      )
      completeFetch(
        dut,
        setField(call.value, 0, 2, 24)
      )

      dut.io.debugPc.get.expect(testPc.U)
      dut.io.debugRasState.get.expect(
        DADAORasState.WaitAccept.U
      )
      dut.io.debugRasDone.get.expect(false.B)
      dut.io.debugRasFault.get.expect(false.B)
      dut.io.debugRasMemReqValid.get.expect(true.B)
      dut.io.debugMemOwner.get.expect(DADAOMemOwner.Ras.U)
      dut.io.debugFaultReason.get.expect(
        DADAODebugFaultReason.None.U
      )
      dut.io.debugFaultCode.get.expect(DADAOFaultCode.None.U)
      dut.io.debugFault.get.expect(false.B)
      acceptRasRequest(dut, mrPtr - 8, write = true, oldest)
      completeRasResponse(dut, 0)

      dut.io.debugPc.get.expect((testPc + 8).U)
      dut.io.debugFault.get.expect(false.B)
      readReg(dut, DADAORegBank.Ra, 0) should be(
        (BigInt(63) << 48) | (mrPtr - 8)
      )
      readReg(dut, DADAORegBank.Ra, 63) should be(
        (BigInt(1) << 48) | (testPc + 4)
      )
    }
  }

  it should "restore from MemRAS before committing ret" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      initCore(dut, testPc)
      val mrPtr = BigInt("fc0000006000", 16)
      val returnAddress = BigInt("fc0000001234", 16)
      writeReg(dut, DADAORegBank.Ra, 0, mrPtr)

      val ret = DADAODecoderTable.entries(
        DADAODecoderTable.ids.indexOf("ret_riii_ra")
      )
      val retWord =
        setField(setField(ret.value, 18, 0, 6), 0, 0, 18)
      completeFetch(dut, retWord)

      dut.io.debugPc.get.expect(testPc.U)
      dut.io.debugFault.get.expect(false.B)
      dut.io.debugRasState.get.expect(
        DADAORasState.WaitAccept.U
      )
      dut.io.debugMemOwner.get.expect(DADAOMemOwner.Ras.U)
      dut.io.debugRasMemReqValid.get.expect(true.B)
      acceptRasRequest(dut, mrPtr, write = false)
      completeRasResponse(
        dut,
        (BigInt(1) << 48) | returnAddress
      )

      dut.io.debugPc.get.expect(returnAddress.U)
      dut.io.debugFault.get.expect(false.B)
      readReg(dut, DADAORegBank.Ra, 0) should be(mrPtr + 8)
    }
  }

  it should "preserve ret IP and RAS state on MemRAS read fault" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      initCore(dut, testPc)
      val mrPtr = BigInt("fc0000007000", 16)
      writeReg(dut, DADAORegBank.Ra, 0, mrPtr)

      val ret = DADAODecoderTable.entries(
        DADAODecoderTable.ids.indexOf("ret_riii_ra")
      )
      val retWord =
        setField(setField(ret.value, 18, 0, 6), 0, 0, 18)
      completeFetch(dut, retWord)
      dut.io.debugFault.get.expect(false.B)
      dut.io.debugRasState.get.expect(
        DADAORasState.WaitAccept.U
      )
      dut.io.debugMemOwner.get.expect(DADAOMemOwner.Ras.U)
      dut.io.debugRasMemReqValid.get.expect(true.B)
      acceptRasRequest(dut, mrPtr, write = false)
      completeRasResponse(
        dut,
        0,
        fault = true,
        faultCode = DADAOFaultCode.Unmapped
      )

      dut.io.debugPc.get.expect(testPc.U)
      dut.io.debugFault.get.expect(true.B)
      dut.io.debugFaultCode.get.expect(DADAOFaultCode.Unmapped.U)
      readReg(dut, DADAORegBank.Ra, 0) should be(mrPtr)
    }
  }
}
