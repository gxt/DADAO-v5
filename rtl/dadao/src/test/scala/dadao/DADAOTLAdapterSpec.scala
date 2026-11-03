package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOTLAdapterSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAOTLAdapter"

  private val params = DADAOParams()
  private val testAddr = params.ramBase + 0x100

  private def clearResponse(dut: DADAOTLAdapter): Unit = {
    dut.io.tl.d.bits.opcode.poke(0.U)
    dut.io.tl.d.bits.param.poke(0.U)
    dut.io.tl.d.bits.size.poke(0.U)
    dut.io.tl.d.bits.source.poke(0.U)
    dut.io.tl.d.bits.sink.poke(0.U)
    dut.io.tl.d.bits.denied.poke(false.B)
    dut.io.tl.d.bits.corrupt.poke(false.B)
    dut.io.tl.d.bits.data.poke(0.U)
  }

  private def clearInputs(dut: DADAOTLAdapter): Unit = {
    dut.io.core.req.valid.poke(false.B)
    dut.io.core.req.bits.addr.poke(0.U)
    dut.io.core.req.bits.write.poke(false.B)
    dut.io.core.req.bits.size.poke(DADAOMemSize.Byte.U)
    dut.io.core.req.bits.wdata.poke(0.U)
    dut.io.core.req.bits.wstrb.poke(0.U)
    dut.io.core.req.bits.kind.poke(DADAOMemKind.Data.U)
    dut.io.core.resp.ready.poke(false.B)
    dut.io.tl.a.ready.poke(false.B)
    dut.io.tl.d.valid.poke(false.B)
    clearResponse(dut)
  }

  private def acceptCoreRequest(dut: DADAOTLAdapter): Unit = {
    dut.io.core.req.valid.poke(true.B)
    dut.io.core.req.ready.expect(true.B)
    dut.clock.step()
    dut.io.core.req.valid.poke(false.B)
  }

  private def acceptA(dut: DADAOTLAdapter): Unit = {
    dut.io.tl.a.valid.expect(true.B)
    dut.io.tl.a.ready.poke(true.B)
    dut.clock.step()
    dut.io.tl.a.ready.poke(false.B)
  }

  it should "translate a Get and hold A under backpressure" in {
    test(new DADAOTLAdapter(params)) { dut =>
      clearInputs(dut)
      dut.io.core.req.bits.addr.poke(testAddr.U)
      dut.io.core.req.bits.size.poke(DADAOMemSize.Tetra.U)
      dut.io.core.req.bits.kind.poke(DADAOMemKind.Fetch.U)
      acceptCoreRequest(dut)

      dut.io.tl.a.bits.opcode.expect(
        DADAOTLMessages.Get.U
      )
      dut.io.tl.a.bits.address.expect(testAddr.U)
      dut.io.tl.a.bits.size.expect(DADAOMemSize.Tetra.U)
      dut.clock.step()
      dut.io.tl.a.valid.expect(true.B)
      acceptA(dut)

      val guestBeat =
        BigInt("1122334400000000", 16)
      clearResponse(dut)
      dut.io.tl.d.valid.poke(true.B)
      dut.io.tl.d.bits.opcode.poke(
        DADAOTLMessages.AccessAckData.U
      )
      dut.io.tl.d.bits.size.poke(DADAOMemSize.Tetra.U)
      dut.io.tl.d.bits.source.poke(0.U)
      dut.io.tl.d.bits.data.poke(
        DADAOTLEndian.reverseBeatValue(guestBeat).U
      )
      dut.io.core.resp.valid.expect(true.B)
      dut.io.core.resp.bits.rdata.expect(
        BigInt("11223344", 16).U
      )
      dut.io.core.resp.bits.fault.expect(false.B)

      dut.io.core.resp.ready.poke(true.B)
      dut.clock.step()
      dut.io.tl.d.valid.poke(false.B)
      dut.io.core.resp.valid.expect(false.B)
    }
  }

  it should "align a narrow Put to TileLink lanes" in {
    test(new DADAOTLAdapter(params)) { dut =>
      clearInputs(dut)
      dut.io.core.req.bits.addr.poke((testAddr + 2).U)
      dut.io.core.req.bits.write.poke(true.B)
      dut.io.core.req.bits.size.poke(DADAOMemSize.Wyde.U)
      dut.io.core.req.bits.wdata.poke(BigInt("abcd", 16).U)
      dut.io.core.req.bits.wstrb.poke(0x0c.U)
      acceptCoreRequest(dut)

      dut.io.tl.a.bits.opcode.expect(
        DADAOTLMessages.PutPartialData.U
      )
      dut.io.tl.a.bits.mask.expect("b00001100".U)
      dut.io.tl.a.bits.data.expect(
        BigInt("00000000cdab0000", 16).U
      )
      acceptA(dut)

      clearResponse(dut)
      dut.io.tl.d.valid.poke(true.B)
      dut.io.tl.d.bits.opcode.poke(
        DADAOTLMessages.AccessAck.U
      )
      dut.io.tl.d.bits.source.poke(0.U)
      dut.io.core.resp.valid.expect(true.B)
      dut.io.core.resp.bits.fault.expect(false.B)
      dut.io.core.resp.ready.poke(true.B)
      dut.clock.step()
    }
  }

  it should "map a denied TileLink response to ILLI" in {
    test(new DADAOTLAdapter(params)) { dut =>
      clearInputs(dut)
      dut.io.core.req.bits.addr.poke(testAddr.U)
      dut.io.core.req.bits.size.poke(DADAOMemSize.Octa.U)
      acceptCoreRequest(dut)
      acceptA(dut)

      clearResponse(dut)
      dut.io.tl.d.valid.poke(true.B)
      dut.io.tl.d.bits.opcode.poke(
        DADAOTLMessages.AccessAckData.U
      )
      dut.io.tl.d.bits.denied.poke(true.B)
      dut.io.core.resp.valid.expect(true.B)
      dut.io.core.resp.bits.fault.expect(true.B)
      dut.io.core.resp.bits.faultCode.expect(
        DADAOFaultCode.Illi.U
      )
      dut.io.core.resp.ready.poke(true.B)
      dut.clock.step()
    }
  }
}
