package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOControlExecSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOControlExec"

  private val params = DADAOParams()
  private val testPc = BigInt("fc0000000000", 16)
  private val notTakenPc = testPc + 4
  private val takenPc = testPc + 8
  private val allOnes = BigInt("ffffffffffffffff", 16)

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

  private def codedWord(
      id: String,
      slot0: Int,
      slot1: Int,
      immediate: BigInt,
      immediateWidth: Int
  ): BigInt = {
    val base = DADAODecoderTable.entries(idOf(id)).value
    val withSlots =
      setField(setField(base, 18, slot0), 12, slot1)
    setField(withSlots, 0, immediate, immediateWidth)
  }

  private def pokeDecoded(
      dut: DADAOControlExec,
      id: String,
      word: BigInt,
      currentRb0: BigInt,
      read0Value: BigInt,
      read1Value: BigInt,
      poppedReturnAddress: BigInt = 0
  ): Unit = {
    dut.io.decoded.word.poke(word.U(32.W))
    dut.io.decoded.id.poke(idOf(id).U)
    dut.io.decoded.format.poke(0.U)
    dut.io.decoded.slot0.poke(((word >> 18) & 0x3f).U)
    dut.io.decoded.slot1.poke(((word >> 12) & 0x3f).U)
    dut.io.decoded.slot2.poke(((word >> 6) & 0x3f).U)
    dut.io.decoded.slot3.poke((word & 0x3f).U)
    dut.io.decoded.imm12.poke((word & 0xfff).U)
    dut.io.decoded.imm18.poke((word & 0x3ffff).U)
    dut.io.decoded.imm24.poke((word & 0xffffff).U)
    dut.io.currentRb0.poke(currentRb0.U)
    dut.io.read0Value.poke(read0Value.U)
    dut.io.read1Value.poke(read1Value.U)
    dut.io.poppedReturnAddress.poke(poppedReturnAddress.U)
  }

  it should "evaluate all conditional branches and source banks" in {
    test(new DADAOControlExec(params)) { dut =>
      val cases = Seq(
        ("br.n_riii_rd", DADAORegBank.Rd, allOnes, BigInt(0), true),
        ("br.n_riii_rd", DADAORegBank.Rd, BigInt(1), BigInt(0), false),
        ("br.nn_riii_rd", DADAORegBank.Rd, allOnes, BigInt(0), false),
        ("br.nn_riii_rd", DADAORegBank.Rd, BigInt(0), BigInt(0), true),
        ("br.z_riii_rd", DADAORegBank.Rd, BigInt(0), BigInt(0), true),
        ("br.z_riii_rd", DADAORegBank.Rd, BigInt(1), BigInt(0), false),
        ("br.nz_riii_rd", DADAORegBank.Rd, BigInt(1), BigInt(0), true),
        ("br.nz_riii_rd", DADAORegBank.Rd, BigInt(0), BigInt(0), false),
        ("br.p_riii_rd", DADAORegBank.Rd, BigInt(1), BigInt(0), true),
        ("br.p_riii_rd", DADAORegBank.Rd, allOnes, BigInt(0), false),
        ("br.np_riii_rd", DADAORegBank.Rd, BigInt(0), BigInt(0), true),
        ("br.np_riii_rd", DADAORegBank.Rd, BigInt(1), BigInt(0), false),
        ("br.eq_rrii_rd", DADAORegBank.Rd, BigInt(42), BigInt(42), true),
        ("br.eq_rrii_rd", DADAORegBank.Rd, BigInt(42), BigInt(43), false),
        ("br.ne_rrii_rd", DADAORegBank.Rd, BigInt(42), BigInt(43), true),
        ("br.ne_rrii_rd", DADAORegBank.Rd, BigInt(42), BigInt(42), false),
        ("br.z_riii_rb", DADAORegBank.Rb, BigInt(0), BigInt(0), true),
        ("br.z_riii_rb", DADAORegBank.Rb, BigInt(1), BigInt(0), false),
        ("br.nz_riii_rb", DADAORegBank.Rb, BigInt(1), BigInt(0), true),
        ("br.nz_riii_rb", DADAORegBank.Rb, BigInt(0), BigInt(0), false)
      )

      cases.foreach { case (id, bank, read0, read1, taken) =>
        val width = if (id.startsWith("br.eq") || id.startsWith("br.ne")) {
          12
        } else {
          18
        }
        val word = codedWord(id, 3, 2, 2, width)
        pokeDecoded(dut, id, word, testPc, read0, read1)

        dut.io.isControl.expect(true.B)
        dut.io.isBranch.expect(true.B)
        dut.io.isJump.expect(false.B)
        dut.io.taken.expect(taken.B)
        dut.io.nextRb0.expect((if (taken) takenPc else notTakenPc).U)
        dut.io.read0Bank.expect(bank.U)
        dut.io.read0Addr.expect(3.U)
        if (width == 12) {
          dut.io.read1Bank.expect(DADAORegBank.Rd.U)
          dut.io.read1Addr.expect(2.U)
        }
      }
    }
  }

  it should "evaluate relative and indexed jumps in full 64-bit" in {
    test(new DADAOControlExec(params)) { dut =>
      val highPc =
        testPc | (BigInt("abcd", 16) << 48)
      val relative =
        codedWord(
          "jump_iiii_rb",
          0,
          0,
          (BigInt(1) << 24) - 2,
          24
        )
      pokeDecoded(dut, "jump_iiii_rb", relative, highPc, 0, 0)

      dut.io.isControl.expect(true.B)
      dut.io.isBranch.expect(false.B)
      dut.io.isJump.expect(true.B)
      dut.io.taken.expect(true.B)
      dut.io.nextRb0.expect((highPc - 8).U)

      val base = BigInt("0011223344556677", 16)
      val indexed =
        codedWord("jump_rrii_rb", 3, 2, 2, 12)
      pokeDecoded(dut, "jump_rrii_rb", indexed, highPc, base, 16)

      dut.io.isControl.expect(true.B)
      dut.io.isBranch.expect(false.B)
      dut.io.isJump.expect(true.B)
      dut.io.taken.expect(true.B)
      dut.io.read0Bank.expect(DADAORegBank.Rb.U)
      dut.io.read0Addr.expect(3.U)
      dut.io.read1Bank.expect(DADAORegBank.Rd.U)
      dut.io.read1Addr.expect(2.U)
      dut.io.nextRb0.expect((base + 24).U)
    }
  }

  it should "evaluate call targets and ret through the popped address" in {
    test(new DADAOControlExec(params)) { dut =>
      val relative =
        codedWord("call_iiii_ra", 0, 0, 2, 24)
      pokeDecoded(dut, "call_iiii_ra", relative, testPc, 0, 0)
      dut.io.isControl.expect(true.B)
      dut.io.isBranch.expect(false.B)
      dut.io.isJump.expect(false.B)
      dut.io.isCall.expect(true.B)
      dut.io.isRet.expect(false.B)
      dut.io.nextRb0.expect(takenPc.U)
      dut.io.callReturnAddress.expect((testPc + 4).U)

      val base = BigInt("0011223344556677", 16)
      val indexed =
        codedWord("call_rrii_ra", 3, 2, 2, 12)
      pokeDecoded(dut, "call_rrii_ra", indexed, testPc, base, 16)
      dut.io.isCall.expect(true.B)
      dut.io.read0Bank.expect(DADAORegBank.Rb.U)
      dut.io.read1Bank.expect(DADAORegBank.Rd.U)
      dut.io.nextRb0.expect((base + 24).U)

      val ret = codedWord("ret_riii_ra", 1, 0, 42, 18)
      pokeDecoded(
        dut,
        "ret_riii_ra",
        ret,
        testPc,
        0,
        0,
        BigInt("fc0000001234", 16)
      )
      dut.io.isControl.expect(true.B)
      dut.io.isCall.expect(false.B)
      dut.io.isRet.expect(true.B)
      dut.io.nextRb0.expect(BigInt("fc0000001234", 16).U)
      dut.io.retRdWrite.expect(true.B)
      dut.io.retRdAddr.expect(1.U)
      dut.io.retRdValue.expect(42.U)
    }
  }
}
