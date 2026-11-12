package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOCfxSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAOCfx"

  private val params = DADAOParams()
  private val testPc = BigInt("ffffffff0000", 16)
  private val hmonVector = BigInt("0fffffff0000", 16)
  private val allOnes = BigInt("ffffffffffffffff", 16)
  private val defaultSyncMask = BigInt("fffffffffffffff7", 16)

  private def idOf(name: String): Int =
    DADAODecoderTable.ids.indexOf(name)

  private def setField(
      word: BigInt,
      offset: Int,
      value: BigInt,
      width: Int = 6
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (word & ~mask) | ((value << offset) & mask)
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
    dut.io.currentIp.poke(testPc.U)
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
    dut.io.testStatusSet.cfxMask.poke(allOnes.U)
    dut.io.testRead.cfxha.poke(0.U)
    dut.io.testRead.cg.poke(0.U)
    dut.io.testRead.rc.poke(0.U)
  }

  private def writeCfx(
      dut: DADAOCfx,
      cfxha: Int,
      cg: Int,
      rc: Int,
      data: BigInt
  ): Unit = {
    dut.io.testWrite.valid.poke(true.B)
    dut.io.testWrite.cfxha.poke(cfxha.U)
    dut.io.testWrite.cg.poke(cg.U)
    dut.io.testWrite.rc.poke(rc.U)
    dut.io.testWrite.data.poke(data.U)
    dut.clock.step()
    dut.io.testWrite.valid.poke(false.B)
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

  private def setStatus(
      dut: DADAOCfx,
      mode: Int,
      cfxha: Int,
      mask: BigInt = allOnes
  ): Unit = {
    dut.io.testStatusSet.valid.poke(true.B)
    dut.io.testStatusSet.runMode.poke(mode.U)
    dut.io.testStatusSet.cfxCode.poke(cfxha.U)
    dut.io.testStatusSet.cfxMask.poke(mask.U)
    dut.clock.step()
    dut.io.testStatusSet.valid.poke(false.B)
  }

  private def pokeInstruction(
      dut: DADAOCfx,
      id: String,
      word: BigInt,
      currentIp: BigInt = testPc,
      rdValue: BigInt = 0,
      decoderFault: Boolean = false
  ): Unit = {
    dut.io.decoded.word.poke(word.U(32.W))
    dut.io.decoded.id.poke(idOf(id).U)
    dut.io.currentIp.poke(currentIp.U)
    dut.io.rdValue.poke(rdValue.U)
    dut.io.decoderFault.poke(decoderFault.B)
    dut.io.fire.poke(true.B)
  }

  private def finishInstruction(dut: DADAOCfx): Unit = {
    dut.clock.step()
    dut.io.fire.poke(false.B)
    dut.io.decoderFault.poke(false.B)
  }

  private def cfx2Word(
      id: String,
      cfxha: Int,
      cg: Int,
      rc: Int,
      rd: Int
  ): BigInt = {
    val base = DADAODecoderTable.entries(idOf(id)).value
    val withCfx = setField(base, 18, cfxha, 6)
    val withCg = setField(withCfx, 12, cg, 6)
    val withRc = setField(withCg, 6, rc, 6)
    setField(withRc, 0, rd, 6)
  }

  it should "model reset state and common CFX registers" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      dut.io.status.runMode.expect(DADAORunMode.Hypv.U)
      dut.io.status.cfxCode.expect(DADAOCfxCode.Power.U)
      dut.io.status.cfxMask.expect(allOnes.U)

      readCfx(dut, DADAOCfxCode.Power, 4, 0) should be(
        DADAOCfxCode.Power
      )
      readCfx(dut, DADAOCfxCode.Power, 4, 2) should be(0)
      readCfx(dut, DADAOCfxCode.Power, 3, 0) should be(
        defaultSyncMask
      )
      readCfx(dut, DADAOCfxCode.Hmon, 5, 63) should be(
        BigInt("0000000000003f8f", 16)
      )
      readCfx(dut, DADAOCfxCode.Power, 5, 63) should be(
        BigInt("000000000000070f", 16)
      )

      val vector = BigInt("fc0000001234", 16)
      writeCfx(dut, DADAOCfxCode.Power, 3, 10, vector)
      readCfx(dut, DADAOCfxCode.Power, 3, 10) should be(vector)
    }
  }

  it should "execute cfx2rd and cfx2rc with precise register effects" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      writeCfx(
        dut,
        DADAOCfxCode.Power,
        6,
        1,
        BigInt("123456789abcdef0", 16)
      )

      val cfx2rd = cfx2Word(
        "cfx2rd_crrr_cfx",
        DADAOCfxCode.Power,
        6,
        1,
        5
      )
      pokeInstruction(dut, "cfx2rd_crrr_cfx", cfx2rd)
      dut.io.handled.expect(true.B)
      dut.io.nextIp.expect((testPc + 4).U)
      dut.io.rdWrite.valid.expect(true.B)
      dut.io.rdWrite.addr.expect(5.U)
      dut.io.rdWrite.data.expect(BigInt("123456789abcdef0", 16).U)
      finishInstruction(dut)

      val cfx2rc = cfx2Word(
        "cfx2rc_crrr_cfx",
        DADAOCfxCode.Power,
        6,
        2,
        7
      )
      pokeInstruction(
        dut,
        "cfx2rc_crrr_cfx",
        cfx2rc,
        rdValue = BigInt("0fedcba987654321", 16)
      )
      dut.io.rdWrite.valid.expect(false.B)
      dut.io.nextIp.expect((testPc + 4).U)
      finishInstruction(dut)
      readCfx(dut, DADAOCfxCode.Power, 6, 2) should be(
        BigInt("0fedcba987654321", 16)
      )
    }
  }

  it should "route read-only-register faults through CFXREG" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      writeCfx(dut, DADAOCfxCode.Hmon, 3, 10, hmonVector)

      val word = cfx2Word(
        "cfx2rc_crrr_cfx",
        DADAOCfxCode.Power,
        4,
        0,
        1
      )
      pokeInstruction(
        dut,
        "cfx2rc_crrr_cfx",
        word,
        rdValue = BigInt(0x1234)
      )
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)

      dut.io.status.runMode.expect(DADAORunMode.Hypv.U)
      dut.io.status.cfxCode.expect(DADAOCfxCode.Hmon.U)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Reg
      )
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(1)
    }
  }

  it should "trap to another CFX and restore the frame on escape" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      writeCfx(dut, DADAOCfxCode.Hmon, 3, 10, hmonVector)
      writeCfx(
        dut,
        DADAOCfxCode.Hmon,
        3,
        2,
        defaultSyncMask
      )
      writeCfx(
        dut,
        DADAOCfxCode.Hmon,
        3,
        8,
        DADAORunMode.Supv
      )
      writeCfx(dut, DADAOCfxCode.Hmon, 3, 9, BigInt(0x5))
      writeCfx(dut, DADAOCfxCode.Hmon, 8, 1, BigInt(0x3))

      val trapBase = DADAODecoderTable.entries(
        idOf("trap_ciii_cfx")
      ).value
      val trapWord = setField(
        setField(trapBase, 18, DADAOCfxCode.Hmon, 6),
        0,
        BigInt("12345", 16),
        18
      )
      pokeInstruction(dut, "trap_ciii_cfx", trapWord)
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)

      dut.io.status.runMode.expect(DADAORunMode.Supv.U)
      dut.io.status.cfxCode.expect(DADAOCfxCode.Hmon.U)
      dut.io.status.cfxMask.expect(0x5.U)
      readCfx(dut, DADAOCfxCode.Hmon, 8, 1) should be(allOnes)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 0) should be(
        DADAORunMode.Hypv
      )
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Trap
      )
      readCfx(dut, DADAOCfxCode.Hmon, 5, 3) should be(testPc)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 2) should be(1)

      val escapeBase = DADAODecoderTable.entries(
        idOf("escape_ciii_cfx")
      ).value
      val escapeWord = setField(
        setField(escapeBase, 18, DADAOCfxCode.Hmon, 6),
        0,
        1,
        18
      )
      pokeInstruction(dut, "escape_ciii_cfx", escapeWord)
      dut.io.nextIp.expect((testPc + 4).U)
      finishInstruction(dut)

      dut.io.status.runMode.expect(DADAORunMode.Hypv.U)
      dut.io.status.cfxCode.expect(DADAOCfxCode.Hmon.U)
      dut.io.status.cfxMask.expect(allOnes)
      readCfx(dut, DADAOCfxCode.Hmon, 8, 1) should be(3)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 5) should be(1)
    }
  }

  it should "raise CFXPERM and CFXESC without partial state changes" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      writeCfx(dut, DADAOCfxCode.Hmon, 3, 10, hmonVector)
      writeCfx(
        dut,
        DADAOCfxCode.Hmon,
        3,
        2,
        defaultSyncMask
      )

      val denied = cfx2Word(
        "cfx2rd_crrr_cfx",
        DADAOCfxCode.Hmon,
        4,
        0,
        1
      )
      pokeInstruction(dut, "cfx2rd_crrr_cfx", denied)
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Perm
      )
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(1)

      val wrongEscape = setField(
        setField(
          DADAODecoderTable.entries(
            idOf("escape_ciii_cfx")
          ).value,
          18,
          DADAOCfxCode.Umom,
          6
        ),
        0,
        0,
        18
      )
      pokeInstruction(dut, "escape_ciii_cfx", wrongEscape)
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Esc
      )
    }
  }

  it should "route reserved CFX identifiers through ILLI" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      writeCfx(dut, DADAOCfxCode.Hmon, 3, 10, hmonVector)

      val trapBase = DADAODecoderTable.entries(
        idOf("trap_ciii_cfx")
      ).value
      val trapWord = setField(trapBase, 18, 6, 6)
      pokeInstruction(dut, "trap_ciii_cfx", trapWord)
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Illi
      )
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(1)

      setStatus(dut, DADAORunMode.Hypv, DADAOCfxCode.Power)
      val cfx2rd = cfx2Word(
        "cfx2rd_crrr_cfx",
        6,
        4,
        0,
        5
      )
      pokeInstruction(dut, "cfx2rd_crrr_cfx", cfx2rd)
      dut.io.nextIp.expect(hmonVector.U)
      dut.io.rdWrite.valid.expect(false.B)
      finishInstruction(dut)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Illi
      )
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(2)

      setStatus(dut, DADAORunMode.Hypv, DADAOCfxCode.Power)
      val escapeBase = DADAODecoderTable.entries(
        idOf("escape_ciii_cfx")
      ).value
      val escapeWord = setField(escapeBase, 18, 6, 6)
      pokeInstruction(dut, "escape_ciii_cfx", escapeWord)
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Illi
      )
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(3)
    }
  }

  it should "keep the global interrupt mask after a non-trap frame" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      writeCfx(dut, DADAOCfxCode.Hmon, 3, 10, hmonVector)
      writeCfx(dut, DADAOCfxCode.Hmon, 8, 1, BigInt(3))

      val cfx2rc = cfx2Word(
        "cfx2rc_crrr_cfx",
        DADAOCfxCode.Power,
        4,
        0,
        1
      )
      pokeInstruction(
        dut,
        "cfx2rc_crrr_cfx",
        cfx2rc,
        rdValue = BigInt(0x1234)
      )
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Reg
      )
      readCfx(dut, DADAOCfxCode.Hmon, 8, 1) should be(3)

      val escapeBase = DADAODecoderTable.entries(
        idOf("escape_ciii_cfx")
      ).value
      val escapeWord = setField(escapeBase, 18, DADAOCfxCode.Hmon, 6)
      pokeInstruction(dut, "escape_ciii_cfx", escapeWord)
      dut.io.nextIp.expect(testPc.U)
      finishInstruction(dut)

      dut.io.status.runMode.expect(DADAORunMode.Hypv.U)
      dut.io.status.cfxCode.expect(DADAOCfxCode.Hmon.U)
      readCfx(dut, DADAOCfxCode.Hmon, 8, 1) should be(3)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 5) should be(1)
    }
  }

  it should "reject a disabled semihosting trap as ILLI" in {
    test(new DADAOCfx(params)) { dut =>
      clearInputs(dut)
      writeCfx(dut, DADAOCfxCode.Hmon, 3, 10, hmonVector)

      val trapBase = DADAODecoderTable.entries(
        idOf("trap_ciii_cfx")
      ).value
      val trapWord = setField(
        setField(trapBase, 18, DADAOCfxCode.Hmon, 6),
        0,
        BigInt("3ff00", 16),
        18
      )
      pokeInstruction(dut, "trap_ciii_cfx", trapWord)
      dut.io.nextIp.expect(hmonVector.U)
      finishInstruction(dut)

      dut.io.status.cfxCode.expect(DADAOCfxCode.Hmon.U)
      readCfx(dut, DADAOCfxCode.Hmon, 5, 2) should be(
        DADAOCfxCause.Illi
      )
      readCfx(dut, DADAOCfxCode.Hmon, 4, 2) should be(0)
      readCfx(dut, DADAOCfxCode.Hmon, 4, 3) should be(1)
    }
  }
}
