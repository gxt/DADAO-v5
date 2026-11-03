package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOMemPortSpec extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "DADAOCore reset interface"

  it should "freeze the test-machine RAM base and owner states" in {
    val params = DADAOParams()

    assert(params.ramBase == BigInt("fc0000000000", 16))
    assert(DADAOMemOwner.Idle == 0)
    assert(DADAOMemOwner.Fetch == 1)
    assert(DADAOMemOwner.Data == 2)
  }

  it should "start fetching at the frozen reset vector" in {
    val params = DADAOParams()

    test(new DADAOCore(params)) { dut =>
      dut.io.pc.expect(params.resetVector.U)
      dut.io.mem.req.valid.expect(true.B)
      dut.io.mem.req.bits.addr.expect(params.resetVector.U)
      dut.io.mem.req.bits.write.expect(false.B)
      dut.io.mem.req.bits.size.expect(DADAOMemSize.Tetra.U)
      dut.io.mem.req.bits.wdata.expect(0.U)
      dut.io.mem.req.bits.wstrb.expect(0.U)
      dut.io.mem.req.bits.kind.expect(DADAOMemKind.Fetch.U)
      dut.io.mem.resp.ready.expect(true.B)
    }
  }
}
