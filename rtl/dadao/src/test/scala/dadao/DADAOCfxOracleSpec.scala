package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOCfxOracleSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAOCfx oracle"

  private val params = DADAOParams()

  private def idOf(op: String): Int = {
    val id = op match {
      case "cfx2rd" => "cfx2rd_crrr_cfx"
      case "cfx2rc" => "cfx2rc_crrr_cfx"
      case "escape" => "escape_ciii_cfx"
      case "trap"   => "trap_ciii_cfx"
      case other =>
        throw new IllegalArgumentException(s"unsupported CFX op: $other")
    }
    DADAODecoderTable.ids.indexOf(id)
  }

  private def setField(
      word: BigInt,
      offset: Int,
      value: BigInt,
      width: Int
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (word & ~mask) | ((value << offset) & mask)
  }

  private def encodedWord(step: DADAOCfxOracleStep): BigInt = {
    val base =
      DADAODecoderTable.entries(idOf(step.op)).value
    step.op match {
      case "cfx2rd" | "cfx2rc" =>
        setField(
          setField(
            setField(
              setField(base, 18, step.cfxha, 6),
              12,
              step.cg,
              6
            ),
            6,
            step.rc,
            6
          ),
          0,
          step.rd,
          6
        )
      case "escape" | "trap" =>
        setField(
          setField(base, 18, step.cfxha, 6),
          0,
          step.immediate,
          18
        )
    }
  }

  private def clearInputs(dut: DADAOCfx): Unit = {
    dut.io.decoded.word.poke(0.U)
    dut.io.decoded.id.poke(0.U)
    dut.io.decoded.format.poke(0.U)
    dut.io.decoded.slot0.poke(0.U)
    dut.io.decoded.slot1.poke(0.U)
    dut.io.decoded.slot2.poke(0.U)
    dut.io.decoded.slot3.poke(0.U)
    dut.io.decoded.imm12.poke(0.U)
    dut.io.decoded.imm18.poke(0.U)
    dut.io.decoded.imm24.poke(0.U)
    dut.io.currentIp.poke(0.U)
    dut.io.rdValue.poke(0.U)
    dut.io.decoderFault.poke(false.B)
    dut.io.fire.poke(false.B)
    dut.io.testWrite.valid.poke(false.B)
    dut.io.testWrite.cfxha.poke(0.U)
    dut.io.testWrite.cg.poke(0.U)
    dut.io.testWrite.rc.poke(0.U)
    dut.io.testWrite.data.poke(0.U)
    dut.io.testStatusSet.valid.poke(false.B)
    dut.io.testStatusSet.runMode.poke(DADAORunMode.Hypv.U)
    dut.io.testStatusSet.cfxCode.poke(DADAOCfxCode.Power.U)
    dut.io.testStatusSet.cfxMask.poke(
      BigInt("ffffffffffffffff", 16).U
    )
    dut.io.testRead.cfxha.poke(0.U)
    dut.io.testRead.cg.poke(0.U)
    dut.io.testRead.rc.poke(0.U)
  }

  private def writeCfx(
      dut: DADAOCfx,
      write: DADAOCfxOracleRegisterWrite
  ): Unit = {
    dut.io.testWrite.valid.poke(true.B)
    dut.io.testWrite.cfxha.poke(write.cfxha.U)
    dut.io.testWrite.cg.poke(write.cg.U)
    dut.io.testWrite.rc.poke(write.rc.U)
    dut.io.testWrite.data.poke(write.data.U)
    dut.clock.step()
    dut.io.testWrite.valid.poke(false.B)
  }

  private def setStatus(
      dut: DADAOCfx,
      vector: DADAOCfxOracleVector
  ): Unit = {
    dut.io.testStatusSet.valid.poke(true.B)
    dut.io.testStatusSet.runMode.poke(vector.initialMode.U)
    dut.io.testStatusSet.cfxCode.poke(vector.initialCfx.U)
    dut.io.testStatusSet.cfxMask.poke(vector.initialMask.U)
    dut.clock.step()
    dut.io.testStatusSet.valid.poke(false.B)
  }

  private def readCfx(
      dut: DADAOCfx,
      cfxha: Int,
      cg: Int,
      rc: Int
  ): BigInt = {
    dut.io.testRead.cfxha.poke(cfxha.U)
    dut.io.testRead.cg.poke(cg.U)
    dut.io.testRead.rc.poke(rc.U)
    dut.io.testReadValid.expect(true.B)
    dut.io.testReadData.peek().litValue
  }

  DADAOCfxOracleTable.vectors.foreach { vector =>
    it should s"match ${vector.name}" in {
      test(new DADAOCfx(params)) { dut =>
        clearInputs(dut)
        setStatus(dut, vector)
        vector.registerWrites.foreach(writeCfx(dut, _))

        vector.steps.foreach { step =>
          dut.io.decoded.word.poke(encodedWord(step).U(32.W))
          dut.io.decoded.id.poke(idOf(step.op).U)
          dut.io.currentIp.poke(step.currentIp.U)
          dut.io.rdValue.poke(step.rdValue.U)
          dut.io.decoderFault.poke(false.B)
          dut.io.fire.poke(true.B)

          dut.io.handled.expect(true.B)
          dut.io.nextIp.expect(step.expectedNextIp.U)
          dut.io.rdWrite.valid.expect(step.expectedRdValid.B)
          if (step.expectedRdValid) {
            dut.io.rdWrite.addr.expect(step.expectedRdAddr.U)
            dut.io.rdWrite.data.expect(step.expectedRdData.U)
          }
          dut.clock.step()
          dut.io.fire.poke(false.B)
        }

        dut.io.status.runMode.expect(vector.expected.runMode.U)
        dut.io.status.cfxCode.expect(vector.expected.cfxCode.U)
        dut.io.status.cfxMask.expect(vector.expected.cfxMask.U)
        readCfx(dut, vector.expected.cfxCode, 5, 2) should be(
          vector.expected.causeId
        )
        readCfx(dut, vector.expected.cfxCode, 5, 3) should be(
          vector.expected.causeIp
        )
        readCfx(dut, vector.expected.cfxCode, 4, 2) should be(
          vector.expected.trapNum
        )
        readCfx(dut, vector.expected.cfxCode, 4, 3) should be(
          vector.expected.syncNum
        )
        readCfx(dut, vector.expected.cfxCode, 4, 5) should be(
          vector.expected.escapeNum
        )
        readCfx(dut, DADAOCfxCode.Hmon, 8, 1) should be(
          vector.expected.hmonGlobalMask
        )
      }
    }
  }
}
