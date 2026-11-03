package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAORasOracleSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAORas oracle"

  private val params = DADAOParams()

  private def clearInputs(dut: DADAORas): Unit = {
    dut.io.req.push.poke(false.B)
    dut.io.req.pop.poke(false.B)
    dut.io.req.pushAddress.poke(0.U)
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

  DADAORasOracleTable.vectors.foreach { vector =>
    it should s"match ${vector.name}" in {
      test(new DADAORas(params)) { dut =>
        clearInputs(dut)
        writeRa(
          dut,
          0,
          (BigInt(vector.initialRaCnt) << 48) |
            vector.initialMrPtr
        )
        if (vector.initialTopCount != 0) {
          writeRa(
            dut,
            63,
            (BigInt(vector.initialTopCount) << 48) |
              vector.initialTopAddr
          )
        }
        if (vector.initialNextTopCount != 0) {
          writeRa(
            dut,
            62,
            (BigInt(vector.initialNextTopCount) << 48) |
              vector.initialNextTopAddr
          )
        }
        if (vector.initialOldestAddr != 0) {
          writeRa(
            dut,
            1,
            (BigInt(1) << 48) | vector.initialOldestAddr
          )
        }

        dut.io.req.push.poke(vector.requestPush.B)
        dut.io.req.pop.poke(vector.requestPop.B)
        dut.io.req.pushAddress.poke(vector.requestAddr.U)
        dut.clock.step()

        if (vector.expectedMemReqValid) {
          dut.io.resp.memReqValid.expect(true.B)
          dut.io.resp.memReqWrite.expect(vector.expectedMemReqWrite.B)
          dut.io.resp.memReqAddr.expect(vector.expectedMemReqAddr.U)
          dut.io.req.push.poke(false.B)
          dut.io.req.pop.poke(false.B)
          dut.io.memReqAccepted.poke(true.B)
          dut.clock.step()
          dut.io.memReqAccepted.poke(false.B)

          dut.io.memResp.valid.poke(true.B)
          dut.io.memResp.data.poke(
            (
              (BigInt(vector.responseCount) << 48) |
                vector.responseAddress
            ).U
          )
          dut.io.memResp.fault.poke(vector.responseFault.B)
          dut.io.memResp.faultCode.poke(vector.responseFaultCode.U)
          dut.io.resp.done.expect(vector.expectedDone.B)
          dut.io.resp.faultCode.expect(vector.expectedFaultCode.U)
          dut.clock.step()
          dut.io.memResp.valid.poke(false.B)
          dut.io.memResp.fault.poke(false.B)
        } else {
          dut.io.resp.done.expect(vector.expectedDone.B)
          dut.io.resp.faultCode.expect(vector.expectedFaultCode.U)
          dut.io.req.push.poke(false.B)
          dut.io.req.pop.poke(false.B)
        }

        dut.io.resp.raCnt.expect(vector.expectedRaCnt.U)
        dut.io.resp.mrPtr.expect(vector.expectedMrPtr.U)
        dut.io.values(63).expect(
          (
            (BigInt(vector.expectedTopCount) << 48) |
              vector.expectedTopAddr
          ).U
        )
      }
    }
  }
}
