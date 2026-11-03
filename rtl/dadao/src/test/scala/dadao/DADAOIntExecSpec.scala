package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAOIntExecSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAOIntExec"

  private val params = DADAOParams()
  private val testPc = BigInt("fc0000000000", 16)
  private val allOnes64 = (BigInt(1) << 64) - 1

  private def entryFor(id: String): DADAOExecEntry =
    DADAOExecTable.entries(
      DADAOExecTable.ids.indexOf(id)
    )

  private def baseWord(id: String): BigInt =
    DADAODecoderTable.entries(entryFor(id).id).value

  private def setField(
      word: BigInt,
      offset: Int,
      value: BigInt,
      width: Int = 6
  ): BigInt = {
    val mask = ((BigInt(1) << width) - 1) << offset
    (word & ~mask) | ((value << offset) & mask)
  }

  private def clear(
      dut: DADAOIntExecHarness,
      pc: BigInt = testPc
  ): Unit = {
    dut.io.pc.poke(pc.U)
    dut.io.word.poke(0.U)
    dut.io.instructionId.poke(0.U)
    dut.io.commit.poke(false.B)
    dut.io.controlValid.poke(true.B)
    dut.io.controlIsM1.poke(true.B)
    dut.io.testRegWrite.valid.poke(false.B)
    dut.io.testRegWrite.bank.poke(DADAORegBank.Rd.U)
    dut.io.testRegWrite.addr.poke(0.U)
    dut.io.testRegWrite.data.poke(0.U)
    dut.io.extWrite.valid.poke(false.B)
    dut.io.extWrite.bank.poke(DADAORegBank.Rd.U)
    dut.io.extWrite.addr.poke(0.U)
    dut.io.extWrite.data.poke(0.U)
    dut.io.debugReadBank.poke(DADAORegBank.Rd.U)
    dut.io.debugReadAddr.poke(0.U)
  }

  private def loadRegister(
      dut: DADAOIntExecHarness,
      bank: Int,
      addr: Int,
      data: BigInt
  ): Unit = {
    dut.io.testRegWrite.valid.poke(true.B)
    dut.io.testRegWrite.bank.poke(bank.U)
    dut.io.testRegWrite.addr.poke(addr.U)
    dut.io.testRegWrite.data.poke(data.U)
    dut.clock.step()
    dut.io.testRegWrite.valid.poke(false.B)
  }

  private def runInstruction(
      dut: DADAOIntExecHarness,
      id: String,
      word: BigInt
  ): Unit = {
    val entry = entryFor(id)
    dut.io.instructionId.poke(entry.id.U)
    dut.io.word.poke(word.U(32.W))
    dut.io.commit.poke(true.B)
    dut.clock.step()
    dut.io.commit.poke(false.B)
  }

  private def readRegister(
      dut: DADAOIntExecHarness,
      bank: Int,
      addr: Int
  ): BigInt = {
    dut.io.debugReadBank.poke(bank.U)
    dut.io.debugReadAddr.poke(addr.U)
    dut.io.debugReadData.peek().litValue
  }

  it should "execute descriptor-selected narrow arithmetic" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      loadRegister(dut, DADAORegBank.Rd, 2, BigInt("ffffffff", 16))
      loadRegister(dut, DADAORegBank.Rd, 3, 1)

      val word = setField(
        setField(
          setField(baseWord("add.ut_orrr_rd"), 12, 1),
          6,
          2
        ),
        0,
        3
      )
      runInstruction(dut, "add.ut_orrr_rd", word)
      readRegister(dut, DADAORegBank.Rd, 1) should be(0)
    }
  }

  it should "commit an external load register write" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      dut.io.extWrite.valid.poke(true.B)
      dut.io.extWrite.bank.poke(DADAORegBank.Rd.U)
      dut.io.extWrite.addr.poke(1.U)
      dut.io.extWrite.data.poke(BigInt("beef", 16).U)
      dut.clock.step()
      dut.io.extWrite.valid.poke(false.B)

      readRegister(dut, DADAORegBank.Rd, 1) should be(
        BigInt("beef", 16)
      )
    }
  }

  it should "execute read-modify-write immediate operations" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      loadRegister(dut, DADAORegBank.Rd, 1, 100)
      val addWord = setField(
        setField(baseWord("add.si_riii_rd"), 18, 1),
        0,
        7,
        18
      )
      runInstruction(dut, "add.si_riii_rd", addWord)
      readRegister(dut, DADAORegBank.Rd, 1) should be(107)

      val setWord =
        setField(
          setField(
            setField(baseWord("set.zw_rwii_rd"), 18, 2),
            16,
            1,
            2
          ),
          0,
          BigInt("1234", 16),
          16
        )
      runInstruction(dut, "set.zw_rwii_rd", setWord)
      readRegister(dut, DADAORegBank.Rd, 2) should be(
        BigInt("12340000", 16)
      )

      val orWord =
        setField(
          setField(
            setField(baseWord("or.w_rwii_rd"), 18, 2),
            16,
            1,
            2
          ),
          0,
          BigInt("8000", 16),
          16
        )
      runInstruction(dut, "or.w_rwii_rd", orWord)
      readRegister(dut, DADAORegBank.Rd, 2) should be(
        BigInt("92340000", 16)
      )
    }
  }

  it should "execute aip.si relative to the current instruction address" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      val positiveWord = setField(
        setField(baseWord("aip.si_riii_rb"), 18, 1),
        0,
        1,
        18
      )
      runInstruction(dut, "aip.si_riii_rb", positiveWord)
      readRegister(dut, DADAORegBank.Rb, 1) should be(testPc + 0x1000)

      val negativeWord = setField(
        setField(baseWord("aip.si_riii_rb"), 18, 2),
        0,
        (BigInt(1) << 18) - 1,
        18
      )
      runInstruction(dut, "aip.si_riii_rb", negativeWord)
      readRegister(dut, DADAORegBank.Rb, 2) should be(testPc - 0x1000)
    }
  }

  it should "write both destinations for dual arithmetic" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      loadRegister(dut, DADAORegBank.Rd, 3, allOnes64)
      loadRegister(dut, DADAORegBank.Rd, 4, 1)
      val word = setField(
        setField(
          setField(baseWord("add.uo_rrrr_rd"), 18, 1),
          12,
          2
        ),
        6,
        3
      )
      val finalWord = setField(word, 0, 4)
      runInstruction(dut, "add.uo_rrrr_rd", finalWord)
      readRegister(dut, DADAORegBank.Rd, 1) should be(1)
      readRegister(dut, DADAORegBank.Rd, 2) should be(0)
    }
  }

  it should "implement conditional assignment write enables" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      loadRegister(dut, DADAORegBank.Rd, 2, 0)
      loadRegister(dut, DADAORegBank.Rd, 3, 11)
      loadRegister(dut, DADAORegBank.Rd, 4, 22)
      val csZ = setField(
        setField(
          setField(
            setField(baseWord("cs.z_rrrr_rd"), 18, 2),
            12,
            1
          ),
          6,
          3
        ),
        0,
        4
      )
      runInstruction(dut, "cs.z_rrrr_rd", csZ)
      readRegister(dut, DADAORegBank.Rd, 1) should be(11)

      loadRegister(dut, DADAORegBank.Rd, 1, 99)
      loadRegister(dut, DADAORegBank.Rd, 2, 5)
      loadRegister(dut, DADAORegBank.Rd, 3, 5)
      loadRegister(dut, DADAORegBank.Rd, 4, 33)
      val csNe = setField(
        setField(
          setField(
            setField(baseWord("cs.ne_rrrr_rd"), 18, 2),
            12,
            3
          ),
          6,
          1
        ),
        0,
        4
      )
      runInstruction(dut, "cs.ne_rrrr_rd", csNe)
      readRegister(dut, DADAORegBank.Rd, 1) should be(99)
    }
  }

  it should "execute rd2rd bulk copy through the internal path" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      loadRegister(dut, DADAORegBank.Rd, 10, 1)
      loadRegister(dut, DADAORegBank.Rd, 11, 2)
      loadRegister(dut, DADAORegBank.Rd, 12, 3)
      val word = setField(
        setField(
          setField(baseWord("rd2rd_orri_rd"), 12, 20),
          6,
          10
        ),
        0,
        3
      )
      runInstruction(dut, "rd2rd_orri_rd", word)
      readRegister(dut, DADAORegBank.Rd, 20) should be(1)
      readRegister(dut, DADAORegBank.Rd, 21) should be(2)
      readRegister(dut, DADAORegBank.Rd, 22) should be(3)
    }
  }

  it should "use rb0 as pc during rb2rb bulk copy" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      loadRegister(dut, DADAORegBank.Rb, 1, 7)
      val word = setField(
        setField(
          setField(baseWord("rb2rb_orri_rb"), 12, 3),
          6,
          0
        ),
        0,
        3
      )
      runInstruction(dut, "rb2rb_orri_rb", word)
      readRegister(dut, DADAORegBank.Rb, 3) should be(testPc)
      readRegister(dut, DADAORegBank.Rb, 4) should be(7)
      readRegister(dut, DADAORegBank.Rb, 5) should be(0)
    }
  }

  it should "mask ra0 writes through rd2ra" in {
    test(new DADAOIntExecHarness(params)) { dut =>
      clear(dut)
      loadRegister(dut, DADAORegBank.Rd, 1, allOnes64)
      val word = setField(
        setField(
          setField(baseWord("rd2ra_orri_ra"), 12, 0),
          6,
          1
        ),
        0,
        1
      )
      runInstruction(dut, "rd2ra_orri_ra", word)
      readRegister(dut, DADAORegBank.Ra, 0) should be(
        BigInt("003fffffffffffff", 16)
      )
    }
  }
}
