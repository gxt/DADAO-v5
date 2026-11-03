package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOTestMemorySpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOTestMemory"

  private val params = DADAOParams()
  private val address = BigInt("fc0000000000", 16)

  private def loadEntry(
      dut: DADAOTestMemory,
      index: Int,
      data: BigInt,
      writable: Boolean = true,
      fault: Boolean = false,
      faultCode: Int = 0
  ): Unit = {
    dut.io.load.valid.poke(true.B)
    dut.io.load.index.poke(index.U)
    dut.io.load.address.poke(address.U)
    dut.io.load.data.poke(data.U)
    dut.io.load.writable.poke(writable.B)
    dut.io.load.fault.poke(fault.B)
    dut.io.load.faultCode.poke(faultCode.U)
    dut.clock.step()
    dut.io.load.valid.poke(false.B)
  }

  private def presentRequest(
      dut: DADAOTestMemory,
      write: Boolean = false,
      wdata: BigInt = 0,
      size: Int = DADAOMemSize.Octa,
      addrLow: Int = 0,
      wstrb: Int = 0xff
  ): Unit = {
    dut.io.req.valid.poke(true.B)
    dut.io.req.bits.addr.poke((address + addrLow).U)
    dut.io.req.bits.write.poke(write.B)
    dut.io.req.bits.size.poke(size.U)
    dut.io.req.bits.wdata.poke(wdata.U)
    dut.io.req.bits.wstrb.poke(wstrb.U)
    dut.io.req.bits.kind.poke(DADAOMemKind.Data.U)
  }

  private def waitForRequestAccept(dut: DADAOTestMemory): Unit = {
    var cycles = 0
    while (!dut.io.req.ready.peek().litToBoolean && cycles < 16) {
      dut.clock.step()
      cycles += 1
    }
    assert(
      dut.io.req.ready.peek().litToBoolean,
      "test memory did not accept request within 16 cycles"
    )
    dut.clock.step()
    dut.io.req.valid.poke(false.B)
  }

  private def waitForResponse(dut: DADAOTestMemory): Unit = {
    var cycles = 0
    dut.io.resp.ready.poke(true.B)
    while (!dut.io.resp.valid.peek().litToBoolean && cycles < 16) {
      dut.clock.step()
      cycles += 1
    }
    assert(
      dut.io.resp.valid.peek().litToBoolean,
      "test memory did not return a response within 16 cycles"
    )
  }

  it should "honor request-ready and response latency delays" in {
    for (latency <- Seq(0, 1, 2, 4)) {
      test(
        new DADAOTestMemory(
          params,
          maxEntries = 8,
          reqReadyDelay = 2,
          memRespLatency = latency
        )
      ) { dut =>
        loadEntry(dut, 0, BigInt("77880000", 16))
        presentRequest(dut)

        dut.io.req.ready.expect(false.B)
        dut.clock.step()
        dut.io.req.ready.expect(false.B)
        dut.clock.step()
        dut.io.req.ready.expect(true.B)
        waitForRequestAccept(dut)

        if (latency > 0) {
          dut.io.resp.valid.expect(false.B)
          dut.clock.step(latency)
        }
        waitForResponse(dut)
        dut.io.resp.bits.rdata.expect(
          BigInt("77880000", 16).U
        )
        dut.io.resp.bits.fault.expect(false.B)
        dut.clock.step()
        dut.io.resp.valid.expect(false.B)
      }
    }
  }

  it should "commit a store and return the updated value" in {
    test(new DADAOTestMemory(params, maxEntries = 8)) { dut =>
      loadEntry(dut, 0, BigInt("1122334455667788", 16))

      presentRequest(
        dut,
        write = true,
        wdata = BigInt("8877665544332211", 16)
      )
      waitForRequestAccept(dut)
      waitForResponse(dut)
      dut.io.resp.bits.fault.expect(false.B)
      dut.clock.step()

      presentRequest(dut)
      waitForRequestAccept(dut)
      waitForResponse(dut)
      dut.io.resp.bits.rdata.expect(
        BigInt("8877665544332211", 16).U
      )
      dut.io.stats.writeCount.expect(1.U)
    }
  }

  it should "merge byte and wyde stores without disturbing other lanes" in {
    test(new DADAOTestMemory(params, maxEntries = 8)) { dut =>
      loadEntry(dut, 0, BigInt("1122334455667788", 16))

      presentRequest(
        dut,
        write = true,
        wdata = BigInt("aa", 16),
        size = DADAOMemSize.Byte,
        addrLow = 2,
        wstrb = 0x04
      )
      waitForRequestAccept(dut)
      waitForResponse(dut)
      dut.io.resp.bits.fault.expect(false.B)
      dut.clock.step()

      presentRequest(
        dut,
        write = true,
        wdata = BigInt("aabb", 16),
        size = DADAOMemSize.Wyde,
        addrLow = 4,
        wstrb = 0x30
      )
      waitForRequestAccept(dut)
      waitForResponse(dut)
      dut.io.resp.bits.fault.expect(false.B)
      dut.clock.step()

      presentRequest(dut)
      waitForRequestAccept(dut)
      waitForResponse(dut)
      dut.io.resp.bits.rdata.expect(
        BigInt("1122aa44aabb7788", 16).U
      )
    }
  }

  it should "return big-endian narrow values from the selected offset" in {
    test(new DADAOTestMemory(params, maxEntries = 8)) { dut =>
      loadEntry(dut, 0, BigInt("1122334455667788", 16))

      presentRequest(
        dut,
        size = DADAOMemSize.Wyde,
        addrLow = 2
      )
      waitForRequestAccept(dut)
      waitForResponse(dut)
      dut.io.resp.bits.rdata.expect(BigInt("3344", 16).U)
      dut.clock.step()

      presentRequest(
        dut,
        size = DADAOMemSize.Tetra,
        addrLow = 4
      )
      waitForRequestAccept(dut)
      waitForResponse(dut)
      dut.io.resp.bits.rdata.expect(BigInt("55667788", 16).U)
    }
  }

  it should "return UNMAPPED for a missing entry" in {
    test(new DADAOTestMemory(params, maxEntries = 8)) { dut =>
      presentRequest(dut)
      waitForRequestAccept(dut)
      waitForResponse(dut)

      dut.io.resp.bits.fault.expect(true.B)
      dut.io.resp.bits.faultCode.expect(
        DADAOFaultCode.Unmapped.U
      )
      dut.clock.step()
      dut.io.stats.unmappedCount.expect(1.U)
    }
  }

  it should "reject a write to a read-only entry with ILLI" in {
    test(new DADAOTestMemory(params, maxEntries = 8)) { dut =>
      loadEntry(
        dut,
        0,
        BigInt("77880000", 16),
        writable = false
      )
      presentRequest(dut, write = true, wdata = 1)
      waitForRequestAccept(dut)
      waitForResponse(dut)

      dut.io.resp.bits.fault.expect(true.B)
      dut.io.resp.bits.faultCode.expect(
        DADAOFaultCode.Illi.U
      )
      dut.io.stats.writeCount.expect(0.U)
    }
  }

  it should "propagate an injected response fault" in {
    test(new DADAOTestMemory(params, maxEntries = 8)) { dut =>
      loadEntry(
        dut,
        0,
        BigInt("77880000", 16),
        fault = true,
        faultCode = DADAOFaultCode.Unmapped
      )
      presentRequest(dut)
      waitForRequestAccept(dut)
      waitForResponse(dut)

      dut.io.resp.bits.fault.expect(true.B)
      dut.io.resp.bits.faultCode.expect(
        DADAOFaultCode.Unmapped.U
      )
      dut.clock.step()
      dut.io.stats.faultCount.expect(1.U)
    }
  }
}
