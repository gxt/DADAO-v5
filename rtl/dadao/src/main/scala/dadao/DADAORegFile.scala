package dadao

import chisel3._
import chisel3.util.{Cat, MuxLookup, Valid}

object DADAORegBank {
  val Rd: Int = 0
  val Rb: Int = 1
  val Ra: Int = 2
}

final class DADAOBulkCopyReq(val addrBits: Int = 64) extends Bundle {
  val valid = Bool()
  val sourceBank = UInt(2.W)
  val destBank = UInt(2.W)
  val sourceStart = UInt(6.W)
  val destStart = UInt(6.W)
  val count = UInt(6.W)
}

final class DADAOBlockRegWrite extends Bundle {
  val valid = Bool()
  val bank = UInt(2.W)
  val start = UInt(6.W)
  val count = UInt(6.W)
  val data = Vec(63, UInt(64.W))
}

final class DADAORegFileIO(val addrBits: Int) extends Bundle {
  val pc = Input(UInt(addrBits.W))

  val rdReadAddr = Input(Vec(DADAORegFileIO.ReadPorts, UInt(6.W)))
  val rdReadData = Output(Vec(DADAORegFileIO.ReadPorts, UInt(64.W)))
  val rbReadAddr = Input(Vec(DADAORegFileIO.ReadPorts, UInt(6.W)))
  val rbReadData = Output(Vec(DADAORegFileIO.ReadPorts, UInt(64.W)))
  val raReadAddr = Input(Vec(DADAORegFileIO.ReadPorts, UInt(6.W)))
  val raReadData = Output(Vec(DADAORegFileIO.ReadPorts, UInt(64.W)))

  val rdWrite = Input(Vec(64, Valid(UInt(64.W))))
  val rbWrite = Input(Vec(64, Valid(UInt(64.W))))
  val raWrite = Input(Vec(64, Valid(UInt(64.W))))

  val bulkCopy = Input(new DADAOBulkCopyReq(addrBits))
  val blockWrite = Input(new DADAOBlockRegWrite)
}

object DADAORegFileIO {
  val ReadPorts: Int = 6
}

final class DADAORegFile(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAORegFileIO(params.addrBits))
  val rasControl = IO(new DADAORasControlIO(params))

  private val rdRegs = RegInit(VecInit(Seq.fill(64)(0.U(64.W))))
  private val rbRegs = RegInit(VecInit(Seq.fill(64)(0.U(64.W))))
  private val ras = Module(new DADAORas(params))
  ras.io.req := rasControl.req
  ras.io.memReqAccepted := rasControl.memReqAccepted
  ras.io.memResp := rasControl.memResp
  rasControl.resp := ras.io.resp

  private def readRd(addr: UInt): UInt =
    Mux(addr === 0.U, 0.U(64.W), rdRegs(addr))

  private def readRb(addr: UInt): UInt =
    Mux(addr === 0.U, io.pc, rbRegs(addr))

  private def readRa(addr: UInt): UInt =
    Mux(
      addr === 0.U,
      Cat(0.U(10.W), ras.io.values(0)(53, 0)),
      ras.io.values(addr)
    )

  private def readBank(bank: UInt, addr: UInt): UInt =
    MuxLookup(bank, 0.U(64.W))(
      Seq(
        DADAORegBank.Rd.U -> readRd(addr),
        DADAORegBank.Rb.U -> readRb(addr),
        DADAORegBank.Ra.U -> readRa(addr)
      )
    )

  io.rdReadData := VecInit(io.rdReadAddr.map(readRd))
  io.rbReadData := VecInit(io.rbReadAddr.map(readRb))
  io.raReadData := VecInit(io.raReadAddr.map(readRa))

  private val raWrites =
    Wire(Vec(64, Valid(UInt(64.W))))
  raWrites := io.raWrite

  for (index <- 1 until 64) {
    when(io.rdWrite(index).valid) {
      rdRegs(index) := io.rdWrite(index).bits
    }
    when(io.rbWrite(index).valid) {
      rbRegs(index) := io.rbWrite(index).bits
    }
  }

  private val blockEnd =
    Cat(0.U(1.W), io.blockWrite.start) +
      Cat(0.U(1.W), io.blockWrite.count)

  for (index <- 0 until 64) {
    val destIndex = index.U(6.W)
    val inBlockRange =
      io.blockWrite.valid &&
        destIndex >= io.blockWrite.start &&
        destIndex < blockEnd
    val blockOffset = destIndex - io.blockWrite.start
    val blockData = io.blockWrite.data(blockOffset)

    when(inBlockRange) {
      when(io.blockWrite.bank === DADAORegBank.Rd.U) {
        when(destIndex =/= 0.U) {
          rdRegs(destIndex) := blockData
        }
      }.elsewhen(io.blockWrite.bank === DADAORegBank.Rb.U) {
        when(destIndex =/= 0.U) {
          rbRegs(destIndex) := blockData
        }
      }.elsewhen(io.blockWrite.bank === DADAORegBank.Ra.U) {
        when(destIndex === 0.U) {
          raWrites(0).valid := true.B
          raWrites(0).bits := Cat(0.U(10.W), blockData(53, 0))
        }.otherwise {
          raWrites(destIndex).valid := true.B
          raWrites(destIndex).bits := blockData
        }
      }
    }
  }

  private val destEnd =
    Cat(0.U(1.W), io.bulkCopy.destStart) +
      Cat(0.U(1.W), io.bulkCopy.count)

  for (index <- 0 until 64) {
    val destIndex = index.U(6.W)
    val inDestRange =
      io.bulkCopy.valid &&
        destIndex >= io.bulkCopy.destStart &&
        destIndex < destEnd
    val offset = destIndex - io.bulkCopy.destStart
    val sourceIndex =
      (
        Cat(0.U(1.W), io.bulkCopy.sourceStart) +
          Cat(0.U(1.W), offset)
      )(5, 0)
    val sourceValue =
      readBank(io.bulkCopy.sourceBank, sourceIndex)

    when(inDestRange) {
      when(io.bulkCopy.destBank === DADAORegBank.Rd.U) {
        when(destIndex =/= 0.U) {
          rdRegs(destIndex) := sourceValue
        }
      }.elsewhen(io.bulkCopy.destBank === DADAORegBank.Rb.U) {
        when(destIndex =/= 0.U) {
          rbRegs(destIndex) := sourceValue
        }
      }.elsewhen(io.bulkCopy.destBank === DADAORegBank.Ra.U) {
        when(destIndex === 0.U) {
          raWrites(0).valid := true.B
          raWrites(0).bits := Cat(0.U(10.W), sourceValue(53, 0))
        }.otherwise {
          raWrites(destIndex).valid := true.B
          raWrites(destIndex).bits := sourceValue
        }
      }
    }
  }

  ras.io.write := raWrites
}
