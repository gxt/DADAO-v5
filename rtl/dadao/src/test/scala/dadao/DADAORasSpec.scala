package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAORasSpec extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "DADAORas"

  private val params = DADAOParams()

  private def clearWrites(dut: DADAORas): Unit = {
    dut.io.req.push.poke(false.B)
    dut.io.req.pushAddress.poke(0.U)
    dut.io.req.pop.poke(false.B)
    dut.io.memReqAccepted.poke(false.B)
    dut.io.memResp.valid.poke(false.B)
    dut.io.memResp.data.poke(0.U)
    dut.io.memResp.fault.poke(false.B)
    dut.io.memResp.faultCode.poke(0.U)
    for (index <- 0 until 64) {
      dut.io.write(index).valid.poke(false.B)
      dut.io.write(index).bits.poke(0.U)
    }
  }

  private def writeRa(
      dut: DADAORas,
      index: Int,
      value: BigInt
  ): Unit = {
    dut.io.write(index).valid.poke(true.B)
    dut.io.write(index).bits.poke(value.U)
    dut.clock.step()
    dut.io.write(index).valid.poke(false.B)
  }

  private def push(dut: DADAORas, address: BigInt): Unit = {
    dut.io.req.push.poke(true.B)
    dut.io.req.pushAddress.poke(address.U)
    dut.io.req.pop.poke(false.B)
    dut.clock.step()
    dut.io.req.push.poke(false.B)
  }

  private def pop(dut: DADAORas): Unit = {
    dut.io.req.push.poke(false.B)
    dut.io.req.pop.poke(true.B)
    dut.clock.step()
    dut.io.req.pop.poke(false.B)
  }

  it should "push, fold recursion, pop and underflow a cold RegRAS" in {
    test(new DADAORas(params)) { dut =>
      clearWrites(dut)
      dut.io.req.push.poke(false.B)
      dut.io.req.pushAddress.poke(0.U)
      dut.io.req.pop.poke(false.B)

      val addressA = BigInt("fc0000000100", 16)
      val addressB = BigInt("fc0000000200", 16)

      push(dut, addressA)
      dut.io.resp.raCnt.expect(1.U)
      dut.io.values(63).expect(
        ((BigInt(1) << 48) | addressA).U
      )

      push(dut, addressA)
      dut.io.resp.raCnt.expect(1.U)
      dut.io.values(63).expect(
        ((BigInt(2) << 48) | addressA).U
      )

      push(dut, addressB)
      dut.io.resp.raCnt.expect(2.U)
      dut.io.values(63).expect(
        ((BigInt(1) << 48) | addressB).U
      )
      dut.io.values(62).expect(
        ((BigInt(2) << 48) | addressA).U
      )

      dut.io.req.pop.poke(true.B)
      dut.io.resp.popAddress.expect(addressB.U)
      dut.io.resp.fault.expect(false.B)
      dut.clock.step()
      dut.io.req.pop.poke(false.B)
      dut.io.resp.raCnt.expect(1.U)
      dut.io.values(63).expect(
        ((BigInt(2) << 48) | addressA).U
      )

      dut.io.req.pop.poke(true.B)
      dut.io.resp.popAddress.expect(addressA.U)
      dut.io.resp.fault.expect(false.B)
      dut.clock.step()
      dut.io.req.pop.poke(false.B)
      dut.io.resp.raCnt.expect(1.U)
      dut.io.values(63).expect(
        ((BigInt(1) << 48) | addressA).U
      )

      dut.io.req.pop.poke(true.B)
      dut.io.resp.popAddress.expect(addressA.U)
      dut.io.resp.fault.expect(false.B)
      dut.clock.step()
      dut.io.req.pop.poke(false.B)
      dut.io.resp.raCnt.expect(0.U)

      dut.io.req.pop.poke(true.B)
      dut.io.resp.fault.expect(true.B)
      dut.io.resp.faultCode.expect(DADAOFaultCode.Rasuf.U)
      dut.clock.step()
      dut.io.req.pop.poke(false.B)
      dut.io.resp.raCnt.expect(0.U)
    }
  }

  it should "raise RASOF and RASUF without partial state changes" in {
    test(new DADAORas(params)) { dut =>
      clearWrites(dut)
      dut.io.req.push.poke(false.B)
      dut.io.req.pushAddress.poke(0.U)
      dut.io.req.pop.poke(false.B)

      writeRa(dut, 0, BigInt(63) << 48)
      dut.io.req.push.poke(true.B)
      dut.io.req.pushAddress.poke(BigInt("fc0000000300", 16).U)
      dut.io.resp.fault.expect(true.B)
      dut.io.resp.faultCode.expect(DADAOFaultCode.Rasof.U)
      dut.io.resp.raCnt.expect(63.U)
      dut.clock.step()
      dut.io.req.push.poke(false.B)

      writeRa(
        dut,
        0,
        (BigInt(1) << 48) | BigInt("fc0000000400", 16)
      )
      writeRa(dut, 63, BigInt("fc0000000400", 16))
      dut.io.req.pop.poke(true.B)
      dut.io.resp.fault.expect(true.B)
      dut.io.resp.faultCode.expect(DADAOFaultCode.Rasuf.U)
      dut.clock.step()
      dut.io.req.pop.poke(false.B)
      dut.io.resp.raCnt.expect(1.U)
    }
  }

  private def startPush(dut: DADAORas, address: BigInt): Unit = {
    dut.io.req.push.poke(true.B)
    dut.io.req.pushAddress.poke(address.U)
    dut.io.req.pop.poke(false.B)
    dut.clock.step()
    dut.io.req.push.poke(false.B)
  }

  private def startPop(dut: DADAORas): Unit = {
    dut.io.req.push.poke(false.B)
    dut.io.req.pop.poke(true.B)
    dut.clock.step()
    dut.io.req.pop.poke(false.B)
  }

  private def acceptMemReq(dut: DADAORas): Unit = {
    dut.io.memReqAccepted.poke(true.B)
    dut.clock.step()
    dut.io.memReqAccepted.poke(false.B)
  }

  private def completeMemResp(
      dut: DADAORas,
      data: BigInt,
      fault: Boolean = false,
      faultCode: Int = DADAOFaultCode.None
  ): Unit = {
    dut.io.memResp.valid.poke(true.B)
    dut.io.memResp.data.poke(data.U)
    dut.io.memResp.fault.poke(fault.B)
    dut.io.memResp.faultCode.poke(faultCode.U)
    dut.io.resp.done.expect(true.B)
    dut.clock.step()
    dut.io.memResp.valid.poke(false.B)
    dut.io.memResp.fault.poke(false.B)
  }

  it should "spill the oldest entry and shift the architectural view" in {
    test(new DADAORas(params)) { dut =>
      clearWrites(dut)

      val mrPtr = BigInt("fc0000004000", 16)
      val oldest = (BigInt(7) << 48) |
        BigInt("fc0000000100", 16)
      val secondTop = (BigInt(2) << 48) |
        BigInt("fc0000000200", 16)
      val top = (BigInt(3) << 48) |
        BigInt("fc0000000300", 16)
      val pushed = BigInt("fc0000000500", 16)

      writeRa(dut, 0, (BigInt(63) << 48) | mrPtr)
      writeRa(dut, 1, oldest)
      writeRa(dut, 2, secondTop)
      writeRa(dut, 63, top)

      startPush(dut, pushed)
      dut.io.resp.done.expect(false.B)
      dut.io.resp.memReqValid.expect(true.B)
      dut.io.resp.memReqWrite.expect(true.B)
      dut.io.resp.memReqAddr.expect((mrPtr - 8).U)
      dut.io.resp.memReqWdata.expect(oldest.U)
      acceptMemReq(dut)
      dut.io.resp.memReqValid.expect(false.B)

      completeMemResp(dut, 0)
      dut.io.resp.fault.expect(false.B)
      dut.io.resp.raCnt.expect(63.U)
      dut.io.resp.mrPtr.expect((mrPtr - 8).U)
      dut.io.values(63).expect(
        ((BigInt(1) << 48) | pushed).U
      )
      dut.io.values(62).expect(top.U)
      dut.io.values(1).expect(secondTop.U)
    }
  }

  it should "restore one or many entries from MemRAS on ret" in {
    test(new DADAORas(params)) { dut =>
      clearWrites(dut)

      val mrPtr = BigInt("fc0000006000", 16)
      val returnAddress = BigInt("fc0000001234", 16)
      writeRa(dut, 0, mrPtr)

      startPop(dut)
      dut.io.resp.memReqValid.expect(true.B)
      dut.io.resp.memReqWrite.expect(false.B)
      dut.io.resp.memReqAddr.expect(mrPtr.U)
      acceptMemReq(dut)

      dut.io.memResp.valid.poke(true.B)
      dut.io.memResp.data.poke(
        ((BigInt(1) << 48) | returnAddress).U
      )
      dut.io.memResp.fault.poke(false.B)
      dut.io.memResp.faultCode.poke(0.U)
      dut.io.resp.done.expect(true.B)
      dut.io.resp.popAddress.expect(returnAddress.U)
      dut.io.resp.fault.expect(false.B)
      dut.clock.step()
      dut.io.memResp.valid.poke(false.B)
      dut.io.resp.raCnt.expect(0.U)
      dut.io.resp.mrPtr.expect((mrPtr + 8).U)

      writeRa(dut, 0, mrPtr)
      startPop(dut)
      acceptMemReq(dut)
      dut.io.memResp.valid.poke(true.B)
      dut.io.memResp.data.poke(
        ((BigInt(3) << 48) | returnAddress).U
      )
      dut.io.memResp.fault.poke(false.B)
      dut.io.resp.popAddress.expect(returnAddress.U)
      dut.clock.step()
      dut.io.memResp.valid.poke(false.B)
      dut.io.resp.raCnt.expect(1.U)
      dut.io.resp.mrPtr.expect((mrPtr + 8).U)
      dut.io.values(63).expect(
        ((BigInt(2) << 48) | returnAddress).U
      )
    }
  }

  it should "raise RASUF for a zero-count MemRAS entry" in {
    test(new DADAORas(params)) { dut =>
      clearWrites(dut)

      val mrPtr = BigInt("fc0000007000", 16)
      writeRa(dut, 0, mrPtr)
      startPop(dut)
      acceptMemReq(dut)

      dut.io.memResp.valid.poke(true.B)
      dut.io.memResp.data.poke(0.U)
      dut.io.memResp.fault.poke(false.B)
      dut.io.resp.done.expect(true.B)
      dut.io.resp.fault.expect(true.B)
      dut.io.resp.faultCode.expect(DADAOFaultCode.Rasuf.U)
      dut.io.resp.popAddress.expect(0.U)
      dut.clock.step()
      dut.io.memResp.valid.poke(false.B)
      dut.io.resp.raCnt.expect(0.U)
      dut.io.resp.mrPtr.expect(mrPtr.U)
    }
  }

  it should "keep MemRAS state unchanged on fault or misalignment" in {
    test(new DADAORas(params)) { dut =>
      clearWrites(dut)

      val mrPtr = BigInt("fc0000008000", 16)
      val top = (BigInt(3) << 48) |
        BigInt("fc0000000300", 16)
      writeRa(dut, 0, (BigInt(63) << 48) | mrPtr)
      writeRa(dut, 63, top)

      startPush(dut, BigInt("fc0000009000", 16))
      acceptMemReq(dut)
      dut.io.memResp.valid.poke(true.B)
      dut.io.memResp.data.poke(0.U)
      dut.io.memResp.fault.poke(true.B)
      dut.io.memResp.faultCode.poke(DADAOFaultCode.Unmapped.U)
      dut.io.resp.done.expect(true.B)
      dut.io.resp.fault.expect(true.B)
      dut.io.resp.faultCode.expect(DADAOFaultCode.Unmapped.U)
      dut.clock.step()
      dut.io.memResp.valid.poke(false.B)
      dut.io.memResp.fault.poke(false.B)
      dut.io.resp.raCnt.expect(63.U)
      dut.io.resp.mrPtr.expect(mrPtr.U)
      dut.io.values(63).expect(top.U)

      writeRa(dut, 0, (BigInt(63) << 48) | (mrPtr + 4))
      dut.io.req.push.poke(true.B)
      dut.io.req.pushAddress.poke(BigInt("fc000000a000", 16).U)
      dut.io.req.pop.poke(false.B)
      dut.io.resp.done.expect(true.B)
      dut.io.resp.memReqValid.expect(false.B)
      dut.io.resp.fault.expect(true.B)
      dut.io.resp.faultCode.expect(DADAOFaultCode.Malign.U)
      dut.clock.step()
      dut.io.req.push.poke(false.B)
      dut.io.resp.raCnt.expect(63.U)
      dut.io.resp.mrPtr.expect((mrPtr + 4).U)
      dut.io.values(63).expect(top.U)
    }
  }
}
