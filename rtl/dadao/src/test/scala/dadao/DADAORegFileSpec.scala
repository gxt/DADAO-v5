package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec
import org.scalatest.matchers.should.Matchers

final class DADAORegFileSpec
    extends AnyFlatSpec
    with ChiselScalatestTester
    with Matchers {
  behavior of "DADAORegFile"

  private val testPc = BigInt("fc0000000000", 16)

  private def clearInputs(dut: DADAORegFile): Unit = {
    dut.io.pc.poke(testPc.U)
    dut.rasControl.req.push.poke(false.B)
    dut.rasControl.req.pushAddress.poke(0.U)
    dut.rasControl.req.pop.poke(false.B)
    dut.rasControl.memReqAccepted.poke(false.B)
    dut.rasControl.memResp.valid.poke(false.B)
    dut.rasControl.memResp.data.poke(0.U)
    dut.rasControl.memResp.fault.poke(false.B)
    dut.rasControl.memResp.faultCode.poke(0.U)
    for (index <- 0 until DADAORegFileIO.ReadPorts) {
      dut.io.rdReadAddr(index).poke(0.U)
      dut.io.rbReadAddr(index).poke(0.U)
      dut.io.raReadAddr(index).poke(0.U)
    }
    for (index <- 0 until 64) {
      dut.io.rdWrite(index).valid.poke(false.B)
      dut.io.rdWrite(index).bits.poke(0.U)
      dut.io.rbWrite(index).valid.poke(false.B)
      dut.io.rbWrite(index).bits.poke(0.U)
      dut.io.raWrite(index).valid.poke(false.B)
      dut.io.raWrite(index).bits.poke(0.U)
    }
    dut.io.bulkCopy.valid.poke(false.B)
    dut.io.bulkCopy.sourceBank.poke(DADAORegBank.Rd.U)
    dut.io.bulkCopy.destBank.poke(DADAORegBank.Rd.U)
    dut.io.bulkCopy.sourceStart.poke(0.U)
    dut.io.bulkCopy.destStart.poke(0.U)
    dut.io.bulkCopy.count.poke(0.U)
    dut.io.blockWrite.valid.poke(false.B)
    dut.io.blockWrite.bank.poke(DADAORegBank.Rd.U)
    dut.io.blockWrite.start.poke(0.U)
    dut.io.blockWrite.count.poke(0.U)
    for (index <- 0 until 63) {
      dut.io.blockWrite.data(index).poke(0.U)
    }
  }

  private def writeOne(
      dut: DADAORegFile,
      bank: Int,
      index: Int,
      value: BigInt
  ): Unit = {
    val write = bank match {
      case DADAORegBank.Rd => dut.io.rdWrite(index)
      case DADAORegBank.Rb => dut.io.rbWrite(index)
      case DADAORegBank.Ra => dut.io.raWrite(index)
      case other => fail(s"unsupported bank $other")
    }
    write.valid.poke(true.B)
    write.bits.poke(value.U)
    dut.clock.step()
    write.valid.poke(false.B)
  }

  private def readOne(
      dut: DADAORegFile,
      bank: Int,
      index: Int
  ): BigInt = {
    bank match {
      case DADAORegBank.Rd =>
        dut.io.rdReadAddr(0).poke(index.U)
        dut.io.rdReadData(0).peek().litValue
      case DADAORegBank.Rb =>
        dut.io.rbReadAddr(0).poke(index.U)
        dut.io.rbReadData(0).peek().litValue
      case DADAORegBank.Ra =>
        dut.io.raReadAddr(0).poke(index.U)
        dut.io.raReadData(0).peek().litValue
      case other =>
        fail(s"unsupported bank $other")
    }
  }

  private def bulkCopy(
      dut: DADAORegFile,
      sourceBank: Int,
      destBank: Int,
      sourceStart: Int,
      destStart: Int,
      count: Int
  ): Unit = {
    dut.io.bulkCopy.valid.poke(true.B)
    dut.io.bulkCopy.sourceBank.poke(sourceBank.U)
    dut.io.bulkCopy.destBank.poke(destBank.U)
    dut.io.bulkCopy.sourceStart.poke(sourceStart.U)
    dut.io.bulkCopy.destStart.poke(destStart.U)
    dut.io.bulkCopy.count.poke(count.U)
    dut.clock.step()
    dut.io.bulkCopy.valid.poke(false.B)
  }

  private def blockWrite(
      dut: DADAORegFile,
      bank: Int,
      start: Int,
      values: Seq[BigInt]
  ): Unit = {
    for (index <- values.indices) {
      dut.io.blockWrite.data(index).poke(values(index).U)
    }
    dut.io.blockWrite.valid.poke(true.B)
    dut.io.blockWrite.bank.poke(bank.U)
    dut.io.blockWrite.start.poke(start.U)
    dut.io.blockWrite.count.poke(values.size.U)
    dut.clock.step()
    dut.io.blockWrite.valid.poke(false.B)
  }

  it should "reset banks and enforce special register behavior" in {
    test(new DADAORegFile) { dut =>
      clearInputs(dut)
      readOne(dut, DADAORegBank.Rd, 0) should be(0)
      readOne(dut, DADAORegBank.Rb, 0) should be(testPc)
      readOne(dut, DADAORegBank.Ra, 0) should be(0)

      writeOne(dut, DADAORegBank.Rd, 0, BigInt("ffffffffffffffff", 16))
      writeOne(dut, DADAORegBank.Rb, 0, BigInt("ffffffffffffffff", 16))
      writeOne(dut, DADAORegBank.Ra, 0, BigInt("ffffffffffffffff", 16))

      readOne(dut, DADAORegBank.Rd, 0) should be(0)
      readOne(dut, DADAORegBank.Rb, 0) should be(testPc)
      readOne(dut, DADAORegBank.Ra, 0) should be(
        BigInt("003fffffffffffff", 16)
      )
    }
  }

  it should "expose the complete 64-bit pc through rb0" in {
    test(new DADAORegFile) { dut =>
      val highPc =
        testPc | (BigInt("abcd", 16) << 48)
      clearInputs(dut)
      dut.io.pc.poke(highPc.U)
      readOne(dut, DADAORegBank.Rb, 0) should be(highPc)
    }
  }

  it should "provide six independent reads per bank" in {
    test(new DADAORegFile) { dut =>
      clearInputs(dut)
      for (offset <- 0 until DADAORegFileIO.ReadPorts) {
        dut.io.rdWrite(40 + offset).valid.poke(true.B)
        dut.io.rdWrite(40 + offset).bits.poke((11 * (offset + 1)).U)
        dut.io.rbWrite(20 + offset).valid.poke(true.B)
        dut.io.rbWrite(20 + offset).bits.poke((100 + offset).U)
        dut.io.raWrite(30 + offset).valid.poke(true.B)
        dut.io.raWrite(30 + offset).bits.poke((200 + offset).U)
      }
      dut.clock.step()
      for (offset <- 0 until DADAORegFileIO.ReadPorts) {
        dut.io.rdWrite(40 + offset).valid.poke(false.B)
        dut.io.rbWrite(20 + offset).valid.poke(false.B)
        dut.io.raWrite(30 + offset).valid.poke(false.B)
      }

      for (offset <- 0 until DADAORegFileIO.ReadPorts) {
        dut.io.rdReadAddr(offset).poke((40 + offset).U)
        dut.io.rdReadData(offset).expect((11 * (offset + 1)).U)
        dut.io.rbReadAddr(offset).poke((20 + offset).U)
        dut.io.rbReadData(offset).expect((100 + offset).U)
        dut.io.raReadAddr(offset).poke((30 + offset).U)
        dut.io.raReadData(offset).expect((200 + offset).U)
      }
    }
  }

  it should "return the old value during a same-cycle write" in {
    test(new DADAORegFile) { dut =>
      clearInputs(dut)
      writeOne(dut, DADAORegBank.Rd, 7, BigInt("11", 16))
      dut.io.rdReadAddr(0).poke(7.U)
      dut.io.rdWrite(7).valid.poke(true.B)
      dut.io.rdWrite(7).bits.poke(BigInt("22", 16).U)
      dut.io.rdReadData(0).expect(BigInt("11", 16).U)
      dut.clock.step()
      dut.io.rdWrite(7).valid.poke(false.B)
      dut.io.rdReadData(0).expect(BigInt("22", 16).U)
    }
  }

  it should "copy 63 registers with an internal source snapshot" in {
    test(new DADAORegFile) { dut =>
      clearInputs(dut)
      for (index <- 1 until 64) {
        dut.io.rdWrite(index).valid.poke(true.B)
        dut.io.rdWrite(index).bits.poke((BigInt(index) * 3).U)
      }
      dut.clock.step()
      for (index <- 1 until 64) {
        dut.io.rdWrite(index).valid.poke(false.B)
      }

      bulkCopy(
        dut,
        sourceBank = DADAORegBank.Rd,
        destBank = DADAORegBank.Rb,
        sourceStart = 1,
        destStart = 1,
        count = 63
      )

      readOne(dut, DADAORegBank.Rb, 1) should be(3)
      readOne(dut, DADAORegBank.Rb, 31) should be(93)
      readOne(dut, DADAORegBank.Rb, 63) should be(189)

      bulkCopy(
        dut,
        sourceBank = DADAORegBank.Rd,
        destBank = DADAORegBank.Ra,
        sourceStart = 0,
        destStart = 10,
        count = 2
      )
      readOne(dut, DADAORegBank.Ra, 10) should be(0)
      readOne(dut, DADAORegBank.Ra, 11) should be(3)
    }
  }

  it should "copy rb0 as pc and mask ra0 writes" in {
    test(new DADAORegFile) { dut =>
      clearInputs(dut)
      writeOne(dut, DADAORegBank.Rb, 1, BigInt("123456789", 16))

      bulkCopy(
        dut,
        sourceBank = DADAORegBank.Rb,
        destBank = DADAORegBank.Ra,
        sourceStart = 0,
        destStart = 1,
        count = 2
      )
      readOne(dut, DADAORegBank.Ra, 1) should be(testPc)
      readOne(dut, DADAORegBank.Ra, 2) should be(
        BigInt("123456789", 16)
      )

      writeOne(
        dut,
        DADAORegBank.Rd,
        1,
        BigInt("ffffffffffffffff", 16)
      )
      bulkCopy(
        dut,
        sourceBank = DADAORegBank.Rd,
        destBank = DADAORegBank.Ra,
        sourceStart = 1,
        destStart = 0,
        count = 1
      )
      readOne(dut, DADAORegBank.Ra, 0) should be(
        BigInt("003fffffffffffff", 16)
      )
    }
  }

  it should "preserve source values for same-bank non-overlapping copy" in {
    test(new DADAORegFile) { dut =>
      clearInputs(dut)
      for ((index, value) <- Seq(10 -> 1, 11 -> 2, 12 -> 3)) {
        writeOne(dut, DADAORegBank.Rd, index, BigInt(value))
      }
      bulkCopy(
        dut,
        sourceBank = DADAORegBank.Rd,
        destBank = DADAORegBank.Rd,
        sourceStart = 10,
        destStart = 20,
        count = 3
      )

      readOne(dut, DADAORegBank.Rd, 10) should be(1)
      readOne(dut, DADAORegBank.Rd, 20) should be(1)
      readOne(dut, DADAORegBank.Rd, 21) should be(2)
      readOne(dut, DADAORegBank.Rd, 22) should be(3)
    }
  }

  it should "commit a contiguous block to RD, RB, or RA" in {
    test(new DADAORegFile) { dut =>
      clearInputs(dut)

      blockWrite(
        dut,
        DADAORegBank.Rd,
        1,
        Seq(BigInt(11), BigInt(22), BigInt(33))
      )
      readOne(dut, DADAORegBank.Rd, 1) should be(11)
      readOne(dut, DADAORegBank.Rd, 2) should be(22)
      readOne(dut, DADAORegBank.Rd, 3) should be(33)
      readOne(dut, DADAORegBank.Rd, 4) should be(0)

      blockWrite(
        dut,
        DADAORegBank.Rb,
        0,
        Seq(BigInt("ffff", 16), BigInt(44))
      )
      readOne(dut, DADAORegBank.Rb, 1) should be(44)

      blockWrite(
        dut,
        DADAORegBank.Ra,
        0,
        Seq(BigInt("ffffffffffffffff", 16), BigInt(55))
      )
      readOne(dut, DADAORegBank.Ra, 0) should be(
        BigInt("003fffffffffffff", 16)
      )
      readOne(dut, DADAORegBank.Ra, 1) should be(55)
    }
  }
}
