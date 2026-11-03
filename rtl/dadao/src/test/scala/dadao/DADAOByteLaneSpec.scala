package dadao

import chisel3._
import chiseltest._
import org.scalatest.flatspec.AnyFlatSpec

final class DADAOByteLaneProbeIO extends Bundle {
  val oldData = Input(UInt(64.W))
  val writeData = Input(UInt(64.W))
  val readData = Input(UInt(64.W))
  val addrLow = Input(UInt(3.W))
  val size = Input(UInt(3.W))
  val wstrb = Input(UInt(8.W))

  val laneMask = Output(UInt(8.W))
  val writeMask = Output(UInt(8.W))
  val merged = Output(UInt(64.W))
  val extracted = Output(UInt(64.W))
}

final class DADAOByteLaneProbe extends Module {
  val io = IO(new DADAOByteLaneProbeIO)

  io.laneMask := DADAOByteLane.laneMask(io.addrLow, io.size)
  io.writeMask :=
    DADAOByteLane.laneMask(io.addrLow, io.size) & io.wstrb
  io.merged := DADAOByteLane.mergeWrite(
    io.oldData,
    io.writeData,
    io.addrLow,
    io.size,
    io.wstrb
  )
  io.extracted := DADAOByteLane.readValue(
    io.readData,
    io.addrLow,
    io.size
  )
}

final class DADAOByteLaneSpec
    extends AnyFlatSpec
    with ChiselScalatestTester {
  behavior of "DADAOByteLane"

  private def prepare(dut: DADAOByteLaneProbe): Unit = {
    dut.io.oldData.poke(0.U)
    dut.io.writeData.poke(0.U)
    dut.io.readData.poke(0.U)
    dut.io.addrLow.poke(0.U)
    dut.io.size.poke(DADAOMemSize.Byte.U)
    dut.io.wstrb.poke(0.U)
  }

  it should "generate big-endian byte masks" in {
    test(new DADAOByteLaneProbe) { dut =>
      prepare(dut)
      dut.clock.step()

      dut.io.addrLow.poke(3.U)
      dut.io.size.poke(DADAOMemSize.Byte.U)
      dut.io.laneMask.expect(0x08.U)

      dut.io.addrLow.poke(2.U)
      dut.io.size.poke(DADAOMemSize.Wyde.U)
      dut.io.laneMask.expect(0x0c.U)

      dut.io.addrLow.poke(4.U)
      dut.io.size.poke(DADAOMemSize.Tetra.U)
      dut.io.laneMask.expect(0xf0.U)

      dut.io.addrLow.poke(0.U)
      dut.io.size.poke(DADAOMemSize.Octa.U)
      dut.io.laneMask.expect(0xff.U)
    }
  }

  it should "merge right-aligned stores into big-endian lanes" in {
    test(new DADAOByteLaneProbe) { dut =>
      prepare(dut)
      dut.clock.step()

      dut.io.writeData.poke(BigInt("11223344", 16).U)
      dut.io.addrLow.poke(0.U)
      dut.io.size.poke(DADAOMemSize.Tetra.U)
      dut.io.wstrb.poke(0x0f.U)
      dut.io.writeMask.expect(0x0f.U)
      dut.io.merged.expect(BigInt("1122334400000000", 16).U)

      dut.io.oldData.poke(BigInt("1122334455667788", 16).U)
      dut.io.writeData.poke(BigInt("aa", 16).U)
      dut.io.addrLow.poke(2.U)
      dut.io.size.poke(DADAOMemSize.Byte.U)
      dut.io.wstrb.poke(0x04.U)
      dut.io.merged.expect(BigInt("1122aa4455667788", 16).U)

      dut.io.writeData.poke(BigInt("aabb", 16).U)
      dut.io.addrLow.poke(4.U)
      dut.io.size.poke(DADAOMemSize.Wyde.U)
      dut.io.wstrb.poke(0x30.U)
      dut.io.merged.expect(BigInt("11223344aabb7788", 16).U)
    }
  }

  it should "extract right-aligned big-endian load values" in {
    test(new DADAOByteLaneProbe) { dut =>
      prepare(dut)
      dut.clock.step()
      dut.io.readData.poke(BigInt("1122334455667788", 16).U)

      dut.io.addrLow.poke(0.U)
      dut.io.size.poke(DADAOMemSize.Byte.U)
      dut.io.extracted.expect(BigInt("11", 16).U)

      dut.io.addrLow.poke(3.U)
      dut.io.size.poke(DADAOMemSize.Byte.U)
      dut.io.extracted.expect(BigInt("44", 16).U)

      dut.io.addrLow.poke(2.U)
      dut.io.size.poke(DADAOMemSize.Wyde.U)
      dut.io.extracted.expect(BigInt("3344", 16).U)

      dut.io.addrLow.poke(4.U)
      dut.io.size.poke(DADAOMemSize.Tetra.U)
      dut.io.extracted.expect(BigInt("55667788", 16).U)

      dut.io.addrLow.poke(0.U)
      dut.io.size.poke(DADAOMemSize.Octa.U)
      dut.io.extracted.expect(BigInt("1122334455667788", 16).U)
    }
  }
}
