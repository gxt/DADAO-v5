package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOTLMemorySpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAO TileLink memories"

  private val params = DADAOParams()
  private val tlParams = DADAOTLParams(params.addrBits)

  private def issueA(
      dut: DADAOTLManagerIO,
      clock: Clock,
      address: BigInt,
      opcode: Int,
      size: Int,
      mask: Int = 0,
      data: BigInt = 0
  ): Unit = {
    dut.a.valid.poke(true.B)
    dut.a.bits.opcode.poke(0.U)
    dut.a.bits.param.poke(0.U)
    dut.a.bits.size.poke(0.U)
    dut.a.bits.source.poke(0.U)
    dut.a.bits.address.poke(0.U)
    dut.a.bits.mask.poke(0.U)
    dut.a.bits.data.poke(0.U)
    dut.a.bits.corrupt.poke(false.B)
    dut.a.bits.opcode.poke(opcode.U)
    dut.a.bits.size.poke(size.U)
    dut.a.bits.source.poke(0.U)
    dut.a.bits.address.poke(address.U)
    dut.a.bits.mask.poke(mask.U)
    dut.a.bits.data.poke(data.U)
    dut.a.ready.expect(true.B)
    clock.step()
    dut.a.valid.poke(false.B)
  }

  it should "serve ROM reads and deny ROM writes" in {
    val data = BigInt("0123456789abcdef", 16)
    test(new DADAOTLROM(params, Seq(data))) { dut =>
      dut.io.tl.d.ready.poke(true.B)
      issueA(
        dut.io.tl,
        dut.clock,
        params.bootRomBase,
        DADAOTLMessages.Get,
        DADAOMemSize.Octa
      )
      dut.io.tl.d.valid.expect(true.B)
      dut.io.tl.d.bits.opcode.expect(
        DADAOTLMessages.AccessAckData.U
      )
      dut.io.tl.d.bits.data.expect(data.U)
      dut.io.tl.d.bits.denied.expect(false.B)
      dut.clock.step()

      issueA(
        dut.io.tl,
        dut.clock,
        params.bootRomBase,
        DADAOTLMessages.PutFullData,
        DADAOMemSize.Octa,
        mask = 0xff
      )
      dut.io.tl.d.valid.expect(true.B)
      dut.io.tl.d.bits.opcode.expect(
        DADAOTLMessages.AccessAck.U
      )
      dut.io.tl.d.bits.denied.expect(true.B)
      dut.clock.step()
    }
  }

  it should "merge a narrow RAM write and read it back" in {
    test(new DADAOTLRAM(params)) { dut =>
      dut.io.tl.d.ready.poke(true.B)
      val address = params.ramBase + 3
      val data = BigInt("00000000aa000000", 16)
      issueA(
        dut.io.tl,
        dut.clock,
        address,
        DADAOTLMessages.PutPartialData,
        DADAOMemSize.Byte,
        mask = 0x08,
        data = data
      )
      dut.io.tl.d.valid.expect(true.B)
      dut.io.tl.d.bits.opcode.expect(
        DADAOTLMessages.AccessAck.U
      )
      dut.clock.step()
      dut.clock.step()

      issueA(
        dut.io.tl,
        dut.clock,
        address,
        DADAOTLMessages.Get,
        DADAOMemSize.Byte
      )
      dut.io.tl.d.valid.expect(true.B)
      dut.io.tl.d.bits.opcode.expect(
        DADAOTLMessages.AccessAckData.U
      )
      dut.io.tl.d.bits.data.expect(data.U)
      dut.clock.step()
    }
  }
}
