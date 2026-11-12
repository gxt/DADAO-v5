package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOBlockMemExecSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOBlockMemExec"

  private val params = DADAOParams()
  private val baseAddress = BigInt("fc0000000100", 16)
  private val offsetValue = BigInt("20", 16)
  private val sourceValue = BigInt("deadbeef11223344", 16)
  private val responseValue = BigInt("ff80ff7f8001fe01", 16)

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
      startReg: Int,
      baseReg: Int,
      offsetReg: Int,
      count: Int
  ): BigInt = {
    val index = DADAODecoderTable.ids.indexOf(id)
    val word = DADAODecoderTable.entries(index).value
    setField(
      setField(
        setField(
          setField(word, 18, startReg),
          12,
          baseReg
        ),
        6,
        offsetReg
      ),
      0,
      count
    )
  }

  it should "decode all 15 M1 block memory forms" in {
    test(new DADAOBlockMemExec(params)) { dut =>
      val cases = Seq(
        ("ldm.ub_rrri_rd", false, 8, DADAORegBank.Rd),
        ("ldm.uw_rrri_rd", false, 16, DADAORegBank.Rd),
        ("ldm.ut_rrri_rd", false, 32, DADAORegBank.Rd),
        ("ldm.sb_rrri_rd", false, 8, DADAORegBank.Rd),
        ("ldm.sw_rrri_rd", false, 16, DADAORegBank.Rd),
        ("ldm.st_rrri_rd", false, 32, DADAORegBank.Rd),
        ("stm.b_rrri_rd", true, 8, DADAORegBank.Rd),
        ("stm.w_rrri_rd", true, 16, DADAORegBank.Rd),
        ("stm.t_rrri_rd", true, 32, DADAORegBank.Rd),
        ("ldm.o_rrri_rd", false, 64, DADAORegBank.Rd),
        ("stm.o_rrri_rd", true, 64, DADAORegBank.Rd),
        ("ldm.o_rrri_rb", false, 64, DADAORegBank.Rb),
        ("stm.o_rrri_rb", true, 64, DADAORegBank.Rb),
        ("ldm.o_rrri_ra", false, 64, DADAORegBank.Ra),
        ("stm.o_rrri_ra", true, 64, DADAORegBank.Ra)
      )

      cases.foreach {
        case (id, store, width, bank) =>
          val index = DADAODecoderTable.ids.indexOf(id)
          val startReg = 7
          val baseReg = 2
          val offsetReg = 1
          val count = 3
          val addrLow = if (width == 16) 2 else if (width == 32) 4 else 0
          val firstAddress = baseAddress + offsetValue
          val address = firstAddress + addrLow

          dut.io.decoded.word.poke(
            codedWord(id, startReg, baseReg, offsetReg, count).U(32.W)
          )
          dut.io.decoded.id.poke(index.U)
          dut.io.baseValue.poke(baseAddress.U)
          dut.io.offsetValue.poke(offsetValue.U)
          dut.io.address.poke(address.U)
          dut.io.sourceValue.poke(sourceValue.U)
          dut.io.responseValue.poke(responseValue.U)
          dut.clock.step()

          dut.io.isBlock.expect(true.B)
          dut.io.isLoad.expect((!store).B)
          dut.io.isStore.expect(store.B)
          dut.io.firstAddress.expect(firstAddress.U)
          dut.io.startRegAddr.expect(startReg.U)
          dut.io.baseRegAddr.expect(baseReg.U)
          dut.io.offsetRegAddr.expect(offsetReg.U)
          dut.io.targetBank.expect(bank.U)
          dut.io.count.expect(count.U)

          val expectedSize = width match {
            case 8 => DADAOMemSize.Byte
            case 16 => DADAOMemSize.Wyde
            case 32 => DADAOMemSize.Tetra
            case _ => DADAOMemSize.Octa
          }
          dut.io.requestSize.expect(expectedSize.U)
          val valueMask = (BigInt(1) << width) - 1
          dut.io.requestWdata.expect((sourceValue & valueMask).U)
          val strobe =
            (((1 << (width / 8)) - 1) << addrLow) & 0xff
          dut.io.requestWstrb.expect(strobe.U)

          val raw = responseValue & valueMask
          val signed = id.startsWith("ldm.sb") ||
            id.startsWith("ldm.sw") ||
            id.startsWith("ldm.st")
          val extended =
            if (width == 64) raw
            else if (signed && raw.testBit(width - 1)) {
              raw | (((BigInt(1) << (64 - width)) - 1) << width)
            } else raw
          dut.io.loadValue.expect(extended.U)
      }
    }
  }

  it should "limit the metadata table to the M1 block forms" in {
    assert(DADAOBlockMemTable.entries.size == 15)
    assert(
      DADAOBlockMemTable.entries.forall { entry =>
        DADAODecoderTable.entries(entry.id).scope == DADAOScope.M1
      }
    )
  }

  it should "accept the maximum count without wrapping" in {
    test(new DADAOBlockMemExec(params)) { dut =>
      val index = DADAODecoderTable.ids.indexOf("ldm.o_rrri_rd")

      dut.io.decoded.word.poke(
        codedWord("ldm.o_rrri_rd", 1, 2, 3, 63).U(32.W)
      )
      dut.io.decoded.id.poke(index.U)
      dut.io.baseValue.poke(baseAddress.U)
      dut.io.offsetValue.poke(0.U)
      dut.io.address.poke(baseAddress.U)
      dut.io.sourceValue.poke(0.U)
      dut.io.responseValue.poke(0.U)
      dut.clock.step()

      dut.io.isBlock.expect(true.B)
      dut.io.isLoad.expect(true.B)
      dut.io.count.expect(63.U)
    }
  }
}
