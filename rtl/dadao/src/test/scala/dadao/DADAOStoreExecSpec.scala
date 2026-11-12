package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOStoreExecSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOStoreExec"

  private val params = DADAOParams()
  private val baseAddress = BigInt("fc0000000100", 16)

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
      source: Int,
      base: Int,
      immediate: Int = 0
  ): BigInt = {
    val index = DADAODecoderTable.ids.indexOf(id)
    val word = DADAODecoderTable.entries(index).value
    setField(
      setField(
        setField(word, 18, source),
        12,
        base
      ),
      0,
      BigInt(immediate) & BigInt("fff", 16),
      width = 12
    )
  }

  private def prepare(
      dut: DADAOStoreExec,
      id: String,
      sourceReg: Int,
      baseReg: Int,
      sourceValue: BigInt,
      immediate: Int = 0
  ): Unit = {
    val index = DADAODecoderTable.ids.indexOf(id)
    dut.io.decoded.word.poke(
      codedWord(id, sourceReg, baseReg, immediate).U(32.W)
    )
    dut.io.decoded.id.poke(index.U)
    dut.io.baseValue.poke(baseAddress.U)
    dut.io.sourceValue.poke(sourceValue.U)
    dut.clock.step()
  }

  it should "prepare all six M1 single-register stores" in {
    test(new DADAOStoreExec(params)) { dut =>
      val cases = Seq(
        (
          "st.b_rrii_rd",
          0,
          DADAORegBank.Rd,
          DADAOMemSize.Byte,
          0x01,
          BigInt("80ff00aa11223344", 16)
        ),
        (
          "st.w_rrii_rd",
          2,
          DADAORegBank.Rd,
          DADAOMemSize.Wyde,
          0x0c,
          BigInt("80ffbabe11223344", 16)
        ),
        (
          "st.t_rrii_rd",
          4,
          DADAORegBank.Rd,
          DADAOMemSize.Tetra,
          0xf0,
          BigInt("deadbeef11223344", 16)
        ),
        (
          "st.o_rrii_rd",
          0,
          DADAORegBank.Rd,
          DADAOMemSize.Octa,
          0xff,
          BigInt("1122334455667788", 16)
        ),
        (
          "st.o_rrii_rb",
          0,
          DADAORegBank.Rb,
          DADAOMemSize.Octa,
          0xff,
          BigInt("aabbccddeeff0011", 16)
        ),
        (
          "st.o_rrii_ra",
          0,
          DADAORegBank.Ra,
          DADAOMemSize.Octa,
          0xff,
          BigInt("0102030405060708", 16)
        )
      )

      cases.foreach {
        case (id, addrLow, bank, size, strobe, sourceValue) =>
          val sourceReg = 7
          val baseReg = 9
          prepare(
            dut,
            id,
            sourceReg,
            baseReg,
            sourceValue,
            immediate = addrLow
          )
          dut.io.isStore.expect(true.B)
          dut.io.baseRegAddr.expect(baseReg.U)
          dut.io.sourceBank.expect(bank.U)
          dut.io.sourceRegAddr.expect(sourceReg.U)
          dut.io.requestAddr.expect((baseAddress + addrLow).U)
          dut.io.requestSize.expect(size.U)
          val width = 1 << size
          val valueMask = (BigInt(1) << (width * 8)) - 1
          dut.io.requestWdata.expect((sourceValue & valueMask).U)
          dut.io.requestWstrb.expect(strobe.U)
      }
    }
  }

  it should "sign extend a negative immediate for the store address" in {
    test(new DADAOStoreExec(params)) { dut =>
      prepare(
        dut,
        "st.o_rrii_rd",
        sourceReg = 3,
        baseReg = 4,
        sourceValue = BigInt("12345678", 16),
        immediate = -8
      )
      dut.io.requestAddr.expect((baseAddress - 8).U)
      dut.io.requestWdata.expect(BigInt("12345678", 16).U)
      dut.io.requestWstrb.expect(0xff.U)
    }
  }
}
