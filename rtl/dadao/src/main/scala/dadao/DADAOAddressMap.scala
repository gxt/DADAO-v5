package dadao

import chisel3._
import chisel3.util.{Cat, MuxLookup}

object DADAOMemoryRegion {
  val Unmapped: Int = 0
  val Ram: Int = 1
  val BootRom: Int = 2
}

final class DADAOAccessCheckIO(val params: DADAOParams) extends Bundle {
  val addr = Input(UInt(params.addrBits.W))
  val write = Input(Bool())
  val size = Input(UInt(3.W))
  val kind = Input(UInt(2.W))

  val region = Output(UInt(2.W))
  val mapped = Output(Bool())
  val aligned = Output(Bool())
  val allowed = Output(Bool())
  val fault = Output(Bool())
  val faultCode = Output(UInt(8.W))
}

final class DADAOAccessCheck(
    val params: DADAOParams = DADAOParams()
) extends Module {
  val io = IO(new DADAOAccessCheckIO(params))

  private val addressExt = Cat(0.U(1.W), io.addr)
  private val bytesExt = Cat(
    0.U((params.addrBits - 3).W),
    DADAOByteLane.sizeBytes(io.size)
  )
  private val accessEnd = addressExt + bytesExt

  private def inside(base: BigInt, extent: BigInt): Bool = {
    val start = base.U((params.addrBits + 1).W)
    val limit = (base + extent).U((params.addrBits + 1).W)
    addressExt >= start && accessEnd <= limit
  }

  private val ramHit = inside(params.ramBase, params.ramSize)
  private val bootRomHit = inside(params.bootRomBase, params.bootRomSize)
  private val mapped = ramHit || bootRomHit

  private val fetchAccess = io.kind === DADAOMemKind.Fetch.U
  private val dataAccess = io.kind === DADAOMemKind.Data.U
  private val validKind = fetchAccess || dataAccess
  private val sizeLegal = io.size <= DADAOMemSize.Octa.U
  private val alignmentMask =
    DADAOByteLane.sizeBytes(io.size) - 1.U
  private val naturallyAligned =
    sizeLegal && (io.addr & alignmentMask) === 0.U

  private val readOnlyViolation = bootRomHit && io.write
  private val fetchWidthViolation =
    fetchAccess && io.size =/= DADAOMemSize.Tetra.U
  private val kindViolation =
    !validKind ||
      (fetchAccess && io.write) ||
      fetchWidthViolation
  private val permissionViolation = readOnlyViolation || kindViolation

  private val region = MuxLookup(
    Cat(ramHit, bootRomHit),
    DADAOMemoryRegion.Unmapped.U(2.W)
  )(
    Seq(
      "b10".U -> DADAOMemoryRegion.Ram.U(2.W),
      "b01".U -> DADAOMemoryRegion.BootRom.U(2.W)
    )
  )

  private val faultCode = Mux(
    !mapped,
    DADAOFaultCode.Unmapped.U(8.W),
    Mux(
      !sizeLegal,
      DADAOFaultCode.Illi.U(8.W),
      Mux(
        !naturallyAligned,
        DADAOFaultCode.Malign.U(8.W),
        Mux(
          permissionViolation,
          DADAOFaultCode.Illi.U(8.W),
          DADAOFaultCode.None.U(8.W)
        )
      )
    )
  )

  io.region := region
  io.mapped := mapped
  io.aligned := naturallyAligned
  io.allowed := faultCode === DADAOFaultCode.None.U
  io.fault := faultCode =/= DADAOFaultCode.None.U
  io.faultCode := faultCode
}
