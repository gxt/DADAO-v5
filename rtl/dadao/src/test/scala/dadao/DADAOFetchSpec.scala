package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOFetchSpec extends AnyFlatSpec with ChiselScalatestTester {
  behavior of "DADAOCore fetch/decode"

  private val params = DADAOParams()
  private val testPc = BigInt("fc0000000000", 16)

  private def resetTo(dut: DADAOCore, pc: BigInt): Unit = {
    dut.io.testRegWrite.get.valid.poke(false.B)
    dut.io.testRegWrite.get.bank.poke(DADAORegBank.Rd.U)
    dut.io.testRegWrite.get.addr.poke(0.U)
    dut.io.testRegWrite.get.data.poke(0.U)
    dut.io.debugRegBank.get.poke(DADAORegBank.Rd.U)
    dut.io.debugRegAddr.get.poke(0.U)
    dut.io.pcInitValid.get.poke(true.B)
    dut.io.pcInit.get.poke(pc.U)
    dut.reset.poke(true.B)
    dut.clock.step(2)
    dut.reset.poke(false.B)
    dut.clock.step()
    dut.io.pcInitValid.get.poke(false.B)
  }

  private def completeFetch(
      dut: DADAOCore,
      word: BigInt,
      responseDelay: Int = 0
  ): Unit = {
    dut.io.mem.req.ready.poke(true.B)
    dut.clock.step()
    dut.io.mem.req.valid.expect(false.B)

    if (responseDelay > 0) {
      dut.clock.step(responseDelay)
    }
    dut.io.mem.resp.valid.poke(true.B)
    dut.io.mem.resp.bits.rdata.poke(word.U)
    dut.io.mem.resp.bits.fault.poke(false.B)
    dut.io.mem.resp.bits.faultCode.poke(0.U)
    dut.clock.step()
    dut.io.mem.resp.valid.poke(false.B)
  }

  private def setField(
      value: BigInt,
      offset: Int,
      field: BigInt,
      width: Int
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (value & ~mask) | ((field << offset) & mask)
  }

  it should "hold the request while waiting and commit only after response" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      resetTo(dut, testPc)
      dut.io.debugPc.get.expect(testPc.U)

      dut.io.mem.req.valid.expect(true.B)
      dut.io.mem.req.bits.addr.expect(testPc.U)
      dut.io.mem.req.bits.kind.expect(DADAOMemKind.Fetch.U)
      dut.io.mem.req.bits.size.expect(DADAOMemSize.Tetra.U)
      dut.io.mem.req.bits.wstrb.expect(0.U)

      dut.io.mem.req.ready.poke(false.B)
      dut.clock.step(2)
      dut.io.mem.req.bits.addr.expect(testPc.U)
      dut.io.debugPc.get.expect(testPc.U)

      dut.io.mem.req.ready.poke(true.B)
      dut.clock.step()
      dut.io.mem.req.valid.expect(false.B)
      dut.clock.step(2)
      dut.io.debugPc.get.expect(testPc.U)

      val swym = DADAODecoderTable.entries(DADAODecoderTable.swymId)
      dut.io.mem.resp.valid.poke(true.B)
      dut.io.mem.resp.bits.rdata.poke(swym.value.U)
      dut.io.mem.resp.bits.fault.poke(false.B)
      dut.clock.step()

      dut.io.debugPc.get.expect((testPc + 4).U)
      dut.io.debugDecodedValid.get.expect(true.B)
      dut.io.debugNoop.get.expect(true.B)
      dut.io.mem.resp.valid.poke(false.B)
    }
  }

  it should "keep full rb0 while fetching only its low 48 bits" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      val fullPc =
        testPc | (BigInt("abcd", 16) << 48)

      resetTo(dut, fullPc)
      dut.io.debugPc.get.expect(fullPc.U)
      dut.io.mem.req.valid.expect(true.B)
      dut.io.mem.req.bits.addr.expect(testPc.U)

      dut.io.debugRegBank.get.poke(DADAORegBank.Rb.U)
      dut.io.debugRegAddr.get.poke(0.U)
      dut.io.debugRegData.get.expect(fullPc.U)

      val swym = DADAODecoderTable.entries(DADAODecoderTable.swymId)
      completeFetch(dut, swym.value)
      dut.io.debugPc.get.expect((fullPc + 4).U)
      dut.io.debugFault.get.expect(false.B)
    }
  }

  it should "commit a taken branch through the control path" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      val branch =
        DADAODecoderTable.entries(
          DADAODecoderTable.ids.indexOf("br.z_riii_rd")
        )
      val word = setField(
        setField(branch.value, 18, 0, 6),
        0,
        2,
        18
      )

      resetTo(dut, testPc)
      completeFetch(dut, word)
      dut.io.debugPc.get.expect((testPc + 8).U)
      dut.io.debugFault.get.expect(false.B)
      dut.io.mem.req.bits.addr.expect((testPc + 8).U)
    }
  }

  it should "push a call return address and pop it through ret" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      val call =
        DADAODecoderTable.entries(
          DADAODecoderTable.ids.indexOf("call_iiii_ra")
        )
      val ret =
        DADAODecoderTable.entries(
          DADAODecoderTable.ids.indexOf("ret_riii_ra")
        )
      val callWord = setField(call.value, 0, 2, 24)
      val retWord =
        setField(setField(ret.value, 18, 0, 6), 0, 0, 18)

      resetTo(dut, testPc)
      completeFetch(dut, callWord)
      dut.io.debugPc.get.expect((testPc + 8).U)
      dut.io.debugRegBank.get.poke(DADAORegBank.Ra.U)
      dut.io.debugRegAddr.get.poke(63.U)
      dut.io.debugRegData.get.expect(
        ((BigInt(1) << 48) | (testPc + 4)).U
      )

      completeFetch(dut, retWord)
      dut.io.debugPc.get.expect((testPc + 4).U)
      dut.io.debugRegAddr.get.poke(0.U)
      dut.io.debugRegData.get.expect(0.U)
      dut.io.debugFault.get.expect(false.B)
    }
  }

  it should "stop before fetch on an unaligned PC" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      resetTo(dut, testPc + 2)
      dut.clock.step()
      dut.io.mem.req.valid.expect(false.B)
      dut.io.debugFault.get.expect(true.B)
      dut.io.debugFaultCode.get.expect(DADAOFaultCode.Ialign.U)
      dut.io.debugPc.get.expect((testPc + 2).U)
    }
  }

  it should "raise UNDI for a reserved word without advancing PC" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      resetTo(dut, testPc)
      completeFetch(dut, BigInt(0))
      dut.io.debugFault.get.expect(true.B)
      dut.io.debugFaultCode.get.expect(DADAOFaultCode.Undi.U)
      dut.io.debugPc.get.expect(testPc.U)
    }
  }

  it should "raise ILLI for an out-of-scope implemented encoding" in {
    test(new DADAOCore(params, testMode = true)) { dut =>
      resetTo(dut, testPc)
      val fp = DADAODecoderTable.entries.find(_.scope == DADAOScope.Fp).get
      completeFetch(dut, fp.value)
      dut.io.debugFault.get.expect(true.B)
      dut.io.debugFaultCode.get.expect(DADAOFaultCode.Illi.U)
      dut.io.debugFaultReason.get
        .expect(DADAODebugFaultReason.IlliScopeFp.U)
      dut.io.debugPc.get.expect(testPc.U)
    }
  }
}
